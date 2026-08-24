#!/usr/bin/env python3
"""Drive upload broker -- the ONLY thing on the box that ever reads the
Drive OAuth credential (task-e713c4e2, CEO order: "เจาะระบบ SomPong ยากขึ้น
1 Step").

Why this exists: giving SomPong (running on Contabo as user `secretary`,
which has no sudo -- `sudo -l -U secretary` -> "not allowed to run sudo", so
a setuid/sudo shim is not available here) the Drive OAuth refresh token
directly would give anyone who compromises that account read/download/
DELETE over the CEO's entire Google Drive. This daemon runs as its own
system user (`driveup`) and holds the credential instead. `secretary` talks
to it over a group-gated unix socket and can ask for exactly one thing:
upload a staged file into ONE fixed folder. Containment goal (the test of
whether this held): an attacker with full control of `secretary` can upload
files into that one folder and can do nothing else to the CEO's Drive --
cannot read it, cannot list it, cannot delete from it, cannot obtain the
token.

Three properties make that true, all enforced here, not by config:
  1. The destination folder id is fixed from THIS PROCESS's own config
     (DRIVE_BROKER_FOLDER_ID / DEFAULT_FOLDER_ID below) and is never read
     from a client request, under any key. handle_request() only ever reads
     "op", "path", "name" off the request object -- an attacker-supplied
     "folder_id"/"parent"/"destination" key is simply never looked at.
  2. Exactly one operation exists ("upload"). There is no list, read,
     download, move, rename, or trash-arbitrary-file code path in this
     module at all -- see test_drive_upload_broker.py's grep-style guard
     test. The only two Drive calls this module ever makes are
     ilag_sync.upload() (write the new file) and ilag_mirror.list_folder()
     against the fixed folder id (to verify the upload actually landed --
     scripts/video_to_drive.py already established this "never trust the
     upload call's own 200, re-list before saying ok" pattern; reused
     as-is, not reimplemented).
  3. Caller identity is checked via SO_PEERCRED against an explicit uid
     allowlist, and every path is resolved (symlinks followed) and checked
     against a configured staging root AFTER resolution -- same shape as
     the SSRF guard in lib/link_reader.py's check_url_safe() ("resolve
     first, then check"), so a symlink that lives inside the staging root
     but points outside it (e.g. at /home/secretary/.secretary.env or
     /etc/shadow) is rejected, not followed.

The credential is never logged, echoed, or returned -- not on error paths
either (_redact() scrubs every secret value + the live-cached access token
out of every log line and every response, unconditionally; see
test_credential_never_appears_in_response_or_log_including_on_error_path).

Protocol -- one JSON line in, one JSON line out, over
DRIVE_BROKER_SOCKET_PATH:
    request:  {"op": "upload", "path": "<abs path>", "name": "<optional>"}
    response: {"ok": true, "id", "name", "link", "size"}
           or {"ok": false, "error": "<reason>"}

Config, all via environment (set by scripts/install-drive-broker.sh's
systemd unit, never by this code):
    DRIVE_BROKER_ENV             path to a file readable only by `driveup`
                                  holding GOOGLE_OAUTH_CLIENT_ID/SECRET/
                                  REFRESH_TOKEN (required)
    DRIVE_BROKER_STAGING_ROOT    the only directory tree uploadable paths
                                  may resolve into (required)
    DRIVE_BROKER_ALLOWED_UIDS    comma-separated uid(s) permitted to call in
                                  (required) -- in production, `secretary`'s
                                  uid only
    DRIVE_BROKER_SOCKET_PATH     unix socket to listen on
                                  (default: /run/driveup/drive-broker.sock)
    DRIVE_BROKER_FOLDER_ID       the fixed destination folder (default: the
                                  CEO's Desktop Cloud root, same id
                                  scripts/video_to_drive.py's
                                  DRIVE_SOMPONG_GRAB_FOLDER_ID already
                                  points at -- kept as an independent
                                  constant here rather than importing that
                                  one, same reasoning video_to_drive.py's
                                  own docstring gives for keeping
                                  DRIVE_SOMPONG_GRAB_FOLDER_ID and
                                  DRIVE_VIDEO_PARENT_FOLDER_ID apart: two
                                  names that happen to agree today should
                                  not silently start disagreeing for each
                                  other later)
    DRIVE_BROKER_MAX_UPLOAD_BYTES    per-file cap (default 500 MiB)
    DRIVE_BROKER_MAX_REQUEST_BYTES   request-line cap (default 64 KiB)
    DRIVE_BROKER_SOCKET_TIMEOUT      per-connection read timeout, seconds
                                      (default 30)

Single-threaded accept loop: one connection handled start-to-finish before
the next is accepted, so "one upload at a time" is structural, not a lock.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import socket
import stat
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "gdrive-bridge"))
import ilag_sync  # noqa: E402 -- module object, so ENV_CANDIDATES can be overridden (same idiom as scripts/video_to_drive.py)
from ilag_mirror import list_folder  # noqa: E402 -- the ONLY listing this module ever does, always against cfg.folder_id

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.logger import get_logger  # noqa: E402

# task-e713c4e2 D1 -- the CEO's Desktop Cloud root. See module docstring for
# why this is a separate constant from scripts/video_to_drive.py's
# DRIVE_SOMPONG_GRAB_FOLDER_ID even though both currently equal it.
DEFAULT_FOLDER_ID = "115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR"
DEFAULT_SOCKET_PATH = "/run/driveup/drive-broker.sock"
DEFAULT_MAX_UPLOAD_BYTES = 500 * 1024 * 1024   # 500 MiB
DEFAULT_MAX_REQUEST_BYTES = 64 * 1024          # 64 KiB -- one JSON line naming a path
DEFAULT_SOCKET_TIMEOUT = 30.0

# Below this length a "secret" is almost certainly an empty/placeholder
# value, not a real credential -- redacting it would just mangle ordinary
# short substrings in log lines and error text for no benefit.
_MIN_REDACTABLE_SECRET_LEN = 8


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class BrokerConfig:
    env_path: Path
    socket_path: Path
    allowed_uids: frozenset[int]
    staging_root: Path
    folder_id: str
    max_upload_bytes: int
    max_request_bytes: int
    socket_timeout: float


# --------------------------------------------------------------------------- config

def load_config(env: Mapping[str, str] | None = None) -> BrokerConfig:
    env = os.environ if env is None else env

    def require(key: str) -> str:
        value = env.get(key)
        if not value:
            raise ConfigError(f"{key} is required (unset or empty)")
        return value

    env_path = Path(require("DRIVE_BROKER_ENV"))

    staging_root_raw = Path(require("DRIVE_BROKER_STAGING_ROOT"))
    try:
        staging_root = staging_root_raw.resolve(strict=True)
    except OSError as e:
        raise ConfigError(f"DRIVE_BROKER_STAGING_ROOT does not exist: {staging_root_raw} ({e})") from e
    if not staging_root.is_dir():
        raise ConfigError(f"DRIVE_BROKER_STAGING_ROOT is not a directory: {staging_root}")

    uids_raw = require("DRIVE_BROKER_ALLOWED_UIDS")
    try:
        allowed_uids = frozenset(int(u.strip()) for u in uids_raw.split(",") if u.strip())
    except ValueError as e:
        raise ConfigError(f"DRIVE_BROKER_ALLOWED_UIDS must be comma-separated integers, got {uids_raw!r}: {e}") from e
    if not allowed_uids:
        raise ConfigError("DRIVE_BROKER_ALLOWED_UIDS must name at least one uid")

    def optional_int(key: str, default: int) -> int:
        raw = env.get(key)
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError as e:
            raise ConfigError(f"{key} must be an integer, got {raw!r}: {e}") from e

    return BrokerConfig(
        env_path=env_path,
        socket_path=Path(env.get("DRIVE_BROKER_SOCKET_PATH") or DEFAULT_SOCKET_PATH),
        allowed_uids=allowed_uids,
        staging_root=staging_root,
        folder_id=env.get("DRIVE_BROKER_FOLDER_ID") or DEFAULT_FOLDER_ID,
        max_upload_bytes=optional_int("DRIVE_BROKER_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES),
        max_request_bytes=optional_int("DRIVE_BROKER_MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES),
        socket_timeout=float(optional_int("DRIVE_BROKER_SOCKET_TIMEOUT", int(DEFAULT_SOCKET_TIMEOUT))),
    )


def apply_oauth_env_override(env_path: Path) -> None:
    """Point ilag_sync's OAuth loader at DRIVE_BROKER_ENV. Same override
    idiom scripts/video_to_drive.py uses for SOMPONG_DRIVE_ENV -- ilag_sync
    is shared, general-purpose Drive plumbing that otherwise hardcodes the
    Mac-only claudeflow .env candidates."""
    ilag_sync.ENV_CANDIDATES = [env_path]


# --------------------------------------------------------------------------- secret redaction

def load_secret_values() -> frozenset[str]:
    """The current OAuth triple's values, for redaction -- never for
    forwarding anywhere. Call once at startup, after
    apply_oauth_env_override()."""
    try:
        values = ilag_sync._load_oauth()
    except SystemExit:
        return frozenset()
    return frozenset(v for v in values.values() if v and len(v) >= _MIN_REDACTABLE_SECRET_LEN)


def current_secrets(startup_secrets: frozenset[str]) -> frozenset[str]:
    """startup_secrets plus whatever access token ilag_sync has cached right
    now (it refreshes/rotates independently of the OAuth triple)."""
    token = ilag_sync._token_cache.get("value")
    if token and len(str(token)) >= _MIN_REDACTABLE_SECRET_LEN:
        return startup_secrets | {str(token)}
    return startup_secrets


def redact(text: str, secrets: frozenset[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def redact_result(result: dict, secrets: frozenset[str]) -> dict:
    out = dict(result)
    if "error" in out and isinstance(out["error"], str):
        out["error"] = redact(out["error"], secrets)
    return out


# --------------------------------------------------------------------------- path safety

def resolve_staged_path(path_str: str, staging_root: Path, max_bytes: int) -> tuple[Path | None, str | None]:
    """(resolved_path, None) if `path_str` is a regular file, at or under
    `max_bytes`, whose FULLY RESOLVED (symlinks followed) location is inside
    `staging_root` -- otherwise (None, reason). Resolve-first-then-check:
    a symlink that lives inside staging_root but points outside it resolves
    outside and is rejected, same shape as lib/link_reader.py's
    check_url_safe() D3 SSRF guard ("resolve first, then check")."""
    if not path_str.startswith("/"):
        return None, "path must be absolute"

    try:
        resolved = Path(path_str).resolve(strict=True)
    except FileNotFoundError:
        return None, "path does not exist"
    except OSError as e:
        return None, f"could not resolve path: {e}"

    try:
        resolved.relative_to(staging_root)
    except ValueError:
        return None, "path is outside the staging root"

    try:
        st = resolved.stat()
    except OSError as e:
        return None, f"could not stat path: {e}"

    if not stat.S_ISREG(st.st_mode):
        return None, "path is not a regular file"
    if st.st_size > max_bytes:
        return None, f"file too large ({st.st_size} bytes, cap is {max_bytes})"

    return resolved, None


def _valid_name(name: object) -> bool:
    return isinstance(name, str) and bool(name) and "/" not in name and name not in (".", "..")


# --------------------------------------------------------------------------- upload (the only two Drive calls in this module)

def do_upload(local_path: Path, name: str, folder_id: str) -> dict:
    try:
        res = ilag_sync.upload(local_path, name, folder_id)
    except Exception:
        return {"ok": False, "error": "upload to Drive failed"}

    # Never trust the upload call's own response -- re-list the fixed
    # destination folder fresh and require the name+size to actually be
    # there. Same verify-before-trust pattern scripts/video_to_drive.py and
    # scripts/gdrive-bridge/ilag_mirror.py already use.
    try:
        fresh = list_folder(folder_id)
    except Exception:
        return {"ok": False, "error": "uploaded but the verification listing failed"}

    local_size = local_path.stat().st_size
    drive_size = fresh.get(name)
    if drive_size is None or drive_size != local_size:
        return {"ok": False, "error": "upload could not be verified in a fresh folder listing"}

    file_id = res.get("id")
    return {
        "ok": True,
        "id": file_id,
        "name": name,
        "link": f"https://drive.google.com/file/d/{file_id}/view" if file_id else None,
        "size": local_size,
    }


def handle_request(raw: bytes, cfg: BrokerConfig) -> dict:
    """Pure(ish) dispatcher: parses the one supported request shape and
    calls do_upload(). Deliberately reads ONLY "op"/"path"/"name" off the
    parsed object -- any other key (folder_id, parent, destination, ...) is
    never looked at, so a client can put whatever it wants there and it is
    ignored, not refused-because-seen."""
    try:
        req = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "error": "invalid JSON request"}
    if not isinstance(req, dict):
        return {"ok": False, "error": "request must be a JSON object"}

    if req.get("op") != "upload":
        return {"ok": False, "error": f"unsupported op {req.get('op')!r} -- only 'upload' exists"}

    path_str = req.get("path")
    if not isinstance(path_str, str) or not path_str:
        return {"ok": False, "error": "'path' is required and must be a string"}

    resolved, err = resolve_staged_path(path_str, cfg.staging_root, cfg.max_upload_bytes)
    if err:
        return {"ok": False, "error": err}

    name = req.get("name")
    if name is not None and not _valid_name(name):
        return {"ok": False, "error": "'name' must be a plain filename with no path separators"}

    return do_upload(resolved, name or resolved.name, cfg.folder_id)


# --------------------------------------------------------------------------- peer identity (SO_PEERCRED)

def get_peer_uid(conn: socket.socket) -> int:
    """Linux-only (SO_PEERCRED) -- the deploy target (Contabo) and CI both
    run Linux. Factored out so tests can monkeypatch this one function
    directly rather than needing a real cross-platform peer-credential
    syscall to exercise the allowlist logic."""
    if not hasattr(socket, "SO_PEERCRED"):
        raise OSError("SO_PEERCRED is not available on this platform")
    creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", creds)
    return uid


# --------------------------------------------------------------------------- socket plumbing

def _read_line(conn: socket.socket, max_bytes: int) -> bytes:
    buf = bytearray()
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            if buf:
                raise ValueError("connection closed before the request line was terminated")
            raise ValueError("connection closed with no request")
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise ValueError(f"request exceeds max size ({max_bytes} bytes)")
        newline = buf.find(b"\n")
        if newline != -1:
            return bytes(buf[:newline])


def _send_json(conn: socket.socket, obj: dict) -> None:
    try:
        conn.sendall((json.dumps(obj) + "\n").encode("utf-8"))
    except OSError:
        pass  # client already gone -- nothing left to do


def handle_connection(conn: socket.socket, cfg: BrokerConfig, logger: logging.Logger,
                       startup_secrets: frozenset[str]) -> None:
    conn.settimeout(cfg.socket_timeout)

    try:
        uid = get_peer_uid(conn)
    except OSError as e:
        logger.warning("could not read peer credentials: %s", e)
        _send_json(conn, {"ok": False, "error": "could not verify caller identity"})
        return

    if uid not in cfg.allowed_uids:
        logger.warning("refused connection from uid %s (not in allowlist)", uid)
        _send_json(conn, {"ok": False, "error": "caller not authorized"})
        return

    try:
        raw = _read_line(conn, cfg.max_request_bytes)
    except (TimeoutError, socket.timeout):
        _send_json(conn, {"ok": False, "error": "request timed out"})
        return
    except ValueError as e:
        _send_json(conn, {"ok": False, "error": str(e)})
        return

    result = handle_request(raw, cfg)
    secrets = current_secrets(startup_secrets)
    safe_result = redact_result(result, secrets)

    if safe_result.get("ok"):
        logger.info("upload uid=%s name=%s size=%s", uid, safe_result.get("name"), safe_result.get("size"))
    else:
        logger.warning("refused uid=%s error=%s", uid, safe_result.get("error"))

    _send_json(conn, safe_result)


def bind_socket(socket_path: Path) -> socket.socket:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(socket_path))
    os.chmod(socket_path, 0o660)  # group-only -- `driveup`'s own group, matches install-drive-broker.sh
    sock.listen(4)
    return sock


_shutdown_requested = False


def _request_shutdown(signum, frame) -> None:  # noqa: ARG001
    global _shutdown_requested
    _shutdown_requested = True


def serve_forever(server_sock: socket.socket, cfg: BrokerConfig, logger: logging.Logger,
                   startup_secrets: frozenset[str], *, once: bool = False) -> None:
    while not _shutdown_requested:
        server_sock.settimeout(1.0)
        try:
            conn, _ = server_sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        try:
            handle_connection(conn, cfg, logger, startup_secrets)
        except Exception:
            logger.exception("unexpected error handling a connection")
        finally:
            conn.close()
        if once:
            return


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    once = argv is not None and "--once" in argv

    try:
        cfg = load_config()
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 1

    logger = get_logger("drive_upload_broker")
    apply_oauth_env_override(cfg.env_path)
    startup_secrets = load_secret_values()

    try:
        server_sock = bind_socket(cfg.socket_path)
    except OSError as e:
        logger.error("could not bind socket at %s: %s", cfg.socket_path, e)
        return 1

    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)

    logger.info(
        "listening on %s -- allowed uids=%s, folder=%s, staging_root=%s, max_upload_bytes=%s",
        cfg.socket_path, sorted(cfg.allowed_uids), cfg.folder_id, cfg.staging_root, cfg.max_upload_bytes,
    )
    try:
        serve_forever(server_sock, cfg, logger, startup_secrets, once=once)
    finally:
        server_sock.close()
        cfg.socket_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
