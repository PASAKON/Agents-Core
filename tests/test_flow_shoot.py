"""Tests for the zero-model Flow shot runner (task-6eabea66).

Covers everything a browser is NOT needed for: sheet parsing, the ledger's
idempotent init / atomic write / status transitions, credit-cap arithmetic,
refusal-card detection, zip-vs-bare-mp4 handling, and duration verification.
FlowBrowser (the only class that touches Playwright/CDP) is never
instantiated here — see its docstring in tools/flow_shoot.py.

Run via:  pytest tests/test_flow_shoot.py
(not in pytest.ini's default `testpaths` — run explicitly, same convention
as tests/test_multihost.py.)
"""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tools import flow_ledger, flow_shoot

FIXTURE_SHEET = Path(__file__).resolve().parent.parent / "docs" / "scripts" / "banchi-ACT2.md"

# REPORT-iter3 (task-04851451): a prior version of this suite wrote
# 'shot 35: submitted (attempt 1, est 4 credits)' straight into the REAL
# runner log — the CTO read that line as evidence a live fire had happened.
# _log() reads the module-global LOG_PATH fresh on every call, so
# redirecting it is enough; the two fixtures below are prevention
# (function-scoped, every test) and proof (session-scoped, the whole run).
REAL_LOG_PATH = Path(__file__).resolve().parent.parent / "state" / "banchi" / "flow_shoot.log"


@pytest.fixture(autouse=True)
def _redirect_log(tmp_path, monkeypatch):
    monkeypatch.setattr(flow_shoot, "LOG_PATH", tmp_path / "flow_shoot.log")


@pytest.fixture(scope="session", autouse=True)
def _real_log_untouched_by_this_suite():
    before = REAL_LOG_PATH.read_bytes() if REAL_LOG_PATH.exists() else None
    yield
    after = REAL_LOG_PATH.read_bytes() if REAL_LOG_PATH.exists() else None
    assert before == after, (
        f"a test in this suite wrote to the REAL runner log ({REAL_LOG_PATH}) "
        "instead of the redirected LOG_PATH — this is the exact bug "
        "REPORT-iter3 reports (a stray write there cost the CTO a wrong "
        "conclusion about a live fire)"
    )


# ── sheet parsing ────────────────────────────────────────────────────────────

def test_parse_sheet_reads_every_shot_in_the_fixture():
    shots = flow_ledger.parse_sheet(FIXTURE_SHEET)
    assert len(shots) == 24
    assert [s["shot"] for s in shots] == list(range(35, 59))


def test_parse_sheet_chips_are_in_attach_order():
    shots = {s["shot"]: s for s in flow_ledger.parse_sheet(FIXTURE_SHEET)}
    # SHOT 35 ATTACH line: 1) @nong_daeng 2) @lung_somchai 3) @noodle_shop
    assert shots[35]["chips"] == ["@nong_daeng", "@lung_somchai", "@noodle_shop"]
    # SHOT 58 has only two chips (character + location, no second character)
    assert shots[58]["chips"] == ["@nong_daeng", "@staircase"]


def test_parse_sheet_durations_match_shot_headers():
    shots = {s["shot"]: s for s in flow_ledger.parse_sheet(FIXTURE_SHEET)}
    assert shots[35]["dur_s"] == 6
    assert shots[40]["dur_s"] == 10
    assert shots[36]["dur_s"] == 8


def test_parse_sheet_prompt_block_is_verbatim():
    shots = {s["shot"]: s for s in flow_ledger.parse_sheet(FIXTURE_SHEET)}
    prompt = shots[35]["prompt"]
    assert prompt.startswith("Use <IMAGE_REF_0> as the character reference for nong_daeng.")
    assert prompt.rstrip().endswith(
        "Medium shot, static camera. Contemporary Thai realist drama, "
        "shot on 35mm, desaturated colour, natural light.")
    # the dialogue lines themselves must survive byte for byte
    assert '"ลูกชิ้นพิเศษโต๊ะห้า"' in prompt


def test_parse_sheet_act_from_filename():
    shots = flow_ledger.parse_sheet(FIXTURE_SHEET)
    assert all(s["act"] == "2" for s in shots)


def test_parse_sheet_no_shots_raises(tmp_path):
    empty = tmp_path / "banchi-ACT9.md"
    empty.write_text("# nothing here\n", encoding="utf-8")
    with pytest.raises(ValueError):
        flow_ledger.parse_sheet(empty)


# ── ledger: idempotent init, atomic write, status transitions ──────────────

def test_init_ledger_writes_one_row_per_shot(tmp_path):
    ledger = tmp_path / "ACT2.tsv"
    result = flow_ledger.init_ledger(FIXTURE_SHEET, ledger)
    assert result == {"total": 24, "existing": 0, "added": 24}
    rows = flow_ledger.load_ledger(ledger)
    assert len(rows) == 24
    assert rows[35]["status"] == "todo"
    assert rows[35]["chips"] == "@nong_daeng,@lung_somchai,@noodle_shop"
    assert rows[35]["dur_s"] == "6"


def test_init_ledger_is_idempotent_and_never_overwrites(tmp_path):
    ledger = tmp_path / "ACT2.tsv"
    flow_ledger.init_ledger(FIXTURE_SHEET, ledger)

    rows = flow_ledger.load_ledger(ledger)
    rows[35]["status"] = "verified"
    rows[35]["sha256"] = "deadbeef"
    flow_ledger.save_ledger(ledger, rows)

    result = flow_ledger.init_ledger(FIXTURE_SHEET, ledger)
    assert result == {"total": 24, "existing": 24, "added": 0}

    reloaded = flow_ledger.load_ledger(ledger)
    assert reloaded[35]["status"] == "verified"
    assert reloaded[35]["sha256"] == "deadbeef"
    assert len(reloaded) == 24


def test_init_ledger_appends_only_new_shots(tmp_path):
    ledger = tmp_path / "ACT2.tsv"
    all_shots = flow_ledger.parse_sheet(FIXTURE_SHEET)
    partial = {s["shot"]: {
        "shot": s["shot"], "act": s["act"], "dur_s": s["dur_s"],
        "chips": ",".join(s["chips"]), "prompt_sha": s["prompt_sha"],
        "status": "todo", "flow_clip_id": "", "file": "", "sha256": "",
        "got_dur": "", "attempts": "0", "note": "",
    } for s in all_shots if s["shot"] < 40}
    flow_ledger.save_ledger(ledger, partial)
    assert len(flow_ledger.load_ledger(ledger)) == 5  # 35..39

    result = flow_ledger.init_ledger(FIXTURE_SHEET, ledger)
    assert result == {"total": 24, "existing": 5, "added": 19}
    assert len(flow_ledger.load_ledger(ledger)) == 24


def test_save_ledger_is_atomic_no_tmp_file_left_behind(tmp_path):
    ledger = tmp_path / "ACT2.tsv"
    flow_ledger.init_ledger(FIXTURE_SHEET, ledger)
    tmp_marker = ledger.with_suffix(ledger.suffix + ".tmp")
    assert ledger.exists()
    assert not tmp_marker.exists()


def test_save_ledger_collapses_tabs_and_newlines_inside_fields(tmp_path):
    ledger = tmp_path / "safe.tsv"
    rows = {
        35: {
            "shot": 35, "act": 2, "dur_s": 6, "chips": "@a",
            "prompt_sha": "abc", "status": "refused", "flow_clip_id": "",
            "file": "", "sha256": "", "got_dur": "", "attempts": "2",
            "note": "ล้มเหลว\npolicy\tmessage",
        }
    }
    flow_ledger.save_ledger(ledger, rows)
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 2
    assert flow_ledger.load_ledger(ledger)[35]["note"] == (
        "ล้มเหลว policy message")


