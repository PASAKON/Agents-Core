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
import threading
import time
from pathlib import Path

import pytest

from lib import coo_policy
from lib import db as db_mod
from runners import coo_dispatch, coo_gate, coo_mcp_server, coo_worker
from scripts.lib import cxo_mcp_config
from tools import coo_field_notes

ROOT = Path(__file__).resolve().parents[1]
SID = "cootest1"


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    with db_mod.get_conn() as conn:
        conn.execute("CREATE VIEW coo_respawn_events AS SELECT id, kind, payload, ts "
                     "FROM events WHERE kind IN ('coo_respawn_request', 'coo_respawn_done')")
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "contabo")
    db_mod.register_cxo_session("coo", SID, "contabo")
    coo_gate._recent.clear()


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
    # "-": a missing entry would fail the "+" pre-step's namespace before it creates the directory
    # (226/NAMESPACE, RUN-20261014-0237-2c9e)
    assert re.search(rf"^ReadWritePaths=(.* )?-{re.escape(sock_dir)}( |$)", unit, re.M)


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


# --------------------------------------------------------------------------- respawn_clevel (CEO pick #18)

def _respawn(role="cto", host="contabo", sid=SID, **extra) -> dict:
    return coo_gate.handle(
        {"op": "respawn_clevel", "session_id": sid, "role": role, "host": host, **extra},
        994,
    )


@pytest.mark.parametrize('stamp', ['2026-10-26T04:00:01Z', 'invalid', None])
def test_respawn_clock_skew_fails_closed(stamp):
    events = [{'id': 1, 'payload': {'role': 'cto'}, 'ts': stamp}]
    assert '10 minutes' in coo_policy.respawn_rate_limit_reason(
        events, 'cto', now='2026-10-26T04:00:00Z')


def test_respawn_global_daily_cap_and_start_deduplication():
    events = [{'id': i, 'kind': 'coo_respawn_request', 'payload': {'role': role},
               'ts': '2026-10-26T01:00:00Z'} for i, role in enumerate(['cto', 'cmo', 'cto'], 1)]
    assert 'Thai day' in coo_policy.respawn_rate_limit_reason(
        events, 'cfo', now='2026-10-26T04:00:00Z')
    events = events[:2] + [{'id': 4, 'kind': 'coo_respawn_done',
                           'payload': {'role': 'cto', 'started': True, 'request_id': 1},
                           'ts': '2026-10-26T03:59:00Z'}]
    assert coo_policy.respawn_rate_limit_reason(events, 'cfo', now='2026-10-26T04:00:00Z') is None
    assert '10 minutes' in coo_policy.respawn_rate_limit_reason(events, 'cto', now='2026-10-26T04:00:00Z')


def test_refused_attempts_do_not_use_the_daily_start_budget():
    # Three requests the dispatcher refused before launch (started: false) start nothing, so a
    # fourth role that is really gone can still be started the same day (re-review task-7de606ca).
    events = []
    for i, role in enumerate(['cto', 'cmo', 'cgo']):
        events.append({'id': 2 * i + 1, 'kind': 'coo_respawn_request', 'payload': {'role': role},
                       'ts': '2026-10-26T01:00:00Z'})
        events.append({'id': 2 * i + 2, 'kind': 'coo_respawn_done',
                       'payload': {'role': role, 'started': False, 'request_id': 2 * i + 1},
                       'ts': '2026-10-26T01:00:05Z'})
    assert coo_policy.respawn_rate_limit_reason(events, 'cfo', now='2026-10-26T04:00:00Z') is None
    # A request with no done event yet is unsettled and keeps its slot (fail closed).
    events.append({'id': 7, 'kind': 'coo_respawn_request', 'payload': {'role': 'cfo'},
                   'ts': '2026-10-26T03:59:00Z'})
    assert '10 minutes' in coo_policy.respawn_rate_limit_reason(events, 'cfo', now='2026-10-26T04:00:00Z')


def _respawn_events() -> list[dict]:
    with db_mod.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, task_id, actor, kind, payload, ts FROM events WHERE kind='coo_respawn_request' ORDER BY id"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d["payload"]) if isinstance(d["payload"], str) else d["payload"]
        out.append(d)
    return out


@pytest.mark.parametrize("role", ["cto", "cmo", "cgo", "cfo"])
def test_respawn_policy_and_gate_allow_four_peer_c_levels(role):
    assert coo_policy.COO_RESPAWN_ROLES == ("cto", "cmo", "cgo", "cfo")
    coo_policy.check_respawn(role, "contabo")
    out = _respawn(role=role)
    assert out["ok"] is True and out["queued"] is True and out["role"] == role and out["host"] == "contabo"
    assert isinstance(out["request_id"], int) and out["request_id"] >= 1
    evs = [e for e in _respawn_events() if e["id"] == out["request_id"]]
    assert len(evs) == 1
    assert evs[0]["task_id"] is None
    assert evs[0]["actor"] == "coo_gate"
    assert evs[0]["payload"] == {"role": role, "host": "contabo", "by_session": SID}


@pytest.mark.parametrize("bad_role", ["coo", "researcher", "developer", "project_head", "CTO", ""])
def test_respawn_gate_refuses_bad_roles(bad_role):
    out = _respawn(role=bad_role)
    assert out["ok"] is False
    assert _respawn_events() == []


@pytest.mark.parametrize("bad_host", ["mac", "winbox", "CONTABO", "localhost", ""])
def test_respawn_gate_refuses_non_contabo_hosts(bad_host):
    out = _respawn(host=bad_host)
    assert out["ok"] is False
    if bad_host.strip():
        assert "other hosts wait for Run Inbox P2" in out["error"]
    assert _respawn_events() == []


