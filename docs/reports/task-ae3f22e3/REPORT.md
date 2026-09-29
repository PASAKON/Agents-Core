# task-ae3f22e3 — host-agnostic merge path (Org Mesh W0.2)

## Summary

Built host-agnostic merge/revert path in `tools/git_ops.py` +
`tools/revert_task.py` (`tools/rollback.py` mirrored for consistency): a
project with origin remote merges/reverts in throwaway detached worktree of
`origin/<base>`, always pushes, then best-effort fast-forwards runtime
checkout via `git merge --ff-only` (git decides if dirty/diverged checkout
can advance). Project with no origin remote keeps exact original local path.
Item 7 (`review_diff` in `lib/org_tools_registry.py`) blocked — see
Issues/Blockers.

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
- `tests/test_merge_push.py`, `scripts/test_merge_noop_guard.py`,
  `scripts/test_merge_remote_branch.py`, `scripts/test_revert_task.py`,
  `tests/test_worktree_sparse.py` — read, not modified; all pass unchanged.

## Commits

- `86637292` — git_ops: host-aware merge via temp worktree (Org Mesh W0.2)
- `857e4286` — revert_task: host-aware revert via temp worktree (Org Mesh W0.2)
- `6ceefb4c` — rollback: host-aware rollback via temp worktree (Org Mesh W0.2)
- `5600f362` — tests: fake_projects fixture + Org Mesh W0.2 origin-path coverage

## Tests

- ran: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (full suite)
  - passed: 2832
  - failed: 0
  - skipped: 24
  - known-unrelated failure named in brief
    (`tests/test_machine_doctor.py::test_detect_machine_by_unique_os_when_hostname_does_not_match`)
    did not reproduce this run — full suite clean.
- ran: `python scripts/test_merge_noop_guard.py` — `ALL PASS` (4/4 `[PASS]`)
- ran: `python scripts/test_revert_task.py` — `OK` (6/6 unittest tests)
- ran: `pytest scripts/test_merge_remote_branch.py` — 7 passed (pytest-only
  file, no `__main__` block)
- ran: `pytest tests/test_merge_origin_path.py -v` — 10 passed: clean
  runtime; unrelated dirty file still fast-forwards; incoming change
  collides with dirty file (ff skipped, reason given, local edit
  untouched); diverged runtime (ff skipped, local commit untouched); origin
  moves between fetch and push (retry integrates, both land); conflict
  (nothing pushed); touches violation (refused before any push); no-origin
  project keeps old local path; revert clean; revert diverged.

## Issues / Blockers

- **Item 7 (`review_diff`) NOT done.** Task brief + declared `touches` both
  name `runners/org_tools_registry.py` — path does not exist (Glob
  confirmed). Real `_h_review_diff` implementation (wired into
  `runners/cto_mcp_server.py` via `reg.dispatch_sync`) lives in
  `lib/org_tools_registry.py`. Editing it blocked by
  `scripts/hook-self-repo-guard.py` (ADR 0020) — that path not in this
  task's `touches`. Sent `dev_message` to CTO flagging discrepancy, asked
  for `lib/org_tools_registry.py` added to touches — no reply received
  before this report. Did not attempt to work around the guard.
  - Design ready: keep existing
    `if not t or not t.get("worktree"): return "no worktree"` gate first,
    git/filesystem-free (required —
    `scripts/test_org_tools_registry.py::test_review_diff_equivalence`
    exercises this against a REAL project with no worktree, no mocking);
    then resolve `repo` via `_repo_path_for_host`, fetch `origin/<base>`
    when project has one, diff `origin/<base>...<branch ref>` (or local
    `<base>...<branch ref>` when no origin) via `_run`/`_resolve_merge_ref`
    from `tools.git_ops`, replacing current `tools.worktree` calls (which
    assume the task's own worktree dir exists locally — never true for a
    winbox/Contabo worker from the hub).
- Everything else in brief (items 1-6, 8, 9) done, committed, tested green.

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
  caller (git_ops, revert_task, rollback, and org_tools_registry once
  unblocked) from one fixture.

## Skill learning
- MISSING [no owner] : task briefs naming a file path should be verified
  against the live repo (and the task's own declared `touches`) before work
  starts — `runners/org_tools_registry.py` named in both brief and touches
  but never existed; real file (`lib/org_tools_registry.py`) one directory
  over, cost a full self-repo-guard round-trip plus a CTO dev_message to
  unblock. evidence: task-ae3f22e3, `scripts/hook-self-repo-guard.py` (ADR
  0020) refusal on `lib/org_tools_registry.py`.
- COSTLY [no owner] : resolving whether `lib.config.project_path_for_host`
  could be reused directly (it can't — see Notes for Reviewer) took a full
  grep-every-caller pass before writing any code. Prevented by: fixed rule
  — a shared helper doing its own internal lookup (`get_project`/
  `projects()`) is safe to call only from code paths a test patches at the
  SAME layer the helper reads from; if a test monkeypatches a narrower name
  (e.g. `module.get_project`), duplicate the helper's logic locally against
  the already-fetched object instead of calling the shared helper.
- (none) beyond the two items above.
