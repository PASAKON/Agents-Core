# task-3a803be1 — standing worktree reap (gc_stale_tasks --reap, systemd timer, tests, skill paragraph)

Result lines (as the brief requires):

- **new tests PASS on branch**: `python -m pytest scripts/test_gc_worktree_reap.py scripts/test_gc_stale_tasks.py` → 53 passed, 0 failed, 0 skipped (`test_gc_stale_tasks.py` is script-style and collects 0 tests under pytest; run directly it prints `ALL PASS`).
- **fault tests FAIL on base 43d1777b**: the same test file run against the unchanged `tools/gc_stale_tasks.py` from 43d1777b → 38 failed, 15 passed. The two fault tests fail there:
  `test_runner_only_untracked_files_count_as_clean` (fault 1) and `test_merged_review_row_qualifies` (fault 2). Also failing on base: `test_unmerged_review_row_is_flag_only`, `test_commit_on_no_remote_blocks`, `test_live_cwd_blocks_and_releases`, `test_path_mismatch_blocks`, `test_row_path_clean_but_computed_path_holds_unpushed_work`, `test_worktree_of_another_repo_blocks`, `test_symlinked_worktree_path_blocks`, the two second-look tests, `test_origin_is_fetched_once_per_run`, `test_failed_fetch_turns_ancestry_off_…`, `test_cwd_scan_reads_a_proc_tree_and_fails_closed`, `test_runner_file_that_is_a_symlink_is_not_followed`, `test_runner_file_hash_covers_at_most_one_mb`, `test_dry_run_default_removes_nothing` (no per-worktree lines on base), `test_main_prints_df_before_and_after`, all 8 `test_foreign_untracked_file_blocks_removal` cases and all 12 `test_is_runner_file` cases (no such function on base).
  Passing on base (so behaviour kept): the 4 `test_live_statuses_…` and `test_in_progress_with_head_equal_…` cases, `test_terminal_clean_worktree_removed`, `test_terminal_dirty_worktree_skipped`, `test_review_stale_unmerged_…`, `test_review_fresh_unmerged_…`, `test_merged_status_removed_then_idempotent`, `test_folder_with_no_task_row_is_never_touched`, `test_tracked_change_to_a_runner_named_file_blocks`, `test_runner_file_below_a_symlinked_directory_…`. The two installer tests pass on base only because the base scratch copy was given the new installer and units.

SKILL-OVERRIDE: none.

