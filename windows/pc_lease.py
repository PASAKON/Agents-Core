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

DATA = Path.home() / "Documents" / "CookieRunScript"
TOKEN = DATA / "modelplay" / "pipe_token"
LEASE = DATA / "modelplay" / "PC_LEASE.json"
LOG = DATA / "modelplay" / "pc_lease.log"
PIPE = "http://127.0.0.1:8794"

DEFAULT_MINUTES = 120          # "others need 1-2 hours" -- CEO 2026-09-14
MAX_MINUTES = 480
RESUME_TRIES = 3               # tick gives up after this, loudly, instead of looping


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
    while time.time() - t0 < 420:
        s = status()
        if s:
            job = s.get("job")
            if job == "preflight":
                saw_preflight = True
            elif s.get("bot_alive"):
                return True, "farming"
            elif saw_preflight and not s.get("bot_alive"):
                return False, ("preflight ran and did not release the bot - "
                               "the app refused to start farming; check the app log")
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


def cmd_give_back(_args) -> int:
    lease = read_lease()
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
        print("OK - lease released. Cookie Run was not running when you took it, "
              "so nothing was restarted.")
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


def cmd_gate(_args) -> int:
    """Exit 0 if it is safe to touch the screen, 3 if a tenant is farming unleased.

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
        # spoken for (2026-09-14). So say who has it. stderr, so it cannot
        # corrupt anything parsing stdout.
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

    print("REFUSED: something is using the winbox screen and you hold no lease.")
    print("")
    print("  ./scripts/pc-lease.sh take --who \"<you>: <what for>\"")
    print("  ... your work ...")
    print("  ./scripts/pc-lease.sh give-back")
    print("")
    print("Takes ~5 s. You outrank the tenant -- this only stops you fighting it")
    print("for the foreground, which is how it stalls silently while still")
    print("reporting itself alive. See the winbox-pc-lease skill.")
    print("Override for a genuine emergency: WINBOX_NO_LEASE=1")
    return 3


def cmd_tick(_args) -> int:
    """The watchdog. Resumes Cookie Run when a lease runs out."""
    lease = read_lease()
    if not lease:
        return 0
    if remaining(lease) > 0:
        return 0

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

    e = sub.add_parser("extend")
    e.add_argument("--minutes", type=int, default=60)
    e.set_defaults(fn=cmd_extend)

    sub.add_parser("gate").set_defaults(fn=cmd_gate)
    sub.add_parser("tick").set_defaults(fn=cmd_tick)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
