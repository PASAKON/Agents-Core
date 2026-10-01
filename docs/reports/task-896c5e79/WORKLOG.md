# WORKLOG — task-896c5e79 (SomPong = COO, Agents-Core half)

Append-only. Times are UTC.

## 2026-10-01 base, before any edit

- Base = origin/main dfa72f92 (worktree clean). Contract: `docs/design/sompong-coo-session.md`.
- **Base pytest** (`/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q -p no:cacheprovider`, ~25 min, 3 other
  workers on the box): **5924 passed, 373 skipped, 7 failed** (counted from the progress rows: this pytest run
  did not print a totals line). The 7 failures are main's, none touch this task:
  - `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins` (plugins installed on this box)
  - `scripts/test_wiki_multiroot.py::test_namespaced_read` (wiki root not configured for the test)
  - `tests/test_h3_runner_model_launch.py::test_script_org_tools_registry_verdict` (charter-gate warning on stderr)
  - `tests/test_self_host.py::test_local_spawn_writes_host` (RuntimeError)
  - `tests/test_w18_contabo_consumers.py::test_only_the_three_dropins_exist`
  - `tests/test_w31_windows_portability.py::test_lib_config_loads_the_yaml_files_under_a_non_utf8_locale`
  - `tests/test_w31_windows_portability.py::test_delegate_reads_its_policy_file_under_a_non_utf8_locale`
- Base scripts (all rc 0): `scripts/test_org_tools_registry.py` ALL PASS, `scripts/test_mcp_role_config.py` OK 0 failures,
  `scripts/test_tool_parity.py` ALL PASS.

## 2026-10-01 probes with the real claude 2.1.285 (no model call, no paid anything)

A stub MCP server named `sompong` (declares `experimental['claude/channel']`, one tool) in a throwaway tmux
session `probe-stub` (never `sompong`), cwd = a scratch dir. Killed afterwards; no process left.

- `--dangerously-load-development-channels server:sompong` needs a confirmation. Verbatim screen:
  `WARNING: Loading development channels` … `Channels: server:sompong` … `❯ 1. I am using this for local development` / `2. Exit`
  / `Enter to confirm · Esc to cancel`. Option 1 is selected by default. **A stray Down lands on "2. Exit" and Enter then
  ends the session** (this happened to the first variant-B run) — the supervisor presses Enter only after it sees `❯ 1.`.
- After confirming, the banner reads `Channels (experimental) messages from server:sompong inject directly in this session ·
  restart without --dangerously-load-development-channels to stop`, the stub's stdio server was spawned, footer
  `⏵⏵ auto mode on (shift+tab to cycle)`.
- Folder-trust prompt opens on `❯ No, exit`; `Down` → `❯ Yes, I trust this folder`; then Enter.
- `--strict-mcp-config --mcp-config <file outside cwd>` loads the server (so SomPong's `.mcp.json` must be passed explicitly).
- `--add-dir /opt/MoonieXHQ/Agents/Core` makes `/skills` list the org's project skills (ALL_*, CMO_*, CFO_*… 124 total) with a cwd that has none.
- `--settings <file>` hooks run: a SessionStart hook wrote its log. **`$CLAUDE_PROJECT_DIR` is the session cwd**, not Agents-Core, so
  `"${CLAUDE_PROJECT_DIR:-$PWD}/scripts/hook-*.py"` would point into the SomPong repo. (`/hooks` shows "0 hooks" for
  `--settings` hooks even though they fire — the menu only lists settings files.)
- Gap this closes: with cwd = SomPong, Agents-Core's project hooks (mailbox drain `hook-inbox.py`, secret-env guard, …) and
  `.claude/skills` do not load. Launcher therefore adds `--add-dir "$ROOT"` and a generated `--settings` carrying the org hooks.
