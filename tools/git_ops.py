"""Git operations restricted to CTO. Merge worktree branch → default, then push."""
from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from lib import db
from lib.config import get_project, is_c_level, self_host
from lib.notify import info, success, error, warn
from tools import workdir
from tools.delegate import _scope_applies
from tools.worker_reap import close_dev
from tools.worktree import branch_name, provision_worktree, remove_worktree


class GitOpsError(Exception):
    pass


def _run(cmd: list[str], cwd: str | Path) -> str:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise GitOpsError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()


def _run_shell(cmd: str, cwd: str | Path) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(cwd), shell=True,
                       capture_output=True, text=True)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def _conflict_files(repo: Path) -> list[str]:
    try:
        out = _run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=repo)
        return [line for line in out.splitlines() if line.strip()]
    except GitOpsError:
        return []


def _touches_violation(worktree: str, base: str, touches: list[str],
                       ref: str = "HEAD") -> list[str]:
    """Return files the branch changed (vs base) that fall outside `touches`.

    A file is "covered" if it exactly matches a declared path, sits under a
    declared directory prefix, or matches a declared glob. Only called when
    `touches` is non-empty — an empty declaration means the task made no
    scope claim and is not gated (matches check_collisions semantics).
    """
    try:
        out = _run(["git", "diff", "--name-only", f"{base}...{ref}"], cwd=worktree)
    except GitOpsError:
        return []
    changed = [line for line in out.splitlines() if line.strip()]
    extra = []
    for f in changed:
        covered = any(
            f == t or f.startswith(t.rstrip("/") + "/") or fnmatch.fnmatch(f, t)
            for t in touches
        )
        if not covered:
            extra.append(f)
    return extra


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    """True if `ancestor` is an ancestor of (or equal to) `descendant`.

    Used to detect a no-op merge: if the task branch is already contained in
    base, `git merge` reports "Already up to date" and creates no commit.
    """
    r = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=str(repo), capture_output=True, text=True,
    )
    # exit 0 = is ancestor; 1 = not; other = bad ref / error (treat as "not"
    # so the subsequent merge surfaces the real failure).
    return r.returncode == 0


def _resolve_merge_ref(repo: Path, branch: str) -> str:
    """The ref `git merge` should consume for `branch`.

    A Mac worker's branch exists locally (its worktree lives in this clone).
    A REMOTE worker (winbox, Contabo) pushes from its own clone, so the hub
    only ever has `origin/<branch>` — and `git merge <branch>` fails with
    "not something we can merge" (E2E task-95803168, 2026-09-18; the same
    hand-merge workaround had sat in memory since 2026-09-09). Prefer the
    local branch when it exists; otherwise fetch it from origin and merge the
    remote-tracking ref. Raises GitOpsError when neither exists.
    """
    r = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=str(repo), capture_output=True, text=True,
    )
    if r.returncode == 0:
        return branch
    subprocess.run(["git", "fetch", "origin", branch], cwd=str(repo),
                   capture_output=True, text=True)  # best effort; verified next
    r = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"],
        cwd=str(repo), capture_output=True, text=True,
    )
    if r.returncode == 0:
        return f"origin/{branch}"
    raise GitOpsError(
        f"branch {branch} exists neither locally nor on origin — nothing to "
        f"merge (remote worker never pushed?)"
    )


def _repo_path_for_host(proj: dict, host: str) -> str:
    """This host's runtime checkout for `proj` (Org Mesh W0.2).

    Same rule as `lib.config.project_path_for_host`, applied to an already-
    fetched project dict instead of a project KEY: `mac` falls back to the
    legacy top-level `path` when `paths.mac` is absent, every other host
    requires `paths.<host>`. Deliberately does not call
    `project_path_for_host` itself — that function does its own internal
    `get_project()` lookup against `lib.config`'s real project registry, so
    calling it here would bypass a test's `monkeypatch.setattr(git_ops,
    "get_project", ...)` (the established pattern across the merge/revert
    test suite) and hit the real config/projects.yaml instead of the fake
    project the test built.
    """
    if host == "mac":
        p = (proj.get("paths") or {}).get("mac") or proj.get("path")
    else:
        p = (proj.get("paths") or {}).get(host)
    if not p:
        raise ValueError(
            f"project {proj.get('key')!r} has no path configured for host "
            f"{host!r} — not routable there. Add it under paths.{host} in "
            f"config/projects.yaml."
        )
    return p


CHANNEL_FILES = ("REPORT.md", "BLOCKER.md")


