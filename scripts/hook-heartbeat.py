#!/usr/bin/env python3
"""PostToolUse hook: session heartbeat for the Project Monitor.

Org restructure P3-C (docs/plans/org-restructure-p3-plan.md), signal 1. A session
that has `CXO_SESSION_ID` or `WORKER_TASK_ID` in its env appends one JSON line

    {"session_id": "...", "task_id": "..." | null, "ts": "2026-10-15T00:21:27Z"}

to state/reports/heartbeat.jsonl, at most once a minute per session. Hooks run under
the SYSTEM python3, which has no `ORG_DB_URL` and no psycopg, so the hub is not
reachable from here: tools/heartbeat_fold.py (run by the live-sessions publisher,
which has the hub env) folds the file into `session_heartbeats` and
`projects.last_active`.

  - A worker (`WORKER_TASK_ID` set) writes session_id "worker-<task id>" and its
    task id; the fold maps the task to its Project Head's project. Any other session
    writes its `CXO_SESSION_ID` with a null task id; the fold maps a Project Head to
    its project through state/locks/project_head-<id>.project.
  - The once-a-minute gate is the mtime of a stamp file,
    state/reports/heartbeat.d/<key>, where key is the session_id above, so a Project
    Head and its workers each beat on their own.
  - Root: `ORG_ROOT` when set (runners/worker_init.py exports the hub checkout on
    every worker spawn; a worker's own `__file__` is its worktree, which has no
    state/ of its own), else this file's checkout.

FAIL-OPEN CONTRACT: this runs after every tool call, so it never blocks, never prints
and always exits 0 (a bad env, an id that is not a plain token, an unwritable
directory: all silent). stdlib only and no `re` / `json` import, to stay well under
50 ms. The payload on stdin is drained and ignored, so the harness never gets EPIPE.
Timing is in the task report. It does not register itself; the settings.json entry is
a separate step.
"""
import os
import sys
import time

STAMP_S = 60


def _token(value):
    """`value` when it is a plain ASCII token (it becomes a file name and a JSON
    string with no escaping), else ""."""
    value = (value or "").strip()
    if not 0 < len(value) <= 64 or not value.isascii() or not value[0].isalnum():
        return ""
    return value if all(c.isalnum() or c in "._-" for c in value) else ""


def beat():
    task = _token(os.environ.get("WORKER_TASK_ID"))
    if task:
        session = "worker-" + task
    else:
        session = _token(os.environ.get("CXO_SESSION_ID"))
        if not session:
            return
    root = (os.environ.get("ORG_ROOT") or "").strip() or os.path.dirname(
        os.path.dirname(os.path.realpath(__file__)))
    reports = os.path.join(root, "state", "reports")
    stamp = os.path.join(reports, "heartbeat.d", session)
    now = time.time()
    try:
        if 0 <= now - os.stat(stamp).st_mtime < STAMP_S:
            return
    except OSError:
        pass
    os.makedirs(os.path.dirname(stamp), exist_ok=True)
    line = '{"session_id":"%s","task_id":%s,"ts":"%s"}\n' % (
        session, '"%s"' % task if task else "null",
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)))
    fd = os.open(os.path.join(reports, "heartbeat.jsonl"),
                 os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("ascii"))
    finally:
        os.close(fd)
    os.close(os.open(stamp, os.O_WRONLY | os.O_CREAT, 0o644))
    os.utime(stamp, None)


def main():
    try:
        if not sys.stdin.isatty():
            sys.stdin.buffer.read()
    except Exception:
        pass
    try:
        beat()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
