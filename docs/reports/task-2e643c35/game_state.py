#!/usr/bin/env python3
"""game_state.py - state engine for the ข้าวหอม survival game HUD.

usage: python3 tools/game_state.py ep04 [--prev ep03] [--commit] [--root DIR]

Replays epNN/events.json on top of the previous episode's end state
(canon/state/<prev>-end.json, default prev = the episode before NN) and writes
epNN/game/{end,hud,loadout,summary}.json.  --commit also copies end.json to
canon/state/epNN-end.json.  On a bad input it prints a Thai+English message to
stderr, exits 1 and writes nothing.  Python 3 stdlib only; no network.

How the brief left room, and what this file does (each is also in the REPORT):
- Only `pass` advances hunger.  `use` with hours drains the item, not hunger.
- Clock: an event's `clock` places it on the story clock; a clock earlier than
  the previous event's start is the next day.  After a `pass` the clock moves
  on by `hours`.  An event placed inside the previous pass is moved up to the
  end of that pass (with a warning) - the clock never runs backwards.
- "In use": hand/body items have an `equipped` flag (default true).  On a
  `pass`, a hand/body item with drain_per_hour drains only while equipped
  (a torch in the bag does not burn); bag/home items drain whenever, unless
  items.json sets "passive": false (a torch drains only through `use`).
  `use` with hours drains the item whether equipped or not.
- One use/eat takes drain_per_use of the item; with drain_per_use 0 a count
  item loses 1, and eating a pct/days item takes the whole item.
- Hunger 0 "for a whole pass" = hunger is already 0 when the pass starts.
- Popups: loot "+n name"; eat/use of a count item "-n name" (the last one
  "name หมด!" instead); drain "name 35% → 15%"; break op "name หัก!"; drained
  to 0 "name พัง!"; hunger 0 "หิวมาก!"; day rollover that spoils food
  "name เสียแล้ว".  Popups carry the applied (clamped) change.
- v3 additions: water (0-100), mind (0-100), money (>= 0), xp/level (0-100)
  with skill badges, trust per NPC (0-100), container slots (3/5/8/12),
  and verbs money, water, mind, xp, trust, world, container.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_POPUP = 18
EPS = 1e-9
OPS = ("use", "eat", "loot", "break", "lose", "damage", "heal", "equip", "unequip", "pass",
       "money", "water", "mind", "xp", "trust", "world", "container")
NEEDS_ITEM = ("use", "eat", "loot", "break", "lose", "equip", "unequip")
SLOTS = ("bag", "hand", "body", "home")
UNITS = ("pct", "count", "days")
WORN = ("hand", "body")
CONTAINER_SLOTS = {
    "none": 3,
    "ไม่มีกระเป๋า": 3,
    "pocket": 3,
    "ถุง": 5,
    "bag": 5,
    "plastic_bag": 5,
    "เป้": 8,
    "backpack": 8,
    "เรือ": 12,
    "แพ": 12,
    "boat": 12,
    "raft": 12,
}


class GameError(Exception):
    """A bad input or a broken continuity.  The message is 'ไทย / English'."""


def fail(th, en):
    raise GameError("%s / %s" % (th, en))


# ---------------------------------------------------------------- small helpers

def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def num(x):
    """Number for a JSON file: 2 decimals, an int when it is whole."""
    x = round(float(x), 2)
    return int(x) if x == int(x) else x


def txt(x):
    """Number for popup text: 1 decimal, no trailing .0."""
    x = round(float(x), 1)
    return str(int(x)) if x == int(x) else str(x)


def clamp(x):
    return max(0.0, min(100.0, x))


def clean(s):
    return re.sub(r"\s+", " ", s.replace("«", "").replace("»", "")).strip()


def fit(cands):
    """First candidate that is at most MAX_POPUP chars; else the last, cut."""
    cands = [clean(c) for c in cands]
    for c in cands:
        if len(c) <= MAX_POPUP:
            return c
    return cands[-1][:MAX_POPUP]


def parse_clock(s, where):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s) if isinstance(s, str) else None
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        fail("เวลา (clock) ผิดรูปแบบ %r ที่ %s ต้องเป็น HH:MM" % (s, where),
             "bad clock %r at %s, expected HH:MM" % (s, where))
    return int(m.group(1)) * 60 + int(m.group(2))


def fmt_clock(total_min):
    m = int(total_min) % 1440
    return "%02d:%02d" % (m // 60, m % 60)


def join_en(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def strip_article(s):
    return re.sub(r"^(a|an|the)\s+", "", s, flags=re.I)


def read_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("ไม่พบไฟล์ %s: %s" % (what, path), "missing %s: %s" % (what, path))
    except (ValueError, OSError) as e:
        fail("อ่านไฟล์ %s ไม่ได้: %s" % (what, path), "cannot read %s (%s): %s" % (what, e, path))


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


# ---------------------------------------------------------------- loading

def load_items(path):
    raw = read_json(path, "canon/items.json")
    if not isinstance(raw, dict) or not raw:
        fail("items.json ต้องเป็น object ของไอเทม", "items.json must be a non-empty object of items")
    items = {}
    for iid, d in raw.items():
        if not isinstance(d, dict):
            fail("ไอเทม %r ต้องเป็น object" % iid, "item %r must be an object" % iid)
        slot, unit = d.get("slot", "bag"), d.get("unit", "pct")
        if slot not in SLOTS:
            fail("ไอเทม %r: slot %r ไม่ถูกต้อง" % (iid, slot), "item %r: bad slot %r, use %s" % (iid, slot, "|".join(SLOTS)))
        if unit not in UNITS:
            fail("ไอเทม %r: unit %r ไม่ถูกต้อง" % (iid, unit), "item %r: bad unit %r, use %s" % (iid, unit, "|".join(UNITS)))
        it = {"name_th": str(d.get("name_th", iid)), "name_en": str(d.get("name_en") or iid.replace("_", " ")),
              "slot": slot, "unit": unit, "icon": d.get("icon", ""),
              "passive": d.get("passive", True) is not False}
        for k in ("drain_per_hour", "drain_per_use", "hunger_gain", "hp_gain"):
            v = d.get(k, 0)
            if not is_num(v):
                fail("ไอเทม %r: %s ต้องเป็นตัวเลข" % (iid, k), "item %r: %s must be a number" % (iid, k))
            it[k] = float(v)
        for k in ("drain_per_hour", "drain_per_use"):
            if it[k] < 0:
                fail("ไอเทม %r: %s ติดลบไม่ได้" % (iid, k), "item %r: %s cannot be negative" % (iid, k))
        exp = d.get("expires_after_days")
        if exp is not None and (not is_num(exp) or exp <= 0):
            fail("ไอเทม %r: expires_after_days ต้องเป็น null หรือมากกว่า 0" % iid,
                 "item %r: expires_after_days must be null or > 0 (got %r)" % (iid, exp))
        it["expires_after_days"] = exp
        items[iid] = it
    return items


def load_state(path, items):
    st = read_json(path, "start state")
    if not isinstance(st, dict):
        fail("ไฟล์สถานะเริ่มต้นต้องเป็น object: %s" % path, "start state must be an object: %s" % path)
    for k in ("day", "clock", "hp", "hunger", "hunger_drain_per_hour", "inv"):
        if k not in st:
            fail("ไฟล์สถานะเริ่มต้นขาดคีย์ %r: %s" % (k, path), "start state lacks key %r: %s" % (k, path))
    parse_clock(st["clock"], "start state")
    for k in ("day", "hp", "hunger", "hunger_drain_per_hour"):
        if not is_num(st[k]):
            fail("สถานะเริ่มต้น: %s ต้องเป็นตัวเลข" % k, "start state: %s must be a number" % k)
    if not isinstance(st["inv"], list):
        fail("สถานะเริ่มต้น: inv ต้องเป็น list", "start state: inv must be a list")
    inv = []
    for e in st["inv"]:
        if not isinstance(e, dict) or e.get("id") not in items:
            fail("สถานะเริ่มต้น: ไม่รู้จักไอเทม %r" % (e.get("id") if isinstance(e, dict) else e,),
                 "start state: unknown item id %r" % (e.get("id") if isinstance(e, dict) else e,))
        if not is_num(e.get("value")) or e["value"] <= 0 or not is_num(e.get("got_day")):
            fail("สถานะเริ่มต้น: %r ต้องมี value > 0 และ got_day" % e["id"],
                 "start state: %r needs value > 0 and got_day" % e["id"])
        entry = {"id": e["id"], "value": float(e["value"]), "got_day": int(e["got_day"])}
        if e.get("equipped") is False:
            entry["equipped"] = False
        inv.append(entry)
    out = {"day": int(st["day"]), "clock": st["clock"], "hp": clamp(float(st["hp"])),
           "hunger": clamp(float(st["hunger"])), "hunger_drain_per_hour": float(st["hunger_drain_per_hour"]),
           "inv": inv}
    out["water"] = clamp(float(st["water"])) if "water" in st and is_num(st["water"]) else 100.0
    out["mind"] = clamp(float(st["mind"])) if "mind" in st and is_num(st["mind"]) else 100.0
    out["money"] = max(0.0, float(st["money"])) if "money" in st and is_num(st["money"]) else 0.0
    out["xp"] = clamp(float(st["xp"])) if "xp" in st and is_num(st["xp"]) else 0.0
    out["level"] = clamp(float(st["level"])) if "level" in st and is_num(st["level"]) else 1.0
    out["trust"] = {str(k): clamp(float(v)) for k, v in st.get("trust", {}).items() if is_num(v)} if isinstance(st.get("trust"), dict) else {}
    c_slots = st.get("container_slots", st.get("slots", 8))
    out["container_slots"] = int(clamp(float(c_slots))) if is_num(c_slots) else 8
    out["badges"] = list(st.get("badges", [])) if isinstance(st.get("badges"), list) else []
    return out


def check_events(events, items):
    """Validate every event up front, so nothing is written for a bad episode."""
    if not isinstance(events, list):
        fail("events.json ต้องเป็น list", "events.json must be a list")
    out, last_t = [], None
    for k, ev in enumerate(events, 1):
        if not isinstance(ev, dict):
            fail("เหตุการณ์ #%d ต้องเป็น object" % k, "event #%d must be an object" % k)
        ev = dict(ev)
        op, t = ev.get("op"), ev.get("t")
        if op not in OPS:
            fail("เหตุการณ์ #%d: op %r ไม่รู้จัก" % (k, op), "event #%d: unknown op %r, use %s" % (k, op, "|".join(OPS)))
        if not is_num(t) or t < 0:
            fail("เหตุการณ์ #%d: t ต้องเป็นวินาที >= 0" % k, "event #%d: t must be seconds >= 0 (got %r)" % (k, t))
        if last_t is not None and t < last_t:
            fail("เหตุการณ์ไม่เรียงตามเวลา: #%d t=%s มาหลัง t=%s" % (k, t, last_t),
                 "events out of time order: #%d t=%s comes after t=%s" % (k, t, last_t))
        last_t = t
        if "clock" in ev:
            parse_clock(ev["clock"], "event #%d" % k)
        if op in NEEDS_ITEM:
            iid = ev.get("item")
            if iid not in items:
                fail("ไม่รู้จักไอเทม %r (เหตุการณ์ #%d, t=%s)" % (iid, k, t),
                     "unknown item id %r (event #%d, t=%s)" % (iid, k, t))
        n = ev.get("n", 1)
        if not is_num(n) or n != int(n) or n < 1:
            fail("เหตุการณ์ #%d: n ต้องเป็นจำนวนเต็ม >= 1" % k, "event #%d: n must be an integer >= 1 (got %r)" % (k, n))
        ev["n"] = int(n)
        for key in ("hours", "hp", "value", "delta", "water", "mind", "money", "xp", "trust", "slots", "level"):
            if key in ev and not is_num(ev[key]):
                fail("เหตุการณ์ #%d: %s ต้องเป็นตัวเลข" % (k, key), "event #%d: %s must be a number" % (k, key))
        if ev.get("hours", 0) < 0:
            fail("เหตุการณ์ #%d: hours ติดลบไม่ได้" % k, "event #%d: hours cannot be negative" % k)
        if op == "pass" and "hours" not in ev:
            fail("เหตุการณ์ #%d: pass ต้องมี hours" % k, "event #%d: pass needs hours" % k)
        if op in ("damage", "heal") and "hp" not in ev:
            fail("เหตุการณ์ #%d: %s ต้องมี hp" % (k, op), "event #%d: %s needs hp" % (k, op))
        if op == "trust" and not any(x in ev for x in ("npc", "name", "target")):
            fail("เหตุการณ์ #%d: trust ต้องระบุ npc" % k, "event #%d: trust needs npc" % k)
        if op == "world" and not any(x in ev for x in ("text_th", "event", "msg", "text", "name")):
            fail("เหตุการณ์ #%d: world ต้องระบุข้อความเหตุการณ์" % k, "event #%d: world needs event text" % k)
        out.append(ev)
    return out


def check_stills(stills):
    if not isinstance(stills, dict) or any(not is_num(v) or v < 0 for v in stills.values()):
        fail("stills.json ต้องเป็น {id: วินาที}", "stills.json must map each still id to seconds >= 0")
    return stills


# ---------------------------------------------------------------- the engine

class Engine:
    def __init__(self, items, state):
        self.items = items
        self.hp, self.hunger = state["hp"], state["hunger"]
        self.drain = state["hunger_drain_per_hour"]
        self.inv = [dict(e) for e in state["inv"]]
        self.water = clamp(float(state.get("water", 100.0)))
        self.mind = clamp(float(state.get("mind", 100.0)))
        self.money = max(0.0, float(state.get("money", 0.0)))
        self.xp = clamp(float(state.get("xp", 0.0)))
        self.level = clamp(float(state.get("level", 1.0)))
        self.trust = {k: clamp(float(v)) for k, v in state.get("trust", {}).items()}
        self.container_slots = int(state.get("container_slots", 8))
        self.badges = list(state.get("badges", []))
        self.world_events = []
        self.cur = state["day"] * 1440 + parse_clock(state["clock"], "start state")
        self.last_start = self.cur
        self.popups, self.bars, self.inv_rows, self.timeline = [], [], [], []
        self.gained, self.lost, self.warnings = {}, {}, []
        self.t, self.k, self.touched = 0, 0, {}
        self.record(0)

    # -- views
    def day(self):
        return int(self.cur // 1440)

    def spoiled(self, e, day=None):
        exp = self.items[e["id"]]["expires_after_days"]
        return exp is not None and (self.day() if day is None else day) - e["got_day"] >= exp

    def alive(self, e):
        return any(x is e for x in self.inv)

    def entries(self, iid):
        return [e for e in self.inv if e["id"] == iid]

    def active(self, e):
        return self.items[e["id"]]["slot"] not in WORN or e.get("equipped", True)

    def snap_inv(self):
        out = []
        for e in self.inv:
            it = self.items[e["id"]]
            out.append({"id": e["id"], "name_th": it["name_th"], "icon": it["icon"],
                        "value": num(e["value"]), "unit": it["unit"], "spoiled": self.spoiled(e)})
        return out

    def snap_load(self):
        worn = [e for e in self.inv if self.items[e["id"]]["slot"] in WORN and e.get("equipped", True)]
        ids = []
        for slot in ("body", "hand"):
            for e in worn:
                if self.items[e["id"]]["slot"] == slot and e["id"] not in ids:
                    ids.append(e["id"])
        return ids

    def record(self, t):
        b = {"hp": num(self.hp), "hunger": num(self.hunger)}
        if hasattr(self, "water") and self.water is not None:
            b["water"] = num(self.water)
        if hasattr(self, "mind") and self.mind is not None:
            b["mind"] = num(self.mind)
        if hasattr(self, "money") and self.money is not None:
            b["money"] = num(self.money)
        if hasattr(self, "xp") and self.xp is not None:
            b["xp"] = num(self.xp)
        if hasattr(self, "level") and self.level is not None:
            b["level"] = num(self.level)
        self._push(self.bars, t, b)
        self._push(self.inv_rows, t, {"slots": self.snap_inv()})
        self.timeline.append((t, self.snap_load()))

    @staticmethod
    def _push(rows, t, data):
        if rows and rows[-1]["t"] == t:  # same instant: the later state wins
            rows.pop()
        if rows and {k: v for k, v in rows[-1].items() if k != "t"} == data:
            return  # nothing changed since the last row
        row = {"t": t}
        row.update(data)
        rows.append(row)

    def pop(self, kind, *texts, **kw):
        self.popups.append({"t": self.t, "kind": kind, "text_th": fit(texts), "item": kw.get("item")})

    def warn(self, th, en):
        self.warnings.append("t=%s: %s / %s" % (self.t, th, en))

    @staticmethod
    def tally(d, key, amount):
        d[key] = d.get(key, 0) + amount

    # -- time
    def move_clock(self, ev):
        if "clock" not in ev:
            return
        mins = parse_clock(ev["clock"], "event #%d" % self.k)
        cand = (self.last_start // 1440) * 1440 + mins
        if cand < self.last_start:
            cand += 1440  # clock went round midnight
        if cand < self.cur:
            self.warn("เหตุการณ์ #%d (%s) อยู่ในช่วง pass ก่อนหน้า ขยับไปท้าย pass" % (self.k, ev["clock"]),
                      "event #%d (%s) falls inside the previous pass; moved to its end" % (self.k, ev["clock"]))
            cand = self.cur
        self.last_start = cand
        self.set_time(cand)

    def set_time(self, new):
        old_day, self.cur = self.day(), new
        self.day_check(old_day)

    def day_check(self, old_day):
        new_day = self.day()
        if new_day <= old_day:
            return
        for e in self.inv:
            if self.spoiled(e, new_day) and not self.spoiled(e, old_day):
                name = self.items[e["id"]]["name_th"]
                self.pop("warn", "%sเสียแล้ว" % name, "ของเสียแล้ว", item=e["id"])

    # -- bars
    def _hp(self, delta):
        old = self.hp
        self.hp = clamp(self.hp + delta)
        applied = self.hp - old
        if abs(applied) > EPS:
            self.pop("gain" if applied > 0 else "lose", "%s%s พลังชีวิต" % ("+" if applied > 0 else "-", txt(abs(applied))))
        if self.hp <= EPS < old:
            self.warn("พลังชีวิตเหลือ 0", "HP reached 0")

    def _hunger(self, delta):
        old = self.hunger
        self.hunger = clamp(self.hunger + delta)
        applied = self.hunger - old
        if abs(applied) > EPS:
            self.pop("gain" if applied > 0 else "lose", "%s%s อิ่ม" % ("+" if applied > 0 else "-", txt(abs(applied))))

    def _water(self, delta):
        old = self.water
        self.water = clamp(self.water + delta)
        applied = self.water - old
        if abs(applied) > EPS:
            self.pop("gain" if applied > 0 else "lose",
                     "%s%s น้ำในร่างกาย" % ("+" if applied > 0 else "-", txt(abs(applied))),
                     "%s%s น้ำ" % ("+" if applied > 0 else "-", txt(abs(applied))))
        if self.water <= EPS < old:
            self.warn("น้ำในร่างกายเหลือ 0", "body water reached 0")

    def _mind(self, delta):
        old = self.mind
        self.mind = clamp(self.mind + delta)
        applied = self.mind - old
        if abs(applied) > EPS:
            self.pop("gain" if applied > 0 else "lose",
                     "%s%s สติ" % ("+" if applied > 0 else "-", txt(abs(applied))))
        if self.mind <= EPS < old:
            self.warn("สติเหลือ 0", "mind reached 0")

    def _money(self, delta):
        old = self.money
        self.money = max(0.0, self.money + delta)
        applied = self.money - old
        if abs(applied) > EPS:
            self.pop("gain" if applied > 0 else "lose",
                     "%s%s บาท" % ("+" if applied > 0 else "-", txt(abs(applied))))
        if self.money <= EPS < old:
            self.warn("เงินหมด", "money reached 0")

    def _xp(self, delta, badge=None, level=None):
        old = self.xp
        self.xp = clamp(self.xp + delta)
        applied = self.xp - old
        if abs(applied) > EPS:
            self.pop("gain" if applied > 0 else "lose",
                     "%s%s XP" % ("+" if applied > 0 else "-", txt(abs(applied))))
        if level is not None:
            self.level = clamp(float(level))
        if badge:
            b_str = str(badge)
            if b_str not in self.badges:
                self.badges.append(b_str)
            self.pop("gain", b_str, "ทักษะใหม่")

    def _trust(self, npc, delta):
        old = float(self.trust.get(npc, 50.0))
        new_val = clamp(old + delta)
        self.trust[npc] = num(new_val)
        applied = new_val - old
        if abs(applied) > EPS:
            self.pop("gain" if applied > 0 else "lose",
                     "%s%s ไว้ใจ (%s)" % ("+" if applied > 0 else "-", txt(abs(applied)), npc),
                     "%s%s ไว้ใจ" % ("+" if applied > 0 else "-", txt(abs(applied))),
                     item=npc)

    # -- inventory
    def dec(self, e, amount, how):
        """Take `amount` off an entry's value; remove it at 0."""
        if amount <= 0:
            return
        it, old = self.items[e["id"]], e["value"]
        self.touched.setdefault(id(e), (e, old))
        e["value"] = max(0.0, old - amount)
        if it["unit"] == "count":
            self.tally(self.lost, (e["id"], how), old - e["value"])
        if e["value"] <= EPS:
            self.remove(e, how, popup=it["unit"] != "count")

    def remove(self, e, how, popup=True):
        self.inv = [x for x in self.inv if x is not e]
        it = self.items[e["id"]]
        if it["unit"] != "count":
            self.tally(self.lost, (e["id"], how), 1)
        if not popup:
            return
        name = it["name_th"]
        if how == "break":
            self.pop("break", "%sหัก!" % name, "หัก!", item=e["id"])
        elif how == "lose":
            self.pop("lose", "%sหาย!" % name, "หาย!", item=e["id"])
        elif how == "eat":
            self.pop("empty", "%sหมด!" % name, "หมด!", item=e["id"])
        else:
            self.pop("break", "%sพัง!" % name, "พัง!", item=e["id"])

    def flush(self, how):
        """Popups for what this event did to values (one per item, not per step)."""
        units = {}
        for e, old in self.touched.values():
            it, new, gone = self.items[e["id"]], e["value"], not self.alive(e)
            if it["unit"] == "count":
                u = units.setdefault(e["id"], [0.0, False])
                u[0] += old - new
                u[1] = u[1] or gone
            elif not gone and abs(new - old) > EPS:
                sfx = "%" if it["unit"] == "pct" else " วัน"
                name, a, b = it["name_th"], txt(old) + sfx, txt(new) + sfx
                self.pop("drain", "%s %s → %s" % (name, a, b), "%s %s → %s" % (name, txt(old), b),
                         "%s → %s" % (name, b), "%s → %s" % (a, b), item=e["id"])
        for iid, (n, emptied) in units.items():
            if n <= EPS:
                continue
            name = self.items[iid]["name_th"]
            if emptied and how != "lose":
                self.pop("empty", "%sหมด!" % name, "หมด!", item=iid)
            else:
                self.pop("lose", "-%s %s" % (txt(n), name), "-%s" % txt(n), item=iid)

    # -- errors that name the event
    def where(self):
        return "เหตุการณ์ #%d, t=%s" % (self.k, self.t), "event #%d, t=%s" % (self.k, self.t)

    def not_held(self, iid, verb_th, verb_en):
        th, en = self.where()
        name = self.items[iid]["name_th"]
        fail("ไม่มี %s (%s) ในกระเป๋า จึง%sไม่ได้ (%s)" % (name, iid, verb_th, th),
             "cannot %s %r: not in the inventory (%s)" % (verb_en, iid, en))

    # -- ops
    def apply(self, ev, k):
        self.k, self.t, self.touched = k, ev["t"], {}
        self.move_clock(ev)
        getattr(self, "op_" + ev["op"])(ev)
        if "hp" in ev and ev["op"] not in ("damage", "heal"):
            self._hp(ev["hp"])
        self.flush(ev["op"])
        self.record(self.t)

    def op_pass(self, ev):
        hours = ev["hours"]
        if self.hunger <= EPS:
            self.pop("warn", "หิวมาก!")
            self.warn("หิวมาก: hunger เป็น 0 ตลอด pass", "starving: hunger was 0 for the whole pass")
        self.hunger = clamp(self.hunger - self.drain * hours)
        for e in list(self.inv):
            rate = self.items[e["id"]]["drain_per_hour"]
            if rate > 0 and self.active(e) and self.items[e["id"]].get("passive", True):
                self.dec(e, rate * hours, "pass")
        old_day = self.day()
        self.cur += hours * 60
        self.day_check(old_day)

    def _use(self, ev, how):
        iid, it = ev["item"], self.items[ev["item"]]
        verb = ("กิน", "eat") if how == "eat" else ("ใช้", "use")
        first = None
        for _ in range(ev["n"]):
            cands = [e for e in self.entries(iid) if not (how == "eat" and self.spoiled(e))]
            if not cands:
                if self.entries(iid):
                    th, en = self.where()
                    fail("กิน %s (%s) ที่เสียแล้วไม่ได้ (%s)" % (it["name_th"], iid, th),
                         "cannot eat spoiled %r (%s)" % (iid, en))
                self.not_held(iid, *verb)  # held fewer than n
            e = cands[0]
            first = first or e
            if it["drain_per_use"] > 0:
                per = it["drain_per_use"]
            elif it["unit"] == "count":
                per = 1.0
            else:
                per = float("inf") if how == "eat" else 0.0  # eating takes the whole item
            self.dec(e, per, how)
            self._hunger(it["hunger_gain"])
            self._hp(it["hp_gain"])
        hours = ev.get("hours", 0)
        if hours > 0 and first is not None and self.alive(first):
            self.dec(first, it["drain_per_hour"] * hours, how)

    def op_use(self, ev):
        self._use(ev, "use")

    def op_eat(self, ev):
        self._use(ev, "eat")

    def op_loot(self, ev):
        iid, n, it = ev["item"], ev["n"], self.items[ev["item"]]
        day = self.day()
        if it["unit"] == "pct":
            for _ in range(n):
                self.inv.append({"id": iid, "value": float(ev.get("value", 100)), "got_day": day})
        else:  # count and days: one stack of n (a count stack merges within the same day)
            same = [e for e in self.entries(iid) if e["got_day"] == day]
            if "value" not in ev and it["unit"] == "count" and same:
                same[0]["value"] += n
            else:
                self.inv.append({"id": iid, "value": float(ev.get("value", n)), "got_day": day})
        self.tally(self.gained, iid, n)
        self.pop("gain", "+%d %s" % (n, it["name_th"]), "+%d" % n, item=iid)

    def op_break(self, ev):
        iid = ev["item"]
        ents = self.entries(iid)
        if not ents:
            self.not_held(iid, "ทำ", "break")
        e = ents[0]
        if self.items[iid]["unit"] == "count":
            self.tally(self.lost, (iid, "break"), e["value"])
        self.remove(e, "break")

    def op_lose(self, ev):
        iid, n, it = ev["item"], ev["n"], self.items[ev["item"]]
        ents = self.entries(iid)
        have = sum(e["value"] for e in ents) if it["unit"] == "count" else len(ents)
        if have + EPS < n:
            self.not_held(iid, "ทำหาย", "lose")
        if it["unit"] == "count":
            left = float(n)
            for e in ents:
                take = min(left, e["value"])
                self.dec(e, take, "lose")
                left -= take
                if left <= EPS:
                    break
        else:
            for e in ents[:n]:
                self.remove(e, "lose")

    def op_damage(self, ev):
        self._hp(-abs(ev["hp"]))

    def op_heal(self, ev):
        self._hp(abs(ev["hp"]))

    def _equip(self, ev, flag):
        iid = ev["item"]
        ents = self.entries(iid)
        if not ents:
            self.not_held(iid, "สวม" if flag else "ถอด", "equip" if flag else "unequip")
        if self.items[iid]["slot"] not in WORN:
            self.warn("%s ไม่ใช่ของ hand/body จึงไม่มีผล" % iid, "%r is not a hand/body item: equip has no effect" % iid)
            return
        for e in ents:
            if flag:
                e.pop("equipped", None)
            else:
                e["equipped"] = False

    def op_equip(self, ev):
        self._equip(ev, True)

    def op_unequip(self, ev):
        self._equip(ev, False)

    # -- new v3 ops
    def op_water(self, ev):
        d = ev.get("delta")
        if d is None:
            d = ev.get("water", ev.get("value", ev.get("amount", 0)))
        self._water(float(d))

    def op_mind(self, ev):
        d = ev.get("delta")
        if d is None:
            d = ev.get("mind", ev.get("value", ev.get("amount", 0)))
        self._mind(float(d))

    def op_money(self, ev):
        d = ev.get("delta")
        if d is None:
            d = ev.get("money", ev.get("amount", ev.get("value", 0)))
        self._money(float(d))

    def op_xp(self, ev):
        d = ev.get("delta")
        if d is None:
            d = ev.get("xp", ev.get("value", ev.get("amount", 0)))
        badge = ev.get("badge", ev.get("skill"))
        level = ev.get("level")
        self._xp(float(d), badge=badge, level=level)

    def op_trust(self, ev):
        npc = str(ev.get("npc", ev.get("name", ev.get("target"))))
        if "delta" in ev:
            self._trust(npc, float(ev["delta"]))
        elif "trust" in ev:
            self._trust(npc, float(ev["trust"]))
        elif "amount" in ev:
            self._trust(npc, float(ev["amount"]))
        elif "value" in ev:
            old = float(self.trust.get(npc, 0.0))
            new_val = clamp(float(ev["value"]))
            self.trust[npc] = num(new_val)
            applied = new_val - old
            if abs(applied) > EPS:
                self.pop("gain" if applied > 0 else "lose",
                         "%s%s ไว้ใจ (%s)" % ("+" if applied > 0 else "-", txt(abs(applied)), npc),
                         "%s%s ไว้ใจ" % ("+" if applied > 0 else "-", txt(abs(applied))),
                         item=npc)
        else:
            fail("เหตุการณ์ #%d: trust ต้องมี delta หรือ value" % self.k,
                 "event #%d: trust needs delta or value" % self.k)

    def op_world(self, ev):
        text = str(ev.get("text_th", ev.get("event", ev.get("msg", ev.get("text", ev.get("name", "เหตุการณ์โลก"))))))
        rule = ev.get("rule", ev.get("evidence", ev.get("id")))
        entry = {"t": self.t, "event": text}
        if rule:
            entry["rule"] = str(rule)
        self.world_events.append(entry)
        self.pop("warn", fit([text, "เหตุการณ์โลก"]), item=rule)

    def op_container(self, ev):
        slots = ev.get("slots")
        cname = ev.get("container", ev.get("name", ev.get("type", "")))
        if slots is None and cname in CONTAINER_SLOTS:
            slots = CONTAINER_SLOTS[cname]
        if slots is None:
            slots = 8
        slots = int(clamp(float(slots)))
        self.container_slots = slots
        self.pop("gain", "กระเป๋า %d ช่อง" % slots, "%d ช่อง" % slots)

    # -- results
    def en_line(self, ids):
        en = lambda i: self.items[i]["name_en"]
        body = [en(i) for i in ids if self.items[i]["slot"] == "body"]
        hand = [en(i) for i in ids if self.items[i]["slot"] == "hand"]
        parts = []
        if body:
            parts.append("wears " + join_en(body))
        if hand:
            parts.append("holds " + join_en(hand))
        for i, it in self.items.items():
            if it["slot"] in WORN and i not in ids:
                parts.append("no " + strip_article(en(i)))
        return ", ".join(parts) or "carries nothing"

    def loadout_at(self, s):
        ts = [t for t, _ in self.timeline]
        i = bisect.bisect_right(ts, s) - 1
        return self.timeline[max(i, 0)][1]

    def end_state(self, ep_num):
        total = int(round(self.cur))
        inv = []
        for e in self.inv:
            d = {"id": e["id"], "value": num(e["value"]), "got_day": e["got_day"]}
            if e.get("equipped") is False:
                d["equipped"] = False
            inv.append(d)
        end = {"ep": ep_num, "day": total // 1440, "clock": fmt_clock(total), "hp": num(self.hp),
               "hunger": num(self.hunger), "hunger_drain_per_hour": num(self.drain), "inv": inv}
        end["water"] = num(self.water)
        end["mind"] = num(self.mind)
        end["money"] = num(self.money)
        end["xp"] = num(self.xp)
        end["level"] = num(self.level)
        end["trust"] = {k: num(v) for k, v in self.trust.items()}
        end["container_slots"] = int(self.container_slots)
        if self.badges:
            end["badges"] = list(self.badges)
        return end


