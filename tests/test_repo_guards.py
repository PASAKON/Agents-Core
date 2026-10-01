"""CI repo guards: scripts/conflict_marker_guard.py and media_guard.py --since.

The pre-commit hooks are local to each machine and were never installed on
every box, so CI (.github/workflows/ci.yml `repo-guards`) runs both on what a
push or pull request brings in.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.conflict_marker_guard as cmg  # noqa: E402

MEDIA_GUARD = ROOT / "scripts" / "media_guard.py"
POLICY = ROOT / "config" / "storage-policy.yaml"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _commit(repo, msg="c"):
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", msg)


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "README.md").write_text("Title\n=======\n")
    _commit(r, "init")
    return r


def test_clean_repo_passes(repo):
    assert cmg.find_markers(repo) == {}


def test_committed_conflict_is_found(repo):
    (repo / "doc.md").write_text("a\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> topic\nb\n")
    _commit(repo)
    assert cmg.find_markers(repo) == {"doc.md": [2, 6]}
    assert cmg.main(["--repo", str(repo)]) == 1


def test_a_lone_marker_like_line_is_not_a_conflict(repo):
    (repo / "doc.md").write_text("<<<<<<< this is a quote of git output\n")
    _commit(repo)
    assert cmg.find_markers(repo) == {}


def _media_guard(repo, since):
    return subprocess.run([sys.executable, str(MEDIA_GUARD), "--policy", str(POLICY),
                           "--repo", str(repo), "--since", since],
                          capture_output=True, text=True)


def test_since_flags_large_media_added_after_the_base(repo):
    base = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    (repo / "big.png").write_bytes(os.urandom(2 * 1024 * 1024))
    _commit(repo)
    r = _media_guard(repo, base)
    assert r.returncode == 1 and "big.png" in r.stdout


def test_since_ignores_media_already_on_the_base(repo):
    (repo / "big.png").write_bytes(os.urandom(2 * 1024 * 1024))
    _commit(repo)
    base = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    (repo / "note.md").write_text("x\n")
    _commit(repo)
    assert _media_guard(repo, base).returncode == 0


def test_since_with_an_unknown_base_skips(repo):
    r = _media_guard(repo, "0123456789abcdef0123456789abcdef01234567")
    assert r.returncode == 0 and "skipped" in r.stdout


def test_this_repo_has_no_conflict_markers():
    assert cmg.find_markers(ROOT) == {}
