"""Tests for scripts/gdrive-bridge/ilag_sync.py's diff: md5 is the proof, size only the pre-check
(CEO 2026-09-28 ruling 3, "md5 everywhere"). No live Drive call: api/urlopen refuse."""
import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "gdrive-bridge"))
import ilag_sync  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("ilag_sync tried a real Drive call")
    monkeypatch.setattr(ilag_sync, "api", refuse)
    monkeypatch.setattr(urllib.request, "urlopen", refuse)


def local_entry(tmp_path, rel, data):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return {"size": len(data), "abs": p}


def drive_entry(data, fid="D", md5=True, mime="video/mp4"):
    return {"id": fid, "size": len(data), "mime": mime,
            "md5": hashlib.md5(data).hexdigest() if md5 else None}


def test_md5_file_streams_in_chunks(tmp_path):
    p = tmp_path / "clip.mp4"
    data = bytes(range(256)) * 41
    p.write_bytes(data)
    assert ilag_sync.md5_file(p, chunk=7) == hashlib.md5(data).hexdigest()


def test_same_size_different_bytes_is_an_md5_mismatch(tmp_path):
    local = {"All Scene/S1/a.mp4": local_entry(tmp_path, "a.mp4", b"AAAA")}
    drive = {"All Scene/S1/a.mp4": drive_entry(b"AAAB")}
    r = ilag_sync.compare(local, drive)
    assert r["size_mismatch"] == []
    assert r["md5_mismatch"] == ["All Scene/S1/a.mp4"]
    assert r["local_md5"]["All Scene/S1/a.mp4"] == hashlib.md5(b"AAAA").hexdigest()


def test_identical_bytes_are_clean(tmp_path):
    local = {"S1/a.mp4": local_entry(tmp_path, "a.mp4", b"same bytes")}
    drive = {"S1/a.mp4": drive_entry(b"same bytes")}
    r = ilag_sync.compare(local, drive)
    assert (r["only_local"], r["only_drive"], r["size_mismatch"], r["md5_mismatch"],
            r["unverified"]) == ([], [], [], [], [])
    assert r["both"] == ["S1/a.mp4"]


def test_size_mismatch_is_reported_without_hashing(tmp_path, monkeypatch):
    local = {"S1/a.mp4": local_entry(tmp_path, "a.mp4", b"short")}
    drive = {"S1/a.mp4": drive_entry(b"much longer")}
    monkeypatch.setattr(ilag_sync, "md5_file",
                        lambda *a, **k: pytest.fail("size already differs; no hash needed"))
    r = ilag_sync.compare(local, drive)
    assert r["size_mismatch"] == ["S1/a.mp4"] and r["md5_mismatch"] == []


def test_no_md5_on_drive_is_unverified_not_clean(tmp_path):
    local = {"S1/a.mp4": local_entry(tmp_path, "a.mp4", b"bytes")}
    drive = {"S1/a.mp4": drive_entry(b"bytes", md5=False)}
    r = ilag_sync.compare(local, drive)
    assert r["unverified"] == ["S1/a.mp4"] and r["md5_mismatch"] == []


def test_only_drive_skips_logs_and_google_native_files(tmp_path):
    drive = {"logs.txt": drive_entry(b"log", mime="text/plain"),
             "StoryBoard": drive_entry(b"", md5=False, mime="application/vnd.google-apps.document"),
             "S1/gone.mp4": drive_entry(b"x")}
    assert ilag_sync.compare({}, drive)["only_drive"] == ["S1/gone.mp4"]


def test_walk_drive_asks_for_and_keeps_md5(monkeypatch):
    seen = {}

    def fake_api(url, params=None, **kw):
        seen["fields"] = params["fields"]
        return {"files": [{"id": "X", "name": "a.mp4", "mimeType": "video/mp4",
                           "size": "4", "md5Checksum": "abc"}]}
    monkeypatch.setattr(ilag_sync, "api", fake_api)
    files, _ = ilag_sync.walk_drive("ROOT")
    assert "md5Checksum" in seen["fields"]
    assert files["a.mp4"]["md5"] == "abc"


def test_diff_prints_md5_mismatch_and_the_mark_command(tmp_path, monkeypatch, capsys):
    local = {"S1/a.mp4": local_entry(tmp_path, "a.mp4", b"AAAA")}
    drive = {"S1/a.mp4": drive_entry(b"AAAB", fid="DRIVE-ID-1")}
    monkeypatch.setattr(ilag_sync, "walk_local", lambda root: local)
    monkeypatch.setattr(ilag_sync, "walk_drive", lambda fid: (drive, {"": fid, "S1": "S1ID"}))
    monkeypatch.setattr(sys, "argv", ["ilag_sync.py", "diff"])
    assert ilag_sync.main() == 0
    out = capsys.readouterr().out
    assert "md5-mismatch: 1" in out and "size-mismatch: 0" in out
    assert "DIFFERENT MD5" in out
    assert "drive_broken.py mark DRIVE-ID-1" in out
