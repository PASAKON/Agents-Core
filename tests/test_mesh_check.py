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

import ast
import asyncio
import copy
import json
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.mesh_check as m  # noqa: E402


# ---------------------------------------------------------------------------
# L0 — identity
# ---------------------------------------------------------------------------

def test_check_l0_green_when_sources_agree(pinned_mac_host, monkeypatch):
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


# --- L0 root_match: agents_root OR the registered checkout of this repo -----
# winbox's agents_root is the spawn directory; the Agents-Core checkout is
# config/projects.yaml `mooniex-agents` `paths.winbox` (task-47202255).

WIN_SPAWN = r"C:\Users\x\spawn"
WIN_CHECKOUT = r"C:\Users\x\spawn\repo\Agents-Core"


@pytest.fixture
def fake_registry(monkeypatch, tmp_path):
    """A hosts/projects registry shaped like the real config: winbox registers its
    checkout under `paths`, away from its agents_root; mac registers both alike."""
    hosts = {
        "mac": {"agents_root": "/fake/mac/Core"},
        "winbox": {"agents_root": WIN_SPAWN},
    }
    projects = {m.AGENTS_PROJECT_KEY: {"paths": {"mac": "/fake/mac/Core", "winbox": WIN_CHECKOUT}}}
    monkeypatch.setattr(m.config, "hosts", lambda: hosts)
    monkeypatch.setattr(m.config, "projects", lambda: projects)
    return hosts, projects


def test_root_match_windows_checkout_ignores_case_and_separator(fake_registry):
    for spelling in (WIN_CHECKOUT, WIN_CHECKOUT.replace("\\", "/"),
                     WIN_CHECKOUT.replace("\\", "/").lower(), WIN_CHECKOUT.upper() + "\\"):
        assert m._root_match_host(Path(spelling)) == "winbox", spelling


def test_root_match_windows_checkout_of_the_real_config(monkeypatch):
    """Not the fixture: the winbox row config/projects.yaml really carries."""
    registered = m.config.projects()[m.AGENTS_PROJECT_KEY]["paths"]["winbox"]
    assert m._root_match_host(Path(registered.replace("\\", "/").lower())) == "winbox"


def test_root_match_agents_root_still_matches(fake_registry):
    assert m._root_match_host(Path("/fake/mac/Core")) == "mac"
    assert m._root_match_host(Path(WIN_SPAWN.lower().replace("\\", "/"))) == "winbox"


def test_root_match_a_worktree_matches_nobody(fake_registry):
    """Under a registered checkout is still not a registered checkout."""
    for worktree in ("/fake/mac/Core/worktrees/mooniex-agents__developer__task-1",
                     WIN_CHECKOUT + r"\worktrees\task-1", WIN_SPAWN + r"\worktrees\task-1",
                     "/fake/mac/Core-other"):
        assert m._root_match_host(Path(worktree)) is None, worktree


def test_root_match_without_a_registered_checkout_falls_back_to_agents_root(fake_registry, monkeypatch):
    monkeypatch.setattr(m.config, "projects", lambda: {})
    assert m._root_match_host(Path(WIN_SPAWN)) == "winbox"
    assert m._root_match_host(Path(WIN_CHECKOUT)) is None


def test_root_match_resolves_a_symlink_for_a_path_that_exists_here(monkeypatch, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("cannot create a symlink here")
    monkeypatch.setattr(m.config, "hosts", lambda: {"mac": {"agents_root": "/elsewhere"}})
    monkeypatch.setattr(m.config, "projects",
                        lambda: {m.AGENTS_PROJECT_KEY: {"paths": {"mac": str(link)}}})
    assert m._root_match_host(real) == "mac"
    assert m._root_match_host(link) == "mac"


def test_check_l0_green_on_winbox_when_run_from_its_registered_checkout(fake_registry, monkeypatch):
    monkeypatch.setattr(m.config, "self_host", lambda: "winbox")
    monkeypatch.setattr(m, "_tailscale_guess_host", lambda: "winbox")
    ok, reason = m.check_l0(Path(WIN_CHECKOUT.replace("\\", "/").lower()))
    assert (ok, reason) == (True, None)


def test_check_l0_red_from_a_worktree_even_when_the_checkout_is_registered(fake_registry, monkeypatch):
    monkeypatch.setattr(m.config, "self_host", lambda: "winbox")
    monkeypatch.setattr(m, "_tailscale_guess_host", lambda: "winbox")
    ok, reason = m.check_l0(Path(WIN_CHECKOUT + r"\worktrees\task-1"))
    assert ok is False
    assert "root_match=(unregistered)" in reason
    assert "self_host=winbox" in reason


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


# --- L1 to this host itself: no ssh, a cell that never counts ----------------
# winbox cannot resolve its own ssh alias, so the cell to itself made it red
# (task-47202255).

#
# ONE identity per run decides which cell is "to itself": the host the matrix
# labels its row with (`_running_host_guess`), passed to `_l1_cell` as `me`.
# `self_host()` is a second source and can disagree (a worktree, another
# node.yaml, the Linux CI runner answering "contabo" for a test that runs the
# matrix as "mac"); if it chose, a red cell would silently become an uncounted
# n/a. The tests pin it every which way to prove it is never consulted.

SELF_HOST_PINS = ["mac", "contabo", "winbox", ValueError]  # a host key, or "raises this"


def _pin_self_host(monkeypatch, pin) -> None:
    def fake():
        if isinstance(pin, type):
            raise pin("cannot resolve self_host")
        return pin
    monkeypatch.setattr(m.config, "self_host", fake)


@pytest.fixture(params=SELF_HOST_PINS, ids=lambda p: p if isinstance(p, str) else "raises-" + p.__name__)
def self_host_pin(request, monkeypatch):
    """The test runs once per self_host() answer: each host, and "cannot say"."""
    _pin_self_host(monkeypatch, request.param)
    return request.param


# self_host() is lru_cached and reads ORG_HOST first. Every test in this file
# starts on "mac", whatever box runs it (the Linux CI runner is "contabo"), the
# way the `hub` fixture below does; a test that needs another answer overrides it.
_REAL_SELF_HOST = m.config.self_host


@pytest.fixture(autouse=True)
def _self_host_is_mac_whatever_the_box(monkeypatch):
    monkeypatch.setenv("ORG_HOST", "mac")
    _REAL_SELF_HOST.cache_clear()
    yield
    _REAL_SELF_HOST.cache_clear()


def _fake_ssh(monkeypatch, red=()) -> list:
    """Replace subprocess.run: record the alias of every ssh dialled (the list
    returned); an alias in `red` answers 255, every other one 0."""
    dialled: list = []

    def fake_run(cmd, **kwargs):
        dialled.append(cmd[5])
        return _FakeCompleted(returncode=255 if cmd[5] in red else 0, stderr="no route to host")
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    return dialled


def test_l1_cell_to_this_host_never_runs_subprocess(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("subprocess.run called for an L1 cell to this host")
    monkeypatch.setattr(m.subprocess, "run", boom)
    cell = m._l1_cell("winbox", "winbox")
    assert cell["ok"] is True and cell["reason"] == "n/a" and cell["kind"] == "n/a"
    assert m._judge(cell) == ("n/a", "skip")


def test_l1_cell_never_asks_self_host_who_this_host_is(self_host_pin, monkeypatch):
    """Whatever self_host() says, only `me` makes a cell n/a, and a red answer to
    any other target stays red."""
    dialled = _fake_ssh(monkeypatch, red=("mooniex-vps",))
    assert m._l1_cell("contabo", "contabo")["kind"] == "n/a"
    assert dialled == []
    cell = m._l1_cell("contabo", "mac")
    assert cell["ok"] is False and "no route to host" in cell["reason"]
    assert dialled == ["mooniex-vps"]


def test_l1_cell_to_another_host_is_still_the_ssh_answer(monkeypatch):
    dialled = _fake_ssh(monkeypatch)
    assert m._l1_cell("contabo", "winbox") == {"ok": True, "reason": None}
    assert dialled == ["mooniex-vps"]


def test_l1_cell_dials_everyone_when_the_run_has_no_identity(monkeypatch):
    """me is None: nothing is "this host", so nothing is skipped."""
    dialled = _fake_ssh(monkeypatch)
    assert m._l1_cell("contabo", None)["ok"] is True
    assert m._l1_cell("winbox", None)["ok"] is True
    assert dialled == ["mooniex-vps", "winbox"]


def test_local_payload_l1_to_this_host_is_na_and_dials_no_one_at_its_alias(self_host_pin, monkeypatch):
    dialled = _fake_ssh(monkeypatch)
    monkeypatch.setattr(m, "_running_host_guess", lambda root: "winbox")
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))
    monkeypatch.setattr(m, "check_l2", _async_return((True, None)))
    payload = asyncio.run(m.local_payload())
    assert payload["l1"]["winbox"] == {"ok": True, "reason": "n/a", "kind": "n/a"}
    assert payload["l1"]["contabo"] == {"ok": True, "reason": None}
    assert payload["l1"]["mac"] == {"ok": False, "reason": "closed (by design)"}
    assert dialled == ["mooniex-vps"]


