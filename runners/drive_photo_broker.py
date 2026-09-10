#!/usr/bin/env python3
"""Drive photo broker -- broker #2 (task-a1c618db, design of record: org wiki
`mooniex:projects/sompong-line.md` feature F2; CEO 2026-09-10: "SomPong แอบ
เก็บรูป (เอาไว้เป็นความทรงจำ) ที่ทุกคนส่งมาในกลุ่ม เสมอ รูปครอบครัว ไฟล์ครอบครัว
... เอาใส่ใน Google Drive").

This is a SIBLING of runners/drive_upload_broker.py, not a modification of it
-- that broker and its `Desktop Cloud` target are untouched. Same shape, same
three safety properties (see that module's docstring for the full reasoning),
copied here rather than imported so the two brokers can never accidentally
start sharing config, a socket, or a uid allowlist:

  1. The destination folder id is fixed from THIS PROCESS's own config
     (DRIVE_PHOTO_BROKER_FOLDER_ID / DEFAULT_FOLDER_ID below) and is never
     read from a client request under any key ("folder_id"/"parent"/
     "destination" are simply never looked at).
  2. Exactly one client-facing operation exists ("upload"). There is no
     list/read/download/move/rename/trash-arbitrary-file code path -- see
     test_drive_photo_broker.py's grep-style guard test. The internal Drive
     calls this module makes are: ilag_sync.upload() (write the file),
     ilag_mirror.list_folder() (verify it landed -- against either the fixed
     root or the one resolved month folder, never anywhere else), and a
     scoped find-or-create against ilag_sync.api() for the month folder
     itself (see "the one new attack surface" below) -- never a generic
     ensure_folder() over an attacker-shaped path.
  3. Caller identity is checked via SO_PEERCRED against an explicit uid
     allowlist, and every upload path is resolved (symlinks followed) and
     checked against a configured staging root AFTER resolution.

The credential is never logged, echoed, or returned -- not on error paths
either (same _redact() scheme as drive_upload_broker.py).

CONTAINMENT BOUNDARY, PRECISELY (task-4307c02c, 2026-09-10): the guarantee
this design gives is CONTAINER != DRIVE, never HOST ROOT != DRIVE.
A compromised claudeflow container never gets this socket, this credential,
or a network path to either -- at worst it writes garbage bytes onto a disk
it already controls (the outbox). That property does not depend on which
uids appear in DRIVE_PHOTO_BROKER_ALLOWED_UIDS, and it is unaffected by uid
0 (root) being one of them. Host root is a different matter and is NOT a
boundary this design claims to hold: on this box root already owns
/root/projects, every credential file on disk, systemd, and every service
user (including this one) -- a host-root compromise has the Drive
regardless of which uid any of these processes run as, so refusing to list
uid 0 here would not remove any real capability from root, only from an
allowlist root can rewrite at will anyway. That is why
runners/sompong_photo_filer.py (the broker's one caller) is allowed to run
as root -- see that module's docstring and docs/design/sompong-photos.md
for the full reasoning, including the alternatives that were rejected
(chmod/ACL on /root, relocating the outbox). This broker process itself
keeps running as its own unprivileged `photoup` user regardless -- it is
the one process on the box that holds the Drive OAuth credential, and
nothing about the filer's uid changes that.

THE ONE NEW ATTACK SURFACE -- the "subfolder" request field:
    SomPong's photos are filed by month ("My Picture & Videos." / YYYY-MM/,
    per the gdrive-filing skill's carve-out for this one folder). The broker
    -- not the caller -- must be able to create that month folder the first
    time it's needed, since the caller (sompong_photo_filer.py, running as a
    host process with no Drive access of its own) has no other way to get
    one made. That is new capability this broker's sibling does not have, so
    it gets the same "resolve first, then check" discipline everything else
    here uses: `subfolder` is validated as a VALUE, not a path -- it must
    fullmatch `^[0-9]{4}-[0-9]{2}$` using an explicit ASCII digit class (not
    `\\d`, which also matches non-ASCII decimal digits under Python's default
    Unicode-aware regex behaviour) -- so no id, no slash, no `..`, no
    unicode digit, no arbitrarily long string ever reaches a Drive call. The
    resolved-or-created folder is always a DIRECT CHILD of the broker's own
    fixed folder id -- the search query and the creation call both pin
    `parents`/`'... in parents'` to `cfg.folder_id`, never to anything client
    supplied. A request with no `subfolder` uploads into the fixed folder
    itself, same as the sibling broker's only mode.

Protocol -- one JSON line in, one JSON line out, over
DRIVE_PHOTO_BROKER_SOCKET_PATH:
    request:  {"op": "upload", "path": "<abs path>", "name": "<optional>",
               "subfolder": "<optional, YYYY-MM>"}
    response: {"ok": true, "id", "name", "link", "size"}
           or {"ok": false, "error": "<reason>"}

Config, all via environment (set by scripts/install-photo-broker.sh's
systemd unit, never by this code):
    DRIVE_PHOTO_BROKER_ENV             path to a file readable only by
                                        `photoup` holding GOOGLE_OAUTH_
                                        CLIENT_ID/SECRET/REFRESH_TOKEN
                                        (required)
    DRIVE_PHOTO_BROKER_STAGING_ROOT    the only directory tree uploadable
                                        paths may resolve into (required) --
                                        NOT the claudeflow outbox (this
                                        unprivileged user cannot traverse
                                        /root at all): a separate directory
                                        (default /var/lib/photoup/staging,
                                        task-29744f52) that the root-run
                                        filer copies verified bytes into
                                        before calling this broker -- see
                                        runners/sompong_photo_filer.py's
                                        "Staging copy" docstring section and
                                        docs/design/sompong-photos.md
    DRIVE_PHOTO_BROKER_ALLOWED_UIDS    comma-separated uid(s) permitted to
                                        call in (required) -- the host
                                        filer's uid, which is 0 (root) as of
                                        task-4307c02c: see "CONTAINMENT
                                        BOUNDARY, PRECISELY" above for why
                                        that is safe here. The claudeflow
                                        CONTAINER is a different identity
                                        entirely and must never appear here
                                        -- but it never could anyway, since
                                        it has no socket, credential, or
                                        network path to reach this broker in
                                        the first place.
    DRIVE_PHOTO_BROKER_SOCKET_PATH     unix socket to listen on (default:
                                        /run/photoup/photo-broker.sock)
    DRIVE_PHOTO_BROKER_FOLDER_ID       the fixed destination folder (default:
                                        "My Picture & Videos.", CEO-approved
                                        2026-09-10 -- see the gdrive-filing
                                        skill's folder table)
    DRIVE_PHOTO_BROKER_MAX_UPLOAD_BYTES    per-file cap (default 200 MiB)
    DRIVE_PHOTO_BROKER_MAX_REQUEST_BYTES   request-line cap (default 64 KiB)
    DRIVE_PHOTO_BROKER_SOCKET_TIMEOUT      per-connection read timeout,
                                            seconds (default 30)

Single-threaded accept loop: one connection handled start-to-finish before
the next is accepted, so "one upload at a time" is structural, not a lock.
"""
from __future__ import annotations

