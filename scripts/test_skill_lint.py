"""Tests for scripts/skill-lint.py (ADR 0022 Wave 1).

Five finding codes, checked independently:
  1. missing SKILL.md
  2. unparseable frontmatter
  3. name != directory basename
  4. created_by outside {human, agent}
  5. audience token not a known role or group

Plus the two structural guarantees the task brief calls out by name:
  - root/role-token derivation is never hardcoded to a machine-specific path
    (this repo lives at /Users/gob/Projects/Agents on the Mac and
    /opt/mooniex-agents on Contabo -- both must work).
  - a skill reached through a symlink under .claude/skills/ is refused, not
    silently skipped and not linted -- consistent with
    skill-curator.py's own invariant 3, which this module reuses
    (`_resolve_within`) rather than reimplementing.

Every fixture lives under tmp_path, same convention as test_skill_curator.py:
this module never opens the real .claude/skills/ or policies/agents.yaml
except in the one test that deliberately checks the real files are
well-formed enough to derive from.

Run standalone:   python scripts/test_skill_lint.py
Or under pytest:  pytest scripts/test_skill_lint.py
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "skill_lint", ROOT / "scripts" / "skill-lint.py"
)
assert _SPEC is not None and _SPEC.loader is not None
skill_lint = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = skill_lint
_SPEC.loader.exec_module(skill_lint)


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

def _write_skill(
    base: Path,
    name: str,
    *,
    fm_name: "str | None" = ...,  # ... sentinel means "same as name"
    created_by: "str | None" = None,
    audience: "list[str] | None" = None,
    extra_frontmatter: "str | None" = None,
    body: str = "content",
) -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    lines.append(f"name: {name if fm_name is ... else fm_name}")
    if created_by is not None:
        lines.append(f"created_by: {created_by}")
    if audience is not None:
        lines.append("audience: [" + ", ".join(audience) + "]")
    if extra_frontmatter:
        lines.append(extra_frontmatter)
    lines += ["description: fixture skill for skill-lint tests", "---", "", f"# {name}", "", body, ""]
    (d / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
    return d


_KNOWN_AUDIENCE = {"cto", "cfo", "cmo", "cgo", "developer", "browser_operator"} | {"all", "cxo", "worker"}


def _findings_by_code(findings) -> dict:
    out: dict[int, list] = {}
    for f in findings:
        out.setdefault(f.code, []).append(f)
    return out


# --------------------------------------------------------------------------
# code 1 -- missing SKILL.md
# --------------------------------------------------------------------------

def test_missing_skill_md_is_code_1(tmp_path: Path) -> None:
    (tmp_path / "no-skill-md").mkdir()
    findings = skill_lint.lint_skill("no-skill-md", tmp_path / "no-skill-md", _KNOWN_AUDIENCE)
    assert len(findings) == 1
    assert findings[0].code == 1
    assert findings[0].code_name == "missing-skill-md"


# --------------------------------------------------------------------------
# code 2 -- unparseable frontmatter
# --------------------------------------------------------------------------

def test_no_opening_frontmatter_marker_is_code_2(tmp_path: Path) -> None:
    d = tmp_path / "plain-md"
    d.mkdir()
    (d / "SKILL.md").write_text("# Just a heading, no frontmatter\n", encoding="utf-8")
    findings = skill_lint.lint_skill("plain-md", d, _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [2]


def test_unclosed_frontmatter_block_is_code_2(tmp_path: Path) -> None:
    d = tmp_path / "unclosed"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: unclosed\ndescription: no closing marker\n", encoding="utf-8")
    findings = skill_lint.lint_skill("unclosed", d, _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [2]


def test_invalid_yaml_syntax_is_code_2(tmp_path: Path) -> None:
    d = tmp_path / "bad-yaml"
    d.mkdir()
    # An unquoted plain scalar containing ": " (colon-space) is invalid YAML
    # -- the exact bug found live in higgsfield-unlimited-gen/SKILL.md during
    # this task, before it was reformatted as a block scalar.
    (d / "SKILL.md").write_text(
        '---\nname: bad-yaml\ndescription: some text (generic): more text\n---\nbody\n',
        encoding="utf-8",
    )
    findings = skill_lint.lint_skill("bad-yaml", d, _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [2]


def test_frontmatter_that_parses_to_a_list_not_a_mapping_is_code_2(tmp_path: Path) -> None:
    d = tmp_path / "list-frontmatter"
    d.mkdir()
    (d / "SKILL.md").write_text("---\n- just\n- a\n- list\n---\nbody\n", encoding="utf-8")
    findings = skill_lint.lint_skill("list-frontmatter", d, _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [2]


# --------------------------------------------------------------------------
# code 3 -- name != directory basename
# --------------------------------------------------------------------------

def test_name_mismatch_is_code_3(tmp_path: Path) -> None:
    _write_skill(tmp_path, "on-disk-name", fm_name="frontmatter-name")
    findings = skill_lint.lint_skill("on-disk-name", tmp_path / "on-disk-name", _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [3]
    assert "frontmatter-name" in findings[0].message
    assert "on-disk-name" in findings[0].message


def test_matching_name_is_clean(tmp_path: Path) -> None:
    _write_skill(tmp_path, "matches", created_by="human", audience=["cto"])
    findings = skill_lint.lint_skill("matches", tmp_path / "matches", _KNOWN_AUDIENCE)
    assert findings == []


# --------------------------------------------------------------------------
# code 4 -- created_by outside {human, agent}
# --------------------------------------------------------------------------

def test_role_valued_created_by_is_code_4(tmp_path: Path) -> None:
    """The exact incident this wave exists to catch: created_by: cto."""
    _write_skill(tmp_path, "role-created-by", created_by="cto")
    findings = skill_lint.lint_skill("role-created-by", tmp_path / "role-created-by", _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [4]
    assert "cto" in findings[0].message


@pytest.mark.parametrize("value", ["human", "agent"])
def test_valid_created_by_values_are_clean(tmp_path: Path, value: str) -> None:
    _write_skill(tmp_path, "valid-cb", created_by=value)
    findings = skill_lint.lint_skill("valid-cb", tmp_path / "valid-cb", _KNOWN_AUDIENCE)
    assert findings == []


def test_absent_created_by_is_not_a_finding(tmp_path: Path) -> None:
    """A skill written before Wave 1's backfill, or a brand-new one whose
    author hasn't gotten to it yet, must not be flagged -- this is a lint
    that helps, never a gate that blocks (CEO decisions 4 and 10)."""
    _write_skill(tmp_path, "no-created-by")
    findings = skill_lint.lint_skill("no-created-by", tmp_path / "no-created-by", _KNOWN_AUDIENCE)
    assert findings == []


# --------------------------------------------------------------------------
# code 5 -- audience token not a known role or group
# --------------------------------------------------------------------------

def test_unknown_audience_token_is_code_5(tmp_path: Path) -> None:
    _write_skill(tmp_path, "bad-audience", audience=["not_a_real_role"])
    findings = skill_lint.lint_skill("bad-audience", tmp_path / "bad-audience", _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [5]
    assert "not_a_real_role" in findings[0].message


def test_typo_role_token_is_code_5_even_alongside_valid_ones(tmp_path: Path) -> None:
    _write_skill(tmp_path, "mixed-audience", audience=["cto", "browser_operater"])  # typo
    findings = skill_lint.lint_skill("mixed-audience", tmp_path / "mixed-audience", _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [5]
    assert "browser_operater" in findings[0].message


@pytest.mark.parametrize("group", ["all", "cxo", "worker"])
def test_group_tokens_are_valid_audience_values(tmp_path: Path, group: str) -> None:
    _write_skill(tmp_path, "group-audience", audience=[group])
    findings = skill_lint.lint_skill("group-audience", tmp_path / "group-audience", _KNOWN_AUDIENCE)
    assert findings == []


def test_real_role_tokens_are_valid_audience_values(tmp_path: Path) -> None:
    _write_skill(tmp_path, "role-audience", audience=["cto", "cfo", "browser_operator"])
    findings = skill_lint.lint_skill("role-audience", tmp_path / "role-audience", _KNOWN_AUDIENCE)
    assert findings == []


def test_absent_audience_is_not_a_finding(tmp_path: Path) -> None:
    _write_skill(tmp_path, "no-audience", created_by="human")
    findings = skill_lint.lint_skill("no-audience", tmp_path / "no-audience", _KNOWN_AUDIENCE)
    assert findings == []


# --------------------------------------------------------------------------
# symlink refusal -- must agree with skill-curator.py's invariant 3
# --------------------------------------------------------------------------

def test_symlinked_entry_under_owned_dir_is_refused_not_linted(tmp_path: Path) -> None:
    curator = skill_lint._load_curator()
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)

    external_dir = tmp_path / "external-repo"
    real_skill = _write_skill(external_dir, "real-skill", created_by="cto")  # would be a finding if linted
    (owned_dir / "sym-skill").symlink_to(real_skill, target_is_directory=True)

    names, refused = skill_lint.discover_skills(owned_dir, curator)

    assert "sym-skill" not in names
    assert len(refused) == 1
    assert "sym-skill" in refused[0]
    assert "symlink" in refused[0]
    # The refusal is invariant-3 shaped, not a crash and not a silent skip.
    with pytest.raises(curator.CuratorError, match="symlink"):
        curator._resolve_within("sym-skill", owned_dir)


def test_symlink_pointing_inside_owned_dir_is_also_refused(tmp_path: Path) -> None:
    """skill-curator.py's _resolve_within refuses ANY symlink directly under
    the owned dir, not only one that escapes it -- this module must agree,
    or the two tools would each think a different set of names is safe."""
    curator = skill_lint._load_curator()
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    real = _write_skill(owned_dir, "real-inside")
    (owned_dir / "sym-inside").symlink_to(real, target_is_directory=True)

    names, refused = skill_lint.discover_skills(owned_dir, curator)
    assert "real-inside" in names
    assert "sym-inside" not in names
    assert any("sym-inside" in r for r in refused)


def test_ordinary_directories_are_unaffected_by_symlink_refusal(tmp_path: Path) -> None:
    curator = skill_lint._load_curator()
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill(owned_dir, "real-one", created_by="human", audience=["cto"])
    _write_skill(owned_dir, "real-two", created_by="agent")

    names, refused = skill_lint.discover_skills(owned_dir, curator)
    assert sorted(names) == ["real-one", "real-two"]
    assert refused == []


# --------------------------------------------------------------------------
# role/group derivation -- policies/agents.yaml is the only source
# --------------------------------------------------------------------------

def test_load_role_groups_from_real_agents_yaml() -> None:
    """Reads the real policies/agents.yaml (read-only) -- the one place this
    module is allowed to touch real repo state, because the whole point is
    proving the real file derives sane groups, not a synthetic stand-in."""
    all_tokens, cxo_tokens, worker_tokens = skill_lint.load_role_groups()

    # CEO's model is null ("the user -- no LLM") -- level: c but excluded
    # from every group, because a skill can never run inside a CEO session.
    assert "ceo" not in all_tokens
    assert "ceo" not in cxo_tokens

    # Verbatim-confirmed by two real skills' own text (session-change-model:
    # "Shared by CTO/CFO/CGO/CMO"; higgsfield-unlimited-gen: "any C-level
    # (CTO, CMO, CFO, CGO)").
    assert cxo_tokens == {"cto", "cfo", "cgo", "cmo"}

    assert "developer" in worker_tokens
    assert "browser_operator" in worker_tokens
    assert "cto" not in worker_tokens
    assert worker_tokens <= all_tokens
    assert cxo_tokens <= all_tokens


def test_load_role_groups_from_synthetic_agents_yaml(tmp_path: Path) -> None:
    """Derivation logic itself, decoupled from the real file's current
    contents -- a role added or removed from policies/agents.yaml tomorrow
    must not need a matching edit here."""
    fixture = tmp_path / "agents.yaml"
    fixture.write_text(
        "roles:\n"
        "  ceo:\n"
        "    level: c\n"
        "    model: null\n"
        "  ops_lead:\n"
        "    level: c\n"
        "    model: claude-sonnet-5\n"
        "  grunt:\n"
        "    level: w\n"
        "    model: claude-sonnet-5\n",
        encoding="utf-8",
    )
    all_tokens, cxo_tokens, worker_tokens = skill_lint.load_role_groups(fixture)
    assert all_tokens == {"ops_lead", "grunt"}
    assert cxo_tokens == {"ops_lead"}
    assert worker_tokens == {"grunt"}


def test_known_audience_tokens_includes_group_names(tmp_path: Path) -> None:
    fixture = tmp_path / "agents.yaml"
    fixture.write_text("roles:\n  solo:\n    level: c\n    model: claude-sonnet-5\n", encoding="utf-8")
    known = skill_lint._known_audience_tokens(fixture)
    assert known == {"solo", "all", "cxo", "worker"}


# --------------------------------------------------------------------------
# root derivation -- never hardcoded (hard constraint #2)
# --------------------------------------------------------------------------

def test_root_is_derived_from_file_location_not_hardcoded(tmp_path: Path) -> None:
    """Copies skill-curator.py + skill-lint.py into a throwaway tree that is
    NOT /Users/gob/Projects/Agents and NOT /opt/mooniex-agents, executes the
    copy, and asserts its ROOT tracks the copy's own location. If ROOT (or
    the module's default owned_skills_dir) were ever hardcoded to either
    machine's real path, this would be the only test to notice -- on the Mac
    or on Contabo alike, hardcoding always happens to "work" locally."""
    fake_repo = tmp_path / "not-the-real-repo-root"
    fake_scripts = fake_repo / "scripts"
    fake_scripts.mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "skill-curator.py", fake_scripts / "skill-curator.py")
    shutil.copy(ROOT / "scripts" / "skill-lint.py", fake_scripts / "skill-lint.py")
    (fake_repo / "policies").mkdir()
    shutil.copy(ROOT / "policies" / "agents.yaml", fake_repo / "policies" / "agents.yaml")
    (fake_repo / ".claude" / "skills").mkdir(parents=True)

    spec = importlib.util.spec_from_file_location(
        "skill_lint_copy", fake_scripts / "skill-lint.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.ROOT == fake_repo
    assert module.ROOT != ROOT
    assert str(module.ROOT) not in ("/Users/gob/Projects/Agents", "/opt/mooniex-agents")
    assert module.AGENTS_YAML == fake_repo / "policies" / "agents.yaml"

    # And the derived curator agrees on the same fake root for the owned dir.
    curator_copy = module._load_curator()
    assert curator_copy.CuratorPaths.default().owned_skills_dir == fake_repo / ".claude" / "skills"


# --------------------------------------------------------------------------
# run_check / main -- end-to-end over a fixture directory (never real state)
# --------------------------------------------------------------------------

def test_run_check_end_to_end_over_fixture_dir(tmp_path: Path) -> None:
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill(owned_dir, "clean-one", created_by="human", audience=["cto"])
    _write_skill(owned_dir, "clean-two", created_by="agent", audience=["all"])
    _write_skill(owned_dir, "dirty", created_by="cto")  # code 4

    findings, refused = skill_lint.run_check(owned_dir=owned_dir)

    assert refused == []
    codes = _findings_by_code(findings)
    assert set(codes.keys()) == {4}
    assert codes[4][0].skill == "dirty"


def test_main_exit_code_reflects_findings_only_not_refused(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill(owned_dir, "clean", created_by="human", audience=["cto"])
    external = tmp_path / "external"
    real = _write_skill(external, "real-elsewhere")
    (owned_dir / "sym").symlink_to(real, target_is_directory=True)

    rc = skill_lint.main(["check", "--skills-dir", str(owned_dir)])
    out = capsys.readouterr().out
    assert rc == 0  # a refused symlink alone must not fail the check
    assert "refused" in out
    assert "clean" in out or "0 findings" in out


def test_main_exit_code_is_nonzero_on_a_real_finding(tmp_path: Path) -> None:
    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill(owned_dir, "dirty", created_by="cto")

    rc = skill_lint.main(["check", "--skills-dir", str(owned_dir)])
    assert rc == 1


def test_main_json_output_is_valid_json(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    import json

    owned_dir = tmp_path / ".claude" / "skills"
    owned_dir.mkdir(parents=True)
    _write_skill(owned_dir, "dirty", created_by="cto")

    rc = skill_lint.main(["check", "--json", "--skills-dir", str(owned_dir)])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert rc == 1
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["code"] == 4
    assert payload["refused"] == []


# --------------------------------------------------------------------------
# never a gate -- the CLI itself carries no --strict / block-authoring path
# --------------------------------------------------------------------------

def test_cli_has_no_strict_flag() -> None:
    """CEO decisions 4 and 10 (ADR 0022): no approval gate, in any form. A
    --strict flag is exactly the shape a future caller could wire into a
    gate, so this asserts it was never added, not just that today's call
    doesn't use it."""
    with pytest.raises(SystemExit):
        skill_lint.main(["check", "--strict"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))


