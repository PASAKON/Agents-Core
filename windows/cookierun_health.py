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
CHECK_WINDOW_S = 70 * 60     # fallback only, for the first run / lost state
LAST_CHECK = MODELPLAY / "health_last_check"
FOREGROUND = MODELPLAY / "foreground.json"
FOREGROUND_STALE_S = 8 * 60   # tick writes it every few minutes


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


def window_over_game():
    """Title of the non-BlueStacks window holding the Windows foreground, or None.

    This check runs over ssh, in session 0, which cannot see session 1's windows
    at all - so it reads what pc_lease's tick recorded from inside session 1.
    An answer older than FOREGROUND_STALE_S is discarded rather than trusted: a
    check that cannot tell true from false has no business setting a verdict,
    which is the lesson the removed CredentialUIBroker check left behind.
    """
    try:
        d = json.loads(FOREGROUND.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if time.time() - float(d.get("t", 0)) > FOREGROUND_STALE_S:
        return None
    return None if d.get("is_tenant") else (d.get("title") or "an untitled window")


def newest_session():
    """(name, runs, last_progress, started) for the session the bot is writing to.

    `started` comes from the session name -- session-<epoch> -- rather than
    ctime, which Windows preserves across a copy and would quietly mis-date a
    restored directory.

    `last_progress` is the newest ROUND, not the session directory's mtime.
    Those are not the same thing, and the difference hid a 50-minute outage on
    2026-09-17: a Windows passkey dialog covered the game, the bot crashed, the
    supervisor opened a fresh session directory -- and that write refreshed the
    very timestamp this check reads to decide whether anything is happening. A
    farm that had produced nothing since 11:40 measured twelve minutes old and
    the verdict came back OK. A round is the work; nothing else counts as
    progress, least of all a restart.
    """
    try:
        dirs = [p for p in MODELPLAY.glob("session-*") if p.is_dir()]
    except OSError:
        return None, 0, None, None
    if not dirs:
        return None, 0, None, None
    d = max(dirs, key=lambda p: p.stat().st_mtime)
    run_dirs = [x for x in d.iterdir() if x.is_dir()]
    try:
        started = float(d.name.split("-", 1)[1])
    except (IndexError, ValueError):
        started = d.stat().st_ctime
    # No rounds yet is not "no information": a session that has been open for
    # half an hour without finishing one is exactly the case worth catching.
    last_progress = max([x.stat().st_mtime for x in run_dirs], default=started)
    return d.name, len(run_dirs), last_progress, started


def recent_stalls():
    """Stalls that have appeared since the previous run of this check.

    Third attempt, and the first one that is actually about "new".

    A fixed wall-clock window keeps reporting STALLING for hours after the
    screen has been named and the bot restarted with the fix -- it cannot tell
    "happening now" from "happened and was dealt with", so it cries wolf at its
    own repair (2026-09-15).

    Scoping to the running session fixes that and breaks the opposite way: a
    restart clears the slate, so the stalls that happened in the minute BEFORE
    it -- the ones that caused the restart -- are the ones it throws away. On
    2026-09-17 two stalls were saved at 12:04 and 12:12, the bot crashed and
    reopened a session at 12:13, and this reported "0 new" over the top of an
    hour-long outage.

    Both of those are proxies for the only question worth asking: has anything
    happened that I have not already seen? So ask it directly -- remember when
    this last ran. Each stall is then reported exactly once, on the check that
    discovers it, whatever the bot did in between.

    The cost of remembering is that a second run in the same minute reports 0:
    this check consumes what it reports. That is the contract, and it is why
    only one caller should be running it on a schedule.
    """
    if not STALLS.is_dir():
        return 0, 0
    try:
        since = float(LAST_CHECK.read_text().strip())
    except (OSError, ValueError):
        since = time.time() - CHECK_WINDOW_S     # first run, or state lost
    files = list(STALLS.glob("*.png"))
    new = len([f for f in files if f.stat().st_mtime > since])
    try:
        LAST_CHECK.write_text(str(time.time()))
    except OSError:
        pass                                      # degrade to the window, never crash
    return len(files), new


ADB = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PKG = "com.devsisters.crg"


def foreground_app() -> str | None:
    """Which Android app owns the emulator screen, or None if we cannot tell.

    Chrome's first-run page took the foreground on 2026-09-16 and the bot sat on
    it for 25 minutes before its pixel-based stuck timer noticed. Android knows
    the answer instantly. BlueStacks blocks `am` and `pm` over adb ("error:
    closed") but `dumpsys` reads fine, so detection works even though control
    does not -- which is the half that matters here.
    """
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


# There was a credential_dialog() check here, and a BLOCKED verdict built on it.
# Removed 2026-09-17: it tested for the CredentialUIBroker *process*, which
# lingers long after its dialog is gone, so it reported "a dialog is on the
# screen, a human must click Cancel" against a screenshot-verified empty lobby.
# There is no cheap way from session 0 to tell a live dialog from a stale
# process -- window enumeration needs session 1 -- and a check that cannot tell
# true from false has no business setting a verdict. DOWN is accurate; go look
# at the screen when it says so.


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
    sess, runs, last_progress, started = newest_session()
    stalls_total, stalls_recent = recent_stalls()
    gb = free_gb()
    fg = foreground_app()
    fg_win = window_over_game()
    age_min = int((time.time() - last_progress) / 60) if last_progress else None

    lines = []
    verdict = "OK"
    reason = ""

    if s is None:
        verdict, reason = "NO-APP", "the Cookie Run app is not running, so nothing can drive the bot"
    elif s.get("esc_hold"):
        verdict, reason = "DOWN", "ESC hold is set - a human stopped the bot and only a human clears it"
    elif fg_win:
        # Someone is using the desktop. Cookie Run yields to other computer-use
        # agents, always (CEO) - so this is PARKED, not a fault, whether or not
        # they remembered the lease. Reporting DOWN here would send whoever
        # reads it to go restart a farm that must not start.
        verdict = "PARKED"
        reason = (f"a window is over the game on the Windows side: {fg_win!r} - "
                  f"Cookie Run yields; Android still reports the game foreground "
                  f"because it is, underneath")
    elif lease:
        verdict = "PARKED"
        reason = f"screen lent to {lease.get('who', '?')} until {time.strftime('%H:%M', time.localtime(lease['expires_at']))}"
    elif not s.get("bot_alive"):
        verdict, reason = "DOWN", "nobody holds the screen and the bot is not running"
    elif s.get("job") == "preflight":
        # A preflight in progress is normal. A preflight still in progress hours
        # after the last finished round is a loop, and calling that OK is how
        # this check reported green through a three-hour outage on 2026-09-17
        # while played_24h sat frozen at 0.167. The gate is allowed to take a
        # while; it is not allowed to become the steady state.
        if age_min is not None and age_min > 45:
            verdict, reason = ("STUCK", f"preflight has been cycling for {age_min} min "
                                        f"without a finished round - it is looping, not starting")
        else:
            verdict, reason = "OK", "preflight dry round in progress"
    elif fg and fg != GAME_PKG:
        verdict, reason = "STUCK", f"a foreign app owns the emulator screen: {fg}"
    elif age_min is not None and age_min >= ROUND_QUIET_S / 60:
        verdict, reason = "STUCK", f"bot is alive but has finished no round for {age_min} min"
    elif stalls_recent:
        verdict, reason = "STALLING", f"{stalls_recent} screen(s) the navigator could not name since the last check"

    lines.append(f"VERDICT: {verdict}")
    if reason:
        lines.append(f"reason : {reason}")
    if s:
        lines.append(f"bot    : alive={s.get('bot_alive')} job={s.get('job')} "
                     f"guard={s.get('night_guard')} esc_hold={s.get('esc_hold')} "
                     f"played_24h={s.get('played_fraction_24h')}")
    lines.append(f"lease  : {'held by ' + str(lease.get('who')) if lease else 'free'}")
    lines.append(f"rounds : {sess} runs={runs} last_round={age_min} min ago")
    lines.append(f"stalls : {stalls_total} total, {stalls_recent} new since the last check")
    if fg_win:
        lines.append(f"window : {fg_win}  <-- over the game, Windows side")
    lines.append(f"screen : {fg or 'unknown'}" + ('' if fg in (None, GAME_PKG) else '  <-- NOT the game'))
    lines.append(f"disk   : {gb} GB free on C:")
    print("\n".join(lines))

    return 0 if verdict in ("OK", "PARKED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
