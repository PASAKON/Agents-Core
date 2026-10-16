"""KIT probes use local fixture repositories only; no network or SSH."""
import copy
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import mesh_check as m


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


@pytest.fixture
def checkout(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
        "commit", "--allow-empty", "-qm", "fixture")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path


def green(checkout):
    repo = m.kit_git(checkout)
    return {**{name: copy.deepcopy(repo) for name in ("core", "rules", "wikis", "memory")},
            "skills_repo": 120, "skills_home": 120, "role": True,
            "launcher": True, "hooks": True}


def test_git_facts_and_no_fetch(checkout, monkeypatch):
    original = m._kit_run
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return original(argv, **kwargs)

    monkeypatch.setattr(m, "_kit_run", run)
    facts = m.kit_git(checkout)
    assert facts["head"] == git(checkout, "rev-parse", "HEAD")
    assert facts["origin_main"] == facts["head"]
    assert facts["behind"] == 0
    assert facts["merge_base_age_hours"] >= 0
    assert not any("fetch" in call for call in calls)
    assert m.check_kit(green(checkout))["ok"]


def test_behind_and_missing_ref(checkout):
    old = git(checkout, "rev-parse", "HEAD")
    git(checkout, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
        "commit", "--allow-empty", "-qm", "next")
    git(checkout, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(checkout, "reset", "--hard", old)
    assert m.kit_git(checkout)["behind"] == 1
    git(checkout, "update-ref", "-d", "refs/remotes/origin/main")
    assert m.kit_git(checkout)["status"] == "n/a"


def test_plain_directory_missing_and_symlink(checkout, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert m.kit_git(plain)["status"] == "not-git"
    assert m.kit_git(plain / "missing")["status"] == "n/a"
    link = tmp_path / "link"
    link.symlink_to(checkout, target_is_directory=True)
    assert m.kit_git(link)["head"] == m.kit_git(checkout)["head"]


@pytest.mark.parametrize("name", ["rules", "wikis", "memory"])
@pytest.mark.parametrize("failure", ["not-git", "n/a", "diverged"])
def test_repo_red(checkout, name, failure):
    facts = green(checkout)
    if failure == "diverged":
        facts[name]["head"] = "f" * 40
    else:
        facts[name]["status"] = failure
    cell = m.check_kit(facts)
    assert not cell["ok"] and name in cell["reason"]


@pytest.mark.parametrize("behind,age,ok", [(0, 1000, True), (1, 24, True),
                                          (1, 24.01, False), (1, "n/a", False)])
def test_core_age(checkout, behind, age, ok):
    facts = green(checkout)
    facts["core"].update(behind=behind, merge_base_age_hours=age)
    assert m.check_kit(facts)["ok"] is ok


@pytest.mark.parametrize("key,value", [("skills_repo", 119), ("skills_repo", "n/a"),
                                       ("role", False),
                                       ("launcher", False), ("hooks", False)])
def test_required_facts(checkout, key, value):
    facts = green(checkout)
    facts[key] = value
    assert not m.check_kit(facts)["ok"]


@pytest.mark.parametrize("count", [0, 11, 119, "n/a", None])
def test_home_skills_informational(checkout, count):
    facts = green(checkout)
    facts["skills_home"] = count
    assert m.check_kit(facts)["ok"]


@pytest.mark.parametrize("raw", [None, [], {}, {"rules": []}])
def test_missing_malformed_facts_fail_closed(raw):
    cell = m.check_kit(raw)
    assert not cell["ok"]
    assert len(cell["reason"]) <= 80


def test_mcp_parser_never_returns_values():
    assert m.kit_mcp_names(json.dumps({"mcpServers": {
        "org": {"env": {"TOKEN": "private-value"}}, "lungnote": {}}})) == ["lungnote", "org"]
    for raw in (None, "{", [], {"mcpServers": []}):
        assert m.kit_mcp_names(raw) == "n/a"


def test_paths_contract_and_fallback(tmp_path, monkeypatch):
    root, home = tmp_path / "core", tmp_path / "home"
    (root / "config").mkdir(parents=True)
    (root / "config/hosts.yaml").write_text("hosts:\n  contabo:\n    kit_paths:\n      rules: /fixture/rules\n")
    (root / "config/machine-contract.yaml").write_text("machines:\n  contabo:\n    hq: /fixture/hq\n")
    paths = m.kit_paths(root, home, "contabo")
    assert paths["rules"] == Path("/fixture/rules")
    assert paths["memory"] == Path("/fixture/hq/Agents/Memory")
    monkeypatch.setenv("WIKI_ROOT_ORG", str(tmp_path / "rules"))
    paths = m.kit_paths(root, home, None)
    assert paths["rules"] == tmp_path / "rules"
    assert paths["memory"].parent.parent == home / ".claude/projects"


def test_collector_missing_repo_modules(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "_kit_run", lambda *a, **k: None)
    facts = m.kit_facts(tmp_path, home=tmp_path / "home")
    assert facts["mcp_names"] == "n/a"
    assert facts["core"]["status"] == "not-git"
    assert facts["skills_repo"] == 0
    assert not facts["hooks"]


def test_collector_skills_and_launcher_config(checkout, monkeypatch):
    home = checkout / "home"
    for base in (checkout, home):
        for i in range(120):
            skill = base / ".claude/skills" / str(i)
            skill.mkdir(parents=True)
            (skill / "SKILL.md").touch()
    generator = checkout / "scripts/lib/cxo_mcp_config.py"
    generator.parent.mkdir(parents=True)
    generator.write_text("def _names_for(role): return ['org']\n"
                         "def _build(*args): return {'env': {'TOKEN': 'private-value'}}\n")
    facts = m.kit_facts(checkout, home=home)
    assert facts["skills_repo"] == facts["skills_home"] == 120
    assert facts["mcp_names"] == ["org"]
    assert "private-value" not in json.dumps(facts)
    assert not (generator.parent / "__pycache__").exists()


def test_piped_source_without_dependencies(tmp_path):
    result = subprocess.run([sys.executable, "-S", "-", "--local", "--json"],
                            cwd=tmp_path, input=Path(m.__file__).read_text(),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    facts = json.loads(result.stdout)["kit"]
    assert facts["core"]["status"] == "not-git"
    assert facts["mcp_names"] == "n/a"


def test_linked_worktree_uses_primary_launcher(checkout):
    generator = checkout / "scripts/lib/cxo_mcp_config.py"
    generator.parent.mkdir(parents=True)
    generator.write_text(
        "from pathlib import Path\n"
        "def _names_for(role):\n"
        "    assert role == 'project_head'\n"
        "    return ['org', 'absent']\n"
        "def _build(name, root, role=''):\n"
        "    assert role == 'project_head'\n"
        "    if name == 'org' and (Path(root) / '.git').is_dir():\n"
        "        return {'env': {'TOKEN': 'private-value'}}\n"
        "def hub_route(root): return 'infisical'\n")
    worktree = checkout / 'task'
    git(checkout, 'worktree', 'add', '--detach', str(worktree))
    facts = m.kit_facts(worktree, home=checkout / 'home')
    assert facts['mcp_names'] == ['org']
    assert 'private-value' not in json.dumps(facts)
    assert not (generator.parent / '__pycache__').exists()


def test_fetch_is_explicit(checkout, monkeypatch):
    calls = []
    original = m._kit_run

    def run(argv, **kwargs):
        calls.append(argv)
        if "fetch" in argv:
            return subprocess.CompletedProcess(argv, 1, "", "private-error")
        return original(argv, **kwargs)

    monkeypatch.setattr(m, "_kit_run", run)
    facts = m.kit_git(checkout, fetch=True)
    assert any("fetch" in call for call in calls)
    assert facts["fetch"] == "n/a"
    assert "private-error" not in json.dumps(facts)


def test_install_check_does_not_create_home(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    home = tmp_path / "absent"
    result = subprocess.run(["bash", str(m.ROOT / "scripts/install-claude-home.sh"), "--check"],
                            capture_output=True, env={**os.environ, "CLAUDE_HOME": str(home),
                                                     "CLAUDE_HOME_SRC": str(src)})
    assert result.returncode == 1
    assert not home.exists()


def test_wave_and_render(checkout, monkeypatch):
    monkeypatch.setattr(m, "HOSTS", ["contabo", "winbox", "mac"])
    cells = {"KIT": {h: {h: m.check_kit(green(checkout))} for h in m.HOSTS}}
    assert m.render(cells, "w4")[2:] == (0, 0)
    assert m.render(cells, "w5")[2:] == (3, 0)
    cells["KIT"]["winbox"]["winbox"] = m.check_kit(None)
    text, failed, good, bad = m.render(cells, "w5")
    assert failed and (good, bad) == (2, 1)
    assert "## KIT facts" in text
    assert ("KIT", "contabo", "winbox") not in m.EXPECT


def test_default_does_not_write_ledger_or_snapshots(monkeypatch):
    monkeypatch.setattr(m, "HAVE_CONFIG", True)
    monkeypatch.setattr(m, "HOSTS", ["contabo"])
    monkeypatch.setattr(m, "_running_host_guess", lambda root: "contabo")
    monkeypatch.setattr(m, "kit_facts", lambda **kwargs: {})
    monkeypatch.setattr(m, "check_l0", lambda root: (True, None))

    async def l2(root):
        return True, None

    def forbidden(*args, **kwargs):
        pytest.fail("default mode attempted a write")

    monkeypatch.setattr(m, "check_l2", l2)
    monkeypatch.setattr(m, "check_l8", lambda *args: m._green())
    monkeypatch.setattr(m, "check_invariant", lambda: m._green())
    monkeypatch.setattr(m, "l4_probe", forbidden)
    monkeypatch.setattr(m, "write_state", forbidden)
    assert asyncio.run(m.amain(["--expect", "w5"])) == 1


def test_old_peer_falls_back_to_piped_source(monkeypatch):
    calls = []

    def ssh(alias, command, **kwargs):
        calls.append(kwargs)
        return json.dumps({"kit": {}} if "stdin_path" in kwargs else {"l0": {}})

    monkeypatch.setattr(m, "_ssh_run", ssh)
    assert m._collect_peer_local("winbox", {"os": "windows", "agents_root": "C:/fixture"},
                                 Path("fixture.py")) == {"kit": {}}
    assert len(calls) == 2 and "stdin_path" in calls[-1]
