# REPORT task-b485f75f

## Summary

Completed read-only Org Queue Audit A3 (`O-20261114-1701-56fb`) covering real resource, lock, queue, quota, Chrome CDP, and video render collisions over the last 30 days (`2026-10-15` to `2026-11-14`). Delivered `docs/reports/org-queue-audit/A3-incidents.md` with `file:line` citations for every claim, a chronological ledger of verified incidents (date, resource, task IDs, time/money lost, and whether a lease with wait+wake would have prevented it), structural root-cause analysis of current lock/queue stores, and a ranked top 5 resources to move first into the unified hub lease/queue system (`mutex` / `pool` / `rate`).

Key findings documented in `docs/reports/org-queue-audit/A3-incidents.md`:
1. **Path / `touches` conflicts (`lib/db.py:1360-1430`, `tools/delegate.py:2703-2726`):** 49 conflict events across 33 tasks, including **11 tasks permanently cancelled by `tools/gc_stale_tasks.py:347-368` after 60 minutes** (`task-1d5941ba`, `task-635a4385`, `task-dafd0138`, `task-7e06fd4e`, `task-898654bb`, `task-2161c20a`, `task-32f6419e`, `task-1babfc10`, `task-19f3dfbc`, `task-3ea0d7c9`, plus `task-f7dd40d5` & `task-a089c9cc`) and two 3-way mutual deadlocks (`2026-10-27` and `2026-11-06`) caused by `'conflict'` and `'pending'` being in `ACTIVE_STATUSES` (`lib/db.py:1384-1385`) and wildcard strings (`docs/reports/task-*/REPORT.md`) not expanding `<task-id>`.
2. **Host capacity, RAM floor, CPU-exception slot, & `disk orange` (`lib/router.py:305-416`, `tools/delegate.py:2249-2258, 2539-2547`, `tools/host_queue.py:22`):** 290+ `no_host:` retry events across 39 tasks (including 15h 58m / >180 5-min retries on `task-52c5c97a` and 36 retries on `task-ca79b69b` / `task-5f9b0d7a`), plus 23 Contabo `disk orange` refusals (`tools/delegate.py:2539-2547`) that return `pending` **without enqueuing**, causing `task-897debd6` to be killed by 30-min GC (`tools/gc_stale_tasks.py:254`). Also found that `tools/gc_stale_tasks.py:64, 254` checks `disk_queue` and `budget_queue` but omits `host_queue.is_queued(t["id"])`.
3. **Runner quota buckets & `budget_queue` (`tools/budget_queue.py:18`, `tools/quota_reset.py:100-108`):** 200+ `tier_defer: queued for budget` events across 25 tasks (including 98 5-min retries over 7h 49m on `task-7124afcb`), **7 budget-queued tasks killed by 30-min GC** (`task-7311db37`, `task-30ff715e`, `task-43a3c5c2`, `task-c02aee60`, `task-dcbc3859`, `task-1fcc16b5`, `task-0eed0821`) because `state/budget_queue.jsonl` is per-host (`tools/gc_stale_tasks.py:27-29, 254`), and 28 wasted/failed spawns from exhausted pins, unknown Codex quota rollouts, and stale `runner_model` across queue/re-route (`task-c7065d2a`, `task-4ca6899a`). Moreover, `tools/budget_queue.py:1-130` defines no `drain()` function, so `tools/quota_reset.py:103-105` cannot wake `budget_queue` on quota reset.
4. **Browser operator pool caps (`tools/delegate.py:2650-2667`) & Chrome CDP port/channel clashes:** 6 `browser cap` conflicts (`1/1` on Contabo, `2/2` on Winbox) with **3 browser tasks killed by 60-min GC** (`task-3b0b5401`, `task-fbf0afe1`, `task-dfe3f610`), plus live Chrome CDP clashes on `winbox:9224` (`docs/reports/last-bell-refs-r1/REPORT.md:49, 75`, `tools/chatgpt_images.py:29-31, 97`) and `winbox:9226` YouTube Studio channel switching between Jade Tally and Ghost Rules (`docs/reports/ghostrules-ep3-ep4-schedule-20261114/REPORT.md:34, 48-49`).
5. **Parallel video render OOMs & `.bl-render.lock` (`tools/ilag_cut.py:62, 988-1016`):** Parallel Contabo renders caused 5x swap slowdown and OOM (`docs/reports/task-cc55e620/REPORT.md:45, 54`), while the Linux-only `/opt/MoonieXHQ/Work/.bl-render.lock` blocked sandboxed worker `task-d4c1f234` (`docs/reports/task-d4c1f234/REPORT.md:47`).

