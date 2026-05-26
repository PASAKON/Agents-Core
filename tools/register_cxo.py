"""Register a CXO session in c_level_sessions on spawn.

Called by scripts/cxo-claude.sh after tab is up:
  python3 -m tools.register_cxo --role <role> --session <sid>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.db import register_cxo_session  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--role", required=True)
    p.add_argument("--session", required=True)
    args = p.parse_args()
    register_cxo_session(args.role, args.session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
