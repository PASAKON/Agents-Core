"""The PreToolUse hooks run under the plain `python3` on PATH, not the repo
venv. On the Mac that interpreter has no PyYAML (measured 2026-09-29).

Two regressions this file pins:

1. `lib.db` must import without PyYAML. W0.1 (task-1bfb0389) added a
   module-level `from lib import config`, and `lib.config` needs yaml, so
   every hook that imports `lib.db` crashed at import.
2. `hook-self-repo-guard.py` must refuse, not allow, when it cannot import
   `lib.db`. A crash at import exits 1, which Claude Code treats as
   non-blocking, so the guard silently allowed every write in a worktree.

Each case runs in a subprocess so the import block cannot leak into the rest
of the suite.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "scripts" / "hook-self-repo-guard.py"

_WRITE_EVENT = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.txt"}})


def _run(code: str, *, cwd: Path, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd), input=stdin, capture_output=True, text=True, timeout=60,
    )


def _fake_worktree(tmp_path: Path) -> Path:
    wt = tmp_path / "checkout" / "worktrees" / "mooniex-agents__developer__task-aaaaaaaa"
    wt.mkdir(parents=True)
    return wt


def _guard_with_blocked(module: str) -> str:
    """Run the guard as __main__ with `module` made unimportable."""
    return (
        "import runpy, sys\n"
        f"sys.modules[{module!r}] = None\n"
        f"runpy.run_path({str(HOOK)!r}, run_name='__main__')\n"
    )


def test_lib_db_imports_without_yaml(tmp_path):
    code = (
        "import sys\n"
        "sys.modules['yaml'] = None\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import lib.db\n"
        "print('ok')\n"
    )
    r = _run(code, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"


def test_guard_loads_lib_db_without_yaml(tmp_path):
    code = (
        "import runpy, sys\n"
        "sys.modules['yaml'] = None\n"
        f"g = runpy.run_path({str(HOOK)!r}, run_name='guard_under_test')\n"
        "print(repr(g['_DB_IMPORT_ERROR']))\n"
    )
    r = _run(code, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "None"


def test_guard_refuses_in_worktree_when_lib_db_cannot_import(tmp_path):
    wt = _fake_worktree(tmp_path)
    r = _run(_guard_with_blocked("lib.db"), cwd=wt, stdin=_WRITE_EVENT)
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "could not import lib.db" in r.stderr


def test_guard_allows_outside_worktree_when_lib_db_cannot_import(tmp_path):
    r = _run(_guard_with_blocked("lib.db"), cwd=tmp_path, stdin=_WRITE_EVENT)
    assert r.returncode == 0, (r.returncode, r.stderr)
