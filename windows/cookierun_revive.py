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


def last_round_age_s() -> float | None:
    """Seconds since the farm last finished a ROUND -- not since a file moved.

    These part company at exactly the wrong moment. When the bot crashes, the
    supervisor opens a fresh session directory, and that write makes the farm
    look busy to anything measuring directory mtime. On 2026-09-17 a Windows
    passkey dialog sat over the game from 11:40; the bot crashed at 12:13 and
    reopened a session, and both this watchdog and the hourly health check read
    that restart as thirteen minutes of healthy work. Rounds are the only thing
    that cannot be faked by a restart.
    """
    try:
        dirs = [p for p in (DATA / "modelplay").glob("session-*") if p.is_dir()]
    except OSError:
        return None
    if not dirs:
        return None
    newest = max(dirs, key=lambda p: p.stat().st_mtime)
    runs = [x for x in newest.iterdir() if x.is_dir()]
    if runs:
        return time.time() - max(x.stat().st_mtime for x in runs)
    try:                                   # no rounds yet: age the session itself
        return time.time() - float(newest.name.split("-", 1)[1])
    except (IndexError, ValueError):
        return time.time() - newest.stat().st_mtime


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
# 2 min, not 5. Chrome has taken the emulator screen five times today; the
# grace exists only so a legitimate brief app switch is not fought over, and
# two minutes is still far longer than any such switch. At 5 min grace plus a
# 10 min tick the farm was losing up to 15 minutes per occurrence.
FOREIGN_GRACE_S = 2 * 60


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


# A round is ~5 min. Fourteen is past any legitimate round plus the navigation
# either side of it, and sits just above the hourly health check's 12 so the two
# never argue about the same minute.
STALLED_S = 14 * 60


# How long a foreign window may sit over the game before we assume it was
# forgotten rather than being used. Below this, the farm stands down.
FOREIGN_WINDOW_GRACE_S = 30 * 60


def foreign_window_over_game():
    """(title, is_foreground) of a non-BlueStacks window covering the game.

    Windows-side obstruction is invisible to every other check we have, because
    they all ask Android -- and Android answers correctly that the game is in
    the foreground, on the Android side, underneath somebody's browser. That is
    how five preflights in a row failed on 2026-09-17 while the navigator
    matched the Result panel at 0.998 and pressed an OK that went into Chrome.

    Foreground matters more than presence. A peer DRIVING a browser keeps it
    foreground; a window someone forgot to close sits behind. The first must be
    left alone -- CEO's rule is that Cookie Run yields to other computer-use
    agents, always -- and the second must not be allowed to park the farm
    forever, which is exactly what happened when a peer released the screen
    lease correctly but left a maximised Chrome behind.
    """
    import ctypes
    import ctypes.wintypes
    u = ctypes.windll.user32
    fg = u.GetForegroundWindow()
    found = []

    def title_of(hwnd):
        n = u.GetWindowTextLengthW(hwnd)
        if n == 0:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value

    def visit(hwnd, _):
        if not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd):
            return True
        t = title_of(hwnd)
        if not t or "BlueStacks" in t or "Cookie Run Script" in t:
            return True
        found.append((t[:50], hwnd == fg))
        return True

    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    try:
        u.EnumWindows(CB(visit), 0)
    except Exception as e:
        log(f"foreign_window_over_game failed: {e}")
        return None
    if not found:
        return None
    for t, is_fg in found:
        if is_fg:
            return (t, True)
    return (found[0][0], False)


def minimise_foreign_windows() -> str:
    """Minimise non-BlueStacks windows. Only ever called on a window that has
    been sitting there, unused, past the grace -- never on one a peer is
    driving. Minimise, never close: it belongs to whoever opened it."""
    import ctypes
    import ctypes.wintypes
    u = ctypes.windll.user32
    touched = []

    def visit(hwnd, _):
        if not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd):
            return True
        n = u.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        t = buf.value
        if "BlueStacks" in t or "Cookie Run Script" in t:
            return True
        u.ShowWindow(hwnd, 6)
        touched.append(t[:40])
        return True

    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    try:
        u.EnumWindows(CB(visit), 0)
    except Exception as e:
        log(f"minimise_foreign_windows failed: {e}")
    return ", ".join(touched) if touched else ""


def dismiss_windows_dialog() -> bool:
    """Close any Windows credential prompt sitting on top of the game.

    On 2026-09-17 a "Sign in with a passkey" dialog appeared at 11:40 and the
    farm did nothing for fifty minutes. Android reported the game in the
    foreground the whole time and was right -- the obstruction was a Windows
    modal over BlueStacks, which owns the keyboard and mouse, so every press the
    bot made went into the dialog.

    A previous attempt to DETECT this failed and had to be reverted: from
    session 0 there is no way to tell a live dialog from a CredentialUIBroker
    process that has outlived its window, and a check that cannot tell true from
    false has no business setting a verdict. Acting is a different question from
    reporting. Ending that process is harmless when there is no dialog and is
    the fix when there is one, so we do not need to know which case we are in --
    only that the farm is stalled, which we already know by then.

    Never clicks. Synthetic clicks aimed at this dialog on 2026-09-16 passed
    through it into the game and flipped the Jump/Slide button layout.
    """
    import subprocess
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "$p = Get-Process CredentialUIBroker -ErrorAction SilentlyContinue; "
             "if ($p) { $p | Stop-Process -Force; 'closed' } else { 'none' }"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000)
        return "closed" in r.stdout
    except Exception as e:
        log(f"dismiss_windows_dialog failed: {e}")
        return False


