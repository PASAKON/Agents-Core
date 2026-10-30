"""Fill-based host selection shared by workers and Project Heads.

Contabo is preferred below the configured limit; other hosts rank by fill,
then running workers. Explicit pins restrict candidates but retain all resource
checks. Complete live readings are required. No eligible host leaves work
pending for the watchdog's host queue. A shared DB slot serializes the CEO's
CPU exception for Contabo-only tasks. Header helpers also serve runner routing.
"""
from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timezone

from lib import config, db

ENV_FLAG = "ORG_HOST_ROUTER"
PROBE_MAX_AGE_S = 60
# A probe stamped slightly in the future is a clock difference between boxes,
# not a fresher probe. Beyond this it is treated as unreadable, never as fresh.
PROBE_FUTURE_SKEW_S = 10
_NOT_ONLINE = ("offline", "pending_identity", "leaving", "left")   # leaving: W4.2b, `leave --live` has begun

_NEEDS_RE = re.compile(r"^[ \t]*needs:[ \t]*(.*)$", re.IGNORECASE | re.MULTILINE)

# A directive line (`needs:` here, `override:` in tools/route.py) counts only in
# the description's HEADER: the leading lines up to the first blank line, at most
# this many. Text pasted into a description (a web page, a letter, a quoted worker
# report) must not be able to pin a task to a host or satisfy the IRON §59 gate
# (W2.7 review F11). A directive after the header is ignored, never an error.
MAX_HEADER_LINES = 5


def header(description: str | None) -> str:
    """The header block of `description` as text; "" for None or an empty one.

    Blank means empty after str.strip(), so a line of spaces, tabs, \\r or a
    Unicode space ends the header too. Lines are split on \\n only, the same
    boundary `^` has in a MULTILINE regex. The one definition of "header" that
    parse_needs, tools.route.check_override and add_needs_line share.
    """
    out: list[str] = []
    for line in (description or "").split("\n"):
        if not line.strip() or len(out) >= MAX_HEADER_LINES:
            break
        out.append(line)
    return "\n".join(out)


def add_header_line(description: str | None, line: str) -> str:
    """`description` with `line` added at the end of its header block.

    No existing header line moves, so a directive already on line 1 stays on
    line 1. Trailing whitespace of the description is dropped. Raises
    ValueError when the header already holds MAX_HEADER_LINES lines: there is
    no place left where the line would count, and adding it below the header
    would be a silent no-op.
    """
    text = (description or "").rstrip()
    lines = text.split("\n") if text else []
    at = 0
    while at < len(lines) and lines[at].strip():
        at += 1
    if at >= MAX_HEADER_LINES:
        raise ValueError(
            f"the description's first block already has {MAX_HEADER_LINES} lines "
            f"(no blank line before line {MAX_HEADER_LINES + 1}): a directive "
            f"counts only in that block, so there is no room for `{line}`. "
            "Put a blank line after the opening lines, or write the line into "
            "the block yourself."
        )
    lines.insert(at, line)
    return "\n".join(lines)


def enabled() -> bool:
    """ORG_HOST_ROUTER is 1/true/on. Default off (same switch shape as
    lib.mesh.enabled)."""
    value = os.environ.get(ENV_FLAG)
    return (value.strip().lower() in ("1", "true", "on") if value is not None
            else bool(settings().get("enabled", False)))


def settings() -> dict:
    return yaml.safe_load(config.HOSTS_CONFIG.read_text(encoding="utf-8")).get("router", {})


@dataclass
class HostPick:
    host: str | None            # None = no host fits; the task stays pending
    line: str                   # the one delegate_log line for this decision
    rejected: dict[str, str] = field(default_factory=dict)


def parse_needs(description: str | None) -> list[str]:
    """Names from every `needs: a, b` line in the HEADER of a task description
    (`header`; a `needs:` line further down is ignored). Lowercased,
    de-duplicated, in order. No such line (or an empty one) = no constraint."""
    out: list[str] = []
    for m in _NEEDS_RE.finditer(header(description)):
        for name in m.group(1).split(","):
            name = name.strip().lower()
            if name and name not in out:
                out.append(name)
    return out


