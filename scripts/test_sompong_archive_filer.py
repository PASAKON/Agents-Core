"""Tests for runners/sompong_archive_filer.py (task-3f9b62a0).

Every test isolates the module's own globals (OUTBOX, STAGING_ROOT,
STATE_DIR and the four state-file paths derived from it, MAX_RETRIES,
MIN_FREE_MB) to tmp_path via monkeypatch -- same idiom
scripts/test_sompong_photo_filer.py's `filer_env` fixture uses.
`_upload_via_broker` is monkeypatched with a fake that hashes whatever
bytes actually got staged, so every test's md5 stays internally
consistent without hardcoding a hash. `_now_bangkok` is monkeypatched to
a fixed instant so "is this month closed" never depends on the day the
test suite happens to run.

Covers (task's required "done means" list):
  - closed-month log uploaded + local deleted
  - open month not uploaded
  - changed-in-last-24h not uploaded
  - a late-arriving second file for an already-filed month uploads as
    "-part2"
  - a complete media pair (bin + sidecar) uploads then both delete
  - md5 mismatch on upload keeps the local file
  - broker down keeps the local file
  - symlink / hardlink / FIFO in the outbox are skipped and never read
  - same content already in the local ledger (crash-recovery / "already
    on Drive") counts as done without a second upload
"""
from __future__ import annotations

import calendar
import gzip
import hashlib
import json
import os
import stat
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import runners.sompong_archive_filer as filer  # noqa: E402


FIXED_NOW = datetime(2026, 9, 26, 12, 0, 0, tzinfo=filer.BANGKOK_TZ)
CLOSED_MONTH = "2026-07"   # last day + 32d = 2026-09-01, before FIXED_NOW
OPEN_MONTH = "2026-09"     # last day + 32d = 2026-11-01, after FIXED_NOW


@pytest.fixture
def filer_env(tmp_path, monkeypatch):
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    staging = tmp_path / "staging"
    staging.mkdir()
    state = tmp_path / "state"

    monkeypatch.setattr(filer, "OUTBOX", outbox)
    monkeypatch.setattr(filer, "STAGING_ROOT", staging)
    monkeypatch.setattr(filer, "STATE_DIR", state)
    monkeypatch.setattr(filer, "LOCK_PATH", state / "sompong_archive_filer.lock")
    monkeypatch.setattr(filer, "FAILCOUNT_PATH", state / "failcounts.json")
    monkeypatch.setattr(filer, "LOG_LEDGER_PATH", state / "filed_logs.json")
    monkeypatch.setattr(filer, "MEDIA_LEDGER_PATH", state / "filed_media.json")
    monkeypatch.setattr(filer, "MAX_RETRIES", 3)
    monkeypatch.setattr(filer, "MIN_FREE_MB", 0)
    monkeypatch.setattr(filer, "_now_bangkok", lambda: FIXED_NOW)
    return outbox


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_log(outbox: Path, month: str, content: bytes, *, age_hours: float = 48.0) -> Path:
    path = outbox / f"log-{month}.jsonl"
    path.write_bytes(content)
    mtime = (FIXED_NOW - timedelta(hours=age_hours)).timestamp()
    os.utime(path, (mtime, mtime))
    return path


def _write_media_pair(outbox: Path, month: str, msgid: str, content: bytes, *, ext: str = ".jpg",
                       sha256: str | None = None) -> tuple[Path, Path]:
    month_dir = outbox / "media" / month
    month_dir.mkdir(parents=True, exist_ok=True)
    bin_path = month_dir / f"{msgid}{ext}"
    json_path = month_dir / f"{msgid}.json"
    bin_path.write_bytes(content)
    sidecar = {
        "kind": "image", "mime": "image/jpeg", "size": len(content),
        "sha256": sha256 if sha256 is not None else _sha256(content),
        "senderId": "U1", "senderName": "test", "target": "G1",
        "ts": 1788975600, "fileName": f"{msgid}{ext}", "f2Staged": False,
    }
    json_path.write_text(json.dumps(sidecar), encoding="utf-8")
    return bin_path, json_path


def _matching_md5_upload(calls: list):
    """A fake _upload_via_broker that always reports back the md5 of
    whatever bytes were actually staged, so verify-before-delete succeeds
    for any content without hardcoding a hash."""
    def fake(path, name, subfolder):
        calls.append((Path(path), name, subfolder))
        data = Path(path).read_bytes()
        return True, "ok", hashlib.md5(data).hexdigest()
    return fake


# --------------------------------------------------------------------------- closed-month log

def test_closed_month_log_uploaded_and_local_deleted(filer_env, monkeypatch):
    outbox = filer_env
    content = b'{"ts": 1}\n{"ts": 2}\n'
    path = _write_log(outbox, CLOSED_MONTH, content)

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("log_filed") == 1
    assert not path.exists()
    assert len(calls) == 1
    staged_path, drive_name, subfolder = calls[0]
    assert drive_name == f"log-{CLOSED_MONTH}.jsonl.gz"
    assert subfolder == CLOSED_MONTH
    # the broker is only ever handed a staged, process-named gzip copy
    assert staged_path.parent == filer.STAGING_ROOT
    assert staged_path != path
    assert not staged_path.exists()  # removed after the attempt

    ledger = filer._load_log_ledger()
    assert _sha256(content) in ledger
    assert ledger[_sha256(content)]["name"] == f"log-{CLOSED_MONTH}.jsonl.gz"


