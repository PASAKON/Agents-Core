# REPORT task-52d634ef

## Changes

- `tools/ask_run.py`: optional `ask --job`, exact job matching for the same requester session, cancellation of matching pending cards, bounded Thai replacement notice, and stderr warnings for own pending questions created within 30 minutes when no job is supplied. Dry runs do not query or cancel cards. A missing live media submission result now fails instead of reporting a successful dry run.
- `runners/cto_mcp_server.py`, `runners/coo_mcp_server.py`, `lib/org_tools_registry.py`: expose and forward MCP `job`; groups reject a job rather than silently ignoring it.
- `tests/test_ask_run_jobs.py`: 13 socket-free cases covering replacement, isolation, trimming, failed cancellation/submission, warning success, CLI/MCP forwarding, dry run, validation, missing media result, and the exact real-process `ask --pick many --media <one file>` refusal.
- Existing ask-run test fixtures and request assertions now account for the pending-card lookup.

## Storage decision

This repo owns the requester, not the Console card database. The existing Console implementation filters unknown fields from requester JSON. The implementation therefore stores a visible, bounded `job: <key>` line in the existing persisted `why` column; no database migration or direct database access is required. Keys are 1–64 ASCII letters/digits plus dot, colon, underscore and hyphen (first character alphanumeric). The marker survives trimming. Replacement notices and the marker share the existing question-plus-why five-line budget, with each why line at most 90 characters. A replacement of multiple cards names the first cancelled id and the additional count.

## Validation

- Used `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` throughout.
- Ran the required `python -m pytest tests/test_ask_run*.py` command. It produced fixture errors because socket creation is denied in this sandbox (`PermissionError: [Errno 1] Operation not permitted` at `ThreadingHTTPServer(("127.0.0.1", 0), ...)`). Interrupted the run after repeated errors and no further progress. Full-suite pass is not established.
- A focused `tests/test_ask_run.py -x` run confirmed the socket restriction at the first fixture.
- `python -m pytest tests/test_ask_run_jobs.py`: **13 passed**.
- `python -m py_compile` on all four changed production Python files: passed.
- `git diff --check`: passed.
- No real PostgreSQL tests were added or run; no org database or live cards were accessed.

## Blockers

- The complete HTTP-based test suite must be rerun by the launcher/reviewer in an environment permitting loopback sockets. This task does not yet meet the full-suite-pass acceptance condition.
- Launcher owns commit and push under the remote-worker contract; changes are left in the assigned worktree for it. Use `git commit -F <file>` when committing.

## Not checked / risk

- Cancellation and creation are separate HTTP operations. Concurrent senders can race; a creation failure after successful cancellation leaves the old cards cancelled. Strict cross-host atomic enforcement requires a Console server transaction outside this assigned repository.
- Job storage is visible why text rather than a dedicated structured column. Manually writing the exact marker in an older card's why makes it match that job. This is restricted to the same requester session.
- The lookup requests the API's maximum 200 pending rows. Older rows beyond that window are not examined.
- No live hub, CMO `run_v2.sh` integration, or PostgreSQL validation was performed. The exact CLI media failure already returned exit 2 before this change; the new subprocess regression pins that behavior, but cannot prove a caller shell preserves its exit code.
- New job dry-run output includes the internal job key; replacement notices depend on live pending cards and are computed only during submission.

## Skill learning

- (none)