def add_needs_line(description: str, needs: str | None) -> str:
    """`description` plus a `needs: a, b` line, for create_task(needs=...).

    `needs` is a JSON array string or comma-separated names, the two shapes
    create_task already takes for `touches`. Empty leaves the text unchanged.
    The line goes at the end of the header block (`add_header_line`), where
    parse_needs reads it; ValueError if that block is already full.
    """
    raw = (needs or "").strip()
    if not raw:
        return description
    try:
        names = json.loads(raw)
        if not isinstance(names, list):
            names = [raw]
    except ValueError:
        names = raw.split(",")
    line = ", ".join(n for n in (str(x).strip() for x in names) if n)
    if not line:
        return description
    return add_header_line(description, f"needs: {line}")


def manual_line(host: str, source: str) -> str:
    return f"manual: {host} · {source}"


def _json_list(raw) -> list[str] | None:
    """A JSON-array column as a list; None when absent or not a list."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None
    if not isinstance(raw, list):
        return None
    return [str(x).strip().lower() for x in raw]


def _probe_problem(row: dict | None, now: datetime) -> str | None:
    """Why this host's probe cannot be trusted, or None when it is fresh."""
    stale = f"no probe ≤{PROBE_MAX_AGE_S} s"
    raw = (row or {}).get("probed_at")
    if not raw:
        return stale
    try:
        stamp = datetime.fromisoformat(str(raw).strip())
    except ValueError:
        return f"{stale} (probed_at unreadable)"
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    age = (now - stamp).total_seconds()
    if age < -PROBE_FUTURE_SKEW_S:
        return f"{stale} (probed_at in the future)"
    if age > PROBE_MAX_AGE_S:
        return f"{stale} (last one {int(age)} s old)"
    return None


def _decode_touches(raw) -> list:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    return raw if isinstance(raw, list) else []


def role_runners(task: dict) -> list[str]:
    """Runners the task's role may use, in route's order.

    Mirrors tools.delegate._route_runner: a hand-pinned runner, model_hint
    'claude' or ORG_ROUTER=off skip the router, so the runner is then that pin
    (or claude); a role with no router class stays on claude. Otherwise the
    runner of every `ok` plan from route.plan. route.py is read, never changed.
    """
    pinned = (task.get("runner") or "").strip().lower()
    if pinned:
        return [pinned]
    if ((task.get("model_hint") or "").strip().lower() == "claude"
            or os.environ.get("ORG_ROUTER", "").strip().lower() == "off"):
        return ["claude"]
    # Lazy: tools.route imports tools.delegate, which imports this module.
    from tools import route
    brief = task.get("description")
    cfg = route.load_plans()
    cls = route.class_for(task["role"], brief, cfg)
    if not cls:
        return ["claude"]
    plans = route.plan(cls, touches=_decode_touches(task.get("touches")),
                       brief=brief, host=None, cfg=cfg)
    out: list[str] = []
    for p in plans:
        if p.verdict == "ok" and p.choice.runner not in out:
            out.append(p.choice.runner)
    return out


def _num(v, fmt: str) -> str:
    return "?" if v is None else format(v, fmt)


def _exception_slot(task_id: str, reserve: bool, ttl: int) -> bool:
    """One shared DB slot; active jobs retain it beyond the pending-start TTL."""
    from datetime import timedelta
    key = "host-router:contabo-cpu"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        conn.execute(
            "DELETE FROM locks WHERE key=? AND NOT EXISTS "
            "(SELECT 1 FROM tasks WHERE tasks.id=locks.owner AND "
            "(tasks.status IN ('in_progress','queued_remote','rate_limited','stalled') "
            "OR (tasks.status='pending' AND locks.expires_at>?)))", (key, now))
        if not reserve:
            return conn.execute("SELECT owner FROM locks WHERE key=?", (key,)).fetchone() is None
        row = conn.execute(
            "INSERT INTO locks (key,owner,expires_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO NOTHING RETURNING owner", (key, task_id, expires)).fetchone()
        if row is not None:
            return True
        # A mesh handoff rechecks the same task on the target host. It is
        # still one job, so its reservation must survive that second check.
        existing = conn.execute("SELECT owner FROM locks WHERE key=?", (key,)).fetchone()
        return existing is not None and existing["owner"] == task_id


