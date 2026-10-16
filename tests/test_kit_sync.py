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
    assert len(calls) == (2 if stage == "status" else 4)
    assert capsys.readouterr().err.count("timed out") == 2


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
