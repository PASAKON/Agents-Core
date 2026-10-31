# REPORT task-970c5548

Implemented the additive v4 portfolio monitor and pusher opt-in. No services
were deployed or restarted, and no push was performed.

## Files changed

- `lib/portfolio.py`: v4 project workers, opening time, stage and review count;
  order role and project closure; C-level work, host resources, parked PHs;
  public text sanitization; compact UTF-8 128 KB cap and ordered list shedding.
- `tools/portfolio_push.py`: explicit version 4, retaining the default and older versions.
- `tests/test_portfolio_v4.py`: synthetic contract tests and an optional real-PG integration test.
- `tests/test_portfolio_monitor_v3.py`: unknown-version rejection now uses 5,
  because 4 is supported. Existing legacy output assertions are unchanged.
- `docs/design/portfolio-monitor-v4.md`: public contract, limits, data-source
  behavior and deployment sequence.
- This report.

## Validation performed

Used the prescribed Python interpreter, `env -u WORKER_TASK_ID`, and
`pytest -o addopts=""`.

- Full `tests/test_portfolio*.py` run before the last four additional assertions:
  **219 passed, 171 skipped, 2 setup errors**. Both errors are existing HTTP
  socket tests denied by the sandbox, not assertion failures.
- Final same suite excluding exactly those two socket tests:
  **223 passed, 171 skipped, 2 deselected**. This includes **41 passing v4 tests**.
- New tests cover all new keys, states and stage mappings, caps, owner filtering,
  review counting, host fallback and load basis, parked/live exclusion, order
  roles and closure boundaries, legacy empty-body bytes, and size-drop order
  including the final failure case and a real 128 KB UTF-8 measurement.
- `git diff --check`: clean.
- Read the supplied contract first and consulted the private mockup sources
  read-only. No private source or snapshot was copied into the repository.
- `tools/host_fill.py` was not changed.

## Synthetic sample v4 payload

An illustrative host with one C-level task and one parked head, with no
currently displayed projects or orders:

```json
{
  "v": 4,
  "generated_at": "2026-10-14T03:20:00Z",
  "counts": {"in_progress": 0, "parked": 0, "late": 0, "waiting_ceo": 0, "no_plan": 0},
  "attention": [],
  "projects": [],
  "orders": [],
  "unlinked_ph": [],
  "clevel_work": [
    {"lane": "cto", "title": "Synthetic task", "state": "running", "host": "node-a", "created_at": "2026-10-14T03:00:00Z"}
  ],
  "hosts": [
    {"name": "node-a", "online": true, "fill_pct": 26, "fill_basis": "load", "ram_free_gb": 2.5, "disk_free_gb": null, "waiting_host": 0, "sessions": 1}
  ],
  "parked_ph": [
    {"sid": "aaaa1111", "project": "sample", "host": "node-a"}
  ]
}
```

## Not checked / risk

- Real PostgreSQL tests (including populated legacy golden comparisons) could
  not run; `ORG_TEST_DB_URL` was unavailable. Database integration still needs
  a run on a throwaway PostgreSQL 16 instance.
- Actual host probes, production lock files, and Console acceptance were not
  exercised. Host probes in tests are mocked.
- The current host collector omits disk-free readings, so that field is null.
  Unix CPU-to-load labeling follows the current probe implementation and host
  registry OS; a future probe change should update that mapping.
- The two socket tests require an environment permitting localhost listeners.
- CLI monitor version choices are unchanged; v4 is exposed by the library and
  pusher as requested.

## Blockers

- No commit SHA: `git add` and `git commit` failed because the worktree's
  shared Git metadata is read-only (`index.lock` cannot be created). Changes
  remain in the assigned worktree for the launcher to commit. No push occurred.
- Docker socket access was denied. No existing database answered at the
  requested test port. Installed PostgreSQL 16 could not be started as an
  unprivileged account because the sandbox denied ownership/group changes.
  No production database was touched.
- Sandbox policy denied creation of localhost sockets for two existing tests.
- Request: rerun the full suite with a throwaway database and localhost socket
  access before deployment.

## Skill learning

- (none)

Hard part: preserving legacy payload behavior while adapting incomplete host
readings and enforcing deterministic byte-based shedding.
