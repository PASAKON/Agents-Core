"""Tests for tools/memory_sync.py (task-8d37c0f1, task-0610144c).

Every git repo here is built under tmp_path — never the real
Agents-Memory checkout, never ~/.claude/projects/. Throwaway repos model the
real setup: a bare "origin" (``PASAKON/Agents-Memory`` on GitHub) and two
clones ("writer" and "local"/"reader").

Run standalone:   python tests/test_memory_sync.py
Or under pytest:  pytest tests/test_memory_sync.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import traceback
from contextlib import redirect_stdout
from io import StringIO
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


def _diverged_repos(tmp_path: Path) -> tuple[Path, Path, Path]:
    bare = _init_bare(tmp_path)
    writer = _clone(bare, tmp_path, "writer")
    _commit_file(writer, "MEMORY.md", "base line\n", "init")
    _git(writer, "push", "-q", "origin", "HEAD")
    local = _clone(bare, tmp_path, "local")
    _commit_file(
        writer,
        "MEMORY.md",
        "base line\nprivate remote lesson\n",
        "remote update",
    )
    _git(writer, "push", "-q", "origin", "HEAD")
    return bare, local, _symlink_memory_dir(tmp_path, local)


# --------------------------------------------------------------------------
# slug + symlink resolution
# --------------------------------------------------------------------------

def test_claude_project_slug_matches_observed_convention(tmp_path: Path) -> None:
    got = memory_sync._claude_project_slug(Path("/Users/gob/MoonieXHQ/Agents/Core"))
    assert got == "-Users-gob-MoonieXHQ-Agents-Core"
    got_wt = memory_sync._claude_project_slug(
        Path("/Users/gob/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-8d37c0f1")
    )
    assert got_wt == (
        "-Users-gob-MoonieXHQ-Agents-Core-worktrees-mooniex-agents--developer--task-8d37c0f1"
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
# pull: fast-forward & divergence reconciliation
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

    # --ff-only fails, then a clean merge preserves both sessions' work.
    assert memory_sync.pull(memory_dir) == 0
    assert (stale / "local-note.md").read_text() == "orphaned\n"
    assert (stale / "MEMORY.md").read_text() == "v2-from-elsewhere\n"
    assert len(_git(stale, "rev-list", "--parents", "-1", "HEAD").stdout.split()) == 3
    assert not _git(stale, "status", "--porcelain").stdout.strip()


def test_pull_diverged_memory_md_conflict_merges_by_union(tmp_path: Path) -> None:
    """Diverged MEMORY.md conflict -> merged by line union via .gitattributes."""
    bare, local, memory_dir = _diverged_repos(tmp_path)
    _commit_file(
        local,
        "MEMORY.md",
        "base line\nprivate local lesson\n",
        "local update",
    )

    output = StringIO()
    with redirect_stdout(output):
        assert memory_sync.pull(memory_dir) == 0

    out = output.getvalue()
    assert "private local lesson" not in out
    assert "private remote lesson" not in out
    assert "base line" not in out

    merged_memory = (local / "MEMORY.md").read_text()
    assert "base line\n" in merged_memory
    assert "private local lesson\n" in merged_memory
    assert "private remote lesson\n" in merged_memory
    assert "<<<<<<<" not in merged_memory

    assert (local / ".gitattributes").exists()
    assert "MEMORY.md merge=union" in (local / ".gitattributes").read_text()
    assert len(_git(local, "rev-list", "--parents", "-1", "HEAD").stdout.split()) == 3
    assert not (local / ".git" / "MERGE_HEAD").exists()
    assert not _git(local, "status", "--porcelain").stdout.strip()


def test_pull_topic_file_conflict_keeps_both_versions_and_prints_only_names(
    tmp_path: Path,
) -> None:
    """Topic-file conflict (modify/modify and add/add) -> keeps ours and writes
    theirs as <name>.theirs-<shortsha>.md; output prints only file names."""
    bare = _init_bare(tmp_path)
    writer = _clone(bare, tmp_path, "writer")
    _commit_file(writer, "MEMORY.md", "- [topic](reference_topic.md)\n", "init")
    _commit_file(writer, "reference_topic.md", "initial topic\n", "init topic")
    _git(writer, "push", "-q", "origin", "HEAD")

    local = _clone(bare, tmp_path, "local")
    memory_dir = _symlink_memory_dir(tmp_path, local)

    # Remote modifies reference_topic.md, adds reference_new.md, and appends MEMORY.md
    (writer / "MEMORY.md").write_text(
        "- [topic](reference_topic.md)\n- [remote](reference_new.md)\n"
    )
    (writer / "reference_topic.md").write_text("SECRET_REMOTE_TOPIC_BODY\n")
    (writer / "reference_new.md").write_text("SECRET_REMOTE_ADD_ADD_BODY\n")
    _git(writer, "add", "-A")
    _git(writer, "commit", "-q", "-m", "remote topic edits")
    _git(writer, "push", "-q", "origin", "HEAD")
    remote_shortsha = _git(writer, "rev-parse", "--short", "HEAD").stdout.strip()

    # Local modifies reference_topic.md, adds reference_new.md, and appends MEMORY.md
    (local / "MEMORY.md").write_text(
        "- [topic](reference_topic.md)\n- [local](reference_new.md)\n"
    )
    (local / "reference_topic.md").write_text("SECRET_LOCAL_TOPIC_BODY\n")
    (local / "reference_new.md").write_text("SECRET_LOCAL_ADD_ADD_BODY\n")
    _git(local, "add", "-A")
    _git(local, "commit", "-q", "-m", "local topic edits")

    output = StringIO()
    with redirect_stdout(output):
        assert memory_sync.pull(memory_dir) == 0

    out = output.getvalue()
    # File names are printed, never file contents
    assert "reference_topic.md" in out
    assert f"reference_topic.theirs-{remote_shortsha}.md" in out
    assert "reference_new.md" in out
    assert f"reference_new.theirs-{remote_shortsha}.md" in out
    for secret in (
        "SECRET_REMOTE_TOPIC_BODY",
        "SECRET_LOCAL_TOPIC_BODY",
        "SECRET_REMOTE_ADD_ADD_BODY",
        "SECRET_LOCAL_ADD_ADD_BODY",
    ):
        assert secret not in out

    # Both versions of both topic files are preserved on disk and committed
    assert (local / "reference_topic.md").read_text() == "SECRET_LOCAL_TOPIC_BODY\n"
    assert (
        local / f"reference_topic.theirs-{remote_shortsha}.md"
    ).read_text() == "SECRET_REMOTE_TOPIC_BODY\n"
    assert (local / "reference_new.md").read_text() == "SECRET_LOCAL_ADD_ADD_BODY\n"
    assert (
        local / f"reference_new.theirs-{remote_shortsha}.md"
    ).read_text() == "SECRET_REMOTE_ADD_ADD_BODY\n"

    # MEMORY.md merged by union without conflict markers
    merged_index = (local / "MEMORY.md").read_text()
    assert "- [remote](reference_new.md)\n" in merged_index
    assert "- [local](reference_new.md)\n" in merged_index
    assert "<<<<<<<" not in merged_index

    assert len(_git(local, "rev-list", "--parents", "-1", "HEAD").stdout.split()) == 3
    assert not (local / ".git" / "MERGE_HEAD").exists()
    assert not _git(local, "status", "--porcelain").stdout.strip()


def test_pull_dirty_tree_still_merges_and_keeps_local_changes(tmp_path: Path) -> None:
    """Dirty working tree (uncommitted edits to tracked + untracked files, plus
    uncommitted edits to a file remote also modified) -> pull commits local
    edits first and merges remote cleanly without printing file contents."""
    bare, local, memory_dir = _diverged_repos(tmp_path)
    _commit_file(local, "note.md", "local committed note\n", "local update")
    # Uncommitted edits to tracked note.md, tracked MEMORY.md, and untracked file
    (local / "note.md").write_text("SECRET_UNCOMMITTED_NOTE\n")
    (local / "MEMORY.md").write_text("base line\nSECRET_UNCOMMITTED_INDEX_LINE\n")
    (local / "reference_untracked.md").write_text("SECRET_UNTRACKED_TOPIC\n")

    output = StringIO()
    with redirect_stdout(output):
        assert memory_sync.pull(memory_dir) == 0

    out = output.getvalue()
    for secret in (
        "SECRET_UNCOMMITTED_NOTE",
        "SECRET_UNCOMMITTED_INDEX_LINE",
        "SECRET_UNTRACKED_TOPIC",
        "private remote lesson",
    ):
        assert secret not in out

    assert (local / "note.md").read_text() == "SECRET_UNCOMMITTED_NOTE\n"
    assert (local / "reference_untracked.md").read_text() == "SECRET_UNTRACKED_TOPIC\n"
    merged_memory = (local / "MEMORY.md").read_text()
    assert "SECRET_UNCOMMITTED_INDEX_LINE\n" in merged_memory
    assert "private remote lesson\n" in merged_memory
    assert len(_git(local, "rev-list", "--parents", "-1", "HEAD").stdout.split()) == 3
    assert not _git(local, "status", "--porcelain").stdout.strip()


def test_pull_multiple_branches_in_config_and_remote_merges_cleanly(
    tmp_path: Path,
) -> None:
    """Multiple branch.<name>.merge entries or extra remote branches must never
    cause 'fatal: Cannot fast-forward to multiple branches'."""
    bare = _init_bare(tmp_path)
    writer = _clone(bare, tmp_path, "writer")
    _commit_file(writer, "MEMORY.md", "v1\n", "init")
    _git(writer, "push", "-q", "origin", "HEAD")

    branch = _git(writer, "symbolic-ref", "--short", "HEAD").stdout.strip()
    # Push a second branch to origin
    _git(writer, "checkout", "-q", "-b", "side-branch")
    _commit_file(writer, "side.md", "side\n", "side commit")
    _git(writer, "push", "-q", "origin", "side-branch")
    _git(writer, "checkout", "-q", branch)

    local = _clone(bare, tmp_path, "local")
    memory_dir = _symlink_memory_dir(tmp_path, local)

    # Corrupt local config with a second merge branch (causes git pull --ff-only
    # to fail with "fatal: Cannot fast-forward to multiple branches")
    _git(local, "config", "--add", f"branch.{branch}.merge", "refs/heads/side-branch")

    # Advance main on origin
    _commit_file(writer, "MEMORY.md", "v1\nv2 from main\n", "advance main")
    _git(writer, "push", "-q", "origin", branch)

    output = StringIO()
    with redirect_stdout(output):
        assert memory_sync.pull(memory_dir) == 0

    assert "multiple branches" not in output.getvalue().lower()
    assert "v2 from main" not in output.getvalue()
    assert (local / "MEMORY.md").read_text() == "v1\nv2 from main\n"
    merge_refs = _git(
        local, "config", "--get-all", f"branch.{branch}.merge"
    ).stdout.splitlines()
    assert len(merge_refs) == 1


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


def test_push_diverged_merges_and_lands(tmp_path: Path) -> None:
    bare, local, memory_dir = _diverged_repos(tmp_path)
    (local / "note.md").write_text("local note\n")
    assert memory_sync.push(memory_dir) == 0
    assert _git(bare, "rev-parse", "HEAD").stdout == _git(local, "rev-parse", "HEAD").stdout
    assert _git(bare, "show", "HEAD:note.md").stdout == "local note\n"
    assert "private remote lesson\n" in _git(bare, "show", "HEAD:MEMORY.md").stdout
    assert len(_git(local, "rev-list", "--parents", "-1", "HEAD").stdout.split()) == 3
    assert not _git(local, "status", "--porcelain").stdout.strip()


def test_push_conflict_reconciles_and_pushes_without_leaking_content(
    tmp_path: Path,
) -> None:
    """When push hits non-fast-forward with both MEMORY.md and topic-file
    conflicts, it merges MEMORY.md by union, keeps both topic versions, and
    pushes the reconciled commit to origin without printing file contents."""
    bare, local, memory_dir = _diverged_repos(tmp_path)
    writer = tmp_path / "writer"
    _commit_file(writer, "reference_shared.md", "REMOTE_TOPIC_SECRET\n", "remote topic")
    _git(writer, "push", "-q", "origin", "HEAD")
    remote_shortsha = _git(writer, "rev-parse", "--short", "HEAD").stdout.strip()

    (local / "MEMORY.md").write_text("base line\nprivate local lesson\n")
    (local / "reference_shared.md").write_text("LOCAL_TOPIC_SECRET\n")

    output = StringIO()
    with redirect_stdout(output):
        assert memory_sync.push(memory_dir) == 0

    out = output.getvalue()
    assert "reference_shared.md" in out
    assert f"reference_shared.theirs-{remote_shortsha}.md" in out
    assert "private local lesson" not in out
    assert "private remote lesson" not in out
    assert "REMOTE_TOPIC_SECRET" not in out
    assert "LOCAL_TOPIC_SECRET" not in out

    assert _git(bare, "rev-parse", "HEAD").stdout == _git(local, "rev-parse", "HEAD").stdout
    remote_memory = _git(bare, "show", "HEAD:MEMORY.md").stdout
    assert "private local lesson\n" in remote_memory
    assert "private remote lesson\n" in remote_memory
    assert _git(bare, "show", "HEAD:reference_shared.md").stdout == "LOCAL_TOPIC_SECRET\n"
    assert (
        _git(bare, "show", f"HEAD:reference_shared.theirs-{remote_shortsha}.md").stdout
        == "REMOTE_TOPIC_SECRET\n"
    )
    assert not (local / ".git" / "MERGE_HEAD").exists()
    assert not _git(local, "status", "--porcelain").stdout.strip()


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