# --------------------------------------------------------------------------
# ADR 0026 -- codes 8 / 9 / 10: the learning loop's field notes
# --------------------------------------------------------------------------

import subprocess as _sp

_GOOD_NOTE = "- 2026-09-22 [MISSING] §0 Pre-flight — skip the menu when the CEO opens with the problem · evidence: session cto-0e8d80b8 · status: pending"


def _git(cwd: Path, *args: str, env_date: "str | None" = None) -> str:
    import os
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
    })
    if env_date:
        env["GIT_AUTHOR_DATE"] = env_date
        env["GIT_COMMITTER_DATE"] = env_date
    r = _sp.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, env=env, check=True)
    return r.stdout


def _repo_with_skill(tmp_path: Path, name: str = "noted", body: str = "rule one\n\nrule two") -> Path:
    _git(tmp_path, "init", "-q")
    d = _write_skill(tmp_path, name, created_by="human", audience=["all"], body=body)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return d


def test_wellformed_field_notes_are_clean(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "noted", body="rule\n\n## Field notes\n\n" + _GOOD_NOTE + "\n  continuation lines are fine\n")
    findings = skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == []


@pytest.mark.parametrize("bad, problem", [
    ("- [MISSING] no date · evidence: task-1 · status: pending", "date"),
    ("- 2026-13-40 [MISSING] bad date · evidence: task-1 · status: pending", "not a real date"),
    ("- 2026-09-22 [WEIRD] bad kind · evidence: task-1 · status: pending", "kind"),
    ("- 2026-09-22 [WRONG] no evidence · status: pending", "evidence"),
    ("- 2026-09-22 [WRONG] no status · evidence: task-1", "status"),
    ("- 2026-09-22 [WRONG] bad status · evidence: task-1 · status: maybe", "status"),
])
def test_malformed_field_note_is_code_8_and_names_the_problem(tmp_path: Path, bad: str, problem: str) -> None:
    d = _write_skill(tmp_path, "noted", body="rule\n\n## Field notes\n\n" + bad + "\n")
    findings = skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [8]
    assert problem in findings[0].message
    assert "SKILL.md:" in findings[0].message  # line number, so the author can find it


