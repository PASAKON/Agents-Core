# REPORT task-857789b6

Order O-20261101-1644-d559, GH #634 (winbox agy browser_operator dies at once). Branch `agent/developer-task-857789b6`, from origin/main f95833d8. Nothing was run on winbox and no PowerShell exists on this box: every `.ps1` change is checked by static tests only.

## Summary

On winbox, a `browser_operator` agy run now gets a prompt that allows exactly one shell command (the `tools/agy_browse.py` call), starts in its worktree, and is covered by a Windows allow-list (`config/agy-settings-winbox.json`) that a new installer puts at `%USERPROFILE%\.gemini\antigravity-cli\settings.json`. Every other role keeps the edit-only prompt word for word. After any agy run the launcher appends `AGY_DENIED` lines to `agy-events.log` naming the refused tool, and (for browser_operator, which now asks agy for JSON) the path or command, with URLs and tokens scrubbed.

## Files Changed

- `windows/spawn-worker.ps1` -- agy block only (+107, -1 line):
  - `$agyBrowser = ($Role -eq 'browser_operator')`; only then a second prompt that allows the one browse command, spelled with the venv python when `<worktree>\.venv\Scripts\python.exe` exists, else `%LOCALAPPDATA%\Programs\Python\Python311\python.exe`. The default edit-only here-string is untouched.
  - `--add-dir $WorkDir` when `-WorkDir` is set (all agy roles, as the codex branch and `runners/agy_local.py` already do).
  - browser_operator only: `--output-format json`; the launcher does `Set-Location` + `[Environment]::CurrentDirectory` to the worktree before agy starts, and sets `AGY_BROWSE_SHOT_DIR` to `-WorkDir` or `.launch-<task>\shots` (outside the worktree, so `git add -A` never sees a screenshot).
  - all agy roles: a `try { } catch {}` step after the EXITCODE line and before the report step that appends `AGY_DENIED` lines (details below).
- `config/agy-settings-winbox.json` (new) -- Windows allow-list and deny-list. `config/agy-settings.json` is not touched, so the Mac/Contabo rule and `tests/test_agy_browse.py::test_repo_agy_settings_carry_exactly_the_reviewed_rule` are unaffected.
- `windows/install-agy-settings.ps1` (new) -- installer.
- `tests/test_agy_settings_winbox.py` (new) -- 90 tests.
- `docs/reports/task-857789b6/REPORT.md` -- this file.

### The Windows settings file

- Allow, two `command(regex:...)` rules, same tail for both: ` tools[/\]agy_browse\.py`, optional `--port N` / `--tab ID`, the 14 verbs of `tools/agy_browse.VERBS` (a test pins the list), then arguments.
  - Rule 1: `C:\Users\passg\mooniex\worktrees\<project>__browser_operator__task-<8 hex>\.venv\Scripts\python.exe`.
  - Rule 2: `C:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe`.
  - Arguments are tokens separated by one space: a bare token of `[A-Za-z0-9_./:#=@+\[\]-]`, or a single- or double-quoted token that may also hold space, `,` and `()`. This is stricter than the Mac rule, because the Windows shell parses `(`, `,` and `%` differently from bash; a selector or phrase that needs them must be quoted, and the prompt says so.
- Allow, two `read_file` rules: `C:\Users\passg\mooniex\worktrees` in backslash and slash spelling. No `read_url`, `mcp`, `write_file`, `command(*)`.
- Deny: the 11 Mac entries kept, plus `del`, `erase`, `rd`, `rmdir`, `ri`, `Remove-Item`, `Invoke-WebRequest`, `Invoke-RestMethod`, `iwr`, `irm`.

### The installer

`powershell -NoProfile -ExecutionPolicy Bypass -File windows\install-agy-settings.ps1 [-DryRun] [-ExpectSha256 <hex>] [-Source <path>] [-Destination <path>]`

