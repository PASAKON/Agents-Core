"""Mac runner lane for agy (Antigravity CLI) — headless execution in a task worktree.

Wired via runners/worker_init.py when runner == 'agy'.
Follows the contract in docs/ops/agent-runners.md §6 and §6b:
agy only edits files; the hub handles git add, verification, and commit.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from lib import db

ORG_PYTHON = str(Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python")
# Same pattern as tools/route._AGY_BROWSE_RE: the brief that routes a task to agy
# is the brief that must be told agy_browse is allowed.
_AGY_BROWSE_RE = re.compile(r"(?<![\w/])tools/agy_browse\.py\b")

# Placeholder so tests or callers can monkeypatch agy_local.update_status directly
update_status: Callable[..., Any] | None = None


def _update_status(task_id: str, status: str, **kwargs: Any) -> bool:
    """Delegate to monkeypatched agy_local.update_status or agy_local.db.update_status."""
    mod_fn = globals().get("update_status")
    if callable(mod_fn):
        return mod_fn(task_id, status, **kwargs)
    return db.update_status(task_id, status, **kwargs)


def find_agy_binary() -> str:
    """Resolve agy binary: env AGY_BIN -> ~/.local/bin/agy -> agy on PATH."""
    env_bin = os.environ.get("AGY_BIN")
    if env_bin and env_bin.strip():
        return env_bin.strip()
    local_bin = Path.home() / ".local" / "bin" / "agy"
    if local_bin.exists():
        return str(local_bin)
    return shutil.which("agy") or "agy"


def build_agy_prompt(prompt: str, worktree: str) -> str:
    """Append the agy contract (allowed commands, edit scope, report) to the task prompt."""
    contract = (
        f"Work only inside {worktree}. You may edit files there. "
        f"The only shell commands you may run are: `{ORG_PYTHON} -m pytest <args>` (run tests with exactly this interpreter path), "
        f"`git status`, `git diff`, `git log`, `git show`, `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `pwd`. "
        f"Any other command, including git add, git commit, pip, npm or a bare python, aborts your run and loses your work. "
        f"Ignore any earlier instruction to commit, to call MCP tools or to run other commands; the hub commits for you. "
        f"When finished, write REPORT.md at the worktree root with three headings: "
        f"Files changed, What was done, Blockers."
    )
    if _AGY_BROWSE_RE.search(prompt):
        # GH #188: a browser brief routed here (tools/route.class_for) needs its one
        # browser command named, or the list above tells agy it may not browse.
        contract += (
            f" Exception for this browser task: you may also run "
            f"`{ORG_PYTHON} tools/agy_browse.py [--port N] [--tab ID] <verb> [args]` from the worktree root, "
            f"with exactly this interpreter path. It is your only browser. Every argument may use only "
            f"A-Z a-z 0-9, space and _ . / : # = @ % + , ' \" ( ) [ ] - : no Thai or other non-ASCII text, "
            f"no * ? ~ (so no [attr*=x] selectors). A command outside this set is denied, and the denial ends "
            f"your run with no retry. To reach an element by a label you cannot type, go by position: "
            f"`count button`, then `text ':nth-match(button, N)'` to read it, then `click ':nth-match(button, N)'`."
        )
    p = prompt.rstrip()
    if p:
        return f"{p}\n\n{contract}\n"
    return f"{contract}\n"


def tail_log(log_path: Path, n: int = 40) -> str:
    """Return the last n lines of log_path as a string."""
    if not log_path.exists():
        return ""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def run_git(worktree: str, args: list[str]) -> subprocess.CompletedProcess:
    """Run a git command in the worktree."""
    cmd = ["git", "-C", worktree] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def run_agy_subprocess(
    agy_bin: str,
    prompt: str,
    worktree: str,
    log_path: Path,
    timeout: int = 3600,
    model: str | None = None,
) -> int:
    """Run agy headless with stdout and stderr appended to log_path."""
    effective_model = model if model else (os.environ.get("AGY_MODEL") or "gemini-3.8-flash-high")
    cmd = [agy_bin, "-p", prompt, "--model", effective_model, "--mode", "accept-edits", "--add-dir", worktree]
    work_dir = os.environ.get("WORK_DIR")
    if work_dir and Path(work_dir).is_dir():
        # agy_browse writes shots to $WORK_DIR/agy-shots; outside the workspace a headless
        # read_file of one is auto-denied and the run dies (task-4245497d, task-ed829cdc).
        cmd += ["--add-dir", work_dir]
    with open(log_path, "a", encoding="utf-8") as f:
        try:
            proc = subprocess.run(
                cmd,
                cwd=worktree,
                stdin=subprocess.DEVNULL,
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
            return proc.returncode
        except subprocess.TimeoutExpired:
            f.write(f"\n[agy_local] Process timed out after {timeout} seconds\n")
            return 124
        except Exception as e:
            f.write(f"\n[agy_local] Process execution failed: {e}\n")
            return 1


def run_agy_task(task: dict, worktree: str, prompt: str, role: str) -> int:
    """Execute an agy worker task in worktree and manage git lifecycle and status."""
    task_id = task.get("id") or ""
    log_path = Path(worktree) / ".agy-run.log"

    # Record own PID first
    _update_status(task_id, "in_progress", pid=os.getpid(), actor=role)

    # Resolve binary and assemble prompt
    agy_bin = find_agy_binary()
    full_prompt = build_agy_prompt(prompt, worktree)

    # Run agy
    exit_code = run_agy_subprocess(
        agy_bin,
        full_prompt,
        worktree,
        log_path,
        timeout=3600,
        model=(task.get("runner_model") or None),
    )

    # Git stage: add all, unstage the run log, check cached diff
    run_git(worktree, ["add", "-A"])
    # REPORT.md is read into the task row below, never merged into the repo.
    run_git(worktree, ["reset", "-q", "--", ".agy-run.log", "REPORT.md"])
    diff_res = run_git(worktree, ["diff", "--cached", "--quiet"])

    # git diff --quiet exits 0 when there are no differences (nothing staged)
    if diff_res.returncode == 0:
        tail = tail_log(log_path, 40)
        prefix = f"agy produced no file changes (exit {exit_code})"
        report = f"{prefix}\n\n{tail}" if tail else prefix
        _update_status(task_id, "failed", report=report, actor=role)
        return 6

    # Otherwise commit
    title = " ".join((task.get("title") or "").split())
    commit_msg = f"agy({task_id}): {title}"
    commit_res = run_git(
        worktree,
        [
            "-c", "user.name=agy-worker",
            "-c", "user.email=agy-worker@localhost",
            "commit", "-q", "-m", commit_msg,
        ],
    )
    if commit_res.returncode != 0:
        report = f"agy edited files but git commit failed:\n{commit_res.stderr[-2000:]}"
        _update_status(task_id, "failed", report=report, actor=role)
        return 7

    # Read REPORT.md
    report_file = Path(worktree) / "REPORT.md"
    if report_file.exists():
        try:
            body = report_file.read_text(encoding="utf-8", errors="replace")
            report_text = body.strip() if body.strip() else "(no REPORT.md)"
        except Exception:
            report_text = "(no REPORT.md)"
    else:
        report_text = "(no REPORT.md)"

    tail = tail_log(log_path, 40)
    review_report = f"{report_text}\n\n--- agy log tail ---\n{tail}"
    _update_status(task_id, "review", report=review_report, actor=role)
    return 0
