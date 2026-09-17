"""Branch poller — hub side, Phase 1 (docs/design/multi-host-workers.md).

Every POLL_SECONDS: for each `in_progress` task whose `host` is a remote
spoke (not NULL, not 'mac'), check whether its branch landed on GitHub yet.
A pushed branch carrying REPORT.md flips the task to `review`; one carrying
BLOCKER.md opens a GitHub issue and marks it `blocked_human`; and if the
remote worker died before pushing either, the task fails with a clear
`delegate_log`.

Effective 2026-09-17 (GH #151): REPORT.md/BLOCKER.md must open with a
`# REPORT task-<id>` / `# BLOCKER task-<id>` header naming the EXACT task
id being polled — see `_header_task_id`. A file missing that header, or
naming a different task, is never flipped on; a stale/wrong-task file
(task-424077a4 inherited a stray Higgsfield report checked out from a
committed-on-main REPORT.md) must never be read as this task's own report
again. No grandfather clause for pre-2026-09-17 branches — the header is
required unconditionally from here on.

Git is the only cross-machine channel (design doc §3 rule 2) — this is the
hub-side half of that contract. tools/delegate.py's `_spawn_remote` is the
spoke-side half: it clones the worktree in and hands off; this file is what
notices the branch coming back out.

Run:  python -m runners.branch_poller          (loop, POLL_SECONDS)
      python -m runners.branch_poller --once   (single tick, for tests)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db  # noqa: E402
from lib.config import get_project, host as get_host  # noqa: E402
from lib.logger import get_logger  # noqa: E402
from tools.worker_reap import close_remote  # noqa: E402

POLL_SECONDS = 60
SSH_TIMEOUT_S = 20
GIT_TIMEOUT_S = 20

# GAP 2 (task-59780ac3): how long the newest commit on a finished remote
# branch must sit untouched before branch_poller will close that worker's
# surface — proof it has stopped pushing, not evidence by itself (a worker
# mid-render writes nothing new for much longer than this; REPORT.md having
# landed is the actual "done" signal, this just rules out "still mid-push").
REVIEW_CLOSE_QUIET_S = 5 * 60

_LOGGER = None


def _log():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger("branch_poller")
    return _LOGGER


def _run(cmd: list[str], *, cwd: str | None = None,
         timeout: float = GIT_TIMEOUT_S) -> subprocess.CompletedProcess:
    """subprocess.run that never raises — a poller tick surviving a bad git/
    ssh/gh call (offline Mac, dead network, gh not authed) matters more than
    it seeing the exact exception; callers just get a nonzero returncode."""
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def remote_branch_exists(repo_path: str, branch: str) -> bool:
    """`git ls-remote origin refs/heads/<branch>` — True iff it lists
    something. Read-only, no local fetch."""
    r = _run(["git", "ls-remote", "origin", f"refs/heads/{branch}"], cwd=repo_path)
    return r.returncode == 0 and bool(r.stdout.strip())


def fetch_branch(repo_path: str, branch: str) -> bool:
    r = _run(["git", "fetch", "origin", branch], cwd=repo_path)
    if r.returncode != 0:
        _log().warning("fetch origin %s failed in %s: %s", branch, repo_path,
                       (r.stderr or "").strip()[:300])
    return r.returncode == 0


def read_remote_file(repo_path: str, branch: str, file_name: str) -> str | None:
    """`git show origin/<branch>:<file_name>`, or None if the file (or the
    ref) is absent — a missing REPORT.md/BLOCKER.md is an expected, normal
    "still working" state, never an error to raise on."""
    r = _run(["git", "show", f"origin/{branch}:{file_name}"], cwd=repo_path)
    if r.returncode != 0:
        return None
    return r.stdout


def remote_commit_age_seconds(repo_path: str, branch: str) -> float | None:
    """Seconds since the newest commit on `origin/<branch>` — the branch
    must already be fetched by the caller (fetch_branch); this never fetches
    on its own. None on any git failure (ref missing, empty/non-numeric
    output) — callers must treat that as "cannot prove it's quiet yet",
    never as "old enough"."""
    r = _run(["git", "log", "-1", "--format=%ct", f"origin/{branch}"], cwd=repo_path)
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    if not out:
        return None
    try:
        commit_epoch = int(out)
    except ValueError:
        return None
    return time.time() - commit_epoch


def _maybe_close_finished_remote_worker(task_id: str, repo_path: str, branch: str) -> None:
    """Close a remote worker's surface right after its task flips to
    `review` (GAP 2, task-59780ac3) — the gap measured 2026-09-08: on the
    Mac the CTO sees the iTerm tab and closes it at merge_task, but nobody
    watches a remote box, so task-5d0bd2fa's winbox claude.exe + terminal
    window sat alive for 5h54m after REPORT.md landed, until the CTO killed
    them by hand.

    A remote worker that pushed REPORT.md has declared itself finished — its
    entire output is in git, the process holds nothing more to give. But the
    CEO's hard rule (2026-09-07) is that a surface must NEVER be closed
    under a worker that may still be working (it could be waiting on a
    render), so this only acts when ALL of:
      (a) task.host is a remote spoke,
      (b) status is still 'review' on a fresh re-read here — a merge or a
          re-delegate could have raced the flip above,
      (c) REPORT.md is still present on the branch,
      (d) the branch's newest commit is at least REVIEW_CLOSE_QUIET_S old —
          proof the worker has actually stopped pushing, not mid-push.

    Passes close_remote's `allow_review=True` opt-in explicitly — no other
    caller in this codebase does. Never raises: a failure here must never
    undo the status flip that already landed; each early return is a normal
    "not eligible yet", not an error.
    """
    try:
        task = db.get_task(task_id)
    except Exception as e:
        _log().warning("task %s: could not re-read for review-close: %s", task_id, e)
        return
    if not task:
        return
    host = task.get("host")
    if not host or host == "mac":
        return
    if task.get("status") != "review":
        return
    if read_remote_file(repo_path, branch, "REPORT.md") is None:
        return
    age = remote_commit_age_seconds(repo_path, branch)
    if age is None or age < REVIEW_CLOSE_QUIET_S:
        return
    reap = close_remote(task, reason="branch_poller: REPORT.md pushed and quiet",
                        allow_review=True)
    _log().info("task %s: review-close attempted host=%s ssh_ok=%s refused=%s",
               task_id, host, reap.get("ssh_ok"), reap.get("refused"))


def remote_pid_alive(host_cfg: dict, pid: int) -> bool | None:
    """True/False from a live `tasklist` check; None if the host couldn't be
    reached at all — "unreachable" must never collapse into "dead", or a
    Wi-Fi blip fails a task that is still running fine."""
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias:
        return None
    r = _run(["ssh", ssh_alias, "tasklist", "/FI", f'"PID eq {pid}"'],
             timeout=SSH_TIMEOUT_S)
    if r.returncode != 0:
        return None
    return str(pid) in r.stdout


def open_blocker_issue(task_id: str, title_line: str, body: str) -> str | None:
    """`gh issue create` for a pushed BLOCKER.md. Returns the issue URL, or
    None on failure — never raises; a poller tick must survive `gh` being
    unauthenticated, offline, or rate-limited."""
    title = f"[{task_id}] {title_line}"[:250]
    r = _run(["gh", "issue", "create", "--title", title, "--body", body],
             timeout=SSH_TIMEOUT_S)
    if r.returncode != 0:
        _log().warning("gh issue create failed for %s: %s", task_id,
                       (r.stderr or "").strip()[:300])
        return None
    out = r.stdout.strip()
    return out.splitlines()[-1] if out else None


def parse_worker_json(text: str) -> dict:
    """Parse a `.worker.json` blob (written by windows/spawn-worker.ps1):
    `{"pid": int, "started_at": <ISO8601 str>, "host": str}`. Raises
    ValueError with a clear message on any missing/malformed field — a
    malformed file must read as an error, never silently as "no data yet"."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f".worker.json is not an object: {text!r}")
    missing = [k for k in ("pid", "started_at", "host") if k not in data]
    if missing:
        raise ValueError(f".worker.json missing field(s) {missing}: {text!r}")
    if not isinstance(data["pid"], int):
        raise ValueError(f".worker.json pid is not an int: {data['pid']!r}")
    return data


