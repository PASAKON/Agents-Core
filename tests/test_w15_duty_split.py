"""Org Mesh W1.5 (task-a137ecca): on a shared ledger every watchdog duty has exactly one owner per row.

LOCAL duty  -> acts only on rows THIS box runs          (row host == self)
REMOTE duty -> acts only on rows THIS box dispatched that run elsewhere
               (host != self AND dispatcher_host == self)
A row where neither holds is skipped: never cancelled, never stalled, never marked dead.

One fake ledger holds every (host, dispatcher_host, runner) combination over
{mac, contabo, winbox, NULL} x {claude, codex, agy} (48 rows per status). Every duty is
driven through its real entry point, once with self_host() pinned to "mac" and once to
"contabo"; only the process/ssh/tmux/git edges are stubbed. The result of a pass is the set
of rows the duty acted on, compared against a small reference model of the rules (`_owner`)
that shares no code with the implementation.

  local:   local_stall, finished_reap, terminal_local, work_watch, gc1, gc1b_local, gc3_local
  remote:  remote_stall, terminal_remote, close_remote, gc1b_remote, gc3_remote
  dispatcher-only (a status flip, no local resource): blocked_human, gc2
  poller / launcher_close: see `_owner`

NULL semantics (asserted by `test_null_host_and_dispatcher_behave_as_self`): dispatcher NULL is
this box. Host NULL is "not spawned yet", so the row belongs to its dispatcher (NULL too: this
box). That last clause is the one refinement of "NULL host means self": read literally, an
unspawned row dispatched by the OTHER box would be local on both boxes.

No real tasks.db, ssh, tmux, osascript or git: sqlite lives in tmp_path, everything else is a stub.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
import lib.db as db_mod  # noqa: E402
import runners.branch_poller as poller  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
import tools.gc_stale_tasks as gc  # noqa: E402
import tools.session_reconcile as session_reconcile  # noqa: E402
import tools.work_watch as work_watch  # noqa: E402
import tools.worker_reap as reap  # noqa: E402

BOXES = ("mac", "contabo")
HOSTS = ("mac", "contabo", "winbox", None)
RUNNERS = ("claude", "codex", "agy")
EXTERNAL = ("codex", "agy")
ALL_KEYS = [(h, d, r) for h in HOSTS for d in HOSTS for r in RUNNERS]
EXPLICIT = [k for k in ALL_KEYS if k[0] is not None and k[1] is not None]

LOCAL_DUTIES = ("local_stall", "finished_reap", "terminal_local", "work_watch",
                "gc1", "gc1b_local", "gc3_local")
REMOTE_DUTIES = ("remote_stall", "terminal_remote", "close_remote",
                 "gc1b_remote", "gc3_remote")
DISPATCHER_DUTIES = ("blocked_human", "gc2")
ALL_DUTIES = (LOCAL_DUTIES + REMOTE_DUTIES + DISPATCHER_DUTIES
              + ("poller", "launcher_close"))


def _iso(minutes_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")


def _id(prefix: str, key: tuple) -> str:
    return f"task-{prefix}-{key[0] or 'null'}-{key[1] or 'null'}-{key[2]}"


def _key_of(task_id: str) -> tuple:
    _, _, h, d, r = task_id.split("-")
    return (None if h == "null" else h, None if d == "null" else d, r)


def _keys(ids) -> set:
    return {_key_of(i) for i in ids}


def _ledger(prefix: str, status: str, **extra) -> list[dict]:
    return [{"id": _id(prefix, k), "project": "fake-proj", "status": status,
             "host": k[0], "dispatcher_host": k[1], "runner": k[2],
             "branch": f"agent/{k[2]}", "pid": None, "updated_at": _iso(1), **extra}
            for k in ALL_KEYS]


def _owner(duty: str, key: tuple):
    """Reference model for an EXPLICIT (host, dispatcher_host, runner) row: the one box that
    should act, or None when no box that runs a watchdog here (mac/contabo) should."""
    h, d, r = key
    if duty in LOCAL_DUTIES:
        return h
    if duty in REMOTE_DUTIES:
        return d if d != h else None
    if duty in DISPATCHER_DUTIES:
        return d
    if duty == "poller":
        return d if (d != h or r in EXTERNAL) else None
    if duty == "launcher_close":
        return d if (d == h and r in EXTERNAL) else None
    raise AssertionError(duty)


# ---------------------------------------------------------------------------
# The passes: every duty through its real entry point, once per box
# ---------------------------------------------------------------------------

def _lister(by_status: dict):
    return lambda status=None, limit=0, **kw: list(by_status.get(status, []))


def _poller_duties(mp):
    by_status = {"in_progress": _ledger("p", "in_progress"), "review": _ledger("p", "review")}
    polled, closed = [], []
    mp.setattr(poller.db, "list_tasks", _lister(by_status))
    mp.setattr(poller, "check_task", lambda t: polled.append(t["id"]))
    mp.setattr(poller, "get_project", lambda key: {"path": "/nowhere", "default_branch": "main"})
    mp.setattr(poller, "_maybe_close_finished_local_launcher",
               lambda tid, repo, branch: closed.append(tid))
    poller.tick()
    return {"poller": _keys(polled), "launcher_close": _keys(closed)}


def _scan_duties(mp):
    by_status = {
        "in_progress": _ledger("s", "in_progress", updated_at=_iso(40), pid=4242, review=None),
        "blocked_human": _ledger("b", "blocked_human", updated_at=_iso(60 * 24 * 3), review=None),
        "review": _ledger("f", "review", updated_at=_iso(120), pid=77),
    }
    remote_stall, stalled, escalated, reaped = [], [], [], []

    def _update(task_id, status, **kw):
        review = json.loads(kw.get("review") or "{}")
        (escalated if review.get("from_status") == "blocked_human" else stalled).append(task_id)

    mp.setattr(watchdog.db, "list_tasks", _lister(by_status))
    mp.setattr(watchdog.db, "update_status", _update)
    mp.setattr(watchdog.db, "set_fields", lambda *a, **kw: None)
    mp.setattr(watchdog, "gc_stale_tasks", lambda: [])
    mp.setattr(watchdog, "sweep_terminal_surfaces", lambda: [])
    mp.setattr(watchdog, "_drain_disk_queue", lambda: None)
    mp.setattr(watchdog.work_watch, "watch",
               lambda: {"alerted": [], "lungnote_filed": [], "green": []})
    mp.setattr(watchdog, "_check_remote_stall", lambda t, host: remote_stall.append(t["id"]))
    mp.setattr(watchdog, "_mac_surfaces", lambda: True)
    mp.setattr(watchdog, "_pid_alive", lambda pid: pid == 77)   # stalled rows dead, finished rows alive
    mp.setattr(watchdog, "_close_tab", lambda tid: True)
    mp.setattr(watchdog, "_file_stalled_issue", lambda t, s: "issue")
    mp.setattr(watchdog, "_cleanup_tmux_ttyd", lambda t: {})
    mp.setattr(watchdog, "close_dev", lambda tid, reason: reaped.append(tid) or {})
    mp.delenv("ORG_WATCHDOG_BRANCH_POLL", raising=False)
    watchdog.scan_once()
    return {"local_stall": _keys(stalled), "remote_stall": _keys(remote_stall),
            "blocked_human": _keys(escalated), "finished_reap": _keys(reaped)}


def _terminal_duties(mp):
    status = watchdog.TERMINAL_SURFACE_STATUSES[0]
    rows = _ledger("t", status, updated_at=_iso(60), pid=99)
    local_closed, remote_seen = [], []
    mp.setattr(watchdog.db, "list_tasks", _lister({status: rows}))
    mp.setattr(watchdog, "SWEEP_CAP", 10_000)
    mp.setattr(watchdog, "_mac_surfaces", lambda: True)
    mp.setattr("scripts.browser.tab_registry.all_claims", lambda: {})
    mp.setattr(watchdog, "_log_unclaimed_org_tabs", lambda claimed: None)
    mp.setattr(watchdog, "_live_tmux_sessions", lambda: set())
    mp.setattr(watchdog, "_live_task_tab_ids", lambda: set())
    mp.setattr(watchdog, "_pid_alive", lambda pid: True)
    mp.setattr(watchdog, "_sweep_remote_terminal_task", lambda t, host: remote_seen.append(t["id"]))
    mp.setattr(watchdog, "close_dev", lambda tid, reason: local_closed.append(tid) or {})
    watchdog.sweep_terminal_surfaces()
    return {"terminal_local": _keys(local_closed), "terminal_remote": _keys(remote_seen)}


def _work_watch_duty(mp):
    mp.setattr(work_watch, "_pid_alive", lambda pid: False)
    rows = _ledger("w", "in_progress", pid=5)
    return {"work_watch": _keys(r["id"] for r in rows if work_watch._pid_dead_in_progress(r))}


def _close_remote_duty(mp, tmp_path):
    mp.setattr(reap, "_remote_hosts",
               lambda: {n: {"ssh": n, "os": "windows"} for n in ("mac", "contabo", "winbox")})
    mp.setattr(reap, "remote_pid_matches_task", lambda spec, pid, task_id: True)
    mp.setattr(reap.subprocess, "run", lambda cmd, **kw: SimpleNamespace(returncode=0, stderr=""))
    acted = [r["id"] for r in _ledger("c", "cancelled", pid=5)
             if reap.close_remote(r)["command"] is not None]
    return {"close_remote": _keys(acted)}


def _gc_duties(mp, tmp_path, variant: str):
    """`variant` picks which liveness answer lets gc act: "local" = the local pid is dead (the
    remote probe says alive), "remote" = the reverse. So each variant sees only the rows whose
    liveness question went to that probe."""
    old = _iso(600)
    with db_mod.get_conn() as conn:
        for prefix, status, extra in (
                ("g1", "pending", {}),
                ("g1b", "pending", {"assigned_agent": "dev"}),
                ("g2", "conflict", {}),
                ("g3", "rate_limited", {"retry_after_ts": old})):
            for r in _ledger(prefix, status):
                conn.execute(
                    """INSERT INTO tasks (id, project, role, status, title, description, touches,
                       depends_on, host, dispatcher_host, runner, pid, assigned_agent, spawned_at,
                       retry_after_ts, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (r["id"], "fake-proj", "developer", status, "t", "d", "[]", "[]", r["host"],
                     r["dispatcher_host"], r["runner"], 4242, extra.get("assigned_agent"),
                     old if prefix == "g1b" else None, extra.get("retry_after_ts"), old, old))
        conn.commit()
    mp.setattr(gc, "_pid_alive", lambda pid: variant == "remote")
    mp.setattr(gc, "remote_pid_alive", lambda cfg, pid: variant == "local")
    mp.setattr(gc, "get_host", lambda name: {"ssh": name})
    mp.setattr(gc, "_reclaim_worktree", lambda t, dry_run=False: {})
    mp.setattr(gc.disk_queue, "is_queued", lambda task_id: False)
    gc.gc_stale_tasks()
    with db_mod.get_conn() as conn:
        cancelled = [r["id"] for r in conn.execute("SELECT id FROM tasks WHERE status='cancelled'")]
    by_cat = {p: {i for i in cancelled if i.startswith(f"task-{p}-")} for p in ("g1", "g1b", "g2", "g3")}
    if variant == "local":
        return {"gc1": _keys(by_cat["g1"]), "gc1b_local": _keys(by_cat["g1b"]),
                "gc3_local": _keys(by_cat["g3"]), "gc2": _keys(by_cat["g2"])}
    return {"gc1b_remote": _keys(by_cat["g1b"]), "gc3_remote": _keys(by_cat["g3"])}


