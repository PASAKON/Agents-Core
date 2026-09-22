"""Tests for scripts/install-claude-home.sh (ADR 0027) — every run inside tmp_path
via CLAUDE_HOME / CLAUDE_HOME_SRC / PROJECTS; never touches the real ~/.claude.
The fixture SRC carries no plugins.txt and no launchd/, so those stanzas are
skipped and the test needs neither the `claude` CLI nor launchd.

Run: .venv/bin/python -m pytest scripts/test_install_claude_home.py -q
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "install-claude-home.sh"


def _src(tmp: Path) -> Path:
    src = tmp / "claude-home"
    (src / "hooks").mkdir(parents=True)
    (src / "commands").mkdir()
    (src / "mcp" / "mooniex-coord").mkdir(parents=True)
    (src / "tools").mkdir()
    (src / "CLAUDE.md").write_text("# global\n")
    (src / "settings.json").write_text('{"hooks": {}}\n')
    (src / "settings.local.json.example").write_text('{"permissions": {"allow": []}}\n')
    (src / "hooks" / "a.js").write_text("// a\n")
    (src / "commands" / "spawn-cto.md").write_text("spawn\n")
    (src / "mcp" / "mooniex-coord" / "index.mjs").write_text("// mcp\n")
    (src / "tools" / "t.py").write_text("print(1)\n")
    target = tmp / "Projects" / "Agents" / ".claude" / "skills" / "mapped-skill"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: mapped-skill\n---\n")
    (src / "skills.txt").write_text("# name\ttarget\nmapped-skill\t$PROJECTS/Agents/.claude/skills/mapped-skill\nghost-skill\t$PROJECTS/nowhere/ghost-skill\n")
    return src


def _run(tmp: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update({
        "CLAUDE_HOME": str(tmp / "dot-claude"),
        "CLAUDE_HOME_SRC": str(tmp / "claude-home"),
        "PROJECTS": str(tmp / "Projects"),
        "HOME": str(tmp / "home"),
    })
    (tmp / "home").mkdir(exist_ok=True)
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True)


def test_fresh_install_links_every_entry_and_check_is_then_clean(tmp_path: Path) -> None:
    src = _src(tmp_path)
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    home = tmp_path / "dot-claude"
    for rel in ("CLAUDE.md", "settings.json", "hooks", "commands", "mcp/mooniex-coord", "tools"):
        p = home / rel
        assert p.is_symlink() and Path(os.readlink(p)) == src / rel, rel
    assert (home / "skills" / "mapped-skill").is_symlink()
    assert (home / "settings.local.json").is_file() and not (home / "settings.local.json").is_symlink()
    assert "WARN     ghost-skill: target missing" in r.stdout  # warns, does not fail
    c = _run(tmp_path, "--check")
    assert c.returncode == 0, c.stdout
    assert "clean" in c.stdout


def test_check_reports_drift_for_a_real_file_and_changes_nothing(tmp_path: Path) -> None:
    _src(tmp_path)
    home = tmp_path / "dot-claude"
    home.mkdir()
    (home / "CLAUDE.md").write_text("# edited live\n")
    c = _run(tmp_path, "--check")
    assert c.returncode == 1
    assert "DRIFT    CLAUDE.md is a real copy and DIFFERS" in c.stdout
    assert (home / "CLAUDE.md").is_file() and not (home / "CLAUDE.md").is_symlink()  # untouched


def test_install_captures_a_differing_real_file_into_the_repo_then_links(tmp_path: Path) -> None:
    src = _src(tmp_path)
    home = tmp_path / "dot-claude"
    home.mkdir()
    (home / "settings.json").write_text('{"hooks": {}, "model": "opus"}\n')
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CAPTURED settings.json" in r.stdout
    assert (src / "settings.json").read_text() == '{"hooks": {}, "model": "opus"}\n'  # live edit survived
    assert (home / "settings.json").is_symlink()
    backups = list((home / "backups").glob("claude-home-*/settings.json"))
    assert len(backups) == 1 and backups[0].read_text() == '{"hooks": {}, "model": "opus"}\n'


def test_unmapped_real_skill_dir_is_reported_and_never_clobbered(tmp_path: Path) -> None:
    _src(tmp_path)
    home = tmp_path / "dot-claude"
    (home / "skills" / "orphan").mkdir(parents=True)
    (home / "skills" / "orphan" / "SKILL.md").write_text("x")
    (home / "skills" / "synced").mkdir()  # Claude's own — exempt
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "UNMAPPED real dir skills/orphan" in r.stdout
    assert "synced" not in r.stdout
    assert (home / "skills" / "orphan" / "SKILL.md").read_text() == "x"


def test_mapped_skill_that_is_a_real_dir_is_drift_not_overwritten(tmp_path: Path) -> None:
    _src(tmp_path)
    home = tmp_path / "dot-claude"
    (home / "skills" / "mapped-skill").mkdir(parents=True)
    (home / "skills" / "mapped-skill" / "SKILL.md").write_text("real")
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "DRIFT    skills/mapped-skill is a REAL dir" in r.stdout
    assert (home / "skills" / "mapped-skill" / "SKILL.md").read_text() == "real"


def test_install_is_idempotent(tmp_path: Path) -> None:
    _src(tmp_path)
    assert _run(tmp_path).returncode == 0
    r = _run(tmp_path)
    assert r.returncode == 0 and "CAPTURED" not in r.stdout and "backed up" not in r.stdout


def test_missing_src_dir_exits_2(tmp_path: Path) -> None:
    r = _run(tmp_path)
    assert r.returncode == 2
