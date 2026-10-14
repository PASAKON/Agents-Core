"""Comment recording and read-only pick table against a temporary ledger."""
import json
import sqlite3

import pytest

from lib import db
from tools.runner_comment import write_comment
from tools.runner_picks import build_table
from tools.model_stats import compute_stats, skill_scores
from tools import route


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "tasks.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db.init()
    return path


def _task(model):
    task_id = db.create_task(project="mooniex-agents", role="developer",
                             title="test", description="test", owner_cto="test-owner")
    db.set_fields(task_id, runner="codex", runner_model=model,
                  review=json.dumps({"merge_sha": "abc"}))
    db.update_status(task_id, "done")
    return task_id


def test_comment_validation_and_review_merge(ledger):
    task_id = _task("sol:xhigh")
    with pytest.raises(ValueError, match="unknown kind"):
        write_comment(task_id, kind="trial", first_pass="y", line="good")
    write_comment(task_id, kind="dev_small", first_pass="y", line="good")
    review = json.loads(db.get_task(task_id)["review"])
    assert review["merge_sha"] == "abc"
    assert review["runner_comment"]["line"] == "good"


def test_stats_keep_models_separate(ledger):
    first = _task("sol:xhigh")
    _task("astra:xhigh")
    write_comment(first, kind="dev_small", first_pass="y", line="good")
    stats = compute_stats(ledger)
    assert stats["codex", "sol:xhigh"].n == 1
    assert stats["codex", "astra:xhigh"].first_pass_rate is None
    scores = skill_scores(ledger, {"roles": {"dev": ["codex:sol:xhigh", "codex:astra:xhigh"]}})
    assert set(scores) == {("codex", "sol:xhigh"), ("codex", "astra:xhigh")}
    assert route.rank("dev", {}, scores, cfg={"roles": {"dev": ["codex:sol:xhigh"]}})[0].model == "sol:xhigh"
    assert route.rank("default", {}, {}, cfg={"roles": {"default": ["codex:"]}})[0].model == "gpt-6-astra:default"


def test_picks_hide_cells_with_fewer_than_three_comments(ledger):
    for _ in range(2):
        task_id = _task("sol:xhigh")
        write_comment(task_id, kind="dev_small", first_pass="y", line="good")
    assert "| dev_small | codex:sol:xhigh | — | — | — |" in build_table(ledger)
