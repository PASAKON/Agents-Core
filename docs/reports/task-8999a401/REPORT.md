# REPORT task-8999a401

## Files changed
- `windows/spawn-worker.ps1` — added optional `-MeshDispatch` (`''`, `'0'`, `'1'`), derived `$meshDispatchOn` (`$MeshDispatch -eq '1'` when passed, else `[bool]$AgentsRoot`), added `/WORKER.md` to `info/exclude` (`$toAdd`) and `WORKER.md` to `git reset -q -- ...`, and appended local branch publication via `python -m tools.remote_maintenance local-publish '$wt' '$Branch' '$Task'` in `New-ReportStepBody` when `-not $meshDispatchOn`.
- `tools/remote_maintenance.py` — added `'WORKER.md'` to `SCRATCH`, added `BRIEF_FILES`, `BRANCH_RE`, and `PH_BRANCH_RE`, hardened `outgoing_check` to refuse force/refspec pushes (`+...`, `:`), non-agent branches (`main`, `master`, etc.), and committed brief/scratch files (`TASK.md`, `WORKER.md`, `.org-task.json`, `.org-worker.mcp.json`, `CTO-FEEDBACK.md`), and added `local_publish(worktree, branch, task_id)` + CLI verb `local-publish`.
- `scripts/spawn-worker-remote.sh` — gated the remote `git push` skip on `ORG_MESH_DISPATCH=1` so `mac`/`winbox` launches also push when mesh dispatch is off.
- `tests/test_winbox_launcher_push.py` — unit tests covering generated `launch.ps1` text for flag on (marker only) vs flag off (marker + `local-publish`), `/WORKER.md` exclusion/reset, and `local_publish` refusing gitleaks findings, media files, >1 MB blobs, base-branch pushes, force-push refs, committed brief files, and <4 GB free RAM on Windows.

## What was done
1. Unified Winbox local branch publication when `ORG_MESH_DISPATCH` is off with the hub's mesh publication gate (`tools.remote_maintenance.outgoing_check(..., push=True)`), invoked via `python -m tools.remote_maintenance local-publish <worktree> <branch> <task_id>` from the Winbox `Agents-Core` checkout (`C:\Users\passg\mooniex\org` or `$AgentsRoot`).
2. Enforced all 6 required checks in one code path (`tools/remote_maintenance.py`):
   - 4 GiB free RAM floor on Windows (`require_free_ram()`).
   - `gitleaks` scan over `HEAD --not --remotes=public -m` in a hub-owned scratch repo (`scan_outgoing`).
   - Outgoing media extension (`MEDIA`) and >1 MB blob (`1048576`) checks across all outgoing commits/blobs.
   - Canonical target URL from `config/projects.yaml` (`publish_url`) and refusal of split `remote.origin.pushurl`.
   - Strict branch validation (`agent/<runner>-task-<8hex>`), refusing base branches (`main`/`master`) and force/refspec pushes (`+...`, `:`, `--force`).
   - Exclusion and pre-commit reset of `WORKER.md` alongside `TASK.md`, `.org-task.json`, `.org-worker.mcp.json`, and `CTO-FEEDBACK.md`, plus outgoing commit check refusing `BRIEF_FILES`.
3. Updated `scripts/spawn-worker-remote.sh` line 751 so `git push` is only skipped on `mac`/`winbox` when `ORG_MESH_DISPATCH=1`.

## Tests
```text
env -u ORG_DB_URL /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts="" tests/test_winbox_launcher_push.py tests/test_remote_maintenance.py tests/test_w33_spawn_worker_ps1.py tests/test_spawn_worker_ps1_runners.py tests/test_ps1_no_drive_scoped_vars.py tests/test_agy_settings_winbox.py tests/test_w06_launcher_report.py
344 passed
```

## Not checked / risk
- Live Winbox end-to-end worker spawn with `ORG_MESH_DISPATCH` unset will be exercised immediately after landing this PR via HostSpawn B3/B3b and SomPongAdmin `task-62e1066c`.
- Requires `C:\Users\passg\mooniex\org` on Winbox to be pulled to the merged commit so `tools/remote_maintenance.py` on Winbox has the `local-publish` CLI verb before spawning the next Winbox worker.

## Blockers
None.

## Skill learning
No new skill needed; existing `CTO_Gate_MergeChecklist` and `CXO_Protocol_DelegateExternal` cover this workflow.
