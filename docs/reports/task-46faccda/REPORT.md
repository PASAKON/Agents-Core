# REPORT task-46faccda

## Changes

- `tools/spend_guard.py`: trust the legacy fal balance only when positive; otherwise try documented billing. Failed fallback errors identify both sources and explicitly say the balance is unknown. Missing or malformed credits also follow this failure path. `read_all` converts the reader's `ProviderError` into `ok: False` using its existing credential-redaction handling.
- `tests/test_spend_guard.py`: cover zero and negative legacy balances, documented balances of $8.97 and zero, HTTP 403, missing/malformed credits, positive legacy $5 behavior, CEO alert and test-alert wording, offline status, failed snapshots, and absence of pause actions in armed mode.
- `docs/ops/spend-guard.md`: document the 23 Oct evidence and the trust/fallback policy.

The existing failed-reading paths already skip spend calculations and cycle updates, store no balance or spend counter for the failed snapshot, report blind/cannot-read instead of $0, and do not request pauses. Regression tests verify these paths without changing them.

## Validation

- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_spend_guard.py`: **71 passed**.
- `git diff --check`: passed.
- All provider calls in validation used fake HTTP. No network calls, keys, or `.env` files were accessed.

## Limitations

Live fal connectivity was not tested. Historical snapshots were not rewritten; prior unobserved spend cannot be recovered by this fix.

## Blockers

- (none)

## Skill learning

- (none)
