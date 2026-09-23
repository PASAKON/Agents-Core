"""Tests for the zero-model BL TikTok watcher (task-c01b0b99).

Covers everything a browser is NOT needed for: the raw-JSON adapters (against
saved fixtures — tests/fixtures/bl_tiktok/), the new-since-last-run diff
logic, delta computation, ledger load/save, and the pure process_run()
orchestration step. BLTikTokBrowser (the only class that touches Playwright/
CDP) is never instantiated here — see its docstring in tools/bl_tiktok_watch.py
for why its selectors/endpoints are UNVERIFIED against the live DOM.

Run via:  pytest tests/test_bl_tiktok_watch.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import bl_tiktok_watch as watch

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bl_tiktok"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ── extract_video_stats_from_raw ────────────────────────────────────────────

def test_extract_video_stats_reads_every_video_in_the_fixture():
    rows = watch.extract_video_stats_from_raw(_load("content_list_run1.json"))
    assert len(rows) == 2
    assert rows[0] == {
        "id": "7291000000000000001", "views": 12000, "likes": 800,
        "comments": 12, "shares": 40, "saves": 5,
    }
    assert rows[1]["id"] == "7291000000000000002"


def test_extract_video_stats_raises_on_unrecognized_shape():
    with pytest.raises(watch.UnrecognizedResponseShape):
        watch.extract_video_stats_from_raw(_load("unrecognized_shape.json"))


# ── extract_comments_from_raw / extract_inbox_messages_from_raw ────────────

def test_extract_comments_reads_every_comment_and_normalizes_fields():
    rows = watch.extract_comments_from_raw(
        _load("comments_video1_run1.json"), video_id="7291000000000000001")
    assert len(rows) == 2
    assert rows[0]["id"] == "c-1001"
    assert rows[0]["video_id"] == "7291000000000000001"
    assert rows[0]["handle"] == "user_a"
    assert rows[0]["text"] == "เช็คโบรคยังไงคะ"


def test_extract_inbox_messages_reads_every_message():
    rows = watch.extract_inbox_messages_from_raw(_load("inbox_run1.json"))
    assert len(rows) == 2
    assert rows[0]["id"] == "m-9001"
    assert rows[0]["handle"] == "dm_user_x"


# ── new_items_since (the "new since last run" diff) ─────────────────────────

def test_new_items_since_excludes_already_seen_ids():
    run1 = watch.extract_comments_from_raw(_load("comments_video1_run1.json"), "v1")
    run2 = watch.extract_comments_from_raw(_load("comments_video1_run2.json"), "v1")
    seen = {c["id"] for c in run1}
    new = watch.new_items_since(seen, run2)
    assert [c["id"] for c in new] == ["c-1003"]


def test_new_items_since_empty_seen_set_returns_everything():
    rows = watch.extract_inbox_messages_from_raw(_load("inbox_run1.json"))
    assert watch.new_items_since(set(), rows) == rows


def test_new_items_since_returns_empty_when_nothing_new():
    rows = watch.extract_inbox_messages_from_raw(_load("inbox_run1.json"))
    seen = {r["id"] for r in rows}
    assert watch.new_items_since(seen, rows) == []


# ── video_deltas ─────────────────────────────────────────────────────────────

def test_video_deltas_first_ever_sighting_equals_raw_stat():
    curr = watch.extract_video_stats_from_raw(_load("content_list_run1.json"))
    deltas = watch.video_deltas({}, curr)
    assert deltas["7291000000000000001"] == {
        "views": 12000, "likes": 800, "comments": 12, "shares": 40, "saves": 5}


def test_video_deltas_computes_difference_from_previous_run():
    run1 = watch.extract_video_stats_from_raw(_load("content_list_run1.json"))
    run2 = watch.extract_video_stats_from_raw(_load("content_list_run2.json"))
    prev = {row["id"]: row for row in run1}
    deltas = watch.video_deltas(prev, run2)
    assert deltas["7291000000000000001"] == {
        "views": 1204, "likes": 38, "comments": 2, "shares": 1, "saves": 0}
    # unseen before this run -> delta equals its raw stat, not a spurious jump
    assert deltas["7291000000000000003"]["views"] == 900
    # unchanged video -> all-zero delta
    assert deltas["7291000000000000002"] == {
        "views": 0, "likes": 0, "comments": 0, "shares": 0, "saves": 0}


# ── ledger I/O ───────────────────────────────────────────────────────────────

def test_load_state_missing_file_returns_empty_defaults(tmp_path):
    state = watch.load_state(tmp_path / "nope.json")
    assert state == {"videos": {}, "seen_comment_ids": [], "seen_dm_ids": [], "last_run_at": None}


def test_save_state_then_load_state_roundtrips(tmp_path):
    path = tmp_path / "state.json"
    state = {"videos": {"v1": {"views": 10}}, "seen_comment_ids": ["c-1"],
              "seen_dm_ids": [], "last_run_at": "2026-09-23T16:00:00+07:00"}
    watch.save_state(path, state)
    assert watch.load_state(path) == state


def test_save_state_leaves_no_tmp_file_behind(tmp_path):
    path = tmp_path / "state.json"
    watch.save_state(path, {"videos": {}, "seen_comment_ids": [], "seen_dm_ids": [], "last_run_at": None})
    assert not path.with_suffix(".json.tmp").exists()
    assert path.exists()


def test_append_events_writes_one_json_object_per_line(tmp_path):
    path = tmp_path / "events.jsonl"
    watch.append_events(path, [{"type": "comment", "id": "c-1"}, {"type": "dm", "id": "m-1"}])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"type": "comment", "id": "c-1"}


def test_append_events_appends_across_multiple_calls(tmp_path):
    path = tmp_path / "events.jsonl"
    watch.append_events(path, [{"type": "comment", "id": "c-1"}])
    watch.append_events(path, [{"type": "comment", "id": "c-2"}])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_append_events_with_empty_list_is_a_noop(tmp_path):
    path = tmp_path / "events.jsonl"
    watch.append_events(path, [])
    assert not path.exists()


# ── process_run (the pure orchestration step) ───────────────────────────────

def test_process_run_first_ever_run_reports_every_comment_and_dm_as_new():
    videos = watch.extract_video_stats_from_raw(_load("content_list_run1.json"))
    comments = watch.extract_comments_from_raw(_load("comments_video1_run1.json"), videos[0]["id"])
    inbox = watch.extract_inbox_messages_from_raw(_load("inbox_run1.json"))
    state = watch.load_state(Path("/nonexistent/for/this/test"))

    new_state, summary, events = watch.process_run(
        videos, {videos[0]["id"]: comments}, inbox, state, run_at="2026-09-23T16:00:00+07:00")

    assert len(new_state["videos"]) == 2
    assert set(new_state["seen_comment_ids"]) == {"c-1001", "c-1002"}
    assert set(new_state["seen_dm_ids"]) == {"m-9001", "m-9002"}
    assert len(events) == 4  # 2 comments + 2 dms
    assert "New comments: 2" in summary
    assert "New DMs: 2" in summary


def test_process_run_second_run_only_reports_the_new_comment():
    vid = "7291000000000000001"
    run1_comments = watch.extract_comments_from_raw(_load("comments_video1_run1.json"), vid)
    run2_comments = watch.extract_comments_from_raw(_load("comments_video1_run2.json"), vid)
    videos1 = watch.extract_video_stats_from_raw(_load("content_list_run1.json"))
    videos2 = watch.extract_video_stats_from_raw(_load("content_list_run2.json"))

    state, _, _ = watch.process_run(videos1, {vid: run1_comments}, [], watch.load_state(Path("/nope")),
                                     run_at="2026-09-23T15:00:00+07:00")
    new_state, summary, events = watch.process_run(
        videos2, {vid: run2_comments}, [], state, run_at="2026-09-23T16:00:00+07:00")

    assert len(events) == 1
    assert events[0]["id"] == "c-1003"
    assert "New comments: 1" in summary
    # earlier comments must not resurface as "new" on the second run
    assert "c-1001" not in summary
    # video deltas must reflect the second run's changes, not the first's
    assert "views +1204" in summary


def test_process_run_no_new_comments_or_dms_reports_zero():
    videos = watch.extract_video_stats_from_raw(_load("content_list_run1.json"))
    comments = watch.extract_comments_from_raw(_load("comments_video1_run1.json"), videos[0]["id"])
    state, _, _ = watch.process_run(videos, {videos[0]["id"]: comments}, [], watch.load_state(Path("/nope")))
    new_state, summary, events = watch.process_run(videos, {videos[0]["id"]: comments}, [], state)
    assert events == []
    assert "New comments: 0" in summary
    assert "New DMs: 0" in summary


# ── status_summary ───────────────────────────────────────────────────────────

def test_status_summary_missing_ledger(tmp_path):
    assert "empty or not found" in watch.status_summary(tmp_path / "nope.json")


def test_status_summary_reports_counts(tmp_path):
    path = tmp_path / "state.json"
    watch.save_state(path, {
        "videos": {"v1": {}, "v2": {}},
        "seen_comment_ids": ["c-1", "c-2", "c-3"],
        "seen_dm_ids": ["m-1"],
        "last_run_at": "2026-09-23T16:00:00+07:00",
    })
    out = watch.status_summary(path)
    assert "2 videos tracked" in out
    assert "comments seen: 3" in out
    assert "dms seen: 1" in out
