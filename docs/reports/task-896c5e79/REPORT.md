# REPORT — task-896c5e79: SomPong = COO (Agents-Core half)

Contract of record: `docs/design/sompong-coo-session.md` (unchanged). Sibling: SomPong task-179acf77 (merged, SomPong main
`9f4cee4`). Branch `agent/developer-task-896c5e79`, 6 commits on top of origin/main `dfa72f92`. Nothing installed, enabled or
started; nothing pushed.

## What was built

| # | Deliverable | Where |
|---|---|---|
| 1 | Role wiring: parked branch re-applied (not merged), `coo` row, roster line, memory cap, mailbox | `67946af0`, `cf1f036f`: `policies/agents.yaml`, `lib/roles.py`, `claude-home/settings.json`, `tools/session_cap.py`, `tools/session_name.py`, `tools/send_to_cxo.py`, `runners/relay_mcp_server.py` |
| 2 | Launcher `cxo-claude.sh --role coo` (+ `spawn-cxo.sh` refusal) | `scripts/cxo-claude.sh`, `scripts/lib/coo_host.py`, `scripts/lib/cxo_hooks_settings.py` |
| 3 | `/spawn-coo` | `claude-home/commands/spawn-coo.md`, `scripts/spawn-coo.sh` |
| 4 | Supervisor | `scripts/sompong-supervise.sh`, `deploy/systemd/mooniex-sompong.service` |
| 5 | `roles/coo.md` rewritten | `roles/coo.md` |
| 6 | Tests | `tests/test_sompong_supervise.py` (60), `tests/test_spawn_coo.py` (53), `tests/test_c_level_roles.py` (parked branch's 18 + additions) |

### Parked branch (`origin/parked/coo-wiring` 9617f9f9)
Cherry-picked and resolved by hand where the code had moved (646 commits of drift): the parked branch's coo shim role is
gone; `coo` is now SomPong. `runners/secretary_server.py` untouched. Its 18 tests still pass. The gaps its report listed are
closed: `claude-home/settings.json` roster line, `tools/session_cap.py`, `send_to_cxo(role="coo")` through the normal mailbox.

### Singleton ("never two")
- `lib/roles.py::SINGLETON_ROLES=("coo",)` + `singleton_refusal`: `send_to_cxo --spawn` and the relay's `spawn_c_level` refuse coo
  (audited as "rejected"), pointing at `/spawn-coo`. `--session` on the launcher is refused too.
- `spawn-coo.sh` takes a flock, checks tmux `sompong` for a live `claude` process, and only then starts the unit.
- The launcher refuses a second live coo launcher (`state/locks/coo-*.lock` pid alive + cmdline match).
- tmux name `sompong` (not `coo-<id>`) via `session_name.TMUX_NAME_OVERRIDES`; `send_to_cxo`'s wake nudge targets it.

### Launcher (Contabo only)
Host from `lib/config.py::self_host()` via `scripts/lib/coo_host.py` (exit 3 = unresolved → treated as not-Contabo, fail
closed). Off Contabo: exactly `SomPong (COO) runs on Contabo only — use /spawn-coo`, exit 1. On Contabo: cwd
`/opt/MoonieXHQ/Projects/MoonieX/SomPong`; `--dangerously-load-development-channels server:sompong` (the only form that
works for a `server:` channel on 2.1.285/2.1.286, probed); SomPong's `.mcp.json` as a second `--mcp-config` next to the
strict org one; `--add-dir <Agents-Core>` for the org skills; generated `--settings` with the org hooks (see below);
`--remote-control SomPong`; `SOMPONG_COO_SESSION=1` exported (the family-gate hook is inert without it); registered in
`c_level_sessions` as role `coo`, host `contabo` (asserted in a test).

### Who runs as whom (differs from the brief's first picture — see WORKLOG)
**CEO ruling 16:1x (via the CTO): SomPong runs as the unprivileged `sompong` user; root goes only through the Run Inbox**
(a red card, fresh Face ID on the CEO's phone; `roles/coo.md` tells it to `ask_run` risk red, then `ask_run_wait`
`max_wait_s=900`, cancel its own card after 15 minutes, never sudo). Code default unchanged (CTO 14:05Z): `SOMPONG_USER`
(default `sompong`), root only with `SOMPONG_ALLOW_ROOT=1`, still `env -i` + allowlist (tested: no runuser, no key names).
The launcher keeps `HOME=<sompong's home>` because `ask_run` reads `~/.config/mooniex/run-inbox.token` (0600); a missing
token prints ONE warning line ("SomPong (COO) warning: ... run-inbox.token is missing ...") and the session still starts; the
supervisor copies that warning into the journal. `mcp__org__ask_run` and `mcp__org__ask_run_wait` are in the coo session's
allowed tools (asserted).
The sibling task found the session must not be root (inbox keys are root-only; acceptance probe 5). So:
supervisor + tmux stay **root** (tmux `sompong` must be in root's tmux server — Console, wake nudge, session_gc, session_list
all look there); the launcher does its bookkeeping as root and starts `claude` through
`runuser -u sompong -- env -i <allowlist> claude …`. Mailbox letters are 0600 mkstemp files, unreadable to that user, so
`_share_letter` makes coo letters group-readable (0664 / box 2775, group `secretary`) and the launcher moves unread letters
of a dead session's box into the new one.

### Supervisor
`sompong-supervise.sh` (Type=simple, flock'd, bash 3.2-clean): starts tmux `sompong` running the launcher; restarts when the
tmux session or its `claude` process is gone; **5 launches per 10 min, then waits and logs `CRASH LOOP`** (no hot loop);
answers startup prompts by reading the pane (trust → Down+Enter, "Teach auto mode" → `3`, dev-channels → Enter only when
`❯ 1.` is selected, "New MCP server" → `1`; a login screen is logged, not answered), each with a gap and a budget, never typing into a screen it
cannot classify; runs the launcher's `--dry-run` first so a refusal reaches the journal. `ExecStop` = `--stop`: `/exit`,
grace period, `kill-session`. Unit file is files only.

### `roles/coo.md`
`<channel source="sompong">` tags and their meta; reply only through `reply/skip/send/ask_ceo/history/media`; plain-text
chat format; CEO turn vs family turn (risky family action → `ask_ceo` first; no answer in 10 min = no); money / secrets /
permanent deletion → the CEO even in a CEO turn; routing through `send_to_cxo` with a self-contained brief, worker tasks
through the owning C-level; where it runs and as whom; memory = files. Checked against the merged SomPong repo's
`CLAUDE.md` and its task REPORT so both agree. Model-tier and Skill-learning sections kept.

## Tests

See the task report (`submit_report`) for the final numbers; recorded in WORKLOG.

- Base (origin/main dfa72f92): 5924 passed / 373 skipped / 7 failed. The 7 are main's own, unrelated (list in WORKLOG).
- New tests run only against fakes on PATH (tmux that refuses inexact targets, ps, sleep, systemctl, ssh, runuser, claude):
  no real tmux, systemd, ssh, runuser, claude, and no `create_worktree`.
- Mutation-checked (each reverted): fd 9 leaked into tmux; loose pane target; Enter without a selected-line check; no
  backoff; launcher host guard off; spawn-coo always starts; stray check off; channel flag dropped; `_share_letter` not
  called; route allowed from Contabo; spawn-cxo refusal off.

## Open items for the CTO (deploy and follow-ups)

1. **Deploy prerequisites — none exist on this box.** Unix user `sompong` (SomPong `ops/install-contabo.sh`), its own
   `claude` install + one CEO login as that user, membership of group `secretary`, `SOMPONG_SOCKET_OWNER=sompong`, the Run
   Inbox token at `~sompong/.config/mooniex/run-inbox.token` (0600; warning only if missing), `state/tasks.db` shared (item 2).
   `id sompong` fails today; the launcher says so ("SomPong (COO) cannot start: unix user sompong missing") and the
   supervisor logs it instead of looping. The unit is **not** installed, enabled or started.
2. **What fails for an unprivileged session user today (probed as uid `nobody`, fixtures in /tmp, nothing real touched):**
   - **The org MCP server does not start** when the user can read but not write `state/tasks.db`:
     `runners/cto_mcp_server.py` calls `db.init()` before serving, `lib/db.py _connect()` runs `PRAGMA journal_mode=WAL`, and a
     WAL database needs a writable `-shm` beside it → `sqlite3.OperationalError: attempt to write a readonly database`, exit 1,
     **no org tools at all, `ask_run` included** (so the Run Inbox path below cannot work either). Pinned by a strict-xfail test
     (`test_org_mcp_server_starts_and_lists_its_tools_for_a_uid_that_can_only_read_the_db`); it turns into a failure the day
     it starts working, so it must then be un-xfailed. Production `tasks.db` is root:root 0644.
   - **Works** once `state/` (2775) and `tasks.db` (0664) are shared with the session user's group: 25 tools listed, `ask_run`
     and `ask_run_wait` among them (passing test `..._for_a_uid_that_can_write_the_shared_db`). Sharing a live WAL database
     between users is fragile (the `-wal`/`-shm` files belong to whoever created them): the tasks hub is the real fix.
   - **`mailbox.send` into another role's box fails**: boxes are root-owned 0755 and the letter is a `mkstemp` file →
     `PermissionError` as `sompong`, so `send_to_cxo` from SomPong cannot reach the CTO/CMO/... until the boxes are
     group-writable (`lib/mailbox.py`, not in this task's touches; not probed further, no test). The Run Inbox result letter the
     hub writes into SomPong's own box is 0600 root and unreadable to it, but `ask_run_wait` polls the hub over HTTP, so the
     15-minute wait does not depend on that letter.
   - The role file already tells SomPong to route through a C-level, so it stays inside the contract, but the routing tool
     cannot deliver until the two permission points above are fixed at deploy (or in `lib/mailbox.py`/`lib/db.py`).
3. **Follow-ups done after the guard was fixed (CTO 14:05Z):** `tools/node_dispatch.py` (`_clevel_session_live` asks
   `tmux_name`, so a Mac→Contabo letter to coo is not refused as "no live session") and `tools/session_gc.py`
   (`reconcile` matches a live `coo-<id>` lock with tmux `sompong`, no false ORPHAN), each with tests, mutation-checked.
   **Still open, other owners:** `lib/mailbox.py` (relay_to_session and mesh `deliver_letter` write 0600 letters: a
   group-readable letter for singleton roles would replace `_share_letter`); MoonieX Console `src/tmux/names.js` has no
   cgo/coo (other repo); `windows/cxo-claude.ps1` has no coo refusal (cannot run here).
4. **Not reproduced by me:** the exact text of the "Teach auto mode" and "New MCP server" dialogs (taken from the brief and the
   sibling's WORKLOG). The classifier needs a phrase plus the menu line, so a changed layout means no keystroke, never a
   wrong one. The trust and dev-channels screens are from my own probe on 2.1.285. claude drifted to 2.1.286 during the task.
5. Dynamic remote-control tests (`scripts/test_session_remote_control.py`) skip in this worktree: they need a worktree `.venv`
   and the self-repo guard blocked creating one. `--remote-control` is the one literal in `cxo-claude.sh`, as that test requires.
6. The sibling's open risks 1, 6, 9 also apply (non-root not enforced in code on their side; hook "ask" under
   bypassPermissions unverified; a non-root session user not exercised live).
