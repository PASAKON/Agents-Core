"""Executable specification only: serialized transitions, never a runtime lock.

Time is hub seconds. `tick` is one due reaper/scheduler pass. Liveness is an
injected authoritative observation; an unknown/partitioned host is not dead.
The Phase C adapter must expose these operations without using this model.
"""
from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    state: str
    token: int | None = None
    reason: str | None = None


class LeaseModel:
    def __init__(self):
        self.now = 0
        self.online = True
        self.config = {}
        self.grants = {}
        self.queue = []
        self.history = {}
        self.cooling = {}
        self.live = {}
        self.serial = 0
        self.sequence = 0
        self._wakes = []
        self._letters = []
        self._events = []
        self._imports = {}
        self._order = []

    def configure(self, name, *, kind="mutex", capacity=1, heartbeat_s=5,
                  max_hold_s=30, window_s=20, queue_cap=100, paid=False,
                  on_hub_down="fail_closed", needs_ceo_card=False, project=None):
        if paid and on_hub_down != "fail_closed":
            raise ValueError("paid resource must fail closed")
        if kind not in {"mutex", "pool", "rate"} or capacity < 1:
            raise ValueError("invalid resource")
        if kind == "mutex" and capacity != 1:
            raise ValueError("mutex capacity is one")
        self.config[name] = dict(kind=kind, capacity=capacity,
                                 heartbeat_s=heartbeat_s, max_hold_s=max_hold_s,
                                 window_s=window_s, queue_cap=queue_cap, paid=paid,
                                 on_hub_down=on_hub_down,
                                 needs_ceo_card=needs_ceo_card, project=project)
        self.grants.setdefault(name, {})
        self.history.setdefault(name, [])
        self.cooling.setdefault(name, 0)

    def hub(self, online):
        self.online = online

    def advance(self, seconds):
        assert seconds >= 0
        self.now += seconds

    def liveness(self, owner, *, pid, tmux, session):
        self.live[owner] = pid or tmux or session

    def _alive(self, owner):
        return self.live.get(owner, True)

    def _room(self, name):
        c = self.config[name]
        if c["kind"] == "rate":
            used = sum(t > self.now - c["window_s"] for t in self.history[name])
            return self.now >= self.cooling[name] and used < c["capacity"]
        return len(self.grants[name]) < c["capacity"]

    def acquire(self, name, owner, **kwargs):
        return self.acquire_many([name], owner, **kwargs)

    def acquire_many(self, names, owner, *, priority=10, client_time=None,
                     fail_at=None):
        names = tuple(sorted(set(names)))
        self._order = list(names)
        if not self.online:
            safe = all(self.config[n]["on_hub_down"] == "uncoordinated"
                       and not self.config[n]["paid"] for n in names)
            return Result("uncoordinated" if safe else "refused",
                          reason=None if safe else "hub_down")
        self.tick()
        if all(owner in self.grants[n] for n in names):
            return Result("granted", self.grants[names[0]][owner]["token"])
        existing = next((r for r in self.queue
                         if r["names"] == names and r["owner"] == owner), None)
        if existing:
            return Result("waiting" if existing["approved"] else "awaiting_approval")
        for n in names:
            c = self.config[n]
            if len(self.waiters(n)) >= c["queue_cap"]:
                return Result("refused", reason=f"queue_full:{c['queue_cap']}")
        if fail_at in names:
            raise OSError("injected transaction abort before commit")
        self.sequence += 1
        request = dict(names=names, owner=owner, priority=priority,
                       sequence=self.sequence,
                       approved=not any(self.config[n]["needs_ceo_card"] for n in names))
        # Every arrival goes through the same scheduler; new arrivals cannot barge.
        self.queue.append(request)
        self._schedule(arrival=request)
        if all(owner in self.grants[n] for n in names):
            return Result("granted", self.grants[names[0]][owner]["token"])
        return Result("waiting" if request["approved"] else "awaiting_approval")

    def _schedule(self, arrival=None):
        blocked = set()
        for r in sorted(list(self.queue), key=lambda r: (r["priority"], r["sequence"])):
            owner, names = r["owner"], r["names"]
            if not self._alive(owner):
                self.queue.remove(r)
                continue
            if not r["approved"]:
                continue  # approval-pending requests are not eligible FIFO members
            if blocked.intersection(names) or not all(self._room(n) for n in names):
                blocked.update(names)
                continue
            self.serial += 1
            for n in names:
                c = self.config[n]
                self.grants[n][owner] = dict(token=self.serial, start=self.now,
                    expires=self.now + min(2 * c["heartbeat_s"], c["max_hold_s"]),
                    ack=r is arrival, request=deepcopy(r))
                if c["kind"] == "rate":
                    self.history[n].append(self.now)
                if r is not arrival:
                    self._wakes.append((n, owner))
            self.queue.remove(r)

    def tick(self):
        if not self.online:
            return
        for n, holders in self.grants.items():
            for owner, g in list(holders.items()):
                capped = self.now >= g["start"] + self.config[n]["max_hold_s"]
                if capped or self.now >= g["expires"] or not self._alive(owner):
                    del holders[owner]
                    if capped:
                        self._letters.append((owner, "max_hold"))
                    # Dispatch claims are durable until ack; an expired claim retries.
                    if not g["ack"] and self._alive(owner):
                        self._events.append(("unacked_expired", n, owner))
                        if g["request"] not in self.queue:
                            self.queue.append(deepcopy(g["request"]))
        self._schedule()

    def renew(self, name, owner, token=None, client_time=None):
        if not self.online:
            return False
        self.tick()
        g = self.grants[name].get(owner)
        if not g or (token is not None and g["token"] != token):
            return False
        c = self.config[name]
        g["expires"] = min(self.now + 2 * c["heartbeat_s"], g["start"] + c["max_hold_s"])
        return True

    def valid(self, name, owner, token):
        g = self.grants[name].get(owner)
        return bool(self.online and g and g["token"] == token
                    and self.now < g["expires"]
                    and self.now < g["start"] + self.config[name]["max_hold_s"])

    def release(self, name, owner, token, *, role=None, reason=None):
        if not self.online:
            return False
        target = owner
        if not self.valid(name, owner, token):
            if role not in {"CEO", "CTO"} or not reason:
                return False
            target = next((o for o, g in self.grants[name].items()
                           if g["token"] == token), None)
            if target is None:
                return False
            self._events.append(("release_override", role, reason))
            self._letters.append((target, "stop"))
        del self.grants[name][target]
        self._schedule()
        return True

    def release_many(self, names, owner):
        for name in sorted(set(names)):
            self.grants[name].pop(owner, None)
        self._schedule()

    def release_project(self, project, owner):
        self.release_many([n for n, c in self.config.items()
                           if c["project"] == project], owner)

    def cool(self, name, *, until, source):
        self.cooling[name] = max(self.cooling[name], until)
        self._events.append(("cooling", source, until))

    def reset_quota(self, name):
        self.cooling[name] = self.now
        self.history[name] = []
        self._schedule()

    def override(self, name, owner, *, role, reason):
        if role != "CEO" or not reason or not self.online:
            return Result("refused", reason="not_authorized")
        for old in list(self.grants[name]):
            self._letters.append((old, "stop"))
        self.grants[name].clear()
        self._events.append(("override", role, reason))
        self.sequence += 1
        r = dict(names=(name,), owner=owner, priority=-1,
                 sequence=self.sequence, approved=not self.config[name]["needs_ceo_card"])
        self.queue.append(r)
        self._schedule(arrival=r)
        g = self.grants[name].get(owner)
        return Result("granted", g["token"]) if g else Result("awaiting_approval")

    def approve(self, name, owner, *, role, card):
        if role != "CEO" or not card:
            return False
        for r in self.queue:
            if r["owner"] == owner and r["names"] == (name,):
                r["approved"] = True
                self._events.append(("approval", card, owner))
                self._schedule()
                return True
        return False

    def cancel(self, owner):
        self.queue = [r for r in self.queue if r["owner"] != owner]

    def gc_candidates(self, owners):
        protected = {r["owner"] for r in self.queue}
        protected.update(o for hs in self.grants.values() for o in hs)
        return [o for o in owners if o not in protected]

    def dispatch(self, name, owner, *, failure=None):
        if failure is None:
            self.grants[name][owner]["ack"] = True
        else:
            self._events.append(("dispatch_retry", failure, owner))

    def pending_dispatch(self, name):
        return [o for o, g in self.grants[name].items() if not g["ack"]]

    def restart(self):
        return deepcopy(self)

    def import_rows(self, source, rows, *, fail=False):
        staged = deepcopy(self._imports)
        known = {row["task_id"] for (origin, _), row in self._imports.items()
                 if origin == source}
        for ordinal, row in enumerate(rows):
            key = (source, ordinal)
            if key in staged and staged[key] != row:
                raise ValueError("source changed after frozen snapshot")
            staged[key] = deepcopy(row)
        if fail:
            raise OSError("import transaction aborted")
        name = f"import:{source}"
        if name not in self.config:
            self.configure(name)
        for row in rows:
            # One logical dispatch per source/task; retain every raw line above.
            owner = row["task_id"]
            if owner not in known:
                self.sequence += 1
                self.queue.append(dict(names=(name,), owner=owner, priority=10,
                                       sequence=self.sequence, approved=True))
                known.add(owner)
        self._imports = staged

    def imported(self):
        return deepcopy(self._imports)

    def holders(self, name):
        return list(self.grants[name])

    def waiters(self, name):
        return [r["owner"] for r in sorted(self.queue,
                key=lambda r: (r["priority"], r["sequence"])) if name in r["names"]]

    def wakes(self):
        return list(self._wakes)

    def letters(self):
        return list(self._letters)

    def events(self):
        return list(self._events)

    def acquisition_order(self):
        return list(self._order)
