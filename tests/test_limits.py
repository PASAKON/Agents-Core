"""Tests for tools/limits.py.

Covers:
- load_limits defaults when file missing
- validate limits against plans.yaml buckets and valid key ranges
- render produces deterministic flow style YAML with header
- set_limit round trip and rejected values leaving file unchanged
- CLI commands: show, set, validate
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import limits


@pytest.fixture
def mock_plans_cfg():
    return {
        "buckets": {
            "claude": {"provider": "anthropic"},
            "codex": {"provider": "openai"},
            "agy-gemini": {"provider": "google"},
            "agy-claude": {"provider": "google"},
        }
    }


def test_load_limits_missing_file_returns_defaults(tmp_path, monkeypatch):
    nonexistent = tmp_path / "limits.yaml"
    monkeypatch.setattr(limits, "LIMITS_PATH", nonexistent)

    data = limits.load_limits()
    assert data == limits.DEFAULT_LIMITS
    assert "claude" in data
    assert data["claude"]["plan_usd"] == 20
    assert data["claude"]["reserve_pct"] == 50
    assert data["claude"]["min_5h_pct"] == 30


def test_validate_limits(mock_plans_cfg):
    valid = {
        "claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30},
        "codex": {"plan_usd": 20, "reserve_pct": 20, "min_5h_pct": 0},
    }
    assert limits.validate(valid, mock_plans_cfg) == []

    # Unknown bucket
    unknown_bucket = {"unknown_b": {"plan_usd": 10, "reserve_pct": 10, "min_5h_pct": 10}}
    errs = limits.validate(unknown_bucket, mock_plans_cfg)
    assert any("not in plans.yaml buckets" in e for e in errs)

    # Invalid keys
    invalid_keys = {"claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30, "extra": 1}}
    errs = limits.validate(invalid_keys, mock_plans_cfg)
    assert any("invalid key 'extra'" in e for e in errs)

    # Value out of bounds: plan_usd <= 0
    bad_plan = {"claude": {"plan_usd": 0, "reserve_pct": 50, "min_5h_pct": 30}}
    errs = limits.validate(bad_plan, mock_plans_cfg)
    assert any("plan_usd must be a number > 0" in e for e in errs)

    # Value out of bounds: reserve_pct > 100 or < 0
    bad_reserve = {"claude": {"plan_usd": 20, "reserve_pct": 105, "min_5h_pct": 30}}
    errs = limits.validate(bad_reserve, mock_plans_cfg)
    assert any("reserve_pct must be between 0 and 100" in e for e in errs)

    # Value out of bounds: min_5h_pct < 0
    bad_5h = {"claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": -1}}
    errs = limits.validate(bad_5h, mock_plans_cfg)
    assert any("min_5h_pct must be between 0 and 100" in e for e in errs)


def test_render_deterministic_flow_style():
    data = {
        "agy-gemini": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
        "claude": {"plan_usd": 20, "reserve_pct": 50, "min_5h_pct": 30},
        "codex": {"plan_usd": 20, "reserve_pct": 20, "min_5h_pct": 0},
        "agy-claude": {"plan_usd": 100, "reserve_pct": 10, "min_5h_pct": 10},
    }
    rendered = limits.render(data)
    assert "change with: .venv/bin/python tools/limits.py set <bucket>.<key> <value>" in rendered
    assert "buckets:" in rendered

    # Verify deterministic order: claude, codex, agy-gemini, agy-claude
    claude_pos = rendered.find("claude:")
    codex_pos = rendered.find("codex:")
    gemini_pos = rendered.find("agy-gemini:")
    claude_agy_pos = rendered.find("agy-claude:")
    assert 0 < claude_pos < codex_pos < gemini_pos < claude_agy_pos

    # Valid YAML load
    parsed = yaml.safe_load(rendered)
    assert parsed["buckets"]["claude"]["plan_usd"] == 20
    assert parsed["buckets"]["claude"]["reserve_pct"] == 50


def test_set_limit_round_trip_and_rejected_value_leaves_file_unchanged(tmp_path, monkeypatch, mock_plans_cfg):
    target = tmp_path / "limits.yaml"
    monkeypatch.setattr(limits, "LIMITS_PATH", target)
    monkeypatch.setattr(limits, "load_plans", lambda path=None: mock_plans_cfg)

    # Initial write of default limits
    initial = limits.load_limits()
    target.write_text(limits.render(initial), encoding="utf-8")
    initial_content = target.read_text(encoding="utf-8")

    # Round trip update
    updated = limits.set_limit("claude", "reserve_pct", "40", path=target)
    assert updated["claude"]["reserve_pct"] == 40
    reloaded = limits.load_limits(target)
    assert reloaded["claude"]["reserve_pct"] == 40

    after_update_content = target.read_text(encoding="utf-8")
    assert "reserve_pct: 40" in after_update_content

    # Rejected value: reserve_pct > 100
    with pytest.raises(ValueError, match="reserve_pct must be between 0 and 100"):
        limits.set_limit("claude", "reserve_pct", "150", path=target)
    assert target.read_text(encoding="utf-8") == after_update_content

    # Rejected value: non-numeric string
    with pytest.raises(ValueError, match="invalid numeric value"):
        limits.set_limit("claude", "reserve_pct", "forty", path=target)
    assert target.read_text(encoding="utf-8") == after_update_content

    # Rejected value: unknown bucket
    with pytest.raises(ValueError, match="unknown bucket"):
        limits.set_limit("nonexistent", "reserve_pct", "20", path=target)
    assert target.read_text(encoding="utf-8") == after_update_content

    # Rejected value: unknown key
    with pytest.raises(ValueError, match="invalid limit key"):
        limits.set_limit("claude", "unknown_key", "20", path=target)
    assert target.read_text(encoding="utf-8") == after_update_content


def test_cli_show_set_validate(tmp_path, monkeypatch, capsys, mock_plans_cfg):
    target = tmp_path / "limits.yaml"
    monkeypatch.setattr(limits, "LIMITS_PATH", target)
    monkeypatch.setattr(limits, "load_plans", lambda path=None: mock_plans_cfg)

    # show
    rc = limits.main(["show"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "bucket" in out
    assert "claude" in out
    assert "agy-gemini" in out

    # validate valid
    rc = limits.main(["validate"])
    assert rc == 0

    # set
    rc = limits.main(["set", "claude.reserve_pct", "35"])
    assert rc == 0
    assert target.is_file()
    assert limits.load_limits(target)["claude"]["reserve_pct"] == 35

    # set invalid
    rc = limits.main(["set", "claude.reserve_pct", "200"])
    assert rc == 1
    err_out = capsys.readouterr().err
    assert "reserve_pct must be between 0 and 100" in err_out
