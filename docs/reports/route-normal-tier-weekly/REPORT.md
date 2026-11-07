# REPORT task-c8a1ece9

Normal shell tasks no longer defer solely because Codex exceeds its daily target while its weekly projection holds through reset. `_tier_plans` reuses each plan's projection, falling back to headroom below -5 percentage points when reset coverage is unavailable. Missing data leaves the gate open. Low-tier daily gating is unchanged.

## Files changed

- `tools/route.py`
- `tests/test_route_budget.py`
- `tests/test_usage_budget_p4a.py`
- Both task and policy reports.

## Validation performed

`/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_route_budget.py tests/test_usage_budget.py tests/test_usage_budget_p4a.py`

75 passed in 4.14s; no `-q` flag. `git diff --check` passed. Tests cover the requested 1.7-point holding / 20-point failing cases, low-tier behavior, missing forecast/headroom, and the -5-point fallback boundary.

## Not checked / risk

No live dispatch or queue drain, quota API validation, or full repository test suite. The predicate recognizes existing forecast text; future wording changes require corresponding maintenance. A missing reset-aware projection uses daily headroom as the authorized proxy.

## Blockers

PR to `main` awaits the launcher-owned commit and push. Implementation and requested tests are complete. No mailbox was present.

## Skill learning

- (none)
