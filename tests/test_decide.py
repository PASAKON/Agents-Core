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
from pathlib import Path

import pytest
import yaml

from lib import decision_ledger
from tools import decide as decide_mod

REAL_SITES = ("browser.page_state", "browser.moderation_action",
              "sompong.route", "skill.route")

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Text that matches none of browser.page_state.yaml's rules patterns, so
# every ladder test here reaches the jev/openrouter rungs instead of
# resolving on the free `rules` provider.
NEUTRAL_STATE = "totally unrelated page text seen by the operator"


def _jev_fixture() -> dict:
    return json.loads((FIXTURES_DIR / "jev_decisions_response.json").read_text())


@pytest.fixture(autouse=True)
def _redirect_ledger(tmp_path, monkeypatch):
    # Same pattern as tests/test_flow_shoot.py's LOG_PATH redirect: point
    # the module-global at a tmp dir so no test ever touches the real
    # state/decisions/ ledger.
    monkeypatch.setattr(decision_ledger, "LEDGER_DIR", tmp_path / "decisions")


@pytest.fixture(autouse=True)
def _clean_decide_env(monkeypatch):
    for var in ("DECIDE_PROVIDER", "OPENROUTER_API_KEY", "DECIDE_BUDGET_USD",
                "DECIDE_JEV_MODEL", "JEV_API_KEY", "JEV_API_URL"):
        monkeypatch.delenv(var, raising=False)
    # `_env()` falls back to the gitignored repo-root .env when an env var
    # is unset — real for production, but a test asserting "no key set"
    # must never see the real .env (it has a live OPENROUTER_API_KEY +
    # DECIDE_PROVIDER=jev, task-a6129a75: two tests hit the LIVE API before
    # this line existed). Neutralize the fallback itself, not just the vars.
    monkeypatch.setattr(decide_mod, "_read_dotenv_var", lambda name: None)


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


def test_budget_refusal_counts_prior_jev_spend(monkeypatch):
    # First call spends jev's real (fixture) cost; the second call's
    # pre-flight estimate then pushes cumulative spend over a budget sized
    # to allow exactly one call — proving the gate sums across calls, not
    # just within one (task-a6129a75 deliverable 3).
    _enable_jev(monkeypatch, budget="0.00002")
    resp = _FakeResp(_jev_fixture())
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        return resp

    d1 = decide_mod.decide(
        "browser.page_state", NEUTRAL_STATE, provider="jev", _http_post=fake_post,
    )
    assert d1.choice == "moderated"
    assert d1.cost_usd == pytest.approx(1.995e-05)

    d2 = decide_mod.decide(
        "browser.page_state", NEUTRAL_STATE, provider="jev", _http_post=fake_post,
    )
    assert d2.choice is None
    assert "decision_budget_refused" in d2.error
    assert len(calls) == 1  # the second call never reached HTTP


# ── openrouter provider (monkeypatched HTTP client) ─────────────────────

