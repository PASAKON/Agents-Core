#!/usr/bin/env python3
"""TraderMindset deterministic content checks (the code-side validator).

This is the canonical, reusable validator library for caption content. Two
consumers:

  * scripts/tm_prompt_eval.py  — the deterministic half of the A/B eval gate
    (length / emoji / banned-phrase / percentage). The other half is an LLM
    voice/quality judge.
  * scripts/tm_prompt_evolve.py — the *destination* of a PROMOTE-TO-VALIDATOR
    flag: when a reject category repeats ≥2 rounds the rule must become code
    HERE, not another prompt tweak (the LuNar lesson: prompt rules half-fail).

Design note — what is and isn't deterministic
---------------------------------------------
Reliable as code: emoji, profit-guarantee phrases, explicit %/returns, length.
NOT reliable as a substring rule: "investment advice". A CEO-APPROVED week-1
post literally says "…ทำให้เราเข้าออเดอร์ได้สวย" (descriptive, not a signal), so
a bare "เข้าออเดอร์" blocklist would false-positive known-good content. Directive
detection is therefore returned as a SOFT signal (warnings), and the real gate
for advice/tone is the LLM judge in the eval harness — not a hard code fail.

The shipped generator keeps its own tiny inline guard (trader_mindset_batch
._assert_caption_clean); we reuse its exact emoji regex here so the emoji shape
has a single source of truth, and extend the banned list as a superset.

No network, no API key — pure functions, fully unit-testable offline.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trader_mindset_batch import _EMOJI_RE  # noqa: E402  single source for emoji shape

# --------------------------------------------------------------------------- #
# Limits (CEO hard-rules + week-1 voice). Tuned so every CEO-approved week-1
# caption passes with margin, while the must-fail golden cases trip.
# --------------------------------------------------------------------------- #
CAPTION_MAX_CHARS = 600      # week-1 longest ~200; "too long" negative ~800+
SUBLINE_MAX_CHARS = 40       # matches the caption prompt's "<= 40 ตัวอักษร" spec

# Profit-guarantee phrases. Superset of the generator's inline list; these are
# unambiguous in Thai trading copy and absent from every week-1 post.
GUARANTEE_PHRASES = [
    "การันตีกำไร", "การันตี", "รับรองกำไร", "รับประกันกำไร", "การันตีผลตอบแทน",
    "รวยแน่", "รวยเร็ว", "ได้แน่นอน", "กำไรแน่นอน", "กำไรแน่", "ไม่มีทางขาดทุน",
    "คืนทุนแน่", "ผลตอบแทนแน่นอน",
]

# Directive / signal phrases — SOFT only (see module docstring). Imperative,
# trade-instruction style; not mere mentions of trading concepts.
DIRECTIVE_PHRASES = [
    "ซื้อเลย", "ขายเลย", "เข้าเลย", "เข้าออเดอร์เลย", "เปิดออเดอร์เลย",
    "ให้ซื้อ", "ให้ขาย", "ฟันธง", "แนะนำให้เข้า", "สัญญาณเข้า", "จุดเข้าออเดอร์",
    "เป้าราคา", "ลากยาว", "ทุบราคา", "ตามไม้นี้",
]

# Explicit numeric-return language ("ห้ามพูดถึงผลตอบแทนเป็นตัวเลข/เปอร์เซ็นต์").
_PERCENT_RE = re.compile(r"\d+\s*%|เปอร์เซ็น|เปอร์เซ็นต์|เท่าตัว|พันเปอร์เซ็น")


# --------------------------------------------------------------------------- #
# Atomic checks
# --------------------------------------------------------------------------- #
def has_emoji(text: str) -> bool:
    """True if any emoji/pictograph is present (CEO rule: no emoji)."""
    return bool(_EMOJI_RE.search(text or ""))


def find_guarantee(text: str) -> list[str]:
    """Profit-guarantee phrases present in the text (longest-match, de-duped)."""
    t = text or ""
    hits: list[str] = []
    for phrase in sorted(GUARANTEE_PHRASES, key=len, reverse=True):
        if phrase in t and not any(phrase in h for h in hits):
            hits.append(phrase)
    return hits


def has_percentage(text: str) -> bool:
    """True if the text quotes a numeric/percentage return."""
    return bool(_PERCENT_RE.search(text or ""))


def find_directive(text: str) -> list[str]:
    """Directive/signal phrases (SOFT signal — warnings, not a hard fail)."""
    t = text or ""
    return [p for p in DIRECTIVE_PHRASES if p in t]


def caption_length(caption: str) -> int:
    return len(caption or "")


def subline_length(sub_line: str) -> int:
    return len(sub_line or "")


# --------------------------------------------------------------------------- #
# Aggregate
# --------------------------------------------------------------------------- #
def check_caption(caption: str, sub_line: str = "", tags=None) -> dict:
    """Run all hard checks on a candidate caption + sub-line.

    Returns a structured verdict::

        {
          "passed": bool,            # all HARD checks pass
          "checks": {name: bool},    # True = ok for each hard check
          "violations": [str],       # human-readable, hard failures only
          "warnings": [str],         # soft signals (directive/advice)
          "caption_len": int, "subline_len": int,
          "score": float,            # 0..1 deterministic quality score
        }
    """
    caption = caption or ""
    sub_line = sub_line or ""
    blob = caption + "\n" + sub_line

    emoji_ok = not has_emoji(blob)
    guarantees = find_guarantee(blob)
    guarantee_ok = not guarantees
    percent_ok = not has_percentage(blob)
    cap_len = caption_length(caption)
    sub_len = subline_length(sub_line)
    caption_len_ok = cap_len <= CAPTION_MAX_CHARS
    subline_len_ok = sub_len <= SUBLINE_MAX_CHARS

    checks = {
        "emoji": emoji_ok,
        "guarantee": guarantee_ok,
        "percentage": percent_ok,
        "caption_length": caption_len_ok,
        "subline_length": subline_len_ok,
    }
    violations: list[str] = []
    if not emoji_ok:
        violations.append("contains emoji")
    if not guarantee_ok:
        violations.append("profit-guarantee phrase(s): " + ", ".join(guarantees))
    if not percent_ok:
        violations.append("quotes a numeric/percentage return")
    if not caption_len_ok:
        violations.append(f"caption too long ({cap_len} > {CAPTION_MAX_CHARS} chars)")
    if not subline_len_ok:
        violations.append(f"sub_line too long ({sub_len} > {SUBLINE_MAX_CHARS} chars)")

    warnings = [f"directive/signal phrase: {p}" for p in find_directive(blob)]

    # Deterministic score: full marks minus an even share per failed hard check.
    score = sum(1 for ok in checks.values() if ok) / len(checks)

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "violations": violations,
        "warnings": warnings,
        "caption_len": cap_len,
        "subline_len": sub_len,
        "score": score,
    }
