# REPORT task-18dd8cb4

## Files changed
- tools/delegate.py: restored round one; trust errors now append a single-line warning and continue spawning, reads must succeed before any write, config location resolves CLAUDE_CONFIG_DIR at call time, JSON preserves Thai text, and the no-owner AppleScript fallback runs in the new window's initial session and returns.
- tools/worktree.py: restored round-one existing-branch worktree recovery without branch deletion.
- tools/gc_stale_tasks.py: restored round-one clearing of the worktree field after removal.
- tests/test_delegate_spawn_reliability.py: restored round-one regressions and added four review regressions for invalid JSON, environment resolution, unescaped Thai, and no second fallback tab; fixtures use temporary configs.
- docs/reports/task-18dd8cb4/REPORT.md: replaced with round-two validation and limitations.

Restoration used origin/agent/codex-task-18dd8cb4 (2a1d5d00): the requested origin/agent/codex-task-task-18dd8cb4 does not exist locally. No Git metadata was modified.

## Tests
All commands ran from the worktree root. Temporary config initialization:

```sh
mkdir -p /tmp/task-18dd8cb4-config
printf '{}\n' > /tmp/task-18dd8cb4-config/.claude.json
```

The first unadapted attempt stalled after two tests and was interrupted, with no final totals. As in round one, subsequent runs used /tmp/spawn_reliability_safety.py:

```python
import pytest

@pytest.fixture(autouse=True)
def inline_threads(monkeypatch):
    import asyncio
    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    monkeypatch.setattr(asyncio, "to_thread", inline)
```

Required round-one suite command:

```sh
PYTHONPATH="/tmp:$PWD" PYTEST_PLUGINS=spawn_reliability_safety CLAUDE_CONFIG_DIR=/tmp/task-18dd8cb4-config HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_delegate_*.py tests/test_w03_self_host_spawn.py tests/test_spawn_*.py -o addopts="" -p no:warnings
```

Pytest result: **1 failed, 237 passed, 1 xfailed in 87.48s (0:01:27)**. All 21 spawn-reliability regressions passed. The only failure is `tests/test_spawn_coo.py::test_org_mcp_server_starts_and_lists_its_tools_for_a_uid_that_can_write_the_shared_db`: `os.chown(fx / "state", 0, group)` raises `OSError: [Errno 22] Invalid argument`, as in round one. The suite now collects 239 tests after the new regressions and intervening main changes.

An additional run used the same command with `scripts/test_spawn_tab_routing.py scripts/test_watchdog_reap.py` appended before `-o`. Result: **21 failed, 261 passed, 1 xfailed in 82.22s (0:01:22)**. All 21 spawn-reliability regressions passed. The three routing failures are the review-noted DB-guard failures. The 16 watchdog failures comprise 15 DB-guard refusals and one missing macOS osascript; importing that script also globally stubs notification functions, causing the Darwin notification assertion to fail. The remaining failure is the existing COO chown permission test. These extra scripts were left unchanged.

`git diff --check`: passed.

## Not verified
- Native asyncio thread scheduling: the temporary adapter runs thread work inline.
- Live Mac iTerm routing, Claude TUI startup, concurrent config writers, tmux lifecycle, winbox startup, or live services.
- Issue #124 relay-failure notifications and issue #161 manual-reset stale assigned_agent recovery remain out of scope.
- Original intermittent first-spawn failure still needs a fresh task on the Mac.

## Blockers
- No implementation blocker. Sandbox and existing script failures prevent a fully green broad run; see Tests. No commits, network requests, or service operations were performed.

## Skill learning
- (none)
