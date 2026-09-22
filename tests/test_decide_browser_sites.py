"""Tests for the two browser decision sites (task-b8a9a714):
config/decisions/browser.page_state.yaml and
config/decisions/browser.moderation_action.yaml.

Covers: the measured strings from google-flow-ops SKILL.md,
higgsfield-unlimited-gen SKILL.md and tools/flow_shoot.py's is_refusal_text
resolve to the expected `choice` via the free rules provider (no network,
no paid call — same env-stripping convention as tests/test_decide.py); and
the conservative action-mapping gate duplicated in tools/flow_shoot.py and
scripts/higgsfield/gen_loop.py (`_decision_is_confident`) refuses to treat
anything softer than a rule (prob 1.0) or >=0.9 confidence as actionable.

Run via: pytest tests/test_decide_browser_sites.py -q
(not in pytest.ini's default testpaths — run explicitly, same convention as
tests/test_flow_shoot.py / tests/test_decide.py.)
"""
from __future__ import annotations

import pytest

from lib import decision_ledger
from scripts.higgsfield import gen_loop
from tools import decide as decide_mod
from tools import flow_shoot


@pytest.fixture(autouse=True)
def _redirect_ledger(tmp_path, monkeypatch):
    # Same pattern as tests/test_decide.py: point the module-global at a
    # tmp dir so no test here ever touches the real state/decisions/ ledger.
    monkeypatch.setattr(decision_ledger, "LEDGER_DIR", tmp_path / "decisions")


@pytest.fixture(autouse=True)
def _clean_decide_env(monkeypatch):
    for var in ("DECIDE_PROVIDER", "OPENROUTER_API_KEY", "DECIDE_BUDGET_USD",
                "JEV_API_KEY", "JEV_API_URL"):
        monkeypatch.delenv(var, raising=False)


# ── browser.page_state: measured strings -> expected choice ────────────────

# Verbatim from google-flow-ops SKILL.md § "A policy refusal comes from the
# DIALOGUE" / tools/flow_shoot.py:149 is_refusal_text's own two patterns.
FLOW_REFUSAL_CARD = (
    "ล้มเหลว\n"
    "การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่นหรือส่งความคิดเห็น\n"
    "ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้"
)


def test_flow_refusal_card_is_moderated():
    d = decide_mod.decide("browser.page_state", FLOW_REFUSAL_CARD)
    assert d.choice == "moderated"
    assert d.provider == "rules"
    assert d.probs == {"moderated": 1.0}


def test_higgsfield_generate_button_enabled_is_idle():
    # higgsfield-unlimited-gen SKILL.md § HARD rule 2's button-state table:
    # bare "Generate" or "Unlimited ... 0" (struck price), not disabled ->
    # nothing in flight, Unlimited correctly applied. This is the exact
    # framing gen_loop.extract_state()/flow_shoot.extract_state() produce.
    state = 'button="Generate" disabled=false'
    d = decide_mod.decide("browser.page_state", state)
    assert d.choice == "idle"
    assert d.provider == "rules"

    state_unlimited = 'button="Unlimited 140 0" disabled=false'
    d2 = decide_mod.decide("browser.page_state", state_unlimited)
    assert d2.choice == "idle"


def test_higgsfield_generating_text_is_generating():
    d = decide_mod.decide("browser.page_state", 'button="Generating..." disabled=true')
    assert d.choice == "generating"


def test_sign_in_text_is_signed_out():
    # google-flow-ops SKILL.md § "Mid-session Google sign-out": a bare
    # "Sign in" control means the session is gone.
    d = decide_mod.decide("browser.page_state", "Sign in")
    assert d.choice == "signed_out"

    # Higgsfield's own indicator (gen_loop.extract_state()'s literal marker
    # text for its live-verified .hfnav-auth-login selector).
    d2 = decide_mod.decide("browser.page_state", "sign in required (not logged in)")
    assert d2.choice == "signed_out"


def test_higgsfield_rate_limit_toast_is_rate_limited():
    # higgsfield-unlimited-gen SKILL.md § HARD rule 4's concurrency toast —
    # "not a real block", same bucket as an HTTP 429.
    d = decide_mod.decide("browser.page_state", "1 unlimited generation at a time")
    assert d.choice == "rate_limited"


