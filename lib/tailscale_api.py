"""Tailscale control-plane client for the org join door (Org Mesh W4, CEO gate G3 part 2).

stdlib only. Two jobs, both through one OAuth client (client credentials):

    mint_authkey(host)   a one-use, pre-authorized, tag:org-node pre-auth key, valid 1 hour
    delete_device(host)  remove that node's device from the tailnet (`hq_join leave --live`)

    client = from_env(os.environ)        # None when the OAuth client is not configured
    client.mint_authkey("node-a")        # "tskey-auth-..."
    client.delete_device("node-a")       # True deleted, False already gone

Environment (Infisical, Agents-Core prod, folder /org-join):
    TAILSCALE_OAUTH_CLIENT_ID, TAILSCALE_OAUTH_CLIENT_SECRET   both or neither.
There is no environment variable for the base URL: the client secret is only ever posted to
BASE_URL unless a caller in code (a test) passes another.

Secrets: the client secret, the access token and a minted key are never put in an exception
message, a log line or an argument list. An error carries the operation, the HTTP status and
the `message` / `error` text Tailscale sent (cut, printable ASCII, with anything that looks like
a key or equals a secret held here replaced by [redacted]), and nothing else of the response.
A network failure carries the exception class name only.

deploy/join/README.md "Tailscale pre-auth key" and docs/ops/hq-join.md carry the operator view.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Mapping

from lib import config

BASE_URL = "https://api.tailscale.com"
TAG = "tag:org-node"
KEY_TTL_S = 3600           # the pre-auth key is good for one hour and one use
TOKEN_SKEW_S = 60          # a cached access token is dropped this long before it expires
TIMEOUT_S = 10             # per request; a mint is at most two (token, key)
MAX_BODY = 4 * 1024 * 1024  # more than any tailnet's device list; a bigger answer is refused

ID_ENV = "TAILSCALE_OAUTH_CLIENT_ID"
SECRET_ENV = "TAILSCALE_OAUTH_CLIENT_SECRET"

_KEY_RE = re.compile(r"[\x21-\x7e]{1,200}")          # what a pre-auth key looks like (join_api checks too)
_DEVICE_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")  # goes into a URL path: nothing else gets through
_SECRETISH_RE = re.compile(r"tskey-[A-Za-z0-9_-]+")
_ERR_CHARS = 160

# opener(request, timeout=...) -> a response: a context manager with .status and .read(n).
Opener = Callable[..., object]


class TailscaleError(Exception):
    """A refusal or a failure. `status` is the HTTP status, or None when there was none."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """The bearer token must not follow a redirect to another host."""

    def redirect_request(self, *args, **kwargs):
        return None


def _default_opener(request, timeout: float):
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


class TailscaleClient:
    def __init__(self, client_id: str, client_secret: str, *, base_url: str = BASE_URL,
                 opener: Opener | None = None, clock: Callable[[], float] = time.monotonic,
                 timeout: float = TIMEOUT_S):
        if not client_id or not client_secret:
            raise ValueError("a Tailscale OAuth client id and secret are both required")
        self._id = client_id
        self._secret = client_secret
        self._base = base_url.rstrip("/")
        self._open = opener or _default_opener
        self._clock = clock
        self._timeout = timeout
        self._lock = threading.Lock()
        self._token: str | None = None
        self._token_until = 0.0

    def __repr__(self) -> str:   # never the secret, even in a traceback
        return "TailscaleClient()"

    # ------------------------------------------------------------ plumbing

    def _scrub(self, text: str) -> str:
        for secret in (self._secret, self._token):
            if secret:
                text = text.replace(secret, "[redacted]")
        text = _SECRETISH_RE.sub("[redacted]", text)
        return "".join(c if " " <= c <= "~" else "?" for c in text)[:_ERR_CHARS]

    def _error(self, op: str, status: int | None, raw: bytes) -> TailscaleError:
        """HTTP status + Tailscale's own `message` / `error` string. Nothing else of the body."""
        text = ""
        try:
            body = json.loads(raw.decode("utf-8"))
            for field in ("message", "error_description", "error"):
                if isinstance(body, dict) and isinstance(body.get(field), str):
                    text = body[field]
                    break
        except (ValueError, UnicodeDecodeError):
            pass
        text = self._scrub(text)
        return TailscaleError(f"tailscale {op} failed: HTTP {status}" + (f": {text}" if text else ""), status)

    def _send(self, op: str, request) -> tuple[int, bytes]:
        """(status, body) for a 2xx; TailscaleError for everything else, 404 included."""
        try:
            with self._open(request, timeout=self._timeout) as resp:
                status, raw = resp.status, resp.read(MAX_BODY + 1)
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read(MAX_BODY)
            except Exception:
                raw = b""
            raise self._error(op, exc.code, raw) from None
        except Exception as exc:   # URLError carries the target host and a reason: class name only
            raise TailscaleError(f"tailscale {op} failed: {type(exc).__name__}") from None
        if len(raw) > MAX_BODY:
            raise TailscaleError(f"tailscale {op} failed: answer too large", status)
        if not 200 <= status < 300:
            raise self._error(op, status, raw)
        return status, raw

    def _json(self, op: str, raw: bytes):
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise TailscaleError(f"tailscale {op} failed: answer is not JSON") from None

    def access_token(self) -> str:
        """The OAuth access token, fetched once and reused until TOKEN_SKEW_S before it expires."""
        with self._lock:
            if self._token and self._clock() < self._token_until:
                return self._token
            form = urllib.parse.urlencode({"client_id": self._id, "client_secret": self._secret,
                                           "grant_type": "client_credentials"}).encode("ascii")
            req = urllib.request.Request(
                self._base + "/api/v2/oauth/token", data=form, method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
            _, raw = self._send("token", req)
            body = self._json("token", raw)
            token = body.get("access_token") if isinstance(body, dict) else None
            if not isinstance(token, str) or not token:
                raise TailscaleError("tailscale token failed: no access_token in the answer")
            ttl = body.get("expires_in")
            ttl = ttl if isinstance(ttl, (int, float)) and not isinstance(ttl, bool) else 0
            self._token = token
            self._token_until = self._clock() + max(ttl - TOKEN_SKEW_S, 0)
            return token

    def _forget_token(self) -> None:
        with self._lock:
            self._token, self._token_until = None, 0.0

    def _api(self, op: str, method: str, path: str, payload: dict | None = None) -> tuple[int, bytes]:
        """One authorised call. A 401 means the cached token died early: fetch a new one, once."""
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        for attempt in (0, 1):
            headers = {"Authorization": "Bearer " + self.access_token(), "Accept": "application/json"}
            if data is not None:
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(self._base + path, data=data, method=method, headers=headers)
            try:
                return self._send(op, req)
            except TailscaleError as exc:
                if exc.status == 401 and attempt == 0:
                    self._forget_token()
                    continue
                raise
        raise AssertionError("unreachable")  # pragma: no cover

    # ------------------------------------------------------------ the two jobs

    def mint_authkey(self, host: str) -> str:
        """A one-use, pre-authorized, non-ephemeral, tag:org-node pre-auth key for `host`, 1 hour."""
        _check_host(host)
        body = {"capabilities": {"devices": {"create": {
                    "reusable": False, "ephemeral": False, "preauthorized": True, "tags": [TAG]}}},
                "expirySeconds": KEY_TTL_S, "description": f"org-node:{host}"}
        _, raw = self._api("mint key", "POST", "/api/v2/tailnet/-/keys", body)
        key = self._json("mint key", raw)
        key = key.get("key") if isinstance(key, dict) else None
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            raise TailscaleError("tailscale mint key failed: no usable key in the answer")
        return key

    def delete_device(self, host: str) -> bool:
        """Remove the tailnet device of `host`. True when one was deleted, False when there was none
        (never joined, or already gone: a re-run converges).

        Only a device whose hostname is `host` AND whose tags include tag:org-node is ever touched.
        An untagged device, or one with other tags only, is not this node. Two matches are refused,
        not guessed at."""
        _check_host(host)
        _, raw = self._api("list devices", "GET", "/api/v2/tailnet/-/devices")
        listed = self._json("list devices", raw)
        devices = listed.get("devices") if isinstance(listed, dict) else None
        if not isinstance(devices, list):
            raise TailscaleError("tailscale list devices failed: no device list in the answer")
        match = [d for d in devices if isinstance(d, dict)
                 and isinstance(d.get("hostname"), str) and d["hostname"].lower() == host
                 and isinstance(d.get("tags"), list) and TAG in d["tags"]]
        if not match:
            return False
        if len(match) > 1:
            raise TailscaleError(f"tailscale delete device refused: {len(match)} devices named "
                                 f"{host} carry {TAG}; remove the stale one in the admin console")
        dev_id = match[0].get("id")
        if not isinstance(dev_id, str) or not _DEVICE_ID_RE.fullmatch(dev_id):
            raise TailscaleError("tailscale delete device failed: the device has no usable id")
        try:
            self._api("delete device", "DELETE", "/api/v2/device/" + urllib.parse.quote(dev_id, safe=""))
        except TailscaleError as exc:
            if exc.status == 404:      # gone between the list and the delete
                return False
            raise
        return True


def _check_host(host: object) -> None:
    if not isinstance(host, str) or not config.HOST_NAME_RE.fullmatch(host):
        raise ValueError("bad host name")   # never echoed: it may be caller data


def from_env(environ: Mapping[str, str], **kw) -> TailscaleClient | None:
    """A client from TAILSCALE_OAUTH_CLIENT_ID / _SECRET in `environ`, or None when neither is set.
    One without the other is a ValueError naming the variables (never a value): a half
    configuration must not look like "not configured". `kw` goes to TailscaleClient (tests)."""
    cid = (environ.get(ID_ENV) or "").strip()
    secret = (environ.get(SECRET_ENV) or "").strip()
    if not cid and not secret:
        return None
    if not cid or not secret:
        missing = ID_ENV if not cid else SECRET_ENV
        raise ValueError(f"{ID_ENV} and {SECRET_ENV} must be set together; {missing} is missing")
    return TailscaleClient(cid, secret, **kw)
