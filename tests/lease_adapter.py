"""Contract adapter: injected clock/liveness/mail only, no reference-model calls."""
from copy import deepcopy

from lib.lease import Actor, HubUnavailable, MemoryStore, Service


class FakeStore(MemoryStore):
    online=True

    def run(self,*args,**kwargs):
        if not self.online:
            raise HubUnavailable("injected hub outage")
        return super().run(*args,**kwargs)


class LeaseAdapter:
    def __init__(self):
        self.clock=[0]
        self.live={}
        self.notifications=[]
        self.store=FakeStore(lambda:self.clock[0])
        self.service=Service(self.store,liveness=lambda owner:self.live.get(owner),
            deliver=self._deliver,approval_verifier=lambda card,actor,rows,now:bool(card) and actor.role=="CEO")
        self.order=[]

    def _deliver(self,owner,event):
        if event["payload"].get("wake"):
            item=(event["event_key"],event["resource"],owner)
            if item not in self.notifications:
                self.notifications.append(item)
        return True

    def _snapshot(self):
        return self.store.run(lambda s,n,t:deepcopy(s),readonly=True)

    def _group(self,names,owner):
        names=sorted(set(names))
        s=self._snapshot()
        for w in reversed(list(s["waiters"].values())):
            if w["owner_session"]==owner and w["state"] not in {"done","cancelled"}:
                rows=self.service._rows(s,w["group_id"])
                if sorted(r["resource"] for r in rows)==names:
                    return w["group_id"]

    def configure(self,name,**kwargs):
        self.service.configure(name,**kwargs)

    def acquire(self,name,owner,**kwargs):
        return self.acquire_many([name],owner,**kwargs)

    def acquire_many(self,names,owner,*,priority=10,client_time=None,fail_at=None):
        self.order=sorted(set(names))
        if self.store.online:
            group=self._group(names,owner)
            if group:
                self.service.tick()
                return self.service.status(group,Actor(owner))
        return self.service.acquire(names,Actor(owner,priority=priority),fail_at=fail_at)

    def renew(self,name,owner,token=None,client_time=None):
        if not self.store.online:
            return False
        group=self._group([name],owner)
        if not group:
            return False
        if token is None:
            token=self.service.status(group,Actor(owner)).token
        return self.service.renew(group,Actor(owner),token)

    def valid(self,name,owner,token):
        group=self._group([name],owner)
        return bool(group and self.service.valid(group,Actor(owner),token))

    def release(self,name,owner,token,*,role=None,reason=None):
        group=self._group([name],owner)
        if group and self.service.release(group,Actor(owner),token):
            return True
        if role in {"CEO","CTO"} and reason:
            s=self._snapshot()
            w=next((w for w in s["waiters"].values() if w["resource"]==name and w["fence"]==token),None)
            if w:
                return self.service.administer("release_override",Actor(owner,role),request_id=w["group_id"],reason=reason)
        return False

    def release_many(self,names,owner):
        group=self._group(names,owner)
        if group:
            result=self.service.status(group,Actor(owner))
            return self.service.release(group,Actor(owner),result.tokens)

    def release_project(self,project,owner):
        for name,r in self._snapshot()["resources"].items():
            if r["policy"].get("project")==project:
                self.release_many([name],owner)

    def advance(self,seconds):
        self.clock[0]+=seconds

    def liveness(self,owner,*,pid,tmux,session):
        self.live[owner]=pid or tmux or session

    def hub(self,online):
        self.store.online=online

    def tick(self):
        self.service.tick()

    def restart(self):
        self.service=Service(self.store,liveness=lambda owner:self.live.get(owner),deliver=self._deliver,
            approval_verifier=lambda card,actor,rows,now:bool(card) and actor.role=="CEO")
        return self

    def dispatch(self,name,owner,*,failure=None):
        self.service.acknowledge(self._group([name],owner),Actor(owner),failure=failure)

    def pending_dispatch(self,name):
        return [w["owner_session"] for w in self._snapshot()["waiters"].values() if w["resource"]==name and w["state"]=="claimed"]

    def cool(self,name,*,until,source):
        self.service.administer("cool",Actor("provider","CTO"),name=name,until=until,reason=source)

    def reset_quota(self,name):
        self.service.administer("reset",Actor("provider","CTO"),name=name,reason="verified reset")

    def override(self,name,owner,*,role,reason):
        return self.service.administer("override",Actor(owner,role),name=name,reason=reason)

    def approve(self,name,owner,*,role,card):
        return self.service.administer("approve",Actor("authority",role),request_id=self._group([name],owner),card=card,reason="verified card")

    def cancel(self,owner):
        groups={w["group_id"] for w in self._snapshot()["waiters"].values() if w["owner_session"]==owner}
        for group in groups:
            self.service.cancel(group,Actor(owner))

    def gc_candidates(self,owners):
        protected={w["owner_session"] for w in self._snapshot()["waiters"].values() if w["state"] not in {"done","cancelled"}}
        return [o for o in owners if o not in protected]

    def import_rows(self,source,rows,*,fail=False):
        self.service.import_rows(source,rows,fail=fail)

    def imported(self):
        return {(e["payload"]["source"],e["payload"]["ordinal"]):e["payload"]["row"] for e in self._snapshot()["events"] if e["kind"]=="import"}

    def holders(self,name):
        return [h["owner"] for h in self._snapshot()["resources"][name]["holders"].values()]

    def waiters(self,name):
        return [w["owner_session"] for w in sorted(self._snapshot()["waiters"].values(),key=self.service._order) if w["resource"]==name and w["state"] in {"waiting","awaiting_approval"}]

    def wakes(self):
        return [(name,owner) for key,name,owner in self.notifications]

    def letters(self):
        return [(e["payload"].get("owner",e["actor"]),"max_hold" if e["kind"]=="max_hold" else "stop") for e in self._snapshot()["events"] if e["payload"].get("stop")]

    def events(self):
        return [(e["kind"],e["payload"].get("role"),e["payload"].get("reason")) for e in self._snapshot()["events"]]

    def acquisition_order(self):
        return self.order
