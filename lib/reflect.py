"""Reflection: a read-only digest of recent org activity.

Lets the CTO open a session knowing where things stand — what merged, what's
open or stuck, and any recurring failure signal — without trawling the event
log by hand. Read-side counterpart to recall(): recall answers "what did we do
about X", reflect answers "what's the state of the org right now".

Corrigible by design: it surfaces candidate patterns for a human to act on; it
does NOT auto-write rules or mutate any memory.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from . import db
from .recall import _outcome

# Task statuses that represent unfinished or troubled work worth flagging.
_OPEN_CONCERN = ("failed", "blocked_human", "conflict", "stalled", "rate_limited")
# Event kinds that signal something went wrong.
_FAILURE_KINDS = {
    "status_failed", "status_conflict", "status_stalled",
    "status_blocked_human", "status_rate_limited",
}


def reflect(days: int = 7, project: str | None = None) -> dict:
    """Aggregate org activity over the last `days`. Read-only."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(
        timespec="seconds")
    with db.get_conn() as conn:
        tq = ("SELECT id,project,role,status,title,report,review,branch,"
              "updated_at FROM tasks WHERE updated_at>=?")
        targs: list = [since]
        if project:
            tq += " AND project=?"
            targs.append(project)
        tasks = [dict(r) for r in conn.execute(tq, targs).fetchall()]
        eq = "SELECT kind FROM events WHERE ts>=?"
        eargs: list = [since]
        if project:
            eq = ("SELECT e.kind FROM events e JOIN tasks t ON e.task_id=t.id "
                  "WHERE e.ts>=? AND t.project=?")
            eargs.append(project)
        fail_kinds = Counter(
            r["kind"] for r in conn.execute(eq, eargs).fetchall()
            if r["kind"] in _FAILURE_KINDS
        )

    tasks.sort(key=lambda t: t.get("updated_at") or "", reverse=True)
    merged = [t for t in tasks if t["status"] in ("done", "merged")]
    concerns = [t for t in tasks if t["status"] in _OPEN_CONCERN]
    return {
        "window_days": days,
        "since": since[:10],
        "tasks_touched": len(tasks),
        "by_project": dict(Counter(t["project"] for t in tasks)),
        "merged": [
            {"task_id": t["id"], "project": t["project"], "title": t["title"],
             "outcome": _outcome(t)}
            for t in merged[:10]
        ],
        "concerns": [
            {"task_id": t["id"], "project": t["project"], "status": t["status"],
             "title": t["title"]}
            for t in concerns[:10]
        ],
        "recurring_failures": dict(fail_kinds),
    }


def reflect_text(days: int = 7, project: str | None = None) -> str:
    d = reflect(days=days, project=project)
    scope = f" [{project}]" if project else ""
    lines = [
        f"org reflect{scope} — last {d['window_days']}d (since {d['since']}): "
        f"{d['tasks_touched']} tasks touched"
    ]
    if d["by_project"]:
        lines.append("  by project: " + ", ".join(
            f"{k}={v}" for k, v in sorted(d["by_project"].items())))
    if d["merged"]:
        lines.append(f"  merged ({len(d['merged'])}):")
        for m in d["merged"]:
            lines.append(f"    - {m['task_id']} [{m['project']}] {m['title']} → {m['outcome']}")
    if d["concerns"]:
        lines.append(f"  open concerns ({len(d['concerns'])}):")
        for c in d["concerns"]:
            lines.append(f"    - {c['task_id']} [{c['project']}] {c['status']} — {c['title']}")
    lines.append("  recurring failures: " + (
        ", ".join(f"{k}={v}" for k, v in d["recurring_failures"].items())
        if d["recurring_failures"] else "none"))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 7
    print(reflect_text(days=days))
