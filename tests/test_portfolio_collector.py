"""Collector contract against a loopback Console; no production hub or wakes."""
import contextlib
import http.client
import io
import json
import threading
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from lib import mailbox, portfolio
from tools import mail_wake, portfolio_delivery as delivery, portfolio_push as push


@pytest.fixture(params=["memory", "http"])
def console(tmp_path, monkeypatch, request):
    requests, wakes, unblocked = [], [], []
    pending = {"nudges": [], "messages": []}
    failures = {}
    token = "test-only-collector-token"
    monkeypatch.setattr(push, "COLLECTOR_STATE", tmp_path / "collector.json")
    monkeypatch.setattr(push, "COLLECTOR_OFF", tmp_path / "collector.off")
    monkeypatch.setattr(delivery, "ROOT", tmp_path)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setenv("ORG_LETTERS_META", str(tmp_path / "meta.jsonl"))
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    project = {"ph_session": "abcd1234", "lane": "cto", "blocker_on": "ceo"}
    monkeypatch.setattr(portfolio, "get_project", lambda pid: project)
    monkeypatch.setattr(portfolio, "unblock", lambda pid, **kw: unblocked.append((pid, kw)))
    live = {"project_head-abcd1234", "cto-fresh"}
    monkeypatch.setattr(delivery, "live_boxes", lambda: live)
    monkeypatch.setattr(mail_wake, "wake", lambda *args: wakes.append(args) or {"woke": True})

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            assert self.headers["Authorization"] == "Bearer " + token
            requests.append(("GET", self.path, None))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(pending[self.path.rsplit("/", 1)[1]]).encode())

        def do_POST(self):
            assert self.headers["Authorization"] == "Bearer " + token
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(("POST", self.path, body))
            code = failures.get(self.path, 200)
            self.send_response(code)
            self.end_headers()
            if code == 200 and self.path.endswith("/ack"):
                kind, nid = self.path.split("/")[3:5]
                pending[kind][:] = [p for p in pending[kind] if p["id"] != nid]

    server = None
    if request.param == "http":
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        except PermissionError:
            pytest.skip("sandbox disallows loopback sockets; memory HTTP transport runs separately")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
    else:
        # Exercise the same http.server handler over bytes in restricted sandboxes.
        class Wire:
            def __init__(self, data):
                self.input, self.output = io.BytesIO(data), io.BytesIO()

            def makefile(self, *args):
                return self.input

            def sendall(self, data):
                self.output.write(data)

        class Opener:
            def open(self, req, timeout=None):
                data = req.data or b""
                headers = dict(req.header_items())
                headers["Content-Length"] = str(len(data))
                raw = f"{req.method} {urllib.parse.urlsplit(req.full_url).path} HTTP/1.0\r\n"
                raw += "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"
                wire = Wire(raw.encode() + data)
                Handler(wire, ("127.0.0.1", 1), None)
                resp = http.client.HTTPResponse(Wire(wire.output.getvalue()))
                resp.begin()
                if resp.status >= 400:
                    raise urllib.error.HTTPError(req.full_url, resp.status, "refused", {}, resp)
                return resp
        monkeypatch.setattr(push, "_OPENER", Opener())
        base = "http://127.0.0.1:1"
    yield {"pending": pending, "requests": requests, "live": live, "project": project,
           "wakes": wakes, "unblocked": unblocked, "failures": failures,
           "base": base, "token": token, "run": lambda **kw: push.collect(base, token, **kw)}
    if server:
        server.shutdown()
        server.server_close()
        thread.join()


def nudge(c, action="report", nid="pn-1"):
    c["pending"]["nudges"].append({"id": nid, "project": "demo", "action": action})


def letters():
    return list(mailbox.INBOX_ROOT.rglob("*.json"))


