"""Tests for lib.reflect.

Run:  pytest lib/test_reflect.py   (or: python -m lib.test_reflect)
Smoke tests over a throwaway tmp_path DB (see lib/test_recall.py — same
GH #56 isolation fix) seeded with one merged task and one failed task, plus
shape/contract checks. Under plain `python -m lib.test_reflect` (no pytest
fixtures) this still reads whatever real DB is on this machine, unchanged.
"""
from __future__ import annotations

import pytest

from . import db as db_mod
from . import reflect as rf


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    # owner_cto="test" below is a synthetic id with no c_level_sessions row —
    # this suite tests reflect(), not the charter gate, so skip it here.
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    done_id = db_mod.create_task(
        project="test-proj", role="developer",
        title="ship the leaderboard", description="d", owner_cto="test",
    )
    db_mod.update_status(done_id, "done", branch="agent/x", report="shipped")
    open_id = db_mod.create_task(
        project="test-proj", role="developer",
        title="fix the flaky deploy", description="d", owner_cto="test",
    )
    db_mod.update_status(open_id, "failed")


def _check(name: str, cond: bool) -> bool:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return cond


def test_shape() -> bool:
    d = rf.reflect(days=3650)
    ok = True
    ok &= _check("has all keys",
                 {"window_days", "since", "tasks_touched", "by_project",
                  "merged", "concerns", "recurring_failures"} <= set(d))
    ok &= _check("tasks_touched is int >=0",
                 isinstance(d["tasks_touched"], int) and d["tasks_touched"] >= 0)
    ok &= _check("merged is list", isinstance(d["merged"], list))
    ok &= _check("merged capped at 10", len(d["merged"]) <= 10)
    ok &= _check("by_project is dict", isinstance(d["by_project"], dict))
    ok &= _check("recurring_failures is dict",
                 isinstance(d["recurring_failures"], dict))
    if d["merged"]:
        ok &= _check("merged item has keys",
                     {"task_id", "project", "title", "outcome"} <= set(d["merged"][0]))
    return ok


def test_window() -> bool:
    wide = rf.reflect(days=3650)["tasks_touched"]
    narrow = rf.reflect(days=0)["tasks_touched"]
    ok = True
    ok &= _check("narrow window <= wide window", narrow <= wide)
    ok &= _check("by_project counts sum to tasks_touched",
                 sum(rf.reflect(days=3650)["by_project"].values()) == wide)
    return ok


def test_project_filter() -> bool:
    d = rf.reflect(days=3650)
    if not d["by_project"]:
        return _check("no data to filter (skipped)", True)
    proj = max(d["by_project"], key=d["by_project"].get)
    scoped = rf.reflect(days=3650, project=proj)
    ok = True
    ok &= _check("scoped by_project only that project",
                 set(scoped["by_project"]) <= {proj})
    ok &= _check("scoped count <= total", scoped["tasks_touched"] <= d["tasks_touched"])
    return ok


def test_text() -> bool:
    txt = rf.reflect_text(days=30)
    ok = True
    ok &= _check("text has header", txt.startswith("org reflect"))
    ok &= _check("text mentions failures line", "recurring failures:" in txt)
    return ok


def main() -> int:
    suites = [test_shape, test_window, test_project_filter, test_text]
    all_ok = True
    for s in suites:
        print(f"{s.__name__}:")
        all_ok &= s()
    print("\n" + ("ALL PASS" if all_ok else "SOME FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
