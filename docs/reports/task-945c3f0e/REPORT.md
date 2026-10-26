# REPORT task-945c3f0e

To: CTO Main. Implemented the 26 October C-level persona-name migration in the assigned worktree. No live session was renamed, no live sweep was run, and no commit or deployment was made.

## Changes

- `policies/agents.yaml`, `lib/config.py`: configured persona emojis beside the three persona names; added `persona_emoji_for`.
- `lib/session_names.py`: canonical builder, old/new readers, role/persona identity matching, topic/state-preserving migration, and the 26 October exception to the old keep-every-part rule. CFO/CGO remain bare when they have no persona.
- `tools/rename_service.py`: builds the canonical name and plans old-to-new C-level migration. Only the configured persona emoji can carry a joiner through the typing guard. PH/worker behavior is unchanged.
- `tools/live_sessions.py`: both display generations and machine-prefixed forms parse; cleaning preserves the joiner within a C-level persona while filtering format characters elsewhere.
- `tools/send_to_cxo.py`, `tools/whois.py`: old/new addresses resolve by role plus persona; whois preserves ambiguity handling and transport-based authentication.
- `scripts/cxo-claude.sh`, `scripts/cto-claude.sh`: use the shared builder for fresh names and the COO Remote Control label. `scripts/spawn-cxo.sh` documents its delegation to that launcher; `scripts/session-rename.sh` documents the new service-built shape.
- `roles/coo.md`, `roles/cto.md`, `roles/cmo.md`, `.claude/skills/session-open/SKILL.md`: updated canonical name examples; corrected SomPong to สมพงษ์ and Kavin to เควิน. Ging already read กิ๊ง.
- `tests/test_persona_names.py`: 10 regression cases for all three builders, Windows ASCII JSON round trips, old/new parsing/address resolution, send routing, and joiner filtering.
- `tests/test_rename_service.py`: added mocked old-to-new sweep coverage including unchanged PH/worker names; updated canonical fixtures.
- `tests/test_session_names.py`, `scripts/test_live_sessions.py`, `scripts/test_session_rename.py`: updated canonical expectations. `tests/test_cxo_claude_session_id.py`: asserts the actual fake-launcher `-n` argument.

Audited `lib/coo_policy.py`, `tools/node_dispatch.py`, `tools/mesh_check.py`, `runners/mac_agent.py`, and `scripts/hook-rename-nudge.py`: this checkout uses structured role/session identities there, not matching the old parenthesized persona string. Their worker-only ASCII constraints remain intact. `windows/cxo-claude.ps1` already reads the CLI JSON with `ConvertFrom-Json`; `ensure_ascii=True` remains unchanged and is tested under cp1252 output encoding.

`scripts/test_tm_prompt_loop.py` contains neither of the reported SomPong misspellings in this checkout; it was inspected and left unchanged. IRON-RULES was not touched.

## Validation

All commands used `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest`, without `-q`. Outputs were redirected to files under `/tmp/task-945c3f0e-*.log`.

1. `tests/test_persona_names.py tests/test_session_names.py scripts/test_live_sessions.py scripts/test_session_merge_live_rename.py tests/test_whois.py scripts/test_cxo_crosstalk.py tests/test_cxo_claude_session_id.py tests/test_cxo_claude_ps1.py`: **631 passed, 2 skipped** (37.43s; `final-passing.log`).
2. After the final reader/cleaner change: `tests/test_persona_names.py tests/test_session_names.py scripts/test_live_sessions.py tests/test_rename_service.py::test_persona_migration_keeps_topic_and_leaves_ph_worker`: **454 passed** (7.08s; `readers-final.log`).
3. After adding the actual launcher-name assertion: `tests/test_persona_names.py tests/test_rename_service.py::test_persona_migration_keeps_topic_and_leaves_ph_worker tests/test_cxo_claude_session_id.py`: **18 passed** (35.43s; `regression.log`).
4. `tests/test_rename_service.py scripts/test_session_rename.py`: **63 passed, 68 failed, 9 setup errors** (9.93s; `socket.log`). All failures/errors in this run are sandbox system-call restrictions: Unix socket operations raise `PermissionError: Operation not permitted`; one ownership test's `os.chown(..., 1001, -1)` raises `EINVAL`. The isolated mocked migration test passes separately.
5. `scripts/test_tm_prompt_loop.py`: **19 passed, 1 failed** (1.01s; `prompt.log`). Existing `test_registry_active_is_v1` expects poster `v1`, but the unchanged registry has poster `v3`.
6. Baseline red check: `-p persona_base_check tests/test_persona_names.py tests/test_rename_service.py::test_persona_migration_keeps_topic_and_leaves_ph_worker`: **11 failed** (0.90s; `base.log`), as required. A temporary pytest plugin loaded the six original production modules from `git show HEAD:<path>` into memory; it made no checkout changes and was deleted afterward. Every new regression case fails against the baseline behavior.
7. `bash -n` passed for all four listed shell scripts. `git diff --check` passed. Added Python source contains no literal U+200D; emoji joiners are escaped.

## Not checked / risk

- The required socket-backed tests cannot be certified green inside this sandbox; rerun them on the normal test host before merge.
- Native Windows/PowerShell execution was not available (PowerShell-dependent coverage is skipped); the JSON round trip itself passed with ASCII output under cp1252.
- No full suite, live tmux sweep, service restart, production messaging, or deployment was performed. Existing sessions change only when the updated service is deployed and its sweep runs.
- The unrelated prompt-registry expectation remains failing.

## Blockers

- Sandbox rejects Unix socket sends/binds and an ownership change needed by existing tests. Approval policy is `never`, so escalation is unavailable. CTO Main should rerun the two affected files in the normal environment.
- No implementation blocker remains; deployment and live rename are intentionally outside this task's authorization.

## Skill learning

- (none)

## CTO review fix (26 Oct 2026)

- `tests/test_spawn_coo.py:507-508` still expected the old COO name, so it failed on the branch. Both
  expected names are now the new one. The launcher's output was already right.
- The socket-backed tests were rerun on Contabo (70 files touching names, sessions or routing):
  3707 passed, 23 failed, 14 errors. Base 61bbe571 fails the same set in this environment
  (`scripts/test_maintab.py` fixture 'tmp' ×14, `scripts/test_session_status.py` ×9,
  `scripts/test_session_reconcile.py` ×8, `scripts/test_spawn_tab_routing.py` ×5). The one other failure was
  `test_spawn_coo`, now fixed: `tests/test_spawn_coo.py tests/test_persona_names.py` 72 passed, 1 xfailed.
- The new tests on base code: `tests/test_persona_names.py` plus
  `test_rename_service.py::test_persona_migration_keeps_topic_and_leaves_ph_worker` → 11 failed.