Reads the source as bytes (refuses a BOM, a source without non-empty allow/deny arrays, or a `command(*)` allow), prints and checks its sha256, stops with exit 3 if `%USERPROFILE%\.gemini\antigravity-cli` does not exist, copies an existing different file to `settings.json.bak-<yyyyMMdd-HHmmss>` (never over an existing backup name), writes a temp file in the same folder, checks its hash, replaces `settings.json` in one step (`File.Replace`, or `File.Move` when there was none), reads it back, and prints `SOURCE= DEST= BACKUP= SHA256=`. The same bytes already installed: `ALREADY_INSTALLED`, nothing written. `-DryRun` prints the plan and writes nothing. Rollback: copy the printed `BACKUP` over `settings.json`, or delete `settings.json` when `BACKUP=none`.

sha256 as committed (LF, ASCII), for the Contabo card to pin:
- `config/agy-settings-winbox.json` `78c621f5810779ad15dfe1e9ec9255a40e1944e105671af4010786ab162377d4`
- `windows/install-agy-settings.ps1` `f0b24bae0f813e41e176a2448e2cab3dc5756f48f965654e3158660610677dd7`

(These match the tree at commit 102a5c7c. A later commit on this branch that touches either file changes them; recompute with `sha256sum` on the merged tree before pinning.)

### The denied-target log (item 4)

What agy does and does not tell us, measured on Contabo's agy 1.4.12 without a model call: `agy changelog` says a headless `-p` run "ends with a notice naming the refused actions and reports them as `denied_actions` in the JSON output"; the plain-text notice (`a tool required the "read_file" permission that headless mode cannot prompt for ...`) names only the tool; agy's own log files under `~/.gemini/antigravity-cli/log` hold no denial detail at all. So the path or command can only come from `denied_actions`, which needs `--output-format json`. The step therefore:
- all agy roles: finds `a tool required the "<tool>" permission` in `agy-events.log` and appends `AGY_DENIED tool=<tool>`;
- when the log holds a `denied_actions` array (browser_operator, which now runs with `--output-format json`): appends one `AGY_DENIED tool=<action> key=value ...` line per entry, taking every short string field of the entry except page-content keys (`response content text body html page output stdout stderr message snippet data`);
- every value: JSON escapes undone, any `scheme://...` replaced by `<url>`, `ya29.`/`eyJ` tokens and `*token|secret|password|key=...` assignments redacted, whitespace collapsed, cut at 200 characters, line cut at 600, at most 20 lines. It only appends (`AppendAllText`), is wrapped in `try { } catch {}`, and runs before the report step so the stub report's log tail carries the lines.

The field names inside a `denied_actions` entry beyond `action` are not documented; that is why the step logs whatever short string fields are there rather than guessing a key.

## Commits

- b4f0b9ee -- agy-winbox: browser_operator shell contract, Windows allow-list, denied-target log, installer
- 102a5c7c -- agy-winbox: tests for the winbox allow-list, installer, launcher and denied-target step
- (this REPORT is committed after those two)

## Tests

