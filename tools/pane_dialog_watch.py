"""One read-only tmux scan; notify the CEO about unattended dialogs."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from lib.roles import c_level_roles

ROOT = Path(__file__).resolve().parent.parent
WAIT_SECONDS = 300
DIALOG_MARKERS = (
    "Do you want to proceed?",
    "Yes, and don't ask again",
    "No, and tell Claude what to do differently",
    "Yes, I trust this folder",
)


def tmux(args):
    return subprocess.run(
        ["tmux", *args], check=True, capture_output=True, text=True, timeout=10,
    ).stdout


def notify_ceo(message):
    from lib.telegram_out import send_to_ceo

    return send_to_ceo(message)


def dialog_line(text):
    for line in text.splitlines():
        if any(marker in line for marker in DIALOG_MARKERS):
            return line.strip()[:200]
    return None


def run_once(*, runner=tmux, notifier=notify_ceo, now=None):
    now = time.time() if now is None else now
    threshold = float(os.environ.get("PANE_DIALOG_WATCH_SECONDS", WAIT_SECONDS))
    if threshold < 0 or not threshold < float("inf"):
        raise ValueError("PANE_DIALOG_WATCH_SECONDS must be finite and nonnegative")
    path = Path(os.environ.get("PANE_DIALOG_WATCH_STATE", ROOT / "state/pane-dialog-watch.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Timer and manual runs share a lock, including notification + state update.
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = json.loads(path.read_text()) if path.exists() else {}
        panes = runner(["list-panes", "-a", "-F", "#{session_name}\t#{pane_id}"])
        current = {}
        failures = 0
        prefixes = tuple(role + "-" for role in c_level_roles())
        for entry in panes.splitlines():
            session, pane = entry.split("\t", 1)
            if session != "sompong" and not any(
                session.startswith(prefix) and len(session) > len(prefix)
                for prefix in prefixes
            ):
                continue
            key = json.dumps([session, pane])
            try:
                # No scrollback: old dialogs must not keep a cleared pane blocked.
                line = dialog_line(runner(["capture-pane", "-p", "-t", pane]))
            except (OSError, subprocess.SubprocessError):
                if key in previous:
                    current[key] = previous[key]
                failures += 1
                continue
            if line is None:
                continue
            record = previous.get(key, {"first_seen": now, "notified": False})
            current[key] = record
            if not record["notified"] and now - record["first_seen"] >= threshold:
                message = (
                    f"CEO action needed: {session} ({pane}) is waiting for a "
                    f"permission/confirmation answer ({int(now - record['first_seen'])}s).\n"
                    f"{line}"
                )
                result = notifier(message)
                if result.get("ok"):
                    record["notified"] = True
                else:
                    failures += 1
            # Persist each successful notice before attempting another pane.
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(json.dumps({**previous, **current}) + "\n")
            temporary.replace(path)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(current) + "\n")
        temporary.replace(path)
        return failures


def main():
    try:
        failures = run_once()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print("pane-dialog-watch: scan/state failure; state retained", file=sys.stderr)
        return 1
    if failures:
        print(f"pane-dialog-watch: {failures} capture/notification failures; will retry", file=sys.stderr)
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
