#!/usr/bin/env python3
"""`hq join` / `hq leave`, the hub side (Org Mesh W4.1).

docs/ops/hq-join.md has the operator view. Six verbs:

    python -m tools.hq_join mint --host <name> [--ttl-min 15]
    python -m tools.hq_join accept --token <t|-> --host <name> --os <os> \\
                                   --hq-root <path> --pubkey <age1...>
                                   [--deploy-pubkey "ssh-ed25519 AAAA..."]
    python -m tools.hq_join status [--host <name>]      # joined nodes + key fingerprint
    python -m tools.hq_join approve --host <name> --fingerprint <8 chars>   # W4.6a
    python -m tools.hq_join provision --host <name>     # Mac side (W4.2)
    python -m tools.hq_join sealed --host <name>        # prints the ciphertext
    python -m tools.hq_join leave --host <name> [--live]
    python -m tools.hq_join export-hosts [--out PATH]

mint    A one-time token for a NEW host name. Only its sha256 goes to the hub
         (table join_tokens). The token is printed once, alone, on stdout.
accept   Consumes the token and inserts the `hosts` row as pending_identity
         with the node's public key, in ONE transaction. The consume is a
         single UPDATE ... WHERE used_at IS NULL AND expires_at > now
         RETURNING, so two racing accepts cannot both win (SQLite serialises
         writers, Postgres re-checks the WHERE after the first commit).
status   W4.6a. One line per joined node: status, whether it is approved, and the
         FINGERPRINT of its age key (the last 8 chars of the public recipient, no
         secret). The operator compares it with the one join.sh printed on the node.
approve  W4.6a (F1). `--fingerprint` must equal the fingerprint of the stored key
         (constant-time compare) on a pending_identity row; it sets hosts.approved_at.
         `provision` does nothing for a row that is not approved, so whoever wins
         the accept race with a leaked token still gets no identity.
provision
         W4.2 / W4.2b. An approved pending_identity row becomes identity_ready:
         seal a v2 bundle {"v":2,"host":H,"token_url":<hub token URL>} to the
         host's age key, register the host's GitHub deploy key, store ONLY the
         ciphertext and the deploy key id (table node_secrets). Infisical is
         not touched: a node has no identity of its own (CEO 2026-10-03), the
         hub serves it the token itself (tools/node_token_api.py) for as long
         as the row is approved and not leaving. The URL is the environment
         variable ORG_NODE_TOKEN_URL; without it provision refuses. A failure
         after the deploy key removes it. Re-running on an identity_ready row
         does nothing.
sealed   W4.2. Prints the armored ciphertext of a host (only that host's age
         key opens it). How it reaches the node is W4.3.
leave    Plans the revocation of everything a node holds. Without --live it
         prints the plan and changes nothing. With --live the FIRST step sets
         the row to `leaving` (the token service refuses the host from that
         moment); then each other step runs through a revoker; one failed step
         never stops the others; the row goes to `left` only when every step
         succeeded, and stays `leaving` otherwise.
export-hosts
         Writes a hosts.yaml-shaped export of the `hosts` table. Nothing reads
         it yet (lib/config.hosts() still reads config/hosts.yaml).

Nothing here touches a live system unless ORG_W42_PROVISION=1. Every outside
act (Tailscale, GitHub, ssh) is injectable: a `Revoker` is a callable taking a
Step and returning an Outcome, and `provision` takes a gh runner and a sealer.
`leave --live` uses UNWIRED_REVOKERS ("not wired yet") unless the flag is on; with
it, wired_revokers() deletes the GitHub deploy key for real, removes the tailnet
device too when TAILSCALE_OAUTH_CLIENT_ID / _SECRET are in the environment
(lib/tailscale_api.py), and settles authorized_keys by what was PLACED
(_placed_authorized_keys): nothing for a joined node, so it is ok there; a core
host's lines are placed and no code removes them, so it refuses. The `leaving`
step is the hub's own database write and does not depend on the flag. Tests
inject fakes.

Exit    0 ok, 1 ran and failed (leave with steps left behind, provision
        failed), 2 refused (bad argument, or the token/host was rejected)
        with nothing changed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from lib import config, db, sealed, tailscale_api  # noqa: E402
from tools import infisical_setup  # noqa: E402

ACTOR = "hq_join"
_log = logging.getLogger("hq_join")
DEFAULT_TTL_MIN = 15
MAX_TTL_MIN = 60

# fullmatch only. hqj_ + 43 url-safe base64 chars = token_urlsafe(32), 256 bits.
TOKEN_RE = re.compile(r"hqj_[A-Za-z0-9_-]{43}")
# host names end up in ssh aliases, node.yaml and authorized_keys comments.
# 3-31 chars, `[a-z][a-z0-9-]{1,29}[a-z0-9]`: the one rule, owned by lib.config because
# node.yaml is read there. 31 is the most `infisical_setup.py save` (NAME_RE) accepts.
HOST_RE = config.HOST_NAME_RE
OS_NAMES = ("darwin", "linux", "windows")
# age X25519 recipient: bech32, hrp "age", 32 bytes -> 52 data chars + 6 checksum.
AGE_RE = re.compile(r"age1[02-9ac-hj-np-z]{58}")
_BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
# W4.6a F1. What the operator compares by eye and types into `approve`: the last 8 chars of
# the recipient (2 key chars + the 6-char checksum). The recipient is public, so is this.
FINGERPRINT_LEN = 8
FINGERPRINT_RE = re.compile(r"[02-9ac-hj-np-z]{8}")
# W4.6a F14. hq_root flows into config_json agents_root/worktrees, and a shell may interpolate
# it later: no `$`, backtick, `;`, quote, `(`, `&`, `|`. lib.config._node_hq_root has the same set.
HQ_ROOT_CHARS_RE = re.compile(r"[A-Za-z0-9 ._/\\:-]+")

# hosts.status values that keep a name taken. Only `left` frees it.
STATUS_LEFT = "left"
STATUS_PENDING = "pending_identity"
STATUS_READY = "identity_ready"   # W4.2: its sealed bundle is in the hub, the node has not joined yet
# W4.2b: `leave --live` has started and has not finished. The token service refuses the host as
# `left` from this moment, and a name in this state stays taken (only `left` frees it).
STATUS_LEAVING = "leaving"
# Not exported to hosts.yaml: a node that has no identity yet, one that has an identity
# but has not finished joining (no probe, nothing to route to), one that is leaving, and one that left.
NOT_EXPORTED = (STATUS_LEFT, STATUS_LEAVING, STATUS_PENDING, STATUS_READY)

# W4.2b (CEO 2026-10-03). A node has no Infisical identity: provision seals it a bundle that says
# where to ask the hub for its token, and tools/node_token_api.py answers there.
TOKEN_URL_ENV = "ORG_NODE_TOKEN_URL"
BUNDLE_VERSION = 2
# scheme://host[:port][/path], nothing else: no userinfo, query or fragment (the node adds
# `?host=<its name>` itself), no whitespace, bounded. A DNS name or an IPv4 address.
TOKEN_URL_RE = re.compile(r"https?://[A-Za-z0-9][A-Za-z0-9.-]{0,98}(?::[0-9]{1,5})?(?:/[A-Za-z0-9._~/-]{0,100})?")

# W4.2. The live path (real Infisical, real gh) is off unless this is "1".
W42_FLAG = "ORG_W42_PROVISION"
GH_REPO = "PASAKON/Agents-Core"
# ssh-ed25519 public key line: `ssh-ed25519 <base64>` and an optional comment. The regex only
# splits the line; _is_ed25519_blob decodes the base64 and checks the wire format. A real key
# is 51 bytes (4-byte length, "ssh-ed25519", 4-byte length 32, the key), so 68 characters, no padding.
DEPLOY_PUBKEY_RE = re.compile(
    r"ssh-ed25519 ([A-Za-z0-9+/]+)(?: [\x20-\x7e]{1,80})?")
_ED25519_BLOB_HEAD = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
_ED25519_BLOB_LEN = len(_ED25519_BLOB_HEAD) + 32
# A provision claim younger than this, with no ciphertext yet, is a run still in progress.
CLAIM_STALE_S = 600


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


def reserved_hosts() -> frozenset:
    """Names no joined node may take (W4.6a F13): the admin identity `setup`, the retired shared
    name `org-node`, and every machine identity in infisical_setup.MACHINES. A core host's name
    carries its Infisical credential file and its dispatch keys, and a node must never be
    mistaken for one. Read at call time, so a new MACHINES entry is covered."""
    return frozenset({infisical_setup.SETUP, infisical_setup.NODE_IDENTITY,
                      *infisical_setup.MACHINES})


def _check_host(host: str) -> None:
    if not isinstance(host, str) or not HOST_RE.fullmatch(host):
        raise JoinError("bad_arg", "host name must be 3-31 chars: a-z, 0-9, '-', "
                                   "starting with a letter, not ending in '-'")
    if host in reserved_hosts():
        raise JoinError("bad_arg", f"host name {host!r} is reserved (an Infisical identity name)")


def check_token_url(url: str | None) -> str:
    """The hub's token URL as it goes into a node's bundle, or JoinError naming TOKEN_URL_ENV."""
    url = (url or "").strip()
    if not url:
        raise JoinError("no_token_url", f"the hub's token URL is not set: set {TOKEN_URL_ENV} "
                                        f"(for example http://<hub tailnet address>:8792/v1/token)")
    if not TOKEN_URL_RE.fullmatch(url):
        raise JoinError("bad_token_url", f"{TOKEN_URL_ENV} must look like "
                                         f"http://<host>[:port]/<path>, with no user, query or fragment")
    return url


def fingerprint(pubkey: str) -> str:
    """The short check string of an age recipient: its last FINGERPRINT_LEN chars."""
    return pubkey[-FINGERPRINT_LEN:]


def _check_hq_root(os_name: str, path: str) -> str:
    if not isinstance(path, str) or not path or len(path) > 240:
        raise JoinError("bad_arg", "hq-root must be a non-empty path of at most 240 chars")
    if any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise JoinError("bad_arg", "hq-root must not contain control characters")
    if not HQ_ROOT_CHARS_RE.fullmatch(path):
        raise JoinError("bad_arg", "hq-root may contain only letters, digits, space and . _ / \\ : -")
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

# A new name is inserted; an existing name is left alone by the INSERT (DO NOTHING) and only a
# `left` row is re-joined, by the UPDATE (W4.6c: one statement used to do both with
# ON CONFLICT DO UPDATE ... excluded.*, and Postgres then asks for SELECT on every column it reads
# through `excluded`, which would have let the public endpoint's role read each host's key and
# config; two statements need SELECT on host and status only). Both run in the caller's
# transaction: a name that is neither new nor `left` matches nothing, the caller raises, and the
# consume rolls back. Two racing accepts for one name: the second finds the row `pending_identity`
# and matches nothing. Probe columns are reset: they describe the machine that left.
_INSERT_HOST_SQL = (
    "INSERT INTO hosts (host, os, hq_root, agents_root, provides, max_workers, "
    "status, pubkey, config_json, updated_at, deploy_pubkey) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(host) DO NOTHING RETURNING host"
)
_REJOIN_HOST_SQL = (
    "UPDATE hosts SET os = ?, hq_root = ?, agents_root = ?, provides = ?, max_workers = ?, "
    "status = ?, pubkey = ?, config_json = ?, updated_at = ?, deploy_pubkey = ?, "
    "approved_at = NULL, probed_at = NULL, free_gb = NULL, ram_free_gb = NULL, "
    "running = NULL, version = NULL, cpus = NULL, load_per_core = NULL, runners = NULL "
    f"WHERE host = ? AND status = '{STATUS_LEFT}' RETURNING host"
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


def _is_ed25519_blob(b64: str) -> bool:
    """The base64 of a real ssh-ed25519 public key: it decodes (no padding, no stray character)
    to exactly the 51-byte wire blob, the "ssh-ed25519" header and a 32-byte key."""
    try:
        blob = base64.b64decode(b64, validate=True)
    except ValueError:
        return False
    return len(blob) == _ED25519_BLOB_LEN and blob.startswith(_ED25519_BLOB_HEAD)


def _check_deploy_pubkey(key: str | None) -> str | None:
    """None stays None (the node gets no deploy key). A key line is reduced to
    "ssh-ed25519 <base64>": the comment is free text and is not stored."""
    if key is None:
        return None
    m = DEPLOY_PUBKEY_RE.fullmatch(key.strip() if isinstance(key, str) else "")
    if not m or not _is_ed25519_blob(m.group(1)):
        raise JoinError("bad_arg", "deploy-pubkey is not an ssh-ed25519 public key line "
                                   "(ssh-ed25519 AAAA... [comment])")
    return f"ssh-ed25519 {m.group(1)}"


def accept(token: str, host: str, os_name: str, hq_root: str, pubkey: str,
           *, deploy_pubkey: str | None = None, now: datetime | None = None) -> dict:
    """Consume `token` and register `host` as pending_identity. All-or-nothing:
    any refusal rolls back, so a rejected call leaves the token usable.

    `deploy_pubkey` (W4.2, optional) is the ssh-ed25519 public key that
    `provision` registers as the node's GitHub deploy key, stored in
    hosts.deploy_pubkey. Without it the node gets no deploy key: logged, not
    an error."""
    # Arguments first: a typo must not cost the operator a token.
    _check_host(host)
    if os_name not in OS_NAMES:
        raise JoinError("bad_arg", f"os must be one of {', '.join(OS_NAMES)}")
    root = _check_hq_root(os_name, hq_root)
    if not valid_age_recipient(pubkey):
        raise JoinError("bad_arg", "pubkey is not a valid age X25519 recipient (age1...)")
    deploy_key = _check_deploy_pubkey(deploy_pubkey)
    if deploy_key is None:
        _log.info("hq_join: %s joins without --deploy-pubkey: no GitHub deploy key will be made", host)
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
        values = (host, os_name, root, agents_root, json.dumps([]), 1,
                  STATUS_PENDING, pubkey, json.dumps(entry), now_s, deploy_key)
        placed = conn.execute(_INSERT_HOST_SQL, values).fetchone()
        if placed is None:  # the name exists: only a `left` row may be taken over again
            placed = conn.execute(_REJOIN_HOST_SQL, values[1:] + (host,)).fetchone()
        if placed is None:  # raising rolls the consume back too
            raise JoinError("host_in_use", f"host name {host!r} is already registered")
        db.log_event(conn, None, ACTOR, "join_accept",
                     {"host": host, "os": os_name, "deploy_key": deploy_key is not None})
    return {"host": host, "status": STATUS_PENDING, "agents_root": agents_root,
            "fingerprint": fingerprint(pubkey)}


# ---------------------------------------------------------------- approve (W4.6a, F1)

def approve(host: str, fp: str, *, now: datetime | None = None) -> dict:
    """Mark a pending_identity host approved: `fp` must be the fingerprint (last 8 chars) of
    the age key the hub stored for it. A human reads it off the node's screen, so a racer who
    won /accept with their own key cannot be approved by mistake: their key has another
    fingerprint. No provision happens without this (provision skips unapproved rows).

    The compare is constant time. The error never echoes the stored fingerprint (that would
    let a mismatch be fixed by copying it from the error). Approving twice is a no-op."""
    _check_host(host)
    want = fp.strip().lower() if isinstance(fp, str) else ""
    if not FINGERPRINT_RE.fullmatch(want):
        raise JoinError("bad_arg", f"fingerprint must be the last {FINGERPRINT_LEN} characters "
                                   f"of the node's age recipient (a-z 0-9, no b i o 1)")
    with db.get_conn() as conn:
        row = conn.execute("SELECT status, pubkey, approved_at FROM hosts WHERE host = ?",
                           (host,)).fetchone()
    if row is None:
        raise JoinError("unknown_host", f"host {host!r} is not registered")
    if not row["pubkey"]:
        raise JoinError("not_joined", f"host {host!r} was not joined through hq_join")
    if row["status"] != STATUS_PENDING:
        raise JoinError("bad_status", f"host {host!r} is {row['status']!r}; "
                                      f"only {STATUS_PENDING} can be approved")
    if not hmac.compare_digest(fingerprint(row["pubkey"]).encode("ascii"), want.encode("ascii")):
        raise JoinError("fingerprint_mismatch",
                        f"that is not the fingerprint of the key {host!r} registered; "
                        f"re-read the one join.sh printed on the node's own screen. "
                        f"If they still differ, someone else used the token: do not approve")
    if row["approved_at"] is not None:
        return {"host": host, "status": STATUS_PENDING, "approved_at": row["approved_at"],
                "changed": False}
    now_s = _iso(_utc(now))
    with db.get_conn() as conn:
        # pubkey and status are in the WHERE: the approval binds to the key that was compared.
        done = conn.execute(
            "UPDATE hosts SET approved_at = ?, updated_at = ? WHERE host = ? AND status = ? "
            "AND pubkey = ? AND approved_at IS NULL RETURNING host",
            (now_s, now_s, host, STATUS_PENDING, row["pubkey"])).fetchone()
        if done is None:
            raise JoinError("conflict", f"{host!r} changed while it was being approved, try again")
        db.log_event(conn, None, ACTOR, "join_approve", {"host": host, "fingerprint": want})
    return {"host": host, "status": STATUS_PENDING, "approved_at": now_s, "changed": True}


def node_status(host: str | None = None) -> list[dict]:
    """Every node that joined through accept (rows with a pubkey), or just `host`: name,
    hosts.status, os, fingerprint and approved_at. Nothing here is secret."""
    if host is not None:
        _check_host(host)
    with db.get_conn() as conn:
        rows = conn.execute("SELECT host, status, os, pubkey, approved_at FROM hosts "
                            "WHERE pubkey IS NOT NULL ORDER BY host").fetchall()
    out = [{"host": r["host"], "status": r["status"], "os": r["os"],
            "fingerprint": fingerprint(r["pubkey"]), "approved_at": r["approved_at"],
            "awaiting_approval": r["status"] == STATUS_PENDING and r["approved_at"] is None}
           for r in rows if host is None or r["host"] == host]
    if host is not None and not out:
        raise JoinError("unknown_host", f"host {host!r} did not join through hq_join")
    return out


# ---------------------------------------------------------------- leave

@dataclass(frozen=True)
class Step:
    kind: str    # key into the revokers mapping
    target: str  # what it acts on (the node, or the other host for authorized_keys)
    what: str    # one line for the plan
    host: str = ""  # the node that is leaving; set on authorized_keys steps, where target is another host


@dataclass(frozen=True)
class Outcome:
    ok: bool
    detail: str = ""


Revoker = Callable[[Step], Outcome]

# Steps run in plan_leave's order: `leaving` (the hub's own write, see _begin_leave), Tailscale,
# GitHub, then authorized_keys on each other host. A real revoker must be idempotent: a step
# that finds nothing left to revoke (already gone, 404) is ok, so a re-run after
# a partial failure converges.


def _not_wired(why: str) -> Revoker:
    def revoke(step: Step) -> Outcome:
        return Outcome(False, f"not wired yet: {why}")
    return revoke


_AUTHORIZED_KEYS_WHY = "needs the W2.8 ssh mesh (forced-command keys)"


def _placed_authorized_keys(host: str, target: str) -> list[str]:
    """The authorized_keys lines code has put on `target` for `host`: the ONE place that
    knows. Leave revokes what was placed, so revoke_authorized_keys removes exactly what
    this returns.

    A joined node: [] today. join.sh / join.ps1 (W4.3 step 3) create the node's keys on the
    node only, and nothing writes them into any host's authorized_keys. W2.8-for-nodes is the
    place that must start recording its placements here, in the same change that places them.

    A core host (mac, contabo, winbox; every reserved name is treated alike): its W2.8a
    dispatch lines ARE placed on the other hosts. They are not enumerated here, so one
    descriptor stands for them and the revoker refuses until a remover exists."""
    if host in reserved_hosts():
        return [f"{host}'s W2.8a dispatch line on {target}"]
    return []


def revoke_authorized_keys(step: Step) -> Outcome:
    """The `authorized_keys` leg. Nothing placed means nothing to remove: ok. Something
    placed has no remover yet, so it refuses; saying ok there would mark a node `left`
    while its key still opens a door. A step with no node named is refused for the same
    reason: "none placed" is a claim about one host."""
    if not step.host:
        return Outcome(False, "the step names no node, so what was placed cannot be known")
    placed = _placed_authorized_keys(step.host, step.target)
    if placed:
        return Outcome(False, f"not wired yet: {_AUTHORIZED_KEYS_WHY}; "
                              f"{len(placed)} placed on {step.target}, nothing removes them")
    return Outcome(True, f"none placed: no code puts {step.host}'s key on {step.target} yet "
                         f"(W2.8 for joined nodes); nothing to remove")


# What `leave --live` uses unless ORG_W42_PROVISION=1 (then wired_revokers(),
# below, replaces the github entry, the tailscale one when the Tailscale OAuth client is in
# the environment, and the authorized_keys one with revoke_authorized_keys). Every step
# refuses, so nothing outside the hub can be touched by this file.
UNWIRED_REVOKERS: Mapping[str, Revoker] = {
    "tailscale_device": _not_wired(
        f"needs {W42_FLAG}=1 and {tailscale_api.ID_ENV} + {tailscale_api.SECRET_ENV} in the environment"),
    "github_deploy_key": _not_wired(
        f"live revocation is off (set {W42_FLAG}=1, W4.2)"),
    "authorized_keys": _not_wired(_AUTHORIZED_KEYS_WHY),
}


# ---------------------------------------------------------------- W4.2: identity

# `gh` is run as gh(args, stdin_text) -> (returncode, stdout, stderr); args are what
# follows the word `gh`. A sealer is seal(recipient, plaintext_bytes) -> armored bytes.
GhRunner = Callable[[list, "str | None"], tuple]
Sealer = Callable[[str, bytes], bytes]


def w42_enabled() -> bool:
    return os.environ.get(W42_FLAG) == "1"


def _gh_subprocess(args: list, stdin: str | None = None) -> tuple:
    p = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True,
                       timeout=60, check=False)
    return p.returncode, p.stdout, p.stderr


def _no_gh(args: list, stdin: str | None = None) -> tuple:
    raise RuntimeError("no gh runner was injected")


def add_deploy_key(gh: GhRunner, host: str, key: str) -> str:
    """Register `key` as a read-only deploy key on GH_REPO, titled org-node:<host>.
    Returns the key id as text. The key is a PUBLIC key, so it may sit in the body."""
    body = json.dumps({"title": f"org-node:{host}", "key": key, "read_only": True})
    rc, out, err = gh(["api", f"repos/{GH_REPO}/keys", "-X", "POST", "--input", "-"], body)
    if rc != 0:
        raise JoinError("gh_failed", f"gh could not add the deploy key: {err.strip()[:200]}")
    try:
        return str(int(json.loads(out)["id"]))
    except (ValueError, KeyError, TypeError):
        raise JoinError("gh_failed", "gh returned no deploy key id") from None


def delete_deploy_key(gh: GhRunner, key_id: str) -> None:
    """Delete one deploy key by id. Already gone (404) counts as done."""
    if not isinstance(key_id, str) or not re.fullmatch(r"[0-9]{1,20}", key_id):
        raise JoinError("bad_arg", "bad deploy key id")
    rc, out, err = gh(["api", f"repos/{GH_REPO}/keys/{key_id}", "-X", "DELETE"], None)
    if rc != 0 and "HTTP 404" not in err:
        raise JoinError("gh_failed", f"gh could not delete the deploy key: {err.strip()[:200]}")


def _exec(sql: str, params: tuple = ()) -> None:
    with db.get_conn() as conn:
        conn.execute(sql, params)


def _deploy_key_id(host: str) -> str | None:
    """The GitHub deploy key id recorded for host, or None."""
    with db.get_conn() as conn:
        r = conn.execute("SELECT github_deploy_key_id AS kid FROM node_secrets WHERE host = ?",
                         (host,)).fetchone()
    return r["kid"] if r else None


def _void_bundle(host: str, now_s: str) -> None:
    """Mark the host's sealed bundle revoked and drop the ciphertext: `sealed` serves nothing
    for it from here on. Idempotent: the first revoked_at stays."""
    _exec("UPDATE node_secrets SET revoked_at = COALESCE(revoked_at, ?), ciphertext = NULL "
          "WHERE host = ?", (now_s, host))


def _revoke_key_leg(host: str, kid: str | None, gh: GhRunner) -> None:
    if kid:
        delete_deploy_key(gh, kid)
    _exec("UPDATE node_secrets SET github_deploy_key_id = NULL WHERE host = ?", (host,))


def tailscale_revoker(client=None) -> Revoker | None:
    """The `tailscale_device` leg: remove the node's tag:org-node device from the tailnet
    (lib.tailscale_api.delete_device, which refuses anything untagged and any ambiguity).
    `client` defaults to the one TAILSCALE_OAUTH_CLIENT_ID / _SECRET in the environment name; None
    when the environment holds none, so the step stays unwired. Half a configuration is not
    "none": the step refuses, naming the variables. Builds a client and calls nothing."""
    if client is None:
        try:
            client = tailscale_api.from_env(os.environ)
        except ValueError as exc:   # names the two variables, never a value
            return _not_wired(str(exc))
        if client is None:
            return None

    def revoke(step: Step) -> Outcome:
        gone = client.delete_device(step.target)
        return Outcome(True, "deleted" if gone else "no tag:org-node device on the tailnet")
    return revoke


def wired_revokers(*, gh: GhRunner | None = None, tailscale=None) -> Mapping[str, Revoker]:
    """UNWIRED_REVOKERS with the live legs made real: the deploy key is deleted by the id in
    node_secrets. The tailnet device is removed when `tailscale` (a client) is given or the
    environment holds the Tailscale OAuth client (tailscale_revoker); otherwise tailscale_device
    stays unwired. authorized_keys is revoke_authorized_keys: ok for a joined node (nothing
    placed), refused for a core host. There is no Infisical leg: a node holds no Infisical
    credential (W4.2b)."""
    def revoke_key(step: Step) -> Outcome:
        kid = _deploy_key_id(step.target)
        _revoke_key_leg(step.target, kid, gh or _gh_subprocess)
        return Outcome(True, "deleted" if kid else "no deploy key recorded")

    table = {**UNWIRED_REVOKERS, "github_deploy_key": revoke_key,
             "authorized_keys": revoke_authorized_keys}
    ts = tailscale_revoker(tailscale)
    if ts is not None:
        table["tailscale_device"] = ts
    return table


def default_revokers() -> Mapping[str, Revoker]:
    return wired_revokers() if w42_enabled() else UNWIRED_REVOKERS


# Claim the node_secrets row before anything is made. One statement, so of two racing
# provisions exactly one places it. A row that is revoked and holds no deploy key (a node that
# left and came back) is taken over; any other row stays. The row's old Infisical column (from
# before W4.2b) is not written any more: a stale id stays as the audit trail it always was.
_CLAIM_SQL = (
    "INSERT INTO node_secrets (host, created_at) VALUES (?, ?) "
    "ON CONFLICT(host) DO UPDATE SET ciphertext = NULL, "
    "github_deploy_key_id = NULL, created_at = excluded.created_at, fetched_at = NULL, "
    "revoked_at = NULL "
    "WHERE node_secrets.revoked_at IS NOT NULL AND node_secrets.github_deploy_key_id IS NULL "
    "RETURNING host"
)


def _claim(host: str, t: datetime, gh: GhRunner) -> None:
    now_s = _iso(t)
    with db.get_conn() as conn:
        if conn.execute(_CLAIM_SQL, (host, now_s)).fetchone() is not None:
            return
        old = conn.execute("SELECT * FROM node_secrets WHERE host = ?", (host,)).fetchone()
    if old is None:
        raise JoinError("conflict", "node_secrets changed while claiming, try again")
    age_s = (t - datetime.fromisoformat(old["created_at"])).total_seconds()
    if old["ciphertext"] is None and age_s < CLAIM_STALE_S:
        raise JoinError("busy", f"provisioning of {host!r} is already running "
                                f"(started {old['created_at']})")
    # What an earlier run left (it crashed, or could not delete the key): clear it, then claim.
    try:
        _void_bundle(host, now_s)
        _revoke_key_leg(host, old["github_deploy_key_id"], gh)
    except Exception as exc:
        raise JoinError("leftover", f"could not remove what an earlier provision of {host!r} "
                                    f"left ({type(exc).__name__}: {str(exc)[:200]})") from None
    with db.get_conn() as conn:
        if conn.execute(_CLAIM_SQL, (host, now_s)).fetchone() is None:
            raise JoinError("busy", f"provisioning of {host!r} was claimed by another run")


def _undo(host: str, kid: str | None, gh: GhRunner, cause: Exception, now_s: str) -> JoinError:
    """Remove what this run made. Whatever cannot be removed keeps its id in node_secrets
    (and is named in the error) so `leave` or the next run can finish the job."""
    left = []
    try:
        _void_bundle(host, now_s)
    except Exception:
        left.append("sealed_bundle")
    try:
        _revoke_key_leg(host, kid, gh)
    except Exception:
        left.append(f"github_deploy_key:{kid}")
    try:
        with db.get_conn() as conn:
            if not left:  # nothing outside is left: the claim row was ours, drop it
                conn.execute("DELETE FROM node_secrets WHERE host = ?", (host,))
            db.log_event(conn, None, ACTOR, "node_provision_failed",
                         {"host": host, "cause": type(cause).__name__, "left_behind": left})
    except Exception:
        pass  # the hub may be what failed; the JoinError below still names the leftovers
    why = f"{type(cause).__name__}: {cause}"[:200]
    if left:
        return JoinError("provision_orphans",
                         f"provisioning {host!r} failed ({why}) and could NOT remove: "
                         f"{', '.join(left)}; run `leave --host {host} --live` to finish")
    return JoinError("provision_failed",
                     f"provisioning {host!r} failed ({why}); everything made for it was removed")


def provision(host: str, *, gh: GhRunner | None = None, sealer: Sealer | None = None,
              token_url: str | None = None, now: datetime | None = None) -> dict:
    """pending_identity -> identity_ready for `host`: seal the token bundle, deploy key, store.

    Never touches Infisical (CEO 2026-10-03): the bundle is {"v":2,"host":host,"token_url":URL},
    sealed to the host's age key, and the node asks the hub for its token at that URL
    (tools/node_token_api.py). Order: claim the node_secrets row; seal (a failure here happens
    before any deploy key exists); register the deploy key, if the host gave one, and record its
    id; then store the ciphertext and flip the status in ONE transaction. A failure after the
    deploy key removes it (_undo). An identity_ready row is a no-op.

    `token_url` defaults to the environment variable ORG_NODE_TOKEN_URL; without either, provision
    refuses before anything is claimed. `gh=None` means live for the GitHub leg: it needs
    ORG_W42_PROVISION=1; an injected `gh` (tests) does not."""
    _check_host(host)
    with db.get_conn() as conn:
        row = conn.execute("SELECT status, pubkey, deploy_pubkey, approved_at FROM hosts "
                           "WHERE host = ?", (host,)).fetchone()
    if row is None:
        raise JoinError("unknown_host", f"host {host!r} is not registered")
    if not row["pubkey"]:
        raise JoinError("not_joined", f"host {host!r} was not joined through hq_join")
    if row["status"] == STATUS_READY:
        return {"host": host, "status": STATUS_READY, "changed": False}
    if row["status"] != STATUS_PENDING:
        raise JoinError("bad_status", f"host {host!r} is {row['status']!r}; "
                                      f"only {STATUS_PENDING} can be provisioned")
    if row["approved_at"] is None:   # W4.6a F1: checked before any claim or deploy key
        raise JoinError("not_approved", f"host {host!r} is not approved: compare its key "
                                        f"fingerprint, then `hq_join approve --host {host} "
                                        f"--fingerprint <8 chars>`")
    url = check_token_url(token_url if token_url is not None else os.environ.get(TOKEN_URL_ENV))
    if gh is None:
        if not w42_enabled():
            raise JoinError("not_enabled", f"live provisioning is off: set {W42_FLAG}=1")
        gh = _gh_subprocess
    sealer = sealer or sealed.seal
    t = _utc(now)
    now_s = _iso(t)
    _claim(host, t, gh)
    kid = None
    try:
        payload = json.dumps({"v": BUNDLE_VERSION, "host": host, "token_url": url},
                             separators=(",", ":")).encode("utf-8")
        ciphertext = sealer(row["pubkey"], payload).decode("ascii")
        if row["deploy_pubkey"]:
            kid = add_deploy_key(gh, host, row["deploy_pubkey"])
            _exec("UPDATE node_secrets SET github_deploy_key_id = ? WHERE host = ?", (kid, host))
        else:
            _log.info("hq_join: %s has no deploy pubkey: no GitHub deploy key made", host)
        with db.get_conn() as conn:
            stored = conn.execute(
                "UPDATE node_secrets SET ciphertext = ? WHERE host = ? "
                "AND revoked_at IS NULL RETURNING host", (ciphertext, host)).fetchone()
            ready = conn.execute(
                "UPDATE hosts SET status = ?, updated_at = ? WHERE host = ? AND status = ? "
                "RETURNING host", (STATUS_READY, now_s, host, STATUS_PENDING)).fetchone()
            if stored is None or ready is None:  # raising rolls both back
                raise JoinError("conflict", f"{host!r} changed while it was being provisioned")
            db.log_event(conn, None, ACTOR, "node_provisioned",
                         {"host": host, "deploy_key": kid is not None})
    except Exception as exc:
        raise _undo(host, kid, gh, exc, now_s) from None
    return {"host": host, "status": STATUS_READY, "changed": True, "deploy_key": kid is not None}


def provision_pending(*, gh: GhRunner | None = None, sealer: Sealer | None = None,
                      token_url: str | None = None, skip=(),
                      now: datetime | None = None) -> list[dict]:
    """provision() for every pending_identity row not in `skip`. One bad row never stops
    the others: it becomes {host, error}. With no `gh` (the watchdog) it does nothing unless
    ORG_W42_PROVISION=1; the admin identity file is no longer a precondition (W4.2b: nothing
    here logs in to Infisical).

    A row that is not approved (W4.6a F1) is not touched and does not count as a failure:
    it becomes {host, skipped: "not_approved"}. The caller says so, at its own pace: this
    function logs nothing for it, or every pass would."""
    if gh is None:
        if not w42_enabled():
            return []
        gh = _gh_subprocess
    results = []
    for h in db.list_hosts():
        if h["status"] != STATUS_PENDING or not h["pubkey"] or h["host"] in skip:
            continue
        if h.get("approved_at") is None:
            results.append({"host": h["host"], "skipped": "not_approved"})
            continue
        try:
            results.append(provision(h["host"], gh=gh, sealer=sealer, token_url=token_url, now=now))
        except Exception as exc:
            code = exc.code if isinstance(exc, JoinError) else type(exc).__name__
            results.append({"host": h["host"], "error": code})
            _log.warning("hq_join: provision of %s failed: %s", h["host"], code)
    return results


def sealed_ciphertext(host: str, *, now: datetime | None = None) -> str:
    """The armored ciphertext stored for `host`; stamps fetched_at the first time."""
    _check_host(host)
    with db.get_conn() as conn:
        r = conn.execute("SELECT ciphertext, fetched_at, revoked_at FROM node_secrets "
                         "WHERE host = ?", (host,)).fetchone()
        if r is None or not r["ciphertext"] or r["revoked_at"]:
            raise JoinError("not_provisioned", f"no sealed secret for host {host!r}")
        if r["fetched_at"] is None:
            conn.execute("UPDATE node_secrets SET fetched_at = ? WHERE host = ?",
                         (_iso(_utc(now)), host))
            db.log_event(conn, None, ACTOR, "node_sealed_fetch", {"host": host})
    return r["ciphertext"]


# The one step the hub runs itself, before any revoker (leave() calls _begin_leave for it).
STEP_LEAVING = "status_leaving"


def _begin_leave(host: str, now_s: str) -> Outcome:
    """The FIRST step of a live leave: the row becomes `leaving` and its sealed bundle is voided,
    in one transaction. From the next request on, the token service answers this host 403
    (`left`): the CEO's rule that a node that left can never get the token again starts here,
    not after the slow steps. Idempotent; a `left` row is never moved back."""
    with db.get_conn() as conn:
        conn.execute("UPDATE hosts SET status = ?, updated_at = ? WHERE host = ? AND status != ?",
                     (STATUS_LEAVING, now_s, host, STATUS_LEFT))
        conn.execute("UPDATE node_secrets SET revoked_at = COALESCE(revoked_at, ?), "
                     "ciphertext = NULL WHERE host = ?", (now_s, host))
    return Outcome(True, f"status {STATUS_LEAVING}, token service refuses {host}")


def plan_leave(conn, host: str) -> list[Step]:
    others = conn.execute(
        "SELECT host FROM hosts WHERE host != ? AND COALESCE(status, '') != ? "
        "ORDER BY host", (host, STATUS_LEFT),
    ).fetchall()
    steps = [
        Step(STEP_LEAVING, host,
             f"set {host} to `{STATUS_LEAVING}` and void its sealed bundle: the token service "
             f"refuses it from this moment"),
        Step("tailscale_device", host, f"remove the tailnet device and pre-auth key of {host}"),
        Step("github_deploy_key", host, f"delete the deploy key(s) registered for {host}"),
    ]
    for r in others:
        steps.append(Step(
            "authorized_keys", r["host"],
            f"remove {host}'s dispatch key and admin pubkey line from authorized_keys on {r['host']}",
            host))
    return steps


def leave(host: str, *, live: bool = False,
          revokers: Mapping[str, Revoker] | None = None,
          now: datetime | None = None) -> dict:
    """Plan (live=False) or run (live=True) the revocation of `host`.

    live=False never calls a revoker and never writes to the hub. live=True
    runs the steps in order: first `status_leaving` (the hub's own write: the row becomes
    `leaving`, so the token service refuses the host at once), then `revokers` (default
    default_revokers()) once per other step, catching whatever a revoker raises as a failed
    step. Only a run where every step is ok marks the row `left`; any failure leaves it
    `leaving`, still refused, and a re-run finishes the job. The exception is the first step:
    if `status_leaving` itself fails the row may still be issuing, so NO other step runs, the
    answer is `partial` and every step is in `left_behind`.
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

    table = default_revokers() if revokers is None else revokers
    results = []
    stopped = False
    for s in steps:
        if stopped:
            # status_leaving failed: the row may still be issuing the token. Deleting the node's
            # Tailscale device and deploy key now would cut a node the hub still serves, and the
            # operator would think it had left. Nothing else runs; a re-run starts again here.
            results.append({"kind": s.kind, "target": s.target, "what": s.what, "ok": False,
                            "detail": f"not run: the {STEP_LEAVING} step failed"})
            continue
        revoker = (lambda step: _begin_leave(step.target, _iso(_utc(now)))) \
            if s.kind == STEP_LEAVING else table.get(s.kind)
        if revoker is None:
            out = Outcome(False, "no revoker for this step")
        else:
            try:
                out = revoker(s)
            except Exception as exc:  # one failed step must not stop the others
                out = Outcome(False, f"{type(exc).__name__}: {str(exc)[:200]}")
        results.append({"kind": s.kind, "target": s.target, "what": s.what,
                        "ok": out.ok, "detail": out.detail})
        stopped = s.kind == STEP_LEAVING and not out.ok
    left_behind = [f"{r['kind']}:{r['target']}" for r in results if not r["ok"]]
    status = STATUS_LEFT if not left_behind else "partial"
    try:
        with db.get_conn() as conn:
            if not left_behind:
                conn.execute("UPDATE hosts SET status = ?, updated_at = ? WHERE host = ?",
                             (STATUS_LEFT, _iso(_utc(now)), host))
            # Names only: a revoker's detail text can carry a provider's error body.
            db.log_event(conn, None, ACTOR, "join_leave",
                         {"host": host, "status": status, "left_behind": left_behind})
    except Exception:
        if not stopped:
            raise
        # The hub already failed on step 1; the answer below is the record. Do not turn it into
        # a traceback because the audit row could not be written either.
    return {"host": host, "live": True, "status": status, "steps": results,
            "left_behind": left_behind}


