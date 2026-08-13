"""CTO -> DEV visible chat: type a message directly into the DEV's iTerm tab.

The message is prefixed with `[CTO]:` so the user (and the DEV's claude TUI)
can tell who is talking. Unlike MCP-based delegation, this leaves the work
fully visible -- every keystroke appears in the DEV's tab and the DEV's
response streams in real time.

Usage:
    python -m tools.send_to_dev <task_id_or_prefix> "<message>"
    python -m tools.send_to_dev task-161dbcf7 "status check please"

Tab matching: the spawn helper sets the iTerm tab title to
`<RoleDisplay> (<full_task_id>)` via an ANSI title escape. We match on the
full task id.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.iterm_type import type_submit_fragment
from tools import tmux_session as tmux


PREFIX = "[CTO]:"


def _send_tmux(session: str, message: str) -> None:
    """Type `[CTO]: <message>\\n` into the tmux session.

    Visible identically in every attached viewer (iTerm + browser ttyd).
    """
    text = f"{PREFIX} {message}"
    tmux.send_keys(session, text, press_enter=True)


def _run_osascript(script: str) -> subprocess.CompletedProcess:
    """Execute `script` via osascript, capturing rather than trusting exit
    code -- osascript exits 0 whether it matched an iTerm tab or looped over
    zero windows (GH #60). Isolated as its own function (rather than an
    inline `subprocess.run` call inside `_send`) so tests can substitute a
    fake runner -- callable that takes the assembled script and returns an
    object with `.returncode` / `.stdout`, matching `CompletedProcess` -- and
    simulate matched / unmatched / failed osascript without iTerm or a real
    `osascript` binary."""
    return subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=False,
    )


def _send(full_id: str, message: str, *, runner=None) -> bool:
    """Type message into the tab whose title contains the full task id, or
    fall back to a 6-char slice match for tabs spawned before the full-id
    title change. Returns True iff a tab actually matched and was typed
    into -- never True on a zero-iteration loop (GH #60).

    `runner` defaults to `_run_osascript` looked up dynamically (not bound
    as a default-arg value) so a test can monkeypatch the module-level
    `_run_osascript` name and have that take effect even for callers -- like
    `send()` -- that don't pass `runner` explicitly.
    """
    if runner is None:
        runner = _run_osascript
    text = f"{PREFIX} {message}"
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')
    submit = type_submit_fragment(escaped)
    fallback = full_id[:6]
    script = f'''
tell application "iTerm"
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      tell t
        if name of current session contains "{full_id}" then
          select t
          tell current session
            {submit}
          end tell
          set didSend to true
        end if
      end tell
    end repeat
  end repeat
  if not didSend then
    repeat with w in windows
      repeat with t in tabs of w
        tell t
          if name of current session contains "{fallback}" then
            select t
            tell current session
              {submit}
            end tell
            set didSend to true
          end if
        end tell
      end repeat
    end repeat
  end if
  if didSend then
    return "1"
  end if
  return "0"
end tell
'''
    result = runner(script)
    if result.returncode != 0:
        return False
    return result.stdout.strip() == "1"


def send(task_id: str, message: str) -> str:
    """Programmatic send. Resolves tmux vs iTerm, returns one-line summary.

    Contract: delivered or raised, never "probably" (GH #60). Raises
    RuntimeError when no tmux session and no iTerm tab (full id or 6-char
    fallback) matched -- it never returns a success string for a send that
    went nowhere.

    Used by `tools/delegate.py` for the mandatory kickoff ping (IRON-RULES
    §29); `_auto_kickoff` there already wraps this call in try/except and
    warns rather than propagating, so a raise here surfaces loudly without
    blocking the spawn or leaving the task row half-written.
    """
    db.init()
    task = db.get_task(task_id)
    if not task:
        from lib.db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM tasks WHERE id LIKE ? LIMIT 1",
                (f"{task_id}%",),
            ).fetchone()
        if not row:
            raise ValueError(f"no task matching {task_id}")
        task = db.get_task(row[0])

    tid = task["id"]
    tmux_sess = task.get("tmux_session")
    if tmux_sess and tmux.has_session(tmux_sess):
        _send_tmux(tmux_sess, message)
        return f"sent via tmux {tmux_sess}: {PREFIX} {message}"
    if not _send(tid, message):
        raise RuntimeError(
            f"send_to_dev: no iTerm tab matched task {tid} "
            f"(full id or 6-char fallback {tid[:6]}) -- message NOT "
            f"delivered: {PREFIX} {message}"
        )
    return f"sent to tab matching {tid}: {PREFIX} {message}"


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: python -m tools.send_to_dev <task_id_or_prefix> "<message>"',
              file=sys.stderr)
        return 1
    needle, message = sys.argv[1], sys.argv[2]
    try:
        result = send(needle, message)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
