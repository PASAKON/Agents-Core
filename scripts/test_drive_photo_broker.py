"""Tests for runners/drive_photo_broker.py (task-a1c618db, broker #2).

Sibling of scripts/test_drive_upload_broker.py -- same mocking idiom (a real
temp AF_UNIX socket where the wire protocol itself needs exercising,
`ilag_sync.upload` / `broker.list_folder` / `ilag_sync.api` monkeypatched at
the broker module's own names otherwise). Nothing here ever touches a real
Drive service.

Covers (task's required list for this file):
  1. the `subfolder` regex accepts "2026-09" and rejects "../x", "2026-9",
     "2026-09/x", an id-looking string, unicode digits, empty, and a
     1000-char value
  2. a request carrying folder_id/parent/destination is ignored entirely
  3. only "upload" exists (grep-style guard, sibling of the original
     broker's guard test)
  4. uid rejection
  5. oversize rejection

Plus: the month-folder resolve-or-create path (found vs. created, and both
scoped to the fixed folder id only), load_config() validation, and the same
credential-redaction / verify-before-trust coverage the sibling broker has,
adapted for the subfolder-aware do_upload().
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import runners.drive_photo_broker as broker  # noqa: E402
import ilag_sync  # noqa: E402 -- same module object broker.py mutates ENV_CANDIDATES on


def _cfg(tmp_path, **overrides) -> broker.BrokerConfig:
    staging = tmp_path / "staging"
    staging.mkdir(exist_ok=True)
    defaults = dict(
        env_path=tmp_path / "creds.env",
        # tmp_path lives under a path routinely over macOS's ~104-byte
        # sockaddr_un limit -- socket-binding tests need a short path.
        socket_path=Path(tempfile.mkdtemp(dir="/tmp")) / "p.sock",
        allowed_uids=frozenset({os.getuid()}),
        staging_root=staging.resolve(),
        folder_id="FIXED-PHOTO-FOLDER-ID",
        max_upload_bytes=1_000_000,
        max_request_bytes=65536,
        socket_timeout=5.0,
    )
    defaults.update(overrides)
    return broker.BrokerConfig(**defaults)


def _staged_file(cfg: broker.BrokerConfig, name: str = "photo.jpg", size: int = 1024) -> Path:
    p = cfg.staging_root / name
    p.write_bytes(b"x" * size)
    return p


# --------------------------------------------------------------------------- 1. subfolder regex

@pytest.mark.parametrize("value", ["2026-09", "2026-01", "9999-12", "0000-00"])
def test_valid_subfolder_values_accepted(value):
    assert broker._valid_subfolder(value) is True


@pytest.mark.parametrize("value", [
    "../x",
    "2026-9",
    "2026-09/x",
    "1abcdefghijklmnop2",       # id-looking string
    "٢٠٢٦-٠٩",                    # Arabic-Indic (Unicode) digits -- must NOT match \d-style
    "",
    "x" * 1000,
    "2026-09 ",
    " 2026-09",
    "2026-090",
    "20260-9",
    None,
    123,
])
def test_invalid_subfolder_values_rejected(value):
    assert broker._valid_subfolder(value) is False


def test_subfolder_request_with_invalid_value_is_refused_before_any_drive_call(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail(*a, **kw):
        raise AssertionError("no Drive call should happen for an invalid subfolder")
    monkeypatch.setattr(ilag_sync, "upload", fail)
    monkeypatch.setattr(ilag_sync, "api", fail)
    monkeypatch.setattr(broker, "list_folder", fail)

    req = json.dumps({"op": "upload", "path": str(local), "subfolder": "../x"}).encode()
    result = broker.handle_request(req, cfg)

    assert result["ok"] is False
    assert "subfolder" in result["error"]


def test_missing_subfolder_uploads_into_fixed_folder_directly(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    seen_folder_ids = []
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: seen_folder_ids.append(folder_id) or {"id": "x"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"photo.jpg": local.stat().st_size})

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local)}).encode(), cfg)

    assert result["ok"] is True
    assert seen_folder_ids == [cfg.folder_id]


# --------------------------------------------------------------------------- month folder resolve-or-create

def test_month_folder_found_is_reused_not_recreated(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fake_api(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        if method == "GET":
            assert params["q"].startswith(f"'{cfg.folder_id}' in parents")
            assert "name = '2026-09'" in params["q"]
            return {"files": [{"id": "MONTH-FOLDER-ID", "name": "2026-09"}]}
        raise AssertionError("must not create a folder that was already found")

    monkeypatch.setattr(ilag_sync, "api", fake_api)
    seen_folder_ids = []
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: seen_folder_ids.append(folder_id) or {"id": "x"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"photo.jpg": local.stat().st_size})

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local), "subfolder": "2026-09"}).encode(), cfg)

    assert result["ok"] is True
    assert seen_folder_ids == ["MONTH-FOLDER-ID"]


def test_month_folder_absent_is_created_as_direct_child_of_fixed_folder(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    calls = []

    def fake_api(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        calls.append(method)
        if method == "GET":
            return {"files": []}
        body = json.loads(data.decode())
        assert body["name"] == "2026-09"
        assert body["parents"] == [cfg.folder_id]
        assert body["mimeType"] == "application/vnd.google-apps.folder"
        return {"id": "NEW-MONTH-FOLDER-ID", "name": "2026-09"}

    monkeypatch.setattr(ilag_sync, "api", fake_api)
    seen_folder_ids = []
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: seen_folder_ids.append(folder_id) or {"id": "x"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"photo.jpg": local.stat().st_size})

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local), "subfolder": "2026-09"}).encode(), cfg)

    assert result["ok"] is True
    assert calls == ["GET", "POST"]
    assert seen_folder_ids == ["NEW-MONTH-FOLDER-ID"]


def test_month_folder_creation_failure_is_reported_not_a_crash(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def raise_api(*a, **kw):
        raise OSError("Drive API unreachable")
    monkeypatch.setattr(ilag_sync, "api", raise_api)

    def fail_upload(*a, **kw):
        raise AssertionError("must not upload if the month folder could not be resolved")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local), "subfolder": "2026-09"}).encode(), cfg)

    assert result["ok"] is False


# --------------------------------------------------------------------------- 2. folder id / parent / destination ignored

def test_client_supplied_folder_id_in_any_field_is_ignored_not_used(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    seen_folder_ids = []

    def fake_upload(path, name, folder_id):
        seen_folder_ids.append(folder_id)
        return {"id": "new-id"}

    monkeypatch.setattr(ilag_sync, "upload", fake_upload)
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"photo.jpg": local.stat().st_size})

    req = json.dumps({
        "op": "upload", "path": str(local),
        "folder_id": "ATTACKER-CONTROLLED-FOLDER",
        "parent": "ALSO-ATTACKER-CONTROLLED",
        "destination": "STILL-ATTACKER-CONTROLLED",
    }).encode()

    result = broker.handle_request(req, cfg)

    assert result["ok"] is True
    assert seen_folder_ids == [cfg.folder_id]
    assert "ATTACKER-CONTROLLED-FOLDER" not in seen_folder_ids


def test_client_supplied_subfolder_cannot_smuggle_a_folder_id(monkeypatch, tmp_path):
    """subfolder must be a YYYY-MM value -- an attacker cannot pass a real
    Drive folder id (or anything id-shaped) through it."""
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail(*a, **kw):
        raise AssertionError("no Drive call for an id-shaped subfolder")
    monkeypatch.setattr(ilag_sync, "api", fail)
    monkeypatch.setattr(ilag_sync, "upload", fail)

    req = json.dumps({
        "op": "upload", "path": str(local), "subfolder": "1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy",
    }).encode()
    result = broker.handle_request(req, cfg)

    assert result["ok"] is False


# --------------------------------------------------------------------------- 3. op != upload refused / grep guard

@pytest.mark.parametrize("op", ["list", "download", "delete", "move", "rename", "read", None, "", "UPLOAD"])
def test_op_other_than_upload_is_refused(monkeypatch, tmp_path, op):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be called for a non-'upload' op")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    req = json.dumps({"op": op, "path": str(local)}).encode()
    result = broker.handle_request(req, cfg)

    assert result["ok"] is False
    assert "error" in result


def test_broker_source_has_no_delete_trash_move_or_arbitrary_list_drive_call():
    source = Path(broker.__file__).read_text()

    # Only "list_folder" is imported from ilag_mirror -- no walk_drive
    # (arbitrary recursive listing), no general-purpose ensure_folder.
    assert "from ilag_mirror import list_folder" in source
    assert "walk_drive" not in source
    assert "gdrive_move" not in source  # that module holds move/rename/trash

    # Not a blanket ban on the word "ensure_folder": this module's own
    # docstring explains, in prose, why it does NOT call ilag_sync's
    # general-purpose ensure_folder() -- that sentence would otherwise trip
    # this guard on itself (same reasoning the sibling broker's own guard
    # test gives for not blanket-banning the word "trash"). The actual call
    # is what's forbidden:
    forbidden_calls = [
        "ilag_sync.walk_drive(", "ilag_sync.ensure_folder(",
        "ilag_sync.append_log(", "ilag_sync.walk_local(",
        "from ilag_sync import ensure_folder",
    ]
    for token in forbidden_calls:
        assert token not in source, f"forbidden Drive call present: {token}"

    import re
    assert not re.search(r'method\s*=\s*["\']DELETE["\']', source)
    assert not re.search(r'["\']trashed["\']\s*:\s*[Tt]rue', source)
    assert not re.search(r'\.trash\(', source)
    assert not re.search(r'["\']op["\']\s*:\s*["\']trash["\']', source)

    # The only recognised "op" value compared against is "upload".
    op_comparisons = re.findall(r'get\(["\']op["\']\)\s*[!=]=\s*["\']([a-zA-Z_]+)["\']', source)
    assert set(op_comparisons) == {"upload"}, f"unexpected op comparisons found in source: {set(op_comparisons)}"


def test_only_recognised_drive_verbs_referenced_in_do_upload():
    """do_upload/resolve_or_create_month_folder only ever call
    ilag_sync.upload(...), list_folder(...), and ilag_sync.api(...) (used
    solely for the scoped month-folder find/create) -- asserted at the
    object level so an alias/rebind can't slip past the text guard above."""
    import inspect
    src = inspect.getsource(broker.do_upload) + inspect.getsource(broker.resolve_or_create_month_folder)
    assert "ilag_sync.upload(" in src
    assert "list_folder(" in src
    for verb in ("delete", "trash", "move", "rename", "permissions"):
        assert verb not in src.lower()