def test_status_summary_counts_and_next_todo(tmp_path):
    ledger = tmp_path / "ACT2.tsv"
    flow_ledger.init_ledger(FIXTURE_SHEET, ledger)
    rows = flow_ledger.load_ledger(ledger)
    rows[35]["status"] = "verified"
    rows[36]["status"] = "refused"
    flow_ledger.save_ledger(ledger, rows)

    summary = flow_ledger.status_summary(ledger)
    assert "verified" in summary and "1" in summary
    assert "refused" in summary
    assert "next todo: shot 37" in summary


def test_status_summary_missing_ledger(tmp_path):
    summary = flow_ledger.status_summary(tmp_path / "nope.tsv")
    assert "empty or not found" in summary


def test_all_statuses_are_the_documented_set():
    assert flow_ledger.STATUSES == {
        "todo", "submitted", "generated", "downloaded", "verified",
        "refused", "needs_model", "failed",
    }


# ── credit-cap arithmetic ────────────────────────────────────────────────────

@pytest.mark.parametrize("spent,estimate,cap,expected", [
    (0, 12, 300, False),
    (290, 12, 300, True),
    (288, 12, 300, False),  # exactly at cap is allowed
    (0, 301, 300, True),
    (0, 300, 300, False),
])
def test_credit_cap_exceeded(spent, estimate, cap, expected):
    assert flow_shoot.credit_cap_exceeded(spent, estimate, cap) is expected


def test_parse_credit_estimate_extracts_number():
    assert flow_shoot.parse_credit_estimate("การสร้างใช้ 20 เครดิต") == 20
    assert flow_shoot.parse_credit_estimate("ยอดคงเหลือ 9413 เครดิต ...") == 9413
    assert flow_shoot.parse_credit_estimate("no credits mentioned here") is None


def test_normalize_prompt_whitespace_collapses_newline_runs():
    # Confirmed live 2026-09-19: the composer's contenteditable box
    # re-normalizes blank-line count on round-trip (a single '\n' and a
    # blank-line '\n\n' both come back as some other run of newlines) while
    # every character of actual text survives — so the mismatch check must
    # compare on newline-collapsed text, not raw strings.
    single = "line one\nline two"
    blank = "line one\n\nline two"
    five = "line one\n\n\n\n\nline two"
    assert flow_shoot.normalize_prompt_whitespace(single) == "line one\nline two"
    assert flow_shoot.normalize_prompt_whitespace(blank) == "line one\nline two"
    assert flow_shoot.normalize_prompt_whitespace(five) == "line one\nline two"
    assert (flow_shoot.normalize_prompt_whitespace(single)
            == flow_shoot.normalize_prompt_whitespace(blank)
            == flow_shoot.normalize_prompt_whitespace(five))


def test_normalize_prompt_whitespace_still_catches_a_real_content_change():
    original = "says: \"เบาๆ... อย่าให้แม่ตื่น\""
    dropped_a_word = "says: \"เบาๆ... แม่ตื่น\""
    assert (flow_shoot.normalize_prompt_whitespace(original)
            != flow_shoot.normalize_prompt_whitespace(dropped_a_word))


def test_effective_duration_override_wins():
    assert flow_shoot.effective_duration(8, 4) == 4


def test_effective_duration_no_override_uses_sheet_duration():
    assert flow_shoot.effective_duration(8, None) == 8


def test_run_arg_parsing_defaults_generation_720p_and_download_1080p():
    ap = flow_shoot.build_parser()
    args = ap.parse_args(["run", "--sheet", "s.md", "--ledger", "l.tsv",
                           "--dest", "d", "--credit-cap", "10"])
    assert args.resolution == "720p"
    assert args.download_resolution == "1080p"
    assert args.force_duration is None


def test_run_arg_parsing_accepts_resolution_and_force_duration():
    ap = flow_shoot.build_parser()
    args = ap.parse_args(["run", "--sheet", "s.md", "--ledger", "l.tsv",
                           "--dest", "d", "--credit-cap", "10",
                           "--resolution", "360p", "--force-duration", "4"])
    assert args.resolution == "360p"
    assert args.force_duration == 4


def test_run_arg_parsing_rejects_unknown_resolution():
    ap = flow_shoot.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["run", "--sheet", "s.md", "--ledger", "l.tsv",
                        "--dest", "d", "--credit-cap", "10",
                        "--resolution", "1080p"])


def test_download_resolution_allows_only_free_upscale_or_legacy_720p():
    ap = flow_shoot.build_parser()
    args = ap.parse_args(["pull", "--sheet", "s.md", "--ledger", "l.tsv",
                          "--dest", "d", "--download-resolution", "720p"])
    assert args.download_resolution == "720p"
    with pytest.raises(SystemExit):
        ap.parse_args(["pull", "--sheet", "s.md", "--ledger", "l.tsv",
                       "--dest", "d", "--download-resolution", "4K"])


def test_validate_download_option_accepts_free_1080p_and_rejects_paid_4k():
    flow_shoot.validate_download_option(
        "1080p\nเพิ่มความละเอียดแล้ว", "1080p")
    with pytest.raises((ValueError, RuntimeError)):
        flow_shoot.validate_download_option(
            "4K\nเพิ่มความละเอียดแล้ว · 50 เครดิต", "4K")
    with pytest.raises(RuntimeError, match="credit-bearing"):
        flow_shoot.validate_download_option(
            "1080p\nเพิ่มความละเอียดแล้ว · 50 เครดิต", "1080p")


def test_parse_only_ranges_and_lists():
    assert flow_shoot.parse_only("37-46") == set(range(37, 47))
    assert flow_shoot.parse_only("37,40,52") == {37, 40, 52}
    assert flow_shoot.parse_only("37-39,52") == {37, 38, 39, 52}
    assert flow_shoot.parse_only("5") == {5}


# ── refusal-card detection ───────────────────────────────────────────────────

REFUSAL_CARD = (
    "ล้มเหลว\n"
    "การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่นหรือส่งความคิดเห็น\n"
    "ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้"
)
GENERIC_FAILURE_CARD = (
    "ล้มเหลว\n"
    "ขออภัย สร้างวิดีโอนี้ไม่สำเร็จ\n"
    "ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้"
)


def test_is_refusal_text_detects_policy_refusal():
    assert flow_shoot.is_refusal_text(REFUSAL_CARD) is True


def test_is_refusal_text_detects_generic_failure_by_prefix():
    assert flow_shoot.is_refusal_text(GENERIC_FAILURE_CARD) is True


def test_is_refusal_text_false_for_a_normal_success_page():
    assert flow_shoot.is_refusal_text("วิดีโอของคุณพร้อมแล้ว ดาวน์โหลด") is False


def test_is_refusal_text_false_for_empty_or_none():
    assert flow_shoot.is_refusal_text("") is False
    assert flow_shoot.is_refusal_text(None) is False


def test_first_dialogue_line_extracts_the_thai_quote():
    prompt = flow_ledger.parse_sheet(FIXTURE_SHEET)[0]["prompt"]
    line = flow_shoot.first_dialogue_line(prompt)
    assert line == "ลูกชิ้นพิเศษโต๊ะห้า"


def test_first_dialogue_line_none_when_no_dialogue():
    assert flow_shoot.first_dialogue_line("no dialogue markers here") is None


