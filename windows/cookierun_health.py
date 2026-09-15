#!/usr/bin/env python3
"""cookierun_health.py -- one headless verdict on whether the farm is healthy.

Written for an hourly check that must NOT cost a screenshot. Screenshots never
leave a model's context, so a recurring visual check makes every later iteration
more expensive than the last (IRON-RULES 42). This answers from logs, file
mtimes and the app pipe instead, and only tells a human to go look when there is
something to look at.

    VERDICT: OK | PARKED | DOWN | STUCK | STALLING | NO-APP

The distinction that matters most is PARKED vs DOWN. Cookie Run is *supposed*
to be off while another agent holds the screen lease -- a check that cannot tell
those apart will either cry wolf every time someone borrows the machine, or
worse, "fix" it by starting the bot on top of their work.

Exit 0 = nothing to do (OK or PARKED). Exit 1 = needs attention.
"""
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

DATA = Path.home() / "Documents" / "CookieRunScript"
TOKEN = DATA / "modelplay" / "pipe_token"
LEASE = DATA / "modelplay" / "PC_LEASE.json"
MODELPLAY = DATA / "modelplay"
STALLS = Path.home() / "cookierun-bot" / "label_review" / "stalls"

ROUND_QUIET_S = 12 * 60      # a round runs ~5 min; 12 min of silence is stuck
STALL_WINDOW_S = 2 * 60 * 60  # stall screenshots written in the last 2 h


def pipe_status():
    try:
        tok = TOKEN.read_text().strip()
    except OSError:
        return None
    req = urllib.request.Request("http://127.0.0.1:8794/status",
                                 headers={"X-Pipe-Token": tok})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def lease_now():
    try:
        d = json.loads(LEASE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d if d.get("expires_at", 0) > time.time() else None


def newest_session():
    try:
        dirs = [p for p in MODELPLAY.glob("session-*") if p.is_dir()]
    except OSError:
        return None, 0, None
    if not dirs:
        return None, 0, None
    d = max(dirs, key=lambda p: p.stat().st_mtime)
    runs = len([x for x in d.iterdir() if x.is_dir()])
    return d.name, runs, d.stat().st_mtime


def recent_stalls():
    if not STALLS.is_dir():
        return 0, 0
    files = list(STALLS.glob("*.png"))
    cutoff = time.time() - STALL_WINDOW_S
    return len(files), len([f for f in files if f.stat().st_mtime > cutoff])


def free_gb():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-PSDrive C).Free"],
            capture_output=True, text=True, timeout=25,
            creationflags=0x08000000).stdout.strip()
        return round(int(out) / (1024 ** 3), 1)
    except Exception:
        return None


def main() -> int:
    s = pipe_status()
    lease = lease_now()
    sess, runs, mtime = newest_session()
    stalls_total, stalls_recent = recent_stalls()
    gb = free_gb()
    age_min = int((time.time() - mtime) / 60) if mtime else None

    lines = []
    verdict = "OK"
    reason = ""

    if s is None:
        verdict, reason = "NO-APP", "the Cookie Run app is not running, so nothing can drive the bot"
    elif s.get("esc_hold"):
        verdict, reason = "DOWN", "ESC hold is set - a human stopped the bot and only a human clears it"
    elif lease:
        verdict = "PARKED"
        reason = f"screen lent to {lease.get('who', '?')} until {time.strftime('%H:%M', time.localtime(lease['expires_at']))}"
    elif not s.get("bot_alive"):
        verdict, reason = "DOWN", "nobody holds the screen and the bot is not running"
    elif s.get("job") == "preflight":
        verdict, reason = "OK", "preflight dry round in progress"
    elif age_min is not None and age_min > ROUND_QUIET_S / 60:
        verdict, reason = "STUCK", f"bot is alive but has written nothing for {age_min} min"
    elif stalls_recent:
        verdict, reason = "STALLING", f"{stalls_recent} screen(s) the navigator could not name in the last 2 h"

    lines.append(f"VERDICT: {verdict}")
    if reason:
        lines.append(f"reason : {reason}")
    if s:
        lines.append(f"bot    : alive={s.get('bot_alive')} job={s.get('job')} "
                     f"guard={s.get('night_guard')} esc_hold={s.get('esc_hold')} "
                     f"played_24h={s.get('played_fraction_24h')}")
    lines.append(f"lease  : {'held by ' + str(lease.get('who')) if lease else 'free'}")
    lines.append(f"rounds : {sess} runs={runs} last_write={age_min} min ago")
    lines.append(f"stalls : {stalls_total} total, {stalls_recent} in the last 2 h")
    lines.append(f"disk   : {gb} GB free on C:")
    print("\n".join(lines))

    return 0 if verdict in ("OK", "PARKED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
