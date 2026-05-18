"""GitHub issue helper.

Used by DEVs to persist blockers as durable GitHub issues so work survives
a closed tab, sleeping mac, or dropped network. The CTO/DEV orchestration
playbook makes this mandatory for every blocker.

Usage (programmatic):
    from tools.gh_issue import create_issue
    url = create_issue(project_key, title, body)

Usage (CLI):
    python -m tools.gh_issue <project_key> "<title>" "<body>"

Requires `gh` CLI authenticated with repo scope.
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional

from lib.config import get_project


class GhError(Exception):
    pass


def _parse_repo(remote: str) -> str:
    """Extract `owner/repo` from a git remote URL (ssh or https)."""
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?$", remote.strip())
    if not m:
        raise GhError(f"cannot parse github remote: {remote}")
    return m.group(1)


def _check_auth() -> None:
    """Verify `gh` CLI is installed and authenticated. Raise loudly otherwise."""
    try:
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    except FileNotFoundError:
        raise GhError(
            "gh CLI not installed. install: brew install gh && gh auth login"
        )
    if r.returncode != 0:
        raise GhError(
            f"gh CLI not authenticated. run: gh auth login\n{r.stderr.strip()}"
        )


def create_issue(project_key: str, title: str, body: str,
                 labels: Optional[list[str]] = None) -> str:
    """Create a GitHub issue on the project's repo. Returns issue URL."""
    _check_auth()
    proj = get_project(project_key)
    remote = proj.get("remote") or ""
    if not remote:
        raise GhError(f"project {project_key} has no remote configured")
    repo = _parse_repo(remote)

    base_cmd = ["gh", "issue", "create",
                "--repo", repo,
                "--title", title,
                "--body", body]
    cmd = list(base_cmd)
    if labels:
        for lab in labels:
            cmd.extend(["--label", lab])

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        if labels and "label" in r.stderr.lower() and "not found" in r.stderr.lower():
            # one or more labels don't exist on repo — retry without labels
            r2 = subprocess.run(base_cmd, capture_output=True, text=True)
            if r2.returncode == 0:
                return r2.stdout.strip().splitlines()[-1]
        raise GhError(f"gh issue create failed: {r.stderr.strip()}")
    url = r.stdout.strip().splitlines()[-1]
    return url


def main() -> int:
    import sys
    if len(sys.argv) < 4:
        print('usage: python -m tools.gh_issue <project_key> "<title>" "<body>"',
              file=sys.stderr)
        return 1
    url = create_issue(sys.argv[1], sys.argv[2], sys.argv[3])
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
