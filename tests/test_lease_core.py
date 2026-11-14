"""Boundary checks beyond the frozen scenario contract."""
from copy import deepcopy
from datetime import timedelta
import json
import threading

import pytest
import yaml

from lease_backend import LeaseBackend
from lib import lease as api
from tools.lease import main


@pytest.fixture
def backend(monkeypatch):
    b = LeaseBackend()
    b.configure("r")
    monkeypatch.setattr(api, "_configured", (b.service, api.Identity("a")))
    return b


def test_context_releases_on_exception_and_forbids_nested(backend):
    with pytest.raises(RuntimeError, match="body failed"):
        with api.lease("r", purpose="test") as handle:
            handle.assert_valid()
            assert handle.token > 0
            with pytest.raises(api.LeaseError, match="nested"):
                with api.lease("r", purpose="nested"):
                    pass
            with pytest.raises(api.LeaseError, match="nested"):
                api.acquire("r", purpose="nested durable request")
            raise RuntimeError("body failed")
    assert backend.holders("r") == []
    assert not handle.thread.is_alive()
    with api.lease("r", purpose="again") as new:
        assert new.token > handle.token


def test_context_timeout_cancels_but_durable_wait_does_not(backend):
    backend.acquire("r", "holder")
    with pytest.raises(api.LeaseError, match="waiting"):
        with api.lease("r", purpose="sync", wait_s=0):
            pass
    assert backend.waiters("r") == []
    result = api.acquire("r", purpose="async", idempotency_key="one")
    assert api.wait(result.request_id).state == "waiting"
    assert backend.waiters("r") == ["a"]
    again = api.acquire("r", purpose="async", idempotency_key="one")
    assert again.request_id == result.request_id
    assert backend.waiters("r") == ["a"]


def test_heartbeat_marks_lost_and_rejects_guarded_work(backend):
    result = api.acquire("r", purpose="heartbeat")
    handle = api.Handle(backend.service, api.Identity("a"), result)
    called = threading.Event()
    def fail(*args):
        called.set()
        return False
    backend.service.renew = fail
    thread = threading.Thread(target=handle.heartbeat, args=(0.001,))
    thread.start()
    assert called.wait(1)
    thread.join(1)
    assert not thread.is_alive()
    with pytest.raises(api.LeaseLost):
        handle.assert_valid()


def test_hub_error_does_not_mask_body_exception_or_leave_nested_flag(backend):
    with pytest.raises(RuntimeError, match="original"):
        with api.lease("r", purpose="failure"):
            backend.hub(False)
            raise RuntimeError("original")
    assert not getattr(api._local, "holding", False)


def test_status_read_only_and_stale_fence_refused_before_reap(backend):
    result = api.acquire("r", purpose="test")
    backend.advance(10)
    before = deepcopy(backend.store.state)
    assert api.status(result.request_id).state == "expired"
    assert backend.store.state == before
    effects = []
    with pytest.raises(api.LeaseLost):
        backend.service.guarded_write("r", result.request_id, result.token, api.Identity("a"),
                                      lambda tx: effects.append("bad"))
    assert effects == []


def test_outbox_failure_preserves_claim_and_retries(backend):
    a = backend.acquire("r", "a")
    backend.acquire("r", "b")
    backend.service.deliver = lambda e: False
    backend.release("r", "a", a.token)
    assert backend.pending_dispatch("r") == ["b"]
    grant = next(e for e in backend.store.state.events.values() if e["kind"] == "grant" and e["actor"] == "b")
    assert grant["delivered_at"] is None and grant["attempts"] == 1
    backend.service.deliver = backend._deliver
    backend.tick()
    backend.tick()
    assert backend.wakes() == [("r", "b")]


def test_scheduler_reaps_and_delivers_without_another_client_call(backend):
    backend.acquire("r", "a")
    backend.acquire("r", "b")
    backend.liveness("a", pid=False, tmux=False, session=False)
    delivered = threading.Event()
    def notify(e):
        backend._deliver(e)
        delivered.set()
        return True
    backend.service.deliver = notify
    backend.service.start_scheduler()
    try:
        assert delivered.wait(1)
        assert backend.holders("r") == ["b"]
    finally:
        backend.service.close()
    assert not backend.service._scheduler_thread.is_alive()


def test_provider_cooling_extends_only_and_event_id_is_idempotent(backend):
    backend.configure("rate", kind="rate", capacity=1, window_s=20)
    service = backend.service
    admin = api.Identity("provider", admin="CTO")
    now = backend.store.state.now
    service.administer("cool", "rate", admin, reason="provider", until=now+timedelta(seconds=50), provider_event_id="a")
    service.administer("cool", "rate", admin, reason="provider", until=now+timedelta(seconds=10), provider_event_id="b")
    assert backend.store.state.resources["rate"]["cooling_until"] == now+timedelta(seconds=50)
    service.administer("reset", "rate", admin, reason="verified", provider_event_id="reset")
    service.administer("reset", "rate", admin, reason="verified", provider_event_id="reset")
    assert backend.store.state.resources["rate"]["quota_epoch"] == 1


