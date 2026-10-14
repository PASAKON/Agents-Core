"""Git worktree per task. Each DEV works in own isolated dir on dedicated branch."""
from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from lib.config import get_project, project_path_for_host, self_host

ROOT = Path(__file__).resolve().parent.parent
WORKTREE_DIR = ROOT / "worktrees"
STORAGE_POLICY = ROOT / "config" / "storage-policy.yaml"


class GitError(Exception):
    pass


def _load_storage_policy() -> dict:
    """Tiny private loader for config/storage-policy.yaml (ADR 0030). A
    shared tools/storage_policy.py loader is being built separately — do
    not create/import it here (task brief); this stays a one-off private
    read scoped to this module."""
    try:
        return yaml.safe_load(STORAGE_POLICY.read_text()) or {}
    except OSError:
        return {}


def _sparse_worktree_policy() -> dict:
    return _load_storage_policy().get("sparse_worktree") or {}


def _media_guard_extensions() -> set[str]:
    """Reused, not duplicated: `sparse_worktree` filters by the same media
    extensions `media_guard` already declares (CTO reopen feedback,
    task-bfa778ab iter1)."""
    exts = (_load_storage_policy().get("media_guard") or {}).get("extensions") or []
    return {str(e).lower() for e in exts}


def _escape_sparse_pattern(path: str) -> str:
    """Escape `path` for use as the tail of a non-cone gitignore-style
    sparse-checkout negation line ("!/" + this). Backslash-escapes: a
    leading `!` or `#` (line-start comment/negation meaning), `*`/`?`/`[`
    wherever they occur (glob metacharacters), and trailing spaces
    (gitignore strips unescaped trailing whitespace). Paths with Thai
    characters pass through unchanged — only ASCII metacharacters above
    are special to gitignore pattern syntax."""
    out = []
    for i, ch in enumerate(path):
        if ch in ("*", "?", "["):
            out.append("\\" + ch)
        elif i == 0 and ch in ("!", "#"):
            out.append("\\" + ch)
        else:
            out.append(ch)
    escaped = "".join(out)
    stripped = escaped.rstrip(" ")
    n_trailing = len(escaped) - len(stripped)
    if n_trailing:
        escaped = stripped + ("\\ " * n_trailing)
    return escaped


def _large_tracked_media(repo: Path, start_point: str, min_bytes: int,
                         extensions: set[str]) -> list[str]:
    """Exact repo-relative paths of tracked files at `start_point` larger
    than `min_bytes` with a `media_guard.extensions` extension. `-z` NUL-
    terminates records so filenames with spaces/Thai characters parse
    correctly (never split a path on whitespace)."""
    r = subprocess.run(
        ["git", "ls-tree", "-r", "-l", "-z", start_point],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8",
    )
    if r.returncode != 0:
        raise GitError(f"git ls-tree -r -l -z {start_point}\n{r.stderr}")

    out: list[str] = []
    for record in r.stdout.split("\0"):
        if not record:
            continue
        meta, sep, path = record.partition("\t")
        if not sep:
            continue
        fields = meta.split()
        if len(fields) < 4:
            continue
        try:
            size = int(fields[3])
        except ValueError:
            continue
        if size <= min_bytes:
            continue
        basename = path.rsplit("/", 1)[-1]
        ext = basename.rsplit(".", 1)[-1].lower() if "." in basename else ""
        if ext in extensions:
            out.append(path)
    return out


def _run(cmd: list[str], cwd: str | Path | None = None) -> str:
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise GitError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()


def sparse_exclusions(repo: Path, start_point: str, role: str) -> list[str]:
    """Exact repo-relative paths a sparse worktree of `role` leaves off disk:
    tracked files at `start_point` above `sparse_worktree.min_bytes` with a
    `media_guard.extensions` extension, minus `keep_paths` (CTO 3d312dd6
    review, 2026-09-23: workers read reference media outside their touches
    -- skills' templates, prototypes, knowledge/ design references -- so
    those stay on disk). Empty for a `full_checkout_roles` role (e.g.
    video_editor) and when the policy sets no `min_bytes`/extensions."""
    policy = _sparse_worktree_policy()
    min_bytes = policy.get("min_bytes")
    if role in set(policy.get("full_checkout_roles") or []) or not min_bytes:
        return []
    extensions = _media_guard_extensions()
    if not extensions:
        return []
    large_media = _large_tracked_media(repo, start_point, int(min_bytes), extensions)
    keep = [str(g) for g in (policy.get("keep_paths") or [])]
    if keep:
        large_media = [p for p in large_media
                       if not any(fnmatch.fnmatch(p, g) for g in keep)]
    return large_media


