"""Tests for scripts/video_to_drive.py (task-4133eb30, task-c7d455aa D3/D4).

Stubs every Drive/network/subprocess boundary -- no real yt-dlp, no real
Drive calls, no network. video_to_drive's own module-level names
(upload/list_folder/download/probe_resolution) are patched directly -- the
same idiom scripts/test_mailbox.py and scripts/test_cxo_crosstalk.py use
for looked-up-at-call-time module globals.

Covers (task's required list):
  1. resolve_oauth_env_candidates: SOMPONG_DRIVE_ENV, when set, names exactly
     one file; unset falls back to CF_ENV_CANDIDATES unchanged (D4).
  2. apply_oauth_env_override actually rewrites ilag_sync's module-level
     ENV_CANDIDATES -- the thing that makes the OAuth loader itself
     configurable, not just the resolver function.
  3. main() targets DRIVE_SOMPONG_GRAB_FOLDER_ID directly -- no
     find-or-create call, no sub-folder -- and DRIVE_VIDEO_PARENT_FOLDER_ID
     is never read anywhere in this module (D3 guard test -- this is the
     one that protects mooniex-claudeflow/src/video/videodrive.js and
     scripts/higgsfield/gen_loop.py, which both depend on that variable
     meaning something else).
  4. process_url: a verification miss (file not listed at destination) is a
     FAILURE and the local file is kept, not deleted.
  5. process_url: a size mismatch at the destination is a failure too.
  6. download(): the flaky "universal data for rehydration" TikTok error
     retries; any other yt-dlp error surfaces on the first attempt.
  7. process_url: an existing same-name-same-size remote file is SKIPped --
     upload is never called, nothing is deleted remotely (the module never
     calls any Drive delete/trash function at all).
  8. main(): exit code is non-zero when any URL fails, 0 when all succeed.

pytest style, tmp_path + monkeypatched module globals only (ADR 0021 §1).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_to_drive as vtd  # noqa: E402
import ilag_sync  # noqa: E402 -- same module vtd.apply_oauth_env_override() mutates


def _make_local_file(tmp_path: Path, name: str = "clip.mp4", size: int = 2048) -> Path:
    p = tmp_path / name
    p.write_bytes(b"x" * size)
    return p


# --------------------------------------------------------------------------- D3/D4: folder + env config

def test_no_reference_to_drive_video_parent_folder_id_anywhere_in_module():
    """D3 guard test: this module must never read DRIVE_VIDEO_PARENT_FOLDER_ID
    -- that variable resolves to ALL DRAFT/BLACK LIQUIDITY and is load-bearing
    for mooniex-claudeflow/src/video/videodrive.js and
    scripts/higgsfield/gen_loop.py. Source-level check, not a call-tracking
    mock, so it also catches a re-introduction that never gets exercised by
    another test. The module docstring is allowed to MENTION the variable's
    name (explaining why it is deliberately absent) -- what must never appear
    is code that actually reads it."""
    source = Path(vtd.__file__).read_text()
    assert 'os.environ.get("DRIVE_VIDEO_PARENT_FOLDER_ID"' not in source
    assert "== 'DRIVE_VIDEO_PARENT_FOLDER_ID'" not in source
    assert '== "DRIVE_VIDEO_PARENT_FOLDER_ID"' not in source
    assert not hasattr(vtd, "load_parent_folder_id")
    assert not hasattr(vtd, "find_or_create_folder")


def test_main_uploads_directly_into_the_sompong_grab_folder_no_subfolder(monkeypatch, tmp_path):
    monkeypatch.setattr(vtd.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setattr(vtd, "apply_oauth_env_override", lambda: None)
    seen_folder_ids = []

    def fake_process_url(url, *, folder_id, **kw):
        seen_folder_ids.append(folder_id)
        return True

    monkeypatch.setattr(vtd, "process_url", fake_process_url)

    rc = vtd.main(["https://a", "--log-file", str(tmp_path / "log.txt")])

    assert rc == 0
    assert seen_folder_ids == [vtd.DRIVE_SOMPONG_GRAB_FOLDER_ID]
    assert vtd.DRIVE_SOMPONG_GRAB_FOLDER_ID == "115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR"


def test_main_calls_apply_oauth_env_override_before_any_upload(monkeypatch, tmp_path):
    monkeypatch.setattr(vtd.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    order = []
    monkeypatch.setattr(vtd, "apply_oauth_env_override", lambda: order.append("env"))
    monkeypatch.setattr(vtd, "process_url", lambda url, **kw: order.append("upload") or True)

    vtd.main(["https://a", "--log-file", str(tmp_path / "log.txt")])

    assert order == ["env", "upload"]


def test_resolve_oauth_env_candidates_uses_sompong_drive_env_when_set(monkeypatch):
    monkeypatch.setenv("SOMPONG_DRIVE_ENV", "/opt/mooniex-secrets/drive.env")
    assert vtd.resolve_oauth_env_candidates() == [Path("/opt/mooniex-secrets/drive.env")]


def test_resolve_oauth_env_candidates_falls_back_to_claudeflow_candidates_when_unset(monkeypatch):
    monkeypatch.delenv("SOMPONG_DRIVE_ENV", raising=False)
    assert vtd.resolve_oauth_env_candidates() == vtd.CF_ENV_CANDIDATES


def test_apply_oauth_env_override_rewrites_ilag_sync_env_candidates(monkeypatch):
    monkeypatch.setenv("SOMPONG_DRIVE_ENV", "/opt/mooniex-secrets/drive.env")
    original = list(ilag_sync.ENV_CANDIDATES)
    try:
        vtd.apply_oauth_env_override()
        assert ilag_sync.ENV_CANDIDATES == [Path("/opt/mooniex-secrets/drive.env")]
    finally:
        ilag_sync.ENV_CANDIDATES = original


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


def test_verify_listing_that_raises_fails_one_url_not_the_whole_batch(monkeypatch, tmp_path):
    """A blip during verification must cost one URL, not the run.

    The pre-upload listing was guarded and the post-upload one was not, so a
    transient error there escaped process_url, killed the loop mid-batch and
    skipped the summary -- losing every later URL right after an upload that
    had actually succeeded.
    """
    local = _make_local_file(tmp_path, "clip.mp4", 2048)
    monkeypatch.setattr(vtd, "download", lambda url, dest_dir, **kw: local)
    monkeypatch.setattr(vtd, "probe_resolution", lambda p: "720x1280")

    calls = {"n": 0}

    def flaky_list(folder_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return {}                       # pre-upload: not there yet
        raise OSError("connection reset")   # post-upload: verification blows up

    monkeypatch.setattr(vtd, "list_folder", flaky_list)
    monkeypatch.setattr(vtd, "upload", lambda path, name, folder_id: {"id": "x"})

    ok = vtd.process_url("https://example.com/v", folder_id="F", stage_dir=tmp_path,
                         log_path=tmp_path / "log.txt")

    assert ok is False
    assert local.exists(), "unverified upload must keep the local copy"


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
    monkeypatch.setattr(vtd.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setattr(vtd, "apply_oauth_env_override", lambda: None)
    outcomes = {"https://a": True, "https://b": False}
    monkeypatch.setattr(vtd, "process_url", lambda url, **kw: outcomes[url])

    rc = vtd.main(["https://a", "https://b", "--log-file", str(tmp_path / "log.txt")])

    assert rc == 1


def test_main_exit_code_zero_when_all_succeed(monkeypatch, tmp_path):
    monkeypatch.setattr(vtd.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setattr(vtd, "apply_oauth_env_override", lambda: None)
    monkeypatch.setattr(vtd, "process_url", lambda url, **kw: True)

    rc = vtd.main(["https://a", "https://b", "--log-file", str(tmp_path / "log.txt")])

    assert rc == 0


def test_main_fails_fast_when_yt_dlp_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(vtd.shutil, "which", lambda tool: None)
    called = {}
    monkeypatch.setattr(vtd, "apply_oauth_env_override", lambda: called.setdefault("hit", True))

    rc = vtd.main(["https://a", "--log-file", str(tmp_path / "log.txt")])

    assert rc == 1
    assert "hit" not in called  # never got as far as touching Drive/env
