"""Unit tests for 100% AGY Project Head Brain (`tools/ph_brain.py`)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import ph_brain


@pytest.fixture
def fake_codex(monkeypatch, tmp_path):
    binary = tmp_path / 'codex'
    log = tmp_path / 'codex-calls.jsonl'
    binary.write_text(f'''#!{sys.executable}
import json, sys
with open({str(log)!r}, 'a') as f:
    f.write(json.dumps(dict(argv=sys.argv[1:], prompt=sys.stdin.read())) + '\\n')
print(json.dumps(dict(type='thread.started', thread_id='codex-thread')))
print(json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='Plan ready'))))
print(json.dumps(dict(type='turn.completed')))
''')
    binary.chmod(0o755)
    monkeypatch.setenv('CODEX_BIN', str(binary))
    return log


def _fake_bin(tmp_path, name, body):
    b = tmp_path / name
    b.write_text(f'#!{sys.executable}\nimport json, sys\n' + body)
    b.chmod(0o755)
    return b


@pytest.fixture
def fake_claude(monkeypatch, tmp_path):
    log = tmp_path / 'claude-calls.jsonl'
    b = _fake_bin(tmp_path, 'claude', f"""
with open({str(log)!r}, 'a') as f:
    f.write(json.dumps(dict(argv=sys.argv[1:], prompt=sys.stdin.read())) + '\\n')
