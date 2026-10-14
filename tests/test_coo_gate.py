"""SomPong's research workers (CEO card Q-20261013-1948-4a33): the role allowlist at each of its
enforcement points, the COO gate's ops and uid check, the dispatcher's holds, the research box,
and the coo branch of the MCP config.

SQLite only (tests/test_db_hosts_letters.py convention): lib.db points at a tmp_path ledger. The
hub-side trigger is checked by reading deploy/coo-gate/org_coo_role.sql; its live proof is that
file's own section 6, which ran on the hub.

Run:  .venv/bin/python -m pytest tests/test_coo_gate.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from lib import coo_policy
from lib import db as db_mod
from runners import coo_dispatch, coo_gate, coo_mcp_server, coo_worker
from scripts.lib import cxo_mcp_config

ROOT = Path(__file__).resolve().parents[1]
SID = "cootest1"


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "contabo")
    db_mod.register_cxo_session("coo", SID, "contabo")


def _events(tid: str, kind: str) -> list[dict]:
    with db_mod.get_conn() as conn:
        rows = conn.execute("SELECT payload FROM events WHERE task_id=? AND kind=?", (tid, kind)).fetchall()
    return [json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"] for r in rows]


def _create(role="researcher", sid=SID) -> dict:
    return coo_gate.handle({"op": "create_task", "session_id": sid, "role": role,
                            "title": "t", "description": "brief"}, 994)


# --------------------------------------------------------------------------- policy, 3 places

@pytest.mark.parametrize("role", coo_policy.COO_WORKER_ROLES)
def test_policy_passes_the_three_roles(role):
    coo_policy.check_role("coo", role)


@pytest.mark.parametrize("role", ["developer", "devops_engineer", "security_engineer", "tester", "", "Researcher"])
def test_policy_refuses_every_other_role_for_coo(role):
    with pytest.raises(coo_policy.CooRoleRefused, match="Q-20261013-1948-4a33"):
        coo_policy.check_role("coo", role)


def test_policy_leaves_other_owners_alone():
    coo_policy.check_role("cto", "developer")
    coo_policy.check_role(None, "developer")


def test_db_create_task_refuses_a_coo_developer():
    """CTO_Gate_MergeChecklist §4b: the entry point every Python path shares has the guard."""
    with pytest.raises(coo_policy.CooRoleRefused):
        db_mod.create_task("mooniex-agents", "developer", "t", "d", owner_cto=SID, owner_role="coo")
    with db_mod.get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"] == 0


def test_sql_trigger_lists_exactly_the_policy_roles():
    sql = (ROOT / "deploy" / "coo-gate" / "org_coo_role.sql").read_text()
    m = re.search(r"NEW\.role NOT IN \(([^)]*)\)", sql)
    assert m, "the tasks guard's role list moved: update this test with it"
    assert tuple(re.findall(r"'([a-z_]+)'", m.group(1))) == coo_policy.COO_WORKER_ROLES
    assert "PASSWORD '" not in sql.upper()   # never a literal in this file


# --------------------------------------------------------------------------- gate ops

def test_gate_creates_a_coo_researcher_task():
    out = _create()
    assert out["ok"], out
    task = db_mod.get_task(out["task_id"])
    assert (task["owner_role"], task["owner_cto"], task["role"], task["status"]) == ("coo", SID, "researcher", "pending")
    assert task["runner"] in (None, "")   # coo_worker routes it, outside runners first


def test_gate_refuses_a_code_role_before_writing():
    out = _create("developer")
    assert not out["ok"] and "refused" in out["error"]
    with db_mod.get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"] == 0


def test_gate_refuses_a_session_that_is_not_coo():
    db_mod.register_cxo_session("cto", "ctoabc12", "contabo")
    out = _create(sid="ctoabc12")
    assert not out["ok"] and "not a coo session" in out["error"]


def test_gate_delegate_files_a_request_once_and_only_for_pending():
    tid = _create()["task_id"]
    out = coo_gate.handle({"op": "delegate_task", "task_id": tid}, 994)
    assert out["ok"] and out["queued"]
    assert _events(tid, "coo_delegate_request") == [{"uid": 994}]
    assert db_mod.get_task(tid)["status"] == "pending"          # the gate never changes status
    db_mod.update_status(tid, "in_progress", actor="test", force=True)
    again = coo_gate.handle({"op": "delegate_task", "task_id": tid}, 994)
    assert not again["ok"] and "only a pending task" in again["error"]


def test_gate_hides_tasks_that_are_not_coo():
    other = db_mod.create_task("mooniex-agents", "developer", "t", "d", owner_cto="ctoabc12", owner_role="cto")
    for op in ("get_task", "delegate_task", "close_task"):
        out = coo_gate.handle({"op": op, "task_id": other}, 994)
        assert out == {"ok": False, "error": f"{other} is not a coo task"}


def test_gate_close_takes_a_verdict():
    tid = _create()["task_id"]
    db_mod.update_status(tid, "review", actor="test", force=True)
    bad = coo_gate.handle({"op": "close_task", "task_id": tid, "result": "maybe"}, 994)
    assert not bad["ok"]
    ok = coo_gate.handle({"op": "close_task", "task_id": tid, "result": "fail", "why": " off topic "}, 994)
    assert ok["ok"]
    assert _events(tid, "coo_close_request") == [{"uid": 994, "result": "fail", "why": "off topic"}]


@pytest.mark.parametrize("req", [None, [], {"op": 3}, {"op": "drop_table"},
                                 {"op": "list_tasks", "limit": 999},
                                 {"op": "get_task", "task_id": "../etc"}])
def test_gate_bad_requests_get_an_answer_not_an_exception(req):
    assert coo_gate.handle(req, 994)["ok"] is False


def test_gate_answers_only_allowed_uids():
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with a, b:
        b.sendall(b'{"op": "ping"}\n')
        coo_gate.serve_one(a, frozenset({os.getuid() + 12345}))
        assert json.loads(b.recv(4096))["error"] == "this uid may not use the COO gate"
    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    with a, b:
        b.sendall(b'{"op": "ping"}\n')
        coo_gate.serve_one(a, frozenset({os.getuid()}))
        assert json.loads(b.recv(4096))["ok"] is True


def test_allowed_uids_always_include_root_and_reject_junk():
    assert coo_gate.allowed_uids({"COO_GATE_ALLOWED_UIDS": "994"}) == frozenset({0, 994})
    with pytest.raises(SystemExit):
        coo_gate.allowed_uids({"COO_GATE_ALLOWED_UIDS": "sompong"})


# --------------------------------------------------------------------------- dispatcher

def _delegated(role: str) -> str:
    tid = _create(role)["task_id"]
    assert coo_gate.handle({"op": "delegate_task", "task_id": tid}, 994)["ok"]
    return tid


@pytest.fixture
def _host_ok(monkeypatch):
    started = []
    monkeypatch.setattr(coo_dispatch, "mem_available_mb", lambda *a: 4096)
    monkeypatch.setattr(coo_dispatch, "tmux_server_up", lambda: True)
    monkeypatch.setattr(coo_dispatch, "start_researcher", lambda tid: started.append(tid) or True)
    monkeypatch.setattr(coo_dispatch, "start_root_role", lambda tid: started.append(tid) or True)
    return started


def test_dispatch_holds_shell_roles_until_they_have_a_box(_host_ok):
    tid = _delegated("data_analyst")
    coo_dispatch.dispatch_once({})
    coo_dispatch.dispatch_once({})
    assert _host_ok == []
    held = _events(tid, "coo_dispatch_held")
    assert len(held) == 1 and "Q-20261013-2111-5ff5" in held[0]["why"]


def test_dispatch_starts_a_researcher(_host_ok):
    tid = _delegated("researcher")
    coo_dispatch.dispatch_once({})
    assert _host_ok == [tid]


def test_dispatch_cancels_a_code_role_that_got_past_the_gate(_host_ok):
    tid = _delegated("researcher")
    with db_mod.get_conn() as conn:       # as if a row reached the ledger some other way
        conn.execute("UPDATE tasks SET role='developer' WHERE id=?", (tid,))
    coo_dispatch.dispatch_once({})
    assert _host_ok == [] and db_mod.get_task(tid)["status"] == "cancelled"


def test_dispatch_waits_for_memory_and_one_worker(monkeypatch, _host_ok):
    _delegated("researcher")
    monkeypatch.setattr(coo_dispatch, "mem_available_mb", lambda *a: 900)
    coo_dispatch.dispatch_once({})
    assert _host_ok == []
    monkeypatch.setattr(coo_dispatch, "mem_available_mb", lambda *a: 4096)
    busy = _create()["task_id"]
    db_mod.update_status(busy, "in_progress", actor="test", force=True)
    coo_dispatch.dispatch_once({})
    assert _host_ok == []


def test_mem_available_parses_meminfo():
    assert coo_dispatch.mem_available_mb("MemTotal: 8000000 kB\nMemAvailable:    2097152 kB\n") == 2048


# --------------------------------------------------------------------------- research box

def test_box_drops_env_caps_and_maps_root_away(tmp_path):
    argv = coo_worker.box_argv("codex", ["codex", "exec", "x"], tmp_path, read_roots=())
    for flag in ("--clearenv", "--unshare-user", "--die-with-parent", "--new-session"):
        assert flag in argv
    assert argv[argv.index("--cap-drop") + 1] == "ALL"
    assert argv[argv.index("--uid") + 1] == str(coo_worker.BOX_UID)
    set_vars = {argv[i + 1] for i, a in enumerate(argv) if a == "--setenv"}
    assert not set_vars & {"ORG_DB_URL", "INFISICAL_TOKEN", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"}
    assert argv[-3:] == ["codex", "exec", "x"]
    assert "/etc/infisical" not in " ".join(argv)


def test_claude_runner_gets_no_shell_no_edit_and_no_mcp():
    inner = coo_worker.runner_inner(coo_worker.Candidate("claude", "claude-sonnet-5-5"), "p")
    allowed = inner[inner.index("--allowed-tools") + 1]
    assert set(allowed.split(",")) <= {"Read", "Grep", "Glob", "WebSearch", "WebFetch"}
    assert "Bash" in inner[inner.index("--disallowed-tools") + 1]
    assert json.loads(inner[inner.index("--mcp-config") + 1]) == {"mcpServers": {}}


def test_codex_runner_searches_read_only():
    inner = coo_worker.runner_inner(coo_worker.Candidate("codex", None), "p")
    assert inner[:2] == ["codex", "--search"]
    assert inner[inner.index("-s") + 1] == "read-only"


def test_agy_box_settings_read_and_fetch_only():
    rules = json.loads(coo_worker.AGY_SETTINGS.read_text())["permissions"]
    assert all(r.startswith(("read_file(", "read_url(")) for r in rules["allow"])
    assert "command(*)" in rules["deny"]


def test_secret_hits_catch_a_dsn_and_pass_prose():
    assert coo_worker.secret_hits("see postgresql://org_coo:hunter2hunter2@db.example:5432/org")
    assert coo_worker.secret_hits("# Answer\nPostgreSQL 18 shipped on 2025-09-25.") == []


def test_is_report_rejects_a_status_line():
    assert not coo_worker.is_report("Waiting for the research subagent to complete its inspection.")
    assert coo_worker.is_report("# PostgreSQL 18\n## Findings\n" + "x" * 250)


@pytest.mark.skipif(os.geteuid() != 0, reason="needs root to chown a dir to an unmapped uid")
def test_box_cannot_reach_a_dir_closed_to_others(tmp_path):
    closed = tmp_path / "closed"
    (closed / "inner").mkdir(parents=True)
    os.chown(closed, 54321, 54321)
    closed.chmod(0o700)
    assert not coo_worker.box_can_reach(closed / "inner" / "f")
    closed.chmod(0o711)
    assert coo_worker.box_can_reach(closed / "inner" / "f")


def test_gate_unit_makes_the_socket_dir_its_own():
    # systemd chowns a RuntimeDirectory back to the unit's User= before every command, which undid a
    # chown pre-step on the first install (RUN-20261013-2142-7e3b): the dir comes from a "+" step.
    unit = (ROOT / "deploy" / "coo-gate" / "org-coo-gate.service").read_text()
    sock_dir = os.path.dirname(coo_gate.DEFAULT_SOCKET)
    assert not re.search(r"^RuntimeDirectory", unit, re.M)
    assert f"ExecStartPre=+/usr/bin/install -d -o org-coo-gate -g org-coo-gate -m 0755 {sock_dir}\n" in unit
    assert re.search(rf"^ReadWritePaths=(.* )?{re.escape(sock_dir)}( |$)", unit, re.M)


# --------------------------------------------------------------------------- MCP side

def test_mcp_wait_task_polls_until_the_report(monkeypatch):
    answers = iter([{"ok": True, "task": {"status": "in_progress"}},
                    {"ok": True, "task": {"status": "review", "report": "# r"}}])
    monkeypatch.setattr(coo_mcp_server, "get_task", lambda tid: next(answers))
    clock = iter([0, 5, 15])
    out = coo_mcp_server.wait_task("task-1", 600, sleep=lambda s: None, clock=lambda: next(clock))
    assert out["task"]["status"] == "review"


def test_mcp_without_the_gate_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(coo_mcp_server, "SOCKET_PATH", str(tmp_path / "none.sock"))
    out = coo_mcp_server.call("ping")
    assert out["ok"] is False and "not running" in out["error"]


def test_cxo_config_gives_coo_the_gate_server_and_only_its_tools(tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("")
    (tmp_path / "runners").mkdir()
    shutil.copy(ROOT / "runners" / "coo_mcp_server.py", tmp_path / "runners" / "coo_mcp_server.py")
    entry = cxo_mcp_config._build("org", str(tmp_path), "coo")
    assert entry["args"] == ["-m", "runners.coo_mcp_server"]
    assert "with-org-db-env" not in json.dumps(entry)
    allowed = cxo_mcp_config._allowed_for(["org"], str(tmp_path), False, "coo")
    assert allowed == [f"mcp__org__{n}" for n in coo_mcp_server.TOOL_NAMES]
    assert "mcp__org__merge_task" not in allowed


# --------------------------------------------------------------------------- Run Inbox on the COO server
# SomPong's root work goes through a Run card (CEO 2026-10-01) and its questions through question
# cards; the gate server must serve ask_run / ask_ceo / ask_run_wait itself (PH #adb2edb0, 2026-10-14).

def test_coo_server_serves_the_run_inbox_tools():
    assert {"ask_run", "ask_ceo", "ask_run_wait"} <= set(coo_mcp_server.TOOL_NAMES)


def test_coo_server_loads_with_the_stdlib_only(tmp_path):
    # cxo_mcp_config reads TOOL_NAMES under the launcher's system python3: the import must not pull
    # tools.ask_run, mcp or the hub db in at load time.
    code = ("import importlib.util, sys; "
            f"spec = importlib.util.spec_from_file_location('m', {str(ROOT / 'runners' / 'coo_mcp_server.py')!r}); "
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
            "bad = [k for k in sys.modules if k.split('.')[0] in ('tools', 'mcp', 'lib', 'psycopg')]; "
            "print(len(m.TOOL_NAMES), bad)")
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == f"{len(coo_mcp_server.TOOL_NAMES)} []"


def test_run_inbox_path_holds_no_hub_credential():
    # The ask tools are HTTPS to the Run Inbox with the session user's own token; nothing on the way
    # reads the Postgres hub or its DSN.
    src = (ROOT / "tools" / "ask_run.py").read_text()
    assert "ORG_DB_URL" not in src and "from lib import db" not in src and "psycopg" not in src


def test_coo_ask_run_dry_run_builds_the_card_and_sends_nothing(monkeypatch):
    from tools import ask_run as ask_run_tool
    monkeypatch.setenv("CXO_ROLE", "coo")
    monkeypatch.setenv("CXO_SESSION_ID", "coo-test0001")
    monkeypatch.delenv("WORKER_TASK_ID", raising=False)
    monkeypatch.delenv("WORKER_ROLE", raising=False)
    monkeypatch.setattr(ask_run_tool, "submit", lambda payload: pytest.fail("dry_run posted"))
    out = coo_mcp_server.ask_run(host="contabo", why="restart the inbox after a deploy",
                                 command="systemctl status mooniex-sompong.service", dry_run=True)
    assert out["ok"] is True and out["dry_run"] is True
    assert out["payload"]["command"] == "systemctl status mooniex-sompong.service"


def test_coo_ask_run_refusal_comes_back_as_ok_false(monkeypatch):
    from tools import ask_run as ask_run_tool
    monkeypatch.setenv("CXO_ROLE", "coo")
    monkeypatch.setenv("CXO_SESSION_ID", "coo-test0001")
    monkeypatch.setattr(ask_run_tool, "submit", lambda payload: pytest.fail("a refused ask posted"))
    out = coo_mcp_server.ask_run(host="contabo", why="x",
                                 command="echo ghp_" + "A" * 36, dry_run=False)
    assert out["ok"] is False and "refused" in out["error"]
    assert "A" * 36 not in out["error"]


def test_coo_ask_ceo_and_wait_go_to_ask_run(monkeypatch):
    from tools import ask_run as ask_run_tool
    seen = {}
    monkeypatch.setattr(ask_run_tool, "mcp_ask_ceo",
                        lambda arguments: seen.setdefault("ask", arguments) and {"id": "Q-1", "url": "u"})
    monkeypatch.setattr(ask_run_tool, "wait_result",
                        lambda i, **kw: {"terminal": True, "status": "answered", "id": i, **kw})
    out = coo_mcp_server.ask_ceo(question="Which one?", options=["a", "b"], why="w")
    assert out == {"ok": True, "id": "Q-1", "url": "u"} and seen["ask"]["options"] == ["a", "b"]
    w = coo_mcp_server.ask_run_wait("Q-1", max_wait_s=30)
    assert w["ok"] is True and w["status"] == "answered" and w["max_wait_s"] == 30
    assert w["tail_lines_n"] == 40


def test_coo_ask_run_hub_error_comes_back_as_ok_false(monkeypatch):
    from tools import ask_run as ask_run_tool

    def boom(payload):
        raise ask_run_tool.HubError("the hub is unreachable")
    monkeypatch.setenv("CXO_ROLE", "coo")
    monkeypatch.setenv("CXO_SESSION_ID", "coo-test0001")
    monkeypatch.setattr(ask_run_tool, "submit", boom)
    out = coo_mcp_server.ask_run(host="contabo", why="check the unit", command="uptime")
    assert out == {"ok": False, "error": "the hub is unreachable"}
