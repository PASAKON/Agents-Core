"""tools/contabo_invoice_reminder.py — the CEO's Contabo top-up mail, 3 days and 1 day before month end.

What must hold: the reminder days fall 3 and 1 days before the last day of a 28-, 29-, 30- or 31-day
month, in Bangkok time; the timer file fires on exactly those days; any other day sends nothing; the
mail is a kind=action from the timer's own session with a ref that differs per month and per reminder;
it carries the amount and the panel link and nothing card-shaped. A fake `post` stands in for the hub;
nothing here reaches the Console or Google.

Run: .venv/bin/python -m pytest tests/test_contabo_invoice_reminder.py
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from tools import contabo_invoice_reminder as rem
from tools import email_ceo

ENV = {"ORG_MACHINE": "contabo"}  # what the systemd unit has: no CXO_ROLE, no session
TIMER = Path(__file__).resolve().parent.parent / "deploy/systemd/contabo-invoice-reminder.timer"


@pytest.mark.parametrize("year, month, last, first, second", [
    (2026, 10, 31, 28, 30),
    (2026, 11, 30, 27, 29),
    (2027, 2, 28, 25, 27),
    (2028, 2, 29, 26, 28),
])
def test_the_reminder_days_are_3_and_1_days_before_the_last_day(year, month, last, first, second):
    days = [d for d in range(1, last + 1) if rem.days_left(date(year, month, d)) in rem.SEND_ON]
    assert days == [first, second]
    assert rem.invoice_date(date(year, month, 1)) == date(year, month, last)


def test_the_timer_fires_on_the_same_days_the_script_mails():
    text = TIMER.read_text(encoding="utf-8")
    fires = re.findall(r"^OnCalendar=\*-\*~0?(\d+) (\d\d:\d\d):00 Asia/Bangkok$", text, re.M)
    # `~K` is the K-th last day of the month, i.e. K-1 days before the last day
    assert sorted(int(k) - 1 for k, _ in fires) == sorted(rem.SEND_ON)
    assert {t for _, t in fires} == {rem.FIRE_AT}
    assert "Persistent=true" in text


def bangkok(y, m, d, hh=8, mm=30):
    return datetime(y, m, d, hh, mm, tzinfo=email_ceo.THAI)


def test_a_run_on_any_other_day_sends_nothing():
    def post(body):
        raise AssertionError("must not post")

    got = rem.run(now=bangkok(2026, 10, 13), env=ENV, post=post)
    assert got["mailed"] is False and "18 days" in got["reason"]


def test_the_day_is_the_bangkok_day_not_the_boxs():
    # 01:30 UTC on 28 Oct is 08:30 in Bangkok but still the 27th in Berlin; 23:30 UTC on the 27th is the 28th in Bangkok
    seen = []
    rem.run(now=datetime(2026, 10, 27, 23, 30, tzinfo=timezone.utc), env=ENV, post=seen.append)
    assert seen and seen[0]["ref"] == "contabo-invoice-2026-10-d3"


def test_the_three_day_mail_is_an_action_from_the_timers_own_session():
    seen = []
    got = rem.run(now=bangkok(2026, 10, 28), env=ENV, post=lambda b: seen.append(b) or {"id": "N-0001"})
    (body,) = seen
    assert body["kind"] == "action" and body["role"] == "cto" and body["session"] == "cto-contabo-invoice"
    assert body["machine"] == "contabo"
    assert body["title"] == "เติมเงิน Contabo €8.00 ก่อน 31 ต.ค. (อีก 3 วัน)"
    assert body["link"] == "https://new.contabo.com"
    assert "€8.00" in body["need"] and "Restore" in body["why"] and "31 ต.ค." in body["if_not"]
    assert got["hub"] == {"id": "N-0001"}


def test_each_reminder_has_its_own_ref_so_neither_is_a_duplicate():
    refs = []
    for y, m, d in [(2026, 10, 28), (2026, 10, 30), (2026, 11, 27), (2026, 11, 29)]:
        rem.run(now=bangkok(y, m, d), env=ENV, post=lambda b: refs.append(b["ref"]))
    assert refs == ["contabo-invoice-2026-10-d3", "contabo-invoice-2026-10-d1",
                    "contabo-invoice-2026-11-d3", "contabo-invoice-2026-11-d1"]


def test_a_catch_up_run_says_how_many_days_are_really_left():
    seen = []
    rem.run(now=bangkok(2026, 10, 29), env=ENV, post=seen.append)
    rem.run(now=bangkok(2026, 10, 31), env=ENV, post=seen.append)
    assert [b["title"] for b in seen] == ["เติมเงิน Contabo €8.00 ก่อน 31 ต.ค. (อีก 2 วัน)",
                                          "เติมเงิน Contabo €8.00 ก่อน 31 ต.ค. (วันนี้)"]


def test_the_test_mail_is_marked_and_names_the_real_dates():
    seen = []
    rem.run(test=True, now=bangkok(2026, 10, 13), env=ENV, post=seen.append)
    (body,) = seen
    assert body["title"].startswith("ทดสอบ: ") and body["ref"] == "contabo-invoice-test-20261013"
    assert "28 ต.ค. และ 30 ต.ค." in body["why"] and "08:30" in body["why"]


def test_every_field_fits_the_hubs_limits_and_passes_the_secret_check():
    limits = {"title": 90, "need": 200, "why": 500, "if_not": 200, "link": 300}
    for test in (False, True):
        for day in (date(2026, 10, 28), date(2026, 12, 30), date(2028, 2, 26)):
            f = rem.fields_for(day, test=test)
            assert all(len(f[k]) <= n for k, n in limits.items()), f
            assert all("\n" not in f[k] for k in limits if k != "why")
            email_ceo.build_payload(f, kind=rem.KIND, session=rem.SESSION, role=rem.ROLE, env=ENV)


def test_no_card_detail_can_reach_the_mail():
    text = " ".join(rem.fields_for(date(2026, 10, 28)).values()).lower()
    assert not re.search(r"\d{4}[ -]?\d{4}[ -]?\d{4}", text)
    assert not any(w in text for w in ("card", "บัตร", "visa", "mastercard", "cvv"))


@pytest.mark.parametrize("exc, code", [
    (email_ceo.Refused("hub refused (409: duplicate; id=N-0001)"), 2),
    (email_ceo.HubError("hub unreachable"), 3),
])
def test_the_cli_exit_codes_tell_systemd_what_to_retry(monkeypatch, capsys, exc, code):
    def boom(**_):
        raise exc

    monkeypatch.setattr(rem, "run", boom)
    assert rem.main([]) == code