def _drop_channel_files(repo: Path, pre_sha: str) -> list[str]:
    """After a merge, remove REPORT.md / BLOCKER.md that the merge introduced
    at the repo root and commit the removal. They are a remote worker's
    channel to the hub (roles/_worker_remote.md), not repository content --
    a REPORT.md left on main was the #151 root cause (every fresh worktree
    checked it out). Files that already existed at `pre_sha` are left alone.
    Returns the paths removed."""
    dropped = []
    for name in CHANNEL_FILES:
        if not (repo / name).exists():
            continue
        was_there = subprocess.run(
            ["git", "cat-file", "-e", f"{pre_sha}:{name}"],
            cwd=str(repo), capture_output=True, text=True,
        ).returncode == 0
        if not was_there:
            dropped.append(name)
    if dropped:
        _run(["git", "rm", "-q", "--", *dropped], cwd=repo)
        _run(["git", "commit", "-q", "-m",
              f"merge: drop worker channel file(s) {', '.join(dropped)} (not repo content)"],
             cwd=repo)
    return dropped


def _blocking_dirty_paths(porcelain: str, branch_paths: set[str]) -> tuple[list[str], list[str]]:
    """Split `git status --porcelain` output into (blocking, ignored) for the
    merge pre-flight.

    Tracked modifications always block: `git merge` refuses to overwrite
    local changes. Untracked paths (`??`) block only when the branch brings
    the same path, or a path under an untracked directory — otherwise git
    merges around them untouched. Refusing on EVERY untracked path (the
    original #42 check) stalled merges for as long as any concurrent session
    kept a scratch directory in the shared main checkout: on 2026-09-18
    another CTO's `prototypes/bl51-first30/` held up two unrelated merges.
    """
    blocking: list[str] = []
    ignored: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if not line.startswith("??"):
            blocking.append(path)
            continue
        prefix = path if path.endswith("/") else path + "/"
        if path in branch_paths or any(bp.startswith(prefix) for bp in branch_paths):
            blocking.append(path)
        else:
            ignored.append(path)
    return blocking, ignored


_TRANSIENT_PUSH_MARKERS = (
    "internal server error", "connection reset", "connection refused",
    " 500 ", "http/1.1 500", "http/2 500", " 502 ", " 503 ", " 504 ",
)


def _is_transient_push_error(stderr: str) -> bool:
    low = f" {stderr.lower()} "
    return any(m in low for m in _TRANSIENT_PUSH_MARKERS)


def _is_non_ff_rejection(stderr: str) -> bool:
    low = stderr.lower()
    return "[rejected]" in low or "non-fast-forward" in low or "fetch first" in low


