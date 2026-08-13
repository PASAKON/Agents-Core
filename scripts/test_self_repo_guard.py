"""Tests for the self_repo_guard PreToolUse hook (ADR 0020).

Proves the decision table in scripts/hook-self-repo-guard.py:

  cwd not in a DEV worktree              -> inert (allow, silent)
  protected path, NOT in touches         -> refuse
  protected path, IS in touches          -> allow
  unprotected path                       -> allow
  path escaping into the parent checkout -> refuse, touches cannot override
  cannot decide (no db / no row / bad task id / bad payload) -> refuse

WHAT THE BASH INSPECTION DOES NOT CATCH — asserted here on purpose, so the
gaps stay visible in test output instead of being assumed away:
  - writes performed by an interpreter (`python -c`, `python script.py`,
    `node -e`) — any write whose path only exists inside the program
  - paths built from shell variables or command substitution
    (`rm -rf "$DIR"`, `rm -rf $(cat f)`)
  - `find ... -delete` / `find ... -exec rm {} +`
  - `xargs rm`, and anything else where the destructive verb is not the first
    word of its segment
  - `rsync --delete`, `perl -pi`, `patch`, editors, `chmod`/`chown`
  - alias/function indirection, `eval`, base64-encoded commands

Run standalone:   python scripts/test_self_repo_guard.py
Or under pytest:  pytest scripts/test_self_repo_guard.py
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "hook_self_repo_guard", ROOT / "scripts" / "hook-self-repo-guard.py")
assert _SPEC is not None and _SPEC.loader is not None
guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guard)

TASK = "task-aaaaaaaa"


# --------------------------------------------------------------------------
# fixtures — everything lives under tmp_path. The real state/tasks.db,
# state/locks/ and output/ are never opened by this module.
# --------------------------------------------------------------------------

def _make_worktree(tmp_path: Path, touches=("output/notes.md",),
                   with_db: bool = True) -> tuple[Path, Path]:
    """Build <tmp>/Agents/{state/tasks.db, worktrees/mooniex-agents__developer__<task>}."""
    checkout = tmp_path / "Agents"
    wt = checkout / "worktrees" / f"mooniex-agents__developer__{TASK}"
    for d in ("lib", "runners", "tools", "policies", "config", "scripts",
              "state/locks", "output", ".claude", ".venv/bin"):
        (wt / d).mkdir(parents=True, exist_ok=True)
    (checkout / "state").mkdir(parents=True, exist_ok=True)
    (checkout / "lib").mkdir(parents=True, exist_ok=True)
    if with_db:
        conn = sqlite3.connect(checkout / "state" / "tasks.db")
        conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, touches TEXT)")
        conn.execute("INSERT INTO tasks (id, touches) VALUES (?,?)",
                     (TASK, json.dumps(list(touches))))
        conn.commit()
        conn.close()
    return checkout, wt


def _edit(path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


def _write(path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}


def _bash(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def _decide(event: dict, wt: Path, **kw):
    return guard.decide(event, cwd=str(wt), **kw)


# --------------------------------------------------------------------------
# trigger condition
# --------------------------------------------------------------------------

def test_inert_outside_a_dev_worktree(tmp_path: Path) -> None:
    """A C-level session in the repo root is not affected at all."""
    checkout, _ = _make_worktree(tmp_path)
    for event in (_edit(str(checkout / "lib" / "db.py")),
                  _bash("rm -rf lib/"),
                  _write("lib/db.py")):
        code, msg = guard.decide(event, cwd=str(checkout))
        assert code == 0, f"should be inert outside a worktree, got {code}: {msg}"
        assert msg == ""


def test_inert_for_tools_it_does_not_watch(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path)
    code, _ = _decide({"tool_name": "Read",
                       "tool_input": {"file_path": "lib/db.py"}}, wt)
    assert code == 0


# --------------------------------------------------------------------------
# protected vs declared
# --------------------------------------------------------------------------

def test_protected_not_in_touches_refuses(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("output/notes.md",))
    for path in ("lib/db.py", "runners/watchdog.py", "tools/git_ops.py",
                 "policies/permissions.md", "config/projects.yaml",
                 ".claude/settings.json", "state/tasks.db",
                 "state/locks/x.topic", "scripts/hook-browser-guard.py",
                 ".venv/bin/python"):
        code, msg = _decide(_edit(path), wt)
        assert code == 2, f"{path} should be refused, got {code}"
        assert "self_repo_guard" in msg and "touches" in msg
        assert path.split("/")[0] in msg


def test_protected_in_touches_allows(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("lib/db.py",))
    code, msg = _decide(_edit("lib/db.py"), wt)
    assert code == 0, f"declared path must pass, got {code}: {msg}"
    code, _ = _decide(_edit("lib/config.py"), wt)
    assert code == 2, "an undeclared sibling must still be refused"


def test_touches_directory_prefix_covers_children(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("lib/",))
    code, msg = _decide(_write("lib/deep/nested/new.py"), wt)
    assert code == 0, f"declared dir prefix must cover children, got {msg}"


def test_touches_glob_covers_match(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("scripts/hook-*.py",))
    code, msg = _decide(_write("scripts/hook-self-repo-guard.py"), wt)
    assert code == 0, f"declared glob must cover the match, got {msg}"


def test_unprotected_path_allows(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=())
    for path in ("output/report.md", "README.md", "docs/x.md",
                 "scripts/test_something.py", str(tmp_path / "scratch.txt")):
        code, msg = _decide(_write(path), wt)
        assert code == 0, f"{path} is not load-bearing, got {code}: {msg}"


def test_absolute_path_inside_worktree_is_classified(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=())
    code, _ = _decide(_edit(str(wt / "lib" / "db.py")), wt)
    assert code == 2, "an absolute path into lib/ must be refused too"


# --------------------------------------------------------------------------
# escaping the worktree
# --------------------------------------------------------------------------

def test_escape_to_parent_checkout_refuses_even_when_declared(tmp_path: Path) -> None:
    """`touches` is worktree-relative; it can never license the live checkout."""
    checkout, wt = _make_worktree(tmp_path, touches=("lib/", "lib/db.py"))
    code, msg = _decide(_edit("../../lib/db.py"), wt)
    assert code == 2, "writing into the parent checkout must always refuse"
    assert "OUTSIDE this worktree" in msg
    code, msg = _decide(_edit(str(checkout / "lib" / "db.py")), wt)
    assert code == 2 and "OUTSIDE this worktree" in msg


def test_symlink_out_of_the_worktree_refuses(tmp_path: Path) -> None:
    """A real worktree's .env is a symlink to the checkout's secrets file."""
    checkout, wt = _make_worktree(tmp_path, touches=(".env",))
    (checkout / ".env").write_text("REDACTED=***\n")
    (wt / ".env").symlink_to(checkout / ".env")
    code, msg = _decide(_edit(".env"), wt)
    assert code == 2, "a symlink escaping the worktree must refuse"
    assert "OUTSIDE this worktree" in msg


def test_writes_far_outside_are_left_alone(tmp_path: Path) -> None:
    """Scratchpads stay usable — the guard is about the runtime, not the disk."""
    _, wt = _make_worktree(tmp_path, touches=())
    code, msg = _decide(_write(str(tmp_path / "scratch" / "note.md")), wt)
    assert code == 0, f"scratch writes must pass, got {msg}"


# --------------------------------------------------------------------------
# bash inspection
# --------------------------------------------------------------------------

def test_bash_destructive_forms_refuse(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("output/notes.md",))
    cases = [
        "rm -rf lib/",
        "rm -rf lib/*",
        "rm lib/db.py runners/watchdog.py",
        "cd /tmp; rm -rf lib/",
        "mv lib/db.py /tmp/db.py",
        "echo broken > lib/db.py",
        "echo more >> config/projects.yaml",
        "echo x | tee tools/git_ops.py",
        "sed -i '' 's/a/b/' tools/git_ops.py",
        "sed -i.bak s/a/b/ policies/permissions.md",
        "truncate -s 0 state/tasks.db",
        "git checkout -- lib/db.py",
        "git clean -fdx",
        "git reset --hard origin/main",
        "git checkout -- .",
        "dd if=/dev/zero of=state/tasks.db",
        "rm -rf .venv",
        "rm -rf ../../lib",
        "sudo rm -rf tools/",
        "FOO=bar rm -rf lib/",
    ]
    for cmd in cases:
        code, msg = _decide(_bash(cmd), wt)
        assert code == 2, f"should refuse: {cmd!r} (got {code})"
        assert "self_repo_guard" in msg


def test_bash_harmless_forms_allow(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("output/notes.md",))
    cases = [
        "cat lib/db.py",
        "grep -rn touches lib/",
        "ls -la tools/",
        "git status",
        "git add -A && git commit -m 'x'",
        "python scripts/test_self_repo_guard.py",
        "rm -rf output/tmp",
        "echo hi > output/notes.md",
        "pytest -q 2>&1 | tail -5",
        "git diff main...HEAD --stat",
    ]
    for cmd in cases:
        code, msg = _decide(_bash(cmd), wt)
        assert code == 0, f"should allow: {cmd!r} (got {code}: {msg})"


def test_bash_declared_path_allows(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("lib/",))
    code, msg = _decide(_bash("rm -rf lib/stale.py"), wt)
    assert code == 0, f"declared dir must allow the rm, got {msg}"


def test_known_gaps_are_not_caught(tmp_path: Path) -> None:
    """Documented blind spots. If one of these starts failing the guard got
    better, and the report's 'not caught' list must be updated to match."""
    _, wt = _make_worktree(tmp_path, touches=())
    uncaught = [
        "python -c \"open('lib/db.py','w').write('')\"",
        "python scripts/wipe_it.py",
        "DIR=lib; rm -rf \"$DIR\"",
        "rm -rf $(echo lib)",
        "find lib -name '*.py' -delete",
        "find lib -name '*.py' -exec rm {} +",
        "ls lib | xargs rm",
        "rsync -a --delete /tmp/empty/ lib/",
        "perl -pi -e 's/a/b/' lib/db.py",
    ]
    for cmd in uncaught:
        code, _ = _decide(_bash(cmd), wt)
        assert code == 0, f"unexpectedly caught {cmd!r} — update the gap list"


