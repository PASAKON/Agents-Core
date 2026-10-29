# REPORT task-6c990fcc

## Summary

Implemented the SafeRestart P4 (`winbox`) fix so that a registered, live, resumable session whose Windows Terminal tab is missing (`windows/wake.ps1` exit `2`, non-ambiguous) is saved by its JSONL transcript rather than failing the entire preflight:

- Added `win_resumable(entry)` and updated `win_preflight(rows, manifest=None)` in `tools/restart_run.py` to split `win_wake(row, 'preflight', True)` by exit code:
  - When `wake.ps1` exits `2` (no matching tab, excluding ambiguous multi-tab exit `2`), `identity(row) in win_live()`, and the row's manifest entry passes `win_launcher(entry)` with a known `uuid`, the row is marked `untyped` (`row['untyped'] = True`) and remains in the manifest with its own `mode` so `resume` reopens it with `--resume <uuid>` in a new tab carrying `#<sid>`.
  - When `wake.ps1` exits `2` for a non-live or non-resumable row (e.g. missing `uuid`), or on any other preflight failure (ambiguous tabs, foreground guard refusal exit `3`, desktop/UIA failure exit `4`, or `win_gate()` refusal exit `3`), preflight still fails closed with nothing saved, closed, or written.
- In `prep()`'s destructive loop on `winbox`, an `untyped` row skips `/compact` and `/session-save`, calls `win_record(row, 'force_saved')`, prints `no_tab_saved_by_jsonl: <name>`, and calls `gone(row, 'winbox')`.
- In `prep --dry-run` on `winbox`, an `untyped` row prints `would save by jsonl (no tab): <name>` in the per-row plan and touches nothing on disk.
- Left `report()`, `ask_run()`, and all Contabo/Mac paths untouched.

## Files changed

- `tools/restart_run.py` — updated `win_preflight()`, `win_record()`, `win_plan_lines()`, `prep()`, and added `win_resumable()`.
- `tests/test_restart_run.py` — added unit tests covering:
  - (a) tab-missing live resumable row (`resume_full`, `compact_then_resume`, `resume_lazy`) -> no `send`, `force_saved` recorded, `gone` called, entry preserved in manifest, `prep` exits `0`;
  - (b) tab-missing non-live row -> preflight fails (`exit 1`), no marker or manifest written;
  - (c) tab-missing row with no `uuid` -> fails closed (`exit 1`), no marker or manifest written;
  - ambiguous multi-tab (`exit 2`) and foreground refusal (`exit 3`) on live resumable rows -> fail closed (`exit 1`);
  - (d) `--dry-run` on a tab-missing live resumable row -> prints `would save by jsonl (no tab): <name>` and writes nothing.
- `docs/reports/task-6c990fcc/REPORT.md` — task report.

## Validation

- Head SHA: pending launcher commit (AGY remote worker contract: file tools only; git commit and shell validation delegated to the launcher/review process).
- Test command for review validation:
  `pytest -q tests/test_restart_run.py`
- Output tail: delegated to the review process per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process"). Static verification confirmed all existing test fixtures and assertions in `tests/test_restart_run.py` remain satisfied alongside the new test cases.

## Not checked / risk

- `windows/wake.ps1` exit codes on a real Windows desktop session were not executed; tests stub `wake.ps1`, `win_live`, `win_record`, and `gone` (printing `argc` only, never `env`).
- Shell test execution and `gitleaks` scan were left to the launcher/review process per the AGY file-tools-only contract.

## Blockers

- (none)

## Skill learning

- (none)