@pytest.mark.parametrize("extra_field,val", [
    ("prompt", "do something"),
    ("brief", "secret instructions"),
    ("argv", ["--dangerously-skip-permissions"]),
    ("id", "deadbeef"),
    ("uuid", "d405e3e2-1111-2222-3333-a6f2f69c4825"),
    ("initial_prompt", "hi"),
    ("session", "override"),
])
def test_respawn_gate_rejects_any_extra_field(extra_field, val):
    out = _respawn(**{extra_field: val})
    assert out["ok"] is False and extra_field in out["error"]
    assert _respawn_events() == []


def test_respawn_gate_refuses_non_coo_session():
    db_mod.register_cxo_session("cto", "ctosess1", "contabo")
    out = _respawn(sid="ctosess1")
    assert out["ok"] is False and "not a coo session" in out["error"]
    assert _respawn_events() == []


def test_respawn_gate_rate_limit_one_per_10_min_and_three_per_thai_day(monkeypatch):
    # 2026-10-26 02:00 UTC == 09:00 Asia/Bangkok.
    now = "2026-10-26T02:00:00+00:00"
    with db_mod.get_conn() as conn:
        conn.execute(
            "INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_respawn_request', ?, ?)",
            (json.dumps({"role": "cto", "host": "contabo", "by_session": SID}), "2026-10-26T01:55:00+00:00"),
        )
    # 5 min later: refused for cto (10-min cooldown), but cmo is independent and allowed.
    refused_10m = _respawn_at(now, role="cto")
    assert refused_10m["ok"] is False and "10 min" in refused_10m["error"]
    allowed_cmo = _respawn_at(now, role="cmo")
    assert allowed_cmo["ok"] is True

    # 15 min after first cto request (02:10 UTC == 09:10 BKK): 2nd cto request today succeeds.
    now = "2026-10-26T02:10:00+00:00"
    with db_mod.get_conn() as conn:
        conn.execute(
            "INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_respawn_request', ?, ?)",
            (json.dumps({"role": "cto", "host": "contabo", "by_session": SID}), "2026-10-26T02:10:00+00:00"),
        )
        conn.execute(
            "INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_respawn_request', ?, ?)",
            (json.dumps({"role": "cto", "host": "contabo", "by_session": SID}), "2026-10-26T02:30:00+00:00"),
        )
    # At 03:00 UTC (10:00 BKK), 3 cto requests already exist in the current Thai day -> 4th refused.
    now = "2026-10-26T03:00:00+00:00"
    refused_day = _respawn_at(now, role="cto")
    assert refused_day["ok"] is False and "Thai day" in refused_day["error"]

    # At 17:05 UTC == 2026-10-27 00:05 Asia/Bangkok (next Thai day, still 2026-10-26 in UTC!): allowed!
    now = "2026-10-26T17:05:00+00:00"
    allowed_next_thai_day = _respawn_at(now, role="cto")
    assert allowed_next_thai_day["ok"] is True


def test_sql_events_guard_allows_only_narrow_coo_respawn_request():
    sql = (ROOT / "deploy" / "coo-gate" / "org_coo_role.sql").read_text()
    assert "IF NEW.kind = 'coo_respawn_request' THEN" in sql
    assert "IF NEW.task_id IS NOT NULL THEN" in sql
    assert "ARRAY['by_session', 'host', 'role']" in sql
    m = re.search(r"\(NEW\.payload::jsonb ->> 'role'\) IN \(([^)]*)\)", sql)
    assert m, "coo_respawn_request role allowlist missing in org_coo_events_guard"
    assert tuple(re.findall(r"'([a-z_]+)'", m.group(1))) == coo_policy.COO_RESPAWN_ROLES
    assert "((NEW.payload::jsonb ->> 'host') = 'contabo') IS DISTINCT FROM TRUE" in sql
    for field in ('role', 'host', 'by_session'):
        assert f"jsonb_typeof(NEW.payload::jsonb -> '{field}') IS DISTINCT FROM 'string'" in sql
    assert "((NEW.payload::jsonb ->> 'role') IN ('cto', 'cmo', 'cgo', 'cfo')) IS DISTINCT FROM TRUE" in sql
    assert "SET LOCAL ROLE org_coo" in sql
    assert "ARRAY['coo_respawn_done', 'coo_respawn_request']" in sql
    assert '"role":null' in sql
    assert "WHEN SQLSTATE 'ZX001' THEN accepted := true" in sql
    assert "GRANT INSERT (task_id, actor, kind, payload, ts) ON events TO org_coo;" in sql
    assert "CREATE OR REPLACE VIEW coo_respawn_events WITH (security_barrier)" in sql
    assert "GRANT SELECT ON coo_respawn_events TO org_coo;" in sql
    assert "'tasks', 'coo_respawn_events', 'c_level_sessions'" in sql
    assert "GRANT SELECT (id, kind, payload, ts)" not in sql


# --------------------------------------------------------------------------- CEO-order mirror (CO-<n>)
# org_coo mirrors SomPong's relayed CEO orders into the hub `orders` table (lib/portfolio order_take
# / order_close). Column grants cannot limit rows, so section 5's triggers do; these tests state each
# grant, each guard condition and each proof case of org_coo_role.sql. The same file is run against a
# real Postgres by tests/test_coo_orders_pg.py.

ORDER_INSERT_COLS = ("id", "words", "channel", "taken_by", "taken_at", "project_id", "due_at", "due_set_by")
ORDER_UPDATE_COLS = ("closed_at", "outcome")
EVENT_INSERT_COLS = ("project_id", "at", "kind", "actor", "body")


def _sql_flat() -> str:
    """The role file with every run of whitespace squeezed to one space, so a wrapped statement matches."""
    return " ".join((ROOT / "deploy" / "coo-gate" / "org_coo_role.sql").read_text().split())


def _sql_function(name: str) -> str:
    flat = _sql_flat()
    m = re.search(rf"CREATE OR REPLACE FUNCTION {name}\(\) RETURNS trigger .*? \$fn\$;", flat)
    assert m, f"{name} is missing from org_coo_role.sql"
    return m.group(0)


