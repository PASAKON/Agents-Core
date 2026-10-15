# REPORT task-d3f5a7e5

Question: which code writes to the `tasks` table (insert, update of status or fields, delete) without recording who did it?

Scope read: `lib/`, `tools/`, `runners/`, plus `dashboard.py` and `main.py` (grep only). There is no `mcp/` directory in this repo. The MCP servers live in `runners/*_mcp_server.py` and `lib/org_tools_registry.py`, and I covered those. `worktrees/`, `state/`, `node_modules`, `tests/` and `scripts/` were skipped. Two test files sit inside `lib/` (see the last section).

## How `actor` works in the DB layer

| Where | Behaviour |
|---|---|
| `lib/db.py:1127` `update_status(task_id, status, *, actor="system", force=False, **fields)` | The UPDATE is at `db.py:1167`. The event goes to `events.actor` at `db.py:1182`. When the terminal-merged guard refuses a change, the refusal is logged with the same actor at `db.py:1175`. If the caller passes no actor, the event says `"system"`. |
| `lib/db.py:1193` `set_fields(task_id, *, actor="system", **fields)` | The UPDATE is at `db.py:1212`. The event is at `db.py:1213`. Same `"system"` default. |
| `lib/db.py:1045` `create_task(...)` | It has **no actor parameter**. The only INSERT is at `db.py:1085`. The event is hard-coded `"system"` at `db.py:1090`. The only trace of the creator is `owner_cto` / `owner_role`, taken from `CTO_SESSION_ID` / `CXO_SESSION_ID` / `CXO_ROLE` (`db.py:970-986`). Only the row records that, not the event. |
| `lib/db.py:1095` `claim_task(task_id, agent)` | The UPDATE is at `db.py:1100`. `agent` is required. It is stored in `assigned_agent` and in the event actor (`db.py:1105`). |
| `lib/db_pg.py` | It has no task write functions. It holds DDL (`PG_SCHEMA`) and the `Connection` wrapper that translates SQL. Every write goes through `lib/db.py`. |
| DELETE | **No `DELETE FROM tasks` exists** in `lib/`, `tools/` or `runners/`. The other `DELETE FROM` hits are on `locks`, `node_secrets`, `live_sessions`, `transcripts` and `ceo_orders`. |
| Raw writes that bypass `db.py` | Only two: `lib/db.py:833` (migration backfill) and `tools/session_reconcile.py:121`. Neither writes an event. |
| The `tasks` table | It has no `actor` column. "Who did it" exists only in `events.actor`. |

## Abbreviations

- **C** = any C-level session (cto, cfo, cmo, cgo, coo) via `runners/cto_mcp_server.py` and `lib/org_tools_registry.py`.
- **PH** = Project Head. PHs are served `create_task`, `delegate_task`, `delegate_parallel_tasks`, `reopen_task` and `close_dev` (`PH_TOOLS`, `org_tools_registry.py:972`). They are not served `merge_task` or `revert_task_tool`.
- **WD** = `runners/watchdog.py`.
- **CD** = `runners/coo_dispatch.py`.
- **ND** = `tools/node_dispatch.py`.
- **W** = a worker process (dev, researcher, etc.).
- **DEL** = every caller of `tools/delegate.py`. `delegate_task` is reached from:
  - C and PH, through `org_tools_registry.py:227` and `cto_mcp_server.py:92`;
  - WD, `watchdog.py:967`;
  - CD, `coo_dispatch.py:144`;
  - ND, `node_dispatch.py:560`;
  - `tools/quota_handoff.py:170`;
  - `tools/bl_ab_run.py:535`;
  - `delegate_parallel`, `delegate.py:2738`.
  - `mesh_spawn_worker` is also called directly by WD at `watchdog.py:772`.
- **QH** = `tools/quota_handoff.py`. Its `--check-stop` mode is run by outside-runner launchers (codex/agy), and its handoff mode by a PH/CTO or an operator.

Verdicts:
- **OK**: the actor is passed and names the real caller.
- **missing**: no actor, so the event says `"system"`, or there is no event at all.
- **misleading**: a hard-coded actor that hides the real caller, or a wrong default.

## Table