# ── settings dict: read_settings reads resolution back like every other
#    setting. Live 2026-09-19: every mat-button-toggle LABEL (720p, 360p,
#    x1..x4, every duration, every aspect) is always rendered regardless of
#    which is selected — only the wrapper's mat-button-toggle-checked class
#    says which one is active. These fakes model exactly that, so a test
#    that only fakes "label present in text" (the old, wrong assumption)
#    can't accidentally pass again. ────────────────────────────────────────

ALL_TOGGLE_LABELS = {
    "360p", "720p", "4 วินาที", "6 วินาที", "8 วินาที", "10 วินาที",
    "9:16", "16:9", "องค์ประกอบ", "เฟรม", "x1", "x2", "x3", "x4",
}


class _FakeToggleLocator:
    def __init__(self, present: bool, checked: bool):
        self._present = present
        self._checked = checked

    @property
    def first(self):
        return self

    def count(self) -> int:
        return 1 if self._present else 0

    def get_attribute(self, _name: str) -> str:
        return "mat-button-toggle-checked" if self._checked else "mat-button-toggle"


class _FakePanel:
    """Stands in for the <flow-prompt-box-settings> overlay locator."""

    def __init__(self, checked_labels: set[str], known_labels=ALL_TOGGLE_LABELS,
                 inner_text: str = ""):
        self._checked_labels = checked_labels
        self._known_labels = known_labels
        self._inner_text = inner_text

    def count(self) -> int:
        return 1

    def evaluate(self, _script: str) -> str:
        return self._inner_text

    def locator(self, _selector: str) -> "_FakePanel":
        return self

    def filter(self, has_text: str) -> _FakeToggleLocator:
        present = any(has_text in label for label in self._known_labels)
        checked = any(has_text in label for label in self._checked_labels)
        return _FakeToggleLocator(present, checked)


class _MissingPanel:
    def count(self) -> int:
        return 0


class _FakePage:
    def __init__(self, panel=None, body: str = ""):
        self._panel = panel
        self._body = body

    def locator(self, selector: str):
        assert selector == "flow-prompt-box-settings"
        return self._panel if self._panel is not None else _MissingPanel()

    def evaluate(self, _script: str) -> str:
        return self._body


def test_read_settings_confirms_matching_resolution_and_duration():
    panel = _FakePanel(
        checked_labels={"360p", "4 วินาที", "9:16", "องค์ประกอบ", "x1"},
        inner_text="Omni 1.1 Flash",
    )
    browser = flow_shoot.FlowBrowser()
    browser.page = _FakePage(panel=panel)
    settings = browser.read_settings(dur_s=4, resolution="360p")
    assert settings == {
        "model_omni": True,
        "mode_ingredients": True,
        "aspect_9_16": True,
        "qty_x1": True,
        "resolution": True,
        "duration": True,
    }


def test_read_settings_flags_resolution_mismatch():
    # panel shows the account default 720p checked — the 360p click didn't take.
    panel = _FakePanel(
        checked_labels={"720p", "4 วินาที", "9:16", "องค์ประกอบ", "x1"},
        inner_text="Omni 1.1 Flash",
    )
    browser = flow_shoot.FlowBrowser()
    browser.page = _FakePage(panel=panel)
    settings = browser.read_settings(dur_s=4, resolution="360p")
    assert settings["resolution"] is False


def test_read_settings_ignores_unselected_labels_that_are_merely_present():
    # 720p, 360p, x2, x3, x4, every OTHER duration/aspect are all always
    # rendered in the panel regardless of selection — presence alone must
    # not read back as "confirmed".
    panel = _FakePanel(
        checked_labels={"360p", "4 วินาที", "9:16", "องค์ประกอบ", "x1"},
        inner_text="Omni 1.1 Flash",
    )
    browser = flow_shoot.FlowBrowser()
    browser.page = _FakePage(panel=panel)
    settings = browser.read_settings(dur_s=8, resolution="720p")  # neither is checked
    assert settings["resolution"] is False
    assert settings["duration"] is False


def test_read_settings_defaults_resolution_to_720p():
    panel = _FakePanel(
        checked_labels={"720p", "8 วินาที", "9:16", "องค์ประกอบ", "x1"},
        inner_text="Omni 1.1 Flash",
    )
    browser = flow_shoot.FlowBrowser()
    browser.page = _FakePage(panel=panel)
    settings = browser.read_settings(dur_s=8)  # resolution omitted -> default "720p"
    assert settings["resolution"] is True


def test_read_settings_falls_back_to_collapsed_pill_text_when_panel_is_closed():
    # set_settings closes the panel before returning; a caller reading
    # settings afterwards only has the collapsed pill's flattened text.
    browser = flow_shoot.FlowBrowser()
    browser.page = _FakePage(body="Agent   วิดีโอ · 720p · 8 วินาที · 9:16 · x1")
    settings = browser.read_settings(dur_s=8, resolution="720p")
    assert settings["resolution"] is True
    assert settings["duration"] is True
    assert settings["model_omni"] is False  # "Omni 1.1 Flash" not in this fixture


# ── zip-vs-mp4 handling ──────────────────────────────────────────────────────

def _make_clip(path: Path, duration: float, silent: bool) -> None:
    audio = "anullsrc=r=8000:cl=mono" if silent else "sine=frequency=440:sample_rate=8000"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"color=c=black:s=64x64:d={duration}",
         "-f", "lavfi", "-i", f"{audio}",
         "-t", str(duration), "-c:v", "libx264", "-c:a", "aac", str(path)],
        check=True, capture_output=True,
    )


def test_extract_clip_from_zip_with_one_mp4(tmp_path):
    mp4 = tmp_path / "raw.mp4"
    _make_clip(mp4, duration=2.0, silent=False)
    zpath = tmp_path / "ดาวน์โหลด (1).zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(mp4, arcname="Some_generated_name_20260919.mp4")

    dest_dir = tmp_path / "dest"
    result = flow_shoot.extract_clip(zpath, dest_dir, 42)
    assert result == dest_dir / "shot-42.mp4"
    assert result.exists() and result.stat().st_size > 0


def test_extract_clip_from_zip_with_wrong_count_raises(tmp_path):
    zpath = tmp_path / "bad.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("a.mp4", b"x")
        zf.writestr("b.mp4", b"y")
    with pytest.raises(ValueError):
        flow_shoot.extract_clip(zpath, tmp_path / "dest", 1)


def test_extract_clip_bare_mp4_is_copied_and_renamed(tmp_path):
    mp4 = tmp_path / "Man_talking_20260919141229.mp4"
    _make_clip(mp4, duration=1.5, silent=True)
    dest_dir = tmp_path / "dest"
    result = flow_shoot.extract_clip(mp4, dest_dir, 7)
    assert result == dest_dir / "shot-07.mp4"
    assert result.exists()


def test_extract_clip_unknown_extension_raises(tmp_path):
    junk = tmp_path / "whatever.txt"
    junk.write_text("not a clip")
    with pytest.raises(ValueError):
        flow_shoot.extract_clip(junk, tmp_path / "dest", 1)


# ── duration / audio verification ───────────────────────────────────────────

def test_verify_clip_passes_within_tolerance(tmp_path):
    clip = tmp_path / "shot-01.mp4"
    _make_clip(clip, duration=6.0, silent=False)
    ok, reason = flow_shoot.verify_clip(clip, expected_dur=6)
    assert ok is True
    assert "6.0" in reason or "6." in reason


