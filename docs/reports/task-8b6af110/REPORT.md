# REPORT task-8b6af110

APPROVE — PR #558, head `5ccb4039dbc821f460d128c74c3e3648e4d4679f`.

## Review reasons

- `tools/restart_run.py:191-193`: retains the name-derived key and adds the UUID-tail key using the same role. This matches the planner's fallback in `tools/restart_plan.py:213` and `identity()`'s eight-hex requirement. No new registry rows are admitted: dead-process filtering in `tools/live_sessions.py:504` and the process-start mismatch rejection at `tools/restart_run.py:187` run before either key is inserted.
- `tools/restart_run.py:281-282,726-729`: real and dry-run prep now recognize short-named PH sessions. The no-tab fallback still requires an unambiguous missing-tab result and either park or a resumable entry; the desktop/lease checks remain intact.
- `tools/restart_run.py:599`: gone() now waits while the matching UUID-tail session remains alive and reports live_until_reboot after the bounded wait. It does not kill the process. Prep intentionally ignores its false result on Windows, where reboot ends the process.
- `tools/restart_run.py:838,866,890`: resume's initial already-live check and post-launch registration wait use the same identity and now recognize the session correctly. Non-Windows behavior is unchanged.
- `tests/test_restart_run.py:789-798`: fixture accurately represents the production parser output for the mismatched PH name and UUID. It asserts the added key and identity membership. The test mocks the registry rather than exercising parsing, and uses manifest-style `sid` rather than plan-style `session_id`; both are accepted by identity(). Supplementary review checks exercised the real parser and plan-style identity.

## Validation performed

- Reviewed the complete two-file commit diff and all win_live() callers; `git diff 5ccb4039^ 5ccb4039 --check` passed.
- Ran `python -m pytest -q tests/test_restart_run.py` against an exact `git archive 5ccb4039` snapshot inside the assigned worktree: passed, exit 0, all tests reached 100%.
- Used the existing repository virtualenv by prepending `/opt/MoonieXHQ/Agents/Core/.venv/bin` to PATH because bare `python` was unavailable.
- Supplementary in-memory checks, with a temporary registry JSON file: real read_registry() produced `(project_head, f35)` and the full UUID; win_live() produced both expected keys; plan-style identity matched; dead PID and mismatched procStart produced an empty set. OS liveness APIs were mocked.

## Not checked / risk

- No live Windows restart, Terminal typing, lease service, reboot, or logon-resume integration was exercised.
- `tools/restart_run.py:193`: identity remains role plus only eight UUID hex digits. A different live session with the same role and UUID tail can satisfy the lookup, incorrectly skip resume or satisfy the launch wait, and keep gone() waiting until timeout. The extra alias exposes this existing short-identity limitation to mismatched-name sessions; it does not provide full-UUID uniqueness. A different role or different tail does not match through the new alias. Existing name-key aliases are retained too.
- `tools/restart_run.py:185-190`: absent/unreadable/malformed procStart or an unavailable actual start time still permits a live reused PID to count. This existing fail-open behavior is not fixed here; a new alias can make such a row match a plan. No claim of absolute foreign-process exclusion is made.
- UUID validation is permissive (hex and hyphens, not canonical UUID syntax). Normal registry UUIDs work; aliases containing hyphens cannot match identity()'s valid eight-hex IDs. Registry role/name trust and races between liveness observation and action remain unchanged.

## Files changed

- Added only `docs/reports/task-8b6af110/REPORT.md`. No source or test changes. Temporary review snapshot removed after validation.

## Blockers

- No remaining review blocker. Checkout of PR head was blocked by read-only Git metadata outside the assigned worktree. Reviewed and tested an exact archive inside the assigned worktree instead; original HEAD and branch were left unchanged.
- MAILBOX.md was absent when checked.

## Skill learning

- (none)
