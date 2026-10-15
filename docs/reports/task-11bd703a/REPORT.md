# REPORT task-11bd703a

## Summary

Implemented Run Watch part B (watcher code, light/count with sticky red state, pure lifecycle decision function, pure launch argv builder, role prompt, CTO procedure skill, and pytest suite) without starting any live process, tmux session, or service.

## Files Changed

- `tools/run_watch.py` — Added `compute_light` (`light_and_count`), `acknowledge_runs` (`ack_runs`), `state_file`, `format_watch_name` (`watch_light_name`), `close_after_s`, and the `light [--json]` CLI subcommand; wired `status` to acknowledge shown failed/dead runs under `state/run-watch/<host>/ack.json`.
- `tools/run_watcher.py` — Created pure lifecycle decision function `decide_lifecycle` (`decide`), `next_start_count`, `WatcherCycle`, `steward_open_file`, `record_give_up` (appending one line to `state/steward/<host>/open.md` on `give_up`), threshold helpers (`quiet_s`, `close_after_s`, `batch_s`), and pure launch argv builders `build_launch_argv` / `build_claude_argv`.
- `roles/run_watch.md` — Created read-only watcher role prompt (30 lines, ≤40 lines, English: single allowed tool `Bash(bash scripts/hub/org-python.sh tools/run_watch.py *)`, answers ≤3 lines, makes no decisions, takes no action).
- `.claude/skills/CTO_Procedure_RunWatch/SKILL.md` — Created fixed dispatch table skill (`CTO_Procedure_RunWatch`) matching the frontmatter and lint rules of `CTO_Procedure_*` skills.
- `tests/test_run_watcher.py` — Created fixture-only pytest suite covering all light states, sticky 🔴 and both clearing paths, all lifecycle transitions including `restart` once then `give_up` writing `open.md`, launch argv builder output, env overrides, winbox ASCII watch names, and role/skill contract checks.

## Rule-to-Test Mapping

| Requirement / Rule | Implementation | Test in `tests/test_run_watcher.py` |
|---|---|---|
| ⚪ when 0 active runs (including only `done` runs) | `run_watch.compute_light` | `test_light_white_when_zero_active_runs` |
| 🟢 when all active runs are `running` | `run_watch.compute_light` | `test_light_green_when_all_active_runs_are_running` |
| 🟡 when any active run is `quiet` (>15 min / `RUN_WATCH_QUIET_S`) | `run_watch.compute_light` | `test_light_yellow_when_any_active_run_is_quiet_over_15m` |
| 🔴 when any run is `failed` or `dead` | `run_watch.compute_light` | `test_light_red_when_any_run_failed_or_dead` |
| Sticky 🔴 persists until acknowledged by `status` (`state/run-watch/<host>/ack.json`) | `run_watch.compute_light`, `run_watch.acknowledge_runs`, `run_watch.main(["status", ...])` | `test_sticky_red_persists_until_cleared_and_clears_on_status_ack` |
| Sticky 🔴 clears when task is re-delegated (`status` or `spawned_at` changes) | `run_watch.compute_light`, `run_watch._run_sig` | `test_sticky_red_clears_when_task_is_redelegated` |
| `run_watch.py light [--json]` + `winbox` ASCII name via `session_names.watch_name` & `windows_safe` (`Runs: 2 ok\|quiet\|FAIL\|idle`) | `run_watch.format_watch_name`, `run_watch.main(["light", ...])` | `test_winbox_ascii_watch_name_and_cli_light` |
| Lifecycle `start` on first active run, `stop` 10 min (`RUN_WATCH_CLOSE_AFTER_S`) after last run ends | `run_watcher.decide_lifecycle` | `test_lifecycle_start_and_close_after_stop` |
| Lifecycle `restart` once on watcher death while active; second death -> `give_up` + 1 line in `state/steward/<host>/open.md`; never resumed until next run cycle | `run_watcher.decide_lifecycle`, `run_watcher.WatcherCycle`, `run_watcher.record_give_up` | `test_lifecycle_restart_once_then_give_up_writes_open_md_and_resets_next_cycle` |
| Pure launch argv builder (`runwatch-<host>`, `claude --model haiku --remote-control --strict-mcp-config --mcp-config ... --permission-mode dontAsk --allowedTools ... --append-system-prompt-file roles/run_watch.md -n <Watch name>`) | `run_watcher.build_launch_argv`, `run_watcher.build_claude_argv` | `test_launch_argv_builder_output` |
| Threshold env overrides (`RUN_WATCH_QUIET_S`, `RUN_WATCH_CLOSE_AFTER_S`, `RUN_WATCH_BATCH_S`) | `run_watcher.quiet_s`, `run_watcher.close_after_s`, `run_watcher.batch_s` | `test_threshold_env_overrides` |
| `roles/run_watch.md` (≤40 lines) & `.claude/skills/CTO_Procedure_RunWatch/SKILL.md` fixed dispatch table | `roles/run_watch.md`, `.claude/skills/CTO_Procedure_RunWatch/SKILL.md` | `test_role_and_skill_files_exist_and_match_contract` |

## Validation & What Could Not Be Run

Per the AGY headless remote worker contract ("For AGY, use file tools only; leave shell validation to the review process. If a check needs another command, write it in REPORT.md instead of running it"), no shell commands were executed during this run.

Commands for the reviewer to run from `/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-11bd703a`:
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_run_watcher.py tests/test_run_watch.py tests/test_run_liveness.py tests/test_session_names.py`
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python scripts/skill-lint.py .claude/skills/CTO_Procedure_RunWatch/SKILL.md`

## Next Steps (Out of Scope for Part B)

- Installing/enabling the watcher on hosts.
- Wiring the watchdog tick to call `tools/run_watcher.py` and execute the lifecycle action.
- Creating/starting the live `runwatch-<host>` tmux session.
- Switching/wiring the Mac terminal integration.
- Any host-level setup requiring root privileges.

## Blockers

- (none)

## Skill learning

- (none)
