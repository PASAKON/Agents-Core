#!/usr/bin/env python3
"""Post the household reminders that are due today into their allowlisted LINE chat, once a day.

Why: a household bill (the first one is the water bill, on the 10th and the 15th of every month from
November 2026) has to land in the family LINE group as a plain text message on the right morning, every
month, with nobody remembering to send it. That needs no model and no new session: a timer, a JSON file
of rows and the send path the COO session (SomPong) already uses. Adding the next bill is one more row
in the rows file. It is not new code and not a new unit.

How it sends: ClaudeFlow's SomPong internal API, `POST <base>/internal/sompong/send` with
`Authorization: Bearer $SOMPONG_INTERNAL_KEY` and the body `{"target": "<C|U|R + 32 hex>", "text": "..."}`
(the same body SomPong's own client sends for LINE: no `platform`, which defaults to line, and no
`reply_token`, so ClaudeFlow pushes). ClaudeFlow checks the target against its allowlist
(LINE_SOMPONG_ALLOWED_GROUPS plus the CEO's user id), strips markdown decoration and double quotes from
the text, refuses a push that would eat into the monthly push-quota reserve, and logs the message as a
bot reply in that chat's log, so SomPong sees it in context. This tool talks to it only over HTTP.

Rows file (default /etc/mooniex/household-reminders.json; example: deploy/household-reminders.example.json):
    {"version": 1, "rows": [{"id": "water-mwa", "platform": "line", "target": "C<32 hex>",
      "from": "2026-11-01", "until": null, "grace_days": 1,
      "fires": [{"day": 10, "text": "..."}, {"day": 15, "text": "..."}]}]}
  - It is refused (exit 4, nothing sent) unless it is a regular file, opened with O_NOFOLLOW, owned by
    root, with no group or other permission bits (mode & 0o077 == 0), at most 64 KiB and valid JSON.
  - Strict schema: an unknown key or a duplicate key is an error. id is [a-z0-9-]{1,40} and unique.
    platform is "line" only. target is ^[CUR][0-9a-f]{32}$. from is YYYY-MM-DD. until is YYYY-MM-DD or
    null (default null). grace_days is 0..27 (default 1). day is 1..28, or -1 for the last day of the
    month, unique within a row. text is 1..2000 characters and not blank.

When a fire is due: "today" is the date in Asia/Bangkok (zoneinfo), never the box clock, because Contabo
runs Europe/Berlin. A fire is due when 0 <= today - fire_date <= grace_days and from <= fire_date <= until.
The fire dates of this month and of the previous month are both checked, so a catch-up run after
downtime (the timer has Persistent=true) also crosses a month boundary: the reminder of the 31st still
goes out on the 1st with grace_days >= 1. grace_days stops at 27, so no fire can be due twice.

Ledger: <state-dir>/sent.jsonl (default /var/lib/household-reminders). One line per sent fire, keyed by
(row id, YYYY-MM of the fire date, day). A key already there is skipped. A line is appended only after a
2xx. The run holds an flock on the ledger from reading it to its last append, so two runs never both send
the same fire. Delivery is at least once: if ClaudeFlow pushed but its answer never arrived (a timeout or
a 502 after LINE got the message), the retry sends the reminder again.

Output: one line per fire with the row id, the day and the HTTP status. The target is shown only as its
last 4 characters, the text only in --dry-run, and the key never.

Verbs:
    python3 tools/household_reminders.py                         # the timer: send what is due today
    python3 tools/household_reminders.py --dry-run [--date D]    # show what would be sent; sends nothing, needs no key
    python3 tools/household_reminders.py --rows PATH --state-dir DIR --date YYYY-MM-DD
  SOMPONG_INTERNAL_BASE_URL overrides the base URL (default http://127.0.0.1:3011). HTTP timeout 20 s.

Exit:
    0  every due fire was sent (or was already in the ledger), or nothing is due
    2  the API refused a fire: any 4xx except 401/408/429 (403 forbidden = target not on the allowlist,
       400 = bad body), and 429 push_quota_guard (the monthly push-quota reserve). Not retried.
       Also when a fire was sent but its ledger line could not be written: a retry would post it twice.
    3  transient: no SOMPONG_INTERNAL_KEY, connection error, timeout, 5xx, 401, 408, 429 rate_limited,
       or the ledger lock is held by another run. systemd retries.
    4  the rows file was refused; nothing was sent
  With several due fires every one is still tried, and the exit is the highest code among them: 3 outranks
  2 so that systemd retries the transient fire; a fire that is refused again only repeats its 2.
"""
from __future__ import annotations

