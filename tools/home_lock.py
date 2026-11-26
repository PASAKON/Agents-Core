"""Browser-home locks: two sessions never drive one Chrome at once (CEO 2026-10-14).

Before you use a Chrome that the login inventory found (Console
`scripts/relay-inventory.mjs`, or the reuse gate in `relay-request.mjs open`),
take its lock. Release it when you are done. A lock that nobody renews ends on
its TTL.

    python3 tools/home_lock.py acquire home:winbox:9224 [--owner cto-xxxx] [--ttl 1800] [--purpose "images"] [--wait 300]
    python3 tools/home_lock.py renew   home:winbox:9224 [--owner …] [--ttl 1800]
    python3 tools/home_lock.py release home:winbox:9224 [--owner …]
    python3 tools/home_lock.py queue   home:winbox:9224 [--json]
    python3 tools/home_lock.py list

    from tools.home_lock import home_lock
    with home_lock("home:winbox:9224", purpose="ChatGPT images", wait_s=300) as lock:
        ...              # lock.renew() on a long job
                         # HomeLockHeld if another owner has it (or wait_s times out)

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

With LEASE_DB_URL set, calls use lib.lease instead. LEASE_OWNER_SESSION is
the trusted identity; --owner cannot impersonate another session. TTLs are
bounded by the resource's max_hold_s policy. Console cutover is Phase C3;
do not enable mixed Console/lease writers for a shared home.

Exit codes: 0 ok · 2 held by another owner, or a bad argument · 3 hub unreachable or refused.
stdlib only.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
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
QUEUE_DIR = ROOT / "state" / "home-queue"
HEARTBEAT_TTL_S = 120.0
POLL_MIN_S, POLL_MAX_S = 10.0, 15.0
_THREAD_LOCK = threading.Lock()

HubError = ask_run.HubError


def _clock() -> float:
    return time.time()


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _poll_delay() -> float:
    return random.uniform(POLL_MIN_S, POLL_MAX_S)


def _owner_alive(owner: str) -> bool:
    return bool(owner)


def _pid_alive(pid: int) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            raw = stat_path.read_text(encoding="utf-8", errors="ignore")
            rparen = raw.rfind(")")
            if rparen != -1 and raw[rparen + 1:].lstrip().startswith("Z"):
                return False
        except OSError:
            pass
    return True


class HomeLockHeld(Exception):
    """Another owner holds the lock and it has not expired."""

    def __init__(self, key: str, holder: dict, message: str | None = None, position: int | None = None):
        self.key, self.holder, self.position = key, holder, position
        if message is None:
            message = (f"{key} is held by {holder.get('owner', '?')} until {holder.get('expiresAt', '?')}"
                       + (f" ({holder['purpose']})" if holder.get("purpose") else ""))
        super().__init__(message)


def default_owner(env: dict | None = None) -> str:
    """This process's session or task id, or ''."""
    env = os.environ if env is None else env
    if env.get("LEASE_DB_URL") and env.get("LEASE_OWNER_SESSION"):
        return env["LEASE_OWNER_SESSION"]
    task = (env.get("WORKER_TASK_ID") or "").strip()
    if task:
        return task
    role, sid = ask_run._env_box(env)
    sid = (env.get("ORG_SESSION_ID") or sid or "").strip()
    if not sid:
        return ""
    return sid if not role or sid.startswith(role + "-") else f"{role}-{sid}"


def _check_key(key: str) -> None:
    if not KEY_RE.match(key or "") or not 1 <= int(key.rsplit(":", 1)[1]) <= 65535:
        raise ValueError("key must be home:<host>:<port>, e.g. home:winbox:9224")


def _check(key: str, owner: str, ttl: int | None = None, wait_s: float | None = None) -> None:
    _check_key(key)
    if not OWNER_RE.match(owner or ""):
        raise ValueError("owner must be a session or task id (pass --owner, or run inside a session)")
    if ttl is not None and not (TTL_MIN_S <= ttl <= TTL_MAX_S):
        raise ValueError(f"ttl must be {TTL_MIN_S}-{TTL_MAX_S} seconds")
    if wait_s is not None and wait_s < 0:
        raise ValueError("wait must be >= 0 seconds")


