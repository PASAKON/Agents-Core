# REPORT task-7c9ac1f6

Implementation prepared in `agent/codex-task-7c9ac1f6`. **Not a completed live rollout.** Order O-20261106-2326-b778 / card Q-20261106-1617-4ea0.

## Changes

- `lib/ph_state.py`: model-free start/end recorder, portable shared-hub state, local PID checks, 10-minute silence classification, task/card waits, native Claude pane classification, count suffix and short status lines. Start records PH session, host, brain/model, one-line doing, supervising turn PID and a unique attempt ID. End records timestamp and exit code, including exceptions and timeout (124). Missing `ORG_DB_URL` refuses an unrecorded production brain turn; no local writable fallback.
- `lib/db.py`: additive `ph_state` table in SQLite and PostgreSQL initialization, including the PostgreSQL schema-current check. No existing table dropped. This is the migration needed by the brief, beyond the task's originally listed touch paths.
- `tools/ph_brain.py`: all current model/fallback attempts pass through the recorder. Direct `invoke_agy` bypass is rejected. `BRAIN_RUNNERS` gives future adapters the same turn door; a fake Codex adapter is exercised by a regression test. No real Codex backend was added. Added `wait --ph ID --ref task-/Q-/QG-/RUN-ID` and host-local `observe` commands.
- `tools/run_watch_driver.py`: reads all hosts from the hub, samples only local native PH panes/PIDs, atomically queues one lane-owner letter per silent incident, and appends ` · PH 🧠N ⏳N 🔴N`. Existing guarded `/rename` runs only when the resulting name changes. PH names are never changed. Native PH metadata comes from existing session/launcher records; an AGY shell pane cannot override the recorded brain state.
- `tools/run_watch.py`: `ph-display [--once] --host HOST` renders short rows; its independent five-second clock shows ⚠️ after snapshot age exceeds 180 seconds. Closed registered sessions are excluded from the PH view.
- `tools/run_watcher.py`: documents that PH telemetry does not enter the model prompt.
- Tests: added `tests/test_ph_state.py`; extended PH brain and Watch driver tests; updated the PostgreSQL schema catalog fixture in `tests/test_db_init_pg_lock.py`.

## Display and token evidence

The implementation selects **local `! bash` output**, not Haiku-authored reports:

```text
! bash scripts/hub/org-python.sh tools/run_watch.py ph-display --once --host contabo
```

The driver submits this through the existing guarded input path, only when PH identity/project/host/state changes and at most once per 60 seconds. Elapsed seconds alone do not trigger another command. Held/busy input is retried without acknowledging an unsent update.

A separate local terminal pane inside the Watch tmux session continuously renders the same snapshot. Its own clock can show stale-data failure when the driver has stopped. The driver recreates a missing display process. This pane does not run a model.

| Measurement | Result |
| --- | --- |
| PH recording model calls | 0 by implementation: database writes only; runner is outside the recorder |
| Simulated one-hour stable PH Watch | One `/rename`, one local `! bash` submission, **0 model prompts**; no repeated submissions |
| Real Watch Haiku turns/hour before | **Not measured** |
| Real Watch Haiku turns/hour after | **Not measured** |

The simulated count is not a claim about measured live Haiku turns. Existing worker-event messages and `/compact` behavior remain and can still consume Haiku turns.

## Validation

