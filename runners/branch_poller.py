"""Branch poller — hub side, Phase 1 (docs/design/multi-host-workers.md).

Every POLL_SECONDS: for each `in_progress` task in the POLLER set
(`in_poller_set`, W1.5) -- dispatched by this box (`dispatcher_host ==
self_host()`, NULL = this box) AND either running on another host or one of
this box's own codex/agy launcher runs (no MCP report call, git is the only
signal) -- check whether its branch landed on GitHub yet. A claude row on this
box reports through its own submit_report and is never polled; a row
dispatched by another box is that box's to poll. REPORT.md / BLOCKER.md are
looked for at
`docs/reports/<task-id>/` first, then at the repo root (`read_task_file`).
A pushed branch carrying REPORT.md flips the task to `review`; one carrying
BLOCKER.md opens a GitHub issue and marks it `blocked_human`; and if the
remote worker died before pushing either, the task fails with a clear
`delegate_log`.

Effective 2026-09-17 (GH #151): REPORT.md/BLOCKER.md must open with a
`# REPORT task-<id>` / `# BLOCKER task-<id>` header naming the EXACT task
id being polled — see `_header_task_id`. A file missing that header, or
naming a different task, is never flipped on; a stale/wrong-task file
(task-424077a4 inherited a stray Higgsfield report checked out from a
committed-on-main REPORT.md) must never be read as this task's own report
again. No grandfather clause for pre-2026-09-17 branches — the header is
required unconditionally from here on.

Git is the only cross-machine channel (design doc §3 rule 2) — this is the
hub-side half of that contract. tools/delegate.py's `_spawn_remote` is the
spoke-side half: it clones the worktree in and hands off; this file is what
notices the branch coming back out.

Run:  python -m runners.branch_poller          (loop, POLL_SECONDS)
      python -m runners.branch_poller --once   (single tick, for tests)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db, mesh  # noqa: E402
from lib.config import get_project, host as get_host, self_host  # noqa: E402
from lib.logger import get_logger  # noqa: E402
from tools import delegate as delegate_mod  # noqa: E402
from tools import tmux_session  # noqa: E402
from tools.git_ops import _run_shell  # noqa: E402
from tools.worker_reap import (_cleanup_tmux_ttyd, close_remote,  # noqa: E402
                               is_dispatched_here, is_local_row, is_remote_row,
                               row_dispatcher, row_host)
from tools.worktree import provision_worktree  # noqa: E402

POLL_SECONDS = 60
SSH_TIMEOUT_S = 20
GIT_TIMEOUT_S = 20

# task-adbc6f43: runners whose "REPORT.md landed" claim is never trusted on
# its own -- claude follows WORKER.md and its own MCP submit_report contract
# on the Mac; codex/agy are headless CLIs whose only signal is git, and
# codex specifically exits 0 after writing nothing (docs/ops/agent-runners.md
# §4). See _artefact_gate_for_external_runner below.
EXTERNAL_RUNNERS = ("codex", "agy")

# GAP 2 (task-59780ac3): how long the newest commit on a finished remote
# branch must sit untouched before branch_poller will close that worker's
# surface — proof it has stopped pushing, not evidence by itself (a worker
# mid-render writes nothing new for much longer than this; REPORT.md having
# landed is the actual "done" signal, this just rules out "still mid-push").
REVIEW_CLOSE_QUIET_S = 5 * 60

_LOGGER = None


def _log():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger("branch_poller")
    return _LOGGER


def _run(cmd: list[str], *, cwd: str | None = None,
         timeout: float = GIT_TIMEOUT_S) -> subprocess.CompletedProcess:
    """subprocess.run that never raises — a poller tick surviving a bad git/
    ssh/gh call (offline Mac, dead network, gh not authed) matters more than
    it seeing the exact exception; callers just get a nonzero returncode."""
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def remote_branch_exists(repo_path: str, branch: str) -> bool:
    """`git ls-remote origin refs/heads/<branch>` — True iff it lists
    something. Read-only, no local fetch."""
    r = _run(["git", "ls-remote", "origin", f"refs/heads/{branch}"], cwd=repo_path)
    return r.returncode == 0 and bool(r.stdout.strip())


def fetch_branch(repo_path: str, branch: str) -> bool:
    r = _run(["git", "fetch", "origin", branch], cwd=repo_path)
    if r.returncode != 0:
        _log().warning("fetch origin %s failed in %s: %s", branch, repo_path,
                       (r.stderr or "").strip()[:300])
    return r.returncode == 0


def read_remote_file(repo_path: str, branch: str, file_name: str) -> str | None:
    """`git show origin/<branch>:<file_name>`, or None if the file (or the
    ref) is absent — a missing REPORT.md/BLOCKER.md is an expected, normal
    "still working" state, never an error to raise on."""
    r = _run(["git", "show", f"origin/{branch}:{file_name}"], cwd=repo_path)
    if r.returncode != 0:
        return None
    return r.stdout


def read_task_file(repo_path: str, branch: str, task_id: str,
                   file_name: str) -> str | None:
    """A worker's REPORT.md / BLOCKER.md as pushed on `branch`:
    `docs/reports/<task-id>/<file_name>` first, then `<file_name>` at the
    repo root (the layout every worker used before W0.6 moved codex/agy
    reports under docs/). The first path that exists wins outright -- a
    docs-path file with the wrong header is refused by the caller, never
    papered over by a root file that happens to carry the right one."""
    text = read_remote_file(repo_path, branch, f"docs/reports/{task_id}/{file_name}")
    if text is not None:
        return text
    return read_remote_file(repo_path, branch, file_name)


def remote_commit_age_seconds(repo_path: str, branch: str) -> float | None:
    """Seconds since the newest commit on `origin/<branch>` — the branch
    must already be fetched by the caller (fetch_branch); this never fetches
    on its own. None on any git failure (ref missing, empty/non-numeric
    output) — callers must treat that as "cannot prove it's quiet yet",
    never as "old enough"."""
    r = _run(["git", "log", "-1", "--format=%ct", f"origin/{branch}"], cwd=repo_path)
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    if not out:
        return None
    try:
        commit_epoch = int(out)
    except ValueError:
        return None
    return time.time() - commit_epoch


def _maybe_close_finished_remote_worker(task_id: str, repo_path: str, branch: str) -> None:
    """Close a remote worker's surface right after its task flips to
    `review` (GAP 2, task-59780ac3) — the gap measured 2026-09-08: on the
    Mac the CTO sees the iTerm tab and closes it at merge_task, but nobody
    watches a remote box, so task-5d0bd2fa's winbox claude.exe + terminal
    window sat alive for 5h54m after REPORT.md landed, until the CTO killed
    them by hand.

    A remote worker that pushed REPORT.md has declared itself finished — its
    entire output is in git, the process holds nothing more to give. But the
    CEO's hard rule (2026-09-07) is that a surface must NEVER be closed
    under a worker that may still be working (it could be waiting on a
    render), so this only acts when ALL of:
      (a) task.host is a remote spoke,
      (b) status is still 'review' on a fresh re-read here — a merge or a
          re-delegate could have raced the flip above,
      (c) REPORT.md is still present on the branch,
      (d) the branch's newest commit is at least REVIEW_CLOSE_QUIET_S old —
          proof the worker has actually stopped pushing, not mid-push.

    Passes close_remote's `allow_review=True` opt-in explicitly — no other
    caller in this codebase does. Never raises: a failure here must never
    undo the status flip that already landed; each early return is a normal
    "not eligible yet", not an error.
    """
    try:
        task = db.get_task(task_id)
    except Exception as e:
        _log().warning("task %s: could not re-read for review-close: %s", task_id, e)
        return
    if not task:
        return
    if not is_remote_row(task):
        return
    host = row_host(task)
    if task.get("status") != "review":
        return
    if read_task_file(repo_path, branch, task_id, "REPORT.md") is None:
        return
    age = remote_commit_age_seconds(repo_path, branch)
    if age is None or age < REVIEW_CLOSE_QUIET_S:
        return
    reap = close_remote(task, reason="branch_poller: REPORT.md pushed and quiet",
                        allow_review=True)
    _log().info("task %s: review-close attempted host=%s ssh_ok=%s refused=%s",
               task_id, host, reap.get("ssh_ok"), reap.get("refused"))


def _tmux_alive(session: str) -> bool:
    try:
        return tmux_session.has_session(session)
    except (OSError, subprocess.SubprocessError):
        return False


def _maybe_close_finished_local_launcher(task_id: str, repo_path: str, branch: str) -> None:
    """The hub's own codex/agy launcher run (host == self, W0.3b) after its
    task reached `review` (W1.5). No close_remote and no ssh: the launcher
    already killed its own tmux session when the CLI exited, so normally there
    is nothing to do and this returns at the first check. If the session is
    still alive once REPORT.md is on the branch and the newest commit is
    REVIEW_CLOSE_QUIET_S old (the worker has stopped pushing), close the tmux
    session + ttyd locally.

    Same never-raises contract as the remote version: each early return is a
    normal "not eligible yet". Re-reads the row so a merge or re-delegate that
    raced the flip is respected."""
    try:
        task = db.get_task(task_id)
    except Exception as e:
        _log().warning("task %s: could not re-read for local review-close: %s", task_id, e)
        return
    if not task or task.get("status") != "review":
        return
    if not (is_local_row(task) and is_dispatched_here(task)
            and _runner_of(task) in EXTERNAL_RUNNERS):
        return
    sessions = {s for s in (task.get("tmux_session"),
                            tmux_session.session_name_for(task_id)) if s}
    if not any(_tmux_alive(s) for s in sessions):
        return
    # Only reached for a session that outlived its run, so the fetch (the
    # commit-age check below needs a fetched ref) is the rare path.
    if not fetch_branch(repo_path, branch):
        return
    if read_task_file(repo_path, branch, task_id, "REPORT.md") is None:
        return
    age = remote_commit_age_seconds(repo_path, branch)
    if age is None or age < REVIEW_CLOSE_QUIET_S:
        return
    cleanup = _cleanup_tmux_ttyd(task)
    _log().info("task %s: local launcher session still alive after review + quiet "
               "period, closed locally tmux_killed=%s ttyd_killed=%s",
               task_id, cleanup.get("tmux_killed"), cleanup.get("ttyd_killed"))


def _runner_of(task: dict) -> str:
    return (task.get("runner") or "claude").strip().lower()


def in_poller_set(task: dict) -> bool:
    """The POLLER set (W1.5): a row this box dispatched AND either running on
    another host (git is its only report channel) or one of this box's own
    codex/agy launcher runs (W0.3b: they push a branch with docs/reports/<id>/
    REPORT.md and make no MCP report call). A claude row on this box reports
    through its own submit_report, so it is not polled; a row dispatched by
    another box is that box's to poll -- on a shared ledger two pollers would
    double-flip it. Does not look at `status`; `tick` selects `in_progress`."""
    return is_dispatched_here(task) and (
        not is_local_row(task) or _runner_of(task) in EXTERNAL_RUNNERS)


def _repo_path_here(proj: dict) -> str | None:
    """This box's own checkout of the project: `paths.<self_host>` first, the
    top-level `path:` (the Mac's) last. The poller runs `git ls-remote/fetch/
    show` there, so on a Contabo hub the Mac path is a directory that is not
    there and every branch would read as "not pushed yet"."""
    return (proj.get("paths") or {}).get(self_host()) or proj.get("path")


def remote_pid_alive(host_cfg: dict, pid: int) -> bool | None:
    """True/False from a live `tasklist` check; None if the host couldn't be
    reached at all — "unreachable" must never collapse into "dead", or a
    Wi-Fi blip fails a task that is still running fine."""
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias:
        return None
    r = _run(["ssh", ssh_alias, "tasklist", "/FI", f'"PID eq {pid}"'],
             timeout=SSH_TIMEOUT_S)
    if r.returncode != 0:
        return None
    return str(pid) in r.stdout


def open_blocker_issue(task_id: str, title_line: str, body: str) -> str | None:
    """`gh issue create` for a pushed BLOCKER.md. Returns the issue URL, or
    None on failure — never raises; a poller tick must survive `gh` being
    unauthenticated, offline, or rate-limited."""
    title = f"[{task_id}] {title_line}"[:250]
    r = _run(["gh", "issue", "create", "--title", title, "--body", body],
             timeout=SSH_TIMEOUT_S)
    if r.returncode != 0:
        _log().warning("gh issue create failed for %s: %s", task_id,
                       (r.stderr or "").strip()[:300])
        return None
    out = r.stdout.strip()
    return out.splitlines()[-1] if out else None


def parse_worker_json(text: str) -> dict:
    """Parse a `.worker.json` blob (written by windows/spawn-worker.ps1):
    `{"pid": int, "started_at": <ISO8601 str>, "host": str}`. Raises
    ValueError with a clear message on any missing/malformed field — a
    malformed file must read as an error, never silently as "no data yet"."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f".worker.json is not an object: {text!r}")
    missing = [k for k in ("pid", "started_at", "host") if k not in data]
    if missing:
        raise ValueError(f".worker.json missing field(s) {missing}: {text!r}")
    if not isinstance(data["pid"], int):
        raise ValueError(f".worker.json pid is not an int: {data['pid']!r}")
    return data


def _fetch_remote_text(host_cfg: dict, remote_path: str) -> str | None:
    """Read a text file already sitting on a Windows spoke, over ssh,
    read-only. None on any failure (unreachable host, missing file, no ssh
    alias) — never raises, same "can't confirm -> treat as absent" shape as
    tools.delegate._remote_sha256's probe."""
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias:
        return None
    escaped = remote_path.replace("'", "''")
    cmd = f"if (Test-Path '{escaped}') {{ Get-Content -Raw -Encoding UTF8 '{escaped}' }}"
    r = _run(["ssh", ssh_alias, "powershell", "-NoProfile", "-Command", cmd],
            timeout=SSH_TIMEOUT_S)
    if r.returncode != 0:
        return None
    return r.stdout or None


def _codex_transcript_remote_path(host_cfg: dict, task_id: str) -> str:
    """windows/spawn-worker.ps1's codex branch writes its --json events to
    `$launchDir/codex-events.jsonl`, where `$launchDir` is
    `<agents_root>\\.launch-<task>` — beside the script, never inside the
    worktree (a file there would get swept into the worker's own
    `git add -A`)."""
    agents_root = host_cfg["agents_root"].rstrip("\\")
    return f"{agents_root}\\.launch-{task_id}\\codex-events.jsonl"


def _fetch_codex_transcript(host_name: str, task_id: str) -> str | None:
    """codex's --json events for `task_id`, wherever its launcher wrote them.
    A Windows spoke: powershell over ssh (windows/spawn-worker.ps1). A Linux
    spoke: `cat` over ssh. The hub's own launcher run (host == self, W1.5):
    a plain read of this checkout's `.launch-<task>/`, where
    scripts/spawn-worker-remote.sh puts it beside itself. Before this a Linux
    codex row could never pass the gate (backslash path, powershell command)
    and would fail instead of reaching review. ValueError = unknown host."""
    host_cfg = get_host(host_name)
    if host_name == self_host():
        try:
            text = (ROOT / f".launch-{task_id}" / "codex-events.jsonl").read_text(
                encoding="utf-8", errors="replace")
        except OSError:
            return None
        return text or None
    if host_cfg.get("os") == "linux":
        ssh_alias = host_cfg.get("ssh")
        if not ssh_alias:
            return None
        root = host_cfg["agents_root"].rstrip("/")
        r = _run(["ssh", ssh_alias, "cat", f"{root}/.launch-{task_id}/codex-events.jsonl"],
                 timeout=SSH_TIMEOUT_S)
        return r.stdout if r.returncode == 0 and r.stdout else None
    return _fetch_remote_text(host_cfg, _codex_transcript_remote_path(host_cfg, task_id))


def _run_project_tests_on_branch(repo_path: str, branch: str,
                                 test_cmd: str) -> tuple[int, str]:
    """Materialise `origin/<branch>` into a scratch git worktree beside
    `repo_path` and run `test_cmd` there — the SAME `test_command` field and
    the SAME provision_worktree/_run_shell helpers tools.git_ops.merge_task's
    gate_tests already uses, so this gate and the merge-time gate can never
    judge a branch's tests differently (CTO: "make sure the two cannot
    disagree; do not add new surface"). Always tears the scratch worktree
    down, even on failure."""
    scratch = Path(tempfile.mkdtemp(prefix="mooniex-gate-"))
    scratch.rmdir()  # `git worktree add` creates the dir itself; must not pre-exist
    try:
        add = _run(["git", "-C", repo_path, "worktree", "add", "--detach",
                   str(scratch), f"origin/{branch}"], timeout=60)
        if add.returncode != 0:
            return 1, f"git worktree add failed: {(add.stderr or '').strip()[:500]}"
        try:
            provision_worktree(Path(repo_path), scratch)
        except OSError as e:  # never let a provisioning bug block the gate itself
            _log().warning("gate: provision_worktree failed for %s: %s", branch, e)
        return _run_shell(test_cmd, cwd=scratch)
    finally:
        _run(["git", "-C", repo_path, "worktree", "remove", "--force", str(scratch)])


def _artefact_gate_for_external_runner(task: dict, repo_path: str,
                                       branch: str) -> "delegate_mod.GateResult":
    """The gate task-adbc6f43's iter-2 review demanded be wired into a real
    entry point, called from check_task right before an external runner's
    task would flip to review. Builds the `run_tests` callback and (for
    codex) fetches the --json transcript, then defers the actual pass/fail
    logic to tools.delegate.artefact_gate — never reimplemented here.

    A project with no `test_command` configured skips the test-run check
    (returns success for it) rather than failing — matches
    tools.git_ops.merge_task's own `if gate and test_cmd and worktree`
    skip-when-absent behaviour, for the same "cannot disagree" reason."""
    task_id = task["id"]
    runner = (task.get("runner") or "claude").strip().lower()
    proj = get_project(task["project"])
    base = proj["default_branch"]
    test_cmd = proj.get("test_command")

    if test_cmd:
        def run_tests() -> tuple[int, str]:
            return _run_project_tests_on_branch(repo_path, branch, test_cmd)
    else:
        def run_tests() -> tuple[int, str]:
            return 0, "no test_command configured for this project — skipped"

    codex_transcript = None
    if runner == "codex":
        try:
            codex_transcript = _fetch_codex_transcript(row_host(task), task_id)
        except ValueError as e:
            _log().warning("task %s: could not resolve host for codex transcript: %s",
                           task_id, e)

    return delegate_mod.artefact_gate(
        runner=runner, repo_path=repo_path, branch=branch, base=base,
        run_tests=run_tests, codex_transcript=codex_transcript,
    )


_HEADER_RE_TEMPLATE = r"^#\s*{kind}\s+(task-\S+)\s*$"


def _header_task_id(content: str, kind: str) -> str | None:
    """The task id named on a REPORT.md/BLOCKER.md's first line, or None if
    that line is missing or doesn't match `# {kind} task-<id>` exactly
    (`kind` is "REPORT" or "BLOCKER"). Whitespace-only content and a blank
    first line both read as "no header" rather than raising."""
    stripped = content.strip()
    if not stripped:
        return None
    first_line = stripped.splitlines()[0].strip()
    m = re.match(_HEADER_RE_TEMPLATE.format(kind=kind), first_line)
    return m.group(1) if m else None


def _publish_via_mesh(task: dict) -> None:
    """W2.3 (ORG_MESH_DISPATCH): a worker never pushes. When the row was
    dispatched by a different box than the one it runs on, ask the worker's
    host to publish the branch (`publish_branch <task-id>`, node_dispatch's
    `git push origin <agent branch>` from the worktree) before this tick looks
    for it on origin. Never raises, never changes the row: an unreachable host
    or a refusal only means "not published yet", and the branch check below
    reads origin either way."""
    if not mesh.enabled() or row_dispatcher(task) == row_host(task):
        return
    task_id, host_name = task["id"], row_host(task)
    try:
        reply = mesh.dispatch(host_name, "publish_branch", task_id)
    except mesh.MeshUnreachable as e:
        _log().warning("task %s: publish_branch on %s got no answer: %s",
                       task_id, host_name, e)
        return
    if reply.get("ok"):
        _log().info("task %s: published by %s: %s", task_id, host_name, reply.get("result"))
    else:
        _log().info("task %s: publish_branch on %s said no: %s",
                    task_id, host_name, reply.get("error"))


def check_task(task: dict) -> None:
    """One task's tick. Never raises — a bad/malformed row must not kill
    the loop for every other task. Acts only on the POLLER set
    (`in_poller_set`, W1.5): rows this box dispatched that run elsewhere, plus
    its own codex/agy launcher runs."""
    task_id = task["id"]
    branch = task.get("branch")
    if not branch or not in_poller_set(task):
        return
    host_name = row_host(task)
    local_run = is_local_row(task)

    try:
        proj = get_project(task["project"])
    except ValueError as e:
        _log().warning("task %s: unknown project %s: %s", task_id, task.get("project"), e)
        return
    repo_path = _repo_path_here(proj)
    if not repo_path:
        _log().warning("task %s: project %s has no checkout on %s to poll from",
                       task_id, task.get("project"), self_host())
        return

    _publish_via_mesh(task)

    if remote_branch_exists(repo_path, branch):
        fetch_branch(repo_path, branch)

        report = read_task_file(repo_path, branch, task_id, "REPORT.md")
        if report is not None:
            header_id = _header_task_id(report, "REPORT")
            if header_id != task_id:
                found = header_id or "no header"
                _log().warning(
                    "task %s: REPORT.md header mismatch (%s) on %s — refusing",
                    task_id, found, branch,
                )
                db.set_fields(
                    task_id, actor="branch_poller",
                    delegate_log=(
                        f"REPORT.md header mismatch on {branch}: found "
                        f"{found!r}, expected 'task {task_id}' — refusing to "
                        "flip to review"
                    ),
                )
                return

            runner = (task.get("runner") or "claude").strip().lower()
            if runner in EXTERNAL_RUNNERS:
                gate = _artefact_gate_for_external_runner(task, repo_path, branch)
                if not gate:
                    reason = "; ".join(gate.reasons)
                    _log().warning(
                        "task %s: artefact gate REFUSED runner=%s on %s: %s",
                        task_id, runner, branch, reason,
                    )
                    db.update_status(
                        task_id, "failed",
                        delegate_log=f"artefact gate refused (runner={runner}): {reason}",
                        actor="branch_poller",
                    )
                    return
                _log().info("task %s: artefact gate passed runner=%s (%s)",
                           task_id, runner, "; ".join(gate.reasons))

            db.update_status(task_id, "review", report=report, actor="branch_poller")
            _log().info("task %s -> review (REPORT.md on %s)", task_id, branch)
            if local_run:
                _maybe_close_finished_local_launcher(task_id, repo_path, branch)
            else:
                _maybe_close_finished_remote_worker(task_id, repo_path, branch)
            return

        blocker = read_task_file(repo_path, branch, task_id, "BLOCKER.md")
        if blocker is not None:
            header_id = _header_task_id(blocker, "BLOCKER")
            if header_id != task_id:
                found = header_id or "no header"
                _log().warning(
                    "task %s: BLOCKER.md header mismatch (%s) on %s — refusing",
                    task_id, found, branch,
                )
                db.set_fields(
                    task_id, actor="branch_poller",
                    delegate_log=(
                        f"BLOCKER.md header mismatch on {branch}: found "
                        f"{found!r}, expected 'task {task_id}' — refusing to "
                        "flip to blocked_human"
                    ),
                )
                return
            # First line is the mandatory header; the issue title/body come
            # from the worker's actual blocker text, the line after it.
            body_lines = [ln for ln in blocker.strip().splitlines() if ln.strip()]
            first_line = body_lines[1] if len(body_lines) > 1 else "blocked"
            issue_url = open_blocker_issue(task_id, first_line, blocker)
            log_line = f"remote worker blocked: {first_line}"
            if issue_url:
                log_line += f" — {issue_url}"
            db.update_status(task_id, "blocked_human", delegate_log=log_line,
                             actor="branch_poller")
            _log().info("task %s -> blocked_human (%s)", task_id, log_line)
            return

        # Branch exists but neither REPORT.md nor BLOCKER.md landed yet —
        # still working, no state change.
        return

    # No branch pushed yet. Before treating this as "still working", check
    # whether the remote process is even still alive. A local launcher run's
    # pid is the watchdog's LOCAL duty (pid liveness), not the poller's.
    pid = task.get("pid")
    if not pid or local_run:
        return
    try:
        host_cfg = get_host(host_name)
    except ValueError:
        return
    alive = remote_pid_alive(host_cfg, pid)
    if alive is False:
        db.update_status(
            task_id, "failed",
            delegate_log="remote worker died before pushing",
            actor="branch_poller",
        )
        _log().warning("task %s -> failed (pid %s gone on %s, no branch pushed)",
                       task_id, pid, host_name)


def _sweep_review_local_launchers() -> None:
    """A local launcher row is polled only while `in_progress`; once flipped to
    `review` nothing else would look at its tmux session again, so the "still
    alive after review + quiet period" close would never get a second chance.
    Re-offer each such row every tick; `_maybe_close_finished_local_launcher`
    returns at its first (cheap, tmux-only) check for the normal case where the
    launcher already tore its own session down."""
    for t in db.list_tasks(status="review", limit=500):
        if not (t.get("branch") and is_local_row(t) and is_dispatched_here(t)
                and _runner_of(t) in EXTERNAL_RUNNERS):
            continue
        try:
            repo_path = _repo_path_here(get_project(t["project"]))
            if repo_path:
                _maybe_close_finished_local_launcher(t["id"], repo_path, t["branch"])
        except Exception as e:  # a bad task must never kill the loop
            _log().error("review sweep failed for %s: %s", t.get("id"), e)


def tick() -> int:
    """One poll pass over the POLLER set (`in_poller_set`): in-progress rows
    this box dispatched that run on another host, plus its own codex/agy
    launcher runs. Returns the count of tasks checked (not how many changed —
    0 changes on a normal tick is the common case, not a problem)."""
    tasks = [t for t in db.list_tasks(status="in_progress", limit=500)
             if in_poller_set(t)]
    for t in tasks:
        try:
            check_task(t)
        except Exception as e:  # a bad task must never kill the loop
            _log().error("check_task failed for %s: %s", t.get("id"), e)
    _sweep_review_local_launchers()
    return len(tasks)


def main() -> None:
    once = "--once" in sys.argv
    db.init()
    _log().info("branch_poller starting (poll=%ss once=%s)", POLL_SECONDS, once)
    while True:
        try:
            n = tick()
            if n:
                _log().info("tick: checked %d polled task(s)", n)
        except Exception as e:
            _log().error("tick failed: %s", e)
        if once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
