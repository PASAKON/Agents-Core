# task-1c687904 — Org Mesh W2.3: `lib/mesh.py` + delegate / watchdog / branch_poller wiring

## Files changed

| File | Change |
|---|---|
| `lib/mesh.py` | NEW. `dispatch(host, verb, *args, timeout=None) -> dict`, `enabled()`, `build_argv()`, `MeshUnreachable`. |
| `tools/delegate.py` | `mesh_spawn_worker()` (new, public, sync), `_queued_remote_attempts()`; one gated block at the top of `_spawn_remote`. `_route_runner` / `pick_runner` / `delegate_task` untouched. |
| `runners/watchdog.py` | `_retry_queued_remote()` + a "Sixth-b pass" in `scan_once`; `_mesh_pid_alive()`; `_check_remote_stall` uses it when the flag is on. |
| `runners/branch_poller.py` | `_publish_via_mesh()`, called in `check_task` just before the origin branch lookup. |
| `lib/db.py` | `queued_remote` added to `VALID_STATUS` and `ACTIVE_STATUSES`, with comments (CTO granted the path). Nothing else. |
| `tests/test_w23_mesh_dispatch.py` | NEW. 81 tests, fakes only. |

## What was done

**`lib/mesh.py`.** `enabled()` reads `ORG_MESH_DISPATCH` (1/true/on, default off).
`dispatch()` runs `tools.node_dispatch.dispatch(verb, args)` in-process when `host ==
self_host()`, else `ssh -i ~/.ssh/org_dispatch -o BatchMode=yes -o ConnectTimeout=10
<alias> <verb> <args...>`. Arguments are checked before ssh with node_dispatch's own
rules (`HANDLERS`, `_check_args`, `parse_command` round-trip), not a second copy of the
regexes, and each is `shlex`-quoted. A bad verb/arg comes back as the same refusal dict
the server would give and never reaches ssh. A host that answered "no" returns its
error dict. Timeout, ssh exit 255, `OSError`, non-JSON, or a reply whose `ok` is not a
bool raise `MeshUnreachable`. A host with `ssh: null` (the Mac) raises `MeshUnreachable`
and is never dialled. An unknown host raises `ValueError` (config error, not "unreachable").

**delegate.** With the flag on, `_spawn_remote` for a host that is not this one (and not
`local=True`) sends `spawn_worker <task_id>` through mesh instead of the launcher ssh.
`spawn_worker` needs a `pending` row whose host is NULL or that box, so
`mesh_spawn_worker` puts the row there first. No answer: status `queued_remote`, host
kept, a `delegate_log` line "mesh spawn_worker on <h> unreachable (attempt N): ...", no
raise. The box said no: `failed`, like a failed launcher run, unless the far side already
moved the row. `dry_run` prints `mesh_cmd=<ssh argv>` and sends nothing.

**watchdog.** (a) Once per pass, every `queued_remote` row this box dispatched to another
host gets exactly one `mesh_spawn_worker` retry (`is_remote_row`, so a row another box
dispatched is left alone). A failed pass leaves it queued; attempts are counted from the
`status_queued_remote` events and written to `delegate_log`. (b) Remote liveness:
`pid_alive <task_id>` replaces the ssh `tasklist`/`ps` query. **HEARTBEAT: node_dispatch's
`pid_alive` reply is `{task_id, pid, alive}`; it carries no heartbeat age, so HEARTBEAT
staleness stays on today's path (`read_remote_heartbeat`, ssh cat/type).** Not changed, as
the brief said.

**branch_poller.** With the flag on and `row_dispatcher(task) != row_host(task)`,
`publish_branch <task_id>` goes to the worker's host before the origin branch lookup.
Never raises, never touches the row: no answer or a refusal means "not published yet",
and the lookup that follows reads origin either way. Workers never push.

## Status lists (CTO-FEEDBACK: name every list)

**Touched (2):** `lib/db.py` `VALID_STATUS` and `lib/db.py` `ACTIVE_STATUSES`. One comment
updated (`_TERMINAL_MERGED` note now names `queued_remote`).

**Postgres:** `lib/db_pg.py` has no status whitelist or CHECK (`status TEXT NOT NULL
DEFAULT 'pending'`, no `update_status` of its own). `update_status` validates in
`lib/db.py` before any backend call, so one edit covers SQLite and Postgres. No `.sql`
files in the tree.

**Derived, correct with no edit** (`VALID_STATUS - ACTIVE_STATUSES - {...}`):
`runners/watchdog.py` `TERMINAL_SURFACE_STATUSES` and `tools/worker_reap.py`
`_TERMINAL_SURFACE_STATUSES` now exclude `queued_remote`. `RELEASING_STATUSES` does not
list it, so path locks stay held while queued. A test pins all three.

