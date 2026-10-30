"""tools/owner_relay.py (W2, design C2): task events become owner letters, by the
token rules of the brief (one letter per box per tick, fyi never wakes, no wake into a
busy or parked session, 12 wakes per box per Thai day, then an hourly batch)."""
from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lib import mailbox
from tools import owner_relay as orl
from tools import wake_audit

NOW = 1_800_000_000.0
RULE = "─" * 50
READY = f"some output\n{RULE}\n❯\xa0\n{RULE}\n  ? for shortcuts\n"     # an empty input box
DRAFT = f"some output\n{RULE}\n❯ half a sentence\n{RULE}\n"
PH, PH_SID = "project_head-3bea1120", "3bea1120"


@pytest.mark.parametrize("suffix", ["lock", "project.parked", "spawned_by"])
def test_lock_file_hardening(tmp_path, monkeypatch, suffix):
    monkeypatch.setattr(orl, "LOCKS_DIR", tmp_path)
    p = tmp_path / f"{PH}.{suffix}"
    p.write_text("1\n")
    p.chmod(0o644)
    assert orl._is_ph_sid(PH_SID)
    p.chmod(0o664)
    assert not orl._is_ph_sid(PH_SID)
    assert not orl.has_lock(PH) and not orl.parked(PH)
    p.chmod(0o644)
    os.link(p, tmp_path / "second")
    assert not orl._is_ph_sid(PH_SID)


@pytest.mark.parametrize("raw", [b"{", b"", b"[]", b"\xff"])
def test_state_parse_hardening(tmp_path, raw):
    p = tmp_path / "state.json"
    p.write_bytes(raw)
    with pytest.raises(orl.StateUnusable):
        orl.load_state("live", p)


def test_state_read_hardening(tmp_path):
    p = tmp_path / "state.json"
    assert orl.load_state("live", p) == orl._fresh("live")
    p.write_text("{}")
    p.chmod(0o664)
    with pytest.raises(orl.StateUnusable):
        orl.load_state("live", p)


def test_lock_directory_hardening(tmp_path):
    directory = tmp_path / "locks"
    directory.mkdir()
    p = directory / "cto-fresh.lock"
    p.write_text("1")
    alias = tmp_path / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    assert orl._ours(p)
    assert not orl._ours(alias / p.name)


def test_hub_running_identifier_hardening(monkeypatch):
    from contextlib import nullcontext
    from lib import db

    class Conn:
        def execute(self, *args):
            return self

        def fetchall(self):
            return [{"id": tid} for tid in ("task-12345678", "../task-12345678", "task-12345678\n", None)]

    monkeypatch.setattr(db, "get_conn", lambda **kwargs: nullcontext(Conn()))
    assert orl.Hub().running("contabo") == [{"id": "task-12345678"}]


@pytest.mark.parametrize("key", ["wakes", "last_wake", "rewake", "dead_eps", "seen", "queue_seen", "pending"])
def test_state_size_hardening(tmp_path, monkeypatch, key):
    monkeypatch.setattr(orl, "STATE_READ_MAX", 512)
    st = orl._fresh("live")
    value = {"2026-10-30": 1} if key == "wakes" else ["x" * 80]
    st[key] = {f"box-{i}": value for i in range(200)}
    p = tmp_path / "state.json"
    orl.save_state(st, p)
    assert p.stat().st_size <= orl.STATE_READ_MAX
    assert len(orl.load_state("live", p)[key]) < 200
    assert len(st[key]) == 200
    st["cursor"] = "x" * 1000
    with pytest.raises(orl.StateUnusable):
        orl.save_state(st, p)


