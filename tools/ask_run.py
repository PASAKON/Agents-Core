#!/usr/bin/env python3
"""Run Inbox requester — ask the CEO to run one command on a host, from any
session or worker (docs/design/run-inbox/DESIGN.md §6 + §13, brief
docs/ops/briefs/run-inbox-p1b-core.md).

The one rule (DESIGN §2): the CEO's tap on the phone is the only authority.
This tool creates a card, reads it, cancels its own pending card and streams
its output. It has no verb that approves, and the org token it carries cannot
approve either (the hub refuses it).

Verbs:
    python3 tools/ask_run.py create --host contabo --why "weekly capture" \\
        --script Agents-Core@9df4e185:scripts/contabo_blueprint.sh [-- args...]
    python3 tools/ask_run.py create --host contabo --why "..." \\
        --command "systemctl restart mooniex-console"      # C-level roles only
    python3 tools/ask_run.py wait <id>     # polls every 5 s until it ends
    python3 tools/ask_run.py list [--status pending] [--limit 50]
    python3 tools/ask_run.py cancel <id>   # your own pending ask only
    python3 tools/ask_run.py tail <id>     # live output (SSE) to stdout

`create --dry-run` prints the JSON body and calls nothing (no token needed).
`<id>` is RUN-YYYYMMDD-HHMM-xxxx, or the phone URL that ends in #RUN-...

Refused here, BEFORE any network call (exit 2):
  - a secret-shaped value anywhere in the ask: the key family of
    scripts/contabo_blueprint.sh's final pass (a token/secret/password/
    api_key/private_key/client_secret/access_key assigned a literal value,
    a BEGIN ... PRIVATE KEY block) plus well-known token shapes (GitHub,
    sk-..., Slack, AWS, Google, GitLab, JWT, Bearer). Reference an env var by
    name ($NAME, --env-key NAME) or an Infisical path instead;
  - --command from a role other than cto/cfo/cxo/ceo (CEO decision 1,
    DESIGN §11). The hub enforces the same gate (403 freeform_needs_c_level).

Hub:   RUN_INBOX_URL, default https://terminal.mooniex.com
Token: RUN_INBOX_TOKEN, else ~/.config/mooniex/run-inbox.token (mode 0600).
       Never printed, never logged, never sent anywhere but the hub: a
       redirect is refused, not followed (urllib would copy the
       Authorization header onto the redirected request — measured).

requester.session is the MAILBOX BOX NAME `<role>-<id>` (cto-6ebacd0e,
dev-task-8669cf28): the hub drops the result letter into
state/inbox/<requester.session>/, and scripts/hook-inbox.py drains exactly
`<role>-<id>` boxes. Resolved from --session, else ORG_SESSION_ID /
CXO_SESSION_ID / CTO_SESSION_ID / WORKER_TASK_ID the way hook-inbox.py
resolves the session's own box.

Exit codes: 0 ok (wait/tail: the ask ended `done`) · 1 the ask ended failed/
denied/expired/cancelled · 2 refused here or bad arguments · 3 no token,
hub unreachable, or hub error · 4 wait --max-wait elapsed first.

stdlib only (urllib) and Python 3.9+, so it runs on any box's python3.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

DEFAULT_URL = "https://terminal.mooniex.com"
URL_ENV = "RUN_INBOX_URL"
TOKEN_ENV = "RUN_INBOX_TOKEN"
TOKEN_FILE = Path(".config") / "mooniex" / "run-inbox.token"  # under the user's home

# CEO decision 1 (DESIGN §11): freeform commands are for these roles only; the
# hub checks the same list and answers 403 freeform_needs_c_level.
C_LEVEL_ROLES = ("cto", "cfo", "cxo", "ceo")
RISKS = ("green", "amber", "red")
SHELLS = ("bash", "powershell", "cmd")
TERMINAL_STATES = ("done", "failed", "denied", "expired", "cancelled")
NO_RUN_STATES = ("denied", "expired", "cancelled")  # ended without running

DEFAULT_RISK = "amber"          # DESIGN §6 signature: risk="amber"
DEFAULT_TIMEOUT_S = 300         # DESIGN §4: 300 s run timeout
POLL_INTERVAL_S = 5.0           # brief: wait polls every 5 s
MIN_INTERVAL_S = 1.0            # floor for --interval (tests lower it)
HTTP_TIMEOUT_S = 20.0
MAX_POLL_FAILURES = 12          # consecutive transient errors `wait` rides out (~1 min)
TAIL_LINES = 40
USER_AGENT = "mooniex-ask-run/1"

EXIT_OK = 0
EXIT_ENDED_BADLY = 1
EXIT_REFUSED = 2
EXIT_HUB = 3
EXIT_STILL_WAITING = 4

_HOST_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")   # session / task ids
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_ID_RE = re.compile(r"^RUN-[A-Za-z0-9][A-Za-z0-9-]{3,63}$")


class Refused(Exception):
    """Refused here, before any network call (exit 2)."""


class HubError(Exception):
    """No token, the hub is unreachable, or it answered with an error (exit 3)."""

    def __init__(self, message: str, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


def _say(msg: str) -> None:
    print(msg, file=sys.stderr)


# ------------------------------------------------------------ secret shapes
# The key family and the private-key marker are copied VERBATIM from
# scripts/contabo_blueprint.sh step 10 (its final redaction pass);
# tests/test_ask_run.py asserts both strings still appear there, so the two
# cannot drift apart silently. The hub (P1a) refuses the same family with
# 400 secret_shaped_value; this copy only makes the refusal happen before
# anything leaves the box.
SECRET_KEY_WORDS = r"(?:token|secret|passw(?:or)?d|api[_-]?key|private[_-]?key|client[_-]?secret|access[_-]?key)"
PRIVATE_KEY_MARKER = r"BEGIN [A-Z ]*PRIVATE KEY"

_KEY = r"[A-Za-z0-9_.\-]*" + SECRET_KEY_WORDS + r"[A-Za-z0-9_.\-]*"
# (a) the blueprint's own rule: a line that assigns a value to a secret-named key
_ASSIGN_LINE = re.compile(r"^\s*[-\"']?(?P<key>" + _KEY + r")[\"']?\s*[:=]\s*(?P<val>\S.*)$", re.IGNORECASE)
# (b) the same rule per shell word, so FOO_TOKEN=x mid-command, --password=x
#     and ?access_token=x inside a URL are caught too ({} is not a separator:
#     it would cut ${NAME} in half; JSON keys are rule (c)'s job)
_WORD_SPLIT = re.compile(r"[\s\[\]()<>,;&|?`]+")
_ASSIGN_WORD = re.compile(r"^[-\"']*(?P<key>" + _KEY + r")[\"']?[:=](?P<val>.+)$", re.IGNORECASE)
# (c) a quoted key in JSON/YAML text: {"api_key": "x"}
_QUOTED_KEY = re.compile(
    r"[\"'](?P<key>" + _KEY + r")[\"']\s*:\s*(?P<val>\"[^\"]*\"|'[^']*'|[^\s,}\]]+)", re.IGNORECASE)
_KEYMAT = re.compile(PRIVATE_KEY_MARKER)
# A value that only NAMES an env var is the recommended form (DESIGN §6), not a secret.
_ENV_REF = re.compile(
    r"""^["']?(?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_][A-Za-z0-9_]*%|\$env:[A-Za-z_][A-Za-z0-9_]*)["']?[,;]?$""")
_EMPTY_VALUES = ("", "''", '""', "<redacted>", "'<redacted>'", '"<redacted>"')
# Values that are secrets whatever key (if any) they sit under.
_TOKEN_SHAPES = (
    ("a GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")),
    ("an sk-... API key", re.compile(r"\bsk-(?:ant-|or-v1-|proj-)?[A-Za-z0-9_\-]{30,}")),
    ("a Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("an AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("a GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}")),
    ("a JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    ("a Bearer credential", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/\-]{16,}=*", re.IGNORECASE)),
)


