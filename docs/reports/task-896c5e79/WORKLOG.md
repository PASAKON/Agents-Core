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

## 2026-10-01 design: who runs what (read the sibling's REPORT before settling this)

SomPong task-179acf77 (merged on SomPong main 9f4cee4) says in its REPORT "Open risks" 1: the session must NOT be root
(`SOMPONG_COO_SESSION=1` + non-root; the inbox's keys, `state/inbox.db` and its env are root-only), and the contract's
acceptance probe 5 says the session cannot read the inbox keys. Contabo's other sessions are all root, so a plain
`cxo-claude.sh --role coo` under a root supervisor would have broken that. Settled shape:

| piece | runs as | why |
|---|---|---|
| `mooniex-sompong.service` + `sompong-supervise.sh` | root | tmux `sompong` must live in **root's** tmux server: MoonieX Console, `send_to_cxo`'s wake (`tmux send-keys`), `session_gc`, `session_list` all look there; another user's tmux server is invisible to them |
| `cxo-claude.sh --role coo` bookkeeping (lock, `c_level_sessions` row, mailbox box, temp MCP/hook files) | root (the launching user) | same files every C-level launcher writes |
| `claude` itself | `runuser -u sompong -- env -i <allowlist> claude …` | unprivileged, empty environment; allowlist = HOME USER LOGNAME PATH TERM LANG ORG_HOST SOMPONG_COO_SESSION WIKI_ROOT_* DISABLE_AUTOUPDATER CLAUDE_CODE_* CXO_ROLE/SESSION/SESSION_ID (+ LUNGNOTE_MCP_NODE) |

Consequences handled in code:
- A letter from a C-level is written by `mailbox.send` as a 0600 mkstemp file in a 0755 box; SomPong's user could not
  open it and the mailbox hook skips unreadable letters. `tools/send_to_cxo.py::_share_letter` (coo only) chmods the letter
  0664 and the box 2775; the launcher creates the box 2775 (group `secretary`, which owns `state/`, mode 2775) and moves
  unread letters of a dead session's box to the new one (each launch is a new id: `register_cxo_session` upserts on
  (role, session_id) without resetting status, so a stable id was rejected).
- cwd = the SomPong repo, so Agents-Core's project hooks and `.claude/skills` would not load: the launcher adds
  `--add-dir $ROOT` (org skills; probed) and a generated `--settings` carrying the org hooks with the
  `${CLAUDE_PROJECT_DIR:-$PWD}` placeholder replaced by the absolute root (`scripts/lib/cxo_hooks_settings.py`).
  SomPong's own project hook (family gate) still loads: Claude Code merges hooks from every source.
- the supervisor runs `cxo-claude.sh --role coo --dry-run` first (host, repo, `.mcp.json`, unix user, that user's claude,
  hooks file) so a refusal reaches the journal instead of dying inside a pane nobody reads.

**Deploy prerequisites (the CTO's checklist, none exists on this box yet):** unix user `sompong` (SomPong repo
`ops/install-contabo.sh`, nologin shell is fine, `runuser -u` does not use it); its own `claude` install under
`/home/sompong/.local/bin` (`/root/.local/bin/claude` is not usable by another user) and ONE CEO login as that user;
membership of group `secretary`; `SOMPONG_SOCKET_OWNER=sompong` for the inbox. Not exercised live (the user does not exist).
**Unresolved:** `state/tasks.db` is root:root 0644, so a non-root session can read but not write it: org tools that write
(create_task, delegate, merge) will fail for SomPong until the DB is shared or the hub (tasks.db → Contabo Postgres) is in
place. The role file tells SomPong to route through a C-level anyway, which is the contract's rule.

## 2026-10-01 tmux 3.4 semantics (private server, `TMUX_TMPDIR=/tmp/sp-supprobe`)

- `has-session` / `kill-session` / `list-panes` take `-t =name`; `capture-pane` / `send-keys` / `display-message` need
  `-t =name:` (with `-t =name` alone: "can't find pane"). A bare `-t sompong` prefix-matches `sompong-anything`.
- A real `claude` process shows comm `claude`; the launcher is a bash parent, so "alive" means a `claude` anywhere in the
  pane's process tree (BFS over `ps -e -o pid=,ppid=,comm=`), not the pane pid.
- Socket paths over ~108 characters fail: the probe dir had to be `/tmp/sp-supprobe`, not the scratchpad.
- The supervisor sim with a fake launcher on that private server: start → trust prompt answered → dev-channels prompt
  answered → "SomPong is up"; kill claude → restart; `SOMPONG_MAX_RESTARTS=3` → "CRASH LOOP: 3 launches in the last 60s —
  waiting 10s"; `--stop` ends the session and the supervisor exits; no process left over.

## 2026-10-01 launcher verification

