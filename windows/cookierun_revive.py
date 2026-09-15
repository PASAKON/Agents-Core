#!/usr/bin/env python3
"""cookierun_revive.py -- restart the farm when it has stopped and nothing owns the stop.

On 2026-09-15 the game exited around 23:32. The bot's own recovery ladder did
exactly what it should -- back out, restart BlueStacks, and after 41 minutes give
up and stop rather than flail at a screen it could not read. That part worked.

What did not work is what happened next: nothing. The farm sat dead for an hour
and a half until a human-driven hourly check noticed. A give-up is recoverable --
minutes after it stopped, a fresh launch reached the lobby on its own -- so the
only thing missing was somebody to press start.

This is that somebody. A scheduled task, so it does not depend on any session
being open.

It refuses to start in three cases, and each refusal matters more than the restart:
  * a screen lease is held      -> another agent is using the desktop
  * ESC_HOLD is set             -> a human stopped the bot; only a human clears it
  * the bot is already alive    -> nothing to do
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

DATA = Path.home() / "Documents" / "CookieRunScript"
TOKEN = DATA / "modelplay" / "pipe_token"
LEASE = DATA / "modelplay" / "PC_LEASE.json"
LOG = DATA / "modelplay" / "cookierun_revive.log"

# How long the farm must have been down before we step in. Long enough that a
# deliberate short stop (someone restarting it by hand, a preflight between
# runs) is never fought over; short enough that a dead night is impossible.
DOWN_GRACE_S = 10 * 60
COOLDOWN_S = 30 * 60          # never retry a failed revive faster than this
STATE = DATA / "modelplay" / "revive_state.json"


def log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass


def pipe(method: str, path: str, body: dict | None = None, timeout: int = 90):
    try:
        tok = TOKEN.read_text().strip()
    except OSError:
        return None
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:8794{path}", data=data, method=method,
        headers={"X-Pipe-Token": tok, "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def last_write_age_s() -> float | None:
    try:
        dirs = [p for p in (DATA / "modelplay").glob("session-*") if p.is_dir()]
    except OSError:
        return None
    if not dirs:
        return None
    return time.time() - max(d.stat().st_mtime for d in dirs)


def state_get() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def state_set(d: dict) -> None:
    try:
        STATE.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    s = pipe("GET", "/status", timeout=20)
    if s is None:
        log("app is not running - cannot revive from here")
        return 1
    if s.get("bot_alive"):
        return 0
    if s.get("esc_hold"):
        log("ESC hold set - a human stopped the bot; leaving it alone")
        return 0

    try:
        lease = json.loads(LEASE.read_text(encoding="utf-8"))
        if lease.get("expires_at", 0) > time.time():
            return 0                       # somebody is using the screen
    except (OSError, ValueError):
        pass

    age = last_write_age_s()
    if age is not None and age < DOWN_GRACE_S:
        return 0                           # only just stopped; give it room

    st = state_get()
    since = time.time() - st.get("last_try", 0)
    if since < COOLDOWN_S:
        return 0

    state_set({"last_try": time.time()})
    down_min = int(age / 60) if age else None
    log(f"farm has been down {down_min} min with nobody holding it - starting night")

    r = pipe("POST", "/run", {"fn": "night", "args": {"rounds": 60}, "who": "revive"})
    if r is None or not r.get("ok", False):
        log(f"revive FAILED: {str(r)[:200]}")
        return 1

    # Do not claim success on the call returning. A preflight dry round can run
    # first and bot_alive is true for that too, so wait for it to clear.
    t0 = time.time()
    while time.time() - t0 < 420:
        s2 = pipe("GET", "/status", timeout=20)
        if s2 and s2.get("bot_alive") and s2.get("job") != "preflight":
            log("revived - farming")
            return 0
        time.sleep(10)
    log("started but never reached a farming state within 7 min")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
