"""Tests for tools/decide.py + lib/decision_ledger.py (task-2a29d27e).

No network, no paid call, ever — every openrouter/jev path here is either
gated off by env (the default, safe state) or exercised through an injected
`_http_post` fake. Run via:

    pytest tests/test_decide.py -q

(not in pytest.ini's default `testpaths` — run explicitly, same convention
as tests/test_flow_shoot.py.)
"""
from __future__ import annotations

import json

import pytest
import yaml

from lib import decision_ledger
from tools import decide as decide_mod

REAL_SITES = ("browser.page_state", "browser.moderation_action",
              "sompong.route", "skill.route")


@pytest.fixture(autouse=True)
def _redirect_ledger(tmp_path, monkeypatch):
    # Same pattern as tests/test_flow_shoot.py's LOG_PATH redirect: point
    # the module-global at a tmp dir so no test ever touches the real
    # state/decisions/ ledger.
    monkeypatch.setattr(decision_ledger, "LEDGER_DIR", tmp_path / "decisions")


@pytest.fixture(autouse=True)
def _clean_decide_env(monkeypatch):
    for var in ("DECIDE_PROVIDER", "OPENROUTER_API_KEY", "DECIDE_BUDGET_USD",
                "JEV_API_KEY", "JEV_API_URL"):
        monkeypatch.delenv(var, raising=False)


def _write_site(tmp_path, monkeypatch, name: str, cfg: dict) -> None:
    d = tmp_path / "sites"
    d.mkdir(exist_ok=True)
    (d / f"{name}.yaml").write_text(yaml.safe_dump(cfg))
    monkeypatch.setattr(decide_mod, "DECISIONS_DIR", d)


# ── rules provider, end-to-end ──────────────────────────────────────────

def test_rules_provider_matches_moderated_text_end_to_end():
    d = decide_mod.decide("browser.page_state", "ล้มเหลว: content policy violation")
    assert d.choice == "moderated"
    assert d.provider == "rules"
    assert d.cost_usd == 0.0
    assert d.calibrated is True
    assert d.probs == {"moderated": 1.0}


def test_rules_provider_no_match_falls_through_ladder(tmp_path, monkeypatch):
    _write_site(tmp_path, monkeypatch, "t.norule", {
        "site": "t.norule", "question": "q?",
        "options": [{"id": "a", "meaning": "a"}, {"id": "b", "meaning": "b"}],
        "provider_policy": "rules-only",
        "rules": [{"pattern": "zzz-no-match-zzz", "option": "a"}],
        "counterfactual": {},
    })
    d = decide_mod.decide("t.norule", "text that matches nothing")
    assert d.choice is None
    assert "no rule matched" in (d.error or "")


# ── config / validation errors ──────────────────────────────────────────

def test_unknown_site_refused():
    with pytest.raises(decide_mod.DecisionError, match="unknown decision site"):
        decide_mod.decide("no.such.site", "x")


def test_over_255_options_refused(tmp_path, monkeypatch):
    opts = [{"id": f"opt{i}", "meaning": "m"} for i in range(256)]
    _write_site(tmp_path, monkeypatch, "t.toobig", {
        "site": "t.toobig", "question": "q?", "options": opts,
        "provider_policy": "rules-only", "rules": [], "counterfactual": {},
    })
    with pytest.raises(decide_mod.DecisionError, match="255"):
        decide_mod.load_site("t.toobig")


# ── ledger ────────────────────────────────────────────────────────────

def test_ledger_row_written_per_call():
    decide_mod.decide("browser.page_state", "generating now")
    rows = decision_ledger.read_month()
    assert len(rows) == 1
    assert rows[0]["site"] == "browser.page_state"
    assert rows[0]["choice"] == "generating"


