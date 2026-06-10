"""DEV -> CTO visible chat: type a message directly into the CTO's
iTerm tab (title "CTO #<id> ..." live-summary format per IRON-RULES §32,
or legacy "CTO Chat #<id>" — both matched).

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
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.config import display_for  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOCKS_DIR = ROOT / "state" / "locks"
STATE_DIR = ROOT / "state"
CTO_TAB_FALLBACK_MATCH = "CTO Chat"


def _read_winid(cto_id: str) -> str | None:
    """Return the iTerm window id for `cto_id`, or None if missing/invalid."""
    p = LOCKS_DIR / f"cto-{cto_id}.winid"
    try:
        raw = p.read_text().strip()
    except OSError:
        return None
    return raw if raw.isdigit() else None


def _log_orphan(cto_id: str, from_id: str, role: str | None,
                message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    snippet = repr(message[:80])
    log_path = STATE_DIR / f"orphan-dev-replies-{cto_id}.log"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] from={from_id} role={role or 'unknown'} msg={snippet}\n")


def send(from_id: str, message: str, role: str | None = None,
         cto_id: str | None = None) -> bool:
    """Type `[<Role> <from_id>]: <message>` into the CTO tab. Returns True
    if a matching tab was found.

    `role` is the DEV's role key (e.g. `web_designer`) and renders as
    the display label (e.g. `Web Designer`). Falls back to `[Dev:<from_id>]:`
    when role is missing or unknown.

    `cto_id`: route ONLY to the iTerm window whose id is stored in
    `state/locks/cto-<cto_id>.winid`. If the file is missing or the window
    is gone the message is dropped to `state/orphan-dev-replies-<cto_id>.log`
    and False is returned — no broadcast to other CTO windows.

    When `cto_id` is None (legacy callers): broadcast to every tab whose
    session name contains "CTO Chat", preserving pre-multi-CTO behaviour.
    """
    if role:
        prefix = f"[{display_for(role)} {from_id}]:"
    else:
        prefix = f"[Dev:{from_id}]:"
    text = f"{prefix} {message}"
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')

    if cto_id:
        winid = _read_winid(cto_id)
        if winid is None:
            _log_orphan(cto_id, from_id, role, message)
            sys.stderr.write(
                f"[send_to_cto] winid missing for cto={cto_id}; "
                f"message orphaned to state/orphan-dev-replies-{cto_id}.log\n"
            )
            return False

        # Match both title generations: legacy "CTO Chat #<id>" and the
        # live-summary format "CTO #<id> <glyph> <summary>" (IRON-RULES §32).
        script = f'''
tell application "iTerm"
  set didSend to false
  try
    set targetWin to window id {winid}
    repeat with t in tabs of targetWin
      try
        if (name of current session of t contains "CTO Chat") or (name of current session of t contains "CTO #{cto_id}") then
          tell current session of t
            write text "{escaped}" newline NO
            write text (ASCII character 13) newline NO
          end tell
          set didSend to true
          exit repeat
        end if
      end try
    end repeat
  end try
  if didSend then
    return "1"
  end if
  return "0"
end tell
'''
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True)
        out = r.stdout.strip() if r.returncode == 0 else ""
        if out != "1":
            _log_orphan(cto_id, from_id, role, message)
            sys.stderr.write(
                f"[send_to_cto] window id={winid} for cto={cto_id} not found; "
                f"message orphaned\n"
            )
            return False
        return True

    # Legacy path: cto_id=None — broadcast to all "CTO Chat" tabs.
    # Used by old callers that don't know the owning CTO (single-CTO setups).
    script = f'''
tell application "iTerm"
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      tell t
        if (name of current session contains "{CTO_TAB_FALLBACK_MATCH}") or (name of current session contains "CTO #") then
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
  end if
  return "0"
end tell
'''
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    out = r.stdout.strip() if r.returncode == 0 else ""
    return out == "1"


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
