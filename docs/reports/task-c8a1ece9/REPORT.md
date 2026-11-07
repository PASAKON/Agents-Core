# REPORT task-c8a1ece9

Normal-tier routing now considers weekly runway before closing the daily budget gate. A plan that holds past reset stays eligible; a plan reaching reserve before reset remains over budget. When the projection cannot establish reset coverage, headroom below -5 percentage points closes the gate. Missing headroom leaves it open. Low tier retains its strict daily rule.

## Files changed

- `tools/route.py`: update the normal-tier over-budget predicate using existing plan projections and headroom fallback.
- `tests/test_route_budget.py`: shell-task regressions for 1.7 points over with weekly runway, 20 points over with failing projection, holding-projection precedence, unchanged low tier, missing data, and the fallback boundary.
- `tests/test_usage_budget_p4a.py`: give synthetic over-budget snapshots explicit -20-point headroom so existing deferral tests exercise the new policy with sufficient data.
- `docs/reports/route-normal-tier-weekly/REPORT.md`: requested policy report.
- This report.

## Validation performed

Command: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_route_budget.py tests/test_usage_budget.py tests/test_usage_budget_p4a.py`

Result: 75 passed in 4.14s. Invoked without `-q` as requested. `git diff --check` passed.

## Not checked / risk

- No live dispatch, quota API, or queue drain was performed; tests use deterministic quota and budget inputs.
- Projection recognition uses the existing forecast strings (`holds past reset` and `before reset`). Changes to their wording must update this predicate; unrecognized projections use headroom.
- Full repository suite was not run.

## Blockers

- Code and requested validation are complete. PR to `main` remains pending the launcher's commit and push, which the worker contract assigns to the launcher. No default-branch changes were made.
- No `MAILBOX.md` was present during work.

## Skill learning

- (none)
