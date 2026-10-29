# REPORT task-d9b7786e

## Result

Implemented SafeRestart support for the verified `cto-fresh` session and other roster C-level `*-fresh` sessions. PR #562's live leadership/no-charter and stale `saved` behavior is unchanged.

- PR number: unavailable; GitHub API connection is blocked in this environment. No PR was created or merged.
- Current HEAD/base SHA: `17936f869cd98f5212621bd4f65620b180f2cabb` (PR #562 merged).
- Task branch: `agent/codex-task-d9b7786e`.
- Implementation head SHA: pending the launcher's commit/push, as specified by the worker contract. Changes remain in the assigned worktree; `main` was not changed.

## Files changed

- `tools/live_sessions.py`: recognize roster C-level (never CEO) `<role>-fresh:` records only when `read_lock` securely reads the exact full session UUID from `<role>-fresh.uuid`. Carry the verified launcher ID in local registry rows. `_launcher_uuid` is unchanged.
- `tools/restart_plan.py`: preserve the launcher ID and prefer `(role, fresh)` for charter/status, falling back to the UUID-tail key when no fresh row exists.
- `tools/restart_run.py`: preserve launcher ID/full UUID in the resume manifest; use the real tmux name for save, close, wait, recreation, and leftover systemd scope lookup; query saved status by `fresh`.
- `scripts/cto-claude.sh`, `scripts/cxo-claude.sh`: for explicit resume with session ID `fresh`, retain the resolved conversation UUID in the lock and omit `--session-id`/`--fork-session`. Normal launchers keep their existing fork behavior.
- `tests/test_restart_plan.py`, `tests/test_restart_run.py`: exact reported UUID/tmux regression, charter/status precedence, mismatching and unsafe locks, worker/CEO/unlisted-role rejection, manifest round trip, actual close target, and execution of launcher UUID/CLI argument blocks.

## Resume choice

The manifest records `launcher_id=fresh` and UUID `d405e3e2-5e46-406d-b9ae-a6f2f69c4825`. Resume exports `CTO_SESSION_ID=fresh` and passes that full UUID to `--resume`. This avoids inventing a second lock identity and does not depend on a lock surviving shutdown. The current launcher otherwise creates a new UUID and adds `--fork-session`; the narrowly scoped launcher adjustment is necessary to reopen the same JSONL rather than merely fork its context. CXO uses the same treatment for consistency with the roster-wide identity rule.

## Validation

All commands ran in the assigned worktree, which includes `deploy/`, using `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`.

- Requested command: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_restart_run.py tests/test_restart_plan.py tests/test_whois.py tests/test_whois_probes.py tests/test_rename_service.py tests/test_c_level_roles.py` (final run also emitted JUnit XML): **597 passed, 68 failed, 2 skipped**. All 68 failures are in `test_rename_service.py`: 67 sandbox `PermissionError` failures and one `os.chown(..., 1001, -1)` failure with `EINVAL`. All new regressions and the restart, whois, whois-probe, and role tests pass.
- Additional `tests/test_launcher_resume_short_id.py tests/test_restart_resume_gaps.py`: 36 passed.
- `bash -n scripts/cto-claude.sh scripts/cxo-claude.sh`: passed.
- `git diff --check`: passed.
- Independent sandbox probe `socket.socketpair(); a.sendall(b"test")` fails with `PermissionError: [Errno 1] Operation not permitted`, matching rename-service test failures.

## Not checked / risk

- New identity input: a registry record with tmux `<listed-C-level>-fresh:...` and a canonical lowercase full UUID may now claim that C-level role, verified, only when the same role's `fresh.uuid` securely matches. CEO, workers named CTO, absent/mismatched/symlinked/writable/hard-linked locks do not qualify. This retains the existing trust in local launcher/registry writers; it is not stronger process authentication.
- `_launcher_uuid`, whois owner-lock checks, and rename-service authorization were not broadened. Local whois owner verification still requires its existing UUID-tail lock.
- No live CTO session was stopped, no production hub was queried, and no reboot or real Claude CLI resume was performed. The launcher tests execute relevant shell blocks with a stub CLI; an on-host smoke test remains necessary. The target is Contabo; macOS launcher behavior was not exercised.
- Resume manifests are trusted local operational input, as before. Their fresh identity fields are shape/role/UUID-tail validated; the old UUID lock is intentionally not required after shutdown.
- Full socket/ownership-dependent rename-service validation requires a less restricted test runner. The environment also rejects the test's ownership change with `EINVAL`.

## Blockers

- `gh api repos/PASAKON/Agents-Core --jq .full_name` fails with `error connecting to api.github.com`. `gh auth status` also reports the configured account token invalid; authentication could not be verified independently of network restrictions. No sign-in was attempted.
- The launcher must commit/push these changes, rerun the socket-dependent checks on a suitable runner, and open a PR against `PASAKON/Agents-Core:main`. Record its PR number and implementation head SHA here after publication. Do not merge as part of this task.

## Skill learning

- (none)
