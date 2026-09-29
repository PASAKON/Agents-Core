"""Org Mesh W0.3 (task-6f6e5179): a C-level on ANY host delegates locally and to a spoke.

Covers the six behaviours the task pins:

  1. self_host()=contabo and no `host` arg  -> local spawn, no ssh at all
  2. non-darwin                             -> osascript/`open` never run, tmux is
  3. create_worktree                        -> the host path from projects.yaml
  4. remote deploy                          -> bytes are `git show origin/<base>:<path>`,
                                               even when the working-tree copy is dirty
  5. remote deploy                          -> nothing lands under the spoke's tracked scripts/
  6. worker MCP config                      -> on the Mac it parses equal to the template

No real tasks.db, no Postgres, no ssh, no network: subprocess is faked for
ssh/scp, git runs against throwaway repos in tmp_path, and every spawn side
effect is stubbed.
"""
from __future__ import annotations

import asyncio
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
import lib.db as db_mod  # noqa: E402
import lib.worker_mcp_config as wmc  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.worktree as worktree_mod  # noqa: E402

_REAL_RUN = subprocess.run


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _git(cwd: Path, *args: str) -> str:
    r = _REAL_RUN(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                  cwd=str(cwd), capture_output=True, text=True, check=True)
    return r.stdout


def _commit_files(repo: Path, files: dict[str, str], msg: str) -> None:
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)


