import json
import io
import runpy
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

from tools.runner_share import summary

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("year", [1970, 2026, 9999])
def test_log_at_any_clock(tmp_path, monkeypatch, capsys, year):
    hook = runpy.run_path(str(ROOT / "scripts/hook-agent-route.py"))
    class Clock:
        @staticmethod
        def now(tz):
            return datetime(year, 1, 1, tzinfo=tz)
    hook["main"].__globals__["datetime"] = Clock
    cfg = tmp_path / "config.yaml"
    cfg.write_text("mode: log\n")
    spool = tmp_path / "route.jsonl"
    monkeypatch.setenv("AGENT_ROUTE_CONFIG", str(cfg))
    monkeypatch.setenv("AGENT_ROUTE_PATH", str(spool))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(agent())))
    assert hook["main"]() == 0
    assert json.loads(spool.read_text())["decision"] == "log"
    assert not capsys.readouterr().err


@pytest.mark.parametrize("script", ["hook-agent-route.py", "hook-ph-handson.py"])
def test_permission_failure_is_silent(monkeypatch, capsys, tmp_path, script):
    hook = runpy.run_path(str(ROOT / "scripts" / script))
    cfg = tmp_path / "config.yaml"
    cfg.write_text("mode: enforce\n")
    monkeypatch.setenv("AGENT_ROUTE_CONFIG", str(cfg))
    monkeypatch.setenv("CXO_ROLE", "project_head")
    payload = agent() if script == "hook-agent-route.py" else dict(
        session_id="s1", tool_name="Write", tool_input={"file_path": "x.py"})
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    original = Path.open
    def denied(path, mode="r", *args, **kwargs):
        if "a" in mode:
            raise PermissionError("read-only reports")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", denied)
    assert hook["main"]() == 0
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize("command", ["git commit -m example", "git -C repo commit -m example"])
def test_commit_is_not_handson(invoke, tmp_path, command):
    result = invoke("hook-ph-handson.py", dict(session_id="s1", tool_name="Bash",
                    tool_input={"command": command}), ph=True)
    assert result.returncode == 0 and not result.stdout and not result.stderr
    assert not (tmp_path / "ph-handson.jsonl").exists()


def test_large_spool_bounded_read(tmp_path, monkeypatch, capsys):
    spool = tmp_path / "ph.jsonl"
    recent = json.dumps(dict(session_id="s1", reminded=True,
                            ts=datetime.now(timezone.utc).isoformat())).encode() + b"\n"
    spool.write_bytes((b"x" * 1000 + b"\n") * 2048 + recent)
    size = spool.stat().st_size
    hook = runpy.run_path(str(ROOT / "scripts/hook-ph-handson.py"))
    original = Path.open
    reads = []
    class Bounded:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def __getattr__(self, name):
            return getattr(self.stream, name)
        def read(self, n=-1):
            reads.append((self.stream.tell(), n))
            assert 0 <= n <= 65536
            return self.stream.read(n)
    def tracked(path, *args, **kwargs):
        stream = original(path, *args, **kwargs)
        return Bounded(stream) if path == spool else stream
    monkeypatch.setattr(Path, "open", tracked)
    monkeypatch.setenv("PH_HANDSON_PATH", str(spool))
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(dict(
        session_id="s1", tool_name="Write", tool_input={"file_path": "x.py"}))))
    assert hook["main"]() == 0
    assert reads == [(size - 65536, 65536)]
    assert spool.stat().st_size > size
    assert not capsys.readouterr().out


@pytest.fixture
def invoke(tmp_path):
    def run(script, payload, mode="log", ph=False, config=None):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(f'mode: {mode}\n' if config is None else config)
        if config == "missing":
            cfg.unlink()
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


@pytest.mark.parametrize("config", ["missing", "[", "null", "[]", "mode: bogus", "mode: enforce\nextra: ["])
def test_bad_config(invoke, tmp_path, config):
    result = invoke("hook-agent-route.py", agent(), config=config)
    assert result.returncode == 0 and not result.stderr
    assert json.loads((tmp_path / "agent-route.jsonl").read_text())["decision"] == "error_allow"


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
    "cat <<'EOF' > x.sql\nsecret\nEOF", 'sed -i "s/a/b/" "my file.py"'])
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
