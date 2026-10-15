"""Tests for tools/skill_rename.py.

Everything runs against a tiny fake repo in tmp_path (a real `git init`, because --apply shells out to
`git mv`). The module's seam is its two module globals, ROOT and SKILLS: the fixture monkeypatches both, so the
real `.claude/skills` is never read or written. No refactor of the tool was needed.
"""
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "tools" / "skill_rename.py"
_spec = importlib.util.spec_from_file_location("skill_rename_under_test", _SRC)
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)

OLD1, NEW1 = "CTO_Film_Production", "CTO_Procedure_FilmProduction"
OLD2, NEW2 = "ALL_Style_Guide", "ALL_Standard_StyleGuide"
SIBLING = "CTO_Film_PromptFormat"  # must never be touched by the CTO_Film_Production rename

PLAN = [
    {"old": OLD1, "new": NEW1, "kind": "procedure", "owner": "cto", "audience_add": ["cto"]},
    {"old": OLD2, "new": NEW2, "kind": "standard", "owner": "cmo", "audience_add": ["cmo"]},
]

# path (relative to the fake repo) -> text
SKILL1 = (f"---\nname: {OLD1}\ndescription: >\n  Produce a film shot by shot. See {OLD1} for details.\n---\n\n"
          f"# {OLD1}\n\nSibling: {SIBLING}.\n")
SKILL2 = (f"---\nname: {OLD2}\nkind: knowledge\nowner: coo\naka: [Old_Style]\naudience: [worker, coo]\n"
          f"description: \"House style for copy. Pairs with {OLD1}.\"\n---\n\nBody of the style guide.\n")
SKILL3 = (f"---\nname: {SIBLING}\nkind: knowledge\ndescription: Prompt format. Sibling of {OLD1}.\n---\n\n"
          f"Prompt format body.\n")
CTO_MD = (f"Use {OLD1} and {SIBLING}.\n"
          f"Ends a sentence: see {OLD1}.\n"
          f"Not this: {OLD1}_v2, scripts/{OLD1}.py, my-{OLD1}, {OLD1}X\n"
          f"Style: {OLD2}\n")
GUIDE_MD = f"`{OLD1}` and `{OLD2}`\n"

# Live (INCLUDE) files that must be rewritten
LIVE = {
    f".claude/skills/{OLD1}/SKILL.md": SKILL1,
    f".claude/skills/{OLD1}/refs/extra.md": "Extra file that must move with the directory.\n",
    f".claude/skills/{OLD2}/SKILL.md": SKILL2,
    f".claude/skills/{SIBLING}/SKILL.md": SKILL3,
    "roles/cto.md": CTO_MD,
    "docs/guide.md": GUIDE_MD,
}
# Files that mention the old names and must be left alone, with the reason
EXCLUDED = {
    "docs/reports/old.md": f"report: {OLD1} {OLD2}\n",           # EXCLUDE_PREFIX
    "docs/ops/letter.md": f"letter: {OLD1}\n",                    # EXCLUDE_PREFIX
    "docs/research/r.md": f"research: {OLD1}\n",                  # EXCLUDE_PREFIX
    "docs/WAVE-1.md": f"wave: {OLD1}\n",                          # EXCLUDE_PREFIX (docs/WAVE*)
    "roles/worktrees/x.md": f"worktree copy: {OLD1}\n",           # EXCLUDE_PARTS
    "tests/.launch-task/note.md": f"launch: {OLD1}\n",            # .launch-task
    "scripts/blob.bin": f"binary-ish: {OLD1}\n",                  # suffix not in TEXT_SUFFIX
    "notes/outside.md": f"outside INCLUDE: {OLD1}\n",             # not in INCLUDE
}
KEEP = {
    "docs/org/SKILL-KINDS-2026-09-27.md": f"mapping record: {OLD1} -> {NEW1}\n",   # KEEP_OLD_NAMES
    "tools/skill_rename.py": f"# the tool itself names {OLD1}\n",                  # KEEP_OLD_NAMES
}
# 3 (skill1) + 2 (skill2) + 1 (skill3) + 3 (roles/cto.md) + 2 (docs/guide.md)
EXPECTED_COUNTS = {
    f".claude/skills/{OLD1}/SKILL.md": 3,
    f".claude/skills/{OLD2}/SKILL.md": 2,
    f".claude/skills/{SIBLING}/SKILL.md": 1,
    "roles/cto.md": 3,
    "docs/guide.md": 2,
}


