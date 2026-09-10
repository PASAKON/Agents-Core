"""Tests for runners/sompong_photo_filer.py (task-a1c618db).

Every test isolates the module's own globals (OUTBOX, SOCKET_PATH, state
paths, MAX_RETRIES) to tmp_path via monkeypatch -- same pattern
scripts/test_secretary_waker.py's `waker_env` fixture uses for that loop's
own globals. `_upload_via_broker` is monkeypatched for most tests (the "mock
the network-touching call" idiom secretary_waker's own tests use for
`_invoke_secretary`); one test drives it for real over a real temp AF_UNIX
socket against a stub server, to prove the wire request is shaped correctly
-- that stub server is ours, never Drive, and never the real broker.

Covers (task's required list):
  - a complete pair uploads then deletes locally
  - a JSON with no matching .bin is skipped, not half-processed
  - a .bin with no matching .json is never touched (naturally, by scan design)
  - sha256 mismatch quarantines both files
  - a duplicate sha256 (already in filed.json) is skipped/deleted, not re-uploaded
  - month folder is derived in Asia/Bangkok (a UTC-evening timestamp that
    rolls to the next day in Bangkok)
  - a failing upload never deletes the local pair
  - MAX_RETRIES consecutive failures quarantines the pair
"""
from __future__ import annotations

import hashlib
import json
import socket
import sys
import tempfile
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import runners.sompong_photo_filer as filer  # noqa: E402


