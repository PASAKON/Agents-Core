"""The CEO's hold on the winbox screen (windows/pc_lease.py ceo-on / ceo-off).

Twice (2026-10-07, 2026-10-09 13:36) an agent took a FREE lease and relaunched
Minecraft over the Dota 2 game the CEO was playing. His two desktop buttons
(windows/desktop/) set a hold that every agent-facing command must respect.

pc_lease.py runs on Windows and talks to the Cookie Run app over a local pipe,
so every call that would leave this process -- status, run_fn, pipe, the
screen-clear task, the window minimiser, resume, wait_until_stopped,
record_foreground -- is swapped for a recorder. Nothing here touches a real
window, a real pipe, or the real ~/Documents/CookieRunScript.

Run:  python -m pytest tests/test_pc_lease_ceo_hold.py -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
PC_LEASE = ROOT / "windows" / "pc_lease.py"
REVIVE = ROOT / "windows" / "cookierun_revive.py"
HEALTH = ROOT / "windows" / "cookierun_health.py"
DESKTOP = ROOT / "windows" / "desktop"
ON_CMD = DESKTOP / "\u0e43\u0e0a\u0e49\u0e04\u0e2d\u0e21.cmd"                       # ใช้คอม.cmd
OFF_CMD = DESKTOP / "\u0e40\u0e25\u0e34\u0e01\u0e43\u0e0a\u0e49\u0e04\u0e2d\u0e21.cmd"   # เลิกใช้คอม.cmd
PS1 = DESKTOP / "ceo_button.ps1"

NIGHT_PLAN = {"fn": "night", "args": {"model": "champ", "rounds": 60}}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def box(tmp_path, monkeypatch):
    """A fresh pc_lease module pointed at tmp_path, with every outside effect recorded."""
    m = load(PC_LEASE, "pc_lease_under_test")
    data = tmp_path / "CookieRunScript"
    mp = data / "modelplay"
    m.DATA = data
    m.TOKEN = mp / "pipe_token"
    m.LEASE = mp / "PC_LEASE.json"
    m.LOG = mp / "pc_lease.log"
    m.CEO_HOLD = mp / "CEO_HOLD.json"
    m.CEO_HOLD_LOCK = mp / "CEO_HOLD.lock"
    m.RESUMING = mp / "FARM_RESUMING.json"
    m.FOREGROUND = mp / "foreground.json"

    calls: list[tuple] = []
    # hooks: {"status" | "nap" | "request_screen_clear" | <run_fn name>: callable},
    # run when that call happens -- how a test makes the CEO press a button
    # in the middle of another command.
    st = SimpleNamespace(status={"bot_alive": False}, stops=True, resume_ok=True,
                         hooks={}, game_up=True)

    def hook(name):
        f = st.hooks.get(name)
        if f:
            f()

    def fake_status():
        calls.append(("status",))
        hook("status")
        return None if st.status is None else dict(st.status)

    def fake_run_fn(fn, args=None):
        calls.append(("run_fn", fn, args))
        if fn == "bot_stop" and st.stops and st.status is not None:
            st.status["bot_alive"] = False
            st.status["job"] = None
        hook(fn)
        return {"ok": True}

    def fake_pipe(*a, **k):
        calls.append(("pipe",) + a)
        return None

    def fake_resume(plan, why):
        calls.append(("resume", plan, why))
        return (True, "farming") if st.resume_ok else (False, "pipe call failed")

    def fake_wait_until_stopped(limit_s=40):
        calls.append(("wait_until_stopped",))
        return st.status is None or not st.status.get("bot_alive")

    originals = {k: getattr(m, k) for k in ("resume", "minimise_foreign_windows",
                                            "request_screen_clear")}
    m.status = fake_status
    m.run_fn = fake_run_fn
    m.pipe = fake_pipe
    m.request_screen_clear = lambda: calls.append(("request_screen_clear",)) or hook(
        "request_screen_clear")
    m.minimise_foreign_windows = lambda: calls.append(("minimise",)) or "Chrome"
    m.resume = fake_resume
    m.wait_until_stopped = fake_wait_until_stopped
    m.record_foreground = lambda: calls.append(("record_foreground",))
    m.nap = lambda sec: calls.append(("nap", sec)) or hook("nap")
    m.game_running = lambda: st.game_up

    def run(*argv):
        monkeypatch.setattr(sys, "argv", ["pc_lease.py", *argv])
        return m.main()

    def names():
        return [c[0] for c in calls]

    return SimpleNamespace(m=m, calls=calls, st=st, run=run, names=names,
                           originals=originals, mp=mp)


def put_lease(box, *, minutes_left=30, who="cto: sky scene", was_running=True,
              resume=NIGHT_PLAN):
    now = time.time()
    box.m.write_lease({"who": who, "taken_at": now - 600,
                       "expires_at": now + minutes_left * 60,
                       "was_running": was_running, "resume": resume,
                       "resume_failures": 0})


def put_hold(box, **kw):
    d = {"since": time.time() - 300, "was_running": False, "resume": None, "bumped": None}
    d.update(kw)
    box.m.write_ceo_hold(d)
    return d


def hold_on_disk(box):
    return json.loads(box.m.CEO_HOLD.read_text(encoding="utf-8"))


def never_touched_windows(box):
    return "minimise" not in box.names() and "request_screen_clear" not in box.names()


# --- ceo-on -------------------------------------------------------------------

def test_ceo_on_writes_the_hold_and_is_idempotent(box, capsys):
    assert box.run("ceo-on") == 0
    first = hold_on_disk(box)
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("PC: CEO - ")
    assert "locked out" in out and out.isascii()

    time.sleep(0.01)
    assert box.run("ceo-on") == 0
    out = capsys.readouterr().out
    assert "already held" in out
    assert hold_on_disk(box)["since"] == first["since"]
    assert never_touched_windows(box)


def test_ceo_on_with_the_bot_alive_stops_it_with_bot_stop_never_esc(box, capsys):
    box.st.status = {"bot_alive": True, "night_guard": True, "champion": "champ"}
    assert box.run("ceo-on") == 0
    fns = [c[1] for c in box.calls if c[0] == "run_fn"]
    assert fns == ["bot_stop"]
    assert "esc" not in fns
    h = hold_on_disk(box)
    assert h["was_running"] is True
    assert h["resume"] == {"fn": "night", "args": {"model": "champ", "rounds": 60}}
    assert "FARM: stopped" in capsys.readouterr().out
    assert never_touched_windows(box)


def test_ceo_on_second_press_keeps_the_original_plan(box, capsys):
    box.st.status = {"bot_alive": True, "night_guard": True, "champion": "champ"}
    box.run("ceo-on")
    plan = hold_on_disk(box)["resume"]
    box.st.status = {"bot_alive": True, "night_guard": False, "champion": "other"}
    box.run("ceo-on")
    assert hold_on_disk(box)["resume"] == plan
    assert hold_on_disk(box)["was_running"] is True


def test_ceo_on_still_holds_when_the_bot_will_not_stop(box, capsys):
    box.st.status = {"bot_alive": True, "night_guard": True, "champion": "champ"}
    box.st.stops = False
    assert box.run("ceo-on") == 1
    out = capsys.readouterr().out
    assert box.m.CEO_HOLD.exists()
    assert out.splitlines()[0].startswith("PC: CEO - ")
    assert "WARNING:" in out and out.isascii()
    assert never_touched_windows(box)


def test_ceo_on_bumps_an_active_lease_and_keeps_its_file(box, capsys):
    put_lease(box, who="cto: sky scene r22")
    assert box.run("ceo-on") == 0
    out = capsys.readouterr().out
    assert "BUMPED: cto: sky scene r22" in out
    assert hold_on_disk(box)["bumped"]["who"] == "cto: sky scene r22"
    assert box.m.LEASE.exists(), "the holder must still see their lease - and that it is blocked"
    assert never_touched_windows(box)


def test_ceo_on_leaves_no_temp_file_behind(box):
    box.run("ceo-on")
    assert sorted(p.name for p in box.mp.iterdir() if "CEO_HOLD" in p.name) == ["CEO_HOLD.json"]


def test_ceo_on_rewrites_an_unreadable_hold_and_stays_held(box, capsys):
    box.mp.mkdir(parents=True, exist_ok=True)
    box.m.CEO_HOLD.write_text("{not json", encoding="utf-8")
    assert box.run("ceo-on") == 0
    assert isinstance(hold_on_disk(box)["since"], (int, float))
    assert "unreadable" in capsys.readouterr().out


# --- ceo-off ------------------------------------------------------------------

def test_ceo_off_without_a_hold_says_so(box, capsys):
    assert box.run("ceo-off") == 0
    assert capsys.readouterr().out.startswith("NO HOLD:")
    assert "resume" not in box.names()


def test_ceo_off_resumes_the_farm_it_stopped(box, capsys):
    box.st.status = {"bot_alive": True, "night_guard": True, "champion": "champ"}
    box.run("ceo-on")
    capsys.readouterr()
    assert box.run("ceo-off") == 0
    out = capsys.readouterr().out
    assert not box.m.CEO_HOLD.exists()
    resumes = [c for c in box.calls if c[0] == "resume"]
    assert resumes == [("resume", {"fn": "night", "args": {"model": "champ", "rounds": 60}},
                        "ceo-off")]
    assert out.splitlines()[0].startswith("PC: released")
    assert "FARM: back" in out and out.isascii()
    assert never_touched_windows(box)


def test_ceo_off_does_not_resume_a_farm_that_was_not_running(box, capsys):
    box.run("ceo-on")
    assert box.run("ceo-off") == 0
    assert "resume" not in box.names()
    assert "FARM: off" in capsys.readouterr().out
    assert never_touched_windows(box)


def test_ceo_off_reports_a_failed_resume(box, capsys):
    put_hold(box, was_running=True, resume=NIGHT_PLAN)
    box.st.resume_ok = False
    assert box.run("ceo-off") == 1
    out = capsys.readouterr().out
    assert "FARM: failed" in out and not box.m.CEO_HOLD.exists()


def test_ceo_off_hands_the_plan_to_an_active_agent_lease(box, capsys):
    put_lease(box, was_running=False, resume=None, who="browser_operator: clips")
    put_hold(box, was_running=True, resume=NIGHT_PLAN)
    assert box.run("ceo-off") == 0
    out = capsys.readouterr().out
    assert "resume" not in box.names()
    lease = box.m.read_lease()
    assert lease["was_running"] is True and lease["resume"] == NIGHT_PLAN
    assert "FARM: handed" in out
    assert never_touched_windows(box)


def test_ceo_off_settles_an_expired_bumped_lease_itself(box, capsys):
    """Left on file, the next tick would minimise the CEO's own windows."""
    put_lease(box, minutes_left=-5, was_running=True, resume=NIGHT_PLAN)
    put_hold(box)
    assert box.run("ceo-off") == 0
    assert not box.m.LEASE.exists()
    assert [c for c in box.calls if c[0] == "resume"] == [("resume", NIGHT_PLAN, "ceo-off")]
    assert never_touched_windows(box)