def _passes_for(box: str, tmp_path: Path) -> dict:
    out: dict = {}

    def duty(fn, *args, db_name: str | None = None):
        with pytest.MonkeyPatch.context() as mp:
            # a module-scoped fixture runs before the per-test autouse isolation, so pin it here
            mp.delenv("ORG_DB_URL", raising=False)
            mp.setenv("ORG_HOST", box)
            config.self_host.cache_clear()
            assert config.self_host() == box
            mp.setattr(db_mod, "DB_PATH", tmp_path / (db_name or "unused.db"))
            if db_name:
                db_mod.init()
            out.update(fn(mp, *args))

    duty(_poller_duties)
    duty(_scan_duties)
    duty(_terminal_duties)
    duty(_work_watch_duty)
    duty(_close_remote_duty, tmp_path, db_name="close_remote.db")
    duty(_gc_duties, tmp_path, "local", db_name="gc_local.db")
    duty(_gc_duties, tmp_path, "remote", db_name="gc_remote.db")
    config.self_host.cache_clear()
    return out


@pytest.fixture(scope="module")
def passes(tmp_path_factory):
    result = {box: _passes_for(box, tmp_path_factory.mktemp(box)) for box in BOXES}
    yield result
    config.self_host.cache_clear()


def _actors(passes, duty, key) -> set:
    return {b for b in BOXES if key in passes[b][duty]}


