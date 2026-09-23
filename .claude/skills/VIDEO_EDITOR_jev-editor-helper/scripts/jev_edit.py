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
import csv
import html
import json
import sys
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
# DECIDE_BUDGET_USD. `eval`'s defaults are the task's own hard numbers
# ($0.05, 2000 calls); `plan` gets a much smaller default sized for one
# episode (~40-80 lines x up to 6 questions).
EVAL_MAX_USD = 0.05
EVAL_MAX_CALLS = 2000
PLAN_MAX_USD_DEFAULT = 0.05
PLAN_MAX_CALLS_DEFAULT = 2000


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
    candidate_map=None,
) -> dict:
    return {
        "line_id": line_id, "question": question, "status": status,
        "choice": choice, "confidence": confidence, "needs_review": needs_review,
        "provider": provider, "cost_usd": cost_usd, "ledger_id": ledger_id,
        "writer_beat": writer_beat, "disagreement": disagreement,
        "skip_reason": skip_reason, "context": context, "candidate_map": candidate_map,
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
            disagreement=disagreement, context=context,
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


# ──────────────────────────────────────────────────────────────────── eval

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

    cases: list[dict] = []
    with gt_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            cases.append(row)
    if not cases:
        print(f"groundtruth file {gt_path} has no rows", file=sys.stderr)
        return 1

    tracker = SpendTracker(EVAL_MAX_CALLS, EVAL_MAX_USD)
    per_site: dict[str, list[tuple[float, bool]]] = {}
    misses: list[str] = []

    for rep in range(args.reps):
        for case in cases:
            site = case["question"]
            expected = case["expected"]
            state = json.loads(case["state"]) if case.get("state") else {}
            try:
                d = _ask(site, state, tracker)
            except BudgetExceeded as e:
                print(f"eval stopped: {e}", file=sys.stderr)
                _print_eval_report(per_site, tracker, misses)
                return 3
            conf = lib.confidence_of(d.probs)
            correct = d.choice == expected
            per_site.setdefault(site, []).append((conf, correct))
            if not correct:
                misses.append(f"{case.get('line_id', '?')}/{site} rep{rep}: truth={expected} got={d.choice} conf={conf:.2f}")

    _print_eval_report(per_site, tracker, misses)
    return 0


def _print_eval_report(per_site: dict, tracker: SpendTracker, misses: list[str]) -> None:
    for site, rows in sorted(per_site.items()):
        right = sum(1 for _, c in rows if c)
        buckets = lib.bucket_confidence(rows)
        print(f"site: {site}   cases {len(rows)}")
        print(f"right {right}/{len(rows)}")
        for label, b in buckets.items():
            acc = f"{b['accuracy']:.2f}" if b["accuracy"] is not None else "—"
            print(f"  conf {label}: n={b['n']} acc={acc}")
    print(f"spend: ${tracker.cost_usd:.6f} over {tracker.calls} calls")
    if misses:
        print("misses:")
        for m in misses:
            print(f"  {m}")


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
    p_plan.add_argument("--max-usd", type=float, default=PLAN_MAX_USD_DEFAULT)
    p_plan.add_argument("--out", required=True)

    p_story = sub.add_parser("storyboard")
    p_story.add_argument("decisions")
    p_story.add_argument("--out", required=True)

    p_eval = sub.add_parser("eval")
    p_eval.add_argument("groundtruth")
    p_eval.add_argument("--reps", type=int, default=2)
    p_eval.add_argument("--gate", type=float, default=DEFAULT_GATE)
    p_eval.add_argument("--state-lang", choices=["en", "th"], default="en")

    args = parser.parse_args(argv)
    if args.cmd == "plan":
        return cmd_plan(args)
    if args.cmd == "storyboard":
        return cmd_storyboard(args)
    if args.cmd == "eval":
        return cmd_eval(args)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