def test_ceo_off_on_an_unreadable_hold_releases_without_guessing(box, capsys):
    box.mp.mkdir(parents=True, exist_ok=True)
    box.m.CEO_HOLD.write_text("", encoding="utf-8")
    assert box.run("ceo-off") == 0
    assert not box.m.CEO_HOLD.exists()
    assert "FARM: unknown" in capsys.readouterr().out
    assert "resume" not in box.names()


# --- what agents meet under the hold ----------------------------------------

@pytest.mark.parametrize("content", ["{not json", "", "[]", '{"since": "noon"}'])
def test_an_unparseable_hold_file_counts_as_held(box, content):
    box.mp.mkdir(parents=True, exist_ok=True)
    box.m.CEO_HOLD.write_text(content, encoding="utf-8")
    h = box.m.read_ceo_hold()
    assert h is not None and h["corrupt"] is True
    assert box.run("take", "--who", "codex: shoot") == 2


def test_no_hold_file_means_no_hold(box):
    assert box.m.read_ceo_hold() is None


@pytest.mark.parametrize("force", [False, True])
def test_take_is_refused_under_the_hold_even_with_force(box, capsys, force):
    put_hold(box)
    argv = ["take", "--who", "cto: sky scene"] + (["--force"] if force else [])
    assert box.run(*argv) == 2
    out = capsys.readouterr().out
    assert out.startswith("REFUSED: the CEO is using this PC")
    assert re.search(r"since \d\d:\d\d", out) and "release button" in out
    assert not box.m.LEASE.exists()
    assert box.names() == [], "a refused take must not even ask Cookie Run"


