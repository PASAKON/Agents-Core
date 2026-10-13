"""scripts/hook-agent-route-log.py -- log-only PreToolUse hook on Agent
(tool-value plan 2026-10-13 §4.3 M2, week 1).

Every case points AGENT_ROUTE_LOG_PATH at tmp_path, never the real state/.
"""
from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "hookagentlog", ROOT / "scripts" / "hook-agent-route-log.py"
)
hookagentlog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hookagentlog)

CLEAR = ("CXO_SESSION", "CTO_SESSION", "CXO_ROLE", "CXO_SESSION_ID",
         "CTO_SESSION_ID", "WORKER_TASK_ID", "CLAUDE_CODE_ENTRYPOINT")
SECRET_PROMPT = "route: task-0123abcd\nwrite the parser; the token is sk-live-DO-NOT-LOG"


def _env(monkeypatch, tmp_path, **env) -> Path:
    for var in CLEAR:
        monkeypatch.delenv(var, raising=False)
    spool = tmp_path / "reports" / "agent-calls.jsonl"
    monkeypatch.setenv("AGENT_ROUTE_LOG_PATH", str(spool))
    base = {"CXO_SESSION": "1", "CXO_ROLE": "cto", "CTO_SESSION_ID": "abcd1234",
            "CLAUDE_CODE_ENTRYPOINT": "cli"}
    base.update(env)
    for k, v in base.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    return spool


def _call(monkeypatch, *, tool="Agent", cwd="/opt/MoonieXHQ/Agents/Core",
          raw=None, **tool_input) -> tuple[int, str]:
    tool_input.setdefault("description", "Write the parser")
    tool_input.setdefault("prompt", SECRET_PROMPT)
    text = raw if raw is not None else json.dumps(
        {"session_id": "s1", "cwd": cwd, "hook_event_name": "PreToolUse",
         "tool_name": tool, "tool_input": tool_input})
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    out = io.StringIO()
    with redirect_stdout(out):
        rc = hookagentlog.main()
    return rc, out.getvalue()


def _lines(spool: Path) -> list[dict]:
    if not spool.exists():
        return []
    return [json.loads(line) for line in spool.read_text(encoding="utf-8").splitlines()]


def test_logs_one_line_and_never_the_prompt(monkeypatch, tmp_path):
    spool = _env(monkeypatch, tmp_path)
    rc, out = _call(monkeypatch, subagent_type="general-purpose", model="sonnet",
                    run_in_background=True)
    assert (rc, out) == (0, "")
    [rec] = _lines(spool)
    assert {k: rec[k] for k in ("schema", "session_id", "role", "org_session", "cwd",
                                "entrypoint", "tool", "subagent_type", "model",
                                "description", "prompt_chars", "read_only",
                                "background", "route", "override")} == {
        "schema": 1, "session_id": "s1", "role": "cto", "org_session": "abcd1234",
        "cwd": "/opt/MoonieXHQ/Agents/Core", "entrypoint": "cli", "tool": "Agent",
        "subagent_type": "general-purpose", "model": "sonnet",
        "description": "Write the parser", "prompt_chars": len(SECRET_PROMPT),
        "read_only": False, "background": True, "route": "task-0123abcd", "override": ""}
    assert rec["ts"].endswith("+00:00") and rec["host"]
    raw = spool.read_text(encoding="utf-8")
    assert "sk-live" not in raw and "write the parser" not in raw


def test_markers_and_read_only_types(monkeypatch, tmp_path):
    spool = _env(monkeypatch, tmp_path)
    _call(monkeypatch, subagent_type="Explore", prompt="\n  override: Security — audit\nrest")
    _call(monkeypatch, prompt="Override: in-session Agent run by CTO")
    _call(monkeypatch, subagent_type="Plan", prompt="plan it\nroute: task-0123abcd")
    _call(monkeypatch, tool="Task", subagent_type="fork", prompt="")
    got = [(r["subagent_type"], r["read_only"], r["route"], r["override"], r["tool"])
           for r in _lines(spool)]
    assert got == [
        ("Explore", True, "", "security", "Agent"),
        ("general-purpose", False, "", "in-session", "Agent"),  # no subagent_type given
        ("Plan", True, "", "", "Agent"),  # a marker only counts on the first line
        ("fork", False, "", "", "Task"),
    ]


def test_appends_across_calls(monkeypatch, tmp_path):
    spool = _env(monkeypatch, tmp_path)
    for _ in range(3):
        _call(monkeypatch)
    assert len(_lines(spool)) == 3


def test_silent_for_workers_sompong_and_non_clevel(monkeypatch, tmp_path):
    for env, cwd in (
        ({"WORKER_TASK_ID": "task-0123abcd"}, "/opt/MoonieXHQ/Agents/Core"),
        ({}, "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-0123abcd"),
        ({"CXO_ROLE": "coo"}, "/opt/MoonieXHQ/Agents/Core"),
        ({"CXO_SESSION": None}, "/opt/MoonieXHQ/Agents/Core"),
    ):
        spool = _env(monkeypatch, tmp_path, **env)
        assert _call(monkeypatch, cwd=cwd) == (0, "")
        assert not spool.exists(), env


def test_cto_session_alone_counts_and_headless_is_labelled(monkeypatch, tmp_path):
    spool = _env(monkeypatch, tmp_path, CXO_SESSION=None, CTO_SESSION="1",
                 CTO_SESSION_ID=None, CXO_SESSION_ID="ef567890",
                 CLAUDE_CODE_ENTRYPOINT="sdk-cli")
    _call(monkeypatch)
    [rec] = _lines(spool)
    assert (rec["org_session"], rec["entrypoint"]) == ("ef567890", "sdk-cli")


def test_other_tools_and_bad_input_are_ignored(monkeypatch, tmp_path):
    spool = _env(monkeypatch, tmp_path)
    assert _call(monkeypatch, tool="Bash") == (0, "")
    assert _call(monkeypatch, raw="not json") == (0, "")
    assert _call(monkeypatch, raw="[1, 2]") == (0, "")
    assert _call(monkeypatch, raw=json.dumps({"tool_name": "Agent", "tool_input": "x"})) == (0, "")
    [rec] = _lines(spool)  # the string tool_input still logs, with empty fields
    assert (rec["prompt_chars"], rec["subagent_type"]) == (0, "general-purpose")


def test_unwritable_spool_never_blocks(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("AGENT_ROUTE_LOG_PATH", str(blocker / "sub" / "agent-calls.jsonl"))
    assert _call(monkeypatch) == (0, "")


def test_registered_in_settings_for_agent():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    entries = [e for e in settings["hooks"]["PreToolUse"]
               if any("hook-agent-route-log.py" in h.get("command", "") for h in e["hooks"])]
    assert len(entries) == 1
    assert set(entries[0]["matcher"].split("|")) == {"Agent", "Task"}
