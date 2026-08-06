"""Equivalence + wiring proof for lib/org_tools_registry.py (task-78ef13b0).

The registry consolidates the tool registration/wiring (arg parsing,
response formatting, cross-CTO ownership gate, error handling) that
`runners/cto_mcp_server.py` and `runners/cto.py` currently hand-duplicate —
see the registry module's own docstring and
`org:reference/2026-08-06-agents-system-audit.md` (finding W1). This suite
proves the registry's dispatch() is a faithful drop-in for
`runners/cto_mcp_server.py`'s CURRENT behavior (the file both this task and
that audit treat as the "correct" prod path) by calling the real
`cto_mcp_server.py` functions side-by-side with `dispatch()` against the
same isolated state and asserting byte-identical output.

Runs against an isolated temp SQLite DB (never `state/tasks.db`). The four
tools with real subprocess/git/iTerm side effects (delegate_task,
delegate_parallel_tasks, merge_task, revert_task_tool) have their dangerous
leaf call (do_delegate / delegate_parallel / do_merge / revert_task) patched
to an in-memory fake on BOTH the registry and cto_mcp_server.py sides before
calling either — this suite never spawns a real iTerm tab, runs git against
a real repo, or writes a real wiki commit. Their "not found" branch is
exercised UNPATCHED instead (real business logic raises before any
subprocess call), which doubles as the Do-3 error-wrapper proof for those
two tools specifically.

Run via:  python scripts/test_org_tools_registry.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db  # noqa: E402
from lib import org_tools_registry as reg  # noqa: E402
from lib import toon  # noqa: E402
import tools.revert_task as revert_task_mod  # noqa: E402
from runners import cto_mcp_server as srv  # noqa: E402

PROJECT = "mooniex-claudeflow"
ROLE = "developer"
CTO_A = "ctoAAAA1"
CTO_B = "ctoBBBB2"

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _run(coro):
    return asyncio.run(coro)


def _dispatch(name: str, **kwargs) -> str:
    return _run(reg.dispatch(name, **kwargs))


# ---------------------------------------------------------------------------
# 1. Registry shape
# ---------------------------------------------------------------------------

def test_registry_names_match_prod() -> bool:
    expected = {
        "wiki_read", "wiki_list", "wiki_search", "wiki_write", "create_task",
        "check_collisions", "delegate_task", "delegate_parallel_tasks",
        "get_task", "review_diff", "merge_task", "reopen_task",
        "list_projects", "stats", "recall", "reflect", "revert_task_tool",
    }
    names = set(reg.BY_NAME)
    return names == expected and all(callable(getattr(srv, n, None)) for n in names)


# ---------------------------------------------------------------------------
# 2. The point-1 regression: owner_cto stamping
# ---------------------------------------------------------------------------

def test_owner_cto_regression() -> tuple[bool, str | None]:
    """create_task through the registry MUST stamp owner_cto from
    CTO_SESSION_ID — matching cto_mcp_server.py's (correct) behavior, not
    cto.py's t_create_task (which omits owner_cto= entirely)."""
    with mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        os.environ.pop("CXO_SESSION_ID", None)
        os.environ.pop("CXO_ROLE", None)
        tid = _dispatch("create_task", project=PROJECT, role=ROLE,
                        title="owner_cto regression", description="d")
    row = db.get_task(tid)
    ok = bool(row) and row["owner_cto"] == CTO_A
    return ok, tid


# ---------------------------------------------------------------------------
# 3. Read-only / pure tools — direct equivalence against the real srv fn
# ---------------------------------------------------------------------------

def test_wiki_read_equivalence() -> bool:
    expected = srv.wiki_read("org:IRON-RULES.md")
    got = _dispatch("wiki_read", path="org:IRON-RULES.md")
    return got == expected and len(got) > 0


def test_wiki_list_equivalence() -> bool:
    expected = srv.wiki_list("org:decisions")
    got = _dispatch("wiki_list", prefix="org:decisions")
    return got == expected and got.startswith("[")


def test_wiki_search_equivalence() -> bool:
    expected = srv.wiki_search("TOON")
    got = _dispatch("wiki_search", query="TOON")
    return got == expected


def test_wiki_write_equivalence() -> bool:
    """wiki_write is real-git-commit side-effecting — patch the leaf so
    neither side touches the actual wiki repo."""
    import tools.wiki as wiki_mod
    fake = mock.Mock(return_value="wrote fake:path.md (0: )")
    with mock.patch.object(wiki_mod, "wiki_write", fake):
        expected = srv.wiki_write("fake:path.md", "content", "msg")
        got = _dispatch("wiki_write", path="fake:path.md", content="content", message="msg")
    calls_have_role = all(c.kwargs.get("role") == "cto" for c in fake.call_args_list)
    return got == expected == "wrote fake:path.md (0: )" and fake.call_count == 2 and calls_have_role


