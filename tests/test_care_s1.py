import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from lib.care.outbox import Outbox, make_idempotency_key
from lib.care.quota import QuotaConfig, decide_push
from lib.care.sender import CareSender

TOKEN = "DUMMY-TOKEN-NOT-REAL"
NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


class FakeHttp:
    def __init__(self, usage=0, reply=200, push=200):
        self.usage, self.reply, self.push, self.calls = usage, reply, push, []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers), body))
        if url.endswith("/quota/consumption"):
            return 200, {"totalUsage": self.usage}
        if url.endswith("/reply"):
            return self.reply, {}
        return self.push, {}


@pytest.fixture
def ob():
    o = Outbox(sqlite3.connect(":memory:"), clock=lambda: NOW)
    o.init_schema()
    return o


def add(ob, key="k1", kind="care_reply", token=None, exp=None, critical=False):
    rid, _ = ob.enqueue(idempotency_key=key, recipient_id="U1", recipient_display_name="N",
                        message_kind=kind, payload=[{"type": "text", "text": "x"}],
                        reply_token=token, reply_token_expires_at=exp, critical=critical)
    return rid


def sender(ob, http, dry=False, alerts=None):
    return CareSender(ob, http, TOKEN, QuotaConfig(), alert_coo=(alerts.append if alerts is not None else (lambda m: None)),
                      dry_run=dry, clock=lambda: NOW)


def test_idempotent_enqueue(ob):
    a = add(ob)
    assert ob.enqueue(idempotency_key="k1", recipient_id="U", recipient_display_name="N",
                      message_kind="care_reply", payload=[])[1] is False
    assert add(ob) == a
    assert make_idempotency_key("c", "r", "e", "1") == make_idempotency_key("c", "r", "e", "1")


def test_claim_is_atomic_and_before_send(ob):
    rid = add(ob, token="rt")
    assert ob.claim_sending(rid, "api_reply") is True
    assert ob.claim_sending(rid, "api_reply") is False
    assert ob.stuck_sending() == [rid]

    seen = {}

    class Spy(FakeHttp):
        def __call__(s, m, u, h, b):
            seen["state"] = ob.get(rid2)["state"]
            return super().__call__(m, u, h, b)

    rid2 = add(ob, key="k2", token="rt")
    sender(ob, Spy()).process(rid2)
    assert seen["state"] == "sending"
    assert ob.get(rid2)["state"] == "sent"


def test_reply_path_free_no_quota_read(ob):
    rid = add(ob, token="rt", exp=NOW + timedelta(seconds=10))
    h = FakeHttp()
    assert sender(ob, h).process(rid) == "sent_reply"
    assert [c[1].rsplit("/", 1)[-1] for c in h.calls] == ["reply"]
    assert ob.get(rid)["delivery_via"] == "api_reply"


def test_reply_rejected_reroutes(ob):
    rid = add(ob, token="rt")
    assert sender(ob, FakeHttp(reply=400)).process(rid) == "reply_rejected"
    row = ob.get(rid)
    assert row["state"] == "deferred" and row["reply_token"] is None


def test_care_reply_after_expiry_never_pushes(ob):
    rid = add(ob, token="rt", exp=NOW - timedelta(seconds=1))
    h = FakeHttp()
    assert sender(ob, h).process(rid) == "defer_browser"
    assert h.calls == [] and ob.get(rid)["state"] == "deferred"


def test_announcement_push_after_expiry(ob):
    rid = add(ob, kind="important_announcement", token="rt", exp=NOW - timedelta(seconds=1))
    h = FakeHttp(usage=10)
    assert sender(ob, h).process(rid) == "sent_push"
    assert h.calls[0][1].endswith("/quota/consumption")  # read before push
    assert h.calls[1][2]["X-Line-Retry-Key"]


def test_alert_once_at_240(ob):
    alerts = []
    r1 = add(ob, "a", "important_announcement")
    r2 = add(ob, "b", "important_announcement")
    s = sender(ob, FakeHttp(usage=239), alerts=alerts)
    s.process(r1)
    s.process(r2)
    assert len(alerts) == 1 and TOKEN not in alerts[0]


def test_hard_stop_and_reserve():
    cfg = QuotaConfig(critical_reserve=10)
    assert decide_push(cfg, 300).reason == "hard_stop"
    assert decide_push(cfg, 289).allowed  # 290th push: non-critical may use up to 290
    assert decide_push(cfg, 290).reason == "critical_reserve"  # 291-300 critical only
    assert decide_push(cfg, 290, critical=True).allowed
    assert not decide_push(cfg, 299, batch=2, critical=True).allowed
    assert decide_push(QuotaConfig(), 100).reason == "ok_reserve_unset"


def test_hard_stop_defers_row(ob):
    rid = add(ob, kind="important_announcement")
    h = FakeHttp(usage=300)
    assert sender(ob, h).process(rid) == "blocked_hard_stop"
    assert all(not c[1].endswith("/push") for c in h.calls)
    assert ob.get(rid)["state"] == "deferred"


def test_429_halts_month(ob):
    r1 = add(ob, "a", "important_announcement")
    r2 = add(ob, "b", "important_announcement")
    h = FakeHttp(usage=1, push=429)
    s = sender(ob, h)
    assert s.process(r1) == "halted_429"
    n = len(h.calls)
    assert s.process(r2) == "blocked_monthly_halt"
    assert len(h.calls) == n  # no further http at all


def test_dry_run_sends_nothing(ob):
    r1 = add(ob, "a", token="rt")
    r2 = add(ob, "b", "important_announcement")
    h = FakeHttp()
    s = sender(ob, h, dry=True)
    assert s.process(r1) == "would_reply"
    assert s.process(r2) == "would_push"
    assert all(c[0] == "GET" for c in h.calls)
    assert ob.get(r1)["state"] == "queued" and ob.get(r2)["state"] == "queued"


def test_network_error_not_retried(ob):
    rid = add(ob, token="rt")

    def boom(*a):
        raise OSError("x")

    assert sender(ob, boom).process(rid) == "failed"
    assert ob.get(rid)["state"] == "failed"
    assert sender(ob, FakeHttp()).process(rid) == "skip_failed"


def test_token_never_stored(ob):
    rid = add(ob, kind="important_announcement")
    sender(ob, FakeHttp()).process(rid)
    dump = "\n".join(ob.conn.iterdump())
    assert TOKEN not in dump
