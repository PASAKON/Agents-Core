"""tools.git_ops push step (task-cdb376d9, github issue #165).

On 2026-09-23 merge_task's push step attempted a single `git push` and
reported `merged: true` regardless of whether it landed on origin — the
merge existed only in the local checkout until a CTO pulled + pushed by
hand (three times that day: a real non-fast-forward race and two GitHub
500s). This file proves the fixed push step:

  - a non-fast-forward rejection is integrated (fetch + `merge --no-edit`,
    never rebase, never --force) and the push retried once
  - a conflicting integration aborts the merge, leaves the local merge
    commit in place, and is reported — never forced
  - transient remote errors (HTTP 5xx / "Internal Server Error" /
    connection reset) are retried up to 3 attempts with a short backoff
  - the result always carries `pushed` and `on_origin`, and a failure's
    `push_error` reads "merged locally, NOT pushed: <reason>" so it can
    never be mistaken for a real success

`_push_base` (and the `_push_once`/`_is_non_ff_rejection`/
`_is_transient_push_error`/`_verify_on_origin` helpers it uses) do not
exist before this fix — every test below fails on today's code at
collection (ImportError). Real temp git repos (bare origin + clones); the
transient-error tests inject the push runner because a real git push has
no way to fabricate an HTTP 500 against a local bare repo (same
constraint the CTO brief's item 2 notes). Test isolation is the root
conftest.py's autouse fixtures (ORG_ROOT / DB / workdir root all pinned to
tmp_path) — no test touches the real repo, tasks.db, or GitHub.

Run via:  pytest tests/test_merge_push.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
from tools import git_ops  # noqa: E402
from tools.git_ops import _push_base  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", *args],
        cwd=str(cwd), capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


# --------------------------------------------------------------- fixtures


@pytest.fixture
def origin_and_hub(tmp_path):
    """Bare `origin` + a `hub` clone (the project checkout `merge_task`
    acts on) already carrying one local, unpushed commit on top of what
    origin has — the state `_push_base` is called in right after a merge
    commit lands locally."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))

    seed = tmp_path / "seed"
    _git(tmp_path, "clone", "-q", str(origin), str(seed))
    (seed / "README.md").write_text("seed\n")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-qm", "C0 seed")
    _git(seed, "push", "-q", "origin", "HEAD:main")

    hub = tmp_path / "hub"
    _git(tmp_path, "clone", "-q", str(origin), str(hub))
    (hub / "feature.txt").write_text("hub work\n")
    _git(hub, "add", "feature.txt")
    _git(hub, "commit", "-qm", "C1 hub merge commit")
    merge_sha = _git(hub, "rev-parse", "HEAD")
    return origin, hub, merge_sha


# ----------------------------------------------------- (a) plain fast-forward


def test_plain_fast_forward_push(origin_and_hub):
    origin, hub, merge_sha = origin_and_hub

    result = _push_base(hub, "main", merge_sha)

    assert result["pushed"] is True
    assert result["on_origin"] is True
    assert "push_error" not in result
    assert _git(hub, "rev-parse", "origin/main") == merge_sha


# ------------------------------------------------- (b) non-ff race, integrates


def test_non_fast_forward_integrates_and_pushes(origin_and_hub):
    origin, hub, merge_sha = origin_and_hub

    # another clone pushes to origin after hub already has its local commit
    # — the exact race the issue describes ("another session had pushed").
    rival = hub.parent / "rival"
    _git(hub.parent, "clone", "-q", str(origin), str(rival))
    (rival / "rival.txt").write_text("rival work\n")
    _git(rival, "add", "rival.txt")
    _git(rival, "commit", "-qm", "C1-rival concurrent commit")
    rival_sha = _git(rival, "rev-parse", "HEAD")
    _git(rival, "push", "-q", "origin", "main")

    result = _push_base(hub, "main", merge_sha)

    assert result["pushed"] is True
    assert result["on_origin"] is True
    assert result.get("integrated") is True
    log = _git(hub, "log", "origin/main", "--format=%H")
    assert merge_sha in log       # hub's own commit made it
    assert rival_sha in log       # rival's commit was integrated, not overwritten
    assert (hub / "rival.txt").exists()
    assert (hub / "feature.txt").exists()


# -------------------------------------------- (c) conflicting concurrent change


def test_conflicting_concurrent_change_never_forces(origin_and_hub):
    origin, hub, merge_sha = origin_and_hub

    # rival adds the SAME path with different content -> add/add conflict
    # when hub tries to integrate origin's history.
    rival = hub.parent / "rival2"
    _git(hub.parent, "clone", "-q", str(origin), str(rival))
    (rival / "feature.txt").write_text("rival conflicting content\n")
    _git(rival, "add", "feature.txt")
    _git(rival, "commit", "-qm", "C1-rival conflicting commit")
    _git(rival, "push", "-q", "origin", "main")
    origin_head_before = _git(hub, "ls-remote", str(origin), "main").split()[0]

    result = _push_base(hub, "main", merge_sha)

    assert result["pushed"] is False
    assert result["on_origin"] is False
    assert result["push_error"].startswith("merged locally, NOT pushed:")
    # local merge commit preserved -- never discarded
    assert _git(hub, "rev-parse", "HEAD") == merge_sha
    # merge --abort left a clean tree, nothing half-applied
    assert _git(hub, "status", "--porcelain") == ""
    # origin untouched -- proves no force-push happened
    assert _git(hub, "ls-remote", str(origin), "main").split()[0] == origin_head_before