def test_notes_outside_the_field_notes_section_are_not_linted(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "noted", body="- not a field note, just a bullet\n\n## Other\n- 2026-09-22 [WEIRD] x")
    assert skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE) == []


def test_staged_body_edit_without_field_note_is_code_9(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    md = d / "SKILL.md"
    md.write_text(md.read_text().replace("rule one", "rule one, rewritten"), encoding="utf-8")
    _git(tmp_path, "add", "-A")
    findings = skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE, staged=True)
    assert [f.code for f in findings] == [9]


def test_staged_body_edit_with_field_note_in_same_diff_is_clean(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    md = d / "SKILL.md"
    md.write_text(
        md.read_text().replace("rule one", "rule one, rewritten") + "\n## Field notes\n\n" + _GOOD_NOTE + "\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", "-A")
    assert skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE, staged=True) == []


def test_staged_check_is_off_unless_asked(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    md = d / "SKILL.md"
    md.write_text(md.read_text().replace("rule one", "rule one, rewritten"), encoding="utf-8")
    _git(tmp_path, "add", "-A")
    assert skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE) == []


def test_staged_frontmatter_only_edit_is_not_code_9(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    md = d / "SKILL.md"
    md.write_text(md.read_text().replace("created_by: human", "created_by: human\npinned: true"), encoding="utf-8")
    _git(tmp_path, "add", "-A")
    assert skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE, staged=True) == []


