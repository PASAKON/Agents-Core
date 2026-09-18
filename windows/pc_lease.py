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

Two rules are load-bearing:

* It stops the bot with bot_stop (the STOP file), NEVER with esc. esc writes
  ESC_HOLD, which blocks every future launch until a HUMAN clears it -- app.py
  refuses clear_hold unless the CTO is relaying the CEO's own words. A script
  that used esc would take the farm down for the night, not for an hour.
* The lease carries an expiry and `tick` enforces it. A borrower that crashes,
  loses its context or simply forgets costs one lease, not one night.

Output is deliberately ASCII-only: it travels back through a PowerShell argument
layer that turns non-ASCII into "?", and "?" is a single-char wildcard in
PowerShell paths (docs/reports/FINDING-winbox-ascii-only.md).
"""
import argparse
import json
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
PIPE = "http://127.0.0.1:8794"

DEFAULT_MINUTES = 120          # "others need 1-2 hours" -- CEO 2026-09-14
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

    if lease and remaining(lease) > 0:
        mins = int(remaining(lease) // 60)
        print(f"PC: BUSY - held by {lease.get('who', '?')}")
        print(f"    until {hhmm(lease['expires_at'])} ({mins} min left)")
        print("    If that is you, carry on. If not, coordinate with them -")
        print("    or take it anyway: peers outrank each other only by agreement.")
    elif lease:
        print("PC: FREE - a lease expired and the watchdog has not ticked yet")
    else:
        print("PC: FREE - nobody holds a lease")

    if s is None:
        print("Cookie Run: app NOT running (nothing to stop, screen is yours)")
    elif s.get("esc_hold"):
        print("Cookie Run: HELD by a human ESC (stays stopped until a human clears it)")
    elif s.get("bot_alive"):
        print("Cookie Run: RUNNING - call `take` before you touch the screen")
    else:
        print("Cookie Run: idle (app up, bot stopped)")
    return 0


def cmd_take(args) -> int:
    minutes = max(1, min(int(args.minutes), MAX_MINUTES))
    who = ascii_only(args.who or "unnamed agent")[:120]

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
    """
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
    """Exit 0 if it is safe to touch the screen, 3 if a tenant is farming unleased.

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
    """
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
    record_foreground()
    lease = read_lease()
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
    if cleared and not cleared.startswith("FAILED"):
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

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
