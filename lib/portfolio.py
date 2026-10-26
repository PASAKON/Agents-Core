"""Org restructure P3-B: the portfolio data layer (docs/plans/org-restructure-p3-plan.md).

Every write to the registry tables (projects, milestones, ceo_gos, resource_locks) goes
through this module, and every write that belongs to a project also appends one
`project_events` row signed with `actor` (the caller's identity, e.g.
`project_head-7cf528f0`). Who may write is decided one layer up (tools/portfolio.py);
this layer only checks that the input is well formed and that the transition is legal.

Postgres only, like the tables: with ORG_DB_URL unset every call raises PortfolioError
(run through `bash scripts/hub/org-python.sh`).

Three writes do not append an event, because `project_events.kind` has no value for them
and a new kind is a schema change (P3-A): `lock_take` / `lock_release` (the lock row is
its own record: holder, since, until), a `go_add` / `go_use` for a GO that names no
project (`project_id` is NOT NULL on events), and `edit_project` (it returns the old and
the new value of every field it changed, so the caller's output is the only trace).

`monitor_rows` / `monitor_payload` are the P3-E v1 contract. The fixture
docs/plans/fixtures/portfolio-monitor-v1.json and tests/test_portfolio.py pin the shape.
"""
from __future__ import annotations

import contextlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from lib import db

STAGES = ("idea", "brainstorm", "ready", "active", "review", "closed", "parked", "cancelled")
TIERS = ("critical", "normal", "low")
TERMINAL = ("closed", "cancelled")
BLOCKERS = ("ceo", "clevel", "external", "resource")
MONITOR_STAGES = ("active", "review", "parked")

BKK = timezone(timedelta(hours=7))          # Asia/Bangkok, no DST
WORKING_S = 5 * 60                           # a heartbeat this fresh is "working"
IDLE_S = 24 * 3600                           # a heartbeat this fresh is "idle", else "stalled"
MAX_ROWS = 20
GENERATING_MAX_AGE_S = IDLE_S                # a task row untouched this long is not "generating"

ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
LANE_RE = re.compile(r"[a-z]{2,12}")
RESOURCE_RE = re.compile(r"[a-z0-9][a-z0-9_.:-]{0,100}")
GO_SOURCE_RE = re.compile(r"(run:Q-|run:RUN-|chat:)\S.*")
MAX_TITLE = 400
MAX_TEXT = 2000


class PortfolioError(ValueError):
    """Bad input, an unknown project, or a transition the registry does not allow."""


class LockHeld(PortfolioError):
    """lock_take: another live holder has the resource."""


def _utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise PortfolioError("now must be timezone-aware")
    return now.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_utc(value) -> datetime | None:
    """A DB timestamp (timestamptz -> aware datetime; task rows keep ISO text) as aware UTC."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _text(value, what: str, *, limit: int = MAX_TEXT) -> str:
    s = (value or "").strip() if isinstance(value, str) else ""
    if not s:
        raise PortfolioError(f"{what} is required")
    if len(s) > limit:
        raise PortfolioError(f"{what} is longer than {limit} characters")
    return s


def _actor(actor: str) -> str:
    return _text(actor, "actor", limit=120)


@contextlib.contextmanager
def _tx(conn=None):
    """The caller's connection (it commits), else one hub connection that commits on exit."""
    if conn is not None:
        yield conn
        return
    if not db.pg_url():
        raise PortfolioError("the portfolio lives in the hub: ORG_DB_URL is unset "
                             "(run through scripts/hub/org-python.sh)")
    with db.get_conn() as c:
        yield c


def _project(conn, project_id: str, *, lock: bool = False):
    """The project row, or PortfolioError. `lock` takes the row lock first, so two
    writers to one project (a milestone number, a blocker) take turns."""
    if not ID_RE.fullmatch(project_id or ""):
        raise PortfolioError(f"bad project id {project_id!r} (lowercase letters, digits, '-')")
    row = conn.execute("SELECT * FROM projects WHERE id = ?" + (" FOR UPDATE" if lock else ""),
                       (project_id,)).fetchone()
    if row is None:
        raise PortfolioError(f"no such project: {project_id}")
    return row


def _event(conn, project_id: str, kind: str, actor: str, body: dict, now: datetime) -> None:
    conn.execute("INSERT INTO project_events (project_id, at, kind, actor, body)"
                 " VALUES (?, ?, ?, ?, ?::jsonb)",
                 (project_id, now, kind, actor, json.dumps(body, ensure_ascii=False)))


def _bare_session(session: str | None) -> str | None:
    s = (session or "").strip()
    return s[len("project_head-"):] if s.startswith("project_head-") else (s or None)


def pct(done: int, total: int) -> int:
    """round(100 * done / total), halves up (the Console side rounds in SQL/JS, not
    Python's banker's rounding); 0 when there is nothing to do."""
    return (200 * done + total) // (2 * total) if total else 0


# ---------------------------------------------------------------------------
# writes
# ---------------------------------------------------------------------------