import argparse
import calendar
import fcntl
import http.client
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")
DEFAULT_ROWS = "/etc/mooniex/household-reminders.json"
DEFAULT_STATE_DIR = "/var/lib/household-reminders"
LEDGER_NAME = "sent.jsonl"
DEFAULT_BASE_URL = "http://127.0.0.1:3011"
SEND_PATH = "/internal/sompong/send"
HTTP_TIMEOUT_SEC = 20.0
LOCK_WAIT_SEC = 60.0
MAX_ROWS_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
EXPECTED_UID = 0                    # the rows file must belong to root; tests patch this

EXIT_OK, EXIT_REFUSED, EXIT_TRANSIENT, EXIT_ROWS = 0, 2, 3, 4

ID_RE = re.compile(r"[a-z0-9-]{1,40}")
TARGET_RE = re.compile(r"[CUR][0-9a-f]{32}")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
TOKEN_RE = re.compile(r"[a-z_]{1,40}")    # an error/via word from the API, safe to print
TOP_KEYS = {"version", "rows"}
ROW_REQUIRED = {"id", "platform", "target", "from", "fires"}
ROW_OPTIONAL = {"until", "grace_days"}
FIRE_KEYS = {"day", "text"}
MAX_TEXT = 2000
MAX_GRACE = 27
DEFAULT_GRACE = 1


class RowsError(Exception):
    """The rows file is refused: nothing is sent (exit 4)."""


class LedgerBusy(Exception):
    """Another run holds the ledger lock (exit 3)."""


@dataclass(frozen=True)
class Fire:
    day: int
    text: str


@dataclass(frozen=True)
class Row:
    id: str
    platform: str
    target: str
    start: date
    until: date | None
    grace_days: int
    fires: tuple[Fire, ...]


@dataclass(frozen=True)
class Due:
    row: Row
    fire: Fire
    date: date

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.row.id, f"{self.date:%Y-%m}", self.fire.day)


# --- rows file ---------------------------------------------------------------------------------

