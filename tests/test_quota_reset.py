from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from tools import quota, quota_reset as reset

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)
END = "2026-11-20T00:00:00Z"


@pytest.fixture(autouse=True)
def sender(monkeypatch):
    send = Mock()
    monkeypatch.setattr(reset.email_ceo, "send", send)
    return send


@pytest.fixture
def hub(monkeypatch):
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = None
    @contextmanager
    def get_conn():
        yield conn
    monkeypatch.setattr(reset.db, "get_conn", get_conn)
    log = Mock()
    monkeypatch.setattr(reset.db, "log_event", log)
    drain = Mock()
    monkeypatch.setattr(reset, "drain_waiting", drain)
    return log, drain, conn


def q(pct, **kwargs):
    return quota.Quota("codex", weekly_remaining=1-pct/100,
                       weekly_resets_at=END, **kwargs)


@pytest.mark.parametrize("before,after,count", [(100, 0, 1), (52, 1, 1), (30, 15, 0), (30, 10, 1)])
def test_drops_and_dedupe(tmp_path, hub, sender, before, after, count):
    history = tmp_path / "quota-history.jsonl"
    quota.record_snapshot({"codex": q(before)}, history, NOW)
    events = reset.process({"codex": q(after)}, history=history, now=NOW)
    assert len(events) == count
    assert reset.process({"codex": q(after)}, history=history, now=NOW) == []
    log, drain, _ = hub
    assert log.call_count == drain.call_count == count
    assert sender.call_count == count
    if count:
        assert log.call_args.args[1:4] == (None, "quota_reset", "quota_reset")
        assert list(reset.rows(history.with_name("quota-resets.jsonl"))) == events


def test_plan_change_multiple_buckets_drains_once(tmp_path, hub, sender):
    history = tmp_path / "quota-history.jsonl"
    quota.record_snapshot({b: q(10, plan_type="plus") for b in reset.BUCKETS}, history, NOW)
    events = reset.process({b: q(10, plan_type="pro") for b in reset.BUCKETS}, history=history, now=NOW)
    assert len(events) == 4
    assert all(e["reason"] == "plan_changed" for e in events)
    assert hub[0].call_count == 4
    hub[1].assert_called_once()
    assert sender.call_count == 3
    assert {c.args[0]["ref"] for c in sender.call_args_list} == {
        f"{b}:{END}" for b in reset.MAIL_BUCKETS}


@pytest.mark.parametrize("old_reset,expected", [
    ("2026-11-15T00:00:00Z", True), ("2026-11-12T00:00:00Z", False),
    ("2026-11-19T00:00:00Z", False)])
def test_reset_extended_before_due(old_reset, expected):
    old = {"weekly_remaining": .5, "weekly_resets_at": old_reset}
    new = {"weekly_remaining": .5, "weekly_resets_at": END}
    assert bool(reset.reset_event("codex", old, new, NOW)) == expected


def test_bonus_and_errors_not_resets():
    old = {"weekly_remaining": 0}
    new = {"weekly_remaining": 1, "weekly_raw": 0}
    assert reset.reset_event("codex", old, new, NOW) is None
    new = {"weekly_remaining": 1, "error": "offline"}
    assert reset.reset_event("codex", old, new, NOW) is None


def test_hub_dedupe_repairs_missing_local_journal(tmp_path, hub, sender):
    history = tmp_path / "quota-history.jsonl"
    quota.record_snapshot({"codex": q(100)}, history, NOW)
    hub[2].execute.return_value.fetchone.return_value = {"id": 1}
    assert len(reset.process({"codex": q(0)}, history=history, now=NOW)) == 1
    hub[0].assert_not_called()
    sender.assert_not_called()


def test_mail_failure_preserves_publication_and_history(tmp_path, hub, sender, caplog):
    history = tmp_path / "quota-history.jsonl"
    quota.record_snapshot({"codex": q(100)}, history, NOW)
    sender.side_effect = RuntimeError("private response must not be logged")
    events = reset.process({"codex": q(0)}, history=history, now=NOW)
    quota.record_snapshot({"codex": q(0)}, history, NOW)
    assert len(events) == 1
    assert len(list(reset.rows(history))) == 2
    assert list(reset.rows(history.with_name("quota-resets.jsonl"))) == events
    hub[0].assert_called_once()
    hub[1].assert_called_once()
    assert "quota reset mail failed for codex (RuntimeError)" in caplog.text
    assert "private response" not in caplog.text


