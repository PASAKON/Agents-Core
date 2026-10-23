"""Synthetic data only; all IO to services is replaced by in-process fakes."""
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

from tools import sompong_reminders as r

NOW = datetime(2026, 10, 30, 2, tzinfo=timezone.utc)
ENV = dict(SUPABASE_URL="https://example.invalid", SUPABASE_SECRET_KEY="synthetic-secret",
           LUNGNOTE_USER_ID="synthetic-user", SOMPONG_EA_WAKE_KEY="synthetic-wake-secret")


class Harness:
    def __init__(self, tmp_path):
        self.path = tmp_path / "ledger.jsonl"
        self.todos = []
        self.wakes = []
        self.patches = []
        self.requests = []
        self.result = 202
        self.fail_patch = False
        self.now = NOW

    def add(self, text="[SomPong] Send a synthetic reminder to the test chat", due=NOW, **kwargs):
        todo = dict(id=f"todo-{len(self.todos)}", text=text, due_at=due.isoformat(), done=False, **kwargs)
        self.todos.append(todo)
        return todo

    def fetch(self, req):
        self.requests.append(req)
        if req.get_method() == "GET":
            return self.todos
        self.patches.append(req)
        if self.fail_patch:
            raise r.HubError("synthetic patch failure")
        query = parse_qs(urlsplit(req.full_url).query)
        for todo in self.todos:
            if query["id"] == ["eq." + todo["id"]]:
                todo.update(json.loads(req.data))
                return [todo]
        return []

    def post(self, body):
        self.wakes.append(body)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def run(self, **kwargs):
        r.run_pass(now=self.now, env=ENV, fetch=self.fetch, post=self.post, ledger=self.path, **kwargs)

    def rows(self):
        return list(r.Ledger(self.path).rows.values())


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def test_filters(h):
    h.add("[SomPong · CEO] synthetic instruction")
    h.add("[SomPong] synthetic instruction")
    h.add("[SomeoneElse] synthetic instruction")
    h.add(due=NOW + timedelta(seconds=1))
    h.add(status="cancelled")
    h.add(status="done")
    h.add()["done"] = True
    h.run()
    assert len(h.wakes) == 2
    query = parse_qs(urlsplit(h.requests[0].full_url).query)
    assert query["text"] == ["like.*[SomPong*"]
    assert "cancelled" in query["or"][0]


@pytest.mark.parametrize("age,expired", [(72, False), (72.001, True)])
def test_one_shot_expiry(h, age, expired):
    h.add(due=NOW - timedelta(hours=age))
    h.run()
    h.run()
    assert len(h.wakes) == (0 if expired else 1)
    assert h.rows()[0]["status"] == ("expired" if expired else "accepted")


def test_expired_repeat_moves_after_now(h):
    todo = h.add("[SomPong] repeat:last-1,last@09:00 synthetic", NOW - timedelta(days=100))
    h.run()
    assert not h.wakes
    assert todo["due_at"] == "2026-10-31T09:00:00+07:00"
    assert set(json.loads(h.patches[0].data)) == {"due_at", "due_text"}


@pytest.mark.parametrize("seconds,late", [(0, False), (300, False), (301, True)])
def test_payload(h, seconds, late):
    todo = h.add(due=NOW - timedelta(seconds=seconds))
    h.run()
    body = h.wakes[0]
    for name in ("event_id", "message_id", "sender_id"):
        assert r.ID_RE.fullmatch(body[name])
    assert body["role"] == "reminder"
    assert body["event_id"] == r.event_key(todo["id"], r.parse_date(todo["due_at"]))
    assert (" · ช้า " in body["text"]) is late
    assert body["ts"] == int(NOW.timestamp())
    assert body["text"].endswith(todo["text"])
    assert len(body["text"]) <= 20000


@pytest.mark.parametrize("result,status,count", [(202, "accepted", 1), (422, "rejected:422", 1),
    (400, "rejected:400", 1), (413, "rejected:413", 1), (503, None, 2),
    (ConnectionError("synthetic"), None, 2), (TimeoutError(), None, 2)])
def test_results_and_restart(h, result, status, count):
    h.add()
    h.result = result
    h.run()
    h.run()  # Each pass reloads the persisted ledger, just as a new process does.
    assert len(h.wakes) == count
    assert [row["status"] for row in h.rows()] == ([] if status is None else [status])


def test_moved_due_fires_again(h):
    todo = h.add()
    h.run()
    todo["due_at"] = (NOW + timedelta(minutes=2)).isoformat()
    h.now += timedelta(minutes=2)
    h.run()
    assert len({body["event_id"] for body in h.wakes}) == 2


