"""Tests for tools/mesh_check.py (docs/design/org-mesh.md acceptance test).

Mocks subprocess the same way tests/test_multihost.py does
(monkeypatch.setattr(mod.subprocess, "run", fake_run)); mocks the MCP client
by monkeypatching mcp.ClientSession / mcp.client.stdio.stdio_client, which
tools/mesh_check.py imports lazily inside each function, so patching the
live mcp module attributes takes effect on the next call.

Per level: one test where the cell is green and one where it goes red and
the combined exit-code path (render()'s any_fail, which amain() returns
1/0 from verbatim) flips — a check that cannot fail is worthless.

Run via: pytest tests/test_mesh_check.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.mesh_check as m  # noqa: E402


# ---------------------------------------------------------------------------
# L0 — identity
# ---------------------------------------------------------------------------

def test_check_l0_green_when_sources_agree(monkeypatch):
    monkeypatch.setattr(m, "_tailscale_guess_host", lambda: "mac")
    monkeypatch.setattr(m, "_root_match_host", lambda root: "mac")
    ok, reason = m.check_l0(Path("/whatever"))
    assert ok is True
    assert reason is None


def test_check_l0_red_when_sources_disagree(monkeypatch):
    monkeypatch.setattr(m, "_tailscale_guess_host", lambda: "mac")
    monkeypatch.setattr(m, "_root_match_host", lambda root: None)  # -> "(unregistered)"
    ok, reason = m.check_l0(Path("/some/worktree"))
    assert ok is False
    assert "sources disagree" in reason
    assert "tailscale=mac" in reason
    assert "root_match=(unregistered)" in reason


def test_check_l0_self_host_failure_is_not_a_disagreement(monkeypatch):
    """self_host() landed in W0.1 (task-1bfb0389) and can itself raise
    (bad ORG_HOST/node.yaml, unregistered box) — that failure must be
    silently excluded, not treated as a third conflicting source."""
    monkeypatch.setattr(m, "_tailscale_guess_host", lambda: "contabo")
    monkeypatch.setattr(m, "_root_match_host", lambda root: "contabo")

    def _boom():
        raise RuntimeError("cannot resolve self_host: env=None, ...")

    monkeypatch.setattr(m.config, "self_host", _boom)
    ok, reason = m.check_l0(Path("/opt/MoonieXHQ/Agents/Core"))
    assert ok is True
    assert reason is None


# ---------------------------------------------------------------------------
# L1 — ssh
# ---------------------------------------------------------------------------

class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_l1_green_when_ssh_succeeds(monkeypatch):
    def fake_run(cmd, **kwargs):
        assert cmd[:5] == ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
        assert cmd[5] == "mooniex-vps"
        return _FakeCompleted(returncode=0)
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    ok, reason = m.check_l1("contabo")
    assert ok is True
    assert reason is None


def test_check_l1_red_when_ssh_fails(monkeypatch):
    def fake_run(cmd, **kwargs):
        return _FakeCompleted(returncode=255, stderr="Connection refused")
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    ok, reason = m.check_l1("contabo")
    assert ok is False
    assert "Connection refused" in reason


def test_check_l1_mac_target_is_closed_by_design_without_attempting_ssh(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise AssertionError("must not attempt ssh to a host with no alias")
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    ok, reason = m.check_l1("mac")
    assert ok is False
    assert reason == "closed (by design)"


def test_check_l1_windows_target_falls_back_to_cmd_exit(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[-1] == "true":
            return _FakeCompleted(returncode=1, stderr="bash: true: command not found")
        return _FakeCompleted(returncode=0)
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    ok, reason = m.check_l1("winbox")
    assert ok is True
    assert reason is None
    assert calls[0][5] == "winbox" and calls[0][-1] == "true"
    assert calls[1][-3:] == ["cmd", "/c", "exit"] or calls[1][-4:] == ["cmd", "/c", "exit", "0"]


# ---------------------------------------------------------------------------
# L2 — org MCP
# ---------------------------------------------------------------------------

class _FakeStdioCtx:
    async def __aenter__(self):
        return (None, None)

    async def __aexit__(self, *exc):
        return False


class _FakeToolsResult:
    def __init__(self, names):
        self.tools = [types.SimpleNamespace(name=n) for n in names]


class _FakeCallResult:
    def __init__(self, text):
        self.content = [types.SimpleNamespace(text=text)]


class _FakeSession:
    def __init__(self, *_a, **_k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def initialize(self):
        return None


def _install_fake_mcp(monkeypatch, tool_names, call_responses=None):
    import mcp
    import mcp.client.stdio as mcp_stdio

    responses = call_responses or {}

    class _Session(_FakeSession):
        async def list_tools(self):
            return _FakeToolsResult(tool_names)

        async def call_tool(self, name, args):
            fn = responses.get(name)
            text = fn(args) if callable(fn) else (fn or "")
            return _FakeCallResult(text)

    monkeypatch.setattr(mcp_stdio, "stdio_client", lambda params: _FakeStdioCtx())
    monkeypatch.setattr(mcp, "ClientSession", _Session)


def test_check_l2_green_when_both_tools_listed(monkeypatch, tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    _install_fake_mcp(monkeypatch, ["create_task", "delegate_task", "get_task"])
    ok, reason = asyncio.run(m.check_l2(tmp_path))
    assert ok is True
    assert reason is None


def test_check_l2_red_when_delegate_task_missing(monkeypatch, tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    _install_fake_mcp(monkeypatch, ["create_task"])  # delegate_task missing
    ok, reason = asyncio.run(m.check_l2(tmp_path))
    assert ok is False
    assert "delegate_task" in reason


def test_check_l2_red_when_venv_missing(tmp_path):
    ok, reason = asyncio.run(m.check_l2(tmp_path))
    assert ok is False
    assert reason == ".venv missing"


# ---------------------------------------------------------------------------
# L3 — delegate (--live)
# ---------------------------------------------------------------------------

def _toon_task(**fields) -> str:
    return "\n".join(f"{k}: {v}" for k, v in fields.items())


def test_run_l3_probe_green_full_cycle(monkeypatch, tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    monkeypatch.setattr(m, "_register_probe_session", lambda session_id, host: None)

    responses = {
        "create_task": lambda args: "task-abc12345",
        "delegate_task": lambda args: _toon_task(status="in_progress"),
        "get_task": lambda args: _toon_task(status="review"),
        "merge_task": lambda args: _toon_task(merged="true", merge_sha="deadbeef1234"),
    }
    _install_fake_mcp(monkeypatch, ["create_task", "delegate_task", "get_task", "merge_task"],
                      responses)
    monkeypatch.setattr(m, "_git_ls_remote_has", lambda root, sha: True)
    monkeypatch.setattr(m, "_git_status_porcelain", lambda root: "")

    ok, reason = asyncio.run(m.run_l3_probe("mac", "contabo", tmp_path, "w0", False))
    assert ok is True
    assert reason is None


def test_run_l3_probe_red_when_task_fails(monkeypatch, tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    monkeypatch.setattr(m, "_register_probe_session", lambda session_id, host: None)

    responses = {
        "create_task": lambda args: "task-abc12345",
        "delegate_task": lambda args: _toon_task(status="in_progress"),
        "get_task": lambda args: _toon_task(status="failed"),
    }
    _install_fake_mcp(monkeypatch, ["create_task", "delegate_task", "get_task", "merge_task"],
                      responses)

    ok, reason = asyncio.run(m.run_l3_probe("mac", "contabo", tmp_path, "w0", False))
    assert ok is False
    assert "failed" in reason


def test_run_l3_probe_red_when_merge_sha_not_on_origin(monkeypatch, tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("#!/bin/sh\n")
    monkeypatch.setattr(m, "_register_probe_session", lambda session_id, host: None)

    responses = {
        "create_task": lambda args: "task-abc12345",
        "delegate_task": lambda args: _toon_task(status="in_progress"),
        "get_task": lambda args: _toon_task(status="review"),
        "merge_task": lambda args: _toon_task(merged="true", merge_sha="deadbeef1234"),
    }
    _install_fake_mcp(monkeypatch, ["create_task", "delegate_task", "get_task", "merge_task"],
                      responses)
    monkeypatch.setattr(m, "_git_ls_remote_has", lambda root, sha: False)

    ok, reason = asyncio.run(m.run_l3_probe("mac", "contabo", tmp_path, "w0", False))
    assert ok is False
    assert "not found on origin" in reason


# ---------------------------------------------------------------------------
# L4 — ledger
# ---------------------------------------------------------------------------

def test_l4_probe_green_when_peer_sees_task(monkeypatch):
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4green1")
    monkeypatch.setattr(m, "_ssh_run",
                        lambda alias, cmd, timeout, stdin_path=None: json.dumps({"id": "task-l4green1"}))
    ok, reason = m.l4_probe("mac", "contabo")
    assert ok is True
    assert reason is None


def test_l4_probe_red_when_peer_ledger_is_separate(monkeypatch):
    """Today's real state: one sqlite per host, so the target never sees a
    task created on this host's ledger."""
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4red001")
    monkeypatch.setattr(m, "_ssh_run", lambda alias, cmd, timeout, stdin_path=None: json.dumps({}))
    ok, reason = m.l4_probe("mac", "contabo")
    assert ok is False
    assert "separate ledger" in reason