def test_take_refuses_when_the_ceo_presses_mid_take(box, capsys):
    """The bot stopped for the agent becomes the CEO's release button's to restart."""
    box.st.status = {"bot_alive": True, "night_guard": True, "champion": "champ"}
    real_run_fn = box.m.run_fn

    def ceo_presses_during_the_stop(fn, args=None):
        r = real_run_fn(fn, args)
        put_hold(box)
        return r

    box.m.run_fn = ceo_presses_during_the_stop
    assert box.run("take", "--who", "cto: sky scene") == 2
    assert not box.m.LEASE.exists()
    h = hold_on_disk(box)
    assert h["was_running"] is True and h["resume"]["fn"] == "night"


def test_extend_is_refused_under_the_hold(box, capsys):
    put_lease(box)
    before = box.m.read_lease()["expires_at"]
    put_hold(box)
    assert box.run("extend", "--minutes", "60") == 2
    assert capsys.readouterr().out.startswith("REFUSED: the CEO is using this PC")
    assert box.m.read_lease()["expires_at"] == before


@pytest.mark.parametrize("as_who", [None, "cto: sky scene"])
def test_gate_refuses_under_the_hold_with_an_empty_stdout(box, capsys, as_who):
    put_lease(box, who="cto: sky scene")
    put_hold(box)
    argv = ["gate"] + (["--as", as_who] if as_who else [])
    assert box.run(*argv) == 3
    cap = capsys.readouterr()
    assert cap.out == ""
    assert cap.err.startswith("REFUSED: the CEO is using the winbox screen")


def test_gate_without_a_hold_still_passes_an_idle_farm(box, capsys):
    assert box.run("gate") == 0
    assert capsys.readouterr().out == ""


def test_status_first_line_under_the_hold(box, capsys):
    put_lease(box)
    put_hold(box)
    box.st.status = {"bot_alive": False}
    assert box.run("status") == 0
    out = capsys.readouterr().out
    assert re.fullmatch(r"PC: CEO - the CEO is using this PC since \d\d:\d\d\. "
                        r"Hands off the screen\.", out.splitlines()[0])
    assert "PC: BUSY" in out and "Cookie Run: idle" in out
    assert "PC: FREE" not in out and out.isascii()


def test_status_never_says_free_under_the_hold(box, capsys):
    put_hold(box)
    box.st.status = None
    box.run("status")
    out = capsys.readouterr().out
    assert "FREE" not in out and "screen is yours" not in out


# --- the watchdog and give-back under the hold ---------------------------------

def test_tick_under_the_hold_folds_an_expired_lease_and_touches_nothing(box):
    put_lease(box, minutes_left=-1, was_running=True, resume=NIGHT_PLAN)
    put_hold(box)
    assert box.run("tick") == 0
    assert "record_foreground" in box.names()
    assert "minimise" not in box.names() and "resume" not in box.names()
    assert not box.m.LEASE.exists()
    h = hold_on_disk(box)
    assert h["was_running"] is True and h["resume"] == NIGHT_PLAN


def test_tick_under_the_hold_leaves_an_active_lease_alone(box):
    put_lease(box, minutes_left=30)
    put_hold(box)
    assert box.run("tick") == 0
    assert box.m.LEASE.exists()
    assert hold_on_disk(box)["was_running"] is False
    assert "minimise" not in box.names() and "resume" not in box.names()


def test_tick_without_a_hold_still_does_its_job(box):
    put_lease(box, minutes_left=-1, was_running=True, resume=NIGHT_PLAN)
    assert box.run("tick") == 0
    assert "minimise" in box.names() and "resume" in box.names()


def test_give_back_under_the_hold_clears_nothing_and_resumes_nothing(box, capsys):
    put_lease(box, was_running=True, resume=NIGHT_PLAN)
    put_hold(box)
    assert box.run("give-back") == 0
    out = capsys.readouterr().out
    assert never_touched_windows(box) and "resume" not in box.names()
    assert not box.m.LEASE.exists()
    h = hold_on_disk(box)
    assert h["was_running"] is True and h["resume"] == NIGHT_PLAN
    assert "CEO" in out and "release button" in out and out.isascii()


