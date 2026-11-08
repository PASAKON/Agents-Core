# REPORT task-95553a00

Implemented persistent Codex PH planning turns, automatic fallback after the AGY chain reports quota exhaustion/429, live owner resolution, and case-insensitive launcher STATUS lookup.

## Files changed
- tools/ph_brain.py: Codex adapter, JSON reply extraction, separate codex_session_id persistence, explicit --brain codex, quota-only automatic fallback with to_model: codex, configured Sol/xhigh planning choice, router forecast reserve check including estimated size-S cost, read-only execution.
- tools/send_to_cto.py: retain live recorded owners; otherwise try role-active then live role-prefixed tmux names; report when no live owner exists while preserving queued mail.
- scripts/cxo-claude.sh: find an existing STATUS filename without case sensitivity, preserving explicit path overrides.
- tests/test_ph_brain.py, tests/test_send_to_cto.py, tests/test_cxo_claude_session_id.py: fake provider binaries, first/resumed turns, quota fallback, reserve refusal, owner resolution and missing-live diagnostic, launcher case regression.
- docs/reports/ph-brain-codex/REPORT.md: feature validation and risks.

## Validation performed
- Requested plain command: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ph_brain*.py tests/test_send_to_cto.py tests/test_cxo_claude_session_id.py tests/test_restart_run.py` — 285 passed in 57.89s.
- After adding the live-owner preservation assertion and improving failure diagnostics: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ph_brain.py tests/test_send_to_cto.py` — 21 passed in 2.63s.
- `bash -n scripts/cxo-claude.sh` and `git diff --check` passed.
- No real Codex or AGY invocation; provider execution tests use local fake executables.

## Not checked / risk
- Live CLI/account compatibility was not exercised, as requested. Codex JSON thread.started and item.completed events are the adapter contract.
- A provider switch carries the stored previous summary and incoming message, not the full AGY transcript. Each provider retains its own persistent session afterward.
- Missing quota snapshot data remains permissive, consistent with router unknown-quota behavior. This change enforces available reserve data; it does not refresh the quota collector.
- A default AGY turn retries the AGY chain before falling back again. Explicit --brain codex avoids those retries during the outage.
- If multiple same-role tmux sessions exist without a live active pointer, the first sorted live name is selected. Remote-host session discovery is outside this change.

## Blockers
- Commit blocked by the managed filesystem: both `git add` and `git commit` failed with `Unable to create '/opt/MoonieXHQ/Agents/Core/.git/worktrees/mooniex-agents__developer__task-95553a00/index.lock': Read-only file system`. The shared Git metadata is outside the writable worktree. No commit was created; the launcher must stage and commit the saved changes with its permissions.

## Skill learning
- Read `.claude/skills/CTO_Knowledge_Codex/SKILL.md`: Codex uses the OpenAI subscription bucket and may hit nested-sandbox limitations; live execution remains unverified. Repository config supplies Sol/xhigh for planning and Astra/xhigh for complex work.
