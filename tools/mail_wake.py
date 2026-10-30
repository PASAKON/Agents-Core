"""Wake the session that waits on a mailbox letter, the moment a card ends.

The Console writes a Run Inbox result letter into `state/inbox/<box>/` when a card
ends (`<box>` = the card's `requester.session`, the mailbox name `<role>-<id>`:
cto-fresh, project_head-b2ff34d1, cmo-e785343f, dev-task-8669cf28) but never woke
the pane, so an idle session saw the CEO's answer only with the CEO's next chat
prompt (Q-20261029-2106-b3b3, Q-20261029-2021-4e31, Q-20261029-2038-68c3). The
Console now calls this once per box:

    python -m tools.mail_wake <box> [--label RUN-INBOX]

It wakes the box only when `state/inbox/<box>/` holds at least one unread `*.json`
letter, read no-follow (`lib.mailbox._BoxView`: this runs as root over boxes other
users can write, so a symlinked box or letter must never be followed).

  * `<role>-<sid>` with role a C-level or `project_head`: `send_to_cxo.attempt_wake`,
    at once. No debounce, because the session is waiting on that answer. Needs the
    venv's python (lib.config reads policies/agents.yaml) but not ORG_DB_URL.
  * `<role>-task-<8 hex>` (a worker): the tmux session `wd-<8 hex>`, which
    `tools/delegate.py` names with `tmux_session.session_name_for` and
    `tools/send_to_worker.py` wakes through the same `agent_transport.attempt_wake`.
    Derived from the box name, so no hub lookup: a task on another backend has no
    such session and is simply not woken.
  * Anything else: no wake.

Best effort, like `attempt_wake`: one JSON line {"box", "woke", "reason"}, exit 0
even when nothing could be woken, exit 2 only for a usage error (a missing box or a
name that is not one path segment). Never raises.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import mailbox  # noqa: E402
from lib.roles import PH_ROLE, c_level_roles  # noqa: E402

DEFAULT_LABEL = "RUN-INBOX"
# One path segment: the same rule the hub puts on requester.session.
BOX_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
# `<worker role>-<task id>`; the role is whatever WORKER_ROLE holds ("dev" by default).
WORKER_BOX_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*-(task-[0-9a-f]{8})")


def _result(box: str, woke: bool, reason: str) -> dict:
    return {"box": box, "woke": woke, "reason": reason}


def _has_unread(box_path: Path) -> bool:
    with mailbox._BoxView(box_path) as view:
        return view.ok and next(view.letters(), None) is not None


def wake(box: str, label: str = DEFAULT_LABEL) -> dict:
    """Wake `box`'s session if it has an unread letter. Never raises."""
    try:
        return _wake(box, label)
    except Exception as e:  # best effort: a broken wake must never fail the Console's call
        return _result(box, False, f"error: {type(e).__name__}")


def _wake(box: str, label: str) -> dict:
    if not BOX_RE.fullmatch(box):
        return _result(box, False, "invalid box name")
    box_path = mailbox.INBOX_ROOT / box
    if box_path.is_symlink():
        return _result(box, False, "box is a symlink, refused")
    if not _has_unread(box_path):
        return _result(box, False, "no unread letter")

    role, _, sid = box.partition("-")
    if sid and (role in c_level_roles() or role == PH_ROLE):
        from tools import send_to_cxo  # lazy: a refusal above never pays for the import

        woke = send_to_cxo.attempt_wake(role, sid, label)
    elif (m := WORKER_BOX_RE.fullmatch(box)):
        from tools import agent_transport, tmux_session

        woke = agent_transport.attempt_wake(
            tmux_session.session_name_for(m.group(1)), label, "mail_wake")
    else:
        return _result(box, False, "not a session box")
    return _result(box, bool(woke), "woke" if woke else "no live session reached")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tools.mail_wake", description=__doc__.split("\n")[0])
    p.add_argument("box", help="mailbox name <role>-<id>, as in the card's requester.session")
    p.add_argument("--label", default=DEFAULT_LABEL,
                   help=f"who the wake says it is from (default {DEFAULT_LABEL})")
    args = p.parse_args(argv)
    print(json.dumps(wake(args.box, args.label)))
    return 0 if BOX_RE.fullmatch(args.box) else 2


if __name__ == "__main__":
    sys.exit(main())
