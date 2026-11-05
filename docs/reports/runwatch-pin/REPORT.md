# RunWatch: one pinned Watch session per host (task-34996640)

Order O-20261103-2239-23d8, owner project run-watch (PH#58eb5246). Branch `agent/developer-task-34996640`.
The live `runwatch-*` tmux session was not touched.

## What changed

| # | CEO ask | Where | How |
|---|---|---|---|
| 1 | Name `🌐 Watch Runs: 0🔴`, no `#id3` | `lib/session_names.py`, `tools/run_watch.py` | `watch_name(n, light, host)` (the `sid` argument is gone). `format_watch_name(n, light, host=)` keeps the winbox ASCII form: `Watch Runs: 0 idle`. `light` lost its `--sid` flag. The reader `_WATCH_RE` takes both the new and the old `Watch#a1b Runs: …` shape; `parse_short` gives `("watch", "")` for the new one, and `live_sessions` already handles an empty id (`tail.startswith("")`). |
| 2 | One conversation per host | `tools/run_watch_driver.py`, `tools/run_watcher.py` | `driver.json` keeps `uuid`. `build_claude_argv(session_id=, resume=)` ends in `--session-id <uuid>` on the first start and `-r <uuid>` on every later one, with `--remote-control <name>` and `-n <name>` both set to the current name. `resume` is true when `~/.claude/projects/<slug of ROOT>/<uuid>.jsonl` exists, else `--session-id` again (a first launch that died before its first message left nothing for `-r` to open, and `-r` would fail). |
| 3 | Always up, killed only for low memory | same | `decide_lifecycle` never returns `stop`: a missing session is started even with 0 runs, a live one is left alone. The driver kills it only when `MemAvailable < RUN_WATCH_KILL_AVAIL_MB` (default 350); the start limit stays 700, so the kill and the next start cannot flap. That kill resets `start_count`, so it does not use up the one restart. `close_after_s` / `RUN_WATCH_CLOSE_AFTER_S` and the stop-flush logic (`flush_ticks`) are removed. |
| 4 | Cap the context | `tools/run_watch_driver.py` | With an event pending and a ready prompt, if the transcript grew by `RUN_WATCH_COMPACT_TOKENS` (default 60000, estimated as bytes / 4) since the last compaction, the driver types `/compact` instead of the event line; the event goes in on a later tick. The size at that moment is `compact_base` in `driver.json`, because compaction appends to the transcript instead of shrinking it. |
| 5 | Tests | four test files | see below |

One addition the brief did not name: the old crash-loop guard (restart once, then `give_up` and a line in `state/steward/<host>/open.md`) relied on the "run cycle" ending to reset. With an always-up session there is no cycle, so a host would give up for good after two deaths a week apart, or restart every minute if it reset on idle. `forget_deaths` (pure, tested) resets the count after `RUN_WATCH_STABLE_S` (600 s) up, and after `give_up` the host tries again `RUN_WATCH_RETRY_S` (3600 s) later.

`available_mb()` now raises `ValueError` when `/proc/meminfo` has no `MemAvailable:` line, instead of returning 0. 0 would have read as "kill the session" now that low memory kills. The start path already treated `ValueError` as "MemAvailable unreadable".

## Tests

Run: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_run_watch.py tests/test_run_watcher.py tests/test_run_watch_driver.py tests/test_session_names.py` → 219 passed.
Wider run over the 37 test files that import `session_names`, `live_sessions`, `run_watch*`, `run_liveness`, `rename_service`, `coo_dispatch` or `wake_audit`: 2048 passed, 130 skipped, 1 xfailed, 1 failed. The failure is `tests/test_coo_gate.py::test_coo_ask_run_hub_error_comes_back_as_ok_false`: it refuses because `WORKER_TASK_ID` is set in a worker's environment. It passes with `env -u WORKER_TASK_ID`; it is not this change.

New or rewritten tests (the five asks in the brief):
- name format: `test_session_names.py` (writer strings, cut at 32, reader accepts old and new), `test_run_watcher.py::test_winbox_ascii_watch_name_and_cli_light`.
- first start `--session-id`, later `-r` with the same uuid and the same `--remote-control` name: `test_first_start_creates_the_conversation_and_every_later_start_resumes_it`, `test_a_start_with_no_stored_conversation_creates_it_again`, `test_launch_argv_builder_output`.
- idle host starts one and never kills it: `test_idle_host_starts_one_session_and_never_stops_it`, `test_lifecycle_session_is_always_up_and_never_stopped`.
- low-memory kill then resume keeps the uuid: `test_low_memory_kills_the_session_and_the_next_tick_resumes_the_same_conversation`, plus `test_memory_between_the_kill_and_the_start_limits_changes_nothing` and `test_dry_run_never_kills`.
- compact only past the threshold, before the event line, only at a ready prompt: `test_compact_is_typed_only_past_the_threshold_and_before_the_next_event_line`, `test_compact_waits_for_a_ready_prompt`.
- crash-loop guard: `test_restart_give_up`, `test_forget_deaths_after_a_stable_stretch_and_after_the_retry_wait`.

Fails-without-the-change check (each mutation applied to the committed code, the named test files run, then restored): compact `>=` → `>` (1 failed); never compact (2); always `--session-id` (2); new uuid every start (4); kill limit = start limit (1); low-memory kill counted as a death (1); idle host stops (1); no stable reset (1). Every mutation was caught.

## Not checked / risk

- **Does `claude -r <uuid>` keep the same claude.ai Remote Control session? Not proved end to end.** I did not launch a real `--remote-control` session: it would register a session on the CEO's claude.ai account and I was told not to touch the live one. What I did: read the installed binary (`/root/.local/share/claude/versions/2.1.318`, `strings`-style `grep -a`). It stores the bridge session pointer in the transcript and, on resume, re-attaches to it: `[bridge:repl] Attaching ${M} with the host's work secret`, a `reattachOrFail` / `reattachSessionId` path, and a guard `localHolderGuard: {mode:"decline"}` that skips re-attaching when `[bridge:repl] bridge session ${M} from the resumed transcript is still served by local pid …`. So by the code the same session is meant to come back, but I read minified JS and ran nothing. Two things could still break the pin: the server may have dropped the bridge session if the session was down long, and the guard declines to attach if the killed `claude` process is still alive when the next tick resumes. **A 5-minute check for the operator:** start the pinned session, note its URL in the Claude app, `tmux kill-session -t runwatch-<host>`, wait one tick, and see whether the same entry comes back with the same URL.
- Not run live: `/compact` typed into a real Haiku pane. It goes through `rename_service.type_rename` like `/rename`, but I did not watch a real prompt take it, nor confirm that a compaction shows as "turn running" so the event line waits for it.
- Not checked: whether a typed `/rename` also renames the claude.ai Remote Control title (the RC name is fixed at launch from the then-current count and light); if not, the pin keeps the launch name there while the local name follows the count.
- The 60000-token trigger is bytes / 4 of the jsonl, not real tokens. It over-counts (JSON around each message), so compaction comes early; the real context was not measured.
- A session already running from before this change has no `uuid`: the driver adopts, renames and keeps it, but cannot compact it, and the pinned conversation only begins at its next start. To switch at once an operator kills `runwatch-<host>` (not done here). The unit file did not change.
- Windows: the driver reads `/proc/meminfo`, so it is still Linux only (the timer is installed on Contabo). The winbox name form is covered by tests, not by a winbox run.
- I did not read the wiki (`IRON-RULES.md`, playbooks): the wiki roots are not mounted in this worker (`wiki 'mooniex' not available`, `wiki 'org' not available`). I followed the brief and the code.
- No `git push` and no PR opened (worker rule 2); the branch is ready for CTO Main.

## Reach list (callers of what I touched)

- `session_names.watch_name`: only `run_watch.format_watch_name` (and the `lib.config` re-export). `_WATCH_RE`/`parse_short`: `tools/live_sessions.py:192`, `runners/coo_dispatch.py:328,340` (both survive an empty id).
- `run_watch.format_watch_name`, `light --sid`, `close_after_s`: only the watcher/driver and their tests.
- `run_watcher.decide_lifecycle`, `next_start_count`, `WatcherCycle`, `build_launch_argv`, `build_claude_argv`: the driver and tests only (signatures changed on purpose; `session_id` is a required keyword, so a stale caller fails loudly).
- Docs updated: `docs/ops/run-watch.md`, `docs/ops/live-sessions.md`. `roles/run_watch.md` and the `CTO_Procedure_RunWatch` skill needed no change.
