#!/usr/bin/env python3
"""Mail the CEO: the only way a session emails him (CEO 2026-10-02, skill ALL_Protocol_EmailCEO).

Four kinds and nothing else; the hub (Console POST /api/notify/ceo) refuses the rest:
    action    a decision only he can make, and it blocks work       → mail, phone buzzes
    alert     money, a customer or security is being hurt now       → mail, phone buzzes
    done      an order he gave is finished; link to the result      → mail, silent
    deadline  one of his to-dos falls due within 24 h               → no mail; the 08:00 digest
Run cards and relay login requests already mail by themselves: never send one of those here.

Verbs:
    python3 tools/email_ceo.py send --kind action --title "อนุมัติเครดิต Flow 300 สำหรับ EP3" \\
        --need "ตอบ อนุมัติ/ไม่ ในแชท CTO" --why "script EP3 ผ่านแล้ว" \\
        --if-not "EP3 ไม่ทันเสาร์ 19:30" --link https://... [--ref task-1234] [--dry-run]
    python3 tools/email_ceo.py deadlines [--dry-run]
        # timer (deploy/ceo-deadline-feed.*): his LungNote to-dos due in the next 24 h → kind=deadline

The org MCP tool `email_ceo` (lib/org_tools_registry.py) calls mcp_send(): one path, same checks.

Caps live in the hub: 3 mails per session per Thai day (an alert is exempt), 20 for the org, the same
kind + ref within 6 h is a duplicate. Refused here before any network call: a secret-shaped value
(the tools/ask_run.py rules), a worker process, a role that is not C-level, and more than the CEO
reads: title + need + why + if_not + link + due over 5 lines or a line over 90 characters
(CEO 2026-10-14, lib/ceo_text.py; ref is the hub's dedupe key and does not count).

Hub + token: the Run hub's (tools/ask_run.py): RUN_INBOX_URL (default https://terminal.mooniex.com),
RUN_INBOX_TOKEN or ~/.config/mooniex/run-inbox.token. The token never appears in output.
Exit: 0 accepted · 2 refused (here, or by the hub: a field, a cap, a duplicate) · 3 no token / hub down.
"""
from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import ask_run  # noqa: E402

KINDS = ("action", "alert", "done", "deadline")
FIELDS = ("title", "need", "why", "if_not", "link", "ref", "due")
CEO_READS = ("title", "need", "why", "if_not", "link", "due")   # ≤5 lines together, title = line 1
PATH = "/api/notify/ceo"
THAI = timezone(timedelta(hours=7))
FEED_SESSION = "cto-deadline-feed"  # the timer's own name in the ledger; caps are per session
FEED_MAX = 30
LUNGNOTE_ENV = ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "LUNGNOTE_USER_ID")
EXIT_OK, EXIT_REFUSED, EXIT_HUB = 0, 2, 3

Refused = ask_run.Refused
HubError = ask_run.HubError