@pytest.fixture
def filer_env(tmp_path, monkeypatch):
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    monkeypatch.setattr(filer, "OUTBOX", outbox)
    monkeypatch.setattr(filer, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(filer, "LOCK_PATH", tmp_path / "state" / "filer.lock")
    monkeypatch.setattr(filer, "FAILCOUNT_PATH", tmp_path / "state" / "failcounts.json")
    monkeypatch.setattr(filer, "MAX_RETRIES", 3)
    return outbox


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_pair(outbox: Path, pair_id: str, content: bytes, *, sha256: str | None = None,
                 ts: int = 1788975600, name: str = "พ่อ", message_id: str | None = None,
                 ext: str = ".jpg", group_id: str = "G1", user_id: str = "U1",
                 kind: str = "image", mime: str = "image/jpeg") -> tuple[Path, Path]:
    bin_path = outbox / f"{pair_id}.bin"
    json_path = outbox / f"{pair_id}.json"
    bin_path.write_bytes(content)
    data = {
        "groupId": group_id, "messageId": message_id or pair_id, "userId": user_id,
        "name": name, "ts": ts, "kind": kind, "mime": mime, "ext": ext,
        "sha256": sha256 if sha256 is not None else _sha256(content),
    }
    json_path.write_text(json.dumps(data), encoding="utf-8")
    return bin_path, json_path


# --------------------------------------------------------------------------- happy path

def test_complete_pair_uploads_then_deletes_locally(filer_env, monkeypatch):
    outbox = filer_env
    content = b"fake jpeg bytes"
    bin_path, json_path = _write_pair(outbox, "msg1", content)

    calls = []

    def fake_upload(path, name, subfolder):
        calls.append((path, name, subfolder))
        return True, "ok"
    monkeypatch.setattr(filer, "_upload_via_broker", fake_upload)

    counts = filer.tick()

    assert counts == {"filed": 1}
    assert not bin_path.exists()
    assert not json_path.exists()
    assert len(calls) == 1
    uploaded_path, uploaded_name, subfolder = calls[0]
    assert uploaded_path == bin_path
    assert "msg1" in uploaded_name
    assert subfolder == "2026-09"  # ts=1788975600 in Bangkok, see the tz test below

    ledger = filer._load_filed_ledger()
    assert _sha256(content) in ledger
    assert ledger[_sha256(content)]["date"] == "2026-09"


def test_filename_format_matches_spec(filer_env, monkeypatch):
    outbox = filer_env
    content = b"photo-bytes"
    _write_pair(outbox, "abc123", content, ts=1788975600, name="พ่อ", message_id="abc123", ext=".jpg")

    seen = {}
    monkeypatch.setattr(filer, "_upload_via_broker",
                         lambda path, name, subfolder: (seen.setdefault("name", name), (True, "ok"))[1])

    filer.tick()

    # (<sender name>) (D-M-YYYY) (<HHMM>) <messageId><ext>
    assert seen["name"].startswith("(พ่อ) (")
    assert seen["name"].endswith("abc123.jpg")


# --------------------------------------------------------------------------- incomplete pairs

def test_json_without_bin_is_skipped_not_half_processed(filer_env, monkeypatch):
    outbox = filer_env
    json_path = outbox / "orphan.json"
    json_path.write_text(json.dumps({
        "groupId": "G1", "messageId": "orphan", "userId": "U1", "name": "แม่",
        "ts": 1788975600, "kind": "image", "mime": "image/jpeg", "ext": ".jpg",
        "sha256": "deadbeef",
    }), encoding="utf-8")

    def fail_upload(*a, **kw):
        raise AssertionError("must never upload for an incomplete pair")
    monkeypatch.setattr(filer, "_upload_via_broker", fail_upload)

    counts = filer.tick()

    assert counts == {"skipped_incomplete": 1}
    assert json_path.exists()  # left alone, not quarantined, not deleted


def test_bin_without_json_is_never_touched(filer_env, monkeypatch):
    outbox = filer_env
    bin_path = outbox / "lonely.bin"
    bin_path.write_bytes(b"some bytes with no json sidecar yet")

    def fail_upload(*a, **kw):
        raise AssertionError("must never upload for a pair with no JSON")
    monkeypatch.setattr(filer, "_upload_via_broker", fail_upload)

    counts = filer.tick()

    assert counts == {}  # nothing enumerated at all -- driven by *.json glob
    assert bin_path.exists()


def test_corrupt_json_is_quarantined(filer_env, monkeypatch):
    outbox = filer_env
    bin_path = outbox / "bad.bin"
    bin_path.write_bytes(b"bytes")
    json_path = outbox / "bad.json"
    json_path.write_text("{not valid json", encoding="utf-8")

    def fail_upload(*a, **kw):
        raise AssertionError("must never upload for a corrupt pair")
    monkeypatch.setattr(filer, "_upload_via_broker", fail_upload)

    counts = filer.tick()

    assert counts == {"quarantined_corrupt": 1}
    assert not bin_path.exists()
    assert not json_path.exists()
    failed_dir = outbox / "failed"
    assert (failed_dir / "bad.bin").exists()
    assert (failed_dir / "bad.json").exists()


# --------------------------------------------------------------------------- sha256 mismatch

def test_sha_mismatch_quarantines_both_files_never_uploads(filer_env, monkeypatch):
    outbox = filer_env
    bin_path, json_path = _write_pair(outbox, "tampered", b"real bytes", sha256="0" * 64)

    def fail_upload(*a, **kw):
        raise AssertionError("must never upload a pair with a sha256 mismatch")
    monkeypatch.setattr(filer, "_upload_via_broker", fail_upload)

    counts = filer.tick()

    assert counts == {"quarantined_sha_mismatch": 1}
    failed_dir = outbox / "failed"
    assert (failed_dir / "tampered.bin").exists()
    assert (failed_dir / "tampered.json").exists()
    assert not bin_path.exists()
    assert not json_path.exists()


# --------------------------------------------------------------------------- dedup

def test_duplicate_sha_is_deleted_not_reuploaded(filer_env, monkeypatch):
    outbox = filer_env
    content = b"already filed before"
    sha = _sha256(content)
    bin_path, json_path = _write_pair(outbox, "dupe1", content, sha256=sha)

    ledger_path = outbox / "filed.json"
    ledger_path.write_text(json.dumps({sha: {"name": "(already) (1-1-2026) (0000) x.jpg", "date": "2026-01"}}),
                            encoding="utf-8")

    def fail_upload(*a, **kw):
        raise AssertionError("must never re-upload an already-filed sha256")
    monkeypatch.setattr(filer, "_upload_via_broker", fail_upload)

    counts = filer.tick()

    assert counts == {"duplicate": 1}
    assert not bin_path.exists()
    assert not json_path.exists()
    failed_dir = outbox / "failed"
    assert not failed_dir.exists() or not any(failed_dir.iterdir())


# --------------------------------------------------------------------------- Asia/Bangkok month folder

def test_month_folder_derived_in_asia_bangkok_not_utc():
    # A UTC evening timestamp that rolls into the next day (and month) once
    # converted to +07:00. 2026-08-31T18:30:00Z -> 2026-09-01T01:30 Bangkok.
    import calendar
    from datetime import datetime, timezone
    utc_dt = datetime(2026, 8, 31, 18, 30, 0, tzinfo=timezone.utc)
    ts = calendar.timegm(utc_dt.timetuple())

    data = {"ts": ts}
    assert filer._month_folder(data) == "2026-09"

    bkk = filer._local_dt(ts)
    assert bkk.year == 2026 and bkk.month == 9 and bkk.day == 1


def test_month_folder_used_end_to_end_for_a_utc_evening_timestamp(filer_env, monkeypatch):
    import calendar
    from datetime import datetime, timezone
    outbox = filer_env
    utc_dt = datetime(2026, 8, 31, 18, 30, 0, tzinfo=timezone.utc)
    ts = calendar.timegm(utc_dt.timetuple())
    content = b"evening upload"
    _write_pair(outbox, "evening1", content, ts=ts)

    seen = {}

    def fake_upload(path, name, subfolder):
        seen["subfolder"] = subfolder
        return True, "ok"
    monkeypatch.setattr(filer, "_upload_via_broker", fake_upload)

    filer.tick()

    assert seen["subfolder"] == "2026-09"


# --------------------------------------------------------------------------- failure / retry discipline

def test_failing_upload_never_deletes_the_local_pair(filer_env, monkeypatch):
    outbox = filer_env
    bin_path, json_path = _write_pair(outbox, "flaky", b"bytes")

    monkeypatch.setattr(filer, "_upload_via_broker", lambda path, name, subfolder: (False, "broker unreachable"))

    counts = filer.tick()

    assert counts == {"upload_failed": 1}
    assert bin_path.exists()
    assert json_path.exists()
    failcounts = filer._load_failcounts(filer.FAILCOUNT_PATH)
    assert failcounts.get("flaky") == 1


def test_retry_cap_quarantines_after_max_retries(filer_env, monkeypatch):
    outbox = filer_env
    bin_path, json_path = _write_pair(outbox, "always_flaky", b"bytes")

    monkeypatch.setattr(filer, "_upload_via_broker", lambda path, name, subfolder: (False, "broker unreachable"))

    for _ in range(filer.MAX_RETRIES - 1):
        counts = filer.tick()
        assert counts == {"upload_failed": 1}
        assert bin_path.exists()

    counts = filer.tick()
    assert counts == {"quarantined_retry_cap": 1}
    assert not bin_path.exists()
    assert not json_path.exists()
    failed_dir = outbox / "failed"
    assert (failed_dir / "always_flaky.bin").exists()
    assert (failed_dir / "always_flaky.json").exists()

    failcounts = filer._load_failcounts(filer.FAILCOUNT_PATH)
    assert "always_flaky" not in failcounts


def test_upload_recovering_before_retry_cap_clears_failcount(filer_env, monkeypatch):
    outbox = filer_env
    bin_path, json_path = _write_pair(outbox, "recovers", b"bytes")

    monkeypatch.setattr(filer, "_upload_via_broker", lambda path, name, subfolder: (False, "still down"))
    filer.tick()
    assert filer._load_failcounts(filer.FAILCOUNT_PATH).get("recovers") == 1

    monkeypatch.setattr(filer, "_upload_via_broker", lambda path, name, subfolder: (True, "ok"))
    counts = filer.tick()

    assert counts == {"filed": 1}
    assert not bin_path.exists()
    assert not json_path.exists()
    assert "recovers" not in filer._load_failcounts(filer.FAILCOUNT_PATH)


# --------------------------------------------------------------------------- ordering

def test_pairs_processed_oldest_ts_first(filer_env, monkeypatch):
    outbox = filer_env
    _write_pair(outbox, "newer", b"new-bytes", ts=1788975700)
    _write_pair(outbox, "older", b"old-bytes", ts=1788975600)

    order = []
    monkeypatch.setattr(filer, "_upload_via_broker",
                         lambda path, name, subfolder: (order.append(path.stem), (True, "ok"))[1])

    filer.tick()

    assert order == ["older", "newer"]


# --------------------------------------------------------------------------- single-flight

def test_concurrent_tick_is_skipped_not_double_processed(filer_env, monkeypatch):
    outbox = filer_env
    _write_pair(outbox, "locked", b"bytes")

    fd = filer._try_lock(filer.LOCK_PATH)
    assert fd is not None
    try:
        def fail_upload(*a, **kw):
            raise AssertionError("must not process while another tick holds the lock")
        monkeypatch.setattr(filer, "_upload_via_broker", fail_upload)
        counts = filer.tick()
        assert counts == {}
    finally:
        filer._unlock(fd)


# --------------------------------------------------------------------------- real socket, stub server -- never Drive

def _run_stub_broker_once(socket_path: Path, response: dict, captured: list):
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(socket_path))
    server.listen(1)
    server.settimeout(5.0)
    conn, _ = server.accept()
    try:
        raw = b""
        while not raw.endswith(b"\n"):
            chunk = conn.recv(65536)
            if not chunk:
                break
            raw += chunk
        captured.append(json.loads(raw.decode()))
        conn.sendall((json.dumps(response) + "\n").encode())
    finally:
        conn.close()
        server.close()


