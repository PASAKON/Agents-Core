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

    python3 tools/ask_run.py ask --question "Ship tonight or tomorrow?" \\
        --option "Tonight" --option "Tomorrow 09:00" --recommended 1 --why "..."
    python3 tools/ask_run.py wait Q-...    # polls the hub for the CEO's tap
    python3 tools/ask_run.py list --questions
    python3 tools/ask_run.py cancel Q-...

    python3 tools/ask_run.py ask --batch questions.json   # 1-6 questions, one group
    python3 tools/ask_run.py wait QG-...   # until every question in the group has ended

A command that SPENDS credit carries a spend label (CEO 2026-10-14, Console docs/run.md §Spend label):
    python3 tools/ask_run.py create --host contabo --why "render EP62" \
        --command "python tools/fal_render.py --ep 62 --max-usd 1.5" \
        --spend-provider fal --spend-estimate 0.9 --spend-cap 1.5 --spend-how "4 x 15 s x $0.015/s"
The command is ONE simple command running one of our tools (python3 <repo script>.py, node <repo
script>.js or python3 -m tools.|scripts.|runners.<module>; no ; & | redirects $ ` backslash globs)
and carries the cap as --max-usd N / --max-credits N; a script ask
carries it in its args. balance_after defaults to the spend guard's openrouter/fal balance minus
the cap (with the snapshot time, balance_at). A command that only looks like spend: --no-spend "<reason>".
Under the hub's enforce mode a label runs only on a --script card with no --cwd, for a .py listed in
config/spend-tools.txt, pinned to origin/main's tip (a command card or a wrapper cannot tie the cap
to our reviewed tool); under warn (the default) any other labelled card is posted with the reason
it was not checked.

`create --dry-run` and `ask --dry-run` print the JSON body and call nothing (no
token needed). `<id>` is RUN-YYYYMMDD-HHMM-xxxx (a command card),
Q-YYYYMMDD-HHMM-xxxx (a question card) or QG-YYYYMMDD-HHMM-xxxx (a group of
questions), or the phone URL that ends in #<id>.

Several questions at once (CEO 2026-10-14, QUESTIONS.md §10): `ask --batch FILE`
(FILE is a JSON list, `-` = stdin) raises up to 6 questions as one group, shown
together on /run. Each item is {"question", "why", "options": [labels],
"recommended": 1-based or 0, "free_text": true|false}; the requester, host and
expiry are the group's (the flags), never an item's. Every item gets the same
checks as a lone `ask`. The CEO answers them and sends once: you get ONE letter
for everything he sent you, so one wake. `wait` on any Q- id in the group works
as before; `wait QG-...` returns when every question in it has ended.

A QUESTION card (docs/design/run-inbox/QUESTIONS.md, the contract this half
builds against) is a 2-4 option question the CEO answers with one tap on /run.
The same one rule holds: this tool creates, reads and cancels its own
question and has no verb that answers. The CEO's tap is the only authority:
the hub takes an answer from his passkey session only, and `wait Q-...` reads
THAT record from the hub (never the mailbox letter, which is a wake-up call
any process on the box could forge). A question never stands in for a command
card: anything that runs a command, spends money or touches a secret goes on
a command card (red = fresh Face ID).

The org MCP tools `ask_run` / `ask_ceo` / `ask_run_wait`
(lib/org_tools_registry.py, served by runners/cto_mcp_server.py in every
C-level session) call `mcp_ask()` / `mcp_ask_ceo()` / `wait_result()` below:
one implementation, same checks.

Refused here, BEFORE any network call (exit 2):
  - a secret-shaped value anywhere in the ask: the key family of
    scripts/contabo_blueprint.sh's final pass (a token/secret/password/
    api_key/private_key/client_secret/access_key assigned a literal value,
    a BEGIN ... PRIVATE KEY block) plus well-known token shapes (GitHub,
    sk-..., Slack, AWS, Google, GitLab, JWT, Bearer). Reference an env var by
    name ($NAME, --env-key NAME) or an Infisical path instead;
  - --command from a role that is not C-level: `c_level` in
    policies/agents.yaml, the list lib/config.is_c_level reads (CEO decision
    1, DESIGN §11). The hub runs the same gate (403 freeform_needs_c_level).
Refused here for `ask` too (QUESTIONS.md §3.2; exit 2, one stderr line each):
secret shapes in any field; a role that is not C-level (the hub: 403
question_needs_c_level); 2-4 options and the question / why / label limits;
a command-shaped (§5: the question, every label, every line of why) or
money-naming (§6: the question and every label) text, Unicode spaces read as
spaces; a worker process (WORKER_TASK_ID set) claiming a C-level role.
Refused for every card (CEO 2026-10-14, lib/ceo_text.py): more than the CEO
reads, 5 lines of 90 characters (a command card: why + expected, the command
itself exempt; a question card and each item of a group: question + why).

Hub:   RUN_INBOX_URL, default https://terminal.mooniex.com. For the question
       verbs (ask, wait/cancel Q-..., list --questions) it must be the bare
       address, http(s)://host[:port] and at most one trailing "/": a path,
       query or fragment would move where those calls go, so it is refused.
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

Exit codes: 0 ok (wait/tail: the ask ended `done`, the question `answered`) ·
1 the ask ended failed/denied/expired/cancelled (a question: expired or
cancelled) · 2 refused here or bad arguments · 3 no token, hub unreachable,
or hub error · 4 wait --max-wait elapsed first.

stdlib only (urllib) and Python 3.9+, so it runs on any box's python3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "https://terminal.mooniex.com"
URL_ENV = "RUN_INBOX_URL"
TOKEN_ENV = "RUN_INBOX_TOKEN"
TOKEN_FILE = Path(".config") / "mooniex" / "run-inbox.token"  # under the user's home
# Org restructure P2 (security review of Console task-fabda3b9, 2026-10-14): the
# token file is the C-level's. A Contabo worker has no token of its own, so it
# fell back to that file and the hub saw a C-level token: the Console's worker
# checks (freeform_needs_c_level, RUN_INBOX_WORKER_SCRIPTS=0) never met a
# worker. With this host flag on (lib/org_flags.py), a worker process uses
# RUN_INBOX_TOKEN (a worker token) or nothing. An honest-path guard: a worker
# running as the same unix user can still read the file itself.
WORKER_TOKEN_FLAG = "ORG_WORKER_TOKEN_ONLY"

# CEO decision 1 (DESIGN §11): freeform commands are for C-level roles only.
# The list is the org's own `c_level` key (see c_level_roles), never a copy here.
AGENTS_POLICY = ROOT / "policies" / "agents.yaml"
RISKS = ("green", "amber", "red")
SHELLS = ("bash", "powershell", "cmd")
TERMINAL_STATES = ("done", "failed", "denied", "expired", "cancelled")
NO_RUN_STATES = ("denied", "expired", "cancelled")  # ended without running
QUESTION_TERMINAL_STATES = ("answered", "expired", "cancelled")  # QUESTIONS.md §2
ANSWER_VIA = "operator_passkey_session"   # QUESTIONS.md §3.3; Console src/run/questions.js ANSWER_VIA

# QUESTIONS.md §3.1 limits.
QUESTION_MAX = 300
WHY_MAX = 1000
LABEL_MAX = 120
OPTIONS_MIN, OPTIONS_MAX = 2, 4
EXPIRES_DEFAULT_H = 24.0
EXPIRES_MIN_S, EXPIRES_MAX_S = 600, 604800   # 10 min .. 7 days (§2)
ASKS_PATH = "/api/run/asks"
QUESTIONS_PATH = "/api/run/questions"
GROUPS_PATH = "/api/run/question-groups"   # QUESTIONS.md §10
MEDIA_PATH = "/api/run/question-media"     # QUESTIONS.md §11: one raw upload per file
GROUP_MAX = 6                              # questions in one group (§10)
GROUP_TERMINAL_STATES = ("done",)          # a group is done when none of its questions is pending
GROUP_ITEM_KEYS = ("question", "why", "options", "recommended", "free_text")
BATCH_FILE_MAX = 64 * 1024

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
_QID_RE = re.compile(r"^Q-[0-9]{8}-[0-9]{4}-[0-9a-f]{4}\Z")   # QUESTIONS.md §2
_GID_RE = re.compile(r"^QG-[0-9]{8}-[0-9]{4}-[0-9a-f]{4}\Z")  # QUESTIONS.md §10


class Refused(Exception):
    """Refused here, before any network call (exit 2)."""


class HubError(Exception):
    """No token, the hub is unreachable, or it answered with an error (exit 3).
    `transient` marks what waiting can fix (unreachable, 5xx, 429); a missing
    token, a 4xx or a redirect never is."""

    def __init__(self, message: str, status: int | None = None, code: str | None = None,
                 transient: bool = False):
        super().__init__(message)
        self.status = status
        self.code = code
        self.transient = transient


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


_C_LEVEL_LINE = re.compile(r"^c_level:[ \t]*(?P<rest>[^#]*?)[ \t]*(?:#.*)?$")
_BLOCK_ITEM = re.compile(r"^[ \t]+-[ \t]*(?P<item>[^#\s]+)[ \t]*(?:#.*)?$")


def c_level_roles(path: Path | None = None) -> tuple[str, ...]:
    """The org's C-level roles: the top-level `c_level` list in
    policies/agents.yaml, the same key lib/config.is_c_level reads. Parsed
    with the stdlib (flow `[a, b]` or block `- a` form) so this tool needs no
    PyYAML; tests check it against yaml.safe_load. Fails closed: an unreadable
    file or a missing/empty key refuses the ask instead of guessing a list."""
    path = AGENTS_POLICY if path is None else path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        raise Refused(f"cannot read the C-level roles from {path}: {e.strerror or e}") from None
    for i, line in enumerate(lines):
        m = _C_LEVEL_LINE.match(line)
        if not m:
            continue
        rest = m.group("rest")
        items: list[str] = []
        if rest.startswith("[") and rest.endswith("]"):
            items = [x.strip().strip("'\"") for x in rest[1:-1].split(",")]
        elif not rest:
            for nxt in lines[i + 1:]:
                if not nxt.strip() or nxt.lstrip().startswith("#"):
                    continue
                item = _BLOCK_ITEM.match(nxt)
                if not item:
                    break
                items.append(item.group("item").strip("'\""))
        roles = tuple(r.lower() for r in items if r)
        if roles:
            return roles
        break
    raise Refused(f"no readable `c_level:` list in {path}; refusing rather than guessing who is C-level")


# A Project Head raises Run cards like a C-level (CEO 2026-10-14 ~17:35 TH, in CTO Main's chat:
# "PH ควรจบงานได้ด้วยตัวเอง ส่ง RUN ได้ทำได้เหมือน CXO ทุกอย่าง"). The hub still decides by token
# (src/run/create.js: via operator|clevel), and the CEO's tap stays the authority. Kept as a
# literal so this tool needs nothing beyond the stdlib (lib.roles.PH_ROLE).
PH_ROLE = "project_head"


def card_roles(path: Path | None = None) -> tuple[str, ...]:
    """The roles that may raise a Run card: the C-level list plus the Project Head."""
    return c_level_roles(path) + (PH_ROLE,)


def check_role_gate(payload: dict) -> None:
    if payload["kind"] != "command":
        return
    roles = card_roles()
    role = payload["requester"]["role"]
    if role not in roles:
        raise Refused(
            f"freeform_needs_c_level: --command is for C-level sessions ({'/'.join(roles)}, "
            f"policies/agents.yaml c_level); this requester is role {role!r}. Commit the script, "
            "push it, and ask with --script repo@sha:path (DESIGN §6, CEO decision 1).")


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
                      "(your C-level role, or dev for a worker)")
    worker = env.get("WORKER_TASK_ID")
    if worker and role in card_roles():   # whatever CXO_ROLE says: a worker env is never C-level or a PH
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


# ------------------------------------------------------------ the spend label
# Console docs/run.md §Spend label (CEO 2026-10-14). A card that spends credit carries provider,
# kind of credit, estimate, cap ("never more than"), balance left after and how it was computed, and
# the command carries the cap as --max-usd / --max-credits. The hub runs the same checks and also
# refuses (RUN_INBOX_SPEND_LABEL=enforce) a command that names a paying provider with no label;
# these copies fail before anything leaves the box. For openrouter and fal (usd) the balance left
# after comes from the spend guard's last snapshot (state/spend_guard/snapshots.jsonl) when the
# requester does not give one.
SPEND_UNITS = ("usd", "credits")
SPEND_BILLING = ("api", "account")
SPEND_GUARD_PROVIDERS = ("openrouter", "fal")
SPEND_GUARD_MAX_AGE_S = 3600
_SPEND_PROVIDER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")
_SPEND_MAX = 1e7
_SPEND_HOW_MAX = 300
_SPEND_BUDGET_MAX = 200
_SPEND_KEYS = ("provider", "billing", "unit", "estimate", "cap", "balance_after", "how", "budget")


def spend_guard_balance(provider: str, *, root: Path | None = None,
                        now: datetime | None = None) -> float | None:
    """The provider's balance in the spend guard's newest snapshot, or None (no file, not read OK,
    older than an hour). Read only; the guard itself runs on Contabo every 15 minutes."""
    got = spend_guard_reading(provider, root=root, now=now)
    return got[0] if got else None


def spend_guard_reading(provider: str, *, root: Path | None = None,
                        now: datetime | None = None) -> tuple[float, str] | None:
    """(balance, snapshot time as ISO UTC) from the spend guard's newest snapshot, or None."""
    base = root or Path(os.environ.get("ORG_ROOT") or ROOT)
    path = base / "state" / "spend_guard" / "snapshots.jsonl"
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 65536))
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        at = _ts(row.get("at"))
        rec = row.get(provider) or {}
        if at is None or not rec.get("ok") or not isinstance(rec.get("balance"), (int, float)):
            continue
        age = ((now or datetime.now(timezone.utc)) - at).total_seconds()
        if not 0 <= age <= SPEND_GUARD_MAX_AGE_S:
            return None
        return float(rec["balance"]), at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return None


# A labelled command must be ONE simple command running one of our tools, read by allowlists (the
# hub's simpleWords + capCheck, Console src/run/spend.js; cases shared byte for byte in
# tests/fixtures/spend-cap-flag.json): python3 <repo script>.py, node <repo script>.js or
# python3 -m tools.|scripts.|runners.<module>, plain words and quotes, no space or control
# character other than the ASCII space.
_UNQUOTED_REFUSED = frozenset(";&|()<>\n\r$`\\*?[]{}#")
_DQUOTE_REFUSED = frozenset("$`\\")
_PYTHON = frozenset({"python3", "python"})
_SCRIPT_PATH = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
_MODULE = re.compile(r"^(?:tools|scripts|runners)(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_CAP_NUMBER = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
_ODD_SPACE_WHY = "a space or control character other than the ASCII space"


def _odd_space(c: str) -> bool:
    r"""The JS class [\s\p{Cc}\p{Cf}\p{Z}] the hub refuses (the ASCII space aside)."""
    import unicodedata
    return c != " " and (c.isspace() or c == "﻿" or unicodedata.category(c) in ("Cc", "Cf", "Zs", "Zl", "Zp"))


def _repo_script(path: str, ext: str) -> bool:
    return bool(_SCRIPT_PATH.match(path)) and ".." not in path.split("/") and bool(re.search(ext, path))


def simple_words(command: str) -> tuple[list[str] | None, str | None]:
    """(words, None) for one simple command running one of our tools, else (None, why not)."""
    words: list[str] = []
    word: str | None = None
    quote = None
    for c in command:
        if quote == "'":
            if c == "'":
                quote = None
            elif _odd_space(c):
                return None, _ODD_SPACE_WHY
            else:
                word += c
            continue
        if quote == '"':
            if c == '"':
                quote = None
            elif c in _DQUOTE_REFUSED:
                return None, f"{c} inside double quotes"
            elif _odd_space(c):
                return None, _ODD_SPACE_WHY
            else:
                word += c
            continue
        if c in " \t":
            if word is not None:
                words.append(word)
            word = None
            continue
        if c in _UNQUOTED_REFUSED:
            return None, "a line break" if c in "\n\r" else f"an unquoted {c}"
        if _odd_space(c):
            return None, _ODD_SPACE_WHY
        if word is None:
            word = ""
        if c in "'\"":
            quote = c
        else:
            word += c
    if quote:
        return None, "an unclosed quote"
    if word is not None:
        words.append(word)
    if not words:
        return None, "no program"
    program, first, second = (words + [None, None])[:3]
    allowed = ((program in _PYTHON and first == "-m" and second is not None and _MODULE.match(second))
               or (program in _PYTHON and first is not None and _repo_script(first, r"\.py$"))
               or (program == "node" and first is not None and _repo_script(first, r"\.(?:mjs|cjs|js)$")))
    if not allowed:
        return None, ("only python3 <repo script>.py, python3 -m tools.|scripts.|runners.<module> or "
                      f"node <repo script>.js runs under a label (got {program[:40]})")
    return words, None


def cap_flag_check(command: str, unit: str, cap: float, *, argv: list[str] | None = None) -> str | None:
    """None when the command is one simple command of ours whose every flag for `unit` is the plain
    number `cap`; otherwise the hub's refusal code: spend_command_not_simple |
    spend_cap_flag_missing | spend_cap_flag_mismatch (1e3, '100 ', no value) |
    spend_cap_flag_ambiguous (a name argparse would expand to a cap flag: --max, --ma=100, --max-u,
    --max-usd-..., or any cap-like word after a bare --). Words split at the first = like argparse.
    `argv` (a script ask: [path, *args]) skips the program reading."""
    if argv:
        if any(_odd_space(c) for w in argv for c in str(w)):
            return "spend_command_not_simple"
        words = [str(w) for w in argv]
    else:
        words, _why = simple_words(command)
        if words is None:
            return "spend_command_not_simple"
    flag = "--max-usd" if unit == "usd" else "--max-credits"
    other = "--max-credits" if unit == "usd" else "--max-usd"

    def cap_like(name: str) -> bool:
        return len(name) >= 3 and (flag.startswith(name) or other.startswith(name)
                                   or bool(re.match(r"--max-[uc]", name)))

    values: list[float | None] = []
    positional = False
    i = 1
    while i < len(words):
        w = words[i]
        i += 1
        if not w.startswith("--"):
            continue
        if w == "--" and not positional:
            positional = True
            continue
        name, eq, rest = w.partition("=")
        if " " in name:
            continue
        if positional:
            if cap_like(name):
                return "spend_cap_flag_ambiguous"
            continue
        if name == other:
            # its value is skipped only when it is one: a following -word is a flag of its own
            # (hub review round 4 MED-2)
            if not eq and i < len(words) and not words[i].startswith("-"):
                i += 1
            continue
        if name == flag:
            if eq:
                value = rest
            else:
                value = words[i] if i < len(words) else None
                i += 1
            values.append(float(value) if value is not None and _CAP_NUMBER.match(value) else None)
            continue
        if cap_like(name):
            return "spend_cap_flag_ambiguous"
    if not values:
        return "spend_cap_flag_missing"
    return "spend_cap_flag_mismatch" if any(v != cap for v in values) else None


def _spend_amount(name: str, value: Any, *, allow_negative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value \
            or abs(value) > _SPEND_MAX or (value < 0 and not allow_negative):
        raise Refused(f"invalid_spend: {name} is a number from 0 to {_SPEND_MAX:g}")
    if abs(round(value, 4) - value) > 1e-12:
        raise Refused(f"invalid_spend: {name} takes at most 4 decimal places")
    return float(value)


def build_spend(spend: dict | None, no_spend: str | None, command_text: str,
                *, argv: list[str] | None = None, root: Path | None = None,
                now: datetime | None = None) -> tuple[str, Any] | None:
    """('spend', label) | ('no_spend', reason) | None, with the hub's checks run first."""
    if spend and no_spend:
        raise Refused("spend_label_conflict: give a spend label or --no-spend, not both")
    if no_spend is not None:
        reason = _one_line("--no-spend", no_spend)
        if len(reason) > _SPEND_HOW_MAX:
            raise Refused(f"invalid_no_spend: at most {_SPEND_HOW_MAX} characters")
        return ("no_spend", reason)
    if not spend:
        return None
    unknown = sorted(set(spend) - set(_SPEND_KEYS))
    if unknown:
        raise Refused(f"invalid_spend: unknown field {unknown[0]!r} (fields: {', '.join(_SPEND_KEYS)})")
    provider = str(spend.get("provider") or "").strip().lower()
    if not _SPEND_PROVIDER_RE.match(provider):
        raise Refused("invalid_spend: provider is a short lowercase name like fal, openrouter, higgsfield")
    billing = spend.get("billing") or "api"
    unit = spend.get("unit") or "usd"
    if billing not in SPEND_BILLING:
        raise Refused(f"invalid_spend: billing is {' or '.join(SPEND_BILLING)}")
    if unit not in SPEND_UNITS:
        raise Refused(f"invalid_spend: unit is {' or '.join(SPEND_UNITS)}")
    if spend.get("estimate") is None or spend.get("cap") is None:
        raise Refused("invalid_spend: estimate and cap are required")
    estimate = _spend_amount("estimate", spend["estimate"])
    cap = _spend_amount("cap", spend["cap"])
    if cap <= 0:
        raise Refused("invalid_spend: cap is above 0")
    if estimate > cap:
        raise Refused("spend_estimate_over_cap: the estimate is above the cap")
    how = _one_line("spend how", str(spend.get("how") or ""))
    if len(how) > _SPEND_HOW_MAX:
        raise Refused(f"invalid_spend: how is at most {_SPEND_HOW_MAX} characters")
    label: dict[str, Any] = {"provider": provider, "billing": billing, "unit": unit,
                             "estimate": estimate, "cap": cap, "how": how}
    if spend.get("balance_after") is not None:
        label["balance_after"] = _spend_amount("balance_after", spend["balance_after"], allow_negative=True)
        label["balance_source"] = "declared"
    elif provider in SPEND_GUARD_PROVIDERS and unit == "usd":
        got = spend_guard_reading(provider, root=root, now=now)
        if got is not None:
            label["balance_after"] = round(got[0] - cap, 4)
            # the hub shows this as the requester's reading, with the snapshot's age (round 4 L1, L2)
            label["balance_source"] = "spend_guard"
            label["balance_at"] = got[1]
    if label.get("balance_after") is not None and label["balance_after"] < 0:
        raise Refused(f"spend_cap_over_balance: a cap of {cap:g} is more than the {provider} balance")
    if spend.get("budget"):
        budget = _one_line("spend budget", str(spend["budget"]))
        if len(budget) > _SPEND_BUDGET_MAX:
            raise Refused(f"invalid_spend: budget is at most {_SPEND_BUDGET_MAX} characters")
        label["budget"] = budget
    want = "--max-usd" if unit == "usd" else "--max-credits"
    why = {
        "spend_cap_flag_missing": f"the command must carry {want} {cap:g} (the tool stops there)",
        "spend_cap_flag_mismatch": f"every {want} in the command must be the plain number {cap:g}",
        "spend_cap_flag_ambiguous": f"a --word argparse would expand to {want} (--max, --max-u ...) is refused",
        "spend_command_not_simple": "a labelled command is ONE simple command: python3 <repo script>.py, "
                                    "node <repo script>.js or python3 -m tools.|scripts.|runners.<module>, "
                                    "no ; & | redirects $ ` backslash globs # or odd spaces",
    }
    code = cap_flag_check(command_text, unit, cap, argv=argv)
    if code == "spend_command_not_simple":
        code_why = _ODD_SPACE_WHY if argv else simple_words(command_text)[1]
        raise Refused(f"{code} ({code_why}): {why[code]}")
    if code:
        raise Refused(f"{code}: {why[code]}")
    return ("spend", label)


def _spend_from_args(args: argparse.Namespace) -> dict | None:
    """The create flags (--spend-*) as a label dict; None when none was given. The MCP path sets
    args.spend directly."""
    if getattr(args, "spend", None):
        return args.spend
    got = {k: getattr(args, f"spend_{k}", None) for k in _SPEND_KEYS}
    return {k: v for k, v in got.items() if v is not None} or None


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
            raise Refused("script arguments go with a script ask; with a command, put the whole line "
                          "in the command")
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
    # A script ask's args are an argv the hub quotes itself, so its cap is read from [path, *args]
    # (the hub renders it as `bash x.sh ...`, which the simple-command rule would refuse).
    argv = [payload["script"]["path"], *script_args] if payload.get("kind") == "script" else None
    spent = build_spend(_spend_from_args(args), getattr(args, "no_spend", None),
                        payload.get("command") or "", argv=argv)
    if spent:
        payload[spent[0]] = spent[1]
    return payload


# ------------------------------------------------------- the question card
# QUESTIONS.md §5 and §6, carried here as the same rule lists and the same test
# table (tests/test_ask_run_questions.py) the Console's JS copy is held to. The
# hub refuses the same texts (command_shaped / money_needs_command_card); this
# copy makes the refusal happen before anything leaves the box. A rule is
# named in the message, the text itself never is.
_CMD_WORDS = (
    "sudo rm mv cp chmod chown kill pkill killall systemctl service journalctl docker kubectl git gh "
    "npm npx node pnpm yarn pip pip3 python python3 bash sh zsh ssh scp rsync curl wget tmux crontab "
    "launchctl brew apt apt-get dnf yum infisical psql mysql sqlite3 dropdb createdb make terraform "
    "ansible pwsh powershell cmd schtasks taskkill reg eval exec export source cd ls cat echo tee dd "
    "mkfs shutdown reboot ln find sed awk xargs openssl ufw iptables").split()
_PS_WORDS = "Remove-Item Set-Item Invoke-WebRequest Invoke-Expression iwr iex".split()


def _any_of(words: list[str]) -> str:
    return "(?:" + "|".join(re.escape(w) for w in words) + ")"


_COMMAND_SHAPES = (
    ("a backtick, $( or ${", re.compile(r"`|\$\(|\$\{")),
    ("&& or ||", re.compile(r"&&|\|\|")),
    ("a pipe into a word", re.compile(r"(^|\s)\|\s*[A-Za-z]")),
    ("a redirect to a path", re.compile(r"(^|\s)>>?\s*[/~.]")),
    ("a CLI flag", re.compile(r"(^|\s)--[A-Za-z]|(^|\s)-[A-Za-z]{1,4}(?=\s|$)")),
    ("a path", re.compile(r"^(?:\.{1,2}|~)?/\S")),
    ("a shell script name", re.compile(r"\b[\w.-]+\.(?:sh|ps1|bat)\b", re.IGNORECASE)),
    # an optional lead word (any case), then a lowercase command word, or a
    # PowerShell one in any case, then a space: "Make it bigger" passes.
    ("a command line", re.compile(r"^(?:(?i:run|execute|exec|รัน|สั่ง)\s+)?(?:" + _any_of(_CMD_WORDS)
                                  + "|(?i:" + _any_of(_PS_WORDS) + ")) ")),
)
# §6 as amended 2026-10-13, pattern for pattern (tests/test_ask_run_questions.py pins the text).
_MONEY_SHAPES = (
    ("a currency sign before a digit", re.compile(r"[$฿€£¥₹]\s*\d")),
    ("an amount in a currency", re.compile(
        r"\d[\d,.]*\s*[kKmM]?\s*(?:usd|thb|baht|eur|gbp|inr|dollars?|bucks?|pounds?|บาท|ดอลลาร์|ดอลล่าร์)",
        re.IGNORECASE)),
    ("a currency code before a digit", re.compile(r"\b(?:usd|thb|eur|gbp|inr)\s*\d", re.IGNORECASE)),
    ("an amount of credits", re.compile(r"\d[\d,.]*\s*[kKmM]?\s*(?:credits?|เครดิต)", re.IGNORECASE)),
)
# Characters the CEO cannot see on the card but a string compare would: control
# and format characters (zero-width, bidi overrides), line / paragraph
# separators. A newline is the one allowed exception, and only inside `why`.
_HIDDEN_CATEGORIES = ("Cc", "Cf", "Cs", "Zl", "Zp")


def _ascii_spaces(text: str) -> str:
    """Every Unicode space (category Zs: NBSP, thin space, ideographic space ...)
    becomes an ASCII space before §5 / §6 match (QUESTIONS.md §5): the rules
    look for a literal space after a command word, and `git\\u00a0push` is a
    command the CEO reads as `git push`."""
    return "".join(" " if unicodedata.category(c) == "Zs" else c for c in text)


def command_shaped(text: str) -> str | None:
    """The name of the first §5 rule `text` matches, else None."""
    text = _ascii_spaces(text).strip()
    for name, rx in _COMMAND_SHAPES:
        if rx.search(text):
            return name
    return None


def money_shaped(text: str) -> str | None:
    """The name of the first §6 rule `text` matches, else None."""
    text = _ascii_spaces(text)
    for name, rx in _MONEY_SHAPES:
        if rx.search(text):
            return name
    return None


def _has_hidden_char(text: str, *, newline_ok: bool = False) -> bool:
    return any(unicodedata.category(c) in _HIDDEN_CATEGORIES and not (newline_ok and c == "\n")
               for c in text)


def _self_host_id() -> str | None:
    """lib.config.self_host(), when this checkout's `lib` is importable and
    resolves (PyYAML + config/hosts.yaml); None on any failure. The repo root
    goes on the END of sys.path so `python3 tools/ask_run.py` can find `lib`
    without it shadowing anything already importable."""
    try:
        if str(ROOT) not in sys.path:
            sys.path.append(str(ROOT))
        from lib.config import self_host
        return str(self_host()).strip().lower() or None
    except Exception:  # noqa: BLE001 - any failure means "fall back to the hostname"
        return None


def resolve_host(flag: str | None, env: dict | None = None) -> str:
    """requester.host (QUESTIONS.md §9): --host, else ORG_HOST, else
    lib.config.self_host() when importable, else the lowercased short hostname."""
    env = os.environ if env is None else env
    host = ((flag or "").strip() or (env.get("ORG_HOST") or "").strip() or _self_host_id()
            or socket.gethostname().split(".")[0]).strip().lower()
    if not _HOST_RE.match(host):
        raise Refused(f"cannot tell which machine this session runs on (got {host!r}): "
                      "pass --host contabo | mac | winbox")
    return host


def _expires_s(hours: Any) -> int:
    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or hours != hours \
            or hours in (float("inf"), float("-inf")):
        raise Refused("invalid_expires_in_s: --expires-h is a number of hours (default 24)")
    return int(round(hours * 3600))


def build_question(args: argparse.Namespace, env: dict | None = None) -> dict:
    """The POST /api/run/questions body (QUESTIONS.md §3.1), in the contract's
    field order, before the content checks. Only the fields §3.1 names are
    ever set: there is no field here that could carry an answer (§1.2), and
    `--recommended N` (1-based) becomes `recommended: true` on that option."""
    who = resolve_requester(args.session, args.role, getattr(args, "task", None), env)
    requester: dict[str, Any] = {"session": who["session"], "role": who["role"],
                                 "host": resolve_host(args.host, env)}
    if "task" in who:
        requester["task"] = who["task"]
    options = []
    for i, label in enumerate(args.option or []):
        option: dict[str, Any] = {"label": (label or "").strip()}
        if args.recommended == i + 1:
            option["recommended"] = True
        options.append(option)
    body: dict[str, Any] = {
        "question": (args.question or "").strip(),
        "why": (args.why or "").replace("\r\n", "\n").replace("\r", "\n").strip(),
        "options": options,
        "free_text": not args.no_free_text,
        "expires_in_s": _expires_s(args.expires_h),
        "requester": requester,
    }
    paths, captions = list(getattr(args, "media", None) or []), list(getattr(args, "caption", None) or [])
    if paths:        # QUESTIONS.md §11: ids are filled in once the files are uploaded
        if not options:
            del body["options"]
        body["media"] = [{"caption": (captions[i] or "").strip()} if i < len(captions) and (captions[i] or "").strip()
                         else {} for i in range(len(paths))]
        if getattr(args, "pick", None) is not None:
            body["pick"] = args.pick
    elif captions or getattr(args, "pick", None) is not None:
        raise Refused("invalid_media: --caption and --pick go with --media")
    return body


def check_question_role_gate(body: dict) -> None:
    """QUESTIONS.md §1.6: C-level only. The hub answers a worker's token with
    403 question_needs_c_level; this refuses the role before sending."""
    roles = card_roles()
    role = body["requester"]["role"]
    if role not in roles:
        raise Refused(
            f"question_needs_c_level: a question card is for C-level sessions ({'/'.join(roles)}, "
            f"policies/agents.yaml c_level); this requester is role {role!r}. A worker reports to "
            "its C-level session, which asks the CEO.")


def check_question(body: dict, args: argparse.Namespace) -> None:
    """QUESTIONS.md §3.1 limits, then §5 (command_shaped), then §6
    (money_needs_command_card), in the order §3.2 lists the hub's refusals.
    Messages name the field and the rule, never the text."""
    question, why, options = body["question"], body["why"], body.get("options") or []
    if not question:
        raise Refused("question_required: --question is empty")
    if "\n" in question or "\r" in question or len(question) > QUESTION_MAX:
        raise Refused(f"invalid_question: one line, at most {QUESTION_MAX} characters "
                      f"(got {len(question)})")
    if not why:
        raise Refused("why_required: --why is empty (the CEO reads it before tapping)")
    if len(why) > WHY_MAX:
        raise Refused(f"invalid_why: at most {WHY_MAX} characters (got {len(why)})")
    if "media" in body:
        check_media(body, args)      # a set has no options; one item may bring its own 2 to 4
    if options or "media" not in body:
        if not OPTIONS_MIN <= len(options) <= OPTIONS_MAX:
            raise Refused(f"invalid_options: {OPTIONS_MIN} to {OPTIONS_MAX} options "
                          f"(--option, repeatable), got {len(options)}")
    seen: dict[str, int] = {}
    for i, option in enumerate(options):
        label = option["label"]
        if not label or "\n" in label or "\r" in label or len(label) > LABEL_MAX:
            raise Refused(f"invalid_options: options[{i}].label is one line of 1 to {LABEL_MAX} characters")
        if label.casefold() in seen:
            raise Refused(f"invalid_options: options[{i}].label repeats options[{seen[label.casefold()]}]"
                          " (labels are unique, case-insensitive)")
        seen[label.casefold()] = i
    rec = args.recommended
    if rec is not None and (isinstance(rec, bool) or not isinstance(rec, int)
                            or not 1 <= rec <= len(options)):
        raise Refused(f"invalid_options: --recommended is an option number, 1 to {len(options)}")
    if not EXPIRES_MIN_S <= body["expires_in_s"] <= EXPIRES_MAX_S:
        raise Refused(f"invalid_expires_in_s: --expires-h is {EXPIRES_MIN_S / 3600:.2g} to "
                      f"{EXPIRES_MAX_S / 3600:g} hours (got {body['expires_in_s'] / 3600:g})")
    fields = [("question", question)] + [(f"options[{i}].label", o["label"]) for i, o in enumerate(options)]
    hidden_code = {"question": "invalid_question", "why": "invalid_why"}
    for field, text in fields + [("why", why)]:
        if _has_hidden_char(text, newline_ok=field == "why"):
            raise Refused(f"{hidden_code.get(field, 'invalid_options')}: {field} has a hidden "
                          "character (control, zero-width or bidi)")
    # §5 runs on the question, every label and every line of why, each line as its own text;
    # §6 (money) never on why: context may mention cost.
    why_lines = [(f"why (line {n})" if "\n" in why else "why", line)
                 for n, line in enumerate(why.split("\n"), 1)]
    for field, text in fields + why_lines:
        rule = command_shaped(text)
        if rule:
            raise Refused(f"command_shaped: {field} looks like a command ({rule}); a question is not a "
                          "command. Anything that runs a command, spends money or touches a secret "
                          "goes on a command card (ask_run create, Face ID).")
    for field, text in fields:
        rule = money_shaped(text)
        if rule:
            raise Refused(f"money_needs_command_card: {field} names an amount ({rule}); a question never "
                          "approves spend. Money goes on a command card (ask_run create, Face ID).")


def check_ceo_text(fields: Any) -> None:
    """lib/ceo_text.py: the CEO reads at most 5 lines of 90 characters on a card or a mail
    (CEO 2026-10-14). Refused when the text is longer; no flag skips it. The repo root goes on the
    END of sys.path, as in _self_host_id; a checkout that cannot load it fails closed (ImportError)."""
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    from lib import ceo_text
    try:
        ceo_text.check_ceo_text(fields)
    except ceo_text.TooLong as e:
        raise Refused(str(e)) from None


def prepare_question(args: argparse.Namespace, env: dict | None = None) -> dict:
    """The POST body with every local refusal already run, in §3.2's order:
    secret shapes over the whole body, the C-level gate, then the content
    checks. `ask` and the MCP tool `ask_ceo` both come here."""
    body = build_question(args, env)
    hits = find_secret_shapes(body)
    if hits:
        raise Refused("secret_shaped_value; nothing was sent: " + "; ".join(hits)
                      + ". A question carries no secret, ever (DESIGN §6).")
    check_question_role_gate(body)
    check_question(body, args)
    check_ceo_text([("question", body["question"]), ("why", body["why"])])
    return body


# ------------------------------------------------------------ media cards
# QUESTIONS.md §11 (the Console builds the hub half to the same section). A card may
# carry 1-12 pictures, videos or sounds the CEO looks at on /run and picks from. The card shows a
# PREVIEW; the sender keeps the master. Everything below runs BEFORE the first network call:
#   1. the path is a regular file (not a symlink, FIFO or device), opened once, and those bytes are
#      copied into a private file in the temp dir: the checks, ffprobe and ffmpeg read that copy and
#      never the path again, so a swap after the open (a symlink, another file) changes nothing;
#   2. the kind comes from the first bytes alone, never the name: picture JPEG/PNG/GIF/WebP, video
#      MP4/MOV/WebM, audio MP3/AAC/M4A/WAV/OGG. A `.jpg` that is HTML or SVG is refused here;
#   3. ffprobe reads it with the demuxer forced to the sniffed type and only the `file` protocol, so
#      a hostile container cannot become a playlist or a network fetch; a frame over 100 megapixels
#      (a decompression bomb) is refused;
#   4. shrink (§11.2): a picture with a long edge over 2048 px becomes 2048 (JPEG; WebP stays WebP);
#      a video becomes 720p H.264/AAC MP4 with +faststart (an MP4/MOV that already is one is only
#      re-wrapped) plus a poster JPEG at 0.5 s; audio that is not MP3/AAC/M4A becomes M4A AAC 128k;
#   5. the caps are checked on what will be uploaded: picture 10 MB, video 50 MB, audio 20 MB.
# Staged files, and the private copy of each source, live in a temp dir that is removed afterwards.
# No ffmpeg: refused, never uploaded untranscoded. Captions and file names pass the same §5 / §6 /
# secret checks as the question.
MEDIA_MAX = 12                # items on one card
CAPTION_MAX = 60              # characters under one item (§8.2)
MEDIA_NAME_MAX = 80           # characters of a file name shown on the card (§8.3)
MB = 1024 * 1024
MEDIA_CAPS = {"image": 10 * MB, "video": 50 * MB, "audio": 20 * MB}
IMAGE_EDGE = 2048             # long edge of an uploaded picture
VIDEO_HEIGHT = 720
MAX_PIXELS = 100_000_000
MAX_SOURCE_BYTES = 2048 * MB  # a source is copied into the temp dir whole before anything reads it (see
                              # stage_one), so it costs that much disk once; a phone clip of several minutes
                              # fits, anything bigger is cut down by hand first
STAGE_DISK_MARGIN = 128 * MB  # free space kept beyond that copy: the converted file (at most 50 MB + 1 byte),
                              # the poster (10 MB) and the items staged before it
POSTER_AT_S = ("0.5", "0")    # the poster frame; "0" is for a clip shorter than half a second
PROBE_TIMEOUT_S = 60
CONVERT_TIMEOUT_S = 900
UPLOAD_TIMEOUT_S = 300.0      # per socket operation, not for the whole 50 MB
FFMPEG_THREADS = "2"          # Contabo shares its RAM with every C-level session
PICKS = ("one", "many")
_MEDIA_ID_RE = re.compile(r"^M-[0-9a-f]{24}\Z")          # QUESTIONS.md §11
PENDING_MEDIA_ID = "M-<uploaded when sent>"
FFMPEG_HINT = ("ffmpeg and ffprobe are needed to shrink media before it is uploaded and one is not on PATH. "
               "Install them: apt-get install ffmpeg (Contabo), brew install ffmpeg (Mac), "
               "winget install Gyan.FFmpeg (winbox). Nothing is uploaded without them.")
VIDEO_HINT = ("cut it shorter or lower the quality, for example: ffmpeg -i IN -vf scale=-2:480 "
              "-c:v libx264 -crf 32 -preset veryfast -c:a aac -b:a 64k OUT.mp4")

# fmt -> (kind, extension, ffmpeg demuxer forced when reading it)
MEDIA_FORMATS = {
    "jpeg": ("image", ".jpg", "jpeg_pipe"), "png": ("image", ".png", "png_pipe"),
    "gif": ("image", ".gif", "gif"), "webp": ("image", ".webp", "webp_pipe"),
    "mp4": ("video", ".mp4", "mov"), "mov": ("video", ".mov", "mov"),
    "webm": ("video", ".webm", "matroska"),
    "mp3": ("audio", ".mp3", "mp3"), "aac": ("audio", ".aac", "aac"), "m4a": ("audio", ".m4a", "mov"),
    "wav": ("audio", ".wav", "wav"), "ogg": ("audio", ".ogg", "ogg"),
}
_VIDEO_BRANDS = (b"isom", b"iso2", b"iso5", b"mp41", b"mp42", b"avc1", b"M4V ")   # QUESTIONS.md §11
_AUDIO_BRANDS = (b"M4A ", b"M4B ")                                                 # QUESTIONS.md §11
_FFMPEG_BASE = ["-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-threads", FFMPEG_THREADS,
                "-protocol_whitelist", "file"]


@dataclass
class Staged:
    """One item ready to upload: the file to send (inside the temp dir) and what to say about it."""
    index: int
    name: str
    kind: str
    path: Path
    size: int
    sha256: str
    source_size: int
    note: str
    poster: Path | None = None
    poster_size: int = 0
    poster_sha256: str = ""


def media_name(path: str) -> str:
    """The file's base name for the card and the answer (§8.3): any path part, control and format
    characters (zero-width, bidi marks) and line separators gone, cut to MEDIA_NAME_MAX. It is text
    only and never reaches a path."""
    base = os.path.basename(str(path).replace("\\", "/"))
    clean = "".join(c for c in base if unicodedata.category(c) not in _HIDDEN_CATEGORIES)
    return clean.strip()[:MEDIA_NAME_MAX].strip()


def sniff_media(head: bytes) -> str | None:
    """The MEDIA_FORMATS key the first bytes say, else None. Magic bytes only (QUESTIONS.md §11):
    no SVG, HTML or PDF, and an ftyp brand outside the two lists is refused."""
    if head[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:4] == b"RIFF":
        return "webp" if head[8:12] == b"WEBP" else "wav" if head[8:12] == b"WAVE" else None
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand == b"qt  ":
            return "mov"
        return "mp4" if brand in _VIDEO_BRANDS else "m4a" if brand in _AUDIO_BRANDS else None
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:3] == b"ID3":
        return "mp3"
    if len(head) >= 2 and head[0] == 0xFF:
        if head[1] & 0xF6 == 0xF0:          # ADTS: sync, layer bits 00
            return "aac"
        if head[1] & 0xE0 == 0xE0:          # MPEG audio frame sync, not ADTS
            return "mp3"
    return None


def _mb(n: int) -> str:
    return f"{n / MB:.1f} MB" if n >= MB // 10 else f"{n / 1024:.0f} KB"


def find_ffmpeg() -> tuple[str, str]:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not (ffmpeg and ffprobe):
        raise Refused("ffmpeg_missing: " + FFMPEG_HINT)
    return ffmpeg, ffprobe


def _run_tool(cmd: list[str], timeout: float) -> subprocess.CompletedProcess:
    """Run one tool with no stdin and a deadline: the one place a subprocess starts."""
    try:
        return subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise Refused(f"invalid_media: {os.path.basename(cmd[0])} ran longer than {timeout:g} s "
                      "and was stopped") from None
    except OSError as e:
        raise Refused(f"ffmpeg_missing: could not start {os.path.basename(cmd[0])} "
                      f"({e.strerror or e}). {FFMPEG_HINT}") from None


def _tool_said(cp: subprocess.CompletedProcess) -> str:
    lines = (cp.stderr or b"").decode("utf-8", "replace").strip().splitlines()
    return (lines[-1] if lines else f"exit {cp.returncode}")[:160]


def _media_stream(info: dict, codec_type: str) -> dict | None:
    for s in info.get("streams") or []:
        if isinstance(s, dict) and s.get("codec_type") == codec_type \
                and not (s.get("disposition") or {}).get("attached_pic"):
            return s
    return None


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _open_regular(path: str, refuse: Callable[[str, str], Refused]) -> tuple[int, int]:
    """(fd, size) of a regular, non-empty file. A symlink is refused (the final component), so the
    bytes read are the bytes of the path given; a FIFO or a device never blocks the open."""
    try:
        if stat.S_ISLNK(os.lstat(path).st_mode):
            raise refuse("invalid_media", "is a symlink; pass the real file")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
                     | getattr(os, "O_BINARY", 0))
    except FileNotFoundError:
        raise refuse("invalid_media", "does not exist") from None
    except OSError as e:
        raise refuse("invalid_media", f"cannot be opened ({e.strerror or e})") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise refuse("invalid_media", "is not a regular file")
        if st.st_size == 0:
            raise refuse("invalid_media", "is empty")
    except Refused:
        os.close(fd)
        raise
    return fd, st.st_size


def _copy_capped(fd: int, dst: Path, cap: int) -> int:
    """Copy the fd's bytes from the start into a NEW file dst (O_EXCL, mode 0600: nothing already at that
    name is followed or overwritten), at most cap + 1 of them; returns how many."""
    os.lseek(fd, 0, os.SEEK_SET)
    total = 0
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(dst, flags, 0o600), "wb") as out:
        while total <= cap:
            chunk = os.read(fd, min(1 << 20, cap + 1 - total))
            if not chunk:
                break
            out.write(chunk)
            total += len(chunk)
    return total


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sniff_file(path: Path) -> str | None:
    with open(path, "rb") as f:
        return sniff_media(f.read(64))