def machine(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    named = (env.get("ORG_MACHINE") or "").strip().lower()
    if named:
        return named
    return {"darwin": "mac", "win32": "winbox"}.get(sys.platform, "contabo")


def build_payload(fields: dict, *, kind: str, session: str = "", role: str = "",
                  env: dict | None = None) -> dict:
    """The POST body, or Refused. Role and session resolve the way ask_run does (a worker is refused)."""
    env = os.environ if env is None else env
    kind = (kind or "").strip().lower()
    if kind not in KINDS:
        raise Refused(f"kind must be one of {'/'.join(KINDS)} (got {kind!r}); "
                      "anything else is not a mail to the CEO (skill ALL_Protocol_EmailCEO)")
    who = ask_run.resolve_requester(session or None, role or None, None, env)
    if env.get("WORKER_TASK_ID") and not env.get("CXO_ROLE"):
        raise Refused("a worker never mails the CEO: report to your C-level, which decides (CEO 2026-10-02)")
    senders = [r for r in ask_run.c_level_roles() if r != "ceo"]
    if who["role"] not in senders:
        raise Refused(f"role {who['role']!r} may not mail the CEO; C-level only ({', '.join(senders)})")
    body: dict[str, Any] = {"kind": kind, "role": who["role"], "session": who["session"], "machine": machine(env)}
    for name in FIELDS:
        value = fields.get(name)
        if isinstance(value, str) and value.strip():
            body[name] = value.strip()
    hits = ask_run.find_secret_shapes(body)
    if hits:
        raise Refused(f"secret-shaped value in {hits[0]}: a secret never goes in a mail")
    ask_run.check_ceo_text([(name, body.get(name)) for name in CEO_READS])
    return body


def _post(body: dict, *, dry_run: bool = False) -> dict:
    """POST to the hub. 4xx → Refused carrying the hub's error, field, hint and first id; 5xx → HubError."""
    url = ask_run.base_url() + PATH + ("?dry_run=1" if dry_run else "")
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"Authorization": "Bearer " + ask_run.load_token(),
                                          "Content-Type": "application/json; charset=utf-8",
                                          "Accept": "application/json", "User-Agent": "mooniex-email-ceo/1",
                                          "X-Run-Session": body.get("session", "")})
    try:
        with ask_run._OPENER.open(req, timeout=ask_run.HTTP_TIMEOUT_S) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400 or e.code >= 500 or e.code == 401:
            raise ask_run._hub_error(e) from None
        try:
            got = json.loads(e.read() or b"{}")
        except ValueError:
            got = {}
        detail = ", ".join(f"{k}={got[k]}" for k in ("field", "what", "kind", "cap", "id", "max") if k in got)
        msg = f"hub refused ({e.code}: {got.get('error', 'error')}{'; ' + detail if detail else ''})"
        if got.get("hint"):
            msg += f": {got['hint']}"
        refused = Refused(msg)
        refused.status = e.code
        raise refused from None
    except (urllib.error.URLError, OSError) as e:
        raise HubError(f"hub unreachable at {ask_run.base_url()}: {getattr(e, 'reason', e)}", transient=True) from None


def send(fields: dict, *, kind: str, session: str = "", role: str = "", dry_run: bool = False,
         env: dict | None = None) -> dict:
    return _post(build_payload(fields, kind=kind, session=session, role=role, env=env), dry_run=dry_run)


def mcp_send(arguments: dict, env: dict | None = None) -> dict:
    """MCP `email_ceo`: same checks, same POST. Returns the hub's answer ({id, mailed, buzz, quota})."""
    a = {k: (v if v is not None else "") for k, v in arguments.items()}
    try:
        return send({k: a.get(k, "") for k in FIELDS}, kind=a.get("kind", ""), session=a.get("session", ""),
                    role=a.get("role", ""), dry_run=bool(a.get("dry_run")), env=env)
    except Refused as e:
        raise Refused(f"refused: {e}") from None


# ------------------------------------------------------------------ deadlines (timer)
def due_todos(now: datetime, env: dict | None = None, fetch=None) -> list[dict]:
    """His open LungNote to-dos with due_at in [now, now + 24 h], soonest first. The PostgREST creds come
    from the environment (Infisical LungNote-MCP/prod through `infisical_setup.py run`), never a file."""
    return lungnote_request([
        ("done", "eq.false"),
        ("due_at", f"gte.{now.isoformat()}"), ("due_at", f"lte.{(now + timedelta(hours=24)).isoformat()}"),
        ("select", "id,text,due_at,due_text"), ("order", "due_at.asc"), ("limit", str(FEED_MAX)),
    ], env, fetch)


