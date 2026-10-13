"""tools/home_lock.py against a fake front-door Console on loopback: the same
routes and answers as MoonieX-Console src/relay/locks.js (docs/relay.md §12)."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tools import home_lock

TOKEN = "test-org-token-not-real"


class FakeFrontDoor:
    def __init__(self):
        self.locks: dict[str, dict] = {}
        self.calls: list[tuple[str, str, str]] = []
        self.not_front_door = False


@pytest.fixture
def hub(monkeypatch):
    state = FakeFrontDoor()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, status, body):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _auth(self):
            state.calls.append((self.command, self.path, self.headers.get("Authorization", "")))
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self._send(401, {"error": "unauthenticated"})
                return False
            if state.not_front_door:
                self._send(409, {"error": "not_front_door", "frontDoor": "https://front.example"})
                return False
            return True

        def do_GET(self):
            if self._auth() and self.path == "/api/relay/locks":
                self._send(200, {"locks": list(state.locks.values())})

        def do_POST(self):
            if not self._auth():
                return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            key, owner = body.get("key"), body.get("owner")
            cur = state.locks.get(key)
            if self.path == "/api/relay/locks/acquire":
                if cur and cur["owner"] != owner:
                    return self._send(409, {"ok": False, "holder": cur})
                lock = {"key": key, "owner": owner, "expiresAt": f"ttl+{body.get('ttl')}",
                        **({"purpose": body["purpose"]} if body.get("purpose") else {})}
                state.locks[key] = lock
                return self._send(200, {"ok": True, "lock": lock, "renewed": bool(cur)})
            if self.path == "/api/relay/locks/release":
                released = bool(cur and cur["owner"] == owner)
                if released:
                    del state.locks[key]
                return self._send(200, {"ok": True, "released": released})
            self._send(404, {})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("RUN_INBOX_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    monkeypatch.setenv("RUN_INBOX_TOKEN", TOKEN)
    for var in ("WORKER_TASK_ID", "CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "ORG_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    yield state
    srv.shutdown()


KEY = "home:winbox:9224"


def test_acquire_held_release(hub):
    lock = home_lock.acquire(KEY, "cto-685b012b", 900, "ChatGPT images")
    assert lock["owner"] == "cto-685b012b"
    with pytest.raises(home_lock.HomeLockHeld) as e:
        home_lock.acquire(KEY, "task-bbbb2222")
    assert e.value.holder["owner"] == "cto-685b012b"
    assert "ChatGPT images" in str(e.value)
    assert home_lock.release(KEY, "task-bbbb2222") is False   # only the owner releases
    assert home_lock.release(KEY, "cto-685b012b") is True
    assert home_lock.acquire(KEY, "task-bbbb2222")["owner"] == "task-bbbb2222"
    assert [lk["key"] for lk in home_lock.list_locks()] == [KEY]
    assert all(auth == f"Bearer {TOKEN}" for _, _, auth in hub.calls)


def test_context_manager_releases_on_error(hub):
    with pytest.raises(RuntimeError):
        with home_lock.home_lock(KEY, owner="cto-1", purpose="x") as held:
            assert hub.locks[KEY]["owner"] == "cto-1"
            held.renew(120)
            raise RuntimeError("job failed")
    assert KEY not in hub.locks


def test_owner_from_env(hub, monkeypatch):
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", "685b012b")
    assert home_lock.default_owner() == "cto-685b012b"
    monkeypatch.setenv("WORKER_TASK_ID", "task-abcd1234")
    assert home_lock.default_owner() == "task-abcd1234"
    assert home_lock.acquire(KEY)["owner"] == "task-abcd1234"


def test_bad_arguments_never_reach_the_hub(hub):
    for bad in (dict(key="winbox:9224", owner="x1"), dict(key=KEY, owner="a b"), dict(key=KEY, owner="x1", ttl=5),
                dict(key="home:winbox:70000", owner="x1"), dict(key="home:" + "a" * 25 + ":9224", owner="x1")):
        with pytest.raises(ValueError):
            home_lock.acquire(**bad)
    with pytest.raises(ValueError, match="owner"):
        home_lock.acquire(KEY)  # no owner given, none in env
    assert hub.calls == []


def test_a_console_that_is_not_the_front_door_says_where_it_is(hub):
    hub.not_front_door = True
    with pytest.raises(home_lock.HubError, match="front.example"):
        home_lock.acquire(KEY, "cto-1")


def test_cli_exit_codes(hub, capsys):
    assert home_lock.main(["acquire", KEY, "--owner", "cto-1", "--purpose", "images"]) == 0
    assert "held by cto-1" in capsys.readouterr().out
    assert home_lock.main(["acquire", KEY, "--owner", "cto-2"]) == 2
    assert "held by cto-1" in capsys.readouterr().err
    assert home_lock.main(["list"]) == 0
    assert KEY in capsys.readouterr().out
    assert home_lock.main(["release", KEY, "--owner", "cto-1"]) == 0


def test_unreachable_hub_is_exit_3(monkeypatch, capsys):
    monkeypatch.setenv("RUN_INBOX_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("RUN_INBOX_TOKEN", TOKEN)
    assert home_lock.main(["list"]) == 3
    err = capsys.readouterr().err
    assert "unreachable" in err and TOKEN not in err
