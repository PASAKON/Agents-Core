# REPORT task-3bf2da7c

Three follow-ups on the mesh path from the W2.7 review and the W4.4/W3.5 probe work.
All three are done and committed. Item 2 (deliver_letter timeout) first stopped on `tools/agent_transport.py`, which this task had not declared (`hook-self-repo-guard`, ADR 0020); the CTO added the path (CTO-FEEDBACK.md) and item 2 landed in 0cfd302c.

Not touched, as instructed: `tools/hq_join.py`, `lib/db.py`, `lib/config.py`, and the `pick_runner` / `resolved_runner` region of `tools/delegate.py`. No ssh, no hub writes outside tests, nothing on winbox or Contabo.

## Item 1: `queued_remote` retry cap (done)

**Before.** `runners/watchdog.py:_retry_queued_remote` dialled every `queued_remote` row on every 300 s pass forever, so a host that never came back held its rows' path locks indefinitely.

**After.**
- `lib/mesh.py`: `MAX_ATTEMPTS = 12`, `ENV_MAX_ATTEMPTS = "ORG_MESH_MAX_ATTEMPTS"`, `max_attempts()`. A value that is not a whole number of 1 or more falls back to 12; a typo never turns the cap off.
- Why 12: the first attempt is at delegate time, so 12 attempts are 11 watchdog passes of 300 s, about 55 minutes of silence (longer when a dial hangs to its full 300 s verb timeout). That rides out a reboot, a Windows update restart or a tailnet re-key, and stops well short of the locks blocking other work for hours.
- `tools/delegate.py`: new `give_up_queued_remote(task_id, host_name, attempts)`. Moves the row to `failed` with a `delegate_log` naming host, attempt count and cap. It uses `db.update_status(..., "failed")`, which is the path every failed launcher run takes and which releases the locks (`RELEASING_STATUSES`); no new release path. Tells the owner once through `send_to_cto.send` (the existing owner-letter path) plus `error()`. A row that is no longer `queued_remote` is returned untouched and not announced, so a repeat call cannot notify twice. A mailbox error is warned and does not undo the failure.
- `runners/watchdog.py`: the cap is checked before the `silent_hosts` skip and before any dial, so a capped row behind a silent host is still failed, and giving up does not make that host silent. One bad row does not stop the others.
- **Count per task, not over a window.** `db.recent_events(limit=500, task_id=...)` does filter by task in SQL, so a busy ledger of *other* tasks never undercounted. It still took only the newest 500 events of the *same* task, so a row that logged many other events could push old `status_queued_remote` events out of view and never reach the cap. `_queued_remote_attempts` is now `SELECT COUNT(*) ... WHERE task_id=? AND kind=?`. Pinned both ways (600 noise events from other tasks; 600 noise events on the same task).

**Tests** (`tests/test_mesh_followups.py`): 21 tests for this item. Run against `bacba144` code, all fail except the cross-task count, which already worked there and is kept as a regression pin.

## Item 3: `runner_claude` on macOS (done)

**Before.** `_PROVIDES_DETECTORS` only checked `~/.claude/.credentials.json`; macOS keeps the login in the Keychain, so a signed-in Mac reported no `runner_claude`.

**After** (`tools/node_dispatch.py`, `_claude_signed_in`):
- Linux and Windows: unchanged file check (`os.stat`, never opened).
- macOS, in order:
  1. `claude auth status --json`, bounded by `PROBE_CHILD_TIMEOUT_S`. Only the `loggedIn` boolean is used. Its output also carries an email and an org name; they are parsed in place and never stored, logged or returned.
  2. If the CLI cannot answer (not on PATH, hung, would not start, output not that JSON or no boolean `loggedIn`): `/usr/bin/security find-generic-password -s "Claude Code-credentials"`. **No `-w`, no `-g`.** Exit code is the whole answer; stdout, stderr and stdin are /dev/null.
  3. With `CLAUDE_CONFIG_DIR` set and the CLI unable to answer, the file check is used, because the default Keychain item may belong to a different login. I did not measure how Claude Code names that item for a custom dir, so the doc says "may" rather than asserting a hashed suffix.
- Probe worst case on macOS: 5 children, 25 s (was 3 children, 15 s). `docs/ops/node-dispatch.md` updated.
- Measured on this Mac (read-only, booleans only): `loggedIn` true; `runner_claude` now in `provides_measured`; the old file check returns false here; the whole detector takes about 1.5 s.

