"""Tests for quota self-host alias resolution and local reading (task-a1985bc5)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import pytest

from lib import config
from tools.quota import _ssh_target, fetch_claude


def test_ssh_target_self_alias_returns_none(monkeypatch):
    """When self_host's alias equals the configured alias, _ssh_target returns None."""
    monkeypatch.setattr(config, "self_host", lambda: "contabo")
    # In config/hosts.yaml, contabo has ssh: mooniex-vps
    assert _ssh_target("mooniex-vps") is None


def test_ssh_target_different_alias_returns_alias(monkeypatch):
    """When alias is different from self_host's alias, _ssh_target returns the alias."""
    monkeypatch.setattr(config, "self_host", lambda: "contabo")
    assert _ssh_target("winbox") == "winbox"
    assert _ssh_target("other-host") == "other-host"

    monkeypatch.setattr(config, "self_host", lambda: "mac")
    # On mac, ssh is None in config/hosts.yaml
    assert _ssh_target("mooniex-vps") == "mooniex-vps"


def test_ssh_target_self_host_raises_runtime_error(monkeypatch):
    """When self_host raises RuntimeError, _ssh_target returns the alias unchanged."""
    def _raise():
        raise RuntimeError("cannot resolve self_host")

    monkeypatch.setattr(config, "self_host", _raise)
    assert _ssh_target("mooniex-vps") == "mooniex-vps"


def test_ssh_target_host_raises_exception(monkeypatch):
    """When config.host raises an exception, _ssh_target returns the alias unchanged."""
    monkeypatch.setattr(config, "self_host", lambda: "unknown-box")
    assert _ssh_target("mooniex-vps") == "mooniex-vps"


def test_ssh_target_none():
    """Falsy alias returns None."""
    assert _ssh_target(None) is None
    assert _ssh_target("") is None


def test_fetch_claude_self_alias_reads_locally(tmp_path, monkeypatch):
    """fetch_claude with the self alias reads a tmp_path usage.json locally without subprocess.run."""
    usage_file = tmp_path / "usage.json"
    usage_data = {
        "five_hour": {"utilization": 17.0, "resets_at": "2026-09-29T03:10:00+00:00"},
        "seven_day": {"utilization": 98.0, "resets_at": "2026-09-29T10:00:00+00:00"},
    }
    usage_file.write_text(json.dumps(usage_data))

    monkeypatch.setattr(config, "self_host", lambda: "contabo")

    def _fail_subprocess(*args, **kwargs):
        pytest.fail("subprocess.run must not be called when reading local usage.json")

    monkeypatch.setattr(subprocess, "run", _fail_subprocess)

    cfg = {
        "quota_sources": {
            "claude": {
                "ssh": "mooniex-vps",
                "path": str(usage_file),
            }
        }
    }
    quota = fetch_claude(cfg)
    assert quota.error is None
    assert quota.weekly_remaining == 0.02
    assert quota.daily_remaining == 0.83
    assert quota.weekly_resets_at == "2026-09-29T10:00:00+00:00"
    assert quota.daily_resets_at == "2026-09-29T03:10:00+00:00"
    assert quota.source == str(usage_file)


def test_fetch_claude_self_alias_reads_locally_via_load_plans(tmp_path, monkeypatch):
    """fetch_claude with self alias when relying on load_plans()."""
    usage_file = tmp_path / "usage.json"
    usage_data = {
        "five_hour": {"utilization": 17.0, "resets_at": "2026-09-29T03:10:00+00:00"},
        "seven_day": {"utilization": 98.0, "resets_at": "2026-09-29T10:00:00+00:00"},
    }
    usage_file.write_text(json.dumps(usage_data))

    monkeypatch.setattr(config, "self_host", lambda: "contabo")

    def _fail_subprocess(*args, **kwargs):
        pytest.fail("subprocess.run must not be called when reading local usage.json")

    monkeypatch.setattr(subprocess, "run", _fail_subprocess)

    mock_cfg = {
        "quota_sources": {
            "claude": {
                "ssh": "mooniex-vps",
                "path": str(usage_file),
            }
        }
    }
    monkeypatch.setattr("tools.quota.load_plans", lambda path=None: mock_cfg)

    quota = fetch_claude()
    assert quota.error is None
    assert quota.weekly_remaining == 0.02
    assert quota.daily_remaining == 0.83
    assert quota.source == str(usage_file)
