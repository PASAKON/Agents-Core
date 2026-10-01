#!/usr/bin/env python3
"""The hub's public join endpoint (Org Mesh W4.3): what `join.sh` / `join.ps1` talk to.

    python -m tools.join_api --port 8791 [--bind ADDR] [--public-url https://<hub>]

Runs on Contabo as the system user `org-join` with ONE secret in its environment, the DSN of the
Postgres role `org_join` (ORG_JOIN_DB_URL, from the /org-join folder of Agents-Core prod; see
deploy/join/org-join.service and deploy/join/org_join_role.sql). stdlib only,
ThreadingHTTPServer. It binds 127.0.0.1 unless told otherwise, and `--bind` (env
JOIN_API_BIND) takes ONLY a loopback address or one inside 172.16.0.0/12 (a docker bridge):
never 0.0.0.0, never a public or other private address (Org Mesh W4.5: traefik reaches it
through a socat container on the bridge, deploy/join/docker-compose.join-proxy.yml).

Routes, all under /org-join/ (every other path, and every other method on these, is 404):

    GET  join.sh, join.ps1   deploy/join/<file> as text/plain. No secret, no hub-internal
                             address. The one placeholder, @@ORG_JOIN_HUB@@, becomes the
                             public hub URL so `curl .../join.sh | sh` knows where it came from.
    POST accept              {token, host, os, hq_root, pubkey, deploy_pubkey?}
                             -> hq_join.accept(). 200 {host, status}. Plus
                             `tailscale_authkey` when a TailscaleMinter is configured.
    POST sealed              {host, token}. 202 {status: pending} until the host is
                             identity_ready, then 200 {status: ready, ciphertext}. Allowed
                             only for the token that joined that host, within 24 h of its use.
                             EVERY other case is the same 403: no oracle.

Hardening: body at most 8 KB and JSON only, an in-memory per-IP rate limit, no CORS, no
directory serving. The log line is method, path, status and host, never a body, a token,
a ciphertext or a key. An exception is logged by class name only.

Database load (W4.6, F11): every request opens its own hub connection, and the hub's Postgres is
shared with the whole org. At most DB_SLOTS requests are inside their database section at once;
one that cannot get a slot within DB_WAIT_S seconds is answered 503 {"error":"busy"}. The body
is read and its shape checked BEFORE the slot is taken, so a slow client never holds one, and
the 503 depends on load only, never on the token.

Database role (W4.6c, F3): the endpoint is public, so it connects as the least-privileged role
`org_join` (column grants on three tables, CONNECTION LIMIT 5), never as the full hub role `org`.
It reads ORG_JOIN_DB_URL. Only when that is unset and JOIN_API_ALLOW_ORG_ROLE=1 does it fall back to
ORG_DB_URL, with a one-line warning; without the flag it refuses to start.

The TailscaleMinter is an injectable `host -> pre-auth key` callable. main() wires
lib.tailscale_api when TAILSCALE_OAUTH_CLIENT_ID and TAILSCALE_OAUTH_CLIENT_SECRET are both in
the environment (the /org-join folder the unit already injects); one without the other refuses
to start. Without them the field is absent and join.sh requires the machine to be on the
tailnet already. A minter that raises does not fail the accept: no key field, one warning
with the exception's class name.
"""
from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import logging
import os
import re
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db, db_pg, tailscale_api  # noqa: E402
from tools import hq_join  # noqa: E402

_log = logging.getLogger("join_api")

BIND_HOST = "127.0.0.1"  # the default; `--bind` may move it onto a docker bridge, see check_bind
DOCKER_NET = ipaddress.ip_network("172.16.0.0/12")  # every bridge docker hands out by default
DEFAULT_PORT = 8791
PREFIX = "/org-join/"
SCRIPTS_DIR = ROOT / "deploy" / "join"
SCRIPT_NAMES = ("join.sh", "join.ps1")
HUB_PLACEHOLDER = b"@@ORG_JOIN_HUB@@"

