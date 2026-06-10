#!/usr/bin/env python3
"""TraderMindset reflective prompt updater (GEPA-style, lightweight).

Reads the prior round's reject reasons (natural language, not scores), reflects
on them, and proposes the NEXT prompt version as a DRAFT — it never activates a
prompt itself. Activation only happens after the eval gate (tm_prompt_eval.py)
returns a win and a human/CTO flips registry.active.

GEPA idea applied (DSPy/GEPA, ICLR 2026): mutate the prompt from natural-language
feedback rather than a scalar reward, propose a candidate, and select it with a
held-out evaluation. Here:

  reflect (this script)  ->  propose DRAFT v(N+1)  ->  eval A/B gate  ->  activate

The LuNar promote-rule (wiki §4.5, feedback_lunar_brevity_enforce_in_code):
a reject CATEGORY that recurs >= threshold rounds is NOT folded back into the
prompt (prompt rules half-fail). Instead it is flagged

    PROMOTE TO VALIDATOR: <rule to write as code>

so the rule moves into scripts/tm_checks.py (deterministic) or the eval judge.
Only sub-threshold, one-off lessons are folded into the draft prompt.

Lessons input format (claudeflow scripts/tm-export-lessons.js):
    [ { "slug": "...", "reason": "...", "date": "YYYY-MM-DD" }, ... ]

Usage:
  PY=/Users/gob/Projects/Agents/.venv/bin/python
  $PY scripts/tm_prompt_evolve.py --lessons lessons.json --dry            # no API
  $PY scripts/tm_prompt_evolve.py --lessons lessons.json --kind caption   # REAL (CTO)
  $PY scripts/tm_prompt_evolve.py --lessons lessons.json --out-dir /tmp/x # test sink

HARD RULE: --dry touches NO paid API (deterministic reflection + fixture). The
first REAL reflective rewrite (LLM-assisted) is run by the CTO (ask-before-paid).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tm_prompts  # noqa: E402

PROMOTE_THRESHOLD = 2   # same category >= this many rejects => code validator, not prompt

# Which prompt section absorbs folded (sub-threshold) lessons, per kind.
FOLD_SECTION = {"caption": "system", "poster": "preamble"}

# Reject-reason categorizer. Order matters: most specific first. Matching is a
# simple substring test against the (lower-cased) Thai/English reason text.
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("emoji", ["อิโมจิ", "อีโมจิ", "emoji", "สติกเกอร์", "ไอคอน"]),
    ("guarantee", ["การันตี", "รับรองกำไร", "รับประกัน", "รวยแน่", "ผลตอบแทน",
                   "เปอร์เซ็น", "กำไรแน่", "การันตีกำไร", "%"]),
    ("advice", ["ชี้นำ", "สัญญาณ", "บอกให้ซื้อ", "บอกให้ขาย", "เข้าออเดอร์",
                "แนะนำซื้อ", "แนะนำขาย", "ฟันธง", "ชี้เป้า", "เป้าราคา"]),
    ("too_long", ["ยาวเกิน", "ยาวไป", "ยาว", "กระชับ", "ตัดให้สั้น", "เยอะเกิน",
                  "สั้นลง", "too long"]),
    ("tone", ["โทน", "แข็ง", "ไม่สุภาพ", "กันเอง", "รุ่นพี่", "ทางการเกิน",
              "ไม่เป็นธรรมชาติ", "ห้วน", "คำลงท้าย"]),
    ("repetitive", ["ซ้ำ", "จำเจ", "ซ้ำซาก", "โครงเดิม", "เหมือนเดิม", "น่าเบื่อ"]),
    ("format", ["ย่อหน้า", "บรรทัด", "รูปแบบ", "format", "แฮชแท็ก", "hashtag", "แท็ก"]),
]

# Per-category: is it cleanly code-enforceable, and the concrete validator rule.
CATEGORY_META: dict[str, dict] = {
    "emoji": {
        "code": True,
        "rule": "tm_checks.has_emoji() already detects this — wire check_caption() "
                "into the generator's accept path so an emoji caption is auto-rejected "
                "before it is emailed.",
    },
    "guarantee": {
        "code": True,
        "rule": "Extend tm_checks.GUARANTEE_PHRASES / _PERCENT_RE with the new "
                "phrasing; check_caption() then hard-fails it deterministically.",
    },
    "too_long": {
        "code": True,
        "rule": "Lower/enforce tm_checks.CAPTION_MAX_CHARS / SUBLINE_MAX_CHARS in "
                "code — length is unreliable as a prompt instruction (LuNar lesson).",
    },
    "advice": {
        "code": "partial",
        "rule": "Add phrasing to tm_checks.DIRECTIVE_PHRASES (SOFT) AND require the "
                "eval LLM judge to reject directive captions — bare substring matching "
                "is false-positive-prone (week-1 uses 'เข้าออเดอร์' descriptively).",
    },
    "tone": {
        "code": False,
        "rule": "Not cleanly code-enforceable. Promote to the eval LLM judge as a "
                "scored voice dimension + human spot-check; stop re-tightening the prompt.",
    },
    "repetitive": {
        "code": False,
        "rule": "Not a regex. Add a similarity check vs prior captions "
                "(future: pgvector pre-screen, wiki §4.5) or a judge dimension.",
    },
    "format": {
        "code": True,
        "rule": "Add a structure check to tm_checks (e.g. '.'-only paragraph breaks, "
                "tag count) and enforce in code.",
    },
    "other": {
        "code": False,
        "rule": "Uncategorized — needs human review; cannot auto-promote to a validator.",
    },
}


# --------------------------------------------------------------------------- #
# Categorization
# --------------------------------------------------------------------------- #
def categorize(reason: str) -> str:
    """Map a free-text reject reason to a category key (or 'other')."""
    r = (reason or "").lower()
    for cat, kws in CATEGORY_KEYWORDS:
        if any(kw.lower() in r for kw in kws):
            return cat
    return "other"


def categorize_lessons(lessons: list[dict]) -> dict[str, list[dict]]:
    """Group lessons by category, preserving input order within a group."""
    grouped: dict[str, list[dict]] = {}
    for l in lessons:
        grouped.setdefault(categorize(l.get("reason", "")), []).append(l)
    return grouped


def split_promote_fold(grouped: dict[str, list[dict]], threshold: int):
    """Partition categories into (promote, fold) by recurrence threshold."""
    promote = {c: ls for c, ls in grouped.items() if len(ls) >= threshold}
    fold = {c: ls for c, ls in grouped.items() if len(ls) < threshold}
    return promote, fold


# --------------------------------------------------------------------------- #
# Draft construction (deterministic, --dry)
# --------------------------------------------------------------------------- #
def build_reflection_block(fold: dict[str, list[dict]]) -> str:
    """Render folded one-off lessons as durable do-not rules to bake into prompt."""
    if not fold:
        return ""
    lines = ["", "บทเรียนที่ห้ามพลาดซ้ำ (อัปเดตอัตโนมัติจาก reject รอบก่อน — tm_prompt_evolve):"]
    for cat, ls in fold.items():
        for l in ls:
            date = l.get("date", "?")
            reason = (l.get("reason", "") or "").strip()
            lines.append(f"- [{date}] {reason}")
    return "\n".join(lines)


def _fold_into_section(raw: str, section: str, reflection: str) -> str:
    """Append `reflection` inside the named fenced block, preserving everything else."""
    if not reflection:
        return raw
    pat = re.compile(
        r"(##[ \t]+" + re.escape(section) + r"[ \t]*\r?\n+```[A-Za-z]*\r?\n)(.*?)(\r?\n```)",
        re.S)
    m = pat.search(raw)
    if not m:
        raise ValueError(f"section {section!r} (fenced block) not found in prompt file")
    return raw[:m.start()] + m.group(1) + m.group(2) + "\n" + reflection + m.group(3) + raw[m.end():]


def make_draft_md(raw: str, kind: str, src_version: str, draft_version: str,
                  fold: dict, promote: dict, banner_date: str) -> str:
    """Produce the DRAFT markdown: provenance banner + folded reflection."""
    section = FOLD_SECTION[kind]
    promoted_str = ", ".join(f"{c}×{len(ls)}" for c, ls in promote.items()) or "none"
    folded_str = ", ".join(f"{c}×{len(ls)}" for c, ls in fold.items()) or "none"
    banner = (
        f"\n> **DRAFT {draft_version} — NOT ACTIVE.** Generated by `scripts/tm_prompt_evolve.py`"
        f" from {src_version} on {banner_date}.\n"
        f"> Folded (reflected into this prompt): {folded_str}."
        f" Promoted to validator (NOT in prompt): {promoted_str}.\n"
        f"> Activate ONLY after `scripts/tm_prompt_eval.py` reports a win vs {src_version},"
        f" then flip `registry.active.{kind}`.\n")
    # Insert the banner right after the first markdown title line.
    nl = raw.find("\n")
    raw = raw[: nl + 1] + banner + raw[nl + 1:] if nl != -1 else raw + banner
    reflection = build_reflection_block(fold)
    return _fold_into_section(raw, section, reflection)


# --------------------------------------------------------------------------- #
# Reflection via LLM (REAL run only — never under --dry)
# --------------------------------------------------------------------------- #
def reflect_llm(raw: str, kind: str, fold: dict, model: str) -> str:
    """Ask an LLM to integrate folded lessons into the prompt section, return new md.

    Reached only on a REAL run. Mirrors the generator's OpenRouter access so no new
    dependency is added. The deterministic --dry path does NOT call this.
    """
    import urllib.request

    import trader_mindset_batch as tm  # reuse env-key loader + endpoint (no new dep)
    key = tm.load_env_key("OPENROUTER_API_KEY")
    section = FOLD_SECTION[kind]
    current = tm_prompts.load_prompt(kind, tm_prompts.active_version(kind))[section]
    lessons_txt = "\n".join(
        f"- [{c}] {l.get('reason','')}" for c, ls in fold.items() for l in ls)
    messages = [
        {"role": "system", "content":
            "You refine a Thai marketing system-prompt. Integrate the recurring lessons "
            "as concise, durable rules WITHOUT bloating or changing the existing voice. "
            "Return ONLY the revised section text (no markdown fences, no commentary)."},
        {"role": "user", "content":
            f"Current `{section}` section:\n---\n{current}\n---\n\n"
            f"Recurring lessons to fold in:\n{lessons_txt}\n\n"
            "Return the full revised section text."},
    ]
    payload = {"model": model, "messages": messages, "temperature": 0.3}
    req = urllib.request.Request(
        tm.OPENROUTER_ENDPOINT, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://mooniex.com", "X-Title": "MoonieX TM evolve"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    new_section = data["choices"][0]["message"]["content"].strip()
    return _replace_section(raw, section, new_section)


def _replace_section(raw: str, section: str, new_text: str) -> str:
    pat = re.compile(
        r"(##[ \t]+" + re.escape(section) + r"[ \t]*\r?\n+```[A-Za-z]*\r?\n)(.*?)(\r?\n```)",
        re.S)
    m = pat.search(raw)
    if not m:
        raise ValueError(f"section {section!r} not found")
    return raw[:m.start()] + m.group(1) + new_text + m.group(3) + raw[m.end():]


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def render_report(kind: str, src_version: str, draft_version: str, total: int,
                  grouped: dict, promote: dict, fold: dict, draft_path: str,
                  threshold: int) -> str:
    out = ["=== tm_prompt_evolve report ===",
           f"kind: {kind}   active: {src_version} -> draft: {draft_version}",
           f"lessons: {total} (threshold for promote = {threshold})", ""]
    out.append("categories:")
    for cat, ls in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        tag = "[PROMOTE->validator]" if cat in promote else "[fold->prompt]"
        out.append(f"  {cat:<11} x{len(ls):<2} {tag}")
    out.append("")
    out.append("PROMOTE TO VALIDATOR (do NOT fix in prompt — code it in tm_checks / judge):")
    if promote:
        for cat, ls in promote.items():
            slugs = ", ".join(l.get("slug", "?") for l in ls)
            out.append(f"  PROMOTE TO VALIDATOR: [{cat} x{len(ls)}] {CATEGORY_META[cat]['rule']}")
            out.append(f"      offending slugs: {slugs}")
    else:
        out.append("  (none this round)")
    out.append("")
    out.append("Folded into draft prompt (sub-threshold, reflective):")
    if fold:
        for cat, ls in fold.items():
            for l in ls:
                out.append(f"  - [{cat}] ({l.get('date','?')}) {l.get('slug','?')}: {l.get('reason','')}")
    else:
        out.append("  (none — nothing sub-threshold to fold)")
    out.append("")
    out.append(f"draft written: {draft_path}  (NOT activated)")
    out.append(f"next step: scripts/tm_prompt_eval.py --kind {kind} --a {src_version} "
               f"--b {draft_version} --dry ; win => flip registry.active.{kind}")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def evolve(lessons: list[dict], kind: str, out_dir: str, dry: bool, model: str,
           threshold: int, banner_date: str | None) -> dict:
    """Core: categorize -> partition -> build draft -> write. Returns a summary dict."""
    grouped = categorize_lessons(lessons)
    promote, fold = split_promote_fold(grouped, threshold)

    src_version = tm_prompts.active_version(kind)
    raw = open(tm_prompts.prompt_path(kind, src_version), encoding="utf-8").read()

    # draft version = next free vN+1 across the real prompts dir (not the out_dir sink)
    draft_version = tm_prompts.next_version(kind)
    if banner_date is None:
        dates = [l.get("date") for l in lessons if l.get("date")]
        banner_date = max(dates) if dates else "unknown"

    if dry or not fold:
        draft_md = make_draft_md(raw, kind, src_version, draft_version, fold, promote, banner_date)
    else:
        # REAL: LLM integrates folded lessons, then bolt on the provenance banner.
        new_raw = reflect_llm(raw, kind, fold, model)
        draft_md = make_draft_md(new_raw, kind, src_version, draft_version, {}, promote, banner_date)

    os.makedirs(out_dir, exist_ok=True)
    draft_path = os.path.join(out_dir, f"{kind}-{draft_version}.md")
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(draft_md)

    return {"grouped": grouped, "promote": promote, "fold": fold,
            "src_version": src_version, "draft_version": draft_version,
            "draft_path": draft_path}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TraderMindset reflective prompt evolver (GEPA-style)")
    ap.add_argument("--lessons", metavar="PATH", required=True,
                    help="JSON [{slug,reason,date}] of prior-round rejects")
    ap.add_argument("--kind", choices=tm_prompts.KINDS, default="caption")
    ap.add_argument("--dry", action="store_true",
                    help="no paid API: deterministic reflection (still writes the DRAFT)")
    ap.add_argument("--out-dir", default=tm_prompts.PROMPTS_DIR,
                    help="where to write the draft (default: prompts/trader-mindset/)")
    ap.add_argument("--model", default=os.environ.get("TM_EVOLVE_MODEL", "anthropic/claude-3.5-sonnet"))
    ap.add_argument("--threshold", type=int, default=PROMOTE_THRESHOLD)
    ap.add_argument("--date", help="banner date override (default: max lesson date)")
    args = ap.parse_args(argv)

    with open(args.lessons, encoding="utf-8") as f:
        lessons = json.load(f)
    if not isinstance(lessons, list):
        sys.exit("lessons file must be a JSON array of {slug,reason,date}")

    res = evolve(lessons, args.kind, args.out_dir, args.dry, args.model,
                 args.threshold, args.date)
    print(render_report(args.kind, res["src_version"], res["draft_version"], len(lessons),
                        res["grouped"], res["promote"], res["fold"], res["draft_path"],
                        args.threshold))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
