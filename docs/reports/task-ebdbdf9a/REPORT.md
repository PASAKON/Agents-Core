# REPORT task-ebdbdf9a

## Files changed

- `CLAUDE.md` — replaced the winbox 4 GB live EA RAM reserve with the CEO's 90% RAM, CPU and disk start condition.
- `config/hosts.yaml` — documented that the 4 GB floor was replaced on 2026-11-11 by the 90% fill limit.
- `roles/cto-windows.md` — replaced the 4 GB free guidance with the 90% start condition and kept the one-heavy-thing rule.

## Validation performed

- Searched `CLAUDE.md`, `roles/`, `.claude/skills/*/SKILL.md`, and `docs/design/kit-hub.md` for winbox/live-EA reserve wording and 4 GB references related to it.
- Confirmed the three former reserve references are the only matching policy references in the requested paths; other 4 GB mentions are unrelated (for example disk or swap details).
- Reviewed the edited lines and `git status --short`.
- No tests run; this task changes text only.

## Not checked / risk

- Did not search outside the paths named in the task for additional winbox reserve wording.
- The 90% work-start condition is documented here; runtime behavior is governed by existing host-fill configuration and code, which this task did not change.

## Blockers

- None.

## Skill learning

- (none)