def test_local_payload_dials_every_host_when_it_cannot_tell_where_it_runs(self_host_pin, monkeypatch):
    """The labelling source says None (a worktree, tailscale silent): no cell is
    n/a, this host's own included, even when self_host() names one."""
    dialled = _fake_ssh(monkeypatch, red=("winbox",))
    monkeypatch.setattr(m, "_running_host_guess", lambda root: None)
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))
    monkeypatch.setattr(m, "check_l2", _async_return((True, None)))
    payload = asyncio.run(m.local_payload())
    assert set(dialled) == {"winbox", "mooniex-vps"}
    assert payload["l1"]["winbox"]["ok"] is False and "kind" not in payload["l1"]["winbox"]
    assert payload["l1"]["contabo"] == {"ok": True, "reason": None}


def _l1_row(md: str, frm: str) -> list[str]:
    section = md.split("## L1")[1].split("## L2")[0]
    row = [ln for ln in section.splitlines() if ln.startswith(f"| {frm} ")][0]
    return [c.strip() for c in row.strip("|").split("|")]


def _matrix(monkeypatch, running_host: str, expect: str = "w0"):
    monkeypatch.setattr(m, "_running_host_guess", lambda root: running_host)
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))
    monkeypatch.setattr(m, "check_l2", _async_return((True, None)))
    monkeypatch.setattr(m, "_collect_peer_local", lambda alias, cfg, script_path: None)
    args = types.SimpleNamespace(expect=expect, live=False, no_merge=False)
    combined, _ = asyncio.run(m.build_matrix(args))
    return combined, m.render(combined, expect)


def test_matrix_l1_to_this_host_is_na_and_dials_no_one_at_its_alias(self_host_pin, monkeypatch):
    dialled = _fake_ssh(monkeypatch)
    combined, (md, any_fail, n_ok, n_fail) = _matrix(monkeypatch, "winbox")
    assert "winbox" not in combined["L1"]["winbox"]  # the diagonal has no cell at all
    assert _l1_row(md, "winbox")[m.HOSTS.index("winbox") + 1] == "n/a"
    assert dialled == ["mooniex-vps"]
    assert any_fail is False and n_fail == 0


@pytest.mark.parametrize("running, other_self, red_alias, red_to", [
    ("contabo", "winbox", "winbox", "winbox"),       # self_host() names the TARGET
    ("winbox", "contabo", "mooniex-vps", "contabo"),  # self_host() names ANOTHER host
])
def test_matrix_a_red_l1_cell_stays_red_when_self_host_names_another_host(
        monkeypatch, running, other_self, red_alias, red_to):
    """The two identity sources disagree, in each direction. The matrix row is
    labelled `running`, so that row dials every other host, and a red answer is
    a red cell that counts and flips the exit code. The CI failure was this:
    the matrix ran as "mac", self_host() said "contabo", and a red L1 to contabo
    came out as n/a."""
    _pin_self_host(monkeypatch, other_self)
    dialled = _fake_ssh(monkeypatch, red=(red_alias,))
    combined, (md, any_fail, n_ok, n_fail) = _matrix(monkeypatch, running)
    assert red_alias in dialled
    cell = combined["L1"][running][red_to]
    assert cell["ok"] is False and "kind" not in cell
    assert "FAIL(" in _l1_row(md, running)[m.HOSTS.index(red_to) + 1]
    assert any_fail is True and n_fail >= 1


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


def _l3_green_cycle_with_status(monkeypatch, tmp_path, before: str, after: str):
    """A full green L3 cycle whose `git status --porcelain` reads `before` when
    the probe starts and `after` once the merge is on origin."""
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
    reads = iter([before, after])
    monkeypatch.setattr(m, "_git_status_porcelain", lambda root: next(reads))
    return asyncio.run(m.run_l3_probe("mac", "contabo", tmp_path, "w0", False))


# The Mac's runtime checkout always carries the harness's model line in
# claude-home/settings.json, so a check for an absolutely clean checkout could
# never pass there.
_MAC_DIRT = " M claude-home/settings.json\n M state/banchi/flow_shoot.log\n?? state/jules/"


def test_run_l3_probe_green_when_the_checkout_was_dirty_before_the_probe(monkeypatch, tmp_path):
    ok, reason = _l3_green_cycle_with_status(monkeypatch, tmp_path, _MAC_DIRT, _MAC_DIRT)
    assert ok is True
    assert reason is None


def test_run_l3_probe_green_when_another_session_adds_untracked_files(monkeypatch, tmp_path):
    ok, reason = _l3_green_cycle_with_status(
        monkeypatch, tmp_path, _MAC_DIRT, _MAC_DIRT + "\n?? state/work_watch_state.json")
    assert ok is True
    assert reason is None


def test_run_l3_probe_red_when_the_cycle_dirties_a_tracked_file(monkeypatch, tmp_path):
    ok, reason = _l3_green_cycle_with_status(
        monkeypatch, tmp_path, _MAC_DIRT, "UU docs/ops/mesh-probe/mac-contabo.md\n" + _MAC_DIRT)
    assert ok is False
    assert reason == "merge left the runtime checkout dirty: UU docs/ops/mesh-probe/mac-contabo.md"


def test_run_l3_probe_red_when_git_status_fails_after_the_merge(monkeypatch, tmp_path):
    ok, reason = _l3_green_cycle_with_status(monkeypatch, tmp_path, "", m._GIT_STATUS_FAILED)
    assert ok is False
    assert reason == "git status failed after merge"


# ---------------------------------------------------------------------------
# L4 — ledger
# ---------------------------------------------------------------------------

@pytest.fixture
def l4_cancelled(monkeypatch):
    """Record the probe's clean-up instead of writing to any ledger."""
    import lib.db as db_mod
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(db_mod, "update_status",
                        lambda task_id, status, **kw: seen.append((task_id, status)) or True)
    return seen


def test_l4_probe_green_when_peer_sees_task(monkeypatch, l4_cancelled):
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4green1")
    monkeypatch.setattr(m, "_ssh_run",
                        lambda alias, cmd, timeout, stdin_path=None: json.dumps({"id": "task-l4green1"}))
    ok, reason = m.l4_probe("mac", "contabo")
    assert ok is True
    assert reason is None
    assert l4_cancelled == [("task-l4green1", "cancelled")]


def test_l4_probe_red_when_peer_ledger_is_separate(monkeypatch, l4_cancelled):
    """Before the hub: one sqlite per host, so the target never sees a task
    created on this host's ledger."""
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4red001")
    monkeypatch.setattr(m, "_ssh_run", lambda alias, cmd, timeout, stdin_path=None: json.dumps({}))
    ok, reason = m.l4_probe("mac", "contabo")
    assert ok is False
    assert "separate ledger" in reason
    assert l4_cancelled == [("task-l4red001", "cancelled")]


def test_l4_probe_red_when_target_unreachable(monkeypatch, l4_cancelled):
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4red002")
    ok, reason = m.l4_probe("contabo", "mac")  # mac has no ssh alias
    assert ok is False
    assert reason == "target unreachable (no ssh alias)"
    assert l4_cancelled == [("task-l4red002", "cancelled")]