def apply_sparse(repo: Path, wt: Path, start_point: str, role: str) -> list[str]:
    """Sparse step shared by every worktree spawn path (ADR 0030): create_worktree,
    restore_worktree and scripts/spawn-worker-remote.sh (via the CLI below).

    Call it on a worktree added with `git worktree add --no-checkout`, BEFORE
    the checkout; the caller then runs `git checkout <branch>` in `wt`. Returns
    the excluded paths. Empty = nothing to exclude: NOTHING was written, so
    that checkout is a plain full one.

    Excludes by EXACT PATH, never by directory. A directory-level exclude was
    tried and reverted: git refuses `git add -A` for any NEW file under an
    excluded directory ("paths ... outside of your sparse-checkout
    definition", exit 1), which would break nearly every browser_operator
    commit under docs/reports (see storage-policy.yaml's comment for the
    measurement). Exact paths keep every directory inside the sparse
    definition, so a brand-new file anywhere is always addable. The sparse
    config is written into THIS worktree's own git-dir
    (extensions.worktreeConfig + per-worktree scope) -- never the main
    checkout's, which stays untouched.

    On a git failure part-way, sparse-checkout is switched back off before the
    error is re-raised: `sparse-checkout init --no-cone` alone leaves the
    default root-files-only pattern, so a caller that fell back to a plain
    checkout would otherwise get a worktree holding the top-level files only."""
    excluded = sparse_exclusions(repo, start_point, role)
    if not excluded:
        return []
    try:
        # Once set it stays set; skipping the write keeps spawns that start
        # together from fighting over the repo's config lock.
        cur = subprocess.run(["git", "config", "--get", "extensions.worktreeConfig"],
                             cwd=str(repo), capture_output=True, text=True)
        if cur.stdout.strip() != "true":
            _run(["git", "config", "extensions.worktreeConfig", "true"], cwd=repo)
        _run(["git", "sparse-checkout", "init", "--no-cone"], cwd=wt)
        patterns = ["/*"] + [f"!/{_escape_sparse_pattern(p)}" for p in excluded]
        _run(["git", "sparse-checkout", "set", "--no-cone", *patterns], cwd=wt)
    except Exception:
        subprocess.run(["git", "sparse-checkout", "disable"], cwd=str(wt),
                       capture_output=True, text=True)
        raise
    return excluded


def _checkout_sparse_or_full(repo: Path, wt: Path, branch: str, start_point: str,
                             role: str) -> None:
    """apply_sparse, then check `branch` out in `wt` (added with --no-checkout).
    A sparse step that fails costs disk, never the spawn: warn on stderr and
    check the whole tree out instead."""
    try:
        apply_sparse(repo, wt, start_point, role)
    except Exception as e:  # noqa: BLE001 - any failure here must not fail the spawn
        print(f"worktree: sparse step failed ({type(e).__name__}); full checkout "
              f"instead: {str(e).strip()[:300]}", file=sys.stderr)
    _run(["git", "checkout", branch], cwd=wt)


def worktree_path(project_key: str, role: str, task_id: str) -> Path:
    safe = project_key.replace("/", "_").replace(" ", "_")
    return WORKTREE_DIR / f"{safe}__{role}__{task_id}"


def branch_name(role: str, task_id: str) -> str:
    return f"agent/{role}-{task_id}"


def provision_worktree(repo: Path, wt: Path) -> list[str]:
    """Symlink gitignored runtime deps from the canonical repo into a worktree.

    A worktree only contains git-tracked files. `node_modules` and `.env` are
    gitignored, so a bare worktree fails every dependency/env-dependent command
    — including `merge_task`'s gate_tests, which runs the project test_command
    with cwd=worktree (confirmed 2026-07-19: a valid single-file SQL branch was
    false-failed because its worktree had neither node_modules nor .env). Symlink
    rather than copy → no secret duplication, stays consistent with the source,
    and is discarded automatically when the worktree is removed. Idempotent;
    silently skips whatever the canonical repo does not have.
    """
    names = ("node_modules", ".env")
    # Opt-out for repos whose .env holds keys that spend money on their own
    # (RunPod, image/LLM APIs): a marker file in the canonical repo keeps the
    # real .env out of every worktree. Measured 2026-09-26 on ComfyRunpod: a
    # worker's "offline" test reached the live key through this symlink and
    # made 2 paid calls, and the app lets .env override the fake keys a test
    # sets in its environment (task-e59b65e3).
    link_names = names if not (repo / ".worktree-no-env").exists() else ("node_modules",)
    linked: list[str] = []
    for name in link_names:
        src = repo / name
        dst = wt / name
        if src.exists() and not dst.exists():
            try:
                dst.symlink_to(src)
                linked.append(name)
            except OSError:
                pass
    # A repo whose .gitignore uses a dir-only pattern (`node_modules/`) does NOT
    # ignore a *symlink* named node_modules, so a DEV's mandatory `git add -A`
    # would commit the provisioning symlink (an absolute host path) into the
    # branch. Anchor both names in the worktree's own git exclude so they can
    # never be staged, regardless of the repo's .gitignore style.
    _exclude_in_worktree(wt, names)
    return linked


