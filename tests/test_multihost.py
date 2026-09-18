"""Tests for Phase 1 multi-host workers (docs/design/multi-host-workers.md).

Covers: remote argv rendering per role (worker_tool_grants reuse), hosts/
paths resolution + the not-routable error, branch_poller state transitions
against a real local git repo standing in for GitHub (no network), and
`.worker.json` parsing.

Run via:  pytest tests/test_multihost.py
(not in pytest.ini's default `testpaths` — run explicitly, alongside the
default `pytest` run, per this task's own Rules.)
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
import lib.db as db_mod  # noqa: E402
import runners.branch_poller as poller  # noqa: E402
import runners.worker_init as worker_init  # noqa: E402
import tools.delegate as delegate  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Remote argv rendering per role — reuses worker_tool_grants, never a
#    second hand-maintained flag list.
# ---------------------------------------------------------------------------

def test_render_remote_claude_args_developer_has_no_chrome():
    args = delegate._render_remote_claude_args("developer", "winbox")
    assert "--chrome" not in args
    assert "--remote-control" in args
    assert "--strict-mcp-config" in args
    assert "--model" in args and "--effort" in args


def test_render_remote_claude_args_browser_operator_gets_chrome():
    args = delegate._render_remote_claude_args("browser_operator", "winbox")
    assert "--chrome" in args
    assert "mcp__claude-in-chrome__navigate" in args


def test_render_remote_claude_args_allowed_tools_is_last():
    """--allowed-tools is variadic and swallows every following argv
    element (runners/worker_init.py's own documented rule) — it must be
    the last flag in the rendered string, nothing after it."""
    args = delegate._render_remote_claude_args("developer", "winbox")
    parts = args.split()
    idx = parts.index("--allowed-tools")
    # Exactly one token follows --allowed-tools (the comma-joined list) —
    # if a later flag existed it would appear as a second token here.
    assert idx == len(parts) - 2


def test_render_remote_claude_args_no_remote_control_when_host_disables(monkeypatch):
    """config/hosts.yaml's `remote_control: false` must actually suppress
    the flag on a remote spawn — this used to be a literal `--remote-control`
    that hosts.yaml had no way to turn off."""
    monkeypatch.setattr(worker_init, "get_host", lambda name: {"remote_control": False})
    args = delegate._render_remote_claude_args("developer", "some-host")
    assert "--remote-control" not in args.split()


def test_render_remote_claude_args_allowed_tools_still_last_without_remote_control(monkeypatch):
    """--allowed-tools stays the last token even when --remote-control is
    dropped (one fewer flag ahead of it) — it is variadic and swallows
    everything after it, so nothing may follow."""
    monkeypatch.setattr(worker_init, "get_host", lambda name: {"remote_control": False})
    args = delegate._render_remote_claude_args("browser_operator", "some-host")
    parts = args.split()
    assert "--remote-control" not in parts
    idx = parts.index("--allowed-tools")
    assert idx == len(parts) - 2


def test_spawn_iterm_tab_tmux_branch_exits_after_attach(monkeypatch):
    """ADDENDUM 2 (CTO 2026-09-07): ending a worker must close its window,
    not just the process — the tmux-attach tab command must end `; exit $?`
    so a dead tmux session doesn't leave a bare shell prompt open (mirrors
    the non-tmux branch's GH #27 fix)."""
    captured = {}

    class _FakeResult:
        stdout = "spawned"

    def fake_run(cmd, **kwargs):
        captured["script"] = cmd[2]  # ["osascript", "-e", <script>]
        return _FakeResult()

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    delegate._spawn_iterm_tab("developer", "task-xyz", tmux_attach="cto-abc123")
    assert "tmux attach -t cto-abc123; exit $?" in captured["script"]


# ---------------------------------------------------------------------------
# ADDENDUM 3: per-host browser_operator cap, enforced at delegate_task time.
# ---------------------------------------------------------------------------

def _insert_task(db_mod_, *, task_id: str, role: str, status: str,
                 host: str | None, project: str = "mooniex-agents") -> None:
    with db_mod_.get_conn() as conn:
        ts = db_mod_.now_iso()
        conn.execute(
            """INSERT INTO tasks
               (id, project, role, status, title, description,
                touches, depends_on, host, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, project, role, status, "t", "d",
             json.dumps([]), "[]", host, ts, ts),
        )
        conn.commit()


def test_browser_operator_cap_reached_sets_conflict(temp_db):
    # mac's cap is 2 — two already live on mac.
    _insert_task(temp_db, task_id="task-bo01", role="browser_operator",
                status="in_progress", host=None)  # NULL counts as mac
    _insert_task(temp_db, task_id="task-bo02", role="browser_operator",
                status="rate_limited", host="mac")
    _insert_task(temp_db, task_id="task-bo03", role="browser_operator",
                status="pending", host="mac")
    new_id = temp_db.create_task(
        project="mooniex-agents", role="browser_operator", title="t3",
        description="d", owner_cto="test-owner",
    )

    result = asyncio.run(delegate.delegate_task(new_id, host="mac"))

    assert result["status"] == "conflict"
    assert "browser cap: 2/2 operators live on mac" in result["delegate_log"]


def test_browser_operator_below_cap_is_not_blocked(temp_db):
    """Below cap, the check must not short-circuit — it should fall through
    to the real spawn path. host='winbox' + dry_run=True keeps this test
    network- and side-effect-free (no real worktree/git ops against the
    canonical repo) while still proving the cap check itself let it pass:
    a dry-run write leaves status='pending' (only delegate_log is set), so
    reaching that instead of 'conflict' is proof the cap did not block it."""
    new_id = temp_db.create_task(
        project="mooniex-agents", role="browser_operator", title="t1",
        description="d", owner_cto="test-owner", host="winbox",
    )
    result = asyncio.run(delegate.delegate_task(new_id, host="winbox", dry_run=True))
    assert result["status"] == "pending"
    assert "[dry-run]" in (result.get("delegate_log") or "")


def test_browser_operator_cap_winbox_is_two(temp_db):
    """winbox allows TWO browser operators, not one.

    The CEO raised it on 2026-09-09 ("ไม่เกิน 2 Worker", commit b9370bd9 --
    the second slot is a read-only tab) and config/hosts.yaml has carried
    max_browser_operators: 2 ever since. This test kept asserting 1/1 and so
    stayed red for ten days, which is worse than having no test: a suite with
    a familiar failure in it is a suite nobody reads. The cap the test asserts
    must come from the same place the code reads it.
    """
    _insert_task(temp_db, task_id="task-bo10", role="browser_operator",
                status="in_progress", host="winbox")
    _insert_task(temp_db, task_id="task-bo11", role="browser_operator",
                status="in_progress", host="winbox")
    new_id = temp_db.create_task(
        project="mooniex-agents", role="browser_operator", title="t2",
        description="d", owner_cto="test-owner", host="winbox",
    )

    result = asyncio.run(delegate.delegate_task(new_id, host="winbox", dry_run=True))

    assert result["status"] == "conflict"
    assert "browser cap: 2/2 operators live on winbox" in result["delegate_log"]


def test_browser_operator_one_live_on_winbox_still_passes(temp_db):
    """One live operator is BELOW winbox's cap of two -- it must not block."""
    _insert_task(temp_db, task_id="task-bo12", role="browser_operator",
                status="in_progress", host="winbox")
    new_id = temp_db.create_task(
        project="mooniex-agents", role="browser_operator", title="t3",
        description="d", owner_cto="test-owner", host="winbox",
    )

    result = asyncio.run(delegate.delegate_task(new_id, host="winbox", dry_run=True))

    assert result["status"] == "pending"


def test_ssh_remote_url_converts_https():
    assert (delegate._ssh_remote_url("https://github.com/PASAKON/mooniex-agents.git")
            == "git@github.com:PASAKON/mooniex-agents.git")


def test_ssh_remote_url_leaves_ssh_unchanged():
    ssh_url = "git@github.com:PASAKON/mooniex-webapp.git"
    assert delegate._ssh_remote_url(ssh_url) == ssh_url


def test_ssh_remote_url_bad_format_raises():
    with pytest.raises(ValueError):
        delegate._ssh_remote_url("not-a-url")


def test_ps_quote_escapes_special_characters():
    quoted = delegate._ps_quote('a "quoted" $value `backtick`')
    assert quoted.startswith('"') and quoted.endswith('"')
    assert '`"quoted`"' in quoted
    assert "`$value" in quoted
    assert "``backtick``" in quoted


# ---------------------------------------------------------------------------
# 2. hosts.yaml / projects.yaml paths resolution + the not-routable error
# ---------------------------------------------------------------------------

def test_hosts_loads_all_three():
    h = config.hosts()
    assert set(h) == {"mac", "winbox", "contabo"}


def test_host_mac_has_no_ssh_alias():
    assert config.host("mac")["ssh"] is None
    assert config.host("winbox")["ssh"] == "winbox"
    assert config.host("winbox")["os"] == "windows"


def test_host_unknown_raises():
    with pytest.raises(ValueError, match="unknown host"):
        config.host("does-not-exist")


def test_project_path_for_host_mac_falls_back_to_top_level_path():
    # mooniex-agents has both a top-level `path:` and paths.mac — must agree.
    assert (config.project_path_for_host("mooniex-agents", "mac")
            == config.get_project("mooniex-agents")["path"])


def test_project_path_for_host_winbox_resolves():
    p = config.project_path_for_host("mooniex-agents", "winbox")
    assert p == r"C:\Users\UsEr\mooniex\repo\MoonieX-Agents"


def test_project_path_for_host_not_routable_raises_clear_error():
    # mooniex-console has no `paths:` entry at all.
    with pytest.raises(ValueError, match="not routable"):
        config.project_path_for_host("mooniex-console", "winbox")


def test_worker_session_name_shape():
    name = config.worker_session_name(
        "winbox", "browser_operator", "task-4a59a1a4", "SHOOT the teaser")
    assert name == "WINDOWS Browser Operator #4a59a1a4 (SHOOT the teaser)"


def test_worker_session_name_truncates_long_title():
    long_title = "x" * 80
    name = config.worker_session_name("mac", "developer", "task-abcd1234", long_title)
    assert "…" in name
    assert len(name.split("(", 1)[1]) <= 45  # 40 chars + ellipsis + ")"


# ---------------------------------------------------------------------------
# 3. .worker.json parsing
# ---------------------------------------------------------------------------

def test_parse_worker_json_valid():
    blob = json.dumps({"pid": 4242, "started_at": "2026-09-07T06:00:00Z", "host": "winbox"})
    data = poller.parse_worker_json(blob)
    assert data == {"pid": 4242, "started_at": "2026-09-07T06:00:00Z", "host": "winbox"}


def test_parse_worker_json_missing_field_raises():
    blob = json.dumps({"pid": 1, "host": "winbox"})
    with pytest.raises(ValueError, match="missing field"):
        poller.parse_worker_json(blob)


def test_parse_worker_json_bad_pid_type_raises():
    blob = json.dumps({"pid": "not-a-number", "started_at": "x", "host": "winbox"})
    with pytest.raises(ValueError, match="pid is not an int"):
        poller.parse_worker_json(blob)


def test_parse_worker_json_not_an_object_raises():
    with pytest.raises(ValueError, match="not an object"):
        poller.parse_worker_json("[1, 2, 3]")


# ---------------------------------------------------------------------------
# 4. branch_poller state transitions against a real local git repo standing
#    in for GitHub — a `git fetch`/`ls-remote`/`show` against a bare repo on
#    local disk is not network traffic, matching the "no network in tests"
#    rule the same way scripts/test_touches_gate.py's real-repo tests do.
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {repo}\n{r.stderr}")
    return r.stdout.strip()


class _FakeOrigin:
    """A bare 'origin' repo + a 'work' clone (what branch_poller polls from)
    + a 'remote_worker' clone (what a remote spawn's git push simulates)."""

    def __init__(self, tmp: Path):
        self.origin = tmp / "origin.git"
        self.work = tmp / "work"
        self.remote_worker = tmp / "remote_worker"

        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)],
                       check=True, capture_output=True)

        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.work)],
                       check=True, capture_output=True)
        _git(self.work, "config", "user.email", "t@test")
        _git(self.work, "config", "user.name", "test")
        (self.work / "README.md").write_text("base\n")
        _git(self.work, "add", "README.md")
        _git(self.work, "commit", "-q", "-m", "C0 base")
        _git(self.work, "push", "-q", "origin", "main")

        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.remote_worker)],
                       check=True, capture_output=True)
        _git(self.remote_worker, "config", "user.email", "worker@test")
        _git(self.remote_worker, "config", "user.name", "worker")

    def push_branch(self, branch: str, files: dict[str, str], *,
                    committer_date: str | None = None) -> None:
        """Simulate the remote worker: new branch, write `files`, commit,
        push — exactly what a real winbox worker's REPORT.md/BLOCKER.md
        push produces on the branch_poller side.

        `committer_date` (e.g. "<unix-epoch> +0000") backdates the commit
        via GIT_AUTHOR_DATE/GIT_COMMITTER_DATE — used to simulate an "old,
        quiet" branch for the GAP 2 review-close tests without a real
        multi-minute sleep in the test."""
        _git(self.remote_worker, "checkout", "-q", "-b", branch)
        for name, content in files.items():
            (self.remote_worker / name).write_text(content)
        _git(self.remote_worker, "add", "-A")
        env = None
        if committer_date is not None:
            import os
            env = {**os.environ, "GIT_AUTHOR_DATE": committer_date,
                   "GIT_COMMITTER_DATE": committer_date}
        r = subprocess.run(["git", "commit", "-q", "-m", f"push {branch}"],
                           cwd=str(self.remote_worker), capture_output=True,
                           text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"git commit in {self.remote_worker}\n{r.stderr}")
        _git(self.remote_worker, "push", "-q", "origin", branch)
        _git(self.remote_worker, "checkout", "-q", "main")


