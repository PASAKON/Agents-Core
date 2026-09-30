#!/usr/bin/env python3
"""`hq join` / `hq leave`, the hub side (Org Mesh W4.1).

docs/ops/hq-join.md has the operator view. Four verbs:

    python -m tools.hq_join mint --host <name> [--ttl-min 15]
    python -m tools.hq_join accept --token <t|-> --host <name> --os <os> \\
                                   --hq-root <path> --pubkey <age1...>
    python -m tools.hq_join leave --host <name> [--live]
    python -m tools.hq_join export-hosts [--out PATH]

mint     A one-time token for a NEW host name. Only its sha256 goes to the hub
         (table join_tokens). The token is printed once, alone, on stdout.
accept   Consumes the token and inserts the `hosts` row as pending_identity
         with the node's public key, in ONE transaction. The consume is a
         single UPDATE ... WHERE used_at IS NULL AND expires_at > now
         RETURNING, so two racing accepts cannot both win (SQLite serialises
         writers, Postgres re-checks the WHERE after the first commit).
leave    Plans the revocation of everything a node holds. Without --live it
         prints the plan and changes nothing. With --live it runs each step
         through a revoker; one failed step never stops the others; the row
         goes to `left` only when every step succeeded.
export-hosts
         Writes a hosts.yaml-shaped export of the `hosts` table. Nothing reads
         it yet (lib/config.hosts() still reads config/hosts.yaml).

Nothing here touches a live system. Every outside act (Infisical, Tailscale,
GitHub, ssh) is a `Revoker`: a callable taking a Step and returning an
Outcome. `leave --live` uses UNWIRED_REVOKERS, which refuse with "not wired
yet", until W4.2 and CEO gate G3 replace them. Tests inject fakes.

Exit    0 ok, 1 ran and failed (leave with steps left behind), 2 refused
        (bad argument, or the token/host was rejected) with nothing changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from lib import config, db  # noqa: E402

ACTOR = "hq_join"
DEFAULT_TTL_MIN = 15
MAX_TTL_MIN = 60

# fullmatch only. hqj_ + 43 url-safe base64 chars = token_urlsafe(32), 256 bits.
TOKEN_RE = re.compile(r"hqj_[A-Za-z0-9_-]{43}")
# host names end up in ssh aliases, node.yaml and authorized_keys comments.
HOST_RE = re.compile(r"[a-z][a-z0-9-]{1,30}[a-z0-9]")
OS_NAMES = ("darwin", "linux", "windows")
# age X25519 recipient: bech32, hrp "age", 32 bytes -> 52 data chars + 6 checksum.
AGE_RE = re.compile(r"age1[02-9ac-hj-np-z]{58}")
_BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

# hosts.status values that keep a name taken. Only `left` frees it.
STATUS_LEFT = "left"
STATUS_PENDING = "pending_identity"
# Not exported to hosts.yaml: a node that has no identity yet, and one that left.
NOT_EXPORTED = (STATUS_LEFT, STATUS_PENDING)


class JoinError(Exception):
    """A refusal. `code` is machine-readable; `message` never contains a token."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------- helpers

def _utc(now: datetime | None) -> datetime:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _iso(t: datetime) -> str:
    # One fixed format everywhere, so expires_at > now is a string compare.
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _bech32_polymod(values: list[int]) -> int:
    gen = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            if (top >> i) & 1:
                chk ^= gen[i]
    return chk


def valid_age_recipient(key: str) -> bool:
    """Shape AND bech32 checksum, so a mistyped key is refused here and not
    discovered when W4.2 seals a client secret to a key nobody can open."""
    if not AGE_RE.fullmatch(key):
        return False
    hrp, _, data = key.rpartition("1")
    values = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    values += [_BECH32.index(c) for c in data]
    return _bech32_polymod(values) == 1


def _check_host(host: str) -> None:
    if not isinstance(host, str) or not HOST_RE.fullmatch(host):
        raise JoinError("bad_arg", "host name must be 3-32 chars: a-z, 0-9, '-', "
                                   "starting with a letter, not ending in '-'")


