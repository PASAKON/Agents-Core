"""Tests for tools/skill_rename.py.

All fixtures live exclusively under pytest's `tmp_path` with a throwaway local
git repository and monkeypatched `skill_rename.ROOT` / `skill_rename.SKILLS`.
The real `.claude/skills` and repo checkout are never touched.
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import skill_rename


DEFAULT_PLAN = [
    {
        "old": "CTO_Film_Production",
        "new": "CMO_Knowledge_Film_Production",
        "kind": "knowledge",
        "owner": "CMO",
        "audience_add": ["cmo"],
    },
    {
        "old": "skill-curator",
        "new": "COO_Protocol_SkillCurator",
        "kind": "protocol",
        "owner": "COO",
        "audience_add": ["coo"],
    },
]


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def _build_fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Create a tiny fake repo tree in tmp_path and point skill_rename at it."""
    repo = tmp_path / "repo"
    skills = repo / ".claude" / "skills"

    # Skill 1: minimal frontmatter (missing kind/owner/aka/audience, plain description)
    _write(
        skills / "CTO_Film_Production" / "SKILL.md",
        "---\n"
        "name: CTO_Film_Production\n"
        "description: Film production facts and pointers to CTO_Film_PromptFormat.\n"
        "---\n\n"
        "# CTO_Film_Production\n\n"
        "Use CTO_Film_Production with CTO_Film_PromptFormat and `scripts/skill-curator.py`.\n",
    )
    _write(
        skills / "CTO_Film_Production" / "reference.md",
        "Extra notes for CTO_Film_PromptFormat.\n",
    )

    # Skill 2: existing kind/owner/aka/audience fields and quoted description
    _write(
        skills / "skill-curator" / "SKILL.md",
        "---\n"
        "name: skill-curator\n"
        "kind: rules\n"
        "owner: CTO\n"
        "aka: [legacy-curator]\n"
        "audience: [cto, worker]\n"
        'description: "Curates org skills alongside CTO_Film_Production."\n'
        "---\n\n"
        "# skill-curator\n\n"
        "Run `scripts/skill-curator.py` for skill-curator.\n",
    )

    # Skill 3: neighbor skill that shares the `CTO_Film_` prefix and is NOT renamed
    _write(
        skills / "CTO_Film_PromptFormat" / "SKILL.md",
        "---\n"
        "name: CTO_Film_PromptFormat\n"
        "kind: standard\n"
        "owner: CTO\n"
        "description: STANDARD — Prompt format standard for CTO_Film_PromptFormat.\n"
        "---\n\n"
        "# CTO_Film_PromptFormat\n\n"
        "Keep CTO_Film_PromptFormat separate.\n",
    )

    # INCLUDE referencing files
    _write(
        repo / "roles" / "cmo.md",
        "# CMO Role\n\n"
        "Owns CTO_Film_Production and CTO_Film_PromptFormat.\n"
        "Do not confuse CTO_Film_Production_Extra or Pre_CTO_Film_Production with CTO_Film_Production.\n"
        "See skill-curator. Also run scripts/skill-curator.py.\n",
    )
    _write(
        repo / "CLAUDE.md",
        "# CLAUDE\n\n"
        "Active skills: `CTO_Film_Production` and `skill-curator` and `CTO_Film_PromptFormat`.\n",
    )
    _write(
        repo / "docs" / "design" / "film-guide.md",
        "# Film Guide\n\n"
        "Pipeline uses CTO_Film_Production and CTO_Film_PromptFormat.\n",
    )

    # EXCLUDE_PREFIX referencing files (must remain untouched)
    _write(
        repo / "docs" / "reports" / "2026-09-27-report.md",
        "Historical report mentioning CTO_Film_Production and skill-curator.\n",
    )
    _write(
        repo / "docs" / "ops" / "migration.md",
        "Ops history mentioning CTO_Film_Production and skill-curator.\n",
    )

    # KEEP_OLD_NAMES referencing files (must remain untouched)
    _write(
        repo / "docs" / "org" / "SKILL-KINDS-2026-09-27.md",
        "Rename mapping: CTO_Film_Production -> CMO_Knowledge_Film_Production, "
        "skill-curator -> COO_Protocol_SkillCurator.\n",
    )
    _write(
        repo / "scripts" / "skill-curator.py",
        "# skill-curator script referencing skill-curator and CTO_Film_Production\n",
    )

    # Initialize an isolated throwaway git repo so `git -C ROOT mv` works inside tmp_path
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "--local", "user.email", "test@example.com"],
        ["git", "config", "--local", "user.name", "skill-rename-tests"],
        ["git", "config", "--local", "commit.gpgsign", "false"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "fixture"],
    ):
        subprocess.run(cmd, cwd=str(repo), check=True, capture_output=True)

    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(DEFAULT_PLAN), encoding="utf-8")

    monkeypatch.setattr(skill_rename, "ROOT", repo)
    monkeypatch.setattr(skill_rename, "SKILLS", skills)
    return repo, plan_path


