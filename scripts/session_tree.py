#!/usr/bin/env python3
"""
session_tree.py — render a live work-breakdown tree from the org task DB.

Reads state/tasks.db READ-ONLY and emits a Mermaid flowchart grouping tasks by
project, coloured by status, with depends_on drawn as edges. Optionally renders
to PNG via the mermaid-cli (npx).

The DB is flat today (parent_task is unused, most sessions hold one task), so the
tree is 2 levels: project (root) -> task nodes. When create_task starts setting
parent_task, nest_by_parent() will deepen it automatically.

Usage:
    python scripts/session_tree.py                 # active + recently-done, all projects
    python scripts/session_tree.py --status all    # every task (can be a big blob)
    python scripts/session_tree.py --project mooniex-webapp --days 7
    python scripts/session_tree.py --render        # also produce the PNG
    python scripts/session_tree.py --out /tmp/x.mmd --render
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import db as db_lib  # noqa: E402

# status -> (mermaid class, human bucket)
STATUS_CLASS = {
    "done": "done",
    "merged": "done",
    "review": "wip",
    "in_progress": "wip",
    "rate_limited": "wip",
    "conflict": "wip",
    "pending": "todo",
    "failed": "fail",
    "dropped": "fail",
    "cancelled": "cancel",
}
ACTIVE = {"pending", "review", "in_progress", "rate_limited", "conflict", "failed"}

CLASSDEFS = [
    "classDef done   fill:#15803d,color:#fff,stroke:#166534,stroke-width:1px;",
    "classDef wip    fill:#b45309,color:#fff,stroke:#92400e,stroke-width:2px;",
    "classDef todo   fill:#334155,color:#cbd5e1,stroke:#475569,stroke-width:1px;",
    "classDef fail   fill:#b91c1c,color:#fff,stroke:#7f1d1d,stroke-width:2px;",
    "classDef cancel fill:#1e293b,color:#64748b,stroke:#334155,stroke-width:1px;",
    "classDef proj   fill:#0f172a,color:#fff,stroke:#64748b,stroke-width:3px;",
]




def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:  # some rows store naive timestamps — assume UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fetch_tasks(conn, status_mode: str, days: int, project: str | None,
                session: str | None) -> list[sqlite3.Row]:
    rows = conn.execute(
        "SELECT id, project, role, status, title, depends_on, "
        "created_at, updated_at, session_id FROM tasks"
    ).fetchall()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for r in rows:
        if project and r["project"] != project:
            continue
        if session and r["session_id"] != session:
            continue
        st = r["status"]
        if status_mode == "all":
            keep = True
        elif status_mode == "terminal":
            keep = st in {"done", "merged", "cancelled", "dropped", "failed"}
        else:  # active (default): live tasks + recently-finished
            if st in ACTIVE:
                keep = True
            elif st in {"done", "merged"}:
                ts = _parse_ts(r["updated_at"]) or _parse_ts(r["created_at"])
                keep = bool(ts and ts >= cutoff)
            else:
                keep = False
        if keep:
            out.append(r)
    return out


def _nid(task_id: str) -> str:
    """Mermaid-safe node id from a task id."""
    return "n" + re.sub(r"[^0-9a-zA-Z]", "", task_id)


def _label(text: str, limit: int = 40) -> str:
    """Sanitise a string for a Mermaid quoted label."""
    text = (text or "").strip().replace("\n", " ")
    text = text.replace('"', "'").replace("[", "(").replace("]", ")")
    text = text.replace("|", "/").replace("{", "(").replace("}", ")")
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def build_mermaid(tasks: list[sqlite3.Row], title_note: str) -> str:
    if not tasks:
        return 'flowchart LR\n  empty["no tasks match filter"]:::todo\n' + "\n".join(CLASSDEFS)

    by_project: dict[str, list[sqlite3.Row]] = {}
    for t in tasks:
        by_project.setdefault(t["project"], []).append(t)

    node_ids = {t["id"] for t in tasks}
    lines = ["flowchart LR"]
    lines.append(f'  %% {title_note}')

    # status order within a project: wip, fail, pending, done, cancel
    order = {"wip": 0, "fail": 1, "todo": 2, "done": 3, "cancel": 4}
    for proj in sorted(by_project):
        rows = sorted(
            by_project[proj],
            key=lambda r: order.get(STATUS_CLASS.get(r["status"], "todo"), 9),
        )
        pid = "sg_" + re.sub(r"[^0-9a-zA-Z]", "", proj)
        lines.append(f'  subgraph {pid} ["{_label(proj, 32)}  ·  {len(rows)}"]')
        lines.append("    direction TB")
        for r in rows:
            cls = STATUS_CLASS.get(r["status"], "todo")
            short = r["id"].replace("task-", "")
            label = f'{_label(r["title"], 38)}<br/>{short} · {r["status"]}'
            lines.append(f'    {_nid(r["id"])}["{label}"]:::{cls}')
        lines.append("  end")

    # depends_on edges (only within the filtered set)
    edge_lines = []
    for t in tasks:
        try:
            deps = json.loads(t["depends_on"] or "[]")
        except (json.JSONDecodeError, TypeError):
            deps = []
        for dep in deps:
            if dep in node_ids:
                edge_lines.append(f'  {_nid(dep)} -.->|blocks| {_nid(t["id"])}')
    if edge_lines:
        lines.append("  %% depends_on edges")
        lines.extend(edge_lines)

    lines.extend("  " + c for c in CLASSDEFS)
    return "\n".join(lines)


# ASCII / ANSI output — CTO chat is a terminal REPL, so a coloured text tree is
# what the human actually sees (no inline image rendering in iTerm2).
ANSI = {"done": "32", "wip": "33", "todo": "34", "fail": "31", "cancel": "90"}
GLYPH = {"done": "✓", "wip": "◔", "todo": "○", "fail": "✗", "cancel": "·"}


def build_ascii(tasks: list[sqlite3.Row], title_note: str, color: bool = True) -> str:
    def paint(code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    if not tasks:
        return f"(no tasks match filter)\n{title_note}"

    by_project: dict[str, list[sqlite3.Row]] = {}
    for t in tasks:
        by_project.setdefault(t["project"], []).append(t)

    order = {"wip": 0, "fail": 1, "todo": 2, "done": 3, "cancel": 4}
    lines = [paint("1", f"WORK TREE · {title_note}")]
    projects = sorted(by_project)
    for pi, proj in enumerate(projects):
        rows = sorted(by_project[proj],
                      key=lambda r: order.get(STATUS_CLASS.get(r["status"], "todo"), 9))
        p_last = pi == len(projects) - 1
        lines.append(f"{'└─' if p_last else '├─'} {paint('1', proj)} · {len(rows)}")
        pipe = "   " if p_last else "│  "
        for ri, r in enumerate(rows):
            cls = STATUS_CLASS.get(r["status"], "todo")
            r_last = ri == len(rows) - 1
            short = r["id"].replace("task-", "")
            title = (r["title"] or "").replace("\n", " ")[:46]
            node = paint(ANSI.get(cls, "0"),
                         f"{GLYPH.get(cls, '○')} {title} · {r['status']}")
            lines.append(f"{pipe}{'└─' if r_last else '├─'} {node}  {paint('90', short)}")
    legend = "  ".join(paint(ANSI[k], f"{GLYPH[k]} {k}")
                        for k in ("done", "wip", "todo", "fail", "cancel"))
    lines += ["", f"legend: {legend}"]
    return "\n".join(lines)


def render_png(mmd_path: Path, png_path: Path) -> bool:
    try:
        subprocess.run(
            ["npx", "-y", "@mermaid-js/mermaid-cli", "-i", str(mmd_path),
             "-o", str(png_path), "-t", "dark", "-b", "#0b1220", "-s", "2"],
            check=True, capture_output=True, text=True, timeout=300,
        )
        return png_path.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[render] failed: {e}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Mermaid work-breakdown tree from tasks.db")
    ap.add_argument("--status", choices=["active", "all", "terminal"], default="active",
                    help="active (default): live + recently-done; all; terminal")
    ap.add_argument("--days", type=int, default=3,
                    help="recent-done window in days (active mode), default 3")
    ap.add_argument("--project", help="filter to one project key")
    ap.add_argument("--session", help="filter to one session_id")
    ap.add_argument("--out", type=Path, default=Path("/tmp/session_tree.mmd"))
    ap.add_argument("--mermaid", action="store_true",
                    help="emit a Mermaid .mmd file instead of the default ASCII tree")
    ap.add_argument("--render", action="store_true",
                    help="render the Mermaid to PNG via npx mmdc (implies --mermaid)")
    ap.add_argument("--no-open", action="store_true", help="do not auto-open the PNG")
    ap.add_argument("--no-color", action="store_true", help="plain ASCII, no ANSI colour")
    args = ap.parse_args()

    if not db_lib.pg_url() and not db_lib.DB_PATH.exists():
        print(f"tasks.db not found at {db_lib.DB_PATH}", file=sys.stderr)
        return 1

    with db_lib.get_conn(readonly=True, timeout=10) as conn:
        tasks = fetch_tasks(conn, args.status, args.days, args.project, args.session)

    note = (f"status={args.status} days={args.days} "
            f"project={args.project or 'all'} -> {len(tasks)} tasks")

    if args.render or args.mermaid:
        mmd = build_mermaid(tasks, note)
        args.out.write_text(mmd, encoding="utf-8")
        print(f"[mmd] {len(tasks)} tasks -> {args.out}")
        if args.render:
            png = args.out.with_suffix(".png")
            if render_png(args.out, png):
                print(f"[png] {png}")
                if not args.no_open and sys.platform == "darwin":
                    subprocess.run(["open", str(png)], check=False)
            else:
                return 2
    else:
        # default: coloured ASCII tree straight to the terminal (what CEO sees)
        print(build_ascii(tasks, note, color=not args.no_color))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
