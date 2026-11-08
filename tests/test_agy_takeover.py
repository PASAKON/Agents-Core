"""Unit tests for Cross-Host Claude Code -> AGY Takeover (`tools/agy_takeover.py`)."""
from __future__ import annotations

from pathlib import Path

from tools import agy_takeover


def test_format_handoff_markdown_includes_brief_mailbox_turns_and_skills(tmp_path):
    sample = {
        "host": "contabo",
        "uuid": "88d0d421-625d-4075-ab2b-fdc03511068d",
        "short_id": "3511068d",
        "kind": "project_head",
        "role_label": "project_head-3511068d",
        "project": "CnDrama",
        "owner": "cxo:cmo:fresh",
        "cwd": "/opt/MoonieXHQ/Agents/Core",
        "git_branch": "main",
        "quota_stopped": True,
        "last_ts": "2026-11-01T13:22:27Z",
        "brief": "# PH brief: CnDrama\nWrite EP02 script.",
        "drained_mailbox": ["[RUN-INBOX] : RUN-20261101-1157-77ce FAILED E_EXIT_NONZERO"],
        "recent_turns": [
            {"role": "user", "text": "Start EP02", "ts": "2026-11-01T13:00:00Z"},
            {"role": "assistant", "text": "You've hit your weekly limit", "ts": "2026-11-01T13:22:27Z"},
        ],
        "resolved_skills": [
            {"name": "CMO_Procedure_Colab_DirectRender", "path": "/opt/MoonieXHQ/Agents/Core/.claude/skills/CMO_Procedure_Colab_DirectRender/SKILL.md"}
        ],
    }
    saved = agy_takeover.save_handoff_bundle(sample, takeover_dir=tmp_path)
    text = saved.read_text(encoding="utf-8")
    assert "# Emergency AGY Takeover Brief: CnDrama" in text
    assert "CMO_Procedure_Colab_DirectRender" in text
    assert "RUN-20261101-1157-77ce FAILED" in text
    assert "Write EP02 script." in text
    assert (tmp_path / "latest-handoff.md").read_text(encoding="utf-8") == text


def test_resolve_local_skill_paths_finds_real_claude_skills():
    resolved = agy_takeover.resolve_local_skill_paths(["session-open", "NON_EXISTENT_SKILL_XYZ"])
    names = [r["name"] for r in resolved]
    assert "session-open" in names
    assert "NON_EXISTENT_SKILL_XYZ" not in names
    assert Path(resolved[0]["path"]).is_file()


def test_resolve_host_affinity_pins_cookierun_to_winbox_and_ea_to_contabo_winbox():
    cr = agy_takeover.resolve_host_affinity("cookierun-bot", r"C:\Users\passg\cookierun-bot", "winbox")
    assert cr["stay_on_host"] is True
    assert cr["pinned_host"] == "winbox"
    assert cr["allowed_hosts"] == ["winbox"]
    assert "mac" in cr["blocked_hosts"]
    assert "contabo" in cr["blocked_hosts"]

    ea = agy_takeover.resolve_host_affinity("mooniex-expertadvisor", "/opt/MoonieXHQ/Projects/MoonieX/ExpertAdvisor", "contabo")
    assert ea["stay_on_host"] is True
    assert ea["pinned_host"] == "contabo"
    assert ea["runtime_host"] == "winbox"
    assert "mac" in ea["blocked_hosts"]


def test_evaluate_preflight_blocks_moving_cookierun_off_winbox():
    info = {
        "host": "winbox",
        "short_id": "cr123456",
        "project": "cookierun-bot",
        "cwd": r"C:\Users\passg\cookierun-bot",
        "env_probe": {
            "cwd": r"C:\Users\passg\cookierun-bot",
            "cwd_exists": True,
            "git_ready": True,
            "venv_python": r"C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe",
            "has_package_json": False,
            "node_modules_ready": True,
            "disk_free_gb": 120.0,
            "tools": {"git": "git", "python": "python.exe"},
            "local_large_items": ["label_review/ (local data dir)"],
        },
    }
    # Staying on winbox -> READY, zero package reinstall rule
    pf_ok = agy_takeover.evaluate_preflight(info, requested_host="winbox")
    assert pf_ok["ready"] is True
    assert pf_ok["status"] == "READY"
    assert r"C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe" in pf_ok["no_reinstall_rule"]
    assert "NEVER run pip install" in pf_ok["no_reinstall_rule"]

    # Trying to move CookieRun to mac or contabo -> BLOCKED_WRONG_HOST
    pf_mac = agy_takeover.evaluate_preflight(info, requested_host="mac")
    assert pf_mac["ready"] is False
    assert pf_mac["status"] == "BLOCKED_WRONG_HOST"
    assert any("Host-Affinity Violation" in r for r in pf_mac["block_reasons"])


def test_evaluate_preflight_blocks_cross_host_drift_and_missing_cwd():
    info = {
        "host": "contabo",
        "short_id": "3511068d",
        "project": "CnDrama",
        "cwd": "/opt/MoonieXHQ/Agents/Core",
        "env_probe": {
            "cwd": "/opt/MoonieXHQ/Agents/Core",
            "cwd_exists": True,
            "git_ready": True,
            "venv_python": "/opt/MoonieXHQ/Agents/Core/.venv/bin/python",
            "has_package_json": False,
            "node_modules_ready": True,
            "disk_free_gb": 48.5,
            "tools": {"git": "/usr/bin/git", "agy": "/root/.local/bin/agy"},
            "local_large_items": [],
        },
    }
    pf_drift = agy_takeover.evaluate_preflight(info, requested_host="mac")
    assert pf_drift["ready"] is False
    assert pf_drift["status"] == "BLOCKED_WRONG_HOST"

    info_missing = dict(info)
    info_missing["env_probe"] = dict(info["env_probe"], cwd_exists=False)
    pf_missing = agy_takeover.evaluate_preflight(info_missing, requested_host="contabo")
    assert pf_missing["ready"] is False
    assert pf_missing["status"] == "MISSING_ENV"


def test_resume_in_place_dry_run_and_refuses_wrong_host(monkeypatch, tmp_path):
    monkeypatch.setattr(agy_takeover, "TAKEOVER_DIR", tmp_path)
    sample = {
        "host": "winbox",
        "uuid": "11112222-3333-4444-5555-666677778888",
        "short_id": "77778888",
        "kind": "worker",
        "role_label": "task-77778888",
        "project": "cookierun-bot",
        "owner": "cto",
        "cwd": r"C:\Users\passg\cookierun-bot",
        "git_branch": "main",
        "quota_stopped": True,
        "last_ts": "2026-11-08T15:00:00Z",
        "env_probe": {
            "cwd": r"C:\Users\passg\cookierun-bot",
            "cwd_exists": True,
            "git_ready": True,
            "venv_python": r"C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe",
            "has_package_json": False,
            "node_modules_ready": True,
            "disk_free_gb": 95.0,
            "tools": {"python": "python.exe"},
            "local_large_items": ["label_review/ (local data dir)"],
        },
    }
    monkeypatch.setattr(agy_takeover, "inspect_target", lambda *a, **kw: dict(sample))

    res = agy_takeover.resume_in_place("cookierun-bot", dry_run=True)
    assert res["ok"] is True
    assert res["source_host"] == "winbox"
    assert res["status"] == "READY"

    import pytest
    with pytest.raises(ValueError, match="BLOCKED_WRONG_HOST"):
        agy_takeover.resume_in_place("cookierun-bot", target_host="mac", dry_run=True)

