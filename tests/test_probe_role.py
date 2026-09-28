"""Tests for the `probe` worker role (task-c7309e8c, Org Mesh L3,
docs/ops/mesh-check.md). Pytest style, `tmp_path` DB fixture only (ADR
0021 SS1) -- never the real state/tasks.db.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_probe_role.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config  # noqa: E402
import lib.db as db_mod  # noqa: E402


def test_probe_role_pins_haiku_model():
    role = config.role("probe")
    assert role["model"] == "claude-haiku-4-5-20251001"


def test_probe_role_is_worker_tier():
    role = config.role("probe")
    assert role["level"] == "w"


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    """Isolated sqlite ledger -- never state/tasks.db (ADR 0021 SS1)."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return db_mod


def test_create_task_accepts_probe_role(temp_db):
    task_id = temp_db.create_task(
        project="mooniex-agents",
        role="probe",
        title="mesh-probe mac->contabo",
        description="mesh-check L3 probe (mac -> contabo).",
    )
    assert task_id.startswith("task-")
    task = temp_db.get_task(task_id)
    assert task["role"] == "probe"


def test_roles_probe_md_exists_and_documents_contract():
    text = (ROOT / "roles" / "probe.md").read_text()
    assert "docs/ops/mesh-probe/<from>-<to>.md" in text
    assert "mesh-probe:" in text
