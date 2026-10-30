#!/usr/bin/env python3
"""Push the Project Monitor payload to Console (org restructure P3-E, Agents-Core half).

Agents-Core builds `lib.portfolio.monitor_payload()` from the hub and POSTs it as JSON to
Console; Console never reads Agents-Core's files. The live-sessions publisher on Contabo runs
this once a minute (tools/live_sessions.py PortfolioPush); by hand:

    bash scripts/hub/org-python.sh tools/infisical_setup.py run MoonieX-Console prod -- \\
        .venv/bin/python tools/portfolio_push.py

Environment:
  PORTFOLIO_PUSH_TOKEN   required, the bearer token (Infisical MoonieX-Console/prod)
  PORTFOLIO_PUSH_URL     default https://terminal.mooniex.com; https only, http only on loopback
  ORG_DB_URL             the hub the payload is built from
  PORTFOLIO_MONITOR_V    unset: v2. 1/2/3/4: v1/v2/v3/v4 (deploy Console support first; docs/design/portfolio-monitor-v4.md)

POST <url>/api/portfolio/monitor, `Authorization: Bearer <token>`, 10 s timeout, urllib only.
Console answers 204 on a good push; 400, 401, 413 or 503 otherwise.

Exit: 0 pushed (204)
      2 not configured: token unset or malformed, or the URL is not https (nothing sent)
      3 the payload could not be built, the hub is down (nothing sent: Console then goes
        stale and answers 503, by design)
      4 Console refused (any status but 204, a redirect included) or could not be reached

One line on stderr per run, starting `portfolio_push: `. The token and the response body are
never printed, and a hub error is named by its class only (a psycopg message can name the host).
Module level is stdlib only; lib.portfolio loads inside the function that needs it.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_URL = "https://terminal.mooniex.com"
PATH = "/api/portfolio/monitor"
TIMEOUT_S = 10
EXIT_OK, EXIT_NOT_CONFIGURED, EXIT_NO_PAYLOAD, EXIT_REFUSED = 0, 2, 3, 4
PREFIX = "portfolio_push: "

# What Console's status codes mean (MoonieX-Console PR #34). Fixed text: the body is never read.
STATUS_WHY = {
    400: "payload rejected",
    401: "token rejected",
    413: "payload too large",
    503: "console is stale or its hub is down",
}
_TOKEN_RE = re.compile(r"[\x21-\x7e]{1,512}")     # printable, no whitespace: it goes into a header
_LOOPBACK = ("127.0.0.1", "localhost", "::1")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A 3xx is an answer, not a detour: urllib would resend the Authorization header to
    wherever Location points."""

    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _log(line: str) -> None:
    print(PREFIX + line, file=sys.stderr)


def endpoint(base: str | None = None) -> str | None:
    """The full push URL, or None when `base` would carry the token somewhere unsafe."""
    base = (base if base is not None else os.environ.get("PORTFOLIO_PUSH_URL") or DEFAULT_URL).strip()
    parts = urllib.parse.urlsplit(base)
    if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in _LOOPBACK):
        return base.rstrip("/") + PATH
    return None


def build_payload() -> dict:
    from lib import portfolio
    # v2 by default since Console 15399d5 stores v2 and still serves v1 to the old widget;
    # PORTFOLIO_MONITOR_V=1 pushes the v1 body again (ProjectTrack P4). PORTFOLIO_MONITOR_V=3 pushes v3
    # (docs/design/portfolio-monitor-v3.md): only after the Console that accepts v3 is deployed, or
    # the page goes stale.
    version = os.environ.get("PORTFOLIO_MONITOR_V")
    if version == "1":
        return portfolio.monitor_payload()
    return portfolio.monitor_payload(version=int(version) if version in ("3", "4") else 2)


def _post(url: str, token: str, body: bytes) -> int:
    """The HTTP status of the POST. An HTTPError is its status, its body never read."""
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "mooniex-agents-portfolio-push/1",    # urllib's default UA is blocked by some edges
    })
    try:
        with _OPENER.open(req, timeout=TIMEOUT_S) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        exc.close()
        return exc.code


def main() -> int:
    token = os.environ.get("PORTFOLIO_PUSH_TOKEN", "").strip()
    if not token:
        _log("PORTFOLIO_PUSH_TOKEN is unset, nothing sent")
        return EXIT_NOT_CONFIGURED
    if not _TOKEN_RE.fullmatch(token):
        _log("PORTFOLIO_PUSH_TOKEN is malformed, nothing sent")
        return EXIT_NOT_CONFIGURED
    url = endpoint()
    if url is None:
        _log("PORTFOLIO_PUSH_URL must be https (http only on loopback), nothing sent")
        return EXIT_NOT_CONFIGURED
    try:
        payload = build_payload()
    except Exception as exc:
        _log(f"no payload ({type(exc.__cause__ or exc).__name__}), nothing sent")
        return EXIT_NO_PAYLOAD
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    try:
        status = _post(url, token, body)
    except Exception as exc:
        _log(f"console unreachable ({type(exc.__cause__ or exc).__name__})")
        return EXIT_REFUSED
    if status == 204:
        _log(f"ok 204, {len(payload.get('projects', []))} projects, {len(body)} bytes")
        return EXIT_OK
    why = STATUS_WHY.get(status)
    _log(f"HTTP {status}" + (f" ({why})" if why else "") + (", expected 204" if status < 300 else ""))
    return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
