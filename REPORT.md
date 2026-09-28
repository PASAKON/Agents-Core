# REPORT task-e0b85ae6

## Summary
Fixed both hub cutover scripts so a live SQLite ledger can no longer lose rows on
migration: both now checkpoint the WAL (`PRAGMA wal_checkpoint(TRUNCATE)`, retried
on busy) and move `tasks.db` + `-wal` + `-shm` together via a new shared
`scripts/hub/wal-checkpoint-archive.sh`, and both verify per-table SQLite-vs-Postgres
row counts before archiving via a new shared `scripts/hub/verify_migration_counts.py`
(cutover-mac.sh already had an inline version of this; contabo-cutover.sh had none).
`contabo-cutover.sh`'s dirty-tree check now ignores only tracked
`state/machine-discovered-*.yaml` (the weekly machine_doctor cron rewrite that made
it refuse unconditionally), and its `git checkout -B main origin/main` (which
force-resets main, discarding unpushed local commits) is replaced with
`git checkout main` + `git merge --ff-only origin/main`, refusing with a clear
message when that isn't possible. To make the git-sync logic testable without ssh
or a real Contabo box, I split it out of `contabo-cutover.sh`'s inline ssh heredoc
into a new `scripts/hub/contabo-cutover-remote.sh` (ROOT/ENVF overridable via env
vars for tests, defaulting to the real Contabo paths in production);
`contabo-cutover.sh` is now a thin ssh transport that pipes that file's content to
`bash -s` on the target host, same mechanism as before.

## Files Changed
- `scripts/hub/wal-checkpoint-archive.sh` (new) — checkpoint + retry-on-busy +
  refuse, then move `<db>`/`<db>-wal`/`<db>-shm` (whichever exist) to an archive
  path. Shared by both cutover scripts; directly testable standalone.
