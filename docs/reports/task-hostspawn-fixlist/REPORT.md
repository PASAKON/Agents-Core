# HostSpawn spawn_ph fix list (task-84a9898b)

Branch `agent/agy-task-84a9898b`, based on main `0f8ea19b` (PR #617 merged: its
CTO-only-on-Contabo rule in `tools/clevel_gate.py` is untouched).

## What changed

| # | Fix | Where |
|---|---|---|
| 1 | `_pid_is_launcher` probes with `lib.proc.pid_alive` (a dead pid on Windows raised WinError 87 out of `live_lock`, #579). `cxo-claude.ps1` now wraps everything after the lock write in the `try` whose `finally` removes the lock, `.uuid`, and a PH's claim and owner record, so a launch that throws before claude starts leaves nothing behind. | `tools/clevel_gate.py`, `windows/cxo-claude.ps1` |
| 2 | A PH is named by the registry's display name (`HostSpawn`, not the typed `hostspawn`): `_register_project` reads the row's `name`, rebuilds the launch command with it, so `.project` and `--project` agree. A NEW project row must be PascalCase (`pf.pascal_refusal`, opt-in `open_project(pascal_name=True)`, which only `spawn_ph` sets). | `tools/spawn_ph.py`, `lib/portfolio.py` |
| 3 | The owner recorded for a PH is the hub's session id (`cto-f69c4825`), not the launcher lock id (`cto-fresh`): `spawn_ph.hub_sid` maps a non-8-hex lock id through `<lane>-<id>.uuid` (last 8 hex of the UUID). `restart_run.win_hub_ph` maps an old `cto-fresh` row the same way through `c_level_sessions.resume_uuid`. | `tools/spawn_ph.py`, `tools/restart_run.py` |
| 4 | `session-rename.sh` says `unchanged` by the FULL rendered name (new record `state/locks/<role>-<id>.rendered`), not by the topic. `.topic` is kept as it was (`--show`, the rename nudge hook and `cxo-claude.sh` read it). | `scripts/session-rename.sh`, `docs/SESSION-RENAME-STATE.md` |

`tools/rename_service.py`: **no behaviour change.** Its topic-vs-project drop
(`topic == project`) is already an exact, case-sensitive compare, so a topic that
differs from the project only by case is already kept. I added a comment and a pin
test. If the intent was the opposite (drop a topic that matches the project
ignoring case), that is a one-line `casefold()` change and needs a ruling.

## Tests

`tests/test_hostspawn_fixlist.py`: 52 tests, fakes only (no host, network, hub or
tmux; the rename script talks to a stand-in unix-socket service). Each fix was
reverted to the base file in turn and the file re-run: fixes 1, 2, 3 and 4 each
turn tests red (the `rename_service.py` pin is the one test that passes either
way, by design).

## Not checked / risk

- **`windows/cxo-claude.ps1` was verified by text only.** There is no `pwsh` on
  this box, so the widened `try/finally` was never executed. The check is a
  brace-depth test that every `throw` after the lock write sits inside the
  try whose finally does the cleanup, plus a manual read: no `exit` inside the
  widened region except the final `exit $code`; `$wroteActive`, `$isPh` and
  `$mcpConfig` are set before they are read in `finally`. A run on winbox is
  the real test.
- `pascal_name` is opt-in. The CLI `tools/portfolio.py open` and every other
  caller keep free-text names, so a non-PascalCase row can still be created
  that way.
- The mesh branch of `spawn()` (a PH spawned on another host) and the card path
  (`card_owner`, requester "cto-fresh") are not canonicalised: the remote claim
  is written with the typed name and the lock-id owner. Known limit.
- `restart_run.win_hub_sid` assumes `c_level_sessions.resume_uuid` holds the
  session UUID for a closed or saved session; a session that never saved has no
  row, and its PH is then reported "no owner session" as before (fail closed).
- The 7 registry rows that already say `cto-fresh` are not rewritten here; that
  is a data fix after merge.
- Tests outside the three named files that I ran because I touched their
  modules: `tests/test_cxo_claude_ps1.py`, `tests/test_rename_service.py`,
  `tests/test_restart_run.py`, `scripts/test_session_rename.py`,
  `tests/test_projecttrack_p1.py`, `tests/test_usage_budget_p4a.py` (539 passed,
  1 skipped). I did not run the full suite.
- `tests/test_projecttrack_p1.py` is not in the task's touch list; one line changed
  (`"project": "p"` to `"P"`) because a new spawn row must now be PascalCase.
