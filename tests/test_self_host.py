"""Tests for lib.config.self_host() (task-1bfb0389, Org Mesh W0.1).

Covers the 5-step resolution order (env > node.yaml > ROOT-match > platform
> raise), each bad-input error path, worktree/symlink ROOT matching, and the
two write sites this task wires up: lib.db.create_task's dispatcher_host and
tools.delegate's local-spawn host write.

Run via:  pytest tests/test_self_host.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.config as config  # noqa: E402
import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_self_host_cache():
    """self_host() is cached per process (functools.lru_cache) -- every
    test below changes one of its sources, so a stale cached answer must
    never leak between tests in this file, or into
    tests/test_worker_naming.py's own current_host() tests running in the
    same pytest process."""
    config.self_host.cache_clear()
    yield
    config.self_host.cache_clear()


_HOSTS = {
    "mac": {"os": "darwin", "agents_root": "/fake/mac/agents"},
    "winbox": {"os": "windows", "agents_root": "/fake/winbox/agents"},
    "contabo": {"os": "linux", "agents_root": "/fake/contabo/agents"},
}


def _patch_hosts(monkeypatch, hosts: dict) -> None:
    monkeypatch.setattr(config, "hosts", lambda: hosts)


def _patch_home(monkeypatch, tmp_path: Path) -> Path:
    """Point NODE_CONFIG_PATH at a per-test file so a real
    ~/.config/mooniex/node.yaml on the box running these tests can never
    leak in."""
    node_path = tmp_path / "node.yaml"
    monkeypatch.setattr(config, "NODE_CONFIG_PATH", node_path)
    return node_path


def _patch_root(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(config, "ROOT", root)


# ---------------------------------------------------------------------------
# Resolution order: env > node.yaml > ROOT match > platform
# ---------------------------------------------------------------------------

def test_env_wins_over_everything(monkeypatch, tmp_path):
    _patch_hosts(monkeypatch, _HOSTS)
    _patch_home(monkeypatch, tmp_path)  # no node.yaml written -> absent
    _patch_root(monkeypatch, tmp_path / "nowhere")  # matches no agents_root
    monkeypatch.setenv("ORG_HOST", "Winbox")  # case-insensitive
    assert config.self_host() == "winbox"


def test_node_yaml_wins_over_root_and_platform(monkeypatch, tmp_path):
    _patch_hosts(monkeypatch, _HOSTS)
    monkeypatch.delenv("ORG_HOST", raising=False)
    node_path = _patch_home(monkeypatch, tmp_path)
    node_path.write_text(yaml.safe_dump({"host": "contabo"}))
    # W4.6a F12: for a name hosts.yaml declares, ROOT has to AGREE with node.yaml (a node.yaml
    # that disagrees raises: tests/test_w46a_hub_fixes.py). Here ROOT is contabo's; the test box
    # is darwin, so the platform source says mac and node.yaml must still beat it.
    _patch_root(monkeypatch, Path(_HOSTS["contabo"]["agents_root"]))
    assert config.self_host() == "contabo"


def test_root_match_wins_over_platform(monkeypatch, tmp_path):
    # Two darwin hosts make the platform source ambiguous (returns None) --
    # a pass here can only be explained by the ROOT match, not platform.
    hosts = {
        "mac": {"os": "darwin", "agents_root": str(tmp_path / "agents")},
        "othermac": {"os": "darwin", "agents_root": str(tmp_path / "other")},
    }
    _patch_hosts(monkeypatch, hosts)
    monkeypatch.delenv("ORG_HOST", raising=False)
    _patch_home(monkeypatch, tmp_path)
    root = tmp_path / "agents"
    root.mkdir()
    _patch_root(monkeypatch, root)
    assert config.self_host() == "mac"


def test_platform_wins_when_exactly_one_host_matches_os(monkeypatch, tmp_path):
    hosts = {
        "solo-linux": {"os": "linux", "agents_root": str(tmp_path / "nope")},
        "solo-windows": {"os": "windows", "agents_root": str(tmp_path / "nope2")},
    }
    _patch_hosts(monkeypatch, hosts)
    monkeypatch.delenv("ORG_HOST", raising=False)
    _patch_home(monkeypatch, tmp_path)
    _patch_root(monkeypatch, tmp_path / "nowhere")
    monkeypatch.setattr(config.platform, "system", lambda: "Linux")
    assert config.self_host() == "solo-linux"


# ---------------------------------------------------------------------------
# Error paths -- raise instead of guessing
# ---------------------------------------------------------------------------

def test_bad_org_host_raises(monkeypatch, tmp_path):
    _patch_hosts(monkeypatch, _HOSTS)
    _patch_home(monkeypatch, tmp_path)
    monkeypatch.setenv("ORG_HOST", "nonexistent-host")
    with pytest.raises(ValueError, match="nonexistent-host"):
        config.self_host()


def test_bad_node_yaml_host_raises(monkeypatch, tmp_path):
    _patch_hosts(monkeypatch, _HOSTS)
    monkeypatch.delenv("ORG_HOST", raising=False)
    node_path = _patch_home(monkeypatch, tmp_path)
    node_path.write_text(yaml.safe_dump({"host": "nonexistent-host"}))
    with pytest.raises(ValueError, match="nonexistent-host"):
        config.self_host()


def test_ambiguous_platform_with_no_other_source_raises(monkeypatch, tmp_path):
    hosts = {
        "linux-a": {"os": "linux", "agents_root": str(tmp_path / "a")},
        "linux-b": {"os": "linux", "agents_root": str(tmp_path / "b")},
    }
    _patch_hosts(monkeypatch, hosts)
    monkeypatch.delenv("ORG_HOST", raising=False)
    _patch_home(monkeypatch, tmp_path)
    _patch_root(monkeypatch, tmp_path / "nowhere")
    monkeypatch.setattr(config.platform, "system", lambda: "Linux")
    with pytest.raises(RuntimeError, match="cannot resolve self_host"):
        config.self_host()


# ---------------------------------------------------------------------------
# ROOT match: worktree + symlinked agents_root
# ---------------------------------------------------------------------------

def test_worktree_under_agents_root_resolves_to_that_host(monkeypatch, tmp_path):
    hosts = {"mac": {"os": "darwin", "agents_root": str(tmp_path / "agents")}}
    _patch_hosts(monkeypatch, hosts)
    monkeypatch.delenv("ORG_HOST", raising=False)
    _patch_home(monkeypatch, tmp_path)
    worktree = tmp_path / "agents" / "worktrees" / "mooniex-agents__developer__task-xyz"
    worktree.mkdir(parents=True)
    _patch_root(monkeypatch, worktree)
    assert config.self_host() == "mac"


def test_symlinked_agents_root_resolves(monkeypatch, tmp_path):
    """Mirrors Contabo's compat symlink (docs/design/org-mesh.md §1b):
    hosts.yaml's agents_root can itself be reached through a symlink --
    ROOT must still match once both sides are resolved to real paths."""
    real = tmp_path / "real-agents"
    real.mkdir()
    link = tmp_path / "compat-link"
    link.symlink_to(real)
    hosts = {"contabo": {"os": "linux", "agents_root": str(link)}}
    _patch_hosts(monkeypatch, hosts)
    monkeypatch.delenv("ORG_HOST", raising=False)
    _patch_home(monkeypatch, tmp_path)
    _patch_root(monkeypatch, real)
    assert config.self_host() == "contabo"


# ---------------------------------------------------------------------------
# self_host_sources() -- diagnostic, never raises
# ---------------------------------------------------------------------------

def test_self_host_sources_reports_bad_env_as_error_not_raise(monkeypatch, tmp_path):
    _patch_hosts(monkeypatch, _HOSTS)
    _patch_home(monkeypatch, tmp_path)
    monkeypatch.setenv("ORG_HOST", "nonexistent-host")
    sources = config.self_host_sources()
    assert "error" in sources["env"]
    assert "nonexistent-host" in sources["env"]


# ---------------------------------------------------------------------------
# Write sites: create_task's dispatcher_host, local spawn's host
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


def test_create_task_writes_dispatcher_host(temp_db):
    real_host = config.self_host()  # this process's real host (unpatched)
    tid = temp_db.create_task(project="test-project", role="developer",
                              title="t", description="d",
                              owner_cto="test-owner")
    task = temp_db.get_task(tid)
    assert task["dispatcher_host"] == real_host


def _fake_project() -> dict:
    return {
        "key": "test-project",
        "name": "test",
        "remote": "git@github.com:test/test.git",
        "path": "/tmp/does-not-matter",
        "default_branch": "main",
        "agents_allowed": ["developer"],
        "spawn_backend": "iterm",
        "web_ui": "off",
    }


def _fake_create_worktree(project_key, role, task_id, sparse=False):
    return {"project": project_key, "task_id": task_id, "role": role,
            "branch": f"agent/{role}-{task_id}",
            "worktree": f"/tmp/fake-worktree-{task_id}",
            "base": "main", "repo": "/tmp/does-not-matter", "provisioned": []}


def test_local_spawn_writes_host(temp_db, monkeypatch):
    real_host = config.self_host()  # this process's real host (unpatched)
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "get_project", lambda key: _fake_project())
    monkeypatch.setattr(delegate, "create_worktree", _fake_create_worktree)
    monkeypatch.setattr(delegate, "_spawn_iterm_tab",
                        lambda role, task_id, **kw: "spawned")

    tid = temp_db.create_task(project="test-project", role="developer",
                              title="t", description="d",
                              owner_cto="someone-else")  # out of every storage scope
    asyncio.run(delegate.delegate_task(tid))

    task = temp_db.get_task(tid)
    assert task["host"] == real_host