def test_open_month_log_not_uploaded(filer_env, monkeypatch):
    outbox = filer_env
    path = _write_log(outbox, OPEN_MONTH, b"still being written\n")

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("skipped_open_month") == 1
    assert "log_filed" not in counts
    assert path.exists()
    assert calls == []


def test_recently_modified_closed_month_log_not_uploaded(filer_env, monkeypatch):
    outbox = filer_env
    path = _write_log(outbox, CLOSED_MONTH, b"just touched\n", age_hours=1.0)

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("skipped_recently_modified") == 1
    assert "log_filed" not in counts
    assert path.exists()
    assert calls == []


def test_late_second_file_for_already_filed_month_uploads_as_part2(filer_env, monkeypatch):
    outbox = filer_env
    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    first = _write_log(outbox, CLOSED_MONTH, b"first batch\n")
    counts1 = filer.tick()
    assert counts1.get("log_filed") == 1
    assert not first.exists()
    assert calls[-1][1] == f"log-{CLOSED_MONTH}.jsonl.gz"

    # ClaudeFlow writes a fresh file for the same month with new late rows
    second = _write_log(outbox, CLOSED_MONTH, b"late rows\n")
    counts2 = filer.tick()
    assert counts2.get("log_filed") == 1
    assert not second.exists()
    assert calls[-1][1] == f"log-{CLOSED_MONTH}-part2.jsonl.gz"


def test_log_md5_mismatch_keeps_local(filer_env, monkeypatch):
    outbox = filer_env
    path = _write_log(outbox, CLOSED_MONTH, b"content\n")

    def bad_md5(p, name, subfolder):
        return True, "ok", "0" * 32
    monkeypatch.setattr(filer, "_upload_via_broker", bad_md5)

    counts = filer.tick()

    assert counts.get("log_md5_mismatch") == 1
    assert path.exists()
    assert _sha256(path.read_bytes()) not in filer._load_log_ledger()


def test_log_broker_down_keeps_local(filer_env, monkeypatch):
    outbox = filer_env
    path = _write_log(outbox, CLOSED_MONTH, b"content\n")

    def down(p, name, subfolder):
        return False, "broker unreachable", None
    monkeypatch.setattr(filer, "_upload_via_broker", down)

    counts = filer.tick()

    assert counts.get("log_upload_failed") == 1
    assert path.exists()


def test_log_duplicate_of_ledger_entry_deleted_without_reupload(filer_env, monkeypatch):
    outbox = filer_env
    content = b"already archived content\n"
    path = _write_log(outbox, CLOSED_MONTH, content)

    filer.STATE_DIR.mkdir(parents=True, exist_ok=True)
    filer._save_log_ledger({_sha256(content): {"name": f"log-{CLOSED_MONTH}.jsonl.gz", "month": CLOSED_MONTH}})

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("log_duplicate") == 1
    assert not path.exists()
    assert calls == []  # never re-uploaded


# --------------------------------------------------------------------------- media pairs

def test_media_pair_uploaded_then_both_deleted(filer_env, monkeypatch):
    outbox = filer_env
    content = b"fake jpeg bytes"
    bin_path, json_path = _write_media_pair(outbox, "2026-08", "msg1", content)

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("media_filed") == 1
    assert not bin_path.exists()
    assert not json_path.exists()
    assert len(calls) == 2  # bin + sidecar, uploaded independently
    names = {c[1] for c in calls}
    assert names == {"msg1.jpg", "msg1.json"}
    for _, _, subfolder in calls:
        assert subfolder == "2026-08"

    ledger = filer._load_media_ledger()
    assert _sha256(content) in ledger
    assert ledger[_sha256(content)]["msgid"] == "msg1"


def test_media_pair_open_month_still_uploads_no_closed_wait(filer_env, monkeypatch):
    # Media has no closed-month gate, unlike text logs -- use the OPEN
    # month to prove that.
    outbox = filer_env
    content = b"fresh media bytes"
    bin_path, json_path = _write_media_pair(outbox, OPEN_MONTH, "msg2", content)

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("media_filed") == 1
    assert not bin_path.exists()
    assert not json_path.exists()


def test_media_bin_md5_mismatch_keeps_both_local(filer_env, monkeypatch):
    outbox = filer_env
    content = b"fake jpeg bytes"
    bin_path, json_path = _write_media_pair(outbox, "2026-08", "msg3", content)

    def bad_bin_md5(path, name, subfolder):
        if name.endswith(".json"):
            data = Path(path).read_bytes()
            return True, "ok", hashlib.md5(data).hexdigest()
        return True, "ok", "0" * 32
    monkeypatch.setattr(filer, "_upload_via_broker", bad_bin_md5)

    counts = filer.tick()

    assert counts.get("media_upload_failed") == 1
    assert bin_path.exists()
    assert json_path.exists()


