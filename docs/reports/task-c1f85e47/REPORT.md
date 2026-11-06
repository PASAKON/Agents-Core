# REPORT task-c1f85e47

Completed the midday weekly-reset budget fix for CEO order O-20261106-2354-7c9f.

## Files changed
- `tools/usage_budget.py`: trim observations before the last weekly reset, using a quota increase greater than 0.02 or a later reset timestamp. Compute start remaining and usage from the trimmed records; preserve days-left calculation from the latest row.
- `tests/test_usage_budget.py`: updated post-reset numeric assertions and added regression coverage for both affected providers, zero-start usage without reset, last-reset selection, timestamp-only detection, and invalid or missing previous reset timestamps.
- `docs/reports/usage-budget-midday-reset/REPORT.md`: detailed requested bug report.
- `docs/reports/task-c1f85e47/REPORT.md`: task completion report.

## Validation
Executed `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_usage_budget.py tests/test_usage_budget_p4a.py tests/test_route_budget.py` without `-q`: **64 passed in 4.21s**.

## Not checked / risk
- Full repository suite, live quota history, snapshot refresh, and delegate queue recovery were not checked.
- Reset detection uses the requested heuristic; malformed or missing timestamps cannot establish a timestamp-based reset.

## Blockers
- None.

## Skill learning
- (none)