# --------------------------------------------------------------------------
# fail closed
# --------------------------------------------------------------------------

def test_db_missing_refuses(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, with_db=False)
    code, msg = _decide(_edit("lib/db.py"), wt)
    assert code == 2 and "could not decide" in msg
    assert "tasks.db not found" in msg


def test_db_unreadable_refuses(tmp_path: Path) -> None:
    checkout, wt = _make_worktree(tmp_path)
    (checkout / "state" / "tasks.db").write_bytes(b"not a database at all")
    code, msg = _decide(_edit("lib/db.py"), wt)
    assert code == 2 and "could not decide" in msg


def test_task_row_missing_refuses(tmp_path: Path) -> None:
    checkout, wt = _make_worktree(tmp_path)
    conn = sqlite3.connect(checkout / "state" / "tasks.db")
    conn.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()
    code, msg = _decide(_edit("lib/db.py"), wt)
    assert code == 2 and "no task row" in msg


def test_unparseable_task_id_refuses(tmp_path: Path) -> None:
    checkout = tmp_path / "Agents"
    wt = checkout / "worktrees" / "mooniex-agents__developer__nope"
    (wt / "lib").mkdir(parents=True)
    code, msg = _decide(_edit("lib/db.py"), wt)
    assert code == 2 and "does not end in a task id" in msg