def test_sql_grants_the_order_mirror_exactly_what_order_take_and_order_close_use():
    flat = _sql_flat()
    assert ("GRANT SELECT, INSERT (id, words, channel, taken_by, taken_at, project_id, due_at, due_set_by), "
            "UPDATE (closed_at, outcome) ON orders TO org_coo;") in flat
    assert "GRANT INSERT (project_id, at, kind, actor, body) ON project_events TO org_coo;" in flat
    assert flat.count("ON orders TO org_coo") == 1 and flat.count("ON project_events TO org_coo") == 1
    # The grants are the columns lib/portfolio actually writes: a changed INSERT there fails here first.
    src = (ROOT / "lib" / "portfolio.py").read_text()
    take = re.search(r"INSERT INTO orders \(([^)]*)\)", src)
    assert tuple(c.strip() for c in take.group(1).split(",")) == ORDER_INSERT_COLS
    assert "UPDATE orders SET closed_at = ?, outcome = ? WHERE id = ?" in src
    event = re.search(r"INSERT INTO project_events \(([^)]*)\)", src)
    assert tuple(c.strip() for c in event.group(1).split(",")) == EVENT_INSERT_COLS
    # Nothing destructive, nothing on the other portfolio tables.
    for table in ("projects", "milestones", "ceo_gos", "resource_locks", "post_ledger", "session_heartbeats"):
        assert f"ON {table} TO org_coo" not in flat
    assert not re.search(r"GRANT [^;]*\b(DELETE|TRUNCATE|TRIGGER|ALL)\b", flat)


def test_sql_orders_guard_holds_inserts_to_co_rows_and_updates_to_closing_them():
    fn = _sql_function("org_coo_orders_guard")
    assert "IF current_user <> 'org_coo' THEN RETURN NEW;" in fn
    # INSERT
    assert "IF TG_OP = 'INSERT' THEN" in fn
    assert "(NEW.id ~ '^CO-[0-9]+$') IS DISTINCT FROM TRUE" in fn
    assert "NEW.taken_by IS DISTINCT FROM 'sompong'" in fn
    assert "NEW.channel IS DISTINCT FROM ('sompong:' || substr(NEW.id, 4))" in fn
    assert "NEW.project_id IS NOT NULL" in fn
    assert "NEW.due_at IS NOT NULL" in fn
    # UPDATE
    assert "(OLD.id ~ '^CO-[0-9]+$') IS DISTINCT FROM TRUE OR OLD.closed_at IS NOT NULL" in fn
    assert "NEW.closed_at IS NULL" in fn
    assert ("(to_jsonb(NEW) - 'closed_at' - 'outcome') IS DISTINCT FROM "
            "(to_jsonb(OLD) - 'closed_at' - 'outcome')") in fn
    assert "SET search_path = pg_catalog" in fn
    flat = _sql_flat()
    assert ("DROP TRIGGER IF EXISTS org_coo_guard ON orders; CREATE TRIGGER org_coo_guard "
            "BEFORE INSERT OR UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION org_coo_orders_guard();") in flat


def test_sql_project_events_guard_holds_org_coo_to_the_close_event_of_its_closed_order():
    fn = _sql_function("org_coo_project_events_guard")
    assert "IF current_user <> 'org_coo' THEN RETURN NEW;" in fn
    assert "NEW.kind IS DISTINCT FROM 'order'" in fn
    assert "(NEW.body ->> 'op') IS DISTINCT FROM 'close'" in fn
    assert "((NEW.body ->> 'id') ~ '^CO-[0-9]+$') IS DISTINCT FROM TRUE" in fn
    assert "(NEW.actor ~ '^COO#[0-9a-f]{8}$') IS DISTINCT FROM TRUE" in fn
    # The order must exist, belong to this project and already be closed (order_close updates first).
    assert ("SELECT 1 FROM public.orders o WHERE o.id = (NEW.body ->> 'id') "
            "AND o.project_id = NEW.project_id AND o.closed_at IS NOT NULL") in fn
    assert "SET search_path = pg_catalog" in fn
    flat = _sql_flat()
    assert ("DROP TRIGGER IF EXISTS org_coo_guard ON project_events; CREATE TRIGGER org_coo_guard "
            "BEFORE INSERT ON project_events FOR EACH ROW EXECUTE FUNCTION org_coo_project_events_guard();") in flat


@pytest.mark.parametrize("session_id", ["abcd1234", "00000000", "f66280fc", "0badc0de"])
def test_sql_event_actor_pattern_matches_the_label_report_to_ceo_writes_for_the_coo(session_id):
    """lib/ceo_report passes identity.label() as the actor; for SomPong that is "COO#<CXO_SESSION_ID>",
    and cxo-claude.sh mints or adopts that id as 8 lowercase hex digits."""
    from tools.agent_transport import Identity
    label = Identity("cxo", "coo", session_id).label()
    assert label == f"COO#{session_id}"
    pattern = re.search(r"NEW\.actor ~ '([^']+)'", _sql_function("org_coo_project_events_guard")).group(1)
    pattern = pattern.replace("$", r"\Z")       # Postgres' $ is end of string; Python's also matches before a final newline
    assert re.search(pattern, label)
    for other in (Identity("cxo", "cto", session_id).label(), Identity("cxo", "project_head", session_id).label(),
                  "COO#ABCD1234", "COO#abcd123", "COO#abcd12345", "COO#abcd123g", "sompong", f"{label}\n"):
        assert not re.search(pattern, other), other


