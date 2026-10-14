"""Record reviewed runner outcomes in the hub event stream."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db
from tools.forecast import infer_size
from tools.quota import load_plans

KIND = "runner_fit"
SCHEMA = 1
RESULTS = ("pass", "redo", "fail")
FAIL_REASONS = ("limit", "no-shell", "wrong", "crash", "timeout", "scope", "other")
JOB_TYPES = ("code", "tests", "fix", "docs", "skill", "review", "browse", "decision", "research", "media", "other")


def build(**f):
    if "first_pass" in f:
        raise ValueError("first_pass is computed")
    p = dict(schema=SCHEMA, model=None, bucket=None, size=None, fail_reason=None,
             why="", minutes=None, iteration=0, reviewer_fix=False, pct_done=None,
             source="manual", reviewer=None)
    p.update(f)
    if not isinstance(p.get("runner"), str) or not p["runner"].strip():
        raise ValueError("runner is required")
    p["runner"] = p["runner"].strip().lower()
    for key, allowed in (("schema", (SCHEMA,)), ("job_type", JOB_TYPES),
                         ("result", RESULTS), ("size", (None, "S", "M", "L")),
                         ("source", ("delegate", "manual"))):
        if p.get(key) not in allowed:
            raise ValueError(f"invalid {key}")
    if p["result"] == "fail":
        if p["fail_reason"] not in FAIL_REASONS:
            raise ValueError("fail requires a valid fail_reason")
    else:
        p["fail_reason"] = None
    for key in ("model", "bucket", "reviewer"):
        if p[key] is not None and not isinstance(p[key], str):
            raise ValueError(f"{key} must be a string or None")
    if not isinstance(p["why"], str):
        raise ValueError("why must be a string")
    if type(p["iteration"]) is not int or p["iteration"] < 0:
        raise ValueError("iteration must be a nonnegative integer")
    if type(p["reviewer_fix"]) is not bool:
        raise ValueError("reviewer_fix must be a bool")
    if p["pct_done"] is not None and (type(p["pct_done"]) is not int or not 0 <= p["pct_done"] <= 100):
        raise ValueError("pct_done must be an integer from 0 to 100")
    if p["minutes"] is not None:
        try:
            p["minutes"] = float(p["minutes"])
        except (ValueError, TypeError):
            raise ValueError("minutes must be a number") from None
        if not math.isfinite(p["minutes"]) or p["minutes"] < 0:
            raise ValueError("minutes must be finite and nonnegative")
    p["first_pass"] = p["result"] == "pass" and p["iteration"] == 0 and not p["reviewer_fix"]
    return p


def bucket_for(runner, model, cfg):
    candidate = f"{runner}:{model or ''}"
    for name, bucket in cfg.get("buckets", {}).items():
        if any(candidate.startswith(prefix) for prefix in bucket.get("match", [])):
            return name
    return None


def from_task(task, events, **review):
    runner = (task.get("runner") or "claude").lower()
    model = task.get("runner_model") or task.get("model_hint")
    starts, ends = [], []
    for event in events:
        kind = event["kind"]
        if kind == "status_in_progress" or kind in ("status_review", "status_done", "status_failed", "status_cancelled"):
            ts = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
            (starts if kind == "status_in_progress" else ends).append(ts)
    touches = task.get("touches") or []
    if isinstance(touches, str):
        touches = json.loads(touches)
    fields = dict(runner=runner, model=model, bucket=bucket_for(runner, model, load_plans()),
                  size=infer_size(touches, task.get("description")), iteration=task.get("iteration") or 0,
                  minutes=round((max(ends) - min(starts)).total_seconds() / 60, 1) if starts and ends else None)
    fields.update(review)
    fields["source"] = "delegate"
    return build(**fields)


def status_events(conn, task_id):
    return conn.execute("SELECT kind, ts FROM events WHERE task_id=? AND kind LIKE 'status_%' ORDER BY ts", (task_id,)).fetchall()


def record(conn, task_id, actor, payload):
    return db.log_event(conn, task_id, actor, KIND, payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("task", "manual"):
        sub = subs.add_parser(command)
        if command == "task":
            sub.add_argument("task_id")
        else:
            sub.add_argument("--runner", required=True)
            sub.add_argument("--model")
            sub.add_argument("--minutes", type=float)
            sub.add_argument("--task-id")
        sub.add_argument("--job", dest="job_type", required=True)
        sub.add_argument("--result", required=True)
        sub.add_argument("--why", default="")
        sub.add_argument("--fail-reason")
        sub.add_argument("--reviewer-fix", action="store_true")
        sub.add_argument("--pct-done", type=int)
        sub.add_argument("--dry-run", action="store_true")
    subs.add_parser("list").add_argument("--since")
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "list":
            since = args["since"]
            if since:
                datetime.strptime(since, "%Y-%m-%d")
            with db.get_conn() as conn:
                rows = conn.execute("SELECT payload FROM events WHERE kind=?" + (" AND ts>=?" if since else "") + " ORDER BY ts, id", (KIND, since) if since else (KIND,)).fetchall()
            for row in rows:
                payload = row["payload"]
                print(json.dumps(json.loads(payload) if isinstance(payload, str) else payload))
            return 0
        task_id = args.pop("task_id")
        dry_run = args.pop("dry_run")
        if command == "task":
            task = db.get_task(task_id)
            if task is None:
                raise ValueError("task not found")
            with db.get_conn() as conn:
                payload = from_task(task, status_events(conn, task_id), **args)
        else:
            payload = build(**args)
            payload["bucket"] = bucket_for(payload["runner"], payload["model"], load_plans())
        print(json.dumps(payload))
        if not dry_run:
            with db.get_conn() as conn:
                record(conn, task_id, "runner_fit", payload)
        return 0
    except ValueError as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 2
    except (db.HubUnavailable, OSError) as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
