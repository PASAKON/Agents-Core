# REPORT task-7d544700

## Changes

Added run-level `--aspect` (`9:16` default, `16:9` optional) for FilmFormula.

- `tools/flow_shoot.py`: run/pull parsers; chosen-aspect toggle and read-back under `aspect`; aspect-aware download dimensions; chosen-size 360p log.
- `tools/flow_shoot_card.py`: validated aspect flag forwarded exactly once in inner argv.
- `tests/test_flow_shoot.py`: parser defaults/rejections, fake settings selection/read-back, both orientation size tables, pre-Submit refusal, fake run/pull verification and no extra Submit after mismatch; existing stubs updated.
- `tests/test_flow_shoot_card.py`: default/explicit aspect forwarding, invalid values and aliases rejected; exact argv updated.
- `docs/reports/task-7d544700/REPORT.md`: validation and PR handoff.

Cap logic, credit estimates, ledger behavior, bundle/hash/lock behavior, and `config/spend-tools.txt` are unchanged.

## Validation

Base: local `origin/main` at `d116d13e40d76cbf9f7b29e9077558ad92394839`, which contains `5dde95fd` (verified with `git merge-base --is-ancestor`). Working branch: `agent/codex-task-7d544700`. No default-branch changes.

Command (no additional `-q`):

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_flow_shoot.py tests/test_flow_shoot_card.py
214 passed in 18.76s
```

Regression: `tests/test_flow_shoot.py::test_run_accepts_landscape_aspect`.

- Base result: `1 failed in 0.59s` (`unrecognized arguments: --aspect 16:9`).
- Branch result: `1 passed in 0.58s`.

The base check loaded `git show origin/main:tools/flow_shoot.py` into the imported `tools.flow_shoot` module and ran the same new test with `pytest.main`. This tests the actual base implementation without altering the worktree or default branch. The branch check used the normal `python -m pytest` invocation for that test.

`git diff --check` passed. Only the four requested code/test files and this report were changed. New tests use fake browser/media probes; existing local media tests also passed. No live Flow, winbox, SSH, or network calls were made.

## Not checked / risk

- The `16:9` toggle text was not checked on live Flow.
- The `16:9` output sizes (640x360, 1280x720, 1920x1080) were not checked on live Flow; tests use the brief's expected sizes.
- Square output remains unsupported. The collapsed settings read-back retains the existing body-text fallback behavior.

## Blockers

- Git metadata is read-only: `git add -N docs/reports/task-7d544700/REPORT.md` failed creating `index.lock`. The report remains untracked, so `git diff --stat origin/main` currently lists the four code/test files; the launcher must add the report to include the fifth file in that diff.
- PR creation remains for the launcher/operator: the worker contract reserves commits and pushes for the launcher, and this task prohibits network calls. Changes are ready for commit/push and a PR to `main`; do not merge. No PR was opened by this worker.

## Skill learning

- (none)

## PR handoff

Title: Add run-level Flow aspect selection with portrait default

Use the following body when opening the PR to `main`:

```markdown
FilmFormula needs landscape Flow output. Add `--aspect 16:9` to run, pull, and the card wrapper while preserving `9:16` as the default. Settings read-back still blocks Submit on mismatch; downloaded dimensions follow the selected aspect. Size failures retain the existing failed-file behavior without another Submit.

Files changed:
- tools/flow_shoot.py
- tools/flow_shoot_card.py
- tests/test_flow_shoot.py
- tests/test_flow_shoot_card.py
- docs/reports/task-7d544700/REPORT.md

Validation: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_flow_shoot.py tests/test_flow_shoot_card.py`
Result: `214 passed in 18.76s`. `git diff --check` passed.

New regression test: `test_run_accepts_landscape_aspect`.
Against origin/main d116d13e: `1 failed in 0.59s` (unrecognized --aspect).
On this branch: `1 passed in 0.58s`.

Cap logic, credit estimates, ledger behavior, bundle/hash checks, lock, and spend-tools configuration are unchanged.

## Not checked / risk
- The 16:9 toggle text was not checked on live Flow.
- The 16:9 output sizes were not checked on live Flow; fake tests validate the specified sizes.
- No live Flow, winbox, SSH, or network calls were made. Square output remains unsupported.

Do not merge as part of this task.
```
