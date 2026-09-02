"""Tests for scripts/skill-doctrine-lint.py (ADR 0022 Wave 5, section 5.3).

This tool checks exactly one thing: every `**HARD --`-tagged rule block
across `.claude/skills/` carries a `Why hard:` clause somewhere before the
next rule or heading. It is a hand-run lint, never a gate -- the CLI has no
`--strict` mode and `main()` never refuses to write anything (there is
nothing to write; this tool only reads).

Every fixture lives under tmp_path, same convention as test_skill_lint.py:
this module never opens the real .claude/skills/ except in the two tests
that deliberately check the real corpus (the acceptance criterion this tool
exists to prove: zero defects against the post-Wave-5 corpus, and it did
report the two real ones found live during authoring, before they were
fixed).

Run standalone:   python scripts/test_skill_doctrine_lint.py
Or under pytest:  pytest scripts/test_skill_doctrine_lint.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "skill_doctrine_lint", ROOT / "scripts" / "skill-doctrine-lint.py"
)
assert _SPEC is not None and _SPEC.loader is not None
doctrine_lint = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = doctrine_lint
_SPEC.loader.exec_module(doctrine_lint)


def _write_skill_md(base: Path, name: str, body_lines: list[str]) -> Path:
    """A minimal but real SKILL.md -- frontmatter is irrelevant to this
    tool (it never parses YAML), so it stays trivial."""
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    fm = ["---", f"name: {name}", "description: fixture for doctrine-lint tests", "---", ""]
    (d / "SKILL.md").write_text("\n".join(fm + body_lines) + "\n", encoding="utf-8")
    return d


# --------------------------------------------------------------------------
# core detection: HARD tag -> block -> Why hard: clause
# --------------------------------------------------------------------------

def test_hard_block_with_why_hard_is_clean(tmp_path: Path) -> None:
    skill_md = _write_skill_md(tmp_path, "clean", [
        "## Rules",
        "",
        '1. **HARD — Never do the dangerous thing.** Detail here.',
        "",
        "   **Why hard:** money — it spends real credits with no undo.",
        "",
        "2. Advice: do the sensible thing instead, because X causes Y.",
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "clean")
    assert findings == []


def test_hard_block_missing_why_hard_is_a_defect(tmp_path: Path) -> None:
    """The exact case this tool exists to catch."""
    skill_md = _write_skill_md(tmp_path, "dirty", [
        "## Rules",
        "",
        '1. **HARD — Never do the dangerous thing.** Detail here, but no',
        "   justification clause anywhere in this block.",
        "",
        "2. Advice: do the sensible thing instead.",
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "dirty")
    assert len(findings) == 1
    assert findings[0].skill == "dirty"
    # 1-indexed line of the HARD tag: 5 frontmatter lines + 1 blank body
    # separator (see _write_skill_md) + the 3rd body_lines entry (index 2).
    assert findings[0].line == 8


def test_why_hard_after_the_next_hard_tag_does_not_count(tmp_path: Path) -> None:
    """A Why hard: clause belongs to the block it appears IN -- a second
    HARD rule's reason must not retroactively excuse the first rule's
    missing one."""
    skill_md = _write_skill_md(tmp_path, "two-rules", [
        '1. **HARD — First rule, no reason given here.**',
        '2. **HARD — Second rule.** **Why hard:** money.',
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "two-rules")
    assert len(findings) == 1
    assert findings[0].line == 6  # first body_lines entry, after 5 fm lines


def test_why_hard_is_case_insensitive(tmp_path: Path) -> None:
    skill_md = _write_skill_md(tmp_path, "case", [
        '1. **HARD — Do the thing.**',
        "   WHY HARD: it is irreversible.",
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "case")
    assert findings == []


def test_block_boundary_is_next_heading_when_no_next_rule(tmp_path: Path) -> None:
    """A HARD block that is the last rule under a heading still has a
    boundary -- the next heading, not end-of-file, so a Why hard: clause
    placed in the NEXT section must not count."""
    skill_md = _write_skill_md(tmp_path, "heading-boundary", [
        "## Rules",
        "",
        '1. **HARD — Last rule under this heading, no reason.**',
        "",
        "## Somewhere else entirely",
        "",
        "**Why hard:** this belongs to a different topic, not the rule above.",
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "heading-boundary")
    assert len(findings) == 1


# --------------------------------------------------------------------------
# false-positive avoidance -- narrative use of the word HARD, not a tag
# --------------------------------------------------------------------------

def test_narrative_use_of_the_word_hard_is_not_a_tag(tmp_path: Path) -> None:
    """Plain-English sentences that use the word HARD (not the `**HARD --`
    bold-open rule-tag shape) must not be flagged. All three lines below
    were real false positives caught while authoring this tool against the
    live corpus."""
    skill_md = _write_skill_md(tmp_path, "narrative", [
        "A skill with zero HARD rules is not a defect.",
        "See the HARD LIMIT above for the unrelated concept.",
        "The contract says a rule is either HARD-with-a-reason, or advice.",
        "Some HARDWARE reference that should never match either.",
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "narrative")
    assert findings == []


def test_heading_lines_are_never_treated_as_a_rule_tag(tmp_path: Path) -> None:
    skill_md = _write_skill_md(tmp_path, "heading-tag", [
        "## **HARD — this looks like a tag but it is a heading**",
        "",
        "Body text with no HARD tag at all.",
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "heading-tag")
    assert findings == []


def test_real_tag_shape_requires_bold_open_immediately_before_hard(tmp_path: Path) -> None:
    """`HARD --` without the immediately-preceding `**` is prose, not a tag
    -- this is what actually distinguishes rule 3's real tag from the
    narrative sentence describing the contract in the same file."""
    skill_md = _write_skill_md(tmp_path, "no-bold", [
        "The rule below is HARD -- no bold marker precedes it here.",
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "no-bold")
    assert findings == []


# --------------------------------------------------------------------------
# multiple defects in one file
# --------------------------------------------------------------------------

def test_multiple_defects_in_one_file_are_all_reported(tmp_path: Path) -> None:
    skill_md = _write_skill_md(tmp_path, "multi", [
        '1. **HARD — First, no reason.**',
        '2. **HARD — Second, no reason.**',
        '3. **HARD — Third.** **Why hard:** money.',
    ])
    findings = doctrine_lint.lint_skill_md(skill_md / "SKILL.md", "multi")
    assert len(findings) == 2
    assert [f.line for f in findings] == [6, 7]  # first two body_lines entries


# --------------------------------------------------------------------------
# symlink refusal -- must agree with skill-curator.py's invariant 3
# --------------------------------------------------------------------------

def test_symlinked_skill_dir_is_never_scanned(tmp_path: Path) -> None:
    curator = doctrine_lint._load_curator()
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)

    external_dir = tmp_path / "external-repo"
    real = _write_skill_md(external_dir, "real-skill", ['1. **HARD — no reason.**'])
    (owned_dir / "sym-skill").symlink_to(real, target_is_directory=True)

    files = doctrine_lint.discover_skill_md_files(owned_dir, curator)
    assert files == []


def test_ordinary_skill_dirs_are_discovered(tmp_path: Path) -> None:
    curator = doctrine_lint._load_curator()
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill_md(owned_dir, "one", ["no rules here"])
    _write_skill_md(owned_dir, "two", ["no rules here either"])

    files = doctrine_lint.discover_skill_md_files(owned_dir, curator)
    assert sorted(p.parent.name for p in files) == ["one", "two"]


# --------------------------------------------------------------------------
# root derivation -- never hardcoded (hard constraint #1)
# --------------------------------------------------------------------------

def test_root_is_derived_from_file_location_not_hardcoded(tmp_path: Path) -> None:
    """Same proof shape as test_skill_lint.py's equivalent test: copies the
    module into a throwaway tree that is NOT /Users/gob/Projects/Agents and
    NOT /opt/mooniex-agents, and asserts its ROOT tracks the copy."""
    fake_repo = tmp_path / "not-the-real-repo-root"
    fake_scripts = fake_repo / "scripts"
    fake_scripts.mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "skill-curator.py", fake_scripts / "skill-curator.py")
    shutil.copy(ROOT / "scripts" / "skill-doctrine-lint.py", fake_scripts / "skill-doctrine-lint.py")
    (fake_repo / ".claude" / "skills").mkdir(parents=True)

    spec = importlib.util.spec_from_file_location(
        "skill_doctrine_lint_copy", fake_scripts / "skill-doctrine-lint.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.ROOT == fake_repo
    assert module.ROOT != ROOT
    assert str(module.ROOT) not in ("/Users/gob/Projects/Agents", "/opt/mooniex-agents")

    curator_copy = module._load_curator()
    assert curator_copy.CuratorPaths.default().owned_skills_dir == fake_repo / ".claude" / "skills"


# --------------------------------------------------------------------------
# run_check / main -- end-to-end over a fixture directory
# --------------------------------------------------------------------------

def test_run_check_end_to_end_over_fixture_dir(tmp_path: Path) -> None:
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill_md(owned_dir, "clean", ['1. **HARD — ok.** **Why hard:** money.'])
    _write_skill_md(owned_dir, "dirty", ['1. **HARD — missing reason.**'])

    findings = doctrine_lint.run_check(owned_dir=owned_dir)
    assert len(findings) == 1
    assert findings[0].skill == "dirty"


def test_main_exit_code_is_zero_when_clean(tmp_path: Path) -> None:
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill_md(owned_dir, "clean", ['1. **HARD — ok.** **Why hard:** money.'])

    rc = doctrine_lint.main(["check", "--skills-dir", str(owned_dir)])
    assert rc == 0


def test_main_exit_code_is_nonzero_on_a_real_finding(tmp_path: Path) -> None:
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill_md(owned_dir, "dirty", ['1. **HARD — missing reason.**'])

    rc = doctrine_lint.main(["check", "--skills-dir", str(owned_dir)])
    assert rc == 1


def test_main_json_output_is_valid_json(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill_md(owned_dir, "dirty", ['1. **HARD — missing reason.**'])

    rc = doctrine_lint.main(["check", "--json", "--skills-dir", str(owned_dir)])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 1
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["skill"] == "dirty"


# --------------------------------------------------------------------------
# never a gate -- no --strict flag exists on the CLI
# --------------------------------------------------------------------------

def test_cli_has_no_strict_flag() -> None:
    """ADR 0022 CEO decisions 4 and 10: no approval gate, in any form. A
    --strict flag is exactly the shape a future caller could wire into a
    gate, so this asserts it was never added."""
    with pytest.raises(SystemExit):
        doctrine_lint.main(["check", "--strict"])


# --------------------------------------------------------------------------
# the real corpus -- the actual acceptance criterion
# --------------------------------------------------------------------------

def test_real_corpus_reports_zero_defects() -> None:
    """ADR 0022 Wave 5 acceptance criterion: after the higgsfield-unlimited-gen
    tiering pass, the real .claude/skills/ corpus reports zero doctrine
    defects. This is the one test in this module that reads real repo state
    on purpose -- everything else uses tmp_path fixtures."""
    findings = doctrine_lint.run_check()
    assert findings == [], (
        f"expected 0 real doctrine defects, found {len(findings)}: "
        + "; ".join(f"{f.file}:{f.line}" for f in findings)
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
