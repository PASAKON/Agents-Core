#!/usr/bin/env python3
"""Durable, model-free LungNote reminder wakes. No dotenv loading."""
from __future__ import annotations

import argparse
import calendar
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.email_ceo import lungnote_request, HubError

TH = ZoneInfo("Asia/Bangkok")
ID_RE = re.compile(r"^[A-Za-z0-9_.:@=+\-]{1,128}$")
LEDGER = Path("/var/lib/sompong-reminders/ledger.jsonl")
LOG = logging.getLogger("sompong-reminders")


def parse_date(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result


def repeat_rule(text):
    tokens = re.findall(r"(?<!\w)repeat:\S*", text)
    if not tokens:
        return None
    if len(tokens) != 1:
        raise ValueError("repeat")
    match = re.fullmatch(r"repeat:((?:[1-9]|[12][0-9]|3[01]|last(?:-1)?)(?:,(?:[1-9]|[12][0-9]|3[01]|last(?:-1)?))*)@([01][0-9]|2[0-3]):([0-5][0-9])", tokens[0])
    if not match:
        raise ValueError("repeat")
    return match[1].split(","), int(match[2]), int(match[3])


def next_occurrence(rule, after):
    days, hour, minute = rule
    local = after.astimezone(TH)
    year, month = local.year, local.month
    while True:
        last = calendar.monthrange(year, month)[1]
        numbers = sorted({last if d == "last" else last - 1 if d == "last-1" else int(d) for d in days})
        for day in numbers:
            if day <= last:
                candidate = datetime(year, month, day, hour, minute, tzinfo=TH)
                if candidate > after:
                    return candidate
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def event_key(todo_id, due):
    return f"reminder:{todo_id}:{int(due.timestamp())}"


def payload(todo, due, now):
    key = event_key(str(todo["id"]), due)
    if not ID_RE.fullmatch(str(todo["id"])) or not ID_RE.fullmatch(key):
        raise ValueError("422")
    late = (now - due).total_seconds()
    marker = f" · ช้า {int(late // 60)} นาที" if late > 300 else ""
    text = f"[เตือนตามนัด · todo {todo['id']} · ครบกำหนด {due.astimezone(TH):%Y-%m-%d %H:%M} TH{marker}] " + todo["text"]
    if len(text) > 20000:
        raise ValueError("413")
    return dict(event_id=key, message_id=key, platform="line", chat_type="dm",
                target="reminder", sender_id="reminder", sender_name="ตัวเตือนตามนัด",
                role="reminder", ts=int(now.timestamp()), text=text)


def wake(body, env):
    req = urllib.request.Request("http://172.18.0.1:8644/v1/wake", method="POST",
        data=json.dumps(body, ensure_ascii=False).encode(), headers={
            "Authorization": "Bearer " + env["SOMPONG_EA_WAKE_KEY"], "Content-Type": "application/json"})
    # Never forward the credential through redirects.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=15) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.rows = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                row = json.loads(line)  # Fail closed on corruption; never replay accepted wakes.
                self.rows[row["key"]] = row

    def record(self, key, todo_id, due, now, status):
        row = dict(key=key, todo_id=todo_id, due_at=due.isoformat(), at=now.isoformat(), status=status)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as stream:
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.rows[key] = row


def run_pass(*, now=None, env=None, fetch=None, post=None, ledger=LEDGER, dry_run=False):
    now = now or datetime.now(timezone.utc)
    env = os.environ if env is None else env
    state = Ledger(ledger)
    offset = 0
    while True:
        todos = lungnote_request([
            ("done", "eq.false"), ("or", "(status.is.null,status.not.in.(done,cancelled,canceled))"),
            ("text", "like.*[SomPong*"), ("due_at", f"lte.{now.isoformat()}"),
            ("select", "*"), ("order", "due_at.asc,id.asc"), ("limit", "500"), ("offset", str(offset)),
        ], env, fetch)
        # Gather before PATCH changes the result set and invalidates offsets.
        if offset == 0:
            all_todos = []
        all_todos.extend(todos)
        if len(todos) < 500:
            break
        offset += len(todos)
    for todo in all_todos:
        if ("[SomPong" not in (todo.get("text") or "") or todo.get("done") or
                todo.get("cancelled") or todo.get("status") in {"done", "cancelled", "canceled"}):
            continue
        raw_id = str(todo.get("id", ""))
        safe_id = raw_id if ID_RE.fullmatch(raw_id) else hashlib.sha256(raw_id.encode()).hexdigest()
        try:
            due = parse_date(todo["due_at"])
        except (ValueError, TypeError, KeyError):
            LOG.warning("id=%s status=invalid-due", safe_id)
            continue
        if due > now:
            continue
        key = event_key(safe_id, due)
        try:
            rule = repeat_rule(todo["text"])
        except ValueError:
            rule = None
            warning_key = "invalid-repeat:" + safe_id
            if warning_key not in state.rows and not dry_run:
                state.record(warning_key, safe_id, due, now, "invalid-repeat")
                LOG.warning("id=%s status=invalid-repeat", safe_id)
        previous = state.rows.get(key, {}).get("status")
        expired = now - due > timedelta(hours=72)
        action = "patch" if rule and (previous == "accepted" or expired) else "skip" if previous else "expire" if expired else "wake"
        if previous and previous.startswith("rejected"):
            action = "skip"
        if dry_run:
            print(safe_id, due.isoformat(), action)
            continue
        if action == "skip":
            continue
        if action == "expire":
            state.record(key, safe_id, due, now, "expired")
            LOG.info("id=%s status=expired", safe_id)
            continue
        if action == "wake":
            try:
                body = payload(todo, due, now)
            except ValueError as exc:
                status = int(str(exc))
            else:
                try:
                    status = post(body) if post else wake(body, env)
                except (urllib.error.URLError, OSError, TimeoutError):
                    LOG.warning("id=%s status=retry", safe_id)
                    continue
            LOG.info("id=%s status=%s", safe_id, status)
            if status == 202:
                state.record(key, safe_id, due, now, "accepted")
            elif status in {400, 413, 422}:
                state.record(key, safe_id, due, now, f"rejected:{status}")
                continue
            else:
                continue
        if rule:
            following = next_occurrence(rule, now if expired and previous != "accepted" else due)
            try:
                result = lungnote_request([
                    ("id", f"eq.{raw_id}"), ("due_at", f"eq.{todo['due_at']}"),
                    ("done", "eq.false"), ("text", f"eq.{todo['text']}"),
                    ("or", "(status.is.null,status.not.in.(done,cancelled,canceled))"),
                ], env, fetch, body={"due_at": following.isoformat(),
                                    "due_text": following.strftime("%Y-%m-%d %H:%M TH")})
                LOG.info("id=%s status=%s", safe_id, "patched" if result else "patch-unmatched")
            except (HubError, OSError):
                LOG.warning("id=%s status=patch-retry", safe_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verb", choices=["serve", "fire-once", "list"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.verb == "list":
        run_pass(dry_run=True)
        return
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                run_pass()
            except Exception:
                LOG.error("status=pass-failed")  # No exception strings containing data or credentials.
                if args.verb != "serve":
                    raise SystemExit(1) from None
            if args.verb != "serve":
                break
            time.sleep(30)


if __name__ == "__main__":
    main()
