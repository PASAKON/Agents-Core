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

Envelope mode (`ORG_MAIL_ENVELOPE=1`, default off; org restructure P1): one
envelope line per letter (id, kind/prio, sender, time, subject), with the body
inline only when it is ENVELOPE_BODY_MAX characters or fewer; a longer one is
read with `read_letter("<id>")` (org MCP) or `python -m tools.letters read <id>`.
`lib.mailbox.drain` then marks the letters read instead of deleting them.
Off, the output is exactly as before.
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

ENVELOPE_BODY_MAX = 400


def _envelope_on() -> bool:
    return os.environ.get("ORG_MAIL_ENVELOPE", "").strip().lower() in ("1", "true", "yes", "on")


def _print_envelopes(letters: list[dict]) -> None:
    print(f"## Mailbox — {len(letters)} letter(s), marked read "
          f"(a body over {ENVELOPE_BODY_MAX} chars: read_letter(\"<id>\") "
          f"or `python -m tools.letters read <id>`)")
    print()
    for letter in letters:
        frm = letter.get("from") or {}
        who = f"{str(frm.get('role') or '?').upper()} {frm.get('session_id', '?')}"
        kind = str(letter.get("kind") or "message")
        prio = str(letter.get("prio") or "normal")
        tag = (kind if prio == "normal" else f"{kind}/{prio}").upper()
        lid = letter.get("id") or "?"
        body = str(letter.get("body") or "")
        subject = letter.get("subject") or " ".join(body.split())[:80]
        print(f"- [{lid}] {tag} from {who} · {letter.get('sent_at', '')} · {subject}")
        if len(body) <= ENVELOPE_BODY_MAX:
            for ln in body.splitlines() or [""]:
                print(f"    {ln}")
        else:
            print(f"    ({len(body)} chars, not shown: read_letter(\"{lid}\"))")
    print()


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

    if _envelope_on():
        _print_envelopes(letters)
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
