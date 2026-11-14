"""Hub lease service. No connection or environment lookup occurs on import.

Gateways inject an authenticated Actor and connection factory. CLI identity is
bound by its trusted launcher, never a caller-supplied role/priority flag.
MemoryStore is a transaction fake; all scheduling/transitions live in Service.
PostgresStore uses the repository's bound SQL API and hub time exclusively.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid


class LeaseError(RuntimeError):
    pass


class LeaseLost(LeaseError):
    pass


class HubUnavailable(LeaseError):
    pass


class RetryGrant(LeaseError):
    pass


@dataclass(frozen=True)
class Actor:
    session: str
    role: str = "worker"
    priority: int = 10


@dataclass
class Result:
    state: str
    request_id: str | None = None
    token: int | None = None
    reason: str | None = None
    position: int | None = None
    expires_at: float | None = None
    tokens: dict = field(default_factory=dict)


def validate_policy(p):
    p = dict(p)
    for key in ("capacity", "heartbeat_s", "max_hold_s", "queue_cap"):
        if type(p.get(key)) is not int or p[key] <= 0:
            raise ValueError(f"invalid {key}")
    if p.get("kind") not in {"mutex", "pool", "rate"}:
        raise ValueError("invalid kind")
    if p["kind"] == "mutex" and p["capacity"] != 1:
        raise ValueError("mutex capacity must be one")
    if p["max_hold_s"] < 2 * p["heartbeat_s"]:
        raise ValueError("max_hold_s must cover two heartbeats")
    if p["kind"] == "rate" and (type(p.get("window_s")) is not int or p["window_s"] <= 0):
        raise ValueError("invalid rate window")
    if p.get("on_hub_down") not in {"fail_closed", "uncoordinated"}:
        raise ValueError("invalid hub failure policy")
    if p.get("paid") and p["on_hub_down"] != "fail_closed":
        raise ValueError("paid resources must fail closed")
    return p


class Registry:
    def __init__(self, path=None, *, references=None):
        import yaml
        root = Path(__file__).resolve().parents[1] / "config"
        self.doc = yaml.safe_load(Path(path or root / "resources.yaml").read_text())
        if not isinstance(self.doc, dict) or type(self.doc.get("version")) is not int:
            raise ValueError("invalid registry")
        self.references = references
        if references is None:
            self.references = {}
            for filename in ("hosts.yaml", "plans.yaml"):
                self.references.update(yaml.safe_load((root / filename).read_text()))
        self.rows = self.doc["resources"]
        self.patterns = []
        seen = set()
        for row in self.rows:
            key = row.get("name", row.get("pattern"))
            if not isinstance(key, str) or key in seen or ("name" in row) == ("pattern" in row):
                raise ValueError("duplicate or invalid resource name")
            seen.add(key)
            if any(c in key for c in "*?[]"):
                raise ValueError("wildcard patterns are ambiguous; use named segments")
            parts = key.split(":")
            regex = ":".join(f"(?P<{p[1:-1]}>[^:]+)" if p.startswith("<") and p.endswith(">") else re.escape(p) for p in parts)
            self.patterns.append((row, re.compile("^" + regex + "$")))
            merged = dict(self.doc["defaults"], **row)
            if "rate" in merged:
                if not isinstance(merged["rate"], dict):
                    raise ValueError("invalid rate")
                merged.update(capacity=merged["rate"].get("grants"), window_s=merged["rate"].get("window_s"))
            if not row.get("alias"):
                check_row = dict(merged)
                if row.get("capacity_from"):
                    check_row.setdefault("capacity", 1)
                if row.get("rate_from"):
                    check_row.setdefault("capacity", 1)
                    check_row.setdefault("window_s", 1)
                validate_policy(check_row)
            if merged.get("paid") and merged.get("on_hub_down") != "fail_closed":
                raise ValueError("paid resources must fail closed")
        # Reject overlapping patterns even before a particular name is requested.
        patterns = [r["pattern"].split(":") for r in self.rows if "pattern" in r]
        for i, a in enumerate(patterns):
            for b in patterns[i + 1:]:
                if len(a) == len(b) and all(x == y or x.startswith("<") or y.startswith("<") for x, y in zip(a, b)):
                    raise ValueError("ambiguous resource patterns")

    def resolve(self, name, _seen=()):
        if name in _seen:
            raise ValueError("alias cycle")
        if not isinstance(name, str) or not name or ".." in re.split(r"[:/]", name) or any(c in name for c in "*?[]\\"):
            raise ValueError("invalid resource name/path")
        matches = [(r, m.groupdict()) for r, regex in self.patterns if (m := regex.fullmatch(name))]
        exact = [v for v in matches if "name" in v[0]]
        matches = exact or matches
        if len(matches) != 1:
            raise ValueError("unknown or ambiguous resource")
        row, fields = matches[0]
        def expand(value):
            for k, v in fields.items():
                value = value.replace("<" + k + ">", v)
            return value
        if "alias" in row:
            target, policy = self.resolve(expand(row["alias"]), (*_seen, name))
            return target, dict(policy, enabled=policy.get("enabled", True) and row.get("enabled", True))
        p = dict(self.doc["defaults"], **row, policy_version=self.doc["version"])
        for key in ("capacity_from", "rate_from"):
            if key in p:
                value = self.references
                for segment in expand(p[key]).split("."):
                    value = value.get(segment) if isinstance(value, dict) else None
                if value is None:
                    p["enabled"] = False
                    p.setdefault("capacity", 1)  # disabled sentinel, never admitted
                    p.setdefault("window_s", 1)
                elif key == "rate_from":
                    p.update(capacity=value["grants"], window_s=value["window_s"])
                else:
                    p["capacity"] = value
        if "rate" in p:
            p.update(capacity=p["rate"]["grants"], window_s=p["rate"]["window_s"])
        if "project" in fields:
            if "path" in fields and (fields["path"].startswith("/") or fields["path"].endswith("/") or "//" in fields["path"] or "." in fields["path"].split("/")):
                raise ValueError("invalid resource name/path")
            p["project"] = fields["project"]
            # Conservative project-wide path mutex; all path callers share it.
            name = f"proj:{fields['project']}:path:__project__"
        if name.startswith(("chrome:", "screen:", "proj:")) and p["on_hub_down"] != "fail_closed":
            raise ValueError("exclusive resources must fail closed")
        return name, validate_policy(p)


def probe_owner_liveness(task: dict | None = None, *, pid_probe=None, tmux_probe=None,
                         session_ok: bool | None = None):
    """Lease liveness verdict using lib.run_liveness probes and vocabulary.

    Quiet is alive (True); unreachable/unknown is None (waits for TTL); only
    confirmed all-process/session death returns False.
    """
    from lib import run_liveness
    if task is None:
        return None if session_ok is None else bool(session_ok)
    pid_ok = (pid_probe or run_liveness.probe_pid)(task)
    tmux_ok = (tmux_probe or run_liveness.probe_tmux)(task)
    if pid_ok or tmux_ok or session_ok:
        return True
    if session_ok is False or ("pid" in task or "tmux_session" in task or "id" in task):
        return False
    return None


def _state():
    return {"resources": {}, "waiters": {}, "events": []}


class MemoryStore:
    """Isolated transactional fake with injected hub clock; never a fallback."""
    def __init__(self, clock=lambda: 0):
        self.clock = clock
        self.state = _state()
        self.lock = threading.RLock()
        self.serial = 0

    def run(self, fn, *, readonly=False):
        with self.lock:
            state = deepcopy(self.state)
            result = fn(state, self.clock(), self)
            if not readonly:
                self.state = state
            return result

    def grant(self, s, rows, now, arrival):
        for w in rows:
            self.serial += 1
            r = s["resources"][w["resource"]]
            p = r["policy"]
            h = dict(owner=w["owner_session"], token=self.serial, started_at=now,
                     expires_at=now + min(2 * p["heartbeat_s"], p["max_hold_s"]))
            r["holders"][w["request_id"]] = h
            w.update(state="acknowledged" if arrival else "claimed", fence=h["token"], claim_until=h["expires_at"])
            _event(s, w["resource"], "grant", w["owner_session"], now,
                   request_id=w["request_id"], fence=h["token"], quota_epoch=r["quota_epoch"],
                   event_key=f"grant:{h['token']}", payload={"wake": not arrival},
                   deliver_after=None if arrival else now)


def _event(s, resource, kind, actor, now, **kw):
    event = dict(resource=resource, kind=kind, actor=actor, at=now,
                 event_key=str(uuid.uuid4()), request_id=None, fence=None,
                 quota_epoch=None, payload={}, deliver_after=None,
                 delivered_at=None, attempts=0)
    event.update(kw)
    s["events"].append(event)
    return event


# The conditional UPDATE is the linearization point, not the earlier scheduler
# observation. SERIALIZABLE + a common resource-row write protects rate counts.
GRANT_SQL = """
WITH head AS MATERIALIZED (
 SELECT * FROM lease_waiters WHERE resource=? AND state='waiting'
 ORDER BY priority,enqueued_at,enqueue_seq LIMIT 1
), granted AS (
 UPDATE leases l SET holders=l.holders || jsonb_build_object(
 h.request_id::text,jsonb_build_object('owner',h.owner_session,
 'token',nextval('lease_fence_seq'), 'started_at',extract(epoch FROM now()),
 'expires_at',extract(epoch FROM now())+LEAST(2*l.heartbeat_s,l.max_hold_s)))
 FROM head h WHERE l.name=? AND h.request_id=?::uuid AND (
 (l.kind IN ('mutex','pool') AND (SELECT count(*) FROM jsonb_object_keys(l.holders))<l.capacity)
 OR (l.kind='rate' AND l.cooling_until<=now() AND (
   EXISTS (SELECT 1 FROM lease_events e WHERE e.resource=l.name AND e.kind='grant'
           AND e.request_id=h.request_id AND e.quota_epoch=l.quota_epoch)
   OR (SELECT count(DISTINCT e.request_id) FROM lease_events e
       WHERE e.resource=l.name AND e.kind='grant' AND e.quota_epoch=l.quota_epoch
       AND e.at>now()-make_interval(secs=>l.window_s))<l.capacity)))
 RETURNING l.name,l.quota_epoch,l.holders->?::text AS holder
), claimed AS (
 UPDATE lease_waiters w SET state=?, fence=(g.holder->>'token')::bigint,
 claim_until=to_timestamp((g.holder->>'expires_at')::double precision)
 FROM granted g WHERE w.request_id=?::uuid RETURNING w.*,g.quota_epoch
)
INSERT INTO lease_events(resource,request_id,event_key,kind,fence,quota_epoch,actor,payload,deliver_after)
SELECT resource,request_id,'grant:'||fence,'grant',fence,quota_epoch,owner_session,
 jsonb_build_object('wake',?::boolean),CASE WHEN ?::boolean THEN now() ELSE NULL END
