import json
from unittest.mock import Mock

import pytest

from tools import idle_sweep as idle

activity = idle.activity

NOW = 1800000000


@pytest.fixture
def env(tmp_path, monkeypatch):
    (tmp_path / "state/locks").mkdir(parents=True)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr(idle.time, "time", lambda: NOW)
    monkeypatch.setattr(idle, "sessions", lambda: {"cto-test": [("%1", "/project")]})
    monkeypatch.setattr(idle, "ready", lambda panes: True)
    monkeypatch.setattr(idle, "activity", lambda *a: (NOW - 3 * idle.DAY, "project"))
    monkeypatch.setattr(idle, "create_card", Mock(return_value="Q-test"))
    monkeypatch.setattr(idle, "question", Mock(return_value={"status": "pending"}))
    monkeypatch.setattr(idle, "command", Mock(return_value=""))
    monkeypatch.setattr(idle, "notify", Mock())
    return tmp_path


def seed(root, age=0):
    idle.persist(root / "state/idle_sweep.json", {
        "cto-test": {"card_id": "Q-test", "raised_at": NOW - age, "snooze_until": 0}})


def test_young_no_card(env, monkeypatch):
    monkeypatch.setattr(idle, "activity", lambda *a: (NOW - 2 * idle.DAY, "p"))
    idle.sweep(env)
    idle.create_card.assert_not_called()


def test_three_days_one_card(env):
    idle.sweep(env)
    idle.sweep(env)
    idle.create_card.assert_called_once()


def test_continue_snoozes(env):
    seed(env)
    idle.question.return_value = {"status": "answered", "answer": {"choice": 1}}
    idle.sweep(env)
    assert json.loads((env / "state/idle_sweep.json").read_text())["cto-test"]["snooze_until"] == NOW + 3 * idle.DAY
    idle.sweep(env)
    idle.create_card.assert_not_called()


def test_close_saved(env):
    seed(env)
    idle.question.return_value = {"status": "answered", "answer": {"choice": 0}}
    idle.sweep(env)
    assert idle.command.call_args.args[0] == ["bash", str(env / "scripts/session-kill.sh"),
        "--status", "saved", "--note", "idle sweep: CEO Q-test", "cto-test"]
    idle.notify.assert_called_once()
    idle.sweep(env)
    idle.notify.assert_called_once()


def test_seven_days_cancel_force_saved(env):
    seed(env, 7 * idle.DAY)
    idle.sweep(env)
    calls = [c.args[0] for c in idle.command.call_args_list]
    assert calls[0][-2:] == ["cancel", "Q-test"]
    assert "force_saved" in calls[1]


@pytest.mark.parametrize("name", ["sompong", "runwatch-abc", "cto-test"])
def test_protected_or_busy(env, monkeypatch, name):
    monkeypatch.setattr(idle, "sessions", lambda: {name: [("%1", "/p")]})
    if name == "cto-test":
        monkeypatch.setattr(idle, "ready", lambda p: False)
    idle.sweep(env)
    idle.create_card.assert_not_called()


def test_off(env):
    (env / "state/idle_sweep.off").touch()
    idle.sweep(env)
    idle.create_card.assert_not_called()
    idle.command.assert_not_called()


@pytest.mark.parametrize("existing", [False, True])
def test_dry_no_mutations(env, existing):
    if existing:
        seed(env, 7 * idle.DAY)
    before = idle.read(env / "state/idle_sweep.json")
    idle.sweep(env, dry_run=True)
    idle.command.assert_not_called()
    idle.create_card.assert_not_called()
    idle.notify.assert_not_called()
    assert idle.read(env / "state/idle_sweep.json") == before


def test_hour_gate(env, monkeypatch):
    run = Mock()
    monkeypatch.setattr(idle, "sweep", run)
    idle.tick(env)
    idle.tick(env)
    run.assert_called_once_with(env)
    monkeypatch.setattr(idle.time, "time", lambda: NOW + 3600)
    idle.tick(env)
    assert run.call_count == 2


def test_caller_lock(env):
    (env / "state/locks/cto-test.lock").write_text(str(idle.os.getppid()))
    idle.sweep(env)
    idle.create_card.assert_not_called()


