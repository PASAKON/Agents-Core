"""tools/household_reminders.py against a fake ClaudeFlow /internal/sompong/send (in-process HTTP server).

Proves: the due logic (days 10/15, -1 in every month length, from/until, grace, a catch-up across a month
boundary), "today" is Bangkok's date and not the box's, the ledger skips what was sent and the flock keeps
two runs apart, every rows-file refusal sends nothing and exits 4, each answer maps to its exit code,
dry-run sends nothing and needs no key, and the key never reaches stdout or stderr.
No network: every request goes to 127.0.0.1 on a port this test opened.
"""
from __future__ import annotations

import contextlib
import fcntl
import io
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import household_reminders as hr  # noqa: E402

KEY = "fake0000key0000fake0000key"   # a dummy, low entropy on purpose (gitleaks)
GROUP = "C" + "0" * 32
FAMILY2 = "C" + "0" * 31 + "1"
BERLIN = ZoneInfo("Europe/Berlin")


def water_row(**over) -> dict:
    row = {"id": "water-mwa", "platform": "line", "target": GROUP, "from": "2026-11-01", "until": None,
           "grace_days": 1, "fires": [{"day": 10, "text": "water bill: pay by the 15th"},
                                      {"day": 15, "text": "water bill: due today"}]}
    row.update(over)
    return row


def doc(*rows) -> dict:
    return {"version": 1, "rows": list(rows) or [water_row()]}


class FakeSend:
    """Answers POST /internal/sompong/send with queued (status, body) pairs, default 200 sent."""

    def __init__(self):
        self.requests: list[dict] = []
        self.answers: list[tuple[int, dict]] = []
        self.delay = 0.0

    def handler(self):
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):   # only a followed redirect would ever GET
                fake.requests.append({"method": "GET", "path": self.path, "auth": self.headers.get("Authorization")})
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                fake.requests.append({"method": "POST", "path": self.path, "auth": self.headers.get("Authorization"),
                                      "ctype": self.headers.get("Content-Type"), "body": body})
                if fake.delay:
                    time.sleep(fake.delay)
                status, out = fake.answers.pop(0) if fake.answers else (200, {"sent": True, "via": "push",
                                                                             "line_message_id": "1"})
                raw = json.dumps(out).encode()
                self.send_response(status)
                if 300 <= status < 400:
                    self.send_header("Location", f"http://127.0.0.1:{self.server.server_address[1]}/elsewhere")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        return H


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass   # the timeout test hangs up on a slow answer; the broken pipe is expected


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.rows = self.dir / "rows.json"
        self.state = self.dir / "state"
        p = mock.patch.object(hr, "EXPECTED_UID", os.getuid())
        p.start()
        self.addCleanup(p.stop)
        self.fake = FakeSend()
        self.srv = QuietServer(("127.0.0.1", 0), self.fake.handler())
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.env = {"SOMPONG_INTERNAL_KEY": KEY, "SOMPONG_INTERNAL_BASE_URL": self.base}

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def write_rows(self, content, mode=0o600) -> Path:
        raw = content if isinstance(content, (bytes, str)) else json.dumps(content, ensure_ascii=False)
        self.rows.write_bytes(raw.encode() if isinstance(raw, str) else raw)
        os.chmod(self.rows, mode)
        return self.rows

    def go(self, day: str | None, *, dry_run=False, env=None, now=None, **kw) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = hr.run(rows_path=str(self.rows), state_dir=str(self.state),
                          today=date.fromisoformat(day) if day else None, dry_run=dry_run,
                          env=self.env if env is None else env, now=now, **kw)
        return code, out.getvalue(), err.getvalue()

    def ledger_lines(self) -> list[dict]:
        p = self.state / hr.LEDGER_NAME
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


