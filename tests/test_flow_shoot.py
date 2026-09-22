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

    def submit(self, expected_chip_count=None) -> None:
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
