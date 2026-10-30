"""tools/escalation_watch.py, W2: the re-wake ladder (design C3), letters to live owner
boxes (C4) and the owner-relay tick wired into main()."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from lib import mailbox
from tools import escalation_watch as ew
from tools import owner_relay as orl

NOW = 1_800_000_000.0
MIN = 60
RULE = "─" * 50
READY = f"some output\n{RULE}\n❯\xa0\n{RULE}\n  ? for shortcuts\n"
PH, PH_SID = "project_head-3bea1120", "3bea1120"


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


@pytest.fixture
def box(tmp_path, monkeypatch):
    locks = tmp_path / "locks"
    locks.mkdir()
    for mod in (ew, orl):
        monkeypatch.setattr(mod, "LOCKS_DIR", locks)
    monkeypatch.setattr(orl, "STATE_PATH", tmp_path / "owner_relay.json")
    monkeypatch.setattr(orl, "MODE_PATH", tmp_path / "owner_relay.mode")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    (locks / f"{PH}.lock").write_text("1\n")
    (locks / f"{PH}.spawned_by").write_text("cxo:cto:c34459eb\n")     # that CTO session ended
    (locks / "cto-active").write_text("fresh\n")
    (locks / "cto-fresh.lock").write_text("1\n")

    class Box:
        path = tmp_path
        sent, woke, wake_result = [], [], {"woke": False, "reason": "no live session reached"}
        sessions = [{"box": PH, "role": "project_head", "sid": PH_SID, "status": "idle", "tmux": PH},
                    {"box": "cto-fresh", "role": "cto", "sid": "fresh", "status": "running", "tmux": "cto-fresh"}]

        def letter(self, to, body, t, name="a"):
            d = tmp_path / "inbox" / to
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"{name}.json"
            p.write_text(json.dumps({"from": "cto-fresh", "body": body, "sent_at": iso(t)}, indent=2))
            os.utime(p, (t, t))
            return p

        def send(self, role, sid, body, fr, fs, **kw):
            self.sent.append((f"{role}-{sid}", body))

        def wake(self, b, label):
            self.woke.append(b)
            return dict(self.wake_result, box=b)

        def rewake(self, now, state, mode="live", budget=None):
            return ew.rewake(self.sessions, now, state, mode=mode, panes=lambda t: READY, wake=self.wake,
                             send=self.send, budget=budget, tier_of=lambda b: "critical")

    b = Box()
    b.sent, b.woke = [], []
    b.sessions = [dict(s) for s in Box.sessions]
    return b


# --- C3: the ladder ------------------------------------------------------------------

def test_rewake_follows_5_15_45_and_stops_at_three_then_one_owner_letter(box):
    box.letter(PH, "blocker · urgent · do the thing", NOW)
    st = orl.load_state("live")
    calls = []
    for m in (4, 5, 10, 15, 30, 45, 50, 60, 120):
        box.rewake(NOW + m * MIN, st)
        calls.append((m, len(box.woke), len(box.sent)))
    assert calls == [(4, 0, 0), (5, 1, 0), (10, 1, 0), (15, 2, 0), (30, 2, 0), (45, 3, 0),
                     (50, 3, 1), (60, 3, 1), (120, 3, 1)]
    to, body = box.sent[0]
    assert to == "cto-fresh" and body.startswith("blocker · urgent ·") and PH in body   # the live box, not c34459eb


def test_the_ladder_is_scaled_by_the_budget_factor(box):
    box.letter(PH, "ask · normal · which one?", NOW)
    st = orl.load_state("live")
    seen = []
    for m in (5, 9, 10, 29, 30, 89, 90):
        over = {"ts": iso(NOW + m * MIN), "rows": {"claude": {"state": "over"}}}        # x2
        box.rewake(NOW + m * MIN, st, budget=over)
        seen.append(len(box.woke))
    assert seen == [0, 0, 1, 1, 2, 2, 3]


def test_a_low_tier_box_is_never_rewoken(box):
    box.letter(PH, "blocker · urgent · x", NOW)
    st = orl.load_state("live")
    ew.rewake(box.sessions, NOW + 60 * MIN, st, mode="live", panes=lambda t: READY, wake=box.wake,
              send=box.send, tier_of=lambda b: "low")
    assert box.woke == []


def test_a_busy_session_is_not_rewoken_and_spends_no_try(box):
    box.letter(PH, "blocker · urgent · x", NOW)
    st = orl.load_state("live")
    box.sessions[0]["status"] = "running"
    box.rewake(NOW + 6 * MIN, st)
    assert box.woke == [] and st["rewake"][PH]["tries"] == 0
    box.sessions[0]["status"] = "idle"
    box.rewake(NOW + 7 * MIN, st)
    assert box.woke == [PH] and st["rewake"][PH]["tries"] == 1


def test_a_fyi_or_report_letter_never_wakes(box):
    box.letter(PH, "fyi · normal · for your eyes", NOW, "a")
    box.letter(PH, "report · normal · done", NOW, "b")
    st = orl.load_state("live")
    for m in (5, 15, 45, 60):
        box.rewake(NOW + m * MIN, st)
    assert box.woke == [] and box.sent == []


def test_the_coo_and_a_parked_ph_are_never_rewoken(box):
    (box.path / "locks" / f"{PH}.lock").unlink()
    (box.path / "locks" / f"{PH}.project.parked").write_text("x\n")
    box.sessions.append({"box": "coo-1852c70e", "role": "coo", "sid": "1852c70e", "status": "idle", "tmux": "c"})
    box.letter(PH, "blocker · urgent · x", NOW)
    box.letter("coo-1852c70e", "blocker · urgent · y", NOW)
    st = orl.load_state("live")
    for m in (5, 15, 45, 60):
        box.rewake(NOW + m * MIN, st)
    assert box.woke == [] and box.sent == []


def test_a_successful_wake_that_drains_the_box_resets_the_ladder(box):
    p = box.letter(PH, "blocker · urgent · x", NOW)
    box.wake_result = {"woke": True, "reason": "woke"}
    st = orl.load_state("live")
    box.rewake(NOW + 5 * MIN, st)
    p.unlink()                                       # the hook drained it
    box.rewake(NOW + 10 * MIN, st)
    assert box.woke == [PH] and PH not in st["rewake"]
    assert st["wakes"][PH][orl.thai_day(NOW + 5 * MIN)] == 1


def test_a_dead_ph_with_unread_letters_tells_its_owner_once_per_episode(box):
    box.sessions = [s for s in box.sessions if s["box"] != PH]      # lock present, no session
    box.letter(PH, "blocker · urgent · x", NOW)
    st = orl.load_state("live")
    box.rewake(NOW + 14 * MIN, st)
    assert box.sent == []
    box.rewake(NOW + 16 * MIN, st)
    box.rewake(NOW + 30 * MIN, st)
    assert [to for to, _ in box.sent] == ["cto-fresh"] and "no live session" in box.sent[0][1]
    assert "spawn-ph.sh --resume 3bea1120" in box.sent[0][1]


def test_dry_mode_prints_the_ladder_and_sends_nothing(box):
    box.letter(PH, "blocker · urgent · x", NOW)
    st = orl.load_state("dry")
    out = []
    for m in (5, 15, 45, 50):
        out += box.rewake(NOW + m * MIN, st, mode="dry")
    assert box.woke == [] and box.sent == []
    assert out == [f"would rewake {PH} try 1", f"would rewake {PH} try 2", f"would rewake {PH} try 3",
                   f"would send cto-fresh <- blocker rewake {PH}"]


# --- C4: live owners -----------------------------------------------------------------

def test_owner_box_falls_back_to_the_role_active_box_when_spawned_by_is_dead(box):
    assert ew.owner_box(PH_SID) == "cto-fresh"
    (box.path / "locks" / "cto-c34459eb.lock").write_text("1\n")
    assert ew.owner_box(PH_SID) == "cto-c34459eb"


def test_live_c_levels_come_from_the_active_pointers(box):
    (box.path / "locks" / "cmo-active").write_text("e785343f\n")
    (box.path / "locks" / "cmo-e785343f.lock").write_text("1\n")
    (box.path / "locks" / "coo-active").write_text("1852c70e\n")          # no lock: not live
    assert ew.live_c_levels() == ["cmo-e785343f", "cto-fresh"]


def test_an_idle_ph_with_open_work_reaches_its_lane_c_level_not_only_the_coo(box, monkeypatch):
    monkeypatch.setattr(ew, "coo_box", lambda: "coo-1852c70e")
    f = {"kind": "idle", "box": PH, "subject": "idle:x", "text": "idle 40 min", "work": True}
    assert ew.recipients(f, []) == ["coo-1852c70e", "cto-fresh"]
    assert ew.recipients(dict(f, work=False), []) == ["coo-1852c70e"]


def test_a_blocker_held_by_a_dead_c_level_box_goes_to_its_live_successor(box, monkeypatch):
    monkeypatch.setattr(ew, "coo_box", lambda: "coo-1852c70e")
    f = {"kind": "blocker", "box": "cto-c34459eb", "ph": PH, "subject": "b", "text": "holds"}
    assert ew.recipients(f, []) == ["coo-1852c70e", "cto-fresh"]


# --- wiring --------------------------------------------------------------------------

class Hub:
    def __init__(self):
        self.ev = [{"id": 7, "task_id": "task-210cf323", "actor": "watchdog", "kind": "status_stalled",
                    "payload": "{}", "ts": iso(NOW - 600)}]

    def events(self, cursor, since):
        return [e for e in self.ev if cursor is None or e["id"] > cursor]

    def tasks(self, ids):
        return {"task-210cf323": {"id": "task-210cf323", "status": "stalled", "owner_cto": PH_SID,
                                  "owner_role": "project_head", "delegate_log": "silent 31 min"}}

    def running(self, host):
        return []


def test_owner_tick_letters_and_wakes_live_and_saves_its_state(box, monkeypatch):
    orl.MODE_PATH.write_text("live\n")
    monkeypatch.setattr(ew, "read_meta", lambda p: [])
    box.wake_result = {"woke": True, "reason": "woke"}
    out = ew.owner_tick(box.sessions, NOW, None, hub=Hub(), panes=lambda t: READY, wake=box.wake, send=box.send)
    assert [to for to, _ in box.sent] == [PH] and "task-210cf323 stalled" in box.sent[0][1]
    assert box.woke == [PH] and any(o.startswith("[live] sent") for o in out)
    assert json.loads(orl.STATE_PATH.read_text())["cursor"] == 7
    ew.owner_tick(box.sessions, NOW + 300, None, hub=Hub(), panes=lambda t: READY, wake=box.wake, send=box.send)
    assert len(box.sent) == 1


def test_a_live_c_level_box_with_no_session_record_is_woken_by_its_screen(box, monkeypatch):
    """CTO Main drains cto-fresh; its session record names another id."""
    orl.MODE_PATH.write_text("live\n")
    monkeypatch.setattr(ew, "read_meta", lambda p: [])
    box.wake_result = {"woke": True, "reason": "woke"}
    hub = Hub()
    hub.tasks = lambda ids: {"task-210cf323": {"id": "task-210cf323", "status": "stalled", "owner_cto": "fresh",
                                               "owner_role": "cto", "delegate_log": ""}}
    sessions = [s for s in box.sessions if s["box"] != "cto-fresh"]
    ew.owner_tick(sessions, NOW, None, hub=hub, panes=lambda t: READY, wake=box.wake, send=box.send)
    assert [to for to, _ in box.sent] == ["cto-fresh"] and box.woke == ["cto-fresh"]
    hub.ev.append({"id": 8, "task_id": "task-210cf323", "actor": "watchdog", "kind": "status_stalled",
                   "payload": "{}", "ts": iso(NOW + 200)})
    busy = "✻ Thinking… (esc to interrupt)\n" + READY
    from lib import pane_screen
    assert pane_screen.pane_busy(busy) and not pane_screen.prompt_ready(busy)
    out = ew.owner_tick(sessions, NOW + 300, None, hub=hub, panes=lambda t: busy, wake=box.wake, send=box.send)
    assert len(box.sent) == 2 and box.woke == ["cto-fresh"]    # a running turn on screen: letter, no wake
    assert any("wake held: screen not ready" in o for o in out)


def test_owner_tick_is_off_with_the_mode_file_and_never_raises(box, monkeypatch):
    orl.MODE_PATH.write_text("off\n")
    assert ew.owner_tick(box.sessions, NOW, None, hub=Hub(), wake=box.wake, send=box.send) == \
        ["owner-relay off (state/owner_relay.mode)"]
    orl.MODE_PATH.write_text("live\n")
    monkeypatch.setattr(orl, "run", lambda *a, **k: 1 / 0)
    out = ew.owner_tick(box.sessions, NOW, None, hub=Hub(), wake=box.wake, send=box.send)
    assert out[0].startswith("note owner relay skipped (ZeroDivisionError")
    assert box.sent == []


def test_main_runs_the_owner_tick_once_under_nudge(box, monkeypatch):
    from lib import config
    monkeypatch.setattr(config, "self_host", lambda: "contabo")
    monkeypatch.setattr(ew.ls, "_open_hub", lambda: (_ for _ in ()).throw(RuntimeError("no hub")))
    monkeypatch.setattr(ew, "local_sessions", lambda host: [])
    monkeypatch.setattr(ew, "question_times", lambda: {})
    monkeypatch.setattr(ew, "read_meta", lambda p: [])
    monkeypatch.setattr(ew, "nudge", lambda *a, **k: [])
    ticks = []
    monkeypatch.setattr(ew, "owner_tick", lambda sessions, now, budget: ticks.append(now) or ["x"])
    assert ew.main(["--nudge"]) == 0 and len(ticks) == 1
    assert ew.main([]) == 0 and len(ticks) == 1          # a dry scan never runs it
