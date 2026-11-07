"""Unit tests for 100% AGY Project Head Brain (`tools/ph_brain.py`)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import ph_brain


@pytest.fixture(autouse=True)
def isolated_ph_hub(monkeypatch, tmp_path):
    from lib import db
    monkeypatch.delenv('ORG_DB_URL', raising=False)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'tasks.db')
    monkeypatch.setattr(ph_brain.ph_state, 'host_name', lambda: 'contabo')
    monkeypatch.setattr(ph_brain.ph_state, 'require_hub', lambda: None)
    ph_brain.ph_state.init()


def _write_snapshot(tmp_path: Path, agy_claude_weekly: float, agy_gemini_weekly: float = 0.96) -> Path:
    snap = tmp_path / "quota-snapshot.json"
    snap.write_text(
        json.dumps(
            {
                "buckets": {
                    "claude": {"weekly_remaining": 0.0, "daily_remaining": 1.0},
                    "agy-claude": {"weekly_remaining": agy_claude_weekly, "daily_remaining": agy_claude_weekly},
                    "agy-gemini": {"weekly_remaining": agy_gemini_weekly, "daily_remaining": agy_gemini_weekly},
                }
            }
        ),
        encoding="utf-8",
    )
    return snap


def test_select_model_chain_prefers_opus_when_agy_claude_available(tmp_path):
    snap = _write_snapshot(tmp_path, agy_claude_weekly=0.94, agy_gemini_weekly=0.96)
    chain = ph_brain.select_model_chain(snapshot_path=snap)
    assert chain[0] == "claude-opus-5-5-high"
    assert "gemini-4-argon-high" in chain


def test_select_model_chain_falls_back_to_argon_when_agy_claude_exhausted(tmp_path):
    snap = _write_snapshot(tmp_path, agy_claude_weekly=0.0, agy_gemini_weekly=0.96)
    chain = ph_brain.select_model_chain(snapshot_path=snap)
    assert chain[0] == "gemini-4-argon-high"


def test_run_turn_persists_conversation_and_auto_falls_back_on_limit(monkeypatch, tmp_path):
    snap = _write_snapshot(tmp_path, agy_claude_weekly=0.94, agy_gemini_weekly=0.96)
    brains_dir = tmp_path / "ph-brains"
    calls = []

    def fake_invoke(prompt, *, model, conversation_id=None, add_dirs=None, mode="accept-edits", timeout_s=600, agy_bin=None):
        calls.append({"prompt": prompt, "model": model, "conversation_id": conversation_id})
        if len(calls) == 1:
            return {
                "ok": True,
                "returncode": 0,
                "model": model,
                "conversation_id": "11111111-2222-3333-4444-555555555555",
                "response": "Turn 1 planned with Opus 5.5",
                "limit_hit": None,
                "raw_stdout": "",
                "raw_stderr": "",
            }
        if len(calls) == 2 and model == "claude-opus-5-5-high":
            # Simulate mid-flight quota exhaustion on Opus 5.5
            return {
                "ok": False,
                "returncode": 1,
                "model": model,
                "conversation_id": conversation_id,
                "response": "You have exhausted your quota on this model.",
                "limit_hit": "you have exhausted your quota on this model",
                "raw_stdout": "You have exhausted your quota on this model.",
                "raw_stderr": "",
            }
        return {
            "ok": True,
            "returncode": 0,
            "model": model,
            "conversation_id": conversation_id,
            "response": "Turn 2 seamlessly continued with Argon High on the same conversation",
            "limit_hit": None,
            "raw_stdout": "",
            "raw_stderr": "",
        }

    monkeypatch.setattr(ph_brain, "invoke_agy", fake_invoke)

    # Turn 1: starts with claude-opus-5-5-high
    r1 = ph_brain.run_turn(
        ph_id="7cf12345",
        project="VideoPipeline",
        lane="cmo",
        owner="cmo-a1b2c3d4",
        message="Plan 95-shot storyboard",
        brains_dir=brains_dir,
        snapshot_path=snap,
    )
    assert r1["ok"] is True
    assert r1["model_used"] == "claude-opus-5-5-high"
    assert r1["conversation_id"] == "11111111-2222-3333-4444-555555555555"
    assert r1.get("fallback_triggered") is False
    assert r1["claude_code_tokens_used"] == 0

    # Turn 2: Opus hits quota mid-flight -> automatically retries on same conversation_id with Argon High
    r2 = ph_brain.run_turn(
        ph_id="7cf12345",
        message="Continue shot 45-95 transitions",
        brains_dir=brains_dir,
        snapshot_path=snap,
    )
    assert r2["ok"] is True
    assert r2["model_used"] == "gemini-4-argon-high"
    assert r2["conversation_id"] == "11111111-2222-3333-4444-555555555555"
    assert r2.get("fallback_triggered") is True
    assert r2["turn_count"] == 2
    assert r2["claude_code_tokens_used"] == 0

    # Verify both Turn 2 attempts passed the exact same conversation_id from Turn 1
    assert calls[1]["conversation_id"] == "11111111-2222-3333-4444-555555555555"
    assert calls[2]["conversation_id"] == "11111111-2222-3333-4444-555555555555"
    assert calls[2]["model"] == "gemini-4-argon-high"

    saved = ph_brain.load_brain_state("7cf12345", brains_dir=brains_dir)
    assert saved["active_model"] == "gemini-4-argon-high"
    assert len(saved["fallback_events"]) == 1
    assert saved["fallback_events"][0]["from_model"] == "claude-opus-5-5-high"
    assert saved["fallback_events"][0]["to_model"] == "gemini-4-argon-high"


def test_ensure_browser_agy_brief_passes_route_class_for():
    from tools import quota, route
    cfg = quota.load_plans()
    raw = "Check Higgsfield generation queue and take a screenshot."
    formatted = ph_brain.ensure_browser_agy_brief(raw)
    assert "http://127.0.0.1:9281" in formatted
    assert "tools/agy_browse.py" in formatted
    assert route.class_for("browser_operator", formatted, cfg) == "browser_agy"

    res = ph_brain.delegate_from_ph(
        ph_id="7cf12345",
        project="VideoPipeline",
        role="browser_operator",
        title="Poll Higgsfield queue",
        brief=raw,
        dry_run=True,
    )
    assert res["runner"] == "agy"
    assert res["runner_model"] == "gemini-3.8-flash-high"



def test_invoke_agy_runs_in_plan_mode_and_returns_on_timeout(monkeypatch):
    monkeypatch.setattr(ph_brain, '_IN_TURN', type('Guard', (), {'get': lambda self: True})())
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        raise ph_brain.subprocess.TimeoutExpired(cmd, kw.get("timeout"))

    monkeypatch.setattr(ph_brain.subprocess, "run", fake_run)
    res = ph_brain.invoke_agy("plan it", model="gemini-4-argon-high", add_dirs=[], agy_bin="agy")
    cmd = seen["cmd"]
    assert cmd[cmd.index("--mode") + 1] == "plan"
    assert res["ok"] is False and res["timed_out"] is True
    assert "timed out after 240s" in res["response"]


def test_first_prompt_carries_the_planner_rule():
    p = ph_brain.build_initial_prompt(ph_id="58eb5246", project="run-watch", lane="cto", owner=None, message="hi")
    assert ph_brain.PLANNER_RULE in p


def test_run_turn_stops_the_chain_on_timeout(monkeypatch, tmp_path):
    snap = _write_snapshot(tmp_path, agy_claude_weekly=0.94, agy_gemini_weekly=0.96)
    calls = []

    def fake_invoke(prompt, *, model, **kw):
        calls.append(model)
        return {"ok": False, "returncode": None, "model": model, "conversation_id": None,
                "response": "brain timed out after 240s; retry once with a shorter message",
                "limit_hit": None, "timed_out": True, "raw_stdout": "", "raw_stderr": ""}

    monkeypatch.setattr(ph_brain, "invoke_agy", fake_invoke)
    r = ph_brain.run_turn(ph_id="58eb5246", project="run-watch", lane="cto", message="go",
                          brains_dir=tmp_path / "b", snapshot_path=snap)
    assert r["ok"] is False and "timed out" in r["response"]
    assert len(calls) == 1


@pytest.mark.parametrize("omit_fallback_key", [False, True])
def test_turn_cli_accepts_success_with_optional_fallback_metadata(monkeypatch, tmp_path, capsys, omit_fallback_key):
    monkeypatch.setattr(ph_brain, "BRAINS_DIR", tmp_path / "brains")
    monkeypatch.setattr(ph_brain, "QUOTA_SNAPSHOT", _write_snapshot(tmp_path, 0.94))
    calls = []

    def fake_invoke(prompt, *, model, **kwargs):
        calls.append(model)
        return {"ok": True, "returncode": 0, "conversation_id": "test-conversation",
                "response": "Plan ready", "limit_hit": None}

    monkeypatch.setattr(ph_brain, "invoke_agy", fake_invoke)
    real_run_turn = ph_brain.run_turn

    def result_without_optional_metadata(**kwargs):
        result = real_run_turn(**kwargs)
        # Simulate a legacy/alternate producer at the CLI result boundary.
        # Current successful run_turn results already include this key.
        result.pop("fallback_triggered")
        return result

    if omit_fallback_key:
        monkeypatch.setattr(ph_brain, "run_turn", result_without_optional_metadata)
    rc = ph_brain.main(["turn", "--ph", "999899b1", "--message", "go"])
    output = capsys.readouterr()
    assert (rc, output.err) == (0, "")
    assert "Plan ready" in output.out
    assert calls == [ph_brain.PRIMARY_MODEL]


@pytest.mark.parametrize("retry_first", [False, True])
def test_timeout_result_includes_fallback_metadata(monkeypatch, tmp_path, retry_first):
    calls = []

    def fake_invoke(prompt, *, model, **kwargs):
        calls.append(model)
        timed_out = not retry_first or len(calls) > 1
        return {"ok": False, "returncode": None if timed_out else 1,
                "conversation_id": None, "response": "timed out" if timed_out else "quota exceeded",
                "limit_hit": None if timed_out else "quota exceeded", "timed_out": timed_out}

    monkeypatch.setattr(ph_brain, "invoke_agy", fake_invoke)
    result = ph_brain.run_turn(ph_id="999899b1", message="go", brains_dir=tmp_path / "brains",
                               snapshot_path=_write_snapshot(tmp_path, 0.94))
    assert result["ok"] is False
    assert "fallback_triggered" in result
    assert result.get("fallback_triggered") is retry_first
    assert len(calls) == (2 if retry_first else 1)