class _FakeResp:
    def __init__(self, data: dict, status_code: int = 200):
        self._data = data
        self.status_code = status_code
        self.text = json.dumps(data)

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _enable_openrouter(monkeypatch, budget="10.00"):
    monkeypatch.setenv("DECIDE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("DECIDE_BUDGET_USD", budget)


def _enable_jev(monkeypatch, budget="10.00", model=None):
    monkeypatch.setenv("DECIDE_PROVIDER", "jev")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("DECIDE_BUDGET_USD", budget)
    if model:
        monkeypatch.setenv("DECIDE_JEV_MODEL", model)


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


# ── jev provider (real OpenRouter /api/alpha/decisions endpoint) ────────

def test_jev_via_decide_yields_null_choice_without_key(monkeypatch):
    monkeypatch.setenv("DECIDE_PROVIDER", "jev")
    d = decide_mod.decide("browser.page_state", "x", provider="jev")
    assert d.choice is None
    assert "OPENROUTER_API_KEY" in d.error


def test_jev_good_response_matches_measured_fixture(monkeypatch):
    # tests/fixtures/jev_decisions_response.json is the verbatim response
    # from the CTO's live probe, 2026-09-22 (research/2026-09-22-typesafe-
    # jev-system-one-models.md § "MEASURED 2026-09-22").
    _enable_jev(monkeypatch)
    resp = _FakeResp(_jev_fixture())
    d = decide_mod.decide(
        "browser.page_state", NEUTRAL_STATE,
        provider="jev", _http_post=lambda *a, **k: resp,
    )
    assert d.provider == "jev"
    assert d.calibrated is True
    assert d.choice == "moderated"
    assert d.cost_usd == pytest.approx(1.995e-05)  # usage.cost, exact — not the price-table estimate
    assert d.tokens_in == 475 and d.tokens_out == 80
    assert set(d.probs) == {
        "idle", "generating", "done", "moderated",
        "rate_limited", "signed_out", "error", "unknown",
    }


def test_jev_400_zod_error_choice_none_when_only_jev_allowed(monkeypatch):
    _enable_jev(monkeypatch)  # DECIDE_PROVIDER=jev -> openrouter/haiku not allowed
    jev_400 = _FakeResp({"error": {"message": "questions.browser.page_state.criteria: Required"}}, status_code=400)
    d = decide_mod.decide(
        "browser.page_state", NEUTRAL_STATE, _http_post=lambda *a, **k: jev_400,
    )
    assert d.choice is None
    assert "jev" in d.error and "openrouter" in d.error
    assert "criteria" in d.error or "HTTP 400" in d.error


def test_jev_model_id_overridable_via_decide_jev_model(monkeypatch):
    _enable_jev(monkeypatch, model="typesafe/jev-2.0-experimental")
    seen_payload = {}

    def fake_post(url, **kw):
        seen_payload.update(kw.get("json") or {})
        return _FakeResp(_jev_fixture())

    decide_mod.decide(
        "browser.page_state", NEUTRAL_STATE, provider="jev", _http_post=fake_post,
    )
    assert seen_payload["model"] == "typesafe/jev-2.0-experimental"


# ── ladder selection by DECIDE_PROVIDER value ───────────────────────────

def test_ladder_rules_setting_disables_all_paid_rungs(monkeypatch):
    monkeypatch.setenv("DECIDE_PROVIDER", "rules")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("DECIDE_BUDGET_USD", "10.00")

    def _boom(*a, **k):
        raise AssertionError("no paid rung may call HTTP when DECIDE_PROVIDER=rules")

    d = decide_mod.decide("browser.page_state", NEUTRAL_STATE, _http_post=_boom)
    assert d.choice is None
    assert "jev" in d.error and "openrouter" in d.error


def test_ladder_jev_setting_allows_only_jev(monkeypatch):
    _enable_jev(monkeypatch)
    resp = _FakeResp(_jev_fixture())
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        return resp

    d = decide_mod.decide("browser.page_state", NEUTRAL_STATE, _http_post=fake_post)
    assert d.provider == "jev"
    assert calls == [decide_mod.JEV_DECISIONS_URL]


def test_ladder_openrouter_setting_allows_jev_then_haiku_on_jev_failure(monkeypatch):
    _enable_openrouter(monkeypatch)  # DECIDE_PROVIDER=openrouter -> jev THEN haiku
    jev_400 = _FakeResp({"error": {"message": "bad request"}}, status_code=400)
    haiku_content = json.dumps({"choice": "generating", "confidence": 0.9})
    haiku_resp = _FakeResp({
        "choices": [{"message": {"content": haiku_content}}],
        "usage": {"prompt_tokens": 30, "completion_tokens": 4},
    })
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        return jev_400 if url == decide_mod.JEV_DECISIONS_URL else haiku_resp

    d = decide_mod.decide("browser.page_state", NEUTRAL_STATE, _http_post=fake_post)
    assert calls == [decide_mod.JEV_DECISIONS_URL, decide_mod.OPENROUTER_URL]
    assert d.provider == "openrouter"
    assert d.choice == "generating"


def test_provider_gate_error_names_decide_provider(monkeypatch):
    monkeypatch.delenv("DECIDE_PROVIDER", raising=False)
    with pytest.raises(decide_mod.ProviderUnavailable, match="DECIDE_PROVIDER"):
        decide_mod._provider_gate("jev")


# ── env var fallback: os.environ -> gitignored repo-root .env ──────────

def test_env_prefers_os_environ_over_dotenv(monkeypatch):
    monkeypatch.setenv("SOME_DECIDE_VAR", "env-value")
    monkeypatch.setattr(decide_mod, "_read_dotenv_var", lambda name: "dotenv-value")
    assert decide_mod._env("SOME_DECIDE_VAR") == "env-value"


def test_env_falls_back_to_dotenv_when_unset(monkeypatch):
    monkeypatch.delenv("SOME_DECIDE_VAR", raising=False)
    monkeypatch.setattr(decide_mod, "_read_dotenv_var", lambda name: "dotenv-value")
    assert decide_mod._env("SOME_DECIDE_VAR") == "dotenv-value"


def test_env_empty_value_counts_as_absent(monkeypatch):
    monkeypatch.setenv("SOME_DECIDE_VAR", "")
    monkeypatch.setattr(decide_mod, "_read_dotenv_var", lambda name: None)
    assert decide_mod._env("SOME_DECIDE_VAR") is None


@pytest.mark.allow_dotenv
def test_read_dotenv_var_reads_tmp_env_file(tmp_path, monkeypatch):
    from lib import config as config_mod

    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "OPENROUTER_API_KEY=sk-test-tmp-only\nDECIDE_BUDGET_USD=5\n"
    )
    assert config_mod._read_dotenv_var("OPENROUTER_API_KEY") == "sk-test-tmp-only"
    assert config_mod._read_dotenv_var("DECIDE_BUDGET_USD") == "5"
    assert config_mod._read_dotenv_var("NO_SUCH_VAR") is None


def test_providers_yaml_has_jev_openrouter_price_entry():
    prices = decide_mod._provider_prices()
    entry = prices["openrouter"][decide_mod.DEFAULT_JEV_MODEL]
    assert entry["in"] == 0.042
    assert entry["out"] == 0.0


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