def test_create_task_equivalence() -> tuple[bool, list[str]]:
    tid_srv = srv.create_task(PROJECT, ROLE, "equiv A", "d",
                              depends_on="", touches='["a/b.py","c/d.py"]')
    tid_reg = _dispatch("create_task", project=PROJECT, role=ROLE,
                        title="equiv B", description="d",
                        depends_on="", touches='["a/b.py","c/d.py"]')
    row_srv = db.get_task(tid_srv)
    row_reg = db.get_task(tid_reg)
    ok = (
        tid_srv.startswith("task-") and tid_reg.startswith("task-")
        and json.loads(row_srv["touches"]) == ["a/b.py", "c/d.py"]
        and json.loads(row_reg["touches"]) == ["a/b.py", "c/d.py"]
    )
    return ok, [tid_srv, tid_reg]


def test_check_collisions_equivalence() -> bool:
    expected = srv.check_collisions(PROJECT, '["a/b.py"]')
    got = _dispatch("check_collisions", project=PROJECT, touches='["a/b.py"]')
    return got == expected and "a/b.py" in got


def test_get_task_equivalence(tid: str) -> bool:
    expected = srv.get_task(tid)
    got = _dispatch("get_task", task_id=tid)
    return got == expected and tid in got


def test_get_task_missing_equivalence() -> bool:
    expected = srv.get_task("task-doesnotexist")
    got = _dispatch("get_task", task_id="task-doesnotexist")
    return got == expected == "null"


def test_review_diff_equivalence() -> bool:
    tid = db.create_task(PROJECT, ROLE, "no worktree", "d", owner_cto=CTO_A)
    expected = srv.review_diff(tid)
    got = _dispatch("review_diff", task_id=tid)
    return got == expected == "no worktree"


def test_list_projects_equivalence() -> bool:
    expected = srv.list_projects()
    got = _dispatch("list_projects")
    return got == expected and PROJECT in got


def test_stats_equivalence() -> bool:
    expected = srv.stats()
    got = _dispatch("stats")
    return got == expected


def test_recall_equivalence() -> bool:
    expected = srv.recall("equiv")
    got = _dispatch("recall", query="equiv")
    return got == expected and "equiv" in got


def test_reflect_equivalence() -> bool:
    expected = srv.reflect(7)
    got = _dispatch("reflect", days=7)
    return got == expected


# ---------------------------------------------------------------------------
# 4. reopen_task — pure DB mutation, safe to call the real srv fn directly
# ---------------------------------------------------------------------------

def test_reopen_task_not_found_equivalence() -> bool:
    expected = srv.reopen_task("task-nope", "fb")
    got = _dispatch("reopen_task", task_id="task-nope", feedback="fb")
    return got == expected == "not found"


def test_reopen_task_foreign_equivalence() -> bool:
    tid = db.create_task(PROJECT, ROLE, "foreign reopen", "d", owner_cto=CTO_B)
    with mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = srv.reopen_task(tid, "fb")
        got = _dispatch("reopen_task", task_id=tid, feedback="fb")
    after = db.get_task(tid)
    return got == expected and "Refusing cross-CTO" in got and after["iteration"] == 0


def test_reopen_task_success_equivalence() -> bool:
    tid_srv = db.create_task(PROJECT, ROLE, "reopen srv", "d", owner_cto=CTO_A)
    tid_reg = db.create_task(PROJECT, ROLE, "reopen reg", "d", owner_cto=CTO_A)
    with mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = srv.reopen_task(tid_srv, "do it better")
        got = _dispatch("reopen_task", task_id=tid_reg, feedback="do it better")
    row_srv = db.get_task(tid_srv)
    row_reg = db.get_task(tid_reg)
    return (
        got == expected == "reopened"
        and row_srv["status"] == row_reg["status"] == "pending"
        and row_srv["iteration"] == row_reg["iteration"] == 1
        and "do it better" in row_srv["description"]
        and "do it better" in row_reg["description"]
    )


# ---------------------------------------------------------------------------
# 5. Side-effecting tools — dangerous leaf patched on BOTH sides
# ---------------------------------------------------------------------------

def test_merge_task_foreign_gate() -> bool:
    tid = db.create_task(PROJECT, ROLE, "foreign merge", "d", owner_cto=CTO_B)
    fake = mock.Mock(return_value={"should": "not be called"})
    with mock.patch.object(srv, "do_merge", fake), \
         mock.patch.object(reg, "do_merge", fake), \
         mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = srv.merge_task(tid)
        got = _dispatch("merge_task", task_id=tid)
    return got == expected and "Refusing cross-CTO" in got and fake.call_count == 0