def replay(items, state, events, stills, ep):
    events = check_events(events, items)
    stills = check_stills(stills)
    start = {"day": state["day"], "clock": state["clock"], "hp": num(state["hp"]), "hunger": num(state["hunger"])}
    if "water" in state:
        start["water"] = num(state["water"])
    if "mind" in state:
        start["mind"] = num(state["mind"])
    if "money" in state:
        start["money"] = num(state["money"])
    eng = Engine(items, state)
    for k, ev in enumerate(events, 1):
        eng.apply(ev, k)
    m = re.fullmatch(r"ep(\d+)", ep)
    end = eng.end_state(int(m.group(1)) if m else 0)
    loadout = {sid: eng.loadout_at(s) for sid, s in stills.items()}
    loadout["_en"] = {sid: eng.en_line(loadout[sid]) for sid in stills}
    name = lambda iid: items[iid]["name_th"]
    summary = {
        "ep": ep,
        "gained": [{"id": i, "name_th": name(i), "n": num(n)} for i, n in eng.gained.items()],
        "lost": [{"id": i, "name_th": name(i), "n": num(n), "how": how} for (i, how), n in eng.lost.items()],
        "remaining": [dict(s, got_day=e["got_day"]) for s, e in zip(eng.snap_inv(), eng.inv)],
        "start": start,
        "end": {"day": end["day"], "clock": end["clock"], "hp": end["hp"], "hunger": end["hunger"]},
        "warnings": eng.warnings,
    }
    hud = {"bars": eng.bars, "inv": [{"t": r["t"], "slots": r["slots"]} for r in eng.inv_rows], "popups": eng.popups}
    return {"end": end, "hud": hud, "loadout": loadout, "summary": summary, "warnings": eng.warnings}


