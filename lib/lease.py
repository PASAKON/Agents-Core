"""Hub leases. Identity and administrative capabilities belong to the launcher.

No connection is opened on import. Configure a Service at the authenticated
boundary; ordinary callers cannot select priority, approval or an override role.
All mutation callbacks run in a SERIALIZABLE transaction with bounded retries.
The fake repository used by the scenario suite is not a production fallback.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import threading
import time
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = {"claimed", "acknowledged"}
PENDING = {"waiting", "awaiting_approval"}


class LeaseError(RuntimeError):
    pass


class LeaseLost(LeaseError):
    pass


def stamp(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def encoded(value):
    return json.dumps(value, default=lambda x: x.isoformat() if isinstance(x, datetime) else str(x))


def validate_policy(policy):
    p = dict(policy)
    if p.get("kind") not in {"mutex", "pool", "rate"}:
        raise ValueError("invalid resource kind")
    for key in ("capacity", "heartbeat_s", "max_hold_s", "queue_cap"):
        if type(p.get(key)) is not int or p[key] <= 0:
            raise ValueError(f"invalid {key}")
    if p["kind"] == "mutex" and p["capacity"] != 1:
        raise ValueError("mutex capacity must be one")
    if p["kind"] == "rate" and (type(p.get("window_s")) is not int or p["window_s"] <= 0):
        raise ValueError("invalid rate window")
    if p["max_hold_s"] < 2 * p["heartbeat_s"]:
        raise ValueError("max_hold must cover two heartbeats")
    if p.get("on_hub_down", "fail_closed") not in {"fail_closed", "uncoordinated"}:
        raise ValueError("invalid hub-down policy")
    if p.get("paid") and p.get("on_hub_down") != "fail_closed":
        raise ValueError("paid resources must fail closed")
    return p


class Registry:
    """Resolve exact names before patterns and freeze reviewed policy values."""

    def __init__(self, path=ROOT / "config/resources.yaml", *, references=None):
        document = yaml.safe_load(Path(path).read_text())
        self.version = document["version"]
        if type(self.version) is not int or self.version < 1:
            raise ValueError("invalid registry version")
        self.defaults = document.get("defaults", {})
        self.rows = document["resources"]
        if references is None:
            references = {}
            for source in ("hosts", "plans"):
                references.update(yaml.safe_load((ROOT / f"config/{source}.yaml").read_text()))
        self.references = references
        seen = set()
        for row in self.rows:
            key = row.get("name", row.get("pattern"))
            if not isinstance(key, str) or key in seen or ("name" in row) == ("pattern" in row):
                raise ValueError("duplicate or invalid registry name")
            seen.add(key)
            if "alias" not in row:
                p = {**self.defaults, **row}
                if "capacity_from" in row or "rate_from" in row:
                    p.setdefault("capacity", 1)  # validation only, never admission
                    if "rate_from" in row:
                        p.setdefault("window_s", 1)
                validate_policy(p)

    @staticmethod
    def match(pattern, name):
        parts = re.split(r"(<[a-z_]+>)", pattern)
        expression = "".join(f"(?P<{s[1:-1]}>.+)" if s.startswith("<") else re.escape(s) for s in parts)
        match = re.fullmatch(expression, name)
        return None if match is None else match.groupdict()

    def resolve(self, name, _seen=()):
        if not isinstance(name, str) or not name or name in _seen:
            raise ValueError("invalid name or alias cycle")
        exact = [(r, {}) for r in self.rows if r.get("name") == name]
        matches = exact or [(r, m) for r in self.rows if "pattern" in r
                            and (m := self.match(r["pattern"], name)) is not None]
        if len(matches) != 1:
            raise ValueError("unknown or ambiguous resource")
        row, fields = matches[0]
        def expand(s):
            for k, v in fields.items():
                s = s.replace(f"<{k}>", v)
            return s
        if "alias" in row:
            return self.resolve(expand(row["alias"]), (*_seen, name))
        p = {**self.defaults, **row, "policy_version": self.version}
        for key in ("capacity_from", "rate_from"):
            if key in p:
                value = self.references
                for part in expand(p[key]).split("."):
                    value = value.get(part) if isinstance(value, dict) else None
                if value is None:
                    raise LeaseError("unverified_capacity")
                if key == "capacity_from":
                    p["capacity"] = value
                else:
                    p["capacity"], p["window_s"] = value["grants"], value["window_s"]
        validate_policy(p)
        if p.get("enabled", True) is not True:
            raise LeaseError("disabled_resource")
        if name.startswith(("chrome:", "proj:", "browser_operator:")) and p["on_hub_down"] != "fail_closed":
            raise ValueError("exclusive resources must fail closed")
        if "project" in fields:
            path = fields.get("path", "")
            if not path or ".." in path.replace("\\", "/").split("/") or "{" in path or "}" in path:
                raise ValueError("unsafe or unexpanded project path")
            p["project"] = fields["project"]
            name = f"proj:{fields['project']}:path:*"  # conservative project-wide mode
        return name, p


@dataclass(frozen=True)
class Identity:
    session: str
    priority: int = 10
    admin: str | None = None
    # Optional verified host/process identity for the injected liveness observer.
    evidence: dict = field(default_factory=dict)


class ProbeLiveness:
    """Adapt the existing probes without run-status/spawn-grace filtering.

    verify_instance validates the host boot and PID start identity on the owning
    host. Remote/unreachable identities return None; local PID reuse is never
    treated as proof about a remote owner. A surviving session wins over a
    replaced child PID after compaction.
    """
    def __init__(self, verify_instance, session_probe, *, pid_probe=None, tmux_probe=None):
        from lib.run_liveness import probe_pid, probe_tmux
        self.verify_instance = verify_instance
        self.session_probe = session_probe
        self.pid_probe = pid_probe or probe_pid
        self.tmux_probe = tmux_probe or probe_tmux

    def __call__(self, owner, evidence):
        session = self.session_probe(owner, evidence)
        if session is True:
            return True
        if self.verify_instance(evidence) is not True:
            return None
        values = (self.pid_probe(evidence), self.tmux_probe(evidence), session)
        if any(v is True for v in values):
            return True
        return False if all(v is False for v in values) else None


@dataclass
class Result:
    state: str
    request_id: str | None = None
    token: int | None = None
    reason: str | None = None
    position: int | None = None
    expires_at: str | None = None
    grants: dict = field(default_factory=dict)


@dataclass
class State:
    now: datetime
    resources: dict = field(default_factory=dict)
    waiters: dict = field(default_factory=dict)
    events: dict = field(default_factory=dict)


def resource_row(name, p):
    return dict(name=name, kind=p["kind"], project=p.get("project"), capacity=p["capacity"],
                window_s=p.get("window_s"), heartbeat_s=p["heartbeat_s"], max_hold_s=p["max_hold_s"],
                policy_version=p.get("policy_version", 1), policy=p, holders={},
                cooling_until=datetime.min.replace(tzinfo=timezone.utc), quota_epoch=0,
                next_check_at=None)


def event(s, resource, kind, owner, *, request=None, token=None, payload=None, wake=False, key=None):
    key = key or f"{kind}:{uuid4()}"
    if key not in s.events:
        s.events[key] = dict(resource=resource, request_id=request, event_key=key,
                             kind=kind, at=s.now, fence=token,
                             quota_epoch=s.resources[resource]["quota_epoch"], actor=owner,
                             payload=payload or {}, deliver_after=s.now if wake else None,
                             delivered_at=None, attempts=0)
    return s.events[key]


def room(s, resource):
    r = s.resources[resource]
    if r["kind"] != "rate":
        return len(r["holders"]) < r["capacity"]
    cutoff = s.now - timedelta(seconds=r["window_s"])
    used = sum(e["kind"] == "grant" and e["resource"] == resource
               and e["quota_epoch"] == r["quota_epoch"] and e["at"] > cutoff
               for e in s.events.values())
    return r["cooling_until"] <= s.now and used < r["capacity"]


# This is the grant linearization point, including FIFO, capacity, rate debit,
# waiter claim and durable wake. No SELECT-then-INSERT grant path exists.
GRANT_SQL = """
WITH head AS MATERIALIZED (
 SELECT * FROM lease_waiters WHERE resource = ? AND state = 'waiting'
 ORDER BY priority, enqueued_at, enqueue_seq LIMIT 1
), granted AS (
 UPDATE leases l SET holders = l.holders || jsonb_build_object(
  h.request_id::text, jsonb_build_object('owner', h.owner_session,
   'token', nextval('lease_fence_seq'), 'started_at', now(),
   'expires_at', now() + make_interval(secs => LEAST(2*l.heartbeat_s,l.max_hold_s))))
 FROM head h WHERE l.name = ? AND h.request_id = ?::uuid
 AND ((l.kind IN ('mutex','pool') AND
       (SELECT count(*) FROM jsonb_object_keys(l.holders)) < l.capacity)
  OR (l.kind = 'rate' AND l.cooling_until <= now() AND
      (SELECT count(*) FROM lease_events e WHERE e.resource = l.name
       AND e.kind = 'grant' AND e.quota_epoch = l.quota_epoch
       AND e.at > now()-make_interval(secs => l.window_s)) < l.capacity))
 RETURNING l.name, l.holders -> ?::text AS holder, l.quota_epoch
), claimed AS (
 UPDATE lease_waiters w SET state = 'claimed', fence = (g.holder->>'token')::bigint,
 claim_until = (g.holder->>'expires_at')::timestamptz
 FROM granted g WHERE w.request_id = ?::uuid RETURNING w.*
)
INSERT INTO lease_events(resource,request_id,event_key,kind,fence,quota_epoch,actor,payload,deliver_after)
SELECT c.resource,c.request_id,'grant:' || c.fence,'grant',c.fence,g.quota_epoch,
 c.owner_session,jsonb_build_object('wake',true), CASE WHEN ? THEN now() ELSE NULL END