def test_verify_clip_within_the_0_6s_tolerance_edge(tmp_path):
    clip = tmp_path / "shot-01.mp4"
    _make_clip(clip, duration=6.5, silent=False)  # 0.5s off a 6s target
    ok, _ = flow_shoot.verify_clip(clip, expected_dur=6)
    assert ok is True


def test_verify_clip_fails_outside_tolerance(tmp_path):
    clip = tmp_path / "shot-01.mp4"
    _make_clip(clip, duration=4.0, silent=False)
    ok, reason = flow_shoot.verify_clip(clip, expected_dur=8)
    assert ok is False
    assert "DURATION" in reason


def test_verify_clip_fails_on_silence(tmp_path):
    clip = tmp_path / "shot-01.mp4"
    _make_clip(clip, duration=4.0, silent=True)
    ok, reason = flow_shoot.verify_clip(clip, expected_dur=4)
    assert ok is False
    assert reason == "NO AUDIO"


def test_verify_clip_checks_requested_upscale_resolution(tmp_path, monkeypatch):
    clip = tmp_path / "shot-01.mp4"
    _make_clip(clip, duration=4.0, silent=False)
    monkeypatch.setattr(flow_shoot, "probe_video_dimensions",
                        lambda _path: (1080, 1920))
    ok, reason = flow_shoot.verify_clip(
        clip, expected_dur=4, expected_resolution="1080p")
    assert ok is True
    assert "1080x1920" in reason

    monkeypatch.setattr(flow_shoot, "probe_video_dimensions",
                        lambda _path: (720, 1280))
    ok, reason = flow_shoot.verify_clip(
        clip, expected_dur=4, expected_resolution="1080p")
    assert ok is False
    assert reason == "RESOLUTION got 720x1280 want 1080x1920"


def test_verify_clip_missing_file():
    ok, reason = flow_shoot.verify_clip(Path("/does/not/exist.mp4"), expected_dur=6)
    assert ok is False
    assert reason == "file missing"


def test_verify_clip_tolerance_uses_force_duration_override_not_sheet_dur(tmp_path):
    # Sheet says this shot is 8s; --force-duration 4 (the proof-shot flag)
    # renders it at 4s. verify_clip must be checked against the override,
    # not the sheet's original duration, or a correctly-rendered proof clip
    # would fail its own verification.
    clip = tmp_path / "shot-03.mp4"
    _make_clip(clip, duration=4.0, silent=False)
    sheet_dur_s, force_duration = 8, 4

    overridden = flow_shoot.effective_duration(sheet_dur_s, force_duration)
    ok, reason = flow_shoot.verify_clip(clip, expected_dur=overridden)
    assert ok is True

    # Without the override (i.e. checked against the sheet's own duration)
    # the same clip correctly fails — proving the override is load-bearing.
    ok_unoverridden, reason_unoverridden = flow_shoot.verify_clip(clip, expected_dur=sheet_dur_s)
    assert ok_unoverridden is False
    assert "DURATION" in reason_unoverridden


def test_sha256_file_is_stable(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"same bytes")
    assert flow_shoot.sha256_file(f) == flow_shoot.sha256_file(f)
    g = tmp_path / "b.bin"
    g.write_bytes(b"different bytes")
    assert flow_shoot.sha256_file(f) != flow_shoot.sha256_file(g)


# ── check_replay_script.py gate (the thing that actually blocks merge) ──────

def test_check_replay_script_accepts_flow_shoot():
    env = os.environ.copy()
    git_bash_bin = Path(r"C:\Program Files\Git\bin")
    if git_bash_bin.exists():
        env["PATH"] = str(git_bash_bin) + os.pathsep + env.get("PATH", "")
    r = subprocess.run(
        [sys.executable, "tools/check_replay_script.py", "tools/flow_shoot.py",
         "tools/flow_ledger.py", "scripts/flow/launch-chrome-debug.sh"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stdout + r.stderr


# ── chip-count hard gate (CTO, 19 Sep, task-a09ed18a): a shot must never
#    reach Submit unless the LIVE chip count exactly matches what the shot
#    needs. Found live: attach_chip(@staircase) logged a timeout, yet the
#    run still reached "submitted" a second later — _attempt_chip's
#    per-handle "count increased from before" check is not proof the RIGHT
#    total ended up attached. These exercise cmd_run's real control flow
#    against a stub FlowBrowser (injected via the new browser_factory
#    param) rather than a pure helper, because what must be proven is that
#    submit() itself is never called, not just that some boolean is False. ─

class _GateStubBrowser:
    """chip_count() plays back a scripted sequence of return values, one
    per call, decoupled from attach_chip() — this is what lets a test
    reproduce the live bug exactly: every per-handle
    "count increased since before" check in _attempt_chip can pass while
    the TOTAL the hard gate re-reads afterwards still does not match what
    the shot needs (a transient over-count during polling that reverts by
    the time of the final authoritative read)."""

    def __init__(self, chip_count_sequence: list[int]):
        self._seq = list(chip_count_sequence)
        self._idx = 0
        self._pasted = ""
        self.submit_called = False
        self.download_called = False

    def attach(self) -> None:
        pass

    def mute_all_media(self) -> None:
        pass

    def reset_composer(self) -> None:
        pass

    def close(self) -> None:
        pass

    def set_settings(self, dur_s, resolution="720p") -> dict:
        return {"model_omni": True, "mode_ingredients": True, "aspect_9_16": True,
                "qty_x1": True, "resolution": True, "duration": True}

    def chip_count(self) -> int:
        val = self._seq[min(self._idx, len(self._seq) - 1)]
        self._idx += 1
        return val

    def attach_chip(self, _handle: str) -> bool:
        return True  # the click itself "succeeds" from attach_chip's own POV

    def paste_prompt(self, text: str) -> None:
        self._pasted = text

    def read_prompt_text(self) -> str:
        return self._pasted

    def read_credit_estimate(self) -> int:
        return 4

    def submit(self, expected_chip_count: int | None = None) -> None:
        self.submit_called = True

    def poll_result(self, timeout_s: int = 0) -> dict:
        return {"status": "refusal", "text": "ล้มเหลว (stub, positive-control test)"}

    def download(self):
        self.download_called = True
        raise AssertionError("download() must never be reached in this test")


def _run_args(tmp_path: Path, ledger_name: str) -> object:
    ap = flow_shoot.build_parser()
    return ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET),
        "--ledger", str(tmp_path / ledger_name),
        "--dest", str(tmp_path / "dest"),
        "--credit-cap", "999", "--only", "35",
    ])


def test_chip_count_mismatch_blocks_submit(tmp_path):
    # Shot 35 needs 3 chips. Each per-handle attach appears to succeed
    # (chip_count keeps rising across the 3 attempts, briefly touching 3),
    # but the hard gate's own re-read afterwards sees only 2 — must refuse
    # to proceed, and submit() must never be called.
    args = _run_args(tmp_path, "gate_mismatch.tsv")
    stub = _GateStubBrowser(chip_count_sequence=[0, 1, 1, 2, 2, 3, 2])
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False
    assert stub.download_called is False
    rows = flow_ledger.load_ledger(tmp_path / "gate_mismatch.tsv")
    assert rows[35]["status"] == "needs_model"
    assert "chip count mismatch" in rows[35]["note"]
    assert rc == 1  # this row left "todo" without reaching "verified"


