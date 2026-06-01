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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.config import display_for  # noqa: E402

CTO_TAB_FALLBACK_MATCH = "CTO Chat"


def send(from_id: str, message: str, role: str | None = None,
         cto_id: str | None = None) -> bool:
    """Type `[<Role> <from_id>]: <message>` into the CTO tab. Returns True
    if a matching tab was found.

    `role` is the DEV's role key (e.g. `web_designer`) and renders as
    the display label (e.g. `Web Designer`). Falls back to `[Dev:<from_id>]:`
    when role is missing or unknown.

    `cto_id`: route to the CTO tab named `CTO Chat #<cto_id>` only. Falls
    back to broadcasting to every tab containing "CTO Chat" when None —
    used by legacy callers that don't know the owning CTO.
    """
    if role:
        prefix = f"[{display_for(role)} {from_id}]:"
    else:
        prefix = f"[Dev:{from_id}]:"
    text = f"{prefix} {message}"
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')
    # Two-pass routing: exact-match owner_cto first; if that tab is gone
    # (CTO crashed / respawned with new id), broadcast to any live
    # `CTO Chat #` tab so the DEV reply isn't lost. Fallback returns "2"
    # so the caller can log the reroute.
    primary = f"CTO Chat #{cto_id}" if cto_id else CTO_TAB_FALLBACK_MATCH
    fallback = CTO_TAB_FALLBACK_MATCH
    script = f'''
tell application "iTerm"
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      set tabName to ""
      try
        set tabName to name of t
      end try
      set sessName to ""
      try
        set sessName to name of current session of t
      end try
      if (tabName contains "{primary}") or (sessName contains "{primary}") then
        tell current session of t
          write text "{escaped}" newline NO
          write text (ASCII character 13) newline NO
        end tell
        set didSend to true
      end if
    end repeat
  end repeat
  if didSend then
    return "1"
  end if
  set didFallback to false
  repeat with w in windows
    repeat with t in tabs of w
      set tabName to ""
      try
        set tabName to name of t
      end try
      set sessName to ""
      try
        set sessName to name of current session of t
      end try
      if (tabName contains "{fallback}") or (sessName contains "{fallback}") then
        tell current session of t
          write text "{escaped}" newline NO
          write text (ASCII character 13) newline NO
        end tell
        set didFallback to true
      end if
    end repeat
  end repeat
  if didFallback then
    return "2"
  end if
  return "0"
end tell
'''
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    out = r.stdout.strip() if r.returncode == 0 else ""
    if out == "2":
        sys.stderr.write(
            f"[send_to_cto] owner_cto={cto_id} tab missing; "
            f"broadcast fallback to any CTO Chat # tab\n"
        )
    return out in ("1", "2")


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: python -m tools.send_to_cto <from_id> "<message>" [role] [cto_id]',
              file=sys.stderr)
        return 1
    role = sys.argv[3] if len(sys.argv) > 3 else None
    cto_id = sys.argv[4] if len(sys.argv) > 4 else None
    ok = send(sys.argv[1], sys.argv[2], role=role, cto_id=cto_id)
    print("sent" if ok else "no CTO tab matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
