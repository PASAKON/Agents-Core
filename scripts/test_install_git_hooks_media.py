"""
Tests for the media-guard stanza written by scripts/install-git-hooks.sh.

Runs the installer against a throwaway repo under tmp_path -- never the real
repo, per task rules. The throwaway repo gets its own config/storage-policy.yaml
(a tmp policy) and a copy of the real scripts/media_guard.py, plus a
.venv/bin/python symlinked to sys.executable (the interpreter running pytest,
which already has PyYAML -- media_guard.py and its own test already depend on
it) so the hook's scope check has a real python+yaml to read with.
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


def _write_policy(repo, scope_media_guard):
    """Overwrite config/storage-policy.yaml's `scope.media_guard`. The hook
    reads the policy fresh at every commit, so tests can flip scope between
    commits without re-running the installer."""
    policy = {
        "scope": {"media_guard": scope_media_guard},
        "media_guard": {
            "max_bytes": 1048576,
            "extensions": ["mp4", "png"],
            "allow": [],
        },
    }
    with open(repo / "config" / "storage-policy.yaml", "w") as f:
        yaml.dump(policy, f)


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

    # config/storage-policy.yaml -- the "tmp policy": scope.media_guard for
    # the WORKER_CTO_ID gate (list scope by default), media_guard for
    # scripts/media_guard.py itself (same file, same shape as the real
    # config/storage-policy.yaml).
    (repo / "config").mkdir()
    _write_policy(repo, [PILOT_CTO_ID])

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
    assert "BEGIN media-guard" in text
    assert "END media-guard" in text
    assert os.access(hook, os.X_OK)


def test_reinstall_does_not_duplicate_stanza(throwaway_repo):
    run_installer(throwaway_repo)
    result = run_installer(throwaway_repo)
    assert result.returncode == 0, result.stderr

    hook_text = (throwaway_repo / ".git" / "hooks" / "pre-commit").read_text()
    assert hook_text.count("BEGIN media-guard") == 1
    assert hook_text.count("BEGIN gitleaks guard") == 1
    assert hook_text.count("BEGIN skill-lint") == 1


def test_reinstall_rewrites_stale_stanza_body(throwaway_repo):
    """The bug this task fixes: the old installer SKIPPED the whole
    media-guard block whenever its BEGIN marker was already present, so a
    repo whose hook was written before the scope-map switch would keep
    running the stale (pre-scope) body forever. Hand-write a stanza with
    the SAME markers but a sabotaged body (`exit 1` unconditionally), then
    re-run the installer -- it must replace the body, not leave the
    sabotaged one in place. This fails if `install-git-hooks.sh` goes back
    to `if ! grep -q 'BEGIN media-guard' ...; then ... fi` around this
    stanza."""
    hook = throwaway_repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/bin/sh\n"
        "\n"
        "# --- BEGIN media-guard (ADR 0030 / Work/RULES.md rule 5; tracked via scripts/install-git-hooks.sh) ---\n"
        "echo 'stale stanza, must be replaced' >&2\n"
        "exit 1\n"
        "# --- END media-guard ---\n"
        "\n"
        "exit 0\n"
    )
    hook.chmod(0o755)

    result = run_installer(throwaway_repo)
    assert result.returncode == 0, result.stderr

    text = hook.read_text()
    assert text.count("BEGIN media-guard") == 1
    assert "stale stanza, must be replaced" not in text
    assert "scope_rc" in text  # the real, current stanza body landed

    # And the replaced stanza actually works: a small file, scope-list
    # membership -- must be allowed, not the sabotaged unconditional exit 1.
    small_png = throwaway_repo / "small.png"
    small_png.write_bytes(b"0" * 1024)
    res = commit(throwaway_repo, ["small.png"], worker_cto_id=PILOT_CTO_ID)
    assert res.returncode == 0, res.stdout + res.stderr


# --------------------------------------------------------- scope: a list


def test_large_mp4_blocked_for_scope_list_member(throwaway_repo):
    run_installer(throwaway_repo)

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id=PILOT_CTO_ID)
    assert res.returncode != 0
    assert "media_guard" in (res.stdout + res.stderr)
    assert subprocess.run(
        ["git", "log", "--oneline"], cwd=throwaway_repo, capture_output=True, text=True
    ).stdout.count("\n") == 1  # only the init commit


def test_large_mp4_allowed_for_non_member(throwaway_repo):
    run_installer(throwaway_repo)

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id="someone-else")
    assert res.returncode == 0, res.stdout + res.stderr


def test_large_mp4_allowed_when_worker_cto_id_unset_and_scope_is_list(throwaway_repo):
    run_installer(throwaway_repo)

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id=None)
    assert res.returncode == 0, res.stdout + res.stderr


def test_small_png_allowed_for_scope_list_member(throwaway_repo):
    run_installer(throwaway_repo)

    small_png = throwaway_repo / "small.png"
    small_png.write_bytes(b"0" * 1024)

    res = commit(throwaway_repo, ["small.png"], worker_cto_id=PILOT_CTO_ID)
    assert res.returncode == 0, res.stdout + res.stderr


# ------------------------------------------------------- scope: "all"


def test_large_mp4_blocked_for_every_commit_when_scope_is_all(throwaway_repo):
    """"all" runs the guard for EVERY commit -- WORKER_CTO_ID need not even
    be set. This fails if the stanza still requires WORKER_CTO_ID before
    reading policy at all (today's pre-scope-map `if [ -n
    "${WORKER_CTO_ID:-}" ]` gate around the whole block)."""
    run_installer(throwaway_repo)
    _write_policy(throwaway_repo, "all")

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id=None)
    assert res.returncode != 0
    assert "media_guard" in (res.stdout + res.stderr)


def test_large_mp4_blocked_for_any_worker_when_scope_is_all(throwaway_repo):
    run_installer(throwaway_repo)
    _write_policy(throwaway_repo, "all")

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id="anybody-at-all")
    assert res.returncode != 0
    assert "media_guard" in (res.stdout + res.stderr)


# ------------------------------------------------- missing scope key / unreadable


def test_large_mp4_allowed_when_media_guard_scope_key_missing(throwaway_repo):
    """Missing `scope.media_guard` -> warn, never block (same contract as an
    unreadable policy file)."""
    run_installer(throwaway_repo)
    policy = {
        "media_guard": {"max_bytes": 1048576, "extensions": ["mp4", "png"], "allow": []},
    }
    with open(throwaway_repo / "config" / "storage-policy.yaml", "w") as f:
        yaml.dump(policy, f)

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id=PILOT_CTO_ID)
    assert res.returncode == 0, res.stdout + res.stderr


def test_large_mp4_allowed_when_policy_unreadable(throwaway_repo):
    run_installer(throwaway_repo)
    (throwaway_repo / "config" / "storage-policy.yaml").write_text("not: [valid, yaml: :::")

    large_mp4 = throwaway_repo / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))

    res = commit(throwaway_repo, ["large.mp4"], worker_cto_id=PILOT_CTO_ID)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "could not read storage policy" in (res.stdout + res.stderr)
