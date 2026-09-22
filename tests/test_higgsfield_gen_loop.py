"""Tests for scripts/higgsfield/gen_loop.py's decide()-backed completion
poll (task-b8a9a714). Covers everything a browser is NOT needed for:
extract_state()'s JS-call shape, poll_for_result()'s moderated/signed_out/
error/generating/download classification, and the conservative
action-mapping gate (_decision_is_confident). No Playwright, no network, no
paid call — same env-stripping convention as tests/test_decide.py.

Run via: pytest tests/test_higgsfield_gen_loop.py -q
(not in pytest.ini's default testpaths — run explicitly, same convention as
tests/test_flow_shoot.py.)
"""
from __future__ import annotations

import pytest

from lib import decision_ledger
from scripts.higgsfield import gen_loop


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
    monkeypatch.setattr(gen_loop.time, "sleep", lambda _s: None)


class _FakeHiggsfieldPage:
    """state_text feeds extract_state()'s EXTRACT_STATE_JS call.
    video_urls_sequence feeds _hf_urls() -> video_urls(page)'s scan, one
    list per call (stays on the last entry once exhausted) — models history
    lazily revealing a newly-finished clip's hf_<timestamp> CDN url."""

    def __init__(self, state_text: str = "", video_urls_sequence=None):
        self.state_text = state_text
        self._urls_seq = list(video_urls_sequence or [[]])
        self._urls_idx = 0

    def evaluate(self, script):
        if script == gen_loop.EXTRACT_STATE_JS:
            return self.state_text
        if "querySelectorAll('video')" in script:
            urls = self._urls_seq[self._urls_idx]
            if self._urls_idx < len(self._urls_seq) - 1:
                self._urls_idx += 1
            return urls
        return None  # window.scrollTo(...) and anything else

    def wait_for_timeout(self, _ms):
        pass


# ── extract_state() ──────────────────────────────────────────────────────

def test_extract_state_returns_the_configured_text():
    page = _FakeHiggsfieldPage(state_text='button="Generate" disabled=false')
    assert gen_loop.extract_state(page) == 'button="Generate" disabled=false'


def test_extract_state_never_raises_on_a_broken_page():
    class _BoomPage:
        def evaluate(self, _script):
            raise RuntimeError("page closed")
    assert gen_loop.extract_state(_BoomPage()) == ""


# ── poll_for_result(): moderated / signed_out / error short-circuit ────────

def test_poll_for_result_face_ip_scanner_text_escalates():
    page = _FakeHiggsfieldPage(state_text="Face/IP scanner flagged this clip for resemblance")
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=5)
    assert result["status"] == "refusal"
    assert result["moderation_choice"] == "escalate_ceo"


def test_poll_for_result_rights_verification_banner_escalates():
    page = _FakeHiggsfieldPage(state_text='button="Confirm Rights" disabled=false')
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=5)
    assert result["status"] == "refusal"
    assert result["moderation_choice"] == "escalate_ceo"


def test_poll_for_result_signed_out_stops():
    page = _FakeHiggsfieldPage(state_text="sign in required (not logged in)")
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=5)
    assert result["status"] == "stopped"
    assert result["reason"] == "signed_out"


def test_poll_for_result_error_text_stops():
    page = _FakeHiggsfieldPage(state_text="Prompt is required")
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=5)
    assert result["status"] == "stopped"
    assert result["reason"] == "error"


# ── poll_for_result(): benign/uncertain states never stop a healthy run ────

def test_poll_for_result_generating_keeps_polling_to_timeout():
    page = _FakeHiggsfieldPage(state_text='button="Generating..." disabled=true')
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=0.001)
    assert result == {"status": "timeout"}


def test_poll_for_result_idle_button_keeps_polling_to_timeout():
    # A confident-but-benign "idle" read must not be treated as a hazard —
    # only moderated/signed_out/error short-circuit the wait.
    page = _FakeHiggsfieldPage(state_text='button="Generate" disabled=false')
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=0.001)
    assert result == {"status": "timeout"}


def test_poll_for_result_unknown_text_keeps_polling_to_timeout():
    page = _FakeHiggsfieldPage(state_text="nothing recognizable here")
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=0.001)
    assert result == {"status": "timeout"}


# ── poll_for_result(): the real completion signal (a new hf_ CDN url) ──────

def test_poll_for_result_returns_download_once_a_new_hf_timestamp_appears():
    page = _FakeHiggsfieldPage(
        state_text='button="Generating..." disabled=true',
        video_urls_sequence=[
            [],
            ["https://d111.cloudfront.net/hf_20260101_000000_a.mp4"],
        ],
    )
    result = gen_loop.poll_for_result(page, t0_max="", timeout_s=5)
    assert result == {"status": "download",
                       "url": "https://d111.cloudfront.net/hf_20260101_000000_a.mp4"}


def test_poll_for_result_ignores_a_url_no_newer_than_the_baseline():
    # t0_max already equals the only timestamp _hf_urls() will ever see —
    # this must NOT be treated as a new completion (it's the clip that was
    # already there before this Generate click).
    page = _FakeHiggsfieldPage(
        state_text="",
        video_urls_sequence=[["https://d1.cloudfront.net/hf_20260101_000000_a.mp4"]],
    )
    result = gen_loop.poll_for_result(page, t0_max="20260101_000000", timeout_s=0.001)
    assert result == {"status": "timeout"}


# ── action-mapping gate (duplicated from tools/flow_shoot.py) ──────────────

def test_decision_is_confident_matches_flow_shoots_behaviour():
    from tools import decide as decide_mod
    from tools import flow_shoot

    confident = decide_mod.Decision(
        choice="moderated", probs={"moderated": 1.0}, provider="rules",
        tokens_in=0, tokens_out=0, latency_ms=0.1, cost_usd=0.0,
        counterfactual_usd=0.01, ledger_id="x", calibrated=True, error=None,
    )
    unconfident = decide_mod.Decision(
        choice="moderated", probs={"moderated": 0.5}, provider="openrouter",
        tokens_in=10, tokens_out=5, latency_ms=1.0, cost_usd=0.0001,
        counterfactual_usd=0.001, ledger_id="x", calibrated=False, error=None,
    )
    assert gen_loop._decision_is_confident(confident) == flow_shoot._decision_is_confident(confident) is True
    assert gen_loop._decision_is_confident(unconfident) == flow_shoot._decision_is_confident(unconfident) is False
