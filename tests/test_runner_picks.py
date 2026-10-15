"""Per-model stats and the picks table read reviewers' verdicts from runner_fit events."""
import json

import pytest

from lib import db
from tools import route, runner_fit
from tools.model_stats import compute_stats, skill_scores
from tools.runner_picks import build_table


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "tasks.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db.init()
    return path


def _task(model, *, job="code", result="pass", why="good", iteration=0):
    task_id = db.create_task(project="mooniex-agents", role="developer",
                             title="test", description="test", owner_cto="test-owner")
    db.set_fields(task_id, runner="codex", runner_model=model, iteration=iteration)
    db.update_status(task_id, "done")
    payload = runner_fit.build(runner="codex", model=model, job_type=job, result=result,
                               why=why, iteration=iteration,
                               fail_reason="wrong" if result == "fail" else None)
    with db.get_conn() as conn:
        runner_fit.record(conn, task_id, "test", payload)
    return task_id


def test_stats_keep_models_separate_and_read_first_pass(ledger):
    _task("sol:xhigh")
    _task("sol:xhigh", result="redo", iteration=1)
    _task("astra:xhigh")
    stats = compute_stats(ledger)
    assert stats["codex", "sol:xhigh"].n == 2
    assert stats["codex", "sol:xhigh"].first_pass_rate == 0.5
    assert stats["codex", "astra:xhigh"].first_pass_rate == 1.0
    scores = skill_scores(ledger, {"roles": {"dev": ["codex:sol:xhigh", "codex:astra:xhigh"]}})
    assert set(scores) == {("codex", "sol:xhigh"), ("codex", "astra:xhigh")}
    assert route.rank("dev", {}, scores, cfg={"roles": {"dev": ["codex:sol:xhigh"]}})[0].model == "sol:xhigh"
    assert route.rank("default", {}, {}, cfg={"roles": {"default": ["codex:"]}})[0].model == "gpt-6-astra:default"


def test_a_task_without_a_review_has_no_first_pass(ledger):
    task_id = db.create_task(project="mooniex-agents", role="developer",
                             title="t", description="t", owner_cto="test-owner")
    db.set_fields(task_id, runner="codex", runner_model="sol:high")
    db.update_status(task_id, "done")
    assert compute_stats(ledger)["codex", "sol:high"].first_pass_rate is None


def test_picks_table_hides_cells_under_three_runs(ledger):
    for _ in range(2):
        _task("sol:xhigh", job="review")
    for i in range(3):
        _task("astra:high", job="code", why=f"run {i} | ok", result="pass" if i else "redo",
              iteration=0 if i else 1)
    table = build_table(ledger)
    assert "| review | codex:sol:xhigh | 2 | — | — | — |" in table
    row = next(l for l in table.splitlines() if "codex:astra:high" in l)
    assert "| 3 | 2/1/0 | 2/3 |" in row and "run 2 \\| ok" in row