@pytest.mark.parametrize("live,recipient,box", [
    ({"project_head-abcd1234", "cto-fresh"}, "ph", "project_head-abcd1234"),
    ({"cto-fresh"}, "lead", "cto-fresh"),
    (set(), "none", None),
])
def test_live_routing_ack_and_read(console, live, recipient, box):
    console["live"].clear()
    console["live"].update(live)
    nudge(console)
    console["run"]()
    ack = console["requests"][-2][2]  # messages GET follows the nudge ack
    assert ack["delivered_to"] == recipient and ack["woke"] == bool(box)
    assert len(letters()) == int(bool(box))
    if box:
        path = letters()[0]
        letter = json.loads(path.read_text())
        assert path.parent.name == box and letter["kind"] == "ask"
        assert letter["body"].startswith("CEO report · demo\n")
        assert console["wakes"] == [(box, "CEO-PORTFOLIO")]
        console["run"]()
        assert not any(r[1].endswith("/read") for r in console["requests"])
        path.unlink()
        console["run"]()
        assert ("POST", "/api/portfolio/nudges/pn-1/read", {}) in console["requests"]
        assert json.loads(push.COLLECTOR_STATE.read_text()) == {}


def test_message_verbatim_and_private_even_in_dry_run(console, capsys):
    text = "Private CEO text\n" + "ท" * 1980
    console["pending"]["messages"] = [{"id": "pm-1", "project": "demo", "text": text}]
    console["run"](dry_run=True)
    assert not push.COLLECTOR_STATE.exists() and not letters() and not console["wakes"]
    assert all(r[0] == "GET" for r in console["requests"])
    console["run"]()
    body = json.loads(letters()[0].read_text())["body"]
    assert body == "CEO message · demo\nCEO wrote:\n" + text and len(body) <= 2200
    output = capsys.readouterr()
    assert text not in output.out + output.err and console["token"] not in output.out + output.err
    letters()[0].unlink()
    console["run"]()
    assert ("POST", "/api/portfolio/messages/pm-1/read", {}) in console["requests"]


@pytest.mark.parametrize("action", ["done", "report", "resume", "lead"])
def test_fixed_actions_and_system_unblock(console, action):
    nudge(console, action)
    console["run"](dry_run=True)
    assert console["unblocked"] == []
    console["run"]()
    assert json.loads(letters()[0].read_text())["body"] == f"CEO {action} · demo\n" + push.SENTENCES[action]
    assert console["unblocked"] == ([("demo", {"actor": "system"})] if action == "done" else [])


def test_kill_switch_and_combined_cap(console):
    push.COLLECTOR_OFF.touch()
    console["run"]()
    assert not console["requests"] and not push.COLLECTOR_STATE.exists()
    push.COLLECTOR_OFF.unlink()
    for i in range(18):
        nudge(console, nid=f"pn-{i}")
    console["pending"]["messages"] = [
        {"id": f"pm-{i}", "project": "demo", "text": "continue"} for i in range(10)]
    console["run"]()
    assert len(letters()) == len(console["wakes"]) == 20
    console["run"]()
    assert len(letters()) == 28


def test_ack_failure_retries_without_duplicate_letter_or_wake(console):
    nudge(console)
    path = "/api/portfolio/nudges/pn-1/ack"
    console["failures"][path] = 503
    with pytest.raises(Exception):
        console["run"]()
    assert len(letters()) == len(console["wakes"]) == 1
    console["failures"][path] = 200
    console["run"]()
    assert len(letters()) == len(console["wakes"]) == 1


def test_restart_between_letter_and_wake_recovers(console, monkeypatch):
    nudge(console)
    wake = mail_wake.wake
    monkeypatch.setattr(mail_wake, "wake", lambda *a: (_ for _ in ()).throw(RuntimeError("interrupted")))
    with pytest.raises(RuntimeError):
        console["run"]()
    assert len(letters()) == 1 and console["wakes"] == []
    monkeypatch.setattr(mail_wake, "wake", wake)
    console["run"]()
    assert len(letters()) == len(console["wakes"]) == 1


def test_failed_wake_is_truthfully_acked(console, monkeypatch):
    nudge(console)
    monkeypatch.setattr(mail_wake, "wake", lambda *a: {"woke": False, "reason": "private transport error"})
    console["run"]()
    ack = next(r[2] for r in console["requests"] if r[1].endswith("/ack"))
    assert ack == {"delivered_to": "ph", "woke": False, "reason": "no live session reached"}


