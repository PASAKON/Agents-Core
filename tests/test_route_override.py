"""Tests for route.check_override — IRON-RULES §59 rule 7.

All tests use tmp_path / monkeypatch fixtures only.  The real ledger is never
touched.
"""
from __future__ import annotations

import os
import pytest

from tools.route import check_override, reason_code, REASON_CODES, _IRON_59_MSG

# Minimal cfg with "developer" in role_classes (mirrors plans.yaml).
_CFG = {
    "role_classes": {"developer": "dev_general"},
    "roles": {"dev_general": ["claude:claude-sonnet-4-6", "agy:gemini-3.8-flash-high"]},
}


def _task(**kwargs) -> dict:
    """Build a minimal task dict with the given overrides."""
    base = {
        "id": "task-test",
        "role": "developer",
        "runner": None,
        "runner_model": None,
        "model_hint": None,
        "description": "",
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# 1. Role not in role_classes → None (router doesn't handle it; a pin is fine)
# ---------------------------------------------------------------------------
def test_role_not_routed_returns_none():
    task = _task(role="video_editor", runner="claude", runner_model=None)
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# 2. ORG_ROUTER=off → None (repair mode)
# ---------------------------------------------------------------------------
def test_org_router_off_returns_none(monkeypatch):
    monkeypatch.setenv("ORG_ROUTER", "off")
    task = _task(runner="claude", runner_model=None)
    assert check_override(task, _CFG) is None


def test_org_router_off_mixed_case_returns_none(monkeypatch):
    monkeypatch.setenv("ORG_ROUTER", "  OFF  ")
    task = _task(runner="claude", runner_model=None)
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# 3. runner AND runner_model both set (router-written row) → NOT a manual pin
# ---------------------------------------------------------------------------
def test_router_written_row_returns_none():
    task = _task(runner="agy", runner_model="gemini-3.8-flash-high")
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# 4. runner='claude', runner_model=None, no override line → refusal message
# ---------------------------------------------------------------------------
def test_runner_set_no_runner_model_no_override_returns_message(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    task = _task(runner="claude", runner_model=None, description="Do the thing.")
    result = check_override(task, _CFG)
    assert result == _IRON_59_MSG


# ---------------------------------------------------------------------------
# 5. runner='claude', runner_model=None, description has "override: ceo-order — CEO order"
# ---------------------------------------------------------------------------
def test_runner_set_with_override_line_returns_none(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    desc = "Do the thing.\noverride: ceo-order — CEO order\nMore text."
    task = _task(runner="claude", runner_model=None, description=desc)
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# 6. model_hint='claude', no override line → refusal message
# ---------------------------------------------------------------------------
def test_model_hint_no_override_returns_message(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    task = _task(model_hint="claude", description="Implement feature X.")
    result = check_override(task, _CFG)
    assert result == _IRON_59_MSG


# ---------------------------------------------------------------------------
# 7. "Override:   ab-test" — case-insensitive, leading/trailing space
# ---------------------------------------------------------------------------
def test_override_line_case_and_space_insensitive(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    desc = "Fix something.\n  Override:   ab-test\n"
    task = _task(runner="claude", runner_model=None, description=desc)
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# 8. "no override: here" embedded mid-sentence does NOT count
# ---------------------------------------------------------------------------
def test_embedded_override_not_at_line_start_does_not_count(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    desc = "There is no override: here in this description."
    task = _task(runner="claude", runner_model=None, description=desc)
    result = check_override(task, _CFG)
    assert result == _IRON_59_MSG


# ---------------------------------------------------------------------------
# 9. No pin at all → None (normal unset task)
# ---------------------------------------------------------------------------
def test_no_pin_returns_none(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    task = _task()  # runner=None, runner_model=None, model_hint=None
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# 10. Internal error → None (never raises)
# ---------------------------------------------------------------------------
def test_check_override_never_raises():
    # Pass something totally broken as a task
    assert check_override(None, _CFG) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Router-written codex row: "codex:" means the CLI default, so the router
# writes runner_model="" AND "router:" into delegate_log.
# ---------------------------------------------------------------------------
def test_router_written_codex_row_with_empty_model_returns_none(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    task = _task(runner="codex", runner_model="", delegate_log="router: codex")
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# Each of the 8 codes passes, including punctuation and upper-case
# ---------------------------------------------------------------------------
def test_all_8_codes_pass(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    for code in REASON_CODES:
        task = _task(runner="claude", description=f"override: {code} because reasons")
        assert check_override(task, _CFG) is None, f"code {code} should pass"

    # Specific tests for punctuation and casing
    task1 = _task(runner="claude", description="override: ceo-order — CEO said X")
    assert check_override(task1, _CFG) is None

    task2 = _task(runner="claude", description="override: Review")
    assert check_override(task2, _CFG) is None


# ---------------------------------------------------------------------------
# Refused: invalid codes, line 6, after blank line
# ---------------------------------------------------------------------------
def test_refused_override_cases(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)

    # 1. override: in-session Agent
    task_in_session = _task(runner="claude", description="override: in-session Agent")
    res = check_override(task_in_session, _CFG)
    assert res is not None
    assert '"in-session" is not a reason code.' in res
    assert res.startswith(_IRON_59_MSG)

    # 2. override: runner=claude
    task_runner = _task(runner="claude", description="override: runner=claude")
    res_runner = check_override(task_runner, _CFG)
    assert res_runner is not None
    assert '"runner=claude" is not a reason code.' in res_runner
    assert res_runner.startswith(_IRON_59_MSG)

    # 3. code on line 6 (outside header)
    desc_l6 = "1\n2\n3\n4\n5\noverride: ceo-order"
    task_l6 = _task(runner="claude", description=desc_l6)
    assert check_override(task_l6, _CFG) == _IRON_59_MSG

    # 4. code after the first blank line
    desc_blank = "first line\n\noverride: ceo-order"
    task_blank = _task(runner="claude", description=desc_blank)
    assert check_override(task_blank, _CFG) == _IRON_59_MSG


# ---------------------------------------------------------------------------
# Codex hand pin: runner "codex", runner_model "", delegate_log without "router:"
# ---------------------------------------------------------------------------
def test_codex_hand_pin(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)

    # Hand pin with no delegate_log is refused
    task_hand1 = _task(runner="codex", runner_model="", delegate_log="")
    assert check_override(task_hand1, _CFG) == _IRON_59_MSG

    # Hand pin with manual log is refused
    task_hand2 = _task(runner="codex", runner_model="", delegate_log="manual: dev pinned")
    assert check_override(task_hand2, _CFG) == _IRON_59_MSG

    # Routed row with "router: codex" in delegate_log is allowed
    task_routed = _task(runner="codex", runner_model="", delegate_log="router: codex  [codex] — reserve ok")
    assert check_override(task_routed, _CFG) is None


# ---------------------------------------------------------------------------
# Jules hint tests
# ---------------------------------------------------------------------------
def test_jules_hint(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)

    # Mock get_project and load_jules_config
    monkeypatch.setattr(
        "lib.config.get_project",
        lambda key: {"jules_repo": "PASAKON/Agents-Core"} if key == "mooniex-agents" else {},
    )
    monkeypatch.setattr(
        "tools.route.load_jules_config",
        lambda path=None: {"repos": [{"repo": "PASAKON/Agents-Core"}]},
    )

    # 1. Size-S task on mooniex-agents: Jules hint appears
    task_s = _task(
        runner="claude",
        project="mooniex-agents",
        title="Add widget",
        description="Add widget component",
        touches=["tools/a.py"],
    )
    res_s = check_override(task_s, _CFG)
    assert res_s is not None
    expected_hint = (
        'Jules can take this (size S/M, allowlisted repo): '
        'python tools/jules.py create --repo Agents-Core --title "Add widget" --brief brief.md'
    )
    assert expected_hint in res_s

    # 2. Absent when description contains "deploy"
    task_deploy = _task(
        runner="claude",
        project="mooniex-agents",
        title="Deploy app",
        description="deploy to staging server",
        touches=["tools/a.py"],
    )
    res_deploy = check_override(task_deploy, _CFG)
    assert res_deploy is not None
    assert "Jules can take this" not in res_deploy

    # 3. Absent when size is L
    task_l = _task(
        runner="claude",
        project="mooniex-agents",
        title="Large task",
        description="x" * 6001,
        touches=["tools/a.py"],
    )
    res_l = check_override(task_l, _CFG)
    assert res_l is not None
    assert "Jules can take this" not in res_l


# ---------------------------------------------------------------------------
# reason_code() unit tests
# ---------------------------------------------------------------------------
def test_reason_code_unit():
    assert reason_code("override: review") == "review"
    assert reason_code("override: Review") == "review"
    assert reason_code("override: ceo-order — CEO said X") == "ceo-order"
    assert reason_code("override: ab-test (experiment)") == "ab-test"
    assert reason_code("override: silent-wrong, risky") == "silent-wrong"
    assert reason_code("override: claude-tool. needed") == "claude-tool"
    assert reason_code("override: box-bound; mac only") == "box-bound"
    assert reason_code("override: quota-handoff: claude hit cap") == "quota-handoff"
    assert reason_code("override: in-session Agent") is None
    assert reason_code("override: runner=claude") is None
    assert reason_code("override: unknown-code") is None
    assert reason_code("no override here") is None
    assert reason_code(None) is None
    assert reason_code("1\n2\n3\n4\n5\noverride: review") is None
    assert reason_code("1\n\noverride: review") is None