def test_sql_order_mirror_proof_cases_and_privilege_lists():
    sql = (ROOT / "deploy" / "coo-gate" / "org_coo_role.sql").read_text()
    flat = _sql_flat()
    # Section 6 knows the new privileges and the one new readable table.
    want = re.search(r"want text := (.*?);\s*BEGIN", sql, re.S).group(1)
    tokens = set(re.findall(r"[a-z_]+\.[a-z_]+:[A-Z]+", want))
    assert {f"orders.{c}:INSERT" for c in ORDER_INSERT_COLS} <= tokens
    assert {f"orders.{c}:UPDATE" for c in ORDER_UPDATE_COLS} <= tokens
    assert {f"project_events.{c}:INSERT" for c in EVENT_INSERT_COLS} <= tokens
    assert not {t for t in tokens if t.startswith(("orders.", "project_events.")) and t.endswith(":REFERENCES")}
    assert ("'tasks', 'coo_respawn_events', 'c_level_sessions', 'live_hosts', 'live_sessions', 'orders')") in flat
    assert "live_hosts, live_sessions and orders, nothing destructive" in flat
    # The behavioural proof: a separate block, so the audit / field-note proof above it is untouched.
    proof = sql.split("DO $orders_proof$")[1].split("$orders_proof$;")[0]
    for case in (
        "A valid CO order, taken and closed",              # accepted
        "A CO order of a project, closed with its event",  # accepted
        "An O- id", "A taken_by other than sompong", "A channel that is not the id",
        "A due date on insert", "A project on insert",
        "An update of a closed CO order", "An update that changes words",
        "An update that does not set closed_at", "An update of an order that is not CO-<n>",
        "A project_events row of another kind", "A close event under another actor", "A take event",
        "A close event for an order that is still open", "A close event for another project''s order",
        "A close event for an order that is not CO-<n>",
    ):
        assert f"('{case}" in proof, case
    assert proof.count(", true,") == 2          # the two accepted cases; everything else is refused
    assert "SET LOCAL ROLE org_coo" in proof
    assert "WHEN SQLSTATE 'ZX001' THEN accepted := true" in proof
    assert "IF NOT switched OR proof_step < proof_last THEN" in proof     # a broken setup step fails the run
    assert "GRANT UPDATE (words) ON public.orders TO org_coo" in proof     # so the trigger, not the grant, refuses
    # Rolled back as the existing cases do: every case ends in the ZX001 raise, never a COMMIT.
    assert "RAISE EXCEPTION USING ERRCODE = 'ZX001'" in proof and "COMMIT" not in proof


def test_respawn_status_and_mcp_tool_roundtrip(monkeypatch):
    assert coo_mcp_server.TOOL_NAMES[-1] == "respawn_clevel"
    monkeypatch.setenv("CXO_SESSION_ID", SID)
    monkeypatch.setattr(
        coo_mcp_server,
        "call",
        lambda op, **fields: coo_gate.handle({"op": op, **fields}, 994),
    )
    queued = coo_mcp_server.respawn_clevel("cto", "contabo")
    assert queued["ok"] is True and queued["queued"] is True
    req_id = queued["request_id"]

    pending_status = coo_mcp_server.respawn_status(req_id)
    assert pending_status["ok"] is True and pending_status["done"] is False

    with db_mod.get_conn() as conn:
        db_mod.log_event(
            conn, None, "coo_dispatch", "coo_respawn_done",
            {
                "request_id": req_id,
                "role": "cto",
                "host": "contabo",
                "ok": True,
                "mode": "resume",
                "sid": "f69c4825",
                "uuid": "d405e3e2-1111-2222-3333-a6f2f69c4825",
                "reason": "resume session started in tmux cto-f69c4825",
            },
        )
    done_status = coo_mcp_server.respawn_clevel(request_id=req_id)
    assert done_status["ok"] is True and done_status["done"] is True
    assert done_status["respawn_ok"] is True
    assert done_status["mode"] == "resume"
    assert done_status["sid"] == "f69c4825"
    assert done_status["uuid"] == "d405e3e2-1111-2222-3333-a6f2f69c4825"


@pytest.mark.parametrize("other_session,other_role", [(SID, "cmo"), ("othercoo", "cto")])
def test_respawn_request_id_ignores_interleaved_requests(monkeypatch, other_session, other_role):
    original = db_mod.log_event

    def interleaved(conn, task_id, actor, kind, payload):
        original(conn, task_id, actor, kind, payload)
        original(conn, None, actor, kind,
                 {"role": other_role, "host": "contabo", "by_session": other_session})

    monkeypatch.setattr(db_mod, "log_event", interleaved)
    result = _respawn()
    assert result["ok"] is True
    events = _respawn_events()
    assert len(events) == 2
    assert result["request_id"] == events[0]["id"]


@pytest.mark.parametrize("done_id", [None, 999999])
def test_respawn_status_requires_matching_request_id(done_id):
    result = _respawn()
    payload = {"role": "cto", "host": "contabo", "ok": True}
    if done_id is not None:
        payload["request_id"] = done_id
    with db_mod.get_conn() as conn:
        db_mod.log_event(conn, None, "coo_dispatch", "coo_respawn_done", payload)
    status = coo_gate.op_respawn_status({"request_id": result["request_id"]}, 994)
    assert status["done"] is False


def test_respawn_view_excludes_unrelated_payloads():
    with db_mod.get_conn() as conn:
        db_mod.log_event(conn, None, "test", "private_event", {"private": "secret"})
        assert conn.execute("SELECT * FROM coo_respawn_events").fetchall() == []
    assert "FROM events" not in (ROOT / "runners/coo_gate.py").read_text()


