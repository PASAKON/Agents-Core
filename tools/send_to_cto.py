"""DEV -> CTO visible chat: type a message directly into the CTO's
iTerm tab (title "CTO Chat", set by scripts/spawn-cto.sh).

Mirror of tools/send_to_dev.py, opposite direction. Used by the DEV's
Stop hook so every DEV reply types into the CTO chat as a user prompt
- the CEO can watch the conversation flow in real time, and the CTO's
claude TUI processes the DEV message as fresh input.

Usage:
    python -m tools.send_to_cto <from_id> "<message>"
    python -m tools.send_to_cto task-161dbcf7 "patch ready, please review"
"""
from __future__ import annotations

import subprocess
import sys

CTO_TAB_MATCH = "CTO"


def send(from_id: str, message: str) -> bool:
    """Type `[Dev:<from_id>]: <message>` into the CTO tab. Returns True if
    a matching tab was found."""
    prefix = f"[Dev:{from_id}]:"
    text = f"{prefix} {message}"
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')
    script = f'''
tell application "iTerm"
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      tell t
        if name of current session contains "{CTO_TAB_MATCH}" then
          tell current session
            write text "{escaped}" newline NO
            write text (ASCII character 13) newline NO
          end tell
          set didSend to true
        end if
      end tell
    end repeat
  end repeat
  if didSend then
    return "1"
  else
    return "0"
  end if
end tell
'''
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "1"


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: python -m tools.send_to_cto <from_id> "<message>"',
              file=sys.stderr)
        return 1
    ok = send(sys.argv[1], sys.argv[2])
    print("sent" if ok else "no CTO tab matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
