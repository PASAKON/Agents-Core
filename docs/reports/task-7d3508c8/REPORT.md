# REPORT task-7d3508c8

## Summary

Added a per-key FIFO wait queue to `tools/home_lock.py` (with zero changes to `MoonieX-Console` or `lib/lease.py`) so callers needing a busy browser home (`home:<host>:<port>`) wait in arrival order instead of failing immediately or requesting a new CEO login:

1. **`acquire <key> --wait <seconds>` and `home_lock(key, ..., wait_s=...)`**:
   - When `wait_s` is `0` / omitted, behaviour is unchanged (single immediate `POST /api/relay/locks/acquire` call; raises `HomeLockHeld` on `409`).
   - When `wait_s > 0`, the caller records a FIFO ticket for `<key>` and waits using a plain process sleep loop polling every 10–15 s with jitter (`POLL_MIN_S = 10.0`, `POLL_MAX_S = 15.0`).
   - Retries the real acquire (`POST /api/relay/locks/acquire`) only when the caller is first in line (`position == 1`) and the lock is free or expired.
   - On timeout, removes the caller's ticket and exits `2` (`HomeLockHeld`) with `"still queued behind <owner>, position N"`.
2. **Per-key FIFO ticket persistence and dead-waiter pruning**:
   - Tickets are stored per key in `state/home-queue/<key-safe>.jsonl` protected by `fcntl.flock` (`LOCK_EX`) plus an intra-process thread lock. (File-based queue on Contabo is used for v1 since `lib/db.py` does not expose a generic queue helper and `tools/home_lock.py` is stdlib-only.)
   - Before every queue read/touch, any ticket whose PID/owner is gone (`os.kill(pid, 0)` / `/proc/<pid>/stat` zombie check) or whose heartbeat is older than `120 s` (`HEARTBEAT_TTL_S = 120.0`) is dropped automatically.
3. **`home_lock.py queue <key> [--json]`**:
   - Prints current lock holder and queued FIFO waiters (`owner`, `purpose`, `waited <N>s`).
4. **Tests (`tests/test_home_lock_queue.py`)**:
   - Uses a fake lock transport and fake clock to verify:
     - 3 waiters acquire the lock strictly in arrival order (`waiter-1`, `waiter-2`, `waiter-3`) and non-first waiters do not retry `acquire`.
     - Dead waiters (both dead PID and stale heartbeat > 120 s) are skipped.
     - Timeout exits with code `2` and `"still queued behind <owner>, position N"`.
     - Existing behaviour without `--wait` is unchanged.
     - `home_lock(..., wait_s=...)` context manager and `home_lock.py queue <key>` CLI output.

## Files changed

- `tools/home_lock.py`
- `tests/test_home_lock_queue.py`
- `docs/reports/task-7d3508c8/REPORT.md`

## Validation performed

Static verification of all code paths and test cases across `tools/home_lock.py`, `tests/test_home_lock_queue.py`, `tests/test_home_lock.py`, and `tests/test_home_lock_lease.py`. Per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process. ... never sed, find, python or rm"), shell execution of `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_home_lock_queue.py tests/test_home_lock*.py` is left to the review harness (expected totals: `16 passed` — 5 in `tests/test_home_lock_queue.py`, 6 in `tests/test_home_lock.py`, 5 in `tests/test_home_lock_lease.py`).

## Not checked / risk

- Pytest shell execution was not run directly in the AGY worker session because the AGY Remote Worker Contract restricts running `python` in print mode; the review process runs `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_home_lock_queue.py tests/test_home_lock*.py`.
- Queue files live under `state/home-queue/<key-safe>.jsonl` with `fcntl.flock`, which coordinates waiters on the same host (Contabo-only for v1); cross-host waiters do not share local filesystem state until the queue is moved to the hub or `lib/lease.py` cutover (Phase C3).

## Blockers

- (none)

## Skill learning

- (none)