def _push_once(repo: Path, base: str) -> tuple[int, str, str]:
    """Seam for tests: run `git push origin HEAD:<base>` once, never --force.

    `HEAD:<base>` (not a bare `<base>`) so this also works from a detached
    HEAD (Org Mesh W0.2 merges happen in a temp detached worktree) — a bare
    branch-name push has no local branch ref to resolve there. Behaviorally
    identical to `git push origin <base>` from an attached HEAD on `<base>`.

    Tests inject transient (HTTP 5xx-style) failures by monkeypatching this
    function directly (real git has no way to fabricate a 500 locally).
    """
    r = subprocess.run(["git", "push", "origin", f"HEAD:{base}"], cwd=str(repo),
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def _verify_on_origin(repo: Path, base: str, merge_sha: str) -> bool:
    """After a push, fetch and confirm merge_sha actually landed on origin/<base>."""
    try:
        _run(["git", "fetch", "origin", base], cwd=repo)
    except GitOpsError:
        return False
    r = subprocess.run(
        ["git", "merge-base", "--is-ancestor", merge_sha, f"origin/{base}"],
        cwd=str(repo), capture_output=True, text=True,
    )
    return r.returncode == 0


def _push_base(repo: Path, base: str, merge_sha: str) -> dict:
    """Push `base` to origin. Never rebases, never force-pushes.

    - Non-fast-forward rejection (another session pushed first): fetch
      origin/<base> and merge it into the local base with --no-edit, then
      retry the push once. A conflict during that integration merge aborts
      the merge (leaving the local merge commit in place) and is reported,
      never forced.
    - Transient remote errors (HTTP 5xx / "Internal Server Error" /
      connection reset): retried up to 3 attempts total with a short
      backoff between them.

    Returns a dict always containing `pushed` and `on_origin`, plus either
    `push_output` (success) or `push_error` (failure, last stderr trimmed —
    prefixed so a `pushed: false` result reads as distinctly different from
    a normal success to anyone scanning the result).
    """
    integrated = False
    transient_retries = 0
    last_stderr = ""
    while True:
        rc, stdout, stderr = _push_once(repo, base)
        if rc == 0:
            out = (stdout + stderr).strip()
            result = {"pushed": True, "push_output": out[:300],
                      "on_origin": _verify_on_origin(repo, base, merge_sha)}
            if integrated:
                result["integrated"] = True
            return result

        last_stderr = (stderr or "").strip()

        if not integrated and _is_non_ff_rejection(last_stderr):
            try:
                _run(["git", "fetch", "origin", base], cwd=repo)
                _run(["git", "merge", "--no-edit", f"origin/{base}"], cwd=repo)
            except GitOpsError as merge_err:
                try:
                    _run(["git", "merge", "--abort"], cwd=repo)
                except GitOpsError:
                    pass
                reason = f"integration merge conflict, local merge commit preserved: {str(merge_err)[:400]}"
                return {"pushed": False, "on_origin": False,
                        "push_error": f"merged locally, NOT pushed: {reason}"}
            integrated = True
            continue  # base now has origin's changes folded in — retry the push

        if _is_transient_push_error(last_stderr) and transient_retries < 2:
            transient_retries += 1
            time.sleep(0.3 * transient_retries)
            continue

        reason = last_stderr[:400] or "unknown push error"
        return {"pushed": False, "on_origin": False,
                "push_error": f"merged locally, NOT pushed: {reason}"}


def _create_temp_worktree(repo: Path, ref: str, *, prefix: str) -> Path:
    """Add a throwaway detached worktree of `repo` at `ref`.

    `git worktree add` only registers a new working directory against
    `repo`'s existing object store/refs — it never touches `repo`'s own
    working directory or current branch, so this is safe to call while
    `repo` is any host's live, possibly-dirty runtime checkout.
    """
    tmp_root = Path(tempfile.mkdtemp(prefix=prefix))
    wt = tmp_root / "wt"
    _run(["git", "worktree", "add", "--detach", str(wt), ref], cwd=repo)
    return wt


def _remove_temp_worktree(repo: Path, tmp_dir: Path) -> None:
    """Undo `_create_temp_worktree`. Best-effort — a leftover temp dir is a
    disk-hygiene nuisance, never a reason to fail a merge that already
    landed."""
    try:
        _run(["git", "worktree", "remove", "--force", str(tmp_dir)], cwd=repo)
    except GitOpsError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        try:
            _run(["git", "worktree", "prune"], cwd=repo)
        except GitOpsError:
            pass
    shutil.rmtree(tmp_dir.parent, ignore_errors=True)


def _ff_runtime_checkout(repo: Path, base: str) -> dict:
    """Best-effort fast-forward of this host's runtime checkout to
    `origin/<base>`, after a merge already landed on origin.

    `git merge --ff-only` is the whole mechanism: it only touches files that
    actually differ between the checkout's old and new tip, so it silently
    tolerates a dirty file the incoming change never touches, and it
    refuses — cleanly, with nothing mutated — the moment the checkout has
    diverged or the incoming change collides with a dirty file. No
    special-casing needed for any of those cases; git already decides
    correctly. This never runs inside the merge's own temp worktree, and a
    refusal here never undoes or blocks the merge that already landed on
    origin.
    """
    r = subprocess.run(["git", "merge", "--ff-only", f"origin/{base}"],
                       cwd=str(repo), capture_output=True, text=True)
    if r.returncode == 0:
        return {"runtime_updated": True, "runtime_reason": None}
    reason = (r.stderr or r.stdout or "unknown ff error").strip()[:500]
    return {"runtime_updated": False, "runtime_reason": reason}


def merge_task(task_id: str, *, role: str = "cto", strategy: str = "no-ff",
               push: bool | None = None, cleanup: bool = True,
               gate_tests: bool = False, override_touches_check: bool = False) -> dict:
    """Merge agent branch into project default branch. CTO only.

    Host-aware (Org Mesh W0.2, docs/design/org-mesh.md C5): when the project
    has an origin remote (`remote:` set in config/projects.yaml), the merge
    happens in a throwaway detached worktree of `origin/<base>` — never in
    this host's live runtime checkout, which may be dirty, diverged, or
    simply not exist at `proj["path"]` (a Mac-only path) on this host. After
    the merge lands on origin, the runtime checkout is fast-forwarded in
    place, best-effort — a refusal there (dirty file collision, diverged
    checkout) never undoes or blocks the merge that already landed.

    A project with no `remote` (no origin) keeps the original local-checkout
    merge path unchanged, gated by `auto_push` exactly as before.

    With gate_tests=True (or proj.gate_tests=true), run proj.test_command
    in the worktree before merging — failure reopens the task with output.

    If the task declared `touches`, the branch's actual changed files (vs
    base) are checked against that declaration before anything else runs.
    A file outside the declaration blocks the merge (status→review, branch
    and worktree preserved) instead of merging silently — this is what
    would have caught the git-add-A/stale-worktree incident (issue #29)
    automatically instead of relying on a human running `git diff --stat`
    by habit. Pass override_touches_check=True after manually reviewing
    the diff (review_diff tool) to force through a legitimate over-touch.

    On merge conflict: abort, set status=conflict, file a gh issue with
    the conflict files so the human can resolve.

    `auto_push` on the project controls only whether a WORKER may push its
    own branch directly — on a project with an origin remote, a merge
    always pushes (unless the caller explicitly passes push=False, e.g. for
    testing). A no-origin project keeps deferring to `auto_push` as before.
    """
    if not is_c_level(role):
        raise PermissionError(f"only C-level can merge. got: {role}")

    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"task not found: {task_id}")
    if task["status"] not in ("review", "done"):
        raise GitOpsError(f"task {task_id} not in review/done state (got {task['status']})")

    proj = get_project(task["project"])
    base = proj["default_branch"]
    branch = task["branch"] or branch_name(task["role"], task_id)
    worktree = task.get("worktree")
    host = self_host()
    repo = Path(_repo_path_for_host(proj, host))
    has_origin = bool(proj.get("remote"))

    if has_origin:
        _run(["git", "fetch", "origin", base], cwd=repo)
    base_ref = f"origin/{base}" if has_origin else base

    merge_ref = _resolve_merge_ref(repo, branch)

    if worktree and not override_touches_check:
        try:
            declared_touches = json.loads(task.get("touches") or "[]")
        except (TypeError, json.JSONDecodeError):
            declared_touches = []
        if declared_touches:
            if Path(worktree).exists():
                extra = _touches_violation(worktree, base_ref, declared_touches)
            else:
                # Remote worker: its worktree is on another box. Diff the
                # fetched ref inside the hub clone instead of silently
                # skipping the gate (the old call raised inside _run and
                # returned [] -- no gate at all for winbox tasks).
                extra = _touches_violation(str(repo), base_ref, declared_touches,
                                           ref=merge_ref)
            if extra:
                shown = extra[:20]
                msg = (f"branch {branch} changed {len(extra)} file(s) outside declared "
                       f"touches {declared_touches}: {shown}"
                       + (f" ... (+{len(extra) - 20} more)" if len(extra) > 20 else "") +
                       ". Refusing to merge — review with review_diff, then either "
                       "narrow the branch or retry merge_task with override_touches_check=True.")
                warn(f"touches violation on {task_id}: {msg}")
                db.update_status(
                    task_id, "review", actor="cto",
                    review=json.dumps({"touches_violation": True, "extra_files": extra,
                                       "declared_touches": declared_touches}),
                )
                return {"merged": False, "touches_violation": True, "extra_files": extra,
                        "declared_touches": declared_touches, "branch": branch, "base": base,
                        "project": proj["key"]}

    gate = gate_tests or bool(proj.get("gate_tests"))
    test_cmd = proj.get("test_command")
    if gate and test_cmd and worktree:
        # Safety net: a bare worktree (no gitignored node_modules/.env) would
        # false-fail every dep/env-dependent test. Normally provisioned at
        # worktree creation; re-ensure here for pre-existing worktrees. Idempotent.
        provisioned = provision_worktree(repo, Path(worktree))
        if provisioned:
            info(f"gate_tests: provisioned {provisioned} into worktree")
        info(f"gate_tests: running `{test_cmd}` in {worktree}")
        rc, out = _run_shell(test_cmd, cwd=worktree)
        if rc != 0:
            tail = "\n".join(out.splitlines()[-60:])
            warn(f"gate_tests FAILED ({rc}) — reopening task")
            db.update_status(
                task_id, "pending",
                description=(task["description"] +
                             f"\n\n## CTO Test Gate FAILED (iter {task['iteration']+1})\n"
                             f"`{test_cmd}` exit={rc}\n\n```\n{tail}\n```"),
                iteration=task["iteration"] + 1,
                assigned_agent=None,
                actor="cto",
            )
            return {"merged": False, "gate_tests": "failed",
                    "exit_code": rc, "tail": tail[:1000]}
        success(f"gate_tests passed ({test_cmd})")

    # ADR 0030 / Work/RULES.md rule 6 — `work_dir` scope only (task-36aaa3c4).
    # This is BOTH "the close gate" and "the done path" the task brief
    # names separately: the two merge paths below (_merge_local,
    # _merge_via_temp_worktree) are the only call sites in the codebase that
    # ever write status='done' (grepped "done" across tools/ lib/ runners/
    # — merge_task is it), so gating here covers both.
    # Run before any git mutation (same pre-flight shape as the
    # touches-violation check above) so a refusal has zero git state to
    # undo. Out-of-scope owner_cto: unchanged, this block never runs.
    if _scope_applies("work_dir", task.get("owner_cto")):
        work_folder = workdir.folder_path(task_id)
        if work_folder.exists():
            close_result = workdir.close(task_id, by="cto")
            if not close_result.get("closed"):
                unfiled = close_result.get("unfiled", [])
                msg = (f"Work/{task_id}/ still holds {len(unfiled)} unfiled "
                       f"file(s) — refusing to merge until they are filed "
                       f"(Assets via ALL_Rules_HQ_Filing, or Drive via CXO_Rules_GDrive_Filing): "
                       f"{unfiled[:20]}")
                warn(f"close gate blocked {task_id}: {msg}")
                db.update_status(
                    task_id, "review", actor="cto",
                    review=json.dumps({"work_dir_unfiled": True, "unfiled": unfiled}),
                )
                return {"merged": False, "work_dir_unfiled": True, "unfiled": unfiled,
                        "branch": branch, "base": base, "project": proj["key"]}

    if not has_origin:
        return _merge_local(task_id, task, proj, repo, base, branch, merge_ref,
                            worktree, strategy, push, cleanup, host)

    return _merge_via_temp_worktree(task_id, task, proj, repo, base, branch,
                                    merge_ref, worktree, strategy, push,
                                    cleanup, host)