def open_project(project_id: str, name: str, lane: str, *, actor: str, stage: str = "idea",
                 owner_session: str | None = None, ph_session: str | None = None,
                 host: str | None = None, repos: list[str] | None = None,
                 goal: str | None = None, done_criteria: str | None = None,
                 budget_usd: float | None = None, relay_accounts: list[str] | None = None,
                 hq_row: str | None = None, now: datetime | None = None, conn=None) -> dict:
    """Register a project. The brief's `open(id, name, lane, ...)`."""
    now, actor = _utc(now), _actor(actor)
    if not ID_RE.fullmatch(project_id or ""):
        raise PortfolioError(f"bad project id {project_id!r} (lowercase letters, digits, '-')")
    name = _text(name, "name", limit=120)
    if not LANE_RE.fullmatch(lane or ""):
        raise PortfolioError(f"bad lane {lane!r}")
    if stage not in STAGES or stage in TERMINAL:
        raise PortfolioError(f"a project opens at one of {[s for s in STAGES if s not in TERMINAL]}")
    if budget_usd is not None and budget_usd < 0:
        raise PortfolioError("budget_usd must be >= 0")
    for what, lst in (("repos", repos), ("relay_accounts", relay_accounts)):
        if lst is not None and not all(isinstance(x, str) and x.strip() for x in lst):
            raise PortfolioError(f"{what} must be a list of non-empty strings")
    with _tx(conn) as c:
        got = c.execute(
            "INSERT INTO projects (id, name, lane, owner_session, ph_session, host, repos, stage,"
            " goal, done_criteria, budget_usd, relay_accounts, hq_row, opened_at, ready_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?::jsonb, ?, ?, ?)"
            " ON CONFLICT (id) DO NOTHING RETURNING id",
            (project_id, name, lane, owner_session, _bare_session(ph_session), host,
             json.dumps(list(repos or [])), stage, goal, done_criteria, budget_usd,
             json.dumps(list(relay_accounts or [])), hq_row, now,
             now if stage == "ready" else None)).fetchone()
        if got is None:
            raise PortfolioError(f"project {project_id} already exists")
        _event(c, project_id, "opened", actor, {"name": name, "lane": lane, "stage": stage}, now)
        return dict(_project(c, project_id))


def set_stage(project_id: str, stage: str, *, actor: str, reason: str | None = None,
              now: datetime | None = None, conn=None) -> dict:
    """Move a project to another stage. `closed` goes through close(), which needs an outcome."""
    now, actor = _utc(now), _actor(actor)
    if stage not in STAGES:
        raise PortfolioError(f"unknown stage {stage!r}; one of {list(STAGES)}")
    if stage == "closed":
        raise PortfolioError("use close(): a closed project needs an outcome and a learning")
    with _tx(conn) as c:
        row = _project(c, project_id, lock=True)
        if row["stage"] in TERMINAL:
            raise PortfolioError(f"{project_id} is {row['stage']}; that is final")
        if row["stage"] == stage:
            raise PortfolioError(f"{project_id} is already {stage}")
        c.execute("UPDATE projects SET stage = ?,"
                  " ready_at = CASE WHEN ? = 'ready' AND ready_at IS NULL THEN ? ELSE ready_at END,"
                  " closed_at = CASE WHEN ? = 'cancelled' THEN ? ELSE closed_at END"
                  " WHERE id = ?", (stage, stage, now, stage, now, project_id))
        body = {"from": row["stage"], "to": stage}
        if reason:
            body["reason"] = _text(reason, "reason")
        _event(c, project_id, "stage", actor, body, now)
        return dict(_project(c, project_id))


def set_tier(project_id, tier, *, actor, why, go=None, now=None, conn=None):
    now, actor = _utc(now), _actor(actor)
    if tier not in TIERS:
        raise PortfolioError(f"unknown tier {tier!r}")
    why = _text(why, "why")
    with _tx(conn) as c:
        row = _project(c, project_id, lock=True)
        c.execute("UPDATE projects SET tier = ? WHERE id = ?", (tier, project_id))
        _event(c, project_id, "tier", actor,
               {"from": row["tier"], "to": tier, "why": why, "go": go}, now)
        return dict(_project(c, project_id))


def tier_for(task) -> str:
    """Header, PH owner, repository (highest tier), then normal; fail open on DB errors."""
    try:
        header = re.split(r"\r?\n\s*\r?\n", task.get("description") or "", maxsplit=1)[0]
        for line in header.splitlines():
            match = re.fullmatch(r"\s*tier:\s*(critical|normal|low)\s*", line)
            if match:
                return match[1]
        with _tx() as c:
            rows = [dict(r) for r in c.execute("SELECT tier, ph_session, repos FROM projects").fetchall()]
        owner = _bare_session(task.get("owner_cto"))
        owned = [r["tier"] for r in rows if owner and _bare_session(r["ph_session"]) == owner]
        if owned:
            return min((t for t in owned if t in TIERS), key=TIERS.index, default="normal")
        matched = []
        for row in rows:
            repos = row["repos"]
            if isinstance(repos, str):
                repos = json.loads(repos)
            if task.get("project") in (repos or []) and row["tier"] in TIERS:
                matched.append(row["tier"])
        return min(matched, key=TIERS.index, default="normal")
    except Exception:
        return "normal"


