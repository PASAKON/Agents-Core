"""ProjectTrack P3: tools/portfolio_watch.py and the live-sessions loop's PortfolioWatch.

No hub, no network. The ladder runs on stubbed findings with the mailbox and the state file in
tmp_path; findings() itself runs against the same in-memory store the P1 tests use.
"""
import contextlib
import io
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib import mailbox, portfolio as pf
from tests.test_projecttrack_p1 import Store
from tools import live_sessions as ls, portfolio_watch as pw

ROOT = Path(__file__).resolve().parent.parent
T = datetime(2026, 10, 27, 3, tzinfo=timezone.utc)
PH, OWNER = "project_head-40fefb4e", "cto-fresh"


@pytest.fixture
def box(tmp_path, monkeypatch):
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setenv("ORG_LETTERS_META", str(tmp_path / "meta.jsonl"))
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    monkeypatch.setattr(pw, "STATE_PATH", tmp_path / "state" / "portfolio_watch.json")
    return tmp_path


def letters(name):
    role, sid = name.split("-", 1)
    return mailbox.peek(role, sid)


def state():
    return json.loads(pw.STATE_PATH.read_text())["episodes"]


def finding(kind="late", id="proj", name="Proj", since=None, ph=PH, owner=OWNER, **kw):
    since = since or T - timedelta(hours=1)
    what = {"late": f"due {pw._iso(since)[:10]}", "no_plan": "no dated milestone",
            "waiting_ceo": "waiting on CEO", "unlinked_order": "taken, no project yet"}[kind]
    return {"key": f"{id}:{kind}", "kind": kind, "id": id, "name": name, "what": what, "since": since,
            "ph": ph, "owner": owner, **kw}


class Source:
    """What findings() returns on the next run."""

    def __init__(self, monkeypatch, *items, complete=True):
        self.set(*items, complete=complete)
        monkeypatch.setattr(pw, "findings", lambda now, conn=None: self.found)

    def set(self, *items, complete=True):
        self.found = pw.Found(items)
        self.found.complete = complete


def go(at, nudge=True, **kw):
    out = []
    rc = pw.run(at, nudge=nudge, out=out.append, **kw)
    return rc, out


# --- the ladder ----------------------------------------------------------------------

def test_a_late_project_writes_the_ph_once_and_a_second_run_writes_nothing(box, monkeypatch):
    Source(monkeypatch, finding())
    assert go(T)[0] == 0
    (letter,) = letters(PH)
    assert letter["kind"] == "blocker" and letter["prio"] == "urgent"
    assert letter["from"] == {"role": "system", "session_id": "portfolio-watch"}
    assert letter["subject"] == "late: Proj due 2026-10-27" and len(letter["subject"]) <= 80
    assert letter["body"].startswith("blocker · urgent · portfolio watch:")
    for word in ("finish it", "portfolio.py replan proj", "portfolio.py block proj"):
        assert word in letter["body"]
    assert letters(OWNER) == []
    assert state()["proj:late"] == {"start": pw._iso(T), "sent": ["first"], "red": False}
    go(T + timedelta(minutes=5))
    go(T + timedelta(hours=3, minutes=59))
    assert len(letters(PH)) == 1 and letters(OWNER) == []


def test_after_4_hours_the_owner_hears_once_and_after_24_the_episode_goes_red_without_a_letter(box, monkeypatch):
    Source(monkeypatch, finding())
    go(T)
    go(T + timedelta(hours=4))
    (letter,) = letters(OWNER)
    assert letter["subject"] == "still late: Proj due 2026-10-27" and letter["kind"] == "blocker"
    for word in ("cut scope", "move the date", "change the PH", "park"):
        assert word in letter["body"]
    assert len(letters(PH)) == 1
    go(T + timedelta(hours=10))
    assert len(letters(OWNER)) == 1 and state()["proj:late"]["red"] is False
    go(T + timedelta(hours=24))
    assert state()["proj:late"] == {"start": pw._iso(T), "sent": ["first", "owner"], "red": True}
    go(T + timedelta(hours=30))
    assert len(letters(PH)) == 1 and len(letters(OWNER)) == 1      # red is a mark, never a letter


