"""Tests for the SomPong lane-routing layer in runners/secretary_server.py
(task-3de56f59, CEO 2026-09-22 "SomPong routing ทำได้เลย", ADR 0029).

Lane selection (decide("sompong.route", ...) -> confidence gate -> lane)
lives inline inside run_secretary_turn (call chain: Handler.do_POST ->
run_secretary_turn -> decide("sompong.route") -> lane -> _run_claude_once
(profile)). scripts/test_secretary_server.py covers the light lane's argv
shape and the HTTP `model` surface; this file covers the routing matrix
itself -- outcome x profile x confidence -> lane -- plus the decision
ledger row and the sompong_lane usage-event side effects.

No network, no paid call, ever: tests/conftest.py's autouse fixture already
seals the paid decide() vars + the .env fallback for every test under
tests/ (task-a6129a75: a live .env with DECIDE_PROVIDER=jev set would
otherwise let a test make a real paid call). This file adds its own
decision-ledger redirect (same LEDGER_DIR pattern as tests/test_flow_shoot.py
/ tests/test_decide.py) and a secretary-session-db redirect, since
run_secretary_turn touches both.

Run via: pytest tests/test_sompong_route.py -q
(not in pytest.ini's default testpaths — run explicitly, same convention as
tests/test_flow_shoot.py / tests/test_decide.py.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import runners.secretary_server as ss  # noqa: E402
from lib import decision_ledger  # noqa: E402
from tools import decide as decide_mod  # noqa: E402
from tools import flow_shoot  # noqa: E402


@pytest.fixture(autouse=True)
def _redirect_decision_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(decision_ledger, "LEDGER_DIR", tmp_path / "decisions")


@pytest.fixture(autouse=True)
def _redirect_session_db(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "SESSION_DB_PATH", tmp_path / "secretary_sessions.db")


def _decision(choice, provider="openrouter", prob=1.0, error=None):
    """A tools.decide.Decision stand-in, same construction style as
    tests/test_decide_browser_sites.py's TestActionMappingGate."""
    probs = {} if choice is None else {choice: prob}
    return decide_mod.Decision(
        choice=choice, probs=probs, provider=provider,
        tokens_in=10, tokens_out=5, latency_ms=1.0, cost_usd=0.0001,
        counterfactual_usd=0.01, ledger_id="test-ledger-id",
        calibrated=(provider == "jev"), error=error,
    )


def _stub_run_claude_once(monkeypatch, result=None):
    """Stub ss._run_claude_once, recording every call's (prompt, session_id,
    profile, lane). Never a real subprocess -- same stub style
    scripts/test_secretary_server.py's running_server fixture uses."""
    calls: list[dict] = []
    default = (0, json.dumps({"session_id": "sess-x", "result": "ok",
                              "is_error": False}), "", False)

    def _fake(prompt, session_id, profile=ss.PROFILE_SECRETARY, lane=ss.LANE_FULL):
        calls.append({"prompt": prompt, "session_id": session_id,
                      "profile": profile, "lane": lane})
        return result if result is not None else default

    monkeypatch.setattr(ss, "_run_claude_once", _fake)
    return calls


# ---------------------------------------------------------------------------
# The routing matrix: outcome x profile x confidence -> lane.
# ---------------------------------------------------------------------------

def test_confident_rules_chitchat_routes_light(monkeypatch) -> None:
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("chitchat", provider="rules"))
    calls = _stub_run_claude_once(monkeypatch)
    ss.run_secretary_turn("ขอบคุณครับ", "conv-rules-chitchat", ss.PROFILE_SECRETARY)
    assert calls[0]["lane"] == ss.PROFILE_LIGHT


def test_confident_paid_chitchat_p095_routes_light(monkeypatch) -> None:
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("chitchat", provider="jev", prob=0.95))
    calls = _stub_run_claude_once(monkeypatch)
    ss.run_secretary_turn("anything", "conv-p95", ss.PROFILE_FAMILY)
    assert calls[0]["lane"] == ss.PROFILE_LIGHT


def test_unconfident_paid_chitchat_p06_routes_full(monkeypatch) -> None:
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("chitchat", provider="jev", prob=0.6))
    calls = _stub_run_claude_once(monkeypatch)
    ss.run_secretary_turn("anything", "conv-p60", ss.PROFILE_FAMILY)
    assert calls[0]["lane"] == ss.LANE_FULL


