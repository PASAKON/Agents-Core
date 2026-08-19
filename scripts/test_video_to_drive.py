"""Tests for scripts/video_to_drive.py (task-4133eb30).

Stubs every Drive/network/subprocess boundary -- no real yt-dlp, no real
Drive calls, no network. video_to_drive's own module-level names
(api/upload/list_folder/download/probe_resolution) are patched directly --
the same idiom scripts/test_mailbox.py and scripts/test_cxo_crosstalk.py use
for looked-up-at-call-time module globals.

Covers (task's required list):
  1. find_or_create_folder reuses an existing "desktop cloud" folder --
     create (POST) is never called.
  2. find_or_create_folder creates it exactly once when absent.
  3. process_url: a verification miss (file not listed at destination) is a
     FAILURE and the local file is kept, not deleted.
  4. process_url: a size mismatch at the destination is a failure too.
  5. download(): the flaky "universal data for rehydration" TikTok error
     retries; any other yt-dlp error surfaces on the first attempt.
  6. process_url: an existing same-name-same-size remote file is SKIPped --
     upload is never called, nothing is deleted remotely (the module never
     calls any Drive delete/trash function at all).
  7. main(): exit code is non-zero when any URL fails, 0 when all succeed.

pytest style, tmp_path + monkeypatched module globals only (ADR 0021 §1).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_to_drive as vtd  # noqa: E402


def _make_local_file(tmp_path: Path, name: str = "clip.mp4", size: int = 2048) -> Path:
    p = tmp_path / name
    p.write_bytes(b"x" * size)
    return p


# --------------------------------------------------------------------------- find_or_create_folder

def test_folder_reused_when_already_exists(monkeypatch):
    calls = []

    def fake_api(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        calls.append(method)
        assert method == "GET", "must never POST (create) when the folder already exists"
        return {"files": [{"id": "existing-folder-id", "name": "desktop cloud"}]}

    monkeypatch.setattr(vtd, "api", fake_api)

    folder_id = vtd.find_or_create_folder("desktop cloud", "parent-id")

    assert folder_id == "existing-folder-id"
    assert calls == ["GET"]


def test_folder_created_exactly_once_when_absent(monkeypatch):
    calls = []

    def fake_api(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        calls.append(method)
        if method == "GET":
            return {"files": []}
        assert data is not None
        return {"id": "new-folder-id", "name": "desktop cloud"}

    monkeypatch.setattr(vtd, "api", fake_api)

    folder_id = vtd.find_or_create_folder("desktop cloud", "parent-id")

    assert folder_id == "new-folder-id"
    assert calls == ["GET", "POST"]
    assert calls.count("POST") == 1


# --------------------------------------------------------------------------- download() retry

def _fake_run_sequence(results):
    """results[i]: {"ok": True, "path": str} or {"ok": False, "stderr": str},
    one per successive yt-dlp invocation."""
    state = {"n": 0}

    def fake_run(cmd, capture_output=True, text=True):
        assert cmd[0] == "yt-dlp"
        i = state["n"]
        state["n"] += 1
        outcome = results[i]
        if outcome["ok"]:
            idx = cmd.index("--print-to-file")
            pathfile = Path(cmd[idx + 2])
            pathfile.write_text(outcome["path"] + "\n")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr=outcome.get("stderr", ""))

    return fake_run, state


def test_flaky_extractor_error_retries_and_eventually_succeeds(monkeypatch, tmp_path):
    target = tmp_path / "uploader-123.mp4"
    target.write_bytes(b"x" * 10)

    fake_run, state = _fake_run_sequence([
        {"ok": False, "stderr": "ERROR: Unable to extract universal data for rehydration"},
        {"ok": False, "stderr": "ERROR: Unable to extract universal data for rehydration"},
        {"ok": True, "path": str(target)},
    ])
    monkeypatch.setattr(vtd.subprocess, "run", fake_run)
    sleeps = []

    result = vtd.download("https://tiktok.com/x", tmp_path, sleep=sleeps.append)

    assert result == target
    assert state["n"] == 3
    assert len(sleeps) == 2  # backoff before attempt 2 and attempt 3, none after success


def test_non_flaky_error_fails_on_first_attempt_no_retry(monkeypatch, tmp_path):
    fake_run, state = _fake_run_sequence([
        {"ok": False, "stderr": "ERROR: Unsupported URL"},
        {"ok": True, "path": str(tmp_path / "unused.mp4")},  # must never be reached
    ])
    monkeypatch.setattr(vtd.subprocess, "run", fake_run)
    sleeps = []

    with pytest.raises(vtd.DownloadError, match="Unsupported URL"):
        vtd.download("https://example.com/x", tmp_path, sleep=sleeps.append)

    assert state["n"] == 1
    assert sleeps == []


# --------------------------------------------------------------------------- process_url

def test_verify_miss_is_failure_and_keeps_local_file(monkeypatch, tmp_path):
    local = _make_local_file(tmp_path, "clip.mp4", 2048)
    monkeypatch.setattr(vtd, "download", lambda url, dest_dir, **kw: local)
    monkeypatch.setattr(vtd, "probe_resolution", lambda p: "720x1280")
    monkeypatch.setattr(vtd, "list_folder", lambda folder_id: {})  # empty before AND after upload

    uploaded = {}
    monkeypatch.setattr(vtd, "upload", lambda path, name, folder_id: uploaded.setdefault("v", {"id": "x"}))

    ok = vtd.process_url("https://example.com/v", folder_id="F", stage_dir=tmp_path,
                         log_path=tmp_path / "log.txt")

    assert ok is False
    assert "v" in uploaded  # it did upload -- the miss is at the verify step, not before
    assert local.exists()  # kept, not deleted


def test_size_mismatch_at_destination_is_failure(monkeypatch, tmp_path):
    local = _make_local_file(tmp_path, "clip.mp4", 2048)
    monkeypatch.setattr(vtd, "download", lambda url, dest_dir, **kw: local)
    monkeypatch.setattr(vtd, "probe_resolution", lambda p: "720x1280")

    listings = iter([{}, {"clip.mp4": 999}])  # pre-upload: absent; post-upload: wrong size
    monkeypatch.setattr(vtd, "list_folder", lambda folder_id: next(listings))
    monkeypatch.setattr(vtd, "upload", lambda path, name, folder_id: {"id": "x"})

    ok = vtd.process_url("https://example.com/v", folder_id="F", stage_dir=tmp_path,
                         log_path=tmp_path / "log.txt")

    assert ok is False
    assert local.exists()


def test_existing_same_name_same_size_is_skipped(monkeypatch, tmp_path):
    local = _make_local_file(tmp_path, "clip.mp4", 4096)
    monkeypatch.setattr(vtd, "download", lambda url, dest_dir, **kw: local)
    monkeypatch.setattr(vtd, "probe_resolution", lambda p: "1080x1920")
    monkeypatch.setattr(vtd, "list_folder", lambda folder_id: {"clip.mp4": 4096})

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be called on a name+size match")
    monkeypatch.setattr(vtd, "upload", fail_upload)

    log_path = tmp_path / "log.txt"
    ok = vtd.process_url("https://example.com/v", folder_id="F", stage_dir=tmp_path, log_path=log_path)

    assert ok is True
    assert not local.exists()  # remote already verified equal -- safe to drop staging copy
    assert "SKIP" in log_path.read_text()
    # nothing is deleted remotely: the module holds no trash/delete call at all
    assert not hasattr(vtd, "trash") and not hasattr(vtd, "delete_remote")


def test_successful_upload_verifies_logs_and_deletes_local(monkeypatch, tmp_path):
    local = _make_local_file(tmp_path, "clip.mp4", 4096)
    monkeypatch.setattr(vtd, "download", lambda url, dest_dir, **kw: local)
    monkeypatch.setattr(vtd, "probe_resolution", lambda p: "1080x1920")

    listings = iter([{}, {"clip.mp4": 4096}])  # absent before, present+matching after
    monkeypatch.setattr(vtd, "list_folder", lambda folder_id: next(listings))
    monkeypatch.setattr(vtd, "upload", lambda path, name, folder_id: {"id": "file-id-1"})

    log_path = tmp_path / "log.txt"
    ok = vtd.process_url("https://example.com/v", folder_id="F", stage_dir=tmp_path, log_path=log_path)

    assert ok is True
    assert not local.exists()
    log_text = log_path.read_text()
    assert "ADD" in log_text and "file-id-1" in log_text


# --------------------------------------------------------------------------- main() exit code

def test_main_exit_code_nonzero_when_any_url_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(vtd, "load_parent_folder_id", lambda: "parent-id")
    monkeypatch.setattr(vtd, "find_or_create_folder", lambda name, parent_id: "folder-id")
    outcomes = {"https://a": True, "https://b": False}
    monkeypatch.setattr(vtd, "process_url", lambda url, **kw: outcomes[url])

    rc = vtd.main(["https://a", "https://b", "--log-file", str(tmp_path / "log.txt")])

    assert rc == 1


def test_main_exit_code_zero_when_all_succeed(monkeypatch, tmp_path):
    monkeypatch.setattr(vtd, "load_parent_folder_id", lambda: "parent-id")
    monkeypatch.setattr(vtd, "find_or_create_folder", lambda name, parent_id: "folder-id")
    monkeypatch.setattr(vtd, "process_url", lambda url, **kw: True)

    rc = vtd.main(["https://a", "https://b", "--log-file", str(tmp_path / "log.txt")])

    assert rc == 0
