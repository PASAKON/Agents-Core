#!/usr/bin/env python3
"""org_inspector.py — READ-ONLY data layer for "what is the org doing right
now" and "what saved history exists" (task-05ae76f3).

Backs the two questions the CEO asks SomPong (the Telegram secretary) from
the phone:

  "มี terminal อะไรเปิดอยู่บ้าง / อยู่ Mac หรือ Contabo / คุยเรื่องอะไร /
   ทำงานอยู่หรือ idle / ไปถึงกี่ % แล้ว / ใครติด blocker อะไร"
  "ขอดูประวัติ session เก่าหน่อย"

Host-agnostic: it runs unchanged on the Mac (iTerm + hundreds of saved
sessions) and on Contabo (neither), and reports what is actually on THIS
machine — never guesses, never reaches for the other host. The caller merges
the two views.

READ-ONLY BY DESIGN (CEO constraint): SomPong is a middleman — it looks
things up and passes messages, it never does the work and never fixes the
problem itself. Nothing in this module writes, deletes, spawns, or sends
anything. If you find yourself adding a function that changes state, you
have misread the design.

Consumed by runners/mac_agent.py (kinds 'terminals' and 'history'); the
Contabo-side MCP wiring is a separate task.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# One copy of the tab-title grammar (glyphs + blocker extraction) lives in
# scripts/session_list.py; we import it rather than grow a second, drifting
# copy. session_list is import-safe: everything side-effecting sits in main().
from scripts.session_list import GLYPHS, birth, parse_title  # noqa: E402

TAB_DIR = Path(os.environ.get("ORG_INSPECTOR_TAB_DIR", ROOT / "state" / "tab-titles"))
LOG_DIR = Path(os.environ.get("ORG_INSPECTOR_LOG_DIR", ROOT / "state" / "logs"))
SAVE_DIR = Path(os.environ.get(
    "ORG_INSPECTOR_SAVE_DIR", Path.home() / ".claude" / "session-data"))

# Session ids are hex by construction (scripts/session_list.py ID_RE); a
# non-hex id can only come from a caller, so it matches nothing rather than
# being interpolated into a glob.
SID_RE = re.compile(r"^[0-9a-fA-F]{6,}$")
SESSION_NAME_RE = re.compile(r"^(?P<role>[A-Za-z][A-Za-z0-9]*)-(?P<sid>[0-9a-fA-F]{6,})$")

# ---------------------------------------------------------------------------
# history_read — the one function that returns file CONTENT, so it carries the
# whole security burden. Everything is allowlist-driven; refusals return a
# {"status": "rejected", "reason": ...} dict and never raise, never partially
# succeed, and never open the file.
# ---------------------------------------------------------------------------

# Explicit allowlist of roots a history_read may touch, compared on RESOLVED
# paths so both `../` traversal and a symlink pointing outward are refused.
#
# ⚠ Raw Claude Code transcripts (~/.claude/projects/**/*.jsonl) are
# deliberately NOT in this list and must never be added. They are full
# verbatim conversations — secrets have been pasted into C-level chats and
# live in them forever (e.g. a Cloudflare API token, 7 Aug). history_read
# feeds Telegram; reading transcripts through it would exfiltrate them. The
# /session-save summaries plus the structured event logs give the CEO the
# history without that hazard.
ALLOWED_HISTORY_ROOTS: tuple[Path, ...] = (
    LOG_DIR,
    TAB_DIR,
    SAVE_DIR,
)

# Extension ALLOWLIST, not a blocklist — a blocklist is a promise you cannot
# keep (there is no finite list of dangerous extensions).
ALLOWED_HISTORY_EXTENSIONS = frozenset({".log", ".tmp", ".title", ".base", ".json"})

# Line cap matches READ_SESSION_MAX_LINES in runners/relay_mcp_server.py —
# one shared notion of "how much text may leave the machine in one call".
MAX_TAIL_LINES = 200

# Byte cap so a giant file cannot be pulled through in one call even when it
# has very long lines.
MAX_READ_BYTES = 256 * 1024


def detect_host() -> str:
    """Which machine this module is running on. Detected, never guessed.

    ORG_INSPECTOR_HOST wins first (tests, unusual boxes), then the platform.
    This module can only ever see the host it runs on — reporting the other
    machine's sessions from here is the caller's merge job, not ours.
    """
    override = os.environ.get("ORG_INSPECTOR_HOST")
    if override:
        return override
    return "mac" if sys.platform == "darwin" else "contabo"


def _tmux_bin() -> str:
    """Absolute path to tmux. Same rationale as mac_agent._tmux_bin(): under
    launchd/systemd the process gets a bare PATH and Homebrew's /opt/homebrew
    is not on it; a plain "tmux" then resolves to nothing and live sessions
    get misreported as absent. Kept local (not imported) so this tool never
    pulls in runners.* and its heavier module-level config."""
    override = os.environ.get("ORG_INSPECTOR_TMUX_BIN")
    if override:
        return override
    for candidate in ("/opt/homebrew/bin/tmux", "/usr/local/bin/tmux", "/usr/bin/tmux"):
        if Path(candidate).exists():
            return candidate
    return "tmux"  # last resort; surfaces as a real error, not a silent miss


def _tmux_ls() -> dict[str, dict]:
    """Live tmux sessions as {name: {"activity": epoch, "attached": bool}}.

    returncode != 0 means "no server / no sessions / no tmux" — all of those
    are simply "nothing live right now", not errors worth raising on.
    """
    try:
        r = subprocess.run(
            [_tmux_bin(), "ls", "-F",
             "#{session_name} #{session_activity} #{session_attached}"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if r.returncode != 0:
        return {}
    out: dict[str, dict] = {}
    for line in r.stdout.splitlines():
        parts = line.strip().rsplit(" ", 2)
        if len(parts) != 3:
            continue
        name, activity, attached = parts
        try:
            out[name] = {
                "activity": float(activity),
                "attached": int(attached) > 0,
            }
        except ValueError:
            continue
    return out


def _read_main_json(stem: str) -> dict:
    """{goal, done, total} from a .main.json, or {} when absent/unparseable.

    A half-written or corrupt file must read as "progress unknown", not crash
    the whole listing."""
    try:
        data = json.loads((TAB_DIR / f"{stem}.main.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _percent(done, total) -> int | None:
    """round(done / total * 100), or None when unknown. Never invented from
    glyph or age — a made-up number reported to the CEO over Telegram is
    worse than "ไม่รู้"."""
    if not isinstance(done, int) or not isinstance(total, int) or total == 0:
        return None
    return round(done / total * 100)


def list_sessions(include_closed: bool = False) -> list[dict]:
    """One row per C-level session on THIS host, newest activity first.

    Merges live tmux with the on-disk tab-title state; the two are
    independent — a .title with no live tmux is a past session, a live tmux
    with no .title never set one. Both are real and both appear, with the
    missing half as None.

    include_closed=False (default) hides 🏁/🔗 rows that are not live — the
    CEO wants "what is happening now" 95% of the time.
    """
    host = detect_host()
    now = time.time()
    live = _tmux_ls()
    # lowercased stem -> (actual tmux name, info); tmux names are lowercase in
    # practice but a stray uppercase spawn must not fork one session into two
    # rows (one live, one not)
    live_by_stem = {k.lower(): (k, v) for k, v in live.items()}

    stems: dict[str, tuple[str, str]] = {}  # "role-id" -> (role, id)
    for name in live:
        m = SESSION_NAME_RE.match(name)
        if m:
            stems[name.lower()] = (m.group("role").lower(), m.group("sid").lower())
    if TAB_DIR.is_dir():
        for fn in TAB_DIR.iterdir():
            if not fn.name.endswith(".title"):
                continue
            m = SESSION_NAME_RE.match(fn.name[:-len(".title")])
            if m:
                stem = f"{m.group('role').lower()}-{m.group('sid').lower()}"
                stems.setdefault(stem, (m.group("role").lower(), m.group("sid").lower()))

    rows = []
    for stem, (role, sid) in stems.items():
        tmux_entry = live_by_stem.get(stem)
        title_path = TAB_DIR / f"{stem}.title"
        log_path = LOG_DIR / f"{stem}.log"

        glyph = state = summary = blocker = None
        try:
            glyph, state, summary, blocker = parse_title(
                title_path.read_text(encoding="utf-8").strip())
        except OSError:
            pass  # live session that never set a title — glyph stays None

        main = _read_main_json(stem)
        goal = main.get("goal") if isinstance(main.get("goal"), str) else None
        done = main.get("done") if isinstance(main.get("done"), int) else None
        total = main.get("total") if isinstance(main.get("total"), int) else None

        # created ≈ spawn time: earliest birth across title/base/log
        cands = []
        for p in (title_path, TAB_DIR / f"{stem}.base", log_path):
            try:
                cands.append(birth(p))
            except OSError:
                pass
        created = min(cands) if cands else None

        # last activity: newest of title/log mtime and (if live) tmux activity
        la = []
        for p in (title_path, log_path):
            try:
                la.append(p.stat().st_mtime)
            except OSError:
                pass
        if tmux_entry:
            la.append(tmux_entry[1]["activity"])
        last_active = max(la) if la else now

        rows.append({
            "host": host,
            "role": role,
            "id": sid,
            "tmux_name": tmux_entry[0] if tmux_entry else None,
            "live": tmux_entry is not None,
            "attached": bool(tmux_entry and tmux_entry[1]["attached"]),
            "glyph": glyph,
            "state": state,
            "summary": summary,
            "goal": goal,
            "done": done,
            "total": total,
            "percent": _percent(done, total),
            "blocker": blocker,
            "created": created,
            "last_active": last_active,
            "idle_seconds": max(0, int(now - last_active)),
        })

    if not include_closed:
        rows = [r for r in rows
                if r["live"] or r["glyph"] not in ("🏁", "🔗")]
    rows.sort(key=lambda r: r["last_active"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# history — sizes and counts only (history_index); one file's tail
# (history_read), behind the allowlists above.
# ---------------------------------------------------------------------------

def _file_info(path: Path) -> dict:
    st = path.stat()
    return {"path": str(path), "bytes": st.st_size, "mtime": st.st_mtime}


def history_index(session_id: str | None = None) -> dict:
    """What saved history exists — sizes and counts, never content.

    With session_id, only that session's event log and /session-save files;
    without it, every session-save file on the host.

    Event logs are enumerated ONLY for a named session: line-counting every
    log on the host is slow (777 files on this Mac), so without a session_id
    they are deliberately skipped — and the skip is SAID, never reported as
    a zero (`event_logs: None`, `counts.event_logs: "not_enumerated"`,
    `event_logs_enumerated: False`). SomPong reads this back to the CEO over
    Telegram; a 0 there means "ไม่มี log เลย", which would be a lie — 0 must
    stay reserved for "we looked and there are none". The bare file count
    (`event_log_files`) is cheap even when line counts are not, so it is
    always included.
    """
    sid = None
    asked = session_id is not None
    if asked:
        if not SID_RE.fullmatch(session_id):
            # Non-hex id can only come from a caller. Match nothing rather
            # than interpolate it into a glob pattern.
            session_id = ""
        sid = session_id.lower() or None

    event_logs = None
    if sid and LOG_DIR.is_dir():
        event_logs = []
        for p in sorted(LOG_DIR.glob(f"*-{sid}.log")):
            try:
                info = _file_info(p)
            except OSError:
                continue
            role = p.name[: -len(sid) - len(".log") - 1]
            lines = 0
            try:
                with open(p, "rb") as fh:
                    for _ in fh:
                        lines += 1
            except OSError:
                lines = None
            event_logs.append({**info, "role": role, "lines": lines})
    elif asked:
        # A (possibly invalid) session that matches nothing: we LOOKED, so
        # an empty list is a genuine zero, not an omission.
        event_logs = []

    # Cheap even when line counts are not: one iterdir, no file opens.
    event_log_files = None
    if LOG_DIR.is_dir():
        try:
            event_log_files = sum(
                1 for p in LOG_DIR.iterdir()
                if p.name.endswith(".log"))
        except OSError:
            pass

    saves = []
    if SAVE_DIR.is_dir():
        pattern = f"*-{sid}-session.tmp" if sid else "*-session.tmp"
        for p in SAVE_DIR.glob(pattern):
            try:
                saves.append(_file_info(p))
            except OSError:
                continue
        saves.sort(key=lambda s: s["mtime"], reverse=True)

    return {
        "host": detect_host(),
        "session_id": sid,
        "event_logs": event_logs,
        "event_logs_enumerated": event_logs is not None,
        "event_log_files": event_log_files,
        "session_saves": saves,
        "counts": {
            "event_logs": len(event_logs) if event_logs is not None
                          else "not_enumerated",
            "session_saves": len(saves),
        },
    }


def _contained(path: Path, roots: tuple[Path, ...]) -> Path | None:
    """Resolved path if it sits under one of `roots` (compared resolved, so
    `../` and an outward symlink both fail), else None."""
    try:
        resolved = Path(path).resolve()
    except OSError:
        return None
    for root in roots:
        try:
            r = Path(root).resolve()
        except OSError:
            continue
        if resolved == r or r in resolved.parents:
            return resolved
    return None


def history_read(path: str, tail_lines: int = 80) -> dict:
    """Tail of ONE history file, or a rejection. Never raises, never
    partially succeeds, and never opens a file that failed a check."""
    if not isinstance(path, str) or not path.strip():
        return {"status": "rejected", "reason": "path must be a non-empty string"}
    suffix = Path(path).suffix.lower()
    if suffix not in ALLOWED_HISTORY_EXTENSIONS:
        return {"status": "rejected",
                "reason": f"extension {suffix!r} not in allowlist "
                          f"({', '.join(sorted(ALLOWED_HISTORY_EXTENSIONS))})"}
    resolved = _contained(Path(path), ALLOWED_HISTORY_ROOTS)
    if resolved is None:
        return {"status": "rejected",
                "reason": "path is outside ALLOWED_HISTORY_ROOTS "
                          "(state/logs, state/tab-titles, ~/.claude/session-data)"}

    try:
        st = resolved.stat()
        if not resolved.is_file():
            return {"status": "rejected", "reason": "not a regular file"}
    except OSError:
        return {"status": "rejected", "reason": "file not found"}

    capped_lines = max(1, min(int(tail_lines), MAX_TAIL_LINES))
    truncated_bytes = 0
    try:
        with open(resolved, "rb") as fh:
            if st.st_size > MAX_READ_BYTES:
                fh.seek(-MAX_READ_BYTES, os.SEEK_END)
                raw = fh.read()
                raw = raw.split(b"\n", 1)[1]  # drop the partial first line
                truncated_bytes = st.st_size - len(raw)
            else:
                raw = fh.read()
    except OSError as e:
        return {"status": "rejected", "reason": f"read failed: {e}"}

    lines = raw.decode("utf-8", errors="replace").splitlines()
    kept = lines[-capped_lines:]
    return {
        "status": "ok",
        "path": str(resolved),
        "bytes_total": st.st_size,
        "bytes_read": len(raw),
        "truncated_bytes": truncated_bytes,
        "lines_total": len(lines),
        "lines_returned": len(kept),
        "text": "\n".join(kept),
    }
