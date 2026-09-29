# REPORT task-350e4165

## Summary

Built the read-only fallback for the org ledger (Org Mesh W1.7): a new
`scripts/hub/export_to_sqlite.py` writes a periodic SQLite snapshot of the
Postgres hub; `lib/db.py`'s `get_conn()` now falls back to that snapshot
(read-only) when `ORG_DB_URL` is set but the hub is unreachable, and raises
a new `HubUnavailable` for a write through the fallback or for no usable
snapshot at all; scheduler files (launchd + systemd, files only) trigger the
export every 15 minutes; `hook-self-repo-guard.py` now routes through the
fallback and stays fail-closed exactly when the brief requires; `hook-log-
prompt.py` needed no change (already routes through `lib.db` and is already
fail-open by its existing broad `except`); `hook-memory-nudge.py` needed no
change because it does not read the ledger at all (see Notes for Reviewer).
New test file `tests/test_db_snapshot_fallback.py` covers every scenario in
the brief. Full suite: 2826 passed, 4 failed (1 expected pre-existing +
3 unrelated pre-existing, see Issues/Blockers), 25 skipped.

## Files Changed

- `lib/db.py` — added `SNAPSHOT_PATH`, `HUB_CONNECT_TIMEOUT_S`, `HubUnavailable`,
  the snapshot-meta helpers (`init_snapshot_meta`, `write_snapshot_meta`,
  `read_snapshot_meta`), `_SnapshotConnection`, `_open_snapshot_fallback`, and
  a rewritten `get_conn()` that falls back to the read-only snapshot on a hub
  connect failure. `sqlite_connect()` is untouched. `ORG_DB_URL` unset takes
  the same `_connect()` branch as before, byte-for-byte.
- `scripts/hub/export_to_sqlite.py` (new) — reads the hub via `lib.db_pg.connect()`
  directly (not `lib.db.get_conn()` — see Notes for Reviewer), writes
  `tasks`, `c_level_sessions`, and the last 30 days of `events` atomically
  (temp file + `os.replace`) into a snapshot built with `lib.db`'s own
  schema/init. Exit 0 + "hub not configured" when `ORG_DB_URL` unset; exit 1
  (old snapshot preserved) when the hub is unreachable or unreadable.
- `scripts/com.mooniex.org-snapshot.plist` (new) — launchd scheduler, Mac,
  every 900s, shaped like `scripts/com.mooniex.agents-watchdog.plist`. Files
  only — not installed by this task.
- `deploy/systemd/org-snapshot.service` (new) + `deploy/systemd/org-snapshot.timer`
  (new) — systemd scheduler, Contabo/Linux, every 15 minutes,
  `EnvironmentFile=/root/.config/mooniex/org-db.env`. Files only.
- `scripts/hook-self-repo-guard.py` — `load_touches()` now reads through
  `db_lib.get_conn()` and converts the new `db_lib.HubUnavailable` into the
  existing fail-closed `GuardError` path. Removed the now-dead
  `HubUnreachable` fail-open carve-out (superseded by the transparent
  snapshot fallback inside `get_conn()` itself — see Notes for Reviewer).
  `ArchivedHub`/`ArchivedDB` (the tasks.db-is-a-directory sentinel) is
  unrelated and untouched.
- `tests/test_db_snapshot_fallback.py` (new) — covers every scenario in the
  task brief's Tests section (see below).

## Commits

- `a5b642bb` — lib/db: read-only snapshot fallback when the org ledger hub is unreachable
- `19314165` — scripts/hub: export_to_sqlite.py writes the org ledger snapshot
- `d2d2ea6b` — deploy: scheduler units for the org ledger snapshot export (files only)
- `56359801` — hook-self-repo-guard: route through lib.db's snapshot fallback, stay closed
- `58d99d2d` — tests: cover the org ledger snapshot fallback (Org Mesh W1.7)

## Tests

- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (full suite, no `-q`)
- passed: 2826
- failed: 4
- skipped: 25

New file alone: `.../.venv/bin/python -m pytest tests/test_db_snapshot_fallback.py -p no:warnings` → **12 passed, 1 skipped** (the skip is the `ORG_TEST_DB_URL`-gated Postgres export test — no such server on this box).

### The 4 full-suite failures

1. `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`
   — the ONE failure the task brief named as known/pre-existing/unrelated. Confirmed unrelated: compares this box's `~/.claude/plugins/installed_plugins.json` against a baseline list; nothing to do with the ledger.