def _probe(ffprobe: str, path: str, fmt: str, refuse: Callable[[str, str], Refused]) -> dict:
    """ffprobe's streams and format for `path`, read as the sniffed type and nothing else."""
    cmd = [ffprobe, "-hide_banner", "-loglevel", "error", "-protocol_whitelist", "file",
           "-f", MEDIA_FORMATS[fmt][2], "-print_format", "json", "-show_streams", "-show_format",
           "-i", "file:" + path]
    cp = _run_tool(cmd, PROBE_TIMEOUT_S)
    if cp.returncode != 0:
        raise refuse("invalid_media", f"is not a readable {MEDIA_FORMATS[fmt][0]} ({_tool_said(cp)})")
    try:
        info = json.loads(cp.stdout or b"{}")
    except ValueError:
        raise refuse("invalid_media", "gave ffprobe no usable answer") from None
    return info if isinstance(info, dict) else {}


def _too_large(refuse: Callable[[str, str], Refused], kind: str, size: int | None, after: str,
               cap: int | None = None) -> Refused:
    cap = MEDIA_CAPS[kind] if cap is None else cap
    shown = _mb(size) if size is not None else f"more than {_mb(cap)}"
    hint = f"; {VIDEO_HINT}" if kind == "video" else ""
    return refuse("too_large", f"is {shown} {after}, over the {_mb(cap)} cap for a {kind}{hint}")


