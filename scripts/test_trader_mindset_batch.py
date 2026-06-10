#!/usr/bin/env python3
"""Unit tests for scripts/trader_mindset_batch.py.

No paid API is ever touched: the composite/stamp/prompt paths are pure and the
dry-run is asserted to make zero network calls. Run:

  /Users/gob/Projects/Agents/.venv/bin/python scripts/test_trader_mindset_batch.py

The Thai-shaping test also writes a visual proof poster to
  output/trader-mindset/_test/sample_composite.png
so the reviewer can eyeball that tone marks sit correctly (not floating).
"""
from __future__ import annotations

import io
import os
import sys
import unittest
import urllib.request
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trader_mindset_batch as tm  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ARTIFACT_DIR = os.path.join(tm.OUT_ROOT, "_test")


class TopicPoolTests(unittest.TestCase):
    def setUp(self):
        self.doc = tm.load_topics()
        self.topics = self.doc["topics"]

    def test_at_least_40_topics(self):
        self.assertGreaterEqual(len(self.topics), 40, "need >= 40 seed topics")

    def test_four_themes_present(self):
        themes = {t["theme"] for t in self.topics}
        self.assertEqual(themes, {"discipline", "patience", "focus", "lesson"})

    def test_slugs_unique(self):
        slugs = [t["slug"] for t in self.topics]
        self.assertEqual(len(slugs), len(set(slugs)), "slugs must be unique")

    def test_required_keys_and_ascii_slug(self):
        for t in self.topics:
            for k in ("id", "slug", "theme", "hero_word", "seed_idea", "used_at"):
                self.assertIn(k, t, f"{t.get('id')} missing {k}")
            self.assertTrue(t["slug"].isascii(), f"{t['slug']} must be ascii (filename safe)")
            self.assertIsNone(t["used_at"], "seed pool must ship all-unused")


class PickTopicsTests(unittest.TestCase):
    def test_unused_first_then_lru(self):
        doc = {"topics": [
            {"id": "t001", "slug": "a", "theme": "x", "hero_word": "h", "seed_idea": "s",
             "used_at": "2026-06-01T00:00:00Z"},
            {"id": "t002", "slug": "b", "theme": "x", "hero_word": "h", "seed_idea": "s",
             "used_at": None},
            {"id": "t003", "slug": "c", "theme": "x", "hero_word": "h", "seed_idea": "s",
             "used_at": None},
        ]}
        # count=1 -> first unused in file order
        self.assertEqual([t["slug"] for t in tm.pick_topics(doc, 1)], ["b"])
        # count=3 -> both unused first, then least-recently-used fills the gap
        self.assertEqual([t["slug"] for t in tm.pick_topics(doc, 3)], ["b", "c", "a"])


class DryRunTests(unittest.TestCase):
    def test_dry_run_makes_no_network_call_and_no_round_dir(self):
        before = set(os.listdir(tm.OUT_ROOT)) if os.path.isdir(tm.OUT_ROOT) else set()

        def boom(*a, **k):
            raise AssertionError("dry run must not open any network connection")

        orig = urllib.request.urlopen
        urllib.request.urlopen = boom
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tm.main(["--dry", "--count", "3"])
            out = buf.getvalue()
        finally:
            urllib.request.urlopen = orig

        self.assertEqual(rc, 0)
        self.assertIn("[DRY] no API calls", out)
        self.assertIn("poster fal prompt", out)
        self.assertIn("caption LLM", out)
        # dry must not create a round-NNN directory
        after = set(os.listdir(tm.OUT_ROOT)) if os.path.isdir(tm.OUT_ROOT) else set()
        new_rounds = {d for d in (after - before) if d.startswith("round-")}
        self.assertFalse(new_rounds, f"dry run leaked round dirs: {new_rounds}")


