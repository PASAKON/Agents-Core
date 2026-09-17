"""File-based org mailbox — the delivery mechanism for C-level cross-talk.

Task task-de2cdc15 (CEO directive 2026-08-14, option A: queue only, no wake
attempt). Replaces "type the message into a terminal" (iTerm AppleScript /
tmux send-keys), which failed silently three different ways in one day: GH
#69 (bytes landed in the sender's own session, `didSend` still true), a
swallowed Enter that left messages sitting unsubmitted in the composer, and
key-encoding differences that did nothing without raising. "Text is on
screen" was being read as "the message arrived" -- it isn't the same claim.

Delivery is redefined here as a much smaller claim: **the letter exists in
the recipient's box.** No terminal is typed into, no process is woken, no
tab is searched for. A box is inspectable with plain `ls` and delivery is
provable without running anything.

Storage: `state/inbox/<role>-<session_id>/<utc-compact-ts>-<from_role>-<from_sid>.json`
-- files, not a table (IRON §30 governs new tables; the codebase already
keys per-session sidecars this way: `.winid`, `.tty`, `.uuid`, `.spawned_by`
in state/locks/).

Routing (max-3-hop, reply-only-to-owner) is deliberately NOT enforced here.
`chain` is stored as a human-readable audit trail only -- it is data the
sender controls, so a forged or truncated chain must never be able to
unlock a deeper reach or a skip-the-owner reply. The routing guard lives in
`tools/send_to_cxo.py`'s `authorize()`, which resolves depth and ownership
from recorded state (`tasks.owner_role`/`owner_cto`, `state/locks/*.spawned_by`)
-- never from a letter's own `chain` field. This module only stores and
retrieves; enforcement is the caller's job.

Public surface: `send()`, `peek()`, `drain()`.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

def _resolve_root() -> Path:
    """Hub checkout root. `ORG_ROOT` (set by runners/worker_init.py on every
    worker spawn, GH #154) wins when present -- a worker's own `__file__`
    resolves to its worktree, which has no `state/` of its own, so a hook
    invoked as `${CLAUDE_PROJECT_DIR}/scripts/hook-inbox.py` from inside a
    worktree would otherwise import THIS module from the worktree's own
    `lib/` copy and drain a directory that doesn't exist. A hub-side process
    (CTO session, worker MCP server) never has `ORG_ROOT` set and falls back
    to `__file__` exactly as before."""
    org_root = os.environ.get("ORG_ROOT")
    if org_root and org_root.strip():
        return Path(org_root)
    return Path(__file__).resolve().parent.parent


ROOT = _resolve_root()

# Referenced via the module global at call time (never bound as a default
# argument value) so a test can monkeypatch `mailbox.INBOX_ROOT` and have
# every caller -- including one that already imported this module before
# the patch -- observe the override. Same idiom `tools/send_to_cxo.py` uses
# for `_run_osascript`.
INBOX_ROOT = ROOT / "state" / "inbox"


def _box(role: str, session_id: str, root: Path | None) -> Path:
    base = root if root is not None else INBOX_ROOT
    return base / f"{role}-{session_id}"


def _ts() -> str:
    """UTC compact timestamp, microsecond-resolution so two letters queued
    in the same box within the same second still sort and never collide."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def send(
    to_role: str,
    to_session_id: str,
    body: str,
    from_role: str,
    from_session_id: str,
    *,
    chain: list[str] | None = None,
    root: Path | None = None,
) -> Path:
    """Write one letter into (to_role, to_session_id)'s box. Returns the
    final path. Delivery == the file exists; nothing is typed anywhere.

    Atomic: a temp file is written in the SAME directory as the final
    letter, then `os.replace()`d into place. A concurrent `peek()`/`drain()`
    scanning the box with `glob("*.json")` never observes a partial write --
    the temp file's `.tmp` suffix doesn't match that glob until the rename
    makes it a `.json` file in one filesystem operation.
    """
    box = _box(to_role, to_session_id, root)
    box.mkdir(parents=True, exist_ok=True)
    letter = {
        "from": {"role": from_role, "session_id": from_session_id},
        "to": {"role": to_role, "session_id": to_session_id},
        "chain": list(chain) if chain else [f"{from_role}:{from_session_id}"],
        "sent_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "body": body,
    }
    final = box / f"{_ts()}-{from_role}-{from_session_id}.json"
    fd, tmp = tempfile.mkstemp(dir=str(box), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(letter, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, final)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return final


def _letters(role: str, session_id: str, root: Path | None) -> list[Path]:
    box = _box(role, session_id, root)
    if not box.is_dir():
        return []
    return sorted(box.glob("*.json"))


def peek(role: str, session_id: str, *, root: Path | None = None) -> list[dict]:
    """Non-destructive: every readable letter currently waiting, oldest
    first. Never deletes anything."""
    out = []
    for p in _letters(role, session_id, root):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def drain(role: str, session_id: str, *, root: Path | None = None) -> list[dict]:
    """Exactly-once: each letter is read, handed back, and only THEN
    deleted -- never delete-then-read. A letter that fails to parse is left
    in place rather than silently discarded, and is simply skipped (no
    output) -- this runs from a UserPromptSubmit hook on every prompt of
    every session, so it must never raise or print noise of its own."""
    out = []
    for p in _letters(role, session_id, root):
        try:
            letter = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        p.unlink(missing_ok=True)
        out.append(letter)
    return out
