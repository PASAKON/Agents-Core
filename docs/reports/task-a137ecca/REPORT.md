# REPORT task-a137ecca

Org Mesh W1.5: every watchdog duty is now split into LOCAL (acts on rows this box runs) and REMOTE (acts on rows this box dispatched), so a shared ledger gives each row exactly one owner per duty.

## Summary
Ownership is decided by predicates in `tools/worker_reap.py` (`is_local_row`, `is_remote_row`, `is_dispatched_here`, `row_host`), and every duty in the watchdog, gc, work_watch, close_remote and branch poller now asks them instead of comparing `host` to `self_host()`. The poller set now includes this box's own codex/agy launcher rows. Full suite is green on both hosts: 3463 passed / 27 skipped / 0 failed, default and `ORG_HOST=contabo`.

## Files Changed
- `tools/worker_reap.py` — new predicates `row_host`, `row_dispatcher`, `is_local_row`, `is_dispatched_here`, `is_remote_row`; `close_remote` also refuses a row dispatched by another host; docstring.
- `runners/watchdog.py` — `scan_once` (local stall, remote stall, blocked_human escalation, finished-DEV reap) and `sweep_terminal_surfaces` (local half, remote half) use the predicates; module docstring.
- `tools/gc_stale_tasks.py` — `_alive_for_gc` and categories 1 / 1b / 2 / 3 use the predicates; docstring.
- `tools/work_watch.py` — `_pid_dead_in_progress` is local-only (no more remote probe via gc).
- `runners/branch_poller.py` — `in_poller_set`, `tick`, `check_task`, `_maybe_close_finished_local_launcher`, `_sweep_review_local_launchers`, `_repo_path_here`, `_fetch_codex_transcript`; docs.
- `tests/test_w15_duty_split.py` — new, 87 tests.
- `tests/test_w04_self_host_sites.py` — updated `test_work_watch_dead_pid_check_is_local_only_for_this_host`: it patched `work_watch._alive_for_gc` (removed) and asserted the old "host != self is remote, ask gc" rule; it now asserts another box's row is never judged from here. No other existing test encoded the old rule; the rest pass unchanged.
- `docs/reports/task-a137ecca/REPORT.md` — this file.
- Not touched, as instructed: `tools/delegate.py`, the `ORG_WATCHDOG_BRANCH_POLL` flag and its default (off; pinned by a test), `tools/disk_queue.py`, `tools/session_reconcile.py`.

## Definitions as implemented
`self` = `lib.config.self_host()`.
- `row_host(t)` = `t.host` or `t.dispatcher_host` or self.
- `dispatcher(t)` = `t.dispatcher_host` or self.
- LOCAL row: `row_host == self`. REMOTE row: `row_host != self AND dispatcher == self`. A row that is neither is skipped: never cancelled, never stalled, never marked dead.

## Duty table (pass, then the row set it acts on)
| Pass | Entry point | Row set |
|---|---|---|
| pid liveness / stall / ping (in_progress) | `watchdog.scan_once` | LOCAL |
| remote stall (ssh) | `scan_once` -> `_check_remote_stall` | REMOTE |
| blocked_human 24h escalation | `scan_once` | dispatcher == self, any host (a status flip + GH issue, no local resource) |
| finished-DEV reap (review/done, Darwin only) | `scan_once` -> `close_dev` | LOCAL |
| terminal-surface sweep, local half (Darwin only) | `sweep_terminal_surfaces` | LOCAL |
| terminal-surface sweep, remote half | `_sweep_remote_terminal_task` -> `close_remote` | REMOTE |
| `close_remote` | `tools/worker_reap.py` | host set, host != self, dispatcher == self |
| gc cat 1 (pending, unassigned) | `gc_stale_tasks` | LOCAL (its pid check and disk_queue exemption read this box) |
| gc cat 1b (pending, assigned, dead process) | `_alive_for_gc` | LOCAL by pid; REMOTE by ssh probe; anything else reads None = never act |
| gc cat 2 (conflict) | `gc_stale_tasks` | dispatcher == self |
| gc cat 3 (rate_limited) | `gc_stale_tasks` | LOCAL or REMOTE (same as 1b); any other row is skipped before the liveness call |
| `release_terminal_task_locks` | `gc_stale_tasks` | unchanged: universal and idempotent |
| work_watch dead-pid | `_pid_dead_in_progress` | LOCAL |
| branch poller | `branch_poller.tick` | POLLER set: in_progress, dispatcher == self AND (host != self OR runner in codex, agy) |
| local launcher close | `tick` review sweep -> `_maybe_close_finished_local_launcher` | review rows, LOCAL, dispatcher == self, runner codex/agy, tmux session still alive |
| session_reconcile | `reconcile` | unchanged: already only c_level_sessions rows with host == self or NULL |
| disk_queue drain | `_drain_disk_queue` | unchanged: `state/disk_queue.jsonl` sits inside each checkout (`ROOT/state`, untracked), so a box can only drain what it queued. Pinned by a test |

