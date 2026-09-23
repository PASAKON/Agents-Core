"""tools/work_watch.py — Work/ watcher (Work/RULES.md rules 7-8, ADR 0030
§D, task-dbe47b9b).

Every test relies on conftest.py's autouse `_isolate_workdir_root` fixture
(pins `tools.workdir._default_root()` to a per-test tmp_path) so nothing
here ever touches the real ~/MoonieXHQ/Work — matching tests/test_workdir.py
and tests/test_delegate_disk_floor.py's own convention. Seams: `now=` (time),
`session_cap.live_sessions` monkeypatched (live sessions), `send_to_cto.send`
monkeypatched (never a real mailbox write attempted here), and
`_add_lungnote_todo` monkeypatched (never a real LungNote MCP call/spawn).

Run via:  pytest tests/test_work_watch.py
(collected by the default `pytest` run — pytest.ini testpaths includes
`tests` alongside `scripts lib`.)
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.session_name as session_name  # noqa: E402
import tools.work_watch as work_watch  # noqa: E402
import tools.workdir as workdir  # noqa: E402


@pytest.fixture()
def env(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


def _ts(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat(timespec="seconds")


def _orphan_task(db_mod_, *, status: str = "done", hours_ago: float = 30,
                 owner_cto: str | None = "sess1", owner_role: str = "cto",
                 pid: int | None = None, host: str | None = None) -> str:
    tid = db_mod_.create_task(project="mooniex-agents", role="developer",
                              title="w", description="d", owner_cto=owner_cto,
                              owner_role=owner_role, host=host)
    if status != "pending":
        db_mod_.update_status(tid, status, actor="test")
    if pid is not None:
        db_mod_.set_fields(tid, actor="test", pid=pid)
    import sqlite3
    conn = sqlite3.connect(str(db_mod_.DB_PATH))
    conn.execute("UPDATE tasks SET updated_at=? WHERE id=?", (_ts(hours_ago), tid))
    conn.commit()
    conn.close()
    workdir.create(tid)  # under the conftest-pinned tmp Work root
    (workdir.folder_path(tid) / "in" / "clip.mp4").write_bytes(b"x" * 100)
    return tid


def _state_path(tmp_path) -> Path:
    return tmp_path / "work_watch_state.json"


def _stub_lungnote(monkeypatch, calls: list) -> None:
    monkeypatch.setattr(work_watch, "_add_lungnote_todo",
                        lambda text, due_at, **k: calls.append((text, due_at)) or True)


# ---------------------------------------------------------------------------
# Owner alive -> alert; owner dead -> LungNote.
# ---------------------------------------------------------------------------

def test_alert_when_owner_alive(env, monkeypatch, tmp_path):
    monkeypatch.setattr(work_watch, "_disk_at_risk", lambda: True)
    tid = _orphan_task(env, owner_cto="sess1", owner_role="cto")
    basename = session_name.lock_basename("cto", "sess1")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [basename])
    sent = []
    monkeypatch.setattr(work_watch.send_to_cto, "send",
                        lambda *a, **k: sent.append((a, k)) or True)
    lungnote_calls: list = []
    _stub_lungnote(monkeypatch, lungnote_calls)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert result["alerted"] == [tid]
    assert lungnote_calls == []
    assert sent[0][0][0] == tid  # from_id == task_id
    assert "100" in sent[0][0][1]  # bytes mentioned


def test_lungnote_when_owner_dead(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, owner_cto="sess2", owner_role="cto")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [])
    sent = []
    monkeypatch.setattr(work_watch.send_to_cto, "send",
                        lambda *a, **k: sent.append(a) or True)
    lungnote_calls: list = []
    _stub_lungnote(monkeypatch, lungnote_calls)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert result["lungnote_filed"] == [tid]
    assert sent == []
    assert len(lungnote_calls) == 1
    text, due_at = lungnote_calls[0]
    assert "[CRITICAL]" in text
    assert tid in text
    assert due_at.startswith(datetime.now(timezone.utc).date().isoformat())


def test_ownerless_task_goes_to_lungnote(env, monkeypatch, tmp_path):
    """No owner_cto at all -> nobody to alert -> straight to LungNote."""
    tid = _orphan_task(env, owner_cto=None, owner_role=None)
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: ["cto-sess1"])
    lungnote_calls: list = []
    _stub_lungnote(monkeypatch, lungnote_calls)
    monkeypatch.setattr(work_watch.send_to_cto, "send", lambda *a, **k: True)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert result["lungnote_filed"] == [tid]


# ---------------------------------------------------------------------------
# 24h rate limit + permanent LungNote dedupe.
# ---------------------------------------------------------------------------

def test_rate_limited_within_24h(env, monkeypatch, tmp_path):
    monkeypatch.setattr(work_watch, "_disk_at_risk", lambda: True)
    tid = _orphan_task(env, owner_cto="sess1", owner_role="cto")
    basename = session_name.lock_basename("cto", "sess1")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [basename])
    sent = []
    monkeypatch.setattr(work_watch.send_to_cto, "send",
                        lambda *a, **k: sent.append(1) or True)
    _stub_lungnote(monkeypatch, [])
    sp = _state_path(tmp_path)
    now0 = datetime.now(timezone.utc)

    work_watch.watch(state_path=sp, now=now0)
    work_watch.watch(state_path=sp, now=now0 + timedelta(hours=1))  # < 24h later

    assert len(sent) == 1  # second tick skipped entirely


def test_never_alerts_twice_for_the_same_folder(env, monkeypatch, tmp_path):
    """CEO 2026-09-23: one letter per folder, ever — no daily repeats."""
    monkeypatch.setattr(work_watch, "_disk_at_risk", lambda: True)
    tid = _orphan_task(env, owner_cto="sess1", owner_role="cto")
    basename = session_name.lock_basename("cto", "sess1")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [basename])
    sent = []
    monkeypatch.setattr(work_watch.send_to_cto, "send",
                        lambda *a, **k: sent.append(1) or True)
    _stub_lungnote(monkeypatch, [])
    sp = _state_path(tmp_path)
    now0 = datetime.now(timezone.utc)

    work_watch.watch(state_path=sp, now=now0)
    work_watch.watch(state_path=sp, now=now0 + timedelta(hours=25))

    assert len(sent) == 1  # rechecked past 24h, but never a second letter


def test_lungnote_never_filed_twice_for_same_folder(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, owner_cto="sess2", owner_role="cto")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [])
    monkeypatch.setattr(work_watch.send_to_cto, "send", lambda *a, **k: True)
    lungnote_calls: list = []
    _stub_lungnote(monkeypatch, lungnote_calls)
    sp = _state_path(tmp_path)
    now0 = datetime.now(timezone.utc)

    work_watch.watch(state_path=sp, now=now0)
    # Owner still dead, well past the 24h rate limit -- must NOT file a
    # second to-do for the same folder.
    work_watch.watch(state_path=sp, now=now0 + timedelta(days=3))

    assert len(lungnote_calls) == 1


# ---------------------------------------------------------------------------
# in_progress + dead pid (never covered by workdir.orphans() alone).
# ---------------------------------------------------------------------------

def test_in_progress_dead_pid_is_a_candidate(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, status="in_progress", hours_ago=1,
                       owner_cto="sess2", pid=424242)
    monkeypatch.setattr(work_watch, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [])
    lungnote_calls: list = []
    _stub_lungnote(monkeypatch, lungnote_calls)
    monkeypatch.setattr(work_watch.send_to_cto, "send", lambda *a, **k: True)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert result["lungnote_filed"] == [tid]


def test_in_progress_live_pid_is_not_a_candidate(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, status="in_progress", hours_ago=1,
                       owner_cto="sess2", pid=424242)
    monkeypatch.setattr(work_watch, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [])
    lungnote_calls: list = []
    _stub_lungnote(monkeypatch, lungnote_calls)
    monkeypatch.setattr(work_watch.send_to_cto, "send", lambda *a, **k: True)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert result["lungnote_filed"] == []
    assert result["alerted"] == []


# ---------------------------------------------------------------------------
# Green listing after abandon_days -- never deletes.
# ---------------------------------------------------------------------------

def test_green_listed_after_abandon_days(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, hours_ago=15 * 24, owner_cto="sess2")  # > 14d default
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [])
    _stub_lungnote(monkeypatch, [])
    monkeypatch.setattr(work_watch.send_to_cto, "send", lambda *a, **k: True)
    folder = workdir.folder_path(tid)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert tid in result["green"]
    assert folder.is_dir()  # never deleted


def test_not_green_before_abandon_days(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, hours_ago=30, owner_cto="sess2")  # 30h: flagged, not Green
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [])
    _stub_lungnote(monkeypatch, [])
    monkeypatch.setattr(work_watch.send_to_cto, "send", lambda *a, **k: True)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert tid not in result["green"]


# ---------------------------------------------------------------------------
# Never deletes anything -- across every outcome above the folder persists.
# ---------------------------------------------------------------------------

def test_watch_never_deletes_the_folder(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, owner_cto="sess2")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [])
    _stub_lungnote(monkeypatch, [])
    monkeypatch.setattr(work_watch.send_to_cto, "send", lambda *a, **k: True)
    folder = workdir.folder_path(tid)
    assert folder.is_dir()

    work_watch.watch(state_path=_state_path(tmp_path))

    assert folder.is_dir()
    assert (folder / "in" / "clip.mp4").exists()


def test_no_letter_when_owner_alive_and_nothing_at_risk(env, monkeypatch, tmp_path):
    """CEO 2026-09-23: a permanent watchdog letter only when critical/risky.
    Healthy disk + small folder -> recorded, no letter, no LungNote."""
    tid = _orphan_task(env, owner_cto="sess1", owner_role="cto")
    basename = session_name.lock_basename("cto", "sess1")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [basename])
    monkeypatch.setattr(work_watch, "_disk_at_risk", lambda: False)
    sent = []
    monkeypatch.setattr(work_watch.send_to_cto, "send",
                        lambda *a, **k: sent.append(1) or True)
    lungnote_calls: list = []
    _stub_lungnote(monkeypatch, lungnote_calls)

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert sent == [] and result["alerted"] == [] and lungnote_calls == []


def test_large_folder_is_a_risk_even_on_a_healthy_disk(env, monkeypatch, tmp_path):
    tid = _orphan_task(env, owner_cto="sess1", owner_role="cto")
    basename = session_name.lock_basename("cto", "sess1")
    monkeypatch.setattr(work_watch.session_cap, "live_sessions", lambda: [basename])
    monkeypatch.setattr(work_watch, "_disk_at_risk", lambda: False)
    monkeypatch.setattr(work_watch, "RISK_FOLDER_BYTES", 50)  # folder holds 100 bytes
    sent = []
    monkeypatch.setattr(work_watch.send_to_cto, "send",
                        lambda *a, **k: sent.append(1) or True)
    _stub_lungnote(monkeypatch, [])

    result = work_watch.watch(state_path=_state_path(tmp_path))

    assert result["alerted"] == [tid] and len(sent) == 1
