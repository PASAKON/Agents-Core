# task-719e0c56 — Org Mesh W1.6: ORG_DB_URL to every org MCP server through the env-file wrapper

> **Iteration 2 follows this heading and supersedes parts of iteration 1.** Superseded: "wrapper when the env file exists" (now needs the node-file switch too) and the watchdog unit's `EnvironmentFile` (reverted). The iteration-1 text below is kept as written for the record; where it disagrees with Iteration 2, Iteration 2 wins.

## Iteration 2 (CTO-FEEDBACK: the env file is not the cutover)

### Why
The env file exists on the Mac (since 2026-09-18) and on Contabo before any cutover. Wrapping on existence alone would have moved every NEW session to Postgres while the watchdog, the hooks and the CLI stayed on `state/tasks.db`: a split ledger. The switch must be an explicit per-host act.

### What changed
- `scripts/lib/cxo_mcp_config.py` (stdlib only, runs under system `python3`):
  - `hub_is_live()` reads the node file (`~/.config/mooniex/node.yaml`, override `$MOONIEX_NODE_YAML`). Live only when a top-level line matches `^org_db:\s*hub\s*$` after a trailing ` # comment` is stripped. The last `org_db:` line wins.
  - Not live: any other value (`sqlite`, `hubx`, `hub#x`, quoted, empty), an indented or commented-out line, a missing key, a missing file, a directory.
  - `org_db_wrapper()` now needs ALL of: hub live, env file exists (`is_file()`, never opened), wrapper script exists, not Windows. `lib/worker_mcp_config.py` is unchanged in logic and follows through `cxo.wrap_org_entry` (docstring names the switch).
  - `set_org_db(text, value)` is the writer, next to the reader so the grammar lives in one place. It replaces the first `org_db:` line in place, drops later duplicates, appends if absent, removes all on `None`, and keeps every other line byte for byte (`host:` above all). Idempotent.
- `scripts/hub/cutover_flip.py`: step 4 `--apply` also writes `org_db: hub` (via `set_org_db`, path from `node_yaml_path()` so the override name cannot drift). New `--rollback` (with `--apply`) removes the line and leaves the plists alone. Dry-run prints the diff and writes nothing. A missing node file is created holding only the switch.
- `scripts/hub/cutover-mac.sh`: step-4 text names the node-file line, says the env file alone is not the switch, and says running sessions and workers keep their old MCP config until they restart. Summary and rollback text name `cutover_flip.py --rollback --apply`. `bash -n` clean.
- `deploy/systemd/mooniex-watchdog.service`: back to 9631849f except the comment's last sentence, which now reads "ORG_DB_URL for the Postgres hub reaches this unit at Contabo's own cutover (W1.8), through a systemd drop-in, not this file." No `EnvironmentFile`.
- `tests/test_w04_self_host_sites.py`: back to 9631849f (`git diff 9631849f` is empty); it pins "no EnvironmentFile" again.
- `conftest.py`: the autouse fixture now also pins `MOONIEX_NODE_YAML` to a nonexistent tmp file.
- `tests/test_w16_org_db_injection.py`: rewritten, 57 tests (was 16; 51 for the switch, `set_org_db`, `cutover_flip`, plus 6 for mesh_check added in 2b). Fake env file and fake node file in `tmp_path` only; the real env file and real node file are never opened, and an autouse fixture points both overrides at missing files.

### Tests added (the CTO's list)
- Env file present, switch absent: both generators return today's plain entry byte for byte (the case that matters most). Also a node file with only `host: mac`.
- Both present: wrapped, no secret and no `ORG_DB_URL` in any generated JSON. Switch present, env file absent: plain. Wrapper script missing: plain. Windows: plain.
- 14 non-live node files (`sqlite`, commented, `hubx`, `xhub`, indented, nested, quoted, `hub#x`, empty, last-line-wins to `sqlite`, empty file, more) are plain. 7 live spellings (trailing comment, CRLF, no final newline, `sqlite` then `hub`, extra spaces) are wrapped. Default paths under a fake `$HOME` with both overrides unset.
- `set_org_db` unit tests: replace in place, no duplicate, `host:` kept, append with and without a final newline, remove, idempotent.
- `cutover_flip` (tested on a tmp copy, never the real cutover, plists and node file in tmp): dry-run leaves the node file byte-identical and prints `+org_db: hub`. `--apply` is idempotent, never duplicates, keeps `host:` and `hq_root:`, and replaces an existing `org_db: sqlite`. `--rollback` dry-run is a no-op. `--rollback --apply` removes the line and leaves the plists. The line `--apply` writes is exactly the one `hub_is_live()` reads. The tracked files are never touched in any of the four modes.
- `cutover-mac.sh` parses (`bash -n`) and carries the restart sentence and the rollback command.

