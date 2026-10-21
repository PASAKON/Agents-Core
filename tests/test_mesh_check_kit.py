"""KIT probes use local fixture repositories only; no network or SSH."""
import copy
import asyncio
import base64
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
            "launcher": True, "hooks": True,
            **{key: True for key in m.KIT_SESSION_FACTS}}


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
    assert "memory pull/file" in text and "memory hook/file" not in text
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


@pytest.mark.parametrize("override", [False, True])
def test_core_path_controls_all_checkout_facts(tmp_path, monkeypatch, override):
    root, core, home = (tmp_path / name for name in ("root", "core", "home"))
    root.mkdir()
    for name in ("roles/project_head.md", "scripts/spawn-ph.sh", "windows/cxo-claude.ps1",
                 ".claude/skills/example/SKILL.md"):
        path = core / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    generator = core / "scripts/lib/cxo_mcp_config.py"
    generator.parent.mkdir(parents=True)
    generator.write_text("def _names_for(role): return ['org']\n"
                         "def _build(*args): return {}\n"
                         "def hub_route(root): return 'infisical'\n")
    monkeypatch.setattr(m, "kit_git", lambda path, **kwargs: {"path": str(path)})
    monkeypatch.setattr(m, "_kit_run", lambda *a, **k: None)
    paths = {"core": str(core), "rules": "/fixture/rules", "wikis": "/fixture/wikis"} if override else None
    facts = m.kit_facts(root, home=home, path_overrides=paths)
    selected = core if override else root
    assert facts["core"]["path"] == str(selected)
    assert facts["skills_repo"] == int(override)
    assert facts["role"] is override
    assert facts["launcher"] is override
    assert facts["mcp_names"] == (["org"] if override else "n/a")
    slug = m.re.sub(r"[^A-Za-z0-9]", "-", str(selected))
    assert facts["memory"]["path"] == str(home / ".claude/projects" / slug / "memory")
    if override:
        assert facts["rules"]["path"] == paths["rules"]
        assert facts["wikis"]["path"] == paths["wikis"]


@pytest.mark.parametrize("platform", ["windows", "linux"])
def test_peer_transports_paths_to_deployed_and_piped_collectors(monkeypatch, platform):
    paths = {key: f"C:/kit with spaces/$literal/{key}" for key in ("core", "rules", "wikis", "memory")}
    calls = []

    def ssh(alias, command, **kwargs):
        calls.append(command)
        encoded = command.split("--kit-paths-b64 ")[1]
        assert m._parse_args(["--local", "--kit-paths-b64", encoded]).kit_paths_b64 == paths
        return None if "stdin_path" not in kwargs else '{"kit": {}}'

    monkeypatch.setattr(m, "_ssh_run", ssh)
    assert m._collect_peer_local("peer", {"os": platform, "agents_root": "/wrong",
                                         "kit_paths": paths}, Path("fixture.py")) == {"kit": {}}
    assert len(calls) == 2


