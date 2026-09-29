#!/usr/bin/env python3
"""Drive SHARE broker -- SomPong's EA runner's one way to hand the CEO a link
to a file on his Drive (task-1c07d46b, contract of record: org wiki
`mooniex:projects/sompong-ea.md` section D, ADR 0032; CEO 2026-09-26 approved
exactly one destination, `SomPong Share/` at the Drive root, id
`1Qn7B0e6Pa7y8gS5bjUfs-f5ewMIERUsR`).

This is a THIRD sibling of runners/drive_upload_broker.py and
runners/drive_photo_broker.py, not a modification of either -- same shape,
same three safety properties (see drive_photo_broker.py's docstring for the
full reasoning), copied here rather than imported so none of the three
brokers can ever accidentally start sharing config, a socket, or a uid
allowlist:

  1. The destination folder id is fixed from THIS PROCESS's own config
     (DRIVE_SHARE_BROKER_FOLDER_ID / DEFAULT_FOLDER_ID below) and is never
     read from a client request under any key ("folder_id"/"parent"/
     "destination" are simply never looked at).
  2. Exactly one client-facing operation exists ("share"). There is no
     list/read/download/move/rename/trash-arbitrary-file code path -- see
     test_drive_share_broker.py's grep-style guard test.
  3. Caller identity is checked via SO_PEERCRED against an explicit uid
     allowlist (the uid of `sompong`, resolved by the installer at deploy
     time -- never hard-coded in this module), and every share path is
     resolved (symlinks followed) and checked against a configured staging
     root AFTER resolution.

WHAT THIS BROKER ADDS OVER ITS SIBLINGS -- a PUBLIC link:

Every upload this broker performs ends with a `{"type": "anyone", "role":
"reader"}` permission on the freshly uploaded file -- i.e. anyone who has the
link can view it, no Google sign-in required. That is the entire point of
this broker (SomPong needs to hand the CEO a link he can open from LINE on
his phone), and it is also why the destination is locked to ONE CEO-approved
folder that holds nothing else: this broker can never be pointed at
`Desktop Cloud` or `My Picture & Videos.` (drive_upload_broker.py's and
drive_photo_broker.py's own fixed folders) because its folder id is a
compile-time-adjacent constant, exactly like theirs, never a request field.

Order of operations for one request, all of it or none of it:
    open (atomically, see below) -> upload -> set the anyone/reader
    permission -> re-read the file fresh (parents AND size) to verify it
    actually landed, public, in the right place -> return its webViewLink ->
    delete the staged copy.
The staged copy is removed in a `finally` -- on ok:true AND on ok:false --
so a share request never leaves a second copy of a CEO file sitting on disk
after the socket round-trip ends, win or lose.

TOCTOU FIX (task-1c07d46b iteration 2, CTO-FEEDBACK.md): the staging
directory is owned by `sompong` -- the CALLER, not a trusted root process
(unlike drive_upload_broker.py's root filer or drive_photo_broker.py's
container outbox) -- and by CEO ruling `sompong` may edit its own runner
code. A "resolve the path, stat it, then later re-open it by name" flow (the
sibling brokers' pattern) has a race window between the check and the open:
the caller can swap the staged file for a symlink to any `shareup`-readable
file (e.g. this broker's own OAuth credential) in that window, and the
broker would upload and PUBLICLY share whatever the symlink now points to.
Closed by making the "check" and the "open" the same atomic syscall:
    1. `path` must name a bare file directly inside the staging root -- no
       `/`, no subdirs, no `..`. Checked as a string, before anything is
       opened.
    2. Hold a `dir_fd` on the staging root (`os.open(root, O_DIRECTORY)`)
       and open the file with `os.open(name, O_NOFOLLOW|O_NONBLOCK,
       dir_fd=root_fd)`. If `name` is (or has become, by the time of this
       call) a symlink, the open itself fails with ELOOP -- its target is
       NEVER read. O_NONBLOCK means a FIFO can't hang the broker either.
    3. Every safety check (`S_ISREG`, `st_nlink == 1` i.e. no hardlink to
       another file, `st_uid` matches the uid that connected over the
       socket, size <= cap) is `fstat()` on that OPENED fd, never `stat()`
       on the path -- nothing can be swapped out from under an already-open
       fd.
    4. The upload itself reads from that same fd (copied into a
       broker-private PrivateTmp file, since ilag_sync.upload() takes a
       path) -- the attacker-writable staging name is never opened by path
       a second time. The staged name is unlinked via the same `dir_fd`.

Protocol -- one JSON line in, one JSON line out, over
DRIVE_SHARE_BROKER_SOCKET_PATH (fixed by contract: /run/mooniex-share-broker/broker.sock):
    request:  {"op": "share", "path": "<staging path>", "name": "<display name>"}
    response: {"ok": true, "id": "...", "link": "<webViewLink>"}
           or {"ok": false, "error": "<reason>"}

Config, all via environment (set by scripts/install-share-broker.sh's
systemd unit, never by this code):
    DRIVE_SHARE_BROKER_ENV             path to a file holding GOOGLE_OAUTH_
                                        CLIENT_ID/SECRET/REFRESH_TOKEN
                                        (required). UNLIKE the two sibling
                                        brokers' broker-owned credential
                                        files, this one is ROOT-owned,
                                        readable only by the broker user
                                        (`shareup`) -- task instruction, on
                                        the record here rather than left
                                        implicit: it changes nothing about
                                        who can list/upload through the
                                        broker (that is still the uid
                                        allowlist below), it only means a
                                        compromise of the broker's own
                                        unprivileged account cannot also
                                        rewrite its own credential file.
    DRIVE_SHARE_BROKER_STAGING_ROOT    the only directory tree shareable
                                        paths may resolve into (required) --
                                        contract fixes this to
                                        /var/lib/sompong-share/staging
                                        (group `shareup`, mode 2770; files
                                        the runner stages there are 0640).
    DRIVE_SHARE_BROKER_ALLOWED_UIDS    comma-separated uid(s) permitted to
                                        call in (required) -- resolved by
                                        the installer as `id -u sompong` at
                                        deploy time, never hard-coded here.
    DRIVE_SHARE_BROKER_SOCKET_PATH     unix socket to listen on (default:
                                        /run/mooniex-share-broker/broker.sock,
                                        the contract's fixed path)
    DRIVE_SHARE_BROKER_FOLDER_ID       the fixed destination folder (default:
                                        "SomPong Share/", CEO-approved
                                        2026-09-26, id
                                        1Qn7B0e6Pa7y8gS5bjUfs-f5ewMIERUsR --
                                        see the gdrive-filing skill and org
                                        wiki `mooniex:projects/sompong-ea.md`)
    DRIVE_SHARE_MAX_MB                 per-file cap in MiB (default 300 --
                                        task-fixed env var name/default)
    DRIVE_SHARE_BROKER_MAX_REQUEST_BYTES   request-line cap (default 64 KiB)
    DRIVE_SHARE_BROKER_SOCKET_TIMEOUT      per-connection read timeout,
                                            seconds (default 30)

Single-threaded accept loop: one connection handled start-to-finish before
the next is accepted, so "one share at a time" is structural, not a lock.

Logging (task instruction): a refusal or a success logs a REASON only --
never a filename, a display name, or file content. The Drive file id and
link are not logged either (a link with view access is itself sharable
information, no different from a credential in that sense for logging
purposes).
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
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "gdrive-bridge"))
import ilag_sync  # noqa: E402 -- module object, so ENV_CANDIDATES can be overridden (same idiom as the sibling brokers)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.logger import get_logger  # noqa: E402

# CEO 2026-09-26 approval, org wiki mooniex:projects/sompong-ea.md section D --
# "SomPong Share/" at the Drive root. The ONLY destination this broker will
# ever write to.
DEFAULT_FOLDER_ID = "1Qn7B0e6Pa7y8gS5bjUfs-f5ewMIERUsR"
DEFAULT_SOCKET_PATH = "/run/mooniex-share-broker/broker.sock"
DEFAULT_MAX_MB = 300
DEFAULT_MAX_REQUEST_BYTES = 64 * 1024          # 64 KiB -- one JSON line
DEFAULT_SOCKET_TIMEOUT = 30.0

# Below this length a "secret" is almost certainly an empty/placeholder
# value, not a real credential -- redacting it would just mangle ordinary
# short substrings in log lines and error text for no benefit. Same
# threshold the sibling brokers use.
_MIN_REDACTABLE_SECRET_LEN = 8

_PERMISSION_BODY = {"type": "anyone", "role": "reader"}


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

    env_path = Path(require("DRIVE_SHARE_BROKER_ENV"))

    staging_root_raw = Path(require("DRIVE_SHARE_BROKER_STAGING_ROOT"))
    try:
        staging_root = staging_root_raw.resolve(strict=True)
    except OSError as e:
        raise ConfigError(f"DRIVE_SHARE_BROKER_STAGING_ROOT does not exist: {staging_root_raw} ({e})") from e
    if not staging_root.is_dir():
        raise ConfigError(f"DRIVE_SHARE_BROKER_STAGING_ROOT is not a directory: {staging_root}")

    uids_raw = require("DRIVE_SHARE_BROKER_ALLOWED_UIDS")
    try:
        allowed_uids = frozenset(int(u.strip()) for u in uids_raw.split(",") if u.strip())
    except ValueError as e:
        raise ConfigError(f"DRIVE_SHARE_BROKER_ALLOWED_UIDS must be comma-separated integers, got {uids_raw!r}: {e}") from e
    if not allowed_uids:
        raise ConfigError("DRIVE_SHARE_BROKER_ALLOWED_UIDS must name at least one uid")

    def optional_int(key: str, default: int) -> int:
        raw = env.get(key)
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError as e:
            raise ConfigError(f"{key} must be an integer, got {raw!r}: {e}") from e

    max_mb = optional_int("DRIVE_SHARE_MAX_MB", DEFAULT_MAX_MB)
    if max_mb <= 0:
        raise ConfigError(f"DRIVE_SHARE_MAX_MB must be positive, got {max_mb}")

    return BrokerConfig(
        env_path=env_path,
        socket_path=Path(env.get("DRIVE_SHARE_BROKER_SOCKET_PATH") or DEFAULT_SOCKET_PATH),
        allowed_uids=allowed_uids,
        staging_root=staging_root,
        folder_id=env.get("DRIVE_SHARE_BROKER_FOLDER_ID") or DEFAULT_FOLDER_ID,
        max_upload_bytes=max_mb * 1024 * 1024,
        max_request_bytes=optional_int("DRIVE_SHARE_BROKER_MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES),
        socket_timeout=float(optional_int("DRIVE_SHARE_BROKER_SOCKET_TIMEOUT", int(DEFAULT_SOCKET_TIMEOUT))),
    )


def apply_oauth_env_override(env_path: Path) -> None:
    """Point ilag_sync's OAuth loader at DRIVE_SHARE_BROKER_ENV. Same override
    idiom the sibling brokers use -- ilag_sync is shared, general-purpose
    Drive plumbing that otherwise hardcodes the Mac-only claudeflow .env
    candidates."""
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

def _valid_name(name: object) -> bool:
    return isinstance(name, str) and bool(name) and "/" not in name and name not in (".", "..")


def _validate_bare_child_name(path_str: str, staging_root: Path) -> tuple[str | None, str | None]:
    """String-shape check only -- no resolve(), no stat(), nothing that
    could itself become a race window. `path_str`'s directory must equal
    `staging_root` EXACTLY (as text) and its final component must be a bare
    filename (no `/`, not `.`/`..`). The actual containment guarantee comes
    from the dir_fd + O_NOFOLLOW open in _open_and_verify_staged_fd() below,
    not from this comparison -- this just rejects an obviously wrong shape
    (a subdirectory, a `..` segment, a relative path) before anything is
    opened. Returns (bare_name, None) or (None, reason)."""
    if not path_str.startswith("/"):
        return None, "path must be absolute"

    p = Path(path_str)
    name = p.name
    if not _valid_name(name):
        return None, "path must name a plain file, not a directory or '.'/'..'"
    if str(p.parent) != str(staging_root):
        return None, "path must be a direct child of the staging root, no subdirectories"

    return name, None


def _open_and_verify_staged_fd(name: str, root_fd: int, expected_uid: int,
                                max_bytes: int) -> tuple[int | None, os.stat_result | None, str | None]:
    """Atomically open `name` as a direct child of the staging root (via
    `root_fd`) with O_NOFOLLOW -- the open() call IS the security check, so
    nothing between "checked" and "used" can swap what gets read. A symlink
    at `name` (planted before this call, or swapped in during the request)
    fails the open with ELOOP -- its target is never read. O_NONBLOCK means
    a FIFO opens immediately (never hangs the broker) and is then rejected
    by the S_ISREG check below, unread.

    Every check past the open is `fstat()` on the OPENED fd, never `stat()`
    on the path or name -- what fstat() reports cannot be swapped out from
    under an already-open fd. Returns (fd, stat, None) on success (caller
    must close fd) or (None, None, reason) on any rejection (fd already
    closed)."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
    except OSError as e:
        return None, None, f"could not open staged file: {e}"

    try:
        st = os.fstat(fd)
    except OSError as e:
        os.close(fd)
        return None, None, f"could not stat staged file: {e}"

    if not stat.S_ISREG(st.st_mode):
        os.close(fd)
        return None, None, "staged path is not a regular file"
    if st.st_nlink != 1:
        os.close(fd)
        return None, None, "staged file has more than one hard link"
    if st.st_uid != expected_uid:
        os.close(fd)
        return None, None, "staged file is not owned by the allowed caller"
    if st.st_size > max_bytes:
        os.close(fd)
        return None, None, f"file too large ({st.st_size} bytes, cap is {max_bytes})"

    return fd, st, None


