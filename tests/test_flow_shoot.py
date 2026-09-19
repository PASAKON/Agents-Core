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

import subprocess
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


def test_verify_clip_missing_file():
    ok, reason = flow_shoot.verify_clip(Path("/does/not/exist.mp4"), expected_dur=6)
    assert ok is False
    assert reason == "file missing"


def test_sha256_file_is_stable(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"same bytes")
    assert flow_shoot.sha256_file(f) == flow_shoot.sha256_file(f)
    g = tmp_path / "b.bin"
    g.write_bytes(b"different bytes")
    assert flow_shoot.sha256_file(f) != flow_shoot.sha256_file(g)


# ── check_replay_script.py gate (the thing that actually blocks merge) ──────

def test_check_replay_script_accepts_flow_shoot():
    r = subprocess.run(
        ["python3", "tools/check_replay_script.py", "tools/flow_shoot.py",
         "tools/flow_ledger.py", "scripts/flow/launch-chrome-debug.sh"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
