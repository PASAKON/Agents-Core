#!/usr/bin/env python3
"""Host facts for the SomPong (COO) launchers, read through lib.config.

SomPong is one session, on Contabo only (docs/design/sompong-coo-session.md,
CEO 2026-10-01). cxo-claude.sh and spawn-coo.sh need two answers from the same
place, and neither may guess from `hostname` or `uname`:

    coo_host.py host     print this machine's registry name (mac|winbox|contabo)
    coo_host.py route    print "<ssh alias> <agents_root>" when this machine can
                         reach Contabo over ssh, exit 4 when it has no route

Exit 3 = the host could not be resolved (lib.config.self_host raised). Callers
treat that as "not Contabo": the guard fails closed.

`ssh:` in config/hosts.yaml is an alias that "must match a Host entry in
~/.ssh/config on the Mac". Only the Mac is therefore known to hold a route to
Contabo; winbox has none registered, so ROUTE_FROM stays one host until
hosts.yaml says otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROUTE_FROM = ("mac",)
HOME_HOST = "contabo"


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd not in ("host", "route"):
        print("usage: coo_host.py host|route", file=sys.stderr)
        return 2
    try:
        from lib import config

        me = config.self_host()
    except Exception as exc:  # unresolved host, missing PyYAML, bad node.yaml
        print(f"coo_host: cannot resolve this machine: {exc}", file=sys.stderr)
        return 3
    if cmd == "host":
        print(me)
        return 0
    if me == HOME_HOST or me not in ROUTE_FROM:
        return 4
    target = config.hosts()[HOME_HOST]
    alias = target.get("ssh")
    if not alias:
        return 4
    print(f"{alias} {target['agents_root']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
