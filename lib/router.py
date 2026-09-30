"""Host router (PLAN-auto-dispatch H2, Org Mesh W2.6): pick the machine for a task.

    pick_host(task) -> HostPick

WHICH runner a task uses is tools/route.py's job (CTO #24ca1c0a's lane). This
module answers WHERE. It is called from tools/delegate.py's host-resolution
block only when the task names no host of its own, and only when the env flag
ORG_HOST_ROUTER is on (default OFF -- with it off, nothing in here runs and
delegate keeps today's `host= arg > tasks.host > self_host()`).

A host is a candidate only if ALL of these hold (each rejection gets exactly one
reason, the first check that failed, and the reasons go to delegate_log):

  1. a probe no older than 60 s is in the `hosts` table (tools/node_dispatch.py
     `probe` writes it) and `status` is not offline / pending_identity / left
  2. `provides` contains every name in the task's `needs: a, b` description line
  3. `running < max_workers`
  4. the project has `paths.<host>` in config/projects.yaml
  5. at least one runner the role can use is installed on the host
     (`hosts.runners`, from the probe)

Survivors are ranked by lowest `load_per_core`, then most `ram_free_gb`, then
name. No survivor -> HostPick.host is None and `line` is `no_host: ...`; the
caller leaves the task pending and does not spawn. There is no fallback host:
a stale or missing probe means "unknown", and unknown is never "fine".

`needs` has no column (lib/db.py is locked to other tasks); it is read from a
description line, the same way route.check_override reads `override:`.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from lib import config, db

ENV_FLAG = "ORG_HOST_ROUTER"
PROBE_MAX_AGE_S = 60
# A probe stamped slightly in the future is a clock difference between boxes,
# not a fresher probe. Beyond this it is treated as unreadable, never as fresh.
PROBE_FUTURE_SKEW_S = 10
_NOT_ONLINE = ("offline", "pending_identity", "left")

_NEEDS_RE = re.compile(r"^[ \t]*needs:[ \t]*(.*)$", re.IGNORECASE | re.MULTILINE)


def enabled() -> bool:
    """ORG_HOST_ROUTER is 1/true/on. Default off (same switch shape as
    lib.mesh.enabled)."""
    return os.environ.get(ENV_FLAG, "").strip().lower() in ("1", "true", "on")


@dataclass
class HostPick:
    host: str | None            # None = no host fits; the task stays pending
    line: str                   # the one delegate_log line for this decision
    rejected: dict[str, str] = field(default_factory=dict)


def parse_needs(description: str | None) -> list[str]:
    """Names from every `needs: a, b` line of a task description. Lowercased,
    de-duplicated, in order. No such line (or an empty one) = no constraint."""
    out: list[str] = []
    for m in _NEEDS_RE.finditer(description or ""):
        for name in m.group(1).split(","):
            name = name.strip().lower()
            if name and name not in out:
                out.append(name)
    return out


def add_needs_line(description: str, needs: str | None) -> str:
    """`description` plus a `needs: a, b` line, for create_task(needs=...).

    `needs` is a JSON array string or comma-separated names, the two shapes
    create_task already takes for `touches`. Empty leaves the text unchanged.
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
    return f"{description.rstrip()}\nneeds: {line}" if description.strip() else f"needs: {line}"


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


def pick_host(task: dict, *, hosts_rows: list[dict] | None = None,
              now: datetime | None = None) -> HostPick:
    """Choose a host for `task` (a tasks row), or say why none fits.

    `hosts_rows` (default: the `hosts` table) and `now` exist for tests.
    Never raises on bad data: an unreadable table or router error is a
    rejection of every host, with the error as the reason.
    """
    now = now or datetime.now(timezone.utc)
    needs = parse_needs(task.get("description"))
    project = task.get("project")
    try:
        rows = db.list_hosts() if hosts_rows is None else hosts_rows
        by_name = {r["host"]: r for r in rows}
        configured = set(config.hosts())
        names = sorted(configured | set(by_name))
        known_project = project in config.projects()
    except Exception as e:  # noqa: BLE001 -- see docstring
        return HostPick(None, f"no_host: router error: {type(e).__name__}: {e}")

    rejected: dict[str, str] = {}
    alive: list[dict] = []
    for name in names:
        row = by_name.get(name)
        why = ("not in config/hosts.yaml" if name not in configured
               else _reject_reason(name, row, needs, project, known_project, now))
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
    if not survivors:
        return HostPick(None, f"no_host: {rej or 'no hosts configured'}", rejected)

    best = min(survivors, key=lambda r: (
        r["load_per_core"],
        -(r["ram_free_gb"] if r.get("ram_free_gb") is not None else -1.0),
        r["host"]))
    line = (f"host: {best['host']} · load {_num(best['load_per_core'], '.2f')}/core"
            f" · ram {_num(best.get('ram_free_gb'), '.1f')} GB"
            f" · running {best['running']}/{best['max_workers']}"
            f" · rejected: {rej or 'none'}")
    return HostPick(best["host"], line, rejected)


def _reject_reason(name: str, row: dict | None, needs: list[str],
                   project: str | None, known_project: bool,
                   now: datetime) -> str | None:
    """First of checks 1-4 (module docstring) that `name` fails, or None.
    Check 5 (runners) needs route and runs only for hosts that got this far."""
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
    if row.get("load_per_core") is None:
        return "no load_per_core reading"
    return None
