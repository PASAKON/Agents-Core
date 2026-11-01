"""Tests for tools/game_state.py.

run:  cd /opt/MoonieXHQ/Work/khaohom-survival && python3 -m unittest tools/test_game_state.py -v
Every test builds its own throw-away project root in a temp folder, so the real
canon/ and epNN/ folders are never read or written.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import game_state  # noqa: E402
from game_state import GameError  # noqa: E402

TOOL = Path(game_state.__file__).resolve()


def item(name_th, name_en, slot="bag", unit="pct", **kw):
    d = {"name_th": name_th, "name_en": name_en, "slot": slot, "unit": unit, "drain_per_hour": 0,
         "drain_per_use": 0, "expires_after_days": None, "hunger_gain": 0, "hp_gain": 0, "icon": ""}
    d.update(kw)
    return d


ITEMS = {
    "torch": item("ไฟฉาย", "a torch", "hand", drain_per_hour=10, icon="props/torch.png"),
    "stick": item("ไม้", "a wooden stick", "hand", icon="props/stick.png"),
    "boots": item("รองเท้าบู๊ต", "rubber boots", "body", icon="props/boots.png"),
    "gloves": item("ถุงมือยาง", "gloves", "body", icon="props/gloves.png"),
    "rice": item("ข้าวสาร", "rice", "bag", "count", drain_per_use=1, hunger_gain=20, icon="props/rice.png"),
    "cooked_rice": item("ข้าวสวย", "cooked rice", "bag", "count", drain_per_use=1, hunger_gain=25,
                        expires_after_days=1, icon="props/cooked.png"),
    "phone": item("โทรศัพท์", "a phone", "bag", drain_per_hour=2, icon="props/phone.png"),
    "plaster": item("พลาสเตอร์", "a plaster", "bag", "count", drain_per_use=1, hp_gain=5, icon="props/plaster.png"),
}


def inv(*entries):
    return [{"id": i, "value": v, "got_day": d} for i, v, d in entries]


BASE_INV = inv(("torch", 35, 1), ("stick", 100, 1), ("boots", 100, 1), ("rice", 2, 2),
               ("phone", 90, 1), ("plaster", 2, 3))


def ev(t, op, clock="22:00", **kw):
    d = {"t": t, "clock": clock, "op": op}
    d.update(kw)
    return d


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def put(self, rel, obj):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def make(self, events, items=None, stills=None, inventory=None, ep="ep04", prev="ep03", **state):
        st = {"ep": 3, "day": 3, "clock": "22:00", "hp": 80, "hunger": 30, "hunger_drain_per_hour": 1.5,
              "inv": BASE_INV if inventory is None else inventory}
        st.update(state)
        self.put("canon/items.json", ITEMS if items is None else items)
        self.put("canon/state/%s-end.json" % prev, st)
        self.put("%s/events.json" % ep, events)
        if stills is not None:
            self.put("%s/stills.json" % ep, stills)

    def run_ep(self, events, ep="ep04", **kw):
        self.make(events, ep=ep, **kw)
        return game_state.run_episode(self.root, ep)

    @staticmethod
    def popups(res):
        return [(p["kind"], p["text_th"]) for p in res["hud"]["popups"]]

    def slots(self, row):
        return {s["id"]: s for s in row["slots"]}


class HappyPath(Base):
    EVENTS = [
        ev(0.5, "unequip", item="torch", note_th="ปิดไฟฉาย"),
        ev(2.0, "pass", hours=2),
        ev(4.2, "loot", "00:00", item="rice", n=1),
        ev(6.0, "eat", "00:10", item="rice"),
        ev(8.0, "use", "00:20", item="torch", hours=1),
        ev(9.0, "equip", "00:30", item="torch"),
        ev(10.0, "damage", "00:30", hp=-10),
        ev(11.0, "heal", "00:40", hp=5),
        ev(11.5, "use", "00:45", item="plaster"),
        ev(12.0, "break", "00:50", item="stick"),
        ev(13.0, "lose", "01:00", item="rice"),
    ]

    def setUp(self):
        super().setUp()
        self.res = self.run_ep(self.EVENTS, stills={"K1": 0.0, "K2": 12.5})

    def test_end_state(self):
        end = self.res["end"]
        self.assertEqual((end["ep"], end["day"], end["clock"]), (4, 4, "01:00"))
        self.assertEqual((end["hp"], end["hunger"], end["hunger_drain_per_hour"]), (80, 47, 1.5))
        got = {(e["id"], e["value"], e["got_day"]) for e in end["inv"]}
        self.assertEqual(got, {("torch", 25, 1), ("boots", 100, 1), ("rice", 1, 4), ("phone", 86, 1), ("plaster", 1, 3)})
        self.assertNotIn("equipped", json.dumps(end))  # the torch was re-equipped; no flag is written

    def test_popups(self):
        got = self.popups(self.res)
        for want in [("drain", "โทรศัพท์ 90% → 86%"), ("gain", "+1 ข้าวสาร"), ("gain", "+20 อิ่ม"),
                     ("drain", "ไฟฉาย 35% → 25%"), ("lose", "-10 พลังชีวิต"), ("gain", "+5 พลังชีวิต"),
                     ("gain", "+5 พลังชีวิต"), ("lose", "-1 พลาสเตอร์"), ("break", "ไม้หัก!")]:
            self.assertIn(want, got)
        self.assertEqual(got.count(("lose", "-1 ข้าวสาร")), 2)  # the eat and the lose
        for p in self.res["hud"]["popups"]:
            self.assertLessEqual(len(p["text_th"]), 18)
            self.assertNotIn("«", p["text_th"])
            self.assertNotIn("»", p["text_th"])
            self.assertIn(p["kind"], ("gain", "lose", "break", "empty", "drain", "warn"))
        ts = [p["t"] for p in self.res["hud"]["popups"]]
        self.assertEqual(ts, sorted(ts))

    def test_hud_rows_only_when_something_changes(self):
        h = self.res["hud"]
        self.assertEqual([(r["t"], r["hp"], r["hunger"]) for r in h["bars"]],
                         [(0, 80, 30), (2.0, 80, 27), (6.0, 80, 47), (10.0, 70, 47), (11.0, 75, 47), (11.5, 80, 47)])
        # unequip (0.5) and equip (9.0) change no slot, so they add no inv row
        self.assertEqual([r["t"] for r in h["inv"]], [0, 2.0, 4.2, 6.0, 8.0, 11.5, 12.0, 13.0])
        first = h["inv"][0]["slots"][0]
        self.assertEqual(set(first), {"id", "name_th", "icon", "value", "unit", "spoiled"})
        self.assertEqual((first["id"], first["name_th"], first["icon"], first["value"], first["unit"], first["spoiled"]),
                         ("torch", "ไฟฉาย", "props/torch.png", 35, "pct", False))
        self.assertNotIn("stick", self.slots(h["inv"][-1]))

    def test_summary(self):
        s = self.res["summary"]
        self.assertEqual([(g["id"], g["n"]) for g in s["gained"]], [("rice", 1)])
        self.assertEqual({(g["id"], g["n"], g["how"]) for g in s["lost"]},
                         {("rice", 1, "eat"), ("rice", 1, "lose"), ("stick", 1, "break"), ("plaster", 1, "use")})
        self.assertEqual({r["id"] for r in s["remaining"]}, {"torch", "boots", "rice", "phone", "plaster"})
        self.assertEqual((s["start"]["clock"], s["end"]["clock"], s["end"]["hp"]), ("22:00", "01:00", 80))

    def test_files_are_written(self):
        for name in ("end", "hud", "loadout", "summary"):
            data = json.loads((self.root / ("ep04/game/%s.json" % name)).read_text(encoding="utf-8"))
            self.assertEqual(data, json.loads(json.dumps(self.res[name], ensure_ascii=False)))


class Errors(Base):
    def test_eat_item_not_held(self):
        with self.assertRaises(GameError) as cm:
            self.run_ep([ev(1, "eat", item="rice")], inventory=inv(("stick", 100, 1)))
        msg = str(cm.exception)
        self.assertIn("ไม่มี", msg)
        self.assertIn("not in the inventory", msg)
        self.assertFalse((self.root / "ep04/game").exists())  # nothing is written for a bad episode

    def test_eat_more_than_held(self):
        with self.assertRaises(GameError):
            self.run_ep([ev(1, "eat", item="rice", n=3)], inventory=inv(("rice", 2, 1)))

    def test_use_item_not_held(self):
        with self.assertRaises(GameError):
            self.run_ep([ev(1, "use", item="torch", hours=1)], inventory=inv(("stick", 100, 1)))

    def test_unknown_id(self):
        for op in ("loot", "use", "eat", "equip"):
            with self.subTest(op=op), self.assertRaises(GameError) as cm:
                self.run_ep([ev(1, op, item="unicorn")])
            self.assertIn("ไม่รู้จักไอเทม", str(cm.exception))
            self.assertIn("unknown item id", str(cm.exception))

    def test_unknown_id_in_start_state(self):
        with self.assertRaises(GameError):
            self.run_ep([], inventory=inv(("unicorn", 1, 1)))

    def test_events_out_of_order(self):
        with self.assertRaises(GameError) as cm:
            self.run_ep([ev(5.0, "pass", hours=1), ev(3.0, "pass", hours=1)])
        self.assertIn("ไม่เรียงตามเวลา", str(cm.exception))
        self.assertIn("out of time order", str(cm.exception))

    def test_events_with_the_same_t_are_in_order(self):
        self.run_ep([ev(5.0, "pass", hours=1), ev(5.0, "damage", hp=-1)])

    def test_bad_input_shapes(self):
        for bad in ([ev(1, "dance")], [ev("x", "pass", hours=1)], [ev(1, "pass")], [ev(1, "damage")],
                    [ev(1, "pass", hours=-1)], [ev(1, "loot", item="rice", n=0)], [ev(1, "pass", "25:99", hours=1)]):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                self.run_ep(bad)

    def test_cli_exits_non_zero_with_thai_and_english(self):
        self.make([ev(1, "eat", item="rice")], inventory=inv(("stick", 100, 1)))
        p = subprocess.run([sys.executable, str(TOOL), "ep04", "--root", str(self.root)],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 1)
        self.assertIn("ผิดพลาด", p.stderr)
        self.assertIn("ERROR", p.stderr)
        self.assertFalse((self.root / "ep04/game").exists())

    def test_missing_start_state(self):
        self.make([])
        with self.assertRaises(GameError) as cm:
            game_state.run_episode(self.root, "ep04", prev="ep02")
        self.assertIn("ep02-end.json", str(cm.exception))


class Clamps(Base):
    def test_hp_clamps_at_100_and_0(self):
        res = self.run_ep([ev(1, "heal", hp=20), ev(2, "damage", hp=-150), ev(3, "damage", hp=5)], hp=95)
        self.assertEqual([r["hp"] for r in res["hud"]["bars"]], [95, 100, 0])
        self.assertEqual(res["end"]["hp"], 0)
        self.assertEqual(self.popups(res), [("gain", "+5 พลังชีวิต"), ("lose", "-100 พลังชีวิต")])  # applied, not asked
        self.assertTrue(any("HP reached 0" in w for w in res["warnings"]))

    def test_damage_sign_does_not_matter(self):
        a = self.run_ep([ev(1, "damage", hp=-10)])["end"]["hp"]
        b = self.run_ep([ev(1, "damage", hp=10)])["end"]["hp"]
        self.assertEqual((a, b), (70, 70))

    def test_hunger_clamps_at_100_and_0(self):
        res = self.run_ep([ev(1, "eat", item="rice"), ev(2, "pass", hours=100)], hunger=95)
        self.assertEqual([r["hunger"] for r in res["hud"]["bars"]], [95, 100, 0])
        self.assertIn(("gain", "+5 อิ่ม"), self.popups(res))


class Drain(Base):
    def test_torch_drains_to_zero_breaks_and_is_removed(self):
        res = self.run_ep([ev(1, "use", item="torch", hours=2)], stills={"K1": 0.0, "K2": 1.0},
                          inventory=inv(("torch", 15, 1), ("boots", 100, 1)))
        self.assertIn(("break", "ไฟฉายพัง!"), self.popups(res))
        self.assertNotIn("drain", [k for k, _ in self.popups(res)])  # a break, not a 15% -> 0% drain
        self.assertEqual([e["id"] for e in res["end"]["inv"]], ["boots"])
        self.assertNotIn("torch", self.slots(res["hud"]["inv"][-1]))
        self.assertEqual(res["loadout"]["K1"], ["boots", "torch"])
        self.assertEqual(res["loadout"]["K2"], ["boots"])
        self.assertEqual([(g["id"], g["how"]) for g in res["summary"]["lost"]], [("torch", "use")])

    def test_a_pass_drains_an_equipped_torch_to_zero_too(self):
        res = self.run_ep([ev(1, "pass", hours=2)], inventory=inv(("torch", 15, 1)))
        self.assertIn(("break", "ไฟฉายพัง!"), self.popups(res))
        self.assertEqual(res["end"]["inv"], [])

    def test_torch_in_the_bag_does_not_burn_on_a_pass(self):
        res = self.run_ep([ev(1, "unequip", item="torch"), ev(2, "pass", hours=2)],
                          inventory=inv(("torch", 35, 1), ("phone", 90, 1)))
        end = {e["id"]: e for e in res["end"]["inv"]}
        self.assertEqual(end["torch"]["value"], 35)
        self.assertEqual(end["torch"]["equipped"], False)  # carried to the next episode
        self.assertEqual(end["phone"]["value"], 86)  # bag items drain whenever

    def test_equipped_flag_survives_into_the_next_episode(self):
        self.make([ev(1, "unequip", item="torch")], inventory=inv(("torch", 35, 1)))
        game_state.run_episode(self.root, "ep04", commit=True)
        self.put("ep05/events.json", [ev(1, "pass", "22:00", hours=1)])
        res = game_state.run_episode(self.root, "ep05")
        self.assertEqual(res["end"]["inv"][0]["value"], 35)

    def test_count_item_used_up_says_empty(self):
        res = self.run_ep([ev(1, "eat", item="rice")], inventory=inv(("rice", 1, 2)))
        self.assertEqual(self.popups(res), [("gain", "+20 อิ่ม"), ("empty", "ข้าวสารหมด!")])
        self.assertEqual(res["end"]["inv"], [])

    def test_hunger_zero_for_a_whole_pass_warns_and_goes_on(self):
        res = self.run_ep([ev(1, "pass", hours=2), ev(2, "damage", hp=-1)], hunger=0)
        self.assertIn(("warn", "หิวมาก!"), self.popups(res))
        self.assertEqual((res["end"]["hunger"], res["end"]["hp"]), (0, 79))
        calm = self.run_ep([ev(1, "pass", hours=1)], hunger=10)
        self.assertNotIn("warn", [k for k, _ in self.popups(calm)])


class Spoilage(Base):
    def test_food_spoils_when_the_day_rolls_over_and_stays_in_the_bag(self):
        res = self.run_ep([ev(1, "pass", hours=4)], inventory=inv(("cooked_rice", 1, 3)))
        self.assertIn(("warn", "ข้าวสวยเสียแล้ว"), self.popups(res))
        self.assertTrue(self.slots(res["hud"]["inv"][-1])["cooked_rice"]["spoiled"])
        self.assertEqual((res["end"]["day"], res["end"]["clock"]), (4, "02:00"))
        self.assertEqual([e["id"] for e in res["end"]["inv"]], ["cooked_rice"])
        self.assertEqual([r["id"] for r in res["summary"]["remaining"] if r["spoiled"]], ["cooked_rice"])

    def test_eating_spoiled_food_is_an_error(self):
        with self.assertRaises(GameError) as cm:
            self.run_ep([ev(1, "pass", hours=4), ev(2, "eat", "02:30", item="cooked_rice")],
                        inventory=inv(("cooked_rice", 1, 3)))
        self.assertIn("เสียแล้ว", str(cm.exception))
        self.assertIn("spoiled", str(cm.exception))

    def test_food_already_spoiled_at_the_start(self):
        with self.assertRaises(GameError):
            self.run_ep([ev(1, "eat", item="cooked_rice")], inventory=inv(("cooked_rice", 1, 1)))
        res = self.run_ep([ev(1, "damage", hp=-1)], inventory=inv(("cooked_rice", 1, 1)))
        self.assertTrue(self.slots(res["hud"]["inv"][0])["cooked_rice"]["spoiled"])
        self.assertEqual(self.popups(res), [("lose", "-1 พลังชีวิต")])  # no warning for what was spoiled before

    def test_eating_picks_the_fresh_stack(self):
        res = self.run_ep([ev(1, "eat", item="cooked_rice")], inventory=inv(("cooked_rice", 1, 1), ("cooked_rice", 2, 3)))
        self.assertEqual([(e["got_day"], e["value"]) for e in res["end"]["inv"]], [(1, 1), (3, 1)])

    def test_unspoiled_until_day_minus_got_day_reaches_the_limit(self):
        res = self.run_ep([ev(1, "damage", hp=-1)], inventory=inv(("cooked_rice", 1, 3)))
        self.assertFalse(self.slots(res["hud"]["inv"][0])["cooked_rice"]["spoiled"])


class Loadout(Base):
    SMALL = {k: ITEMS[k] for k in ("boots", "stick", "gloves")}

    def test_loadout_drops_the_stick_after_its_break_event(self):
        res = self.run_ep([ev(5.0, "break", item="stick")], items=self.SMALL, inventory=inv(("boots", 100, 1), ("stick", 100, 1)),
                          stills={"K1": 0.0, "K2": 4.9, "K3": 5.0, "K4": 6.3})
        lo = res["loadout"]
        self.assertEqual(lo["K1"], ["boots", "stick"])
        self.assertEqual(lo["K2"], ["boots", "stick"])
        self.assertEqual(lo["K3"], ["boots"])
        self.assertEqual(lo["K4"], ["boots"])

    def test_equip_and_unequip_change_the_loadout(self):
        res = self.run_ep([ev(2.0, "unequip", item="boots"), ev(5.0, "equip", item="boots")], items=self.SMALL,
                          inventory=inv(("boots", 100, 1)), stills={"K1": 1.0, "K2": 3.0, "K3": 6.0})
        self.assertEqual([res["loadout"][k] for k in ("K1", "K2", "K3")], [["boots"], [], ["boots"]])
        self.assertEqual(res["loadout"]["_en"]["K2"], "no rubber boots, no wooden stick, no gloves")  # items.json order

    def test_loot_adds_to_the_loadout(self):
        res = self.run_ep([ev(2.0, "loot", item="gloves")], items=self.SMALL, inventory=inv(("boots", 100, 1)),
                          stills={"K1": 1.0, "K2": 2.0})
        self.assertEqual((res["loadout"]["K1"], res["loadout"]["K2"]), (["boots"], ["boots", "gloves"]))

    def test_nothing_held(self):
        res = self.run_ep([], items={"stick": ITEMS["stick"]}, inventory=[], stills={"K1": 0})
        self.assertEqual(res["loadout"]["_en"]["K1"], "no wooden stick")
        res = self.run_ep([], items={"phone": ITEMS["phone"]}, inventory=[], stills={"K1": 0})
        self.assertEqual(res["loadout"]["_en"]["K1"], "carries nothing")


class PopupsAndClock(Base):
    def test_long_names_still_fit_in_18_chars(self):
        items = dict(ITEMS, big=item("ไฟฉายแรงสูงกันน้ำพิเศษมาก", "a big torch", "hand", drain_per_hour=10))
        res = self.run_ep([ev(1, "pass", hours=1)], items=items, inventory=inv(("big", 35, 1)))
        pops = res["hud"]["popups"]
        self.assertEqual([p["kind"] for p in pops], ["drain"])
        self.assertLessEqual(len(pops[0]["text_th"]), 18)
        self.assertIn("35%", pops[0]["text_th"])
        self.assertIn("25%", pops[0]["text_th"])

    def test_guillemets_are_stripped(self):
        items = dict(ITEMS, rice=dict(ITEMS["rice"], name_th="«ข้าว»"))
        res = self.run_ep([ev(1, "loot", item="rice")], items=items)
        self.assertEqual(res["hud"]["popups"][0]["text_th"], "+1 ข้าว")

    def test_clock_past_midnight_is_the_next_day(self):
        res = self.run_ep([ev(1, "damage", "07:00", hp=-1)])
        self.assertEqual((res["end"]["day"], res["end"]["clock"]), (4, "07:00"))

    def test_clock_inside_a_pass_is_moved_to_its_end_with_a_warning(self):
        res = self.run_ep([ev(1, "pass", "22:00", hours=2), ev(2, "damage", "23:00", hp=-1)], stills={})
        self.assertEqual((res["end"]["day"], res["end"]["clock"]), (4, "00:00"))
        self.assertEqual(len(res["warnings"]), 1)
        self.assertIn("inside the previous pass", res["warnings"][0])

    def test_missing_stills_file_warns(self):
        res = self.run_ep([ev(1, "damage", hp=-1)])
        self.assertEqual(res["loadout"], {"_en": {}})
        self.assertTrue(any("stills.json" in w for w in res["warnings"]))

    def test_a_pass_ends_the_episode_on_the_new_clock(self):
        res = self.run_ep([ev(1, "pass", "22:30", hours=1.5)])
        self.assertEqual((res["end"]["day"], res["end"]["clock"]), (4, "00:00"))

    def test_loot_stacks_within_one_day_but_not_across_days(self):
        res = self.run_ep([ev(1, "loot", item="rice"), ev(2, "loot", item="rice", n=2), ev(3, "pass", hours=3),
                           ev(4, "loot", "01:00", item="rice")], inventory=[])
        self.assertEqual([(e["id"], e["value"], e["got_day"]) for e in res["end"]["inv"]],
                         [("rice", 3, 3), ("rice", 1, 4)])


class Cli(Base):
    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = game_state.main(list(args) + ["--root", str(self.root)])
        return code, out.getvalue()

    def test_default_prev_commit_and_chaining(self):
        self.make([ev(1, "pass", hours=3), ev(2, "eat", "01:00", item="rice")], stills={"K1": 0.0})
        state_file = self.root / "canon/state/ep04-end.json"
        code, out = self.cli("ep04")
        self.assertEqual(code, 0)
        self.assertIn("hunger", out)
        self.assertFalse(state_file.exists())  # no --commit, no write
        for name in ("end", "hud", "loadout", "summary"):
            self.assertTrue((self.root / ("ep04/game/%s.json" % name)).exists())
        code, out = self.cli("ep04", "--commit")
        self.assertEqual(code, 0)
        self.assertEqual(state_file.read_bytes(), (self.root / "ep04/game/end.json").read_bytes())
        # ep05 starts from ep04's end state by default; --prev names it explicitly
        self.put("ep05/events.json", [ev(1, "pass", "01:00", hours=2)])
        code, _ = self.cli("ep05")
        self.assertEqual(code, 0)
        end5 = json.loads((self.root / "ep05/game/end.json").read_text(encoding="utf-8"))
        end4 = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual((end5["ep"], end5["day"], end5["clock"]), (5, 4, "03:00"))
        self.assertEqual(end5["hunger"], end4["hunger"] - 3)
        self.assertEqual(self.cli("ep05", "--prev", "ep04")[0], 0)
        self.assertEqual(self.cli("ep05", "--prev", "ep03")[0], 0)

    def test_cli_error_leaves_canon_alone(self):
        self.make([ev(1, "eat", item="plaster2")])
        code, _ = self.cli("ep04", "--commit")
        self.assertEqual(code, 1)
        self.assertFalse((self.root / "canon/state/ep04-end.json").exists())


# ================================================================ New v3 Tests

class V3VerbsAndClamping(Base):
    def test_water_verb_gain_lose_and_clamping(self):
        # Starts at 90; +20 clamps at 100; -150 clamps at 0 with warning
        res = self.run_ep([ev(1, "water", delta=20), ev(2, "water", delta=-150)], water=90)
        self.assertEqual(res["hud"]["bars"][1]["water"], 100)
        self.assertEqual(res["hud"]["bars"][2]["water"], 0)
        self.assertEqual(res["end"]["water"], 0)
        self.assertIn(("gain", "+10 น้ำในร่างกาย"), self.popups(res))
        self.assertIn(("lose", "-100 น้ำในร่างกาย"), self.popups(res))
        self.assertTrue(any("body water reached 0" in w for w in res["warnings"]))

    def test_mind_verb_gain_lose_and_clamping(self):
        # Starts at 85; +25 clamps at 100; -200 clamps at 0 with warning
        res = self.run_ep([ev(1, "mind", delta=25), ev(2, "mind", delta=-200)], mind=85)
        self.assertEqual(res["hud"]["bars"][1]["mind"], 100)
        self.assertEqual(res["hud"]["bars"][2]["mind"], 0)
        self.assertEqual(res["end"]["mind"], 0)
        self.assertIn(("gain", "+15 สติ"), self.popups(res))
        self.assertIn(("lose", "-100 สติ"), self.popups(res))
        self.assertTrue(any("mind reached 0" in w for w in res["warnings"]))

    def test_money_verb_and_non_negative_clamping(self):
        # Starts at 3000 THB; can gain past 100; clamps at >= 0
        res = self.run_ep([ev(1, "money", delta=500), ev(2, "money", delta=-5000)], money=3000)
        self.assertEqual(res["hud"]["bars"][1]["money"], 3500)
        self.assertEqual(res["hud"]["bars"][2]["money"], 0)
        self.assertEqual(res["end"]["money"], 0)
        self.assertIn(("gain", "+500 บาท"), self.popups(res))
        self.assertIn(("lose", "-3500 บาท"), self.popups(res))
        self.assertTrue(any("money reached 0" in w for w in res["warnings"]))

    def test_xp_and_level_verb(self):
        # XP gain, badge award, and level setting
        res = self.run_ep([
            ev(1, "xp", delta=30, badge="ต้มน้ำ Lv1", level=2),
            ev(2, "xp", delta=150)  # clamps at 100
        ], xp=20, level=1)
        self.assertEqual(res["end"]["xp"], 100)
        self.assertEqual(res["end"]["level"], 2)
        self.assertIn("ต้มน้ำ Lv1", res["end"]["badges"])
        self.assertIn(("gain", "+30 XP"), self.popups(res))
        self.assertIn(("gain", "ต้มน้ำ Lv1"), self.popups(res))
        self.assertIn(("gain", "+50 XP"), self.popups(res))

    def test_trust_verb_and_per_npc_clamping(self):
        # Trust tracked per NPC, clamped to [0, 100]
        res = self.run_ep([
            ev(1, "trust", npc="ป้าข้างบ้าน", delta=25),      # 80 + 25 -> clamps 100
            ev(2, "trust", npc="ชายหมวกตกปลา", delta=120),    # 0 + 120 -> clamps 100
            ev(3, "trust", npc="ชายหมวกตกปลา", delta=-150),   # 100 - 150 -> clamps 0
            ev(4, "trust", npc="คนแปลกหน้า", value=60),        # direct value setting
        ], trust={"ป้าข้างบ้าน": 80, "ชายหมวกตกปลา": 0})
        self.assertEqual(res["end"]["trust"]["ป้าข้างบ้าน"], 100)
        self.assertEqual(res["end"]["trust"]["ชายหมวกตกปลา"], 0)
        self.assertEqual(res["end"]["trust"]["คนแปลกหน้า"], 60)
        self.assertIn(("gain", "+20 ไว้ใจ (ป้าข้างบ้าน)"), self.popups(res))
        self.assertIn(("gain", "+100 ไว้ใจ (ชายหมวกตกปลา)"), self.popups(res))
        self.assertIn(("lose", "-100 ไว้ใจ (ชายหมวกตกปลา)"), self.popups(res))

    def test_world_verb(self):
        # World event popup and log
        res = self.run_ep([ev(1, "world", text_th="สัญญาณมือถือหายแล้ว", rule="T1a")])
        self.assertIn(("warn", "สัญญาณมือถือหายแล้ว"), self.popups(res))

    def test_container_verb(self):
        # Container slots setting via integer and named containers
        res = self.run_ep([
            ev(1, "container", slots=5),
            ev(2, "container", container="เป้"),
            ev(3, "container", container="แพ")
        ])
        self.assertEqual(res["end"]["container_slots"], 12)
        self.assertIn(("gain", "กระเป๋า 5 ช่อง"), self.popups(res))
        self.assertIn(("gain", "กระเป๋า 8 ช่อง"), self.popups(res))
        self.assertIn(("gain", "กระเป๋า 12 ช่อง"), self.popups(res))

    def test_v3_state_defaults_when_omitted(self):
        # Old start state without v3 fields loads safely with defaults
        res = self.run_ep([])
        self.assertEqual(res["end"]["water"], 100)
        self.assertEqual(res["end"]["mind"], 100)
        self.assertEqual(res["end"]["money"], 0)
        self.assertEqual(res["end"]["xp"], 0)
        self.assertEqual(res["end"]["level"], 1)
        self.assertEqual(res["end"]["trust"], {})
        self.assertEqual(res["end"]["container_slots"], 8)


if __name__ == "__main__":
    unittest.main()