# ---------------------------------------------------------------- rotate after leave (F8)

# Leaving stops the hub serving a node the token; it does not recall a token the node already
# received. The hub hands a node exactly infisical_setup.NODE_SECRET_NAMES (W4.2b), so that list is
# exact, not a guess. docs/ops/hq-join.md carries the procedure.
ROTATE_DOC = 'docs/ops/hq-join.md, "After a leave: rotate what the node could read"'


def rotate_scope() -> dict:
    """What `leave --live` tells the operator to rotate: {where: [secret NAMES]}. A name list
    only: no value is read, held or returned."""
    return {f"{infisical_setup.NODE_PROJECT}/prod": list(infisical_setup.NODE_SECRET_NAMES)}


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
    a.add_argument("--deploy-pubkey", default=None,
                   help="the node's ssh-ed25519 public key line, for its GitHub deploy key "
                        "(without it the node gets none)")
    st = sub.add_parser("status", help="joined nodes: status, approval and key fingerprint")
    st.add_argument("--host", default=None)
    ap = sub.add_parser("approve", help="approve a pending host after comparing its key "
                                        "fingerprint with the one join.sh printed on the node")
    ap.add_argument("--host", required=True)
    ap.add_argument("--fingerprint", required=True,
                    help=f"last {FINGERPRINT_LEN} chars of the node's age recipient, "
                         f"as read on the node")
    pr = sub.add_parser("provision", help=f"seal an approved pending host's token bundle and "
                                          f"register its deploy key (needs {TOKEN_URL_ENV}; the "
                                          f"live GitHub leg needs {W42_FLAG}=1)")
    pr.add_argument("--host", required=True)
    se = sub.add_parser("sealed", help="print the armored ciphertext stored for a host")
    se.add_argument("--host", required=True)
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
                         args.hq_root, args.pubkey, deploy_pubkey=args.deploy_pubkey)
            if args.deploy_pubkey is None:
                print(f"hq_join: no --deploy-pubkey: {args.host} gets no GitHub deploy key",
                      file=sys.stderr)
            print(json.dumps({"ok": True, **res}))
            return 0
        if args.verb == "status":
            return _print_status(node_status(args.host))
        if args.verb == "approve":
            res = approve(args.host, args.fingerprint)
            print(json.dumps({"ok": True, **res}))
            return 0
        if args.verb == "provision":
            res = provision(args.host)
            print(json.dumps({"ok": True, **res}))
            return 0
        if args.verb == "sealed":
            sys.stdout.write(sealed_ciphertext(args.host).rstrip("\n") + "\n")
            return 0
        if args.verb == "leave":
            res = leave(args.host, live=args.live)
            return _print_leave(res, rotate_scope() if args.live and not res.get("note") else None)
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
    except (sealed.SealError, OSError) as exc:
        # provision's own failures arrive as JoinError; this is the sealer failing
        # before it ran. Type and a cut message, never a body.
        print(f"hq_join: failed ({type(exc).__name__}): {str(exc)[:200]}", file=sys.stderr)
        return 1


