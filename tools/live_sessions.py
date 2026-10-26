"""Live Claude Code sessions across hosts — one publisher, one compact list.

Senders used to call ListAgents (83 rows, ~70 dead, ~5k tokens) and some sent
to names from memory. Claude Code keeps one file per live process,
``<config>/sessions/<pid>.json``; this module reads them, publishes the live
ones to the hub (``live_sessions`` + ``live_hosts``), and prints the C-level
and Project Head sessions of every host in under 1k tokens (workers: --all).

    python3 -m tools.live_sessions [--all] [--id <sid>] [--json] [--local]
    python3 -m tools.live_sessions publish --once      # prints a count only
    python3 -m tools.live_sessions publish --loop      # standalone publisher

The publisher is the standalone ``publish --loop`` process, one per host,
started on demand by ``ensure_publisher()`` from scripts/hook-inbox.py (a hook
script is read from disk on every prompt, so a git pull is enough to roll it
out). Entry points:

  ensure_publisher()            the hook's call: spawn the loop if none is alive
  render_for_tool(id, all)      the text for the MCP tool; own short connection

A host with no hub route of its own (winbox: no venv) is pulled instead: the
publisher on a host that lists it under ``live_sessions_pull`` reads its
registry over ssh once a minute and publishes it under the pulled host's name.

Fail open everywhere: a hub that cannot be reached costs one line of text, a
publisher that cannot publish costs nothing. Never SQLite (``state/tasks.db``
is a tombstone), never lib.db's connection, never the DSN anywhere. The hook
imports this under the system python3, so module level is stdlib only: lib.*
and argparse load inside the functions that need them.
See docs/ops/live-sessions.md.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_NAME = "live_sessions.publisher.lock"
SPAWN_STAMP = "live_sessions.spawned"
LOCK_PATH = ROOT / "state" / "locks" / LOCK_NAME

CONNECT_TIMEOUT_S = 3     # the publisher and the reader both give up fast
POLL_S = 5                # holder: how often the registry signature is read
REFRESH_S = 60            # holder: publish at least this often (dead pids drop out)
RETRY_S = 30              # backoff after a failed publish or connect
SPAWN_GAP_S = 60          # ensure_publisher spawns at most once per this
STALE_DAYS = 1            # a host's rows older than this are deleted
STMT_TIMEOUT_MS = 10_000  # a hung hub must not wedge the lock holder
DEFAULT_TTL_S = 150       # reader: 2 missed refreshes + slack
STALE_SHOW_S = STALE_DAYS * 86400   # reader: a silent host's last rows stay listed, marked stale

# Thailand has no DST, so a fixed offset needs no tz database (winbox has none).
TH = timezone(timedelta(hours=7))

# CTO verified 2026-10-13: the COO (SomPong) is reachable cross-session ONLY as
# "SomPong"; its local session name "CONTABO COO #a7eb4963" returned "not
# reachable". Every other role is reachable under its session name.
# Applies only to an old-style name (one with "#<id>"): from the CEO's
# 14 Oct ruling SomPong's Remote Control name and session name are both
# "COO (SomPong)", so the name is the address again.
ADDRESS_ALIAS = {"coo": "SomPong"}

HOST_ORDER = ("contabo", "mac", "winbox")

# "⏸ MAC CTO #671f688f (topic)": optional leading non-letters, a host word, the
# role words, then the short id. Anything after the id is the human topic.
# The bracket before the id is optional and never part of the role: a Project
# Head's lane, "CONTABO Project Head (CTO) #3c1f65ae (OrgRestructure)" (org
# restructure P2), or a C-level's persona, "CONTABO COO (SomPong) #a7eb4963"
# (CEO 2026-10-14 session names). A name without one parses as before.
_NAME_RE = re.compile(
    r"^[\W_]*(?:CONTABO|MAC|WINDOWS|WINBOX)\s+([A-Za-z][A-Za-z ]*?)"
    r"(?:\s+\((?:[^\w\s():]+: )?[A-Za-z]{2,32}\))?\s+#([0-9a-f]{6,12})\b")
# CEO 2026-10-14: a C-level's name is "<ROLE> (<Name>)", e.g. "CTO (Kavin)", with no
# machine and no #id; a role without a persona is the bare role, "CFO". Text after
# " — " is the human topic (session-rename.sh). The role and id come from the
# session record instead (_ids_from_record), never from this name alone.
_SHORT_NAME_RE = re.compile(
    r"^[\W_]*(?!CEO\b)(C[A-Z]O)(?:\s+\((?:[^\w\s():]+: )?([A-Za-z]{2,32})\))?(?:\s+—\s.*)?$")
# The launchers run every org session in a tmux session named "<role>-<sid>"
# (cxo-claude.sh, cto-claude.sh, spawn-ph.sh); Claude Code records it in the
# session file as "<tmux session>:@<window>.%<pane>".
_TMUX_ID_RE = re.compile(r"^([a-z][a-z_]{1,30})-([0-9a-f]{8}):")
# A worker's tmux session: "wd-<sid>" or "<project>-task-<sid>" (tools/delegate.py).
_WORKER_TMUX_RE = re.compile(r"^(?:wd|[a-z0-9][a-z0-9_-]{0,40}-task)-([0-9a-f]{8}):")
# A launcher tmux name that is not "<role>-<sid>" but still names the role.
_FIXED_TMUX_ROLE = {"sompong": "coo"}
# cxo-claude.sh writes the session's full UUID to <role>-<sid>.uuid here; the
# fixed tmux claims its role only for the session that file names (M10 #7).
LOCKS_DIR = ROOT / "state" / "locks"
NAME_ONLY = "[name only]"
OFF_RULE_LINES = 5
_C_LEVEL_RE = re.compile(r"^c[a-z]o$")
_SESSION_FILE_RE = re.compile(r"^\d+\.json$")   # not <pid>.<hash>.key

MAX_SESSION_BYTES = 64 * 1024   # a real record is under 2 KiB; a bigger file is not one
MAX_NAME_CHARS = 120
_BAD_CHARS = ("Cc", "Cf", "Zl", "Zp")   # controls, bidi/format, line and paragraph separators
# O_NOFOLLOW: never through a planted symlink. O_NONBLOCK: a FIFO cannot hold the
# open. The getattr keeps Windows (which has neither) importing.
_O_SAFE = (getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
           | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0))

FOOTER = ('send: SendMessage(to=<text after the status, without a trailing [name only] or ⚠ mark>, '
          'verbatim). "N agents are named X" → re-send with the [ref] the error marks active.')
STALE_NOTE = ('stale = its host stopped reporting (header); the session may still be live — '
              'send, and trust the send\'s answer over this list.')
NAME_ONLY_NOTE = ('[name only] = no launcher tmux claims the role; the role is read from '
                  'the name, which any session can set.')
CLAIM_NOTE = ('⚠ claims <title> = the name carries a reserved title (CTO Main, CMO Main) but the row\'s '
              'role is not that C-level: it is not the CTO / CMO; check a sender with tools.whois.')
STATUS_RANK = {"running": 0, "idle": 1, "unknown": 2, "stale": 3}

# OrgMesh P8: any session can rename itself, so a reserved title may be shown only for a row whose
# role is that C-level. The role is the one the launcher's tmux claims (or, on a host with no tmux,
# the name's own, which the "[name only]" mark already flags). Anywhere in the name, as a whole
# phrase; a host emoji or a state glyph in front changes nothing. Between the title and "Main" it
# lets through nothing but spaces, an id ("#c34", "#7cf528f0") and one run of separators
# (- _ . / \ · • — – : |), so "CTO-Main", "CTOMain", "CTO#c34 Main" are caught and "(CTO) - Main
# Street" is not. "C T O Main" counts in capitals only: "send c to main" is not a claim. (P8c, F6)
_RESERVED_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<title>(?i:CTO|CMO)|C\s*[TM]\s*O)\s*(?:#[0-9a-fA-F]{3,8})?"
    r"[\s\-_./\\\u00b7\u2022\u2014\u2013:|]*(?i:Main)(?![A-Za-z])")

# The columns every hub has, then the ones lib.db.init() adds later (verified: M8, bridge_id: P8d).
# Until a hub has run init() publishers and readers run without the later ones: a row reads
# unverified and has no bridge id. A column the connecting role may not read is absent too.
_SESSION_COLS = ("host", "uuid", "sid", "role", "name", "address", "status", "pid",
                 "former_name", "renamed_at")
_OPTIONAL_COLS = ("verified", "bridge_id")


def _upsert_session(extra=()) -> str:
    """The upsert of one live_sessions row, with the optional columns in `extra`."""
    marks = ", ".join(["?"] * len(_SESSION_COLS) + ["now()"] + ["?"] * len(extra))
    sets = ", ".join([f"{c} = EXCLUDED.{c}" for c in _SESSION_COLS[2:]] + ["seen_at = now()"]
                     + [f"{c} = EXCLUDED.{c}" for c in extra])
    return (f"INSERT INTO live_sessions ({', '.join(_SESSION_COLS + ('seen_at',) + tuple(extra))})"
            f" VALUES ({marks}) ON CONFLICT (host, uuid) DO UPDATE SET {sets}")


def _live_columns(conn) -> set[str]:
    """The optional live_sessions columns this hub has and this role can read."""
    return {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema()"
        " AND table_name = 'live_sessions' AND column_name IN ('verified', 'bridge_id')").fetchall()}


_UPSERT_HOST = (
    "INSERT INTO live_hosts (host, published_at, publisher, n_sessions, error)"
    " VALUES (?, now(), ?, ?, NULL)"
    " ON CONFLICT (host) DO UPDATE SET published_at = now(),"
    " publisher = EXCLUDED.publisher, n_sessions = EXCLUDED.n_sessions, error = NULL")
# A failed pull keeps the last good published_at (and rows): only the error moves.
# A host never published gets a row stamped now, so "unreachable since" has a date.
_HOST_ERROR = (
    "INSERT INTO live_hosts (host, published_at, publisher, n_sessions, error)"
    " VALUES (?, now(), ?, 0, ?)"
    " ON CONFLICT (host) DO UPDATE SET error = EXCLUDED.error")


# ---------------------------------------------------------------------------
# registry: <config>/sessions/<pid>.json -> rows
# ---------------------------------------------------------------------------

def parse_name(name: str, session_id: str) -> tuple[str, str]:
    """(role, short id) from a session's display name. An old-style name
    carries both; a short C-level name ("CTO (Kavin)") carries the role and
    the id is the last 8 hex of the session UUID, which the launchers make
    end in the short id (cxo-claude.sh CXO_UUID). No match is role
    ``unknown`` with the same UUID tail. A leading host emoji ("🌐 CTO (Kavin)",
    CEO 2026-10-14) is dropped first; a name without one parses the same."""
    from lib import session_names   # stdlib only, safe under the hook's python3
    name = session_names.strip_host(name or "")
    m = _NAME_RE.match(name)
    if m:
        return m.group(1).strip().lower().replace(" ", "_"), m.group(2)
    m = _SHORT_NAME_RE.match(name)
    if m:
        return m.group(1).lower(), session_id[-8:]
    # "PH#6c4 (CTO) - SpendGuard" / "Dev#afe - OrgRestructure: …" (lib/session_names):
    # the name shows 3 hex; the full id is the UUID tail when it agrees, else the 3.
    short = session_names.parse_short(name)
    if short:
        role, id3 = short
        tail = session_id[-8:]
        return role, tail if tail.startswith(id3) else id3
    return "unknown", session_id[-8:]


def read_lock(path, limit: int = 256) -> str:
    """The stripped text of a small lock file, or "". state/locks is group-writable
    by the secretary service with no sticky bit, so a root reader must not follow a
    planted symlink (to /dev/zero, a FIFO or a root-only token): a regular file only
    (_safe_open), at most `limit` bytes, owned by root or by this reader (§2b review
    of #283 v2, B-1), not group/other writable and with one link, so a root-owned
    group-writable file (state/logs/*) renamed or hard-linked in is refused (round 3, L-1)."""
    fd = _safe_open(path, os.O_RDONLY, create=False)
    if fd is None:
        return ""
    try:
        st = os.fstat(fd)
        if (st.st_size > limit or st.st_uid not in (0, os.geteuid())
                or st.st_mode & 0o022 or st.st_nlink != 1):
            return ""
        data = os.read(fd, limit + 1)
    except OSError:
        return ""
    finally:
        os.close(fd)
    if len(data) > limit:
        return ""
    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return ""


def _launcher_uuid(role: str, session_id: str) -> bool:
    """True when the launcher's <role>-<sid>.uuid file names exactly this session."""
    tail = session_id[-8:]
    if not re.fullmatch(r"[0-9a-f]{8}", tail):
        return False
    return read_lock(LOCKS_DIR / f"{role}-{tail}.uuid") == session_id


def _ids_from_record(data, name: str, session_id: str) -> tuple[str, str, bool]:
    """(role, short id, verified) for one session record. "verified" means the
    launcher's tmux CLAIMS the role, not that anything proves it: a tmux name is
    only as good as whoever started it. The launcher's tmux
    session name "<role>-<sid>" wins, so an org session is found whatever its
    display name says; a sid that the session UUID does not end in is not
    trusted (a hand-made tmux session with an org-looking name). Otherwise the
    name, and `verified` is False. A session in some other tmux (a worker's
    "wd-<sid>") never gets a C-level or PH role from its name: a worker that
    /renames itself "CTO (Kavin)" is listed as "unknown" (M8, 2026-10-14)."""
    tmux = data.get("tmux")
    tmux = tmux if isinstance(tmux, str) and tmux else None
    m = _TMUX_ID_RE.match(tmux) if tmux else None
    # Only a listed role: a worker's tmux ("wd-<sid>") says nothing about its role.
    if m and is_listed(m.group(1)) and m.group(1) != "ceo" and session_id.endswith(m.group(2)):
        return m.group(1), m.group(2), True
    role, sid = parse_name(name, session_id)
    fixed = _FIXED_TMUX_ROLE.get(tmux.split(":", 1)[0]) if tmux else None
    if fixed and _launcher_uuid(fixed, session_id):
        return fixed, (sid if role == fixed else session_id[-8:]), True
    w = _WORKER_TMUX_RE.match(tmux) if tmux else None
    if tmux and is_listed(role):
        return "unknown", (w.group(1) if w else session_id[-8:]), False
    # a worker's short name shows 3 hex; its tmux name has all 8
    if w and (sid == w.group(1) or (len(sid) == 3 and w.group(1).startswith(sid))):
        return role, w.group(1), True
    return role, sid, False


def address_for(role: str, name: str) -> str:
    """What SendMessage takes: the name as it is (host emoji included), or the COO's
    alias for an old-style name."""
    if role in ADDRESS_ALIAS and "#" in name:
        return ADDRESS_ALIAS[role]
    return name


def is_c_level(role: str) -> bool:
    return bool(_C_LEVEL_RE.match(role))


PH_ROLE = "project_head"


def is_listed(role: str) -> bool:
    """Printed without --all: the C-levels and the Project Heads, the sessions a
    C-level or a PH sends orders to (org restructure P2). Workers need --all."""
    return is_c_level(role) or role == PH_ROLE


def map_status(raw) -> str:
    """Only running / idle / unknown ever leave this: the status is printed
    right above the "send verbatim" footer, so a value a session file chose
    must not be able to carry text."""
    raw = str(raw or "").strip()
    if raw == "idle":
        return "idle"
    if raw in ("busy", "shell"):
        return "running"
    return "unknown"


def _clean(text, limit: int) -> str:
    """One printable line: control, format (bidi) and line/paragraph separator
    characters become a space, runs of spaces collapse, at most ``limit``
    characters. A session file is written by whoever owns the registry dir (the
    sompong user, a root worker, winbox), and the name is printed as an address
    the model is told to send to verbatim: a "\\n" in it would forge a row."""
    from lib import session_names
    raw = str(text)
    body = session_names.split_name(raw)[2]
    match = session_names._C_LEVEL_BODY_RE.fullmatch(body)
    if not match:
        long = session_names._MACHINE_LONG_RE.match(body)
        if long and re.fullmatch(r"C[A-Z]O", long.group("role")):
            match = long
    start = end = -1
    if match and match.group("person_emoji"):
        offset = len(raw) - len(body)
        start, end = (offset + i for i in match.span("person_emoji"))
    # Preserve ZWJ only within the C-level persona; retain filtering everywhere else.
    s = "".join(" " if unicodedata.category(c) in _BAD_CHARS
                and not (c == "\u200d" and start <= i < end) else c
                for i, c in enumerate(raw))
    return re.sub(r" {2,}", " ", s).strip()[:limit].rstrip()


def _config():
    from lib import config
    return config


def _win_kernel32():
    import ctypes
    return ctypes.windll.kernel32


def _proc_starttime(pid: int) -> int | None:
    """Field 22 of /proc/<pid>/stat. The command name in field 2 may hold
    spaces and parentheses, so count from the last ')'."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as f:
            tail = f.read().decode("utf-8", "replace").rsplit(")", 1)[1].split()
        return int(tail[19])
    except (OSError, IndexError, ValueError):
        return None


def is_alive(pid: int, proc_start=None) -> bool:
    """Linux: kill(0) works AND the start time still equals procStart (a reused
    pid has another one). macOS: kill(0). Windows: the process has not exited
    (os.kill(pid, 0) there would send CTRL_C_EVENT, so it is never called)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        k32 = _win_kernel32()
        handle = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            import ctypes
            code = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(handle, ctypes.byref(code))) \
                and code.value == 259                  # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except PermissionError:
        pass            # another user's process: it exists
    except (OSError, OverflowError, ValueError):
        return False
    if sys.platform.startswith("linux") and proc_start is not None:
        return _proc_starttime(pid) == proc_start
    return True


def session_dirs(host: str) -> list[Path]:
    """Registry dirs for ``host``: hosts.<host>.claude_session_dirs when set,
    else ``$CLAUDE_CONFIG_DIR/sessions`` or ``~/.claude/sessions``. Deduped by
    realpath; a missing dir stays in the list (it can appear later)."""
    try:
        listed = (_config().hosts().get(host) or {}).get("claude_session_dirs")
    except Exception:
        listed = None
    if not listed:
        base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude")
        listed = [os.path.join(base, "sessions")]
    out, seen = [], set()
    for d in listed:
        p = Path(os.path.expanduser(str(d)))
        real = os.path.realpath(p)
        if real not in seen:
            seen.add(real)
            out.append(p)
    return out


def _ms_to_dt(ms) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _former_name(former) -> str | None:
    """The newest of ``formerNames`` ([{name, until}]), by ``until``."""
    if not isinstance(former, list):
        return None
    named = [f for f in former if isinstance(f, dict) and f.get("name")]
    if not named:
        return None
    def until(f):
        u = f.get("until")
        return u if isinstance(u, (int, float)) else 0
    return str(max(named, key=until)["name"])   # max keeps the first of equal keys


def _safe_open(path, flags: int, *, create: bool) -> int | None:
    """An fd on a regular file at ``path``, or None. The publisher runs as root
    over paths another account can replace (state/ is group-writable by the
    secretary service, and sompong writes its own registry dir), so an open must
    not follow a planted symlink (lock -> /etc/shadow), block on a FIFO, or
    write through a hard link: O_NOFOLLOW + O_NONBLOCK, then fstat must say a
    regular file (and, for a file we create, one link). ``create`` also opens the
    parent dir with O_NOFOLLOW, so a symlinked state/locks is refused too."""
    dfd = fd = None
    try:
        path, kw = os.fspath(path), {}
        if create and os.open in os.supports_dir_fd:
            parent, path = os.path.split(path)
            dfd = os.open(parent or ".", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _O_SAFE)
            kw["dir_fd"] = dfd
        fd = os.open(path, flags | _O_SAFE | (os.O_CREAT if create else 0), 0o644, **kw)
        st = os.fstat(fd)
        if stat.S_ISREG(st.st_mode) and (st.st_nlink == 1 or not create):
            return fd
    except OSError:
        pass
    finally:
        if dfd is not None:
            os.close(dfd)
    if fd is not None:
        os.close(fd)
    return None


def _read_session_file(path) -> bytes | None:
    """The bytes of one registry file, or None. Regular files only (no symlink,
    no FIFO, no /dev/zero behind a link), at most MAX_SESSION_BYTES: the
    publisher runs as root over a dir the sompong user also writes."""
    fd = _safe_open(path, os.O_RDONLY, create=False)
    if fd is None:
        return None
    try:
        if os.fstat(fd).st_size > MAX_SESSION_BYTES:
            return None
        with os.fdopen(fd, "rb", closefd=False) as f:
            data = f.read(MAX_SESSION_BYTES + 1)   # a file that grew meanwhile
    except OSError:
        return None
    finally:
        os.close(fd)
    return data if len(data) <= MAX_SESSION_BYTES else None


def _row_from_file(path: Path) -> dict | None:
    """One live session row from one file, or None (dead, corrupt, no name)."""
    raw = _read_session_file(path)
    if raw is None:
        return None
    try:
        return _row_from_data(json.loads(raw.decode("utf-8")))
    except (ValueError, RecursionError):    # RecursionError: 60k nested '['
        return None


def _proc_start(raw) -> int | None:
    """procStart as Linux writes it (/proc stat field 22: an int or a digit
    string), else None. Claude Code on macOS writes a date string ("Tue Oct 13
    11:55:05 2026"); it is only compared on Linux, so it must not drop the row."""
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    if isinstance(raw, str) and raw.isascii() and raw.isdigit():
        return int(raw)
    return None


_BRIDGE_ID_RE = re.compile(r"session_[A-Za-z0-9]{1,100}")


def _bridge_id(raw) -> str | None:
    """The record's Remote Control id ("session_<letters+digits>", what a message from this
    session carries as `from=bridge:<id>`), or None for anything else. Strict: it ends up in a
    column that tools/whois compares, and it is printed nowhere."""
    return raw if isinstance(raw, str) and _BRIDGE_ID_RE.fullmatch(raw) else None


def _row_from_data(data, *, check_alive: bool = True) -> dict | None:
    """The row for one session record (a file's JSON, or an entry the winbox
    pull returns, whose liveness the far side already checked), or None."""
    try:
        pid = int(data["pid"])
        session_id = _clean(data["sessionId"], 64)
        proc_start = _proc_start(data.get("procStart"))
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    # pid is an INTEGER column: one out-of-range value would fail the whole host's publish
    if not session_id or not 0 < pid < 2 ** 31:
        return None
    if check_alive and not is_alive(pid, proc_start):
        return None
    name = _clean(data.get("name") or "", MAX_NAME_CHARS)
    if not name:
        return None     # nothing to address it by
    role, sid, verified = _ids_from_record(data, name, session_id)
    former = _former_name(data.get("formerNames"))
    return {
        "uuid": session_id, "sid": sid, "role": role, "name": name, "verified": verified,
        "address": address_for(role, name),
        "status": map_status(data.get("status")), "pid": pid,
        "former_name": _clean(former, MAX_NAME_CHARS) if former else None,
        "renamed_at": _ms_to_dt(data.get("nameSince")),
        "bridge_id": _bridge_id(data.get("bridgeSessionId")),
        "_updated": data.get("updatedAt") if isinstance(data.get("updatedAt"), (int, float)) else 0,
    }


def _one_per_uuid(rows) -> list[dict]:
    """One row per session UUID; the newest record (``updatedAt``) wins."""
    by_uuid: dict[str, dict] = {}
    for row in rows:
        old = by_uuid.get(row["uuid"])
        if old is None or row["_updated"] >= old["_updated"]:
            by_uuid[row["uuid"]] = row
    return list(by_uuid.values())


def read_registry(dirs) -> list[dict]:
    """Every live session in ``dirs``. Unreadable dirs, dead pids and corrupt
    files are skipped silently."""
    rows = []
    for d in dirs:
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for fname in names:
            if _SESSION_FILE_RE.match(fname):
                row = _row_from_file(Path(d) / fname)
                if row is not None:
                    rows.append(row)
    return _one_per_uuid(rows)


def registry_signature(dirs) -> tuple:
    """Cheap change detector: sorted (filename, mtime_ns, size) of every
    ``<pid>.json``. A rename rewrites the file, so it shows within one poll."""
    sig = []
    for d in dirs:
        try:
            with os.scandir(d) as it:
                for e in it:
                    if _SESSION_FILE_RE.match(e.name):
                        st = e.stat()
                        sig.append((e.name, st.st_mtime_ns, st.st_size))
        except OSError:
            continue
    return tuple(sorted(sig))


# ---------------------------------------------------------------------------
# publisher
# ---------------------------------------------------------------------------

def _publisher_label() -> str:
    try:
        import getpass
        user = getpass.getuser()
    except Exception:
        user = "?"
    return f"{user}/{os.getpid()}"


def publish_once(conn, host: str, dirs, prev_uuids) -> set[str]:
    """publish_rows() for the sessions in this host's own registry dirs."""
    return publish_rows(conn, host, promote_project_heads(read_registry(dirs)), prev_uuids)


def _windows_host(host: str) -> bool:
    try:
        return _config().host(host).get("os") == "windows"
    except Exception:   # an unknown host, or no config here: no launcher tmux to expect
        return True


def demote_untmuxed(rows, host: str) -> list[dict]:
    """On a host whose launchers always start a tmux (Contabo, the Mac), a session
    with no launcher tmux claiming its role is not given a C-level or PH role from
    its name alone: role "unknown" (M10 #6). Windows hosts have no tmux; their rows
    keep the name's role, marked name only."""
    if _windows_host(host):
        return rows
    for r in rows:
        if not r.get("verified") and is_listed(r["role"]):
            r["role"] = "unknown"
            r["address"] = address_for("unknown", r["name"])
    return rows


def promote_project_heads(rows) -> list[dict]:
    """Role `project_head` for a local C-level box that is a Project Head. A session opened
    as a C-level and made a PH later keeps its launcher box (cto-<sid>, CXO_ROLE=cto), so
    the registry says "cto"; only THIS host holds state/locks/project_head-<sid>.project,
    so only this host can say so, and it does it here, before the row leaves it. Another
    host judges the name by the role it is sent (off_rule_notes), never by a guess.
    Only a row the launcher's tmux claims (`verified`) is moved, and only for a marker
    that is a project name build_name would use; any other value leaves the role as it
    is. tools/rename_service reads read_registry() directly and keeps the box role."""
    for r in rows:
        if (r.get("verified") and is_c_level(r["role"]) and r["role"] != "ceo"
                and re.fullmatch(r"[0-9a-f]{8}", r["sid"])
                and re.fullmatch(r"[A-Za-z0-9_]{1,40}",
                                 read_lock(LOCKS_DIR / f"{PH_ROLE}-{r['sid']}.project"))):
            r["role"] = PH_ROLE
            r["address"] = address_for(PH_ROLE, r["name"])
    return rows


def publish_rows(conn, host: str, rows, prev_uuids, publisher: str | None = None) -> set[str]:
    """One transaction: upsert every live row, delete this host's rows that were
    published last time and are gone now, upsert ``live_hosts``, and delete this
    host's rows older than a day. Returns the uuids now published."""
    rows = demote_untmuxed(rows, host)
    now_uuids = {r["uuid"] for r in rows}
    extra = tuple(c for c in _OPTIONAL_COLS if c in _live_columns(conn))
    sql = _upsert_session(extra)
    for r in rows:
        args = (host, r["uuid"], r["sid"], r["role"], r["name"], r["address"],
                r["status"], r["pid"], r["former_name"], r["renamed_at"])
        conn.execute(sql, args + tuple(bool(r.get("verified")) if c == "verified" else r.get("bridge_id")
                                       for c in extra))
    gone = sorted(set(prev_uuids) - now_uuids)
    if gone:
        conn.execute("DELETE FROM live_sessions WHERE host = ? AND uuid = ANY(?)",
                     (host, gone))
    conn.execute(_UPSERT_HOST, (host, publisher or _publisher_label(), len(rows)))
    conn.execute("DELETE FROM live_sessions WHERE host = ?"
                 f" AND seen_at < now() - interval '{STALE_DAYS} day'", (host,))
    conn.commit()
    return now_uuids


# ---------------------------------------------------------------------------
# pull: a host with no hub route of its own (winbox has no venv) is read over ssh
# ---------------------------------------------------------------------------

PULL_TIMEOUT_S = 25   # hard cap on one ssh pull; the local 5 s loop waits at most this

# Runs on the pulled Windows host. A record is kept only when its pid exists and
# its process creation FILETIME matches procStart within 1 ms, or, if procStart
# is absent, the process started within 10 s of startedAt (a reused pid fails).
# stdout is ONE json array; PowerShell's CLIXML progress noise goes to stderr.
PS_PULL_SCRIPT = r"""$ProgressPreference='SilentlyContinue'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$o=@()
$d=Join-Path $env:USERPROFILE '.claude\sessions'
if(Test-Path $d){foreach($f in Get-ChildItem $d -Filter '*.json' -File){try{
$j=Get-Content -Raw -Encoding UTF8 -LiteralPath $f.FullName|ConvertFrom-Json
$p=Get-Process -Id ([int]$j.pid) -ErrorAction Stop
if($null -ne $j.procStart){$keep=[math]::Abs($p.StartTime.ToFileTimeUtc() - [int64]$j.procStart) -le 10000}else{
$t=[DateTimeOffset]::new($p.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds()
$keep=[math]::Abs($t-[int64]$j.startedAt) -le 10000
}
if($keep){$o+=[pscustomobject]@{pid=[int]$j.pid;sessionId=[string]$j.sessionId;name=[string]$j.name;status=[string]$j.status;nameSince=$j.nameSince;formerNames=@($j.formerNames|Where-Object{$_});bridgeSessionId=[string]$j.bridgeSessionId}}
}catch{}}}
ConvertTo-Json -InputObject @($o) -Compress -Depth 4"""


class PullError(Exception):
    """A pull that failed; the message is a fixed label, safe to store and print
    (never ssh's own stderr, which can name hosts and keys)."""


def ps_encoded(script: str = PS_PULL_SCRIPT) -> str:
    """-EncodedCommand wants base64 of UTF-16LE; it survives ssh quoting."""
    import base64
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def pull_argv(ssh_target: str) -> list[str]:
    # "--": the target comes from hosts.yaml, and OpenSSH reads options with getopt
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "--", ssh_target,
            "powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", ps_encoded()]


def pull_remote(ssh_target: str, *, timeout: float = PULL_TIMEOUT_S) -> list[dict]:
    """The pulled host's live sessions, as the same rows read_registry() gives.
    Raises PullError(label) on a timeout, a non-zero exit or output that is not
    a JSON array of records."""
    import subprocess
    try:
        proc = subprocess.run(pull_argv(ssh_target), stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise PullError("ssh timeout") from None
    except OSError:
        raise PullError("ssh unavailable") from None
    if proc.returncode != 0:
        raise PullError(f"ssh exit {proc.returncode}")
    # stdout only. PowerShell may lead with a BOM; take the last non-empty line.
    lines = proc.stdout.decode("utf-8-sig", "replace").strip().splitlines()
    try:
        entries = json.loads(lines[-1])
    except (IndexError, ValueError, RecursionError):
        raise PullError("bad output") from None
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise PullError("bad output")
    return _one_per_uuid(r for r in (_row_from_data(e, check_alive=False) for e in entries) if r)


def record_pull_error(conn, host: str, label: str, publisher: str | None = None) -> None:
    """Mark ``host`` unreachable without touching its rows or its published_at."""
    conn.execute(_HOST_ERROR, (host, publisher or _publisher_label(), label))
    conn.commit()


def pull_targets(host: str) -> list[tuple[str, str]]:
    """(host, ssh alias) for every host ``host`` pulls: hosts.<host>.live_sessions_pull,
    each resolved through hosts.<name>.ssh. A name without an ssh alias is skipped."""
    try:
        hosts = _config().hosts()
        out = []
        for name in (hosts.get(host) or {}).get("live_sessions_pull") or []:
            alias = (hosts.get(name) or {}).get("ssh")
            if alias:
                out.append((str(name), str(alias)))
        return out
    except Exception:
        return []


# Project Monitor push (org restructure P3-E): the hub host runs tools/portfolio_push.py once a
# minute under `infisical_setup run MoonieX-Console prod`, which holds PORTFOLIO_PUSH_TOKEN.
PUSH_HOSTS = ("contabo",)     # the hub host: its config/hosts.yaml key, as self_host() returns it
PUSH_TIMEOUT_S = 30       # a push still alive after this is killed (portfolio_push's own cap is 10 s)
PUSH_PREFIX = "portfolio_push: "
PUSH_EXIT = {2: "not configured", 3: "hub unreachable", 4: "console refused or unreachable"}


def push_enabled(host: str) -> bool:
    """Only the hub host pushes: the Mac and winbox publish sessions and nothing else."""
    return host in PUSH_HOSTS


def push_argv(root: Path = ROOT) -> list[str]:
    venv_python = Path(root) / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    return [python, str(Path(root) / "tools" / "infisical_setup.py"), "run", "MoonieX-Console", "prod",
            "--", python, str(Path(root) / "tools" / "portfolio_push.py")]


class PortfolioPush:
    """One push per REFRESH_S, never two at once, never in the publisher's way. ``tick`` starts
    the subprocess and returns; the next tick reaps it. It cannot raise: a failure is handed to
    ``report`` (the loop's deduplicated log line), and a push alive past PUSH_TIMEOUT_S is killed.
    The child inherits the loop's environment (`infisical_setup run` keeps it and adds the
    project's secrets), so ORG_DB_URL reaches portfolio_push.py. Only a line the child prefixed
    with ``portfolio_push: `` is ever forwarded, never the rest of its output."""

    def __init__(self, argv, *, cwd=ROOT, report=None, popen=None, clock=time.monotonic):
        self.argv, self.cwd, self.report, self.clock = list(argv), str(cwd), report, clock
        self._popen = popen
        self.proc = None
        self.started = 0.0
        self.next_at = 0.0
        self.failing = False

    def _say(self, what: str) -> None:
        if self.report:
            try:
                self.report(f"portfolio push {what}")
            except Exception:
                pass

    def _spawn(self):
        import subprocess
        popen = self._popen or subprocess.Popen
        return popen(self.argv, cwd=self.cwd, env=dict(os.environ), stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)

    def _kill(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass
        try:
            proc.stderr.close()
        except Exception:
            pass

    def _own_line(self, proc) -> str:
        try:
            text = proc.stderr.read(4096).decode("utf-8", "replace")
            proc.stderr.close()
        except Exception:
            return ""
        lines = [ln[len(PUSH_PREFIX):] for ln in text.splitlines() if ln.startswith(PUSH_PREFIX)]
        return _clean(lines[-1], 120) if lines else ""

    def _reap(self) -> bool:
        """False while a push is still in flight."""
        rc = self.proc.poll()
        if rc is None:
            if self.clock() - self.started > PUSH_TIMEOUT_S:
                self._kill()
                self.failing = True
                self._say(f"timed out after {PUSH_TIMEOUT_S}s")
                return True
            return False
        line, self.proc = self._own_line(self.proc), None
        if rc != 0:
            self.failing = True
            self._say(f"exit {rc} ({PUSH_EXIT.get(rc, 'failed')})" + (f": {line}" if line else ""))
        elif self.failing:
            self.failing = False
            self._say("ok again")
        return True

    def tick(self) -> None:
        try:
            if self.proc is not None and not self._reap():
                return
            now = self.clock()
            if now < self.next_at:
                return
            self.next_at = now + REFRESH_S      # a failed spawn waits a full period too
            self.proc, self.started = self._spawn(), now
        except Exception as exc:
            self.proc = None
            self.failing = True
            self._say(f"error ({type(exc).__name__})")

    def close(self) -> None:
        self._kill()


def make_push(host: str, report=None) -> PortfolioPush | None:
    return PortfolioPush(push_argv(), report=report) if push_enabled(host) else None


def _try_lock(f) -> bool:
    try:
        if sys.platform == "win32":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def acquire_lock(path: Path = LOCK_PATH, *, write_pid: bool = False):
    """The open lock file when this process now holds the host's publisher lock,
    else None (held by another process, or the file cannot be opened). Closing
    the file, or exiting, releases it. ``write_pid`` leaves the holder's pid in
    the file for `cat` (POSIX only: a Windows byte lock blocks readers)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    # no O_TRUNC: a probe that loses must not wipe the holder's pid
    fd = _safe_open(path, os.O_RDWR, create=True)
    if fd is None:
        return None
    f = os.fdopen(fd, "r+b")
    if not _try_lock(f):
        f.close()
        return None
    if write_pid and sys.platform != "win32":
        try:
            f.seek(0)
            f.truncate()
            f.write(str(os.getpid()).encode())
            f.flush()
        except OSError:
            pass
    return f


def _code_stamp(path: Path):
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


class Publisher:
    """The loop of ``publish --loop``. ``run`` returns an exit code:

      0  another publisher holds the lock, or this file changed on disk (a git
         pull; the next prompt's hook respawns the loop on the new code), or
         ``stop`` was set
      1  ORG_DB_URL is unset

    Once a minute it also folds the heartbeat hook's file into the hub
    (``_fold_due``); a fold error is reported and rolled back, never fatal.

    A failed connect or publish is reported through ``on_error(class name)``
    (never the message: a psycopg message can name the host), then RETRY_S of
    quiet with the lock still held, then a fresh connection. Zero live sessions
    is a result, not an error: the snapshot is published with 0 rows."""

    def __init__(self, url, host, dirs, *, stop=None, lock_path=LOCK_PATH,
                 on_error=None, connect=None, code_path=Path(__file__),
                 pull=(), pull_fn=None, fold_fn=None,
                 fold_path=Path(__file__).with_name("heartbeat_fold.py"),
                 push=None):
        import threading
        self.url, self.host, self.dirs = url, host, list(dirs)
        self.pull, self._pull_fn = list(pull), pull_fn or pull_remote
        self.push = push        # PortfolioPush on the hub host, else None
        self._pulled_at: dict[str, float] = {}
        self._pulled_prev: dict[str, set[str]] = {}
        self.stop = stop or threading.Event()
        self.lock_path, self.on_error = lock_path, on_error
        self._connect = connect or _connect
        self.code_path, self._code0 = code_path, _code_stamp(code_path)
        self.fold_path, self._fold0 = fold_path, _code_stamp(fold_path)
        self._fold_fn, self._folded_at = fold_fn, None
        self.prev: set[str] = set()

    def _done(self) -> bool:
        return (self.stop.is_set() or _code_stamp(self.code_path) != self._code0
                or _code_stamp(self.fold_path) != self._fold0)

    def run(self) -> int:
        lock = acquire_lock(self.lock_path, write_pid=True)
        if lock is None:
            return 0
        try:
            if not self.url:
                self._report("ORG_DB_URL unset")
                return 1
            while not self._done():
                try:
                    self._hold()
                except Exception as exc:
                    self._report(type(exc.__cause__ or exc).__name__)
                    self.stop.wait(RETRY_S)
            return 0
        finally:
            if self.push:
                self.push.close()
            lock.close()

    def _report(self, what: str) -> None:
        if self.on_error:
            try:
                self.on_error(what)
            except Exception:
                pass

    def _pull_due(self, conn) -> None:
        """Once per REFRESH_S per pulled host, inline: the 25 s cap on one pull
        is the most it can delay the local 5 s loop. A failed pull leaves the
        host's rows alone and records the label; a DB error is not a pull error
        and propagates to run() like any other."""
        for name, ssh in self.pull:
            now = time.monotonic()
            if now - self._pulled_at.get(name, -REFRESH_S) < REFRESH_S:
                continue
            self._pulled_at[name] = now     # failures wait a full period too
            label = f"{_publisher_label()} ssh {self.host}"
            try:
                rows = self._pull_fn(ssh)
            except PullError as exc:
                record_pull_error(conn, name, str(exc), label)
                continue
            self._pulled_prev[name] = publish_rows(
                conn, name, rows, self._pulled_prev.get(name, set()), label)

    def _fold_due(self, conn) -> None:
        """Once per REFRESH_S: fold the heartbeat hook's jsonl into the hub (org
        restructure P3-C, tools/heartbeat_fold.py). Whatever goes wrong here is
        reported and rolled back, never raised: publishing goes on."""
        if self._folded_at is not None and time.monotonic() - self._folded_at < REFRESH_S:
            return
        self._folded_at = time.monotonic()
        try:
            fold = self._fold_fn
            if fold is None:
                from tools.heartbeat_fold import fold
            fold(conn)
        except Exception as exc:
            self._report("heartbeat fold " + type(exc).__name__)
            try:
                conn.rollback()
            except Exception:
                pass

    def _hold(self) -> None:
        conn = self._connect(self.url)
        try:
            last_sig, last_pub = None, 0.0
            while not self._done():
                sig = registry_signature(self.dirs)
                if sig != last_sig or time.monotonic() - last_pub >= REFRESH_S:
                    self.prev = publish_once(conn, self.host, self.dirs, self.prev)
                    last_sig, last_pub = sig, time.monotonic()
                self._pull_due(conn)
                self._fold_due(conn)
                if self.push:
                    self.push.tick()
                self.stop.wait(POLL_S)
        finally:
            try:
                conn.close()
            except Exception:
                pass


def _connect(url, timeout=None):
    """Own connection, never lib.db's pooled one. db_pg.connect raises
    HubConnectError (no SQLite fallback)."""
    from lib import db_pg
    conn = db_pg.connect(url, timeout=timeout or CONNECT_TIMEOUT_S)
    conn.execute(f"SET statement_timeout = {int(STMT_TIMEOUT_MS)}")
    conn.commit()
    return conn


def _spawn_argv(root: Path) -> list[str] | None:
    """argv of the detached loop, or None when this host cannot reach the hub's
    secrets (Windows without a hub prefix). ORG_DB_URL is never read here: the
    wrapper (POSIX) or the infisical prefix (Windows) puts it in the child."""
    tail = ["-m", "tools.live_sessions", "publish", "--loop"]
    if sys.platform == "win32":
        libdir = str(Path(root) / "scripts" / "lib")
        if libdir not in sys.path:
            sys.path.insert(0, libdir)
        import cxo_mcp_config
        prefix = cxo_mcp_config.windows_hub_prefix(str(root))
        return [*prefix, prefix[0], *tail] if prefix else None
    venv_python = Path(root) / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    return ["bash", "scripts/hub/with-org-db-env.sh", python, *tail]


def ensure_publisher(root: Path = ROOT) -> bool:
    """Start the host's publisher unless one is alive. True only when a process
    was spawned. Called from scripts/hook-inbox.py on every C-level prompt, so
    the common case (lock held, a publisher is running) is one open + flock.

    The spawn guard (SPAWN_GAP_S, by the mtime of state/locks/live_sessions.spawned)
    stops a crash loop and two prompts racing; a second process that slips
    through exits at once on the lock. Stderr of the child goes to
    state/live_sessions.log.

    Only the main checkout starts a publisher: a hook running from a worktree
    would put hub credentials behind unreviewed branch code. The lock and the
    stamp are opened with _safe_open (a planted symlink or FIFO there means no
    spawn); an unsafe log only costs the child its stderr."""
    if os.environ.get("ORG_LIVE_SESSIONS", "").strip().lower() == "off":
        return False
    if "worktrees" in Path(root).resolve().parts:
        return False
    locks = Path(root) / "state" / "locks"
    probe = acquire_lock(locks / LOCK_NAME)
    if probe is None:
        return False
    probe.close()
    fd = _safe_open(locks / SPAWN_STAMP, os.O_WRONLY, create=True)
    if fd is None:
        return False
    try:
        st = os.fstat(fd)
        if st.st_size and time.time() - st.st_mtime < SPAWN_GAP_S:   # size 0: just created
            return False
        os.ftruncate(fd, 0)     # stamped before the spawn: a failing spawn cannot loop
        os.write(fd, b"1")
    except OSError:
        return False
    finally:
        os.close(fd)
    argv = _spawn_argv(root)
    if argv is None:
        return False
    import subprocess
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "cwd": str(root)}
    if sys.platform == "win32":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kw["start_new_session"] = True
    log_fd = _safe_open(Path(root) / "state" / "live_sessions.log",
                        os.O_WRONLY | os.O_APPEND, create=True)
    try:
        subprocess.Popen(argv, stderr=subprocess.DEVNULL if log_fd is None else log_fd, **kw)
    finally:
        if log_fd is not None:
            os.close(log_fd)
    return True


# ---------------------------------------------------------------------------
# reader
# ---------------------------------------------------------------------------

def _snapshot_from_hub(conn, ttl_s: float) -> dict:
    """Rows seen within ``ttl_s`` plus each host's publish age. A host whose own
    publish is older than ``ttl_s`` keeps its last rows (up to STALE_SHOW_S old)
    with status "stale": a silent publisher is not proof its sessions ended.
    Ages come from the hub's clock (now() - stored), so host clock skew never shows."""
    hosts = {}
    for r in conn.execute(
            "SELECT host, published_at, error,"
            " EXTRACT(EPOCH FROM now() - published_at) AS age FROM live_hosts").fetchall():
        hosts[r["host"]] = {"age": float(r["age"]), "published_at": r["published_at"],
                            "error": r["error"]}
    rows = []
    have = _live_columns(conn)
    optional = "".join(f"{c if c in have else 'NULL AS ' + c}, " for c in _OPTIONAL_COLS)
    for r in conn.execute(
            "SELECT host, uuid, sid, role, name, address, status, pid, " + optional +
            "EXTRACT(EPOCH FROM now() - seen_at) AS age FROM live_sessions"
            " ORDER BY host, name").fetchall():
        age = float(r["age"])
        info = hosts.get(r["host"])
        host_stale = info is None or info["age"] > ttl_s
        if (age > STALE_SHOW_S) if host_stale else (age > ttl_s):
            continue
        rows.append({"host": r["host"], "uuid": r["uuid"], "sid": r["sid"],
                     "role": r["role"], "name": r["name"], "address": r["address"],
                     "status": "stale" if host_stale else r["status"], "pid": r["pid"],
                     "verified": bool(r.get("verified")), "bridge_id": r.get("bridge_id"),
                     "age": age, "stale": host_stale})
    return {"rows": rows, "hosts": hosts, "local": False}


def _snapshot_local() -> dict:
    """This host's registry straight from disk; no hub."""
    host = _config().self_host()
    rows = [{"host": host, "uuid": r["uuid"], "sid": r["sid"], "role": r["role"],
             "name": r["name"], "address": r["address"], "status": r["status"],
             "pid": r["pid"], "verified": r.get("verified", False), "age": 0.0}
            for r in promote_project_heads(demote_untmuxed(read_registry(session_dirs(host)), host))]
    return {"rows": rows, "hosts": {host: {"age": 0.0, "published_at": None}}, "local": True}


def _host_order(seen) -> list[str]:
    known = list(HOST_ORDER)
    try:
        known += [h for h in _config().hosts() if h not in known]
    except Exception:
        pass
    return known + sorted(h for h in set(seen) if h not in known)


def _fmt_since(dt, today=None) -> str:
    """Thai time, with the date unless ``today`` (a Thai-time date) is the same day."""
    if dt is None:
        return "?"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(TH)
    return dt.strftime("%H:%M" if today == dt.date() else "%m-%d %H:%M")


def reserved_claim(row: dict) -> str | None:
    """"CTO Main" / "CMO Main" when the row's name carries that title and its role is not the
    matching C-level (cto / cmo); None otherwise. NFKC first, so full-width letters read the same."""
    name = unicodedata.normalize("NFKC", row.get("name") or "")
    for m in _RESERVED_RE.finditer(name):
        title = re.sub(r"\s+", "", m.group("title")).upper()
        if row.get("role") != title.lower():
            return f"{title} Main"
    return None


def _line(row: dict) -> str:
    mark = "" if row.get("verified") else f"  {NAME_ONLY}"
    claim = reserved_claim(row)
    if claim:
        mark += f"  ⚠ claims {claim}"
    return f"{row['status']:<7}  {row['address']}{mark}"


def _claims_listed(row: dict) -> bool:
    """An "unknown" row whose name reads as a C-level or a PH (M10 #6): shown, marked."""
    return row["role"] == "unknown" and is_listed(parse_name(row["name"], row["uuid"])[0])


def _rule_context(role: str, host: str) -> tuple[str | None, bool]:
    try:
        cfg = _config()
        persona = cfg.persona_for(role) if is_c_level(role) else None
    except Exception:
        persona = None
    return persona or None, _windows_host(host)


def off_rule_notes(rows) -> list[str]:
    """One line per name that breaks the CEO's 14 Oct naming rule (M10), checked by
    lib/session_names.rule_problem. Rows with no role ("unknown") are not judged."""
    from lib import session_names
    out = []
    for r in rows:
        persona, windows = _rule_context(r["role"], r["host"])
        why = session_names.rule_problem(r["name"], r["role"], r["sid"], r["host"],
                                         persona=persona, windows=windows)
        if why:
            out.append(f'name off-rule: "{r["name"]}" ({r["host"]} #{r["sid"]}): {why}')
    if len(out) > OFF_RULE_LINES:   # the list stays under ~1k tokens
        out = out[:OFF_RULE_LINES] + [f"name off-rule: +{len(out) - OFF_RULE_LINES} more"]
    return out


def _sort_key(row: dict):
    # a Project Head sorts after the C-levels of its status and host
    return (STATUS_RANK.get(row["status"], 2), row["host"], row["role"] == PH_ROLE, row["name"])


def format_snapshot(snap: dict, *, all_roles=False, sid=None, ttl_s=DEFAULT_TTL_S,
                    now: datetime | None = None) -> str:
    rows = snap["rows"]
    if sid is not None:
        want = sid.strip().lstrip("#").lower()
        hit = [r for r in rows if want and (r["sid"] == want or r["uuid"] == want
                                            or r["uuid"].endswith(want))]
        return "\n".join(_line(r) for r in sorted(hit, key=_sort_key)) \
            or "not live (no fresh row)"
    now = now or datetime.now(timezone.utc)
    parts = [f"live {now.astimezone(TH).strftime('%H:%M')} TH"]
    for host in _host_order(list(snap["hosts"]) + [r["host"] for r in rows]):
        info = snap["hosts"].get(host)
        if info is None:
            if not snap["local"]:
                parts.append(f"{host} none (no publisher yet)")
            continue
        if info["age"] > ttl_s:
            n_stale = sum(1 for r in rows if r["host"] == host and is_listed(r["role"]))
            if info.get("error"):
                since = _fmt_since(info["published_at"], now.astimezone(TH).date())
                why = f"unreachable ({info['error']}) since {since}"
            else:
                why = f"no publisher since {_fmt_since(info['published_at'])}"
            parts.append(f"{host} {n_stale} stale ({why})" if n_stale
                         else (f"{host} {why}" if info.get("error") else f"{host} none ({why})"))
            continue
        mine = [r for r in rows if r["host"] == host]
        c_level = sum(1 for r in mine if is_c_level(r["role"]))
        heads = sum(1 for r in mine if r["role"] == PH_ROLE)
        claims = sum(1 for r in mine if _claims_listed(r))
        workers = len(mine) - c_level - heads - claims
        age = "local" if snap["local"] else f"{int(info['age'])}s"
        extra = ((f"+{heads} PH, " if heads else "") + (f"+{claims} name only, " if claims else "")
                 + (f"+{workers} workers, " if workers else ""))
        parts.append(f"{host} {c_level} ({extra}{age})")
    shown = sorted((r for r in rows if all_roles or is_listed(r["role"]) or _claims_listed(r)),
                   key=_sort_key)
    notes = [STALE_NOTE] if any(r.get("stale") for r in shown) else []
    if any(not r.get("verified") for r in shown):
        notes.append(NAME_ONLY_NOTE)
    if any(reserved_claim(r) for r in shown):
        notes.append(CLAIM_NOTE)
    return "\n".join([" · ".join(parts)] + [_line(r) for r in shown] + [FOOTER]
                     + duplicate_notes(shown) + off_rule_notes(shown) + notes)


def duplicate_notes(rows) -> list[str]:
    """One line per address that more than one row carries. A short C-level
    name has no machine or id in it (CEO 2026-10-14), so a Mac "CTO (Kavin)"
    and Contabo's are the same text. The [ref] SendMessage then needs is
    ListAgents' own and cannot be computed here; its rows print "tmux
    <role>-<sid>", which the host and sid below match."""
    by_addr: dict[str, list[dict]] = {}
    for r in rows:
        by_addr.setdefault(r["address"].casefold(), []).append(r)
    out = []
    for group in by_addr.values():
        if len(group) < 2:
            continue
        where = ", ".join(f"{r['host']} #{r['sid']} "
                          + ("tmux-claimed" if r.get("verified") else "name only")
                          for r in group)
        out.append(f'same name on {len(group)} rows: "{group[0]["address"]}" ({where}) — '
                   f'SendMessage needs "<name> [ref]": take the ref from the ListAgents '
                   f'row whose tmux ends "-<sid>", or use send_to_cxo(role=…).')
    return out


def _to_json(snap: dict, *, all_roles=False, sid=None, ttl_s=DEFAULT_TTL_S) -> str:
    rows = sorted((r for r in snap["rows"]
                   if all_roles or sid is not None or is_listed(r["role"]) or _claims_listed(r)),
                  key=_sort_key)
    if sid is not None:
        want = sid.strip().lstrip("#").lower()
        rows = [r for r in rows if want and (r["sid"] == want or r["uuid"].endswith(want))]
    return json.dumps({
        "hosts": {h: {"age_s": int(i["age"]), "fresh": i["age"] <= ttl_s}
                  | ({"error": i["error"]} if i.get("error") else {})
                  for h, i in snap["hosts"].items()},
        "sessions": [{k: r[k] for k in ("host", "sid", "role", "status", "address")}
                     | {"verified": bool(r.get("verified")), "claims": reserved_claim(r)}
                     | {"age_s": int(r["age"]), "stale": bool(r.get("stale"))} for r in rows],
    }, ensure_ascii=False)


def render(conn, *, all_roles=False, sid=None, ttl_s=DEFAULT_TTL_S,
           now: datetime | None = None) -> str:
    """The list: a header line, one line per live session, a footer."""
    return format_snapshot(_snapshot_from_hub(conn, ttl_s), all_roles=all_roles,
                           sid=sid, ttl_s=ttl_s, now=now)


def _unreachable(exc: BaseException) -> str:
    """One line for any failure to read the hub: the error class, never the
    message (a connect error can carry the host, and a URL carries a password)."""
    return (f"live_sessions: hub unreachable ({type(exc.__cause__ or exc).__name__})"
            " — fall back to ListAgents")


class HubUrlUnset(Exception):
    pass


def _open_hub():
    url = (os.environ.get("ORG_DB_URL") or "").strip()
    if not url:
        raise HubUrlUnset()
    return _connect(url, timeout=CONNECT_TIMEOUT_S)


def render_for_tool(id: str = "", all: bool = False) -> str:
    """The MCP tool body: its own short connection, never an exception."""
    conn = None
    try:
        conn = _open_hub()
        return render(conn, all_roles=bool(all), sid=id.strip() or None)
    except Exception as exc:
        return _unreachable(exc)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parser():
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m tools.live_sessions", description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="include workers (C-levels and Project Heads always show)")
    ap.add_argument("--id", dest="sid", help="one session by its short id")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--local", action="store_true", help="this host's registry, no hub")
    sub = ap.add_subparsers(dest="cmd")
    pub = sub.add_parser("publish", help="write this host's sessions to the hub")
    g = pub.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true", help="one publish, prints the count")
    g.add_argument("--loop", action="store_true", help="the host's publisher (exits 0 if one is alive)")
    return ap


def _cmd_publish(args) -> int:
    try:
        host = _config().self_host()
        dirs = session_dirs(host)
        if args.once:
            conn = _open_hub()
            try:
                print(len(publish_once(conn, host, dirs, set())))
            finally:
                conn.close()
            return 0
        last = []

        def err(what):      # stderr is state/live_sessions.log: one line per change, not per retry
            if last[:1] != [what]:
                last[:] = [what]
                stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                print(f"{stamp} live_sessions: publish failed ({what})", file=sys.stderr, flush=True)
        url = (os.environ.get("ORG_DB_URL") or "").strip()
        try:
            return Publisher(url, host, dirs, on_error=err, pull=pull_targets(host),
                             push=make_push(host, err)).run()
        except KeyboardInterrupt:
            return 0
    except Exception as exc:
        print(f"live_sessions: publish failed ({type(exc.__cause__ or exc).__name__})",
              file=sys.stderr)
        return 1


def _read_text(args) -> str:
    """What the reader prints: the list, the json, or the one-line failure."""
    try:
        if args.local:
            snap = _snapshot_local()
        else:
            conn = _open_hub()
            try:
                snap = _snapshot_from_hub(conn, DEFAULT_TTL_S)
            finally:
                conn.close()
        if args.json:
            return _to_json(snap, all_roles=args.all, sid=args.sid, ttl_s=DEFAULT_TTL_S)
        return format_snapshot(snap, all_roles=args.all, sid=args.sid, ttl_s=DEFAULT_TTL_S)
    except Exception as exc:
        if args.local:
            return f"live_sessions: local registry unreadable ({type(exc).__name__})"
        return _unreachable(exc)


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "publish":
        return _cmd_publish(args)
    print(_read_text(args))
    return 0


if __name__ == "__main__":
    try:
        rc = main()
        sys.stdout.flush()
    except BrokenPipeError:     # `| head`: the reader is gone, not an error
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        rc = 0
    sys.exit(rc)