MAX_BODY = 8 * 1024
RATE_LIMIT = 30          # requests per client per RATE_WINDOW_S
RATE_WINDOW_S = 60.0
SEALED_WINDOW = timedelta(hours=24)
DRAIN_MAX = 64 * 1024    # an oversized body is read (and dropped) up to this, so close() is not an RST
REQUEST_TIMEOUT_S = 15
DB_SLOTS = 4             # requests inside a database section at the same time, whole process
#                          (the role org_join allows 5 connections: the four slots plus one spare)
DB_WAIT_S = 2.0          # how long a request waits for a slot before it is answered 503

# Shapes checked before anything is built from them.
_ORIGIN_RE = re.compile(r"https?://[A-Za-z0-9.-]{1,253}(?::[0-9]{1,5})?")
_HOSTHDR_RE = re.compile(r"[A-Za-z0-9.-]{1,253}(?::[0-9]{1,5})?")
_AUTHKEY_RE = re.compile(r"[\x21-\x7e]{1,200}")

# host -> one-use, pre-authorized, tagged Tailscale pre-auth key (lib.tailscale_api.mint_authkey).
TailscaleMinter = Callable[[str], str]

_JSON = "application/json"


class _Refuse(Exception):
    """An answer to send instead of running the route. `code` is the machine-readable
    part of the body; it never carries caller data."""

    def __init__(self, status: int, code: str, drain: int = 0):
        super().__init__(code)
        self.status = status
        self.code = code
        self.drain = drain


# One answer for every token or host refusal, so nothing tells a caller which check failed.
_REFUSED = (403, "refused")

# Module level, so every server and every handler thread in this process shares the same four.
_DB_GATE = threading.BoundedSemaphore(DB_SLOTS)


def _release_conn() -> None:
    """Close this thread's pooled hub connection. lib.db keeps one per thread and never closes it,
    and this server starts a thread per request; the role org_join allows 5 connections, so a
    connection must not outlive the slot it was used in."""
    url = db.pg_url()
    if url:
        db_pg.evict(url)


@contextlib.contextmanager
def _db_slot():
    """Hold one of the DB_SLOTS for the body of the `with`. No slot within DB_WAIT_S is a 503.
    The thread's connection is closed before the slot is given back."""
    if not _DB_GATE.acquire(timeout=DB_WAIT_S):
        raise _Refuse(503, "busy")
    try:
        yield
    finally:
        try:
            _release_conn()
        finally:
            _DB_GATE.release()