import json
import logging
import os
import re
import signal
import socket
import stat
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "gdrive-bridge"))
import ilag_sync  # noqa: E402 -- module object, so ENV_CANDIDATES can be overridden (same idiom as drive_upload_broker.py)
from ilag_mirror import list_folder  # noqa: E402 -- the ONLY arbitrary-scope-free listing this module ever does

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.logger import get_logger  # noqa: E402

# CEO 2026-09-10 carve-out, gdrive-filing skill's "My Picture & Videos." row.
DEFAULT_FOLDER_ID = "1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy"
DEFAULT_SOCKET_PATH = "/run/photoup/photo-broker.sock"
DEFAULT_MAX_UPLOAD_BYTES = 200 * 1024 * 1024   # 200 MiB
DEFAULT_MAX_REQUEST_BYTES = 64 * 1024          # 64 KiB -- one JSON line
DEFAULT_SOCKET_TIMEOUT = 30.0

# Below this length a "secret" is almost certainly an empty/placeholder
# value, not a real credential -- redacting it would just mangle ordinary
# short substrings in log lines and error text for no benefit.
_MIN_REDACTABLE_SECRET_LEN = 8

# Explicit ASCII-only digit class -- NOT \d, which under Python's default
# (non-re.ASCII) regex behaviour also matches Unicode decimal digits (e.g.
# U+0660 ARABIC-INDIC DIGIT ZERO). fullmatch() with fixed-width quantifiers
# also means an over-long string simply fails to match, no length check or
# ReDoS surface needed separately.
SUBFOLDER_RE = re.compile(r"^[0-9]{4}-[0-9]{2}$")


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

    env_path = Path(require("DRIVE_PHOTO_BROKER_ENV"))

    staging_root_raw = Path(require("DRIVE_PHOTO_BROKER_STAGING_ROOT"))
    try:
        staging_root = staging_root_raw.resolve(strict=True)
    except OSError as e:
        raise ConfigError(f"DRIVE_PHOTO_BROKER_STAGING_ROOT does not exist: {staging_root_raw} ({e})") from e
    if not staging_root.is_dir():
        raise ConfigError(f"DRIVE_PHOTO_BROKER_STAGING_ROOT is not a directory: {staging_root}")

    uids_raw = require("DRIVE_PHOTO_BROKER_ALLOWED_UIDS")
    try:
        allowed_uids = frozenset(int(u.strip()) for u in uids_raw.split(",") if u.strip())
    except ValueError as e:
        raise ConfigError(f"DRIVE_PHOTO_BROKER_ALLOWED_UIDS must be comma-separated integers, got {uids_raw!r}: {e}") from e
    if not allowed_uids:
        raise ConfigError("DRIVE_PHOTO_BROKER_ALLOWED_UIDS must name at least one uid")

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
        socket_path=Path(env.get("DRIVE_PHOTO_BROKER_SOCKET_PATH") or DEFAULT_SOCKET_PATH),
        allowed_uids=allowed_uids,
        staging_root=staging_root,
        folder_id=env.get("DRIVE_PHOTO_BROKER_FOLDER_ID") or DEFAULT_FOLDER_ID,
        max_upload_bytes=optional_int("DRIVE_PHOTO_BROKER_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES),
        max_request_bytes=optional_int("DRIVE_PHOTO_BROKER_MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES),
        socket_timeout=float(optional_int("DRIVE_PHOTO_BROKER_SOCKET_TIMEOUT", int(DEFAULT_SOCKET_TIMEOUT))),
    )


def apply_oauth_env_override(env_path: Path) -> None:
    """Point ilag_sync's OAuth loader at DRIVE_PHOTO_BROKER_ENV. Same override
    idiom drive_upload_broker.py uses for DRIVE_BROKER_ENV -- ilag_sync is
    shared, general-purpose Drive plumbing that otherwise hardcodes the
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
    `staging_root` -- otherwise (None, reason). Identical discipline to
    drive_upload_broker.py's function of the same name -- resolve first,
    then check, so a symlink inside staging_root pointing outside it is
    rejected, not followed."""
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


def _valid_subfolder(value: object) -> bool:
    return isinstance(value, str) and bool(SUBFOLDER_RE.fullmatch(value))


# --------------------------------------------------------------------------- month folder (the one new attack surface, scoped)

def find_month_folder(subfolder: str, parent_folder_id: str) -> str | None:
    """Look for a folder literally named `subfolder`, as a DIRECT CHILD of
    `parent_folder_id` -- never a recursive/arbitrary search. Only ever
    called with a `subfolder` that already passed `_valid_subfolder()`."""
    query = (
        f"'{parent_folder_id}' in parents and trashed = false and "
        "mimeType = 'application/vnd.google-apps.folder' and "
        f"name = '{subfolder}'"
    )
    res = ilag_sync.api(ilag_sync.DRIVE_FILES, params={
        "q": query, "fields": "files(id,name)", "pageSize": "10",
    }, timeout=30)
    for f in res.get("files", []):
        if f.get("name") == subfolder:
            return f.get("id")
    return None


def create_month_folder(subfolder: str, parent_folder_id: str) -> str:
    """Create `subfolder` as a DIRECT CHILD of `parent_folder_id`. Only ever
    called with a `subfolder` that already passed `_valid_subfolder()` --
    this is not a general-purpose folder-creation call, it accepts no path."""
    made = ilag_sync.api(
        ilag_sync.DRIVE_FILES, method="POST",
        params={"fields": "id,name"},
        data=json.dumps({
            "name": subfolder,
            "parents": [parent_folder_id],
            "mimeType": "application/vnd.google-apps.folder",
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    return made["id"]


def resolve_or_create_month_folder(subfolder: str, parent_folder_id: str) -> str:
    found = find_month_folder(subfolder, parent_folder_id)
    if found:
        return found
    return create_month_folder(subfolder, parent_folder_id)


# --------------------------------------------------------------------------- upload

def do_upload(local_path: Path, name: str, root_folder_id: str, subfolder: str | None) -> dict:
    if subfolder:
        try:
            dest_folder_id = resolve_or_create_month_folder(subfolder, root_folder_id)
        except Exception:
            return {"ok": False, "error": "could not resolve or create the month folder"}
    else:
        dest_folder_id = root_folder_id

    try:
        res = ilag_sync.upload(local_path, name, dest_folder_id)
    except Exception:
        return {"ok": False, "error": "upload to Drive failed"}

    # Never trust the upload call's own response -- re-list the resolved
    # destination folder fresh and require the name+size to actually be
    # there. Same verify-before-trust pattern as drive_upload_broker.py.
    try:
        fresh = list_folder(dest_folder_id)
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
    calls do_upload(). Deliberately reads ONLY "op"/"path"/"name"/"subfolder"
    off the parsed object -- any other key (folder_id, parent, destination,
    ...) is never looked at, so a client can put whatever it wants there and
    it is ignored, not refused-because-seen."""
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

    subfolder = req.get("subfolder")
    if subfolder is not None and not _valid_subfolder(subfolder):
        return {"ok": False, "error": "'subfolder' must match YYYY-MM exactly (ASCII digits only)"}

    return do_upload(resolved, name or resolved.name, cfg.folder_id, subfolder)


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
    os.chmod(socket_path, 0o660)  # group-only -- `photoup`'s own group, matches install-photo-broker.sh
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

    logger = get_logger("drive_photo_broker")
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
