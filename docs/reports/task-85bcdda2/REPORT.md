# REPORT task-85bcdda2

Verdict: **changes needed**.

Independent review of PR #448, exclusively `f58ee07a..25bdcaec`. Line references below refer to `25bdcaec`, not this report worktree. Read the worker brief, plan sections 1–4 and 8, and v2 contract. No implementation files were edited and no snapshots were exported.

## Blockers

- No access blocker prevented the source review. No live database, services, or external credentials were used.
- Full scoped pytest validation was not performed: the assigned worktree is at `4b6af024`, not `25bdcaec`. Running its tests would test the wrong tree. The instruction to review via git without exporting a snapshot, together with the assigned-worktree restriction, was preserved. The in-memory checks below are targeted reproductions, not a pytest pass or PostgreSQL integration validation.

## Should-fix

1. **P2 — A milestone replan corrupts the project's original CEO due date.** `lib/portfolio.py:917–919` stores the target milestone's old date into the project-wide `due_first_at`, even when `n != 0` and the project's own due date has not moved. Reproduced with a CEO project due October 30 and milestone 1 due October 27: moving that milestone to October 28 sets `due_first_at` to October 27. Subsequently moving the project to November 1 retains October 27 because of `COALESCE`. The v2 widget then falsely reports that the CEO's original project deadline was October 27. Preserve the original project/effective CEO deadline only when that deadline changes; milestone history must not consume this project-wide field. Add a test with distinct milestone and project dates, followed by a project replan.

2. **P2 — Explicit resume tier is still rejected by the public CLI.** `tools/spawn_ph.py:901–906` includes `args.tier` in the incompatible-resume arguments and never passes a tier to `resume`. Executing the target `main` with `--resume 12345678 --tier critical --dry-run` exits 2 before reaching resume. The correction at `tools/spawn_ph.py:466–487` allows a manually constructed registration plan to carry a tier, but `resume()` at line 857 has no tier parameter and its plan does not receive one. Thus the requested explicit `--tier` behavior is not reachable. Allow and forward the option through CLI, resume, and registration; test the public route. Resume without schedule arguments remains supported.

3. **P2 — The new ready gate does not cover mesh-created PHs.** The gate added at `tools/spawn_ph.py:541` protects `spawn`, but `main` dispatches `mesh` separately at lines 883–884. `_mesh_main` at lines 753–766 accepts no schedule and sends only lane/session/project; `spawn_from_mesh` at lines 674–684 creates a plan, writes its claim, and launches without either `ready_schedule` or `_register_project`. A new remote PH can therefore start without kind, due/cadence, or a registry row. This route predates the diff; the finding is the missing coverage of the new “new spawn needs schedule” requirement, not a claim that this PR introduced mesh spawning. Carry the schedule through the dispatch and enforce/register it at the receiving boundary, or explicitly refuse new mesh spawns until that is supported.

## Nits

- None.

## Other review results

- **Migrations:** `lib/db.py:369`, `:773`, `:859` add the project/milestone migration lists and schema-current requirements; tasks use the existing migration list. `lib/db_pg.py:48` contains CREATE statements only, with no ALTER. All 32 PG_SCHEMA statements match `_PG_CREATE_RE` using the production statement splitter. The migration loops check existing columns, and the SQL artifact uses `IF NOT EXISTS` plus drop/re-add of the event constraint inside a transaction. `docs/design/projecttrack-p1-ddl.sql:3–34` matches the code's column definitions, orders table/indexes, and event constraint, and includes the requested grant. Actual PostgreSQL execution/idempotence was not exercised.
- **Replan:** `lib/portfolio.py:896–916` rejects negative milestone numbers, normalizes aware timestamps to UTC, uses the absolute delta for the two-day PH limit (including earlier moves), and rejects PH changes to a CEO project date for both project and milestone targets. C-level roles can move either target. `COALESCE` sets due history once, but with the wrong source in finding 1.
- **Orders:** `lib/portfolio.py:953–1015` generates the required Bangkok timestamp plus four hex characters. State precedence, linked milestone completion with evidence, percentage fallback to project milestones, worker/heartbeat detection, and close handling were inspected. `tools/portfolio.py:104–135` rejects PH order take/link/close in `authorize`; lines 383–405 check both existing and destination projects for link/close. The existing flag-controlled enforcement pattern is retained, so authorization refusals remain advisory when enforcement is disabled, as required by the brief.
- **Monitor:** `_monitor_all` and `monitor_rows` are byte-identical to the base. The version-1 output construction at `lib/portfolio.py:852–855` is unchanged. Inspected v2 exact key sets, string limits/control sanitization, nullable fields, UTC formatting, 20/20/10 list caps, counts before capping, active-only no-plan detection, strict >30-minute unlinked-order detection, three-day closed-order retention, and loop deadline calculation at lines 1038–1110. No additional contract defect identified beyond the incorrect `due_moved_from` value in finding 1. `tools/portfolio_push.py:87–90` opts into v2 only for the exact environment value `2`.
- **Spawn/card:** `tools/spawn_ph.py:520–554` gates local new spawns before planning and binds their schedule to card arguments. Card construction at lines 691–721 includes the schedule; both shell wrappers forward arguments to Python. Resume reuses the schedule and registry row. Findings 2 and 3 describe remaining coverage gaps.
- **Task association:** `lib/portfolio.py:869–884` wraps resolution in `except Exception`, returns null on lookup/input failures, prioritizes a first-block project line, then resolves the PH session. `lib/db.py:1138–1147` inserts the returned nullable id. Ordinary lookup failures therefore do not escape into `create_task`; this integration was inspected, not executed end-to-end.
- **Public-repository scan:** reviewed added source, tests, DDL, and implementation-report lines. No added credential, IP address, private hostname, or personal-data disclosure identified.

## Validation performed

- Read target files using `git show 25bdcaec:<path>` and the requested base-to-head `git diff`; no fetch or checkout changes.
- `git diff --check f58ee07a 25bdcaec` passed.
- Ran Python heredoc checks with `env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR PYTHONDONTWRITEBYTECODE=1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -`. Target function definitions were selected from `git show` with AST and executed in memory with explicit test doubles; no repository modules from the current checkout were imported.
- Reproduced finding 1 using the exact target replan function and an in-memory SQLite database, with transaction/event/role dependencies stubbed. Confirmed the incorrect date survives a subsequent project replan.
- Reproduced finding 2 using the exact target CLI `main`; observed argparse exit 2 before resume.
- Asserted byte equality of the base/target v1 monitor engine source.
- Asserted code/DDL agreement for migration columns, orders CREATE statements, and event constraint. An initial ad hoc semicolon split rejected a SQL comment; rerunning with the target `_split_statements` passed all 32 statements. This was a check-harness correction, not a product failure.
- Read mailbox between review steps when present; no mailbox was present.

## Files changed

- `docs/reports/task-85bcdda2/REPORT.md` only.

## Skill learning

- (none)
