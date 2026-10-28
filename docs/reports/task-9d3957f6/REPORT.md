# REPORT task-9d3957f6

## Result

Implemented DiskSteward P1 part B on existing feature branch `agent/codex-task-9d3957f6`, in the assigned sparse worktree (`core.sparseCheckout=true`). No host archival, removal, scheduler installation, or real Drive operation was performed. Part A's four owned files are unchanged. The launcher owns committing and pushing these changes under the worker contract.

Read the approved Thai plan, especially “ส่งไป Google Drive” and “ระบบระยะยาว” §3, the Drive filing skill, the existing folder map, and P0 script step 4. The P0 preserved task-named tarballs in a local state directory before reaping. The permanent implementation uses `$XDG_STATE_HOME/worktree-reap/<task-id>/runner-<unique>.tgz` (default `~/.local/state`), mode 0600, and logs the path plus full archive SHA-256.

## Files changed

- `tools/drive_leg.py`: `runner-state [--dry-run] [--runner codex|agy|all]`; defaults to seven days; reads part A's `retention_days` and `paths: [{path, action}]`, including `agy-gemini` / `agy-claude`. Also accepts simple path strings and `log_paths`. Archives regular files to the existing family folder ID plus `Runner-State/contabo/<runner>/` (the same machine name the other drive_leg verbs use). One uniquely named tar and per-member path/size/md5 manifest per source root. Replayable disk-backed snapshots, secret-name exclusion, no symlink traversal, verification through `put()`, and source removal through `_delete_verified()` only after every upload succeeds. AGY log removal is deferred until uploads succeed; a log-only invocation probes relay availability without uploading. Quota retries apply independently to mkdir, archive streaming, manifest upload and verification listing: five retries, exponential delay plus jitter, 120-second cap. Other failures do not retry.
- `tools/gc_stale_tasks.py`: tar untracked runner files before removal, preserve checkout on archive failure, and recheck after archival. Add separate review-only `--review-idle` mode, dry by default. Requires idle task timestamps and files, exact current branch/origin HEAD equality, strict cleanliness, existing path/repository/cwd guards and repeated checks. Keeps the branch and review row path for restoration. Reads task rows without initializing/migrating the DB; dry mode uses cached origin refs and never fetches. Acting mode still fetches and fails closed for review on fetch failure.
- `tools/worktree.py`: `restore <task_id>` uses the recorded branch and the same sparse creation helper and layout. Idempotent for the correct checkout; refuses symlink, foreign repo, nested non-worktree path, or wrong branch. Supports the existing `ORG_ROOT` convention for the worktree base when invoking tools from a development worktree.
- `tests/test_drive_leg.py`, `scripts/test_gc_worktree_reap.py`: fake relay tests, quota success/exhaustion, secrets, dry-run, changed sources, relay/md5 failures, AGY log handling, symlinks/recent files, archive-before-removal and archive failure, all three review-idle conditions, and restore round trip/refusal.
- `.claude/skills/CXO_Knowledge_GDrive_FolderMap/SKILL.md`: Runner-State family in both tree and table; no invented child folder ID.
- `docs/ops/machine-contract-drive-leg.md`, `docs/ops/machine-contract-schedules.md`: found weekly transcript cadence in the documented Contabo cron (`30 3 * * 0`); changed to daily (`30 3 * * *`). No transcript scheduler exists under `deploy/` in this checkout. The Mac transcript plist is already daily. Documentation explicitly distinguishes prepared changes from installed schedules and calls for retiring standalone transcript cron at steward cutover.
- `docs/reports/task-9d3957f6/PR_BODY.md`: prepared PR description.

## Validation performed

All tests run from this sparse worktree, using the existing venv interpreter only; no test ran in the main checkout. The system `python` is absent and system `python3` has no pytest, so the interpreter used is `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`.

```sh
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_drive_leg.py scripts/test_gc_worktree_reap.py tests/test_worktree_sparse.py tests/test_worktree_keep_paths.py scripts/test_gc_stale_tasks.py -q -o addopts=''
```

Full suite result: **119 passed in 39.01s**. Final review then added fetch pruning and a deleted-origin-branch regression; reran the entire reaper file: **61 passed in 24.52s**. Existing sparse policy and stale-task sweep tests are included in the full run. Fixtures use fake rclone, temporary bare origins, worktrees, SQLite databases and local state directories. No real Drive, Docker or task mutation is involved. `git diff --check` passes. The exact Agents-Rules companion diff below passes `git -C /opt/MoonieXHQ/Agents/Rules apply --check -` without changing that repository.