def test_dry_run_changes_nothing_and_lists_moves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, plan_path = _build_fake_repo(tmp_path, monkeypatch)
    before = _snapshot(repo)

    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_path)])
    skill_rename.main()

    after = _snapshot(repo)
    assert after == before
    assert not (repo / ".claude" / "skills" / "CMO_Knowledge_Film_Production").exists()
    assert not (repo / ".claude" / "skills" / "COO_Protocol_SkillCurator").exists()

    out = capsys.readouterr().out
    assert "2 skills · 5 files · 13 mentions to rewrite" in out
    assert "dry run: nothing changed" in out
    assert ".claude/skills/CTO_Film_Production/SKILL.md" in out
    assert ".claude/skills/skill-curator/SKILL.md" in out
    assert "roles/cmo.md" in out
    assert "CLAUDE.md" in out
    assert "docs/design/film-guide.md" in out
    assert "docs/reports/2026-09-27-report.md" not in out
    assert "docs/org/SKILL-KINDS-2026-09-27.md" not in out
    assert "scripts/skill-curator.py" not in out


def test_apply_moves_dir_and_patches_frontmatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path = _build_fake_repo(tmp_path, monkeypatch)
    skills = repo / ".claude" / "skills"

    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_path), "--apply"])
    skill_rename.main()

    # Non-SKILL files inside the moved skill directory move to the new skill directory
    assert (skills / "CMO_Knowledge_Film_Production" / "reference.md").is_file()
    assert not (skills / "CTO_Film_Production" / "reference.md").exists()

    # Skill 1: missing kind/owner/aka/audience inserted, unquoted description prefixed with kind
    film_md = (skills / "CMO_Knowledge_Film_Production" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: CMO_Knowledge_Film_Production\n" in film_md
    assert "kind: knowledge\n" in film_md
    assert "owner: CMO\n" in film_md
    assert "aka: [CTO_Film_Production]\n" in film_md
    assert "audience: [cmo, worker]\n" in film_md
    assert (
        "description: KNOWLEDGE — Film production facts and pointers to CTO_Film_PromptFormat.\n"
        in film_md
    )

    # Skill 2: existing kind/owner overwritten, aka appended, audience prepended, quoted description prefixed
    curator_md = (skills / "COO_Protocol_SkillCurator" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: COO_Protocol_SkillCurator\n" in curator_md
    assert "kind: protocol\n" in curator_md
    assert "owner: COO\n" in curator_md
    assert "aka: [legacy-curator, skill-curator]\n" in curator_md
    assert "audience: [coo, cto, worker]\n" in curator_md
    assert (
        'description: "PROTOCOL — Curates org skills alongside CMO_Knowledge_Film_Production."\n'
        in curator_md
    )

    # Block-scalar description (`>-`) also receives the uppercase kind prefix on the first content line
    block_patched = skill_rename.patch_frontmatter(
        "---\nname: old-skill\ndescription: >-\n  Folded description line.\n---\nBody\n",
        {
            "old": "old-skill",
            "new": "ALL_Rules_NewSkill",
            "kind": "rules",
            "owner": "ALL",
            "audience_add": ["all"],
        },
    )
    assert "description: >-\n  RULES — Folded description line.\n" in block_patched


def test_apply_rewrites_whole_tokens_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path = _build_fake_repo(tmp_path, monkeypatch)

    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_path), "--apply"])
    skill_rename.main()

    cmo_text = (repo / "roles" / "cmo.md").read_text(encoding="utf-8")
    assert "Owns CMO_Knowledge_Film_Production and CTO_Film_PromptFormat." in cmo_text
    assert (
        "Do not confuse CTO_Film_Production_Extra or Pre_CTO_Film_Production "
        "with CMO_Knowledge_Film_Production." in cmo_text
    )
    assert "See COO_Protocol_SkillCurator. Also run scripts/skill-curator.py." in cmo_text

    claude_text = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert (
        "Active skills: `CMO_Knowledge_Film_Production` and `COO_Protocol_SkillCurator` "
        "and `CTO_Film_PromptFormat`." in claude_text
    )

    guide_text = (repo / "docs" / "design" / "film-guide.md").read_text(encoding="utf-8")
    assert "Pipeline uses CMO_Knowledge_Film_Production and CTO_Film_PromptFormat." in guide_text

    # Neighbor skill CTO_Film_PromptFormat is completely untouched
    prompt_md = (repo / ".claude" / "skills" / "CTO_Film_PromptFormat" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "name: CTO_Film_PromptFormat\n" in prompt_md
    assert "Keep CTO_Film_PromptFormat separate." in prompt_md


def test_apply_leaves_excluded_and_keep_old_names_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path = _build_fake_repo(tmp_path, monkeypatch)
    excluded_report = repo / "docs" / "reports" / "2026-09-27-report.md"
    excluded_ops = repo / "docs" / "ops" / "migration.md"
    keep_kinds_doc = repo / "docs" / "org" / "SKILL-KINDS-2026-09-27.md"
    keep_curator_py = repo / "scripts" / "skill-curator.py"

    expected = {
        p: p.read_text(encoding="utf-8")
        for p in (excluded_report, excluded_ops, keep_kinds_doc, keep_curator_py)
    }

    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_path), "--apply"])
    skill_rename.main()

    for path, original_text in expected.items():
        assert path.read_text(encoding="utf-8") == original_text
        assert "CTO_Film_Production" in path.read_text(encoding="utf-8")
        assert "skill-curator" in path.read_text(encoding="utf-8")