def test_unknown_text_has_no_confident_rule_match():
    # "unknown" is browser.page_state.yaml's own option meaning "None of the
    # above rules matched" — with no paid provider configured (the default,
    # safe state) that resolves to choice=None, not the literal string
    # "unknown"; a caller's own action-mapping gate is what should then
    # treat this as "stop, don't guess" (see TestActionMappingGate below).
    d = decide_mod.decide("browser.page_state", "the quick brown fox jumps over nothing relevant")
    assert d.choice is None
    assert "no rule matched" in (d.error or "")


# ── browser.moderation_action: measured strings -> expected choice ─────────

def test_face_ip_scanner_text_is_escalate_ceo():
    # higgsfield-unlimited-gen SKILL.md: "the same automated Face/IP scanner
    # that terminally killed three healthy plates in one day" — human call
    # only, never auto-retry.
    d = decide_mod.decide("browser.moderation_action", "Face/IP scanner flagged this clip for resemblance")
    assert d.choice == "escalate_ceo"
    assert d.provider == "rules"


def test_rights_verification_banner_is_escalate_ceo():
    d = decide_mod.decide("browser.moderation_action", "Rights verification required")
    assert d.choice == "escalate_ceo"
    d2 = decide_mod.decide("browser.moderation_action", 'button="Confirm Rights" disabled=false')
    assert d2.choice == "escalate_ceo"


def test_copyright_text_is_rewrite_chips_not_rewrite_dialogue():
    # NOTE: the task brief's own Tests section lists "copyright text ->
    # rewrite_dialogue", but config/decisions/browser.moderation_action.yaml
    # (landed by T1, task-2a29d27e) maps copyright/IP/trademark to
    # rewrite_chips, whose own `meaning` is explicit: "rewrite the
    # Element/chip, NOT the dialogue." Copyright is a flag on REFERENCE
    # MATERIAL, not the spoken line, so rewrite_chips is the semantically
    # correct mapping — this test follows the landed, correct yaml rather
    # than the brief's apparent typo (flagged in REPORT.md's Skill learning
    # section).
    d = decide_mod.decide("browser.moderation_action", "This clip was flagged for copyright")
    assert d.choice == "rewrite_chips"


def test_flow_policy_refusal_text_is_rewrite_dialogue():
    d = decide_mod.decide("browser.moderation_action", FLOW_REFUSAL_CARD)
    assert d.choice == "rewrite_dialogue"


def test_rate_limit_text_is_retry_same():
    d = decide_mod.decide("browser.moderation_action", "slot busy, too many requests")
    assert d.choice == "retry_same"


def test_unknown_moderation_text_has_no_confident_rule_match():
    d = decide_mod.decide("browser.moderation_action", "completely unrelated text")
    assert d.choice is None


# ── action-mapping gate: prob < 0.9 -> not actionable, no submit ───────────
# tools/flow_shoot.py's and scripts/higgsfield/gen_loop.py's
# _decision_is_confident() are duplicated (tools/decide.py is out of this
# task's declared touch surface) but must agree byte-for-byte on behaviour.

@pytest.mark.parametrize("confident_fn", [
    flow_shoot._decision_is_confident,
    gen_loop._decision_is_confident,
])
class TestActionMappingGate:
    def test_rules_provider_is_always_actionable(self, confident_fn):
        d = decide_mod.decide("browser.page_state", FLOW_REFUSAL_CARD)
        assert d.provider == "rules"
        assert confident_fn(d) is True

    def test_high_confidence_paid_choice_is_actionable(self, confident_fn):
        d = decide_mod.Decision(
            choice="moderated", probs={"moderated": 0.95}, provider="openrouter",
            tokens_in=10, tokens_out=5, latency_ms=1.0, cost_usd=0.0001,
            counterfactual_usd=0.001, ledger_id="x", calibrated=False, error=None,
        )
        assert confident_fn(d) is True

    def test_low_confidence_choice_is_not_actionable(self, confident_fn):
        d = decide_mod.Decision(
            choice="moderated", probs={"moderated": 0.4}, provider="openrouter",
            tokens_in=10, tokens_out=5, latency_ms=1.0, cost_usd=0.0001,
            counterfactual_usd=0.001, ledger_id="x", calibrated=False, error=None,
        )
        assert confident_fn(d) is False

    def test_no_choice_is_not_actionable(self, confident_fn):
        d = decide_mod.Decision(
            choice=None, probs={}, provider="jev", tokens_in=0, tokens_out=0,
            latency_ms=0.0, cost_usd=0.0, counterfactual_usd=0.0, ledger_id="x",
            calibrated=False, error="jev: no key",
        )
        assert confident_fn(d) is False
