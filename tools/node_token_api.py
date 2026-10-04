#!/usr/bin/env python3
"""The hub's node-token service (Org Mesh W4.2b): how an approved node gets the Claude token.

    python -m tools.node_token_api --port 792 [--bind ADDR]

CEO ruling 2026-10-03: a node has no Infisical identity (Free allows 5 and they are all taken).
The hub reads the token from Infisical itself and hands it, sealed, to a node it has approved.
This is the one exception to "a service reads its secrets through `infisical run`" and it is for
nodes only: THIS process still gets its own values through `infisical run`
(deploy/node-token/org-node-token.service).

    GET /v1/token?host=H[&nonce=N]
                            200 {"ciphertext": <armored age>} sealed to hosts.pubkey of H.
                            The plaintext is {"v":1,"host":H,"name":"CLAUDE_CODE_OAUTH_TOKEN",
                            "value":...,"issued_at":...,"nonce":N}. N is 32 hex characters the
                            node made up for this request and is echoed only when sent;
                            node_token.py always sends one and refuses an answer without it, so
                            an old sealed answer cannot be played back to it. Sealing is the authentication: only H's
                            age identity (on H, root 0600) opens it, so any other caller learns
                            nothing, and the tailnet-only bind is the second wall.
                            403 {"error": code} unless the row is approved and its status is one
                            that issues: unknown_host (no such host, or it never joined through
                            hq_join), left (it is leaving or has left: for good, R4),
                            not_approved (approved_at is NULL), not_issuing (any other status,
                            for example pending_identity). `?name=` picks one of
                            infisical_setup.NODE_SECRET_NAMES; the default is the first.
                            503 {"error": "hub_unavailable"} when the hub database does not
                            answer: this service never decides from the read-only snapshot
                            lib.db falls back to (see _hub).
    GET /health             {"ok","token_loaded","db"}: booleans. Never a value, a length or
                            the last four characters. 200 when ok, 503 when not.

The token is never written to a file by this process, never logged, never in an error message.
The log line for a grant is `issued <NAME> to <host>`; everything else names a method, a path and
a status. It sees the hub through the Postgres role `org_node_token` (ORG_NODE_TOKEN_DB_URL,
deploy/node-token/org_node_token_role.sql): SELECT on host, status, pubkey and approved_at of
`hosts`, nothing else, so it cannot approve a node, write an event or read any other table. It
never falls back to ORG_DB_URL, the full role.

Binds only an address inside 100.64.0.0/10 (a tailnet address). 0.0.0.0, loopback, a LAN or a
public address, a hostname and IPv6 are refused at start (exit 2), the way tools/join_api.py
refuses what is not a docker bridge. Tests alone may bind loopback, with allow_loopback=True;
main() never passes it. Rate limited per source address (every request) and per host (a request
that will be granted: a refused one is charged to its source only, so a peer cannot spend a
victim host's window). The repo's lib.sealed and lib.db, ThreadingHTTPServer, HTTP/1.0.

Start-up refuses (exit 2) when a name in infisical_setup.NODE_SECRET_NAMES is missing from the
environment, naming the variable; and when ORG_NODE_TOKEN_DB_URL is missing.
"""
from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import logging
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db, db_pg, sealed  # noqa: E402
from tools import hq_join, infisical_setup  # noqa: E402
from tools.join_api import RateLimiter  # noqa: E402

_log = logging.getLogger("node_token_api")

DEFAULT_PORT = 792   # below 1024: only root (or CAP_NET_BIND_SERVICE) can take it while the service is down
TAILNET_NET = ipaddress.ip_network("100.64.0.0/10")   # Tailscale's CGNAT range
TOKEN_PATH = "/v1/token"
HEALTH_PATH = "/health"
NONCE_RE = re.compile(r"[0-9a-f]{32}")   # what node_token.py sends: 16 random bytes as hex
ORG_NODE_TOKEN_DB_ENV = "ORG_NODE_TOKEN_DB_URL"
BIND_ENV = "NODE_TOKEN_BIND"

# hosts.status values that issue. Fail closed: a status nobody listed here (offline, a new one)
# is refused as not_issuing until someone decides it should issue.
ISSUING_STATUSES = (hq_join.STATUS_READY, "online")
LEFT_STATUSES = (hq_join.STATUS_LEAVING, hq_join.STATUS_LEFT)

RATE_LIMIT = 30          # requests per source address, and per host, per RATE_WINDOW_S
RATE_WINDOW_S = 60.0
REQUEST_TIMEOUT_S = 15
DB_SLOTS = 2             # requests inside a database section at once (role org_node_token allows 3)
DB_WAIT_S = 2.0
MAX_VALUE_LEN = 4096     # a secret longer than this is a mistake in what was put in Infisical

