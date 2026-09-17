"""Tests for tools/memory_sync.py (task-8d37c0f1).

Every git repo here is built under tmp_path — never the real
Agents-Memory checkout, never ~/.claude/projects/. Two temp repos model the
real setup: a bare "origin" (``PASAKON/Agents-Memory`` on GitHub) and a
non-bare "clone" (the sibling checkout a memory-dir symlink points at).

Run standalone:   python scripts/test_memory_sync.py
Or under pytest:  pytest scripts/test_memory_sync.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import memory_sync  # noqa: E402


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    r = _run(["git", *args], cwd)
    assert r.returncode == 0, f"git {args} failed: {r.stderr}"
    return r


def _init_bare(tmp_path: Path, name: str = "origin.git") -> Path:
    bare = tmp_path / name
    _git(tmp_path, "init", "--bare", "-q", str(bare))
    return bare


def _clone(bare: Path, tmp_path: Path, name: str) -> Path:
    clone = tmp_path / name
    _git(tmp_path, "clone", "-q", str(bare), str(clone))
    _git(clone, "config", "user.email", "test@example.com")
    _git(clone, "config", "user.name", "Test")
    return clone


def _commit_file(repo: Path, filename: str, content: str, msg: str) -> None:
    (repo / filename).write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)


def _symlink_memory_dir(tmp_path: Path, target: Path) -> Path:
    memory_dir = tmp_path / "fake-home" / ".claude" / "projects" / "slug" / "memory"
    memory_dir.parent.mkdir(parents=True, exist_ok=True)
    memory_dir.symlink_to(target)
    return memory_dir


# --------------------------------------------------------------------------
# slug + symlink resolution
# --------------------------------------------------------------------------

def test_claude_project_slug_matches_observed_convention(tmp_path: Path) -> None:
    got = memory_sync._claude_project_slug(Path("/Users/gob/Projects/Agents"))
    assert got == "-Users-gob-Projects-Agents"
    got_wt = memory_sync._claude_project_slug(
        Path("/Users/gob/Projects/Agents/worktrees/mooniex-agents__developer__task-8d37c0f1")
    )
    assert got_wt == (
        "-Users-gob-Projects-Agents-worktrees-mooniex-agents--developer--task-8d37c0f1"
    )


def test_resolve_repo_path_follows_relative_symlink(tmp_path: Path) -> None:
    target = tmp_path / "Agents-Memory"
    target.mkdir()
    memory_dir = tmp_path / "memory"
    memory_dir.symlink_to(Path("Agents-Memory"))  # relative target
    resolved = memory_sync.resolve_repo_path(memory_dir)
    assert resolved == target.resolve()


def test_resolve_repo_path_none_for_plain_dir(tmp_path: Path) -> None:
    plain = tmp_path / "memory"
    plain.mkdir()
    assert memory_sync.resolve_repo_path(plain) is None


# --------------------------------------------------------------------------
# not wired up (no symlink) — no-op exit 0 on both commands
# --------------------------------------------------------------------------

def test_pull_noop_when_not_a_symlink(tmp_path: Path) -> None:
    plain = tmp_path / "memory"
    plain.mkdir()
    assert memory_sync.pull(plain) == 0


def test_push_noop_when_not_a_symlink(tmp_path: Path) -> None:
    plain = tmp_path / "memory"
    plain.mkdir()
    assert memory_sync.push(plain) == 0


def test_pull_noop_when_memory_dir_missing_entirely(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    assert memory_sync.pull(missing) == 0
    assert memory_sync.push(missing) == 0


# --------------------------------------------------------------------------
# pull
# --------------------------------------------------------------------------

def test_pull_fast_forwards_cleanly(tmp_path: Path) -> None:
    bare = _init_bare(tmp_path)
    writer = _clone(bare, tmp_path, "writer")
    _commit_file(writer, "MEMORY.md", "v1\n", "init")
    _git(writer, "push", "-q", "origin", "HEAD")

    reader = _clone(bare, tmp_path, "reader")
    memory_dir = _symlink_memory_dir(tmp_path, reader)

    # writer pushes a second commit the reader doesn't have yet
    _commit_file(writer, "MEMORY.md", "v2\n", "update")
    _git(writer, "push", "-q", "origin", "HEAD")

    assert memory_sync.pull(memory_dir) == 0
    assert (reader / "MEMORY.md").read_text() == "v2\n"


def test_pull_diverged_does_not_fail_and_does_not_block(tmp_path: Path) -> None:
    """A crashed session's unpushed local commit must never fail the pull."""
    bare = _init_bare(tmp_path)
    writer = _clone(bare, tmp_path, "writer")
    _commit_file(writer, "MEMORY.md", "v1\n", "init")
    _git(writer, "push", "-q", "origin", "HEAD")

    stale = _clone(bare, tmp_path, "stale")
    memory_dir = _symlink_memory_dir(tmp_path, stale)

    # stale session made a local commit it never pushed (it "died")
    _commit_file(stale, "local-note.md", "orphaned\n", "local only, never pushed")

    # meanwhile someone else pushed a divergent commit to origin
    _commit_file(writer, "MEMORY.md", "v2-from-elsewhere\n", "elsewhere update")
    _git(writer, "push", "-q", "origin", "HEAD")

    # --ff-only must fail here (diverged histories) — pull() must swallow it
    assert memory_sync.pull(memory_dir) == 0
    # the local unpushed commit is untouched, proving nothing was force-merged
    assert (stale / "local-note.md").read_text() == "orphaned\n"


