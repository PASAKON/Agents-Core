"""Tests for lib.reflect. Plain-script style (no pytest dependency).

Run:  python -m lib.test_reflect
Read-only smoke tests over the live tasks.db plus shape/contract checks.
"""
from __future__ import annotations

from . import reflect as rf


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
