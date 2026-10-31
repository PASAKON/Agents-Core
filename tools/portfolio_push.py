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
  PORTFOLIO_MONITOR_V    unset: v2. 1/2/3/4: v1/v2/v3/v4 (deploy Console support first; docs/design/portfolio-monitor-v4.md).
                         The file state/portfolio_monitor.version (one line, 1-4) wins over it: ensure_publisher respawns
                         the publisher from hooks without this env, and the file survives that.

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

After a successful push, collect up to 20 CEO items/receipts. Delivery state is private in
state/portfolio_collector.json; touch state/portfolio_collector.off to stop collection.
--dry-run fetches pending items and prints action/project/recipient only, without pushing,
writing mail, waking, unblocking, or acknowledging. CEO message text is never printed.
"""
from __future__ import annotations

import json
import argparse
import fcntl
import os
import re
import sys
import tempfile
import time
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
COLLECTOR_STATE = ROOT / "state" / "portfolio_collector.json"
COLLECTOR_OFF = ROOT / "state" / "portfolio_collector.off"
COLLECTOR_CAP = 20
COLLECTOR_BUDGET_S = 15  # share the publisher's 30-second child timeout with the push
SENTENCES = {
    "done": "CEO pressed ทำแล้ว on your blocker: it is unblocked, continue",
    "report": "CEO requested a progress report: report the current status and next step.",
    "resume": "CEO requested that you resume this project: continue the next step now.",
    "lead": "CEO requested leadership on this project: take ownership and drive the next step.",
}


def _collector_request(base, token, path, body=None, *, timeout=TIMEOUT_S):
    req = urllib.request.Request(base + "/api/portfolio/" + path,
        data=None if body is None else json.dumps(body).encode(),
        method="GET" if body is None else "POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "mooniex-agents-portfolio-push/1"})
    try:
        response = _OPENER.open(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        # An ack may have committed before its response was lost.
        if body is not None and path.endswith("/ack") and exc.code == 409:
            exc.close()
            return None
        raise
    with response as resp:
        if body is not None:
            return None
        raw = resp.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise ValueError("collector response too large")
        items = json.loads(raw)
        if not isinstance(items, list):
            raise ValueError("collector response is not a list")
        return items


def _save_collector(state):
    fd, tmp = tempfile.mkstemp(dir=COLLECTOR_STATE.parent, prefix=".portfolio_collector.")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(state, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, COLLECTOR_STATE)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _wake_receipt(receipt, state):
    from tools import mail_wake
    if not receipt.get("wake_pending"):
        return
    result = mail_wake.wake(Path(receipt["letter"]).parent.name, "CEO-PORTFOLIO")
    receipt["ack"]["woke"] = bool(result.get("woke"))
    # Fixed reason: transport errors must not leak private data to Console.
    receipt["ack"]["reason"] = "woke" if receipt["ack"]["woke"] else "no live session reached"
    receipt["wake_pending"] = False
    _save_collector(state)


def _collector_round(base, token, *, dry_run=False):
    from lib import mailbox, portfolio
    from tools import portfolio_delivery

    deadline = time.monotonic() + COLLECTOR_BUDGET_S

    def request(path, body=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("collector round budget exhausted")
        return _collector_request(base, token, path, body, timeout=min(TIMEOUT_S, remaining))

    from lib import safe_file
    try:
        state = json.loads(safe_file.read_text(COLLECTOR_STATE))
    except FileNotFoundError:
        state = {}
    # A corrupt ledger must stop delivery, never silently resend every letter.
    if not isinstance(state, dict):
        raise ValueError("invalid collector state")
    if not dry_run:
        _save_collector(state)  # verify persistence before writing any letter
    count = 0
    for nid, receipt in list(state.items()):
        if count >= COLLECTOR_CAP:
            break
        path = receipt["kind"] + "/" + nid
        if dry_run:
            continue
        if not receipt["acked"]:
            count += 1
            _wake_receipt(receipt, state)
            request(path + "/ack", receipt["ack"])
            receipt["acked"] = True
            _save_collector(state)
        elif receipt["letter"] and not Path(receipt["letter"]).exists():
            count += 1
            request(path + "/read", {})
            del state[nid]
            _save_collector(state)
        elif not receipt["letter"]:
            del state[nid]
            _save_collector(state)

    live = None
    for kind in ("nudges", "messages"):
        items = request(kind)
        for item in items:
            if count >= COLLECTOR_CAP:
                break
            if not isinstance(item, dict):
                continue
            nid, pid = item.get("id", ""), item.get("project", "")
            if not isinstance(nid, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,80}", nid):
                continue
            if nid in state:
                continue
            if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", pid):
                continue
            action = "message" if kind == "messages" else item.get("action")
            if action == "message":
                text = item.get("text")
                if not isinstance(text, str) or not 1 <= len(text) <= 2000:
                    continue
                sentence = "CEO wrote:\n" + text
            elif isinstance(action, str) and action in SENTENCES:
                sentence = SENTENCES[action]
            else:
                continue
            try:
                project = portfolio.get_project(pid)
            except portfolio.PortfolioError:
                project = {}  # unknown project: ack as none instead of failing every round
            if live is None:
                live = portfolio_delivery.live_boxes()
            box, recipient = portfolio_delivery.target(project, live)
            count += 1
            if dry_run:
                # Never print the CEO's text, even in preview mode.
                print(f"would send CEO {action} · {pid} to {recipient}; kind=ask; "
                      + ("wake immediately" if box else "no live recipient"))
                continue
            if action == "done" and project.get("blocker_on") is not None:
                try:
                    portfolio.unblock(pid, actor="system")
                except Exception as exc:  # the push login may be read-only on projects: still deliver the press
                    _log(f"unblock {pid} refused ({type(exc).__name__}), letter asks the recipient")
                    sentence += f"\n(The automatic unblock was refused: run tools/portfolio.py unblock {pid}.)"
            receipt = {"kind": kind, "letter": None, "acked": False, "wake_pending": bool(box),
                       "ack": {"delivered_to": recipient, "woke": False,
                               "reason": "no live recipient" if not box else "wake not completed"}}
            if box:
                role, sid = box.split("-", 1)
                body = f"CEO {action} · {pid}\n{sentence}"
                receipt["letter"] = str(mailbox.send(role, sid, body, "system", "portfolio-collector",
                    kind="ask", subject=body.splitlines()[0], prio="urgent"))
            state[nid] = receipt
            _save_collector(state)
            _wake_receipt(receipt, state)
            request(kind + "/" + nid + "/ack", receipt["ack"])
            receipt["acked"] = True
            _save_collector(state)


def collect(base, token, *, dry_run=False):
    """One bounded round, serialized against manual invocations. No secret/text logging."""
    if COLLECTOR_OFF.exists():
        return
    if dry_run:
        return _collector_round(base, token, dry_run=True)
    COLLECTOR_STATE.parent.mkdir(parents=True, exist_ok=True)
    from lib import safe_file
    with safe_file.open_append(COLLECTOR_STATE.with_suffix(".lock")) as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        _collector_round(base, token)


def _log(line: str) -> None:
    print(PREFIX + line, file=sys.stderr)


def endpoint(base: str | None = None) -> str | None:
    """The full push URL, or None when `base` would carry the token somewhere unsafe."""
    base = (base if base is not None else os.environ.get("PORTFOLIO_PUSH_URL") or DEFAULT_URL).strip()
    parts = urllib.parse.urlsplit(base)
    if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in _LOOPBACK):
        return base.rstrip("/") + PATH
    return None


VERSION_FILE = ROOT / "state" / "portfolio_monitor.version"
VERSIONS = ("1", "2", "3", "4")
_version_warned = False


def monitor_version() -> str | None:
    """The file's version, else PORTFOLIO_MONITOR_V. A refused or bad file logs once and falls back (CTO gate 2b:
    root reads it from a group-writable folder, so a planted link or FIFO is never followed)."""
    global _version_warned
    from lib import safe_file
    try:
        value = safe_file.read_text(VERSION_FILE, 16).strip()
    except FileNotFoundError:
        value = None
    except (OSError, UnicodeError) as exc:
        value, why = None, type(exc).__name__
        if not _version_warned:
            _log(f"version file refused ({why}), using the env")
            _version_warned = True
    if value is not None and value not in VERSIONS:
        if not _version_warned:
            _log("version file holds no 1-4, using the env")
            _version_warned = True
        value = None
    return value or os.environ.get("PORTFOLIO_MONITOR_V")


def build_payload() -> dict:
    from lib import portfolio
    # v2 by default since Console 15399d5 stores v2 and still serves v1 to the old widget;
    # PORTFOLIO_MONITOR_V=1 pushes the v1 body again (ProjectTrack P4). PORTFOLIO_MONITOR_V=3 pushes v3
    # (docs/design/portfolio-monitor-v3.md): only after the Console that accepts v3 is deployed, or
    # the page goes stale.
    version = monitor_version()
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args([] if argv is None else argv)
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
    if args.dry_run:
        try:
            collect(url[:-len(PATH)], token, dry_run=True)
        except Exception as exc:
            _log(f"collector failed ({type(exc).__name__})")
            return EXIT_REFUSED
        return EXIT_OK
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
        try:
            collect(url[:-len(PATH)], token)
        except Exception as exc:
            _log(f"collector failed ({type(exc).__name__})")
            return EXIT_REFUSED
        _log(f"ok 204, {len(payload.get('projects', []))} projects, {len(body)} bytes")
        return EXIT_OK
    why = STATUS_WHY.get(status)
    _log(f"HTTP {status}" + (f" ({why})" if why else "") + (", expected 204" if status < 300 else ""))
    return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