_JSON = "application/json"
_DB_GATE = threading.BoundedSemaphore(DB_SLOTS)

Sealer = Callable[[str, bytes], bytes]

# What the `age` child gets as its whole environment. This process holds the role's DSN in ORG_DB_URL
# and (until main() pops them) the token and ORG_NODE_TOKEN_DB_URL; `age -r <recipient> -a` needs none
# of it, so it inherits none of it. No HOME: sealing to a recipient reads no file.
AGE_ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin"}


def _age_runner(argv: list, data: bytes, timeout: int) -> tuple:
    """lib.sealed's runner, with the child's environment replaced by AGE_ENV. The binary is found the
    way lib.sealed finds it (this process's PATH, then the usual bin dirs) and run by its full path."""
    argv = [sealed.find_age(argv[0]), *argv[1:]]
    try:
        p = subprocess.run(argv, input=data, capture_output=True, timeout=timeout, check=False, env=AGE_ENV)
    except subprocess.TimeoutExpired:
        raise sealed.SealError(f"age did not finish within {timeout} s") from None
    return p.returncode, p.stdout, p.stderr


def _seal(recipient: str, plaintext: bytes) -> bytes:
    return sealed.seal(recipient, plaintext, runner=_age_runner)


class _Refuse(Exception):
    """An answer to send instead of running the route. `code` never carries caller data."""

    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code