def test_l4_probe_red_when_target_unreachable(monkeypatch):
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4red002")
    ok, reason = m.l4_probe("contabo", "mac")  # mac has no ssh alias
    assert ok is False
    assert reason == "target unreachable (no ssh alias)"


# ---------------------------------------------------------------------------
# render() — wave gating, "closed (by design)", and the exit-code tie-in
# amain() reuses (`return 1 if any_fail else 0`)
# ---------------------------------------------------------------------------

def test_render_green_cell_is_ok_and_does_not_fail():
    combined = {"L0": {"mac": {"mac": {"ok": True, "reason": None}}}}
    for lvl in ("L1", "L2", "L3", "L4"):
        combined.setdefault(lvl, {h: {} for h in m.HOSTS})
    md, any_fail, n_ok, n_fail = m.render(combined, "w0")
    assert any_fail is False
    assert n_ok == 1
    assert n_fail == 0
    assert "ok" in md


def test_render_red_cell_fails_and_flips_exit_code():
    combined = {lvl: {h: {} for h in m.HOSTS} for lvl in m.LEVELS}
    combined["L1"]["mac"]["contabo"] = {"ok": False, "reason": "boom"}
    md, any_fail, n_ok, n_fail = m.render(combined, "w0")
    assert any_fail is True
    assert n_fail == 1
    assert "FAIL(boom)" in md


