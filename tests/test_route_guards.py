import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

from tools.runner_share import summary

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def invoke(tmp_path):
    def run(script, payload, mode="log", ph=False, deadline="2999-01-01T00:00:00Z"):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(f'mode: {mode}\nenforce_after: "{deadline}"\n')
        env = dict(os.environ, AGENT_ROUTE_CONFIG=str(cfg),
                   AGENT_ROUTE_PATH=str(tmp_path / "agent-route.jsonl"),
                   PH_HANDSON_PATH=str(tmp_path / "ph-handson.jsonl"),
                   CXO_ROLE="project_head" if ph else "cto")
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script)],
                              input=payload if isinstance(payload, str) else json.dumps(payload),
                              text=True, capture_output=True, env=env)
    return run


def agent(prompt="secret prompt", kind="general-purpose"):
    return dict(session_id="s1", tool_name="Agent", tool_input=dict(
        prompt=prompt, description="d" * 100, subagent_type=kind))


@pytest.mark.parametrize("kind", ["Explore", "Plan", "claude-code-guide", "statusline-setup"])
def test_read_only(invoke, kind):
    assert invoke("hook-agent-route.py", agent(kind=kind), "enforce").returncode == 0


@pytest.mark.parametrize("mode,code", [("log", 0), ("enforce", 2)])
def test_missing(invoke, tmp_path, mode, code):
    result = invoke("hook-agent-route.py", agent(), mode)
    assert result.returncode == code
    raw = (tmp_path / "agent-route.jsonl").read_text()
    row = json.loads(raw)
    assert not row["has_reason"] and len(row["description"]) == 60
    assert "secret prompt" not in raw
    if code:
        assert len(result.stderr.splitlines()) == 1
        assert "quota-handoff" in result.stderr


@pytest.mark.parametrize("prompt,code", [("override: review — check", 0),
    ("override: bogus — check", 2), ("intro\n\noverride: review", 2)])
def test_reason(invoke, prompt, code):
    assert invoke("hook-agent-route.py", agent(prompt), "enforce").returncode == code


def test_expired(invoke):
    assert invoke("hook-agent-route.py", agent(), deadline="2000-01-01T00:00:00Z").returncode == 2


@pytest.mark.parametrize("payload", ["garbage", "[]", '{"tool_input":null}'])
def test_garbage(invoke, tmp_path, payload):
    assert invoke("hook-agent-route.py", payload, "enforce").returncode == 0
    assert json.loads((tmp_path / "agent-route.jsonl").read_text())["decision"] == "error_allow"


@pytest.mark.parametrize("ph,ext,flag", [(False, ".py", False), (True, ".py", True), (True, ".md", False)])
def test_edit(invoke, tmp_path, ph, ext, flag):
    p = dict(session_id="s1", tool_name="Edit", tool_input={"file_path": "x" + ext})
    result = invoke("hook-ph-handson.py", p, ph=ph)
    assert result.returncode == 0
    assert bool(result.stdout) == flag
    assert (tmp_path / "ph-handson.jsonl").exists() == flag


@pytest.mark.parametrize("command", ["sed -i x.py", "echo secret > x.ts", "tee x.sh <<'EOF'\nsecret\nEOF",
    "cat <<'EOF' > x.sql\nsecret\nEOF", "git commit -m secret", 'sed -i "s/a/b/" "my file.py"'])
def test_shell(invoke, tmp_path, command):
    p = dict(session_id="s1", tool_name="Bash", tool_input={"command": command})
    assert invoke("hook-ph-handson.py", p, ph=True).stdout
    raw = (tmp_path / "ph-handson.jsonl").read_text()
    assert command not in raw and "secret" not in raw
    assert json.loads(raw)["path"] == "shell"


def test_cap(invoke, tmp_path):
    p = dict(session_id="s1", tool_name="Write", tool_input={"file_path": "x.py"})
    assert invoke("hook-ph-handson.py", p, ph=True).stdout
    assert not invoke("hook-ph-handson.py", p, ph=True).stdout
    path = tmp_path / "ph-handson.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 2
    rows[0]["ts"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert invoke("hook-ph-handson.py", p, ph=True).stdout
    p["session_id"] = "s2"
    assert invoke("hook-ph-handson.py", p, ph=True).stdout


@pytest.mark.parametrize("payload", ["garbage", "[]"])
def test_ph_garbage(invoke, tmp_path, payload):
    result = invoke("hook-ph-handson.py", payload, ph=True)
    assert result.returncode == 0 and not result.stdout
    assert not (tmp_path / "ph-handson.jsonl").exists()


def test_non_ph_shell(invoke, tmp_path):
    result = invoke("hook-ph-handson.py", dict(session_id="s1", tool_name="Bash",
                    tool_input={"command": "git commit -m example"}))
    assert result.returncode == 0 and not result.stdout
    assert not (tmp_path / "ph-handson.jsonl").exists()


def test_seeded_table(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE tasks (runner TEXT, created_at TEXT)")
    conn.executemany("INSERT INTO tasks VALUES (?, ?)", [
        (r, "2026-10-13T17:00:00Z") for r in ["claude", "codex", "agy", None]])
    conn.execute("INSERT INTO tasks VALUES ('claude', '2026-10-14T17:00:00Z')")
    for name, extra in [("agent-route", {"has_reason": True}), ("agent-route", {"has_reason": False}), ("ph-handson", {})]:
        with (tmp_path / (name + ".jsonl")).open("a") as f:
            f.write(json.dumps(dict(ts="2026-10-14T10:00:00+07:00", session_id="s1", **extra)) + "\n")
    text = summary(conn, date(2026, 10, 14), tmp_path)
    assert "claude=1 codex=1 agy=1 other=1 outside=50.0%" in text
    assert "s1=1/1/1" in text and len(text) < 300 and "\n" not in text
    conn.close()