Poller behaviour: flips to `review` with the report text for claude, codex and agy alike; a host==self claude/NULL row is not polled. For a local launcher row after the flip there is no `close_remote` and no ssh. `_sweep_review_local_launchers` re-offers review rows each tick (the poller otherwise never looks at `review` rows again), and `_maybe_close_finished_local_launcher` closes the tmux session + ttyd locally only if it is still alive, REPORT.md is on the branch and the newest commit is at least `REVIEW_CLOSE_QUIET_S` (300 s) old. The normal case is that the launcher already killed its own session, and the function returns at the first tmux check.

Two more changes inside `branch_poller.py` that the poller set needs to work on a Contabo hub at all: the repo path is this box's own checkout (`paths.<self>`, then `path`) instead of always the Mac's `path`, and the codex `turn.completed` transcript is read locally for a local launcher row, over `ssh cat` for a Linux spoke, and by the existing Windows path otherwise. Without these a Contabo poller would look for the branch in a Mac directory and every codex row would fail the artefact gate.

## Delegate writes `host` on every spawn path (read only, `tools/delegate.py` not changed)
- Windows remote spawn: `_spawn_remote` `db.update_status(... host=host_name ...)` at tools/delegate.py:1457.
- Linux remote spawn and the local launcher (`local=True`): `_spawn_remote` `db.update_status(... host=host_name ...)` at tools/delegate.py:1561-1565.
- Local Mac spawn: `db.set_fields(task_id, spawned_at=..., host=this_host)` at tools/delegate.py:2156, before `_spawn_local`.
- Paths that start no process (dry-run, disk-floor queueing, refusal, `blocked_host`, failed setup) leave `host` NULL by design; that is the "not spawned yet" case in note 1.

## Commits
- 18d0b9b4 — W1.5: LOCAL/REMOTE duty split by (host, dispatcher_host) at watchdog/gc/work_watch/reap/poller; poller set incl. own codex/agy launcher rows; local-launcher review close
- 106bfaee — W1.5: tests/test_w15_duty_split.py, docstrings for the duty split
- a third commit adds this report (its sha is in the submit_report block)

## Tests
- `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` from the worktree, default host: **3463 passed, 27 skipped, 0 failed** in 289 s.
- Same with `ORG_HOST=contabo`: **3463 passed, 27 skipped, 0 failed** in 283 s.
- `tests/test_w15_duty_split.py`: 87 tests. One fake ledger of 48 rows per status (every host x dispatcher x runner over mac/contabo/winbox/NULL x claude/codex/agy), 16 duties driven through their real entry points with only the process/ssh/tmux/git edges stubbed, run with `self_host` pinned to mac then contabo, compared against an independent reference model. It asserts: at most one box acts per row per duty; exactly one where the row's host (LOCAL duties) or dispatcher (REMOTE duties) is mac/contabo; a winbox row dispatched by contabo is polled by contabo only; a contabo row dispatched by mac is polled by mac only; a contabo-dispatched contabo codex/agy row is in contabo's poller set and the claude row is not; NULL host/dispatcher behave as self on each box; nothing is touched for a row neither box owns. Plus `check_task`, local-launcher close, transcript, repo-path, flag-default, disk_queue and session_reconcile tests.
- Mutation probe (scratch copy, not the worktree): making `is_remote_row` the old `host != self` rule fails 6 of the new tests, so they can fail.

