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
