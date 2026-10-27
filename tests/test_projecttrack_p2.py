"""CEO orders relayed by SomPong become hub `orders` rows CO-<N> (task-01fb8d15).

The real order_take / order_close run against p1's in-memory store; the relay and
report_to_ceo helpers that call them are best-effort and never touch a hub here.
"""
import re
from datetime import datetime, timezone

import pytest

import runners.relay_mcp_server as rms
from lib import ceo_report as cr
from lib import portfolio as pf
from test_projecttrack_p1 import Store, store  # noqa: F401 -- `store` is the p1 fixture

T = datetime(2026, 10, 27, 1, tzinfo=timezone.utc)
ACTOR = "sompong"


def hub_row(store, oid):
    row = store.execute("SELECT id, words, channel, taken_by, closed_at, outcome FROM orders WHERE id = ?",
                        (oid,)).fetchone()
    return tuple(row) if row else None


def test_ceo_order_hub_id_is_the_ledger_id_behind_co():
    assert pf.ceo_order_hub_id(7) == "CO-7"
    assert pf.ceo_order_hub_id("12") == "CO-12"
    with pytest.raises(ValueError):
        pf.ceo_order_hub_id("7; DROP TABLE orders")


def test_order_take_uses_an_explicit_id_and_still_generates_one_without(store):
    assert pf.order_take("ship this", "sompong:7", actor=ACTOR, now=T, order_id="CO-7") == "CO-7"
    assert hub_row(store, "CO-7")[:4] == ("CO-7", "ship this", "sompong:7", "sompong")
    generated = pf.order_take("and this", "sompong:8", actor=ACTOR, now=T)
    assert re.fullmatch(r"O-20261027-0800-[a-f0-9]{4}", generated)


def test_the_channel_the_relay_uses_passes_order_takes_own_check(store):
    # The brief said channel='relay'; order_take only accepts sompong:<n> or chat:<role>-<session>.
    with pytest.raises(pf.PortfolioError, match="channel"):
        pf.order_take("x", "relay", actor=ACTOR, now=T, order_id="CO-9")
    assert pf.order_take("x", "sompong:9", actor=ACTOR, now=T, order_id="CO-9") == "CO-9"


def test_relay_mirror_then_report_close_round_trip_on_the_real_verbs(store):
    rms._hub_order_mirror("cto", 5, "ship the film")
    assert hub_row(store, "CO-5") == ("CO-5", "ship the film", "sompong:5", "sompong", None, None)

    cr._hub_order_close(5, "done", "film shipped " + "z" * 300, "CTO#abc123")
    row = hub_row(store, "CO-5")
    assert row[4] is not None
    assert row[5] == "done: film shipped " + "z" * (200 - len("film shipped "))


def test_closing_a_missing_co_row_does_not_raise(store):
    assert cr._hub_order_close(404, "done", "nothing to close", "CTO#abc123") is None
    assert store.execute("SELECT count(*) FROM orders").fetchone()[0] == 0


def test_closing_an_already_closed_co_row_does_not_raise_or_rewrite_it(store):
    rms._hub_order_mirror("cto", 6, "once")
    cr._hub_order_close(6, "done", "first", "CTO#abc123")
    first = hub_row(store, "CO-6")
    assert cr._hub_order_close(6, "failed", "second", "CTO#abc123") is None
    assert hub_row(store, "CO-6") == first


def test_no_hub_is_not_an_error_and_names_only_the_exception_class(monkeypatch):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    audits = []
    monkeypatch.setattr(rms, "_audit", lambda *a: audits.append(a))
    assert rms._hub_order_mirror("cto", 3, "secret order text") is None
    assert audits == [("relay_to_session", "cto", "hub_order_failed", "order_id=3 error=PortfolioError")]
    assert cr._hub_order_close(3, "done", "secret detail", "CTO#abc123") is None