# ---------------------------------------------------------------------------
# The rules, over the whole fake ledger
# ---------------------------------------------------------------------------

def test_every_duty_actually_ran(passes):
    """A duty whose stubs silently matched nothing would make every assertion below vacuous."""
    for box in BOXES:
        for duty in ALL_DUTIES:
            assert duty in passes[box], (box, duty)
            assert passes[box][duty], f"{duty} on {box} acted on nothing"


@pytest.mark.parametrize("duty", ALL_DUTIES)
def test_each_duty_acts_on_exactly_the_rows_the_rules_name(duty, passes):
    for key in EXPLICIT:
        expect = {b for b in BOXES if _owner(duty, key) == b}
        got = _actors(passes, duty, key)
        assert len(got) <= 1, f"{duty}: two boxes act on {key}: {got}"
        assert got == expect, f"{duty} {key}: acted by {got}, rules say {expect}"


def test_local_duties_have_exactly_one_owner_for_a_row_mac_or_contabo_runs(passes):
    for duty in LOCAL_DUTIES:
        for key in EXPLICIT:
            want = 1 if key[0] in BOXES else 0
            assert len(_actors(passes, duty, key)) == want, (duty, key)


def test_remote_duties_have_exactly_one_owner_for_a_row_a_box_dispatched_elsewhere(passes):
    for duty in REMOTE_DUTIES:
        for key in EXPLICIT:
            want = 1 if (key[1] in BOXES and key[1] != key[0]) else 0
            assert len(_actors(passes, duty, key)) == want, (duty, key)


