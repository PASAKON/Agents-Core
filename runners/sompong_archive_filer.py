#!/usr/bin/env python3
"""Host-side filer that archives SomPong's LINE data to Google Drive.

ClaudeFlow (the containerized bot) writes into an outbox it does not control
past that point:

    archive-outbox/
        log-<YYYY-MM>.jsonl              one append-only text log per month
        media/<YYYY-MM>/<msgid>.<ext>    a media file
        media/<YYYY-MM>/<msgid>.json     its sidecar (written last)

This process (root, on the host, never inside the container) is the only
thing that reads that tree. It uploads a text log only once its month is
closed (>= 32 days after the month's last day) and has not changed in the
last 24h -- ClaudeFlow may still be appending late rows to the CURRENT
month right up to the moment it rolls over. Media pairs upload as soon as
both files exist; there is no closed-month wait for them.

Uploads go through `runners/drive_photo_broker.py`, run here as a SECOND,
independently configured instance (own system user, socket, staging dir,
and DRIVE_PHOTO_BROKER_FOLDER_ID pointed at the SomPong-LINE backup folder).
This filer never holds the Drive OAuth token -- it only ever writes bytes
into a staging directory the broker's user can read and asks the broker to
upload them. The broker exposes exactly one operation ("upload") and no
list/read call (see scripts/test_drive_photo_broker.py's guard tests), so
this filer cannot ask Drive "does this already exist?" -- the local ledger
below is the sole record of what has already been archived, and it is the
only thing that can decide "-partN" numbering or crash-recovery dedup.  If
the ledger is ever lost, the worst case is a harmless duplicate upload
(same name/content, new file id), never a lost upload or a wrongly deleted
local file, because deletion is gated on the ledger being written for that
exact upload first.

Every name this filer reads out of the outbox comes from a directory
listing (os.listdir on an already-open directory fd), never from JSON
content or a client-supplied string, so it is always a single path
component with no "/" or "..". Every open of such a name still uses
os.open(name, O_NOFOLLOW | O_NONBLOCK, dir_fd=parent_fd) followed by
os.fstat(fd) to reject anything that is not a regular file with exactly
one hard link -- a symlink, a hardlink, a FIFO, or anything else gets
skipped and logged, never opened by path a second time (no
resolve-then-reopen TOCTOU window). This mirrors the dir_fd pattern in
runners/drive_share_broker.py (main branch) rather than the older
resolve()-then-relative_to() guard in sompong_photo_filer.py, because a
month's log file can still be mid-append by another process while this
filer is looking at the directory.

Logs never carry chat content -- only file/month/msgid names and reasons.
"""

from __future__ import annotations

import calendar
import gzip
import hashlib
import json
import os
import re
import socket
import stat
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.logger import get_logger  # noqa: E402

BANGKOK_TZ = timezone(timedelta(hours=7))

DEFAULT_OUTBOX = "/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/data/sompong/archive-outbox"
DEFAULT_STAGING_ROOT = "/var/lib/archiveup/staging"
DEFAULT_STATE_DIR = "/var/lib/archiveup/state"
DEFAULT_SOCKET_PATH = "/run/archiveup/archive-broker.sock"

OUTBOX = Path(os.environ.get("SOMPONG_ARCHIVE_OUTBOX", DEFAULT_OUTBOX))
STAGING_ROOT = Path(os.environ.get("SOMPONG_ARCHIVE_STAGING_ROOT", DEFAULT_STAGING_ROOT))
STATE_DIR = Path(os.environ.get("SOMPONG_ARCHIVE_FILER_STATE_DIR", DEFAULT_STATE_DIR))
SOCKET_PATH = os.environ.get("SOMPONG_ARCHIVE_BROKER_SOCKET_PATH", DEFAULT_SOCKET_PATH)

