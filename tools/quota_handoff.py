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
    args = parser.parse_args(argv)
    try:
        # Registry/delegate diagnostics must not corrupt the JSON result line.
        with redirect_stdout(sys.stderr):
            result = handoff(**vars(args))
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