def _literal(val: str) -> bool:
    """True when what follows `key=` / `key:` starts with a literal value.
    Only the first word counts: a shell assignment ends at whitespace, so in
    `GH_TOKEN="$GH_TOKEN" ./deploy.sh` the value is the env reference."""
    words = val.split()
    first = words[0] if words else ""
    return first not in _EMPTY_VALUES and not _ENV_REF.match(first)


def _strings(obj: Any, where: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(obj, str):
        yield where or "value", obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{where}.{k}" if where else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{where}[{i}]")


def find_secret_shapes(payload: Any) -> list[str]:
    """`field: what` for every secret-shaped value in `payload` — the field
    and the key NAME only, never the value itself. Empty list = clean."""
    hits: list[str] = []
    for field, text in _strings(payload):
        if _KEYMAT.search(text):
            hits.append(f"{field}: private key material")
            continue
        for line in text.splitlines() or [text]:
            m = _ASSIGN_LINE.match(line)
            if m and _literal(m.group("val")):
                hits.append(f"{field}: {m.group('key')}=<value>")
            for m in _QUOTED_KEY.finditer(line):
                if _literal(m.group("val")):
                    hits.append(f"{field}: {m.group('key')}=<value>")
            for word in _WORD_SPLIT.split(line):
                m = _ASSIGN_WORD.match(word)
                if m and _literal(m.group("val")):
                    hits.append(f"{field}: {m.group('key')}=<value>")
        for label, rx in _TOKEN_SHAPES:
            if rx.search(text):
                hits.append(f"{field}: looks like {label}")
    return list(dict.fromkeys(hits))


