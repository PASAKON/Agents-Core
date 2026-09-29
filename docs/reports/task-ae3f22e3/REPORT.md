# task-ae3f22e3 — host-agnostic merge path (Org Mesh W0.2)

## Summary

Built host-agnostic merge/revert path in `tools/git_ops.py` +
`tools/revert_task.py` (`tools/rollback.py` mirrored for consistency): a
project with origin remote merges/reverts in throwaway detached worktree of
`origin/<base>`, always pushes, then best-effort fast-forwards runtime
checkout via `git merge --ff-only` (git decides if dirty/diverged checkout
can advance). Project with no origin remote keeps exact original local path.

Round 2 (CTO-FEEDBACK.md): CTO fixed the task's `touches` (its brief had
named a nonexistent `runners/org_tools_registry.py`; real file is
`lib/org_tools_registry.py`). Item 7 (`review_diff`) is now done — it diffs
from the host's runtime checkout via `_repo_path_for_host`/
`_resolve_merge_ref`, never the task's own `worktree` path, so it works for
a Contabo/winbox worker whose worktree never exists on the hub. Added
`tests/test_review_diff_origin.py` (2 tests) and one `tools/rollback.py`
origin-path test. All items 1-9 done. Full suite: 2835 passed, 0 failed, 24
skipped.

## Files Changed

- `tools/git_ops.py` — `merge_task` split: dispatcher + `_merge_local` (old
  path, byte-for-byte) + `_merge_via_temp_worktree` (new path). New
  `_repo_path_for_host`, `_create_temp_worktree`, `_remove_temp_worktree`,
  `_ff_runtime_checkout` helpers. `_push_once` pushes `HEAD:<base>` (works
  from detached worktree). Result dict gains `pushed`, `merge_sha`,
  `on_origin`, `runtime_updated`, `runtime_reason`, `host`.
- `tools/revert_task.py` — same split (`revert_task` dispatcher +
  `_revert_local` + `_revert_via_temp_worktree`). `_commits_ahead` gains
  optional `upto` param so depth-limit check measures against
  `origin/<base>` instead of possibly-stale local HEAD.
- `tools/rollback.py` — same pattern (`rollback` dispatcher +
  `_rollback_local` + `_rollback_via_temp_worktree`). No prior test file
  covers this standalone CLI.
- `conftest.py` — new `fake_projects` fixture: bare origin repo + clone
  standing in for runtime checkout, wired into `lib.config`'s project
  registry (patches `lib.config.projects`, covers every module calling
  `get_project` — git_ops, revert_task, rollback, org_tools_registry — from
  one fixture).
- `tests/test_merge_origin_path.py` (new) — 10 tests, temp-worktree
  merge/revert path (see Tests).
- `tools/worktree.py` — not touched. No helper needed there; temp-worktree
  helpers live in `git_ops.py`, reused by `revert_task.py`/`rollback.py`.
  Its `diff_summary`/`diff_full` now unused (see Issues/Blockers item 7) but
  left in place — removing exceeds "only touch worktree.py for a
  temp-worktree helper" scope; W0.3 owns rest of that file.
- `lib/org_tools_registry.py` — item 7 (round 2). `_h_review_diff` rewritten:
  keeps the `no worktree` gate as the first, git/filesystem-free check, then
  resolves `repo` via `_repo_path_for_host(proj, self_host())`, fetches
  `origin/<base>` when the project has one, and diffs
  `origin/<base>...<branch ref>` (or `<base>...<branch ref>` with no
  remote) using `_run`/`_resolve_merge_ref` from `tools.git_ops` — never
  the task's own `worktree` path. Imports: `self_host` added from
  `lib.config`; `_run`/`_resolve_merge_ref`/`_repo_path_for_host` added
  from `tools.git_ops`; `diff_summary`/`diff_full` import from
  `tools.worktree` replaced with `branch_name` (its only remaining need).
- `tests/test_review_diff_origin.py` (new, round 2) — 2 tests: branch
  published to origin only (no local worktree dir — the Contabo/winbox
  case), and a no-remote project diffing its local branch.
- `tests/test_merge_origin_path.py` — round 2 addition: one
  `tools/rollback.py` origin-path test (push happens, runtime ff reported).
- `tests/test_merge_push.py`, `scripts/test_merge_noop_guard.py`,
  `scripts/test_merge_remote_branch.py`, `scripts/test_revert_task.py`,
  `tests/test_worktree_sparse.py` — read, not modified; all pass unchanged.

## Commits

- `86637292` — git_ops: host-aware merge via temp worktree (Org Mesh W0.2)
- `857e4286` — revert_task: host-aware revert via temp worktree (Org Mesh W0.2)
- `6ceefb4c` — rollback: host-aware rollback via temp worktree (Org Mesh W0.2)
- `5600f362` — tests: fake_projects fixture + Org Mesh W0.2 origin-path coverage
- `33d00255` — docs: task-ae3f22e3 round-1 report
- (round 2 commits: `lib/org_tools_registry.py` review_diff rewrite,
  `tests/test_review_diff_origin.py`, rollback test, this report update —
  see `git log` for exact SHAs at submission time)

## Tests

- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (full suite, background, no `-q`/`-x`)
  - passed: 2835
  - failed: 0
  - skipped: 24
  - known-unrelated failure named in brief
    (`tests/test_machine_doctor.py::test_detect_machine_by_unique_os_when_hostname_does_not_match`)
    did not reproduce in either round's run — full suite clean.
- ran: `python scripts/test_merge_noop_guard.py` — `ALL PASS` (4/4 `[PASS]`)
- ran: `python scripts/test_revert_task.py` — `OK` (6/6 unittest tests)
- ran: `pytest scripts/test_merge_remote_branch.py` — 7 passed (pytest-only
  file, no `__main__` block)