def park(project_id: str, *, actor: str, reason: str | None = None,
         now: datetime | None = None, conn=None) -> dict:
    return set_stage(project_id, "parked", actor=actor, reason=reason, now=now, conn=conn)


EDITABLE = ("name", "goal", "repos", "done_criteria", "host")


def edit_fields(*, name: str | None = None, goal: str | None = None, repos: list[str] | None = None,
                done_criteria: str | None = None, host: str | None = None) -> dict:
    """The fields of an edit that were given (not None), checked and cleaned; PortfolioError when
    none was given or a value is bad. Needs no hub, so a caller can refuse before it connects."""
    given = {k: v for k, v in (("name", name), ("goal", goal), ("repos", repos),
                               ("done_criteria", done_criteria), ("host", host)) if v is not None}
    if not given:
        flags = ", ".join("--" + f.replace("_", "-") for f in EDITABLE)
        raise PortfolioError(f"nothing to edit: give at least one of {flags}")
    for field, value in given.items():
        if field == "repos":
            if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
                raise PortfolioError("repos must be a list of one or more non-empty strings")
            given[field] = [x.strip() for x in value]
        else:
            given[field] = _text(value, field, limit=120 if field in ("name", "host") else MAX_TEXT)
    return given


def edit_project(project_id: str, *, actor: str, name: str | None = None, goal: str | None = None,
                 repos: list[str] | None = None, done_criteria: str | None = None,
                 host: str | None = None, conn=None) -> dict:
    """Change the descriptive fields of a project: only the ones given (not None), and at least
    one. A value equal to the current one is left alone. Returns {project, changed: {field:
    {from, to}}}; no event row is written (project_events.kind has no value for it)."""
    _actor(actor)
    new = edit_fields(name=name, goal=goal, repos=repos, done_criteria=done_criteria, host=host)
    with _tx(conn) as c:
        row = _project(c, project_id, lock=True)
        changed = {f: {"from": row[f], "to": v} for f, v in new.items() if row[f] != v}
        if changed:
            sets = ", ".join(f"{f} = ?" + ("::jsonb" if f == "repos" else "") for f in changed)
            c.execute(f"UPDATE projects SET {sets} WHERE id = ?",
                      (*[json.dumps(v["to"]) if f == "repos" else v["to"] for f, v in changed.items()], project_id))
        return {"project": project_id, "changed": changed}


def milestone_add(project_id: str, title: str, *, actor: str, n: int | None = None,
                  now: datetime | None = None, conn=None) -> int:
    """Append a milestone (number = highest + 1 unless `n` is given). Returns its number."""
    now, actor = _utc(now), _actor(actor)
    title = _text(title, "title", limit=MAX_TITLE)
    if n is not None and n < 1:
        raise PortfolioError("milestone number must be >= 1")
    with _tx(conn) as c:
        _project(c, project_id, lock=True)
        if n is None:
            n = c.execute("SELECT COALESCE(MAX(n), 0) + 1 FROM milestones WHERE project_id = ?",
                          (project_id,)).fetchone()[0]
        elif c.execute("SELECT 1 FROM milestones WHERE project_id = ? AND n = ?",
                       (project_id, n)).fetchone():
            raise PortfolioError(f"{project_id} already has milestone {n}")
        c.execute("INSERT INTO milestones (project_id, n, title) VALUES (?, ?, ?)",
                  (project_id, n, title))
        _event(c, project_id, "milestone", actor, {"op": "add", "n": n, "title": title}, now)
        return n


def milestone_done(project_id: str, n: int, evidence: str, *, actor: str,
                   now: datetime | None = None, conn=None) -> dict:
    """Mark a milestone done. Evidence (sha, Drive id, URL or path) is required; the table
    CHECK refuses a done row without it too."""
    now, actor = _utc(now), _actor(actor)
    evidence = _text(evidence, "evidence", limit=MAX_TITLE)
    with _tx(conn) as c:
        _project(c, project_id, lock=True)
        got = c.execute("UPDATE milestones SET done_at = ?, evidence = ?"
                        " WHERE project_id = ? AND n = ? AND done_at IS NULL RETURNING title",
                        (now, evidence, project_id, n)).fetchone()
        if got is None:
            exists = c.execute("SELECT done_at FROM milestones WHERE project_id = ? AND n = ?",
                               (project_id, n)).fetchone()
            raise PortfolioError(f"{project_id} milestone {n} is already done" if exists
                                 else f"{project_id} has no milestone {n}")
        _event(c, project_id, "milestone", actor,
               {"op": "done", "n": n, "title": got["title"], "evidence": evidence}, now)
        return {"project": project_id, "n": n, "title": got["title"], "evidence": evidence}


def block(project_id: str, on: str, what: str, *, actor: str,
          now: datetime | None = None, conn=None) -> dict:
    """Record what the project waits for and on whom. The wait clock keeps its start while
    the blocker stays on the same party."""
    now, actor = _utc(now), _actor(actor)
    if on not in BLOCKERS:
        raise PortfolioError(f"blocker 'on' must be one of {list(BLOCKERS)}")
    what = _text(what, "what")
    with _tx(conn) as c:
        row = _project(c, project_id, lock=True)
        since = row["blocker_since"] if row["blocker_on"] == on and row["blocker_since"] else now
        c.execute("UPDATE projects SET blocker_on = ?, blocker_what = ?, blocker_since = ? WHERE id = ?",
                  (on, what, since, project_id))
        _event(c, project_id, "blocker", actor, {"on": on, "what": what}, now)
        return {"project": project_id, "on": on, "since": iso(_as_utc(since))}


