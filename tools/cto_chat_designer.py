"""CTO -> Web Designer direct chat.

Spawns `claude` in the designer's git worktree (read from tasks DB),
pipes the prompt via stdin, streams claude's stdout back to the CTO
terminal AND tees it to the same mirror log the tmux passive viewer
tails. End result: CTO can drive the designer from iTerm without
opening the claudesign Web UI, and the designer keeps full conversation
context via `claude --continue`.

Why this exists:
  - `tools/send_to_dev.py` only types into a visible iTerm tab. The
    web_designer pane is a `tail -F mirror.log` viewer (see
    `runners/dev_init.py` line ~115), not a claude TUI — typing into it
    is a no-op.
  - `claudesign_tmux_bin.py` is the bridge claudesign daemon spawns
    when the Web UI fires a prompt. This module is the CTO-side
    counterpart that bypasses the Web UI.

Usage:
    python -m tools.cto_chat_designer <task_id> "<prompt>"
    python -m tools.cto_chat_designer task-88536568 "tighten the hero spacing"

The first invocation seeds a new claude session in the worktree; later
invocations use `--continue` so the designer remembers prior turns.
Output is streamed both to the CTO terminal and to
`/tmp/mooniex-mirror-<task_id>.log`.
"""
from __future__ import annotations

import shutil
import sys
import threading
from pathlib import Path
from subprocess import PIPE, Popen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db

MIRROR_DIR = Path("/tmp")


def _resolve_claude_bin() -> str:
    """Locate the real `claude` CLI even under a stripped PATH.

    Mirrors claudesign_tmux_bin._resolve_claude_bin. Normally this module
    runs from an interactive CTO shell (so `which` succeeds), but the same
    candidate-walk keeps it alive if ever spawned under a GUI/nohup PATH
    that lacks ~/.local/bin — where the native-installer claude now lives.
    """
    found = shutil.which("claude")
    if found:
        return found
    home = Path.home()
    candidates = [
        home / ".local/bin/claude",        # native installer (2.x)
        home / ".claude/local/claude",     # legacy local install
        Path("/opt/homebrew/bin/claude"),  # apple-silicon homebrew
        Path("/usr/local/bin/claude"),     # intel homebrew / manual
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "claude"  # last resort — let exec surface a clear PATH error


CLAUDE_BIN = _resolve_claude_bin()
SESSION_MARKER_DIR = Path.home() / ".claude" / "projects"


def _resolve_task(needle: str) -> dict:
    """Accept full task id or prefix; return task row dict."""
    db.init()
    task = db.get_task(needle)
    if task:
        return task
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM tasks WHERE role='web_designer' "
            "AND (id=? OR id LIKE ? OR id LIKE ?) "
            "ORDER BY updated_at DESC LIMIT 1",
            (needle, f"{needle}%", f"%{needle}"),
        ).fetchone()
    if not row:
        raise ValueError(f"no web_designer task matching: {needle}")
    return db.get_task(row[0])


def _has_prior_session(worktree: Path) -> bool:
    """Cheap check for whether `claude --continue` will find a session.

    claude stores per-cwd sessions under ~/.claude/projects/<escaped-cwd>/.
    Absence means first run → omit --continue so claude starts fresh.
    """
    if not SESSION_MARKER_DIR.exists():
        return False
    escaped = str(worktree).replace("/", "-")
    return (SESSION_MARKER_DIR / escaped).exists()


def _pump_stdin(proc: Popen, payload: bytes) -> None:
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.write(payload)
            proc.stdin.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass


def send(task_id_or_prefix: str, prompt: str) -> int:
    """Run one prompt against the designer's worktree. Returns claude's exit code."""
    task = _resolve_task(task_id_or_prefix)
    if task["role"] != "web_designer":
        raise ValueError(
            f"task {task['id']} role is {task['role']}, expected web_designer"
        )

    worktree = task.get("worktree")
    if not worktree or not Path(worktree).is_dir():
        raise ValueError(f"worktree missing for task {task['id']}: {worktree}")

    task_id = task["id"]
    mirror_path = MIRROR_DIR / f"mooniex-mirror-{task_id}.log"
    mirror_path.touch(exist_ok=True)

    args = [CLAUDE_BIN, "-p", prompt]
    if _has_prior_session(Path(worktree)):
        args.append("--continue")

    sys.stderr.write(
        f"[cto->designer] task={task_id} worktree={worktree} "
        f"continue={'--continue' in args}\n"
    )
    sys.stderr.flush()

    proc = Popen(
        args, cwd=worktree, stdin=PIPE, stdout=PIPE, stderr=PIPE, bufsize=-1
    )

    threading.Thread(
        target=_pump_stdin, args=(proc, b""), daemon=True
    ).start()

    with mirror_path.open("ab") as mirror:
        marker = (
            f"\n--- cto chat-designer task={task_id} ---\n"
            f"[CTO]: {prompt}\n"
        ).encode()
        mirror.write(marker)
        mirror.flush()
        sys.stdout.write(marker.decode("utf-8", errors="replace"))
        sys.stdout.flush()

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
            sys.stderr.buffer.write(err_tail)
            sys.stderr.flush()
    except Exception:
        pass

    return proc.wait()


def main() -> int:
    if len(sys.argv) < 3:
        print(
            'usage: python -m tools.cto_chat_designer <task_id_or_prefix> "<prompt>"',
            file=sys.stderr,
        )
        return 1
    needle, prompt = sys.argv[1], sys.argv[2]
    try:
        return send(needle, prompt)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
