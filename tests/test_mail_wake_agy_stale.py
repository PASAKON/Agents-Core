"""Stale AGY takeover marker in state/agy-sessions/<box>.json must not steal wakes
from a live Claude pane (CEO bug 18 Nov 2026, Q-20261118-0505-4535).

Run: /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_mail_wake_agy_stale.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import claude_quota, mailbox  # noqa: E402
from tools import agy_card_run, mail_wake, send_to_cxo  # noqa: E402

CONV_UUID = "aced3034-2643-403e-ac26-42f1884593d6"


@pytest.fixture
def env_setup(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    sdir = tmp_path / "agy-sessions"
    sdir.mkdir()
    monkeypatch.setattr(mailbox, "INBOX_ROOT", inbox)
    monkeypatch.setattr(mail_wake, "AGY_SESSIONS_DIR", sdir)
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    monkeypatch.setattr(claude_quota, "HISTORY", tmp_path / "no-quota-history.jsonl")

    agy_runs: list[str] = []
    monkeypatch.setattr(mail_wake, "_spawn_agy_runner", lambda box: agy_runs.append(box))

    state = type("State", (), {})()
    state.inbox = inbox
    state.sdir = sdir
    state.agy_runs = agy_runs
    return state


def _deliver_letter(inbox: Path, box: str) -> Path:
    role, _, sid = box.partition("-")
    return mailbox.send(role, sid, "Q-20261118-0505-4535 answered: Proceed", "run-inbox", "hub", root=inbox)


def _write_marker(sdir: Path, box: str, *, mode: int = 0o600) -> Path:
    role, _, sid = box.partition("-")
    path = sdir / f"{box}.json"
    record = {
        "box": box,
        "role": role,
        "session_id": sid,
        "conversation_id": CONV_UUID,
        "host": "contabo",
        "cwd": str(ROOT),
        "model": "claude-opus-5-5-high",
        "mode": "accept-edits",
        "parked": False,
        "created_at": "2026-11-15T21:44:00Z",
        "updated_at": "2026-11-15T21:44:00Z",
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    path.chmod(mode)
    return path


def test_marker_with_live_pane_wakes_pane_and_parks_marker(env_setup, monkeypatch):
    """(a) marker + live pane -> pane woken, marker parked (atomic write, 0600, parked_note)."""
    wake_calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        send_to_cxo,
        "attempt_wake",
        lambda role, sid, label: wake_calls.append((role, sid, label)) or True,
    )

    for box, role, sid, init_mode in (
        ("cto-fresh", "cto", "fresh", 0o644),
        ("project_head-b2ff34d1", "project_head", "b2ff34d1", 0o600),
    ):
        marker = _write_marker(env_setup.sdir, box, mode=init_mode)
        _deliver_letter(env_setup.inbox, box)

        out = mail_wake.wake(box, "ASK-CEO")
        assert out == {"box": box, "woke": True, "reason": "woke"}
        assert wake_calls[-1] == (role, sid, "ASK-CEO")
        assert env_setup.agy_runs == []

        assert marker.is_file() and not marker.is_symlink()
        assert (marker.stat().st_mode & 0o777) == 0o600
        data = json.loads(marker.read_text(encoding="utf-8"))
        assert data["parked"] is True
        assert isinstance(data.get("parked_note"), str) and data["parked_note"].strip()
        assert data["conversation_id"] == CONV_UUID
        assert agy_card_run.load_session(box, sessions_dir=env_setup.sdir) is None


def test_marker_with_no_pane_runs_agy_as_today(env_setup, monkeypatch):
    """(b) marker + no pane -> live Claude pane tried first, then AGY runs as today."""
    wake_calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        send_to_cxo,
        "attempt_wake",
        lambda role, sid, label: wake_calls.append((role, sid, label)) or False,
    )

    for box, role, sid in (
        ("cto-fresh", "cto", "fresh"),
        ("project_head-b2ff34d1", "project_head", "b2ff34d1"),
    ):
        marker = _write_marker(env_setup.sdir, box)
        _deliver_letter(env_setup.inbox, box)

        out = mail_wake.wake(box)
        assert wake_calls[-1] == (role, sid, "RUN-INBOX")
        assert out == {"box": box, "woke": True, "reason": "woke AGY session"}
        assert env_setup.agy_runs[-1] == box

        data = json.loads(marker.read_text(encoding="utf-8"))
        assert data["parked"] is False
        assert agy_card_run.load_session(box, sessions_dir=env_setup.sdir) is not None


def test_no_marker_unchanged(env_setup, monkeypatch):
    """(c) no marker -> unchanged (both with no marker file and after a marker was parked)."""
    wake_calls: list[tuple[str, str, str]] = []
    pane_live = True
    monkeypatch.setattr(
        send_to_cxo,
        "attempt_wake",
        lambda role, sid, label: wake_calls.append((role, sid, label)) or pane_live,
    )

    # 1. No marker file in sessions_dir at all: live pane wakes normally, no marker created.
    _deliver_letter(env_setup.inbox, "cto-fresh")
    assert mail_wake.wake("cto-fresh") == {"box": "cto-fresh", "woke": True, "reason": "woke"}
    assert wake_calls == [("cto", "fresh", "RUN-INBOX")]
    assert env_setup.agy_runs == []
    assert not (env_setup.sdir / "cto-fresh.json").exists()

    # 2. No marker file and no live pane: reports no live session reached, no marker created.
    pane_live = False
    assert mail_wake.wake("cto-fresh") == {
        "box": "cto-fresh",
        "woke": False,
        "reason": "no live session reached",
    }
    assert env_setup.agy_runs == []
    assert not (env_setup.sdir / "cto-fresh.json").exists()

    # 3. Once a stale marker is parked by a live wake, no active marker remains:
    # a later wake with no live pane stays "no live session reached" instead of running AGY.
    _write_marker(env_setup.sdir, "cto-fresh")
    pane_live = True
    assert mail_wake.wake("cto-fresh") == {"box": "cto-fresh", "woke": True, "reason": "woke"}
    pane_live = False
    assert mail_wake.wake("cto-fresh") == {
        "box": "cto-fresh",
        "woke": False,
        "reason": "no live session reached",
    }
    assert env_setup.agy_runs == []


def test_marker_with_live_pane_while_claude_spent_keeps_agy_takeover(env_setup, monkeypatch):
    """(d) Claude spent + marker: the takeover is live, so AGY gets the wake first,
    the Claude pane is not tried and the marker stays unparked."""
    inbox, sdir, agy_runs = env_setup.inbox, env_setup.sdir, env_setup.agy_runs
    box = "cto-fresh"
    _deliver_letter(inbox, box)
    marker = _write_marker(sdir, box)
    calls = []
    monkeypatch.setattr(send_to_cxo, "attempt_wake", lambda role, sid, label: calls.append(sid) or True)
    monkeypatch.setattr(mail_wake, "_claude_spent", lambda: True)
    res = mail_wake.wake(box)
    assert res["reason"] == mail_wake.AGY_REASON
    assert agy_runs == [box]
    assert calls == []
    assert json.loads(marker.read_text(encoding="utf-8"))["parked"] is False