def test_l4_probe_reads_a_posix_peer_through_org_python(monkeypatch, l4_cancelled):
    """After G1 a bare venv python over ssh has no ORG_DB_URL and dies on the
    tombstone (ArchivedDB), which read as "read-only ssh to target failed"."""
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4posix1")
    sent: list[str] = []

    def fake_ssh(alias, cmd, timeout, stdin_path=None):
        sent.append(cmd)
        return json.dumps({"id": "task-l4posix1"})

    monkeypatch.setattr(m, "_ssh_run", fake_ssh)
    ok, _ = m.l4_probe("mac", "contabo")
    assert ok is True
    assert len(sent) == 1
    assert "bash scripts/hub/org-python.sh -m tools.mesh_check --get-task task-l4posix1 --json" in sent[0]
    assert ".venv/bin/python" not in sent[0]


def test_l4_probe_reads_winbox_with_its_venv_python(monkeypatch, l4_cancelled):
    import lib.db as db_mod
    monkeypatch.setattr(db_mod, "create_task", lambda **kw: "task-l4win001")
    sent: list[str] = []
    monkeypatch.setattr(m, "_ssh_run",
                        lambda alias, cmd, timeout, stdin_path=None: sent.append(cmd) or None)
    ok, reason = m.l4_probe("mac", "winbox")
    assert ok is False
    assert reason == "read-only ssh to target failed"
    assert len(sent) == 1
    assert "\\.venv\\Scripts\\python.exe" in sent[0]
    assert "org-python.sh" not in sent[0]
    assert l4_cancelled == [("task-l4win001", "cancelled")]


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


def test_amain_exits_1_when_an_in_scope_cell_is_red(self_host_pin, monkeypatch, tmp_path, capsys):
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


def test_amain_exits_0_when_everything_in_scope_is_green(self_host_pin, monkeypatch, tmp_path, capsys):
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


# ---------------------------------------------------------------------------
# Mesh levels: SEC, L5, L6, L7, L8 and the one-poller invariant.
#
# Every cell has a green, a red and an unreachable test. Nothing here dials a
# host: subprocess.run is a recorder or a tripwire, mesh.dispatch is a fake far
# side, and the hub is a tmp_path SQLite ledger (the same isolation
# tests/test_w23_mesh_dispatch.py uses). self is pinned to "mac" (mesh_ssh:
# null in config/hosts.yaml); contabo and winbox carry a real mesh_ssh.
# ---------------------------------------------------------------------------

from lib import config as hub_config  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import mesh  # noqa: E402
from lib import router  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402


@pytest.fixture
def hub(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "mac")
    monkeypatch.setenv("HOME", str(tmp_path))  # the org_dispatch key path expands from it
    hub_config.self_host.cache_clear()
    yield db_mod
    hub_config.self_host.cache_clear()


def _as_host(monkeypatch, name: str) -> None:
    monkeypatch.setenv("ORG_HOST", name)
    hub_config.self_host.cache_clear()


class FakeSsh:
    """subprocess.run, recorded. `handler(argv)` returns (returncode, stdout,
    stderr) or raises."""

    def __init__(self, handler):
        self.handler, self.calls = handler, []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        rc, out, err = self.handler(list(argv))
        return subprocess.CompletedProcess(argv, rc, out, err)


def _ssh(monkeypatch, handler) -> FakeSsh:
    fake = FakeSsh(handler)
    monkeypatch.setattr(subprocess, "run", fake)
    return fake


def _no_ssh(monkeypatch) -> None:
    def boom(argv, **kw):
        raise AssertionError(f"nothing may be dialled: {argv}")
    monkeypatch.setattr(subprocess, "run", boom)


def _nd_line(ok: bool, verb: str = "probe", **extra) -> str:
    return json.dumps({"ok": ok, "verb": verb, **extra}) + "\n"


def _probe_reply(host: str) -> dict:
    return {"ok": True, "verb": "probe", "result": {"host": host}}


def _sec_handler(host: str = "contabo"):
    """A correctly locked far side: `probe` answers, everything else is refused."""
    def handler(argv):
        if argv[-1] == "probe":
            return 0, _nd_line(True, result={"host": host}), ""
        return 2, _nd_line(False, error="unknown verb"), ""
    return handler


# ---- SEC -------------------------------------------------------------------

def test_sec_payloads_are_the_acceptance_check_2_list_plus_bash():
    assert set(m.SEC_PAYLOADS) == {"probe; id", "probe && id", "$(id)", "`id`", "probe | id", "bash"}


def test_sec_green_when_probe_answers_and_every_payload_is_refused(hub, monkeypatch):
    ssh = _ssh(monkeypatch, _sec_handler())
    assert m.check_sec("contabo") == {"ok": True, "reason": None}
    assert [argv[-1] for argv, _ in ssh.calls] == ["probe", *m.SEC_PAYLOADS]
    dest = hub_config.host("contabo")["mesh_ssh"]
    for argv, kw in ssh.calls:
        assert argv[:3] == ["ssh", "-F", "none"]
        assert argv[-2] == dest  # the mesh destination, never the admin alias
        assert hub_config.host("contabo")["ssh"] not in argv
    # every payload goes out raw, after the very prefix build_argv made for `probe`
    prefix = ssh.calls[0][0][:-1]
    assert all(argv[:-1] == prefix for argv, _ in ssh.calls[1:])


