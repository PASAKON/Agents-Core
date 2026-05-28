#!/usr/bin/env python3
"""PostToolUse Edit|Write hook — mark category as presented after the
tool succeeded. Means the user just answered ECC's fact gate for this
path; future paths in the same category should bypass.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gateguard_categories import category_for, mark_category_presented


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    tool = (data.get("tool_name") or "").lower()
    if tool not in ("edit", "write", "multiedit"):
        return

    # PostToolUse fires only on success; no further status check needed.
    tool_input = data.get("tool_input") or {}
    if tool == "multiedit":
        for e in tool_input.get("edits", []):
            cat = category_for(e.get("file_path", "") or "")
            if cat:
                mark_category_presented(cat)
    else:
        cat = category_for(tool_input.get("file_path", "") or "")
        if cat:
            mark_category_presented(cat)


if __name__ == "__main__":
    main()