def test_identifier_entry_hardening(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid identifier reached filesystem")
    monkeypatch.setattr(orl.ls, "read_lock", unexpected)
    monkeypatch.setattr(mailbox, "_open_dir", unexpected)
    assert orl.active_box("../cto") is None
    assert orl.ph_owner("../12345678") is None
    assert orl.unread("../cto-fresh") == []


def test_collect_identifier_hardening(org):
    bad = "../task-12345678"
    row = org.hub.task(bad, "in_progress", _state="dead")
    org.hub.runs = [row]
    org.hub.event(bad, "fields_set", payload={"last_checkpoint": "BLOCKED"})
    inspected = []
    lines = orl.collect(NOW, orl._fresh("live"), hub=org.hub, live=set(), meta=(),
                        queues=[], notes=[], inspect=lambda r: inspected.append(r) or "dead")
    assert lines == [] and inspected == []


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


class FakeHub:
    def __init__(self):
        self.ev, self.rows, self.runs, self.calls = [], {}, [], []
        self.down = False

    def task(self, tid, status, owner=PH_SID, role="project_head", **kw):
        self.rows[tid] = {"id": tid, "status": status, "owner_cto": owner, "owner_role": role,
                          "delegate_log": kw.pop("log", ""), **kw}
        return self.rows[tid]

    def event(self, tid, kind, actor="branch_poller", t=NOW - 60, payload=None):
        self.ev.append({"id": len(self.ev) + 100, "task_id": tid, "actor": actor, "kind": kind,
                        "payload": json.dumps(payload or {}), "ts": iso(t)})

    def events(self, cursor, since):
        if self.down:
            raise RuntimeError("hub down")
        self.calls.append((cursor, since))
        return [e for e in self.ev if (e["id"] > cursor if cursor is not None else e["ts"] >= since)]

    def tasks(self, ids):
        return {i: self.rows[i] for i in ids if i in self.rows}

    def running(self, host):
        return list(self.runs)


@pytest.fixture
def org(tmp_path, monkeypatch):
    locks = tmp_path / "locks"
    locks.mkdir()
    monkeypatch.setattr(orl, "LOCKS_DIR", locks)
    monkeypatch.setattr(orl, "STATE_PATH", tmp_path / "owner_relay.json")
    monkeypatch.setattr(orl, "MODE_PATH", tmp_path / "owner_relay.mode")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    (locks / f"{PH}.lock").write_text("1\n")
    (locks / f"{PH}.spawned_by").write_text("cxo:cto:c34459eb\n")     # a CTO session that ended
    (locks / "cto-active").write_text("fresh\n")
    (locks / "cto-fresh.lock").write_text("1\n")

    class Org:
        hub = FakeHub()
        sent, woke = [], []
        sessions = {PH: {"box": PH, "role": "project_head", "sid": PH_SID, "status": "idle", "tmux": PH},
                    "cto-fresh": {"box": "cto-fresh", "role": "cto", "sid": "fresh", "status": "idle",
                                  "tmux": "cto-fresh"}}
        screens: dict = {}
        path = tmp_path
        queues: list = []

        def send(self, role, sid, body, fr, fs, **kw):
            self.sent.append((f"{role}-{sid}", body))

        def wake(self, box, label):
            self.woke.append(box)
            return {"box": box, "woke": True, "reason": "woke"}

        def panes(self, target):
            return self.screens.get(target, READY)

        def tick(self, now=NOW, mode="live", meta=(), budget=None, state=None):
            st = state if state is not None else orl.load_state(mode)
            out = orl.run(now, st, mode=mode, hub=self.hub, sessions=self.sessions, panes=self.panes,
                          meta=meta, send=self.send, wake=self.wake, inspect=lambda t: t.get("_state"),
                          queues=self.queues, budget=budget, tier_of=lambda b: "normal")
            return out, st

    o = Org()
    o.hub, o.sent, o.woke, o.screens, o.queues = FakeHub(), [], [], {}, []
    return o


# --- the token rules (brief D8) ------------------------------------------------------

def test_five_events_in_one_box_in_one_tick_are_one_letter_and_one_wake(org):
    for i in range(5):
        tid = f"task-0000000{i}"
        org.hub.task(tid, "failed", log=f"exit 1 step {i}")
        org.hub.event(tid, "status_failed")
    out, _ = org.tick()
    assert len(org.sent) == 1 and org.woke == [PH]
    box, body = org.sent[0]
    assert box == PH and body.startswith("blocker · urgent ·")
    assert all(f"task-0000000{i} failed" in body for i in range(5))
    assert len(body) <= orl.LETTER_MAX
    assert any("sent project_head-3bea1120" in l and "+wake" in l for l in out)


def test_a_fyi_letter_never_wakes(org):
    org.hub.task("task-aaaaaaaa", "pending")
    org.queues = [("budget", [{"task_id": "task-aaaaaaaa", "owner_cto": PH_SID, "queued_at": iso(NOW - 60),
                               "buckets": ["codex"]}])]
    org.tick()
    assert [b for b, _ in org.sent] == [PH] and org.sent[0][1].startswith("fyi · ")
    assert org.woke == []


@pytest.mark.parametrize("status,screen", [("running", READY), ("idle", DRAFT)])
def test_a_busy_session_gets_the_letter_but_no_wake(org, status, screen):
    org.sessions[PH]["status"] = status
    org.screens[PH] = screen
    org.hub.task("task-bbbbbbbb", "stalled")
    org.hub.event("task-bbbbbbbb", "status_stalled", actor="watchdog")
    out, _ = org.tick()
    assert [b for b, _ in org.sent] == [PH] and org.woke == []
    assert any("wake held" in l for l in out)


def test_a_parked_ph_gets_no_letter_and_no_wake(org):
    (org.path / "locks" / f"{PH}.lock").unlink()
    (org.path / "locks" / f"{PH}.spawned_by").rename(org.path / "locks" / f"{PH}.spawned_by.parked")
    del org.sessions[PH]
    org.hub.task("task-cccccccc", "failed")
    org.hub.event("task-cccccccc", "status_failed")
    org.tick()
    assert org.sent == [] and org.woke == []


def test_after_twelve_wakes_in_a_thai_day_the_next_waits_for_the_hourly_batch(org):
    st = orl.load_state("live")
    st["wakes"][PH] = {orl.thai_day(NOW): orl.DAY_WAKES}
    st["last_wake"][PH] = NOW - 600
    org.hub.task("task-dddddddd", "failed")
    org.hub.event("task-dddddddd", "status_failed")
    out, st = org.tick(state=st)
    assert len(org.sent) == 1 and org.woke == []               # the 13th: letter yes, wake no
    assert any("day cap" in l for l in out)
    org.hub.task("task-eeeeeeee", "failed")
    org.hub.event("task-eeeeeeee", "status_failed", t=NOW + 2000)
    org.tick(now=NOW + 2000, state=st)
    assert org.woke == []                                       # 43 min after the last wake
    org.hub.task("task-ffffffff", "failed")
    org.hub.event("task-ffffffff", "status_failed", t=NOW + 3000)
    org.tick(now=NOW + 3000, state=st)
    assert org.woke == [PH]                                     # the hourly batch
    assert st["wakes"][PH][orl.thai_day(NOW)] == orl.DAY_WAKES + 1


def test_the_hourly_batch_waits_budget_factor_times_longer(org):
    st = orl.load_state("live")
    st["wakes"][PH] = {orl.thai_day(NOW): orl.DAY_WAKES}
    st["last_wake"][PH] = NOW - 3600
    over = {"ts": iso(NOW), "rows": {"claude": {"state": "over"}}}
    assert orl.may_wake(st, PH, NOW, tier="normal", budget=over)[0] is False       # x2 x2 = 4 h
    assert orl.may_wake(st, PH, NOW, tier="normal", budget=None)[0] is True
    assert orl.may_wake(st, PH, NOW, tier="low", budget=None)[0] is False


# --- what becomes a letter -----------------------------------------------------------

def test_a_status_the_owner_set_itself_is_not_sent_back_to_it(org):
    org.hub.task("task-11111111", "blocked_human")
    org.hub.event("task-11111111", "status_blocked_human", actor=PH)
    org.hub.task("task-22222222", "review", owner="fresh", role="cto")
    org.hub.event("task-22222222", "status_review", actor="cto")
    org.tick()
    assert org.sent == []


def test_a_review_the_worker_already_reported_is_skipped(org):
    org.hub.task("task-33333333", "review")
    org.hub.event("task-33333333", "status_review", actor="developer", t=NOW - 120)
    meta = [{"from": "developer-task-33333333", "to": PH, "kind": "report", "t": NOW - 100}]
    org.tick(meta=meta)
    assert org.sent == []
    org.hub.task("task-44444444", "review")
    org.hub.event("task-44444444", "status_review", actor="developer", t=NOW - 120)
    org.tick()
    assert len(org.sent) == 1 and org.sent[0][1].startswith("ask · normal ·") and org.woke == [PH]


def test_a_task_that_moved_on_or_a_deliberate_cancel_gets_nothing(org):
    org.hub.task("task-55555555", "in_progress")            # failed, then reopened
    org.hub.event("task-55555555", "status_failed")
    org.hub.task("task-66666666", "cancelled")
    org.hub.event("task-66666666", "status_cancelled", actor="cmo")
    org.tick()
    assert org.sent == []
    org.hub.task("task-77777777", "cancelled")
    org.hub.event("task-77777777", "status_cancelled", actor="gc_stale_tasks")
    org.tick()
    assert len(org.sent) == 1 and "task-77777777 cancelled" in org.sent[0][1]


def test_a_second_run_sends_nothing_new(org):
    org.hub.task("task-88888888", "failed")
    org.hub.event("task-88888888", "status_failed")
    _, st = org.tick()
    org.tick(state=st)
    assert len(org.sent) == 1
    assert org.hub.calls[1][0] == 100                          # the cursor moved past the event


def test_the_first_run_looks_back_eight_hours_only(org):
    org.tick()
    assert org.hub.calls[0] == (None, iso(NOW - orl.BOOTSTRAP_S))


def test_a_dead_worker_is_one_letter_and_a_suspect_one_more(org):
    row = org.hub.task("task-99999999", "in_progress", spawned_at=iso(NOW - 3600))
    org.hub.runs = [dict(row, _state="dead")]
    _, st = org.tick()
    assert len(org.sent) == 1 and "task-99999999 dead" in org.sent[0][1]
    org.tick(state=st)
    assert len(org.sent) == 1                                  # once per run of the task
    org.hub.runs = []
    org.hub.event("task-99999999", "fields_set", actor="watchdog",
                  payload={"review": json.dumps({"watchdog": "suspect"})})
    org.tick(state=st)
    org.hub.event("task-99999999", "fields_set", actor="watchdog",
                  payload={"review": json.dumps({"watchdog": "suspect"})})
    org.tick(state=st)
    assert len(org.sent) == 2 and "task-99999999 suspect" in org.sent[1][1]


def test_a_queue_entry_is_one_fyi_then_one_ask_after_twelve_hours(org):
    org.hub.task("task-abababab", "pending")
    org.queues = [("budget", [{"task_id": "task-abababab", "owner_cto": PH_SID, "queued_at": iso(NOW - 60),
                               "buckets": ["codex", "claude"]}])]
    _, st = org.tick()
    org.tick(now=NOW + 3600, state=st)
    assert len(org.sent) == 1 and "budget queue: codex,claude" in org.sent[0][1]
    org.tick(now=NOW + orl.QUEUE_LATE_S, state=st)
    assert len(org.sent) == 2 and "ask the CEO on /run" in org.sent[1][1] and org.woke == [PH]
    org.tick(now=NOW + 2 * orl.QUEUE_LATE_S, state=st)
    assert len(org.sent) == 2


def test_a_dead_ph_letters_its_owner_c_level_on_the_live_box(org):
    del org.sessions[PH]                                     # lock present, no session
    org.hub.task("task-cdcdcdcd", "failed")
    org.hub.event("task-cdcdcdcd", "status_failed")
    org.tick()
    assert [b for b, _ in org.sent] == ["cto-fresh"]          # .spawned_by names cto-c34459eb: no lock
    assert f"PH {PH} dead" in org.sent[0][1] and org.woke == ["cto-fresh"]


def test_a_c_level_owner_without_a_lock_goes_to_its_active_box_and_the_coo_never(org):
    org.hub.task("task-edededed", "failed", owner="c34459eb", role="cto")
    org.hub.event("task-edededed", "status_failed")
    org.hub.task("task-fefefefe", "failed", owner="1852c70e", role="coo")
    org.hub.event("task-fefefefe", "status_failed")
    org.tick()
    assert [b for b, _ in org.sent] == ["cto-fresh"]


def test_ten_letters_per_run_and_eight_tasks_per_letter_the_rest_next_tick(org, monkeypatch):
    for n in range(12):
        sid = f"{n:08x}"
        (org.path / "locks" / f"project_head-{sid}.lock").write_text("1\n")
        org.sessions[f"project_head-{sid}"] = {"box": f"project_head-{sid}", "role": "project_head",
                                               "sid": sid, "status": "idle", "tmux": "x"}
        org.hub.task(f"task-a{n:07x}", "failed", owner=sid)
        org.hub.event(f"task-a{n:07x}", "status_failed")
    for i in range(10):
        org.hub.task(f"task-b{i:07x}", "review")
        org.hub.event(f"task-b{i:07x}", "status_review", actor="developer", t=NOW - 3600)
    _, st = org.tick()
    assert len(org.sent) == orl.MAX_LETTERS
    ph_letter = [body for box, body in org.sent if box == PH][0]
    assert ph_letter.count("\n- ") == orl.MAX_LINES and len(ph_letter) <= orl.LETTER_MAX
    org.tick(now=NOW + 300, state=st)
    boxes = [b for b, _ in org.sent[orl.MAX_LETTERS:]]     # the oldest box went first: PH + 00..08
    assert sorted(boxes) == sorted([PH, "project_head-00000009", "project_head-0000000a",
                                    "project_head-0000000b"])
    assert [body for box, body in org.sent[orl.MAX_LETTERS:] if box == PH][0].count("\n- ") == 2


def test_a_letter_names_task_ids_and_short_reasons_and_never_runs_past_600_chars(org):
    org.hub.task("task-0a0a0a0a", "failed", log="x" * 5000 + "\x1b[31m tail ‮")
    org.hub.event("task-0a0a0a0a", "status_failed")
    org.tick()
    body = org.sent[0][1]
    assert len(body) <= orl.LETTER_MAX and "\x1b" not in body and "‮" not in body
    assert "-> reopen or re-delegate it" in body


# --- modes, state and safety ---------------------------------------------------------

def test_dry_sends_and_wakes_nothing_but_says_what_it_would_send(org):
    org.hub.task("task-12121212", "failed")
    org.hub.event("task-12121212", "status_failed")
    out, _ = org.tick(mode="dry")
    assert org.sent == [] and org.woke == []
    assert out == [f"would send {PH} <- blocker 1: task-12121212:failed"]


def test_going_live_after_a_dry_run_sends_what_dry_only_printed(org):
    org.hub.task("task-13131313", "failed")
    org.hub.event("task-13131313", "status_failed")
    _, st = org.tick(mode="dry")
    orl.save_state(st)
    org.tick(mode="live")
    assert len(org.sent) == 1


def test_the_mode_file_is_read_safely(org):
    assert orl.read_mode() == "dry"                                  # missing: dry
    orl.MODE_PATH.write_text("live\n")
    assert orl.read_mode() == "live"
    orl.MODE_PATH.write_text("LIVE please\n")
    assert orl.read_mode() == "dry"                                  # unknown word: dry
    orl.MODE_PATH.write_text("off")
    assert orl.read_mode() == "off"
    os.chmod(orl.MODE_PATH, 0o666)
    assert orl.read_mode() == "dry"                                  # anyone could write it
    orl.MODE_PATH.unlink()
    real = org.path / "elsewhere"
    real.write_text("live")
    orl.MODE_PATH.symlink_to(real)
    assert orl.read_mode() == "dry"                                  # never through a link


def test_off_does_nothing_at_all(org):
    org.hub.task("task-14141414", "failed")
    org.hub.event("task-14141414", "status_failed")
    out = orl.run(NOW, orl.load_state("off"), mode="off", hub=org.hub, sessions=org.sessions,
                  panes=org.panes, send=org.send, wake=org.wake)
    assert org.sent == [] and org.hub.calls == [] and not orl.STATE_PATH.exists()
    assert out == ["owner-relay off (state/owner_relay.mode)"]


def test_the_state_is_written_atomically_and_never_through_a_planted_link(org):
    target = org.path / "victim"
    target.write_text("keep")
    orl.STATE_PATH.symlink_to(target)
    with pytest.raises(orl.StateUnusable):
        org.tick()
    assert target.read_text() == "keep" and orl.STATE_PATH.is_symlink()
    orl.save_state(orl._fresh("live"))
    assert target.read_text() == "keep" and not orl.STATE_PATH.is_symlink()
    assert json.loads(orl.STATE_PATH.read_text())["mode"] == "live"


def test_a_state_that_cannot_be_saved_sends_nothing(org, monkeypatch):
    org.hub.task("task-15151515", "failed")
    org.hub.event("task-15151515", "status_failed")

    def broken(state, path=None):
        raise orl.StateUnusable("disk full")

    with pytest.raises(orl.StateUnusable):
        orl.run(NOW, orl.load_state("live"), mode="live", hub=org.hub, sessions=org.sessions,
                panes=org.panes, send=org.send, wake=org.wake, queues=[], save=broken)
    assert org.sent == []


def test_hub_down_keeps_the_cursor_and_sends_nothing_new(org):
    org.hub.down = True
    out, st = org.tick()
    assert org.sent == [] and st["cursor"] is None and out[0].startswith("note hub unreadable")


def test_stats_print_wakes_per_box_per_day(org):
    st = orl.load_state("live")
    orl.note_wake(st, PH, NOW)
    orl.note_wake(st, PH, NOW + 60)
    assert orl.stats(st) == [f"{orl.thai_day(NOW)} {PH} 2 wakes"]


def test_wake_audit_lists_owner_relay_as_gated_and_paced(monkeypatch, tmp_path):
    assert "owner_relay" in wake_audit.GATED and wake_audit.BACKOFF_GATED["owner_relay"] == "tools/owner_relay.py"
    row = wake_audit.classify_unit("a.timer", "ExecStart=python tools/escalation_watch.py --nudge")
    assert (row["flagged"], row["trigger"]) == (False, "backoff") and "owner_relay" in row["evidence"]
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "escalation_watch.py").write_text("x = wake_interval(1)\n")
    (tmp_path / "tools" / "owner_relay.py").write_text("BATCH_S = 3600\n")       # not paced: flagged
    monkeypatch.setattr(wake_audit, "ROOT", tmp_path)
    assert wake_audit.classify_unit("a.timer", "ExecStart=python tools/escalation_watch.py --nudge")["flagged"]


