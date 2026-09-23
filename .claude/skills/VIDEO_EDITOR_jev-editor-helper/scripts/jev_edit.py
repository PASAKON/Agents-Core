#!/usr/bin/env python3
"""jev_edit.py — run Jev per BLACK LIQUIDITY script line for the per-line
editorial calls a human editor used to make by eye (task-5cfe20b1, CEO
ruling 2026-09-23: "ให้ JEV Model ช่วยตัดสินใจแทน Editor — Editor ใส่ข้อมูลให้
JEV และทำตามที่ JEV ตัดสินใจให้"). Calls the org's production decision path,
tools/decide.py's decide() — never a raw HTTP call — so budget gating,
provider ladder and the ledger all apply exactly as for every other site.

Six sites (config/decisions/bl.*.yaml), asked per line in order:
  bl.beat          hook / show / verdict / cta / other      — always asked
  bl.entry         shrink / hard_cut / other                — lines after the first
  bl.focus_device  spotlight / highlight_sweep / zoom_only / none / other
                                                              — only when beat == show
  bl.focus_target  A-F / other (REAL_MANIFEST evidence boxes) — only when a
                                                              device was chosen and
                                                              candidates exist
  bl.highlight_word A-F / other (numbers/words/brands in the line)
                                                              — only when candidates exist
  bl.text_slot     A-F / other (free text rectangles)         — only when candidates exist

See SKILL.md for the full design and jev-ops SKILL.md for what a Jev call
costs and why. State passed to every site is DATA (jev-ops HARD rule 3) —
script/web text never becomes an option; the options are always the ones
declared in config/decisions/bl.*.yaml.

CLI:
    python3 jev_edit.py plan <script.tsv> [--manifest REAL_MANIFEST.json]
        [--gate 0.7] [--state-lang en|th] [--max-calls N] [--max-usd F]
        --out decisions.jsonl
    python3 jev_edit.py storyboard decisions.jsonl --out storyboard.html
    python3 jev_edit.py eval <groundtruth.tsv> [--reps 2] [--gate 0.7]
        [--state-lang en|th]
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ROOT = SKILL_DIR.parent.parent.parent  # .claude/skills/<name>/ -> repo root
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # for jev_edit_lib

import jev_edit_lib as lib  # noqa: E402
from tools import decide as decide_mod  # noqa: E402

BRAND_MAP_PATH = ROOT / ".claude" / "skills" / "blackliquidity-cut" / "brand-display.yaml"

# jev-ops SKILL.md's own gate: "kept 80% of answers and let zero wrong ones
# through" at 0.7, "replaced by what your eval measures" per the task brief.
DEFAULT_GATE = 0.7

# HARD (jev-ops rule 1 / task brief): every loop that calls Jev carries its
# own call ceiling and dollar cap, on top of tools/decide.py's monthly
# DECIDE_BUDGET_USD. TASK_BUDGET_CAP_USD is the task's own hard number —
# $0.05 for EVERYTHING this task spends, not per invocation (CTO review
# 2026-09-23: "Cap: $0.05 total for this task, including the $0.014 already
# spent"). Both `plan` and `eval` size their default --max-usd off the
# TRUE remaining balance (task cap minus this task's own ledger spend so
# far), not a fresh $0.05 every run.
TASK_BUDGET_CAP_USD = 0.05
EVAL_MAX_CALLS = 2000
PLAN_MAX_CALLS_DEFAULT = 2000


def _task_spend_so_far_usd() -> float:
    """Sum of cost_usd across every bl.* row this worktree's ledger has ever
    written (state/decisions/*.jsonl) — the same authoritative source the
    task's reports have summed by hand each round. Missing/unreadable
    ledger files count as 0 spend, never an error (a fresh worktree has no
    ledger yet)."""
    total = 0.0
    decisions_dir = ROOT / "state" / "decisions"
    if not decisions_dir.exists():
        return 0.0
    for path in decisions_dir.glob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if str(row.get("site", "")).startswith("bl."):
                    total += float(row.get("cost_usd") or 0.0)
        except (OSError, json.JSONDecodeError):
            continue
    return total


def _remaining_task_budget_usd() -> float:
    return max(0.0, TASK_BUDGET_CAP_USD - _task_spend_so_far_usd())


class BudgetExceeded(RuntimeError):
    pass


class SpendTracker:
    """Local call-ceiling + dollar-cap, independent of tools/decide.py's
    monthly DECIDE_BUDGET_USD gate — jev-ops SKILL.md rule 1 is explicit
    that ad-hoc scripts need their own ceiling on top of that one."""

    def __init__(self, max_calls: int, max_usd: float):
        self.max_calls = max_calls
        self.max_usd = max_usd
        self.calls = 0
        self.cost_usd = 0.0

    def check(self) -> None:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"call ceiling reached: {self.calls}/{self.max_calls}")
        if self.cost_usd >= self.max_usd:
            raise BudgetExceeded(f"dollar cap reached: ${self.cost_usd:.5f}/${self.max_usd:.5f}")

    def record(self, cost_usd: float) -> None:
        self.calls += 1
        self.cost_usd += cost_usd


def _ask(site: str, state: dict, tracker: SpendTracker):
    tracker.check()
    d = decide_mod.decide(site, state)
    tracker.record(d.cost_usd)
    return d


def _row(
    line_id: str, question: str, *, status: str, choice=None, confidence=None,
    needs_review=None, provider=None, cost_usd=0.0, ledger_id=None,
    writer_beat=None, disagreement=False, skip_reason=None, context=None,
    candidate_map=None, state_lang=None,
) -> dict:
    return {
        "line_id": line_id, "question": question, "status": status,
        "choice": choice, "confidence": confidence, "needs_review": needs_review,
        "provider": provider, "cost_usd": cost_usd, "ledger_id": ledger_id,
        "writer_beat": writer_beat, "disagreement": disagreement,
        "skip_reason": skip_reason, "context": context, "candidate_map": candidate_map,
        "state_lang": state_lang,
    }


def _context_snippet(line: "lib.ScriptLine") -> str:
    parts = [p for p in (line.screen, line.shot, line.spoken[:60]) if p]
    return " · ".join(parts[:2]) or line.spoken[:60]


def _beat_state(line: "lib.ScriptLine", index: int, total: int, state_lang: str) -> dict:
    state = {
        "line_index": index, "total_lines": total,
        "shot": line.shot, "screen": line.screen,
        "has_screen_hint": bool(line.screen),
    }
    if state_lang == "th":
        state["spoken"] = line.spoken
    return state


def _entry_state(prev_beat: str, this_beat: str, prev_mode, this_mode, index: int) -> dict:
    return {
        "line_index": index,
        "prev_beat": prev_beat, "this_beat": this_beat,
        "mode_change": lib.entry_mode_change(prev_mode, this_mode),
    }


def _focus_device_state(line: "lib.ScriptLine", state_lang: str) -> dict:
    state = {"shot": line.shot, "screen": line.screen}
    if state_lang == "th":
        state["spoken"] = line.spoken
    return state


def plan_episode(
    lines: list["lib.ScriptLine"], *, manifest: list[dict] | None, brand_map: dict,
    gate: float, state_lang: str, tracker: SpendTracker,
) -> list[dict]:
    rows: list[dict] = []
    prev_beat: str | None = None
    prev_mode: str | None = None
    total = len(lines)

    for i, line in enumerate(lines):
        context = _context_snippet(line)

        # bl.beat — always asked.
        try:
            d = _ask("bl.beat", _beat_state(line, i, total, state_lang), tracker)
        except BudgetExceeded as e:
            rows.append(_row(line.tag, "bl.beat", status="skipped", skip_reason=str(e), context=context))
            break
        conf = lib.confidence_of(d.probs)
        beat_choice = d.choice
        disagreement = bool(line.beat) and line.beat != beat_choice
        rows.append(_row(
            line.tag, "bl.beat", status="answered", choice=beat_choice, confidence=conf,
            needs_review=lib.needs_review(beat_choice, conf, gate), provider=d.provider,
            cost_usd=d.cost_usd, ledger_id=d.ledger_id, writer_beat=line.beat or None,
            disagreement=disagreement, context=context, state_lang=state_lang,
        ))
        this_mode = lib.mode_for_beat(beat_choice)

        # bl.entry — every line but the first.
        if i > 0:
            try:
                d2 = _ask("bl.entry", _entry_state(prev_beat, beat_choice, prev_mode, this_mode, i), tracker)
                conf2 = lib.confidence_of(d2.probs)
                rows.append(_row(
                    line.tag, "bl.entry", status="answered", choice=d2.choice, confidence=conf2,
                    needs_review=lib.needs_review(d2.choice, conf2, gate), provider=d2.provider,
                    cost_usd=d2.cost_usd, ledger_id=d2.ledger_id, context=context,
                ))
            except BudgetExceeded as e:
                rows.append(_row(line.tag, "bl.entry", status="skipped", skip_reason=str(e), context=context))

        # bl.focus_device — only when this line shows something.
        focus_device_choice = None
        if beat_choice == "show":
            try:
                d3 = _ask("bl.focus_device", _focus_device_state(line, state_lang), tracker)
                conf3 = lib.confidence_of(d3.probs)
                focus_device_choice = d3.choice
                rows.append(_row(
                    line.tag, "bl.focus_device", status="answered", choice=focus_device_choice,
                    confidence=conf3, needs_review=lib.needs_review(focus_device_choice, conf3, gate),
                    provider=d3.provider, cost_usd=d3.cost_usd, ledger_id=d3.ledger_id, context=context,
                    state_lang=state_lang,
                ))
            except BudgetExceeded as e:
                rows.append(_row(line.tag, "bl.focus_device", status="skipped", skip_reason=str(e), context=context))

        # bl.focus_target — only when a device was chosen and boxes exist.
        focus_box = None
        if focus_device_choice not in (None, "none", "other"):
            dom_candidates = lib.dom_candidates_for_tag(manifest, line.tag)
            if dom_candidates:
                labelled = lib.label_candidates(dom_candidates)
                try:
                    d4 = _ask("bl.focus_target", {"candidates": labelled}, tracker)
                    conf4 = lib.confidence_of(d4.probs)
                    focus_box = lib.resolve_label(labelled, d4.choice)
                    rows.append(_row(
                        line.tag, "bl.focus_target", status="answered", choice=d4.choice,
                        confidence=conf4, needs_review=lib.needs_review(d4.choice, conf4, gate),
                        provider=d4.provider, cost_usd=d4.cost_usd, ledger_id=d4.ledger_id,
                        context=context, candidate_map=labelled,
                    ))
                except BudgetExceeded as e:
                    rows.append(_row(line.tag, "bl.focus_target", status="skipped", skip_reason=str(e), context=context))
            else:
                rows.append(_row(
                    line.tag, "bl.focus_target", status="skipped", needs_review=True,
                    skip_reason="no computed candidates (no REAL_MANIFEST evidence_box for this tag)",
                    context=context,
                ))

        # bl.highlight_word — only when the line has any word/number/brand candidates.
        words = lib.content_words(line.spoken, brand_map)
        if words:
            labelled_words = lib.label_candidates(words)
            try:
                d5 = _ask("bl.highlight_word", {"candidates": labelled_words}, tracker)
                conf5 = lib.confidence_of(d5.probs)
                rows.append(_row(
                    line.tag, "bl.highlight_word", status="answered", choice=d5.choice,
                    confidence=conf5, needs_review=lib.needs_review(d5.choice, conf5, gate),
                    provider=d5.provider, cost_usd=d5.cost_usd, ledger_id=d5.ledger_id,
                    context=context, candidate_map=labelled_words,
                ))
            except BudgetExceeded as e:
                rows.append(_row(line.tag, "bl.highlight_word", status="skipped", skip_reason=str(e), context=context))
        else:
            rows.append(_row(
                line.tag, "bl.highlight_word", status="skipped", needs_review=True,
                skip_reason="no number/word/brand candidates in this line", context=context,
            ))

        # bl.text_slot — only when at least one free rectangle survives.
        # AVATAR_BOX is specifically the COMPOSITE-mode box (§6d: "always
        # above the avatar's head... the composite exists precisely to free
        # that space"). In full-frame mode the avatar fills nearly the whole
        # canvas and text is placed AT CHEST HEIGHT ON it instead (§6d: "In
        # full-frame mode it sits at chest height") — there is no computed
        # full-frame silhouette to route text around, so only composite mode
        # filters bands against AVATAR_BOX.
        avatar_active = this_mode == "composite"
        free = lib.free_text_rects(lib.AVATAR_BOX, focus_box, avatar_active=avatar_active)
        if free:
            labelled_slots = lib.label_candidates(free)
            try:
                d6 = _ask("bl.text_slot", {"candidates": labelled_slots}, tracker)
                conf6 = lib.confidence_of(d6.probs)
                rows.append(_row(
                    line.tag, "bl.text_slot", status="answered", choice=d6.choice,
                    confidence=conf6, needs_review=lib.needs_review(d6.choice, conf6, gate),
                    provider=d6.provider, cost_usd=d6.cost_usd, ledger_id=d6.ledger_id,
                    context=context, candidate_map=labelled_slots,
                ))
            except BudgetExceeded as e:
                rows.append(_row(line.tag, "bl.text_slot", status="skipped", skip_reason=str(e), context=context))
        else:
            rows.append(_row(
                line.tag, "bl.text_slot", status="skipped", needs_review=True,
                skip_reason="no free rectangle clears the avatar/focus box", context=context,
            ))

        prev_beat, prev_mode = beat_choice, this_mode

    return rows


def cmd_plan(args: argparse.Namespace) -> int:
    lines = lib.parse_script_tsv(Path(args.script))
    if not lines:
        print(f"no lines parsed from {args.script}", file=sys.stderr)
        return 1
    manifest = None
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    brand_map = lib.load_brand_map(BRAND_MAP_PATH) if BRAND_MAP_PATH.exists() else {}
    tracker = SpendTracker(args.max_calls, args.max_usd)

    rows = plan_episode(
        lines, manifest=manifest, brand_map=brand_map, gate=args.gate,
        state_lang=args.state_lang, tracker=tracker,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")

    flagged = sum(1 for r in rows if r.get("needs_review"))
    print(
        f"plan: {len(lines)} lines, {len(rows)} decision rows, "
        f"{tracker.calls} Jev calls, ${tracker.cost_usd:.6f} spent, "
        f"{flagged} flagged for review -> {out_path}"
    )
    return 0


# ─────────────────────────────────────────────────────────────── storyboard

_STATUS_ICON = {
    "ok": '<svg viewBox="0 0 16 16" width="14" height="14"><path d="M2 8l4 4 8-8" stroke="#1a7f37" stroke-width="2" fill="none"/></svg>',
    "flag": '<svg viewBox="0 0 16 16" width="14" height="14"><path d="M3 1v14M3 2h9l-2.5 3L12 8H3" stroke="#b35900" stroke-width="1.6" fill="none" stroke-linejoin="round"/></svg>',
    "skip": '<svg viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="6" stroke="#888" stroke-width="1.6" fill="none"/><path d="M5.5 8h5" stroke="#888" stroke-width="1.6"/></svg>',
}

_STORYBOARD_CSS = """
body{font-family:-apple-system,Helvetica,Arial,sans-serif;background:#0b0c0f;color:#eef1f3;margin:0;padding:24px}
h1{font-size:18px;margin:0 0 4px}
.sub{color:#9aa3ab;font-size:13px;margin-bottom:18px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:6px 10px;border-bottom:1px solid #262a30;text-align:left;vertical-align:top}
th{color:#9aa3ab;font-weight:600;position:sticky;top:0;background:#0b0c0f}
tr.flagged{background:#241a0e}
tr.line-start td{border-top:2px solid #3a3f47}
.ctx{color:#9aa3ab;max-width:260px}
.conf{font-variant-numeric:tabular-nums}
.badge{display:inline-flex;align-items:center;gap:4px}
.disagree{color:#e0202f;font-weight:600}
"""


def _status_key(row: dict) -> str:
    if row.get("status") == "skipped":
        return "skip"
    return "flag" if row.get("needs_review") else "ok"


def cmd_storyboard(args: argparse.Namespace) -> int:
    rows = []
    with Path(args.decisions).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    flagged_total = sum(1 for r in rows if r.get("needs_review"))
    lines_seen: list[str] = []
    for r in rows:
        if r["line_id"] not in lines_seen:
            lines_seen.append(r["line_id"])

    body = []
    for line_id in lines_seen:
        line_rows = [r for r in rows if r["line_id"] == line_id]
        for j, r in enumerate(line_rows):
            status = _status_key(r)
            tr_classes = []
            if j == 0:
                tr_classes.append("line-start")
            if status == "flag":
                tr_classes.append("flagged")
            cls_attr = f' class="{" ".join(tr_classes)}"' if tr_classes else ""
            choice = html.escape(str(r.get("choice") or "—"))
            conf = r.get("confidence")
            conf_s = f"{conf:.2f}" if isinstance(conf, (int, float)) else "—"
            ctx = html.escape(r.get("context") or "")
            disagree = ""
            if r.get("disagreement"):
                disagree = f' <span class="disagree">writer said {html.escape(str(r.get("writer_beat")))}</span>'
            reason = html.escape(r.get("skip_reason") or "")
            body.append(
                "<tr{cls}>"
                "<td>{line_id}</td><td>{q}</td>"
                "<td><span class=\"badge\">{icon}{choice}{disagree}</span></td>"
                "<td class=\"conf\">{conf}</td>"
                "<td class=\"ctx\">{ctx}{reason}</td>"
                "</tr>".format(
                    cls=cls_attr, line_id=html.escape(line_id) if j == 0 else "",
                    q=html.escape(r["question"]), icon=_STATUS_ICON[status],
                    choice=choice, disagree=disagree, conf=conf_s, ctx=ctx,
                    reason=(f' <em>{reason}</em>' if reason else ""),
                )
            )

    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>BLACK LIQUIDITY — Jev storyboard</title>
<style>{_STORYBOARD_CSS}</style></head>
<body>
<h1>BLACK LIQUIDITY — Jev editorial storyboard</h1>
<div class="sub">{len(lines_seen)} lines · {len(rows)} decisions · {flagged_total} flagged for CEO review</div>
<table>
<thead><tr><th>Line</th><th>Question</th><th>Choice</th><th>Conf.</th><th>Context</th></tr></thead>
<tbody>
{''.join(body)}
</tbody>
</table>
</body></html>
"""
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"storyboard: {len(lines_seen)} lines, {flagged_total} flagged -> {out_path}")
    return 0


# ─────────────────────────────────────────── Jev up-skill scoreboard (§57) ─
# freeze / final / score / report / seed-ref1300 / baseline — task-161643f7.

SCOREBOARD_DIR = ROOT / "prototypes" / "bl-jev-scoreboard"
SCOREBOARD_JSONL = SCOREBOARD_DIR / "scoreboard.jsonl"
SCOREBOARD_MD = SCOREBOARD_DIR / "SCOREBOARD.md"
SITE_YAML_DIR = ROOT / "config" / "decisions"
DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def _git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "").strip()


def _current_site_yaml_sha() -> str:
    """The committed-state fingerprint `freeze`/`score` compare against —
    the latest commit touching any `config/decisions/bl.*.yaml` file, plus
    a `:dirty` suffix if one of them has uncommitted changes right now
    (catches a criteria edit that was never committed at all)."""
    paths = sorted(str(p.relative_to(ROOT)) for p in SITE_YAML_DIR.glob("bl.*.yaml"))
    if not paths:
        return "no-site-yamls"
    commit_sha = _git_output("log", "-1", "--format=%H", "--", *paths) or "uncommitted"
    dirty = _git_output("status", "--porcelain", "--", *paths)
    return f"{commit_sha}:dirty" if dirty else commit_sha


def _all_ledger_rows() -> list[dict]:
    decisions_dir = ROOT / "state" / "decisions"
    out: list[dict] = []
    if not decisions_dir.exists():
        return out
    for path in decisions_dir.glob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                out.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def cmd_freeze(args: argparse.Namespace) -> int:
    decisions_path = Path(args.decisions)
    rows = _read_jsonl(decisions_path)
    if not rows:
        print(f"no decision rows in {decisions_path}", file=sys.stderr)
        return 1
    stamp = lib.build_frozen_stamp(str(decisions_path), rows, _current_site_yaml_sha(), _iso_now())
    frozen_path = lib.frozen_path_for(decisions_path)
    frozen_path.write_text(json.dumps(stamp, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"froze {len(rows)} rows -> {frozen_path} (site_yaml_sha={stamp['site_yaml_sha']})")
    return 0


def _apply_final(rows: list[dict], line_id: str, question: str, choice: str) -> bool:
    for r in rows:
        if r.get("line_id") == line_id and r.get("question") == question:
            rec = lib.final_call_record(question, r.get("state_lang"), r.get("choice"), r.get("confidence"), choice)
            r["final"] = choice
            r["applied_by"] = rec["applied_by"]
            r["jev_wrong_at_gate"] = rec["jev_wrong_at_gate"]
            return True
    return False


def cmd_final(args: argparse.Namespace) -> int:
    decisions_path = Path(args.decisions)
    rows = _read_jsonl(decisions_path)
    if not rows:
        print(f"no decision rows in {decisions_path}", file=sys.stderr)
        return 1

    calls: list[tuple[str, str, str]] = []
    if args.tsv:
        calls.extend((r["line_id"], r["question"], r["choice"]) for r in lib.parse_final_tsv(Path(args.tsv)))
    if args.line_id:
        if not args.question or args.choice is None:
            print("final: line_id given without question/choice", file=sys.stderr)
            return 2
        calls.append((args.line_id, args.question, args.choice))
    if not calls:
        print("final: nothing to record (pass line_id question choice, or --tsv)", file=sys.stderr)
        return 2

    applied = 0
    not_found: list[str] = []
    for line_id, question, choice in calls:
        if _apply_final(rows, line_id, question, choice):
            applied += 1
        else:
            not_found.append(f"{line_id}/{question}")

    _write_jsonl(decisions_path, rows)
    print(f"final: {applied}/{len(calls)} recorded -> {decisions_path}")
    if not_found:
        print(f"not found in decisions.jsonl: {', '.join(not_found)}", file=sys.stderr)
    return 0 if not not_found else 1


def _find_transcripts_for_task(task_id: str, projects_dir: Path) -> list[Path]:
    """`~/.claude/projects/*<task_id>*/*.jsonl` — robust to the repo's
    2026-09-23 path rename (old slugs `-Users-gob-Projects-Agents-...`, new
    ones `-Users-gob-MoonieXHQ-Agents-Core-...`, both contain the task id)."""
    if not projects_dir.exists():
        return []
    return sorted(projects_dir.glob(f"*{task_id}*/*.jsonl"))


def _iter_transcript_usage_records(paths: list[Path]):
    """Streams `{"message": {"id", "usage"}}` records only — never
    materializes a full transcript line (tool output/file content can be
    huge; a 31MB real transcript was seen, task-52c669bb)."""
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = d.get("message")
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage")
                if not usage:
                    continue
                yield {"message": {"id": msg.get("id"), "usage": usage}}


def _editor_usage_for_tasks(task_ids: list[str], projects_dir: Path) -> dict:
    all_paths: list[Path] = []
    missing_tasks: list[str] = []
    for tid in task_ids:
        paths = _find_transcripts_for_task(tid, projects_dir)
        if not paths:
            missing_tasks.append(tid)
        all_paths.extend(paths)
    usage = lib.sum_transcript_usage(list(_iter_transcript_usage_records(all_paths)))
    return {"usage": usage, "missing_tasks": missing_tasks, "transcript_count": len(all_paths)}


def _scoreboard_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    d = Path(args.scoreboard_dir) if getattr(args, "scoreboard_dir", None) else SCOREBOARD_DIR
    return d / "scoreboard.jsonl", d / "SCOREBOARD.md"


def cmd_score(args: argparse.Namespace) -> int:
    scoreboard_jsonl, _ = _scoreboard_paths(args)
    decisions_path = Path(args.decisions)
    rows = _read_jsonl(decisions_path)
    if not rows:
        print(f"no decision rows in {decisions_path}", file=sys.stderr)
        return 1

    frozen_path = lib.frozen_path_for(decisions_path)
    frozen = json.loads(frozen_path.read_text(encoding="utf-8")) if frozen_path.exists() else None
    try:
        lib.check_frozen(frozen, rows, _current_site_yaml_sha())
    except lib.FreezeError as e:
        print(f"score refused: {e}", file=sys.stderr)
        return 3

    timings = lib.parse_line_timings(Path(args.timings)) if args.timings else {}
    frames = lib.jev_beat_frames(rows, timings)
    summary = lib.applied_summary(rows)
    raw_acc = lib.raw_accuracy_by_site(rows)
    wrong = lib.count_jev_wrong_at_gate(rows)

    ledger_by_id = lib.index_ledger_by_id(_all_ledger_rows())
    spend = lib.jev_spend_and_tokens(rows, ledger_by_id)

    counterfactual_tokens_total = 0.0
    site_cfg_cache: dict[str, dict] = {}
    for r in rows:
        if r.get("applied_by") != "jev":
            continue
        led = ledger_by_id.get(r.get("ledger_id"))
        if not led:
            continue
        q = r.get("question")
        if q not in site_cfg_cache:
            try:
                site_cfg_cache[q] = decide_mod.load_site(q)
            except decide_mod.DecisionError:
                site_cfg_cache[q] = {}
        ct = lib.counterfactual_tokens(site_cfg_cache[q], int(led.get("state_chars") or 0))
        counterfactual_tokens_total += ct["tokens_total"]

    editor_new_tpm = None
    editor_total_tpm = None
    editor_usage = None
    missing_editor_tasks: list[str] = []
    if args.editor_task:
        task_ids = [t.strip() for t in args.editor_task.split(",") if t.strip()]
        result = _editor_usage_for_tasks(task_ids, Path(args.projects_dir))
        editor_usage = result["usage"]
        missing_editor_tasks = result["missing_tasks"]
        video_seconds = lib.video_duration_seconds(timings)
        editor_new_tpm = lib.tokens_per_video_minute(lib.new_work_tokens(editor_usage), video_seconds)
        editor_total_tpm = lib.tokens_per_video_minute(editor_usage["total"], video_seconds)

    row = {
        "episode": args.episode,
        "kind": "cut",
        "scored_at": _iso_now(),
        "decisions_total": summary["decisions_total"],
        "jev_applied": summary["jev_applied"],
        "jev_applied_pct": summary["jev_applied_pct"],
        "jev_seconds": frames["jev_seconds"],
        "jev_frames": frames["jev_frames"],
        "jev_raw_accuracy": raw_acc,
        "jev_wrong_at_gate": wrong,
        "jev_usd": spend["jev_usd"],
        "jev_tokens": spend["jev_tokens"],
        "counterfactual_usd": spend["counterfactual_usd"],
        "counterfactual_tokens": counterfactual_tokens_total,
        "net_saved_usd": spend["counterfactual_usd"] - spend["jev_usd"],
        "editor_new_tokens_per_video_min": editor_new_tpm,
        "editor_total_tokens_per_video_min": editor_total_tpm,
        "editor_usage": editor_usage,
        "editor_task": args.editor_task,
        "site_yaml_sha": frozen.get("site_yaml_sha") if frozen else None,
        "missing_beat_timing_tags": frames["missing_tags"],
        "missing_ledger_ids": spend["missing_ledger_ids"],
        "missing_editor_tasks": missing_editor_tasks,
    }
    _append_jsonl(scoreboard_jsonl, row)
    print(
        f"score: {row['episode']} decisions={row['decisions_total']} "
        f"jev_applied={row['jev_applied']} ({row['jev_applied_pct']:.1f}%) "
        f"frames={row['jev_frames']} jev_usd=${row['jev_usd']:.6f} "
        f"net_saved(est)=${row['net_saved_usd']:.6f} "
        f"wrong_at_gate={row['jev_wrong_at_gate']} -> {scoreboard_jsonl}"
    )
    if row["missing_beat_timing_tags"]:
        print(f"WARNING: no timing for bl.beat lines: {row['missing_beat_timing_tags']}", file=sys.stderr)
    if missing_editor_tasks:
        print(f"WARNING: no transcript found for editor tasks: {missing_editor_tasks}", file=sys.stderr)
    return 0


def cmd_seed_ref1300(args: argparse.Namespace) -> int:
    scoreboard_jsonl, _ = _scoreboard_paths(args)
    rows = _read_jsonl(scoreboard_jsonl)
    if any(r.get("episode") == "REF-1300" for r in rows):
        print("REF-1300 already seeded, skipping (idempotent)")
        return 0
    _append_jsonl(scoreboard_jsonl, lib.REF_1300_ROW)
    print(f"seeded REF-1300 -> {scoreboard_jsonl}")
    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    scoreboard_jsonl, _ = _scoreboard_paths(args)
    episodes_in = lib.parse_baseline_episodes_tsv(Path(args.episodes))
    if not episodes_in:
        print(f"no episodes parsed from {args.episodes}", file=sys.stderr)
        return 1

    resolved = []
    for ep in episodes_in:
        paths = _find_transcripts_for_task(ep["task_id"], Path(args.projects_dir))
        duration = ep.get("duration_seconds")
        missing = []
        if not paths:
            missing.append("transcript")
        if duration is None:
            missing.append("duration")
        new_tpm = total_tpm = None
        usage = None
        if not missing:
            usage = lib.sum_transcript_usage(list(_iter_transcript_usage_records(paths)))
            new_tpm = lib.tokens_per_video_minute(lib.new_work_tokens(usage), duration)
            total_tpm = lib.tokens_per_video_minute(usage["total"], duration)
        resolved.append({
            "episode": ep["episode"], "task_id": ep["task_id"], "duration_seconds": duration,
            "editor_new_tokens_per_video_min": new_tpm,
            "editor_total_tokens_per_video_min": total_tpm,
            "usage": usage, "missing": ",".join(missing) or None,
        })

    baseline_row = lib.build_baseline_row(resolved)
    others = [r for r in _read_jsonl(scoreboard_jsonl) if r.get("kind") != "baseline"]
    _write_jsonl(scoreboard_jsonl, [baseline_row] + others)

    print(
        f"baseline: n={baseline_row['n_measured']} (of {baseline_row['n_total']} listed) — "
        f"new tok/min (primary) = {baseline_row['editor_new_tokens_per_video_min']}, "
        f"total tok/min (secondary) = {baseline_row['editor_total_tokens_per_video_min']} -> {scoreboard_jsonl}"
    )
    for e in resolved:
        status = (
            f"MISSING ({e['missing']})" if e["missing"]
            else f"{e['editor_new_tokens_per_video_min']:.0f} new / {e['editor_total_tokens_per_video_min']:.0f} total tok/min"
        )
        print(f"  {e['episode']} ({e['task_id']}): {status}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    scoreboard_jsonl, scoreboard_md = _scoreboard_paths(args)
    rows = _read_jsonl(scoreboard_jsonl)
    if not rows:
        print(f"no rows in {scoreboard_jsonl} — run seed-ref1300/score first", file=sys.stderr)
        return 1

    cut_rows = [r for r in rows if r.get("kind") == "cut"]
    baseline_rows = [r for r in rows if r.get("kind") == "baseline"]
    baseline_tpm = baseline_rows[-1].get("editor_new_tokens_per_video_min") if baseline_rows else None
    verdict = lib.evaluate_hypothesis(cut_rows, baseline_tpm)

    scoreboard_md.parent.mkdir(parents=True, exist_ok=True)
    scoreboard_md.write_text(lib.render_scoreboard_md(rows, verdict), encoding="utf-8")
    print(f"report: {len(rows)} rows -> {scoreboard_md} ({lib.hypothesis_line(verdict)})")
    return 0


# ──────────────────────────────────────────────────────────────────── eval
# Ground truth is prototypes/bl-ref-census/groundtruth.tsv's shape
# (task-82380776), not a tag/question/expected/state file someone hand-
# writes — see jev_edit_lib.py's "census groundtruth" section for the two
# label maps and why focus_device's vocabulary only partially overlaps.

def _no_real_evidence(target: str) -> bool:
    # "-" = nothing named; "avatar box (whole)" / "...avatar still full-size"
    # = the avatar itself is the P2 target, not a piece of evidence — same
    # as no screen hint for bl.beat's purposes (census: 4+2 of 45 rows).
    return target in ("-", "") or "avatar" in target.lower()


def _beat_case(row: dict, index: int, total: int, state_lang: str) -> dict:
    target = row.get("target", "")
    screen = "" if _no_real_evidence(target) else target
    state = {
        "line_index": index, "total_lines": total, "shot": "", "screen": screen,
        "has_screen_hint": bool(screen),
    }
    if state_lang == "th":
        state["spoken"] = row.get("text", "")
    return {"line_id": lib.census_line_id(row), "expected": row.get("class", ""), "state": state}


def _entry_cases(rows: list[dict]) -> list[dict]:
    cases = []
    prev_beat: str | None = None
    prev_mode: str | None = None
    for i, row in enumerate(rows):
        this_beat = row.get("class", "")
        this_mode = lib.mode_for_beat(this_beat)
        mapped = lib.ENTRY_TYPE_MAP.get(row.get("entry_type", ""))
        if mapped and i > 0:
            state = {
                "line_index": i, "prev_beat": prev_beat, "this_beat": this_beat,
                "mode_change": lib.entry_mode_change(prev_mode, this_mode),
            }
            cases.append({"line_id": lib.census_line_id(row), "expected": mapped, "state": state})
        prev_beat, prev_mode = this_beat, this_mode
    return cases


def _focus_device_cases(rows: list[dict]) -> list[dict]:
    cases = []
    for row in rows:
        raw = row.get("focus_device", "")
        mapped = lib.FOCUS_DEVICE_MAP.get(raw.split(" (")[0].strip()) or lib.FOCUS_DEVICE_MAP.get(raw)
        if not mapped:
            continue
        target = row.get("target", "")
        state = {"shot": "", "screen": "" if _no_real_evidence(target) else target}
        cases.append({"line_id": lib.census_line_id(row), "expected": mapped, "state": state})
    return cases


def _run_eval_cases(site: str, cases: list[dict], reps: int, tracker: SpendTracker, misses: list[str]) -> list[tuple[float, bool]]:
    scored: list[tuple[float, bool]] = []
    for rep in range(reps):
        for case in cases:
            d = _ask(site, case["state"], tracker)
            conf = lib.confidence_of(d.probs)
            correct = d.choice == case["expected"]
            scored.append((conf, correct))
            if not correct:
                misses.append(
                    f"{case['line_id']}/{site} rep{rep}: truth={case['expected']} got={d.choice} conf={conf:.2f}"
                )
    return scored


def cmd_eval(args: argparse.Namespace) -> int:
    gt_path = Path(args.groundtruth)
    if not gt_path.exists():
        print(
            f"groundtruth file not found: {gt_path} — stopping per task brief "
            "('If it does not exist when your build and tests are done, stop "
            "and report. The CTO will reopen you for the eval.')",
            file=sys.stderr,
        )
        return 2

    rows = lib.parse_census_groundtruth(gt_path)
    if not rows:
        print(f"groundtruth file {gt_path} has no rows", file=sys.stderr)
        return 1

    tracker = SpendTracker(args.max_calls, args.max_usd)
    misses: list[str] = []
    total = len(rows)

    beat_en_cases = [_beat_case(r, i, total, "en") for i, r in enumerate(rows)]
    beat_th_cases = [_beat_case(r, i, total, "th") for i, r in enumerate(rows)]
    entry_cases = _entry_cases(rows)
    focus_cases = _focus_device_cases(rows)

    print(f"groundtruth: {total} rows ({gt_path})")
    print(f"budget: max_calls={args.max_calls} max_usd=${args.max_usd:.5f} "
          f"(task spend so far this ledger: ${_task_spend_so_far_usd():.6f})")
    if len(focus_cases) < 12:
        print(
            f"bl.focus_device: SKIPPED — only {len(focus_cases)} rows share this "
            "site's vocabulary with the census (highlighter_sweep/pan+zoom); "
            "avatar_shrink/avatar_slide/plate_dissolve/pop*/scroll are real P2 "
            "events but not evidence-focus devices this site models. Below the "
            "jev-ops ≥12-case minimum to trust an accuracy number."
        )

    variants = [
        ("bl.beat [state=en]", "bl.beat", beat_en_cases),
        ("bl.beat [state=th]", "bl.beat", beat_th_cases),
        ("bl.entry", "bl.entry", entry_cases),
    ]
    if len(focus_cases) >= 12:
        variants.append(("bl.focus_device", "bl.focus_device", focus_cases))

    for label, site, cases in variants:
        try:
            scored = _run_eval_cases(site, cases, args.reps, tracker, misses)
        except BudgetExceeded as e:
            print(f"eval stopped before {label}: {e}", file=sys.stderr)
            print(f"spend so far: ${tracker.cost_usd:.6f} over {tracker.calls} calls")
            if misses:
                print("misses:")
                for m in misses:
                    print(f"  {m}")
            return 3
        _report_variant(label, scored)

    print(f"total eval spend: ${tracker.cost_usd:.6f} over {tracker.calls} calls")
    if misses:
        print("misses:")
        for m in misses:
            print(f"  {m}")
    return 0


def _report_variant(label: str, scored: list[tuple[float, bool]]) -> None:
    right = sum(1 for _, c in scored if c)
    n = len(scored)
    buckets = lib.bucket_confidence(scored)
    gate = lib.recommend_gate(scored)
    print(f"site: {label}   cases {n}")
    print(f"right {right}/{n}" if n else "right 0/0")
    for lbl, b in buckets.items():
        acc = f"{b['accuracy']:.2f}" if b["accuracy"] is not None else "—"
        print(f"  conf {lbl}: n={b['n']} acc={acc}")
    print(f"  recommended gate: {gate if gate is not None else 'NONE — even the highest-confidence case was wrong'}")


# ───────────────────────────────────────────────────────────────────── CLI

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jev_edit.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("script")
    p_plan.add_argument("--manifest", default=None)
    p_plan.add_argument("--gate", type=float, default=DEFAULT_GATE)
    p_plan.add_argument("--state-lang", choices=["en", "th"], default="en")
    p_plan.add_argument("--max-calls", type=int, default=PLAN_MAX_CALLS_DEFAULT)
    p_plan.add_argument("--max-usd", type=float, default=_remaining_task_budget_usd())
    p_plan.add_argument("--out", required=True)

    p_story = sub.add_parser("storyboard")
    p_story.add_argument("decisions")
    p_story.add_argument("--out", required=True)

    p_eval = sub.add_parser("eval")
    p_eval.add_argument("groundtruth")
    p_eval.add_argument("--reps", type=int, default=2)
    p_eval.add_argument("--max-calls", type=int, default=EVAL_MAX_CALLS)
    p_eval.add_argument("--max-usd", type=float, default=_remaining_task_budget_usd())

    p_freeze = sub.add_parser("freeze")
    p_freeze.add_argument("decisions")

    p_final = sub.add_parser("final")
    p_final.add_argument("decisions")
    p_final.add_argument("line_id", nargs="?")
    p_final.add_argument("question", nargs="?")
    p_final.add_argument("choice", nargs="?")
    p_final.add_argument("--tsv", default=None, help="bulk form: line_id\\tquestion\\tchoice per row")

    p_score = sub.add_parser("score")
    p_score.add_argument("decisions")
    p_score.add_argument("--timings", default=None, help="tag\\tt0\\tt1 TSV, the episode's line timings")
    p_score.add_argument("--episode", required=True)
    p_score.add_argument("--editor-task", default=None, help="task-XXXX[,task-YYYY] — editor session(s) to sum real token usage from")
    p_score.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    p_score.add_argument("--scoreboard-dir", default=None, help="override prototypes/bl-jev-scoreboard (testing)")

    p_seed = sub.add_parser("seed-ref1300")
    p_seed.add_argument("--scoreboard-dir", default=None)

    p_baseline = sub.add_parser("baseline")
    p_baseline.add_argument("episodes", help="episode\\ttask_id\\tduration_seconds TSV")
    p_baseline.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    p_baseline.add_argument("--scoreboard-dir", default=None)

    p_report = sub.add_parser("report")
    p_report.add_argument("--scoreboard-dir", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "plan":
        return cmd_plan(args)
    if args.cmd == "storyboard":
        return cmd_storyboard(args)
    if args.cmd == "eval":
        return cmd_eval(args)
    if args.cmd == "freeze":
        return cmd_freeze(args)
    if args.cmd == "final":
        return cmd_final(args)
    if args.cmd == "score":
        return cmd_score(args)
    if args.cmd == "seed-ref1300":
        return cmd_seed_ref1300(args)
    if args.cmd == "baseline":
        return cmd_baseline(args)
    if args.cmd == "report":
        return cmd_report(args)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
