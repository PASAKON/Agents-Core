"""Lease CLI for trusted launcher processes; all results are JSON."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import lease as api


def main(argv=None, *, service=None, actor=None):
    parser=argparse.ArgumentParser(description=__doc__,epilog=(
        "Exit codes: 0 granted/success; 2 invalid arguments/configuration; "
        "3 waiting/awaiting approval; 4 refused, stale, expired or terminal; "
        "5 hub unavailable. Trusted launcher supplies LEASE_DB_URL and "
        "LEASE_OWNER_SESSION. No client role/priority/approval flags."))
    commands=parser.add_subparsers(dest="command",required=True)
    p=commands.add_parser("acquire")
    p.add_argument("name",nargs="+")
    p.add_argument("--purpose",required=True)
    p.add_argument("--idempotency-key",default=None)
    for command in ("renew","release","status","wait"):
        p=commands.add_parser(command)
        p.add_argument("request_id")
        if command in {"renew","release"}:
            p.add_argument("--token",required=True,help="integer for one resource, or JSON object mapping group names to tokens")
        if command=="wait":
            p.add_argument("--wait-s",type=float,default=0)
    args=parser.parse_args(argv)
    try:
        if service is None:
            service,actor=api.default_service()
        if args.command=="acquire":
            result=service.acquire(args.name,actor,purpose=args.purpose,idempotency_key=args.idempotency_key)
        elif args.command in {"renew","release"}:
            result=getattr(service,args.command)(args.request_id,actor,json.loads(args.token))
        elif args.command=="wait":
            result=service.wait(args.request_id,actor,args.wait_s)
        else:
            result=service.status(args.request_id,actor)
        data=asdict(result) if isinstance(result,api.Result) else {"state":"success" if result else "refused"}
        print(json.dumps(data,sort_keys=True))
        if data.get("reason")=="hub_down":
            return 5
        return 0 if data["state"] in {"granted","success"} else 3 if data["state"] in {"waiting","awaiting_approval"} else 4
    except (ValueError,api.LeaseError) as exc:
        print(json.dumps({"state":"refused","reason":str(exc)}))
        return 2
    except Exception:
        # Connection exceptions can contain credentials; never echo them.
        print(json.dumps({"state":"refused","reason":"hub_unavailable"}))
        return 5


if __name__=="__main__":
    raise SystemExit(main())
