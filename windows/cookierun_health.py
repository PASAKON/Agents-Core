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
CHECK_WINDOW_S = 70 * 60     # one hourly check plus slack, so none slips between


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
    """(name, runs, last_write, started) for the session the bot is writing to.

    `started` comes from the session name -- session-<epoch> -- rather than
    ctime, which Windows preserves across a copy and would quietly mis-date a
    restored directory.
    """
    try:
        dirs = [p for p in MODELPLAY.glob("session-*") if p.is_dir()]
    except OSError:
        return None, 0, None, None
    if not dirs:
        return None, 0, None, None
    d = max(dirs, key=lambda p: p.stat().st_mtime)
    runs = len([x for x in d.iterdir() if x.is_dir()])
    try:
        started = float(d.name.split("-", 1)[1])
    except (IndexError, ValueError):
        started = d.stat().st_ctime
    return d.name, runs, d.stat().st_mtime, started


def recent_stalls(session_start: float | None):
    """Stalls that are NEW since the last check, and in the current run.

    Two ways to get this wrong, both met in practice on 2026-09-15/16:

    A fixed wall-clock window alone keeps reporting STALLING for hours after the
    screen has been named and the bot restarted with the fix -- it cannot tell
    "happening now" from "happened and was dealt with", so it cries wolf at its
    own repair.

    Run-scoping alone has the same failure with a longer fuse: this run has been
    going four hours, so one stall at 06:30 would be re-reported on every hourly
    check until the bot happens to restart. That is worse, because the fix for a
    stall is often NOT a restart.

    So: newer than the running session (a restart clears the slate) AND newer
    than one check interval, with slack so nothing slips between checks. Each
    stall is then reported exactly once -- on the check that discovers it.
    """
    if not STALLS.is_dir():
        return 0, 0
    files = list(STALLS.glob("*.png"))
    since_last_check = time.time() - CHECK_WINDOW_S
    cutoff = max(session_start, since_last_check) if session_start else since_last_check
    return len(files), len([f for f in files if f.stat().st_mtime > cutoff])


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


def credential_dialog() -> bool:
    """Is a Windows credential prompt sitting on the screen?

    A "Sign in with a passkey" dialog from CredentialUIBroker parked itself over
    the game at 23:37 on 2026-09-16 and stayed. It cannot be clicked away by
    script -- Windows deliberately makes credential prompts ignore synthetic
    input -- so this is a human-only fix, and the farm is dead until someone
    presses Cancel. Worth naming in the verdict rather than reporting a generic
    DOWN and making the next reader rediscover it.
    """
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "if (Get-Process -Name CredentialUIBroker -ErrorAction SilentlyContinue) "
             "{ 'yes' } else { 'no' }"],
            capture_output=True, text=True, timeout=25,
            creationflags=0x08000000).stdout.strip()
        return out == "yes"
    except Exception:
        return False


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
    sess, runs, mtime, started = newest_session()
    stalls_total, stalls_recent = recent_stalls(started)
    gb = free_gb()
    fg = foreground_app()
    cred = credential_dialog()
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
    elif cred and not s.get("bot_alive"):
        verdict, reason = ("BLOCKED",
                           "a Windows credential dialog is on the screen. It cannot be "
                           "dismissed by script - Windows ignores synthetic clicks on "
                           "credential prompts by design. A HUMAN must press Cancel.")
    elif not s.get("bot_alive"):
        verdict, reason = "DOWN", "nobody holds the screen and the bot is not running"
    elif s.get("job") == "preflight":
        verdict, reason = "OK", "preflight dry round in progress"
    elif fg and fg != GAME_PKG:
        verdict, reason = "STUCK", f"a foreign app owns the emulator screen: {fg}"
    elif age_min is not None and age_min > ROUND_QUIET_S / 60:
        verdict, reason = "STUCK", f"bot is alive but has written nothing for {age_min} min"
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
    lines.append(f"rounds : {sess} runs={runs} last_write={age_min} min ago")
    lines.append(f"stalls : {stalls_total} total, {stalls_recent} new since the last check")
    lines.append(f"screen : {fg or 'unknown'}" + ('' if fg in (None, GAME_PKG) else '  <-- NOT the game'))
    # Only when it is actually the verdict. The broker process lingers after its
    # dialog is dismissed, so printing this on every check -- while the farm is
    # plainly farming -- is the same cry-wolf failure as the stall window was.
    if verdict == "BLOCKED":
        lines.append("BLOCKER: Windows credential dialog open (human must click Cancel)")
    lines.append(f"disk   : {gb} GB free on C:")
    print("\n".join(lines))

    return 0 if verdict in ("OK", "PARKED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
