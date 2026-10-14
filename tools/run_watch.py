"""Which runs are alive, quiet, finished, failed or dead -- no model involved.

    bash scripts/hub/org-python.sh tools/run_watch.py status [--json] [--bad]
    bash scripts/hub/org-python.sh tools/run_watch.py tail <task> [-n 15]
    bash scripts/hub/org-python.sh tools/run_watch.py follow

  status   one row per active run, and per run that ended in the last 30 min,
           on THIS host. A header line plus a row each. --bad keeps quiet /
           failed / dead; --json prints {"host", "at", "runs": [...]}.
  tail     the last lines the task's worker wrote (its transcript or CLI log),
           secrets masked.
  follow   one line per state change (start, done, failed, dead, quiet,
           resumed) and nothing else. Changes are held and printed together at
           most once per RUN_WATCH_BATCH_S. State lives in memory only: a
           restarted `follow` starts from what it sees, so ask `status` first.

The state of a run comes from lib/run_liveness.py (one reader for every tool).
Thresholds: RUN_WATCH_QUIET_S (900), RUN_WATCH_BATCH_S (120), RUN_WATCH_ENDED_S
(1800), RUN_WATCH_SPAWN_GRACE_S (90), RUN_WATCH_REPORT_GRACE_S (180),
RUN_WATCH_POLL_S (10).

If the hub cannot be read the whole output is the single line
`hub unreachable` and the exit code is 3. The ledger is opened straight from
ORG_DB_URL with db_pg.connect: lib.db.get_conn() would fall back to the
15-minute-old read-only snapshot, and a run that finished since then would
read as dead (test B7). Nothing here ever prints the DSN.

Exit codes: 0 ok, 1 unknown task / no log, 2 usage, 3 hub unreachable,
4 this host cannot be identified.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db_pg, run_liveness  # noqa: E402

HUB_CONNECT_TIMEOUT_S = 3
POLL_S_DEFAULT = 10
TITLE_MAX = 40
TAIL_BYTES = 256 * 1024
TAIL_LINE_MAX = 200

# Worst first, so the line that needs a human is the first one.
_SEVERITY = {"dead": 0, "failed": 1, "quiet": 2, "running": 3, "done": 4}
BAD_STATES = frozenset({"dead", "failed", "quiet"})

EXIT_NO_TASK = 1
EXIT_HUB = 3
EXIT_HOST = 4


class HubUnreachable(RuntimeError):
    """The ledger could not be read. Carries no detail on purpose: a driver
    message can name the host, and the contract is one line."""


class HostUnknown(RuntimeError):
    pass


def _query(sql: str, params: tuple) -> list[dict]:
    """Run one read against the hub. Raises HubUnreachable for anything short
    of a clean read (no URL, no driver, no route, a bad query): rows we could
    not read are never "dead" rows."""
    url = (os.environ.get("ORG_DB_URL") or "").strip()
    if not url:
        raise HubUnreachable("ORG_DB_URL not set")
    try:
        conn = db_pg.connect(url, timeout=HUB_CONNECT_TIMEOUT_S)
    except db_pg.HubConnectError as exc:
        raise HubUnreachable("connect failed") from exc
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception as exc:  # noqa: BLE001 -- any failed read is "unreadable"
        raise HubUnreachable("query failed") from exc
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def fetch_tasks() -> list[dict]:
    """Every row that can be a run, straight from the hub."""
    marks = ",".join("?" * len(run_liveness.RUN_STATUSES))
    return _query(f"SELECT * FROM tasks WHERE status IN ({marks}) "
                  "ORDER BY updated_at DESC LIMIT 300", run_liveness.RUN_STATUSES)


def fetch_task(needle: str) -> dict | None:
    """One row by exact id, `task-` + hex, or a unique prefix, in any status."""
    needle = needle.strip()
    rows = _query("SELECT * FROM tasks WHERE id = ? OR id = ? OR id LIKE ? "
                  "OR id LIKE ? LIMIT 3",
                  (needle, f"task-{needle}", f"{needle}%", f"task-{needle}%"))
    exact = [r for r in rows if r["id"] in (needle, f"task-{needle}")]
    if exact:
        return exact[0]
    return rows[0] if len(rows) == 1 else None


def this_host() -> str:
    from lib.config import self_host
    try:
        return self_host()
    except Exception as exc:  # noqa: BLE001 -- RuntimeError, but never guess
        raise HostUnknown(str(exc).splitlines()[0] if str(exc) else "unknown") from exc


def collect_runs(tasks: list[dict], *, now: float | None = None,
                 is_local=None, **probes) -> list[dict]:
    """The runs worth showing: this host's, active or ended in the last
    RUN_WATCH_ENDED_S, worst first. `probes` go to inspect_run (tests)."""
    from tools.worker_reap import is_local_row
    is_local = is_local or is_local_row
    now = time.time() if now is None else now
    cutoff = now - run_liveness.ended_s()
    runs = []
    for task in tasks:
        if not is_local(task):
            continue
        run = run_liveness.inspect_run(task, now=now, **probes)
        if run is None:
            continue
        if run["state"] in ("done", "failed"):
            ended = run_liveness.parse_ts(run["ended"])
            if ended is None or ended < cutoff:
                continue
        runs.append(run)
    runs.sort(key=lambda r: (_SEVERITY[r["state"]], r["started"] or ""))
    return runs


# --------------------------------------------------------------------------
# text rendering
# --------------------------------------------------------------------------

def _dur(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h{seconds % 3600 // 60:02d}m"
    return f"{seconds // 86400}d{seconds % 86400 // 3600:02d}h"


def _hhmm(iso_ts: str | None) -> str:
    return iso_ts[11:16] + "Z" if iso_ts and len(iso_ts) >= 16 else "-"


def _title(text: str) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= TITLE_MAX else text[:TITLE_MAX - 1] + "…"


def _engine(run: dict) -> str:
    model = (run["model"] or "").removeprefix("claude-")
    return f"{run['runner']}/{model}" if model else run["runner"]


def render_status(runs: list[dict]) -> str:
    """A header line and one row per run; `no runs` when there are none."""
    if not runs:
        return "no runs"
    head = ("task", "runner/model", "owner", "title", "started", "elapsed",
            "last log", "state")
    rows = [head] + [(
        r["task"], _engine(r), (r["owner"] or "-")[:8], _title(r["title"]),
        _hhmm(r["started"]), _dur(r["elapsed_s"]),
        "-" if r["idle_s"] is None else _dur(r["idle_s"]) + " ago", r["state"],
    ) for r in runs]
    widths = [max(len(row[i]) for row in rows) for i in range(len(head) - 1)]
    return "\n".join(
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row[:-1]))
        + "  " + row[-1] for row in rows)


# --------------------------------------------------------------------------
# follow
# --------------------------------------------------------------------------

class Follower:
    """Turns a stream of `collect_runs` snapshots into batched change lines.

    A batch window opens at the first change and closes `batch_s` later; every
    change in between is printed together, once. So a burst never prints more
    than one batch per window, at the cost of at most `batch_s` of delay.
    """

    def __init__(self, batch_s: int | None = None):
        self.batch_s = run_liveness.batch_s() if batch_s is None else batch_s
        self.prev: dict[str, str] = {}
        self.seeded = False
        self.pending: list[str] = []
        self.window_start: float | None = None

    @staticmethod
    def _event(old: str | None, new: str) -> str | None:
        if old is None:
            return "start" if new in ("running", "quiet") else new
        if old == new:
            return None
        if new == "running":
            return "resumed"
        return new

    def step(self, runs: list[dict], now: float) -> list[str]:
        """Feed one snapshot; returns the lines to print now (often none)."""
        current = {r["task"]: r["state"] for r in runs}
        if not self.seeded:             # the first look is the baseline, not news
            self.prev, self.seeded = current, True
            return []
        for run in runs:
            event = self._event(self.prev.get(run["task"]), run["state"])
            if event is None:
                continue
            tail = ""
            if event == "quiet" and run["idle_s"] is not None:
                tail = f" idle {_dur(run['idle_s'])}"
            elif event == "dead":
                tail = " pid and tmux gone"
            self.pending.append(
                f"{_hhmm(run_liveness.iso(now))} {event:<7} {run['task']} "
                f"{_engine(run)} {(run['owner'] or '-')[:8]} {_title(run['title'])}{tail}")
            if self.window_start is None:
                self.window_start = now
        self.prev = current
        if self.pending and self.window_start is not None \
                and now - self.window_start >= self.batch_s:
            out, self.pending, self.window_start = self.pending, [], None
            return out
        return []


def run_follow(*, fetch=None, clock=time.time, sleep=time.sleep, out=None,
               poll_s: int | None = None, max_polls: int | None = None,
               **collect) -> int:
    """Poll, feed the Follower, print what it releases. `max_polls` bounds the
    loop for tests; the real command runs until killed."""
    fetch = fetch or fetch_tasks
    out = out or sys.stdout
    poll_s = run_liveness._env_int("RUN_WATCH_POLL_S", POLL_S_DEFAULT) \
        if poll_s is None else poll_s
    follower = Follower()
    polls = 0
    while max_polls is None or polls < max_polls:
        now = clock()
        try:
            runs = collect_runs(fetch(), now=now, **collect)
        except HubUnreachable:
            print("hub unreachable", file=out)
            out.flush()
            return EXIT_HUB
        for line in follower.step(runs, now):
            print(line, file=out)
        out.flush()
        polls += 1
        if max_polls is None or polls < max_polls:
            sleep(poll_s)
    return 0


# --------------------------------------------------------------------------
# tail
# --------------------------------------------------------------------------

def _read_tail(path: Path) -> str:
    size = path.stat().st_size
    with path.open("rb") as fh:
        if size > TAIL_BYTES:
            fh.seek(size - TAIL_BYTES)
            fh.readline()               # drop the partial line we landed in
        return fh.read().decode("utf-8", errors="replace")


def tail_lines(path: Path, n: int) -> list[str]:
    """The last `n` readable lines of a worker log. A claude transcript is
    flattened to `hh:mm:ss kind summary` (the same renderer as
    tools/remote_worker_log.py); anything else, a codex event stream or an
    agy log, is shown line by line. Secrets masked either way."""
    from tools.remote_worker_log import _entries_from_jsonl, _mask_secrets
    raw = _read_tail(path)
    lines: list[str] = []
    if path.suffix == ".jsonl":
        lines = [f"{ts} {kind} {summary}" for ts, kind, summary in _entries_from_jsonl(raw)]
    if not lines:
        lines = [" ".join(ln.split()) for ln in raw.splitlines() if ln.strip()]
    return [_mask_secrets(ln)[:TAIL_LINE_MAX] for ln in lines[-n:]]


def cmd_tail(args) -> int:
    task = fetch_task(args.task)
    if task is None:
        print(f"no task {args.task}")
        return EXIT_NO_TASK
    from tools.worker_reap import is_local_row
    if not is_local_row(task):
        print(f"{task['id']} runs on another host; its log is not here")
        return EXIT_NO_TASK
    path, _ = run_liveness.newest_log(task)
    if path is None:
        print(f"{task['id']} has written no log yet")
        return EXIT_NO_TASK
    for line in tail_lines(path, args.n):
        print(line)
    return 0


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run_watch", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("status", help="active and just-ended runs on this host")
    st.add_argument("--json", action="store_true")
    st.add_argument("--bad", action="store_true", help="quiet, failed, dead only")
    tl = sub.add_parser("tail", help="the last lines a task's worker wrote")
    tl.add_argument("task")
    tl.add_argument("-n", type=int, default=15)
    sub.add_parser("follow", help="one line per state change")
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        host = this_host()
    except HostUnknown as exc:
        print(f"host unknown: {exc}")
        return EXIT_HOST
    try:
        if args.cmd == "follow":
            return run_follow()
        if args.cmd == "tail":
            return cmd_tail(args)
        runs = collect_runs(fetch_tasks())
    except HubUnreachable:
        print("hub unreachable")
        return EXIT_HUB
    if args.bad:
        runs = [r for r in runs if r["state"] in BAD_STATES]
    if args.json:
        print(json.dumps({"host": host, "at": run_liveness.iso(time.time()),
                          "runs": runs}, ensure_ascii=False))
    elif not runs:
        print("no bad runs" if args.bad else "no runs")
    else:
        print(render_status(runs))
    return 0


if __name__ == "__main__":
    try:
        rc = main()
        sys.stdout.flush()
    except BrokenPipeError:     # `| head`: the reader is gone, not an error
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        rc = 0
    sys.exit(rc)
