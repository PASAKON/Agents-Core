"""tools/agy_kit_check.py — AGY must see every org skill (docs/design/cto-pair.md, 2026-11-19)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools import agy_kit_check


def _skill(d: Path, name: str) -> None:
    (d / name).mkdir(parents=True)
    (d / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")


def _repo(tmp: Path, *, org: int, tracked: list[str], untracked: list[str], cfg: list[str] | None = None) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    (tmp / ".agents").mkdir()
    (tmp / ".agents" / "skills.json").write_text(json.dumps(
        {"entries": [{"path": p} for p in (cfg if cfg is not None else [".agents/skills", ".claude/skills"])]}))
    for i in range(org):
        _skill(tmp / ".claude" / "skills", f"ORG_{i}")
    for n in tracked + untracked:
        _skill(tmp / ".agents" / "skills", n)
    for n in tracked:
        subprocess.run(["git", "-C", str(tmp), "add", f".agents/skills/{n}/SKILL.md"], check=True)
    return tmp


def test_clean_repo_passes(tmp_path: Path) -> None:
    r = agy_kit_check.check(_repo(tmp_path, org=5, tracked=["takeover"], untracked=[]), budget=10)
    assert r["ok"], r["problems"]
    assert r["total"] == 6


def test_untracked_third_party_skill_fails(tmp_path: Path) -> None:
    r = agy_kit_check.check(_repo(tmp_path, org=5, tracked=["takeover"], untracked=["asset-allocation"]), budget=10)
    assert not r["ok"]
    assert r["untracked"] == ["asset-allocation"]


def test_over_budget_fails(tmp_path: Path) -> None:
    r = agy_kit_check.check(_repo(tmp_path, org=11, tracked=[], untracked=[]), budget=10)
    assert not r["ok"]
    assert any("over the budget" in p for p in r["problems"])


def test_missing_claude_skills_entry_fails(tmp_path: Path) -> None:
    r = agy_kit_check.check(_repo(tmp_path, org=1, tracked=[], untracked=[], cfg=[".agents/skills"]), budget=10)
    assert not r["ok"]
    assert any("does not list .claude/skills" in p for p in r["problems"])


def test_this_repo_lists_claude_skills_and_fits_budget() -> None:
    r = agy_kit_check.check(budget=agy_kit_check.DEFAULT_BUDGET)
    assert ".agents/skills.json does not list .claude/skills" not in r["problems"]
    assert r["org_skills"] + 1 <= agy_kit_check.DEFAULT_BUDGET


@pytest.mark.parametrize("size", [900, 1000, 1200])
@pytest.mark.parametrize("style", ["quoted", "plain", "folded", "literal"])
def test_description_byte_limit(tmp_path: Path, size: int, style: str) -> None:
    root = _repo(tmp_path, org=1, tracked=[], untracked=[])
    # Thai characters demonstrate that the limit counts UTF-8 bytes, not characters.
    value = "ก" * (size // 3) + "x" * (size % 3)
    if style in ("folded", "literal"):
        value = (">-" if style == "folded" else "|-") + "\n  " + value
    elif style == "quoted":
        value = '"' + value + '"'
    (root / ".claude/skills/ORG_0/SKILL.md").write_text(
        f"---\nname: ORG_0\ndescription: {value}\nowner: CTO\n---\n"
        + "description: " + "z" * 2000, encoding="utf-8")
    result = agy_kit_check.check(root)
    assert result["ok"] == (size <= 1000)
    assert result["long_descriptions"] == ([("ORG_0", size)] if size > 1000 else [])
    if size > 1000:
        assert result["problems"] == [
            "1 skill description(s) over 1000 bytes: ORG_0 (1200)"]


def test_multiline_description_and_cli_override(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path, org=1, tracked=[], untracked=[])
    (root / ".claude/skills/ORG_0/SKILL.md").write_text(
        '---\ndescription: >\n  ' + 'x' * 600 + '\n  ' + 'y' * 600
        + '\nowner: CTO\n---\n', encoding="utf-8")
    assert agy_kit_check.check(root)["long_descriptions"] == [("ORG_0", 1201)]
    assert agy_kit_check.main(["--root", str(root), "--max-desc-bytes", "1201", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["long_descriptions"] == []
