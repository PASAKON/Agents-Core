# task-42aed98f report: join step 9 home, NODE_HOST_RE 3-31, seed skip, hq-join doc (Org Mesh W4.4c)

## Summary
join.sh step 9 now hands the probe `HOME="$HOME"` inside the sudo `env`, so the probe reads the node.yaml step 8 wrote even when sudo gives it root's HOME; the dry run names that home and file. `NODE_HOST_RE` is 3-31 (same string as `lib.config.HOST_NAME_RE`, stdlib-only kept), `seed_hosts_from_config()` seeds only what `config/hosts.yaml` declares, and `docs/ops/hq-join.md` says 3 to 31 and explains how a joined node knows itself.

## Step 9: the home/path choice (join.sh)
**Chosen: pass `HOME`.** The probe command is now `as_root env HOME="$HOME" ORG_HOST="$HOST" PYTHONDONTWRITEBYTECODE=1 ...`.
- Why not "point the probe at the node.yaml path": there is no env override for it. `lib.config.NODE_CONFIG_PATH` is a module constant computed from `Path.home()` at import (lib/config.py:201), and `lib/config.py` is outside this task's touches. HOME is the only lever that does not need a code change.
- Same home by construction: step 8's `write_node_yaml` writes `$CONF_DIR/node.yaml`, `CONF_DIR=$HOME/.config/mooniex` (check_args), and step 9 passes that same `$HOME`. `env` sets it after sudo has reset it, so it survives a default sudoers (`env_reset`), `always_set_home` and a plain `sudo sh join.sh`.
- Side effect, better not worse: the probe's other home lookups (`~/.claude`, `~/.codex`, `~/.gemini`, the ms-playwright cache, Chrome candidates in tools/node_dispatch.py) now look at the joining user's home, where the node's runners live, instead of root's. They are path checks/reads; the probe does not write under HOME (`PYTHONDONTWRITEBYTECODE=1` is already set), so root creates no root-owned files in the user's home.
- Dry run (step 9) now prints `env HOME=<home> ORG_HOST=<host> python3 tools/infisical_setup.py run ...` and `HOME=<home> is handed on explicitly: the probe reads <home>/.config/mooniex/node.yaml, the file step 8 wrote`.

## join.ps1: verified from the script, no behaviour fix needed
- `$script:ConfDir = Join-Path $env:USERPROFILE '.config\mooniex'` (Initialize-Args); step 8's `Write-NodeYaml` writes `ConfDir\node.yaml`.
- Step 9 `Invoke-Probe` runs `& $venvPy ...` in the same PowerShell process: no `Start-Process`, `-Credential`, `-Verb RunAs`, `runas` or `Invoke-Command`. A child inherits `USERPROFILE`, and on Windows Python's `Path.home()` reads `USERPROFILE` (not `HOME`). "Run as administrator" on the same account keeps `USERPROFILE`; if the operator elevates with a different admin account, `USERPROFILE` is that account's, and step 8 and step 9 still agree because both come from this one process.
- Added to `Invoke-Probe`, before the dry-run return: a `Say` line "the probe reads <ConfDir>\node.yaml (USERPROFILE <x>, the same window and user that step 8 wrote it under)" plus a comment. ASCII only, PS 5.1 syntax (`Join-Path` in parentheses, string concatenation).
- `pwsh` is not installed here: the ps1 change is proven by a static test and the existing ASCII test (the parse test skips without pwsh). The added line was not executed.

## Files Changed
- deploy/join/join.sh — step 9 (`do_probe`): `HOME="$HOME"` in the sudo `env`, dry-run lines, comment.
- deploy/join/join.ps1 — `Invoke-Probe`: dry-run line naming the node.yaml and USERPROFILE, comment.
- tools/infisical_setup.py — `NODE_HOST_RE` `{1,30}` -> `{1,29}` (3-31), comment says why it is a copy.
- lib/db.py — `seed_hosts_from_config()` skips names not declared in `config/hosts.yaml` (reads it via `config.HOSTS_CONFIG`; `yaml` imported lazily next to `lib.config`, so lib.db still imports without PyYAML); docstring.
- docs/ops/hq-join.md — "3 to 32" -> "3 to 31"; new section "How a joined node knows itself" (one paragraph); "(join.sh step 5)" -> "step 8" (node.yaml is written in step 8; the old number was wrong).
- tests/test_w44c_join_followups.py — new, 28 test items (23 pass, 5 skip = the `pg` param, `ORG_TEST_DB_URL` unset).
- docs/reports/task-42aed98f/REPORT.md — this file.

## Commits
- 1419b7d9 — join: step 9 hands HOME to the probe explicitly, dry run names the node.yaml it reads
- 088767df — config: NODE_HOST_RE 3-31, seed_hosts_from_config skips what hosts.yaml does not declare, hq-join doc, w44c tests
- (report commit follows this file)

## Tests
- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (full suite, once, after the last code change; 13 min 55 s, so it ran in the background)
- passed: 5303
- failed: 0
- skipped: 204 (every `pg` param, `ORG_TEST_DB_URL` unset, plus other env-gated ones, as before)
- new file alone: tests/test_w44c_join_followups.py 23 passed, 5 skipped. `shellcheck -s sh deploy/join/join.sh` clean (installed here; the existing shellcheck test ran).
- scripts, run as scripts: `scripts/test_org_tools_registry.py` ALL PASS · `scripts/test_mcp_role_config.py` OK, 0 failure(s) · `scripts/test_tool_parity.py` ALL PASS (exit 0 each)
- Postgres: the seed tests are parametrized `sqlite`/`pg` like test_w41; the `pg` leg did NOT run here (no `ORG_TEST_DB_URL`). Only SQLite is proven. The code path (`upsert_host`) is backend-agnostic, but that is a claim, not an observation.
- Red before green: the new file was run against the unfixed code first: 10 failed (dry-run step 9, probe under sudo, control, ps1 line, NODE_HOST_RE parity, the 32-char boundary, 32-char mint, 3 seed tests). After the fixes: all pass.