def read_rows_file(path: str) -> bytes:
    """The raw bytes of the rows file, or RowsError when it is not a small, private, root-owned file."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        if os.path.islink(path):
            raise RowsError(f"{path} is a symlink") from None
        raise RowsError(f"cannot open {path}: {exc.strerror or type(exc).__name__}") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise RowsError(f"{path} is not a regular file")
        if st.st_uid != EXPECTED_UID:
            raise RowsError(f"{path} is owned by uid {st.st_uid}, not {EXPECTED_UID}")
        if st.st_mode & 0o077:
            raise RowsError(f"{path} has mode {stat.S_IMODE(st.st_mode):04o}; group/other bits must be 0 (chmod 0600)")
        if st.st_size > MAX_ROWS_BYTES:
            raise RowsError(f"{path} is {st.st_size} bytes, over the {MAX_ROWS_BYTES}-byte limit")
        chunks, size = [], 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_ROWS_BYTES:
                raise RowsError(f"{path} grew past the {MAX_ROWS_BYTES}-byte limit while being read")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _no_duplicate_keys(pairs: list) -> dict:
    out = {}
    for k, v in pairs:
        if k in out:
            raise RowsError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _no_constant(name: str):
    raise RowsError(f"{name} is not allowed")


def _int(value, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RowsError(f"{where} must be an integer")
    return value


def _date(value, where: str) -> date:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        raise RowsError(f"{where} must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RowsError(f"{where} is not a real date: {value}") from None


def _keys(obj, required: set, optional: set, where: str) -> None:
    if not isinstance(obj, dict):
        raise RowsError(f"{where} must be an object")
    unknown = sorted(set(obj) - required - optional)
    if unknown:
        raise RowsError(f"{where} has unknown key(s): {', '.join(unknown)}")
    missing = sorted(required - set(obj))
    if missing:
        raise RowsError(f"{where} is missing key(s): {', '.join(missing)}")


def _fire(obj, where: str) -> Fire:
    _keys(obj, FIRE_KEYS, set(), where)
    day = _int(obj["day"], f"{where}.day")
    if not (1 <= day <= 28 or day == -1):
        raise RowsError(f"{where}.day must be 1..28 or -1 (last day of the month), not {day}")
    text = obj["text"]
    if not isinstance(text, str) or not 1 <= len(text) <= MAX_TEXT or not text.strip():
        raise RowsError(f"{where}.text must be 1..{MAX_TEXT} characters and not blank")
    return Fire(day=day, text=text)


def _row(obj, where: str) -> Row:
    _keys(obj, ROW_REQUIRED, ROW_OPTIONAL, where)
    rid = obj["id"]
    if not isinstance(rid, str) or not ID_RE.fullmatch(rid):
        raise RowsError(f"{where}.id must match [a-z0-9-]{{1,40}}")
    where = f"row {rid}"
    if obj["platform"] != "line":
        raise RowsError(f"{where}.platform must be \"line\"")
    target = obj["target"]
    if not isinstance(target, str) or not TARGET_RE.fullmatch(target):
        raise RowsError(f"{where}.target must match ^[CUR][0-9a-f]{{32}}$")
    start = _date(obj["from"], f"{where}.from")
    until = None if obj.get("until") is None else _date(obj["until"], f"{where}.until")
    if until is not None and until < start:
        raise RowsError(f"{where}.until is before its from")
    grace = _int(obj.get("grace_days", DEFAULT_GRACE), f"{where}.grace_days")
    if not 0 <= grace <= MAX_GRACE:
        raise RowsError(f"{where}.grace_days must be 0..{MAX_GRACE}")
    fires_in = obj["fires"]
    if not isinstance(fires_in, list) or not fires_in:
        raise RowsError(f"{where}.fires must be a non-empty list")
    fires = tuple(_fire(f, f"{where}.fires[{i}]") for i, f in enumerate(fires_in))
    days = [f.day for f in fires]
    if len(set(days)) != len(days):
        raise RowsError(f"{where}.fires has the same day twice")
    return Row(id=rid, platform="line", target=target, start=start, until=until, grace_days=grace, fires=fires)


def parse_rows(raw: bytes) -> list[Row]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise RowsError("not UTF-8") from None
    try:
        doc = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_no_constant)
    except json.JSONDecodeError as exc:
        raise RowsError(f"not valid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from None
    _keys(doc, TOP_KEYS, set(), "the file")
    if _int(doc["version"], "version") != 1:
        raise RowsError("version must be 1")
    if not isinstance(doc["rows"], list):
        raise RowsError("rows must be a list")
    rows = [_row(r, f"rows[{i}]") for i, r in enumerate(doc["rows"])]
    ids = [r.id for r in rows]
    if len(set(ids)) != len(ids):
        raise RowsError("two rows share an id")
    return rows


def load_rows(path: str) -> list[Row]:
    raw = read_rows_file(path)          # its errors already name the path
    try:
        return parse_rows(raw)
    except RowsError as exc:
        raise RowsError(f"{path}: {exc}") from None


# --- what is due -------------------------------------------------------------------------------

def bangkok_today(now: datetime | None = None) -> date:
    """Today's date in Asia/Bangkok, whatever zone the box runs in."""
    return (now or datetime.now(timezone.utc)).astimezone(BANGKOK).date()


def fire_date(year: int, month: int, day: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1] if day == -1 else day)


def due_fires(rows: list[Row], today: date) -> list[Due]:
    """Every fire whose date this month or last month falls in [today - grace_days, today], within from..until."""
    prev = today.replace(day=1) - timedelta(days=1)
    months = ((prev.year, prev.month), (today.year, today.month))
    out: list[tuple[date, int, int, Due]] = []
    for r_i, row in enumerate(rows):
        for f_i, fire in enumerate(row.fires):
            for year, month in months:
                d = fire_date(year, month, fire.day)
                if not 0 <= (today - d).days <= row.grace_days:
                    continue
                if d < row.start or (row.until is not None and d > row.until):
                    continue
                out.append((d, r_i, f_i, Due(row=row, fire=fire, date=d)))
    return [due for *_, due in sorted(out, key=lambda t: t[:3])]


# --- ledger ------------------------------------------------------------------------------------

def _parse_ledger(raw: bytes) -> set[tuple[str, str, int]]:
    keys = set()
    for line in raw.decode("utf-8", "replace").splitlines():
        try:
            rec = json.loads(line)
            keys.add((str(rec["id"]), str(rec["month"]), int(rec["day"])))
        except (ValueError, KeyError, TypeError):
            continue   # a torn line from a crash: at worst that one fire is sent again
    return keys