class DueLogic(unittest.TestCase):
    def due(self, rows, day: str) -> list[tuple[str, int, str]]:
        rows = hr.parse_rows(json.dumps({"version": 1, "rows": rows}).encode())
        return [(d.row.id, d.fire.day, d.date.isoformat()) for d in hr.due_fires(rows, date.fromisoformat(day))]

    def test_day_10_and_15_with_one_grace_day(self):
        r = [water_row()]
        self.assertEqual(self.due(r, "2026-11-09"), [])
        self.assertEqual(self.due(r, "2026-11-10"), [("water-mwa", 10, "2026-11-10")])
        self.assertEqual(self.due(r, "2026-11-11"), [("water-mwa", 10, "2026-11-10")])   # catch-up
        self.assertEqual(self.due(r, "2026-11-12"), [])
        self.assertEqual(self.due(r, "2026-11-15"), [("water-mwa", 15, "2026-11-15")])
        self.assertEqual(self.due(r, "2026-11-16"), [("water-mwa", 15, "2026-11-15")])
        self.assertEqual(self.due(r, "2026-11-17"), [])

    def test_grace_zero_is_the_day_only(self):
        r = [water_row(grace_days=0)]
        self.assertEqual(self.due(r, "2026-11-10"), [("water-mwa", 10, "2026-11-10")])
        self.assertEqual(self.due(r, "2026-11-11"), [])

    def test_wider_grace_catches_both_fires(self):
        r = [water_row(grace_days=7)]
        self.assertEqual(self.due(r, "2026-11-16"), [("water-mwa", 10, "2026-11-10"), ("water-mwa", 15, "2026-11-15")])

    def test_from_and_until(self):
        r = [water_row(until="2026-12-12")]
        self.assertEqual(self.due(r, "2026-10-10"), [])                  # before from
        self.assertEqual(self.due(r, "2026-12-10"), [("water-mwa", 10, "2026-12-10")])
        self.assertEqual(self.due(r, "2026-12-15"), [])                  # after until
        self.assertEqual(self.due(r, "2027-01-10"), [])
        # from is compared with the fire date, not with today: a fire on the 10th before from never catches up
        self.assertEqual(self.due([water_row(**{"from": "2026-11-11"})], "2026-11-11"), [])

    def test_last_day_in_every_month_length(self):
        r = [{"id": "rent", "platform": "line", "target": GROUP, "from": "2026-01-01", "grace_days": 0,
              "fires": [{"day": -1, "text": "rent"}]}]
        for today in ("2027-02-28", "2028-02-29", "2026-11-30", "2026-12-31", "2027-04-30"):
            self.assertEqual(self.due(r, today), [("rent", -1, today)], today)
        for today in ("2028-02-28", "2026-11-29", "2026-12-30", "2026-11-01"):
            self.assertEqual(self.due(r, today), [], today)

    def test_catch_up_crosses_a_month_boundary(self):
        r = [{"id": "rent", "platform": "line", "target": GROUP, "from": "2026-01-01", "grace_days": 1,
              "fires": [{"day": -1, "text": "rent"}]}]
        self.assertEqual(self.due(r, "2027-01-01"), [("rent", -1, "2026-12-31")])
        self.assertEqual(self.due(r, "2027-03-01"), [("rent", -1, "2027-02-28")])
        self.assertEqual(self.due(r, "2027-01-02"), [])

    def test_two_rows_due_the_same_day_keep_file_order(self):
        r = [water_row(), water_row(id="power-pea", target=FAMILY2, fires=[{"day": 10, "text": "power"}])]
        self.assertEqual(self.due(r, "2026-11-10"), [("water-mwa", 10, "2026-11-10"), ("power-pea", 10, "2026-11-10")])


class BangkokDate(Base):
    def test_bangkok_date_not_the_box_clock(self):
        # 19:30 in Berlin on the 9th is 01:30 on the 10th in Bangkok.
        self.assertEqual(hr.bangkok_today(datetime(2026, 11, 9, 19, 30, tzinfo=BERLIN)), date(2026, 11, 10))
        # 01:30 in Berlin on the 10th is 07:30 on the 10th in Bangkok.
        self.assertEqual(hr.bangkok_today(datetime(2026, 11, 10, 1, 30, tzinfo=BERLIN)), date(2026, 11, 10))
        self.assertEqual(hr.bangkok_today(datetime(2026, 11, 9, 17, 59, tzinfo=BERLIN)), date(2026, 11, 9))

    def test_a_run_on_the_9th_in_berlin_sends_the_10th(self):
        self.write_rows(doc())
        self.addCleanup(time.tzset)   # runs after patch.dict has put TZ back
        with mock.patch.dict(os.environ, {"TZ": "Europe/Berlin"}):
            time.tzset()
            self.assertEqual(datetime.fromtimestamp(datetime(2026, 11, 9, 19, 30, tzinfo=BERLIN).timestamp()).day, 9)
            code, out, _ = self.go(None, now=datetime(2026, 11, 9, 19, 30, tzinfo=BERLIN))
        self.assertEqual(code, 0)
        self.assertIn("2026-11-10 (Asia/Bangkok)", out)
        self.assertEqual([r["body"]["text"] for r in self.fake.requests], ["water bill: pay by the 15th"])

    def test_default_clock_is_bangkok(self):
        fixed = datetime(2026, 11, 9, 18, 30, tzinfo=ZoneInfo("UTC"))   # 01:30 on the 10th in Bangkok

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

        with mock.patch.object(hr, "datetime", Clock):
            self.assertEqual(hr.bangkok_today(), date(2026, 11, 10))