@pytest.mark.parametrize("box", BOXES)
@pytest.mark.parametrize("duty", ALL_DUTIES)
def test_null_host_and_dispatcher_behave_as_self(box, duty, passes):
    for key in ALL_KEYS:
        if key[0] is not None and key[1] is not None:
            continue
        d = key[1] or box
        twin = (key[0] or d, d, key[2])
        assert (key in passes[box][duty]) == (twin in passes[box][duty]), \
            f"{duty} on {box}: {key} must act like {twin}"


def test_nothing_is_cancelled_stalled_or_killed_for_a_row_neither_box_owns(passes):
    neither = [("winbox", "winbox", r) for r in RUNNERS] + [(None, "winbox", r) for r in RUNNERS]
    for box in BOXES:
        for duty in ALL_DUTIES:
            for key in neither:
                assert key not in passes[box][duty], f"{duty} on {box} touched {key}"


# ---------------------------------------------------------------------------
# The poller set, spelled out
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("runner", RUNNERS)
def test_a_winbox_row_dispatched_by_contabo_is_polled_by_contabo_only(runner, passes):
    key = ("winbox", "contabo", runner)
    assert key in passes["contabo"]["poller"]
    assert key not in passes["mac"]["poller"]


@pytest.mark.parametrize("runner", RUNNERS)
def test_a_contabo_row_dispatched_by_mac_is_polled_by_mac_only(runner, passes):
    key = ("contabo", "mac", runner)
    assert key in passes["mac"]["poller"]
    assert key not in passes["contabo"]["poller"]


def test_a_contabo_dispatched_contabo_row_is_polled_only_when_its_runner_is_codex_or_agy(passes):
    assert ("contabo", "contabo", "codex") in passes["contabo"]["poller"]
    assert ("contabo", "contabo", "agy") in passes["contabo"]["poller"]
    assert ("contabo", "contabo", "claude") not in passes["contabo"]["poller"]
    for runner in RUNNERS:
        assert ("contabo", "contabo", runner) not in passes["mac"]["poller"]


def test_the_mac_polls_its_own_codex_launcher_rows_and_not_its_claude_ones(passes):
    assert ("mac", "mac", "codex") in passes["mac"]["poller"]
    assert ("mac", "mac", "claude") not in passes["mac"]["poller"]


@pytest.fixture
def as_box(monkeypatch):
    def _set(name: str) -> None:
        monkeypatch.setenv("ORG_HOST", name)
        config.self_host.cache_clear()
        assert config.self_host() == name
    yield _set
    config.self_host.cache_clear()


