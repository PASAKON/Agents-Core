# REPORT task-950153b4

## Changes

- `tools/ph_brain.py`: defensive fallback metadata read and complete metadata on every returned turn result, including timeouts.
- `tests/test_ph_brain.py`: mocked CLI missing-metadata regression and first/retried timeout contract checks; existing fallback readers use `.get`.
- `roles/ph_shell.md`: mandatory shell-owned blocker letter, concrete CLI, optional GitHub issue, and explicit rule 4 exception.
- `docs/reports/ph-brain-fallback-keyerror/REPORT.md`: detailed diagnosis, red/green evidence, and limitations.
- `docs/reports/task-950153b4/PR_BODY.md`: ready PR description.

## Validation performed

`/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ph_brain.py`

Before production fix: 3 failed, 8 passed. After fix: 11 passed. AGY was mocked; no quota was spent. `git diff --check` passed.

## Not checked / risk

The current success producer already includes the field, and current timeout CLI handling skips the unsafe reader. The exact KeyError is reproduced by deliberately omitting metadata at the result boundary, while real timeout results independently demonstrate the incomplete contract. Live deployed source and PH state were not checked; model oscillation is not diagnosed or changed. No live mailbox, issue, delegation, or takeover calls were made.

## Blockers

PR publication is pending launcher commit/push, as required by the Remote Worker Contract. Changes are ready on `agent/codex-task-950153b4`; main was not changed. After publication, open the requested PR using:

```bash
gh pr create --repo PASAKON/Agents-Core --base main --head agent/codex-task-950153b4 --title "Fix PH brain fallback metadata handling and outage escalation" --body-file docs/reports/task-950153b4/PR_BODY.md
```

## Skill learning

- (none)
