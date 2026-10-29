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
CONTABO_LIVE = Path('/opt/MoonieXHQ/Agents/Core')


def core_root() -> Path:
    return Path(os.environ.get('KIT_ROOT_CORE', Path(__file__).resolve().parents[1]))


def pull() -> int:
    for name in (*ROOTS, 'KIT_ROOT_CORE'):
        reason = None
        deadline = time.monotonic() + TIMEOUT_SECONDS
        try:
            core = name == 'KIT_ROOT_CORE'
            value = str(core_root()) if core else os.environ.get(name)
            if core and Path(value).resolve() == CONTABO_LIVE.resolve():
                reason = 'Contabo live checkout: the merge card syncs it'
            elif not value or not (Path(value) / ".git").exists():
                reason = "not a git checkout"
            else:
                def git(*args: str) -> subprocess.CompletedProcess:
                    return subprocess.run(
                        ["git", "-C", value, *args], capture_output=True,
                        text=True, timeout=max(0.001, deadline - time.monotonic()),
                        env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                             "GCM_INTERACTIVE": "Never"},
                    )

                status = git("status", "--porcelain", "--untracked-files=no" if core else "--untracked-files=normal")
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


def check() -> int:
    deadline = time.monotonic() + 9.5
    offline = ''
    try:
        root = core_root().resolve()
        if not (root / '.git').exists():
            raise ValueError('not a git checkout')

        def git(*args, budget=None):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('timed out')
            result = subprocess.run(
                ['git', '-C', str(root), *args], capture_output=True, text=True,
                timeout=min(remaining, budget or remaining),
                env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never'},
            )
            if result.returncode:
                raise ValueError('git ref unavailable')
            return result.stdout.strip()

        try:
            git('fetch', '-q', 'origin', 'main', budget=6)
        except (ValueError, subprocess.TimeoutExpired):
            offline = ' (offline)'
        behind = int(git('rev-list', '--count', 'HEAD..origin/main'))
        ahead = int(git('rev-list', '--count', 'origin/main..HEAD'))
        if behind:
            paths = git('diff', '--name-only', 'HEAD', 'origin/main', '--', '.claude/skills')
            skills = sorted({p.split('/')[2] for p in paths.splitlines()
                             if p.startswith('.claude/skills/') and len(p.split('/')) >= 4})
            names = ', '.join(skills[:8] + ([f'+{len(skills) - 8} more'] if len(skills) > 8 else [])) or 'none'
            line = (f'KIT STALE: {behind} behind origin/main; skills that differ: {names}'
                    ' — run git pull --ff-only before work that needs them')
        else:
            line = f"kit ok ({git('rev-parse', 'HEAD')[:8]} contains origin/main)"
        if ahead:
            line += (f' · {ahead} local commits wait for the hub sync' if root == CONTABO_LIVE.resolve()
                     else f' · KIT UNPUBLISHED: {ahead} local commits not on GitHub — open a PR to CTO Main')
    except FileNotFoundError:
        line = 'kit check skipped: git missing'
    except subprocess.TimeoutExpired:
        line = 'kit check skipped: timed out'
    except (OSError, ValueError) as exc:
        line = f'kit check skipped: {" ".join(str(exc).split())}'
    print(line + offline)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["pull", "check"])
    args = parser.parse_args()
    return pull() if args.command == 'pull' else check()


if __name__ == "__main__":
    raise SystemExit(main())
