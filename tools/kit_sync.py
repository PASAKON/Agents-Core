"""Best-effort, fast-forward-only wiki updates before a session starts."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOTS = ("WIKI_ROOT_ORG", "WIKI_ROOT_MOONIEX")
TIMEOUT_SECONDS = 15.0


def pull() -> int:
    for name in ROOTS:
        reason = None
        deadline = time.monotonic() + TIMEOUT_SECONDS
        try:
            value = os.environ.get(name)
            if not value or not (Path(value) / ".git").exists():
                reason = "not a git checkout"
            else:
                def git(*args: str) -> subprocess.CompletedProcess:
                    return subprocess.run(
                        ["git", "-C", value, *args], capture_output=True,
                        text=True, timeout=max(0.001, deadline - time.monotonic()),
                        env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                             "GCM_INTERACTIVE": "Never"},
                    )

                status = git("status", "--porcelain", "--untracked-files=normal")
                if status.returncode:
                    reason = "cannot inspect checkout"
                elif status.stdout.strip():
                    reason = "dirty checkout"
                elif git("-c", "merge.autostash=false", "-c", "rebase.autostash=false",
                         "pull", "--ff-only", "--no-rebase").returncode:
                    reason = "pull unavailable (offline, diverged, or busy)"
        except subprocess.TimeoutExpired:
            reason = "timed out"
        except (OSError, ValueError):
            reason = "git unavailable or checkout inaccessible"
        if reason:
            print(f"[kit_sync] {name}: {reason}; using existing files", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["pull"])
    parser.parse_args()
    return pull()


if __name__ == "__main__":
    raise SystemExit(main())
