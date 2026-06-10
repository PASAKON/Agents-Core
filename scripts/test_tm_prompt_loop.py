#!/usr/bin/env python3
"""Unit tests for the TraderMindset prompt learning loop.

Covers all four deliverables, no paid API touched:
  D1 externalize : registry-loaded prompts reproduce the pre-refactor strings
  D2 evolve      : reject categorization + promote-to-validator + draft writing
  D3 eval        : deterministic checks + A/B verdict (pass AND block paths)
  D4 (METRICS.md is prose — not unit-tested)

Run:
  /Users/gob/Projects/Agents/.venv/bin/python scripts/test_tm_prompt_loop.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import tm_checks            # noqa: E402
import tm_prompt_eval as ev  # noqa: E402
import tm_prompt_evolve as evo  # noqa: E402
import tm_prompts           # noqa: E402
import trader_mindset_batch as tm  # noqa: E402

GOLDEN = os.path.join(REPO, "data", "tm-golden-set.json")
FIXTURES = os.path.join(REPO, "data", "tm-eval-fixtures.json")
LESSONS_FIXTURE = os.path.join(REPO, "data", "tm-lessons-fixture.json")

# The exact caption system message before externalization (regression lock).
EXPECTED_SYS = (
    "คุณคือก็อปปี้ไรเตอร์เพจเทรดทอง MoonieX เขียนแคปชันสายจิตวิทยาการเทรด ภาษาไทย "
    "โทนสุภาพอบอุ่นแบบรุ่นพี่ ตามแนว voice เดิมของเพจ\n\n"
    "กฎเหล็ก (ห้ามฝ่าฝืน):\n"
    "- ห้ามชี้นำการลงทุน ห้ามบอกให้ซื้อ/ขาย/เข้าออเดอร์ใด ๆ\n"
    "- ห้ามการันตีกำไร ห้ามพูดถึงผลตอบแทนเป็นตัวเลข/เปอร์เซ็นต์\n"
    "- ห้ามใช้อิโมจิทุกชนิด\n"
    "- โทนสุภาพ ลงท้าย 'ครับ' เป็นธรรมชาติ เหมือนเทรดเดอร์รุ่นพี่คุยกับรุ่นน้อง\n"
    "- เป็นข้อคิด/จิตวิทยาการเทรด ไม่ใช่สัญญาณเทรด"
)

TOPIC = {"id": "t001", "slug": "t001-x", "theme": "discipline",
         "hero_word": "วินัย", "seed_idea": "กำไรระยะยาวมาจากวินัย", "used_at": None}


# --------------------------------------------------------------------------- #
# D1 — externalized prompts reproduce the original behavior
# --------------------------------------------------------------------------- #
class ExternalizedPromptTests(unittest.TestCase):
    def test_caption_system_is_byte_identical(self):
        msgs = tm.build_caption_messages(TOPIC, "")
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], EXPECTED_SYS)

    def test_caption_user_has_topic_voice_and_schema(self):
        user = tm.build_caption_messages(TOPIC, "")[1]["content"]
        self.assertIn('แกนหัวข้อ (theme=discipline): hero word = "วินัย"', user)
        self.assertIn("ไอเดียตั้งต้น: กำไรระยะยาวมาจากวินัย", user)
        self.assertIn("รูปแบบแคปชัน (อิงโพสต์ week-1):", user)   # voice baked in
        self.assertIn('"caption":', user)
        self.assertIn('"sub_line":', user)
        self.assertIn('"tags":', user)
        # no-lessons: the voice block butts straight onto the JSON instruction
        self.assertIn("ที่จุกใจ\n\nสร้างผลลัพธ์", user)

    def test_caption_lessons_injected_between_voice_and_schema(self):
        user = tm.build_caption_messages(TOPIC, "ห้ามยาวเกิน")[1]["content"]
        self.assertIn("ที่จุกใจ\n\nห้ามยาวเกิน\n\nสร้างผลลัพธ์", user)

    def test_poster_prompt_assembly_and_rotation(self):
        p0 = tm.build_poster_prompt(TOPIC, 0, "")
        self.assertTrue(p0.startswith(
            "Identity (Critical): strictly reference @image1"))
        self.assertIn("three-quarter view", p0)          # scenes[0]
        self.assertIn("INK-BRUSH", p0)                    # art_styles[0]
        self.assertIn("'วินัย' fills the upper-left with bold textured strokes.", p0)
        self.assertTrue(p0.endswith("Render the hero word accurately and legibly."))
        # idx rotates style + scene
        p1 = tm.build_poster_prompt(TOPIC, 1, "")
        self.assertIn("CHROME METALLIC", p1)             # art_styles[1]
        self.assertIn("trading desk", p1)                # scenes[1]

    def test_poster_lessons_guidance_appended_nonrendering(self):
        p = tm.build_poster_prompt(TOPIC, 0, "เพี้ยน\nนอกแบรนด์")
        self.assertIn("Internal art-direction guidance (DO NOT render", p)
        self.assertIn("เพี้ยน นอกแบรนด์", p)              # newlines flattened to spaces
        self.assertTrue(p.endswith("Keep the poster clean and on-brand."))

    def test_registry_active_is_v1(self):
        reg = tm_prompts.load_registry(force=True)
        self.assertEqual(reg["active"], {"caption": "v1", "poster": "v1"})
        self.assertTrue(any(h["version"] == "v1" for h in reg["history"]))


# --------------------------------------------------------------------------- #
# D3 — deterministic checks (tm_checks)
# --------------------------------------------------------------------------- #
class DeterministicCheckTests(unittest.TestCase):
    WEEK1 = [
        'แต่ซ่อนอยู่ใน "วินัย" ของเราครับ\n.\nคนมีวินัย ทำกำไรได้ทั้งเส้นทาง',
        'ความเก่งทำให้เราเข้าออเดอร์ได้สวย\nแต่ความอดทน ทำให้เราอยู่ในเกมนานพอ',  # descriptive "เข้าออเดอร์"
    ]

    def test_week1_examples_pass(self):
        for cap in self.WEEK1:
            self.assertTrue(tm_checks.check_caption(cap, "")["passed"], cap)

    def test_emoji_caught(self):
        r = tm_checks.check_caption("กำไรมาจากการรอ 🚀", "")
        self.assertFalse(r["passed"])
        self.assertFalse(r["checks"]["emoji"])

    def test_profit_guarantee_caught_but_negation_passes(self):
        self.assertFalse(tm_checks.check_caption("ทำตามนี้การันตีกำไรครับ", "รวยแน่")["passed"])
        # compliant anti-guarantee must NOT trip the bare word
        self.assertTrue(tm_checks.check_caption("ไม่มีใครการันตีตลาดได้ครับ", "")["passed"])

    def test_percentage_caught(self):
        self.assertFalse(tm_checks.check_caption("ทำกำไร 80% ต่อเดือน", "")["checks"]["percentage"])

    def test_length_limits(self):
        self.assertFalse(tm_checks.check_caption("ก" * (tm_checks.CAPTION_MAX_CHARS + 1), "")["passed"])
        self.assertFalse(tm_checks.check_caption("ok", "ย" * (tm_checks.SUBLINE_MAX_CHARS + 1))["passed"])

    def test_directive_is_soft_warning_not_hard_fail(self):
        r = tm_checks.check_caption("เห็นแบบนี้ ตามไม้นี้ได้เลย", "")
        self.assertTrue(r["passed"])        # not a hard violation
        self.assertTrue(r["warnings"])      # but flagged as a soft signal


# --------------------------------------------------------------------------- #
# D2 — reflective evolve: categorize + promote + draft
# --------------------------------------------------------------------------- #
class EvolveTests(unittest.TestCase):
    def test_categorizer(self):
        self.assertEqual(evo.categorize("แคปชันยาวเกินไป อ่านแล้วเยอะ"), "too_long")
        self.assertEqual(evo.categorize("โทนแข็งไป ไม่เหมือนรุ่นพี่"), "tone")
        self.assertEqual(evo.categorize("ใส่อิโมจิเยอะไป"), "emoji")
        self.assertEqual(evo.categorize("การันตีกำไรเกินจริง"), "guarantee")
        self.assertEqual(evo.categorize("ชี้นำให้ซื้อทองชัดไป"), "advice")
        self.assertEqual(evo.categorize("อะไรก็ไม่รู้"), "other")

    def test_promote_threshold_partition(self):
        grouped = {"too_long": [1, 2], "tone": [1]}
        promote, fold = evo.split_promote_fold(grouped, 2)
        self.assertIn("too_long", promote)
        self.assertIn("tone", fold)
        self.assertNotIn("too_long", fold)

    def test_evolve_dry_writes_parseable_draft_and_flags(self):
        lessons = json.load(open(LESSONS_FIXTURE, encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            res = evo.evolve(lessons, "caption", d, dry=True, model="x",
                             threshold=2, banner_date="2026-06-10")
            self.assertIn("too_long", res["promote"])     # repeated -> promote
            self.assertIn("tone", res["fold"])            # one-off -> fold
            self.assertTrue(os.path.exists(res["draft_path"]))
            draft = open(res["draft_path"], encoding="utf-8").read()
            sections = tm_prompts.parse_prompt_md(draft)
            self.assertEqual(set(sections), {"system", "user"})         # still parseable
            self.assertIn("{{lessons}}", sections["user"])              # slots intact
            self.assertIn("บทเรียนที่ห้ามพลาดซ้ำ", sections["system"])   # tone folded in
            report = evo.render_report("caption", res["src_version"], res["draft_version"],
                                       len(lessons), res["grouped"], res["promote"],
                                       res["fold"], res["draft_path"], 2)
            self.assertIn("PROMOTE TO VALIDATOR:", report)
            self.assertIn("too_long", report)

    def test_evolve_does_not_touch_registry(self):
        reg_path = os.path.join(tm_prompts.PROMPTS_DIR, "registry.json")
        before = json.load(open(reg_path, encoding="utf-8"))
        lessons = json.load(open(LESSONS_FIXTURE, encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            evo.evolve(lessons, "caption", d, dry=True, model="x", threshold=2, banner_date="2026-06-10")
        after = json.load(open(reg_path, encoding="utf-8"))
        self.assertEqual(before["active"], after["active"])


# --------------------------------------------------------------------------- #
# D3 — eval gate verdict (pass + block)
# --------------------------------------------------------------------------- #
class EvalGateTests(unittest.TestCase):
    def test_golden_dry_eval_passes(self):
        cases = ev.load_golden(GOLDEN)
        fixtures = ev.load_fixtures(FIXTURES)
        res = ev.evaluate(cases, "v1", "v2", dry=True, fixtures=fixtures, model="x", eps=ev.TIE_EPS)
        self.assertEqual(res["loses"], 0)
        self.assertEqual(res["critical"], 0)
        self.assertGreaterEqual(res["wins"], 1)
        self.assertTrue(res["activate_ok"])
        self.assertIn("ACTIVATE-OK", ev.render_report(res))

    def test_main_dry_exit_zero(self):
        self.assertEqual(ev.main(["--dry"]), 0)

    def test_block_when_candidate_leaks_on_negative(self):
        # B regresses: emits an emoji on the emoji must-fail case; A clean.
        case = [{"id": "neg-emoji", "kind": "caption", "type": "negative",
                 "theme": "patience", "hero_word": "ใจเย็น", "expect": "emoji",
                 "seed_idea": "x"}]
        fixtures = {"neg-emoji": {
            "a": {"caption": "ใจเย็นไว้ครับ", "sub_line": "", "tags": []},
            "b": {"caption": "ใจเย็นไว้ครับ 😄", "sub_line": "", "tags": []}}}
        res = ev.evaluate(case, "v1", "v2", dry=True, fixtures=fixtures, model="x", eps=ev.TIE_EPS)
        self.assertEqual(res["loses"], 1)
        self.assertEqual(res["critical"], 1)
        self.assertFalse(res["activate_ok"])
        self.assertIn("BLOCKED", ev.render_report(res))

    def test_block_when_candidate_adds_hard_violation_positive(self):
        # B introduces a guarantee on a positive case A handled cleanly.
        case = [{"id": "pos", "kind": "caption", "type": "positive",
                 "theme": "lesson", "hero_word": "กำไร", "seed_idea": "x"}]
        fixtures = {"pos": {
            "a": {"caption": "กำไรมาจากการรอครับ", "sub_line": "", "tags": []},
            "b": {"caption": "ทำตามเพจการันตีกำไรครับ", "sub_line": "", "tags": []}}}
        res = ev.evaluate(case, "v1", "v2", dry=True, fixtures=fixtures, model="x", eps=ev.TIE_EPS)
        self.assertFalse(res["activate_ok"])
        self.assertEqual(res["critical"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