def test_apply_writes_30_day_redirect_stub_at_old_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path = _build_fake_repo(tmp_path, monkeypatch)
    skills = repo / ".claude" / "skills"

    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_path), "--apply"])
    skill_rename.main()

    today = datetime.date.today()
    until = (today + datetime.timedelta(days=30)).isoformat()

    for entry in DEFAULT_PLAN:
        stub_path = skills / entry["old"] / "SKILL.md"
        assert stub_path.is_file()
        stub_text = stub_path.read_text(encoding="utf-8")
        assert f"name: {entry['old']}\n" in stub_text
        assert f"kind: {entry['kind']}\n" in stub_text
        assert "disable-model-invocation: true\n" in stub_text
        assert f"MOVED to {entry['new']} on {today.isoformat()}." in stub_text
        assert f"this stub is removed after {until}." in stub_text
        assert f"MOVED: this skill is now `{entry['new']}`" in stub_text


def test_refuses_bad_plan_unknown_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path = _build_fake_repo(tmp_path, monkeypatch)
    before = _snapshot(repo)

    bad_kind_plan = [
        {
            "old": "CTO_Film_Production",
            "new": "CMO_Knowledge_Film_Production",
            "kind": "unknown_kind",
            "owner": "CMO",
            "audience_add": ["cmo"],
        }
    ]
    plan_path.write_text(json.dumps(bad_kind_plan), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_path), "--apply"])

    with pytest.raises(SystemExit, match="breaks the naming rule"):
        skill_rename.main()

    assert _snapshot(repo) == before


def test_refuses_bad_plan_target_exists_or_missing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path = _build_fake_repo(tmp_path, monkeypatch)
    before = _snapshot(repo)

    # Target already exists (`CTO_Film_PromptFormat` is already present in `.claude/skills`)
    target_exists_plan = [
        {
            "old": "CTO_Film_Production",
            "new": "CTO_Film_PromptFormat",
            "kind": "standard",
            "owner": "CTO",
            "audience_add": [],
        }
    ]
    plan_path.write_text(json.dumps(target_exists_plan), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_path), "--apply"])

    with pytest.raises(SystemExit, match="already exists"):
        skill_rename.main()

    assert _snapshot(repo) == before

    # Source skill does not exist
    missing_old_plan = [
        {
            "old": "No_Such_Skill",
            "new": "CMO_Knowledge_Film_Production",
            "kind": "knowledge",
            "owner": "CMO",
            "audience_add": [],
        }
    ]
    plan_path.write_text(json.dumps(missing_old_plan), encoding="utf-8")

    with pytest.raises(SystemExit, match="not found"):
        skill_rename.main()

    assert _snapshot(repo) == before