def unblock(project_id: str, *, actor: str, note: str | None = None,
            now: datetime | None = None, conn=None) -> dict:
    now, actor = _utc(now), _actor(actor)
    with _tx(conn) as c:
        row = _project(c, project_id, lock=True)
        if row["blocker_on"] is None:
            raise PortfolioError(f"{project_id} has no blocker")
        c.execute("UPDATE projects SET blocker_on = NULL, blocker_what = NULL, blocker_since = NULL"
                  " WHERE id = ?", (project_id,))
        body = {"was_on": row["blocker_on"], "since": iso(_as_utc(row["blocker_since"]))
                if row["blocker_since"] else None}
        if note:
            body["note"] = _text(note, "note")
        _event(c, project_id, "unblocked", actor, body, now)
        return {"project": project_id, "was_on": row["blocker_on"]}


def decided(project_id: str, text: str, *, actor: str, now: datetime | None = None, conn=None) -> dict:
    """A decision taken for the CEO (what, in one line). Event only: no column holds it."""
    now, actor = _utc(now), _actor(actor)
    text = _text(text, "text")
    with _tx(conn) as c:
        _project(c, project_id)
        _event(c, project_id, "decided_for_ceo", actor, {"text": text}, now)
        return {"project": project_id, "text": text}


def close(project_id: str, outcome: str, learning: str, *, actor: str,
          now: datetime | None = None, conn=None) -> dict:
    """Close a project. A blocker no longer applies, so it is cleared."""
    now, actor = _utc(now), _actor(actor)
    outcome, learning = _text(outcome, "outcome"), _text(learning, "learning")
    with _tx(conn) as c:
        row = _project(c, project_id, lock=True)
        if row["stage"] in TERMINAL:
            raise PortfolioError(f"{project_id} is already {row['stage']}")
        c.execute("UPDATE projects SET stage = 'closed', closed_at = ?, outcome = ?,"
                  " blocker_on = NULL, blocker_what = NULL, blocker_since = NULL WHERE id = ?",
                  (now, outcome, project_id))
        _event(c, project_id, "closed", actor,
               {"from": row["stage"], "outcome": outcome, "learning": learning}, now)
        return dict(_project(c, project_id))


def go_add(words: str, source: str, action: str, *, actor: str, go_id: str | None = None,
           project_id: str | None = None, max_usd: float | None = None,
           given_at: datetime | None = None, expires_at: datetime | None = None,
           verify: Callable[[str], None] | None = None,
           now: datetime | None = None, conn=None) -> dict:
    """Record a CEO GO (his words verbatim, where he said it, what it allows, the cap).

    The table CHECK validates `source` as `run:Q-...`, `run:RUN-...` or `chat:<session>` and
    nothing more. `verify(source)` is the hook for the Run Inbox lookup the P3 plan asks of
    this layer: it raises to refuse. Not wired by default (no network here)."""
    now, actor = _utc(now), _actor(actor)
    words, action = _text(words, "words"), _text(action, "action")
    if not GO_SOURCE_RE.fullmatch(source or ""):
        raise PortfolioError("source must be run:Q-<id>, run:RUN-<id> or chat:<session>")
    if max_usd is not None and max_usd < 0:
        raise PortfolioError("max_usd must be >= 0")
    given_at = _utc(given_at) if given_at else now
    if expires_at is not None and _utc(expires_at) <= given_at:
        raise PortfolioError("expires_at must be after given_at")
    if verify is not None:
        verify(source)
    go_id = go_id or f"GO-{now.astimezone(BKK):%Y%m%d}-{secrets.token_hex(2)}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,60}", go_id):
        raise PortfolioError(f"bad GO id {go_id!r}")
    with _tx(conn) as c:
        if project_id is not None:
            _project(c, project_id)
        got = c.execute(
            "INSERT INTO ceo_gos (id, words, source, project_id, action, max_usd, given_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO NOTHING RETURNING id",
            (go_id, words, source, project_id, action, max_usd, given_at,
             _utc(expires_at) if expires_at else None)).fetchone()
        if got is None:
            raise PortfolioError(f"GO {go_id} already exists")
        if project_id is not None:
            _event(c, project_id, "ceo_go", actor, {"op": "add", "go": go_id, "action": action,
                                                    "max_usd": max_usd, "source": source}, now)
        return {"go": go_id, "project": project_id, "action": action, "max_usd": max_usd}


