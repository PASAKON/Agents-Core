"""Subprocess-level tests for scripts/hook-inbox.py resolving ORG_ROOT
(GH #154, fix for task-3009a00d's undrained letter).

scripts/test_mailbox.py already covers hook-inbox.py in-process (import +
monkeypatch, same interpreter, same sys.path). That style can prove the
ORG_ROOT branch exists but can NEVER reproduce the actual bug: an in-process
import always resolves `Path(__file__)` against the one lib/mailbox.py
already on sys.path, so the worktree-vs-hub confusion never happens there.

These tests instead SPAWN `python3 scripts/hook-inbox.py` with cwd pointed
at a throwaway directory that carries its OWN copy of hook-inbox.py + lib/
(the same shape `${CLAUDE_PROJECT_DIR}/scripts/hook-inbox.py` produces for a
real DEV worktree) so `Path(__file__).resolve().parent.parent` inside that
subprocess genuinely resolves to the fake worktree, not this checkout.

Run standalone:   python scripts/test_hook_inbox.py
Or under pytest:  pytest scripts/test_hook_inbox.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_ENV_STRIP = (
    "ORG_ROOT", "WORKER_TASK_ID", "WORKER_ROLE",
    "CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID",
)


def _make_fake_worktree(tmp_path: Path) -> Path:
    """<tmp>/worktree/{scripts/hook-inbox.py, lib/{__init__.py, mailbox.py}}
    -- self-contained, same shape a real DEV worktree has. No state/ of its
    own, matching the real bug report (task-3009a00d's worktree had none)."""
    wt = tmp_path / "worktree"
    (wt / "scripts").mkdir(parents=True)
    (wt / "lib").mkdir(parents=True)
    shutil.copy(REPO_ROOT / "scripts" / "hook-inbox.py",
                wt / "scripts" / "hook-inbox.py")
    shutil.copy(REPO_ROOT / "lib" / "__init__.py", wt / "lib" / "__init__.py")
    shutil.copy(REPO_ROOT / "lib" / "mailbox.py", wt / "lib" / "mailbox.py")
    return wt


def _letter(body: str) -> str:
    return json.dumps({
        "from": {"role": "cto", "session_id": "abc"},
        "to": {"role": "developer", "session_id": "task-x"},
        "chain": ["cto:abc"],
        "sent_at": "2026-01-01T00:00:00Z",
        "body": body,
    })


def _run_hook(wt: Path, env_extra: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _ENV_STRIP}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(wt / "scripts" / "hook-inbox.py")],
        cwd=str(wt), input="{}", capture_output=True, text=True,
        env=env, timeout=15,
    )


def test_org_root_set_drains_the_hub_box(tmp_path: Path):
    """ORG_ROOT pointed at a fake hub -> the hook, run from the fake
    worktree, still finds and drains the hub's letter (the fix)."""
    wt = _make_fake_worktree(tmp_path)
    hub = tmp_path / "hub"
    box = hub / "state" / "inbox" / "developer-task-x"
    box.mkdir(parents=True)
    (box / "20260101T000000000000Z-cto-abc.json").write_text(
        _letter("ทดสอบ ORG_ROOT drains the hub box"), encoding="utf-8")

    result = _run_hook(wt, {
        "ORG_ROOT": str(hub),
        "WORKER_TASK_ID": "task-x",
        "WORKER_ROLE": "developer",
    })

    assert result.returncode == 0, result.stderr
    assert "ทดสอบ ORG_ROOT drains the hub box" in result.stdout
    assert list(box.glob("*.json")) == []           # drained -- exactly once
    assert not (wt / "state").exists()               # never touched the worktree


def test_without_org_root_nothing_drains(tmp_path: Path):
    """Same setup, ORG_ROOT simply absent -- the hook falls back to
    __file__, which resolves inside the fake WORKTREE (no state/ there), so
    the hub's letter is never seen and never drained. This documents
    today's pre-ORG_ROOT behaviour explicitly rather than leaving it an
    assumption: the fallback is exercised, not just declared."""
    wt = _make_fake_worktree(tmp_path)
    hub = tmp_path / "hub"
    box = hub / "state" / "inbox" / "developer-task-x"
    box.mkdir(parents=True)
    letter = box / "20260101T000000000000Z-cto-abc.json"
    letter.write_text(_letter("should never surface without ORG_ROOT"),
                       encoding="utf-8")

    result = _run_hook(wt, {
        "WORKER_TASK_ID": "task-x",
        "WORKER_ROLE": "developer",
    })

    assert result.returncode == 0, result.stderr
    assert "should never surface without ORG_ROOT" not in result.stdout
    assert letter.exists()                            # never drained
