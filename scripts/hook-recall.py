#!/usr/bin/env python3
"""UserPromptSubmit hook: auto-recall relevant past org work.

Runs the CEO's prompt through lib.recall and surfaces the top confident
matches (past tasks: status, merge sha, gist) as additional context, so the
CTO sees prior work BEFORE planning — without having to call recall by hand.
This is the read-side counterpart to the write-only event log.

Gated to CTO sessions (CTO_SESSION=1). Prints nothing when there's no strong
match, so ordinary prompts stay clean. The tokenizer is ASCII, so it keys off
English nouns embedded in Thai prompts (leaderboard / deploy / claudeflow /
lunar); pure-Thai prompts simply produce no match.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MIN_SCORE = 3   # at least one title hit (×3) or several body hits
MAX_HITS = 3
MIN_PROMPT_LEN = 8


def main() -> int:
    if os.environ.get("CTO_SESSION") != "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = (payload.get("prompt") or "").strip()
    if len(prompt) < MIN_PROMPT_LEN:
        return 0

    try:
        from lib import recall as recall_lib
        hits = recall_lib.recall(prompt, limit=MAX_HITS)
    except Exception:
        return 0

    hits = [h for h in hits if h["score"] >= MIN_SCORE]
    if not hits:
        return 0

    print("## Recall — relevant past work (auto; verify it's still current before acting)")
    print()
    for i, h in enumerate(hits, 1):
        age = f" ({h['age_days']}d ago)" if h.get("age_days") is not None else ""
        print(f"{i}. {h['task_id']} [{h['project']}] {h['status']} · {h['updated_at']}{age} — {h['title']}")
        print(f"   → {h['outcome']}")
        if h.get("superseded_by"):
            print("   ⚠ newer work touched same files — verify current: "
                  + ", ".join(h["superseded_by"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
