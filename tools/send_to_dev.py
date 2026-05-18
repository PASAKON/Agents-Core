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


PREFIX = "[CTO]:"


def _send(full_id: str, message: str) -> None:
    """Send message to tab whose title contains the full task id, or
    fall back to a 6-char slice match for tabs spawned before the
    full-id title change."""
    text = f"{PREFIX} {message}"
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')
    fallback = full_id[:6]
    script = f'''
tell application "iTerm"
  activate
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      tell t
        if name of current session contains "{full_id}" then
          select t
          tell current session
            write text "{escaped}" newline NO
            write text (ASCII character 13) newline NO
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
              write text "{escaped}" newline NO
              write text (ASCII character 13) newline NO
            end tell
          end if
        end tell
      end repeat
    end repeat
  end if
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: python -m tools.send_to_dev <task_id_or_prefix> "<message>"',
              file=sys.stderr)
        return 1
    needle, message = sys.argv[1], sys.argv[2]

    db.init()
    task = db.get_task(needle)
    if not task:
        from lib.db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM tasks WHERE id LIKE ? LIMIT 1",
                (f"{needle}%",),
            ).fetchone()
        if not row:
            print(f"no task matching {needle}", file=sys.stderr)
            return 2
        task = db.get_task(row[0])

    tid = task["id"]
    _send(tid, message)
    print(f"sent to tab matching {tid}: {PREFIX} {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
