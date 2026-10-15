"""Unit tests for tools/resume_worker.py.

Mocks subprocess.run, lib.db, and tools.delegate._owner_window_id so no test
ever opens an iTerm tab or touches the SQLite/Postgres hub.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import NamedTuple
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db  # noqa: E402
from tools import delegate, resume_worker  # noqa: E402


class MockEnv(NamedTuple):
    db_init: MagicMock
    get_task: MagicMock
    owner_window_id: MagicMock
    run: MagicMock


@pytest.fixture(autouse=True)
def mock_env(monkeypatch: pytest.MonkeyPatch) -> MockEnv:
    """Seal subprocess.run, lib.db, and _owner_window_id for every test."""
    m_init = MagicMock(name="db.init")
    m_get_task = MagicMock(name="db.get_task", return_value=None)
    m_winid = MagicMock(name="_owner_window_id", return_value=None)
    m_run = MagicMock(name="subprocess.run")

    def _forbid_db_conn(*_args, **_kwargs):
        raise AssertionError("real DB connection forbidden in unit tests")

    monkeypatch.setattr(db, "init", m_init)
    monkeypatch.setattr(db, "get_task", m_get_task)
    monkeypatch.setattr(db, "get_conn", _forbid_db_conn)
    monkeypatch.setattr(delegate, "_owner_window_id", m_winid)
    monkeypatch.setattr(resume_worker, "_owner_window_id", m_winid)
    monkeypatch.setattr(subprocess, "run", m_run)
    monkeypatch.setattr(resume_worker.subprocess, "run", m_run)

    return MockEnv(
        db_init=m_init,
        get_task=m_get_task,
        owner_window_id=m_winid,
        run=m_run,
    )


def _expected_cmd(display: str, role: str, task_id: str) -> str:
    tab_title = f"{display} ({task_id}) [RESUMED]"
    return (
        f"printf '\\\\033]1;{tab_title}\\\\007' && "
        f"cd '{resume_worker.ROOT}' && source .venv/bin/activate && "
        f"python -m runners.worker_resume {role} {task_id}"
    )


def test_soft_resume_when_session_id_present(mock_env: MockEnv) -> None:
    """Soft path is selected when the task row has a captured session_id."""
    mock_env.get_task.return_value = {
        "id": "task-soft01",
        "role": "developer",
        "status": "rate_limited",
        "session_id": "sess-uuid-1234",
        "owner_cto": "cto11111",
        "owner_role": "cto",
    }
    mock_env.owner_window_id.return_value = "1001"

    result = resume_worker.resume("task-soft01")

    assert result == "OK: resume tab opened for task-soft01 (mode=soft)"
    mock_env.db_init.assert_called_once_with()
    mock_env.get_task.assert_called_once_with("task-soft01")
    mock_env.run.assert_called_once()
    call_args, call_kwargs = mock_env.run.call_args
    assert call_kwargs == {"check": True}
    argv = call_args[0]
    assert isinstance(argv, list) and len(argv) == 3
    assert argv[0] == "osascript"
    assert argv[1] == "-e"
    expected_cmd = _expected_cmd("Developer", "developer", "task-soft01")
    assert f'write text "{expected_cmd}"' in argv[2]


def test_hard_resume_when_session_id_missing_or_empty(mock_env: MockEnv) -> None:
    """Hard path is selected when session_id is None, empty, or absent."""
    mock_env.get_task.return_value = {
        "id": "task-hard02",
        "role": "tester",
        "status": "rate_limited",
        "session_id": None,
        "owner_cto": "cto22222",
        "owner_role": "cto",
    }

    result = resume_worker.resume("task-hard02")

    assert result == "OK: resume tab opened for task-hard02 (mode=hard)"
    mock_env.run.assert_called_once()
    call_args, call_kwargs = mock_env.run.call_args
    assert call_kwargs == {"check": True}
    argv = call_args[0]
    assert argv[:2] == ["osascript", "-e"]
    expected_cmd = _expected_cmd("Tester", "tester", "task-hard02")
    assert f'write text "{expected_cmd}"' in argv[2]


def test_spawn_resume_tab_exact_argv_and_runner_command(mock_env: MockEnv) -> None:
    """_spawn_resume_tab builds the exact osascript argv and shell command."""
    mock_env.owner_window_id.return_value = "7777"

    resume_worker._spawn_resume_tab(
        "developer",
        "task-argv03",
        owner_cto="cto33333",
        owner_role="cto",
    )

    mock_env.run.assert_called_once()
    call_args, call_kwargs = mock_env.run.call_args
    assert len(call_args) == 1
    assert call_kwargs == {"check": True}
    argv = call_args[0]
    assert argv[0] == "osascript"
    assert argv[1] == "-e"
    script = argv[2]
    expected_cmd = _expected_cmd("Developer", "developer", "task-argv03")
    assert script.count(f'write text "{expected_cmd}"') == 2
    assert "Developer (task-argv03) [RESUMED]" in script
    assert "python -m runners.worker_resume developer task-argv03" in script


def test_unknown_task_id_returns_error_without_spawning(mock_env: MockEnv) -> None:
    """An unknown task id returns an ERROR string and does not spawn a tab."""
    mock_env.get_task.return_value = None

    result = resume_worker.resume("task-unknown99")

    assert result == "ERROR: task task-unknown99 not found"
    mock_env.db_init.assert_called_once_with()
    mock_env.get_task.assert_called_once_with("task-unknown99")
    mock_env.owner_window_id.assert_not_called()
    mock_env.run.assert_not_called()


def test_done_status_returns_error_without_spawning(mock_env: MockEnv) -> None:
    """A task with status == 'done' returns an ERROR string and does not spawn."""
    mock_env.get_task.return_value = {
        "id": "task-done01",
        "role": "developer",
        "status": "done",
        "session_id": "sess-done",
        "owner_cto": "cto11111",
        "owner_role": "cto",
    }

    result = resume_worker.resume("task-done01")

    assert result == "ERROR: task task-done01 already done; nothing to resume"
    mock_env.db_init.assert_called_once_with()
    mock_env.get_task.assert_called_once_with("task-done01")
    mock_env.owner_window_id.assert_not_called()
    mock_env.run.assert_not_called()


@pytest.mark.parametrize(
    "status",
    ["rate_limited", "stalled", "failed", "pending", "in_progress", "review", "cancelled"],
)
def test_other_statuses_are_resumed_by_current_code(
    mock_env: MockEnv, status: str
) -> None:
    """Current code only blocks status == 'done'; every other status spawns a tab."""
    mock_env.get_task.return_value = {
        "id": f"task-{status}",
        "role": "developer",
        "status": status,
        "session_id": "sess-xyz",
    }

    result = resume_worker.resume(f"task-{status}")

    assert result == f"OK: resume tab opened for task-{status} (mode=soft)"
    mock_env.db_init.assert_called_once_with()
    mock_env.run.assert_called_once()


def test_owner_window_id_passed_through_and_embedded_in_applescript(
    mock_env: MockEnv,
) -> None:
    """owner_cto and owner_role are passed to _owner_window_id and used in AppleScript."""
    mock_env.get_task.return_value = {
        "id": "task-cfo01",
        "role": "data_analyst",
        "status": "rate_limited",
        "session_id": "sess-cfo",
        "owner_cto": "cfo01234",
        "owner_role": "cfo",
    }
    mock_env.owner_window_id.return_value = "4821"

    result = resume_worker.resume("task-cfo01")

    assert result == "OK: resume tab opened for task-cfo01 (mode=soft)"
    mock_env.owner_window_id.assert_called_once_with("cfo01234", "cfo")
    script = mock_env.run.call_args[0][0][2]
    assert 'if "4821" is not "" then' in script
    assert "set targetWin to (first window whose id is (4821))" in script
    assert '(tabName contains "CFO Chat #") or (tabName contains "CFO #")' in script


def test_missing_owner_handled_with_cto_default_and_fallback_script(
    mock_env: MockEnv,
) -> None:
    """Missing owner_cto / owner_role defaults owner_role to 'cto' and skips winid match."""
    mock_env.get_task.return_value = {
        "id": "task-noowner",
        "role": "developer",
        "status": "rate_limited",
        "session_id": None,
        "owner_cto": None,
        "owner_role": None,
    }
    mock_env.owner_window_id.return_value = None

    result = resume_worker.resume("task-noowner")

    assert result == "OK: resume tab opened for task-noowner (mode=hard)"
    mock_env.owner_window_id.assert_called_once_with(None, "cto")
    script = mock_env.run.call_args[0][0][2]
    assert 'if "" is not "" then' in script
    assert "set targetWin to (first window whose id is (0))" in script
    assert '(tabName contains "CTO Chat #") or (tabName contains "CTO #")' in script


def test_cli_main_missing_arg_prints_usage_to_stderr_and_returns_1(
    mock_env: MockEnv,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() with no task_id prints usage to stderr and returns exit code 1."""
    monkeypatch.setattr(sys, "argv", ["tools/resume_worker.py"])

    rc = resume_worker.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert captured.err == "usage: python -m tools.resume_worker <task_id>\n"
    mock_env.db_init.assert_not_called()
    mock_env.run.assert_not_called()


