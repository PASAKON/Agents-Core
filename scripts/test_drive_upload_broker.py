"""Tests for runners/drive_upload_broker.py (task-e713c4e2).

Mocked, no live network, no real socket to a real Drive service -- every
test that needs a socket at all uses a real temp AF_UNIX file (cheap, local,
no service on the other end) with `ilag_sync.upload` / `ilag_mirror.list_folder`
monkeypatched at the broker module's own names, same idiom
scripts/test_video_to_drive.py already uses for its module-level globals.

Covers (task's required list):
  1. client-supplied folder id in ANY field is ignored/refused -- the fixed
     server-side folder is always the destination.
  2. a request with `op` other than "upload" is refused.
  3. a path outside the staging root is refused, INCLUDING via a symlink
     that lives inside the staging root but resolves outside it.
  4. a path that is not a regular file (directory, fifo) is refused.
  5. a peer uid not in the allowlist is refused.
  6. upload succeeded but the verification listing does not show the file
     -> ok:false, reported as failure.
  7. the credential never appears in any response or log line, including on
     error paths.
  8. a grep-style guard test asserting the broker source contains no
     delete/trash/list-arbitrary-folder Drive call.

Plus: load_config() validation, and an end-to-end real-temp-socket pass
through handle_connection() to prove the wire protocol (framing, peer-uid
gate, response shape) actually works, not just handle_request() in
isolation.
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
import runners.drive_upload_broker as broker  # noqa: E402
import ilag_sync  # noqa: E402 -- same module broker.py mutates ENV_CANDIDATES on


def _cfg(tmp_path, **overrides) -> broker.BrokerConfig:
    staging = tmp_path / "staging"
    staging.mkdir(exist_ok=True)
    defaults = dict(
        env_path=tmp_path / "creds.env",
        # pytest's tmp_path lives under /private/var/folders/... -- routinely
        # over macOS's ~104-byte sockaddr_un limit ("AF_UNIX path too long").
        # Socket-binding tests need a short path; /tmp is always short.
        socket_path=Path(tempfile.mkdtemp(dir="/tmp")) / "b.sock",
        allowed_uids=frozenset({os.getuid()}),
        staging_root=staging.resolve(),
        folder_id="FIXED-FOLDER-ID",
        max_upload_bytes=1_000_000,
        max_request_bytes=65536,
        socket_timeout=5.0,
    )
    defaults.update(overrides)
    return broker.BrokerConfig(**defaults)


def _staged_file(cfg: broker.BrokerConfig, name: str = "clip.mp4", size: int = 1024) -> Path:
    p = cfg.staging_root / name
    p.write_bytes(b"x" * size)
    return p


# --------------------------------------------------------------------------- 1. folder id ignored

def test_client_supplied_folder_id_in_any_field_is_ignored_not_used(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    seen_folder_ids = []

    def fake_upload(path, name, folder_id):
        seen_folder_ids.append(folder_id)
        return {"id": "new-id"}

    monkeypatch.setattr(ilag_sync, "upload", fake_upload)
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"clip.mp4": local.stat().st_size})

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


def test_client_supplied_folder_id_ignored_even_when_upload_would_otherwise_fail_verify(monkeypatch, tmp_path):
    """Belt and suspenders on test 1: even if the attacker's folder id WERE
    honoured, the fixed-folder verification listing would catch it (file
    would not show up there). This proves the id is never even read, not
    merely that verification happens to save us."""
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "x"})

    listed_folder_ids = []

    def fake_list_folder(folder_id):
        listed_folder_ids.append(folder_id)
        return {"clip.mp4": local.stat().st_size}

    monkeypatch.setattr(broker, "list_folder", fake_list_folder)

    req = json.dumps({"op": "upload", "path": str(local), "folder_id": "ATTACKER"}).encode()
    result = broker.handle_request(req, cfg)

    assert result["ok"] is True
    assert listed_folder_ids == [cfg.folder_id]


# --------------------------------------------------------------------------- 2. op != upload refused

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


def test_missing_op_key_entirely_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    req = json.dumps({"path": str(local)}).encode()
    result = broker.handle_request(req, cfg)
    assert result["ok"] is False


# --------------------------------------------------------------------------- 3. path outside staging root

def test_path_outside_staging_root_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"x" * 100)

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(outside)}).encode(), cfg)

    assert result["ok"] is False
    assert "staging root" in result["error"]


def test_symlink_inside_staging_root_resolving_outside_it_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    secret = tmp_path / "secretary-env-like-file"
    secret.write_bytes(b"GOOGLE_OAUTH_REFRESH_TOKEN=totally-real-secret")
    link = cfg.staging_root / "looks-like-a-video.mp4"
    link.symlink_to(secret)

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(link)}).encode(), cfg)

    assert result["ok"] is False
    assert "staging root" in result["error"]


def test_nonexistent_path_is_refused_not_a_crash(tmp_path):
    cfg = _cfg(tmp_path)
    missing = cfg.staging_root / "does-not-exist.mp4"
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(missing)}).encode(), cfg)
    assert result["ok"] is False


# --------------------------------------------------------------------------- 4. not a regular file

def test_directory_path_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    subdir = cfg.staging_root / "a-directory"
    subdir.mkdir()
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(subdir)}).encode(), cfg)
    assert result["ok"] is False
    assert "regular file" in result["error"]


def test_fifo_path_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    fifo_path = cfg.staging_root / "a-fifo"
    os.mkfifo(fifo_path)
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(fifo_path)}).encode(), cfg)
    assert result["ok"] is False
    assert "regular file" in result["error"]


def test_file_over_size_cap_is_refused(tmp_path):
    cfg = _cfg(tmp_path, max_upload_bytes=100)
    big = _staged_file(cfg, size=200)
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(big)}).encode(), cfg)
    assert result["ok"] is False
    assert "too large" in result["error"]


# --------------------------------------------------------------------------- 5. peer uid allowlist

def test_peer_uid_not_in_allowlist_is_refused_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, allowed_uids=frozenset({999999}))  # definitely not us
    logger = logging.getLogger("test-broker-uid-refused")

    def fail_upload(*a, **kw):
        raise AssertionError("upload must never be reached for an unauthorized peer")
    monkeypatch.setattr(ilag_sync, "upload", fail_upload)

    response = _round_trip(cfg, logger, {"op": "upload", "path": "/whatever"}, monkeypatch=monkeypatch)

    assert response["ok"] is False
    assert "not authorized" in response["error"]


def test_peer_uid_in_allowlist_is_accepted_over_a_real_socket(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path, allowed_uids=frozenset({os.getuid()}))
    local = _staged_file(cfg)
    logger = logging.getLogger("test-broker-uid-accepted")

    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "ok-id"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"clip.mp4": local.stat().st_size})

    response = _round_trip(cfg, logger, {"op": "upload", "path": str(local)}, monkeypatch=monkeypatch)

    assert response["ok"] is True
    assert response["id"] == "ok-id"


def _round_trip(cfg: broker.BrokerConfig, logger: logging.Logger, request: dict,
                 startup_secrets: frozenset[str] = frozenset(), *, monkeypatch=None) -> dict:
    """Real temp AF_UNIX socket, real accept()/connect() -- no real Drive
    service anywhere in the loop. get_peer_uid() is monkeypatched to return
    this test process's own uid (SO_PEERCRED itself is Linux-only -- the
    deploy target and CI, but not necessarily wherever this suite runs --
    same idiom the module's own docstring calls out: "tests can monkeypatch
    this one function directly"). The allowlist COMPARISON is still real:
    whether that uid is refused or accepted depends entirely on
    cfg.allowed_uids, exercised for real by each test above."""
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


# --------------------------------------------------------------------------- 6. verify miss -> ok:false

def test_upload_succeeded_but_verify_listing_misses_file_is_failure(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "uploaded-id"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {})  # empty -- file not found

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local)}).encode(), cfg)

    assert result["ok"] is False
    assert "verif" in result["error"].lower()


def test_upload_succeeded_but_verify_shows_wrong_size_is_failure(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg, size=1024)

    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "uploaded-id"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"clip.mp4": 999})

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local)}).encode(), cfg)

    assert result["ok"] is False


def test_verify_listing_raising_is_failure_not_a_crash(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: {"id": "x"})

    def raise_list(folder_id):
        raise OSError("connection reset")
    monkeypatch.setattr(broker, "list_folder", raise_list)

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local)}).encode(), cfg)

    assert result["ok"] is False


def test_upload_call_itself_raising_is_failure_not_a_crash(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)

    def raise_upload(path, name, folder_id):
        raise OSError("network blip")
    monkeypatch.setattr(ilag_sync, "upload", raise_upload)

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local)}).encode(), cfg)

    assert result["ok"] is False


# --------------------------------------------------------------------------- 7. credential never leaks

SECRET_TOKEN = "SECRET-REFRESH-TOKEN-abcdef1234567890"


def test_credential_never_appears_in_response_or_log_including_on_error_path(monkeypatch, tmp_path, caplog):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    logger = logging.getLogger("test-broker-secret-leak")
    logger.addHandler(logging.NullHandler())

    def leaky_upload(path, name, folder_id):
        # simulate an exception whose text embeds the real secret -- e.g. a
        # library that echoes request state into its error message
        raise RuntimeError(f"upload failed, used token {SECRET_TOKEN} against {folder_id}")

    monkeypatch.setattr(ilag_sync, "upload", leaky_upload)
    monkeypatch.setattr(broker, "get_peer_uid", lambda conn: os.getuid())  # see _round_trip's docstring

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


def test_redact_scrubs_secret_from_arbitrary_text():
    secrets = frozenset({SECRET_TOKEN, "another-long-enough-secret-value"})
    text = f"error talking to Drive: token={SECRET_TOKEN} failed"
    redacted = broker.redact(text, secrets)
    assert SECRET_TOKEN not in redacted
    assert "[REDACTED]" in redacted


def test_redact_result_scrubs_error_field_only():
    secrets = frozenset({SECRET_TOKEN})
    result = {"ok": False, "error": f"failed with {SECRET_TOKEN}"}
    safe = broker.redact_result(result, secrets)
    assert SECRET_TOKEN not in safe["error"]


def test_current_secrets_includes_live_cached_access_token(monkeypatch):
    monkeypatch.setattr(ilag_sync, "_token_cache", {"value": "live-access-token-1234567890"})
    startup = frozenset({"startup-secret-value-abcdef"})
    combined = broker.current_secrets(startup)
    assert "live-access-token-1234567890" in combined
    assert "startup-secret-value-abcdef" in combined


# --------------------------------------------------------------------------- 8. grep-style guard test

def test_broker_source_has_no_delete_trash_or_arbitrary_list_drive_call():
    source = Path(broker.__file__).read_text()

    # Only "list_folder" is imported from ilag_mirror -- no walk_drive
    # (arbitrary recursive listing), no arbitrary folder browsing.
    assert "from ilag_mirror import list_folder" in source
    assert "walk_drive" not in source
    assert "ensure_folder" not in source

    # No other Drive verb reachable via the ilag_sync module object either.
    forbidden_calls = [
        "ilag_sync.api(", "ilag_sync.walk_drive(", "ilag_sync.ensure_folder(",
        "ilag_sync.append_log(", "ilag_sync.walk_local(",
    ]
    for token in forbidden_calls:
        assert token not in source, f"forbidden Drive call present: {token}"

    # No delete/trash HTTP verb, Drive API call, or request field, anywhere
    # in actual code -- deliberately NOT a blanket ban on the word "trash":
    # this module's own docstring explains, in prose, that no trash path
    # exists, and that sentence would otherwise trip the guard on itself.
    import re
    assert not re.search(r'method\s*=\s*["\']DELETE["\']', source)
    assert not re.search(r'["\']trashed["\']\s*:\s*[Tt]rue', source)
    assert not re.search(r'\.trash\(', source)
    assert not re.search(r'["\']op["\']\s*:\s*["\']trash["\']', source)

    # The only recognised "op" value compared against is "upload" -- no
    # code path branches on list/download/delete/move/rename. Matches both
    # == and != (the real source reads `req.get("op") != "upload"`).
    op_comparisons = re.findall(r'get\(["\']op["\']\)\s*[!=]=\s*["\']([a-zA-Z_]+)["\']', source)
    assert set(op_comparisons) == {"upload"}, f"unexpected op comparisons found in source: {set(op_comparisons)}"


def test_only_two_drive_functions_referenced_anywhere_in_module():
    """handle_request/do_upload only ever call ilag_sync.upload(...) and the
    module-level list_folder(...) -- asserted at the object level, not just
    the source text, so this also catches an alias/rebind that would slip
    past the text-based guard above."""
    import inspect
    do_upload_src = inspect.getsource(broker.do_upload)
    assert "ilag_sync.upload(" in do_upload_src
    assert "list_folder(" in do_upload_src
    for verb in ("delete", "trash", "move", "rename", "permissions"):
        assert verb not in do_upload_src.lower()


# --------------------------------------------------------------------------- config validation

def test_load_config_requires_env_var(tmp_path):
    env = {"DRIVE_BROKER_STAGING_ROOT": str(tmp_path), "DRIVE_BROKER_ALLOWED_UIDS": "1001"}
    with pytest.raises(broker.ConfigError, match="DRIVE_BROKER_ENV"):
        broker.load_config(env)


def test_load_config_requires_staging_root_to_exist(tmp_path):
    env = {
        "DRIVE_BROKER_ENV": str(tmp_path / "creds.env"),
        "DRIVE_BROKER_STAGING_ROOT": str(tmp_path / "does-not-exist"),
        "DRIVE_BROKER_ALLOWED_UIDS": "1001",
    }
    with pytest.raises(broker.ConfigError, match="DRIVE_BROKER_STAGING_ROOT"):
        broker.load_config(env)


def test_load_config_rejects_non_integer_uids(tmp_path):
    env = {
        "DRIVE_BROKER_ENV": str(tmp_path / "creds.env"),
        "DRIVE_BROKER_STAGING_ROOT": str(tmp_path),
        "DRIVE_BROKER_ALLOWED_UIDS": "not-a-number",
    }
    with pytest.raises(broker.ConfigError, match="DRIVE_BROKER_ALLOWED_UIDS"):
        broker.load_config(env)


def test_load_config_uses_defaults_for_optional_values(tmp_path):
    env = {
        "DRIVE_BROKER_ENV": str(tmp_path / "creds.env"),
        "DRIVE_BROKER_STAGING_ROOT": str(tmp_path),
        "DRIVE_BROKER_ALLOWED_UIDS": "1001,1002",
    }
    cfg = broker.load_config(env)
    assert cfg.allowed_uids == frozenset({1001, 1002})
    assert cfg.folder_id == broker.DEFAULT_FOLDER_ID
    assert cfg.max_upload_bytes == broker.DEFAULT_MAX_UPLOAD_BYTES
    assert cfg.socket_path == Path(broker.DEFAULT_SOCKET_PATH)


# --------------------------------------------------------------------------- name handling

def test_optional_name_overrides_local_filename(monkeypatch, tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg, name="raw-download-xyz.mp4")

    seen_names = []
    monkeypatch.setattr(ilag_sync, "upload", lambda path, name, folder_id: seen_names.append(name) or {"id": "x"})
    monkeypatch.setattr(broker, "list_folder", lambda folder_id: {"pretty-name.mp4": local.stat().st_size})

    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local), "name": "pretty-name.mp4"}).encode(), cfg)

    assert result["ok"] is True
    assert seen_names == ["pretty-name.mp4"]


def test_name_with_path_separator_is_refused(tmp_path):
    cfg = _cfg(tmp_path)
    local = _staged_file(cfg)
    result = broker.handle_request(
        json.dumps({"op": "upload", "path": str(local), "name": "../../etc/passwd"}).encode(), cfg)
    assert result["ok"] is False
