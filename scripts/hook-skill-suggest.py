#!/usr/bin/env python3
"""UserPromptSubmit hook — detect skill-trigger keywords in user prompt
and inject a one-line reminder so the AI doesn't miss the trigger.

Reads JSON event from stdin (Claude Code hook contract):
  {"prompt": "...", "session_id": "...", ...}

Writes a one-line context block to stdout if a trigger matches.
Silent (exit 0) if no match.
"""
from __future__ import annotations

import json
import re
import sys

TRIGGERS: list[tuple[str, str, str]] = [
    # (regex, skill_name, reason)
    (
        r"(?i)\b(bug|broken|throwing|throws|crash|crashes|crashed|hang|hangs|hanging|stack ?trace|traceback|fail(s|ed|ing)?|error)\b",
        "debug-mantra",
        "Debug session detected — invoke /debug-mantra (recite 4-step mantra before any fix).",
    ),
    (
        r"(?i)\b(review|audit|sanity[- ]?check|second opinion|look over|scrutinize)\b",
        "scrutinize",
        "Review request detected — invoke /scrutinize (simpler-alternative pass first).",
    ),
    (
        r"(?i)\b(post[- ]?mortem|rca|root[- ]?cause|document the fix|writeup|write[- ]?up)\b",
        "post-mortem",
        "RCA request detected — invoke /post-mortem (requires repro+root cause+validated fix).",
    ),
    (
        r"(?i)\b(merge|ship|land|approve)\b.*\b(task|pr|branch)\b",
        "cto-merge-checklist",
        "Merge intent detected — run /cto-merge-checklist gates before merge_task.",
    ),
    (
        r"(?i)\b(spawn dev|delegate|kick.?off the dev|start the developer)\b",
        "dev-spawn-protocol",
        "DEV spawn detected — follow /dev-spawn-protocol (touches lock + kickoff ping).",
    ),
]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    prompt = event.get("prompt") or event.get("user_prompt") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return 0

    for regex, skill, reason in TRIGGERS:
        if re.search(regex, prompt):
            print(f"[skill-suggest] {skill}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
