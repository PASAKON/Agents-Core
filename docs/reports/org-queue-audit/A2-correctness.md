# A2 — lock and queue correctness

Order O-20261114-1701-56fb; task-e1f4e689. Audit only: no implementation fixes.
Console paths below are relative to `/opt/MoonieXHQ/Projects/MoonieX/Console`;
other paths are relative to the assigned Agents worktree.

## Proven defects

All proof functions are in `tests/test_queue_audit_a2.py`. High means lost work
or broken exclusion; medium means bounded delay, scope leakage, or premature cancellation.
Each proof asserts the desired safe behavior and intentionally fails today.

| Bug | File:line | Scenario and observed result | Proof test | Severity | Fix idea |
| --- | --- | --- | --- | --- | --- |
| A2-001 | `lib/db.py:1365`, `lib/db.py:1368`; PG translation `lib/db_pg.py:397` | A reads absent; B acquires and commits; A overwrites B; both return true. Scratch SQLite executes the forced schedule; PG translation also has an unconditional conflict update (PG not executed). | `test_A2_001_concurrent_acquire_two_winners` (line 34) | High | Conditional atomic upsert using database time and RETURNING; issue fencing generations. |
| A2-002 | `lib/db.py:1453` | Releasing project `alpha_beta` also releases the same task's `alphaXbeta` lock because `_` is a LIKE wildcard. Owner predicate remains intact. | `test_A2_002_project_like_wildcard_releases_other_project` (line 61) | Medium | Escape LIKE metacharacters or store project as a separate equality column. |
| A2-003 | `lib/db.py:1439` | First path commits; second acquisition raises; rollback branch is never reached and the first lock remains. | `test_A2_003_path_exception_leaks_partial_locks` (line 68) | Medium | Acquire the entire set in one transaction with exception rollback. |
| A2-004 | `tools/disk_queue.py:68`, `tools/disk_queue.py:77` | A loads an empty queue, B finishes enqueue, then A saves its stale snapshot and loses B. | `test_A2_004_disk_concurrent_enqueue_loses_entry` (line 81) | High | Serialize read-modify-write or use transactional queue rows. |
| A2-005 | `tools/disk_queue.py:56` | Failure after opening the existing queue for truncating write destroys the previously acknowledged entry. | `test_A2_005_disk_crash_truncates_queue` (line 96) | High | Atomic replacement with durability barriers or a transactional store. |
| A2-006 | `tools/host_queue.py:171`, `tools/host_queue.py:173`, `tools/host_queue.py:177` | Entry is durably removed before get_task raises; lookup is outside the recovery try block. Proof uses the supported local-only queue mode. | `test_A2_006_host_lookup_error_loses_entry` (line 113) | High | Keep a leased claim until lookup and delegation are acknowledged. |
| A2-007 | `tools/host_queue.py:172`, `tools/host_queue.py:178` | Process death between removal and successful delegation leaves no local waiter; BaseException models death without running the ordinary exception requeue. | `test_A2_007_host_crash_before_delegate_loses_entry` (line 124) | High | Persist claim state with a reclaimable lease rather than destructive pop. |
| A2-008 | `tools/gc_stale_tasks.py:254`, `tools/gc_stale_tasks.py:277` | Old local pending task waiting in host queue has no exemption and is selected for cancellation. Dry-run proves selection without deleting worktrees. | `test_A2_008_gc_cancels_host_waiter` (line 139) | Medium | Make GC consult all durable wait/claim records. |
| A2-009 | `tools/quota_reset.py:103`, `tools/quota_reset.py:104`; actual drain `runners/watchdog.py:970` | Reset dispatcher looks for budget_queue.drain, silently skips it, and never attempts the ready budget waiter. Watchdog still drains later: this is a missed immediate wake, not an entirely undrained queue. | `test_A2_009_quota_reset_skips_budget_drain` (line 154) | Medium | Export and call a shared budget drain entry point. |
| A2-010 | `lib/db.py:432`, `lib/db.py:1362`, `lib/db.py:1363` | Without elapsed real time, a second client eleven minutes ahead replaces a ten-minute live lease. | `test_A2_010_clock_skew_steals_live_lease` (line 170) | High | Evaluate expiry and renewal against authoritative database time. |
| A2-011 | `runners/watchdog.py:1025`, `runners/watchdog.py:1028` | Disk entry is popped; delegate raises an ordinary error; watchdog reports it but never restores the entry. | `test_A2_011_disk_delegate_error_loses_entry` (line 191) | High | Retain a claim until acknowledgement and retry failures. |
| A2-012 | Console `src/relay/locks.js:30`, `src/relay/locks.js:78`, `src/relay/locks.js:90` | A live A lock exists; injected read failure becomes empty state; B receives a lock and overwrites A's persisted record. | `test_A2_012_console_read_error_forgets_live_holder` (line 206) | High | Treat only ENOENT as empty; reject acquisitions on unreadable or invalid state. |

## What is correct and why

