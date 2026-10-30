# REPORT task-c02aee60

## What changed

- C1: Contabo-first selection using complete live fill readings, then remote fill and worker-count ties. Explicit host pins retain their destination and resource checks. Caps are Contabo 3, winbox 3, Mac 2; winbox requires 4 GB free RAM and excludes ExpertAdvisor.
- The Contabo CPU exception requires an explicit Contabo task, CPU highest, RAM and disk below 80%, and at least 1.6 GB free RAM. An atomic shared database reservation permits one exception job at a time and remains held while that job is active.
- Unavailable tasks remain pending with a “queued for host” log. The existing watchdog retries the host queue, preserving explicit destinations; no timer was added.
- C2: PH selection uses the picker, including `--host mac`. The existing PH worker cap already counts cross-host and queued-remote workers. Mac dispatch uses mesh and its non-Claude workers use the shared bash launcher with BSD base64 handling.
- C3: CTO host refusal is unconditional in the common gate. Shell and Windows launchers enforce the Contabo-only rule.
- The router switch remains off by default, matching the supplied WIP configuration. Config is read for each routing decision; the environment switch takes precedence.

## Files changed

- `config/hosts.yaml`, `lib/router.py`
- `tools/delegate.py`, `tools/host_fill.py`, `tools/host_queue.py`, `runners/watchdog.py`
- `tools/spawn_ph.py`, `tools/node_dispatch.py` (C2 probe lease fact and Linux PH launch support only)
- `tools/clevel_gate.py`, `scripts/cto-claude.sh`, `scripts/cxo-claude.sh`, `windows/cxo-claude.ps1`
- `scripts/spawn-worker-remote.sh`
- `tests/test_router.py`, `tests/test_router_hub_only.py`
- This report.

## Validation

Only the two authorized pytest files were run, using fake probes, launchers, and a temporary SQLite database. The system Python has no pytest; the existing repository virtual environment supplied the interpreter.

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q -o addopts='' tests/test_router.py tests/test_router_hub_only.py
...........................                                              [100%]
27 passed in 1.41s
```

- `git diff --check`: passed.
- `bash -n scripts/spawn-worker-remote.sh scripts/cto-claude.sh scripts/cxo-claude.sh`: passed.
- Earlier test attempts were interrupted during asyncio executor shutdown in this environment. Dispatch tests now use an inline fake executor; the shared-slot concurrency test still uses real threads against a temporary database.
- Gitleaks scanned the tracked diff plus new files with redacted output: no leaks found.

## Not checked / risk

- No live probes, SSH, host launches, network checks, or full-suite runs were performed. B1 is already merged; live `host_fill` output was deliberately not collected under iteration 4's fake-only requirement.
- Windows PowerShell execution, live Mac launcher behavior, and PostgreSQL concurrency remain for integration validation. The local shared-slot race was tested with SQLite.
- Remote PH creation retains the existing mesh brief handoff: the owner sends the brief after launch; standard CLI output returns the brief and this next step.
- Legacy tests for the superseded load-based router were not run. CI owns broader validation.
- The Mac launcher uses portable bash/tmux commands; base64 decoding now selects BSD/GNU flags by uname. GNU timeout was already optional. No live launcher deployment was performed.

## Blockers

- The runner supplied branch `agent/codex-task-c02aee60` at `3a5ea30a`, rather than the requested branch/head. No branch was switched and main was not modified.
- The required `git cherry-pick 23620568` and later `git add` both failed because worktree Git metadata is read-only. The WIP cap/policy changes were applied to working files, with the iteration-4 RAM floor added. A commit cannot be created here; the PH/launcher must commit these files on the intended task branch, push, and open the PR.

## Skill learning

- (none)