Executed with the existing repository virtual environment (system `python3` has no pytest):

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ph_state.py tests/test_ph_brain.py tests/test_run_watch.py tests/test_run_watcher.py tests/test_run_watch_driver.py tests/test_pane_screen.py tests/test_db_init_pg_lock.py tests/test_db_pg_translate.py tests/test_db_hosts_letters.py tests/test_db_snapshot_fallback.py tests/test_db_backend_pg.py tests/test_migrate_tasks_db.py
```

**237 passed, 20 skipped in 19.39s.** PostgreSQL-dependent tests require an isolated `ORG_TEST_DB_URL`; none was configured. `git diff --check` passed.

Evidence includes:

- Every current model in `MODEL_CHAIN` observes a thinking row before invocation and an exit afterwards; raw AGY invocation is refused. A registered fake future Codex adapter crosses the same door.
- `contabo`, `winbox`, and `mac` round-trip in a temporary shared table. The Watch snapshot integration test lists all three and samples only the local native PH.
- Thinking, task/card waiting, idle and silent states; 600/601-second silence and 180/181-second stale boundaries.
- A real disposable child process is killed and its dead PID classifies red. This is **not** a live PH kill drill.
- Native busy/choice/idle screen predicates; AGY shell-pane non-interference.
- One queued lane letter across repeated observations, and no letter from an observation whose turn already ended.
- Watch count transitions, change-only local Bash output, 60-second throttle, held-input retry, and independent stale display after a simulated driver stop.
- Existing Watch lifecycle, low-memory restart, busy-pane safety, worker-event batching, database initialization and migration tests.

## Deployment handoff

1. Publish this branch through the launcher, review the additive migration, and run the normal hub `db.init()` migration before starting the new Watch driver. The first recorded AGY turn also initializes its telemetry table.
2. Deploy the same code with the shared `ORG_DB_URL` and correct existing host identity on Contabo, winbox and Mac. Contabo's Watch lists all hosts without filtering the PH rows.
3. Schedule `tools/ph_brain.py observe` on each spoke using its normal hub Python environment. This is needed for prompt remote PID-death detection and native pane sampling; no spoke timer/service was installed here. Without it, remote active turns still become red after ten minutes but an immediately killed remote PID is not locally probed from Contabo.
4. Explicit card waits currently enter through `ph_brain.py wait --ph ID --ref CARD_ID`; the observer polls the existing Run Inbox reader and clears completed waits. Worker waits are inferred from hub ownership. Automatic discovery of all cards and caller-policy wiring for the new wait verb are not included.
5. Perform the requested real PH thinking → waiting → idle, killed-PID and stopped-driver drills on Contabo, then on winbox/Mac when PHs are available. Capture names and rows, and compare real Watch transcript turn counts over equal before/after one-hour windows.

## Not checked / risk

- **Live drills not performed on any host.** Read-only `tmux -N list-sessions` returned `error connecting to /tmp/tmux-0/default (Operation not permitted)`. No real PH was launched/killed and no Watch service was stopped. No access escalation was attempted.
- Local `! bash` mode is implemented and submission-tested, but its actual installed Claude UI behavior, permissions and Haiku accounting were not verified live. No model-message fallback is enabled.
- The independent stale warning is visible in the local tmux display pane. Whether a phone Remote Control client exposes that sibling pane is unverified; a previous one-shot Bash result in the Claude transcript does not update itself after the driver stops. This is a remaining remote-display limitation.
- Selecting the display pane can defer guarded Claude input until the Claude pane is selected again. Existing safety checks hold input rather than typing into an unexpected prompt.
- Native pane sampling supports tmux surfaces. A Windows native PH outside tmux needs its host surface adapter; not implemented here.
- The stored PID belongs to the synchronous supervising turn process, not the AGY subprocess. PID reuse/start-time identity is not independently verified. No remote PID is probed on Contabo.
- Future adapters must be registered through `BRAIN_RUNNERS`; the fake-adapter regression covers this extension point, not arbitrary future code that deliberately adds a separate launcher.
- Real PostgreSQL execution, delivered owner letters, full CI and **CI fail-set ⊆ main's** were not verified. Tests used temporary SQLite plus PostgreSQL translation/catalog fixtures.
- No PR, merge or production deployment completed. The worker contract assigns committing and pushing to the launcher after this turn. Default branch was not touched. No hooks or settings were changed.

## Blockers

- Live tmux access is denied in this worker environment; live drills and actual before/after Haiku measurement need the deployment owner/runtime.
- Spoke observer scheduling and native Windows surface integration remain deployment/integration work.
- The launcher must commit/push before a reviewable remote PR and CI comparison can be completed. The report does not mark these done.
- No MAILBOX.md was present during checks; no STOP message was received.

## Skill learning

- (none)
