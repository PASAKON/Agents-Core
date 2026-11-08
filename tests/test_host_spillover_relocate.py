"""Tests for Cross-Host Auto-Spillover, Active Queue Notifications,
3-Tier Task/Data Relocation (`tools/relocate_task.py`), Red `[ย้ายงาน]` Run Card,
and Cross-Host PH Brain Continuity (`tools/ph_brain.py`)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lib import config, db, router
from tools import delegate, host_queue, ph_brain, relocate_task

NOW = datetime(2026, 11, 8, 16, 30, tzinfo=timezone.utc)


def _row(
    host: str,
    *,
    running: int = 0,
    max_workers: int = 3,
    ram_used_pct: float = 40.0,
    cpu_pct: float = 30.0,
    disk_used_pct: float = 40.0,
    ram_free_gb: float = 8.0,
    ceo_hold: bool | None = None,
    provides: list[str] | None = None,
) -> dict:
    ram_total = ram_free_gb / max(1.0 - ram_used_pct / 100.0, 0.05)
    facts: dict = {
        "ram_free_gb": ram_free_gb,
        "ram_total_gb": ram_total,
        "cpu_pct": cpu_pct,
        "free_gb": 100.0 - disk_used_pct,
        "disk_total_gb": 100.0,
    }
    if ceo_hold is not None:
        facts["ceo_hold"] = ceo_hold
    return {
        "host": host,
        "status": "online",
        "probed_at": NOW.isoformat(),
        "provides": provides or ["chrome", "ffmpeg"],
        "max_workers": max_workers,
        "running": running,
        "ram_free_gb": ram_free_gb,
        "load_per_core": cpu_pct / 100.0,
        "runners": ["claude", "codex", "agy"],
        "facts": facts,
    }


@pytest.mark.parametrize(
    "contabo_kwargs,expected_reason_prefix",
    [
        ({"running": 3, "max_workers": 3}, "full 3/3"),
        ({"ram_used_pct": 92.0}, "fill 92.0% (ram)"),
        ({"cpu_pct": 95.0, "ram_free_gb": 1.0}, "fill 95.0% (cpu)"),
        ({"disk_used_pct": 93.0}, "fill 93.0% (disk)"),
    ],
)
def test_contabo_full_auto_spills_over_to_mac_or_winbox(contabo_kwargs, expected_reason_prefix):
    """When Contabo is full (3/3 workers, or RAM/CPU/Disk >= 90%), even a task with
    host='contabo' automatically spills over to Mac or Winbox."""
    rows = [
        _row("contabo", **contabo_kwargs),
        _row("mac", running=0, max_workers=2, cpu_pct=20.0),
        _row("winbox", running=1, max_workers=3, cpu_pct=40.0, ceo_hold=False),
    ]
    task = {
        "id": "task-spill01",
        "project": "mooniex-agents",
        "role": "developer",
        "host": "contabo",
        "runner": "agy",
        "description": "Implement feature X",
    }
    pick = router.pick_host(task, hosts_rows=rows, now=NOW)
    assert pick.host in ("mac", "winbox")
    assert pick.rejected["contabo"].startswith(expected_reason_prefix)


def test_box_bound_tasks_do_not_spillover_automatically():
    """Tasks with override: box-bound, comfy-runpod-worker, or local CDP browser_operator
    stay on their pinned host when full."""
    rows = [
        _row("contabo", running=3, max_workers=3),
        _row("mac", running=0, max_workers=2),
    ]
    t_override = {
        "id": "task-bb1",
        "project": "mooniex-agents",
        "role": "developer",
        "host": "contabo",
        "runner": "agy",
        "description": "override: box-bound\n\nStay on contabo",
    }
    assert router.is_box_bound(t_override)
    assert router.pick_host(t_override, hosts_rows=rows, now=NOW).host is None

    t_browser = {
        "id": "task-bb2",
        "project": "mooniex-agents",
        "role": "browser_operator",
        "host": "contabo",
        "runner": "agy",
        "description": "Use tools/agy_browse.py on http://127.0.0.1:9280",
    }
    assert router.is_box_bound(t_browser)
    assert router.pick_host(t_browser, hosts_rows=rows, now=NOW).host is None


def test_guardrail_4_winbox_ceo_hold_blocks_worker_spillover():
    """Guardrail #4: When CEO holds the PC lease on Winbox (`ceo_hold=True`),
    workers do not spillover onto Winbox."""
    rows = [
        _row("contabo", running=3, max_workers=3),
        _row("winbox", running=0, max_workers=3, ceo_hold=True),
        _row("mac", running=0, max_workers=2),
    ]
    task = {
        "id": "task-lease1",
        "project": "mooniex-agents",
        "role": "developer",
        "host": "contabo",
        "runner": "agy",
        "description": "Fix bug",
    }
    pick = router.pick_host(task, hosts_rows=rows, now=NOW)
    assert pick.host == "mac"
    assert pick.rejected["winbox"] == "PC lease held or unknown"


def test_active_notification_when_all_hosts_full(monkeypatch, tmp_path):
    """When all hosts are full (`resolved_host is None`), `_delegate_task` enqueues
    the task in `host_queue` AND immediately notifies the owner via `send_to_cto.send`."""
    monkeypatch.setattr(host_queue, "QUEUE_PATH", tmp_path / "queue.jsonl")
    monkeypatch.setattr(router, "enabled", lambda: True)

    fake_task = {
        "id": "task-qnotify",
        "title": "Test queue notify",
        "project": "mooniex-agents",
        "role": "developer",
        "status": "pending",
        "host": "contabo",
        "owner_cto": "cto-main",
        "owner_role": "cto",
        "description": "Do work",
    }
    monkeypatch.setattr(delegate.db, "get_task", lambda tid: fake_task)
    monkeypatch.setattr(delegate.db, "set_fields", lambda *a, **kw: None)
    monkeypatch.setattr(
        delegate,
        "_route_host",
        lambda t, h: asyncio.sleep(0, result=(None, "no_host: contabo(full 3/3) mac(full 2/2) winbox(PC lease held)")),
    )

    sent_messages: list[tuple] = []
    monkeypatch.setattr(
        delegate.send_to_cto,
        "send",
        lambda tid, msg, **kw: sent_messages.append((tid, msg, kw)),
    )

    res = asyncio.run(delegate._delegate_task("task-qnotify"))
    assert res["id"] == "task-qnotify"
    assert len(host_queue.load()) == 1
    assert len(sent_messages) == 1
    tid, msg, kw = sent_messages[0]
    assert tid == "task-qnotify"
    assert "queued for host capacity (0 ahead)" in msg
    assert "contabo(full 3/3)" in msg


def test_portable_cndrama_and_video_editor_assessment():
    """CnDrama and video_editor tasks are portable across contabo, mac, and winbox
    without triggering a heavy-setup card when active files are <= 500 MB."""
    task = {
        "id": "task-cndrama01",
        "project": "CnDrama",
        "role": "video_editor",
        "host": "contabo",
        "description": "Cut EP12 of CnDrama with ffmpeg",
    }
    for target in ("mac", "winbox", "contabo"):
        res = relocate_task.assess_migration(
            task,
            target,
            source_host="contabo",
            work_bytes=120 * 1024 * 1024,  # 120 MB active episode files
        )
        assert res["ready"] is True
        assert res["portable"] is True
        assert res["missing_installs"] == []
        assert res["migration_card"] is None


def test_heavy_setup_builds_valid_red_run_card(monkeypatch):
    """When relocating requires installing heavy packages/tools (e.g. CookieRun to mac,
    or > 500 MB staging), `relocate_task` returns `requires_ceo_approval` with a
    RED `/run` Card (`risk='red'`, tag `[ย้ายงาน]`) that passes `ask_run.mcp_ask` dry-run."""
    cookie_task = {
        "id": "task-cookie99",
        "project": "cookierun-bot",
        "role": "developer",
        "status": "in_progress",
        "host": "winbox",
        "description": "Retrain ONNX obstacle detector on label_review/",
    }
    monkeypatch.setattr(relocate_task.db, "get_task", lambda tid: cookie_task)

    res = asyncio.run(
        relocate_task.relocate_task(
            "task-cookie99",
            target_host="mac",
            dry_run=True,
            confirmed=False,
            raise_card=True,
        )
    )
    assert res["ok"] is False
    assert res["status"] == "requires_ceo_approval"
    card = res["migration_card"]
    assert card is not None
    assert card["tag"] == "[ย้ายงาน]"
    assert card["risk"] == "red"
    assert card["why"].startswith("[ย้ายงาน] ต้องติดตั้ง:")
    assert "ยอมรับไหม?" in card["why"]
    assert len(card["why"]) <= 88
    assert len(card["expected"]) <= 88
    assert "|" not in card["why"] and "|" not in card["expected"]
    # Verify ask_run.mcp_ask dry_run accepted the card without Refused
    assert res["raised_card"]["dry_run"] is True
    assert res["raised_card"]["payload"]["risk"] == "red"


def test_3tier_file_classification_and_tmp_cleanup(tmp_path):
    """Active working files in `Work/<task-id>/{in,out}` are measured and classified
    into Tier 1 / Tier 2 / Tier 3, while `Work/<task-id>/tmp/` is excluded and cleaned up."""
    work_dir = tmp_path / "task-vid01"
    (work_dir / "in").mkdir(parents=True)
    (work_dir / "out").mkdir(parents=True)
    (work_dir / "tmp").mkdir(parents=True)

    (work_dir / "in" / "clip1.mp4").write_bytes(b"x" * 2048)
    (work_dir / "out" / "cut.mp4").write_bytes(b"y" * 1024)
    (work_dir / "tmp" / "cache.raw").write_bytes(b"z" * (20 * 1024 * 1024))

    measured = relocate_task.measure_active_work_bytes(work_dir)
    assert measured == 3072  # tmp/ is excluded
    assert relocate_task.classify_transfer_tier(0) == "tier1_git"
    assert relocate_task.classify_transfer_tier(measured) == "tier2_tailscale_rsync"
    assert relocate_task.classify_transfer_tier(600 * 1024 * 1024) == "tier3_gdrive_stage"

    clean_res = relocate_task.cleanup_source_artifacts(
        {"id": "task-vid01", "host": config.self_host()},
        work_dir=work_dir,
        dry_run=False,
    )
    assert clean_res["removed_tmp"] is True
    assert not (work_dir / "tmp").exists()
    assert (work_dir / "in" / "clip1.mp4").exists()


def test_ph_brain_cross_host_continuity(monkeypatch, tmp_path):
    """When a PH brain starts on a new host where `state/ph-brains/<ph_id>.json`
    does not exist yet, `load_brain_state(..., fetch_hub=True)` inherits `project`,
    `lane`, `owner`, `last_summary`, and `relocated_from_host` from `ph_state`."""
    monkeypatch.setattr(
        ph_brain,
        "_fetch_hub_ph_state",
        lambda pid: {
            "session_id": f"ph-{pid}",
            "project": "CnDrama",
            "lane": "cmo",
            "owner": "cmo-main",
            "host": "contabo",
            "model": "claude-opus-5-5-medium",
            "doing": "Completed EP04 script & voiceover; ready for ffmpeg cut.",
        },
    )
    state = ph_brain.load_brain_state("cndrama01", brains_dir=tmp_path, fetch_hub=True)
    assert state["project"] == "CnDrama"
    assert state["lane"] == "cmo"
    assert state["owner"] == "cmo-main"
    assert state["relocated_from_host"] == "contabo"
    assert "Completed EP04 script" in state["last_summary"]

    prompt = ph_brain.build_initial_prompt(
        ph_id=state["ph_id"],
        project=state["project"],
        lane=state["lane"],
        owner=state["owner"],
        message="Continue EP04 cut on Mac",
        previous_summary=state["last_summary"],
        relocated_from_host=state["relocated_from_host"],
    )
    assert "[Cross-Host Continuity Summary from previous PH turn on 'contabo']" in prompt
    assert "Completed EP04 script & voiceover" in prompt
