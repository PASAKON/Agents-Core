"""Runner skill statistics use only temporary databases and explicit config."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import model_stats, route
from tools.model_stats import RunnerStat, compute_stats, compute_stats_by_class, skill_scores


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "tasks.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE tasks (id TEXT, role TEXT, status TEXT, iteration INTEGER, runner TEXT)")
        conn.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?)", [
            ("t1", "developer", "done", 0, "agy"),
            ("t2", "developer", "done", 1, "agy"),
            ("t3", "developer", "failed", 0, "agy"),
            ("t4", "developer", "cancelled", 0, "agy"),
            ("t5", "tester", "merged", 0, None),
            ("t6", "tester", "done", 0, "claude"),
            ("t7", "developer", "review", 0, "codex"),
        ])
        conn.commit()
    before = path.read_bytes()
    yield path
    assert path.read_bytes() == before


@pytest.fixture
def cfg():
    return {"roles": {
        "dev_general": ["agy:gemini-3.8-flash-high", "claude:claude-sonnet-5"],
        "complex": ["codex:astra:xhigh"],
    }}


def test_compute_stats(db):
    stats = compute_stats(db)
    assert stats == {
        "agy": RunnerStat("agy", "*", 3, 2, 1, 1 / 3, 0.5),
        "claude": RunnerStat("claude", "*", 2, 2, 0, 0.0, 1.0),
    }
    assert "codex" not in stats
    assert compute_stats(db, task_class="tester") == {
        "claude": RunnerStat("claude", "tester", 2, 2, 0, 0.0, 1.0),
    }
    assert compute_stats(db, task_class="missing") == {}


def test_compute_stats_by_class(db):
    assert compute_stats_by_class(db) == {
        ("agy", "developer"): RunnerStat("agy", "developer", 3, 2, 1, 1 / 3, 0.5),
        ("claude", "tester"): RunnerStat("claude", "tester", 2, 2, 0, 0.0, 1.0),
    }


def test_skill_scores(db, cfg):
    assert skill_scores(db, cfg) == {
        ("agy", "gemini-3.8-flash-high"): (0.5, 3),
        ("claude", "claude-sonnet-5"): (1.0, 2),
    }
    cfg["roles"]["extra"] = ["agy:another:xhigh"]
    assert skill_scores(db, cfg)["agy", "another"] == (0.5, 3)
    assert skill_scores(db, cfg, task_class="tester") == {
        ("claude", "claude-sonnet-5"): (1.0, 2),
    }


def test_missing_db_is_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        compute_stats(path)
    assert not path.exists()


def test_load_skill_scores_failure(monkeypatch, cfg):
    monkeypatch.setattr(route, "load_plans", lambda: cfg)
    calls = []

    def fail(db_path, plans_cfg):
        calls.append((db_path, plans_cfg))
        raise RuntimeError("stats unavailable")

    monkeypatch.setattr(model_stats, "skill_scores", fail)
    assert route.load_skill_scores() == {}
    assert calls == [(ROOT / "state" / "tasks.db", cfg)]


def test_load_skill_scores_success(monkeypatch, tmp_path, db, cfg):
    # Redirect the router's repository root to the fixture DB's parent.
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "tasks.db").write_bytes(db.read_bytes())
    monkeypatch.setattr(route, "ROOT", tmp_path)
    monkeypatch.setattr(route, "load_plans", lambda: cfg)
    assert route.load_skill_scores() == skill_scores(db, cfg)


@pytest.mark.parametrize("by_class", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
def test_cli(db, by_class, json_output):
    cmd = [sys.executable, str(ROOT / "tools" / "model_stats.py"), "--db", str(db)]
    if by_class:
        cmd.append("--by-class")
    if json_output:
        cmd.append("--json")
    output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    role = "developer" if by_class else "*"
    if json_output:
        rows = json.loads(output)
        assert len(rows) == 2
        assert rows[0] == {
            "runner": "agy", "task_class": role, "n": 3, "passed": 2,
            "failed": 1, "mean_iteration": 1 / 3, "score": 0.5,
        }
    else:
        assert output.splitlines() == [
            f"agy {role} n=3 pass=2 fail=1 mean_iter=0.3333 score=0.5000",
            f"claude {'tester' if by_class else '*'} n=2 pass=2 fail=0 mean_iter=0.0000 score=1.0000",
        ]
