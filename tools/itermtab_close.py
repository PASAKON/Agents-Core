"""CLI entry for close_session: python -m tools.itermtab_close --role <role> --session <sid>.

Shim module so the idle-ping watcher can invoke the 4-gate close helper
without importing itermtab directly from bash.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.itermtab import close_session  # noqa: E402


def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Close an ID-locked CXO iTerm tab.")
    p.add_argument("--role", required=True, help="C-level role (cto/cmo/cgo/cfo)")
    p.add_argument("--session", required=True, help="Session ID (matches lock file name)")
    args = p.parse_args()
    ok = close_session(args.role, args.session)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