def test_give_back_under_the_hold_with_no_lease(box, capsys):
    put_hold(box)
    assert box.run("give-back") == 0
    assert never_touched_windows(box)
    assert "CEO" in capsys.readouterr().out


def test_full_cycle_agent_bumped_then_expired_then_ceo_off(box, capsys):
    """take -> ceo-on bumps it -> it expires under the hold -> ceo-off restores."""
    box.st.status = {"bot_alive": True, "night_guard": True, "champion": "champ"}
    assert box.run("take", "--who", "cto: sky scene") == 0
    assert box.run("ceo-on") == 0
    lease = box.m.read_lease()
    lease["expires_at"] = time.time() - 1
    box.m.write_lease(lease)
    assert box.run("tick") == 0
    assert box.run("ceo-off") == 0
    resumes = [c for c in box.calls if c[0] == "resume"]
    assert resumes == [("resume", {"fn": "night", "args": {"model": "champ", "rounds": 60}},
                        "ceo-off")]
    assert "minimise" not in box.names()


# --- the backstops inside the two functions that act on the screen --------------

def test_the_real_minimiser_refuses_under_the_hold(box):
    put_hold(box)
    out = box.originals["minimise_foreign_windows"]()
    assert out.startswith("REFUSED")


def test_the_real_resume_refuses_under_the_hold(box):
    put_hold(box)
    ok, why = box.originals["resume"](NIGHT_PLAN, "test")
    assert ok is False and "CEO" in why
    assert "status" not in box.names()


def test_the_real_clear_screen_task_entry_refuses_under_the_hold(box, capsys):
    put_hold(box)
    box.m.minimise_foreign_windows = box.originals["minimise_foreign_windows"]
    assert box.run("clear-screen") == 0
    assert capsys.readouterr().out.startswith("REFUSED")


# --- the other two watchdogs on the box --------------------------------------------

def test_revive_stands_down_under_the_hold(tmp_path):
    r = load(REVIVE, "revive_under_test")
    r.CEO_HOLD = tmp_path / "CEO_HOLD.json"
    r.LOG = tmp_path / "revive.log"
    seen = []
    r.pipe = lambda *a, **k: seen.append(a)
    r.CEO_HOLD.write_text("{}", encoding="utf-8")
    assert r.main() == 0
    assert seen == [], "revive must not even ask the app anything under the hold"
    r.CEO_HOLD.unlink()
    assert r.ceo_holds_the_pc() is False


def test_health_calls_a_held_farm_parked_not_down(tmp_path, capsys):
    h = load(HEALTH, "health_under_test")
    h.CEO_HOLD = tmp_path / "CEO_HOLD.json"
    h.LEASE = tmp_path / "PC_LEASE.json"
    h.CEO_HOLD.write_text(json.dumps({"since": time.time() - 60}), encoding="utf-8")
    h.pipe_status = lambda: {"bot_alive": False, "job": None, "esc_hold": False}
    h.newest_session = lambda: ("session-1", 3, time.time() - 3600, time.time() - 7200)
    h.recent_stalls = lambda: (0, 0)
    h.free_gb = lambda: 100.0
    h.foreground_app = lambda: None
    h.window_over_game = lambda: "Dota 2"
    h.emulator_missing = lambda: False
    assert h.main() == 0
    out = capsys.readouterr().out
    assert "VERDICT: PARKED" in out and "the CEO is using this PC" in out


# --- the CEO presses his button in the middle of something else ---------------
# Each of these sets the hold from inside another command, at the moment the
# review found it was not looked at again.

def press(box):
    """What the use-PC button leaves on disk, without running ceo-on."""
    return lambda: put_hold(box)


def run_fns(box):
    return [c[1] for c in box.calls if c[0] == "run_fn"]


def test_resume_stands_down_when_pressed_during_the_game_restart(box):
    box.st.game_up = False
    box.st.hooks["restart_game"] = press(box)
    ok, why = box.originals["resume"](NIGHT_PLAN, "test")
    assert (ok, why) == (False, box.m.HOLD_WHY)
    assert "night" not in run_fns(box), "the farm started under the CEO"
    assert not box.m.RESUMING.exists()


def test_resume_stands_down_when_pressed_mid_sleep(box):
    box.st.game_up = False
    naps = []
    box.st.hooks["nap"] = lambda: naps.append(1) or (len(naps) == 10 and put_hold(box))
    ok, why = box.originals["resume"](NIGHT_PLAN, "test")
    assert (ok, why) == (False, box.m.HOLD_WHY)
    assert "night" not in run_fns(box)
    assert len(naps) == 10, "waited out the whole 45 s after the press"


def test_resume_stops_the_farm_it_started_when_pressed_mid_preflight(box):
    def started():
        box.st.status.update(job="preflight")
        put_hold(box)
    box.st.hooks["night"] = started
    ok, why = box.originals["resume"](NIGHT_PLAN, "test")
    assert (ok, why) == (False, box.m.HOLD_WHY)
    assert run_fns(box) == ["night", "bot_stop"]
    assert "esc" not in run_fns(box)


def test_resume_marks_itself_while_it_runs_and_clears_the_mark(box):
    seen = []
    box.st.hooks["night"] = lambda: seen.append(box.m.RESUMING.exists()) or \
        box.st.status.update(bot_alive=True)
    assert box.originals["resume"](NIGHT_PLAN, "test") == (True, "farming")
    assert seen == [True] and not box.m.RESUMING.exists()


