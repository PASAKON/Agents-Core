# REPORT task-359e1c0a

Project SafeRestart (PH#47c4051c), PASAKON/Agents-Core.

- Branch: `agent/codex-task-359e1c0a`.
- PR number: unavailable; PR creation is blocked (see Blockers). Do not merge.
- Current HEAD/base SHA: `bdb8e2b2b0b4798fc1be73d2ef89380f822fc384`. Changes are uncommitted for the launcher; the final pushed head SHA must be recorded after its commit.

## Changes

- `tools/restart_plan.py`: mark live registry rows explicitly; resume live C-level/Project Head sessions lazily when they lack a charter and tasks. Preserve override, closed, incomplete-evidence, working-turn and CEO-card gates. Honor hub `parked`/`saved` and `.project.parked`/`.spawned_by.parked` locks.
- `tools/restart_run.py`: an empty manifest can select a C-level requester from the supplied or latest saved host plan. Skip notification when the environment/file has no Run Inbox token, printing `notify skipped: no Run Inbox token on <host>` and preserving report exit 0/1. Configured-token notification failures still exit 2.
- `tests/test_restart_plan.py`, `tests/test_restart_run.py`: cover the three reported winbox sessions entering the lazy manifest, all configured C-level roles, explicit parked hub/lock state, saved-plan requester selection, token absence and token files. Existing park and notification failure tests remain passing.
- `windows/org-resume-logon.ps1`: clarify the logged report exit meaning.
- `scripts/winbox-restart.sh`: header requires the plain one-line card command `bash scripts/winbox-restart.sh --sha <sha>` with cwd in its own field, because a prefix makes the card appear busy.

The header edit changes the script's SHA-256. New `scripts/winbox-restart.sh` SHA-256:

`94c64accb74fd360c5afa5c9b0cbfd956e968f209bbd687bbba8e80f5dbcc0f5`

## Validation

Run only in the assigned worktree, which includes `deploy/`:

- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_restart_run.py tests/test_restart_plan.py` — passed, exit 0.
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_restart_run.py -k notification_token_file` — three subsequently added token-file cases passed, exit 0.
- `git diff --check` — passed.
- `sha256sum scripts/winbox-restart.sh` — digest above.

## Not checked / risk

- This changes Contabo plans too: a live C-level/PH without a charter will now reopen instead of park, subject to existing safety gates and service-managed exclusions.
- No live reboot, Windows logon task, desktop typing, Contabo session restart, or Run Inbox submission was performed. Session/notification behavior was tested with isolated mocks.
- PH resume still requires existing owner/project recovery to succeed; this patch preserves those checks. Unknown evidence still waits rather than silently reopening.
- When no manifest owner or saved-plan C-level exists, the legacy configured service requester fallback remains.

## Blockers

- GitHub API is unreachable: `gh pr list --head agent/codex-task-359e1c0a --json number,url,headRefOid` returned `error connecting to api.github.com`. No PR was opened or merged.
- The worker contract assigns commit/push to the launcher after this turn. Launcher/follow-up must commit and push, open the requested PR against `main`, and fill in its number and final head SHA here. The current HEAD above is the base, not a claim that the changes have been committed.

## Skill learning

- (none)