def _origin_and_clone(tmp_path: Path, files: dict[str, str]) -> tuple[Path, Path]:
    """A bare origin with `files` on main, plus a clone standing in for the hub's repo."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "--initial-branch=main", str(origin))
    seed = tmp_path / "seed"
    _git(tmp_path, "clone", "-q", str(origin), str(seed))
    _commit_files(seed, files, "v1")
    _git(seed, "push", "-q", "origin", "HEAD:main")
    hub = tmp_path / "hub"
    _git(tmp_path, "clone", "-q", str(origin), str(hub))
    return origin, hub


def _push_from_seed(tmp_path: Path, files: dict[str, str], msg: str) -> None:
    seed = tmp_path / "seed"
    _commit_files(seed, files, msg)
    _git(seed, "push", "-q", "origin", "HEAD:main")


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_ROUTER", "off")  # the runner-routing hook is not under test here
    db_mod.init()
    return db_mod


@pytest.fixture(autouse=True)
def _clear_self_host_cache():
    config.self_host.cache_clear()
    yield
    config.self_host.cache_clear()


# ---------------------------------------------------------------------------
# 1 + 2. local spawn on a non-Mac self_host
# ---------------------------------------------------------------------------

class _Spawn:
    """Everything a local spawn touches, recorded; nothing real runs."""

    def __init__(self):
        self.subprocess_argv: list[list[str]] = []
        self.tmux_created: list[dict] = []
        self.iterm_calls: list[dict] = []
        self.worktree: Path | None = None


@pytest.fixture()
def local_spawn(temp_db, monkeypatch, tmp_path):
    rec = _Spawn()
    wt = tmp_path / "wt"
    wt.mkdir()
    _git(wt, "init", "-q", "-b", "main")

    def fake_run(argv, *a, **kw):
        rec.subprocess_argv.append([str(x) for x in argv])
        if argv and argv[0] == "git":
            return _REAL_RUN(argv, *a, **kw)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    proj = {"key": "test-project", "name": "t", "remote": "git@github.com:t/t.git",
            "path": "/nowhere/mac", "paths": {"contabo": "/nowhere/contabo"},
            "default_branch": "main", "agents_allowed": ["developer"],
            "spawn_backend": "iterm", "web_ui": "on"}

    def fake_create_worktree(project_key, role, task_id, sparse=False):
        return {"project": project_key, "task_id": task_id, "role": role,
                "branch": f"agent/{role}-{task_id}", "worktree": str(wt),
                "base": "main", "repo": "/nowhere", "provisioned": []}

    def fake_tmux_create(name, *, cwd, cmd):
        rec.tmux_created.append({"name": name, "cmd": cmd})

    def fake_iterm(role, task_id, **kw):
        rec.iterm_calls.append({"role": role, "task_id": task_id, **kw})
        return "spawned"

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "get_project", lambda key: proj)
    monkeypatch.setattr(delegate, "create_worktree", fake_create_worktree)
    monkeypatch.setattr(delegate, "_spawn_iterm_tab", fake_iterm)
    monkeypatch.setattr(delegate.tmux, "create", fake_tmux_create)
    monkeypatch.setattr(delegate.tmux, "pick_free_port", lambda: 7681)
    monkeypatch.setattr(delegate.tmux, "start_ttyd", lambda *a, **k: 4242)
    monkeypatch.setattr(delegate, "_spawn_background", lambda coro: coro.close())
    rec.worktree = wt
    return rec


def _new_task(temp_db, **kw) -> str:
    return temp_db.create_task(project="test-project", role="developer", title="t",
                               description="d", owner_cto="someone-else", **kw)


def _ssh_or_scp(rec: _Spawn) -> list[list[str]]:
    return [a for a in rec.subprocess_argv if a and a[0] in ("ssh", "scp")]


def test_self_host_contabo_no_host_arg_spawns_locally_without_ssh(local_spawn, temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "self_host", lambda: "contabo")
    monkeypatch.setattr(sys, "platform", "linux")
    tid = _new_task(temp_db)

    row = asyncio.run(delegate.delegate_task(tid))

    assert row["host"] == "contabo"
    assert _ssh_or_scp(local_spawn) == [], "a spawn on the box itself must never ssh"
    assert len(local_spawn.tmux_created) == 1
    assert tid in local_spawn.tmux_created[0]["cmd"]


def test_local_spawn_writes_the_same_task_sidecar_as_a_remote_spawn(local_spawn, temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "self_host", lambda: "contabo")
    monkeypatch.setattr(sys, "platform", "linux")
    tid = _new_task(temp_db, touches=["docs/x.md"])

    asyncio.run(delegate.delegate_task(tid))

    sidecar = local_spawn.worktree / ".org-task.json"
    assert sidecar.is_file()
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    meta = json.loads(sidecar.read_text())
    assert meta["task_id"] == tid and meta["host"] == "contabo" and meta["role"] == "developer"
    assert meta["touches"] == ["docs/x.md"]
    status = _git(local_spawn.worktree, "status", "--porcelain")
    assert ".org-task.json" not in status, "the sidecar must be git-excluded"


def test_non_darwin_never_runs_osascript_or_open_and_uses_tmux(local_spawn, temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "self_host", lambda: "contabo")
    monkeypatch.setattr(sys, "platform", "linux")
    tid = _new_task(temp_db)

    asyncio.run(delegate.delegate_task(tid))

    assert local_spawn.iterm_calls == [], "iTerm is Mac-only"
    binaries = {a[0] for a in local_spawn.subprocess_argv if a}
    assert "osascript" not in binaries and "open" not in binaries
    assert len(local_spawn.tmux_created) == 1


def test_darwin_keeps_the_iterm_tab(local_spawn, temp_db, monkeypatch):
    """The Mac path must not change: the iTerm tab is spawned."""
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    monkeypatch.setattr(sys, "platform", "darwin")
    tid = _new_task(temp_db)

    asyncio.run(delegate.delegate_task(tid))

    assert len(local_spawn.iterm_calls) == 1


# ---------------------------------------------------------------------------
# 3. create_worktree resolves the checkout for self_host()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("host", ["contabo", "mac"])
def test_create_worktree_uses_the_host_path_from_projects_yaml(tmp_path, monkeypatch, host):
    _o1, contabo_repo = _origin_and_clone(tmp_path / "c", {"README.md": "x\n"})
    _o2, mac_repo = _origin_and_clone(tmp_path / "m", {"README.md": "x\n"})
    proj = {"key": "test-project", "path": str(mac_repo), "default_branch": "main",
            "paths": {"mac": str(mac_repo), "contabo": str(contabo_repo)}}
    monkeypatch.setattr(config, "projects", lambda: {"test-project": proj})
    monkeypatch.setattr(worktree_mod, "self_host", lambda: host)
    monkeypatch.setattr(worktree_mod, "WORKTREE_DIR", tmp_path / "worktrees")
    monkeypatch.setattr(worktree_mod, "STORAGE_POLICY", tmp_path / "no-policy.yaml")

    info = worktree_mod.create_worktree("test-project", "developer", "task-w03host")

    expected = {"contabo": contabo_repo, "mac": mac_repo}[host]
    assert Path(info["repo"]) == expected
    assert (Path(info["worktree"]) / ".git").exists()
    listed = "\n".join(worktree_mod.list_worktrees("test-project"))
    assert Path(info["worktree"]).name in listed


def test_create_worktree_refuses_a_host_with_no_path(tmp_path, monkeypatch):
    proj = {"key": "test-project", "path": "/mac/only", "default_branch": "main"}
    monkeypatch.setattr(config, "projects", lambda: {"test-project": proj})
    monkeypatch.setattr(worktree_mod, "self_host", lambda: "contabo")
    monkeypatch.setattr(worktree_mod, "WORKTREE_DIR", tmp_path / "worktrees")
    with pytest.raises(ValueError, match="no path configured for host 'contabo'"):
        worktree_mod.create_worktree("test-project", "developer", "task-w03none")


# ---------------------------------------------------------------------------
# 4 + 5. remote deploy sources origin/<base>, writes nothing under scripts/
# ---------------------------------------------------------------------------

_LAUNCHER_V1 = "#!/usr/bin/env bash\necho launcher v1\n"
_LAUNCHER_V2 = "#!/usr/bin/env bash\necho launcher v2 -- merged on origin\n"
_DIRTY = "#!/usr/bin/env bash\necho DIRTY LOCAL EDIT, never merged\n"


class _Remote:
    def __init__(self):
        self.argv: list[list[str]] = []
        self.scp: list[dict] = []


@pytest.fixture()
def fake_remote(monkeypatch):
    rec = _Remote()

    def fake_run(argv, *a, **kw):
        argv = [str(x) for x in argv]
        if argv[0] == "git":
            return _REAL_RUN(argv, *a, **kw)
        rec.argv.append(argv)
        if argv[0] == "scp":
            # the staging dir is deleted right after the call: read it now
            rec.scp.append({"src_bytes": Path(argv[1]).read_bytes(), "dest": argv[2]})
        # an ssh sha probe answers with empty stdout = "file absent on the box"
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    return rec


def _dirty_hub(tmp_path: Path, monkeypatch) -> Path:
    """Hub repo whose origin/main is one commit STALE (proves the fetch) and
    whose working tree carries an unmerged edit of the launcher."""
    _origin, hub = _origin_and_clone(tmp_path, {"scripts/spawn-worker-remote.sh": _LAUNCHER_V1})
    _push_from_seed(tmp_path, {"scripts/spawn-worker-remote.sh": _LAUNCHER_V2}, "v2")
    (hub / "scripts" / "spawn-worker-remote.sh").write_text(_DIRTY)
    monkeypatch.setattr(delegate, "ROOT", hub)
    return hub


def test_linux_deploy_sends_the_origin_blob_not_the_dirty_working_tree(tmp_path, monkeypatch, fake_remote):
    hub = _dirty_hub(tmp_path, monkeypatch)
    host_cfg = {"ssh": "mooniex-vps", "agents_root": "/opt/MoonieXHQ/Agents/Core", "os": "linux"}

    actions = delegate._ensure_remote_deploy_linux(host_cfg, base="main")

    assert (hub / "scripts" / "spawn-worker-remote.sh").read_text() == _DIRTY  # left alone
    assert len(fake_remote.scp) == 1
    sent = fake_remote.scp[0]
    assert sent["src_bytes"] == _LAUNCHER_V2.encode(), "must be the fetched origin/main blob"
    assert sent["src_bytes"] != _DIRTY.encode()
    assert sent["dest"] == "mooniex-vps:/opt/MoonieXHQ/Agents/Core/.launch/spawn-worker-remote.sh"
    assert any("deployed spawn-worker-remote.sh" in a for a in actions)


def test_linux_deploy_writes_nothing_under_the_spokes_tracked_scripts(tmp_path, monkeypatch, fake_remote):
    _dirty_hub(tmp_path, monkeypatch)
    host_cfg = {"ssh": "mooniex-vps", "agents_root": "/opt/MoonieXHQ/Agents/Core", "os": "linux"}

    delegate._ensure_remote_deploy_linux(host_cfg, base="main")

    remote_argv = [a for a in fake_remote.argv if a[0] in ("ssh", "scp")]
    assert remote_argv, "the deploy must have run something"
    for argv in remote_argv:
        joined = " ".join(argv)
        assert "/Core/scripts" not in joined, f"touches the spoke's tracked scripts/: {joined}"
        assert "hook-self-repo-guard" not in joined, "the guard is no longer deployed"
    assert all(s["dest"].split(":", 1)[1].startswith("/opt/MoonieXHQ/Agents/Core/.launch/")
               for s in fake_remote.scp)


def test_windows_deploy_also_sends_origin_blobs(tmp_path, monkeypatch, fake_remote):
    files = {
        "windows/spawn-worker.ps1": "# ps1 v1\n",
        "roles/_worker_shared.md": "shared v1\n",
        "roles/_worker_remote.md": "remote v1\n",
        "roles/developer.md": "developer v1\n",
    }
    _origin, hub = _origin_and_clone(tmp_path, files)
    _push_from_seed(tmp_path, {"windows/spawn-worker.ps1": "# ps1 v2 on origin\n",
                               "roles/developer.md": "developer v2 on origin\n"}, "v2")
    (hub / "windows" / "spawn-worker.ps1").write_text("# DIRTY local ps1\n")
    (hub / "roles" / "developer.md").write_text("DIRTY local role doc\n")
    monkeypatch.setattr(delegate, "ROOT", hub)
    host_cfg = {"ssh": "winbox", "agents_root": "C:\\mooniex", "os": "windows"}

    delegate._ensure_remote_deploy(host_cfg, "developer", base="main")

    by_name = {Path(s["dest"].split(":", 1)[1].replace("\\", "/")).name: s["src_bytes"]
               for s in fake_remote.scp}
    assert by_name["spawn-worker.ps1"] == b"# ps1 v2 on origin\n"
    assert by_name["developer.md"] == b"developer v2 on origin\n"
    assert by_name["_worker_shared.md"] == b"shared v1\n"
    assert b"DIRTY" not in b"".join(by_name.values())


def test_deploy_dry_run_runs_no_subprocess_at_all(monkeypatch):
    def boom(*a, **k):
        raise AssertionError(f"dry-run ran a subprocess: {a}")

    monkeypatch.setattr(delegate.subprocess, "run", boom)
    host_cfg = {"ssh": "mooniex-vps", "agents_root": "/opt/x", "os": "linux"}
    out = delegate._ensure_remote_deploy_linux(host_cfg, dry_run=True, base="main")
    assert out and all(o.startswith("[dry-run]") for o in out)
    assert all(".launch/" in o for o in out)


# ---------------------------------------------------------------------------
# 6. worker MCP config
# ---------------------------------------------------------------------------

def _mac_inputs():
    return dict(venv_python=wmc.TEMPLATE_PYTHON, lungnote_js=wmc.TEMPLATE_LUNGNOTE_JS,
                lungnote_node="node")


def test_mac_generated_worker_mcp_config_parses_equal_to_the_template(monkeypatch):
    # The Mac's LungNote install is a fact about the machine running the test,
    # not about the generator: pin it so this holds on any box.
    monkeypatch.setattr(wmc, "_is_file", lambda p: True)
    template = json.loads(wmc.TEMPLATE.read_text())

    generated = wmc.generate(wmc.TEMPLATE_ROOT, **_mac_inputs())

    assert generated == template


def test_generated_config_for_another_host_has_no_mac_path(monkeypatch, capsys):
    monkeypatch.setattr(wmc, "_is_file", lambda p: p == "/opt/lungnote/index.js")
    generated = wmc.generate("/opt/MoonieXHQ/Agents/Core",
                             venv_python="/opt/MoonieXHQ/Agents/Core/.venv/bin/python",
                             lungnote_js="/opt/lungnote/index.js",
                             lungnote_node="/opt/node-v22/bin/node")

    assert "/Users/gob" not in json.dumps(generated)
    org = generated["mcpServers"]["org"]
    assert org["command"] == "/opt/MoonieXHQ/Agents/Core/.venv/bin/python"
    assert org["args"] == ["/opt/MoonieXHQ/Agents/Core/runners/worker_mcp_server.py"]
    assert org["cwd"] == "/opt/MoonieXHQ/Agents/Core"
    ln = generated["mcpServers"]["lungnote"]
    assert ln["args"] == ["/opt/lungnote/index.js"] and ln["command"] == "/opt/node-v22/bin/node"
    assert capsys.readouterr().err == ""


def test_generated_config_drops_lungnote_and_logs_one_line_when_absent(monkeypatch, capsys):
    monkeypatch.setattr(wmc, "_is_file", lambda p: False)
    generated = wmc.generate("/opt/MoonieXHQ/Agents/Core",
                             venv_python="/opt/MoonieXHQ/Agents/Core/.venv/bin/python",
                             lungnote_js="/nowhere/index.js", lungnote_node="node")

    assert "lungnote" not in generated["mcpServers"] and "org" in generated["mcpServers"]
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and "lungnote" in err[0].lower()


def test_generation_keeps_the_org_command_the_cutover_flip_rewrote(tmp_path, monkeypatch):
    """scripts/hub/cutover_flip.py points the org server at the env wrapper and
    adds ORG_DB_URL; a generator that rebuilt the org entry would undo it."""
    monkeypatch.setattr(wmc, "_is_file", lambda p: True)
    flipped = {"mcpServers": {"org": {
        "command": f"{wmc.TEMPLATE_ROOT}/scripts/hub/with-org-db-env.sh",
        "args": [wmc.TEMPLATE_PYTHON, f"{wmc.TEMPLATE_ROOT}/runners/worker_mcp_server.py"],
        "cwd": wmc.TEMPLATE_ROOT,
        "env": {"PYTHONUNBUFFERED": "1", "ORG_DB_URL": "postgres://hub/org"},
    }}}
    tpl = tmp_path / "worker.mcp.json"
    tpl.write_text(json.dumps(flipped))

    out = wmc.generate("/opt/MoonieXHQ/Agents/Core", template=tpl,
                       venv_python="/opt/MoonieXHQ/Agents/Core/.venv/bin/python")

    org = out["mcpServers"]["org"]
    assert org["command"] == "/opt/MoonieXHQ/Agents/Core/scripts/hub/with-org-db-env.sh"
    assert org["args"][0] == "/opt/MoonieXHQ/Agents/Core/.venv/bin/python"
    assert org["env"]["ORG_DB_URL"] == "postgres://hub/org"


def test_write_for_worktree_is_mode_600_and_git_excluded(tmp_path, monkeypatch):
    monkeypatch.setattr(wmc, "_is_file", lambda p: True)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit_files(repo, {"a.txt": "a\n"}, "init")

    out = wmc.write_for_worktree(repo, wmc.TEMPLATE_ROOT)

    assert out == repo / ".org-worker.mcp.json"
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert json.loads(out.read_text()) == wmc.generate(wmc.TEMPLATE_ROOT)
    assert ".org-worker.mcp.json" not in _git(repo, "status", "--porcelain")


def test_worker_launchers_read_the_generated_config_not_the_template():
    """Both readers must go through write_for_worktree — a second, direct read
    of config/worker.mcp.json would hand a Contabo worker the Mac's paths."""
    for rel in ("runners/worker_init.py", "runners/worker_resume.py"):
        src = (ROOT / rel).read_text()
        assert "write_for_worktree(" in src, rel
        assert 'ROOT / "config" / "worker.mcp.json"' not in src, rel
