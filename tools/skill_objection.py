#!/usr/bin/env python3
"""tools/skill_objection.py — CEO rule 8 / ADR 0022 §6.

A worker that hits a conflict using a skill it did not write reports back to
the skill's author. One `events` row (db.log_event, kind="skill_objection")
+ one LungNote to-do addressed to the resolved author. No `resolve` verb —
completing the to-do IS the resolution (ADR 0017: a human runs that verb).
No author-liveness ladder / tmux delivery / mailbox / severity rank — cut
per playbook Wave 4: most objections route to CTO regardless.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db  # noqa: E402
from tools import agent_transport  # noqa: E402

_CURATOR_PATH = ROOT / "scripts" / "skill-curator.py"
_REPORT_PATH = ROOT / "scripts" / "skill-report.py"


def _load(module_name: str, path: Path):
    """Dynamic import of a hyphenated-filename script — same trick
    scripts/skill-curator.py itself uses to reuse scripts/skill-report.py."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _skill_dir(name: str) -> Path | None:
    """SKILL.md dir for `name` — reuses skill-report.py's `_skill_locations()`
    (owned / user / plugin) and additionally checks the archive dir, which
    skill-report.py deliberately does not scan (it reports the *visible*
    portfolio; an objection may still target a just-archived skill)."""
    loc = _load("_skill_report", _REPORT_PATH)._skill_locations().get(name)
    if loc is not None:
        return loc
    cand = ROOT / ".claude" / "skills-archive" / name
    return cand if (cand / "SKILL.md").is_file() else None


def resolve_author(skill: str) -> str:
    """`author.role` from frontmatter, else "cto" (lazy-backfill default,
    ADR 0022 §6 — routes exactly where objections already went)."""
    skill_dir = _skill_dir(skill)
    fm = _load("_skill_curator", _CURATOR_PATH)._read_frontmatter(skill_dir) if skill_dir else {}
    author = fm.get("author")
    role = author.get("role") if isinstance(author, dict) else None
    return role.strip() if isinstance(role, str) and role.strip() else "cto"


def _add_lungnote_todo(text: str) -> None:
    """Fail-open: a durable DB event already exists by the time this runs,
    so a LungNote outage must never raise (matches request_human_handoff)."""
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "lib" / "mcp_call.py"),
             "--server", "lungnote", "--root", str(ROOT),
             "--tool", "add_todo", "--args", json.dumps({"text": text})],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        pass


def raise_objection(skill: str, conflict: str, did_instead: str, blocked: bool = False) -> dict:
    """Write one skill_objection event + one LungNote to-do. Returns the
    logged payload (includes "author")."""
    author = resolve_author(skill)
    identity = agent_transport.current_identity()
    actor = f"{identity.role}/{identity.session_id or '-'}"
    payload = {"skill": skill, "conflict": conflict, "did_instead": did_instead,
               "blocked": bool(blocked), "author": author, "raised_by": actor}
    with db.get_conn() as conn:
        db.log_event(conn, os.environ.get("WORKER_TASK_ID") or None, actor,
                     "skill_objection", payload)
    _add_lungnote_todo(f"[skill objection -> {author}] {skill}: {conflict}"
                        + (" (BLOCKED)" if blocked else ""))
    return payload


def list_objections(limit: int = 50) -> list[dict]:
    """Most recent skill_objection events, newest first."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, ts, actor, payload FROM events WHERE kind='skill_objection' "
            "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        try:
            payload = json.loads(r["payload"] or "{}")
        except ValueError:
            payload = {}
        out.append({"id": r["id"], "ts": r["ts"], "actor": r["actor"], **payload})
    return out


def summary(days: int = 30) -> dict[str, dict]:
    """Per-skill count + last conflict text, feeding skill-report.py's `obj`
    column. No resolve verb (§6) means no signal distinguishes a resolved
    objection from an open one, so `open` == `total` by construction — kept
    as two numbers so a future LungNote-side join can narrow `open` later
    without reshaping this return."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: dict[str, dict] = {}
    # list_objections() is newest-first, so the FIRST row seen per skill is
    # its most recent — setdefault seeds last_conflict from that row and
    # never overwrites it on later (older) rows for the same skill.
    for row in list_objections(limit=100000):
        try:
            ts = datetime.fromisoformat(row["ts"])
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < cutoff or not row.get("skill"):
            continue
        rec = out.setdefault(row["skill"],
                             {"open": 0, "total": 0, "last_conflict": row.get("conflict", "")})
        rec["open"] += 1
        rec["total"] += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="skill_objection.py")
    sub = ap.add_subparsers(dest="verb", required=True)
    p_raise = sub.add_parser("raise")
    for a in ("skill", "conflict", "did_instead"):
        p_raise.add_argument(a)
    p_raise.add_argument("--blocked", action="store_true")
    sub.add_parser("list").add_argument("--limit", type=int, default=50)
    sub.add_parser("summary").add_argument("--days", type=int, default=30)
    args = ap.parse_args(argv)

    if args.verb == "raise":
        print(json.dumps(raise_objection(args.skill, args.conflict, args.did_instead,
                                          args.blocked), indent=2))
    elif args.verb == "list":
        for row in list_objections(args.limit):
            print(f"{row['id']}  {row['ts']}  {row.get('skill')}  -> {row.get('author')}"
                  f"  {row.get('conflict', '')}")
    elif args.verb == "summary":
        for skill, rec in sorted(summary(args.days).items()):
            print(f"{skill}  open={rec['open']} total={rec['total']}  "
                  f"last: {rec['last_conflict'][:80]}")
    return 0


if __name__ == "__main__":
    db.init()
    raise SystemExit(main())
