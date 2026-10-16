"""Tests for Run Watch part B (tools/run_watch.py light/ack + tools/run_watcher.py).

Fixtures only -- no hub connection, no subprocesses, no tmux.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lib import run_liveness as rl, session_names as sn
from tools import run_watch as rw, run_watcher as watcher

NOW = 1_800_000_000.0


def iso(offset_s: float) -> str:
    return datetime.fromtimestamp(NOW - offset_s, timezone.utc).isoformat(timespec="seconds")


def row(tid: str = "task-aaaa1111", **kw) -> dict:
    base = {
        "id": tid,
        "status": "in_progress",
        "role": "developer",
        "title": "fixture title",
        "runner": "claude",
        "runner_model": "claude-sonnet-5-5",
        "owner_cto": "7cf528f0",
        "pid": 4242,
        "tmux_session": None,
        "worktree": None,
        "spawned_at": iso(3600),
        "created_at": iso(3700),
        "updated_at": iso(3000),
    }
    base.update(kw)
    return base


def stubs(alive=(), logs=None):
    logs = logs or {}
    return dict(
        is_local=lambda t: t.get("host") in (None, "contabo"),
        pid_alive_fn=lambda t: t["id"] in alive,
        tmux_alive_fn=lambda t: False,
        newest_log_fn=lambda t: (
            (f"/log/{t['id']}", logs[t["id"]]) if t["id"] in logs else (None, None)
        ),
    )


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    # Anything that writes state lands under tmp_path, never the checkout.
    monkeypatch.setattr(rw, "STATE_ROOT", tmp_path / "run-watch")
    monkeypatch.setattr(watcher, "STEWARD_ROOT", tmp_path / "steward")
    for name in (
        "RUN_WATCH_QUIET_S",
        "RUN_WATCH_CLOSE_AFTER_S",
        "RUN_WATCH_BATCH_S",
        "RUN_WATCH_ENDED_S",
        "RUN_WATCH_SPAWN_GRACE_S",
        "RUN_WATCH_REPORT_GRACE_S",
        "RUN_WATCH_POLL_S",
        "RUN_WATCH_STATE_DIR",
        "RUN_WATCH_STEWARD_DIR",
        "RUN_WATCH_SID",
    ):
        monkeypatch.delenv(name, raising=False)


# --------------------------------------------------------------------------
# 1. Light states and active count
# --------------------------------------------------------------------------

def test_light_white_when_zero_active_runs(tmp_path: Path):
    assert rw.compute_light([], host="contabo", state_dir=tmp_path) == (0, "⚪")
    # A recently finished ("done") run is not active, so count is 0 and light is ⚪.
    tasks = [row("task-done0001", status="review", updated_at=iso(120))]
    runs = rw.collect_runs(tasks, now=NOW, **stubs())
    assert [r["state"] for r in runs] == ["done"]
    assert rw.compute_light(runs, host="contabo", state_dir=tmp_path) == (0, "⚪")


def test_light_green_when_all_active_runs_are_running(tmp_path: Path):
    tasks = [
        row("task-run00001"),
        row("task-run00002"),
        row("task-done0001", status="review", updated_at=iso(120)),
    ]
    probes = stubs(
        alive={"task-run00001", "task-run00002"},
        logs={"task-run00001": NOW - 10, "task-run00002": NOW - 30},
    )
    runs = rw.collect_runs(tasks, now=NOW, **probes)
    n_active, light = rw.compute_light(runs, host="contabo", state_dir=tmp_path)
    assert (n_active, light) == (2, sn.LIGHTS[0])
    assert light == "\U0001F7E2"


def test_light_yellow_when_any_active_run_is_quiet_over_15m(tmp_path: Path):
    tasks = [
        row("task-run00001"),
        row("task-quiet001"),
    ]
    probes = stubs(
        alive={"task-run00001", "task-quiet001"},
        logs={"task-run00001": NOW - 10, "task-quiet001": NOW - 905},
    )
    runs = rw.collect_runs(tasks, now=NOW, **probes)
    n_active, light = rw.compute_light(runs, host="contabo", state_dir=tmp_path)
    assert (n_active, light) == (2, sn.LIGHTS[1])
    assert light == "\U0001F7E1"


def test_light_red_when_any_run_failed_or_dead(tmp_path: Path):
    # Failed run with one running run -> n_active=1, light=🔴
    tasks_fail = [
        row("task-run00001"),
        row("task-fail0001", status="failed", updated_at=iso(100)),
    ]
    probes_fail = stubs(alive={"task-run00001"}, logs={"task-run00001": NOW - 5})
    runs_fail = rw.collect_runs(tasks_fail, now=NOW, **probes_fail)
    assert rw.compute_light(runs_fail, host="contabo", state_dir=tmp_path / "f") == (
        1,
        "\U0001F534",
    )

    # Dead run with zero running runs -> n_active=0, light=🔴
    tasks_dead = [row("task-dead0001")]
    probes_dead = stubs(alive=set(), logs={"task-dead0001": NOW - 2000})
    runs_dead = rw.collect_runs(tasks_dead, now=NOW, **probes_dead)
    assert rw.compute_light(runs_dead, host="contabo", state_dir=tmp_path / "d") == (
        0,
        "\U0001F534",
    )


# --------------------------------------------------------------------------
# 2. Sticky 🔴 and its two ways to clear (status ack vs re-delegation)
# --------------------------------------------------------------------------

def test_sticky_red_persists_until_cleared_and_clears_on_status_ack(
    tmp_path: Path, monkeypatch, capsys
):
    state_dir = tmp_path / "state" / "run-watch" / "contabo"
    tasks = [
        row("task-run00001"),
        row("task-fail0001", status="failed", spawned_at=iso(3600), updated_at=iso(200)),
    ]
    probes = stubs(alive={"task-run00001"}, logs={"task-run00001": NOW - 5})
    runs = rw.collect_runs(tasks, now=NOW, **probes)

    # 1. Initial check sees failed run -> 🔴 and writes state file.
    assert rw.compute_light(runs, host="contabo", state_dir=state_dir) == (1, "\U0001F534")
    ack_file = state_dir / "ack.json"
    assert ack_file.exists()

    # 2. Even if the failed run ages past the 30-min collect_runs window, 🔴 stays sticky.
    only_running = [r for r in runs if r["state"] == "running"]
    assert rw.compute_light(only_running, host="contabo", state_dir=state_dir) == (
        1,
        "\U0001F534",
    )
    assert rw.compute_light([], host="contabo", state_dir=state_dir) == (0, "\U0001F534")

    # 3. Way 1 to clear: a `status` answer shows the failed run -> records ack in state file.
    monkeypatch.setattr(rw, "this_host", lambda: "contabo")
    monkeypatch.setattr(rw, "fetch_tasks", lambda: tasks)
    real_collect = rw.collect_runs
    monkeypatch.setattr(
        rw, "collect_runs", lambda ts, **kw: real_collect(ts, now=NOW, **{**probes, **kw})
    )
    rc = rw.main(["status", "--bad", "--state-dir", str(state_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "task-fail0001" in out

    # 4. Now light clears from 🔴 to 🟢 (even while task-fail0001 is still in `runs`),
    #    and to ⚪ when no active runs remain.
    assert rw.compute_light(runs, host="contabo", state_dir=state_dir) == (1, "\U0001F7E2")
    assert rw.compute_light([], host="contabo", state_dir=state_dir) == (0, "⚪")


def test_sticky_red_clears_when_task_is_redelegated(tmp_path: Path):
    state_dir = tmp_path / "state" / "run-watch" / "contabo"
    # Dead run triggers sticky 🔴
    t_dead = row("task-dead0001", status="in_progress", spawned_at=iso(3600))
    runs_dead = rw.collect_runs(
        [t_dead], now=NOW, **stubs(alive=set(), logs={"task-dead0001": NOW - 2000})
    )
    assert rw.compute_light(runs_dead, host="contabo", state_dir=state_dir) == (
        0,
        "\U0001F534",
    )
    # Stays 🔴 when polled with no runs
    assert rw.compute_light([], host="contabo", state_dir=state_dir) == (0, "\U0001F534")

    # Way 2a: Task is re-delegated with a new spawned_at and is now running -> clears 🔴 to 🟢.
    t_respawned = row("task-dead0001", status="in_progress", spawned_at=iso(60))
    runs_respawned = rw.collect_runs(
        [t_respawned],
        now=NOW,
        **stubs(alive={"task-dead0001"}, logs={"task-dead0001": NOW - 5}),
    )
    assert rw.compute_light(runs_respawned, host="contabo", state_dir=state_dir) == (
        1,
        "\U0001F7E2",
    )

    # Way 2b: Failed task's status/spawned_at changes in `tasks` -> clears sticky 🔴 to ⚪.
    t_fail = row("task-fail0002", status="failed", spawned_at=iso(3600), updated_at=iso(100))
    runs_fail = rw.collect_runs([t_fail], now=NOW, **stubs())
    assert rw.compute_light(runs_fail, host="contabo", state_dir=state_dir) == (
        0,
        "\U0001F534",
    )
    t_redelegated = row("task-fail0002", status="assigned", spawned_at=iso(30))
    assert rw.compute_light(
        [], host="contabo", state_dir=state_dir, tasks=[t_redelegated]
    ) == (0, "⚪")


# --------------------------------------------------------------------------
# 3. `run_watch.py light [--json]` and winbox ASCII name via windows_safe
# --------------------------------------------------------------------------

def test_winbox_ascii_watch_name_and_cli_light(tmp_path: Path, monkeypatch, capsys):
    # Direct formatter on winbox across all four light states:
    assert rw.format_watch_name(2, rw.LIGHT_OK, sid="a1b2c3", host="winbox") == (
        "Watch#a1b Runs: 2 ok"
    )
    assert rw.format_watch_name(2, rw.LIGHT_QUIET, sid="a1b2c3", host="winbox") == (
        "Watch#a1b Runs: 2 quiet"
    )
    assert rw.format_watch_name(1, rw.LIGHT_BAD, sid="a1b2c3", host="winbox") == (
        "Watch#a1b Runs: 1 FAIL"
    )
    assert rw.format_watch_name(0, rw.LIGHT_IDLE, sid="a1b2c3", host="winbox") == (
        "Watch#a1b Runs: 0 idle"
    )
    for light in sn.LIGHTS:
        win_name = rw.format_watch_name(2, light, sid="a1b", host="winbox")
        assert win_name.isascii()

    # Non-windows host uses emoji prefix and emoji light from session_names.watch_name:
    hub_name = rw.format_watch_name(2, rw.LIGHT_OK, sid="a1b2c3", host="contabo")
    assert hub_name == sn.watch_name("a1b2c3", 2, rw.LIGHT_OK, host="contabo")
    assert "Watch#a1b Runs: 2\U0001F7E2" in hub_name

    # CLI `run_watch.py light` and `run_watch.py light --json`:
    tasks = [row("task-run00001"), row("task-run00002")]
    probes = stubs(
        alive={"task-run00001", "task-run00002"},
        logs={"task-run00001": NOW - 5, "task-run00002": NOW - 10},
    )
    monkeypatch.setattr(rw, "fetch_tasks", lambda: tasks)
    real_collect = rw.collect_runs
    monkeypatch.setattr(
        rw, "collect_runs", lambda ts, **kw: real_collect(ts, now=NOW, **{**probes, **kw})
    )

    rc = rw.main(
        ["light", "--host", "winbox", "--sid", "f9e", "--state-dir", str(tmp_path)]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "Watch#f9e Runs: 2 ok"

    rc = rw.main(
        [
            "light",
            "--json",
            "--host",
            "contabo",
            "--sid",
            "f9e",
            "--state-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc == {
        "host": "contabo",
        "n_active": 2,
        "light": "\U0001F7E2",
        "state": "ok",
        "name": sn.watch_name("f9e", 2, "\U0001F7E2", host="contabo"),
    }


# --------------------------------------------------------------------------
# 4. Lifecycle decisions (start, stop, restart once, give_up -> open.md, none)
# --------------------------------------------------------------------------

def test_lifecycle_start_and_close_after_stop(tmp_path: Path):
    # No runs, no watcher -> none
    assert watcher.decide_lifecycle(0, False, 0, None, NOW, state_root=tmp_path) == "none"

    # First run goes active, no watcher alive -> start
    assert watcher.decide_lifecycle(1, False, 0, None, NOW, state_root=tmp_path) == "start"

    # Run active and watcher alive -> none
    assert watcher.decide_lifecycle(1, True, 1, None, NOW, state_root=tmp_path) == "none"

    # Last run ended < 10 min (600s) ago while watcher alive -> none
    assert watcher.decide_lifecycle(0, True, 1, 0, NOW, state_root=tmp_path) == "none"
    assert watcher.decide_lifecycle(0, True, 1, 599, NOW, state_root=tmp_path) == "none"

    # Last run ended >= 10 min (600s) ago while watcher alive -> stop
    assert watcher.decide_lifecycle(0, True, 1, 600, NOW, state_root=tmp_path) == "stop"
    assert watcher.decide_lifecycle(0, True, 1, 750, NOW, state_root=tmp_path) == "stop"
    # Passing last-ended as an epoch timestamp also works with `now`:
    assert (
        watcher.decide_lifecycle(0, True, 1, NOW - 600, NOW, state_root=tmp_path) == "stop"
    )


def test_lifecycle_restart_once_then_give_up_writes_open_md_and_resets_next_cycle(
    tmp_path: Path,
):
    cycle = watcher.WatcherCycle(host="contabo", state_root=tmp_path)
    open_md = tmp_path / "state" / "steward" / "contabo" / "open.md"

    # 1. Idle -> none
    assert cycle.step(0, False, None, NOW) == "none"

    # 2. First run goes active -> start (start_count becomes 1)
    assert cycle.step(2, False, None, NOW) == "start"
    assert cycle.start_count == 1
    assert cycle.step(2, True, None, NOW + 10) == "none"

    # 3. Watcher dies while runs are active -> restart ONCE (start_count becomes 2)
    assert cycle.step(2, False, None, NOW + 20) == "restart"
    assert cycle.start_count == 2
    assert not open_md.exists()

    # 4. Watcher dies a second time while runs are active -> give_up + 1 line in open.md
    assert cycle.step(2, False, None, NOW + 30) == "give_up"
    assert cycle.start_count == 3
    assert open_md.exists()
    lines = open_md.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "runwatch-contabo" in lines[0]

    # 5. Never resumed during the same active run cycle: stays "none", no extra open.md line
    assert cycle.step(2, False, None, NOW + 40) == "none"
    assert cycle.step(1, False, None, NOW + 50) == "none"
    assert len(open_md.read_text(encoding="utf-8").splitlines()) == 1

    # 6. Active runs finish -> cycle resets; next run starts a fresh watcher
    assert cycle.step(0, False, 10, NOW + 60) == "none"
    assert cycle.start_count == 0
    assert cycle.step(1, False, None, NOW + 70) == "start"
    assert cycle.start_count == 1


# --------------------------------------------------------------------------
# 5. Launch argv builder
# --------------------------------------------------------------------------

def test_launch_argv_builder_output():
    configured = watcher.build_launch_argv("contabo", cwd="/repo", env={"RUN_WATCH_SID": "abc"})
    assert configured[5:9] == ["-c", "/repo", "-e", "RUN_WATCH_SID=abc"]
    argv = watcher.build_launch_argv(
        "contabo", sid="abc12345", n_active=2, light=rw.LIGHT_OK
    )
    assert isinstance(argv, list)
    assert argv[:5] == ["tmux", "new-session", "-d", "-s", "runwatch-contabo"]
    claude_part = argv[5:]
    assert claude_part == [
        "claude",
        "--model",
        "haiku",
        "--remote-control",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        "Bash(bash scripts/hub/org-python.sh tools/run_watch.py *)",
        "--append-system-prompt-file",
        "roles/run_watch.md",
        "-n",
        sn.watch_name("abc12345", 2, rw.LIGHT_OK, host="contabo"),
    ]

    # Winbox argv uses ASCII Watch name via windows_safe
    win_argv = watcher.build_launch_argv(
        "winbox", sid="abc12345", n_active=1, light=rw.LIGHT_BAD
    )
    assert win_argv[:5] == ["tmux", "new-session", "-d", "-s", "runwatch-winbox"]
    assert win_argv[-2:] == ["-n", "Watch#abc Runs: 1 FAIL"]


# --------------------------------------------------------------------------
# 6. Threshold env overrides (RUN_WATCH_QUIET_S, RUN_WATCH_CLOSE_AFTER_S, RUN_WATCH_BATCH_S)
# --------------------------------------------------------------------------

def test_threshold_env_overrides(monkeypatch, tmp_path: Path):
    assert watcher.quiet_s() == 900
    assert watcher.close_after_s() == 600
    assert watcher.batch_s() == 120

    monkeypatch.setenv("RUN_WATCH_QUIET_S", "300")
    monkeypatch.setenv("RUN_WATCH_CLOSE_AFTER_S", "180")
    monkeypatch.setenv("RUN_WATCH_BATCH_S", "45")

    assert watcher.quiet_s() == 300
    assert watcher.close_after_s() == 180
    assert watcher.batch_s() == 45

    # Quiet threshold at 300s makes a 350s-idle run "quiet" -> 🟡
    tasks = [row("task-q1")]
    probes = stubs(alive={"task-q1"}, logs={"task-q1": NOW - 350})
    runs = rw.collect_runs(tasks, now=NOW, **probes)
    assert rw.compute_light(runs, host="contabo", state_dir=tmp_path) == (1, "\U0001F7E1")

    # Close-after threshold at 180s stops at 180s, not 179s
    assert watcher.decide_lifecycle(0, True, 1, 179, NOW, state_root=tmp_path) == "none"
    assert watcher.decide_lifecycle(0, True, 1, 180, NOW, state_root=tmp_path) == "stop"

    # Follow batch window uses RUN_WATCH_BATCH_S=45
    follower = rw.Follower()
    assert follower.batch_s == 45


# --------------------------------------------------------------------------
# 7. Role and skill files (not wired, shape & line bounds)
# --------------------------------------------------------------------------

def test_role_and_skill_files_exist_and_match_contract():
    role_path = watcher.ROOT / "roles" / "run_watch.md"
    assert role_path.exists()
    role_lines = role_path.read_text(encoding="utf-8").splitlines()
    assert 1 <= len(role_lines) <= 40
    role_text = "\n".join(role_lines)
    assert "tools/run_watch.py" in role_text
    assert "3 lines" in role_text

    skill_path = (
        watcher.ROOT / ".claude" / "skills" / "CTO_Procedure_RunWatch" / "SKILL.md"
    )
    assert skill_path.exists()
    skill_text = skill_path.read_text(encoding="utf-8")
    assert skill_text.startswith("---\nname: CTO_Procedure_RunWatch\n")
    for required in (
        "มีอะไรรันอยู่",
        "status",
        "งาน X ถึงไหน",
        "tail X",
        "อะไรพัง",
        "status --bad",
        "ตอบได้แค่สถานะงาน ถาม PH/CTO",
    ):
        assert required in skill_text


def test_launch_argv_takes_an_absolute_claude_path():
    argv = watcher.build_launch_argv("contabo", claude_bin="/root/.local/bin/claude")
    assert "/root/.local/bin/claude" in argv and "claude" not in argv