def test_ledger_row_written_on_total_failure():
    # rules-then-llm, no rule matches, both LLM rungs gated off by default
    # env -> the ladder exhausts every rung, choice stays None, and a row
    # is STILL written (never silently dropped).
    d = decide_mod.decide("browser.page_state", "completely unmatched text xyz")
    assert d.choice is None
    rows = decision_ledger.read_month()
    assert len(rows) == 1
    assert rows[0]["error"]
    assert "openrouter" in rows[0]["error"] and "jev" in rows[0]["error"]


# ── budget gate ──────────────────────────────────────────────────────────

def test_budget_refused_when_decide_budget_usd_is_zero(monkeypatch):
    monkeypatch.setenv("DECIDE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    # DECIDE_BUDGET_USD left unset -> defaults to 0 -> refused before any
    # HTTP call is even attempted (the fake would raise if it were reached).
    def _boom(*a, **k):
        raise AssertionError("HTTP must never be called when budget is 0")

    d = decide_mod.decide(
        "browser.page_state", "some ambiguous page text",
        provider="openrouter", _http_post=_boom,
    )
    assert d.choice is None
    assert "decision_budget_refused" in (d.error or "")
    rows = decision_ledger.read_month()
    assert len(rows) == 1
    assert "decision_budget_refused" in rows[0]["error"]


# ── openrouter provider (monkeypatched HTTP client) ─────────────────────

class _FakeResp:
    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _enable_openrouter(monkeypatch, budget="10.00"):
    monkeypatch.setenv("DECIDE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("DECIDE_BUDGET_USD", budget)


def test_openrouter_good_json_returns_choice(monkeypatch):
    _enable_openrouter(monkeypatch)
    content = json.dumps({"choice": "idle", "confidence": 0.87})
    resp = _FakeResp({
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 8},
    })
    d = decide_mod.decide(
        "browser.page_state", "ambiguous state text",
        provider="openrouter", _http_post=lambda *a, **k: resp,
    )
    assert d.choice == "idle"
    assert d.probs == {"idle": 0.87}
    assert d.provider == "openrouter"
    assert d.calibrated is False
    assert d.cost_usd > 0
    assert d.tokens_in == 120 and d.tokens_out == 8


def test_openrouter_bad_json_yields_null_choice(monkeypatch):
    _enable_openrouter(monkeypatch)
    resp = _FakeResp({"choices": [{"message": {"content": "not json at all"}}]})
    d = decide_mod.decide(
        "browser.page_state", "ambiguous state text",
        provider="openrouter", _http_post=lambda *a, **k: resp,
    )
    assert d.choice is None
    assert "bad/off-schema" in d.error


def test_openrouter_off_schema_choice_yields_null(monkeypatch):
    _enable_openrouter(monkeypatch)
    content = json.dumps({"choice": "not_a_real_option", "confidence": 0.5})
    resp = _FakeResp({"choices": [{"message": {"content": content}}]})
    d = decide_mod.decide(
        "browser.page_state", "ambiguous state text",
        provider="openrouter", _http_post=lambda *a, **k: resp,
    )
    assert d.choice is None
    assert "not in site options" in d.error


def test_openrouter_disabled_by_default_falls_through():
    # No DECIDE_PROVIDER / OPENROUTER_API_KEY set (autouse fixture clears
    # them) -> forcing provider="openrouter" explicitly still refuses.
    d = decide_mod.decide("browser.page_state", "x", provider="openrouter")
    assert d.choice is None
    assert "disabled" in d.error or "OPENROUTER_API_KEY" in d.error


# ── jev provider ─────────────────────────────────────────────────────────

def test_jev_raises_provider_unavailable_without_key():
    cfg = decide_mod.load_site("browser.page_state")
    with pytest.raises(decide_mod.ProviderUnavailable, match="JEV_API_KEY"):
        decide_mod._jev_provider(cfg, "some state")


def test_jev_via_decide_yields_null_choice_without_key():
    d = decide_mod.decide("browser.page_state", "x", provider="jev")
    assert d.choice is None
    assert "JEV_API_KEY" in d.error


# ── counterfactual arithmetic ─────────────────────────────────────────────

def test_counterfactual_arithmetic_matches_formula():
    cfg = {"counterfactual": {"images": 1, "big_model_tokens_out": 20}}
    usd, basis = decide_mod._counterfactual_usd(cfg, state_chars=400)
    prices = decide_mod._provider_prices()["counterfactual"]["claude-fable-5-1"]
    expected_tokens_in = 400 / 4 + 1 * 814
    expected = (expected_tokens_in / 1_000_000) * prices["in"] + (20 / 1_000_000) * prices["out"]
    assert usd == pytest.approx(expected)
    assert "ESTIMATE" in basis


def test_counterfactual_extra_input_chars_included():
    cfg = {"counterfactual": {"images": 0, "big_model_tokens_out": 0, "extra_input_chars": 1000}}
    usd, basis = decide_mod._counterfactual_usd(cfg, state_chars=0)
    prices = decide_mod._provider_prices()["counterfactual"]["claude-fable-5-1"]
    expected = (1000 / 4 / 1_000_000) * prices["in"]
    assert usd == pytest.approx(expected)
    assert "extra_input_chars=1000" in basis


# ── report ─────────────────────────────────────────────────────────────

def test_report_output_has_expected_columns():
    decide_mod.decide("browser.page_state", "generating")
    decide_mod.decide("browser.page_state", "ล้มเหลว อาจละเมิดนโยบาย")
    text = decide_mod.report_text()
    assert "ESTIMATE" in text
    for col in ("site", "calls", "provider_mix", "tokens_in", "tokens_out",
                "cost_usd", "counterfactual_usd", "saved_usd"):
        assert col in text
    assert "browser.page_state" in text


def test_report_empty_month_says_so():
    text = decide_mod.report_text("2099-01")
    assert "no decisions logged" in text


# ── the four shipped site yaml files ─────────────────────────────────────

@pytest.mark.parametrize("site", REAL_SITES)
def test_shipped_site_yaml_validates(site):
    cfg = decide_mod.load_site(site)
    assert cfg["provider_policy"] in decide_mod.LADDERS
    options = decide_mod._resolve_options(cfg)
    assert 0 < len(options) <= decide_mod.MAX_OPTIONS


def test_skill_route_resolves_real_org_skills():
    cfg = decide_mod.load_site("skill.route")
    options = decide_mod._resolve_options(cfg)
    ids = {o["id"] for o in options}
    assert "browser-operator" in ids
    assert "google-flow-ops" in ids


def test_extract_trigger_patterns_pulls_comma_clause():
    desc = "Some intro. Trigger on /foo, bar baz, and qux quux. Trailing text."
    patterns = decide_mod.extract_trigger_patterns(desc)
    assert "/foo" in patterns
    assert "bar baz" in patterns
    assert "qux quux" in patterns


def test_extract_trigger_patterns_empty_when_no_trigger_clause():
    assert decide_mod.extract_trigger_patterns("No trigger clause here.") == []


# ── max_state_chars truncation ───────────────────────────────────────────

def test_state_is_truncated_to_max_state_chars(tmp_path, monkeypatch):
    _write_site(tmp_path, monkeypatch, "t.trunc", {
        "site": "t.trunc", "question": "q?",
        "options": [{"id": "a", "meaning": "a"}],
        "max_state_chars": 5,
        "provider_policy": "rules-only",
        "rules": [{"pattern": "^abcde$", "option": "a"}],
        "counterfactual": {},
    })
    d = decide_mod.decide("t.trunc", "abcdefghij")
    assert d.choice == "a"  # only matches if truncated to exactly "abcde"


# ── MCP registration (both servers) ──────────────────────────────────────

def test_decide_registered_in_cto_mcp_server():
    from runners import cto_mcp_server as srv
    assert "decide" in srv.mcp._tool_manager._tools


def test_decide_registered_in_worker_mcp_server():
    from runners import worker_mcp_server as srv
    assert "decide" in srv.mcp._tool_manager._tools


def test_decide_registered_in_org_tools_registry():
    from lib import org_tools_registry as reg
    assert "decide" in reg.BY_NAME