def test_a_finding_that_is_gone_clears_its_episode_and_a_new_one_starts_fresh(box, monkeypatch):
    src = Source(monkeypatch, finding(), finding("no_plan", id="other"))
    go(T)
    assert set(state()) == {"proj:late", "other:no_plan"}
    src.set(finding("no_plan", id="other"))
    rc, out = go(T + timedelta(hours=1))
    assert rc == 0 and set(state()) == {"other:no_plan"} and len(letters(PH)) == 2   # nothing new for the end
    src.set(finding())
    go(T + timedelta(hours=2))
    assert state()["proj:late"]["start"] == pw._iso(T + timedelta(hours=2)) and len(letters(PH)) == 3
    src.set()
    assert go(T + timedelta(hours=3))[0] == 0 and state() == {}


def test_a_list_cut_at_the_monitors_cap_never_ends_an_episode(box, monkeypatch):
    src = Source(monkeypatch, finding())
    go(T)
    src.set(complete=False)             # attention hit its 10 rows: this one may only be hidden
    rc, out = go(T + timedelta(hours=1))
    assert "proj:late" in state() and any("more may be hidden" in line for line in out)
    src.set(finding())
    go(T + timedelta(hours=2))
    assert len(letters(PH)) == 1        # still the one episode: no second first letter


def test_a_project_with_no_ph_writes_its_c_level_first(box, monkeypatch):
    Source(monkeypatch, finding(ph=None))
    go(T)
    (letter,) = letters(OWNER)
    assert "no Project Head" in letter["body"] and letter["subject"] == "late: Proj due 2026-10-27"
    assert [f for f in box.glob("inbox/*")] == [box / "inbox" / OWNER]
    go(T + timedelta(hours=4))          # the 4 h step is its own step: one more, never more than one per step
    assert len(letters(OWNER)) == 2
    go(T + timedelta(hours=5))
    assert len(letters(OWNER)) == 2


def test_a_project_with_no_plan_is_asked_for_milestones_and_dates(box, monkeypatch):
    Source(monkeypatch, finding("no_plan"))
    go(T)
    (letter,) = letters(PH)
    assert letter["subject"] == "no plan: Proj no dated milestone"
    assert "has no plan" in letter["body"] and "milestone add" in letter["body"] and "is no plan" not in letter["body"]


def test_a_waiting_ceo_finding_gets_no_letter_but_is_tracked_and_goes_red(box, monkeypatch):
    Source(monkeypatch, finding("waiting_ceo"))
    go(T)
    go(T + timedelta(hours=5))
    go(T + timedelta(hours=25))
    assert not (box / "inbox").exists()
    assert state()["proj:waiting_ceo"]["red"] is True


def test_an_unlinked_order_writes_the_c_level_that_took_it_only_once_it_is_30_minutes_old(box, monkeypatch):
    order = lambda age: finding("unlinked_order", id="O-20261027-1000-ab12", name="ship the poster",
                                since=T - timedelta(minutes=age), ph=None, owner="coo-1a2b3c4d")
    src = Source(monkeypatch, order(29))
    go(T)
    assert not (box / "inbox").exists()
    src.set(order(31))
    go(T + timedelta(minutes=2))
    (letter,) = letters("coo-1a2b3c4d")
    assert letter["subject"] == "unlinked order: ship the poster taken, no project yet"
    assert "order link O-20261027-1000-ab12 <project>" in letter["body"] and "ship the poster" in letter["body"]
    go(T + timedelta(minutes=10))
    assert len(letters("coo-1a2b3c4d")) == 1


def test_the_ceo_is_never_written_to_and_an_unaddressable_finding_sends_nothing(box, monkeypatch):
    assert pw._taker_box("ceo-1") is None and pw._box("ceo", "x") is None
    assert pw._box("../etc", "x") is None and pw._box("cto", "a/b") is None
    Source(monkeypatch, finding(ph=None, owner=None))
    rc, out = go(T)
    assert rc == 0 and not (box / "inbox").exists()
    assert pw.plan(pw.Found([finding(ph=None, owner=None)]), {"episodes": {}}, T) == []


