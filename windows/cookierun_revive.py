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


ADB = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PKG = "com.devsisters.crg"
FOREIGN_GRACE_S = 5 * 60


def foreground_app() -> str | None:
    """Which Android app owns the emulator screen (None if adb cannot say)."""
    import subprocess
    try:
        subprocess.run([ADB, "connect", "127.0.0.1:5555"], capture_output=True,
                       timeout=20, creationflags=0x08000000)
        out = subprocess.run(
            [ADB, "-s", "emulator-5554", "shell", "dumpsys", "activity", "activities"],
            capture_output=True, text=True, timeout=30,
            creationflags=0x08000000).stdout
    except Exception:
        return None
    for line in out.splitlines():
        if "topResumedActivity" in line and "u0 " in line:
            try:
                return line.split("u0 ", 1)[1].split("/", 1)[0].strip()
            except IndexError:
                return None
    return None


def clear_foreign_app(fg: str) -> int:
    """A non-game app has the screen while the bot is running. Restart the game.

    Chrome's first-run page has now taken the emulator twice (01:14 and 06:30 on
    2026-09-16) and the BlueStacks launcher once. The bot's own ladder does get
    out of these -- it backs out, then restarts BlueStacks -- but it waits 25
    minutes before the first step, because it can only tell it is stuck by the
    absence of progress. Android answers instantly via dumpsys, so there is no
    reason to buy that information with 25 minutes of dead farm.
    """
    st = state_get()
    first = st.get("foreign_since")
    now = time.time()
    if not first or st.get("foreign_app") != fg:
        state_set({**st, "foreign_since": now, "foreign_app": fg})
        log(f"foreign app on screen: {fg} - watching")
        return 0
    if now - first < FOREIGN_GRACE_S:
        return 0
    if now - st.get("last_try", 0) < COOLDOWN_S:
        return 0

    state_set({**st, "last_try": now, "foreign_since": None, "foreign_app": None})
    log(f"{fg} has owned the screen for {int((now - first) / 60)} min - restarting the game")
    pipe("POST", "/run", {"fn": "bot_stop", "args": {}, "who": "revive"})
    time.sleep(10)
    r = pipe("POST", "/run", {"fn": "restart_game", "args": {}, "who": "revive"})
    if r is None or not r.get("ok", False):
        log(f"restart_game FAILED: {str(r)[:200]}")
        return 1

    # Clearing the obstruction is not the job -- farming is. The first version
    # of this stopped here, having tidied the screen and left the farm off, and
    # then its own 30-minute cooldown blocked the down-path that would have
    # noticed (measured 2026-09-16: cleared Chrome at 08:14, farm idle until the
    # cooldown expired). Finish what we started, in this tick.
    t0 = time.time()
    while time.time() - t0 < 300:               # the game takes ~2 min to come up
        time.sleep(15)
        s = pipe("GET", "/status", timeout=20)
        if s and not s.get("job"):              # restart_game has finished
            break
    started = start_farm("after clearing " + fg)
    return 0 if started else 1


def start_farm(why: str) -> bool:
    """night + wait for the preflight to clear. Shared by both recovery paths."""
    r = pipe("POST", "/run", {"fn": "night", "args": {"rounds": 60}, "who": "revive"})
    if r is None or not r.get("ok", False):
        log(f"start FAILED ({why}): {str(r)[:200]}")
        return False
    t0 = time.time()
    while time.time() - t0 < 420:
        s = pipe("GET", "/status", timeout=20)
        if s and s.get("bot_alive") and s.get("job") != "preflight":
            log(f"farming again ({why})")
            return True
        time.sleep(10)
    log(f"started but never reached a farming state within 7 min ({why})")
    return False


def main() -> int:
    s = pipe("GET", "/status", timeout=20)
    if s is None:
        log("app is not running - cannot revive from here")
        return 1
    if s.get("bot_alive"):
        # Alive is not the same as making progress: a foreign app can own the
        # screen while the bot sits there reading it.
        if s.get("job") == "preflight":
            return 0
        fg = foreground_app()
        if fg and fg != GAME_PKG:
            return clear_foreign_app(fg)
        st = state_get()
        if st.get("foreign_since"):
            state_set({**st, "foreign_since": None, "foreign_app": None})
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

    # Never claims success on the call returning: bot_alive is true during a
    # preflight dry round too, so start_farm waits for that to clear.
    return 0 if start_farm(f"down {down_min} min") else 1


if __name__ == "__main__":
    raise SystemExit(main())