@pytest.mark.parametrize("box", BOXES)
def test_poller_set_predicate_matches_what_tick_polls(box, passes, as_box):
    as_box(box)
    for key in ALL_KEYS:
        row = {"host": key[0], "dispatcher_host": key[1], "runner": key[2]}
        assert poller.in_poller_set(row) == (key in passes[box]["poller"]), (box, key)


# ---------------------------------------------------------------------------
# branch_poller.check_task: the poller set reaches review; a local launcher is not ssh-closed
# ---------------------------------------------------------------------------

def _wire_check_task(monkeypatch, *, branch_exists=True, project=None):
    seen = SimpleNamespace(flips=[], remote_close=[], local_close=[], repo=[], pid_probe=[])
    proj = project or {"path": "/mac/repo", "default_branch": "main"}
    monkeypatch.setattr(poller, "get_project", lambda key: proj)
    monkeypatch.setattr(poller, "remote_branch_exists",
                        lambda repo, br: seen.repo.append(repo) or branch_exists)
    monkeypatch.setattr(poller, "fetch_branch", lambda repo, br: True)
    monkeypatch.setattr(poller, "read_task_file",
                        lambda repo, br, tid, name: f"# REPORT {tid}\nok\n" if name == "REPORT.md" else None)
    monkeypatch.setattr(poller, "_artefact_gate_for_external_runner",
                        lambda t, repo, br: SimpleNamespace(reasons=["ok"]))
    monkeypatch.setattr(poller.db, "update_status",
                        lambda tid, status, **kw: seen.flips.append((tid, status)))
    monkeypatch.setattr(poller, "_maybe_close_finished_remote_worker",
                        lambda tid, repo, br: seen.remote_close.append(tid))
    monkeypatch.setattr(poller, "_maybe_close_finished_local_launcher",
                        lambda tid, repo, br: seen.local_close.append(tid))
    monkeypatch.setattr(poller, "get_host", lambda name: {"ssh": name})
    monkeypatch.setattr(poller, "remote_pid_alive", lambda cfg, pid: seen.pid_probe.append(pid))
    return seen


def _row(task_id, host, dispatcher, runner, **extra):
    return {"id": task_id, "project": "p", "branch": "agent/x", "host": host,
            "dispatcher_host": dispatcher, "runner": runner, "pid": 7, **extra}


@pytest.mark.parametrize("runner", EXTERNAL)
def test_local_codex_or_agy_launcher_row_flips_to_review_and_is_closed_locally_not_over_ssh(
        runner, as_box, monkeypatch):
    as_box("contabo")
    seen = _wire_check_task(monkeypatch)

    poller.check_task(_row("task-launch01", "contabo", "contabo", runner))

    assert seen.flips == [("task-launch01", "review")]
    assert seen.local_close == ["task-launch01"]
    assert seen.remote_close == []


def test_remote_row_dispatched_here_flips_to_review_and_takes_the_ssh_close(as_box, monkeypatch):
    as_box("contabo")
    seen = _wire_check_task(monkeypatch)

    poller.check_task(_row("task-winrow01", "winbox", "contabo", "claude"))

    assert seen.flips == [("task-winrow01", "review")]
    assert seen.remote_close == ["task-winrow01"]
    assert seen.local_close == []


@pytest.mark.parametrize("host,dispatcher,runner", [
    ("contabo", "contabo", "claude"),   # this box's own claude worker reports through MCP
    ("winbox", "mac", "codex"),         # another box's dispatch
    ("mac", "mac", "codex"),            # another box's own launcher run
    ("winbox", "winbox", "claude"),     # nobody's
])
def test_check_task_leaves_rows_outside_the_poller_set_alone(host, dispatcher, runner, as_box, monkeypatch):
    as_box("contabo")
    seen = _wire_check_task(monkeypatch)

    poller.check_task(_row("task-other001", host, dispatcher, runner))

    assert (seen.flips, seen.repo, seen.pid_probe) == ([], [], [])


def test_a_local_launcher_row_with_no_branch_yet_is_not_judged_dead_from_the_poller(as_box, monkeypatch):
    """A local pid is the watchdog's LOCAL duty. The poller's ssh dead-pid tail is remote-only."""
    as_box("contabo")
    seen = _wire_check_task(monkeypatch, branch_exists=False)

    poller.check_task(_row("task-launch02", "contabo", "contabo", "codex"))

    assert (seen.flips, seen.pid_probe) == ([], [])


