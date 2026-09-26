"""Tests for runners/drive_share_broker.py (task-1c07d46b, broker #3).

Sibling of scripts/test_drive_photo_broker.py -- same mocking idiom (a real
temp AF_UNIX socket where the wire protocol itself needs exercising,
`ilag_sync.upload` / `ilag_sync.api` monkeypatched at the broker module's own
names otherwise). Nothing here ever touches a real Drive service.

Covers (task's required list for this file):
  1. wrong uid refused
  2. a path outside staging refused, including symlink escape and ".."
  3. an unknown op refused
  4. an upload that goes elsewhere never happens (assert the parent id)
  5. the permission body is exactly anyone/reader
  6. the staged file is deleted on success and on failure
  7. verify failure gives ok:false

Plus: load_config() validation (including DRIVE_SHARE_MAX_MB), the
credential-redaction / verify-before-trust coverage the sibling brokers
have, the client-supplied-folder-id-is-ignored guard, and a grep-style
source guard confirming no delete/trash/move/list/read code path exists.
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
import runners.drive_share_broker as broker  # noqa: E402
import ilag_sync  # noqa: E402 -- same module object broker.py mutates ENV_CANDIDATES on


def _cfg(tmp_path, **overrides) -> broker.BrokerConfig:
    staging = tmp_path / "staging"
    staging.mkdir(exist_ok=True)
    defaults = dict(
        env_path=tmp_path / "creds.env",
        # tmp_path lives under a path routinely over macOS's ~104-byte
        # sockaddr_un limit -- socket-binding tests need a short path.
        socket_path=Path(tempfile.mkdtemp(dir="/tmp")) / "s.sock",
        allowed_uids=frozenset({os.getuid()}),
        staging_root=staging.resolve(),
        folder_id="FIXED-SHARE-FOLDER-ID",
        max_upload_bytes=1_000_000,
        max_request_bytes=65536,
        socket_timeout=5.0,
    )
    defaults.update(overrides)
    return broker.BrokerConfig(**defaults)


def _staged_file(cfg: broker.BrokerConfig, name: str = "report.pdf", size: int = 1024) -> Path:
    p = cfg.staging_root / name
    p.write_bytes(b"x" * size)
    return p


def _ok_drive(monkeypatch, *, file_id: str = "shared-id", link: str = "https://drive.google.com/file/d/shared-id/view",
              folder_id: str = "FIXED-SHARE-FOLDER-ID", size: int | None = None,
              permission_calls: list | None = None):
    """Wire up ilag_sync.upload/api so a whole share round-trip succeeds."""
    def fake_upload(path, name, dest_folder_id):
        return {"id": file_id}

    def fake_api(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        if url.endswith("/permissions"):
            if permission_calls is not None:
                permission_calls.append(json.loads(data.decode()))
            return {"id": "perm-1"}
        # the re-read call
        return {
            "id": file_id, "name": "report.pdf",
            "size": size, "parents": [folder_id], "webViewLink": link,
        }

    monkeypatch.setattr(ilag_sync, "upload", fake_upload)
    monkeypatch.setattr(ilag_sync, "api", fake_api)


# --------------------------------------------------------------------------- 1. wrong uid refused

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


def test_wrong_uid_is_refused_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, allowed_uids=frozenset({999999}))
    logger = logging.getLogger("test-share-broker-uid-refused")

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be reached for an unauthorized peer")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    response = _round_trip(cfg, logger, {"op": "share", "path": "/whatever", "name": "x.pdf"},
                            monkeypatch=monkeypatch)

    assert response["ok"] is False
    assert "not authorized" in response["error"]


def test_correct_uid_is_accepted_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, allowed_uids=frozenset({os.getuid()}))
    local = _staged_file(cfg)
    logger = logging.getLogger("test-share-broker-uid-accepted")
    _ok_drive(monkeypatch, size=local.stat().st_size)

    response = _round_trip(cfg, logger, {"op": "share", "path": str(local), "name": "report.pdf"},
                            monkeypatch=monkeypatch)

    assert response["ok"] is True
    assert response["id"] == "shared-id"
    assert response["link"] == "https://drive.google.com/file/d/shared-id/view"


def test_uid_zero_is_not_special_cased_as_always_allowed(monkeypatch, tmp_path):
    """The allowlist is the only source of truth. A broker configured
    without 0 must still refuse a uid-0 caller (mirrors the sibling
    broker's own uid-0-is-not-magic coverage)."""
    cfg = _cfg(tmp_path, allowed_uids=frozenset({1001}))
    logger = logging.getLogger("test-share-broker-uid0-not-hardcoded-allowed")

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be reached for an unauthorized peer")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)
    monkeypatch.setattr(broker, "get_peer_uid", lambda conn: 0)

    response = _round_trip(cfg, logger, {"op": "share", "path": "/whatever", "name": "x.pdf"})

    assert response["ok"] is False
    assert "not authorized" in response["error"]


# --------------------------------------------------------------------------- 2. path outside staging refused

def test_path_outside_staging_root_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"x" * 100)
    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(outside), "name": "outside.pdf"}).encode(), cfg)
    assert result["ok"] is False
    assert "staging root" in result["error"]
    assert outside.exists()  # never staged, never touched


