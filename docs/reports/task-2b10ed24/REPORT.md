# REPORT task-2b10ed24

Implemented the read-only SafeRestart planner on agent/codex-task-2b10ed24,
whose starting HEAD equals origin/main (690953236422d6fa4b0edf708c2297aa5bd9f671).
The default branch was not changed.

## Files changed

- tools/restart_plan.py: local-host registry enumeration using live_sessions readers,
  bounded reverse JSONL reading, context/turn measurements, SELECT-only hub inspection,
  policy/overrides, token-million estimates, worker/warning output and JSON/table CLI.
- tests/test_restart_plan.py: synthetic transcripts and mocked hub/registry tests.
- docs/reports/task-2b10ed24/REPORT.md: this report.

## Validation performed

- From the assigned worktree, using the existing shared interpreter only:
  `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_restart_plan.py -q -o addopts=''`
  completed with **23 passed**. No tests ran in the main checkout.
- `git diff --check` passed.
- Gitleaks scanned the new-file diff via `gitleaks stdin --redact --no-banner`:
  no leaks found (including this report).
- Direct CLI dry run completed and wrote output under state/restart (removed
  after validation to keep runtime data out of the public commit):

```text
SESSION   ROLE             C       ACTION                 REASON
WARNING: Hub unavailable; ownership, cards, paid generations and merges cannot be verified.
WARNING: No live registry sessions visible; this is not proof the host is safe to restart.
Output: state/restart/contabo-20261015T215541940365Z.json
```

## Limitations

- Run on the selected host; remote PID validation is deliberately refused.
- A missing transcript, missing activity/context measurement or unavailable hub
  produces incomplete evidence and a conservative wait recommendation.
- Optional cards/generation/merge tables are inspected when present. Runtime
  schemas could not be verified against the hub. Only recorded Codex/AGY worker
  PIDs can be identified; unregistered workers are not attributed to sessions.
- Malformed JSONL lines and individual lines over 8 MiB are skipped. The reader
  uses bounded memory even on very large transcript files.
- Costs treat C as tokens and convert it to millions before applying equations.

## Blockers

- The prescribed `bash scripts/hub/org-python.sh` dry run failed before reaching
  the planner because its environment wrapper could not resolve its service host.
  The direct run could not reach hub data or see any live session records. A
  verified real Contabo session plan remains to be run in the host environment.
- Commit/push are left to the launcher as directed by the final Remote Worker
  Contract. No PR has been opened and no PR number is available. Requested title:
  **SafeRestart P1: restart_plan.py read-only planner**, targeting main.

## Skill learning

- (none)
