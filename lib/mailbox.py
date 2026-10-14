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
import stat
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
        prio = letter_prio(kind, prio)
        if kind not in KINDS:
            raise ValueError(f"unknown letter kind {kind!r}; one of {', '.join(KINDS)}")
        if prio not in PRIOS:
            raise ValueError(f"unknown letter prio {prio!r}; one of {', '.join(PRIOS)}")
        subj = resolve_subject(subject, body)[0]
        if kind != "order" and subj.lower().startswith("order #"):
            subj = ("re: " + subj)[:SUBJECT_MAX]   # only relay_to_session names an order
        envelope = {"id": _new_id(), "subject": subj,
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
    _log_meta(letter["sent_at"], f"{from_role}-{from_session_id}", f"{to_role}-{to_session_id}",
              kind if envelope else (kind or body_kind(body)), root)
    return final


# Who wrote to whom, when, and the kind: never the body (M11, the escalation watch,
# tools/escalation_watch.py). A drained letter is gone with the envelope off, so this
# is the only record that a PH's blocker was sent and whether its C-level answered.
META_NAME = "letters-meta.jsonl"
META_MAX_BYTES = 5 * 1024 * 1024
# "blocker · urgent · …" (roles/project_head.md: the kind is plain text until the
# envelope flag is on), after an optional "[From …] :" marker the MCP tool prepends
_BODY_KIND_RE = re.compile(r"^\s*(?:\[[^\]]{0,120}\]\s*:\s*)?([a-z]+)\s*\u00b7")


def body_kind(body: str) -> str | None:
    m = _BODY_KIND_RE.match(body or "")
    return m.group(1) if m and m.group(1) in KINDS else None


def meta_path(root: Path | None = None) -> Path:
    """ORG_LETTERS_META wins (every test points it into its tmp_path), else
    state/reports/ next to the inbox root the letter went to."""
    override = os.environ.get("ORG_LETTERS_META", "").strip()
    if override:
        return Path(override)
    return (root if root is not None else INBOX_ROOT).parent / "reports" / META_NAME


def _log_meta(sent_at: str, from_box: str, to_box: str, kind: str | None,
              root: Path | None = None) -> None:
    """Append one line; never raises (a letter is delivered whether or not this lands)."""
    try:
        path = meta_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.stat().st_size > META_MAX_BYTES:
                os.replace(path, path.with_suffix(".jsonl.1"))
        except FileNotFoundError:
            pass
        line = json.dumps({"sent_at": sent_at, "from": from_box, "to": to_box,
                           "kind": kind or "message"}, ensure_ascii=False) + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT
                     | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
    except Exception:
        pass


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
# kinds and prios as the org restructure plan's §6.2 names them (order, ask,
# blocker, report, fyi), plus message (no kind given) and answer (a reply to an ask)
KINDS = ("message", "order", "ask", "blocker", "report", "answer", "fyi")
PRIOS = ("normal", "urgent")
URGENT_KINDS = ("order", "ask", "blocker")   # their prio when the sender gives none
SUBJECT_MAX = 80
RETAIN_DAYS = 7
READ_DIR = "read"
WAKE_BATCH = 3                # this many waiting letters wake at once
DEFAULT_DEBOUNCE_S = 600.0    # ORG_WAKE_DEBOUNCE_S when unset or unreadable
SWEEP_STALE_S = 180.0         # a sweeper heartbeat older than this is dead
LAST_WAKE_FILE = ".last_wake"  # in the box; not *.json, so no reader sees it
SWEEP_BEAT_FILE = ".wake-sweep"  # in INBOX_ROOT, touched by every sweep
_ID_RE = re.compile(r"[A-Za-z0-9_.-]{1,96}")
_READ_CAP = 1 << 20           # a marker or letter read by a root process, at most

# Root processes (a C-level sender, the wake sweep) touch the files below in
# boxes the unprivileged COO user can write (its box is group/ACL-writable).
# So every such read or write is no-follow and non-blocking: a planted symlink
# or FIFO named `.last_wake`, `read` or `*.json` must never make root write,
# delete or hang outside the box.
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_DIRFD_OK = all(f in os.supports_dir_fd for f in (os.open, os.stat, os.unlink, os.mkdir, os.rename))


def _read_regular(path: Path) -> str | None:
    """Text of `path` if it is a regular file (not a symlink, FIFO or device),
    at most _READ_CAP bytes; None otherwise. Never raises."""
    try:
        fd = os.open(str(path), os.O_RDONLY | _NOFOLLOW | _NONBLOCK)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        return os.read(fd, _READ_CAP).decode("utf-8", "replace")
    except OSError:
        return None
    finally:
        os.close(fd)


def _open_dir(path: Path, *, dir_fd: int | None = None) -> int | None:
    """An fd on directory `path` (relative to `dir_fd` when given), opened
    no-follow: None when it is missing, a symlink or not a directory."""
    try:
        return os.open(str(path), os.O_RDONLY | _O_DIRECTORY | _NOFOLLOW, dir_fd=dir_fd)
    except OSError:
        return None


def _open_read_dir_at(bfd: int, *, create: bool, owned: bool = True) -> int | None:
    """An fd on `read/` inside the open box `bfd`, opened no-follow. `owned`:
    only a directory this process's user owns, so nothing is archived into or
    read from a `read/` another user planted. None when it cannot be had;
    never raises."""
    if create:
        try:
            os.mkdir(READ_DIR, dir_fd=bfd)
        except FileExistsError:
            pass
        except OSError:
            return None
    dfd = _open_dir(Path(READ_DIR), dir_fd=bfd)
    if dfd is not None and owned:
        try:
            mine = os.fstat(dfd).st_uid == os.geteuid()
        except OSError:
            mine = False
        if not mine:
            os.close(dfd)
            return None
    return dfd


def _open_read_dir(box: Path, *, create: bool, owned: bool = True) -> int | None:
    """`_open_read_dir_at` from a path: the box is opened no-follow first (the
    COO user's ACL reaches every box and the inbox root, so a box could be
    swapped for a link too)."""
    bfd = _open_dir(box)
    if bfd is None:
        return None
    try:
        return _open_read_dir_at(bfd, create=create, owned=owned)
    finally:
        os.close(bfd)


def _read_at(dfd: int, name: str) -> str | None:
    """`_read_regular` for an entry of an open directory."""
    try:
        fd = os.open(name, os.O_RDONLY | _NOFOLLOW | _NONBLOCK, dir_fd=dfd)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        return os.read(fd, _READ_CAP).decode("utf-8", "replace")
    except OSError:
        return None
    finally:
        os.close(fd)


def _write_at(dfd: int, name: str, text: str, mode: int) -> None:
    """Write entry `name` of an open directory by atomic rename. Raises OSError."""
    tmp = f".{secrets.token_hex(6)}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW, mode, dir_fd=dfd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)
    except BaseException:
        try:
            os.unlink(tmp, dir_fd=dfd)
        except OSError:
            pass
        raise


def _iter_dir(dfd: int, where: Path):
    """(filename, letter) for each `*.json` letter of an open directory, oldest
    first, each read no-follow relative to it; anything else is skipped."""
    try:
        names = sorted(n for n in os.listdir(dfd) if n.endswith(".json"))
    except OSError:
        return
    for name in names:
        try:
            letter = json.loads(_read_at(dfd, name) or "")
        except Exception:
            continue
        if isinstance(letter, dict):
            yield name, _fill(letter, where / name)


def _iter_paths(paths):
    """`_iter_dir` by path, for an OS without dir_fd (Windows: no unprivileged
    user shares a box there)."""
    for f in paths:
        try:
            letter = json.loads(_read_regular(f) or "")
        except Exception:
            continue
        if isinstance(letter, dict):
            yield f.name, _fill(letter, f)


class _BoxView:
    """One box's unread letters, read and archived without following a link:
    relative to the box opened no-follow, so swapping the box for a symlink
    mid-pass changes nothing (a root drain of a box the COO can rename).
    `ok` is False for a missing box or one that is a symlink."""

    def __init__(self, box: Path) -> None:
        self.box = box
        self.fd = _open_dir(box) if _DIRFD_OK else None
        self.ok = self.fd is not None if _DIRFD_OK else (box.is_dir() and not box.is_symlink())

    def __enter__(self) -> "_BoxView":
        return self

    def __exit__(self, *exc) -> None:
        if self.fd is not None:
            os.close(self.fd)

    def letters(self):
        if not self.ok:
            return iter(())
        if self.fd is not None:
            return _iter_dir(self.fd, self.box)
        return _iter_paths(sorted(self.box.glob("*.json")))

    def archive(self, name: str, letter: dict) -> None:
        if self.fd is not None:
            _archive_at(self.fd, name, letter)
        else:
            _archive(self.box / name, letter)


def _read_dir_letters(box: Path) -> list[tuple[str, dict]]:
    """(filename, letter) for each read letter in `<box>/read/` this user owns."""
    if not _DIRFD_OK:
        rd = _read_box(box)
        if box.is_symlink() or rd.is_symlink() or not rd.is_dir():
            return []
        return list(_iter_paths(sorted(rd.glob("*.json"))))
    dfd = _open_read_dir(box, create=False)
    if dfd is None:
        return []
    try:
        return list(_iter_dir(dfd, box / READ_DIR))
    finally:
        os.close(dfd)


def _replace_file(dirpath: Path, name: str, text: str) -> None:
    """Write `dirpath/name` by atomic rename: a planted symlink or hard link at
    that name is replaced, never written through. Raises OSError."""
    fd, tmp = tempfile.mkstemp(dir=str(dirpath), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dirpath / name)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def envelope_on() -> bool:
    """Read at call time, so a long-lived process (an MCP server) follows the
    env it was started with, and a test can flip it with monkeypatch."""
    return os.environ.get(ENVELOPE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def default_subject(body: str) -> str:
    """The first SUBJECT_MAX characters of the body, whitespace collapsed."""
    return " ".join(str(body or "").split())[:SUBJECT_MAX]


def letter_prio(kind: str | None, prio: str | None) -> str:
    """The prio a letter is stored and woken with: the sender's, else urgent
    for an order, ask or blocker and normal for every other kind."""
    return prio or ("urgent" if (kind or "message") in URGENT_KINDS else "normal")


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
    """`L-MMDD-HHMM-xxxx` (UTC, 4 random hex), the plan's §6.2 letter id."""
    return f"L-{datetime.now(timezone.utc):%m%d-%H%M}-{secrets.token_hex(2)}"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fill(letter: dict, path: Path) -> dict:
    """Envelope fields for a letter written before envelope mode (or by a
    sender running with the flag off): the filename stem is its id. Also
    normalises what a reader prints, whoever wrote the file: a non-token id
    becomes the stem, the subject one line of at most 80 characters, an
    unknown kind or prio the default."""
    if not isinstance(letter.get("id"), str) or not _ID_RE.fullmatch(letter["id"]):
        letter["id"] = path.stem
    subject = " ".join(str(letter.get("subject") or "").split())[:SUBJECT_MAX]
    letter["subject"] = subject or default_subject(letter.get("body", ""))
    if letter.get("kind") not in KINDS:
        letter["kind"] = "message"
    if letter.get("prio") not in PRIOS:
        letter["prio"] = "normal"
    letter.setdefault("read_at", None)
    return letter


def _read_box(box: Path) -> Path:
    return box / READ_DIR


def _archive_at(bfd: int, name: str, letter: dict) -> None:
    """Move unread letter `name` of the open box `bfd` to its `read/`, carrying
    `read_at`. Never raises: if the read copy cannot be written the letter is
    removed anyway, because a letter that stays unread would be delivered
    again on every prompt (exactly-once wins over keeping a copy). A `read`
    that is a symlink or not this user's keeps no copy."""
    try:
        mode = os.stat(name, dir_fd=bfd, follow_symlinks=False).st_mode & 0o777
        dfd = _open_read_dir_at(bfd, create=True)
        if dfd is not None:
            try:
                _write_at(dfd, name, json.dumps(letter, ensure_ascii=False, indent=2), mode)
            finally:
                os.close(dfd)
    except Exception:
        pass
    try:
        os.unlink(name, dir_fd=bfd)
    except OSError:
        pass


def _archive(path: Path, letter: dict) -> None:
    """`_archive_at` by path, for an OS without dir_fd."""
    try:
        rd = _read_box(path.parent)
        if not rd.is_symlink():
            rd.mkdir(exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(rd), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(letter, fh, ensure_ascii=False, indent=2)
                try:
                    os.chmod(tmp, path.lstat().st_mode & 0o777)
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
    read: the archive file's mtime). Returns how many went. Never raises.

    The wake sweep runs this as root over every box, the COO's included, so
    `read/` is opened no-follow and every entry is stat'ed and unlinked
    relative to that open directory: a `read` symlink planted in the box
    points the prune nowhere, and swapping it mid-pass changes nothing."""
    cutoff = (now if now is not None else time.time()) - RETAIN_DAYS * 86400
    rd = _read_box(box)
    gone = 0
    if not _DIRFD_OK:  # Windows: no dir_fd; no unprivileged box there either
        try:
            if rd.is_symlink():
                return 0
            for f in rd.glob("*.json"):
                try:
                    if f.lstat().st_mtime < cutoff:
                        f.unlink(missing_ok=True)
                        gone += 1
                except OSError:
                    continue
        except Exception:
            pass
        return gone
    dfd = _open_read_dir(box, create=False, owned=False)
    if dfd is None:
        return 0
    try:
        for name in os.listdir(dfd):
            if not name.endswith(".json"):
                continue
            try:
                if os.stat(name, dir_fd=dfd, follow_symlinks=False).st_mtime < cutoff:
                    os.unlink(name, dir_fd=dfd)
                    gone += 1
            except OSError:
                continue
    except Exception:
        pass
    finally:
        os.close(dfd)
    return gone


def _drain_envelope(role: str, session_id: str, root: Path | None) -> list[dict]:
    box = _box(role, session_id, root)
    out = []
    with _BoxView(box) as view:
        if not view.ok:
            return out        # no box, or one swapped for a link: nobody's box
        for name, letter in view.letters():   # malformed / not a regular file: left in place
            letter["read_at"] = _iso_now()
            view.archive(name, letter)
            out.append(letter)
    prune(box)
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


def list_letters(role: str, session_id: str, *, root: Path | None = None,
                 include_read: bool = True, limit: int = 50) -> list[dict]:
    """Summaries (no body) of the box's letters, newest first: the unread
    ones, then (include_read) those read in the last RETAIN_DAYS."""
    box = _box(role, session_id, root)
    with _BoxView(box) as view:
        items = [_summary(l, True) for _, l in view.letters()]
    if include_read:
        items += [_summary(l, False) for _, l in _read_dir_letters(box)]
    items.sort(key=lambda d: (str(d.get("sent_at") or ""), str(d.get("id") or "")), reverse=True)
    return items[:max(0, int(limit))]


def read_letter(role: str, session_id: str, letter_id: str, *,
                root: Path | None = None) -> dict | None:
    """The whole letter with this id from the box, or None. An unread one is
    marked read on the way (envelope mode). The id is only ever compared,
    never joined into a path, and one that is not a plain token is refused."""
    if not isinstance(letter_id, str) or not _ID_RE.fullmatch(letter_id):
        return None
    box = _box(role, session_id, root)
    with _BoxView(box) as view:
        for name, letter in view.letters():
            if letter["id"] == letter_id:
                if envelope_on():
                    letter["read_at"] = _iso_now()
                    view.archive(name, letter)
                return letter
    for _, letter in _read_dir_letters(box):
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
        fd = os.open(str(base / SWEEP_BEAT_FILE),
                     os.O_WRONLY | os.O_CREAT | _NOFOLLOW | _NONBLOCK, 0o644)
        try:
            if stat.S_ISREG(os.fstat(fd).st_mode):
                os.utime(fd if os.utime in os.supports_fd else str(base / SWEEP_BEAT_FILE))
        finally:
            os.close(fd)
    except OSError:
        pass


def sweeper_alive(*, root: Path | None = None, now: float | None = None) -> bool:
    base = root if root is not None else INBOX_ROOT
    try:
        st = (base / SWEEP_BEAT_FILE).lstat()
    except OSError:
        return False
    if not stat.S_ISREG(st.st_mode):
        return False
    return (now if now is not None else time.time()) - st.st_mtime <= SWEEP_STALE_S


def _last_wake(box: Path) -> float:
    try:
        return float((_read_regular(box / LAST_WAKE_FILE) or "").strip())
    except ValueError:
        return 0.0


def note_wake(role: str, session_id: str, *, root: Path | None = None,
              now: float | None = None) -> None:
    """Record that this box was just woken: letters already waiting no longer
    count toward the next wake. Never raises."""
    box = _box(role, session_id, root)
    try:
        if box.is_dir() and not box.is_symlink():
            _replace_file(box, LAST_WAKE_FILE, repr(now if now is not None else time.time()))
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
            m = p.lstat().st_mtime
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
