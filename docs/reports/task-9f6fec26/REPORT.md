# REPORT — task-9f6fec26 (auto-compact window → 300k)

## Summary

Every session this org launches now auto-compacts at 300,000 tokens instead
of the 1M-model default (~967K): set at the documented `autoCompactWindow`
key in `claude-home/settings.json` (symlinked live to `~/.claude/settings.json`
on the Mac, ADR 0027) plus a guarded `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000`
env-var export (only-if-unset) in all six launchers, for boxes where
settings.json is a stale copy. Added a `## Compact instructions` section to
the global CLAUDE.md, a new ops runbook, and a config test. Full suite: 1120
passed / 2 pre-existing failures (verified identical on `main`, unrelated to
this change) / 16 skipped, exit 1.

## Verified doc quotes (facts-first, per task brief)

Fetched https://code.claude.com/docs/en/model-config directly (no cache hit
in `mooniex:research/` — see Skill learning below for why the answer isn't
also filed there):

> **`autoCompactWindow`** - Settings key to save your preferred auto-compact window
> **`CLAUDE_CODE_AUTO_COMPACT_WINDOW`** - Environment variable for scripts and cloud environments
> **`/autocompact`** - Interactive command to set the window for this and future sessions
> **`DISABLE_COMPACT`** - Environment variable to disable all compaction
>
> "Models running with a native 1M window, such as Sonnet 5, the Fable
> models, and Opus 4.7 and later on the Anthropic API, compact before the
> window fills, **at about 967K tokens by default**."
>
> Priority order: 1. env var (`CLAUDE_CODE_AUTO_COMPACT_WINDOW`) — takes
> precedence over all; 2. CLI flag (`--autocompact`); 3. `/autocompact`
> command; 4. settings file (`autoCompactWindow`); 5. model's tuned default.

Matches the brief's key names exactly — no deviation needed. Installed CLI
confirmed at 2.1.280 (`claude --version`).

## Files Changed

- `claude-home/settings.json` — added top-level `"autoCompactWindow": 300000`; every existing key/hook untouched (diff is a single added line).
- `scripts/cto-claude.sh` — guarded export near existing `DISABLE_AUTOUPDATER=1`; this script runs `claude` as a child process at the end (not `exec`), so the export reliably reaches the real process.
- `scripts/cxo-claude.sh` — same, same anchor point.
- `scripts/spawn-cto.sh` — guarded export near the existing `ENV_PREFIX` env-forwarding loop.
- `scripts/spawn-cxo.sh` — same.
- `scripts/spawn-worker.sh` — guarded export before the final `exec .venv/bin/python -m runners.worker_init`; confirmed `runners/worker_init.py` does `env = os.environ.copy()` then `os.execvpe("claude", ..., env)`, so this one reliably reaches the worker's claude process.
- `scripts/spawn-worker-remote.sh` — guarded export near existing `GIT_TERMINAL_PROMPT`/`GIT_SSH_COMMAND` exports.
- `claude-home/CLAUDE.md` — added `## Compact instructions` section (9 lines of content, within the ≤15 line budget), add-only, nothing else in the file touched.
- `docs/ops/token-saving-2026-09-25.md` — new ops runbook: what/where, in-session verification (`/context`, `/usage`), weekly check, rollback, and the exact re-derive command (`bash scripts/install-claude-home.sh`, confirmed exists).
- `tests/test_token_saving_config.py` — new: settings.json parses + carries the key; each of the 6 launchers has the guard; CLAUDE.md carries the section. Reads repo files by path only, never `$HOME`.
- `WORKLOG.md`, `REPORT.md` — this task's process files (worktree root).

## Commits

- `75584b82` — token-saving: set autoCompactWindow=300000 in settings.json + all 6 launchers
- `e4353ac6` — token-saving: add Compact instructions section to global CLAUDE.md
- `6e573ecc` — worklog: backfill steps 0-3
- `8f783132` — docs: token-saving-2026-09-25 ops runbook
- `2881cb29` — worklog: step4
- `9759d423` — test: token-saving auto-compact window config
- `75498245` — worklog: step5

All on `agent/developer-task-9f6fec26`, none touch `main`.

## Tests

- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests` (this worktree has no `.venv` of its own — see Skill learning; used the main repo's venv against this worktree's `tests/` by running with cwd = worktree)
- passed: 1120
- failed: 2 — **both pre-existing and unrelated to this task**, reproduced identically on `main` in a subshell (never changed the session cwd):
  - `tests/test_machine_doctor.py::test_detect_machine_by_unique_os_when_hostname_does_not_match` — the test's own comment says "This suite runs on Linux (Contabo, per the brief)"; running on macOS Darwin makes the OS-fallback pick `macbox` instead of the test's hardcoded `linuxbox` expectation. Platform-dependent test, not a real regression.
  - `tests/test_multihost.py::test_browser_operator_cap_reached_sets_conflict` — fails because this Mac currently has **3.9–4.0 GB free disk**, under ADR 0030's 5 GB floor, so the spawn is queued (`pending`) instead of hitting the cap path the test expects (`conflict`). Environmental, not code.
- skipped: 16
- exit code: **1** (both failures above; the new `tests/test_token_saving_config.py` — 4/4 — is inside this run and passes)
- ran standalone: `.venv/bin/python -m pytest tests/test_token_saving_config.py -x` → 4 passed
- `bash -n` on all 6 edited launchers: OK (also confirms macOS bash 3.2 compatibility — no arrays, no `declare -A`, no `${var,,}` used)
- `python3 -c "import json; json.load(open('claude-home/settings.json'))"` → valid
- smoke test (one run only, as instructed): `claude -p "reply with the single word ok" --model claude-sonnet-5` → replied `ok`

SKILL-OVERRIDE: cto-merge-checklist :: task brief said run `pytest tests -q -x` :: ran `pytest tests -x` (no extra `-q`) :: pytest.ini's own `addopts` already carries `-q`; a second `-q` makes `-qq`, which drops the pass/fail totals line — promoted HARD rule in that skill (§2, 2026-09-25, 3 independent sightings) takes precedence over the brief's literal command text.

## Issues / Blockers

- **Disk space on this Mac is at 3.9–4.0 GB free**, under ADR 0030's 5 GB spawn floor — this is what's causing the second test failure above and could be blocking other spawns right now. Out of scope for this task (not in `touches`), but worth the CTO's attention per IRON §48 (alert first, move by hand).
- This worktree was created with no `.venv` of its own — had to run tests against the main repo's `.venv/bin/python`. Not blocking (worked fine), but the task's own step 6/7 command text (`.venv/bin/python -m pytest ...`) assumes a `.venv` exists in the worktree, which it didn't here.

## Notes for Reviewer

- The guarded export added to `scripts/spawn-cto.sh`, `scripts/spawn-cxo.sh`, and `scripts/spawn-worker-remote.sh` sets the var in **that script's own shell**, per the brief's literal instruction ("do not restructure the scripts"). For `spawn-cto.sh`/`spawn-cxo.sh`, the actual `claude` process is launched later inside a fresh osascript/tmux shell (both files' own comments already document that a caller's plain `export` does not cross that boundary — only vars explicitly re-exported through the `ENV_PREFIX` loop do). The var **does** reach the real process there regardless, because `cto-claude.sh`/`cxo-claude.sh` carry the same guarded export directly in the shell that execs `claude` as a child. For `spawn-worker-remote.sh`, the real claude invocation happens inside a separately generated `LAUNCH_SH` run via `tmux new-session -d` on Contabo — this script's own export may not cross into that tmux session's environment (same class of issue). Recommend the CTO verify with `echo $CLAUDE_CODE_AUTO_COMPACT_WINDOW` inside an actual spawned Contabo worker session before relying on it there; if it doesn't propagate, the fix is one more `printf 'export CLAUDE_CODE_AUTO_COMPACT_WINDOW=...\n'` line in the `LAUNCH_SH` generation block (near the existing `ORG_HOST`/`ORG_WORKER_FINISH` lines) — deliberately not done here since the brief said not to restructure.
- `spawn-worker.sh`'s export is confirmed to reliably reach the local Mac worker's `claude` process (`os.environ.copy()` → `os.execvpe`), and `scripts/cto-claude.sh`/`scripts/cxo-claude.sh`'s exports are confirmed to reach their `claude` child process directly — these three plus `claude-home/settings.json` are the parts of this change I'd call load-bearing; the other three are honest defense-in-depth.

## Skill learning

- MISSING [research cache policy (ADR 0028 §6) | no owner] : the research-cache gate (`scripts/hook-research-gate.py`) requires writing a `mooniex:research/*.md` file after any web search, but the developer/worker role's Shared DEV Conventions hard rule #4 ("You cannot write to the wiki. Only C-level can.") forbids exactly that write — no skill or doc says which wins for a worker who must WebFetch external docs. I followed the hard rule (no wiki write) and instead put the verified quotes directly in this REPORT.md and in `docs/ops/token-saving-2026-09-25.md` · evidence: this session's `hook-research-gate.py` block message + `IRON-RULES.md` §0/§47 vs. the worker role conventions text.
- MISSING [dev-spawn-protocol §Agent-tool fallback] : this worktree (`mooniex-agents__developer__task-9f6fec26`) had no `.venv` of its own; had to run tests/smoke against the main repo's absolute `.venv/bin/python` path. This is a second, independent sighting of the same gap the skill already notes from the Run Inbox P1b worker (2026-09-25, commit a0abdcaf: "Agent-tool fallback: push the brief first, name the main .venv") — worth promoting from field-note to rule given 2 independent hits now · evidence: task-9f6fec26, `ls .venv` → not found in this worktree, `.venv/bin/python -m pytest` from the brief's own step 6/7 text would have failed verbatim.
- COSTLY [no owner] : verifying whether a guarded env-var export in a launcher script actually reaches the final spawned `claude` process took real investigation (reading `os.execvpe` call sites, tracing osascript/tmux fresh-shell semantics already documented inline in `spawn-cto.sh`/`spawn-worker-remote.sh`) — a task brief that lists N files to add the "same" export line to should also say which of them are confirmed to reach the real process vs. which are advisory only, so a reviewer doesn't assume uniform effectiveness across all six · evidence: task-9f6fec26, see "Notes for Reviewer" above for the three-way split (cto-claude.sh/cxo-claude.sh/spawn-worker.sh confirmed load-bearing; spawn-cto.sh/spawn-cxo.sh/spawn-worker-remote.sh are defense-in-depth only).
