"""Is a run alive? The ONE place that answers it.

`tools/run_watch.py` (the zero-model status/tail/follow API) and, later, the
Session Steward both read a run's state from here, so "dead" means the same
thing to every reader.

A run is a task row whose worker is (or just was) doing the work. From the
row, plus three probes, `classify` returns exactly one of:

    running  a worker process or tmux session is alive and wrote its log
             within QUIET_S
    quiet    alive, but no log write for more than QUIET_S (a hung or very
             long turn -- yellow, not red)
    done     status review / done / merged: the report is in
    failed   status failed / stalled
    dead     status in_progress, the pid AND every tmux session of the task
             are gone, and the grace periods below have passed

and `None` for a row that is not a run at all: pending, rate_limited,
conflict, blocked_*, queued_remote (nothing is supposed to be executing) and
cancelled / reverted (a person ended it on purpose -- neither working nor
broken, so it must not hold a red light).

Where a run writes (measured 2026-10-15, not assumed):

  * state/logs/<role>_<task>.log -- the org logger. It gets ONE line, at
    report time (57 bytes for a finished task), so it says nothing about a
    run in progress and is deliberately not read here.
  * <hub root>/.launch-<task>/codex-events.jsonl and agy-events.log -- stdout
    of the codex / agy CLI under scripts/spawn-worker-remote.sh. Grows with
    every event.
  * <worktree>/.agy-run.log -- agy under runners/agy_local.py.
  * <claude config dir>/projects/<worktree slug>/*.jsonl -- a claude worker's
    own transcript; one line per message / tool call. This is the signal for
    every claude worker.
  * <worktree>/HEARTBEAT is NOT a signal. The codex/agy launcher rewrites it
    every 60 s from a side loop whether or not the CLI is doing anything, so
    reading it would make a hung codex look alive forever.

Rules that keep this from crying wolf. The CEO asked (2026-10-15) to see
whether a run is working and to know when it broke or died: "พัง หรือ ตายเมื่อไหร่
ต้องรู้และ เชคได้". That only helps if a red light is true:

  * `dead` needs positive proof: the pid probe says gone AND no tmux session
    answers. A pid we may not signal (EPERM) counts as alive -- this is a
    reader, not a reaper, so a watcher running as another user must not see
    every root-owned worker as dead (tools.worker_reap._pid_alive answers the
    opposite way on purpose: it is the one that sends the signal).
  * A row spawned or written less than SPAWN_GRACE_S ago is `running`:
    delegate writes the row before the process exists, and reopen_task writes
    it before the respawn.
  * A codex / agy worker exits cleanly and THEN waits for runners/branch_poller
    (every 60 s) to see REPORT.md and flip the row to `review`. For that gap
    the row is in_progress, the pid and tmux session are gone, and nothing is
    wrong (seen live 2026-10-15, task-c7116818). Those runners stay `running`
    for REPORT_GRACE_S after their last output before they read as `dead`.
  * Whether the HUB could be read is not decided here. A caller that could
    not read the rows has no rows to classify and must say "hub unreachable",
    never "dead" (tools/run_watch.py, test B7).
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.proc import pid_alive
from tools import tmux_session

ROOT = Path(__file__).resolve().parent.parent

STATES = ("running", "quiet", "done", "failed", "dead")

DONE_STATUSES = frozenset({"review", "done", "merged"})
FAILED_STATUSES = frozenset({"failed", "stalled"})
# Runners whose row is flipped by branch_poller after the process has exited.
EXTERNAL_RUNNERS = frozenset({"codex", "agy"})
LIVE_STATUSES = frozenset({"in_progress"})
# Every status that can be a run. run_watch selects rows with these.
RUN_STATUSES = tuple(sorted(DONE_STATUSES | FAILED_STATUSES | LIVE_STATUSES))

DEFAULT_QUIET_S = 900
DEFAULT_BATCH_S = 120
DEFAULT_ENDED_S = 1800
DEFAULT_SPAWN_GRACE_S = 90
DEFAULT_REPORT_GRACE_S = 180   # branch_poller's 60 s poll, plus the launcher's commit + push


def _env_int(name: str, default: int) -> int:
    """A positive int from the environment; a missing, blank, non-numeric or
    non-positive value is `default` -- a typo in a threshold must not crash a
    watcher or silence it."""
    try:
        value = int(os.environ.get(name, "").strip())
    except ValueError:
        return default
    return value if value > 0 else default


def quiet_s() -> int:
    """No log write for longer than this => `quiet`. RUN_WATCH_QUIET_S."""
    return _env_int("RUN_WATCH_QUIET_S", DEFAULT_QUIET_S)


def batch_s() -> int:
    """`follow` prints at most one batch per this many seconds. RUN_WATCH_BATCH_S."""
    return _env_int("RUN_WATCH_BATCH_S", DEFAULT_BATCH_S)


def ended_s() -> int:
    """A finished run stays in `status` this long. RUN_WATCH_ENDED_S."""
    return _env_int("RUN_WATCH_ENDED_S", DEFAULT_ENDED_S)


def spawn_grace_s() -> int:
    """A just-spawned row is never `dead` inside this. RUN_WATCH_SPAWN_GRACE_S."""
    return _env_int("RUN_WATCH_SPAWN_GRACE_S", DEFAULT_SPAWN_GRACE_S)


def report_grace_s() -> int:
    """How long a finished codex / agy run may wait for branch_poller before
    it reads as dead. RUN_WATCH_REPORT_GRACE_S."""
    return _env_int("RUN_WATCH_REPORT_GRACE_S", DEFAULT_REPORT_GRACE_S)


def parse_ts(value) -> float | None:
    """Epoch seconds from a ledger timestamp (ISO 8601; naive means UTC), or
    None when it is missing or unreadable."""
    if not value or not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp()


def iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


def started_at(task: dict) -> float | None:
    """When the worker was last spawned. `spawned_at` is stamped by
    delegate_task at spawn and by nothing else; `created_at` is the fallback
    for a row that was never delegated."""
    return parse_ts(task.get("spawned_at")) or parse_ts(task.get("created_at"))


def tmux_names(task: dict) -> list[str]:
    """The tmux sessions a task's worker may live in: the one recorded on its
    row (`mooniex-task-<id>` from the remote launcher) and the `wd-<id>`
    convention. Same two names worker_reap._cleanup_tmux_ttyd kills."""
    return [n for n in dict.fromkeys(
        (task.get("tmux_session"), tmux_session.session_name_for(task["id"]))) if n]


def claude_project_dir(worktree: str) -> Path:
    """Where Claude Code keeps the transcripts of a session started in
    `worktree`: every character outside [A-Za-z0-9] in the absolute path
    becomes `-` (measured: /opt/MoonieXHQ/Agents/Core/worktrees/x__y__task-1
    -> -opt-MoonieXHQ-Agents-Core-worktrees-x--y--task-1)."""
    base = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    return Path(base) / "projects" / re.sub(r"[^A-Za-z0-9]", "-", worktree)


def log_files(task: dict) -> list[Path]:
    """Every file this task's worker could be writing right now (see the
    module docstring for what each one is). Only existing files count."""
    tid = task["id"]
    hub_root = Path(os.environ.get("ORG_ROOT") or ROOT)
    launch = hub_root / f".launch-{tid}"
    found = [launch / "codex-events.jsonl", launch / "agy-events.log"]
    worktree = task.get("worktree")
    if worktree:
        found.append(Path(worktree) / ".agy-run.log")
        try:
            found.extend(claude_project_dir(worktree).glob("*.jsonl"))
        except OSError:
            pass
    return [p for p in found if p.is_file()]


def newest_log(task: dict) -> tuple[Path | None, float | None]:
    """(path, mtime) of the file this task wrote to last, or (None, None)."""
    best: tuple[Path | None, float | None] = (None, None)
    for path in log_files(task):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if best[1] is None or mtime > best[1]:
            best = (path, mtime)
    return best


def model_of(task: dict) -> str | None:
    """The model that drives the run: the one the router picked
    (`runner_model`), else the role's configured model for a claude worker."""
    if task.get("runner_model"):
        return task["runner_model"]
    if (task.get("runner") or "claude") != "claude":
        return None
    try:
        from lib.config import get_role
        return get_role(task["role"]).get("model")
    except Exception:  # noqa: BLE001 -- display only, never fail a status on it
        return None