def test_boxes_follow_the_owner_session_and_the_lane():
    assert pw._owner_box("cto", "cto-fresh") == "cto-fresh"
    assert pw._owner_box("cmo", "cmo-ab12cd34") == "cmo-ab12cd34"
    assert pw._owner_box("cto", "abcd1234") == "cto-abcd1234"
    assert pw._owner_box("cto", None) is None
    assert pw._ph_box("project_head-40fefb4e") == pw._ph_box("40fefb4e") == PH
    assert pw._ph_box(None) is None


def test_a_dry_run_prints_what_it_would_send_and_touches_nothing(box, monkeypatch):
    Source(monkeypatch, finding())
    rc, out = go(T, nudge=False)
    assert rc == 0 and any(l == f"would send  {PH} <- late: Proj due 2026-10-27" for l in out)
    assert not (box / "inbox").exists() and not pw.STATE_PATH.exists() and not (box / "meta.jsonl").exists()
    go(T)
    assert len(letters(PH)) == 1        # the dry run left no mark: the real run still sends


def test_a_letter_that_fails_to_send_is_not_remembered_and_goes_out_next_run(box, monkeypatch):
    Source(monkeypatch, finding())
    boom = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
    rc, out = go(T, send=boom)
    assert rc == 1 and state()["proj:late"]["sent"] == [] and any("not sent" in l for l in out)
    assert go(T + timedelta(minutes=5))[0] == 0
    assert len(letters(PH)) == 1 and state()["proj:late"]["sent"] == ["first"]


def test_a_state_file_that_cannot_be_saved_sends_nothing(box, monkeypatch):
    Source(monkeypatch, finding())
    (box / "blocked").write_text("a file where the state directory should be")
    monkeypatch.setattr(pw, "STATE_PATH", box / "blocked" / "portfolio_watch.json")
    rc, out = go(T)
    assert rc == 1 and not (box / "inbox").exists() and any("no letter goes out" in l for l in out)


def test_a_corrupt_or_hostile_state_file_reads_as_empty(box):
    pw.STATE_PATH.parent.mkdir(parents=True)
    pw.STATE_PATH.write_text("{not json")
    assert pw.load_state(T) == {"episodes": {}}
    pw.STATE_PATH.write_text(json.dumps({"episodes": {"a:late": {"start": "2999-01-01T00:00:00Z", "sent": ["first", "x"], "red": "yes"},
                                                       "b:late": "junk", 7: {}}}))
    assert pw.load_state(T) == {"episodes": {"a:late": {"start": pw._iso(T), "sent": ["first"], "red": False}}}


# --- findings() against the real payload ---------------------------------------------

@pytest.fixture
def store(monkeypatch):
    store = Store()

    @contextlib.contextmanager
    def tx(conn=None):
        yield conn or store
    monkeypatch.setattr(pf, "_tx", tx)
    yield store
    store.raw.close()