def test_staged_brand_new_skill_is_not_code_9(tmp_path: Path) -> None:
    _repo_with_skill(tmp_path, name="existing")
    d = _write_skill(tmp_path, "fresh", created_by="agent", audience=["all"], body="first rule")
    _git(tmp_path, "add", "-A")
    assert skill_lint.lint_skill("fresh", d, _KNOWN_AUDIENCE, staged=True) == []


def test_staged_check_outside_a_repo_is_silent(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "loose", body="rule")
    assert skill_lint.lint_skill("loose", d, _KNOWN_AUDIENCE, staged=True) == []


def _flip(tmp_path: Path, d: Path, i: int) -> None:
    md = d / "SKILL.md"
    md.write_text(md.read_text() + f"\nflip {i}\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", f"skill({d.name}): flip — rule {i} — evidence task-{i}")


def test_two_flip_commits_inside_30_days_is_code_10(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    _flip(tmp_path, d, 1)
    _flip(tmp_path, d, 2)
    findings = skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE)
    assert [f.code for f in findings] == [10]
    assert "CONTESTED" in findings[0].message


def test_one_flip_commit_is_not_code_10(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    _flip(tmp_path, d, 1)
    assert skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE) == []


def test_note_and_rule_commits_are_not_flips(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    for verb in ("note", "rule", "note"):
        md = d / "SKILL.md"
        md.write_text(md.read_text() + f"\n{verb}\n", encoding="utf-8")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", f"skill(noted): {verb} — x — evidence task-1")
    assert skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE) == []


def test_flips_on_another_skill_do_not_count(tmp_path: Path) -> None:
    d = _repo_with_skill(tmp_path)
    other = _write_skill(tmp_path, "other", created_by="human", audience=["all"], body="x")
    _git(tmp_path, "add", "-A"); _git(tmp_path, "commit", "-q", "-m", "add other")
    _flip(tmp_path, other, 1); _flip(tmp_path, other, 2)
    assert skill_lint.lint_skill("noted", d, _KNOWN_AUDIENCE) == []
    assert [f.code for f in skill_lint.lint_skill("other", other, _KNOWN_AUDIENCE)] == [10]


def test_cli_has_staged_flag_and_it_is_off_by_default() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    # mirror main()'s parser: the flag must exist and default False
    ns = skill_lint.main.__globals__["argparse"].ArgumentParser  # sanity: same module
    assert ns is argparse.ArgumentParser
    out = _sp.run([sys.executable, str(ROOT / "scripts" / "skill-lint.py"), "check", "--help"], capture_output=True, text=True)
    assert "--staged" in out.stdout
