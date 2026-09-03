"""Tests for scripts/prompt-lint.py, on synthetic fixtures (not the real corpus
under docs/prompts/absence/ -- those are covered by `prompt-lint.py --validate`
against the 30 known instances in AUTHORING-RULES.md).

stdlib unittest, not pytest -- pytest isn't installed in this environment and
the task brief asks for stdlib only, no new dependencies.

Run:  python3 scripts/test_prompt_lint.py
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("prompt_lint", ROOT / "scripts" / "prompt-lint.py")
assert _SPEC is not None and _SPEC.loader is not None
prompt_lint = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = prompt_lint
_SPEC.loader.exec_module(prompt_lint)


def _classes(findings) -> set[str]:
    return {f.cls for f in findings}


def _lint_text(tmp_path: Path, text: str, name: str = "fixture.txt"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return prompt_lint.lint_file(p)


class NoMarkerFile(unittest.TestCase):
    """13/16 real files have no NOTES/PASTE markers -- the whole file is the
    paste zone, so a warning-glyph/attribution/date line anywhere must fire."""

    def test_no_marker_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), "just a plain line of prose.\n")
            self.assertIn("NO_MARKER", _classes(findings))

    def test_guidance_leak_without_markers(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), '⚠️ CTO note (CEO 2026-08-30): fix this before firing.\n')
            self.assertIn("GUIDANCE_LEAK", _classes(findings))
            self.assertIn("ATTRIBUTION", _classes(findings))
            self.assertIn("DATE_STAMP", _classes(findings))
            self.assertTrue(any(f.severity == "ERROR" for f in findings))


class NotesZoneIsQuiet(unittest.TestCase):
    """Guidance sitting inside a properly closed NOTES zone is working as
    intended and must not be reported as a violation."""

    def test_notes_zone_not_scanned(self):
        import tempfile
        text = (
            "=== NOTES · DO NOT PASTE ANY OF THIS ===\n"
            "⚠️ CTO note (CEO 2026-08-30): take abcd1234 failed, fix the cart.\n"
            "=== END NOTES ===\n"
            "=== ↓↓↓ PASTE FROM HERE ↓↓↓ · everything above is notes ===\n"
            "A clean cinematic description with no guidance leak at all.\n"
            "=== ↑↑↑ PASTE STOPS HERE ↑↑↑ · everything below is notes ===\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertEqual([f for f in findings if f.severity == "ERROR"], [])


class MarkerCancelled(unittest.TestCase):
    def test_paste_this_entire_text_cancels_marker(self):
        import tempfile
        text = (
            "attach the previz, then paste THIS ENTIRE TEXT as the prompt.\n"
            "=== THE PROMPT (paste from here down) ===\n"
            "a clean description.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertIn("MARKER_CANCELLED", _classes(findings))


class SecondAtVideo(unittest.TestCase):
    def test_duplicate_at_video_in_one_block_flagged(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            "@Video 1 sets the camera. Later, @Video 1 sets it again.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertIn("SECOND_AT_VIDEO", _classes(findings))

    def test_single_at_video_per_block_not_flagged(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            "@Video 1 sets the camera and blocking for this shot.\n"
            "-----------------------------------------------------------\n"
            "@Video 1 sets the camera for the next shot's own block.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertNotIn("SECOND_AT_VIDEO", _classes(findings))


class QuotedReference(unittest.TestCase):
    def test_quoted_reference_like_string_flagged(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            'the composer showed a bare "Video — the cart design" line with no chip.\n'
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertIn("QUOTED_REFERENCE", _classes(findings))


class ProhibitionByDescription(unittest.TestCase):
    def test_two_identical_people_flagged(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            "take 1 rendered him twice, two identical men standing side by side.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertIn("PROHIBITION_BY_DESCRIPTION", _classes(findings))


class NegativeContradictsReference(unittest.TestCase):
    def test_mirror_contradiction_flagged(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            "THE PLAQUE READS CORRECT-WAY-ROUND — never mirrored.\n"
            "CRITICAL NEGATIVES: no un-mirrored plaque text.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertIn("NEGATIVE_CONTRADICTS_REFERENCE", _classes(findings))

    def test_large_crack_contradiction_flagged(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            "The crack floats in the near plane, large and unmistakable.\n"
            "CRITICAL NEGATIVES: no large crack.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertIn("NEGATIVE_CONTRADICTS_REFERENCE", _classes(findings))

    def test_no_false_alarm_without_reference(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            "CRITICAL NEGATIVES: no large crack, no smoke, no fire.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertNotIn("NEGATIVE_CONTRADICTS_REFERENCE", _classes(findings))


class MultipleShotsInBlock(unittest.TestCase):
    def test_two_zero_s_restarts_in_one_block_flagged(self):
        import tempfile
        text = (
            "=== THE PROMPT (paste from here down) ===\n"
            "[0s] first micro-event happens.\n"
            "[0s] a second, unrelated micro-event happens.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            findings = _lint_text(Path(d), text)
            self.assertIn("MULTIPLE_SHOTS_IN_BLOCK", _classes(findings))


class ShotFiltering(unittest.TestCase):
    """--shot must anchor to a block's own title line, not substring-match
    anywhere in its body (regression: S1A used to match inside the S1C
    block because S1C's body happened to mention 'S1A' in passing)."""

    def test_shot_filter_does_not_leak_into_unrelated_block(self):
        import tempfile
        text = (
            "---------------------------------------------------------------\n"
            "S1A · THE FLOOR\n"
            "---------------------------------------------------------------\n"
            "a clean description of the floor shot.\n"
            "---------------------------------------------------------------\n"
            "S1C · THE CART\n"
            "---------------------------------------------------------------\n"
            "⚠️ note (CEO 2026-09-03): S1A and S1B are unaffected by this override.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.txt"
            p.write_text(text, encoding="utf-8")
            findings = prompt_lint.lint_file(p, shot="S1A")
            # the S1C block's guidance leak must not show up under a S1A filter
            self.assertFalse(any("S1C" in f.text or "override" in f.text for f in findings))

    def test_shot_filter_finds_its_own_block(self):
        import tempfile
        text = (
            "---------------------------------------------------------------\n"
            "S1C · THE CART\n"
            "---------------------------------------------------------------\n"
            "⚠️ note (CEO 2026-09-03): fix the wheels.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.txt"
            p.write_text(text, encoding="utf-8")
            findings = prompt_lint.lint_file(p, shot="S1C")
            self.assertIn("GUIDANCE_LEAK", _classes(findings))


class ExitCode(unittest.TestCase):
    def test_clean_file_exits_zero(self):
        import subprocess
        import tempfile
        text = (
            "=== ↓↓↓ PASTE FROM HERE ↓↓↓ · everything above is notes ===\n"
            "A perfectly clean cinematic description of a room, nothing else.\n"
            "=== ↑↑↑ PASTE STOPS HERE ↑↑↑ · everything below is notes ===\n"
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "clean.txt"
            p.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "prompt-lint.py"), str(p)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dirty_file_exits_nonzero(self):
        import subprocess
        import tempfile
        text = "⚠️ CTO note (CEO 2026-08-30): fix this before firing.\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "dirty.txt"
            p.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "prompt-lint.py"), str(p)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
