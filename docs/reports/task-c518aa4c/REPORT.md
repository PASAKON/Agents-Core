# REPORT task-c518aa4c

Implemented leftover C-level scope cleanup and actionable restart notifications.

## Files changed
- `tools/restart_run.py`: after the live-pane guard, probe the exact Linux C-level scope and stop it before tmux creation. Stop failures retain recovery state and report the unit. Dry runs only probe and print planned mutations. Missing C-levels (excluding COO) receive a resume command card with the existing requester, amber risk, fixed production cwd, expected count, and a single-line reason limited to 90 characters. PH-only failures retain question cards.
- `tests/test_restart_run.py`: mock inactive scope probes, distinguish probes from mutations, and retain question-card coverage for PH-only failures.
- `tests/test_restart_resume_gaps.py`: cover active/inactive scopes, ordering, live-pane guards including dry run, dry-run probe behavior, stop failure and retained recovery state, retry skipping live rows, and C-level command cards including long multiline names.
- `docs/reports/task-c518aa4c/REPORT.md`: this report.

## Validation
Ran from the assigned worktree:

```text
.venv/bin/python -m pytest -q tests/test_restart_run.py tests/test_restart_resume_gaps.py tests/test_restart_plan.py
........................................................................ [ 66%]
.....................................                                    [100%]
```

Exit status 0; 109 tests passed. `git diff --check` passed.
The worktree initially had no `.venv`; an ignored symlink to the existing Core environment enabled the exact requested command. Tests ran in the worktree, with subprocess/tmux mocked for the new cases; no real sessions or scopes were changed.

## Limitations
- No live Contabo restart was attempted.
- Task branch `agent/codex-task-c518aa4c` began at `origin/main` (`890b021d`). Changes are left for the launcher to commit and push, per the worker contract.

## Blockers
- (none)

## Skill learning
- (none)