FROM claimed c JOIN granted g ON c.resource = g.name RETURNING fence
"""


class PgStore:
    """Repository adapter; serializes sorted resource rows, never process locks.

    C1 deliberately locks the small registry for a scheduler pass. This is safe
    for intersecting groups; a later optimization may narrow the lock set.
    """

    def __init__(self, connect=None):
        if connect is None:
            from lib.db import get_conn
            connect = get_conn
        self.connect = connect

    @contextmanager
    def transaction(self):
        with self.connect() as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            conn.execute("SET LOCAL statement_timeout = '5s'")
            conn.execute("SET LOCAL lock_timeout = '2s'")
            conn.execute("SELECT name FROM leases ORDER BY name FOR UPDATE").fetchall()
            unit = PgUnit(conn)
            yield unit
            unit.sync()


class PgUnit:
    def __init__(self, conn):
        self.conn = conn
        self.reload()

    def reload(self):
        c = self.conn
        now = c.execute("SELECT now() AS now").fetchone()["now"]
        def rows(table, key):
            result = {}
            for row in c.execute(f"SELECT * FROM {table}").fetchall():
                d = dict(row)
                for k in ("request_id", "group_id"):
                    if d.get(k) is not None:
                        d[k] = str(d[k])
                result[d[key]] = d
            return result
        self.state = State(now, rows("leases", "name"), rows("lease_waiters", "request_id"),
                           rows("lease_events", "event_key"))
        self.saved = deepcopy(self.state)

    def sync(self):
        """Persist non-grant transitions under the resource locks.

        Holder admission is exclusively grant(); this path handles expiry,
        renew, release and administration after owner/fence validation.
        """
        for table, current, previous, key, json_fields, generated in (
            ("leases", self.state.resources, self.saved.resources, "name", {"holders", "policy"}, set()),
            ("lease_waiters", self.state.waiters, self.saved.waiters, "request_id", {"payload", "approval"}, {"enqueue_seq"}),
            ("lease_events", self.state.events, self.saved.events, "event_key", {"payload"}, {"event_id"}),
        ):
            for ident, row in current.items():
                old = previous.get(ident)
                if old == row:
                    continue
                cols = [k for k in row if k not in generated]
                values = [encoded(row[k]) if k in json_fields and row[k] is not None else row[k] for k in cols]
                marks = ["?::jsonb" if k in json_fields else "?" for k in cols]
                if old is None:
                    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(marks)}) RETURNING *"
                    returned = dict(self.conn.execute(sql, values).fetchone())
                    for k in generated:
                        row[k] = returned[k]
                else:
                    assignments = ','.join(f"{k}={m}" for k, m in zip(cols, marks))
                    self.conn.execute(f"UPDATE {table} SET {assignments} WHERE {key}=?", (*values, ident))
        self.saved = deepcopy(self.state)

    def grant(self, request_id, wake):
        self.sync()
        w = self.state.waiters[request_id]
        result = self.conn.execute(GRANT_SQL, (w["resource"], w["resource"], request_id,
                                               request_id, request_id, wake)).fetchone()
        if result is None:
            raise LeaseError("grant_conflict")  # roll back the whole group
        self.reload()


def mailbox_wake(e):
    """Outbox delivery is at-least-once; event_key is the receiver dedup key."""
    session = e["actor"]
    if not session:
        return True
    role, separator, sid = session.partition("-")
    if not separator or not sid:
        return False  # identity without a mailbox address; never broadcast
    from lib import mailbox
    from tools.mail_wake import wake
    mailbox.send(role, sid, f"lease {e['kind']}: {e['resource']} request={e['request_id']} event={e['event_key']}",
                 "lease", "hub", subject="Lease ready" if e["kind"] == "grant" else "Lease stopped",
                 kind="ask", prio="urgent")
    return bool(wake(session, label="Lease ready").get("woke"))


class Service:
    def __init__(self, store=None, registry=None, *, observer=None, deliver=mailbox_wake, admission=None):
        self.store = store if store is not None else PgStore()
        self.registry = registry if registry is not None else Registry()
        # An observer returns False only after authoritative identity-aware death.
        # Missing/unreachable probes are None, never a local-PID guess for another host.
        self.observer = observer or (lambda owner, evidence: None)
        self.deliver = deliver
        self.admission = admission or (lambda policy: not policy.get("admission"))
        self.changed = threading.Condition()
        self._scheduler_stop = threading.Event()
        self._scheduler_thread = None

    def start_scheduler(self):
        """Start the hub owner's reaper/outbox supervisor (one per service).

        HTTP/launcher integration starts this on its long-lived hub process.
        Short-lived CLI holders still own their explicit renewals.
        """
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        self._scheduler_stop.clear()
        def supervise():
            while not self._scheduler_stop.is_set():
                delay = 5.0
                try:
                    self.tick()
                    def next_delay(tx):
                        checks = [5.0]
                        for r in tx.state.resources.values():
                            checks.append(float(r["heartbeat_s"]))
                            if r["next_check_at"] is not None:
                                checks.append(max(0.05, (r["next_check_at"]-tx.state.now).total_seconds()))
                        return min(checks)
                    delay = self.run(next_delay)
                except Exception:
                    pass  # fail closed; retry the durable state after reconnection
                self._scheduler_stop.wait(delay)
        self._scheduler_thread = threading.Thread(target=supervise, daemon=True, name="lease-scheduler")
        self._scheduler_thread.start()

    def close(self):
        self._scheduler_stop.set()
        if self._scheduler_thread:
            self._scheduler_thread.join()

    def run(self, operation):
        for attempt in range(5):
            try:
                with self.store.transaction() as tx:
                    result = operation(tx)
                with self.changed:
                    self.changed.notify_all()
                return result
            except Exception as exc:
                if getattr(exc, "sqlstate", None) not in {"40001", "40P01", "23505"} or attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))

    def dead(self, w):
        try:
            return self.observer(w["owner_session"], w["payload"].get("identity", {})) is False
        except Exception:
            return False  # unavailable probes are unknown, not confirmed death

    def reap(self, tx):
        s = tx.state
        groups = {}
        for w in s.waiters.values():
            if w["state"] in PENDING | ACTIVE:
                groups.setdefault(w["group_id"], []).append(w)
        for rows in groups.values():
            dead = any(self.dead(w) for w in rows)
            held = [(w, s.resources[w["resource"]],
                     s.resources[w["resource"]]["holders"].get(w["request_id"])) for w in rows]
            expired = any(h and s.now >= stamp(h["expires_at"]) for _, _, h in held)
            capped = any(h and s.now >= stamp(h["started_at"]) + timedelta(seconds=r["max_hold_s"])
                         for _, r, h in held)
            if not (dead or expired or capped):
                continue
            # Expiry of any member revokes the group, never leaves partial authority.
            unacked = all(w["state"] == "claimed" for w in rows) and not dead
            reconcile = unacked and any(r["kind"] == "rate" for _, r, _ in held)
            for w, r, holder in held:
                if w["state"] in PENDING:
                    w["state"] = "cancelled" if dead else w["state"]
                    continue
                r["holders"].pop(w["request_id"], None)
                if reconcile:
                    # Keep the durable claim for an authenticated reconciler;
                    # never charge another submission on an ambiguous retry.
                    w["payload"]["reconcile_required"] = True
                    w["state"] = "claimed"
                else:
                    w["state"] = "waiting" if unacked else "done"
                retry = unacked and not reconcile
                event(s, r["name"], "max_hold" if capped else "unacked_expired" if retry else "expired",
                      w["owner_session"], request=w["request_id"], token=w["fence"], wake=capped)
                w["fence"] = w["claim_until"] = None

    def schedule(self, tx, arrival=None):
        self.reap(tx)
        s = tx.state
        groups = {}
        for w in sorted(s.waiters.values(), key=lambda w: (w["priority"], w["enqueued_at"], w["enqueue_seq"])):
            if w["state"] == "waiting":
                groups.setdefault(w["group_id"], []).append(w["request_id"])
        blocked = set()
        for group, ids in groups.items():
            s = tx.state
            rows = [s.waiters[i] for i in ids]
            names = {w["resource"] for w in rows}
            if blocked & names or not all(room(s, n) and self.admission(s.resources[n]["policy"]) for n in names):
                blocked.update(names)
                continue
            for w in sorted(rows, key=lambda w: w["resource"]):
                tx.grant(w["request_id"], wake=group != arrival)
            if group == arrival:
                for i in ids:
                    tx.state.waiters[i]["state"] = "acknowledged"
        s = tx.state
        for r in s.resources.values():
            checks = [stamp(h["expires_at"]) for h in r["holders"].values()]
            if r["cooling_until"] > s.now:
                checks.append(r["cooling_until"])
            if r["kind"] == "rate":
                checks.extend(e["at"] + timedelta(seconds=r["window_s"]) for e in s.events.values()
                              if e["resource"] == r["name"] and e["kind"] == "grant"
                              and e["quota_epoch"] == r["quota_epoch"] and
                              e["at"] + timedelta(seconds=r["window_s"]) > s.now)
            r["next_check_at"] = min(checks) if checks else None

    @staticmethod
    def result(s, request_id, identity):
        row = s.waiters.get(request_id)
        if row is None or row["owner_session"] != identity.session:
            return Result("refused", reason="unknown_request")
        rows = [w for w in s.waiters.values() if w["group_id"] == row["group_id"]]
        grants = {}
        for w in rows:
            h = s.resources[w["resource"]]["holders"].get(w["request_id"])
            if h and stamp(h["expires_at"]) > s.now:
                grants[w["resource"]] = dict(request_id=w["request_id"], **h)
        state = "granted" if len(grants) == len(rows) else row["state"]
        if state in ACTIVE:
            state = "expired"
        first = grants.get(row["resource"], {})
        queue = sorted((w for w in s.waiters.values() if w["resource"] == row["resource"]
                        and w["state"] == "waiting"), key=lambda w: (w["priority"], w["enqueued_at"], w["enqueue_seq"]))
        position = next((i + 1 for i, w in enumerate(queue) if w["request_id"] == request_id), None)
        return Result(state, request_id, first.get("token"), position=position,
                      expires_at=first.get("expires_at"), grants=grants)

    def acquire(self, names, identity, *, purpose, idempotency_key=None):
        if not identity.session or not purpose:
            raise ValueError("authenticated session and purpose are required")
        names = [names] if isinstance(names, str) else names
        resolved = dict(self.registry.resolve(n) for n in names)
        if not resolved:
            raise ValueError("empty lease group")
        key = idempotency_key or str(uuid4())
        group = str(uuid4())
        ids = {n: str(uuid4()) for n in sorted(resolved)}
        def operation(tx):
            s = tx.state
            for n, p in sorted(resolved.items()):
                if n not in s.resources:
                    s.resources[n] = resource_row(n, p)
                elif s.resources[n]["policy"] != p:
                    # Config reductions never evict holders; only later admission changes.
                    row = resource_row(n, p)
                    for field in ("holders", "cooling_until", "quota_epoch", "next_check_at"):
                        row[field] = s.resources[n][field]
                    s.resources[n] = row
            existing = [w for w in s.waiters.values() if w["owner_session"] == identity.session
                        and w["idempotency_key"] == key]
            if existing:
                if {w["resource"] for w in existing} != set(resolved):
                    raise ValueError("idempotency key reused for another group")
                self.schedule(tx)
                return self.result(tx.state, sorted(existing, key=lambda w: w["resource"])[0]["request_id"], identity)
            self.reap(tx)
            for n, p in sorted(resolved.items()):
                count = sum(w["resource"] == n and w["state"] in PENDING for w in s.waiters.values())
                if count >= p["queue_cap"]:
                    return Result("refused", reason=f"queue_full:{p['queue_cap']}")
            approval = any(p.get("needs_ceo_card") for p in resolved.values())
            seq = max((w["enqueue_seq"] for w in s.waiters.values()), default=0)
            for i, n in enumerate(sorted(resolved)):
                s.waiters[ids[n]] = dict(request_id=ids[n], resource=n, group_id=group,
                    owner_session=identity.session, task_id=None, priority=identity.priority,
                    enqueue_seq=seq+i+1, enqueued_at=s.now,
                    state="awaiting_approval" if approval else "waiting", idempotency_key=key,
                    purpose=purpose, payload={"identity": identity.evidence}, approval=None,
                    fence=None, claim_until=None)
            self.schedule(tx, arrival=group)
            return self.result(tx.state, ids[sorted(resolved)[0]], identity)
        try:
            result = self.run(operation)
        except Exception as exc:
            from lib.db_pg import HubConnectError, is_operational_error
            if not isinstance(exc, (ConnectionError, HubConnectError)) and not is_operational_error(exc):
                raise
            advisory = all(p.get("on_hub_down") == "uncoordinated" and not p.get("paid")
                           for p in resolved.values())
            return Result("uncoordinated" if advisory else "refused", reason="hub_down")
        self.dispatch_outbox()
        return result

    def status(self, request_id, identity):
        # No expiry cleanup or outbox delivery: status is strictly read-only.
        return self.run(lambda tx: self.result(tx.state, request_id, identity))

    @staticmethod
    def authorized(s, name, request_id, token, identity):
        r = s.resources.get(name)
        h = r and r["holders"].get(request_id)
        w = s.waiters.get(request_id)
        return bool(h and w and w["resource"] == name and w["owner_session"] == identity.session
                    and h["owner"] == identity.session and h["token"] == token
                    and s.now < stamp(h["expires_at"])
                    and s.now < stamp(h["started_at"]) + timedelta(seconds=r["max_hold_s"]))

    def valid(self, name, request_id, token, identity):
        return self.run(lambda tx: self.authorized(tx.state, name, request_id, token, identity))

    def guarded_write(self, name, request_id, token, identity, effect):
        """Serialize a DB effect with authority validation in the same transaction.

        effect receives the repository transaction and must be transactional and
        retry-safe. Browser/file effects need a far-side actuator, not this hook.
        """
        def operation(tx):
            if not self.authorized(tx.state, name, request_id, token, identity):
                raise LeaseLost("stale or expired fence")
            return effect(tx)
        return self.run(operation)

    def renew(self, name, request_id, token, identity):
        def operation(tx):
            self.reap(tx)
            s = tx.state
            valid = self.authorized(s, name, request_id, token, identity)
            if valid:
                r = s.resources[name]
                h = r["holders"][request_id]
                expires = min(s.now + timedelta(seconds=2*r["heartbeat_s"]),
                              stamp(h["started_at"]) + timedelta(seconds=r["max_hold_s"]))
                h["expires_at"] = expires.isoformat()
                s.waiters[request_id]["claim_until"] = expires
                s.waiters[request_id]["state"] = "acknowledged"
            self.schedule(tx)
            return valid
        result = self.run(operation)
        self.dispatch_outbox()
        return result

    def release(self, grants, identity):
        def operation(tx):
            s = tx.state
            if not all(self.authorized(s, n, g["request_id"], g["token"], identity) for n, g in grants.items()):
                return False
            for n, g in sorted(grants.items()):
                del s.resources[n]["holders"][g["request_id"]]
                s.waiters[g["request_id"]]["state"] = "done"
                event(s, n, "release", identity.session, request=g["request_id"], token=g["token"])
            self.schedule(tx)
            return True
        result = self.run(operation)
        self.dispatch_outbox()
        return result

    def cancel(self, request_id, identity):
        def operation(tx):
            s = tx.state
            w = s.waiters.get(request_id)
            if w is None or w["owner_session"] != identity.session:
                return False
            for row in s.waiters.values():
                if row["group_id"] == w["group_id"] and row["state"] in PENDING | ACTIVE:
                    s.resources[row["resource"]]["holders"].pop(row["request_id"], None)
                    row["state"] = "cancelled"
                    event(s, row["resource"], "cancelled", identity.session, request=row["request_id"])
            self.schedule(tx)
            return True
        result = self.run(operation)
        self.dispatch_outbox()
        return result

    def tick(self):
        self.run(self.schedule)
        self.dispatch_outbox()

    def acknowledge(self, request_id, token, identity, *, failure=None):
        def operation(tx):
            s = tx.state
            w = s.waiters.get(request_id)
            if not w or not self.authorized(s, w["resource"], request_id, token, identity):
                return False
            if failure:
                w["payload"]["retry_reason"] = failure
                event(s, w["resource"], "dispatch_retry", identity.session,
                      request=request_id, payload={"failure": failure})
            else:
                w["state"] = "acknowledged"
            return True
        return self.run(operation)

    def administer(self, action, name, identity, *, reason, request_id=None,
                   token=None, card=None, until=None, provider_event_id=None):
        """Trusted server boundary only; no CLI role/approval flags.

        The authentication layer must bind verified cards and provider event IDs
        before calling. Ordinary lease clients never construct admin identities.
        """
        if identity.admin not in {"CEO", "CTO"} or not reason:
            return False
        if action in {"override", "approve"} and identity.admin != "CEO":
            return False
        if action == "approve" and not card:
            return False
        if action not in {"override", "approve", "release", "cool", "reset"}:
            raise ValueError("unknown administrative action")
        def operation(tx):
            s = tx.state
            r = s.resources[name]
            key = f"provider:{name}:{provider_event_id}" if provider_event_id else None
            if key and key in s.events:
                return True
            if action in {"cool", "reset"}:
                if action == "cool":
                    if until is None:
                        # No guessed reset: explicit administrative reset required.
                        r["cooling_until"] = datetime.max.replace(tzinfo=timezone.utc)
                    else:
                        r["cooling_until"] = max(r["cooling_until"], stamp(until))
                else:
                    r["cooling_until"] = s.now
                    r["quota_epoch"] += 1
            elif action == "approve":
                w = s.waiters.get(request_id)
                if not w or w["resource"] != name or w["state"] != "awaiting_approval":
                    return False
                for row in s.waiters.values():
                    if row["group_id"] == w["group_id"]:
                        row["state"] = "waiting"
                        row["enqueued_at"] = s.now
                        row["approval"] = {"card": card, "request_id": row["request_id"],
                                           "resource": row["resource"], "purpose": row["purpose"],
                                           "actor": identity.session, "at": s.now.isoformat()}
            else:
                targets = list(r["holders"]) if action == "override" else [request_id]
                if action == "release" and (request_id not in r["holders"] or
                                             r["holders"][request_id]["token"] != token):
                    return False
                for target in targets:
                    h = r["holders"].pop(target)
                    s.waiters[target]["state"] = "done"
                    event(s, name, "stop", h["owner"], request=target, token=h["token"], wake=True)
                if action == "override":
                    request = str(uuid4())
                    s.waiters[request] = dict(request_id=request, resource=name, group_id=request,
                        owner_session=identity.session, task_id=None, priority=-1,
                        enqueue_seq=max((w["enqueue_seq"] for w in s.waiters.values()), default=0)+1,
                        enqueued_at=s.now, state="awaiting_approval" if r["policy"].get("needs_ceo_card") else "waiting",
                        idempotency_key=request, purpose=reason, payload={}, approval=None,
                        fence=None, claim_until=None)
            event(s, name, "release_override" if action == "release" else action,
                  identity.session, request=request_id, payload={"role": identity.admin,
                  "reason": reason, "card": card}, key=key)
            self.schedule(tx, arrival=request if action == "override" else None)
            if action == "override":
                return self.result(tx.state, request, identity)
            return True
        result = self.run(operation)
        self.dispatch_outbox()
        return result

    def import_snapshot(self, source, rows, *, fail=False):
        """Stage a frozen snapshot supplied by a later migration adapter.

        No JSONL files are read or changed. Raw records and completion receipts
        live in events, preserving duplicate source ordinals across retries.
        """
        name = f"import:{source}"
        def operation(tx):
            s = tx.state
            if name not in s.resources:
                _, p = self.registry.resolve(name)
                s.resources[name] = resource_row(name, p)
            known = {e["payload"]["row"]["task_id"] for e in s.events.values()
                     if e["kind"] == "import" and e["resource"] == name}
            for ordinal, row in enumerate(rows):
                key = f"import:{source}:{ordinal}"
                if key in s.events and s.events[key]["payload"]["row"] != row:
                    raise ValueError("source changed after frozen snapshot")
                event(s, name, "import", "migration", key=key,
                      payload={"source": source, "ordinal": ordinal, "row": deepcopy(row)})
                owner = row["task_id"]
                if owner not in known:
                    request = str(uuid4())
                    s.waiters[request] = dict(request_id=request, resource=name, group_id=request,
                        owner_session=owner, task_id=owner, priority=10,
                        enqueue_seq=max((w["enqueue_seq"] for w in s.waiters.values()), default=0)+1,
                        enqueued_at=s.now, state="waiting", idempotency_key=f"import:{source}:{owner}",
                        purpose="frozen migration", payload={}, approval=None, fence=None, claim_until=None)
                    known.add(owner)
            if fail:
                raise OSError("injected import transaction failure")
        self.run(operation)

    def dispatch_outbox(self):
        # Delivery happens after the grant commit. Failure leaves the claim and
        # event durable, and a later tick retries it. Never undo a committed grant.
        try:
            pending = self.run(lambda tx: deepcopy([e for e in tx.state.events.values()
                if e["deliver_after"] is not None and e["deliver_after"] <= tx.state.now
                and e["delivered_at"] is None]))
        except Exception:
            return
        for e in pending:
            try:
                delivered = self.deliver(e)
            except Exception:
                delivered = False
            def mark(tx):
                row = tx.state.events[e["event_key"]]
                row["attempts"] += 1
                if delivered:
                    row["delivered_at"] = tx.state.now
            try:
                self.run(mark)
            except Exception:
                pass  # crash/commit failure => at-least-once redelivery

    def wait(self, request_id, identity, wait_s=0):
        if wait_s < 0:
            raise ValueError("negative wait")
        deadline = time.monotonic() + wait_s
        while True:
            self.tick()
            result = self.status(request_id, identity)
            if result.state not in PENDING or time.monotonic() >= deadline:
                return result
            # Local condition is a hint. Cross-process durable wake is the mailbox;
            # bounded refresh also handles expiry/cooling with no releasing client.
            with self.changed:
                self.changed.wait(min(0.5, max(0, deadline-time.monotonic())))


_configured = None
_local = threading.local()


def configure(service, identity):
    """Install the service and authenticated launcher identity at the boundary."""
    global _configured
    _configured = service, identity


def current():
    if _configured is None:
        raise LeaseError("launcher must configure an authenticated lease service")
    return _configured


def acquire(name, *, purpose, idempotency_key=None):
    if getattr(_local, "holding", False):
        raise LeaseError("declare all resources in one group; nested acquisition is forbidden")
    service, identity = current()
    return service.acquire(name, identity, purpose=purpose, idempotency_key=idempotency_key)


def status(request_id):
    service, identity = current()
    return service.status(request_id, identity)


def wait(request_id, wait_s=0):
    service, identity = current()
    return service.wait(request_id, identity, wait_s)


def renew(name, request_id, token):
    service, identity = current()
    return service.renew(name, request_id, token, identity)


def release(name, request_id, token):
    service, identity = current()
    return service.release({name: dict(request_id=request_id, token=token)}, identity)


class Handle:
    def __init__(self, service, identity, result):
        self.service, self.identity = service, identity
        self.request_id, self.token, self.expires_at = result.request_id, result.token, result.expires_at
        self.grants = result.grants
        self.lost = threading.Event()
        self.stop = threading.Event()
        self.thread = None

    def assert_valid(self):
        if self.lost.is_set() or not all(self.service.valid(n, g["request_id"], g["token"], self.identity)
                                         for n, g in self.grants.items()):
            self.lost.set()
            raise LeaseLost("lease authority lost; stop guarded work")

    def heartbeat(self, interval):
        while not self.stop.wait(interval):
            try:
                if not all(self.service.renew(n, g["request_id"], g["token"], self.identity)
                           for n, g in self.grants.items()):
                    self.lost.set()
                    return
            except Exception:
                self.lost.set()
                return


@contextmanager
def lease_many(names, *, purpose, wait_s=0):
    if getattr(_local, "holding", False):
        raise LeaseError("declare all resources in one group; nested acquisition is forbidden")
    service, identity = current()
    _local.holding = True
    handle = None
    request = None
    try:
        result = service.acquire(names, identity, purpose=purpose)
        request = result.request_id
        if result.state in PENDING:
            result = service.wait(request, identity, wait_s)
        if result.state != "granted":
            if request:
                service.cancel(request, identity)
            raise LeaseError(result.reason or result.state)
        handle = Handle(service, identity, result)
        interval = min(service.registry.resolve(n)[1]["heartbeat_s"] for n in result.grants)
        handle.thread = threading.Thread(target=handle.heartbeat, args=(interval,), daemon=True,
                                         name=f"lease-{request}")
        handle.thread.start()
        yield handle
        handle.assert_valid()
    finally:
        try:
            if handle:
                handle.stop.set()
                handle.thread.join()
                try:
                    if not service.release(handle.grants, identity):
                        handle.lost.set()
                except Exception:
                    handle.lost.set()  # hub TTL remains authoritative during partition
            elif request:
                try:
                    service.cancel(request, identity)
                except Exception:
                    pass  # do not mask the original backend error
        finally:
            _local.holding = False


def lease(name, *, purpose, wait_s=0):
    return lease_many([name], purpose=purpose, wait_s=wait_s)
