"""Org restructure P3-B: lib/portfolio.py and tools/portfolio.py.

The first block needs no database. The rest runs against a LOCAL Postgres and self-skips
unless ORG_TEST_DB_URL is set (see tests/test_portfolio_schema.py for the setup); every test
drops the portfolio tables first (ADR 0021: never a production database)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.db_pg as db_pg  # noqa: E402
import lib.portfolio as pf  # noqa: E402
from lib import org_flags  # noqa: E402
from tools import portfolio as cli  # noqa: E402
from tools.agent_transport import CEO_IDENTITY, Identity  # noqa: E402

ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
needs_pg = pytest.mark.skipif(not ORG_TEST_DB_URL, reason="ORG_TEST_DB_URL not set (local Postgres 16)")

FIXTURE = ROOT / "docs" / "plans" / "fixtures" / "portfolio-monitor-v1.json"
STATUS_MD = ROOT / "docs" / "plans" / "org-restructure-STATUS.md"
PORTFOLIO = ("projects", "project_events", "milestones", "ceo_gos",
             "resource_locks", "post_ledger", "session_heartbeats")
UTC = timezone.utc
T = datetime(2026, 10, 14, 3, 20, tzinfo=UTC)                  # the fixture's generated_at
COO, CTO, CMO = (Identity("cxo", r, s) for r, s in (("coo", "f66280fc"), ("cto", "c34459eb"), ("cmo", "ef04792e")))
PH = Identity("cxo", "project_head", "7cf528f0")
WORKER = Identity("dev", "developer", "task-ed6c77d9")


def at(hh: int, mm: int = 0, ss: int = 0, day: int = 14) -> datetime:
    return datetime(2026, 10, day, hh, mm, ss, tzinfo=UTC)


# --- no database -------------------------------------------------------------

@pytest.mark.parametrize("done,total,want", [
    (0, 0, 0), (0, 5, 0), (5, 5, 100), (1, 3, 33), (2, 3, 67), (6, 8, 75), (4, 6, 67),
    (1, 8, 13), (3, 8, 38), (1, 200, 1), (199, 200, 100),     # halves round up, not to even
])
def test_pct_is_round_half_up_and_zero_without_milestones(done, total, want):
    assert pf.pct(done, total) == want


def test_fixture_agrees_with_the_rules():
    fx = json.loads(FIXTURE.read_text())
    rows = fx["projects"]
    for r in rows:
        assert r["pct"] == pf.pct(r["milestones"]["done"], r["milestones"]["total"])
        assert r["parked"] == (r["state"] == "parked")
    assert fx["counts"] == {"in_progress": sum(not r["parked"] for r in rows),
                            "parked": sum(r["parked"] for r in rows)}
    live = [r["last_active"] for r in rows if not r["parked"]]
    assert live == sorted(live, reverse=True) and not any(r["parked"] for r in rows[:len(live)])


STATUS_TEXT = """\
# X STATUS

| # | Milestone | State | Evidence |
|---|---|---|---|
| M1 | first | landed | abc123, PR #1 |
| M2 | has a \\| pipe | landed | PR #2 |
| M3 | landed but no evidence | landed | — |
| M4 | still open | PR ready, merge on hold | PR #3 |
| M5 | not started | open | — |

prose