def _convert_args(how: str, path: str, fmt: str, out_fmt: str) -> list[str]:
    """ffmpeg arguments between the base options and `-fs N OUT`."""
    src = ["-f", MEDIA_FORMATS[fmt][2], "-i", "file:" + path]
    if how == "image":
        codec = ["-c:v", "libwebp", "-quality", "80"] if out_fmt == "webp" \
            else ["-c:v", "mjpeg", "-q:v", "3", "-pix_fmt", "yuvj420p"]
        return src + ["-frames:v", "1", "-an", "-map_metadata", "-1", "-vf",
                      f"scale=w={IMAGE_EDGE}:h={IMAGE_EDGE}:force_original_aspect_ratio=decrease",
                      *codec, "-update", "1"]
    if how == "audio":
        return src + ["-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1", "-c:a", "aac",
                      "-b:a", "128k", "-movflags", "+faststart", "-f", "ipod"]
    codec = ["-c", "copy"] if how == "copy" else [
        "-vf", f"scale=-2:'min({VIDEO_HEIGHT},ih)'", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "28", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k"]
    return src + ["-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn", "-map_metadata", "-1", *codec,
                  "-movflags", "+faststart", "-f", "mp4"]


def _convert(ffmpeg: str, tail: list[str], out: Path, kind: str, expect: str,
             refuse: Callable[[str, str], Refused]) -> int:
    """Run one conversion into `out`; returns its size once it is under the cap and sniffs as
    `expect`. `-fs` stops the encoder one byte over the cap, so a huge source cannot fill the disk."""
    cp = _run_tool([ffmpeg, *_FFMPEG_BASE, *tail, "-fs", str(MEDIA_CAPS[kind] + 1), str(out)],
                   CONVERT_TIMEOUT_S)
    if cp.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        raise refuse("invalid_media", f"could not be converted by ffmpeg ({_tool_said(cp)})")
    size = out.stat().st_size
    if size > MEDIA_CAPS[kind]:
        raise _too_large(refuse, kind, None, "after the shrink")
    if _sniff_file(out) != expect:
        raise refuse("invalid_media", "came out of ffmpeg as an unexpected file type; not uploaded")
    return size


def _poster(ffmpeg: str, video: Path, out: Path, refuse: Callable[[str, str], Refused]) -> int:
    """The poster JPEG of a staged (already shrunk) video: the frame at 0.5 s, else the first."""
    for at in POSTER_AT_S:
        out.unlink(missing_ok=True)
        tail = ["-ss", at, "-f", "mov", "-i", "file:" + str(video), "-frames:v", "1", "-an",
                "-map_metadata", "-1", "-vf", f"scale=-2:'min({VIDEO_HEIGHT},ih)'",
                "-c:v", "mjpeg", "-q:v", "4", "-pix_fmt", "yuvj420p", "-update", "1"]
        cp = _run_tool([ffmpeg, *_FFMPEG_BASE, *tail, "-fs", str(MEDIA_CAPS["image"] + 1), str(out)],
                       CONVERT_TIMEOUT_S)
        if cp.returncode == 0 and out.is_file() and 0 < out.stat().st_size <= MEDIA_CAPS["image"] \
                and _sniff_file(out) == "jpeg":
            return out.stat().st_size
    raise refuse("invalid_media", "has no frame ffmpeg can take a poster from")


def _stage_source(fd: int, size: int, copy: Path, kind: str, refuse: Callable[[str, str], Refused]) -> int:
    """Copy the opened source into `copy` (a new private file in the work dir); returns its size. The size
    is checked first and again on what was read (the file may grow), and the disk must have room for the
    copy and what comes out of ffmpeg, so a full disk is a refusal and not a half-written file."""
    if size > MAX_SOURCE_BYTES:
        raise _too_large(refuse, kind, size, "as a source", MAX_SOURCE_BYTES)
    try:
        free = shutil.disk_usage(copy.parent).free
        if free < size + STAGE_DISK_MARGIN:
            raise refuse("no_space", f"needs {_mb(size + STAGE_DISK_MARGIN)} free in the temp dir to be checked "
                                     f"and shrunk and only {_mb(free)} is; free some space or point TMPDIR "
                                     "at a bigger disk")
        copied = _copy_capped(fd, copy, MAX_SOURCE_BYTES)
    except OSError as e:
        raise refuse("invalid_media", f"could not be copied for checking ({e.strerror or e})") from None
    if copied > MAX_SOURCE_BYTES:
        raise _too_large(refuse, kind, copied, "as a source", MAX_SOURCE_BYTES)
    return copied


def stage_one(src: str, work_dir: Path, index: int, tools: tuple[str, str]) -> Staged:
    """One file -> a Staged item in `work_dir`, or a Refused naming the item and the rule."""
    ffmpeg, ffprobe = tools
    path = os.path.abspath(src)
    name = media_name(src) or f"item {index + 1}"

    def refuse(code: str, why: str) -> Refused:
        return Refused(f"{code}: media[{index}] {name} {why}")

    fd, size = _open_regular(path, refuse)
    src_copy = work_dir / f"{index}.src"     # what the checks and both tools read: `path` is never opened again
    try:
        fmt = sniff_media(os.read(fd, 64))   # from the open fd: a wrong type is refused before any copy is made
        if fmt is None:
            raise refuse("unsupported_media", "is not a picture (JPEG, PNG, GIF, WebP), video (MP4, MOV, "
                                              "WebM) or audio (MP3, M4A, AAC, WAV, OGG): its first bytes "
                                              "say something else (the file name is not looked at)")
        kind, ext, _demux = MEDIA_FORMATS[fmt]
        size = _stage_source(fd, size, src_copy, kind, refuse)
        if _sniff_file(src_copy) != fmt:
            raise refuse("invalid_media", "changed while it was being read; try again")
        info = _probe(ffprobe, str(src_copy), fmt, refuse)
        how: str | None = None           # None = upload the file as it is
        out_fmt, note = fmt, ""
        if kind == "image":
            v = _media_stream(info, "video")
            w, h = (_int(v.get("width")), _int(v.get("height"))) if v else (0, 0)
            if w <= 0 or h <= 0:
                raise refuse("invalid_media", "is a picture ffprobe cannot measure")
            if w * h > MAX_PIXELS:
                raise refuse("invalid_media", f"is {w}x{h} px, over {MAX_PIXELS // 1_000_000} megapixels; "
                                              "cut it down first")
            if max(w, h) > IMAGE_EDGE:
                how, out_fmt = "image", "webp" if fmt == "webp" else "jpeg"
                note = f"{w}x{h} shrunk to {IMAGE_EDGE} px"
        elif kind == "video":
            v, a = _media_stream(info, "video"), _media_stream(info, "audio")
            if v is None:
                raise refuse("invalid_media", "has no picture track")
            if _int(v.get("width")) * _int(v.get("height")) > MAX_PIXELS:
                raise refuse("invalid_media", f"has a frame over {MAX_PIXELS // 1_000_000} megapixels")
            copy = (fmt in ("mp4", "mov") and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p"
                    and 0 < _int(v.get("height")) <= VIDEO_HEIGHT
                    and (a is None or a.get("codec_name") == "aac"))
            how, out_fmt = ("copy" if copy else "video"), "mp4"
            note = "re-wrapped as MP4" if copy else f"shrunk to {VIDEO_HEIGHT}p H.264"
        else:
            if _media_stream(info, "audio") is None:
                raise refuse("invalid_media", "has no sound track")
            if fmt not in ("mp3", "aac", "m4a"):
                how, out_fmt, note = "audio", "m4a", "converted to M4A AAC 128k"
        dst = work_dir / f"{index}{MEDIA_FORMATS[out_fmt][1]}"
        if how is None:
            if size > MEDIA_CAPS[kind]:
                raise _too_large(refuse, kind, size, "as it is")
            os.replace(src_copy, dst)        # the bytes that were probed are the bytes that go out
            out_size = dst.stat().st_size
        else:
            out_size = _convert(ffmpeg, _convert_args(how, str(src_copy), fmt, out_fmt), dst, kind, out_fmt, refuse)
    finally:
        os.close(fd)
        src_copy.unlink(missing_ok=True)
    staged = Staged(index, name, kind, dst, out_size, _sha256_file(dst), size, note)
    if kind == "video":
        poster = work_dir / f"{index}.poster.jpg"
        staged.poster_size = _poster(ffmpeg, dst, poster, refuse)
        staged.poster, staged.poster_sha256 = poster, _sha256_file(poster)
    return staged


def stage_media(paths: list[str], work_dir: Path) -> list[Staged]:
    """Stage every file in order, or raise on the first that cannot go. The tools are looked for
    once, first: no ffmpeg is the refusal whatever the files are."""
    tools = find_ffmpeg()
    return [stage_one(p, work_dir, i, tools) for i, p in enumerate(paths)]


def _name_header(name: str) -> str:
    """X-Media-Name: a header is latin-1, so a name with anything but printable ASCII (Thai!) or
    with a `%` goes out percent-encoded as UTF-8. The hub decodes it (QUESTIONS.md §11)."""
    plain = all(0x20 <= ord(c) < 0x7F for c in name) and "%" not in name
    return name if plain else urllib.parse.quote(name, safe="")


def upload_staged(path: Path, size: int, sha256: str, name: str, session: str) -> str:
    """POST one staged file (QUESTIONS.md §11) and return the hub's media id. X-Run-Session is the
    card's requester.session: the hub files the upload under it and attaches it only to a question
    from that same session. The hub's answer must agree with what was sent (size, sha256) or nothing
    is attached."""
    with open(path, "rb") as f:
        resp = _call("POST", MEDIA_PATH, raw=f, raw_length=size, timeout=UPLOAD_TIMEOUT_S,
                     headers={"X-Run-Session": session, "X-Media-Name": _name_header(name)})
    resp = _unwrap(resp)
    media_id = resp.get("media_id")
    if not isinstance(media_id, str) or not _MEDIA_ID_RE.match(media_id):
        raise HubError("hub accepted the upload but returned no valid media id")
    for key, sent in (("bytes", size), ("sha256", sha256)):
        if key in resp and resp[key] != sent:
            raise HubError(f"hub stored {key} {str(resp[key])[:80]!r} for an upload of {str(sent)[:80]!r}; "
                           "not attaching it")
    return media_id


def _staged_line(s: Staged) -> str:
    out = f"media[{s.index}] {s.name}: {s.kind} {_mb(s.source_size)}"
    if s.size != s.source_size or s.note:
        out += f" -> {_mb(s.size)}"
    if s.note:
        out += f" ({s.note})"
    return out + (" + poster" if s.poster else "")


def send_media_question(payload: dict, paths: list[str], *, dry_run: bool) -> tuple[dict, dict | None, list[str]]:
    """Stage every file, upload them (and the video posters), then POST the question with the
    media ids in (QUESTIONS.md §11). (body, hub's answer or None for a dry run, one line per item).
    The temp dir is gone before this returns; the hub drops an upload nobody attaches within 1 h."""
    with tempfile.TemporaryDirectory(prefix="ask-run-media-") as tmp:
        staged = stage_media(paths, Path(tmp))
        lines = [_staged_line(s) for s in staged]
        entries = []
        for s, m in zip(staged, payload["media"]):
            entry: dict[str, Any] = {"id": PENDING_MEDIA_ID}
            if m.get("caption"):
                entry["caption"] = m["caption"]
            if s.poster:
                entry["poster_id"] = PENDING_MEDIA_ID
            entries.append(entry)
        body = {**payload, "media": entries}
        if dry_run:
            return body, None, lines
        session = str((payload.get("requester") or {}).get("session") or "")
        for s, entry in zip(staged, entries):
            entry["id"] = upload_staged(s.path, s.size, s.sha256, s.name, session)
            if s.poster:
                entry["poster_id"] = upload_staged(s.poster, s.poster_size, s.poster_sha256,
                                                   f"{s.name}.poster.jpg"[:MEDIA_NAME_MAX], session)
        return body, submit_question(body), lines


def check_media(body: dict, args: argparse.Namespace) -> None:
    """The local checks of a media card that need no file: how many items, --pick, the options
    rule, free_text, and the caption and file-name texts. Messages name the field and the rule."""
    media, options = body["media"], body.get("options") or []
    n, pick = len(media), body.get("pick")
    if n > MEDIA_MAX:
        raise Refused(f"too_many_media: {n} items; a card holds at most {MEDIA_MAX}")
    paths = list(args.media or [])
    if len(args.caption or []) > n:
        raise Refused(f"invalid_media: {len(args.caption)} captions for {n} items (they match by order)")
    if pick is not None and pick not in PICKS:
        raise Refused(f"invalid_pick: --pick is one or many (got {str(pick)[:20]!r})")
    if n == 1 and pick == "many":
        raise Refused("invalid_pick: one item has nothing to pick many of; use --pick one or leave it out")
    if n >= 2 and pick is None:
        raise Refused(f"pick_required: {n} items need --pick one (he taps one) or --pick many (he ticks any)")
    if n >= 2 and options:
        raise Refused("options_not_allowed: a card with 2 or more items has no options; the items are "
                      "the choices (A, B, C ...)")
    if not options and args.recommended is not None:
        raise Refused("invalid_options: --recommended names one of the options you give (a one-item "
                      "card with --option); the items of a set are not recommended")
    if args.no_free_text:
        raise Refused("invalid_free_text: a media card always has the optional note")
    texts = [(f"media[{i}].caption", m["caption"]) for i, m in enumerate(media) if m.get("caption")]
    for field, text in texts:
        if "\n" in text or "\r" in text or len(text) > CAPTION_MAX:
            raise Refused(f"invalid_caption: {field} is one line of at most {CAPTION_MAX} characters "
                          f"(got {len(text)})")
        if _has_hidden_char(text):
            raise Refused(f"invalid_caption: {field} has a hidden character (control, zero-width or bidi)")
    names = [(f"media[{i}] file name", media_name(p)) for i, p in enumerate(paths)]
    for field, text in texts + names:
        rule = command_shaped(text)
        if rule:
            what = "rename the file" if "file name" in field else "reword it"
            raise Refused(f"command_shaped: {field} looks like a command ({rule}); {what}. Anything that "
                          "runs a command, spends money or touches a secret goes on a command card.")
    for field, text in texts:
        rule = money_shaped(text)
        if rule:
            raise Refused(f"money_needs_command_card: {field} names an amount ({rule}); a question never "
                          "approves spend. Money goes on a command card (ask_run create, Face ID).")
    hits = find_secret_shapes({f"media[{i}] file name": media_name(p) for i, p in enumerate(paths)})
    if hits:
        raise Refused("secret_shaped_value; nothing was sent: " + "; ".join(hits)
                      + ". A file name carries no secret, ever (DESIGN §6).")


# ------------------------------------------------------------ hub access
def _raw_base_url() -> str:
    return (os.environ.get(URL_ENV) or "").strip() or DEFAULT_URL


def base_url() -> str:
    url = _raw_base_url()
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise HubError(f"{URL_ENV} must be an http(s) URL (got {url!r})")
    return url.rstrip("/")


# scheme://host[:port] and at most one trailing "/": nothing the question routes could be steered by.
_BARE_HUB_RE = re.compile(r"https?://[^\s/\\?#@\x00-\x1f]+/?", re.IGNORECASE)


def question_base_url() -> str:
    """base_url() for the question verbs: the hub's address and nothing after
    host[:port] but an optional trailing "/". A base with a path, query or
    fragment moves where `ask` / `wait` / `cancel` / `list --questions` really
    go (a base ending in a question's own route plus `?x=` made `ask` POST
    to that route; security review 2026-10-13). Command cards keep base_url():
    no config here sets a path, but RUN_INBOX_URL lives outside this repo on
    three machines. The message names the part, never the value (a query can
    carry a secret)."""
    try:
        base_url()                               # the scheme error first, as for every verb
        raw = _raw_base_url()
        if _BARE_HUB_RE.fullmatch(raw):
            return base_url()
        parts = urllib.parse.urlsplit(raw)
    except ValueError:                           # urlsplit: "Invalid IPv6 URL" and the like
        raise Refused(f"{URL_ENV} is not a URL of the form http(s)://host[:port]") from None
    extras = [name for name, present in (
        ("a path", parts.path not in ("", "/")), ("a query", "?" in raw), ("a fragment", "#" in raw),
        ("credentials", "@" in parts.netloc)) if present]
    raise Refused(f"{URL_ENV} must be the hub's address only (http(s)://host[:port], at most one trailing "
                  f"'/'), but it has {' and '.join(extras) or 'more after the host'}: question cards "
                  "are sent to fixed routes under it, so a longer address would send them somewhere else")


def token_path() -> Path:
    return Path.home() / TOKEN_FILE


def _is_worker_process(env: dict | None = None) -> bool:
    """WORKER_TASK_ID or WORKER_ROLE set to any value, even empty: the rule the
    Console's relay role gate uses too (src/relay/roleGate.js callerFromEnv)."""
    env = os.environ if env is None else env
    return "WORKER_TASK_ID" in env or "WORKER_ROLE" in env


def _host_flag_on(name: str) -> bool:
    """lib.org_flags.on(name); the repo root goes on the END of sys.path, as in
    _self_host_id. A checkout whose `lib` cannot load reads the flag as on: the
    guard fails closed for a worker, never open."""
    try:
        if str(ROOT) not in sys.path:
            sys.path.append(str(ROOT))
        from lib import org_flags
        return org_flags.on(name)
    except Exception:  # noqa: BLE001 - see docstring
        return True


def load_token() -> str:
    """RUN_INBOX_TOKEN, else the token file (0600). The value goes into the
    Authorization header and nowhere else — no message here names it. A worker
    process gets no file fallback while WORKER_TOKEN_FLAG is on."""
    val = (os.environ.get(TOKEN_ENV) or "").strip()
    if val:
        return val
    if _is_worker_process() and _host_flag_on(WORKER_TOKEN_FLAG):
        raise HubError(f"a worker process (WORKER_TASK_ID / WORKER_ROLE set) needs its own token in "
                       f"{TOKEN_ENV}; the token file is the C-level's (host flag {WORKER_TOKEN_FLAG}). "
                       f"Report the step to your Project Head or C-level instead")
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
    "question_needs_c_level": "only C-level sessions ask the CEO a question; a worker reports to its C-level session",
    "command_shaped": "a question is not a command: commands go on a command card (ask_run create, Face ID)",
    "money_needs_command_card": "a question never approves spend: money goes on a command card (ask_run create, Face ID)",
    "answer_not_allowed": "a question cannot carry its own answer; only the CEO's tap on /run answers",
    "too_many_open_questions": "50 questions already wait on the CEO; cancel stale ones (list --questions, cancel Q-...)",
    "unsupported_media": "the hub reads the type from the first bytes: picture JPEG/PNG/GIF/WebP, video MP4/MOV/WebM, audio MP3/M4A/AAC/WAV/OGG",
    "too_large": "the preview caps are picture 10 MB, video 50 MB, audio 20 MB",
    "rate_limited": "at most 40 uploads per session per hour; wait and ask again",
    "invalid_media": "every media id must be an upload of this session that no card has taken yet",
    "media_not_in_groups": "a media card is raised alone, not in a --batch group",
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
    if isinstance(body, dict) and isinstance(body.get("field"), str):
        msg += f" in {body['field'][:60]}"   # where, never the value (QUESTIONS.md §3.2)
    if detail:
        msg += f" {detail}"
    hint = _HINTS.get(code) or _HINTS.get(e.code)
    if hint:
        msg += f": {hint}"
    return HubError(msg, status=e.code, code=code, transient=e.code >= 500 or e.code == 429)


def _is_question_path(path: str) -> bool:
    return any(path == base or path.startswith(base + "/") for base in (QUESTIONS_PATH, GROUPS_PATH, MEDIA_PATH))


def _request(method: str, path: str, *, body: Any = None, query: dict | None = None,
             accept: str = "application/json", timeout: float | None = HTTP_TIMEOUT_S,
             raw: Any = None, raw_length: int = 0, headers: dict | None = None):
    # every question call (ask, wait, cancel, list --questions) passes the strict address check here,
    # before the token is read and before a connection is opened
    base = question_base_url() if _is_question_path(path) else base_url()
    token = load_token()
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    out_headers = {"Authorization": "Bearer " + token, "Accept": accept, "User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        out_headers["Content-Type"] = "application/json; charset=utf-8"
    elif raw is not None:        # a media upload: the file's bytes, streamed, never held whole
        data = raw
        out_headers["Content-Type"] = "application/octet-stream"
        out_headers["Content-Length"] = str(raw_length)
    out_headers.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=out_headers, method=method)
    try:
        return _OPENER.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise _hub_error(e) from None
    except (urllib.error.URLError, OSError) as e:  # refused, DNS, TLS, timeout
        raise HubError(f"hub unreachable at {base_url()}: {getattr(e, 'reason', e)}",
                       transient=True) from None


def _call(method: str, path: str, *, body: Any = None, query: dict | None = None,
          timeout: float | None = HTTP_TIMEOUT_S, **upload: Any) -> Any:
    resp = _request(method, path, body=body, query=query, timeout=timeout, **upload)
    try:
        with resp:
            raw = resp.read()
    except OSError as e:
        raise HubError(f"hub connection dropped mid-answer: {e}", transient=True) from None
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
    if "#" in s:  # the phone URL .../run#RUN-... or .../run#Q-...
        s = s.rsplit("#", 1)[1]
    if not (_ID_RE.match(s) or _QID_RE.match(s) or _GID_RE.match(s)):
        raise Refused(f"not a Run Inbox id: {raw!r} (expected RUN-YYYYMMDD-HHMM-xxxx, "
                      "Q-YYYYMMDD-HHMM-xxxx, QG-YYYYMMDD-HHMM-xxxx, or its /run#... URL)")
    return s


def is_question_id(ask_id: str) -> bool:
    """A question card's id (Q-...), as opposed to a command card's (RUN-...)."""
    return ask_id.startswith("Q-")


def is_group_id(ask_id: str) -> bool:
    """A group of questions (QG-...), raised by `ask --batch` / ask_ceo(questions=...)."""
    return ask_id.startswith("QG-")


def card_url(ask_id: str) -> str:
    return f"{base_url()}/run#{ask_id}"


def _ask_path(ask_id: str, suffix: str = "") -> str:
    return f"{ASKS_PATH}/{urllib.parse.quote(ask_id, safe='')}{suffix}"


def _question_path(question_id: str, suffix: str = "") -> str:
    return f"{QUESTIONS_PATH}/{urllib.parse.quote(question_id, safe='')}{suffix}"


def _group_path(group_id: str) -> str:
    return f"{GROUPS_PATH}/{urllib.parse.quote(group_id, safe='')}"


def _record_path(ask_id: str) -> str:
    """GET path of a card, a question or a group, by the id's prefix."""
    if is_group_id(ask_id):
        return _group_path(ask_id)
    return _question_path(ask_id) if is_question_id(ask_id) else _ask_path(ask_id)


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
    shown, total = tail_lines(rec, lines)
    if total:
        print(f"--- output tail ({len(shown)} of {total} lines) ---")
        print("\n".join(shown))


def tail_lines(rec: dict, lines: int = TAIL_LINES) -> tuple[list[str], int]:
    """(the last `lines` lines of the record's output tail, how many it has); 0 = all."""
    tail = rec.get("output_tail")
    if not isinstance(tail, str) or not tail:
        return [], 0
    all_lines = tail.splitlines()
    return (all_lines[-lines:] if lines and lines > 0 else all_lines), len(all_lines)


# ------------------------------------------------- shared by the CLI and MCP
def prepare_ask(args: argparse.Namespace, script_args: list[str], env: dict | None = None) -> dict:
    """The POST body with the local refusals already run: secret shapes
    first, then the C-level gate, then the CEO's 5 lines (why + expected).
    `create` and the MCP tool both come here."""
    payload = build_payload(args, script_args, env)
    hits = find_secret_shapes(payload)
    if hits:
        raise Refused("secret_shaped_value; nothing was sent:\n  " + "\n  ".join(hits)
                      + "\nReference an env var by name ($NAME, --env-key NAME) or an Infisical path "
                        "instead (DESIGN §6).")
    check_role_gate(payload)
    check_ceo_text([("why", payload["why"]), ("expected", payload.get("expected"))])
    return payload


def submit(payload: dict, path: str = ASKS_PATH) -> dict:
    """POST the ask; the hub's answer plus the phone URL of the card."""
    resp = _unwrap(_call("POST", path, body=payload))
    ask_id = resp.get("id")
    if not isinstance(ask_id, str) or not ask_id:
        raise HubError(f"hub accepted the ask but returned no id: {json.dumps(resp)[:200]}")
    return {**resp, "url": card_url(ask_id)}


def submit_question(payload: dict) -> dict:
    """POST the question; the hub's answer plus the phone URL of the card."""
    resp = submit(payload, QUESTIONS_PATH)
    if not _QID_RE.match(resp["id"]):
        raise HubError(f"hub accepted the question but returned a malformed id: {resp['id'][:80]!r}")
    return resp


def _blank(value: Any) -> bool:
    return not (isinstance(value, str) and value.strip())


def _picks_problem(rec: dict, answer: dict) -> str | None:
    """A media card's answer must name items the card has, each once, and `picked` must be their
    letters; anything else is a record this tool will not print as the CEO's choice."""
    picks = answer.get("picks")
    if picks is None:
        return None
    media = rec.get("media")
    top = len(media) if isinstance(media, list) and media else MEDIA_MAX
    if not isinstance(picks, list) or len(set(map(repr, picks))) != len(picks) or any(
            isinstance(n, bool) or not isinstance(n, int) or not 0 <= n < top for n in picks):
        return "answer.picks is not a list of distinct item numbers of this card"
    picked = answer.get("picked")
    if picked is not None and picked != [media_label(n) for n in picks]:
        return "answer.picked does not match answer.picks"
    return None


def verify_question_record(rec: dict) -> None:
    """The record is the hub's, and it is what a session cites as the CEO's
    decision (QUESTIONS.md §1.3). Fail closed on the hub's own marker, not on a
    username (the operator's name is whatever the Console's operators table says):
    an `answered` record needs `answer.via == ANSWER_VIA` (the answer route sets
    it for a passkey-session answer and for nothing else), a non-empty
    `answered_by` and a non-empty `answered_at`. Anything else is not an answer
    anyone can attribute."""
    if rec.get("status") != "answered":
        return
    answer = rec.get("answer")
    if not isinstance(answer, dict):
        reason = "answer is not an object"
    elif answer.get("via") != ANSWER_VIA:
        reason = f"answer.via is not {ANSWER_VIA!r}"
    elif _blank(answer.get("answered_by")):
        reason = "answer.answered_by is empty"
    elif _blank(answer.get("answered_at")):
        reason = "answer.answered_at is empty"
    elif (reason := _picks_problem(rec, answer)):
        pass
    else:
        return
    raise HubError(f"{rec.get('id', '?')}: the hub record says answered but {reason}; "
                   "not trusting it (QUESTIONS.md §1.3, §3.3)")


def load_batch_file(path: str) -> Any:
    """`ask --batch FILE`: the JSON list of questions (`-` = stdin). A bad file
    is a refusal, before any network call."""
    try:
        raw = sys.stdin.read(BATCH_FILE_MAX + 1) if path == "-" else \
            Path(path).read_text(encoding="utf-8")[:BATCH_FILE_MAX + 1]
    except (OSError, UnicodeDecodeError) as e:
        raise Refused(f"invalid_questions: cannot read --batch {path!r}: {e.__class__.__name__}") from None
    if len(raw) > BATCH_FILE_MAX:
        raise Refused(f"invalid_questions: --batch file is over {BATCH_FILE_MAX // 1024} KB")
    try:
        return json.loads(raw)
    except ValueError as e:
        raise Refused(f"invalid_questions: --batch is not JSON (line {getattr(e, 'lineno', '?')})") from None


def _item_refusal(index: int, err: Refused) -> Refused:
    """An item's refusal, with the item named and the rule code still first."""
    text = str(err)
    m = re.match(r"([a-z_]+)[:;]\s*(.*)\Z", text, re.S)
    code, rest = (m.group(1), m.group(2)) if m else ("invalid_questions", text)
    return Refused(f"{code}: questions[{index}]: {rest}")


def prepare_question_group(items: Any, args: argparse.Namespace, env: dict | None = None) -> dict:
    """The POST /api/run/question-groups body (QUESTIONS.md §10): every item
    through prepare_question(), the same checks as a lone `ask`, then one body
    that carries the requester and expiry once. An item may not set its own
    requester, host or expiry: the group has one asker and one deadline."""
    if isinstance(items, dict) and set(items) == {"questions"}:
        items = items["questions"]
    if not isinstance(items, list) or not 1 <= len(items) <= GROUP_MAX:
        raise Refused(f"invalid_questions: a group is a list of 1 to {GROUP_MAX} questions"
                      + (f" (got {len(items)})" if isinstance(items, list) else ""))
    bodies = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise Refused(f"invalid_questions: questions[{i}] is not an object")
        extra = sorted(set(item) - set(GROUP_ITEM_KEYS))
        if extra:
            raise Refused(f"invalid_questions: questions[{i}] has {', '.join(extra)}; an item carries only "
                          f"{', '.join(GROUP_ITEM_KEYS)} (requester, host and expiry are the group's)")
        shared = {"session": args.session, "role": args.role, "host": args.host,
                  "task": getattr(args, "task", None), "expires_h": args.expires_h}
        try:
            body = prepare_question(_mcp_question_namespace({**item, **shared}), env)
        except Refused as e:
            raise _item_refusal(i, e) from None
        bodies.append(body)
    payload = {
        "questions": [{k: b[k] for k in ("question", "why", "options", "free_text")} for b in bodies],
        "expires_in_s": bodies[0]["expires_in_s"],
        "requester": bodies[0]["requester"],
    }
    hits = find_secret_shapes(payload)
    if hits:  # each item was checked; this is the body as sent
        raise Refused("secret_shaped_value; nothing was sent: " + "; ".join(hits))
    return payload


def submit_question_group(payload: dict) -> dict:
    """POST the group; the hub's answer with the phone URL of the group and of each question."""
    resp = _unwrap(_call("POST", GROUPS_PATH, body=payload))
    group_id = resp.get("group_id")
    if not isinstance(group_id, str) or not _GID_RE.match(group_id):
        raise HubError(f"hub accepted the group but returned no group id: {json.dumps(resp)[:200]}")
    questions = resp.get("questions")
    if not isinstance(questions, list) or len(questions) != len(payload["questions"]) or not all(
            isinstance(q, dict) and isinstance(q.get("id"), str) and _QID_RE.match(q["id"]) for q in questions):
        raise HubError(f"hub accepted group {group_id} but its question ids are malformed")
    return {**resp, "url": card_url(group_id),
            "questions": [{**q, "url": card_url(q["id"])} for q in questions]}


def verify_group_record(rec: dict) -> None:
    """A group's record is its questions' records; each one is checked like a
    lone answer (verify_question_record), and a group the hub calls done must
    have no question still pending."""
    questions = rec.get("questions")
    if not isinstance(questions, list) or not questions or not all(isinstance(q, dict) for q in questions):
        raise HubError(f"{rec.get('id', '?')}: the hub's group record has no questions; not trusting it")
    for q in questions:
        if not _QID_RE.match(str(q.get("id", ""))) or (rec.get("id") and q.get("group_id") != rec.get("id")):
            raise HubError(f"{rec.get('id', '?')}: a question in the group record is not one of its own")
        verify_question_record(q)
    if rec.get("status") in GROUP_TERMINAL_STATES and any(
            q.get("status") not in QUESTION_TERMINAL_STATES for q in questions):
        raise HubError(f"{rec.get('id', '?')}: the hub says the group is done but a question is still "
                       "pending; not trusting it")


def poll_until_end(ask_id: str, *, interval: float = POLL_INTERVAL_S, max_wait: float = 0,
                   on_status: Callable[[str, dict], None] | None = None,
                   on_retry: Callable[[HubError, int], None] | None = None,
                   ) -> tuple[dict | None, bool]:
    """GET the ask every `interval` s (never faster than MIN_INTERVAL_S) until
    it reaches a terminal state -> (record, True), or until `max_wait` s have
    passed (0 = no limit) -> (last record or None, False). Rides out
    MAX_POLL_FAILURES transient errors in a row; anything else raises at once."""
    interval = max(interval, MIN_INTERVAL_S)
    deadline = time.monotonic() + max_wait if max_wait and max_wait > 0 else None
    terminal = (GROUP_TERMINAL_STATES if is_group_id(ask_id)
                else QUESTION_TERMINAL_STATES if is_question_id(ask_id) else TERMINAL_STATES)
    last_rec: dict | None = None
    last_status = None
    failures = 0
    while True:
        rec = None
        try:
            rec = _unwrap(_call("GET", _record_path(ask_id)))
            failures = 0
        except HubError as e:
            failures += 1
            if not e.transient or failures > MAX_POLL_FAILURES:
                raise
            if on_retry:
                on_retry(e, failures)
        if rec is not None:
            rec.setdefault("id", ask_id)
            last_rec = rec
            status = str(rec.get("status") or "?")
            if status != last_status:
                last_status = status
                if on_status:
                    on_status(status, rec)
            if status in terminal:
                return rec, True
        pause = interval
        if deadline is not None:
            left = deadline - time.monotonic()
            if left <= 0:
                return last_rec, False
            pause = min(interval, left)
        time.sleep(pause)


# ------------------------------------------------------------ the MCP tools
# lib/org_tools_registry.py `ask_run` / `ask_ceo` / `ask_run_wait` call these
# (in a worker thread, so the org server's event loop never blocks). Nothing
# here prints: that server's stdout is its JSON-RPC channel.
WAIT_DEFAULT_S = 600.0
WAIT_MAX_S = 3600.0


def _mcp_namespace(a: dict) -> tuple[argparse.Namespace, list[str]]:
    """MCP arguments -> the Namespace `create` parses, so both run one path.
    An empty string means "not given" (FastMCP stubs default to "")."""
    script, command = (a.get("script") or "").strip(), a.get("command") or ""
    if bool(script) == bool(command):
        raise Refused("give exactly one of script (repo@sha:path) or command")
    risk = a.get("risk") or DEFAULT_RISK
    if risk not in RISKS:
        raise Refused(f"risk must be one of {'/'.join(RISKS)} (got {risk!r})")
    shell = a.get("shell") or None
    if shell is not None and shell not in SHELLS:
        raise Refused(f"shell must be one of {'/'.join(SHELLS)} (got {shell!r})")
    timeout = a.get("timeout_s", DEFAULT_TIMEOUT_S)
    if isinstance(timeout, float) and timeout.is_integer():
        timeout = int(timeout)
    if isinstance(timeout, bool) or not isinstance(timeout, int):
        raise Refused("timeout_s must be a whole number of seconds")
    script_args = a.get("args") or []
    if not isinstance(script_args, list) or not all(isinstance(x, str) for x in script_args):
        raise Refused("args must be a list of strings")
    env_keys = a.get("env_keys") or None
    if env_keys is not None and (not isinstance(env_keys, list)
                                 or not all(isinstance(k, str) for k in env_keys)):
        raise Refused("env_keys must be a list of variable names")
    ns = argparse.Namespace(
        host=a.get("host") or "", script=script or None, command=None if script else command,
        why=a.get("why") or "", expected=a.get("expected") or None, risk=risk, timeout=timeout,
        expects_input=bool(a.get("expects_input")), shell=shell, cwd=a.get("cwd") or None,
        env_key=env_keys, task=a.get("task") or None, session=a.get("session") or None,
        role=a.get("role") or None, dry_run=bool(a.get("dry_run")), json=False,
        spend=None, no_spend=(a.get("no_spend") or None))
    spend = a.get("spend") or None
    if spend is not None and not isinstance(spend, dict):
        raise Refused(f"invalid_spend: spend is an object with {', '.join(_SPEND_KEYS)}")
    ns.spend = spend
    return ns, list(script_args)


def mcp_ask(arguments: dict, env: dict | None = None) -> dict:
    """MCP `ask_run`: the same checks and the same POST as `create`. Returns
    {id, url, risk, expires_at}, or {dry_run, would_post, payload}."""
    try:
        ns, script_args = _mcp_namespace(arguments)
        payload = prepare_ask(ns, script_args, env)
    except Refused as e:
        raise Refused(f"refused: {e}") from None
    if ns.dry_run:
        return {"dry_run": True, "would_post": f"{base_url()}/api/run/asks", "payload": payload}
    resp = submit(payload)
    return {"id": resp["id"], "url": resp["url"], "risk": resp.get("risk"),
            "expires_at": resp.get("expires_at")}


def _mcp_question_namespace(a: dict) -> argparse.Namespace:
    """MCP `ask_ceo` arguments -> the Namespace `ask` parses, so both run one
    path. `recommended` is 1-based, 0 = none; an empty string means "not given"."""
    media = a.get("media") or []
    if not isinstance(media, list) or not all(isinstance(m, dict) for m in media):
        raise Refused("invalid_media: media is a list of {path, caption} objects")
    paths, captions = [], []
    for i, m in enumerate(media):
        extra = sorted(set(m) - {"path", "caption"})
        if extra or not isinstance(m.get("path"), str) or not m["path"].strip() \
                or not isinstance(m.get("caption") or "", str):
            raise Refused(f"invalid_media: media[{i}] is {{path, caption}}: a path string and an optional "
                          f"caption string{', no other key (got ' + ', '.join(map(str, extra)) + ')' if extra else ''}")
        paths.append(m["path"])
        captions.append(m.get("caption") or "")
    options = a.get("options")
    if media and options in (None, ""):
        options = []
    if not isinstance(options, list) or not all(isinstance(x, str) for x in options):
        raise Refused(f"invalid_options: options is a list of {OPTIONS_MIN} to {OPTIONS_MAX} strings")
    pick = a.get("pick") or None
    if pick is not None and not isinstance(pick, str):
        raise Refused("invalid_pick: pick is one or many")
    recommended = a.get("recommended") or 0
    if isinstance(recommended, float) and recommended.is_integer():
        recommended = int(recommended)
    if isinstance(recommended, bool) or not isinstance(recommended, int) or recommended < 0:
        raise Refused("invalid_options: recommended is an option number, 1-based (0 = none)")
    free_text = a.get("free_text", True)
    if not isinstance(free_text, bool):
        raise Refused("invalid_free_text: free_text is true or false")
    return argparse.Namespace(
        question=a.get("question") or "", option=list(options), recommended=recommended or None,
        why=a.get("why") or "", no_free_text=not free_text,
        expires_h=a.get("expires_h", EXPIRES_DEFAULT_H), session=a.get("session") or None,
        role=a.get("role") or None, host=a.get("host") or None, task=a.get("task") or None,
        dry_run=bool(a.get("dry_run")), json=False,
        media=paths or None, caption=captions if any(captions) else None, pick=pick)


def _mcp_ask_ceo_group(arguments: dict, env: dict | None) -> dict:
    """MCP `ask_ceo` with `questions`: the same checks and the same POST as
    `ask --batch`. The one-card fields must be empty: a call is one card or one group."""
    try:
        lone = [k for k in ("question", "why") if (arguments.get(k) or "").strip()]
        if arguments.get("options"):
            lone.append("options")
        if arguments.get("recommended"):
            lone.append("recommended")
        if arguments.get("free_text", True) is not True:
            lone.append("free_text")
        if arguments.get("media"):
            raise Refused("media_not_in_groups: a media card is raised alone, not inside questions (a group)")
        if lone:
            raise Refused(f"invalid_questions: give questions (a group) or {', '.join(lone)} (one card), "
                          "not both; each item of questions carries its own question, why, options, "
                          "recommended and free_text")
        ns = argparse.Namespace(session=arguments.get("session") or None, role=arguments.get("role") or None,
                                host=arguments.get("host") or None, task=arguments.get("task") or None,
                                expires_h=arguments.get("expires_h", EXPIRES_DEFAULT_H))
        payload = prepare_question_group(arguments.get("questions"), ns, env)
        base = question_base_url()
    except Refused as e:
        raise Refused(f"refused: {e}") from None
    if arguments.get("dry_run"):
        return {"dry_run": True, "would_post": base + GROUPS_PATH, "payload": payload}
    resp = submit_question_group(payload)
    return {"group_id": resp["group_id"], "url": resp["url"], "expires_at": resp.get("expires_at"),
            "questions": [{"id": q["id"], "url": q["url"]} for q in resp["questions"]]}


def mcp_ask_ceo(arguments: dict, env: dict | None = None) -> dict:
    """MCP `ask_ceo`: the same checks and the same POST as `ask`. Returns
    {id, url, expires_at}, or {dry_run, would_post, payload}. It creates the
    question and nothing else: no path here answers one (QUESTIONS.md §1.1).
    With `questions` (1-6 items) it raises one group instead, like `ask --batch`,
    and returns {group_id, url, expires_at, questions: [{id, url}]}."""
    if arguments.get("questions") not in (None, "", []):
        return _mcp_ask_ceo_group(arguments, env)
    try:
        if arguments.get("options") in (None, "") and not (arguments.get("question") or "").strip():
            raise Refused("question_required: give question, options and why (one card), or questions "
                          f"(a group of up to {GROUP_MAX})")
        ns = _mcp_question_namespace(arguments)
        payload = prepare_question(ns, env)
        base = question_base_url()
        if payload.get("media"):
            body, resp, lines = send_media_question(payload, list(ns.media), dry_run=ns.dry_run)
            if resp is None:
                return {"dry_run": True, "would_post": base + QUESTIONS_PATH, "payload": body, "media": lines}
            return {"id": resp["id"], "url": resp["url"], "expires_at": resp.get("expires_at"), "media": lines}
    except Refused as e:
        raise Refused(f"refused: {e}") from None
    if ns.dry_run:
        return {"dry_run": True, "would_post": base + QUESTIONS_PATH, "payload": payload}
    resp = submit_question(payload)
    return {"id": resp["id"], "url": resp["url"], "expires_at": resp.get("expires_at")}


def wait_result(ask_id: str, *, max_wait_s: float = WAIT_DEFAULT_S,
                interval_s: float = POLL_INTERVAL_S, tail_lines_n: int = TAIL_LINES) -> dict:
    """MCP `ask_run_wait`: `wait`, bounded so one tool call never outlives the
    client (max_wait_s, default 600, at most 3600). terminal=False = call again.
    The output tail is cut to its last `tail_lines_n` lines (0 = all). A Q-...
    id waits on a question card: the hub's record, {terminal, status, answer, ...}.
    A QG-... id waits on a group: terminal once no question in it is pending,
    with every question's record under `questions`."""
    try:
        ask_id = normalize_id(ask_id)
    except Refused as e:
        raise Refused(f"refused: {e}") from None
    max_wait = min(max(float(max_wait_s or WAIT_DEFAULT_S), 1.0), WAIT_MAX_S)
    rec, ended = poll_until_end(ask_id, interval=float(interval_s or POLL_INTERVAL_S),
                                max_wait=max_wait)
    rec = dict(rec or {"id": ask_id})
    if is_question_id(ask_id):
        verify_question_record(rec)
    elif is_group_id(ask_id) and rec.get("questions") is not None:
        verify_group_record(rec)
    out: dict[str, Any] = {"terminal": ended}
    if not ended:
        out["note"] = f"still {rec.get('status', 'unknown')} after {max_wait:g} s; call ask_run_wait again"
    shown, total = tail_lines(rec, tail_lines_n)
    if total and len(shown) < total:
        rec["output_tail"] = "\n".join(shown)
        rec["output_tail_shown"] = f"last {len(shown)} of {total} lines"
    out.update(rec)
    return out


# ------------------------------------------------------------------ verbs
def cmd_create(args: argparse.Namespace, script_args: list[str]) -> int:
    payload = prepare_ask(args, script_args)
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        sys.stdout.flush()
        _say(f"dry run: nothing sent (would POST {base_url()}/api/run/asks)")
        return EXIT_OK
    resp = submit(payload)
    ask_id = resp["id"]
    if args.json:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
    else:
        print(ask_id)
        print(resp["url"])
    _say(f"{resp.get('status', 'pending')} · risk {resp.get('risk', '?')} · expires "
         f"{resp.get('expires_at', '?')}. Only the CEO's tap runs it. "
         f"Next: python3 tools/ask_run.py wait {ask_id}")
    return EXIT_OK


def cmd_ask_batch(args: argparse.Namespace) -> int:
    payload = prepare_question_group(load_batch_file(args.batch), args)
    base = question_base_url()
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        sys.stdout.flush()
        _say(f"dry run: nothing sent (would POST {base}{GROUPS_PATH})")
        return EXIT_OK
    resp = submit_question_group(payload)
    group_id = resp["group_id"]
    if args.json:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
    else:
        print(group_id)
        print(resp["url"])
        for q in resp["questions"]:
            print(q["id"])
    _say(f"{resp.get('status', 'pending')} · {len(resp['questions'])} questions · expires "
         f"{resp.get('expires_at', '?')}. Only the CEO's tap on /run answers them; what he sends you "
         f"at once comes as one letter. Next: python3 tools/ask_run.py wait {group_id}")
    return EXIT_OK


def cmd_ask(args: argparse.Namespace) -> int:
    if args.batch:
        return cmd_ask_batch(args)
    payload = prepare_question(args)
    base = question_base_url()
    if payload.get("media"):
        body, resp, lines = send_media_question(payload, list(args.media), dry_run=args.dry_run)
        for line in lines:
            _say(line)
        if resp is None:
            print(json.dumps(body, indent=2, ensure_ascii=False))
            sys.stdout.flush()
            _say(f"dry run: nothing sent (would upload {len(lines)} item(s) to {base}{MEDIA_PATH}, "
                 f"then POST {base}{QUESTIONS_PATH})")
            return EXIT_OK
    elif args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        sys.stdout.flush()
        _say(f"dry run: nothing sent (would POST {base}{QUESTIONS_PATH})")
        return EXIT_OK
    else:
        resp = submit_question(payload)
    question_id = resp["id"]
    if args.json:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
    else:
        print(question_id)
        print(resp["url"])
    _say(f"{resp.get('status', 'pending')} · expires {resp.get('expires_at', '?')}. Only the CEO's tap "
         f"on /run answers it. Next: python3 tools/ask_run.py wait {question_id}")
    return EXIT_OK


def _plain(value: Any) -> str:
    """A hub string printed on one line with its control and format characters dropped."""
    return "".join(c for c in str(value) if unicodedata.category(c) not in _HIDDEN_CATEGORIES).strip()


def picked_line(rec: dict, answer: dict) -> str | None:
    """The line a session reads for a media card (QUESTIONS.md §11), else None for any other
    card: `picked: B (cover_b.png) · note: ...`, `picked: A (a.jpg), C (c.jpg)`, `picked: none · note: ...`
    (a redo, or a set where nothing was ticked), `picked: ใช้ได้ · note: ...` (one item). The
    note part only when there is a note."""
    picks = answer.get("picks")
    redo = answer.get("redo") is True or rec.get("redo") is True
    if not (rec.get("media") or isinstance(picks, list) or redo):
        return None
    if redo or (isinstance(picks, list) and not picks):
        who = "none"
    elif isinstance(picks, list):
        labels, names = answer.get("picked"), answer.get("picked_names")
        parts = []
        for i, n in enumerate(picks):
            label = _plain(labels[i]) if isinstance(labels, list) and i < len(labels) else media_label(n)
            name = _plain(names[i]) if isinstance(names, list) and i < len(names) and names[i] else ""
            parts.append(f"{label} ({name})" if name else label)
        who = ", ".join(parts)
    else:
        choice = answer.get("choice")
        who = _plain(answer["label"]) if answer.get("label") else \
            f"option {choice + 1}" if isinstance(choice, int) and not isinstance(choice, bool) else "?"
    note = _plain(answer["text"]) if answer.get("text") else ""
    return f"picked: {who}" + (f" · note: {note}" if note else "")


def media_label(n: Any) -> str:
    """Item n (0-based) as the card letters it: A, B, C ... L."""
    return chr(65 + n) if isinstance(n, int) and not isinstance(n, bool) and 0 <= n < MEDIA_MAX else "?"


def print_question_result(rec: dict, *, as_json: bool = False) -> None:
    """The §3.3 record: whole as JSON, else the lines a session cites as the
    CEO's decision (id, status, who answered and when, the option, the note,
    the sha256 the page verified)."""
    if as_json:
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return
    answer = rec.get("answer") if isinstance(rec.get("answer"), dict) else None
    parts = [str(rec.get("id", "?")), str(rec.get("status", "?"))]
    if answer:
        parts += [f"by {answer.get('answered_by', '?')}", f"at {answer.get('answered_at', '?')}"]
    print("  ".join(parts))
    if rec.get("question"):
        print(f"question: {rec['question']}")
    if answer and picked_line(rec, answer):
        print(picked_line(rec, answer))
        if rec.get("sha256"):
            print(f"sha256: {rec['sha256']}")
    elif answer:
        choice = answer.get("choice")
        if isinstance(choice, int) and not isinstance(choice, bool):
            print(f"answer: option {choice + 1} \"{answer.get('label')}\"")
        if answer.get("text"):
            print(f"note: {answer['text']}")
        if rec.get("sha256"):
            print(f"sha256: {rec['sha256']}")
    elif rec.get("status") == "expired":
        print(f"nobody answered before {rec.get('expires_at', '?')}")


def print_group_result(rec: dict, *, as_json: bool = False) -> None:
    """A group: whole as JSON, else one header line and each question's lines."""
    if as_json:
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return
    questions = rec.get("questions") or []
    answered = sum(1 for q in questions if q.get("status") == "answered")
    print(f"{rec.get('id', '?')}  {rec.get('status', '?')}  {answered} of {len(questions)} answered")
    for q in questions:
        print()
        print_question_result(q)


def cmd_wait(args: argparse.Namespace) -> int:
    ask_id = normalize_id(args.id)
    rec, ended = poll_until_end(
        ask_id, interval=args.interval, max_wait=args.max_wait,
        on_status=lambda status, _rec: _say(f"{datetime.now().strftime('%H:%M:%S')} {ask_id} {status}"),
        on_retry=lambda e, n: _say(f"{ask_id}: {e} (retry {n}/{MAX_POLL_FAILURES})"))
    if not ended or rec is None:
        last = (rec or {}).get("status") or "unknown"
        _say(f"{ask_id} still {last} after {args.max_wait:g} s; run wait again later")
        return EXIT_STILL_WAITING
    if is_question_id(ask_id):
        verify_question_record(rec)
        print_question_result(rec, as_json=args.json)
        return EXIT_OK if rec.get("status") == "answered" else EXIT_ENDED_BADLY
    if is_group_id(ask_id):
        verify_group_record(rec)
        print_group_result(rec, as_json=args.json)
        return EXIT_OK if all(q.get("status") == "answered" for q in rec["questions"]) else EXIT_ENDED_BADLY
    print_result(rec, lines=args.lines, as_json=args.json)
    return EXIT_OK if rec.get("status") == "done" else EXIT_ENDED_BADLY


def cmd_list_questions(args: argparse.Namespace) -> int:
    query = {}
    if args.status:
        query["status"] = args.status
    if args.limit:
        query["limit"] = str(args.limit)
    resp = _call("GET", QUESTIONS_PATH, query=query)
    questions = resp.get("questions") if isinstance(resp, dict) else resp
    questions = [q for q in (questions or []) if isinstance(q, dict)]
    if args.json:
        print(json.dumps(questions, indent=2, ensure_ascii=False))
        return EXIT_OK
    if not questions:
        print("(no questions)")
        return EXIT_OK
    for q in questions:
        who = q.get("requester") if isinstance(q.get("requester"), dict) else {}
        text = str(q.get("question", "?"))
        row = (f"{q.get('id', '?')}  {str(q.get('status', '?')):<9} "
               f"{who.get('session', '?')}@{who.get('host', '?')}  "
               f"{text if len(text) <= 70 else text[:67] + '...'}")
        if q.get("status") == "pending" and q.get("expires_at"):
            row += f"  (expires {q['expires_at']})"
        print(row)
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    if args.questions:
        return cmd_list_questions(args)
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
    if is_group_id(ask_id):
        raise Refused("a group has no cancel of its own: cancel each question by its Q- id "
                      f"(python3 tools/ask_run.py wait {ask_id} --max-wait 1 lists them)")
    path = _question_path(ask_id, "/cancel") if is_question_id(ask_id) else _ask_path(ask_id, "/cancel")
    resp = _unwrap(_call("POST", path, body={}))
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
    if is_question_id(ask_id) or is_group_id(ask_id):
        raise Refused("a question card runs nothing and has no output to tail: "
                      f"use `wait {ask_id}` for the CEO's answer")
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
    sp = c.add_argument_group("spend label (a card that spends credit; Console docs/run.md §Spend label)")
    sp.add_argument("--spend-provider", metavar="NAME", help="fal | openrouter | higgsfield | ... (lowercase)")
    sp.add_argument("--spend-billing", choices=SPEND_BILLING, help="api credit or account credit (default api)")
    sp.add_argument("--spend-unit", choices=SPEND_UNITS, help="usd or credits (default usd)")
    sp.add_argument("--spend-estimate", type=float, metavar="N", help="what it should cost")
    sp.add_argument("--spend-cap", type=float, metavar="N",
                    help="never more than; the command must carry --max-usd N / --max-credits N")
    sp.add_argument("--spend-balance-after", type=float, metavar="N",
                    help="balance left after (default for openrouter/fal usd: the spend guard's balance - cap)")
    sp.add_argument("--spend-how", metavar="TEXT", help="one line: how the estimate and cap were computed")
    sp.add_argument("--spend-budget", metavar="TEXT", help="one line: the budget this comes out of")
    sp.add_argument("--no-spend", metavar="REASON",
                    help="the command looks like spend but is not (e.g. a balance read); shown on the card")
    c.add_argument("--dry-run", action="store_true", help="print the JSON body, send nothing")
    c.add_argument("--json", action="store_true", help="print the hub's answer as JSON")

    q = sub.add_parser("ask", help="ask the CEO a 2-4 option question (one tap on /run); prints its id "
                                   "and the phone URL. Never for a command, money or a secret: those go "
                                   "on a command card (create)")
    q.add_argument("--question", help=f"one line, at most {QUESTION_MAX} characters")
    q.add_argument("--option", action="append", metavar="LABEL",
                   help=f"an answer the CEO can tap; repeat {OPTIONS_MIN} to {OPTIONS_MAX} times")
    q.add_argument("--recommended", type=int, metavar="N",
                   help="1-based: the option that carries the recommended badge")
    q.add_argument("--why", help=f"context the CEO reads before tapping (at most {WHY_MAX} characters)")
    q.add_argument("--batch", metavar="FILE",
                   help=f"1 to {GROUP_MAX} questions as one group (a JSON list, - = stdin; each item "
                        "{question, why, options, recommended, free_text}); replaces "
                        "--question/--option/--why/--recommended/--no-free-text. One send from the "
                        "CEO = one letter to you")
    q.add_argument("--media", action="append", metavar="PATH",
                   help=f"a picture, video or sound for the CEO to look at and pick from; repeat 1 to {MEDIA_MAX} "
                        "times. The type is read from the first bytes. It is shrunk before upload (picture "
                        "2048 px, video 720p MP4 + poster, audio M4A); you keep the master. Needs ffmpeg. "
                        "Replaces --option for 2 or more items (QUESTIONS.md §11)")
    q.add_argument("--caption", action="append", metavar="TEXT",
                   help=f"under the item of the same order (at most {CAPTION_MAX} characters, one line); repeatable")
    q.add_argument("--pick", metavar="one|many",
                   help="2 or more items: one = he taps one, many = he ticks any, even none (required). "
                        "One item: leave it out (he answers ใช้ได้ / แก้ / ไม่เอา)")
    q.add_argument("--no-free-text", action="store_true",
                   help="an option is required and the CEO gets no text box (default: he may add a note)")
    q.add_argument("--expires-h", type=float, default=EXPIRES_DEFAULT_H, metavar="HOURS",
                   help="how long the question waits (default 24, from 10 minutes to 7 days)")
    q.add_argument("--host", help="the machine this session runs on: contabo | mac | winbox "
                                  "(default: ORG_HOST, else this checkout's self_host, else the hostname)")
    q.add_argument("--session", help="your mailbox name <role>-<id>, e.g. cto-6ebacd0e (default: from env)")
    q.add_argument("--role", help="your role (default: CXO_ROLE / WORKER_ROLE)")
    q.add_argument("--dry-run", action="store_true", help="print the JSON body, send nothing")
    q.add_argument("--json", action="store_true", help="print the hub's answer as JSON")

    w = sub.add_parser("wait", help="poll an ask (RUN-...), a question (Q-...) or a group (QG-...) until it "
                                    "ends; exit 0 done / answered (a group: every question answered), "
                                    "1 failed/denied/expired/cancelled")
    w.add_argument("id")
    w.add_argument("--interval", type=float, default=POLL_INTERVAL_S, metavar="SECONDS")
    w.add_argument("--max-wait", type=float, default=0, metavar="SECONDS",
                   help="give up after this long, exit 4 (default: until the ask ends)")
    w.add_argument("--lines", type=int, default=TAIL_LINES, help="output tail lines to print (0 = all)")
    w.add_argument("--json", action="store_true", help="print the final record as JSON")

    ls = sub.add_parser("list", help="your own asks (or, with --questions, your own questions)")
    ls.add_argument("--questions", action="store_true", help="list question cards instead of command cards")
    ls.add_argument("--status", help="pending | running | done | all (the hub's filter); "
                                     "with --questions: pending | answered | done | all")
    ls.add_argument("--limit", type=int, default=50)
    ls.add_argument("--json", action="store_true")

    x = sub.add_parser("cancel", help="cancel your own pending ask or question (RUN-... / Q-...)")
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
    if args.verb == "ask":
        lone = [flag for flag, given in (("--question", args.question is not None),
                                         ("--option", args.option is not None),
                                         ("--why", args.why is not None),
                                         ("--recommended", args.recommended is not None),
                                         ("--media", args.media is not None),
                                         ("--caption", args.caption is not None),
                                         ("--pick", args.pick is not None),
                                         ("--no-free-text", args.no_free_text)) if given]
        if args.batch is not None and lone:
            parser.error(f"--batch carries every question; drop {', '.join(lone)}")
        needed = ("--question", "--why") if args.media else ("--question", "--option", "--why")
        missing = [f for f in needed if f not in lone]
        if args.batch is None and missing:
            parser.error(f"the following arguments are required: {', '.join(missing)} (or --batch FILE)")
    try:
        if args.verb == "create":
            return cmd_create(args, script_args)
        if args.verb == "ask":
            return cmd_ask(args)
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
