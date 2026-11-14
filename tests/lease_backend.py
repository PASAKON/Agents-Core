"""Scratch repository and public contract adapter for lib.lease.

The production Service owns every scheduling/lifecycle transition. This fake
implements only transaction storage and the atomic SQL grant primitive. It does
not import or subclass the reference model and cannot open a hub connection.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import threading

from lib.lease import (Service, State, Identity, Result, Registry, validate_policy,
                       event, room, resource_row, LeaseError)


class FakeRegistry:
    def __init__(self):
        self.rows = {}

    def resolve(self, name):
        return name, deepcopy(self.rows[name])


class MemoryStore:
    def __init__(self):
        self.state = State(datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.serial = 0
        self.online = True
        self.lock = threading.RLock()
        self.fail_at = None

    @contextmanager
    def transaction(self):
        if not self.online:
            raise ConnectionError("fake hub down")
        with self.lock:
            unit = MemoryUnit(self, deepcopy(self.state))
            yield unit
            self.state = unit.state


class MemoryUnit:
    def __init__(self, store, state):
        self.store, self.state = store, state

    def grant(self, request_id, wake):
        s = self.state
        w = s.waiters[request_id]
        name = w["resource"]
        if self.store.fail_at == name:
            raise OSError("injected transaction abort")
        head = min((x for x in s.waiters.values() if x["resource"] == name and x["state"] == "waiting"),
                   key=lambda x: (x["priority"], x["enqueued_at"], x["enqueue_seq"]))
        if head["request_id"] != request_id or not room(s, name):
            raise LeaseError("grant_conflict")
        self.store.serial += 1
        r = s.resources[name]
        expires = s.now + timedelta(seconds=min(2*r["heartbeat_s"], r["max_hold_s"]))
        h = dict(owner=w["owner_session"], token=self.store.serial,
                 started_at=s.now.isoformat(), expires_at=expires.isoformat())
        r["holders"][request_id] = h
        w.update(state="claimed", fence=h["token"], claim_until=expires)
        event(s, name, "grant", w["owner_session"], request=request_id, token=h["token"],
              wake=wake, key=f"grant:{h['token']}", payload={"wake": True})


class LeaseBackend:
    def __init__(self):
        self.store = MemoryStore()
        self.registry = FakeRegistry()
        self.live = {}
        self.notifications = []
        self._order = []
        self.service = Service(self.store, self.registry, observer=lambda o, _: self.live.get(o),
                               deliver=self._deliver)

    def _deliver(self, e):
        if e["event_key"] not in {x["event_key"] for x in self.notifications}:
            self.notifications.append(deepcopy(e))
        return True

    def configure(self, name, *, kind="mutex", capacity=1, heartbeat_s=5,
                  max_hold_s=30, window_s=20, queue_cap=100, paid=False,
                  on_hub_down="fail_closed", needs_ceo_card=False, project=None):
        p = validate_policy(dict(kind=kind, capacity=capacity, heartbeat_s=heartbeat_s,
             max_hold_s=max_hold_s, window_s=window_s, queue_cap=queue_cap, paid=paid,
             on_hub_down=on_hub_down, needs_ceo_card=needs_ceo_card, project=project))
        self.registry.rows[name] = p
        def operation(tx):
            old = tx.state.resources.get(name)
            tx.state.resources[name] = resource_row(name, p)
            if old:
                for key in ("holders", "cooling_until", "quota_epoch"):
                    tx.state.resources[name][key] = old[key]
        self.service.run(operation)

    def hub(self, online):
        self.store.online = online

    def advance(self, seconds):
        assert seconds >= 0
        self.store.state.now += timedelta(seconds=seconds)

    def liveness(self, owner, *, pid, tmux, session):
        self.live[owner] = pid or tmux or session

    def _rows(self, name=None, owner=None, states=None):
        return sorted((w for w in self.store.state.waiters.values()
                       if (name is None or w["resource"] == name)
                       and (owner is None or w["owner_session"] == owner)
                       and (states is None or w["state"] in states)),
                      key=lambda w: (w["priority"], w["enqueued_at"], w["enqueue_seq"]))

    def _row(self, name, owner):
        rows = self._rows(name, owner, {"waiting", "awaiting_approval", "claimed", "acknowledged"})
        return rows[0] if rows else None

    def acquire(self, name, owner, **kwargs):
        return self.acquire_many([name], owner, **kwargs)

    def acquire_many(self, names, owner, *, priority=10, client_time=None, fail_at=None):
        names = sorted(set(names))
        self._order = names
        rows = [self._row(n, owner) for n in names]
        key = rows[0]["idempotency_key"] if all(rows) else None
        self.store.fail_at = fail_at
        try:
            return self.service.acquire(names, Identity(owner, priority), purpose="scenario", idempotency_key=key)
        finally:
            self.store.fail_at = None

    def tick(self):
        if self.store.online:
            self.service.tick()

    def renew(self, name, owner, token=None, client_time=None):
        w = self._row(name, owner)
        return bool(self.store.online and w and self.service.renew(name, w["request_id"],
                    w["fence"] if token is None else token, Identity(owner)))

    def valid(self, name, owner, token):
        w = self._row(name, owner)
        return bool(self.store.online and w and self.service.valid(name, w["request_id"], token, Identity(owner)))

    def release(self, name, owner, token, *, role=None, reason=None):
        if not self.store.online:
            return False
        w = self._row(name, owner)
        if w and self.service.release({name: dict(request_id=w["request_id"], token=token)}, Identity(owner)):
            return True
        target = next((x for x in self._rows(name) if x["fence"] == token), None)
        if not target:
            return False
        return self.service.administer("release", name, Identity(owner, admin=role), reason=reason,
                                       request_id=target["request_id"], token=token)

    def release_many(self, names, owner):
        grants = {n: dict(request_id=w["request_id"], token=w["fence"])
                  for n in sorted(set(names)) if (w := self._row(n, owner))}
        return self.service.release(grants, Identity(owner))

    def release_project(self, project, owner):
        return self.release_many([n for n, p in self.registry.rows.items() if p.get("project") == project], owner)

    def cool(self, name, *, until, source):
        return self.service.administer("cool", name, Identity("provider", admin="CTO"), reason=source,
                    until=datetime(2026, 1, 1, tzinfo=timezone.utc)+timedelta(seconds=until))

    def reset_quota(self, name):
        return self.service.administer("reset", name, Identity("provider", admin="CTO"), reason="verified reset")

    def override(self, name, owner, *, role, reason):
        return self.service.administer("override", name, Identity(owner, admin=role), reason=reason) or Result("refused")

    def approve(self, name, owner, *, role, card):
        w = self._row(name, owner)
        return bool(w and self.service.administer("approve", name, Identity("ceo", admin=role),
                    reason="verified card", request_id=w["request_id"], card=card))

    def cancel(self, owner):
        for w in self._rows(owner=owner, states={"waiting", "awaiting_approval"}):
            self.service.cancel(w["request_id"], Identity(owner))

    def gc_candidates(self, owners):
        protected = {w["owner_session"] for w in self._rows(states={"waiting", "awaiting_approval", "claimed", "acknowledged"})}
        return [o for o in owners if o not in protected]

    def dispatch(self, name, owner, *, failure=None):
        w = self._row(name, owner)
        return self.service.acknowledge(w["request_id"], w["fence"], Identity(owner), failure=failure)

    def pending_dispatch(self, name):
        return [w["owner_session"] for w in self._rows(name, states={"claimed"})]

    def restart(self):
        # New service, same durable store. No scheduler/reaper runs on construction.
        self.service = Service(self.store, self.registry, observer=lambda o, _: self.live.get(o), deliver=self._deliver)
        return self

    def import_rows(self, source, rows, *, fail=False):
        name = f"import:{source}"
        if name not in self.registry.rows:
            self.configure(name)
        self.service.import_snapshot(source, rows, fail=fail)

    def imported(self):
        return {(e["payload"]["source"], e["payload"]["ordinal"]): deepcopy(e["payload"]["row"])
                for e in self.store.state.events.values() if e["kind"] == "import"}

    def holders(self, name):
        return [h["owner"] for h in self.store.state.resources[name]["holders"].values()]

    def waiters(self, name):
        return [w["owner_session"] for w in self._rows(name, states={"waiting", "awaiting_approval"})]

    def wakes(self):
        return [(e["resource"], e["actor"]) for e in self.notifications if e["kind"] == "grant"]

    def letters(self):
        return [(e["actor"], e["kind"]) for e in self.notifications if e["kind"] in {"stop", "max_hold"}]

    def events(self):
        return [(e["kind"], e["payload"].get("role"), e["payload"].get("reason"))
                for e in self.store.state.events.values()]

    def acquisition_order(self):
        return self._order