- ran: `env -u ORG_DB_URL .venv/bin/python -m pytest -q -o addopts='' tests/test_agy_settings_winbox.py tests/test_agy_settings_rules.py tests/test_agy_browse.py tests/test_spawn_worker_ps1_runners.py scripts/test_spawn_worker_ps1.py`
- passed: 249
- failed: 0
- skipped: 0
- also ran, because they read `spawn-worker.ps1`: `tests/test_spawn_worker_ps1_finish.py test_delegate_probe_gate.py test_delegate_winbox_injection.py test_h3_runner_model_launch.py test_nonclaude_worker_contract.py test_ps1_no_drive_scoped_vars.py test_w03_self_host_spawn.py test_w06_launcher_report.py test_w27_security.py test_w33_node_dispatch_windows.py test_w33_spawn_worker_ps1.py`: 677 passed, 1 failed. The failure was `test_w33_spawn_worker_ps1.py::test_braces_and_parens_balance`: my `denied_actions` pattern had a bare `}` in a character class. Fixed (`[,\x7d]`); that file, the new file and `test_spawn_worker_ps1_runners.py` then ran 158 passed.
- The new file covers: both allowed python forms with 13 command shapes each; `; & && | || > >> < \n \r\n ` $(` after, glued to and inside the command; shell syntax in arguments; another script; another python (12 forms); a python outside a `__browser_operator__` worktree (11 forms); bad verbs/ports/tabs; the verb list equals `tools.agy_browse.VERBS`; Mac forms refused and the other way round; allow-list holds exactly 2 command rules and 2 reads; every deny entry matched by no allow rule; the Mac deny entries and the order's Windows forms are present; installer text (path, atomic replace, backup before write, hashes, `-LiteralPath`, no network or delete calls beyond its own temp file); launcher text (role gate, default prompt word for word, `--add-dir`, JSON only for the browser, cwd, step order); the denied-target patterns taken out of the script and run by a Python mirror of its loop (notice, JSON, URL and secret scrub, page-content keys, truncation, 20-line cap).
- Fails-without-the-fix check, done in memory (no file edited): 7 mutations of the loaded settings each made the matching test fail (`;` added to the bare class, role segment loosened, Python version unpinned, `iwr` dropped from deny, an `rm` allow added, an extra allow rule, `()` allowed in bare tokens). `test_the_url_pattern_is_what_stops_the_leak` empties the URL pattern and asserts the URL then reaches the log.

## Issues / Blockers

- `mcp__org__wiki_read("org:IRON-RULES.md")` answered "wiki 'org' not available in this environment", so I read `/opt/MoonieXHQ/Agents/Rules/IRON-RULES.md` on disk (grep for agy) and the repo docs instead.
- Model for a remote agy run with no pin (asked in the order): `gemini-3.8-flash-high`, not Argon. It lives in `windows/spawn-worker.ps1` line 828 (`$agyModel = if ($RunnerModel) { $RunnerModel } else { 'gemini-3.8-flash-high' }`). `tools/delegate.py` (~L1542) sends `-RunnerModel` only when `task['runner_model']` is set; a task pinned `runner=agy` with no model sends nothing, so the script default applies. The same default sits in `scripts/spawn-worker-remote.sh:115` and `runners/agy_local.py:111`. The router's `browser_agy` class in `config/plans.yaml:44` lists only `agy:gemini-3.8-flash-high`; Argon is first only in `dev_general` and `doc_text`. I changed none of it.
- Why the read was denied is not proven. Findings, none verified on winbox: the generated launcher never set agy's working directory (Contabo starts agy in tmux `-c $WT`, the Mac runner sets `cwd=worktree`), so a relative path resolves against the scheduled task's folder, outside the `--add-dir` workspace; and `-WorkDir` is empty for a remote task unless its row carries `work_dir` (`tools/delegate.py` creates a Work folder only for local runs), so a missing Work folder is not what stopped task-62e1066c. I set the working directory for browser_operator only. The other winbox agy roles still start in the scheduled task's folder; whether that is why task-27510f80, task-05286854 and task-acd86db6 died is unknown, and I left it alone as out of scope.

## Notes for Reviewer

- Reach of the change:
  - `windows/spawn-worker.ps1` agy branch is entered from `tools/delegate.py::_spawn_remote` (ssh) and `tools/node_dispatch.py` (self-host spawn); neither passes anything new. `-Role` already goes through `_PS_TOKEN_RE`.
  - Tests that read the script: the 16 files listed above, all green except the one fixed brace case.
  - New config keys, exports, fixtures: none. `config/machine-contract.yaml` row `$HOME/.gemini/antigravity-cli/settings.json` says "restore: cp config/agy-settings.json" for `machine: all`; on winbox the restore source is now `config/agy-settings-winbox.json` via the installer. I did not edit the contract (not in this task's files); it needs a winbox row.
  - `docs/ops/agy-browser.md` documents the Mac rule only; it needs a Windows paragraph. Also not edited.
- Scope of the settings file: agy reads one user settings file for every agy run by that Windows user, so these rules are visible to all agy roles on winbox, not only browser_operator. The role split comes from the prompt, and, for rule 1, from the `__browser_operator__` worktree name; rule 2 (the named Python) has no role in its text. The `read_file` prefix is the worktrees root, the smallest static prefix that covers "the worktree"; the per-task scope comes from `--add-dir`. If you want per-run scope instead, agy 1.4.12 has `--settings` ("this session only, never saved: a JSON object of settings.json keys, inline or as a file path"), which would let the launcher pass the rules for one run. I did not use it: the order asks for the installed file, and I could not check the flag on winbox's agy.
- `agy-events.log` for a browser_operator run now holds agy's JSON result, not prose, so a stub REPORT built from its tail is JSON. The `AGY_DENIED` lines are the last lines, so they are inside the 200-line tail. Widening `--output-format json` to all agy roles is a one-line change once the first winbox run shows the flag works.
- First winbox use: run the installer with `-DryRun` first, then with `-ExpectSha256 <the source hash the dry run printed>`.
- Where this will break first, in my reading: `tools/agy_browse.py` exists only in a Core worktree, so a browser_operator task on another project has no script to run; and the named Python 3.11 needs playwright for `agy_browse` to attach.

## Not checked / risk

- Nothing here ran on winbox or under PowerShell. A syntax slip in the generated launcher shows up as a worker that dies before agy starts, and the only guard is the repo's brace-balance test and my text checks. Run the installer with `-DryRun` first, and one `browser_operator` agy task read-only before relying on it.
- agy's real matcher on Windows: I used Python `re` as the stand-in. Not known: whether agy matches the command exactly as the model typed it, whether it normalises `\` and `/` in `read_file` targets (hence both spellings), whether a prefix target covers the worktree below it, and whether the agy state folder on Windows is `%USERPROFILE%\.gemini\antigravity-cli` (taken from the Mac/Contabo path and `docs/ops/agent-runners.md` sec. 6b; the installer refuses to write when the folder is missing).
- `--output-format json` on winbox's agy build (Contabo is 1.4.12; winbox is unknown): if the flag is unknown there, a browser_operator run fails at once instead of starting. The field names in a `denied_actions` entry are unknown beyond `action`.
- That the denial is the whole cause of the failed task-62e1066c, and that the working-directory change cures it.

## Skill learning

- MISSING [CTO_Knowledge_AGY §headless contract] : `agy --settings '<json or file>'` gives session-only settings (no global file needed), `--output-format json|stream-json` and `--print-timeout` exist on 1.4.12, and `agy changelog` is a free, local way to read what a CLI version does (1.1.27+: a refused action is named in a notice and returned as `denied_actions`). agy's own log files hold no denial detail. · evidence: task-857789b6, `agy --help`, `agy changelog` on Contabo 1 Nov
- MISSING [CTO_Knowledge_AGY §What holds] : the winbox launcher (`windows/spawn-worker.ps1`) started agy with no working directory, while Contabo (`tmux -c $WT`) and the Mac (`cwd=worktree`) do; a relative path in a brief resolves against the scheduled task's folder on winbox. n=1, unverified on winbox · evidence: task-857789b6, `windows/spawn-worker.ps1` agy branch, `scripts/spawn-worker-remote.sh:273`, `runners/agy_local.py`
- WRONG [docs/ops/agent-runners.md §6b] : "a global settings.json allow-list is parsed and discarded one line later ... a dead end" (2026-09-22) -- since 2026-09-30 the global `config/agy-settings.json` allow-list is what lets headless agy run `pytest` and `agy_browse` on Mac and Contabo · evidence: `mooniex:research/2026-09-30-agy-cli-permissions-headless.md`, `config/machine-contract.yaml:64` · fix: mark the §6b paragraph superseded and point to `config/agy-settings.json`
- COSTLY [developer playbook | no owner] : no PowerShell on Contabo, so a `.ps1` change cannot be run; the only syntax guard is `tests/test_w33_spawn_worker_ps1.py::test_braces_and_parens_balance`, which counts raw `{` `}` and failed on a regex character class `[,}]` in a single-quoted pattern. Write `\x7d` for a literal `}` in any pattern inside `spawn-worker.ps1` · evidence: task-857789b6, a 4-minute batch of 12 test files before that failure showed · prevented by: run `tests/test_w33_spawn_worker_ps1.py` right after the first `.ps1` edit, not at the end