Fixture root (symlinks to the code, private `state/`, `ORG_ROOT` pointing at an empty dir so the DB write lands there), a
fake `claude` that records argv/env/cwd, a fake `runuser`. Result recorded as tests (tests/test_spawn_coo.py): refusal text is
exactly "SomPong (COO) runs on Contabo only — use /spawn-coo" for mac, winbox, an unresolved host, with and without
`--dry-run` and `--session`; on Contabo the fake claude got `--dangerously-load-development-channels server:sompong`,
`--mcp-config <SomPong>/.mcp.json` as a second config next to the strict org one, `--add-dir <root>`, `--settings`,
`--remote-control SomPong`, cwd = the SomPong dir, and only the allowlisted environment.

Claude version drift: probes ran on 2.1.285; the box auto-updated to 2.1.286 during the task (the sibling saw the same
and verified 2.1.285 and 2.1.286). The dialog texts for "Teach auto mode" and "New MCP server found in this project" were
NOT reproduced by me: they come from the task brief (answer `3`) and the sibling's WORKLOG; the classifier keys on a
phrase plus the menu line (`Enter to confirm` / `1. Use this MCP server`), so a changed layout means "no answer typed",
never a wrong one. The trust and dev-channels screens are from my own probe.

## 2026-10-01 undeclared touches (self-repo guard, ADR 0020) — NOT done, listed for the CTO

- `tools/node_dispatch.py` ~L1026: `_session_live(session_name.lock_basename(role, sid))` should be `tmux_name(role, sid)`.
  Without it a Mac→Contabo cross-host letter to coo is refused at `deliver_letter` ("no live session") because the tmux
  session is `sompong`, not `coo-<id>`.
- `tools/session_gc.py` `reconcile`: treat `session_name.TMUX_NAME_OVERRIDES` values as matched, else tmux `sompong` is
  reported as an ORPHAN session (and a coo lock as having no tmux).
- MoonieX Console `src/tmux/names.js` has no cgo/coo (another repo).
- `relay_to_session` and the mesh `deliver_letter` write 0600 letters too: a `lib/mailbox.py` follow-up (create letters
  group-readable for singleton roles) would replace `_share_letter`.

## 2026-10-01 tests

New: `tests/test_sompong_supervise.py` (60), `tests/test_spawn_coo.py` (53). All on fakes on PATH (tmux that refuses inexact
targets, ps, sleep, systemctl, ssh, runuser, claude): no real tmux/systemd/ssh/runuser/claude, no `create_worktree`.
Mutation checks (each reverted, tests failed as they should): fd 9 leaked into tmux; loose pane target; Enter without the
selected-line check; no backoff; launcher host guard off; spawn-coo always starts; stray check off; channel flag dropped;
`_share_letter` not called; route allowed from Contabo; spawn-cxo refusal off.
Traps hit: `$PREFLIGHT` unquoted was word-split (a shell one-liner as the preflight silently ran as `echo`) → `bash -c`;
`spawn-cxo.sh`'s coo refusal sat after the role-doc check, whose Mac-absolute ROOT does not exist on Contabo → moved above.

## 2026-10-01 full suite at f3d53a95 (before the CTO's session-user change)

`/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest` (env -u WORKER_TASK_ID, WIKI_ROOT_* set): **6 failed, 6057 passed,
373 skipped** in 19m40s. Base was 5924 passed / 373 skipped / 7 failed. The 6 failures are all on the base list (skill
visibility, wiki multiroot, h3 registry verdict, w18 dropins, the two w31 locale tests); the 7th base failure
(`tests/test_self_host.py::test_local_spawn_writes_host`) passed this time, so there is no new failure. Scripts at the same
commit: `scripts/test_org_tools_registry.py` ALL PASS, `scripts/test_mcp_role_config.py` OK 0 failures,
`scripts/test_tool_parity.py` ALL PASS. The full-launch test now also asserts the `c_level_sessions` row (role coo, host
contabo) and `SOMPONG_COO_SESSION=1` in the claude env; `--permission-mode auto` is asserted (CTO letter 11:23Z: already true).

## 2026-10-01 CTO letter 12:24Z: session user = SOMPONG_SESSION_USER, default root — NOT APPLIED, two blocks

Contract change read (origin 76229c79, "Session user"). Requested: session user is a setting `SOMPONG_SESSION_USER`
(default root); root → no runuser, no "unix user missing" refusal, still `env -i <allowlist>`; `_share_letter` only for a
non-root user; keep the non-root path and its tests; plus 3a (`node_dispatch` uses `tmux_name`) and 3b (`session_gc`
counts `TMUX_NAME_OVERRIDES`).

