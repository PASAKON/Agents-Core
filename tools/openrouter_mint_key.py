#!/usr/bin/env python3
"""Mint one capped OpenRouter key and file it in Infisical, without the value ever reaching a screen.

First use: SomPong's Jev filter (sompong.route), CEO GO RUN-20261014-0751-1c3d: $1/month, paid from the
existing OpenRouter balance. Run it on a Run card, under the management key that spend guard already holds:

    python3 tools/infisical_setup.py run Agents-Core prod --path /spend-guard --as contabo -- \\
      .venv/bin/python tools/openrouter_mint_key.py \\
        --name mooniex-sompong-prod-jev-exp2027-01-14 --limit 1 --reset monthly \\
        --to MoonieX-SomPong/prod/OPENROUTER_API_KEY_JEV \\
        --comment "Jev filter for SomPong's inbox (sompong.route)" \\
        --meta provider_name=mooniex-sompong-prod-jev-exp2027-01-14 \\
        --meta console_url=https://openrouter.ai/settings/keys --meta scope=inference \\
        --meta expires=2027-01-14 --meta owner=cto --meta spend_cap=1usd-monthly

Steps, each one stops the run on failure:
  1. refuse when a key with this name already exists (no duplicates, no second spend line);
  2. POST /keys with the name, the USD limit and the reset period;
  3. pipe the new key on stdin to `infisical_setup.py put … --as <--put-as>` (default contabo, which must be
     a Developer on the target project; the temporary `setup` identity is retired, PLAN §3);
  4. if the put fails, DELETE the new key at OpenRouter, so no key exists that nobody holds;
  5. read the stored value's last 4 back with `infisical_setup.py last4` and compare.
It prints the key's name, hash prefix, limit and "last4 match" — never the key, never the management key.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.spend_guard import OPENROUTER, ProviderError, delete_key, urllib_http  # noqa: E402

ADMIN_ENV = "OPENROUTER_API_KEY_ADMIN"
SETUP = str(ROOT / "tools" / "infisical_setup.py")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")           # provider-page name, ≤40 chars (PLAN §4b)
TARGET_RE = re.compile(r"^([A-Za-z0-9-]+)/(dev|prod)/([A-Z][A-Z0-9_]*)$")
MAX_LIMIT_USD = 20.0                                          # a bigger cap is a different conversation
RESETS = ("daily", "weekly", "monthly")

Http = Callable[[str, str, dict, Any], "tuple[int, Any]"]
Run = Callable[..., "subprocess.CompletedProcess"]


class MintError(RuntimeError):
    pass


def _auth(admin: str) -> dict:
    return {"Authorization": f"Bearer {admin}"}


def existing_names(admin: str, http: Http) -> set[str]:
    names: set[str] = set()
    offset = 0
    while True:
        status, got = http("GET", f"{OPENROUTER}/keys?include_disabled=true&offset={offset}", _auth(admin), None)
        if status != 200 or not isinstance(got, dict):
            raise MintError(f"list keys HTTP {status}")
        page = got.get("data") or []
        names |= {k.get("name") for k in page if isinstance(k, dict) and k.get("name")}
        if len(page) < 100:
            return names
        offset += len(page)


def create(admin: str, name: str, limit: float, reset: str, http: Http) -> tuple[str, str]:
    """Returns (key, hash). The key lives only in this process's memory."""
    status, got = http("POST", f"{OPENROUTER}/keys", _auth(admin),
                       {"name": name, "limit": limit, "limit_reset": reset})
    if status not in (200, 201) or not isinstance(got, dict):
        raise MintError(f"create key HTTP {status}")
    key = got.get("key")
    hsh = (got.get("data") or {}).get("hash")
    if not isinstance(key, str) or not key or not isinstance(hsh, str) or not hsh:
        raise MintError("create key: answer has no key or no hash")
    return key, hsh


def _clean_env() -> dict:
    """The put/last4 children need no provider key in their environment."""
    return {k: v for k, v in os.environ.items() if not k.startswith("OPENROUTER_")}