# --------------------------------------------- (d) transient error then success


def test_transient_error_retries_then_succeeds(origin_and_hub, monkeypatch):
    origin, hub, merge_sha = origin_and_hub
    real_push_once = git_ops._push_once
    calls = {"n": 0}

    def fake_push_once(repo, base):
        calls["n"] += 1
        if calls["n"] <= 2:
            return 1, "", ("fatal: unable to access origin: The requested URL "
                           "returned error: 500 Internal Server Error")
        return real_push_once(repo, base)

    monkeypatch.setattr(git_ops, "_push_once", fake_push_once)
    sleeps = []
    monkeypatch.setattr(git_ops.time, "sleep", lambda s: sleeps.append(s))

    result = _push_base(hub, "main", merge_sha)

    assert calls["n"] == 3  # measured: a 500 twice, then success on the third try
    assert result["pushed"] is True
    assert result["on_origin"] is True
    assert len(sleeps) == 2  # backoff before retry 2 and retry 3


# ------------------------------------------------ (e) persistent transient fail


def test_persistent_transient_error_fails_after_three_attempts(origin_and_hub, monkeypatch):
    origin, hub, merge_sha = origin_and_hub
    calls = {"n": 0}

    def fake_push_once(repo, base):
        calls["n"] += 1
        return 1, "", "fatal: the remote end hung up unexpectedly: connection reset"

    monkeypatch.setattr(git_ops, "_push_once", fake_push_once)
    monkeypatch.setattr(git_ops.time, "sleep", lambda s: None)

    result = _push_base(hub, "main", merge_sha)

    assert calls["n"] == 3
    assert result["pushed"] is False
    assert result["on_origin"] is False
    assert result["push_error"].startswith("merged locally, NOT pushed:")
    assert "connection reset" in result["push_error"]


# ---------------------------------------- end-to-end through merge_task itself


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


@pytest.fixture
def hub_with_origin(tmp_path):
    origin = tmp_path / "e2e-origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "e2e-seed"
    _git(tmp_path, "clone", "-q", str(origin), str(seed))
    (seed / "README.md").write_text("seed\n")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-qm", "C0 base")
    _git(seed, "push", "-q", "origin", "HEAD:main")
    hub = tmp_path / "e2e-hub"
    _git(tmp_path, "clone", "-q", str(origin), str(hub))
    return origin, hub


def _make_review_task(hub: Path) -> tuple[str, str]:
    tid = db_mod.create_task(project="test-project", role="developer",
                              title="merge push test", description="d")
    branch = f"agent/developer-{tid}"
    _git(hub, "checkout", "-q", "-b", branch)
    (hub / "feature.txt").write_text("hello\n")
    _git(hub, "add", "-A")
    _git(hub, "commit", "-q", "-m", "C1 feature")
    _git(hub, "checkout", "-q", "main")
    db_mod.update_status(tid, "review", actor="test")
    return tid, branch


def _fake_project(repo: Path) -> dict:
    return {"key": "test-project", "path": str(repo), "default_branch": "main"}


def test_merge_task_pushes_and_reports_on_origin(temp_db, hub_with_origin, monkeypatch):
    origin, hub = hub_with_origin
    monkeypatch.setattr(git_ops, "get_project", lambda key: _fake_project(hub))
    tid, branch = _make_review_task(hub)

    result = git_ops.merge_task(tid, push=True, cleanup=False)

    assert result["merged"] is True
    assert result["pushed"] is True
    assert result["on_origin"] is True
    assert "push_error" not in result
    merge_sha = result["merge_sha"]
    assert _git(hub, "rev-parse", "origin/main") == merge_sha
    assert db_mod.get_task(tid)["status"] == "done"


def test_merge_task_push_false_reports_pushed_false_without_attempting(
    temp_db, hub_with_origin, monkeypatch
):
    origin, hub = hub_with_origin
    monkeypatch.setattr(git_ops, "get_project", lambda key: _fake_project(hub))
    tid, branch = _make_review_task(hub)

    result = git_ops.merge_task(tid, push=False, cleanup=False)

    assert result["merged"] is True
    assert result["pushed"] is False
    assert result["on_origin"] is False
    # origin never advanced -- push was never attempted
    _git(hub, "fetch", "-q", "origin", "main")
    assert _git(hub, "rev-parse", "origin/main") != result["merge_sha"]