def test_malformed_payload_refuses(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path)
    code, msg = _decide({}, wt, payload_ok=False)
    assert code == 2 and "not readable JSON" in msg


def test_missing_tool_input_refuses(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path)
    code, msg = _decide({"tool_name": "Edit"}, wt)
    assert code == 2 and "no readable tool_input" in msg
    code, msg = _decide({"tool_name": "Bash", "tool_input": {}}, wt)
    assert code == 2 and "no command string" in msg


def test_refusal_message_names_path_reason_and_fix(tmp_path: Path) -> None:
    _, wt = _make_worktree(tmp_path, touches=("output/notes.md",))
    _, msg = _decide(_edit("lib/db.py"), wt)
    assert "lib/db.py" in msg                         # which path
    assert "load-bearing org runtime" in msg          # why protected
    assert "DECLARE THE PATH, NOT TO DISABLE" in msg  # the fix
    assert "output/notes.md" in msg                   # what was declared


# --------------------------------------------------------------------------
# standalone runner (no pytest required)
# --------------------------------------------------------------------------

def main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failures = 0
    for name, fn in tests:
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(Path(td))
                print(f"  [PASS] {name}")
            except Exception:
                failures += 1
                print(f"  [FAIL] {name}")
                traceback.print_exc()
    print(f"\n{len(tests)} tests, "
          f"{'ALL PASS' if failures == 0 else str(failures) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
