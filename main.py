"""CEO entrypoint. Hands a request to the CTO and prints the result."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# ensure _org/ is on path so `lib.*` and `agents.*` work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from runners.cto import run as cto_run
from lib import db
from lib.notify import info


def main():
    parser = argparse.ArgumentParser(description="Mooniex CEO → CTO interface")
    parser.add_argument("request", nargs="*", help="CEO request (or stdin if empty)")
    parser.add_argument("--init", action="store_true", help="Initialize DB then exit")
    parser.add_argument("--stats", action="store_true", help="Print task stats then exit")
    args = parser.parse_args()

    if args.init:
        db.init()
        return

    if args.stats:
        print(db.stats())
        return

    if args.request:
        request = " ".join(args.request)
    else:
        print("CEO> ", end="", flush=True)
        request = sys.stdin.read().strip()

    if not request:
        print("no request given", file=sys.stderr)
        sys.exit(1)

    db.init()  # idempotent
    info(f"CEO: {request[:120]}")
    out = asyncio.run(cto_run(request))
    print("\n" + "=" * 60)
    print("CTO REPORT")
    print("=" * 60)
    print(out)


if __name__ == "__main__":
    main()