def test_cli_main_with_task_id_prints_result_and_returns_0_for_good_and_bad_task(
    mock_env: MockEnv,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() prints resume(task_id) to stdout and returns 0 for both OK and ERROR tasks."""
    # 1. Good (resumable) task
    mock_env.get_task.return_value = {
        "id": "task-cli-ok",
        "role": "developer",
        "status": "rate_limited",
        "session_id": "sess-cli",
        "owner_cto": "cto12345",
        "owner_role": "cto",
    }
    monkeypatch.setattr(sys, "argv", ["tools/resume_worker.py", "task-cli-ok"])

    rc_ok = resume_worker.main()
    cap_ok = capsys.readouterr()
    assert rc_ok == 0
    assert cap_ok.out == "OK: resume tab opened for task-cli-ok (mode=soft)\n"
    assert cap_ok.err == ""

    # 2. Bad (unknown) task — current CLI still prints ERROR to stdout and returns 0
    mock_env.get_task.return_value = None
    monkeypatch.setattr(sys, "argv", ["tools/resume_worker.py", "task-cli-missing"])

    rc_bad = resume_worker.main()
    cap_bad = capsys.readouterr()
    assert rc_bad == 0
    assert cap_bad.out == "ERROR: task task-cli-missing not found\n"
    assert cap_bad.err == ""