# --------------------------------------------------------------------------- share (upload + permission + verify)

def set_public_reader_permission(file_id: str) -> None:
    """Set EXACTLY ONE permission on the freshly uploaded file: anyone with
    the link can view it. The request body is a fixed literal
    (_PERMISSION_BODY) -- never built from, or influenced by, anything in
    the client's request."""
    ilag_sync.api(
        f"{ilag_sync.DRIVE_FILES}/{file_id}/permissions",
        method="POST",
        params={"fields": "id"},
        data=json.dumps(_PERMISSION_BODY).encode(),
        headers={"Content-Type": "application/json"},
    )


def verify_shared_file(file_id: str, folder_id: str, expected_size: int) -> tuple[dict | None, str | None]:
    """Re-read the file FRESH from Drive (never trust the upload response)
    and require its parent to be exactly the fixed folder and its size to
    match the local staged copy. Returns (info, None) on success, or
    (None, reason) -- info carries webViewLink for the caller."""
    try:
        info = ilag_sync.api(
            f"{ilag_sync.DRIVE_FILES}/{file_id}",
            params={"fields": "id,name,size,parents,webViewLink"},
            timeout=30,
        )
    except Exception:
        return None, "could not verify the upload -- re-read of the file failed"

    parents = info.get("parents") or []
    if parents != [folder_id]:
        return None, "uploaded file's parent folder could not be verified"

    size = info.get("size")
    if size is None or int(size) != expected_size:
        return None, "uploaded file's size could not be verified"

    if not info.get("webViewLink"):
        return None, "uploaded file has no webViewLink"

    return info, None


