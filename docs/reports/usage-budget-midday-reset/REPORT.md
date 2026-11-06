# REPORT task-c1f85e47

## Files changed
- `tools/usage_budget.py`: retain readings from the last weekly reset in the daily window. A reset is a remaining-quota rise greater than 0.02 or a reset timestamp moving later by at least one hour. Timestamp detection skips missing or invalid values; daily usage counts only subsequent drops. Days left still comes from the latest reading.
- `tests/test_usage_budget.py`: updated midday reset expectations and added coverage for an empty midnight followed by a reset, no-reset usage with a zero baseline, Claude timestamp jitter, the one-hour boundary, missing timestamps on either side, and multiple resets.
- `docs/reports/usage-budget-midday-reset/REPORT.md`: sole task report, per superseding CTO instructions. The duplicate `docs/reports/task-c1f85e47/REPORT.md` was absent from this worktree and was not created.

## Validation performed
- Ran `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_usage_budget.py tests/test_usage_budget_p4a.py tests/test_route_budget.py` without `-q`: **66 passed in 4.60s**.
- Claude-style timestamps varying around a fixed reset by ±0.02 seconds preserve the sum of drops (0.5) and produce state `over` above target.

## Not checked / risk
- No live quota polling, deployment, or production queue replay was performed.
- Reset detection remains heuristic: quota rises greater than 0.02 count as resets; timestamp shifts below one hour do not independently count.

## Blockers
- None.

## Skill learning
- (none)