def go_use(go_id: str, *, actor: str, used_by: str | None = None,
           now: datetime | None = None, conn=None) -> dict:
    """Spend a GO: one use, while it has not expired."""
    now, actor = _utc(now), _actor(actor)
    with _tx(conn) as c:
        got = c.execute("UPDATE ceo_gos SET used_by = ?, used_at = ? WHERE id = ? AND used_at IS NULL"
                        " AND (expires_at IS NULL OR expires_at > ?)"
                        " RETURNING project_id, action, max_usd",
                        (used_by or actor, now, go_id, now)).fetchone()
        if got is None:
            row = c.execute("SELECT used_at, expires_at FROM ceo_gos WHERE id = ?", (go_id,)).fetchone()
            raise PortfolioError(f"no such GO: {go_id}" if row is None else
                                 f"GO {go_id} is already used" if row["used_at"] else f"GO {go_id} has expired")
        if got["project_id"] is not None:
            _event(c, got["project_id"], "ceo_go", actor,
                   {"op": "use", "go": go_id, "action": got["action"]}, now)
        return {"go": go_id, "project": got["project_id"], "action": got["action"],
                "max_usd": float(got["max_usd"]) if got["max_usd"] is not None else None}


def lock_take(resource: str, until: datetime, *, holder: str, project_id: str | None = None,
              now: datetime | None = None, conn=None) -> dict:
    """Take a resource until `until`. Fails (LockHeld) when another holder has it and its
    until is still ahead; the same holder extends; a lock past its until is free."""
    now, holder = _utc(now), _actor(holder)
    until = _utc(until)
    if not RESOURCE_RE.fullmatch(resource or ""):
        raise PortfolioError(f"bad resource name {resource!r}")
    if until <= now:
        raise PortfolioError("until must be in the future")
    with _tx(conn) as c:
        if project_id is not None:
            _project(c, project_id)
        got = c.execute(
            "INSERT INTO resource_locks (resource, holder_session, project_id, since, until_at)"
            " VALUES (?, ?, ?, ?, ?) ON CONFLICT (resource) DO UPDATE SET"
            " holder_session = EXCLUDED.holder_session, project_id = EXCLUDED.project_id,"
            " since = CASE WHEN resource_locks.holder_session = EXCLUDED.holder_session"
            "              AND resource_locks.until_at > ? THEN resource_locks.since ELSE EXCLUDED.since END,"
            " until_at = EXCLUDED.until_at"
            " WHERE resource_locks.holder_session = EXCLUDED.holder_session OR resource_locks.until_at <= ?"
            " RETURNING resource", (resource, holder, project_id, now, until, now, now)).fetchone()
        if got is None:
            cur = c.execute("SELECT holder_session, until_at FROM resource_locks WHERE resource = ?",
                            (resource,)).fetchone()
            raise LockHeld(f"{resource} is held by {cur['holder_session']} until {iso(_as_utc(cur['until_at']))}")
        return {"resource": resource, "holder": holder, "project": project_id, "until": iso(until)}


def lock_release(resource: str, *, holder: str, force: bool = False, conn=None) -> bool:
    """Release a lock. Only its holder may, unless `force` (the COO or the CEO). False when the
    resource was not locked."""
    holder = _actor(holder)
    with _tx(conn) as c:
        cur = c.execute("SELECT holder_session FROM resource_locks WHERE resource = ? FOR UPDATE",
                        (resource,)).fetchone()
        if cur is None:
            return False
        if cur["holder_session"] != holder and not force:
            raise PortfolioError(f"{resource} is held by {cur['holder_session']}, not {holder}")
        c.execute("DELETE FROM resource_locks WHERE resource = ?", (resource,))
        return True


# ---------------------------------------------------------------------------
# STATUS.md import (P3-G helper)
# ---------------------------------------------------------------------------

def _cells(line: str) -> list[str]:
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]


_EMPHASIS_RE = re.compile(r"([*_]{1,3})(.+?)\1(.*)", re.S)
_STATE_WORD_RE = re.compile(r"(done|landed)(?![a-z])(.*)", re.I | re.S)
_MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
          r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?![a-z])\.?")
_ZONE = r"(?:th|ict|bkk|utc|gmt|cest|cet|z|[+-]\d{2}:?\d{2})(?![a-z])"
_CLOCK = rf"\d{{1,2}}[:.]\d{{2}}(?::\d{{2}})?(?:\s*[ap]m)?(?:\s*{_ZONE})?"
_STAMP = (rf"(?:\d{{4}}-\d{{2}}-\d{{2}}(?:[t ]\d{{1,2}}:\d{{2}}(?::\d{{2}})?(?:\s*{_ZONE})?)?"
          rf"|\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?|\d{{1,2}}\s+{_MONTH}(?:\s+\d{{4}})?"
          rf"|{_MONTH}\s+\d{{1,2}}(?:,?\s+\d{{4}})?|{_CLOCK})")
_AFTER_DONE_RE = re.compile(rf"(?:[\s,;:.()@~–—-]*(?:(?:at|on)\s+)?{_STAMP})*[\s.;,)]*", re.I)


def _plain_state(state: str) -> str:
    """A State cell without the Markdown emphasis around it: `**done** 10:04 TH`, `*done*`,
    `__done__`. Only a balanced pair is removed, so `**done` and `done*` stay as they are."""
    s = state.strip()
    for _ in range(3):
        m = _EMPHASIS_RE.fullmatch(s)
        if m is None:
            break
        s = (m.group(2) + m.group(3)).strip()
    return s


