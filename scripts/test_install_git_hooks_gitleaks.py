"""
Tests for the gitleaks stanza written by scripts/install-git-hooks.sh.

2026-10-12: Contabo had no gitleaks on PATH and the hook skipped the secret
guard without a word. A missing gitleaks must now be loud: the installer exits
2 (unless ALLOW_NO_GITLEAKS=1) and the hook warns on every commit.

Runs the installer against a throwaway repo under tmp_path, never the real repo.
"Missing" means PATH=/usr/bin:/bin; "present" adds a stub gitleaks that exits 0.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parent / "install-git-hooks.sh"
BARE_PATH = "/usr/bin:/bin"

pytestmark = pytest.mark.skipif(
    shutil.which("gitleaks", path=BARE_PATH) is not None,
    reason="gitleaks lives in /usr/bin or /bin here; cannot simulate a missing one",
)


def _env(extra_path=None, **extra):
    path = f"{extra_path}:{BARE_PATH}" if extra_path else BARE_PATH
    env = {k: v for k, v in os.environ.items() if k != "ALLOW_NO_GITLEAKS"}
    env.update(PATH=path, **extra)
    return env


def run_installer(repo, **env):
    return subprocess.run(["sh", str(INSTALLER)], cwd=repo, env=_env(**env),
                          capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "throwaway"
    repo.mkdir()
    for cmd in (["init"], ["config", "user.name", "test"],
                ["config", "user.email", "test@test.com"]):
        subprocess.run(["git", *cmd], cwd=repo, check=True, capture_output=True)
    return repo


@pytest.fixture
def stub_bin(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "gitleaks"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    return str(bin_dir)


def hook_text(repo):
    return (repo / ".git" / "hooks" / "pre-commit").read_text()


def test_installer_exits_2_and_warns_without_gitleaks(repo):
    result = run_installer(repo)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "gitleaks is NOT on PATH" in result.stderr
    assert "BEGIN gitleaks guard" in hook_text(repo)  # the hook is still written


def test_allow_no_gitleaks_exits_0_but_still_warns(repo):
    result = run_installer(repo, ALLOW_NO_GITLEAKS="1")
    assert result.returncode == 0, result.stderr
    assert "gitleaks is NOT on PATH" in result.stderr


def test_installer_quiet_when_gitleaks_present(repo, stub_bin):
    result = run_installer(repo, extra_path=stub_bin)
    assert result.returncode == 0, result.stderr
    assert "NOT on PATH" not in result.stderr


def test_commit_without_gitleaks_says_guard_skipped(repo):
    run_installer(repo, ALLOW_NO_GITLEAKS="1")
    (repo / "a.txt").write_text("a")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True, capture_output=True)
    result = subprocess.run(["git", "commit", "-m", "a"], cwd=repo, env=_env(),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "secret guard SKIPPED" in result.stderr


def test_reinstall_replaces_a_stale_gitleaks_stanza(repo):
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    (hooks / "pre-commit").write_text(
        "#!/bin/sh\n"
        "# --- BEGIN gitleaks guard (old) ---\n"
        "if command -v gitleaks >/dev/null 2>&1; then\n"
        "  gitleaks protect --staged --redact --no-banner || exit 1\n"
        "fi\n"
        "# --- END gitleaks guard ---\n"
    )
    run_installer(repo, ALLOW_NO_GITLEAKS="1")
    run_installer(repo, ALLOW_NO_GITLEAKS="1")
    text = hook_text(repo)
    assert text.count("BEGIN gitleaks guard") == 1
    assert "secret guard SKIPPED" in text


def test_unmarked_hand_written_guard_is_not_doubled(repo):
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    (hooks / "pre-commit").write_text(
        "#!/bin/sh\ngitleaks protect --staged --redact --no-banner || exit 1\n"
    )
    run_installer(repo, ALLOW_NO_GITLEAKS="1")
    assert hook_text(repo).count("gitleaks protect --staged") == 1
