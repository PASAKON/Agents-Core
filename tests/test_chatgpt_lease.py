"""C2 integration tests: fake storage and browser, never external services."""
import threading
from datetime import datetime, timezone

import pytest

from lib import lease as leases
from tools import chatgpt_images as ci


@pytest.fixture
def service(monkeypatch):
    clock = [1000.0]
    service = leases.Service(leases.MemoryStore(lambda: clock[0]))
    service.configure("chatgpt:winbox:9224", kind="rate", capacity=100, window_s=60, max_hold_s=21600)
    service.configure("home:winbox:9224", max_hold_s=21600)
    monkeypatch.setenv("LEASE_DB_URL", "fake-only")
    monkeypatch.setattr(leases, "default_service", lambda: (service, leases.Actor(threading.current_thread().name)))
    return service, clock


def args(tmp_path):
    return ci.build_parser().parse_args(["--prompt", "image", "--name", "test", "--out", str(tmp_path),
                                        "--lease-host", "winbox", "--wait-s", "2"])


def test_concurrent_runs_wait_before_opening_browser(service, monkeypatch, tmp_path):
    entered, finish, waiting = threading.Event(), threading.Event(), threading.Event()
    calls, results = [], []
    svc, _ = service
    original_wait = svc.wait
    def wait(*a, **kw):
        waiting.set()
        return original_wait(*a, **kw)
    monkeypatch.setattr(svc, "wait", wait)
    class Browser:
        def __init__(self, **kw): pass
        def attach(self):
            calls.append(threading.current_thread().name)
        def close(self): pass
    def schedule(*a, **kw):
        kw["guard"].assert_valid()
        if threading.current_thread().name == "first":
            entered.set()
            assert finish.wait(3)
        return 0, []
    monkeypatch.setattr(ci, "ChatGPTBrowser", Browser)
    monkeypatch.setattr(ci, "run_scheduler", schedule)
    first = threading.Thread(name="first", target=lambda: results.append(ci.cmd_run(args(tmp_path / "a"))))
    second = threading.Thread(name="second", target=lambda: results.append(ci.cmd_run(args(tmp_path / "b"))))
    first.start()
    try:
        assert entered.wait(2)
        second.start()
        assert waiting.wait(2)
        assert calls == ["first"]
    finally:
        finish.set()
        first.join(4)
        if second.ident:
            second.join(4)
    assert not first.is_alive() and not second.is_alive()
    assert calls == ["first", "second"]
    assert results == [0, 0]
    assert svc.held_resources("") == []


@pytest.mark.parametrize("note,deadline", [("try again in 30 minutes", 2800), ("usage cap", 8200)])
def test_quota_exit_cools_before_release(service, monkeypatch, tmp_path, note, deadline):
    svc, clock = service
    closed = []
    class Browser:
        def __init__(self, **kw): pass
        def attach(self): pass
        def close(self): closed.append(True)
    monkeypatch.setattr(ci, "ChatGPTBrowser", Browser)
    monkeypatch.setattr(ci, "run_scheduler", lambda *a, **kw: (5, [dict(status="stopped", hazard_kind="usage_limit", note=note)]))
    real_deadline = ci.cooling_deadline
    monkeypatch.setattr(ci, "cooling_deadline", lambda text: real_deadline(text, datetime.fromtimestamp(clock[0], timezone.utc)))
    assert ci.cmd_run(args(tmp_path)) == 5
    assert closed and not svc.held_resources("")
    other = leases.Actor("next")
    pending = svc.acquire(["chatgpt:winbox:9224", "home:winbox:9224"], other)
    assert pending.state == "waiting"
    clock[0] = deadline - 1
    svc.tick()
    assert svc.status(pending.request_id, other).state == "waiting"
    clock[0] = deadline
    svc.tick()
    assert svc.status(pending.request_id, other).state == "granted"


@pytest.mark.parametrize("text,seconds", [("unknown", 7200), ("try again in 15 minutes", 900),
    ("reset 13:30", 5400), ("reset 1:30 PM", 5400), ("reset 2026-11-14T13:00:00Z", 3600),
    ("reset 00:10", 43800)])
def test_reset_parser(text, seconds):
    now = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
    assert ci.cooling_deadline(text, now) == now.timestamp() + seconds


def test_unset_keeps_old_path(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("LEASE_DB_URL", raising=False)
    monkeypatch.setattr(leases, "default_service", lambda: pytest.fail("hub touched"))
    monkeypatch.setattr(ci, "_cmd_run", lambda a: 5)
    assert ci.cmd_run(args(tmp_path)) == 5
    assert capsys.readouterr().out == "lease: off (LEASE_DB_URL unset)\n"


def test_exception_releases(service, monkeypatch, tmp_path):
    monkeypatch.setattr(ci, "_cmd_run", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        ci.cmd_run(args(tmp_path))
    assert not service[0].held_resources("")


def test_cooling_requires_current_owner(service):
    svc, _ = service
    actor = leases.Actor("owner")
    grant = svc.acquire("chatgpt:winbox:9224", actor)
    with pytest.raises(leases.LeaseLost):
        svc.report_cooling(grant.request_id, leases.Actor("other"), grant.tokens, "chatgpt:winbox:9224", 9999)
    assert svc.report_cooling(grant.request_id, actor, grant.tokens, "chatgpt:winbox:9224") == 8200


def test_registry_disabled_without_verified_numbers():
    registry = leases.Registry()
    for name in ("chatgpt:winbox:9224", "home:winbox:9224"):
        assert registry.resolve(name)[1]["enabled"] is False


def test_loopback_needs_canonical_host(monkeypatch, tmp_path):
    a = args(tmp_path)
    a.lease_host = None
    monkeypatch.delenv("ORG_HOST", raising=False)
    with pytest.raises(ValueError):
        ci.lease_resource(a)
    monkeypatch.setenv("ORG_HOST", "winbox")
    assert ci.lease_resource(a) == "chatgpt:winbox:9224"


def test_wait_timeout_cancels_without_browser(service, monkeypatch, tmp_path):
    svc, _ = service
    svc.acquire("home:winbox:9224", leases.Actor("busy"))
    monkeypatch.setattr(ci, "ChatGPTBrowser", lambda **kw: pytest.fail("opened browser while waiting"))
    a = args(tmp_path)
    a.wait_s = 0
    assert ci.cmd_run(a) == 1
    assert svc.store.run(lambda s, n, t: all(w["state"] == "cancelled" for w in s["waiters"].values()
        if w["owner_session"] != "busy"), readonly=True)


def test_hazard_keeps_reported_ampm():
    _, note = ci.classify_hazard("You've reached your limit. Try again at 1:30 PM", True)
    now = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
    assert ci.cooling_deadline(note, now) == now.timestamp() + 5400