| other | table |
|---|---|
| a | b |
"""


def test_parse_status_milestones_marks_done_only_with_landed_and_evidence():
    rows = pf.parse_status_milestones(STATUS_TEXT)
    assert [r["code"] for r in rows] == ["M1", "M2", "M3", "M4", "M5"]
    assert [r["done"] for r in rows] == [True, True, False, False, False]
    assert rows[1]["title"] == "M2 has a | pipe"
    assert rows[0]["evidence"] == "abc123, PR #1" and rows[2]["evidence"] == ""


def test_parse_status_md_of_org_restructure_read_only():
    before = STATUS_MD.stat().st_mtime_ns
    rows = pf.parse_status_milestones(STATUS_MD.read_text(encoding="utf-8"))
    assert len(rows) >= 15 and any(r["done"] for r in rows) and not all(r["done"] for r in rows)
    assert all(r["evidence"] for r in rows if r["done"])
    assert {"M1", "P3-A", "M6"} <= {r["code"] for r in rows}
    assert STATUS_MD.stat().st_mtime_ns == before


def test_import_status_dry_run_needs_no_hub_and_writes_nothing(monkeypatch, capsys):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    assert cli.run(["--import-status", str(STATUS_MD), "--project", "org-restructure", "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] and out["total"] >= 15 and 0 < out["done"] < out["total"]
    assert out["milestones"][0]["n"] == 1


@pytest.mark.parametrize("text,delta", [("+90m", timedelta(minutes=90)), ("+2h", timedelta(hours=2)),
                                        ("+1d", timedelta(days=1))])
def test_parse_when_relative(text, delta):
    assert cli.parse_when(text, T) == T + delta


def test_parse_when_iso_needs_a_zone():
    assert cli.parse_when("2026-10-15T09:00:00Z", T) == at(9, day=15)
    for bad in ("2026-10-15T09:00:00", "tomorrow", "+2w"):
        with pytest.raises(pf.PortfolioError):
            cli.parse_when(bad, T)


# --- who may write ------------------------------------------------------------

def _project(id_="org-restructure", name="Org restructure", lane="cto", ph=None):
    return {"id": id_, "name": name, "lane": lane, "ph_session": ph}


@pytest.fixture
def locks(tmp_path):
    (tmp_path / "project_head-7cf528f0.project").write_text("OrgRestructure")
    (tmp_path / "project_head-aaaa1111.project").write_text("Mimi Page\n")
    return tmp_path


def test_ceo_and_coo_may_write_every_project(locks):
    for who in (CEO_IDENTITY, COO):
        for verb in ("open", "stage", "milestone", "go_add", "go_use", "lock", "import"):
            assert cli.authorize(who, verb, _project(lane="cmo"), "cmo", locks) is None


def test_c_level_writes_its_own_lane_only(locks):
    assert cli.authorize(CTO, "stage", _project(lane="cto"), locks_dir=locks) is None
    assert "own lane" in cli.authorize(CTO, "stage", _project(lane="cmo"), locks_dir=locks)
    assert cli.authorize(CTO, "open", None, lane="cto", locks_dir=locks) is None
    assert cli.authorize(CTO, "open", None, lane="cmo", locks_dir=locks)
    assert cli.authorize(CMO, "go_add", _project(lane="cmo"), locks_dir=locks) is None
    assert cli.authorize(CMO, "lock", None, locks_dir=locks) is None          # a lock without a project


def test_project_head_writes_its_own_project_only(locks):
    assert cli.authorize(PH, "milestone", _project(), locks_dir=locks) is None           # by .project name
    assert cli.authorize(PH, "milestone", _project(id_="x", name="X", ph="7cf528f0"), locks_dir=locks) is None
    assert cli.authorize(PH, "milestone", _project(id_="mimi-page", name="Mimi", lane="cmo"), locks_dir=locks)
    assert cli.authorize(PH, "lock", None, locks_dir=locks) is None
    assert "cannot open" in cli.authorize(PH, "open", None, lane="cto", locks_dir=locks)
    assert "cannot open" in cli.authorize(PH, "go_add", _project(), locks_dir=locks)    # no minting its own GO
    assert cli.authorize(PH, "go_use", None, locks_dir=locks)                           # a GO of no project
    other = Identity("cxo", "project_head", "aaaa1111")
    assert cli.authorize(other, "stage", _project(id_="mimi-page", name="Mimi", lane="cmo"), locks_dir=locks) is None
    assert cli.authorize(other, "stage", _project(), locks_dir=locks)


def test_project_head_with_no_record_or_a_bad_session_owns_nothing(locks, tmp_path):
    ghost = Identity("cxo", "project_head", "deadbeef")
    assert cli.authorize(ghost, "stage", _project(), locks_dir=locks)
    evil = Identity("cxo", "project_head", "../7cf528f0")
    assert cli.authorize(evil, "stage", _project(), locks_dir=locks)


def test_workers_and_unknown_callers_are_read_only(locks):
    assert "read-only" in cli.authorize(WORKER, "milestone", _project(), locks_dir=locks)
    assert cli.authorize(None, "stage", _project(), locks_dir=locks)
    assert cli.authorize(Identity("cxo", "project_manager", "1"), "stage", _project(), locks_dir=locks)


# --- against Postgres ---------------------------------------------------------

def _drop(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for t in reversed(PORTFOLIO):
            conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        conn.execute("DROP FUNCTION IF EXISTS project_events_append_only() CASCADE")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def pg(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    for v in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", "ORG_CHARTER_GATE", "ORG_PORTFOLIO_ENFORCE"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(org_flags, "FLAGS_DIR", tmp_path / "no-flags")
    monkeypatch.setattr(cli, "REFUSAL_LOG", tmp_path / "refusals.jsonl")
    monkeypatch.setattr(cli, "LOCKS_DIR", tmp_path / "locks")
    (tmp_path / "locks").mkdir()
    db_pg.evict(ORG_TEST_DB_URL)
    _drop(ORG_TEST_DB_URL)
    db_mod.init()
    db_pg.evict(ORG_TEST_DB_URL)                  # no prepared statement survives the DROP
    conn = db_pg.connect(ORG_TEST_DB_URL, timeout=10)
    conn.execute("DELETE FROM tasks")
    conn.commit()
    yield conn
    conn.rollback()
    conn.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()
    db_pg.evict(ORG_TEST_DB_URL)
    _drop(ORG_TEST_DB_URL)


def q(conn, sql, params=()):
    rows = conn.execute(sql, params).fetchall()
    conn.commit()
    return rows


def kinds(conn, pid):
    return [r["kind"] for r in q(conn, "SELECT kind FROM project_events WHERE project_id = ? ORDER BY id", (pid,))]


def mk(pid="p1", lane="cto", stage="active", name=None, **kw):
    return pf.open_project(pid, name or pid, lane, actor="cto-c34459eb", stage=stage, now=at(1), **kw)


def beat(conn, session, pid, when):
    conn.execute("INSERT INTO session_heartbeats (session_id, project_id, at) VALUES (?, ?, ?)"
                 " ON CONFLICT (session_id) DO UPDATE SET project_id = EXCLUDED.project_id, at = EXCLUDED.at",
                 (session, pid, when))
    conn.commit()


def stamp(conn, pid, when):
    conn.execute("INSERT INTO project_events (project_id, at, kind, actor) VALUES (?, ?, 'heartbeat_rollup', 'hb')",
                 (pid, when))
    conn.commit()


def task(conn, tid, *, project="mooniex-agents", owner="7cf528f0", role="project_head", status="in_progress",
         since=at(3, 2), updated=at(3, 19)):
    conn.execute("INSERT INTO tasks (id, project, role, status, title, description, owner_cto, owner_role,"
                 " spawned_at, created_at, updated_at) VALUES (?, ?, 'developer', ?, 't', 'd', ?, ?, ?, ?, ?)",
                 (tid, project, status, owner, role, since.isoformat(), since.isoformat(), updated.isoformat()))
    conn.commit()


def state_of(pid, now=T):
    return next(r for r in pf.monitor_rows(now) if r["id"] == pid)


@needs_pg
def test_every_verb_writes_its_row_and_an_event(pg):
    a = "project_head-7cf528f0"
    p = pf.open_project("p1", "P One", "cto", actor="cto-c34459eb", goal="g", budget_usd=12.5,
                        repos=["PASAKON/Agents-Core"], ph_session="project_head-7cf528f0", now=at(1))
    assert p["stage"] == "idea" and p["repos"] == ["PASAKON/Agents-Core"] and p["ph_session"] == "7cf528f0"
    assert pf.set_stage("p1", "ready", actor=a, now=at(1, 1))["ready_at"] == at(1, 1)
    assert pf.set_stage("p1", "active", actor=a, now=at(1, 2))["stage"] == "active"
    n = pf.milestone_add("p1", "ship it", actor=a, now=at(1, 3))
    assert n == 1 and pf.milestone_add("p1", "second", actor=a, now=at(1, 3)) == 2
    pf.milestone_done("p1", 1, "sha 3b6c6bf7", actor=a, now=at(1, 4))
    pf.block("p1", "ceo", "pick one", actor=a, now=at(1, 5))
    assert q(pg, "SELECT blocker_on, blocker_what FROM projects WHERE id = 'p1'")[0]["blocker_on"] == "ceo"
    pf.unblock("p1", actor=a, now=at(1, 6))
    assert q(pg, "SELECT blocker_on FROM projects WHERE id = 'p1'")[0]["blocker_on"] is None
    pf.decided("p1", "chose the cheaper runner", actor=a, now=at(1, 7))
    g = pf.go_add("go ahead, up to $5", "run:Q-20261014-0047-6955", "spend", actor="cto-c34459eb",
                  project_id="p1", max_usd=5, now=at(1, 8))
    pf.go_use(g["go"], actor=a, now=at(1, 9))
    pf.park("p1", actor=a, reason="CEO paused it", now=at(1, 10))
    pf.close("p1", "shipped", "tests first", actor="cto-c34459eb", now=at(1, 11))

    assert kinds(pg, "p1") == ["opened", "stage", "stage", "milestone", "milestone", "milestone", "blocker",
                               "unblocked", "decided_for_ceo", "ceo_go", "ceo_go", "stage", "closed"]
    ev = q(pg, "SELECT * FROM project_events WHERE project_id = 'p1' ORDER BY id")
    assert ev[0]["actor"] == "cto-c34459eb" and ev[1]["actor"] == a and ev[-1]["actor"] == "cto-c34459eb"
    assert ev[8]["body"] == {"text": "chose the cheaper runner"}
    assert ev[-1]["body"] == {"from": "parked", "outcome": "shipped", "learning": "tests first"}
    row = q(pg, "SELECT * FROM projects WHERE id = 'p1'")[0]
    assert row["stage"] == "closed" and row["outcome"] == "shipped" and row["closed_at"] == at(1, 11)
    ms = q(pg, "SELECT n, done_at, evidence FROM milestones WHERE project_id = 'p1' ORDER BY n")
    assert ms[0]["evidence"] == "sha 3b6c6bf7" and ms[0]["done_at"] == at(1, 4) and ms[1]["done_at"] is None
    go = q(pg, "SELECT * FROM ceo_gos WHERE id = ?", (g["go"],))[0]
    assert go["used_by"] == a and go["used_at"] == at(1, 9) and float(go["max_usd"]) == 5


@needs_pg
def test_lock_rows_write_no_event(pg):
    mk()
    pf.lock_take("browser_home:contabo:3", at(4), holder="project_head-7cf528f0", project_id="p1", now=at(2))
    row = q(pg, "SELECT * FROM resource_locks")[0]
    assert (row["holder_session"], row["project_id"], row["until_at"]) == ("project_head-7cf528f0", "p1", at(4))
    assert kinds(pg, "p1") == ["opened"]
    assert pf.lock_release("browser_home:contabo:3", holder="project_head-7cf528f0") is True
    assert q(pg, "SELECT count(*) AS n FROM resource_locks")[0]["n"] == 0


@needs_pg
def test_milestone_done_without_evidence_fails_and_changes_nothing(pg):
    mk()
    pf.milestone_add("p1", "m", actor="x", now=at(1))
    for bad in (None, "", "   "):
        with pytest.raises(pf.PortfolioError, match="evidence is required"):
            pf.milestone_done("p1", 1, bad, actor="x", now=at(2))
    assert q(pg, "SELECT done_at, evidence FROM milestones")[0]["done_at"] is None
    assert kinds(pg, "p1") == ["opened", "milestone"]
    pf.milestone_done("p1", 1, "PR #1", actor="x", now=at(2))
    with pytest.raises(pf.PortfolioError, match="already done"):
        pf.milestone_done("p1", 1, "PR #2", actor="x", now=at(3))         # evidence is not overwritten
    with pytest.raises(pf.PortfolioError, match="no milestone 9"):
        pf.milestone_done("p1", 9, "PR #2", actor="x", now=at(3))
    assert q(pg, "SELECT evidence FROM milestones")[0]["evidence"] == "PR #1"


@needs_pg
def test_bad_input_and_illegal_transitions_are_refused(pg):
    mk()
    for bad in (lambda: mk("p1"), lambda: mk("Bad Id"), lambda: pf.open_project("p2", " ", "cto", actor="x"),
                lambda: pf.open_project("p2", "n", "CTO", actor="x"), lambda: pf.open_project("p2", "n", "cto", actor="x", stage="closed"),
                lambda: pf.set_stage("p1", "doing", actor="x"), lambda: pf.set_stage("p1", "closed", actor="x"),
                lambda: pf.set_stage("p1", "active", actor="x"), lambda: pf.set_stage("nope", "review", actor="x"),
                lambda: pf.block("p1", "bob", "x", actor="x"), lambda: pf.block("p1", "ceo", " ", actor="x"),
                lambda: pf.unblock("p1", actor="x"), lambda: pf.close("p1", "", "l", actor="x"),
                lambda: pf.close("p1", "o", "", actor="x"), lambda: pf.go_add("w", "sompong", "a", actor="x"),
                lambda: pf.go_add("w", "chat:cto", "a", actor="x", project_id="nope"),
                lambda: pf.go_add("w", "chat:cto", "a", actor="x", given_at=at(2), expires_at=at(1)),
                lambda: pf.lock_take("Bad Res", at(5), holder="x", now=at(2)),
                lambda: pf.lock_take("r", at(1), holder="x", now=at(2)), lambda: pf.milestone_add("p1", " ", actor="x"),
                lambda: pf.milestone_add("p1", "t", actor="x", n=0), lambda: pf.decided("p1", "", actor="x"),
                lambda: pf.go_use("nope", actor="x")):
        with pytest.raises(pf.PortfolioError):
            bad()
    pf.close("p1", "done", "l", actor="x", now=at(2))
    for bad in (lambda: pf.close("p1", "o", "l", actor="x"), lambda: pf.set_stage("p1", "active", actor="x")):
        with pytest.raises(pf.PortfolioError, match="final|already"):
            bad()
    assert kinds(pg, "p1") == ["opened", "closed"]


@needs_pg
def test_block_keeps_the_wait_clock_while_the_party_stays_and_close_clears_it(pg):
    mk()
    pf.block("p1", "ceo", "first", actor="x", now=at(1, 5))
    r = pf.block("p1", "ceo", "second wording", actor="x", now=at(2))
    assert r["since"] == "2026-10-14T01:05:00Z"
    assert pf.block("p1", "external", "vendor", actor="x", now=at(3))["since"] == "2026-10-14T03:00:00Z"
    pf.close("p1", "o", "l", actor="x", now=at(4))
    assert q(pg, "SELECT blocker_on, blocker_what, blocker_since FROM projects")[0]["blocker_on"] is None


@needs_pg
def test_concurrent_style_milestone_numbers_never_collide(pg):
    mk()
    got = [pf.milestone_add("p1", f"m{i}", actor="x", now=at(1)) for i in range(5)]
    assert got == [1, 2, 3, 4, 5]
    assert pf.milestone_add("p1", "explicit", actor="x", n=9, now=at(1)) == 9
    with pytest.raises(pf.PortfolioError, match="already has milestone 9"):
        pf.milestone_add("p1", "again", actor="x", n=9, now=at(1))
    assert pf.milestone_add("p1", "after", actor="x", now=at(1)) == 10


@needs_pg
def test_lock_semantics(pg):
    mk()
    r = "render_slot:h3"
    pf.lock_take(r, at(4), holder="project_head-aaaa1111", now=at(2))
    with pytest.raises(pf.LockHeld, match=r"held by project_head-aaaa1111 until 2026-10-14T04:00:00Z"):
        pf.lock_take(r, at(5), holder="project_head-bbbb2222", now=at(3))
    pf.lock_take(r, at(6), holder="project_head-aaaa1111", now=at(3))                  # the holder extends
    row = q(pg, "SELECT since, until_at FROM resource_locks")[0]
    assert (row["since"], row["until_at"]) == (at(2), at(6))                           # since is kept
    with pytest.raises(pf.PortfolioError, match="not project_head-bbbb2222"):
        pf.lock_release(r, holder="project_head-bbbb2222")
    pf.lock_take(r, at(9), holder="project_head-bbbb2222", now=at(7))                  # past its until: free
    assert q(pg, "SELECT holder_session FROM resource_locks")[0]["holder_session"] == "project_head-bbbb2222"
    assert pf.lock_release(r, holder="coo-f66280fc", force=True) is True               # the COO frees it
    assert pf.lock_release(r, holder="coo-f66280fc") is False                          # nothing to free
    with pytest.raises(pf.PortfolioError, match="no such project"):
        pf.lock_take(r, at(9), holder="x", project_id="nope", now=at(7))


@needs_pg
def test_a_go_is_used_once_and_not_after_it_expires(pg):
    mk()
    g = pf.go_add("ok", "chat:cto-c34459eb", "spend", actor="cto", go_id="GO-1", project_id="p1",
                  expires_at=at(5), now=at(1))
    assert g["go"] == "GO-1" and kinds(pg, "p1") == ["opened", "ceo_go"]
    assert pf.go_project("GO-1") == "p1"
    assert pf.go_use("GO-1", actor="ph", now=at(2))["project"] == "p1"
    with pytest.raises(pf.PortfolioError, match="already used"):
        pf.go_use("GO-1", actor="ph", now=at(3))
    pf.go_add("ok", "run:RUN-20261014-0219-f576", "x", actor="cto", go_id="GO-2", expires_at=at(5), now=at(1))
    with pytest.raises(pf.PortfolioError, match="expired"):
        pf.go_use("GO-2", actor="ph", now=at(6))
    pf.go_add("ok", "chat:cto", "x", actor="cto", go_id="GO-3", now=at(1))             # no project: no event
    assert pf.go_use("GO-3", actor="ph", now=at(2))["project"] is None
    with pytest.raises(pf.PortfolioError, match="already exists"):
        pf.go_add("ok", "chat:cto", "x", actor="cto", go_id="GO-3", now=at(1))
    assert kinds(pg, "p1") == ["opened", "ceo_go", "ceo_go"]


@needs_pg
def test_go_add_runs_the_verify_hook_before_writing(pg):
    seen = []

    def refuse(source):
        seen.append(source)
        raise pf.PortfolioError("Run Inbox has no such card")
    with pytest.raises(pf.PortfolioError, match="no such card"):
        pf.go_add("w", "run:Q-1", "a", actor="x", go_id="GO-9", verify=refuse, now=at(1))
    assert seen == ["run:Q-1"] and q(pg, "SELECT count(*) AS n FROM ceo_gos")[0]["n"] == 0


@needs_pg
def test_import_milestones_runs_once(pg):
    mk()
    rows = pf.parse_status_milestones(STATUS_TEXT)
    assert pf.import_milestones("p1", rows, actor="coo-f66280fc", source="STATUS.md", now=at(2)) == \
        {"project": "p1", "total": 5, "done": 2}
    ms = q(pg, "SELECT n, title, done_at, evidence FROM milestones ORDER BY n")
    assert [m["n"] for m in ms] == [1, 2, 3, 4, 5] and ms[0]["title"] == "M1 first"
    assert [m["done_at"] is not None for m in ms] == [True, True, False, False, False]
    assert ms[2]["evidence"] is None
    assert kinds(pg, "p1") == ["opened", "milestone"]
    assert q(pg, "SELECT body FROM project_events WHERE kind = 'milestone'")[0]["body"]["op"] == "import"
    with pytest.raises(pf.PortfolioError, match="runs once"):
        pf.import_milestones("p1", rows, actor="x", source="STATUS.md", now=at(3))
    mk("p2")
    with pytest.raises(pf.PortfolioError, match="no milestone rows"):
        pf.import_milestones("p2", [], actor="x", source="s")


# --- the monitor --------------------------------------------------------------

@needs_pg
def test_state_precedence_first_match_wins(pg):
    mk(ph_session="7cf528f0")
    pf.park("p1", actor="x", now=at(2))
    pf.block("p1", "ceo", "x", actor="x", now=at(2, 30))
    task(pg, "task-1")
    beat(pg, "s1", "p1", at(3, 19))
    assert state_of("p1")["state"] == "parked"                                    # parked beats all
    pf.set_stage("p1", "active", actor="x", now=at(2, 40))
    assert state_of("p1")["state"] == "waiting_ceo"                               # blocker on ceo beats the rest
    pf.block("p1", "external", "x", actor="x", now=at(2, 50))
    assert state_of("p1")["state"] == "waiting"
    pf.unblock("p1", actor="x", now=at(3))
    assert state_of("p1")["state"] == "generating"                                # a running task beats a heartbeat
    pg.execute("UPDATE tasks SET status = 'done'")
    pg.commit()
    r = state_of("p1")
    assert r["state"] == "working"                                                # heartbeat 1 min old
    beat(pg, "s1", "p1", at(3, 14, 59))                                           # 5 min 1 s old
    assert state_of("p1")["state"] == "idle"
    beat(pg, "s1", "p1", T - timedelta(hours=24, seconds=1))
    assert state_of("p1")["state"] == "stalled"
    pg.execute("DELETE FROM session_heartbeats")
    pg.commit()
    assert state_of("p1")["state"] == "stalled"                                   # no heartbeat at all


@needs_pg
def test_working_edge_is_five_minutes(pg):
    mk()
    beat(pg, "s1", "p1", T - timedelta(seconds=300))
    assert state_of("p1")["state"] == "working"
    beat(pg, "s1", "p1", T - timedelta(seconds=301))
    assert state_of("p1")["state"] == "idle"


@needs_pg
def test_generating_matches_the_owner_ph_session_or_the_project_key_only_while_fresh(pg):
    mk("p1", ph_session="7cf528f0")
    mk("p2")
    mk("p3", ph_session="aaaa1111")
    mk("p4", ph_session="bbbb2222")
    task(pg, "t-ph", owner="7cf528f0")                                            # owned by p1's PH
    task(pg, "t-key", project="p2", owner=None, role=None)                        # tasks.project == p2's id
    task(pg, "t-done", owner="aaaa1111", status="review")                         # not running
    task(pg, "t-cto", owner="bbbb2222", role="cto")                               # owner_role is not a PH
    assert state_of("p1")["state"] == "generating" and state_of("p1")["state_since"] == "2026-10-14T03:02:00Z"
    assert state_of("p2")["state"] == "generating"
    assert state_of("p3")["state"] == "stalled" and state_of("p4")["state"] == "stalled"
    pg.execute("UPDATE tasks SET updated_at = ? WHERE id IN ('t-ph', 't-key')", ((T - timedelta(days=2)).isoformat(),))
    pg.commit()
    assert state_of("p1")["state"] == "stalled" and state_of("p2")["state"] == "stalled"   # a row nobody touched lies


@needs_pg
def test_only_active_review_and_parked_projects_are_listed(pg):
    for stage in ("idea", "brainstorm", "ready", "active", "review", "parked"):
        pf.open_project(f"p-{stage}", stage, "cto", actor="x", stage=stage, now=at(1))
    pf.open_project("p-closed", "closed", "cto", actor="x", now=at(1))
    pf.close("p-closed", "o", "l", actor="x", now=at(1, 1))
    pf.open_project("p-cancelled", "cancelled", "cto", actor="x", now=at(1))
    pf.set_stage("p-cancelled", "cancelled", actor="x", now=at(1, 1))
    assert sorted(r["id"] for r in pf.monitor_rows(T)) == ["p-active", "p-parked", "p-review"]
    assert pf.monitor_payload(T)["counts"] == {"in_progress": 2, "parked": 1}


@needs_pg
def test_pct_comes_from_milestones_with_evidence(pg):
    mk()
    assert state_of("p1")["pct"] == 0 and state_of("p1")["milestones"] == {"done": 0, "total": 0}
    for i in range(8):
        pf.milestone_add("p1", f"m{i}", actor="x", now=at(1))
    pf.milestone_done("p1", 1, "sha 1", actor="x", now=at(1, 1))
    r = state_of("p1")
    assert (r["pct"], r["milestones"]) == (13, {"done": 1, "total": 8})             # 12.5 rounds up
    pf.milestone_done("p1", 2, "sha 2", actor="x", now=at(1, 2))
    assert state_of("p1")["pct"] == 25


@needs_pg
def test_the_blocker_text_never_reaches_the_monitor(pg):
    mk()
    secret = "log in to account SECRET-ACCT-9f3 and approve invoice"
    pf.block("p1", "ceo", secret, actor="x", now=at(2))
    pf.decided("p1", "decided about SECRET-ACCT-9f3", actor="x", now=at(2, 1))
    blob = json.dumps(pf.monitor_payload(T), ensure_ascii=False)
    assert "SECRET-ACCT" not in blob and "approve invoice" not in blob
    r = state_of("p1")
    assert r["blocker"] == {"on": "ceo", "since": "2026-10-14T02:00:00Z"} and set(r["blocker"]) == {"on", "since"}
    assert q(pg, "SELECT blocker_what FROM projects")[0]["blocker_what"] == secret      # the text is kept, not shown


@needs_pg
def test_at_most_twenty_rows_non_parked_first_by_last_active(pg):
    for i in range(22):
        mk(f"live-{i:02d}")
        pg.execute("UPDATE projects SET last_active = ? WHERE id = ?", (at(2) + timedelta(minutes=i), f"live-{i:02d}"))
    for i in range(3):
        mk(f"park-{i}")
        pf.park(f"park-{i}", actor="x", now=at(3, i))
        pg.execute("UPDATE projects SET last_active = ? WHERE id = ?", (at(3, 10 + i), f"park-{i}"))
    pg.commit()
    payload = pf.monitor_payload(T)
    ids = [r["id"] for r in payload["projects"]]
    assert len(ids) == 20 and ids == [f"live-{i:02d}" for i in range(21, 1, -1)]
    assert payload["counts"] == {"in_progress": 22, "parked": 3}                       # counts are before the cap
    assert len(pf.monitor_rows(T)) == 20
    for i in range(12, 22):                                                           # 12 live rows left over
        pg.execute("UPDATE projects SET stage = 'closed' WHERE id = ?", (f"live-{i:02d}",))
    pg.commit()
    ids = [r["id"] for r in pf.monitor_rows(T)]
    assert ids[:12] == [f"live-{i:02d}" for i in range(11, -1, -1)]
    assert ids[12:] == ["park-2", "park-1", "park-0"]                                 # parked last, newest first


@needs_pg
def test_active_today_counts_from_midnight_bangkok_and_only_short_gaps(pg):
    mk()
    midnight = datetime(2026, 10, 13, 17, 0, tzinfo=UTC)                              # 00:00 on 14 Oct, UTC+7
    stamp(pg, "p1", midnight - timedelta(minutes=1))                                  # 23:59 yesterday: excluded
    stamp(pg, "p1", midnight + timedelta(minutes=2))                                  # starts the first run
    stamp(pg, "p1", midnight + timedelta(minutes=6))                                  # +4 min
    stamp(pg, "p1", midnight + timedelta(minutes=11))                                 # +5 min (still one run)
    stamp(pg, "p1", midnight + timedelta(minutes=30))                                 # 19 min gap: a break
    stamp(pg, "p1", midnight + timedelta(minutes=33))                                 # +3 min
    assert state_of("p1")["active_today_s"] == (4 + 5 + 3) * 60
    assert state_of("p1", midnight + timedelta(hours=1))["active_today_s"] == (4 + 5 + 3) * 60
    assert state_of("p1", midnight + timedelta(minutes=10))["active_today_s"] == 4 * 60   # later stamps are the future
    assert state_of("p1", midnight - timedelta(seconds=1))["active_today_s"] == 0         # still yesterday


@needs_pg
def test_working_state_since_is_where_the_current_run_began(pg):
    mk()
    for m in (140, 150, 160, 170, 175):                                               # minutes before T
        stamp(pg, "p1", T - timedelta(minutes=m))
    for m in (60, 56, 52, 5, 1):
        stamp(pg, "p1", T - timedelta(minutes=m))
    beat(pg, "s1", "p1", T - timedelta(minutes=1))
    r = state_of("p1")
    assert r["state"] == "working" and r["state_since"] == pf.iso(T - timedelta(minutes=5))


@needs_pg
def test_monitor_payload_equals_the_fixture_for_the_same_state(pg):
    """Seed the four projects of docs/plans/fixtures/portfolio-monitor-v1.json and read them back."""
    a, b = "x", "y"
    # black-liquidity: generating, 6 of 8, 100 min of 5-minute activity ending 03:19:40
    pf.open_project("black-liquidity", "BLACK LIQUIDITY", "cmo", actor=a, stage="active",
                    ph_session="aaaa1111", now=at(10, day=13))
    for i in range(8):
        pf.milestone_add("black-liquidity", f"m{i}", actor=a, now=at(10, 1, day=13))
    for i in range(1, 7):
        pf.milestone_done("black-liquidity", i, f"sha {i}", actor=a, now=at(10, 2, day=13))
    for k in range(21):
        stamp(pg, "black-liquidity", at(3, 19, 40) - timedelta(seconds=300 * k))
    task(pg, "task-bl", owner="aaaa1111", since=at(3, 2), updated=at(3, 19))
    # org-restructure: waiting on the CEO since 02:40, 4 of 6, 70 min of activity ending 03:10
    pf.open_project("org-restructure", "Org restructure", "cto", actor=a, stage="active", now=at(10, day=13))
    for i in range(6):
        pf.milestone_add("org-restructure", f"m{i}", actor=a, now=at(10, 1, day=13))
    for i in range(1, 5):
        pf.milestone_done("org-restructure", i, f"sha {i}", actor=a, now=at(10, 2, day=13))
    pf.block("org-restructure", "ceo", "pick a card", actor=a, now=at(2, 40))
    for k in range(15):
        stamp(pg, "org-restructure", at(2, 0) + timedelta(minutes=5 * k))
    # mimi-page: idle, last seen 01:00
    pf.open_project("mimi-page", "Mimi", "cmo", actor=a, stage="active", now=at(10, day=13))
    beat(pg, "mimi", "mimi-page", at(1, 0))
    # film-2: parked on 8 Oct, 1 of 10
    pf.open_project("film-2", "Film 2 (8 min)", "cmo", actor=a, stage="active", now=at(8, day=8))
    for i in range(10):
        pf.milestone_add("film-2", f"m{i}", actor=a, now=at(8, 1, day=8))
    pf.milestone_done("film-2", 1, "drive id 1", actor=a, now=at(8, 2, day=8))
    pf.park("film-2", actor=a, now=at(9, day=8))
    assert pf.monitor_payload(T) == json.loads(FIXTURE.read_text())


def _shape(v):
    if isinstance(v, dict):
        return {k: _shape(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_shape(x) for x in v[:1]]
    return type(v).__name__


@needs_pg
def test_payload_has_the_fixture_keys_and_types(pg):
    fx = json.loads(FIXTURE.read_text())
    mk("a", "cmo")
    mk("b", "cto")
    mk("c")
    pf.milestone_add("a", "m", actor="x", now=at(1))
    pf.block("b", "resource", "slot busy", actor="x", now=at(2))
    pf.park("c", actor="x", now=at(2))
    payload = pf.monitor_payload(T)
    assert list(payload) == list(fx) and payload["v"] == 1
    assert _shape({k: v for k, v in payload.items() if k != "projects"}) == \
        _shape({k: v for k, v in fx.items() if k != "projects"})
    blocked = next(r for r in fx["projects"] if r["blocker"])
    plain = next(r for r in fx["projects"] if not r["blocker"])
    assert len(payload["projects"]) == 3
    for row in payload["projects"]:
        want = blocked if row["blocker"] else plain
        assert list(row) == list(want)                                        # same keys, same order
        assert _shape(row) == _shape(want)                                    # same types, blocker included
        assert row["state"] in {"working", "generating", "waiting_ceo", "waiting", "idle", "stalled", "parked"}
        assert row["blocker"] is None or set(row["blocker"]) == {"on", "since"}
    json.dumps(payload)                                                       # serialisable as is


# --- the command line ----------------------------------------------------------

def cmd(*argv, who=CEO_IDENTITY):
    return cli.run(list(argv), identity=who, now=T)


@needs_pg
def test_cli_verbs_round_trip(pg, capsys):
    assert cmd("open", "p1", "--name", "P One", "--lane", "cto", "--stage", "active", "--repos", "PASAKON/Agents-Core, PASAKON/Console") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "p1" and out["repos"] == ["PASAKON/Agents-Core", "PASAKON/Console"]
    assert cmd("milestone", "add", "p1", "first thing") == 0 and json.loads(capsys.readouterr().out) == {"project": "p1", "n": 1}
    assert cmd("milestone", "done", "p1", "1", "--evidence", "sha abc") == 0
    assert cmd("block", "p1", "--on", "ceo", "--what", "pick one") == 0
    assert cmd("unblock", "p1") == 0
    assert cmd("decided", "p1", "used the cheaper runner") == 0
    assert cmd("go", "add", "--words", "go", "--source", "chat:cto-c34459eb", "--action", "spend", "--id", "GO-1",
               "--project", "p1", "--max-usd", "3", "--expires-at", "+1d") == 0
    assert cmd("go", "use", "GO-1") == 0
    assert cmd("lock", "take", "browser_home:contabo:3", "--until", "+2h", "--project", "p1") == 0
    assert cmd("lock", "release", "browser_home:contabo:3") == 0
    assert cmd("stage", "p1", "review") == 0
    assert cmd("park", "p1", "--reason", "paused") == 0
    assert cmd("close", "p1", "--outcome", "shipped", "--learning", "ok") == 0
    capsys.readouterr()
    assert kinds(pg, "p1") == ["opened", "milestone", "milestone", "blocker", "unblocked", "decided_for_ceo",
                               "ceo_go", "ceo_go", "stage", "stage", "closed"]
    assert {r["actor"] for r in q(pg, "SELECT actor FROM project_events")} == {"ceo"}
    assert cmd("show") == 0 and json.loads(capsys.readouterr().out)["projects"][0]["id"] == "p1"
    assert cmd("show", "p1") == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["pct"] == 100 and shown["milestones"][0]["evidence"] == "sha abc" and len(shown["events"]) == 11


@needs_pg
def test_cli_monitor_prints_the_payload(pg, capsys):
    mk()
    assert cmd("monitor", who=WORKER) == 0                                   # reads need no write right
    out = json.loads(capsys.readouterr().out)
    assert out["v"] == 1 and out["projects"][0]["id"] == "p1"


@needs_pg
def test_cli_errors_exit_2_with_one_line(pg, capsys):
    assert cmd("stage", "nope", "review") == 2
    assert "no such project" in capsys.readouterr().err
    mk()
    assert cmd("milestone", "done", "p1", "1", "--evidence", "x") == 2
    assert cmd("lock", "take", "r", "--until", "soon") == 2
    assert "bad time" in capsys.readouterr().err
    assert cmd("block", "p1", "--on", "bob", "--what", "x") == 2          # argparse choices
    assert cmd() == 2


@needs_pg
def test_a_refusal_is_logged_and_allowed_while_the_flag_is_off(pg, capsys, tmp_path):
    mk()
    assert cmd("milestone", "add", "p1", "by a worker", who=WORKER) == 0
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "would be refused" in err and "read-only" in err
    assert q(pg, "SELECT count(*) AS n FROM milestones")[0]["n"] == 1             # the write went ahead
    assert q(pg, "SELECT actor FROM project_events WHERE kind = 'milestone'")[0]["actor"] == "developer-task-ed6c77d9"
    log = [json.loads(x) for x in (tmp_path / "refusals.jsonl").read_text().splitlines()]
    assert len(log) == 1 and log[0]["verb"] == "milestone" and log[0]["actor"] == "developer-task-ed6c77d9"
    assert log[0]["enforced"] is False and log[0]["project"] == "p1"


@needs_pg
def test_a_refusal_is_final_once_the_flag_is_on(pg, capsys, monkeypatch, tmp_path):
    mk()
    monkeypatch.setenv("ORG_PORTFOLIO_ENFORCE", "1")
    assert cmd("milestone", "add", "p1", "by a worker", who=WORKER) == 1
    err = capsys.readouterr().err
    assert "refused" in err and "would be" not in err
    assert cmd("open", "p2", "--name", "P2", "--lane", "cmo", who=CTO) == 1             # not CTO's lane
    assert cmd("go", "add", "--words", "go", "--source", "chat:x", "--action", "a", who=PH) == 1
    assert q(pg, "SELECT count(*) AS n FROM milestones")[0]["n"] == 0
    assert q(pg, "SELECT count(*) AS n FROM projects")[0]["n"] == 1
    assert json.loads((tmp_path / "refusals.jsonl").read_text().splitlines()[0])["enforced"] is True
    assert cmd("milestone", "add", "p1", "by the CEO") == 0                              # allowed callers still work
    assert cmd("open", "p3", "--name", "P3", "--lane", "cto", who=CTO) == 0


@needs_pg
def test_enforced_project_head_writes_only_its_own_project(pg, monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_PORTFOLIO_ENFORCE", "1")
    (tmp_path / "locks" / "project_head-7cf528f0.project").write_text("OrgRestructure")
    mk("org-restructure", name="Org restructure")
    mk("mimi-page", "cmo", name="Mimi")
    assert cmd("milestone", "add", "org-restructure", "mine", who=PH) == 0
    assert cmd("milestone", "add", "mimi-page", "not mine", who=PH) == 1
    assert cmd("lock", "take", "browser_home:contabo:3", "--until", "+1h", who=PH) == 0
    assert q(pg, "SELECT holder_session FROM resource_locks")[0]["holder_session"] == "project_head-7cf528f0"
    assert cmd("lock", "release", "browser_home:contabo:3", who=PH) == 0
    assert [r["actor"] for r in q(pg, "SELECT actor FROM project_events WHERE kind = 'milestone'")] == ["project_head-7cf528f0"]


@needs_pg
def test_cli_import_status_writes_once(pg, tmp_path, capsys):
    mk("org-restructure")
    f = tmp_path / "S.md"
    f.write_text(STATUS_TEXT)
    assert cmd("--import-status", str(f), "--project", "org-restructure") == 0
    assert json.loads(capsys.readouterr().out) == {"project": "org-restructure", "total": 5, "done": 2}
    assert cmd("--import-status", str(f), "--project", "org-restructure") == 2
    assert "runs once" in capsys.readouterr().err
    assert cmd("--import-status", str(f)) == 2                                       # needs --project
    assert cmd("--import-status", str(tmp_path / "missing.md"), "--project", "org-restructure") == 2
    assert state_of("org-restructure")["pct"] == 40


def test_without_the_hub_a_write_says_so_in_one_line(monkeypatch, capsys):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    assert cmd("open", "p1", "--name", "P", "--lane", "cto") == 2
    assert "ORG_DB_URL is unset" in capsys.readouterr().err
    with pytest.raises(pf.PortfolioError, match="ORG_DB_URL is unset"):
        pf.monitor_payload(T)
