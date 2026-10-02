"""scripts/sompong-inbox-deploy.sh and deploy/systemd/sompong-inbox.service (CEO 2026-10-02).

The inbox runs as root, so it must run a root-owned release, never the repo `sompong` edits. Every
test builds a throwaway git repo and inbox root in tmp, runs git as the current user
(SOMPONG_DEPLOY_RUNAS=""), and puts a FAKE systemctl in front: it logs its argv, and on `restart`
creates (or, in the failing mode, never creates) the inbox socket, so nothing reaches systemd.

Run: .venv/bin/python -m pytest tests/test_sompong_inbox_deploy.py
"""
from __future__ import annotations

import os
import socket
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "scripts" / "sompong-inbox-deploy.sh"
UNIT = ROOT / "deploy" / "systemd" / "sompong-inbox.service"

FAKE_SYSTEMCTL = r'''#!__PY__
import os, socket, sys
log = os.environ["FAKE_LOG"]
with open(log, "a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\n")
state = os.environ["SOMPONG_STATE_DIR"]
sock = os.path.join(state, "inbox.sock")
mode = os.environ.get("FAKE_MODE", "ok")
if sys.argv[1] == "restart":
    if os.path.exists(sock):
        os.unlink(sock)
    current = os.path.realpath(os.environ["SOMPONG_INBOX_ROOT"] + "/current")
    broken = os.path.exists(os.path.join(current, "BROKEN"))
    if mode == "ok" and not broken:
        s = socket.socket(socket.AF_UNIX); s.bind(sock); s.close()
    sys.exit(0)
if sys.argv[1] == "is-active":
    current = os.path.realpath(os.environ["SOMPONG_INBOX_ROOT"] + "/current")
    sys.exit(0 if mode == "ok" and not os.path.exists(os.path.join(current, "BROKEN")) else 3)
sys.exit(0)
'''


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture
def env(tmp_path: Path) -> dict:
    repo = tmp_path / "SomPong"
    (repo / "inbox").mkdir(parents=True)
    (repo / "inbox" / "__init__.py").write_text("")
    (repo / "inbox" / "__main__.py").write_text("print('inbox')\n")
    os.chmod(repo / "inbox" / "__main__.py", 0o700)
    (repo / "runner").mkdir()
    (repo / "runner" / "config.py").write_text("X = 1\n")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "one")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "systemctl"
    fake.write_text(FAKE_SYSTEMCTL.replace("__PY__", sys.executable))
    fake.chmod(0o755)
    state = tmp_path / "state"
    state.mkdir()
    (tmp_path / "unit").mkdir()
    return {
        **os.environ,
        "SOMPONG_REPO": str(repo),
        "SOMPONG_INBOX_ROOT": str(tmp_path / "inbox-root"),
        "SOMPONG_STATE_DIR": str(state),
        "SOMPONG_UNIT_DEST": str(tmp_path / "unit" / "sompong-inbox.service"),
        "SYSTEMCTL": str(fake),
        "SOMPONG_DEPLOY_RUNAS": "",
        "SOMPONG_DEPLOY_ALLOW_NONROOT": "1",
        "SOMPONG_DEPLOY_HEALTH_WAIT": "6",
        "FAKE_LOG": str(tmp_path / "systemctl.log"),
    }


def run(env: dict, *args: str, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(DEPLOY), *args], env={**env, **extra}, capture_output=True,
                          text=True, timeout=60)


def commit(env: dict, path: str, text: str, msg: str) -> str:
    repo = Path(env["SOMPONG_REPO"])
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", msg)
    return _git(repo, "rev-parse", "HEAD")


def test_deploy_makes_a_release_and_points_current_at_it(env, tmp_path):
    r = run(env)
    assert r.returncode == 0, r.stderr
    sha = _git(Path(env["SOMPONG_REPO"]), "rev-parse", "HEAD")
    rel = Path(env["SOMPONG_INBOX_ROOT"]) / "releases" / sha
    assert os.path.realpath(Path(env["SOMPONG_INBOX_ROOT"]) / "current") == str(rel)
    assert (rel / "inbox" / "__main__.py").read_text() == "print('inbox')\n"
    assert f"sha={sha}" in (rel / ".release").read_text()
    # modes are normalised: the 0700 file is 0644 in the release, dirs 0755
    assert stat.S_IMODE((rel / "inbox" / "__main__.py").stat().st_mode) == 0o644
    assert stat.S_IMODE((rel / "inbox").stat().st_mode) == 0o755
    log = Path(env["FAKE_LOG"]).read_text()
    assert "restart sompong-inbox.service" in log
    # the unit was installed from Agents-Core, then systemd reloaded
    assert Path(env["SOMPONG_UNIT_DEST"]).read_text() == UNIT.read_text()
    assert "daemon-reload" in log
    assert f"running release {sha}" in r.stdout