@pytest.mark.parametrize("where", ["stdout", "stderr"])
def test_sec_red_when_uid_appears_anywhere_even_beside_a_refusal(hub, monkeypatch, where):
    leak = "uid=0(root) gid=0(root) groups=0(root)"

    def handler(argv):
        if argv[-1] == "$(id)":
            # node_dispatch's own refusal is still the last stdout line: only the
            # uid= check can catch this one.
            return ((2, _nd_line(False, error="unknown verb"), leak) if where == "stderr"
                    else (2, leak + "\n" + _nd_line(False, error="unknown verb"), ""))
        return _sec_handler()(argv)

    _ssh(monkeypatch, handler)
    cell = m.check_sec("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "uid=" in cell["reason"] and "$(id)" in cell["reason"]


def test_sec_red_when_a_payload_is_answered_ok_true(hub, monkeypatch):
    def handler(argv):
        if argv[-1] == "probe && id":
            return 0, _nd_line(True, result={"host": "contabo"}), ""
        return _sec_handler()(argv)

    _ssh(monkeypatch, handler)
    cell = m.check_sec("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "probe && id" in cell["reason"]


@pytest.mark.parametrize("answer", ["", "bash-5.2$ \n", "not json at all\n", "[1, 2]\n"])
def test_sec_red_when_a_payload_gets_no_node_dispatch_refusal(hub, monkeypatch, answer):
    def handler(argv):
        if argv[-1] == "bash":
            return 0, answer, ""
        return _sec_handler()(argv)

    _ssh(monkeypatch, handler)
    cell = m.check_sec("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "not refused by node_dispatch" in cell["reason"]


def test_sec_red_when_probe_answers_as_another_host(hub, monkeypatch):
    _ssh(monkeypatch, _sec_handler(host="winbox"))
    cell = m.check_sec("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "'winbox'" in cell["reason"] and "'contabo'" in cell["reason"]


def test_sec_red_when_probe_is_refused(hub, monkeypatch):
    _ssh(monkeypatch, lambda argv: (2, _nd_line(False, error="refused"), ""))
    cell = m.check_sec("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "probe refused" in cell["reason"]


@pytest.mark.parametrize("stage", ["probe", "payload"])
@pytest.mark.parametrize("how", ["exit255", "timeout", "oserror"])
def test_sec_unreachable_when_nothing_answers(hub, monkeypatch, stage, how):
    target = "probe" if stage == "probe" else "`id`"

    def handler(argv):
        if argv[-1] != target:
            return _sec_handler()(argv)
        if how == "timeout":
            raise subprocess.TimeoutExpired(argv, 30)
        if how == "oserror":
            raise OSError("no ssh binary")
        return 255, "", "Permission denied (publickey)."

    _ssh(monkeypatch, handler)
    cell = m.check_sec("contabo")
    assert cell["ok"] is False
    assert cell["kind"] == "unreachable"


def test_sec_target_without_mesh_ssh_is_closed_and_never_dialled(hub, monkeypatch):
    _no_ssh(monkeypatch)
    assert m.check_sec("mac") == {"ok": False, "reason": "closed (by design)", "kind": "closed"}


def test_sec_refuses_to_judge_the_host_it_runs_on(hub, monkeypatch):
    _as_host(monkeypatch, "contabo")
    _no_ssh(monkeypatch)
    cell = m.check_sec("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "this host" in cell["reason"]


def test_sec_a_payload_refused_locally_never_counts_as_the_far_sides_refusal(hub, monkeypatch):
    """lib.mesh answers a bad verb itself, with the dict the server would give
    and no ssh. Prove that answer exists, then that check_sec does not take it."""
    _no_ssh(monkeypatch)
    local = mesh.dispatch("contabo", "probe; id")
    assert local["ok"] is False  # a refusal made here, with nothing dialled

    # (1) argv for the shell probes refused here: nothing is dialled, so the
    # far side was not tested, and the cell must not be green.
    monkeypatch.setattr(mesh, "dispatch", lambda host, verb, *a, timeout=None: _probe_reply(host))

    def refuse(host, verb, args):
        raise nd.Refusal("refused before ssh")

    monkeypatch.setattr(mesh, "build_argv", refuse)
    cell = m.check_sec("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "far side not tested" in cell["reason"]


def test_sec_shell_payloads_never_go_through_mesh_dispatch(hub, monkeypatch):
    seen: list[tuple] = []

    def dispatch(host, verb, *args, timeout=None):
        seen.append((host, verb, args))
        return _probe_reply(host)

    monkeypatch.setattr(mesh, "dispatch", dispatch)
    ssh = _ssh(monkeypatch, _sec_handler())
    assert m.check_sec("contabo")["ok"] is True
    assert seen == [("contabo", "probe", ())]  # only the verb; the raw text went to ssh
    assert [argv[-1] for argv, _ in ssh.calls] == list(m.SEC_PAYLOADS)


# ---- L5 --------------------------------------------------------------------

def _probe_worker(host: str = "contabo", status: str = "in_progress", role: str = "probe") -> str:
    tid = db_mod.create_task("mooniex-agents", role, "mesh probe worker", "d", host=host)
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, tid))
    return tid


class FarSide:
    """Stands in for mesh.dispatch: records every call, then lets `fn` answer."""

    def __init__(self, fn):
        self.fn, self.calls = fn, []

    def __call__(self, host, verb, *args, timeout=None):
        self.calls.append((host, verb, args, timeout))
        return self.fn(host, verb, args)


def _far(monkeypatch, fn) -> FarSide:
    far = FarSide(fn)
    monkeypatch.setattr(mesh, "dispatch", far)
    return far


def _deliver(mark: bool = True, to: str | None = None, **extra):
    """A far side that delivers: it flips the hub row (when `mark`) and answers
    in the shape of verb_deliver_letter."""
    def fn(host, verb, args):
        lid = int(args[0])
        letter = db_mod.get_letter(lid)
        if mark:
            db_mod.mark_letter_delivered(lid)
        result = {"letter_id": lid, "delivered": True,
                  "to": to or f"probe-{letter['to_session']}", **extra}
        return {"ok": True, "verb": verb, "result": result}
    return fn


def _letters() -> list[dict]:
    with db_mod.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM letters ORDER BY id").fetchall()]


def test_l5_green_posix_shape_and_the_letter_says_it_is_a_probe(hub, monkeypatch):
    tid = _probe_worker("contabo")
    far = _far(monkeypatch, _deliver())
    cell = m.l5_probe("mac", "contabo")
    assert cell == {"ok": True, "reason": None, "note": "wake not reported"}
    (letter,) = _letters()
    assert (letter["to_host"], letter["to_role"], letter["to_session"]) == ("contabo", "probe", tid)
    assert (letter["from_host"], letter["from_role"]) == ("mac", "mesh_check")
    assert letter["status"] == "delivered"
    assert "mesh-check probe letter" in letter["body"] and "Ignore it" in letter["body"]
    assert far.calls == [("contabo", "deliver_letter", (str(letter["id"]),), None)]


def test_l5_green_and_says_so_when_the_reply_reports_the_wake(hub, monkeypatch):
    _probe_worker("contabo")
    _far(monkeypatch, _deliver(woke=True, why=""))
    assert m.l5_probe("mac", "contabo") == {"ok": True, "reason": None, "note": "woke"}


def test_l5_green_for_a_worker_letter_on_windows_that_reports_woke_false(hub, monkeypatch):
    """_append_worker_mailbox answers `woke: False` and no `why`: a worker is
    never woken, it reads MAILBOX.md before every tool call. Not a failed wake."""
    _probe_worker("winbox")
    _far(monkeypatch, _deliver(woke=False))
    assert m.l5_probe("mac", "winbox")["ok"] is True


def test_l5_green_when_the_far_side_says_already_delivered(hub, monkeypatch):
    _probe_worker("contabo")

    def fn(host, verb, args):
        db_mod.mark_letter_delivered(int(args[0]))
        return {"ok": True, "verb": verb, "result": {"letter_id": int(args[0]),
                                                      "already_delivered": True}}

    _far(monkeypatch, fn)
    assert m.l5_probe("mac", "contabo")["ok"] is True


def test_l5_red_when_the_reply_says_delivered_but_the_hub_row_is_not(hub, monkeypatch):
    _probe_worker("contabo")
    _far(monkeypatch, _deliver(mark=False))
    cell = m.l5_probe("mac", "contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "hub row is 'pending'" in cell["reason"]
    assert [r["status"] for r in _letters()] == ["failed"]  # the watchdog must not retry a probe


def test_l5_red_when_the_wake_was_tried_and_failed_and_the_letter_stays_delivered(hub, monkeypatch):
    _probe_worker("contabo")
    _far(monkeypatch, _deliver(woke=False, why="wake raised OSError"))
    cell = m.l5_probe("mac", "contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "wake failed" in cell["reason"] and "OSError" in cell["reason"]
    assert [r["status"] for r in _letters()] == ["delivered"]  # a delivered row is never rewritten


def test_l5_red_when_deliver_letter_is_refused(hub, monkeypatch):
    _probe_worker("contabo")
    _far(monkeypatch, lambda host, verb, args: {"ok": False, "verb": verb, "error": "no live tmux"})
    cell = m.l5_probe("mac", "contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "no live tmux" in cell["reason"]
    assert [r["status"] for r in _letters()] == ["failed"]


def test_l5_red_when_the_letter_reached_a_different_recipient(hub, monkeypatch):
    _probe_worker("contabo")
    _far(monkeypatch, _deliver(to="probe-task-ffffffff"))
    cell = m.l5_probe("mac", "contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "expected probe-" in cell["reason"]


def test_l5_red_when_the_reply_is_for_another_letter_or_neither_flag(hub, monkeypatch):
    _probe_worker("contabo")
    _far(monkeypatch, lambda host, verb, args: {"ok": True, "verb": verb,
                                                  "result": {"letter_id": 999999, "delivered": True}})
    assert "reply is for letter 999999" in m.l5_probe("mac", "contabo")["reason"]
    _far(monkeypatch, lambda host, verb, args: {"ok": True, "verb": verb,
                                                  "result": {"letter_id": int(args[0])}})
    cell = m.l5_probe("mac", "contabo")
    assert cell["ok"] is False and "neither delivered nor already_delivered" in cell["reason"]


def test_l5_red_without_a_live_probe_worker_on_the_target_and_writes_no_letter(hub, monkeypatch):
    _probe_worker("winbox")                    # wrong host
    _probe_worker("contabo", status="review")  # not in progress
    _probe_worker("contabo", role="developer")  # wrong role
    _far(monkeypatch, lambda *a: pytest.fail("nothing to deliver"))
    cell = m.l5_probe("mac", "contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "no in_progress probe worker on contabo" in cell["reason"]
    assert _letters() == []


def test_l5_unreachable_when_the_host_gives_no_answer_and_the_letter_is_abandoned(hub, monkeypatch):
    _probe_worker("contabo")

    def down(host, verb, args):
        raise mesh.MeshUnreachable(f"{verb} on {host}: no route")

    _far(monkeypatch, down)
    cell = m.l5_probe("mac", "contabo")
    assert cell["ok"] is False
    assert cell["kind"] == "unreachable"
    assert [r["status"] for r in _letters()] == ["failed"]


def test_l5_unreachable_when_the_hub_cannot_be_read(hub, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("hub down")

    monkeypatch.setattr(db_mod, "list_tasks", boom)
    _far(monkeypatch, lambda *a: pytest.fail("must not be dialled"))
    assert m.l5_probe("mac", "contabo")["kind"] == "unreachable"


def test_l5_unreachable_when_the_letter_cannot_be_written(hub, monkeypatch):
    _probe_worker("contabo")

    def boom(*a, **kw):
        raise RuntimeError("hub down")

    monkeypatch.setattr(db_mod, "create_letter", boom)
    _far(monkeypatch, lambda *a: pytest.fail("must not be dialled"))
    assert m.l5_probe("mac", "contabo")["kind"] == "unreachable"


def test_l5_target_without_mesh_ssh_is_closed_and_writes_no_letter(hub, monkeypatch):
    _probe_worker("mac")
    _no_ssh(monkeypatch)
    _far(monkeypatch, lambda *a: pytest.fail("must not be dialled"))
    assert m.l5_probe("contabo", "mac") == {"ok": False, "reason": "closed (by design)", "kind": "closed"}
    assert _letters() == []


# ---- L6 --------------------------------------------------------------------

def _stamp_probe(host: str, age_s: float) -> None:
    when = datetime.now(timezone.utc) - timedelta(seconds=age_s)
    db_mod.upsert_host(host, probed_at=when.isoformat(timespec="seconds"))


def _probing(host: str):
    """A far side that answers `probe` and writes its probed_at, like verb_probe."""
    def fn(h, verb, args):
        db_mod.upsert_host(host, probed_at=db_mod.now_iso())
        return _probe_reply(host)
    return fn


def test_l6_green_when_probe_answers_in_time_and_the_hosts_row_is_fresh(hub, monkeypatch):
    far = _far(monkeypatch, _probing("contabo"))
    assert m.l6_probe("contabo") == {"ok": True, "reason": None}
    assert far.calls == [("contabo", "probe", (), m.L6_MAX_S)]  # bounded by the 60 s rule


def test_l6_the_running_host_answers_in_process_so_it_is_never_closed(hub, monkeypatch):
    assert not hub_config.host("mac").get("mesh_ssh")  # the Mac has none, yet it is not closed
    _far(monkeypatch, _probing("mac"))
    assert m.l6_probe("mac")["ok"] is True


def test_l6_red_when_the_hosts_row_is_stale_or_missing(hub, monkeypatch):
    _far(monkeypatch, lambda h, v, a: _probe_reply("contabo"))  # answers, never writes the row
    cell = m.l6_probe("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "not fresh" in cell["reason"]
    _stamp_probe("contabo", age_s=5 * 60)
    cell = m.l6_probe("contabo")
    assert cell["ok"] is False and "last one" in cell["reason"]


def test_l6_freshness_is_the_routers_own_rule_not_a_copy_of_its_number(hub, monkeypatch):
    _far(monkeypatch, lambda h, v, a: _probe_reply("contabo"))
    _stamp_probe("contabo", age_s=30)
    assert m.l6_probe("contabo")["ok"] is True
    monkeypatch.setattr(router, "PROBE_MAX_AGE_S", 10)
    cell = m.l6_probe("contabo")
    assert cell["ok"] is False and "not fresh" in cell["reason"]


def test_l6_red_when_probe_answers_as_another_host_or_is_refused(hub, monkeypatch):
    _far(monkeypatch, lambda h, v, a: _probe_reply("winbox"))
    assert "'winbox'" in m.l6_probe("contabo")["reason"]
    _far(monkeypatch, lambda h, v, a: {"ok": False, "verb": v, "error": "boom"})
    cell = m.l6_probe("contabo")
    assert cell["ok"] is False and "kind" not in cell and "probe refused" in cell["reason"]


def test_l6_red_when_the_answer_takes_the_full_minute(hub, monkeypatch):
    _far(monkeypatch, _probing("contabo"))
    ticks = iter([100.0, 100.0 + m.L6_MAX_S + 1])
    monkeypatch.setattr(m, "time", types.SimpleNamespace(monotonic=lambda: next(ticks)))
    cell = m.l6_probe("contabo")
    assert cell["ok"] is False and "kind" not in cell
    assert "took 61 s" in cell["reason"]


def test_l6_unreachable_when_probe_gets_no_answer_or_the_hub_cannot_be_read(hub, monkeypatch):
    def down(h, v, a):
        raise mesh.MeshUnreachable("probe on contabo: ssh failed")

    _far(monkeypatch, down)
    assert m.l6_probe("contabo")["kind"] == "unreachable"

    _far(monkeypatch, _probing("contabo"))

    def boom(host):
        raise RuntimeError("hub down")

    monkeypatch.setattr(db_mod, "get_host", boom)
    assert m.l6_probe("contabo")["kind"] == "unreachable"


def test_l6_a_host_with_no_mesh_ssh_is_closed_when_it_is_not_the_one_we_run_on(hub, monkeypatch):
    _as_host(monkeypatch, "contabo")
    _far(monkeypatch, lambda *a: pytest.fail("must not be dialled"))
    assert m.l6_probe("mac") == {"ok": False, "reason": "closed (by design)", "kind": "closed"}


# ---- L7 --------------------------------------------------------------------

def _hosts_rows() -> list[dict]:
    base = {"status": "online", "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "running": 0, "max_workers": 3, "load_per_core": 0.1, "ram_free_gb": 8.0,
            "runners": json.dumps(["claude"])}
    return [
        {"host": "contabo", **base, "provides": json.dumps(["always_on", "api"])},
        {"host": "winbox", **base, "max_workers": 2, "provides": json.dumps(["chrome", "win_gui"])},
        {"host": "mac", **base, "max_workers": 4, "provides": json.dumps(["chrome", "macos_cu"])},
    ]


def _with_rows(monkeypatch, rows):
    monkeypatch.setattr(db_mod, "list_hosts", lambda: rows)


def _never_write_hosts(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("L7 must never write the hosts table")
    monkeypatch.setattr(db_mod, "upsert_host", boom)


def test_l7_green_always_on_picks_contabo_and_win_gui_picks_winbox_then_no_host_when_stale(hub, monkeypatch):
    rows = _hosts_rows()
    _with_rows(monkeypatch, rows)
    _never_write_hosts(monkeypatch)
    before = copy.deepcopy(rows)
    assert m.l7_probe() == {"contabo": {"ok": True, "reason": None},
                            "winbox": {"ok": True, "reason": None}}
    assert rows == before  # the stale winbox row was made in a COPY


def test_l7_red_when_always_on_does_not_pick_contabo(hub, monkeypatch):
    rows = _hosts_rows()
    rows[0]["provides"] = json.dumps(["api"])  # contabo no longer provides always_on
    _with_rows(monkeypatch, rows)
    cells = m.l7_probe()
    assert cells["contabo"]["ok"] is False and "kind" not in cells["contabo"]
    assert "needs always_on" in cells["contabo"]["reason"] and "no_host" in cells["contabo"]["reason"]
    assert cells["winbox"]["ok"] is True


def test_l7_red_when_win_gui_picks_another_host(hub, monkeypatch):
    rows = _hosts_rows()
    rows[2]["provides"] = json.dumps(["win_gui"])  # the Mac claims win_gui and is less loaded
    rows[2]["load_per_core"] = 0.0
    _with_rows(monkeypatch, rows)
    cell = m.l7_probe()["winbox"]
    assert cell["ok"] is False and "kind" not in cell
    assert "picked 'mac'" in cell["reason"]


def test_l7_red_when_a_stale_winbox_still_gets_the_task(hub, monkeypatch):
    """A router with a fallback host would pass the first half and fail this."""
    rows = _hosts_rows()
    _with_rows(monkeypatch, rows)
    monkeypatch.setattr(router, "pick_host",
                        lambda task, hosts_rows=None, now=None: router.HostPick("winbox", "host: winbox"))
    cell = m.l7_probe()["winbox"]
    assert cell["ok"] is False and "expected no_host" in cell["reason"]


def test_l7_red_when_the_live_winbox_probe_is_already_stale(hub, monkeypatch):
    rows = _hosts_rows()
    rows[1]["probed_at"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(timespec="seconds")
    _with_rows(monkeypatch, rows)
    cell = m.l7_probe()["winbox"]
    assert cell["ok"] is False and "kind" not in cell
    assert "no probe" in cell["reason"]


def test_l7_unreachable_when_the_hub_cannot_be_read(hub, monkeypatch):
    def boom():
        raise RuntimeError("hub down")

    monkeypatch.setattr(db_mod, "list_hosts", boom)
    cells = m.l7_probe()
    assert {c["kind"] for c in cells.values()} == {"unreachable"}
    assert set(cells) == {"contabo", "winbox"}


# ---- L8 --------------------------------------------------------------------

def _drill(tmp_path: Path, **over) -> Path:
    data = {"ok": True, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "host": "testbox", "steps": [{"name": "mint", "ok": True}, {"name": "join", "ok": True}]}
    data.update(over)
    (tmp_path / m.JOIN_DRILL_FILE).write_text(json.dumps(data))
    return tmp_path


def test_l8_missing_file_is_not_run_and_never_green(tmp_path):
    cell = m.check_l8(tmp_path, events=lambda: None)
    assert cell["ok"] is False and cell["kind"] == "not_run"
    assert "no join_drill event" in cell["reason"]


def test_l8_green_for_a_fresh_ok_drill_with_steps(tmp_path):
    cell = m.check_l8(_drill(tmp_path))
    assert cell["ok"] is True and "testbox" in cell["note"]


def test_l8_seven_days_is_the_edge(tmp_path):
    now = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    ok = _drill(tmp_path, at=(now - timedelta(days=6, hours=23)).isoformat())
    assert m.check_l8(ok, now)["ok"] is True
    old = _drill(tmp_path, at=(now - timedelta(days=7, hours=1)).isoformat())
    cell = m.check_l8(old, now)
    assert cell["ok"] is False and "kind" not in cell and "days old" in cell["reason"]


def test_l8_red_when_the_drill_failed_names_the_failed_step(tmp_path):
    cell = m.check_l8(_drill(tmp_path, ok=False, steps=[{"name": "mint", "ok": True},
                                                       {"name": "accept", "ok": False}]))
    assert cell["ok"] is False and "kind" not in cell and "accept" in cell["reason"]


@pytest.mark.parametrize("over", [
    {"ok": "yes"}, {"host": ""}, {"steps": "none"}, {"at": "yesterday"}, {"at": None},
    {"steps": []},                                              # ok with nothing recorded
    {"steps": [{"name": "mint", "ok": True}, {"name": "join", "ok": False}]},  # ok with a failed step
    {"at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()},      # dated in the future
])
def test_l8_red_when_the_file_is_malformed_or_contradicts_itself(tmp_path, over):
    cell = m.check_l8(_drill(tmp_path, **over))
    assert cell["ok"] is False and "kind" not in cell


def test_l8_red_when_the_file_is_not_json_or_not_an_object(tmp_path):
    (tmp_path / m.JOIN_DRILL_FILE).write_text("{not json")
    assert m.check_l8(tmp_path)["ok"] is False
    (tmp_path / m.JOIN_DRILL_FILE).write_text("[1]")
    assert m.check_l8(tmp_path)["ok"] is False


# ---- L8: the join_drill events row, for a machine that never ran the drill --------

def _event(**over) -> dict:
    data = {"ok": True, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "host": "drill-20261003-140000",
            "steps": [{"name": "join", "ok": True, "detail": "x"}, {"name": "probe", "ok": True}]}
    data.update(over)
    return data


def test_l8_reads_the_event_when_the_file_is_missing_and_goes_green(tmp_path):
    cell = m.check_l8(tmp_path, events=lambda: _event())
    assert cell["ok"] is True and "drill-20261003-140000" in cell["note"]


def test_l8_the_file_wins_over_an_event(tmp_path):
    cell = m.check_l8(_drill(tmp_path, ok=False, steps=[{"name": "mint", "ok": False}]),
                      events=lambda: _event())
    assert cell["ok"] is False and "mint" in cell["reason"]


def test_l8_event_gets_the_same_checks_as_the_file(tmp_path):
    now = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    old = _event(at=(now - timedelta(days=8)).isoformat())
    cell = m.check_l8(tmp_path, now, events=lambda: old)
    assert cell["ok"] is False and "kind" not in cell and "days old" in cell["reason"]
    failed = _event(ok=False, steps=[{"name": "join", "ok": True}, {"name": "probe", "ok": False}])
    cell = m.check_l8(tmp_path, events=lambda: failed)
    assert cell["ok"] is False and "probe" in cell["reason"]
    for bad in ({"ok": "yes"}, {"host": ""}, {"steps": []}, {"at": "yesterday"}):
        assert m.check_l8(tmp_path, events=lambda bad=bad: _event(**bad))["ok"] is False
    assert m.check_l8(tmp_path, events=lambda: [1])["ok"] is False


def test_l8_hub_that_cannot_be_read_is_not_run_not_green_and_not_a_crash(tmp_path):
    def boom():
        raise RuntimeError("hub down")

    cell = m.check_l8(tmp_path, events=boom)
    assert cell["ok"] is False and cell["kind"] == "not_run" and "RuntimeError" in cell["reason"]


def test_join_drill_record_then_latest_round_trip_and_the_newest_wins(hub, tmp_path):
    assert m.latest_join_drill() is None
    assert m.check_l8(tmp_path)["kind"] == "not_run"                 # the real reader, empty hub
    m.join_drill_record(_event(ok=False, host="drill-old", steps=[{"name": "join", "ok": False}]))
    m.join_drill_record(_event())
    got = m.latest_join_drill()
    assert got["host"] == "drill-20261003-140000" and got["ok"] is True
    cell = m.check_l8(tmp_path)                                      # the Mac: no file, real reader
    assert cell["ok"] is True and "drill-20261003-140000" in cell["note"]


def test_join_drill_record_refuses_a_bad_or_oversized_payload(hub):
    for bad in ([1], {"host": 3}, {"host": "h", "pad": "x" * (m.JOIN_DRILL_MAX_BYTES + 1)}):
        with pytest.raises(ValueError):
            m.join_drill_record(bad)
    assert m.latest_join_drill() is None


def test_join_drill_task_is_pending_targeted_and_carries_the_l3_probe_path(hub):
    tid = m.join_drill_task_create("drill-20261003-140000")
    task = hub.get_task(tid)
    assert task["status"] == "pending" and task["host"] == "drill-20261003-140000"
    assert task["project"] == "mooniex-agents" and task["role"] == "developer"
    assert "docs/ops/mesh-probe/contabo-drill-20261003-140000.md" in json.dumps(task["touches"])
    assert "mesh-probe:" in task["description"]
    with pytest.raises(ValueError):
        m.join_drill_task_create("Bad Host; rm -rf /")


def test_join_drill_task_close_cancels_once(hub):
    tid = m.join_drill_task_create("drill-20261003-140000")
    assert m.join_drill_task_close(tid) is True
    assert hub.get_task(tid)["status"] == "cancelled"


def test_join_drill_cli_verbs_and_exit_codes(hub, tmp_path, capsys):
    assert m.join_drill_cli("task-create", "drill-20261003-140000") == 0
    tid = capsys.readouterr().out.strip().splitlines()[-1]
    assert tid.startswith("task-")
    assert m.join_drill_cli("task-close", tid) == 0
    f = tmp_path / "d.json"
    f.write_text(json.dumps(_event()))
    assert m.join_drill_cli("record", str(f)) == 0
    assert m.latest_join_drill()["host"] == "drill-20261003-140000"
    f.write_text("{not json")
    assert m.join_drill_cli("record", str(f)) == 2
    assert m.join_drill_cli("record", str(tmp_path / "nope.json")) == 2
    assert m.join_drill_cli("task-create", "Bad Host") == 2
    assert m.join_drill_cli("explode", "x") == 2
    assert "unknown verb" in capsys.readouterr().err


def test_join_drill_flag_needs_no_expect_and_hands_over_to_the_cli(monkeypatch):
    seen = []
    monkeypatch.setattr(m, "join_drill_cli", lambda verb, arg: seen.append((verb, arg)) or 0)
    assert asyncio.run(m.amain(["--join-drill", "task-close", "task-0123abcd"])) == 0
    assert seen == [("task-close", "task-0123abcd")]


# ---- INV -------------------------------------------------------------------

def _row(host, dispatcher, runner="claude", status="in_progress") -> str:
    tid = db_mod.create_task("mooniex-agents", "developer", "t", "d")
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET host=?, dispatcher_host=?, runner=?, status=? WHERE id=?",
                     (host, dispatcher, runner, status, tid))
    return tid


def test_inv_green_when_every_candidate_row_has_exactly_one_poller(hub):
    _row("contabo", "mac")                 # remote claude row: the dispatcher (mac) polls it
    _row("contabo", "contabo", "codex")    # a launcher run on its own box: that box polls it
    _row("mac", "mac", "claude")           # local claude row: nobody polls, not a candidate
    cell = m.check_invariant()
    assert cell["ok"] is True
    assert cell["rows"] == 2 and cell["note"] == "2 rows"


def test_inv_red_names_a_row_nobody_polls_and_a_row_every_host_polls(hub):
    zero = _row("contabo", "ghost-box")    # dispatched by a host that is not in hosts.yaml
    many = _row(None, None, "codex")       # a launcher run nobody placed: every host claims it
    legacy = _row("contabo", None)         # no dispatcher_host: every host but contabo believes it dispatched it
    fine = _row("winbox", "mac")
    cell = m.check_invariant()
    assert cell["ok"] is False and "kind" not in cell
    assert any(o.startswith(f"{legacy} (2 pollers: mac, winbox") for o in cell["offenders"])
    assert any(o.startswith(f"{zero} (0 pollers") for o in cell["offenders"])
    assert any(o.startswith(f"{many} (3 pollers") for o in cell["offenders"])
    assert not any(fine in o for o in cell["offenders"])
    assert zero in cell["reason"] and many in cell["reason"]
    assert cell["rows"] == 4


def test_inv_ignores_rows_that_are_not_in_progress(hub):
    _row("contabo", "ghost-box", status="done")
    assert m.check_invariant()["ok"] is True


def test_inv_is_read_only_and_puts_self_host_back(hub, monkeypatch):
    _row("contabo", "mac")

    def boom(*a, **kw):
        raise AssertionError("INV must not write")

    monkeypatch.setattr(db_mod, "update_status", boom)
    monkeypatch.setattr(db_mod, "upsert_host", boom)
    with db_mod.get_conn() as conn:
        before = [dict(r) for r in conn.execute("SELECT * FROM tasks").fetchall()]
    assert m.check_invariant()["ok"] is True
    with db_mod.get_conn() as conn:
        assert [dict(r) for r in conn.execute("SELECT * FROM tasks").fetchall()] == before
    import os
    assert os.environ["ORG_HOST"] == "mac" and hub_config.self_host() == "mac"


def test_self_host_as_restores_an_unset_variable(monkeypatch):
    import os
    monkeypatch.delenv("ORG_HOST", raising=False)
    with m._self_host_as("contabo"):
        assert hub_config.self_host() == "contabo"
    assert "ORG_HOST" not in os.environ
    hub_config.self_host.cache_clear()


def test_inv_unreachable_when_the_hub_cannot_be_read(hub, monkeypatch):
    def boom(**kw):
        raise RuntimeError("hub down")

    monkeypatch.setattr(db_mod, "list_tasks", boom)
    cell = m.check_invariant()
    assert cell["ok"] is False and cell["kind"] == "unreachable"


# ---- render, scoping and the exit code -------------------------------------

def _empty() -> dict:
    return {lvl: ({"all": {}} if lvl in m.SINGLE_LEVELS else {h: {} for h in m.HOSTS})
            for lvl in m.LEVELS}


def _row_of(md: str, level: str, first_col: str) -> str:
    start = md.index(f"## {level}\n")
    nxt = md.find("\n## ", start + 1)
    section = md[start: nxt if nxt != -1 else len(md)]
    return [ln for ln in section.splitlines() if ln.startswith(f"| {first_col} ")][0]


def test_render_a_target_with_no_mesh_ssh_is_closed_by_design_and_never_counts():
    md, any_fail, n_ok, n_fail = m.render(_empty(), "w3")
    for level in ("SEC", "L5"):
        for frm in ("contabo", "winbox"):
            cells = _row_of(md, level, frm).split("|")[1:-1]
            assert cells[m.HOSTS.index("mac") + 1].strip() == "closed (by design)"
    assert (any_fail, n_ok, n_fail) == (False, 0, 0)


def test_render_unreachable_is_failing_but_reads_differently_from_red():
    combined = _empty()
    combined["SEC"]["mac"]["contabo"] = m._unreachable("probe on contabo: ssh failed")
    combined["SEC"]["mac"]["winbox"] = m._red("'bash' ran in a shell")
    md, any_fail, n_ok, n_fail = m.render(combined, "w3")  # SEC into winbox is w3
    row = _row_of(md, "SEC", "mac")
    assert "UNREACHABLE(probe on contabo: ssh failed)" in row
    assert "FAIL('bash' ran in a shell)" in row
    assert any_fail is True and n_fail == 2


def test_render_a_computed_closed_cell_never_counts():
    combined = _empty()
    combined["L6"]["mac"]["mac"] = m._closed()
    md, any_fail, n_ok, n_fail = m.render(combined, "w2")
    assert "closed (by design)" in _row_of(md, "L6", "mac")
    assert (any_fail, n_ok, n_fail) == (False, 0, 0)


def test_render_ok_cell_shows_its_note():
    combined = _empty()
    combined["L5"]["mac"]["contabo"] = m._green("wake not reported")
    md, any_fail, n_ok, n_fail = m.render(combined, "w2")
    assert "ok (wake not reported)" in _row_of(md, "L5", "mac")
    assert (any_fail, n_ok) == (False, 1)


def test_render_single_level_cells_inv_and_l8():
    combined = _empty()
    combined["INV"]["all"]["all"] = {"ok": False, "reason": "1 of 2 rows: task-1234abcd (0 pollers)"}
    md, any_fail, n_ok, n_fail = m.render(combined, "w1")
    assert "| one poller per remote row | FAIL(1 of 2 rows: task-1234abcd (0 pollers)) |" in md
    assert any_fail is True
    # L8 is w4: a "not run" at w3 is not claimed yet, at w4 it fails the run
    combined = _empty()
    combined["L8"]["all"]["all"] = {"ok": False, "reason": "no drill recorded", "kind": "not_run"}
    md, any_fail, _, _ = m.render(combined, "w3")
    assert "| join drill | n/a |" in md and any_fail is False
    md, any_fail, _, n_fail = m.render(combined, "w4")
    assert "| join drill | not run (no drill recorded) |" in md
    assert any_fail is True and n_fail == 1


def test_render_new_levels_do_not_count_before_their_wave():
    combined = _empty()
    for lvl, frm, to in (("SEC", "mac", "contabo"), ("L5", "mac", "winbox"),
                         ("L6", "winbox", "winbox"), ("L7", "contabo", "contabo")):
        combined[lvl][frm][to] = m._red("boom")
    _, any_fail, _, n_fail = m.render(combined, "w1")
    assert (any_fail, n_fail) == (False, 0)
    _, any_fail, _, n_fail = m.render(combined, "w2")
    assert n_fail == 2  # L5 mac->winbox and L6 winbox are w3
    _, _, _, n_fail = m.render(combined, "w3")
    assert n_fail == 4


def test_sec_cells_touching_winbox_wait_for_w3_like_the_other_winbox_cells():
    # node_dispatch on Windows and the winbox forced-command line are W3.3/W3.4,
    # so a w2 run must be able to go green on Mac <-> Contabo alone.
    for frm, to in (("mac", "winbox"), ("contabo", "winbox"), ("winbox", "contabo"), ("winbox", "mac")):
        assert m.EXPECT[("SEC", frm, to)] == "w3"
    for frm, to in (("mac", "contabo"), ("contabo", "mac")):
        assert m.EXPECT[("SEC", frm, to)] == "w2"
    combined = _empty()
    combined["SEC"]["mac"]["winbox"] = m._unreachable("probe on winbox: ssh failed")
    md, any_fail, _, n_fail = m.render(combined, "w2")
    assert (any_fail, n_fail) == (False, 0)
    assert "UNREACHABLE" not in _row_of(md, "SEC", "mac")


def _stub_levels(monkeypatch, calls):
    monkeypatch.setattr(m, "check_sec", lambda to: calls.append(("SEC", to)) or m._green())
    monkeypatch.setattr(m, "l5_probe", lambda frm, to: calls.append(("L5", frm, to)) or m._green())
    monkeypatch.setattr(m, "l6_probe", lambda h: calls.append(("L6", h)) or m._green())

    def l7(cases):
        calls.append(("L7", tuple(c[0] for c in cases)))
        return {c[0]: m._green() for c in cases}

    monkeypatch.setattr(m, "l7_probe", l7)


def test_run_mesh_levels_touches_only_claimed_cells_and_probes_before_the_router_reads(monkeypatch):
    calls: list[tuple] = []
    _stub_levels(monkeypatch, calls)
    combined = _empty()
    m._run_mesh_levels(combined, "mac", "w2")
    assert ("SEC", "contabo") in calls and ("SEC", "winbox") not in calls  # w3
    assert ("L5", "mac", "contabo") in calls and ("L5", "mac", "winbox") not in calls  # w3
    assert ("L6", "mac") in calls and ("L6", "contabo") in calls and ("L6", "winbox") not in calls
    assert ("L7", ("contabo",)) in calls
    assert calls.index(("L6", "contabo")) < calls.index(("L7", ("contabo",)))  # L6 freshens the rows
    assert combined["SEC"]["mac"]["contabo"]["ok"] is True
    assert combined["L7"]["contabo"]["contabo"]["ok"] is True
    assert "winbox" not in combined["L5"]["mac"]  # w3: not claimed yet, so not computed


def test_run_mesh_levels_writes_nothing_before_w2(monkeypatch):
    calls: list[tuple] = []
    _stub_levels(monkeypatch, calls)
    m._run_mesh_levels(_empty(), "mac", "w1")
    assert calls == []


def _amain_stubs(monkeypatch, tmp_path, calls):
    monkeypatch.setattr(m, "_running_host_guess", lambda root: "mac")
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))
    monkeypatch.setattr(m, "check_l2", _async_return((True, None)))
    monkeypatch.setattr(m, "check_l1", lambda target: (True, None))
    monkeypatch.setattr(m, "l4_probe", lambda frm, to: (True, None))
    monkeypatch.setattr(m, "_collect_peer_local", lambda alias, cfg, script_path: None)
    monkeypatch.setattr(m, "write_state", lambda combined, args, running_host: tmp_path / "latest.json")
    monkeypatch.setattr(m, "run_l3_probe", _async_return((True, None)))  # --live must not reach the real L3
    monkeypatch.setattr(m, "check_invariant", lambda: calls.append("INV") or m._green("0 rows"))
    monkeypatch.setattr(m, "check_l8", lambda state_dir: calls.append("L8") or m._green())
    _stub_levels(monkeypatch, calls)


def test_amain_without_live_never_dials_but_still_reads_the_invariant(monkeypatch, tmp_path, capsys):
    calls: list = []
    _amain_stubs(monkeypatch, tmp_path, calls)
    assert asyncio.run(m.amain(["--expect", "w2"])) == 0
    assert calls == ["INV"]  # SEC / L5 / L6 / L7 need --live; L8 is claimed at w4
    out = capsys.readouterr().out
    assert "## SEC" in out and "## INV" in out and "| one poller per remote row | ok (0 rows) |" in out


def test_amain_live_exits_1_on_an_unreachable_cell_and_prints_it(monkeypatch, tmp_path, capsys):
    calls: list = []
    _amain_stubs(monkeypatch, tmp_path, calls)
    monkeypatch.setattr(m, "check_sec",
                        lambda to: m._unreachable("probe on contabo: ssh failed") if to == "contabo" else m._green())
    assert asyncio.run(m.amain(["--expect", "w2", "--live"])) == 1
    assert "UNREACHABLE(probe on contabo: ssh failed)" in capsys.readouterr().out


def test_amain_live_exits_0_when_everything_claimed_is_green_or_closed(monkeypatch, tmp_path, capsys):
    calls: list = []
    _amain_stubs(monkeypatch, tmp_path, calls)
    assert asyncio.run(m.amain(["--expect", "w2", "--live"])) == 0
    assert "closed (by design)" in capsys.readouterr().out  # SEC / L5 into the Mac


# ---------------------------------------------------------------------------
# Text decoding: every text-mode subprocess call names utf-8 (task-47202255)
#
# text=True alone decodes with the locale codec, cp1252 on winbox, and a byte
# like 0x81 then kills the reader thread with UnicodeDecodeError. A new call that
# forgets the encoding must fail here, not on a Windows box later.
# ---------------------------------------------------------------------------

_SUBPROCESS_CALLS = {"run", "Popen", "check_output", "check_call", "call"}


def _kw(call: "ast.Call") -> dict:
    return {k.arg: k.value for k in call.keywords if k.arg}


def _is_true(node) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _is_const(node, value) -> bool:
    return isinstance(node, ast.Constant) and node.value == value


def _text_calls_without_utf8(source: str) -> tuple[int, list[int]]:
    """(text-mode subprocess calls seen, line numbers of those that do not pass
    encoding="utf-8" and errors="replace"). A call that hides its keywords behind
    **kwargs counts as lacking them: the walker cannot see them."""
    seen, bad = 0, []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in _SUBPROCESS_CALLS
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"):
            continue
        kw = _kw(node)
        if not (_is_true(kw.get("text")) or _is_true(kw.get("universal_newlines"))):
            continue
        seen += 1
        if not (_is_const(kw.get("encoding"), "utf-8") and _is_const(kw.get("errors"), "replace")):
            bad.append(node.lineno)
    return seen, bad


def test_every_text_mode_subprocess_call_in_mesh_check_names_utf8():
    seen, bad = _text_calls_without_utf8((ROOT / "tools" / "mesh_check.py").read_text(encoding="utf-8"))
    assert seen >= 10, f"walker saw only {seen} text-mode calls; it has stopped finding them"
    assert bad == [], f"text=True without encoding='utf-8', errors='replace' at lines {bad}"


def test_the_utf8_walker_can_fail():
    """A check that cannot fail is worthless: prove the walker flags each way to miss."""
    ok = 'subprocess.run(c, text=True, encoding="utf-8", errors="replace")'
    assert _text_calls_without_utf8(ok) == (1, [])
    for src in ("subprocess.run(c, text=True)",
                "subprocess.run(c, universal_newlines=True)",
                'subprocess.run(c, text=True, encoding="utf-8")',
                'subprocess.check_output(c, text=True, encoding="cp1252", errors="replace")',
                "subprocess.run(c, text=True, **opts)"):
        seen, bad = _text_calls_without_utf8(src)
        assert (seen, bad) == (1, [1]), src
    assert _text_calls_without_utf8("subprocess.run(c, capture_output=True)") == (0, [])


def test_ssh_run_passes_utf8_and_replace_to_subprocess(monkeypatch):
    """The keywords reach subprocess.run, not only the source text the walker reads."""
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return _FakeCompleted(returncode=0, stdout="ok")
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    assert m._ssh_run("mooniex-vps", "true", timeout=5) == "ok"
    assert seen["encoding"] == "utf-8" and seen["errors"] == "replace"