**Checked and left alone (out of scope, none blocks the feature):**
- `tools/terminal_restart.py` `LIVE_STATUSES` (pending/in_progress/rate_limited/blocked_human): a queued row has no tab or process to protect.
- `scripts/session_tree.py` status map + `ACTIVE`, `tools/itermtab.py` tab-colour map, `lib/reflect.py` `_OPEN_CONCERN`: display only. A `queued_remote` row falls through to each one's default.
- `tools/gc_stale_tasks.py`: cancels stale pending/conflict/rate_limited only. A `queued_remote` row is never GC'd (see Notes: no retry cap).
- `scripts/hq_migrate_step4b.py` `GATE_STATUSES`, `tools/delegate.py` `_BROWSER_OPERATOR_ACTIVE_STATUSES`: unrelated to remote spawn.

## Tests

- `.venv/bin/python -m pytest -p no:warnings` (default host): **3764 passed, 27 skipped, 0 failed** in 298 s.
- `ORG_HOST=contabo .venv/bin/python -m pytest -p no:warnings`: **3764 passed, 27 skipped, 0 failed** in 301 s.
- Baseline before my new file (flag off, same command): 3683 passed, 27 skipped. 3683 + 81 new = 3764.
- `scripts/test_org_tools_registry.py`: `ALL PASS`. `scripts/test_mcp_role_config.py`: `OK — 0 failure(s)`. `scripts/test_status_terminal_guard.py`: `ALL PASS`.
- `tests/test_w23_mesh_dispatch.py`: 81 passed alone.

The new file covers: flag parsing; self goes in-process; the exact ssh argv (`-i`,
`BatchMode=yes`, `ConnectTimeout=10`, alias, per-verb timeout, `stdin=DEVNULL`); 14
injection-looking inputs refused before ssh; 9 unreachable kinds; a verb refusal returned
as a dict; unreachable -> `queued_remote` (locks held, host kept, no raise); refusal ->
`failed`; the watchdog retries once per pass (two passes = two attempts, also through
`scan_once`); success clears the row; another box's row is skipped; flag off does nothing;
`pid_alive` replaces the ssh liveness query; HEARTBEAT stays on `read_remote_heartbeat`;
unreachable is "unknown, never dead"; a box that cannot say falls back to the ssh probe;
`publish_branch` is sent only when dispatcher != host and before the branch lookup; flag
OFF pins today's launcher command for contabo and winbox and asserts `lib.mesh` is never
called. The notifier (`osascript`) is silenced in the fixture.

Flag-off guarantee: the launcher/HEARTBEAT pins (`test_h3_runner_model_launch`,
`test_spawn_remote_linux`, `test_delegate_probe_gate`, `test_multihost`,
`test_w03b_local_launcher`, `test_watchdog_remote_heartbeat`, `test_w15_duty_split`,
`test_w04_self_host_sites`) stayed green with my code in and the flag off, before the
new file existed.

## Blockers

None. `lib/db.py` was blocked by `self_repo_guard` until the CTO added it to `touches`;
applied as scoped.

## Notes for the reviewer

- A mesh **timeout** does not prove the spawn did not start. `mesh_spawn_worker` therefore queues a row only if it is still `pending` after the timeout; a row the far side already moved (possible on a shared ledger after W1.10) is left alone and a warning is logged. Residual window: separate ledgers (today), where the Mac's row stays `pending` even if the remote spawned, so a retry after a real spawn-then-timeout can start a second worker. It closes with W1.10; this is why the flag is off until then.
- `publish_branch` refuses non-`review` rows, but the poller only visits `in_progress` rows: until something sets `review` on the worker host it is a refused, audited no-op per tick per remote row. Harmless, noisy in `events`.
- No cap on `queued_remote` retries, and `gc_stale_tasks` does not cancel it. A permanently dead host retries every pass until someone cancels the row.
- `branch_poller` and `gc_stale_tasks` liveness stay on the ssh `remote_pid_alive`; only the watchdog stall check moved to `pid_alive`.
- The self-dispatch path (`host == self_host()`) exists in `lib/mesh.py` and is tested, but no caller uses it.
- `scripts/test_watchdog_reap.py` (15 failures) and `scripts/test_surface_reaper.py` (28) fail when run **alone**, identically on an untouched `HEAD~1` export, and pass inside the full suite. Order dependence that predates this task.

## Skill learning

- MISSING [developer playbook / project-layout | no owner] : a task that adds a status must declare `lib/db.py` in `touches` up front; `self_repo_guard` only shows the declared list after the first refused edit. evidence: task-1c687904, guard refusal on `lib/db.py`
- COSTLY [no owner] : `scripts/test_watchdog_reap.py` and `scripts/test_surface_reaper.py` fail when run alone, on the untouched baseline too, and pass only in the full suite. Cost a baseline export to prove it was not mine. prevented by: a note in the testing playbook, run those two only via the full suite.
- COSTLY [no owner] : `lib.notify.success()/error()` runs `osascript` on the Mac, so any test that drives a code path calling them and forbids subprocess dies on it. prevented by: stub `lib.notify.notify` in the test fixture.