def _check_hq_root(os_name: str, path: str) -> str:
    if not isinstance(path, str) or not path or len(path) > 240:
        raise JoinError("bad_arg", "hq-root must be a non-empty path of at most 240 chars")
    if any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise JoinError("bad_arg", "hq-root must not contain control characters")
    if os_name == "windows":
        ok = re.fullmatch(r"[A-Za-z]:[\\/].*", path) is not None
    else:
        ok = path.startswith("/")
    if not ok:
        raise JoinError("bad_arg", f"hq-root is not an absolute {os_name} path")
    if ".." in re.split(r"[\\/]", path):
        raise JoinError("bad_arg", "hq-root must not contain '..'")
    cleaned = path.rstrip("\\/")
    if not cleaned or re.fullmatch(r"[A-Za-z]:", cleaned):
        raise JoinError("bad_arg", "hq-root must not be a filesystem root")
    return cleaned


def _layout(os_name: str, hq_root: str) -> tuple[str, str]:
    """(agents_root, worktrees) under an HQ root, same shape as the Mac's
    /Users/gob/MoonieXHQ/Agents/Core and Contabo's /opt/MoonieXHQ/Agents/Core."""
    sep = "\\" if os_name == "windows" else "/"
    agents = f"{hq_root}{sep}Agents{sep}Core"
    return agents, f"{agents}{sep}worktrees"


def _refuse_taken(conn, host: str) -> None:
    """A name is free when it has no row, or its row is `left`. Stricter than
    "online/pending_identity": offline and never-heartbeated (status NULL,
    e.g. a row seeded from hosts.yaml) also keep the name, or a token holder
    could take over the identity of a host that is merely asleep."""
    row = conn.execute("SELECT status FROM hosts WHERE host=?", (host,)).fetchone()
    if row is not None:
        if row["status"] != STATUS_LEFT:
            raise JoinError("host_in_use", f"host name {host!r} is already registered")
    elif host in config.hosts():
        raise JoinError("host_in_use", f"host name {host!r} is declared in config/hosts.yaml")


# ---------------------------------------------------------------- mint

def mint(host: str, ttl_min: int = DEFAULT_TTL_MIN, *, now: datetime | None = None) -> dict:
    """Create a one-time token for `host`. Returns {token, host, expires_at}.
    The token exists only in this return value; the hub keeps its sha256."""
    _check_host(host)
    if not isinstance(ttl_min, int) or not 1 <= ttl_min <= MAX_TTL_MIN:
        raise JoinError("bad_arg", f"ttl-min must be 1-{MAX_TTL_MIN}")
    t = _utc(now)
    token = "hqj_" + secrets.token_urlsafe(32)
    expires = _iso(t + timedelta(minutes=ttl_min))
    with db.get_conn() as conn:
        _refuse_taken(conn, host)
        conn.execute(
            "INSERT INTO join_tokens (token_hash, host, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (hash_token(token), host, _iso(t), expires),
        )
        db.log_event(conn, None, ACTOR, "join_mint", {"host": host, "expires_at": expires})
    return {"token": token, "host": host, "expires_at": expires}


# ---------------------------------------------------------------- accept

# Consume the token. One statement: the WHERE is evaluated and used_at is set
# under the same row lock, so of N racing calls exactly one gets a row back.
# `host` is in the WHERE so a wrong name does not burn the token.
_CONSUME_SQL = (
    "UPDATE join_tokens SET used_at = ? "
    "WHERE token_hash = ? AND host = ? AND used_at IS NULL AND expires_at > ? "
    "RETURNING token_hash"
)

# A `left` row may be re-joined; any other row keeps its name (WHERE on the
# DO UPDATE: no row comes back and the caller rolls the consume back).
# Probe columns are reset: they describe the machine that left.
_INSERT_HOST_SQL = (
    "INSERT INTO hosts (host, os, hq_root, agents_root, provides, max_workers, "
    "status, pubkey, config_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(host) DO UPDATE SET os=excluded.os, hq_root=excluded.hq_root, "
    "agents_root=excluded.agents_root, provides=excluded.provides, "
    "max_workers=excluded.max_workers, status=excluded.status, "
    "pubkey=excluded.pubkey, config_json=excluded.config_json, "
    "updated_at=excluded.updated_at, probed_at=NULL, free_gb=NULL, "
    "ram_free_gb=NULL, running=NULL, version=NULL, cpus=NULL, "
    "load_per_core=NULL, runners=NULL "
    f"WHERE hosts.status = '{STATUS_LEFT}' RETURNING host"
)


