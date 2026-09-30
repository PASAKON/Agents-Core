"""Org Mesh W2.6 / PLAN-auto-dispatch H2 (task-10136806): lib/router.pick_host and
the host-resolution block in tools/delegate.py, behind env ORG_HOST_ROUTER.

  * flag off       -> today's `host= arg > tasks.host > self_host()`, pick_host never called
  * explicit host / tasks.host win (flag on too) and the log says `manual:`
  * each filter (stale probe, status, provides, full, no project path, no usable
    runner, no load reading) rejects a host on its own
  * lowest load_per_core wins; ties break on ram_free_gb desc, then name
  * no match -> task stays pending, `no_host: <reason per host>`, no spawn
  * the chosen host reaches `_route_runner` and the spawn

Fakes only: a tmp_path ledger for `hosts` rows, config.hosts/projects patched for
the unit tests, `_route_runner` / `_spawn_remote` / `_remote_free_gb` replaced in
the delegate flow. No ssh, no real tasks.db, no quota read.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import lib.config as config
import lib.db as db_mod
import lib.router as router
import tools.delegate as delegate

NOW = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
FRESH = (NOW - timedelta(seconds=5)).isoformat(timespec="seconds")
STALE = "no probe ≤60 s"

HOSTS = {"mac": {}, "winbox": {}, "contabo": {}}
PROJECTS = {
    "proj": {"path": "/m", "paths": {"winbox": "/w", "contabo": "/c"}},
    "nocontabo": {"path": "/m", "paths": {"winbox": "/w"}},
}


def row(name, **kw):
    """A healthy, freshly probed hosts row; override any field."""
    base = {
        "host": name, "status": None, "probed_at": FRESH,
        "provides": ["chrome"], "max_workers": 3, "running": 0,
        "ram_free_gb": 4.0, "load_per_core": 0.5, "runners": ["claude"],
    }
    base.update(kw)
    return base


def task(**kw):
    base = {"id": "task-x", "project": "proj", "role": "developer",
            "description": "do it", "touches": "[]", "runner": None, "model_hint": None}
    base.update(kw)
    return base


@pytest.fixture()
def world(monkeypatch):
    monkeypatch.setattr(config, "hosts", lambda: HOSTS)
    monkeypatch.setattr(config, "projects", lambda: PROJECTS)
    box = SimpleNamespace(runners=["claude"])
    monkeypatch.setattr(router, "role_runners", lambda t: box.runners)
    return box


def pick(rows, **kw):
    return router.pick_host(kw.pop("task", task()), hosts_rows=rows, now=NOW, **kw)


# ---------------------------------------------------------------------------
# needs: line, flag
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("desc, want", [
    (None, []),
    ("no such line", []),
    ("needs:", []),
    ("needs:   ", []),
    ("needs: win_gui", ["win_gui"]),
    ("intro\nneeds: chrome, Win_GUI ,chrome\nmore", ["chrome", "win_gui"]),
    ("needs: a\nNeeds: b, c", ["a", "b", "c"]),
    ("  needs: a", ["a"]),
    ("this needs: a", []),            # not at the start of a line
    ("needs:\nchrome", []),           # the value must be on the same line
])
def test_parse_needs(desc, want):
    assert router.parse_needs(desc) == want


@pytest.mark.parametrize("desc, needs, want", [
    ("do it", "", "do it"),
    ("do it", "  ", "do it"),
    ("do it", ",,", "do it"),
    ("do it", "[]", "do it"),
    ("do it\n", "win_gui", "do it\nneeds: win_gui"),
    ("do it", "win_gui, chrome", "do it\nneeds: win_gui, chrome"),
    ("do it", '["win_gui", " chrome "]', "do it\nneeds: win_gui, chrome"),
    ("", "gpu", "needs: gpu"),
])
def test_add_needs_line(desc, needs, want):
    assert router.add_needs_line(desc, needs) == want
    assert router.parse_needs(want) == router.parse_needs(f"x\n{want}")


def test_create_task_needs_param_is_appended_to_the_description(monkeypatch, tmp_path):
    """The MCP stub is where `needs` is accepted (the registry's ToolSpec would
    silently drop it), so the line must land in the stored description."""
    import inspect
    from runners import cto_mcp_server as srv

    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    assert inspect.signature(srv.create_task).parameters["needs"].default == ""

    with_needs = srv.create_task("mooniex-agents", "developer", "t", "body",
                                 needs="win_gui, chrome")
    without = srv.create_task("mooniex-agents", "developer", "t", "body")

    got = db_mod.get_task(with_needs)["description"]
    assert got == "body\nneeds: win_gui, chrome"
    assert router.parse_needs(got) == ["win_gui", "chrome"]
    assert db_mod.get_task(without)["description"] == "body", "empty needs = unchanged"


@pytest.mark.parametrize("value, want", [
    (None, False), ("", False), ("0", False), ("off", False),
    ("1", True), ("true", True), (" ON ", True),
])
def test_flag_default_off(monkeypatch, value, want):
    if value is None:
        monkeypatch.delenv("ORG_HOST_ROUTER", raising=False)
    else:
        monkeypatch.setenv("ORG_HOST_ROUTER", value)
    assert router.enabled() is want


# ---------------------------------------------------------------------------
# pick_host: each filter on its own
# ---------------------------------------------------------------------------

def three(**contabo_override):
    """contabo is the lightest, so it wins unless something rejects it."""
    return [row("contabo", **{"load_per_core": 0.1, **contabo_override}),
            row("mac", load_per_core=0.5), row("winbox", load_per_core=0.9)]


def test_baseline_lightest_host_wins(world):
    p = pick(three())
    assert p.host == "contabo"
    assert p.line == ("host: contabo · load 0.10/core · ram 4.0 GB · running 0/3"
                      " · rejected: none")


@pytest.mark.parametrize("override, reason", [
    ({"probed_at": (NOW - timedelta(seconds=61)).isoformat()}, "last one 61 s old"),
    ({"probed_at": None}, STALE),
    ({"probed_at": "garbage"}, "probed_at unreadable"),
    ({"probed_at": (NOW + timedelta(minutes=5)).isoformat()}, "probed_at in the future"),
    ({"status": "offline"}, "status offline"),
    ({"status": "pending_identity"}, "status pending_identity"),
    ({"running": 3}, "full 3/3"),
    ({"running": None}, "running/max_workers unknown"),
    ({"max_workers": None}, "running/max_workers unknown"),
    ({"load_per_core": None}, "no load_per_core reading"),
    ({"runners": ["codex"]}, "no usable runner"),
    ({"runners": None}, "no usable runner"),
])
def test_each_filter_rejects_contabo_on_its_own(world, override, reason):
    p = pick(three(**override))
    assert p.host == "mac", "the next lightest host takes over"
    assert reason in p.rejected["contabo"]
    assert list(p.rejected) == ["contabo"], "no other host is rejected"
    assert f"contabo({p.rejected['contabo']})" in p.line


def test_missing_provides_rejects_on_its_own(world):
    rows = three(provides=["chrome"])
    rows[2]["provides"] = ["chrome", "win_gui"]          # only winbox has it
    p = pick(rows, task=task(description="x\nneeds: win_gui, chrome"))
    assert p.host == "winbox"
    assert p.rejected["contabo"] == "provides lacks win_gui"
    assert p.rejected["mac"] == "provides lacks win_gui"


def test_empty_needs_is_no_constraint(world):
    rows = three(provides=None)
    assert pick(rows).host == "contabo"


def test_project_without_a_path_for_the_host(world):
    p = pick(three(), task=task(project="nocontabo"))
    assert p.host == "mac"                                # mac falls back to `path:`
    assert p.rejected == {"contabo": "no paths.contabo for nocontabo"}


def test_unknown_project_rejects_every_host(world):
    p = pick(three(), task=task(project="nope"))
    assert p.host is None
    assert all(r == "unknown project nope" for r in p.rejected.values())


def test_running_below_max_is_ok(world):
    assert pick(three(running=2)).host == "contabo"


def test_probe_at_exactly_60s_is_fresh(world):
    at = (NOW - timedelta(seconds=60)).isoformat()
    assert pick(three(probed_at=at)).host == "contabo"


def test_naive_probed_at_is_utc(world):
    at = (NOW - timedelta(seconds=5)).replace(tzinfo=None).isoformat()
    assert pick(three(probed_at=at)).host == "contabo"


def test_usable_runner_only_needs_one_overlap(world):
    world.runners = ["agy", "claude"]
    assert pick(three(runners=["claude", "codex"])).host == "contabo"
    world.runners = ["agy"]
    p = pick(three(runners=["claude", "codex"]))
    assert p.host is None
    assert p.rejected["contabo"] == "no usable runner (role: agy · host: claude,codex)"


def test_no_ok_runner_rejects_every_host(world):
    world.runners = []
    p = pick(three())
    assert p.host is None
    assert "role: none ok" in p.rejected["mac"]


def test_host_only_in_the_table_is_rejected(world):
    p = pick(three() + [row("ghost", load_per_core=0.0)])
    assert p.host == "contabo"
    assert p.rejected == {"ghost": "not in config/hosts.yaml"}


# ---------------------------------------------------------------------------
# pick_host: ranking
# ---------------------------------------------------------------------------

def test_lowest_load_wins(world):
    rows = [row("contabo", load_per_core=0.40, ram_free_gb=9.0),
            row("mac", load_per_core=0.05, ram_free_gb=0.5),
            row("winbox", load_per_core=0.30, ram_free_gb=9.0)]
    assert pick(rows).host == "mac"


def test_load_tie_breaks_on_more_free_ram(world):
    rows = [row("contabo", load_per_core=0.2, ram_free_gb=2.0),
            row("mac", load_per_core=0.2, ram_free_gb=6.5),
            row("winbox", load_per_core=0.2, ram_free_gb=3.0)]
    assert pick(rows).host == "mac"


def test_ram_tie_breaks_on_name(world):
    rows = [row("winbox", load_per_core=0.2), row("mac", load_per_core=0.2),
            row("contabo", load_per_core=0.2)]
    assert pick(rows).host == "contabo"


def test_unknown_ram_loses_the_tie(world):
    rows = [row("contabo", load_per_core=0.2, ram_free_gb=None),
            row("mac", load_per_core=0.2, ram_free_gb=0.1)]
    p = pick(rows)
    assert p.host == "mac"


def test_success_line_lists_every_rejection(world):
    p = pick([row("contabo", load_per_core=0.25, ram_free_gb=3.44, running=1),
              row("mac", running=3), row("winbox", status="offline")])
    assert p.line == ("host: contabo · load 0.25/core · ram 3.4 GB · running 1/3"
                      " · rejected: mac(full 3/3) winbox(status offline)")


# ---------------------------------------------------------------------------
# pick_host: no match
# ---------------------------------------------------------------------------

def test_empty_table_is_no_probe_for_every_host(world):
    """The Mac ledger has an empty hosts table until the probe timers run."""
    p = pick([])
    assert p.host is None
    assert p.line == ("no_host: contabo(no probe ≤60 s) mac(no probe ≤60 s)"
                      " winbox(no probe ≤60 s)")


def test_no_match_lists_each_reason(world):
    p = pick([row("contabo", running=3), row("mac", status="left"),
              row("winbox", probed_at=(NOW - timedelta(minutes=9)).isoformat())])
    assert p.host is None
    assert p.line == ("no_host: contabo(full 3/3) mac(status left)"
                      " winbox(no probe ≤60 s (last one 540 s old))")


def test_unreadable_table_is_no_host_not_a_crash(world, monkeypatch):
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(db_mod, "list_hosts", boom)
    p = router.pick_host(task(), now=NOW)
    assert p.host is None
    assert p.line == "no_host: router error: RuntimeError: db down"


def test_route_failure_rejects_hosts_with_the_error(world, monkeypatch):
    def boom(t):
        raise ValueError("plans.yaml gone")
    monkeypatch.setattr(router, "role_runners", boom)
    p = pick(three())
    assert p.host is None
    assert p.rejected["contabo"] == "route error: ValueError: plans.yaml gone"


def test_route_is_not_read_when_no_host_survives_the_cheap_filters(world, monkeypatch):
    calls = []
    monkeypatch.setattr(router, "role_runners", lambda t: calls.append(1) or ["claude"])
    assert pick([]).host is None
    assert calls == [], "a cold quota read is not worth it with nothing to pick"


# ---------------------------------------------------------------------------
# role_runners reads route, never changes it
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_route(monkeypatch):
    from tools import route
    box = SimpleNamespace(cls="dev_general", plans=[], plan_calls=[])

    def plan(cls, **kw):
        box.plan_calls.append((cls, kw))
        return box.plans

    monkeypatch.setattr(route, "load_plans", lambda: {"cfg": 1})
    monkeypatch.setattr(route, "class_for", lambda role, brief, cfg: box.cls)
    monkeypatch.setattr(route, "plan", plan)
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    return box


def _plan(runner, verdict="ok"):
    return SimpleNamespace(verdict=verdict, choice=SimpleNamespace(runner=runner))


def test_role_runners_are_the_ok_plans_in_order(fake_route):
    fake_route.plans = [_plan("agy"), _plan("codex", "will_hit"), _plan("claude"),
                        _plan("agy"), _plan("codex", "cannot")]
    t = task(touches='["a.py"]')
    assert router.role_runners(t) == ["agy", "claude"]
    cls, kw = fake_route.plan_calls[0]
    assert cls == "dev_general"
    assert kw["host"] is None and kw["touches"] == ["a.py"] and kw["brief"] == "do it"


def test_role_runners_no_ok_plan_is_empty(fake_route):
    fake_route.plans = [_plan("agy", "will_hit"), _plan("codex", "unknown")]
    assert router.role_runners(task()) == []


def test_role_runners_unrouted_role_stays_on_claude(fake_route):
    fake_route.cls = None
    assert router.role_runners(task()) == ["claude"]
    assert fake_route.plan_calls == []


def test_role_runners_model_hint_claude_skips_route(fake_route):
    assert router.role_runners(task(model_hint=" Claude ")) == ["claude"]
    assert fake_route.plan_calls == []


def test_role_runners_hand_pin_is_the_runner(fake_route):
    assert router.role_runners(task(runner="Codex")) == ["codex"]
    assert fake_route.plan_calls == []


def test_role_runners_router_off_is_claude(fake_route, monkeypatch):
    monkeypatch.setenv("ORG_ROUTER", "off")
    assert router.role_runners(task()) == ["claude"]
    assert fake_route.plan_calls == []


# ---------------------------------------------------------------------------
# delegate_task: the host-resolution block
# ---------------------------------------------------------------------------

@pytest.fixture()
def flow(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.delenv("ORG_HOST_ROUTER", raising=False)
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    db_mod.init()
    rec = SimpleNamespace(route_hosts=[], spawn_hosts=[], route_log=None)
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "_remote_free_gb", lambda ssh: 100.0)

    def route_runner(t, role, host):
        rec.route_hosts.append(host)
        if rec.route_log:
            db_mod.set_fields(t["id"], delegate_log=rec.route_log, actor="cto")
        return None

    async def spawn_remote(t, host, **kw):
        rec.spawn_hosts.append(host)
        return db_mod.get_task(t["id"])

    monkeypatch.setattr(delegate, "_route_runner", route_runner)
    monkeypatch.setattr(delegate, "_spawn_remote", spawn_remote)
    monkeypatch.setattr(router, "role_runners", lambda t: ["claude"])
    return rec


def new_task(**kw):
    return db_mod.create_task(project="mooniex-agents", role="developer", title="t",
                              description=kw.pop("description", "d"), owner_cto="x", **kw)


def probe(name, **kw):
    fields = {"probed_at": db_mod.now_iso(), "provides": ["chrome"], "max_workers": 3,
              "running": 0, "ram_free_gb": 4.0, "load_per_core": 0.5,
              "runners": ["claude"]}
    fields.update(kw)
    db_mod.upsert_host(name, **fields)


def run(tid, **kw):
    return asyncio.run(delegate.delegate_task(tid, **kw))


@pytest.mark.parametrize("arg, task_host, want", [
    ("winbox", None, "winbox"),         # explicit arg
    ("winbox", "contabo", "winbox"),    # arg beats tasks.host
    (None, "contabo", "contabo"),       # tasks.host
    (None, None, "mac"),                # self_host()
])
def test_flag_off_is_todays_resolution_and_never_calls_pick_host(
        flow, monkeypatch, arg, task_host, want):
    def boom(*a, **k):
        raise AssertionError("pick_host must not run with ORG_HOST_ROUTER off")
    monkeypatch.setattr(router, "pick_host", boom)
    tid = new_task(host=task_host)

    run(tid, host=arg)

    assert flow.route_hosts == [want]
    assert db_mod.get_task(tid)["delegate_log"] is None, "flag off writes no host line"


@pytest.mark.parametrize("arg, task_host, want, source", [
    ("winbox", None, "winbox", "host= argument"),
    ("winbox", "contabo", "winbox", "host= argument"),
    (None, "contabo", "contabo", "tasks.host"),
])
def test_flag_on_explicit_host_and_tasks_host_win_and_are_manual(
        flow, monkeypatch, arg, task_host, want, source):
    monkeypatch.setenv("ORG_HOST_ROUTER", "1")
    monkeypatch.setattr(router, "pick_host",
                        lambda *a, **k: pytest.fail("a named host must not be re-picked"))
    tid = new_task(host=task_host)
    probe("mac", load_per_core=0.0)      # lighter than anything named: still ignored

    run(tid, host=arg)

    assert flow.route_hosts == [want]
    assert db_mod.get_task(tid)["delegate_log"] == f"manual: {want} · {source}"


def test_flag_on_picks_the_lightest_host_and_it_reaches_route_and_spawn(flow, monkeypatch):
    monkeypatch.setenv("ORG_HOST_ROUTER", "1")
    probe("mac", load_per_core=0.60)
    probe("winbox", load_per_core=0.90)
    probe("contabo", load_per_core=0.10, ram_free_gb=3.0, running=1)
    tid = new_task()

    row_ = run(tid)

    assert flow.route_hosts == ["contabo"]
    assert flow.spawn_hosts == ["contabo"]
    assert row_["delegate_log"].startswith(
        "host: contabo · load 0.10/core · ram 3.0 GB · running 1/3 · rejected: none")


def test_flag_on_needs_line_steers_the_pick(flow, monkeypatch):
    monkeypatch.setenv("ORG_HOST_ROUTER", "1")
    probe("mac", load_per_core=0.01)
    probe("contabo", load_per_core=0.10)
    probe("winbox", load_per_core=0.90, provides=["chrome", "win_gui"])
    tid = new_task(description="click things\nneeds: win_gui")

    run(tid)

    assert flow.spawn_hosts == ["winbox"]


def test_flag_on_no_match_leaves_the_task_pending_and_never_spawns(flow, monkeypatch):
    """Empty hosts table = no probe for any host (the Mac ledger today)."""
    monkeypatch.setenv("ORG_HOST_ROUTER", "1")
    tid = new_task()

    row_ = run(tid)

    assert row_["status"] == "pending"
    assert row_["delegate_log"] == ("no_host: contabo(no probe ≤60 s) mac(no probe ≤60 s)"
                                    " winbox(no probe ≤60 s)")
    assert flow.route_hosts == [] and flow.spawn_hosts == []
    assert db_mod.get_task(tid)["host"] is None


def test_flag_on_no_match_can_be_retried_once_a_probe_lands(flow, monkeypatch):
    monkeypatch.setenv("ORG_HOST_ROUTER", "1")
    tid = new_task()
    assert run(tid)["delegate_log"].startswith("no_host:")

    probe("contabo")
    row_ = run(tid)

    assert flow.spawn_hosts == ["contabo"]
    assert row_["delegate_log"].startswith("host: contabo")


def test_host_line_survives_the_route_runner_overwrite(flow, monkeypatch):
    monkeypatch.setenv("ORG_HOST_ROUTER", "1")
    probe("contabo")
    flow.route_log = "router: agy gemini [agy-gemini] — ok"
    tid = new_task()

    row_ = run(tid)

    head, tail = row_["delegate_log"].split("\n")
    assert head.startswith("host: contabo · load 0.50/core")
    assert tail == "router: agy gemini [agy-gemini] — ok"
