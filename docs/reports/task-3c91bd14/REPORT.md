# REPORT task-3c91bd14

## Summary & Seam Analysis
Added the first pytest suite for `tools/skill_rename.py` in `tests/test_skill_rename.py`.

- **Seam used (no refactor needed):** `tools/skill_rename.py` resolves `ROOT` and `SKILLS` from module globals at call time (`live_files()` and `main()`), and `main()` parses `sys.argv` via `argparse.ArgumentParser().parse_args()`. The test fixture `_build_fake_repo` creates an isolated fake repository tree inside `tmp_path / "repo"` (with a local throwaway `git init` so `git -C str(ROOT) mv` operates solely inside `tmp_path`), and points the module at it via `monkeypatch.setattr(skill_rename, "ROOT", repo)` and `monkeypatch.setattr(skill_rename, "SKILLS", repo / ".claude" / "skills")`. `tools/skill_rename.py` did not need to be modified.
- **Fixture coverage:** 3 skills in `tmp_path` (`CTO_Film_Production`, `skill-curator`, and neighbor `CTO_Film_PromptFormat`), live referencing files across `INCLUDE` (`roles/cmo.md`, `CLAUDE.md`, `docs/design/film-guide.md`), historical files under `EXCLUDE_PREFIX` (`docs/reports/2026-09-27-report.md`, `docs/ops/migration.md`), and protected files in `KEEP_OLD_NAMES` (`docs/org/SKILL-KINDS-2026-09-27.md`, `scripts/skill-curator.py`).

## Files Changed
- `tests/test_skill_rename.py` (new, 7 tests covering dry run, `--apply` directory move + frontmatter patching, whole-token reference rewrites, `EXCLUDE_PREFIX` / `KEEP_OLD_NAMES` preservation, 30-day redirect stubs, and bad `PLAN` entry refusals)
- `REPORT.md` (new, task report at worktree root)
- `docs/reports/task-3c91bd14/REPORT.md` (new, task report per worker contract)

## Seeded Reverts (One-Line Changes in `tools/skill_rename.py` Per Test)

1. **`test_dry_run_changes_nothing_and_lists_moves`**
   - **Line 153** of `tools/skill_rename.py`:
     - Original: `    if not a.apply:`
     - Seeded revert: `    if False:`
   - **Why it goes red:** Dry run fails to return early before applying renames, mutating the fake repo on disk (`after == before` fails) and omitting `"dry run: nothing changed"` from stdout.

2. **`test_apply_moves_dir_and_patches_frontmatter`**
   - **Line 171** of `tools/skill_rename.py`:
     - Original: `        f.write_text(patch_frontmatter(f.read_text(encoding="utf-8"), e), encoding="utf-8")`
     - Seeded revert: `        pass`
   - **Why it goes red:** The moved `SKILL.md` files never have `kind`, `owner`, `aka`, `audience`, or the uppercase `<KIND> — ` description prefix patched into their frontmatter.

3. **`test_apply_rewrites_whole_tokens_only`**
   - **Line 39** of `tools/skill_rename.py`:
     - Original: `    return re.compile(r"(?<![A-Za-z0-9_.\-])" + re.escape(name) + r"(?![A-Za-z0-9_\-]|\.[A-Za-z])")`
     - Seeded revert: `    return re.compile(re.escape(name))`
   - **Why it goes red:** Without whole-token boundaries and the `|\.[A-Za-z]` negative lookahead, `CTO_Film_Production_Extra`, `Pre_CTO_Film_Production`, and `scripts/skill-curator.py` are corrupted by substring replacement.

4. **`test_apply_leaves_excluded_and_keep_old_names_untouched`**
   - **Line 25** of `tools/skill_rename.py`:
     - Original: `EXCLUDE_PREFIX = ("docs/reports", "docs/ops", "docs/research", "docs/WAVE")  # docs/WAVE*: governance history`
     - Seeded revert: `EXCLUDE_PREFIX = ()`
   - **Why it goes red:** `live_files()` walks `docs/reports/2026-09-27-report.md` and `docs/ops/migration.md` and rewrites their historical `CTO_Film_Production` / `skill-curator` mentions.

5. **`test_apply_writes_30_day_redirect_stub_at_old_name`**
   - **Line 123** of `tools/skill_rename.py`:
     - Original: `    until = (today + datetime.timedelta(days=30)).isoformat()`
     - Seeded revert: `    until = (today + datetime.timedelta(days=7)).isoformat()`
   - **Why it goes red:** The redirect stub written at `.claude/skills/<old>/SKILL.md` carries a 7-day removal date instead of the required 30-day removal date.

6. **`test_refuses_bad_plan_unknown_kind`**
   - **Line 141** of `tools/skill_rename.py`:
     - Original: `        if not NAME_RE.match(e["new"]) or e["kind"] not in KINDS:`
     - Seeded revert: `        if not NAME_RE.match(e["new"]):`
   - **Why it goes red:** `main()` no longer validates `e["kind"]` against `KINDS`, failing `pytest.raises(SystemExit, match="breaks the naming rule")` when `new` is a syntactically valid name (`CMO_Knowledge_Film_Production`) paired with `"kind": "unknown_kind"`.

7. **`test_refuses_bad_plan_target_exists_or_missing_source`**
   - **Line 139** of `tools/skill_rename.py`:
     - Original: `        if (SKILLS / e["new"]).exists():`
     - Seeded revert: `        if False:`
   - **Why it goes red:** `main()` fails to raise `SystemExit("STOP: CTO_Film_PromptFormat already exists")` when the target directory already exists under `.claude/skills`.

## Validation Performed & Limitations
- **Shell / pytest limitation:** Running as an AGY headless worker under the Remote Worker Contract (`For AGY, use file tools only; leave shell validation to the review process; Any tool call that needs approval is auto-denied`). Therefore, pytest was not executed via shell tool call.
- **Static verification:** Manually traced all 7 tests, regex boundaries, mention counts (`2 skills · 5 files · 13 mentions to rewrite`), frontmatter transformations, and git fixture commands against `tools/skill_rename.py` lines 1–181.
- **Command for reviewer / PH validation:**
  ```bash
  /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_skill_rename.py
  ```

## Blockers
- (none)

## Skill learning
- (none)
