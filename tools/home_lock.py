"""Browser-home locks: two sessions never drive one Chrome at once (CEO 2026-10-14).

Before you use a Chrome that the login inventory found (Console
`scripts/relay-inventory.mjs`, or the reuse gate in `relay-request.mjs open`),
take its lock. Release it when you are done. A lock that nobody renews ends on
its TTL.

    python3 tools/home_lock.py acquire home:winbox:9224 [--owner cto-xxxx] [--ttl 1800] [--purpose "images"]
    python3 tools/home_lock.py renew   home:winbox:9224 [--owner …] [--ttl 1800]
    python3 tools/home_lock.py release home:winbox:9224 [--owner …]
    python3 tools/home_lock.py list

    from tools.home_lock import home_lock
    with home_lock("home:winbox:9224", purpose="ChatGPT images") as lock:
        ...              # lock.renew() on a long job
                         # HomeLockHeld if another owner has it

Key format: `home:<host>:<port>`. The host is the hub `hosts` name (contabo,
mac, winbox) and the port is the Chrome's CDP port on that host. The owner is a
session id (cto-xxxx) or a task id. Only the owner renews or releases a lock,
with the same class of token that took it (a worker token cannot release a
C-level's lock); the CEO's own Console session may release any.
The default owner comes from this process's env: WORKER_TASK_ID, otherwise
<role>-<session id>, resolved the way ask_run.py resolves it.
The TTL defaults to 1800 s and must be between 60 s and 6 h.
This key format was agreed with PH OrgRestructure on 2026-10-14. P3 adds
`render:<host>` keys.

Transport: the locks live at the front-door Console (MoonieX-Console
docs/relay.md §12, /api/relay/locks/*). They are reached through the Run hub's
address and org token, the same ones ask_run.py uses (RUN_INBOX_URL,
RUN_INBOX_TOKEN or ~/.config/mooniex/run-inbox.token). Every call goes through
_transport() and nowhere else. To move the store to the hub, change that one
function; no caller changes.

Exit codes: 0 ok · 2 held by another owner, or a bad argument · 3 hub unreachable or refused.
stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import ask_run  # noqa: E402

KEY_RE = re.compile(r"^home:[a-z0-9]{1,24}:\d{1,5}$")
OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,63}$")
TTL_DEFAULT_S = 1800
TTL_MIN_S, TTL_MAX_S = 60, 6 * 3600
LOCKS_PATH = "/api/relay/locks"
EXIT_OK, EXIT_HELD, EXIT_HUB = 0, 2, 3

HubError = ask_run.HubError


class HomeLockHeld(Exception):
    """Another owner holds the lock and it has not expired."""

    def __init__(self, key: str, holder: dict):
        self.key, self.holder = key, holder
        super().__init__(f"{key} is held by {holder.get('owner', '?')} until {holder.get('expiresAt', '?')}"
                         + (f" ({holder['purpose']})" if holder.get("purpose") else ""))


def default_owner(env: dict | None = None) -> str:
    """This process's session or task id, or ''."""
    env = os.environ if env is None else env
    task = (env.get("WORKER_TASK_ID") or "").strip()
    if task:
        return task
    role, sid = ask_run._env_box(env)
    sid = (env.get("ORG_SESSION_ID") or sid or "").strip()
    if not sid:
        return ""
    return sid if not role or sid.startswith(role + "-") else f"{role}-{sid}"


def _check(key: str, owner: str, ttl: int | None = None) -> None:
    if not KEY_RE.match(key or "") or not 1 <= int(key.rsplit(":", 1)[1]) <= 65535:
        raise ValueError("key must be home:<host>:<port>, e.g. home:winbox:9224")
    if not OWNER_RE.match(owner or ""):
        raise ValueError("owner must be a session or task id (pass --owner, or run inside a session)")
    if ttl is not None and not (TTL_MIN_S <= ttl <= TTL_MAX_S):
        raise ValueError(f"ttl must be {TTL_MIN_S}-{TTL_MAX_S} seconds")


