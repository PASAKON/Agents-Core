import json
import io
import runpy
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone

import pytest

from tools.runner_share import summary

ROOT = Path(__file__).resolve().parents[1]


def test_permission_failure_is_silent(monkeypatch, capsys):
    hook = runpy.run_path(str(ROOT / "scripts/hook-ph-handson.py"))
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(dict(
        session_id="s1", tool_name="Write", tool_input={"file_path": "x.py"}))))
    original = Path.open
    def denied(path, mode="r", *args, **kwargs):
        if "a" in mode:
            raise PermissionError("read-only reports")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", denied)
    assert hook["main"]() == 0
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


COMMIT_MESSAGE_HEREDOC = "git commit -m \"$(cat <<'EOF'\nfix it's > x.py\ntee y.sh\nEOF\n)\""


@pytest.mark.parametrize("command", ["git commit -m example", "git -C repo commit -m example",
    "git add -A && git commit -m x", COMMIT_MESSAGE_HEREDOC])
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
    def run(script, payload, ph=False):
        env = dict(os.environ, PH_HANDSON_PATH=str(tmp_path / "ph-handson.jsonl"),
                   CXO_ROLE="project_head" if ph else "cto")
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script)],
                              input=payload if isinstance(payload, str) else json.dumps(payload),
                              text=True, capture_output=True, env=env)
    return run


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


def bash(command):
    return dict(session_id="s1", tool_name="Bash", tool_input={"command": command})


@pytest.mark.parametrize("command", [
    "cat > x.py <<'EOF'\nit's an apostrophe in the body\nEOF",
    "cat > x.py <<'EOF'\nprint(1)\nEOF\ngit add -A && git commit -m x",
    "echo a > x.py && git commit -m x",
    "git commit -m x; echo a > x.py",
    "cat > x.py <<'EOF'\ngit commit -m x\nEOF",
    "cat > x.py <<EOF\nfirst\nEOF\ncat > y.sh <<'EOF'\nsecond\nEOF",
    "echo a | tee x.py it's"])
def test_write_beside_commit_or_quote_is_counted(invoke, tmp_path, command):
    assert invoke("hook-ph-handson.py", bash(command), ph=True).stdout
    assert json.loads((tmp_path / "ph-handson.jsonl").read_text())["path"] == "shell"


@pytest.mark.parametrize("command", [
    "cat <<'EOF'\nprint('x > y.py')\nEOF",
    "python3 - <<'EOF'\nopen('x.py', 'w')\nEOF",
    "echo hi > notes.md && git commit -m x",
    "cat <<< 'x.py'"])
def test_content_is_not_a_write(invoke, tmp_path, command):
    assert not invoke("hook-ph-handson.py", bash(command), ph=True).stdout
    assert not (tmp_path / "ph-handson.jsonl").exists()


@pytest.mark.parametrize("command", ["git - " * 170000, "sed " * 260000, "x" * (1 << 20),
    "git commit -m x\n" * 70000, "echo " + "a > " * 260000, "sed -i " + " " * (1 << 20) + "x.py"],
    ids=["git-dash", "sed-repeat", "plain", "commits", "redirects", "spaces"])
def test_one_megabyte_command_is_fast(tmp_path, monkeypatch, command):
    assert len(command) >= 1_000_000
    hook = runpy.run_path(str(ROOT / "scripts/hook-ph-handson.py"))
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setenv("PH_HANDSON_PATH", str(tmp_path / "ph.jsonl"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(bash(command))))
    started = time.perf_counter()
    assert hook["main"]() == 0
    assert time.perf_counter() - started < 0.5


def test_write_past_the_cut_is_not_seen():
    hook = runpy.run_path(str(ROOT / "scripts/hook-ph-handson.py"))
    assert hook["shell_ext"]("echo " + "a" * 5000 + " > x.py") is None
    assert hook["shell_ext"]("echo " + "a" * 4000 + " > x.py") == ".py"


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
