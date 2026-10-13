"""Read this session's own mailbox: list the letters, or read one in full.

Envelope mail (org restructure P1, `ORG_MAIL_ENVELOPE=1`): scripts/hook-inbox.py
prints one envelope line per letter and leaves out a body over 400 characters.
This is the CLI half of reading it back; the org MCP tools `read_letter` /
`list_letters` call the same two functions in lib/mailbox.py.

The box is resolved from this process's env only (`lib.mailbox.current_box`:
CXO_ROLE + CXO_SESSION_ID/CTO_SESSION_ID, or WORKER_TASK_ID + WORKER_ROLE),
never from an argument, so no caller can open another session's box.

Usage:
    python -m tools.letters list [--unread] [--limit N] [--json]
    python -m tools.letters read <id> [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import mailbox  # noqa: E402

NO_BOX = ("no mailbox for this process: it has no CXO_ROLE + CXO_SESSION_ID "
          "(or CTO_SESSION_ID), and no WORKER_TASK_ID")


def render_list(items: list[dict]) -> str:
    if not items:
        return "no letters (read ones are kept 7 days in envelope mode)"
    lines = []
    for d in items:
        state = "unread" if d.get("unread") else f"read {d.get('read_at') or ''}".strip()
        tag = d.get("kind") or "message"
        if (d.get("prio") or "normal") != "normal":
            tag = f"{tag}/{d['prio']}"
        lines.append(f"[{d.get('id')}] {tag.upper()} from {d.get('from')} · "
                     f"{d.get('sent_at') or ''} · {d.get('chars')} chars · {state} · "
                     f"{d.get('subject') or ''}")
    return "\n".join(lines)


def render_letter(letter: dict) -> str:
    frm = letter.get("from") or {}
    head = (f"[{letter.get('id')}] {str(letter.get('kind') or 'message').upper()}"
            f"/{letter.get('prio') or 'normal'} from {frm.get('role', '?')}:"
            f"{frm.get('session_id', '?')} · sent {letter.get('sent_at') or '?'}"
            f" · read {letter.get('read_at') or '-'}\n"
            f"subject: {letter.get('subject') or ''}\n")
    return head + "\n" + str(letter.get("body") or "")


def list_text(*, unread_only: bool = False, limit: int = 20) -> str:
    box = mailbox.current_box()
    if box is None:
        return NO_BOX
    return render_list(mailbox.list_letters(*box, include_read=not unread_only, limit=limit))


def read_text(letter_id: str) -> str:
    box = mailbox.current_box()
    if box is None:
        return NO_BOX
    letter = mailbox.read_letter(*box, letter_id)
    if letter is None:
        return f"no letter {letter_id!r} in this session's box (read ones are kept 7 days)"
    return render_letter(letter)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.letters", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="the box's letters, newest first")
    ls.add_argument("--unread", action="store_true", help="unread letters only")
    ls.add_argument("--limit", type=int, default=20)
    ls.add_argument("--json", action="store_true")
    rd = sub.add_parser("read", help="one letter in full")
    rd.add_argument("id")
    rd.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    box = mailbox.current_box()
    if box is None:
        print(NO_BOX, file=sys.stderr)
        return 2
    if args.cmd == "list":
        items = mailbox.list_letters(*box, include_read=not args.unread, limit=args.limit)
        print(json.dumps(items, ensure_ascii=False, indent=2) if args.json else render_list(items))
        return 0
    letter = mailbox.read_letter(*box, args.id)
    if letter is None:
        print(f"no letter {args.id!r} in this session's box", file=sys.stderr)
        return 1
    print(json.dumps(letter, ensure_ascii=False, indent=2) if args.json else render_letter(letter))
    return 0


if __name__ == "__main__":
    sys.exit(main())
