"""Tests for scripts/gdrive-bridge/ilag_mirror.py."""
import sys
from pathlib import Path

# Add gdrive-bridge to path to import ilag_mirror
sys.path.insert(0, str(Path(__file__).resolve().parent / "gdrive-bridge"))
import ilag_mirror

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Every Drive call in ilag_mirror goes through its module-level `api`.
    Fail loudly instead of reaching Drive if a test leaves a path unmocked --
    e.g. if the where-check is removed and main() falls through to list_folder."""
    def _refuse(*args, **kwargs):
        raise AssertionError("ilag_mirror tried a real Drive API call")
    monkeypatch.setattr(ilag_mirror, "api", _refuse)


def test_mismatch_returns_2(tmp_path, monkeypatch, capsys):
    f = tmp_path / "test.mp4"
    f.write_text("data")

    upload_called = False
    def mock_upload(*args, **kwargs):
        nonlocal upload_called
        upload_called = True
        return {"id": "123"}

    log_called = False
    def mock_append_log(*args, **kwargs):
        nonlocal log_called
        log_called = True

    def mock_folder_name(folder_id):
        return "S3-A"

    monkeypatch.setattr(ilag_mirror, "upload", mock_upload)
    monkeypatch.setattr(ilag_mirror, "append_log", mock_append_log)
    monkeypatch.setattr(ilag_mirror, "folder_name", mock_folder_name)
    monkeypatch.setattr(sys, "argv", ["ilag_mirror.py", "folder_abc", "All Scene/S9-C", "note", str(f)])

    assert ilag_mirror.main() == 2

    out, err = capsys.readouterr()
    assert "refusing to upload: <where> segment 'S9-C' does not match Drive folder name 'S3-A'" in out

    assert not upload_called
    assert not log_called
    assert f.exists()

def test_match_calls_upload_and_deletes(tmp_path, monkeypatch, capsys):
    f = tmp_path / "test.mp4"
    f.write_text("data")

    upload_called = False
    def mock_upload(*args, **kwargs):
        nonlocal upload_called
        upload_called = True
        return {"id": "123"}

    log_called = False
    def mock_append_log(lines, *args, **kwargs):
        nonlocal log_called
        log_called = True
        assert len(lines) == 1
        assert "All Scene/S9-C" in lines[0]

    def mock_folder_name(folder_id):
        return "S9-C"

    def mock_list_folder(folder_id):
        return {"test.mp4": len("data")}

    monkeypatch.setattr(ilag_mirror, "upload", mock_upload)
    monkeypatch.setattr(ilag_mirror, "append_log", mock_append_log)
    monkeypatch.setattr(ilag_mirror, "folder_name", mock_folder_name)
    monkeypatch.setattr(ilag_mirror, "list_folder", mock_list_folder)
    monkeypatch.setattr(sys, "argv", ["ilag_mirror.py", "folder_abc", "All Scene/S9-C", "note", str(f)])

    assert ilag_mirror.main() == 0

    assert upload_called
    assert log_called
    assert not f.exists()

def test_match_no_delete(tmp_path, monkeypatch, capsys):
    f = tmp_path / "test.mp4"
    f.write_text("data")

    def mock_upload(*args, **kwargs):
        return {"id": "123"}

    def mock_append_log(lines, *args, **kwargs):
        pass

    def mock_folder_name(folder_id):
        return "S9-C"

    def mock_list_folder(folder_id):
        return {"test.mp4": len("data")}

    monkeypatch.setattr(ilag_mirror, "upload", mock_upload)
    monkeypatch.setattr(ilag_mirror, "append_log", mock_append_log)
    monkeypatch.setattr(ilag_mirror, "folder_name", mock_folder_name)
    monkeypatch.setattr(ilag_mirror, "list_folder", mock_list_folder)
    monkeypatch.setattr(sys, "argv", ["ilag_mirror.py", "--no-delete", "folder_abc", "All Scene/S9-C", "note", str(f)])

    assert ilag_mirror.main() == 0

    assert f.exists()

def test_folder_lookup_exception(tmp_path, monkeypatch, capsys):
    f = tmp_path / "test.mp4"
    f.write_text("data")

    upload_called = False
    def mock_upload(*args, **kwargs):
        nonlocal upload_called
        upload_called = True
        return {"id": "123"}

    def mock_folder_name(folder_id):
        raise ValueError("Network error")

    monkeypatch.setattr(ilag_mirror, "upload", mock_upload)
    monkeypatch.setattr(ilag_mirror, "folder_name", mock_folder_name)
    monkeypatch.setattr(sys, "argv", ["ilag_mirror.py", "folder_abc", "All Scene/S9-C", "note", str(f)])

    assert ilag_mirror.main() == 2

    out, err = capsys.readouterr()
    assert "failed to look up folder name" in out

    assert not upload_called
    assert f.exists()

def test_trailing_slash_matches(tmp_path, monkeypatch, capsys):
    f = tmp_path / "test.mp4"
    f.write_text("data")

    upload_called = False
    def mock_upload(*args, **kwargs):
        nonlocal upload_called
        upload_called = True
        return {"id": "123"}

    def mock_append_log(lines, *args, **kwargs):
        pass

    def mock_folder_name(folder_id):
        return "S9-C"

    def mock_list_folder(folder_id):
        return {"test.mp4": len("data")}

    monkeypatch.setattr(ilag_mirror, "upload", mock_upload)
    monkeypatch.setattr(ilag_mirror, "append_log", mock_append_log)
    monkeypatch.setattr(ilag_mirror, "folder_name", mock_folder_name)
    monkeypatch.setattr(ilag_mirror, "list_folder", mock_list_folder)
    # The where argument has a trailing slash
    monkeypatch.setattr(sys, "argv", ["ilag_mirror.py", "folder_abc", "All Scene/S9-C/", "note", str(f)])

    assert ilag_mirror.main() == 0

    assert upload_called
    assert not f.exists()
