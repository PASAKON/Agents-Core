# task-f248ea50 — session names (plan N) + the CEO's 15 Oct ruling + the ghost-suggestion sweep stall

Branch `agent/developer-task-f248ea50`, worker Developer (Sonnet 5.5), for PH#7cf528f0 (OrgRestructure).
Nothing was pushed, deployed or restarted; the live rename service on Contabo still runs the code it had.

## What changed in direction mid-run

PH#7cf relayed a CEO ruling (15 Oct ~06:40 TH, he renamed two live sessions by hand) that supersedes the plan's §N.2 shapes:

| kind | name | cap |
|---|---|---|
| existing C-level / PH | keeps every part; the sweep only adds the host emoji (M10d rule, as at `2fa20adf`) | none |
| new C-level | `🌐 <ROLE> (<Persona>) — <topic>` | none |
| new PH | `🌐 PH#<id3> (<LANE>) - <Project>` | none |
| new worker | `🌐 Dev·S#49b Org: job` (winbox ASCII `Dev.S#49b Org: job`) | 32 after the emoji, `…` counted |
| Watch | `🌐 Watch#a1b Runs: 2🟢` | 32 |

So the first pass (compact C-level/PH, a sweep that rebuilt every off-rule name, launchers writing `CTO#c34 Main`) was
taken back: `tools/rename_service.py`, both launchers, `tools/itermtab.py`, `tools/live_sessions.py`,
`test_spawn_coo`, `test_c_level_roles`, `scripts/test_*` went back to `origin/main`; `lib/session_names.py` was
rewritten (its readers take the old, the compact and the ruling shapes; `rule_problem` has no cap on C-level / PH
and keeps the cap and the `.`/`·` rule for the compact worker shape only).

## Files

- `lib/session_names.py` — ruling writers `clevel_name(role, persona, host)`, `ph_session_name(sid, lane, projects, host)`; compact `worker_name(…, model, windows)` and `watch_name`; `fit` (32 cap, new worker/Watch only); readers and `rule_problem` for all shapes.
- `lib/config.py` — `worker_session_name(…, model)` and `head_short` (reads `short:` in `config/projects.yaml`, else the table, else 10 chars); re-exports.
- `runners/worker_init.py`, `runners/worker_resume.py`, `tools/delegate.py`, `tools/node_dispatch.py` — pass the worker's `model` to the name.
- `lib/pane_screen.py` — `strip_ansi`, `drop_ghost`, `not_ready_reason`; every box predicate reads a capture with attributes.
- `tools/rename_service.py` — `_screen` uses `capture-pane -p -e`; `_blocked` replaces `_ready`; the wait line names its reason. Everything else is the M10d file.
- `roles/{cto,cmo,cfo,cgo,coo,project_head}.md`, `docs/ops/live-sessions.md`, `scripts/session-rename.sh` header — the ruling shapes, the host emoji, the ghost/wait paragraph.
- Tests: `tests/test_pane_screen.py` (new, 23), `tests/test_session_names.py`, `tests/test_rename_service.py`, `tests/test_worker_naming.py`, `tests/test_multihost.py`, `tests/test_delegate_winbox_injection.py`.

## The ghost suggestion (second addition)

