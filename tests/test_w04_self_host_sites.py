"""Org Mesh W0.4 (task-1af90170): "local or remote?" is answered by self_host(), not by "mac".

Sites covered, each under self_host()=="mac" (old behaviour, must not change) and
self_host()=="contabo" (NULL/empty host and host=="contabo" are local, host=="mac" is remote):

  runners/watchdog.py      scan_once, sweep_terminal_surfaces (+ the darwin-only guards)
  runners/branch_poller.py tick, check_task, _maybe_close_finished_remote_worker
  tools/gc_stale_tasks.py  _alive_for_gc and the "spawned pending" report text
  tools/work_watch.py      _pid_dead_in_progress
  tools/worker_reap.py     close_remote
  tools/send_to_worker.py  send

Plus the branch poller reading `docs/reports/<task-id>/{REPORT,BLOCKER}.md` before the root
copy, and the Contabo systemd unit.

No real tasks.db, no ssh, no network: sqlite lives in tmp_path, git runs against throwaway
bare repos, and every process/tab/ssh call is stubbed.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
import lib.db as db_mod  # noqa: E402
import lib.mailbox as mailbox  # noqa: E402
import runners.branch_poller as poller  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
import tools.gc_stale_tasks as gc  # noqa: E402
import tools.send_to_worker as sd  # noqa: E402
import tools.work_watch as work_watch  # noqa: E402
import tools.worker_reap as reap  # noqa: E402

# (self_host, hosts that are local there, hosts that are remote there)
CASES = [
    pytest.param("mac", [None, "", "mac"], ["contabo", "winbox"], id="self=mac"),
    pytest.param("contabo", [None, "", "contabo"], ["mac", "winbox"], id="self=contabo"),
]


@pytest.fixture
def host_is(monkeypatch, pinned_mac_host):
    """host_is("mac"|"contabo") makes self_host() answer that, from the real resolver.

    Starts from pinned_mac_host (every source pinned to the Mac); "contabo" is then chosen
    through ORG_HOST, the first source, so no test depends on the box that runs it.
    """
    def _set(name: str) -> None:
        if name == "mac":
            monkeypatch.delenv("ORG_HOST", raising=False)
        else:
            monkeypatch.setenv("ORG_HOST", name)
        config.self_host.cache_clear()
        assert config.self_host() == name

    yield _set
    config.self_host.cache_clear()


def _iso(minutes_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return db_mod


def _insert_task(conn_db, *, task_id: str, status: str = "in_progress", host=None,
                 branch: str | None = None, pid: int | None = None,
                 project: str = "fake-proj", role: str = "developer",
                 assigned_agent: str | None = None, spawned_at: str | None = None,
                 worktree: str | None = None) -> str:
    with conn_db.get_conn() as conn:
        ts = conn_db.now_iso()
        conn.execute(
            """INSERT INTO tasks
               (id, project, role, status, title, description, touches, depends_on,
                branch, host, pid, assigned_agent, spawned_at, worktree,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, project, role, status, "t", "d", "[]", "[]", branch, host, pid,
             assigned_agent, spawned_at, worktree, ts, ts),
        )
        conn.commit()
    return task_id


# ---------------------------------------------------------------------------
# runners/watchdog.py
# ---------------------------------------------------------------------------

def _stub_scan(monkeypatch, rows_by_status: dict[str, list[dict]]) -> None:
    """scan_once with every pass but the ones under test stubbed out."""
    monkeypatch.setattr(watchdog.db, "list_tasks",
                        lambda status=None, limit=0: list(rows_by_status.get(status, [])))
    monkeypatch.setattr(watchdog, "gc_stale_tasks", lambda: [])
    monkeypatch.setattr(watchdog, "sweep_terminal_surfaces", lambda: [])
    monkeypatch.setattr(watchdog, "_drain_disk_queue", lambda: None)
    monkeypatch.setattr(watchdog.work_watch, "watch",
                        lambda: {"alerted": [], "lungnote_filed": [], "green": []})
    monkeypatch.delenv("ORG_WATCHDOG_BRANCH_POLL", raising=False)


