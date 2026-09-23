"""
Tests for the media-guard (pilot) stanza written by scripts/install-git-hooks.sh.

Runs the installer against a throwaway repo under tmp_path -- never the real
repo, per task rules. The throwaway repo gets its own config/storage-policy.yaml
(a tmp policy) and a copy of the real scripts/media_guard.py, plus a
.venv/bin/python symlinked to sys.executable (the interpreter running pytest,
which already has PyYAML -- media_guard.py and its own test already depend on
it) so the hook's pilot check has a real python+yaml to read with.
"""
import os
import subprocess
import sys
from pathlib import Path

import yaml
import pytest

INSTALLER = Path(__file__).resolve().parent / "install-git-hooks.sh"
REAL_MEDIA_GUARD = Path(__file__).resolve().parent / "media_guard.py"

PILOT_CTO_ID = "0e8d80b8"


def run_installer(repo):
    return subprocess.run(
        ["sh", str(INSTALLER)],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def commit(repo, paths, worker_cto_id=None, message="add file"):
    env = os.environ.copy()
    if worker_cto_id is None:
        env.pop("WORKER_CTO_ID", None)
    else:
        env["WORKER_CTO_ID"] = worker_cto_id

    subprocess.run(["git", "add", *paths], cwd=repo, check=True, capture_output=True)
    return subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def throwaway_repo(tmp_path):
    repo = tmp_path / "throwaway"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    (repo / "README.md").write_text("init")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    # config/storage-policy.yaml -- the "tmp policy": pilot_owner_cto for the
    # WORKER_CTO_ID gate, media_guard for scripts/media_guard.py itself
    # (same file, same shape as the real config/storage-policy.yaml).
    (repo / "config").mkdir()
    policy = {
        "pilot_owner_cto": [PILOT_CTO_ID],
        "media_guard": {
            "max_bytes": 1048576,
            "extensions": ["mp4", "png"],
            "allow": [],
        },
    }
    with open(repo / "config" / "storage-policy.yaml", "w") as f:
        yaml.dump(policy, f)

    # scripts/media_guard.py -- copy of the real, merged guard script.
    (repo / "scripts").mkdir()
    (repo / "scripts" / "media_guard.py").write_text(REAL_MEDIA_GUARD.read_text())

    # .venv -- symlink to the real venv running this test (sys.prefix), which
    # already has PyYAML (media_guard.py imports it too). A symlink to just
    # the `python` binary is not enough: CPython's venv detection looks for
    # pyvenv.cfg next to argv0's own (unresolved) parent dirs, so it needs
    # `<repo>/.venv/pyvenv.cfg` to actually resolve -- symlinking the whole
    # .venv directory makes that transparent, and `<repo>/.venv/bin/python`
    # still resolves to sys.executable, never a bare "python".
    os.symlink(sys.prefix, repo / ".venv")

    return repo


def test_installer_writes_media_guard_stanza(throwaway_repo):
    result = run_installer(throwaway_repo)
    assert result.returncode == 0, result.stderr

    hook = throwaway_repo / ".git" / "hooks" / "pre-commit"
    assert hook.exists()
    text = hook.read_text()
    assert "BEGIN media-guard (pilot)" in text
    assert "END media-guard (pilot)" in text
    assert os.access(hook, os.X_OK)


def test_reinstall_does_not_duplicate_stanza(throwaway_repo):
    run_installer(throwaway_repo)
    result = run_installer(throwaway_repo)
    assert result.returncode == 0, result.stderr

    hook_text = (throwaway_repo / ".git" / "hooks" / "pre-commit").read_text()
    assert hook_text.count("BEGIN media-guard (pilot)") == 1
    assert hook_text.count("BEGIN gitleaks guard") == 1
    assert hook_text.count("BEGIN skill-lint") == 1


def test_large_mp4_blocked_for_pilot_worker(throwaway_repo):
    run_installer(throwaway_repo)

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id=PILOT_CTO_ID)
    assert res.returncode != 0
    assert "media_guard" in (res.stdout + res.stderr)
    assert subprocess.run(
        ["git", "log", "--oneline"], cwd=throwaway_repo, capture_output=True, text=True
    ).stdout.count("\n") == 1  # only the init commit


def test_large_mp4_allowed_for_non_pilot_worker(throwaway_repo):
    run_installer(throwaway_repo)

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id="someone-else")
    assert res.returncode == 0, res.stdout + res.stderr


def test_large_mp4_allowed_when_worker_cto_id_unset(throwaway_repo):
    run_installer(throwaway_repo)

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id=None)
    assert res.returncode == 0, res.stdout + res.stderr


def test_small_png_allowed_for_pilot_worker(throwaway_repo):
    run_installer(throwaway_repo)

    small_png = throwaway_repo / "small.png"
    small_png.write_bytes(b"0" * 1024)

    res = commit(throwaway_repo, ["small.png"], worker_cto_id=PILOT_CTO_ID)
    assert res.returncode == 0, res.stdout + res.stderr