class SendAndLedger(Base):
    def test_sends_the_body_ledgers_and_dedupes(self):
        self.write_rows(doc())
        code, out, err = self.go("2026-11-10")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.fake.requests), 1)
        req = self.fake.requests[0]
        self.assertEqual(req["path"], "/internal/sompong/send")
        self.assertEqual(req["auth"], f"Bearer {KEY}")
        self.assertEqual(req["ctype"], "application/json")
        self.assertEqual(req["body"], {"target": GROUP, "text": "water bill: pay by the 15th"})
        self.assertIn("water-mwa day=10 date=2026-11-10 target=...0000 status=200 sent via=push", out)
        self.assertNotIn(GROUP, out + err)
        (line,) = self.ledger_lines()
        self.assertEqual((line["id"], line["month"], line["day"], line["status"]), ("water-mwa", "2026-11", 10, 200))
        self.assertEqual(os.stat(self.state / hr.LEDGER_NAME).st_mode & 0o777, 0o600)
        # the same day again, and the catch-up day after: nothing sent twice
        for again in ("2026-11-10", "2026-11-11"):
            code, out, _ = self.go(again)
            self.assertEqual(code, 0)
            self.assertIn("already sent (ledger), skipped", out)
        self.assertEqual(len(self.fake.requests), 1)
        # next month's 10th is a new key
        self.assertEqual(self.go("2026-12-10")[0], 0)
        self.assertEqual(len(self.fake.requests), 2)
        self.assertEqual([x["month"] for x in self.ledger_lines()], ["2026-11", "2026-12"])

    def test_nothing_due_sends_nothing_and_needs_no_key(self):
        self.write_rows(doc())
        code, out, _ = self.go("2026-11-12", env={})
        self.assertEqual(code, 0)
        self.assertIn("0 fire(s) due", out)
        self.assertEqual(self.fake.requests, [])

    def test_two_fires_due_on_one_day(self):
        self.write_rows(doc(water_row(), water_row(id="power-pea", target=FAMILY2,
                                                   fires=[{"day": 10, "text": "power bill"}])))
        code, out, _ = self.go("2026-11-10")
        self.assertEqual(code, 0)
        self.assertEqual([r["body"] for r in self.fake.requests],
                         [{"target": GROUP, "text": "water bill: pay by the 15th"},
                          {"target": FAMILY2, "text": "power bill"}])
        self.assertEqual([(x["id"], x["day"]) for x in self.ledger_lines()], [("water-mwa", 10), ("power-pea", 10)])

    def test_mixed_failures_still_send_the_others_and_report_the_worst(self):
        rows = doc(water_row(), water_row(id="power-pea", target=FAMILY2, fires=[{"day": 10, "text": "power"}]))
        self.write_rows(rows)
        self.fake.answers = [(403, {"error": "forbidden"}), (200, {"sent": True, "via": "push"})]
        code, out, _ = self.go("2026-11-10")
        self.assertEqual(code, 2)
        self.assertEqual(len(self.fake.requests), 2)
        self.assertEqual([x["id"] for x in self.ledger_lines()], ["power-pea"])
        self.assertIn("water-mwa day=10 date=2026-11-10 target=...0000 status=403 refused error=forbidden", out)
        # refused + transient: 3 wins so systemd retries
        os.unlink(self.state / hr.LEDGER_NAME)
        self.fake.requests.clear()
        self.fake.answers = [(403, {"error": "forbidden"}), (500, {"error": "boom"})]
        self.assertEqual(self.go("2026-11-10")[0], 3)
        self.assertEqual(len(self.fake.requests), 2)
        self.assertEqual(self.ledger_lines(), [])

    def test_retry_sends_only_what_is_still_unsent(self):
        self.write_rows(doc(water_row(), water_row(id="power-pea", target=FAMILY2, fires=[{"day": 10, "text": "p"}])))
        self.fake.answers = [(200, {"sent": True, "via": "push"}), (502, {"error": "send_failed"})]
        self.assertEqual(self.go("2026-11-10")[0], 3)
        self.assertEqual(self.go("2026-11-10")[0], 0)
        self.assertEqual([r["body"]["target"] for r in self.fake.requests], [GROUP, FAMILY2, FAMILY2])
        self.assertEqual([x["id"] for x in self.ledger_lines()], ["water-mwa", "power-pea"])

    def test_flock_keeps_a_second_run_out(self):
        self.write_rows(doc())
        self.state.mkdir()
        fd = os.open(self.state / hr.LEDGER_NAME, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            code, _, err = self.go("2026-11-10", lock_wait=0)
            self.assertEqual(code, 3)
            self.assertIn("another run holds the lock", err)
            self.assertEqual(self.fake.requests, [])
        finally:
            os.close(fd)

    def test_a_waiting_run_reads_the_ledger_the_lock_holder_wrote(self):
        self.write_rows(doc())
        self.state.mkdir()
        fd = os.open(self.state / hr.LEDGER_NAME, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)

        def other_run_finishes():
            time.sleep(0.4)
            os.write(fd, b'{"id":"water-mwa","month":"2026-11","day":10,"status":200}\n')
            os.close(fd)   # releases the lock

        t = threading.Thread(target=other_run_finishes)
        t.start()
        code, out, _ = self.go("2026-11-10", lock_wait=5)
        t.join()
        self.assertEqual(code, 0)
        self.assertIn("already sent (ledger), skipped", out)
        self.assertEqual(self.fake.requests, [])

    def test_a_torn_ledger_line_is_ignored(self):
        self.write_rows(doc())
        self.state.mkdir()
        (self.state / hr.LEDGER_NAME).write_text('{"id":"water-mwa","mon')
        self.assertEqual(self.go("2026-11-10")[0], 0)
        self.assertEqual(len(self.fake.requests), 1)
        # our line starts on a fresh line, so the next run still sees it
        self.assertEqual(self.go("2026-11-10")[0], 0)
        self.assertEqual(len(self.fake.requests), 1)
        self.assertEqual((self.state / hr.LEDGER_NAME).read_text().splitlines()[0], '{"id":"water-mwa","mon')


class ExitCodes(Base):
    CASES = [
        (200, {"sent": True, "via": "push"}, 0),
        (400, {"error": "invalid_text"}, 2),
        (403, {"error": "forbidden"}, 2),
        (401, {"error": "unauthorized"}, 3),
        (408, {}, 3),
        (429, {"error": "rate_limited"}, 3),
        (429, {"error": "push_quota_guard"}, 2),
        (500, {"error": "internal"}, 3),
        (502, {"error": "send_failed"}, 3),
    ]

    def test_status_mapping(self):
        self.write_rows(doc())
        for status, body, want in self.CASES:
            with self.subTest(status=status, body=body):
                if self.state.exists():
                    (self.state / hr.LEDGER_NAME).unlink(missing_ok=True)
                self.fake.answers = [(status, body)]
                code, out, err = self.go("2026-11-10")
                self.assertEqual(code, want, out + err)
                self.assertIn(f"status={status}", out)
                self.assertEqual(len(self.ledger_lines()), 1 if want == 0 else 0)
                self.assertNotIn(KEY, out + err)

    def test_connection_refused_is_transient(self):
        self.write_rows(doc())
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        code, out, err = self.go("2026-11-10", env={"SOMPONG_INTERNAL_KEY": KEY,
                                                    "SOMPONG_INTERNAL_BASE_URL": f"http://127.0.0.1:{port}"})
        self.assertEqual(code, 3)
        self.assertIn("status=none transient error=ConnectionRefusedError", out)
        self.assertNotIn(KEY, out + err)
        self.assertEqual(self.ledger_lines(), [])

    def test_timeout_is_transient(self):
        self.write_rows(doc())
        self.fake.delay = 1.0
        code, out, _ = self.go("2026-11-10", timeout=0.2)
        self.assertEqual(code, 3)
        self.assertIn("status=none transient", out)
        self.assertEqual(self.ledger_lines(), [])

    def test_no_key_is_transient_and_sends_nothing(self):
        self.write_rows(doc())
        code, _, err = self.go("2026-11-10", env={"SOMPONG_INTERNAL_BASE_URL": self.base})
        self.assertEqual(code, 3)
        self.assertIn("no SOMPONG_INTERNAL_KEY", err)
        self.assertEqual(self.fake.requests, [])

    def test_a_redirect_is_not_followed(self):
        # urllib would follow a 302 to a POST as a GET carrying the same Authorization header
        self.write_rows(doc())
        for status in (302, 307):
            with self.subTest(status=status):
                self.fake.requests.clear()
                self.fake.answers = [(status, {})]
                code, out, _ = self.go("2026-11-10")
                self.assertEqual(code, 2)
                self.assertEqual([r["method"] for r in self.fake.requests], ["POST"])
                self.assertIn(f"status={status} refused", out)

    def test_classify_table(self):
        self.assertEqual(hr.classify(None, ""), 3)
        self.assertEqual(hr.classify(204, ""), 0)
        self.assertEqual(hr.classify(415, "unsupported_media_for_line"), 2)
        self.assertEqual(hr.classify(429, ""), 3)
        self.assertEqual(hr.classify(503, ""), 3)


class KeyNeverPrinted(Base):
    def test_main_output_never_holds_the_key(self):
        self.write_rows(doc())
        seen = []
        for status, body in ((200, {"sent": True, "via": "push"}), (401, {"error": "unauthorized"}),
                             (500, {"error": KEY})):   # even an answer that echoes the key
            if self.state.exists():
                (self.state / hr.LEDGER_NAME).unlink(missing_ok=True)
            self.fake.answers = [(status, body)]
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, self.env), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                hr.main(["--rows", str(self.rows), "--state-dir", str(self.state), "--date", "2026-11-10"])
            seen.append(out.getvalue() + err.getvalue())
        self.assertTrue(all("status=" in s for s in seen))
        for s in seen:
            self.assertNotIn(KEY, s)
            self.assertNotIn(KEY[-12:], s)

    def test_say_scrubs_the_key_from_any_line(self):
        self.write_rows(doc())
        with mock.patch.object(hr, "_label", lambda d: f"{d.row.id} leaked={KEY}"):
            code, out, err = self.go("2026-11-10")
        self.assertEqual(code, 0)
        self.assertIn("leaked=[REDACTED]", out)
        self.assertNotIn(KEY, out + err)

    def test_a_key_with_a_newline_is_not_echoed(self):
        self.write_rows(doc())
        bad = KEY + "\nX-Evil: 1"
        code, out, err = self.go("2026-11-10", env={"SOMPONG_INTERNAL_KEY": bad, "SOMPONG_INTERNAL_BASE_URL": self.base})
        self.assertEqual(code, 3)
        self.assertNotIn(KEY, out + err)