def test_dotdot_path_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    secret_dir = tmp_path.parent / f"escape-{tmp_path.name}"
    secret_dir.mkdir(exist_ok=True)
    secret = secret_dir / "not-yours.pdf"
    secret.write_bytes(b"x" * 100)
    dotdot_path = str(cfg.staging_root / ".." / ".." / secret_dir.name / "not-yours.pdf")
    result = broker.handle_request(
        json.dumps({"op": "share", "path": dotdot_path, "name": "x.pdf"}).encode(), cfg)
    assert result["ok"] is False
    assert "staging root" in result["error"]


def test_symlink_inside_staging_root_resolving_outside_it_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    secret = tmp_path / "sompong-env-like-file"
    secret.write_bytes(b"GOOGLE_OAUTH_REFRESH_TOKEN=totally-real-secret")
    link = cfg.staging_root / "looks-like-a-report.pdf"
    link.symlink_to(secret)
    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(link), "name": "report.pdf"}).encode(), cfg)
    assert result["ok"] is False
    assert "staging root" in result["error"]
    assert secret.exists()  # never touched, let alone deleted


def test_relative_path_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    result = broker.handle_request(
        json.dumps({"op": "share", "path": "relative/report.pdf", "name": "report.pdf"}).encode(), cfg)
    assert result["ok"] is False
    assert "absolute" in result["error"]


def test_nonexistent_path_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    missing = cfg.staging_root / "never-written.pdf"
    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(missing), "name": "report.pdf"}).encode(), cfg)
    assert result["ok"] is False


# --------------------------------------------------------------------------- 3. unknown op refused

@pytest.mark.parametrize("op", ["list", "download", "delete", "move", "rename", "read", "upload", None, "", "SHARE"])
def test_op_other_than_share_is_refused(monkeypatch, tmp_path, op):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be called for a non-'share' op")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    req = json.dumps({"op": op, "path": str(local), "name": "report.pdf"}).encode()
    result = broker.handle_request(req, cfg)

    assert result["ok"] is False
    assert "error" in result
    assert local.exists()  # refused before touching the staged file at all


