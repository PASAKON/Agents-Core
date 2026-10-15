"""Tests for fail-closed sender identity resolution in tools/agent_transport.py
(task task-cb6ed4a3).

Covers:
  * A bare environment (no CXO_ROLE, WORKER_TASK_ID, CTO_SESSION_ID, or
    CEO_SESSION=1) is refused with PermissionError in current_identity(),
    _resolve_sender_role(), send_to_cxo.send/spawn/main, and
    send_to_worker.send/main.
  * Each legitimate CEO path resolves and delivers as expected:
    - Direct CEO CLI/tool path with explicit CEO_SESSION=1 marker resolves to
      CEO_IDENTITY / "CEO" and delivers letters via send_to_cxo and
      send_to_worker.
    - Console / Secretary relay path (runners.mac_agent.do_relay /
      runners.relay_mcp_server) uses Identity("secretary", "secretary",
      "sompong") without relying on a bare-env current_identity() fallback.
  * Worker (WORKER_TASK_ID), C-level (CXO_ROLE + CXO_SESSION_ID, CTO_SESSION_ID),
    and Project Head (CXO_ROLE=project_head + CXO_SESSION_ID) resolve unchanged.
  * Setting CEO_SESSION=1 inside a worker env (WORKER_TASK_ID present), C-level
    env, or Project Head env does NOT make the caller the CEO.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.ceo_report as ceo_report  # noqa: E402
import lib.db as db_mod  # noqa: E402
import lib.mailbox as mailbox  # noqa: E402
import runners.mac_agent as mac_agent  # noqa: E402
import tools.agent_transport as at  # noqa: E402
import tools.send_to_cxo as sc  # noqa: E402
import tools.send_to_worker as sw  # noqa: E402

_IDENTITY_VARS = (
    "CXO_ROLE",
    "CXO_SESSION_ID",
    "CXO_SESSION",
    "CTO_SESSION_ID",
    "CTO_SESSION",
    "WORKER_TASK_ID",
    "WORKER_ROLE",
    "ORG_PH_LANE",
    "ORG_PH_PROJECT",
    "ORG_PH_OWNER",
    "CEO_SESSION",
    "ORG_CEO_SESSION",
)


@pytest.fixture(autouse=True)
def bare_identity_env(monkeypatch: pytest.MonkeyPatch):
    """Start every test with a completely bare identity environment."""
    for var in _IDENTITY_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate DB, locks, and mailbox root under tmp_path."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    locks = tmp_path / "locks"
    locks.mkdir()
    inbox = tmp_path / "inbox"
    monkeypatch.setattr(at, "LOCKS_DIR", locks)
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", inbox)
    monkeypatch.setattr(at.notify, "info", lambda *a, **k: None)
    monkeypatch.setattr(sc.notify, "info", lambda *a, **k: None)
    return {"db": db_mod, "locks": locks, "inbox": inbox}


def _insert_task(conn, *, role: str = "developer", owner_role: str = "cto",
                 owner_cto: str = "ctosess1") -> str:
    tid = "task-" + uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            depends_on, touches, owner_role, owner_cto, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, "mooniex-agents", role, "in_progress", "t", "d",
         "[]", "[]", owner_role, owner_cto, ts, ts),
    )
    conn.commit()
    return tid


# ---------------------------------------------------------------------------
# 1. Bare environment is refused (fail closed)
# ---------------------------------------------------------------------------

def test_bare_env_refused_in_current_identity():
    with pytest.raises(PermissionError, match="no recognised identity"):
        at.current_identity()


def test_bare_env_refused_in_resolve_sender_role():
    with pytest.raises(PermissionError, match="no recognised identity"):
        at._resolve_sender_role()


def test_bare_env_refused_in_send_to_cxo_send_and_spawn(isolated_env, monkeypatch):
    locks = isolated_env["locks"]
    inbox = isolated_env["inbox"]
    (locks / "cfo-active").write_text("cfosess1")

    with pytest.raises(PermissionError):
        sc.send("cfo", "unauthenticated message")
    assert mailbox.peek("cfo", "cfosess1", root=inbox) == []

    with pytest.raises(PermissionError):
        sc.spawn("cfo", "unauthenticated spawn")

    monkeypatch.setattr(sys, "argv", ["send_to_cxo", "cfo", "unauthenticated cli"])
    assert sc.main() == 4
    assert mailbox.peek("cfo", "cfosess1", root=inbox) == []


def test_bare_env_refused_in_send_to_worker_send_and_main(isolated_env, monkeypatch):
    inbox = isolated_env["inbox"]
    with isolated_env["db"].get_conn() as conn:
        tid = _insert_task(conn, role="developer")

    with pytest.raises(PermissionError):
        sw.send(tid, "unauthenticated worker message")
    assert mailbox.peek("developer", tid, root=inbox) == []

    monkeypatch.setattr(sys, "argv", ["send_to_worker", tid, "unauthenticated cli"])
    assert sw.main() == 4
    assert mailbox.peek("developer", tid, root=inbox) == []


def test_bare_env_rejected_cleanly_in_report_to_ceo():
    res = ceo_report.report_to_ceo(1, "done", "summary")
    assert res.startswith("rejected: report_to_ceo must be called from a C-level session")


@pytest.mark.parametrize("env_vars", [
    {"CXO_ROLE": "cmo"},
    {"CXO_ROLE": "ceo", "CXO_SESSION_ID": "ceosess1"},
    {"CXO_ROLE": "not_a_role", "CXO_SESSION_ID": "sess1"},
    {"WORKER_ROLE": "developer"},
    {"CXO_SESSION_ID": "sess1"},
])
def test_partial_or_invalid_identity_env_refused(monkeypatch, env_vars):
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(PermissionError):
        at.current_identity()


# ---------------------------------------------------------------------------
# 2. Legitimate CEO paths still resolve and deliver as the CEO
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("marker_var", ["CEO_SESSION", "ORG_CEO_SESSION"])
def test_ceo_marker_resolves_as_ceo_and_delivers(isolated_env, monkeypatch, marker_var):
    monkeypatch.setenv(marker_var, "1")
    assert at.current_identity() == at.CEO_IDENTITY
    assert at._resolve_sender_role() == "CEO"

    locks = isolated_env["locks"]
    inbox = isolated_env["inbox"]
    (locks / "cfo-active").write_text("cfosess1")

    res_cxo = sc.send("cfo", "hello cfo")
    assert res_cxo == "queued to CFO #cfosess1: [CEO] : hello cfo"
    cfo_letters = mailbox.peek("cfo", "cfosess1", root=inbox)
    assert len(cfo_letters) == 1
    assert cfo_letters[0]["body"] == "hello cfo"
    assert cfo_letters[0]["from"] == {"role": "ceo", "session_id": "ceo"}

    with isolated_env["db"].get_conn() as conn:
        tid = _insert_task(conn, role="developer")
    monkeypatch.setattr(sw, "_attempt_wake", lambda *a, **k: False)
    res_worker = sw.send(tid, "hello worker")
    assert f"queued to Developer ({tid}): [CEO] : hello worker" in res_worker
    dev_letters = mailbox.peek("developer", tid, root=inbox)
    assert len(dev_letters) == 1
    assert dev_letters[0]["body"] == "hello worker"
    assert dev_letters[0]["from"] == {"role": "ceo", "session_id": "ceo"}


def test_secretary_relay_path_works_on_bare_env(isolated_env, monkeypatch):
    """Console / SomPong relay_to_session and mac_agent.do_relay construct
    Identity('secretary', 'secretary', 'sompong') directly and do not depend on
    CEO_SESSION being set in the daemon environment."""
    locks = isolated_env["locks"]
    inbox = isolated_env["inbox"]
    (locks / "cfo-active").write_text("cfosess1")
    monkeypatch.setattr(mac_agent, "find_session_for_role", lambda r: "cfo-cfosess1")
    monkeypatch.setattr(mac_agent, "attempt_wake", lambda *a, **k: True)

    ok, detail = mac_agent.do_relay("cfo", {"message": "[CEO via Secretary]: check budget"})
    assert ok is True
    assert "delivered to cfo-cfosess1" in detail
    letters = mailbox.peek("cfo", "cfosess1", root=inbox)
    assert len(letters) == 1
    assert letters[0]["from"] == {"role": "secretary", "session_id": "sompong"}


# ---------------------------------------------------------------------------
# 3. Worker, C-level, and Project Head resolve as before
# ---------------------------------------------------------------------------

def test_worker_identity_resolves_as_before(monkeypatch):
    monkeypatch.setenv("WORKER_TASK_ID", "task-1234abcd")
    monkeypatch.setenv("WORKER_ROLE", "security_engineer")
    assert at.current_identity() == at.Identity("dev", "security_engineer", "task-1234abcd")
    assert at._resolve_sender_role() == at.display_for("security_engineer")


def test_clevel_identity_resolves_as_before(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cmo")
    monkeypatch.setenv("CXO_SESSION_ID", "cmosess1")
    assert at.current_identity() == at.Identity("cxo", "cmo", "cmosess1")
    assert at._resolve_sender_role() == "CMO"


def test_standalone_cto_identity_resolves_as_before(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctosess9")
    assert at.current_identity() == at.Identity("cxo", "cto", "ctosess9")
    assert at._resolve_sender_role() == "CTO"


def test_project_head_identity_resolves_as_before(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setenv("CXO_SESSION_ID", "deadbeef")
    monkeypatch.setenv("ORG_PH_LANE", "cto")
    assert at.current_identity() == at.Identity("cxo", "project_head", "deadbeef")
    assert at._resolve_sender_role() == "Project Head (CTO) #deadbeef"

    monkeypatch.delenv("CXO_SESSION_ID")
    with pytest.raises(PermissionError, match="Project Head"):
        at.current_identity()


# ---------------------------------------------------------------------------
# 4. Setting the CEO marker inside a worker, C-level, or PH env never makes it CEO
# ---------------------------------------------------------------------------

def test_ceo_marker_inside_worker_env_does_not_make_it_ceo(isolated_env, monkeypatch):
    with isolated_env["db"].get_conn() as conn:
        tid = _insert_task(conn, role="developer", owner_role="cmo", owner_cto="cmosess1")
    (isolated_env["locks"] / "cto-active").write_text("ctosess1")
    (isolated_env["locks"] / "cmo-active").write_text("cmosess1")

    monkeypatch.setenv("WORKER_TASK_ID", tid)
    monkeypatch.setenv("WORKER_ROLE", "developer")
    monkeypatch.setenv("CEO_SESSION", "1")
    monkeypatch.setenv("ORG_CEO_SESSION", "1")

    ident = at.current_identity()
    assert ident == at.Identity("dev", "developer", tid)
    assert ident != at.CEO_IDENTITY
    assert at._resolve_sender_role() == "Developer"

    # Worker with CEO_SESSION=1 still cannot bypass authorize() to message CTO
    with pytest.raises(PermissionError, match="owner"):
        sc.send("cto", "trying to spoof CEO from worker")
    assert mailbox.peek("cto", "ctosess1", root=isolated_env["inbox"]) == []


def test_ceo_marker_inside_clevel_or_ph_env_does_not_make_it_ceo(monkeypatch):
    monkeypatch.setenv("CEO_SESSION", "1")
    monkeypatch.setenv("CXO_ROLE", "cfo")
    monkeypatch.setenv("CXO_SESSION_ID", "cfosess1")
    assert at.current_identity() == at.Identity("cxo", "cfo", "cfosess1")
    assert at._resolve_sender_role() == "CFO"

    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setenv("CXO_SESSION_ID", "abcd1234")
    monkeypatch.setenv("ORG_PH_LANE", "cfo")
    assert at.current_identity() == at.Identity("cxo", "project_head", "abcd1234")
    assert at._resolve_sender_role() == "Project Head (CFO) #abcd1234"
