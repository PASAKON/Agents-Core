"""tools/work_archive.py — Work/<task_id>/ cold-archive step (task-abc20690,
Work/RULES.md rule 6, ADR 0030).

Every test injects `root=tmp_path` and a fake `uploader` — never the real
~/MoonieXHQ/Work or the real Google Drive. Run via:
    pytest tests/test_work_archive.py
(not in pytest.ini's default testpaths, same convention as test_workdir.py.)
"""
from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.work_archive as work_archive  # noqa: E402
import tools.workdir as workdir  # noqa: E402

TASK = "task-abc12345"


def _make_folder(tmp_path: Path) -> Path:
    folder = workdir.create(TASK, root=tmp_path)
    (folder / "in" / "unfiled.jpg").write_bytes(b"y" * 5)
    (folder / "out" / "deliverable.mp4").write_bytes(b"z" * 7)
    return folder


def _matching_uploader(calls: list | None = None):
    """Fake uploader whose returned md5Checksum always matches the local md5
    work_archive.py computed for the same file (round-tripped via its own
    _hash_file so this test never hardcodes a checksum)."""
    def _uploader(local_path: Path, dest_name: str) -> dict:
        _, md5 = work_archive._hash_file(local_path)
        if calls is not None:
            calls.append((local_path, dest_name))
        return {"id": "fake-" + dest_name, "name": dest_name, "md5Checksum": md5}
    return _uploader


def _mismatching_uploader(local_path: Path, dest_name: str) -> dict:
    return {"id": "fake-" + dest_name, "name": dest_name, "md5Checksum": "0" * 32}


# --------------------------------------------------------------------- basics

def test_archive_rejects_empty_paths(tmp_path):
    _make_folder(tmp_path)
    with pytest.raises(ValueError):
        work_archive.archive(TASK, [], root=tmp_path)


def test_archive_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        work_archive.archive(TASK, ["in/unfiled.jpg"], root=tmp_path)


# --------------------------------------------------------------------- dry_run

def test_dry_run_uploads_nothing_and_deletes_nothing(tmp_path):
    folder = _make_folder(tmp_path)
    calls: list = []

    result = work_archive.archive(
        TASK, ["in/unfiled.jpg", "out/deliverable.mp4"],
        root=tmp_path, dry_run=True, uploader=_matching_uploader(calls),
    )

    assert result["dry_run"] is True
    assert result["verified"] is False
    assert calls == []  # uploader never called
    assert (folder / "in" / "unfiled.jpg").exists()
    assert (folder / "out" / "deliverable.mp4").exists()
    # the tar/manifest are still built locally so the preview is inspectable
    assert Path(result["tar_path"]).exists()
    assert Path(result["manifest_path"]).exists()


# ------------------------------------------------------------- tar + manifest

def test_tar_and_manifest_contents(tmp_path):
    _make_folder(tmp_path)
    result = work_archive.archive(
        TASK, ["in/unfiled.jpg", "out/deliverable.mp4"],
        root=tmp_path, dry_run=True,
    )

    assert result["dest"].startswith(f"Agents-Work-{TASK}-")
    assert result["dest"].endswith(".tar")
    with tarfile.open(result["tar_path"]) as tf:
        names = sorted(tf.getnames())
    assert names == ["in/unfiled.jpg", "out/deliverable.mp4"]

    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["task"] == TASK
    assert manifest["files"] == 2
    assert manifest["bytes"] == Path(result["tar_path"]).stat().st_size
    assert manifest["sha256"] == result["sha256"]
    assert manifest["md5"] == result["md5"]
    assert sorted(manifest["sources"]) == ["in/unfiled.jpg", "out/deliverable.mp4"]
    assert manifest["created"][-6] in ("+", "-")  # ISO-8601 with a UTC offset
    assert TASK in manifest["restore"] and result["dest"] in manifest["restore"]


# -------------------------------------------------------------- verified path

def test_matching_md5_verifies_and_logs(tmp_path, monkeypatch):
    folder = _make_folder(tmp_path)
    log_path = tmp_path / "drive-archive.log"
    monkeypatch.setattr(work_archive, "LOG_PATH", str(log_path))
    calls: list = []

    result = work_archive.archive(
        TASK, ["in/unfiled.jpg", "out/deliverable.mp4"],
        root=tmp_path, dry_run=False, uploader=_matching_uploader(calls),
    )

    assert result["verified"] is True
    assert result["error"] is None
    assert len(calls) == 2  # tar, then manifest
    # local scratch is cleaned up only after a verified upload
    assert not Path(result["tar_path"]).exists()
    assert not Path(result["manifest_path"]).exists()
    # nothing about the SOURCE files changes -- archive() never deletes them
    assert (folder / "in" / "unfiled.jpg").exists()
    assert (folder / "out" / "deliverable.mp4").exists()

    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
    assert all("verified" in ln and "drive md5" in ln for ln in lines)
    assert result["dest"] in lines[0]


# ------------------------------------------------------------- mismatch path