# --- review round 1 (30 Oct): the mode is set by the tool, never by a shell redirect -----

def test_set_mode_writes_both_files_and_never_through_a_planted_link(org):
    victim = org.path / "victim.txt"
    victim.write_text("keep me\n")
    orl.MODE_PATH.symlink_to(victim)                     # planted before the first write
    assert orl.main(["--set-mode", "live"]) == 0
    assert victim.read_text() == "keep me\n"
    st = os.lstat(orl.MODE_PATH)
    assert stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o644 and orl.read_mode() == "live"
    assert orl._ours(orl.STATE_PATH) and orl.load_state("live")["mode"] == "live"
    assert orl.main(["--set-mode", "off"]) == 0 and orl.read_mode() == "off"


def test_set_mode_refuses_when_the_state_name_is_a_directory(org, capsys):
    orl.STATE_PATH.mkdir()
    assert orl.main(["--set-mode", "live"]) == 1
    assert not orl.MODE_PATH.exists() and orl.read_mode() == "dry"
    assert "mode not set" in capsys.readouterr().err


def test_screen_ready_tells_a_running_turn_from_a_held_screen(org):
    busy = "✻ Thinking… (esc to interrupt)\n" + READY
    for screen, want in ((READY, (True, "")), (busy, (False, "busy: turn running on screen")),
                         (DRAFT, (False, "screen not ready: prompt not empty"))):
        org.screens[PH] = screen
        assert orl.screen_ready(PH, org.sessions, org.panes) == want
    assert all(r.startswith(orl.NO_TRY) for r in ("busy", "busy: turn running on screen"))
    assert not "screen not ready: prompt not empty".startswith(orl.NO_TRY)
