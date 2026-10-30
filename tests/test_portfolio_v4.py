"""Synthetic v4 wire-contract coverage; optional PostgreSQL integration."""
import copy
import json
from datetime import timedelta

import pytest

from lib import config, portfolio as pf
from tools import host_fill, live_sessions, portfolio_push
from test_portfolio import T, needs_pg, pg
from test_portfolio_monitor_v3 import hub, seed_golden


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, tasks=(), waiting=()):
        self.tasks, self.waiting = tasks, waiting

    def execute(self, sql, params=()):
        return Rows(self.waiting if "count(*)" in sql else self.tasks)


def work(i=0, status="pending", owner="aaaa1111", age=0):
    return dict(id=str(i), owner_cto=owner, title="Synthetic task", status=status, host="node-a",
                created_at=T + timedelta(seconds=i), updated_at=T - timedelta(days=age))


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "self_host", lambda: "node-a")
    monkeypatch.setattr(pf, "_live_by_sid", lambda c: {})
    monkeypatch.setattr(live_sessions, "_snapshot_from_hub", lambda *a: {"rows": []})
    monkeypatch.setattr(host_fill, "collect", lambda: [])
    return tmp_path


def extend(tasks, stage="active", extra_projects=None):
    projects = {"sample": dict(ph_session="aaaa1111", opened_at=T, stage=stage)}
    projects.update(extra_projects or {})
    rows = [dict(id="sample", ph={"sid": "aaaa1111"})]
    extra = pf._v4_extend(rows, projects, Connection(tasks), T)
    return rows[0], extra


@pytest.mark.parametrize("status,state", list(pf._WORK_STATES.items()))
def test_worker_states_and_exact_keys(isolated, status, state):
    row, extra = extend([work(status=status)])
    assert row["workers"] == [{"title": "Synthetic task", "state": state, "host": "node-a"}]
    assert row["review_n"] == int(status == "review")
    assert row["opened_at"] == pf.iso(T)
    assert set(extra) == {"clevel_work", "hosts", "parked_ph"}


@pytest.mark.parametrize("stage,want", [(s, s) for s in ("active", "parked", "ready", "closed")] + [("review", "other")])
def test_stage_mapping(isolated, stage, want):
    assert extend([], stage)[0]["stage"] == want


def test_workers_caps_age_owner_review_and_text(isolated):
    tasks = [work(i, "review", "project_head-aaaa1111") for i in range(12)]
    tasks += [work(20, "review", age=8), work(21, owner="bbbb2222")]
    tasks[11].update(title="\x00" + "界" * 80, host="BAD HOST")
    row, _ = extend(tasks)
    assert len(row["workers"]) == 8 and row["review_n"] == 13
    assert row["workers"][0] == {"title": "界" * 60, "state": "review", "host": None}


def test_clevel_work_excludes_all_ph_owners_and_review_and_old(isolated):
    tasks = [work(i, owner="cto-fresh") for i in range(25)]
    tasks += [work(99, owner="cmo-bbbb2222"), work(98, "review", "cgo-fresh"),
              work(97, owner="coo-fresh", age=8), work(96, owner="developer-free")]
    _, extra = extend(tasks, extra_projects={"hidden": {"ph_session": "bbbb2222"}})
    assert len(extra["clevel_work"]) == 20
    assert {r["lane"] for r in extra["clevel_work"]} == {"cto"}
    assert extra["clevel_work"][0] == dict(lane="cto", title="Synthetic task", state="queued",
                                           host="node-a", created_at=pf.iso(T + timedelta(seconds=24)))


def test_parked_caps_patterns_and_live_skip(isolated):
    locks = isolated / "state" / "locks"
    locks.mkdir(parents=True)
    for i in range(25):
        (locks / f"project_head-{i:08d}.project.parked").write_text("sample\n")
    (locks / "project_head-invalid!.project.parked").write_text("sample")
    (locks / "project_head-00000001.project.parked").write_text("INVALID")
    rows = pf._v4_parked({"00000000": {}})
    assert len(rows) == 20 and rows[0] == {"sid": "00000001", "project": None, "host": "node-a"}
    assert rows[-1]["sid"] == "00000020"


def test_hosts_exact_keys_caps_counts_and_failure(isolated, monkeypatch):
    monkeypatch.setattr(host_fill, "collect", lambda: [dict(name=f"node-{i}", online=True, fill_pct=1200,
                         highest="load", ram_free_gb=2.5, disk_free_gb=10) for i in reversed(range(7))])
    monkeypatch.setattr(live_sessions, "_snapshot_from_hub", lambda *a: {"rows": [
        dict(host="node-0", stale=False), dict(host="node-0", stale=True)]})
    rows = pf._v4_hosts(Connection(waiting=[dict(host="node-0", n=3)]))
    assert len(rows) == 5
    assert rows[0] == dict(name="node-0", online=True, fill_pct=999, fill_basis="load",
                           ram_free_gb=2.5, disk_free_gb=10.0, waiting_host=3, sessions=1)
    def fail():
        raise RuntimeError("unavailable")
    monkeypatch.setattr(host_fill, "collect", fail)
    assert pf._v4_hosts(Connection()) == []


def size(payload):
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())


@pytest.mark.parametrize("os_name,basis", [("linux", "load"), ("darwin", "load"), ("windows", "cpu")])
def test_host_cpu_basis_and_missing_numbers(isolated, monkeypatch, os_name, basis):
    monkeypatch.setattr(config, "hosts", lambda: {"node-a": {"os": os_name}})
    monkeypatch.setattr(host_fill, "collect", lambda: [dict(name="node-a", highest="cpu", fill_pct=25.5,
                                                          ram_free_gb=float("nan"))])
    row = pf._v4_hosts(Connection())[0]
    assert row["fill_basis"] == basis and row["fill_pct"] == 26
    assert row["ram_free_gb"] is None and row["disk_free_gb"] is None