def test_render_cell_above_expect_wave_is_na_not_fail():
    """L2 winbox is gated to w3 — a red (or even green) result computed at
    w0 must render 'n/a' and never contribute to the exit code."""
    combined = {lvl: {h: {} for h in m.HOSTS} for lvl in m.LEVELS}
    combined["L2"]["winbox"]["winbox"] = {"ok": False, "reason": "no org MCP"}
    md, any_fail, n_ok, n_fail = m.render(combined, "w0")
    assert any_fail is False
    assert n_fail == 0
    assert n_ok == 0
    l2_section = md.split("## L2")[1].split("## L3")[0]
    winbox_row = [ln for ln in l2_section.splitlines() if ln.startswith("| winbox")][0]
    assert "n/a" in winbox_row
    assert "FAIL" not in winbox_row


def test_render_l1_mac_target_shows_closed_by_design_below_w2():
    combined = {lvl: {h: {} for h in m.HOSTS} for lvl in m.LEVELS}
    md, any_fail, n_ok, n_fail = m.render(combined, "w0")
    l1_section = md.split("## L1")[1].split("## L2")[0]
    contabo_row = [ln for ln in l1_section.splitlines() if ln.startswith("| contabo")][0]
    assert "closed (by design)" in contabo_row
    assert any_fail is False