def test_choice_none_routes_full_lane(monkeypatch) -> None:
    """A provider that ran but returned an off-schema/empty answer (choice
    None) must never drive a lane change -- same as tools/flow_shoot.py's
    _decision_is_confident gate."""
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision(None, provider="openrouter"))
    calls = _stub_run_claude_once(monkeypatch)
    ss.run_secretary_turn("anything", "conv-none", ss.PROFILE_SECRETARY)
    assert calls[0]["lane"] == ss.LANE_FULL


def test_decide_raising_routes_full_lane(monkeypatch) -> None:
    def _boom(site, state):
        raise RuntimeError("boom")
    monkeypatch.setattr(ss.decide_tool, "decide", _boom)
    calls = _stub_run_claude_once(monkeypatch)
    ss.run_secretary_turn("anything", "conv-raise", ss.PROFILE_SECRETARY)
    assert calls[0]["lane"] == ss.LANE_FULL


def test_sompong_route_off_skips_decide_entirely_and_uses_full_lane(monkeypatch) -> None:
    monkeypatch.setenv("SOMPONG_ROUTE", "off")

    def _boom(site, state):
        raise AssertionError("decide() must not be called when SOMPONG_ROUTE=off")
    monkeypatch.setattr(ss.decide_tool, "decide", _boom)
    calls = _stub_run_claude_once(monkeypatch)
    ss.run_secretary_turn("ขอบคุณครับ", "conv-off", ss.PROFILE_FAMILY)
    assert calls[0]["lane"] == ss.LANE_FULL


def test_family_spam_returns_constant_reply_and_skips_model_call(monkeypatch) -> None:
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("spam", provider="rules"))

    def _boom(*a, **k):
        raise AssertionError("_run_claude_once must not be called for family spam")
    monkeypatch.setattr(ss, "_run_claude_once", _boom)

    content = ss.run_secretary_turn("https://example.com/x", "conv-spam-family",
                                    ss.PROFILE_FAMILY)
    assert content == ss.SPAM_REPLY_TEXT


def test_secretary_spam_routes_full_lane_never_treats_ceo_as_spam(monkeypatch) -> None:
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("spam", provider="rules"))
    calls = _stub_run_claude_once(monkeypatch)
    content = ss.run_secretary_turn("https://example.com/x", "conv-spam-secretary",
                                    ss.PROFILE_SECRETARY)
    assert calls[0]["lane"] == ss.LANE_FULL
    assert content == "ok"


@pytest.mark.parametrize("choice", ["order_for_cto", "order_for_other_cxo", "question"])
def test_other_confident_outcomes_route_full_lane_unchanged(monkeypatch, choice) -> None:
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision(choice, provider="rules"))
    calls = _stub_run_claude_once(monkeypatch)
    ss.run_secretary_turn("anything", f"conv-{choice}", ss.PROFILE_SECRETARY)
    assert calls[0]["lane"] == ss.LANE_FULL
    # full lane is byte-for-byte today's behaviour: the same prompt/session
    # reach _run_claude_once, nothing rewritten by the routing layer.
    assert calls[0]["prompt"] == "anything"
    assert calls[0]["profile"] == ss.PROFILE_SECRETARY


# ---------------------------------------------------------------------------
# Session continuity: the light lane must not read or grow a session.
# ---------------------------------------------------------------------------

def test_light_lane_ignores_existing_session_and_never_persists_one(monkeypatch) -> None:
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("chitchat", provider="rules"))
    ss.set_session_id("conv-light-session", "old-full-lane-session")
    calls = _stub_run_claude_once(monkeypatch, result=(
        0, json.dumps({"session_id": "new-light-session", "result": "ครับผม",
                      "is_error": False}), "", False))

    ss.run_secretary_turn("ขอบคุณ", "conv-light-session", ss.PROFILE_SECRETARY)

    assert calls[0]["session_id"] is None, "must never --resume an existing full-lane session"
    assert calls[0]["lane"] == ss.PROFILE_LIGHT
    assert ss.get_session_id("conv-light-session") == "old-full-lane-session", (
        "a light-lane run's own session_id must never be persisted, and the "
        "existing full-lane record must be left untouched")


# ---------------------------------------------------------------------------
# The decision ledger: one row per message, whatever the outcome.
# ---------------------------------------------------------------------------