def _key_safe(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", key)


def _queue_path(key: str) -> Path:
    return QUEUE_DIR / f"{_key_safe(key)}.jsonl"


def _ticket_alive(ticket: dict, now: float) -> bool:
    owner = ticket.get("owner")
    if not owner or not _owner_alive(owner):
        return False
    try:
        hb = float(ticket["heartbeat"])
    except (KeyError, TypeError, ValueError):
        return False
    if now - hb > HEARTBEAT_TTL_S:
        return False
    pid = ticket.get("pid")
    if pid is not None:
        try:
            if not _pid_alive(int(pid)):
                return False
        except (TypeError, ValueError):
            return False
    return True


@contextmanager
def _locked_queue_file(key: str) -> Iterator[list[dict]]:
    path = _queue_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _THREAD_LOCK:
        with open(path, "a+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                tickets: list[dict] = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        if isinstance(row, dict):
                            tickets.append(row)
                    except ValueError:
                        continue
                yield tickets
                f.seek(0)
                f.truncate(0)
                for row in tickets:
                    f.write(json.dumps(row, separators=(",", ":")) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _enqueue_or_touch(
    key: str,
    owner: str,
    purpose: str = "",
    now: float | None = None,
    pid: int | None = None,
) -> tuple[int, list[dict]]:
    now = _clock() if now is None else now
    pid = os.getpid() if pid is None else pid
    with _locked_queue_file(key) as tickets:
        alive = [t for t in tickets if _ticket_alive(t, now)]
        pos = 0
        for idx, t in enumerate(alive, 1):
            if t.get("owner") == owner:
                t["heartbeat"] = now
                t["pid"] = pid
                if purpose:
                    t["purpose"] = purpose
                pos = idx
                break
        if pos == 0:
            alive.append({
                "key": key,
                "owner": owner,
                "pid": pid,
                "purpose": purpose,
                "enqueuedAt": now,
                "heartbeat": now,
            })
            pos = len(alive)
        tickets[:] = alive
        return pos, [dict(t) for t in alive]


def _dequeue(key: str, owner: str, now: float | None = None) -> None:
    now = _clock() if now is None else now
    path = _queue_path(key)
    if not path.exists():
        return
    with _locked_queue_file(key) as tickets:
        tickets[:] = [
            t for t in tickets
            if t.get("owner") != owner and _ticket_alive(t, now)
        ]


def _read_queue(key: str, now: float | None = None) -> list[dict]:
    now = _clock() if now is None else now
    path = _queue_path(key)
    if not path.exists():
        return []
    with _locked_queue_file(key) as tickets:
        alive = [t for t in tickets if _ticket_alive(t, now)]
        tickets[:] = alive
        return [dict(t) for t in alive]


def _is_expired(expires_at: Any, now: float) -> bool:
    if expires_at is None or expires_at == "":
        return False
    if isinstance(expires_at, (int, float)):
        return float(expires_at) <= now
    if isinstance(expires_at, str):
        try:
            return float(expires_at) <= now
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp() <= now
        except ValueError:
            return False
    return False


def _transport(method: str, op: str, body: dict | None = None) -> tuple[int, dict]:
    """The one place a lock call leaves this process: (HTTP status, JSON body).
    A 409 comes back as data (held / not the front door); other refusals and
    network errors raise HubError. The token goes into the header and nowhere else."""
    if os.environ.get("LEASE_DB_URL"):
        return _lease_transport(op, body)
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


def _lease_transport(op: str, body: dict | None) -> tuple[int, dict]:
    from lib import lease as leases
    try:
        service, actor = leases.default_service()
        locks = service.held_resources("home:")
        def public(lock):
            return {k: (datetime.fromtimestamp(v, timezone.utc).isoformat() if k == "expiresAt" else v)
                    for k, v in lock.items() if k not in {"request_id", "token"}}
        if not op:
            return 200, {"locks": [public(lk) for lk in locks]}
        key, owner = body["key"], body["owner"]
        if owner != actor.session:
            raise HubError("owner must match trusted LEASE_OWNER_SESSION")
        held = next((lk for lk in locks if lk["key"] == key), None)
        if op == "release":
            return 200, {"released": bool(held and held["owner"] == owner and
                service.release(held["request_id"], actor, held["token"]))}
        if held and held["owner"] != owner:
            return 409, {"holder": public(held)}
        if not held:
            result = service.acquire(key, actor, purpose=body.get("purpose") or "browser home")
            if result.state != "granted":
                if result.request_id:
                    service.cancel(result.request_id, actor)
                if result.state == "waiting":
                    return 409, {"holder": {}}
                raise HubError("lease refused: " + (result.reason or result.state))
            service.acknowledge(result.request_id, actor)
            held = dict(request_id=result.request_id, token=result.token)
        if not service.renew(held["request_id"], actor, held["token"], ttl_s=body["ttl"]):
            raise HubError("home lease expired before renewal")
        lock = next(lk for lk in service.held_resources("home:") if lk["key"] == key)
        return 200, {"lock": public(lock)}
    except HubError:
        raise
    except Exception as exc:
        raise HubError("lease service unavailable or refused") from exc


def _not_front_door(body: dict) -> HubError | None:
    if body.get("error") == "not_front_door":
        return HubError(f"that Console keeps no locks; point RUN_INBOX_URL at the front door {body.get('frontDoor', '')}")
    return None


def _acquire_once(key: str, owner: str, ttl: int = TTL_DEFAULT_S, purpose: str = "") -> dict:
    status, body = _transport("POST", "acquire", {"key": key, "owner": owner, "ttl": ttl, "purpose": purpose})
    if status == 409:
        err = _not_front_door(body)
        if err:
            raise err
        raise HomeLockHeld(key, body.get("holder") or {})
    return body.get("lock") or {}


def _current_holder(key: str, now: float | None = None) -> dict | None:
    now = _clock() if now is None else now
    for lk in list_locks():
        if lk.get("key") == key:
            if _is_expired(lk.get("expiresAt"), now):
                return None
            return lk
    return None


def _is_lock_free_or_expired(key: str, owner: str, now: float | None = None) -> tuple[bool, dict | None]:
    holder = _current_holder(key, now)
    if holder is None or holder.get("owner") == owner:
        return True, holder
    return False, holder


def acquire(
    key: str,
    owner: str | None = None,
    ttl: int = TTL_DEFAULT_S,
    purpose: str = "",
    wait_s: float = 0,
) -> dict:
    """Take the lock (or renew your own). With wait_s > 0, queue FIFO when held."""
    owner = owner or default_owner()
    _check(key, owner, ttl, wait_s)
    if not wait_s:
        return _acquire_once(key, owner, ttl, purpose)

    start = _clock()
    deadline = start + float(wait_s)
    acquired = False
    last_holder: dict = {}
    pos, _ = _enqueue_or_touch(key, owner, purpose, start)
    try:
        if pos == 1:
            try:
                lock = _acquire_once(key, owner, ttl, purpose)
                acquired = True
                _dequeue(key, owner, start)
                return lock
            except HomeLockHeld as exc:
                last_holder = exc.holder or {}
        else:
            holder = _current_holder(key, start)
            if holder and holder.get("owner") == owner:
                lock = _acquire_once(key, owner, ttl, purpose)
                acquired = True
                _dequeue(key, owner, start)
                return lock
            if holder:
                last_holder = holder

        while True:
            now = _clock()
            remaining = deadline - now
            if remaining <= 0:
                pos, tickets = _enqueue_or_touch(key, owner, purpose, now)
                holder = _current_holder(key, now) or last_holder
                behind = holder.get("owner") if holder and holder.get("owner") != owner else None
                if not behind:
                    ahead = [t["owner"] for t in tickets if t.get("owner") and t.get("owner") != owner]
                    behind = ahead[0] if ahead else (last_holder.get("owner") or "?")
                raise HomeLockHeld(
                    key,
                    holder or {"owner": behind},
                    message=f"{key}: still queued behind {behind}, position {pos}",
                    position=pos,
                )

            sleep_s = min(remaining, _poll_delay())
            _sleep(sleep_s)

            now = _clock()
            pos, _ = _enqueue_or_touch(key, owner, purpose, now)
            if pos != 1:
                continue
            free, holder = _is_lock_free_or_expired(key, owner, now)
            if holder:
                last_holder = holder
            if not free:
                continue
            try:
                lock = _acquire_once(key, owner, ttl, purpose)
                acquired = True
                _dequeue(key, owner, now)
                return lock
            except HomeLockHeld as exc:
                last_holder = exc.holder or last_holder
    finally:
        if not acquired:
            _dequeue(key, owner)


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


def queue_status(key: str) -> dict:
    """Return current holder and live FIFO waiters for key."""
    _check_key(key)
    now = _clock()
    holder = _current_holder(key, now)
    holder_owner = holder.get("owner") if holder else None
    raw_waiters = _read_queue(key, now)
    waiters: list[dict] = []
    for t in raw_waiters:
        if holder_owner and t.get("owner") == holder_owner:
            continue
        enq = float(t.get("enqueuedAt", now))
        waiters.append({
            "position": len(waiters) + 1,
            "owner": t["owner"],
            "purpose": t.get("purpose") or "",
            "waited_s": max(0, int(now - enq)),
            "pid": t.get("pid"),
            "enqueuedAt": enq,
            "heartbeat": float(t.get("heartbeat", now)),
        })
    return {"key": key, "holder": holder, "waiters": waiters}


class _Held:
    def __init__(self, key: str, owner: str, ttl: int, lock: dict):
        self.key, self.owner, self.ttl, self.lock = key, owner, ttl, lock

    def renew(self, ttl: int | None = None) -> dict:
        self.lock = renew(self.key, self.owner, ttl or self.ttl)
        return self.lock


@contextmanager
def home_lock(
    key: str,
    owner: str | None = None,
    ttl: int = TTL_DEFAULT_S,
    purpose: str = "",
    wait_s: float = 0,
) -> Iterator[_Held]:
    """Hold the lock for the block; release it on the way out, also on an error."""
    owner = owner or default_owner()
    held = _Held(key, owner, ttl, acquire(key, owner, ttl, purpose, wait_s=wait_s))
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
            s.add_argument("--wait", type=float, default=0)
    q = sub.add_parser("queue")
    q.add_argument("key")
    q.add_argument("--json", action="store_true")
    sub.add_parser("list")
    sub.choices["list"].add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.verb in ("acquire", "renew"):
            lock = acquire(
                a.key,
                a.owner or None,
                a.ttl,
                getattr(a, "purpose", ""),
                wait_s=getattr(a, "wait", 0) or 0,
            )
            print(f"{lock.get('key', a.key)} held by {lock.get('owner')} until {lock.get('expiresAt')}")
        elif a.verb == "release":
            ok = release(a.key, a.owner or None)
            print(f"{a.key} released" if ok else f"{a.key} was not held by you (expired or someone else's)")
        elif a.verb == "queue":
            info = queue_status(a.key)
            if a.json:
                print(json.dumps(info, indent=2))
            else:
                h = info["holder"]
                if h:
                    p_str = f" ({h['purpose']})" if h.get("purpose") else ""
                    print(f"holder: {h.get('owner', '?')} until {h.get('expiresAt', '?')}{p_str}")
                else:
                    print("holder: (none)")
                if not info["waiters"]:
                    print("waiters: (none)")
                for w in info["waiters"]:
                    p_str = f"  ({w['purpose']})" if w.get("purpose") else ""
                    print(f"  {w['position']}. {w['owner']}  waited {w['waited_s']}s{p_str}")
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
