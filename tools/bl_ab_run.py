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
    spawn-full  print (NEVER spawn) Arm 1's whole-episode brief, verbatim
                from docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md
                (task-99f3d2e8: both arms now route through Arm A's own
                bl_compose.py/beats.json workflow, CTO ruling 2026-09-25).
    spawn-seg   print (NEVER spawn) one segment editor's brief, from the
                BRIEF-seg.md template (word-for-word identical to
                BRIEF-arm1.md outside the range + segment contract) filled
                in with that segment's own [t0,t1) window and tags.
                Requires a segments.json from tools/bl_split.py.

Usage:
    python3 tools/bl_ab_run.py fixture --episode-work-dir ~/MoonieXHQ/Work/task-501f1d89
    python3 tools/bl_ab_run.py spawn-a --owner-cto 91a17eb2
    python3 tools/bl_ab_run.py push-tool --worktree <remote worktree path>
    python3 tools/bl_ab_run.py collect --arm A --branch agent/video_editor-task-XXXX \\
        --worktree <remote worktree path> --work-dir ~/MoonieXHQ/Work/task-XXXX
    python3 tools/bl_ab_run.py run-c --work-dir ~/MoonieXHQ/Work/task-XXXX
    python3 tools/bl_ab_run.py score --work-dir ~/MoonieXHQ/Work/task-XXXX
    python3 tools/bl_ab_run.py fixture-full
    python3 tools/bl_ab_run.py spawn-full
    python3 tools/bl_ab_run.py spawn-seg --segments segments.json --seg seg01
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.bl_compose import frame_floor, load_generator_functions, load_script_line_map  # noqa: E402

SSH_ALIAS = "mooniex-vps"
CONTABO_FIXTURE_DIR = "/opt/MoonieXHQ/Work/bl-ab-ep57"
SKILL_TEMPLATE = ROOT / ".claude" / "skills" / "CMO_Procedure_BlackLiquidity_Cut" / "template"
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

# ── per-episode values (EP58, task-ee30ba95) ────────────────────────────────────
# The generator (build_cut.py/assemble.py from GENERATOR_BRANCH) was written for
# EP57 and carries three EP57-only values: the avatar windows (lip_offset/
# LIP_DUR/pick_lip), TOTAL_DUR, and the date on the brand bug. An episode work
# dir that holds `offsets.json` (bl_tools.py offsets' own output) and
# `episode.json` ({"episode": N, "date": "YYYY-MM-DD"}) gets its own values
# written into the staged copies; a dir without them (EP57's) is staged exactly
# as before.

LIP_DUR_MARGIN = 0.05        # EP57's own LIP_DUR = video length - 0.05..0.08, on the 0.05 s grid
LIP_DUR_TOLERANCE = 0.2      # check_lip_windows: a LIP_DUR further than this from its file is not this episode's
THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
EP57_BRAND_BUG_DATE = '<div class="dt2">23 ก.ย. 69</div>'   # assemble.py's own hardcoded replacement


