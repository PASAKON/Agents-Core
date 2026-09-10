#!/usr/bin/env python3
"""The host-side drain for SomPong's family-photo backup (task-a1c618db,
design of record: org wiki `mooniex:projects/sompong-line.md` feature F2).

claudeflow runs the family bot inside Docker. Docker never gets the Drive
OAuth broker's unix socket mounted into it -- that would hand a container
compromise the CEO's Drive, which is exactly the containment property
runners/drive_upload_broker.py (and its sibling runners/drive_photo_broker.py)
exist to prevent. Instead the container only WRITES staged photo files onto
the shared volume (claudeflow's compose already mounts `./data:/app/data`,
host `/root/projects/mooniex-claudeflow/data`) and this HOST process --
outside Docker, never touching the credential itself -- drains that outbox
through the photo broker's socket.

Runs as root (task-4307c02c, 2026-09-10): the outbox sits under
/root/projects/mooniex-claudeflow/data/..., and /root is mode 0700 on
Contabo -- no non-root uid can ever traverse into it, no matter what the
leaf outbox directory's own permissions say (measured: `sudo -u
sompongphoto test -r <outbox>` failed even though the leaf itself was
group-writable to that user). Root already owns this whole box -- the
credential files, systemd, and every service user, this one included -- so
a process that can read /root/projects grants a host-root compromise
nothing it did not already have; see docs/design/sompong-photos.md and
runners/drive_photo_broker.py's own docstring ("CONTAINMENT BOUNDARY,
PRECISELY") for the full reasoning and the alternatives that were rejected.
Running as root is exactly why every path this loop is about to open is
resolved and checked against OUTBOX first (`_resolves_inside_outbox()`,
same resolve-then-check discipline drive_photo_broker.py already uses for
its own upload paths) -- a symlink dropped into the outbox pointing
anywhere else on the host must never be followed, since root would happily
read (or quarantine-move) whatever it points at otherwise.

    claudeflow container -> writes <id>.bin + <id>.json pair
                                    |
                          this loop notices it (poll)
                                    |
                    verify sha256, dedup, name, month folder
                                    |
                     upload through drive_photo_broker.py's socket
                                    |
                  only on confirmed success: delete pair + record sha256

Outbox contract (claudeflow's side -- separate task, described here only so
this loop's assumptions are traceable): for one photo/video the container
writes `<id>.bin` (the raw bytes) then, LAST and atomically (write-tmp +
rename, same discipline this module itself uses for its own state), writes
`<id>.json`:
    {"groupId": "...", "messageId": "...", "userId": "...", "name": "...",
     "ts": 1788975600, "kind": "image", "mime": "image/jpeg", "ext": ".jpg",
     "sha256": "..."}
`ts` is a Unix epoch integer (same convention as the wiki's own
`log.jsonl` line shape). Because the JSON is written last, a directory
listing can only ever find a *.json alongside a matching *.bin for a pair
that is genuinely complete -- a JSON with no bin yet (or a bin with no JSON
yet) means a write is still in flight, or something is wrong; either way
this loop leaves it alone rather than half-processing it.

Per complete pair, oldest (`ts`) first:
  1. Recompute sha256 over the bytes and compare to the JSON's `sha256`.
     Mismatch (or a JSON that fails to parse, or is missing required
     fields) -> quarantine (move both files to `failed/`), log, never
     upload. This is a hard quarantine, not a retry -- the bytes named by
     this pair are not what the JSON claims, retrying changes nothing.
  2. Dedup against `filed.json` (sha256 -> {name, date}) kept beside the
     outbox: a sha256 already filed means this exact photo made it to Drive
     before (e.g. a retried webhook delivery) -- delete the local pair
     without uploading again.
  3. Month folder from `ts`, converted to Asia/Bangkok (+07:00, no DST) --
     `YYYY-MM`, matching the gdrive-filing skill's "file by month" rule for
     `My Picture & Videos.`.
  4. Filename: `(<sender name>) (D-M-YYYY) (<HHMM>) <messageId><ext>` --
     gdrive-filing's parenthesised-fields naming style; the messageId
     disambiguates two photos sent in the same minute. The sender name is
     stripped of anything outside `[\\w฀-๿ .()-]` first.
  5. Upload through drive_photo_broker.py's socket (never Drive directly --
     this process holds no Drive credential of any kind). Only once the
     broker confirms `ok: true` does this loop record the sha256 in
     `filed.json` and delete the local pair. A failed upload leaves both
     files exactly where they were -- "never delete a file that has not
     been confirmed uploaded" holds even across a crash mid-tick, since the
     ledger write happens (and is fsynced via atomic rename) before the
     delete, so a crash between the two just repeats step 2 next tick and
     dedupes it away instead of re-uploading or losing data.

Retry discipline mirrors runners/secretary_waker.py (read that file -- this
loop is a sibling of it): a JSON sidecar (`failcounts.json`, under this
loop's own state dir, never inside the outbox) tracks consecutive upload
failures per pair id; a pair that fails MAX_RETRIES times in a row moves to
`failed/` instead of being retried forever against a paid API. Single-flight
via a non-blocking flock, same idiom as secretary_waker's `_try_lock` --
reimplemented here rather than imported, since that module carries HTTP/
mailbox concerns this one has no use for. One bad tick logs and sleeps; the
loop itself never dies.

Run:  python -m runners.sompong_photo_filer          (loop)
      python -m runners.sompong_photo_filer --once   (single tick, for testing)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover -- POSIX only; this org runs Mac + Linux
    fcntl = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.logger import get_logger  # noqa: E402
from runners.drive_photo_broker import DEFAULT_SOCKET_PATH as _BROKER_DEFAULT_SOCKET_PATH  # noqa: E402

# ---------------------------------------------------------------------------
# Config -- plain module-level constants read from the environment, same
# style runners/secretary_waker.py uses; tests monkeypatch these attributes
# directly (see scripts/test_secretary_waker.py's `waker_env` fixture for the
# idiom this file's own tests copy).
# ---------------------------------------------------------------------------
DEFAULT_OUTBOX = "/root/projects/mooniex-claudeflow/data/sompong/photos-outbox"

OUTBOX = Path(os.environ.get("SOMPONG_PHOTO_OUTBOX") or DEFAULT_OUTBOX)
# Same env var name the broker itself reads its bind path from -- this
# process is the broker's one intended client, so the two must always agree
# on where the socket lives without a second name to drift out of sync.
SOCKET_PATH = Path(os.environ.get("DRIVE_PHOTO_BROKER_SOCKET_PATH") or _BROKER_DEFAULT_SOCKET_PATH)

POLL_SECONDS = int(os.environ.get("SOMPONG_PHOTO_FILER_POLL_SECONDS", "60"))
MAX_RETRIES = int(os.environ.get("SOMPONG_PHOTO_FILER_MAX_RETRIES", "5"))
# Generous: a 200 MiB upload (the broker's own per-file cap) plus Drive
# latency, with margin -- same "don't let a client timeout race the far
# side's own ceiling" reasoning secretary_waker.py documents for its own
# timeout default.
BROKER_TIMEOUT_SECONDS = int(os.environ.get("SOMPONG_PHOTO_FILER_BROKER_TIMEOUT_SECONDS", "1830"))

STATE_DIR = Path(os.environ.get("SOMPONG_PHOTO_FILER_STATE_DIR") or ROOT / "state" / "sompong_photo_filer")
LOCK_PATH = STATE_DIR / "filer.lock"
FAILCOUNT_PATH = STATE_DIR / "failcounts.json"

FILED_LEDGER_NAME = "filed.json"
FAILED_DIRNAME = "failed"

BANGKOK_TZ = timezone(timedelta(hours=7))

# Sender-name sanitisation, exactly as specified: word chars (already
# Unicode-aware, so this covers Thai too) plus the Thai block explicitly,
# space, dot, parens, hyphen. Anything else is stripped, not substituted.
_SENDER_NAME_ALLOWED_RE = re.compile(r"[^\w฀-๿ .()-]")

_LOGGER = None


def _log():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger("sompong_photo_filer")
    return _LOGGER


# ---------------------------------------------------------------------------
# Single-flight -- non-blocking flock, released by the kernel on exit (even
# `kill -9`). Same idiom runners/secretary_waker.py's `_try_lock` uses.
# ---------------------------------------------------------------------------

def _try_lock(path: Path):
    if fcntl is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def _unlock(fd) -> None:
    if fd is None:
        return
    try:
        os.close(fd)  # releases the flock too
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Poison-pair cap -- same shape as secretary_waker's failcounts.json, keyed
# by pair id (the shared `<id>` stem of `<id>.bin`/`<id>.json`) instead of a
# mailbox letter's filename.
# ---------------------------------------------------------------------------

def _load_failcounts(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_failcounts(path: Path, counts: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counts), encoding="utf-8")


# ---------------------------------------------------------------------------
# Dedup ledger -- sha256 -> {"name": <drive filename>, "date": <YYYY-MM>}.
# Lives beside the outbox (not under STATE_DIR) so it travels with the data
# it describes rather than with this process's own bookkeeping.
# ---------------------------------------------------------------------------

def _ledger_path() -> Path:
    return OUTBOX / FILED_LEDGER_NAME


def _load_filed_ledger() -> dict:
    try:
        return json.loads(_ledger_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_filed_ledger(ledger: dict) -> None:
    path = _ledger_path()
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(ledger), encoding="utf-8")
    tmp.replace(path)  # atomic on POSIX


# ---------------------------------------------------------------------------
# Pair discovery -- scan for *.json (never recurses into failed/, and
# FILED_LEDGER_NAME lives in the same directory so it must be excluded by
# name). A JSON is only ever picked up alongside a *.bin sharing its stem;
# a *.bin with no matching *.json is never enumerated here at all -- it is
# naturally skipped, not specially handled.
# ---------------------------------------------------------------------------

def _bin_path_for(json_path: Path) -> Path:
    return json_path.with_name(json_path.stem + ".bin")


# Prefix on the `parse_error` slot _load_pair() returns for a path that fails
# this check, so _process_one() can log/count it distinctly from an actually
# corrupt JSON body without changing the tuple shape either function passes
# around.
_SYMLINK_ESCAPE_PREFIX = "symlink escape: "


def _resolves_inside_outbox(path: Path) -> bool:
    """True iff `path` exists and its FULLY RESOLVED (symlinks followed)
    location is inside OUTBOX. This loop runs as root (task-4307c02c), so it
    can open anything on the host if it blindly follows wherever a symlink
    dropped into the outbox happens to point -- every path this loop is
    about to open is checked here first, the same resolve-then-check
    discipline runners/drive_photo_broker.py already uses for its own
    upload paths."""
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    try:
        resolved.relative_to(OUTBOX.resolve())
    except ValueError:
        return False
    return True


def _load_pair(json_path: Path) -> tuple[str, Path, Path, dict | None, str | None]:
    """(id, json_path, bin_path, data_or_None, parse_error_or_None)."""
    stem = json_path.stem
    bin_path = _bin_path_for(json_path)
    if not _resolves_inside_outbox(json_path):
        return stem, json_path, bin_path, None, f"{_SYMLINK_ESCAPE_PREFIX}.json resolves outside the outbox"
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 -- any parse failure is "corrupt", not a crash
        return stem, json_path, bin_path, None, str(e)
    if not isinstance(data, dict):
        return stem, json_path, bin_path, None, "JSON root is not an object"
    return stem, json_path, bin_path, data, None


def _sort_key(item: tuple[str, Path, Path, dict | None, str | None]) -> float:
    _stem, json_path, _bin_path, data, _err = item
    ts = data.get("ts") if data else None
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        return json_path.stat().st_mtime
    except OSError:
        return 0.0


def _pending_pairs() -> list[tuple[str, Path, Path, dict | None, str | None]]:
    if not OUTBOX.is_dir():
        return []
    items = [
        _load_pair(p) for p in OUTBOX.glob("*.json")
        if p.name != FILED_LEDGER_NAME
    ]
    items.sort(key=_sort_key)
    return items


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

def _sanitize_sender_name(name: object) -> str:
    cleaned = _SENDER_NAME_ALLOWED_RE.sub("", str(name or "")).strip()
    return cleaned or "unknown"


def _local_dt(ts: object) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone(BANGKOK_TZ)


def _month_folder(data: dict) -> str:
    dt = _local_dt(data["ts"])
    return f"{dt.year:04d}-{dt.month:02d}"


def _drive_file_name(data: dict) -> str:
    dt = _local_dt(data["ts"])
    sender = _sanitize_sender_name(data.get("name"))
    date_part = f"{dt.day}-{dt.month}-{dt.year}"
    time_part = f"{dt.hour:02d}{dt.minute:02d}"
    message_id = str(data.get("messageId") or "")
    ext = str(data.get("ext") or "")
    if ext and not ext.startswith("."):
        ext = "." + ext
    return f"({sender}) ({date_part}) ({time_part}) {message_id}{ext}"


# ---------------------------------------------------------------------------
# Quarantine / cleanup
# ---------------------------------------------------------------------------

def _quarantine(json_path: Path, bin_path: Path) -> None:
    failed_dir = OUTBOX / FAILED_DIRNAME
    failed_dir.mkdir(parents=True, exist_ok=True)
    for p in (json_path, bin_path):
        try:
            # is_symlink() first: p.exists() follows symlinks and reports
            # False for a dangling one, which would otherwise leave a
            # malicious/broken symlink sitting in the outbox forever,
            # re-glob'd and re-quarantine-attempted (but never actually
            # moved) every tick. rename() itself never follows the link --
            # it moves the symlink, not whatever it points at.
            if p.is_symlink() or p.exists():
                p.rename(failed_dir / p.name)
        except OSError as e:
            _log().error("could not quarantine %s: %s", p, e)


def _delete_pair(json_path: Path, bin_path: Path) -> None:
    for p in (json_path, bin_path):
        try:
            p.unlink(missing_ok=True)
        except OSError as e:
            _log().error("could not delete %s: %s", p, e)


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Broker call -- the ONLY place this module touches a socket. Never Drive
# directly, never the credential. Tests monkeypatch this one function (same
# "mock the network-touching call, exercise everything around it for real"
# idiom scripts/test_secretary_waker.py uses for `_invoke_secretary`).
# ---------------------------------------------------------------------------

def _upload_via_broker(bin_path: Path, name: str, subfolder: str) -> tuple[bool, str]:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(BROKER_TIMEOUT_SECONDS)
        sock.connect(str(SOCKET_PATH))
    except OSError as e:
        return False, f"could not connect to photo broker: {e}"

    try:
        request = json.dumps({
            "op": "upload", "path": str(bin_path), "name": name, "subfolder": subfolder,
        }) + "\n"
        try:
            sock.sendall(request.encode("utf-8"))
            raw = b""
            while not raw.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                raw += chunk
        except (OSError, TimeoutError, socket.timeout) as e:
            return False, f"broker communication failed: {e}"
    finally:
        sock.close()

    if not raw:
        return False, "broker returned no response"
    try:
        resp = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, "broker returned invalid JSON"

    if not isinstance(resp, dict) or not resp.get("ok"):
        error = resp.get("error") if isinstance(resp, dict) else None
        return False, str(error or "broker refused the upload")
    return True, "ok"


# ---------------------------------------------------------------------------
# One pair
# ---------------------------------------------------------------------------

def _process_one(item: tuple[str, Path, Path, dict | None, str | None],
                  ledger: dict, failcounts: dict) -> str:
    stem, json_path, bin_path, data, parse_error = item

    if parse_error is not None:
        _quarantine(json_path, bin_path)
        failcounts.pop(stem, None)
        if parse_error.startswith(_SYMLINK_ESCAPE_PREFIX):
            _log().error("photo pair %s: %s -- quarantined", stem, parse_error)
            return "quarantined_symlink_escape"
        _log().error("photo pair %s: corrupt JSON (%s) -- quarantined", stem, parse_error)
        return "quarantined_corrupt"

    if not bin_path.exists():
        _log().debug("photo pair %s: .json present but .bin missing -- skipping this tick", stem)
        return "skipped_incomplete"

    if not _resolves_inside_outbox(bin_path):
        _quarantine(json_path, bin_path)
        failcounts.pop(stem, None)
        _log().error("photo pair %s: .bin resolves outside the outbox (symlink?) -- quarantined", stem)
        return "quarantined_symlink_escape"

    sha_expected = data.get("sha256")
    try:
        sha_actual = _sha256_of(bin_path)
    except OSError as e:
        _log().error("photo pair %s: could not read %s (%s)", stem, bin_path, e)
        return "skipped_read_error"

    if not isinstance(sha_expected, str) or not sha_expected or sha_actual != sha_expected:
        _quarantine(json_path, bin_path)
        failcounts.pop(stem, None)
        _log().error("photo pair %s: sha256 mismatch (expected=%s actual=%s) -- quarantined",
                      stem, sha_expected, sha_actual)
        return "quarantined_sha_mismatch"

    if sha_actual in ledger:
        _delete_pair(json_path, bin_path)
        failcounts.pop(stem, None)
        _log().info("photo pair %s: duplicate of already-filed sha256 %s -- deleted", stem, sha_actual)
        return "duplicate"

    try:
        name = _drive_file_name(data)
        month = _month_folder(data)
    except Exception as e:  # noqa: BLE001 -- missing/malformed required fields is "corrupt"
        _quarantine(json_path, bin_path)
        failcounts.pop(stem, None)
        _log().error("photo pair %s: could not build a destination name (%s) -- quarantined", stem, e)
        return "quarantined_corrupt"

    ok, detail = _upload_via_broker(bin_path, name, month)
    if not ok:
        n = failcounts.get(stem, 0) + 1
        if n >= MAX_RETRIES:
            _quarantine(json_path, bin_path)
            failcounts.pop(stem, None)
            _log().error("photo pair %s: upload failed %s time(s) -- quarantined (%s)", stem, n, detail)
            return "quarantined_retry_cap"
        failcounts[stem] = n
        _log().warning("photo pair %s: upload failed (%s/%s): %s", stem, n, MAX_RETRIES, detail)
        return "upload_failed"

    # Record before delete: if the process dies between these two lines, the
    # next tick's dedup check (above) deletes the still-present local pair
    # as a "duplicate" instead of re-uploading it or leaving it stranded.
    ledger[sha_actual] = {"name": name, "date": month}
    _save_filed_ledger(ledger)
    failcounts.pop(stem, None)
    _delete_pair(json_path, bin_path)
    _log().info("photo pair %s: filed as '%s' (%s)", stem, name, month)
    return "filed"


# ---------------------------------------------------------------------------
# One tick
# ---------------------------------------------------------------------------

def tick() -> dict[str, int]:
    fd = _try_lock(LOCK_PATH)
    if fd is None:
        _log().info("previous tick still in flight -- skipping")
        return {}
    try:
        return _tick_locked()
    finally:
        _unlock(fd)


def _tick_locked() -> dict[str, int]:
    items = _pending_pairs()
    if not items:
        return {}

    ledger = _load_filed_ledger()
    failcounts = _load_failcounts(FAILCOUNT_PATH)
    counts: dict[str, int] = {}

    for item in items:
        try:
            action = _process_one(item, ledger, failcounts)
        except Exception as e:  # noqa: BLE001 -- one bad pair must never stop the rest of the tick
            _log().error("photo pair %s: unexpected error (%s)", item[0], e)
            action = "error"
        counts[action] = counts.get(action, 0) + 1

    _save_failcounts(FAILCOUNT_PATH, failcounts)
    return counts


def main() -> None:
    once = "--once" in sys.argv
    _log().info("sompong_photo_filer starting (outbox=%s poll=%ss max_retries=%s once=%s)",
                OUTBOX, POLL_SECONDS, MAX_RETRIES, once)
    while True:
        try:
            tick()
        except Exception as e:  # noqa: BLE001 -- one bad tick must never kill the loop
            _log().error("tick failed: %s", e)
        if once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
