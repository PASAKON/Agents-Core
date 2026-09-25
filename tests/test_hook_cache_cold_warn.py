"""scripts/hook-cache-cold-warn.py -- UserPromptSubmit cache-cold warning.

Task task-a40d2d8e (CEO ruling 2026-09-25): a C-level session idle >60 min
with context >300k tokens gets ONE blocking warning before its next turn
re-writes the whole 1-hour prompt cache at 2x input price. Every case here
points ORG_COLD_STATE_DIR at tmp_path -- a run that wrote real state broke
~/.claude links on 2026-09-25 (see docs/ops/cache-cold-guard-2026-09-25.md).
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "hookcold", ROOT / "scripts" / "hook-cache-cold-warn.py"
)
hookcold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hookcold)


def _write_transcript(path: Path, *, idle_minutes: float, ctx_tokens: int,
                       model: str = "claude-opus-5-5") -> None:
    ts = (datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)).isoformat()
    ts = ts.replace("+00:00", "Z")
    line = {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": 0,
                "cache_creation_input_tokens": min(ctx_tokens, 100_000),
                "cache_read_input_tokens": max(ctx_tokens - 100_000, 0),
            },
        },
    }
    path.write_text(json.dumps(line) + "\n")


def _run(monkeypatch, tmp_path, *, prompt="status?",
          cwd="/Users/gob/MoonieXHQ/Agents/Core",
          session_id="test-session-1", transcript_text=None,
          idle_minutes=None, ctx_tokens=None, model="claude-opus-5-5",
          extra_env=None):
    for var in ("WORKER_TASK_ID", "CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    state_dir = tmp_path / "state"
    monkeypatch.setenv("ORG_COLD_STATE_DIR", str(state_dir))
    if extra_env:
        for k, v in extra_env.items():
            monkeypatch.setenv(k, v)

    transcript_path = tmp_path / "transcript.jsonl"
    if transcript_text is not None:
        transcript_path.write_text(transcript_text)
    else:
        _write_transcript(
            transcript_path, idle_minutes=idle_minutes, ctx_tokens=ctx_tokens,
            model=model,
        )

    payload = {
        "session_id": session_id,
        "transcript_path": str(transcript_path),
        "prompt": prompt,
        "cwd": cwd,
    }
    out, err = io.StringIO(), io.StringIO()
    stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = hookcold.main()
    finally:
        sys.stdin = stdin
    return rc, out.getvalue(), err.getvalue(), state_dir


def test_stale_session_blocks_once_then_passes_within_grace(monkeypatch, tmp_path):
    rc1, out1, err1, state_dir = _run(
        monkeypatch, tmp_path, idle_minutes=125, ctx_tokens=600_000,
        session_id="stale-1",
    )
    assert rc1 == 2
    assert out1 == ""
    assert "idle 2h" in err1
    assert "600k" in err1
    assert "$" in err1
    state_file = state_dir / "stale-1.json"
    assert state_file.exists()
    recorded = json.loads(state_file.read_text())
    assert recorded["ctx_tokens"] == 600_000

    # Resend within the grace window (ORG_COLD_GRACE_MIN default 10 min):
    # must pass through untouched, never blocking twice in a row.
    rc2, out2, err2, _ = _run(
        monkeypatch, tmp_path, idle_minutes=125, ctx_tokens=600_000,
        session_id="stale-1",
    )
    assert rc2 == 0
    assert err2 == ""


def test_idle_below_threshold_passes(monkeypatch, tmp_path):
    rc, _, err, state_dir = _run(
        monkeypatch, tmp_path, idle_minutes=10, ctx_tokens=600_000,
    )
    assert rc == 0
    assert err == ""
    assert not state_dir.exists() or not list(state_dir.glob("*.json"))


def test_worker_cwd_is_exempt(monkeypatch, tmp_path):
    worktree_cwd = (
        "/Users/gob/MoonieXHQ/Agents/Core/worktrees/"
        "mooniex-agents__developer__task-deadbeef"
    )
    rc, _, err, _ = _run(
        monkeypatch, tmp_path, idle_minutes=125, ctx_tokens=600_000,
        cwd=worktree_cwd,
    )
    assert rc == 0
    assert err == ""


def test_worker_task_id_env_is_exempt(monkeypatch, tmp_path):
    rc, _, err, _ = _run(
        monkeypatch, tmp_path, idle_minutes=125, ctx_tokens=600_000,
        extra_env={"WORKER_TASK_ID": "task-deadbeef"},
    )
    assert rc == 0
    assert err == ""


def test_wake_marker_prompt_is_exempt(monkeypatch, tmp_path):
    rc, _, err, _ = _run(
        monkeypatch, tmp_path, idle_minutes=125, ctx_tokens=600_000,
        prompt="[New message from CTO]",
    )
    assert rc == 0
    assert err == ""


def test_slash_command_is_exempt(monkeypatch, tmp_path):
    rc, _, err, _ = _run(
        monkeypatch, tmp_path, idle_minutes=125, ctx_tokens=600_000,
        prompt="/session-save",
    )
    assert rc == 0
    assert err == ""


def test_pending_mail_is_exempt(monkeypatch, tmp_path):
    """UserPromptSubmit hooks run in PARALLEL (code.claude.com/docs/en/hooks),
    so a block here can race scripts/hook-inbox.py's mailbox drain on the
    same prompt. Standing down whenever this session's own mailbox is
    non-empty removes that race."""
    import lib.mailbox as mailbox
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    inbox_dir = tmp_path / "inbox" / "cto-letter-sess"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "20260925T000000000000Z-ceo-x.json").write_text(json.dumps({
        "from": {"role": "ceo", "session_id": "x"},
        "to": {"role": "cto", "session_id": "letter-sess"},
        "chain": ["ceo:x"],
        "sent_at": "2026-09-25T00:00:00Z",
        "body": "hello",
    }))

    rc, _, err, _ = _run(
        monkeypatch, tmp_path, idle_minutes=125, ctx_tokens=600_000,
        session_id="letter-sess",
        extra_env={"CXO_ROLE": "cto", "CTO_SESSION_ID": "letter-sess"},
    )
    assert rc == 0
    assert err == ""


def test_malformed_transcript_fails_open(monkeypatch, tmp_path):
    rc, _, err, _ = _run(
        monkeypatch, tmp_path,
        transcript_text="not valid json\n{also not valid\n",
    )
    assert rc == 0
    assert err == ""


def test_malformed_stdin_fails_open(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_COLD_STATE_DIR", str(tmp_path / "state"))
    for var in ("WORKER_TASK_ID", "CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    stdin = sys.stdin
    sys.stdin = io.StringIO("not json at all")
    try:
        rc = hookcold.main()
    finally:
        sys.stdin = stdin
    assert rc == 0