# --------------------------------------------------------------------------
# push
# --------------------------------------------------------------------------

def test_push_nothing_changed_exits_zero(tmp_path: Path) -> None:
    bare = _init_bare(tmp_path)
    writer = _clone(bare, tmp_path, "writer")
    _commit_file(writer, "MEMORY.md", "v1\n", "init")
    _git(writer, "push", "-q", "origin", "HEAD")

    clean = _clone(bare, tmp_path, "clean")
    memory_dir = _symlink_memory_dir(tmp_path, clean)

    before = _git(bare, "rev-parse", "HEAD").stdout.strip()
    assert memory_sync.push(memory_dir) == 0
    after = _git(bare, "rev-parse", "HEAD").stdout.strip()
    assert before == after, "push with nothing staged must not create a commit"


def test_push_commits_and_pushes_real_change(tmp_path: Path) -> None:
    bare = _init_bare(tmp_path)
    writer = _clone(bare, tmp_path, "writer")
    _commit_file(writer, "MEMORY.md", "v1\n", "init")
    _git(writer, "push", "-q", "origin", "HEAD")

    editor = _clone(bare, tmp_path, "editor")
    memory_dir = _symlink_memory_dir(tmp_path, editor)
    (editor / "MEMORY.md").write_text("v1\nnew line from this session\n")

    assert memory_sync.push(memory_dir) == 0

    # verify it actually landed on "GitHub" (the bare repo), not just locally
    check = _clone(bare, tmp_path, "verify")
    assert "new line from this session" in (check / "MEMORY.md").read_text()


def test_push_fails_loudly_when_remote_unreachable(tmp_path: Path) -> None:
    bare = _init_bare(tmp_path)
    broken = _clone(bare, tmp_path, "broken")
    _commit_file(broken, "MEMORY.md", "v1\n", "init")
    _git(broken, "push", "-q", "origin", "HEAD")

    memory_dir = _symlink_memory_dir(tmp_path, broken)
    (broken / "MEMORY.md").write_text("v2 — will never leave this machine\n")

    # point origin at a path that no longer exists — push must fail
    _git(broken, "remote", "set-url", "origin", str(tmp_path / "gone-missing.git"))

    assert memory_sync.push(memory_dir) == 1
    # the commit was still made locally — only the push leg failed
    log = _git(broken, "log", "--oneline", "-1").stdout
    assert "memory:" in log


# --------------------------------------------------------------------------
# standalone runner (no pytest required)
# --------------------------------------------------------------------------

def main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failures = 0
    for name, fn in tests:
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(Path(td))
                print(f"  [PASS] {name}")
            except Exception:
                failures += 1
                print(f"  [FAIL] {name}")
                traceback.print_exc()
    print(f"\n{len(tests)} tests, "
          f"{'ALL PASS' if failures == 0 else str(failures) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
