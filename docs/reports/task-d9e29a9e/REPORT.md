# REPORT task-d9e29a9e

## Files changed

- `runners/watchdog.py`: restore round-one periodic mesh probing, persistent outage state, scan summary and acceptance CLI; add `_public_detail` to hide SSH identities, IPv4/IPv6 addresses and tailnet names in public issue titles/bodies only. Local credential-redacted diagnostics remain unchanged.
- `tests/test_watchdog_mesh_probe.py`: restore 24 round-one cases and add seven privacy regressions covering SSH identity, IPv4, plain/bracketed/mapped IPv6, tailnet names, host labels and preservation of local diagnostics.
- `docs/ops/node-dispatch.md`: restore periodic-probe documentation and explain public-only address sanitization.
- `docs/reports/task-d9e29a9e/REPORT.md`: replace the round-one report with this round-two validation record.

Restoration: the supplied `origin/agent/codex-task-task-d9e29a9e` ref was absent. Restored all four files from the available `origin/agent/codex-task-d9e29a9e` ref instead. No Git metadata was changed.

Alert channel: existing GitHub issue channel via `tools.gh_issue.create_issue`, project `mooniex-agents`, labels `watchdog` and `agent`, as used by `_file_stalled_issue`; it provides durable CTO/CEO visibility for ownerless host outages. `_send_ping` targets a task's worker. Public issue text now removes network identity details after the existing credential redaction.

## Tests

Commands ran from the assigned worktree, with mocked dispatch and temporary keys for probe tests. Broader tests disable the real probe pass. No live probes, alerts, package installation or network commands were performed.

New test file: **31 passed in 0.81s**.

```bash
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_watchdog_mesh_probe.py -o addopts="" -p no:warnings
```

Watchdog/mesh regression: **428 passed, 5 deselected in 87.01s (0:01:27)**. These include all 31 probe tests (428 distinct passing tests overall). The same five async remote-spawn cases excluded in round one remain excluded because that run reproduced a stall inside `asyncio.run` outside the probe pass.

```bash
export ORG_MESH_PROBE=0
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_watchdog_mesh_probe.py scripts/test_watchdog_remote_heartbeat.py scripts/test_watchdog_plist.py tests/test_mesh_check.py tests/test_mesh_followups.py tests/test_w28_mesh_destination.py tests/test_w25_spawn_c_level_mesh.py tests/test_w23_mesh_dispatch.py -k 'not test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh and not test_flag_on_unreachable_queues_the_row_and_returns and not test_flag_on_no_answer_after_the_far_side_moved_the_row_does_not_queue_it and not test_flag_on_a_refusal_fails_the_task_like_a_failed_launcher and not test_flag_on_a_refusal_after_the_far_side_moved_the_row_leaves_it' -o addopts="" -p no:warnings > /tmp/task-d9e29a9e-round2-regression.txt 2>&1
```

`git diff --check` passed.

## Not verified

- Live Mac/winbox/Contabo SSH acceptance, forced-command key installation, far-host audit rows and GitHub delivery require the CTO's configured dispatcher and live services.
- Full suite was not rerun for this round's public-text-only change. Round one collected 8211 tests but stalled around 20% with existing failures/setup errors and no final totals; its isolated first failure was the ADR 0021 real-checkout database guard. Five existing async mesh dispatch tests remain unverified here.
- The standalone watchdog reap harness remains excluded per the repository's test configuration.
- Atomic state replacement prevents partial JSON, but a crash between issue creation and state persistence can duplicate an alert; multiple watchdog processes are not coordinated.
- No commit, push or merge: launcher owns commit/push; Contabo CTO owns review/merge.

## Blockers

- No implementation blocker. Complete suite validation still needs the normal test environment for the pre-existing failures and async stalls; fixes outside the allowed paths were not attempted.

## Skill learning

- (none)