@pytest.mark.parametrize("box,expected", [("mac", "/mac/repo"), ("contabo", "/opt/contabo/repo")])
def test_the_poller_reads_this_boxs_own_checkout(box, expected, as_box, monkeypatch):
    as_box(box)
    seen = _wire_check_task(monkeypatch, project={
        "path": "/mac/repo", "paths": {"contabo": "/opt/contabo/repo"}, "default_branch": "main"})

    poller.check_task(_row("task-repo0001", "winbox", box, "claude"))

    assert seen.repo == [expected]


# ---------------------------------------------------------------------------
# Local launcher: closed after review + the existing quiet period, locally, only if still alive
# ---------------------------------------------------------------------------

def _wire_local_close(monkeypatch, *, row, tmux_alive=True, age=None):
    seen = SimpleNamespace(cleaned=[], fetched=[], remote_close=[])
    monkeypatch.setattr(poller.db, "get_task", lambda tid: row)
    monkeypatch.setattr(poller, "_tmux_alive", lambda session: tmux_alive)
    monkeypatch.setattr(poller, "fetch_branch", lambda repo, br: seen.fetched.append(br) or True)
    monkeypatch.setattr(poller, "read_task_file", lambda repo, br, tid, name: "# REPORT\n")
    monkeypatch.setattr(poller, "remote_commit_age_seconds", lambda repo, br: age)
    monkeypatch.setattr(poller, "_cleanup_tmux_ttyd",
                        lambda t: seen.cleaned.append(t["id"]) or {"tmux_killed": True, "ttyd_killed": False})
    monkeypatch.setattr(poller, "close_remote", lambda *a, **kw: seen.remote_close.append(a))
    return seen


def _review_row(**over):
    return {"id": "task-launch09", "status": "review", "host": "contabo",
            "dispatcher_host": "contabo", "runner": "codex", "tmux_session": None, **over}


def test_local_launcher_session_still_alive_after_the_quiet_period_is_closed_locally(as_box, monkeypatch):
    as_box("contabo")
    seen = _wire_local_close(monkeypatch, row=_review_row(), age=poller.REVIEW_CLOSE_QUIET_S + 1)

    poller._maybe_close_finished_local_launcher("task-launch09", "/repo", "agent/x")

    assert seen.cleaned == ["task-launch09"]
    assert seen.remote_close == []


@pytest.mark.parametrize("why,kw,over", [
    ("session already gone", {"tmux_alive": False, "age": 10_000}, {}),
    ("still inside the quiet period", {"age": poller.REVIEW_CLOSE_QUIET_S - 1}, {}),
    ("no commit age", {"age": None}, {}),
    ("status moved off review", {"age": 10_000}, {"status": "in_progress"}),
    ("claude row", {"age": 10_000}, {"runner": "claude"}),
    ("another box's run", {"age": 10_000}, {"host": "mac", "dispatcher_host": "contabo"}),
])
def test_local_launcher_close_stays_its_hand(why, kw, over, as_box, monkeypatch):
    as_box("contabo")
    seen = _wire_local_close(monkeypatch, row=_review_row(**over), **kw)

    poller._maybe_close_finished_local_launcher("task-launch09", "/repo", "agent/x")

    assert seen.cleaned == [], why
    assert seen.remote_close == [], why


def test_review_sweep_reoffers_only_local_external_launcher_rows(as_box, monkeypatch):
    as_box("contabo")
    rows = [_row("task-rv-mine", "contabo", "contabo", "codex", status="review"),
            _row("task-rv-claude", "contabo", "contabo", "claude", status="review"),
            _row("task-rv-remote", "winbox", "contabo", "codex", status="review"),
            _row("task-rv-theirs", "mac", "mac", "codex", status="review")]
    monkeypatch.setattr(poller.db, "list_tasks", lambda status=None, limit=0, **kw: list(rows))
    monkeypatch.setattr(poller, "get_project", lambda key: {"path": "/r"})
    offered = []
    monkeypatch.setattr(poller, "_maybe_close_finished_local_launcher",
                        lambda tid, repo, br: offered.append(tid))

    poller._sweep_review_local_launchers()

    assert offered == ["task-rv-mine"]