Read all 13 FAILED lines in the canonical host's `state/drive-leg.log` (this worktree has no copy). Actual quota text includes `"quota_unit": "1/min/{project}"`, `"reason": "RATE_LIMIT_EXCEEDED"`, and trailing `rateLimitExceeded`. Tests cover those strings, `403 userRateLimitExceeded`, `429`, and `rate-limit`.

### Host runner-state dry-run

Command (exit 0; false relay ensures no accidental Drive call can succeed):

```sh
DRIVE_LEG_RCLONE=/bin/false /opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/drive_leg.py runner-state --dry-run
```

```text
runner-state codex: /root/.codex/sessions: 113 files, 77498165 B, archive to Runner-State/contabo/codex, older than 7 days [dry-run]
runner-state agy: /root/.gemini/antigravity-cli/conversations: 113 files, 426949448 B, archive to Runner-State/contabo/agy, older than 7 days [dry-run]
runner-state agy: /root/.gemini/antigravity-cli/brain: 1972 files, 406002607 B, archive to Runner-State/contabo/agy, older than 7 days [dry-run]
runner-state agy: /root/.gemini/antigravity-cli/log: 5914 files, 188546297 B, delete logs (no upload), older than 7 days [dry-run]
```

### Host review-idle dry-run

Direct `/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/gc_stale_tasks.py --review-idle` failed before selecting tasks because the sparse worktree has no `state/tasks.db`. Output began and ended as follows (intervening traceback omitted):

```text
df before:
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        72G   59G   13G  83% /
FileNotFoundError: tasks.db not found at /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-9d3957f6/state/tasks.db
```

The normal `scripts/hub/with-org-db-env.sh` invocation with `ORG_ROOT=/opt/MoonieXHQ/Agents/Core` could not reach the hub environment provider: `urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>`. No credentials were printed. For useful host evidence, ran the same dry CLI against the host's existing read-only task snapshot (snapshot mtime 2026-10-28 14:44), explicitly overriding only the DB path:

```sh
ORG_ROOT=/opt/MoonieXHQ/Agents/Core /opt/MoonieXHQ/Agents/Core/.venv/bin/python -c 'from pathlib import Path; from lib import db; from tools import gc_stale_tasks; db.DB_PATH = Path("/opt/MoonieXHQ/Agents/Core/state/tasks.snapshot.db"); raise SystemExit(gc_stale_tasks.main())' --review-idle
```

Exit 0. This is snapshot evidence, not a live-ledger eligibility claim. Full output:

```text
df before:
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        72G   59G   13G  83% /
reap: cached origin refs in '/opt/MoonieXHQ/Agents/Core' (dry-run; no fetch)
  skipped       task-6bf6db6d  review          214.0 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__browser_operator__task-6bf6db6d'  -- review task is not idle long enough
reap: cached origin refs in '/opt/MoonieXHQ/Projects/MoonieX/Console' (dry-run; no fetch)
  skipped       task-5eb22787  review            3.4 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-console__security_engineer__task-5eb22787'  -- review worktree is not clean
  skipped       task-f99c6370  review          214.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__browser_operator__task-f99c6370'  -- review branch HEAD does not equal origin HEAD
  skipped       task-c7aa0799  review            3.6 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-console__developer__task-c7aa0799'  -- review worktree is not clean
  skipped       task-3bae2e59  review          213.7 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__browser_operator__task-3bae2e59'  -- review branch HEAD does not equal origin HEAD
  skipped       task-6667f7ca  review          216.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-6667f7ca'  -- review task is not idle long enough
  skipped       task-c1ad1e4f  review          973.3 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-c1ad1e4f'  -- review task is not idle long enough
  skipped       task-969c8299  review          216.2 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-969c8299'  -- review task is not idle long enough
  skipped       task-340d66ad  review          216.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-340d66ad'  -- review task is not idle long enough
  skipped       task-ab94e651  review          217.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-ab94e651'  -- review task is not idle long enough
  skipped       task-89e8ab84  review          214.0 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__browser_operator__task-89e8ab84'  -- review branch HEAD does not equal origin HEAD
  skipped       task-e7bd04c6  review          217.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-e7bd04c6'  -- review task is not idle long enough
  skipped       task-4edacf73  review          216.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-4edacf73'  -- review task is not idle long enough
  skipped       task-9148e7c0  review          216.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__tester__task-9148e7c0'  -- review task is not idle long enough
  skipped       task-f4045ccd  review          217.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-f4045ccd'  -- review task is not idle long enough
  skipped       task-7a7d1a66  review          972.3 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-7a7d1a66'  -- review task is not idle long enough
  skipped       task-0d3ec506  review          216.5 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__security_engineer__task-0d3ec506'  -- review task is not idle long enough
  skipped       task-69f822f3  review          216.6 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-69f822f3'  -- review task is not idle long enough
  skipped       task-57982869  review          217.1 MB  '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-57982869'  -- review task is not idle long enough
[dry-run] reap: would remove 0 worktree(s) (0.0 MB), skipped 19, flagged 0 stale 'review' worktree(s) (>21d, not merged), kept 0 other 'review' worktree(s)
df after:
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        72G   59G   13G  83% /
```

