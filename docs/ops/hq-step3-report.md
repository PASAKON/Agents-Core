# task-b5f61b47 — HQ step ③ migration (MoonieX products + LinkReed/Webapp)

## Outcome summary

All eleven `step: 3` rows of `~/MoonieXHQ/hq.yaml` moved for real on the Mac,
verified, `hq doctor` clean. One real crash happened mid-`--apply` (see
"Incident" below); the script was fixed to be resumable and the migration
was completed on a second `--apply` run. Nothing was left half-moved at any
point a human could have observed it — the crash landed between two
completed rows and a moved-but-not-yet-symlinked one, which was fixed by
hand within the same turn before continuing.

## Before / after table

| path | branch | HEAD sha | dirty | before | after | worktrees |
|---|---|---|---|---|---|---|
| MoonieX/WebApp | bootstrap/landing-mvp | `654be5870c` | 0 | `/Users/gob/Projects/mooniex-webapp` | `/Users/gob/MoonieXHQ/Projects/MoonieX/WebApp` | — |
| MoonieX/ClaudeFlow | main | `3fdf429a26` | 0 | `.../mooniex-claudeflow` | `.../MoonieX/ClaudeFlow` | `Agents/worktrees/claudeflow-cto-broll`, `claudeflow-cto-tts` — both repaired, `git status` clean |
| MoonieX/Console | main | `ed5ce7b979` | 1 | `.../mooniex-console` | `.../MoonieX/Console` | `/private/tmp/console-review` — dangling (deleted without `git worktree remove`), pruned |
| MoonieX/LunarAgent | main | `454dcbffd3` | 1 | `.../mooniex-lunar-agent` | `.../MoonieX/LunarAgent` | — |
| MoonieX/Scriptable | main | `7f2d6f0073` | 0 | `.../mooniex-scriptable` | `.../MoonieX/Scriptable` | `Agents/worktrees/mooniex-scriptable__developer__task-ea46caac` — repaired, `git status` clean |
| MoonieX/WebDesign | ui/accordion-component | `51a9db4a83` | 0 | `.../mooniex-website-templete` | `.../MoonieX/WebDesign` | — |
| MoonieX/ClaudeSign | mooniex-main | `7d29e81b0f` | 4 | `.../mooniex-claudesign` | `.../MoonieX/ClaudeSign` | — |
| MoonieX/CookierunBot | main | `40d0eea6f8` | 39 | `.../cookierun-bot` | `.../MoonieX/CookierunBot` | — |
| MoonieX/AlphaTrader | main | `96840a7642` | 0 | `.../mooniex-alphatrader` | `.../MoonieX/AlphaTrader` | — |
| MoonieX/ComfyRunpod | main | `af81317de1` | 0 | `.../comfy-runpod-worker` | `.../MoonieX/ComfyRunpod` | — |
| LinkReed/Webapp | main | `60363a7598` | 0 | `/Users/gob/Projects/LinkReed-Webapp` | `/Users/gob/MoonieXHQ/Projects/LinkReed/Webapp` | — |

Every sha and dirty count above is unchanged before vs. after (re-verified
post-migration by hand, not just trusted from the script's own
`move_and_verify`). All 11 old paths are now compat symlinks pointing at
their new location, recorded in `hq.yaml compat_links:` with
`remove_at_step: 4`.

## Pushes

- `mooniex-claudesign` branch `mooniex-main` was ahead 17 on its tracking
  remote `mooniex` (there is no `origin`; `upstream` = `nexu-io/open-design`,
  untouched). Pushed with plain `git push` (uses the configured upstream, so
  it went to `mooniex`, never force). Verified live: `git ls-remote --heads
  mooniex mooniex-main` → `7d29e81b0f...` matches local HEAD exactly.
- `LinkReed-Webapp` branch `main` was ahead 2 on `origin`. Pushed, verified
  live: `git ls-remote --heads origin main` → `60363a7598...` matches local
  HEAD exactly.
- `mooniex-website-templete` branch `ui/accordion-component` has no upstream
  → **not pushed**, recorded in the manifest as `not pushed: no upstream —
  Projects/MoonieX/WebDesign branch ui/accordion-component`. Moved anyway per
  the task brief.

## launchd plists rewritten

- `~/Library/LaunchAgents/com.mooniex.console-mac.plist` — `ProgramArguments`
  and `WorkingDirectory` both rewritten from `/Users/gob/Projects/mooniex-console`
  to `/Users/gob/MoonieXHQ/Projects/MoonieX/Console`. `plutil -lint` → OK.
- `~/Library/LaunchAgents/com.mooniex.claude-usage-sync.plist` — `ProgramArguments`
  rewritten from `/Users/gob/Projects/mooniex-scriptable` to
  `/Users/gob/MoonieXHQ/Projects/MoonieX/Scriptable`. `plutil -lint` → OK.