def test_findings_reads_the_monitors_flags_and_the_boxes(store):
    actor = "cto-abcdef12"
    pf.open_project("late-one", "Late One", "cto", actor=actor, stage="active", owner_session="cto-fresh",
                    ph_session="project_head-40fefb4e", due_at=T - timedelta(hours=2), due_set_by="clevel",
                    now=T - timedelta(days=1))
    pf.milestone_add("late-one", "ship", due_at=T + timedelta(days=1), actor=actor, now=T - timedelta(days=1))
    pf.open_project("lone", "Lone", "cmo", actor="cmo-1", stage="active", now=T - timedelta(days=1))   # no PH, no plan
    pf.open_project("parked-one", "Parked", "cto", actor=actor, stage="active", owner_session="cto-fresh",
                    ph_session="aaaaaaaa", due_at=T - timedelta(days=2), due_set_by="clevel", now=T - timedelta(days=3))
    pf.park("parked-one", actor=actor, now=T - timedelta(days=1))
    for oid, words, taker, project, age in (("O-1", "ship the poster", "coo-1a2b3c4d", None, timedelta(minutes=31)),
                                            ("O-2", "too fresh", "coo-1a2b3c4d", None, timedelta(minutes=5)),
                                            ("O-3", "already linked", actor, "late-one", timedelta(hours=2))):
        store.execute("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id) VALUES (?, ?, ?, ?, ?, ?)",
                      (oid, words, "sompong:3", taker, T - age, project))
    found = pw.findings(T, store)
    by = {f["key"].split(":", 1)[1] if f["kind"] == "unlinked_order" else f["key"]: f for f in found}
    assert set(by) == {"late-one:late", "lone:no_plan", "unlinked_order"} and found.complete
    late = by["late-one:late"]
    assert (late["ph"], late["owner"], late["name"]) == (PH, "cto-fresh", "Late One")
    assert late["what"] == "due 2026-10-27" and late["since"] == T - timedelta(hours=2)
    assert (by["lone:no_plan"]["ph"], by["lone:no_plan"]["owner"]) == (None, None)
    order = by["unlinked_order"]
    assert (order["name"], order["owner"], order["ph"]) == ("ship the poster", "coo-1a2b3c4d", None)


def _open(pid="proj", **kw):
    pf.open_project(pid, "Proj", "cto", actor="cto-abcdef12", stage="active", owner_session="cto-fresh",
                    ph_session="project_head-40fefb4e", now=T - timedelta(days=1), **kw)


def test_a_milestone_10_minutes_overdue_writes_the_ph_once_and_a_replan_clears_the_episode(box, store):
    _open(due_at=T + timedelta(days=1), due_set_by="ph")
    pf.milestone_add("proj", "write it", due_at=T - timedelta(minutes=10), actor="cto-abcdef12", now=T - timedelta(days=1))
    pf.milestone_add("proj", "ship it", due_at=T + timedelta(days=1), actor="cto-abcdef12", now=T - timedelta(days=1))
    (found,) = pw.findings(T, store)
    assert (found["key"], found["since"]) == ("proj:late", T - timedelta(minutes=10))
    rc, out = go(T, conn=store)
    assert rc == 0
    (letter,) = letters(PH)
    assert letter["subject"].startswith("late: Proj") and "since 2026-10-27T02:50Z, 10 min ago" in letter["body"]
    assert state()["proj:late"]["sent"] == ["first"] and letters(OWNER) == []
    go(T + timedelta(minutes=5), conn=store)
    assert len(letters(PH)) == 1                                    # one letter per episode
    pf.replan("proj", 1, T + timedelta(days=1), actor="cto-abcdef12", actor_role="cto", why="dependency", now=T)
    rc, out = go(T + timedelta(minutes=10), conn=store)
    assert rc == 0 and state() == {} and len(letters(PH)) == 1 and any("nothing late" in line for line in out)


def test_the_letter_about_a_late_milestone_names_it_in_the_subject(box, store):
    _open(due_at=T + timedelta(days=1), due_set_by="ph")
    pf.milestone_add("proj", "write it", due_at=T - timedelta(minutes=10), actor="cto-abcdef12", now=T - timedelta(days=1))
    (found,) = pw.findings(T, store)
    assert found["what"] == "M1"
    assert go(T, conn=store)[0] == 0
    assert [l["subject"] for l in letters(PH)] == ["late: Proj M1"]
    assert "(M1; since 2026-10-27T02:50Z, 10 min ago)" in letters(PH)[0]["body"]


