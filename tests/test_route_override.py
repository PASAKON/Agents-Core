"""Tests for route.check_override — IRON-RULES §59.

All tests use tmp_path / monkeypatch fixtures only.  The real ledger is never
touched.
"""
import os
import pytest

from tools.route import check_override, _IRON_59_MSG

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
# 5. runner='claude', runner_model=None, description has "override: CEO order"
# ---------------------------------------------------------------------------
def test_runner_set_with_override_line_returns_none(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    desc = "Do the thing.\noverride: CEO order\nMore text."
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
# 7. "Override:   A/B test" — case-insensitive, leading/trailing space
# ---------------------------------------------------------------------------
def test_override_line_case_and_space_insensitive(monkeypatch):
    monkeypatch.delenv("ORG_ROUTER", raising=False)
    desc = "Fix something.\n  Override:   A/B test\n"
    task = _task(runner="claude", runner_model=None, description=desc)
    assert check_override(task, _CFG) is None


# ---------------------------------------------------------------------------
# 8. "no override: here" embedded mid-sentence does NOT count
#    (regex is anchored at line start with ^\s*override:\s*\S)
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