def test_md5_mismatch_verifies_false_keeps_local_tar(tmp_path, monkeypatch):
    folder = _make_folder(tmp_path)
    log_path = tmp_path / "drive-archive.log"
    monkeypatch.setattr(work_archive, "LOG_PATH", str(log_path))

    result = work_archive.archive(
        TASK, ["in/unfiled.jpg", "out/deliverable.mp4"],
        root=tmp_path, dry_run=False, uploader=_mismatching_uploader,
    )

    assert result["verified"] is False
    assert result["error"] and "mismatch" in result["error"]
    assert Path(result["tar_path"]).exists()  # nothing deleted on mismatch
    assert Path(result["manifest_path"]).exists()
    assert (folder / "in" / "unfiled.jpg").exists()
    assert (folder / "out" / "deliverable.mp4").exists()
    assert not log_path.exists()  # only a verified archive gets logged


def test_uploader_exception_verifies_false(tmp_path):
    _make_folder(tmp_path)

    def _boom(local_path, dest_name):
        raise RuntimeError("network down")

    result = work_archive.archive(
        TASK, ["in/unfiled.jpg"], root=tmp_path, dry_run=False, uploader=_boom,
    )

    assert result["verified"] is False
    assert "network down" in result["error"]


# ------------------------------------------- _default_uploader (opener seam)
#
# iteration 1 (CTO reopen 2026-09-23): _default_uploader now speaks the Drive
# REST resumable-upload protocol itself, chunked, via an injected `opener`
# seam -- never the Drive-for-Desktop mount, never ilag_sync.py's upload()
# (whole file in RAM). These tests exercise that chunking directly; no
# socket, no real Drive, no real OAuth (access_token() is monkeypatched out).

import re


def _range_end(content_range: str) -> int:
    # "bytes {start}-{end}/{size}" -> end
    return int(re.match(r"bytes (\d+)-(\d+)/(\d+)", content_range).group(2))


def test_default_uploader_resumable_chunks_and_308(tmp_path, monkeypatch):
    monkeypatch.setattr(work_archive, "_access_token", lambda: "fake-token")

    size = 20 * 1024 * 1024  # 20 MiB -> 8 + 8 + 4 MiB, three PUTs
    local = tmp_path / "big.tar"
    local.write_bytes(b"\0" * size)

    calls: list[tuple] = []

    def fake_opener(method, url, *, headers=None, body=None):
        calls.append((method, url, dict(headers or {}), body or b""))
        if method == "POST":
            assert url.startswith(work_archive.DRIVE_UPLOAD)
            assert headers["X-Upload-Content-Length"] == str(size)
            return 200, {"Location": "https://fake.example/session-1"}, b""
        if method == "PUT":
            assert url == "https://fake.example/session-1"
            assert len(body) <= work_archive.CHUNK_SIZE  # never more than one chunk
            put_so_far = sum(1 for c in calls if c[0] == "PUT")
            end = _range_end(headers["Content-Range"])
            if put_so_far < 3:
                return 308, {"Range": f"bytes=0-{end}"}, b""
            return 200, {}, json.dumps({
                "id": "file123", "name": "big.tar", "size": str(size),
                "md5Checksum": "deadbeefdeadbeefdeadbeefdeadbeef",
            }).encode()
        raise AssertionError(f"unexpected method {method}")

    meta = work_archive._default_uploader(local, "big.tar", opener=fake_opener)

    put_calls = [c for c in calls if c[0] == "PUT"]
    assert len(put_calls) == 3
    assert [c[2]["Content-Range"] for c in put_calls] == [
        f"bytes 0-8388607/{size}",
        f"bytes 8388608-16777215/{size}",
        f"bytes 16777216-20971519/{size}",
    ]
    assert all(len(c[3]) <= work_archive.CHUNK_SIZE for c in put_calls)  # no single read > 8 MiB
    assert meta["md5Checksum"] == "deadbeefdeadbeefdeadbeefdeadbeef"


def test_default_uploader_falls_back_to_get_by_id_for_md5(tmp_path, monkeypatch):
    monkeypatch.setattr(work_archive, "_access_token", lambda: "fake-token")
    local = tmp_path / "small.tar"
    local.write_bytes(b"x" * 100)

    calls: list[tuple] = []

    def fake_opener(method, url, *, headers=None, body=None):
        calls.append((method, url, dict(headers or {})))
        if method == "POST":
            return 200, {"Location": "https://fake.example/session-2"}, b""
        if method == "PUT":
            # final chunk in one PUT (100 bytes), response carries no md5Checksum
            return 200, {}, json.dumps({"id": "file999", "name": "small.tar", "size": "100"}).encode()
        if method == "GET":
            assert url.startswith(f"{work_archive.DRIVE_FILES}/file999")
            assert headers["Authorization"] == "Bearer fake-token"
            return 200, {}, json.dumps({"id": "file999", "md5Checksum": "cafebabe"}).encode()
        raise AssertionError(f"unexpected method {method}")

    meta = work_archive._default_uploader(local, "small.tar", opener=fake_opener)

    assert meta["md5Checksum"] == "cafebabe"
    assert [c[0] for c in calls] == ["POST", "PUT", "GET"]  # GET only fired because md5 was missing
