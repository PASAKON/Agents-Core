"""Pure-function tests for the jev-editor-helper skill's jev_edit_lib.py
(task-5cfe20b1): candidate building, slot mapping, the confidence gate, and
SCRIPT.tsv parsing. No network, no tools.decide import, no paid call ever —
jev_edit.py's CLI orchestration (which does call tools.decide.decide()) is
deliberately out of scope here.

Loaded via importlib.util.spec_from_file_location, same pattern as
tests/test_hook_log_prompt_records.py / tests/test_gc_ratelimited_liveness.py
— the module lives under `.claude/skills/...`, not an importable package path.

Run via: pytest tests/test_jev_edit.py -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = (
    ROOT / ".claude" / "skills" / "VIDEO_EDITOR_jev-editor-helper" / "scripts" / "jev_edit_lib.py"
)
spec = importlib.util.spec_from_file_location("jev_edit_lib", LIB_PATH)
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)


# ────────────────────────────────────────────────────── SCRIPT.tsv parsing ─

def test_parse_script_tsv_reads_all_columns(tmp_path):
    p = tmp_path / "SCRIPT.tsv"
    p.write_text(
        "tag\tspoken\tshot\tbeat\tscreen\n"
        "HOOK-1\tโบรกเกอร์นี้ไม่มีใบอนุญาตจริงหรือ\tavatar full\t\t\n"
        "CONTEXT-1\tดูคะแนน WikiFX 1.69\tcomposite\tshow\twikifx score card\n",
        encoding="utf-8",
    )
    lines = lib.parse_script_tsv(p)
    assert len(lines) == 2
    assert lines[0].tag == "HOOK-1"
    assert lines[0].beat == ""
    assert lines[1].beat == "show"
    assert lines[1].screen == "wikifx score card"


def test_parse_script_tsv_skips_rows_missing_tag_or_spoken(tmp_path):
    p = tmp_path / "SCRIPT.tsv"
    p.write_text(
        "tag\tspoken\tshot\tbeat\tscreen\n"
        "\tsome text\tx\t\t\n"  # missing tag
        "TAG-2\t\tx\t\t\n"  # missing spoken
        "TAG-3\thas text\tx\t\t\n",
        encoding="utf-8",
    )
    lines = lib.parse_script_tsv(p)
    assert [l.tag for l in lines] == ["TAG-3"]


def test_parse_script_tsv_tolerates_missing_optional_columns(tmp_path):
    p = tmp_path / "SCRIPT.tsv"
    p.write_text("tag\tspoken\nA\ttext here\n", encoding="utf-8")
    lines = lib.parse_script_tsv(p)
    assert lines[0].shot == "" and lines[0].beat == "" and lines[0].screen == ""


def test_parse_script_tsv_handles_no_header_positional_rows(tmp_path):
    # task-80d18826's real bl57-script/SCRIPT.tsv shape: no header row,
    # 4 or 5 tab-separated columns straight to data.
    p = tmp_path / "SCRIPT.tsv"
    p.write_text(
        "HOOK-1\tข้อความแรก\t\thook\n"
        "HOOK-3\tข้อความสอง\twikifx-xxlmarkets-review\tshow\t1.99/10\n",
        encoding="utf-8",
    )
    lines = lib.parse_script_tsv(p)
    assert len(lines) == 2
    assert lines[0].tag == "HOOK-1" and lines[0].beat == "hook" and lines[0].screen == ""
    assert lines[1].shot == "wikifx-xxlmarkets-review" and lines[1].screen == "1.99/10"


# ───────────────────────────────────────────────── beat -> mode / entry ────

@pytest.mark.parametrize("beat,expected", [
    ("show", "composite"),
    ("hook", "full"),
    ("verdict", "full"),
    ("cta", "full"),
    ("other", None),
    (None, None),
])
def test_mode_for_beat(beat, expected):
    assert lib.mode_for_beat(beat) == expected


def test_entry_mode_change_defaults_missing_prev_to_full():
    assert lib.entry_mode_change(None, "composite") == "full_to_composite"
    assert lib.entry_mode_change("composite", None) == "composite_to_full"
    assert lib.entry_mode_change("full", "full") == "full_to_full"


# ──────────────────────────────────────────────────────── rectangle maths ──

def test_rect_overlaps_true_for_intersecting_rects():
    a = {"x": 0, "y": 0, "w": 100, "h": 100}
    b = {"x": 50, "y": 50, "w": 100, "h": 100}
    assert lib.rect_overlaps(a, b) is True


def test_rect_overlaps_false_for_disjoint_rects():
    a = {"x": 0, "y": 0, "w": 10, "h": 10}
    b = {"x": 100, "y": 100, "w": 10, "h": 10}
    assert lib.rect_overlaps(a, b) is False


def test_rect_overlaps_margin_catches_near_miss():
    a = {"x": 0, "y": 0, "w": 10, "h": 10}
    b = {"x": 11, "y": 0, "w": 10, "h": 10}  # 1px gap, no overlap unmargined
    assert lib.rect_overlaps(a, b, margin=0) is False
    assert lib.rect_overlaps(a, b, margin=5) is True


def test_text_bands_stay_inside_safe_area():
    bands = lib.text_bands()
    assert len(bands) > 0
    for band in bands:
        assert band["y"] >= lib.SAFE_TOP
        assert band["y"] + band["h"] <= lib.SAFE_BOTTOM
        assert band["x"] == lib.SAFE_LEFT


def test_text_bands_narrow_below_rail_wide_above():
    bands = lib.text_bands()
    for band in bands:
        right_edge = band["x"] + band["w"]
        if band["y"] < lib.RAIL_Y:
            assert right_edge == lib.CANVAS_W - lib.SAFE_RIGHT_WIDE
        else:
            assert right_edge == lib.CANVAS_W - lib.SAFE_RIGHT_NARROW


def test_free_text_rects_excludes_avatar_box_when_active():
    all_bands = lib.text_bands()
    free = lib.free_text_rects(lib.AVATAR_BOX, None, avatar_active=True)
    assert len(free) < len(all_bands)
    for band in free:
        assert not lib.rect_overlaps(band, lib.AVATAR_BOX, lib.CLEARANCE)


def test_free_text_rects_ignores_avatar_box_when_inactive():
    all_bands = lib.text_bands()
    free = lib.free_text_rects(lib.AVATAR_BOX, None, avatar_active=False)
    assert len(free) == len(all_bands)


def test_free_text_rects_also_excludes_focus_box():
    focus_box = {"x": 120, "y": 300, "w": 800, "h": 150}
    free_without = lib.free_text_rects(lib.AVATAR_BOX, None, avatar_active=True)
    free_with = lib.free_text_rects(lib.AVATAR_BOX, focus_box, avatar_active=True)
    assert len(free_with) < len(free_without)
    for band in free_with:
        assert not lib.rect_overlaps(band, focus_box, lib.CLEARANCE)


# ─────────────────────────────────────────────── labelling / resolving ─────

def test_label_candidates_caps_at_six():
    items = [{"x": i} for i in range(9)]
    labelled = lib.label_candidates(items)
    assert len(labelled) == 6
    assert [c["label"] for c in labelled] == ["A", "B", "C", "D", "E", "F"]
    assert labelled[0]["x"] == 0


def test_label_candidates_fewer_than_six():
    labelled = lib.label_candidates([{"x": 1}, {"x": 2}])
    assert [c["label"] for c in labelled] == ["A", "B"]


def test_resolve_label_finds_match():
    labelled = lib.label_candidates([{"v": "one"}, {"v": "two"}])
    assert lib.resolve_label(labelled, "B")["v"] == "two"


def test_resolve_label_returns_none_for_other_or_unknown():
    labelled = lib.label_candidates([{"v": "one"}])
    assert lib.resolve_label(labelled, "other") is None
    assert lib.resolve_label(labelled, "Z") is None
    assert lib.resolve_label(labelled, None) is None


# ──────────────────────────────────────────── REAL_MANIFEST DOM candidates ─

def test_dom_candidates_for_tag_filters_by_covers_and_sorts_reading_order():
    manifest = [
        {
            "file": "real/a.png", "covers": ["CONTEXT-3"],
            "evidence_box": [{"x": 100, "y": 500, "w": 200, "h": 80},
                              {"x": 50, "y": 100, "w": 300, "h": 60}],
        },
        {"file": "real/b.png", "covers": ["OTHER-1"], "evidence_box": [{"x": 0, "y": 0, "w": 10, "h": 10}]},
    ]
    candidates = lib.dom_candidates_for_tag(manifest, "CONTEXT-3")
    assert len(candidates) == 2
    # sorted top-to-bottom: y=100 box before y=500 box
    assert candidates[0]["y"] == 100
    assert candidates[1]["y"] == 500
    assert all(c["source"] == "real/a.png" for c in candidates)


def test_dom_candidates_for_tag_empty_without_manifest():
    assert lib.dom_candidates_for_tag(None, "TAG-1") == []


def test_dom_candidates_for_tag_empty_when_entry_has_no_evidence_box():
    # current tools/bl_realfootage.py manifest shape — no evidence_box yet.
    manifest = [{"file": "real/a.png", "covers": ["TAG-1"]}]
    assert lib.dom_candidates_for_tag(manifest, "TAG-1") == []


def test_dom_candidates_for_tag_caps_at_six():
    manifest = [{
        "file": "real/a.png", "covers": ["T"],
        "evidence_box": [{"x": i, "y": i, "w": 10, "h": 10} for i in range(9)],
    }]
    assert len(lib.dom_candidates_for_tag(manifest, "T")) == 6


# ───────────────────────────────────────── content words / numbers / brand ─

def test_content_words_extracts_number_and_dedups():
    words = lib.content_words("สเปรดต่ำสุด GOLD 25% ของราคา")
    texts = [w["text"] for w in words]
    assert "25%" in texts
    assert "GOLD" in texts
    kinds = {w["text"]: w["kind"] for w in words}
    assert kinds["25%"] == "number"
    assert kinds["GOLD"] == "word"


def test_content_words_brand_mention_via_map():
    brand_map = {"เอ็กซ์เอ็ม": "XM", "เอ็กซ์เนส": "Exness"}
    words = lib.content_words("ลองเข้าเว็บเอ็กซ์เอ็มดูเองเลย", brand_map)
    assert {"text": "XM", "kind": "brand"} in words


def test_content_words_caps_at_six_and_orders_by_appearance():
    spoken = "A1 B2 C3 D4 E5 F6 G7"
    words = lib.content_words(spoken)
    assert len(words) == 6
    assert [w["text"] for w in words] == ["A1", "B2", "C3", "D4", "E5", "F6"]


def test_content_words_empty_for_plain_thai_sentence_no_brand():
    assert lib.content_words("ผมบอกความจริงที่ไม่มีใครบอกมึง") == []


# ───────────────────────────────────────────────── confidence + the gate ───

def test_confidence_of_returns_max_prob():
    assert lib.confidence_of({"a": 0.2, "b": 0.7, "c": 0.1}) == 0.7


def test_confidence_of_empty_probs_is_zero():
    assert lib.confidence_of({}) == 0.0


@pytest.mark.parametrize("choice,conf,gate,expected", [
    ("a", 0.9, 0.7, False),
    ("a", 0.5, 0.7, True),
    (None, 0.99, 0.7, True),
    ("a", 0.7, 0.7, False),
])
def test_needs_review_gate(choice, conf, gate, expected):
    assert lib.needs_review(choice, conf, gate) is expected


def test_bucket_confidence_buckets_correctly():
    rows = [
        (0.3, False), (0.45, True),
        (0.55, True), (0.65, False),
        (0.75, True), (0.80, True),
        (0.90, True), (0.99, True), (0.86, False),
    ]
    buckets = lib.bucket_confidence(rows)
    low = buckets["0.00-0.50"]
    assert low["n"] == 2 and low["accuracy"] == pytest.approx(0.5)
    mid = buckets["0.50-0.70"]
    assert mid["n"] == 2 and mid["accuracy"] == pytest.approx(0.5)
    hi = buckets["0.70-0.85"]
    assert hi["n"] == 2 and hi["accuracy"] == pytest.approx(1.0)
    top = [v for k, v in buckets.items() if k.startswith(">=0.85") or k == "0.85-1.00"][0]
    assert top["n"] == 3
    assert top["accuracy"] == pytest.approx(2 / 3)


def test_bucket_confidence_empty_bucket_has_none_accuracy():
    buckets = lib.bucket_confidence([(0.95, True)])
    assert buckets["0.00-0.50"]["n"] == 0
    assert buckets["0.00-0.50"]["accuracy"] is None


# ─────────────────────────────────────────────────────── load_brand_map ────

def test_load_brand_map_reads_yaml_and_skips_comments(tmp_path):
    p = tmp_path / "brand-display.yaml"
    p.write_text(
        "# a comment line, ignored by pyyaml\n"
        "วิกิเอฟเอ็กซ์: WikiFX\n"
        "ติ๊กต๊อก: TikTok\n",
        encoding="utf-8",
    )
    brand_map = lib.load_brand_map(p)
    assert brand_map == {"วิกิเอฟเอ็กซ์": "WikiFX", "ติ๊กต๊อก": "TikTok"}


def test_load_brand_map_reads_the_real_shipped_file():
    real_path = (
        ROOT / ".claude" / "skills" / "blackliquidity-cut" / "brand-display.yaml"
    )
    if not real_path.exists():
        pytest.skip("blackliquidity-cut brand-display.yaml not in this sparse checkout")
    brand_map = lib.load_brand_map(real_path)
    assert brand_map.get("เอ็กซ์เอ็ม") == "XM"


# ──────────────────────────────────────────────────── recommend_gate ───────

def test_recommend_gate_finds_smallest_all_correct_threshold():
    rows = [(0.3, False), (0.5, True), (0.6, False), (0.72, True), (0.9, True)]
    assert lib.recommend_gate(rows) == 0.72


def test_recommend_gate_none_when_top_confidence_is_wrong():
    rows = [(0.5, True), (0.99, False)]
    assert lib.recommend_gate(rows) is None


def test_recommend_gate_none_for_empty_rows():
    assert lib.recommend_gate([]) is None


def test_recommend_gate_all_correct_returns_lowest():
    rows = [(0.2, True), (0.6, True), (0.9, True)]
    assert lib.recommend_gate(rows) == 0.2


# ───────────────────────────────────────── census groundtruth (task-82380776) ─

def test_parse_census_groundtruth_reads_rows(tmp_path):
    p = tmp_path / "groundtruth.tsv"
    p.write_text(
        "t0\tt1\ttext\tclass\tentry_type\tfocus_device\ttarget\thighlighted_word\tsfx\n"
        "0.00\t1.90\tข้อความ\thook\tcut\tavatar_slide\tavatar box (whole)\t-\tother@1.96\n",
        encoding="utf-8",
    )
    rows = lib.parse_census_groundtruth(p)
    assert len(rows) == 1
    assert rows[0]["class"] == "hook"
    assert rows[0]["entry_type"] == "cut"


def test_census_line_id_uses_t0():
    assert lib.census_line_id({"t0": "9.20", "t1": "11.34"}) == "t9.20"


def test_entry_type_map_known_values():
    assert lib.ENTRY_TYPE_MAP["cut"] == "hard_cut"
    assert lib.ENTRY_TYPE_MAP["shrink"] == "shrink"
    assert "-" not in lib.ENTRY_TYPE_MAP


def test_focus_device_map_only_covers_matching_concepts():
    assert lib.FOCUS_DEVICE_MAP["highlighter_sweep"] == "highlight_sweep"
    assert lib.FOCUS_DEVICE_MAP["pan+zoom"] == "zoom_only"
    for unmapped in ("avatar_shrink", "avatar_slide", "plate_dissolve", "pop", "scroll"):
        assert unmapped not in lib.FOCUS_DEVICE_MAP


# ═══════════════════════════ Jev up-skill scoreboard (task-161643f7) ═══════

# ──────────────────────────────────────────────────────── freeze / integrity

def _beat_row(line_id, choice, confidence, state_lang="th", question="bl.beat"):
    return {"line_id": line_id, "question": question, "choice": choice, "confidence": confidence,
            "state_lang": state_lang, "ledger_id": f"led-{line_id}-{question}"}


def test_sha256_of_rows_ignores_final_and_applied_by_fields():
    rows = [_beat_row("L1", "hook", 0.9)]
    before = lib.sha256_of_rows(rows)
    rows[0]["final"] = "hook"
    rows[0]["applied_by"] = "jev"
    rows[0]["jev_wrong_at_gate"] = False
    after = lib.sha256_of_rows(rows)
    assert before == after


def test_sha256_of_rows_changes_if_jev_answer_changes():
    a = [_beat_row("L1", "hook", 0.9)]
    b = [_beat_row("L1", "show", 0.9)]  # choice differs
    assert lib.sha256_of_rows(a) != lib.sha256_of_rows(b)


def test_check_frozen_refuses_when_never_frozen():
    with pytest.raises(lib.FreezeError, match="not frozen"):
        lib.check_frozen(None, [_beat_row("L1", "hook", 0.9)], "sha-abc")


def test_check_frozen_refuses_on_site_yaml_sha_mismatch():
    rows = [_beat_row("L1", "hook", 0.9)]
    frozen = lib.build_frozen_stamp("decisions.jsonl", rows, "sha-old", "2026-09-23T00:00:00+00:00")
    with pytest.raises(lib.FreezeError, match="site YAML sha changed"):
        lib.check_frozen(frozen, rows, "sha-new")


def test_check_frozen_refuses_when_jev_answers_tampered_after_freeze():
    rows = [_beat_row("L1", "hook", 0.9)]
    frozen = lib.build_frozen_stamp("decisions.jsonl", rows, "sha-abc", "2026-09-23T00:00:00+00:00")
    tampered = [_beat_row("L1", "show", 0.9)]  # choice edited after freeze
    with pytest.raises(lib.FreezeError, match="changed since freeze"):
        lib.check_frozen(frozen, tampered, "sha-abc")


def test_check_frozen_passes_when_nothing_changed_even_after_final_added():
    rows = [_beat_row("L1", "hook", 0.9)]
    frozen = lib.build_frozen_stamp("decisions.jsonl", rows, "sha-abc", "2026-09-23T00:00:00+00:00")
    rows[0]["final"] = "hook"
    rows[0]["applied_by"] = "jev"
    lib.check_frozen(frozen, rows, "sha-abc")  # must not raise


def test_frozen_path_for_replaces_jsonl_suffix():
    assert lib.frozen_path_for(Path("out/decisions.jsonl")) == Path("out/decisions.frozen.json")


# ──────────────────────────────────────────────────── applied_by / the gate

def test_safe_gate_for_bl_beat_th_is_measured():
    assert lib.safe_gate_for("bl.beat", "th") == 0.95


def test_safe_gate_for_bl_beat_en_has_none():
    assert lib.safe_gate_for("bl.beat", "en") is None


def test_safe_gate_for_bl_entry_has_none_regardless_of_state_lang():
    assert lib.safe_gate_for("bl.entry", None) is None


def test_safe_gate_for_unmeasured_site_is_none():
    assert lib.safe_gate_for("bl.text_slot", None) is None


def test_applied_by_gate_boundary_just_below_vs_at_threshold():
    below = lib.final_call_record("bl.beat", "th", "hook", 0.949, "hook")
    at = lib.final_call_record("bl.beat", "th", "hook", 0.95, "hook")
    assert below == {"applied_by": "editor", "jev_wrong_at_gate": False}
    assert at == {"applied_by": "jev", "jev_wrong_at_gate": False}


def test_applied_by_ungated_site_always_editor_even_at_full_confidence():
    rec = lib.final_call_record("bl.entry", None, "hard_cut", 1.00, "hard_cut")
    assert rec == {"applied_by": "editor", "jev_wrong_at_gate": False}


def test_applied_by_ungated_state_variant_always_editor():
    rec = lib.final_call_record("bl.beat", "en", "cta", 0.99, "cta")
    assert rec == {"applied_by": "editor", "jev_wrong_at_gate": False}


def test_applied_by_editor_override_above_gate_flags_jev_wrong_at_gate():
    rec = lib.final_call_record("bl.beat", "th", "verdict", 0.97, "hook")
    assert rec == {"applied_by": "editor", "jev_wrong_at_gate": True}


def test_parse_final_tsv_reads_bulk_rows(tmp_path):
    p = tmp_path / "finals.tsv"
    p.write_text("line_id\tquestion\tchoice\nL1\tbl.beat\thook\nL2\tbl.entry\tshrink\n", encoding="utf-8")
    rows = lib.parse_final_tsv(p)
    assert rows == [
        {"line_id": "L1", "question": "bl.beat", "choice": "hook"},
        {"line_id": "L2", "question": "bl.entry", "choice": "shrink"},
    ]


# ─────────────────────────────────────────────────────────── frames + timing

def test_parse_line_timings_reads_tag_t0_t1(tmp_path):
    p = tmp_path / "timings.tsv"
    p.write_text("tag\tt0\tt1\nL1\t0.0\t3.0\nL2\t3.0\t7.5\n", encoding="utf-8")
    timings = lib.parse_line_timings(p)
    assert timings == {"L1": (0.0, 3.0), "L2": (3.0, 7.5)}


def test_video_duration_seconds_is_max_t1():
    assert lib.video_duration_seconds({"L1": (0.0, 3.0), "L2": (3.0, 7.5)}) == 7.5


def test_jev_beat_frames_sums_only_applied_bl_beat_lines():
    rows = [
        {"line_id": "L1", "question": "bl.beat", "applied_by": "jev"},
        {"line_id": "L2", "question": "bl.beat", "applied_by": "editor"},
        {"line_id": "L3", "question": "bl.entry", "applied_by": "jev"},  # not bl.beat — excluded
        {"line_id": "L4", "question": "bl.beat", "applied_by": "jev"},
    ]
    timings = {"L1": (0.0, 3.0), "L2": (3.0, 7.5), "L3": (7.5, 10.0), "L4": (10.0, 12.0)}
    result = lib.jev_beat_frames(rows, timings)
    # L1 3.0s -> 90 frames, L4 2.0s -> 60 frames; L2 not applied, L3 not bl.beat
    assert result == {"jev_seconds": 5.0, "jev_frames": 150, "missing_tags": []}


def test_jev_beat_frames_lists_missing_timing_tags_without_crashing():
    rows = [{"line_id": "NOPE", "question": "bl.beat", "applied_by": "jev"}]
    result = lib.jev_beat_frames(rows, {})
    assert result == {"jev_seconds": 0.0, "jev_frames": 0, "missing_tags": ["NOPE"]}


# ─────────────────────────────────────────────────────────── score aggregates

def test_applied_summary_counts_and_percent():
    rows = [
        {"applied_by": "jev"}, {"applied_by": "jev"}, {"applied_by": "editor"}, {"applied_by": "editor"},
    ]
    assert lib.applied_summary(rows) == {"decisions_total": 4, "jev_applied": 2, "jev_applied_pct": 50.0}


def test_raw_accuracy_by_site_groups_by_site_key_and_ignores_missing_final():
    rows = [
        {"question": "bl.beat", "state_lang": "th", "choice": "hook", "final": "hook"},
        {"question": "bl.beat", "state_lang": "th", "choice": "show", "final": "hook"},
        {"question": "bl.beat", "state_lang": "en", "choice": "cta", "final": "cta"},
        {"question": "bl.entry", "state_lang": None, "choice": "shrink", "final": None},  # no final yet — excluded
    ]
    out = lib.raw_accuracy_by_site(rows)
    assert out["bl.beat[th]"] == {"n": 2, "correct": 1, "accuracy": 0.5}
    assert out["bl.beat[en]"] == {"n": 1, "correct": 1, "accuracy": 1.0}
    assert "bl.entry" not in out


def test_count_jev_wrong_at_gate():
    rows = [{"jev_wrong_at_gate": True}, {"jev_wrong_at_gate": False}, {"jev_wrong_at_gate": True}]
    assert lib.count_jev_wrong_at_gate(rows) == 2


# ─────────────────────────────────────────────────────── IRON §57 token proof

def test_jev_spend_and_tokens_uses_only_this_plans_ledger_rows():
    rows = [
        {"ledger_id": "led-1", "applied_by": "jev"},
        {"ledger_id": "led-2", "applied_by": "editor"},
        {"ledger_id": "led-missing", "applied_by": "jev"},
    ]
    ledger_by_id = {
        "led-1": {"tokens_in": 60, "tokens_out": 5, "cost_usd": 0.000002, "counterfactual_usd": 0.002},
        "led-2": {"tokens_in": 40, "tokens_out": 5, "cost_usd": 0.000001, "counterfactual_usd": 0.001},
        # led-missing intentionally absent, plus an unrelated month row that must NOT be summed:
        "led-other-episode": {"tokens_in": 999, "tokens_out": 999, "cost_usd": 1.0, "counterfactual_usd": 1.0},
    }
    out = lib.jev_spend_and_tokens(rows, ledger_by_id)
    assert out["jev_tokens"] == 110
    assert out["jev_usd"] == pytest.approx(0.000003)
    assert out["counterfactual_usd"] == pytest.approx(0.002)  # only led-1 is applied_by=jev
    assert out["missing_ledger_ids"] == ["led-missing"]


def test_counterfactual_tokens_matches_decide_py_formula():
    cfg = {"counterfactual": {"images": 0, "big_model_tokens_out": 30, "extra_input_chars": 0}}
    out = lib.counterfactual_tokens(cfg, state_chars=200)
    assert out == {"tokens_in": 50.0, "tokens_out": 30, "tokens_total": 80.0}


def test_sum_transcript_usage_dedupes_by_message_id():
    # The same message id repeated 3x with IDENTICAL usage — the real shape
    # measured on task-52c669bb's transcript (143/168 ids repeated, every
    # repeat byte-identical). Summing naively would triple-count.
    one = {"message": {"id": "msg-1", "usage": {
        "input_tokens": 2, "output_tokens": 88,
        "cache_read_input_tokens": 0, "cache_creation_input_tokens": 88284,
    }}}
    lines = [one, one, one]
    totals = lib.sum_transcript_usage(lines)
    assert totals == {"input": 2, "output": 88, "cache_read": 0, "cache_write": 88284, "total": 88374}


def test_sum_transcript_usage_returns_four_components_separately():
    # CTO review 2026-09-23: cache_read must be its own component, kept
    # separate from cache_write/input/output, so a caller can exclude it
    # from the primary (new-work) metric.
    lines = [
        {"message": {"id": "m1", "usage": {"input_tokens": 5, "output_tokens": 7,
                                            "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 20}}},
    ]
    totals = lib.sum_transcript_usage(lines)
    assert totals == {"input": 5, "output": 7, "cache_read": 1000, "cache_write": 20, "total": 1032}


def test_new_work_tokens_excludes_cache_read():
    usage = {"input": 5, "output": 7, "cache_read": 1000, "cache_write": 20, "total": 1032}
    assert lib.new_work_tokens(usage) == 32  # 5+7+20, NOT +1000


def test_primary_and_secondary_metric_maths_matches_real_bl55_numbers():
    # CTO's own dedup count of task-52c669bb's real 31MB transcript
    # (deduped by message.id): 336 in, 168884 out, 800018 cache_write,
    # 54500654 cache_read, over a 133.13s render. Primary must reproduce
    # the CTO's own 969,238 new-work tokens = 436,823/min exactly; the
    # secondary (incl. cache) is the same total this task measured before.
    usage = {"input": 336, "output": 168884, "cache_read": 54500654, "cache_write": 800018,
              "total": 336 + 168884 + 54500654 + 800018}
    duration_s = 133.13
    new_total = lib.new_work_tokens(usage)
    assert new_total == 969238
    primary = lib.tokens_per_video_minute(new_total, duration_s)
    secondary = lib.tokens_per_video_minute(usage["total"], duration_s)
    assert primary == pytest.approx(436_823, abs=1)
    assert secondary == pytest.approx(24_999_576, abs=5)
    assert secondary > primary * 50  # cache reads dominate the total, as measured (98.3%)


def test_sum_transcript_usage_sums_distinct_ids_and_skips_lines_without_usage():
    lines = [
        {"message": {"id": "m1", "usage": {"input_tokens": 10, "output_tokens": 1,
                                            "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
        {"message": {"id": "m2", "usage": {"input_tokens": 20, "output_tokens": 2,
                                            "cache_read_input_tokens": 5, "cache_creation_input_tokens": 0}}},
        {"message": {"content": "no usage here"}},  # a user turn — no usage key
        {},  # a malformed/empty record
    ]
    totals = lib.sum_transcript_usage(lines)
    assert totals["total"] == 38  # (10+1) + (20+2+5)


def test_tokens_per_video_minute_normalises_correctly():
    assert lib.tokens_per_video_minute(6000, 60.0) == pytest.approx(6000.0)  # 1 min of video
    assert lib.tokens_per_video_minute(3000, 30.0) == pytest.approx(6000.0)  # 0.5 min of video


def test_tokens_per_video_minute_none_when_no_duration():
    assert lib.tokens_per_video_minute(1000, None) is None
    assert lib.tokens_per_video_minute(1000, 0) is None


# ────────────────────────────────────────────── BASELINE + pass/fail (§57)

def test_median_odd_and_even():
    assert lib.median([3.0, 1.0, 2.0]) == 2.0
    assert lib.median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert lib.median([]) is None


def test_build_baseline_row_medians_only_measured_episodes():
    episodes = [
        {"episode": "BL52", "task_id": "task-a", "editor_new_tokens_per_video_min": None,
         "editor_total_tokens_per_video_min": None, "missing": "transcript"},
        {"episode": "BL53", "task_id": "task-b", "editor_new_tokens_per_video_min": 1000.0,
         "editor_total_tokens_per_video_min": 50000.0, "missing": None},
        {"episode": "BL54", "task_id": "task-c", "editor_new_tokens_per_video_min": 3000.0,
         "editor_total_tokens_per_video_min": 70000.0, "missing": None},
    ]
    row = lib.build_baseline_row(episodes)
    assert row["editor_new_tokens_per_video_min"] == 2000.0
    assert row["editor_total_tokens_per_video_min"] == 60000.0
    assert row["n_measured"] == 2
    assert row["n_total"] == 3


def test_build_baseline_row_n_equals_one_matches_real_bl55():
    # CTO review 2026-09-23: BASELINE = BL55 only, n=1.
    episodes = [
        {"episode": "BL52", "task_id": "task-b2d369ed", "editor_new_tokens_per_video_min": None,
         "editor_total_tokens_per_video_min": None, "missing": "transcript"},
        {"episode": "BL53", "task_id": "task-f52b76c4", "editor_new_tokens_per_video_min": None,
         "editor_total_tokens_per_video_min": None, "missing": "transcript,duration"},
        {"episode": "BL54", "task_id": "task-1499ecd7", "editor_new_tokens_per_video_min": None,
         "editor_total_tokens_per_video_min": None, "missing": "transcript"},
        {"episode": "BL55", "task_id": "task-52c669bb", "editor_new_tokens_per_video_min": 436823.0,
         "editor_total_tokens_per_video_min": 24999576.0, "missing": None},
    ]
    row = lib.build_baseline_row(episodes)
    assert row["n_measured"] == 1
    assert row["editor_new_tokens_per_video_min"] == 436823.0


def _episode(ep, tpm, applied_pct, wrong=0):
    return {"episode": ep, "editor_new_tokens_per_video_min": tpm, "jev_applied_pct": applied_pct, "jev_wrong_at_gate": wrong}


def test_evaluate_hypothesis_in_progress_before_four_episodes():
    episodes = [_episode("EP57", 5000.0, 10.0), _episode("EP58", 4800.0, 15.0)]
    out = lib.evaluate_hypothesis(episodes, baseline_tokens_per_min=5000.0)
    assert out == {"verdict": "IN_PROGRESS", "n": 2, "of": 4, "reasons": ["2/4 episodes scored"]}


def test_evaluate_hypothesis_pass_when_all_four_conditions_hold():
    episodes = [
        _episode("EP57", 6000.0, 10.0), _episode("EP58", 5500.0, 20.0),
        _episode("EP59", 4000.0, 30.0), _episode("EP60", 3000.0, 40.0),
    ]
    out = lib.evaluate_hypothesis(episodes, baseline_tokens_per_min=5000.0)
    assert out["verdict"] == "PASS"
    assert out["mean_ep59_60"] == 3500.0
    assert out["wrong_at_gate_total"] == 0


def test_evaluate_hypothesis_fail_when_mean_above_baseline():
    episodes = [
        _episode("EP57", 6000.0, 10.0), _episode("EP58", 5800.0, 20.0),
        _episode("EP59", 5500.0, 30.0), _episode("EP60", 5200.0, 40.0),
    ]
    out = lib.evaluate_hypothesis(episodes, baseline_tokens_per_min=5000.0)
    assert out["verdict"] == "FAIL"
    assert any("baseline" in r for r in out["reasons"])


def test_evaluate_hypothesis_fail_when_wrong_at_gate_hits_threshold():
    episodes = [
        _episode("EP57", 6000.0, 10.0, wrong=1), _episode("EP58", 5000.0, 20.0, wrong=1),
        _episode("EP59", 3000.0, 30.0), _episode("EP60", 2000.0, 40.0),
    ]
    out = lib.evaluate_hypothesis(episodes, baseline_tokens_per_min=5000.0)
    assert out["verdict"] == "FAIL"
    assert out["wrong_at_gate_total"] == 2
    assert any("jev_wrong_at_gate" in r for r in out["reasons"])


def test_evaluate_hypothesis_in_progress_when_baseline_missing():
    episodes = [
        _episode("EP57", 6000.0, 10.0), _episode("EP58", 5000.0, 20.0),
        _episode("EP59", 4000.0, 30.0), _episode("EP60", 3000.0, 40.0),
    ]
    out = lib.evaluate_hypothesis(episodes, baseline_tokens_per_min=None)
    assert out["verdict"] == "IN_PROGRESS"


# ─────────────────────────────────────────────────────────────── report.md

def test_format_delta_up_down_flat_and_missing():
    assert lib.format_delta(10.0, 8.0) == "↑2.0"
    assert lib.format_delta(8.0, 10.0) == "↓2.0"
    assert lib.format_delta(10.0, 10.0) == "→0"
    assert lib.format_delta(10.0, None) == ""
    assert lib.format_delta(None, 10.0) == ""


def test_previous_row_none_for_first_row_in_file():
    rows = [{"episode": "REF-1300"}, {"episode": "EP57"}]
    assert lib.previous_row(rows, 0) is None
    assert lib.previous_row(rows, 1) == {"episode": "REF-1300"}


def test_render_scoreboard_md_smoke(tmp_path):
    rows = [dict(lib.REF_1300_ROW), {
        "episode": "EP57", "kind": "cut", "decisions_total": 175, "jev_applied": 8,
        "jev_applied_pct": 4.6, "jev_seconds": 12.3, "jev_frames": 369, "jev_wrong_at_gate": 0,
        "jev_usd": 0.004573, "jev_raw_accuracy": {"bl.beat[th]": {"n": 40, "correct": 20, "accuracy": 0.5}},
        "editor_new_tokens_per_video_min": None, "editor_total_tokens_per_video_min": None,
    }]
    verdict = {"verdict": "IN_PROGRESS", "n": 1, "of": 4, "reasons": ["1/4 episodes scored"]}
    md = lib.render_scoreboard_md(rows, verdict)
    assert "REF-1300" in md
    assert "EP57" in md
    assert "IN PROGRESS (1/4)" in md
    assert "Jev ตัดสินเอง 8 จาก 175 จุด" in md


# ──────────────────────────────────────────────────── baseline TSV parsing

def test_parse_baseline_episodes_tsv_blank_duration_is_none(tmp_path):
    p = tmp_path / "episodes.tsv"
    p.write_text("episode\ttask_id\tduration_seconds\nBL52\ttask-a\t128.27\nBL53\ttask-b\t\n", encoding="utf-8")
    rows = lib.parse_baseline_episodes_tsv(p)
    assert rows == [
        {"episode": "BL52", "task_id": "task-a", "duration_seconds": 128.27},
        {"episode": "BL53", "task_id": "task-b", "duration_seconds": None},
    ]