### lib/db.py and raw writers

| file:line | function called | actor passed | who can run this code path | verdict |
|---|---|---|---|---|
| lib/db.py:1090 | `log_event` inside `create_task` (INSERT at 1085) | literal `"system"`, with no way to override | every `create_task` caller (rows below) | **missing** (no actor param; the event hides the creator) |
| lib/db.py:1105 | `log_event` inside `claim_task` (UPDATE at 1100) | variable `agent` (required) | worker_init, delegate, CD | OK |
| lib/db.py:1127 | `update_status` signature | default literal `"system"` | every caller that omits `actor` (QH rows below) | **misleading** (default hides the caller) |
| lib/db.py:1193 | `set_fields` signature | default literal `"system"` | every caller that omits `actor` | **misleading** (same default) |
| lib/db.py:833 | raw `UPDATE tasks SET delegate_log=report…` backfill in `init_schema` | none, and no event written | runs on every `db.init()` / `init_schema` in any process (C, PH, W, WD, scripts/migrate) | **missing** (low: one-off data migration, but it rewrites rows silently) |
| tools/session_reconcile.py:121 | raw `UPDATE tasks SET owner_cto=substr(...)` | none, and no event written | operator / cron, `python -m tools.session_reconcile --apply` | **missing** (the only non-db.py UPDATE; no audit row) |

### create_task callers (no actor parameter exists)

| file:line | function called | actor passed | who can run this code path | verdict |
|---|---|---|---|---|
| lib/org_tools_registry.py:171 | `db.create_task` in `_h_create_task` | none; `owner_cto` is stamped from `CTO_SESSION_ID`, `owner_role` from env | C, PH (`create_task` is in `PH_TOOLS`), QH via `quota_handoff.py:160` | **missing** (event says `"system"`; only `owner_*` identifies the caller, and it is blank for sessions without those env vars) |
| runners/cto_mcp_server.py:78 | `reg.dispatch_sync("create_task")`, a pass-through into the row above | none | C, PH | **missing** (same as above) |
| runners/coo_gate.py:150 | `db.create_task` in `op_create_task` | none; `owner_cto=session_id`, `owner_role=coo` are passed | COO (via `coo_mcp_server`) | **missing** (the row names the COO but the event says `"system"`) |
| tools/mesh_check.py:756 | `db_mod.create_task` (L4 probe) | none | operator / mesh health checks on any host | **missing** (the same function cancels the row at 771 as `mesh_check`, so create and cancel disagree) |
| tools/mesh_check.py:1469 | `db_mod.create_task` (join drill) | none | operator running the join drill | **missing** (cancel at 1480 uses `drill-join`) |
| tools/bl_ab_run.py:530 | `db.create_task` | none; `owner_cto` is passed | operator / CTO CLI | **missing** |

### tools/delegate.py

Every call below passes the literal `actor="cto"`. The code is shared by **DEL**, which includes PH, COO dispatch, the watchdog, node_dispatch and the quota handoff. For those callers `"cto"` is wrong. Every row is **misleading** unless noted.