def test_merge_task_format_equivalence() -> bool:
    tid = db.create_task(PROJECT, ROLE, "merge fmt", "d", owner_cto=CTO_A)
    canned = {"merged": True, "merge_sha": "abc1234", "touches_violation": False}
    fake = mock.Mock(return_value=canned)
    with mock.patch.object(srv, "do_merge", fake), \
         mock.patch.object(reg, "do_merge", fake), \
         mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = srv.merge_task(tid)
        got = _dispatch("merge_task", task_id=tid)
    return got == expected == toon.encode(canned) and fake.call_count == 2


def test_merge_task_not_found_now_caught() -> bool:
    """Do-3, now wired into cto_mcp_server.py too (task-724cff99):
    merge_task's real business logic still raises ValueError for a
    nonexistent task_id before any subprocess call (safe to prove
    unmocked) — but srv.merge_task is now a thin stub over
    dispatch_sync(), so BOTH sides catch it uniformly and return the same
    ERROR string. Neither raises anymore."""
    with mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        got = _dispatch("merge_task", task_id="task-doesnotexist")
        expected = srv.merge_task("task-doesnotexist")
    return got == expected and got.startswith("ERROR:") and "not found" in got


def test_delegate_task_foreign_gate() -> bool:
    tid = db.create_task(PROJECT, ROLE, "foreign delegate", "d", owner_cto=CTO_B)
    fake = mock.AsyncMock(return_value={"should": "not be called"})
    with mock.patch.object(srv, "do_delegate", fake), \
         mock.patch.object(reg, "do_delegate", fake), \
         mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = _run(srv.delegate_task(tid))
        got = _dispatch("delegate_task", task_id=tid)
    return got == expected and "Refusing cross-CTO" in got and fake.await_count == 0


def test_delegate_task_format_equivalence() -> bool:
    tid = db.create_task(PROJECT, ROLE, "delegate fmt", "d", owner_cto=CTO_A)
    canned = {"id": tid, "status": "in_progress"}
    fake = mock.AsyncMock(return_value=canned)
    with mock.patch.object(srv, "do_delegate", fake), \
         mock.patch.object(reg, "do_delegate", fake), \
         mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = _run(srv.delegate_task(tid))
        got = _dispatch("delegate_task", task_id=tid)
    return got == expected == toon.encode(canned)[:6000] and fake.await_count == 2


def test_delegate_task_not_found_now_caught() -> bool:
    """Do-3, now wired into cto_mcp_server.py too (task-724cff99): real
    (unpatched) business logic still raises ValueError before any
    subprocess call for a nonexistent task, so this is safe to run
    un-mocked — but srv.delegate_task is now a thin stub over dispatch(),
    so BOTH sides catch it uniformly. Neither raises anymore."""
    got = _dispatch("delegate_task", task_id="task-doesnotexist")
    expected = _run(srv.delegate_task("task-doesnotexist"))
    return got == expected and got.startswith("ERROR:")


def test_delegate_parallel_tasks_equivalence() -> bool:
    tid1 = db.create_task(PROJECT, ROLE, "par1", "d", owner_cto=CTO_A)
    tid2 = db.create_task(PROJECT, ROLE, "par2", "d", owner_cto=CTO_A)
    canned = [{"id": tid1, "status": "in_progress"}, {"id": tid2, "status": "in_progress"}]
    fake = mock.AsyncMock(return_value=canned)
    ids_json = json.dumps([tid1, tid2])
    with mock.patch.object(srv, "delegate_parallel", fake), \
         mock.patch.object(reg, "delegate_parallel", fake):
        expected = _run(srv.delegate_parallel_tasks(ids_json))
        got = _dispatch("delegate_parallel_tasks", task_ids=ids_json)
    return got == expected == toon.encode(canned)[:8000] and fake.await_count == 2


def test_revert_task_foreign_gate() -> bool:
    tid = db.create_task(PROJECT, ROLE, "foreign revert", "d", owner_cto=CTO_B)
    fake = mock.Mock(return_value={"should": "not be called"})
    with mock.patch.object(revert_task_mod, "revert_task", fake), \
         mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = _run(srv.revert_task_tool(tid))
        got = _dispatch("revert_task_tool", task_id=tid)
    return got == expected and "Refusing cross-CTO" in got and fake.call_count == 0


def test_revert_task_format_equivalence() -> bool:
    tid = db.create_task(PROJECT, ROLE, "revert fmt", "d", owner_cto=CTO_A)
    canned = {"reverted": True, "merge_sha": "abc1234", "revert_sha": "def5678"}
    fake = mock.Mock(return_value=canned)
    with mock.patch.object(revert_task_mod, "revert_task", fake), \
         mock.patch.dict(os.environ, {"CTO_SESSION_ID": CTO_A}):
        expected = _run(srv.revert_task_tool(tid, False))
        got = _dispatch("revert_task_tool", task_id=tid)
    return got == expected == toon.encode(canned)