def probe_pid(task: dict) -> bool:
    return pid_alive(task.get("pid"), denied_is_alive=True)


def probe_tmux(task: dict) -> bool:
    """True when any of the task's tmux sessions exists. No tmux binary on the
    box (a Mac worker in an iTerm tab, winbox) is simply "no session"."""
    for name in tmux_names(task):
        try:
            if tmux_session.has_session(name):
                return True
        except OSError:
            return False
    return False


def probe_report(task: dict) -> bool | None:
    """Whether `<worktree>/docs/reports/<task id>/REPORT.md` exists; None when
    the row has no worktree path or the path cannot be read."""
    worktree = task.get("worktree")
    tid = task.get("id")
    if not worktree or not tid or not isinstance(worktree, (str, os.PathLike)):
        return None
    if isinstance(worktree, str) and not worktree.strip():
        return None
    try:
        return (Path(worktree) / "docs" / "reports" / str(tid) / "REPORT.md").is_file()
    except (OSError, ValueError):
        return None


def classify(task: dict, *, pid_ok: bool, tmux_ok: bool,
             last_log: float | None, now: float,
             report_ok: bool | None = None) -> str | None:
    """The state of one run, from the row and the probe answers. Pure:
    no I/O, so the five states can be pinned by a fixture."""
    status = task.get("status")
    if status in DONE_STATUSES:
        return "done"
    if status in FAILED_STATUSES:
        return "failed"
    if status not in LIVE_STATUSES:
        return None
    started = started_at(task)
    if not (pid_ok or tmux_ok):
        touched = max((t for t in (started, parse_ts(task.get("updated_at")))
                       if t is not None), default=None)
        if touched is not None and now - touched < spawn_grace_s():
            return "running"
        if (task.get("runner") or "claude") in EXTERNAL_RUNNERS and report_ok is not False:
            gone = max((t for t in (last_log, started) if t is not None), default=None)
            if gone is not None and now - gone < report_grace_s():
                return "running"
        return "dead"
    marks = [t for t in (last_log, started) if t is not None]
    if marks and now - max(marks) > quiet_s():
        return "quiet"
    return "running"


