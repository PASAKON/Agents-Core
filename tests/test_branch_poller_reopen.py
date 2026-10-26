"""Round freshness against the same local Git/database fakes as multihost."""
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from test_multihost import _git, _insert_remote_task, fake_origin, temp_db
from runners import branch_poller as poller


START = 1_800_000_000


@pytest.mark.parametrize("kind", ["REPORT", "BLOCKER"])
@pytest.mark.parametrize("layout", ["root", "docs"])
@pytest.mark.parametrize("runner", ["codex", "agy"])
@pytest.mark.parametrize("case", ["old", "new", "first", "missing", "invalid"])
def test_round_freshness(fake_origin, temp_db, monkeypatch, kind, layout, runner, case):
    task_id = "task-reopen01"
    monkeypatch.setattr(poller, "_STALE_FILE_ROUNDS", {})
    branch = f"agent/{runner}-{task_id}"
    path = f"{kind}.md"
    if layout == "docs":
        path = f"docs/reports/{task_id}/{path}"
        (fake_origin.remote_worker / path).parent.mkdir(parents=True)
    content = f"# {kind} {task_id}\nRound result\n"
    commit_time = START - 60 if case in ("old", "missing", "invalid") else START + 60
    initial_content = content + "Previous round\n" if case == "new" else content
    initial_time = START - 60 if case == "new" else commit_time
    fake_origin.push_branch(branch, {path: initial_content},
                            committer_date=f"{initial_time} +0000")
    if case == "new":
        _git(fake_origin.remote_worker, "checkout", branch)
        (fake_origin.remote_worker / path).write_text(content)
        with monkeypatch.context() as commit_env:
            commit_env.setenv("GIT_AUTHOR_DATE", f"{commit_time} +0000")
            commit_env.setenv("GIT_COMMITTER_DATE", f"{commit_time} +0000")
            _git(fake_origin.remote_worker, "commit", "-am", "current round result")
        _git(fake_origin.remote_worker, "push", "origin", branch)
    # A newer unrelated commit must not make an old result current.
    if case == "old":
        _git(fake_origin.remote_worker, "checkout", branch)
        _git(fake_origin.remote_worker, "commit", "--allow-empty", "-m", "still working")
        _git(fake_origin.remote_worker, "push", "origin", branch)

    _insert_remote_task(temp_db, task_id=task_id, branch=branch,
                        host="winbox", project="fake-proj", pid=999)
    spawned_at = datetime.fromtimestamp(START, timezone.utc).isoformat()
    if case == "missing":
        spawned_at = None
    elif case == "invalid":
        spawned_at = "not a timestamp"
    temp_db.set_fields(task_id, runner=runner, spawned_at=spawned_at)
    monkeypatch.setattr(poller, "get_project", lambda key: {"path": str(fake_origin.work)})
    monkeypatch.setattr(poller, "_publish_via_mesh", lambda task: None)
    monkeypatch.setattr(poller, "_maybe_close_finished_remote_worker", lambda *a: None)
    gate_result = Mock(reasons=["passed"])
    # False means the still-running external runner would be failed by the old poller.
    gate = Mock(return_value=gate_result)
    if case == "old":
        class Refused:
            reasons = ["no turn.completed"]

            def __bool__(self):
                return False
        gate.return_value = Refused()
    monkeypatch.setattr(poller, "_artefact_gate_for_external_runner", gate)
    issue = Mock(return_value="https://example.test/issues/1")
    monkeypatch.setattr(poller, "open_blocker_issue", issue)
    logger = Mock()
    monkeypatch.setattr(poller, "_log", lambda: logger)

    poller.check_task(temp_db.get_task(task_id))
    expected = "in_progress" if case == "old" else ("review" if kind == "REPORT" else "blocked_human")
    assert temp_db.get_task(task_id)["status"] == expected
    if case == "old":
        poller.check_task(temp_db.get_task(task_id))
        gate.assert_not_called()
        issue.assert_not_called()
        assert logger.info.call_count == 1
        # A new round gets its own single diagnostic.
        temp_db.set_fields(task_id, spawned_at=datetime.fromtimestamp(START + 1, timezone.utc).isoformat())
        poller.check_task(temp_db.get_task(task_id))
        assert logger.info.call_count == 2
    elif kind == "REPORT":
        gate.assert_called_once()
        assert temp_db.get_task(task_id)["report"] == content
    else:
        issue.assert_called_once_with(task_id, "Round result", content)
