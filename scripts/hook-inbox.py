#!/usr/bin/env python3
"""UserPromptSubmit hook: drain this session's mailbox and print it.

Task task-de2cdc15 (CEO directive 2026-08-14, option A). Read-side
counterpart to `lib/mailbox.py` -- modelled on `scripts/hook-recall.py`'s
shape: read the event JSON on stdin, print to stdout, fail silent with
`return 0` always. A hook that raises must never block a prompt.

Drains the CURRENT session's own box and prints the letters as context.
The box is resolved from env only -- `CXO_ROLE` + `CXO_SESSION_ID`
(`CTO_SESSION_ID` for a plain `cto-claude.sh` launch, which exports that
instead) for a C-level session, or `WORKER_TASK_ID`/`WORKER_ROLE` for a DEV
worktree -- the same resolution `tools/send_to_cxo.py`'s
`current_identity()` uses. Never from anything a caller passes: a prompt
cannot ask this hook to open somebody else's box.

Draining is exactly-once (`lib.mailbox.drain`), so the same letter is
never printed twice. Prints nothing when the box is empty -- this runs on
every prompt of every session, so silence (the common case) must cost
nothing.

Also, for a C-level session only, makes sure the host's live-sessions
publisher is running (`tools.live_sessions.ensure_publisher`, task-9c563bea).
A hook SCRIPT is read from disk on every prompt, unlike the hook CONFIG, which
Claude Code snapshots at startup -- so a `git pull` is the whole rollout: the
next prompt on that host starts the publisher. One open + flock when it is
already alive; nothing printed, nothing raised.
"""
from __future__ import annotations

import contextlib
import io
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
    task_id = os.environ.get("WORKER_TASK_ID")
    if task_id:
        return os.environ.get("WORKER_ROLE", "dev"), task_id
    return None


def _ensure_live_publisher() -> None:
    """C-level sessions only (CXO_ROLE set, no WORKER_TASK_ID). Ignores the
    result and every error: this must never cost a prompt anything."""
    try:
        if not os.environ.get("CXO_ROLE") or os.environ.get("WORKER_TASK_ID"):
            return
        # scripts/test_mailbox.py drives main() with CXO_ROLE set; a test run
        # must not start a publisher against the real hub
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        # a hook's stdout becomes the model's context on EVERY prompt: whatever the
        # call writes, it never reaches it
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from tools import live_sessions
            live_sessions.ensure_publisher()
    except Exception:
        pass


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    _ensure_live_publisher()    # before the drain: an empty box still runs it
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
        role_label = str(frm.get("role") or "?").upper()
        print(f"[{role_label}] : {letter.get('body', '')}")
        print(f"    ({frm.get('session_id', '?')} · {letter.get('sent_at', '')})")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