def test_give_back_moves_the_plan_onto_a_hold_pressed_mid_give_back(box, capsys):
    put_lease(box)
    box.m.resume = box.originals["resume"]
    box.st.hooks["request_screen_clear"] = press(box)
    assert box.run("give-back") == 0
    out = capsys.readouterr().out
    assert "NOT restarted" in out and "DID NOT COME BACK" not in out
    assert box.m.read_lease() is None
    hold = hold_on_disk(box)
    assert hold["was_running"] is True and hold["resume"] == NIGHT_PLAN
    assert "night" not in run_fns(box)


def test_tick_moves_the_plan_onto_a_hold_pressed_mid_resume(box):
    put_lease(box, minutes_left=-1)

    def resume_then_pressed(plan, why):
        box.calls.append(("resume", plan, why))
        put_hold(box)
        return False, box.m.HOLD_WHY
    box.m.resume = resume_then_pressed
    assert box.run("tick") == 0
    assert box.m.read_lease() is None
    assert hold_on_disk(box)["resume"] == NIGHT_PLAN


@pytest.mark.parametrize("farm", [{"bot_alive": True, "champion": "champ"},
                                  {"bot_alive": False, "job": "preflight"}])
def test_tick_stops_a_farm_running_under_the_hold(box, farm):
    put_hold(box)
    box.st.status = dict(farm)
    assert box.run("tick") == 0
    assert run_fns(box) == ["bot_stop"]
    assert hold_on_disk(box)["was_running"] is True
    assert never_touched_windows(box)


def test_tick_under_the_hold_leaves_an_idle_farm_alone(box):
    put_hold(box)
    assert box.run("tick") == 0
    assert run_fns(box) == []


def test_ceo_on_stops_a_preflight_too(box, capsys):
    box.st.status = {"bot_alive": False, "job": "preflight"}
    assert box.run("ceo-on") == 0
    assert run_fns(box) == ["bot_stop"]
    assert "FARM: stopped" in capsys.readouterr().out


def test_ceo_on_stops_a_farm_that_comes_back_after_the_stop(box, capsys):
    box.st.status = {"bot_alive": True, "champion": "champ"}
    naps = []

    def comes_back():
        naps.append(1)
        if len(naps) == 2:
            box.st.status.update(bot_alive=True)
    box.st.hooks["nap"] = comes_back
    assert box.run("ceo-on") == 0
    assert run_fns(box) == ["bot_stop", "bot_stop"]
    assert "FARM: stopped" in capsys.readouterr().out


def test_ceo_on_never_undoes_a_release_pressed_while_it_asked_the_farm(box, capsys):
    box.st.status = {"bot_alive": True, "champion": "champ"}
    box.st.hooks["status"] = lambda: box.m.clear_ceo_hold()
    assert box.run("ceo-on") == 0
    assert not box.m.CEO_HOLD.exists(), "ceo-on wrote back a hold he had released"
    assert "bot_stop" not in run_fns(box)
    assert "FARM: released" in capsys.readouterr().out


def test_a_fold_never_resurrects_a_released_hold(box):
    lease = {"who": "x", "was_running": True, "resume": NIGHT_PLAN}
    assert box.m.fold_into_hold(lease, "test") is False
    assert not box.m.CEO_HOLD.exists()


def test_take_keeps_the_plan_when_it_cannot_reach_the_hold(box, capsys):
    box.st.status = {"bot_alive": True, "champion": "champ"}
    real_write = box.m.write_ceo_hold
    box.st.hooks["bot_stop"] = lambda: real_write(
        {"since": time.time(), "was_running": False, "resume": None, "bumped": None})

    def broken(_d):
        raise OSError("disk full")
    box.m.write_ceo_hold = broken
    assert box.run("take", "--who", "cto: x") == 2
    lease = box.m.read_lease()
    assert lease and lease["resume"] and box.m.remaining(lease) <= 0
    box.m.write_ceo_hold = real_write
    assert box.run("tick") == 0
    assert box.m.read_lease() is None and hold_on_disk(box)["resume"]


def test_take_finishes_when_the_hold_came_and_went_mid_take(box, capsys):
    box.st.status = {"bot_alive": True, "champion": "champ"}
    box.st.hooks["bot_stop"] = lambda: (put_hold(box), box.m.clear_ceo_hold())
    assert box.run("take", "--who", "cto: x") == 0
    assert box.m.read_lease()["who"] == "cto: x"


def test_a_stale_hold_lock_is_broken_not_waited_on(box, capsys):
    box.mp.mkdir(parents=True, exist_ok=True)
    box.m.CEO_HOLD_LOCK.write_text("", encoding="utf-8")
    old = time.time() - 60
    os.utime(box.m.CEO_HOLD_LOCK, (old, old))
    t0 = time.time()
    assert box.run("ceo-on") == 0
    assert time.time() - t0 < 5
    assert box.m.CEO_HOLD.exists() and not box.m.CEO_HOLD_LOCK.exists()


def test_revive_stands_down_while_pc_lease_is_resuming(tmp_path):
    r = load(REVIVE, "revive_under_test")
    r.CEO_HOLD = tmp_path / "CEO_HOLD.json"
    r.RESUMING = tmp_path / "FARM_RESUMING.json"
    r.LOG = tmp_path / "revive.log"
    seen = []
    r.pipe = lambda *a, **k: seen.append(a)
    r.RESUMING.write_text("{}", encoding="utf-8")
    assert r.main() == 0 and seen == []