# ---------------------------------------------------------------- episode runner + CLI

def default_prev(ep):
    m = re.fullmatch(r"ep(\d+)", ep)
    if not m or int(m.group(1)) < 1:
        fail("ชื่อตอนต้องเป็น epNN (NN >= 1): %r" % ep, "episode must look like ep04 (NN >= 1): %r" % ep)
    return "ep%0*d" % (len(m.group(1)), int(m.group(1)) - 1)


def run_episode(root, ep, prev=None, commit=False):
    root = Path(root)
    if not re.fullmatch(r"ep\d+", ep):
        fail("ชื่อตอนต้องเป็น epNN: %r" % ep, "episode must look like ep04: %r" % ep)
    prev = prev or default_prev(ep)
    items = load_items(root / "canon" / "items.json")
    state_path = root / "canon" / "state" / ("%s-end.json" % prev)
    if not state_path.exists():
        fail("ไม่พบสถานะเริ่มต้น %s (ใช้ --prev หรือสร้างไฟล์นี้)" % state_path,
             "no start state %s (pass --prev, or create that file)" % state_path)
    state = load_state(state_path, items)
    events = read_json(root / ep / "events.json", "%s/events.json" % ep)
    stills_path = root / ep / "stills.json"
    stills = read_json(stills_path, "%s/stills.json" % ep) if stills_path.exists() else {}
    res = replay(items, state, events, stills, ep)
    if not stills_path.exists():
        res["warnings"].append("%s/stills.json ไม่มี: loadout ว่าง / missing: loadout is empty" % ep)
    gdir = root / ep / "game"
    for name in ("end", "hud", "loadout", "summary"):
        write_json(gdir / ("%s.json" % name), res[name])
    res["committed"] = None
    if commit:
        res["committed"] = root / "canon" / "state" / ("%s-end.json" % ep)
        write_json(res["committed"], res["end"])
    res["prev"], res["dir"] = prev, gdir
    return res