### Tests run (from the worktree, main checkout's interpreter, no `-q`) — final, after iteration 2b
- `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings`, default host: **3433 passed, 27 skipped** in 249.21s, exit 0.
- Same with `ORG_HOST=contabo`: **3433 passed, 27 skipped** in 236.98s, exit 0.
- `.venv/bin/python scripts/test_mcp_role_config.py` standalone: `OK — 0 failure(s)`, exit 0.
- Baseline before any iteration-1 edit: 3376 passed, 27 skipped. 3376 + 57 (new file) = 3433; no other test changed.
- Before 2b (mesh_check blocked) the same runs gave 3427 passed, 27 skipped on both hosts (51 tests in the new file); 2b added 6.

### `tools/mesh_check.py:340` and `:436` (iteration 2b, DONE: was BLOCKED)
`.org-task.json` in the worktree held the first 7 touches and `self_repo_guard` reads it before tasks.db; the CTO refreshed it and the edit went through (commit db72fc67).
- `import importlib.util`; new `_org_server_launch(root, python)` after `_venv_python`. It loads `scripts/lib/cxo_mcp_config.py` by path (the same way `lib/worker_mcp_config.py` does, from mesh_check's own `ROOT`) and returns `_build("org", str(root))`'s `command` and `args`. The plain `python -m runners.cto_mcp_server` launch is used only when that generator file is MISSING (a peer box that has not pulled it, or the piped-over-ssh run) or `_build` returns `None`. Any error inside the generator propagates.
- `check_l2` and `run_l3_probe` now build `StdioServerParameters(command, args, cwd, env)` inside their existing `try:`. A generator error is therefore a red cell (`RuntimeError: ...` in the reason), never a silent probe of the wrong ledger. `env` is unchanged (`os.environ` + `PYTHONUNBUFFERED`, plus `CTO_SESSION_ID` in L3); `ORG_DB_URL` is still never put into it by mesh_check.
- 6 tests in `tests/test_w16_org_db_injection.py`, fake env file and fake node file only: `_org_server_launch` returns the wrapper with switch on + env file, plain with the env file and no switch; `check_l2` with a fake MCP client that records the params passes the wrapper (command, args, cwd, no secret) with the switch on and plain params with it off; a missing generator file falls back to plain; a generator that raises turns `check_l2` red and never starts the client. `tests/test_mesh_check.py` (32 tests) passes unchanged. L3 shares `_org_server_launch` and the same try-block shape; it is covered through the helper, not through a live probe (L3 creates real tasks and is `--live` only).
- Files Changed adds: `tools/mesh_check.py` (helper + 2 call sites), `tests/test_w16_org_db_injection.py` (+6, now 57).

### For Contabo's own cutover (W1.8, not built here)
Write `org_db: hub` into `/root/.config/mooniex/node.yaml` (the same line `cutover_flip.py` writes on the Mac) and give the watchdog unit `ORG_DB_URL` through a systemd drop-in (`EnvironmentFile=`), not through the tracked unit. Until both are done, Contabo sessions stay on SQLite by design.

## Summary
The two MCP config generators now start the org server through `scripts/hub/with-org-db-env.sh` when the hub env file exists on the host, so `ORG_DB_URL` reaches the server at spawn time with nothing written into any config or tracked file. `cutover_flip.py` no longer edits tracked files (only the two untracked launchd plists), and the watchdog systemd unit gets an optional `EnvironmentFile`.

## Files Changed
- `scripts/lib/cxo_mcp_config.py` — new `org_db_wrapper(root)` and `wrap_org_entry(entry, root)`; `_build("org")` returns `wrap_org_entry(<today's entry>, root)`. Wrapper chosen only when: env file exists (`$MOONIEX_ORG_DB_ENV`, else `~/.config/mooniex/org-db.env`; `is_file()` only, never opened) AND `<root>/scripts/hub/with-org-db-env.sh` exists AND `sys.platform != "win32"`. Then `command = <wrapper>`, `args = [<venv python>, *today's args]`, same cwd/env. An entry whose command basename already is the wrapper is returned untouched. `ORG_DB_URL` is never put into `env`.
- `lib/worker_mcp_config.py` — `generate()` calls `cxo.wrap_org_entry(servers["org"], root)` after the template is retargeted (reuses the helper already loaded by path; no copied logic). Docstring updated.
- `scripts/hub/cutover_flip.py` — removed the `config/cto.mcp.json`, `config/worker.mcp.json` and `scripts/cto-claude.sh` SOURCE_BLOCK edits (`MCP_FILES`, `CTO_CLAUDE_SH`, `ANCHOR`, `SOURCE_BLOCK*`, `_flip_mcp_json`, `_flip_cto_claude_sh`, unused `json` import). The two plist flips are unchanged.
- `scripts/hub/cutover-mac.sh` — step-4 wording and the end-of-run summary/rollback text no longer say the tracked files are edited; they say the generators do it and that running sessions keep their old MCP config until restart.
- `deploy/systemd/mooniex-watchdog.service` — added `EnvironmentFile=-/root/.config/mooniex/org-db.env`; replaced the "arrives with W1.6" comment.
- `tests/test_w16_org_db_injection.py` — new, 16 tests (below).
- **Outside the brief's touch list, both needed:**
  - `tests/test_w04_self_host_sites.py:498` — asserted the watchdog unit has NO `EnvironmentFile` (W0.4's "until W1.6" pin). It now asserts exactly one, `EnvironmentFile=-/root/.config/mooniex/org-db.env`. The required change contradicts the old assertion.
  - `conftest.py` — new autouse fixture `_no_real_org_db_env` pins `MOONIEX_ORG_DB_ENV` to a nonexistent tmp file. Without it `tests/test_w03_self_host_spawn.py::test_mac_generated_worker_mcp_config_parses_equal_to_the_template` failed on this Mac (the real env file exists here) while passing on a box without it. Same reason `ORG_DB_URL` is already scrubbed in that file.

## Commits
- 9deecce6 — W1.6: generators route the org MCP server through with-org-db-env.sh when the hub env file exists
- 8ec2e1f5 — W1.6: cutover_flip stops editing tracked files; cutover-mac.sh step-4 wording follows
- 43ad45ab — W1.6: watchdog unit gets an optional EnvironmentFile for ORG_DB_URL; tests/test_w16_org_db_injection.py
- (report commit follows)

## Tests
- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (worktree, main checkout's interpreter)
  - baseline before any edit: **3376 passed, 27 skipped** (264 s)
  - after, default host: **3392 passed, 27 skipped** in 299.54s, exit 0
  - after, `ORG_HOST=contabo`: **3392 passed, 27 skipped** in 291.72s, exit 0
  - +16 = the new file; 0 failed in every run.
- ran: `.venv/bin/python scripts/test_mcp_role_config.py` standalone (real env file present on this Mac, override not set) → `OK — 0 failure(s)` (both before and after the contabo run).
- `tests/test_w03_self_host_spawn.py::test_generation_keeps_the_org_command_the_cutover_flip_rewrote` stays green, unchanged.
- passed: 3392 · failed: 0 · skipped: 27

`tests/test_w16_org_db_injection.py` (fake env file in tmp_path holding `ORG_DB_URL=postgresql://fake:SENTINEL-W16@127.0.0.1:1/x`; an autouse fixture keeps every test off the real file):
- file present: cxo and worker org entries use the wrapper, args start with the venv python, cwd/env unchanged; `SENTINEL-W16` and `ORG_DB_URL` appear nowhere in the generated JSON (checked on the entry, on `cxo_mcp_config.main()`'s `--out` file, and on the worker config); both generators agree on wrapper + python.
- the env file is never opened (`builtins.open` / `Path.open` guarded for that path — would raise).
- file absent: both unwrapped, `json.dumps` equal to today's literal entry byte for byte; file present but wrapper script missing: unwrapped; default path `~/.config/mooniex/org-db.env` honoured when the override is unset.
- Windows (`sys.platform` patched to `win32`): both unwrapped even with the file present.
- already-wrapped template / entry: unchanged, no double wrap (also with no env file).
- `cutover_flip` on a tmp copy (its `ROOT` derives from `__file__`, plists repointed to tmp): dry-run and `--apply` leave `config/cto.mcp.json`, `config/worker.mcp.json`, `scripts/cto-claude.sh` byte-identical and never mention them; `--apply` still flips the two plists once (idempotent), dry-run does not; the shipped tracked launcher inputs contain neither `with-org-db-env` nor `org-db.env`.

## Consumer inventory (step 3): who reads `config/cto.mcp.json` / `config/worker.mcp.json`
**No launcher passes a tracked file to `--mcp-config`.** Every `--mcp-config` in the repo takes a generated file:
- `scripts/cto-claude.sh:446` (`$MCP_CONFIG`, written at `:51` by `cxo_mcp_config.py`), `scripts/cxo-claude.sh:491` (`:101`), `windows/cxo-claude.ps1:262` (`cxo_mcp_config.py --out`, `:227`), `scripts/mcp-borrow.sh:159` (`cxo_mcp_config.py --servers`).
- Workers: `runners/worker_init.py:184/540` and `runners/worker_resume.py:124` pass `write_for_worktree()`'s `.org-worker.mcp.json`; `config/worker.mcp.json` is read only as the template at `lib/worker_mcp_config.py:30`.
- `config/cto.mcp.json` has no code reader at all; the remaining hits are comments/docstrings (`runners/cto_mcp_server.py:6`, `runners/cto_chat.py:146`, `tools/work_watch.py:29`, `scripts/cto-claude.sh:31`, `scripts/cxo-claude.sh:83`, `scripts/lib/cxo_mcp_config.py`), a tmp fixture write (`scripts/test_spawn_tab_routing.py:563`) and the test argv value `tests/test_worker_naming.py:171`.
- `tools/delegate.py:1229` passes `--strict-mcp-config` with no `--mcp-config` (a no-MCP spawn); root `.mcp.json` has no org server; `.claude/settings*.json` register none. Agents/.mcp.json does not exist on this Mac; `~/.claude.json` was not opened (outside the repo, may hold secrets; both launchers use `--strict-mcp-config`, so it is not consulted).
- The checkout never had the flip applied: neither launcher contains the SOURCE_BLOCK and neither JSON names the wrapper, so nothing to revert.

**Direct, unwrapped launches of the org server that are NOT generated (named, not fixed — outside my file list):**
- `tools/mesh_check.py:340` and `:436` spawn `python -m runners.cto_mcp_server` themselves with the caller's env. They reach the hub only if the caller already has `ORG_DB_URL`. Follow-up: build the params from `cxo_mcp_config._build("org", root)`. **Done in iteration 2b** (see "`tools/mesh_check.py`" above).
- `runners/cto_chat.py` runs the org tools in-process (`create_sdk_mcp_server`), so it needs `ORG_DB_URL` in its own process env.
- `scripts/lib/mcp_call.py` uses `_build()`, so it picks up the wrapper automatically.

## Step 6: how a C-level's own CLI writes reach the hub after cutover
The launcher no longer sources the env file into the `claude` process (the SOURCE_BLOCK never landed and is now gone), so a Bash call such as `python -c "from lib import db; db.update_status(...)"` inherits no `ORG_DB_URL`, falls to the SQLite path, and hits the `state/tasks.db` tombstone directory (fails loudly). Route it through the same wrapper:

    scripts/hub/with-org-db-env.sh .venv/bin/python -c "from lib import db; db.update_status(...)"

The wrapper sources the env file and `exec`s the command; it works for any `lib.db` caller run from Bash (`.venv/bin/python -m tools.…` too). Not built, as instructed. Related consequence for the CTO to decide: the two session hooks that use `lib.db` (`scripts/hook-self-repo-guard.py`, `scripts/hook-log-prompt.py`) run in the `claude` process env, which now has no `ORG_DB_URL`; per their own comments they fail loud / open on the tombstone. If they must see the hub, the launchers would have to `exec` claude under the wrapper, which also puts the secret in every Bash child's environment — a secrets-exposure tradeoff, so I did not do it.

## Issues / Blockers
- None blocking. Two files outside the touch list were edited (`tests/test_w04_self_host_sites.py`, `conftest.py`); both were forced by the change (see Files Changed).
- Bash classifier returned "no verdict" twice on the first attempt; a single retry passed each time. No effect on results.

## Notes for Reviewer
- The wrapper decision is made on the host that generates the config, at generation time. A running session keeps the config it started with; cutover needs a restart of sessions to pick the wrapper up.
- Existence-only check means an env file that exists but is unreadable or malformed makes the wrapper's `source` fail under `set -e`, so the org server would not start (the plain entry would have started, then failed on the hub). Accepted per the brief (never open the file); the wrapper's error is on stderr of the server start.
- `mooniex-watchdog.service`: systemd `EnvironmentFile` parses `KEY=value` lines only (no `export`, no expansion). `deploy/systemd/org-snapshot.service:14` already reads the same path (non-optional), so the format is known to work. Unit not installed or started (files only, W0.5).
- Windows/winbox stays on the plain entry by design (`sys.platform == "win32"`); W3.4 owns it.
- Nothing pushed.

## Skill learning
- MISSING [CXO_Protocol_DevSpawn §brief / touch-list]: a touch list should be built by grepping the tests that pin the OLD behaviour of the thing being changed. This brief's list omitted `tests/test_w04_self_host_sites.py:498` (asserts no `EnvironmentFile`) and `conftest.py` (host-file isolation); both had to be edited anyway · evidence: task-719e0c56, commits 9deecce6 / 43ad45ab
- MISSING [no owner]: a test that asserts generator output must pin any host file the generator now looks at (here `MOONIEX_ORG_DB_ENV` in `conftest.py`); a real `~/.config/mooniex/org-db.env` made one existing test pass on Contabo/CI and fail on the CEO's Mac · evidence: `tests/test_w03_self_host_spawn.py::test_mac_generated_worker_mcp_config_parses_equal_to_the_template`, commit 9deecce6
- COSTLY [no owner]: the Grep tool (ripgrep) skips dotfiles, so a consumer inventory misses `.mcp.json` and `.claude/` unless repeated with `grep -rI` · evidence: this task's step-3 inventory; prevented by: run both, or state the dotfile gap in the report

Iteration 2:
- WRONG [CXO_Protocol_DevSpawn §brief / cutover switch]: "wrap when the env file exists" was treated as the cutover signal, but the env file predates the cutover on every host (Mac since 2026-09-18, Contabo too). Existence of an input file is not a per-host switch; it splits the ledger · evidence: task-719e0c56 CTO-FEEDBACK iteration 2, commit e111d2b7 · fix: the brief must name the explicit switch (here `org_db: hub` in node.yaml) and say which files must NOT change behaviour when only the input exists.
- MISSING [CXO_Protocol_DevSpawn §touch-list]: when a brief says "follow the same switch everywhere", the touch list must include every non-generated launch site found by the inventory. `tools/mesh_check.py` was named in the iteration-1 report and required in iteration 2, but was not in the declared `touches`, so `self_repo_guard` blocked it until the CTO refreshed the worktree's `.org-task.json` (the guard reads that sidecar before tasks.db, so a ledger-only touches update does not unblock a running worktree) · evidence: task-719e0c56, `tools/mesh_check.py:340,436`, guard refusal, CTO-FEEDBACK 2b · fix: add every inventory hit under `tools/` to `touches` at spawn.
- MISSING [no owner]: the GateGuard Edit gate fires first and `self_repo_guard` second; a GateGuard-only error does NOT mean the path is cleared. Answer the gate and retry once to see the real verdict · evidence: task-719e0c56 (`tools/mesh_check.py`, 2 rounds).
- COSTLY [no owner]: a mutation probe on a source file to prove a test can fail ("delete the gate, expect red") is refused by the auto-mode classifier as Security Weaken, and a scratch dir containing `.venv` is refused by `self_repo_guard` even in the scratchpad · evidence: task-719e0c56, two refused Bash calls · prevented by: prove the guard with a bad input inside a test (the switch-absent and non-live-value cases do), not by editing the source or building a fake `.venv` path.
