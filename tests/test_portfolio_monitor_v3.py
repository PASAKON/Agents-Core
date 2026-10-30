"""ProjectPage, Agents-Core half: lib.portfolio.monitor_payload(version=3) and `portfolio.py ph`.

The contract is docs/design/portfolio-monitor-v3.md. Everything here runs against a LOCAL
Postgres and self-skips unless ORG_TEST_DB_URL is set (tests/test_portfolio.py has the setup; the
pg fixture and the small helpers are that file's). Nothing here prints a Remote Control id: a
failing assert shows a count or a flag, and the test ids are made-up strings that are not real ones.

Golden files: tests/fixtures/portfolio_monitor_v{1,2}_golden.json are the v1 and v2 bodies of
seed_golden() as they were before v3 existed. To rewrite them on purpose (the v1/v2 contract changed):
    PORTFOLIO_V3_REGEN=1 ORG_TEST_DB_URL=... pytest tests/test_portfolio_monitor_v3.py -k byte_identical
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.portfolio as pf  # noqa: E402
from test_portfolio import (  # noqa: E402, F401  (pg is a fixture, used by name)
    COO, CTO, CMO, PH, WORKER, T, at, kinds, mk, needs_pg, pg, q, task,
)
from tools import ask_run, portfolio_push  # noqa: E402
from tools.agent_transport import CEO_IDENTITY  # noqa: E402
from tools import portfolio as cli  # noqa: E402

GOLDEN = ROOT / "tests" / "fixtures"
APP = "session_01AbCdEf"              # made up; the shape is what counts
APP2 = "session_02ZyXwVu"


# --- seeds --------------------------------------------------------------------

def seed_golden(conn):
    """22 monitored projects: enough that the v1/v2 row cap of 20 cuts two, and every v2 field is set
    somewhere (a late milestone, a CEO blocker, a loop, a plan, a decision, a running task, an order)."""
    for i in range(1, 23):
        pid = f"p{i:02d}"
        pf.open_project(pid, f"Project {i}", "cto" if i % 2 else "cmo", actor="cto-c34459eb",
                        stage="review" if i == 3 else "active", ph_session=f"{i:08x}" if i <= 12 else None,
                        owner_session="cto-fresh" if i % 3 == 0 else None, host="contabo" if i % 4 == 0 else None,
                        kind="loop" if i == 4 else "finite", cadence_h=24 if i == 4 else None, now=at(1, i))
        pf.milestone_add(pid, "first", actor="x", now=at(1, i), due_at=at(2) if i == 1 else None)
        if i % 2:
            pf.milestone_add(pid, "second", actor="x", now=at(1, i))
        if i % 5 == 0:
            pf.milestone_done(pid, 1, "sha abc", actor="x", now=at(2, i))
    pf.block("p02", "ceo", "pick one", actor="x", now=at(2, 30))
    pf.block("p07", "external", "vendor reply", actor="x", now=at(2, 31))
    pf.beat("p04", "round one", actor="x", now=at(3, 10))
    pf.set_plan("p06", next_step="write the tests", next_owner="tester", actor="x", now=at(3, 11))
    pf.decided("p02", "took the cheaper runner", actor="cto-c34459eb", now=at(3, 12))
    pf.order_take("make it faster", "chat:ceo-direct", actor="cto-c34459eb", project_id="p01", now=at(3, 13),
                  order_id="O-fixed-1")
    pf.order_take("something unlinked", "chat:ceo-direct", actor="cto-c34459eb", now=at(2, 0),
                  order_id="O-fixed-2")
    pf.park("p21", actor="x", reason="paused", now=at(3, 14))
    pf.park("p22", actor="x", reason="paused", now=at(3, 15))
    conn.execute("INSERT INTO session_heartbeats (session_id, project_id, at) VALUES (?, ?, ?)",
                 ("hb1", "p01", at(3, 18)))
    conn.commit()
    task(conn, "task-g1", project="p05", owner="00000005", status="in_progress")


def golden_bodies():
    return {v: json.dumps(pf.monitor_payload(T, version=v), ensure_ascii=False, indent=2) + "\n" for v in (1, 2)}


@needs_pg
@pytest.mark.parametrize("v", [1, 2])
def test_v1_and_v2_are_byte_identical_to_before_v3(pg, v):
    seed_golden(pg)
    body = golden_bodies()[v]
    path = GOLDEN / f"portfolio_monitor_v{v}_golden.json"
    if os.environ.get("PORTFOLIO_V3_REGEN") == "1":
        path.write_text(body, encoding="utf-8")
    assert body == path.read_text(encoding="utf-8")
    payload = json.loads(body)
    assert payload["v"] == v and len(payload["projects"]) == 20      # 22 are monitored: the cap still cuts two


# --- a hub with live sessions and a Run Inbox that can be told what to say ---------------------

class FakeRunInbox:
    """Stands in for tools.ask_run._call: records the calls, answers asks and questions, or raises."""

    def __init__(self):
        self.asks, self.questions, self.reply, self.exc, self.calls = [], [], None, None, []

    def __call__(self, method, path, *, body=None, query=None, timeout=None, **kw):
        self.calls.append({"method": method, "path": path, "query": dict(query or {}), "timeout": timeout})
        if self.exc is not None:
            raise self.exc
        if self.reply is not None:
            return self.reply
        return {"asks": self.asks} if path == ask_run.ASKS_PATH else {"questions": self.questions}


def card(session, status="pending"):
    return {"id": "RUN-x", "status": status, "requester": {"session": session, "role": "project_head"}}


@pytest.fixture
def hub(pg, monkeypatch):
    def clean():
        for t in ("live_sessions", "live_hosts"):
            pg.execute(f"DELETE FROM {t}")
        pg.commit()
    clean()
    inbox = FakeRunInbox()
    monkeypatch.setattr(ask_run, "_call", inbox)
    yield SimpleNamespace(conn=pg, inbox=inbox)
    pg.rollback()
    clean()


def live_host(conn, host="contabo", age_s=10):
    conn.execute("INSERT INTO live_hosts (host, published_at, publisher, n_sessions)"
                 " VALUES (?, now() - (? * interval '1 second'), 'test', 1)"
                 " ON CONFLICT (host) DO UPDATE SET published_at = EXCLUDED.published_at", (host, age_s))
    conn.commit()


def live_row(conn, host, sid, *, status="idle", role="project_head", name=None, bridge=APP, age_s=10):
    conn.execute("INSERT INTO live_sessions (host, uuid, sid, role, name, address, status, pid, seen_at, verified, bridge_id)"
                 " VALUES (?, ?, ?, ?, ?, ?, ?, 1, now() - (? * interval '1 second'), true, ?)",
                 (host, f"uuid-{host}-{sid}", sid, role, name or f"PH#{sid[:3]} (CTO) - X", name or "x", status, age_s, bridge))
    conn.commit()


def with_ph(hub, pid="p1", sid="aaaa1111", *, host="contabo", project_host=None, status="idle", bridge=APP,
            host_age_s=10, **kw):
    """An active project whose PH is live on `host` (`status` None: not live anywhere). `project_host` is
    the host written on the project row."""
    mk(pid, ph_session=sid, host=project_host, **kw)
    if status is not None:
        live_host(hub.conn, host, host_age_s)
        live_row(hub.conn, host, sid, status=status, bridge=bridge)


def payload3(**kw):
    return pf.monitor_payload(T, version=3, **kw)


def row_of(payload, pid="p1"):
    return next(r for r in payload["projects"] if r["id"] == pid)


# --- ph.state --------------------------------------------------------------------------------

@needs_pg
def test_a_running_session_is_running_with_its_host_and_app(hub):
    with_ph(hub, status="running")
    ph = row_of(payload3())["ph"]
    assert ph == {"sid": "aaaa1111", "host": "contabo", "live": True, "app": APP, "state": "running"}
    assert hub.inbox.calls == []            # nothing to ask: it is already working


@needs_pg
@pytest.mark.parametrize("status", ["pending", "in_progress", "review"])
def test_idle_with_a_task_in_flight_is_waiting(hub, status):
    with_ph(hub)
    task(hub.conn, "task-1", project="p1", owner="aaaa1111", status=status)
    assert row_of(payload3())["ph"]["state"] == "waiting"
    assert hub.inbox.calls == []            # the task already decided it


@needs_pg
@pytest.mark.parametrize("status", ["done", "merged", "failed", "cancelled", "dropped"])
def test_a_finished_task_does_not_make_it_wait(hub, status):
    with_ph(hub)
    task(hub.conn, "task-1", project="p1", owner="aaaa1111", status=status)
    assert row_of(payload3())["ph"]["state"] == "idle"


@needs_pg
def test_another_sessions_task_does_not_make_it_wait(hub):
    with_ph(hub)
    task(hub.conn, "task-1", project="p1", owner="bbbb2222", status="review")
    assert row_of(payload3())["ph"]["state"] == "idle"


@needs_pg
@pytest.mark.parametrize("where", ["asks", "questions"])
def test_idle_with_a_pending_card_of_its_own_is_waiting(hub, where):
    with_ph(hub)
    getattr(hub.inbox, where).append(card("project_head-aaaa1111"))
    assert row_of(payload3())["ph"]["state"] == "waiting"


@needs_pg
@pytest.mark.parametrize("item", [card("project_head-bbbb2222"), card("project_head-aaaa1111", status="done"),
                                  card("cto-aaaa1111x"), {"status": "pending"}, {"status": "pending", "requester": "x"}])
def test_a_card_that_is_not_pending_and_its_own_does_not_count(hub, item):
    with_ph(hub)
    hub.inbox.asks.append(item)
    assert row_of(payload3())["ph"]["state"] == "idle"


@needs_pg
def test_idle_with_nothing_in_flight_is_idle_and_the_inbox_is_asked_for_pending_only(hub):
    with_ph(hub)
    assert row_of(payload3())["ph"]["state"] == "idle"
    assert sorted(c["path"] for c in hub.inbox.calls) == [ask_run.ASKS_PATH, ask_run.QUESTIONS_PATH]
    assert all(c["query"]["status"] == "pending" and c["timeout"] <= 5 for c in hub.inbox.calls)


@needs_pg
def test_the_inbox_is_asked_once_however_many_idle_phs_there_are(hub):
    for i in range(5):
        with_ph(hub, f"p{i}", f"aaaa000{i}")
    payload3()
    assert len(hub.inbox.calls) == 2


@needs_pg
def test_a_parked_project_is_parked_whatever_its_session_does(hub):
    with_ph(hub, status="running", stage="parked")
    ph = row_of(payload3())["ph"]
    assert ph["state"] == "parked" and ph["live"] is True


@needs_pg
def test_no_live_row_is_offline_and_the_host_falls_back_to_the_project(hub):
    with_ph(hub, status=None, project_host="winbox")
    ph = row_of(payload3())["ph"]
    assert ph == {"sid": "aaaa1111", "host": "winbox", "live": False, "app": None, "state": "offline"}


@needs_pg
def test_no_live_row_and_no_project_host_leaves_the_host_null(hub):
    with_ph(hub, status=None)
    assert row_of(payload3())["ph"]["host"] is None


@needs_pg
def test_a_stale_host_is_offline_but_keeps_its_row_host(hub):
    with_ph(hub, status="running", host_age_s=10_000, project_host="mac")
    ph = row_of(payload3())["ph"]
    assert (ph["live"], ph["state"], ph["host"]) == (False, "offline", "contabo")


@needs_pg
def test_a_host_that_never_published_is_stale(hub):
    mk("p1", ph_session="aaaa1111")
    live_row(hub.conn, "contabo", "aaaa1111", status="running")        # no live_hosts row
    assert row_of(payload3())["ph"]["state"] == "offline"


@needs_pg
def test_the_staleness_threshold_is_the_live_sessions_one(hub):
    from tools import live_sessions
    with_ph(hub, host_age_s=live_sessions.DEFAULT_TTL_S - 20)
    assert row_of(payload3())["ph"]["live"] is True
    hub.conn.execute("UPDATE live_hosts SET published_at = now() - (? * interval '1 second')", (live_sessions.DEFAULT_TTL_S + 20,))
    hub.conn.commit()
    assert row_of(payload3())["ph"]["live"] is False


@needs_pg
def test_a_status_it_cannot_classify_is_unknown(hub):
    with_ph(hub, status="unknown")
    assert row_of(payload3())["ph"]["state"] == "unknown"


@needs_pg
def test_every_state_is_one_of_the_listed_ones(hub):
    with_ph(hub, "p1", "aaaa0001", status="running")
    with_ph(hub, "p2", "aaaa0002")
    with_ph(hub, "p3", "aaaa0003", status="unknown")
    with_ph(hub, "p4", "aaaa0004", status=None)
    with_ph(hub, "p5", "aaaa0005", stage="parked")
    states = {r["ph"]["state"] for r in payload3()["projects"]}
    assert states == {"running", "idle", "unknown", "offline", "parked"} <= set(pf.PH_STATES)


# --- ph.sid / host / app: the shapes the Console validator accepts -----------------------------

@needs_pg
@pytest.mark.parametrize("sid", [None, "", "abc", "ABCD1234", "a" * 17, "has space", "x-y-z-w", "UPPER123"])
def test_a_ph_session_that_is_not_a_valid_sid_gives_no_ph(hub, sid):
    mk("p1", ph_session=sid)
    assert row_of(payload3())["ph"] is None


@needs_pg
def test_a_ph_session_with_the_project_head_prefix_is_read_bare(hub):
    mk("p1", ph_session="project_head-aaaa1111")
    live_host(hub.conn)
    live_row(hub.conn, "contabo", "aaaa1111", status="running")
    ph = row_of(payload3())["ph"]
    assert ph["sid"] == "aaaa1111" and ph["state"] == "running"


@needs_pg
@pytest.mark.parametrize("bad", [
    "https://claude.ai/code/session_01AbCdEf", "javascript:alert(1)", "session_" + "a" * 101, "session_",
    "session_ab-cd", "session_ab cd", "session_ab\n", "Session_01AbCd", "x" + APP, "//evil.example/session_ab",
    "session_<script>", "", " ",
])
def test_an_app_id_that_is_not_a_session_id_is_dropped(hub, bad):
    with_ph(hub, bridge=bad, owner_session="cto-f69c4825")
    live_row(hub.conn, "contabo", "f69c4825", role="cto", bridge=bad)
    live_row(hub.conn, "contabo", "bbbb2222", name="PH#bbb (CTO) - Un", bridge=bad)
    p = payload3()
    assert row_of(p)["ph"]["app"] is None
    assert row_of(p)["lead"]["app"] is None
    assert [u["app"] for u in p["unlinked_ph"]] == [None]


@needs_pg
def test_the_longest_valid_app_id_passes(hub):
    longest = "session_" + "aZ09" * 25
    assert len(longest) == 108
    with_ph(hub, bridge=longest)
    assert row_of(payload3())["ph"]["app"] == longest


@needs_pg
@pytest.mark.parametrize("bad", ["Bad Host!", "x" * 33, "UPPER", "a/b", ""])
def test_a_host_that_is_not_a_host_name_becomes_null(hub, bad):
    with_ph(hub, host=bad)
    live_row(hub.conn, bad, "bbbb2222", name="PH#bbb (CTO) - Un")
    p = payload3()
    assert row_of(p)["ph"]["host"] is None and [u["host"] for u in p["unlinked_ph"]] == [None]


# --- lead --------------------------------------------------------------------------------------

@needs_pg
def test_the_lead_is_found_by_session_id_not_by_role(hub):
    mk("p1", lane="cmo", owner_session="cmo-ef04792e")
    live_host(hub.conn)
    live_row(hub.conn, "contabo", "ef04792e", role="unknown", name="CMO Main", bridge=APP2)
    assert row_of(payload3())["lead"] == {"role": "cmo", "sid": "ef04792e", "app": APP2}


@needs_pg
def test_a_lead_with_no_live_row_still_names_its_lane_and_session(hub):
    mk("p1", owner_session="cto-fresh")
    assert row_of(payload3())["lead"] == {"role": "cto", "sid": "fresh", "app": None}


@needs_pg
@pytest.mark.parametrize("owner", [None, "", "!!", "cto-", "a b", "X" * 40])
def test_no_usable_owner_session_gives_no_lead(hub, owner):
    mk("p1", owner_session=owner)
    assert row_of(payload3())["lead"] is None


@needs_pg
def test_a_bare_owner_session_is_read_as_the_sid(hub):
    mk("p1", owner_session="f69c4825")
    live_host(hub.conn)
    live_row(hub.conn, "contabo", "f69c4825", role="cto", bridge=APP2)
    assert row_of(payload3())["lead"] == {"role": "cto", "sid": "f69c4825", "app": APP2}


# --- last_event_at -----------------------------------------------------------------------------

@needs_pg
def test_last_event_at_is_the_newest_event_of_the_project(hub):
    mk("p1")
    mk("p2")
    pf.milestone_add("p1", "m", actor="x", now=at(2, 5))
    pf.decided("p1", "d", actor="x", now=at(2, 40))
    pf.set_plan("p2", next_step="n", next_owner="o", actor="x", now=at(1, 30))
    p = payload3()
    assert row_of(p, "p1")["last_event_at"] == "2026-10-14T02:40:00Z"
    assert row_of(p, "p2")["last_event_at"] == "2026-10-14T01:30:00Z"


# --- unlinked_ph ---------------------------------------------------------------------------------

@needs_pg
def test_unlinked_ph_lists_live_project_heads_no_row_names_and_parses_their_names(hub):
    live_host(hub.conn, "contabo")
    live_host(hub.conn, "mac")
    live_host(hub.conn, "winbox")
    live_row(hub.conn, "contabo", "8dbe4ccc", name="🌐 PH#8db (CTO) - ExpertAdvisor", bridge=APP)
    live_row(hub.conn, "mac", "a2c13fe6", name="💻 PH#a2c (CMO) - ChampaVeo — BL basket pair 1", bridge=None)
    live_row(hub.conn, "winbox", "1a1da50e", name="🖥️ PH#1a1 (XYZ) - TikTokWinbox", bridge=APP2)
    live_row(hub.conn, "winbox", "43892fb5", name="⏸ 🖥️ PH#438 (COO) - Lumina Skies", bridge=None)
    live_row(hub.conn, "winbox", "4ae68058", name="🖥️ PH#4ae (CFO) - Books + Tax", bridge=None)
    live_row(hub.conn, "contabo", "3f2bd16a", name="something nobody can parse", bridge=None)
    live_row(hub.conn, "contabo", "757e61cc", name="🌐 PH#757 (CTO)", bridge=None)
    got = {u["sid"]: u for u in payload3()["unlinked_ph"]}
    assert got["8dbe4ccc"] == {"sid": "8dbe4ccc", "host": "contabo", "name": "ExpertAdvisor", "lane": "cto", "app": APP}
    assert got["a2c13fe6"] == {"sid": "a2c13fe6", "host": "mac", "name": "ChampaVeo", "lane": "cmo", "app": None}
    assert (got["1a1da50e"]["lane"], got["1a1da50e"]["name"], got["1a1da50e"]["app"]) == ("other", "TikTokWinbox", APP2)
    assert (got["43892fb5"]["lane"], got["43892fb5"]["name"]) == ("coo", "Lumina Skies")
    assert (got["4ae68058"]["lane"], got["4ae68058"]["name"]) == ("cfo", "Books + Tax")
    assert (got["3f2bd16a"]["lane"], got["3f2bd16a"]["name"]) == ("other", None)
    assert (got["757e61cc"]["lane"], got["757e61cc"]["name"]) == ("cto", None)
    assert len(got) == 7


@needs_pg
def test_unlinked_ph_leaves_out_what_is_not_a_live_ph_without_a_row(hub):
    live_host(hub.conn, "contabo")
    live_host(hub.conn, "mac", age_s=10_000)                                     # stale host
    with_ph(hub, "p1", "aaaa1111")                                               # named on a row of the payload
    with_ph(hub, "p2", "aaaa2222", stage="idea")                                 # named, but outside the monitor
    live_row(hub.conn, "contabo", "cccc3333", role="developer", name="Dev·S#ccc Org: job")
    live_row(hub.conn, "contabo", "dddd4444", role="cto", name="CTO (Kavin)")
    live_row(hub.conn, "mac", "eeee5555", name="PH#eee (CMO) - OnAStaleHost")
    live_row(hub.conn, "contabo", "ab", name="PH#ab0 (CTO) - ShortSid")           # not a sid the page accepts
    live_row(hub.conn, "contabo", "ffff6666", name="PH#fff (CTO) - Free", age_s=1000)       # row older than the ttl
    assert [u["sid"] for u in payload3()["unlinked_ph"]] == ["aaaa2222"]


@needs_pg
def test_a_ph_whose_project_is_outside_the_monitor_shows_as_unlinked_not_nowhere(hub):
    mk("p1", ph_session="aaaa1111", stage="idea")
    live_host(hub.conn)
    live_row(hub.conn, "contabo", "aaaa1111", name="🌐 PH#aaa (CTO) - InIdea")
    p = payload3()
    assert p["projects"] == [] and [u["name"] for u in p["unlinked_ph"]] == ["InIdea"]


@needs_pg
def test_unlinked_ph_is_capped_at_20_in_host_then_sid_order(hub):
    live_host(hub.conn, "contabo")
    live_host(hub.conn, "mac")
    for i in range(14):
        live_row(hub.conn, "contabo", f"c{i:07d}", name=f"PH#c{i:02d} (CTO) - C{i}")
    for i in range(11):
        live_row(hub.conn, "mac", f"b{i:07d}", name=f"PH#b{i:02d} (CMO) - B{i}")
    got = payload3()["unlinked_ph"]
    assert len(got) == 20
    assert [u["host"] for u in got] == ["contabo"] * 14 + ["mac"] * 6
    assert [u["sid"] for u in got][:3] == ["c0000000", "c0000001", "c0000002"]


@needs_pg
def test_a_name_with_control_characters_or_a_huge_project_part_is_cleaned_and_cut(hub):
    live_host(hub.conn)
    live_row(hub.conn, "contabo", "aaaa1111", name="PH#aaa (CTO) - " + "x\x07y" + "z" * 300)
    got = payload3()["unlinked_ph"][0]["name"]
    assert len(got) <= pf.MAX_PH_NAME and "\x07" not in got and got.startswith("x y")


# --- rows, size, and v3 against v2 ---------------------------------------------------------------

def many(n):
    for i in range(n):
        mk(f"p{i:02d}", lane="cto" if i % 2 else "cmo")


@needs_pg
def test_v3_shows_40_rows_and_v1_and_v2_still_20(hub):
    many(45)
    v1, v2, v3 = (pf.monitor_payload(T, version=v) for v in (1, 2, 3))
    assert (len(v1["projects"]), len(v2["projects"]), len(v3["projects"])) == (20, 20, 40)
    assert v1["counts"] == {"in_progress": 45, "parked": 0}
    assert v2["counts"]["in_progress"] == v3["counts"]["in_progress"] == 45          # counts are before the cap
    assert pf.MAX_ROWS == 20 and pf.MAX_ROWS_V3 == 40


@needs_pg
def test_a_ph_on_a_row_the_cap_cut_is_unlinked_not_hidden(hub):
    many(45)
    shown = {r["id"] for r in payload3()["projects"]}
    cut = next(f"p{i:02d}" for i in range(45) if f"p{i:02d}" not in shown)
    hub.conn.execute("UPDATE projects SET ph_session = 'aaaa1111' WHERE id = ?", (cut,))
    hub.conn.commit()
    live_host(hub.conn)
    live_row(hub.conn, "contabo", "aaaa1111", name="PH#aaa (CTO) - Cut")
    assert [u["sid"] for u in payload3()["unlinked_ph"]] == ["aaaa1111"]


@needs_pg
def test_a_full_v3_payload_stays_under_64_kb(hub):
    """40 rows and 20 unlinked, every row with a PH, a lead, a plan and a blocker, in Thai (3 bytes a
    character), with Remote Control ids as long as the real ones. The absolute worst case (every text
    field at its cap, ids at the regex's 108 characters) is about 76 KB: docs/design/portfolio-monitor-v3.md."""
    thai = "ทดสอบชื่อโปรเจคภาษาไทย" * 2                                # 44 characters
    app = "session_01" + "AbCd" * 5 + "Ef"                          # 32 characters, the real length
    live_host(hub.conn)
    for i in range(40):
        pid, sid = f"proj-{i:02d}-" + "x" * 50, f"{i:08x}"
        pf.open_project(pid, thai, "cto", actor="cto-c34459eb", stage="active", ph_session=sid,
                        owner_session="cto-f69c4825", host="contabo", now=at(1, i))
        pf.set_plan(pid, next_step=thai, next_owner=thai[:40], actor="x", now=at(2, i))
        pf.block(pid, "ceo" if i % 2 else "external", thai * 2, actor="x", now=at(2, i), ref="r" * 40)
        live_row(hub.conn, "contabo", sid, status="idle", bridge=app)
    live_row(hub.conn, "contabo", "f69c4825", role="cto", bridge=app)
    for i in range(30):
        live_row(hub.conn, "contabo", f"u{i:07d}", name="🌐 PH#u00 (CTO) - " + thai, bridge=app)
    p = payload3()
    assert len(p["projects"]) == 40 and len(p["unlinked_ph"]) == 20
    body = json.dumps(p, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    print("v3 bytes:", len(body))
    assert len(body) < 64 * 1024, len(body)


@needs_pg
def test_a_v3_row_minus_its_new_keys_is_the_v2_row(hub):
    seed_golden(hub.conn)
    v2, v3 = pf.monitor_payload(T, version=2), pf.monitor_payload(T, version=3)
    new = {"ph", "lead", "last_event_at"}
    assert v3["v"] == 3 and "unlinked_ph" in v3 and "unlinked_ph" not in v2
    assert {k for r in v3["projects"] for k in r} - {k for r in v2["projects"] for k in r} == new
    assert [{k: x for k, x in r.items() if k not in new} for r in v3["projects"][:20]] == v2["projects"]
    for key in ("counts", "attention", "orders", "generated_at"):
        assert v3[key] == v2[key]
    assert len(v3["projects"]) == 22                                  # the two the v2 cap cut are here


@needs_pg
def test_v1_and_v2_carry_no_v3_key(hub):
    seed_golden(hub.conn)
    for v in (1, 2):
        p = pf.monitor_payload(T, version=v)
        assert "unlinked_ph" not in p and not any({"ph", "lead", "last_event_at"} & set(r) for r in p["projects"])


@needs_pg
def test_an_unknown_version_is_refused(hub):
    for v in (0, 4, "3", None):
        with pytest.raises(pf.PortfolioError, match="1, 2 or 3"):
            pf.monitor_payload(T, version=v)


# --- the Run Inbox can fail without breaking anything ---------------------------------------------

@needs_pg
@pytest.mark.parametrize("exc", [ask_run.HubError("hub unreachable at https://x: timed out"), ask_run.Refused("no"),
                                 RuntimeError("boom"), OSError("down"), TimeoutError(), ValueError("x"), KeyError("k")])
def test_a_failing_run_inbox_leaves_the_payload_and_the_state_as_idle(hub, exc):
    with_ph(hub)
    hub.inbox.exc = exc
    assert row_of(payload3())["ph"]["state"] == "idle"


@needs_pg
@pytest.mark.parametrize("reply", [None, {}, [], "oops", 7, {"asks": "oops", "questions": 3}, {"asks": [1, None, "x"]},
                                   {"asks": [{"status": "pending", "requester": {"session": 5}}]},
                                   {"asks": [{"status": "pending", "requester": None}]}])
def test_a_run_inbox_that_answers_nonsense_adds_nothing(hub, reply):
    with_ph(hub)
    hub.inbox.reply = reply
    assert row_of(payload3())["ph"]["state"] == "idle"


@needs_pg
def test_one_half_of_the_run_inbox_failing_keeps_the_other(hub, monkeypatch):
    with_ph(hub)
    hub.inbox.questions.append(card("project_head-aaaa1111"))

    def asks_fail(method, path, **kw):
        if path == ask_run.ASKS_PATH:
            raise ask_run.HubError("down")
        return hub.inbox(method, path, **kw)
    monkeypatch.setattr(ask_run, "_call", asks_fail)
    assert row_of(payload3())["ph"]["state"] == "waiting"


@needs_pg
def test_a_list_reply_is_read_like_a_dict_reply(hub):
    with_ph(hub)
    hub.inbox.reply = [card("project_head-aaaa1111")]
    assert row_of(payload3())["ph"]["state"] == "waiting"


# --- the counts the CLI prints ----------------------------------------------------------------------

@needs_pg
def test_v3_counts_count_each_live_ph_once(hub):
    with_ph(hub, "p1", "aaaa0001", status="running")
    with_ph(hub, "p2", "aaaa0002", bridge=None)
    with_ph(hub, "p3", "aaaa0003", status=None)                                  # not live: not counted
    live_row(hub.conn, "contabo", "bbbb0004", name="PH#bbb (CMO) - Free", bridge=APP2)
    assert pf.v3_counts(payload3()) == {"ph_live": 3, "ph_app": 2, "unlinked": 1}


@needs_pg
def test_monitor_v3_counts_prints_numbers_only(hub, capsys):
    with_ph(hub, "p1", "aaaa0001", status="running")
    live_row(hub.conn, "contabo", "bbbb0004", name="PH#bbb (CMO) - Free", bridge=APP2)
    assert cli.run(["monitor", "--v", "3", "--counts"], now=T) == 0
    out = capsys.readouterr().out
    assert out == "ph_live=2 ph_app=2 unlinked=1\n"
    assert "session_" not in out


@needs_pg
def test_monitor_v3_prints_the_json_and_the_other_versions_still_work(hub, capsys):
    with_ph(hub, "p1", "aaaa0001", status="running")
    assert cli.run(["monitor", "--v", "3"], now=T) == 0
    assert json.loads(capsys.readouterr().out)["v"] == 3
    assert cli.run(["monitor", "--v", "2"], now=T) == 0
    assert json.loads(capsys.readouterr().out)["v"] == 2
    assert cli.run(["monitor"], now=T) == 0
    assert json.loads(capsys.readouterr().out)["v"] == 1
    assert cli.run(["monitor", "--v", "4"], now=T) == 2
    capsys.readouterr()


def test_the_pusher_sends_v2_unless_told_otherwise(monkeypatch):
    seen = []
    monkeypatch.setattr(pf, "monitor_payload", lambda *a, **kw: seen.append(kw.get("version", 1)) or {})
    for env, want in ((None, 2), ("", 2), ("2", 2), ("1", 1), ("3", 3), ("junk", 2)):
        monkeypatch.delenv("PORTFOLIO_MONITOR_V", raising=False)
        if env is not None:
            monkeypatch.setenv("PORTFOLIO_MONITOR_V", env)
        portfolio_push.build_payload()
        assert seen[-1] == want, env


# --- portfolio.py ph <project> --session <sid> ----------------------------------------------------

def ph_cmd(*argv, who=CTO):
    return cli.run(["ph", *argv], identity=who, now=T)


def link_events(conn, pid):
    return [json.loads(r["body"]) if isinstance(r["body"], str) else r["body"]
            for r in q(conn, "SELECT body FROM project_events WHERE project_id = ? AND kind = ? ORDER BY id",
                       (pid, pf.PH_LINK_EVENT_KIND))]


def ph_of(conn, pid):
    return q(conn, "SELECT ph_session FROM projects WHERE id = ?", (pid,))[0]["ph_session"]


@needs_pg
@pytest.mark.parametrize("who, lane, actor", [(CTO, "cto", "cto-c34459eb"), (CMO, "cmo", "cmo-ef04792e"),
                                              (COO, "cmo", "coo-f66280fc"), (CEO_IDENTITY, "cto", "ceo")])
def test_ph_links_the_session_and_records_who_did_it(pg, capsys, who, lane, actor):
    mk("p1", lane=lane)
    assert ph_cmd("p1", "--session", "e3050822", who=who) == 0
    assert json.loads(capsys.readouterr().out) == {"project": "p1", "ph_session": "e3050822", "from": None}
    assert ph_of(pg, "p1") == "e3050822"
    [row] = q(pg, "SELECT actor, kind FROM project_events WHERE project_id = 'p1' AND kind = ?", (pf.PH_LINK_EVENT_KIND,))
    assert row["actor"] == actor
    assert link_events(pg, "p1") == [{"op": "ph_link", "from": None, "to": "e3050822"}]


@needs_pg
def test_ph_moves_a_project_to_a_new_ph_and_drops_the_prefix(pg, capsys):
    mk("p1", ph_session="aaaa1111")
    assert ph_cmd("p1", "--session", "project_head-bbbb2222") == 0
    assert json.loads(capsys.readouterr().out)["from"] == "aaaa1111"
    assert ph_of(pg, "p1") == "bbbb2222"
    assert link_events(pg, "p1") == [{"op": "ph_link", "from": "aaaa1111", "to": "bbbb2222"}]


@needs_pg
def test_a_linked_ph_shows_on_the_page_and_leaves_unlinked_ph(hub, capsys):
    mk("p1")
    live_host(hub.conn)
    live_row(hub.conn, "contabo", "e3050822", name="🌐 PH#e30 (CTO) - Page", bridge=APP, status="idle")
    assert [u["sid"] for u in payload3()["unlinked_ph"]] == ["e3050822"]
    assert row_of(payload3())["ph"] is None
    assert ph_cmd("p1", "--session", "e3050822") == 0
    p = payload3()
    assert p["unlinked_ph"] == [] and row_of(p)["ph"]["sid"] == "e3050822" and row_of(p)["ph"]["app"] == APP


@needs_pg
@pytest.mark.parametrize("who", [PH, WORKER])
def test_a_project_head_or_a_worker_cannot_link_a_ph_even_with_enforcement_off(pg, capsys, who):
    mk("p1", ph_session="7cf528f0")                                    # PH is the project's own PH, still refused
    assert os.environ.get("ORG_PORTFOLIO_ENFORCE") is None
    assert ph_cmd("p1", "--session", "e3050822", who=who) == 1
    assert "refused" in capsys.readouterr().err
    assert ph_of(pg, "p1") == "7cf528f0" and link_events(pg, "p1") == []


@needs_pg
def test_a_project_head_gets_its_own_message(pg, capsys):
    mk("p1", ph_session="7cf528f0")
    assert ph_cmd("p1", "--session", "e3050822", who=PH) == 1
    assert "Project Head cannot link" in capsys.readouterr().err


@needs_pg
def test_the_c_level_of_another_lane_cannot_link_a_ph(pg, capsys):
    mk("p1", lane="cto")
    assert ph_cmd("p1", "--session", "e3050822", who=CMO) == 1
    assert "own lane" in capsys.readouterr().err and ph_of(pg, "p1") is None


@needs_pg
def test_ph_refusals_are_logged(pg, capsys):
    mk("p1")
    assert ph_cmd("p1", "--session", "e3050822", who=PH) == 1
    lines = cli.REFUSAL_LOG.read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["verb"] for x in lines] == ["ph"] and json.loads(lines[0])["enforced"] is True


@needs_pg
@pytest.mark.parametrize("bad", ["", "abc", "x" * 17, "ABCDEFGH", "e3050822 ", "e305_822", "../e3050822",
                                 "session_01AbCdEf", "project_head-", "é3050822"])
def test_a_bad_session_id_is_exit_2_and_is_not_echoed(pg, capsys, bad):
    mk("p1")
    assert ph_cmd("p1", "--session", bad) == 2
    err = capsys.readouterr().err
    assert "bad Project Head session id" in err
    assert "session_01AbCdEf" not in err and "../" not in err and "é" not in err
    assert ph_of(pg, "p1") is None and link_events(pg, "p1") == []


@needs_pg
def test_an_unknown_project_is_exit_2(pg, capsys):
    assert ph_cmd("nope", "--session", "e3050822") == 2
    assert capsys.readouterr().err.startswith("portfolio:")


@needs_pg
@pytest.mark.parametrize("stage", ["closed", "cancelled"])
def test_a_finished_project_cannot_get_a_new_ph(pg, capsys, stage):
    mk("p1", stage=stage)
    assert ph_cmd("p1", "--session", "e3050822") == 2
    assert stage in capsys.readouterr().err and ph_of(pg, "p1") is None


@needs_pg
def test_linking_the_same_ph_again_changes_nothing(pg, capsys):
    mk("p1", ph_session="e3050822")
    assert ph_cmd("p1", "--session", "e3050822") == 2
    assert "already has that Project Head" in capsys.readouterr().err
    assert link_events(pg, "p1") == []


@needs_pg
def test_ph_session_is_required(pg, capsys):
    mk("p1")
    assert cli.run(["ph", "p1"], identity=CTO, now=T) == 2
    assert "--session" in capsys.readouterr().err and ph_of(pg, "p1") is None