@pytest.fixture()
def fake_origin():
    with tempfile.TemporaryDirectory() as td:
        yield _FakeOrigin(Path(td))


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    # owner_cto="test-owner" below is synthetic with no c_level_sessions row —
    # this suite tests host/cap routing, not the charter gate, so skip it.
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


def _insert_remote_task(db_mod_, *, task_id: str, branch: str, host: str,
                        project: str, pid: int | None) -> None:
    with db_mod_.get_conn() as conn:
        ts = db_mod_.now_iso()
        conn.execute(
            """INSERT INTO tasks
               (id, project, role, status, title, description,
                touches, depends_on, branch, host, pid,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, project, "developer", "in_progress", "t", "d",
             json.dumps([]), "[]", branch, host, pid, ts, ts),
        )
        conn.commit()


def test_remote_branch_exists_false_then_true(fake_origin):
    branch = "agent/developer-task-poll01"
    assert poller.remote_branch_exists(str(fake_origin.work), branch) is False
    fake_origin.push_branch(branch, {"REPORT.md": "## Summary\nok\n"})
    assert poller.remote_branch_exists(str(fake_origin.work), branch) is True


def test_check_task_report_flips_to_review(fake_origin, temp_db, monkeypatch):
    branch = "agent/developer-task-poll02"
    fake_origin.push_branch(branch, {
        "REPORT.md": "# REPORT task-poll02\n## Summary\nAppended one line.\n## Files Changed\n- docs/hosts-smoke.md\n",
    })
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    _insert_remote_task(temp_db, task_id="task-poll02", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll02"))

    t = temp_db.get_task("task-poll02")
    assert t["status"] == "review"
    assert "Appended one line" in t["report"]


def test_check_task_blocker_flips_to_blocked_human(fake_origin, temp_db, monkeypatch):
    branch = "agent/developer-task-poll03"
    fake_origin.push_branch(branch, {"BLOCKER.md": "# BLOCKER task-poll03\nmissing credentials\nneed API key\n"})
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    monkeypatch.setattr(poller, "open_blocker_issue",
                        lambda task_id, title, body: "https://github.com/x/y/issues/1")
    _insert_remote_task(temp_db, task_id="task-poll03", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll03"))

    t = temp_db.get_task("task-poll03")
    assert t["status"] == "blocked_human"
    assert "missing credentials" in t["delegate_log"]
    assert "issues/1" in t["delegate_log"]


def test_check_task_dead_pid_no_branch_fails(fake_origin, temp_db, monkeypatch):
    branch = "agent/developer-task-poll04"  # never pushed
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    monkeypatch.setattr(poller, "remote_pid_alive", lambda host_cfg, pid: False)
    _insert_remote_task(temp_db, task_id="task-poll04", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll04"))

    t = temp_db.get_task("task-poll04")
    assert t["status"] == "failed"
    assert "died before pushing" in t["delegate_log"]


def test_check_task_unreachable_host_does_not_fail_task(fake_origin, temp_db, monkeypatch):
    """None (host unreachable) must never collapse into False (dead) —
    a Wi-Fi blip must not fail a task that is still running fine."""
    branch = "agent/developer-task-poll05"  # never pushed
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    monkeypatch.setattr(poller, "remote_pid_alive", lambda host_cfg, pid: None)
    _insert_remote_task(temp_db, task_id="task-poll05", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll05"))

    t = temp_db.get_task("task-poll05")
    assert t["status"] == "in_progress"


def test_check_task_still_working_no_state_change(fake_origin, temp_db, monkeypatch):
    """Branch exists but neither REPORT.md nor BLOCKER.md landed yet."""
    branch = "agent/developer-task-poll06"
    fake_origin.push_branch(branch, {"WIP.txt": "still going\n"})
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    _insert_remote_task(temp_db, task_id="task-poll06", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll06"))

    t = temp_db.get_task("task-poll06")
    assert t["status"] == "in_progress"


# ---------------------------------------------------------------------------
# 5. GAP 2 (task-59780ac3): closing a remote worker's surface right after
#    its task flips to review, but only once the branch has gone quiet —
#    never under a worker that might still be pushing.
# ---------------------------------------------------------------------------

def test_check_task_review_close_skips_fresh_commit(fake_origin, temp_db, monkeypatch):
    """REPORT.md just landed (commit is <5 min old, the real case every
    time) — must NOT close the remote worker yet; it could still be
    mid-push. The task still flips to review either way."""
    branch = "agent/developer-task-poll08"
    fake_origin.push_branch(branch, {"REPORT.md": "# REPORT task-poll08\n## Summary\nok\n"})
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    fake_close_remote = mock.Mock()
    monkeypatch.setattr(poller, "close_remote", fake_close_remote)
    _insert_remote_task(temp_db, task_id="task-poll08", branch=branch,
                        host="winbox", project="fake-proj", pid=4242)

    poller.check_task(temp_db.get_task("task-poll08"))

    assert temp_db.get_task("task-poll08")["status"] == "review"
    assert fake_close_remote.call_count == 0


def test_check_task_review_close_fires_on_old_commit(fake_origin, temp_db, monkeypatch):
    """Same setup, but the branch's newest commit is backdated >5 min —
    proof the worker has stopped pushing. close_remote must be called with
    allow_review=True (no other caller in the codebase passes that)."""
    branch = "agent/developer-task-poll09"
    old_epoch = int(time.time()) - 600
    fake_origin.push_branch(branch, {"REPORT.md": "# REPORT task-poll09\n## Summary\nok\n"},
                            committer_date=f"{old_epoch} +0000")
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    fake_close_remote = mock.Mock(return_value={"ssh_ok": True, "refused": None})
    monkeypatch.setattr(poller, "close_remote", fake_close_remote)
    _insert_remote_task(temp_db, task_id="task-poll09", branch=branch,
                        host="winbox", project="fake-proj", pid=4242)

    poller.check_task(temp_db.get_task("task-poll09"))

    assert temp_db.get_task("task-poll09")["status"] == "review"
    assert fake_close_remote.call_count == 1
    assert fake_close_remote.call_args.kwargs.get("allow_review") is True


def test_check_task_review_close_local_task_unaffected(fake_origin, temp_db, monkeypatch):
    """A LOCAL (mac) task must be unaffected by GAP 2's new review-close
    path — check_task returns before ever looking at branch/project for a
    mac/hostless task (see test_check_task_skips_mac_and_hostless_tasks),
    so close_remote must never even be consulted."""
    fake_close_remote = mock.Mock()
    monkeypatch.setattr(poller, "close_remote", fake_close_remote)
    monkeypatch.setattr(config, "get_project",
                        lambda key: (_ for _ in ()).throw(
                            AssertionError("must not look up project for a mac task")))
    _insert_remote_task(temp_db, task_id="task-poll10", branch="agent/developer-task-poll10",
                        host="mac", project="fake-proj", pid=4242)

    poller.check_task(temp_db.get_task("task-poll10"))

    assert temp_db.get_task("task-poll10")["status"] == "in_progress"
    assert fake_close_remote.call_count == 0


def test_check_task_skips_mac_and_hostless_tasks(fake_origin, temp_db, monkeypatch):
    monkeypatch.setattr(config, "get_project",
                        lambda key: (_ for _ in ()).throw(
                            AssertionError("must not look up project for a mac/hostless task")))
    _insert_remote_task(temp_db, task_id="task-poll07a", branch="agent/developer-task-poll07a",
                        host="mac", project="fake-proj", pid=1)
    _insert_remote_task(temp_db, task_id="task-poll07b", branch="agent/developer-task-poll07b",
                        host=None, project="fake-proj", pid=1)

    poller.check_task(temp_db.get_task("task-poll07a"))
    poller.check_task(temp_db.get_task("task-poll07b"))

    assert temp_db.get_task("task-poll07a")["status"] == "in_progress"
    assert temp_db.get_task("task-poll07b")["status"] == "in_progress"


# ---------------------------------------------------------------------------
# 6. GH #151: REPORT.md/BLOCKER.md header must name the exact task id being
#    polled — a mismatched or missing header must never flip status.
# ---------------------------------------------------------------------------

def test_check_task_report_wrong_header_refuses_flip(fake_origin, temp_db, monkeypatch):
    """A REPORT.md naming a DIFFERENT task's id (task-424077a4 inheriting a
    stray Higgsfield report, the real incident behind GH #151) must never
    flip this task to review."""
    branch = "agent/developer-task-poll11"
    fake_origin.push_branch(branch, {
        "REPORT.md": "# REPORT task-somebody-elses-task\n## Summary\nTV-wall plates\n",
    })
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    _insert_remote_task(temp_db, task_id="task-poll11", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll11"))

    t = temp_db.get_task("task-poll11")
    assert t["status"] == "in_progress"
    assert "header mismatch" in t["delegate_log"]
    assert "task-somebody-elses-task" in t["delegate_log"]


def test_check_task_report_no_header_refuses_flip(fake_origin, temp_db, monkeypatch):
    """A REPORT.md with no header at all (pre-2026-09-17 shape) must also be
    refused — no grandfather clause."""
    branch = "agent/developer-task-poll12"
    fake_origin.push_branch(branch, {"REPORT.md": "## Summary\nok, no header\n"})
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    _insert_remote_task(temp_db, task_id="task-poll12", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll12"))

    t = temp_db.get_task("task-poll12")
    assert t["status"] == "in_progress"
    assert "no header" in t["delegate_log"]


def test_check_task_blocker_wrong_header_refuses_flip(fake_origin, temp_db, monkeypatch):
    branch = "agent/developer-task-poll13"
    fake_origin.push_branch(branch, {
        "BLOCKER.md": "# BLOCKER task-wrong-one\nneed a password\n",
    })
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    fake_open_issue = mock.Mock()
    monkeypatch.setattr(poller, "open_blocker_issue", fake_open_issue)
    _insert_remote_task(temp_db, task_id="task-poll13", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll13"))

    t = temp_db.get_task("task-poll13")
    assert t["status"] == "in_progress"
    assert "header mismatch" in t["delegate_log"]
    assert fake_open_issue.call_count == 0


def test_check_task_blocker_no_header_refuses_flip(fake_origin, temp_db, monkeypatch):
    branch = "agent/developer-task-poll14"
    fake_origin.push_branch(branch, {"BLOCKER.md": "need a password\n"})
    monkeypatch.setattr(poller, "get_project",
                        lambda key: {"path": str(fake_origin.work)})
    fake_open_issue = mock.Mock()
    monkeypatch.setattr(poller, "open_blocker_issue", fake_open_issue)
    _insert_remote_task(temp_db, task_id="task-poll14", branch=branch,
                        host="winbox", project="fake-proj", pid=999)

    poller.check_task(temp_db.get_task("task-poll14"))

    t = temp_db.get_task("task-poll14")
    assert t["status"] == "in_progress"
    assert "no header" in t["delegate_log"]
    assert fake_open_issue.call_count == 0


def test_header_task_id_accepts_matching_report_header():
    assert poller._header_task_id("# REPORT task-abc123\n## Summary\n", "REPORT") == "task-abc123"


def test_header_task_id_none_on_wrong_kind():
    # A BLOCKER-shaped header must not match when checking for REPORT.
    assert poller._header_task_id("# BLOCKER task-abc123\n", "REPORT") is None


def test_tick_only_polls_remote_in_progress_tasks(fake_origin, temp_db, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(poller, "check_task", lambda t: calls.append(t["id"]))
    _insert_remote_task(temp_db, task_id="task-tick01", branch="b1", host="winbox",
                        project="p", pid=1)
    _insert_remote_task(temp_db, task_id="task-tick02", branch="b2", host="mac",
                        project="p", pid=1)
    with temp_db.get_conn() as conn:
        conn.execute("UPDATE tasks SET status='review' WHERE id='task-tick01'")
        conn.commit()
    _insert_remote_task(temp_db, task_id="task-tick03", branch="b3", host="contabo",
                        project="p", pid=1)

    n = poller.tick()

    assert calls == ["task-tick03"]
    assert n == 1