@pytest.mark.parametrize("token,after,expected", [
    ("10,15", "2026-10-10", "2026-10-15"), ("10,15", "2026-10-15", "2026-11-10"),
    ("last-1,last", "2024-02-27", "2024-02-28"), ("last-1,last", "2024-02-28", "2024-02-29"),
    ("last-1,last", "2025-02-26", "2025-02-27"), ("last-1,last", "2025-02-27", "2025-02-28"),
    ("last-1,last", "2026-04-28", "2026-04-29"), ("last-1,last", "2026-04-29", "2026-04-30"),
    ("last-1,last", "2026-10-29", "2026-10-30"), ("last-1,last", "2026-10-30", "2026-10-31"),
    ("last-1,last", "2026-12-31", "2027-01-30"), ("31", "2026-03-31", "2026-05-31"),
])
def test_next_occurrence(token, after, expected):
    rule = r.repeat_rule("repeat:" + token + "@09:00")
    assert r.next_occurrence(rule, r.parse_date(after + "T09:00:00+07:00")) == r.parse_date(expected + "T09:00:00+07:00")


def test_patch_retry_without_wake(h):
    h.add("[SomPong] repeat:last-1,last@09:00 synthetic")
    h.fail_patch = True
    h.run()
    assert h.rows()[0]["status"] == "accepted"
    h.now += timedelta(days=5)
    h.fail_patch = False
    h.run()
    assert len(h.wakes) == 1
    assert len(h.patches) == 2
    assert json.loads(h.patches[1].data)["due_at"] == "2026-10-31T09:00:00+07:00"


@pytest.mark.parametrize("token", ["repeat:0@09:00", "repeat:32@09:00", "repeat:10@24:00", "repeat:bad", "repeat:10@09:00x"])
def test_bad_repeat_once(h, caplog, token):
    h.add("[SomPong] " + token)
    h.result = 503
    h.run()
    h.run()
    assert caplog.text.count("status=invalid-repeat") == 1
    assert not h.patches


def test_no_text_or_credentials_in_output(h, caplog, capsys):
    todo = h.add("[SomPong] PRIVATE_SYNTHETIC_TEXT")
    h.run(dry_run=True)
    assert not h.path.exists() and not h.wakes and not h.patches
    h.run()
    output = caplog.text + capsys.readouterr().out + h.path.read_text()
    for secret in (todo["text"], ENV["SUPABASE_SECRET_KEY"], ENV["SOMPONG_EA_WAKE_KEY"]):
        assert secret not in output


@pytest.mark.parametrize("field,value,status", [("id", "bad\nid", "rejected:422"),
    ("id", "a" * 128, "rejected:422"), ("text", "[SomPong]" + "x" * 20000, "rejected:413")])
def test_invalid_payload_rejected_locally(h, field, value, status):
    h.add()[field] = value
    h.run()
    h.run()
    assert not h.wakes
    assert h.rows()[0]["status"] == status


def test_infisical_nested_environment(monkeypatch):
    from tools import infisical_setup as inf
    class FakeOrg:
        def __init__(self, identity):
            pass
        def get(self, *args, **kwargs):
            return {"secrets": [{"secretKey": "SOMPONG_EA_WAKE_KEY", "secretValue": "synthetic-wake-secret"}]}
    monkeypatch.setattr(inf, "Org", FakeOrg)
    monkeypatch.setattr(inf, "_project", lambda *args: {"id": "synthetic", "name": "synthetic"})
    monkeypatch.setattr(inf, "_is_nt", lambda: False)
    for key, value in ENV.items():
        if key != "SOMPONG_EA_WAKE_KEY":
            monkeypatch.setenv(key, value)
    captured = []
    monkeypatch.setattr(inf.os, "execvpe", lambda exe, argv, env: captured.append(env))
    inf.cmd_run("contabo", "synthetic", "prod", ["synthetic-child"])
    assert all(captured[0][key] == value for key, value in ENV.items())


def test_expired_patch_failure_retries_without_wake(h):
    h.add("[SomPong] repeat:10,15@09:00 synthetic", NOW - timedelta(days=100))
    h.fail_patch = True
    h.run()
    h.fail_patch = False
    h.run()
    assert not h.wakes
    assert len(h.patches) == 2
    assert h.todos[0]["due_at"] == "2026-11-10T09:00:00+07:00"


def test_pagination(h):
    for _ in range(501):
        h.add()
    requests = []
    def fetch(req):
        query = parse_qs(urlsplit(req.full_url).query)
        offset = int(query["offset"][0])
        requests.append(offset)
        return h.todos[offset:offset + 500]
    r.run_pass(now=NOW, env=ENV, fetch=fetch, post=h.post, ledger=h.path)
    assert requests == [0, 500]
    assert len(h.wakes) == 501


def test_wake_transport(monkeypatch, h):
    captured = []
    class Response:
        status = 202
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    class Opener:
        def open(self, req, timeout):
            captured.append(req)
            assert timeout == 15
            return Response()
    monkeypatch.setattr(r.urllib.request, "build_opener", lambda *args: Opener())
    body = r.payload(h.add(), NOW, NOW)
    assert r.wake(body, ENV) == 202
    req = captured[0]
    assert req.full_url == "http://172.18.0.1:8644/v1/wake"
    assert req.get_header("Authorization") == "Bearer synthetic-wake-secret"
    assert json.loads(req.data) == body
