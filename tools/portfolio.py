#!/usr/bin/env python3
"""The portfolio registry from the command line (org restructure P3-B, lib/portfolio.py).

    bash scripts/hub/org-python.sh tools/portfolio.py open black-liquidity --name "BLACK LIQUIDITY" --lane cmo
    bash scripts/hub/org-python.sh tools/portfolio.py milestone add black-liquidity "EP7 script locked"
    bash scripts/hub/org-python.sh tools/portfolio.py milestone done black-liquidity 1 --evidence "sha 3b6c6bf7"
    bash scripts/hub/org-python.sh tools/portfolio.py block black-liquidity --on ceo --what "pick the thumbnail"
    bash scripts/hub/org-python.sh tools/portfolio.py show [<id>]
    bash scripts/hub/org-python.sh tools/portfolio.py monitor          # the P3-E v1 JSON the widget reads
    bash scripts/hub/org-python.sh tools/portfolio.py monitor --v 3 --counts   # ph_live=N ph_app=M unlinked=K
    bash scripts/hub/org-python.sh tools/portfolio.py edit black-liquidity --goal "..." --repos a/b,c/d
    bash scripts/hub/org-python.sh tools/portfolio.py edit black-liquidity --kind loop --cadence 24
    bash scripts/hub/org-python.sh tools/portfolio.py replan black-liquidity 1 --due 2026-11-02T00:00:00Z --why "first date"
    bash scripts/hub/org-python.sh tools/portfolio.py --import-status docs/plans/X-STATUS.md \
        --project x --dry-run                                           # a PH STATUS.md table, once
    bash scripts/hub/org-python.sh tools/portfolio.py --import-status docs/plans/X-STATUS.md \
        --project x --reimport [--dry-run]                              # catch an imported project up

Verbs: open, edit, stage, milestone add|done, block, unblock, decided, go add|use, park, close,
lock take|release, show, monitor. Every write appends a project_events row signed with the
caller's identity (`<role>-<session>`, `ceo` for the CEO); `edit` is the exception (no event
kind for it), it prints the old and the new value of each field it changed.

`--import-status` reads a STATUS.md milestone table into a project with no milestones yet, once.
A row is done when its State is `landed` or `done` (any case, with or without Markdown emphasis,
and `done` may be followed by a time or a date) and its Evidence cell is not empty. On a
project that already has milestones the import is refused; `--reimport` then marks done the
milestones that are open in the hub and done in the file, matched by title. It never reopens a
done milestone, never adds one, and `--reimport --dry-run` shows what it would mark (it reads
the hub; the plain `--dry-run` does not).

Who may write comes from tools.agent_transport.current_identity(), never from a flag:
- the CEO and the COO: every project;
- a C-level: projects of its own lane (`open` needs --lane equal to its role);
- a Project Head: its own project only (it is found by ph_session, or by the name in
  state/locks/project_head-<sid>.project); it cannot `open` a project or record a CEO GO,
  because a GO is its spend authority and it may not mint its own;
- a worker or anything else: read-only (show, monitor).

ORG_PORTFOLIO_ENFORCE (lib/org_flags: /etc/org-flags/ORG_PORTFOLIO_ENFORCE, or =1 in the env)
decides what a refusal does. Off, the default: the write goes ahead, one line on stderr says it
would have been refused, and the refusal is appended to state/reports/portfolio-refusals.jsonl.
On: the write is refused, exit 1. Note that a process with no CXO_ROLE / CTO_SESSION_ID /
WORKER_TASK_ID resolves to the CEO (agent_transport.current_identity), so enforcement is only as
strong as that fallback.

Exit: 0 done, 1 refused, 2 bad input or the hub is unreachable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db, org_flags  # noqa: E402
from lib import portfolio as pf  # noqa: E402
from lib.config import is_c_level  # noqa: E402
from lib.db_pg import HubConnectError  # noqa: E402
from tools import agent_transport  # noqa: E402

LOCKS_DIR = agent_transport.LOCKS_DIR
REFUSAL_LOG = ROOT / "state" / "reports" / "portfolio-refusals.jsonl"
PH_ROLE = agent_transport.PH_ROLE
FLAG = "ORG_PORTFOLIO_ENFORCE"
_SID_RE = re.compile(r"[A-Za-z0-9]{1,32}")
REFUSED = object()           # what _write returns for a write the gate stopped


def actor_of(identity) -> str:
    """The name a write is signed with: `project_head-7cf528f0`, `cto-c34459eb`, `ceo`."""
    if identity is None:
        return "unknown"
    return "ceo" if identity.kind == "ceo" else f"{identity.role}-{identity.session_id}"


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").casefold())


def _ph_owns(identity, project: dict, locks_dir: Path) -> bool:
    """A Project Head's own project: the registry names its session, or the name in its
    state/locks/project_head-<sid>.project (written by spawn-ph) is the project's id or name,
    compared without case, spaces or dashes ("OrgRestructure" is org-restructure)."""
    sid = identity.session_id or ""
    if not _SID_RE.fullmatch(sid):
        return False
    if project.get("ph_session") and project["ph_session"] == sid:
        return True
    from tools.send_to_cxo import _trusted_record     # state/locks is group-writable
    record = Path(locks_dir) / f"{PH_ROLE}-{sid}.project"
    try:
        if not _trusted_record(record):
            return False
        name = record.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return bool(_norm(name)) and _norm(name) in {_norm(project["id"]), _norm(project["name"])}


def authorize(identity, verb: str, project: dict | None = None, lane: str | None = None,
              locks_dir: Path | None = None) -> str | None:
    """None when `identity` may do `verb`, else the reason it may not. `project` is the target's
    registry row (None for `open`, and for a lock or GO that names no project); `lane` is the lane
    `open` was asked for."""
    if identity is None:
        return "the caller's identity could not be resolved"
    if identity.kind == "ceo":
        return None
    if identity.kind != "cxo":
        return f"{actor_of(identity)} is read-only: workers cannot write the registry"
    if identity.role == "coo":
        return None
    unowned = project is None and verb in ("lock", "go_add", "go_use", "order_take", "order_link", "order_close")
    if identity.role == PH_ROLE:
        if verb in ("open", "go_add", "order_take", "order_link", "order_close"):
            return "a Project Head cannot open projects, record CEO GOs, or manage orders"
        if unowned and verb != "go_add":
            return None if verb == "lock" else "a Project Head may use only a GO of its own project"
        if project is not None and _ph_owns(identity, project, locks_dir or LOCKS_DIR):
            return None
        return f"{(project or {}).get('id', '?')} is not this Project Head's project"
    if not is_c_level(identity.role):
        return f"{identity.role} may not write the registry"
    if unowned:
        return None
    target = lane if verb == "open" else (project or {}).get("lane")
    if target == identity.role:
        return None
    return f"{identity.role} may write only its own lane's projects, not lane {target!r}"


def _log_refusal(identity, verb: str, project_id: str | None, reason: str, enforced: bool) -> None:
    rec = {"at": pf.iso(datetime.now(timezone.utc)), "actor": actor_of(identity), "verb": verb,
           "project": project_id, "reason": reason, "enforced": enforced}
    try:
        REFUSAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with REFUSAL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass                    # a log that cannot be written never blocks a write


def gate(identity, verb: str, project_id: str | None, reason: str | None) -> bool:
    """True when the write may go ahead. A refusal is logged either way; with the flag off it is
    allowed and one stderr line says it would have been refused."""
    if reason is None:
        return True
    enforced = org_flags.on(FLAG)
    _log_refusal(identity, verb, project_id, reason, enforced)
    if enforced:
        print(f"portfolio: refused: {reason}", file=sys.stderr)
        return False
    print(f"portfolio: would be refused ({FLAG} is off, so it goes ahead): {reason}", file=sys.stderr)
    return True


def parse_when(text: str, now: datetime) -> datetime:
    """`+90m`, `+2h`, `+1d`, or an ISO 8601 time with a zone (`2026-10-15T09:00:00Z`)."""
    m = re.fullmatch(r"\+(\d+)([mhd])", text.strip())
    if m:
        return now + timedelta(**{{"m": "minutes", "h": "hours", "d": "days"}[m.group(2)]: int(m.group(1))})
    try:
        when = datetime.fromisoformat(text.strip())
    except ValueError as e:
        raise pf.PortfolioError(f"bad time {text!r}: use +90m, +2h, +1d or an ISO time with a zone") from e
    if when.tzinfo is None:
        raise pf.PortfolioError(f"bad time {text!r}: it needs a zone (Z or +07:00)")
    return when


def _csv(text: str | None) -> list[str] | None:
    return None if text is None else [x.strip() for x in text.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="portfolio", description=__doc__.split("\n\n")[0])
    p.add_argument("--import-status", metavar="PATH",
                   help="import the milestone table of a PH STATUS.md into --project, once")
    p.add_argument("--project", help="with --import-status: the project to import into")
    p.add_argument("--dry-run", action="store_true", help="with --import-status: parse and print, write nothing")
    p.add_argument("--reimport", action="store_true",
                   help="with --import-status: mark done the open milestones the file shows as done")
    sub = p.add_subparsers(dest="verb")

    s = sub.add_parser("open", help="register a project")
    s.add_argument("id")
    s.add_argument("--name", required=True)
    s.add_argument("--lane", required=True)
    s.add_argument("--stage", default="idea", choices=[x for x in pf.STAGES if x not in pf.TERMINAL])
    s.add_argument("--goal")
    s.add_argument("--done-criteria")
    s.add_argument("--budget-usd", type=float)
    s.add_argument("--host")
    s.add_argument("--owner-session")
    s.add_argument("--ph-session")
    s.add_argument("--repos", help="comma list, e.g. PASAKON/Agents-Core")
    s.add_argument("--relay-accounts", help="comma list of account ids")
    s.add_argument("--hq-row")
    s.add_argument("--kind", choices=("finite", "loop"), default="finite")
    s.add_argument("--due")
    s.add_argument("--cadence", type=int)

    s = sub.add_parser("edit", help="change a project's name, goal, repos, done criteria, host, kind or cadence")
    s.add_argument("id")
    s.add_argument("--name")
    s.add_argument("--goal")
    s.add_argument("--repos", help="comma list; replaces the current list")
    s.add_argument("--done-criteria")
    s.add_argument("--host")
    s.add_argument("--kind", choices=("finite", "loop"), help="a loop needs a cadence (given here or already set)")
    s.add_argument("--cadence", type=int, help="hours between beats of a loop; a positive whole number")

    s = sub.add_parser("tier", help="set a project's budget tier")
    s.add_argument("id")
    s.add_argument("tier", choices=pf.TIERS)
    s.add_argument("--why", required=True)
    s.add_argument("--go")

    s = sub.add_parser("stage", help="move a project to another stage")
    s.add_argument("id")
    s.add_argument("stage", choices=list(pf.STAGES))
    s.add_argument("--reason")

    s = sub.add_parser("milestone", help="add or finish a milestone")
    ms = s.add_subparsers(dest="op", required=True)
    a = ms.add_parser("add")
    a.add_argument("id")
    a.add_argument("title")
    a.add_argument("--n", type=int, help="milestone number (default: next)")
    a.add_argument("--due")
    a.add_argument("--order")
    d = ms.add_parser("done")
    d.add_argument("id")
    d.add_argument("n", type=int)
    d.add_argument("--evidence", required=True, help="sha, Drive id, URL or path")

    s = sub.add_parser("block", help="record what the project waits for")
    s.add_argument("id")
    s.add_argument("--on", required=True, choices=list(pf.BLOCKERS))
    s.add_argument("--what", required=True)
    s.add_argument("--ref")
    s.add_argument("--until")

    s = sub.add_parser("unblock")
    s.add_argument("id")
    s.add_argument("--note")

    s = sub.add_parser("decided", help="log a decision taken for the CEO")
    s.add_argument("id")
    s.add_argument("text")

    s = sub.add_parser("go", help="the CEO's GO register")
    gs = s.add_subparsers(dest="op", required=True)
    a = gs.add_parser("add")
    a.add_argument("--words", required=True, help="the CEO's words, verbatim")
    a.add_argument("--source", required=True, help="run:Q-..., run:RUN-... or chat:<session>")
    a.add_argument("--action", required=True)
    a.add_argument("--id")
    a.add_argument("--project")
    a.add_argument("--max-usd", type=float)
    a.add_argument("--expires-at")
    u = gs.add_parser("use")
    u.add_argument("go_id")
    u.add_argument("--used-by")

    s = sub.add_parser("park")
    s.add_argument("id")
    s.add_argument("--reason")

    s = sub.add_parser("close")
    s.add_argument("id")
    s.add_argument("--outcome", required=True)
    s.add_argument("--learning", required=True)

    s = sub.add_parser("lock", help="a shared resource: a browser home, a render slot")
    ls = s.add_subparsers(dest="op", required=True)
    t = ls.add_parser("take")
    t.add_argument("resource")
    t.add_argument("--until", required=True, help="+90m, +2h, +1d or an ISO time with a zone")
    t.add_argument("--project")
    r = ls.add_parser("release")
    r.add_argument("resource")

    s = sub.add_parser("show", help="one project in full, or every project in brief")
    s.add_argument("id", nargs="?")
    s = sub.add_parser("monitor", help="print the monitor JSON")
    s.add_argument("--v", type=int, choices=(1, 2, 3), default=1)
    s.add_argument("--counts", action="store_true",
                   help="with --v 3: print only ph_live=N ph_app=M unlinked=K (no ids, no names)")
    s = sub.add_parser("report")
    s.add_argument("--json", action="store_true")
    sub.add_parser("eta-stats")
    s = sub.add_parser("replan")
    s.add_argument("id")
    s.add_argument("n", type=int)
    s.add_argument("--due", required=True)
    s.add_argument("--why", required=True)
    s = sub.add_parser("beat")
    s.add_argument("id")
    s.add_argument("--evidence", required=True)
    s = sub.add_parser("plan")
    s.add_argument("id")
    s.add_argument("--next", required=True)
    s.add_argument("--owner", required=True)
    s = sub.add_parser("order")
    orders = s.add_subparsers(dest="op", required=True)
    s = orders.add_parser("take")
    s.add_argument("words")
    s.add_argument("--project")
    s.add_argument("--due")
    s.add_argument("--channel")
    s = orders.add_parser("link")
    s.add_argument("order_id")
    s.add_argument("project")
    s.add_argument("--due")
    s = orders.add_parser("close")
    s.add_argument("order_id")
    s.add_argument("--outcome", required=True)
    return p


def _out(obj) -> None:
    print(json.dumps(pf._jsonable(obj), ensure_ascii=False))


def _identity():
    try:
        return agent_transport.current_identity()
    except PermissionError as e:
        print(f"portfolio: {e}", file=sys.stderr)
        return None


def _import_status(args, identity, now: datetime) -> int:
    path = Path(args.import_status)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise pf.PortfolioError(f"cannot read {path}: {e.strerror}") from e
    rows = pf.parse_status_milestones(text)
    if args.dry_run and not args.reimport:
        _out({"dry_run": True, "project": args.project, "source": path.name, "total": len(rows),
              "done": sum(r["done"] for r in rows),
              "done_state_without_evidence": sum(r["state_done"] and not r["done"] for r in rows),
              "milestones": [{"n": n, "title": r["title"], "done": r["done"], "evidence": r["evidence"]}
                             for n, r in enumerate(rows, 1)]})
        return 0
    if not args.project:
        raise pf.PortfolioError("--import-status needs --project <id>")
    if args.reimport:
        project = pf.get_project(args.project)
        if not args.dry_run and not gate(identity, "reimport", args.project, authorize(identity, "reimport", project)):
            return 1
        _out(pf.reimport_milestones(args.project, rows, actor=actor_of(identity), source=path.name,
                                    dry_run=args.dry_run, now=now))
        return 0
    project = pf.get_project(args.project)
    if not gate(identity, "import", args.project, authorize(identity, "import", project)):
        return 1
    _out(pf.import_milestones(args.project, rows, actor=actor_of(identity), source=path.name, now=now))
    return 0


def _write(args, identity, now: datetime):
    """Run one write verb; its result, or REFUSED when the gate stopped it."""
    actor, v = actor_of(identity), args.verb
    due_set_by = "ceo" if identity and identity.kind == "ceo" else "ph" if identity and identity.role == PH_ROLE else "clevel"

    def ok(verb: str, project: dict | None = None, project_id: str | None = None, lane: str | None = None):
        return gate(identity, verb, project_id or (project or {}).get("id"),
                    authorize(identity, verb, project, lane))

    if v == "open":
        if not ok("open", project_id=args.id, lane=args.lane):
            return REFUSED
        return pf.open_project(args.id, args.name, args.lane, actor=actor, stage=args.stage,
                               owner_session=args.owner_session, ph_session=args.ph_session, host=args.host,
                               repos=_csv(args.repos), goal=args.goal, done_criteria=args.done_criteria,
                               budget_usd=args.budget_usd, relay_accounts=_csv(args.relay_accounts),
                               hq_row=args.hq_row, now=now, kind=args.kind,
                               due_at=parse_when(args.due, now) if args.due else None,
                               due_set_by=due_set_by if args.due else None, cadence_h=args.cadence)
    if v == "order":
        pid = getattr(args, "project", None)
        if args.op != "take":
            with pf._tx() as c:
                existing = pf._order(c, args.order_id)
            old_pid = existing["project_id"]
            if old_pid and not ok("order_" + args.op, pf.get_project(old_pid)):
                return REFUSED
            pid = pid or old_pid
        if not ok("order_" + args.op, pf.get_project(pid) if pid else None):
            return REFUSED
        due = parse_when(args.due, now) if getattr(args, "due", None) else None
        if args.op == "take":
            channel = args.channel or "chat:" + (actor if actor != "ceo" else "ceo-direct")
            return {"id": pf.order_take(args.words, channel, actor=actor, project_id=pid,
                                       due_at=due, due_set_by=due_set_by if due else None, now=now)}
        if args.op == "link":
            return pf.order_link(args.order_id, args.project, actor=actor, due_at=due, now=now)
        return pf.order_close(args.order_id, args.outcome, actor=actor, now=now)
    if v == "go":
        if args.op == "add":
            project = pf.get_project(args.project) if args.project else None
            if not ok("go_add", project):
                return REFUSED
            expires = parse_when(args.expires_at, now) if args.expires_at else None
            return pf.go_add(args.words, args.source, args.action, actor=actor, go_id=args.id,
                             project_id=args.project, max_usd=args.max_usd, expires_at=expires, now=now)
        pid = pf.go_project(args.go_id)
        if not ok("go_use", pf.get_project(pid) if pid else None, project_id=pid):
            return REFUSED
        return pf.go_use(args.go_id, actor=actor, used_by=args.used_by, now=now)
    if v == "lock":
        project = pf.get_project(args.project) if args.op == "take" and args.project else None
        if not ok("lock", project, project_id=getattr(args, "project", None)):
            return REFUSED
        if args.op == "take":
            return pf.lock_take(args.resource, parse_when(args.until, now), holder=actor,
                                project_id=args.project, now=now)
        force = identity is not None and (identity.kind == "ceo" or identity.role == "coo")
        return {"resource": args.resource, "released": pf.lock_release(args.resource, holder=actor, force=force)}

    if v == "edit":                                  # bad input is refused before the hub is asked anything
        pf.edit_fields(name=args.name, goal=args.goal, repos=_csv(args.repos),
                       done_criteria=args.done_criteria, host=args.host, kind=args.kind, cadence_h=args.cadence)
    project = pf.get_project(args.id)
    if not ok(v, project):
        return REFUSED
    if v == "replan":
        role = "ceo" if identity and identity.kind == "ceo" else getattr(identity, "role", "unknown")
        return pf.replan(args.id, args.n, parse_when(args.due, now), actor=actor,
                         actor_role=role, why=args.why, now=now)
    if v == "beat":
        return pf.beat(args.id, args.evidence, actor=actor, now=now)
    if v == "plan":
        return pf.set_plan(args.id, next_step=args.next, next_owner=args.owner, actor=actor, now=now)
    if v == "edit":
        return pf.edit_project(args.id, actor=actor, name=args.name, goal=args.goal, repos=_csv(args.repos),
                               done_criteria=args.done_criteria, host=args.host, kind=args.kind,
                               cadence_h=args.cadence)
    if v == "stage":
        return pf.set_stage(args.id, args.stage, actor=actor, reason=args.reason, now=now)
    if v == "tier":
        return pf.set_tier(args.id, args.tier, actor=actor, why=args.why, go=args.go, now=now)
    if v == "milestone":
        if args.op == "add":
            return {"project": args.id, "n": pf.milestone_add(args.id, args.title, actor=actor, n=args.n, now=now,
                    due_at=parse_when(args.due, now) if args.due else None, order_id=args.order)}
        return pf.milestone_done(args.id, args.n, args.evidence, actor=actor, now=now)
    if v == "block":
        return pf.block(args.id, args.on, args.what, actor=actor, now=now, ref=args.ref,
                        until=parse_when(args.until, now) if args.until else None)
    if v == "unblock":
        return pf.unblock(args.id, actor=actor, note=args.note, now=now)
    if v == "decided":
        return pf.decided(args.id, args.text, actor=actor, now=now)
    if v == "park":
        return pf.park(args.id, actor=actor, reason=args.reason, now=now)
    return pf.close(args.id, args.outcome, args.learning, actor=actor, now=now)     # close


def run(argv: list[str], *, identity=None, now: datetime | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    now = now or datetime.now(timezone.utc)
    try:
        if args.verb is None and not args.import_status:
            parser.print_usage(sys.stderr)
            return 2
        if args.reimport and not args.import_status:
            raise pf.PortfolioError("--reimport goes with --import-status <file> --project <id>")
        if args.verb == "monitor":
            if args.counts and args.v != 3:
                raise pf.PortfolioError("--counts goes with --v 3")
            payload = pf.monitor_payload(now, version=args.v)
            if args.counts:
                print("ph_live={ph_live} ph_app={ph_app} unlinked={unlinked}".format(**pf.v3_counts(payload)))
            else:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.verb == "report":
            rows = pf.report(now)
            if args.json:
                _out(rows)
            else:
                print(pf.render_report(rows))
                for p in pf.idea_with_live_ph(now):      # stage idea is outside the monitor: say it here
                    print(f"idea · {p['name']} ({p['project_id']}) · PH {p['ph_session']} live: set stage or park")
            return 0
        if args.verb == "eta-stats":
            _out(pf.eta_stats())
            return 0
        if args.verb == "show":
            _out(pf.show(args.id, now=now))
            return 0
        identity = identity or _identity()
        if args.import_status:
            return _import_status(args, identity, now)
        result = _write(args, identity, now)
        if result is REFUSED:
            return 1
        _out(result)
        return 0
    except PermissionError as e:
        print(f"portfolio: refused: {e}", file=sys.stderr)
        return 1
    except (pf.PortfolioError, HubConnectError, db.HubUnavailable) as e:
        print(f"portfolio: {e}", file=sys.stderr)
        return 2


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
