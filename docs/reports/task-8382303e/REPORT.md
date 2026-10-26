# REPORT task-8382303e

## Outcome

Restored the 12 first-pass files from ef650d79559decc1e36c55d57fb73973224dace9 and applied CTO iter-2 fixes 1–4.
Actual branch: agent/codex-task-8382303e.
HEAD remains 4b6af0240fae4890e0b46076976afc05d1033b78; changes are uncommitted.

1. Resume preserves the source UUID's last eight hex digits as the short ID but mints a new fork destination UUID. Tests check the destination differs, shares the suffix, appears in the lock file and --session-id, and retains the source in -r.
2. Gate reads only coo_respawn_events, a hub-owner security-barrier view limited to request/done events. Removed events SELECT from grants and the §6 allow-list; explicitly revoked the former column SELECT grant for upgrades. INSERT and the narrow taskless-request trigger remain.
3. Request lookup filters kind, payload by_session and role. Status accepts only the matching request_id. Regression tests insert interleaved requests and unrelated completion events.
4. Removed both _now stubs. Gate/dispatcher functions accept keyword-only now, supplied directly by rate-limit tests.

Testing also exposed first-pass calls to nonexistent live_sessions.ensure_schema and session_names.parse_name, plus treating parse_short's tuple as a dict. Fixed these to read the deployed table and use the existing parser. Test fixtures create their SQLite table and isolate launcher flags/virtual environment.

## Files changed

- deploy/coo-gate/README.md
- deploy/coo-gate/org_coo_role.sql
- lib/coo_policy.py
- runners/coo_dispatch.py
- runners/coo_gate.py
- runners/coo_mcp_server.py (only the first-pass appended tool)
- scripts/cxo-claude.sh
- scripts/resolve-resume-id.sh
- tests/test_coo_gate.py
- tests/test_coo_dispatch.py
- tests/test_cxo_claude_session_id.py
- tests/test_resolve_resume_id.py
- docs/reports/task-8382303e/REPORT.md

## Validation

Interpreter: /opt/MoonieXHQ/Agents/Core/.venv/bin/python (read-only shared environment; tests run in the assigned worktree).

Core command: python -m pytest tests/test_coo_gate.py tests/test_coo_dispatch.py tests/test_cxo_claude_session_id.py tests/test_resolve_resume_id.py -q -o addopts=''

Tail:

```
FAILED tests/test_coo_gate.py::test_gate_answers_only_allowed_uids
FAILED tests/test_coo_gate.py::test_box_cannot_reach_a_dir_closed_to_others
FAILED tests/test_coo_gate.py::test_mcp_without_the_gate_says_so
3 failed, 104 passed in 52.05s
```

These unchanged tests hit sandbox socket PermissionError, chmod OSError, and PermissionError instead of the expected missing-socket error, respectively.

Final focused regression run after explicit-time test cleanup:

```
56 passed, 51 deselected in 35.08s
```

Selection across the same four files: -k 'respawn or dispatch or adopts or rejects_non or resume_sets or resume_respects or resolver'.

Also attempted test_launcher_resume_short_id.py, test_spawn_coo.py,
test_org_p2_launchers.py, test_w03b_local_launcher.py and test_w06_launcher_report.py.
The verbose additional run recorded 119 PASSED, 8 FAILED and 1 XFAIL before
stalling at test_w03b_local_launcher.py::test_linux_self_host_codex_and_agy_run_the_launcher_with_local_bash[codex].
Interrupted it (exit 130); this broader suite is not a passing validation.
Seven failures were in existing spawn_coo launcher/environment tests and one was
test_records_another_user_wrote_are_ignored. These were not changed to mask the failures.

Ran test_w06_launcher_report.py separately to completion: 32 passed in 49.34s.

git diff --check and bash -n for both modified shell scripts passed.
No network, real hub, tmux session, or SQL deployment was used for the new regression tests. PostgreSQL security-barrier semantics and the §6 live proof require deployment validation; local SQL tests check the guard/grant text and SQLite checks the filtered view.

## Decisions

Resume selection remains the first pass: newest spawned_at for the role on Contabo, including legacy NULL/empty-host rows, breaking ties by session_id descending. The root resolver receives that session ID; no resolved UUID means a fresh launch. README documents this and the fork identity.

## Blockers

- The required first command, git cherry-pick ef650d79, failed because the worktree's external Git metadata is read-only (index.lock creation denied). Restored its file contents with apply_patch instead. A later git add failed identically; no commit or new head SHA can be created here. The launcher must commit/push the prepared files in its writable context.
- The supplied checkout is agent/codex-task-8382303e, not the brief's agent/agy-task-8382303e. No branch or default-branch changes were made.
- Core tests have the three sandbox-dependent failures listed above.

## Skill learning

- (none)
