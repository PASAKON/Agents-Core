"""Tests for the BL TikTok CTA loop engine (task-8df13432).

Everything here runs against fake adapters and a tmp_path sqlite db — no
browser, no network. BLTikTokCTABrowser (the only class with real Playwright
calls) is never instantiated; see its UNVERIFIED docstring in
tools/bl_tiktok_cta.py for why.

Run via:  pytest tests/test_bl_tiktok_cta.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import bl_tiktok_cta as cta

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bl_tiktok_cta"


def _load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _pack(episode: str) -> dict:
    return cta.load_pack(FIXTURES, episode)


class FakeAdapters:
    """Records every call so tests can assert exactly what would have hit
    the real TikTok DOM. can_dm is driven by a simple handle->bool map;
    send_dm/reply_comment must NEVER be called in shadow mode."""

    def __init__(self, dmable: dict[str, bool] | None = None):
        self.dmable = dmable or {}
        self.can_dm_calls: list[str] = []
        self.send_dm_calls: list[tuple[str, str]] = []
        self.reply_comment_calls: list[tuple[str, str]] = []

    def can_dm(self, handle: str) -> bool:
        self.can_dm_calls.append(handle)
        return self.dmable.get(handle, False)

    def send_dm(self, handle: str, text: str) -> None:
        self.send_dm_calls.append((handle, text))

    def reply_comment(self, comment_id: str, text: str) -> None:
        self.reply_comment_calls.append((comment_id, text))


def _live_engine(tmp_path, adapters, **kwargs) -> cta.Engine:
    """Live mode with an instant no-op pace delay — used by the state-machine
    tests below, which assert on the OUTWARD adapter calls themselves (the
    dedicated shadow-mode tests separately assert those calls never happen)."""
    conn = cta.connect(tmp_path / "cta.sqlite")
    return cta.Engine(conn, FIXTURES, adapters, live=True, sleep_fn=lambda seconds: None, **kwargs)


def _engine(tmp_path, adapters, **kwargs) -> cta.Engine:
    conn = cta.connect(tmp_path / "cta.sqlite")
    return cta.Engine(conn, FIXTURES, adapters, **kwargs)


# ── keyword matching (incl. Thai spelling drift) ────────────────────────────

def test_match_keyword_exact_keyword_hit():
    pack = _pack("EP54")
    assert cta.match_keyword("อยากได้เช็ครีเบตค่ะ", pack) == "เช็ครีเบต"


def test_match_keyword_variant_with_spelling_drift():
    # เช็คโบรค (ค final) vs the pack's own variant เช็คโบรค written with ก:
    # exercise both directions of the ค/ก fold the brief calls out.
    pack = _pack("EP54")
    assert cta.match_keyword("เช็คโบรคยังไงคะ", pack) == "เช็คโบรค"
    assert cta.match_keyword("เช็กโบรกหน่อยครับ", pack) == "เช็คโบรค"


def test_match_keyword_tolerates_extra_spaces_and_emoji():
    pack = _pack("EP54")
    assert cta.match_keyword("เช็ก โบรก   หน่อยครับ 🙏😊", pack) == "เช็คโบรค"


def test_match_keyword_no_match_returns_none():
    pack = _pack("EP54")
    assert cta.match_keyword("คลิปนี้ตัดดีมาก", pack) is None


def test_match_keyword_EP55_variant():
    # EP55's own keyword (เช็กก่อนฝาก) folds to the same normalized form as
    # the commenter's spelling (เช็คก่อนฝาก) and is checked first, so it wins.
    pack = _pack("EP55")
    assert cta.match_keyword("เช็คก่อนฝาก   ค่ะ", pack) == "เช็กก่อนฝาก"


# ── safety_check: never_say + URL guard ─────────────────────────────────────

def test_safety_check_blocks_never_say_phrase():
    pack = _pack("EP54")
    ok, reason = cta.safety_check("เรารับประกันกำไรแน่นอนครับ", pack)
    assert ok is False
    assert "รับประกันกำไร" in reason


def test_safety_check_allows_url_already_present_in_pack():
    pack = _pack("EP54")
    ok, reason = cta.safety_check(pack["cta"]["dm_message"], pack)
    assert ok is True
    assert reason is None


def test_safety_check_blocks_url_not_in_pack():
    pack = _pack("EP54")
    ok, reason = cta.safety_check("ลิงก์ลับ https://evil.example.com/phish", pack)
    assert ok is False
    assert "evil.example.com" in reason


def test_safety_check_clean_text_passes():
    pack = _pack("EP54")
    ok, reason = cta.safety_check("สวัสดีครับ ขอบคุณที่ติดตามนะครับ", pack)
    assert ok is True
    assert reason is None


# ── state machine: comment path ──────────────────────────────────────────────

def test_comment_dmable_sends_dm_then_replies_comment(tmp_path):
    adapters = FakeAdapters(dmable={"user_a": True})
    engine = _live_engine(tmp_path, adapters)

    decision = engine.process_comment("EP54", {"id": "c-1001", "handle": "user_a", "text": "เช็คโบรคยังไงคะ"})

    assert decision.kind == "dm_sent"
    assert adapters.can_dm_calls == ["user_a"]
    assert adapters.send_dm_calls == [("user_a", _pack("EP54")["cta"]["dm_message"])]
    assert adapters.reply_comment_calls == [("c-1001", _pack("EP54")["cta"]["comment_reply_dm_sent"])]

    contact = cta.get_contact(engine.conn, "user_a")
    assert contact["status"] == "dm_sent"
    assert contact["source_episode"] == "EP54"
    assert contact["matched_keyword"] == "เช็คโบรค"


def test_comment_not_dmable_only_replies_with_invite(tmp_path):
    adapters = FakeAdapters(dmable={"user_a": False})
    engine = _live_engine(tmp_path, adapters)

    decision = engine.process_comment("EP54", {"id": "c-1001", "handle": "user_a", "text": "เช็คโบรคยังไงคะ"})

    assert decision.kind == "dm_invited"
    assert adapters.send_dm_calls == []
    assert adapters.reply_comment_calls == [("c-1001", _pack("EP54")["cta"]["comment_reply_dm_invite"])]

    contact = cta.get_contact(engine.conn, "user_a")
    assert contact["status"] == "dm_invited"


def test_comment_with_no_keyword_match_is_recorded_as_question_and_never_answered(tmp_path):
    adapters = FakeAdapters()
    engine = _engine(tmp_path, adapters)

    decision = engine.process_comment("EP54", {"id": "c-1003", "handle": "user_c", "text": "คลิปนี้ตัดดีมาก"})

    assert decision.kind == "question"
    assert adapters.can_dm_calls == []
    assert adapters.send_dm_calls == []
    assert adapters.reply_comment_calls == []
    assert cta.get_contact(engine.conn, "user_c") is None

    row = engine.conn.execute("SELECT * FROM questions WHERE comment_id = ?", ("c-1003",)).fetchone()
    assert row["handle"] == "user_c"


def test_repeat_comment_from_same_handle_is_skipped_no_double_delivery(tmp_path):
    adapters = FakeAdapters(dmable={"user_a": True})
    engine = _live_engine(tmp_path, adapters)

    first = engine.process_comment("EP54", {"id": "c-1001", "handle": "user_a", "text": "เช็คโบรคยังไงคะ"})
    second = engine.process_comment("EP54", {"id": "c-1004", "handle": "user_a", "text": "เช็คโบรคอีกรอบครับ"})

    assert first.kind == "dm_sent"
    assert second.kind == "duplicate"
    # exactly ONE dm/reply pair — the repeat must not trigger a second delivery
    assert len(adapters.send_dm_calls) == 1
    assert len(adapters.reply_comment_calls) == 1


# ── state machine: inbox path ────────────────────────────────────────────────

def test_inbox_from_known_dm_invited_contact_delivers_and_marks_delivered(tmp_path):
    adapters = FakeAdapters(dmable={"user_b": False})
    engine = _live_engine(tmp_path, adapters)
    engine.process_comment("EP54", {"id": "c-1002", "handle": "user_b", "text": "เช็คโบรคหน่อยครับ"})
    assert cta.get_contact(engine.conn, "user_b")["status"] == "dm_invited"

    decision = engine.process_inbox({"id": "m-9001", "handle": "user_b", "text": "ทักมาแล้วนะครับ"})

    assert decision.kind == "delivered"
    assert adapters.send_dm_calls == [("user_b", _pack("EP54")["cta"]["dm_message"])]
    assert cta.get_contact(engine.conn, "user_b")["status"] == "delivered"


def test_inbox_from_unknown_sender_routes_to_general_stub(tmp_path):
    adapters = FakeAdapters()
    engine = _engine(tmp_path, adapters)

    decision = engine.process_inbox({"id": "m-9002", "handle": "user_z", "text": "สวัสดีครับ อยากคุยด้วย"})

    assert decision.kind == "general"
    assert adapters.send_dm_calls == []
    assert cta.get_contact(engine.conn, "user_z")["status"] == "general"

    row = engine.conn.execute(
        "SELECT * FROM action_log WHERE action_type = 'route_auto_chat_stub'").fetchone()
    assert row["handle"] == "user_z"


def test_inbox_from_already_delivered_contact_does_not_redeliver(tmp_path):
    adapters = FakeAdapters(dmable={"user_b": False})
    engine = _live_engine(tmp_path, adapters)
    engine.process_comment("EP54", {"id": "c-1002", "handle": "user_b", "text": "เช็คโบรคหน่อยครับ"})
    engine.process_inbox({"id": "m-9001", "handle": "user_b", "text": "ทักมาแล้วนะครับ"})
    assert len(adapters.send_dm_calls) == 1

    # A second DM from the same, now-delivered contact must not re-deliver.
    decision = engine.process_inbox({"id": "m-9003", "handle": "user_b", "text": "ขอบคุณครับ"})
    assert decision.kind == "general"
    assert len(adapters.send_dm_calls) == 1


# ── never_say / URL guard blocks an action end-to-end ───────────────────────

def test_blocked_dm_message_is_never_sent_and_is_logged(tmp_path, monkeypatch):
    adapters = FakeAdapters(dmable={"user_a": True})
    engine = _engine(tmp_path, adapters)
    bad_pack = dict(_pack("EP54"))
    bad_pack["cta"] = dict(bad_pack["cta"])
    bad_pack["cta"]["dm_message"] = "เรารับประกันกำไรแน่นอนครับ"
    engine._pack_cache["EP54"] = bad_pack

    decision = engine.process_comment("EP54", {"id": "c-1001", "handle": "user_a", "text": "เช็คโบรคยังไงคะ"})

    assert decision.kind == "blocked"
    assert adapters.send_dm_calls == []
    assert adapters.reply_comment_calls == []
    # contact stays at the pre-send status, never a false 'dm_sent'
    assert cta.get_contact(engine.conn, "user_a")["status"] == "commented"

    row = engine.conn.execute(
        "SELECT * FROM action_log WHERE blocked = 1 AND handle = 'user_a'").fetchone()
    assert "never_say" in row["block_reason"]


# ── shadow mode: no outward adapter call, ever ──────────────────────────────

def test_shadow_mode_writes_planned_actions_and_never_calls_send_dm_or_reply_comment(tmp_path):
    adapters = FakeAdapters(dmable={"user_a": True, "user_d": False})
    engine = _engine(tmp_path, adapters, live=False)

    engine.process_comment("EP54", {"id": "c-1001", "handle": "user_a", "text": "เช็คโบรคยังไงคะ"})
    engine.process_comment("EP55", {"id": "c-2001", "handle": "user_d", "text": "เช็กก่อนฝากด้วยครับ"})

    # can_dm is a read-only check and IS allowed in shadow mode ...
    assert adapters.can_dm_calls == ["user_a", "user_d"]
    # ... but the two OUTWARD adapters must never fire.
    assert adapters.send_dm_calls == []
    assert adapters.reply_comment_calls == []

    planned = engine.conn.execute("SELECT * FROM planned_actions").fetchall()
    assert len(planned) == 3  # dm_send + comment_reply for user_a, comment_reply for user_d
    assert all(row["text"] for row in planned)

    modes = {row["mode"] for row in engine.conn.execute("SELECT DISTINCT mode FROM action_log")}
    assert modes == {"shadow"}


# ── daily cap (live mode only) ───────────────────────────────────────────────

def test_daily_cap_stops_live_actions_once_reached(tmp_path):
    adapters = FakeAdapters(dmable={"user_a": True, "user_b": True})
    engine = _engine(tmp_path, adapters, live=True, daily_cap=2,
                      sleep_fn=lambda seconds: None)

    # user_a is dm-able: costs 2 outward actions (dm_send + comment_reply) and
    # exactly fills the cap of 2.
    decision1 = engine.process_comment("EP54", {"id": "c-1001", "handle": "user_a", "text": "เช็คโบรคยังไงคะ"})
    assert decision1.kind == "dm_sent"
    assert len(adapters.send_dm_calls) == 1
    assert len(adapters.reply_comment_calls) == 1

    # user_b would need a 3rd outward action -> cap must stop it before any
    # adapter call for user_b.
    with pytest.raises(cta.DailyCapReached):
        engine.process_comment("EP54", {"id": "c-1005", "handle": "user_b", "text": "เช็คโบรคด้วยครับ"})

    assert len(adapters.send_dm_calls) == 1
    assert len(adapters.reply_comment_calls) == 1

    blocked_row = engine.conn.execute(
        "SELECT * FROM action_log WHERE blocked = 1 AND mode = 'live'").fetchone()
    assert "daily cap" in blocked_row["block_reason"]


def test_daily_cap_counts_only_today_and_only_live_unblocked_actions(tmp_path):
    conn = cta.connect(tmp_path / "cta.sqlite")
    cta.log_action(conn, mode="live", action_type="dm_send", handle="x", episode="EP54",
                    comment_id="c-1", text="hi", now="2026-09-22T10:00:00+07:00")
    cta.log_action(conn, mode="shadow", action_type="dm_send", handle="x", episode="EP54",
                    comment_id="c-2", text="hi", now="2026-09-23T10:00:00+07:00")
    cta.log_action(conn, mode="live", action_type="dm_send", handle="x", episode="EP54",
                    comment_id="c-3", text="hi", now="2026-09-23T10:00:00+07:00", blocked=True,
                    block_reason="daily cap 1 reached")
    cta.log_action(conn, mode="live", action_type="dm_send", handle="x", episode="EP54",
                    comment_id="c-4", text="hi", now="2026-09-23T11:00:00+07:00")

    assert cta.count_live_actions_today(conn, "2026-09-23") == 1
    assert cta.count_live_actions_today(conn, "2026-09-22") == 1


# ── pack loading ─────────────────────────────────────────────────────────────

def test_load_pack_missing_episode_raises():
    with pytest.raises(cta.PackNotFound):
        cta.load_pack(FIXTURES, "EP999")


# ── full shadow-mode run on fixture data (the report demo) ─────────────────

def test_shadow_run_on_fixture_data_produces_expected_summary(tmp_path):
    adapters = FakeAdapters(dmable={"user_a": True, "user_b": False, "user_d": False, "user_e": True})
    engine = _engine(tmp_path, adapters, live=False)

    comments_by_episode = {
        "EP54": _load_json("comments_ep54.json"),
        "EP55": _load_json("comments_ep55.json"),
    }
    inbox = _load_json("inbox_run1.json")

    comment_decisions, inbox_decisions = cta.run_batch(engine, comments_by_episode, inbox)
    summary = cta.format_summary("2026-09-23T09:00:00+07:00", comment_decisions, inbox_decisions, live=False)

    assert adapters.send_dm_calls == []
    assert adapters.reply_comment_calls == []

    assert "SHADOW" in summary
    assert "would DM @user_a (EP54)" in summary
    assert "would DM @user_e (EP55)" in summary
    assert "would invite @user_b (EP54)" in summary
    assert "would invite @user_d (EP55)" in summary
    assert "Unmatched comments (questions, not auto-answered): 1" in summary
    assert "Duplicate comments skipped (already tracked): 1" in summary  # user_a's second comment
    assert "would deliver to @user_b (EP54)" in summary
    assert "routed to auto-chat-mode STUB" in summary
    assert "@user_z" in summary