# ---------------------------------------------------------------------------
# codex transcript: a Linux launcher's events file is not a Windows path
# ---------------------------------------------------------------------------

def test_codex_transcript_of_this_boxs_own_launcher_is_read_from_its_checkout(as_box, monkeypatch, tmp_path):
    as_box("contabo")
    launch = tmp_path / ".launch-task-tr000001"
    launch.mkdir()
    (launch / "codex-events.jsonl").write_text('{"type":"turn.completed"}\n', encoding="utf-8")
    monkeypatch.setattr(poller, "ROOT", tmp_path)
    monkeypatch.setattr(poller, "get_host", lambda name: {"os": "linux"})

    assert '"turn.completed"' in poller._fetch_codex_transcript("contabo", "task-tr000001")
    assert poller._fetch_codex_transcript("contabo", "task-tr999999") is None


def test_codex_transcript_of_a_linux_spoke_is_cat_over_ssh(as_box, monkeypatch):
    as_box("mac")
    monkeypatch.setattr(poller, "get_host", lambda name: {
        "os": "linux", "ssh": "mooniex-vps", "agents_root": "/opt/MoonieXHQ/Agents/Core"})
    calls = []
    monkeypatch.setattr(poller, "_run", lambda cmd, **kw: calls.append(cmd) or
                        SimpleNamespace(returncode=0, stdout='{"type":"turn.completed"}\n', stderr=""))

    assert poller._fetch_codex_transcript("contabo", "task-tr000002")
    assert calls == [["ssh", "mooniex-vps", "cat",
                      "/opt/MoonieXHQ/Agents/Core/.launch-task-tr000002/codex-events.jsonl"]]


# ---------------------------------------------------------------------------
# Unchanged by W1.5, pinned so a later edit cannot change them unnoticed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag,ticks", [(None, 0), ("1", 1)])
def test_branch_poll_flag_still_defaults_to_off(flag, ticks, as_box, monkeypatch):
    as_box("mac")
    if flag is None:
        monkeypatch.delenv("ORG_WATCHDOG_BRANCH_POLL", raising=False)
    else:
        monkeypatch.setenv("ORG_WATCHDOG_BRANCH_POLL", flag)
    monkeypatch.setattr(watchdog.db, "list_tasks", lambda status=None, limit=0, **kw: [])
    monkeypatch.setattr(watchdog, "gc_stale_tasks", lambda: [])
    monkeypatch.setattr(watchdog, "sweep_terminal_surfaces", lambda: [])
    monkeypatch.setattr(watchdog, "_drain_disk_queue", lambda: None)
    monkeypatch.setattr(watchdog.work_watch, "watch",
                        lambda: {"alerted": [], "lungnote_filed": [], "green": []})
    called = []
    monkeypatch.setattr(watchdog.branch_poller, "tick", lambda: called.append(1) or 0)

    watchdog.scan_once()

    assert len(called) == ticks


def test_disk_queue_file_is_per_checkout_so_a_box_drains_only_what_it_queued():
    """conftest re-points QUEUE_PATH at tmp_path for every test, so read the shipped default."""
    src = (ROOT / "tools" / "disk_queue.py").read_text(encoding="utf-8")
    assert 'QUEUE_PATH = ROOT / "state" / "disk_queue.jsonl"' in src
    assert "ROOT = Path(__file__).resolve().parent.parent" in src


@pytest.mark.parametrize("box", BOXES)
def test_session_reconcile_checks_only_this_boxs_sessions_and_legacy_null_rows(box, as_box, monkeypatch, tmp_path):
    as_box(box)
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "sessions.db")
    db_mod.init()
    with db_mod.get_conn() as conn:
        for i, h in enumerate(("mac", "contabo", "winbox", None)):
            conn.execute("INSERT INTO c_level_sessions (role, session_id, spawned_at, status, host) "
                         "VALUES ('cto', ?, ?, 'open', ?)", (f"s{i}", db_mod.now_iso(), h))
        conn.commit()
    monkeypatch.setattr(session_reconcile, "tmux_lock_live", lambda role, sid: True)

    result = session_reconcile.reconcile(apply=False)

    other = sorted(h for h in ("mac", "contabo", "winbox") if h != box)
    assert result["checked"] == 2   # this box + the NULL legacy row
    assert sorted(h for _, _, h in result["skipped_other_host"]) == other