def check_role_gate(payload: dict) -> None:
    role = payload["requester"]["role"]
    if payload["kind"] == "command" and role not in C_LEVEL_ROLES:
        raise Refused(
            f"freeform_needs_c_level: --command is for C-level sessions ({'/'.join(C_LEVEL_ROLES)}); "
            f"this requester is role {role!r}. Commit the script, push it, and ask with "
            "--script repo@sha:path (DESIGN §6, CEO decision 1).")


# --------------------------------------------------------------- the ask
def parse_script_spec(spec: str) -> tuple[str, str, str]:
    """`repo@sha:path` -> (repo, sha, path). The sha must be a commit id (the
    executor fetches exactly that commit), never a branch name."""
    usage = ("--script takes repo@sha:path at a pushed commit, e.g. "
             "Agents-Core@9df4e185:scripts/contabo_blueprint.sh")
    repo, at, rest = spec.strip().partition("@")
    sha, colon, path = rest.partition(":")
    sha = sha.lower()
    if not (at and colon and _REPO_RE.match(repo) and _SHA_RE.match(sha) and path):
        raise Refused(f"{usage} (got {spec!r})")
    if path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path) or "\\" in path:
        raise Refused(f"--script path must be relative to the repo root, with / separators (got {path!r})")
    if ".." in path.split("/"):
        raise Refused(f"--script path must stay inside the repo (got {path!r})")
    return repo, sha, path


def _env_box(env: dict) -> tuple[str | None, str | None]:
    """(role, session id) of the mailbox this process drains — the same
    resolution as scripts/hook-inbox.py `_current_box`, plus
    tools/agent_transport.py's bare CTO_SESSION_ID fallback."""
    role = env.get("CXO_ROLE")
    if role:
        return role, env.get("CXO_SESSION_ID") or env.get("CTO_SESSION_ID") or None
    task = env.get("WORKER_TASK_ID")
    if task:
        return env.get("WORKER_ROLE") or "dev", task
    sid = env.get("CTO_SESSION_ID")
    if sid:
        return "cto", sid
    return None, None