def test_media_broker_down_keeps_both_local(filer_env, monkeypatch):
    outbox = filer_env
    bin_path, json_path = _write_media_pair(outbox, "2026-08", "msg4", b"bytes")

    def down(path, name, subfolder):
        return False, "broker unreachable", None
    monkeypatch.setattr(filer, "_upload_via_broker", down)

    counts = filer.tick()

    assert counts.get("media_upload_failed") == 1
    assert bin_path.exists()
    assert json_path.exists()


def test_media_duplicate_of_ledger_entry_deleted_without_reupload(filer_env, monkeypatch):
    outbox = filer_env
    content = b"already archived media"
    bin_path, json_path = _write_media_pair(outbox, "2026-08", "msg5", content)

    filer.STATE_DIR.mkdir(parents=True, exist_ok=True)
    filer._save_media_ledger({_sha256(content): {"msgid": "msg5", "month": "2026-08", "bin_name": "msg5.jpg"}})

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("media_duplicate") == 1
    assert not bin_path.exists()
    assert not json_path.exists()
    assert calls == []


def test_incomplete_media_pair_untouched(filer_env, monkeypatch):
    # A .bin with no matching .json (sidecar written last, still pending)
    # is never processed -- confirmed naturally by the pairing scan.
    outbox = filer_env
    month_dir = outbox / "media" / "2026-08"
    month_dir.mkdir(parents=True)
    lone_bin = month_dir / "msg6.jpg"
    lone_bin.write_bytes(b"partial")

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert calls == []
    assert lone_bin.exists()
    assert "media_filed" not in counts


# --------------------------------------------------------------------------- unsafe entries

def test_symlinked_log_skipped_and_never_read(filer_env, monkeypatch, tmp_path):
    outbox = filer_env
    secret = tmp_path / "secret.jsonl"
    secret.write_bytes(b"private chat content\n")
    link = outbox / f"log-{CLOSED_MONTH}.jsonl"
    os.symlink(secret, link)

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("skipped_unsafe") == 1
    assert calls == []
    assert link.is_symlink()  # untouched, never followed or deleted


def test_hardlinked_log_skipped_and_never_read(filer_env, monkeypatch):
    outbox = filer_env
    path = _write_log(outbox, CLOSED_MONTH, b"content\n")
    os.link(path, outbox / "extra_link.txt")  # bumps st_nlink to 2

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("skipped_unsafe") == 1
    assert calls == []
    assert path.exists()


def test_fifo_log_skipped_and_never_read(filer_env, monkeypatch):
    outbox = filer_env
    fifo_path = outbox / f"log-{CLOSED_MONTH}.jsonl"
    os.mkfifo(fifo_path)

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("skipped_unsafe") == 1
    assert calls == []
    assert stat.S_ISFIFO(os.lstat(fifo_path).st_mode)


def test_symlinked_media_bin_skipped_and_never_read(filer_env, monkeypatch, tmp_path):
    outbox = filer_env
    month_dir = outbox / "media" / "2026-08"
    month_dir.mkdir(parents=True)
    secret = tmp_path / "secret.bin"
    secret.write_bytes(b"private media bytes")
    os.symlink(secret, month_dir / "msg7.jpg")
    (month_dir / "msg7.json").write_text(json.dumps({"sha256": _sha256(b"private media bytes")}), encoding="utf-8")

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("skipped_unsafe") == 1
    assert calls == []


def test_hardlinked_media_bin_skipped_and_never_read(filer_env, monkeypatch):
    outbox = filer_env
    content = b"media bytes"
    bin_path, json_path = _write_media_pair(outbox, "2026-08", "msg8", content)
    os.link(bin_path, bin_path.parent / "extra_link.bin")

    calls = []
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload(calls))

    counts = filer.tick()

    assert counts.get("skipped_unsafe") == 1
    assert calls == []
    assert bin_path.exists()
    assert json_path.exists()


# --------------------------------------------------------------------------- ordering / lock

def test_single_flight_lock_skips_concurrent_tick(filer_env, monkeypatch):
    outbox = filer_env
    _write_log(outbox, CLOSED_MONTH, b"content\n")
    monkeypatch.setattr(filer, "_upload_via_broker", _matching_md5_upload([]))

    held_fd = filer._try_lock(filer.LOCK_PATH)
    assert held_fd is not None
    try:
        counts = filer.tick()
        assert counts == {}
    finally:
        filer._unlock(held_fd)


def test_month_closed_boundary_matches_32_day_grace():
    # last day of 2026-07 is 2026-07-31; +32 days = 2026-09-01
    assert filer._is_month_closed("2026-07", datetime(2026, 9, 1, 0, 0, tzinfo=filer.BANGKOK_TZ))
    assert not filer._is_month_closed("2026-07", datetime(2026, 8, 31, 23, 59, tzinfo=filer.BANGKOK_TZ))
