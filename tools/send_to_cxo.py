"""C-level cross-talk: type a message into another C-level's iTerm tab.

The sender (typically CTO/CMO/CGO/CFO acting on a request from CEO)
needs to ask a sibling C-level to do something (e.g. CTO → CFO for a
budget approval, CMO → CGO for an attribution check). This mirrors
`tools/send_to_dev.py` but targets C-level tabs identified by role +
session id (recorded by `scripts/cxo-claude.sh` in
`state/locks/<role>-active`).

The message is prefixed with `[<SENDER-ROLE>]:` so the receiving
C-level (and any onlooking human) can tell who is talking.

Usage:
    python -m tools.send_to_cxo <role> "<message>"
    python -m tools.send_to_cxo cfo "ขอ budget $500 สำหรับ FB ads campaign X"
    python -m tools.send_to_cxo --from cgo cfo "ROAS hit 4.2 — request +$1k uplift"
    python -m tools.send_to_cxo --spawn cfo "budget review needed"

`<role>` = target C-level (cto|cmo|cgo|cfo).
Sender role auto-detected from $CXO_ROLE env when invoked from within a
C-level chat tab; falls back to "CEO" when nothing is set.

--spawn (default OFF for Phase 2): open a new ephemeral iTerm tab for
the request instead of typing into the primary tab. Dedupe-checked:
reuses an alive tab with same topic-slug if created within 10 minutes.
"""
from __future__ import annotations

import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.config import display_for, is_c_level

ROOT = Path(__file__).resolve().parent.parent
LOCKS_DIR = ROOT / "state" / "locks"