@pytest.mark.parametrize("this,local,remote", CASES)
def test_scan_once_sends_only_other_hosts_to_the_remote_check(
        this, local, remote, host_is, monkeypatch):
    host_is(this)
    rows = [{"id": f"task-{i:04d}", "host": h, "status": "in_progress",
             "updated_at": _iso(1), "pid": None}
            for i, h in enumerate(local + remote)]
    _stub_scan(monkeypatch, {"in_progress": rows})
    seen = []
    monkeypatch.setattr(watchdog, "_check_remote_stall",
                        lambda t, host: seen.append((t["host"], host)))

    watchdog.scan_once()

    assert sorted(seen) == sorted((h, h) for h in remote)


@pytest.mark.parametrize("darwin", [True, False], ids=["darwin", "linux"])
def test_stall_closes_the_iterm_tab_only_on_darwin(darwin, host_is, monkeypatch):
    host_is("contabo")
    row = {"id": "task-stall001", "host": None, "status": "in_progress",
           "updated_at": _iso(40), "pid": 4242, "review": None}
    _stub_scan(monkeypatch, {"in_progress": [row]})
    closed, statuses = [], []
    monkeypatch.setattr(watchdog, "_mac_surfaces", lambda: darwin)
    monkeypatch.setattr(watchdog, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(watchdog, "_close_tab", lambda tid: closed.append(tid) or True)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "issue-url")
    monkeypatch.setattr(watchdog, "_cleanup_tmux_ttyd",
                        lambda t: {"tmux_killed": True, "ttyd_killed": False})
    monkeypatch.setattr(watchdog.db, "update_status",
                        lambda tid, status, **kw: statuses.append((tid, status)))

    out = watchdog.scan_once()

    assert statuses == [("task-stall001", "stalled")]
    assert closed == (["task-stall001"] if darwin else [])
    assert out["stalled"][0]["tab_closed"] is darwin


