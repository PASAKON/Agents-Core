"""Tests for tools/send_to_worker.py's remote (non-mac) delivery path.

GH #150 (task task-e40fc5a1): a task whose `host` is not mac/None has no
`tmux_session` -- the old mailbox+tmux path silently no-op'd the wake while
still returning "queued", reading as delivered when nothing had reached the
box. `send()` now hands such a task to `_send_remote()`, which writes into
the DEV's MAILBOX.md over ssh (message body travels on stdin, never
interpolated into the command string) and returns "delivered ..." only
once it has read the line back and confirmed it matches.

Mirrors scripts/test_send_to_worker.py's fixture style (pytest, tmp_path
DB only, ADR 0021 §1 -- never the real state/tasks.db). All ssh calls go
through a fake `subprocess.run` -- no real network, no real winbox.
"""
from __future__ import annotations

import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.mailbox as mailbox  # noqa: E402
import tools.send_to_worker as sd  # noqa: E402


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return db_mod


@pytest.fixture()
def isolated_mailbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "inbox"
    monkeypatch.setattr(mailbox, "INBOX_ROOT", root)
    return root


@pytest.fixture(autouse=True)
def clean_identity_env(monkeypatch: pytest.MonkeyPatch):
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID",
                "WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)


def _insert_task(conn, *, task_id: str | None = None, role: str = "developer",
                 host: str | None = None, worktree: str | None = None) -> str:
    tid = task_id or ("task-" + uuid.uuid4().hex[:8])
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            depends_on, touches, host, worktree, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, "test-proj", role, "in_progress", "t", "d",
         "[]", "[]", host, worktree, ts, ts),
    )
    conn.commit()
    return tid


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# ---------------------------------------------------------------------------
# host=winbox: ssh + stdin transport, read-back verification, "delivered ..."
# ---------------------------------------------------------------------------

def test_remote_send_writes_over_stdin_and_confirms_readback(
    isolated_db, monkeypatch,
):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(
            conn, role="developer", host="winbox",
            worktree=r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__developer__task-remote01",
        )

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        line = kwargs["input"]
        # Simulate: Test-Path ok, Add-Content, then Get-Content -Tail 1
        # echoing exactly the line that was appended.
        return _Result(0, stdout=line + "\n")

    monkeypatch.setattr(sd.subprocess, "run", fake_run)

    result = sd.send(tid, "ทดสอบข้อความภาษาไทย ส่งผ่าน stdin")

    assert result.startswith(f"delivered to Developer ({tid}) on winbox: ")
    assert "queued" not in result
    assert "ทดสอบข้อความภาษาไทย ส่งผ่าน stdin" in result

    assert len(calls) == 1
    call = calls[0]
    assert call["cmd"][:2] == ["ssh", "winbox"]
    # Message body travels ONLY on stdin -- never interpolated into argv,
    # so the destination shell never gets a chance to re-parse it as script.
    assert "ทดสอบข้อความภาษาไทย" not in " ".join(call["cmd"])
    sent_line = call["kwargs"]["input"]
    assert "ทดสอบข้อความภาษาไทย ส่งผ่าน stdin" in sent_line
    assert "\n" not in sent_line  # one line, no embedded newline
    assert sent_line.count(" | ") == 2  # <ts> | <from> | <message>