- `~/Library/LaunchAgents/com.mooniex.webapp.autopull.plist` — **unchanged**.
  It has no hardcoded product path itself (it just runs
  `~/.local/bin/mooniex-webapp-autopull.sh`, a loose script outside any repo
  whose own `REPO=` variable still points at the old
  `/Users/gob/projects/mooniex-webapp` path — that keeps working precisely
  *because* the compat symlink exists). Backed up anyway per the manifest
  pattern (no-op backup, since nothing changed).
- **No `launchctl` command was ever run**, per instruction — the compat
  symlinks keep all three running jobs alive right now; the CTO reloads
  `com.mooniex.console-mac` and `com.mooniex.claude-usage-sync` when ready so
  they pick up the rewritten plist (functionally identical either way, since
  the symlink already resolves correctly).

## Repoints inside this repo (`mooniex-agents`)

`hq_migrate_step3.py --repoint` (new CLI mode) found and rewrote 30 tracked
non-doc files that hard-coded one of the eleven old paths, using the old→new
mapping read from `hq.yaml` before `--apply` touched it:

`config/projects.yaml`, `lib/db.py`, `lib/telegram_out.py`,
`runners/secretary_telegram_poll.py`, `scripts/frost_knight_thumbs.py`,
`scripts/frost_knight_weapons.py`, `scripts/funnel_review.py`,
`scripts/gdrive-bridge/ilag_sync.py`,
`scripts/gdrive-bridge/upload_sorry_sir_soundtrack.py`,
`scripts/gdrive-bridge/upload_suno_cues.py`, `scripts/gen-rebate-scenes.py`,
`scripts/higgsfield/gen_loop.py`, `scripts/mooniex_logo.py`,
`scripts/mooniex_poster.py`, `scripts/post-fed-result.js`,
`scripts/post-fed-warsh.js`, `scripts/post-gold-giveaway-leaderboard.js`,
`scripts/post-rebate-ab.js`, `scripts/pull-gmail-creds.sh`,
`scripts/sompong-mac.sh`, `scripts/sompong-restore-webhook.sh`,
`scripts/spawn-web-designer.sh`, `scripts/spcx_musk_gen.py`,
`scripts/spcx_poster.py`, `scripts/supabase_storage_quota_check.py`,
`scripts/test_designer_spawn_guard.py`, `scripts/trader_mindset_batch.py`,
`scripts/video_to_drive.py`, and 4 files under
`prototypes/bl-model-bakeoff/` (`avatar/omni_run.py`, `avatar/poll_now.py`,
`recover.py`, `run_bakeoff.py`).

After editing, the task brief's own verification grep
(`git grep -I -l -E '/Users/gob/Projects/(mooniex-webapp|...)' -- .
':!docs/reports' ':!docs/briefs' ':!docs/ops' ':!*.md'`) returns **0
matches**. `config/projects.yaml` still parses as YAML; nothing else touched
was YAML/JSON/plist.

**Trap hit and fixed**: the first `--repoint` run also matched two of
`hq_migrate_step3.py`'s own test fixtures, which had used the real
production names `mooniex-webapp` and `cookierun-bot` as synthetic
"old path" literals to test the rewriter itself — rewriting them made `old
== new` in those two tests, silently defeating them. Fixed by renaming the
fixture literals to names that can never collide with the real eleven
(`widget-service`, `gadget-service`) rather than special-casing the script
around its own test file.

## Outside-repo references — for the CTO, not in this diff

- `Agents-Wikis/playbooks/web-designer.md` lines 166 and 168: two hardcoded
  refs to `/Users/gob/Projects/mooniex-claudesign/.od/...` (a directory path
  and a sqlite command). Confirmed via grep — exactly 2, matching the task
  brief. Left untouched (wiki, C-level write only).
- `~/.claude.json` project-trust keys: found **8** keys matching the eleven
  old names (not the 12 the task brief estimated) —
  `/Users/gob/Projects/mooniex-claudeflow`, `mooniex-claudesign`,
  `mooniex-webapp` (twice — once plain, once suffixed `(Desk-A)`, a stale
  pre-ADR-0007 Desk-pattern entry), `LinkReed-Webapp`, `mooniex-console`,
  `comfy-runpod-worker`, `cookierun-bot`. These will each re-prompt Claude
  Code's trust dialog once when next opened at their old (now-symlinked)
  path — left alone per the task brief.

## hq.yaml / hq.py doctor

- `hq.yaml`: all 11 rows' `current:` updated to their new path; 11
  `compat_links:` entries appended (`{path, target, remove_at_step: 4}`).
  Backup of the pre-edit file: see manifest below. **HQ repo was not
  committed**, per instruction — `git -C ~/MoonieXHQ status --short` shows
  only `hq.yaml` and `MAP.md` modified, uncommitted, ready for the CTO.
- `hq.py map` → `MAP.md: 33 rows`.
- `hq.py doctor` output, verbatim:
  ```
  hq doctor: clean — disk agrees with the map
  ```

## Manifests

