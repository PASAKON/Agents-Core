#!/usr/bin/env python3
"""cookierun_probe.py -- drive the game by hand for one errand, from session 1.

The app's pipe can start and stop the bot but cannot press anything or look at
the screen, and a plain ssh session lands in session 0 where the game's window
does not exist. So an errand that needs eyes and a finger -- reading the Combi
off the loadout screen, for instance -- runs here, launched by an INTERACTIVE
scheduled task.

It reads a plan and executes it in order:

    [{"shot": "00-start"},
     {"click": [0.50, 0.90], "wait": 2.0, "why": "ready button"},
     {"shot": "01-loadout"}]

click coordinates are NORMALISED to the game rect (0..1), never raw pixels, and
they go through core.win_point() -- the same function the bot uses. Raw pixels
are how a click ends up 115 px past the thing it was aimed at while every match
score stays perfect (2026-09-16, game_settings).

Every step is logged with what it did, so a run can be read back without
opening a single screenshot.

    python cookierun_probe.py <plan.json> <outdir>
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\UsEr\cookierun-bot")

import cv2                      # noqa: E402
# core is where the geometry actually lives. engine re-exports click/grab/
# win_point but NOT game_rect, so importing only engine dies at the first call
# with AttributeError -- import the module that owns them.
import core                     # noqa: E402

# Reuse core's own SendInput structures -- redeclaring them here is how the
# field layouts silently drift apart and a keystroke goes nowhere.
import ctypes                   # noqa: E402
from core import (_INPUT, _KEYBDINPUT, INPUT_KEYBOARD,   # noqa: E402
                  KEYEVENTF_KEYUP)

KEYEVENTF_UNICODE = 0x0004
VK_BACK = 0x08
# BlueStacks does not type into the game's field directly: text goes to an
# Android IME overlay strip at the top of the screen and only lands in the
# field when Enter commits it. Typing alone looked like it had worked -- the
# overlay showed the word -- while the field underneath still read "Combi".
VK_RETURN = 0x0D


def _send(ev_list) -> None:
    n = len(ev_list)
    arr = (_INPUT * n)(*ev_list)
    if ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(_INPUT)) != n:
        raise RuntimeError(f"SendInput rejected {n} event(s)")


def type_text(s: str) -> None:
    """Type arbitrary text into whatever has focus.

    core.send_key only knows the keys the bot plays with -- it maps a NAME
    through a VK table and raises KeyError on anything else, so it cannot type
    a word. This uses KEYEVENTF_UNICODE, which delivers the character itself
    rather than a key position, so it is also immune to whatever keyboard
    layout the box happens to be on.
    """
    ev = []
    for ch in s:
        for up in (0, KEYEVENTF_KEYUP):
            e = _INPUT(type=INPUT_KEYBOARD)
            e.ki = _KEYBDINPUT(wVk=0, wScan=ord(ch),
                               dwFlags=KEYEVENTF_UNICODE | up, time=0,
                               dwExtraInfo=None)
            ev.append(e)
    _send(ev)


def press_vk(vk: int, times: int = 1) -> None:
    """Press a virtual key (backspace, enter) -- what UNICODE events cannot do."""
    ev = []
    for _ in range(times):
        for up in (0, KEYEVENTF_KEYUP):
            e = _INPUT(type=INPUT_KEYBOARD)
            e.ki = _KEYBDINPUT(wVk=vk, wScan=0, dwFlags=up, time=0,
                               dwExtraInfo=None)
            ev.append(e)
    _send(ev)


def main() -> int:
    plan_path, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    log = (outdir / "probe.log").open("w", encoding="utf-8")

    def say(msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        log.write(line + "\n")
        log.flush()
        print(line)

    rect = core.game_rect()
    if not rect:
        say("ABORT: BlueStacks window not found -- is the game running?")
        return 2
    say(f"game rect: {rect}")

    region = core.resolve_region({"rel": [0, 0, 1, 1], "window": core.GAME_WINDOW})
    steps = json.loads(plan_path.read_text(encoding="utf-8"))

    for i, step in enumerate(steps):
        if "shot" in step:
            img = core.grab(region)
            p = outdir / f"{step['shot']}.png"
            cv2.imwrite(str(p), img)
            say(f"[{i}] shot -> {p.name}  ({img.shape[1]}x{img.shape[0]})")
        if "click" in step:
            nx, ny = step["click"]
            x, y = core.win_point(core.GAME_WINDOW, float(nx), float(ny))
            core.click(x, y, why=step.get("why", "probe"))
            say(f"[{i}] click ({nx:.4f},{ny:.4f}) -> screen ({x},{y})"
                f"  {step.get('why', '')}")
        if "vk" in step:
            press_vk(int(step["vk"]), int(step.get("times", 1)))
            say(f"[{i}] vk 0x{int(step['vk']):02X} x{step.get('times', 1)}"
                f"  {step.get('why', '')}")
        if "clear" in step:
            press_vk(VK_BACK, int(step["clear"]))
            say(f"[{i}] backspace x{step['clear']}")
        if "type" in step:
            type_text(step["type"])
            say(f"[{i}] typed {step['type']!r}")
        if "wait" in step:
            time.sleep(float(step["wait"]))
            say(f"[{i}] waited {step['wait']}s")

    say("plan complete")
    log.close()
    return 0


if __name__ == "__main__":
    # Run under pythonw, never python: a console window belongs to whatever
    # launched it and it opens ON TOP of the game, so the first screenshot came
    # back with a black rectangle over the top-left quarter of the board. A tool
    # for looking at the screen must not be visible on it. Which means nothing
    # can be reported via stdout either -- the log is the only channel, so the
    # log has to survive a crash.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        out.mkdir(parents=True, exist_ok=True)
        (out / "probe.log").open("a", encoding="utf-8").write(traceback.format_exc())
        raise SystemExit(3)