def _exclude_in_worktree(wt: Path, names: tuple[str, ...]) -> None:
    """Append anchored ignore entries to this worktree's git exclude file.

    Uses `git rev-parse --git-path info/exclude` so it resolves correctly for a
    linked worktree. Idempotent; best-effort (silently skips if git can't
    resolve the path, e.g. a non-git temp dir in tests)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(wt), "rev-parse", "--git-path", "info/exclude"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return
        exclude = Path(r.stdout.strip())
        if not exclude.is_absolute():
            exclude = wt / exclude
        exclude.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude.read_text() if exclude.exists() else ""
        add = [f"/{n}" for n in names if f"/{n}" not in existing.split()]
        if add:
            with exclude.open("a") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("\n".join(add) + "\n")
    except OSError:
        pass


def _repo_path(project_key: str) -> Path:
    """The project's checkout on THIS machine (`paths.<self_host()>`).

    The top-level `path:` is the Mac checkout; on any other host it points at a
    directory that does not exist, so it must never be used there."""
    return Path(project_path_for_host(project_key, self_host()))


def restore_worktree(project_key: str, role: str, task_id: str, *,
                     path: str | None = None, branch: str | None = None,
                     sparse: bool = False) -> dict | None:
    """Restore a missing checkout without deleting its unmerged branch.

    `sparse=True` applies the same exclusion as create_worktree, measured on
    the branch tip (ADR 0030)."""
    repo = _repo_path(project_key)
    branch = branch or branch_name(role, task_id)
    result = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                            cwd=str(repo), capture_output=True, text=True)
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise GitError(result.stderr)
    wt = Path(path) if path else worktree_path(project_key, role, task_id)
    wt.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "prune"], cwd=repo)
    if sparse:
        _run(["git", "worktree", "add", "--no-checkout", str(wt), branch], cwd=repo)
        _checkout_sparse_or_full(repo, wt, branch, branch, role)
    else:
        _run(["git", "worktree", "add", str(wt), branch], cwd=repo)
    provision_worktree(repo, wt)
    return {"worktree": str(wt), "branch": branch}


def create_worktree(project_key: str, role: str, task_id: str, *,
                    sparse: bool = False) -> dict:
    """Create isolated worktree on new branch from default branch.

    `sparse=True` excludes large tracked media (ADR 0030). Off by default:
    delegate turns it on only for tasks in the storage pilot
    (`pilot_owner_cto`, CEO 2026-09-23 — own work first)."""
    proj = get_project(project_key)
    repo = _repo_path(project_key)
    base = proj["default_branch"]
    branch = branch_name(role, task_id)
    wt = worktree_path(project_key, role, task_id)

    WORKTREE_DIR.mkdir(parents=True, exist_ok=True)

    # ensure base branch exists locally + fetch if remote tracked
    try:
        _run(["git", "fetch", "origin", base], cwd=repo)
    except GitError:
        pass

    # remove stale worktree if any
    if wt.exists():
        try:
            _run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo)
        except GitError:
            shutil.rmtree(wt, ignore_errors=True)

    # delete stale branch if exists
    try:
        _run(["git", "branch", "-D", branch], cwd=repo)
    except GitError:
        pass

    # Branch from the freshly-fetched remote tip (origin/<base>) rather than
    # the local <base> ref. Local <base> is never fast-forwarded here, so it
    # drifts behind / diverges from origin — which made DEV branches build on
    # a stale lineage and every resulting PR unmergeable (modify/delete
    # conflicts vs the real remote main). Fall back to local <base> only when
    # there is no remote-tracking ref (e.g. a repo with no origin yet).
    start_point = base
    try:
        _run(["git", "rev-parse", "--verify", f"origin/{base}"], cwd=repo)
        start_point = f"origin/{base}"
    except GitError:
        pass

    # Sparse worktrees (ADR 0030, storage-policy.yaml `sparse_worktree`): off
    # unless the caller asks (delegate resolves the per-owner scope). The
    # exclusion rules live in apply_sparse, shared with restore_worktree and
    # scripts/spawn-worker-remote.sh.
    if sparse:
        _run(["git", "worktree", "add", "--no-checkout", "-b", branch, str(wt),
              start_point], cwd=repo)
        _checkout_sparse_or_full(repo, wt, branch, start_point, role)
    else:
        _run(["git", "worktree", "add", "-b", branch, str(wt), start_point], cwd=repo)

    # Bare worktrees lack gitignored runtime deps (node_modules/.env) so the DEV
    # — and the merge gate_tests — can't run anything env/dep-dependent. Symlink
    # them in from the canonical repo.
    provisioned = provision_worktree(repo, wt)

    return {
        "project": project_key,
        "task_id": task_id,
        "role": role,
        "branch": branch,
        "worktree": str(wt),
        "base": base,
        "repo": str(repo),
        "provisioned": provisioned,
    }


def commit_worktree(worktree: str, message: str, author: str | None = None) -> dict:
    wt = Path(worktree)
    _run(["git", "add", "-A"], cwd=wt)
    status = _run(["git", "status", "--porcelain"], cwd=wt)
    if not status:
        return {"committed": False, "reason": "no changes"}
    env_msg = message
    args = ["git"]
    if author:
        args += ["-c", f"user.name={author}", "-c", f"user.email={author}@agents.local"]
    args += ["commit", "-m", env_msg]
    _run(args, cwd=wt)
    sha = _run(["git", "rev-parse", "HEAD"], cwd=wt)
    return {"committed": True, "sha": sha[:12], "message": env_msg}


def diff_summary(worktree: str, base: str) -> str:
    wt = Path(worktree)
    return _run(["git", "diff", "--stat", f"{base}...HEAD"], cwd=wt)


def diff_full(worktree: str, base: str, max_lines: int = 2000) -> str:
    wt = Path(worktree)
    out = _run(["git", "diff", f"{base}...HEAD"], cwd=wt)
    lines = out.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n... ({len(lines)-max_lines} more lines truncated)"
    return out


def remove_worktree(project_key: str, role: str, task_id: str, *, delete_branch: bool = False) -> str:
    repo = _repo_path(project_key)
    wt = worktree_path(project_key, role, task_id)
    branch = branch_name(role, task_id)
    try:
        _run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo)
    except GitError as e:
        if wt.exists():
            shutil.rmtree(wt, ignore_errors=True)
    if delete_branch:
        try:
            _run(["git", "branch", "-D", branch], cwd=repo)
        except GitError:
            pass
    return f"removed worktree {wt}"


def list_worktrees(project_key: str) -> list[str]:
    out = _run(["git", "worktree", "list", "--porcelain"], cwd=_repo_path(project_key))
    return out.splitlines()


def _main(argv: list[str] | None = None) -> int:
    """`python -m tools.worktree apply-sparse` -- the entry point
    scripts/spawn-worker-remote.sh calls between `worktree add --no-checkout`
    and the checkout. Prints `SPARSE_APPLIED excluded=<n>` on success (n=0:
    nothing excluded, nothing written); exit 1 + a stderr line on failure,
    leaving sparse-checkout off so the caller's plain checkout is a full one."""
    ap = argparse.ArgumentParser(prog="python -m tools.worktree")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("apply-sparse", help="sparse step for a --no-checkout worktree")
    p.add_argument("--repo", required=True, help="the project's own checkout")
    p.add_argument("--wt", required=True, help="the --no-checkout worktree")
    p.add_argument("--start-point", required=True, help="ref the worktree branch starts from")
    p.add_argument("--role", required=True)
    args = ap.parse_args(argv)
    try:
        excluded = apply_sparse(Path(args.repo), Path(args.wt), args.start_point, args.role)
    except Exception as e:  # noqa: BLE001 - the launcher falls back to a full checkout
        print(f"apply-sparse failed: {type(e).__name__}: {str(e).strip()[:500]}", file=sys.stderr)
        return 1
    print(f"SPARSE_APPLIED excluded={len(excluded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
