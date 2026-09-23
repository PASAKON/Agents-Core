"""Git worktree per task. Each DEV works in own isolated dir on dedicated branch."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

from lib.config import get_project

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
    linked: list[str] = []
    for name in names:
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


def create_worktree(project_key: str, role: str, task_id: str, *,
                    sparse: bool = False) -> dict:
    """Create isolated worktree on new branch from default branch.

    `sparse=True` excludes large tracked media (ADR 0030). Off by default:
    delegate turns it on only for tasks in the storage pilot
    (`pilot_owner_cto`, CEO 2026-09-23 — own work first)."""
    proj = get_project(project_key)
    repo = Path(proj["path"])
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

    # Sparse worktrees (ADR 0030, storage-policy.yaml `sparse_worktree`).
    # A role in `full_checkout_roles` (e.g. video_editor) gets today's
    # unchanged full checkout. Otherwise, exclude only EXISTING tracked
    # files above `min_bytes` with a media extension, by EXACT PATH — never
    # a directory. A directory-level exclude was tried and reverted:
    # git refuses `git add -A` for any NEW file under an excluded directory
    # ("paths ... outside of your sparse-checkout definition", exit 1),
    # which would break nearly every browser_operator commit under
    # docs/reports (see storage-policy.yaml's comment for the measurement).
    # Excluding by exact path keeps every directory inside the sparse
    # definition, so a brand-new file anywhere is always addable. The
    # sparse config is written into THIS worktree's own git-dir
    # (extensions.worktreeConfig + per-worktree scope) — never the main
    # checkout's, which stays untouched.
    policy = _sparse_worktree_policy()
    min_bytes = policy.get("min_bytes")
    full_roles = set(policy.get("full_checkout_roles") or [])

    large_media: list[str] = []
    if sparse and role not in full_roles and min_bytes:
        extensions = _media_guard_extensions()
        if extensions:
            large_media = _large_tracked_media(repo, start_point, int(min_bytes), extensions)

    if not large_media:
        _run(["git", "worktree", "add", "-b", branch, str(wt), start_point], cwd=repo)
    else:
        _run(["git", "config", "extensions.worktreeConfig", "true"], cwd=repo)
        _run(["git", "worktree", "add", "--no-checkout", "-b", branch, str(wt),
              start_point], cwd=repo)
        _run(["git", "sparse-checkout", "init", "--no-cone"], cwd=wt)
        patterns = ["/*"] + [f"!/{_escape_sparse_pattern(p)}" for p in large_media]
        _run(["git", "sparse-checkout", "set", "--no-cone", *patterns], cwd=wt)
        _run(["git", "checkout", branch], cwd=wt)

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
    proj = get_project(project_key)
    repo = Path(proj["path"])
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
    proj = get_project(project_key)
    out = _run(["git", "worktree", "list", "--porcelain"], cwd=proj["path"])
    return out.splitlines()