1. **Launcher change denied by the auto-mode classifier** ("Security Weaken": the edit to `scripts/cxo-claude.sh` removes the
   launcher's "SomPong must not run as root" refusal). Nothing was written (tree clean at f3d53a95). I did not retry in pieces
   or by another route, and I left every part that depends on it undone so the tree stays consistent (`_share_letter`
   gating, `roles/coo.md` "unprivileged user" wording, unit comments, the launcher tests, the supervisor's login message).
   Needs the user's explicit go (a Bash permission rule) or the CTO applying that hunk itself.
2. **3a / 3b rejected by the self-repo guard (ADR 0020):** the guard's declared-touches list for task-896c5e79 still does not
   contain `tools/node_dispatch.py` or `tools/session_gc.py`; the CTO's "now in your touches" has not reached the task row.
   Not worked around. Needs those two paths added to the task's `touches`.

Ready as soon as both are cleared (all small): node_dispatch L1026 `session_name.tmux_name(role, sid)`; session_gc
`reconcile` builds `tmux_set` from `ROLE_RE` matches plus `TMUX_NAME_OVERRIDES` values and compares each lock with
`tmux_name_for_stem(stem)` (tmux_only = tmux_set − matched tmux names); tests for both (coo lock + tmux `sompong` = matched;
tmux `sompong` alone = tmux_only; live coo lock without tmux = orphan; `_clevel_session_live("coo", sid)` asks tmux for
`sompong`). Launcher: `SOMPONG_SESSION_USER` replaces `SOMPONG_USER`/`SOMPONG_ALLOW_ROOT`; the existing non-root tests move
to `SOMPONG_SESSION_USER=nobody`; new root-default tests (no runuser, allowlist env, no group-writable box).

## 2026-10-01 CTO letter 14:05Z: guard fixed; session user stays as it is

- Self-repo guard: the task's sidecar now carries `tools/node_dispatch.py` and `tools/session_gc.py`. Done: **3a**
  `node_dispatch._clevel_session_live` asks `session_name.tmux_name(role, sid)` (coo → `sompong`); **3b**
  `session_gc.reconcile` counts `TMUX_NAME_OVERRIDES` values as C-level tmux sessions and compares each lock with
  `tmux_name_for_stem(stem)` (a live SomPong = matched; `tmux_only` = tmux names matched). Tests (tests/test_spawn_coo.py):
  liveness asks tmux `sompong` / `cmo-<id>`; coo lock + tmux `sompong` matched, with an unrelated session ignored; live coo
  lock without tmux = orphan; `coo-<id>` as a tmux name is NOT SomPong's (tmux_only + orphan); tmux `sompong` alone =
  tmux_only. Mutation-checked: reverting either source change fails 3 tests.
- Session user: **no change to the launcher** (CTO ruling; the classifier's denial stands). `SOMPONG_USER` (default
  `sompong`) and the `SOMPONG_ALLOW_ROOT=1` opt-in are exactly as before; the `SOMPONG_SESSION_USER` rename is dropped.
  Added `test_root_is_an_explicit_opt_in_and_still_gets_the_clean_env`: with `SOMPONG_USER=root` + `SOMPONG_ALLOW_ROOT=1`
  the launch uses no runuser (no `runuser.log`), `USER`/`LOGNAME` = root, and the claude env is still `env -i` + the
  allowlist (no KEY/TOKEN/SECRET/INFISICAL names; canary values in the launching env never arrive). Skipped unless the test
  runs as uid 0. The refusal without the opt-in is the existing `("root", {"SOMPONG_USER": "root"}, "must not run as root")` case.
- Docs made true under either setting (words only): `roles/coo.md` "Where and as whom you run" (default unprivileged,
  root if the deploy opts in, environment empty either way); the unit file carries the two opt-in lines as COMMENTS with a
  note that it is a CEO decision. The unit stays un-installed.
- Affected tests (node_dispatch, w23 mesh, w33, w35 wire, mesh followups, w27 security, c_level_roles, w25 mesh,
  spawn_coo, sompong_supervise, scripts/test_session_gc.py): 1057 passed.

## 2026-10-01 CEO ruling via CTO 14:15Z: unprivileged sompong; root only through the Run Inbox

- `roles/coo.md` "Where and as whom you run" rewritten: unprivileged `sompong` user, basic commands direct; root work =
  `ask_run` (risk red, role coo, a why the CEO can read on the phone) then `ask_run_wait` `max_wait_s=900`; approved →
  continue; not approved in 15 min → `python3 /opt/MoonieXHQ/Agents/Core/tools/ask_run.py cancel <id>` and tell the asker;
  never sudo; a family turn still needs the CEO's Face ID. The unit's commented root opt-in lines are gone (superseded).
- Launcher: HOME stays the session user's home (already so; now asserted via a fake `getent`); missing
  `~/.config/mooniex/run-inbox.token` = one warning line, session still starts (never reads the file). Supervisor logs a
  `launcher preflight warning:` line when a passing preflight printed one. `mcp__org__ask_run(_wait)` already in coo's allowed
  tools (25 org tools); asserted in the dry-run test.
- Probe + tests for the org MCP server as uid nobody (details in REPORT item 2): read-only DB → server exits at
  `db.init()` (`PRAGMA journal_mode=WAL` → "attempt to write a readonly database"); group-writable DB + state/ → 25 tools
  incl. ask_run/ask_run_wait. Also `mailbox.send` into a root-owned 0755 box as nobody → PermissionError (mkstemp).
- Stopped my own full run (it was on the previous commit) after the CTO's change set; one final full run follows the last edit.
