"""care_outbox store (S1, docs/design/mooniex-care.md §2).

Portable SQL: runs on sqlite3 (tests) and, via the same statements with the
migration in `lib/care/care_outbox.pg.sql`, on the Postgres hub. The store
takes a DB-API connection with qmark params (sqlite3 style). No customer text
or token is ever written to logs by this module.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

STATES = ("queued", "sending", "sent", "deferred", "dropped", "failed", "fallback")
KINDS = ("care_reply", "important_announcement")
VIAS = ("api_reply", "oa_browser", "api_push")
DEFAULT_BASIC_ID = "@587kfqpt"

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS care_outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idempotency_key TEXT NOT NULL UNIQUE,
  channel_basic_id TEXT NOT NULL DEFAULT '@587kfqpt',
  recipient_id TEXT NOT NULL,
  recipient_display_name TEXT NOT NULL,
  message_kind TEXT NOT NULL CHECK (message_kind IN ('care_reply','important_announcement')),
  critical INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL,
  reply_token TEXT,
  reply_token_expires_at TEXT,
  state TEXT NOT NULL DEFAULT 'queued'
    CHECK (state IN ('queued','sending','sent','deferred','dropped','failed','fallback')),
  delivery_via TEXT CHECK (delivery_via IS NULL OR delivery_via IN ('api_reply','oa_browser','api_push')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  sending_started_at TEXT,
  sent_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS care_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

PG_MIGRATION_PATH = Path(__file__).with_name("care_outbox.pg.sql")


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_idempotency_key(channel_id: str, recipient_id: str, source_event_id: str, seq: str) -> str:
    raw = ":".join((channel_id, recipient_id, source_event_id, seq))
    return hashlib.sha256(raw.encode()).hexdigest()


class Outbox:
    def __init__(self, conn, clock=_now):
        self.conn = conn
        self.clock = clock

    def init_schema(self) -> None:
        self.conn.executescript(SQLITE_SCHEMA)
        self.conn.commit()

    def _ts(self) -> str:
        return _iso(self.clock())

    def enqueue(self, *, idempotency_key: str, recipient_id: str, recipient_display_name: str,
                message_kind: str, payload: Any, reply_token: Optional[str] = None,
                reply_token_expires_at: Optional[datetime] = None, critical: bool = False,
                channel_basic_id: str = DEFAULT_BASIC_ID) -> tuple[int, bool]:
        """Insert once per idempotency key. Returns (row_id, created)."""
        if message_kind not in KINDS:
            raise ValueError("bad message_kind")
        ts = self._ts()
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO care_outbox (idempotency_key, channel_basic_id, recipient_id,"
            " recipient_display_name, message_kind, critical, payload_json, reply_token,"
            " reply_token_expires_at, state, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?, 'queued', ?, ?)",
            (idempotency_key, channel_basic_id, recipient_id, recipient_display_name,
             message_kind, 1 if critical else 0, json.dumps(payload), reply_token,
             _iso(reply_token_expires_at), ts, ts))
        created = cur.rowcount == 1
        self.conn.commit()
        row = self.conn.execute("SELECT id FROM care_outbox WHERE idempotency_key=?",
                                (idempotency_key,)).fetchone()
        return row[0], created

    def get(self, row_id: int) -> dict:
        cur = self.conn.execute("SELECT * FROM care_outbox WHERE id=?", (row_id,))
        cols = [c[0] for c in cur.description]
        r = cur.fetchone()
        if r is None:
            raise KeyError(row_id)
        return dict(zip(cols, r))

    def claim_sending(self, row_id: int, via: str) -> bool:
        """Atomic queued/deferred -> sending. MUST run before any send."""
        if via not in VIAS:
            raise ValueError("bad via")
        ts = self._ts()
        cur = self.conn.execute(
            "UPDATE care_outbox SET state='sending', delivery_via=?, sending_started_at=?,"
            " attempt_count=attempt_count+1, updated_at=?"
            " WHERE id=? AND state IN ('queued','deferred')", (via, ts, ts, row_id))
        self.conn.commit()
        return cur.rowcount == 1

    def _finish(self, row_id: int, state: str, error: Optional[str], sent: bool = False,
                from_states=("sending",)) -> bool:
        ts = self._ts()
        marks = ",".join("?" * len(from_states))
        cur = self.conn.execute(
            f"UPDATE care_outbox SET state=?, last_error=?, sent_at=CASE WHEN ? THEN ? ELSE sent_at END,"
            f" updated_at=? WHERE id=? AND state IN ({marks})",
            (state, error, 1 if sent else 0, ts, ts, row_id, *from_states))
        self.conn.commit()
        return cur.rowcount == 1

    def mark_sent(self, row_id: int) -> bool:
        return self._finish(row_id, "sent", None, sent=True)

    def mark_failed(self, row_id: int, error: str) -> bool:
        return self._finish(row_id, "failed", error, from_states=("sending", "queued", "deferred"))

    def mark_deferred(self, row_id: int, error: str) -> bool:
        return self._finish(row_id, "deferred", error, from_states=("sending", "queued", "deferred"))

    def mark_dropped(self, row_id: int, error: str) -> bool:
        return self._finish(row_id, "dropped", error, from_states=("sending", "queued", "deferred"))

    def mark_fallback(self, row_id: int, error: str) -> bool:
        return self._finish(row_id, "fallback", error, from_states=("sending", "queued", "deferred"))

    def clear_reply_token(self, row_id: int) -> None:
        self.conn.execute("UPDATE care_outbox SET reply_token=NULL, updated_at=? WHERE id=?",
                          (self._ts(), row_id))
        self.conn.commit()

    def stuck_sending(self) -> list[int]:
        """Rows left in `sending` after a crash: never auto-retried (design §2.3.3)."""
        return [r[0] for r in self.conn.execute(
            "SELECT id FROM care_outbox WHERE state='sending' ORDER BY id")]

    def pending(self) -> list[int]:
        return [r[0] for r in self.conn.execute(
            "SELECT id FROM care_outbox WHERE state IN ('queued','deferred') ORDER BY id")]

    # key/value flags (alert dedupe, monthly push halt)
    def get_flag(self, key: str) -> Optional[str]:
        r = self.conn.execute("SELECT value FROM care_state WHERE key=?", (key,)).fetchone()
        return r[0] if r else None

    def set_flag(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO care_state (key,value,updated_at) VALUES (?,?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, self._ts()))
        self.conn.commit()

    def set_flag_once(self, key: str, value: str) -> bool:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO care_state (key,value,updated_at) VALUES (?,?,?)",
            (key, value, self._ts()))
        self.conn.commit()
        return cur.rowcount == 1
