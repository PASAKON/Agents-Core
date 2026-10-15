#!/usr/bin/env python3
"""Does this PR touch a path another Project Head owns? (config/path-owners.yaml, lib/path_owners.py)

    python3 tools/pr_owner_check.py <PR#> --project <Name>
    python3 tools/pr_owner_check.py --files tools/a.py,docs/b.md --project <Name>

Run it before `gh pr merge` (roles/project_head.md). One line per path that matters:

    FOREIGN  tools/spend_guard.py  owned by SpendGuard
    SHARED   config/hosts.yaml     shared, tell CTO Main

A path you own or nobody owns prints nothing. stdout carries only those lines; a one-line summary goes to
stderr, so a clean run is never silent.

Exit: 0 clean (shared lines may still print) · 1 a foreign path is touched: write CTO Main kind blocker ·
2 could not check (bad arguments, `gh` failed, an unreadable owners file) - never read 2 as clean.

With a PR number the file list is read-only: `gh pr view N --json files`. gh returns at most 100 files
there, so a list of exactly 100 is re-read, paginated, from `gh api repos/<repo>/pulls/N/files`, including
each renamed file's old path (a PR that moves a path out of another project's area still touches it).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import path_owners  # noqa: E402

DEFAULT_REPO = "PASAKON/Agents-Core"   # the repo config/path-owners.yaml describes
GH_VIEW_FILE_CAP = 100                 # `gh pr view --json files` stops here, silently
GH_TIMEOUT_S = 60


class CheckError(Exception):
    """The check could not run; the caller exits 2."""


def _gh(args: list[str], runner) -> str:
    try:
        r = runner(["gh", *args], capture_output=True, text=True, timeout=GH_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CheckError(f"gh {' '.join(args[:3])}: {e}") from e
    if r.returncode != 0:
        raise CheckError(f"gh {' '.join(args[:3])} exit {r.returncode}: {(r.stderr or '').strip()[:300]}")
    return r.stdout


def pr_files(pr: str, repo: str = DEFAULT_REPO, runner=subprocess.run) -> list[str]:
    """Paths a PR changes, read-only."""
    out = _gh(["pr", "view", pr, "--repo", repo, "--json", "files"], runner)
    try:
        files = [f["path"] for f in json.loads(out)["files"]]
    except (ValueError, KeyError, TypeError) as e:
        raise CheckError(f"gh pr view {pr}: unreadable file list ({e})") from e
    if len(files) >= GH_VIEW_FILE_CAP:
        out = _gh(["api", "--paginate", f"repos/{repo}/pulls/{pr}/files?per_page=100",
                   "--jq", ".[] | .filename, (.previous_filename // empty)"], runner)
        files = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return files


def main(argv: list[str] | None = None, *, runner=subprocess.run) -> int:
    ap = argparse.ArgumentParser(prog="tools/pr_owner_check.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("pr", nargs="?", help="PR number (read with gh, read-only)")
    ap.add_argument("--files", help="comma-separated repo-relative paths, instead of a PR number")
    ap.add_argument("--project", required=True, help="your Project Head project name, e.g. OrgRestructure")
    ap.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo for a PR number (default {DEFAULT_REPO})")
    args = ap.parse_args(argv)
    if bool(args.pr) == bool(args.files):
        ap.error("give exactly one of a PR number or --files")
    if args.pr:
        args.pr = args.pr.lstrip("#")
        if not args.pr.isdigit():   # it goes into a gh argv: digits only, never a flag
            ap.error(f"PR must be a number, got {args.pr!r}")

    try:
        table = path_owners.load_table()
        files = ([f.strip() for f in args.files.split(",") if f.strip()] if args.files
                 else pr_files(args.pr, args.repo, runner))
    except Exception as e:   # gh failed, or the owners file is unreadable: never let that read as clean
        print(f"pr_owner_check: cannot check: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if not files:
        print("pr_owner_check: cannot check: no files to check", file=sys.stderr)
        return 2

    if args.project.casefold() not in {p.casefold() for p in path_owners.projects(table)}:
        print(f"pr_owner_check: note: {args.project!r} owns no paths in config/path-owners.yaml; "
              f"known: {', '.join(path_owners.projects(table))}", file=sys.stderr)

    owners = path_owners.owners_for(files, table)
    foreign = path_owners.foreign_paths(args.project, files, table)
    for path, owner in foreign:
        print(f"FOREIGN  {path}  owned by {owner}")
    shared = [p for p, o in owners.items() if o == path_owners.SHARED]
    for path in shared:
        print(f"SHARED   {path}  shared, tell CTO Main")
    print(f"pr_owner_check: {args.project}: {len(owners)} path(s), {len(foreign)} foreign, "
          f"{len(shared)} shared", file=sys.stderr)
    return 1 if foreign else 0


if __name__ == "__main__":
    sys.exit(main())
