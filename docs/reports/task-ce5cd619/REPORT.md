# REPORT task-ce5cd619

Implemented the org-rule session name for the Windows launcher. Changes are left uncommitted for the launcher.

## Files changed

- `lib/session_names.py`: added the `name` CLI verb using configured C-level personas and the existing PH naming helper; emits one ASCII JSON line, rejects invalid roles and missing PH lane/project with usage and exit 2, and preserves `prefix` output.
- `windows/cxo-claude.ps1`: resolves the rule name from the repo root, parses JSON, and passes it to `-n`. Explicit `-TabTitle` bypasses the lookup. Failures retain the existing machine/title name. Console window title is unchanged; script remains ASCII.
- `tests/test_session_names.py`: added subprocess coverage for CTO, CMO, COO, PH, invalid inputs, cp1252 stdout, and unchanged module `prefix` output.
- `tests/test_cxo_claude_ps1.py`: added static checks for lookup, working directory restoration, fallback, JSON parsing, and title override; existing ASCII check remains.
- `docs/reports/task-ce5cd619/REPORT.md`: this report.

## Validation

Ran without additional pytest flags:

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_session_names.py tests/test_cxo_claude_ps1.py tests/test_w31_windows_portability.py tests/test_w33_node_dispatch_windows.py
704 passed, 2 skipped in 162.00s (0:02:41)
```

`git diff --check` passed.

## Not checked / risk

- No PowerShell execution or live winbox launch: this box has no pwsh, as stated in the task. Launcher behavior is covered by static checks only.
- The required suite has two skipped tests; tests outside the specified suite were not run.

## Blockers

- (none)

## Skill learning

- (none)