def test_chip_count_match_reaches_submit(tmp_path):
    # Positive control: when the final re-read DOES match, the gate must
    # not false-block a correct attach — the run proceeds to Submit.
    args = _run_args(tmp_path, "gate_match.tsv")
    stub = _GateStubBrowser(chip_count_sequence=[0, 1, 1, 2, 2, 3, 3])
    flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is True
    rows = flow_ledger.load_ledger(tmp_path / "gate_match.tsv")
    assert rows[35]["status"] == "refused"  # stub's poll_result() always refuses
    assert rows[35]["note"] == "ล้มเหลว (stub, positive-control test)"


# ── money guards (task-04851451, REPORT-iter3): the CEO counted 16 real
#    generations fired against a runner whose --dry-run and --credit-cap 0
#    both looked correct by control flow alone — iteration 2's own report
#    shows the cap check and the dry-run check sitting right where they
#    should, immediately before the one browser.submit() call, and still 15
#    of those 16 fires happened. "The control flow doesn't call submit()"
#    is not good enough; these prove submit() itself refuses. ──────────────

def test_flowbrowser_submit_raises_when_dry_run_is_set():
    # Unit test on the REAL class, not a stub — this is what "structurally
    # incapable" means: even with no cmd_run control flow involved at all,
    # calling submit() on a dry-run browser must refuse.
    browser = flow_shoot.FlowBrowser()
    browser.dry_run = True
    with pytest.raises(RuntimeError):
        browser.submit()


class _DryRunAwareStubBrowser:
    """Mirrors FlowBrowser's own dry_run guard on submit() exactly (not
    just recording a call), so a test using this stub proves BOTH that
    cmd_run's control flow never reaches submit() under --dry-run AND that
    if it somehow did, submit() itself would raise — "the raise path is
    reachable", not merely untested."""

    def __init__(self, chip_count_value: int):
        self._chip_count = chip_count_value
        self.dry_run = False
        self.submit_called = False
        self._pasted = ""

    def reset_composer(self) -> None:
        # interface parity with FlowBrowser (branch merge 2026-09-23); no-op in a stub
        pass

    def attach(self) -> None:
        pass

    def mute_all_media(self) -> None:
        pass

    def close(self) -> None:
        pass

    def set_settings(self, dur_s, resolution="720p") -> dict:
        return {"model_omni": True, "mode_ingredients": True, "aspect_9_16": True,
                "qty_x1": True, "resolution": True, "duration": True}

    def chip_count(self) -> int:
        return self._chip_count

    def attach_chip(self, _handle: str) -> bool:
        return True

    def paste_prompt(self, text: str) -> None:
        self._pasted = text

    def read_prompt_text(self) -> str:
        return self._pasted

    def read_credit_estimate(self) -> int:
        return 4

    def submit(self, expected_chip_count: int | None = None) -> None:
        if self.dry_run:
            raise RuntimeError("BUG: submit() called while dry_run is set")
        self.submit_called = True

    def poll_result(self, timeout_s: int = 0) -> dict:
        raise AssertionError("poll_result() must never be reached under --dry-run")

    def download(self):
        raise AssertionError("download() must never be reached under --dry-run")


def _dry_run_args(tmp_path: Path, ledger_name: str, cap: int = 999) -> object:
    ap = flow_shoot.build_parser()
    return ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET),
        "--ledger", str(tmp_path / ledger_name),
        "--dest", str(tmp_path / "dest"),
        "--credit-cap", str(cap), "--only", "35", "--dry-run",
    ])


def test_dry_run_cmd_run_never_calls_submit_and_raise_path_is_reachable(tmp_path):
    args = _dry_run_args(tmp_path, "dry.tsv")
    stub = _DryRunAwareStubBrowser(chip_count_value=3)  # shot 35 needs 3 chips
    flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False
    assert stub.dry_run is True  # cmd_run set this on the browser right after construction
    # The raise path is reachable, not just untested: calling submit()
    # directly, now, raises — proving it isn't "never called" by accident.
    with pytest.raises(RuntimeError):
        stub.submit()


def test_dry_run_and_credit_cap_zero_together_still_never_submit(tmp_path):
    # The exact combination REPORT-iter2 ran repeatedly while fixing
    # selectors: `--only 3 --credit-cap 0 --dry-run`. Both guards must hold
    # together, not just individually.
    args = _dry_run_args(tmp_path, "both.tsv", cap=0)
    stub = _DryRunAwareStubBrowser(chip_count_value=3)
    flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False


def _cap_args(tmp_path: Path, ledger_name: str, cap: int, only: str = "35") -> object:
    ap = flow_shoot.build_parser()
    return ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET),
        "--ledger", str(tmp_path / ledger_name),
        "--dest", str(tmp_path / "dest"),
        "--credit-cap", str(cap), "--only", only,
    ])


def test_credit_cap_zero_blocks_submit_on_a_perfectly_matching_attach(tmp_path):
    # Not a dry run — chips match, prompt matches, estimate reads fine.
    # cap=0 alone must be the thing that stops it.
    args = _cap_args(tmp_path, "cap0.tsv", cap=0)
    stub = _GateStubBrowser(chip_count_sequence=[0, 1, 1, 2, 2, 3, 3])
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False
    assert stub.download_called is False
    rows = flow_ledger.load_ledger(tmp_path / "cap0.tsv")
    # The normal (non-exception) cap-reached path just logs CAP REACHED and
    # breaks — it never touches the row, so it stays exactly "todo", never
    # attempted, same as REPORT-iter2's confirmed live behaviour.
    assert rows[35]["status"] == "todo"
    assert rc == 0  # nothing was "attempted" (still todo), so nothing to fail either


class _EstimateUnreadableStubBrowser:
    """chip attach succeeds cleanly; read_credit_estimate() always raises
    EstimateUnreadable, exactly as FlowBrowser does when the live panel's
    credit text can't be parsed. set_settings_calls proves whether a LATER
    shot was ever even started."""

    def __init__(self):
        self._count = 0  # rises by one per attach_chip() call, like the real gate expects
        self.dry_run = False
        self.submit_called = False
        self.set_settings_calls = 0
        self._pasted = ""

    def reset_composer(self) -> None:
        # interface parity with FlowBrowser (branch merge 2026-09-23); no-op in a stub
        pass

    def attach(self) -> None:
        pass

    def mute_all_media(self) -> None:
        pass

    def close(self) -> None:
        pass

    def set_settings(self, dur_s, resolution="720p") -> dict:
        self.set_settings_calls += 1
        return {"model_omni": True, "mode_ingredients": True, "aspect_9_16": True,
                "qty_x1": True, "resolution": True, "duration": True}

    def chip_count(self) -> int:
        return self._count

    def attach_chip(self, _handle: str) -> bool:
        self._count += 1
        return True

    def paste_prompt(self, text: str) -> None:
        self._pasted = text

    def read_prompt_text(self) -> str:
        return self._pasted

    def read_credit_estimate(self) -> int:
        raise flow_shoot.EstimateUnreadable(
            "panel text unreadable, stub reproducing the live failure mode")

    def submit(self, expected_chip_count: int | None = None) -> None:
        self.submit_called = True

    def poll_result(self, timeout_s: int = 0) -> dict:
        raise AssertionError("poll_result() must never be reached")

    def download(self):
        raise AssertionError("download() must never be reached")


def test_credit_cap_zero_blocks_submit_even_when_estimate_read_fails(tmp_path):
    args = _cap_args(tmp_path, "cap0_unreadable.tsv", cap=0)
    stub = _EstimateUnreadableStubBrowser()
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False
    rows = flow_ledger.load_ledger(tmp_path / "cap0_unreadable.tsv")
    assert rows[35]["status"] == "failed"
    assert "estimate unreadable" in rows[35]["note"]
    assert rc == 1


