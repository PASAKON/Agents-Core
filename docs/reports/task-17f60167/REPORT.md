# REPORT — task-17f60167

## Summary
Added `scripts/hook-image-budget.py`, a `PreToolUse` hook that soft-blocks the
9th (and every later) image a **C-level** session reads or screenshots in one
session: it asks the model to state in one line why it needs to look, then
the identical retried call — and only the identical retried call — passes.
DEV worktrees and `WORKER_TASK_ID` sessions are fully exempt. Wired into
`.claude/settings.json`, tested (12 new cases, all pass), and documented.

## Files Changed
- `scripts/hook-image-budget.py` — new hook: FAIL-OPEN, stdlib-only, threshold `ORG_IMAGE_BUDGET` (default 8), state dir `ORG_IMAGE_STATE_DIR`.
- `.claude/settings.json` — added one `PreToolUse` entry (matcher `Read|mcp__claude-in-chrome__computer|mcp__claude-in-chrome__browser_batch`); every existing hook entry untouched.
- `state/image-budget/.gitignore` — `*`, matches the existing `state/cache-cold/.gitignore` convention.
- `tests/test_hook_image_budget.py` — new, 12 tests.
- `docs/ops/image-budget-hook-2026-09-25.md` — new ops doc.
- `docs/reports/task-17f60167/REPORT.md`, `WORKLOG.md` — this report.

## Verified gated-call list (from real transcripts, task-17f60167 §Facts to verify FIRST)
| Call | Gated when | Evidence |
|---|---|---|
| `Read` | `file_path` ends `.png`/`.jpg`/`.jpeg`/`.gif`/`.webp`/`.bmp` | sampled `Read` calls on `.png` paths all returned an image |
| `mcp__claude-in-chrome__computer` | `action` ∈ {`screenshot`, `zoom`} | 4/4 sampled `screenshot` calls returned an image; `left_click` 0/5; `zoom` gated on tool-description evidence (same params as `screenshot`, 0 samples in the small transcript corpus) |
| `mcp__claude-in-chrome__browser_batch` | any nested `{"name":"computer","input":{"action":"screenshot"\|"zoom"}}` | sampled batches nest a `computer` screenshot alongside `navigate`/`get_page_text` |

Not gated (evidence in the ops doc): `upload_image`, `gif_creator`, `find`,
non-image `computer` actions. One anomaly documented, not gated: a single
sampled `scroll` action also returned an image — n=1 against 0/5 for
`left_click`, judged not worth the false-positive rate of gating every scroll.

## Tests
- ran: `.venv/bin/python -m pytest tests -p no:warnings` (via `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`, since no `.venv` exists inside this worktree — the org venv is shared at `Agents/Core/.venv`)
- passed: 1142
- failed: 1
- skipped: 16
- The 1 failure is the pre-existing `tests/test_machine_doctor.py::test_detect_machine_by_unique_os_when_hostname_does_not_match` named in the task brief as known-failing on main today; not touched, per instructions.
- The other two pre-existing failures named in the brief (`tests/test_multihost.py::test_browser_operator_cap_reached_sets_conflict`, an ERROR in `tests/test_worktree_sparse.py::test_default_is_full_checkout_when_sparse_not_requested`) did **not** reproduce — ran both in isolation and they pass today.
- `tests/test_hook_image_budget.py` alone: 12 passed.
- Manual end-to-end smoke test (subprocess, `env -u WORKER_TASK_ID` to bypass my own worker exemption): 8 `Read` calls of `.png` paths → rc=0 each; 9th → rc=2 with the Thai nudge; identical 9th retry → rc=0; state file `{"count": 9, "blocked_hashes": [...]}`.

## Issues / Blockers
- None.

## Notes for Reviewer
- No `org:playbooks/developer.md` exists in the wiki — read `org:IRON-RULES.md` + ADR 0020 + `TASK.md` instead; flagging in case the CTO wants that playbook written.
- `state/image-budget/.gitignore` containing bare `*` self-ignores while untracked (confirmed via `git check-ignore`); had to `git add -f` it once. Same behavior already exists on `state/cache-cold/.gitignore` — not a new problem, just worth knowing if a reviewer wonders why `git status` didn't show it as untracked before the commit.
- The `scroll`-returns-an-image anomaly (documented in the ops doc) is worth a second look if a future session has a bigger transcript corpus to sample from — this task's corpus was only 9 `.jsonl` files.

## Skill learning
- MISSING [org wiki §playbooks] : no `playbooks/developer.md` exists for the developer role, unlike other roles implied by the shared-conventions doc's "relevant `playbooks/<your-role>.md`" instruction · evidence: `mcp__org__wiki_read` on `org:playbooks/developer.md` returned "ERROR: wiki page not found"
- COSTLY [no owner] : my own worker session env carries `WORKER_TASK_ID=task-17f60167` (set by `runners/worker_init.py` before exec), so every manual `Bash`-driven smoke test of a hook that exempts `WORKER_TASK_ID` sessions silently no-ops (rc=0 always) unless the env var is explicitly unset (`env -u WORKER_TASK_ID`) for that one subprocess call · evidence: first manual smoke test run produced rc=0 for all 9 calls with no state file written at all, traced to this exemption firing on my own test harness, not a hook bug · prevented by: when manually smoke-testing a hook that has a `WORKER_TASK_ID` exemption from inside a DEV worker session, always run the subprocess with `env -u WORKER_TASK_ID` first
- (none) beyond the two above
