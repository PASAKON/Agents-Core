# REPORT task-2506e4fd

## Files changed
- `scripts/spawn-worker-remote.sh` — Added `.media-allow` support in `emit_report_commit_push`, exporting `BASE_BRANCH` from `$BASE` and reading `.media-allow` from `origin/$BASE_BRANCH` via `git show`. Added pattern matching using `git ls-files --cached --ignored --exclude-from`, honored ` !large` suffix for > 1 MB binaries, appended kept media to `REPORT.md` and commit body, and enforced `LC_ALL=C` on `awk` size formatting.
- `windows/spawn-worker.ps1` — Added `.media-allow` support in `New-ReportStepBody`, reading `.media-allow` from `origin/$Base`, matching staged files via `git ls-files --cached --ignored --exclude-from`, honoring ` !large` for files > 1 MB, recording kept media in `REPORT.md` and commit body.
- `tests/test_spawn_worker_remote_runners.py` — Added test cases for allowed PNG kept, unallowed PNG reset, allowed > 1 MB reset without ` !large` and kept with it, and `.media-allow` in worktree only being ignored.
- `tests/test_spawn_worker_ps1_runners.py` — Added `test_report_step_media_allow_gate` checking static text and contract in `windows/spawn-worker.ps1`.

## What was done
1. Modified `scripts/spawn-worker-remote.sh` `emit_report_commit_push`:
   - Passes `BASE_BRANCH` from `$BASE`.
   - Reads `.media-allow` from `origin/$BASE_BRANCH:.media-allow` (never from working tree).
   - Parses `.media-allow` lines ignoring comments and blank lines, separating patterns into all-allowed and large-allowed (lines ending with ` !large`).
   - Uses `git ls-files --cached --ignored --exclude-from` to check candidate media/binary files against allow patterns.
   - Resets unallowed media files or allowed files > 1 MB that lack ` !large` and records them under `## Blockers` in `REPORT.md`.
   - Keeps allowed media files, appends `media kept: <file>` to `REPORT.md` and commit body.
2. Modified `windows/spawn-worker.ps1` `New-ReportStepBody`:
   - Mirrors the same `.media-allow` gate for Windows workers, reading from `origin/$Base:.media-allow`.
   - Formats kept media in `REPORT.md` and commits with `media kept:` in the commit body.
3. Added end-to-end tests in `tests/test_spawn_worker_remote_runners.py` and static tests in `tests/test_spawn_worker_ps1_runners.py`.
4. Verified all tests pass across `test_spawn_worker_remote_runners.py`, `test_spawn_worker_ps1_runners.py`, and `test_w06_launcher_report.py`.

## Blockers
- None.

## Summary
Updated Linux (`scripts/spawn-worker-remote.sh`) and Windows (`windows/spawn-worker.ps1`) worker launchers to read an optional `.media-allow` allow-list committed at `origin/<base>:.media-allow`. Staged media files matching allow globs are kept and not reset, the 1 MB binary rule is enforced unless permitted via ` !large`, and kept media files are documented in `REPORT.md` and the report commit body.

## Files Changed
- `scripts/spawn-worker-remote.sh` — `.media-allow` parser, `git ls-files` gate, kept media reporting in REPORT.md and commit body.
- `windows/spawn-worker.ps1` — `.media-allow` parity for Windows worker runner.
- `tests/test_spawn_worker_remote_runners.py` — 4 new test cases for `.media-allow` gate behavior.
- `tests/test_spawn_worker_ps1_runners.py` — static contract test for PowerShell media allow gate.

## Commits
- (Hub commits on developer's behalf per prompt instructions)

## Tests
- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_spawn_worker_remote_runners.py tests/test_spawn_worker_ps1_runners.py`
- passed: 78
- failed: 0
- skipped: 0
- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_w06_launcher_report.py`
- passed: 32
- failed: 0
- skipped: 0

## Issues / Blockers
- None.

## Notes for Reviewer
- `.media-allow` is strictly queried from `origin/<base>:.media-allow` via git show, preventing workers from widening the allow-list during their run.
- Suffix ` !large` allows files > 1 MB while maintaining the 1 MB binary block rule for all other allowed paths.

## Skill learning
- COSTLY  [no owner] : `awk` printf `%.1f` decimal separator depends on system locale (comma vs period) · evidence: task-2506e4fd / `scripts/spawn-worker-remote.sh:561` · prevented by: prefixing awk invocations with `LC_ALL=C awk`
