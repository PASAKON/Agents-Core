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

Envelope mail (org restructure P1, `ORG_MAIL_ENVELOPE=1`, default off). Off,
nothing below changes a byte of what is written or read. On:
  * `send()` adds `id`, `subject` (the first 80 characters of the body when
    the caller gives none), `kind`, `prio` and `read_at` to the letter.
  * `drain()` marks a letter read instead of deleting it: the file moves to
    `<box>/read/` with `read_at` set, and read letters older than 7 days are
    pruned. `peek()` and every glob of `<box>/*.json` still see only unread
    letters, so a reader written before this change keeps working.
  * `list_letters()` / `read_letter()` serve the MCP tools and the CLI
    (`tools/letters.py`), always on the caller's own box (`current_box()`).
  * `wake_due()` / `note_wake()` debounce the wake nudge: an urgent letter
    wakes at once, a normal one when 3 are waiting or the oldest has waited
    `ORG_WAKE_DEBOUNCE_S` (600 s). `tools/mail_wake_sweep.py` fires the late
    wake; with no live sweeper every letter wakes at once, as before.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import time
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
    subject: str | None = None,
    kind: str | None = None,
    prio: str | None = None,
) -> Path:
    """Write one letter into (to_role, to_session_id)'s box. Returns the
    final path. Delivery == the file exists; nothing is typed anywhere.

    Atomic: a temp file is written in the SAME directory as the final
    letter, then `os.replace()`d into place. A concurrent `peek()`/`drain()`
    scanning the box with `glob("*.json")` never observes a partial write --
    the temp file's `.tmp` suffix doesn't match that glob until the rename
    makes it a `.json` file in one filesystem operation.

    `subject`, `kind` and `prio` are stored only in envelope mode (see the
    module docstring); off, they are ignored and the letter is unchanged.
    An unknown `kind` or `prio` raises ValueError before anything is written.
    """
    envelope = None
    if envelope_on():
        kind = kind or "message"
        prio = prio or "normal"
        if kind not in KINDS:
            raise ValueError(f"unknown letter kind {kind!r}; one of {', '.join(KINDS)}")
        if prio not in PRIOS:
            raise ValueError(f"unknown letter prio {prio!r}; one of {', '.join(PRIOS)}")
        envelope = {"id": _new_id(), "subject": resolve_subject(subject, body)[0],
                    "kind": kind, "prio": prio, "read_at": None}
    box = _box(to_role, to_session_id, root)
    box.mkdir(parents=True, exist_ok=True)
    letter = {
        "from": {"role": from_role, "session_id": from_session_id},
        "to": {"role": to_role, "session_id": to_session_id},
        "chain": list(chain) if chain else [f"{from_role}:{from_session_id}"],
        "sent_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "body": body,
    }
    if envelope:
        letter.update(envelope)
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
    every session, so it must never raise or print noise of its own.

    Envelope mode: the letter is moved to `<box>/read/` with `read_at` set
    instead of being deleted (see `_archive`), and read letters past
    RETAIN_DAYS are pruned. Still exactly-once: an archived letter is no
    longer in the box, so no later drain returns it."""
    if envelope_on():
        return _drain_envelope(role, session_id, root)
    out = []
    for p in _letters(role, session_id, root):
        try:
            letter = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        p.unlink(missing_ok=True)
        out.append(letter)
    return out


# ---------------------------------------------------------------------------
# Envelope mail (org restructure P1, behind ORG_MAIL_ENVELOPE, default off)
# ---------------------------------------------------------------------------

ENVELOPE_ENV = "ORG_MAIL_ENVELOPE"
KINDS = ("message", "order", "report", "blocker", "answer", "notice")
PRIOS = ("normal", "urgent")
SUBJECT_MAX = 80
RETAIN_DAYS = 7
READ_DIR = "read"
WAKE_BATCH = 3                # this many waiting letters wake at once
DEFAULT_DEBOUNCE_S = 600.0    # ORG_WAKE_DEBOUNCE_S when unset or unreadable
SWEEP_STALE_S = 180.0         # a sweeper heartbeat older than this is dead
LAST_WAKE_FILE = ".last_wake"  # in the box; not *.json, so no reader sees it
SWEEP_BEAT_FILE = ".wake-sweep"  # in INBOX_ROOT, touched by every sweep
_ID_RE = re.compile(r"[A-Za-z0-9_.-]{1,96}")


def envelope_on() -> bool:
    """Read at call time, so a long-lived process (an MCP server) follows the
    env it was started with, and a test can flip it with monkeypatch."""
    return os.environ.get(ENVELOPE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def default_subject(body: str) -> str:
    """The first SUBJECT_MAX characters of the body, whitespace collapsed."""
    return " ".join(str(body or "").split())[:SUBJECT_MAX]


def resolve_subject(subject: str | None, body: str) -> tuple[str, str | None]:
    """(subject, warning). The warning is set when the caller gave no subject
    and the body's first characters stand in for it; the sending tool shows it
    to its caller."""
    given = " ".join(str(subject or "").split())[:SUBJECT_MAX]
    if given:
        return given, None
    return default_subject(body), (
        f"no subject given; used the first {SUBJECT_MAX} characters of the message")


def _new_id() -> str:
    return "m-" + secrets.token_hex(4)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fill(letter: dict, path: Path) -> dict:
    """Envelope fields for a letter written before envelope mode (or by a
    sender running with the flag off): the filename stem is its id."""
    letter.setdefault("id", path.stem)
    if not letter.get("subject"):
        letter["subject"] = default_subject(letter.get("body", ""))
    letter.setdefault("kind", "message")
    letter.setdefault("prio", "normal")
    letter.setdefault("read_at", None)
    return letter


def _read_box(box: Path) -> Path:
    return box / READ_DIR


def _archive(path: Path, letter: dict) -> None:
    """Move one unread letter to `<box>/read/` carrying `read_at`. Never
    raises: if the read copy cannot be written the letter is removed anyway,
    because a letter that stays unread would be delivered again on every
    prompt (exactly-once wins over keeping a copy)."""
    try:
        rd = _read_box(path.parent)
        rd.mkdir(exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(rd), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(letter, fh, ensure_ascii=False, indent=2)
            try:
                os.chmod(tmp, path.stat().st_mode & 0o777)
            except OSError:
                pass
            os.replace(tmp, rd / path.name)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
    except Exception:
        pass
    path.unlink(missing_ok=True)


def prune(box: Path, *, now: float | None = None) -> int:
    """Delete read letters older than RETAIN_DAYS (by the time they were
    read: the archive file's mtime). Returns how many went. Never raises."""
    cutoff = (now if now is not None else time.time()) - RETAIN_DAYS * 86400
    gone = 0
    try:
        for f in _read_box(box).glob("*.json"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
                    gone += 1
            except OSError:
                continue
    except Exception:
        pass
    return gone


def _drain_envelope(role: str, session_id: str, root: Path | None) -> list[dict]:
    out = []
    for p in _letters(role, session_id, root):
        try:
            letter = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        _fill(letter, p)
        letter["read_at"] = _iso_now()
        _archive(p, letter)
        out.append(letter)
    prune(_box(role, session_id, root))
    return out


def current_box() -> tuple[str, str] | None:
    """(role, session_id) of THIS process's own box, from env only -- the
    same resolution scripts/hook-inbox.py uses. Never from an argument: a
    caller cannot name somebody else's box."""
    role = os.environ.get("CXO_ROLE")
    if role:
        sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
        return (role, sid) if sid else None
    task_id = os.environ.get("WORKER_TASK_ID")
    if task_id:
        return os.environ.get("WORKER_ROLE", "dev"), task_id
    return None


def _summary(letter: dict, unread: bool) -> dict:
    frm = letter.get("from") or {}
    return {
        "id": letter.get("id"),
        "from": f"{frm.get('role', '?')}:{frm.get('session_id', '?')}",
        "subject": letter.get("subject"),
        "kind": letter.get("kind"),
        "prio": letter.get("prio"),
        "sent_at": letter.get("sent_at"),
        "read_at": letter.get("read_at"),
        "chars": len(str(letter.get("body") or "")),
        "unread": unread,
    }


def _parsed(paths) -> list[tuple[Path, dict]]:
    out = []
    for p in paths:
        try:
            out.append((p, _fill(json.loads(p.read_text(encoding="utf-8")), p)))
        except Exception:
            continue
    return out


def list_letters(role: str, session_id: str, *, root: Path | None = None,
                 include_read: bool = True, limit: int = 50) -> list[dict]:
    """Summaries (no body) of the box's letters, newest first: the unread
    ones, then (include_read) those read in the last RETAIN_DAYS."""
    items = [_summary(l, True) for _, l in _parsed(_letters(role, session_id, root))]
    if include_read:
        rd = _read_box(_box(role, session_id, root))
        if rd.is_dir():
            items += [_summary(l, False) for _, l in _parsed(sorted(rd.glob("*.json")))]
    items.sort(key=lambda d: (str(d.get("sent_at") or ""), str(d.get("id") or "")), reverse=True)
    return items[:max(0, int(limit))]


def read_letter(role: str, session_id: str, letter_id: str, *,
                root: Path | None = None) -> dict | None:
    """The whole letter with this id from the box, or None. An unread one is
    marked read on the way (envelope mode). The id is only ever compared,
    never joined into a path, and one that is not a plain token is refused."""
    if not isinstance(letter_id, str) or not _ID_RE.fullmatch(letter_id):
        return None
    for p, letter in _parsed(_letters(role, session_id, root)):
        if letter["id"] == letter_id:
            if envelope_on():
                letter["read_at"] = _iso_now()
                _archive(p, letter)
            return letter
    rd = _read_box(_box(role, session_id, root))
    if rd.is_dir():
        for _, letter in _parsed(sorted(rd.glob("*.json"))):
            if letter["id"] == letter_id:
                return letter
    return None


# --- wake debounce ------------------------------------------------------------

def debounce_s() -> float:
    raw = os.environ.get("ORG_WAKE_DEBOUNCE_S", "").strip()
    try:
        v = float(raw) if raw else DEFAULT_DEBOUNCE_S
    except ValueError:
        v = DEFAULT_DEBOUNCE_S
    return max(0.0, v)


def note_sweep(*, root: Path | None = None) -> None:
    """The sweeper's heartbeat. Never raises."""
    base = root if root is not None else INBOX_ROOT
    try:
        base.mkdir(parents=True, exist_ok=True)
        (base / SWEEP_BEAT_FILE).touch()
    except OSError:
        pass


def sweeper_alive(*, root: Path | None = None, now: float | None = None) -> bool:
    base = root if root is not None else INBOX_ROOT
    try:
        age = (now if now is not None else time.time()) - (base / SWEEP_BEAT_FILE).stat().st_mtime
    except OSError:
        return False
    return age <= SWEEP_STALE_S


def _last_wake(box: Path) -> float:
    try:
        return float((box / LAST_WAKE_FILE).read_text(encoding="utf-8").strip())
    except Exception:
        return 0.0


def note_wake(role: str, session_id: str, *, root: Path | None = None,
              now: float | None = None) -> None:
    """Record that this box was just woken: letters already waiting no longer
    count toward the next wake. Never raises."""
    box = _box(role, session_id, root)
    try:
        if box.is_dir():
            (box / LAST_WAKE_FILE).write_text(
                repr(now if now is not None else time.time()), encoding="utf-8")
    except OSError:
        pass


def waiting_since_wake(role: str, session_id: str, *, root: Path | None = None) -> list[float]:
    """Write times (file mtime: sub-second, unlike sent_at) of the unread
    letters that arrived after the box's last wake."""
    box = _box(role, session_id, root)
    last = _last_wake(box)
    out = []
    for p in _letters(role, session_id, root):
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if m > last:
            out.append(m)
    return out


def wake_due(role: str, session_id: str, prio: str = "normal", *,
             root: Path | None = None, now: float | None = None,
             sweeping: bool = False) -> bool:
    """Should the box be woken now?

    Flag off, an urgent letter, a debounce of 0, or (for a sender) no live
    sweeper to fire a late wake: yes, every time, as before. Otherwise yes
    once WAKE_BATCH letters have arrived since the last wake, or the oldest of
    them has waited debounce_s()."""
    if not envelope_on() or prio == "urgent":
        return True
    window = debounce_s()
    if window <= 0:
        return True
    t = now if now is not None else time.time()
    if not sweeping and not sweeper_alive(root=root, now=t):
        return True
    waiting = waiting_since_wake(role, session_id, root=root)
    if not waiting:
        return False
    return len(waiting) >= WAKE_BATCH or (t - min(waiting)) >= window