@pytest.mark.parametrize("darwin", [True, False], ids=["darwin", "linux"])
def test_finished_dev_reap_pass_runs_only_on_darwin(darwin, host_is, monkeypatch):
    host_is("contabo")
    row = {"id": "task-fin00001", "host": None, "status": "review",
           "updated_at": _iso(120), "pid": 77}
    _stub_scan(monkeypatch, {"review": [row]})
    closes = []
    monkeypatch.setattr(watchdog, "_mac_surfaces", lambda: darwin)
    monkeypatch.setattr(watchdog, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(watchdog, "close_dev",
                        lambda tid, reason: closes.append(tid) or {})

    out = watchdog.scan_once()

    assert closes == (["task-fin00001"] if darwin else [])
    assert len(out["reaped"]) == (1 if darwin else 0)


def test_mac_surfaces_follows_sys_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert watchdog._mac_surfaces() is True
    monkeypatch.setattr(sys, "platform", "linux")
    assert watchdog._mac_surfaces() is False


@pytest.mark.parametrize("darwin", [True, False], ids=["darwin", "linux"])
@pytest.mark.parametrize("this,local,remote", CASES)
def test_terminal_sweep_local_half_is_darwin_only_remote_half_is_not(
        this, local, remote, darwin, host_is, monkeypatch):
    host_is(this)
    status = watchdog.TERMINAL_SURFACE_STATUSES[0]
    rows = [{"id": f"task-{i:04d}", "host": h, "status": status,
             "updated_at": _iso(60), "pid": 99}
            for i, h in enumerate(local + remote)]
    monkeypatch.setattr(watchdog.db, "list_tasks",
                        lambda status=None, limit=0: list(rows)
                        if status == watchdog.TERMINAL_SURFACE_STATUSES[0] else [])
    monkeypatch.setattr(watchdog, "_mac_surfaces", lambda: darwin)
    monkeypatch.setattr("scripts.browser.tab_registry.all_claims", lambda: {})
    monkeypatch.setattr(watchdog, "_log_unclaimed_org_tabs", lambda claimed: None)
    monkeypatch.setattr(watchdog, "_live_tmux_sessions", lambda: set())
    monkeypatch.setattr(watchdog, "_live_task_tab_ids", lambda: set())
    monkeypatch.setattr(watchdog, "_pid_alive", lambda pid: True)
    remote_seen, local_closed = [], []
    monkeypatch.setattr(watchdog, "_sweep_remote_terminal_task",
                        lambda t, host: remote_seen.append(host))
    monkeypatch.setattr(watchdog, "close_dev",
                        lambda tid, reason: local_closed.append(tid) or {})

    watchdog.sweep_terminal_surfaces()

    assert sorted(remote_seen) == sorted(remote)
    local_ids = [r["id"] for r in rows if r["host"] in local]
    assert sorted(local_closed) == (sorted(local_ids) if darwin else [])


# ---------------------------------------------------------------------------
# tools/gc_stale_tasks.py, tools/work_watch.py
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("this,local,remote", CASES)
def test_gc_liveness_is_local_only_for_this_host(this, local, remote, host_is, monkeypatch):
    host_is(this)
    monkeypatch.setattr(gc, "_pid_alive", lambda pid: "local-check")
    monkeypatch.setattr(gc, "get_host", lambda name: {"ssh": name})
    monkeypatch.setattr(gc, "remote_pid_alive", lambda cfg, pid: ("remote-check", cfg["ssh"]))

    for h in local:
        assert gc._alive_for_gc({"host": h, "pid": 5}) == "local-check", h
    for h in remote:
        assert gc._alive_for_gc({"host": h, "pid": 5}) == ("remote-check", h), h


@pytest.mark.parametrize("this", ["mac", "contabo"])
def test_gc_spawned_pending_report_names_this_host_for_a_null_host_row(
        this, host_is, temp_db, monkeypatch):
    host_is(this)
    old = (datetime.now(timezone.utc) - timedelta(minutes=300)).isoformat(timespec="seconds")
    _insert_task(temp_db, task_id="task-gcpend01", status="pending", host=None,
                 assigned_agent="dev", spawned_at=old)
    monkeypatch.setattr(gc, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(gc, "_reclaim_worktree", lambda t, dry_run=False: {})

    gc.gc_stale_tasks()

    task = temp_db.get_task("task-gcpend01")
    assert task["status"] == "cancelled"
    assert f"host={this})" in task["report"]


@pytest.mark.parametrize("this,local,remote", CASES)
def test_work_watch_dead_pid_check_is_local_only_for_this_host(
        this, local, remote, host_is, monkeypatch):
    host_is(this)
    monkeypatch.setattr(work_watch, "_pid_alive", lambda pid: False)   # local: dead
    monkeypatch.setattr(work_watch, "_alive_for_gc", lambda t: True)   # remote: alive

    for h in local:
        assert work_watch._pid_dead_in_progress({"host": h, "pid": 5}) is True, h
    for h in remote:
        assert work_watch._pid_dead_in_progress({"host": h, "pid": 5}) is False, h
    assert work_watch._pid_dead_in_progress({"host": None, "pid": None}) is False


# ---------------------------------------------------------------------------
# tools/worker_reap.py close_remote
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("this,local,remote", CASES)
def test_close_remote_refuses_this_host_and_treats_the_rest_as_remote(
        this, local, remote, host_is, monkeypatch):
    host_is(this)
    ssh_calls = []
    monkeypatch.setattr(reap.subprocess, "run",
                        lambda cmd, **kw: ssh_calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""))

    for h in local:
        r = reap.close_remote({"host": h, "status": "failed"}, reason="t")
        assert "not a remote spoke" in (r["refused"] or ""), h
    assert ssh_calls == []
    for h in remote:
        r = reap.close_remote({"host": h, "status": "failed"}, reason="t")
        assert "not a remote spoke" not in (r["refused"] or ""), h


# ---------------------------------------------------------------------------
# tools/send_to_worker.py send
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("this,local,remote", CASES)
def test_send_delivers_locally_only_for_this_host(
        this, local, remote, host_is, temp_db, tmp_path, monkeypatch):
    host_is(this)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(sd, "_attempt_wake", lambda session, label: None)
    monkeypatch.setattr(sd, "_send_remote", lambda task, message, **kw: "REMOTE")

    for i, h in enumerate(local):
        tid = _insert_task(temp_db, task_id=f"task-loc{i:05d}", host=h)
        assert sd.send(tid, "hi").startswith("queued to"), h
    for i, h in enumerate(remote):
        tid = _insert_task(temp_db, task_id=f"task-rem{i:05d}", host=h)
        assert sd.send(tid, "hi") == "REMOTE", h


# ---------------------------------------------------------------------------
# runners/branch_poller.py: host classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("this,local,remote", CASES)
def test_tick_polls_only_tasks_on_other_hosts(this, local, remote, host_is, monkeypatch):
    host_is(this)
    rows = [{"id": f"task-{i:04d}", "host": h} for i, h in enumerate(local + remote)]
    monkeypatch.setattr(poller.db, "list_tasks", lambda status=None, limit=0: list(rows))
    polled = []
    monkeypatch.setattr(poller, "check_task", lambda t: polled.append(t["host"]))

    n = poller.tick()

    assert sorted(polled) == sorted(remote)
    assert n == len(remote)


@pytest.mark.parametrize("this,local,remote", CASES)
def test_check_task_skips_this_host_before_touching_git(this, local, remote, host_is, monkeypatch):
    host_is(this)
    resolved = []
    monkeypatch.setattr(poller, "get_project",
                        lambda key: resolved.append(key) or (_ for _ in ()).throw(ValueError("stop")))

    for h in [x for x in local if x]:
        poller.check_task({"id": "task-x", "branch": "b", "host": h, "project": "p"})
    assert resolved == []
    poller.check_task({"id": "task-x", "branch": "b", "host": remote[0], "project": "p"})
    assert resolved == ["p"]


# ---------------------------------------------------------------------------
# runners/branch_poller.py: docs/reports/<task-id>/ before the root copy
# ---------------------------------------------------------------------------

def _git(cwd: Path, *args: str, env: dict | None = None) -> str:
    r = subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                       cwd=str(cwd), capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {cwd}\n{r.stderr}")
    return r.stdout.strip()


class _Origin:
    """A bare origin, a clone the poller polls from, and a clone a remote worker pushes from."""

    def __init__(self, tmp: Path):
        self.origin = tmp / "origin.git"
        self.work = tmp / "work"
        self.worker = tmp / "worker"
        _git(tmp, "init", "-q", "--bare", "--initial-branch=main", str(self.origin))
        _git(tmp, "clone", "-q", str(self.origin), str(self.work))
        (self.work / "README.md").write_text("base\n")
        _git(self.work, "add", "-A")
        _git(self.work, "commit", "-q", "-m", "base")
        _git(self.work, "push", "-q", "origin", "main")
        _git(tmp, "clone", "-q", str(self.origin), str(self.worker))

    def push_branch(self, branch: str, files: dict[str, str], *,
                    committer_date: str | None = None) -> None:
        _git(self.worker, "checkout", "-q", "-b", branch)
        for rel, text in files.items():
            p = self.worker / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        _git(self.worker, "add", "-A")
        env = None
        if committer_date:
            env = {**os.environ, "GIT_AUTHOR_DATE": committer_date,
                   "GIT_COMMITTER_DATE": committer_date}
        _git(self.worker, "commit", "-q", "-m", f"push {branch}", env=env)
        _git(self.worker, "push", "-q", "origin", branch)
        _git(self.worker, "checkout", "-q", "main")


@pytest.fixture
def origin(tmp_path):
    return _Origin(tmp_path)


@pytest.fixture
def polled(origin, temp_db, monkeypatch):
    """poll(task_id, files) pushes a branch and runs one check_task; returns the task row."""
    monkeypatch.setattr(poller, "get_project", lambda key: {"path": str(origin.work)})
    monkeypatch.setattr(poller, "open_blocker_issue", lambda tid, title, body: "https://x/issues/1")
    closes = []
    monkeypatch.setattr(poller, "close_remote",
                        lambda task, **kw: closes.append((task["id"], kw)) or {})

    def poll(task_id: str, files: dict[str, str], **push_kw) -> dict:
        branch = f"agent/developer-{task_id}"
        origin.push_branch(branch, files, **push_kw)
        _insert_task(temp_db, task_id=task_id, host="winbox", branch=branch, pid=999)
        poller.check_task(temp_db.get_task(task_id))
        return temp_db.get_task(task_id)

    poll.closes = closes
    return poll


@pytest.fixture(params=["mac", "contabo"])
def poller_on(request, host_is):
    host_is(request.param)
    return request.param


def test_docs_path_report_flips_to_review(poller_on, polled):
    t = polled("task-doc00001", {
        "docs/reports/task-doc00001/REPORT.md": "# REPORT task-doc00001\n## Summary\nfrom docs\n"})
    assert t["status"] == "review"
    assert "from docs" in t["report"]


def test_root_path_report_still_flips_to_review(poller_on, polled):
    t = polled("task-root0001", {"REPORT.md": "# REPORT task-root0001\n## Summary\nfrom root\n"})
    assert t["status"] == "review"
    assert "from root" in t["report"]


def test_docs_path_report_with_wrong_header_is_refused(poller_on, polled):
    t = polled("task-bad00001", {
        "docs/reports/task-bad00001/REPORT.md": "# REPORT task-someoneelse\n## Summary\nnope\n"})
    assert t["status"] == "in_progress"
    assert "REPORT.md header mismatch" in t["delegate_log"]
    assert "task-someoneelse" in t["delegate_log"]


def test_docs_path_report_with_no_header_is_refused(poller_on, polled):
    t = polled("task-nohd0001", {"docs/reports/task-nohd0001/REPORT.md": "## Summary\nno header\n"})
    assert t["status"] == "in_progress"
    assert "no header" in t["delegate_log"]


def test_docs_path_wins_outright_over_a_root_report(poller_on, polled):
    """A bad docs-path file is not papered over by a root file that happens to be right."""
    t = polled("task-both0001", {
        "docs/reports/task-both0001/REPORT.md": "# REPORT task-other\nwrong\n",
        "REPORT.md": "# REPORT task-both0001\n## Summary\nroot is fine\n"})
    assert t["status"] == "in_progress"
    assert "header mismatch" in t["delegate_log"]


def test_good_docs_path_report_beats_a_stale_root_report(poller_on, polled):
    t = polled("task-both0002", {
        "docs/reports/task-both0002/REPORT.md": "# REPORT task-both0002\n## Summary\ndocs wins\n",
        "REPORT.md": "# REPORT task-stale\nold root report\n"})
    assert t["status"] == "review"
    assert "docs wins" in t["report"]


def test_another_tasks_docs_report_is_not_read(poller_on, polled):
    t = polled("task-mine0001", {
        "docs/reports/task-theirs01/REPORT.md": "# REPORT task-theirs01\n## Summary\nnot mine\n"})
    assert t["status"] == "in_progress"
    assert t["delegate_log"] in (None, "")


def test_docs_path_blocker_flips_to_blocked_human(poller_on, polled):
    t = polled("task-blk00001", {
        "docs/reports/task-blk00001/BLOCKER.md": "# BLOCKER task-blk00001\nneed a key\nmore\n"})
    assert t["status"] == "blocked_human"
    assert "need a key" in t["delegate_log"]


def test_docs_path_blocker_with_wrong_header_is_refused(poller_on, polled):
    t = polled("task-blk00002", {
        "docs/reports/task-blk00002/BLOCKER.md": "# BLOCKER task-other\nneed a key\n"})
    assert t["status"] == "in_progress"
    assert "BLOCKER.md header mismatch" in t["delegate_log"]


def test_docs_path_report_triggers_the_review_close_of_a_quiet_worker(poller_on, polled):
    t = polled("task-quiet001", {
        "docs/reports/task-quiet001/REPORT.md": "# REPORT task-quiet001\n## Summary\nok\n"},
        committer_date="1700000000 +0000")
    assert t["status"] == "review"
    assert [c[0] for c in polled.closes] == ["task-quiet001"]
    assert polled.closes[0][1].get("allow_review") is True


# ---------------------------------------------------------------------------
# deploy/systemd/mooniex-watchdog.service
# ---------------------------------------------------------------------------

def test_watchdog_unit_is_a_contabo_loop_service_with_no_secret_and_no_poller():
    text = (ROOT / "deploy" / "systemd" / "mooniex-watchdog.service").read_text()
    live = [ln.strip() for ln in text.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]
    assert "Environment=ORG_HOST=contabo" in live
    assert "WorkingDirectory=/opt/MoonieXHQ/Agents/Core" in live
    assert ("ExecStart=/opt/MoonieXHQ/Agents/Core/.venv/bin/python "
            "-m runners.watchdog --loop") in live
    assert "Restart=always" in live
    assert not any("ORG_WATCHDOG_BRANCH_POLL" in ln for ln in live)
    assert not any(k in ln.upper() for ln in live for k in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))
    assert not any(ln.startswith("EnvironmentFile") for ln in live)