@pytest.mark.parametrize("bucket", sorted(reset.MAIL_BUCKETS))
@pytest.mark.parametrize("reason,label", [
    ("utilization_drop", "รีเซ็ตด้วยตนเอง"), ("reset_extended", "โบนัส"),
    ("plan_changed", "เปลี่ยนแผน")])
def test_mail_content(bucket, reason, label, sender):
    event = {"bucket": bucket, "resets_at": END, "from_pct": 100,
             "to_pct": 0, "reason": reason}
    reset.mail_reset(event)
    fields = sender.call_args.args[0]
    assert fields["title"] == f"🎉 {reset.MAIL_BUCKETS[bucket]} รีเซ็ตแล้ว — โควต้าก้อนใหม่"
    assert "100% -> 0%" in fields["why"]
    assert label in fields["why"]
    assert "20/11/2026 07:00 น." in fields["why"]
    assert fields["ref"] == f"{bucket}:{END}"
    assert sender.call_args.kwargs["kind"] == "quota_reset"
    reset.email_ceo.build_payload(fields, kind="quota_reset", env={"CXO_ROLE": "cto", "CXO_SESSION_ID": "quota-reset"})


@pytest.mark.parametrize("deadline", [None, "invalid"])
def test_mail_unknown_deadline_and_usage(deadline):
    fields = reset.mail_fields({"bucket": "codex", "resets_at": deadline,
                               "from_pct": None, "to_pct": None, "reason": "plan_changed"})
    assert "รีเซ็ตถัดไป: ไม่ทราบ" in fields["why"]


def test_async_drain(monkeypatch):
    from tools import host_queue, budget_queue
    calls = []
    async def host():
        calls.append("host")
    monkeypatch.setattr(host_queue, "drain", host)
    monkeypatch.setattr(budget_queue, "drain", lambda: calls.append("budget"), raising=False)
    reset.drain_waiting()
    assert calls == ["host", "budget"]


def test_daily_drop():
    event = reset.reset_event("claude", {"daily_remaining": 0},
                             {"daily_remaining": 1, "daily_resets_at": END}, NOW)
    assert event["from_pct"] == 100
    assert event["resets_at"] == END


def test_publication_failure_can_retry(tmp_path, hub):
    history = tmp_path / "quota-history.jsonl"
    quota.record_snapshot({"codex": q(100)}, history, NOW)
    hub[0].side_effect = RuntimeError("hub unavailable")
    with pytest.raises(RuntimeError):
        reset.process({"codex": q(0)}, history=history, now=NOW)
    assert list(reset.rows(history.with_name("quota-resets.jsonl"))) == []
    hub[1].assert_not_called()
    hub[0].side_effect = None
    assert len(reset.process({"codex": q(0)}, history=history, now=NOW)) == 1


def test_snapshot_calls_reset_before_appending(tmp_path, monkeypatch):
    import sys
    from tools import usage_budget, cost_learn
    history = tmp_path / "quota-history.jsonl"
    quota.record_snapshot({"codex": q(100)}, history, NOW)
    monkeypatch.setattr(quota, "DEFAULT_HISTORY", history)
    monkeypatch.setattr(quota, "SNAPSHOT_PATH", tmp_path / "snapshot.json")
    monkeypatch.setattr(quota, "load_plans", lambda _: {})
    monkeypatch.setattr(quota, "fetch_all_quotas", lambda _: {"codex": q(0)})
    seen = []
    def process(quotas, **kwargs):
        assert len(list(reset.rows(history))) == 1
        assert quota.read_snapshot()["codex"].weekly_remaining == 1
        seen.append(True)
    monkeypatch.setattr(reset, "process", process)
    monkeypatch.setattr(usage_budget, "write", lambda **kw: None)
    monkeypatch.setattr(cost_learn, "learn", lambda: {})
    monkeypatch.setattr(cost_learn, "write_table", lambda _: None)
    monkeypatch.setattr(sys, "argv", ["quota.py", "--snapshot"])
    quota.main()
    assert seen == [True]
    assert len(list(reset.rows(history))) == 2