def table(res, ep):
    s = res["summary"]
    a, b = s["start"], s["end"]
    kinds = {}
    for p in res["hud"]["popups"]:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    rows = [("", "start (%s)" % res["prev"], "end (%s)" % ep),
            ("day / clock", "%s %s" % (a["day"], a["clock"]), "%s %s" % (b["day"], b["clock"])),
            ("hp", a["hp"], b["hp"]), ("hunger", a["hunger"], b["hunger"])]
    lines = ["%-12s %-16s %s" % tuple(str(c) for c in r) for r in rows]
    lines.append("gained    : " + (", ".join("+%s %s" % (g["n"], g["name_th"]) for g in s["gained"]) or "-"))
    lines.append("lost      : " + (", ".join("-%s %s (%s)" % (g["n"], g["name_th"], g["how"]) for g in s["lost"]) or "-"))
    lines.append("remaining : " + (", ".join("%s %s%s%s" % (r["name_th"], r["value"], {"pct": "%", "days": "d", "count": ""}[r["unit"]],
                                                         " SPOILED" if r["spoiled"] else "") for r in s["remaining"]) or "-"))
    lines.append("popups    : %d (%s)   stills: %d" % (len(res["hud"]["popups"]),
                 ", ".join("%s %d" % kv for kv in sorted(kinds.items())) or "none", len(res["loadout"]) - 1))
    for w in res["warnings"]:
        lines.append("warning   : " + w)
    lines.append("wrote     : %s/{end,hud,loadout,summary}.json" % res["dir"])
    lines.append("committed : %s" % (res["committed"] or "no (pass --commit to write canon/state)"))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Replay one episode's events on the previous end state.")
    ap.add_argument("ep", help="episode folder name, e.g. ep04")
    ap.add_argument("--prev", help="previous episode (default: the one before ep)")
    ap.add_argument("--commit", action="store_true", help="also copy end.json to canon/state/epNN-end.json")
    ap.add_argument("--root", default=str(ROOT), help="project root (default: the folder above tools/)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    try:
        res = run_episode(args.root, args.ep, args.prev, args.commit)
    except GameError as e:
        print("ผิดพลาด / ERROR: %s" % e, file=sys.stderr)
        return 1
    print(table(res, args.ep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
