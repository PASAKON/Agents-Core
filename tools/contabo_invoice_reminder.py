#!/usr/bin/env python3
"""Email the CEO to top up Contabo before the month-end invoice (CEO order 2026-10-12, relayed by SomPong).

The CEO's words: "ถ้าจ่ายช้าจะมีค่า Restore +5$ ค่าธรรมเนียม ซึ่งไม่คุ้ม แต่ถ้าเตือนก่อนเติมเงินเข้าก่อน เราจะได้ในราคานี้เลย".
His Contabo panel (Account > Billing & Payment, screenshot 12 Oct): €8.00 a month, invoices dated the
last day of the month (30 Jun, 31 Jul, 31 Aug, 30 Sep). Nothing on this box can read a "due" signal
without a Contabo API key or a login, and he has given neither, so the schedule is fixed to the month
end: deploy/systemd/contabo-invoice-reminder.timer fires at 08:30 Asia/Bangkok on the 4th-last and the
2nd-last day of every month (`*-*~04`, `*-*~02`), which is 3 days and 1 day before the invoice in a
28-, 29-, 30- or 31-day month alike. This script works the day out again by itself, so a catch-up run
after downtime (Persistent=true) says how many days are really left, and a run on any other day sends
nothing. No model runs here, and no card detail ever goes in the mail.

Kind and sender (skill ALL_Protocol_EmailCEO; the caps live in Console src/notify/ceo.js):
- kind=action: he must do one thing that only he can do (top up on his own account). It is mailed at
  once and buzzes his phone. kind=deadline would never be mailed: it waits for the next 08:00 digest.
- session=cto-contabo-invoice: the hub allows 3 mails per session per Thai day, counted by session
  name, so the timer has its own budget. Each fire sends one mail, on a different day, and no live CTO
  session can use that budget up.
- ref=contabo-invoice-<YYYY-MM>-d<N>: a new ref per month and per reminder, so neither reminder is a
  6-hour duplicate of the other, and a second run the same morning is refused as one (no double mail).
- 08:30 Bangkok: after the 08:00 digest and early in the Thai day, before the org's 20-mail cap is near.

Verbs:
    python3 tools/contabo_invoice_reminder.py [--dry-run]          # the timer: mail if today is a reminder day
    python3 tools/contabo_invoice_reminder.py --test [--dry-run]   # mail today's reminder now, marked ทดสอบ
Exit: 0 mailed, or not a reminder day · 2 refused (a cap, a duplicate) · 3 no token / hub down (systemd retries).
"""
from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import email_ceo  # noqa: E402

AMOUNT = "€8.00"                   # the CEO's panel, 12 Oct 2026
PANEL = "https://new.contabo.com"
KIND = "action"
ROLE = "cto"
SESSION = "cto-contabo-invoice"    # the timer's own mailbox in the hub's ledger; caps are per session
SEND_ON = (3, 1)                   # days before the invoice date, the two timer fires
WINDOW = max(SEND_ON)              # a catch-up run this close to the invoice still mails
FIRE_AT = "08:30"                  # Asia/Bangkok, the timer's OnCalendar
TH_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
             "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")


def invoice_date(day: date) -> date:
    """The invoice this day is waiting for: the last day of its month."""
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def days_left(day: date) -> int:
    return (invoice_date(day) - day).days


def thai_day(day: date) -> str:
    return f"{day.day} {TH_MONTHS[day.month - 1]}"


def fields_for(day: date, *, amount: str = AMOUNT, test: bool = False) -> dict:
    inv, left = invoice_date(day), days_left(day)
    when = thai_day(inv)
    title = f"เติมเงิน Contabo {amount} ก่อน {when} ({'วันนี้' if left == 0 else f'อีก {left} วัน'})"
    why = f"บิล VPS Contabo รายเดือน {amount} ออกวันที่ {when} เติมเงินก่อนได้ราคานี้ ถ้าจ่ายช้ามีค่า Restore ประมาณ $5"
    ref = f"contabo-invoice-{inv:%Y-%m}-d{left}"
    if test:
        reminders = " และ ".join(thai_day(inv.replace(day=inv.day - n)) for n in SEND_ON)
        title = "ทดสอบ: " + title
        why += f"\nนี่คืออีเมลทดสอบ ยังไม่ต้องเติมตอนนี้ ระบบจะเตือนจริงวันที่ {reminders} เวลา {FIRE_AT} น."
        ref = f"contabo-invoice-test-{day:%Y%m%d}"
    return {"title": title, "need": f"เติมเงิน {amount} ที่ Account > Billing & Payment ก่อน {when}",
            "why": why, "if_not": f"เลย {when} โดนค่า Restore ประมาณ $5", "link": PANEL, "ref": ref}


def run(*, test: bool = False, dry_run: bool = False, now: datetime | None = None,
        env: dict | None = None, post=None) -> dict:
    """Mail today's reminder, or say why today is not a reminder day. Refused / HubError propagate."""
    today = (now or datetime.now(email_ceo.THAI)).astimezone(email_ceo.THAI).date()
    left = days_left(today)
    if not test and not 0 <= left <= WINDOW:
        return {"mailed": False, "reason": f"not a reminder day: {left} days to the {invoice_date(today)} invoice"}
    body = email_ceo.build_payload(fields_for(today, test=test), kind=KIND, session=SESSION, role=ROLE, env=env)
    post = post or (lambda b: email_ceo._post(b, dry_run=dry_run))
    return {"ref": body["ref"], "title": body["title"], "hub": post(body)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--test", action="store_true", help="mail today's reminder now, marked ทดสอบ")
    ap.add_argument("--dry-run", action="store_true", help="show the mail the hub would send; send nothing")
    args = ap.parse_args(argv)
    try:
        got = run(test=args.test, dry_run=args.dry_run)
    except email_ceo.Refused as e:
        print(f"contabo_invoice_reminder: refused: {e}", file=sys.stderr)
        return email_ceo.EXIT_REFUSED
    except email_ceo.HubError as e:
        print(f"contabo_invoice_reminder: {e}", file=sys.stderr)
        return email_ceo.EXIT_HUB
    print(json.dumps(got, ensure_ascii=False, indent=2))
    return email_ceo.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
