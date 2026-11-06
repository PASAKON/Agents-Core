# REPORT task-fb34bf0c

Implemented the browse guard trust-boundary fix. Read incident commit
baae88400822d67a3891067df22ce101bb0a1785 before editing.

## Files changed

- `tools/delegate.py`: deploy origin/base guard, policy and commit-gate bytes by SHA256 to winbox's `C:\Users\passg\mooniex\agy-browse\`; deploy the commit helper beside the remote Linux launcher.
- `tools/agy_browse.py`, `config/agy-browse.yaml`: absolute trusted-tool allow rule; reject bare wildcard hosts; read-only Flow port 9226 restricted to `labs.google`. Mutation verbs refuse before attaching. Existing 9224/9280/9281 policy rows remain unchanged. Policy lookup stays anchored to the executable's directory tree, never cwd or worker environment.
- `config/agy-settings.json`, `config/agy-settings-winbox.json`: require pinned absolute guard paths. Winbox also rejects worktree interpreters; its two rules permit the pinned venv or named Python311 installation.
- `windows/spawn-worker.ps1`, `scripts/spawn-worker-remote.sh`, `runners/agy_local.py`: browser prompts use the pinned copy. Non-browser edit-only prompt remains word for word unchanged.
- `tools/guard_commit.py`: both launchers call this trusted helper before committing. It uses metadata captured before worker execution, not `.org-task.json`. Undeclared staged guard additions, modifications, deletions and rename sources are reverted and reported as `guard file reverted: <path>`. Exact paths, directory prefixes and declared globs follow existing touches semantics. A helper error stops the commit. The helper and deploy code are protected too.
- `tools/route.py`: recognize pinned absolute browse paths in browser briefs.
- `docs/ops/agy-browser.md`: document paths, policy, commit gate and rollout boundary.
- Tests: `test_guard_boundary.py`, `test_agy_browse.py`, `test_agy_local.py`, `test_agy_settings_winbox.py`, `test_spawn_worker_remote_runners.py`, `test_route_browser_agy.py`.

## Validation performed

Background test run, output `/tmp/task-fb34bf0c-tests.log`:

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_guard_boundary.py tests/test_agy_browse.py tests/test_agy_local.py tests/test_agy_settings_winbox.py tests/test_spawn_worker_remote_runners.py tests/test_spawn_worker_ps1_runners.py tests/test_route_browser_agy.py
305 passed, 14 skipped
```

Tests exercise SHA256 deploy/no-op behavior using mocked transport, pinned command rules,
policy anchoring, wildcard rejection, all read-only verbs, unchanged existing ports,
captured task metadata, sidecar tampering, guard restoration, authorized touches,
and actual local Git commits produced by both agy/codex shell launcher report steps.
PowerShell launcher wiring and the unchanged edit-only prompt have static regression checks.

The six updated absolute-command acceptance cases fail against the original guard
from base `f154a33e8167c741d5d35e9856c0550331693b66` in an isolated temporary package;
they pass against this change. Output: `/tmp/task-fb34bf0c-base-tests.log`.
`bash -n scripts/spawn-worker-remote.sh` and `git diff --check` pass.

## Winbox settings rollout — CEO card required

Not installed. After approval, run from the updated repository checkout on winbox:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File windows\install-agy-settings.ps1 -ExpectSha256 3144d26fcf6942c8fee469ea118d89aea3564a7429f003b1e0e2e12e781c9bcc
```

The guard deployment must contain this change from the trusted origin/base before
launching browser workers. Mac/Contabo main checkout and installed settings must
also receive the updated policy/tool and absolute-path allow rule. Never include
the pinned folder or main checkout in a worker's writable `--add-dir` directories.

## Not checked / risk

- No SSH to winbox, settings installer execution, live deployment or real browser action was performed.
- This sandbox denies local sockets. The 14 live Chromium tests skip explicitly on that PermissionError; live browser behavior still requires an environment permitting sockets.
- PowerShell execution was not available here. Its command matching and generated launcher wiring are tested without claiming Windows runtime coverage.
- Pinning relies on agy's enforced writable-directory boundary. The pinned files are owned by the launcher outside those directories; this is not a separate OS user or filesystem ACL boundary.
- The commit gate checks staged changes before the hub commit. It does not rewrite commits a different runner may already have created.

## Blockers

- Fetch was denied because the shared Git metadata is read-only in this sandbox. The incident commit was already present and was read successfully.
- `git commit -F docs/reports/task-fb34bf0c/COMMIT_MESSAGE.txt` failed because Git could not create `index.lock` on the read-only shared metadata. The launcher must stage, commit and push the completed changes. No Write tool was available, so the message file was written with apply_patch; its text was never embedded in a shell command. No default-branch changes were made.

## Skill learning

- (none)