POLL_SECONDS = int(os.environ.get("SOMPONG_ARCHIVE_FILER_POLL_SECONDS", "300"))
MAX_RETRIES = int(os.environ.get("SOMPONG_ARCHIVE_FILER_MAX_RETRIES", "5"))
MIN_FREE_MB = int(os.environ.get("SOMPONG_ARCHIVE_MIN_FREE_MB", "2048"))
BROKER_TIMEOUT_SECONDS = int(os.environ.get("SOMPONG_ARCHIVE_BROKER_TIMEOUT_SECONDS", "1830"))
LOG_CLOSE_GRACE_DAYS = int(os.environ.get("SOMPONG_ARCHIVE_LOG_CLOSE_GRACE_DAYS", "32"))
LOG_STABLE_HOURS = int(os.environ.get("SOMPONG_ARCHIVE_LOG_STABLE_HOURS", "24"))
LOG_MAX_UPLOAD_BYTES = int(os.environ.get("SOMPONG_ARCHIVE_LOG_MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))
MEDIA_MAX_UPLOAD_BYTES = int(os.environ.get("SOMPONG_ARCHIVE_MEDIA_MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))

LOCK_PATH = STATE_DIR / "sompong_archive_filer.lock"
FAILCOUNT_PATH = STATE_DIR / "failcounts.json"
LOG_LEDGER_PATH = STATE_DIR / "filed_logs.json"
MEDIA_LEDGER_PATH = STATE_DIR / "filed_media.json"
FAILED_DIRNAME = "failed"

_LOG_NAME_RE = re.compile(r"^log-(\d{4})-(0[1-9]|1[0-2])\.jsonl$")
_MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")
_SAFE_EXT_RE = re.compile(r"^\.[A-Za-z0-9]{1,10}$")

log = get_logger("sompong_archive_filer")


# --- single-flight lock ------------------------------------------------

def _try_lock(path: Path) -> int | None:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o640)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def _unlock(fd: int) -> None:
    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# --- small JSON state files (atomic write) -----------------------------

def _load_json(path: Path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError):
        log.warning("state file unreadable, resetting: %s", path.name)
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.chmod(tmp, 0o640)
    os.replace(tmp, path)


def _load_failcounts() -> dict:
    return _load_json(FAILCOUNT_PATH, {})


def _save_failcounts(data: dict) -> None:
    _save_json(FAILCOUNT_PATH, data)


def _load_log_ledger() -> dict:
    return _load_json(LOG_LEDGER_PATH, {})


def _save_log_ledger(data: dict) -> None:
    _save_json(LOG_LEDGER_PATH, data)


def _load_media_ledger() -> dict:
    return _load_json(MEDIA_LEDGER_PATH, {})


def _save_media_ledger(data: dict) -> None:
    _save_json(MEDIA_LEDGER_PATH, data)


# --- safe directory-entry access (dir_fd + O_NOFOLLOW) ------------------

class _UnsafeEntry(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _open_safe_file(dir_fd: int, name: str, max_bytes: int | None = None) -> tuple[int, os.stat_result]:
    """Open `name` (a directory-entry string, never attacker path text) as a
    regular, single-hardlink file relative to dir_fd. Raises _UnsafeEntry
    (never partially opens) for anything else -- symlink, hardlink, FIFO,
    directory, device, or oversized file."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    except OSError as e:
        raise _UnsafeEntry(f"could not open: {e.strerror or e}")
    try:
        st = os.fstat(fd)
    except OSError as e:
        os.close(fd)
        raise _UnsafeEntry(f"could not stat: {e.strerror or e}")
    if not stat.S_ISREG(st.st_mode):
        os.close(fd)
        raise _UnsafeEntry("not a regular file")
    if st.st_nlink != 1:
        os.close(fd)
        raise _UnsafeEntry("has more than one hard link")
    if max_bytes is not None and st.st_size > max_bytes:
        os.close(fd)
        raise _UnsafeEntry(f"too large ({st.st_size} bytes)")
    return fd, st


def _open_safe_subdir(dir_fd: int, name: str) -> int:
    try:
        return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
    except OSError as e:
        raise _UnsafeEntry(f"could not open subdir: {e.strerror or e}")


def _read_fd_bytes(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 1 << 20)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- staging (filer -> broker handoff) ----------------------------------

def _enough_free_space(root: Path, min_mb: int) -> bool:
    try:
        usage = os.statvfs(str(root))
    except OSError:
        return False
    free_mb = (usage.f_bavail * usage.f_frsize) / (1024 * 1024)
    return free_mb >= min_mb


def _stage_bytes(data: bytes, staged_name: str) -> Path:
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    dest = STAGING_ROOT / staged_name
    tmp = STAGING_ROOT / f".tmp.{os.getpid()}.{staged_name}"
    with open(tmp, "wb") as f:
        f.write(data)
    os.chmod(tmp, 0o640)
    os.replace(tmp, dest)
    return dest


def _remove_staged(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        log.warning("could not remove staged file %s: %s", path.name, e)


def _upload_via_broker(local_path: Path, name: str, subfolder: str) -> tuple[bool, str, str | None]:
    """Returns (ok, detail, md5Checksum). md5Checksum is None on failure."""
    req = json.dumps({"op": "upload", "path": str(local_path), "name": name, "subfolder": subfolder}) + "\n"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(BROKER_TIMEOUT_SECONDS)
            sock.connect(SOCKET_PATH)
            sock.sendall(req.encode())
            sock.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks).decode().strip()
    except (OSError, socket.timeout) as e:
        return False, f"broker unreachable: {e}", None
    if not raw:
        return False, "broker returned no response", None
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError:
        return False, "broker returned invalid response", None
    if resp.get("ok"):
        return True, "uploaded", resp.get("md5Checksum")
    return False, str(resp.get("error", "upload failed")), None


# --- Bangkok time helpers ------------------------------------------------

def _now_bangkok() -> datetime:
    return datetime.now(BANGKOK_TZ)


def _is_month_closed(month: str, now: datetime) -> bool:
    year, mon = int(month[:4]), int(month[5:7])
    last_day = calendar.monthrange(year, mon)[1]
    closed_from = date(year, mon, last_day) + timedelta(days=LOG_CLOSE_GRACE_DAYS)
    return now.date() >= closed_from


def _is_stable(st: os.stat_result, now: datetime, hours: int) -> bool:
    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
    return (now.astimezone(timezone.utc) - mtime) >= timedelta(hours=hours)


# --- failcount / retry discipline ---------------------------------------

def _bump_fail(failcounts: dict, key: str) -> int:
    n = failcounts.get(key, 0) + 1
    failcounts[key] = n
    return n


def _clear_fail(failcounts: dict, key: str) -> None:
    failcounts.pop(key, None)


def _quarantine_file(outbox_fd: int, name: str, subdir: str = "") -> None:
    """Move a repeatedly-failing entry into OUTBOX/failed/<subdir>/name so a
    human can inspect it; stops it from being retried forever."""
    failed_root = OUTBOX / FAILED_DIRNAME / subdir if subdir else OUTBOX / FAILED_DIRNAME
    failed_root.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(name, str(failed_root / name), src_dir_fd=outbox_fd)
    except OSError as e:
        log.error("could not quarantine %s: %s", name, e)


# --- text log processing --------------------------------------------------

def _pending_logs(outbox_fd: int) -> list[str]:
    names = []
    for entry in os.listdir(outbox_fd):
        if _LOG_NAME_RE.fullmatch(entry):
            names.append(entry)
    return sorted(names)


def _process_log(name: str, outbox_fd: int, log_ledger: dict, parts: dict, failcounts: dict) -> str:
    month = _LOG_NAME_RE.fullmatch(name).group(0)[4:-6]
    key = f"log:{name}"

    try:
        fd, st = _open_safe_file(outbox_fd, name, max_bytes=LOG_MAX_UPLOAD_BYTES)
    except _UnsafeEntry as e:
        log.warning("skipping unsafe log entry name=%s reason=%s", name, e.reason)
        return "skipped_unsafe"

    try:
        now = _now_bangkok()
        if not _is_month_closed(month, now):
            os.close(fd)
            return "skipped_open_month"
        if not _is_stable(st, now, LOG_STABLE_HOURS):
            os.close(fd)
            return "skipped_recently_modified"

        raw = _read_fd_bytes(fd)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass

    raw_sha256 = _sha256_bytes(raw)

    if raw_sha256 in log_ledger:
        try:
            os.unlink(name, dir_fd=outbox_fd)
        except OSError as e:
            log.warning("duplicate log %s already filed but could not delete: %s", name, e)
            return "duplicate_delete_failed"
        _clear_fail(failcounts, key)
        log.info("log month=%s already filed, removed local duplicate", month)
        return "log_duplicate"

    if not _enough_free_space(STAGING_ROOT, MIN_FREE_MB):
        log.warning("low free space, deferring log month=%s", month)
        return "skipped_low_space"

    gz_bytes = gzip.compress(raw)
    gz_md5 = hashlib.md5(gz_bytes).hexdigest()
    staged_name = f"log-{raw_sha256}.jsonl.gz"
    staged_path = _stage_bytes(gz_bytes, staged_name)

    part_count = parts.get(month, 0)
    drive_name = f"log-{month}.jsonl.gz" if part_count == 0 else f"log-{month}-part{part_count + 1}.jsonl.gz"

    try:
        ok, detail, md5 = _upload_via_broker(staged_path, drive_name, month)
    finally:
        _remove_staged(staged_path)

    if ok and md5 == gz_md5:
        log_ledger[raw_sha256] = {"name": drive_name, "month": month}
        parts[month] = part_count + 1
        _save_log_ledger(log_ledger)
        _save_json(STATE_DIR / "log_parts.json", parts)
        try:
            os.unlink(name, dir_fd=outbox_fd)
        except OSError as e:
            log.error("uploaded log month=%s but could not delete local: %s", month, e)
            return "log_upload_delete_failed"
        _clear_fail(failcounts, key)
        log.info("log month=%s filed as %s", month, drive_name)
        return "log_filed"

    n = _bump_fail(failcounts, key)
    if ok and md5 != gz_md5:
        log.error("log month=%s md5 mismatch, keeping local (attempt %d)", month, n)
        result = "log_md5_mismatch"
    else:
        log.warning("log month=%s upload failed: %s (attempt %d)", month, detail, n)
        result = "log_upload_failed"
    if n >= MAX_RETRIES:
        _quarantine_file(outbox_fd, name)
        _clear_fail(failcounts, key)
        log.error("log month=%s exceeded retry cap, quarantined", month)
        return result + "_quarantined"
    return result


# --- media pair processing ------------------------------------------------

def _pending_media_months(media_fd: int) -> list[str]:
    names = []
    for entry in os.listdir(media_fd):
        if _MONTH_DIR_RE.fullmatch(entry):
            names.append(entry)
    return sorted(names)


def _pending_media_pairs(month_fd: int) -> list[tuple[str, str, str]]:
    """Returns (msgid, bin_name, json_name) for every complete pair in this
    month directory, found purely from directory-entry names (never JSON
    content), sorted so oldest-looking msgid processes first."""
    entries = os.listdir(month_fd)
    json_stems = {e[:-5] for e in entries if e.endswith(".json")}
    bins: dict[str, str] = {}
    for e in entries:
        if e.endswith(".json"):
            continue
        stem, dot, ext = e.rpartition(".")
        if not dot or not _SAFE_EXT_RE.fullmatch("." + ext):
            continue
        bins[stem] = e
    pairs = []
    for stem, bin_name in bins.items():
        if stem in json_stems:
            pairs.append((stem, bin_name, stem + ".json"))
    return sorted(pairs, key=lambda p: p[0])


def _process_media_pair(
    msgid: str, bin_name: str, json_name: str, month: str, month_fd: int, media_ledger: dict, failcounts: dict
) -> str:
    key = f"media:{month}:{msgid}"

    try:
        json_fd, _ = _open_safe_file(month_fd, json_name, max_bytes=1 << 20)
    except _UnsafeEntry as e:
        log.warning("skipping unsafe sidecar msgid=%s reason=%s", msgid, e.reason)
        return "skipped_unsafe"
    try:
        sidecar_raw = _read_fd_bytes(json_fd)
    finally:
        os.close(json_fd)

    try:
        sidecar = json.loads(sidecar_raw)
    except json.JSONDecodeError:
        log.warning("sidecar msgid=%s is not valid JSON", msgid)
        return "skipped_bad_sidecar"

    try:
        bin_fd, bin_st = _open_safe_file(month_fd, bin_name, max_bytes=MEDIA_MAX_UPLOAD_BYTES)
    except _UnsafeEntry as e:
        log.warning("skipping unsafe media entry msgid=%s reason=%s", msgid, e.reason)
        return "skipped_unsafe"
    try:
        bin_bytes = _read_fd_bytes(bin_fd)
    finally:
        os.close(bin_fd)

    bin_sha256 = _sha256_bytes(bin_bytes)
    expected_sha256 = sidecar.get("sha256")
    if expected_sha256 and expected_sha256 != bin_sha256:
        log.error("media msgid=%s sha256 mismatch with sidecar", msgid)
        return "skipped_sha_mismatch"

    if bin_sha256 in media_ledger:
        try:
            os.unlink(bin_name, dir_fd=month_fd)
            os.unlink(json_name, dir_fd=month_fd)
        except OSError as e:
            log.warning("duplicate media msgid=%s already filed but could not delete: %s", msgid, e)
            return "duplicate_delete_failed"
        _clear_fail(failcounts, key)
        log.info("media msgid=%s already filed, removed local duplicate", msgid)
        return "media_duplicate"

    if not _enough_free_space(STAGING_ROOT, MIN_FREE_MB):
        log.warning("low free space, deferring media msgid=%s", msgid)
        return "skipped_low_space"

    ext = bin_name[len(msgid):]
    staged_bin = _stage_bytes(bin_bytes, f"{bin_sha256}{ext}")
    staged_json = _stage_bytes(sidecar_raw, f"{bin_sha256}.json")

    bin_md5 = hashlib.md5(bin_bytes).hexdigest()
    json_md5 = hashlib.md5(sidecar_raw).hexdigest()

    try:
        bin_ok, bin_detail, bin_drive_md5 = _upload_via_broker(staged_bin, bin_name, month)
        json_ok, json_detail, json_drive_md5 = _upload_via_broker(staged_json, json_name, month)
    finally:
        _remove_staged(staged_bin)
        _remove_staged(staged_json)

    bin_verified = bin_ok and bin_drive_md5 == bin_md5
    json_verified = json_ok and json_drive_md5 == json_md5

    if bin_verified and json_verified:
        media_ledger[bin_sha256] = {"msgid": msgid, "month": month, "bin_name": bin_name}
        _save_media_ledger(media_ledger)
        try:
            os.unlink(bin_name, dir_fd=month_fd)
            os.unlink(json_name, dir_fd=month_fd)
        except OSError as e:
            log.error("uploaded media msgid=%s but could not delete local: %s", msgid, e)
            return "media_upload_delete_failed"
        _clear_fail(failcounts, key)
        log.info("media msgid=%s filed", msgid)
        return "media_filed"

    n = _bump_fail(failcounts, key)
    if bin_ok and not bin_verified:
        reason = "bin md5 mismatch"
    elif json_ok and not json_verified:
        reason = "sidecar md5 mismatch"
    else:
        reason = bin_detail if not bin_ok else json_detail
    log.warning("media msgid=%s upload incomplete: %s (attempt %d)", msgid, reason, n)
    result = "media_upload_failed"
    if n >= MAX_RETRIES:
        failed_root = OUTBOX / FAILED_DIRNAME / "media" / month
        failed_root.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(bin_name, str(failed_root / bin_name), src_dir_fd=month_fd)
            os.rename(json_name, str(failed_root / json_name), src_dir_fd=month_fd)
        except OSError as e:
            log.error("could not quarantine media msgid=%s: %s", msgid, e)
        _clear_fail(failcounts, key)
        log.error("media msgid=%s exceeded retry cap, quarantined", msgid)
        return result + "_quarantined"
    return result


# --- tick / main -----------------------------------------------------------

def _tick_locked() -> dict:
    counts: dict[str, int] = {}

    def bump(action: str) -> None:
        counts[action] = counts.get(action, 0) + 1

    if not OUTBOX.is_dir():
        log.warning("outbox does not exist: %s", OUTBOX)
        return counts

    failcounts = _load_failcounts()
    log_ledger = _load_log_ledger()
    media_ledger = _load_media_ledger()
    parts = _load_json(STATE_DIR / "log_parts.json", {})

    outbox_fd = os.open(str(OUTBOX), os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in _pending_logs(outbox_fd):
            action = _process_log(name, outbox_fd, log_ledger, parts, failcounts)
            bump(action)

        try:
            media_fd = _open_safe_subdir(outbox_fd, "media")
        except _UnsafeEntry as e:
            log.warning("media dir unusable: %s", e.reason)
            media_fd = None

        if media_fd is not None:
            try:
                for month in _pending_media_months(media_fd):
                    try:
                        month_fd = _open_safe_subdir(media_fd, month)
                    except _UnsafeEntry as e:
                        log.warning("media month=%s unusable: %s", month, e.reason)
                        continue
                    try:
                        for msgid, bin_name, json_name in _pending_media_pairs(month_fd):
                            action = _process_media_pair(msgid, bin_name, json_name, month, month_fd, media_ledger, failcounts)
                            bump(action)
                    finally:
                        os.close(month_fd)
            finally:
                os.close(media_fd)
    finally:
        os.close(outbox_fd)

    _save_failcounts(failcounts)
    return counts


def tick() -> dict:
    fd = _try_lock(LOCK_PATH)
    if fd is None:
        log.info("another instance holds the lock, skipping this tick")
        return {}
    try:
        return _tick_locked()
    finally:
        _unlock(fd)


def main() -> int:
    once = "--once" in sys.argv
    log.info("sompong_archive_filer starting outbox=%s once=%s", OUTBOX, once)
    while True:
        counts = tick()
        if counts:
            log.info("tick counts=%s", json.dumps(counts, sort_keys=True))
        if once:
            return 0
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