- `scripts/hub/verify_migration_counts.py` (new) — per-table SQLite-vs-Postgres
  row-count comparison (`tasks`, `c_level_sessions`, `events`, `locks`, matching
  `scripts/migrate_tasks_db.py`'s `TABLES`); exits 1 and prints both count sets on
  any mismatch. Shared by both cutover scripts.
- `scripts/hub/contabo-cutover-remote.sh` (new) — the Contabo-side steps 1-7,
  extracted out of `contabo-cutover.sh`'s old inline ssh heredoc. Fixes the dirty-
  tree check (ignore only `state/machine-discovered-*.yaml`) and the git sync
  (`checkout -B` → `checkout` + `merge --ff-only`, clear refusal message). Uses the
  two new shared scripts for its own archive step. `ROOT`/`ENVF` env vars override
  the real Contabo defaults (test-only hook; production is unaffected since nothing
  sets them today).
- `scripts/hub/contabo-cutover.sh` — now a thin ssh wrapper: pipes
  `contabo-cutover-remote.sh`'s content to `bash -s` on `$HOST_ALIAS`. Top comment
  block rewritten to describe the new step 2 (ff-only) and step 5-6 (verify then
  checkpoint+archive) behaviour, and the rollback note now covers restoring
  `-wal`/`-shm` too.
- `scripts/hub/cutover-mac.sh` — step 3's inline count-check heredoc replaced with
  a call to `scripts/hub/verify_migration_counts.py`; step 5's bare
  `mv state/tasks.db "$ARCHIVE_PATH"` replaced with a call to
  `scripts/hub/wal-checkpoint-archive.sh`; dry-run messages and the final summary's
  rollback note updated to match. Every existing safety check (step 1 liveness gate,
  step 2 watchdog freeze/restore trap, the `--apply`/dry-run default, the tombstone
  directory) is unchanged.
- `tests/test_hub_cutover_scripts.py` (new) — see Tests below. No existing test of
  either script was found (grepped `tests/` and `scripts/` for `cutover-mac` /
  `contabo-cutover` before writing this), so this is a new file, not an extension.

## Commits
- `951d1ba5` — hub: checkpoint WAL + ff-only cutover (Org Mesh W1.1, task-e0b85ae6)
- `d96fe467` — tests: cover the hub cutover WAL-checkpoint + ff-only fixes (task-e0b85ae6)

## Tests
- ran: `.venv/bin/python -m pytest -p no:warnings tests/test_hub_cutover_scripts.py`
- passed: 27
- failed: 0
- skipped: 0

- ran: `.venv/bin/python -m pytest -p no:warnings` (full suite, Linux/Contabo, 465s)
- passed: 2790
- failed: 1 — `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`.
  Pre-existing and unrelated: it compares this worktree's `~/.claude/plugins/installed_plugins.json`
  (machine-local plugin install state, not part of this repo or this task's touches) against a
  checked-in baseline, and fails on any machine whose installed-plugins file doesn't list every
  baseline plugin. Not caused by anything in this diff (only `scripts/hub/*` and
  `tests/test_hub_cutover_scripts.py` were touched) and not present in `tests/test_hub_cutover_scripts.py`
  itself.
- skipped: 20 (pre-existing skips, e.g. Postgres-backed tests without `ORG_TEST_DB_URL` set — no
  local Postgres on this box)

Per the brief's rule: never ran either cutover script against a real ledger, the real Contabo box,
or a real Postgres. `wal-checkpoint-archive.sh` and `contabo-cutover-remote.sh` were run directly
against throwaway `tmp_path` dirs / git repos (the latter's `ROOT`/`ENVF` env-var overrides exist
specifically for this). `cutover-mac.sh` itself was never executed (it resolves ROOT from
`BASH_SOURCE`, so running the real file always touches the real repo checkout regardless of env
vars) — its fixes are proven by testing the two pieces it now calls in isolation plus structural
source assertions (call ordering, no bare `mv state/tasks.db`, no `checkout -B`, `set -e` intact).
`verify_migration_counts.py`'s mismatch logic is tested at the function level (monkeypatched I/O
boundary, same technique `scripts/hub/test_cutover_gate.py` already uses) since no Postgres is
reachable in this sandbox; its `sqlite_counts()` is exercised for real against a temp WAL-mode db.

## Issues / Blockers
- None for this task's scope. The one full-suite failure above is a pre-existing machine-state
  issue unrelated to these changes.

## Notes for Reviewer
- `docs/design/tasks-db-hub.md` §3.3 step 5 still says `mv state/tasks.db state/tasks.db.archived-...`
  (the old, now-superseded single-file move) — I left it alone since that file may also be touched
  by the W1.2/W1.3 waves this task said not to own; worth a follow-up line update once those land.
- `contabo-cutover.sh`'s remote body is now a real file (`contabo-cutover-remote.sh`) instead of an
  inline `<<'REMOTE'` heredoc. Behaviourally identical over ssh (still `FLAG='...' bash -s` piped
  the script's content as stdin) — this was necessary to make the dirty-tree-check and ff-only-merge
  fixes testable without touching the real box, and it's also just easier to read/maintain/shellcheck
  as a standalone file. Flagging since it's a structural change beyond a line-level diff.
- `verify_migration_counts.py`'s `TABLES` tuple is hand-kept in sync with
  `scripts/migrate_tasks_db.py`'s `TABLES` dict (not imported from it) since the latter also carries
  primary-key columns this script has no use for, and importing across module boundaries just for a
  tuple of 4 strings felt like more coupling than the 4-line duplication it avoids. If W1.2/W1.3
  changes `migrate_tasks_db.py`'s table list, this needs a matching edit.
- I did not touch `scripts/migrate_tasks_db.py`, `lib/db*.py`, or anything outside
  `scripts/hub/` + the new test file, per the brief.

## Skill learning
- MISSING [no owner] : no skill covers "how to safely test a bash script whose ROOT self-locates
  via BASH_SOURCE and therefore can't be sandboxed by env vars alone" — I had to work this out from
  first principles (empirically verifying SQLite WAL-checkpoint semantics with throwaway scripts,
  then choosing which pieces to extract into independently-testable files vs. prove via structural
  source assertions). A short note in a testing-conventions or shell-scripting skill on "self-locating
  ROOT via BASH_SOURCE makes a script untestable without copying the tree or adding an env-var
  override" would have saved time. Evidence: task-e0b85ae6, scripts/hub/cutover-mac.sh's
  `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"` line 16 (left unchanged, deliberately,
  to avoid widening this task's diff).
- COSTLY [no owner] : the full `pytest` run on this Contabo box took 465s (7m45s) for ~2811 tests —
  reasonable in absolute terms, but there's no fast "just the changed area + a smoke pass" tier
  documented anywhere I could find, so I ran the full suite exactly as the brief asked with no way to
  shortcut it. Evidence: task-e0b85ae6, this session's full-suite run.
- (none) beyond the two notes above.
