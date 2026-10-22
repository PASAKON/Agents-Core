# REPORT task-8940920a

Implemented UsageBudget P1; changes are ready for launcher commit and review.

## Files changed

- `tools/quota.py`: preserve weekly_raw, append it to history, refresh daily budget after snapshots with isolated error handling.
- `tools/usage_budget.py`: pure Thai-day calculation, backwards chunked history reader, today text/JSON CLI, atomic write, fail-open router cache loader.
- `tools/route.py`: optional budget input to rank, soft over-target partition, budget loading through plan/pick_runner/main, pressure-rule integration.
- `config/plans.yaml`: explanatory comment only; order remains ceo.
- `docs/ops/agent-runners.md`: daily budget commands and routing documentation.
- `tests/test_usage_budget.py`, `tests/test_route_budget.py`: calculation, history, cache, routing, and pressure integration coverage.
- `tests/test_quota_history.py`, `tests/test_quota_snapshot.py`: new history field and snapshot budget refresh assertions.

## Validation

Command (repository virtualenv; system python is unavailable and system python3 lacks pytest):

```sh
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts='' -q tests/test_usage_budget.py tests/test_quota*.py tests/test_route*.py
```

Result: **208 passed in 4.74s**. `git diff --check` passed.

Live history was read without modifying the main checkout:

```sh
/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/usage_budget.py today --history /opt/MoonieXHQ/Agents/Core/state/reports/quota-history.jsonl
```

```text
agy        used 0.0% / target 30.7%  pace 12.7%  headroom +30.7%  under  (resets 24 Oct)
chatgpt    used 0.0% / target 14.3%  pace 5.9%  headroom +14.3%  under  (resets 28 Oct)
claude     used 1.0% / target 16.0%  pace 6.6%  headroom +15.0%  under  (resets 27 Oct)
agy-claude used 0.0% / target 12.5%  pace 5.2%  headroom +12.5%  under  (resets 29 Oct)
```

Existing bonus-adjusted history cannot recover past raw Codex usage; new snapshots will preserve it.
The tail reader stops once each configured bucket has a day-start predecessor. Sparse histories missing
a bucket may require scanning farther back; it streams bounded chunks rather than loading the whole file.

## Diff stat

Implementation and tests, including new files (excluding this report):

```text
config/plans.yaml             |   1 +
docs/ops/agent-runners.md      |  20 +
tests/test_quota_history.py   |   3 +-
tests/test_quota_snapshot.py  |   2 +
tests/test_route_budget.py    |  57 +
tests/test_usage_budget.py    |  88 +
tools/quota.py                |  11 +-
tools/route.py                |  32 +-
tools/usage_budget.py         | 172 +
9 files changed, 379 insertions(+), 7 deletions(-)
```

## Blockers

- Current branch: `agent/codex-task-8940920a`; unchanged HEAD: `890b021d8fb867d278da97137c90755c9a59f15a`.
- Requested `git fetch origin && git switch -c ph/usagebudget-p1 origin/main` failed because the shared Git metadata is read-only. No branch switch or commit occurred; origin/main could not be refreshed.
- Per worker contract, the launcher owns commit/push. Please transfer the reviewed changes onto `ph/usagebudget-p1` from refreshed `origin/main`, commit, push, and open the PR against main titled `UsageBudget P1: daily targets, usage_budget today, router order budget`. Do not merge.
- No PR was opened because no branch could be committed/pushed. No default-branch, Rules, role-file, or systemd changes were made.

## Skill learning

- (none)