def test_piped_source_receives_paths_without_config(checkout, tmp_path):
    cwd = tmp_path / "wrong"
    cwd.mkdir()
    paths = {key: str(checkout) for key in ("core", "rules", "wikis", "memory")}
    encoded = base64.b64encode(json.dumps(paths).encode()).decode()
    result = subprocess.run([sys.executable, "-S", "-", "--local", "--json",
                             "--kit-paths-b64", encoded], cwd=cwd,
                            input=Path(m.__file__).read_text(), capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    facts = json.loads(result.stdout)["kit"]
    for key in paths:
        assert facts[key]["head"] == git(checkout, "rev-parse", "HEAD")


def test_configured_core_and_caller_precedence(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/hosts.yaml").write_text(
        "hosts:\n  winbox:\n    kit_paths:\n      core: C:/configured/core\n")
    home = tmp_path / "home"
    configured = m.kit_paths(tmp_path, home, "winbox")
    assert configured["core"] == Path("C:/configured/core")
    assert configured["memory"] == home / ".claude/projects/C--configured-core/memory"
    passed = m.kit_paths(tmp_path, home, "winbox", {"core": "C:/caller/core"})
    assert passed["core"] == Path("C:/caller/core")
    assert passed["memory"] == home / ".claude/projects/C--caller-core/memory"


@pytest.fixture
def session_kit(tmp_path):
    core, rules = tmp_path / "core space", tmp_path / "rules"
    for path in (core / ".claude/skills/session-open/SKILL.md",
                 core / ".claude/skills/session-close/SKILL.md",
                 core / "scripts/session-deadline-check.py", core / "tools/memory_sync.py",
                 core / "windows/cxo-claude.ps1", core / "scripts/cxo-claude.sh", rules / "IRON-RULES.md"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("raise RuntimeError('must never execute')")
    settings = {"hooks": {"SessionStart": [{"hooks": [
        {"type": "command", "command": 'python3 "${CLAUDE_PROJECT_DIR:-$PWD}"/scripts/session-deadline-check.py'}]}]}}
    (core / "scripts/cxo-claude.sh").write_text('python3 -m tools.memory_sync pull\n')
    (core / "windows/cxo-claude.ps1").write_text('& $venvPy -m tools.memory_sync pull\n')
    (core / ".claude/settings.json").write_text(json.dumps(settings))
    return core, rules


def test_session_present(session_kit):
    assert all(m.kit_session_facts(*session_kit).values())
    assert all(m.kit_session_facts(*session_kit, windows=True).values())


@pytest.mark.parametrize("windows", [False, True])
@pytest.mark.parametrize("source,expected", [
    (None, False), ("", False),
    ("  # python3 -m tools.memory_sync pull", False),
    ("python3 -m tools.memory_sync push", False),
    ("python3 -m tools.memory_sync pull_other", False),
    ("python3 -m tools.memory_sync pull", True),
    ("& $venvPy -m tools.memory_sync pull", True)])
def test_memory_pull_launcher(session_kit, checkout, windows, source, expected):
    core, rules = session_kit
    launcher = core / ("windows/cxo-claude.ps1" if windows else "scripts/cxo-claude.sh")
    if source is None:
        launcher.unlink()
    else:
        launcher.write_text(source)
    facts = m.kit_session_facts(core, rules, windows=windows)
    assert facts["memory_pull"] is expected
    assert facts["memory_script"]
    assert "memory_hook" not in facts
    if not expected:
        assert "memory_pull" in m.check_kit({**green(checkout), **facts})["reason"]


def test_memory_hook_does_not_replace_launcher(session_kit):
    core, rules = session_kit
    (core / "scripts/cxo-claude.sh").write_text("")
    (core / ".claude/settings.json").write_text(json.dumps({"hooks": {"SessionStart": [
        {"hooks": [{"type": "command", "command": "python3 -m tools.memory_sync pull"}]}]}}))
    assert not m.kit_session_facts(core, rules)["memory_pull"]


@pytest.mark.parametrize("key,path", [
    ("session_open", ".claude/skills/session-open/SKILL.md"),
    ("session_close", ".claude/skills/session-close/SKILL.md"),
    ("deadline_script", "scripts/session-deadline-check.py"),
    ("memory_script", "tools/memory_sync.py"), ("iron_rules", "IRON-RULES.md")])
def test_session_missing_file(session_kit, checkout, key, path):
    core, rules = session_kit
    ((rules if key == "iron_rules" else core) / path).unlink()
    facts = m.kit_session_facts(core, rules)
    assert facts[key] is False
    cell = m.check_kit({**green(checkout), **facts})
    assert not cell["ok"] and key in cell["reason"] and len(cell["reason"]) <= 80


@pytest.mark.parametrize("index,label", [(0, "deadline")])
def test_missing_session_hook(session_kit, checkout, index, label):
    core, rules = session_kit
    path = core / ".claude/settings.json"
    data = json.loads(path.read_text())
    removed = data["hooks"]["SessionStart"][0]["hooks"].pop(index)
    data["hooks"]["Stop"] = [{"hooks": [removed]}]
    path.write_text(json.dumps(data))
    facts = m.kit_session_facts(core, rules)
    assert not facts[label + "_hook"] and not facts[label + "_script"]
    assert not m.check_kit({**green(checkout), **facts})["ok"]


@pytest.mark.parametrize("content", ["{", "[]", '{"hooks": null}', '{"hooks":{"SessionStart":[null]}}'])
def test_malformed_settings(session_kit, content):
    core, rules = session_kit
    (core / ".claude/settings.json").write_text(content)
    facts = m.kit_session_facts(core, rules)
    assert not facts["deadline_hook"] and facts["memory_pull"] and facts["memory_script"]


@pytest.mark.parametrize("argument", ['".claude/alternate.json"', '$settings'])
def test_windows_launcher_settings_override(session_kit, argument):
    core, rules = session_kit
    (core / ".claude/alternate.json").write_text('{}')
    (core / "windows/cxo-claude.ps1").write_text(
        '$settings = "$PSScriptRoot/../.claude/alternate.json"\n'
        f'& claude --settings {argument}\n')
    facts = m.kit_session_facts(core, rules, windows=True)
    assert not facts["deadline_hook"] and not facts["memory_pull"] and facts["memory_script"]


def test_unknown_windows_override_fails_closed(session_kit):
    core, rules = session_kit
    (core / "windows/cxo-claude.ps1").write_text('& claude --settings $dynamic')
    assert not m.kit_session_facts(core, rules, windows=True)["deadline_hook"]


def test_windows_override_present_and_missing_settings(session_kit):
    core, rules = session_kit
    settings = core / ".claude/settings.json"
    alternate = core / ".claude/alternate.json"
    settings.rename(alternate)
    (core / "windows/cxo-claude.ps1").write_text(
        '& claude --settings ".claude/alternate.json"\n& $venvPy -m tools.memory_sync pull\n')
    assert all(m.kit_session_facts(core, rules, windows=True).values())
    alternate.unlink()
    facts = m.kit_session_facts(core, rules, windows=True)
    assert not facts["deadline_hook"] and facts["memory_pull"] and facts["memory_script"]


@pytest.mark.parametrize("key", m.KIT_SESSION_FACTS)
def test_missing_session_fact_is_red(checkout, key):
    facts = green(checkout)
    del facts[key]
    cell = m.check_kit(facts)
    assert not cell["ok"] and key in cell["reason"]


def test_script_must_be_referenced_under_core(session_kit, tmp_path):
    core, rules = session_kit
    outside = tmp_path / "session-deadline-check.py"
    outside.touch()
    (core / ".claude/settings.json").write_text(json.dumps({"hooks": {"SessionStart": [
        {"hooks": [{"type": "command", "command": f'python "{outside}"'}]}]}}))
    facts = m.kit_session_facts(core, rules)
    assert facts["deadline_hook"] and not facts["deadline_script"]


def test_session_checks_use_overridden_core(session_kit, tmp_path, monkeypatch):
    core, rules = session_kit
    monkeypatch.setattr(m, "_kit_run", lambda *a, **kw: None)
    facts = m.kit_facts(tmp_path, home=tmp_path, path_overrides={"core": str(core), "rules": str(rules)})
    assert all(facts[key] for key in m.KIT_SESSION_FACTS)


# ---------------------------------------------------------------------------
# OrgMesh P7: a peer with a mesh_ssh and no admin `ssh` alias (the Mac) reports
# its KIT through the read-only `kit` node_dispatch verb. No ssh, no real host.
# ---------------------------------------------------------------------------

_PEER_CFGS = {
    "contabo": {"os": "linux", "ssh": "vps", "mesh_ssh": "root@contabo.example.test", "agents_root": "/c"},
    "winbox": {"os": "windows", "ssh": "wb", "mesh_ssh": "user@winbox.example.test", "agents_root": "C:/w"},
    "mac": {"os": "darwin", "ssh": None, "mesh_ssh": "user@mac.example.test", "agents_root": "/m"},
}


class _Peers:
    """build_matrix run as contabo over three hosts. `collected` is every alias
    `_collect_peer_local` was asked for, `dispatched` every (host, verb, args)
    that reached lib.mesh.dispatch; `reply` / `raises` is what that call gives."""

    def __init__(self, monkeypatch, checkout, cfgs):
        from lib import mesh
        self.mesh, self.facts = mesh, green(checkout)
        self.collected, self.dispatched = [], []
        self.reply = {"ok": True, "verb": "kit", "result": copy.deepcopy(self.facts)}
        self.raises = None

        async def l2(root):
            return True, None

        def local(alias, cfg, script_path):
            self.collected.append(alias)
            return {"kit": copy.deepcopy(self.facts)}

        def dispatch(host, verb, *args, **kwargs):
            self.dispatched.append((host, verb, args))
            if self.raises is not None:
                raise self.raises
            return self.reply

        monkeypatch.setattr(m, "HAVE_CONFIG", True)
        monkeypatch.setattr(m, "HOSTS", list(cfgs))
        monkeypatch.setattr(m.config, "host", lambda name: cfgs[name])
        monkeypatch.setattr(m, "_running_host_guess", lambda root: "contabo")
        monkeypatch.setattr(m, "check_l0", lambda root: (True, None))
        monkeypatch.setattr(m, "check_l1", lambda target: (True, None))
        monkeypatch.setattr(m, "check_l2", l2)
        monkeypatch.setattr(m, "check_l8", lambda *a: m._green())
        monkeypatch.setattr(m, "check_invariant", lambda: m._green())
        monkeypatch.setattr(m, "kit_facts", lambda **kwargs: copy.deepcopy(self.facts))
        monkeypatch.setattr(m, "_collect_peer_local", local)
        monkeypatch.setattr(mesh, "dispatch", dispatch)

    def run(self, expect="w5"):
        import types
        args = types.SimpleNamespace(expect=expect, live=False, no_merge=False)
        combined, _ = asyncio.run(m.build_matrix(args))
        return combined, m.render(combined, expect)


@pytest.fixture
def peers(monkeypatch, checkout):
    return _Peers(monkeypatch, checkout, copy.deepcopy(_PEER_CFGS))


def _kit_row(md, host):
    section = md.split("## KIT facts")[1]
    return [ln for ln in section.splitlines() if ln.startswith(f"| {host} |")][0]


def test_mac_kit_is_filled_from_the_kit_verb(peers):
    combined, (md, any_fail, n_ok, n_fail) = peers.run()
    assert peers.dispatched == [("mac", "kit", ())]  # the bare verb, no argument
    cell = combined["KIT"]["mac"]["mac"]
    assert cell["ok"] is True and cell["facts"] == peers.facts
    assert "| ok |" in _kit_row(md, "mac")
    assert any_fail is False and n_fail == 0 and n_ok >= 3  # contabo, winbox, mac KIT cells
    # every other level for the Mac stays as today: nothing collected, nothing dialled
    assert combined["L0"]["mac"] == {} and combined["L2"]["mac"] == {}
    assert combined["L1"]["mac"] == {}


def test_winbox_and_contabo_keep_todays_path(peers):
    combined, _ = peers.run()
    assert peers.collected == ["wb"]  # contabo is this host; winbox goes the alias route
    assert [d[0] for d in peers.dispatched] == ["mac"]  # the verb is never sent to them
    assert combined["KIT"]["winbox"]["winbox"]["ok"] is True
    assert combined["KIT"]["contabo"]["contabo"]["ok"] is True


def test_a_host_with_an_ssh_alias_never_uses_the_verb(monkeypatch, checkout):
    cfgs = copy.deepcopy(_PEER_CFGS)
    cfgs["mac"]["ssh"] = "mac-admin"  # same host, now with an admin alias
    p = _Peers(monkeypatch, checkout, cfgs)
    combined, _ = p.run()
    assert p.dispatched == []
    assert p.collected == ["wb", "mac-admin"]
    assert combined["KIT"]["mac"]["mac"]["ok"] is True


def test_a_peer_with_neither_alias_nor_mesh_ssh_is_not_dialled(monkeypatch, checkout):
    cfgs = copy.deepcopy(_PEER_CFGS)
    cfgs["mac"]["mesh_ssh"] = None
    p = _Peers(monkeypatch, checkout, cfgs)
    combined, _ = p.run()
    assert p.dispatched == []
    assert combined["KIT"]["mac"]["mac"] == m.check_kit(None)


def test_mac_kit_unreachable_is_a_fail_with_the_reason(peers):
    peers.raises = peers.mesh.MeshUnreachable("kit on mac: ssh failed: refused|\nno route")
    combined, (md, any_fail, n_ok, n_fail) = peers.run()
    cell = combined["KIT"]["mac"]["mac"]
    assert cell["ok"] is False and "kind" not in cell
    assert "ssh failed: refused" in cell["reason"] and "no route" in cell["reason"]
    assert "|" not in cell["reason"] and "\n" not in cell["reason"]  # one table cell
    row = _kit_row(md, "mac")
    assert "ssh failed: refused" in row and row.count("|") == _kit_row(md, "contabo").count("|")
    assert "FAIL(kit on mac: ssh failed: refused" in md  # the KIT matrix cell
    assert any_fail is True and n_fail == 1
    assert combined["L0"]["mac"] == {} and combined["L2"]["mac"] == {}  # nothing else filled in


@pytest.mark.parametrize("error", [ValueError("bad host"), RuntimeError("self_host: no source agrees")])
def test_mac_kit_dispatch_errors_are_a_fail_not_a_crash(peers, error):
    peers.raises = error
    combined, (md, any_fail, _, n_fail) = peers.run()
    cell = combined["KIT"]["mac"]["mac"]
    assert cell["ok"] is False and str(error) in cell["reason"]
    assert any_fail is True and n_fail == 1


def test_mac_kit_refused_reply_is_a_fail_with_the_reason(peers):
    peers.reply = {"ok": False, "verb": "kit", "error": "unknown verb 'kit'. Known: probe"}
    combined, (md, any_fail, _, n_fail) = peers.run()
    cell = combined["KIT"]["mac"]["mac"]
    assert cell["ok"] is False and "unknown verb 'kit'" in cell["reason"]
    assert "FAIL(" in md and any_fail is True and n_fail == 1


@pytest.mark.parametrize("result", [None, "n/a", ["core"], 7])
def test_mac_kit_reply_without_facts_is_a_fail(peers, result):
    peers.reply = {"ok": True, "verb": "kit", "result": result}
    cell = peers.run()[0]["KIT"]["mac"]["mac"]
    assert cell["ok"] is False and "no facts" in cell["reason"]


def test_mac_kit_facts_are_judged_like_any_other_hosts(peers):
    peers.reply["result"]["role"] = False
    cell = peers.run()[0]["KIT"]["mac"]["mac"]
    assert cell["ok"] is False and cell["reason"] == "role"