def test_unchanged_unit_is_not_reinstalled(env):
    dest = Path(env["SOMPONG_UNIT_DEST"])
    dest.write_text(UNIT.read_text())
    assert run(env).returncode == 0
    assert "daemon-reload" not in Path(env["FAKE_LOG"]).read_text()


def test_symlinks_in_the_commit_are_not_extracted(env):
    repo = Path(env["SOMPONG_REPO"])
    os.symlink("/etc/passwd", repo / "inbox" / "evil")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "link")
    r = run(env)
    assert r.returncode == 0, r.stderr
    rel = Path(env["SOMPONG_INBOX_ROOT"]) / "current"
    assert not os.path.lexists(rel / "inbox" / "evil")
    assert "skipped" in r.stderr and "inbox/evil" in r.stderr


@pytest.mark.parametrize("rev", ["-x", "main;id", "a b", "../x", "nope-not-a-branch"])
def test_bad_rev_is_refused_and_nothing_restarts(env, rev):
    r = run(env, rev)
    assert r.returncode != 0
    assert not Path(env["FAKE_LOG"]).exists()
    assert not (Path(env["SOMPONG_INBOX_ROOT"]) / "current").exists()


def test_a_commit_without_inbox_is_refused(env):
    repo = Path(env["SOMPONG_REPO"])
    _git(repo, "rm", "-rq", "inbox")
    _git(repo, "commit", "-qm", "no inbox")
    r = run(env)
    assert r.returncode != 0 and "no inbox/ package" in r.stderr
    assert not Path(env["FAKE_LOG"]).exists()


def test_a_release_that_does_not_come_up_rolls_back(env):
    assert run(env).returncode == 0
    good = os.path.realpath(Path(env["SOMPONG_INBOX_ROOT"]) / "current")
    bad_sha = commit(env, "BROKEN", "x", "broken")
    r = run(env)
    assert r.returncode != 0
    assert "rolled back" in r.stderr
    assert os.path.realpath(Path(env["SOMPONG_INBOX_ROOT"]) / "current") == good
    assert bad_sha not in os.path.realpath(Path(env["SOMPONG_INBOX_ROOT"]) / "current")


def test_first_release_that_fails_reports_no_rollback(env):
    r = run(env, FAKE_MODE="down")
    assert r.returncode != 0
    assert "no previous release" in r.stderr


def test_keeps_the_newest_five_releases(env):
    for i in range(7):
        commit(env, f"inbox/m{i}.py", f"x = {i}\n", f"c{i}")
        assert run(env).returncode == 0
    rels = list((Path(env["SOMPONG_INBOX_ROOT"]) / "releases").iterdir())
    assert len(rels) == 5
    live = os.path.realpath(Path(env["SOMPONG_INBOX_ROOT"]) / "current")
    assert live in {str(p) for p in rels}


def test_refuses_to_run_as_non_root_without_the_test_override(env):
    if os.geteuid() == 0:
        pytest.skip("running as root")
    e = {k: v for k, v in env.items() if k != "SOMPONG_DEPLOY_ALLOW_NONROOT"}
    r = subprocess.run(["bash", str(DEPLOY)], env=e, capture_output=True, text=True)
    assert r.returncode != 0 and "run as root" in r.stderr


def test_unit_runs_the_release_not_the_repo():
    text = UNIT.read_text()
    assert "WorkingDirectory=/opt/sompong-inbox/current" in text
    assert "Environment=SOMPONG_STATE_DIR=/var/lib/sompong-inbox" in text
    assert "ReadWritePaths=/var/lib/sompong-inbox" in text
    assert "Environment=SOMPONG_SOCKET_OWNER=sompong" in text
    active = [l for l in text.splitlines() if l and not l.startswith("#")]
    assert not any("Projects/MoonieX/SomPong" in l for l in active)
