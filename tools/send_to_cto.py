"""DEV -> owning C-level visible chat: type a message directly into the
owner's iTerm tab (title "CTO #<id> ..." live-summary format per
IRON-RULES §32, legacy "CTO Chat #<id>", or a CXO tab "CFO #<id> ..." —
all matched).

Mirror of tools/send_to_dev.py, opposite direction. Used by the DEV's
Stop hook so every DEV reply types into the owner's chat as a user prompt
- the CEO can watch the conversation flow in real time, and the owner's
claude TUI processes the DEV message as fresh input.

Routing (issue #15):
  * `cto_id` + `owner_role` pick the winid lock `state/locks/<role>-<id>.winid`
    (`_read_winid` falls back to the legacy `cto-<id>.winid` for non-cto
    roles). The message types ONLY into that one window — never broadcast.
  * `cto_id=None` (ownerless task) no longer broadcasts to every CTO tab.
    By default the message is dropped to `state/orphan-dev-replies-unowned.log`
    and False is returned. Single-CTO setups that want the old broadcast
    opt in via env `SEND_TO_CTO_BROADCAST=1`.

Usage:
    python -m tools.send_to_cto <from_id> "<message>" [role] [cto_id] [owner_role]
    python -m tools.send_to_cto task-161dbcf7 "patch ready, please review"
"""
from __future__ import annotations

import os
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


def _read_winid(cto_id: str, role: str = "cto") -> str | None:
    """Return the iTerm window id for the owning session, or None.

    Reads `state/locks/<role>-<cto_id>.winid` (cxo-claude.sh writes the lock
    as `<role>-<session>.winid`). When that file is missing and `role` is not
    "cto", falls back to the legacy `cto-<cto_id>.winid` name so older locks
    still resolve. Returns None if neither file exists or the content is not
    all digits.
    """
    candidates = [LOCKS_DIR / f"{role}-{cto_id}.winid"]
    if role != "cto":
        candidates.append(LOCKS_DIR / f"cto-{cto_id}.winid")
    for p in candidates:
        try:
            raw = p.read_text().strip()
        except OSError:
            continue
        if raw.isdigit():
            return raw
    return None


def _log_orphan(cto_id: str, from_id: str, role: str | None,
                message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    snippet = repr(message[:80])
    log_path = STATE_DIR / f"orphan-dev-replies-{cto_id}.log"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] from={from_id} role={role or 'unknown'} msg={snippet}\n")


def send(from_id: str, message: str, role: str | None = None,
         cto_id: str | None = None, owner_role: str = "cto") -> bool:
    """Type `[<Role> <from_id>]: <message>` into the owning session's tab.
    Returns True if a matching tab was found.

    `role` is the DEV's role key (e.g. `web_designer`) and renders as
    the display label (e.g. `Web Designer`). Falls back to `[Dev:<from_id>]:`
    when role is missing or unknown.

    `cto_id` + `owner_role`: route ONLY to the iTerm window whose id is stored
    in `state/locks/<owner_role>-<cto_id>.winid` (legacy `cto-<cto_id>.winid`
    fallback for non-cto roles). If the file is missing or the window is gone
    the message is dropped to `state/orphan-dev-replies-<cto_id>.log` and False
    is returned — no broadcast to other windows.

    When `cto_id` is None (ownerless task): the message is dropped to
    `state/orphan-dev-replies-unowned.log` and False is returned — NO broadcast.
    Set env `SEND_TO_CTO_BROADCAST=1` to restore the legacy broadcast to every
    "CTO Chat" / "CTO #" tab (single-CTO setups only).
    """
    if role:
        prefix = f"[{display_for(role)} {from_id}]:"
    else:
        prefix = f"[Dev:{from_id}]:"
    text = f"{prefix} {message}"
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')

    if cto_id:
        winid = _read_winid(cto_id, owner_role)
        if winid is None:
            _log_orphan(cto_id, from_id, role, message)
            sys.stderr.write(
                f"[send_to_cto] winid missing for cto={cto_id}; "
                f"message orphaned to state/orphan-dev-replies-{cto_id}.log\n"
            )
            return False

        # Match every title generation: legacy "CTO Chat #<id>", the
        # live-summary format "CTO #<id> <glyph> <summary>" (IRON-RULES §32),
        # and CXO tabs "CFO #<id> ..." (cxo-claude.sh TAB_TITLE). Session ids
        # are uuid4-hex8, so a bare "#<id>" contains-match is unique enough.
        script = f'''
tell application "iTerm"
  set didSend to false
  try
    set targetWin to window id {winid}
    repeat with t in tabs of targetWin
      try
        if (name of current session of t contains "CTO Chat") or (name of current session of t contains "#{cto_id}") then
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

    # Ownerless task (cto_id=None). The legacy broadcast typed the report into
    # EVERY CTO/CXO tab — cross-session pollution (issue #15). Default now: drop
    # to a shared unowned log and return False. Opt back in to the broadcast
    # only for single-CTO setups via SEND_TO_CTO_BROADCAST=1.
    if os.environ.get("SEND_TO_CTO_BROADCAST") != "1":
        _log_orphan("unowned", from_id, role, message)
        sys.stderr.write(
            f"[send_to_cto] ownerless message from {from_id} dropped to "
            f"state/orphan-dev-replies-unowned.log "
            f"(set SEND_TO_CTO_BROADCAST=1 to broadcast to all CTO tabs)\n"
        )
        return False

    # Legacy opt-in broadcast: type into every "CTO Chat" / "CTO #" tab.
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
        print('usage: python -m tools.send_to_cto <from_id> "<message>" '
              '[role] [cto_id] [owner_role]', file=sys.stderr)
        return 1
    role = sys.argv[3] if len(sys.argv) > 3 else None
    cto_id = sys.argv[4] if len(sys.argv) > 4 else None
    owner_role = sys.argv[5] if len(sys.argv) > 5 else "cto"
    ok = send(sys.argv[1], sys.argv[2], role=role, cto_id=cto_id,
              owner_role=owner_role)
    print("sent" if ok else "no CTO tab matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