def test_a_done_overdue_milestone_and_a_loop_with_old_milestones_are_not_findings(store):
    _open(due_at=T + timedelta(days=2), due_set_by="ph")
    pf.milestone_add("proj", "write it", due_at=T - timedelta(minutes=10), actor="cto-abcdef12", now=T - timedelta(days=1))
    pf.milestone_done("proj", 1, "sha1", actor="cto-abcdef12", now=T - timedelta(minutes=5))
    _open("loop", kind="loop", cadence_h=24)
    pf.beat("loop", "episode 1", actor="cto-abcdef12", now=T - timedelta(hours=1))      # next beat due 28 Oct 02:00Z
    pf.milestone_add("loop", "old", due_at=T - timedelta(hours=5), actor="cto-abcdef12", now=T - timedelta(days=1))
    assert [f["key"] for f in pw.findings(T, store) if f["kind"] == "late"] == []
    (late,) = [f for f in pw.findings(T + timedelta(hours=24), store) if f["kind"] == "late"]
    assert (late["key"], late["what"]) == ("loop:late", "due 2026-10-28")   # the beat rule, no milestone named


def test_a_parked_or_closed_project_is_never_a_finding_even_if_the_payload_flags_it(store, monkeypatch):
    pf.open_project("gone", "Gone", "cto", actor="cto-1", stage="active", owner_session="cto-fresh",
                    ph_session="aaaaaaaa", due_at=T - timedelta(days=2), due_set_by="clevel", now=T - timedelta(days=3))
    flagged = {"attention": [{"kind": "late", "project_id": "gone", "order_id": None, "text": "x",
                              "since": pw._iso(T - timedelta(days=2)), "decided": None}]}
    monkeypatch.setattr(pf, "monitor_payload", lambda now, conn=None, version=1, attention_cap=10: flagged)
    assert [f["key"] for f in pw.findings(T, store)] == ["gone:late"]
    pf.park("gone", actor="cto-1", now=T - timedelta(days=1))
    assert pw.findings(T, store) == []


def test_findings_reads_past_the_wire_cap_and_says_when_its_own_cap_is_hit(store, monkeypatch):
    ids = [f"p{i}" for i in range(12)]
    for i in ids:
        pf.open_project(i, i, "cto", actor="cto-1", stage="active", owner_session="cto-fresh",
                        due_at=T - timedelta(hours=1), due_set_by="clevel", now=T - timedelta(days=1))
        pf.milestone_add(i, "m", due_at=T + timedelta(days=1), actor="cto-1", now=T - timedelta(days=1))
    found = pw.findings(T, store)
    assert len(found) == 12 and found.complete is True          # the widget's 10 never hides one
    monkeypatch.setattr(pw, "CAP", 5)
    found = pw.findings(T, store)
    assert len(found) == 5 and found.complete is False


def test_a_hub_that_only_answers_from_its_snapshot_is_never_acted_on(monkeypatch):
    from lib import db

    @contextlib.contextmanager
    def snapshot():
        yield db._SnapshotConnection(None, "2026-10-26T00:00:00Z")
    monkeypatch.setattr(db, "get_conn", snapshot)
    with pytest.raises(pw.StaleHub):
        pw.findings(T)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert pw.run(T, nudge=True, out=lambda s: None) == 3
    assert err.getvalue() == "portfolio_watch: no findings (StaleHub), nothing sent\n"


# --- the loop wrapper ----------------------------------------------------------------

class FakeProc:
    def __init__(self, rc=0, stderr=b""):
        self.rc, self.stderr, self.killed = rc, io.BytesIO(stderr), False

    def poll(self):
        return -9 if self.killed else self.rc

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        return self.poll()


class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


def runner(procs, **kw):
    spawns, said, clock = [], [], Clock()

    def popen(argv, **kwargs):
        spawns.append((argv, kwargs))
        return procs[len(spawns) - 1] if len(spawns) <= len(procs) else FakeProc(0)
    return ls.PortfolioWatch(["run"], cwd=ROOT, report=said.append, popen=popen, clock=clock, **kw), spawns, said, clock