def test_estimate_unreadable_stops_the_whole_run_not_just_this_shot(tmp_path):
    # Two shots requested. Shot 35's estimate read fails. Shot 36 must
    # never even be STARTED — not "started and correctly refused to spend",
    # not started at all. set_settings_calls == 1 is the proof: it's the
    # first browser call of every shot's iteration.
    args = _cap_args(tmp_path, "unreadable_stop.tsv", cap=999, only="35,36")
    stub = _EstimateUnreadableStubBrowser()
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False
    assert stub.set_settings_calls == 1
    rows = flow_ledger.load_ledger(tmp_path / "unreadable_stop.tsv")
    assert rows[35]["status"] == "failed"
    assert "estimate unreadable" in rows[35]["note"]
    assert rows[36]["status"] == "todo"  # never touched
    assert rc == 1


def test_flowbrowser_read_credit_estimate_raises_the_specific_type():
    # parse_credit_estimate() itself already has coverage above (returns
    # None on unparseable text); this proves read_credit_estimate() turns
    # that into EstimateUnreadable specifically, not a bare RuntimeError —
    # cmd_run's except clause ordering depends on the type, not the message.
    browser = flow_shoot.FlowBrowser()

    class _NoEstimatePanel:
        def count(self):
            return 1

        def evaluate(self, _script):
            return "no credit text in here at all"

    class _FakePageNoEstimate:
        def locator(self, selector):
            assert selector == "flow-prompt-box-settings"
            return _NoEstimatePanel()

        def evaluate(self, _script):
            return ""

        @property
        def keyboard(self):
            class _KB:
                def press(self, *_a, **_kw):
                    pass
            return _KB()

        def wait_for_timeout(self, _ms):
            pass

    browser.page = _FakePageNoEstimate()
    with pytest.raises(flow_shoot.EstimateUnreadable):
        browser.read_credit_estimate()


# ── chip-count guard, made structural (task-04851451, incident 2, 2026-09-19
#    20:05): a proof-shot run logged attach_chip() TimeoutErrors for BOTH
#    handles of shot 3 and still reached "submitted" a second later. A
#    read-only pull of the actual clip afterward (frame 0, visually
#    inspected) showed both references — @lung_somchai's face/wardrobe and
#    @staircase's location — HAD rendered correctly: attach_chip()'s own
#    return value is decoupled from reality by design (chip_count() is the
#    ground truth _attempt_chip polls, not that boolean; see the class
#    docstring on _GateStubBrowser above), and this run's real live chip
#    count genuinely was 2-of-2 by the time the pre-existing hard gate
#    checked it — the existing test_chip_count_mismatch_blocks_submit
#    already proves that gate refuses a genuine mismatch. What this section
#    adds is the CTO's explicit ask: make the same check unavoidable
#    INSIDE submit() itself, not only in the caller, and reproduce the
#    exact "zero chips" framing end to end. ──────────────────────────────

def test_flowbrowser_submit_raises_chip_count_mismatch():
    # Unit test on the REAL class: even with no cmd_run control flow
    # involved, handing submit() an expected count that doesn't match the
    # live DOM read must refuse.
    browser = flow_shoot.FlowBrowser()

    class _FakeChipLocator:
        def count(self):
            return 0  # live DOM says zero chips attached

    class _FakePage:
        def locator(self, selector):
            assert selector == "flow-ingredient-bar flow-ingredient-chip"
            return _FakeChipLocator()

    browser.page = _FakePage()
    with pytest.raises(flow_shoot.ChipCountMismatch) as exc_info:
        browser.submit(expected_chip_count=2)
    assert exc_info.value.expected == 2
    assert exc_info.value.actual == 0


def test_flowbrowser_submit_with_matching_chip_count_does_not_raise():
    # Positive control: submit() must not false-block a genuine match —
    # this is what the pulled shot-3 clip actually was (2-of-2, visually
    # confirmed), so the guard must let that case through.
    browser = flow_shoot.FlowBrowser()

    class _FakeChipLocator:
        def count(self):
            return 2

    class _FakePage:
        def locator(self, selector):
            return _FakeChipLocator()

        def evaluate(self, _script):
            return None

    class _FakeButtonLocator:
        @property
        def first(self):
            return self

        def click(self):
            pass

    page = _FakePage()
    page.locator = lambda selector: (
        _FakeButtonLocator() if selector.startswith('button[aria-label')
        else _FakeChipLocator())
    browser.page = page
    browser.submit(expected_chip_count=2)  # must not raise


class _ZeroChipsStubBrowser:
    """Reproduces CTO's exact framing of the 20:05 incident, as read from
    the log alone (before the actual clip was pulled and visually
    inspected): attach_chip() reports failure for EVERY handle and
    chip_count() never leaves zero. submit() also carries the real
    class's expected_chip_count guard, so a run against this stub proves
    both layers hold in the literal worst case named."""

    def __init__(self):
        self.dry_run = False
        self.submit_called = False
        self._pasted = ""

    def reset_composer(self) -> None:
        # interface parity with FlowBrowser (branch merge 2026-09-23); no-op in a stub
        pass

    def attach(self) -> None:
        pass

    def mute_all_media(self) -> None:
        pass

    def close(self) -> None:
        pass

    def set_settings(self, dur_s, resolution="720p") -> dict:
        return {"model_omni": True, "mode_ingredients": True, "aspect_9_16": True,
                "qty_x1": True, "resolution": True, "duration": True}

    def chip_count(self) -> int:
        return 0

    def attach_chip(self, _handle: str) -> bool:
        return False

    def paste_prompt(self, text: str) -> None:
        self._pasted = text

    def read_prompt_text(self) -> str:
        return self._pasted

    def read_credit_estimate(self) -> int:
        return 4

    def submit(self, expected_chip_count: int | None = None) -> None:
        if expected_chip_count is not None and self.chip_count() != expected_chip_count:
            raise flow_shoot.ChipCountMismatch(expected_chip_count, self.chip_count())
        self.submit_called = True

    def poll_result(self, timeout_s: int = 0) -> dict:
        raise AssertionError("poll_result() must never be reached")

    def download(self):
        raise AssertionError("download() must never be reached")


def test_zero_chips_attached_never_reaches_submit(tmp_path):
    args = _cap_args(tmp_path, "zero_chips.tsv", cap=999)
    stub = _ZeroChipsStubBrowser()
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False
    rows = flow_ledger.load_ledger(tmp_path / "zero_chips.tsv")
    assert rows[35]["status"] == "needs_model"
    assert "chip never attached" in rows[35]["note"]
    assert rc == 1


# ── decide()-backed poll_result (task-b8a9a714): the old full-body
#    is_refusal_text() scan is replaced by decide('browser.page_state',
#    extract_state(page)) each cycle. These exercise the REAL FlowBrowser.
#    poll_result() against a fake page (no browser, no network — rules
#    provider only, same env-stripping convention as tests/test_decide.py). ─

from lib import decision_ledger  # noqa: E402


@pytest.fixture(autouse=True)
def _redirect_decision_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(decision_ledger, "LEDGER_DIR", tmp_path / "decisions")