def _merge_local(task_id: str, task: dict, proj: dict, repo: Path, base: str,
                 branch: str, merge_ref: str, worktree: str | None,
                 strategy: str, push: bool | None, cleanup: bool,
                 host: str) -> dict:
    """Original merge path: no origin remote, merge directly in `repo`.

    Unchanged from before Org Mesh W0.2 (task brief item 3, byte-for-byte)
    except for the additive `host`/`runtime_updated`/`runtime_reason` result
    fields every merge_task caller can now rely on regardless of path.
    """
    info(f"merging {branch} → {base} on {proj['key']}")
    _run(["git", "checkout", base], cwd=repo)
    try:
        _run(["git", "pull", "--ff-only", "origin", base], cwd=repo)
    except GitOpsError:
        pass

    # Pre-flight: a dirty base worktree (another concurrent session mid-edit)
    # makes `git merge` fail with "local changes would be overwritten" — a
    # transient, local, self-resolving condition, not a real content conflict.
    # Catching it here (issue #42) means we never even attempt the merge, so
    # there's nothing to misreport as conflict:true with an empty file list.
    dirty = _run(["git", "status", "--porcelain"], cwd=repo)
    if dirty:
        branch_paths = set(
            _run(["git", "diff", "--name-only", f"{base}...{merge_ref}"], cwd=repo).splitlines()
        )
        blocking, ignored = _blocking_dirty_paths(dirty, branch_paths)
        if ignored:
            info(f"merge pre-flight on {task_id}: ignoring {len(ignored)} untracked "
                 f"path(s) in base the branch does not touch: {ignored[:5]}")
    if dirty and blocking:
        dirty_files = blocking
        msg = (f"base repo working tree is dirty ({len(dirty_files)} file(s)) — "
               f"refusing to attempt merge. Likely a concurrent session mid-edit; "
               f"wait for it to finish, then retry merge_task.")
        warn(f"merge pre-flight on {task_id}: {msg}")
        db.update_status(
            task_id, "review", actor="cto",
            review=json.dumps({"base_dirty": True, "files": dirty_files}),
        )
        return {"merged": False, "base_dirty": True, "files": dirty_files,
                "branch": branch, "base": base, "project": proj["key"]}

    # Capture pre-merge HEAD so we can verify the merge actually advances base.
    pre_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)

    # Guard: if the branch is already contained in base, `git merge` is a silent
    # no-op ("Already up to date", exit 0). Without this guard the no-op was
    # reported as merged=true (line below hardcoded it) AND triggered destructive
    # cleanup (delete branch + worktree) while nothing landed — losing the work.
    # An ancestor branch means it carries no new commits (stale/empty/wrong ref).
    if _is_ancestor(repo, merge_ref, "HEAD"):
        msg = (f"branch {branch} is already an ancestor of {base} at "
               f"{pre_sha[:8]} — nothing to merge (empty/stale branch ref?). "
               f"Refusing to report success; branch + worktree preserved for retry.")
        error(f"merge no-op on {task_id}: {msg}")
        db.update_status(
            task_id, "review", actor="cto",
            review=json.dumps({"merge_error": msg, "branch": branch, "base": base}),
        )
        return {"merged": False, "no_op": True, "reason": msg,
                "branch": branch, "base": base, "project": proj["key"]}

    merge_args = ["git", "merge", "--no-ff" if strategy == "no-ff" else "--ff",
                  "-m", f"Merge {branch} (task {task_id})", merge_ref]
    try:
        _run(merge_args, cwd=repo)
    except GitOpsError as merge_err:
        conflicts = _conflict_files(repo)
        try:
            _run(["git", "merge", "--abort"], cwd=repo)
        except GitOpsError:
            pass

        # conflicts empty = git aborted before creating any unmerged (U)
        # entries — NOT a real content conflict (e.g. a race that slipped
        # past the pre-flight dirty check above). Reporting conflict:true
        # with files:[] sent reviewers hunting for conflicts that don't
        # exist (issue #42) and auto-filed a noise issue for a transient,
        # self-resolving condition. Surface the raw git error instead; no
        # issue, status back to review (not conflict) so a plain retry works.
        if not conflicts:
            msg = str(merge_err)[:1500]
            warn(f"merge failed on {task_id} with no conflict markers "
                 f"(not a content conflict): {msg}")
            db.update_status(
                task_id, "review", actor="cto",
                review=json.dumps({"merge_error": msg}),
            )
            return {"merged": False, "conflict": False, "merge_error": msg,
                    "branch": branch, "base": base, "project": proj["key"]}

        body = (
            f"Merge of `{branch}` into `{base}` for task `{task_id}` "
            f"failed with conflicts.\n\n"
            f"**Conflicting files** ({len(conflicts)}):\n" +
            "\n".join(f"- `{f}`" for f in conflicts) +
            f"\n\n**Worktree**: `{worktree}`\n"
            f"**Error**:\n```\n{str(merge_err)[:1500]}\n```\n\n"
            "Resolve manually, then re-run merge_task."
        )
        issue_url = ""
        try:
            from tools.gh_issue import create_issue
            issue_url = create_issue(
                proj["key"],
                f"merge conflict: {branch} → {base}",
                body,
                labels=["merge-conflict", "agent"],
            )
        except Exception as e:
            warn(f"gh issue creation failed: {e}")
        db.update_status(
            task_id, "conflict", actor="cto",
            review=json.dumps({"conflicts": conflicts, "issue": issue_url,
                               "error": str(merge_err)[:1000]}),
        )
        error(f"merge conflict on {task_id}: {len(conflicts)} files. issue: {issue_url or '(none)'}")
        return {"merged": False, "conflict": True, "files": conflicts,
                "issue": issue_url}

    # Verify the merge actually advanced base. A no-ff merge of a branch with
    # new commits always creates a new commit; if HEAD is unchanged the merge
    # silently did nothing — fail loudly instead of reporting success + cleaning.
    merge_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    if merge_sha == pre_sha:
        msg = (f"merge of {branch} did not advance {base} (HEAD still "
               f"{pre_sha[:8]}). Aborting without cleanup; branch preserved.")
        error(f"merge no-op on {task_id}: {msg}")
        db.update_status(
            task_id, "review", actor="cto",
            review=json.dumps({"merge_error": msg, "branch": branch, "base": base}),
        )
        return {"merged": False, "no_op": True, "reason": msg,
                "branch": branch, "base": base, "project": proj["key"]}

    dropped = _drop_channel_files(repo, pre_sha)
    if dropped:
        info(f"dropped worker channel file(s) from {base}: {dropped}")

    result = {"merged": True, "branch": branch, "base": base, "project": proj["key"],
              "merge_sha": merge_sha, "host": host, "runtime_updated": True,
              "runtime_reason": None}

    do_push = push if push is not None else proj.get("auto_push", False)
    if do_push:
        push_result = _push_base(repo, base, merge_sha)
        result.update(push_result)
        if push_result["pushed"]:
            note = " (integrated remote changes first)" if push_result.get("integrated") else ""
            success(f"pushed {base} on {proj['key']}{note}")
        else:
            error(f"{push_result['push_error']} ({proj['key']})")
    else:
        result["pushed"] = False
        result["on_origin"] = False

    # Auto-deploy: fire-and-capture; never raise — merge result always preserved.
    auto = proj.get("auto_deploy") or {}
    deploy_result: dict = {"deployed": False, "reason": "no auto_deploy config"}

    if auto.get("enabled"):
        if auto.get("requires_ceo_ack"):
            deploy_result = {"deployed": False, "reason": "awaiting_ceo_ack",
                             "command": auto.get("command", "")}
            info(f"auto_deploy: awaiting CEO ack for {proj['key']}")
        else:
            cmd = auto.get("command", "")
            timeout = int(auto.get("timeout_seconds", 60))
            info(f"auto_deploy: running command for {proj['key']} (timeout={timeout}s)")
            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=timeout
                )
                deploy_result = {
                    "deployed": proc.returncode == 0,
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:],
                    "rc": proc.returncode,
                }
                if proc.returncode == 0:
                    success(f"auto_deploy: succeeded for {proj['key']}")
                else:
                    error(f"auto_deploy: failed rc={proc.returncode} for {proj['key']}")
            except subprocess.TimeoutExpired:
                deploy_result = {"deployed": False, "reason": "timeout",
                                 "timeout_seconds": timeout}
                error(f"auto_deploy: timeout ({timeout}s) for {proj['key']}")

    result["deploy"] = deploy_result

    if cleanup:
        try:
            remove_worktree(task["project"], task["role"], task_id, delete_branch=True)
            result["cleaned"] = True
        except Exception as e:
            result["cleaned"] = False
            result["cleanup_error"] = str(e)[:300]

    db.update_status(
        task_id, "done", actor="cto",
        report=(task.get("report") or "") + f"\n\n## Merge\n{result}",
        review=json.dumps({"merge_sha": merge_sha, "branch": branch,
                           "base": base}),
    )

    try:
        reap = close_dev(task_id, reason="merge_task")
        result["tab_closed"] = reap["closed_tab"]
        result["dev_reap"] = reap
    except Exception as e:
        # A reap problem must never fail the merge — it already landed.
        result["tab_closed"] = False
        result["tab_close_error"] = str(e)[:300]

    return result