def test_missing_name_is_refused(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be called when 'name' is missing")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local)}).encode(), cfg)
    assert result["ok"] is False
    assert "name" in result["error"]


def test_name_with_path_separator_is_refused(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be called for an unsafe name")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "../escape.pdf"}).encode(), cfg)
    assert result["ok"] is False


def test_broker_source_has_no_delete_trash_move_or_arbitrary_list_drive_call():
    source = Path(broker.__file__).read_text()

    forbidden_calls = [
        "ilag_sync.walk_drive(", "ilag_sync.ensure_folder(",
        "ilag_sync.append_log(", "ilag_sync.walk_local(",
        "from ilag_sync import ensure_folder", "from ilag_mirror import",
    ]
    for token in forbidden_calls:
        assert token not in source, f"forbidden Drive call present: {token}"

    import re
    assert not re.search(r'method\s*=\s*["\']DELETE["\']', source)
    assert not re.search(r'["\']trashed["\']\s*:\s*[Tt]rue', source)
    assert not re.search(r'\.trash\(', source)
    assert not re.search(r'["\']op["\']\s*:\s*["\']trash["\']', source)

    # The only recognised "op" value compared against is "share".
    op_comparisons = re.findall(r'get\(["\']op["\']\)\s*[!=]=\s*["\']([a-zA-Z_]+)["\']', source)
    assert set(op_comparisons) == {"share"}, f"unexpected op comparisons found in source: {set(op_comparisons)}"


def test_only_recognised_drive_verbs_referenced_in_do_share():
    """do_share/verify_shared_file/set_public_reader_permission only ever
    call ilag_sync.upload(...) and ilag_sync.api(...) (used for the
    permission POST and the re-read GET) -- asserted at the object level so
    an alias/rebind can't slip past the text guard above."""
    import inspect
    src = (inspect.getsource(broker.do_share) + inspect.getsource(broker.verify_shared_file)
           + inspect.getsource(broker.set_public_reader_permission))
    assert "ilag_sync.upload(" in src
    assert "ilag_sync.api(" in src
    for verb in ("delete", "trash", "move", "rename"):
        assert verb not in src.lower()


# --------------------------------------------------------------------------- 4. upload never goes elsewhere (parent id)

def test_client_supplied_folder_id_in_any_field_is_ignored_not_used(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    seen_folder_ids = []

    def fake_upload(path, name, folder_id):
        seen_folder_ids.append(folder_id)
        return {"id": "new-id"}

    def fake_api(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        if url.endswith("/permissions"):
            return {"id": "perm-1"}
        return {"id": "new-id", "size": local.stat().st_size, "parents": [cfg.folder_id],
                "webViewLink": "https://drive.google.com/file/d/new-id/view"}

    monkeypatch.setattr(ilag_sync, "upload", fake_upload)
    monkeypatch.setattr(ilag_sync, "api", fake_api)

    req = json.dumps({
        "op": "share", "path": str(local), "name": "report.pdf",
        "folder_id": "ATTACKER-CONTROLLED-FOLDER",
        "parent": "ALSO-ATTACKER-CONTROLLED",
        "destination": "STILL-ATTACKER-CONTROLLED",
    }).encode()

    result = broker.handle_request(req, cfg)

    assert result["ok"] is True
    assert seen_folder_ids == [cfg.folder_id]
    assert "ATTACKER-CONTROLLED-FOLDER" not in seen_folder_ids


def test_upload_always_targets_the_fixed_folder_id(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, folder_id="THE-ONE-FIXED-FOLDER")
    local = _staged_file(cfg)
    seen_folder_ids = []

    def fake_upload(path, name, folder_id):
        seen_folder_ids.append(folder_id)
        return {"id": "id-1"}

    _ok_drive(monkeypatch, file_id="id-1", folder_id="THE-ONE-FIXED-FOLDER", size=local.stat().st_size)
    monkeypatch.setattr(ilag_sync, "upload", fake_upload)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is True
    assert seen_folder_ids == ["THE-ONE-FIXED-FOLDER"]


# --------------------------------------------------------------------------- 5. permission body is exactly anyone/reader

def test_permission_body_is_exactly_anyone_reader(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    permission_calls: list = []
    _ok_drive(monkeypatch, size=local.stat().st_size, permission_calls=permission_calls)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is True
    assert permission_calls == [{"type": "anyone", "role": "reader"}]


def test_exactly_one_permission_call_is_made(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    permission_calls: list = []
    _ok_drive(monkeypatch, size=local.stat().st_size, permission_calls=permission_calls)

    broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert len(permission_calls) == 1


def test_permission_failure_gives_ok_false_and_never_reports_a_link(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "id-1"})

    def raise_on_permission(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        raise OSError("Drive API unreachable")
    monkeypatch.setattr(ilag_sync, "api", raise_on_permission)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert "link" not in result


# --------------------------------------------------------------------------- 6. staged file deleted on success and on failure

def test_staged_file_is_deleted_after_a_successful_share(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    _ok_drive(monkeypatch, size=local.stat().st_size)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is True
    assert not local.exists()


def test_staged_file_is_deleted_after_upload_failure(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail_upload(*a, **kw):
        raise RuntimeError("upload failed")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert not local.exists()


def test_staged_file_is_deleted_after_permission_failure(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "id-1"})

    def raise_on_permission(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        raise OSError("Drive API unreachable")
    monkeypatch.setattr(ilag_sync, "api", raise_on_permission)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert not local.exists()


def test_staged_file_is_deleted_after_verify_failure(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    _ok_drive(monkeypatch, size=999999999)  # wrong size -> verify fails

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert not local.exists()


def test_refused_request_before_a_path_is_resolved_never_touches_any_file(monkeypatch, tmp_path):
    """An op other than 'share' is refused before resolve_staged_path() even
    runs -- there is no staged path to delete, and nothing in the staging
    root is touched."""
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def fail_upload(*a, **kw):
        raise AssertionError("must not be called")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    result = broker.handle_request(
        json.dumps({"op": "list", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert local.exists()


# --------------------------------------------------------------------------- 7. verify failure gives ok:false

def test_verify_fails_on_size_mismatch(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    _ok_drive(monkeypatch, size=local.stat().st_size + 1)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert "size" in result["error"].lower()


def test_verify_fails_on_wrong_parent(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, folder_id="FIXED-SHARE-FOLDER-ID")
    local = _staged_file(cfg)
    _ok_drive(monkeypatch, folder_id="SOME-OTHER-FOLDER-ENTIRELY", size=local.stat().st_size)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert "parent" in result["error"].lower()


def test_verify_fails_when_webviewlink_missing(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    _ok_drive(monkeypatch, size=local.stat().st_size, link=None)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False


def test_verify_fails_when_reread_raises(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "id-1"})

    calls = {"n": 0}

    def flaky_api(url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        calls["n"] += 1
        if url.endswith("/permissions"):
            return {"id": "perm-1"}
        raise OSError("Drive API unreachable on re-read")
    monkeypatch.setattr(ilag_sync, "api", flaky_api)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)

    assert result["ok"] is False
    assert "verif" in result["error"].lower()


def test_upload_response_missing_id_is_a_failure(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {})

    def fail_api(*a, **kw):
        raise AssertionError("must not call the Drive API without a file id")
    monkeypatch.setattr(ilag_sync, "api", fail_api)

    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}).encode(), cfg)
    assert result["ok"] is False


# --------------------------------------------------------------------------- oversize rejection

def test_file_over_size_cap_is_refused(tmp_path):
    cfg = _cfg(tmp_path, max_upload_bytes=100)
    big = _staged_file(cfg, size=200)
    result = broker.handle_request(
        json.dumps({"op": "share", "path": str(big), "name": "big.pdf"}).encode(), cfg)
    assert result["ok"] is False
    assert "too large" in result["error"]


def test_request_over_max_bytes_is_refused_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, max_request_bytes=32)
    logger = logging.getLogger("test-share-broker-oversize-request")
    monkeypatch.setattr(broker, "get_peer_uid", lambda conn: os.getuid())

    huge_path = "/" + ("a" * 200)
    response = _round_trip(cfg, logger, {"op": "share", "path": huge_path, "name": "x.pdf"}, monkeypatch=monkeypatch)
    assert response["ok"] is False
    assert "exceeds max size" in response["error"]


# --------------------------------------------------------------------------- credential never leaks

SECRET_TOKEN = "SECRET-SHARE-REFRESH-TOKEN-abcdef1234567890"


def test_credential_never_appears_in_response_or_log_including_on_error_path(monkeypatch, tmp_path, caplog):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    logger = logging.getLogger("test-share-broker-secret-leak")
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
            client.sendall((json.dumps({"op": "share", "path": str(local), "name": "report.pdf"}) + "\n").encode())
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


def test_log_never_contains_the_display_name_or_staged_path(monkeypatch, tmp_path, caplog):
    """Task instruction: log a reason only, never a filename or file
    content. Names both a very distinctive display name and confirms it
    never lands in a log record on the success path."""
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg, name="extremely-distinctive-display-name.pdf")
    logger = logging.getLogger("test-share-broker-no-filename-in-log")
    logger.addHandler(logging.NullHandler())
    monkeypatch.setattr(broker, "get_peer_uid", lambda conn: os.getuid())
    _ok_drive(monkeypatch, size=local.stat().st_size)

    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_sock.bind(str(cfg.socket_path))
    server_sock.listen(1)
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect(str(cfg.socket_path))
        try:
            req = {"op": "share", "path": str(local), "name": "extremely-distinctive-display-name.pdf"}
            client.sendall((json.dumps(req) + "\n").encode())
            conn, _ = server_sock.accept()
            with caplog.at_level(logging.DEBUG):
                try:
                    broker.handle_connection(conn, cfg, logger, frozenset())
                finally:
                    conn.close()
            client.recv(65536)
        finally:
            client.close()
    finally:
        server_sock.close()
        cfg.socket_path.unlink(missing_ok=True)
        try:
            cfg.socket_path.parent.rmdir()
        except OSError:
            pass

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "extremely-distinctive-display-name" not in log_text
    assert str(local) not in log_text


# --------------------------------------------------------------------------- config validation

def test_load_config_requires_env_var(tmp_path):
    env = {"DRIVE_SHARE_BROKER_STAGING_ROOT": str(tmp_path), "DRIVE_SHARE_BROKER_ALLOWED_UIDS": "1001"}
    with pytest.raises(broker.ConfigError, match="DRIVE_SHARE_BROKER_ENV"):
        broker.load_config(env)


def test_load_config_requires_staging_root(tmp_path):
    env = {"DRIVE_SHARE_BROKER_ENV": str(tmp_path / "creds.env"), "DRIVE_SHARE_BROKER_ALLOWED_UIDS": "1001"}
    with pytest.raises(broker.ConfigError, match="DRIVE_SHARE_BROKER_STAGING_ROOT"):
        broker.load_config(env)


def test_load_config_requires_allowed_uids(tmp_path):
    env = {"DRIVE_SHARE_BROKER_ENV": str(tmp_path / "creds.env"), "DRIVE_SHARE_BROKER_STAGING_ROOT": str(tmp_path)}
    with pytest.raises(broker.ConfigError, match="DRIVE_SHARE_BROKER_ALLOWED_UIDS"):
        broker.load_config(env)


def test_load_config_uses_defaults_for_optional_values(tmp_path):
    env = {
        "DRIVE_SHARE_BROKER_ENV": str(tmp_path / "creds.env"),
        "DRIVE_SHARE_BROKER_STAGING_ROOT": str(tmp_path),
        "DRIVE_SHARE_BROKER_ALLOWED_UIDS": "1001,1002",
    }
    cfg = broker.load_config(env)
    assert cfg.allowed_uids == frozenset({1001, 1002})
    assert cfg.folder_id == broker.DEFAULT_FOLDER_ID
    assert cfg.folder_id == "1Qn7B0e6Pa7y8gS5bjUfs-f5ewMIERUsR"
    assert cfg.max_upload_bytes == broker.DEFAULT_MAX_MB * 1024 * 1024
    assert cfg.max_upload_bytes == 300 * 1024 * 1024
    assert cfg.socket_path == Path(broker.DEFAULT_SOCKET_PATH)
    assert cfg.socket_path == Path("/run/mooniex-share-broker/broker.sock")


def test_load_config_reads_drive_share_max_mb(tmp_path):
    env = {
        "DRIVE_SHARE_BROKER_ENV": str(tmp_path / "creds.env"),
        "DRIVE_SHARE_BROKER_STAGING_ROOT": str(tmp_path),
        "DRIVE_SHARE_BROKER_ALLOWED_UIDS": "1001",
        "DRIVE_SHARE_MAX_MB": "5",
    }
    cfg = broker.load_config(env)
    assert cfg.max_upload_bytes == 5 * 1024 * 1024


def test_load_config_rejects_non_positive_max_mb(tmp_path):
    env = {
        "DRIVE_SHARE_BROKER_ENV": str(tmp_path / "creds.env"),
        "DRIVE_SHARE_BROKER_STAGING_ROOT": str(tmp_path),
        "DRIVE_SHARE_BROKER_ALLOWED_UIDS": "1001",
        "DRIVE_SHARE_MAX_MB": "0",
    }
    with pytest.raises(broker.ConfigError, match="DRIVE_SHARE_MAX_MB"):
        broker.load_config(env)


def test_default_folder_and_socket_are_independent_of_the_sibling_brokers():
    import runners.drive_upload_broker as sibling_upload
    import runners.drive_photo_broker as sibling_photo
    assert broker.DEFAULT_FOLDER_ID not in (sibling_upload.DEFAULT_FOLDER_ID, sibling_photo.DEFAULT_FOLDER_ID)
    assert broker.DEFAULT_SOCKET_PATH not in (sibling_upload.DEFAULT_SOCKET_PATH, sibling_photo.DEFAULT_SOCKET_PATH)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