def test_size_drop_order_and_failure(monkeypatch):
    payload = dict(projects=[dict(id="new", opened_at="2026-02-01", workers=["界" * 200]),
                             dict(id="old", opened_at="2026-01-01", workers=["界" * 200])],
                   clevel_work=["界" * 200])
    expected = copy.deepcopy(payload)
    expected["projects"][1]["workers"] = []
    monkeypatch.setattr(pf, "MAX_BODY", size(expected))
    pf._v4_limit(payload)
    assert payload == expected
    expected["projects"][0]["workers"] = []
    monkeypatch.setattr(pf, "MAX_BODY", size(expected))
    pf._v4_limit(payload)
    assert payload == expected
    expected["clevel_work"] = []
    monkeypatch.setattr(pf, "MAX_BODY", size(expected))
    pf._v4_limit(payload)
    assert payload == expected
    monkeypatch.setattr(pf, "MAX_BODY", size(expected) - 1)
    with pytest.raises(pf.PortfolioError, match="128 KB"):
        pf._v4_limit(payload)


def test_real_body_cap():
    assert pf.MAX_BODY == 128 * 1024
    payload = dict(projects=[dict(id=str(i), opened_at=str(i), workers=["界" * 600] * 8)
                             for i in range(40)], clevel_work=["界" * 60] * 20)
    pf._v4_limit(payload)
    assert size(payload) <= 128 * 1024


def test_app_identifiers_only_survive_in_app_fields():
    app = "session" + "_" + "Synthetic123"
    assert pf._v4_public({"app": app, "name": app, "nested": [{"title": "a\x00b"}]}) == {
        "app": app, "name": "", "nested": [{"title": "ab"}]}


@pytest.mark.parametrize("by,want", [(None, None), ("cto-fresh", "cto"), ("bad_role-box", "other"),
                                    ("cfo-box", "cfo")])
@pytest.mark.parametrize("stage,offset,closed", [("closed", 0, True), ("closed", -1, False),
                                              ("active", 1, False)])
def test_order_fields_in_payload(isolated, monkeypatch, by, want, stage, offset, closed):
    order = dict(id="order-example", words="Synthetic order", project_id="sample", taken_by=by,
                 taken_at=T, closed_at=None, due_at=None)
    class Orders(Connection):
        def execute(self, sql, params=()):
            return Rows([order] if sql.startswith("SELECT * FROM orders") else [])
    monkeypatch.setattr(pf, "_v2_rows", lambda *a: ([], {"sample": dict(
        stage=stage, closed_at=T + timedelta(seconds=offset), ph_session=None)}, [], {}))
    monkeypatch.setattr(pf, "_order_progress", lambda *a: ("queued", 0))
    payload = pf.monitor_payload(T, conn=Orders(), version=4)
    assert payload["orders"][0]["by"] == want
    assert payload["orders"][0]["project_closed"] is closed
    assert set(payload) == {"v", "generated_at", "counts", "attention", "projects", "orders",
                            "unlinked_ph", "clevel_work", "hosts", "parked_ph"}


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_empty_payload_bytes(monkeypatch, version):
    monkeypatch.setattr(pf, "_monitor_all", lambda *a: [])
    monkeypatch.setattr(pf, "_v2_rows", lambda *a: ([], {}, [], {}))
    monkeypatch.setattr(pf, "_live_by_sid", lambda c: {})
    monkeypatch.setattr(pf, "_in_flight_owners", lambda c: set())
    def unexpected(*a):
        pytest.fail("legacy version called v4")
    monkeypatch.setattr(pf, "_v4_extend", unexpected)
    counts = dict(in_progress=0, parked=0)
    expected = dict(v=version, generated_at=pf.iso(T), counts=counts)
    if version >= 2:
        counts.update(late=0, waiting_ceo=0, no_plan=0)
        expected["attention"] = []
    expected["projects"] = []
    if version >= 2:
        expected["orders"] = []
    if version == 3:
        expected["unlinked_ph"] = []
    assert json.dumps(pf.monitor_payload(T, conn=Connection(), version=version)) == json.dumps(expected)


@pytest.mark.parametrize("value,want", [(None, 2), ("1", 1), ("2", 2), ("3", 3), ("4", 4)])
def test_pusher_versions(monkeypatch, value, want):
    monkeypatch.delenv("PORTFOLIO_MONITOR_V", raising=False)
    if value:
        monkeypatch.setenv("PORTFOLIO_MONITOR_V", value)
    monkeypatch.setattr(pf, "monitor_payload", lambda version=1: version)
    assert portfolio_push.build_payload() == want


@needs_pg
def test_integration_orders_and_legacy_bytes(hub, isolated):
    seed_golden(hub.conn)
    before = {v: json.dumps(pf.monitor_payload(T, version=v), sort_keys=True) for v in (1, 2, 3)}
    payload = pf.monitor_payload(T, version=4)
    assert payload["v"] == 4 and len(payload["projects"]) == 22
    assert all(o["by"] == "cto" and o["project_closed"] is False for o in payload["orders"])
    assert {v: json.dumps(pf.monitor_payload(T, version=v), sort_keys=True) for v in (1, 2, 3)} == before
    pf.close("p01", "complete", "synthetic lesson", actor="cto-fresh", now=T)
    payload = pf.monitor_payload(T, version=4)
    assert next(o for o in payload["orders"] if o["project_id"] == "p01")["project_closed"] is True
