"""Wiki pulls preserve local work and fail open using temporary repositories."""
import subprocess
from pathlib import Path

import pytest

from tools import kit_sync


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
        text=True, timeout=10,
    ).stdout.strip()


def commit(repo, name):
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-m", name)


@pytest.fixture
def repos(tmp_path, monkeypatch):
    remote = tmp_path / "remote"
    remote.mkdir()
    git(remote, "init", "--bare")
    source = tmp_path / "source"
    git(tmp_path, "clone", str(remote), str(source))
    commit(source, "initial")
    git(source, "push", "origin", "HEAD")
    local = tmp_path / "local"
    git(tmp_path, "clone", str(remote), str(local))
    for name in kit_sync.ROOTS:
        monkeypatch.setenv(name, str(local))
    return remote, source, local


@pytest.fixture(autouse=True)
def isolate_core(tmp_path, monkeypatch):
    for name in kit_sync.ROOTS:
        monkeypatch.delenv(name, raising=False)
    remote = tmp_path / 'core-remote'
    remote.mkdir()
    git(remote, 'init', '--bare', '--initial-branch=main')
    core = tmp_path / 'core'
    git(tmp_path, 'clone', str(remote), str(core))
    commit(core, 'initial')
    git(core, 'push', '-u', 'origin', 'main')
    monkeypatch.setenv('KIT_ROOT_CORE', str(core))
    return core


def test_fast_forward(repos, capsys):
    _, source, local = repos
    commit(source, "remote-change")
    git(source, "push")
    assert kit_sync.pull() == 0
    assert git(local, "rev-parse", "HEAD") == git(source, "rev-parse", "HEAD")
    assert capsys.readouterr().err == ""


def test_diverged_preserves_head(repos, capsys):
    _, source, local = repos
    commit(local, "local-change")
    before = git(local, "rev-parse", "HEAD")
    commit(source, "remote-change")
    git(source, "push")
    assert kit_sync.pull() == 0
    assert git(local, "rev-parse", "HEAD") == before
    assert git(local, "status", "--porcelain") == ""
    assert len(capsys.readouterr().err.splitlines()) == 2


@pytest.mark.parametrize("kind", ["untracked", "modified", "staged"])
def test_dirty_preserved(repos, capsys, kind):
    _, source, local = repos
    commit(source, "remote-change")
    git(source, "push")
    path = local / ("new" if kind == "untracked" else "initial")
    path.write_text("local edits")
    if kind == "staged":
        git(local, "add", path.name)
    before = git(local, "status", "--porcelain")
    assert kit_sync.pull() == 0
    assert path.read_text() == "local edits"
    assert git(local, "status", "--porcelain") == before
    assert not (local / "remote-change").exists()
    assert capsys.readouterr().err.count("dirty checkout") == 2


def test_not_git(tmp_path, monkeypatch, capsys):
    for name in kit_sync.ROOTS:
        monkeypatch.setenv(name, str(tmp_path))
    assert kit_sync.pull() == 0
    assert capsys.readouterr().err.count("not a git checkout") == 2


@pytest.mark.parametrize("stage", ["status", "pull"])
def test_timeout(repos, monkeypatch, capsys, stage):
    calls = []

    def timeout(cmd, **kwargs):
        calls.append(cmd)
        assert 0 < kwargs["timeout"] <= 15
        if stage == "pull" and "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(kit_sync.subprocess, "run", timeout)
    assert kit_sync.pull() == 0
    assert len(calls) == (3 if stage == "status" else 6)
    assert capsys.readouterr().err.count("timed out") == 3


def test_offline(repos, capsys):
    _, _, local = repos
    git(local, "remote", "set-url", "origin", str(local / "missing"))
    before = git(local, "rev-parse", "HEAD")
    assert kit_sync.pull() == 0
    assert git(local, "rev-parse", "HEAD") == before
    assert len(capsys.readouterr().err.splitlines()) == 2


def test_launchers_wire_pull_and_roots():
    root = Path(__file__).resolve().parents[1]
    for script in ("cxo-claude.sh", "cto-claude.sh"):
        text = (root / "scripts" / script).read_text()
        assert "python3 -m tools.kit_sync pull) || true" in text
        assert '"$HOME/MoonieXHQ/Agents/Rules"' in text
        assert '"$HOME/MoonieXHQ/Agents/Wikis"' in text
    text = (root / "windows/cxo-claude.ps1").read_text()
    for repo in ("Rules", "Wikis"):
        assert f"Join-Path $env:USERPROFILE 'mooniex\\repo\\Agents-{repo}'" in text
    assert text.index("$env:WIKI_ROOT_ORG = $rulesRoot") < text.index("-m tools.kit_sync pull")
    assert text.index("$env:WIKI_ROOT_MOONIEX = $wikisRoot") < text.index("-m tools.kit_sync pull")
    assert text.index("-m tools.kit_sync pull") < text.index("& $claude @fullArgs")


