"""P3-E, Agents-Core half: tools/portfolio_push.py and the live-sessions loop's PortfolioPush.

No hub, no Console, no Infisical: build_payload and the opener are faked, the loop's subprocess
is a fake Popen, and the two end-to-end tests talk to a throwaway HTTP server on 127.0.0.1.
Console's answers are the ones MoonieX-Console PR #34 returns: 204, or 400, 401, 413, 503.
"""
from __future__ import annotations

import io
import json
import sys
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import live_sessions as ls  # noqa: E402
from tools import portfolio_push as pp  # noqa: E402

PAYLOAD = json.loads((ROOT / "docs" / "plans" / "fixtures" / "portfolio-monitor-v1.json").read_text())
TOKEN = "pushtok-7d41c9e2b6a5f08e"
DEFAULT_ENDPOINT = "https://terminal.mooniex.com/api/portfolio/monitor"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PORTFOLIO_PUSH_TOKEN", TOKEN)
    monkeypatch.delenv("PORTFOLIO_PUSH_URL", raising=False)


class FakeOpener:
    """Stands in for pp._OPENER: records the request, answers or raises what it is given."""

    def __init__(self, status=204, exc=None):
        self.status, self.exc, self.calls = status, exc, []

    def open(self, req, timeout=None):
        self.calls.append((req, timeout))
        if self.exc is not None:
            raise self.exc
        if self.status >= 300:
            raise urllib.error.HTTPError(req.full_url, self.status, "x", {}, io.BytesIO(b"SECRET-BODY"))
        return _Resp(self.status)


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def wired(monkeypatch):
    """A payload that builds and an opener that answers 204; tests swap either."""
    opener = FakeOpener()
    monkeypatch.setattr(pp, "_OPENER", opener)
    monkeypatch.setattr(pp, "build_payload", lambda: PAYLOAD)
    return opener


def run(capsys) -> tuple[int, str]:
    rc = pp.main()
    out = capsys.readouterr()
    assert out.out == ""
    return rc, out.err


# --- the CLI -------------------------------------------------------------------

def test_a_good_push_posts_the_payload_with_the_right_headers(wired, capsys):
    rc, err = run(capsys)
    assert rc == 0
    (req, timeout), = wired.calls
    assert (req.full_url, req.get_method(), timeout) == (DEFAULT_ENDPOINT, "POST", 10)
    assert req.get_header("Authorization") == f"Bearer {TOKEN}"
    assert req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == PAYLOAD
    assert req.get_header("User-agent").startswith("mooniex-agents-portfolio-push")
    assert err == f"portfolio_push: ok 204, {len(PAYLOAD['projects'])} projects, {len(req.data)} bytes\n"
    assert TOKEN not in err


def test_the_url_comes_from_the_environment_and_a_trailing_slash_is_dropped(wired, monkeypatch, capsys):
    monkeypatch.setenv("PORTFOLIO_PUSH_URL", "https://console.example.test/")
    assert run(capsys)[0] == 0
    assert wired.calls[0][0].full_url == "https://console.example.test/api/portfolio/monitor"


def test_an_unset_token_exits_2_and_neither_builds_nor_sends(monkeypatch, capsys):
    monkeypatch.delenv("PORTFOLIO_PUSH_TOKEN")
    opener = FakeOpener()
    monkeypatch.setattr(pp, "_OPENER", opener)
    built = []
    monkeypatch.setattr(pp, "build_payload", lambda: built.append(1) or PAYLOAD)
    rc, err = run(capsys)
    assert (rc, opener.calls, built) == (2, [], [])
    assert err == "portfolio_push: PORTFOLIO_PUSH_TOKEN is unset, nothing sent\n"


@pytest.mark.parametrize("token", ["", "   ", "two words", "tok\nX-Evil: 1", "tökén"])
def test_an_empty_or_malformed_token_exits_2_and_is_never_echoed(token, wired, monkeypatch, capsys):
    monkeypatch.setenv("PORTFOLIO_PUSH_TOKEN", token)
    rc, err = run(capsys)
    assert (rc, wired.calls) == (2, [])
    assert token.strip() == "" or token not in err


@pytest.mark.parametrize("url", ["http://console.example.test", "ftp://x/y", "file:///etc/passwd", "terminal.mooniex.com", ""])
def test_a_url_that_would_carry_the_token_in_the_clear_exits_2(url, wired, monkeypatch, capsys):
    monkeypatch.setenv("PORTFOLIO_PUSH_URL", url)
    rc, err = run(capsys)
    if url == "":       # empty = unset = the default
        assert rc == 0
    else:
        assert (rc, wired.calls) == (2, [])
        assert TOKEN not in err


