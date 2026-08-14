#!/usr/bin/env python3
"""UserPromptSubmit hook: drain this session's mailbox and print it.

Task task-de2cdc15 (CEO directive 2026-08-14, option A). Read-side
counterpart to `lib/mailbox.py` -- modelled on `scripts/hook-recall.py`'s
shape: read the event JSON on stdin, print to stdout, fail silent with
`return 0` always. A hook that raises must never block a prompt.

Drains the CURRENT session's own box and prints the letters as context.
The box is resolved from env only -- `CXO_ROLE` + `CXO_SESSION_ID`
(`CTO_SESSION_ID` for a plain `cto-claude.sh` launch, which exports that
instead) for a C-level session, or `DEV_TASK_ID`/`DEV_ROLE` for a DEV
worktree -- the same resolution `tools/send_to_cxo.py`'s
`current_identity()` uses. Never from anything a caller passes: a prompt
cannot ask this hook to open somebody else's box.

Draining is exactly-once (`lib.mailbox.drain`), so the same letter is
never printed twice. Prints nothing when the box is empty -- this runs on
every prompt of every session, so silence (the common case) must cost
nothing.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _current_box() -> tuple[str, str] | None:
    """(role, session_id) for the box THIS session drains, or None if this
    session (e.g. a bare CEO shell) has no box of its own."""
    role = os.environ.get("CXO_ROLE")
    if role:
        sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
        return (role, sid) if sid else None
    task_id = os.environ.get("DEV_TASK_ID")
    if task_id:
        return os.environ.get("DEV_ROLE", "dev"), task_id
    return None


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    box = _current_box()
    if box is None:
        return 0
    role, session_id = box

    try:
        from lib import mailbox
        letters = mailbox.drain(role, session_id)
    except Exception:
        return 0
    if not letters:
        return 0

    print(f"## Mailbox — {len(letters)} letter(s) delivered (drained; each arrives once)")
    print()
    for letter in letters:
        frm = letter.get("from") or {}
        print(f"[{frm.get('role', '?')}#{frm.get('session_id', '?')}] {letter.get('sent_at', '')}")
        print(letter.get("body", ""))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
