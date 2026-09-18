"""Tests for scripts/hub/cutover_gate.py (task-7ad6ad8a).

Covers the four cases from the task brief. `_pid_alive`/`_pid_matches_task`
are stubbed on the module -- no real pid or process is ever touched, and
`classify_tasks` takes plain dicts, so the real DB is never touched either.
"""
from __future__ import annotations

from scripts.hub import cutover_gate


def _row(*, status: str, pid: int | None = None, task_id: str = "task-aaaaaaaa"):
    return {"id": task_id, "status": status, "role": "developer",
            "title": "test", "pid": pid}


def test_review_with_dead_pid_is_stale_not_refused(monkeypatch):
    monkeypatch.setattr(cutover_gate, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(cutover_gate, "_pid_matches_task",
                        lambda pid, tid: (_ for _ in ()).throw(
                            AssertionError("must not be called when pid is dead")))
    live, stale = cutover_gate.classify_tasks(
        [_row(status="review", pid=12345)])
    assert live == []
    assert stale == 1


def test_review_with_alive_matching_pid_is_refused(monkeypatch):
    monkeypatch.setattr(cutover_gate, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(cutover_gate, "_pid_matches_task",
                        lambda pid, tid: True)
    row = _row(status="review", pid=12345)
    live, stale = cutover_gate.classify_tasks([row])
    assert live == [row]
    assert stale == 0


def test_review_with_alive_recycled_pid_is_not_refused(monkeypatch):
    """Alive pid that does NOT match this task (recycled onto something
    else) -- not in-flight, same as a dead pid."""
    monkeypatch.setattr(cutover_gate, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(cutover_gate, "_pid_matches_task",
                        lambda pid, tid: False)
    live, stale = cutover_gate.classify_tasks(
        [_row(status="review", pid=12345)])
    assert live == []
    assert stale == 1


def test_in_progress_is_always_refused(monkeypatch):
    monkeypatch.setattr(cutover_gate, "_pid_alive",
                        lambda pid: (_ for _ in ()).throw(
                            AssertionError("in_progress must not check pid")))
    monkeypatch.setattr(cutover_gate, "_pid_matches_task",
                        lambda pid, tid: (_ for _ in ()).throw(
                            AssertionError("in_progress must not check pid")))
    row = _row(status="in_progress", pid=None)
    live, stale = cutover_gate.classify_tasks([row])
    assert live == [row]
    assert stale == 0


def test_review_without_pid_is_neither_live_nor_stale(monkeypatch):
    monkeypatch.setattr(cutover_gate, "_pid_alive",
                        lambda pid: (_ for _ in ()).throw(
                            AssertionError("no pid to check")))
    live, stale = cutover_gate.classify_tasks([_row(status="review", pid=None)])
    assert live == []
    assert stale == 0


def test_mixed_rows_split_correctly(monkeypatch):
    monkeypatch.setattr(cutover_gate, "_pid_alive", lambda pid: pid == 111)
    monkeypatch.setattr(cutover_gate, "_pid_matches_task",
                        lambda pid, tid: pid == 111)
    rows = [
        _row(status="in_progress", task_id="task-11111111"),
        _row(status="review", pid=111, task_id="task-22222222"),
        _row(status="review", pid=999, task_id="task-33333333"),
        _row(status="done", task_id="task-44444444"),
    ]
    live, stale = cutover_gate.classify_tasks(rows)
    assert [r["id"] for r in live] == ["task-11111111", "task-22222222"]
    assert stale == 1
