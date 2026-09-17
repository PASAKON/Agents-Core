"""Static checks on windows/spawn-worker.ps1 (GH #151, #152).

This script can't run on the Mac — no PowerShell, no Windows Terminal, no
winbox. Real end-to-end verification is a Mac->winbox ssh smoke test (see
the task report), and full "does claude.exe actually launch" verification
is the CTO's own job (task brief: "ห้าม launch claude จริง"). What CAN be
verified here, without a Windows box, is that the .ps1 TEXT actually
contains the required steps, in the required order — a regression that
silently deletes one of these lines is exactly the kind of thing a human
skimming a large diff misses.

Run via: pytest scripts/test_spawn_worker_ps1.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "windows" / "spawn-worker.ps1"

STALE_FILES = ("REPORT.md", "BLOCKER.md", "MAILBOX.md", "worker.log", "HEARTBEAT")


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_script_exists():
    assert SCRIPT.is_file()


def test_all_five_stale_files_named_for_cleanup():
    """GH #151: every one of the 5 stale-file names must appear literally
    (defense against a copy-paste that drops one)."""
    text = _text()
    for name in STALE_FILES:
        assert name in text, f"{name!r} not found in spawn-worker.ps1 at all"


def test_stale_file_cleanup_step_exists():
    """A loop/step that actually deletes the stale files — not just
    mentions their names in a comment."""
    text = _text()
    assert re.search(r"Remove-Item\s+-Force\s+\$stale", text), (
        "no 'Remove-Item -Force $stale...' cleanup step found"
    )
    assert "$staleFiles" in text


def test_stale_cleanup_happens_before_task_md_is_written():
    """GH #151's exact requirement: cleanup must land BEFORE TASK.md is
    written, so a fresh worker never even briefly holds another task's
    files."""
    text = _text()
    cleanup_idx = text.index("$staleFiles = @(")
    task_md_idx = text.index("Join-Path $wt 'TASK.md'")
    assert cleanup_idx < task_md_idx, (
        "stale-file cleanup must come before TASK.md is written"
    )


def test_dirty_worktree_refusal_present():
    """GH #151: an existing worktree with TRACKED uncommitted changes must
    refuse the spawn (never force-remove real WIP) and print the exact
    contract line the hub-side delegate.py greps for."""
    text = _text()
    assert "SPAWN_REFUSED=dirty-worktree" in text
    # Must actually check git status, not just print the refusal unconditionally.
    assert "status --porcelain" in text
    # Must ignore untracked-only entries ('??') when deciding dirty.
    assert "StartsWith('??')" in text or "StartsWith(\"??\")" in text


def test_dirty_check_precedes_force_remove():
    """The refusal must happen BEFORE any force-removal of the existing
    worktree — otherwise 'refuse' is dead code that never fires because the
    directory is already gone by the time it's checked."""
    text = _text()
    refuse_idx = text.index("SPAWN_REFUSED=dirty-worktree")
    remove_idx = text.index("worktree remove --force $wt")
    assert refuse_idx < remove_idx


def test_worker_log_tee_present():
    """GH #152: claude's stdout+stderr must be teed to worker.log while
    still rendering on the visible console (CEO watches the screen)."""
    text = _text()
    assert "worker.log" in text
    assert "Tee-Object" in text or "Start-Transcript" in text
    # The tee/transcript must actually wrap the claude.exe invocation, not
    # some unrelated command.
    assert re.search(r"claudeExe\s+@argArray\s+2>&1\s*\|\s*Tee-Object", text) or (
        "Start-Transcript" in text and "claudeExe" in text
    )


def test_worker_log_path_is_inside_worktree():
    """worker.log must live at the worktree root (same place REPORT.md/
    BLOCKER.md/HEARTBEAT/MAILBOX.md live), not beside the launcher scripts."""
    text = _text()
    assert re.search(r"workerLogPath\s*=\s*Join-Path\s+\$wt\s+'worker\.log'", text)