def _consume(conn, now_s: str, token_hash: str, host: str) -> bool:
    """True for exactly one caller per token. Kept a function of its own so
    tests can swap in a read-then-write version and watch the race test fail."""
    row = conn.execute(_CONSUME_SQL, (now_s, token_hash, host, now_s)).fetchone()
    return row is not None


def _diagnose(conn, token_hash: str, host: str, now_s: str) -> JoinError:
    """Why the consume matched nothing. Reads only; `token` is never needed."""
    row = conn.execute(
        "SELECT host, used_at, expires_at FROM join_tokens WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()
    if row is None:
        return JoinError("unknown_token", "unknown token")
    if row["host"] != host:
        return JoinError("wrong_host", "this token was minted for a different host name")
    if row["used_at"] is not None:
        return JoinError("already_used", "this token was already used")
    if row["expires_at"] <= now_s:
        return JoinError("expired", "this token has expired")
    return JoinError("conflict", "the token could not be consumed, try again")


def accept(token: str, host: str, os_name: str, hq_root: str, pubkey: str,
           *, now: datetime | None = None) -> dict:
    """Consume `token` and register `host` as pending_identity. All-or-nothing:
    any refusal rolls back, so a rejected call leaves the token usable."""
    # Arguments first: a typo must not cost the operator a token.
    _check_host(host)
    if os_name not in OS_NAMES:
        raise JoinError("bad_arg", f"os must be one of {', '.join(OS_NAMES)}")
    root = _check_hq_root(os_name, hq_root)
    if not valid_age_recipient(pubkey):
        raise JoinError("bad_arg", "pubkey is not a valid age X25519 recipient (age1...)")
    if not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
        raise JoinError("unknown_token", "unknown token")

    now_s = _iso(_utc(now))
    agents_root, worktrees = _layout(os_name, root)
    # Conservative until the W4.4 probe fills them: nothing runs here yet.
    entry = {
        "os": os_name, "hq_root": root, "ssh": host, "agents_root": agents_root,
        "worktrees": worktrees, "provides": [], "max_workers": 1, "runners": [],
    }
    token_hash = hash_token(token)
    with db.get_conn() as conn:
        if not _consume(conn, now_s, token_hash, host):
            raise _diagnose(conn, token_hash, host, now_s)
        placed = conn.execute(_INSERT_HOST_SQL, (
            host, os_name, root, agents_root, json.dumps([]), 1,
            STATUS_PENDING, pubkey, json.dumps(entry), now_s,
        )).fetchone()
        if placed is None:  # raising rolls the consume back too
            raise JoinError("host_in_use", f"host name {host!r} is already registered")
        db.log_event(conn, None, ACTOR, "join_accept", {"host": host, "os": os_name})
    return {"host": host, "status": STATUS_PENDING, "agents_root": agents_root}


# ---------------------------------------------------------------- leave

@dataclass(frozen=True)
class Step:
    kind: str    # key into the revokers mapping
    target: str  # what it acts on (the node, or the other host for authorized_keys)
    what: str    # one line for the plan


@dataclass(frozen=True)
class Outcome:
    ok: bool
    detail: str = ""


Revoker = Callable[[Step], Outcome]

# Steps run in plan_leave's order: Infisical, Tailscale, GitHub, then
# authorized_keys on each other host. A real revoker must be idempotent: a step
# that finds nothing left to revoke (already gone, 404) is ok, so a re-run after
# a partial failure converges.


def _not_wired(why: str) -> Revoker:
    def revoke(step: Step) -> Outcome:
        return Outcome(False, f"not wired yet: {why}")
    return revoke


# What `leave --live` uses until W4.2 and CEO gate G3. Every step refuses, so
# nothing outside the hub can be touched by this file.
UNWIRED_REVOKERS: Mapping[str, Revoker] = {
    "infisical_client_secret": _not_wired(
        "needs W4.2 (org-node identity and the per-node client secret id)"),
    "tailscale_device": _not_wired("needs the Tailscale OAuth client (CEO gate G3)"),
    "github_deploy_key": _not_wired("needs W4.2 (deploy key ids created through gh api)"),
    "authorized_keys": _not_wired("needs the W2.8 ssh mesh (forced-command keys)"),
}


def plan_leave(conn, host: str) -> list[Step]:
    others = conn.execute(
        "SELECT host FROM hosts WHERE host != ? AND COALESCE(status, '') != ? "
        "ORDER BY host", (host, STATUS_LEFT),
    ).fetchall()
    steps = [
        Step("infisical_client_secret", host,
             f"revoke the Universal Auth client secret of {host} under identity "
             f"org-node (that one only)"),
        Step("tailscale_device", host, f"remove the tailnet device and pre-auth key of {host}"),
        Step("github_deploy_key", host, f"delete the deploy key(s) registered for {host}"),
    ]
    for r in others:
        steps.append(Step(
            "authorized_keys", r["host"],
            f"remove {host}'s dispatch key and admin pubkey line from authorized_keys on {r['host']}"))
    return steps


def leave(host: str, *, live: bool = False,
          revokers: Mapping[str, Revoker] | None = None,
          now: datetime | None = None) -> dict:
    """Plan (live=False) or run (live=True) the revocation of `host`.

    live=False never calls a revoker and never writes to the hub. live=True
    calls `revokers` (default UNWIRED_REVOKERS) once per step, in order, and
    catches whatever a revoker raises as a failed step. Only a run where every
    step is ok marks the row `left`.
    """
    _check_host(host)
    with db.get_conn() as conn:
        row = conn.execute("SELECT status, pubkey FROM hosts WHERE host=?", (host,)).fetchone()
        if row is None:
            raise JoinError("unknown_host", f"host {host!r} is not registered")
        if row["status"] == STATUS_LEFT:
            return {"host": host, "live": live, "status": STATUS_LEFT, "steps": [],
                    "left_behind": [], "note": "already left, nothing to do"}
        if not row["pubkey"]:
            # mac/contabo/winbox: never joined through accept. Revoking "their"
            # keys on every other host would cut the hub off.
            raise JoinError("not_joined", f"host {host!r} was not joined through hq_join; "
                                          f"refusing to revoke a core host")
        steps = plan_leave(conn, host)
    if not live:
        return {"host": host, "live": False, "status": "planned", "left_behind": [],
                "steps": [{"kind": s.kind, "target": s.target, "what": s.what} for s in steps]}

    table = UNWIRED_REVOKERS if revokers is None else revokers
    results = []
    for s in steps:
        revoker = table.get(s.kind)
        if revoker is None:
            out = Outcome(False, "no revoker for this step")
        else:
            try:
                out = revoker(s)
            except Exception as exc:  # one failed step must not stop the others
                out = Outcome(False, f"{type(exc).__name__}: {str(exc)[:200]}")
        results.append({"kind": s.kind, "target": s.target, "what": s.what,
                        "ok": out.ok, "detail": out.detail})
    left_behind = [f"{r['kind']}:{r['target']}" for r in results if not r["ok"]]
    status = STATUS_LEFT if not left_behind else "partial"
    with db.get_conn() as conn:
        if not left_behind:
            conn.execute("UPDATE hosts SET status = ?, updated_at = ? WHERE host = ?",
                         (STATUS_LEFT, _iso(_utc(now)), host))
        # Names only: a revoker's detail text can carry a provider's error body.
        db.log_event(conn, None, ACTOR, "join_leave",
                     {"host": host, "status": status, "left_behind": left_behind})
    return {"host": host, "live": True, "status": status, "steps": results,
            "left_behind": left_behind}


# ---------------------------------------------------------------- export

EXPORT_HEADER = (
    "# GENERATED by `python -m tools.hq_join export-hosts` from the hub's `hosts` table.\n"
    "# Do not hand-edit: the next export overwrites it, comments included.\n"
)


def export_hosts_text() -> str:
    """hosts.yaml text for every host in the hub that has an identity and has
    not left. A row without config_json (never seeded) is refused, not
    exported stripped: a half entry would read as a host that lost its `ssh`."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT host, status, config_json FROM hosts ORDER BY host").fetchall()
    hosts: dict[str, dict] = {}
    unseeded = []
    for r in rows:
        if r["status"] in NOT_EXPORTED:
            continue
        if not r["config_json"]:
            unseeded.append(r["host"])
            continue
        hosts[r["host"]] = json.loads(r["config_json"])
    if unseeded:
        raise JoinError("not_seeded", "no config_json for host(s) " + ", ".join(unseeded)
                        + ": run lib.db.seed_hosts_from_config() first")
    body = yaml.safe_dump({"hosts": hosts}, sort_keys=False, default_flow_style=None,
                          allow_unicode=True)
    return EXPORT_HEADER + "\n" + body


# ---------------------------------------------------------------- CLI

def _read_token(arg: str) -> str:
    """`--token -` reads stdin, so the token can stay out of `ps`."""
    return sys.stdin.readline().strip() if arg == "-" else arg


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hq_join", description=__doc__.split("\n", 1)[0])
    sub = p.add_subparsers(dest="verb", required=True)
    m = sub.add_parser("mint", help="create a one-time join token for a new host name")
    m.add_argument("--host", required=True)
    m.add_argument("--ttl-min", type=int, default=DEFAULT_TTL_MIN)
    a = sub.add_parser("accept", help="consume a token and register the host")
    a.add_argument("--token", required=True, help="the token, or - to read it from stdin")
    a.add_argument("--host", required=True)
    a.add_argument("--os", dest="os_name", required=True)
    a.add_argument("--hq-root", required=True)
    a.add_argument("--pubkey", required=True, help="the node's age recipient, age1...")
    lv = sub.add_parser("leave", help="plan or run the revocation of a host")
    lv.add_argument("--host", required=True)
    lv.add_argument("--live", action="store_true",
                    help="run the steps (without it: print the plan, change nothing)")
    e = sub.add_parser("export-hosts", help="write hosts.yaml from the hosts table")
    e.add_argument("--out", default="-", help="file to write (default: stdout)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.verb == "mint":
            res = mint(args.host, args.ttl_min)
            print(f"hq_join: token for {res['host']} valid until {res['expires_at']}; "
                  f"shown once, single use", file=sys.stderr)
            print(res["token"])
            return 0
        if args.verb == "accept":
            res = accept(_read_token(args.token), args.host, args.os_name,
                         args.hq_root, args.pubkey)
            print(json.dumps({"ok": True, **res}))
            return 0
        if args.verb == "leave":
            res = leave(args.host, live=args.live)
            return _print_leave(res)
        text = export_hosts_text()
        if args.out == "-":
            sys.stdout.write(text)
        else:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"hq_join: wrote {args.out}", file=sys.stderr)
        return 0
    except JoinError as exc:
        print(f"hq_join: refused ({exc.code}): {exc.message}", file=sys.stderr)
        return 2


def _print_leave(res: dict) -> int:
    if res.get("note"):
        print(f"hq_join: {res['host']}: {res['note']}")
        return 0
    if not res["live"]:
        print(f"hq_join: PLAN to revoke {res['host']} (nothing done, add --live to run):")
        for s in res["steps"]:
            print(f"  [plan] {s['kind']} on {s['target']}: {s['what']}")
        return 0
    for s in res["steps"]:
        mark = "ok" if s["ok"] else "FAILED"
        print(f"  [{mark}] {s['kind']} on {s['target']}" + ("" if s["ok"] else f": {s['detail']}"))
    if res["status"] == STATUS_LEFT:
        print(f"hq_join: {res['host']} is now `left`")
        return 0
    print(f"hq_join: {res['host']} NOT marked left; left behind: " + ", ".join(res["left_behind"]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