def resolve_requester(session: str | None, role: str | None, task: str | None,
                      env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    env_role, env_sid = _env_box(env)
    role = (role or env_role or "").strip().lower()
    if not role:
        raise Refused("cannot tell this session's role: pass --role "
                      "(cto/cfo/cxo/ceo for a C-level session, dev for a worker)")
    worker = env.get("WORKER_TASK_ID")
    if worker and not env.get("CXO_ROLE") and role in C_LEVEL_ROLES:
        raise Refused(f"this process is worker {worker} (WORKER_TASK_ID is set); "
                      f"a worker cannot claim role {role!r}")
    session = (session or "").strip()
    if not session:
        sid = (env.get("ORG_SESSION_ID") or env_sid or "").strip()
        box_role = env_role or role
        if sid:
            session = sid if sid.startswith(box_role + "-") else f"{box_role}-{sid}"
    if not session:
        raise Refused("cannot tell this session's mailbox: pass --session <role>-<id> "
                      "(e.g. cto-6ebacd0e) so the result letter reaches you")
    if not _NAME_RE.match(session):
        raise Refused(f"--session must be a mailbox name like cto-6ebacd0e (got {session!r})")
    requester = {"session": session, "role": role}
    task = (task or env.get("WORKER_TASK_ID") or "").strip()
    if task:
        if not _NAME_RE.match(task):
            raise Refused(f"--task must be a task id like task-8669cf28 (got {task!r})")
        requester["task"] = task
    return requester


def _one_line(flag: str, value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise Refused(f"{flag} is empty")
    if "\n" in value or "\r" in value:
        raise Refused(f"{flag} is one line (it is shown on the card)")
    return value


def build_payload(args: argparse.Namespace, script_args: list[str],
                  env: dict | None = None) -> dict:
    """The POST /api/run/asks body, in the contract's field order. Fields the
    requester did not set are left out (the hub applies its defaults) —
    except risk/timeout_s/expects_input, which are always sent explicitly."""
    host = (args.host or "").strip().lower()
    if not _HOST_RE.match(host):
        raise Refused(f"--host must be a host id like contabo / mac / winbox (got {args.host!r})")
    payload: dict[str, Any] = {"host": host}
    if args.script:
        repo, sha, path = parse_script_spec(args.script)
        payload["kind"] = "script"
        payload["script"] = {"repo": repo, "sha": sha, "path": path, "args": list(script_args)}
    else:
        if script_args:
            raise Refused("`-- args...` go with --script; with --command put the whole line in --command")
        if not (args.command or "").strip():
            raise Refused("--command is empty")
        payload["kind"] = "command"
        payload["command"] = args.command  # byte-for-byte: what the CEO reads is what runs
    if args.shell:
        payload["shell"] = args.shell
    if args.cwd:
        payload["cwd"] = args.cwd
    if args.env_key:
        bad = [k for k in args.env_key if not _ENV_NAME_RE.match(k)]
        if bad:
            raise Refused(f"--env-key takes a variable NAME, never NAME=value (got {bad[0]!r})")
        payload["env_keys"] = list(dict.fromkeys(args.env_key))
    payload["why"] = _one_line("--why", args.why)
    if args.expected is not None:
        payload["expected"] = _one_line("--expected", args.expected)
    if args.timeout <= 0:
        raise Refused("--timeout must be a positive number of seconds")
    payload["risk"] = args.risk
    payload["timeout_s"] = args.timeout
    payload["expects_input"] = bool(args.expects_input)
    payload["requester"] = resolve_requester(args.session, args.role, args.task, env)
    return payload


# ------------------------------------------------------------ hub access
def base_url() -> str:
    url = (os.environ.get(URL_ENV) or "").strip() or DEFAULT_URL
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise HubError(f"{URL_ENV} must be an http(s) URL (got {url!r})")
    return url.rstrip("/")


def token_path() -> Path:
    return Path.home() / TOKEN_FILE


def load_token() -> str:
    """RUN_INBOX_TOKEN, else the token file (0600). The value goes into the
    Authorization header and nowhere else — no message here names it."""
    val = (os.environ.get(TOKEN_ENV) or "").strip()
    if val:
        return val
    path = token_path()
    try:
        mode = path.stat().st_mode
    except FileNotFoundError:
        raise HubError(f"no token: set {TOKEN_ENV} or create {path} (mode 0600)") from None
    except OSError as e:
        raise HubError(f"cannot read {path}: {e.strerror}") from None
    if os.name == "posix" and mode & 0o077:
        raise HubError(f"{path} is readable by other users (mode {stat.S_IMODE(mode):04o}); "
                       f"run: chmod 600 {path}")
    try:
        val = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise HubError(f"cannot read {path}: {e.strerror}") from None
    if not val:
        raise HubError(f"{path} is empty")
    return val


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect: following one would hand the Bearer token to
    whatever the Location names (urllib copies Authorization across)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None  # -> urllib raises HTTPError(3xx), handled in _hub_error


_OPENER = urllib.request.build_opener(_NoRedirect())

_HINTS = {
    "secret_shaped_value": "remove the value; reference an env var name or an Infisical path",
    "freeform_needs_c_level": "workers ask with --script repo@sha:path at a pushed commit",
    "peer_exec_not_yet": "that host has no executor yet (P2); only the hub's own host runs cards today",
    401: f"the hub did not accept the org token ({TOKEN_ENV} or ~/{TOKEN_FILE.as_posix()})",
    403: "the org token may not do that (it can create, read its own asks and cancel its own pending ask)",
    404: "no such ask, or not yours (the org token only sees its own asks)",
    409: "not possible in the ask's current state (only a pending ask can be cancelled)",
}


def _maybe_json(raw: Any) -> Any:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _hub_error(e: urllib.error.HTTPError) -> HubError:
    if 300 <= e.code < 400:
        loc = e.headers.get("Location", "?") if e.headers else "?"
        return HubError(f"hub answered {e.code} redirect to {loc}: not followed (the token only goes "
                        f"to {base_url()}); check {URL_ENV}", status=e.code)
    try:
        raw = e.read()
    except Exception:  # noqa: BLE001 - an unreadable error body is still an error
        raw = b""
    body = _maybe_json(raw)
    code = detail = None
    if isinstance(body, dict):
        code = body.get("error") if isinstance(body.get("error"), str) else None
        detail = body.get("message") or body.get("detail")
    elif raw:
        detail = raw[:200].decode("utf-8", "replace")
    msg = f"hub refused ({e.code}{': ' + code if code else ''})"
    if detail:
        msg += f" {detail}"
    hint = _HINTS.get(code) or _HINTS.get(e.code)
    if hint:
        msg += f": {hint}"
    return HubError(msg, status=e.code, code=code)


def _request(method: str, path: str, *, body: Any = None, query: dict | None = None,
             accept: str = "application/json", timeout: float | None = HTTP_TIMEOUT_S):
    token = load_token()
    url = base_url() + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {"Authorization": "Bearer " + token, "Accept": accept, "User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        return _OPENER.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise _hub_error(e) from None
    except (urllib.error.URLError, OSError) as e:  # refused, DNS, TLS, timeout
        raise HubError(f"hub unreachable at {base_url()}: {getattr(e, 'reason', e)}") from None


def _call(method: str, path: str, *, body: Any = None, query: dict | None = None) -> Any:
    resp = _request(method, path, body=body, query=query)
    try:
        with resp:
            raw = resp.read()
    except OSError as e:
        raise HubError(f"hub connection dropped mid-answer: {e}") from None
    if not raw.strip():
        return {}
    parsed = _maybe_json(raw)
    if parsed is None:
        raise HubError(f"hub answered non-JSON: {raw[:120]!r}")
    return parsed


def _unwrap(rec: Any) -> dict:
    """A card, whether the hub sends it bare or as {ask: {...}}."""
    if isinstance(rec, dict) and isinstance(rec.get("ask"), dict):
        return rec["ask"]
    return rec if isinstance(rec, dict) else {}


def normalize_id(raw: str) -> str:
    s = (raw or "").strip()
    if "#" in s:  # the phone URL .../run#RUN-...
        s = s.rsplit("#", 1)[1]
    if not _ID_RE.match(s):
        raise Refused(f"not a Run Inbox id: {raw!r} (expected RUN-YYYYMMDD-HHMM-xxxx or its /run#... URL)")
    return s


def card_url(ask_id: str) -> str:
    return f"{base_url()}/run#{ask_id}"


def _ask_path(ask_id: str, suffix: str = "") -> str:
    return f"/api/run/asks/{urllib.parse.quote(ask_id, safe='')}{suffix}"


# ------------------------------------------------------------- rendering
def _ts(value: Any) -> datetime | None:
    """A hub timestamp (ISO-8601, or epoch seconds / milliseconds) as UTC."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        secs = value / 1000.0 if value > 1e11 else float(value)
        return datetime.fromtimestamp(secs, tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _duration_s(rec: dict) -> float | None:
    ms = rec.get("duration_ms")
    if isinstance(ms, (int, float)) and not isinstance(ms, bool):
        return ms / 1000.0
    started, finished = _ts(rec.get("started_at")), _ts(rec.get("finished_at"))
    if started and finished:
        return max(0.0, (finished - started).total_seconds())
    return None


def _what(ask: dict) -> str:
    cmd = ask.get("command")
    if isinstance(cmd, str) and cmd.strip():
        first = cmd.strip().splitlines()[0]
    else:
        sc = ask.get("script")
        if not isinstance(sc, dict):
            sc = _maybe_json(sc if isinstance(sc, str) else ask.get("script_json"))
        if isinstance(sc, dict):
            args = " ".join(str(a) for a in (sc.get("args") or []))
            first = f"{sc.get('repo', '?')}@{str(sc.get('sha', ''))[:8]}:{sc.get('path', '?')} {args}".strip()
        else:
            first = "?"
    return first if len(first) <= 70 else first[:67] + "..."


def print_result(rec: dict, *, lines: int = TAIL_LINES, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return
    parts = [str(rec.get("id", "?")), str(rec.get("status", "?"))]
    if rec.get("exit_code") is not None:
        parts.append(f"exit {rec['exit_code']}")
    dur = _duration_s(rec)
    if dur is not None:
        parts.append(f"{dur:.1f}s")
    if rec.get("host"):
        parts.append(f"host {rec['host']}")
    print("  ".join(parts))
    if rec.get("error_id"):
        print(f"Error ID {rec['error_id']} (full record on the hub: node scripts/run-error.js {rec['error_id']})")
    if rec.get("deny_reason"):
        print(f"denied: {rec['deny_reason']}")
    tail = rec.get("output_tail")
    if isinstance(tail, str) and tail:
        all_lines = tail.splitlines()
        shown = all_lines[-lines:] if lines > 0 else all_lines
        print(f"--- output tail ({len(shown)} of {len(all_lines)} lines) ---")
        print("\n".join(shown))


# ------------------------------------------------------------------ verbs
def cmd_create(args: argparse.Namespace, script_args: list[str]) -> int:
    payload = build_payload(args, script_args)
    hits = find_secret_shapes(payload)
    if hits:
        raise Refused("secret_shaped_value; nothing was sent:\n  " + "\n  ".join(hits)
                      + "\nReference an env var by name ($NAME, --env-key NAME) or an Infisical path "
                        "instead (DESIGN §6).")
    check_role_gate(payload)
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        sys.stdout.flush()
        _say(f"dry run: nothing sent (would POST {base_url()}/api/run/asks)")
        return EXIT_OK
    resp = _unwrap(_call("POST", "/api/run/asks", body=payload))
    ask_id = resp.get("id")
    if not isinstance(ask_id, str) or not ask_id:
        raise HubError(f"hub accepted the ask but returned no id: {json.dumps(resp)[:200]}")
    url = card_url(ask_id)
    if args.json:
        print(json.dumps({**resp, "url": url}, indent=2, ensure_ascii=False))
    else:
        print(ask_id)
        print(url)
    _say(f"{resp.get('status', 'pending')} · risk {resp.get('risk', '?')} · expires "
         f"{resp.get('expires_at', '?')}. Only the CEO's tap runs it. "
         f"Next: python3 tools/ask_run.py wait {ask_id}")
    return EXIT_OK


def cmd_wait(args: argparse.Namespace) -> int:
    ask_id = normalize_id(args.id)
    interval = max(args.interval, MIN_INTERVAL_S)
    deadline = time.monotonic() + args.max_wait if args.max_wait and args.max_wait > 0 else None
    last = None
    failures = 0
    while True:
        rec = None
        try:
            rec = _unwrap(_call("GET", _ask_path(ask_id)))
            failures = 0
        except HubError as e:
            if e.status is not None and e.status < 500 and e.status != 429:
                raise  # 4xx will not fix itself by waiting
            failures += 1
            if failures > MAX_POLL_FAILURES:
                raise
            _say(f"{ask_id}: {e} (retry {failures}/{MAX_POLL_FAILURES})")
        if rec is not None:
            rec.setdefault("id", ask_id)
            status = str(rec.get("status") or "?")
            if status != last:
                _say(f"{datetime.now().strftime('%H:%M:%S')} {ask_id} {status}")
                last = status
            if status in TERMINAL_STATES:
                print_result(rec, lines=args.lines, as_json=args.json)
                return EXIT_OK if status == "done" else EXIT_ENDED_BADLY
        pause = interval
        if deadline is not None:
            left = deadline - time.monotonic()
            if left <= 0:
                _say(f"{ask_id} still {last or 'unknown'} after {args.max_wait:g} s; run wait again later")
                return EXIT_STILL_WAITING
            pause = min(interval, left)
        time.sleep(pause)


def cmd_list(args: argparse.Namespace) -> int:
    query = {}
    if args.status:
        query["status"] = args.status
    if args.limit:
        query["limit"] = str(args.limit)
    resp = _call("GET", "/api/run/asks", query=query)
    asks = resp.get("asks") if isinstance(resp, dict) else resp
    asks = [a for a in (asks or []) if isinstance(a, dict)]
    if args.json:
        print(json.dumps(asks, indent=2, ensure_ascii=False))
        return EXIT_OK
    if not asks:
        print("(no asks)")
        return EXIT_OK
    for a in asks:
        row = (f"{a.get('id', '?')}  {str(a.get('status', '?')):<9} {str(a.get('host', '?')):<8} "
               f"{str(a.get('risk', '?')):<5}  {_what(a)}")
        if a.get("status") == "pending" and a.get("expires_at"):
            row += f"  (expires {a['expires_at']})"
        print(row)
    return EXIT_OK


def cmd_cancel(args: argparse.Namespace) -> int:
    ask_id = normalize_id(args.id)
    resp = _unwrap(_call("POST", _ask_path(ask_id, "/cancel"), body={}))
    print(f"{resp.get('id', ask_id)} {resp.get('status', 'cancelled')}")
    return EXIT_OK


def _sse_events(lines: Iterable[bytes]) -> Iterator[tuple[str, str]]:
    """(event, data) pairs from SSE lines: `event:`/`data:` fields, multi-line
    data joined with \\n, `:` comments skipped, a blank line dispatches."""
    event, data = "message", []
    for raw in lines:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if not line:
            if data:
                yield event, "\n".join(data)
            event, data = "message", []
            continue
        if line.startswith(":"):
            continue
        field, sep, value = line.partition(":")
        if sep and value.startswith(" "):
            value = value[1:]
        if field == "event":
            event = value or "message"
        elif field == "data":
            data.append(value)
    if data:  # a stream cut before its blank line still delivers what it carried
        yield event, "\n".join(data)


def cmd_tail(args: argparse.Namespace) -> int:
    ask_id = normalize_id(args.id)
    resp = _request("GET", _ask_path(ask_id, "/events"), accept="text/event-stream",
                    timeout=args.idle_timeout)
    final = None
    try:
        with resp:
            for name, data in _sse_events(resp):
                parsed = _maybe_json(data)
                if name == "output":
                    if isinstance(parsed, dict):
                        chunk = next((parsed[k] for k in ("chunk", "text", "data")
                                      if isinstance(parsed.get(k), str)), None)
                    else:
                        chunk = parsed if isinstance(parsed, str) else None
                    sys.stdout.write(chunk if chunk is not None else data + "\n")
                    sys.stdout.flush()
                elif name == "state":
                    status = parsed.get("status") if isinstance(parsed, dict) else (
                        parsed if isinstance(parsed, str) else data)
                    _say(f"[state] {status}")
                    if status in NO_RUN_STATES:
                        return EXIT_ENDED_BADLY
                    if status in TERMINAL_STATES:
                        final = status
                elif name == "end":
                    end = parsed if isinstance(parsed, dict) else {}
                    code, ms = end.get("exit_code"), end.get("duration_ms")
                    took = f" in {ms / 1000:.1f}s" if isinstance(ms, (int, float)) else ""
                    _say(f"[end] exit {code}{took}")
                    return EXIT_OK if code == 0 else EXIT_ENDED_BADLY
                elif name == "error":
                    _say(f"[error] {data}")
    except OSError as e:  # idle timeout or a dropped connection mid-stream
        raise HubError(f"event stream stalled or dropped: {e}") from None
    if final is not None:
        return EXIT_OK if final == "done" else EXIT_ENDED_BADLY
    _say(f"{ask_id}: the event stream closed before an end event; "
         f"check with: python3 tools/ask_run.py wait {ask_id}")
    return EXIT_HUB


# -------------------------------------------------------------------- CLI
def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools/ask_run.py",
        description="Run Inbox requester: put one command on the CEO's phone for a tap. "
                    "The CEO's tap is the only authority; this tool never approves.")
    sub = p.add_subparsers(dest="verb", required=True)

    c = sub.add_parser("create", help="create a card; prints its id and the phone URL")
    what = c.add_mutually_exclusive_group(required=True)
    what.add_argument("--script", metavar="REPO@SHA:PATH",
                      help="a script in a repo at a pushed commit; its args go after a final `--`")
    what.add_argument("--command", metavar="LINE",
                      help="freeform command line, sent byte-for-byte (C-level roles only)")
    c.add_argument("--host", required=True, help="target host id: contabo | mac | winbox")
    c.add_argument("--why", required=True, help="one line for the card: why this has to run")
    c.add_argument("--expected", help="one line for the card: what a good result looks like")
    c.add_argument("--risk", choices=RISKS, default=DEFAULT_RISK,
                   help="your claim (default amber); the hub can only raise it")
    c.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S, metavar="SECONDS",
                   help="run timeout once approved (default 300)")
    c.add_argument("--expects-input", action="store_true",
                   help="the process will wait on stdin (e.g. a login code typed on the phone)")
    c.add_argument("--shell", choices=SHELLS, help="override the host's default shell")
    c.add_argument("--cwd", help="working directory on the host")
    c.add_argument("--env-key", action="append", metavar="NAME",
                   help="env var NAME the executor may pass through (repeatable; never a value)")
    c.add_argument("--task", help="task id (default: WORKER_TASK_ID)")
    c.add_argument("--session", help="your mailbox name <role>-<id>, e.g. cto-6ebacd0e (default: from env)")
    c.add_argument("--role", help="your role (default: CXO_ROLE / WORKER_ROLE)")
    c.add_argument("--dry-run", action="store_true", help="print the JSON body, send nothing")
    c.add_argument("--json", action="store_true", help="print the hub's answer as JSON")

    w = sub.add_parser("wait", help="poll an ask until it ends; exit 0 done, 1 failed/denied/expired/cancelled")
    w.add_argument("id")
    w.add_argument("--interval", type=float, default=POLL_INTERVAL_S, metavar="SECONDS")
    w.add_argument("--max-wait", type=float, default=0, metavar="SECONDS",
                   help="give up after this long, exit 4 (default: until the ask ends)")
    w.add_argument("--lines", type=int, default=TAIL_LINES, help="output tail lines to print (0 = all)")
    w.add_argument("--json", action="store_true", help="print the final record as JSON")

    ls = sub.add_parser("list", help="your own asks")
    ls.add_argument("--status", help="pending | running | done | all (the hub's filter)")
    ls.add_argument("--limit", type=int, default=50)
    ls.add_argument("--json", action="store_true")

    x = sub.add_parser("cancel", help="cancel your own pending ask")
    x.add_argument("id")

    t = sub.add_parser("tail", help="stream an ask's live output (SSE) to stdout")
    t.add_argument("id")
    t.add_argument("--idle-timeout", type=float, default=None, metavar="SECONDS",
                   help="give up when nothing arrives for this long (default: never)")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    script_args: list[str] = []
    if "--" in argv:  # `create --script repo@sha:path -- args...`
        cut = argv.index("--")
        argv, script_args = argv[:cut], argv[cut + 1:]
    parser = _parser()
    args = parser.parse_args(argv)
    if script_args and args.verb != "create":
        parser.error("`-- args...` only go with create --script")
    try:
        if args.verb == "create":
            return cmd_create(args, script_args)
        if args.verb == "wait":
            return cmd_wait(args)
        if args.verb == "list":
            return cmd_list(args)
        if args.verb == "cancel":
            return cmd_cancel(args)
        return cmd_tail(args)
    except Refused as e:
        _say(f"ask_run: refused: {e}")
        return EXIT_REFUSED
    except HubError as e:
        _say(f"ask_run: {e}")
        return EXIT_HUB
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):  # Thai on a Windows console (winbox, P2)
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    sys.exit(main())
