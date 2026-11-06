"""Pure lifecycle decisions and launch argv builder for the Run Watch session.

Nothing in this module starts a process, opens a tmux session, or contacts the
hub. It provides:
  - Threshold helpers: `quiet_s()`, `batch_s()`, `stable_s()`, `retry_s()`
  - Pure lifecycle decision function: `decide_lifecycle(...)` -> one of
    `("start", "restart", "give_up", "none")`, appending one line to
    `state/steward/<host>/open.md` on `give_up`. The Watch session is always up
    (CEO 3 Nov): a missing one is started even with no runs, and nothing here ever
    stops one. The driver alone kills it, for low memory, and resumes it next tick.
  - Pure launch argv builders: `build_launch_argv(...)` / `build_claude_argv(...)`
    for tmux session `runwatch-<host>` with session name built via
    `lib.session_names.watch_name` (and `windows_safe` on `winbox`). One Claude
    conversation per host: the first start gives it `--session-id <uuid>`, every
    later start resumes it with `-r <uuid>`.
"""
from __future__ import annotations

import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import run_liveness  # noqa: E402
from tools import run_watch  # noqa: E402

# "stop" is never decided here: only the driver applies it, to kill the session for low memory.
ACTIONS = ("start", "stop", "restart", "give_up", "none")

DEFAULT_MODEL = "haiku"
# PH rows live in a separate local terminal pane created by run_watch_driver.
# They never enter this model's prompt or change PH session names.
EMPTY_MCP_CONFIG = '{"mcpServers":{}}'
PERMISSION_MODE = "dontAsk"
ALLOWED_TOOL = "Bash(bash scripts/hub/org-python.sh tools/run_watch.py *)"
PROMPT_FILE = "roles/run_watch.md"

STEWARD_ROOT = ROOT / "state" / "steward"

STABLE_S_DEFAULT = 600     # up this long = healthy: earlier deaths are forgotten
RETRY_S_DEFAULT = 3600     # after give_up, try again this much later

quiet_s = run_liveness.quiet_s
batch_s = run_liveness.batch_s


def stable_s() -> int:
    return run_liveness._env_int("RUN_WATCH_STABLE_S", STABLE_S_DEFAULT)


def retry_s() -> int:
    return run_liveness._env_int("RUN_WATCH_RETRY_S", RETRY_S_DEFAULT)


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
    return STEWARD_ROOT / h / "open.md"


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
        f"- [{ts}] runwatch-{h}: watcher died twice in a row ({n} run(s) active); "
        f"giving up, trying again in {retry_s() // 60} min.\n"
    )
    path = steward_open_file(h, open_md=open_md, state_root=state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return path


def decide_lifecycle(
    active_runs: int | Sequence[dict] | None,
    watcher_alive: bool,
    start_count: int = 0,
    now: float | None = None,
    *,
    host: str | None = None,
    open_md: Path | str | None = None,
    state_root: Path | str | None = None,
    record: bool = True,
) -> str:
    """Pure decision function for the Run Watch session lifecycle.

    The session is always up, so only a missing one is acted on, with or without
    runs. Given `(active_runs, watcher_alive, start_count, now)`, returns one of
    `("start", "restart", "give_up", "none")`:
      - `none`: the watcher is alive (never stopped when idle), or it is missing
        after `give_up` (`start_count > 2`), until `forget_deaths` resets the count
      - `start`: no watcher alive and `start_count == 0`
      - `restart`: the watcher died (`start_count == 1`)
      - `give_up`: it died a second time (`start_count == 2`); appends one line
        to `state/steward/<host>/open.md`
    """
    if watcher_alive or start_count > 2:
        return "none"
    if start_count <= 0:
        return "start"
    if start_count == 1:
        return "restart"
    if record:
        record_give_up(
            host,
            now=now,
            active_runs=active_runs,
            open_md=open_md,
            state_root=state_root,
        )
    return "give_up"


decide = decide_lifecycle


def next_start_count(start_count: int, decision: str) -> int:
    """Compute the next tick's `start_count` after `decision` was applied.

    `stop` (the driver's low-memory kill) resets it: a kill the driver chose is
    not a death and must not use up the one restart.
    """
    return {"start": 1, "restart": 2, "give_up": 3, "stop": 0}.get(decision, start_count)


def forget_deaths(
    start_count: int,
    *,
    alive: bool,
    started_at: float | None,
    gave_up_at: float | None,
    now: float,
) -> int:
    """`start_count` after forgetting old deaths: a session up for `stable_s()` is
    healthy, and a host that gave up tries again `retry_s()` later. Without this
    an always-up watcher would give up for good after two deaths a week apart."""
    if alive and started_at is not None and now - started_at >= stable_s():
        return 0
    if start_count > 2 and gave_up_at is not None and now - gave_up_at >= retry_s():
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
        now: float | None = None,
    ) -> str:
        decision = decide_lifecycle(
            active_runs,
            watcher_alive,
            self.start_count,
            now,
            host=self.host,
            open_md=self.open_md,
            state_root=self.state_root,
        )
        self.start_count = next_start_count(self.start_count, decision)
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
    session_id: str,
    resume: bool = False,
    n_active: int = 0,
    light: str = run_watch.LIGHT_IDLE,
    model: str = DEFAULT_MODEL,
    mcp_config: str = EMPTY_MCP_CONFIG,
    prompt_file: str = PROMPT_FILE,
    claude_bin: str = "claude",
) -> list[str]:
    """Pure builder for the `claude` command argv inside the watcher session.

    `session_id` is the host's one conversation: `--session-id` creates it on the
    first start, `-r` (resume=True) reopens it on every later one, under the same
    `--remote-control` name, so the claude.ai session and the CEO's pin stay."""
    h = _resolve_host(host)
    name = run_watch.format_watch_name(n_active, light, host=h)
    return [
        claude_bin,
        "--model",
        model,
        "--remote-control",
        name,
        "--strict-mcp-config",
        "--mcp-config",
        mcp_config,
        "--permission-mode",
        PERMISSION_MODE,
        "--allowedTools",
        ALLOWED_TOOL,
        "--tools",
        "Bash",
        "--setting-sources",
        "user",
        "--system-prompt-file",
        prompt_file,
        "-n",
        name,
        *(["-r", session_id] if resume else ["--session-id", session_id]),
    ]


claude_argv = build_claude_argv


def build_launch_argv(
    host: str | None = None,
    *,
    session_id: str,
    resume: bool = False,
    n_active: int = 0,
    light: str = run_watch.LIGHT_IDLE,
    model: str = DEFAULT_MODEL,
    mcp_config: str = EMPTY_MCP_CONFIG,
    prompt_file: str = PROMPT_FILE,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    claude_bin: str = "claude",
) -> list[str]:
    """Pure builder for the full `tmux new-session -d -s runwatch-<host> claude ...` argv."""
    h = _resolve_host(host)
    return [
        "tmux",
        "new-session",
        "-d",
        "-s",
        tmux_session_name(h),
        *(["-c", str(cwd)] if cwd is not None else []),
        *(arg for key, value in sorted((env or {}).items()) for arg in ("-e", f"{key}={value}")),
        *build_claude_argv(
            h,
            session_id=session_id,
            resume=resume,
            n_active=n_active,
            light=light,
            model=model,
            mcp_config=mcp_config,
            prompt_file=prompt_file,
            claude_bin=claude_bin,
        ),
    ]


launch_argv = build_launch_argv