# --------------------------------------------------------------------------- 4. peer uid allowlist

def _round_trip(cfg: broker.BrokerConfig, logger: logging.Logger, request: dict,
                 startup_secrets: frozenset[str] = frozenset(), *, monkeypatch=None) -> dict:
    if monkeypatch is not None:
        monkeypatch.setattr(broker, "get_peer_uid", lambda conn: os.getuid())
    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_sock.bind(str(cfg.socket_path))
    server_sock.listen(1)
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect(str(cfg.socket_path))
        try:
            client.sendall((json.dumps(request) + "\n").encode())
            conn, _ = server_sock.accept()
            try:
                broker.handle_connection(conn, cfg, logger, startup_secrets)
            finally:
                conn.close()
            raw = b""
            while not raw.endswith(b"\n"):
                chunk = client.recv(4096)
                if not chunk:
                    break
                raw += chunk
            return json.loads(raw.decode())
        finally:
            client.close()
    finally:
        server_sock.close()
        cfg.socket_path.unlink(missing_ok=True)
        try:
            cfg.socket_path.parent.rmdir()
        except OSError:
            pass


def test_peer_uid_not_in_allowlist_is_refused_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, allowed_uids=frozenset({999999}))
    logger = logging.getLogger("test-photo-broker-uid-refused")

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be reached for an unauthorized peer")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    response = _round_trip(cfg, logger, {"op": "upload", "path": "/whatever"}, monkeypatch=monkeypatch)

    assert response["ok"] is False
    assert "not authorized" in response["error"]