def state_is_done(state: str) -> bool:
    """Does a State cell say the milestone is finished? The word is `landed` or `done`, in any
    case and with or without emphasis. After `landed` a note may follow (`landed; install waits
    on the CEO`), as it always could. After `done` only a time or a date may follow (`done 10:04
    TH`, `done 2026-10-14`, `done 14 Oct`), so `done?`, `done, but ...` and `done in a branch`
    are not done; `not done`, `undone` and `planned` do not start with the word. Whether the
    row also has evidence is the caller's rule."""
    m = _STATE_WORD_RE.fullmatch(_plain_state(state))
    if m is None:
        return False
    if m.group(1).casefold() == "landed":
        return not m.group(2).lstrip().startswith("?")
    return _AFTER_DONE_RE.fullmatch(m.group(2)) is not None


def parse_status_milestones(text: str) -> list[dict]:
    """The milestone table(s) of a PH STATUS.md: a header row with Milestone, State and
    Evidence columns. A row counts as done when its State says so (state_is_done) and its
    Evidence is not empty. Returns [{code, title, state, evidence, state_done, done}] in file
    order; `state_done` is the State alone, so a row with `state_done and not done` is one
    that says done and shows no evidence."""
    rows: list[dict] = []
    cols: dict[str, int] | None = None
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            cols = None
            continue
        cells = _cells(line)
        low = [c.casefold() for c in cells]
        if cols is None:
            if "milestone" in low and "evidence" in low and "state" in low:
                cols = {"code": 0, "title": low.index("milestone"), "state": low.index("state"),
                        "evidence": low.index("evidence")}
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if len(cells) <= max(cols.values()) or not cells[cols["title"]]:
            continue
        code, title = cells[cols["code"]], cells[cols["title"]]
        state, evidence = cells[cols["state"]], cells[cols["evidence"]]
        evidence = "" if evidence in ("-", "—", "–") else evidence
        full = f"{code} {title}".strip() if code and code != "#" else title
        state_done = state_is_done(state)
        rows.append({"code": code, "title": full if len(full) <= MAX_TITLE else full[:MAX_TITLE - 1] + "…",
                     "state": state, "evidence": evidence[:MAX_TITLE],
                     "state_done": state_done, "done": state_done and bool(evidence)})
    return rows


def import_milestones(project_id: str, rows: list[dict], *, actor: str, source: str,
                      now: datetime | None = None, conn=None) -> dict:
    """Write parsed STATUS.md rows as the project's milestones, once: refused when the project
    already has any. Done rows are marked done at `now` (the file has no date)."""
    now, actor = _utc(now), _actor(actor)
    if not rows:
        raise PortfolioError("no milestone rows to import")
    with _tx(conn) as c:
        _project(c, project_id, lock=True)
        have = c.execute("SELECT count(*) FROM milestones WHERE project_id = ?", (project_id,)).fetchone()[0]
        if have:
            raise PortfolioError(f"{project_id} already has {have} milestones; the import runs once "
                                 "(--reimport marks the ones the file now shows as done)")
        for n, r in enumerate(rows, 1):
            c.execute("INSERT INTO milestones (project_id, n, title, done_at, evidence) VALUES (?, ?, ?, ?, ?)",
                      (project_id, n, r["title"], now if r["done"] else None, r["evidence"] if r["done"] else None))
        done = sum(1 for r in rows if r["done"])
        _event(c, project_id, "milestone", actor,
               {"op": "import", "source": source, "total": len(rows), "done": done}, now)
        return {"project": project_id, "total": len(rows), "done": done}


def reimport_milestones(project_id: str, rows: list[dict], *, actor: str, source: str,
                        dry_run: bool = False, now: datetime | None = None, conn=None) -> dict:
    """Catch a project that was imported earlier up with its STATUS.md. A milestone that is open
    in the hub and done in the file (with evidence) is marked done at `now` with the file's
    evidence. Nothing else changes: a done milestone is never reopened or given other evidence,
    no row is added (so no duplicate), and a file row whose title is not in the hub exactly once
    (and in the file exactly once) is reported under `unmatched`, not guessed. Milestones are
    matched by title because that is what import_milestones stored. `dry_run` writes nothing.
    Returns {project, total, done_in_file, marked: [{n, title, evidence}], already_done,
    unmatched: [title], dry_run}. One `milestone` event (op reimport) when anything was marked."""
    now, actor = _utc(now), _actor(actor)
    if not rows:
        raise PortfolioError("no milestone rows to import")
    in_file: dict[str, int] = {}
    for r in rows:
        in_file[r["title"]] = in_file.get(r["title"], 0) + 1
    with _tx(conn) as c:
        _project(c, project_id, lock=True)
        have: dict[str, list] = {}
        for m in c.execute("SELECT n, title, done_at FROM milestones WHERE project_id = ? ORDER BY n",
                           (project_id,)).fetchall():
            have.setdefault(m["title"], []).append(m)
        if not have:
            raise PortfolioError(f"{project_id} has no milestones; use the import (without --reimport)")
        marked: list[dict] = []
        already, unmatched = 0, []
        for r in rows:
            if not r["done"]:
                continue
            hit = have.get(r["title"], [])
            if len(hit) != 1 or in_file[r["title"]] != 1:
                unmatched.append(r["title"])
            elif hit[0]["done_at"] is not None:
                already += 1
            elif dry_run or c.execute("UPDATE milestones SET done_at = ?, evidence = ?"
                                      " WHERE project_id = ? AND n = ? AND done_at IS NULL RETURNING n",
                                      (now, r["evidence"], project_id, hit[0]["n"])).fetchone():
                marked.append({"n": hit[0]["n"], "title": r["title"], "evidence": r["evidence"]})
        if marked and not dry_run:
            _event(c, project_id, "milestone", actor,
                   {"op": "reimport", "source": source, "marked": [m["n"] for m in marked]}, now)
        return {"project": project_id, "total": len(rows), "done_in_file": sum(1 for r in rows if r["done"]),
                "marked": marked, "already_done": already, "unmatched": unmatched, "dry_run": dry_run}