- Cause confirmed on the live panes: idle sessions draw `ESC[39m❯\xa0ESC[2m<text>ESC[0m`; `36c49776` draws it in several dim spans split by a plain space (`ESC[2mgoESC[0m ESC[2m…`), which the parser also treats as empty. Plain `-p` shows all of it as typed text.
- Fix as briefed: `-e` capture; escape sequences (SGR, other CSI, OSC 8 hyperlinks) removed; text after the `❯` inside an SGR-2 span is empty, any non-dim visible text is a draft; reset (0, `ESC[m`, 22) ends the span; `38;5;n` / `38;2;r;g;b` arguments are skipped so their `2` is not read as dim; dim state is per row. Busy and choice checks read the text with dim spans kept (the footer hints are dim too).
- Live check (read-only, `-e` captures): `cmo-ef04792e`, `project_head-36c49776`, `project_head-f35affd5` now read ready; before they read "draft".
- **Case 3 (`ESC[38;5;246m❯ ESC[39m` alone) is not a box-reading bug.** Claude Code draws that grey pointer while a turn is running; the footer then says `esc to interrupt`. Seen on three panes today: `wd-f248ea50`, `wd-ed6c77d9` and `project_head-13db8720` itself (right now: grey `❯`, empty box, `_blocked` = "turn running"). The old code was right to refuse; only the log line ("prompt not empty" for all three reasons) was misleading. `13db8720` waited from 01:25:19 and was renamed at 01:54:06 (Contabo clock, CEST), when its turn ended. I made the log say which reason (`prompt not empty` / `turn running` / `choice prompt up`) and did not make the grey pointer itself mean ready or busy: the footer decides. A grey `❯` alone with an idle footer is ready (the brief's fixture); with `esc to interrupt` it is not.
- Not changed, same bug class: `tools/agent_transport.py` (`_wake_tmux_send`), `tools/escalation_watch.py` and `runners/watchdog.py` still capture with plain `-p`, so a ghost suggestion still reads as a draft there (the wake defers, the watchdog may not close). Their tests assert the `capture-pane -p` argv, they are outside the task's `touches`; one-line follow-up each (`-e`).

## Sweep dry run on Contabo (read-only: `rename_service.sweep('contabo', {})`, no tmux write)

| box | name now | sweep would queue |
|---|---|---|
| `cmo-ef04792e` | `CMO (Ging) — CMO Main` | `🌐 CMO (Ging) — CMO Main` |
| `project_head-36c49776` | `PH#36c (CMO) - MimiPage` | `🌐 PH#36c (CMO) - MimiPage` |
| `project_head-f35affd5` | `PH#f35 (CTO) - CookieRun` | `🌐 PH#f35 (CTO) - CookieRun` |
| `cto-c34459eb` | `🌐 CTO (Kavin) — CTO Main` | nothing (on the rule) |
| `project_head-7cf528f0` | `🌐 PH#7cf (CTO) - OrgRestructure` | nothing |
| `project_head-6c487e37` | `🌐 PH#6c4 (CTO) - SpendGuard` | nothing |
| `project_head-13db8720` | `🌐 PH#13d (CMO) - BlackLiquidity` | nothing (the live service added the emoji 01:54:06) |
| `wd-f248ea50` (me) | `🌐 Dev#f24 - OrgRestructure: N: new session-name shape for every role…` | nothing (workers are not swept) |
| COO `fde4c4ca` | `COO (SomPong)` | not reachable: its record has no `tmux` field (it runs under `runuser env -i`), so `session_of` cannot verify it; a relaunch under the launcher names it `🌐 COO (SomPong)` at birth |

Every name comes out unchanged except for the added emoji. The three queued boxes are all `_blocked() == None` on a fresh `-e` capture.

## Tests

- CTO's selection (`-k "session_name or worker_naming or rename or multihost or spawn_coo or delegate or live_sessions or terminal_window"` over `tests/`): **512 passed, 2 skipped, 1 xfailed, 0 failed** (199 s).
- Name/screen files incl. `scripts/test_session_rename.py`, `scripts/test_live_sessions.py`, `tests/test_terminal_window.py`, `tests/test_c_level_roles.py`, `tests/test_spawn_coo.py`: 693 passed, 4 skipped, 1 xfailed.
- After the role-file edits: `test_c_level_roles`, `test_thai_inventory`, `test_nonclaude_worker_contract`, `test_spawn_worker_remote_runners`, the two scripts files, `test_pane_screen`, `test_wake_screen_gate`: 340 passed, 2 skipped.
- Run with `env -u WORKER_TASK_ID -u WORKER_ROLE -u WORKER_CTO_ID -u WORKER_CTO_ROLE`: those leak from the worker's shell into `tests/test_spawn_coo.py::test_send_shares_the_letter_for_coo_but_not_for_other_roles` and fail it with `ArchivedDB`. Environment, not the change.
- Fails without the change: dropping `drop_ghost` fails the ghost cases; removing `-e` fails `test_the_screen_is_captured_with_its_attributes`; rejecting the PH lane shape in `rule_problem` fails 12 N2 cases.

## Merge with #327 (`terminal_window`)

`origin/main` merged into the branch (`2237ea57`) with no conflict; `lib.config.terminal_window`, `config/hosts.yaml mac: terminal_window: false`, `delegate show_window` and the launcher `TERMINAL_WINDOW` all survive (`tests/test_terminal_window.py` green). The launchers are `origin/main`'s, so nothing of the first pass sits next to them.

## Reach of the change (callers, tests)

- `lib/pane_screen` predicates → `tools/rename_service.py`, `tools/agent_transport.py`, `tools/escalation_watch.py` (via rename_service), `runners/watchdog.py`. A capture with no ESC reads exactly as before (`drop_ghost` returns the same object); tests: `test_wake_screen_gate`, `test_rename_service`, `test_pane_screen`.
- `lib/session_names` → `lib/config.py`, `tools/live_sessions.py` (`parse_short`, `strip_host`, `rule_problem` via `_rule_context`), `tools/rename_service.py`, `tools/delegate.py`, `tools/node_dispatch.py` (`windows_safe`), `tools/hook-*` readers of `live_sessions`. `parse_short` now also returns a role for C-level, COO and Watch names, so `live_sessions.parse_name` can give a `watch` role to a name it used to call `unknown`.
- Worker names → every spawn path (`runners/worker_init`, `worker_resume`, `delegate`, `node_dispatch`) and `spawn-worker.ps1` (it gets the rendered string).

## Plan nits

- The plan's example `Dev·S#49b Org: Item 5: sparse wo…` is 33 characters, one over its own 32 cap.
- The plan said a worker's role/model/head come from the task row; the rename service has no hub route (PrivateNetwork). Moot now that the sweep no longer rebuilds workers.
