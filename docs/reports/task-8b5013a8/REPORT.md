# REPORT task-8b5013a8

Implemented the additive Project Head resume path on agent/codex-task-8b5013a8,
whose starting HEAD equals local origin/main (690953236422d6fa4b0edf708c2297aa5bd9f671).

## Files changed

- tools/spawn_ph.py: new resume_command, resume_plan and resume functions immediately before main; minimal CLI argument and early dispatch changes. Reads and validates saved project/owner/lane, refuses active sessions and conflicting projects, preserves identity, and launches tmux without an initial prompt. Dry runs only read state.
- tests/test_spawn_ph_resume.py: 22 tests covering plans, read-only dry runs, missing/invalid records, conflicting holders, active sessions, shell quoting and export parity, MCP dismissal, failed launches, argument validation and unchanged project requirement.
- docs/reports/task-8b5013a8/REPORT.md: this report.

Neither shell launcher changed. AST comparison confirmed launch_command, _plan,
spawn, refusal, _claim_lock and four card functions remain unchanged.

## Validation

- Used /opt/MoonieXHQ/Agents/Core/.venv/bin/python as the interpreter; tests ran from this assigned worktree against its code and temporary fixture directories only. System python3 has no pytest; python is unavailable.
- Initial required test run: 114 passed, 1 failed due to the filesystem rejecting os.chown(..., 1001, -1) with EINVAL in the existing test_records_another_user_wrote_are_ignored test.
- After adding seven more resume cases: pytest tests/test_spawn_ph_resume.py tests/test_org_p2_launchers.py tests/test_ph_on_mac.py -k 'not test_records_another_user_wrote_are_ignored' -o addopts='' : 121 passed, 1 deselected. Existing tests were not edited.
- git diff --check passed.
- Gitleaks stdin --redact --no-banner scanned the diff including the new test and this report: no leaks found (exit 0).

## Launcher findings and limitations

- scripts/spawn-ph.sh already forwards all non-card arguments; no edit needed.
- scripts/cxo-claude.sh resolves --resume through resolve-resume-id.sh before writing a new UUID. Resolution accepts role project_head and reads its .uuid, falling back to the hub resume_uuid lookup.
- The exported CXO_SESSION_ID is retained. The launcher supplies a new Claude UUID with --session-id and adds --fork-session; the org sid, lane, project and owner stay the same.
- No --initial-prompt or positional user prompt is supplied. This establishes no injected opening turn, not zero startup network traffic: Claude's actual --resume --fork-session startup requests were not measured. No live Claude session was started.
- Existing launcher cleanup removes PH .project and .spawned_by records on a clean exit. Such sessions are refused as required; resume needs surviving saved records (for example after an unclean stop). Launcher behavior was not changed.

## Blockers

- gh pr diff 282 was attempted before inspecting/editing code and retried after tests; both failed connecting to api.github.com. PR #282's actual diff could not be reviewed. New functions were confined to the requested insertion point and shell/card implementations left intact.
- GitHub network access prevents opening a PR; no PR number is available. The remote worker contract assigns commit and push to the launcher, so changes are left in the assigned worktree for it. A fresh origin/main fetch was not possible; the existing task branch starts at local origin/main.
- One existing ownership test cannot complete because this environment rejects its chown operation; all other selected tests pass.

PR handoff title: SafeRestart P2a: spawn-ph --resume <sid>

PR handoff body:

owner OrgRestructure not live; CTO Main approved 16 Oct

Add a prompt-free resume path preserving a Project Head's saved sid, project,
lane and owner, with liveness/project collision checks and read-only JSON dry runs.
Protected spawn/card functions and shell launchers are unchanged.
Validation: 121 passed, 1 filesystem-dependent existing test deselected after its
chown failed with EINVAL. See this report for launcher findings and limitations.

## Skill learning

- (none)