# ---------------------------------------------------------------------------
# reads
# ---------------------------------------------------------------------------

def _jsonable(v):
    if isinstance(v, datetime):
        return iso(v)
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def get_project(project_id: str, *, conn=None) -> dict:
    with _tx(conn) as c:
        return dict(_project(c, project_id))


def go_project(go_id: str, *, conn=None) -> str | None:
    """The project a GO names (None for a GO without one); PortfolioError for an unknown GO."""
    with _tx(conn) as c:
        row = c.execute("SELECT project_id FROM ceo_gos WHERE id = ?", (go_id,)).fetchone()
        if row is None:
            raise PortfolioError(f"no such GO: {go_id}")
        return row["project_id"]


def show(project_id: str | None = None, *, now: datetime | None = None, conn=None) -> dict:
    """One project in full (row, milestones, last events, locks, GOs), or every project in brief."""
    now = _utc(now)
    with _tx(conn) as c:
        if project_id is None:
            tot = {r["project_id"]: (r["done"], r["total"]) for r in c.execute(
                "SELECT project_id, count(done_at) AS done, count(*) AS total FROM milestones"
                " GROUP BY project_id").fetchall()}
            out = []
            for r in c.execute("SELECT id, name, lane, stage, tier, blocker_on, blocker_since, last_active"
                               " FROM projects ORDER BY lane, id").fetchall():
                d, t = tot.get(r["id"], (0, 0))
                out.append(_jsonable({**dict(r), "pct": pct(d, t), "milestones": {"done": d, "total": t}}))
            return {"projects": out}
        proj = dict(_project(c, project_id))
        ms = [dict(r) for r in c.execute("SELECT n, title, done_at, evidence FROM milestones"
                                         " WHERE project_id = ? ORDER BY n", (project_id,)).fetchall()]
        ev = [dict(r) for r in c.execute("SELECT at, kind, actor, body FROM project_events"
                                         " WHERE project_id = ? ORDER BY at DESC, id DESC LIMIT 20",
                                         (project_id,)).fetchall()]
        locks = [dict(r) for r in c.execute("SELECT resource, holder_session, since, until_at FROM"
                                            " resource_locks WHERE project_id = ? ORDER BY resource",
                                            (project_id,)).fetchall()]
        gos = [dict(r) for r in c.execute("SELECT id, action, max_usd, given_at, expires_at, used_by, used_at"
                                          " FROM ceo_gos WHERE project_id = ? ORDER BY given_at",
                                          (project_id,)).fetchall()]
        done = sum(1 for m in ms if m["done_at"])
        return _jsonable({"project": proj, "pct": pct(done, len(ms)),
                          "milestones": ms, "events": ev, "locks": locks, "gos": gos})


def _midnight_bkk(now: datetime) -> datetime:
    local = now.astimezone(BKK)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def _active_seconds(stamps: list[datetime]) -> int:
    """Seconds of activity in a sorted timestamp list: the gaps of at most WORKING_S between
    neighbours. A stamp with no neighbour inside that window adds nothing."""
    gaps = [(b - a).total_seconds() for a, b in zip(stamps, stamps[1:])]
    return int(sum(g for g in gaps if g <= WORKING_S))


def _chain_start(stamps: list[datetime]) -> datetime | None:
    """Where the run of stamps ending at the newest one began (gaps of at most WORKING_S)."""
    if not stamps:
        return None
    start = stamps[-1]
    for a in reversed(stamps[:-1]):
        if start - a > timedelta(seconds=WORKING_S):
            break
        start = a
    return start