class DryRun(Base):
    def test_dry_run_sends_nothing_needs_no_key_and_creates_no_state(self):
        self.write_rows(doc())
        code, out, _ = self.go("2026-11-10", dry_run=True, env={"SOMPONG_INTERNAL_BASE_URL": self.base})
        self.assertEqual(code, 0)
        self.assertEqual(self.fake.requests, [])
        self.assertFalse(self.state.exists())
        self.assertIn("would send", out)
        self.assertIn("| water bill: pay by the 15th", out)
        self.assertIn("target=...0000", out)
        self.assertNotIn(GROUP, out)

    def test_dry_run_shows_what_the_ledger_already_holds(self):
        self.write_rows(doc())
        self.assertEqual(self.go("2026-11-15")[0], 0)
        code, out, _ = self.go("2026-11-15", dry_run=True, env={})
        self.assertEqual(code, 0)
        self.assertIn("already sent (ledger), would skip", out)
        self.assertEqual(len(self.fake.requests), 1)


    def test_dry_run_with_an_unreadable_ledger_still_shows_the_fires(self):
        self.write_rows(doc())
        with mock.patch.object(hr, "peek_ledger", lambda state_dir: None):
            code, out, _ = self.go("2026-11-10", dry_run=True, env={})
        self.assertEqual(code, 0)
        self.assertIn("cannot read the ledger", out)
        self.assertIn("would send", out)