def test_render_l1_mac_target_becomes_a_real_fail_from_w2():
    """From w2 the cell is actually judged — since the alias genuinely
    stays None, it renders FAIL, not a silent pass."""
    combined = {lvl: {h: {} for h in m.HOSTS} for lvl in m.LEVELS}
    combined["L1"]["contabo"]["mac"] = {"ok": False, "reason": "closed (by design)"}
    md, any_fail, n_ok, n_fail = m.render(combined, "w2")
    assert any_fail is True
    l1_section = md.split("## L1")[1].split("## L2")[0]
    contabo_row = [ln for ln in l1_section.splitlines() if ln.startswith("| contabo")][0]
    assert "FAIL(closed (by design))" in contabo_row


# ---------------------------------------------------------------------------
# amain() end-to-end exit code, with build_matrix's pieces stubbed
# ---------------------------------------------------------------------------

def _async_return(value):
    async def _f(*_a, **_k):
        return value
    return _f


def test_amain_exits_1_when_an_in_scope_cell_is_red(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(m, "_running_host_guess", lambda root: "mac")
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))
    monkeypatch.setattr(m, "check_l2", _async_return((True, None)))
    monkeypatch.setattr(m, "check_l1", lambda target: (False, "ssh boom") if target == "contabo"
                        else (True, None))
    monkeypatch.setattr(m, "_collect_peer_local", lambda alias, cfg, script_path: None)
    monkeypatch.setattr(m, "write_state", lambda combined, args, running_host: tmp_path / "latest.json")

    rc = asyncio.run(m.amain(["--expect", "w0"]))
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL(ssh boom)" in out


def test_amain_exits_0_when_everything_in_scope_is_green(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(m, "_running_host_guess", lambda root: "mac")
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))
    monkeypatch.setattr(m, "check_l2", _async_return((True, None)))
    monkeypatch.setattr(m, "check_l1", lambda target: (True, None))
    monkeypatch.setattr(m, "_collect_peer_local", lambda alias, cfg, script_path: None)
    monkeypatch.setattr(m, "write_state", lambda combined, args, running_host: tmp_path / "latest.json")

    rc = asyncio.run(m.amain(["--expect", "w0"]))
    assert rc == 0


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def test_toon_field_extracts_scalar():
    text = "status: review\nreport: multi\nword line\n"
    assert m._toon_field(text, "status") == "review"


def test_toon_field_missing_key_is_none():
    assert m._toon_field("status: review\n", "merge_sha") is None


def test_tailscale_guess_host_matches_hostname_substring(monkeypatch):
    def fake_run(cmd, **kwargs):
        assert cmd[:2] == ["tailscale", "status"]
        payload = {"Self": {"HostName": "MacBook Pro ของ GoB", "DNSName": "macbook-pro.ts.net."}}
        return _FakeCompleted(returncode=0, stdout=json.dumps(payload))
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    assert m._tailscale_guess_host() == "mac"


def test_tailscale_guess_host_none_when_unavailable(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("no tailscale binary")
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    assert m._tailscale_guess_host() is None


def test_root_match_host_unregistered_checkout_returns_none():
    assert m._root_match_host(Path("/some/worktree/path")) is None


def test_root_match_host_matches_registered_agents_root():
    assert m._root_match_host(Path(m.config.host("mac")["agents_root"])) == "mac"


def test_parse_args_requires_expect_outside_local_and_get_task():
    with pytest.raises(SystemExit):
        m._parse_args([])


def test_parse_args_local_does_not_require_expect():
    args = m._parse_args(["--local"])
    assert args.local is True
    assert args.expect is None


def test_parse_args_get_task_does_not_require_expect():
    args = m._parse_args(["--get-task", "task-abc123", "--json"])
    assert args.get_task == "task-abc123"
