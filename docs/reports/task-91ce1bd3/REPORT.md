# REPORT task-91ce1bd3

Implemented CEO picks #5 and #25 on `agent/codex-task-91ce1bd3`.

## Files changed

- `runners/coo_mcp_server.py`: register `email_ceo` and `quota` for MCP, allowed-tools, and CLI. Email forces role coo and the environment session, requires nonempty CXO_SESSION_ID, and wraps refusals/hub errors. Quota reads the module-relative snapshot, returns only the requested bucket fields, names read/format errors, and flags snapshots older than two hours.
- `tools/quota.py`: chmod the completed temporary snapshot to 0644 before atomic replacement; history permissions unchanged.
- `tests/test_coo_mcp_server.py`: identity override, missing session, error handling, CLI, MCP registration/schema, quota filtering, age boundary, missing/malformed/unreadable snapshots.
- `tests/test_quota_snapshot.py`: verify public mode before atomic replacement and after replacing an existing 0600 file; isolate an existing test's usage-budget output in tmp_path.
- This report and `PR_BODY.md`: publication handoff.

## Validation

HEAD and origin/main both resolve to `4b6af0240fae4890e0b46076976afc05d1033b78`. `git merge-base --is-ancestor a60f1744 HEAD` returned 1: the flagged commit is not an ancestor. Default branch untouched.

Ran the requested command using the shared virtualenv on PATH:

```text
pytest -q tests/test_coo_mcp_server.py tests/test_quota_snapshot.py tests/test_email_ceo.py tests/test_coo_gate.py tests/test_spawn_coo.py
```

Exit 1: 137 collected, 126 passed, 10 failed, 1 xfailed (pytest.ini adds a second -q and suppresses the numerical summary). Output tail:

```text
FAILED tests/test_coo_gate.py::test_gate_answers_only_allowed_uids
FAILED tests/test_coo_gate.py::test_box_cannot_reach_a_dir_closed_to_others
FAILED tests/test_coo_gate.py::test_mcp_without_the_gate_says_so
FAILED tests/test_spawn_coo.py::test_launcher_runs_claude_unprivileged_with_the_channel_flag_and_a_clean_env
FAILED tests/test_spawn_coo.py::test_launcher_ignores_a_stale_coo_lock
FAILED tests/test_spawn_coo.py::test_launcher_keeps_the_session_users_home_and_warns_once_without_the_run_inbox_token
FAILED tests/test_spawn_coo.py::test_launcher_is_quiet_when_the_run_inbox_token_is_there
FAILED tests/test_spawn_coo.py::test_root_is_an_explicit_opt_in_and_still_gets_the_clean_env
FAILED tests/test_spawn_coo.py::test_org_mcp_server_starts_and_lists_its_tools_for_a_uid_that_can_write_the_shared_db
FAILED tests/test_spawn_coo.py::test_launcher_moves_an_unread_letter_to_the_new_box
```

These failures report sandbox restrictions: Unix socket send/connect EPERM (2), chown EINVAL for unmapped users/groups (2), and systemd bus EPERM (6). No production gate/launcher behavior was changed to accommodate the sandbox. Rerun these tests on a host allowing those operations.

After isolating the generated usage-budget file, reran the three focused files with `-o addopts=''` for an explicit summary:

```text
.........................                                                [100%]
25 passed in 0.73s
```

All new tests and existing email/snapshot tests pass. HTTP/hub calls are mocked. `git diff --check` passes.

## Surprises and limitations

- `session_id()` supports legacy COO_SESSION_ID, so email explicitly requires CXO_SESSION_ID first to meet the stricter contract.
- The first test run stalled in asyncio executor shutdown (confirmed by faulthandler). The MCP wrapper test now mocks asyncio.to_thread and checks forwarding without an executor; production uses the existing server's asyncio.to_thread pattern.
- An existing snapshot CLI test wrote `state/usage-budget/usage-budget.json`; its output is now isolated and the generated file was removed.
- No live email was sent or deployed snapshot modified. Existing snapshot mode changes on the next writer run.

## Blockers

- PR number and final head SHA: pending launcher publication. The Remote Worker Contract says the launcher commits and pushes after this turn. Current HEAD above is the base, not a change commit. Open a PR to PASAKON/Agents-Core main from this task branch after commit/push, using PR_BODY.md; do not merge.
- Full integration validation is limited by the sandbox restrictions listed above.

## Skill learning

- (none)
