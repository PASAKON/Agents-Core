"""Acceptance spec for the Higgsfield credit lane (CEO 2026-10-01: Higgsfield uses
credits, but not one may be spent until the script is finished).

Written by the CTO before the worker starts. The worker makes these pass and must
not edit this file; the merge gate checks that it is byte-identical to main.

Contract under test:
  scripts/higgsfield/credit_guard.py
    parse_price(label) -> int | None
        The charge is the LAST integer on the submit label ("Generate 80 60" = list
        80, charged 60). "Unlimited" with no number = 0. A label that reads like a
        purchase, or carries no number, is None (unreadable = refuse).
    SpendRefused(Exception)
    SpendGuard(max_per_clip, budget, ledger)
        check(label) -> int          price, or SpendRefused
        record(clip_id, price, balance_before=None, balance_after=None)
        spent() -> int               sum of recorded prices, read back from the ledger
  scripts/higgsfield/credit_fire.py
    main(argv) -> int               --fire without both caps returns 2 before any
                                    browser is touched
"""
import json

import pytest

cg = pytest.importorskip("scripts.higgsfield.credit_guard")


@pytest.mark.parametrize("label,price", [
    ("Generate 80 60", 60),
    ("Generate\n80\n60", 60),
    ("Generate 60", 60),
    ("UNLIMITED · 140 0", 0),
    ("Generate Unlimited", 0),
])
def test_parse_price_takes_the_charged_number(label, price):
    assert cg.parse_price(label) == price


@pytest.mark.parametrize("label", ["", "   ", "Generate", "Upgrade plan", "Buy 1000 credits", "Top up 500"])
def test_parse_price_refuses_what_it_cannot_read(label):
    assert cg.parse_price(label) is None


def test_guard_needs_both_caps(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    for bad in [(0, 100), (60, 0), (None, 100), (60, None), (-1, 100)]:
        with pytest.raises((ValueError, TypeError)):
            cg.SpendGuard(*bad, ledger)


def test_guard_allows_within_caps_and_stops_at_budget(tmp_path):
    g = cg.SpendGuard(60, 120, tmp_path / "spend.jsonl")
    assert g.check("Generate 80 60") == 60
    g.record("c1", 60)
    assert g.check("Generate 80 60") == 60
    g.record("c2", 60)
    assert g.spent() == 120
    with pytest.raises(cg.SpendRefused):
        g.check("Generate 80 60")          # would be 180 > budget 120


def test_guard_refuses_over_the_per_clip_cap(tmp_path):
    g = cg.SpendGuard(60, 1000, tmp_path / "spend.jsonl")
    with pytest.raises(cg.SpendRefused):
        g.check("Generate 100 90")


@pytest.mark.parametrize("label", ["Generate", "", "Upgrade plan"])
def test_guard_refuses_an_unreadable_label(tmp_path, label):
    g = cg.SpendGuard(60, 1000, tmp_path / "spend.jsonl")
    with pytest.raises(cg.SpendRefused):
        g.check(label)


def test_spend_survives_a_restart(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    g = cg.SpendGuard(60, 120, ledger)
    g.record("c1", 60)
    g.record("c2", 60)
    again = cg.SpendGuard(60, 120, ledger)
    assert again.spent() == 120
    with pytest.raises(cg.SpendRefused):
        again.check("Generate 80 60")
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert [r["clip_id"] for r in rows] == ["c1", "c2"]


def test_a_charge_above_the_label_is_recorded_then_stops_the_run(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    g = cg.SpendGuard(60, 1000, ledger)
    with pytest.raises(cg.SpendRefused):
        g.record("c1", 60, balance_before=1000, balance_after=880)   # 120 taken for a 60 label
    assert g.spent() >= 60
    assert ledger.read_text().count("c1") == 1


def test_fire_without_caps_is_refused_before_any_browser(tmp_path):
    cf = pytest.importorskip("scripts.higgsfield.credit_fire")
    prompts = tmp_path / "p.csv"
    prompts.write_text("clip_id,prompt\nc1,A quiet lake at sunrise\n", encoding="utf-8")
    base = ["--prompts", str(prompts), "--cdp", "http://127.0.0.1:1"]   # nothing listens on :1
    assert cf.main(base + ["--fire"]) == 2
    assert cf.main(base + ["--fire", "--max-per-clip", "60"]) == 2
    assert cf.main(base + ["--fire", "--budget", "120"]) == 2