# ---------------------------------------------------------------------------
# 6. Uniform error wrapper (Do-3) — general case + format parity check
# ---------------------------------------------------------------------------

def test_error_wrapper_catches_previously_uncaught() -> bool:
    """get_task's business logic (db.get_task, shared by both sides) is
    patched to raise a generic fault. Same proof shape as the
    merge_task/delegate_task not-found tests, but via an injected fault so
    it's independent of any particular business-logic branch. Since
    task-724cff99 wired srv.get_task into dispatch_sync(), BOTH sides now
    catch it uniformly and return the identical ERROR string."""
    boom = mock.Mock(side_effect=RuntimeError("boom"))
    with mock.patch.object(db, "get_task", boom):
        got = _dispatch("get_task", task_id="task-anything")
        expected = srv.get_task("task-anything")
    return got == expected == "ERROR: boom"


def test_error_wrapper_format_matches_already_guarded_tool() -> bool:
    """wiki_read already has try/except in cto_mcp_server.py today — confirm
    the new uniform wrapper doesn't change that pre-existing error format."""
    boom = mock.Mock(side_effect=RuntimeError("wiki boom"))
    with mock.patch.object(reg.wiki_tools, "wiki_read", boom):
        expected = srv.wiki_read("org:whatever.md")
        got = _dispatch("wiki_read", path="org:whatever.md")
    return got == expected == "ERROR: wiki boom"


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="org-tools-registry-")
    db.DB_PATH = Path(tmp) / "tasks.db"
    db.init()

    print("== registry shape ==")
    _mark(test_registry_names_match_prod(), "registry has exactly the 17 cto_mcp_server.py tool names")

    print("== owner_cto regression (point 1) ==")
    ok, seed_tid = test_owner_cto_regression()
    _mark(ok, "create_task via registry stamps owner_cto from CTO_SESSION_ID")

    print("== read-only tools: equivalence vs cto_mcp_server.py ==")
    _mark(test_wiki_read_equivalence(), "wiki_read matches (text)")
    _mark(test_wiki_list_equivalence(), "wiki_list matches (toon)")
    _mark(test_wiki_search_equivalence(), "wiki_search matches (toon)")
    _mark(test_wiki_write_equivalence(), "wiki_write matches (text, leaf patched)")

    ok, ids = test_create_task_equivalence()
    _mark(ok, "create_task matches (text task_id, touches parsed)")
    seed_tid2 = ids[0]

    _mark(test_check_collisions_equivalence(), "check_collisions matches (toon)")
    _mark(test_get_task_equivalence(seed_tid2), "get_task matches (toon)")
    _mark(test_get_task_missing_equivalence(), "get_task on missing id matches ('null')")
    _mark(test_review_diff_equivalence(), "review_diff matches ('no worktree')")
    _mark(test_list_projects_equivalence(), "list_projects matches (toon)")
    _mark(test_stats_equivalence(), "stats matches (toon)")
    _mark(test_recall_equivalence(), "recall matches (text)")
    _mark(test_reflect_equivalence(), "reflect matches (text)")

    print("== reopen_task: 3 branches vs cto_mcp_server.py ==")
    _mark(test_reopen_task_not_found_equivalence(), "reopen_task not-found matches")
    _mark(test_reopen_task_foreign_equivalence(), "reopen_task cross-CTO gate matches")
    _mark(test_reopen_task_success_equivalence(), "reopen_task success matches")

    print("== side-effecting tools: leaf patched, both sides compared ==")
    _mark(test_merge_task_foreign_gate(), "merge_task cross-CTO gate matches")
    _mark(test_merge_task_format_equivalence(), "merge_task format matches (toon)")
    _mark(test_merge_task_not_found_now_caught(), "merge_task not-found: dispatch() and srv.merge_task both catch uniformly (Do-3)")
    _mark(test_delegate_task_foreign_gate(), "delegate_task cross-CTO gate matches")
    _mark(test_delegate_task_format_equivalence(), "delegate_task format matches (toon, 6000-cap)")
    _mark(test_delegate_task_not_found_now_caught(), "delegate_task not-found: dispatch() and srv.delegate_task both catch uniformly (Do-3)")
    _mark(test_delegate_parallel_tasks_equivalence(), "delegate_parallel_tasks format matches (toon, 8000-cap)")
    _mark(test_revert_task_foreign_gate(), "revert_task_tool cross-CTO gate matches")
    _mark(test_revert_task_format_equivalence(), "revert_task_tool format matches (toon)")

    print("== uniform error wrapper (Do-3) ==")
    _mark(test_error_wrapper_catches_previously_uncaught(), "get_task fault: dispatch() and srv.get_task both catch uniformly")
    _mark(test_error_wrapper_format_matches_already_guarded_tool(), "wiki_read fault: format unchanged from existing try/except")

    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
