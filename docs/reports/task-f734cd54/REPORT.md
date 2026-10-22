# REPORT task-f734cd54

## Changes
- `tools/mesh_check.py`: fetch checking-host core once per matrix run through `kit_git`; compare every reported core commit locally against origin/main. Fail missing/unknown heads and failed fetches. Fail behind hosts only when the oldest missing committer timestamp exceeds 24 hours. Preserve remote facts for display.
- `tests/test_mesh_check_kit.py`: local Git probes for the stale-ref incident (66 old commits missing despite reported behind=0 and age=145.17), current head, three fresh commits, the 24-hour boundary, missing/unknown heads, and failed fetch. Matrix probes cover one fetch and failure propagation across local, SSH and mesh transports.
- `tests/test_mesh_check.py`: isolate the new fetch in legacy transport tests.
- `docs/ops/mesh-check.md`: document the checking-host core rule.

## Validation
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/pytest tests/test_mesh_check_kit.py tests/test_mesh_check.py -q`: 272 passed, 0 failed (exit 0; collection separately confirmed 272).
- `git diff --check`: passed.
- `git diff | gitleaks stdin --redact --no-banner`: no leaks found.
- Reviewed added diff lines: no IP addresses or hostname-to-IP mappings.
- Tests use local fixture repositories; no live peer validation performed.

## Blockers
- Bare `pytest` is not on PATH; used the existing repository virtualenv.
- Commit/push/PR blocked: `git add` failed creating the shared worktree `index.lock` with `Read-only file system`. Changes remain uncommitted on `agent/codex-task-f734cd54`. The launcher owns commit and push under the worker contract. No PR number is available; no merge performed.

## Skill learning
- (none)