def test_upload_via_broker_sends_the_expected_wire_request_over_a_real_socket(filer_env, monkeypatch, tmp_path):
    # tmp_path lives under a path routinely over macOS's ~104-byte
    # sockaddr_un limit -- socket-binding tests need a short path, same
    # workaround scripts/test_drive_photo_broker.py's _cfg() uses.
    socket_path = Path(tempfile.mkdtemp(dir="/tmp")) / "stub.sock"
    monkeypatch.setattr(filer, "SOCKET_PATH", socket_path)

    captured: list = []
    response = {"ok": True, "id": "fake-id", "name": "(x) (1-1-2026) (0000) m.jpg", "link": None, "size": 5}
    t = threading.Thread(target=_run_stub_broker_once, args=(socket_path, response, captured), daemon=True)
    t.start()

    local = tmp_path / "photo.bin"
    local.write_bytes(b"12345")
    ok, detail = filer._upload_via_broker(local, "(x) (1-1-2026) (0000) m.jpg", "2026-01")
    t.join(timeout=5.0)

    assert ok is True
    assert captured == [{
        "op": "upload", "path": str(local),
        "name": "(x) (1-1-2026) (0000) m.jpg", "subfolder": "2026-01",
    }]


def test_upload_via_broker_reports_a_refused_upload_as_failure(filer_env, monkeypatch, tmp_path):
    socket_path = Path(tempfile.mkdtemp(dir="/tmp")) / "stub2.sock"
    monkeypatch.setattr(filer, "SOCKET_PATH", socket_path)

    captured: list = []
    response = {"ok": False, "error": "caller not authorized"}
    t = threading.Thread(target=_run_stub_broker_once, args=(socket_path, response, captured), daemon=True)
    t.start()

    local = tmp_path / "photo2.bin"
    local.write_bytes(b"12345")
    ok, detail = filer._upload_via_broker(local, "name.jpg", "2026-01")
    t.join(timeout=5.0)

    assert ok is False
    assert "not authorized" in detail


def test_upload_via_broker_handles_connection_refused(filer_env, monkeypatch, tmp_path):
    monkeypatch.setattr(filer, "SOCKET_PATH", tmp_path / "nothing-listening.sock")
    local = tmp_path / "photo3.bin"
    local.write_bytes(b"12345")

    ok, detail = filer._upload_via_broker(local, "name.jpg", "2026-01")

    assert ok is False
    assert "could not connect" in detail


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
