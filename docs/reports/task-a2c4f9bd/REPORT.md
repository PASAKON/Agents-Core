# REPORT task-a2c4f9bd

First tests for `tools/skill_rename.py`: `tests/test_skill_rename.py`, 46 cases. `pytest` run from the worktree gave **45 passed, 1 xfailed, 0 failed**. The xfail documents a tool bug (see below).

## Files changed
- `tests/test_skill_rename.py` (new)
- `docs/reports/task-a2c4f9bd/REPORT.md` (this file)
- `tools/skill_rename.py`: **not changed**.

## Seam (no refactor needed)
The module has two globals, `ROOT` and `SKILLS`. The `repo` fixture monkeypatches both onto a fake tree in `tmp_path/repo`. The real `.claude/skills` is never touched. `main()` is driven through `sys.argv`.

`--apply` runs a real `git mv`, so the fixture runs `git init` and `git add -A` in the tmp repo. It clears `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE` first. No commit is made, so no git identity is needed.

Fake tree:
- Three skills: `CTO_Film_Production` and `ALL_Style_Guide` are renamed, and `CTO_Film_PromptFormat` stays.
- Live files that mention the old names: `roles/cto.md`, `docs/guide.md`.
- Excluded files that mention the old names:
  - `docs/reports`, `docs/ops`, `docs/research`, `docs/WAVE-1.md` (EXCLUDE_PREFIX)
  - `roles/worktrees/` (EXCLUDE_PARTS)
  - `tests/.launch-task/`
  - `scripts/blob.bin` (suffix not in TEXT_SUFFIX)
  - `notes/outside.md` (not in INCLUDE)
- KEEP_OLD_NAMES files: `docs/org/SKILL-KINDS-2026-09-27.md`, `tools/skill_rename.py`.

## Findings
1. **Latent tool bug** (`patch_frontmatter`, line 99). With a block-style `aka:` list and no `audience:` line, the new `audience:` line is inserted right after `aka:`. That splits the list from its `- item` lines and gives broken YAML. Covered by `test_patch_frontmatter_block_style_aka_without_audience_keeps_list_intact`, marked `xfail(strict=True)`. It goes red as an XPASS once the bug is fixed, which is the cue to remove the marker. I did not fix it, because the brief is tests only.
2. **The brief's sibling example is not a prefix pair.** `CTO_Film_Production` is not a prefix of `CTO_Film_PromptFormat`, so it can never match it. I kept that pair as asked. The real whole-token checks are the look-alikes in `roles/cto.md`: `CTO_Film_Production_v2`, `CTO_Film_ProductionX`, `my-CTO_Film_Production` and `scripts/CTO_Film_Production.py`. These must survive, while `see CTO_Film_Production.` (sentence end) must be rewritten.
3. **A dry run does not list the moves.** It prints only `N skills · F files · M mentions` and the per-file counts. "Lists the right moves" is therefore tested as: the plan size, the exact per-file counts, and that nothing moved on disk.

## Seeded reverts
Each is a one-line change to `tools/skill_rename.py`, with line numbers from the current file. Each test should go red when its revert is applied alone.