def revive_box(tmp_path, monkeypatch):
    r = load(REVIVE, "revive_under_test")
    r.CEO_HOLD = tmp_path / "CEO_HOLD.json"
    r.RESUMING = tmp_path / "FARM_RESUMING.json"
    r.LOG = tmp_path / "revive.log"
    r.STATE = tmp_path / "revive_state.json"
    r.LEASE = tmp_path / "PC_LEASE.json"
    r.foreign_window_over_game = lambda: None
    # A clock that a sleep moves on: revive's waits are loops on time.time(),
    # and code that never looks at the hold again must run out, not hang.
    clock = [time.time()]
    fake = SimpleNamespace(**{k: getattr(time, k) for k in dir(time) if not k.startswith("_")})
    fake.time = lambda: clock[0]
    fake.sleep = lambda sec: clock.__setitem__(0, clock[0] + sec)
    monkeypatch.setattr(r, "time", fake)
    return r


def test_revive_stands_down_when_pressed_during_its_game_restart(tmp_path, monkeypatch):
    r = revive_box(tmp_path, monkeypatch)
    sent = []

    def fake_pipe(method, path, body=None, timeout=90):
        if body:
            sent.append(body["fn"])
            if body["fn"] == "restart_game":
                r.CEO_HOLD.write_text("{}", encoding="utf-8")
        return {"ok": True} if body else {"bot_alive": False, "job": None}
    r.pipe = fake_pipe
    r.state_set({"foreign_since": time.time() - 3600, "foreign_app": "com.android.chrome"})
    assert r.clear_foreign_app("com.android.chrome") == 0
    assert sent == ["bot_stop", "restart_game"], "started the farm under the CEO"


def test_revive_stops_its_own_start_when_pressed_mid_start(tmp_path, monkeypatch):
    r = revive_box(tmp_path, monkeypatch)
    sent = []

    def fake_pipe(method, path, body=None, timeout=90):
        if body:
            sent.append(body["fn"])
            if body["fn"] == "night":
                r.CEO_HOLD.write_text("{}", encoding="utf-8")
            return {"ok": True}
        return {"bot_alive": False, "job": "preflight"}
    r.pipe = fake_pipe
    assert r.start_farm("test") is False
    assert sent == ["night", "bot_stop"]


def test_revive_minimiser_refuses_under_the_hold(tmp_path, monkeypatch):
    r = revive_box(tmp_path, monkeypatch)
    r.CEO_HOLD.write_text("{}", encoding="utf-8")
    assert r.minimise_foreign_windows().startswith("REFUSED")


def health_box(tmp_path, status):
    h = load(HEALTH, "health_under_test")
    h.CEO_HOLD = tmp_path / "CEO_HOLD.json"
    h.LEASE = tmp_path / "PC_LEASE.json"
    h.CEO_HOLD.write_text(json.dumps({"since": time.time() - 60}), encoding="utf-8")
    h.pipe_status = lambda: status
    h.newest_session = lambda: ("session-1", 3, time.time() - 60, time.time() - 7200)
    h.recent_stalls = lambda: (0, 0)
    h.free_gb = lambda: 100.0
    h.foreground_app = lambda: None
    h.window_over_game = lambda: None
    h.emulator_missing = lambda: False
    return h


@pytest.mark.parametrize("status", [{"bot_alive": True, "job": "night", "esc_hold": False},
                                    {"bot_alive": False, "job": "preflight", "esc_hold": False}])
def test_health_names_a_farm_running_under_the_hold(tmp_path, capsys, status):
    assert health_box(tmp_path, status).main() == 1
    assert "VERDICT: RUNNING-UNDER-HOLD" in capsys.readouterr().out


# --- files and answers that are not what they should be ------------------------

def test_a_hold_file_that_is_not_utf8_counts_as_held(box):
    box.mp.mkdir(parents=True, exist_ok=True)
    box.m.CEO_HOLD.write_bytes(b"\xff\xfe{\x00")
    hold = box.m.read_ceo_hold()
    assert hold is not None and hold.get("corrupt")


def test_ceo_on_over_a_non_utf8_hold_marks_the_plan_unknown(box, capsys):
    box.mp.mkdir(parents=True, exist_ok=True)
    box.m.CEO_HOLD.write_bytes(b"\xff\xfe")
    assert box.run("ceo-on") == 0
    assert hold_on_disk(box)["plan_unknown"] is True
    assert box.run("ceo-off") == 0
    assert "FARM: unknown" in capsys.readouterr().out


@pytest.mark.parametrize("content", ["[]", '"x"', "7"])
def test_a_lease_file_that_is_not_an_object_reads_as_none(box, content):
    box.mp.mkdir(parents=True, exist_ok=True)
    box.m.LEASE.write_text(content, encoding="utf-8")
    assert box.m.read_lease() is None
    assert box.run("status") == 0


@pytest.mark.parametrize("content", ["[]", '{"expires_at": "noon"}'])
def test_revive_and_health_read_a_broken_lease_as_no_lease(tmp_path, content):
    r = load(REVIVE, "revive_under_test")
    r.LEASE = tmp_path / "PC_LEASE.json"
    r.LEASE.write_text(content, encoding="utf-8")
    r.CEO_HOLD = tmp_path / "CEO_HOLD.json"
    r.RESUMING = tmp_path / "FARM_RESUMING.json"
    r.LOG = tmp_path / "revive.log"
    r.STATE = tmp_path / "revive_state.json"
    r.pipe = lambda *a, **k: {"bot_alive": False, "job": None, "esc_hold": False}
    r.last_round_age_s = lambda: 60.0          # just stopped: no start either way
    assert r.main() == 0
    h = load(HEALTH, "health_under_test")
    h.LEASE = r.LEASE
    assert h.lease_now() is None


def test_a_lease_expiry_that_is_not_a_number_reads_as_expired(box):
    assert box.m.remaining({"expires_at": "noon"}) < 0
    assert box.m.remaining({"expires_at": None}) < 0