## Files Changed

- `docs/reports/org-queue-audit/A3-incidents.md` — new (30-day collision ledger, root-cause analysis with `file:line` citations, ranked top 5 resources to move first).
- `docs/reports/task-b485f75f/REPORT.md` — new (this task report).

## Validation Performed

- Read and verified lock/queue/router/GC implementations in `lib/db.py:1340-1465`, `lib/router.py:1-450`, `tools/delegate.py:2000-2942`, `tools/home_lock.py:1-200`, `tools/host_queue.py:1-150`, `tools/budget_queue.py:1-130`, `tools/disk_queue.py:1-111`, `tools/gc_stale_tasks.py:1-450`, `tools/worker_reap.py:1-90`, `tools/quota_reset.py:1-168`, `tools/ilag_cut.py:1-120, 900-1165`, `tools/chatgpt_images.py:1-120, 900-1068`, `tools/flow_shoot.py:1-120`, `tools/drive_leg.py:1-120`, and `runners/watchdog.py:1-300, 900-1589`.
- Extracted and cross-checked 30-day hub `events` and `tasks.delegate_log` from `/opt/MoonieXHQ/Agents/Core/state/tasks.snapshot.db` (refreshed `2026-11-14 10:54` via `scripts/hub/export_to_sqlite.py:15-17, 102-119`), `docs/reports/*/REPORT.md`, `/opt/MoonieXHQ/Agents/Core/state/handoff/`, and `git log --since=2026-10-15`.
- Verified with `git status` that only `docs/reports/org-queue-audit/A3-incidents.md` and `docs/reports/task-b485f75f/REPORT.md` were created, and no code, config, or `state/` files were modified.

## Limitations / Not checked / risk

- Headless AGY print-mode allow-list (`config/agy-settings.json:4-24`) forbids running `bash scripts/hub/org-python.sh -c ...`. Hub `tasks` and 30-day `events` were read from the Contabo SQLite hub snapshot `/opt/MoonieXHQ/Agents/Core/state/tasks.snapshot.db` (`scripts/hub/export_to_sqlite.py:15-17`, mtime `2026-11-14 10:54`).
- `state/host_queue.jsonl`, `state/budget_queue.jsonl`, `state/disk_queue.jsonl`, and `state/relay_queue.db` on Contabo currently have 0 lines because `pop()` / `remove()` rewrites the file; historical queue events were reconstructed from hub `events` (`fields_set` on `delegate_log`) and task reports.
- Remote `state/*_queue.jsonl` files on Winbox and Mac were not inspected over SSH (`ssh` is denied in headless AGY and by the no-network audit constraint).

## Blockers

- None.

## Skill learning

- **MISSING** [`CTO_Knowledge_AGY` §2 "The headless worker contract (`roles/_worker_remote.md`)"] : briefs that instruct an AGY worker to run `bash scripts/hub/org-python.sh -c "from lib import db; ..."` cannot execute that command because `config/agy-settings.json:4-24` only allows `pytest`, `agy_browse.py`, `git`, and read-only text utilities (`grep`, `cat`, `head`, `tail`, `wc`, `ls`); however, `/opt/MoonieXHQ/Agents/Core/state/tasks.snapshot.db` (`scripts/hub/export_to_sqlite.py:15-17`) is updated on Contabo and can be searched read-only with `grep -a` · evidence: `task-b485f75f`, `config/agy-settings.json:4-24`, `scripts/hub/export_to_sqlite.py:15-17`.
- **WRONG** [`tools/gc_stale_tasks.py:254` vs `tools/host_queue.py:86-99`] : `gc_stale_tasks.py:254` exempts `disk_queue.is_queued(t["id"])` and `budget_queue.is_queued(t["id"])` from Category 1 (`stale pending >30min`), but omits `host_queue.is_queued(t["id"])` and checks only the local host's `.jsonl` queue file (`tools/gc_stale_tasks.py:27-29`), causing tasks queued in `budget_queue` from another host (`task-7311db37`, `task-30ff715e`, `task-43a3c5c2`, `task-c02aee60`, `task-dcbc3859`, `task-1fcc16b5`, `task-0eed0821`) or refused on `disk orange` (`task-897debd6`) to be cancelled after 30 minutes · evidence: `tools/gc_stale_tasks.py:64, 254`, `tools/delegate.py:2249-2258, 2539-2547`, `state/tasks.snapshot.db:1` (`status_cancelled` events).
