"""Tests for the fal loader in align.py (task-ee1dbcf0).  python3 -m unittest prototypes/ilag-hookdemo/test_align.py -v
Synthetic fal file (no takes needed); the 3 real takes are also loaded when the voice-v4 folder is on this box."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import align  # noqa: E402

HERE = Path(__file__).resolve().parent
NARR = (HERE / "narration.txt").read_text(encoding="utf-8")
PHRASES = align.load(HERE / "phrases.json")


def fal_doc(narration=NARR, n=3):
    chars = list(narration.strip())
    step = -(-len(chars) // n)
    chunks = []
    for k in range(n):
        part = chars[k * step:(k + 1) * step]
        base = k * step
        chunks.append({"characters": part, "character_start_times_seconds": [round((base + i) * 0.1, 3) for i in range(len(part))],
                       "character_end_times_seconds": [round((base + i + 1) * 0.1, 3) for i in range(len(part))]})
    return {"audio": {"url": "x"}, "timestamps": chunks}


def tagged(doc, tag, every_line):
    """The same fal doc with `tag` + a space in front of the text (and of every line when every_line).  The tag characters get a
    zero-width time at the start of the character they precede, as a voice that says nothing for them would."""
    ch, st, en = [], [], []
    for c in doc["timestamps"]:
        ch += c["characters"]
        st += c["character_start_times_seconds"]
        en += c["character_end_times_seconds"]
    oc, os_, oe = [], [], []
    for i, u in enumerate(ch):
        if i == 0 or (every_line and ch[i - 1] == "\n"):
            for t in tag + " ":
                oc.append(t)
                os_.append(st[i])
                oe.append(st[i])
        oc.append(u)
        os_.append(st[i])
        oe.append(en[i])
    n = -(-len(oc) // 3)
    return {"audio": {}, "timestamps": [{"characters": oc[k:k + n], "character_start_times_seconds": os_[k:k + n],
                                         "character_end_times_seconds": oe[k:k + n]} for k in range(0, len(oc), n)]}


class PaceTags(unittest.TestCase):
    def setUp(self):
        self.plain = align.phrase_times(align.join_fal(fal_doc(), NARR), PHRASES)

    def test_tag_at_start_only(self):
        for tag in ("[rushed]", "[speaking quickly]"):
            with self.subTest(tag=tag):
                a = align.join_fal(tagged(fal_doc(), tag, False), NARR)
                self.assertNotIn("[", "".join(a["characters"]))
                self.assertEqual(align.phrase_times(a, PHRASES), self.plain)

    def test_tag_at_start_of_every_line(self):
        d = tagged(fal_doc(), "[rushed]", True)
        flat = "".join("".join(c["characters"]) for c in d["timestamps"])
        self.assertEqual(flat.count("[rushed]"), 6)
        a = align.join_fal(d, NARR)
        self.assertEqual(align.squeeze("".join(a["characters"])), align.squeeze(NARR))   # the space after a tag may stay
        self.assertEqual(align.phrase_times(a, PHRASES), self.plain)

    def test_tags_already_stripped_by_fal(self):
        self.assertEqual(align.phrase_times(align.join_fal(fal_doc(), NARR), PHRASES), self.plain)

    def test_tagged_narration_text_also_compares(self):
        a = align.join_fal(tagged(fal_doc(), "[rushed]", True), "[rushed] " + NARR.replace("\n", "\n[rushed] "))
        self.assertEqual(align.phrase_times(a, PHRASES), self.plain)

    def test_tag_split_across_chunks(self):
        d = tagged(fal_doc(), "[speaking quickly]", False)   # 18 characters, the chunk size is far more, so force a split
        flat = d["timestamps"]
        for k in ("characters", "character_start_times_seconds", "character_end_times_seconds"):
            joined = [x for c in flat for x in c[k]]
            for n, c in enumerate(flat):
                c[k] = joined[n * 10:(n + 1) * 10] if n < len(flat) - 1 else joined[n * 10:]
        self.assertEqual(align.phrase_times(align.join_fal(d, NARR), PHRASES), self.plain)

    def test_plain_alignment_with_tags(self):
        d = tagged(fal_doc(), "[rushed]", True)
        flat = {k: [x for c in d["timestamps"] for x in c[k]] for k in align.KEYS}
        a = align.load_alignment(self._write(flat))
        self.assertEqual(align.phrase_times(a, PHRASES), self.plain)

    def test_unclosed_and_stray_brackets_fail(self):
        d = fal_doc()
        d["timestamps"][0]["characters"][2] = "["
        with self.assertRaisesRegex(align.AlignError, "never closed"):
            align.join_fal(d, NARR)
        d = fal_doc()
        d["timestamps"][0]["characters"][2] = "]"
        with self.assertRaisesRegex(align.AlignError, "stray"):
            align.join_fal(d, NARR)

    def test_real_take_with_tag_in_front(self):
        f = Path("/opt/MoonieXHQ/Work/task-e58b9235/voice-v4/takes/t3_George_s0.3.json")
        if not f.exists():
            self.skipTest("voice-v4 takes not on this box")
        d = align.load(f)
        want = align.phrase_times(align.load_alignment(f, HERE / "narration.txt"), PHRASES)
        for every in (False, True):
            with self.subTest(every_line=every):
                a = align.join_fal(tagged(d, "[rushed]", every), NARR)
                self.assertEqual(align.phrase_times(a, PHRASES), want)

    def _write(self, doc):
        import json
        import tempfile
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(doc, f)
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name


class FalLoader(unittest.TestCase):
    def test_joins_and_maps_all_phrases(self):
        a = align.join_fal(fal_doc(), NARR)
        self.assertEqual(len(a["characters"]), len(NARR.strip()))
        t = align.phrase_times(a, PHRASES)
        self.assertEqual([len(r) for r in t], [len(p) for p in PHRASES])
        self.assertTrue(all(e > s for r in t for s, e in r))

    def test_missing_key(self):
        d = fal_doc()
        del d["timestamps"][1]["character_end_times_seconds"]
        with self.assertRaisesRegex(align.AlignError, "chunk 1 lacks 'character_end_times_seconds'"):
            align.join_fal(d, NARR)

    def test_time_backwards(self):
        d = fal_doc()
        d["timestamps"][2]["character_start_times_seconds"][0] = 0.0
        with self.assertRaisesRegex(align.AlignError, "goes backwards"):
            align.join_fal(d, NARR)

    def test_text_mismatch(self):
        d = fal_doc()
        d["timestamps"][0]["characters"][5] = "ก"
        with self.assertRaisesRegex(align.AlignError, "do not match the narration"):
            align.join_fal(d, NARR)

    def test_truncated(self):
        d = fal_doc()
        d["timestamps"].pop()
        with self.assertRaisesRegex(align.AlignError, "do not match"):
            align.join_fal(d, NARR)

    def test_ignores_whitespace_and_dots(self):
        self.assertEqual(align.squeeze("a b\nc..."), "abc")

    def test_not_fal(self):
        with self.assertRaises(align.AlignError):
            align.join_fal({"words": []}, NARR)

    def test_real_takes(self):
        takes = Path("/opt/MoonieXHQ/Work/task-e58b9235/voice-v4/takes")
        files = sorted(takes.glob("*.json")) if takes.is_dir() else []
        if not files:
            self.skipTest("voice-v4 takes not on this box")
        for f in files:
            with self.subTest(take=f.name):
                a = align.load_alignment(f, HERE / "narration.txt")
                self.assertEqual(len(align.phrase_times(a, PHRASES)), 6)


if __name__ == "__main__":
    unittest.main()
