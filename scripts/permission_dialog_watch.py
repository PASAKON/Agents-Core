#!/usr/bin/env python3
"""Tell the CEO when a C-level session has been stuck on a permission dialog.

GH #182 part 3. A C-level session on Contabo is driven from the phone
(MoonieX Console). When claude stops on a confirmation dialog ("Do you want
to proceed?", the folder-trust prompt, ...), the phone cannot see it, so the
session sits wedged and nobody knows. On 2026-09-28 CTO #4bb20df8 did exactly
that after four classifier refusals.

One pass (run it every minute from permission-dialog-watch.timer):
  1. list tmux sessions named `<role>-<id>` for every C-level role;
  2. read each one's visible screen and look for a dialog;
  3. remember when each dialog was first seen (state file);
  4. once a dialog has waited longer than --after (default 5 min), write ONE
     letter to SomPong's mailbox. The secretary waker already turns those
     letters into a Telegram message, so this needs no secret of its own.
A session whose dialog clears is forgotten, so a later dialog alerts again.

Stays until the Console shows these dialogs as a card (the Console issue filed
with GH #182); then this timer can be removed.

    python scripts/permission_dialog_watch.py            # one pass
    python scripts/permission_dialog_watch.py --dry-run  # print, write nothing
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import mailbox  # noqa: E402
from tools.session_name import ROLE_RE  # noqa: E402
from tools.tmux_session import TRUST_DIALOG_MARKER, tmux_bin  # noqa: E402

SECRETARY_ROLE = "secretary"      # same box lib/ceo_report.py writes to
SECRETARY_SESSION = "sompong"
STATE_PATH = ROOT / "state" / "permission_dialog_watch.json"
DEFAULT_AFTER_S = 300

# Claude Code's confirmation dialogs all ask "Do you want to ..." above a
# numbered "1. Yes" choice; the folder-trust prompt has its own wording.
_ASK_RE = re.compile(r"Do you want to (proceed|make this edit|create|allow|run|use|fetch|overwrite)")
_YES_RE = re.compile(r"^\s*(?:❯\s*)?1\.\s*Yes\b", re.MULTILINE)


def dialog_text(screen: str) -> str | None:
    """The dialog's question line when `screen` shows one, else None."""
    if TRUST_DIALOG_MARKER in screen:
        return "folder-trust prompt (Enter picks 'No, exit')"
    m = _ASK_RE.search(screen)
    if m and _YES_RE.search(screen):
        line = next((ln.strip() for ln in screen.splitlines() if m.group(0) in ln), m.group(0))
        return line[:200]
    return None


def _run(argv: list[str]) -> str:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout if r.returncode == 0 else ""


def c_level_sessions() -> list[str]:
    out = _run([tmux_bin(), "list-sessions", "-F", "#{session_name}"])
    return [s for s in out.splitlines() if ROLE_RE.match(s.strip())]


def screen_of(session: str) -> str:
    return _run([tmux_bin(), "capture-pane", "-t", session, "-p"])


def load_state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def alert_body(session: str, question: str, waited_s: float) -> str:
    return (
        f"[permission-dialog-watch] {session} has been waiting on a permission "
        f"dialog for {int(waited_s // 60)} min and the phone cannot see it: "
        f"\"{question}\". Someone has to answer it at the box (tmux attach -t "
        f"{session}) or the session stays stuck. GH #182"
    )


def notify(body: str, *, root: Path | None = None) -> Path:
    """Letter into SomPong's box. The waker runs as the `secretary` user, so
    the letter takes the box directory's owner; root-owned 0600 would be
    unreadable to it."""
    path = mailbox.send(SECRETARY_ROLE, SECRETARY_SESSION, body,
                        "watchdog", "permission-dialog", root=root)
    try:
        st = path.parent.stat()
        if os.geteuid() == 0 and (st.st_uid, st.st_gid) != (0, 0):
            os.chown(path, st.st_uid, st.st_gid)
    except (OSError, AttributeError):
        pass
    return path


def run_once(*, after_s: float, state_path: Path, dry_run: bool = False,
             now: float | None = None, sessions=None, screen=None, send=None) -> list[str]:
    """One pass. Returns the sessions alerted this pass. `sessions`, `screen`
    and `send` are injectable for tests."""
    now = time.time() if now is None else now
    sessions = sessions or c_level_sessions
    screen = screen or screen_of
    send = send or notify

    prev = load_state(state_path)
    state: dict = {}
    alerted: list[str] = []
    for sess in sessions():
        question = dialog_text(screen(sess))
        if not question:
            continue  # cleared or never there: forget it
        entry = prev.get(sess) or {}
        if entry.get("question") != question:
            entry = {"question": question, "first_seen": now, "alerted": False}
        waited = now - float(entry["first_seen"])
        if waited >= after_s and not entry.get("alerted"):
            body = alert_body(sess, question, waited)
            if dry_run:
                print(f"would alert: {body}")
            else:
                send(body)
            entry["alerted"] = True
            alerted.append(sess)
        state[sess] = entry
    if not dry_run:
        save_state(state_path, state)
    return alerted


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--after", type=float, default=DEFAULT_AFTER_S,
                    help="seconds a dialog may wait before the CEO is told (default 300)")
    ap.add_argument("--state", type=Path, default=STATE_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    alerted = run_once(after_s=args.after, state_path=args.state, dry_run=args.dry_run)
    if alerted:
        print(f"alerted: {', '.join(alerted)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