2. `tests/test_mesh_check.py::test_check_l0_green_when_sources_agree`
3. `tests/test_worker_naming.py::test_current_host_defaults_to_mac`
4. `tests/test_worker_naming.py::test_current_host_blank_org_host_falls_back_to_mac`

   These three were **not** in the brief's known-failure list, so I verified
   before treating them as unrelated: none of the three, nor `lib/config.py`'s
   `self_host()` they depend on, references `lib.db`, `lib.db_pg`,
   `HubUnavailable`, or any file I touched. They fail identically run in
   isolation (`pytest tests/test_mesh_check.py::test_check_l0_green_when_sources_agree
   tests/test_worker_naming.py::test_current_host_defaults_to_mac
   tests/test_worker_naming.py::test_current_host_blank_org_host_falls_back_to_mac`
   → same 3 failures, nothing else). Root cause: `self_host()`
   (`lib/config.py:270`) resolves through several sources beyond `ORG_HOST`
   (node.yaml, ROOT-matched `agents_root`, platform), and on this actual
   Contabo box one of those legitimately resolves to `"contabo"` — but both
   tests hardcode the expectation that clearing/blanking `ORG_HOST` falls
   through to `"mac"`. That assumption only holds on a Mac checkout; it does
   not hold on a real Contabo box regardless of my changes. Pre-existing,
   environment-specific, out of my task's file scope (`lib/config.py`,
   `tests/test_worker_naming.py`, `tests/test_mesh_check.py` — none listed in
   my brief) — left untouched per the "stay inside the listed files" rule.

## Issues / Blockers

- The 3 extra pre-existing failures above (`test_mesh_check.py`,
  `test_worker_naming.py` ×2) are real and reproducible on this box but are
  outside this task's file scope and unrelated to the ledger/snapshot work.
  Flagging for the CTO rather than silently fixing out-of-scope files.
- `hook-memory-nudge.py` was **not modified**: the task brief lists it among
  the three hooks that "must route reads through lib.db" today, but a full
  read plus `git log --oneline -- scripts/hook-memory-nudge.py` (since its
  creation at `e8fe0aea`) confirms it has never read the task ledger — it
  only reads/writes its own `state/session-nudge-counters.json`. There is no
  ledger read in this file to route. No code change made; covered instead by
  a timing-only test confirming it stays fast and unaffected by
  `ORG_DB_URL` (see `tests/test_db_snapshot_fallback.py::test_hook_memory_nudge_timing_unaffected_by_hub`).

## Notes for Reviewer

- **Global connect-timeout default changed.** `get_conn()`'s Postgres branch
  now defaults `timeout` to `HUB_CONNECT_TIMEOUT_S` (3.0s) instead of
  falling through to psycopg's own ~10s default, for **every** caller that
  doesn't pass its own `timeout` — not just the two hooks that already
  passed `timeout=3.0` explicitly. This is a deliberate reading of the task
  brief's "connect timeout of 3s or less" and the design doc's own latency
  budget (measured Mac↔Contabo RTT ~127ms per `docs/design/tasks-db-hub.md`
  §1), applied in `get_conn()` rather than in `db_pg.connect()`'s own
  default so it doesn't affect the other direct `db_pg.connect(timeout=10)`
  callers (`scripts/hub/verify_migration_counts.py`,
  `scripts/migrate_tasks_db.py`, and this task's own `export_to_sqlite.py`).
  Please confirm this is the intended scope — it changes behavior for every
  existing `get_conn()` call site under `ORG_DB_URL`, not just the ones this
  task was scoped to.
- **`export_to_sqlite.py` deliberately bypasses `lib.db.get_conn()`** and
  calls `lib.db_pg.connect()` directly. Using `get_conn()` here would let the
  export "succeed" by silently re-reading the very snapshot it's supposed to
  refresh whenever the hub is down, defeating the brief's "exit non-zero if
  hub unreachable" requirement. See the comment at the `db_pg.connect()`
  call site in that file.
- The old `HubUnreachable` fail-open carve-out in `hook-self-repo-guard.py`
  is now dead code and was removed rather than left stubbed — with the
  snapshot fallback living inside `get_conn()` itself, a merely-unreachable
  hub (with a usable snapshot) now reads through transparently and no
  longer needs special handling in this hook at all. The only new case this
  hook has to think about is `HubUnavailable` (hub down **and** no usable
  snapshot), which is exactly the "cannot read from either place" condition
  the brief says must stay fail-closed — and does.
- Scheduler files are intentionally not installed anywhere (no `launchctl
  load` / `systemctl enable` run) — files-only per the brief.

## Skill learning
- WRONG [no owner] : task brief said `hook-memory-nudge.py` "reads the ledger today" (one of three hooks needing lib.db routing) · evidence: task-350e4165, `git log --oneline -- scripts/hook-memory-nudge.py` since creation at `e8fe0aea` shows it has never imported `lib.db` — it only reads/writes `state/session-nudge-counters.json` · fix: a future Org Mesh W1.x brief that lists hooks "in scope for ledger routing" should be checked against `git grep -l "lib.db\|lib\.db_pg" scripts/hook-*.py` first, not assumed from the hook's name/purpose.
- MISSING [no owner] : full-suite pre-existing-failure list for Contabo runs is incomplete — brief named only `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`, but `tests/test_mesh_check.py::test_check_l0_green_when_sources_agree` and `tests/test_worker_naming.py::test_current_host_defaults_to_mac` / `test_current_host_blank_org_host_falls_back_to_mac` also fail unconditionally on this box (verified in isolation, unrelated to any ledger code) · evidence: task-350e4165 REPORT.md "Tests" section, `lib/config.py:270` `self_host()` resolving to `"contabo"` via a non-`ORG_HOST` source · fix: whichever skill/doc tracks "known pre-existing failures to ignore on Contabo" should add these three so the next worker doesn't have to re-derive it.
