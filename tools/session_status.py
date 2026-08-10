"""Session lifecycle record — the one writer for ``c_level_sessions.status``.

A C-level session ends in one of three ways (task-728e4741):

  ``closed``
      work finished, nothing to come back to.
  ``saved``
      work unfinished, parked on purpose to free RAM (resumable).
  ``force_saved``
      closed while the work was NOT done — a mistake, flagged (resumable).

This module is the single place that writes those values. It exists so the
kill path, the save path and the close path do not each grow their own SQL and
drift. ``scripts/session-kill.sh`` calls :func:`record_close` BEFORE it tears
the session down, so the row exists even if the process dies mid-teardown.

The full Claude UUID — the resume key — lives in
``state/locks/<role>-<id>.uuid`` (the one suffix the launcher deliberately
preserves on close; see :data:`tools.session_name.KEEP_SUFFIXES`).
:func:`record_close` copies that UUID into ``resume_uuid`` at close time so
the record survives even if the file is later removed by hand.

Reader side: :func:`get` / :func:`list_sessions` / :func:`resume_target`.
``resume_target`` falls back to the ``.uuid`` file for rows created before
this column shipped (the column is NULL but the file is still there).
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKS = ROOT / "state" / "locks"

from lib.db import get_conn, now_iso  # noqa: E402
from tools.session_name import lock_basename  # noqa: E402

# The four values ``c_level_sessions.status`` may legally hold.
STATUSES = ("open", "closed", "saved", "force_saved")
# record_close ENDS a session, so ``open`` is not a legal close target —
# the three values a close may set.
CLOSE_STATUSES = ("closed", "saved", "force_saved")

# Mirrors tools.session_name.KEEP_SUFFIXES — the ``.uuid`` the launcher
# preserves on close (NOT in LOCK_SUFFIXES). It is the resume key.
_UUID_SUFFIX = ".uuid"


def _uuid_path(locks_dir: Path, role: str, session_id: str) -> Path:
    return Path(locks_dir) / f"{lock_basename(role, session_id)}{_UUID_SUFFIX}"


def _read_uuid(locks_dir: Path, role: str, session_id: str) -> str | None:
    """The UUID inside a session's ``.uuid`` file, or None if absent/empty.

    Never raises — a missing file is a normal pre-spawn or hand-cleaned state,
    not an error a caller should have to catch.
    """
    try:
        v = _uuid_path(locks_dir, role, session_id).read_text().strip()
    except OSError:
        return None
    return v or None


def record_close(
    role: str,
    session_id: str,
    status: str,
    *,
    note: str | None = None,
    locks_dir: str | Path | None = None,
) -> None:
    """Record that a session has ended.

    Sets ``status``/``closed_at``/``note`` and copies the resume UUID from the
    session's ``.uuid`` file into ``resume_uuid``. Idempotent UPSERT: a row is
    normally created at spawn by ``register_cxo_session``, but this writes one
    if not (a kill that raced ahead of registration) so the record always
    lands. ``note`` overwrites when given and is preserved when None; the
    freshly-read ``resume_uuid`` wins over any stale column value, but if the
    file is gone the old column value is kept.

    Raises ``ValueError`` for any ``status`` outside the three close literals.
    """
    if status not in CLOSE_STATUSES:
        raise ValueError(
            f"invalid close status {status!r}. allowed: {list(CLOSE_STATUSES)}"
        )
    ld = Path(locks_dir) if locks_dir else LOCKS
    resume_uuid = _read_uuid(ld, role, session_id)
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO c_level_sessions
                 (role, session_id, spawned_at, status, closed_at, note, resume_uuid)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(role, session_id) DO UPDATE SET
                 status      = excluded.status,
                 closed_at   = excluded.closed_at,
                 note        = COALESCE(excluded.note, c_level_sessions.note),
                 resume_uuid = COALESCE(excluded.resume_uuid, c_level_sessions.resume_uuid)""",
            (role, session_id, ts, status, ts, note, resume_uuid),
        )


def get(role: str, session_id: str) -> dict | None:
    """One session row, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM c_level_sessions WHERE role=? AND session_id=?",
            (role, session_id),
        ).fetchone()
    return dict(row) if row else None


def list_sessions(status: str | None = None) -> list[dict]:
    """All session rows, newest-spawned first, optionally filtered by status."""
    q = "SELECT * FROM c_level_sessions"
    args: list = []
    if status is not None:
        if status not in STATUSES:
            raise ValueError(
                f"invalid status {status!r}. allowed: {list(STATUSES)}"
            )
        q += " WHERE status=?"
        args.append(status)
    q += " ORDER BY spawned_at DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def resume_target(
    role: str, session_id: str, *, locks_dir: str | Path | None = None
) -> str | None:
    """The full Claude UUID for resuming this session, or None.

    Prefers ``resume_uuid`` (captured at close time, survives ``.uuid`` file
    removal); falls back to the ``.uuid`` file for pre-rollout rows whose
    column is still NULL. None when neither source has a value.
    """
    row = get(role, session_id)
    uuid = row.get("resume_uuid") if row else None
    if uuid:
        return uuid
    ld = Path(locks_dir) if locks_dir else LOCKS
    return _read_uuid(ld, role, session_id)


def main(argv: list[str] | None = None) -> int:
    """CLI entry — drives :func:`record_close` from the shell.

    ``python -m tools.session_status close --role cto --session-id <id>
       --status saved [--note "..."] [--locks-dir <dir>]``

    Mirrors the ``-m tools.<mod>`` convention every other launcher script uses.
    """
    ap = argparse.ArgumentParser(
        prog="tools.session_status",
        description="Record/read the c_level_sessions lifecycle status.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("close", help="record that a session ended")
    c.add_argument("--role", required=True)
    c.add_argument("--session-id", required=True)
    c.add_argument(
        "--status", required=True, choices=sorted(CLOSE_STATUSES),
        help="closed | saved | force_saved",
    )
    c.add_argument("--note", default=None, help="one line of why (optional)")
    c.add_argument(
        "--locks-dir", default=None,
        help="read the .uuid here instead of the default state/locks",
    )

    args = ap.parse_args(argv)
    if args.cmd == "close":
        record_close(
            args.role, args.session_id, args.status,
            note=args.note, locks_dir=args.locks_dir,
        )
        return 0
    return 2  # unreachable: argparse enforces a subcommand


if __name__ == "__main__":
    raise SystemExit(main())
