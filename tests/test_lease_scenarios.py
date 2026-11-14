"""Phase B contracts, authored before the reference model; no production imports.

Phase C swaps only `backend` for a lib.lease contract adapter with a scratch
store, injectable hub clock, liveness, outbox and failure hooks. Observations
below are public adapter methods, never model internals. No sleeps or network.
"""
import itertools

import pytest


@pytest.fixture
def backend():
    from lease_model import LeaseModel
    return LeaseModel


@pytest.fixture
def q(backend):
    service = backend()
    service.configure("r")
    return service


def test_scenario_01_early_release_one_wake(q):
    a = q.acquire("r", "a")
    q.acquire("r", "b")
    q.acquire("r", "c")
    q.release("r", "a", a.token)
    assert q.wakes() == [("r", "b")]
    assert q.holders("r") == ["b"]
    assert q.waiters("r") == ["c"]


def test_scenario_02_dead_holder_one_heartbeat(q):
    q.acquire("r", "a")
    q.acquire("r", "b")
    q.liveness("a", pid=False, tmux=False, session=False)
    q.advance(5)
    q.tick()
    assert q.holders("r") == ["b"]
    assert q.wakes() == [("r", "b")]


def test_scenario_03_alive_forgot_release_max_hold_letter(q):
    q.acquire("r", "a")
    q.acquire("r", "b")
    for _ in range(5):
        q.advance(5)
        assert q.renew("r", "a")
    q.advance(5)
    q.tick()
    assert q.holders("r") == ["b"]
    assert ("a", "max_hold") in q.letters()


def test_scenario_04_endless_renew_capped(q):
    a = q.acquire("r", "a")
    q.acquire("r", "b")
    for _ in range(29):
        q.advance(1)
        assert q.renew("r", "a", a.token)
    q.advance(1)
    assert not q.renew("r", "a", a.token)
    assert q.holders("r") == ["b"]


def test_scenario_05_simultaneous_acquires_one_linearized_winner(backend):
    # Enumerate both linearizations of requests at the same hub instant.
    # Phase C additionally needs a real concurrent PostgreSQL barrier test.
    for order in itertools.permutations(["a", "b"]):
        s = backend()
        s.configure("r")
        results = [s.acquire("r", owner) for owner in order]
        assert sum(r.state == "granted" for r in results) == 1
        assert s.holders("r") == [order[0]]
        assert s.waiters("r") == [order[1]]


def test_scenario_06_ceo_priority_without_preemption(q):
    a = q.acquire("r", "a")
    q.acquire("r", "b")
    q.acquire("r", "ceo", priority=0)
    assert q.holders("r") == ["a"]
    q.release("r", "a", a.token)
    assert q.holders("r") == ["ceo"]
    assert q.waiters("r") == ["b"]


def test_scenario_07_hub_down_policy(q):
    q.configure("paid", paid=True, on_hub_down="fail_closed")
    q.configure("free", on_hub_down="uncoordinated")
    a = q.acquire("r", "a")
    q.hub(False)
    assert q.acquire("paid", "b").reason == "hub_down"
    assert q.acquire("r", "b").reason == "hub_down"
    result = q.acquire("free", "b")
    assert result.state == "uncoordinated" and result.token is None
    q.hub(True)
    assert q.valid("r", "a", a.token)  # A2-012: error never empties store


def test_scenario_08_restart_preserves_waiters_and_claims(q):
    q.acquire("r", "a")
    q.acquire("r", "b")
    q.acquire("r", "c")
    q.advance(10)
    q = q.restart()
    assert q.waiters("r") == ["b", "c"]
    q.tick()
    assert q.holders("r") == ["b"]
    # A2-006/007/011: failures before acknowledgement retain durable claim.
    for failure in ("lookup", "process_death", "delegate"):
        q.dispatch("r", "b", failure=failure)
        q = q.restart()
        assert q.pending_dispatch("r") == ["b"]
    q.advance(10)
    q.tick()
    assert q.pending_dispatch("r") == ["b"]
    assert q.waiters("r") == ["c"]
    q.dispatch("r", "b")
    assert q.pending_dispatch("r") == []