def test_pipe_swallows_a_truncated_http_answer(box, monkeypatch):
    import http.client
    m = load(PC_LEASE, "pc_lease_pipe_test")
    m.TOKEN = box.mp / "pipe_token"
    box.mp.mkdir(parents=True, exist_ok=True)
    m.TOKEN.write_text("t", encoding="utf-8")

    def boom(*a, **k):
        raise http.client.IncompleteRead(b"{")
    monkeypatch.setattr(m.urllib.request, "urlopen", boom)
    assert m.pipe("GET", "/status") is None


def test_ceo_on_says_the_lock_is_on_before_anything_can_fail(box, capsys):
    def broken():
        raise RuntimeError("pipe exploded")
    box.m.status = broken
    assert box.run("ceo-on") == 1
    out = capsys.readouterr().out
    assert out.startswith("PC: CEO")
    assert "WARNING: the lock is on" in out
    assert box.m.CEO_HOLD.exists()


def test_ceo_off_with_a_mangled_plan_still_brings_the_farm_back(box, capsys):
    put_hold(box, was_running=True, resume="garbage")
    assert box.run("ceo-off") == 0
    assert [c[1] for c in box.calls if c[0] == "resume"] == [
        {"fn": "night", "args": {"rounds": 60}}]


def test_the_real_resume_runs_night_for_a_plan_with_no_fn(box):
    box.st.hooks["night"] = lambda: box.st.status.update(bot_alive=True)
    assert box.originals["resume"]({"args": {}}, "test") == (True, "farming")
    assert run_fns(box) == ["night"]


def test_a_resume_plan_survives_an_ab_status_with_holes(box):
    plan = box.m.capture_resume_plan({"bot_alive": True, "ab": {"rounds": None}})
    assert plan["fn"] == "ab" and plan["args"]["rounds"] == 8


# --- the desktop buttons ---------------------------------------------------------

def test_cmd_buttons_are_pure_ascii_and_call_the_right_mode():
    for path, mode in ((ON_CMD, "on"), (OFF_CMD, "off")):
        raw = path.read_bytes()
        assert raw.isascii(), f"{path.name}: cmd.exe reads batch files in the OEM code page"
        text = raw.decode("ascii")
        commands = [ln for ln in text.lower().splitlines() if not ln.startswith("rem ")]
        assert not any("pause" in ln for ln in commands), "the window must not linger"
        assert re.search(r'-File "C:\\mooniex\\pclease\\ceo_button\.ps1" -Mode ' + mode + r"\r?$",
                         text, re.M)


def test_ps1_has_a_utf8_bom_and_runs_the_deployed_lease():
    raw = PS1.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "Windows PowerShell 5.1 reads a BOM-less script as ANSI"
    text = raw.decode("utf-8-sig")
    assert r"C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe" in text
    assert r"C:\mooniex\pclease\pc_lease.py" in text
    assert "'ceo-on'" in text and "'ceo-off'" in text
    # the prefixes it parses must be the ones pc_lease.py prints
    src = PC_LEASE.read_text(encoding="utf-8")
    for prefix in ("PC: CEO", "PC: released", "BUMPED: ", "NO HOLD:", "FARM: "):
        assert prefix in text and prefix in src
    for state in ("back", "handed", "off", "unknown", "failed", "stopped"):
        assert f"'{state}'" in text and f"FARM: {state} " in src


# --- the one-way deploy (scripts/lib/winbox_deploy.sh) --------------------------
# Review blocker, 2026-10-09: the wrappers md5-compared and scp'd the CALLER's
# copy, so the first call from any stale checkout put a pc_lease.py that knows
# nothing of the hold back on the box. These run the real bash helper against a
# fake `ssh` / `scp` pair that keeps "the box" in a temp dir, and fake Windows'
# read-only flag with chmod 444 (a write-open then fails, as on Windows).

import subprocess  # noqa: E402
import textwrap    # noqa: E402

DEPLOY_LIB = ROOT / "scripts" / "lib" / "winbox_deploy.sh"

FAKE_SSH = r'''#!/usr/bin/env python3
import base64, hashlib, os, re, stat, sys
box = os.environ["FAKE_BOX"]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write("ssh " + sys.argv[-1][:200] + "\n")
cmd = sys.argv[-1]
m = re.search(r"-EncodedCommand (\S+)", cmd)
if not m:
    sys.exit(int(os.environ.get("FAKE_RC", "0")))
if os.environ.get("FAKE_SSH_DOWN"):
    sys.exit(255)
ps = base64.b64decode(m.group(1)).decode("utf-16-le")
remote = re.search(r"\$p = '([^']+)'", ps).group(1)
path = os.path.join(box, remote.rsplit("\\", 1)[-1])
def md5():
    return hashlib.md5(open(path, "rb").read()).hexdigest()
if "Select-String" in ps:
    if not os.path.exists(path):
        print("none none -"); sys.exit(0)
    name = re.search(r"\^\[# \]\*(\w+)", ps).group(1)
    v = re.search(r"(?m)^[# ]*" + name + r"\s*=\s*(\d+)", open(path).read())
    os.chmod(path, 0o444)
    print(f"{v.group(1) if v else 0} {md5()} ro"); sys.exit(0)
if "IsReadOnly = $false" in ps:
    if os.path.exists(path):
        os.chmod(path, 0o644)
    sys.exit(0)
if "IsReadOnly = $true" in ps:
    os.chmod(path, 0o444)
    print(md5()); sys.exit(0)
'''