FROM claimed RETURNING fence,extract(epoch FROM at)::double precision AS at
"""


class PostgresStore:
    """C1 uses coarse, sorted resource locks; no process-local authority/cache.

    connect must return lib.db_pg.Connection. Every operation opens its own
    connection, including the heartbeat thread. No implicit real-hub URL.
    """
    def __init__(self, connect):
        self.connect = connect

    def run(self, fn, *, readonly=False):
        for attempt in range(5):
            conn = self.connect()
            try:
                conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE" + (" READ ONLY" if readonly else ""))
                tx = _PGTransaction(conn)
                s = tx.load(readonly)
                now = float(conn.execute("SELECT extract(epoch FROM now())::double precision AS t").fetchone()["t"])
                result = fn(s, now, tx)
                if not readonly:
                    tx.flush(s)
                conn.commit()
                return result
            except Exception as exc:
                conn.rollback()
                if (getattr(exc, "sqlstate", None) not in {"40001", "40P01"} and not isinstance(exc, RetryGrant)) or attempt == 4:
                    raise
            finally:
                conn.close()
        raise LeaseError("serialization retry exhausted")


def _as_json(val):
    return json.loads(val) if isinstance(val, str) else val


class _PGTransaction:
    def __init__(self, conn):
        self.conn = conn
        self.before = _state()

    def load(self, readonly):
        s = _state()
        for row in self.conn.execute("SELECT name,policy,holders,quota_epoch,extract(epoch FROM cooling_until)::double precision AS cooling FROM leases ORDER BY name" + ("" if readonly else " FOR UPDATE")).fetchall():
            d = dict(row)
            policy = _as_json(d["policy"])
            holders = _as_json(d["holders"])
            # JSONB decoded by psycopg; no local clock is consulted.
            s["resources"][d["name"]] = dict(policy=policy, holders=holders,
                cooling_until=max(0, d["cooling"]),
                quota_epoch=d["quota_epoch"])
        for row in self.conn.execute("SELECT *,extract(epoch FROM enqueued_at)::double precision AS queued, extract(epoch FROM claim_until)::double precision AS deadline FROM lease_waiters").fetchall():
            d = dict(row)
            d.update(request_id=str(d["request_id"]), group_id=str(d["group_id"]),
                     payload=_as_json(d["payload"]), approval=_as_json(d["approval"]),
                     enqueued_at=d.pop("queued"), claim_until=d.pop("deadline"))
            s["waiters"][d["request_id"]] = d
        for row in self.conn.execute("SELECT *,extract(epoch FROM at)::double precision AS ts,extract(epoch FROM deliver_after)::double precision AS due,extract(epoch FROM delivered_at)::double precision AS delivered FROM lease_events ORDER BY event_id").fetchall():
            d = dict(row)
            d.update(payload=_as_json(d["payload"]), at=d.pop("ts"),
                     deliver_after=d.pop("due"), delivered_at=d.pop("delivered"))
            if d["request_id"] is not None:
                d["request_id"] = str(d["request_id"])
            s["events"].append(d)
        self.before = deepcopy(s)

        return s

    def flush(self, s):
        for name, r in s["resources"].items():
            if self.before["resources"].get(name) == r:
                continue
            p = r["policy"]
            self.conn.execute("""INSERT INTO leases(name,kind,project,capacity,window_s,heartbeat_s,max_hold_s,policy_version,policy,holders,cooling_until,quota_epoch,next_check_at)
              VALUES (?,?,?,?,?,?,?,?,?::jsonb,'{}'::jsonb,to_timestamp(?),?,now()+make_interval(secs=>?))
              ON CONFLICT(name) DO UPDATE SET policy=excluded.policy,capacity=excluded.capacity,
              policy_version=excluded.policy_version,heartbeat_s=excluded.heartbeat_s,max_hold_s=excluded.max_hold_s,
              cooling_until=excluded.cooling_until,quota_epoch=excluded.quota_epoch,next_check_at=excluded.next_check_at""",
              (name,p["kind"],p.get("project"),p["capacity"],p.get("window_s"),p["heartbeat_s"],p["max_hold_s"],p.get("policy_version",1),json.dumps(p),r["cooling_until"],r["quota_epoch"],p["heartbeat_s"]))
            old=self.before["resources"].get(name,{}).get("holders",{})
            if set(r["holders"])-set(old):
                raise LeaseError("holder creation must use atomic grant")
            for rid,h in old.items():
                if rid not in r["holders"]:
                    self.conn.execute("""UPDATE leases SET holders=holders-?::text WHERE name=?
                      AND holders->?::text->>'owner'=? AND (holders->?::text->>'token')::bigint=?""",
                      (rid,name,rid,h["owner"],rid,h["token"]))
                elif r["holders"][rid]!=h:
                    changed=self.conn.execute("""UPDATE leases SET holders=jsonb_set(holders,ARRAY[?::text,'expires_at'],
                      to_jsonb(LEAST(extract(epoch FROM now())+2*heartbeat_s,
                      (holders->?::text->>'started_at')::numeric+max_hold_s)))
                      WHERE name=? AND holders->?::text->>'owner'=?
                      AND (holders->?::text->>'token')::bigint=?
                      AND (holders->?::text->>'expires_at')::numeric>extract(epoch FROM now())
                      RETURNING name""",(rid,rid,name,rid,h["owner"],rid,h["token"],rid)).fetchone()
                    if not changed:
                        raise RetryGrant("renewal authority changed")
        for rid, w in s["waiters"].items():
            if self.before["waiters"].get(rid) == w:
                continue
            inserted=self.conn.execute("""INSERT INTO lease_waiters(request_id,resource,group_id,owner_session,task_id,priority,enqueued_at,state,idempotency_key,purpose,payload,approval,fence,claim_until)
              VALUES (?::uuid,?,?::uuid,?,?,?,to_timestamp(?),?,?,?,?::jsonb,?::jsonb,?,to_timestamp(?))
              ON CONFLICT(request_id) DO UPDATE SET state=excluded.state,payload=excluded.payload,
              approval=excluded.approval,fence=excluded.fence,claim_until=excluded.claim_until,enqueued_at=excluded.enqueued_at
              RETURNING enqueue_seq""",
              (rid,w["resource"],w["group_id"],w["owner_session"],w.get("task_id"),w["priority"],w["enqueued_at"],w["state"],w["idempotency_key"],w["purpose"],json.dumps(w["payload"]),json.dumps(w.get("approval")),w.get("fence"),w.get("claim_until"))).fetchone()
            w["enqueue_seq"]=inserted["enqueue_seq"]
        old = {e["event_key"]: e for e in self.before["events"]}
        for e in s["events"]:
            if old.get(e["event_key"]) == e:
                continue
            self.conn.execute("""INSERT INTO lease_events(resource,request_id,event_key,kind,at,fence,quota_epoch,actor,payload,deliver_after,delivered_at,attempts)
              VALUES (?,?::uuid,?,?,to_timestamp(?),?,?,?,?::jsonb,to_timestamp(?),to_timestamp(?),?)
              ON CONFLICT(event_key) DO UPDATE SET delivered_at=excluded.delivered_at,attempts=excluded.attempts""",
              (e["resource"],e["request_id"],e["event_key"],e["kind"],e["at"],e["fence"],e["quota_epoch"],e["actor"],json.dumps(e["payload"]),e["deliver_after"],e["delivered_at"],e["attempts"]))
        self.before = deepcopy(s)

    def grant(self, s, rows, now, arrival):
        self.flush(s)
        for w in rows:  # already in canonical resource order; all or rollback
            name, rid = w["resource"], w["request_id"]
            state = "acknowledged" if arrival else "claimed"
            row = self.conn.execute(GRANT_SQL, (name,name,rid,rid,state,rid,not arrival,not arrival)).fetchone()
            if not row:
                raise RetryGrant("conditional grant refused")
            r = s["resources"][name]
            p = r["policy"]
            h = dict(owner=w["owner_session"], token=row["fence"], started_at=now,
                     expires_at=now+min(2*p["heartbeat_s"],p["max_hold_s"]))
            r["holders"][rid] = h
            w.update(state=state,fence=h["token"],claim_until=h["expires_at"])
            _event(s,name,"grant",w["owner_session"],now,request_id=rid,fence=h["token"],
                   quota_epoch=r["quota_epoch"],event_key=f"grant:{h['token']}",
                   payload={"wake":not arrival},deliver_after=None if arrival else now)
        # These updates have already been written by the atomic pipeline.
        self.before = deepcopy(s)


class Service:
    def __init__(self, store, *, registry=None, liveness=None, deliver=None, approval_verifier=None, admission=None):
        self.store = store
        self.registry = registry
        self.liveness = liveness or (lambda owner: None)
        self.deliver = deliver
        self.approval_verifier = approval_verifier or (lambda *args: False)
        self.admission = admission or (lambda name, policy: not policy.get("admission"))
        self.policies = {}

    def configure(self, name, **policy):
        p = dict(kind="mutex", capacity=1, heartbeat_s=5,max_hold_s=30,window_s=20,
                 queue_cap=100,paid=False,on_hub_down="fail_closed",needs_ceo_card=False,
                 enabled=True,policy_version=1)
        p.update(policy)
        validate_policy(p)
        def op(s, now, tx):
            r = s["resources"].setdefault(name,dict(holders={},cooling_until=0,quota_epoch=0))
            if r.get("policy") and r["policy"]["kind"] != p["kind"]:
                raise ValueError("cannot change resource kind")
            r["policy"] = p
        self.store.run(op)
        self.policies[name] = p

    def _resolve(self, names):
        if isinstance(names, str):
            names = [names]
        if not names or any(not isinstance(n,str) or not n for n in names):
            raise ValueError("names must be a nonempty sequence")
        policies = {}
        resolved = []
        for n in names:
            if self.registry:
                n, p = self.registry.resolve(n)
                policies[n] = p
            resolved.append(n)
        return sorted(set(resolved)), policies

    @staticmethod
    def _rows(s, group):
        return sorted((w for w in s["waiters"].values() if w["group_id"] == group),key=lambda w:w["resource"])

    @staticmethod
    def _order(w):
        return w["priority"],w["enqueued_at"],w["enqueue_seq"]

    def _result(self, s, group):
        rows = self._rows(s,group)
        if not rows:
            return Result("refused",group,reason="unknown_request")
        tokens = {w["resource"]: w["fence"] for w in rows if w["state"] in {"claimed","acknowledged"}}
        if len(tokens) == len(rows):
            return Result("granted",group,next(iter(tokens.values())),expires_at=min(w["claim_until"] for w in rows),tokens=tokens)
        state = rows[0]["state"]
        position = 1 + sum(self._order(w)<self._order(rows[0]) for w in s["waiters"].values() if w["resource"]==rows[0]["resource"] and w["state"]=="waiting")
        return Result(state,group,position=position)

    def _schedule(self,s,now,tx,arrival=None):
        blocked = set()
        groups = {}
        for w in sorted(s["waiters"].values(),key=self._order):
            if w["state"] == "waiting":
                groups.setdefault(w["group_id"],[]).append(w)
        for group, rows in groups.items():
            rows.sort(key=lambda w:w["resource"])
            names = {w["resource"] for w in rows}
            if self.liveness(rows[0]["owner_session"]) is False:
                for w in rows:
                    w["state"] = "cancelled"
                continue
            room = not bool(names & blocked)
            for w in rows:
                name = w["resource"]
                r = s["resources"][name]
                p = r["policy"]
                room &= p.get("enabled",True) and self.admission(name,p)
                if p["kind"] == "rate":
                    receipts = [e for e in s["events"] if e["resource"]==name and e["kind"]=="grant" and e["quota_epoch"]==r["quota_epoch"]]
                    used = {e["request_id"] for e in receipts if e["at"]>now-p["window_s"]}
                    retry = any(e["request_id"]==w["request_id"] for e in receipts)
                    room &= now >= r["cooling_until"] and (retry or len(used)<p["capacity"])
                else:
                    room &= len(r["holders"])<p["capacity"]
            if not room:
                blocked.update(names)
                continue
            tx.grant(s,rows,now,group==arrival)

    def _reap(self,s,now):
        expired={}
        for name,r in s["resources"].items():
            for rid,h in r["holders"].items():
                dead = self.liveness(h["owner"]) is False
                capped = now >= h["started_at"]+r["policy"]["max_hold_s"]
                if dead or capped or now>=h["expires_at"]:
                    group=s["waiters"][rid]["group_id"]
                    expired[group]=expired.get(group,False) or capped
        for group,capped in expired.items():
            rows=self._rows(s,group)
            retry=all(w["state"]=="claimed" for w in rows) and self.liveness(rows[0]["owner_session"]) is not False
            for w in rows:
                name=w["resource"]
                h=s["resources"][name]["holders"].pop(w["request_id"],None)
                w["state"]="waiting" if retry else "done"
                if h:
                    _event(s,name,"max_hold" if capped else "expired",h["owner"],now,
                           request_id=w["request_id"],fence=h["token"],payload={"stop":capped},deliver_after=now if capped else None)

    def _mutate(self,fn):
        result = self.store.run(fn)
        try:
            self.deliver_outbox()
        except Exception:
            pass  # committed admission remains valid; outbox retries on next tick
        return result

    def acquire(self,names,actor,*,purpose="lease",idempotency_key=None,task_id=None,fail_at=None):
        if not isinstance(actor,Actor) or not actor.session:
            raise ValueError("authenticated actor required")
        if not purpose:
            raise ValueError("purpose required")
        names, policies = self._resolve(names)
        key = idempotency_key or str(uuid.uuid4())
        group = str(uuid.uuid4())
        ids = {n:str(uuid.uuid4()) for n in names}
        def op(s,now,tx):
            for n,p in policies.items():
                r = s["resources"].setdefault(n,dict(policy=p,holders={},cooling_until=0,quota_epoch=0))
                if r["policy"] != p:
                    raise LeaseError("policy snapshot differs; administrative migration required")
            if any(n not in s["resources"] for n in names):
                raise ValueError("unknown resource")
            if any(not s["resources"][n]["policy"].get("enabled",True) for n in names):
                return Result("refused",reason="disabled")
            existing = [w for w in s["waiters"].values() if w["owner_session"]==actor.session and w["idempotency_key"]==key]
            if existing:
                if sorted(w["resource"] for w in existing)!=names or any(w["purpose"]!=purpose for w in existing):
                    raise ValueError("idempotency key reused for different request")
                self._reap(s,now)
                self._schedule(s,now,tx)
                return self._result(s,existing[0]["group_id"])
            self._reap(s,now)
            for n in names:
                p = s["resources"][n]["policy"]
                count = sum(w["resource"]==n and w["state"] in {"waiting","awaiting_approval"} for w in s["waiters"].values())
                if count >= p["queue_cap"]:
                    return Result("refused",reason=f"queue_full:{p['queue_cap']}")
            approval = any(s["resources"][n]["policy"]["needs_ceo_card"] for n in names)
            seq = max((w["enqueue_seq"] for w in s["waiters"].values()),default=0)+1
            for n in names:
                if fail_at==n:
                    raise OSError("injected transaction abort")
                s["waiters"][ids[n]] = dict(request_id=ids[n],resource=n,group_id=group,owner_session=actor.session,
                    task_id=task_id,priority=actor.priority,enqueue_seq=seq,enqueued_at=now,
                    state="awaiting_approval" if approval else "waiting",idempotency_key=key,purpose=purpose,
                    payload={"names":names},approval=None,fence=None,claim_until=None)
            self._schedule(s,now,tx,arrival=group)
            return self._result(s,group)
        from lib.db_pg import HubConnectError
        try:
            return self._mutate(op)
        except (HubUnavailable, HubConnectError):
            known = {**self.policies, **policies}
            advisory = all(n in known and known[n]["on_hub_down"]=="uncoordinated" and not known[n]["paid"] for n in names)
            return Result("uncoordinated" if advisory else "refused",reason=None if advisory else "hub_down")

    def status(self,request_id,actor):
        def op(s,now,tx):
            rows=self._rows(s,request_id)
            if not rows or any(w["owner_session"]!=actor.session for w in rows):
                return Result("refused",request_id,reason="not_owner")
            result=self._result(s,request_id)
            if result.state=="granted" and result.expires_at<=now:
                return Result("expired",request_id)
            return result
        return self.store.run(op,readonly=True)

    def _authorized(self,s,now,group,actor,tokens):
        rows=self._rows(s,group)
        if isinstance(tokens,int) and len(rows)==1:
            tokens={rows[0]["resource"]:tokens}
        if not isinstance(tokens,dict) or not rows:
            return []
        for w in rows:
            h=s["resources"][w["resource"]]["holders"].get(w["request_id"])
            if not h or h["owner"]!=actor.session or h["token"]!=tokens.get(w["resource"]) or now>=h["expires_at"]:
                return []
        return rows

    def valid(self,request_id,actor,tokens):
        return self.store.run(lambda s,n,t:bool(self._authorized(s,n,request_id,actor,tokens)),readonly=True)

    def renew(self,request_id,actor,tokens):
        def op(s,now,tx):
            self._reap(s,now)
            rows=self._authorized(s,now,request_id,actor,tokens)
            for w in rows:
                r=s["resources"][w["resource"]]
                h=r["holders"][w["request_id"]]
                h["expires_at"]=min(now+2*r["policy"]["heartbeat_s"],h["started_at"]+r["policy"]["max_hold_s"])
                w["claim_until"]=h["expires_at"]
            self._schedule(s,now,tx)
            return bool(rows)
        return self._mutate(op)

    def release(self,request_id,actor,tokens):
        def op(s,now,tx):
            rows=self._authorized(s,now,request_id,actor,tokens)
            for w in rows:
                del s["resources"][w["resource"]]["holders"][w["request_id"]]
                w["state"]="done"
                _event(s,w["resource"],"release",actor.session,now,request_id=w["request_id"],fence=w["fence"])
            self._reap(s,now)
            self._schedule(s,now,tx)
            return bool(rows)
        return self._mutate(op)

    def cancel(self,request_id,actor):
        def op(s,now,tx):
            rows=self._rows(s,request_id)
            if not rows or any(w["owner_session"]!=actor.session for w in rows):
                return False
            for w in rows:
                s["resources"][w["resource"]]["holders"].pop(w["request_id"],None)
                w["state"]="cancelled"
                _event(s,w["resource"],"cancel",actor.session,now,request_id=w["request_id"])
            self._schedule(s,now,tx)
            return True
        return self._mutate(op)

    def tick(self):
        def op(s,now,tx):
            self._reap(s,now)
            self._schedule(s,now,tx)
        self._mutate(op)

    def acknowledge(self,request_id,actor,*,failure=None):
        def op(s,now,tx):
            for w in self._rows(s,request_id):
                if w["owner_session"]!=actor.session:
                    raise LeaseError("not owner")
                if failure:
                    w["payload"]["retry_reason"]=failure
                elif w["state"]=="claimed":
                    w["state"]="acknowledged"
        self._mutate(op)

    def import_rows(self,source,rows,*,fail=False):
        """Import an already-frozen parsed snapshot. No legacy queue is touched."""
        name=f"import:{source}"
        def op(s,now,tx):
            if name not in s["resources"]:
                p=validate_policy(dict(kind="mutex",capacity=1,heartbeat_s=5,max_hold_s=30,
                    queue_cap=1000,paid=False,on_hub_down="fail_closed",needs_ceo_card=False))
                s["resources"][name]=dict(policy=p,holders={},cooling_until=0,quota_epoch=0)
            old={e["payload"]["ordinal"]:e["payload"]["row"] for e in s["events"] if e["kind"]=="import" and e["resource"]==name}
            if old and (len(rows)<len(old) or any(rows[i]!=row for i,row in old.items())):
                raise ValueError("frozen source changed")
            known={row["task_id"] for row in old.values()}
            seq=max((w["enqueue_seq"] for w in s["waiters"].values()),default=0)
            for i,row in enumerate(rows):
                if i in old:
                    continue
                _event(s,name,"import","migration",now,event_key=f"import:{source}:{i}",payload={"ordinal":i,"row":deepcopy(row),"source":source})
                if row["task_id"] in known:
                    continue
                known.add(row["task_id"])
                rid=str(uuid.uuid4())
                seq+=1
                s["waiters"][rid]=dict(request_id=rid,resource=name,group_id=rid,owner_session=row["task_id"],task_id=row["task_id"],
                    priority=10,enqueue_seq=seq,enqueued_at=now,state="waiting",idempotency_key=f"import:{source}:{row['task_id']}",
                    purpose="frozen import",payload={"source":source},approval=None,fence=None,claim_until=None)
            if fail:
                raise OSError("injected import rollback")
        self.store.run(op)

    def administer(self,action,actor,*,name=None,request_id=None,reason=None,card=None,until=None,event_key=None):
        if actor.role not in {"CEO","CTO"} or not reason:
            return False
        if action in {"override","approve"} and actor.role!="CEO":
            return False
        def op(s,now,tx):
            if event_key and any(e["event_key"]==event_key for e in s["events"]):
                return True
            if action=="approve":
                rows=self._rows(s,request_id)
                if not rows or not self.approval_verifier(card,actor,deepcopy(rows),now):
                    return False
                for w in rows:
                    if w["state"]!="awaiting_approval":
                        return False
                for w in rows:
                    w.update(state="waiting",approval={"card":card},enqueued_at=now)
                    _event(s,w["resource"],"approval",actor.session,now,payload={"card":card})
            elif action in {"cool","reset"}:
                r=s["resources"][name]
                if action=="cool":
                    r["cooling_until"]=max(r["cooling_until"],until)
                else:
                    r["quota_epoch"]+=1
                    r["cooling_until"]=now
                _event(s,name,action,actor.session,now,event_key=event_key or str(uuid.uuid4()),payload={"reason":reason})
            elif action in {"release_override","override"}:
                rows=self._rows(s,request_id) if request_id else [w for w in s["waiters"].values() if w["resource"]==name and w["state"] in {"claimed","acknowledged"}]
                for w in rows:
                    s["resources"][w["resource"]]["holders"].pop(w["request_id"],None)
                    w["state"]="done"
                    _event(s,w["resource"],action,actor.session,now,payload={"role":actor.role,"reason":reason,"stop":True,"owner":w["owner_session"]},deliver_after=now)
                if action=="override":
                    group=str(uuid.uuid4())
                    rid=str(uuid.uuid4())
                    p=s["resources"][name]["policy"]
                    s["waiters"][rid]=dict(request_id=rid,resource=name,group_id=group,owner_session=actor.session,task_id=None,
                        priority=-1,enqueue_seq=max((w["enqueue_seq"] for w in s["waiters"].values()),default=0)+1,
                        enqueued_at=now,state="awaiting_approval" if p["needs_ceo_card"] else "waiting",
                        idempotency_key=group,purpose=reason,payload={},approval=None,fence=None,claim_until=None)
                    self._schedule(s,now,tx,arrival=group)
                    return self._result(s,group)
            else:
                raise ValueError("unknown administrative operation")
            self._schedule(s,now,tx)
            return True
        return self._mutate(op)

    def deliver_outbox(self):
        if self.deliver is None:
            return
        events=self.store.run(lambda s,n,t:[deepcopy(e) for e in s["events"] if e["deliver_after"] is not None and e["deliver_after"]<=n and e["delivered_at"] is None],readonly=True)
        for event in events:
            owner=event["payload"].get("owner",event["actor"])
            success=False
            try:
                success=not owner or self.deliver(owner,event) is not False
            except Exception:
                pass  # retain the durable event for retry, never release its claim
            def mark(s,now,tx):
                for e in s["events"]:
                    if e["event_key"]==event["event_key"]:
                        e["attempts"]+=1
                        if success:
                            e["delivered_at"]=now
            self.store.run(mark)

    def wait(self,request_id,actor,wait_s=0):
        deadline=time.monotonic()+max(0,wait_s)
        while True:
            self.tick()
            result=self.status(request_id,actor)
            if result.state not in {"waiting","awaiting_approval"} or time.monotonic()>=deadline:
                return result
            # Durable outbox is the external wake mechanism. Bounded rechecks
            # also cover missed notifications and cooling/TTL deadlines.
            time.sleep(min(0.2,max(0,deadline-time.monotonic())))


def mailbox_delivery(owner,event):
    if not owner:
        return True
    role, separator, session=owner.partition("-")
    if not separator or not session:
        return False
    from lib import mailbox
    from tools import mail_wake
    mailbox.send(role,session,f"Lease {event['kind']}: {event['resource']}; request={event['request_id']}; event={event['event_key']}. Check current fencing authority before acting.",
                 "lease","hub",subject="Lease ready",kind="message",prio="urgent")
    return bool(mail_wake.wake(owner,label="LEASE").get("woke"))


_local=threading.local()


class Handle:
    def __init__(self,service,actor,result,heartbeat_s):
        self.service,self.actor=service,actor
        self.request_id,self.token,self.tokens=result.request_id,result.token,result.tokens
        self.expires_at=result.expires_at
        self.lost=threading.Event()
        self.stop=threading.Event()
        self.heartbeat_s=heartbeat_s
        self.thread=threading.Thread(target=self._heartbeat,name="lease-heartbeat",daemon=True)

    def _heartbeat(self):
        while not self.stop.wait(self.heartbeat_s):
            try:
                if not self.service.renew(self.request_id,self.actor,self.tokens):
                    self.lost.set()
                    return
            except Exception:
                self.lost.set()
                return

    def assert_valid(self):
        if self.lost.is_set() or not self.service.valid(self.request_id,self.actor,self.tokens):
            self.lost.set()
            raise LeaseLost("lease authority lost; stop guarded work")


def default_service():
    # Explicit opt-in keeps offline tests and accidental imports off the hub.
    from lib.db_pg import connect
    url=os.environ.get("LEASE_DB_URL")
    owner=os.environ.get("LEASE_OWNER_SESSION")
    if not url or not owner:
        raise LeaseError("trusted launcher must provide LEASE_DB_URL and LEASE_OWNER_SESSION")
    return Service(PostgresStore(lambda:connect(url)),registry=Registry(),deliver=mailbox_delivery),Actor(owner)


@contextmanager
def lease_many(names,purpose="lease",wait_s=0,*,service=None,actor=None):
    if getattr(_local,"active",False):
        raise LeaseError("nested acquisition requires one declared group")
    if not purpose:
        raise ValueError("purpose required")
    if service is None:
        service,actor=default_service()
    if actor is None:
        raise ValueError("actor required")
    _local.active=True
    handle=None
    result=None
    body_failed=False
    try:
        result=service.acquire(names,actor,purpose=purpose)
        if result.state in {"waiting","awaiting_approval"}:
            result=service.wait(result.request_id,actor,wait_s)
        if result.state!="granted":
            if result.request_id:
                service.cancel(result.request_id,actor)
            raise LeaseError(result.reason or result.state)
        service.acknowledge(result.request_id,actor)
        interval=service.store.run(lambda s,n,t:min(s["resources"][name]["policy"]["heartbeat_s"] for name in result.tokens),readonly=True)
        handle=Handle(service,actor,result,interval)
        handle.thread.start()
        try:
            yield handle
        except BaseException:
            body_failed=True
            raise
    finally:
        try:
            if handle:
                handle.stop.set()
                handle.thread.join()
            if result and result.state=="granted":
                try:
                    service.release(result.request_id,actor,result.tokens)
                except Exception:
                    if not body_failed:
                        raise
            if handle and handle.lost.is_set() and not body_failed:
                raise LeaseLost("heartbeat failed during guarded work")
        finally:
            _local.active=False


def lease(name,purpose="lease",wait_s=0,**kwargs):
    return lease_many([name],purpose=purpose,wait_s=wait_s,**kwargs)


def _call(method,*args,service=None,actor=None,**kwargs):
    if service is None:
        service,actor=default_service()
    if actor is None:
        raise ValueError("actor required")
    return getattr(service,method)(*args,actor=actor,**kwargs)


def acquire(name,**kwargs):
    return _call("acquire",name,**kwargs)


def renew(request_id,token,**kwargs):
    return _call("renew",request_id,tokens=token,**kwargs)


def release(request_id,token,**kwargs):
    return _call("release",request_id,tokens=token,**kwargs)


def status(request_id,**kwargs):
    return _call("status",request_id,**kwargs)


def wait(request_id,wait_s=0,**kwargs):
    return _call("wait",request_id,wait_s=wait_s,**kwargs)