| file:line | function called | actor passed | who can run this code path | verdict |
|---|---|---|---|---|
| tools/delegate.py:708 | `db.update_status` failed (DEV timeout in `wait` mode) | literal `"cto"` (711) | DEL | misleading |
| tools/delegate.py:870 | `db.claim_task(task_id, agent=role_name)` (reopen on a live worker) | variable `role_name` (the worker's role) | DEL (reopen path) | misleading (low): the CTO side performs the claim but the event says the worker did |
| tools/delegate.py:884 | `db.set_fields` | literal `"cto"` (888) | DEL | misleading |
| tools/delegate.py:928 | `db.update_status` failed (worker died before claim) | literal `"cto"` (931) | DEL; the verify task is spawned from any delegate | misleading |
| tools/delegate.py:955 | `db.update_status` failed (respawn failed) | literal `"cto"` (957) | DEL | misleading |
| tools/delegate.py:1344 | `db.update_status` failed (mesh spawn gave up) | literal `"cto"` | WD (`watchdog.py:772`) and DEL | misleading (WD is the real caller) |
| tools/delegate.py:1368 | `db.update_status` pending | literal `"cto"` | WD (772) and DEL | misleading |
| tools/delegate.py:1370 | `db.set_fields` | literal `"cto"` | WD and DEL | misleading |
| tools/delegate.py:1384 | `db.update_status` queued_remote | literal `"cto"` (1385) | WD and DEL | misleading |
| tools/delegate.py:1396 | `db.update_status` failed | literal `"cto"` | WD and DEL | misleading |
| tools/delegate.py:1433 | `db.set_fields` dry-run | literal `"cto"` (1434) | DEL | misleading |
| tools/delegate.py:1549 | `db.set_fields` dry-run ssh | literal `"cto"` (1552) | DEL | misleading |
| tools/delegate.py:1615 | `db.update_status` blocked_host | literal `"cto"` | DEL | misleading |
| tools/delegate.py:1622 | `db.update_status` conflict | literal `"cto"` (1625) | DEL | misleading |
| tools/delegate.py:1632 | `db.update_status` failed | literal `"cto"` (1634) | DEL | misleading |
| tools/delegate.py:1641 | `db.update_status` failed | literal `"cto"` (1643) | DEL | misleading |
| tools/delegate.py:1646 | `db.update_status` in_progress | literal `"cto"` (1649) | DEL | misleading |
| tools/delegate.py:1705 | `db.set_fields` dry-run | literal `"cto"` (1708) | DEL | misleading |
| tools/delegate.py:1730 | `db.update_status` conflict | literal `"cto"` (1733) | DEL | misleading |
| tools/delegate.py:1741 | `db.update_status` failed | literal `"cto"` (1743) | DEL | misleading |
| tools/delegate.py:1749 | `db.update_status` failed | literal `"cto"` (1751) | DEL | misleading |
| tools/delegate.py:1758 | `db.update_status` in_progress | literal `"cto"` (1762) | DEL | misleading |
| tools/delegate.py:1845 | `db.update_status` failed (trust prompt) | literal `"cto"` | DEL | misleading |
| tools/delegate.py:1876 | `db.update_status` failed | literal `"cto"` | DEL | misleading |
| tools/delegate.py:1902 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:1912 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:1919 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:1928 | `db.update_status` failed (tmux create) | literal `"cto"` (1929) | DEL | misleading |
| tools/delegate.py:1948 | `db.set_fields` | literal `"cto"` (1949) | DEL | misleading |
| tools/delegate.py:1961 | `db.update_status` failed (iTerm) | literal `"cto"` (1962) | DEL | misleading |
| tools/delegate.py:2038 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2066 | `db.set_fields` runner/model | literal `"cto"` (2070) | DEL | misleading |
| tools/delegate.py:2099 | `db.set_fields` | literal `"cto"` (2100) | DEL | misleading |
| tools/delegate.py:2309 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2414 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2431 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2459 | `db.update_status` failed | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2462 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2483 | `db.update_status` conflict (browser cap) | literal `"cto"` (2486) | DEL | misleading |
| tools/delegate.py:2512 | `db.set_fields` | literal `"cto"` (2515) | DEL | misleading |
| tools/delegate.py:2532 | `db.update_status` conflict | literal `"cto"` (2535) | DEL | misleading |
| tools/delegate.py:2542 | `db.update_status` conflict | literal `"cto"` (2545) | DEL | misleading |
| tools/delegate.py:2576 | `db.set_fields` | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2579 | `db.set_fields` spawned_at | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2587 | `db.update_status` failed | literal `"cto"` (2590) | DEL | misleading |
| tools/delegate.py:2604 | `db.update_status` pending | literal `"cto"` (2607) | DEL | misleading |
| tools/delegate.py:2649 | `db.set_fields` | literal `"cto"` (2657) | DEL | misleading |
| tools/delegate.py:2674 | `db.set_fields` | literal `"cto"` (2680) | DEL | misleading |
| tools/delegate.py:2687 | `db.update_status` pending (re-delegate) | literal `"cto"` | DEL | misleading |
| tools/delegate.py:2705 | `db.set_fields` spawned_at/host | literal `"cto"` (2706) | DEL | misleading |

### tools/git_ops.py (`merge_task`)

`merge_task(..., role="cto")` is called with the real caller's role at `org_tools_registry.py:276` (cfo, cmo, cgo, coo). The role is checked at `git_ops.py:400-406` and then dropped. `_merge_local` and `_merge_via_temp_worktree` do not receive it. Every status write below passes the literal `"cto"`. All rows are **misleading**. Who can run them: C with `can_merge` in `policies/agents.yaml`. A PH is not served `merge_task`.

| file:line | function called | actor passed | who can run this code path | verdict |
|---|---|---|---|---|
| tools/git_ops.py:451 | `db.update_status` review (touches violation) | literal `"cto"` (452) | C | misleading |
| tools/git_ops.py:474 | `db.update_status` pending (test gate failed) | literal `"cto"` (481) | C | misleading |
| tools/git_ops.py:507 | `db.update_status` review (work-dir unfiled) | literal `"cto"` (508) | C | misleading |
| tools/git_ops.py:560 | `db.update_status` review (base dirty) | literal `"cto"` (561) | C | misleading |
| tools/git_ops.py:580 | `db.update_status` review (merge error) | literal `"cto"` (581) | C | misleading |
| tools/git_ops.py:609 | `db.update_status` review | literal `"cto"` (610) | C | misleading |
| tools/git_ops.py:636 | `db.update_status` conflict | literal `"cto"` (637) | C | misleading |
| tools/git_ops.py:653 | `db.update_status` review | literal `"cto"` (654) | C | misleading |
| tools/git_ops.py:723 | `db.update_status` **done** (merged) | literal `"cto"` (724) | C | misleading (the key "work landed" event) |
| tools/git_ops.py:768 | `db.update_status` review | literal `"cto"` (769) | C | misleading |
| tools/git_ops.py:790 | `db.update_status` review | literal `"cto"` (791) | C | misleading |
| tools/git_ops.py:817 | `db.update_status` conflict | literal `"cto"` (818) | C | misleading |
| tools/git_ops.py:831 | `db.update_status` review | literal `"cto"` (832) | C | misleading |
| tools/git_ops.py:916 | `db.update_status` **done** (merged) | literal `"cto"` (917) | C | misleading (the key "work landed" event) |

### Other tools

| file:line | function called | actor passed | who can run this code path | verdict |
|---|---|---|---|---|
| lib/org_tools_registry.py:294 | `db.update_status` pending, `force=True` (`reopen_task`) | literal `"cto"` (299) | C and **PH** (`reopen_task` is in `PH_TOOLS`) | **misleading** (a PH or CFO reopen is logged as cto) |
| tools/revert_task.py:156 | `db.update_status` reverted (`_revert_local`) | literal `"cto"` | C (`revert_task_tool`, any C-level; not PH); CLI | misleading |
| tools/revert_task.py:225 | `db.update_status` reverted (temp-worktree path) | literal `"cto"` | same as above | misleading |
| tools/rollback.py:113 | `db.update_status` cancelled (`_rollback_local`) | literal `"cto"` (114) | operator CLI (`rollback.py:179` `main`) | misleading |
| tools/rollback.py:171 | `db.update_status` cancelled (temp-worktree path) | literal `"cto"` (172) | operator CLI | misleading |
| tools/quota_handoff.py:98 | `db.update_status` rate_limited | **none**, so default `"system"` | QH `--check-stop`, run by launchers on every codex/agy run end | **missing** |
| tools/quota_handoff.py:109 | `db.update_status` failed (dead run) | **none** | QH launchers | **missing** |
| tools/quota_handoff.py:166 | `db.update_status` failed (quota-handoff) | **none** | PH/CTO or operator (`handoff`) | **missing** |
| tools/quota_handoff.py:167 | `db.set_fields(new_id, runner="claude")` | **none** | PH/CTO or operator | **missing** |
| tools/gc_stale_tasks.py:159 | `db.set_fields` worktree=None | literal `"gc_stale_tasks"` | WD and the gc CLI | OK |
| tools/gc_stale_tasks.py:252 | `db.update_status` cancelled (stale pending) | literal `"gc_stale_tasks"` (253) | WD and CLI | OK |
| tools/gc_stale_tasks.py:297 | `db.update_status` cancelled (stale spawned) | literal `"gc_stale_tasks"` (298) | WD and CLI | OK |
| tools/gc_stale_tasks.py:327 | `db.update_status` cancelled (stale conflict) | literal `"gc_stale_tasks"` (328) | WD and CLI | OK |
| tools/gc_stale_tasks.py:384 | `db.update_status` cancelled (rate-limit overdue) | literal `"gc_stale_tasks"` (385) | WD and CLI | OK |
| tools/node_dispatch.py:903 | `db.set_fields` | const `ACTOR="node_dispatch"` (line 55) | ND on a node (Windows spawn) | OK |
| tools/node_dispatch.py:907 | `db.update_status` failed | `ACTOR` | ND | OK |
| tools/node_dispatch.py:924 | `db.update_status` blocked_host | `ACTOR` | ND | OK |
| tools/node_dispatch.py:929 | `db.update_status` conflict | `ACTOR` | ND | OK |
| tools/node_dispatch.py:935 | `db.update_status` failed | `ACTOR` | ND | OK |
| tools/node_dispatch.py:939 | `db.update_status` failed | `ACTOR` | ND | OK |
| tools/node_dispatch.py:942 | `db.update_status` in_progress | `ACTOR` (945) | ND | OK |
| tools/mesh_check.py:771 | `db_mod.update_status` cancelled | literal `"mesh_check"` | operator / mesh check | OK |
| tools/mesh_check.py:1480 | `db_mod.update_status` cancelled | const `JOIN_DRILL_ACTOR="drill-join"` (line 1378) | operator drill | OK |

### runners/

| file:line | function called | actor passed | who can run this code path | verdict |
|---|---|---|---|---|
| runners/worker_mcp_server.py:100 | `db.update_status` review (`submit_report`) | variable `ROLE` (env `WORKER_ROLE`, fallback `"dev"` at line 30) | W; `WORKER_ROLE` is set by worker_init:522, worker_resume:92 and agy_local:160 | OK (the `"dev"` fallback only applies if the env is unset) |
| runners/worker_mcp_server.py:212 | `db.update_status` blocked_human | variable `ROLE` | W | OK |
| runners/worker_mcp_server.py:322 | `db.set_fields` last_checkpoint (`dev_message`) | literal `"dev"` | **any worker role** (researcher, designer, video_editor, etc.), not only dev | **misleading** (the module's own `ROLE` variable is right there and is ignored) |
| runners/worker_init.py:419 | `db.claim_task(task_id, agent=role)` | variable `role` | W | OK |
| runners/worker_init.py:425 | `db.update_status` failed | variable `role` | W | OK |
| runners/worker_init.py:436 | `db.update_status` failed | variable `role` (439) | W | OK |
| runners/worker_init.py:444 | `db.update_status` failed | variable `role` (448) | W | OK |
| runners/worker_init.py:475 | `db.update_status` in_progress (pid) | variable `role` | W | OK |
| runners/worker_init.py:538 | `db.update_status` in_progress (pid) | variable `role` | W | OK |
| runners/worker_resume.py:63 | `db.update_status` failed | variable `role` (64) | W resume | OK |
| runners/worker_resume.py:68 | `db.update_status` in_progress | variable `role` | W resume | OK |
| runners/agy_local.py:33 | `db.update_status` (wrapper `_update_status`) | forwards `**kwargs` | W (agy) | OK (callers below pass an actor) |
| runners/agy_local.py:146 | `_update_status` in_progress | variable `role` | W (agy) | OK |
| runners/agy_local.py:174 | `_update_status` failed | variable `role` | W (agy) | OK |
| runners/agy_local.py:190 | `_update_status` failed | variable `role` | W (agy) | OK |
| runners/agy_local.py:206 | `_update_status` review | variable `role` | W (agy) | OK |
| runners/coo_worker.py:362 | `db.update_status` in_progress | literal `"coo_worker"` | COO worker only | OK |
| runners/coo_worker.py:372 | `db.update_status` failed | literal `"coo_worker"` | COO worker only | OK |
| runners/coo_worker.py:378 | `db.update_status` review | literal `"coo_worker"` | COO worker only | OK |
| runners/coo_worker.py:380 | `db.update_status` failed | literal `"coo_worker"` | COO worker only | OK |
| runners/coo_dispatch.py:124 | `db.claim_task(tid, "coo_dispatch")` | literal | CD only | OK |
| runners/coo_dispatch.py:133 | `db.update_status` failed | literal `"coo_dispatch"` | CD only | OK |
| runners/coo_dispatch.py:136 | `db.update_status` in_progress | literal `"coo_dispatch"` | CD only | OK |
| runners/coo_dispatch.py:164 | `db.update_status` cancelled | literal `"coo_dispatch"` | CD only | OK |
| runners/coo_dispatch.py:187 | `db.update_status` done | literal `"coo_dispatch"` | CD only | OK |
| runners/coo_dispatch.py:200 | `db.update_status` failed | literal `"coo_dispatch"` | CD only | OK |
| runners/coo_dispatch.py:204 | `db.update_status` failed | literal `"coo_dispatch"` | CD only | OK |
| runners/watchdog.py:505 | `db.set_fields` pid=None | literal `"watchdog"` | WD only | OK |
| runners/watchdog.py:616 | `db.set_fields` pid=None | literal `"watchdog"` | WD only | OK |
| runners/watchdog.py:877 | `db.update_status` stalled | literal `"watchdog"` | WD only | OK |
| runners/watchdog.py:914 | `db.update_status` stalled | literal `"watchdog"` (915) | WD only | OK |
| runners/watchdog.py:1133 | `db.set_fields` review | literal `"watchdog"` | WD only | OK |
| runners/watchdog.py:1168 | `db.update_status` stalled | literal `"watchdog"` | WD only | OK |
| runners/watchdog.py:1224 | `db.update_status` stalled | literal `"watchdog"` | WD only | OK |
| runners/branch_poller.py:516 | `db.set_fields` | literal `"branch_poller"` (517) | branch_poller only | OK |
| runners/branch_poller.py:535 | `db.update_status` failed | literal `"branch_poller"` (538) | branch_poller only | OK |
| runners/branch_poller.py:544 | `db.update_status` review | literal `"branch_poller"` | branch_poller only | OK |
| runners/branch_poller.py:561 | `db.set_fields` | literal `"branch_poller"` (562) | branch_poller only | OK |
| runners/branch_poller.py:578 | `db.update_status` blocked_human | literal `"branch_poller"` (579) | branch_poller only | OK |
| runners/branch_poller.py:599 | `db.update_status` failed | literal `"branch_poller"` (602) | branch_poller only | OK |

Not rows. These files only call into rows above:
- `runners/cto_mcp_server.py` (create/delegate/merge/reopen/revert are pass-throughs to the registry; the create row is at line 78).
- `runners/coo_mcp_server.py`.
- `runners/cto.py`.
- `tools/send_to_cxo.py`, `tools/worker_reap.py` and `tools/session_charter.py` (only mention the functions in comments; they write no task rows).

## Summary (5 lines)

1. The DB layer logs the actor in the event, never on the row. `update_status` and `set_fields` fall back to `"system"`, and `create_task` has no actor argument at all. That makes **13 rows missing** an actor and **72 misleading**. **54 are OK**, and none of the OK rows are in shared code.
2. **50 of the 72 misleading rows are in `tools/delegate.py`**, all `actor="cto"`. That code also runs for PH, COO dispatch (`coo_dispatch.py:144`), the watchdog (`watchdog.py:967`, `:772`), node_dispatch (`node_dispatch.py:560`) and the quota handoff, so those writes show up as the CTO.
3. **All 14 status writes in `tools/git_ops.py` `merge_task`, including both `done` writes (`:723`, `:916`), use `"cto"` while the real caller's `role` is in scope** and then dropped. The same goes for `org_tools_registry.py:294` (`reopen_task`, which PH can call), `revert_task.py:156,225` and `rollback.py:113,171`.
4. Every task INSERT goes through `create_task` (`db.py:1090`). All 6 callers show `"system"` in the event; only `owner_cto` / `owner_role` hint at who created it, and those can be empty. The QH writes (`quota_handoff.py:98,109,166,167`) pass nothing, and `:98` and `:109` run in launchers at the end of a worker run.
5. The runners that own their own writes (watchdog, branch_poller, coo_dispatch, coo_worker, node_dispatch, gc_stale_tasks, worker_init, worker_resume, agy_local) are clean. There is **no DELETE on `tasks`** anywhere. The only raw writes outside `db.py` are `db.py:833` and `session_reconcile.py:121`, and neither leaves an event.

## The 3 places most worth fixing first

1. **`tools/delegate.py` (50 rows: `:708` … `:2705`).**
   - The change: replace the hard-coded `"cto"` with one resolved actor. Either an `actor=` parameter on `delegate_task` / `mesh_spawn_worker` / `_spawn_*`, or a helper that reads `CXO_ROLE` / `ORG_PH_*`.
   - The callers to update: WD (`watchdog.py:967`, `:772`), CD (`coo_dispatch.py:144`), ND (`node_dispatch.py:560`) and QH (`quota_handoff.py:170`) should pass their own name.
   - Why first: it is the biggest block, and it is where spawn, conflict and failure states get written for every worker.
2. **`lib/db.py:1045/1090` (`create_task`) plus the `"system"` defaults at `:1127` and `:1193`.**
   - The change: give `create_task` an `actor` argument that defaults to the `owner_role` from `resolve_session_owner` rather than `"system"`.
   - Also change the defaults so a missing actor falls back to `CXO_ROLE` / `WORKER_ROLE` / `"unknown"` instead of `"system"`.
   - The callers fixed this way: `quota_handoff.py:98,109,166,167`, `org_tools_registry.py:171`, `coo_gate.py:150`, `mesh_check.py:756,1469`, `bl_ab_run.py:530`.
   - Why second: this one fix closes all 13 "missing" rows.
3. **`tools/git_ops.py` `merge_task` (14 rows, `:451` … `:916`) together with `org_tools_registry.py:294` (`reopen_task`).**
   - The change: pass `role` into `_merge_local` and `_merge_via_temp_worktree`, and use it as the actor.
   - For `reopen_task`: use `caller_role()` for the actor.
   - Why third: the merge `done` events are the audit trail for what landed on `main`, and a PH or a non-CTO C-level currently shows up as `"cto"`.

   Runner-up: `runners/worker_mcp_server.py:322`, a one-word fix from `"dev"` to `ROLE`.

## Files changed

- `docs/reports/task-d3f5a7e5/REPORT.md` (this file). No code was changed.

## Validation performed

- Found the write functions by reading `lib/db.py:1045-1213` and by grepping `lib/db_pg.py` for tasks writes (none).
- Found raw writers by grepping `lib tools runners dashboard.py main.py` for `UPDATE/INSERT/DELETE … tasks`.
- Found callers by grepping `create_task|claim_task|update_status|set_fields` under all module aliases (`db.`, `db_mod.`, `_update_status`) and for `from lib.db import <fn>` (none found).
- Opened every multi-line call to read its `actor=` argument. Line numbers in the table are the call-start line; a number in parentheses is the line of `actor=` when it differs.
- Grep output was truncated more than once, so I re-ran several greps per file to make sure no call was dropped. I did not run any tests or code.

## Limitations

- The caller-reach columns come from reading code and the `PH_TOOLS` allowlist, not from running anything. `ORG_PH_ROLES` is a host flag, so whether PH sessions exist on a given host was not checked.
- I did not scan `scripts/` (for example `scripts/migrate_tasks_db.py`), `tests/`, or any outside checkout. A writer there would not appear in the table.
- `lib/test_reflect.py:24,28,29,33` and `lib/test_recall.py:27,32` call `create_task` / `update_status` without an actor. They are test fixtures, so I excluded them from the counts.
- Postgres triggers or other DB-side writers were not examined beyond `lib/db_pg.py`, which defines only the `project_events` triggers.
- Dynamic callers (`getattr(db, ...)`, `eval`) would not be caught by grep. I found none.

## Blockers

- (none)

## Skill learning

- (none)