def clear_stall_while_alive(age_s: float) -> int:
    """The bot is running, the game is in front, and no round has finished.

    Nothing Android-side is wrong or the foreground check would have caught it,
    so the obstruction is above the emulator. Try the cheap, harmless remedy
    first and only restart the farm if the next tick finds it still stuck --
    a restart throws away a round in progress, and some stalls do end on their
    own once whatever stole the foreground goes away.
    """
    st = state_get()
    now = time.time()
    if now - st.get("stall_last_try", 0) < COOLDOWN_S:
        return 0

    mins = int(age_s / 60)
    if not st.get("stall_dismissed"):
        state_set({**st, "stall_dismissed": now})
        closed = dismiss_windows_dialog()
        log(f"alive but no round for {mins} min - "
            + ("closed a Windows credential dialog" if closed
               else "no Windows dialog to close; watching"))
        return 0

    state_set({**st, "stall_last_try": now, "stall_dismissed": None})
    log(f"still no round after {mins} min - restarting the game")
    pipe("POST", "/run", {"fn": "bot_stop", "args": {}, "who": "revive"})
    time.sleep(10)
    r = pipe("POST", "/run", {"fn": "restart_game", "args": {}, "who": "revive"})
    if r is None or not r.get("ok", False):
        log(f"restart_game FAILED: {str(r)[:200]}")
        return 1
    t0 = time.time()
    while time.time() - t0 < 300:
        time.sleep(15)
        s = pipe("GET", "/status", timeout=20)
        if s and not s.get("job"):
            break
    return 0 if start_farm(f"stalled {mins} min") else 1


def start_farm(why: str) -> bool:
    """night + wait for the preflight to clear. Shared by both recovery paths."""
    # Never start the farm underneath somebody else's window. A bot started
    # there looks alive, matches every screen, presses confidently and changes
    # nothing -- the most expensive kind of healthy.
    fw = foreign_window_over_game()
    if fw:
        title, is_fg = fw
        st = state_get()
        since = st.get("fwin_since")
        if not since or st.get("fwin_title") != title:
            state_set({**st, "fwin_since": time.time(), "fwin_title": title})
            log(f"a window is over the game ({title}) - standing down, not starting")
            return False
        if is_fg or time.time() - since < FOREIGN_WINDOW_GRACE_S:
            log(f"{title} still over the game - Cookie Run yields, not starting")
            return False
        state_set({**st, "fwin_since": None, "fwin_title": None})
        log(f"minimising forgotten windows after "
            f"{int((time.time() - since) / 60)} min: {minimise_foreign_windows()}")
    else:
        st = state_get()
        if st.get("fwin_since"):
            state_set({**st, "fwin_since": None, "fwin_title": None})
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


def start_app_task() -> bool:
    """Kick CookieRunAppSrc. Safe even if it is already running -- the task's
    own MultipleInstances=IgnoreNew makes a redundant call a no-op.

    Found 2026-09-16: pythonw.exe access-violated inside _ctypes.pyd at 16:29:54
    and took the whole app down with it -- GUI, pipe server and bot supervisor
    all live in one process. This watchdog then logged "app is not running -
    cannot revive from here" every 10 minutes for 2+ hours, because it only
    ever knew how to talk to the app over its own pipe. It had no way to press
    the button that starts the app in the first place.
    """
    import subprocess
    try:
        r = subprocess.run(["schtasks", "/run", "/tn", "CookieRunAppSrc"],
                           capture_output=True, text=True, timeout=30,
                           creationflags=0x08000000)
        return r.returncode == 0
    except Exception as e:
        log(f"schtasks /run CookieRunAppSrc failed: {e}")
        return False


def main() -> int:
    s = pipe("GET", "/status", timeout=20)
    if s is None:
        st = state_get()
        if time.time() - st.get("app_last_try", 0) < COOLDOWN_S:
            return 1
        state_set({**st, "app_last_try": time.time()})
        age = last_round_age_s()
        down_for = f"{int(age/60)} min" if age is not None else "unknown time"
        log(f"app is not running (down {down_for}) - starting CookieRunAppSrc")
        if not start_app_task():
            log("schtasks /run did not report success")
            return 1
        t0 = time.time()
        while time.time() - t0 < 90:
            time.sleep(5)
            s = pipe("GET", "/status", timeout=20)
            if s is not None:
                break
        if s is None:
            log("app still unreachable 90s after starting the task")
            return 1
        log("app is back - pipe answering")
        # fall through: the code below decides whether to also start farming

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
        # The game is in front and the bot is running, and that is still not
        # the same as farming: a Windows modal over BlueStacks looks exactly
        # like this from every angle Android can see.
        age = last_round_age_s()
        if age is not None and age > STALLED_S:
            return clear_stall_while_alive(age)
        if st.get("stall_dismissed"):
            state_set({**st, "stall_dismissed": None})
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

    age = last_round_age_s()
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