def test_the_hub_being_down_exits_3_sends_nothing_and_logs_the_class_only(wired, monkeypatch, capsys):
    from lib.db_pg import HubConnectError

    def down():
        raise HubConnectError("ORG_DB_URL points at 10.0.0.9 but it is unreachable: password=hunter2")
    monkeypatch.setattr(pp, "build_payload", down)
    rc, err = run(capsys)
    assert (rc, wired.calls) == (3, [])
    assert err == "portfolio_push: no payload (HubConnectError), nothing sent\n"


def test_no_org_db_url_is_the_same_exit_3_and_sends_nothing(monkeypatch, capsys):
    """The real build_payload, no ORG_DB_URL (tests/conftest.py clears it): PortfolioError."""
    opener = FakeOpener()
    monkeypatch.setattr(pp, "_OPENER", opener)
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    rc, err = run(capsys)
    assert (rc, opener.calls) == (3, [])
    assert "PortfolioError" in err


@pytest.mark.parametrize("status,why", [
    (400, "payload rejected"), (401, "token rejected"), (413, "payload too large"),
    (503, "console is stale or its hub is down"), (500, None), (302, None)])
def test_an_http_error_exits_4_and_neither_the_body_nor_the_token_is_logged(status, why, wired, capsys):
    wired.status = status
    rc, err = run(capsys)
    assert rc == 4
    assert err == f"portfolio_push: HTTP {status}" + (f" ({why})" if why else "") + "\n"
    assert "SECRET-BODY" not in err and TOKEN not in err


def test_a_success_status_other_than_204_is_not_a_success(wired, capsys):
    """A 200 is a catch-all page answering for a route that is not there."""
    wired.status = 200
    rc, err = run(capsys)
    assert (rc, err) == (4, "portfolio_push: HTTP 200, expected 204\n")


@pytest.mark.parametrize("exc", [urllib.error.URLError("dns failed for secret.internal"), TimeoutError("timed out"),
                                 ConnectionResetError("peer reset")])
def test_console_unreachable_exits_4_and_names_the_class_only(exc, wired, capsys):
    wired.exc = exc
    rc, err = run(capsys)
    assert rc == 4
    assert err == f"portfolio_push: console unreachable ({type(exc).__name__})\n"