def _json(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def check_bind(addr: str, *, allow_loopback: bool = False) -> str:
    """`addr` if it is an IPv4 address inside 100.64.0.0/10, else ValueError. An allowlist: a typo,
    a hostname, 0.0.0.0, loopback, a LAN, a docker or a public address are refused, not bound.
    `allow_loopback` is for tests; main() never sets it."""
    try:
        ip = ipaddress.IPv4Address(addr)
    except ValueError:
        raise ValueError(f"bind address {addr!r} is not an IPv4 address (hostnames and IPv6 are refused)") from None
    if allow_loopback and ip.is_loopback:
        return addr
    if ip not in TAILNET_NET:
        raise ValueError(f"bind address {addr} refused: only the hub's tailnet address "
                         f"(inside {TAILNET_NET}) is allowed")
    return addr


def load_tokens(environ) -> dict[str, str]:
    """{name: value} for every name in infisical_setup.NODE_SECRET_NAMES, from `environ`.
    ValueError naming the VARIABLE (never a value) when one is missing, empty, too long or holds a
    control character: a service that starts with half a token would answer 200 with garbage."""
    out = {}
    for name in infisical_setup.NODE_SECRET_NAMES:
        value = environ.get(name)
        if not value or not value.strip():
            raise ValueError(f"{name} is not set (it comes from Infisical {infisical_setup.NODE_PROJECT} "
                             f"prod through `infisical_setup.py run`)")
        value = value.strip()
        if len(value) > MAX_VALUE_LEN or any(ord(c) < 33 or ord(c) == 127 for c in value):
            raise ValueError(f"{name} does not look like a token (too long, or it holds a space or "
                             f"a control character)")
        out[name] = value
    return out


def _release_conn() -> None:
    """Close this thread's pooled hub connection: lib.db keeps one per thread and this server
    starts a thread per request, and the role allows only 3."""
    url = db.pg_url()
    if url:
        db_pg.evict(url)


@contextlib.contextmanager
def _db_slot():
    """One of the DB_SLOTS for the body of the `with`; none within DB_WAIT_S is a 503. The
    thread's connection is closed before the slot is given back."""
    if not _DB_GATE.acquire(timeout=DB_WAIT_S):
        raise _Refuse(503, "busy")
    try:
        yield
    finally:
        try:
            _release_conn()
        finally:
            _DB_GATE.release()


@contextlib.contextmanager
def _hub():
    """The hub connection, inside one of the DB_SLOTS. The hub not answering is a 503
    `hub_unavailable`, never a decision taken from old data: when the hub does not answer,
    lib.db.get_conn() hands back a read-only SNAPSHOT of the ledger, and a snapshot that still
    shows `approved_at` and `online` for a host that has since left would issue the token. A
    snapshot connection, an unreachable hub and a connection that dies mid-query are all refused."""
    with _db_slot():
        try:
            with db.get_conn() as conn:
                if isinstance(conn, db._SnapshotConnection):
                    raise _Refuse(503, "hub_unavailable")
                yield conn
        except _Refuse:
            raise
        except Exception as exc:
            if isinstance(exc, db.HubUnavailable) or db_pg.is_operational_error(exc):
                raise _Refuse(503, "hub_unavailable") from None
            raise


def _loggable_host(host: object) -> str | None:
    return host if isinstance(host, str) and hq_join.HOST_RE.fullmatch(host) else None


def _query(path: str, allowed: tuple) -> dict[str, str]:
    """The query string as {name: value}: each name at most once, and only from `allowed`."""
    q = parse_qs(urlsplit(path).query, keep_blank_values=True)
    if any(k not in allowed or len(v) != 1 for k, v in q.items()):
        raise _Refuse(400, "bad_request")
    return {k: v[0] for k, v in q.items()}


def decide(row) -> str | None:
    """The refusal code for this hosts row, or None when it may be issued the token."""
    if row is None or not row["pubkey"]:
        return "unknown_host"
    if row["status"] in LEFT_STATUSES:
        return "left"
    if row["approved_at"] is None:
        return "not_approved"
    if row["status"] not in ISSUING_STATUSES:
        return "not_issuing"
    return None


def _route_token(h: "_Handler"):
    q = _query(h.path, ("host", "name", "nonce"))
    host = _loggable_host(q.get("host"))
    if host is None:
        raise _Refuse(400, "bad_host")
    name = q.get("name", infisical_setup.NODE_SECRET_NAMES[0])
    if name not in h.server.tokens:
        raise _Refuse(400, "bad_name")
    nonce = q.get("nonce")
    if nonce is not None and not NONCE_RE.fullmatch(nonce):
        raise _Refuse(400, "bad_nonce")
    with _hub() as conn:
        row = conn.execute("SELECT status, pubkey, approved_at FROM hosts WHERE host = ?",
                           (host,)).fetchone()
    refusal = decide(row)
    if refusal is not None:
        # A refused request is charged to its source address only (in _handle). Charging the
        # host named in it would let any tailnet peer spend a victim's whole window with
        # `host=victim`, and the victim's own node would then get 429s (exit 4).
        return 403, _json({"error": refusal}), _JSON, host
    if not h.server.host_limiter.allow(host):   # only a request that will be granted counts here
        raise _Refuse(429, "rate_limited")
    payload = {"v": 1, "host": host, "name": name, "value": h.server.tokens[name],
               "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if nonce is not None:   # sealed in with the value: node_token.py refuses an answer without its own
        payload["nonce"] = nonce
    try:
        armored = h.server.sealer(row["pubkey"], _json(payload)).decode("ascii")
    except Exception as exc:   # SealError and anything else: the class only, never a message
        _log.error("sealing for %s failed: %s", host, type(exc).__name__)
        raise _Refuse(500, "internal") from None
    _log.info("issued %s to %s", name, host)
    return 200, _json({"ciphertext": armored}), _JSON, host


def _route_health(h: "_Handler"):
    _query(h.path, ())
    try:
        with _hub() as conn:
            conn.execute("SELECT 1 FROM hosts LIMIT 1").fetchone()
        db_ok = True
    except _Refuse as r:
        if r.code != "hub_unavailable":   # `busy` is the gate being full, not the hub being down
            raise
        db_ok = False
    except Exception:
        db_ok = False
    loaded = bool(h.server.tokens) and all(h.server.tokens.values())
    ok = loaded and db_ok
    return (200 if ok else 503), _json({"ok": ok, "token_loaded": loaded, "db": db_ok}), _JSON, None


ROUTES = {("GET", TOKEN_PATH): _route_token, ("GET", HEALTH_PATH): _route_health}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"      # one request per connection
    default_request_version = "HTTP/1.0"   # Python <= 3.12 would start as 0.9 on a bad request line
    timeout = REQUEST_TIMEOUT_S

    def version_string(self) -> str:
        return "org-node-token"

    def log_message(self, *args) -> None:   # the base class logs the request line: caller data
        pass

    def send_error(self, code, message=None, explain=None) -> None:
        self._send(code, _json({"error": "bad_request"}), _JSON)

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
            pass   # the client went away
        self.close_connection = True

    def _handle(self) -> None:
        method, path, host = self.command, urlsplit(self.path).path, None
        route = ROUTES.get((method, path))
        extra = None
        try:
            if not self.server.source_limiter.allow(self.client_address[0]):
                raise _Refuse(429, "rate_limited")
            if route is None:
                raise _Refuse(404, "not_found")
            status, body, ctype, host = route(self)
        except _Refuse as r:
            status, body, ctype = r.status, _json({"error": r.code}), _JSON
            if status == 429:
                extra = {"Retry-After": str(int(RATE_WINDOW_S))}
            elif status == 503:
                extra = {"Retry-After": str(int(DB_WAIT_S))}
        except Exception as exc:   # never a message: a driver error can carry row values
            status = 500
            _log.error("%s %s: %s", method, path if route else "-", type(exc).__name__)
            body, ctype = _json({"error": "internal"}), _JSON
        # Logged BEFORE the reply, so a reader that has the answer can already see the line.
        # Only a route we serve is named: anything else is "-" (log injection).
        _log.info("%s %s %d host=%s", method, path if route else "-", status, host or "-")
        self._send(status, body, ctype, extra)

    do_GET = do_POST = do_HEAD = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _handle


class NodeTokenServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64   # the default 5 resets a burst of nodes restarting together (seen on macOS)

    def __init__(self, port: int = 0, *, tokens: dict[str, str], bind: str,
                 allow_loopback: bool = False, sealer: Sealer | None = None,
                 source_limiter: RateLimiter | None = None, host_limiter: RateLimiter | None = None):
        check_bind(bind, allow_loopback=allow_loopback)
        self.tokens = dict(tokens)
        self.sealer = sealer or _seal
        self.source_limiter = source_limiter or RateLimiter(RATE_LIMIT, RATE_WINDOW_S)
        self.host_limiter = host_limiter or RateLimiter(RATE_LIMIT, RATE_WINDOW_S)
        super().__init__((bind, port), _Handler)


def make_server(port: int = 0, **kw) -> NodeTokenServer:
    return NodeTokenServer(port, **kw)


def _preflight() -> None:
    """Fail at start, not on the first node's request, when `age` is not installed (every answer is
    sealed with it, so without it each request is a 500 while /health says ok), or when the hub
    schema is not there or the role cannot read it. The main thread's connection is closed again:
    it would hold one of the role's three for the life of the process."""
    sealed.find_age()   # SealError: main() prints its message, which names the package to install
    try:
        with _hub() as conn:
            conn.execute("SELECT host, status, pubkey, approved_at FROM hosts LIMIT 1").fetchall()
    except _Refuse as r:
        raise RuntimeError(r.code) from None   # main() prints the class only
    finally:
        _release_conn()


def main(argv: list[str] | None = None, environ=None) -> int:
    env = os.environ if environ is None else environ
    p = argparse.ArgumentParser(prog="node_token_api", description=__doc__.split("\n", 1)[0])
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--bind", default=env.get(BIND_ENV),
                   help=f"the hub's tailnet IPv4 address, inside {TAILNET_NET} (env {BIND_ENV}; "
                        f"deploy/node-token/bind-tailnet.sh sets it from `tailscale ip -4`)")
    args = p.parse_args(argv)
    try:
        if not args.bind:
            raise ValueError(f"no bind address: pass --bind or set {BIND_ENV} to the hub's tailnet address")
        check_bind(args.bind)
        tokens = load_tokens(env)
        db_url = (env.get(ORG_NODE_TOKEN_DB_ENV) or "").strip()
        if not db_url:
            raise ValueError(f"{ORG_NODE_TOKEN_DB_ENV} is not set (the DSN of the role org_node_token, "
                             f"Agents-Core prod /node-token); this service never uses ORG_DB_URL")
    except ValueError as exc:
        p.error(str(exc))   # exit 2, before the database is touched
    logging.basicConfig(level=logging.INFO, format="%(asctime)s node_token_api %(levelname)s %(message)s")
    os.environ["ORG_DB_URL"] = db_url   # the one variable lib.db reads; this process only
    # os.environ.pop edits this process's live environment and nothing more: the kernel keeps the
    # environment block it recorded at exec (readable under /proc by the same uid, or by root), so
    # those readers still see the values this service started with. What the pops buy is that nothing
    # the service starts from here inherits them (age gets AGE_ENV, not os.environ) and no later dump
    # of os.environ holds them.
    for name in infisical_setup.NODE_SECRET_NAMES:   # held in `tokens` now
        os.environ.pop(name, None)
    os.environ.pop(ORG_NODE_TOKEN_DB_ENV, None)
    try:
        _preflight()
        srv = make_server(args.port, tokens=tokens, bind=args.bind)
    except (OSError, ValueError, sealed.SealError) as exc:   # SealError: age missing; no caller data in it
        print(f"node_token_api: cannot start ({type(exc).__name__}: {str(exc)[:200]})", file=sys.stderr)
        return 1
    except Exception as exc:   # the hub database: a class name, never the driver's message
        print(f"node_token_api: hub database not ready ({type(exc).__name__})", file=sys.stderr)
        return 1
    _log.info("listening on %s:%d (serves %s)", srv.server_address[0], srv.server_address[1],
              ", ".join(sorted(tokens)))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