What the tests prove:
- `test_dry_run_step_9_names_the_home_and_the_node_yaml_it_reads` (the one the task asked for): real `join.sh --dry-run` with a HOME containing a space; step 9 carries `env HOME=<home> ORG_HOST=node-a`, the node.yaml path, and step 8 names the same file; nothing was called.
- `test_the_probe_reads_the_node_yaml_step_8_wrote_even_when_sudo_resets_home`: join.sh's own `parse_args` + `check_args`, then step 8's `write_node_yaml`, then step 9's real `do_probe`, under a fake `sudo` that resets HOME to a bogus root home before exec. The probe stub runs the real `lib.config.self_host()` in a subprocess. Result `probe: ok host=node-a`, and the recorded sudo line starts `sudo env HOME=<home> ORG_HOST=node-a`.
- `test_the_same_run_fails_when_the_home_is_left_out_of_the_probe_command`: control. The same run against a copy of join.sh with `HOME=` removed prints `probe: FAILED ... not a known host`. So the pass is the pass-through, not a forgiving stub. (Both are skipped as root, where join.sh runs step 9 without sudo.)
- `test_join_ps1_runs_step_9_in_the_window_and_user_that_wrote_node_yaml`: static, see above.
- NODE_HOST_RE: pattern string equals `lib.config.HOST_NAME_RE` (and `hq_join.HOST_RE`), flags equal, 10 boundary names, `mint_node_secret(None, "a"*32)` raises `bad host name` before touching org, and `infisical_setup.py` imports only `sys.stdlib_module_names` (AST check, so the Run Inbox card copy stays safe).
- seed: the hub row for a joined node (`ssh: "node-a"`, heartbeat fields) is identical after a seed while `config.hosts()` holds a different synthesized entry (`ssh: None`); no row is created for an unknown node.yaml host; all three hosts.yaml hosts still seeded with their `config_json`; a node.yaml naming `contabo` seeds from hosts.yaml; a second seed changes nothing.

## Issues / Blockers
- **pg leg not run** (no `ORG_TEST_DB_URL` on this Mac). CI with the `postgres:16` service container should run it; please confirm it is green there.
- `seed_hosts_from_config` reads `config/hosts.yaml` itself (one extra `yaml.safe_load`) because a public "declared hosts" accessor would belong in `lib/config.py`, outside my touches. A `config.declared_hosts()` that `hosts()` also uses would remove the second read; left as a suggestion.
- join.ps1's new dry-run line was not executed (no pwsh on this machine); it is a plain `Say` with string concatenation and the ASCII + structure tests pass.
- Display only: the dry-run line prints `HOME=<path>` unquoted, so a home with a space reads as two words on screen. The command actually run quotes it (`HOME="$HOME"`); the test uses a spaced home to prove that.

## Notes for Reviewer
- Only `do_probe` changed in join.sh; ORG_HOST stays (it is what tells the probe which host it is; `_env_host` resolves it through `hosts()` now that node.yaml is visible).
- lib/db.py: `if name not in declared: continue`. Existing seed tests patch `config.hosts` with `mac`/`contabo`, which hosts.yaml declares, so they pass unchanged; a test that patched in a name hosts.yaml lacks would now see it skipped (none exists).
- Docs: one paragraph under a new heading in docs/ops/hq-join.md, facts from lib/config.py (entry keys, validation, hosts.yaml wins, resolution order, bad node.yaml behaviour). Also corrected "(join.sh step 5)" to step 8.
- No live contact: join.sh was only dry-run or sourced with fakes; no real sudo, no network; `~/.config/mooniex/*` and `config/hosts.yaml` untouched.

## Skill learning
- MISSING [CXO_Protocol_DevSpawn §kickoff brief] : the brief did not list the touch paths, so I had to judge that `lib/config.py` (a `declared_hosts()` accessor) was out of bounds. A follow-up brief should list its touch paths, or say which obvious file is not one · evidence: task-42aed98f, seed_hosts_from_config decision
- COSTLY [no owner] : the full pytest suite takes about 14 min here (5303 tests), longer than the 10-min Bash cap, so it must run in the background and be waited on. A brief that says "full suite once at the end" should say to use `run_in_background` · evidence: task-42aed98f, task bw40io5xu moved to background at 600 s
- COSTLY [no owner] : GateGuard fires once per new file for Edit and Write, and stating the four facts before the call does not clear it (measured again on `tools/infisical_setup.py`: facts first, still blocked; facts after the error, passed). Budget one round-trip per file · evidence: task-42aed98f, 6 files
- MISSING [CTO_Gate_MergeChecklist §tests for shell scripts] : a test of a shell step that runs under `sudo` needs a fake `sudo` that resets HOME (like the real one) plus a control run with the fix removed; a fake that only records the call proves the text, not the behaviour. Worth a field note for any future join.sh/join.ps1 change · evidence: tests/test_w44c_join_followups.py `_fake_bin` and the control test