## Issues / Blockers
- None blocking. Three decisions for the CTO, below.

## Notes for Reviewer
1. **NULL host is not literally "self".** The brief says host NULL means self. Read literally, a not-yet-spawned row (host NULL) that the OTHER box dispatched is local on both boxes, so both gc cat 1 passes run on it, and the box that did not queue it cancels it after 30 minutes while it waits in the dispatcher's disk_queue file. Implemented: host NULL -> the row belongs to its dispatcher; dispatcher NULL too -> this box. `(NULL, NULL)` is still "self" on each box. `test_null_host_and_dispatcher_behave_as_self` states this. One line (`row_host` in `tools/worker_reap.py`) flips it to the literal reading.
2. **NULL dispatcher on a shared ledger.** `dispatcher_host` NULL = this box, as specified, so a row `(host=mac, dispatcher=NULL)` reads as "REMOTE, dispatched here" on Contabo. `create_task` always stamps `dispatcher_host` and `scripts/migrate_tasks_db.py --default-host` backfills NULL `host` and `dispatcher_host`, so this should not occur after the W1 migration; only a hand-inserted row would show it.
3. **gc 1b / 3 can cancel a dead row from both ends.** For a Mac-run row dispatched by Contabo, the Mac's pid check (LOCAL) and Contabo's ssh probe (REMOTE) are two separate duties by the brief, so if both find the process dead both cancel. Same target status, the second finds a non-matching status, idempotent. A row with no recorded pid is treated as dead by `_alive_for_gc` before any probe (existing behaviour, left alone).
4. `close_remote` now needs `dispatcher_host` to be this box. It is the one `worker_reap.py` change beyond the predicates, in scope ("only if close_remote needs the local-launcher case"): without the guard a second box on the shared ledger could ssh-kill the worker.
5. `tests/test_w15_duty_split.py` uses a module-scoped fixture, which runs before conftest's per-test autouse isolation, so it unsets `ORG_DB_URL` and points `db.DB_PATH` at tmp_path inside each pass.

## Skill learning
- MISSING [no owner] : the brief's read-list names `org:playbooks/developer.md` and `wiki_read` returned not-found for it, so the role playbook could not be read · evidence: task-a137ecca session start · fix: point the brief template at a path that exists, or add the playbook.
- MISSING [no owner] : the brief's "NULL host means self" and "exactly one owner per duty" contradict each other for an unspawned row dispatched by another box; the worker has to choose and flag it · evidence: `row_host` in tools/worker_reap.py, note 1 above · prevented by: one sentence in the org-mesh design doc saying which box a NULL-host row belongs to.
- COSTLY [no owner] : a module-scoped pytest fixture runs before conftest.py's per-test autouse isolation (`ORG_DB_URL`, `disk_queue.QUEUE_PATH`), so a shared-ledger fixture could reach the real hub on a Mac whose shell carries `ORG_DB_URL` · evidence: tests/test_w15_duty_split.py `_passes_for` · prevented by: a comment in conftest.py naming that ordering.
- COSTLY [no owner] : `hook-cwd-guard` blocks `cd "$VAR"` and the destructive-command gate blocks `rm -rf` even on a fresh scratch directory, which cost two rejected calls building the mutation probe · evidence: session, 2026-09-30 · prevented by: a unique scratch dir name (no `rm`) and `(cd /literal/path && ...)`.
- COSTLY [no owner] : GateGuard clears per file, so each first edit (worker_reap, watchdog, gc_stale_tasks, work_watch, branch_poller, test_w04, the new test file, this report) cost one round; batching two first-edits on an uncleared file left the import edit blocked behind the body edit that succeeded · evidence: session · prevented by: add "never batch first edits on an uncleared file" next to the existing "one error per new file" rule.
