# REPORT task-3cc9b119

## Files changed
- `tools/delegate.py`: Added `"runner_model": task.get("runner_model")` to `_task_meta()`; updated `_spawn_remote()` to query fresh task data from `db.get_task(task_id)` after host validation.
- `scripts/spawn-worker-remote.sh`: Added `--runner-model` argument parsing and decoding from `--task-meta-b64` (`.org-task.json`); added regex validation `^[A-Za-z0-9._:-]{1,64}$`; wired `--model` into agy with `gemini-3.8-flash-high` fallback; wired `-m <model>` into codex when non-empty; updated dry-run outputs; implemented media gate in `emit_report_commit_push` unstaging media extensions and >1MB binaries and appending blocker items to `REPORT.md` while preserving files on disk.
- `windows/spawn-worker.ps1`: Added `$TaskMetaB64` and `$RunnerModel` parameters and sidecar decoding; added regex validation `^[A-Za-z0-9._:-]{1,64}$`; wired agy fallback and codex `-m`; added equivalent media gate in `New-ReportStepBody`.
- `tests/test_h3_runner_model_launch.py`: Added 18 unit and integration tests verifying task metadata propagation, fresh DB lookup, launcher dry-run outputs, fallback behavior, bad runner model rejection, media gate unstaging and blocker generation, PowerShell script structure, `bash -n` validation, and role config/registry script verdicts.

## What was done
1. **Runner Model Propagation & Refresh**:
   - In `tools/delegate.py`, `_task_meta` now includes `"runner_model": task.get("runner_model")`.
   - In `_spawn_remote`, fetched the fresh task record via `db.get_task(task_id)` to ensure the router-selected `runner_model` and `runner` are picked up even if the incoming `task` dict was stale.
2. **Contabo / Linux Launcher (`scripts/spawn-worker-remote.sh`)**:
   - Initialized `RUNNER_MODEL=""` early to satisfy `set -uo pipefail`.
   - Extracted `runner_model` from `.org-task.json` (decoded from `--task-meta-b64`) or `--runner-model`.
   - Validated against `^[A-Za-z0-9._:-]{1,64}$` and exit 2 on bad input.
   - For `agy`, runs `--model "$AGY_MODEL"` (defaulting to `gemini-3.8-flash-high` when unset).
   - For `codex`, runs `-m "$RUNNER_MODEL"` only when non-empty.
   - In `emit_report_commit_push`, added a media gate after `git add -A`: unstages media files (`png`, `jpg`, `jpeg`, `gif`, `webp`, `heic`, `mp4`, `mov`, `webm`, `mkv`, `avi`, `mp3`, `wav`, `m4a`, `aac`, `flac`, `ogg`) and any staged binary larger than 1 MB (via `git diff --cached --numstat`). Appends `- media not committed: <path> (<size>) — upload per CXO_Rules_GDrive_Filing and put the link here` under `## Blockers` in `REPORT.md`, keeping all files intact on disk.
3. **Windows Launcher (`windows/spawn-worker.ps1`)**:
   - Added parameters `$TaskMetaB64` and `$RunnerModel`, sidecar extraction, and `^[A-Za-z0-9._:-]{1,64}$` validation.
   - Configured `agy` to use `$agyModel` (fallback to `gemini-3.8-flash-high`) and `codex` to append `-m $RunnerModel` when present.
   - Implemented the media gate in `New-ReportStepBody` unstaging media extensions and >1MB binaries, appending blockers to `REPORT.md`.
4. **Comprehensive Test Suite**:
   - Created `tests/test_h3_runner_model_launch.py` covering all DO and VERIFY requirements.

## Tests
- Default full pytest suite:
  `3572 passed, 27 skipped in 265.74s (0:04:25)`
- `tests/test_h3_runner_model_launch.py`:
  `18 passed, 1 warning in 5.18s`
- Related launcher suites:
  - `tests/test_spawn_worker_remote_runners.py` + `tests/test_w06_launcher_report.py`: `41 passed`
  - `scripts/test_spawn_worker_ps1.py` + `tests/test_spawn_worker_ps1_runners.py`: `66 passed`
  - `tests/test_w03b_local_launcher.py`: `29 passed`
- `scripts/test_mcp_role_config.py`:
  Verdict: `OK — 0 failure(s)`
- `scripts/test_org_tools_registry.py`:
  Verdict: `ALL PASS`
- Syntax check:
  `bash -n scripts/spawn-worker-remote.sh`: RC 0 (verified by `test_bash_n_spawn_worker_remote`)
- `ORG_HOST=contabo` verification:
  `189 passed in 26.32s` across `test_self_host.py`, `test_spawn_remote_linux.py`, `test_worker_naming.py`, `test_w04_self_host_sites.py`, and `test_w15_duty_split.py`.

## Blockers
- None.

## Skill learning
- `spawn-worker-remote.sh` uses `set -uo pipefail`. All variables like `RUNNER_MODEL` must be initialized at script top (`RUNNER_MODEL=""`) before being checked or referenced, or access them with `${VAR:-}` to avoid unbound variable aborts under `set -u`.
- Existing test harnesses (such as `tests/test_spawn_worker_ps1_runners.py`) extract PowerShell code blocks using strict string substring markers like `code.index("else {", codex_start)`. Avoid using nested `else {` constructs within those blocks to prevent breaking string-slice index boundaries.
- In `tools/delegate.py`, unit test fixtures may invoke `_spawn_remote` with mock tasks that do not exist in the temporary database or without an initialized database. Wrapping `db.get_task(task_id)` in a `try...except` block ensures that unit tests with synthetic tasks continue to run smoothly while real tasks properly fetch updated fields from SQLite.
