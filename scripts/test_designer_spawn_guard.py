"""Guard: web_designer spawns must carry Project ID + design-source path.

CEO 2026-06-04. The org web_designer works in a worktree that omits the
gitignored claudesign .od/, so a project ID alone can't resolve. This test
covers the lib.db guard + resolver + kickoff enrichment.

Run: .venv/bin/python scripts/test_designer_spawn_guard.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import db  # noqa: E402

ID = "7b4becb9-65dd-4b89-b15f-b7b0ec35c607"
SRC = f"/Users/gob/Projects/mooniex-claudesign/.od/projects/{ID}/"


def expect_raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} but none raised")


# 1-4. Pure validation (no DB).
expect_raises(lambda: db.validate_designer_context("web_designer", "build the example page"))
expect_raises(lambda: db.validate_designer_context("web_designer", f"Project {ID} build it"))  # no .od path
expect_raises(lambda: db.validate_designer_context("web_designer", "see .od/projects/foo/ build"))  # no UUID
db.validate_designer_context("web_designer", f"Project ({ID}) ref {SRC} build")  # both → ok
db.validate_designer_context("developer", "anything")  # other roles never gated
db.validate_designer_context("tester", "")
print("guard validation: PASS")

# 5. create_task integration against a throwaway DB (never touch the real queue).
orig = db.DB_PATH
try:
    db.DB_PATH = Path(tempfile.mkdtemp()) / "t.db"
    db.init()
    expect_raises(lambda: db.create_task("mooniex-webapp", "web_designer", "t", "no design context"))
    tid = db.create_task("mooniex-webapp", "web_designer", "t", f"Project ({ID}) ref {SRC}")
    assert tid.startswith("task-"), tid
    tid2 = db.create_task("mooniex-webapp", "developer", "t", "plain dev task, no ctx needed")
    assert tid2.startswith("task-"), tid2
    print("create_task guard: PASS")
finally:
    db.DB_PATH = orig

# 6-7. Resolver + kickoff suffix against the real local .od (skip if absent).
info = db.resolve_od_project(ID)
if info is None:
    print("resolve_od_project: SKIP (.od/app.sqlite not present on this machine)")
    print("kickoff suffix: SKIP")
else:
    assert info["name"], "name should resolve"
    assert info["skill"] == "blog-post", f"unexpected skill: {info['skill']}"
    print(f"resolve_od_project: PASS (name={info['name']} skill={info['skill']})")
    suf = db.designer_kickoff_suffix(f"Project ({ID}) ref {SRC}")
    assert "[design]" in suf and ID in suf and "READ-ONLY" in suf, suf
    assert db.designer_kickoff_suffix("no uuid here") == "", "no UUID → empty suffix"
    print("kickoff suffix: PASS")

print("ALL PASS")