def _write_tree(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.relative_to(root).parts}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    _write_tree(root, {**LIVE, **EXCLUDED, **KEEP})
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    monkeypatch.setattr(sr, "ROOT", root)
    monkeypatch.setattr(sr, "SKILLS", root / ".claude" / "skills")
    return root


def run_main(repo, monkeypatch, plan, *flags):
    plan_file = repo.parent / "PLAN.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["skill_rename.py", str(plan_file), *flags])
    sr.main()


def frontmatter(path):
    """Top-level `key: value` lines of the frontmatter -> dict (first occurrence wins)."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    block = text[4:text.index("\n---", 3)]
    out = {}
    for line in block.split("\n"):
        if re.match(r"^[A-Za-z_-]+:", line):
            k, v = line.split(":", 1)
            out.setdefault(k, v.strip())
    return out


@pytest.fixture
def applied(repo, monkeypatch, capsys):
    before = snapshot(repo)
    run_main(repo, monkeypatch, PLAN, "--apply")
    return repo, before, capsys.readouterr().out


# ---------------------------------------------------------------- helpers: token_re / live_files / stub

@pytest.mark.parametrize("text,expected", [
    (f"x {OLD1} y", 1),
    (f"see {OLD1}.", 1),                    # sentence-ending dot still matches
    (f"`{OLD1}`", 1),
    (f"({OLD1})", 1),
    (f"{OLD1}_v2", 0),                      # longer name with _
    (f"{OLD1}X", 0),                        # longer name with letter
    (f"{OLD1}-b", 0),                       # followed by -
    (f"my-{OLD1}", 0),                      # preceded by -
    (f"pre_{OLD1}", 0),                     # preceded by _
    (f"a.{OLD1}", 0),                       # preceded by .
    (f"scripts/{OLD1}.py", 0),              # a FILE sharing the name
    (SIBLING, 0),                           # the CTO_Film_PromptFormat case from the docstring
])
def test_token_re_matches_whole_tokens_only(text, expected):
    assert len(sr.token_re(OLD1).findall(text)) == expected


def test_live_files_walks_include_and_skips_excluded(repo):
    got = {p.relative_to(repo).as_posix() for p in sr.live_files()}
    assert got == set(LIVE)
    # spell it out: nothing excluded, nothing kept, nothing outside INCLUDE
    for rel in list(EXCLUDED) + list(KEEP):
        assert rel not in got


def test_stub_text_has_redirect_and_30_day_expiry():
    today = datetime.date(2026, 10, 15)
    s = sr.stub(PLAN[0], today)
    assert s.startswith(f"---\nname: {OLD1}\nkind: procedure\n")
    assert f"description: MOVED to {NEW1} on 2026-10-15." in s
    assert "this stub is removed after 2026-11-14." in s       # 30 days later
    assert "disable-model-invocation: true" in s
    assert f"MOVED: this skill is now `{NEW1}` (renamed 2026-10-15" in s
    assert "Remove after 2026-11-14" in s


# ---------------------------------------------------------------- patch_frontmatter, direct

def test_patch_frontmatter_without_frontmatter_stops():
    with pytest.raises(SystemExit, match="no frontmatter"):
        sr.patch_frontmatter("# no frontmatter here\n", PLAN[0])


def test_patch_frontmatter_block_style_aka_gets_new_item_line():
    text = "---\nname: A_B\naka:\n  - Older\naudience: [worker]\ndescription: plain\n---\nbody\n"
    out = sr.patch_frontmatter(text, PLAN[0])
    assert "aka:\n  - CTO_Film_Production\n  - Older\naudience: [cto, worker]\n" in out


@pytest.mark.xfail(strict=True, reason="tool bug: with a block-style aka and NO audience line, the new audience "
                                       "line is inserted right after `aka:`, splitting the list from its items")
def test_patch_frontmatter_block_style_aka_without_audience_keeps_list_intact():
    text = "---\nname: A_B\naka:\n  - Older\ndescription: plain\n---\nbody\n"
    out = sr.patch_frontmatter(text, PLAN[0])
    assert "aka:\n  - CTO_Film_Production\n  - Older\naudience: [cto, worker]\n" in out


def test_patch_frontmatter_existing_aka_not_duplicated():
    text = f"---\nname: A_B\naka: [{OLD1}]\ndescription: plain\n---\nbody\n"
    out = sr.patch_frontmatter(text, PLAN[0])
    assert f"aka: [{OLD1}]\n" in out


def test_patch_frontmatter_plain_description_and_idempotent_prefix():
    text = "---\nname: A_B\ndescription: plain words\n---\nbody\n"
    out = sr.patch_frontmatter(text, PLAN[0])
    assert "description: PROCEDURE — plain words\n" in out
    again = sr.patch_frontmatter(out, PLAN[0])
    assert again.count("PROCEDURE — ") == 1


# ---------------------------------------------------------------- dry run

def test_dry_run_changes_nothing_on_disk(repo, monkeypatch, capsys):
    before = snapshot(repo)
    dirs_before = {p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_dir() and ".git" not in p.parts}
    run_main(repo, monkeypatch, PLAN)
    assert snapshot(repo) == before
    dirs_after = {p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_dir() and ".git" not in p.parts}
    assert dirs_after == dirs_before
    assert (repo / ".claude/skills" / OLD1 / "SKILL.md").read_text(encoding="utf-8") == SKILL1
    assert not (repo / ".claude/skills" / NEW1).exists()
    assert not (repo / ".claude/skills" / NEW2).exists()


def test_dry_run_reports_plan_size_and_the_right_files(repo, monkeypatch, capsys):
    run_main(repo, monkeypatch, PLAN)
    out = capsys.readouterr().out
    assert "2 skills · 5 files · 11 mentions to rewrite" in out
    assert "dry run: nothing changed" in out
    assert "applied" not in out
    for rel, n in EXPECTED_COUNTS.items():
        assert re.search(rf"^\s+{n}\s+{re.escape(rel)}$", out, re.M), (rel, n, out)
    # the per-file refs/extra.md has no mention; excluded and kept files are never listed
    for rel in [*EXCLUDED, *KEEP, f".claude/skills/{OLD1}/refs/extra.md"]:
        assert rel not in out


# ---------------------------------------------------------------- --apply

def test_apply_moves_directories(applied):
    repo, _, out = applied
    skills = repo / ".claude" / "skills"
    assert "applied: moved, patched, repointed, stubbed" in out
    assert (skills / NEW1 / "SKILL.md").is_file()
    assert (skills / NEW1 / "refs" / "extra.md").read_text(encoding="utf-8") == LIVE[f".claude/skills/{OLD1}/refs/extra.md"]
    assert (skills / NEW2 / "SKILL.md").is_file()
    # the old name is now only the stub dir: the real content went with the move
    assert sorted(p.name for p in (skills / OLD1).iterdir()) == ["SKILL.md"]
    assert sorted(p.name for p in (skills / OLD2).iterdir()) == ["SKILL.md"]
    # unrelated skill stays where it is
    assert (skills / SIBLING / "SKILL.md").is_file()


def test_apply_git_mv_registers_the_move_in_the_index(applied):
    repo, _, _ = applied
    tracked = subprocess.run(["git", "ls-files"], cwd=repo, check=True, capture_output=True, text=True).stdout.split()
    assert f".claude/skills/{NEW1}/SKILL.md" in tracked
    assert f".claude/skills/{NEW1}/refs/extra.md" in tracked
    assert f".claude/skills/{NEW2}/SKILL.md" in tracked


def test_frontmatter_name_patched(applied):
    repo, _, _ = applied
    skills = repo / ".claude" / "skills"
    assert frontmatter(skills / NEW1 / "SKILL.md")["name"] == NEW1
    assert frontmatter(skills / NEW2 / "SKILL.md")["name"] == NEW2


def test_frontmatter_kind_added_and_replaced(applied):
    repo, _, _ = applied
    skills = repo / ".claude" / "skills"
    assert frontmatter(skills / NEW1 / "SKILL.md")["kind"] == "procedure"     # was missing: inserted
    assert frontmatter(skills / NEW2 / "SKILL.md")["kind"] == "standard"      # was "knowledge": replaced


def test_frontmatter_owner_added_and_replaced(applied):
    repo, _, _ = applied
    skills = repo / ".claude" / "skills"
    assert frontmatter(skills / NEW1 / "SKILL.md")["owner"] == "cto"          # was missing
    assert frontmatter(skills / NEW2 / "SKILL.md")["owner"] == "cmo"          # was "coo"


def test_frontmatter_aka_records_old_name_and_is_not_rewritten(applied):
    repo, _, _ = applied
    skills = repo / ".claude" / "skills"
    assert frontmatter(skills / NEW1 / "SKILL.md")["aka"] == f"[{OLD1}]"
    assert frontmatter(skills / NEW2 / "SKILL.md")["aka"] == f"[Old_Style, {OLD2}]"


def test_frontmatter_audience_gets_new_audiences_first(applied):
    repo, _, _ = applied
    skills = repo / ".claude" / "skills"
    assert frontmatter(skills / NEW1 / "SKILL.md")["audience"] == "[cto, worker]"   # was missing
    assert frontmatter(skills / NEW2 / "SKILL.md")["audience"] == "[cmo, worker, coo]"


def test_frontmatter_description_starts_with_kind_word(applied):
    repo, _, _ = applied
    skills = repo / ".claude" / "skills"
    text1 = (skills / NEW1 / "SKILL.md").read_text(encoding="utf-8")
    assert "description: >\n  PROCEDURE — Produce a film shot by shot." in text1       # folded scalar
    assert frontmatter(skills / NEW2 / "SKILL.md")["description"].startswith('"STANDARD — House style')  # quoted


def test_frontmatter_field_order_and_body_preserved(applied):
    repo, _, _ = applied
    text = (repo / ".claude/skills" / NEW1 / "SKILL.md").read_text(encoding="utf-8")
    assert text == (f"---\nname: {NEW1}\nkind: procedure\nowner: cto\naka: [{OLD1}]\naudience: [cto, worker]\n"
                    f"description: >\n  PROCEDURE — Produce a film shot by shot. See {NEW1} for details.\n---\n\n"
                    f"# {NEW1}\n\nSibling: {SIBLING}.\n")


def test_references_rewritten_in_live_files(applied):
    repo, _, _ = applied
    assert (repo / "roles/cto.md").read_text(encoding="utf-8") == (
        f"Use {NEW1} and {SIBLING}.\n"
        f"Ends a sentence: see {NEW1}.\n"
        f"Not this: {OLD1}_v2, scripts/{OLD1}.py, my-{OLD1}, {OLD1}X\n"
        f"Style: {NEW2}\n")
    assert (repo / "docs/guide.md").read_text(encoding="utf-8") == f"`{NEW1}` and `{NEW2}`\n"


def test_references_rewrite_other_skills_files_too(applied):
    repo, _, _ = applied
    sib = (repo / ".claude/skills" / SIBLING / "SKILL.md").read_text(encoding="utf-8")
    assert sib == SKILL3.replace(OLD1, NEW1)
    assert (repo / ".claude/skills" / NEW2 / "SKILL.md").read_text(encoding="utf-8").count(NEW1) == 1


def test_whole_token_only_sibling_name_never_touched(applied):
    repo, _, _ = applied
    cto = (repo / "roles/cto.md").read_text(encoding="utf-8")
    assert cto.count(SIBLING) == 1
    assert "CTO_Procedure_FilmPromptFormat" not in cto
    assert not (repo / ".claude/skills" / "CTO_Procedure_FilmPromptFormat").exists()
    assert frontmatter(repo / ".claude/skills" / SIBLING / "SKILL.md")["name"] == SIBLING
    # the longer / adjacent look-alikes survived as well
    assert f"{OLD1}_v2" in cto and f"scripts/{OLD1}.py" in cto and f"my-{OLD1}" in cto and f"{OLD1}X" in cto


def test_exclude_prefix_and_parts_files_untouched(applied):
    repo, before, _ = applied
    after = snapshot(repo)
    for rel, text in EXCLUDED.items():
        assert after[rel] == text.encode("utf-8"), rel


def test_keep_old_names_files_untouched(applied):
    repo, before, _ = applied
    after = snapshot(repo)
    for rel, text in KEEP.items():
        assert after[rel] == text.encode("utf-8"), rel


def test_stub_left_at_old_name_with_redirect(applied):
    repo, _, _ = applied
    today = datetime.date.today()
    until = today + datetime.timedelta(days=30)
    for old, new, kind in ((OLD1, NEW1, "procedure"), (OLD2, NEW2, "standard")):
        text = (repo / ".claude/skills" / old / "SKILL.md").read_text(encoding="utf-8")
        assert text == sr.stub({"old": old, "new": new, "kind": kind}, today)
        fm = frontmatter(repo / ".claude/skills" / old / "SKILL.md")
        assert fm["name"] == old
        assert fm["description"].startswith(f"MOVED to {new} on {today}")
        assert f"removed after {until}" in text
        assert fm["disable-model-invocation"] == "true"
        assert f"`{new}`" in text


def test_apply_changes_only_expected_files(applied):
    repo, before, _ = applied
    after = snapshot(repo)
    # everything outside the skills tree that did not hold a live reference is byte-identical
    for rel in [*EXCLUDED, *KEEP]:
        assert after[rel] == before[rel]
    changed = {rel for rel in before if rel in after and after[rel] != before[rel]
               and not rel.startswith(".claude/skills/")}
    assert changed == {"roles/cto.md", "docs/guide.md"}


# ---------------------------------------------------------------- refused PLAN entries

def _assert_refused(repo, monkeypatch, plan, message, *flags):
    before = snapshot(repo)
    with pytest.raises(SystemExit) as ei:
        run_main(repo, monkeypatch, plan, *flags)
    assert message in str(ei.value)
    assert snapshot(repo) == before                      # nothing moved, patched or stubbed
    assert (repo / ".claude/skills" / OLD1 / "SKILL.md").read_text(encoding="utf-8") == SKILL1


@pytest.mark.parametrize("flags", [(), ("--apply",)])
def test_unknown_kind_is_refused(repo, monkeypatch, flags):
    plan = [{**PLAN[0], "kind": "bogus"}]
    _assert_refused(repo, monkeypatch, plan, "breaks the naming rule", *flags)


@pytest.mark.parametrize("flags", [(), ("--apply",)])
def test_existing_target_is_refused(repo, monkeypatch, flags):
    (repo / ".claude/skills" / NEW1).mkdir()
    _assert_refused(repo, monkeypatch, [PLAN[0]], f"{NEW1} already exists", *flags)


@pytest.mark.parametrize("flags", [(), ("--apply",)])
def test_name_breaking_the_naming_rule_is_refused(repo, monkeypatch, flags):
    plan = [{**PLAN[0], "new": "CTO_Film_Production2"}]         # no <Kind> segment
    _assert_refused(repo, monkeypatch, plan, "breaks the naming rule", *flags)


@pytest.mark.parametrize("flags", [(), ("--apply",)])
def test_missing_old_skill_is_refused(repo, monkeypatch, flags):
    plan = [{**PLAN[0], "old": "CTO_Does_NotExist"}]
    _assert_refused(repo, monkeypatch, plan, "CTO_Does_NotExist not found", *flags)


def test_one_bad_entry_refuses_the_whole_plan_before_anything_moves(repo, monkeypatch):
    plan = [PLAN[0], {**PLAN[1], "kind": "bogus"}]               # good entry first, bad one second
    _assert_refused(repo, monkeypatch, plan, "breaks the naming rule", "--apply")
    assert (repo / ".claude/skills" / OLD1 / "SKILL.md").read_text(encoding="utf-8") == SKILL1
