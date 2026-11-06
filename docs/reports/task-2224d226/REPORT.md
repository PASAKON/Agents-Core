# REPORT task-2224d226

Implemented the Contabo hub publication tools and uninstalled systemd units.
The assigned branch started clean at `4ea7f577f6044588519328d8c7d59e76305d9335`,
identical to the available `origin/main`; no earlier implementation was present.
No default branch, live checkout, service, or remote was changed by this task.
Changes remain in the assigned worktree for the launcher to commit and push.

## Files changed

- `tools/publish_scan.py`: scans additions throughout history, including merge
  parents and subsequently removed values; implements all requested rules and
  allowances, exact-value checks against `origin/main`, redacted shapes, binary
  sizes (including deletions), and exit statuses 0/1/2.
- `tools/hub_sync.py`: fetches main, detects ahead commits and existing candidate
  PRs, builds a two-parent candidate using Git plumbing, scans before pushing,
  creates a new sync branch and PR, closes superseded PRs, and sends CTO letters.
  Reuses the disk steward's validated `state/locks/cto-active` pointer and
  `lib.mailbox.send` convention. External command output is captured, and blocker
  findings include only path, line and rule.
- `tools/kit_overlap.py`: reports shared PR/local-main paths, skills first;
  handles unavailable inputs without a failing exit status.
- `deploy/systemd/kit-hub-sync.service`: root oneshot in the live checkout using
  `scripts/hub/with-org-db-env.sh` and the existing virtualenv interpreter.
- `deploy/systemd/kit-hub-sync.timer`: every two hours with `Persistent=true`.
- `tests/hub_sync_support.py`: isolated local repositories, protocol stubs and
  byte snapshots. Stub diagnostics print argument counts, never arguments;
  stdout carries canned protocol responses required by the calling tools.
- `tests/test_hub_sync.py`: publication, dry run, conflicts, clean divergence,
  scanner blockers, supersession, idempotence, errors and checkout preservation.
- `tests/test_publish_scan.py`: rules, allowances, known values, historical
  removal, redaction, binary addition/deletion and errors.
- `tests/test_kit_overlap.py`: local/PR overlaps, skill ordering and errors.
- `docs/reports/task-2224d226/REPORT.md`: this report.

## Validation performed

Ran the requested command with the specified interpreter, without adding `-q`:

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_hub_sync.py tests/test_publish_scan.py tests/test_kit_overlap.py
54 passed in 17.00s
```

The repository's existing `pytest.ini` supplies quiet output itself. All tests
use local bare remotes in `tmp_path`, fake gh/gitleaks executables on PATH and
injected letter delivery. Git's permitted transport is restricted to `file` in
the fixtures. No test uses the org database wrapper or makes a network call.
Successful dry-run/publication and blocked paths verify byte-identical HEAD,
index and worktree snapshots, including staged, unstaged and untracked files.
Publication tests verify that the bare remote's main remains unchanged and that
the new candidate has local main and origin/main as its ordered parents.
Whitespace checks on the three tool files produced no diagnostics.

Sample actual output saved by the dry-run test against its local fixture repo:

```text
plan: 1 commits; 1 files; skills: demo; gitleaks: clean; publish_scan: clean; binaries: 0
new branch: sync/contabo-main-20261106-1709; PR to main
dry run: no push, PR or report letter
```

## Not checked / risk

- Contabo reports **gh 2.45.0** (`2025-07-18 Ubuntu 2.45.0-1ubuntu0.3`) and
  **gitleaks 8.30.1**. Version commands were run; live authentication, actual
  scanner execution and GitHub API behavior were not exercised. Tests use stubs.
- **The first live run remains unperformed.** It must confirm CTO pointer/mailbox
  routing, wrapper configuration, live scan findings and PR creation. The units
  have not been installed, enabled or started; the CEO card owns that action.
- Scans are heuristic. Binary content is listed, not inspected by publish_scan;
  existing exact values in origin/main are deliberately treated as known.
- Same-minute branch collisions fail instead of reusing a branch. A failure after
  pushing but before creating the PR can leave an orphan sync branch. Publication
  and GitHub/mail delivery are not one atomic transaction.
- The available origin/main ref was verified locally, not refreshed over the
  network during implementation. The launcher owns task-branch publication.

## Blockers

- No implementation or test blockers remain.
- The task's review PR has not been opened: it awaits the launcher's commit and
  push of these changes, as required by the worker contract. Do not merge it.

## Skill learning

- (none)