class CaptionGuardTests(unittest.TestCase):
    def test_emoji_rejected(self):
        with self.assertRaises(ValueError):
            tm._assert_caption_clean("กำไรมาจากการรอ 🚀", "วินัยคือทุกอย่าง")

    def test_guarantee_phrase_rejected(self):
        with self.assertRaises(ValueError):
            tm._assert_caption_clean("ทำตามนี้แล้วการันตีกำไรครับ", "รวยแน่")

    def test_clean_caption_passes(self):
        tm._assert_caption_clean("กำไรมาจากการรอ\n.\nขาดทุนมาจากการรีบ", "ใจเย็นไว้ครับ")

    def test_json_parse_tolerates_fences(self):
        obj = tm._parse_json_object('```json\n{"a": 1, "b": "ค่า"}\n```')
        self.assertEqual(obj["a"], 1)
        self.assertEqual(obj["b"], "ค่า")


class ThaiCompositeTests(unittest.TestCase):
    """The headline risk: Thai tone marks must stack correctly, not float."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(ARTIFACT_DIR, exist_ok=True)

    def test_raqm_available(self):
        from PIL import features
        self.assertTrue(features.check("raqm"),
                        "libraqm required for correct Thai shaping")

    def _ink_bbox(self, text, size=120):
        """Render black text on white with RAQM, return (bbox, width)."""
        font = ImageFont.truetype(tm.FONT_SEMIBOLD, size, layout_engine=ImageFont.Layout.RAQM)
        im = Image.new("L", (size * len(text) + size, size * 3), 255)
        d = ImageDraw.Draw(im)
        d.text((size, size), text, font=font, fill=0)
        inv = Image.eval(im, lambda p: 255 - p)  # ink -> nonzero
        return inv.getbbox(), d.textlength(text, font=font)

    def test_tone_marks_stack_above_base(self):
        # "ที่" = ท (base) + sara ii (above) + mai ek (tone, stacks higher)
        base_bbox, base_w = self._ink_bbox("ท")
        full_bbox, full_w = self._ink_bbox("ที่")
        self.assertIsNotNone(base_bbox)
        self.assertIsNotNone(full_bbox)
        # marks render ABOVE the base -> the composed cluster's ink top is higher
        self.assertLess(full_bbox[1], base_bbox[1],
                        "tone-mark stack should extend above the base glyph")
        # marks are non-spacing -> they must NOT add horizontal advance like loose glyphs
        self.assertLessEqual(full_w, base_w + 2,
                             "tone marks must not advance horizontally (would mean floating)")

    def test_composite_subline_draws_gold_text_in_band(self):
        # dummy "baked" base: navy with a fake gold hero word up top (no network)
        W = H = 1024
        base = Image.new("RGB", (W, H), tm.NAVY)
        d = ImageDraw.Draw(base)
        hero = ImageFont.truetype(tm.FONT_SEMIBOLD, 220, layout_engine=ImageFont.Layout.RAQM)
        d.text((90, 120), "วินัย", font=hero, fill=tm.GOLD)

        sub = "ตลาดไม่ให้รางวัลคนเก่ง แต่ให้คนที่อดทน"
        out = tm.composite_subline(base, sub)
        self.assertEqual(out.size, (W, H))

        # gold ink must appear in the lower band where the sub-line is drawn
        band = out.convert("RGB").crop((0, int(H * 0.70), W, H))
        px = band.load()
        gold_hits = sum(
            1
            for y in range(0, band.height, 3)
            for x in range(0, band.width, 3)
            if px[x, y][0] > 150 and px[x, y][1] > 120 and px[x, y][2] < 130
        )
        self.assertGreater(gold_hits, 200, "sub-line gold text not found in lower band")

        # stamp lockup too if the brand asset is reachable, then save proof artifact
        if os.path.exists(tm.LOCKUP):
            out = tm.stamp_lockup(out)
        proof = os.path.join(ARTIFACT_DIR, "sample_composite.png")
        out.convert("RGB").save(proof)
        self.assertTrue(os.path.exists(proof))
        print(f"\n[proof] wrote {proof}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