def test_caps(env, monkeypatch):
    monkeypatch.setattr(idle, "sessions", lambda: {f"cto-{i}": [(f"%{i}", "/p")] for i in range(10)})
    idle.sweep(env)
    assert idle.create_card.call_count == 5
    idle.persist(env / "state/idle_sweep.json", {f"cto-{i}": {
        "card_id": "Q-test", "raised_at": NOW - 7 * idle.DAY} for i in range(10)})
    idle.sweep(env)
    assert idle.notify.call_count == 3


def test_worker_kill_no_task_mutation(env):
    idle.save_session("mooniex-task-abc", "saved", "note", env)
    idle.command.assert_called_once_with(["tmux", "kill-session", "-t", "=mooniex-task-abc"])


def test_all_panes_must_be_ready(monkeypatch):
    monkeypatch.setattr(idle, "command", Mock(side_effect=["ready", "busy"]))
    monkeypatch.setattr(idle, "prompt_ready", lambda screen: screen == "ready")
    assert not idle.ready([("%1", "/p"), ("%2", "/p")])


def test_untrusted_answer_refused(monkeypatch):
    monkeypatch.setattr(idle.ask_run, "_call", lambda *a: {
        "id": "Q-test", "status": "answered", "answer": {"choice": 0}})
    with pytest.raises(idle.ask_run.HubError):
        idle.question("Q-test")


def test_tmux_inventory_uses_all_panes(monkeypatch):
    run = Mock(return_value=Mock(stdout="cto-a\t%1\t/a\ncto-a\t%2\t/b\n"))
    monkeypatch.setattr(idle.subprocess, "run", run)
    assert idle.sessions() == {"cto-a": [("%1", "/a"), ("%2", "/b")]}
    assert "-a" in run.call_args.args[0]


def test_worker_newest_signal(env, monkeypatch):
    from tools import live_sessions
    from lib import run_liveness
    from datetime import datetime, timezone
    worktree = env / "worker"
    worktree.mkdir()
    log = env / "pane.log"
    log.touch()
    idle.os.utime(log, (NOW - 100, NOW - 100))
    idle.os.utime(worktree, (NOW - 200, NOW - 200))
    task = {"id": "task-abc", "worktree": str(worktree), "project": "p",
            "updated_at": datetime.fromtimestamp(NOW - 50, timezone.utc).isoformat()}
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = task
    monkeypatch.setattr(live_sessions, "_open_hub", lambda: conn)
    monkeypatch.setattr(run_liveness, "log_files", lambda t: [log])
    assert activity("mooniex-task-abc", [("%1", str(worktree))], env) == (NOW - 50, "p")
    conn.close.assert_called_once()


def test_no_signal_skips(env, monkeypatch):
    monkeypatch.setattr(idle, "activity", lambda *a: (None, "p"))
    idle.sweep(env)
    idle.create_card.assert_not_called()


def test_busy_on_recheck_prevents_save(env, monkeypatch):
    seed(env, 7 * idle.DAY)
    monkeypatch.setattr(idle, "ready", Mock(side_effect=[True, False]))
    idle.sweep(env)
    idle.command.assert_not_called()


def test_cancel_failure_prevents_save(env):
    seed(env, 7 * idle.DAY)
    idle.command.side_effect = RuntimeError("hub unavailable")
    idle.sweep(env)
    assert idle.command.call_count == 1
    idle.notify.assert_not_called()


def test_current_session_protected(env, monkeypatch):
    monkeypatch.setenv("TMUX", "socket")
    idle.command.return_value = "cto-test\n"
    idle.sweep(env)
    idle.create_card.assert_not_called()


def test_notice_retried_even_when_last_session_disappears(env, monkeypatch):
    idle.persist(env / "state/idle_sweep.json", {"cto-gone": {
        "saved": NOW, "notice": {"days": 10, "owner": "cxo:cmo:owner"}}})
    monkeypatch.setattr(idle, "sessions", Mock(side_effect=RuntimeError("no tmux server")))
    with pytest.raises(RuntimeError):
        idle.sweep(env)
    idle.notify.assert_called_once_with("cto-gone", 10, "cxo:cmo:owner", env)
    assert "notice" not in json.loads((env / "state/idle_sweep.json").read_text())["cto-gone"]
