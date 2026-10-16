# REPORT task-5e2f9a21

## Changes

- Added `tools/kit_sync.py pull`: each configured wiki checkout gets a total 15-second git budget, a clean-tree check, and `pull --ff-only --no-rebase` with autostash disabled. Failures emit one generic stderr line per root and return zero. No reset, stash, deletion, or local commits.
- Wired both POSIX launchers alongside memory pulls, including the COO wiki pull; added Mac checkout discovery. Wired Windows profile-relative Rules/Wikis environment variables and the wiki pull before Claude starts.
- Added three winbox REBUILD rows owned by CTO for Agents-Rules, Agents-Wikis, and Agents-Memory, with clone restore commands and the CEO's 2026-10-16 OrgMesh approval (IRON §54).
- Added `tests/test_kit_sync.py` with temporary git repositories covering fast-forward, divergence, three dirty states, non-git directories, status/pull timeouts, offline remotes, and launcher wiring.

Files changed: `tools/kit_sync.py`, `tests/test_kit_sync.py`, `scripts/cxo-claude.sh`, `scripts/cto-claude.sh`, `windows/cxo-claude.ps1`, `config/machine-contract.yaml`, and this report.

## Validation

Used `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` with this worktree as cwd; the worktree has no virtualenv and system Python has no pytest.

- `pytest tests/test_kit_sync.py tests/test_cxo_claude_ps1.py tests/test_launcher_resume_short_id.py --tb=short`: **49 passed, 1 skipped** (PowerShell unavailable). Includes all **10 new helper/wiring cases**.
- `pytest tests/test_machine_doctor.py -k 'not on_version_change' --tb=short`: **29 passed, 2 deselected**. The initial runs including version-change checks stalled and were interrupted; no completed count is claimed for those runs.
- Direct YAML validation: all three new rows have the expected machine, path, class, owner, and restore command.
- Broader helper/Windows/model-launch suite: **94 passed, 1 skipped, 1 failed**. Failure: `test_script_org_tools_registry_verdict` invokes a legacy harness blocked by the real-checkout tasks.db protection.
- Broader helper/launcher/Org P2 suite: **93 passed, 1 skipped, 1 failed**. Failure: `test_records_another_user_wrote_are_ignored` cannot chown its temporary fixture in this sandbox.
- COO suite: **55 passed, 1 xfailed, 7 failed**. Six launcher cases fail at the system bus connection (`Operation not permitted`), and one MCP case cannot chown its temporary fixture. Wiki pulls return successfully and report unavailable checkouts before those launcher failures.
- Counts above are per invocation and overlap; they are not additive.
- `bash -n scripts/cxo-claude.sh scripts/cto-claude.sh` and `git diff --check`: passed.
- Gitleaks stdin scan of the diff, including new files: passed, no leaks. Final scan includes this report.

## Blockers

- Per the final Remote Worker Contract, the launcher owns committing and pushing after this turn. Changes remain uncommitted on `agent/codex-task-5e2f9a21`; PR creation and the final head SHA remain pending that handoff. No PR number is available. Open a PR after committing/pushing; do not merge.
- Initial HEAD and local `origin/main` both resolve to `3a3036ed8b7b38727ef5b6171d43e2fa1770a489`. The default branch was not changed or pushed.
- Full green validation is blocked by the sandbox/system-bus, ownership, legacy database-harness, and stalled version-change cases above. No live Mac or Windows smoke test was performed; PowerShell parsing was skipped because pwsh is absent.

## Skill learning

- (none)
