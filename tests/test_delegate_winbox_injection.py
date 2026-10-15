"""M8 (CTO Main security pass, 2026-10-14): the ssh command delegate sends to winbox
is parsed by cmd.exe first, and cmd.exe ignores _ps_quote's backticks. A task title
like `x" & calc & "` used to run a command on winbox. No real ssh: subprocess.run
is faked, as in tests/test_delegate_probe_gate.py."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402
from lib import session_names  # noqa: E402

PAYLOAD = 'x" & calc & "'
CMD_EXE_ACTIVE = set('"&|%^<>`')


@pytest.fixture()
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "_remote_free_gb", lambda ssh_alias: 100.0)
    monkeypatch.setattr(delegate, "_ensure_remote_deploy", lambda *a, **k: [])
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    calls: list[list[str]] = []

    class R:
        def __init__(self, rc=0, out=""):
            self.returncode, self.stdout, self.stderr = rc, out, ""

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "ssh" and len(cmd) == 3 and "spawn-worker.ps1" in cmd[2]:
            return R(0, "4242\n")
        return R(0)
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    return calls


def _task(title: str, **fields) -> str:
    tid = db_mod.create_task(project="mooniex-agents", role="developer", title=title,
                             description="d", owner_cto="test-owner", host="winbox",
                             touches=["tools/m8_marker.py"])
    if fields:
        db_mod.set_fields(tid, actor="cto", **fields)
    return tid


def _spawn_cmd(calls):
    return [c for c in calls if c[0] == "ssh" and len(c) == 3 and "spawn-worker.ps1" in c[2]]


def test_windows_safe_drops_every_cmd_exe_character():
    assert session_names.windows_safe(PAYLOAD) == "x  calc"
    assert not CMD_EXE_ACTIVE & set(session_names.windows_safe('a"b&c|d%e^f<g>h`i!j'))
    assert session_names.windows_safe("y" * 80, 40) == "y" * 40


@pytest.mark.parametrize("title", [PAYLOAD, 'a" | whoami > x.txt & "', "100% %PATH% ^&",
                                   "ชื่อภาษาไทย & del"])
def test_a_hostile_title_reaches_winbox_only_as_plain_text(env, title):
    tid = _task(title)
    asyncio.run(delegate.delegate_task(tid, host="winbox"))
    sent = _spawn_cmd(env)
    assert len(sent) == 1
    name = sent[0][2].split("-SessionName ", 1)[1].split(" -Runner", 1)[0]
    assert name.startswith('"Dev.S#') and name.endswith('"')
    assert not CMD_EXE_ACTIVE & set(name[1:-1])


@pytest.mark.parametrize("key,value", [("RunnerModel", 'm" & calc & "'),
                                       ("WorkDir", 'C:\\w" & calc & "'),
                                       ("SessionName", PAYLOAD), ("SessionName", "Dev#abc - 50%PATH%")])
def test_a_hostile_value_is_refused(key, value):
    tid = "task-0000abcd"
    values = {"Launcher": "C:\\a\\spawn-worker.ps1", "Task": tid, "Project": "p", "Role": "developer",
              "Branch": f"agent/developer-{tid}", "Base": "main", "RepoUrl": "git@github.com:o/r.git",
              "RepoPath": "C:\\r", "WorktreeRoot": "C:\\w", "ClaudeArgs": "", "Model": "m",
              "Effort": "high", "TaskFile": "C:\\a\\t.md", "SessionName": "Dev#abc - ok",
              "Runner": "agy", "RunnerModel": "", "WorkDir": ""}
    delegate._check_windows_spawn_values(values)  # the clean set passes
    with pytest.raises(ValueError, match="not safe to send to winbox"):
        delegate._check_windows_spawn_values({**values, key: value})


def test_a_refused_value_fails_the_task_and_sends_no_ssh(env, monkeypatch):
    monkeypatch.setattr(delegate, "get_worker_session_name", lambda *a, **k: PAYLOAD)
    tid = _task("ok")
    result = asyncio.run(delegate.delegate_task(tid, host="winbox"))
    assert result["status"] == "failed"
    assert "not safe to send to winbox" in result["delegate_log"]
    assert not any(c[0] in ("ssh", "scp") for c in env)


def test_a_browser_operators_claude_args_pass_both_winbox_paths():
    # ~1,500 characters of --allowed-tools: node_dispatch's old 600 cap refused it.
    from tools import node_dispatch as nd
    args = delegate._render_remote_runner_args("browser_operator", "winbox", "claude")
    assert len(args) > 600
    assert nd._PS_CLAUDE_ARGS_RE.fullmatch(args)
    assert not nd._PS_CLAUDE_ARGS_RE.fullmatch(args + ' & calc')
