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

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.portfolio as pf  # noqa: E402
from test_portfolio import (  # noqa: E402, F401  (pg is a fixture, used by name)
    COO, CTO, CMO, PH, WORKER, T, at, kinds, mk, needs_pg, pg, q, task,
)
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