def test_scenario_09_partition_rejects_old_fence(q):
    a = q.acquire("r", "a")
    q.acquire("r", "b")
    q.advance(10)
    q.tick()
    b = q.acquire("r", "b")
    assert b.token > a.token
    assert not q.valid("r", "a", a.token)
    assert not q.renew("r", "a", a.token)
    assert not q.release("r", "a", a.token)
    assert q.valid("r", "b", b.token)


def test_scenario_10_dead_waiter_skipped(q):
    a = q.acquire("r", "a")
    q.acquire("r", "b")
    q.acquire("r", "c")
    q.liveness("b", pid=False, tmux=False, session=False)
    q.release("r", "a", a.token)
    assert q.holders("r") == ["c"]
    assert q.wakes() == [("r", "c")]
    assert q.waiters("r") == []


def test_scenario_11_pool_four_six_requests(q):
    q.configure("p", kind="pool", capacity=4)
    results = [q.acquire("p", str(i)) for i in range(6)]
    assert [r.state for r in results] == ["granted"] * 4 + ["waiting"] * 2
    q.release("p", "1", results[1].token)
    assert q.holders("p") == ["0", "2", "3", "4"]
    assert q.waiters("p") == ["5"]


def test_scenario_12_rate_window_and_far_side_cooling(q):
    q.configure("rate", kind="rate", capacity=2, window_s=20)
    a = q.acquire("rate", "a")
    q.release("rate", "a", a.token)
    q.acquire("rate", "b")
    assert q.acquire("rate", "c").state == "waiting"
    q.cool("rate", until=25, source="chatgpt_exit_5")
    q.advance(20)
    q.tick()
    assert q.waiters("rate") == ["c"]
    q.advance(5)
    q.tick()
    assert q.holders("rate") == ["c"]
    assert q.wakes() == [("rate", "c")]
    q.cool("rate", until=50, source="provider")
    q.acquire("rate", "d")
    q.reset_quota("rate")  # A2-009: reset invokes the same scheduler now
    assert q.holders("rate") == ["c", "d"]


def test_scenario_13_ceo_override_stop_letter_and_fence(q):
    a = q.acquire("r", "a")
    q.acquire("r", "b")
    ceo = q.override("r", "ceo", role="CEO", reason="emergency")
    assert ceo.state == "granted" and ceo.token > a.token
    assert q.holders("r") == ["ceo"]
    assert ("a", "stop") in q.letters()
    assert not q.valid("r", "a", a.token)
    assert ("override", "CEO", "emergency") in q.events()


def test_scenario_14_opposite_multi_lease_order_and_exception_rollback(q):
    q.configure("s")
    assert q.acquire_many(["s", "r"], "a").state == "granted"
    assert q.acquire_many(["r", "s"], "b").state == "waiting"
    assert q.acquisition_order() == ["r", "s"]
    q.release_many(["s", "r"], "a")
    assert q.holders("r") == q.holders("s") == ["b"]
    q.release_many(["r", "s"], "b")
    with pytest.raises(OSError):
        q.acquire_many(["r", "s"], "c", fail_at="s")
    assert q.holders("r") == q.holders("s") == []


def test_scenario_15_client_clock_skew_ignored(q):
    a = q.acquire("r", "a", client_time=-100000)
    assert q.acquire("r", "b", client_time=100000).state == "waiting"
    assert q.valid("r", "a", a.token)
    q.advance(5)
    assert q.renew("r", "a", a.token, client_time=100000)
    assert q.holders("r") == ["a"]


