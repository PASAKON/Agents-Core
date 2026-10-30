"""tools/email_ceo.py — the only way a session emails the CEO (CEO 2026-10-02, skill ALL_Protocol_EmailCEO).

What must hold: only a C-level session can send, only the four kinds, a secret never leaves the box,
the hub's refusals (caps, duplicates) come back as a refusal the agent can read, and the deadline
feeder turns his LungNote to-dos into kind=deadline rows. A local fake stands in for the hub; nothing
here reaches the Console, LungNote or Google.

Run: .venv/bin/python -m pytest tests/test_email_ceo.py
"""
from __future__ import annotations

import json
import threading
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
from types import SimpleNamespace
import io
import os
import pwd
import subprocess
import urllib.error

import pytest

from tools import email_ceo
from lib.ceo_text import check_ceo_text, ceo_lines

CTO_ENV = {"CXO_ROLE": "cto", "CXO_SESSION_ID": "e106b78b", "ORG_MACHINE": "contabo"}
ACTION = {"title": "อนุมัติเครดิต Flow 300 สำหรับ EP3", "need": "ตอบ อนุมัติ/ไม่", "why": "script ผ่านแล้ว",
          "link": "https://terminal.mooniex.com/s/cto-e106b78b", "ref": "ep3-credits"}


def test_payload_takes_role_session_machine_from_env_and_drops_empty_fields():
    body = email_ceo.build_payload({**ACTION, "if_not": "", "due": None}, kind="ACTION", env=CTO_ENV)
    assert body == {"kind": "action", "role": "cto", "session": "cto-e106b78b", "machine": "contabo", **ACTION}


@pytest.mark.parametrize("kind, env, match", [
    ("fyi", CTO_ENV, "kind must be one of"),
    ("action", {"WORKER_TASK_ID": "task-12345678", "WORKER_ROLE": "developer"}, "worker never mails"),
    ("action", {"CXO_ROLE": "developer", "CXO_SESSION_ID": "x1"}, "C-level only"),
])
def test_who_and_what_is_refused_before_any_network_call(kind, env, match):
    with pytest.raises(email_ceo.Refused, match=match):
        email_ceo.build_payload(ACTION, kind=kind, env=env)


def test_a_secret_shaped_value_is_refused_without_echoing_it():
    value = "ghp_" + "a" * 36
    with pytest.raises(email_ceo.Refused) as e:
        email_ceo.build_payload({**ACTION, "why": f"token={value}"}, kind="action", env=CTO_ENV)
    assert value not in str(e.value)


# ------------------------------------------------------------------ the hub round trip
class FakeHub(BaseHTTPRequestHandler):
    answers: list = []
    seen: list = []

    def do_POST(self):  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("content-length", 0)))
        FakeHub.seen.append({"path": self.path, "auth": self.headers.get("authorization"),
                             "session": self.headers.get("x-run-session"), "body": json.loads(raw)})
        status, payload = FakeHub.answers.pop(0)
        out = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):  # quiet
        pass