| Test | Seeded revert |
|---|---|
| `test_token_re_matches_whole_tokens_only` | L39: change the lookahead to `(?![A-Za-z0-9_\-])`, dropping `\|\.[A-Za-z]`. `scripts/X.py` gets matched. |
| `test_whole_token_only_sibling_name_never_touched` | L39: change the lookahead to `(?![\-]\|\.[A-Za-z])`. `_v2` and `X` look-alikes get rewritten. |
| `test_live_files_walks_include_and_skips_excluded` | L47: change `p.suffix not in TEXT_SUFFIX` to `False`. `scripts/blob.bin` is walked. |
| `test_stub_text_has_redirect_and_30_day_expiry` | L123: `days=30` becomes `days=31`. |
| `test_patch_frontmatter_without_frontmatter_stops` | L66: `if not text.startswith("---"):` becomes `if False:`. `ValueError` replaces `SystemExit`. |
| `test_patch_frontmatter_block_style_aka_gets_new_item_line` | L95: `f"  - {e['old']}"` becomes `f"  - {e['new']}"`. |
| `test_patch_frontmatter_existing_aka_not_duplicated` | L91: `if e["old"] not in items:` becomes `if True:`. |
| `test_patch_frontmatter_plain_description_and_idempotent_prefix` | L117: `elif not head.startswith(prefix):` becomes `elif True:`. The prefix is doubled. |
| `test_dry_run_changes_nothing_on_disk` | L153: `if not a.apply:` becomes `if False:`. The dry run applies. |
| `test_dry_run_reports_plan_size_and_the_right_files` | L150: `sum(changes.values())` becomes `len(changes)` in the print. |
| `test_apply_moves_directories` | L158: `f".claude/skills/{e['new']}"` becomes `f".claude/skills/{e['new']}_"`. |
| `test_apply_git_mv_registers_the_move_in_the_index` | L158–159: replace the `subprocess.run(... git mv ...)` call with `(SKILLS / e["old"]).rename(SKILLS / e["new"])`. The move works but the index is stale. |
| `test_frontmatter_name_patched` | L75: `f"name: {e['new']}"` becomes `f"name: {e['old']}"`. |
| `test_frontmatter_kind_added_and_replaced` | L80: `f"kind: {e['kind']}"` becomes `"kind: knowledge"`. The replace branch (skill 2) goes red. |
| `test_frontmatter_owner_added_and_replaced` | L84: `f"owner: {e['owner']}"` becomes `"owner: ceo"`. |
| `test_frontmatter_aka_records_old_name_and_is_not_rewritten` | L87: `f"aka: [{e['old']}]"` becomes `f"aka: [{e['new']}]"`. |
| `test_frontmatter_audience_gets_new_audiences_first` | L103: change the join to `items + [a for a in add if a not in items]`. |
| `test_frontmatter_description_starts_with_kind_word` | L104: `e["kind"].upper()` becomes `e["kind"].lower()`. |
| `test_frontmatter_field_order_and_body_preserved` | L76: `at = find("name") + 1` becomes `+ 2`. Or L119: `+ body` becomes `+ body.lstrip("\n")`. |
| `test_references_rewritten_in_live_files` | L166: `r.sub(new, t)` becomes `r.sub(new, t, count=1)`. |
| `test_references_rewrite_other_skills_files_too` | L22: remove `".claude/skills"` from INCLUDE. |
| `test_exclude_prefix_and_parts_files_untouched` | L25: remove `"docs/ops"` from EXCLUDE_PREFIX. Or L51: remove `or ".launch-task" in rel`. |
| `test_keep_old_names_files_untouched` | L28: remove `"tools/skill_rename.py"` from KEEP_OLD_NAMES. |
| `test_apply_changes_only_expected_files` | L28: remove `"docs/org/SKILL-KINDS-2026-09-27.md"` from KEEP_OLD_NAMES. |
| `test_stub_left_at_old_name_with_redirect` | L175: `stub(e, today)` becomes `stub(e, today - datetime.timedelta(days=1))`. |
| `test_unknown_kind_is_refused` | L141: delete `or e["kind"] not in KINDS`. |
| `test_name_breaking_the_naming_rule_is_refused` | L141: `not NAME_RE.match(e["new"])` becomes `False`. |
| `test_existing_target_is_refused` | L139: `.exists()` becomes `.is_file()`. |
| `test_missing_old_skill_is_refused` | L137: `if not (...).is_file():` becomes `if False:`. |
| `test_one_bad_entry_refuses_the_whole_plan_before_anything_moves` | L136: `for e in plan:` becomes `for e in plan[:1]:`. |

The repoint-before-patch order (L160–171) is covered by the aka assertions. Swapping the two blocks is a multi-line change, so no seeded revert is listed for it.

Each refusal test runs with and without `--apply`. It asserts a byte-identical tree after the refusal.

## Validation performed
- Ran `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_skill_rename.py -q -p no:cacheprovider` from the worktree. Result: 45 passed, 1 xfailed.
- I did **not** run the seeded reverts. They are for the PH to apply.

## Limitations
- `test_stub_left_at_old_name_with_redirect` compares against `datetime.date.today()`. It could be off by one if the test straddles midnight. The fixed-date stub text is covered separately by `test_stub_text_has_redirect_and_30_day_expiry`.
- The tests need a `git` binary on PATH.
- The task title says "override: CEO order 15 Oct — Argon eval (Q in chat)". I could not see any chat, so I worked only from the written job.

## Blockers
- (none)

## Skill learning
- (none)