class RowsRefusals(Base):
    def assert_refused(self, why: str, *, path: Path | None = None):
        out_io, err_io = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out_io), contextlib.redirect_stderr(err_io):
            code = hr.run(rows_path=str(path or self.rows), state_dir=str(self.state),
                          today=date(2026, 11, 10), env=self.env)
        out, err = out_io.getvalue(), err_io.getvalue()
        self.assertEqual(code, 4, out + err)
        self.assertIn("rows file refused", err)
        self.assertIn(why, err)
        self.assertEqual(self.fake.requests, [])
        self.assertFalse(self.state.exists())

    def test_a_good_file_loads(self):
        self.write_rows(doc())
        self.assertEqual([r.id for r in hr.load_rows(str(self.rows))], ["water-mwa"])

    def test_symlink(self):
        self.write_rows(doc())
        link = self.dir / "link.json"
        link.symlink_to(self.rows)
        self.assert_refused("symlink", path=link)

    def test_group_readable(self):
        self.write_rows(doc(), mode=0o640)
        self.assert_refused("group/other bits")

    def test_other_readable(self):
        self.write_rows(doc(), mode=0o604)
        self.assert_refused("group/other bits")

    def test_wrong_owner(self):
        self.write_rows(doc())
        with mock.patch.object(hr, "EXPECTED_UID", os.getuid() + 1):
            self.assert_refused("owned by uid")

    def test_too_big(self):
        body = json.dumps(doc())
        self.write_rows(body + " " * (hr.MAX_ROWS_BYTES + 1 - len(body)))
        self.assert_refused("over the 65536-byte limit")

    def test_bad_json(self):
        self.write_rows('{"version": 1, "rows": [')
        self.assert_refused("not valid JSON")

    def test_missing_file(self):
        self.assert_refused("cannot open")

    def test_not_a_regular_file(self):
        fifo = self.dir / "fifo.json"
        os.mkfifo(fifo, 0o600)
        self.assert_refused("not a regular file", path=fifo)

    def test_schema_refusals(self):
        bad = {
            "unknown key(s): note": doc(water_row(note="x")),
            "unknown key(s): extra": {**doc(), "extra": 1},
            "fires[0] has unknown key(s): hour": doc(water_row(fires=[{"day": 10, "text": "t", "hour": 9}])),
            "target must match": doc(water_row(target="C" + "0" * 31)),
            "target must match ": doc(water_row(target="X" + "0" * 32)),
            "target must match  ": doc(water_row(target="C" + "A" * 32)),
            "platform must be": doc(water_row(platform="telegram")),
            "id must match": doc(water_row(id="Water_MWA")),
            "day must be 1..28 or -1": doc(water_row(fires=[{"day": 29, "text": "t"}])),
            "day must be an integer": doc(water_row(fires=[{"day": True, "text": "t"}])),
            "text must be 1..2000": doc(water_row(fires=[{"day": 10, "text": "x" * 2001}])),
            "text must be 1..2000 ": doc(water_row(fires=[{"day": 10, "text": "   "}])),
            "same day twice": doc(water_row(fires=[{"day": 10, "text": "a"}, {"day": 10, "text": "b"}])),
            "two rows share an id": doc(water_row(), water_row()),
            "grace_days must be 0..27": doc(water_row(grace_days=28)),
            "from must be a YYYY-MM-DD": doc(water_row(**{"from": "20261101"})),
            "until is before its from": doc(water_row(until="2026-10-01")),
            "missing key(s): target": doc({k: v for k, v in water_row().items() if k != "target"}),
            "version must be 1": {"version": 2, "rows": []},
        }
        for why, content in bad.items():
            with self.subTest(why=why):
                self.write_rows(content)
                self.assert_refused(why.strip())

    def test_duplicate_key_and_nan(self):
        self.write_rows('{"version": 1, "version": 1, "rows": []}')
        self.assert_refused("duplicate key")
        self.write_rows('{"version": NaN, "rows": []}')
        self.assert_refused("NaN is not allowed")

    def test_example_file_in_the_repo_is_valid(self):
        example = Path(__file__).resolve().parent.parent / "deploy" / "household-reminders.example.json"
        rows = hr.parse_rows(example.read_bytes())
        self.assertTrue(rows)
        for r in rows:
            self.assertRegex(r.target, r"^[CUR]0+[0-9a-f]?$")   # dummy targets only: this repo is public


if __name__ == "__main__":
    unittest.main()