@pytest.fixture
def hub(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeHub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeHub.answers, FakeHub.seen = [], []
    monkeypatch.setenv("RUN_INBOX_URL", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setenv("RUN_INBOX_TOKEN", "test-token-not-real")
    for k, v in CTO_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("WORKER_TASK_ID", raising=False)
    yield FakeHub
    server.shutdown()


def test_send_posts_the_body_with_the_token_and_session_header(hub):
    hub.answers.append((201, {"id": "N-1a2b", "mailed": True, "buzz": True, "quota": {"session_left": 2}}))
    got = email_ceo.send(ACTION, kind="action")
    assert got["id"] == "N-1a2b"
    (req,) = hub.seen
    assert req["path"] == "/api/notify/ceo"
    assert req["auth"] == "Bearer test-token-not-real" and req["session"] == "cto-e106b78b"
    assert req["body"]["kind"] == "action" and req["body"]["title"] == ACTION["title"]


def test_dry_run_asks_the_hub_to_render_only(hub):
    hub.answers.append((200, {"dry_run": True, "subject": "[ACTION][CTO] x — N-dry0"}))
    email_ceo.send(ACTION, kind="action", dry_run=True)
    assert hub.seen[0]["path"] == "/api/notify/ceo?dry_run=1"


@pytest.mark.parametrize("status, payload, match", [
    (409, {"error": "duplicate", "id": "N-0001", "hint": "the same kind + ref went out within 6 h"}, "duplicate; id=N-0001"),
    (429, {"error": "session_daily_cap", "cap": 3, "hint": "fold it into one mail"}, r"session_daily_cap; cap=3\): fold"),
    (400, {"error": "missing_field", "field": "need", "kind": "action"}, "missing_field; field=need"),
])
def test_a_hub_refusal_reads_as_a_refusal_with_its_reason(hub, status, payload, match):
    hub.answers.append((status, payload))
    with pytest.raises(email_ceo.Refused, match=match):
        email_ceo.send(ACTION, kind="action")


def test_a_hub_5xx_is_a_hub_error_and_the_cli_exits_3(hub, capsys):
    hub.answers.append((500, {"error": "internal"}))
    code = email_ceo.main(["send", "--kind", "action", "--title", "t", "--need", "n", "--why", "w",
                           "--link", "https://x.example"])
    assert code == 3
    assert "test-token-not-real" not in capsys.readouterr().err


def test_the_mcp_entry_runs_the_same_path(hub):
    hub.answers.append((201, {"id": "N-0002", "mailed": False}))
    got = email_ceo.mcp_send({"kind": "deadline", "title": "ยื่นภาษี", "due": "3 ต.ค.", "need": None})
    assert got["id"] == "N-0002"
    assert hub.seen[0]["body"]["due"] == "3 ต.ค." and "need" not in hub.seen[0]["body"]


def test_the_registry_serves_email_ceo():
    from lib import org_tools_registry as reg
    assert "email_ceo" in reg.BY_NAME and "C-level" in reg.BY_NAME["email_ceo"].description


# ------------------------------------------------------------------ deadline feeder
FEED_NOW = datetime(2026, 10, 3, 0, 50, tzinfo=timezone.utc)  # 07:50 Bangkok
LN_ENV = {"SUPABASE_URL": "https://ln.example", "SUPABASE_SECRET_KEY": "sb-not-real", "LUNGNOTE_USER_ID": "u1"}


def test_due_todos_asks_for_the_next_24_hours_only():
    seen = {}

    def fetch(req):
        seen["url"] = req.full_url
        seen["key"] = req.headers.get("Apikey")
        return []

    email_ceo.due_todos(FEED_NOW, LN_ENV, fetch)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(seen["url"]).query)
    assert q["due_at"] == ["gte.2026-10-03T00:50:00+00:00", "lte.2026-10-04T00:50:00+00:00"]
    assert q["done"] == ["eq.false"] and q["user_id"] == ["eq.u1"] and q["select"] == ["id,text,due_at,due_text"]
    assert seen["key"] == "sb-not-real"


def test_due_todos_without_creds_is_a_hub_error():
    with pytest.raises(email_ceo.HubError, match="LungNote-MCP"):
        email_ceo.due_todos(FEED_NOW, {}, lambda r: [])


def test_the_feeder_posts_one_deadline_per_todo_and_counts_duplicates():
    todos = [{"id": "t1", "text": "[SID:cto-1 · backlog] [FYI] ยื่นภาษี  ภ.ง.ด.90", "due_at": "2026-10-03T12:30:00+00:00"},
             {"id": "t2", "text": "x" * 120, "due_at": "2026-10-04T00:00:00Z"}]
    posted = []

    def post(body):
        posted.append(body)
        if body["ref"] == "todo:t2":
            raise email_ceo.Refused("hub refused (409: duplicate; id=N-0001)")
        return {"id": "N-0003"}

    out = email_ceo.feed_deadlines(now=FEED_NOW, env=LN_ENV, fetch=lambda r: todos, post=post)
    assert out == {"due": 2, "queued": 1, "duplicate": 1, "refused": []}
    first = posted[0]
    assert first["kind"] == "deadline" and first["session"] == "cto-deadline-feed" and first["role"] == "cto"
    assert first["title"] == "ยื่นภาษี ภ.ง.ด.90" and first["due"] == "03/10 19:30 น." and first["ref"] == "todo:t1"
    assert len(posted[1]["title"]) == 90


# --- shared LungNote transport (task-5dac9e4a, PR #435) ---
from urllib.parse import parse_qs, urlsplit  # noqa: E402

ENV = dict(SUPABASE_URL="https://example.invalid", SUPABASE_SECRET_KEY="synthetic-secret",
           LUNGNOTE_USER_ID="synthetic-user")


def test_due_todos_keeps_deadline_window():
    requests = []
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    assert email_ceo.due_todos(now, ENV, lambda req: requests.append(req) or []) == []
    query = parse_qs(urlsplit(requests[0].full_url).query)
    assert query["due_at"] == ["gte.2026-10-23T00:00:00+00:00", "lte.2026-10-24T00:00:00+00:00"]
    assert query["done"] == ["eq.false"]
    assert query["user_id"] == ["eq.synthetic-user"]
    assert query["limit"] == [str(email_ceo.FEED_MAX)]
    assert requests[0].get_method() == "GET"


def test_patch_transport():
    requests = []
    email_ceo.lungnote_request([("id", "eq.synthetic-todo")], ENV,
        lambda req: requests.append(req) or [], body={"due_at": "2026-11-01T09:00:00+07:00"})
    assert requests[0].get_method() == "PATCH"
    assert requests[0].get_header("Authorization") == "Bearer synthetic-secret"


NOW = datetime(2026, 10, 25, 18, tzinfo=timezone.utc)


def pr(repo="Agents-Core", number=447):
    return {"repository": {"nameWithOwner": f"PASAKON/{repo}"}, "number": number}


def runner_for(prs):
    def run(cmd, **kwargs):
        assert cmd == ["gh", "search", "prs", "--owner", "PASAKON", "--merged",
                       "--merged-at", "2026-10-24T18:00:00+00:00..2026-10-25T18:00:00+00:00",
                       "--limit", "1000", "--json", "number,repository"]
        assert kwargs["timeout"] == 60
        assert kwargs["check"] is True
        assert kwargs["env"]["HOME"] == pwd.getpwuid(os.getuid()).pw_dir
        return SimpleNamespace(stdout=json.dumps(prs))
    return run


def test_merged_grouping_and_ref(monkeypatch):
    posted = []
    monkeypatch.setattr(email_ceo, "_post", lambda body, **kw: posted.append(body) or {})
    result = email_ceo.feed_merged(now=NOW, env={}, runner=runner_for([
        pr(number=450), pr("Console", 7), pr(number=447), pr(number=448)]))
    assert result["sent"] == 1
    assert len(posted) == 1
    body = posted[0]
    assert body["kind"] == "done"
    assert body["ref"] == "merge-digest-2026-10-26"
    assert body["why"] == "Agents-Core 3: #447 #448 #450\nConsole 1: #7"
    assert body["title"] == "merge แล้ว 24 ชม.: 4 PR"
    assert urlsplit(body["link"]).netloc == "github.com"


@pytest.mark.parametrize("count", [0, 1, 3, 12])
def test_merged_limits(count, monkeypatch):
    posted = []
    monkeypatch.setattr(email_ceo, "_post", lambda body, **kw: posted.append(body) or {})
    prs = [pr("repository-" + str(i) + "x" * 80, n) for i in range(count) for n in range(1, 60)]
    result = email_ceo.feed_merged(now=NOW, env={}, runner=runner_for(prs))
    assert result["sent"] == bool(count)
    assert len(posted) == bool(count)
    if count:
        fields = [(k, posted[0].get(k)) for k in email_ceo.CEO_READS]
        check_ceo_text(fields)
        assert len(ceo_lines(fields)) <= 5
        assert all(len(line) <= 90 for key, line in ceo_lines(fields) if key != "link")
    if count == 12:
        assert posted[0]["why"].splitlines()[-1] == "+10 repo …"


def test_merged_duplicate_409(monkeypatch):
    class Opener:
        def open(self, req, **kwargs):
            raise urllib.error.HTTPError(req.full_url, 409, "Conflict", {},
                                         io.BytesIO(b'{"error":"duplicate"}'))
    monkeypatch.setattr(email_ceo.ask_run, "_OPENER", Opener())
    monkeypatch.setattr(email_ceo.ask_run, "load_token", lambda: "fake-token")
    monkeypatch.setattr(email_ceo.ask_run, "base_url", lambda: "https://example.invalid")
    assert email_ceo.feed_merged(now=NOW, env={}, runner=runner_for([pr()])) == {
        "sent": 1, "status": "already sent"}


@pytest.mark.parametrize("failure", [FileNotFoundError(), subprocess.CalledProcessError(1, "gh"),
                                      subprocess.TimeoutExpired("gh", 60), "bad json", "{}", "[{}]"])
@pytest.mark.parametrize("deadline_exit", [0, 2, 3])
def test_gh_failure_preserves_deadlines(monkeypatch, capsys, failure, deadline_exit):
    posted = []
    def run(*a, **kw):
        if isinstance(failure, Exception):
            raise failure
        return SimpleNamespace(stdout=failure)
    monkeypatch.setattr(email_ceo.subprocess, "run", run)
    monkeypatch.setattr(email_ceo, "due_todos", lambda *a: [{"id": "one", "text": "due", "due_at": ""}])
    def post(body, **kw):
        posted.append(body)
        if deadline_exit == 3:
            raise email_ceo.HubError("offline")
    monkeypatch.setattr(email_ceo, "_post", post)
    if deadline_exit == 2:
        monkeypatch.setattr(email_ceo, "deadline_fields", lambda todo: {"title": "x" * 91})
    assert email_ceo.main(["deadlines"]) == deadline_exit
    assert len(posted) == (deadline_exit != 2)
    assert all(body["kind"] == "deadline" for body in posted)
    assert capsys.readouterr().err.count("merged-digest unavailable; skipped") == 1


def test_no_merged(monkeypatch):
    monkeypatch.setattr(email_ceo, "feed_deadlines", lambda **kw: {"queued": 1})
    monkeypatch.setattr(email_ceo, "feed_merged", lambda **kw: pytest.fail("must skip gh"))
    assert email_ceo.main(["deadlines", "--no-merged"]) == 0


def test_dry_run_never_posts(monkeypatch, capsys):
    monkeypatch.setattr(email_ceo, "due_todos", lambda *a: [{"id": "one", "text": "due", "due_at": ""}])
    monkeypatch.setattr(email_ceo.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=json.dumps([pr()])))
    hub_dry_runs = []
    def post(body, *, dry_run=False):
        if not dry_run:
            pytest.fail("dry-run posted")
        hub_dry_runs.append(body["kind"])
        return {"ok": True}
    monkeypatch.setattr(email_ceo, "_post", post)
    assert email_ceo.main(["deadlines", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert hub_dry_runs == ["deadline"]
    assert 'merged-digest dry-run: {"kind": "done"' in output
    assert "Agents-Core 1: #447" in output


def test_imports_where_there_is_no_pwd(monkeypatch):
    """Windows has no pwd module, and lib.org_tools_registry imports this one on every host:
    a module-level `import pwd` made `cxo_mcp_config --print-allowed` exit 1, so every winbox
    launch from main stopped right after writing its lock (PH c73d0ce9, 30 Oct 2026)."""
    import importlib.util
    import sys
    monkeypatch.setitem(sys.modules, "pwd", None)  # `import pwd` now raises ImportError, as on Windows
    spec = importlib.util.spec_from_file_location("email_ceo_without_pwd", email_ceo.__file__)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.pwd is None
