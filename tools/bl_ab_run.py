#!/usr/bin/env python3
"""BLACK LIQUIDITY Editor A/B/C -- repeatable runner (task-aae4f843).

Encapsulates the mechanical steps of the CEO's 2026-09-25 experiment (an
Editor that decides by eye vs a Scripter's beats.json routed through a
blind Editor vs the same beats.json with no Editor at all) so re-running it
-- on a new episode window, or to re-measure variance -- never again needs
a model to figure out the steps. What still genuinely needs a model is the
EDITORIAL work inside Arm A/B (spawned `video_editor` tasks) -- this script
only automates spawning them, deploying their shared fixture, running
Arm C directly, collecting results, and scoring.

Subcommands:
    fixture     build the local generator dir (build_cut.py/assemble.py
                from the branch + the clean template + episode media) and
                scp it to Contabo as the shared fixture all 3 arms use.
    spawn-a     create + delegate the Arm A video_editor task (brief =
                docs/ops/bl-ab-2026-09-25/arms/A/README.md verbatim).
    spawn-b     same for Arm B.
    push-tool   scp tools/bl_compose.py into a spawned worker's remote
                worktree -- needed only while this tool is unmerged to main
                (spoke worktrees branch from origin/main, not this branch).
    collect     fetch a finished arm's branch (REPORT.md, beats.json,
                render-meta.json, checker-result.json) and scp its mp4 +
                Claude Code transcript back to $WORK_DIR/out/.
    run-c       Arm C: compose + render + check directly over ssh on
                Contabo, no worker, no fix loop.
    score       run tools/bl_score.py against every collected arm's
                beats.json and write docs/ops/bl-ab-2026-09-25/arms/scores.md.

    -- split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, task-1678d38e) --
    fixture-full  stage the FULL 153.0s EP57 fixture (every lipsync part,
                every real/third-party/broll asset, the whole
                SCRIPT.tsv/timings.tsv/audio-hq.mp3, ground-truth redacted)
                straight into a local dir on this box -- no ssh/scp, this
                box IS Contabo. Arm 1 and every Arm 2 segment editor reads
                from the same fixture-full.
    spawn-seg   print (NEVER spawn) one segment editor's brief -- the
                segment contract from PLAN.md plus that segment's own
                [t0,t1) window, layered onto the standard blackliquidity-cut
                pipeline. Requires a segments.json from tools/bl_split.py.

Usage:
    python3 tools/bl_ab_run.py fixture --episode-work-dir ~/MoonieXHQ/Work/task-501f1d89
    python3 tools/bl_ab_run.py spawn-a --owner-cto 91a17eb2
    python3 tools/bl_ab_run.py push-tool --worktree <remote worktree path>
    python3 tools/bl_ab_run.py collect --arm A --branch agent/video_editor-task-XXXX \\
        --worktree <remote worktree path> --work-dir ~/MoonieXHQ/Work/task-XXXX
    python3 tools/bl_ab_run.py run-c --work-dir ~/MoonieXHQ/Work/task-XXXX
    python3 tools/bl_ab_run.py score --work-dir ~/MoonieXHQ/Work/task-XXXX
    python3 tools/bl_ab_run.py fixture-full
    python3 tools/bl_ab_run.py spawn-seg --segments segments.json --seg seg01
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SSH_ALIAS = "mooniex-vps"
CONTABO_FIXTURE_DIR = "/opt/MoonieXHQ/Work/bl-ab-ep57"
SKILL_TEMPLATE = ROOT / ".claude" / "skills" / "blackliquidity-cut" / "template"
GENERATOR_BRANCH = "origin/agent/video_editor-task-501f1d89"
GENERATOR_BRANCH_PATH = "prototypes/bl57-cut"
SCRIPT_TSV = ROOT / "prototypes" / "bl57-script" / "SCRIPT.tsv"
JEV_PATH = "prototypes/bl-jev-scoreboard/ep57"
T_MAX = 30.78
SCRIPTER_BEATS = ROOT / "docs" / "ops" / "bl-ab-2026-09-25" / "beats.json"
GROUND_TRUTH = ROOT / "docs" / "ops" / "bl-ab-2026-09-25" / "ground_truth_beats.json"
ARMS_DIR = ROOT / "docs" / "ops" / "bl-ab-2026-09-25" / "arms"

# ── split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, task-1678d38e) ──
SPLIT_AB_PLAN = ROOT / "docs" / "ops" / "bl-split-ab-2026-09-25" / "PLAN.md"
FULL_EPISODE_WORK_DIR = Path("/opt/MoonieXHQ/Work/bl-split-ep57")
FULL_FIXTURE_DIR_NAME = "generator"
RENDER_LOCK_PATH = "/tmp/bl-render.lock"


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def ssh_cmd(remote_cmd: str, **kw) -> subprocess.CompletedProcess:
    return sh(["ssh", SSH_ALIAS, remote_cmd], **kw)


# ═══════════════════════════════════════════════════════════════════════
# fixture
# ═══════════════════════════════════════════════════════════════════════

def _redact_ground_truth(build_cut_py_source: str) -> str:
    """Blank out build_cut.py's hardcoded BEATS/CHECK_ITEMS (the human
    editor's own answer for this exact window) before staging it into an
    Arm-A fixture. task-9ba58d91's own REPORT.md flagged this: the Arm A
    editor has to open build_cut.py to understand the img_placement/
    box_to_canvas coordinate contract (bl_compose.py's docstring points
    straight at it), and doing so hands them the ground truth before they
    make their own call. The two list literals are the only thing that
    matters here -- blanking them leaves every function
    load_generator_functions() actually needs untouched."""
    import ast
    tree = ast.parse(build_cut_py_source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & {"BEATS", "CHECK_ITEMS"}:
                node.value = ast.List(elts=[], ctx=ast.Load())
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def build_local_generator(stage_dir: Path, episode_work_dir: Path) -> Path:
    """build_cut.py/assemble.py (branch, read-only) + the clean template
    (already in this repo) + the episode media (this Mac's Work dir) ->
    one local generator dir, ready to scp to any host."""
    gen = stage_dir / "generator"
    if gen.exists():
        import shutil
        shutil.rmtree(gen)
    (gen / "media").mkdir(parents=True)

    for name in ("build_cut.py", "assemble.py"):
        out = gen / name
        content = sh(["git", "show", f"{GENERATOR_BRANCH}:{GENERATOR_BRANCH_PATH}/{name}"],
                     cwd=ROOT, capture_output=True, text=True).stdout
        if name == "build_cut.py":
            content = _redact_ground_truth(content)
        out.write_text(content, encoding="utf-8")

    import shutil
    for name in ("index.html", "hyperframes.json", "package.json"):
        shutil.copy2(SKILL_TEMPLATE / name, gen / name)
    shutil.copytree(SKILL_TEMPLATE / "assets", gen / "assets")

    media = episode_work_dir / "tmp" / "cut" / "media"
    shutil.copytree(media / "real", gen / "media" / "real")
    shutil.copytree(media / "third-party", gen / "media" / "third-party")
    shutil.copy2(media / "lip_a.mp4", gen / "media" / "lip_a.mp4")
    (gen / "media" / "matte").mkdir()
    shutil.copy2(media / "matte" / "lip_a-matte.webm", gen / "media" / "matte" / "lip_a-matte.webm")

    ep57_in = episode_work_dir / "in" / "ep57"
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(ep57_in / "audio-hq.mp3"),
        "-t", "31", "-c", "copy", str(gen / "media" / "voice.mp3")])
    return gen


def cmd_fixture(args: argparse.Namespace) -> int:
    stage = Path(args.stage_dir).expanduser()
    stage.mkdir(parents=True, exist_ok=True)
    episode_work_dir = Path(args.episode_work_dir).expanduser()

    build_local_generator(stage, episode_work_dir)
    (stage / "SCRIPT.tsv").write_text(SCRIPT_TSV.read_text(encoding="utf-8"), encoding="utf-8")
    for name in ("timings.tsv", "decisions.jsonl"):
        content = sh(["git", "show", f"{GENERATOR_BRANCH}:{JEV_PATH}/{name}"],
                     cwd=ROOT, capture_output=True, text=True).stdout
        (stage / name).write_text(content, encoding="utf-8")
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(episode_work_dir / "in" / "ep57" / "audio-hq.mp3"),
        "-t", "32", "-c", "copy", str(stage / "audio-hq.mp3")])

    ssh_cmd(f"mkdir -p {CONTABO_FIXTURE_DIR}")
    sh(["scp", "-rq", *(str(p) for p in stage.glob("*")), f"{SSH_ALIAS}:{CONTABO_FIXTURE_DIR}/"])
    r = ssh_cmd(f"du -sh {CONTABO_FIXTURE_DIR}", capture_output=True, text=True)
    print(r.stdout.strip())
    return 0


# ═══════════════════════════════════════════════════════════════════════
# fixture-full (the split-editor A/B's own fixture, task-1678d38e)
# ═══════════════════════════════════════════════════════════════════════
#
# `fixture` above builds a 30.78s WINDOW for the older 3-arm experiment
# (task-aae4f843) and scp's it Mac -> Contabo. This box IS Contabo already
# (CLAUDE.md: the task's own worktree lives under /opt/MoonieXHQ/Agents/Core
# on this machine) and the FULL EP57 media is already local at
# FULL_EPISODE_WORK_DIR -- so fixture-full builds straight into a local
# directory, no ssh/scp round-trip. It stages the WHOLE 153.0s episode
# (every lipsync part, every real/third-party/broll asset, the full
# SCRIPT.tsv/timings.tsv/audio-hq.mp3), unlike `fixture`'s 30.78s slice, and
# ground-truth-redacts build_cut.py exactly the same way `fixture` does --
# a segment editor gets the same coordinate-math functions, never the human
# editor's own answer for this episode.

def build_full_generator(episode_work_dir: Path, dest: Path) -> Path:
    import shutil
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "media").mkdir(parents=True)

    for name in ("build_cut.py", "assemble.py"):
        content = sh(["git", "show", f"{GENERATOR_BRANCH}:{GENERATOR_BRANCH_PATH}/{name}"],
                     cwd=ROOT, capture_output=True, text=True).stdout
        if name == "build_cut.py":
            content = _redact_ground_truth(content)
        (dest / name).write_text(content, encoding="utf-8")

    for name in ("index.html", "hyperframes.json", "package.json"):
        shutil.copy2(SKILL_TEMPLATE / name, dest / name)
    shutil.copytree(SKILL_TEMPLATE / "assets", dest / "assets")

    media_src = episode_work_dir / "media"
    for sub in ("real", "third-party", "broll", "matte"):
        src = media_src / sub
        if src.is_dir():
            shutil.copytree(src, dest / "media" / sub)
    for name in ("lip_a.mp4", "lip_b.mp4", "lip_c.mp4"):
        src = media_src / name
        if src.is_file():
            shutil.copy2(src, dest / "media" / name)

    shutil.copy2(episode_work_dir / "audio-hq.mp3", dest / "audio-hq.mp3")
    shutil.copy2(episode_work_dir / "SCRIPT.tsv", dest / "SCRIPT.tsv")
    shutil.copy2(episode_work_dir / "timings.tsv", dest / "timings.tsv")
    return dest


def cmd_fixture_full(args: argparse.Namespace) -> int:
    episode_work_dir = Path(args.episode_work_dir).expanduser()
    dest = Path(args.dest).expanduser()
    build_full_generator(episode_work_dir, dest)

    expected_mattes = {"lip_a-matte.webm", "lip_b-matte.webm", "lip_c-matte.webm"}
    matte_dir = dest / "media" / "matte"
    have = {p.name for p in matte_dir.glob("*.webm")} if matte_dir.is_dir() else set()
    missing = sorted(expected_mattes - have)
    if missing:
        print(f"WARNING: fixture-full is missing matte(s) {missing} -- a COMP-mode beat on that "
              f"lipsync part needs a fresh `bl_tools.py matte` run before it can render (§6d)")

    r = sh(["du", "-sh", str(dest)], capture_output=True, text=True)
    print(r.stdout.strip())
    print(f"fixture-full staged at {dest}")
    return 0


# ═══════════════════════════════════════════════════════════════════════
# spawn-seg (task-1678d38e) -- brief generation ONLY, never spawns
# ═══════════════════════════════════════════════════════════════════════
#
# Task rule: "Do not spawn anything; show the generated brief text in
# TOOLING.md." Unlike _spawn_arm() above (which really calls delegate_task),
# cmd_spawn_seg() only builds and prints the brief text -- it is a dry-run by
# construction, not by a flag that could be forgotten.

SEGMENT_CONTRACT_TEMPLATE = """\
**Segment contract** (PLAN.md §"Segment contract (what makes the joins invisible)") --
this is what makes your part concat cleanly with every other segment:
- Your segment covers EXACTLY [{t0}, {t1}) seconds of EP57 -- a plate must be
  on screen every frame in that range. The FIRST plate starts at {t0}. The
  LAST plate holds all the way to {t1} -- do not let it end early just
  because its own spoken line ends before {t1}; SKILL.md §6g ("a plate's
  end is the next plate's start") applies at your segment's own edges too.
  No fade in or out at either edge -- it has to cut hard into whatever comes
  before/after your segment.
- Same template, same caption style (SKILL.md §6f -- use the template's
  own `caption()` generator, never a hand-rolled style or a mode-based
  chip/rail/strip -- that is the exact bug this fix exists to prevent), same
  encoder settings (1080x1920, 30fps) as every other segment, so every
  segment concats with `ffmpeg -c copy`, no re-encode.
- **Render VIDEO ONLY -- no audio track.** The master narration audio is
  muxed once, across the WHOLE episode, by the CTO's `tools/bl_merge.py` at
  merge time. An audio track baked into your segment would only be discarded
  -- do not spend time syncing/exporting one.
- Before you render (`npm run render` / `npx hyperframes render`), take the
  render lock so your render never overlaps another segment editor's on this
  4-core/7GB box: `flock {render_lock} npm run render`. Hold the SAME lock
  for `npm run check`/`hyperframes snapshot` too if you run them concurrently
  with another segment's render -- the lock, not a schedule, is what keeps
  renders serialized.
"""


def _segment_brief(seg: dict, fixture_dir: str, seg_index: int, seg_count: int) -> str:
    tags = ", ".join(l["tag"] for l in seg["lines"]) or "(no script lines fall in this window)"
    lines_desc = "\n".join(
        f"  - `{l['tag']}` [{l['t0']}, {l['t1']}]: {l.get('text', '')}" for l in seg["lines"]
    )
    return f"""You are cutting BLACK LIQUIDITY EP57, segment {seg['id']} ({seg_index} of {seg_count}
segments) -- seconds {seg['t0']} to {seg['t1']} ({seg['frame_count']} frames at 30fps). This is Arm 2
("ช่วยกัน") of the split-editor A/B (docs/ops/bl-split-ab-2026-09-25/PLAN.md, CEO 2026-09-25): N editors
each cut one segment in parallel from the SAME fixed skill + template, and the CTO
concats/merges the parts afterward with `tools/bl_merge.py` -- you never see or touch any
other segment. Follow the `blackliquidity-cut` skill's normal pipeline (SKILL.md) end to
end, scoped to your segment only -- steps 1-9 apply exactly as written (transcribe/measure/
normalise/write the cut/gate/look/render/verify), except step 10 (delivery) is replaced by
the push instructions below, and there is no step 5 lipsync-offset search: this fixture's
`SCRIPT.tsv`/`timings.tsv` already carry every line's true wording and exact timing.

**Source material** (all under `{fixture_dir}`, already staged on this box):
- `SCRIPT.tsv` / `timings.tsv` -- every script line's tag, Thai text, shot name, Jev verb
  and exact [t0,t1], for the WHOLE episode (read only the rows inside your window, listed
  below for convenience).
- `media/real/*`, `media/third-party/*`, `media/broll/*.mp4` -- every real-footage still,
  third-party credit image and B-roll clip the full episode uses.
- `media/lip_a.mp4`, `lip_b.mp4`, `lip_c.mp4` + `media/matte/*-matte.webm` -- the avatar's
  real lipsync footage and its pre-matted overlay (SKILL.md §6d). If your window needs a
  matte that is missing from this fixture, say so in REPORT.md rather than skipping the
  composite -- do not fall back to full-frame avatar just because the matte isn't there.
- `index.html` -- the FIXED template (task-1678d38e): one `.cap` style everywhere (§6f),
  `caption(at, out, text)` generator, plates-hold-until-next-plate is now the rule (§6g).
  Copy it into your own workdir per SKILL.md step 6 -- do not hand-roll captions.
- `build_cut.py`/`assemble.py` (read-only, ground-truth redacted) -- for the pure coordinate
  math ONLY (`img_placement`/`box_to_canvas`/`pick_lip`/`lip_offset`) if you want it; their
  own `BEATS`/`CHECK_ITEMS` lists are blanked out on purpose -- make your own editorial
  calls, the same as any BL editor would.

**Your window's script lines:**
{lines_desc if seg['lines'] else '  (none -- this segment is pure B-roll/kinetic, no spoken line starts inside it)'}

{SEGMENT_CONTRACT_TEMPLATE.format(t0=seg['t0'], t1=seg['t1'], render_lock=RENDER_LOCK_PATH)}
**Write** your composition to `prototypes/bl-split-ep57/{seg['id']}/index.html` (in your own
worktree) and render `prototypes/bl-split-ep57/{seg['id']}/{seg['id']}.mp4`.

**Render** (inside your composition's own workdir):
```
flock {RENDER_LOCK_PATH} npx hyperframes@0.8.40 render -o {seg['id']}.mp4
```

**Verify by eye**: pull frames at a few representative timestamps inside [{seg['t0']},
{seg['t1']}) and actually look at them -- caption readable and in the one approved style,
no empty/black frames, nothing on screen ends before the NEXT plate in your window starts.
Then run `python3 tools/bl_checker.py --video {seg['id']}.mp4 --beats <your beats/description>
--composition index.html` and report its verdict.

**Push** (git add/commit/push on your task branch): your composition's `index.html`, a small
`render-meta.json` (path/size/duration/fps via `ffprobe`) -- **not the mp4 itself, media never
goes in git.** Copy `{seg['id']}.mp4` to `/opt/MoonieXHQ/Work/bl-split-ep57/parts/{seg['id']}.mp4`
and your composed `index.html` to `/opt/MoonieXHQ/Work/bl-split-ep57/compositions/{seg['id']}.html`
(outside your worktree -- `merge_task` deletes it, and `tools/bl_merge.py --parts .../parts
--compositions .../compositions` reads directly from there).

Report in REPORT.md: which lines you called COMP/EVID/FF/KIN and why, whether your window's
first/last plate lands exactly on {seg['t0']}/{seg['t1']} with no fade, and the checker verdict.
"""


def cmd_spawn_seg(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.segments).read_text(encoding="utf-8"))
    segments = data["segments"] if isinstance(data, dict) else data
    matches = [s for s in segments if s["id"] == args.seg]
    if not matches:
        ids = [s["id"] for s in segments]
        print(f"error: segment {args.seg!r} not found in {args.segments} (have: {ids})", file=sys.stderr)
        return 1
    seg = matches[0]
    seg_index = segments.index(seg) + 1
    brief = _segment_brief(seg, args.fixture_dir, seg_index, len(segments))
    print(brief)
    print(f"--- DRY RUN: brief generated for {seg['id']} ({seg['t0']}-{seg['t1']}s), "
          f"NOT spawned. Task rule: spawn-seg never calls delegate_task. ---")
    return 0


# ═══════════════════════════════════════════════════════════════════════
# spawn-a / spawn-b
# ═══════════════════════════════════════════════════════════════════════

def _brief_from_readme(arm: str) -> str:
    text = (ARMS_DIR / arm / "README.md").read_text(encoding="utf-8")
    return text.split("## Brief given to the worker\n\n", 1)[1]


def _spawn_arm(arm: str, title: str, touches: list[str], owner_cto: str) -> str:
    from lib import db
    from tools.delegate import delegate_task
    import asyncio

    task_id = db.create_task(
        project="mooniex-agents", role="video_editor", title=title,
        description=_brief_from_readme(arm), touches=touches,
        owner_cto=owner_cto, owner_role="cto", host="contabo",
    )
    result = asyncio.run(delegate_task(task_id, host="contabo"))
    print(f"arm {arm}: task={task_id} status={result.get('status')} "
          f"pid={result.get('pid')} tmux={result.get('tmux_session')} "
          f"worktree={result.get('worktree')} branch={result.get('branch')}")
    return task_id


def cmd_spawn_a(args: argparse.Namespace) -> int:
    _spawn_arm("A", "BL A/B/C Arm A -- cut EP57 0-30.78s by eye",
              ["prototypes/bl-ab-ep57/A/"], args.owner_cto)
    return 0


def cmd_spawn_b(args: argparse.Namespace) -> int:
    _spawn_arm("B", "BL A/B/C Arm B -- blind build from Scripter beats.json",
              ["prototypes/bl-ab-ep57/B/"], args.owner_cto)
    return 0


def cmd_push_tool(args: argparse.Namespace) -> int:
    sh(["scp", "-q", str(ROOT / "tools" / "bl_compose.py"),
        f"{SSH_ALIAS}:{args.worktree}/tools/bl_compose.py"])
    return 0


# ═══════════════════════════════════════════════════════════════════════
# collect
# ═══════════════════════════════════════════════════════════════════════

def cmd_collect(args: argparse.Namespace) -> int:
    arm = args.arm
    out_dir = Path(args.work_dir).expanduser() / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    arm_dir = out_dir / arm
    arm_dir.mkdir(exist_ok=True)

    sh(["git", "fetch", "origin", args.branch], cwd=ROOT)
    for name in ("REPORT.md", f"prototypes/bl-ab-ep57/{arm}/beats.json",
                 f"prototypes/bl-ab-ep57/{arm}/render-meta.json",
                 f"prototypes/bl-ab-ep57/{arm}/checker-result.json"):
        r = subprocess.run(["git", "show", f"origin/{args.branch}:{name}"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 0:
            dest = arm_dir / Path(name).name
            dest.write_text(r.stdout, encoding="utf-8")
            print(f"collected {name} -> {dest}")
        else:
            print(f"not on branch (ok if not applicable): {name}")

    remote_mp4 = f"{CONTABO_FIXTURE_DIR}/{arm}/final-{arm}.mp4"
    sh(["scp", "-q", f"{SSH_ALIAS}:{remote_mp4}", str(arm_dir / f"final-{arm}.mp4")])

    if args.worktree:
        # Claude Code's project slug replaces BOTH "/" and "_" with "-"
        # (a worktree path with a double underscore like
        # ..._video_editor__task-X becomes ...-video-editor--task-X).
        slug = args.worktree.strip("/").replace("/", "-").replace("_", "-")
        r2 = ssh_cmd(f"ls -t /root/.claude/projects/-{slug}/*.jsonl 2>/dev/null | head -1",
                    capture_output=True, text=True)
        session_file = r2.stdout.strip() or None
        if session_file:
            sh(["scp", "-q", f"{SSH_ALIAS}:{session_file}", str(arm_dir / "transcript.jsonl")])
        else:
            print("no transcript found automatically -- scp it by hand if needed for scoring")
    return 0


# ═══════════════════════════════════════════════════════════════════════
# run-c (no worker)
# ═══════════════════════════════════════════════════════════════════════

def cmd_run_c(args: argparse.Namespace) -> int:
    out_dir = Path(args.work_dir).expanduser() / "out" / "C"
    out_dir.mkdir(parents=True, exist_ok=True)

    remote_c = f"{CONTABO_FIXTURE_DIR}/C"
    ssh_cmd(f"mkdir -p {remote_c}")
    ssh_cmd(f"cp {args.repo_path}/docs/ops/bl-ab-2026-09-25/beats.json {remote_c}/beats.json")
    sh(["scp", "-q", str(ROOT / "tools" / "bl_compose.py"), f"{SSH_ALIAS}:{args.repo_path}/tools/bl_compose.py"])

    ssh_cmd(
        f"cd {args.repo_path} && python3 tools/bl_compose.py "
        f"--beats {remote_c}/beats.json --generator-dir {CONTABO_FIXTURE_DIR}/generator "
        f"--t-max {T_MAX} --audio {CONTABO_FIXTURE_DIR}/audio-hq.mp3 "
        f"--out-dir {remote_c}/build --out {remote_c}/final-C.mp4"
    )
    ssh_cmd(
        f"cd {args.repo_path} && python3 tools/bl_checker.py "
        f"--video {remote_c}/final-C.mp4 --beats {remote_c}/beats.json "
        f"--out {remote_c}/checker-result.json"
    )
    for name in ("beats.json", "checker-result.json", "final-C.mp4"):
        sh(["scp", "-q", f"{SSH_ALIAS}:{remote_c}/{name}", str(out_dir / name)])
    return 0


# ═══════════════════════════════════════════════════════════════════════
# score
# ═══════════════════════════════════════════════════════════════════════

def cmd_score(args: argparse.Namespace) -> int:
    from tools import bl_score

    out_dir = Path(args.work_dir).expanduser() / "out"
    truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    (ARMS_DIR / "scores.md").parent.mkdir(parents=True, exist_ok=True)

    sections = []
    for arm in ("A", "B", "C"):
        beats_path = out_dir / arm / "beats.json"
        if not beats_path.is_file():
            sections.append(f"## Arm {arm}\n\n(not collected -- run `collect`/`run-c` first)\n")
            continue
        beats = json.loads(beats_path.read_text(encoding="utf-8"))
        result = bl_score.score(beats, truth)
        usage = None
        usage_path = out_dir / arm / "scripter_usage.json"
        transcript_path = out_dir / arm / "transcript.jsonl"
        if usage_path.is_file():
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
        elif transcript_path.is_file():
            from tools.bl_scripter import usage_from_transcript, _cost_from_token_dict
            t = usage_from_transcript(transcript_path)
            usage = {"backend": "claude-p", "turns": t["turns"], "tokens": t["tokens"],
                     "cost_usd_api_equivalent": round(_cost_from_token_dict(t["tokens"]), 6)}
        md = bl_score.render_markdown(result, usage)
        checker_path = out_dir / arm / "checker-result.json"
        if checker_path.is_file():
            checker = json.loads(checker_path.read_text(encoding="utf-8"))
            md += f"\n\n## Checker verdict\n\n```json\n{json.dumps(checker, indent=2, ensure_ascii=False)}\n```\n"
        sections.append(f"## Arm {arm}\n\n{md}\n")

    out_md = "# BL Editor A/B/C -- per-arm scores (task-aae4f843)\n\n" + "\n".join(sections)
    (ARMS_DIR / "scores.md").write_text(out_md, encoding="utf-8")
    print(f"wrote {ARMS_DIR / 'scores.md'}")
    return 0


# ═══════════════════════════════════════════════════════════════════════

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fixture")
    p.add_argument("--stage-dir", default="~/MoonieXHQ/Work/bl-ab-fixture-stage")
    p.add_argument("--episode-work-dir", required=True, help="e.g. ~/MoonieXHQ/Work/task-501f1d89")
    p.set_defaults(func=cmd_fixture)

    p = sub.add_parser("fixture-full", help="stage the FULL 153s EP57 fixture, local to this box")
    p.add_argument("--episode-work-dir", default=str(FULL_EPISODE_WORK_DIR),
                    help="dir holding audio-hq.mp3/SCRIPT.tsv/timings.tsv/media/ (default: the real box path)")
    p.add_argument("--dest", default=str(FULL_EPISODE_WORK_DIR / FULL_FIXTURE_DIR_NAME),
                    help="where to stage the generator (default: <episode-work-dir>/generator)")
    p.set_defaults(func=cmd_fixture_full)

    p = sub.add_parser("spawn-seg", help="print (never spawn) one segment editor's brief")
    p.add_argument("--segments", required=True, help="segments.json from tools/bl_split.py")
    p.add_argument("--seg", required=True, help="segment id, e.g. seg01")
    p.add_argument("--fixture-dir", default=str(FULL_EPISODE_WORK_DIR / FULL_FIXTURE_DIR_NAME),
                    help="path a spawned editor would read the fixture-full from")
    p.set_defaults(func=cmd_spawn_seg)

    p = sub.add_parser("spawn-a")
    p.add_argument("--owner-cto", required=True)
    p.set_defaults(func=cmd_spawn_a)

    p = sub.add_parser("spawn-b")
    p.add_argument("--owner-cto", required=True)
    p.set_defaults(func=cmd_spawn_b)

    p = sub.add_parser("push-tool")
    p.add_argument("--worktree", required=True, help="remote worktree path on Contabo")
    p.set_defaults(func=cmd_push_tool)

    p = sub.add_parser("collect")
    p.add_argument("--arm", required=True, choices=["A", "B"])
    p.add_argument("--branch", required=True)
    p.add_argument("--worktree", default=None, help="remote worktree path, for transcript collection")
    p.add_argument("--work-dir", required=True)
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("run-c")
    p.add_argument("--work-dir", required=True)
    p.add_argument("--repo-path", default="/opt/mooniex-agents", help="Contabo's main checkout path")
    p.set_defaults(func=cmd_run_c)

    p = sub.add_parser("score")
    p.add_argument("--work-dir", required=True)
    p.set_defaults(func=cmd_score)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
