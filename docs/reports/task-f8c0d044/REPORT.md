# REPORT task-f8c0d044

## Changes

- `tools/owner_relay.py`: hardening of lock, parked, and PH metadata checks through one shared helper using no-follow directory-relative file metadata, regular-file type, ownership, write-mode, and link-count checks.
- `tools/owner_relay.py`: state hardening raises `StateUnusable` for existing unreadable or invalid state; repeated dictionary trimming bounds saved state by `STATE_READ_MAX`, or raises without writing. Identifier hardening filters running, event-row, and queue inputs and guards box, role, and session entry points before filesystem access.
- `tools/escalation_watch.py`: shares the file-trust helper, validates box names, and returns immediately from both relay and re-wake entry points in off mode.
- `tests/test_owner_relay.py` and `tests/test_escalation_watch_w2.py`: hardening regression coverage for writable and multiply linked lock metadata, directory links, invalid state, oversized dictionaries, invalid identifiers, and off-mode state preservation. Updated the existing state-link expectation for fail-closed loading. The ownership test now supplies file metadata directly instead of requiring privileged ownership changes.

## Validation

- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_owner_relay.py tests/test_escalation_watch*.py`: **130 passed**.
- `git diff --check`: passed.
- Initial validation identified the existing ownership test's unsupported `chown` operation in this sandbox; the revised test checks the same ownership condition without changing filesystem ownership.

## Not checked / risk

- No live deployment, production state changes, or live letter/wake checks performed.
- The separate low-priority directory-relative atomic-write hardening remains outside this patch; `_write_atomic` retains its existing implementation.
- Size-driven trimming can remove historical wake counts and deduplication entries, as required by the bounded-state policy. State that cannot fit after dictionary trimming raises `StateUnusable`.
- Ownership rejection is checked with supplied metadata; actual cross-user ownership changes were unavailable in this sandbox.

## Blockers

- None for the three requested hardening changes.

## Skill learning

- (none)
