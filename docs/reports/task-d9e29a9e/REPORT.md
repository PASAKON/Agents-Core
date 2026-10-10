# REPORT task-d9e29a9e

## Files changed

- `runners/watchdog.py`: add periodic mesh probes, per-host failure isolation, two-probe outage confirmation, recovery logging, atomic persistent state, scan summary and `--mesh-probe` acceptance CLI.
- `tests/test_watchdog_mesh_probe.py`: mocked key, clock, dispatch and alert tests for selection, intervals, classifications, transitions, restart/corrupt state, atomic writes, redaction, CLI and scan integration.
- `docs/ops/node-dispatch.md`: document Periodic host probe (#238), prerequisites, settings, classifications, alerts, state and CLI.
- `docs/reports/task-d9e29a9e/REPORT.md`: implementation and validation record.

Alert channel: GitHub issue via `tools.gh_issue.create_issue`, project `mooniex-agents`, labels `watchdog` and `agent`; this is the existing durable CTO/CEO-visible critical channel used by `_file_stalled_issue`. `_send_ping` addresses a task's worker and is unsuitable for an ownerless host outage. No new channel, Run Inbox card or email_ceo call.

State: `state/watchdog-mesh-probe.json`, atomic temporary-file + `os.replace`; stores last pass time, consecutive failures, outage start and whether the outage was reported. A failed alert attempt is isolated and retried on a later bad probe. Calls rely on mesh's existing 30-second probe timeout, with no probe retries.

## Tests

All commands ran from the assigned worktree. Broader runs exported
`ORG_MESH_PROBE=0` first so existing scan tests could not access the real dispatch
key or dial hosts. The new tests explicitly enable the pass with a temporary key
and mocked dispatch. No packages were installed.

New tests (initial run: **24 passed in 0.87s**; final run after explicit state
validation replaced production assertions: **24 passed in 0.94s**):

```bash
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_watchdog_mesh_probe.py -o addopts="" -p no:warnings
```

Initial combined watchdog/mesh run: **426 collected**, interrupted after it
stopped progressing in an existing async dispatch test; pytest printed no final
pass/fail totals (process exit 130).

```bash
export ORG_MESH_PROBE=0
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_watchdog_mesh_probe.py scripts/test_watchdog_remote_heartbeat.py scripts/test_watchdog_plist.py tests/test_mesh_check.py tests/test_mesh_followups.py tests/test_w23_mesh_dispatch.py tests/test_w25_spawn_c_level_mesh.py tests/test_w28_mesh_destination.py -o addopts="" -p no:warnings
```

Full suite: **8211 collected**, interrupted after progress stopped around 20%
in `tests/test_ask_run.py`; failures and setup errors had already appeared in
existing tests. Pytest printed no final pass/fail totals (process exit 130).
The command restores every safety exclusion from `pytest.ini` explicitly because
the required `-o addopts=""` clears those exclusions as well as `-q`.

```bash
export ORG_MESH_PROBE=0
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts="" -p no:warnings --ignore=scripts/test_auto_deploy.py --ignore=scripts/test_depends_on_enforcement.py --ignore=scripts/test_designer_spawn_guard.py --ignore=scripts/test_maintab.py --ignore=scripts/test_org_tools_registry.py --ignore=scripts/test_owner_cto_routing.py --ignore=scripts/test_spawn_tab_routing.py --ignore=scripts/test_surface_reaper.py --ignore=scripts/test_tab_title.py --ignore=scripts/test_tm_prompt_loop.py --ignore=scripts/test_trader_mindset_batch.py --ignore=scripts/test_watchdog_reap.py > /tmp/task-d9e29a9e-full-pytest.txt 2>&1
```

Async stall reproduction: **81 collected / 80 deselected / 1 selected**, timed
stack dump after 30 seconds, then interrupted (exit 130; no final totals). Stack:
`tests/test_w23_mesh_dispatch.py:319 -> _spawn:129 -> asyncio.run -> selectors.select`;
executor thread idle in `concurrent.futures.thread._worker`. This selected test
does not call the new probe pass.

```bash
export ORG_MESH_PROBE=0
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w23_mesh_dispatch.py -k test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh -o addopts="" -p no:warnings -o faulthandler_timeout=30 -vv
```

Separate C-level mesh suite: **63 passed in 3.49s**.

```bash
export ORG_MESH_PROBE=0
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w25_spawn_c_level_mesh.py -o addopts="" -p no:warnings
```

First full-suite failure reproduced alone: **1 failed, 4 passed in 0.56s**.
`scripts/test_dev_tab_color.py::test_zero_in_flight_does_no_api_work` fails in
`lib/db.py:445` with `RuntimeError: tests must not touch a real checkout's tasks.db
(ADR 0021)`. The safety guard prevented the access; no bypass was attempted.

```bash
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest scripts/test_dev_tab_color.py -o addopts="" -p no:warnings -x
```

Completed watchdog/mesh regression subset: **282 passed in 74.06s (0:01:14)**.

```bash
export ORG_MESH_PROBE=0
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_watchdog_mesh_probe.py scripts/test_watchdog_remote_heartbeat.py scripts/test_watchdog_plist.py tests/test_mesh_check.py tests/test_mesh_followups.py tests/test_w28_mesh_destination.py -o addopts="" -p no:warnings > /tmp/task-d9e29a9e-regression-pytest.txt 2>&1
```

Mesh dispatch with the five async remote-spawn cases excluded after the stall
reproduction: **76 passed, 5 deselected in 34.58s**. Together with the 282 and 63
above, **421 distinct targeted tests passed**, including all 24 new tests.

```bash
export ORG_MESH_PROBE=0
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w23_mesh_dispatch.py -k 'not test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh and not test_flag_on_unreachable_queues_the_row_and_returns and not test_flag_on_no_answer_after_the_far_side_moved_the_row_does_not_queue_it and not test_flag_on_a_refusal_fails_the_task_like_a_failed_launcher and not test_flag_on_a_refusal_after_the_far_side_moved_the_row_leaves_it' -o addopts="" -p no:warnings
```

`git diff --check` passed.

## Not verified

- Live Mac/winbox/Contabo SSH acceptance, forced-command key installation, far-host audit rows and GitHub alert delivery require the CTO's configured dispatcher and live services. No live probe or real alert was run.
- Existing excluded watchdog reap script is a standalone harness (pytest.ini excludes it); not run as a live script.
- No commit, push or merge performed: the launcher owns commit/push and the Contabo CTO owns review/merge.
- Atomic state replacement prevents partial JSON; an abrupt crash after issue creation but before state persistence can still duplicate an alert on restart. Multiple watchdog processes sharing this file are not coordinated.

## Blockers

- Implementation complete. A complete full-suite result is blocked by existing
  failures/setup errors and stalled async execution in this sandbox. CTO review
  should rerun the combined and full suites in the normal test environment.
- Fixing the existing failing tests or changing shared test fixtures would require
  paths outside this task's allow-list; none were changed.

## Skill learning

- (none)