def _respawn_at(now, role):
    try:
        return {"ok": True, **coo_gate.op_respawn_clevel(
            {"op": "respawn_clevel", "session_id": SID, "role": role, "host": "contabo"},
            994, now=now)}
    except coo_gate.Refused as exc:
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------------------- audit log (#38)

SQL = ROOT / "deploy" / "coo-gate" / "org_coo_role.sql"
HOOK = ROOT / "scripts" / "coo-audit-hook.py"


def _audit(**over) -> dict:
    req = {"op": "audit_append", "session_id": SID, "tool": "Bash", "input": '{"command": "ls"}', "ok": True}
    req.update(over)
    return coo_gate.handle(req, 994)


def _rows(kind: str) -> list[dict]:
    with db_mod.get_conn() as conn:
        rows = conn.execute("SELECT task_id, actor, payload, ts FROM events WHERE kind=? ORDER BY id", (kind,)).fetchall()
    return [{"task_id": r["task_id"], "actor": r["actor"], "ts": r["ts"], "payload": json.loads(r["payload"])}
            for r in rows]


def test_audit_appends_one_taskless_row_with_exactly_four_keys():
    out = _audit(tool="mcp__org__ask_run", input='{"host": "contabo"}', ok=False)
    assert out == {"ok": True, "recorded": True}
    (row,) = _rows("coo_audit")
    assert row["task_id"] is None and row["actor"] == "coo_gate"
    assert row["payload"] == {"session_id": SID, "tool": "mcp__org__ask_run",
                              "input": '{"host": "contabo"}', "ok": False}


def _fake(*parts: str) -> str:
    """A credential-shaped value built at run time, so no token-shaped literal sits in the repo."""
    return "".join(parts)


REDACT_CASES = [
    (_fake("ghp_", "Ab1" * 13), 'git push https://x:{s}@github.com/o/r'),
    (_fake("sk-", "Zz9" * 15), 'export OPENAI_API_KEY={s} && run'),
    (_fake("sk-ant-", "Qq7" * 15), '{{"env": {{"ANTHROPIC_API_KEY": "{s}"}}}}'),
    ("hunter2 hunter3", '{{"password": "{s}", "user": "u"}}'),
    ("Xq9" * 8, 'curl -H \\"Authorization: Bearer {s}\\" https://api.example/v1'),
    ("Sup3rS3cretPw", 'psql postgresql://org:{s}@db.example:5432/org'),
    ("abc123def456", 'curl "https://api.example/x?access_token={s}&b=1"'),
    (_fake("eyJhbGciOiJI", "UzI1NiJ9.eyJzdWIiOiIx", "MjM0NTY3ODkw.SflKxwRJSMeKKF2QT4"), 'jwt {s} sent'),
    ("dXNlcjpwYXNzd29yZDEyMw==", 'curl -H "Authorization: Basic {s}"'),
    ("Ab3dE5gH7jK9mN1pQ3sT5vW7yZ9bC1dE3fG5", 'key is {s} here'),
    ("MIIEvQIBADANBgkqhkiG9w0BAQEFAASC", '-----BEGIN PRIVATE KEY-----\\n{s}\\n-----END PRIVATE KEY----- after'),
]


def test_audit_redacts_what_looks_like_a_credential():
    for secret, text in REDACT_CASES:
        assert _audit(input=text.format(s=secret))["ok"]
        stored = _rows("coo_audit")[-1]["payload"]["input"]
        for piece in secret.split():
            assert piece not in stored, (text, stored)
        assert "<redacted>" in stored or "***" in stored, (text, stored)


def test_audit_keeps_paths_uuids_and_env_references():
    text = ('{"command": "cd /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-503505d8 '
            '&& GH_TOKEN=\\"$GH_TOKEN\\" gh pr view d405e3e2-1111-2222-3333-a6f2f69c4825"}')
    assert _audit(input=text)["ok"]
    assert _rows("coo_audit")[0]["payload"]["input"] == text


def test_audit_cuts_to_2000_and_a_secret_on_the_cut_does_not_leak():
    key = _fake("sk-", "Q9" * 20)
    assert _audit(input="a " * 995 + key + " tail")["ok"]
    stored = _rows("coo_audit")[0]["payload"]["input"]
    assert len(stored) == 2000 and "Q9Q9Q9" not in stored
    assert _audit(input="y" * 5000)["ok"] and len(_rows("coo_audit")[1]["payload"]["input"]) == 2000


def test_audit_survives_a_nul_and_a_lone_surrogate():
    """Postgres refuses both in a jsonb string, which would otherwise be a way to skip the log."""
    assert _audit(input="a\x00b \ud800 c")["ok"]
    stored = _rows("coo_audit")[0]["payload"]["input"]
    assert stored == "ab ? c"
    stored.encode("utf-8")


def test_audit_cuts_a_long_tool_name_instead_of_losing_the_row():
    assert _audit(tool="t" * 150)["ok"]
    assert _rows("coo_audit")[0]["payload"]["tool"] == "t" * 100


AUDIT_REFUSALS = [
    ({"extra": 1}, "unexpected: extra"),
    ({"input": {"command": "ls"}}, "input must be a string"),
    ({"input": None}, "input must be a string"),
    ({"ok": "yes"}, "ok must be true or false"),
    ({"ok": 1}, "ok must be true or false"),
    ({"tool": ""}, "tool is required"),
    ({"tool": "\x00"}, "tool is required"),
    ({"tool": 5}, "tool is required"),
    ({"session_id": "nosuchsession"}, "not a coo session"),
    ({"session_id": ""}, "session_id is required"),
]


def test_audit_refuses_a_bad_request_and_writes_nothing():
    for over, why in AUDIT_REFUSALS:
        out = _audit(**over)
        assert out["ok"] is False and why in out["error"], (over, out)
    assert _rows("coo_audit") == []


def test_audit_refuses_a_session_that_is_not_coo():
    db_mod.register_cxo_session("cto", "ctoabc12", "contabo")
    assert "not a coo session" in _audit(session_id="ctoabc12")["error"]
    assert _rows("coo_audit") == []


def test_audit_cap_is_600_per_session_per_hour(monkeypatch):
    assert coo_gate.AUDIT_MAX_PER_HOUR == 600 and coo_gate.RATE_WINDOW_S == 3600
    monkeypatch.setattr(coo_gate, "AUDIT_MAX_PER_HOUR", 5)   # same code path, without 600 writes
    db_mod.register_cxo_session("coo", "coo-other", "contabo")
    req = {"op": "audit_append", "session_id": SID, "tool": "Bash", "input": "{}", "ok": True}
    t0 = time.time() - 60       # handle() below reads the real clock: stay inside the same hour
    for i in range(5):
        coo_gate.op_audit_append(req, 994, now=t0 + i)
    with pytest.raises(coo_gate.Refused) as refused:
        coo_gate.op_audit_append(req, 994, now=t0 + 10)
    assert str(refused.value) == "audit rate cap: at most 5 rows per session per hour"
    handled = coo_gate.handle(req, 994)
    assert handled["ok"] is False and "audit rate cap" in handled["error"]
    coo_gate.op_audit_append({**req, "session_id": "coo-other"}, 994, now=t0 + 10)   # another session
    coo_gate.op_audit_append(req, 994, now=t0 + 3600)   # the first row has aged out
    assert len(_rows("coo_audit")) == 7


def test_audit_refusals_do_not_use_up_the_cap(monkeypatch):
    monkeypatch.setattr(coo_gate, "AUDIT_MAX_PER_HOUR", 2)
    for _ in range(5):
        assert _audit(ok="maybe")["ok"] is False
    assert _audit()["ok"] and _audit()["ok"] and _audit()["ok"] is False


# --------------------------------------------------------------------------- the PostToolUse hook

@pytest.fixture
def gate_sock(tmp_path):
    """A real unix socket served by coo_gate.serve_one on this test's ledger."""
    path = str(tmp_path / "g.sock")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(8)
    srv.settimeout(0.2)
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with conn:
                conn.settimeout(5)
                try:
                    coo_gate.serve_one(conn, frozenset({os.getuid()}))
                except OSError:
                    pass

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    yield path
    stop.set()
    t.join(2)
    srv.close()


def _hook(stdin: str, sock: str, session: str | None = None, timeout: float = 15):
    env = {"PATH": os.environ.get("PATH", ""), "COO_GATE_SOCKET": sock}
    if session:
        env["CXO_SESSION_ID"] = session
    t0 = time.monotonic()
    done = subprocess.run([sys.executable, "-I", str(HOOK)], input=stdin, env=env,
                          capture_output=True, text=True, timeout=timeout)
    return done, time.monotonic() - t0


def _event(**over) -> str:
    ev = {"session_id": "claude-uuid-1", "hook_event_name": "PostToolUse", "tool_name": "Bash",
          "tool_input": {"command": "ls /tmp"}, "tool_response": {"stdout": "x", "interrupted": False}}
    ev.update(over)
    return json.dumps(ev)


def test_hook_writes_the_audit_row_through_the_gate(gate_sock):
    done, _ = _hook(_event(), gate_sock, session=SID)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")
    (row,) = _rows("coo_audit")
    assert row["payload"] == {"session_id": SID, "tool": "Bash", "input": '{"command": "ls /tmp"}', "ok": True}


def test_hook_takes_the_hook_session_id_when_the_env_has_none(gate_sock):
    done, _ = _hook(_event(session_id=SID), gate_sock)
    assert done.returncode == 0
    assert _rows("coo_audit")[0]["payload"]["session_id"] == SID


def test_hook_env_session_wins_over_the_hook_session_id(gate_sock):
    _hook(_event(session_id="somebody-else"), gate_sock, session=SID)
    assert [r["payload"]["session_id"] for r in _rows("coo_audit")] == [SID]


@pytest.mark.parametrize("over", [
    {"hook_event_name": "PostToolUseFailure"},
    {"tool_response": {"is_error": True}},
    {"tool_response": {"error": "boom"}},
    {"tool_response": {"success": False}},
])
def test_hook_records_a_failed_call_as_ok_false(gate_sock, over):
    _hook(_event(**over), gate_sock, session=SID)
    assert _rows("coo_audit")[0]["payload"]["ok"] is False


def test_hook_cuts_a_huge_input_to_fit_one_request(gate_sock):
    big = {"file_path": "/tmp/x", "content": "z" * 500_000}
    done, _ = _hook(_event(tool_name="Write", tool_input=big), gate_sock, session=SID)
    assert done.returncode == 0
    (row,) = _rows("coo_audit")
    assert row["payload"]["tool"] == "Write" and len(row["payload"]["input"]) == 2000


def test_hook_fails_open_on_junk_input(gate_sock):
    for stdin in ("", "not json", "[]", "null", '{"tool_input": {}}', '{"tool_name": 5}'):
        done, _ = _hook(stdin, gate_sock, session=SID)
        assert (done.returncode, done.stdout, done.stderr) == (0, "", ""), stdin
    assert _rows("coo_audit") == []


def test_hook_fails_open_with_no_gate(tmp_path):
    done, took = _hook(_event(), str(tmp_path / "missing.sock"), session=SID)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")
    assert took < 5


def test_hook_fails_open_when_the_gate_refuses(gate_sock):
    done, _ = _hook(_event(), gate_sock, session="nosuchsession")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")
    assert _rows("coo_audit") == []


def test_hook_gives_up_after_two_seconds_on_a_gate_that_never_answers(tmp_path):
    path = str(tmp_path / "hung.sock")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(1)       # accepts the connection in the kernel and never reads or answers
    try:
        done, took = _hook(_event(), path, session=SID)
    finally:
        srv.close()
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")
    assert 1.5 < took < 4.5, took


def test_hook_gives_up_after_two_seconds_when_stdin_never_closes(tmp_path):
    env = {"PATH": os.environ.get("PATH", ""), "COO_GATE_SOCKET": str(tmp_path / "none.sock")}
    t0 = time.monotonic()
    proc = subprocess.Popen([sys.executable, "-I", str(HOOK)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        proc.wait(timeout=6)          # stdin stays open (communicate() would close it): only the alarm ends this
        took = time.monotonic() - t0
        out, err = proc.stdout.read(), proc.stderr.read()
    finally:
        proc.kill()
        for f in (proc.stdin, proc.stdout, proc.stderr):
            f.close()
    assert (proc.returncode, out, err) == (0, b"", b"")
    assert 1.5 < took < 4.5


def test_hook_and_gate_agree_on_the_limits():
    import importlib.util
    spec = importlib.util.spec_from_file_location("coo_audit_hook", HOOK)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    assert hook.MAX_AUDIT_TOOL == coo_gate.MAX_AUDIT_TOOL
    assert coo_gate.MAX_AUDIT_INPUT <= hook.SEND_INPUT_CHARS < coo_gate.MAX_REQUEST_BYTES // 4
    assert hook.DEFAULT_SOCKET == coo_gate.DEFAULT_SOCKET


# --------------------------------------------------------------------------- field notes (#24b)

@pytest.fixture
def skills(tmp_path, monkeypatch):
    d = tmp_path / "skills"
    for name in ("ALL_Rules_Approvals", "CTO_Gate_MergeChecklist", "abc"):
        (d / name).mkdir(parents=True)
    (d / "a_file").write_text("not a skill")
    monkeypatch.setattr(coo_gate, "SKILLS_DIR", d)
    return d


def _note(**over) -> dict:
    req = {"op": "field_note", "session_id": SID, "skill": "ALL_Rules_Approvals", "tag": "MISSING",
           "text": "it never says a card expires after 24 h"}
    req.update(over)
    return coo_gate.handle(req, 994)


def test_field_note_default_skills_dir_is_this_repos():
    assert coo_gate.SKILLS_DIR == ROOT / ".claude" / "skills" and coo_gate.SKILLS_DIR.is_dir()


def test_field_note_writes_one_taskless_row_per_tag(skills):
    for tag in ("MISSING", "WRONG", "COSTLY", "CONFIRMED"):
        out = _note(tag=tag)
        assert out == {"ok": True, "recorded": True, "skill": "ALL_Rules_Approvals", "tag": tag}
    rows = _rows("coo_field_note")
    assert [r["payload"]["tag"] for r in rows] == ["MISSING", "WRONG", "COSTLY", "CONFIRMED"]
    assert all(r["task_id"] is None and r["actor"] == "coo_gate" for r in rows)
    assert rows[0]["payload"] == {"session_id": SID, "skill": "ALL_Rules_Approvals", "tag": "MISSING",
                                  "text": "it never says a card expires after 24 h"}


NOTE_REFUSALS = [
    ({"skill": "../etc"}, "skill must match"),
    ({"skill": "ab"}, "skill must match"),
    ({"skill": "a" * 81}, "skill must match"),
    ({"skill": "ALL_Rules_Approvals\n"}, "skill must match"),
    ({"skill": "ALL Rules"}, "skill must match"),
    ({"skill": "..."}, "skill must match"),
    ({"skill": ".hidden-dir"}, "skill must match"),
    ({"skill": None}, "skill must match"),
    ({"skill": "Nonexistent_Skill"}, "not a directory under .claude/skills"),
    ({"skill": "a_file"}, "not a directory under .claude/skills"),
    ({"tag": "OTHER"}, "tag must be one of"),
    ({"tag": "missing"}, "tag must be one of"),
    ({"tag": None}, "tag must be one of"),
    ({"text": "two\nlines"}, "single line"),
    ({"text": "carriage\rreturn inside"}, "single line"),
    ({"text": "x" * 601}, "longer than 600"),
    ({"text": ""}, "text is required"),
    ({"text": "\x00"}, "single line"),
    ({"text": 5}, "text is required"),
    ({"extra": "x"}, "unexpected: extra"),
    ({"session_id": "nosuchsession"}, "not a coo session"),
]


def test_field_note_refuses_a_bad_request_and_writes_nothing(skills):
    for over, why in NOTE_REFUSALS:
        out = _note(**over)
        assert out["ok"] is False and why in out["error"], (over, out)
    assert _rows("coo_field_note") == []


def test_field_note_takes_a_600_character_line(skills):
    assert _note(text="y" * 600)["ok"]
    assert len(_rows("coo_field_note")[0]["payload"]["text"]) == 600


def test_field_note_masks_a_credential_in_the_text(skills):
    key = _fake("ghp_", "Ab1" * 13)
    assert _note(text=f"the skill told me to put {key} in the card")["ok"]
    assert key not in _rows("coo_field_note")[0]["payload"]["text"]


def test_field_note_cap_is_per_session_per_hour(skills, monkeypatch):
    assert coo_gate.FIELD_NOTE_MAX_PER_HOUR == 30
    req = {"op": "field_note", "session_id": SID, "skill": "abc", "tag": "WRONG", "text": "t"}
    monkeypatch.setattr(coo_gate, "FIELD_NOTE_MAX_PER_HOUR", 2)
    coo_gate.op_field_note(req, 994, now=10.0)
    coo_gate.op_field_note(req, 994, now=11.0)
    with pytest.raises(coo_gate.Refused, match="field note rate cap: at most 2 per session per hour"):
        coo_gate.op_field_note(req, 994, now=12.0)
    # the audit cap and the note cap do not share a counter
    assert _audit()["ok"]


def test_gate_serves_the_two_new_ops_and_no_others_were_added():
    assert {"audit_append", "field_note"} <= set(coo_gate.OPS)
    assert set(coo_gate.OPS) == {"ping", "set_charter", "create_task", "delegate_task", "get_task",
                                 "list_tasks", "close_task", "live_sessions", "respawn_clevel",
                                 "respawn_status", "audit_append", "field_note"}


# --------------------------------------------------------------------------- the reader

def _put_note(ts: str, text: str, skill="ALL_Rules_Approvals", tag="WRONG") -> None:
    with db_mod.get_conn() as conn:
        conn.execute("INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'coo_gate', 'coo_field_note', ?, ?)",
                     (json.dumps({"session_id": SID, "skill": skill, "tag": tag, "text": text}), ts))


def test_reader_prints_skill_tag_ts_text_oldest_first(capsys):
    _put_note("2026-10-26T10:00:00+00:00", "first")
    _put_note("2026-10-27T10:00:00+00:00", "second", skill="CTO_Gate_MergeChecklist", tag="COSTLY")
    assert coo_field_notes.main(["list"]) == 0
    cap = capsys.readouterr()
    assert cap.out.splitlines() == [
        "ALL_Rules_Approvals · WRONG · 2026-10-26T10:00:00+00:00 · first",
        "CTO_Gate_MergeChecklist · COSTLY · 2026-10-27T10:00:00+00:00 · second"]
    assert cap.err.strip() == "2 field note(s)"


@pytest.mark.parametrize("since,lines", [
    ("2026-10-27", ["second"]),
    ("2026-10-27T10:00:00Z", ["second"]),
    ("2026-10-27T17:00:00+07:00", ["second"]),      # the same instant, written in Thai time
    ("2026-10-27T10:00:01Z", []),
    ("2026-01-01", ["first", "second"]),
])
def test_reader_since_filters_on_the_instant(capsys, since, lines):
    _put_note("2026-10-26T10:00:00+00:00", "first")
    _put_note("2026-10-27T10:00:00+00:00", "second")
    assert coo_field_notes.main(["list", "--since", since]) == 0
    assert [l.rsplit(" · ", 1)[1] for l in capsys.readouterr().out.splitlines()] == lines


def test_reader_rejects_a_bad_since():
    with pytest.raises(SystemExit):
        coo_field_notes.main(["list", "--since", "yesterday"])


def test_reader_strips_control_characters_from_what_the_coo_wrote(capsys):
    _put_note("2026-10-27T10:00:00+00:00", "a\x1b[31mred\x1b[0m\nfake   line\x07")
    coo_field_notes.main(["list"])
    out = capsys.readouterr().out
    assert "\x1b" not in out and "\x07" not in out and " " not in out
    assert len(out.splitlines()) == 1


def test_reader_tolerates_a_row_it_cannot_parse(capsys):
    with db_mod.get_conn() as conn:
        conn.execute("INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'x', 'coo_field_note', 'not json', '2026-10-27T10:00:00+00:00')")
    assert coo_field_notes.main(["list"]) == 0
    assert capsys.readouterr().out.strip() == "·  · 2026-10-27T10:00:00+00:00 ·"


def test_a_note_filed_through_the_gate_is_readable(skills, capsys):
    assert _note(tag="COSTLY", text="lost 20 minutes to the cwd guard")["ok"]
    coo_field_notes.main(["list"])
    line = capsys.readouterr().out.strip()
    assert line.startswith("ALL_Rules_Approvals · COSTLY · 20") and line.endswith(" · lost 20 minutes to the cwd guard")


# --------------------------------------------------------------------------- the SQL guard for both kinds

def _sql_block(kind: str) -> str:
    sql = SQL.read_text()
    start = sql.index(f"IF NEW.kind = '{kind}' THEN")
    return sql[start:sql.index("RETURN NEW;", start)]


def test_sql_audit_block_matches_the_gate():
    b = _sql_block("coo_audit")
    assert "NEW.task_id IS NOT NULL OR NEW.actor IS DISTINCT FROM 'coo_gate'" in b
    assert "ARRAY['input', 'ok', 'session_id', 'tool']" in b
    for field, kind in (("session_id", "string"), ("tool", "string"), ("input", "string"), ("ok", "boolean")):
        assert f"jsonb_typeof(NEW.payload::jsonb -> '{field}') IS DISTINCT FROM '{kind}'" in b
    assert f"->> 'input'), 2001) > {coo_gate.MAX_AUDIT_INPUT}" in b
    assert f"->> 'tool'), 0) NOT BETWEEN 1 AND {coo_gate.MAX_AUDIT_TOOL}" in b
    assert "->> 'session_id'), 0) NOT BETWEEN 1 AND 64" in b


def test_sql_field_note_block_matches_the_gate():
    b = _sql_block("coo_field_note")
    assert "NEW.task_id IS NOT NULL OR NEW.actor IS DISTINCT FROM 'coo_gate'" in b
    assert "ARRAY['session_id', 'skill', 'tag', 'text']" in b
    for field in ("session_id", "skill", "tag", "text"):
        assert f"jsonb_typeof(NEW.payload::jsonb -> '{field}') IS DISTINCT FROM 'string'" in b
    m = re.search(r"\(NEW\.payload::jsonb ->> 'tag'\) IN \(([^)]*)\)", b)
    assert m and tuple(re.findall(r"'([A-Z]+)'", m.group(1))) == coo_gate.FIELD_NOTE_TAGS
    m = re.search(r"'\^(\[[^']*\]\{3,80\})\$'", b)
    assert m and m.group(1).replace("\\", "") == coo_gate.SKILL_NAME.pattern.replace("\\", "")
    assert f"->> 'text'), 0) NOT BETWEEN 1 AND {coo_gate.MAX_FIELD_NOTE}" in b
    assert "position(E'\\n' IN" in b and "position(E'\\r' IN" in b


def test_sql_grants_and_privilege_list_are_unchanged_by_the_two_kinds():
    sql = SQL.read_text()
    assert sql.count("ON events TO org_coo") == 1                      # the one INSERT grant, no SELECT
    assert "GRANT INSERT (task_id, actor, kind, payload, ts) ON events TO org_coo;" in sql
    assert "coo_audit" not in sql.split("CREATE OR REPLACE VIEW coo_respawn_events")[1].split("GRANT SELECT ON coo_respawn_events")[0]
    assert "('coo_audit'" not in sql.split("-- 5. Row guards")[0]
    assert "events.payload:INSERT" in sql and "events.id" not in sql.split("want text :=")[1].split(";")[0]
    # section 6 proves both directions for both kinds
    proof = sql.split("FOR proof_kind")[1].split("END LOOP")[0]
    for kind in ("coo_audit", "coo_field_note"):
        assert proof.count(f"('{kind}', 'coo_gate',") == 2 and proof.count(f"('{kind}', 'someone_else',") == 1
    assert "true)" in proof and "false)" in proof
