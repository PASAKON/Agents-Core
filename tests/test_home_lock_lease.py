import json

import pytest

from lib import lease as leases
from tools import home_lock as hl

KEY = "home:winbox:9224"


@pytest.fixture
def service(monkeypatch):
    clock = [1000.0]
    svc = leases.Service(leases.MemoryStore(lambda: clock[0]))
    svc.configure(KEY, max_hold_s=21600)
    monkeypatch.setenv("LEASE_DB_URL", "fake-only")
    monkeypatch.setattr(leases, "default_service", lambda: (svc, leases.Actor("owner")))
    monkeypatch.setattr(hl.ask_run, "base_url", lambda: pytest.fail("Console touched"))
    return svc, clock


def test_cli_contract_and_separate_calls(service, capsys):
    assert hl.main(["acquire", KEY, "--owner", "owner", "--purpose", "images", "--ttl", "120"]) == 0
    assert f"{KEY} held by owner until" in capsys.readouterr().out
    assert hl.main(["list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["purpose"] == "images"
    assert set(rows[0]) == {"key", "owner", "expiresAt", "purpose"}
    service[1][0] += 60
    assert hl.main(["renew", KEY, "--owner", "owner", "--ttl", "120"]) == 0
    assert service[0].held_resources("home:")[0]["expiresAt"] == 1180
    assert hl.main(["release", KEY, "--owner", "owner"]) == 0
    assert hl.release(KEY, "owner") is False


def test_held_bad_argument_and_refused_codes(service, monkeypatch):
    svc, _ = service
    svc.acquire(KEY, leases.Actor("other"))
    assert hl.main(["acquire", KEY, "--owner", "owner"]) == 2
    assert hl.main(["acquire", KEY, "--owner", "owner", "--ttl", "1"]) == 2
    assert hl.main(["acquire", KEY, "--owner", "spoof"]) == 3
    assert hl.release(KEY, "owner") is False
    monkeypatch.setattr(leases, "default_service", lambda: (_ for _ in ()).throw(leases.HubUnavailable("down")))
    assert hl.main(["list"]) == 3


def test_context_releases_on_error(service):
    with pytest.raises(RuntimeError):
        with hl.home_lock(KEY, "owner") as held:
            assert held.renew()["owner"] == "owner"
            raise RuntimeError("body")
    assert not hl.list_locks()


def test_expiry_and_reacquire(service):
    hl.acquire(KEY, "owner", 60)
    service[1][0] += 61
    assert not hl.list_locks()
    assert hl.renew(KEY, "owner", 60)["owner"] == "owner"


def test_trusted_default_owner(service, monkeypatch):
    monkeypatch.setenv("LEASE_OWNER_SESSION", "owner")
    assert hl.acquire(KEY)["owner"] == "owner"


def test_unset_uses_console(monkeypatch):
    monkeypatch.delenv("LEASE_DB_URL", raising=False)
    monkeypatch.setattr(leases, "default_service", lambda: pytest.fail("lease service touched"))
    calls = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"lock":{"key":"home:winbox:9224","owner":"owner"}}'
    def open_request(req, **kw):
        calls.append((req.full_url, json.loads(req.data)))
        return Response()
    monkeypatch.setattr(hl.ask_run, "base_url", lambda: "https://fake.invalid")
    monkeypatch.setattr(hl.ask_run, "load_token", lambda: "fake")
    monkeypatch.setattr(hl.ask_run._OPENER, "open", open_request)
    assert hl.acquire(KEY, "owner")["owner"] == "owner"
    assert calls == [("https://fake.invalid/api/relay/locks/acquire", dict(key=KEY, owner="owner", ttl=1800, purpose=""))]