- Crashed run (Console's worktree repair failure):
  `state/hq-step3-migration-20260923T020936.json` — kept for the record,
  covers Phase A (all 11 preflights + both pushes) and the partial Phase B
  (WebApp fully moved+symlinked, ClaudeFlow fully moved+symlinked+2 worktree
  repairs, Console moved only).
- Completing run: `state/hq-step3-migration-20260923T021337.json` (31 ops) —
  the authoritative one for `--rollback`. Both are gitignored (machine-local,
  same pattern as step 2's manifests) — see `.gitignore`.
- `hq.yaml` pre-edit backup: `state/hq-step3-yaml-backup-20260923T021337.yaml`.
- Plist backups: `state/hq-step3-plist-backup-20260923T021337-com.mooniex.console-mac.plist`,
  `...-com.mooniex.claude-usage-sync.plist`.

## Incident: a real crash mid-`--apply`, and how it was handled

`git worktree list --porcelain` for `mooniex-console` included
`/private/tmp/console-review` — a scratch review checkout that had already
been deleted from disk without `git worktree remove`, leaving a dangling
admin entry (git itself flags this "prunable"). `repair_worktree()` correctly
refused it (`error: not a valid path: /private/tmp/console-review`), which
crashed the whole `--apply` process.

**State at the moment of the crash**: WebApp and ClaudeFlow were already
fully moved and symlinked (Phase B had completed for both). Console's repo
directory had already been `shutil.move`'d to its new location, but the crash
happened *before* its compat symlink was created — meaning
`/Users/gob/Projects/mooniex-console` briefly did not exist at all, which
matters because `com.mooniex.console-mac`'s `WorkingDirectory` pointed at
exactly that path and the launchd job was live.

**Immediate fix** (before touching the script): `git worktree prune` on
Console's new location (removed the dangling admin entry — confirmed genuine
via git's own "prunable" flag, nothing live was affected) and manually
created the compat symlink `/Users/gob/Projects/mooniex-console ->
.../MoonieX/Console`, then verified `git status`/`rev-parse HEAD` worked
through it and returned the unchanged sha and dirty count.

**Script fix** (committed, tested — see `b3ad7213`): `list_attached_worktrees()`
now drops any attached worktree whose path no longer exists on disk (pruning
the dangling entry) instead of handing it to `repair_worktree()`; and both
`cmd_plan()`/`cmd_apply()` treat a row whose old path already resolves
(through its own compat symlink) to the row's target as already migrated —
logged and skipped for the filesystem work, but still folded into the
`hq.yaml current/compat_links` update, since a crashed prior run may never
have reached that phase for it. Re-running `--plan` showed WebApp/ClaudeFlow/
Console correctly reported `ALREADY MIGRATED`; the completing `--apply` then
finished the remaining 8 rows cleanly in one pass with no further errors.

## Verification performed after `--apply`

- All 11 repos: `git rev-parse HEAD` matches pre-migration sha exactly;
  `git status --porcelain` line count matches pre-migration dirty count
  exactly; `git remote -v` unchanged (spot-checked ClaudeSign and
  AlphaTrader, both multi-remote).
- Both ClaudeFlow worktrees: `git status` succeeds (clean), `git rev-parse
  --git-dir` resolves inside `.../ClaudeFlow/.git/worktrees/<name>`.
- Scriptable's worktree: same check, resolves inside
  `.../Scriptable/.git/worktrees/<name>`; its one untracked `TASK.md` is its
  own (unrelated) task file, unaffected by the move.
- ClaudeSign → `mooniex` and LinkReed → `origin`: `git ls-remote --heads`
  matches local HEAD exactly on GitHub.
- All 11 old paths are real symlinks resolving to the exact new path.
- `hq.py doctor` clean (see above).

## Blockers

None — the migration completed in full. The two items under "Outside-repo
references" above are informational for the CTO, not blockers.

## Skill learning

- WRONG [hq-filing §Migration] : the skill's step-2 precedent (its own Field
  note) covers a *duplicate clone* turning out to have real unpushed
  branches, but says nothing about a *worktree* whose admin entry outlives
  the directory it points at — a different failure shape that also crashes
  mid-migration if `repair`/`remove` isn't defensive about it · evidence:
  `state/hq-step3-migration-20260923T020936.json` (the crashed run),
  `/private/tmp/console-review`.
- MISSING [hq-filing §Migration] : no guidance for what to do when `--apply`
  crashes mid-run and a row's launchd/production dependency (here, a live
  `WorkingDirectory`) briefly points at nothing — the fix here was "restore
  the symlink by hand within the same turn, verify, then make the script
  itself resumable" but that sequence isn't written down anywhere for the
  next migration step (Agents/* at step ④) to reuse · evidence: this
  report's "Incident" section, commit `b3ad7213`.
- COSTLY [no owner] : `git worktree list --porcelain` returning a dangling
  entry for a path deleted outside git's own bookkeeping cost one full crash
  + manual recovery before the fix; a defensive `git worktree prune` (or an
  existence check) ahead of any `repair` call would have caught it for free
  — worth folding into whatever future skill or playbook governs worktree
  hygiene generally, not just this migration script.