@pytest.fixture(autouse=True)
def _clean_decide_env(monkeypatch):
    for var in ("DECIDE_PROVIDER", "OPENROUTER_API_KEY", "DECIDE_BUDGET_USD",
                "JEV_API_KEY", "JEV_API_URL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _no_real_sleep_in_poll(monkeypatch):
    # poll_result()'s inner loop sleeps POLL_S (8s) every cycle — make this
    # whole suite instant without touching the real timeout arithmetic.
    monkeypatch.setattr(flow_shoot.time, "sleep", lambda _s: None)


class _StatePage:
    """Feeds a fixed state string to extract_state() via its EXTRACT_STATE_JS
    call; every other evaluate() call (the mute/nudge-play snippet
    poll_result() issues each cycle) is a no-op."""

    def __init__(self, state_text: str):
        self.state_text = state_text

    def evaluate(self, script):
        if script == flow_shoot.EXTRACT_STATE_JS:
            return self.state_text
        return None


def test_poll_result_flow_refusal_card_returns_refusal_with_rewrite_dialogue():
    browser = flow_shoot.FlowBrowser()
    browser.page = _StatePage(REFUSAL_CARD)
    result = browser.poll_result(timeout_s=5)
    assert result["status"] == "refusal"
    assert result["moderation_choice"] == "rewrite_dialogue"


def test_poll_result_face_ip_scanner_text_escalates():
    browser = flow_shoot.FlowBrowser()
    browser.page = _StatePage("Face/IP scanner flagged this clip for resemblance")
    result = browser.poll_result(timeout_s=5)
    assert result["status"] == "refusal"
    assert result["moderation_choice"] == "escalate_ceo"


def test_poll_result_signed_out_text_stops():
    browser = flow_shoot.FlowBrowser()
    browser.page = _StatePage("Sign in")
    result = browser.poll_result(timeout_s=5)
    assert result == {"status": "stopped", "text": "Sign in", "reason": "signed_out"}


def test_poll_result_error_text_stops():
    browser = flow_shoot.FlowBrowser()
    browser.page = _StatePage("something went wrong")
    result = browser.poll_result(timeout_s=5)
    assert result["status"] == "stopped"
    assert result["reason"] == "error"


def test_poll_result_generating_text_keeps_polling_to_timeout():
    # A confident-but-benign classification (generating) must NOT stop the
    # loop early — only moderated/signed_out/error short-circuit the wait.
    browser = flow_shoot.FlowBrowser()
    browser.page = _StatePage('button="เริ่มสร้าง" disabled=true | generating')
    result = browser.poll_result(timeout_s=0.001)
    assert result == {"status": "timeout", "text": ""}


def test_poll_result_unknown_text_keeps_polling_to_timeout():
    # No confident rule match at all (choice=None) is treated the same as
    # "keep waiting", not "stop" — stopping is reserved for a CONFIDENT
    # signed_out/error/moderated read, per the conservative action-mapping
    # gate (never guess a healthy run into stopping early).
    browser = flow_shoot.FlowBrowser()
    browser.page = _StatePage("nothing recognizable here")
    result = browser.poll_result(timeout_s=0.001)
    assert result == {"status": "timeout", "text": ""}


class _DownloadArrivesMidPollPage:
    """Simulates the CDN response arriving between two poll cycles — the
    captured-URL check runs first every iteration, so this proves decide()
    never blocks or delays the real completion signal."""

    def __init__(self, urls_list):
        self._urls = urls_list
        self._armed = False

    def evaluate(self, script):
        if script == flow_shoot.EXTRACT_STATE_JS:
            if not self._armed:
                self._armed = True
                self._urls.append("https://flow-content.google/video/captured")
            return "generating"
        return None


def test_poll_result_download_wins_once_url_is_captured_mid_poll():
    browser = flow_shoot.FlowBrowser()
    browser.page = _DownloadArrivesMidPollPage(browser._captured_video_urls)
    result = browser.poll_result(timeout_s=5)
    assert result == {"status": "download", "text": ""}


# ── cmd_run's hazard handling: stop the whole run / escalate, never guess ──

class _StoppedPollStubBrowser(_GateStubBrowser):
    def poll_result(self, timeout_s: int = 0) -> dict:
        return {"status": "stopped", "text": "Sign in", "reason": "signed_out"}


def test_stopped_page_state_halts_the_whole_run_not_just_this_shot(tmp_path):
    args = _cap_args(tmp_path, "stopped.tsv", cap=999, only="35,36")
    stub = _StoppedPollStubBrowser(chip_count_sequence=[0, 1, 1, 2, 2, 3, 3])
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is True  # submit already happened before the poll observed the hazard
    rows = flow_ledger.load_ledger(tmp_path / "stopped.tsv")
    assert rows[35]["status"] == "failed"
    assert "signed_out" in rows[35]["note"]
    assert rows[36]["status"] == "todo"  # never even started — the run halted
    assert rc == 1


class _EscalateCeoStubBrowser(_GateStubBrowser):
    def poll_result(self, timeout_s: int = 0) -> dict:
        return {"status": "refusal", "text": "Rights verification required",
                "moderation_choice": "escalate_ceo"}


def test_escalate_ceo_exits_the_runner_and_never_re_fires(tmp_path):
    args = _cap_args(tmp_path, "escalate.tsv", cap=999)
    stub = _EscalateCeoStubBrowser(chip_count_sequence=[0, 1, 1, 2, 2, 3, 3])
    with pytest.raises(SystemExit):
        flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is True  # the one submit already made — no re-fire happened


# ── money guards stay inert regardless of decide() (task-b8a9a714) ─────────

def test_dry_run_never_calls_decide(tmp_path, monkeypatch):
    def _boom(*_a, **_kw):
        raise AssertionError("decide() must never be called under --dry-run — "
                              "dry-run returns before submit()/poll_result() at all")
    monkeypatch.setattr(flow_shoot.decide_tool, "decide", _boom)
    args = _dry_run_args(tmp_path, "dry_no_decide.tsv")
    stub = _DryRunAwareStubBrowser(chip_count_value=3)
    flow_shoot.cmd_run(args, browser_factory=lambda: stub)
    assert stub.submit_called is False


def test_credit_cap_zero_never_calls_decide(tmp_path, monkeypatch):
    def _boom(*_a, **_kw):
        raise AssertionError("decide() must never be called when credit-cap=0 "
                              "blocks the run before submit()/poll_result()")
    monkeypatch.setattr(flow_shoot.decide_tool, "decide", _boom)
    args = _cap_args(tmp_path, "cap0_no_decide.tsv", cap=0)
    stub = _GateStubBrowser(chip_count_sequence=[0, 1, 1, 2, 2, 3, 3])
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)
    assert stub.submit_called is False
    rows = flow_ledger.load_ledger(tmp_path / "cap0_no_decide.tsv")
    assert rows[35]["status"] == "todo"
    assert rc == 0

# ── live picker DOM contract (winbox, 20 Sep) ──────────────────────────────

class _PickerDOM:
    def __init__(self, row_found=True):
        self.row_found = row_found
        self.chips = 0
        self.fills = []
        self.dialog_selectors = []
        self.close_clicked = False


