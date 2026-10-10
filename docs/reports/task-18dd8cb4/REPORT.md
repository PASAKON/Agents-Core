# REPORT task-18dd8cb4

## Files changed
- tools/delegate.py: catch dead tmux spawns, fail and release locks, log only “spawn started”, restore missing checkouts, require tmux for tab reuse, create a fallback window and warn about missing owner window IDs, atomically pre-trust Claude worktrees, and refuse kickoff at a trust dialog even after a claim.
- tools/worktree.py: restore an existing branch with `git worktree add <path> <branch>` and provision dependencies without deleting the branch; return to normal creation only when the branch is absent.
- tools/gc_stale_tasks.py: clear the recorded worktree after successful removal; retain it if removal leaves the directory behind.
- tests/test_delegate_spawn_reliability.py: 17 asserting regressions covering spawn failures, claim/log behavior, missing worktrees and retained branches, GC, AppleScript routing, owner warnings, atomic trust writes, and trust-dialog refusal.
- docs/reports/task-18dd8cb4/REPORT.md: validation and review handoff.

## Tests
Command (new regression file is included by the delegate glob):

```sh
export PYTHONPATH="/tmp:$PWD"
export PYTEST_PLUGINS=spawn_reliability_safety
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_delegate_*.py tests/test_w03_self_host_spawn.py tests/test_spawn_*.py -o addopts="" -p no:warnings
```

Pytest result: **1 failed, 229 passed, 1 xfailed in 76.47s (0:01:16)**. All 17 new regressions passed.

The failure is `tests/test_spawn_coo.py::test_org_mcp_server_starts_and_lists_its_tools_for_a_uid_that_can_write_the_shared_db`: its setup calls `os.chown(fx / "state", 0, 65534)` and the sandbox returns `OSError: [Errno 22] Invalid argument`. It fails before starting the tested server. No change to that out-of-scope test was made.

The temporary `/tmp/spawn_reliability_safety.py` pytest plugin redirects `tools.delegate.CLAUDE_CONFIG_PATH` to a temporary directory for the session. It also replaces `asyncio.to_thread` with an async adapter that calls the supplied function inline. Initial runs were interrupted after hanging in asyncio's selector/thread completion; a 15-second faulthandler dump showed the main event loop waiting while the worker thread was idle (and another run hung during executor shutdown). This adapter leaves assertions and production functions intact but does not validate real thread scheduling. No real Claude config was read or written.

Temporary plugin contents for reproduction (not a repository change):

```python
from pathlib import Path
import tempfile
import pytest

@pytest.fixture(autouse=True, scope="session")
def isolated_claude_config():
    from tools import delegate
    original = delegate.CLAUDE_CONFIG_PATH
    with tempfile.TemporaryDirectory(prefix="spawn-trust-") as directory:
        delegate.CLAUDE_CONFIG_PATH = Path(directory) / "claude.json"
        yield
    delegate.CLAUDE_CONFIG_PATH = original

@pytest.fixture(autouse=True)
def inline_threads(monkeypatch):
    import asyncio
    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    monkeypatch.setattr(asyncio, "to_thread", inline)
```

`git diff --check`: passed.

## Not verified
- Live Mac iTerm window/tab routing and Claude TUI startup; AppleScript is checked as generated text only.
- Live tmux lifecycle, concurrent Claude config writers, remote winbox startup, and other live services.
- Issue #124 relay-failure notifications are explicitly out of scope.
- Issue #161 manual-reset stale `assigned_agent` recovery is explicitly out of scope.
- The original intermittent first-spawn failure needs a fresh task on the Mac; this patch handles the identified failure modes rather than claiming a live reproduction.

## Blockers
- No implementation blocker. The existing regression suite needs shared Claude config isolation when run without the temporary plugin. Adding that autouse fixture to root `conftest.py` would be appropriate, but that file is outside the allowed edit list and was not changed.
- The full suite is not green here because the existing COO permission test cannot chown to group 65534 in this sandbox. Rerun it on a host supporting that UID/GID.
- Native asyncio thread scheduling could not be validated in this sandbox; rerun without the inline adapter on the review host.

## Skill learning
- (none)
