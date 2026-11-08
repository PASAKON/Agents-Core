# PH shell relay guard

## Change

- `scripts/hook-ph-shell-relay.py` blocks a PH shell Stop when the current user turn has no Bash relay to `ph_brain.py turn`, `ph_brain.py delegate`, or `ask_run.py ask`. It reads at most the last 2 MiB of the transcript and honors `stop_hook_active`.
- `scripts/cxo-claude.sh` exports `ORG_PH_SHELL=1`, writes a `.shell` marker at launch, and starts a new conversation when a resume target does not match that marker. It saves the old UUID in `.uuid.preshell` and seeds the new conversation with a STATUS path and first brain call.
- RunWatch labels an open PH shell with no brain file and no `ph_state` row after ten minutes as `🔴 no brain`; its red count includes that shell.

## Stop hook entry for CTO

Add this object to the existing `hooks.Stop[0].hooks` array in `.claude/settings.json`:

```json
{
  "type": "command",
  "command": "python3 \"${CLAUDE_PROJECT_DIR:-$PWD}\"/scripts/hook-ph-shell-relay.py"
}
```

## Validation

- `bash -n scripts/cxo-claude.sh`: passed using Git Bash.
- `git diff --check`: passed.
- Requested pytest command was attempted but the `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` interpreter is unavailable in this Windows worktree. New hook, launcher, and watch tests are included for the Linux review run.

## Not checked / risk

- Pytest could not be run here; the CTO should run the requested suite on Contabo before enabling the hook.
- The handover STATUS path defaults to `docs/plans/<project>-STATUS.md`; set `ORG_PH_STATUS_PATH` when the project's actual STATUS file is elsewhere.
- The Stop hook is not active until the CTO adds the entry above. `.claude/settings.json` was left untouched as requested.