## Agents-Rules companion PR: exact diff

Suggested title: `Define Runner-State in the Drive archive gate`. The repository is outside writable roots, so no changes or push were attempted there. Apply this exact diff to `/opt/MoonieXHQ/Agents/Rules/playbooks/drive-archive-gate.md` in a separate feature branch/PR:

```diff
diff --git a/playbooks/drive-archive-gate.md b/playbooks/drive-archive-gate.md
--- a/playbooks/drive-archive-gate.md
+++ b/playbooks/drive-archive-gate.md
@@ -22,3 +22,4 @@
 | Source on the Mac | Destination in Google Drive (`ไดรฟ์ของฉัน/`) | Note |
 |---|---|---|
+| Runner state (all machines): Codex `$HOME/.codex/sessions`; AGY `$HOME/.gemini/antigravity-cli/{conversations,brain}` | `BACKUP/MoonieX HQ/Runner-State/<machine>/<runner>/` | DiskSteward plan approved 2026-10-28: archive daily when older than 7 days (policy `runners:`). `tools/drive_leg.py runner-state`: one tar + manifest with member path/size/md5; verify archive AND manifest md5 on Drive before deleting unchanged local sources. Contabo uses `scripts/rclone_via_winbox.sh`; relay/quota/verification failure keeps sources. Secrets excluded. AGY `log` older than 7 days is deleted locally without upload and logged. |
 | `~/Backups/**` | `Archive/Backups/<same relative path>` | VPS backups; keep folder names and dates |
```

## Blockers

- PR creation attempted with `gh pr create --repo PASAKON/Agents-Core --base main --head agent/codex-task-9d3957f6 --draft --title 'DiskSteward P1: verified runner archives and restorable review checkouts' --body-file docs/reports/task-9d3957f6/PR_BODY.md`. Exit 1: `error connecting to api.github.com`. No PR URL exists. Launcher/CTO must publish after the launcher commits and pushes; no sign-in or default-branch changes were made.
- Live hub dry-run could not load its environment due to DNS restrictions. A clearly labeled read-only snapshot dry-run is supplied instead. Re-run against the live hub before deployment.
- Agents-Rules is outside the permitted worktree. Exact companion diff above is the requested fallback.

## Not checked / risk

- No real Drive upload, Drive quota/space query, relay outage test on the actual winbox, or destructive reaper run; these are intentionally covered by fakes/temp repos only. Folder child IDs remain unrecorded until first approved operational upload.
- Runner-State currently follows drive_leg's existing Contabo machine naming and relay path. The new source-opening safeguard uses POSIX no-follow file descriptors; a native Windows runner needs a corresponding handle-based implementation before using this verb directly there.
- Archive scratch storage peaks at one source-root tar; current dry-run largest root is about 427 MB. Failure retains originals and removes scratch. Previously verified remote archives may remain if a later group fails, with new unique names on a later run.
- Secret exclusion is by filename/path component, as requested; arbitrary secrets embedded in otherwise allowed transcript content are not detected.
- Review dry-run uses cached origin refs; acting mode fetches with pruning before exact comparison, so a deleted remote branch does not count as pushed. Task/file activity is conservative and can keep a checkout longer than three days. Existing `/proc` cwd fail-closed behavior remains Linux-specific.
- Snapshot data is not authoritative for current live task state. No schedule is installed, and part A integration is not merged here; its currently visible runner schema was read and tested without editing its files.

## Skill learning

- Drive filing rule 12 requires checksum evidence, and this repo's `put()` strengthens that to both archive and manifest verification. Reusing that boundary plus deferred `_delete_verified()` kept sources intact in fake-relay md5, quota exhaustion, and manifest-failure tests.
