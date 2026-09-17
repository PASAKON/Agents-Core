"""Set/get/clear the one-line charter for the current C-level session.

IRON-RULES §35 (session discipline) binds a session to one problem, but
/session-open — the skill meant to enforce it — never writes to the DB, so
it was skippable (2026-09-17 incident: CTO session 4a904905 skipped it and
fanned into 5 unrelated threads). lib/db.py's create_task() now refuses to
create a task for a session with no charter set here — that's the actual
enforcement; this CLI is how a session sets it.

Usage:
    python3 -m tools.session_charter set "<one-line entry problem>"
    python3 -m tools.session_charter get
    python3 -m tools.session_charter clear

Resolves the current session the same way lib.db.create_task does:
CTO_SESSION_ID (+ role 'cto'), else CXO_SESSION_ID + CXO_ROLE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db  # noqa: E402

MIN_CHARTER_LEN = 10


def _current_session() -> tuple[str | None, str | None]:
    return db.resolve_session_owner()


def _require_session() -> tuple[str, str | None]:
    owner_cto, owner_role = _current_session()
    if not owner_cto:
        raise RuntimeError(
            "no session id in env (CTO_SESSION_ID / CXO_SESSION_ID) — "
            "session_charter only runs inside a spawned C-level session."
        )
    return owner_cto, owner_role


def set_charter(text: str) -> None:
    charter = (text or "").strip()
    if len(charter) < MIN_CHARTER_LEN:
        raise ValueError(
            f"charter must be at least {MIN_CHARTER_LEN} non-whitespace "
            f"characters (got {len(charter)}): {text!r}"
        )
    owner_cto, owner_role = _require_session()
    with db.get_conn() as conn:
        cur = conn.execute(
            "UPDATE c_level_sessions SET charter=? WHERE role=? AND session_id=?",
            (charter, owner_role, owner_cto),
        )
        if cur.rowcount == 0:
            # Never silently INSERT — an unregistered session is a bug to
            # surface, not paper over (register_cxo_session/spawn scripts are
            # the only writers that create this row).
            raise RuntimeError(
                f"session ({owner_role}, {owner_cto}) is not registered in "
                f"c_level_sessions — it was not spawned through the normal "
                f"spawn path (register_cxo_session). Not writing a charter "
                f"for a session that doesn't exist."
            )
    print(f"[session_charter] set for ({owner_role}, {owner_cto}): {charter!r}")


def get_charter() -> str | None:
    owner_cto, owner_role = _require_session()
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT charter FROM c_level_sessions WHERE role=? AND session_id=?",
            (owner_role, owner_cto),
        ).fetchone()
    if row is None:
        raise RuntimeError(
            f"session ({owner_role}, {owner_cto}) is not registered in "
            f"c_level_sessions."
        )
    return row["charter"] or None


def clear_charter() -> None:
    owner_cto, owner_role = _require_session()
    with db.get_conn() as conn:
        cur = conn.execute(
            "UPDATE c_level_sessions SET charter=NULL WHERE role=? AND session_id=?",
            (owner_role, owner_cto),
        )
        if cur.rowcount == 0:
            raise RuntimeError(
                f"session ({owner_role}, {owner_cto}) is not registered in "
                f"c_level_sessions."
            )
    print(f"[session_charter] cleared for ({owner_role}, {owner_cto})")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 1
    cmd, rest = argv[0], argv[1:]
    # Apply pending schema migrations first. `charter` arrived with the
    # registry work (851b0d5) as an idempotent ADD COLUMN inside db.init(),
    # but nothing on a plain `git pull` calls init() — the Contabo CTO hit
    # `sqlite3.OperationalError: no such column: charter` on 2026-09-17 and
    # had to spelunk for the one-liner. Cheap, idempotent, so run it always.
    db.init()
    try:
        if cmd == "set":
            if not rest:
                print('usage: python3 -m tools.session_charter set "<text>"',
                      file=sys.stderr)
                return 1
            set_charter(" ".join(rest))
        elif cmd == "get":
            charter = get_charter()
            print(charter if charter else "(empty)")
        elif cmd == "clear":
            clear_charter()
        else:
            print(f"unknown command {cmd!r}. usage: set|get|clear",
                  file=sys.stderr)
            return 1
    except (RuntimeError, ValueError) as e:
        print(f"[session_charter] ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