class _Console(BaseHTTPRequestHandler):
    seen: list = []
    reply: tuple = (204, None)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        type(self).seen.append((self.path, dict(self.headers), self.rfile.read(n)))
        code, location = type(self).reply
        self.send_response(code)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):       # where urllib sends a redirected POST (302/303) if it is allowed to follow
        type(self).seen.append((self.path, dict(self.headers), b""))
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture
def console(monkeypatch):
    handler = type("H", (_Console,), {"seen": [], "reply": (204, None)})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("PORTFOLIO_PUSH_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(pp, "build_payload", lambda: PAYLOAD)
    yield handler
    server.shutdown()
    server.server_close()


def test_over_a_real_socket_the_server_sees_the_post_the_bearer_and_the_body(console, capsys):
    rc, err = run(capsys)
    assert rc == 0
    (path, headers, body), = console.seen
    assert path == "/api/portfolio/monitor"
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert headers["Content-Type"] == "application/json"
    assert json.loads(body) == PAYLOAD


def test_a_redirect_is_an_answer_and_is_never_followed_with_the_token(console, capsys):
    console.reply = (302, "/elsewhere")     # urllib turns a 302'd POST into a GET and keeps Authorization
    rc, err = run(capsys)
    assert (rc, err) == (4, "portfolio_push: HTTP 302\n")
    assert [p for p, _, _ in console.seen] == ["/api/portfolio/monitor"]


# --- the loop wrapper ----------------------------------------------------------

class FakeProc:
    """A child that exits with `rc` once `done` is set (rc None = still running)."""

    def __init__(self, rc=0, stderr=b""):
        self.rc, self.stderr, self.killed = rc, io.BytesIO(stderr), False

    def poll(self):
        return -9 if self.killed else self.rc

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        return self.poll()


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make(procs, monkeypatch=None, **kw):
    """A PortfolioPush whose spawns hand out `procs` in order; returns (push, spawns, said, clock)."""
    spawns, said, clock = [], [], Clock()

    def popen(argv, **kwargs):
        spawns.append((argv, kwargs))
        return procs[len(spawns) - 1]
    push = ls.PortfolioPush(["run"], cwd=ROOT, report=said.append, popen=popen, clock=clock, **kw)
    return push, spawns, said, clock


def advance(push, clock, seconds, step=5):
    for _ in range(seconds // step):
        clock.t += step
        push.tick()


def test_one_push_a_minute_and_a_clean_run_says_nothing():
    push, spawns, said, clock = make([FakeProc(0) for _ in range(5)])
    push.tick()
    assert len(spawns) == 1
    advance(push, clock, 55)
    assert len(spawns) == 1 and said == []      # reaped, but the minute is not up
    advance(push, clock, 5)
    assert len(spawns) == 2
    advance(push, clock, 120)
    assert len(spawns) == 4 and said == []


def test_at_most_one_push_is_in_flight():
    slow = FakeProc(rc=None)
    push, spawns, said, clock = make([slow, FakeProc(0)])
    push.tick()
    advance(push, clock, 25)                     # past the minute? no, but also still running
    assert len(spawns) == 1 and push.proc is slow and not slow.killed
    clock.t += 40                                # the minute is up, the old push is 70 s old
    push.tick()
    assert slow.killed and len(spawns) == 2 and said == ["portfolio push timed out after 30s"] and push.proc is not slow


def test_a_push_that_outlives_the_timeout_is_killed_and_reported():
    slow = FakeProc(rc=None)
    push, spawns, said, clock = make([slow])
    push.tick()
    advance(push, clock, 30)
    assert not slow.killed and said == []
    advance(push, clock, 5)
    assert slow.killed and push.proc is None
    assert said == ["portfolio push timed out after 30s"]


def test_the_child_gets_the_loops_environment_so_org_db_url_reaches_it(monkeypatch):
    monkeypatch.setenv("ORG_DB_URL", "postgresql://hub.example.test/db")
    push, spawns, said, clock = make([FakeProc(0)])
    push.tick()
    argv, kw = spawns[0]
    assert kw["env"]["ORG_DB_URL"] == "postgresql://hub.example.test/db"
    assert kw["cwd"] == str(ROOT) and kw["start_new_session"] is True


def test_the_argv_is_infisical_run_on_console_prod_then_the_push_script():
    argv = ls.push_argv(ROOT)
    assert argv[1].endswith("tools/infisical_setup.py")
    assert argv[2:6] == ["run", "MoonieX-Console", "prod", "--"]
    assert argv[0] == argv[6]
    assert argv[7].endswith("tools/portfolio_push.py") and len(argv) == 8
    assert (ROOT / "tools" / "infisical_setup.py").is_file() and (ROOT / "tools" / "portfolio_push.py").is_file()


@pytest.mark.parametrize("rc,label", [(2, "not configured"), (3, "hub unreachable"),
                                      (4, "console refused or unreachable"), (1, "failed")])
def test_a_failed_push_is_reported_once_with_its_exit_meaning(rc, label):
    push, spawns, said, clock = make([FakeProc(rc, b"portfolio_push: HTTP 401 (token rejected)\n")])
    push.tick()
    advance(push, clock, 5)
    assert said == [f"portfolio push exit {rc} ({label}): HTTP 401 (token rejected)"]


def test_only_the_childs_own_line_is_forwarded_never_the_rest_of_its_output():
    noisy = (b"[infisical run] MoonieX-Console/prod as contabo: A, PORTFOLIO_PUSH_TOKEN -> python\n"
             b"Traceback ... token=hunter2\n"
             b"portfolio_push: no payload (HubConnectError), nothing sent\x1b[31m\n")
    push, spawns, said, clock = make([FakeProc(3, noisy)])
    push.tick()
    advance(push, clock, 5)
    assert len(said) == 1
    assert said[0].startswith("portfolio push exit 3 (hub unreachable): no payload (HubConnectError)")
    assert "hunter2" not in said[0] and "infisical" not in said[0] and "\x1b" not in said[0]


def test_a_failure_without_an_own_line_still_reports_the_exit_code():
    push, spawns, said, clock = make([FakeProc(1, b"Infisical API error: 403 whatever the body said\n")])
    push.tick()
    advance(push, clock, 5)
    assert said == ["portfolio push exit 1 (failed)"]


def test_recovery_is_reported_once_so_a_later_failure_logs_again():
    push, spawns, said, clock = make([FakeProc(4), FakeProc(0), FakeProc(0)])
    push.tick()
    advance(push, clock, 60)
    assert said == ["portfolio push exit 4 (console refused or unreachable)"]
    advance(push, clock, 65)
    assert said[1:] == ["portfolio push ok again"]


def test_a_spawn_that_raises_is_swallowed_reported_and_retried_next_minute():
    calls = []

    def popen(argv, **kw):
        calls.append(1)
        raise FileNotFoundError("/no/such/python")
    said, clock = [], Clock()
    push = ls.PortfolioPush(["run"], report=said.append, popen=popen, clock=clock)
    push.tick()                                  # must not raise
    advance(push, clock, 30)
    assert calls == [1] and said == ["portfolio push error (FileNotFoundError)"]
    advance(push, clock, 30)
    assert len(calls) == 2


def test_a_report_callback_that_raises_does_not_break_the_loop():
    def boom(what):
        raise RuntimeError("log disk full")
    push, spawns, _, clock = make([FakeProc(4), FakeProc(0)])
    push.report = boom
    push.tick()
    advance(push, clock, 65)
    assert len(spawns) == 2


def test_a_proc_whose_poll_raises_is_swallowed():
    class Bad(FakeProc):
        def poll(self):
            raise OSError("gone")
    push, spawns, said, clock = make([Bad(0)])
    push.tick()
    push.tick()                                  # reaping raises inside tick: swallowed
    assert said == ["portfolio push error (OSError)"] and push.proc is None


def test_close_kills_an_in_flight_push():
    slow = FakeProc(rc=None)
    push, spawns, said, clock = make([slow])
    push.tick()
    push.close()
    assert slow.killed and push.proc is None
    push.close()                                 # twice is fine


# --- gated to Contabo, wired into the publisher --------------------------------

@pytest.mark.parametrize("host,expect", [("contabo", True), ("mac", False), ("winbox", False), ("", False),
                                         ("Contabo", False), ("contabo2", False)])
def test_only_the_hub_host_pushes(host, expect):
    assert ls.push_enabled(host) is expect
    assert (ls.make_push(host) is not None) is expect


def test_publish_loop_starts_a_push_only_on_contabo(monkeypatch, tmp_path):
    built = []

    class Spy:
        def __init__(self, url, host, dirs, **kw):
            built.append((host, kw.get("push")))

        def run(self):
            return 0

    class Cfg:
        def __init__(self, host):
            self.host = host

        def self_host(self):
            return self.host

        def hosts(self):
            return {self.host: {}}

    monkeypatch.setattr(ls, "Publisher", Spy)
    monkeypatch.setattr(ls, "session_dirs", lambda host: [tmp_path])
    args = type("A", (), {"once": False})()
    for host in ("mac", "winbox", "contabo"):
        monkeypatch.setattr(ls, "_config", lambda h=host: Cfg(h))
        assert ls._cmd_publish(args) == 0
    pushes = {host: push for host, push in built}
    assert pushes["mac"] is None and pushes["winbox"] is None
    assert isinstance(pushes["contabo"], ls.PortfolioPush)


class _Hub:
    class _R:
        def fetchall(self):
            return []

    def execute(self, sql, params=()):
        return self._R()

    def commit(self):
        pass

    def close(self):
        pass


def _hold(tmp_path, push, steps=30):
    class Stop(threading.Event):
        n = 0

        def wait(self, timeout=None):
            Stop.n += 1
            if Stop.n >= steps:
                self.set()
            return self.is_set()
    stop = Stop()
    pub = ls.Publisher("postgresql://u@h/db", "contabo", [tmp_path], stop=stop, lock_path=tmp_path / "l",
                       connect=lambda url: _Hub(), push=push)
    return pub, stop


def test_the_publisher_ticks_the_push_every_poll_and_a_dead_push_never_stops_publishing(tmp_path, monkeypatch):
    published = []
    monkeypatch.setattr(ls, "publish_once", lambda conn, host, dirs, prev: published.append(1) or set())
    ticks = []

    class Push:
        def tick(self):
            ticks.append(1)

        def close(self):
            ticks.append("closed")
    pub, stop = _hold(tmp_path, Push())
    assert pub.run() == 0
    assert ticks.count(1) == 30 and ticks[-1] == "closed"       # one per 5 s poll, closed on the way out
    assert published                                            # publishing went on beside it


def test_a_real_push_runner_with_a_crashing_child_leaves_the_publisher_running(tmp_path, monkeypatch):
    published = []
    monkeypatch.setattr(ls, "publish_once", lambda conn, host, dirs, prev: published.append(1) or set())
    clock = Clock()
    monkeypatch.setattr(ls.time, "monotonic", clock)
    reports = []
    procs = iter([FakeProc(4, b"portfolio_push: HTTP 401 (token rejected)\n") for _ in range(10)])
    push = ls.PortfolioPush(["run"], report=reports.append, popen=lambda argv, **kw: next(procs), clock=clock)

    class Stop(threading.Event):
        n = 0

        def wait(self, timeout=None):
            Stop.n += 1
            clock.t += timeout
            if Stop.n >= 40:
                self.set()
            return self.is_set()
    errors = []
    pub = ls.Publisher("postgresql://u@h/db", "contabo", [tmp_path], stop=Stop(), lock_path=tmp_path / "l",
                       connect=lambda url: _Hub(), push=push, on_error=errors.append)
    assert pub.run() == 0
    assert errors == []                          # the publisher itself saw no failure
    assert len(published) >= 3                   # a heartbeat each minute went out
    assert set(reports) == {"portfolio push exit 4 (console refused or unreachable): HTTP 401 (token rejected)"}
    assert len(reports) >= 3                     # a push a minute, each one failing, none of it fatal


def test_a_publisher_without_push_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "publish_once", lambda conn, host, dirs, prev: set())
    pub, stop = _hold(tmp_path, None, steps=3)
    assert pub.run() == 0 and pub.push is None