## Summary
`tools/gc_stale_tasks.py --reap` now removes a finished worktree when every provable condition holds (terminal row, or `review` with HEAD already in `origin/<base>`; clean apart from the runner's own untracked files; no commit on no remote; no process cwd inside; row path is the one `worktree_path()` computes; a second look right before removal agrees), prints one line per worktree plus `df` before and after, and never touches a folder with no task row. `org-worktree-reap.service/.timer` run it as root every 6 h through `with-org-db-env.sh`, `scripts/install-org-worktree-reap.sh` installs them (not run), the reap tests were rewritten on real linked worktrees with a bare origin, and `contabo.md` names the op and marks the red-card step `[SUPERSEDED 2026-10-27]`.

## Files Changed
- tools/gc_stale_tasks.py — reap mode only (stale-task sweep, `_reclaim_worktree` and `_worktree_git_status` untouched). New: runner-file rule + hash lines, `_status_entries` (`status --porcelain=v1 -z --untracked-files=all`), `_cwd_holders` (/proc/*/cwd), `_verified_path`, `_repo_problem`, `_inspect_worktree`, `_fetch_origin` (once per repo per run), `_head_is_merged`, `_removal_check`/`_reap_one` (re-check before removing), rewritten `reap_worktrees` and `_print_reap_report`, `df` before/after in `main()`.
- deploy/systemd/org-worktree-reap.service — new; root, oneshot, `with-org-db-env.sh … gc_stale_tasks.py --reap --go`, Nice/IO idle/MemoryMax 1G/30 min timeout.
- deploy/systemd/org-worktree-reap.timer — new; `OnCalendar=*-*-* 00/6:30:00 Asia/Bangkok`, Persistent.
- scripts/install-org-worktree-reap.sh — new; idempotent install / uninstall / status; fills `@ROOT@`; refuses a checkout under `worktrees/`; as root requires the code it will run to be root-owned and not group/world writable.
- scripts/test_gc_worktree_reap.py — rewritten pytest-native (it had no `test_*` functions, so pytest collected 0). 53 tests; the 7 original scenarios kept.
- .claude/skills/ALL_Rules_DiskHygiene/references/contabo.md — one new paragraph; the "ONE red Run card" step marked `[SUPERSEDED 2026-10-27]` with its text and evidence kept.
- docs/reports/task-3a803be1/REPORT.md — this file.

## Commits
- 88bc43a1 — deploy: org-worktree-reap service + timer + installer
- 7d623571 — tools: gc_stale_tasks --reap removes what is provably dead, no card
- 75add371 — skill(ALL_Rules_DiskHygiene): contabo.md names the standing worktree reap, supersedes the red-card step
- (the commit holding this report follows; `git log` has its sha)

## Tests
- ran: `python -m pytest scripts/test_gc_worktree_reap.py scripts/test_gc_stale_tasks.py -p no:cacheprovider`
- passed: 53
- failed: 0
- skipped: 0
- ran: `python scripts/test_gc_stale_tasks.py` (script-style) → `ALL PASS`
- ran: full suite `python -m pytest -p no:cacheprovider` on the branch (47 min) → 12017 passed, 60 failed, 624 skipped, 1 xfailed. Gate on the fail-set vs base: I ran the 15 files holding those 60 failures on a copy of 43d1777b (docs/reports, docs/prompts, knowledge, prototypes, output, docs/promo left out to save disk; that omission made `tests/test_tool_value.py` error on 19 other tests there, which I ignore). 59 of the 60 fail identically on base (`test_dev_tab_color` 5, `test_revert_task` 6, `test_session_reconcile` 8, `test_session_status` 9, `test_skill_visibility` 1, `test_coo_gate` 1, `test_email_ceo` 13, `test_h3_runner_model_launch` 1, `test_keyfetch_capture` 1, `test_ledger_direct_opens` 1, `test_pc_lease_ceo_hold` 4, `test_ph_on_mac` 1, `test_tool_value` 1, `test_w43_join_scripts` 7), none of them imports `gc_stale_tasks`. The 60th, `tests/test_w46b_node_fixes.py::test_echo_is_restored_on_interrupt_too`, is a pty test with a 15 s finish timeout; it timed out while the suite and my other runs shared the box and passes alone 3 of 3 on the branch and 2 of 2 on base. So the branch's fail-set is a subset of main's, plus one load flake.
- ran on base 43d1777b (unchanged tool + the new test file, in a scratch copy): 38 failed, 15 passed — see the result lines above.
- `systemd-analyze verify` on the substituted units: rc 0. `systemd-analyze calendar` fires 00:30, 06:30, 12:30, 18:30 Bangkok. `bash -n` on the installer: ok. The installer ran against a fake root and a stub `systemctl` (idempotent twice, units filled in, refusal under `worktrees/`, uninstall).

## Issues / Blockers
- The org MCP server (`mcp__org__submit_report`, `wiki_read`) did not connect this session (CONNECT_TIMEOUT), so this report was not submitted through it; the row needs moving to `review` from the CTO side. The wiki was read from disk.
- The brief's fallback says "commit and push" at the deadline; I did not push, because the standing rule is never `git push`. Nothing was left over, so the case did not arise.

## Notes for Reviewer
**What the change reaches** (checked with grep, before the first edit):
- `reap_worktrees()` is called only from `main()` under `--reap`; its return keys are unchanged (`removed`, `skipped`, `flagged_review`) plus a new `kept_review`. `runners/watchdog.py:57` and `scripts/test_spawned_at_clock.py` import only `gc_stale_tasks()` (the sweep), which is untouched.
- Tests: `scripts/test_gc_worktree_reap.py` (rewritten), `scripts/test_gc_stale_tasks.py` (sweep, unchanged, passes).
- Fixtures/config/exports: the unit reads `ORG_ROOT`; `tools.worktree.worktree_path/branch_name/remove_worktree/WORKTREE_DIR/get_project/project_path_for_host` and `lib.db.set_fields` are used, not changed. Tests monkeypatch those on the `tools.worktree` module.
- Text that still says "red Run card" for this class: `ALL_Rules_DiskHygiene/SKILL.md` §What will block you and the 2026-10-14/22/26 field notes (the skill owner folds those; I only edited `contabo.md`).

**Where to look first**
1. `_removal_check` / `_reap_one`: the order is path check → repo check → inspect → (dry run stops here) → inspect again and compare snapshot → `remove_worktree(..., delete_branch=False)`. `remove_worktree` deletes the path it computes, not the row's, so the path check is the one that stops a mis-pointed row; `test_row_path_clean_but_computed_path_holds_unpushed_work` covers that.
2. Terminal rows get `worktree=NULL` after removal; `review` rows keep the column (a reopen restores into that path via `restore_worktree`).
3. `_repo_problem`: the worktree's git common dir must be `<repo>/.git`, so `remove_worktree`'s `rmtree` fallback can never be reached. A project whose clone has another layout is skipped with a reason, not guessed at.
4. Runner files are deleted with the worktree; only the name, size and sha256 (first 1 MiB, opened `O_NOFOLLOW|O_NONBLOCK`, `fstat` regular, `dir_fd` walk, CTO_Gate_MergeChecklist §2b) are printed. A symlink named `REPORT.md` is dirty, not followed.
5. `git fetch origin` runs once per project per run, also on a dry run (it updates remote-tracking refs only). If it fails, the ancestry rule is off for that repo (`review` rows are kept), terminal rows still qualify.

**Judgement calls**
- On a host without readable `/proc` (the Mac) `--reap --go` skips everything with a reason, and an unreadable `/proc/<pid>/cwd` (non-root) blocks too (`CWD_UNREADABLE_BLOCKS`; tests relax it for a non-root user). Fail closed, because a process inside a worktree being removed is the case that loses work.
- A `review` row with zero commits ahead counts as merged (its HEAD is an ancestor of `origin/<base>`), as the brief states.
- Gitignored files are not counted as dirty (as before); a worktree full of ignored build output is removed with it.
- Stricter than the brief: unsafe task ids, a symlinked worktree path, and a foreign git dir all skip. None of them changes a case the brief lists.

**Not run on purpose**: the reaper against the live tree (not even a dry run) and the installer, per the brief. The CTO runs the dry run at review and raises the install card after merge. The unit runs code from `/opt/MoonieXHQ/Agents/Core`, which must carry this merge.

## Not checked / risk
- Never run against the live Contabo tree, so counts on real worktrees (how many it removes, MB freed) are unmeasured; the real data may hold a layout the temp repos do not (sparse checkouts, a project clone with a non-`.git` common dir, a `review` row whose project has no `origin`), and those would show up as `skipped` lines, not removals.
- Root runs git in worktrees. Contabo's worktrees are root-owned (checked: `ls -la` shows root:root), so git's ownership check passes; a worktree owned by another account (e.g. a `sompong`-spawned one) would make git refuse ("dubious ownership"), and the reap then skips it as `skipped_unverifiable` — fail closed and loud, never removed. I did not add `safe.directory` on purpose.
- The timer and installer were verified with `systemd-analyze` and a stub `systemctl`, not on a live systemd; whether `with-org-db-env.sh` finds Infisical creds under a timer-started root unit is untested (the unit relies on the same leg the MCP servers use).
- Tests run as root here. As a non-root CI user a foreign process's cwd is unreadable, so the cwd-blocking tests run with that fail-closed switch off; the fail-closed branch itself is covered with a fake `/proc` tree.

## Skill learning
- WRONG   [ALL_Rules_DiskHygiene §What will block you] : "Passed: an in-repo tool with a purposeful name (`gc_stale_tasks.py --reap --go`)" is not stable — the 2026-10-26 note shows the classifier refused even the dry run; with the standing timer the question goes away for finished worktrees, so the line should point at the timer · evidence: task-3a803be1 75add371, skill 2026-10-26 note · fix: replace by "the timer runs it; do not run --reap by hand on Contabo unless the timer is not installed".
- MISSING [ALL_Rules_DiskHygiene §contabo worktrees] : the 2026-10-14/22/26 field notes describe the dirty-by-runner-files fault and the red-card step; both are now handled by the tool and the timer — fold them as superseded · evidence: task-3a803be1 7d623571, 75add371
- COSTLY  [no owner] : `scripts/test_gc_worktree_reap.py` had no `test_*` functions, so pytest (and the CI) collected 0 tests from it for as long as it existed; the script-style `_mark` pattern passes silently under pytest · evidence: `pytest --collect-only scripts/test_gc_worktree_reap.py` at 43d1777b collected nothing · prevented by: a CI check that a `scripts/test_*.py` file collects ≥1 test or declares itself script-style.