def put(target: tuple[str, str, str], key: str, comment: str, meta: list[str], run: Run,
        identity: str = "contabo") -> None:
    project, env, var = target
    argv = [sys.executable, SETUP, "put", project, env, var, "--stdin", "--as", identity, "--comment", comment]
    for m in meta:
        argv += ["--meta", m]
    p = run(argv, input=key + "\n", text=True, capture_output=True, env=_clean_env(), timeout=120)
    if p.returncode != 0:
        # infisical_setup never echoes a value; still cut its message to one short line
        tail = (p.stderr or p.stdout or "").strip().splitlines()[-1:] or [""]
        raise MintError(f"infisical put exit {p.returncode}: {tail[0][:160]}")


def stored_last4(target: tuple[str, str, str], run: Run, identity: str = "contabo") -> str:
    project, env, var = target
    p = run([sys.executable, SETUP, "last4", project, env, var, "--as", identity],
            text=True, capture_output=True, env=_clean_env(), timeout=60)
    if p.returncode != 0:
        raise MintError(f"infisical last4 exit {p.returncode}")
    m = re.search(r"· last4=(\S{4})\s*$", (p.stdout or "").strip())   # cmd_last4's one line
    return m.group(1) if m else ""


def mint(args: argparse.Namespace, *, http: Http = urllib_http, run: Run = subprocess.run,
         out=sys.stdout) -> int:
    admin = (os.environ.get(ADMIN_ENV) or "").strip()
    if not admin:
        raise MintError(f"{ADMIN_ENV} is not in the environment; run under infisical_setup.py run "
                        "Agents-Core prod --path /spend-guard")
    target = TARGET_RE.match(args.to)
    if not target:
        raise MintError(f"--to must be <Project>/<dev|prod>/<VAR>, got {args.to!r}")
    target_t = (target.group(1), target.group(2), target.group(3))

    if args.name in existing_names(admin, http):
        raise MintError(f"a key named {args.name} already exists at OpenRouter; nothing created")
    key, hsh = create(admin, args.name, args.limit, args.reset, http)
    print(f"created {args.name} hash={hsh[:8]} limit=${args.limit:g}/{args.reset}", file=out)
    try:
        put(target_t, key, args.comment, args.meta, run, args.put_as)
    except (MintError, OSError, subprocess.SubprocessError) as e:
        try:
            delete_key(admin, hsh, http)
            print(f"put failed, deleted {hsh[:8]} at OpenRouter", file=out)
        except ProviderError as d:
            print(f"put failed AND delete failed ({d}); delete {hsh[:8]} by hand at "
                  "https://openrouter.ai/settings/keys", file=out)
        raise MintError(str(e)) from None
    print(f"stored in Infisical {args.to}", file=out)
    got = stored_last4(target_t, run, args.put_as)
    ok = bool(got) and got == key[-4:]
    del key
    print(f"last4 match: {'yes' if ok else 'NO'}", file=out)
    return 0 if ok else 3


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--name", required=True, help="provider-page name, ≤40 chars, lower-case")
    ap.add_argument("--limit", type=float, required=True, help="USD cap OpenRouter enforces on the key")
    ap.add_argument("--reset", choices=RESETS, required=True, help="when the cap resets")
    ap.add_argument("--to", required=True, metavar="Project/env/VAR", help="where the key goes in Infisical")
    ap.add_argument("--comment", required=True, help="purpose (PLAN §4c)")
    ap.add_argument("--meta", action="append", default=[], metavar="k=v", help="metadata for the put")
    ap.add_argument("--put-as", default="contabo", metavar="IDENTITY",
                    help="Infisical identity that writes the key (needs Developer on the target project)")
    a = ap.parse_args(argv)
    if not NAME_RE.match(a.name):
        ap.error(f"--name {a.name!r}: lower-case letters, digits and '-', 3–40 chars")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", a.put_as):
        ap.error(f"--put-as {a.put_as!r}: an identity name")
    if not 0 < a.limit <= MAX_LIMIT_USD:
        ap.error(f"--limit must be > 0 and ≤ {MAX_LIMIT_USD:g} USD")
    return a


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    try:
        return mint(args)
    except (MintError, ProviderError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