_HEADER_RE_TEMPLATE = r"^#\s*{kind}\s+(task-\S+)\s*$"


def _header_task_id(content: str, kind: str) -> str | None:
    """The task id named on a REPORT.md/BLOCKER.md's first line, or None if
    that line is missing or doesn't match `# {kind} task-<id>` exactly
    (`kind` is "REPORT" or "BLOCKER"). Whitespace-only content and a blank
    first line both read as "no header" rather than raising."""
    stripped = content.strip()
    if not stripped:
        return None
    first_line = stripped.splitlines()[0].strip()
    m = re.match(_HEADER_RE_TEMPLATE.format(kind=kind), first_line)
    return m.group(1) if m else None


def check_task(task: dict) -> None:
    """One task's tick. Never raises — a bad/malformed row must not kill
    the loop for every other task."""
    task_id = task["id"]
    branch = task.get("branch")
    host_name = task.get("host")
    if not branch or not host_name or host_name == "mac":
        return

    try:
        proj = get_project(task["project"])
    except ValueError as e:
        _log().warning("task %s: unknown project %s: %s", task_id, task.get("project"), e)
        return
    repo_path = proj.get("path")
    if not repo_path:
        _log().warning("task %s: project %s has no mac path to poll from",
                       task_id, task.get("project"))
        return

    if remote_branch_exists(repo_path, branch):
        fetch_branch(repo_path, branch)

        report = read_remote_file(repo_path, branch, "REPORT.md")
        if report is not None:
            header_id = _header_task_id(report, "REPORT")
            if header_id != task_id:
                found = header_id or "no header"
                _log().warning(
                    "task %s: REPORT.md header mismatch (%s) on %s — refusing",
                    task_id, found, branch,
                )
                db.set_fields(
                    task_id, actor="branch_poller",
                    delegate_log=(
                        f"REPORT.md header mismatch on {branch}: found "
                        f"{found!r}, expected 'task {task_id}' — refusing to "
                        "flip to review"
                    ),
                )
                return
            db.update_status(task_id, "review", report=report, actor="branch_poller")
            _log().info("task %s -> review (REPORT.md on %s)", task_id, branch)
            _maybe_close_finished_remote_worker(task_id, repo_path, branch)
            return

        blocker = read_remote_file(repo_path, branch, "BLOCKER.md")
        if blocker is not None:
            header_id = _header_task_id(blocker, "BLOCKER")
            if header_id != task_id:
                found = header_id or "no header"
                _log().warning(
                    "task %s: BLOCKER.md header mismatch (%s) on %s — refusing",
                    task_id, found, branch,
                )
                db.set_fields(
                    task_id, actor="branch_poller",
                    delegate_log=(
                        f"BLOCKER.md header mismatch on {branch}: found "
                        f"{found!r}, expected 'task {task_id}' — refusing to "
                        "flip to blocked_human"
                    ),
                )
                return
            # First line is the mandatory header; the issue title/body come
            # from the worker's actual blocker text, the line after it.
            body_lines = [ln for ln in blocker.strip().splitlines() if ln.strip()]
            first_line = body_lines[1] if len(body_lines) > 1 else "blocked"
            issue_url = open_blocker_issue(task_id, first_line, blocker)
            log_line = f"remote worker blocked: {first_line}"
            if issue_url:
                log_line += f" — {issue_url}"
            db.update_status(task_id, "blocked_human", delegate_log=log_line,
                             actor="branch_poller")
            _log().info("task %s -> blocked_human (%s)", task_id, log_line)
            return

        # Branch exists but neither REPORT.md nor BLOCKER.md landed yet —
        # still working, no state change.
        return

    # No branch pushed yet. Before treating this as "still working", check
    # whether the remote process is even still alive.
    pid = task.get("pid")
    if not pid:
        return
    try:
        host_cfg = get_host(host_name)
    except ValueError:
        return
    alive = remote_pid_alive(host_cfg, pid)
    if alive is False:
        db.update_status(
            task_id, "failed",
            delegate_log="remote worker died before pushing",
            actor="branch_poller",
        )
        _log().warning("task %s -> failed (pid %s gone on %s, no branch pushed)",
                       task_id, pid, host_name)


def tick() -> int:
    """One poll pass over every in-progress remote task. Returns the count
    of tasks checked (not how many changed — 0 changes on a normal tick is
    the common case, not a problem)."""
    tasks = [
        t for t in db.list_tasks(status="in_progress", limit=500)
        if t.get("host") and t.get("host") != "mac"
    ]
    for t in tasks:
        try:
            check_task(t)
        except Exception as e:  # a bad task must never kill the loop
            _log().error("check_task failed for %s: %s", t.get("id"), e)
    return len(tasks)


def main() -> None:
    once = "--once" in sys.argv
    db.init()
    _log().info("branch_poller starting (poll=%ss once=%s)", POLL_SECONDS, once)
    while True:
        try:
            n = tick()
            if n:
                _log().info("tick: checked %d remote task(s)", n)
        except Exception as e:
            _log().error("tick failed: %s", e)
        if once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
