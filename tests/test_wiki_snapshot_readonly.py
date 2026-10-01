"""wiki_write refuses a root that is not a git checkout (an rsync snapshot,
as Contabo's `org:` / `mooniex:` roots are), BEFORE writing anything."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.wiki as wiki  # noqa: E402


def test_snapshot_root_is_refused_and_left_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki, "_require_root", lambda ns: tmp_path)
    with pytest.raises(wiki.WikiError, match="read-only snapshot"):
        wiki.wiki_write("org:notes/x.md", "hello", role="cto")
    assert not (tmp_path / "notes" / "x.md").exists()


def test_git_root_still_writes_and_commits(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    monkeypatch.setattr(wiki, "_require_root", lambda ns: tmp_path)
    out = wiki.wiki_write("org:notes/x.md", "hello", role="cto")
    assert (tmp_path / "notes" / "x.md").read_text() == "hello"
    assert "no remote" in out
