"""Preserve an outside runner's partial branch and dispatch a Claude successor."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import redirect_stdout
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db, org_tools_registry
from tools import runner_fit

LIMIT_STRINGS = {
    "codex": ("You've hit your usage limit", "You've reached your usage limit", "Usage limit reached", "UsageLimitExceeded"),
    "agy": ("You have exhausted your quota on this model.", "AI: Out of credits", "RESOURCE_EXHAUSTED"),
}


def _read(path):
    try:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def detect(runner, launch_dir, report_text=""):
    launch_dir = Path(launch_dir)
    texts = []
    if runner == "agy":
        texts.extend(_read(launch_dir / "agy-events.log").splitlines())
    elif runner == "codex":
        for line in _read(launch_dir / "codex-events.jsonl").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                texts.append(line)
            else:
                if isinstance(event, dict) and event.get("type") in ("error", "turn.failed"):
                    texts.append(json.dumps(event, ensure_ascii=False))
        texts.append(_read(launch_dir / "codex-final.txt"))
    texts.append(report_text)
    for text in texts:
        for needle in LIMIT_STRINGS.get(runner, ()):
            if needle.lower() in text.lower():
                return needle
    return None


def record_limit_stop(
    task_id,
    launch_dir=None,
    report_text: str = "",
    *,
    runner: str | None = None,
    root=ROOT,
) -> str | None:
    """If an outside run ended on a quota limit, set status='rate_limited' and record quota_stop in review JSON."""
    if isinstance(task_id, dict):
        task = task_id
        task_id = task.get("id")
    else:
        task = db.get_task(task_id) if task_id else None
    if not task_id or task is None:
        return None
    resolved_runner = (runner or task.get("runner") or "").strip().lower()
    if resolved_runner not in ("codex", "agy"):
        return None
    resolved_launch = Path(launch_dir) if launch_dir is not None else Path(root) / f".launch-{task_id}"
    if not report_text:
        report_text = task.get("report") or ""
    if not report_text and task.get("worktree"):
        report_text = _read(Path(task["worktree"]) / "docs" / "reports" / task_id / "REPORT.md")
    matched = detect(resolved_runner, resolved_launch, report_text)
    if not matched:
        return None
    existing_review = task.get("review")
    review_obj: dict = {}
    if isinstance(existing_review, dict):
        review_obj.update(existing_review)
    elif isinstance(existing_review, str) and existing_review.strip():
        try:
            parsed = json.loads(existing_review)
            if isinstance(parsed, dict):
                review_obj.update(parsed)
            else:
                review_obj["previous"] = parsed
        except ValueError:
            review_obj["previous"] = existing_review
    review_obj["quota_stop"] = matched
    review_obj["next"] = f"PH: pick it up on the branch, or python3 tools/quota_handoff.py {task_id}"
    db.update_status(task_id, "rate_limited", review=json.dumps(review_obj))
    return matched


def record_dead_run(task_id, reason: str) -> bool:
    """A run that did no turn (codex: no turn.completed; agy: the jetski no-output stub) ends failed,
    never in review/done. Only a row still in_progress moves: one the PH or the poller already moved
    is left alone."""
    task = db.get_task(task_id) if task_id else None
    if task is None or task.get("status") != "in_progress":
        return False
    db.update_status(task_id, "failed", delegate_log=f"dead run: {reason}")
    return True


check_limit_stop = record_limit_stop
mark_quota_stop = record_limit_stop


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def handoff(task_id, *, pct_done=None, limit_text=None, dry_run=False, delegate=True, root=ROOT):
    task = db.get_task(task_id)
    if task is None:
        raise ValueError("task not found")
    runner = task.get("runner")
    if runner not in ("codex", "agy", "jules"):
        raise ValueError("task runner must be codex, agy or jules")
    if task.get("status") in ("done", "merged"):
        raise ValueError("task is already done or merged")
    branch = task.get("branch")
    report = _git(root, "show", f"origin/{branch}:docs/reports/{task_id}/REPORT.md")
    launch = Path(root) / f".launch-{task_id}"
    matched = limit_text or detect(runner, launch, report.stdout if report.returncode == 0 else "")
    if not matched:
        files = {"agy": "agy-events.log", "codex": "codex-events.jsonl, codex-final.txt", "jules": "report"}[runner]
        reason = f"no limit text found in {launch} ({files}) or report — not a quota stop"
        if runner == "jules":
            reason += "; pass --limit-text with the exact words from the Jules page"
        raise ValueError(reason)
    if not branch:
        raise ValueError("partial work is not on origin")
    remote = _git(root, "ls-remote", "--heads", "origin", branch)
    if remote.returncode or not any(line.split()[-1:] == [f"refs/heads/{branch}"] for line in remote.stdout.splitlines()):
        raise ValueError("partial work is not on origin")
    with db.get_conn() as conn:
        payload = runner_fit.from_task(task, runner_fit.status_events(conn, task_id),
                                      job_type="code", result="fail", fail_reason="limit",
                                      pct_done=pct_done, matched=matched)
    description = (
        f'override: quota-handoff — {runner} hit its limit on {task_id} ("{matched}"), '
        f'{pct_done if pct_done is not None else "unknown"}% done; finish it on that branch\n'
        f'Start: git fetch origin {branch} && git merge --no-edit origin/{branch}. Keep the partial work; do not redo it.\n\n'
        + (task.get("description") or ""))
    touches = task.get("touches") or []
    if isinstance(touches, str):
        touches = json.loads(touches)
    create = dict(project=task["project"], role=task["role"], title=task["title"] + " (quota-handoff)",
                  description=description, depends_on="", touches=json.dumps(touches))
    result = dict(old=task_id, new=None, matched=matched, pct_done=pct_done, branch=branch)
    if dry_run:
        payload["why"] = "quota-handoff to <new id>"
        return dict(result, dry_run=True, create=create, runner_fit=payload, delegate=delegate)
    # The registry allocates the ID; do not fail the old task on a creation refusal.
    new_id = org_tools_registry.dispatch_sync("create_task", **create).strip()
    if not re.fullmatch(r"task-[0-9a-f]{8}", new_id):
        raise ValueError(new_id)
    payload["why"] = f"quota-handoff to {new_id}"
    with db.get_conn() as conn:
        runner_fit.record(conn, task_id, "quota_handoff", payload)
    db.update_status(task_id, "failed", review=f"quota-handoff → {new_id}: {matched}")
    db.set_fields(new_id, runner="claude", runner_model=None)
    if delegate:
        from tools import delegate as delegate_module
        asyncio.run(delegate_module.delegate_task(new_id))
    result["new"] = new_id
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("--pct-done", type=int)
    parser.add_argument("--limit-text")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-delegate", dest="delegate", action="store_false")
    parser.add_argument("--check-stop", action="store_true")
    parser.add_argument("--launch-dir")
    parser.add_argument("--report-file")
    parser.add_argument("--runner")
    parser.add_argument("--dead", help="with --check-stop: the launcher saw a run that did no turn")
    args = parser.parse_args(argv)
    kw = vars(args)
    check_stop = kw.pop("check_stop", False)
    launch_dir = kw.pop("launch_dir", None)
    report_file = kw.pop("report_file", None)
    runner = kw.pop("runner", None)
    dead = kw.pop("dead", None)
    try:
        if check_stop:
            report_text = _read(Path(report_file)) if report_file else ""
            matched = record_limit_stop(
                kw["task_id"],
                launch_dir=launch_dir,
                report_text=report_text,
                runner=runner,
            )
            failed = bool(dead) and not matched and record_dead_run(kw["task_id"], dead)
            print(json.dumps({"task_id": kw["task_id"], "quota_stop": matched, "dead_run_failed": failed}))
            return 0
        # Registry/delegate diagnostics must not corrupt the JSON result line.
        with redirect_stdout(sys.stderr):
            result = handoff(**kw)
        print(json.dumps(result))
        return 0
    except ValueError as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 2
    except (db.HubUnavailable, OSError) as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
