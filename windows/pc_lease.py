#!/usr/bin/env python3
"""pc_lease.py -- who owns the winbox screen right now.

Cookie Run farms this box all night; every other computer-use agent needs it for
an hour or two. Cookie Run always loses that argument (CEO 2026-09-14). This
script is the referee: it parks Cookie Run, hands the screen over, and -- this is
the part that matters -- puts Cookie Run back even when the borrower never
returns.

  pc_lease.py status
  pc_lease.py take --who "<agent>: <what for>" [--minutes 120] [--after-round]
  pc_lease.py give-back
  pc_lease.py extend --minutes 60
  pc_lease.py tick                 # the watchdog; a scheduled task calls this
  pc_lease.py ceo-on               # the CEO's "use PC" button (windows/desktop/)
  pc_lease.py ceo-off              # the CEO's "done" button

Three rules are load-bearing:

* It stops the bot with bot_stop (the STOP file), NEVER with esc. esc writes
  ESC_HOLD, which blocks every future launch until a HUMAN clears it -- app.py
  refuses clear_hold unless the CTO is relaying the CEO's own words. A script
  that used esc would take the farm down for the night, not for an hour.
* The lease carries an expiry and `tick` enforces it. A borrower that crashes,
  loses its context or simply forgets costs one lease, not one night.
* The CEO outranks every lease. A FREE lease is not a free screen: twice
  (2026-10-07, 2026-10-09 13:36) an agent found it FREE and relaunched
  Minecraft over the Dota 2 game the CEO was playing. His two desktop buttons
  write and remove CEO_HOLD.json; while it exists take, extend and gate refuse,
  and nothing here minimises a window or restarts Cookie Run. It has no expiry:
  only the CEO ends it.

Output is deliberately ASCII-only: it travels back through a PowerShell argument
layer that turns non-ASCII into "?", and "?" is a single-char wildcard in
PowerShell paths (docs/reports/FINDING-winbox-ascii-only.md).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Windows defaults stdout to cp1252, and everything here prints text that
# came from somewhere else -- a lease holder's name, a window title, a
# screen name. On 2026-09-18 a lease taken with a U+25D1 in it crashed
# this whole check on the print, so the farm's health was unreadable
# because of a character in somebody's label. Third instance of this same
# cp1252 fault today (esc's ESC_HOLD write, session-rename, this).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path.home() / "Documents" / "CookieRunScript"
TOKEN = DATA / "modelplay" / "pipe_token"
LEASE = DATA / "modelplay" / "PC_LEASE.json"
LOG = DATA / "modelplay" / "pc_lease.log"
CEO_HOLD = DATA / "modelplay" / "CEO_HOLD.json"
PIPE = "http://127.0.0.1:8794"

# BUMP THIS ON EVERY CHANGE TO THIS FILE. scripts/pc-lease.sh copies it to the
# box only when this number is HIGHER than the box copy's (an md5 compare let
# any stale checkout put an older pc_lease.py back -- one that knows nothing of
# the CEO's hold). An edit without a bump stays on your machine and the wrapper
# says so. scripts/lib/winbox_deploy.sh reads the line by this exact shape.
LEASE_VERSION = 1

DEFAULT_MINUTES = 120         # "others need 1-2 hours" -- CEO 2026-09-14
MAX_MINUTES = 480
RESUME_TRIES = 3               # tick gives up after this, loudly, instead of looping



def SKIP_TITLES(t) -> bool:
    """Windows we must never minimise: the game, the app driving it, and
    "Program Manager" -- the shell's own window, which is the desktop
    itself and not anybody's app."""
    t = t[0] if isinstance(t, tuple) else t
    return ("BlueStacks" in t or "Cookie Run Script" in t
            or t == "Program Manager")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def ascii_only(s: str) -> str:
    return s.encode("ascii", "replace").decode("ascii")


# --- the app pipe ------------------------------------------------------------