print(json.dumps(dict(type='result', is_error=False, result='Claude plan', session_id='claude-sess')))
""")
    monkeypatch.setenv('CLAUDE_BIN', str(b))
    return log


def test_codex_first_turn_and_resume(tmp_path, fake_codex):
    args = dict(ph_id='codex-test', brain='codex', brains_dir=tmp_path / 'brains',
                snapshot_path=tmp_path / 'missing.json')
    first = ph_brain.run_turn(message='Plan launch', **args)
    second = ph_brain.run_turn(message='Continue', **args)
    calls = [json.loads(line) for line in fake_codex.read_text().splitlines()]
    assert first['response'] == second['response'] == 'Plan ready'
    assert 'resume' not in calls[0]['argv']
    assert calls[1]['argv'][calls[1]['argv'].index('resume') + 1] == 'codex-thread'
    assert 'sandbox_mode="read-only"' in calls[0]['argv']
    assert ph_brain.codex_config()[0] in calls[0]['argv']
    saved = ph_brain.load_brain_state('codex-test', tmp_path / 'brains')
    assert saved['codex_session_id'] == 'codex-thread'
    assert saved['conversation_id'] is None
    assert saved['turn_count'] == 2


@pytest.mark.parametrize('remaining', [0.8, 0.1])
def test_agy_429_codex_fallback_and_reserve(monkeypatch, tmp_path, fake_codex, fake_claude, remaining):
    agy = tmp_path / 'agy'
    agy.write_text(f'#!{sys.executable}\nimport sys\nprint("RESOURCE_EXHAUSTED 429 Individual quota reached")\nsys.exit(1)\n')
    agy.chmod(0o755)
    snapshot = tmp_path / 'quota.json'
    snapshot.write_text(json.dumps({'buckets': {'codex': {'weekly_remaining': remaining}}}))
    args = dict(ph_id='fallback', message='Plan', agy_bin=str(agy),
                brains_dir=tmp_path / 'brains', snapshot_path=snapshot)
    if remaining < 0.2:
        # Codex held for workers' reserve -> the last brain, Claude Sonnet 5.5 high (CEO 12 Nov).
        result = ph_brain.run_turn(**args)
        assert not fake_codex.exists()
        assert result['bucket_used'] == 'claude' and result['response'] == 'Claude plan'
        assert result['attempts'][-2]['limit_hit'] == 'router reserve'
    else:
        result = ph_brain.run_turn(**args)
        assert result['bucket_used'] == 'codex'
        assert len(result['attempts']) == len(ph_brain.MODEL_CHAIN) + 1
        saved = ph_brain.load_brain_state('fallback', tmp_path / 'brains')
        assert saved['fallback_events'][-1]['to_model'] == 'codex'


def test_explicit_codex_reserve_gate(tmp_path, fake_codex):
    snapshot = tmp_path / 'quota.json'
    snapshot.write_text(json.dumps({'buckets': {'codex': {'weekly_remaining': 0.1}}}))
    with pytest.raises(RuntimeError, match='router budget reserve'):
        ph_brain.run_turn(ph_id='blocked', message='plan', brain='codex',
                          brains_dir=tmp_path / 'brains', snapshot_path=snapshot)
    assert not fake_codex.exists()


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


def test_select_model_chain_prefers_sonnet_when_agy_claude_available(tmp_path):
    snap = _write_snapshot(tmp_path, agy_claude_weekly=0.94, agy_gemini_weekly=0.96)
    chain = ph_brain.select_model_chain(snapshot_path=snap)
    assert chain[0] == "claude-sonnet-5-5-high"
    assert chain[1] == "gemini-4-argon-high"


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
                "response": "Turn 1 planned with Sonnet 5.5 High",
                "limit_hit": None,
                "raw_stdout": "",
                "raw_stderr": "",
            }
        if len(calls) == 2 and model == "claude-sonnet-5-5-high":
            # Simulate mid-flight quota exhaustion on Sonnet 5.5 High
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

    # Turn 1: starts with claude-sonnet-5-5-high
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
    assert r1["model_used"] == "claude-sonnet-5-5-high"
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
    assert saved["fallback_events"][0]["from_model"] == "claude-sonnet-5-5-high"
    assert saved["fallback_events"][0]["to_model"] == "gemini-4-argon-high"

    # Turn 3: since Turn 2 already swapped to gemini-4-argon-high, Turn 3 stays on gemini-4-argon-high directly
    r3 = ph_brain.run_turn(
        ph_id="7cf12345",
        message="Turn 3 follow-up",
        brains_dir=brains_dir,
        snapshot_path=snap,
    )
    assert r3["ok"] is True
    assert r3["model_used"] == "gemini-4-argon-high"
    assert calls[3]["model"] == "gemini-4-argon-high"
    assert len(calls) == 4


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


def test_invoke_agy_ignores_sticky_conversation_error_when_fallback_succeeds(monkeypatch):
    """When claude-opus-5-5-medium hits 429 on a conversation_id and gemini-4-argon-high
    resumes that same conversation_id, agy --output-format json still includes the earlier
    turn's `"error": "Individual quota reached..."` in stdout even though returncode==0
    and response is non-empty. invoke_agy must mark that fallback turn ok=True."""
    monkeypatch.setattr(ph_brain, '_IN_TURN', type('Guard', (), {'get': lambda self: True})())

    def fake_run(cmd, **kw):
        model = cmd[cmd.index("--model") + 1]
        if model == "claude-opus-5-5-medium":
            stdout = (
                'AGY_ERROR: {"short_error":"RESOURCE_EXHAUSTED (code 429): Individual quota reached."}\n'
                '{"conversation_id":"2eaa92be-5d1a-4ef8-b63e-fa219c9b6f54","status":"ERROR","response":"",'
                '"error":"Individual quota reached. Please upgrade your subscription to increase your limits."}\n'
            )
            return SimpleNamespace(returncode=3, stdout=stdout, stderr="error: Individual quota reached.\n")
        stdout = (
            '{"conversation_id":"2eaa92be-5d1a-4ef8-b63e-fa219c9b6f54","status":"ERROR",'
            '"response":"READY_FROM_ARGON_HIGH\\n",'
            '"error":"Individual quota reached. Please upgrade your subscription to increase your limits."}\n'
        )
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(ph_brain.subprocess, "run", fake_run)
    r_opus = ph_brain.invoke_agy("plan", model="claude-opus-5-5-medium", add_dirs=[], agy_bin="agy")
    assert r_opus["ok"] is False
    assert r_opus["limit_hit"] is not None
    assert r_opus["conversation_id"] == "2eaa92be-5d1a-4ef8-b63e-fa219c9b6f54"

    r_argon = ph_brain.invoke_agy(
        "plan",
        model="gemini-4-argon-high",
        conversation_id=r_opus["conversation_id"],
        add_dirs=[],
        agy_bin="agy",
    )
    assert r_argon["ok"] is True
    assert r_argon["limit_hit"] is None
    assert r_argon["response"].strip() == "READY_FROM_ARGON_HIGH"



def test_codex_config_maps_label_to_full_model_id():
    # GhostRules PH 11 Nov: "-m sol" -> "Model metadata for sol not found".
    model, _ = ph_brain.codex_config()
    assert model.startswith('gpt-6-'), model


def _all_agy_out(tmp_path):
    return _fake_bin(tmp_path, 'agy', 'print("RESOURCE_EXHAUSTED 429 Individual quota reached")\nsys.exit(1)\n')


def test_every_brain_out_wakes_the_lane_clevel(monkeypatch, tmp_path):
    # Both AGY lanes, Codex (reserve) and Claude (usage limit) out -> PH waits + one letter.
    woke = []
    monkeypatch.setattr(ph_brain, '_wake_lane_clevel', lambda ph, st, models: woke.append((ph, models)))
    claude = _fake_bin(tmp_path, 'claude', 'print("Claude AI usage limit reached|1762999999")\nsys.exit(1)\n')
    monkeypatch.setenv('CLAUDE_BIN', str(claude))
    snapshot = tmp_path / 'quota.json'
    snapshot.write_text(json.dumps({'buckets': {'codex': {'weekly_remaining': 0.05}}}))
    with pytest.raises(RuntimeError):
        ph_brain.run_turn(ph_id='allout', message='Plan', agy_bin=str(_all_agy_out(tmp_path)),
                          brains_dir=tmp_path / 'brains', snapshot_path=snapshot)
    assert len(woke) == 1 and woke[0][0] == 'allout'
    assert woke[0][1][-2:] == ['codex', 'claude-sonnet-5-5']


def test_a_non_quota_failure_stops_the_chain(monkeypatch, tmp_path, fake_codex, fake_claude):
    # A crash is not a quota stop: never spend Codex or Claude on it, never wake the C-level.
    woke = []
    monkeypatch.setattr(ph_brain, '_wake_lane_clevel', lambda *a: woke.append(a))
    agy = _fake_bin(tmp_path, 'agy', 'print("panic: something broke")\nsys.exit(2)\n')
    with pytest.raises(RuntimeError):
        ph_brain.run_turn(ph_id='crash', message='Plan', agy_bin=str(agy),
                          brains_dir=tmp_path / 'brains', snapshot_path=tmp_path / 'missing.json')
    assert not fake_codex.exists() and not fake_claude.exists() and not woke


def test_claude_brain_resumes_its_own_session(tmp_path, fake_claude):
    args = dict(ph_id='cl', brain='claude', brains_dir=tmp_path / 'brains',
                snapshot_path=tmp_path / 'missing.json')
    ph_brain.run_turn(message='Plan', **args)
    ph_brain.run_turn(message='Next', **args)
    calls = [json.loads(l) for l in fake_claude.read_text().splitlines()]
    assert '--resume' not in calls[0]['argv']
    assert calls[1]['argv'][calls[1]['argv'].index('--resume') + 1] == 'claude-sess'
    assert calls[0]['argv'][calls[0]['argv'].index('--model') + 1] == 'claude-sonnet-5-5'
    assert 'plan' in calls[0]['argv'] and 'high' in calls[0]['argv']
    assert ph_brain.load_brain_state('cl', tmp_path / 'brains')['claude_session_id'] == 'claude-sess'


def test_wake_lane_clevel_letters_the_lane_owner(monkeypatch):
    from tools import send_to_cto
    sent = []
    monkeypatch.setattr(send_to_cto, 'send', lambda *a, **k: sent.append((a, k)) or True)
    ph_brain._wake_lane_clevel('f85ae4fe', {'lane': 'cmo', 'owner': None, 'project': 'GhostRules'}, ['m1'])
    (args, kw), = sent
    assert args[0] == 'f85ae4fe' and kw['owner_role'] == 'cmo' and kw['cto_id'] == 'fresh'
    assert kw['kind'] == 'blocker'


def test_ph_brain_chain_is_one_model_per_agy_lane_then_luna():
    assert [m for m, _ in ph_brain.MODEL_CHAIN] == ['claude-sonnet-5-5-high', 'gemini-4-argon-high']
    assert ph_brain.codex_config() == ('gpt-6-luna', 'high')
