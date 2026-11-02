"""Unit tests for 100% AGY Project Head Brain (`tools/ph_brain.py`)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import ph_brain


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
    assert r1["fallback_triggered"] is False
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
    assert r2["fallback_triggered"] is True
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
