"""Org restructure P2 gates in Core (docs/design/org-restructure-p2.md).

- tools/delegate.py: the router_off hub event (plan §4.3 M1), the resource gate
  on a local spawn (ORG_SPAWN_GATE, plan §7.3) and a Project Head's worker cap
  (plan §3.2, T8 second half), which holds whatever ORG_PH_ROLES says and across
  processes (security review of f73fa02f).
- A Project Head acts only on its own tasks (delegate, reopen, close_dev).
- runners/watchdog.py: a disk-queue drain that a later gate refuses is re-queued.
- lib/org_tools_registry.py: a Project Head is not served, and may not call,
  the tools plan §3.2 / §4.1 deny it; merge_task judges the caller's own role.
- tools/git_ops.py: merge_task reads can_merge from policies/agents.yaml (T9).
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.org_tools_registry as reg  # noqa: E402
import lib.task_ownership as ownership  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.disk_queue as disk_queue  # noqa: E402
import tools.git_ops as git_ops  # noqa: E402

PH = "project_head"


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    for k in ("ORG_ROUTER", "ORG_ROUTER_REASON", "ORG_PH_ROLES", "ORG_SPAWN_GATE",
              "CXO_SESSION_ID", "CTO_SESSION_ID", "ORG_PH_LANE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setattr(delegate, "_PH_SLOTS_DIR", tmp_path / "ph-slots", raising=False)
    db_mod.init()
    yield db_mod


def _task(db, *, owner="ph000001", owner_role=PH, status="pending", runner=None,
          description="d") -> dict:
    tid = db.create_task(project="mooniex-agents", role="developer", title="p2 gate test",
                         description=description, owner_cto=owner, owner_role=owner_role)
    if status != "pending":
        db.update_status(tid, status, actor="test", force=True)
    if runner:
        db.set_fields(tid, runner=runner, actor="test")
    return db.get_task(tid)


def _events(db, kind):
    return [e for e in db.recent_events(limit=200) if e["kind"] == kind]


# --- router_off event (plan §4.3 M1, asked for by CTO #dd03bac1) -------------

def test_router_off_logs_one_event_with_reason_runner_and_actor(temp_db, monkeypatch):
    monkeypatch.setenv("ORG_ROUTER", "off")
    monkeypatch.setenv("ORG_ROUTER_REASON", "router repair #412")
    monkeypatch.setenv("CXO_SESSION_ID", "abcd1234")
    t = _task(temp_db, owner_role="cto")

    assert delegate._route_runner(t, "developer", "test-host") is None

    ev = _events(temp_db, "router_off")
    assert len(ev) == 1
    assert ev[0]["task_id"] == t["id"] and ev[0]["actor"] == "cto-abcd1234"
    assert json.loads(ev[0]["payload"]) == {
        "reason": "router repair #412", "runner": None, "model_hint": None, "pinned": False}


def test_router_off_with_a_pinned_runner_still_logs_and_marks_pinned(temp_db, monkeypatch):
    monkeypatch.setenv("ORG_ROUTER", "OFF")
    t = _task(temp_db, owner_role="cto", runner="claude",
              description="override: security\nbody")

    assert delegate._route_runner(t, "developer", "test-host") is None

    (ev,) = _events(temp_db, "router_off")
    assert ev["actor"] == "cto"
    assert json.loads(ev["payload"]) == {
        "reason": "", "runner": "claude", "model_hint": None, "pinned": True}


def test_router_on_logs_no_router_off_event(temp_db, monkeypatch):
    monkeypatch.setattr("tools.route.pick_runner", Mock(return_value=None), raising=False)
    t = _task(temp_db, owner_role="cto")
    delegate._route_runner(t, "developer", "test-host")
    assert _events(temp_db, "router_off") == []


def test_router_off_event_failure_never_stops_the_delegate(temp_db, monkeypatch):
    monkeypatch.setenv("ORG_ROUTER", "off")
    t = _task(temp_db, owner_role="cto")
    monkeypatch.setattr(delegate.db, "log_event", Mock(side_effect=RuntimeError("hub down")))
    warned = Mock()
    monkeypatch.setattr(delegate, "warn", warned)
    assert delegate._route_runner(t, "developer", "test-host") is None
    assert "router_off event not logged" in warned.call_args[0][0]


# --- Project Head worker cap (plan §3.2, T8) ---------------------------------

def test_ph_cap_holds_whatever_this_process_says_about_the_flag(temp_db):
    # The watchdog's disk-queue drain or the mesh far side may run without
    # ORG_PH_ROLES; a Project Head's row is capped anyway (review finding 3).
    for _ in range(2):
        _task(temp_db, status="in_progress")
    assert delegate._ph_cap_refusal(_task(temp_db))


def test_ph_cap_counts_queued_remote_and_stalled_workers(temp_db):
    _task(temp_db, status="queued_remote")
    _task(temp_db, status="stalled")
    why = delegate._ph_cap_refusal(_task(temp_db))
    assert why and "2/2" in why


def test_ph_cap_counts_a_slot_held_by_another_live_process(temp_db, tmp_path):
    _task(temp_db, status="in_progress")
    other = _task(temp_db)
    holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        slots = tmp_path / "ph-slots"
        slots.mkdir()
        (slots / f"ph000001--{other['id']}").write_text(str(holder.pid))
        assert delegate._ph_cap_refusal(_task(temp_db))          # the watchdog's slot counts
    finally:
        holder.kill()
        holder.wait()
    assert delegate._ph_cap_refusal(_task(temp_db)) is None      # its holder died: free


def test_delegate_task_releases_its_slot_however_it_ends(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 500.0)
    monkeypatch.setattr(delegate, "get_project", Mock(side_effect=RuntimeError("after the gate")))
    t = _task(temp_db)
    with pytest.raises(RuntimeError, match="after the gate"):
        asyncio.run(delegate.delegate_task(t["id"]))
    assert list((tmp_path / "ph-slots").glob("*--task-*")) == []


def test_ph_cap_refuses_a_third_live_worker(temp_db, monkeypatch):
    a = _task(temp_db, status="in_progress")
    b = _task(temp_db, status="rate_limited")
    why = delegate._ph_cap_refusal(_task(temp_db))
    assert why and "2/2" in why and a["id"] in why and b["id"] in why


def test_ph_cap_counts_only_this_heads_live_workers(temp_db, monkeypatch):
    _task(temp_db, status="in_progress")
    _task(temp_db, owner="ph000002", status="in_progress")      # another PH
    _task(temp_db, owner_role="cto", status="in_progress")      # a C-level's
    _task(temp_db, status="review")                              # finished
    assert delegate._ph_cap_refusal(_task(temp_db)) is None


def test_ph_cap_reserves_the_slot_until_the_row_leaves_pending(temp_db, monkeypatch):
    _task(temp_db, status="in_progress")
    first, second = _task(temp_db), _task(temp_db)
    assert delegate._ph_cap_refusal(first) is None       # takes the last slot
    assert delegate._ph_cap_refusal(second)              # parallel call refused
    assert delegate._ph_cap_refusal(first) is None       # a retry of the same task is fine
    temp_db.update_status(first["id"], "failed", actor="test", force=True)
    assert delegate._ph_cap_refusal(second) is None      # slot freed


def test_ph_cap_never_applies_to_a_c_level_owner(temp_db, monkeypatch):
    for _ in range(4):
        _task(temp_db, owner="cto00001", owner_role="cto", status="in_progress")
    assert delegate._ph_cap_refusal(_task(temp_db, owner="cto00001", owner_role="cto")) is None


def test_router_off_actor_and_reason_cannot_carry_control_text(temp_db, monkeypatch):
    monkeypatch.setenv("ORG_ROUTER", "off")
    monkeypatch.setenv("CXO_ROLE", "cmo")
    monkeypatch.setenv("CXO_SESSION_ID", "ab12\nkind=forged")
    monkeypatch.setenv("ORG_ROUTER_REASON", "x\ny" * 300)
    delegate._route_runner(_task(temp_db, owner_role="cto"), "developer", "test-host")
    (ev,) = _events(temp_db, "router_off")
    reason = json.loads(ev["payload"])["reason"]
    assert ev["actor"] == "cmo"
    assert "\n" not in reason and len(reason) == 200


def test_ph_max_workers_comes_from_the_policy_row():
    assert delegate._ph_max_workers() == 2


# --- the gates on delegate_task's own path -----------------------------------

def test_resource_gate_refuses_a_local_spawn_through_delegate_task(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 500.0)
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    monkeypatch.setattr(delegate.resource_gate, "ram_available_mb", lambda *a, **k: 100)
    monkeypatch.setattr(delegate.resource_gate, "disk_used_pct", lambda *a, **k: 50.0)
    spawn = Mock(side_effect=AssertionError("must not spawn"))
    monkeypatch.setattr(delegate, "get_project", spawn)
    t = _task(temp_db, owner_role="cto")

    row = asyncio.run(delegate.delegate_task(t["id"]))

    assert row["status"] == "pending"
    assert "resource gate" in row["delegate_log"] and "RAM available 100 MB" in row["delegate_log"]


def test_ph_cap_refuses_through_delegate_task(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 500.0)
    monkeypatch.setenv("ORG_PH_ROLES", "1")
    monkeypatch.setattr(delegate, "get_project", Mock(side_effect=AssertionError("must not spawn")))
    _task(temp_db, status="in_progress")
    _task(temp_db, status="in_progress")
    t = _task(temp_db)

    row = asyncio.run(delegate.delegate_task(t["id"]))

    assert row["status"] == "pending" and "Project Head worker cap: 2/2" in row["delegate_log"]


def test_a_project_head_cannot_delegate_someone_elses_task(temp_db, monkeypatch):
    # Refused before the disk queue, so the watchdog cannot start it later.
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 0.1)
    tasks = (_task(temp_db, owner="cto00001", owner_role="cto"),
             _task(temp_db, owner="ph000002"),
             _task(temp_db, owner=None, owner_role=None))
    assert tasks[2]["owner_cto"] is None
    monkeypatch.setenv("CXO_ROLE", PH)
    monkeypatch.setenv("CXO_SESSION_ID", "ph000001")
    for t in tasks:
        with pytest.raises(PermissionError, match="only its own tasks"):
            asyncio.run(delegate.delegate_task(t["id"]))
        assert not disk_queue.is_queued(t["id"])


def test_a_project_heads_own_task_passes_the_ownership_check(temp_db, monkeypatch):
    monkeypatch.setenv("CXO_ROLE", PH)
    monkeypatch.setenv("CXO_SESSION_ID", "ph000001")
    assert delegate._ph_ownership_refusal(_task(temp_db)) is None
    monkeypatch.setenv("CXO_ROLE", "cto")
    assert delegate._ph_ownership_refusal(_task(temp_db, owner="cto00001", owner_role="cto")) is None


def test_is_mine_is_strict_for_a_project_head(monkeypatch):
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    monkeypatch.setenv("CXO_ROLE", PH)
    monkeypatch.setenv("CXO_SESSION_ID", "ph000001")
    assert ownership.is_mine({"owner_cto": "ph000001", "owner_role": PH})
    assert not ownership.is_mine({"owner_cto": None, "owner_role": None})
    assert not ownership.is_mine({"owner_cto": "cto00001", "owner_role": "cto"})
    assert not ownership.is_mine({"owner_cto": "ph000001", "owner_role": "cto"})
    monkeypatch.delenv("CXO_SESSION_ID")
    assert not ownership.is_mine({"owner_cto": "", "owner_role": PH})
    monkeypatch.setenv("CXO_ROLE", "cmo")                        # a C-level: as before
    assert ownership.is_mine({"owner_cto": "cto00001", "owner_role": "cto"})


@pytest.mark.parametrize("tool,kw", [
    ("close_dev", {}),
    ("reopen_task", {"feedback": "f"}),
    ("delegate_task", {}),
])
def test_a_project_head_cannot_touch_another_owners_worker(temp_db, monkeypatch, tool, kw):
    t = _task(temp_db, owner="cto00001", owner_role="cto")
    monkeypatch.setenv("CXO_ROLE", PH)
    monkeypatch.setenv("CXO_SESSION_ID", "ph000001")
    import dataclasses
    handler = Mock(side_effect=AssertionError("handler must not run"))
    monkeypatch.setitem(reg.BY_NAME, tool, dataclasses.replace(reg.BY_NAME[tool], handler=handler))
    if reg.BY_NAME[tool].is_async:
        out = asyncio.run(reg.dispatch(tool, task_id=t["id"], **kw))
    else:
        out = reg.dispatch_sync(tool, task_id=t["id"], **kw)
    assert "Refusing cross-CTO mutation" in out and "you are Project Head #ph000001" in out
    handler.assert_not_called()


def test_watchdog_requeues_a_drained_task_a_later_gate_refused(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr(disk_queue, "QUEUE_PATH", tmp_path / "disk_queue.jsonl")
    monkeypatch.setattr(delegate, "_disk_orange_floor_gb", lambda: 5.0)
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 50.0)
    monkeypatch.setattr(watchdog, "success", Mock(side_effect=AssertionError("not a spawn")))
    _task(temp_db, status="in_progress")
    _task(temp_db, status="in_progress")
    t = _task(temp_db)
    disk_queue.enqueue(t["id"], "ph000001")

    out = watchdog._drain_disk_queue()

    assert out["task"] == t["id"] and "Project Head worker cap: 2/2" in out["refused"]
    assert disk_queue.is_queued(t["id"])


def test_resource_gate_is_skipped_for_a_remote_host(monkeypatch):
    monkeypatch.setenv("ORG_SPAWN_GATE", "1")
    monkeypatch.setattr(delegate.resource_gate, "check", Mock(return_value="refused"))
    assert delegate._p2_spawn_refusal({"id": "t", "owner_role": "cto"}, "winbox", "contabo") is None
    assert delegate._p2_spawn_refusal({"id": "t", "owner_role": "cto"}, "contabo", "contabo") == "refused"


# --- registry: what a Project Head is served and may call --------------------

def test_project_head_is_not_served_the_withheld_tools():
    ph = set(reg.served_names(PH))
    cto = set(reg.served_names("cto"))
    assert not ph & reg.PH_WITHHELD_TOOLS
    assert reg.PH_WITHHELD_TOOLS <= cto | reg.ENVELOPE_TOOLS
    assert {"create_task", "delegate_task", "get_task", "send_to_cxo"} <= ph
    assert cto - ph == reg.PH_WITHHELD_TOOLS


def test_every_withheld_name_is_a_real_tool():
    assert reg.PH_WITHHELD_TOOLS <= set(reg.BY_NAME)
    assert set(reg.served_names(PH)) <= reg.PH_TOOLS


def test_a_tool_added_later_is_withheld_from_a_project_head(monkeypatch):
    # Local main's email_ceo is not on this branch's base: the allowlist must
    # withhold it (and anything after it) without anyone listing it.
    import dataclasses
    new = dataclasses.replace(reg.BY_NAME["get_task"], name="email_ceo")
    monkeypatch.setattr(reg, "REGISTRY", list(reg.REGISTRY) + [new])
    monkeypatch.setitem(reg.BY_NAME, "email_ceo", new)
    assert "email_ceo" in reg.served_names("cto")
    assert "email_ceo" not in reg.served_names(PH)
    monkeypatch.setenv("CXO_ROLE", PH)
    out = reg.dispatch_sync("email_ceo", task_id="task-x")
    assert out.startswith("ERROR: email_ceo is not a Project Head tool")


def test_a_project_head_calling_merge_task_is_refused_before_the_handler(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", PH)
    called = Mock()
    monkeypatch.setattr(reg, "do_merge", called)
    out = reg.dispatch_sync("merge_task", task_id="task-x")
    assert out.startswith("ERROR: merge_task is not a Project Head tool")
    called.assert_not_called()


@pytest.mark.parametrize("flag,env_role,expected", [
    (None, "cmo", "cto"),     # flag off: as before, everyone merges as "cto"
    ("1", "cmo", "cmo"),      # flag on: the caller's own role
    ("1", None, "cto"),       # flag on, no CXO_ROLE: "cto" as before
])
def test_merge_task_passes_the_callers_role(monkeypatch, flag, env_role, expected):
    if flag:
        monkeypatch.setenv("ORG_PH_ROLES", flag)
    else:
        monkeypatch.delenv("ORG_PH_ROLES", raising=False)
    if env_role:
        monkeypatch.setenv("CXO_ROLE", env_role)
    else:
        monkeypatch.delenv("CXO_ROLE", raising=False)
    merge = Mock(return_value={"merged": True})
    monkeypatch.setattr(reg, "do_merge", merge)
    reg._h_merge_task(task_id="task-x")
    assert merge.call_args.kwargs["role"] == expected


def test_project_head_writes_only_to_its_own_c_level(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", PH)
    monkeypatch.setenv("ORG_PH_LANE", "cmo")
    send = Mock(return_value="sent")
    monkeypatch.setattr(reg.send_to_cxo_mod, "send", send)
    monkeypatch.setattr(reg.send_to_cxo_mod, "spawn", Mock(side_effect=AssertionError("no spawn")))
    with pytest.raises(PermissionError, match="cannot start"):
        reg._h_send_to_cxo(role="cmo", message="m", spawn=True)
    with pytest.raises(PermissionError, match="only to its own C-level"):
        reg._h_send_to_cxo(role="cto", message="m")
    assert reg._h_send_to_cxo(role="CMO", message="m") == "sent"


def test_c_level_send_to_cxo_is_unchanged(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cto")
    send = Mock(return_value="sent")
    monkeypatch.setattr(reg.send_to_cxo_mod, "send", send)
    assert reg._h_send_to_cxo(role="cfo", message="m") == "sent"
    send.assert_called_once_with("cfo", "m")


def _served_by_server(role: str) -> set[str]:
    env = {k: v for k, v in os.environ.items() if k != "ORG_DB_URL"}
    env["CXO_ROLE"] = role
    out = subprocess.run(
        [sys.executable, "-c",
         "import runners.cto_mcp_server as s;"
         "print(' '.join(t.name for t in s.mcp._tool_manager.list_tools()))"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-800:]
    return set(out.stdout.split())


def test_the_mcp_server_drops_the_withheld_tools_for_a_project_head():
    ph, cto = _served_by_server(PH), _served_by_server("cto")
    assert not ph & reg.PH_WITHHELD_TOOLS
    assert cto - ph == reg.PH_WITHHELD_TOOLS


def test_the_c_level_allowlist_follows_the_role():
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    import cxo_mcp_config
    ph = set(cxo_mcp_config._allowed_for(["org"], str(ROOT), builtins=False, role=PH))
    cto = set(cxo_mcp_config._allowed_for(["org"], str(ROOT), builtins=False, role="cto"))
    assert {f"mcp__org__{n}" for n in reg.PH_WITHHELD_TOOLS} == cto - ph


# --- git_ops: can_merge is read (T9) -----------------------------------------

def test_can_merge_follows_the_policy_rows():
    assert git_ops._role_can_merge("cto") is True
    assert git_ops._role_can_merge(PH) is False
    assert git_ops._role_can_merge("no-such-role") is False


@pytest.mark.parametrize("value", ["false", "true", 1, "yes", None])
def test_can_merge_must_be_a_real_true(monkeypatch, value):
    monkeypatch.setattr("lib.config.role", lambda role: {"can_merge": value})
    assert git_ops._role_can_merge("cto") is False


def test_runners_cto_imports_for_a_project_head():
    env = {k: v for k, v in os.environ.items() if k != "ORG_DB_URL"}
    env["CXO_ROLE"] = PH
    out = subprocess.run([sys.executable, "-c", "import runners.cto as c; print(c.t_merge)"],
                         cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    if "ModuleNotFoundError" in out.stderr and "claude_agent_sdk" in out.stderr:
        pytest.skip("claude_agent_sdk not installed")
    assert out.returncode == 0, out.stderr[-800:]
    assert out.stdout.strip() == "None"


def test_merge_task_refuses_a_project_head():
    with pytest.raises(PermissionError, match="only C-level"):
        git_ops.merge_task("task-x", role=PH)


def test_merge_task_refuses_a_c_level_whose_row_says_no(monkeypatch):
    monkeypatch.setattr(git_ops, "_role_can_merge", lambda role: False)
    with pytest.raises(PermissionError, match="can_merge is false for role cmo"):
        git_ops.merge_task("task-x", role="cmo")
