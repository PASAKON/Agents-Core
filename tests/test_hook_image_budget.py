"""Tests for scripts/hook-image-budget.py (task-17f60167, IRON-RULES §42).

Covers every case named in the task brief: the soft threshold (8 images
allowed, the 9th nudged once then the identical retry passes), the
exemptions (worker worktree cwd, WORKER_TASK_ID), fail-open on malformed
stdin, and that a non-image Read is never counted.

Run standalone:   python -m pytest tests/test_hook_image_budget.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = ROOT / "scripts" / "hook-image-budget.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("hook_image_budget_under_test", HOOK_SRC)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load_hook()


def _run(monkeypatch: pytest.MonkeyPatch, state_dir: Path, event: dict) -> tuple[int, str]:
    monkeypatch.setattr(MOD, "STATE_DIR", state_dir)
    monkeypatch.delenv("ORG_IMAGE_BUDGET", raising=False)
    monkeypatch.delenv("WORKER_TASK_ID", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    rc = MOD.main()
    return rc, err.getvalue()


def _read_event(session: str, file_path: str, cwd: str = "/Users/gob/MoonieXHQ/Agents/Core") -> dict:
    return {
        "session_id": session,
        "cwd": cwd,
        "tool_name": "Read",
        "tool_input": {"file_path": file_path},
    }


def _screenshot_event(session: str, cwd: str = "/Users/gob/MoonieXHQ/Agents/Core") -> dict:
    return {
        "session_id": session,
        "cwd": cwd,
        "tool_name": "mcp__claude-in-chrome__computer",
        "tool_input": {"action": "screenshot", "tabId": 1},
    }


# --------------------------------------------------------------------------
# non-image calls are never counted
# --------------------------------------------------------------------------

def test_read_of_py_file_allowed_and_not_counted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc, err = _run(monkeypatch, tmp_path, _read_event("s1", "/repo/scripts/foo.py"))
    assert rc == 0
    assert err == ""
    assert not (tmp_path / "s1.json").exists()


# --------------------------------------------------------------------------
# threshold: 8 images allowed, 9th nudged once, identical retry passes
# --------------------------------------------------------------------------

def test_eight_images_all_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for i in range(8):
        rc, err = _run(monkeypatch, tmp_path, _read_event("s2", f"/repo/shots/{i}.png"))
        assert rc == 0, f"image {i + 1} should pass"
        assert err == ""


def test_ninth_image_blocked_once_then_identical_retry_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for i in range(8):
        rc, _ = _run(monkeypatch, tmp_path, _read_event("s3", f"/repo/shots/{i}.png"))
        assert rc == 0

    ninth = _read_event("s3", "/repo/shots/ninth.png")

    rc, err = _run(monkeypatch, tmp_path, ninth)
    assert rc == 2
    assert "IRON" in err
    assert "9" in err

    # identical retry (same tool_name + tool_input) passes silently
    rc, err = _run(monkeypatch, tmp_path, ninth)
    assert rc == 0
    assert err == ""

    # never block the same call twice: a third identical call still passes
    rc, err = _run(monkeypatch, tmp_path, ninth)
    assert rc == 0
    assert err == ""


def test_different_tenth_image_blocked_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for i in range(8):
        rc, _ = _run(monkeypatch, tmp_path, _read_event("s4", f"/repo/shots/{i}.png"))
        assert rc == 0

    ninth = _read_event("s4", "/repo/shots/ninth.png")
    rc, _ = _run(monkeypatch, tmp_path, ninth)
    assert rc == 2
    rc, _ = _run(monkeypatch, tmp_path, ninth)  # retry, now counted -> count=9
    assert rc == 0

    tenth = _read_event("s4", "/repo/shots/tenth.png")
    rc, err = _run(monkeypatch, tmp_path, tenth)
    assert rc == 2
    assert "10" in err

    rc, err = _run(monkeypatch, tmp_path, tenth)
    assert rc == 0
    assert err == ""


def test_screenshot_action_counted_as_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for i in range(8):
        rc, _ = _run(monkeypatch, tmp_path, _screenshot_event("s5"))
        assert rc == 0

    rc, err = _run(monkeypatch, tmp_path, _screenshot_event("s5"))
    assert rc == 2
    assert "IRON" in err


def test_zoom_action_counted_as_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "session_id": "s5b",
        "cwd": "/Users/gob/MoonieXHQ/Agents/Core",
        "tool_name": "mcp__claude-in-chrome__computer",
        "tool_input": {"action": "zoom", "tabId": 1, "region": [0, 0, 10, 10]},
    }
    for i in range(8):
        rc, _ = _run(monkeypatch, tmp_path, event)
        assert rc == 0
    rc, err = _run(monkeypatch, tmp_path, event)
    assert rc == 2


def test_click_action_not_counted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "session_id": "s5c",
        "cwd": "/Users/gob/MoonieXHQ/Agents/Core",
        "tool_name": "mcp__claude-in-chrome__computer",
        "tool_input": {"action": "left_click", "tabId": 1, "coordinate": [1, 1]},
    }
    for _ in range(20):
        rc, err = _run(monkeypatch, tmp_path, event)
        assert rc == 0
        assert err == ""


def test_browser_batch_with_nested_screenshot_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def batch_event(marker: str) -> dict:
        return {
            "session_id": "s6",
            "cwd": "/Users/gob/MoonieXHQ/Agents/Core",
            "tool_name": "mcp__claude-in-chrome__browser_batch",
            "tool_input": {
                "actions": [
                    {"name": "navigate", "input": {"url": f"https://example.com/{marker}"}},
                    {"name": "computer", "input": {"action": "screenshot", "tabId": 1}},
                ]
            },
        }

    for i in range(8):
        rc, _ = _run(monkeypatch, tmp_path, batch_event(str(i)))
        assert rc == 0

    rc, err = _run(monkeypatch, tmp_path, batch_event("ninth"))
    assert rc == 2
    assert "IRON" in err


# --------------------------------------------------------------------------
# exemptions
# --------------------------------------------------------------------------

def test_worker_worktree_cwd_exempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = "/Users/gob/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-abc/"
    for i in range(20):
        rc, err = _run(monkeypatch, tmp_path, _read_event("s7", f"/repo/shots/{i}.png", cwd=cwd))
        assert rc == 0
        assert err == ""
    assert not any(tmp_path.iterdir())


def test_worker_task_id_env_exempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MOD, "STATE_DIR", tmp_path)
    monkeypatch.setenv("WORKER_TASK_ID", "task-abc12345")
    for i in range(20):
        monkeypatch.setattr(
            sys, "stdin", io.StringIO(json.dumps(_read_event("s8", f"/repo/shots/{i}.png")))
        )
        err = io.StringIO()
        monkeypatch.setattr(sys, "stderr", err)
        rc = MOD.main()
        assert rc == 0
        assert err.getvalue() == ""
    assert not any(tmp_path.iterdir())


# --------------------------------------------------------------------------
# fail-open
# --------------------------------------------------------------------------

def test_malformed_stdin_fails_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MOD, "STATE_DIR", tmp_path)
    monkeypatch.delenv("WORKER_TASK_ID", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json {{{"))
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    rc = MOD.main()
    assert rc == 0
    assert err.getvalue() == ""


def test_missing_tool_input_fails_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {"session_id": "s9", "cwd": "/Users/gob/MoonieXHQ/Agents/Core", "tool_name": "Read"}
    rc, err = _run(monkeypatch, tmp_path, event)
    assert rc == 0
    assert err == ""


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
