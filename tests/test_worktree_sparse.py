"""Sparse worktrees (ADR 0030, task-bfa778ab) — tools/worktree.py create_worktree.

iter1 rewrite: a directory-level exclude ("docs/reports/**") broke `git add
-A` for any NEW file under that directory (git refuses anything outside the
sparse-checkout definition, exit 1) — 304 browser_operator tasks/30d write
new files under docs/reports, so nearly every one of those commits would
have failed. Fixed by excluding only EXISTING tracked files above
`min_bytes` with a `media_guard.extensions` extension, by EXACT PATH —
every directory (including docs/reports itself) stays inside the sparse
definition, so a brand-new file there is always addable.

Builds a throwaway git repo in tmp_path with: a small tracked src/a.py, a
large tracked docs/reports/big_video.mp4, a small tracked
docs/reports/small_icon.png, and three large tracked files exercising the
sparse-checkout pattern escaping this needs — a leading `!`, a `[` inside
the name, and a Thai filename with a space.

Run via:  pytest tests/test_worktree_sparse.py
(collected by the default `pytest` run — pytest.ini `testpaths` now
includes `tests` alongside `scripts lib`.)

Note (task-2b1b03e7, ADR 0030 §8 scope map): `create_worktree`'s `sparse`
param stays a plain bool here — the scope→bool resolution
(`_scope_applies("sparse_worktree", owner_cto)`, "all" | list | missing)
lives entirely in tools/delegate.py and is covered there
(tests/test_delegate_disk_floor.py's `sparse` assertions). Nothing in this
file changed behaviourally; only the "storage pilot" wording below was
updated to match the current scope-map terminology.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.worktree as worktree_mod  # noqa: E402

LARGE = b"\0" * (2 * 1024 * 1024)   # 2 MiB, well above the 256 KiB min_bytes
SMALL = b"\x89PNG\r\n\x1a\n" + b"\0" * 64  # a few dozen bytes, below min_bytes

BANG_FILE = "!weird.mp4"                    # leading '!' — line-start negation char
BRACKET_FILE = "docs/reports/clip[1].mp4"   # '[' — glob metacharacter
THAI_FILE = "docs/reports/แผนที่ ใหม่.mp4"      # Thai + internal space


def _git(cmd: list[str], cwd: Path) -> str:
    r = subprocess.run(["git", *cmd], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"git {cmd} failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout.strip()


def _write(repo: Path, rel: str, data: bytes) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _init_origin_repo(tmp_path: Path) -> Path:
    """A bare-ish 'origin' repo, matching create_worktree's `origin/<base>`
    start-point path."""
    repo = tmp_path / "origin"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)

    _write(repo, "src/a.py", b"print('hi')\n")
    _write(repo, "docs/reports/big_video.mp4", LARGE)
    _write(repo, "docs/reports/small_icon.png", SMALL)
    _write(repo, BANG_FILE, LARGE)
    _write(repo, BRACKET_FILE, LARGE)
    _write(repo, THAI_FILE, LARGE)

    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


def _make_clone_with_origin(tmp_path: Path, origin: Path) -> Path:
    """The repo `create_worktree` treats as the project's own checkout —
    cloned from `origin` so `origin/<base>` resolves (mirrors production:
    `git fetch origin <base>` + `git rev-parse --verify origin/<base>`)."""
    repo = tmp_path / "repo"
    _git(["clone", str(origin), str(repo)], tmp_path)
    return repo


@pytest.fixture()
def policy_file(tmp_path):
    """A minimal storage-policy.yaml, isolated from the real repo's config
    so this test never depends on (or breaks from) future policy edits."""
    p = tmp_path / "storage-policy.yaml"
    p.write_text(
        "gauge:\n"
        "  orange: 5\n"
        "media_guard:\n"
        "  extensions: [mp4, png]\n"
        "sparse_worktree:\n"
        "  min_bytes: 262144\n"
        "  full_checkout_roles: [\"video_editor\"]\n"
    )
    return p


@pytest.fixture()
def wired(tmp_path, policy_file, monkeypatch):
    """Point worktree.py at the throwaway repo + policy + a scratch
    WORKTREE_DIR (never the real ~/Projects/Agents/worktrees)."""
    origin = _init_origin_repo(tmp_path)
    repo = _make_clone_with_origin(tmp_path, origin)
    wt_dir = tmp_path / "worktrees"

    monkeypatch.setattr(worktree_mod, "STORAGE_POLICY", policy_file)
    monkeypatch.setattr(worktree_mod, "WORKTREE_DIR", wt_dir)
    monkeypatch.setattr(
        worktree_mod, "get_project",
        lambda key: {"path": str(repo), "default_branch": "main"},
    )
    # create_worktree resolves the checkout per host (task-6f6e5179), so the
    # stub must answer for whichever host runs the suite.
    monkeypatch.setattr(worktree_mod, "project_path_for_host", lambda key, host: str(repo))
    return {"origin": origin, "repo": repo, "wt_dir": wt_dir}


# ---------------------------------------------------------------------------
# Sparse role excludes only the large tracked media, by exact path; small
# files and text stay on disk. Covers the leading-'!', '[', and Thai+space
# escaping cases.
# ---------------------------------------------------------------------------

def test_sparse_role_excludes_only_large_tracked_media(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t1", sparse=True)
    wt = Path(info["worktree"])

    assert (wt / "src" / "a.py").exists()
    assert (wt / "docs" / "reports" / "small_icon.png").exists(), \
        "a small tracked png must stay on disk"

    assert not (wt / "docs" / "reports" / "big_video.mp4").exists(), \
        "a large tracked mp4 must be absent from disk"
    assert not (wt / BANG_FILE).exists(), "leading '!' path must still be excluded"
    assert not (wt / BRACKET_FILE).exists(), "'[' in path must still be excluded"
    assert not (wt / THAI_FILE).exists(), "Thai filename with a space must still be excluded"

    # the directories themselves must NOT be excluded (that was the bug) —
    # only the exact large files inside them.
    assert (wt / "docs" / "reports").is_dir()


def test_full_checkout_role_includes_everything(wired):
    info = worktree_mod.create_worktree("testproj", "video_editor", "t2", sparse=True)
    wt = Path(info["worktree"])

    assert (wt / "src" / "a.py").exists()
    assert (wt / "docs" / "reports" / "big_video.mp4").exists()
    assert (wt / BANG_FILE).exists()
    assert (wt / BRACKET_FILE).exists()
    assert (wt / THAI_FILE).exists()


# ---------------------------------------------------------------------------
# The actual regression: a NEW file under a directory that also holds
# excluded large media must still be addable and committable.
# ---------------------------------------------------------------------------

def test_new_files_under_docs_reports_are_addable_and_committable(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t3", sparse=True)
    wt = Path(info["worktree"])

    (wt / "docs" / "reports" / "NEW_REPORT.md").write_text("a new report\n")
    (wt / "docs" / "reports" / "new_screenshot.png").write_bytes(SMALL)

    r = subprocess.run(["git", "add", "-A"], cwd=str(wt), capture_output=True, text=True)
    assert r.returncode == 0, f"git add -A failed:\n{r.stdout}\n{r.stderr}"

    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(wt),
                            capture_output=True, text=True).stdout
    assert "NEW_REPORT.md" in status
    assert "new_screenshot.png" in status

    result = worktree_mod.commit_worktree(str(wt), "test: add new report + screenshot")
    assert result["committed"] is True


# ---------------------------------------------------------------------------
# Main checkout's own sparse-checkout state is never touched.
# ---------------------------------------------------------------------------

def test_main_checkout_stays_non_sparse(wired):
    repo = wired["repo"]
    before = subprocess.run(
        ["git", "sparse-checkout", "list"], cwd=str(repo),
        capture_output=True, text=True,
    )

    worktree_mod.create_worktree("testproj", "developer", "t4", sparse=True)

    after = subprocess.run(
        ["git", "sparse-checkout", "list"], cwd=str(repo),
        capture_output=True, text=True,
    )
    assert after.returncode == before.returncode
    assert after.stdout == before.stdout
    # core.sparseCheckout must stay unset in the main checkout's own scope
    # (i.e. never fall back to the shared/common config).
    cfg = subprocess.run(
        ["git", "config", "--get", "core.sparseCheckout"], cwd=str(repo),
        capture_output=True, text=True,
    )
    assert cfg.returncode != 0, f"core.sparseCheckout leaked into main checkout: {cfg.stdout!r}"
    assert (repo / "docs" / "reports" / "big_video.mp4").exists(), \
        "main checkout must keep its own full working tree"


# ---------------------------------------------------------------------------
# commit_worktree still commits a changed tracked file from a sparse worktree.
# ---------------------------------------------------------------------------

def test_commit_worktree_from_sparse_worktree(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t5", sparse=True)
    wt = Path(info["worktree"])

    (wt / "src" / "a.py").write_text("print('changed')\n")
    result = worktree_mod.commit_worktree(str(wt), "test: sparse commit")

    assert result["committed"] is True
    assert "sha" in result


# ---------------------------------------------------------------------------
# Merging a sparse branch into a full (non-sparse) checkout keeps the large
# excluded media intact — files outside the sparse set are not deleted.
# ---------------------------------------------------------------------------

def test_merge_of_sparse_branch_keeps_large_media_intact(wired):
    repo = wired["repo"]

    info = worktree_mod.create_worktree("testproj", "developer", "t6", sparse=True)
    wt = Path(info["worktree"])
    branch = info["branch"]

    (wt / "NEW_FROM_SPARSE.md").write_text("added from a sparse worktree\n")
    commit = worktree_mod.commit_worktree(str(wt), "test: add file from sparse worktree")
    assert commit["committed"] is True

    # merge_task merges in the MAIN repo checkout (tools/git_ops.py:199,266,321
    # — repo = Path(proj["path"]); `git checkout <base>` and `git merge` both
    # run with cwd=repo), which is always a full, non-sparse checkout. `repo`
    # here stands in for that — it was never sparsified (see test above).
    _git(["checkout", "-b", "scratch"], repo)
    _git(["merge", "--no-ff", branch, "-m", "merge sparse branch"], repo)

    assert (repo / "docs" / "reports" / "big_video.mp4").exists(), \
        "large tracked media must survive a merge of a branch built in a sparse worktree"
    assert (repo / BANG_FILE).exists()
    assert (repo / BRACKET_FILE).exists()
    assert (repo / THAI_FILE).exists()
    assert (repo / "NEW_FROM_SPARSE.md").exists()


def test_default_is_full_checkout_when_sparse_not_requested(wired):
    """sparse defaults to False: a task outside the `sparse_worktree` scope
    (another session's work, CEO 2026-09-23) gets today's full checkout."""
    info = worktree_mod.create_worktree("testproj", "developer", "t9")
    wt = Path(info["worktree"])
    assert (wt / "docs" / "reports" / "big_video.mp4").exists()
    assert (wt / THAI_FILE).exists()


# ---------------------------------------------------------------------------
# One sparse step for every spawn path (task-49b623ed): restore_worktree and
# the shell launcher use the same apply_sparse as create_worktree.
# 300 KB mp4 = just over the 256 KiB min_bytes, the size the brief names.
# ---------------------------------------------------------------------------

CLIP = "docs/clip.mp4"
SKILL_TEMPLATE = ".claude/skills/x/template.mp4"
CLIP_BYTES = b"\0" * 300_000


@pytest.fixture()
def wired300k(tmp_path, monkeypatch):
    origin = tmp_path / "origin300"
    origin.mkdir()
    _git(["init", "-b", "main"], origin)
    _git(["config", "user.email", "t@example.com"], origin)
    _git(["config", "user.name", "Test"], origin)
    _write(origin, "src/a.py", b"print('hi')\n")
    _write(origin, CLIP, CLIP_BYTES)
    _write(origin, "docs/small.mp4", b"\0" * 1024)
    _write(origin, SKILL_TEMPLATE, CLIP_BYTES)
    _git(["add", "-A"], origin)
    _git(["commit", "-m", "init"], origin)
    repo = tmp_path / "repo300"
    _git(["clone", str(origin), str(repo)], tmp_path)
    # a task branch that already exists, as restore_worktree finds it
    _git(["branch", "agent/developer-t10", "origin/main"], repo)
    _git(["branch", "agent/video_editor-t11", "origin/main"], repo)

    policy = tmp_path / "storage-policy300.yaml"
    policy.write_text(
        "media_guard:\n  extensions: [mp4]\n"
        "sparse_worktree:\n  min_bytes: 262144\n  full_checkout_roles: [\"video_editor\"]\n"
        "  keep_paths: [\".claude/skills/*\"]\n")
    monkeypatch.setattr(worktree_mod, "STORAGE_POLICY", policy)
    monkeypatch.setattr(worktree_mod, "WORKTREE_DIR", tmp_path / "worktrees300")
    monkeypatch.setattr(worktree_mod, "get_project",
                        lambda key: {"path": str(repo), "default_branch": "main"})
    monkeypatch.setattr(worktree_mod, "project_path_for_host", lambda key, host: str(repo))
    return {"repo": repo}


def test_restore_worktree_sparse_excludes_300kb_mp4(wired300k):
    info = worktree_mod.restore_worktree("p", "developer", "t10", sparse=True)
    wt = Path(info["worktree"])

    assert not (wt / CLIP).exists(), "a 300 KB tracked mp4 must be absent from a restored sparse worktree"
    assert (wt / "docs/small.mp4").exists()
    assert (wt / "src/a.py").exists()
    assert (wt / SKILL_TEMPLATE).exists(), "keep_paths (.claude/skills/*) stay on disk"
    assert _git(["status", "--porcelain"], wt) == "", "an excluded file must not show up as deleted"

    # exact-path negations: a new file beside the excluded one still adds cleanly
    (wt / "docs" / "NEW.md").write_text("new\n")
    assert subprocess.run(["git", "add", "-A"], cwd=str(wt), capture_output=True).returncode == 0
    assert worktree_mod.commit_worktree(str(wt), "test: new file")["committed"] is True


def test_restore_worktree_default_stays_full(wired300k):
    wt = Path(worktree_mod.restore_worktree("p", "developer", "t10")["worktree"])
    assert (wt / CLIP).exists()


def test_restore_worktree_sparse_video_editor_stays_full(wired300k):
    wt = Path(worktree_mod.restore_worktree("p", "video_editor", "t11", sparse=True)["worktree"])
    assert (wt / CLIP).exists()
    assert (wt / SKILL_TEMPLATE).exists()


def test_apply_sparse_is_a_noop_when_nothing_is_excluded(wired300k):
    """Full-checkout role: returns [] and writes no sparse config at all."""
    repo = wired300k["repo"]
    wt = repo.parent / "wt-noop"
    _git(["worktree", "add", "--no-checkout", "-b", "noop", str(wt), "origin/main"], repo)

    assert worktree_mod.apply_sparse(repo, wt, "origin/main", "video_editor") == []

    cfg = subprocess.run(["git", "config", "--get", "extensions.worktreeConfig"],
                         cwd=str(repo), capture_output=True, text=True)
    assert cfg.returncode != 0, "a no-op must not touch the repo config"
    _git(["checkout", "noop"], wt)
    assert (wt / CLIP).exists()


def test_failing_sparse_step_falls_back_to_full_checkout(wired300k, monkeypatch, capsys):
    """The sparse step dies after `sparse-checkout init` (which leaves the
    root-files-only default list). The spawn must still succeed with the whole
    tree on disk -- src/a.py is below the root, so it proves sparse was undone."""
    real_run = worktree_mod._run

    def flaky(cmd, cwd=None):
        if cmd[1:3] == ["sparse-checkout", "set"]:
            raise worktree_mod.GitError("simulated sparse-checkout set failure")
        return real_run(cmd, cwd=cwd)

    monkeypatch.setattr(worktree_mod, "_run", flaky)
    wt = Path(worktree_mod.create_worktree("p", "developer", "t12", sparse=True)["worktree"])

    assert (wt / CLIP).exists() and (wt / "src/a.py").exists()
    assert "sparse step failed" in capsys.readouterr().err
    assert _git(["status", "--porcelain"], wt) == ""


def test_failing_exclusion_scan_falls_back_in_restore(wired300k, monkeypatch, capsys):
    def boom(*a, **k):
        raise worktree_mod.GitError("simulated ls-tree failure")

    monkeypatch.setattr(worktree_mod, "_large_tracked_media", boom)
    wt = Path(worktree_mod.restore_worktree("p", "developer", "t10", sparse=True)["worktree"])

    assert (wt / CLIP).exists()
    assert "sparse step failed" in capsys.readouterr().err


def test_apply_sparse_cli_prints_marker_and_fails_cleanly(wired300k, capsys):
    repo = wired300k["repo"]
    wt = repo.parent / "wt-cli"
    _git(["worktree", "add", "--no-checkout", "-b", "cli", str(wt), "origin/main"], repo)
    args = ["apply-sparse", "--repo", str(repo), "--wt", str(wt),
            "--start-point", "origin/main", "--role", "developer"]

    assert worktree_mod._main(args) == 0
    assert "SPARSE_APPLIED excluded=1" in capsys.readouterr().out
    _git(["checkout", "cli"], wt)
    assert not (wt / CLIP).exists() and (wt / "src/a.py").exists()

    bad = args[:]
    bad[bad.index("--start-point") + 1] = "no-such-ref"
    assert worktree_mod._main(bad) == 1
    assert "apply-sparse failed" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# scripts/spawn-worker-remote.sh -- the router path (Codex / AGY / Claude
# remote spawn) used to run a bare `git worktree add` (~985 MB per Agents-Core
# worktree). It now adds with --no-checkout, runs `python -m tools.worktree
# apply-sparse`, then checks out; a failing helper falls back to a full
# checkout with a stderr warning, never a failed spawn. These tests run the
# real script (not --dry-run) in a fake agents root: scratch repos under
# tmp_path only, tmux and claude replaced by stubs on PATH.
# ---------------------------------------------------------------------------

REMOTE_SCRIPT = ROOT / "scripts" / "spawn-worker-remote.sh"
SH = "/bin/bash"


def _sgit(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"git {args} failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout.strip()


def _swrite(base: Path, rel: str, data: bytes | str) -> None:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data if isinstance(data, bytes) else data.encode())


@pytest.fixture()
def box(tmp_path):
    """A spoke in miniature: a fake agents root holding the script + the
    helper it calls, a project clone with origin/main, stub tmux and claude."""
    root = tmp_path / "agents_root"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "spawn-worker-remote.sh").write_text(REMOTE_SCRIPT.read_text())
    (root / "roles").mkdir()
    for doc in ("_worker_remote.md", "_worker_shared.md", "developer.md", "video_editor.md"):
        (root / "roles" / doc).write_text(f"# {doc}\n")
    # the helper, as a real file so its ROOT (and so config/storage-policy.yaml)
    # is the fake root; lib/ is the repo's own (lib.config needs lib.session_names)
    (root / "tools").mkdir()
    (root / "tools" / "__init__.py").write_text("")
    (root / "tools" / "worktree.py").write_text((ROOT / "tools" / "worktree.py").read_text())
    (root / "lib").symlink_to(ROOT / "lib")
    (root / "config").mkdir()
    (root / "config" / "storage-policy.yaml").write_text(
        "media_guard:\n  extensions: [mp4]\n"
        "sparse_worktree:\n  min_bytes: 262144\n  full_checkout_roles: [\"video_editor\"]\n"
        "  keep_paths: [\".claude/skills/*\"]\n")
    # python the script finds first: the venv slot of the fake root
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "python").symlink_to(sys.executable)

    origin = tmp_path / "origin"
    origin.mkdir()
    _sgit(origin, "init", "-q", "-b", "main")
    _sgit(origin, "config", "user.email", "t@example.com")
    _sgit(origin, "config", "user.name", "Test")
    _swrite(origin, "src/a.py", "print('hi')\n")
    _swrite(origin, CLIP, CLIP_BYTES)
    _swrite(origin, "docs/small.mp4", b"\0" * 1024)
    _swrite(origin, SKILL_TEMPLATE, CLIP_BYTES)
    _sgit(origin, "add", "-A")
    _sgit(origin, "commit", "-qm", "init")
    repo = tmp_path / "repo"
    _sgit(tmp_path, "clone", "-q", str(origin), str(repo))

    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "tmux").write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        "  list-panes) echo 4242 ;;\n"
        "esac\n"
        "exit 0\n")
    (stubs / "claude").write_text("#!/bin/sh\nexit 0\n")
    for stub in (stubs / "tmux", stubs / "claude"):
        stub.chmod(0o755)

    env = dict(os.environ)
    env.update(PATH=f"{stubs}:{env['PATH']}", HOME=str(tmp_path / "home"))
    return {"root": root, "repo": repo, "wts": tmp_path / "wts", "env": env}


def _spawn(box, *, task="task-sp01", role="developer", extra=()):
    branch = f"agent/{role}-{task}"
    args = [
        SH, str(box["root"] / "scripts" / "spawn-worker-remote.sh"),
        "--task", task, "--project", "scratch", "--role", role, "--branch", branch,
        "--base", "main", "--repo-url", "unused", "--repo-path", str(box["repo"]),
        "--worktree-root", str(box["wts"]), "--claude-args", "--model m",
        "--model", "m", "--effort", "high", "--session-name", "s", *extra,
    ]
    r = subprocess.run(args, input="task text\n", capture_output=True, text=True,
                       env=box["env"], timeout=120)
    return r, box["wts"] / f"scratch__{role}__{task}"


def _assert_spawned(r):
    assert r.returncode == 0, f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    assert r.stdout.strip().splitlines()[-1].startswith("SPAWNED pid=4242"), r.stdout


def test_spawn_is_sparse_for_a_developer(box):
    r, wt = _spawn(box)
    _assert_spawned(r)

    assert "SPARSE_APPLIED excluded=1" in r.stdout
    assert not (wt / CLIP).exists(), "a 300 KB tracked mp4 must stay off disk"
    assert (wt / "docs/small.mp4").exists()
    assert (wt / "src/a.py").exists()
    assert (wt / SKILL_TEMPLATE).exists(), "keep_paths (.claude/skills/*) stay"
    assert _sgit(wt, "status", "--porcelain") == "", "excluded file must not read as deleted"

    # exact-path negations: a new file beside the excluded one still adds
    (wt / "docs" / "NEW.md").write_text("new\n")
    _sgit(wt, "add", "-A")
    assert "NEW.md" in _sgit(wt, "status", "--porcelain")
    # the repo's own checkout is untouched
    assert (box["repo"] / CLIP).exists()


def test_spawn_video_editor_stays_full(box):
    r, wt = _spawn(box, role="video_editor", task="task-sp02")
    _assert_spawned(r)
    assert "SPARSE_APPLIED excluded=0" in r.stdout
    assert (wt / CLIP).exists() and (wt / SKILL_TEMPLATE).exists()


def test_spawn_no_sparse_flag_keeps_full_checkout(box):
    r, wt = _spawn(box, task="task-sp03", extra=("--no-sparse",))
    _assert_spawned(r)
    assert "SPARSE_APPLIED" not in r.stdout
    assert (wt / CLIP).exists()


def test_spawn_falls_back_to_full_checkout_when_helper_is_missing(box):
    (box["root"] / "tools" / "worktree.py").unlink()
    r, wt = _spawn(box, task="task-sp04")
    _assert_spawned(r)
    assert "WARNING sparse step failed" in r.stderr
    assert (wt / CLIP).exists() and (wt / "src/a.py").exists()


def test_spawn_falls_back_when_helper_dies_after_sparse_init(box):
    """A helper killed part-way leaves `sparse-checkout init`'s root-files-only
    list behind; the launcher must switch sparse off before it checks out."""
    (box["root"] / "tools" / "worktree.py").write_text(
        "import subprocess, sys\n"
        "wt = sys.argv[sys.argv.index('--wt') + 1]\n"
        "subprocess.run(['git', 'config', 'extensions.worktreeConfig', 'true'], cwd=wt)\n"
        "subprocess.run(['git', 'sparse-checkout', 'init', '--no-cone'], cwd=wt)\n"
        "sys.exit(1)\n")
    r, wt = _spawn(box, task="task-sp05")
    _assert_spawned(r)
    assert "WARNING sparse step failed" in r.stderr
    assert (wt / CLIP).exists()
    assert (wt / "src/a.py").exists(), "sparse list must be undone, not left at root-files-only"
    assert _sgit(wt, "status", "--porcelain").count("D ") == 0


def test_spawn_reuses_a_prior_worktree_and_is_sparse_again(box):
    r, wt = _spawn(box, task="task-sp07")
    _assert_spawned(r)
    r2, wt2 = _spawn(box, task="task-sp07")
    _assert_spawned(r2)
    assert wt2 == wt and not (wt / CLIP).exists() and (wt / "src/a.py").exists()


def _dry_run(box, *extra):
    r = subprocess.run(
        [SH, str(REMOTE_SCRIPT), "--dry-run", "--task", "task-d1", "--project", "scratch",
         "--role", "developer", "--branch", "agent/developer-task-d1", "--base", "main",
         "--repo-url", "u", "--repo-path", "/r", "--worktree-root", "/w",
         "--claude-args", "--model m", "--model", "m", "--effort", "high",
         "--session-name", "s", *extra],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_dry_run_shows_the_sparse_step(box):
    out = _dry_run(box)
    assert "sparse_step=on" in out
    assert "worktree add --no-checkout" in out
    assert "python -m tools.worktree apply-sparse" in out
    assert "--role developer" in out
    assert "sparse_step=off" in _dry_run(box, "--no-sparse")