def do_share(fd: int, name: str, folder_id: str) -> dict:
    """Uploads from the ALREADY-OPENED, already-fstat-verified `fd` --
    never opens `name` by path again. Copies the fd's bytes into a
    broker-private temp file (the systemd unit sets PrivateTmp=true)
    because ilag_sync.upload() takes a path; the fd itself is what
    _open_and_verify_staged_fd() checked, so this copy step touches nothing
    the caller can still influence."""
    tmp_path: Path | None = None
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        tmp_fd, tmp_name = tempfile.mkstemp(prefix="share-broker-")
        tmp_path = Path(tmp_name)
        with os.fdopen(tmp_fd, "wb") as tmp:
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)

        try:
            res = ilag_sync.upload(tmp_path, name, folder_id)
        except Exception:
            return {"ok": False, "error": "upload to Drive failed"}

        file_id = res.get("id")
        if not file_id:
            return {"ok": False, "error": "upload response was missing a file id"}

        try:
            set_public_reader_permission(file_id)
        except Exception:
            return {"ok": False, "error": "could not set the sharing permission"}

        local_size = tmp_path.stat().st_size
        info, err = verify_shared_file(file_id, folder_id, local_size)
        if err:
            return {"ok": False, "error": err}

        return {"ok": True, "id": file_id, "link": info["webViewLink"]}
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def handle_request(raw: bytes, cfg: BrokerConfig, caller_uid: int) -> dict:
    """Pure(ish) dispatcher: parses the one supported request shape and
    calls do_share(). Deliberately reads ONLY "op"/"path"/"name" off the
    parsed object -- any other key (folder_id, parent, destination, ...) is
    never looked at, so a client can put whatever it wants there and it is
    ignored, not refused-because-seen.

    `caller_uid` is the uid SO_PEERCRED reported for THIS connection
    (already checked against the allowlist by handle_connection) -- passed
    through so the staged file's owner can be checked against the uid that
    is actually asking for it, not just "some allowed uid" (task-1c07d46b
    iteration 2 fix).

    The path is opened via a dir_fd held on the staging root, never
    re-opened by path; the staged name is unlinked via that same dir_fd in
    a `finally`, on ok:true AND on ok:false alike."""
    try:
        req = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "error": "invalid JSON request"}
    if not isinstance(req, dict):
        return {"ok": False, "error": "request must be a JSON object"}

    if req.get("op") != "share":
        return {"ok": False, "error": f"unsupported op {req.get('op')!r} -- only 'share' exists"}

    path_str = req.get("path")
    if not isinstance(path_str, str) or not path_str:
        return {"ok": False, "error": "'path' is required and must be a string"}

    display_name = req.get("name")
    if not _valid_name(display_name):
        return {"ok": False, "error": "'name' is required and must be a plain filename with no path separators"}

    bare_name, err = _validate_bare_child_name(path_str, cfg.staging_root)
    if err:
        return {"ok": False, "error": err}

    try:
        root_fd = os.open(str(cfg.staging_root), os.O_RDONLY | os.O_DIRECTORY)
    except OSError as e:
        return {"ok": False, "error": f"could not open the staging root: {e}"}

    try:
        fd, _st, err = _open_and_verify_staged_fd(bare_name, root_fd, caller_uid, cfg.max_upload_bytes)
        if err:
            return {"ok": False, "error": err}

        try:
            return do_share(fd, display_name, cfg.folder_id)
        finally:
            os.close(fd)
            try:
                os.unlink(bare_name, dir_fd=root_fd)
            except OSError:
                pass  # already gone, or never fully ours to remove -- never fail the response over cleanup
    finally:
        os.close(root_fd)


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

    result = handle_request(raw, cfg, uid)
    secrets = current_secrets(startup_secrets)
    safe_result = redact_result(result, secrets)

    # Reason only -- never a filename, display name, or file content
    # (task instruction).
    if safe_result.get("ok"):
        logger.info("share uid=%s ok", uid)
    else:
        logger.warning("refused uid=%s error=%s", uid, safe_result.get("error"))

    _send_json(conn, safe_result)


def bind_socket(socket_path: Path) -> socket.socket:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(socket_path))
    os.chmod(socket_path, 0o660)  # group-only -- `shareup`'s own group, matches install-share-broker.sh
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

    logger = get_logger("drive_share_broker")
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