def _monitor_all(now: datetime, conn=None) -> list[dict]:
    """Every monitored project as a P3-E row, in monitor order, before the row cap. The rules
    are in monitor_rows."""
    midnight = _midnight_bkk(now)
    with _tx(conn) as c:
        projects = c.execute(
            "SELECT id, name, lane, stage, tier, ph_session, blocker_on, blocker_since, last_active, opened_at"
            " FROM projects WHERE stage IN ('active', 'review', 'parked')").fetchall()
        ms = {r["project_id"]: (r["done"], r["total"]) for r in c.execute(
            "SELECT project_id, count(done_at) AS done, count(*) AS total FROM milestones"
            " GROUP BY project_id").fetchall()}
        beats: dict[str, list[datetime]] = {}
        for r in c.execute("SELECT project_id, at FROM session_heartbeats"
                           " WHERE project_id IS NOT NULL").fetchall():
            beats.setdefault(r["project_id"], []).append(_as_utc(r["at"]))
        today: dict[str, list[datetime]] = {}
        for r in c.execute("SELECT project_id, at FROM project_events WHERE at >= ? AND at <= ?",
                           (midnight, now)).fetchall():
            today.setdefault(r["project_id"], []).append(_as_utc(r["at"]))
        last_event = {r["project_id"]: _as_utc(r["at"]) for r in c.execute(
            "SELECT project_id, max(at) AS at FROM project_events GROUP BY project_id").fetchall()}
        parked_at = {r["project_id"]: _as_utc(r["at"]) for r in c.execute(
            "SELECT DISTINCT ON (project_id) project_id, at FROM project_events"
            " WHERE kind = 'stage' AND body->>'to' = 'parked' ORDER BY project_id, at DESC").fetchall()}
        running = c.execute(
            "SELECT project, owner_role, owner_cto, COALESCE(spawned_at, updated_at, created_at) AS since,"
            " updated_at FROM tasks WHERE status = 'in_progress'").fetchall()
    fresh = now - timedelta(seconds=GENERATING_MAX_AGE_S)
    tasks = [(r["project"], r["owner_role"], r["owner_cto"], _as_utc(r["since"]))
             for r in running if (_as_utc(r["updated_at"]) or fresh) >= fresh]

    rows = []
    for p in projects:
        pid = p["id"]
        done, total = ms.get(pid, (0, 0))
        hb = [t for t in beats.get(pid, []) if t <= now]
        hb_last = max(hb) if hb else None
        stamps = sorted([t for t in hb if t >= midnight] + today.get(pid, []))
        seen = [t for t in (_as_utc(p["last_active"]), hb_last, last_event.get(pid)) if t and t <= now]
        last_active = max(seen) if seen else (_as_utc(p["opened_at"]) or now)
        on = p["blocker_on"]
        since_blocker = _as_utc(p["blocker_since"]) or last_active
        starts = [s or last_active for (proj, role, owner, s) in tasks
                  if proj == pid or (role == "project_head" and p["ph_session"] and owner == p["ph_session"])]
        if p["stage"] == "parked":
            state, since = "parked", parked_at.get(pid) or last_active
        elif on == "ceo":
            state, since = "waiting_ceo", since_blocker
        elif on:
            state, since = "waiting", since_blocker
        elif starts:
            state, since = "generating", min(starts)
        elif hb_last and (now - hb_last).total_seconds() <= WORKING_S:
            state, since = "working", _chain_start(stamps) or hb_last
        elif hb_last and (now - hb_last).total_seconds() <= IDLE_S:
            state, since = "idle", hb_last
        else:
            state, since = "stalled", hb_last or last_active
        rows.append({
            "id": pid, "name": p["name"], "lane": p["lane"],
            "pct": pct(done, total), "milestones": {"done": done, "total": total},
            "state": state, "state_since": iso(min(since, now)), "last_active": iso(last_active),
            "active_today_s": _active_seconds(stamps),
            "blocker": {"on": on, "since": iso(since_blocker)} if on else None,
            "parked": p["stage"] == "parked",
            "_sort": last_active,
        })
    rows.sort(key=lambda r: (r["parked"], -r["_sort"].timestamp(), r["id"]))
    for r in rows:
        del r["_sort"]
    return rows


def monitor_rows(now: datetime | None = None, *, conn=None) -> list[dict]:
    """The P3-E v1 `projects` list: projects in stage active, review or parked, at most MAX_ROWS.

    State, first match wins: parked (stage) > waiting_ceo (blocker on ceo) > waiting (any other
    blocker) > generating (a worker task of the project is in_progress and was touched in the last
    24 h) > working (a session heartbeat within 5 min) > idle (within 24 h) > stalled.

    "A worker task of the project": status in_progress, and either owner_role project_head with
    owner_cto equal to the project's ph_session, or tasks.project equal to the project id.

    state_since: parked, the stage event that parked it; waiting, the blocker's since; generating,
    the oldest running task's start; working, where the current run of activity (gaps of at most
    5 min) began; idle and stalled, the project's last heartbeat (its last sign of life).
    last_active: the newest of projects.last_active, a session heartbeat and a project event.
    active_today_s: from 00:00 Asia/Bangkok, the gaps of at most 5 min between a project's
    heartbeats and events. The blocker's text is never read here, only who it waits on and since
    when. Order: non-parked by last_active desc, then parked."""
    return _monitor_all(_utc(now), conn)[:MAX_ROWS]


def monitor_payload(now: datetime | None = None, *, conn=None) -> dict:
    """The whole P3-E v1 response body. `counts` are before the row cap."""
    now = _utc(now)
    rows = _monitor_all(now, conn)
    counts = {"in_progress": sum(1 for r in rows if not r["parked"]),
              "parked": sum(1 for r in rows if r["parked"])}
    return {"v": 1, "generated_at": iso(now), "counts": counts, "projects": rows[:MAX_ROWS]}
