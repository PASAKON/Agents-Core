# REPORT task-3d392ab3

## Summary

Landed WINDOWS CTO's `winbox/cto-parity` branch (6edac472) via cherry-pick,
reviewed it as owned code, then ported `scripts/cxo-claude.sh` (498 lines,
bash) to `windows/cxo-claude.ps1` supporting any C-level role
(`-Role cto|cmo|cgo|cfo`), with `-Session`/`-InitialPrompt`/`-TabTitle` for
the future ephemeral-spawn path (W3.3). `windows/win-cto.ps1` is now a thin
wrapper (`cxo-claude.ps1 -Role cto @args`) so existing shortcuts keep
working. `roles/cto-windows.md` now names the new launcher. Added
`tests/test_cxo_claude_ps1.py` (static checks, no PowerShell needed).

## Step 1 — landing 6edac472 + review

Cherry-picked clean except one conflict in `scripts/lib/cxo_mcp_config.py`'s
`LUNGNOTE_MCP_JS` candidate list: the incoming commit re-added an
`/opt/lungnote-mcp` compat path that commit `e57ac9e2` had already removed
from `main` (the HQ move finished repointing everything to
`/opt/MoonieXHQ/...` before `winbox/cto-parity` branched). Resolved by
keeping the winbox candidate path and dropping the stale compat path.

Defects found reviewing 6edac472 as owned code (all fixed by folding the
logic into the new generalized `cxo-claude.ps1` rather than patching
`win-cto.ps1` in place, since the task turns that file into a thin wrapper
anyway):

- `windows/win-cto.ps1:72-74` (pre-generalization) exported
  `CXO_ROLE`/`CXO_SESSION`/`CXO_SESSION_ID`/`CTO_SESSION`/`CTO_SESSION_ID`
  **only inside the hub-mode branch**. A standalone launch (the box's actual
  state pre-W1) had none of these set even though a session id had already
  been generated. Fixed: exported unconditionally in `cxo-claude.ps1`.
- Never generated or passed `--allowed-tools`. `scripts/lib/cxo_mcp_config.py`'s
  own docstring names this failure mode as "G1": a server that loads but
  whose tools aren't allow-listed pays the process+schema cost then prompts
  on every call. Fixed: derived via `--print-allowed`, same generator that
  builds `--mcp-config`.