- ran: `pytest tests/test_merge_origin_path.py -v` — 11 passed (10 from
  round 1 + the new rollback origin-path test): clean runtime; unrelated
  dirty file still fast-forwards; incoming change collides with dirty file
  (ff skipped, reason given, local edit untouched); diverged runtime (ff
  skipped, local commit untouched); origin moves between fetch and push
  (retry integrates, both land); conflict (nothing pushed); touches
  violation (refused before any push); no-origin project keeps old local
  path; revert clean; revert diverged; rollback origin path (pushed,
  runtime ff'd, status=cancelled).
- ran: `pytest tests/test_review_diff_origin.py -v` — 2 passed (branch only
  on origin; no-remote local-branch diff).
- ran: `python scripts/test_org_tools_registry.py` (standalone, per CTO
  instruction — pytest's pass count on this file proves nothing, read its
  own OK/FAILED line) — **`ALL PASS`** (all 25 checks, including
  `review_diff matches ('no worktree')` against the REAL `mooniex-claudeflow`
  project with no mocking — confirms the `no worktree` gate still runs
  before any git/config lookup).

## Issues / Blockers

- None. All 9 brief items done, committed, tested green across both rounds.

## Notes for Reviewer

- `_repo_path_for_host(proj, host)` deliberately does NOT call
  `lib.config.project_path_for_host` despite brief naming it.
  `project_path_for_host` does its own internal `get_project()` lookup
  against `lib.config`'s real module state; every existing merge/revert
  test (`tests/test_delegate_workdir.py`, `tests/test_merge_push.py`,
  `scripts/test_revert_task.py`) monkeypatches only `git_ops.get_project`,
  not `lib.config.projects` — calling the shared function would hit real
  `config/projects.yaml` inside those tests and break them.
  `_repo_path_for_host` replicates the same mac-fallback rule against the
  already-fetched `proj` dict — zero behavior change for real projects,
  zero test breakage.
- `has_origin` is `bool(proj.get("remote"))` — config field, not live `git
  remote get-url` check. Every existing fake-project test fixture (none set
  `"remote"`) took the untouched old code path automatically.
- `auto_push` semantics: on an origin project, merge/revert/rollback now
  always pushes regardless of `auto_push` (brief item 4 — flag now means
  only "a worker may not push its own branch directly"). `push=False` still
  overridable explicitly.
- `tools/rollback.py` has no existing test coverage (Glob confirmed — no
  `tests/test_rollback*.py` or `scripts/test_rollback*.py`). Mirrored same
  pattern for consistency but did not add new tests — not in the task's
  required-coverage list, adding test infra for an untested file felt like
  scope creep.
- `fake_projects` fixture patches `lib.config.projects` (the function), not
  `lib.config.get_project`. `project_path_for_host`/`get_project` resolve
  internal calls via `lib.config`'s own module globals at call time, not via
  whatever name a caller imported — patching `projects()` covers every
  caller (git_ops, revert_task, rollback, org_tools_registry) from one
  fixture. Confirmed end-to-end in round 2: `tests/test_review_diff_origin.py`
  calls `lib.org_tools_registry._h_review_diff` directly and it resolves the
  fake project with no extra patching.
- `lib/org_tools_registry.py`'s module docstring (top of file) still says
  "This module is NOT wired into `runners/cto_mcp_server.py`... yet" — that
  is stale; `runners/cto_mcp_server.py:104-106` calls
  `reg.dispatch_sync("review_diff", ...)` directly, and
  `scripts/test_org_tools_registry.py` proves full equivalence. Left
  unchanged — out of this task's scope, flagging for whoever next touches
  that docstring.
- `_h_review_diff`'s git/GitOpsError failures are NOT caught locally (e.g. a
  branch resolvable neither locally nor on origin raises out of
  `_resolve_merge_ref`) — this is intentional, not an oversight:
  `lib.org_tools_registry.dispatch`/`dispatch_sync` already wrap every
  handler call in a uniform `except Exception: return f"ERROR: {e}"` (Do-3,
  see the module's own docstring on `dispatch`), so adding a second
  try/except here would just duplicate that and risk drifting from its
  format.

## Skill learning
- WRONG [no owner §task-brief-verification] : task briefs naming a file
  path should be verified against the live repo (and the task's own
  declared `touches`) before work starts — `runners/org_tools_registry.py`
  named in both brief and touches but never existed; real file
  (`lib/org_tools_registry.py`) one directory over. Cost a full
  self-repo-guard round-trip plus a CTO dev_message, unanswered for the
  rest of round 1 — the CTO's own round-2 feedback confirmed "My brief
  named `runners/org_tools_registry.py`. That file never existed; the
  mistake was mine." evidence: task-ae3f22e3 round 1 blocker,
  CTO-FEEDBACK.md round 2 line 3. fix: worker escalation via dev_message
  worked exactly as designed once the CTO read it — the miss was the CTO's
  dev_message inbox not being checked mid-round, not the escalation
  mechanism itself.
- COSTLY [no owner] : resolving whether `lib.config.project_path_for_host`
  could be reused directly (it can't — see Notes for Reviewer) took a full
  grep-every-caller pass before writing any code. Prevented by: fixed rule
  — a shared helper doing its own internal lookup (`get_project`/
  `projects()`) is safe to call only from code paths a test patches at the
  SAME layer the helper reads from; if a test monkeypatches a narrower name
  (e.g. `module.get_project`), duplicate the helper's logic locally against
  the already-fetched object instead of calling the shared helper.
- (none) beyond the two items above.