def _video_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def _decoded_audio_seconds(path: Path) -> float:
    """What the decoder really delivers -- the clock the render plays -- not the container header's figure
    (EP58's mp3 header says 95.7388 s, the decode is 95.7009 s)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "8000", "-"],
                         capture_output=True, check=True).stdout
    return len(raw) / 2 / 8000


def thai_short_date(iso: str) -> str:
    """'2026-10-01' -> '1 ต.ค. 69' (the brand bug's format: day, month, Buddhist year mod 100)."""
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {THAI_MONTHS[m - 1]} {(y + 543) % 100:02d}"


def episode_meta(episode_work_dir: Path) -> dict:
    path = episode_work_dir / "episode.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def lip_layout(episode_work_dir: Path) -> dict | None:
    """This episode's avatar windows, from bl_tools.py offsets' offsets.json (parts A/B/C -> lip_a/b/c) and the
    length of the normalised media/lip_*.mp4. None when there is no offsets.json (EP57: keep build_cut.py's own)."""
    offsets_path = episode_work_dir / "offsets.json"
    if not offsets_path.is_file():
        return None
    offset: dict[str, float] = {}
    dur: dict[str, float] = {}
    for part in json.loads(offsets_path.read_text(encoding="utf-8")):
        name = f"lip_{part['part'].lower()}"
        if part.get("r", 1.0) < 0.9:
            raise SystemExit(f"fixture-full refused: {offsets_path} matched part {part['part']} weakly "
                             f"(r={part['r']}) -- bl_tools.py says do not seat it until a human confirms")
        media = episode_work_dir / "media" / f"{name}.mp4"
        if not media.is_file():
            raise SystemExit(f"fixture-full refused: {offsets_path} names part {part['part']} but {media} is missing "
                             f"-- LIP_DUR cannot be derived, and silently keeping EP57's windows is the bug this guards")
        offset[name] = float(part["true_s"])
        dur[name] = round(math.floor((_video_duration(media) - LIP_DUR_MARGIN) / 0.05 + 1e-6) * 0.05, 2)
    total = round(frame_floor(_decoded_audio_seconds(episode_work_dir / "audio-hq.mp3")), 4)
    return {"offset": offset, "dur": dur, "total": total}


def _apply_lip_layout(source: str, layout: dict) -> str:
    """Replace build_cut.py's lip_offset / LIP_DUR / pick_lip / TOTAL_DUR with this episode's own. pick_lip hands
    a t0 to the latest take that starts at or before it; bl_compose.check_avatar_window then refuses a t0 that
    runs past that take's end, naming every window."""
    import ast
    names = sorted(layout["offset"], key=lambda n: layout["offset"][n])
    pick = "def pick_lip(t0):\n" + "".join(
        f"    if t0 < {layout['offset'][nxt]!r}:\n        return {cur!r}\n" for cur, nxt in zip(names, names[1:]))
    pick += f"    return {names[-1]!r}\n"
    new = {
        "lip_offset": ast.parse(f"def lip_offset(src):\n    return {layout['offset']!r}[src]\n").body[0],
        "LIP_DUR": ast.parse(f"LIP_DUR = {layout['dur']!r}").body[0],
        "pick_lip": ast.parse(pick).body[0],
        "TOTAL_DUR": ast.parse(f"TOTAL_DUR = {layout['total']!r}").body[0],
    }
    tree = ast.parse(source)
    done = set()
    for i, node in enumerate(tree.body):
        key = node.name if isinstance(node, ast.FunctionDef) else next(
            (t.id for t in getattr(node, "targets", []) if isinstance(t, ast.Name)), None)
        if key in new:
            tree.body[i] = new[key]
            done.add(key)
    if done != set(new):
        raise SystemExit(f"build_cut.py has no top-level {sorted(set(new) - done)} to rewrite -- the generator changed")
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _apply_episode_date(source: str, iso_date: str) -> str:
    if source.count(EP57_BRAND_BUG_DATE) != 1:
        raise SystemExit(f"assemble.py no longer carries exactly one {EP57_BRAND_BUG_DATE!r} -- the generator changed")
    return source.replace(EP57_BRAND_BUG_DATE, f'<div class="dt2">{thai_short_date(iso_date)}</div>')


def check_broll_coverage(dest: Path) -> list[str]:
    """bl_compose defaults a bare KIN beat to media/broll/S{row:02d}.mp4. A scene the generator never finished (EP58:
    S08, S28 -- Drive manifest scenes.status = partial, 38/40) leaves that default pointing at nothing."""
    have = {p.name for p in (dest / "media" / "broll").glob("S*.mp4")}
    if not have:
        return []
    absent = sorted((n, tag) for tag, n in load_script_line_map(dest).items() if f"S{n:02d}.mp4" not in have)
    return [f"WARNING: media/broll has no S{n:02d}.mp4 ({tag}) -- a KIN beat on that line must name its own "
            f"`broll` (or opt out with a falsy one); the default plate would not exist" for n, tag in absent]


def check_lip_windows(dest: Path) -> list[str]:
    """Warnings when the staged build_cut.py's LIP_DUR does not fit the staged media/lip_*.mp4 -- the signature of
    another episode's windows (EP57's) sitting on this episode's lipsync parts."""
    warnings = []
    for name, want in sorted((load_generator_functions(dest).get("LIP_DUR") or {}).items()):
        media = dest / "media" / f"{name}.mp4"
        if not media.is_file():
            warnings.append(f"WARNING: build_cut.py has a window for {name} but media/{name}.mp4 is not staged")
            continue
        have = _video_duration(media)
        if abs(have - want) > LIP_DUR_TOLERANCE:
            warnings.append(f"WARNING: build_cut.py says {name} lasts {want:g}s but media/{name}.mp4 is {have:.2f}s "
                            f"-- these windows are not this episode's (add offsets.json + episode.json to the work dir)")
    return warnings


def build_full_generator(episode_work_dir: Path, dest: Path, force: bool = False) -> Path:
    """Build the generator into a staging dir, then swap it in.

    task-9a4f1029 incident: the old version rmtree'd `dest` first and rebuilt
    from `episode_work_dir`, silently deleting 37 scene clips the CTO had
    staged straight into dest/media/broll. Now nothing in `dest` is deleted
    unless the rebuild recreates it; otherwise it refuses and names the files
    (put them under `episode_work_dir`, the source, or pass force=True).
    """
    import shutil
    stage = dest.parent / (dest.name + ".staging")
    if stage.exists():
        shutil.rmtree(stage)
    _build_generator_into(episode_work_dir, stage)
    if dest.exists():
        old = {p.relative_to(dest) for p in dest.rglob("*") if p.is_file()}
        new = {p.relative_to(stage) for p in stage.rglob("*") if p.is_file()}
        lost = sorted(str(p) for p in old - new)
        if lost and not force:
            shutil.rmtree(stage)
            raise SystemExit(
                f"fixture-full refused: rebuilding {dest} would delete {len(lost)} file(s) "
                f"the rebuild does not recreate, e.g. {lost[:8]}. Move them under "
                f"{episode_work_dir} (the source) or re-run with --force.")
        shutil.rmtree(dest)
    stage.rename(dest)
    return dest


def _build_generator_into(episode_work_dir: Path, dest: Path) -> Path:
    import shutil
    (dest / "media").mkdir(parents=True)

    layout = lip_layout(episode_work_dir)
    date = episode_meta(episode_work_dir).get("date")
    for name in ("build_cut.py", "assemble.py"):
        content = sh(["git", "show", f"{GENERATOR_BRANCH}:{GENERATOR_BRANCH_PATH}/{name}"],
                     cwd=ROOT, capture_output=True, text=True).stdout
        if name == "build_cut.py":
            content = _redact_ground_truth(content)
            if layout:
                content = _apply_lip_layout(content, layout)
        elif date:
            content = _apply_episode_date(content, date)
        (dest / name).write_text(content, encoding="utf-8")

    for name in ("index.html", "hyperframes.json", "package.json"):
        shutil.copy2(SKILL_TEMPLATE / name, dest / name)
    shutil.copytree(SKILL_TEMPLATE / "assets", dest / "assets")
    # real/REAL_MANIFEST.json (+ shots.yaml): SKILL.md 5a says read it before placing anything; the brief's Jev
    # command points at generator/real/REAL_MANIFEST.json. The stills themselves stay in media/real.
    if (episode_work_dir / "real").is_dir():
        shutil.copytree(episode_work_dir / "real", dest / "real")

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
    # assemble.py (off-limits, never edited) hardcodes the composed <audio>
    # element's src to "media/voice.mp3" regardless of what's actually in
    # the fixture -- this was never staged here (the CTO copied it by hand
    # for task-1a5eb073's pilot, which then had to work around the missing
    # file per-render instead). audio-hq.mp3 IS the episode's real
    # narration track (SKILL.md: "this is the clock"), so it's the correct
    # source for the placeholder assemble.py expects.
    shutil.copy2(episode_work_dir / "audio-hq.mp3", dest / "media" / "voice.mp3")
    shutil.copy2(episode_work_dir / "SCRIPT.tsv", dest / "SCRIPT.tsv")
    shutil.copy2(episode_work_dir / "timings.tsv", dest / "timings.tsv")
    # Jev's frozen answers (decisions.base.jsonl / .frozen.json) live in the
    # source's jev/ -- stage them too, so a rebuild never drops them.
    if (episode_work_dir / "jev").is_dir():
        shutil.copytree(episode_work_dir / "jev", dest / "jev")
    return dest


def cmd_fixture_full(args: argparse.Namespace) -> int:
    episode_work_dir = Path(args.episode_work_dir).expanduser()
    dest = Path(args.dest).expanduser() if args.dest else episode_work_dir / FULL_FIXTURE_DIR_NAME
    build_full_generator(episode_work_dir, dest, force=getattr(args, "force", False))

    expected_mattes = {"lip_a-matte.webm", "lip_b-matte.webm", "lip_c-matte.webm"}
    matte_dir = dest / "media" / "matte"
    have = {p.name for p in matte_dir.glob("*.webm")} if matte_dir.is_dir() else set()
    missing = sorted(expected_mattes - have)
    if missing:
        print(f"WARNING: fixture-full is missing matte(s) {missing} -- a COMP-mode beat on that "
              f"lipsync part needs a fresh `bl_tools.py matte` run before it can render (§6d)")

    funcs = load_generator_functions(dest)
    windows = ", ".join(f"{n} [{funcs['lip_offset'](n):g}, {funcs['lip_offset'](n) + d:g})"
                        for n, d in sorted(funcs["LIP_DUR"].items(), key=lambda kv: funcs["lip_offset"](kv[0])))
    print(f"avatar windows bl_compose will enforce: {windows}")
    for warning in check_lip_windows(dest) + check_broll_coverage(dest):
        print(warning)

    r = sh(["du", "-sh", str(dest)], capture_output=True, text=True)
    print(r.stdout.strip())
    print(f"fixture-full staged at {dest}")
    return 0


# ═══════════════════════════════════════════════════════════════════════
# spawn-full / spawn-seg (task-99f3d2e8) -- brief generation ONLY, never
# spawns. Both arms now route through Arm A's own bl_compose.py/beats.json
# workflow (CTO ruling 2026-09-25: "both arms use the Arm A route") --
# BRIEF-arm1.md and BRIEF-seg.md carry that brief verbatim, word-for-word
# identical outside the range description and BRIEF-seg.md's own "Segment
# contract" section. Neither command calls delegate_task; it is a dry run
# by construction, not by a flag that could be forgotten.
# ═══════════════════════════════════════════════════════════════════════

BRIEF_ARM1_PATH = ROOT / "docs" / "ops" / "bl-split-ab-2026-09-25" / "BRIEF-arm1.md"
BRIEF_SEG_PATH = ROOT / "docs" / "ops" / "bl-split-ab-2026-09-25" / "BRIEF-seg.md"


def _brief_body(path: Path) -> str:
    """Strips the file's own leading explainer (everything above the '---'
    rule) -- what a spawned worker actually needs starts at '## Brief given
    to the worker'."""
    text = path.read_text(encoding="utf-8")
    marker = "## Brief given to the worker"
    return text[text.index(marker):]


def _episode_brief(body: str, work_dir: Path) -> str:
    """BRIEF-arm1.md is written for EP57. For another episode, swap in that episode's number, paths, t-max and the
    avatar windows exactly as its staged generator enforces them -- and fail loudly if the brief stopped
    containing one of the EP57 strings, instead of printing EP57 text for EP58."""
    ep = episode_meta(work_dir).get("episode")
    if ep is None:
        raise SystemExit(f"{work_dir}/episode.json with {{\"episode\": N}} is required for a non-EP57 brief")
    funcs = load_generator_functions(work_dir / FULL_FIXTURE_DIR_NAME)
    t_max = frame_floor(_decoded_audio_seconds(work_dir / "audio-hq.mp3"))
    lips = sorted(funcs["LIP_DUR"].items(), key=lambda kv: funcs["lip_offset"](kv[0]))
    ep57_windows = ["[0, 14.9)", "[68.3, 82.95)", "[137.16, 152.51)"]
    subs = [("episode 57", f"episode {ep}"), ("153.0333", f"{t_max:g}"),
            (str(FULL_EPISODE_WORK_DIR), str(work_dir)), ("prototypes/bl-split-ep57/", f"prototypes/bl-ep{ep}/")]
    subs += [(old, f"[{funcs['lip_offset'](n):g}, {funcs['lip_offset'](n) + d:g})")
             for old, (n, d) in zip(ep57_windows, lips)]
    for old, new in subs:
        if old not in body:
            raise SystemExit(f"BRIEF-arm1.md no longer contains {old!r} -- update _episode_brief")
        body = body.replace(old, new)
    return body


def cmd_spawn_full(args: argparse.Namespace) -> int:
    work_dir = getattr(args, "episode_work_dir", None)
    if work_dir and Path(work_dir).expanduser() != FULL_EPISODE_WORK_DIR:
        print(_episode_brief(_brief_body(BRIEF_ARM1_PATH), Path(work_dir).expanduser()))
    else:
        print(_brief_body(BRIEF_ARM1_PATH))
    print("--- DRY RUN: BRIEF-arm1.md printed verbatim, NOT spawned. "
          "Task rule: spawn-full never calls delegate_task. ---")
    return 0


def cmd_spawn_seg(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.segments).read_text(encoding="utf-8"))
    segments = data["segments"] if isinstance(data, dict) else data
    matches = [s for s in segments if s["id"] == args.seg]
    if not matches:
        ids = [s["id"] for s in segments]
        print(f"error: segment {args.seg!r} not found in {args.segments} (have: {ids})", file=sys.stderr)
        return 1
    seg = matches[0]
    tags = ", ".join(l["tag"] for l in seg["lines"]) or "(no script lines fall in this window)"
    template = _brief_body(BRIEF_SEG_PATH)
    # Plain substring replace, NOT str.format() -- the brief's own body is
    # full of literal JSON-shaped curly braces (beats.json's own
    # {"tag","t0",...} shape, extra:{...} examples) that .format() would
    # try to parse as fields and fail on.
    brief = (template
             .replace("{seg}", seg["id"])
             .replace("{t0}", str(seg["t0"]))
             .replace("{t1}", str(seg["t1"]))
             .replace("{tags}", tags))
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
    p.add_argument("--dest", default=None,
                    help="where to stage the generator (default: <episode-work-dir>/generator -- never another "
                         "episode's, so --episode-work-dir alone cannot rebuild EP57's generator under EP58's media)")
    p.add_argument("--force", action="store_true",
                    help="allow the rebuild to delete files in --dest that it does not recreate")
    p.set_defaults(func=cmd_fixture_full)

    p = sub.add_parser("spawn-full", help="print (never spawn) Arm 1's whole-episode brief (BRIEF-arm1.md)")
    p.add_argument("--episode-work-dir", default=None,
                    help="another episode's work dir (needs episode.json + a staged generator/): swaps its number, "
                         "paths, t-max and avatar windows into the EP57 brief (default: the EP57 brief as written)")
    p.set_defaults(func=cmd_spawn_full)

    p = sub.add_parser("spawn-seg", help="print (never spawn) one segment editor's brief (BRIEF-seg.md)")
    p.add_argument("--segments", required=True, help="segments.json from tools/bl_split.py")
    p.add_argument("--seg", required=True, help="segment id, e.g. seg01")
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
    p.add_argument("--repo-path", default="/opt/MoonieXHQ/Agents/Core", help="Contabo's main checkout path")
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