def test_a_decide_row_is_written_per_message(monkeypatch) -> None:
    """Real decide() (rules provider only — free, no network), so this
    proves the row actually lands via the real call path, not a stub."""
    _stub_run_claude_once(monkeypatch)
    assert decision_ledger.read_month() == []

    ss.run_secretary_turn("ขอบคุณครับ", "conv-ledger-1", ss.PROFILE_FAMILY)
    rows = decision_ledger.read_month()
    assert len(rows) == 1
    assert rows[0]["site"] == "sompong.route"
    assert rows[0]["choice"] == "chitchat"
    assert rows[0]["provider"] == "rules"

    ss.run_secretary_turn("สั่งงาน CTO ทำ X ให้หน่อย", "conv-ledger-2", ss.PROFILE_SECRETARY)
    rows = decision_ledger.read_month()
    assert len(rows) == 2
    assert rows[1]["choice"] == "order_for_cto"


# ---------------------------------------------------------------------------
# sompong_lane usage telemetry (D2) — light lane only.
# ---------------------------------------------------------------------------

class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_sompong_lane_usage_event_logged_for_light_lane(monkeypatch) -> None:
    logged = []
    monkeypatch.setattr(ss.db, "get_conn", lambda: _FakeConn())
    monkeypatch.setattr(
        ss.db, "log_event",
        lambda conn, task_id, actor, kind, payload: logged.append((kind, payload)),
    )
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("chitchat", provider="rules"))
    _stub_run_claude_once(monkeypatch, result=(
        0, json.dumps({"session_id": "sess-light", "result": "โอเคครับผม",
                      "is_error": False,
                      "usage": {"input_tokens": 123, "output_tokens": 45}}),
        "", False))

    content = ss.run_secretary_turn("โอเค", "conv-usage-light", ss.PROFILE_FAMILY)

    assert content == "โอเคครับผม"
    assert len(logged) == 1
    kind, payload = logged[0]
    assert kind == "sompong_lane"
    assert payload["lane"] == ss.PROFILE_LIGHT
    assert payload["profile"] == ss.PROFILE_FAMILY
    assert payload["tokens_in"] == 123
    assert payload["tokens_out"] == 45


def test_sompong_lane_usage_event_not_logged_for_full_lane(monkeypatch) -> None:
    logged = []
    monkeypatch.setattr(ss.db, "log_event", lambda *a, **k: logged.append(a))
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("order_for_cto", provider="rules"))
    _stub_run_claude_once(monkeypatch)

    ss.run_secretary_turn("สั่งงาน CTO ทำ X", "conv-usage-full", ss.PROFILE_SECRETARY)

    assert logged == []


def test_light_lane_usage_event_failure_is_non_fatal(monkeypatch) -> None:
    """A DB hiccup while logging telemetry must never break a turn that
    already has its answer (best-effort logging, matches
    tools/skill_objection.py's _add_lungnote_todo fail-open convention)."""
    def _boom():
        raise RuntimeError("db unavailable")
    monkeypatch.setattr(ss.db, "get_conn", _boom)
    monkeypatch.setattr(ss.decide_tool, "decide",
                        lambda site, state: _decision("chitchat", provider="rules"))
    _stub_run_claude_once(monkeypatch, result=(
        0, json.dumps({"session_id": "sess-light2", "result": "ครับผม",
                      "is_error": False}), "", False))

    content = ss.run_secretary_turn("โอเค", "conv-usage-fail", ss.PROFILE_SECRETARY)
    assert content == "ครับผม"


# ---------------------------------------------------------------------------
# _decision_is_confident parity — must agree byte-for-byte with the other
# duplicated copies of this gate (tools/flow_shoot.py, scripts/higgsfield/
# gen_loop.py — tools/decide.py itself is out of this task's declared
# touch surface, same reasoning as tests/test_decide_browser_sites.py's
# TestActionMappingGate).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("d", [
    _decision("chitchat", provider="rules"),
    _decision("chitchat", provider="jev", prob=0.95),
    _decision("chitchat", provider="jev", prob=0.4),
    _decision(None, provider="jev"),
])
def test_decision_is_confident_matches_flow_shoot_gate(d) -> None:
    assert ss._decision_is_confident(d) == flow_shoot._decision_is_confident(d)
