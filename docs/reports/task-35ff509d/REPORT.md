# REPORT task-35ff509d

Independent review of Agents-Core PR #445 (`4b6af024..1d21f0ca`) and MoonieX-Console PR #40 (`ba5b71c..1573789`). Read local git objects only; no fetch, push, merge, or implementation edits. File/line references below refer to the reviewed heads.

## Agents-Core PR #445

- **Blocker — deferred tasks can disappear from the queue.** `tools/budget_queue.py:16–24` performs an unlocked read/modify/write through `disk_queue._save`, which truncates and rewrites the file. Two delegate processes can both read an empty queue and then save their respective single entry: the last write discards the other task. Enqueue racing watchdog pop has the same problem; a crash during rewriting can also truncate the queue. The lost task stays pending without automatic budget retry or GC protection. A barrier-controlled two-thread reproduction retained only `task-a` after both enqueues returned. Use a shared interprocess transaction/lock for enqueue, pop, and rotation, with atomic durable replacement (or a transactional DB queue).
- **Should-fix — a permanently failing head starves every later eligible task.** `runners/watchdog.py:949–950` returns on an exception without rotating or backing off the entry. For example, a queued task's role is removed from its project's `agents_allowed`; delegate raises `PermissionError` at `tools/delegate.py:2459` every time the budget allows retry. Every watchdog tick stops there, indefinitely excluding otherwise runnable tasks. Reproduction with two ready entries and a failing first delegate produced `task-a, task-a, task-a` across three drains. Retain the task with a bounded retry/backoff and permit later entries to progress.
- **Should-fix — dry-run schedules a future real spawn.** `tools/delegate.py:2463–2468` unconditionally enqueues a budget refusal, including `delegate_task(..., dry_run=True)`. With fresh over-budget data, a preview of a pending low-tier task becomes persistent queued work; once ready, `runners/watchdog.py:948` calls delegate without `dry_run` and starts the worker. Guard queue mutation for dry-run and return a preview-only refusal. This is established by control-flow inspection, not a live worker reproduction.

Other requested checks:

- Schema: the CHECK definition includes the new tier event; comparison extracts the literal kind set and recognizes PostgreSQL's normalized CHECK representation. The advisory transaction lock covers migration and the drop/add occurs within the connection transaction. The new projects column participates in the fast-path probe. Targeted fake-PG and SQLite repeat-migration tests passed; live PostgreSQL validation was unavailable. No additional migration blocker found.
- Routing: supplied critical/normal/low matrix, outside-runner fallback, pinned runner, unrouted role, missing/stale snapshot and Thai-day reset tests passed. Critical preserves existing routing; normal filters to eligible under-budget outside runners when gated; low gates on primary buckets. No additional routing blocker found.
- Queue double-spawn: the new drain has no atomic queue claim. Existing delegation guards vary by spawn path; this review does not establish exactly-once spawning under competing drains/manual delegates. The concrete loss and starvation findings above already require changes.
- PH registration: failing closed when the hub is unavailable is acceptable for the stated invariant that every new PH must bind a registry row before starting. Resume also registers before unparking or launching, and preserves the registry tier. This deliberately makes local spawn/resume unavailable without hub access. Resume and spawn-focused tests passed.
- v1 monitor: the only monitor implementation change adds `tier` to the SQL selection; the emitted keys, values, ordering, and serialization code remain unchanged. For identical database state and time, output remains byte-identical; no tier field is emitted. Live DB fixture equality tests were skipped, so this conclusion rests on code comparison rather than a live before/after capture.
- Public-repository review: inspected the complete added diff and searched additions for IPs, URLs, credentials, tokens and SSH references. No newly introduced IP, token value, or private hostname found.

**Verdict: changes needed.**

## MoonieX-Console PR #40

**No blocker found.** No actionable should-fix or nit found in the reviewed changes.

- `src/portfolio/validate.js:84–164` matches the supplied `docs/design/portfolio-monitor-v2.md` field shapes, exact keys, bounds, enum choices, nullability, finite/loop rules and timestamp checks. The order ID pattern enforces the documented structural format.
- Every accepted v2 project is checked through the same v1 projection and row validator used by default GET. Top-level generated time, counts and row cap also satisfy v1. No accepted JSON v2 payload was found whose default projection fails v1 validation.
- `src/portfolio/routes.js:109–121` defaults to v1, returns explicit v2 only when available, and rejects unsupported query versions. Authentication middleware and token comparison are unchanged and still precede query handling/body parsing.
- Validation errors use schema-owned paths, never body values or unexpected key names. Parser errors remain generic; no new response path echoes request content.

**Verdict: approve**, with HTTP integration execution limited by the sandbox as described below.

## Validation performed

- Exported both reviewed commit snapshots into temporary `.review/` directories inside the assigned worktree, so tests used the reviewed heads rather than the worktree's base commit.
- All test and reproduction invocations used `env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR`.
- Core: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_usage_budget_p4a.py tests/test_db_init_pg_lock.py tests/test_delegate_router.py tests/test_spawn_ph_resume.py tests/test_node_dispatch_spawn_ph.py tests/test_portfolio_schema.py tests/test_portfolio.py` completed with exit 0; PostgreSQL-dependent tests skipped. Initial attempts found no `python` binary and no pytest in system `python3`; the existing virtualenv supplied the test dependencies.
- Core: isolated mocked queue reproductions confirmed concurrent lost update and repeated head-of-line exception starvation. No live database or worker spawn used.
- Console: `npm test -- test/portfolio-monitor.test.js` ran against the exported head using existing dependencies. 31 tests passed; 47 HTTP tests failed because socket binding is prohibited (`listen EPERM`), followed by Supertest's null-port error. Vitest also could not write its results cache through the read-only dependency symlink. No HTTP integration pass is claimed.
- Read the provided v2 contract and compared both complete diffs. No network access attempted. No MAILBOX.md was present at the worktree checks.

## Files changed

- `docs/reports/task-35ff509d/REPORT.md` only. Temporary review snapshots and probes were removed. No application code edited.

## Blockers

- Merge blocker for Core: deferred-task loss described above; also address retry starvation and dry-run scheduling before merge.
- Sandbox prevents Console HTTP test listeners. Run its full portfolio test file in an environment permitting local sockets before relying on integration results.
- No live PostgreSQL service was used; schema tests requiring one skipped. Validate migration/fast-path behavior against PostgreSQL in CI.

## Skill learning

- (none)