**Tests** (`tests/test_mesh_followups.py`): 24 tests. Against the original `node_dispatch.py` 23 of 24 fail; the one that passes is the source pin (no `-w`/`-g` string constant), which holds on both. They fail the suite if: any child argv carries a `-w`/`-g`-style flag (regex `-[A-Za-z]*[wg][A-Za-z]*`); the `security` child does not have stdout/stderr/stdin on DEVNULL or drops the timeout; the secret, email or org name reaches the probe answer; a detector function opens or reads a file in the darwin path (AST pin); or a hung `security` does not show as `runner_claude: TimeoutExpired`.

**Existing test changed.** `tests/test_w44_probe_provides.py::test_macos_without_nvidia_smi_reports_no_gpu_and_no_metal` asserted `box.children.calls == []` on faked macOS. A faked macOS now plans one child, `/usr/bin/security` (there is no `claude` on the fake PATH). The test now scripts that child's answer and asserts it is the only child. This file was not in the declared touches; the guard let the edit through. Flagging it so you can confirm.

## Item 2: `deliver_letter` timeout (done, commit 0cfd302c)

**Problem.** `lib/mesh.VERB_TIMEOUT_S` had no `deliver_letter`, so it got `DEFAULT_TIMEOUT_S = 30`. The Windows wake (`_windows_wake` -> `agent_transport.wake_windows_tab`) runs `schtasks /run` (was a literal `timeout=15`) and then waits up to `_WAKE_WAIT_S = 15.0`: 30 s worst case, plus the ssh dial and the letter write. A slow wake for a letter already on disk would time out and read as `MeshUnreachable`.

**Fix.**
- `tools/agent_transport.py`: adds `_WAKE_RUN_TIMEOUT_S = 15` and `WAKE_WORST_CASE_S = _WAKE_RUN_TIMEOUT_S + _WAKE_WAIT_S`, and `wake_windows_tab` passes `_WAKE_RUN_TIMEOUT_S` where it had the literal 15. The CTO asked for the constant only; this one substitution is the same value (15), so wake behaviour is unchanged, and it is what keeps the worst case and the real `schtasks` timeout from drifting apart. One of the tests observes the real `schtasks` timeout through a fake `run` to pin that.
- `lib/mesh.py`: `VERB_TIMEOUT_S["deliver_letter"] = CONNECT_TIMEOUT_S + round(WAKE_WORST_CASE_S) + LETTER_WRITE_MARGIN_S` = 10 + 30 + 15 = 55 s, with `WAKE_WORST_CASE_S` imported, not copied.
- `agent_transport` imports only `lib.notify`, `lib.config`, `tools.session_name`, `tools.tmux_session`; none import `lib.mesh`, so no cycle. `import lib.mesh` measured at 0.05 s.
- `docs/ops/node-dispatch.md`: one paragraph on the timeout, in the client-side section.

**Tests** (`tests/test_mesh_followups.py`, 5). They were red on the branch before this commit (`KeyError: 'deliver_letter'`, full suite 5 failed), which is the "fails on current main" proof, and are green after:
- `test_deliver_letter_has_its_own_timeout`
- `test_deliver_letter_outlasts_the_windows_wake_plus_the_write`
- `test_the_wake_worst_case_is_built_from_the_numbers_the_wake_really_uses`
- `test_mesh_dispatch_gives_deliver_letter_that_timeout`
- `test_a_slow_wake_inside_the_timeout_is_a_reply_not_an_unreachable_host`

## Test runs

- Full suite, run once after item 2, in the worktree: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` = **4959 passed, 0 failed, 28 skipped** in 510 s. (The earlier run, before item 2 landed: 4954 passed, 5 failed, 28 skipped; the 5 were the item-2 tests.)
- `scripts/test_mcp_role_config.py` (pytest) = 7 passed.
- `scripts/test_org_tools_registry.py` is in the 4959 (`pytest.ini` has `testpaths = scripts lib tests`) and passes inside the full run. Run **alone** under pytest it fails 12 + 1 error with `tests must not touch a real checkout's tasks.db (ADR 0021)`, identically on an extracted `bacba144` and on this branch, so it is order-dependent and not from this change: the file points `db.DB_PATH` at a temp file only in its own `main()`. Run as a script (`python scripts/test_org_tools_registry.py`, how it is written to run): ALL PASS, 0 FAIL.
- Invisible-character scan (Python, Cf/Cc/odd-space categories) over every changed and new file: 0.

## Status

| item | state |
|---|---|
| 1 retry cap | done, committed |
| 2 deliver_letter timeout | done, committed |
| 3 runner_claude macOS | done, committed |
