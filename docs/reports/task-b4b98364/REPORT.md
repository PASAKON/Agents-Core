# REPORT task-b4b98364

## 5-Line Summary
1. `lib/db.py` has four `tasks` write functions (`create_task`, `claim_task`, `update_status`, `set_fields`) plus one raw `UPDATE tasks` in `init_schema` (`lib/db.py:832`); `lib/db_pg.py` is a SQL translation/connection layer with no `tasks` write functions of its own, and nothing in the repo deletes from `tasks`.
2. `db.create_task` (`lib/db.py:1045`) accepts no `actor=` parameter at all and unconditionally logs `actor="system"` at `lib/db.py:1090` (even though it resolves `owner_cto, owner_role = resolve_session_owner()` at `lib/db.py:1061`), so every task creation via MCP (`lib/org_tools_registry.py:171`), the COO gate (`runners/coo_gate.py:150`), `tools/quota_handoff.py:160`, and `tools/mesh_check.py:678,756,1469` hides who created the row.
3. `db.update_status` (`lib/db.py:1127`) and `db.set_fields` (`lib/db.py:1193`) default `actor: str = "system"` when `actor=` is omitted, which hides the caller in `tools/quota_handoff.py:98,109,166,167`, while `lib/db.py:832` (`init_schema`) and `tools/session_reconcile.py:120` (`normalize_owner_cto`) run raw `UPDATE tasks` SQL with no `log_event` or `actor` at all.
4. Across `tools/delegate.py` (49 sites), `tools/git_ops.py` (14 sites), `tools/revert_task.py` (2 sites), and `lib/org_tools_registry.py:293` (`reopen_task`), writes hard-code `actor="cto"` (and `tools/delegate.py:870` passes `agent=role_name`, the worker role) even though those paths are executed by any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`), Project Heads (`project_head`), `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py`, and `tools/quota_handoff.py`.
5. In `runners/worker_mcp_server.py:322`, `dev_message` hard-codes `actor="dev"` instead of using the module's `ROLE` variable (`WORKER_ROLE`), misattributing checkpoint writes from non-`dev` worker roles (`researcher`, `tester`, `web_designer`, `browser_operator`, `video_editor`, `data_analyst`, etc.).

---

## Top 3 Places Most Worth Fixing First

1. **`lib/db.py:1045` (`create_task`) + `lib/db.py:1127` (`update_status`) + `lib/db.py:1193` (`set_fields`)**
   - **Why first**: `create_task` already calls `owner_cto, owner_role = resolve_session_owner()` at `lib/db.py:1061` but still logs `"system"` at `lib/db.py:1090` and takes no `actor: str | None = None` argument. Adding `actor: str | None = None` to `create_task` (falling back to `f"{owner_role}-{owner_cto}"` or `owner_role` before `"system"`) and resolving the caller identity in `update_status`/`set_fields` when `actor` is omitted immediately fixes task creation attribution across `_h_create_task` (`lib/org_tools_registry.py:171`), `runners/coo_gate.py:150`, `tools/quota_handoff.py:98,109,160,166,167`, and `tools/mesh_check.py:678,756,1469`.
2. **`tools/delegate.py` (all 50 task-write call sites) + `lib/org_tools_registry.py:293` (`_h_reopen_task`)**
   - **Why second**: `tools/delegate.py` already defines `_delegating_actor() -> str` at `tools/delegate.py:2002` (returning `<role>-<sid>`, `<role>`, or `"cto"` from `CXO_ROLE`/`CXO_SESSION_ID`/`CTO_SESSION_ID`), but only uses it once for `router_off` at line 2029 while hard-coding `actor="cto"` at 49 `db.update_status`/`db.set_fields` sites (and `agent=role_name` at `tools/delegate.py:870`). Because Project Heads (`project_head`), all 5 C-levels, `runners/watchdog.py` (`_retry_queued_remote` at lines 761 & 772, `_drain_disk_queue` at line 967), and `runners/coo_dispatch.py:144` call into `tools/delegate.py`, replacing `actor="cto"` with `actor=_delegating_actor()` (and passing an explicit `actor` from `watchdog`/`coo_dispatch` + fixing `_h_reopen_task` at `lib/org_tools_registry.py:293`) eliminates the largest source of false `"cto"` audit events.
3. **`tools/git_ops.py` (14 `update_status` sites in `merge_task`) + `tools/revert_task.py` (`156`, `225`)**
   - **Why third**: `merge_task` (`tools/git_ops.py:363`) already receives `role: str = "cto"` from `lib/org_tools_registry.py:283` (`os.environ.get("CXO_ROLE") or "cto"`), and Project Heads also run `tools/git_ops.py` via CLI to merge their own project branches, yet all 14 `db.update_status` calls inside `merge_task` (`451, 474, 507, 560, 580, 609, 636, 653, 723, 768, 790, 817, 831, 916`) ignore `role` and pass `actor="cto"`. Similarly, `tools/revert_task.py:156,225` hard-codes `actor="cto"` when any C-level invokes `revert_task`. Threading the resolved caller identity (`<role>-<sid>` or `role`) into those 16 sites makes merge/conflict/revert audit trails accurate.

---

## Step 1: Write Functions in `lib/db.py` (and `lib/db_pg.py`)

- **`lib/db_pg.py`**: SQL translation and Postgres connection/schema layer (`PG_SCHEMA` defines `tasks` at `lib/db_pg.py:42`; `_translate_sql` at `lib/db_pg.py:194`). It defines **no** task-row write functions of its own; all `tasks` writes go through `lib/db.py`.
- **Deletes on `tasks`**: None exist anywhere in `lib/`, `tools/`, `mcp/` (directory not present), or `runners/`.
- **`lib/db.py` write primitives on `tasks`**:
  1. `lib/db.py:832` (`init_schema`, called by `db.init()` at `lib/db.py:852`): executes raw `UPDATE tasks SET delegate_log = report, report = NULL WHERE report IS NOT NULL AND status IN ('failed', 'conflict', 'stalled', 'cancelled') AND delegate_log IS NULL`. Takes **no `actor`** and writes **no `events` row**.
  2. `lib/db.py:1045` (`create_task`): executes `INSERT INTO tasks ...` at `lib/db.py:1084` and `log_event(conn, tid, "system", "task_created", {"role": role, "title": title})` at `lib/db.py:1090`. Takes **no `actor=` parameter**; always records literal `"system"` in `events.actor` (even though `owner_cto, owner_role = resolve_session_owner()` is computed at `lib/db.py:1061`).
  3. `lib/db.py:1095` (`claim_task(task_id: str, agent: str)`): executes `UPDATE tasks SET assigned_agent=?, status='in_progress', updated_at=? WHERE id=? AND status='pending'` at `lib/db.py:1099` and `log_event(conn, task_id, agent, "claimed", {})` at `lib/db.py:1105`. Requires `agent: str` (no default).
  4. `lib/db.py:1127` (`update_status(task_id: str, status: str, *, actor: str = "system", force: bool = False, **fields)`): executes `UPDATE tasks SET {sets} WHERE id=?` at `lib/db.py:1166`, `log_event(conn, task_id, actor, f"status_{status}", ...)` at `lib/db.py:1175`, and `log_event(conn, dep_id, actor, "unblocked", {"by": task_id})` at `lib/db.py:1182`. When `actor=` is omitted, defaults to literal `"system"`.
  5. `lib/db.py:1193` (`set_fields(task_id: str, *, actor: str = "system", **fields)`): executes `UPDATE tasks SET {sets} WHERE id=?` at `lib/db.py:1212` and `log_event(conn, task_id, actor, "fields_set", fields)` at `lib/db.py:1213`. When `actor=` is omitted, defaults to literal `"system"`.

---

## Step 2: Complete Table of `tasks` Table Writes and Callers (`lib/`, `tools/`, `mcp/`, `runners/`)

*(Note: For multi-line calls, `file:line` gives the exact line where the write call begins; if `actor=` appears on a continuation line inside that call, the `actor` column also notes the exact `actor=` line in parentheses so either line reference can be verified immediately.)*

| file:line | function called | actor passed (none / literal / variable) | who can run this code path | verdict (OK / missing / misleading) |
| --- | --- | --- | --- | --- |
| `lib/db.py:832` | `conn.execute("UPDATE tasks SET delegate_log = report, report = NULL ...")` (in `init_schema`) | `none` (no `log_event` call) | Any process calling `db.init()` (`runners/cto.py:131`, `runners/cto_mcp_server.py:55`, `runners/worker_init.py:389`, `runners/worker_mcp_server.py:293`, `runners/watchdog.py:1233`, `tools/gc_stale_tasks.py:409`, `tools/session_reconcile.py:197`, `tools/quota_handoff.py:157`) | `missing` |
| `lib/db.py:1084` | `conn.execute("INSERT INTO tasks ...")` + `log_event(conn, tid, "system", "task_created", ...)` (`lib/db.py:1090`, in `create_task` def at `lib/db.py:1045`) | `literal` (`"system"` hard-coded at `lib/db.py:1090`; `create_task` has no `actor=` param) | All callers of `db.create_task`: C-levels (`cto`, `cfo`, `cmo`, `cgo`, `coo`), Project Heads (`project_head`), `runners/coo_gate.py`, `tools/quota_handoff.py`, `tools/mesh_check.py` | `missing` |
| `lib/db.py:1099` | `conn.execute("UPDATE tasks SET assigned_agent=?, status='in_progress' ...")` + `log_event(conn, task_id, agent, "claimed", {})` (`lib/db.py:1105`, in `claim_task` def at `lib/db.py:1095`) | `variable` (`agent`, required parameter) | Worker launchers (`runners/worker_init.py`, `runners/agy_local.py`), `runners/coo_dispatch.py`, `tools/delegate.py` (`_resume_live_worker`) | `OK` |
| `lib/db.py:1166` | `conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", vals)` + `log_event(conn, task_id, actor, ...)` (`lib/db.py:1175,1182`, in `update_status` def at `lib/db.py:1127`) | `literal` (defaults to `actor: str = "system"` at `lib/db.py:1127` when caller omits `actor=`) | All callers of `db.update_status` across `lib/`, `tools/`, `runners/` | `missing` |
| `lib/db.py:1212` | `conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", vals)` + `log_event(conn, task_id, actor, "fields_set", fields)` (`lib/db.py:1213`, in `set_fields` def at `lib/db.py:1193`) | `literal` (defaults to `actor: str = "system"` at `lib/db.py:1193` when caller omits `actor=`) | All callers of `db.set_fields` across `lib/`, `tools/`, `runners/` | `missing` |
| `lib/org_tools_registry.py:171` | `db.create_task` (in `_h_create_task`) | `none` (`create_task` takes no `actor=` and logs `"system"`) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`) and Project Head (`project_head`, via `PH_TOOLS` in `runners/cto_mcp_server.py`) | `missing` |
| `lib/org_tools_registry.py:293` | `db.update_status` (in `_h_reopen_task`) | `literal` (`actor="cto"` at `lib/org_tools_registry.py:299`) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`) and Project Head (`project_head`, via `PH_TOOLS` in `runners/cto_mcp_server.py`) | `misleading` |
| `tools/delegate.py:708` | `db.update_status` (in `_wait_for_terminal`) | `literal` (`actor="cto"` at `tools/delegate.py:711`) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`), Project Head (`project_head`), `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py`, `tools/quota_handoff.py` | `misleading` |
| `tools/delegate.py:870` | `db.claim_task` (in `_resume_live_worker`) | `variable` (`agent=role_name`, the worker role from `task["role"]`, not the delegating caller) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`) or Project Head (`project_head`) delegating a reopened task | `misleading` |
| `tools/delegate.py:884` | `db.set_fields` (in `_resume_live_worker`) | `literal` (`actor="cto"` at `tools/delegate.py:888`) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`) or Project Head (`project_head`) delegating a reopened task | `misleading` |
| `tools/delegate.py:928` | `db.update_status` (in `_verify_claimed`) | `literal` (`actor="cto"` at `tools/delegate.py:931`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py`, `tools/quota_handoff.py` | `misleading` |
| `tools/delegate.py:955` | `db.update_status` (in `_verify_claimed`) | `literal` (`actor="cto"` at `tools/delegate.py:957`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py`, `tools/quota_handoff.py` | `misleading` |
| `tools/delegate.py:1344` | `db.update_status` (in `give_up_queued_remote`) | `literal` (`actor="cto"`) | `runners/watchdog.py:761` (`_retry_queued_remote`) | `misleading` |
| `tools/delegate.py:1368` | `db.update_status` (in `mesh_spawn_worker`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py:772` (`_retry_queued_remote`), `runners/watchdog.py:967` (`_drain_disk_queue`), `runners/coo_dispatch.py:144` | `misleading` |
| `tools/delegate.py:1370` | `db.set_fields` (in `mesh_spawn_worker`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py:772,967`, `runners/coo_dispatch.py:144` | `misleading` |
| `tools/delegate.py:1384` | `db.update_status` (in `mesh_spawn_worker`) | `literal` (`actor="cto"` at `tools/delegate.py:1385`) | Any C-level, Project Head, `runners/watchdog.py:772,967`, `runners/coo_dispatch.py:144` | `misleading` |
| `tools/delegate.py:1396` | `db.update_status` (in `mesh_spawn_worker`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py:772,967`, `runners/coo_dispatch.py:144` | `misleading` |
| `tools/delegate.py:1433` | `db.set_fields` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1434`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1549` | `db.set_fields` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1552`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1615` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1622` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1625`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1632` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1634`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1641` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1643`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1646` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1649`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1705` | `db.set_fields` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1708`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1730` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1733`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1741` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1743`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1749` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1751`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1758` | `db.update_status` (in `_spawn_remote`) | `literal` (`actor="cto"` at `tools/delegate.py:1762`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1845` | `db.update_status` (in `_trust_prompt`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1876` | `db.update_status` (in `_spawn_local`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1902` | `db.set_fields` (in `_spawn_local`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1912` | `db.set_fields` (in `_spawn_local`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1919` | `db.set_fields` (in `_spawn_local`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1928` | `db.update_status` (in `_spawn_local`) | `literal` (`actor="cto"` at `tools/delegate.py:1929`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1948` | `db.set_fields` (in `_spawn_local`) | `literal` (`actor="cto"` at `tools/delegate.py:1949`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:1961` | `db.update_status` (in `_spawn_local`) | `literal` (`actor="cto"` at `tools/delegate.py:1962`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2038` | `db.set_fields` (in `_route_runner`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2066` | `db.set_fields` (in `_route_runner`) | `literal` (`actor="cto"` at `tools/delegate.py:2070`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2099` | `db.set_fields` (in `_keep_host_line`) | `literal` (`actor="cto"` at `tools/delegate.py:2100`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2309` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2414` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2431` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2459` | `db.update_status` (in `_delegate_task`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2462` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2483` | `db.update_status` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2486`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2512` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2515`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2532` | `db.update_status` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2535`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2542` | `db.update_status` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2545`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2576` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2579` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2587` | `db.update_status` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2590`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2604` | `db.update_status` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2607`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2649` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2657`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2674` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2680`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2687` | `db.update_status` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2688`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/delegate.py:2705` | `db.set_fields` (in `_delegate_task`) | `literal` (`actor="cto"` at `tools/delegate.py:2706`) | Any C-level, Project Head, `runners/watchdog.py`, `runners/coo_dispatch.py`, `tools/node_dispatch.py:560` | `misleading` |
| `tools/git_ops.py:451` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`; ignores `role` param on `merge_task`) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`) via `merge_task` MCP tool, or Project Head / C-level via `python -m tools.git_ops` CLI | `misleading` |
| `tools/git_ops.py:474` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:507` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:560` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:580` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:609` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:636` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:653` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:723` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:768` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:790` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:817` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:831` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/git_ops.py:916` | `db.update_status` (in `merge_task`) | `literal` (`actor="cto"`) | Any C-level via MCP or Project Head / C-level via CLI | `misleading` |
| `tools/revert_task.py:156` | `db.update_status` (in `_revert_local`) | `literal` (`actor="cto"`) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`) via `revert_task` MCP tool, or Project Head / C-level via CLI | `misleading` |
| `tools/revert_task.py:225` | `db.update_status` (in `_revert_via_temp_worktree`) | `literal` (`actor="cto"`) | Any C-level (`cto`, `cfo`, `cmo`, `cgo`, `coo`) via `revert_task` MCP tool, or Project Head / C-level via CLI | `misleading` |
| `tools/quota_handoff.py:98` | `db.update_status` (in `record_limit_stop`) | `none` (defaults to `"system"`) | Remote worker launcher (`scripts/spawn-worker-remote.sh:215`), `runners/branch_poller.py:553`, `runners/watchdog.py:1141`, or CLI caller | `missing` |
| `tools/quota_handoff.py:109` | `db.update_status` (in `record_dead_run`) | `none` (defaults to `"system"`) | Remote worker launcher (`scripts/spawn-worker-remote.sh:215` `--check-stop --dead`) or CLI caller | `missing` |
| `tools/quota_handoff.py:160` | `org_tools_registry.dispatch_sync("create_task", **create)` -> `db.create_task` (in `handoff`) | `none` (`create_task` logs `"system"`) | C-level or Project Head running `python -m tools.quota_handoff <task-id>` | `missing` |
| `tools/quota_handoff.py:166` | `db.update_status` (in `handoff`) | `none` (defaults to `"system"`) | C-level or Project Head running `python -m tools.quota_handoff <task-id>` | `missing` |
| `tools/quota_handoff.py:167` | `db.set_fields` (in `handoff`) | `none` (defaults to `"system"`) | C-level or Project Head running `python -m tools.quota_handoff <task-id>` | `missing` |
| `tools/session_reconcile.py:120` | `conn.execute("UPDATE tasks SET owner_cto = substr(owner_cto, 5) WHERE owner_cto LIKE 'cto-%'")` (in `normalize_owner_cto`) | `none` (raw SQL `UPDATE tasks`, no `log_event`) | C-level / operator running `python -m tools.session_reconcile --apply` | `missing` |
| `tools/mesh_check.py:678` | `session.call_tool("create_task", ...)` -> `db.create_task` (in `_l3_cycle`) | `none` (`create_task` logs `"system"`) | Operator / C-level / drill runner running `python -m tools.mesh_check --level 3` | `missing` |
| `tools/mesh_check.py:756` | `db_mod.create_task` (in `l4_probe`) | `none` (`create_task` logs `"system"`) | Operator / C-level / drill runner running `python -m tools.mesh_check --level 4` | `missing` |
| `tools/mesh_check.py:771` | `db_mod.update_status` (in `l4_probe`) | `literal` (`actor="mesh_check"`) | `tools/mesh_check.py --level 4` probe | `OK` |
| `tools/mesh_check.py:1469` | `db_mod.create_task` (in `join_drill_task_create`) | `none` (`create_task` logs `"system"`) | `scripts/drill-join.sh` / operator running `python -m tools.mesh_check --join-drill-task create` | `missing` |
| `tools/mesh_check.py:1480` | `db_mod.update_status` (in `join_drill_task_close`) | `literal` (`actor=JOIN_DRILL_ACTOR`, `"drill-join"`) | `scripts/drill-join.sh` / operator running `python -m tools.mesh_check --join-drill-task close` | `OK` |
| `tools/gc_stale_tasks.py:159` | `db.set_fields` (in `_backfill_missing_worktrees`) | `literal` (`actor="gc_stale_tasks"`) | `runners/watchdog.py:1098` or operator CLI (`python -m tools.gc_stale_tasks --apply`) | `OK` |
| `tools/gc_stale_tasks.py:252` | `db.update_status` (in `gc`) | `literal` (`actor="gc_stale_tasks"` at `tools/gc_stale_tasks.py:255`) | `runners/watchdog.py:1098` or operator CLI (`python -m tools.gc_stale_tasks --apply`) | `OK` |
| `tools/gc_stale_tasks.py:297` | `db.update_status` (in `gc`) | `literal` (`actor="gc_stale_tasks"` at `tools/gc_stale_tasks.py:300`) | `runners/watchdog.py:1098` or operator CLI (`python -m tools.gc_stale_tasks --apply`) | `OK` |
| `tools/gc_stale_tasks.py:327` | `db.update_status` (in `gc`) | `literal` (`actor="gc_stale_tasks"` at `tools/gc_stale_tasks.py:330`) | `runners/watchdog.py:1098` or operator CLI (`python -m tools.gc_stale_tasks --apply`) | `OK` |
| `tools/gc_stale_tasks.py:384` | `db.update_status` (in `_reconcile_done_Requires_merge`) | `literal` (`actor="gc_stale_tasks"` at `tools/gc_stale_tasks.py:387`) | `runners/watchdog.py:1098` or operator CLI (`python -m tools.gc_stale_tasks --apply`) | `OK` |
| `tools/node_dispatch.py:903` | `db.set_fields` (in `_ingest_remote_branch`) | `literal` (`actor=ACTOR`, `"node_dispatch"`) | `node_dispatch publish_branch` (invoked by `runners/branch_poller.py`) | `OK` |
| `tools/node_dispatch.py:907` | `db.update_status` (in `_ingest_remote_branch`) | `literal` (`actor=ACTOR`, `"node_dispatch"`) | `node_dispatch publish_branch` | `OK` |
| `tools/node_dispatch.py:924` | `db.update_status` (in `_ingest_remote_branch`) | `literal` (`actor=ACTOR`, `"node_dispatch"`, at `tools/node_dispatch.py:925`) | `node_dispatch publish_branch` | `OK` |
| `tools/node_dispatch.py:929` | `db.update_status` (in `_ingest_remote_branch`) | `literal` (`actor=ACTOR`, `"node_dispatch"`) | `node_dispatch publish_branch` | `OK` |
| `tools/node_dispatch.py:935` | `db.update_status` (in `_ingest_remote_branch`) | `literal` (`actor=ACTOR`, `"node_dispatch"`, at `tools/node_dispatch.py:936`) | `node_dispatch publish_branch` | `OK` |
| `tools/node_dispatch.py:939` | `db.update_status` (in `_ingest_remote_branch`) | `literal` (`actor=ACTOR`, `"node_dispatch"`, at `tools/node_dispatch.py:940`) | `node_dispatch publish_branch` | `OK` |
| `tools/node_dispatch.py:942` | `db.update_status` (in `_ingest_remote_branch`) | `literal` (`actor=ACTOR`, `"node_dispatch"`) | `node_dispatch publish_branch` | `OK` |
| `runners/coo_gate.py:150` | `db.create_task` (in `op_create_task`) | `none` (`create_task` takes no `actor=` and logs `"system"`) | COO (`sompong`) calling `create_task` through `org-coo-gate.socket` | `missing` |
| `runners/worker_mcp_server.py:100` | `db.set_fields` (in `task_Checkpoint`) | `variable` (`actor=ROLE`, from `WORKER_ROLE`) | Worker session calling `task_Checkpoint` MCP tool | `OK` |
| `runners/worker_mcp_server.py:212` | `db.update_status` (in `task_Report`) | `variable` (`actor=ROLE`, from `WORKER_ROLE`) | Worker session calling `task_Report` MCP tool | `OK` |
| `runners/worker_mcp_server.py:322` | `db.set_fields` (in `dev_message`) | `literal` (`actor="dev"`, ignoring `ROLE` at `runners/worker_mcp_server.py:29`) | Any Claude worker role (`developer`, `tester`, `web_designer`, `browser_operator`, `video_editor`, `researcher`, `data_analyst`, etc.) calling `dev_message` | `misleading` |
| `runners/worker_init.py:419` | `db.claim_task` (in `main`) | `variable` (`agent=role`) | Local Claude worker process on startup | `OK` |
| `runners/worker_init.py:425` | `db.set_fields` (in `main`) | `variable` (`actor=role`) | Local Claude worker process on startup | `OK` |
| `runners/worker_init.py:436` | `db.update_status` (in `_fail`) | `variable` (`actor=role`) | Local Claude worker process on startup failure | `OK` |
| `runners/worker_init.py:444` | `db.update_status` (in `main`) | `variable` (`actor=role`) | Local Claude worker process on `WORK_DIR` failure | `OK` |
| `runners/worker_init.py:475` | `db.update_status` (in `main`) | `variable` (`actor=role`) | Local Claude worker process on missing binary | `OK` |
| `runners/worker_init.py:538` | `db.update_status` (in `_finalize_after_exit`) | `variable` (`actor=role` at `runners/worker_init.py:539`) | Local Claude worker process on exit without report | `OK` |
| `runners/worker_resume.py:63` | `db.set_fields` (in `main`) | `variable` (`actor=role`) | Resumed local Claude worker process | `OK` |
| `runners/worker_resume.py:68` | `db.update_status` (in `main`) | `variable` (`actor=role` at `runners/worker_resume.py:69`) | Resumed local Claude worker process on missing binary | `OK` |
| `runners/agy_local.py:33` | `db.update_status` (in `_fail`) | `variable` (`actor=role` at `runners/agy_local.py:34`) | Local AGY worker wrapper on pre-claim failure | `OK` |
| `runners/agy_local.py:146` | `db.claim_task` (in `main`) | `variable` (`agent=role`) | Local AGY worker wrapper on startup | `OK` |
| `runners/agy_local.py:174` | `db.set_fields` (in `main`) | `variable` (`actor=role`) | Local AGY worker wrapper recording `pid` | `OK` |
| `runners/agy_local.py:190` | `db.update_status` (in `main`) | `variable` (`actor=role` at `runners/agy_local.py:191`) | Local AGY worker wrapper on timeout | `OK` |
| `runners/agy_local.py:206` | `db.update_status` (in `main`) | `variable` (`actor=role` at `runners/agy_local.py:208`) | Local AGY worker wrapper on exit without report | `OK` |
| `runners/coo_dispatch.py:124` | `db.claim_task` (in `claim_and_run`) | `literal` (`"coo_dispatch"`) | `org-coo-dispatch.service` daemon | `OK` |
| `runners/coo_dispatch.py:133` | `db.update_status` (in `claim_and_run`) | `literal` (`actor="coo_dispatch"`) | `org-coo-dispatch.service` daemon | `OK` |
| `runners/coo_dispatch.py:136` | `db.update_status` (in `claim_and_run`) | `literal` (`actor="coo_dispatch"`, twice on line 136) | `org-coo-dispatch.service` daemon | `OK` |
| `runners/coo_dispatch.py:164` | `db.update_status` (in `claim_and_run`) | `literal` (`actor="coo_dispatch"` at `runners/coo_dispatch.py:165`) | `org-coo-dispatch.service` daemon | `OK` |
| `runners/coo_dispatch.py:187` | `db.update_status` (in `claim_and_run`) | `literal` (`actor="coo_dispatch"` at `runners/coo_dispatch.py:188`) | `org-coo-dispatch.service` daemon | `OK` |
| `runners/coo_dispatch.py:200` | `db.update_status` (in `claim_and_run`) | `literal` (`actor="coo_dispatch"` at `runners/coo_dispatch.py:201`) | `org-coo-dispatch.service` daemon | `OK` |
| `runners/coo_dispatch.py:204` | `db.update_status` (in `claim_and_run`) | `literal` (`actor="coo_dispatch"`) | `org-coo-dispatch.service` daemon | `OK` |
| `runners/coo_worker.py:362` | `db.update_status` (in `run_task`) | `literal` (`actor="coo_worker"` at `runners/coo_worker.py:364`) | COO headless worker runner (`runners/coo_worker.py`) | `OK` |
| `runners/coo_worker.py:372` | `db.update_status` (in `run_task`) | `literal` (`actor="coo_worker"` at `runners/coo_worker.py:374`) | COO headless worker runner (`runners/coo_worker.py`) | `OK` |
| `runners/coo_worker.py:378` | `db.update_status` (in `run_task`) | `literal` (`actor="coo_worker"`) | COO headless worker runner (`runners/coo_worker.py`) | `OK` |
| `runners/coo_worker.py:380` | `db.update_status` (in `run_task`) | `literal` (`actor="coo_worker"` at `runners/coo_worker.py:381`) | COO headless worker runner (`runners/coo_worker.py`) | `OK` |
| `runners/watchdog.py:505` | `db.set_fields` (in `_record_stall_nudge`) | `literal` (`actor="watchdog"`) | `runners/watchdog.py` daemon | `OK` |
| `runners/watchdog.py:616` | `db.set_fields` (in `_record_respawn`) | `literal` (`actor="watchdog"` at `runners/watchdog.py:619`) | `runners/watchdog.py` daemon | `OK` |
| `runners/watchdog.py:877` | `db.update_status` (in `_escalate_stalled`) | `literal` (`actor="watchdog"` at `runners/watchdog.py:879`) | `runners/watchdog.py` daemon | `OK` |
| `runners/watchdog.py:914` | `db.update_status` (in `_auto_respawn`) | `literal` (`actor="watchdog"` at `runners/watchdog.py:916`) | `runners/watchdog.py` daemon | `OK` |
| `runners/watchdog.py:1133` | `db.set_fields` (in `_reap_dead_pid`) | `literal` (`actor="watchdog"` at `runners/watchdog.py:1136`) | `runners/watchdog.py` daemon | `OK` |
| `runners/watchdog.py:1168` | `db.update_status` (in `_reap_dead_pid`) | `literal` (`actor="watchdog"` at `runners/watchdog.py:1171`) | `runners/watchdog.py` daemon | `OK` |
| `runners/watchdog.py:1224` | `db.update_status` (in `_reap_dead_pid`) | `literal` (`actor="watchdog"` at `runners/watchdog.py:1225`) | `runners/watchdog.py` daemon | `OK` |
| `runners/branch_poller.py:516` | `db.set_fields` (in `poll_once`) | `literal` (`actor="branch_poller"`) | `runners/branch_poller.py` daemon | `OK` |
| `runners/branch_poller.py:535` | `db.update_status` (in `poll_once`) | `literal` (`actor="branch_poller"`) | `runners/branch_poller.py` daemon | `OK` |
| `runners/branch_poller.py:544` | `db.update_status` (in `poll_once`) | `literal` (`actor="branch_poller"` at `runners/branch_poller.py:545`) | `runners/branch_poller.py` daemon | `OK` |
| `runners/branch_poller.py:561` | `db.set_fields` (in `poll_once`) | `literal` (`actor="branch_poller"`) | `runners/branch_poller.py` daemon | `OK` |
| `runners/branch_poller.py:578` | `db.update_status` (in `poll_once`) | `literal` (`actor="branch_poller"` at `runners/branch_poller.py:584`) | `runners/branch_poller.py` daemon | `OK` |
| `runners/branch_poller.py:599` | `db.update_status` (in `poll_once`) | `literal` (`actor="branch_poller"` at `runners/branch_poller.py:604`) | `runners/branch_poller.py` daemon | `OK` |

---

## Files changed
- `docs/reports/task-b4b98364/REPORT.md` (created)
- `REPORT.md` (created)
- No code files were modified (`Do not change any code`).

## Validation performed
- Read every Python file in `lib/`, `tools/`, and `runners/` inside `/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__researcher__task-b4b98364` using `view_file` (`mcp/` does not exist in this repository) and verified every `file:line` against the exact line numbers in this worktree.
- Per the AGY Remote Worker Contract (`For AGY, use file tools only; leave shell validation to the review process`), no shell commands were executed.

## Limitations
- `scripts/` and `deploy/` were outside the requested scan directories (`lib/`, `tools/`, `mcp/`, `runners/`), though their interactions with `tools/quota_handoff.py`, `tools/mesh_check.py`, and `runners/coo_gate.py` are noted in the caller analysis.

## Blockers
- (none)

## Skill learning
- (none)
