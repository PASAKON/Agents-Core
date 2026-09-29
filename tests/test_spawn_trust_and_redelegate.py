"""GH #161, #83, #124: the spawn fixes around folder trust and re-delegate.

- #161: delegate records the worktree as trusted in Claude Code's config, a
  wake never types Enter into the folder-trust prompt, the kickoff fails the
  task loudly when a worker is stuck there, and a pending row that still
  names an agent is reset so the next worker can claim.
- #83: a tmux session that dies at once fails the task (RuntimeError used to
  escape), a missing worktree is re-attached to its branch without losing
  commits, and a bare-shell tab is never reused.
- #124: with no owner window, the worker opens a window of its own.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.agent_transport as agent_transport  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.tmux_session as tmux_session  # noqa: E402
import tools.worktree as worktree  # noqa: E402
from lib import claude_trust  # noqa: E402


# --------------------------------------------------------------------------
# lib/claude_trust.py
# --------------------------------------------------------------------------

CLAUDE_JSON = (
    '{\n  "numStartups": 3,\n  "projects": {\n'
    '    "/other/project": {\n      "allowedTools": [],\n'
    '      "hasTrustDialogAccepted": true\n    }\n  },\n  "userID": "x"\n}\n'
)


def test_trust_path_adds_only_the_new_key(tmp_path):
    cfg = tmp_path / "claude.json"
    cfg.write_text(CLAUDE_JSON)
    wt = tmp_path / "wt"
    wt.mkdir()

    assert claude_trust.trust_path(wt, claude_json=cfg) == "ok"

    text = cfg.read_text()
    data = json.loads(text)
    assert data["projects"][str(wt)]["hasTrustDialogAccepted"] is True
    assert data["projects"]["/other/project"]["allowedTools"] == []
    # every original byte is still there, in order: only an insertion
    assert text.replace(f'\n    {json.dumps(str(wt))}: {{"hasTrustDialogAccepted": true}},', "") == CLAUDE_JSON


def test_trust_path_is_idempotent(tmp_path):
    cfg = tmp_path / "claude.json"
    cfg.write_text(CLAUDE_JSON)
    wt = tmp_path / "wt"
    wt.mkdir()
    claude_trust.trust_path(wt, claude_json=cfg)
    before = cfg.read_text()
    assert claude_trust.trust_path(wt, claude_json=cfg) == "already"
    assert cfg.read_text() == before


def test_trust_path_trusts_the_symlinked_and_the_real_path(tmp_path):
    cfg = tmp_path / "claude.json"
    cfg.write_text(CLAUDE_JSON)
    real = tmp_path / "MoonieXHQ" / "wt"
    real.mkdir(parents=True)
    link = tmp_path / "Projects-link"
    link.symlink_to(tmp_path / "MoonieXHQ")

    assert claude_trust.trust_path(link / "wt", claude_json=cfg) == "ok"

    projects = json.loads(cfg.read_text())["projects"]
    assert projects[str(link / "wt")]["hasTrustDialogAccepted"] is True
    assert projects[str(real)]["hasTrustDialogAccepted"] is True


def test_trust_path_sets_the_flag_on_an_existing_untrusted_row(tmp_path):
    cfg = tmp_path / "claude.json"
    wt = tmp_path / "wt"
    wt.mkdir()
    cfg.write_text(json.dumps({"projects": {str(wt): {"allowedTools": ["Bash"]}}}, indent=2))

    assert claude_trust.trust_path(wt, claude_json=cfg) == "ok"

    row = json.loads(cfg.read_text())["projects"][str(wt)]
    assert row == {"allowedTools": ["Bash"], "hasTrustDialogAccepted": True}


def test_trust_path_never_raises(tmp_path):
    assert claude_trust.trust_path(tmp_path, claude_json=tmp_path / "absent.json").startswith("skipped")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert claude_trust.trust_path(tmp_path, claude_json=bad).startswith("skipped")
    assert bad.read_text() == "{not json"


def test_test_suite_never_points_at_the_real_claude_json():
    assert claude_trust.claude_json_path() != Path.home() / ".claude.json"


# --------------------------------------------------------------------------
# the trust-prompt guard
# --------------------------------------------------------------------------

TRUST_SCREEN = (
    "Accessing workspace: /x/worktrees/proj__developer__task-1\n"
    "Quick safety check: Is this a project you created or one you trust?\n"
    " ❯ No, exit\n   Yes, I trust this folder\n"
)


def _fake_capture(monkeypatch, screen: str):
    def run(argv, **kw):
        assert "capture-pane" in argv
        return subprocess.CompletedProcess(argv, 0, stdout=screen, stderr="")
    monkeypatch.setattr(tmux_session.subprocess, "run", run)


def test_shows_trust_dialog(monkeypatch):
    _fake_capture(monkeypatch, TRUST_SCREEN)
    assert tmux_session.shows_trust_dialog("wd-1") is True
    _fake_capture(monkeypatch, "> working on it\n")
    assert tmux_session.shows_trust_dialog("wd-1") is False


def test_wake_does_not_press_enter_into_the_trust_prompt(monkeypatch):
    sent = []
    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: True)
    monkeypatch.setattr(agent_transport.tmux_session, "shows_trust_dialog", lambda s: True)
    agent_transport.attempt_wake("wd-1", "CTO", "test", send_fn=lambda s, t: sent.append(s))
    assert sent == []

    monkeypatch.setattr(agent_transport.tmux_session, "shows_trust_dialog", lambda s: False)
    agent_transport.attempt_wake("wd-1", "CTO", "test", send_fn=lambda s, t: sent.append(s))
    assert sent == ["wd-1"]


@pytest.fixture()
def db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


def _task(db, **fields) -> str:
    tid = db.create_task(project="test-project", role="developer",
                         title="t", description="d", owner_cto="owner")
    if fields:
        db.set_fields(tid, **fields)
    return tid


def test_kickoff_fails_a_worker_stuck_at_the_trust_prompt(db, monkeypatch):
    tid = _task(db, tmux_session="wd-1", worktree="/x/wt")
    db.update_status(tid, "in_progress", assigned_agent="developer", pid=1)
    monkeypatch.setattr(delegate.tmux, "shows_trust_dialog", lambda s: s == "wd-1")
    monkeypatch.setattr(delegate, "KICKOFF_DELAY_S", 0)
    sent = []
    import tools.send_to_worker as stw
    monkeypatch.setattr(stw, "send", lambda task_id, msg: sent.append(task_id))

    asyncio.run(delegate._auto_kickoff(tid, "go"))

    t = db.get_task(tid)
    assert sent == []
    assert t["status"] == "failed"
    assert "folder-trust prompt" in t["delegate_log"] and "/x/wt" in t["delegate_log"]


def test_kickoff_is_sent_when_no_trust_prompt(db, monkeypatch):
    tid = _task(db, tmux_session="wd-1")
    monkeypatch.setattr(delegate.tmux, "shows_trust_dialog", lambda s: False)
    monkeypatch.setattr(delegate, "KICKOFF_DELAY_S", 0)
    sent = []
    import tools.send_to_worker as stw
    monkeypatch.setattr(stw, "send", lambda task_id, msg: sent.append(task_id) or "queued")

    asyncio.run(delegate._auto_kickoff(tid, "go"))

    assert sent == [tid]


# --------------------------------------------------------------------------
# _spawn_local: trust write + tmux RuntimeError (GH #161, #83 ask 1)
# --------------------------------------------------------------------------

def test_spawn_local_trusts_the_worktree_and_fails_on_a_dead_tmux(db, monkeypatch, tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    cfg = tmp_path / "claude.json"
    cfg.write_text('{"projects": {}}')
    monkeypatch.setenv("ORG_CLAUDE_JSON", str(cfg))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(delegate, "self_host", lambda: "contabo")
    monkeypatch.setattr(delegate, "_work_dir_for", lambda *a: None)

    def dead(sess, cwd, cmd):
        raise RuntimeError(f"tmux session {sess!r} was not alive after new-session")
    monkeypatch.setattr(delegate.tmux, "create", dead)

    tid = _task(db, worktree=str(wt))
    row = asyncio.run(delegate._spawn_local(db.get_task(tid), {"web_ui": "off"}))

    assert row["status"] == "failed"
    assert "not alive after new-session" in row["delegate_log"]
    assert json.loads(cfg.read_text())["projects"][str(wt)]["hasTrustDialogAccepted"] is True


# --------------------------------------------------------------------------
# delegate_task re-delegate paths (GH #161 second trap, #83 ask 2)
# --------------------------------------------------------------------------

@pytest.fixture()
def redelegate(db, monkeypatch, tmp_path):
    monkeypatch.setattr(delegate, "_scope_owners", lambda feature: [])
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    monkeypatch.setattr(delegate, "get_project", lambda key: {
        "path": str(tmp_path), "default_branch": "main",
        "agents_allowed": ["developer"], "spawn_backend": "iterm", "web_ui": "off",
    })
    monkeypatch.setenv("ORG_ROUTER", "off")
    rec = {"spawned": [], "restored": []}

    async def fake_spawn_local(task, proj, **kw):
        rec["spawned"].append(db.get_task(task["id"]))
        return db.get_task(task["id"])

    monkeypatch.setattr(delegate, "_spawn_local", fake_spawn_local)
    return rec


def _dead_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def test_pending_row_that_still_names_an_agent_is_reset(db, redelegate, tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    tid = _task(db, worktree=str(wt))
    # the hand reset from GH #161: status pending, pid NULL, agent left set
    db.set_fields(tid, assigned_agent="developer", pid=None)

    asyncio.run(delegate.delegate_task(tid))

    assert len(redelegate["spawned"]) == 1
    row = redelegate["spawned"][0]
    assert row["assigned_agent"] is None
    assert db.claim_task(tid, agent="developer")


def test_pending_row_with_a_live_agent_is_not_reset(db, redelegate, tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    tid = _task(db, worktree=str(wt))
    db.set_fields(tid, assigned_agent="developer", pid=os.getpid())

    asyncio.run(delegate.delegate_task(tid))

    assert redelegate["spawned"] == []
    assert "live pid" in db.get_task(tid)["delegate_log"]


def test_missing_worktree_is_restored_before_spawn(db, redelegate, monkeypatch, tmp_path):
    gone = tmp_path / "gone"
    tid = _task(db, worktree=str(gone), branch="agent/developer-x")
    db.update_status(tid, "failed", force=True)
    calls = []

    def fake_restore(project, role, task_id, *, branch=None, sparse=False):
        calls.append(branch)
        gone.mkdir()
        return {"worktree": str(gone), "branch": branch}
    monkeypatch.setattr(delegate, "restore_worktree", fake_restore)

    asyncio.run(delegate.delegate_task(tid))

    assert calls == ["agent/developer-x"]
    assert len(redelegate["spawned"]) == 1


def test_failed_restore_fails_the_task_instead_of_spawning(db, redelegate, monkeypatch, tmp_path):
    tid = _task(db, worktree=str(tmp_path / "gone"))
    db.update_status(tid, "failed", force=True)

    def boom(*a, **kw):
        raise worktree.GitError("fatal: invalid reference")
    monkeypatch.setattr(delegate, "restore_worktree", boom)

    row = asyncio.run(delegate.delegate_task(tid))

    assert redelegate["spawned"] == []
    assert row["status"] == "failed"
    assert "restore failed" in row["delegate_log"]


# --------------------------------------------------------------------------
# tools/worktree.restore_worktree keeps the branch's commits (#83 ask 2)
# --------------------------------------------------------------------------

def _git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture()
def repo(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "a.txt").write_text("a\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    wt_dir = tmp_path / "worktrees"
    monkeypatch.setattr(worktree, "_repo_path", lambda key: repo)
    monkeypatch.setattr(worktree, "WORKTREE_DIR", wt_dir)
    monkeypatch.setattr(worktree, "get_project", lambda key: {"default_branch": "main"})
    monkeypatch.setattr(worktree, "provision_worktree", lambda repo, wt: [])
    return repo


def test_restore_worktree_reattaches_the_branch_with_its_commits(repo):
    wt = worktree.worktree_path("proj", "developer", "task-1")
    branch = worktree.branch_name("developer", "task-1")
    _git(repo, "worktree", "add", "-q", "-b", branch, str(wt))
    (wt / "work.txt").write_text("unmerged work\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "worker commit")
    sha = _git(wt, "rev-parse", "HEAD")
    import shutil
    shutil.rmtree(wt)            # what gc_stale_tasks leaves behind

    info = worktree.restore_worktree("proj", "developer", "task-1")

    assert info["restored"] is True
    assert (wt / "work.txt").read_text() == "unmerged work\n"
    assert _git(wt, "rev-parse", "HEAD") == sha


def test_restore_worktree_creates_fresh_when_the_branch_is_gone(repo, monkeypatch):
    made = []
    monkeypatch.setattr(worktree, "create_worktree",
                        lambda p, r, t, sparse=False: made.append(t) or {"worktree": "x"})
    worktree.restore_worktree("proj", "developer", "task-2")
    assert made == ["task-2"]


# --------------------------------------------------------------------------
# the iTerm AppleScript (#83 ask 3, #124)
# --------------------------------------------------------------------------

def test_applescript_does_not_reuse_a_bare_shell_tab():
    script = delegate._build_spawn_applescript("echo hi", "task-1", "abc")
    assert '"(-zsh)"' in script and "set bareShell to true" in script
    assert "if not bareShell then" in script


def test_applescript_never_falls_back_to_the_frontmost_window():
    script = delegate._build_spawn_applescript("echo hi", "task-1", "abc")
    assert "set targetWin to current window" not in script
    assert "set targetWin to (create window with default profile)" in script
    assert 'return "spawned"' in script


def test_owner_without_winid_is_reported(monkeypatch):
    warned = []
    monkeypatch.setattr(delegate, "warn", lambda m: warned.append(m))
    monkeypatch.setattr(delegate, "_owner_window_id", lambda *a: None)
    monkeypatch.setattr(delegate.subprocess, "run",
                        lambda argv, **kw: subprocess.CompletedProcess(argv, 0, stdout="spawned"))

    delegate._spawn_iterm_tab("developer", "task-1", owner_cto="eab87266", owner_role="cto")

    assert any("cto-eab87266" in m and "GH #124" in m for m in warned)
