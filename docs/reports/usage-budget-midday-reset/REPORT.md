# REPORT task-c1f85e47

Fixed CEO order O-20261106-2354-7c9f: daily budget calculations now start at the last weekly reset in the Thai-day observation window. A reset is a weekly remaining increase greater than 0.02 or a weekly reset timestamp moving later. Earlier observations are discarded before calculating start remaining and usage; days left still comes from the latest observation.

## Files changed
- `tools/usage_budget.py`: detect the last reset and trim the calculation window.
- `tests/test_usage_budget.py`: assert post-reset numeric totals; cover zero-midnight recovery for codex and agy-claude, zero-start usage without a reset, multiple resets, timestamp-only reset detection, and unusable previous reset timestamps.
- Both this report and `docs/reports/task-c1f85e47/REPORT.md` document the change.

## Validation
Ran the requested command without `-q`:

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_usage_budget.py tests/test_usage_budget_p4a.py tests/test_route_budget.py
64 passed in 4.21s
```

## Not checked / risk
- No live quota history replay, snapshot refresh, or delegate queue processing was performed. Deployment and operational recovery remain outside this worktree change.
- Reset detection follows the requested heuristic: increases of at most 0.02 do not reset accounting unless the reset timestamp moves later. Missing or malformed reset timestamps cannot establish a timestamp-based reset; quota increases still can.
- The full repository test suite was not run.

## Blockers
- None.

## Skill learning
- (none)