def release_exception(task_id: str) -> None:
    task = db.get_task(task_id)
    if not task or task.get("status") not in ("in_progress", "queued_remote", "rate_limited", "stalled"):
        db.release_lock("host-router:contabo-cpu", task_id)


def pick_host(task: dict, *, hosts_rows: list[dict] | None = None,
              now: datetime | None = None, reserve_exception: bool = False) -> HostPick:
    """Contabo first, then lowest complete fill; explicit pins never migrate.

    Supplied rows are probe summaries for offline tests. Production obtains fresh
    facts via host_fill, with remote probes concurrent and bounded by its timeout.
    """
    from tools import host_fill
    try:
        policy = settings()
        registry = config.hosts()
        pin = task.get("host")
        names = [pin] if pin else list(host_fill.HOSTS)
        if hosts_rows is None:
            with ThreadPoolExecutor(max_workers=3) as pool:
                rows = list(pool.map(
                    lambda name: host_fill.probe(name, timeout=policy.get("probe_timeout_s", 10)),
                    names))
        else:
            rows = hosts_rows
        by_name = {r.get("name", r.get("host")): r for r in rows}
        limit = policy.get("fill_limit_pct", 80)
        usable = role_runners(task)
        rejected, candidates = {}, []
        summaries = []
        for name in names:
            row = by_name.get(name, {})
            facts = row.get("facts", row)
            pct, highest, missing = host_fill.fill(facts, rounded=False)
            summaries.append(f"{name} {_num(pct, '.1f')}% ({highest or 'unknown'})")
            why = None
            exception = False
            if name not in registry:
                why = "host not configured"
            elif not row.get("online", False):
                why = "offline"
            elif pct is None or missing:
                why = "fill unknown or incomplete"
            elif name in policy.get("never_on", {}).get(task.get("project"), []) or (
                    name == "winbox" and task.get("project", "").casefold() == "mooniex-expertadvisor"):
                why = "project excluded"
            elif row.get("running") is None or row["running"] >= registry[name]["max_workers"]:
                why = "worker cap reached or unknown"
            elif facts.get("ram_free_gb", -1) < policy.get("min_free_ram_gb", {}).get(name, 0):
                why = "free RAM below floor"
            elif task.get("role") == "project_head" and name == "winbox" and facts.get("ceo_hold", True):
                why = "PC lease held or unknown"
            else:
                try:
                    config.project_path_for_host(task["project"], name)
                except (ValueError, KeyError):
                    why = "project path unavailable"
                provides = _json_list(facts.get("provides", registry[name].get("provides"))) or []
                if not why and not set(parse_needs(task.get("description"))).issubset(provides):
                    why = "required capability unavailable"
                runners = _json_list(facts.get("runners", registry[name].get("runners"))) or []
                if not why and not set(usable).intersection(runners):
                    why = "no usable runner"
                if not why and pct >= limit:
                    ram = 100 * (1 - facts["ram_free_gb"] / facts["ram_total_gb"])
                    disk = 100 * (1 - facts["free_gb"] / facts["disk_total_gb"])
                    exception = (
                        pin == name == "contabo" and highest == "cpu"
                        and ram < limit and disk < limit
                        and facts["ram_free_gb"] >= policy.get("cpu_exception", {}).get("min_free_ram_gb", 1.6)
                        and bool(task.get("id"))
                    )
                    if not exception:
                        why = "fill at or above limit"
            if why:
                rejected[name] = why
            else:
                candidates.append((name, pct, row["running"], exception))
        if not candidates:
            return HostPick(None, "queued for host · " + " · ".join(summaries)
                            + " · " + "; ".join(f"{k}: {v}" for k, v in rejected.items()), rejected)
        best = min(candidates, key=lambda c: (c[0] != policy.get("first_host", "contabo"), c[1], c[2], c[0]))
        if best[3] and not _exception_slot(task["id"], reserve_exception,
                                          policy.get("cpu_exception", {}).get("slot_ttl_s", 600)):
            return HostPick(None, "queued for host · CPU exception slot busy", rejected)
        return HostPick(best[0], f"host: {best[0]} · " + " · ".join(summaries)
                        + (" · CPU exception" if best[3] else ""), rejected)
    except Exception as exc:
        return HostPick(None, f"queued for host · router unavailable ({type(exc).__name__})")
