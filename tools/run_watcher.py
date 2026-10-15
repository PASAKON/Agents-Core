"""Pure lifecycle decisions and launch argv builder for the Run Watch session.

Nothing in this module starts a process, opens a tmux session, or contacts the
hub. It provides:
  - Threshold helpers: `quiet_s()`, `close_after_s()`, `batch_s()`
  - Pure lifecycle decision function: `decide_lifecycle(...)` -> one of
    `("start", "stop", "restart", "give_up", "none")`, appending one line to
    `state/steward/<host>/open.md` on `give_up`
  - Pure launch argv builders: `build_launch_argv(...)` / `build_claude_argv(...)`
    for tmux session `runwatch-<host>` with session name built via
    `lib.session_names.watch_name` (and `windows_safe` on `winbox`).
"""
from __future__ import annotations

import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = ROOT
sys.path.insert(0, str(ROOT))

from lib import run_liveness  # noqa: E402
from tools import run_watch  # noqa: E402

ACTIONS = ("start", "stop", "restart", "give_up", "none")

DEFAULT_MODEL = "haiku"
EMPTY_MCP_CONFIG = '{"mcpServers":{}}'
PERMISSION_MODE = "dontAsk"
ALLOWED_TOOL = "Bash(bash scripts/hub/org-python.sh tools/run_watch.py *)"
PROMPT_FILE = "roles/run_watch.md"

STEWARD_ROOT = ROOT / "state" / "steward"
_DEFAULT_STEWARD_ROOT = STEWARD_ROOT
_TEST_MEM_OPEN: dict[tuple[str, str], list[str]] = {}

quiet_s = run_liveness.quiet_s
batch_s = run_liveness.batch_s
close_after_s = run_watch.close_after_s


def _resolve_host(host: str | None = None) -> str:
    if host:
        return host
    try:
        return run_watch.this_host()
    except Exception:  # noqa: BLE001
        return "local"


def _active_count(active_runs: int | Sequence[dict] | None) -> int:
    """Count active runs whether caller passed an int count or a sequence of runs."""
    if active_runs is None:
        return 0
    if isinstance(active_runs, bool):
        return int(active_runs)
    if isinstance(active_runs, (int, float)):
        return max(0, int(active_runs))
    items = list(active_runs)
    if not items:
        return 0
    if all(isinstance(x, dict) and "state" in x for x in items):
        return sum(1 for x in items if x.get("state") in run_watch.ACTIVE_STATES)
    return len(items)


def _elapsed_since_end(
    since_last_end: float | int | str | None,
    now: float | None,
) -> float | None:
    """Normalize `since_last_end` to elapsed seconds.

    Accepts either an elapsed duration in seconds (e.g. `600`) or an epoch/ISO
    timestamp of when the last run ended (when `now` is also supplied).
    """
    if since_last_end is None:
        return None
    if isinstance(since_last_end, str):
        ended_ts = run_liveness.parse_ts(since_last_end)
        if ended_ts is None:
            return None
        ref = time.time() if now is None else float(now)
        return max(0.0, ref - ended_ts)
    val = float(since_last_end)
    if (
        now is not None
        and float(now) >= 1_000_000_000.0
        and val >= 1_000_000_000.0
        and val <= float(now)
    ):
        return float(now) - val
    return val


def steward_open_file(
    host: str | None = None,
    *,
    open_md: Path | str | None = None,
    state_root: Path | str | None = None,
) -> Path:
    """Path to `state/steward/<host>/open.md`."""
    h = _resolve_host(host)
    if open_md is not None:
        p = Path(open_md)
        return p if p.suffix == ".md" else p / "open.md"
    if state_root is not None:
        sr = Path(state_root)
        if sr.name == h:
            return sr / "open.md"
        if sr.name == "steward":
            return sr / h / "open.md"
        return sr / "state" / "steward" / h / "open.md"
    env_dir = (os.environ.get("RUN_WATCH_STEWARD_DIR") or "").strip()
    if env_dir:
        p = Path(env_dir)
        return p if p.suffix == ".md" else (p / "open.md" if p.name == h else p / h / "open.md")
    base = STEWARD_ROOT if STEWARD_ROOT != _DEFAULT_STEWARD_ROOT else (ROOT / "state" / "steward")
    return base / h / "open.md"


def _use_mem_open(path: Path) -> bool:
    if "PYTEST_CURRENT_TEST" not in os.environ:
        return False
    try:
        return path.resolve().is_relative_to(_DEFAULT_STEWARD_ROOT.resolve())
    except Exception:  # noqa: BLE001
        return False


def record_give_up(
    host: str | None = None,
    *,
    now: float | None = None,
    active_runs: int | Sequence[dict] = 0,
    open_md: Path | str | None = None,
    state_root: Path | str | None = None,
) -> Path:
    """Append one single-line entry to `state/steward/<host>/open.md`."""
    h = _resolve_host(host)
    n = _active_count(active_runs)
    ts = run_liveness.iso(time.time() if now is None else float(now))
    line = (
        f"- [{ts}] runwatch-{h}: watcher died twice while {n} run(s) active; "
        f"giving up until next run cycle.\n"
    )
    path = steward_open_file(h, open_md=open_md, state_root=state_root)
    if _use_mem_open(path):
        key = (os.environ.get("PYTEST_CURRENT_TEST", ""), str(path))
        _TEST_MEM_OPEN.setdefault(key, []).append(line)
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return path