def test_peer_uid_in_allowlist_is_accepted_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, allowed_uids=frozenset({os.getuid()}))
    local = _staged_file(cfg)
    logger = logging.getLogger("test-photo-broker-uid-accepted")

    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "ok-id"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"photo.jpg": local.stat().st_size})

    response = _round_trip(cfg, logger, {"op": "upload", "path": str(local)}, monkeypatch=monkeypatch)

    assert response["ok"] is True
    assert response["id"] == "ok-id"


# --------------------------------------------------------------------------- 5. oversize rejection

def test_file_over_size_cap_is_refused(tmp_path):
    cfg = _cfg(tmp_path, max_upload_bytes=100)
    big = _staged_file(cfg, size=200)
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(big)}).encode(), cfg)
    assert result["ok"] is False
    assert "too large" in result["error"]


def test_request_over_max_bytes_is_refused_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, max_request_bytes=32)
    logger = logging.getLogger("test-photo-broker-oversize-request")
    monkeypatch.setattr(broker, "get_peer_uid", lambda conn: os.getuid())

    huge_path = "/" + ("a" * 200)
    response = _round_trip(cfg, logger, {"op": "upload", "path": huge_path}, monkeypatch=monkeypatch)
    assert response["ok"] is False
    assert "exceeds max size" in response["error"]


