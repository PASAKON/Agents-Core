# REPORT task-7c146bbc

Implemented fresh Codex feed preference and snapshot-driven quota reset events.
Worktree branch: `agent/codex-task-7c146bbc`. Main was not changed.

## Files changed

- `tools/quota.py`: prefer the Codex usage feed for observations under 30 minutes
  old, retain rollout fallback, preserve plan metadata, invoke reset detection
  before history append.
- `tools/quota_reset.py`: compare all four buckets, publish hub events and JSONL,
  dedupe by bucket/deadline with local and hub locking, drain waiting work once
  per detected batch, expose `last [--bucket X]`.
- `tests/test_quota_codex_feed.py`, `tests/test_quota_reset.py`: new feed, detection,
  dedupe, failure/retry, async drain, and snapshot integration coverage.
- `tests/test_quota_codex_limit.py`: explicitly select a missing feed for existing
  rollout fallback tests, preventing dependence on the host's live feed.
- `tests/test_quota_history.py`: include plan_type in the history schema assertion.
- `docs/design/runner-routing/quota-resets.md`: sources, rules, delivery and recovery.

## Validation performed

- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_quota*.py`
  — **109 passed in 3.96s**. No full suite run.
- Initial run exposed two tests depending on absence of the host feed and one
  history field assertion; these were corrected and the requested suite rerun.
- `git diff --check` — clean.
- Inspected the public Codex feed schema; no authentication file or secret read.
- Hub connection/log_event and queue drains mocked in new tests; no production
  hub events, live drain, email, or systemd changes performed.

## Blockers

- No implementation blocker. Commit and push are launcher-owned under the worker
  contract. One PR to main remains for the launcher/review handoff after push;
  no PR was opened or merged in this worktree session.

## Skill learning

- (none)

## Not checked / risk

- Real PostgreSQL advisory-lock/query behavior and cross-host concurrency were
  not exercised; DB boundaries were mocked as permitted by the task.
- Live timer deployment, SSH feed fetching, and actual queued-task spawning were
  not exercised. Detection latency remains bounded by the existing feed and
  snapshot schedules.
- budget_queue currently has no drain function; its normal polling continues.
- A crash or drain failure after event publication relies on normal queue polling
  for recovery. Hub commit before journal append is repaired on the next attempt
  without duplicating the hub event.
- The requested bucket+resets_at key coalesces multiple resets sharing a deadline,
  including unknown (null) deadlines. Unknown-to-known plan metadata does not
  count as an upgrade; both plan values must be present and different.
