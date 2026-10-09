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
    m.FOREGROUND = mp / "foreground.json"

    calls: list[tuple] = []
    st = SimpleNamespace(status={"bot_alive": False}, stops=True, resume_ok=True)

    def fake_status():
        calls.append(("status",))
        return None if st.status is None else dict(st.status)

    def fake_run_fn(fn, args=None):
        calls.append(("run_fn", fn, args))
        if fn == "bot_stop" and st.stops and st.status is not None:
            st.status["bot_alive"] = False
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
    m.request_screen_clear = lambda: calls.append(("request_screen_clear",))
    m.minimise_foreign_windows = lambda: calls.append(("minimise",)) or "Chrome"
    m.resume = fake_resume
    m.wait_until_stopped = fake_wait_until_stopped
    m.record_foreground = lambda: calls.append(("record_foreground",))

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