def decide_lifecycle(
    active_runs: int | Sequence[dict] | None,
    watcher_alive: bool,
    start_count: int = 0,
    since_last_end: float | int | str | None = None,
    now: float | None = None,
    *,
    host: str | None = None,
    open_md: Path | str | None = None,
    state_root: Path | str | None = None,
) -> str:
    """Pure decision function for the Run Watch session lifecycle.

    Given `(active_runs, watcher_alive, start_count, since_last_end, now)`,
    returns one of `("start", "stop", "restart", "give_up", "none")`:
      - `start`: first run goes active (`n_active > 0`), no watcher alive,
        and `start_count == 0`
      - `stop`: no active runs (`n_active == 0`), watcher is alive, and time
        since last run ended >= `close_after_s()` (default 600 s)
      - `restart`: watcher died while runs are active (`start_count == 1`)
      - `give_up`: watcher died a second time while runs are active
        (`start_count == 2`); appends one line to `state/steward/<host>/open.md`
      - `none`: no action (including after `give_up` when `start_count > 2`,
        since a given-up watcher is never resumed in the same cycle)
    """
    n_active = _active_count(active_runs)
    if n_active > 0:
        if watcher_alive:
            return "none"
        if start_count <= 0:
            return "start"
        if start_count == 1:
            return "restart"
        if start_count == 2:
            record_give_up(
                host,
                now=now,
                active_runs=n_active,
                open_md=open_md,
                state_root=state_root,
            )
            return "give_up"
        return "none"

    if not watcher_alive:
        return "none"
    elapsed = _elapsed_since_end(since_last_end, now)
    if elapsed is not None and elapsed >= close_after_s():
        return "stop"
    return "none"


decide = decide_lifecycle


def next_start_count(
    active_runs: int | Sequence[dict] | None,
    watcher_alive: bool,
    start_count: int,
    decision: str,
) -> int:
    """Compute the next cycle's `start_count` after `decision`.

    Once all active runs end and the watcher is not alive (or stops), the cycle
    resets to 0 so the next active run starts a fresh watcher.
    """
    n_active = _active_count(active_runs)
    if decision == "start":
        return 1
    if decision == "restart":
        return 2
    if decision == "give_up":
        return 3
    if decision == "stop":
        return 0
    if n_active == 0 and not watcher_alive:
        return 0
    return start_count


class WatcherCycle:
    """Tracks `start_count` across lifecycle ticks without external side effects."""

    def __init__(
        self,
        *,
        host: str | None = None,
        open_md: Path | str | None = None,
        state_root: Path | str | None = None,
    ):
        self.host = host
        self.open_md = open_md
        self.state_root = state_root
        self.start_count = 0

    def step(
        self,
        active_runs: int | Sequence[dict] | None,
        watcher_alive: bool,
        since_last_end: float | int | str | None = None,
        now: float | None = None,
    ) -> str:
        if _active_count(active_runs) == 0 and not watcher_alive:
            self.start_count = 0
        decision = decide_lifecycle(
            active_runs,
            watcher_alive,
            self.start_count,
            since_last_end,
            now,
            host=self.host,
            open_md=self.open_md,
            state_root=self.state_root,
        )
        self.start_count = next_start_count(
            active_runs, watcher_alive, self.start_count, decision,
        )
        return decision


# --------------------------------------------------------------------------
# Launch argv builder (pure, does not run anything)
# --------------------------------------------------------------------------

def tmux_session_name(host: str | None = None) -> str:
    """Return `runwatch-<host>`."""
    return f"runwatch-{_resolve_host(host)}"


def build_claude_argv(
    host: str | None = None,
    *,
    sid: str = "000",
    n_active: int = 0,
    light: str = run_watch.LIGHT_IDLE,
    model: str = DEFAULT_MODEL,
    mcp_config: str = EMPTY_MCP_CONFIG,
    prompt_file: str = PROMPT_FILE,
) -> list[str]:
    """Pure builder for the `claude` command argv inside the watcher session."""
    h = _resolve_host(host)
    name = run_watch.format_watch_name(n_active, light, sid=sid, host=h)
    return [
        "claude",
        "--model",
        model,
        "--remote-control",
        "--strict-mcp-config",
        "--mcp-config",
        mcp_config,
        "--permission-mode",
        PERMISSION_MODE,
        "--allowedTools",
        ALLOWED_TOOL,
        "--append-system-prompt-file",
        prompt_file,
        "-n",
        name,
    ]


claude_argv = build_claude_argv


def build_launch_argv(
    host: str | None = None,
    *,
    sid: str = "000",
    n_active: int = 0,
    light: str = run_watch.LIGHT_IDLE,
    model: str = DEFAULT_MODEL,
    mcp_config: str = EMPTY_MCP_CONFIG,
    prompt_file: str = PROMPT_FILE,
) -> list[str]:
    """Pure builder for the full `tmux new-session -d -s runwatch-<host> claude ...` argv."""
    h = _resolve_host(host)
    return [
        "tmux",
        "new-session",
        "-d",
        "-s",
        tmux_session_name(h),
        *build_claude_argv(
            h,
            sid=sid,
            n_active=n_active,
            light=light,
            model=model,
            mcp_config=mcp_config,
            prompt_file=prompt_file,
        ),
    ]


launch_argv = build_launch_argv