def test_group_expiry_revokes_every_member_and_transaction_abort_refunds_rate(backend):
    backend.configure("slow", heartbeat_s=10, max_hold_s=30)
    backend.acquire_many(["r", "slow"], "a")
    backend.advance(10)
    backend.tick()
    assert backend.holders("r") == backend.holders("slow") == []
    backend.configure("rate", kind="rate", capacity=1)
    with pytest.raises(OSError):
        backend.acquire_many(["rate", "slow"], "b", fail_at="slow")
    assert backend.holders("rate") == []
    assert backend.acquire("rate", "c").state == "granted"


def test_ambiguous_rate_claim_preserves_receipt_without_recharging(backend):
    backend.configure("rate", kind="rate", capacity=1, window_s=5)
    backend.acquire("rate", "a")
    backend.acquire("rate", "b")
    backend.advance(5)
    backend.tick()
    assert backend.pending_dispatch("rate") == ["b"]
    backend.advance(10)
    backend.tick()
    rows = backend._rows("rate", "b")
    assert rows[0]["payload"]["reconcile_required"] is True
    assert backend.pending_dispatch("rate") == ["b"]
    assert len([e for e in backend.store.state.events.values()
                if e["kind"] == "grant" and e["actor"] == "b"]) == 1


def test_unknown_liveness_not_death_and_stable_session_survives(backend):
    observer = api.ProbeLiveness(lambda e: None, lambda o, e: False,
                                pid_probe=lambda e: False, tmux_probe=lambda e: False)
    assert observer("remote", {}) is None
    observer = api.ProbeLiveness(lambda e: True, lambda o, e: True,
                                pid_probe=lambda e: False, tmux_probe=lambda e: False)
    assert observer("compacted", {}) is True
    backend.service.observer = lambda o, e: (_ for _ in ()).throw(OSError("unreachable"))
    a = backend.acquire("r", "a")
    backend.advance(5)
    backend.tick()
    assert backend.valid("r", "a", a.token)


def make_registry(tmp_path, rows, **defaults):
    path = tmp_path / "resources.yaml"
    path.write_text(yaml.safe_dump(dict(version=1, defaults=dict(heartbeat_s=5,
        max_hold_s=30, queue_cap=10, on_hub_down="fail_closed", **defaults), resources=rows)))
    return api.Registry(path, references={})


@pytest.mark.parametrize("changes", [{"capacity": 0}, {"capacity": True}, {"max_hold_s": 9},
    {"kind": "rate", "window_s": 0}, {"paid": True, "on_hub_down": "uncoordinated"}])
def test_registry_rejects_bad_policy(tmp_path, changes):
    row = dict(name="r", kind="mutex", capacity=1)
    row.update(changes)
    with pytest.raises(ValueError):
        make_registry(tmp_path, [row])


def test_registry_patterns_aliases_disabled_and_missing_references(tmp_path):
    r = make_registry(tmp_path, [dict(pattern="r:<host>", kind="mutex", capacity=1),
        dict(pattern="r:<anything>", kind="mutex", capacity=1),
        dict(name="r:exact", kind="mutex", capacity=1),
        dict(name="alias", alias="r:exact")])
    assert r.resolve("alias")[0] == "r:exact"
    with pytest.raises(ValueError, match="ambiguous"):
        r.resolve("r:other")
    with pytest.raises(ValueError, match="unknown"):
        r.resolve("missing")
    r = make_registry(tmp_path, [dict(name="r", kind="pool", capacity_from="hosts.missing.max_workers")])
    with pytest.raises(api.LeaseError, match="unverified"):
        r.resolve("r")
    r = api.Registry()
    assert r.resolve("host:contabo:workers")[1]["capacity"] == 3
    assert r.resolve("browser_operator:mac")[1]["capacity"] == 2
    with pytest.raises(api.LeaseError, match="disabled"):
        r.resolve("chrome:mac:9222")


def test_registry_canonical_project_path(tmp_path):
    r = make_registry(tmp_path, [dict(pattern="proj:<project>:path:<path>", kind="mutex", capacity=1)])
    assert r.resolve("proj:alpha_beta:path:src/a.py")[0] == "proj:alpha_beta:path:*"
    with pytest.raises(ValueError, match="unsafe"):
        r.resolve("proj:p:path:src/../secret")
    with pytest.raises(ValueError, match="unexpanded"):
        r.resolve("proj:p:path:reports/{task_id}")


def test_cli_json_and_codes(backend, capsys):
    assert main(["acquire", "r", "--purpose", "cli", "--idempotency-key", "a"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["token"] > 0
    assert main(["status", result["request_id"]]) == 0
    capsys.readouterr()
    assert main(["renew", "r", result["request_id"], str(result["token"]+1)]) == 3
    capsys.readouterr()
    assert main(["release", "r", result["request_id"], str(result["token"])]) == 0
    capsys.readouterr()
    assert main(["acquire", "unknown", "--purpose", "cli", "--idempotency-key", "unknown"]) == 4
    assert json.loads(capsys.readouterr().out)["state"] == "refused"
