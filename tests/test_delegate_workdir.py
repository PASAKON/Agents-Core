"""tools/delegate.py WORK_DIR export + tools/git_ops.py merge close-gate
(task-36aaa3c4, Work/RULES.md, ADR 0030 §8 `work_dir` scope).

`work_dir` scope only: `delegate._scope_owners` is monkeypatched to return
a known list for every feature (`temp_db` fixture below), mirroring
tests/test_delegate_disk_floor.py's own pattern. A task owned by anyone
outside that list must be completely untouched by this task's changes —
that's the scope check the brief asks to prove "must fail if removed":
every out-of-scope test below would start failing (a folder appears,
WORK_DIR gets exported, or a merge gets gated) if the
`_scope_applies("work_dir", owner_cto)` guard were deleted from
`_work_dir_for` / the git_ops.py close gate. Checked directly against a
per-feature scope map (not just the fixture's flat list) in
`test_work_dir_for_scope_all_and_list_and_missing_key` below.

Run via:  pytest tests/test_delegate_workdir.py
(collected by the default `pytest` run — pytest.ini `testpaths` now
includes `tests` alongside `scripts lib`.)
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.git_ops as git_ops  # noqa: E402
import tools.workdir as workdir  # noqa: E402


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    # Storage scope (ADR 0030 §8): "pilot-owner" is in scope for every
    # feature this file exercises (work_dir via _work_dir_for / the
    # git_ops.py close gate).
    monkeypatch.setattr(delegate, "_scope_owners", lambda feature: ["pilot-owner"])
    db_mod.init()
    return db_mod


@pytest.fixture()
def work_root(monkeypatch, tmp_path):
    """Redirect tools.workdir's default root (used by every internal call
    inside delegate.py / git_ops.py that doesn't pass root= explicitly) to
    a tmp_path — never the real ~/MoonieXHQ/Work/."""
    root = tmp_path / "Work"
    monkeypatch.setattr(workdir, "_default_root", lambda: root)
    return root


def _new_task(owner: str) -> str:
    return db_mod.create_task(project="test-project", role="developer",
                              title="workdir test", description="d",
                              owner_cto=owner)


# --------------------------------------------------------- _work_dir_for unit

def test_work_dir_for_pilot_creates_folder(temp_db, work_root):
    tid = _new_task("pilot-owner")
    path = delegate._work_dir_for(tid, "pilot-owner")
    assert path is not None
    folder = Path(path)
    assert folder == work_root / tid
    assert (folder / "in").is_dir()
    assert (folder / "tmp").is_dir()
    assert (folder / "out").is_dir()


def test_work_dir_for_non_pilot_returns_none_and_creates_nothing(temp_db, work_root):
    """The scope check itself: removing the `if not
    _scope_applies("work_dir", owner_cto): return None` guard in
    tools/delegate.py:_work_dir_for makes this fail — a folder would get
    created for an out-of-scope owner too."""
    tid = _new_task("someone-else")
    path = delegate._work_dir_for(tid, "someone-else")
    assert path is None
    assert not (work_root / tid).exists()


def test_work_dir_for_scope_all_and_list_and_missing_key(monkeypatch, tmp_path):
    """Direct coverage of the scope map itself (not just the fixture's flat
    list): "all" covers an arbitrary owner AND owner=None; a list covers
    only its members; a policy with no `work_dir` scope key covers nobody.
    Fails if `_scope_applies`/`_scope_owners` regress to the old
    single-list `_storage_applies` semantics."""
    policy = tmp_path / "policy.yaml"

    policy.write_text("scope: {work_dir: all}\n")
    monkeypatch.setattr(delegate, "STORAGE_POLICY", policy)
    assert delegate._scope_applies("work_dir", "any-owner-at-all") is True
    assert delegate._scope_applies("work_dir", None) is True

    policy.write_text("scope: {work_dir: ['pilot-owner']}\n")
    assert delegate._scope_applies("work_dir", "pilot-owner") is True
    assert delegate._scope_applies("work_dir", "someone-else") is False
    assert delegate._scope_applies("work_dir", None) is False

    policy.write_text("scope: {reclaim: all}\n")  # work_dir key absent
    assert delegate._scope_applies("work_dir", "pilot-owner") is False


# ------------------------------------------------- _spawn_iterm_tab cmd string

def test_spawn_iterm_tab_exports_work_dir_next_to_worker_cto_id(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["script"] = cmd[2]  # ["osascript", "-e", <script>]
        class _R:
            stdout = "spawned"
        return _R()

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    delegate._spawn_iterm_tab("developer", "task-cafe1234",
                              owner_cto="pilot-owner",
                              work_dir="/tmp/fake-work/task-cafe1234")
    assert "export WORKER_CTO_ID='pilot-owner'" in captured["script"]
    assert "export WORK_DIR='/tmp/fake-work/task-cafe1234'" in captured["script"]


def test_spawn_iterm_tab_omits_work_dir_when_none(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["script"] = cmd[2]
        class _R:
            stdout = "spawned"
        return _R()

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    delegate._spawn_iterm_tab("developer", "task-cafe1234", owner_cto="someone-else")
    assert "WORK_DIR" not in captured["script"]


# ------------------------------------------------------- delegate_task, full

def _fake_project() -> dict:
    return {
        "path": "/tmp/does-not-matter",
        "default_branch": "main",
        "agents_allowed": ["developer"],
        "spawn_backend": "iterm",
        "web_ui": "off",
    }


def _fake_create_worktree(project_key, role, task_id, sparse=False):
    return {"project": project_key, "task_id": task_id, "role": role,
            "branch": f"agent/{role}-{task_id}",
            "worktree": f"/tmp/fake-worktree-{task_id}",
            "base": "main", "repo": "/tmp/does-not-matter", "provisioned": []}


def test_delegate_task_exports_work_dir_for_pilot_owner(temp_db, work_root, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "get_project", lambda key: _fake_project())
    monkeypatch.setattr(delegate, "create_worktree", _fake_create_worktree)

    spawn_kwargs = {}

    def fake_spawn_iterm_tab(role, task_id, **kw):
        spawn_kwargs.update(kw)
        return "spawned"

    monkeypatch.setattr(delegate, "_spawn_iterm_tab", fake_spawn_iterm_tab)

    tid = _new_task("pilot-owner")
    asyncio.run(delegate.delegate_task(tid))

    assert spawn_kwargs.get("work_dir") is not None
    assert Path(spawn_kwargs["work_dir"]) == work_root / tid
    assert (work_root / tid / "in").is_dir()


def test_delegate_task_gives_non_pilot_neither_folder_nor_env(temp_db, work_root, monkeypatch):
    """Must fail if the scope check is removed: without
    `_scope_applies("work_dir", ...)` gating `_work_dir_for`, this
    out-of-scope task would also get a Work/ folder and a WORK_DIR export."""
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "get_project", lambda key: _fake_project())
    monkeypatch.setattr(delegate, "create_worktree", _fake_create_worktree)

    spawn_kwargs = {}

    def fake_spawn_iterm_tab(role, task_id, **kw):
        spawn_kwargs.update(kw)
        return "spawned"

    monkeypatch.setattr(delegate, "_spawn_iterm_tab", fake_spawn_iterm_tab)

    tid = _new_task("someone-else")
    asyncio.run(delegate.delegate_task(tid))

    assert spawn_kwargs.get("work_dir") is None
    assert not (work_root / tid).exists()


# --------------------------------------------------- git_ops.merge_task gate

def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}\n{r.stderr}")
    return r.stdout.strip()


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@test")
    _git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("base\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "C0 base")


@pytest.fixture()
def merge_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    return repo


def _make_review_task(repo: Path, owner: str) -> tuple[str, str]:
    tid = _new_task(owner)
    branch = f"agent/developer-{tid}"
    _git(repo, "checkout", "-q", "-b", branch)
    (repo / "feature.txt").write_text("hello\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "C1 feature")
    _git(repo, "checkout", "-q", "main")
    db_mod.update_status(tid, "review", actor="test")
    return tid, branch


def _fake_git_ops_project(repo: Path) -> dict:
    return {"key": "test-project", "path": str(repo), "default_branch": "main"}


def test_merge_refused_while_work_folder_has_unfiled_files(
    temp_db, work_root, merge_repo, monkeypatch
):
    monkeypatch.setattr(git_ops, "get_project", lambda key: _fake_git_ops_project(merge_repo))
    tid, branch = _make_review_task(merge_repo, "pilot-owner")
    folder = workdir.create(tid, root=work_root)
    (folder / "out" / "deliverable.mp4").write_bytes(b"x" * 9)

    result = git_ops.merge_task(tid, push=False, cleanup=False)

    assert result["merged"] is False
    assert result["work_dir_unfiled"] is True
    assert any("deliverable.mp4" in f for f in result["unfiled"])
    assert folder.is_dir()  # never removed
    assert db_mod.get_task(tid)["status"] == "review"  # never flipped to done
    # the merge itself never ran (gate is pre-flight, before any git mutation)
    assert _git(merge_repo, "log", "-1", "--format=%s") == "C0 base"


def test_merge_allowed_after_work_folder_is_clean(
    temp_db, work_root, merge_repo, monkeypatch
):
    monkeypatch.setattr(git_ops, "get_project", lambda key: _fake_git_ops_project(merge_repo))
    tid, branch = _make_review_task(merge_repo, "pilot-owner")
    workdir.create(tid, root=work_root)  # empty folder, nothing to file

    result = git_ops.merge_task(tid, push=False, cleanup=False)

    assert result["merged"] is True
    assert db_mod.get_task(tid)["status"] == "done"
    assert not (work_root / tid).exists()  # closed + removed
    assert _git(merge_repo, "log", "-1", "--format=%s") == f"Merge {branch} (task {tid})"


def test_merge_unchanged_for_non_pilot_owner_even_with_unfiled_files(
    temp_db, work_root, merge_repo, monkeypatch
):
    """Scope check at the merge gate: an out-of-scope owner's merge is
    never gated by Work/, even when a folder exists with unfiled files —
    proves `_scope_applies("work_dir", ...)` (not blanket enforcement)
    decides. This would fail if the `if _scope_applies(...)` guard were
    removed from tools/git_ops.py's close gate."""
    monkeypatch.setattr(git_ops, "get_project", lambda key: _fake_git_ops_project(merge_repo))
    tid, branch = _make_review_task(merge_repo, "someone-else")
    folder = workdir.create(tid, root=work_root)
    (folder / "out" / "deliverable.mp4").write_bytes(b"x")

    result = git_ops.merge_task(tid, push=False, cleanup=False)

    assert result["merged"] is True  # never gated — folder ignored
    assert folder.is_dir()  # workdir never touched for a non-pilot task
    assert (folder / "out" / "deliverable.mp4").exists()


def test_merge_allowed_for_pilot_task_with_no_work_folder(
    temp_db, work_root, merge_repo, monkeypatch
):
    """Tasks spawned before this change (e.g. task-2b587031) have no Work/
    folder at all — merge_task must not require one to exist. The close
    gate only fires when `workdir.folder_path(task_id).exists()`."""
    monkeypatch.setattr(git_ops, "get_project", lambda key: _fake_git_ops_project(merge_repo))
    tid, branch = _make_review_task(merge_repo, "pilot-owner")
    assert not workdir.folder_path(tid, root=work_root).exists()  # never created

    result = git_ops.merge_task(tid, push=False, cleanup=False)

    assert result["merged"] is True
    assert db_mod.get_task(tid)["status"] == "done"
