"""Restore disconnected Claude Remote Control on idle local panes. Dry-run is read-only."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.pane_screen import prompt_ready, strip_ansi, typed_text
from tools import agent_transport, tmux_session

ROOT = Path(os.environ.get("ORG_ROOT", Path(__file__).resolve().parent.parent))
INTERVAL = 30 * 60


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=10)


def panes():
    result = run([tmux_session.tmux_bin(), "list-panes", "-a", "-F",
                  "#{session_name}\t#{pane_id}"])
    if result.returncode:
        raise RuntimeError("cannot list local tmux panes")
    return [line.split("\t", 1) for line in result.stdout.splitlines()]


def capture(pane):
    result = run([tmux_session.tmux_bin(), "capture-pane", "-p", "-e", "-S", "-60", "-t", pane])
    if result.returncode:
        raise RuntimeError("cannot capture pane")
    return result.stdout


def status(screen):
    matches = re.findall(r"Remote Control\s+(disconnected|connected|active)\b",
                         strip_ansi(screen), re.I)
    return matches[-1].lower() if matches else None


def command(screen):
    # Only accept known slash commands, preferring the most recent footer hint.
    hints = re.findall(r"(?<!\S)/(remote-control|rc)\b", strip_ansi(screen))
    return "/" + hints[-1] if hints else "/remote-control"


def auth_status():
    result = run(["claude", "auth", "status"])
    try:
        value = json.loads(result.stdout).get("loggedIn")
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, bool) else None


def letter(session, kind):
    from tools import send_to_cto
    owner = "cto-fresh"
    if kind != "blocker":
        if session.startswith("project_head-"):
            from tools.mail_wake import _ph_record
            record = _ph_record(session.removeprefix("project_head-"))
            if record:
                owner = record["owner"]
        elif re.fullmatch(r"c[a-z]+-[\w-]+", session):
            owner = session
    role, sid = owner.split("-", 1)
    message = (f"Remote Control for {session}: CEO login required; no keys sent."
               if kind == "blocker" else
               f"Remote Control for {session}: three reconnect attempts failed; automatic retries stopped.")
    return send_to_cto.send("rc-reconnect", message, cto_id=sid, owner_role=role,
                            kind=kind, subject=f"rc-reconnect:{session}", wake=False)


def send(pane, cmd):
    if len(cmd) >= 100 or not prompt_ready(capture(pane)):
        raise RuntimeError("pane no longer idle")
    agent_transport._wake_tmux_send(pane, cmd)
    # The transport sends Enter (the tmux alias for C-m) with a guarded rescue.
    if typed_text(capture(pane)) == cmd:
        raise RuntimeError("Enter did not submit command")


def _tick(state, save, dry_run, now):
    out = []
    for session, pane in panes():
        if session.startswith(("mooniex-task-", "wd-")):
            continue
        try:
            screen = capture(pane)
            key = f"{session}:{pane}"
            rec = state.setdefault(key, {})
            current = status(screen)
            if current in ("connected", "active"):
                for field in ("attempts", "notified", "login_notified"):
                    rec.pop(field, None)
                continue
            if current != "disconnected":
                continue
            if "run /login" in strip_ansi(screen).lower():
                auth = auth_status()
                if auth is not True:
                    reason = "login required" if auth is False else "auth status unknown"
                    out.append(f"{session} {pane}: {reason}; no typing")
                    if auth is False and not rec.get("login_notified") and not dry_run:
                        rec["login_notified"] = bool(letter(session, "blocker"))
                        save()
                    continue
            if rec.get("attempts", 0) >= 3:
                out.append(f"{session} {pane}: stopped after three attempts")
                if not rec.get("notified") and not dry_run:
                    rec["notified"] = bool(letter(session, "fyi"))
                    save()
                continue
            if not prompt_ready(screen):
                out.append(f"{session} {pane}: busy/draft; skip")
                continue
            if "last" in rec and now - rec["last"] < INTERVAL:
                out.append(f"{session} {pane}: rate limited")
                continue
            cmd = command(screen)
            out.append(f"{session} {pane}: {'would send' if dry_run else 'send'} {cmd}")
            if not dry_run:
                rec.update(last=now, attempts=rec.get("attempts", 0) + 1)
                save()  # reserve before sending, including transport failures
                send(pane, cmd)
        except Exception as exc:
            out.append(f"{session} {pane}: skipped ({type(exc).__name__})")
    if not dry_run:
        save()
    return out


def tick(*, dry_run=False, now=None):
    directory = ROOT / "state"
    if (directory / "rc_reconnect.off").exists():
        return ["rc reconnect disabled"]
    path = directory / "rc_reconnect.json"

    def load():
        value = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(value, dict):
            raise ValueError("invalid reconnect state")
        return value

    now = time.time() if now is None else now
    if dry_run:
        return _tick(load(), lambda: None, True, now)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "rc_reconnect.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return ["rc reconnect already running"]
        state = load()  # malformed state fails closed, never resets retry limits

        def save():
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(state))
            temp.replace(path)

        return _tick(state, save, False, now)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        print("\n".join(tick(dry_run=args.dry_run)))
        return 0
    except Exception as exc:
        print(f"rc reconnect skipped: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