def test_lost_ack_response_accepts_conflict(console):
    nudge(console)
    console["failures"]["/api/portfolio/nudges/pn-1/ack"] = 409
    console["run"]()
    console["run"]()
    assert len(letters()) == 1


def test_read_failure_keeps_receipt_for_next_round(console):
    nudge(console)
    console["run"]()
    letters()[0].unlink()
    path = "/api/portfolio/nudges/pn-1/read"
    console["failures"][path] = 503
    with pytest.raises(urllib.error.HTTPError):
        console["run"]()
    assert "pn-1" in json.loads(push.COLLECTOR_STATE.read_text())
    console["failures"][path] = 200
    console["run"]()
    assert json.loads(push.COLLECTOR_STATE.read_text()) == {} and not letters()


def test_cli_dry_run_never_builds_or_pushes(console, monkeypatch, capsys):
    monkeypatch.setenv("PORTFOLIO_PUSH_TOKEN", console["token"])
    monkeypatch.setenv("PORTFOLIO_PUSH_URL", console["base"])
    monkeypatch.setattr(push, "build_payload", lambda: pytest.fail("dry run built a payload"))
    monkeypatch.setattr(push, "_post", lambda *a: pytest.fail("dry run pushed"))
    nudge(console)
    assert push.main(["--dry-run"]) == 0
    assert "would send CEO report" in capsys.readouterr().out
    assert not letters() and not push.COLLECTOR_STATE.exists()


def test_round_budget_stops_before_sending(console, monkeypatch):
    nudge(console)
    monkeypatch.setattr(push, "COLLECTOR_BUDGET_S", 0)
    with pytest.raises(TimeoutError):
        console["run"]()
    assert not letters() and not console["requests"]


def test_unread_state_corruption_fails_closed(console):
    nudge(console)
    push.COLLECTOR_STATE.write_text("invalid")
    with pytest.raises(ValueError):
        console["run"]()
    assert not letters() and not console["requests"]


def test_live_snapshot_filters_stale_and_wrong_roles(monkeypatch):
    from lib import db
    monkeypatch.setattr(db, "get_conn", contextlib.contextmanager(lambda: iter([object()])))
    monkeypatch.setattr(portfolio, "_live_by_sid", lambda conn: {
        "one": {"role": "project_head", "sid": "abcd1234", "stale": False, "status": "idle"},
        "two": {"role": "cto", "sid": "old", "stale": True, "status": "running"},
        "three": {"role": "developer", "sid": "worker", "stale": False, "status": "running"},
    })
    assert delivery.live_boxes() == {"project_head-abcd1234"}


def test_lane_pointer_and_watch_fallback(console, tmp_path):
    locks = tmp_path / "state" / "locks"
    locks.mkdir(parents=True)
    (locks / "cmo-active").write_text("current")
    console["live"].update({"cmo-current", "cmo-another"})
    assert delivery.lane_box("cmo", console["live"]) == "cmo-current"
    assert delivery.watch_box("cmo-dead") == "cmo-current"
    assert delivery.watch_box("project_head-dead", "cmo") == "cmo-current"
    assert delivery.watch_box("coo-dead") is None


def test_main_collects_after_push_and_redacts_errors(console, monkeypatch, capsys):
    monkeypatch.setenv("PORTFOLIO_PUSH_TOKEN", console["token"])
    monkeypatch.setenv("PORTFOLIO_PUSH_URL", console["base"])
    monkeypatch.setattr(push, "build_payload", lambda: {"projects": []})
    monkeypatch.setattr(push, "_post", lambda *args: 204)
    nudge(console)
    assert push.main() == 0 and len(letters()) == 1
    monkeypatch.setattr(push, "collect", lambda *args: (_ for _ in ()).throw(ValueError("private CEO text")))
    assert push.main() == push.EXIT_REFUSED
    output = capsys.readouterr()
    assert "private CEO text" not in output.err and console["token"] not in output.err
