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

    pick_runner.assert_called_once_with("developer", "test-host", touches=ANY, brief=ANY)
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
    with db_mod.get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {field}=? WHERE id=?", (value, task["id"]))
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

    pick_runner.assert_called_once_with("developer", "test-host", touches=ANY, brief=ANY)
    assert db_mod.get_task(task["id"]) == task


def test_router_error_leaves_row_unchanged(task, pick_runner, monkeypatch):
    pick_runner.side_effect = RuntimeError("quota unavailable")
    warning = Mock()
    monkeypatch.setattr(delegate, "warn", warning)

    assert delegate._route_runner(task, "developer", "test-host") is None

    pick_runner.assert_called_once_with("developer", "test-host", touches=ANY, brief=ANY)
    assert db_mod.get_task(task["id"]) == task
    warning.assert_called_once_with(
        "router skipped task=task-router: quota unavailable")
