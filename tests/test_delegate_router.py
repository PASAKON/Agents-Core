"""Quota routing hook tests with an isolated database and mocked router."""
import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import ANY, Mock

import pytest

from lib import db as db_mod
from tools import delegate


@pytest.fixture()
def task(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    db_mod.init()
    with db_mod.get_conn() as conn:
        ts = db_mod.now_iso()
        conn.execute(
            """INSERT INTO tasks
               (id, project, role, status, title, description,
                touches, depends_on, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("task-router", "test-project", "developer", "pending",
             "Router test", "d", "[]", "[]", ts, ts),
        )
        conn.commit()
    row = db_mod.get_task("task-router")
    assert row["runner"] is None
    return row


@pytest.fixture()
def pick_runner(monkeypatch):
    try:
        importlib.import_module("tools.route")
    except ImportError:
        stub = ModuleType("tools.route")
        monkeypatch.setitem(sys.modules, "tools.route", stub)
        monkeypatch.setattr("tools.route", stub, raising=False)
    fake = Mock(return_value=None)
    monkeypatch.setattr("tools.route.pick_runner", fake, raising=False)
    return fake


def test_choice_persists_runner_and_reason(task, pick_runner, monkeypatch):
    from tools.route import Choice

    pick_runner.return_value = Choice(
        candidate="agy:claude-sonnet-4-6",
        runner="agy",
        model="claude-sonnet-4-6",
        bucket="agy-claude",
        weekly=0.9,
        daily=None,
        skill=None,
        reason="r",
    )
    log = Mock()
    monkeypatch.setattr(delegate, "info", log)

    assert delegate._route_runner(task, "developer", "test-host") == "agy"

    pick_runner.assert_called_once_with("developer", "test-host", touches=ANY, brief=ANY, tier="normal", project="test-project")
    after = db_mod.get_task(task["id"])
    assert after["runner"] == "agy"
    assert after["runner_model"] == "claude-sonnet-4-6"
    assert after["status"] == task["status"]
    assert after["delegate_log"] == "router: agy claude-sonnet-4-6 [agy-claude] — r"
    log.assert_called_once_with(after["delegate_log"])


@pytest.mark.parametrize("field,value", [
    ("runner", "codex"),
    ("model_hint", "claude"),
    ("model_hint", "  CLAUDE  "),
])
def test_explicit_choice_skips_router(task, pick_runner, field, value):
    # IRON §59: a manual pin requires an override line in the description.
    with db_mod.get_conn() as conn:
        conn.execute(
            f"UPDATE tasks SET {field}=?, description=? WHERE id=?",
            (value, "override: review — test\n" + (task["description"] or ""), task["id"]),
        )
        conn.commit()
    before = db_mod.get_task(task["id"])

    assert delegate._route_runner(before, "developer", "test-host") is None

    pick_runner.assert_not_called()
    assert db_mod.get_task(task["id"]) == before


@pytest.mark.parametrize("value", ["off", "  OFF  "])
def test_disabled_router(task, pick_runner, monkeypatch, value):
    monkeypatch.setenv("ORG_ROUTER", value)

    assert delegate._route_runner(task, "developer", "test-host") is None

    pick_runner.assert_not_called()
    assert db_mod.get_task(task["id"]) == task


def test_no_choice_leaves_row_unchanged(task, pick_runner):
    assert delegate._route_runner(task, "developer", "test-host") is None

    pick_runner.assert_called_once_with("developer", "test-host", touches=ANY, brief=ANY, tier="normal", project=ANY)
    assert db_mod.get_task(task["id"]) == task


def test_router_error_leaves_row_unchanged(task, pick_runner, monkeypatch):
    pick_runner.side_effect = RuntimeError("quota unavailable")
    warning = Mock()
    monkeypatch.setattr(delegate, "warn", warning)

    assert delegate._route_runner(task, "developer", "test-host") is None

    pick_runner.assert_called_once_with("developer", "test-host", touches=ANY, brief=ANY, tier="normal", project=ANY)
    assert db_mod.get_task(task["id"]) == task
    warning.assert_called_once_with(
        "router skipped task=task-router: quota unavailable")


def test_pin_without_reason_raises_permission_error_and_logs(
    task, pick_runner, monkeypatch
):
    """IRON §59: _route_runner must raise PermissionError (not swallow it) when
    a manual runner pin has no override line.  The refusal must be written to
    delegate_log, and pick_runner must never be called."""
    warning = Mock()
    monkeypatch.setattr(delegate, "warn", warning)

    # Set runner on 'developer' task without an override line or runner_model.
    with db_mod.get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET runner=? WHERE id=?", ("claude", task["id"])
        )
        conn.commit()
    pinned = db_mod.get_task(task["id"])

    with pytest.raises(PermissionError) as exc_info:
        delegate._route_runner(pinned, "developer", "test-host")

    # Error message written to delegate_log
    after = db_mod.get_task(task["id"])
    assert after["delegate_log"] is not None
    assert "IRON §59" in after["delegate_log"]

    # The same message is in the raised exception
    assert "IRON §59" in str(exc_info.value)

    # warn() was called with the refusal
    warning.assert_called_once()
    assert "IRON §59" in warning.call_args[0][0]

    # pick_runner was never called
    pick_runner.assert_not_called()


def _pin_agy(task):
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET runner=?, runner_model=?, description=? WHERE id=?",
                     ("agy", "gemini-4-argon-high", "override: review — test\nd", task["id"]))
        conn.commit()
    return db_mod.get_task(task["id"])


@pytest.mark.parametrize("weekly,routed", [(0.0, True), (0.4, False)])
def test_agy_pin_on_an_exhausted_bucket_goes_to_the_router(task, pick_runner, monkeypatch, weekly, routed):
    # 12 Nov: task-75a566a1 and task-3334d815 were pinned to AGY at 0% and died rate_limited.
    import tools.route as route
    monkeypatch.setattr(route, "cached_quotas",
                        lambda cfg, **k: {"agy-gemini": SimpleNamespace(weekly_remaining=weekly, limit_hit=False, error=None)})
    monkeypatch.setattr(route, "bucket_for", lambda cand, cfg: "agy-gemini")
    monkeypatch.setattr(route, "load_plans", lambda *a, **k: {})
    monkeypatch.setattr(route, "usage_budget", SimpleNamespace(load_gate_rows=lambda: {}), raising=False)
    row = _pin_agy(task)
    delegate._route_runner(row, "developer", "test-host")
    assert pick_runner.called is routed


@pytest.mark.parametrize("runner,model,fits", [
    ("codex", "gemini-4-argon-high", False),   # task-c7065d2a, 12 Nov: codex 400 model_not_found
    ("codex", "gpt-6-luna:high", True),
    ("codex", "astra", True),
    ("agy", "gpt-6-sol", False),
    ("agy", "gemini-4-argon-high", True),
    ("agy", "claude-sonnet-5-5-high", True),
    ("claude", "gemini-3.8-flash-high", False),
    ("claude", "sonnet", True),
    ("codex", "", True),
])
def test_a_model_from_another_runner_is_refused(runner, model, fits):
    assert delegate._model_fits_runner(runner, model) is fits


# 14 Nov (task-4ca6899a): a codex pin with gpt-6-astra:default sat in the host
# queue; at spawn the router moved it to agy (codex gate row 'over') and agy was
# launched with `--model gpt-6-astra:default` -> exit 1 "invalid model selection".

def _pin_codex_astra(task):
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET runner=?, runner_model=?, description=? WHERE id=?",
                     ("codex", "gpt-6-astra:default", "override: review — test\nd", task["id"]))
        conn.commit()
    return db_mod.get_task(task["id"])


def _codex_gate_over(monkeypatch):
    import tools.route as route
    monkeypatch.setattr(route, "usage_budget",
                        SimpleNamespace(load_gate_rows=lambda: {"codex": {"state": "over"}}),
                        raising=False)
    monkeypatch.setattr(route, "bucket_for", lambda cand, cfg: "codex")
    monkeypatch.setattr(route, "load_plans", lambda *a, **k: {})


@pytest.mark.parametrize("agy_model", ["claude-opus-5-5-medium", None])
def test_rerouted_manual_pin_hands_back_runner_and_model_together(
        task, pick_runner, monkeypatch, agy_model):
    from tools.route import Choice
    _codex_gate_over(monkeypatch)
    pick_runner.return_value = Choice(candidate=f"agy:{agy_model}", runner="agy", model=agy_model,
                                      bucket="agy-claude", weekly=0.9, daily=None, skill=None,
                                      reason="codex over")
    warning = Mock()
    monkeypatch.setattr(delegate, "warn", warning)
    row = _pin_codex_astra(task)

    assert delegate._route_runner(row, "developer", "test-host") == "agy"

    # The caller's dict carries the pair the router wrote, never agy + the codex model.
    assert (row["runner"], row["runner_model"]) == ("agy", agy_model)
    after = db_mod.get_task(task["id"])
    assert (after["runner"], after["runner_model"]) == ("agy", agy_model)
    pin_lines = [c.args[0] for c in warning.call_args_list if "manual pin" in c.args[0]]
    assert pin_lines == [f"router: manual pin codex:gpt-6-astra:default re-routed to "
                         f"agy:{agy_model} task={task['id']}"]


def test_unchanged_pin_logs_no_reroute_warning(task, pick_runner, monkeypatch):
    import tools.route as route
    monkeypatch.setattr(route, "usage_budget",
                        SimpleNamespace(load_gate_rows=lambda: {"codex": {"state": "ok"}}),
                        raising=False)
    monkeypatch.setattr(route, "bucket_for", lambda cand, cfg: "codex")
    monkeypatch.setattr(route, "load_plans", lambda *a, **k: {})
    warning = Mock()
    monkeypatch.setattr(delegate, "warn", warning)
    row = _pin_codex_astra(task)

    assert delegate._route_runner(row, "developer", "test-host") is None
    pick_runner.assert_not_called()
    assert (row["runner"], row["runner_model"]) == ("codex", "gpt-6-astra:default")
    assert not [c for c in warning.call_args_list if "manual pin" in c.args[0]]


@pytest.mark.parametrize("row_model,launched", [
    (None, None),                                       # agy pick with no model: launcher default
    ("claude-opus-5-5-medium", "claude-opus-5-5-medium"),
])
def test_spawn_remote_never_launches_a_fresh_runner_with_a_stale_model(
        task, monkeypatch, row_model, launched):
    """The queued spawn: the row says agy + the router's model, the caller's dict
    says agy (from the router's return) + the old codex model. The launcher must
    get the row's pair; on main the stale gpt-6-astra:default went through."""
    import asyncio
    import base64
    import json
    import re
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET project=?, runner=?, runner_model=?, host=?, branch=? WHERE id=?",
                     ("mooniex-agents", "agy", row_model, "contabo",
                      "agent/agy-task-router", task["id"]))
        conn.commit()
    stale = dict(db_mod.get_task(task["id"]))
    stale["runner_model"] = "gpt-6-astra:default"

    res = asyncio.run(delegate._spawn_remote(stale, "contabo", dry_run=True))

    log_text = res.get("delegate_log") or ""
    m = re.search(r"--task-meta-b64\s+(\S+)", log_text)
    assert m, log_text
    meta = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    assert meta.get("runner_model") == launched
    assert "--runner agy" in log_text or "--runner 'agy'" in log_text, log_text


def test_pair_runner_model_drops_a_model_the_runner_cannot_launch():
    got = delegate._pair_runner_model({"id": "t", "runner": "agy", "runner_model": "gpt-6-astra:default"},
                                      {"runner": None, "runner_model": None})
    assert got["runner_model"] is None
    keep = {"id": "t", "runner": "codex", "runner_model": "gpt-6-luna:high"}
    assert delegate._pair_runner_model(keep, {"runner": None, "runner_model": None}) is keep
