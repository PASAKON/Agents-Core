"""Host router (PLAN-auto-dispatch H2, Org Mesh W2.6, host-fill rule 2026-10-30).

    pick_host(task) -> HostPick

WHICH runner a task uses is tools/route.py's job. This module answers WHERE. It is
called from tools/delegate.py's host-resolution block only when the router switch is
on (config/hosts.yaml `router.enabled`, or env ORG_HOST_ROUTER, which wins).

A host is a candidate only if ALL of these hold (each rejection gets exactly one
reason, the first check that failed, and the reasons go to delegate_log):

  1. a probe no older than 60 s is in the `hosts` table (tools/node_dispatch.py
     `probe` writes it) and `status` is not offline / pending_identity / leaving / left
  2. `provides` contains every name in the task's `needs: a, b` description line
  3. `running < max_workers`
  4. the project has `paths.<host>` in config/projects.yaml
  5. the host-fill rules of config/hosts.yaml `router:` (CEO 2026-10-30): the
     project is not in `never_on` for the host (ExpertAdvisor never on winbox), the
     host keeps its `min_free_ram_gb` (winbox 4 GB), a Project Head does not start
     on winbox while the PC lease is held, and the host's fill (max of RAM, CPU and
     disk used %) is under `fill_limit_pct` (80). Only a row that carries fill
     sensors is judged on fill; a missing sensor makes winbox and the Mac not
     eligible, Contabo keeps the old rule while the readings it has are under the limit.
  6. at least one runner the role can use is installed on the host
     (`hosts.runners`, from the probe)

CPU exception (CEO, Q-20261030-0315-9f03): work pinned to Contabo may start at
80 % or more when CPU is the highest reading, RAM and disk are under the limit and
at least `cpu_exception.min_free_ram_gb` is free; one such job at a time, org-wide.

Survivors rank: Contabo first while it passes, then the lowest fill (no reading
ranks last), then the fewest running workers, then most `ram_free_gb`, then name. A
task that names its host (`task["host"]`) is judged on that host alone: it is never
moved, but the same checks apply. No survivor -> HostPick.host is None and `line` is
`no_host: ...`; the caller leaves the task pending and queues it for the host
(tools/host_queue.py). There is no fallback host: a stale or missing probe means
"unknown", and unknown is never "fine".

`hosts_rows` (tests, mesh_check) are hub rows or `tools.host_fill.probe` rows. With
none, the hub table is read and Contabo is probed live; winbox and the Mac are
probed live (10 s, in parallel) only when Contabo does not take the task.

`needs` has no column; it is read from a description line, the same way
route.check_override reads `override:`. Both read it from the description's HEADER
only (see `header` below): a `needs:` pasted further down is text, not a directive
(W2.7 review F11, W2.11).
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




# --- host-fill rules (CEO 2026-10-30), added on top of the hub-row checks ---

_FILL_KEYS = ("ram_total_gb", "disk_total_gb", "cpu_pct")
_JOIN_BLOCKED = ("pending_identity", "leaving", "left")


def _hub_shape(r: dict, registry: dict, now: datetime) -> dict:
    """A `tools.host_fill.probe` row as a hub row; a hub row passes through.

    The probe was taken just now, so the row is fresh by definition. What the
    probe does not carry (provides, cap, runners) comes from config/hosts.yaml."""
    if "host" in r or "name" not in r:
        return r
    name, cfg, facts = r["name"], registry.get(r["name"]) or {}, r.get("facts") or {}
    cpu = facts.get("cpu_pct")
    row = {"host": name, "status": "online" if r.get("online") else "offline",
           "probed_at": now.isoformat(), "facts": facts,
           "provides": facts.get("provides", cfg.get("provides")),
           "max_workers": r.get("max_workers", cfg.get("max_workers")),
           "running": r.get("running"), "ram_free_gb": facts.get("ram_free_gb"),
           "load_per_core": facts.get("load_per_core", None if cpu is None else cpu / 100),
           "runners": facts.get("runners", cfg.get("runners"))}
    if not r.get("online"):
        row["unanswered"] = True
    return row


def _fill_facts(row: dict) -> dict:
    return {**row, **(row.get("facts") or {})}


def _used_pct(facts: dict, free_key: str, total_key: str) -> float | None:
    try:
        return 100 * (1 - float(facts[free_key]) / float(facts[total_key]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def _cap_reason(name: str, row: dict, task: dict, policy: dict,
                pin: str | None) -> tuple[str | None, bool]:
    """(why not, CPU exception used) for the host-fill rules; (None, False) passes."""
    from tools import host_fill
    facts = _fill_facts(row)
    project = str(task.get("project") or "")
    if name in (policy.get("never_on") or {}).get(project.casefold(), []):
        return f"{project} never runs on {name}", False
    floor = (policy.get("min_free_ram_gb") or {}).get(name)
    capable = any(k in facts for k in _FILL_KEYS)
    if floor is not None:
        free = facts.get("ram_free_gb")
        if free is None:
            return f"free RAM unknown (floor {floor} GB)", False
        if free < floor:
            return f"free RAM {free:.1f} GB under the {floor} GB floor", False
    if capable and task.get("role") == "project_head" and name == "winbox" \
            and facts.get("ceo_hold", True):
        return "PC lease held or unknown", False
    if not capable:
        return None, False        # hub-only row: no fill sensors, the old checks decide
    pct, highest, missing = host_fill.fill(facts, rounded=False)
    limit = policy.get("fill_limit_pct", 80)
    if pct is not None and pct >= limit:
        ram = _used_pct(facts, "ram_free_gb", "ram_total_gb")
        disk = _used_pct(facts, "free_gb", "disk_total_gb")
        exception = (
            pin == name == "contabo" and highest == "cpu" and bool(task.get("id"))
            and ram is not None and ram < limit and disk is not None and disk < limit
            and facts["ram_free_gb"] >= (policy.get("cpu_exception") or {}).get("min_free_ram_gb", 1.6))
        return (None, True) if exception else (f"fill {pct:.1f}% ({highest}) at or above {limit}%", False)
    if missing and (pct is None or name != policy.get("first_host", "contabo")):
        return f"fill incomplete (no {', '.join(missing)} reading)", False
    return None, False


def _live_rows(names: list[str], timeout) -> dict[str, dict]:
    """`tools.host_fill.probe` of each host, in parallel and bounded by `timeout`."""
    from tools import host_fill
    if not names:
        return {}

    def one(name):
        try:
            return host_fill.probe(name, timeout=timeout)
        except Exception:  # noqa: BLE001 -- a host that cannot be probed is a host that did not answer
            return {"name": name, "online": False}

    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        return dict(zip(names, pool.map(one, names)))


def _merge_live(rows: list[dict], live: dict[str, dict], registry: dict, now: datetime) -> list[dict]:
    """Hub rows with the live probes laid over them. The hub keeps what a probe
    cannot know: the join state (leaving / left / pending_identity) and `provides`."""
    by = {r["host"]: r for r in rows if "host" in r}
    for name, probe in live.items():
        row = _hub_shape(probe, registry, now)
        hub = by.get(name)
        if hub and not row.get("unanswered"):
            if hub.get("provides") is not None:
                row["provides"] = hub["provides"]
            if (hub.get("status") or "").strip().lower() in _JOIN_BLOCKED:
                row["status"] = hub["status"]
        by[name] = row
    return list(by.values())


def pick_host(task: dict, *, hosts_rows: list[dict] | None = None,
              now: datetime | None = None, reserve_exception: bool = False) -> HostPick:
    """Choose a host for `task` (a tasks row), or say why none fits.

    `hosts_rows` and `now` exist for tests and mesh_check; without rows the hub
    table is read and the hosts are probed live (module docstring).
    Never raises on bad data: an unreadable table or router error is a
    rejection of every host, with the error as the reason.
    """
    now = now or datetime.now(timezone.utc)
    pin = (task.get("host") or "").strip().lower() or None
    try:
        policy, registry = settings(), config.hosts()
        rows = db.list_hosts() if hosts_rows is None else list(hosts_rows)
        configured = set(registry)
        known_project = task.get("project") in config.projects()
        scope = [pin] if pin else sorted(configured | {r.get("host") or r.get("name") for r in rows})
    except Exception as e:  # noqa: BLE001 -- see docstring
        return HostPick(None, f"no_host: router error: {type(e).__name__}: {e}")
    ctx = dict(task=task, policy=policy, registry=registry, known_project=known_project,
               now=now, pin=pin, reserve=reserve_exception)
    if hosts_rows is not None:
        return _decide([_hub_shape(r, registry, now) for r in rows], scope, **ctx)
    first, timeout = policy.get("first_host", "contabo"), policy.get("probe_timeout_s", 10)
    probeable = [n for n in scope if n in configured]
    live: dict[str, dict] = {}
    probed: list[str] = []
    pick = None
    for stage in ([n for n in probeable if n == first], [n for n in probeable if n != first]):
        if not stage:
            continue
        live.update(_live_rows(stage, timeout))
        probed += stage
        pick = _decide(_merge_live(rows, live, registry, now),
                       [n for n in scope if n in probed or n not in configured], **ctx)
        if pick.host:
            return pick
    return pick or _decide(_merge_live(rows, live, registry, now), scope, **ctx)


def _decide(rows: list[dict], names: list[str], *, task: dict, policy: dict, registry: dict,
            known_project: bool, now: datetime, pin: str | None, reserve: bool) -> HostPick:
    from tools import host_fill
    needs, project = parse_needs(task.get("description")), task.get("project")
    by_name = {r["host"]: r for r in rows if "host" in r}
    configured = set(registry)
    rejected: dict[str, str] = {}
    alive: list[dict] = []
    cpu_exception: set[str] = set()
    fills: list[str] = []
    for name in names:
        row = by_name.get(name)
        why = ("not in config/hosts.yaml" if name not in configured
               else _reject_reason(name, row, needs, project, known_project, now))
        if not why and name in configured:
            why, used = _cap_reason(name, row, task, policy, pin)
            if used:
                cpu_exception.add(name)
        if row and any(k in _fill_facts(row) for k in _FILL_KEYS):
            pct, highest, _ = host_fill.fill(_fill_facts(row), rounded=False)
            if pct is not None:
                fills.append(f"{name} {pct:.1f}% ({highest})")
        if why:
            rejected[name] = why
        else:
            alive.append(row)

    survivors: list[dict] = []
    if alive:
        try:
            usable, runners_err = role_runners(task), None
        except Exception as e:  # noqa: BLE001
            usable, runners_err = [], f"route error: {type(e).__name__}: {e}"
        for row in alive:
            has = _json_list(row.get("runners")) or []
            if set(has) & set(usable):
                survivors.append(row)
            else:
                rejected[row["host"]] = runners_err or (
                    f"no usable runner (role: {','.join(usable) or 'none ok'}"
                    f" · host: {','.join(has) or 'none'})")

    rej = " ".join(f"{h}({rejected[h]})" for h in names if h in rejected)
    seen = f" · fill: {' · '.join(fills)}" if fills else ""
    if not survivors:
        return HostPick(None, f"no_host: {rej or 'no hosts configured'}{seen}", rejected)

    first = policy.get("first_host", "contabo")

    def rank(r):
        # Contabo first while it passes, then the lowest fill (no reading ranks
        # last: the Windows probe has no loadavg, yet winbox stays pickable),
        # then the fewest running workers, then the most free RAM, then name.
        pct = host_fill.fill(_fill_facts(r), rounded=False)[0]
        ram = r.get("ram_free_gb")
        return (r["host"] != first, float("inf") if pct is None else pct,
                r["running"], -(ram if ram is not None else -1.0), r["host"])

    best = min(survivors, key=rank)
    if best["host"] in cpu_exception:
        try:
            free = _exception_slot(task.get("id"), reserve,
                                   (policy.get("cpu_exception") or {}).get("slot_ttl_s", 600))
            busy = "CPU exception slot busy"
        except Exception as e:  # noqa: BLE001 -- no hub, no proof the slot is free
            free, busy = False, f"CPU exception slot unreadable ({type(e).__name__})"
        if not free:
            rejected[best["host"]] = busy
            rej = " ".join(f"{h}({rejected[h]})" for h in names if h in rejected)
            return HostPick(None, f"no_host: {rej}{seen}", rejected)
    cap = best["max_workers"]
    line = (f"host: {best['host']} · load {_num(best.get('load_per_core'), '.2f')}/core"
            f" · ram {_num(best.get('ram_free_gb'), '.1f')} GB"
            f" · running {best['running']}/{cap}"
            f" · rejected: {rej or 'none'}{seen}"
            + (" · CPU exception" if best["host"] in cpu_exception else ""))
    return HostPick(best["host"], line, rejected)


def _reject_reason(name: str, row: dict | None, needs: list[str],
                   project: str | None, known_project: bool,
                   now: datetime) -> str | None:
    """First of checks 1-4 (module docstring) that `name` fails, or None.
    Checks 5-6 (fill rules, runners) run only for hosts that got this far."""
    if row and row.get("unanswered"):
        return "status offline (no answer to the live probe)"
    why = _probe_problem(row, now)
    if why:
        return why
    status = (row.get("status") or "").strip().lower()
    if status in _NOT_ONLINE:
        return f"status {status}"
    provides = _json_list(row.get("provides")) or []
    lacking = [n for n in needs if n not in provides]
    if lacking:
        return f"provides lacks {', '.join(lacking)}"
    running, cap = row.get("running"), row.get("max_workers")
    if running is None or cap is None:
        return "running/max_workers unknown"
    if running >= cap:
        return f"full {running}/{cap}"
    if not known_project:
        return f"unknown project {project}"
    try:
        config.project_path_for_host(project, name)
    except ValueError:
        return f"no paths.{name} for {project}"
    return None
