#!/usr/bin/env python3
"""PreToolUse Edit|Write hook — short-circuit if the file's category has
already had facts presented this session.

Output schema (stdout JSON):
  { "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "allow" } }

Pass-through (empty stdout) lets the next hook (ECC GateGuard) decide.

Disable entirely: export MOONIEX_GATEGUARD_CATEGORY_OFF=1
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gateguard_categories import category_for, is_category_presented


def main() -> None:
    if os.environ.get("MOONIEX_GATEGUARD_CATEGORY_OFF", "").strip() == "1":
        return

    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    tool = (data.get("tool_name") or "").lower()
    if tool not in ("edit", "write", "multiedit"):
        return

    tool_input = data.get("tool_input") or {}

    # MultiEdit has edits[]; single-file Edit/Write has file_path
    if tool == "multiedit":
        file_paths = [e.get("file_path", "") for e in tool_input.get("edits", [])]
    else:
        file_paths = [tool_input.get("file_path", "")]

    # Only short-circuit if ALL paths are in already-presented categories.
    # If ANY path is in an unknown or un-presented category, pass-through to ECC.
    for fp in file_paths:
        cat = category_for(fp or "")
        if cat is None or not is_category_presented(cat):
            return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }))


if __name__ == "__main__":
    main()