def advance(watch, clock, seconds, step=5):
    for _ in range(seconds // step):
        clock.t += step
        watch.tick()


def test_the_watch_is_scheduled_at_most_once_every_5_minutes():
    watch, spawns, said, clock = runner([FakeProc(0)])
    watch.tick()
    assert len(spawns) == 1
    advance(watch, clock, 295)
    assert len(spawns) == 1 and said == []
    advance(watch, clock, 5)
    assert len(spawns) == 2
    advance(watch, clock, 600)
    assert len(spawns) == 4 and said == []


def test_a_child_that_fails_or_hangs_is_reported_once_and_the_next_run_still_comes():
    watch, spawns, said, clock = runner([FakeProc(1, b"noise\nportfolio_watch: failed, 2 findings, 0 letters sent, 1 not sent\nmore noise\n")])
    watch.tick()
    advance(watch, clock, 300)
    assert len(spawns) == 2
    assert set(said) == {"portfolio watch exit 1 (letter or state not written): failed, 2 findings, 0 letters sent, 1 not sent"}
    slow = FakeProc(rc=None)
    watch, spawns, said, clock = runner([slow, FakeProc(0)])
    watch.tick()
    advance(watch, clock, 60)
    assert not slow.killed
    advance(watch, clock, 5)
    assert slow.killed and said == ["portfolio watch timed out after 60s"]
    advance(watch, clock, 235)
    assert len(spawns) == 2 and watch.proc is not None
    watch.close()
    assert watch.proc is None
    live = FakeProc(rc=None)
    watch, spawns, said, clock = runner([live])
    watch.tick()
    watch.close()
    assert live.killed and watch.proc is None


def test_a_spawn_that_raises_never_reaches_the_loop():
    said, clock = [], Clock()

    def popen(argv, **kw):
        raise OSError("no fork")
    watch = ls.PortfolioWatch(["run"], report=said.append, popen=popen, clock=clock)
    watch.tick()
    assert said == ["portfolio watch error (OSError)"] and watch.proc is None


def test_only_the_hub_host_builds_a_watch_and_its_argv_is_the_script_with_nudge():
    assert ls.make_watch("mac") is None and ls.make_watch("winbox") is None
    watch = ls.make_watch("contabo")
    assert isinstance(watch, ls.PortfolioWatch)
    argv = ls.watch_argv(ROOT)
    assert argv[1:] == [str(ROOT / "tools" / "portfolio_watch.py"), "--nudge"]
    assert (ROOT / "tools" / "portfolio_watch.py").is_file()
    assert "infisical" not in " ".join(argv)


def test_the_push_keeps_its_own_period_label_and_prefix():
    push = ls.PortfolioPush(["run"])
    assert (push.period_s, push.timeout_s, push.label, push.prefix) == (60, 30, "portfolio push", "portfolio_push: ")


class _Hub:
    class _R:
        def fetchall(self):
            return []

    def execute(self, sql, params=()):
        return self._R()

    def commit(self):
        pass

    def close(self):
        pass


def test_a_publisher_with_a_failing_watch_child_keeps_publishing_and_closes_it(tmp_path, monkeypatch):
    published = []
    monkeypatch.setattr(ls, "publish_once", lambda conn, host, dirs, prev: published.append(1) or set())
    clock = Clock()
    monkeypatch.setattr(ls.time, "monotonic", clock)
    reports, spawns = [], []

    def popen(argv, **kw):
        spawns.append(argv)
        return FakeProc(3, b"portfolio_watch: no findings (HubConnectError), nothing sent\n")
    watch = ls.PortfolioWatch(["run"], report=reports.append, popen=popen, clock=clock)

    class Stop(threading.Event):
        n = 0

        def wait(self, timeout=None):
            Stop.n += 1
            clock.t += timeout
            if Stop.n >= 200:               # 200 polls of 5 s = 1000 s
                self.set()
            return self.is_set()
    errors = []
    pub = ls.Publisher("postgresql://u@h/db", "contabo", [tmp_path], stop=Stop(), lock_path=tmp_path / "l",
                       connect=lambda url: _Hub(), watch=watch, on_error=errors.append)
    assert pub.run() == 0
    assert errors == [] and len(published) >= 3
    assert 3 <= len(spawns) <= 4            # one every 300 s over ~1000 s
    assert set(reports) == {"portfolio watch exit 3 (hub unreadable): no findings (HubConnectError), nothing sent"}