def pipe(method: str, path: str, body: dict | None = None, timeout: int = 90):
    """Returns the decoded reply, or None if the app is not running."""
    try:
        tok = TOKEN.read_text().strip()
    except OSError:
        return None
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(PIPE + path, data=data, method=method,
                                 headers={"X-Pipe-Token": tok,
                                          "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def status() -> dict | None:
    return pipe("GET", "/status", timeout=20)


def run_fn(fn: str, args: dict | None = None) -> dict | None:
    return pipe("POST", "/run", {"fn": fn, "args": args or {}, "who": "pc_lease"})


# --- the lease ---------------------------------------------------------------

def read_lease() -> dict | None:
    try:
        return json.loads(LEASE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_lease(d: dict) -> None:
    LEASE.parent.mkdir(parents=True, exist_ok=True)
    LEASE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def clear_lease() -> None:
    try:
        LEASE.unlink()
    except OSError:
        pass


def remaining(lease: dict) -> float:
    return lease.get("expires_at", 0) - time.time()


def hhmm(ts: float) -> str:
    return time.strftime("%H:%M", time.localtime(ts))


# --- the CEO's hold ----------------------------------------------------------
# A lease says which AGENT has the screen. It cannot say the CEO is sitting at
# it, and twice now an agent read FREE as "nobody is here" -- 2026-10-07 (a night
# runner) and 2026-10-09 13:36 (a rerun that relaunched Minecraft over his Dota
# 2 game; his words: "let me use the PC first"). So he gets two desktop buttons
# (windows/desktop/) that write and remove this file. While it exists:
#   * take, extend and gate refuse -- no --force, no --as, no holder exception;
#   * nothing here minimises a window or restarts Cookie Run (the windows on
#     screen are his own, and the farm waits for his release button);
#   * a lease that ends folds its "put Cookie Run back" duty onto the hold.
# It has no expiry. A hold the CEO forgot costs the farm an evening; a hold that
# timed out under him costs exactly what these buttons exist to stop.
#
#   {"since": epoch, "was_running": bool, "resume": plan | None,
#    "bumped": {"who": str, "until": epoch} | None}
HOLD_KEYS = ("since", "was_running", "resume", "bumped")


def read_ceo_hold() -> dict | None:
    """None only when there is no hold file. Anything else counts as HELD.

    Fails closed on purpose: a file that exists but cannot be read or parsed
    comes back held, details unknown ("corrupt": True). A broken file must never
    be the thing that frees the CEO's screen.
    """
    try:
        raw = CEO_HOLD.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        raw = None
    try:
        d = json.loads(raw) if raw is not None else None
    except ValueError:
        d = None
    if isinstance(d, dict) and isinstance(d.get("since"), (int, float)):
        return d
    try:
        since = CEO_HOLD.stat().st_mtime
    except OSError:
        since = time.time()
    return {"since": since, "was_running": False, "resume": None, "bumped": None,
            "corrupt": True}


def write_ceo_hold(d: dict) -> None:
    """Atomic (tmp + os.replace): a reader sees the old hold or the new one.

    A torn write would read as corrupt, which still counts as held -- safe, but
    it would lose the plan that puts Cookie Run back. Raises OSError when it
    could not write; the caller decides how loud to be.
    """
    CEO_HOLD.parent.mkdir(parents=True, exist_ok=True)
    tmp = CEO_HOLD.with_name(f"{CEO_HOLD.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({k: d.get(k) for k in HOLD_KEYS}, indent=2),
                   encoding="utf-8")
    for attempt in range(10):
        try:
            os.replace(tmp, CEO_HOLD)
            return
        except PermissionError:
            # Windows will not replace a file another process has open, and the
            # readers (tick, health, revive, every agent's status) each hold it
            # for a moment. Wait one out rather than fail the CEO's button.
            if attempt == 9:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                raise
            time.sleep(0.2)


def clear_ceo_hold() -> bool:
    """Remove the hold. False means it is still there -- say so, loudly."""
    for _ in range(10):
        try:
            CEO_HOLD.unlink()
            return True
        except FileNotFoundError:
            return True
        except PermissionError:
            time.sleep(0.2)              # a reader has it open; see write_ceo_hold
        except OSError:
            return False
    return False


def ceo_refusal(hold: dict) -> list[str]:
    """The refusal every agent-facing command prints while the CEO holds the PC."""
    return [f"REFUSED: the CEO is using this PC (CEO hold since {hhmm(hold['since'])}).",
            "  Wait for the CEO's release button on the winbox desktop. --force does",
            "  not override this and nothing else does either: he is at the keyboard."]


def fold_into_hold(lease: dict, why: str) -> bool:
    """Move a lease's duty to put Cookie Run back onto the CEO hold.

    A lease that ends while the CEO holds the PC must not restart the farm under
    him -- but the farm still has to come back, and the lease is the only record
    that it was running. So the plan moves onto the hold and ceo-off carries it
    out. False means it could not (the hold went away meanwhile, or the write
    failed): the caller then KEEPS the lease, so the plan is never dropped.
    """
    if not lease.get("was_running"):
        return True
    hold = read_ceo_hold()               # re-read: he may have pressed release
    if hold is None:
        log(f"{why}: the CEO hold went away mid-hand-over; keeping the lease")
        return False
    hold["was_running"] = True
    hold["resume"] = hold.get("resume") or lease.get("resume")
    try:
        write_ceo_hold(hold)
    except OSError as e:
        log(f"{why}: could not put {lease.get('who', '?')}'s Cookie Run plan "
            f"on the CEO hold: {e}")
        return False
    log(f"{why}: Cookie Run plan from {lease.get('who', '?')} moved onto the CEO hold")
    return True


# --- stopping and resuming ---------------------------------------------------

def wait_until_stopped(limit_s: int = 40) -> bool:
    t0 = time.time()
    while time.time() - t0 < limit_s:
        s = status()
        if s is None or not s.get("bot_alive"):
            return True
        time.sleep(2)
    return False


def wait_for_round_gap(limit_s: int = 240) -> bool:
    """Park until the bot is between runs, so the in-flight round is kept whole.

    The bot writes its round record and then waits for a fresh run; there is no
    'between rounds' flag on the pipe, so this watches the status line for the
    wait state. Best effort -- returns False on timeout and the caller stops
    anyway (a cut round is marked end=stop-file and is dropped downstream, so
    the cost of giving up is one round, never corrupt data).
    """
    t0 = time.time()
    while time.time() - t0 < limit_s:
        s = status()
        if s is None or not s.get("bot_alive"):
            return True
        line = (s.get("status_line") or "").lower()
        if "waiting for a fresh run" in line or "waiting" in line:
            return True
        time.sleep(3)
    return False


def capture_resume_plan(s: dict) -> dict:
    """What it takes to put Cookie Run back exactly as it was."""
    ab = s.get("ab")
    if ab:
        return {"fn": "ab", "args": {"champion": ab.get("champion", ""),
                                     "candidate": ab.get("candidate", ""),
                                     "rounds": int(ab.get("rounds", 8)),
                                     "then_night": bool(s.get("night_guard"))}}
    if s.get("night_guard"):
        return {"fn": "night", "args": {"model": s.get("champion", ""), "rounds": 60}}
    return {"fn": "bot_start", "args": {"model": s.get("champion", ""), "rounds": 60}}


def resume(plan: dict, why: str) -> tuple[bool, str]:
    """Put Cookie Run back. Returns (ok, human-readable reason)."""
    if read_ceo_hold() is not None:
        # Every path that restarts the farm comes through here, so this is the
        # one check no new caller can forget. Callers under a hold never get
        # this far; this is the backstop if one ever does.
        return False, "the CEO is using this PC (CEO hold) - not resuming"
    s = status()
    if s is None:
        return False, "the Cookie Run app is not running (no pipe) - cannot resume"
    if s.get("esc_hold"):
        # The CEO pressed ESC while the screen was borrowed. That outranks us.
        return False, "ESC hold is set - a human stopped the bot; not resuming"
    if s.get("bot_alive"):
        return True, "already running"

    if not game_running():
        log(f"resume({why}): game window is gone, restarting it first")
        run_fn("restart_game")
        time.sleep(45)

    r = run_fn(plan["fn"], plan["args"])
    if r is None:
        return False, "pipe call failed"
    if not r.get("ok", False):
        return False, f"app refused: {ascii_only(str(r.get('error') or r))[:200]}"

    # bot_alive alone is NOT proof it is farming. After a code change the app
    # runs a dry preflight round first, and bot_alive is true for that too --
    # so an early "running" here is a lie that survives right up until someone
    # checks played_fraction and finds zero (measured 2026-09-14). Wait for the
    # preflight to clear, and say plainly when it has not.
    t0 = time.time()
    saw_preflight = False
    gap_since = None
    while time.time() - t0 < 420:
        s = status()
        if s:
            job = s.get("job")
            if job == "preflight":
                saw_preflight = True
                gap_since = None
            elif s.get("bot_alive"):
                return True, "farming"
            elif saw_preflight:
                # Preflight has ended and the real bot is not up *yet*. That is
                # the normal hand-off gap, not a failure: the app launches the
                # bot a moment after the dry round passes, and calling it dead
                # on the first poll reported a healthy resume as failed
                # (measured 2026-09-14 - the log said "preflight passed, bot
                # start pid 17184" while give-back was printing FAILED).
                gap_since = gap_since or time.time()
                if time.time() - gap_since > 45:
                    return False, ("preflight ended and the bot never started within 45 s - "
                                   "the app did not release it; check the app log")
        time.sleep(5)

    s = status()
    if s and s.get("job") == "preflight":
        return False, ("preflight round still running after 7 min - not farming yet. "
                       "It may still come good; check `status` and the app log")
    return False, "started but never reached a farming state within 7 min"


def game_running() -> bool:
    import subprocess
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq HD-Player.exe", "/NH"],
            capture_output=True, text=True, timeout=20,
            creationflags=0x08000000).stdout
        return "HD-Player" in out
    except Exception:
        return False


# --- commands ----------------------------------------------------------------

def cmd_status(_args) -> int:
    s = status()
    lease = read_lease()
    hold = read_ceo_hold()

    # The CEO's hold is the FIRST line, always: it is the one fact that makes
    # every line after it irrelevant to an agent deciding whether to click.
    if hold is not None:
        print(f"PC: CEO - the CEO is using this PC since {hhmm(hold['since'])}. "
              "Hands off the screen.")
        print("    take, extend and gate refuse until he presses the release button.")
        if hold.get("corrupt"):
            print("    (the hold file is unreadable - it counts as held until he releases it)")

    if lease and remaining(lease) > 0:
        mins = int(remaining(lease) // 60)
        print(f"PC: BUSY - held by {lease.get('who', '?')}")
        print(f"    until {hhmm(lease['expires_at'])} ({mins} min left)")
        if hold is not None:
            print("    That lease is blocked while the CEO holds the PC.")
        else:
            print("    If that is you, carry on. If not, coordinate with them -")
            print("    or take it anyway: peers outrank each other only by agreement.")
    elif hold is not None:
        # Never the word FREE under a hold. A script that greps status for
        # "PC: FREE" would read it as a go -- which is the 13:36 incident again.
        print("    No agent lease is held.")
    elif lease:
        print("PC: FREE - a lease expired and the watchdog has not ticked yet")
    else:
        print("PC: FREE - nobody holds a lease")

    if s is None and hold is not None:
        print("Cookie Run: app NOT running")
    elif s is None:
        print("Cookie Run: app NOT running (nothing to stop, screen is yours)")
    elif s.get("esc_hold"):
        print("Cookie Run: HELD by a human ESC (stays stopped until a human clears it)")
    elif s.get("bot_alive") and hold is not None:
        print("Cookie Run: RUNNING under the CEO hold - it should be stopped. Tell the CTO.")
    elif s.get("bot_alive"):
        print("Cookie Run: RUNNING - call `take` before you touch the screen")
    else:
        print("Cookie Run: idle (app up, bot stopped)")
    return 0


def cmd_take(args) -> int:
    minutes = max(1, min(int(args.minutes), MAX_MINUTES))
    who = ascii_only(args.who or "unnamed agent")[:120]

    # Before the lease check and before --force is even looked at: the CEO is
    # not a peer, and no agreement between agents covers his screen.
    hold = read_ceo_hold()
    if hold is not None:
        log(f"take by {who} REFUSED - CEO hold since {hhmm(hold['since'])}")
        for line in ceo_refusal(hold):
            print(line)
        return 2

    old = read_lease()
    if old and remaining(old) > 0 and not args.force:
        print(f"REFUSED: {old.get('who','?')} holds the PC until {hhmm(old['expires_at'])} "
              f"({int(remaining(old)//60)} min left).")
        print("Wait, or re-run with --force if you have agreed to take over.")
        return 2

    s = status()
    was_running = False
    plan = None

    if s is None:
        note = "Cookie Run app was not running - nothing to stop"
    elif s.get("esc_hold"):
        note = "Cookie Run was already held by a human ESC - nothing to stop"
    elif s.get("bot_alive"):
        plan = capture_resume_plan(s)
        was_running = True
        if s.get("job") == "preflight":
            # Stopping mid-preflight makes the dry round exit non-zero (it dies
            # inside a GPU inference call and reports a DirectML error that reads
            # like a hardware fault but is just the kill). The app then refuses to
            # release the bot, and give-back has to run the whole preflight again.
            print("note: a preflight dry round is in progress. Stopping it costs "
                  "~3 min on give-back, when it has to run again. Taking the screen anyway.")
        if args.after_round:
            print("waiting for the current round to end (up to 4 min)...")
            if not wait_for_round_gap():
                print("  round did not end in time - stopping anyway "
                      "(that round is marked end=stop-file and is dropped downstream)")
        run_fn("bot_stop")
        if wait_until_stopped():
            note = "Cookie Run stopped"
        else:
            print("FAILED: asked Cookie Run to stop but it is still alive after 40s.")
            print("Do NOT use the screen yet. Tell the CTO.")
            log(f"take by {who}: bot_stop did not take effect")
            return 1
    else:
        note = "Cookie Run app up but bot already idle - nothing to stop"

    # The CEO may have pressed his button while we were stopping the bot. His
    # hold wins, and what we just stopped becomes his release button's to
    # restart -- so the plan goes onto the hold instead of into a lease.
    hold = read_ceo_hold()
    if hold is not None:
        fold_into_hold({"who": who, "was_running": was_running, "resume": plan},
                       f"take by {who}")
        log(f"take by {who} REFUSED - the CEO pressed his button mid-take")
        for line in ceo_refusal(hold):
            print(line)
        return 2

    now = time.time()
    write_lease({"who": who, "taken_at": now, "expires_at": now + minutes * 60,
                 "was_running": was_running, "resume": plan,
                 "resume_failures": 0})
    log(f"take by {who} for {minutes} min - {note}")

    print(f"OK - the screen is yours until {hhmm(now + minutes * 60)} ({minutes} min).")
    print(f"     {note}.")
    print("     Call `give-back` the moment you are done - do not wait for the expiry.")
    if was_running:
        print("     If you forget, the watchdog puts Cookie Run back at the expiry anyway.")
    return 0



# ---------------------------------------------------------------- screen tidy
# A borrow ends with two obligations and only one of them was enforced. Peer
# CTO #e1e3d3ef ran take -> work -> give-back correctly three times on
# 2026-09-17 and left a maximised Chrome over BlueStacks after each one. The
# lease read FREE, Android still reported the game foreground -- correctly, it
# was, underneath a browser -- and the bot spent 2.5 hours pressing buttons into
# somebody else's window. Their own sessions were fooled the same way from the
# other side: every `take` answered "bot already idle", which they read as the
# farm being broken.
#
# Their conclusion, and it is right: a rule the borrower has to remember gets
# skipped, and they are the proof twice over. give-back already knows the borrow
# is ending and already reaches session 1; minimising there costs one more call
# on a path we already run, and nobody has to be told anything.
#
# Two traps they hit and paid for, kept here so the next person does not:
#   * ssh lands in SESSION 0 and cannot see session 1's windows. Enumerating
#     from here returns a clean "minimised 0 windows" that did nothing. It has
#     to go through the interactive scheduled task.
#   * inline `Add-Type` with a P/Invoke signature does not survive the
#     ssh -> cmd -> powershell quoting chain. We use ctypes from Python instead,
#     which has no quoting to survive.
CLEAR_TASK = "MooniexPCLeaseClear"


def minimise_foreign_windows() -> str:
    """Minimise every visible window that is not the game or the app.

    Runs in SESSION 1 only -- see the note above. Minimise, never close: the
    window belongs to whoever opened it and they may want it back.

    Never while the CEO holds the PC: then every window on screen is his. Like
    resume(), the check lives here so the clear-screen task cannot get round it.
    """
    if read_ceo_hold() is not None:
        log("minimise_foreign_windows: refused - the CEO holds the PC")
        return "REFUSED: the CEO holds the PC - minimised nothing"

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
        if SKIP_TITLES((t)):
            return True
        u.ShowWindow(hwnd, 6)                 # SW_MINIMIZE
        touched.append(t[:40])
        return True

    saw_tenant = []

    def note_tenant(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        n = u.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        if "BlueStacks" in buf.value:
            saw_tenant.append(buf.value)
        return True

    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    try:
        u.EnumWindows(CB(note_tenant), 0)
        # If we cannot see BlueStacks either, we are not looking at the desktop
        # that has it -- almost certainly session 0, where ssh lands. Reporting
        # "minimised 0 windows" from there is a clean success that did nothing,
        # which is precisely how this went undiagnosed. Say so instead.
        if not saw_tenant:
            raise RuntimeError(
                "cannot see the BlueStacks window - this is not the session that "
                "owns the desktop (ssh lands in session 0). Run it through the "
                f"{CLEAR_TASK} scheduled task.")
        u.EnumWindows(CB(visit), 0)
    except Exception as e:
        log(f"minimise_foreign_windows failed: {e}")
        return f"FAILED: {e}"
    return ", ".join(touched)


def request_screen_clear() -> None:
    """Ask session 1 to tidy the desktop, and wait for it.

    Fire-and-forget would race the farm restart that follows: the bot would take
    its first look at the screen while the browser is still on top, which is the
    exact failure this exists to prevent.
    """
    import subprocess
    try:
        subprocess.run(["schtasks", "/run", "/tn", CLEAR_TASK],
                       capture_output=True, timeout=30, creationflags=0x08000000)
        time.sleep(6)
    except Exception as e:
        log(f"could not trigger {CLEAR_TASK}: {e}")


def cmd_clear_screen(_args) -> int:
    """Session-1 entry point for the scheduled task."""
    done = minimise_foreign_windows()
    log(f"screen clear: {done or 'nothing to minimise'}")
    print(done or "nothing to minimise")
    return 0


def cmd_give_back(_args) -> int:
    lease = read_lease()

    # Under the CEO's hold a give-back clears nothing and restarts nothing: the
    # windows on screen are his, and the farm waits for his release button. The
    # lease still ends here -- its holder is done -- but its duty to put Cookie
    # Run back moves onto the hold instead of being carried out under him.
    hold = read_ceo_hold()
    if hold is not None:
        since = hhmm(hold["since"])
        if not lease:
            print(f"No lease was held. The CEO is using this PC (since {since}) - "
                  "hands off the screen.")
            return 0
        who = lease.get("who", "?")
        if not fold_into_hold(lease, f"give-back by {who}"):
            print("FAILED: could not hand Cookie Run's restart over to the CEO hold.")
            print("The lease is left in place; the watchdog hands it over when it expires.")
            print("Tell the CTO. Either way, hands off the screen - the CEO is using it.")
            return 1
        clear_lease()
        log(f"give-back by {who} during the CEO hold - lease cleared; "
            "screen not cleared, Cookie Run not resumed")
        print(f"OK - lease released. The CEO is using this PC (since {since}), so the")
        print("     screen was NOT cleared and Cookie Run was NOT restarted. Hands off.")
        if lease.get("was_running"):
            print("     Cookie Run comes back when the CEO presses his release button.")
        return 0

    # Before anything else, and on every path out of here -- including the two
    # early returns below, which are the ones that let this happen unnoticed.
    request_screen_clear()
    if not lease:
        print("No lease was held. Nothing to give back.")
        s = status()
        if s and not s.get("bot_alive") and not s.get("esc_hold"):
            print("Note: Cookie Run is idle. If you stopped it by hand, tell the CTO.")
        return 0

    who = lease.get("who", "?")
    if not lease.get("was_running"):
        clear_lease()
        log(f"give-back by {who} - Cookie Run was not running when taken; left as is")
        print("OK - lease released, screen cleared. Cookie Run was not running "
              "when you took it, so nothing was restarted.")
        print("If you expected it to be running, say so - three borrows in a row "
              "reporting this is how 2026-09-17 went unnoticed for hours.")
        return 0

    ok, why = resume(lease.get("resume") or {"fn": "night", "args": {"rounds": 60}}, "give-back")
    clear_lease()
    log(f"give-back by {who} - resume ok={ok} ({why})")
    if ok:
        print(f"OK - lease released and Cookie Run is running again ({why}).")
        return 0
    print(f"LEASE RELEASED, BUT COOKIE RUN DID NOT COME BACK: {why}")
    print("Tell the CTO - the farm is idle until someone looks at it.")
    return 1


def cmd_extend(args) -> int:
    lease = read_lease()
    hold = read_ceo_hold()
    if hold is not None:
        log(f"extend by {(lease or {}).get('who', '?')} REFUSED - "
            f"CEO hold since {hhmm(hold['since'])}")
        for line in ceo_refusal(hold):
            print(line)
        return 2
    if not lease:
        print("No lease to extend. Call `take` first.")
        return 2
    add = max(1, min(int(args.minutes), MAX_MINUTES))
    base = max(lease.get("expires_at", 0), time.time())
    lease["expires_at"] = base + add * 60
    write_lease(lease)
    log(f"extend by {lease.get('who','?')} +{add} min")
    print(f"OK - extended to {hhmm(lease['expires_at'])}.")
    return 0


def cmd_gate(_args) -> int:  # noqa: C901 -- _args carries --as; see main()
    """Exit 0 if it is safe to touch the screen, 3 if a tenant is farming
    unleased or the CEO holds the PC.

    **This command writes nothing to stdout, ever.** It is a predicate, not a
    reporter: the verdict is the exit code and every line of text -- refusal and
    holder NOTE alike -- goes to stderr. Half of that was true after the first
    review (the NOTE moved, the refusal did not), which left "a caller parsing
    stdout is safe" holding on two paths out of three. A guarantee with an
    exception is a guarantee nobody can rely on, so the exception went.
    Humans lose nothing: stderr still reaches the terminal.

    This is the enforcement behind rule 2. A peer session drove this desktop for
    three hours with the bot live underneath (2026-09-14) -- every command
    returned OK, the toasts stacked in its own screenshots, and it read them as
    noise. The rule was written down and the document did not stop it. So the
    scripts that touch the screen call this first.

    The CEO's hold is checked first and refuses with the SAME code, 3. Every
    caller in the repo (winbox-desktop.sh, winbox-line-send.sh) runs
    `pc-lease.sh gate || exit 3`, and the skill documents 0 = proceed, 3 =
    refused; a new code would be one a hand-written `[[ $? == 3 ]]` check reads
    as a pass. --as does not get a holder past it: the CEO is not a lease.
    """
    hold = read_ceo_hold()
    if hold is not None:
        # Local import like the two below: they make `sys` a local name for the
        # whole function, so the module-level one is not visible up here.
        import sys
        say = lambda t="": print(t, file=sys.stderr)
        say(f"REFUSED: the CEO is using the winbox screen (since {hhmm(hold['since'])}).")
        say("  Hands off until he presses the release button on his desktop. No")
        say("  lease, --as or --force gets past this - and do not reach for")
        say("  WINBOX_NO_LEASE: it exists for the farm, and he is at the keyboard.")
        return 3

    lease = read_lease()
    held = lease and remaining(lease) > 0

    if held:
        # The gate cannot tell who is calling, so it cannot refuse a peer on the
        # holder's behalf -- and peers outrank each other only by agreement
        # anyway. But silence here is how two agents end up clicking in the same
        # window: a reviewer found that once anyone parks the tenant, an
        # unleased caller sails straight through with no hint that the screen is
        # spoken for (2026-09-14). So say who has it.
        #
        # --as lets the wrapper name the caller from the lease it took locally,
        # so the holder is not told about itself thirty times in one session. A
        # line aimed at the one person it cannot apply to is a line people learn
        # to skip. Any mismatch, or no --as at all, prints -- it fails toward
        # saying something, because the silence is the failure that costs.
        if (_args.as_who or "").strip() and _args.as_who.strip() == str(lease.get("who", "")).strip():
            return 0
        import sys
        print(f"NOTE: the screen is held by {lease.get('who', '?')} "
              f"until {hhmm(lease['expires_at'])} "
              f"({int(remaining(lease) // 60)} min left).",
              file=sys.stderr)
        print("      If that is not you, talk to them before you click.",
              file=sys.stderr)
        return 0

    s = status()
    if s is None or s.get("esc_hold") or not s.get("bot_alive"):
        return 0                      # nothing is farming; the screen is free

    import sys
    say = lambda t="": print(t, file=sys.stderr)
    say("REFUSED: something is using the winbox screen and you hold no lease.")
    say()
    say("  ./scripts/pc-lease.sh take --who \"<you>: <what for>\"")
    say("  ... your work ...")
    say("  ./scripts/pc-lease.sh give-back")
    say()
    say("Takes ~5 s. You outrank the tenant -- this only stops you fighting it")
    say("for the foreground, which is how it stalls silently while still")
    say("reporting itself alive. See the winbox-pc-lease skill.")
    say("Override for a genuine emergency: WINBOX_NO_LEASE=1")
    return 3


FOREGROUND = DATA / "modelplay" / "foreground.json"


def record_foreground() -> None:
    """Write which window owns the desktop, for readers who cannot see it.

    Everything that judges the farm's health runs over ssh, which lands in
    SESSION 0, which cannot enumerate session 1's windows. So a browser sitting
    over BlueStacks is invisible to every check we own: Android correctly
    reports the game as foreground (it is, underneath), the lease reads FREE,
    and the bot presses buttons into somebody else's window. That cost hours on
    2026-09-17, twice, and the second time it also convinced the freeze probe
    the game had hung - it restarted a game that was fine, because a web page
    does not move between frames.

    This runs in session 1 (the tick task already does), so it can just look.
    Readers get a timestamp and decide for themselves whether it is fresh
    enough to trust - a stale answer here must say nothing rather than guess.
    """
    import ctypes
    import ctypes.wintypes
    u = ctypes.windll.user32
    try:
        hwnd = u.GetForegroundWindow()
        n = u.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value
        FOREGROUND.write_text(json.dumps({
            "t": time.time(),
            "title": title[:120],
            "is_tenant": bool(SKIP_TITLES(title)),
        }), encoding="utf-8")
    except Exception as e:
        log(f"record_foreground failed: {e}")


def cmd_tick(_args) -> int:
    """The watchdog. Resumes Cookie Run when a lease runs out."""
    # Read-only, so it runs under the CEO's hold too: GetForegroundWindow and
    # GetWindowText only look (GetWindowText does not even message a window
    # owned by another process), and the one write is foreground.json.
    record_foreground()
    lease = read_lease()

    # Under the CEO's hold the watchdog minimises nothing and resumes nothing.
    # A lease that runs out meanwhile is cleared here, and its duty to put
    # Cookie Run back moves onto the hold, for his release button to carry out.
    hold = read_ceo_hold()
    if hold is not None:
        if lease and remaining(lease) <= 0 and fold_into_hold(lease, "tick"):
            clear_lease()
            log(f"tick: lease from {lease.get('who', '?')} expired during the CEO "
                "hold - cleared; nothing minimised, nothing resumed")
        return 0

    if not lease:
        return 0
    if remaining(lease) > 0:
        return 0

    # An EXPIRED lease never ran give-back, so the screen-clearing that hangs
    # off give-back never happened either. The CEO borrowed the screen on
    # 2026-09-17, let it lapse rather than returning it, and left a Chrome
    # window over the game - the exact condition give-back was taught to
    # prevent, arriving by the one door that skips it.
    #
    # This runs IN session 1 already, so it can just do it.
    cleared = minimise_foreign_windows()
    if cleared and not cleared.startswith(("FAILED", "REFUSED")):
        log(f"tick: lease lapsed - minimised {cleared}")

    who = lease.get("who", "?")
    if not lease.get("was_running"):
        clear_lease()
        log(f"tick: lease from {who} expired; Cookie Run was not running when taken")
        return 0

    ok, why = resume(lease.get("resume") or {"fn": "night", "args": {"rounds": 60}}, "tick")
    if ok:
        clear_lease()
        log(f"tick: lease from {who} expired - Cookie Run resumed ({why})")
        return 0

    fails = int(lease.get("resume_failures", 0)) + 1
    lease["resume_failures"] = fails
    if fails >= RESUME_TRIES:
        clear_lease()
        log(f"tick: GAVE UP resuming after {fails} tries ({why}). "
            f"Cookie Run is DOWN and nothing is retrying. Lease from {who} cleared.")
    else:
        write_lease(lease)
        log(f"tick: resume attempt {fails}/{RESUME_TRIES} failed ({why}); will retry")
    return 1


# --- the CEO's two buttons ---------------------------------------------------
# windows/desktop/ceo_button.ps1 runs these and turns the output into one Thai
# message box, by reading the line prefixes below -- keep them stable:
#   PC: CEO / PC: released   the hold is on / off
#   BUMPED: <who> ...        an agent lease that just lost the screen
#   FARM: <state> - ...      what happened to Cookie Run
#   NO HOLD: / WARNING: / FAILED:
# Neither command ever minimises, clears or focuses a window. On ceo-on the
# CEO is about to use the screen; on ceo-off the windows on it are his own.

def cmd_ceo_on(_args) -> int:
    """The "use PC" button: lock agents out first, then park Cookie Run."""
    now = time.time()
    hold = read_ceo_hold()
    already = hold is not None and not hold.get("corrupt")
    if hold is not None:
        d = {k: hold.get(k) for k in HOLD_KEYS}  # keep the original since + plan
    else:
        d = {"since": now, "was_running": False, "resume": None, "bumped": None}

    lease = read_lease()
    active = lease if lease and remaining(lease) > 0 else None
    if active:
        # Bumped, not ended: the lease file stays, so its holder's next status
        # or gate shows them exactly why they are blocked, and its own plan for
        # Cookie Run survives to be handed on later.
        d["bumped"] = {"who": ascii_only(str(active.get("who", "?")))[:120],
                       "until": active.get("expires_at")}

    # Lock first, then ask Cookie Run anything. The pipe can take 20 s to answer
    # and the bot up to 40 s to stop; agents are locked out from the press, not
    # from whenever the farm gets round to replying.
    try:
        write_ceo_hold(d)
    except OSError as e:
        log(f"ceo-on: could not write the CEO hold: {e}")
        print("FAILED: could not write the CEO hold - agents are NOT locked out.")
        print(f"        {ascii_only(str(e))[:200]}")
        print("        Tell the CTO.")
        return 1

    warn = None
    s = status()
    if s is None:
        farm = "FARM: no-app - the Cookie Run app is not running, nothing to stop."
    elif s.get("esc_hold"):
        farm = "FARM: idle - Cookie Run is held by a human ESC, nothing to stop."
    elif s.get("bot_alive"):
        if not d.get("resume"):
            d["resume"] = capture_resume_plan(s)
        d["was_running"] = True
        try:
            write_ceo_hold(d)
        except OSError as e:
            log(f"ceo-on: could not record Cookie Run's plan on the hold: {e}")
            warn = ("WARNING: the lock is on, but Cookie Run's restart plan was not saved - "
                    "the release button will not bring the farm back. Tell the CTO.")
        # bot_stop, NEVER esc -- see the header. esc would keep the farm down
        # after the release button too, until a human cleared it by hand.
        run_fn("bot_stop")
        if wait_until_stopped():
            farm = "FARM: stopped - Cookie Run stopped; it comes back on the release button."
        else:
            farm = "FARM: still-running - Cookie Run did not stop."
            warn = ("WARNING: asked Cookie Run to stop but it is still alive after 40 s. "
                    "The lock is on, but the bot may still be pressing keys. Tell the CTO.")
    elif d.get("was_running"):
        farm = "FARM: stopped - Cookie Run is stopped; it comes back on the release button."
    else:
        farm = "FARM: idle - Cookie Run was not running, nothing to stop."

    since = hhmm(d["since"])
    if already:
        print(f"PC: CEO - already held since {since} (kept as it was). Agents stay")
        print("    locked out until the release button is pressed.")
    else:
        print(f"PC: CEO - the PC is the CEO's since {since}. Agents are locked out")
        print("    until the release button is pressed.")
        if hold is not None:
            print("    (the old hold file was unreadable - written again)")
    print(farm)
    if active:
        print(f"BUMPED: {d['bumped']['who']} (lease to {hhmm(active['expires_at'])}) - "
              "blocked until the release button.")
    log(f"ceo-on: CEO hold since {since}{' (already held)' if already else ''} - {farm}"
        + (f"; bumped {d['bumped']['who']}" if active else ""))
    if warn:
        print(warn)
        log(f"ceo-on: {warn}")
        return 1
    return 0


def cmd_ceo_off(_args) -> int:
    """The "done" button: lift the hold, then put Cookie Run back if it was ours."""
    hold = read_ceo_hold()
    if hold is None:
        print("NO HOLD: the CEO hold is not set - nothing to release.")
        return 0
    if not clear_ceo_hold():
        log("ceo-off: could not remove the CEO hold file")
        print("FAILED: could not remove the CEO hold - agents are still locked out.")
        print("        Tell the CTO.")
        return 1

    since = hhmm(hold["since"])
    log(f"ceo-off: CEO hold since {since} released")
    print(f"PC: released - the CEO hold (since {since}) is gone; agents may use the screen.")

    # A plan on the hold means the farm ran when SOMEBODY parked it -- ceo-on
    # itself, or a lease that ended under the hold and folded its plan in.
    was_running = bool(hold.get("was_running") or hold.get("resume"))
    plan = hold.get("resume")

    lease = read_lease()
    if lease and remaining(lease) <= 0:
        # A bumped lease that ran out before the tick folded it. Settle it here:
        # left on file, the next tick would treat it as a lapsed borrow and
        # minimise every window on screen -- the CEO's, a minute after he said
        # he was done.
        if lease.get("was_running"):
            was_running = True
            plan = plan or lease.get("resume")
        clear_lease()
        log(f"ceo-off: lease from {lease.get('who', '?')} had expired - cleared")
        lease = None

    if lease and (was_running or lease.get("was_running")):
        # An agent still holds an unexpired lease. Restarting the farm under it
        # would fight it for the screen; its give-back (or the watchdog at its
        # expiry) restores the farm, so that is where the plan goes.
        if was_running:
            lease["was_running"] = True
            lease["resume"] = plan or lease.get("resume")
            write_lease(lease)
        log(f"ceo-off: Cookie Run's restart handed to {lease.get('who', '?')}'s lease")
        print(f"FARM: handed - {lease.get('who', '?')} still holds a lease until "
              f"{hhmm(lease['expires_at'])}; Cookie Run comes back when they give it back.")
        return 0
    if hold.get("corrupt") and not was_running:
        print("FARM: unknown - the hold file was unreadable, so whether Cookie Run was")
        print("      running is unknown. Not restarting it.")
        return 0
    if not was_running:
        print("FARM: off - Cookie Run was not running when the hold began; nothing restarted.")
        return 0

    # Same fallback as give-back: a hold that knows the farm ran but not how.
    ok, why = resume(plan or {"fn": "night", "args": {"rounds": 60}}, "ceo-off")
    log(f"ceo-off: resume ok={ok} ({why})")
    if ok:
        print(f"FARM: back - Cookie Run is running again ({why}).")
        return 0
    print(f"FARM: failed - Cookie Run did not come back: {why}")
    print("Tell the CTO - the farm is idle until someone looks at it.")
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="who owns the winbox screen")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(fn=cmd_status)

    t = sub.add_parser("take")
    t.add_argument("--who", required=True, help="agent name + what for")
    t.add_argument("--minutes", type=int, default=DEFAULT_MINUTES)
    t.add_argument("--after-round", action="store_true",
                   help="let the current round finish first (slower, keeps that round's data)")
    t.add_argument("--force", action="store_true", help="take over an unexpired lease")
    t.set_defaults(fn=cmd_take)

    sub.add_parser("give-back").set_defaults(fn=cmd_give_back)
    sub.add_parser("clear-screen").set_defaults(fn=cmd_clear_screen)

    e = sub.add_parser("extend")
    e.add_argument("--minutes", type=int, default=60)
    e.set_defaults(fn=cmd_extend)

    g = sub.add_parser("gate")
    g.add_argument("--as", dest="as_who", default="",
                   help="who is calling; suppresses the NOTE when it is the lease holder")
    g.set_defaults(fn=cmd_gate)
    sub.add_parser("tick").set_defaults(fn=cmd_tick)
    sub.add_parser("ceo-on", help="the CEO's 'use PC' button").set_defaults(fn=cmd_ceo_on)
    sub.add_parser("ceo-off", help="the CEO's 'done' button").set_defaults(fn=cmd_ceo_off)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