- Ordinary wrong-owner release cannot delete a hub lock: both key and owner are predicates (`lib/db.py:1375`); `test_owner_guard_and_expiry_control`, `tests/test_queue_audit_a2.py:183`, passes the release-by-B/reacquire-by-B check while A owns it. This is ownership-label checking, not authentication or fencing.
- `find_conflicts` deliberately performs exact normalized path-set intersection, excludes a supplied task, and includes queued_remote among active states (`lib/db.py:1384`, `lib/db.py:1397`, `lib/db.py:1405`, `lib/db.py:1417`). It is advisory discovery, not an atomic reservation.
- A normal false return during path acquisition releases newly accumulated keys (`lib/db.py:1442`); exception handling is the separate A2-003 defect.
- Host enqueue/remove serialize local read-modify-write through a separate flock file and use atomic replacement (`tools/host_queue.py:77`, `tools/host_queue.py:105`, `tools/host_queue.py:111`, `tools/host_queue.py:134`). That protects concurrent writers, not the destructive claim window in drain.
- Budget enqueue/pop/requeue serialize mutations; saving fsyncs a temporary file before replacement (`tools/budget_queue.py:32`, `tools/budget_queue.py:57`, `tools/budget_queue.py:83`, `tools/budget_queue.py:96`, `tools/budget_queue.py:108`). This avoids disk_queue's unlocked stale-snapshot overwrite.
- Budget readiness compares calendar dates in Thai time, not a fixed 24-hour elapsed approximation (`tools/budget_queue.py:118`); retries still pass through delegate (`runners/watchdog.py:982`). Disk and budget waiters are explicitly GC-exempt (`tools/gc_stale_tasks.py:254`).
- Host, disk, and budget all have watchdog drain call sites (`runners/watchdog.py:1412`, `runners/watchdog.py:1416`, `runners/watchdog.py:1424`). No claim that these queues have nobody draining them is justified by source inspection.
- Console acquisition is synchronous within its stated single-writer process and checks live owner/class before writing (`src/relay/locks.js:14`, `src/relay/locks.js:78`, `src/relay/locks.js:80`). HTTP handlers supply the authenticated class (`src/relay/routes.js:386`, `src/relay/routes.js:398`); operator override is intentional (`src/relay/locks.js:102`).
- Console TTL validates integral seconds between 60 and 21600, converts seconds to milliseconds correctly, and ignores records at or beyond expiry (`src/relay/locks.js:74`, `src/relay/locks.js:88`, `src/relay/locks.js:46`). Python's context manager attempts release even when the body raises (`tools/home_lock.py:181`, `tools/home_lock.py:184`).
- Reboot does not inherently make a persisted lease immortal: hub acquisition checks absolute expiry (`lib/db.py:1366`), and Console filters persisted expiry (`src/relay/locks.js:46`). Dead holders may block until TTL; expiry alone neither fences surviving workers nor wakes a waiter (`lib/db.py:1373`; Console `src/relay/locks.js:98`).
- Quota publication uses a transaction-scoped advisory lock and a durable-event duplicate query before insert (`tools/quota_reset.py:135`, `tools/quota_reset.py:136`). This is distinct from the missing budget wake in A2-009.

## Validation

Ran `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_queue_audit_a2.py`:
**12 failed, 1 passed**, all final failures are the intended safety assertions, no skips.
The first run exposed an incomplete GC fake; the final test stubs terminal-lock cleanup
at `tests/test_queue_audit_a2.py:150`, preventing unrelated DB access.
Fixtures use scratch SQLite/files and monkeypatches (`tests/test_queue_audit_a2.py:17`);
Console proof executes the actual JS source with the config import replaced and an
explicit temporary file (`tests/test_queue_audit_a2.py:206`). No HTTP or model calls.
The brief's `tests/conftest.py` has moved to root `conftest.py` (its explanatory comment
at `conftest.py:305`); existing root isolation fixtures apply automatically.

## Not checked / risk

- No live PostgreSQL, multi-host process stress, actual SIGKILL/reboot, power-loss durability,
  or production-state inspection. Interleavings and failures are injected at the real
  code boundaries listed above. PG A2-001 applicability is source-based (`lib/db_pg.py:397`).
- `relay_queue` / `relayQueue` / `relay.queue` searches in the supplied Console `src`
  found no implementation; its SQLite claim/recovery protocol could not be audited.
  This is a checkout/scope limitation, not proof that production has no queue.
- Other `state/locks/` protocols and the resource kinds listed in the brief were not
  supplied as audit implementations; no absence or reboot-recovery claim is made about them.
- Hub queue mirroring is optional and errors are swallowed (`tools/host_queue.py:21`,
  `tools/host_queue.py:38`, `tools/host_queue.py:70`); A2-006/007 prove local-only loss,
  not a comprehensive mirrored-mode recovery test.
- Absolute wall-clock expiry still depends on clock behavior; Console uses one server's
  Date.now (`src/relay/locks.js:71`), while hub clients compute their own (`lib/db.py:1363`).
  Long-running work's renewal/fencing discipline was not exercised.
- Read-only instructions were interpreted with the explicit exception authorizing this
  one new regression test file; only that file and the two required reports were authored.

## Skill learning

- Queue-file atomicity is not claim durability: the atomic save at `tools/host_queue.py:172`
  still loses work when execution dies before `tools/host_queue.py:178` (A2-007).
- A deterministic interleaving can prove a race without timing-sensitive sleeps:
  `tests/test_queue_audit_a2.py:34` forces the stale read and observes two successful owners.