def inspect_run(task: dict, *, now: float | None = None, pid_alive_fn=None,
                tmux_alive_fn=None, newest_log_fn=None,
                report_ok_fn=None) -> dict | None:
    """One run, as the dict `status --json` prints; None when the row is not a
    run. The `*_fn` arguments replace the real probes (tests only).

    A finished run is not probed at all: its state comes from its status, and
    a live pid on a `done` row (an idle worker at its prompt) is not news.
    """
    now = time.time() if now is None else now
    pid_ok = tmux_ok = False
    report_ok = None
    if task.get("status") in LIVE_STATUSES:
        pid_ok = (pid_alive_fn or probe_pid)(task)
        tmux_ok = (tmux_alive_fn or probe_tmux)(task)
        report_ok = (report_ok_fn or probe_report)(task)
    path, last_log = (newest_log_fn or newest_log)(task)
    state = classify(task, pid_ok=pid_ok, tmux_ok=tmux_ok, last_log=last_log,
                     now=now, report_ok=report_ok)
    if state is None:
        return None
    started = started_at(task)
    ended = parse_ts(task.get("updated_at")) if state in ("done", "failed") else None
    end = ended if ended is not None else now
    return {
        "task": task["id"],
        "state": state,
        "status": task.get("status"),
        "runner": task.get("runner") or "claude",
        "model": model_of(task),
        "owner": task.get("owner_cto"),
        "title": task.get("title") or "",
        "started": iso(started),
        "elapsed_s": int(end - started) if started is not None else None,
        "ended": iso(ended),
        "last_log": iso(last_log),
        "idle_s": int(now - last_log) if last_log is not None else None,
        "log": str(path) if path else None,
        "pid": task.get("pid"),
        "pid_alive": pid_ok,
        "tmux_alive": tmux_ok,
    }