def test_scenario_16_fifty_fifo_and_cap(q):
    q.configure("r", queue_cap=50)
    q.acquire("r", "holder")
    names = [f"w{i:02}" for i in range(50)]
    for owner in names:
        assert q.acquire("r", owner).state == "waiting"
    assert q.acquire("r", "overflow").reason == "queue_full:50"
    owner = "holder"
    for following in names:
        q.release("r", owner, q.acquire("r", owner).token)
        assert q.holders("r") == [following]
        owner = following
    assert q.wakes() == [("r", name) for name in names]


def test_scenario_17_gc_exempt_until_explicit_cancel(q):
    a = q.acquire("r", "a")
    q.acquire("r", "b")
    assert q.gc_candidates(["b", "unrelated"]) == ["unrelated"]
    q.cancel("b")
    assert q.waiters("r") == []
    q.release("r", "a", a.token)
    assert q.wakes() == []


def test_scenario_18_nonowner_refused_override_logged_exact_project(q):
    a = q.acquire("r", "a")
    assert not q.release("r", "b", a.token)
    assert not q.release("r", "b", a.token, role="worker", reason="want it")
    assert q.release("r", "b", a.token, role="CTO", reason="abandoned")
    assert ("release_override", "CTO", "abandoned") in q.events()
    for project in ("alpha_beta", "alphaXbeta"):
        q.configure(f"proj:{project}:path:x", project=project)
        q.acquire(f"proj:{project}:path:x", "a")
    q.release_project("alpha_beta", "a")
    assert q.holders("proj:alphaXbeta:path:x") == ["a"]


def test_scenario_19_ceo_card_approval_bound_to_request(q):
    q.configure("card", needs_ceo_card=True)
    assert q.acquire("card", "a").state == "awaiting_approval"
    assert q.holders("card") == []
    assert not q.approve("card", "a", role="worker", card="Q-1")
    assert q.approve("card", "a", role="CEO", card="Q-1")
    assert q.holders("card") == ["a"]
    a = q.acquire("card", "a")
    q.release("card", "a", a.token)
    assert q.acquire("card", "b").state == "awaiting_approval"


def test_scenario_20_compact_resume_stable_session(q):
    a = q.acquire("r", "session-a")
    q.liveness("session-a", pid=False, tmux=True, session=True)
    q.advance(5)
    assert q.renew("r", "session-a", a.token)
    q = q.restart()
    q.advance(5)
    q.tick()
    assert q.valid("r", "session-a", a.token)
    assert q.acquire("r", "session-a").token == a.token


def test_scenario_21_jsonl_import_lossless_idempotent_transactional(q):
    sources = {
        "mac:host": [{'task_id': 'a', 'note': 'keep me'}, {'task_id': 'b'}],
        "winbox:budget": [{'task_id': 'a', 'bucket': 'codex'}],
        "contabo:disk": [{'task_id': 'c'}, {'task_id': 'c'}],
    }
    for source, rows in sources.items():
        q.import_rows(source, rows)
    original = q.imported()
    assert len(original) == 5  # duplicate lines retained by source+ordinal
    assert q.waiters("import:mac:host") == ["a", "b"]
    assert q.waiters("import:winbox:budget") == ["a"]
    assert q.waiters("import:contabo:disk") == ["c"]
    for source, rows in sources.items():
        q.import_rows(source, rows)
    assert q.imported() == original
    assert q.waiters("import:mac:host") == ["a", "b"]
    with pytest.raises(OSError):
        q.import_rows("new:disk", [{'task_id': 'd'}], fail=True)
    assert q.restart().imported() == original  # A2-004/005: no lost old row
    assert original[("mac:host", 0)] == sources["mac:host"][0]
    q.tick()
    for source, owners in (("mac:host", ["a", "b"]),
                           ("winbox:budget", ["a"]), ("contabo:disk", ["c"])):
        resource = f"import:{source}"
        for owner in owners:
            grant = q.acquire(resource, owner)
            assert q.release(resource, owner, grant.token)
        q.import_rows(source, sources[source])
        assert q.waiters(resource) == []  # retry cannot resurrect completed work
        assert q.holders(resource) == []