def _print_status(rows: list) -> int:
    if not rows:
        print("hq_join: no node has joined through hq_join")
    for r in rows:
        if r["awaiting_approval"]:
            gate = "AWAITING APPROVAL"
        else:
            gate = f"approved {r['approved_at']}" if r["approved_at"] else "-"
        print(f"{r['host']}  {r['status']}  {r['os']}  fingerprint {r['fingerprint']}  {gate}")
    if any(r["awaiting_approval"] for r in rows):
        print("hq_join: approve only when the fingerprint matches the one join.sh printed on the "
              "node's own screen; `approve --host <name> --fingerprint <8 chars>`")
    return 0


def _print_rotate(host: str, rotate: dict) -> None:
    """The closing block of `leave --live`: secret NAMES only, never a value."""
    print(f"hq_join: ROTATE what {host} could read. Leaving stops the hub serving it the token "
          f"again; it does not recall a token it already received.")
    for where, names in rotate.items():
        print(f"  {where}: " + (", ".join(names) if names else "(none)"))
    print(f"  procedure: {ROTATE_DOC}")


def _print_leave(res: dict, rotate: dict | None = None) -> int:
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
        code = 0
    else:
        print(f"hq_join: {res['host']} NOT marked left; left behind: "
              + ", ".join(res["left_behind"])
              + f". It stays `{STATUS_LEAVING}` (the token service keeps refusing it); "
                f"run the same leave again.")
        code = 1
    if rotate is not None:   # last on purpose: the output of a live leave ends with it
        _print_rotate(res["host"], rotate)
    return code


if __name__ == "__main__":
    sys.exit(main())