def _json(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def check_bind(addr: str) -> str:
    """`addr` if it is an IPv4 loopback or inside 172.16.0.0/12, else ValueError.

    The join endpoint sits in front of join tokens and sealed secrets, so the address is an
    allowlist and not a blocklist: a typo, a hostname, 0.0.0.0, :: (this server is AF_INET,
    so no IPv6 at all), a public address or a LAN address are all refused rather than bound.
    """
    try:
        ip = ipaddress.IPv4Address(addr)
    except ValueError:
        raise ValueError(f"bind address {addr!r} is not an IPv4 address (hostnames and IPv6 are refused)") from None
    if not (ip.is_loopback or ip in DOCKER_NET):
        raise ValueError(f"bind address {addr} refused: only 127.0.0.0/8 or 172.16.0.0/12 (a docker bridge) is allowed")
    return addr


# ---------------------------------------------------------------- rate limit

class RateLimiter:
    """At most `limit` hits per `window_s` per key. In memory: a restart forgets it,
    and that is fine for an abuse brake (the tokens are 256 bits)."""

    def __init__(self, limit: int = RATE_LIMIT, window_s: float = RATE_WINDOW_S,
                 clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window_s = window_s
        self._clock = clock
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            if len(self._hits) > 4096:  # never grow without bound under a spray of addresses
                self._hits = {k: q for k, q in self._hits.items()
                              if q and now - q[-1] < self.window_s}
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= self.window_s:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


# ---------------------------------------------------------------- the routes

def _field(body: dict, name: str, *, optional: bool = False):
    v = body.get(name)
    if v is None and optional:
        return None
    if not isinstance(v, str) or not v:
        raise _Refuse(400, "bad_arg")
    return v


def _loggable_host(host: object) -> str | None:
    """A caller-supplied name reaches the log only if it is a well-formed host name."""
    return host if isinstance(host, str) and hq_join.HOST_RE.fullmatch(host) else None


def _route_script(h: "_Handler", name: str):
    body = (SCRIPTS_DIR / name).read_bytes()
    hub = h.server.hub_url(h.headers.get("Host"))
    return 200, body.replace(HUB_PLACEHOLDER, hub.encode("ascii")), "text/plain; charset=utf-8", None


def _route_accept(h: "_Handler"):
    body = h.read_json()
    token, host = _field(body, "token"), _field(body, "host")
    log_host = _loggable_host(host)
    args = (token, host, _field(body, "os"), _field(body, "hq_root"), _field(body, "pubkey"))
    deploy = _field(body, "deploy_pubkey", optional=True)
    try:
        with _db_slot():
            res = hq_join.accept(*args, deploy_pubkey=deploy)
    except hq_join.JoinError as exc:
        if exc.code == "bad_arg":
            return 400, _json({"error": "bad_arg", "message": exc.message}), _JSON, log_host
        if exc.code in ("host_in_use", "conflict"):
            return 409, _json({"error": exc.code}), _JSON, log_host
        # unknown_token, wrong_host, already_used, expired: one answer
        return 403, _json({"error": _REFUSED[1]}), _JSON, log_host
    out = {"host": res["host"], "status": res["status"]}
    if h.server.minter is not None:
        try:
            key = h.server.minter(host)
            if isinstance(key, str) and _AUTHKEY_RE.fullmatch(key):
                out["tailscale_authkey"] = key
        except Exception as exc:  # the node joined; it just gets no key, and says so
            _log.warning("tailscale minter failed for %s: %s", log_host, type(exc).__name__)
    return 200, _json(out), _JSON, log_host


def _route_sealed(h: "_Handler"):
    body = h.read_json()
    host, token = body.get("host"), body.get("token")
    log_host = _loggable_host(host)
    if log_host is None or not isinstance(token, str) or not hq_join.TOKEN_RE.fullmatch(token):
        raise _Refuse(*_REFUSED)
    with _db_slot(), db.get_conn() as conn:
        tok = conn.execute("SELECT host, used_at FROM join_tokens WHERE token_hash = ?",
                           (hq_join.hash_token(token),)).fetchone()
        row = conn.execute("SELECT status FROM hosts WHERE host = ?", (log_host,)).fetchone()
    if tok is None or tok["host"] != log_host or tok["used_at"] is None or row is None:
        raise _Refuse(*_REFUSED)
    try:
        used = datetime.fromisoformat(tok["used_at"])
    except ValueError:
        raise _Refuse(*_REFUSED) from None
    if datetime.now(timezone.utc) - used >= SEALED_WINDOW or row["status"] == hq_join.STATUS_LEFT:
        raise _Refuse(*_REFUSED)
    if row["status"] == hq_join.STATUS_PENDING:
        return 202, _json({"status": "pending"}), _JSON, log_host
    try:
        with _db_slot():
            ciphertext = hq_join.sealed_ciphertext(log_host)
    except hq_join.JoinError:  # no live ciphertext (revoked, or never stored)
        raise _Refuse(*_REFUSED) from None
    return 200, _json({"status": "ready", "ciphertext": ciphertext}), _JSON, log_host


ROUTES: dict = {("GET", PREFIX + n): (lambda h, n=n: _route_script(h, n)) for n in SCRIPT_NAMES}
ROUTES[("POST", PREFIX + "accept")] = _route_accept
ROUTES[("POST", PREFIX + "sealed")] = _route_sealed


# ---------------------------------------------------------------- the server

class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # one request per connection: no unread body is ever a second request
    # Python <= 3.12 starts every request as HTTP/0.9, and send_error on a request line it
    # cannot parse then writes no status line at all. Contabo runs 3.12: answer 1.0 always.
    default_request_version = "HTTP/1.0"
    timeout = REQUEST_TIMEOUT_S

    def version_string(self) -> str:
        return "org-join"

    # Nothing the base class logs is wanted: it prints the request line, which is caller data.
    def log_message(self, *args) -> None:
        pass

    def send_error(self, code, message=None, explain=None) -> None:  # malformed line, bad version, ...
        self._send(code, _json({"error": "bad_request"}), _JSON)

    def _client_key(self) -> str:
        if self.server.trust_forwarded:
            # Behind our own proxy the peer is always the proxy, so its last X-Forwarded-For
            # entry (the one it appended) is the caller. Anything else falls back to the peer.
            last = (self.headers.get("X-Forwarded-For") or "").split(",")[-1].strip()
            try:
                return str(ipaddress.ip_address(last))
            except ValueError:
                pass
        return self.client_address[0]

    def read_json(self) -> dict:
        if "Transfer-Encoding" in self.headers:
            raise _Refuse(411, "length_required")
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            raise _Refuse(415, "json_only")
        raw_len = self.headers.get("Content-Length")
        if raw_len is None:
            raise _Refuse(411, "length_required")
        if not (raw_len.isascii() and raw_len.isdigit()) or int(raw_len) == 0:
            raise _Refuse(400, "bad_request")
        n = int(raw_len)
        if n > MAX_BODY:
            raise _Refuse(413, "too_large", drain=n)
        raw = self.rfile.read(n)
        if len(raw) != n:
            raise _Refuse(400, "bad_request")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise _Refuse(400, "bad_request") from None
        if not isinstance(data, dict):
            raise _Refuse(400, "bad_request")
        return data

    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            pass  # the client went away; nothing to tell it
        self.close_connection = True

    def _drain(self, n: int) -> None:
        """Read and drop what an oversized request is still sending, briefly, so closing
        the socket does not reset a client that has not read our 413 yet."""
        try:
            self.connection.settimeout(1)
            left = min(n, DRAIN_MAX)
            while left > 0:
                chunk = self.rfile.read(min(left, 4096))
                if not chunk:
                    break
                left -= len(chunk)
        except OSError:
            pass

    def _handle(self) -> None:
        method, path, host, drain = self.command, urlsplit(self.path).path, None, 0
        route = ROUTES.get((method, path))
        try:
            if not self.server.limiter.allow(self._client_key()):
                status = 429
                self._send(429, _json({"error": "rate_limited"}), _JSON,
                           {"Retry-After": str(int(self.server.limiter.window_s))})
            elif route is None:
                status = 404
                self._send(404, _json({"error": "not_found"}), _JSON)
            else:
                status, body, ctype, host = route(self)
                self._send(status, body, ctype)
        except _Refuse as r:
            status, drain = r.status, r.drain
            self._send(status, _json({"error": r.code}), _JSON,
                       {"Retry-After": str(int(DB_WAIT_S))} if status == 503 else None)
        except Exception as exc:  # never a message: a driver error can carry row values
            status = 500
            _log.error("%s %s: %s", method, path if route else "-", type(exc).__name__)
            self._send(500, _json({"error": "internal"}), _JSON)
        # Only a route we serve is named; anything else is "-" (log injection, a token in a URL).
        _log.info("%s %s %d host=%s", method, path if route else "-", status, host or "-")
        if drain:
            self._drain(drain)

    # Every method goes through the same gate, so an unknown one is a 404 and not a 501 page.
    do_GET = do_POST = do_HEAD = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _handle


class JoinServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int = 0, *, minter: TailscaleMinter | None = None,
                 public_url: str | None = None, trust_forwarded: bool = False,
                 limiter: RateLimiter | None = None, bind: str = BIND_HOST):
        check_bind(bind)
        if public_url is not None:
            public_url = public_url.rstrip("/")
            if not _ORIGIN_RE.fullmatch(public_url):
                raise ValueError("public URL must be http(s)://host[:port], no path")
        self.minter = minter
        self.public_url = public_url
        self.trust_forwarded = trust_forwarded
        self.limiter = limiter or RateLimiter()
        super().__init__((bind, port), _Handler)

    def hub_url(self, host_header: str | None) -> str:
        """The URL join.sh is told it was fetched from. The configured public URL wins; else
        the Host header of THIS request, if it is only host characters. Empty = the script
        then requires --hub."""
        if self.public_url:
            return self.public_url + "/org-join"
        if host_header and _HOSTHDR_RE.fullmatch(host_header):
            return f"http://{host_header}/org-join"
        return ""


def make_server(port: int = 0, **kw) -> JoinServer:
    return JoinServer(port, **kw)


def _preflight() -> None:
    """Fail at start, not on the first caller's request, when the hub schema is not there (or the
    role cannot read it). The main thread's connection is closed again: it would sit open for
    the life of the process and use one of the role's five."""
    try:
        with db.get_conn() as conn:
            for table in ("join_tokens", "hosts", "node_secrets"):
                conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
    finally:
        _release_conn()


ORG_JOIN_DB_ENV = "ORG_JOIN_DB_URL"
ALLOW_ORG_ROLE_ENV = "JOIN_API_ALLOW_ORG_ROLE"


def choose_db_url(environ) -> tuple[str | None, str | None]:
    """(url, warning) for the hub database, from `environ`; ValueError when none may be used.

    ORG_JOIN_DB_URL, the role org_join, wins. Without it the full-role ORG_DB_URL is used only
    when JOIN_API_ALLOW_ORG_ROLE=1, and then with a warning: a public endpoint must not hold
    the org role by accident. With neither set (tests, a laptop) url is None and lib.db keeps
    its own default, the local SQLite file. The messages name variables, never a value."""
    def get(name: str) -> str:
        return (environ.get(name) or "").strip()

    join_url, org_url = get(ORG_JOIN_DB_ENV), get("ORG_DB_URL")
    if join_url:
        note = ("ORG_DB_URL is also set in this environment and is ignored: this endpoint should "
                "not hold the org role at all") if org_url else None
        return join_url, note
    if not org_url:
        return None, None
    if get(ALLOW_ORG_ROLE_ENV) != "1":
        raise ValueError(f"{ORG_JOIN_DB_ENV} is not set and this endpoint will not fall back to "
                         f"ORG_DB_URL (the full org role) unless {ALLOW_ORG_ROLE_ENV}=1")
    return org_url, (f"{ORG_JOIN_DB_ENV} is not set: connecting with ORG_DB_URL, the full org role, "
                     f"because {ALLOW_ORG_ROLE_ENV}=1 (least privilege is off)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="join_api", description=__doc__.split("\n", 1)[0])
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--bind", default=os.environ.get("JOIN_API_BIND") or BIND_HOST,
                   help="IPv4 address to listen on: loopback or inside 172.16.0.0/12 only "
                        f"(env JOIN_API_BIND, default {BIND_HOST})")
    p.add_argument("--public-url", default=os.environ.get("JOIN_API_PUBLIC_URL"),
                   help="https://<hub> as a joining machine sees it (env JOIN_API_PUBLIC_URL)")
    p.add_argument("--trust-forwarded-for", action="store_true",
                   default=os.environ.get("JOIN_API_TRUST_FORWARDED") == "1",
                   help="rate-limit on the last X-Forwarded-For entry (only behind our own proxy)")
    args = p.parse_args(argv)
    try:
        check_bind(args.bind)
        db_url, db_warning = choose_db_url(os.environ)
        ts_client = tailscale_api.from_env(os.environ)  # None = not configured; half of it = ValueError
    except ValueError as exc:
        p.error(str(exc))  # exit 2, before the database is touched
    logging.basicConfig(level=logging.INFO, format="%(asctime)s join_api %(levelname)s %(message)s")
    if db_url:
        os.environ["ORG_DB_URL"] = db_url  # the one variable lib.db reads; this process only
    if db_warning:
        _log.warning("%s", db_warning)
    try:
        _preflight()
        srv = make_server(args.port, public_url=args.public_url,
                          trust_forwarded=args.trust_forwarded_for, bind=args.bind,
                          minter=ts_client.mint_authkey if ts_client else None)
    except (OSError, ValueError) as exc:
        print(f"join_api: cannot start ({type(exc).__name__}: {str(exc)[:200]})", file=sys.stderr)
        return 1
    except Exception as exc:  # the hub database: a class name, never the driver's message
        print(f"join_api: hub database not ready ({type(exc).__name__})", file=sys.stderr)
        return 1
    _log.info("listening on %s:%d (minter %s)", srv.server_address[0], srv.server_address[1],
              "wired" if srv.minter else "not wired")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