- `(Test-Path $orgEnv) -and (Test-Path $venvPy)` collapsed two different
  failure reasons into one "standalone: no org-db.env" message — wrong when
  org-db.env exists but the venv doesn't. Fixed: `cxo-claude.ps1` requires
  the venv up front (matching `cxo-claude.sh`'s own hard `source
  .venv/bin/activate` requirement) and only branches on `org-db.env`
  afterward, so the two failure modes can't be conflated.
- No lock file: a second launch under the same role+session id was never
  refused, unlike Mac/Contabo (which always refuse via `kill -0` on a
  stored pid). Fixed: ported the lock file (`Get-Process -Id` as the
  Windows liveness check), the persisted `.uuid` file (hex-suffix
  construction + non-hex fallback), and the `<role>-active` pointer — none
  of which existed in v2.
- Never registered or reconciled against `c_level_sessions`
  (`tools.register_cxo` / `tools.session_reconcile`), so gate 4 could never
  see a Windows CTO session even in hub mode. Fixed: added both,
  backgrounded, hub-mode only.

## Step 2 — windows/cxo-claude.ps1

Ported step-by-step from `scripts/cxo-claude.sh`, keeping every step that
has meaning on Windows in the same order: role display/model/effort/
fallback-model from `policies/agents.yaml` (plus the `is_c_level` guard);
per-role MCP config + tool whitelist from `scripts/lib/cxo_mcp_config.py`
(regenerated fresh, removed on exit); `CXO_*` env (+ `CTO_SESSION_ID` for
cto); session-id pick/override + the `<role>-active` pointer rule (skipped
when `-Session` is given); the persisted `.uuid` file with the id-suffix
construction and non-hex fallback; lock file; log lines.

**`.sh` steps dropped, and why** (winbox has no equivalent for any of
these):
- iTerm window capture via `osascript` (`.winid` file) — iTerm-only;
  `delegate.py` doesn't route Windows CXO tabs by window id the way it does
  iTerm ones.
- tmux session-name adoption for `CXO_SESSION_ID` — winbox never runs tmux;
  a fresh 8-hex id is always generated unless `-Session` overrides.
- `.tty` file + `scripts/tab-title.sh`'s 60s title-keeper loop, plus
  `tools/maintab.py`'s Main Tab (OSC 2 titlebar) seeding and the iTerm
  `HIDE_TAB_BAR_WHEN_ONLY_ONE_TAB` preference push — all iTerm-specific.
  Replaced with a single `$Host.UI.RawUI.WindowTitle` set (Windows Terminal
  reads this for its own tab strip); no keeper loop needed since nothing on
  Windows clobbers it the way zsh precmd / iTerm profile writes do.
- `scripts/idle-ping-watcher.sh` (auto-close an idle ephemeral tab) — polls
  iTerm tab contents via `osascript`; no Windows port exists. An ephemeral
  `-Session` spawn on winbox does **not** auto-close yet. Flagged as a
  follow-up for whoever builds W3.3's ephemeral-spawn path.
- `LUNGNOTE_MCP_NODE` / `/opt/node-v22` override — Contabo-only (its system
  node is 20, lacks native WebSocket); winbox's node is current enough.

**Constraint handling (CEO 2026-09-28, "wait for both W1s")**: standalone
mode (no `%USERPROFILE%\.config\mooniex\org-db.env`) prints one clear log
line each for org MCP and LungNote being skipped, never calls
`cxo_mcp_config.py` at all in that branch (so there's nothing to crash), and
`--strict-mcp-config` is applied in **both** modes (not just hub mode) —
with no `--mcp-config` at all in standalone — so the session can never
inherit another server's half-configured secret from `Agents/.mcp.json` and
prompt for it. This mirrors an existing precedent already in this codebase:
`tools/delegate.py`'s `_render_remote_claude_args` passes
`--strict-mcp-config` with no `--mcp-config` for remote workers "on a box
that can't have org MCP."

`scripts/lib/cxo_mcp_config.py` was touched only inside the conflict
resolution described in Step 1 (one line changed in the `LUNGNOTE_MCP_JS`
tuple); no control-flow changes, so W1.6's ORG_DB_URL work should rebase
cleanly.

`windows/win-cto.ps1` is now:
```powershell
& (Join-Path $PSScriptRoot 'cxo-claude.ps1') -Role cto @PassThroughArgs
```
`roles/cto-windows.md`'s "Two launch modes" section now names
`cxo-claude.ps1 -Role cto` and notes `win-cto.ps1` is a wrapper.

## Files Changed

- `scripts/lib/cxo_mcp_config.py` — cherry-pick conflict resolution:
  `LUNGNOTE_MCP_JS` candidate list keeps the winbox path, drops the stale
  `/opt/lungnote-mcp` compat path already removed on `main`.
- `windows/cxo-claude.ps1` (new) — the generalized C-level launcher.
- `windows/win-cto.ps1` — reduced to a thin wrapper around `cxo-claude.ps1 -Role cto`.
- `roles/cto-windows.md` — names the new launcher.
- `tests/test_cxo_claude_ps1.py` (new) — static checks (param block, no
  iTerm/osascript/tmux, no hardcoded profile path, org/lungnote skip-log
  lines, `--strict-mcp-config` in both modes, env-var export ordering,
  lock/uuid/active-pointer presence, fork-session detection,
  remote-control lookup, memory-sync-before-launch ordering); a
  `pwsh`-gated `ParseFile` check (skipped here — no `pwsh` on this box).

## Commits

- `a7c17486` — winbox: win-cto.ps1 v2 -- Mac C-level launch parity (hub mode gated on org-db.env) [cherry-picked from 6edac472, conflict resolved]
- `b0b33ffb` — windows: generalize win-cto.ps1 into cxo-claude.ps1 for any C-level (Org Mesh W3.2)

## Tests

- ran: `pytest tests/test_cxo_claude_ps1.py -v` — 16 passed, 1 skipped (the
  `pwsh` `ParseFile` check; no `pwsh` binary on this box, skip is clean and
  intentional per the task brief)
- ran: `python scripts/test_mcp_role_config.py` — own summary line: **`OK — 0 failure(s)`**
  (confirms the `cxo_mcp_config.py` conflict resolution didn't break the
  existing per-role MCP split guards)
- ran: `python -m pytest` (full suite, background, no `-q`/`-x` beyond
  `pytest.ini`'s own `-q`) — **4 failed, 2898 passed, 27 skipped** in 295.5s.
  All 4 failures are exactly the task brief's documented pre-existing
  unrelated failures on this box:
  - `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`
  - `tests/test_mesh_check.py::test_check_l0_green_when_sources_agree`
  - `tests/test_worker_naming.py::test_current_host_defaults_to_mac`
  - `tests/test_worker_naming.py::test_current_host_blank_org_host_falls_back_to_mac`
  No new failures introduced.

## Issues / Blockers

- None. Task explicitly scoped out any live/ssh winbox verification (task
  W3.4) and any `config/*.yaml` edits (task W3.0, in parallel) — both
  honored: no ssh calls made, `config/hosts.yaml`/`config/projects.yaml`
  untouched.
- `scripts/idle-ping-watcher.sh` has no Windows port, so an ephemeral
  `-Session` spawn of a C-level on winbox will not auto-close on idle the
  way a Mac/Contabo one does. Not blocking for this task (W3.2 is about the
  launcher existing and running unattended, not the idle-close UX), but
  whoever wires up W3.3's `node_dispatch start_clevel` should know this gap
  exists before relying on auto-close behavior.

## Notes for Reviewer

- The `--allowed-tools` flag is variadic (consumes tokens until the next
  `--flag`), so its position in `$fullArgs` matters: I kept the exact same
  order `cxo-claude.sh` uses (`--mcp-config`, `--strict-mcp-config`,
  `--remote-control`, `--allowed-tools <tools...>`, `--session-id`, fork,
  positional) rather than the order the reviewed `win-cto.ps1` v2 would
  have implied, specifically so `--allowed-tools` is always immediately
  followed by a `--flag`-shaped token and never accidentally swallows
  `--session-id`'s value or the positional prompt.
- `windows/cxo-claude.ps1` requires the repo's `.venv` to exist up front
  (exits 2 with a clear message otherwise) — this is a hardening vs.
  `win-cto.ps1` v2's softer "no .venv yet -- hooks will no-op" tolerance,
  matching `cxo-claude.sh`'s own hard `source .venv/bin/activate`
  requirement on Mac/Contabo. Flagging in case the team prefers v2's softer
  behavior for winbox specifically (e.g. if a fresh box might legitimately
  reach this script before the venv is provisioned).
- Nothing was run live: no `claude.exe`, no ssh to winbox. Everything above
  is static review + the Linux-side test suite.

## Skill learning
- MISSING [ALL_Protocol_SkillAuthor §n/a] : no skill currently covers "porting a bash C-level launcher to PowerShell" (the PS 5.1 ASCII-only constraint, the strict-mcp-config-with-no-mcp-config pattern for a box that can't have org MCP, the ValueFromRemainingArguments pass-through pattern) — this task's own header comments in windows/cxo-claude.ps1 are the only record of these decisions right now. · evidence: windows/cxo-claude.ps1:1-64 (header), windows/spawn-worker.ps1's existing precedent for the same problem class
- COSTLY [no owner] : resolving the scripts/lib/cxo_mcp_config.py cherry-pick conflict required walking `git log -- scripts/lib/cxo_mcp_config.py` to discover that main had already removed the `/opt/lungnote-mcp` compat path (commit e57ac9e2) after `winbox/cto-parity` branched off an earlier commit — a stale-branch conflict that isn't obvious from the conflict markers alone. · evidence: commit e57ac9e2, task-3d392ab3 · prevented by: when reviewing a long-lived feature branch for cherry-pick, check `git log --oneline -- <conflicted file>` on both sides before resolving, not just the diff hunk
- (none) otherwise — CTO_Knowledge_Winbox_DesktopGUI and roles/cto-windows.md already covered the winbox environment facts (profile path derivation, no tmux/iTerm) accurately; nothing there proved false.
