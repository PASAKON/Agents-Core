# REPORT task-8bc03719

## Changes

- `tools/ask_run.py`: optional CLI/MCP what/does/impact on commands, questions and batch items; normalize lengths to 40/70/70 before hashing; command canonical JSON uses command/what/does/impact order, compact Unicode JSON and plain command bytes without a brief. Commands carry sha256.
- Requester lane follows the C-level role. Project Heads use the hub projects row matched by full or bare PH session, preserving its PascalCase name and lane. Missing, invalid, ambiguous or unavailable metadata is omitted.
- `lib/ceo_text.py`: legacy detail trimming with ellipsis under a brief. Full secret and hidden-character checks run before truncation; no-brief refusals and question/option limits remain.
- `runners/cto_mcp_server.py`, `runners/coo_mcp_server.py`, `lib/org_tools_registry.py`: expose and forward all three fields through schemas and handlers.
- `.claude/skills/ALL_Protocol_RunInbox/SKILL.md`: CEO ruling Q-20261115-1420-81a2 paragraph; replaced refusal rules retained as superseded.
- `tests/test_run_mini_card.py`, `tests/test_ceo_text.py`: new regression coverage. Updated requester/hash expectations in `tests/test_ask_run.py` and `tests/test_ask_run_questions.py`.

## Validation

- Read Console `src/run/brief.js` at the requested external path, without modifying or importing it. Evaluated its commandCanonical algorithm with Node to obtain three fixed SHA-256 vectors: legacy command, omitted empty field, and Unicode/emoji/quotes/backslash/newline escaping.
- Ran the requested plain command with `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ask_run*.py tests/test_ceo_text*.py tests/test_run_mini_card.py`. Fake HTTP server setup fails because this sandbox forbids socket creation (`PermissionError: [Errno 1] Operation not permitted`). Interrupted the stalled run; a fail-fast diagnostic reproduces the first setup error at `tests/test_ask_run.py:138`.
- Focused `tests/test_run_mini_card.py tests/test_ceo_text.py`: 25 passed. Covers canonical hashes, CLI/MCP payload parity, brief lengths, original-text safety checks, all five lanes, PH lookup success/failure, grouped brief propagation and legacy trimming/refusal.
- Existing requester tests (`test_ask_run.py -k 'requester_session or requester_needs'`): 7 passed.
- Python compilation of all five changed Python implementation files passed; `git diff --check` passed.
- Skill lint ran: 78 findings and one refused symlink entry across the repository, including a stale skill index. No unrelated skills were changed.
- No live card sent. New submission tests use dry_run; existing network tests target their fake loopback hub.

## Not checked / risk

- Full HTTP/MCP integration suite needs rerunning in an environment that permits its local sockets. This is not a full-suite pass.
- No live Console submission, real hub portfolio lookup, or deployment was tested. PH metadata tests use a fake connection.
- No MAILBOX.md was present at the checkpoints.

## Blockers

- Sandbox socket restrictions prevent completion of the full requested suite. Reviewer/launcher should rerun that command outside this restriction.
- `git add` and the requested `git commit -F /tmp/task-8bc03719-commit.txt` both failed: Git cannot create the worktree's `index.lock` because the shared Git metadata is read-only. Changes remain unstaged in the assigned worktree for the launcher to commit and push; no commit was created.

## Skill learning

- CEO ruling Q-20261115-1420-81a2 authorizes the RunInbox rule-body change under ALL_Protocol_SkillAuthor §5; old refusal statements remain marked superseded. Console brief.js confirms normalization must precede command hashing.