def _active_session_id(role: str) -> str | None:
    """Return the most-recent C-level session id for `role`, or None.

    Looks first at the `<role>-active` pointer that cxo-claude.sh writes
    on boot. Falls back to the newest matching `.winid` file so we still
    work for sessions started before this helper existed.
    """
    pointer = LOCKS_DIR / f"{role}-active"
    if pointer.exists():
        sid = pointer.read_text().strip()
        if sid:
            return sid
    candidates = sorted(
        LOCKS_DIR.glob(f"{role}-*.winid"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in candidates:
        sid = p.stem.split("-", 1)[1]
        if sid != "active":
            return sid
    return None


def _resolve_sender_role() -> str:
    """Best-effort sender label. CEO when no C-level env is set."""
    r = os.environ.get("CXO_ROLE")
    if r and is_c_level(r):
        return display_for(r)
    if os.environ.get("CTO_SESSION_ID"):
        return display_for("cto")
    return "CEO"


def _send(role: str, session_id: str, message: str, sender: str) -> None:
    """Type `[SENDER]: message\\n` into the C-level tab for (role, session_id)."""
    display = display_for(role)
    tab_match = f"{display} Chat #{session_id}"
    text = f"[{sender}]: {message}"
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "iTerm"
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      tell t
        try
          set tabName to ""
          try
            set tabName to name of t
          end try
          set sessName to ""
          try
            set sessName to name of current session of t
          end try
          if (tabName contains "{tab_match}") or (sessName contains "{tab_match}") then
            tell w to select
            tell t to select
            tell current session
              write text "{escaped}" newline NO
              write text (ASCII character 13) newline NO
            end tell
            set didSend to true
          end if
        end try
      end tell
    end repeat
  end repeat
  if not didSend then error "no iTerm tab matched {tab_match}"
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


# ---------------------------------------------------------------------------
# Spawn-path helpers (--spawn flag, Phase 2)
# ---------------------------------------------------------------------------

def _make_topic_slug(message: str) -> str:
    """First 30 chars of message lowercased → kebab slug, ≤30 chars."""
    raw = message[:30].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug[:30]


def _get_live_winids() -> set[str]:
    """Return the set of live iTerm2 window ids as strings."""
    r = subprocess.run(
        ["osascript", "-e", 'tell application "iTerm2" to return id of windows'],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return set()
    return set(r.stdout.strip().replace(" ", "").split(","))


def _send_to_ephemeral_tab(tab_title: str, text: str) -> None:
    """Type `text` into an existing ephemeral tab matched by its full title."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    escaped_title = tab_title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "iTerm"
  set didSend to false
  repeat with w in windows
    repeat with t in tabs of w
      tell t
        try
          set tabName to ""
          try
            set tabName to name of t
          end try
          set sessName to ""
          try
            set sessName to name of current session of t
          end try
          if (tabName contains "{escaped_title}") or (sessName contains "{escaped_title}") then
            tell w to select
            tell t to select
            tell current session
              write text "{escaped}" newline NO
              write text (ASCII character 13) newline NO
            end tell
            set didSend to true
          end if
        end try
      end tell
    end repeat
  end repeat
  if not didSend then error "no iTerm tab matched {escaped_title}"
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


def _spawn_new_ephemeral(
    role: str, session_id: str, tab_title: str, initial_text: str
) -> None:
    """Open a new iTerm window running cxo-claude.sh for role/session.

    Writes a temp shell script so Unicode / special chars in initial_text
    never need escaping inside an AppleScript string literal.
    """
    def _sh_sq(s: str) -> str:
        return "'" + s.replace("'", "'\"'\"'") + "'"

    cxo_sh = str(ROOT / "scripts" / "cxo-claude.sh")
    shell_cmd = " ".join([
        f"export CXO_SESSION_ID={_sh_sq(session_id)}",
        "&&",
        "bash", _sh_sq(cxo_sh),
        "--role", role,
        "--session", _sh_sq(session_id),
        "--tab-title", _sh_sq(tab_title),
        "--initial-prompt", _sh_sq(initial_text),
    ])

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, dir="/tmp"
    ) as tmp:
        tmp.write("#!/usr/bin/env bash\n")
        tmp.write(shell_cmd + "\n")
        tmp_path = tmp.name
    os.chmod(tmp_path, 0o755)

    title_as = tab_title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "iTerm"
  set newWindow to (create window with default profile)
  tell newWindow
    tell current session of current tab
      set name to "{title_as}"
      write text "bash {tmp_path}"
    end tell
  end tell
end tell
'''
    try:
        subprocess.run(["osascript", "-e", script], check=True)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def spawn(role: str, message: str, sender: str | None = None) -> str:
    """Ephemeral-spawn path: open a new tab for this request.

    Dedupe-checked: if an alive ephemeral tab with the same topic-slug
    was created within the last 10 minutes, reuse it instead of opening
    a second tab. Does NOT write the `<role>-active` pointer.
    """
    if not is_c_level(role):
        raise ValueError(
            f"{role} is not a C-level role. Known C-level: cto, cmo, cgo, cfo"
        )
    label = sender or _resolve_sender_role()
    display = display_for(role)
    topic_slug = _make_topic_slug(message)
    tab_title = f"{display.upper()} <- CTO: {topic_slug}"
    full_text = f"[{label}]: {message}"

    # Dedupe: scan existing ephemeral lock files for this role
    live_winids = _get_live_winids()
    ten_min_ago = time.time() - 600

    for lock_file in sorted(
        LOCKS_DIR.glob(f"{role}-req-*.winid"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        try:
            winid = lock_file.read_text().strip()
            if winid not in live_winids:
                continue  # stale — cleanup-zombies.sh handles removal
            if lock_file.stat().st_mtime < ten_min_ago:
                continue
            topic_file = lock_file.with_suffix(".topic")
            if not topic_file.exists():
                continue
            if topic_file.read_text().strip() != topic_slug:
                continue
            # Match: reuse this alive ephemeral tab
            _send_to_ephemeral_tab(tab_title, full_text)
            return f"reused {display} ephemeral tab {lock_file.stem}: {full_text}"
        except OSError:
            continue

    # No alive matching tab — spawn new
    session_id = f"req-{secrets.token_hex(4)}"
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    topic_path = LOCKS_DIR / f"{role}-{session_id}.topic"
    topic_path.write_text(topic_slug)

    try:
        _spawn_new_ephemeral(role, session_id, tab_title, full_text)
    except Exception:
        topic_path.unlink(missing_ok=True)
        raise

    return f"spawned new {display} tab [{session_id}]: {full_text}"


def send(role: str, message: str, sender: str | None = None) -> str:
    """Programmatic API (legacy path). Returns one-line summary string."""
    if not is_c_level(role):
        raise ValueError(
            f"{role} is not a C-level role. Known C-level: cto, cmo, cgo, cfo"
        )
    sid = _active_session_id(role)
    if not sid:
        raise ValueError(
            f"no active {display_for(role)} session found. "
            f"Spawn one first: bash scripts/spawn-cxo.sh --role {role}"
        )
    label = sender or _resolve_sender_role()
    _send(role, sid, message, label)
    return f"sent to {display_for(role)} #{sid}: [{label}]: {message}"


def main() -> int:
    argv = sys.argv[1:]
    sender_override = None
    do_spawn = False

    remaining: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--spawn":
            do_spawn = True
        elif a == "--from":
            if i + 1 >= len(argv):
                print("--from requires a role argument", file=sys.stderr)
                return 1
            r = argv[i + 1]
            sender_override = display_for(r) if is_c_level(r) else r
            i += 1
        else:
            remaining.append(a)
        i += 1
    argv = remaining

    if len(argv) < 2:
        print(
            'usage: python -m tools.send_to_cxo [--spawn] [--from <role>] <target_role> "<message>"',
            file=sys.stderr,
        )
        return 1
    role, message = argv[0], argv[1]
    try:
        if do_spawn:
            result = spawn(role, message, sender_override)
        else:
            result = send(role, message, sender_override)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") if hasattr(e, "stderr") else ""
        print(f"AppleScript failed: {stderr or e}", file=sys.stderr)
        return 3
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
