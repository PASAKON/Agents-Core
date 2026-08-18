"""Tests for lib/ceo_report.py::report_to_ceo (task-df6de4d4 D3/D6).

Every test isolates ceo_report.QUEUE_DB_PATH and lib.mailbox's INBOX_ROOT to
tmp_path (same pattern scripts/test_relay_mcp_server.py's queue_env fixture
uses) and stubs `ceo_report.current_identity` / `ceo_report.detect_host` --
no real DB, no real SSH, no real mailbox root, no real process env is ever
read. The Mac branch additionally stubs `ceo_report._ssh_exec`, the ONE
choke point both the ledger SQL and the reply-letter tee command go
through, so a test can assert on exactly what left the machine.

Run standalone: python scripts/test_ceo_report.py
Or under pytest:  pytest scripts/test_ceo_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone  # noqa: E402

from lib import ceo_report as cr  # noqa: E402
from lib import mailbox  # noqa: E402
from tools.agent_transport import CEO_IDENTITY, Identity  # noqa: E402


@pytest.fixture
def report_env(tmp_path, monkeypatch):
    """Isolate the ledger DB + mailbox root, and default to a Contabo C-level
    caller (cto#abc123) -- individual tests override detect_host/
    current_identity for the Mac-branch and non-C-level cases."""
    monkeypatch.setattr(cr, "QUEUE_DB_PATH", tmp_path / "relay_queue.db")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setattr(cr, "detect_host", lambda: "contabo")
    monkeypatch.setattr(cr, "current_identity", lambda: Identity("cxo", "cto", "abc123"))
    return tmp_path


def _insert_order(target_role="cto", target_session_id="abc123", host="contabo",
                   order_text="do the thing", status="awaiting_reply") -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with cr._local_conn() as conn:
        cur = conn.execute(
            "INSERT INTO ceo_orders "
            "(target_role, target_session_id, host, order_text, sent_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (target_role, target_session_id, host, order_text, now, status),
        )
        conn.commit()
        return cur.lastrowid


def _reply_letters(inbox_root: Path) -> list[dict]:
    return mailbox.peek("secretary", "sompong", root=inbox_root)


# ---------------------------------------------------------------------------
# 1. Success path (Contabo, local)
# ---------------------------------------------------------------------------

def test_report_to_ceo_success_writes_letter_and_closes_row(report_env):
    order_id = _insert_order()

    result = cr.report_to_ceo(order_id, "done", "shipped it")
    assert result == f"order #{order_id} closed as done"

    letters = _reply_letters(report_env / "inbox")
    assert len(letters) == 1
    assert letters[0]["from"] == {"role": "cto", "session_id": "abc123"}
    assert letters[0]["to"] == {"role": "secretary", "session_id": "sompong"}
    assert f"order #{order_id}" in letters[0]["body"]
    assert "shipped it" in letters[0]["body"]

    with cr._local_conn() as conn:
        row = conn.execute(
            "SELECT status, replied_at, reply_detail FROM ceo_orders WHERE id = ?",
            (order_id,),
        ).fetchone()
    assert row[0] == "done"
    assert row[1] is not None
    assert row[2] == "shipped it"


# ---------------------------------------------------------------------------
# 1b. A failed-over SomPong: the Mac holds the open order, so the reply must
#     land here, not over SSH.
#
# On 2026-08-16 SomPong moved to the Mac and began writing orders into the
# Mac's own relay_queue.db. report_to_ceo still routed by hostname, so it SSH'd
# to Contabo, closed unrelated rows that happened to share an id, shipped the
# letter into a mailbox no live process was reading -- and returned "closed as
# done" for all of it. Four real answers never reached the CEO while every call
# reported success. These two tests pin the rule that replaced hostname
# routing: reply to the ledger that holds this order OPEN.
# ---------------------------------------------------------------------------

def test_mac_with_locally_open_order_replies_locally_and_never_ssh(report_env,
                                                                   monkeypatch):
    monkeypatch.setattr(cr, "detect_host", lambda: "mac")

    def _boom(*a, **k):  # any SSH here means the fix regressed
        raise AssertionError("went to Contabo for an order open on this machine")

    monkeypatch.setattr(cr, "_ssh_sqlite", _boom)
    monkeypatch.setattr(cr, "_ssh_exec", _boom)

    order_id = _insert_order(host="mac")
    assert cr.report_to_ceo(order_id, "done", "answered locally") == \
        f"order #{order_id} closed as done"

    letters = _reply_letters(report_env / "inbox")
    assert len(letters) == 1, "the reply must be readable by the SomPong running here"
    assert "answered locally" in letters[0]["body"]

    with cr._local_conn() as conn:
        status = conn.execute(
            "SELECT status FROM ceo_orders WHERE id = ?", (order_id,)
        ).fetchone()[0]
    assert status == "done"


def test_mac_still_uses_contabo_when_the_local_row_is_not_open(report_env,
                                                              monkeypatch):
    """Ownership is an OPEN row, not a matching id.

    Both ledgers number from 1, so a closed local row carrying the same id is a
    collision, not this order -- it must not capture a Contabo-owned reply.
    """
    monkeypatch.setattr(cr, "detect_host", lambda: "mac")
    order_id = _insert_order(status="done")  # same id, already closed here

    calls = []

    def _fake_ssh_sqlite(sql):
        calls.append(sql)
        return True, "awaiting_reply|"

    monkeypatch.setattr(cr, "_ssh_sqlite", _fake_ssh_sqlite)
    # _ssh_exec returns (ok, output), not a dict -- getting this wrong makes the
    # test fail inside the code under test and look like a real regression.
    monkeypatch.setattr(cr, "_ssh_exec", lambda *a, **k: (True, ""))

    cr.report_to_ceo(order_id, "done", "belongs to Contabo")
    assert calls, "a Contabo-owned order must still be reported over SSH"


# ---------------------------------------------------------------------------
# 2. Bad status -- writes NOTHING (row untouched, no letter)
# ---------------------------------------------------------------------------

def test_bad_status_writes_nothing(report_env):
    order_id = _insert_order()

    result = cr.report_to_ceo(order_id, "in_progress", "still working")
    assert "rejected" in result
    assert "in_progress" in result

    with cr._local_conn() as conn:
        row = conn.execute(
            "SELECT status, replied_at, reply_detail FROM ceo_orders WHERE id = ?",
            (order_id,),
        ).fetchone()
    assert row == ("awaiting_reply", None, None)
    assert _reply_letters(report_env / "inbox") == []


# ---------------------------------------------------------------------------
# 3. Unknown id / double-close -- both honest failures, never silent success
# ---------------------------------------------------------------------------

def test_unknown_order_id_is_reported_as_failure(report_env):
    result = cr.report_to_ceo(999, "done", "whatever")
    assert "not found" in result
    assert _reply_letters(report_env / "inbox") == []


def test_double_close_is_reported_as_failure(report_env):
    order_id = _insert_order()

    first = cr.report_to_ceo(order_id, "done", "shipped")
    assert first == f"order #{order_id} closed as done"

    second = cr.report_to_ceo(order_id, "failed", "actually no")
    assert "already closed as done" in second

    # The second call must not have written a second letter or touched the row.
    assert len(_reply_letters(report_env / "inbox")) == 1
    with cr._local_conn() as conn:
        row = conn.execute(
            "SELECT status, reply_detail FROM ceo_orders WHERE id = ?", (order_id,)
        ).fetchone()
    assert row == ("done", "shipped")


# ---------------------------------------------------------------------------
# 4. Two open orders close independently by id
# ---------------------------------------------------------------------------

def test_two_open_orders_close_independently_by_id(report_env):
    order_a = _insert_order(order_text="task A")
    order_b = _insert_order(order_text="task B")

    result = cr.report_to_ceo(order_a, "done", "A done")
    assert result == f"order #{order_a} closed as done"

    with cr._local_conn() as conn:
        status_a = conn.execute(
            "SELECT status FROM ceo_orders WHERE id = ?", (order_a,)
        ).fetchone()[0]
        status_b = conn.execute(
            "SELECT status FROM ceo_orders WHERE id = ?", (order_b,)
        ).fetchone()[0]
    assert status_a == "done"
    assert status_b == "awaiting_reply"


# ---------------------------------------------------------------------------
# 5. Non-C-level caller refused
# ---------------------------------------------------------------------------

def test_non_c_level_identity_is_refused(report_env, monkeypatch):
    monkeypatch.setattr(cr, "current_identity", lambda: CEO_IDENTITY)
    order_id = _insert_order()

    result = cr.report_to_ceo(order_id, "done", "x")
    assert "rejected" in result

    with cr._local_conn() as conn:
        row = conn.execute(
            "SELECT status FROM ceo_orders WHERE id = ?", (order_id,)
        ).fetchone()
    assert row[0] == "awaiting_reply"
    assert _reply_letters(report_env / "inbox") == []


# ---------------------------------------------------------------------------
# 6. Mac branch -- SSH transport stubbed
# ---------------------------------------------------------------------------

def test_mac_side_reply_ssh_stubbed_success(report_env, monkeypatch):
    """The SQL (lookup SELECT + close UPDATE) and the mailbox tee both go
    out over the ONE stubbed choke point (_ssh_exec) -- assert the actual
    SQL text is what's sent, not just that "something" was sent."""
    monkeypatch.setattr(cr, "detect_host", lambda: "mac")
    calls: list[tuple[str, str | None]] = []

    def fake_ssh_exec(remote_cmd: str, input_text: str | None = None):
        calls.append((remote_cmd, input_text))
        if "SELECT status" in remote_cmd:
            return True, "awaiting_reply|\n"
        if "tee" in remote_cmd:
            return True, ""
        if "UPDATE ceo_orders" in remote_cmd:
            return True, "1\n"
        raise AssertionError(f"unexpected remote command: {remote_cmd!r}")

    monkeypatch.setattr(cr, "_ssh_exec", fake_ssh_exec)

    result = cr.report_to_ceo(7, "blocked", "waiting on CEO reply")
    assert result == "order #7 closed as blocked"

    # remote_cmd is shell-quoted (shlex.quote wraps embedded quotes as
    # '"'"' sequences), so assert on substrings that survive that mangling
    # rather than exact SQL punctuation.
    sql_calls = [c for c, _ in calls if "sqlite3" in c]
    assert any("SELECT status" in c and "7" in c for c in sql_calls)
    assert any("UPDATE ceo_orders" in c and "blocked" in c and "7" in c
               for c in sql_calls)
    tee_calls = [(c, i) for c, i in calls if "tee" in c]
    assert len(tee_calls) == 1
    assert tee_calls[0][1] is not None and "waiting on CEO reply" in tee_calls[0][1]


def test_mac_side_ssh_failure_is_explicit_error_not_success(report_env, monkeypatch):
    """An unreachable VPS must surface as an explicit failure -- never a
    claimed 'closed as ...' for a reply that never landed anywhere."""
    monkeypatch.setattr(cr, "detect_host", lambda: "mac")

    def fake_ssh_exec(remote_cmd: str, input_text: str | None = None):
        return False, "ssh: connect to host mooniex-vps port 22: Connection refused"

    monkeypatch.setattr(cr, "_ssh_exec", fake_ssh_exec)

    result = cr.report_to_ceo(3, "done", "x")
    assert "closed as" not in result
    assert "cannot reach Contabo" in result


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