def lungnote_request(query: list[tuple[str, str]], env: dict | None = None, fetch=None,
                     *, body: dict | None = None):
    """Shared PostgREST transport; credentials are supplied only through the environment."""
    env = os.environ if env is None else env
    url, key, uid = (env.get(n, "") for n in LUNGNOTE_ENV)
    if not (url and key and uid):
        raise HubError(f"{' / '.join(LUNGNOTE_ENV)} not in the environment: run under "
                       "infisical_setup.py run LungNote-MCP prod")
    query = urllib.parse.urlencode([("user_id", f"eq.{uid}"), *query])
    req = urllib.request.Request(f"{url.rstrip('/')}/rest/v1/lungnote_todos?{query}",
                                 data=None if body is None else json.dumps(body).encode(),
                                 method="GET" if body is None else "PATCH",
                                 headers={"apikey": key, "Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json", "Prefer": "return=representation"})
    if fetch is not None:
        return fetch(req)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read() or b"[]")
    except urllib.error.HTTPError as e:
        raise HubError(f"LungNote refused: HTTP {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise HubError("LungNote unreachable") from None


def _thai_when(due_at: str) -> str:
    try:
        d = datetime.fromisoformat(due_at.replace("Z", "+00:00")).astimezone(THAI)
    except (ValueError, AttributeError):
        return str(due_at)[:16]
    return d.strftime("%d/%m %H:%M") + " น."


_TAGS = re.compile(r"^(?:\s*\[[^\]]{0,120}\])+\s*")  # "[SID:cto-x · backlog] " routing tags agents prepend


def deadline_fields(todo: dict) -> dict:
    raw = " ".join(str(todo.get("text") or "").split())
    text = _TAGS.sub("", raw) or raw
    title = text if len(text) <= 90 else text[:89] + "…"
    return {"title": title, "due": _thai_when(todo.get("due_at", "")), "ref": f"todo:{todo.get('id', '')}"[:80]}


def feed_deadlines(*, dry_run: bool = False, now: datetime | None = None, env: dict | None = None,
                   fetch=None, post=None) -> dict:
    env = dict(os.environ if env is None else env)
    env.setdefault("CXO_ROLE", "cto")
    env.setdefault("CXO_SESSION_ID", FEED_SESSION.split("-", 1)[1])
    now = now or datetime.now(timezone.utc)
    todos = due_todos(now, env, fetch)
    post = (lambda body: print(json.dumps(body, ensure_ascii=False))) if dry_run else (post or _post)
    out = {"due": len(todos), "queued": 0, "duplicate": 0, "refused": []}
    for todo in todos:
        body = build_payload(deadline_fields(todo), kind="deadline", session=FEED_SESSION, role="cto", env=env)
        try:
            post(body)
            out["queued"] += 1
        except Refused as e:
            if "duplicate" in str(e):
                out["duplicate"] += 1
            else:
                out["refused"].append(f"{body['ref']}: {e}")
    return out


def merged_fields(prs: list[dict], now: datetime) -> dict | None:
    """Compact repository totals, with detail available through the search link."""
    repos: dict[str, set[int]] = {}
    for pr in prs:
        name = pr["repository"]["nameWithOwner"]
        number = pr["number"]
        if not isinstance(name, str) or not re.fullmatch(r"PASAKON/[\w.-]+", name):
            raise ValueError("invalid repository")
        if type(number) is not int or number <= 0:
            raise ValueError("invalid PR number")
        repos.setdefault(name.split("/", 1)[1], set()).add(number)
    if not repos:
        return None
    window = f"{(now - timedelta(hours=24)).isoformat()}..{now.isoformat()}"
    query = f"org:PASAKON is:pr is:merged merged:{window}"
    link = "https://github.com/search?" + urllib.parse.urlencode({"q": query, "type": "pullrequests"})
    lines = []
    shown = 3 if len(repos) <= 3 else 2
    for name, numbers in sorted(repos.items())[:shown]:
        prefix = f"{name} {len(numbers)}:"
        if len(prefix) > 75:
            prefix = f"{name[:60]}… {len(numbers)}:"
        line = prefix
        for number in sorted(numbers):
            token = f" #{number}"
            if len(line + token) > 88:
                line += " …"
                break
            line += token
        lines.append(line)
    if len(repos) > shown:
        lines.append(f"+{len(repos) - shown} repo …")
    return {"title": f"merge แล้ว 24 ชม.: {sum(map(len, repos.values()))} PR",
            "why": "\n".join(lines), "link": link,
            "ref": f"merge-digest-{now.astimezone(THAI):%Y-%m-%d}"}


def feed_merged(*, dry_run: bool = False, now: datetime | None = None,
                env: dict | None = None, runner=None) -> dict:
    """One gh search; failures never change the deadline feed's result."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    env = dict(os.environ if env is None else env)
    env.setdefault("CXO_ROLE", "cto")
    try:
        if not env.get("HOME"):
            env["HOME"] = pwd.getpwuid(os.getuid()).pw_dir
        window = f"{(now - timedelta(hours=24)).isoformat()}..{now.isoformat()}"
        result = (runner or subprocess.run)(
            ["gh", "search", "prs", "--owner", "PASAKON", "--merged", "--merged-at", window,
             "--limit", "1000", "--json", "number,repository"],
            env=env, capture_output=True, text=True, check=True, timeout=60)
        prs = json.loads(result.stdout)
        if not isinstance(prs, list):
            raise ValueError("expected list")
        fields = merged_fields(prs, now)
        if fields is None:
            return {"sent": 0, "status": "no merged PRs"}
        if dry_run:
            body = build_payload(fields, kind="done", session=FEED_SESSION, role="cto", env=env)
            print("merged-digest dry-run: " + json.dumps(body, ensure_ascii=False))
            return {"sent": 0, "status": "dry-run"}
        try:
            send(fields, kind="done", session=FEED_SESSION, role="cto", env=env)
        except Refused as e:
            if getattr(e, "status", None) == 409:
                return {"sent": 1, "status": "already sent"}
            raise
        return {"sent": 1}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, Refused, HubError):
        print("email_ceo: merged-digest unavailable; skipped", file=sys.stderr)
        return {"sent": 0, "status": "unavailable"}


# ------------------------------------------------------------------ CLI
def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="verb", required=True)
    s = sub.add_parser("send", help="mail the CEO one action / alert / done / deadline")
    s.add_argument("--kind", required=True, choices=KINDS)
    s.add_argument("--title", required=True, help="one line, ≤90 chars: what this is about")
    s.add_argument("--need", default="", help="the ONE thing he must do (action: required)")
    s.add_argument("--why", default="", help="why / what happened / the result; the whole mail is "
                   "≤5 lines of ≤90 chars, title included (detail goes in a linked file)")
    s.add_argument("--if-not", dest="if_not", default="", help="what happens if he does nothing")
    s.add_argument("--link", default="", help="one URL that opens the thing itself")
    s.add_argument("--ref", default="", help="task id / issue / slug; same kind+ref within 6 h = duplicate")
    s.add_argument("--due", default="", help="deadline only: when it falls due")
    s.add_argument("--session", default="", help="your mailbox, e.g. cto-6ebacd0e (default: from env)")
    s.add_argument("--role", default="", help="your C-level role (default: from env)")
    s.add_argument("--dry-run", action="store_true", help="show the mail the hub would send; send nothing")
    d = sub.add_parser("deadlines", help="timer: his LungNote to-dos due within 24 h → kind=deadline")
    d.add_argument("--dry-run", action="store_true")
    d.add_argument("--no-merged", action="store_true", help="skip the daily merged-PR digest")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.verb == "send":
            fields = {k: getattr(args, k) for k in FIELDS}
            got = send(fields, kind=args.kind, session=args.session, role=args.role, dry_run=args.dry_run)
        else:
            try:
                got = feed_deadlines(dry_run=args.dry_run)
            finally:
                if not args.no_merged:
                    merged = feed_merged(dry_run=args.dry_run)
                    print("merged-digest: " + json.dumps(merged, ensure_ascii=False))
    except Refused as e:
        print(f"email_ceo: refused: {e}", file=sys.stderr)
        return EXIT_REFUSED
    except HubError as e:
        print(f"email_ceo: {e}", file=sys.stderr)
        return EXIT_HUB
    print(json.dumps(got, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
