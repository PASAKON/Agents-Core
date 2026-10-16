"""lib/run_liveness.py -- the one reader of "is this run alive" (plan B1).

Every state is pinned from a fixture row plus stubbed pid / tmux / log
answers: no process, tmux server or ledger is touched.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pytest

from lib import run_liveness as rl

NOW = 1_800_000_000.0


def iso(offset_s: float) -> str:
    """Ledger timestamp `offset_s` seconds before NOW."""
    return datetime.fromtimestamp(NOW - offset_s, timezone.utc).isoformat(timespec="seconds")


def row(**kw) -> dict:
    base = {
        "id": "task-aaaa1111", "status": "in_progress", "role": "developer",
        "title": "fixture", "runner": "claude", "runner_model": None,
        "owner_cto": "7cf528f0", "pid": 4242, "tmux_session": None,
        "worktree": None, "spawned_at": iso(3600), "created_at": iso(3700),
        "updated_at": iso(3000),
    }
    base.update(kw)
    return base


def state(task, *, pid=True, tmux=False, last_log=None, now=NOW, report_ok=None):
    return rl.classify(task, pid_ok=pid, tmux_ok=tmux, last_log=last_log,
                       now=now, report_ok=report_ok)


@pytest.fixture(autouse=True)
def _default_thresholds(monkeypatch):
    for name in ("RUN_WATCH_QUIET_S", "RUN_WATCH_BATCH_S", "RUN_WATCH_ENDED_S",
                 "RUN_WATCH_SPAWN_GRACE_S", "RUN_WATCH_REPORT_GRACE_S"):
        monkeypatch.delenv(name, raising=False)


# --- the five states -------------------------------------------------------

def test_running_alive_and_logging():
    assert state(row(), last_log=NOW - 10) == "running"


def test_running_when_only_tmux_answers():
    assert state(row(pid=None), pid=False, tmux=True, last_log=NOW - 10) == "running"


def test_quiet_after_quiet_s_without_a_log_write():
    assert state(row(), last_log=NOW - 901) == "quiet"
    assert state(row(), last_log=NOW - 899) == "running"


@pytest.mark.parametrize("status", ["review", "done", "merged"])
def test_done(status):
    assert state(row(status=status), pid=False) == "done"


@pytest.mark.parametrize("status", ["failed", "stalled"])
def test_failed(status):
    assert state(row(status=status), pid=False) == "failed"


def test_dead_when_pid_and_tmux_are_gone_on_a_live_status():
    assert state(row(), pid=False, tmux=False, last_log=NOW - 3000) == "dead"


@pytest.mark.parametrize("status", ["pending", "rate_limited", "conflict", "blocked_human",
                                    "blocked_host", "queued_remote", "cancelled", "reverted"])
def test_not_a_run(status):
    assert state(row(status=status), pid=False) is None


# --- thresholds come from the environment ---------------------------------

def test_quiet_threshold_from_env(monkeypatch):
    monkeypatch.setenv("RUN_WATCH_QUIET_S", "60")
    assert state(row(), last_log=NOW - 61) == "quiet"
    assert state(row(), last_log=NOW - 59) == "running"


@pytest.mark.parametrize("junk", ["", "abc", "0", "-5", "1.5"])
def test_bad_env_falls_back_to_default(monkeypatch, junk):
    monkeypatch.setenv("RUN_WATCH_QUIET_S", junk)
    monkeypatch.setenv("RUN_WATCH_BATCH_S", junk)
    assert rl.quiet_s() == 900
    assert rl.batch_s() == 120


# --- the rules that keep a red light true ---------------------------------

def test_no_log_yet_judges_quiet_from_the_start_time():
    assert state(row(spawned_at=iso(1000)), last_log=None) == "quiet"
    assert state(row(spawned_at=iso(100)), last_log=None) == "running"


def test_a_log_older_than_the_respawn_does_not_make_it_quiet():
    # reopened task: yesterday's transcript, worker spawned 10 s ago
    assert state(row(spawned_at=iso(10)), last_log=NOW - 90000) == "running"


def test_just_spawned_row_is_never_dead():
    fresh = row(spawned_at=iso(30), updated_at=iso(30))
    assert state(fresh, pid=False, tmux=False) == "running"
    assert state(row(spawned_at=iso(30 + 3600)), pid=False) == "dead"


def test_a_row_written_just_now_is_not_dead_yet():
    # reopen_task writes the row before the respawn: updated_at is fresh
    assert state(row(updated_at=iso(20)), pid=False, tmux=False) == "running"


@pytest.mark.parametrize("runner", ["codex", "agy"])
def test_external_runner_waits_for_branch_poller_before_dead(runner):
    """It exited cleanly; the row flips to review on the next 60 s poll."""
    t = row(runner=runner)
    assert state(t, pid=False, tmux=False, last_log=NOW - 30) == "running"
    assert state(t, pid=False, tmux=False, last_log=NOW - 400) == "dead"


@pytest.mark.parametrize("runner", ["codex", "agy"])
def test_external_runner_report_ok_controls_report_grace(runner):
    t = row(runner=runner)
    assert state(t, pid=False, tmux=False, last_log=NOW - 30, report_ok=False) == "dead"
    assert state(t, pid=False, tmux=False, last_log=NOW - 30, report_ok=True) == "running"
    assert state(t, pid=False, tmux=False, last_log=NOW - 30, report_ok=None) == "running"
    assert rl.classify(t, pid_ok=False, tmux_ok=False, last_log=NOW - 30, now=NOW) == "running"
    fresh = row(runner=runner, spawned_at=iso(30), updated_at=iso(30))
    assert state(fresh, pid=False, tmux=False, last_log=NOW - 30, report_ok=False) == "running"


def test_claude_worker_gets_no_report_grace():
    # a claude worker reports through the MCP tool itself: gone + in_progress = dead
    assert state(row(), pid=False, tmux=False, last_log=NOW - 30) == "dead"


def test_report_grace_from_env(monkeypatch):
    monkeypatch.setenv("RUN_WATCH_REPORT_GRACE_S", "20")
    assert state(row(runner="codex"), pid=False, last_log=NOW - 30) == "dead"


def test_unparseable_timestamps_never_crash():
    t = row(spawned_at="garbage", created_at=None, updated_at="")
    assert state(t, pid=False, tmux=False) == "dead"
    assert state(t, pid=True, last_log=None) == "running"


# --- probes ---------------------------------------------------------------

def test_tmux_names_are_the_recorded_session_and_wd():
    names = rl.tmux_names(row(tmux_session="mooniex-task-aaaa1111"))
    assert names == ["mooniex-task-aaaa1111", "wd-aaaa1111"]
    assert rl.tmux_names(row(tmux_session="wd-aaaa1111")) == ["wd-aaaa1111"]
    assert rl.tmux_names(row()) == ["wd-aaaa1111"]


def test_probe_tmux_checks_every_name_and_survives_a_missing_binary(monkeypatch):
    seen = []
    monkeypatch.setattr(rl.tmux_session, "has_session",
                        lambda n: seen.append(n) or n == "wd-aaaa1111")
    assert rl.probe_tmux(row(tmux_session="mooniex-task-aaaa1111")) is True
    assert seen == ["mooniex-task-aaaa1111", "wd-aaaa1111"]

    def boom(name):
        raise FileNotFoundError("tmux")
    monkeypatch.setattr(rl.tmux_session, "has_session", boom)
    assert rl.probe_tmux(row()) is False


def test_a_pid_we_may_not_signal_still_counts_as_alive(monkeypatch):
    """A reader run by another user must not call every root worker dead."""
    def denied(pid, sig):
        raise PermissionError
    monkeypatch.setattr(os, "kill", denied)
    assert rl.probe_pid(row(pid=4242)) is True
    assert rl.probe_pid(row(pid=None)) is False


def test_probe_report_with_without_and_missing_worktree(monkeypatch, tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    t = row(runner="codex", worktree=str(wt))
    assert rl.probe_report(t) is False

    report = wt / "docs" / "reports" / t["id"] / "REPORT.md"
    report.parent.mkdir(parents=True)
    report.write_text("# REPORT task-aaaa1111\n")
    assert rl.probe_report(t) is True

    assert rl.probe_report(row(worktree=None)) is None
    assert rl.probe_report(row(worktree="")) is None
    assert rl.probe_report({"id": "task-aaaa1111"}) is None

    def denied(self):
        raise PermissionError("unreadable")
    monkeypatch.setattr(rl.Path, "is_file", denied)
    assert rl.probe_report(t) is None


# --- where the log is ------------------------------------------------------

def test_claude_project_dir_slug_matches_the_measured_one(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    wt = "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-ce1930f9"
    assert rl.claude_project_dir(wt).name == (
        "-opt-MoonieXHQ-Agents-Core-worktrees-mooniex-agents--developer--task-ce1930f9")


def test_newest_log_reads_transcript_and_cli_logs_but_not_the_heartbeat(monkeypatch, tmp_path):
    cfg, hub, wt = tmp_path / "cfg", tmp_path / "hub", tmp_path / "wt"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    monkeypatch.setenv("ORG_ROOT", str(hub))
    wt.mkdir()
    t = row(worktree=str(wt))
    proj = rl.claude_project_dir(str(wt))
    proj.mkdir(parents=True)
    transcript = proj / "s1.jsonl"
    transcript.write_text("{}\n")
    launch = hub / ".launch-task-aaaa1111"
    launch.mkdir(parents=True)
    codex = launch / "codex-events.jsonl"
    codex.write_text("{}\n")
    heartbeat = wt / "HEARTBEAT"
    heartbeat.write_text("2026-10-15T00:00:00Z\n")
    os.utime(transcript, (1000, 1000))
    os.utime(codex, (2000, 2000))
    os.utime(heartbeat, (9000, 9000))        # newest of all, and must not count

    assert rl.newest_log(t) == (codex, 2000.0)
    os.utime(transcript, (3000, 3000))
    assert rl.newest_log(t) == (transcript, 3000.0)
    assert heartbeat not in rl.log_files(t)


def test_newest_log_is_none_when_nothing_was_written(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "hub"))
    assert rl.newest_log(row(worktree=str(tmp_path / "wt"))) == (None, None)
    assert rl.newest_log(row(worktree=None)) == (None, None)


# --- inspect_run ----------------------------------------------------------

def _boom(*a, **k):
    raise AssertionError("a finished run must not be probed")


def test_inspect_run_schema_for_a_live_run():
    run = rl.inspect_run(
        row(runner="agy", runner_model="gemini-4-argon-high"), now=NOW,
        pid_alive_fn=lambda t: True, tmux_alive_fn=lambda t: False,
        newest_log_fn=lambda t: ("/x/agy-events.log", NOW - 42))
    assert run == {
        "task": "task-aaaa1111", "state": "running", "status": "in_progress",
        "runner": "agy", "model": "gemini-4-argon-high", "owner": "7cf528f0",
        "title": "fixture", "started": iso(3600), "elapsed_s": 3600, "ended": None,
        "last_log": iso(42), "idle_s": 42, "log": "/x/agy-events.log",
        "pid": 4242, "pid_alive": True, "tmux_alive": False,
    }


def test_inspect_run_of_a_finished_run_uses_the_ledger_not_the_probes():
    run = rl.inspect_run(row(status="review", updated_at=iso(600)), now=NOW,
                         pid_alive_fn=_boom, tmux_alive_fn=_boom,
                         newest_log_fn=lambda t: (None, None))
    assert run["state"] == "done"
    assert run["ended"] == iso(600)
    assert run["elapsed_s"] == 3000          # frozen at the end, not growing with now
    assert (run["pid_alive"], run["tmux_alive"]) == (False, False)


def test_inspect_run_is_none_for_a_row_that_is_not_a_run():
    assert rl.inspect_run(row(status="blocked_human"), now=NOW,
                          pid_alive_fn=_boom, tmux_alive_fn=_boom,
                          newest_log_fn=lambda t: (None, None)) is None


def test_inspect_run_defaults_now_to_the_clock():
    started = datetime.fromtimestamp(time.time() - 5, timezone.utc).isoformat(timespec="seconds")
    run = rl.inspect_run(row(spawned_at=started, updated_at=started),
                         pid_alive_fn=lambda t: True, tmux_alive_fn=lambda t: False,
                         newest_log_fn=lambda t: (None, None))
    assert run["state"] == "running"
    assert 0 <= run["elapsed_s"] < 60


def test_inspect_run_probes_report_for_external_runner(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    t = row(runner="codex", worktree=str(wt))
    dead_run = rl.inspect_run(
        t, now=NOW, pid_alive_fn=lambda r: False, tmux_alive_fn=lambda r: False,
        newest_log_fn=lambda r: ("/x/codex-events.jsonl", NOW - 30))
    assert dead_run["state"] == "dead"

    report = wt / "docs" / "reports" / t["id"] / "REPORT.md"
    report.parent.mkdir(parents=True)
    report.write_text("# REPORT task-aaaa1111\n")
    grace_run = rl.inspect_run(
        t, now=NOW, pid_alive_fn=lambda r: False, tmux_alive_fn=lambda r: False,
        newest_log_fn=lambda r: ("/x/codex-events.jsonl", NOW - 30))
    assert grace_run["state"] == "running"
