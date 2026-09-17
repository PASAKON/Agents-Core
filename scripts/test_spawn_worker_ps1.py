"""Static checks on windows/spawn-worker.ps1 (GH #151, #152).

This script can't run on the Mac — no PowerShell, no Windows Terminal, no
winbox. Real end-to-end verification is a Mac->winbox ssh smoke test (see
the task report), and full "does claude.exe actually launch" verification
is the CTO's own job (task brief: "ห้าม launch claude จริง"). What CAN be
verified here, without a Windows box, is that the .ps1 TEXT actually
contains the required steps, in the required order — a regression that
silently deletes one of these lines is exactly the kind of thing a human
skimming a large diff misses.

Iteration 1 (2026-09-18 CTO review): the launcher piped claude.exe's output
through `| Tee-Object` for a worker.log. Claude Code is an Ink TUI -- a
non-TTY stdout makes it silently drop into --print mode and exit immediately,
killing every winbox spawn. Reverted; `test_launcher_line_is_not_piped` below
is the regression test for exactly this. worker.log and its tee are gone for
good -- #152's "what is it doing" is served by tools/remote_worker_log.py
(reads Claude Code's own JSONL transcript) instead.

Run via: pytest scripts/test_spawn_worker_ps1.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "windows" / "spawn-worker.ps1"

STALE_FILES = ("REPORT.md", "BLOCKER.md", "MAILBOX.md", "HEARTBEAT")


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _code_only() -> str:
    """`_text()` with full-line `#` comments stripped -- so a check for
    whether some pattern is actually USED can't be defeated (or falsely
    tripped) by an explanatory comment merely mentioning it."""
    return "\n".join(
        ln for ln in _text().splitlines() if not ln.strip().startswith("#")
    )


def test_script_exists():
    assert SCRIPT.is_file()


def test_all_stale_files_named_for_cleanup():
    """GH #151: every one of the 4 stale-file names must appear literally
    (defense against a copy-paste that drops one). worker.log is NOT one of
    them (iteration 1 review): nothing writes it any more."""
    text = _text()
    for name in STALE_FILES:
        assert name in text, f"{name!r} not found in spawn-worker.ps1 at all"


def test_worker_log_is_gone():
    """Iteration 1 regression guard: worker.log (and its tee) must not come
    back without also reverting the Ink-TUI-killing pipe. Checks actual
    usage (variable/cmdlet), not the word appearing in an explanatory
    comment about why it was removed."""
    code = _code_only()
    assert "Tee-Object" not in code
    assert "$workerLogPath" not in code
    assert "worker.log" not in code


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


def test_launcher_line_is_not_piped():
    """CTO review 2026-09-18: the launcher's `& $claudeExe @argArray` call
    must be a bare invocation, never piped into anything. Claude Code (Ink
    TUI) treats a non-TTY stdout as --print mode and exits immediately with
    "Input must be provided either through stdin or as a prompt argument
    when using --print" -- measured to kill every winbox spawn within ~12s.
    """
    text = _text()
    m = re.search(r"^&\s*`\$claudeExe\s+@argArray.*$", text, re.MULTILINE)
    assert m, "launcher invocation of $claudeExe not found"
    assert "|" not in m.group(0), (
        f"launcher line pipes claude.exe's output -- this kills the worker: {m.group(0)!r}"
    )


def test_heartbeat_and_mailbox_added_to_info_exclude():
    """GH #150/#152 review: HEARTBEAT and MAILBOX.md must be git-excluded
    via the clone's shared info/exclude (never the project's own .gitignore,
    which must stay generic across any repo cloned on this box), so neither
    ever gets swept into a `git add -A` commit."""
    text = _text()
    assert "rev-parse --git-path info/exclude" in text
    exclude_idx = text.index("rev-parse --git-path info/exclude")
    tail = text[exclude_idx:exclude_idx + 800]
    assert "HEARTBEAT" in tail
    assert "MAILBOX.md" in tail
    # Must not touch the project's own .gitignore for this (only mentioned
    # in the explaining comment, never as an actual write target).
    assert ".gitignore" not in _code_only()


def test_info_exclude_step_happens_after_worktree_add():
    text = _text()
    add_idx = text.index('worktree add -b $Branch $wt "origin/$Base"')
    exclude_idx = text.index("rev-parse --git-path info/exclude")
    assert add_idx < exclude_idx


def test_info_exclude_path_is_resolved_against_repopath():
    """Regression guard (measured live on winbox 2026-09-18): `git -C
    $RepoPath rev-parse --git-path info/exclude` returns a path RELATIVE TO
    $RepoPath, not to this process's own cwd -- using it bare resolved to
    the ssh session's home dir instead of the real .git\\info\\exclude, and
    Add-Content failed silently (HEARTBEAT/MAILBOX.md still showed up in
    `git status`). The result must be joined against $RepoPath whenever it
    isn't already rooted."""
    code = _code_only()
    assert "IsPathRooted" in code, (
        "info/exclude path must be checked for IsPathRooted and joined "
        "against $RepoPath when relative -- see FEEDBACK-1.md follow-up"
    )
    assert re.search(r"Join-Path\s+\$RepoPath\s+\$excludeRel", code)
