"""Identity resolution fails closed (tools/agent_transport.py).

A process whose env names no session used to resolve to the CEO in
current_identity() and _resolve_sender_role(). It is refused now; the CEO's own
command names itself with CEO_MARKER=1, and the mark counts only in an env with
no session key and no Claude Code above it (docs/design/org-restructure-p2.md,
"Next security item").

- a bare env is refused, with or without Claude Code above it;
- the CEO's marked command resolves as the CEO, including in exactly the env a
  Run Inbox card runs with;
- the mark inside a worker, C-level or Project Head env changes nothing, and
  inside an env that only looks like one (an empty WORKER_TASK_ID) it is refused;
- a worker, a C-level and a Project Head resolve as before;
- end to end through send_to_cxo.send: a bare env writes nothing, the marked
  command's letter is from ceo:ceo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.mailbox as mailbox  # noqa: E402
import tools.agent_transport as at  # noqa: E402
import tools.send_to_cxo as sc  # noqa: E402
from tools.agent_transport import CEO_IDENTITY, Identity  # noqa: E402

MARK = at.CEO_MARKER

# What src/run/executor.js (MoonieX-Console) buildRunEnv gives a Run Inbox
# card's command: PATH HOME LANG TERM and the pagers, nothing else.
RUN_CARD_ENV = {"PATH": "/usr/bin:/bin", "HOME": "/root", "LANG": "en_US.UTF-8",
                "TERM": "xterm-256color", "PAGER": "cat", "GIT_PAGER": "cat",
                "SYSTEMD_PAGER": "cat"}


@pytest.fixture(autouse=True)
def bare_env(monkeypatch):
    """No session key, no Claude Code, no mark: a cron job or a fresh shell.
    pytest itself may run under a worker or a Claude Code session."""
    for k in at._SESSION_ENV_KEYS + (MARK,):
        monkeypatch.delenv(k, raising=False)


def _refused(match="no org identity"):
    with pytest.raises(PermissionError, match=match):
        at.current_identity()
    with pytest.raises(PermissionError, match=match):
        at._resolve_sender_role()


# --- a bare env ------------------------------------------------------------------

def test_bare_env_is_refused():
    _refused()


def test_bare_env_under_claude_code_is_refused(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    _refused()


@pytest.mark.parametrize("value", ["", "0", "true", "yes", "ceo", " 2 "])
def test_mark_must_be_exactly_one(monkeypatch, value):
    monkeypatch.setenv(MARK, value)
    _refused()


@pytest.mark.parametrize("role", ["", "dev", "ceo", "secretary", "nobody"])
def test_cxo_role_that_names_no_session_is_refused(monkeypatch, role):
    monkeypatch.setenv("CXO_ROLE", role)
    with pytest.raises(PermissionError, match="cannot send"):
        at.current_identity()


def test_c_level_role_with_no_session_id_is_refused(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cto")
    with pytest.raises(PermissionError, match="no CXO_SESSION_ID"):
        at.current_identity()


# --- the CEO's marked command ----------------------------------------------------

def test_marked_command_is_the_ceo(monkeypatch):
    monkeypatch.setenv(MARK, "1")
    assert at.current_identity() == CEO_IDENTITY
    assert at.current_identity().label() == "CEO"
    assert at._resolve_sender_role() == "CEO"


def test_run_card_env_with_the_mark_is_the_ceo():
    assert at._is_ceo_env({**RUN_CARD_ENV, MARK: "1"})
    assert not at._is_ceo_env(RUN_CARD_ENV)


@pytest.mark.parametrize("key", at._SESSION_ENV_KEYS)
@pytest.mark.parametrize("value", ["", "x"])
def test_mark_never_counts_next_to_a_session_key(key, value):
    assert not at._is_ceo_env({**RUN_CARD_ENV, MARK: "1", key: value})


def test_mark_under_claude_code_is_refused(monkeypatch):
    monkeypatch.setenv(MARK, "1")
    monkeypatch.setenv("CLAUDECODE", "1")
    _refused()


# --- the mark inside a session's env changes nothing -----------------------------

def test_mark_in_a_worker_env_is_the_worker(monkeypatch):
    monkeypatch.setenv(MARK, "1")
    monkeypatch.setenv("WORKER_TASK_ID", "task-abc12345")
    monkeypatch.setenv("WORKER_ROLE", "developer")
    assert at.current_identity() == Identity("dev", "developer", "task-abc12345")
    assert at._resolve_sender_role() == "developer#task-abc12345"


@pytest.mark.parametrize("env", [{"WORKER_TASK_ID": ""}, {"WORKER_ROLE": "developer"},
                                 {"WORKER_TASK_ID": "", "WORKER_ROLE": ""}])
def test_mark_in_a_half_worker_env_is_refused_not_the_ceo(monkeypatch, env):
    monkeypatch.setenv(MARK, "1")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    _refused()


def test_mark_in_a_c_level_env_is_the_c_level(monkeypatch):
    monkeypatch.setenv(MARK, "1")
    monkeypatch.setenv("CXO_ROLE", "cmo")
    monkeypatch.setenv("CXO_SESSION_ID", "c0ffee01")
    assert at.current_identity() == Identity("cxo", "cmo", "c0ffee01")
    assert at._resolve_sender_role() == "CMO"


def test_mark_in_a_c_level_env_without_session_id_is_refused(monkeypatch):
    monkeypatch.setenv(MARK, "1")
    monkeypatch.setenv("CXO_ROLE", "cto")
    with pytest.raises(PermissionError, match="no CXO_SESSION_ID"):
        at.current_identity()


def test_mark_in_a_project_head_env_is_the_project_head(monkeypatch):
    monkeypatch.setenv(MARK, "1")
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setenv("CXO_SESSION_ID", "ab12cd34")
    monkeypatch.setenv("ORG_PH_LANE", "cto")
    assert at.current_identity() == Identity("cxo", "project_head", "ab12cd34")


def test_mark_in_a_project_head_env_without_session_id_is_refused(monkeypatch):
    monkeypatch.setenv(MARK, "1")
    monkeypatch.setenv("CXO_ROLE", "project_head")
    with pytest.raises(PermissionError, match="no CXO_SESSION_ID"):
        at.current_identity()


# --- every other identity resolves as before -------------------------------------

def test_worker_resolves_as_before(monkeypatch):
    monkeypatch.setenv("WORKER_TASK_ID", "task-abc12345")
    monkeypatch.setenv("WORKER_ROLE", "tester")
    assert at.current_identity() == Identity("dev", "tester", "task-abc12345")
    monkeypatch.delenv("WORKER_ROLE")
    assert at.current_identity() == Identity("dev", "dev", "task-abc12345")


def test_c_level_resolves_as_before(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cfo")
    monkeypatch.setenv("CXO_SESSION_ID", "f00d0001")
    assert at.current_identity() == Identity("cxo", "cfo", "f00d0001")
    assert at._resolve_sender_role() == "CFO"


def test_cto_claude_session_resolves_as_before(monkeypatch):
    # scripts/cto-claude.sh exports CXO_ROLE=cto and CTO_SESSION_ID
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CTO_SESSION_ID", "deadbeef")
    assert at.current_identity() == Identity("cxo", "cto", "deadbeef")
    monkeypatch.delenv("CXO_ROLE")  # an older launch with CTO_SESSION_ID only
    assert at.current_identity() == Identity("cxo", "cto", "deadbeef")
    assert at._resolve_sender_role() == "CTO"


def test_project_head_resolves_as_before(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setenv("CXO_SESSION_ID", "ab12cd34")
    monkeypatch.setenv("ORG_PH_LANE", "cmo")
    assert at.current_identity() == Identity("cxo", "project_head", "ab12cd34")
    assert at._resolve_sender_role() == "Project Head (CMO) #ab12cd34"


def test_c_level_wins_over_a_worker_key_as_before(monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", "c0ffee01")
    monkeypatch.setenv("WORKER_TASK_ID", "task-abc12345")
    assert at.current_identity() == Identity("cxo", "cto", "c0ffee01")


# --- end to end through send_to_cxo.send ---------------------------------------

@pytest.fixture()
def cto_box(tmp_path, monkeypatch):
    locks = tmp_path / "locks"
    locks.mkdir()
    (locks / "cto-active").write_text("c0ffee01")
    inbox = tmp_path / "inbox"
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", inbox)
    monkeypatch.setattr(sc, "_attempt_wake", lambda *a, **k: False)
    return inbox


def test_bare_env_send_writes_nothing(cto_box):
    with pytest.raises(PermissionError, match="no org identity"):
        sc.send("cto", "hello")
    assert not cto_box.exists() or not any(cto_box.iterdir())


def test_bare_env_send_cli_exits_4(cto_box, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["send_to_cxo", "cto", "hello"])
    assert sc.main() == 4
    assert "no org identity" in capsys.readouterr().err
    assert not cto_box.exists() or not any(cto_box.iterdir())


def test_marked_command_send_is_from_the_ceo(cto_box, monkeypatch):
    monkeypatch.setenv(MARK, "1")
    out = sc.send("cto", "hello")
    assert out.startswith("queued to CTO #c0ffee01: [CEO] : hello")
    (letter,) = mailbox.peek("cto", "c0ffee01")
    assert letter["from"] == {"role": "ceo", "session_id": "ceo"}