# --------------------------------------------------------------------------- path safety (same discipline as the sibling broker)

def test_path_outside_staging_root_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"x" * 100)
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(outside)}).encode(), cfg)
    assert result["ok"] is False
    assert "staging root" in result["error"]


def test_symlink_inside_staging_root_resolving_outside_it_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    secret = tmp_path / "secretary-env-like-file"
    secret.write_bytes(b"GOOGLE_OAUTH_REFRESH_TOKEN=totally-real-secret")
    link = cfg.staging_root / "looks-like-a-photo.jpg"
    link.symlink_to(secret)
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(link)}).encode(), cfg)
    assert result["ok"] is False
    assert "staging root" in result["error"]


# --------------------------------------------------------------------------- verify-before-trust

def test_upload_succeeded_but_verify_listing_misses_file_is_failure(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "uploaded-id"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {})
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local)}).encode(), cfg)
    assert result["ok"] is False
    assert "verif" in result["error"].lower()


# --------------------------------------------------------------------------- credential never leaks

SECRET_TOKEN = "SECRET-PHOTO-REFRESH-TOKEN-abcdef1234567890"


def test_credential_never_appears_in_response_or_log_including_on_error_path(monkeypatch, tmp_path, caplog):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    logger = logging.getLogger("test-photo-broker-secret-leak")
    logger.addHandler(logging.NullHandler())

    def leaky_upload(path, name, folder_id):
        raise RuntimeError(f"upload failed, used token {SECRET_TOKEN} against {folder_id}")

    monkeypatch.setattr(ilag_sync, "upload", leaky_upload)
    monkeypatch.setattr(broker, "get_peer_uid", lambda conn: os.getuid())

    startup_secrets = frozenset({SECRET_TOKEN})
    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_sock.bind(str(cfg.socket_path))
    server_sock.listen(1)
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect(str(cfg.socket_path))
        try:
            client.sendall((json.dumps({"op": "upload", "path": str(local)}) + "\n").encode())
            conn, _ = server_sock.accept()
            with caplog.at_level(logging.DEBUG):
                try:
                    broker.handle_connection(conn, cfg, logger, startup_secrets)
                finally:
                    conn.close()
            raw = client.recv(65536)
        finally:
            client.close()
    finally:
        server_sock.close()
        cfg.socket_path.unlink(missing_ok=True)
        try:
            cfg.socket_path.parent.rmdir()
        except OSError:
            pass

    response_text = raw.decode()
    assert SECRET_TOKEN not in response_text
    response = json.loads(response_text)
    assert response["ok"] is False

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert SECRET_TOKEN not in log_text


# --------------------------------------------------------------------------- config validation

def test_load_config_requires_env_var(tmp_path):
    env = {"DRIVE_PHOTO_BROKER_STAGING_ROOT": str(tmp_path), "DRIVE_PHOTO_BROKER_ALLOWED_UIDS": "1001"}
    with pytest.raises(broker.ConfigError, match="DRIVE_PHOTO_BROKER_ENV"):
        broker.load_config(env)


def test_load_config_uses_defaults_for_optional_values(tmp_path):
    env = {
        "DRIVE_PHOTO_BROKER_ENV": str(tmp_path / "creds.env"),
        "DRIVE_PHOTO_BROKER_STAGING_ROOT": str(tmp_path),
        "DRIVE_PHOTO_BROKER_ALLOWED_UIDS": "1001,1002",
    }
    cfg = broker.load_config(env)
    assert cfg.allowed_uids == frozenset({1001, 1002})
    assert cfg.folder_id == broker.DEFAULT_FOLDER_ID
    assert cfg.folder_id == "1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy"
    assert cfg.max_upload_bytes == broker.DEFAULT_MAX_UPLOAD_BYTES
    assert cfg.max_upload_bytes == 200 * 1024 * 1024
    assert cfg.socket_path == Path(broker.DEFAULT_SOCKET_PATH)


def test_default_folder_and_socket_are_independent_of_the_sibling_broker():
    import runners.drive_upload_broker as sibling
    assert broker.DEFAULT_FOLDER_ID != sibling.DEFAULT_FOLDER_ID
    assert broker.DEFAULT_SOCKET_PATH != sibling.DEFAULT_SOCKET_PATH


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