def _transport(method: str, op: str, body: dict | None = None) -> tuple[int, dict]:
    """The one place a lock call leaves this process: (HTTP status, JSON body).
    A 409 comes back as data (held / not the front door); other refusals and
    network errors raise HubError. The token goes into the header and nowhere else."""
    url = ask_run.base_url() + LOCKS_PATH + (f"/{op}" if op else "")
    headers = {"Authorization": "Bearer " + ask_run.load_token(), "Accept": "application/json",
               "User-Agent": "mooniex-home-lock/1"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with ask_run._OPENER.open(req, timeout=ask_run.HTTP_TIMEOUT_S) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise HubError("the front door holds too many locks (256); release yours, or wait for TTLs") from None
        if e.code == 409:
            try:
                return 409, json.loads(e.read() or b"{}")
            except ValueError:
                return 409, {}
        raise ask_run._hub_error(e) from None
    except (urllib.error.URLError, OSError) as e:
        raise HubError(f"hub unreachable at {ask_run.base_url()}: {getattr(e, 'reason', e)}", transient=True) from None


def _not_front_door(body: dict) -> HubError | None:
    if body.get("error") == "not_front_door":
        return HubError(f"that Console keeps no locks; point RUN_INBOX_URL at the front door {body.get('frontDoor', '')}")
    return None


def acquire(key: str, owner: str | None = None, ttl: int = TTL_DEFAULT_S, purpose: str = "") -> dict:
    """Take the lock (or renew your own). Returns the lock; raises HomeLockHeld."""
    owner = owner or default_owner()
    _check(key, owner, ttl)
    status, body = _transport("POST", "acquire", {"key": key, "owner": owner, "ttl": ttl, "purpose": purpose})
    if status == 409:
        err = _not_front_door(body)
        if err:
            raise err
        raise HomeLockHeld(key, body.get("holder") or {})
    return body.get("lock") or {}


def renew(key: str, owner: str | None = None, ttl: int = TTL_DEFAULT_S) -> dict:
    """Push your own lock's expiry out. Same call as acquire, so it also takes a free lock."""
    return acquire(key, owner, ttl)


def release(key: str, owner: str | None = None) -> bool:
    """Release your own lock. False when you did not hold it (expired, or someone else's)."""
    owner = owner or default_owner()
    _check(key, owner)
    status, body = _transport("POST", "release", {"key": key, "owner": owner})
    if status == 409:
        raise _not_front_door(body) or HubError("hub refused (409)")
    return bool(body.get("released"))


def list_locks() -> list[dict]:
    status, body = _transport("GET", "")
    if status == 409:
        raise _not_front_door(body) or HubError("hub refused (409)")
    return list(body.get("locks") or [])


class _Held:
    def __init__(self, key: str, owner: str, ttl: int, lock: dict):
        self.key, self.owner, self.ttl, self.lock = key, owner, ttl, lock

    def renew(self, ttl: int | None = None) -> dict:
        self.lock = renew(self.key, self.owner, ttl or self.ttl)
        return self.lock


@contextmanager
def home_lock(key: str, owner: str | None = None, ttl: int = TTL_DEFAULT_S, purpose: str = "") -> Iterator[_Held]:
    """Hold the lock for the block; release it on the way out, also on an error."""
    owner = owner or default_owner()
    held = _Held(key, owner, ttl, acquire(key, owner, ttl, purpose))
    try:
        yield held
    finally:
        try:
            release(key, owner)
        except HubError as e:  # the TTL ends it anyway; say so and keep the block's own outcome
            print(f"home_lock: release of {key} failed ({e}); it expires at {held.lock.get('expiresAt', '?')}",
                  file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="home_lock.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="verb", required=True)
    for verb in ("acquire", "renew", "release"):
        s = sub.add_parser(verb)
        s.add_argument("key")
        s.add_argument("--owner", default="")
        if verb != "release":
            s.add_argument("--ttl", type=int, default=TTL_DEFAULT_S)
        if verb == "acquire":
            s.add_argument("--purpose", default="")
    sub.add_parser("list")
    sub.choices["list"].add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.verb in ("acquire", "renew"):
            lock = acquire(a.key, a.owner or None, a.ttl, getattr(a, "purpose", ""))
            print(f"{lock.get('key', a.key)} held by {lock.get('owner')} until {lock.get('expiresAt')}")
        elif a.verb == "release":
            ok = release(a.key, a.owner or None)
            print(f"{a.key} released" if ok else f"{a.key} was not held by you (expired or someone else's)")
        else:
            locks = list_locks()
            if a.json:
                print(json.dumps(locks, indent=2))
            for lk in [] if a.json else locks:
                print(f"{lk.get('key'):<22} {lk.get('owner'):<20} until {lk.get('expiresAt')}"
                      + (f"  {lk['purpose']}" if lk.get("purpose") else ""))
            if not locks and not a.json:
                print("(no locks held)")
        return EXIT_OK
    except HomeLockHeld as e:
        print(f"home_lock: {e}", file=sys.stderr)
        return EXIT_HELD
    except ValueError as e:
        print(f"home_lock: {e}", file=sys.stderr)
        return EXIT_HELD
    except (HubError, ask_run.Refused) as e:
        print(f"home_lock: {e}", file=sys.stderr)
        return EXIT_HUB


if __name__ == "__main__":
    sys.exit(main())
