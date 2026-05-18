#!/usr/bin/env python3
"""claudesign ↔ tmux/iTerm bridge.

Acts as a drop-in replacement for the `claude` CLI from claudesign daemon's
point of view. When claudesign spawns this binary:

  1. Resolves the active web_designer task from `os.getcwd()`
     (claudesign sets the child's cwd to the project folder, which we
     register as the agent's worktree).
  2. Spawns the real `claude` CLI with the same argv + reads prompt from
     stdin (claudesign passes `promptViaStdin: true`).
  3. Tees claude's stdout to:
       - this process's stdout (back to claudesign daemon for parsing)
       - `/tmp/mooniex-mirror-<task_id>.log` (visible in tmux pane
         `wd-<task_id>` via `tail -f`, which is what iTerm and ttyd
         attach to).

Falls back to bare `claude` exec if no matching task is found, so this
binary stays safe to use as a generic claude wrapper.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import threading
from pathlib import Path
from subprocess import PIPE, Popen

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "state" / "tasks.db"
MIRROR_DIR = Path("/tmp")
CLAUDE_BIN = shutil.which("claude") or "/opt/homebrew/bin/claude"


def _resolve_task(cwd: Path) -> tuple[str | None, str | None]:
    """Return (task_id, tmux_session) for the worktree at `cwd`, else (None, None).

    Walks parents in case daemon passes a subdir of the worktree.
    """
    if not DB_PATH.exists():
        return None, None
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        candidate = cwd
        for _ in range(8):
            row = conn.execute(
                "SELECT id, tmux_session FROM tasks "
                "WHERE worktree=? AND role='web_designer' "
                "AND status IN ('in_progress','pending','review') "
                "ORDER BY updated_at DESC LIMIT 1",
                (str(candidate),),
            ).fetchone()
            if row:
                return row["id"], row["tmux_session"]
            if candidate.parent == candidate:
                break
            candidate = candidate.parent
        return None, None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _pump_stdin(proc: Popen) -> None:
    try:
        data = sys.stdin.buffer.read()
        if data and proc.stdin and not proc.stdin.closed:
            proc.stdin.write(data)
            proc.stdin.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass


def main() -> int:
    cwd = Path(os.getcwd()).resolve()
    task_id, _tmux_sess = _resolve_task(cwd)

    args = [CLAUDE_BIN] + sys.argv[1:]

    # Bridge falls back to vanilla claude when no matching task is found.
    if not task_id:
        os.execvp(CLAUDE_BIN, args)
        return 0  # unreachable

    mirror_path = MIRROR_DIR / f"mooniex-mirror-{task_id}.log"
    mirror_path.touch(exist_ok=True)

    proc = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, bufsize=0)

    threading.Thread(target=_pump_stdin, args=(proc,), daemon=True).start()

    with mirror_path.open("ab") as mirror:
        marker = f"\n--- mooniex bridge run task={task_id} ---\n".encode()
        mirror.write(marker)
        mirror.flush()
        try:
            while True:
                chunk = proc.stdout.read1(4096) if proc.stdout else b""
                if not chunk:
                    break
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                mirror.write(chunk)
                mirror.flush()
        except (BrokenPipeError, OSError):
            pass

    try:
        err_tail = proc.stderr.read() if proc.stderr else b""
        if err_tail:
            with mirror_path.open("ab") as mirror:
                mirror.write(b"\n[stderr]\n" + err_tail + b"\n")
    except Exception:
        pass

    return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
