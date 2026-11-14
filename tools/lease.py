"""JSON lease client for an authenticated hub-side launcher."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import lease as api


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        "Exit codes: 0 granted/success; 2 waiting/awaiting approval; "
        "3 refused/lost/terminal; 4 backend/configuration failure. "
        "Acquire is durable; wait timeout does not cancel it. Launcher must set "
        "LEASE_OWNER_SESSION. CLI holders must renew before expiry. No client role flags."))
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("acquire")
    p.add_argument("names", nargs="+")
    p.add_argument("--purpose", required=True)
    p.add_argument("--idempotency-key", required=True)
    for command in ("renew", "release"):
        p = sub.add_parser(command)
        p.add_argument("name")
        p.add_argument("request_id")
        p.add_argument("token", type=int)
    for command in ("status", "wait"):
        p = sub.add_parser(command)
        p.add_argument("request_id")
        if command == "wait":
            p.add_argument("--wait-s", type=float, default=0)
    args = parser.parse_args(argv)
    try:
        if api._configured is None:
            session = os.environ.get("LEASE_OWNER_SESSION")
            if not session:
                raise api.LeaseError("authenticated launcher identity missing")
            api.configure(api.Service(), api.Identity(session))
        if args.command == "acquire":
            result = api.acquire(args.names, purpose=args.purpose, idempotency_key=args.idempotency_key)
        elif args.command in {"renew", "release"}:
            ok = getattr(api, args.command)(args.name, args.request_id, args.token)
            result = api.Result("granted" if ok else "refused", args.request_id, args.token)
        elif args.command == "wait":
            result = api.wait(args.request_id, args.wait_s)
        else:
            result = api.status(args.request_id)
        print(json.dumps(asdict(result), default=str))
        return 0 if result.state == "granted" else 2 if result.state in api.PENDING else 3
    except Exception as exc:
        # Never print a DB exception: it may contain connection credentials.
        print(json.dumps({"state": "refused", "reason": type(exc).__name__}))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