def _merge_via_temp_worktree(task_id: str, task: dict, proj: dict, repo: Path,
                             base: str, branch: str, merge_ref: str,
                             worktree: str | None, strategy: str,
                             push: bool | None, cleanup: bool, host: str) -> dict:
    """Org Mesh W0.2: merge in a throwaway detached worktree of `origin/<base>`
    so the merge never depends on this host's live runtime checkout — then
    push, then best-effort fast-forward that checkout in place.

    Every gate the local path has (no-op guard, conflict handling, channel-
    file drop) runs the same way here, just scoped to the temp worktree
    instead of `repo`'s own working directory. The touches-check, gate_tests
    and Work/ close gates already ran in merge_task before this is called.
    """
    info(f"merging {branch} → {base} on {proj['key']} (temp worktree, host={host})")

    tmp_dir = _create_temp_worktree(repo, f"origin/{base}", prefix=f"mergewt-{task_id}-")
    try:
        pre_sha = _run(["git", "rev-parse", "HEAD"], cwd=tmp_dir)

        # Same no-op guard as the local path: an already-merged branch is a
        # silent "Already up to date" from `git merge`, not a real merge.
        if _is_ancestor(tmp_dir, merge_ref, "HEAD"):
            msg = (f"branch {branch} is already an ancestor of {base} at "
                   f"{pre_sha[:8]} — nothing to merge (empty/stale branch ref?). "
                   f"Refusing to report success; branch + worktree preserved for retry.")
            error(f"merge no-op on {task_id}: {msg}")
            db.update_status(
                task_id, "review", actor="cto",
                review=json.dumps({"merge_error": msg, "branch": branch, "base": base}),
            )
            return {"merged": False, "no_op": True, "reason": msg,
                    "branch": branch, "base": base, "project": proj["key"], "host": host}

        merge_args = ["git", "merge", "--no-ff" if strategy == "no-ff" else "--ff",
                      "-m", f"Merge {branch} (task {task_id})", merge_ref]
        try:
            _run(merge_args, cwd=tmp_dir)
        except GitOpsError as merge_err:
            conflicts = _conflict_files(tmp_dir)
            try:
                _run(["git", "merge", "--abort"], cwd=tmp_dir)
            except GitOpsError:
                pass

            if not conflicts:
                msg = str(merge_err)[:1500]
                warn(f"merge failed on {task_id} with no conflict markers "
                     f"(not a content conflict): {msg}")
                db.update_status(
                    task_id, "review", actor="cto",
                    review=json.dumps({"merge_error": msg}),
                )
                return {"merged": False, "conflict": False, "merge_error": msg,
                        "branch": branch, "base": base, "project": proj["key"], "host": host}

            body = (
                f"Merge of `{branch}` into `{base}` for task `{task_id}` "
                f"failed with conflicts.\n\n"
                f"**Conflicting files** ({len(conflicts)}):\n" +
                "\n".join(f"- `{f}`" for f in conflicts) +
                f"\n\n**Worktree**: `{worktree}`\n"
                f"**Error**:\n```\n{str(merge_err)[:1500]}\n```\n\n"
                "Resolve manually, then re-run merge_task."
            )
            issue_url = ""
            try:
                from tools.gh_issue import create_issue
                issue_url = create_issue(
                    proj["key"],
                    f"merge conflict: {branch} → {base}",
                    body,
                    labels=["merge-conflict", "agent"],
                )
            except Exception as e:
                warn(f"gh issue creation failed: {e}")
            db.update_status(
                task_id, "conflict", actor="cto",
                review=json.dumps({"conflicts": conflicts, "issue": issue_url,
                                   "error": str(merge_err)[:1000]}),
            )
            error(f"merge conflict on {task_id}: {len(conflicts)} files. issue: {issue_url or '(none)'}")
            return {"merged": False, "conflict": True, "files": conflicts,
                    "issue": issue_url}

        merge_sha = _run(["git", "rev-parse", "HEAD"], cwd=tmp_dir)
        if merge_sha == pre_sha:
            msg = (f"merge of {branch} did not advance {base} (HEAD still "
                   f"{pre_sha[:8]}). Aborting without cleanup; branch preserved.")
            error(f"merge no-op on {task_id}: {msg}")
            db.update_status(
                task_id, "review", actor="cto",
                review=json.dumps({"merge_error": msg, "branch": branch, "base": base}),
            )
            return {"merged": False, "no_op": True, "reason": msg,
                    "branch": branch, "base": base, "project": proj["key"], "host": host}

        dropped = _drop_channel_files(tmp_dir, pre_sha)
        if dropped:
            info(f"dropped worker channel file(s) from {base}: {dropped}")

        # Task brief item 4: on an origin project, a merge always pushes
        # regardless of `auto_push` (that flag now only means "a worker may
        # not push its own branch directly"). push=False stays available for
        # tests that need to inspect a landed-but-not-pushed merge.
        do_push = push if push is not None else True
        if do_push:
            push_result = _push_base(tmp_dir, base, merge_sha)
        else:
            push_result = {"pushed": False, "on_origin": False}
    finally:
        _remove_temp_worktree(repo, tmp_dir)

    result = {"merged": True, "branch": branch, "base": base, "project": proj["key"],
              "merge_sha": merge_sha, "host": host}
    result.update(push_result)
    if push_result.get("pushed"):
        note = " (integrated remote changes first)" if push_result.get("integrated") else ""
        success(f"pushed {base} on {proj['key']}{note}")
    elif "push_error" in push_result:
        error(f"{push_result['push_error']} ({proj['key']})")

    if push_result.get("pushed"):
        ff_result = _ff_runtime_checkout(repo, base)
    else:
        ff_result = {"runtime_updated": False, "runtime_reason": "not pushed"}
    if not ff_result["runtime_updated"]:
        warn(f"runtime checkout on {host} not fast-forwarded for {proj['key']}: "
             f"{ff_result.get('runtime_reason')}")
    result.update(ff_result)

    # Auto-deploy acts on the runtime checkout — never fire it against one
    # that wasn't actually advanced.
    auto = proj.get("auto_deploy") or {}
    deploy_result: dict = {"deployed": False, "reason": "no auto_deploy config"}
    if auto.get("enabled"):
        if not ff_result["runtime_updated"]:
            deploy_result = {"deployed": False,
                             "reason": "runtime_updated=false, skipping deploy"}
        elif auto.get("requires_ceo_ack"):
            deploy_result = {"deployed": False, "reason": "awaiting_ceo_ack",
                             "command": auto.get("command", "")}
            info(f"auto_deploy: awaiting CEO ack for {proj['key']}")
        else:
            cmd = auto.get("command", "")
            timeout = int(auto.get("timeout_seconds", 60))
            info(f"auto_deploy: running command for {proj['key']} (timeout={timeout}s)")
            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=timeout
                )
                deploy_result = {
                    "deployed": proc.returncode == 0,
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:],
                    "rc": proc.returncode,
                }
                if proc.returncode == 0:
                    success(f"auto_deploy: succeeded for {proj['key']}")
                else:
                    error(f"auto_deploy: failed rc={proc.returncode} for {proj['key']}")
            except subprocess.TimeoutExpired:
                deploy_result = {"deployed": False, "reason": "timeout",
                                 "timeout_seconds": timeout}
                error(f"auto_deploy: timeout ({timeout}s) for {proj['key']}")
    result["deploy"] = deploy_result

    if cleanup:
        try:
            remove_worktree(task["project"], task["role"], task_id, delete_branch=True)
            result["cleaned"] = True
        except Exception as e:
            result["cleaned"] = False
            result["cleanup_error"] = str(e)[:300]

    db.update_status(
        task_id, "done", actor="cto",
        report=(task.get("report") or "") + f"\n\n## Merge\n{result}",
        review=json.dumps({"merge_sha": merge_sha, "branch": branch,
                           "base": base}),
    )

    try:
        reap = close_dev(task_id, reason="merge_task")
        result["tab_closed"] = reap["closed_tab"]
        result["dev_reap"] = reap
    except Exception as e:
        # A reap problem must never fail the merge — it already landed.
        result["tab_closed"] = False
        result["tab_close_error"] = str(e)[:300]

    return result