def test_remote_send_strips_embedded_newlines_from_message(isolated_db, monkeypatch):
    """MAILBOX.md is append-only, one line per message -- the sent line
    itself must never carry an embedded newline, even though the return
    string (like the mac "queued ..." string) still echoes the caller's raw
    message verbatim, newlines and all."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(
            conn, role="developer", host="winbox",
            worktree=r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__developer__task-remote02",
        )

    sent = {}

    def fake_run(cmd, **kwargs):
        line = kwargs["input"]
        sent["line"] = line
        return _Result(0, stdout=line + "\n")

    monkeypatch.setattr(sd.subprocess, "run", fake_run)

    result = sd.send(tid, "line one\nline two\r\nline three")
    assert result.startswith("delivered to")
    assert "\n" not in sent["line"] and "\r" not in sent["line"]
    assert "line one line two line three" in sent["line"]


# ---------------------------------------------------------------------------
# ssh failure -> raise, never "queued"/"delivered"
# ---------------------------------------------------------------------------

def test_remote_send_ssh_failure_raises_not_queued(isolated_db, monkeypatch):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(
            conn, role="developer", host="winbox",
            worktree=r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__developer__task-remote03",
        )

    def fake_run(cmd, **kwargs):
        raise OSError("ssh: connect to host winbox port 22: Connection refused")

    monkeypatch.setattr(sd.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        sd.send(tid, "status check please")
    assert "queued" not in str(exc_info.value)
    assert "winbox" in str(exc_info.value)


def test_remote_send_nonzero_returncode_raises_not_queued(isolated_db, monkeypatch):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(
            conn, role="developer", host="winbox",
            worktree=r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__developer__task-remote04",
        )

    def fake_run(cmd, **kwargs):
        return _Result(1, stdout="", stderr="Access is denied.")

    monkeypatch.setattr(sd.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        sd.send(tid, "status check please")
    assert "queued" not in str(exc_info.value)
    assert "Access is denied" in str(exc_info.value)


def test_remote_send_readback_mismatch_raises(isolated_db, monkeypatch):
    """The write may have landed but garbled (encoding mishap, partial
    write) -- a readback that doesn't match what was sent must raise, not
    return a false "delivered"."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(
            conn, role="developer", host="winbox",
            worktree=r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__developer__task-remote05",
        )

    def fake_run(cmd, **kwargs):
        return _Result(0, stdout="something else entirely\n")

    monkeypatch.setattr(sd.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        sd.send(tid, "status check please")
    assert "queued" not in str(exc_info.value)
    assert "could not be verified" in str(exc_info.value)


def test_remote_send_no_worktree_yet_raises(isolated_db, monkeypatch):
    """Task delegated to a remote host but the spawn hasn't landed yet --
    worktree column is still NULL."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, role="developer", host="winbox", worktree=None)

    calls = []
    monkeypatch.setattr(sd.subprocess, "run", lambda cmd, **kw: calls.append(cmd))

    with pytest.raises(RuntimeError) as exc_info:
        sd.send(tid, "status check please")
    assert "retry after spawn" in str(exc_info.value)
    assert calls == []  # never even attempted ssh -- no worktree to write into


def test_remote_send_err_no_worktree_marker_raises(isolated_db, monkeypatch):
    """Worktree column IS set but the directory is actually gone on the box
    (removed, box rebuilt, ...) -- the remote script's own Test-Path guard
    reports it via ERR_NO_WORKTREE / exit 2."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(
            conn, role="developer", host="winbox",
            worktree=r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__developer__task-remote06",
        )

    def fake_run(cmd, **kwargs):
        return _Result(2, stdout="ERR_NO_WORKTREE\n")

    monkeypatch.setattr(sd.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        sd.send(tid, "status check please")
    assert "retry after spawn" in str(exc_info.value)


# ---------------------------------------------------------------------------
# host=mac (or unset): unchanged mailbox+tmux path, "queued ..." string.
# ---------------------------------------------------------------------------

def test_mac_task_path_unchanged(isolated_db, isolated_mailbox_root, monkeypatch):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, role="developer", host="mac")

    calls = []
    monkeypatch.setattr(sd, "_wake_tmux_send", lambda s, t: calls.append((s, t)))
    ssh_calls = []
    monkeypatch.setattr(sd.subprocess, "run", lambda cmd, **kw: ssh_calls.append(cmd))

    result = sd.send(tid, "kickoff please")

    assert result.startswith(f"queued to {sd.display_for('developer')} ({tid}):")
    assert "delivered" not in result
    assert ssh_calls == []  # never touches ssh/subprocess for a mac task
    letters = mailbox.peek("developer", tid, root=isolated_mailbox_root)
    assert len(letters) == 1
    assert letters[0]["body"] == "kickoff please"


def test_hostless_task_path_unchanged(isolated_db, isolated_mailbox_root, monkeypatch):
    """host is NULL in the DB (every pre-multihost task, and every project
    still on the default) -- must resolve exactly like host='mac', not be
    misread as a remote task."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, role="developer", host=None)

    ssh_calls = []
    monkeypatch.setattr(sd.subprocess, "run", lambda cmd, **kw: ssh_calls.append(cmd))

    result = sd.send(tid, "kickoff please")

    assert result.startswith("queued to")
    assert ssh_calls == []