class _PickerLocator:
    def __init__(self, dom, kind):
        self.dom = dom
        self.kind = kind

    @property
    def first(self):
        return self

    @property
    def last(self):
        return self

    def locator(self, selector):
        self.dom.dialog_selectors.append(selector)
        if selector.startswith('input[aria-label="ค้นหาเนื้อหา"]'):
            return _PickerLocator(self.dom, "search")
        if selector == ".asset-item":
            return _PickerLocator(self.dom, "row")
        if selector == ".asset-item:visible":
            return _PickerLocator(self.dom, "rows")
        if selector == 'button[aria-label="ปิด"]':
            return _PickerLocator(self.dom, "close")
        raise AssertionError(f"unexpected dialog selector: {selector}")

    def filter(self, has_text=None):
        return self

    def click(self, **_kwargs):
        if self.kind == "row":
            self.dom.chips = 1
        elif self.kind == "close":
            self.dom.close_clicked = True

    def wait_for(self, **_kwargs):
        if self.kind == "row" and not self.dom.row_found:
            raise TimeoutError("not rendered")

    def fill(self, value):
        self.dom.fills.append(value)

    def input_value(self):
        return self.dom.fills[-1] if self.dom.fills else ""

    def count(self):
        return 0 if self.kind == "rows" else 1

    def inner_text(self, **_kwargs):
        return ""


class _PickerPage:
    def __init__(self, dom):
        self.dom = dom

    def locator(self, selector):
        if selector == 'button[aria-label="เพิ่มองค์ประกอบลงในช่องพรอมต์"]':
            return _PickerLocator(self.dom, "opener")
        if selector in ('[role="dialog"]', '[role="dialog"]:visible'):
            return _PickerLocator(self.dom, "dialog")
        raise AssertionError(
            f"picker assets/search must be scoped to the dialog, got: {selector}")

    def get_by_text(self, *_args, **_kwargs):
        return _PickerLocator(self.dom, "add")

    def wait_for_timeout(self, _ms):
        pass


def _picker_browser(row_found=True):
    dom = _PickerDOM(row_found=row_found)
    browser = flow_shoot.FlowBrowser()
    browser.page = _PickerPage(dom)
    browser.chip_count = lambda: dom.chips
    return browser, dom


def test_attach_chip_searches_full_picker_dataset_and_verifies_chip_count():
    browser, dom = _picker_browser(row_found=True)

    assert browser.attach_chip("@nong_daeng") is True
    assert dom.fills == ["", "@nong_daeng"]
    assert (
        'input[aria-label="ค้นหาเนื้อหา"], input[aria-label="ค้นหา"]'
        in dom.dialog_selectors
    )
    assert ".asset-item" in dom.dialog_selectors
    assert dom.chips == 1


def test_attach_chip_closes_picker_when_search_has_no_result():
    browser, dom = _picker_browser(row_found=False)

    assert browser.attach_chip("@missing_asset") is False
    assert dom.fills == ["", "@missing_asset", "", "missing_asset"]
    assert dom.close_clicked is True


def test_download_card_never_reuses_a_prior_clip_url(monkeypatch):
    class Card:
        def click(self):
            pass

    class Page:
        def wait_for_timeout(self, _ms):
            pass

        def evaluate(self, _script):
            pass

    browser = flow_shoot.FlowBrowser()
    browser.download_resolution = "720p"  # exercise the legacy CDN guard
    browser.page = Page()
    browser._captured_video_urls = ["https://flow-content.google/video/old"]
    monkeypatch.setattr(flow_shoot, "COMPLETION_TIMEOUT_S", 0)

    with pytest.raises(RuntimeError, match="refusing to reuse a prior clip URL"):
        browser.download_card(Card())


# ── a log write must never be able to stop a shoot ──────────────────────────
# 2026-09-22: Act 5 died at shot 128 after 18 good ones. The log file was UTF-8,
# but stdout on Windows is cp1252 and every line of this film is Thai, so one
# un-encodable character raised UnicodeEncodeError straight out of print().
class _Cp1252Stdout:
    """stdout that behaves like a Windows console: cp1252, and it raises."""
    encoding = "cp1252"

    def __init__(self):
        self.written = []

    def write(self, s):
        s.encode("cp1252")          # raises UnicodeEncodeError on Thai
        self.written.append(s)
        return len(s)

    def flush(self):
        pass


def test_log_survives_a_console_that_cannot_encode_thai(tmp_path, monkeypatch):
    monkeypatch.setattr(flow_shoot, "LOG_PATH", tmp_path / "run.log")
    fake = _Cp1252Stdout()
    monkeypatch.setattr(sys, "stdout", fake)

    flow_shoot._log('shot 128: submitted "ผมแค่จะไม่จ่ายอีกแล้ว"')

    # the console got something rather than an exception
    assert any("shot 128" in w for w in fake.written)
    # and the file kept the real Thai, undamaged
    written = (tmp_path / "run.log").read_text(encoding="utf-8")
    assert "ผมแค่จะไม่จ่ายอีกแล้ว" in written


def test_log_leaves_an_ordinary_console_untouched(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(flow_shoot, "LOG_PATH", tmp_path / "run.log")
    flow_shoot._log("shot 129: verified — 8.0s 1080x1920 ผ่าน")
    assert "ผ่าน" in capsys.readouterr().out


# ── picker row matching: exact asset, never a prefix of another ──

@pytest.mark.parametrize("handle,row_text,expected", [
    ("@cop_wit", "@cop_wit", True),
    ("@cop_wit", "cop_wit\nตัวละคร", True),
    ("@cop_wit", "@cop_wit_uniform_A", False),
    ("@cop_wit", "cop_wit_uniform_A\nรูปภาพ", False),
    ("@cop_wit_uniform_A", "cop_wit_uniform_A\nรูปภาพ", True),
    ("@cop_wit_uniform_A", "@cop_wit_uniform_AB", False),
    ("@noodle_shop", "@noodle_shop_thriving", False),
    ("@noodle_shop", "@noodle_shop", True),
    ("@noodle_shop_thriving", "@noodle_shop_thriving", True),
    ("@nong_daeng", "@nong_daeng_suit", False),
])
def test_picker_row_pattern_matches_the_exact_asset_only(handle, row_text, expected):
    assert bool(flow_shoot.picker_row_pattern(handle).search(row_text)) is expected


# ── card key for a shot with no dialogue ──

def test_card_fragment_prefers_dialogue():
    p = ('In a shop — five tables. a man <IMAGE_REF_0> — walks in.\n\n'
         'The man speaks Thai, and says: "สวัสดีครับลุง"')
    assert flow_shoot.card_fragment(p) == "สวัสดีครับลุง"


def test_card_fragment_falls_back_to_the_action_not_the_location():
    p = ('Use <IMAGE_REF_0> as the character reference for cop_wit.\n\n'
         'In a narrow Bangkok shophouse ground floor turned noodle shop — five worn '
         'wooden tables, night. a Thai man of 32 <IMAGE_REF_0> — sits alone at the '
         'corner table facing the door with a bowl in front of him, saying nothing.\n\n'
         'Medium close shot on him alone, static camera.')
    frag = flow_shoot.card_fragment(p)
    assert frag.startswith("sits alone at the corner table")
    assert "five worn" not in frag and len(frag) <= 60


# ── a submit only counts once a NEW batch is at the top of the feed ──

@pytest.mark.parametrize("before,after,expected", [
    ((6, "old 176"), (7, "new 179"), True),      # one more batch
    ((6, "old 176"), (6, "new 179"), True),      # virtualised feed: same count, new head
    ((6, "old 176"), (6, "old 176"), False),     # nothing happened
    ((6, "old 176"), (-1, ""), False),           # failed read is not a change
    ((-1, ""), (7, "new 179"), False),           # unknown baseline is not a change
    ((0, ""), (0, ""), False),
])
def test_feed_changed(before, after, expected):
    assert flow_shoot.feed_changed(before, after) is expected