FAKE_SCP = r'''#!/usr/bin/env python3
import os, shutil, sys
box = os.environ["FAKE_BOX"]
src, dst = sys.argv[-2], sys.argv[-1]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(f"scp {src} {dst}\n")
target = os.path.join(box, dst.split(":", 1)[1].rsplit("\\", 1)[-1])
try:
    shutil.copyfile(src, target)
except PermissionError:
    print(f"scp: {dst}: Permission denied", file=sys.stderr); sys.exit(1)
'''


@pytest.fixture
def fakebox(tmp_path):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name, body in (("ssh", FAKE_SSH), ("scp", FAKE_SCP)):
        (bin_ / name).write_text(body)
        (bin_ / name).chmod(0o755)
    box = tmp_path / "box"
    box.mkdir()
    log = tmp_path / "calls.log"
    log.write_text("")
    env = {**__import__("os").environ, "PATH": f"{bin_}:{__import__('os').environ['PATH']}",
           "FAKE_BOX": str(box), "FAKE_LOG": str(log), "WINBOX_HOST": "winbox"}

    def deploy(src, version_name="LEASE_VERSION", remote=r"C:\mooniex\pclease\pc_lease.py",
               **extra):
        script = (f'set -euo pipefail; HOST=winbox; . "{DEPLOY_LIB}"; '
                  f'winbox_deploy "{src}" \'{remote}\' {version_name}')
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                              env={**env, **extra}, timeout=60)

    def scps():
        return [ln for ln in log.read_text().splitlines() if ln.startswith("scp ")]

    return SimpleNamespace(box=box, env=env, deploy=deploy, scps=scps, tmp=tmp_path,
                           on_box=lambda name="pc_lease.py": box / name)


def version_file(tmp, name, version, body="print('x')\n"):
    p = tmp / name
    p.write_text(f"LEASE_VERSION = {version}\n{body}")
    return p


def test_deploy_puts_a_first_copy_on_the_box_read_only(fakebox):
    src = version_file(fakebox.tmp, "pc_lease.py", 1)
    r = fakebox.deploy(src)
    assert r.returncode == 0, r.stderr
    assert fakebox.on_box().read_bytes() == src.read_bytes()
    assert not (fakebox.on_box().stat().st_mode & 0o200), "the box copy must be left read-only"
    assert r.stdout == ""


def test_deploy_never_goes_backwards(fakebox):
    fakebox.on_box().write_text("LEASE_VERSION = 2\nprint('new')\n")
    stale = version_file(fakebox.tmp, "pc_lease.py", 1, body="print('old')\n")
    r = fakebox.deploy(stale)
    assert r.returncode == 0
    assert fakebox.scps() == [], "a stale checkout must not copy anything"
    assert fakebox.on_box().read_text().endswith("print('new')\n")
    assert "stale" in r.stderr and r.stdout == ""


def test_deploy_an_unversioned_local_copy_never_replaces_a_versioned_box(fakebox):
    fakebox.on_box().write_text("LEASE_VERSION = 1\nprint('hold-aware')\n")
    old = fakebox.tmp / "pc_lease.py"
    old.write_text("print('pre-hold')\n")                    # what main had
    assert fakebox.deploy(old).returncode == 0
    assert fakebox.scps() == []


def test_deploy_moves_forward(fakebox):
    fakebox.on_box().write_text("print('pre-hold, unversioned')\n")
    src = version_file(fakebox.tmp, "pc_lease.py", 1)
    r = fakebox.deploy(src)
    assert r.returncode == 0, r.stderr
    assert fakebox.on_box().read_bytes() == src.read_bytes()


def test_deploy_same_version_different_content_keeps_the_box_copy(fakebox):
    fakebox.on_box().write_text("LEASE_VERSION = 1\nprint('box')\n")
    src = version_file(fakebox.tmp, "pc_lease.py", 1, body="print('local edit')\n")
    r = fakebox.deploy(src)
    assert fakebox.scps() == []
    assert "bump LEASE_VERSION" in r.stderr


def test_deploy_does_nothing_blind_when_the_box_cannot_be_read(fakebox):
    src = version_file(fakebox.tmp, "pc_lease.py", 5)
    r = fakebox.deploy(src, FAKE_SSH_DOWN="1")
    assert r.returncode == 0 and fakebox.scps() == []
    assert "not deploying" in r.stderr


def test_an_old_wrapper_cannot_overwrite_the_read_only_box_copy(fakebox):
    """What a pre-fix pc-lease.sh does on an md5 mismatch: a bare scp. It fails."""
    src = version_file(fakebox.tmp, "pc_lease.py", 1)
    fakebox.deploy(src)
    old = fakebox.tmp / "old_pc_lease.py"
    old.write_text("print('pre-hold')\n")
    r = subprocess.run(["scp", "-q", str(old), r"winbox:C:\mooniex\pclease\pc_lease.py"],
                       capture_output=True, text=True, env=fakebox.env)
    assert r.returncode != 0
    assert fakebox.on_box().read_bytes() == src.read_bytes()


def test_pc_lease_wrapper_gate_keeps_stdout_empty_when_the_checkout_is_stale(fakebox):
    fakebox.on_box().write_text("LEASE_VERSION = 999\nprint('newer')\n")
    r = subprocess.run(["bash", str(ROOT / "scripts" / "pc-lease.sh"), "gate"],
                       capture_output=True, text=True, env=fakebox.env, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""
    assert "stale" in r.stderr
    assert fakebox.scps() == []


@pytest.mark.parametrize("path,name", [(PC_LEASE, "LEASE_VERSION"),
                                       (HEALTH, "HEALTH_VERSION"),
                                       (REVIVE, "REVIVE_VERSION")])
def test_every_deployed_file_carries_its_version_line(path, name):
    assert re.search(rf"(?m)^{name} = \d+$", path.read_text(encoding="utf-8"))