@pytest.mark.parametrize('dirty', ['clean', 'untracked', 'modified', 'staged', 'live'])
def test_core_pull(isolate_core, tmp_path, monkeypatch, capsys, dirty):
    core = isolate_core
    source = tmp_path / 'publisher'
    git(tmp_path, 'clone', git(core, 'remote', 'get-url', 'origin'), str(source))
    commit(source, 'update')
    git(source, 'push')
    if dirty in ('modified', 'staged'):
        (core / 'initial').write_text('edits')
        if dirty == 'staged':
            git(core, 'add', 'initial')
    elif dirty == 'untracked':
        (core / 'scratch').touch()
    elif dirty == 'live':
        link = tmp_path / 'live-link'
        link.symlink_to(core, target_is_directory=True)
        monkeypatch.setattr(kit_sync, 'CONTABO_LIVE', link)
    assert kit_sync.pull() == 0
    assert (core / 'update').exists() is (dirty in ('clean', 'untracked'))
    err = capsys.readouterr().err
    if dirty in ('modified', 'staged'):
        assert 'KIT_ROOT_CORE: dirty checkout' in err
    if dirty == 'live':
        assert 'Contabo live checkout: the merge card syncs it' in err


@pytest.mark.parametrize('mode', ['ok', 'stale', 'ahead', 'live', 'offline', 'missing'])
def test_check(isolate_core, tmp_path, monkeypatch, capsys, mode):
    core = isolate_core
    sha = git(core, 'rev-parse', 'HEAD')[:8]
    if mode == 'stale':
        source = tmp_path / 'publisher'
        git(tmp_path, 'clone', git(core, 'remote', 'get-url', 'origin'), str(source))
        for i in reversed(range(10)):
            name = f'.claude/skills/skill{i}/SKILL.md'
            (source / name).parent.mkdir(parents=True)
            commit(source, name)
        git(source, 'push')
    if mode in ('ahead', 'live'):
        commit(core, 'local')
        sha = git(core, 'rev-parse', 'HEAD')[:8]
    if mode == 'live':
        monkeypatch.setattr(kit_sync, 'CONTABO_LIVE', core)
    if mode == 'offline':
        git(core, 'remote', 'set-url', 'origin', str(tmp_path / 'absent'))
    if mode == 'missing':
        monkeypatch.setenv('KIT_ROOT_CORE', str(tmp_path))
    assert kit_sync.check() == 0
    line = capsys.readouterr().out
    assert len(line.splitlines()) == 1
    expected = f'kit ok ({sha} contains origin/main)'
    if mode == 'stale':
        expected = ('KIT STALE: 10 behind origin/main; skills that differ: '
                    + ', '.join(f'skill{i}' for i in range(8))
                    + ', +2 more — run git pull --ff-only before work that needs them')
    elif mode == 'ahead':
        expected += ' · KIT UNPUBLISHED: 1 local commits not on GitHub — open a PR to CTO Main'
    elif mode == 'live':
        expected += ' · 1 local commits wait for the hub sync'
    elif mode == 'offline':
        expected += ' (offline)'
    elif mode == 'missing':
        expected = 'kit check skipped: not a git checkout'
    assert line == expected + '\n'


@pytest.mark.parametrize('failure', ['missing-git', 'fetch-timeout'])
def test_check_failure_budget(isolate_core, monkeypatch, capsys, failure):
    original = subprocess.run
    elapsed = [0.0]
    monkeypatch.setattr(kit_sync.time, 'monotonic', lambda: elapsed[0])

    def run(argv, **kwargs):
        assert 0 < kwargs['timeout'] <= 9.5 - elapsed[0]
        if failure == 'missing-git':
            raise FileNotFoundError('git')
        if 'fetch' in argv:
            assert kwargs['timeout'] == 6
            elapsed[0] += 6
            raise subprocess.TimeoutExpired(argv, 6)
        return original(argv, **kwargs)

    monkeypatch.setattr(kit_sync.subprocess, 'run', run)
    assert kit_sync.check() == 0
    line = capsys.readouterr().out
    if failure == 'missing-git':
        assert line == 'kit check skipped: git missing\n'
    else:
        assert line.startswith('kit ok (') and line.endswith(' (offline)\n')