def _read_all(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def peek_ledger(state_dir: str) -> set[tuple[str, str, int]] | None:
    """The ledger's keys without locking or creating anything (for --dry-run); None when unreadable."""
    try:
        fd = os.open(os.path.join(state_dir, LEDGER_NAME), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return set()
    except OSError:
        return None
    try:
        return _parse_ledger(_read_all(fd))
    finally:
        os.close(fd)


class Ledger:
    """sent.jsonl under an exclusive flock, held from the first read to the last append."""

    def __init__(self, state_dir: str, lock_wait: float = LOCK_WAIT_SEC):
        os.makedirs(state_dir, mode=0o700, exist_ok=True)
        self.fd = os.open(os.path.join(state_dir, LEDGER_NAME),
                          os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        deadline = time.monotonic() + lock_wait
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(self.fd)
                    raise LedgerBusy(f"another run holds the lock on {os.path.join(state_dir, LEDGER_NAME)}") from None
                time.sleep(0.1)
        raw = _read_all(self.fd)
        self.keys = _parse_ledger(raw)
        self._torn_tail = bool(raw) and not raw.endswith(b"\n")   # a crash mid-line: start ours on a new line

    def append(self, due: Due, status: int, via: str) -> None:
        rec = {"id": due.row.id, "month": f"{due.date:%Y-%m}", "day": due.fire.day, "date": due.date.isoformat(),
               "status": status, "via": via,
               "sent_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        line = ("\n" if self._torn_tail else "") + json.dumps(rec, separators=(",", ":")) + "\n"
        os.write(self.fd, line.encode())
        self._torn_tail = False
        os.fsync(self.fd)
        self.keys.add(due.key)

    def close(self) -> None:
        os.close(self.fd)   # releases the flock


# --- the send ----------------------------------------------------------------------------------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would carry the bearer key to another URL: answer it as an error instead."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# No proxy either: an http_proxy in the environment must never see the key.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _json_or_empty(raw: bytes) -> dict:
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _token(value) -> str:
    return value if isinstance(value, str) and TOKEN_RE.fullmatch(value) else ""


def post_send(base_url: str, key: str, target: str, text: str, timeout: float) -> tuple[int | None, dict, str]:
    """(HTTP status or None, the JSON answer, the exception class name when no status came back)."""
    body = json.dumps({"target": target, "text": text}).encode("utf-8")
    req = urllib.request.Request(base_url.rstrip("/") + SEND_PATH, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, _json_or_empty(resp.read(MAX_RESPONSE_BYTES)), ""
    except urllib.error.HTTPError as exc:
        try:
            data = _json_or_empty(exc.read(MAX_RESPONSE_BYTES))
        except (OSError, http.client.HTTPException):
            data = {}
        finally:
            exc.close()
        return exc.code, data, ""
    except urllib.error.URLError as exc:
        reason = exc.reason
        return None, {}, "URLError" if isinstance(reason, str) else type(reason).__name__
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # Never str(exc): http.client puts a bad header's value (the key) into its ValueError text.
        return None, {}, type(exc).__name__


def classify(status: int | None, error: str) -> int:
    """Exit code for one fire's answer."""
    if status is None:
        return EXIT_TRANSIENT
    if 200 <= status < 300:
        return EXIT_OK
    if status in (401, 408):
        return EXIT_TRANSIENT
    if status == 429:
        # ClaudeFlow answers 429 for two things: rate_limited (per chat per hour, passes) and
        # push_quota_guard (the month's push quota is down to its reserve, does not pass today).
        return EXIT_REFUSED if error == "push_quota_guard" else EXIT_TRANSIENT
    if 400 <= status < 500:
        return EXIT_REFUSED
    if 500 <= status < 600:
        return EXIT_TRANSIENT
    return EXIT_REFUSED   # 1xx/3xx: a wrong SOMPONG_INTERNAL_BASE_URL, which a retry does not fix


# --- run ---------------------------------------------------------------------------------------

def _tail(target: str) -> str:
    return "..." + target[-4:]


def _label(due: Due) -> str:
    return f"{due.row.id} day={due.fire.day} date={due.date.isoformat()} target={_tail(due.row.target)}"


def run(*, rows_path: str = DEFAULT_ROWS, state_dir: str = DEFAULT_STATE_DIR, today: date | None = None,
        dry_run: bool = False, env: dict | None = None, timeout: float = HTTP_TIMEOUT_SEC,
        lock_wait: float = LOCK_WAIT_SEC, now: datetime | None = None) -> int:
    env = os.environ if env is None else env
    key = env.get("SOMPONG_INTERNAL_KEY", "")
    hide = [key] if len(key.strip()) >= 8 else []   # a shorter "key" is a typo; scrubbing it would mangle text

    def say(line: str, *, err: bool = False) -> None:
        for secret in hide:
            line = line.replace(secret, "[REDACTED]")
        print(line, file=sys.stderr if err else sys.stdout, flush=True)

    day = today or bangkok_today(now)
    try:
        rows = load_rows(rows_path)
    except RowsError as exc:
        say(f"household_reminders: rows file refused, nothing sent: {exc}", err=True)
        return EXIT_ROWS
    due = due_fires(rows, day)
    say(f"household_reminders: {day.isoformat()} (Asia/Bangkok): {len(rows)} row(s), {len(due)} fire(s) due"
        + (" [dry run]" if dry_run else ""))
    if not due:
        return EXIT_OK

    if dry_run:
        sent = peek_ledger(state_dir)
        if sent is None:
            say(f"  (cannot read the ledger in {state_dir}: fires already sent are not marked below)")
            sent = set()
        for d in due:
            if d.key in sent:
                say(f"  {_label(d)} already sent (ledger), would skip")
                continue
            say(f"  {_label(d)} would send {len(d.fire.text)} chars:")
            for line in d.fire.text.splitlines() or [""]:
                say(f"    | {line}")
        return EXIT_OK

    try:
        ledger = Ledger(state_dir, lock_wait=lock_wait)
    except LedgerBusy as exc:
        say(f"household_reminders: {exc}; nothing sent", err=True)
        return EXIT_TRANSIENT
    except OSError as exc:
        say(f"household_reminders: cannot open the ledger in {state_dir}: "
            f"{exc.strerror or type(exc).__name__}; nothing sent", err=True)
        return EXIT_TRANSIENT
    try:
        pending = [d for d in due if d.key not in ledger.keys]
        for d in due:
            if d.key in ledger.keys:
                say(f"  {_label(d)} already sent (ledger), skipped")
        if not pending:
            return EXIT_OK
        if not key.strip():
            say(f"household_reminders: no SOMPONG_INTERNAL_KEY in the environment (start it under "
                f"infisical_setup.py run MoonieX-SomPong prod); {len(pending)} fire(s) not sent", err=True)
            return EXIT_TRANSIENT
        base_url = env.get("SOMPONG_INTERNAL_BASE_URL") or DEFAULT_BASE_URL
        worst = EXIT_OK
        for d in pending:
            status, answer, failure = post_send(base_url, key, d.row.target, d.fire.text, timeout)
            error = _token(answer.get("error"))
            code = classify(status, error)
            if code == EXIT_OK:
                via = _token(answer.get("via"))
                say(f"  {_label(d)} status={status} sent via={via or '?'}")
                try:
                    ledger.append(d, status, via)
                except OSError as exc:
                    # Sent but not recorded: a retry would post it again, so stop here and do not retry.
                    say(f"household_reminders: {d.row.id} day={d.fire.day} was sent but the ledger write failed "
                        f"({exc.strerror or type(exc).__name__}); stopping, exit {EXIT_REFUSED} so systemd "
                        f"does not post it twice", err=True)
                    return EXIT_REFUSED
            else:
                what = "refused" if code == EXIT_REFUSED else "transient"
                detail = error or failure or "-"
                say(f"  {_label(d)} status={status if status is not None else 'none'} {what} error={detail}")
            worst = max(worst, code)
        return worst
    finally:
        ledger.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rows", default=DEFAULT_ROWS, help=f"rows file (default {DEFAULT_ROWS})")
    ap.add_argument("--state-dir", default=DEFAULT_STATE_DIR, help=f"ledger directory (default {DEFAULT_STATE_DIR})")
    ap.add_argument("--date", type=date.fromisoformat, metavar="YYYY-MM-DD",
                    help="act as if today (Asia/Bangkok) were this date")
    ap.add_argument("--dry-run", action="store_true", help="print what would be sent; send nothing, need no key")
    args = ap.parse_args(argv)
    return run(rows_path=args.rows, state_dir=args.state_dir, today=args.date, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
