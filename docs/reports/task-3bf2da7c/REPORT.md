# REPORT task-3bf2da7c

Three follow-ups on the mesh path from the W2.7 review and the W4.4/W3.5 probe work.
Item 1 (queued_remote retry cap) and item 3 (runner_claude on macOS) are done and committed.
Item 2 (deliver_letter timeout) is written, tested and proven in a scratch copy, but **not applied to this branch**: it needs one edit in `tools/agent_transport.py`, a path this task did not declare, and `hook-self-repo-guard` refused it (ADR 0020). The exact patch is at the end of this file.

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

## Item 2: `deliver_letter` timeout (written, NOT applied)

**Problem.** `lib/mesh.VERB_TIMEOUT_S` has no `deliver_letter`, so it gets `DEFAULT_TIMEOUT_S = 30`. The Windows wake (`_windows_wake` -> `agent_transport.wake_windows_tab`) runs `schtasks /run` (literal `timeout=15`) and then waits up to `_WAKE_WAIT_S = 15.0`: 30 s worst case, plus the ssh dial and the letter write. A slow wake for a letter already on disk would time out and read as `MeshUnreachable`.

**Fix.** The 15 s for `schtasks` is a literal inside `wake_windows_tab`, so the wake's worst case cannot be derived by import until that file exposes it. Needs, in `tools/agent_transport.py`:

```diff
--- a/tools/agent_transport.py
+++ b/tools/agent_transport.py
@@ -176,6 +176,10 @@
 WAKE_TASK_NAME = "MooniexOrgWake"
 WAKE_DIR = ROOT / "state" / "wake"
 _WAKE_WAIT_S = 15.0
+_WAKE_RUN_TIMEOUT_S = 15  # the `schtasks /run` call
+# The longest wake_windows_tab can block: the schtasks call, then the wait for
+# the result. lib/mesh.py sizes the deliver_letter timeout from it.
+WAKE_WORST_CASE_S = _WAKE_RUN_TIMEOUT_S + _WAKE_WAIT_S
 _WAKE_LABEL_RE = re.compile(r"[A-Za-z0-9_.#-]{1,40}")
 _WAKE_SID_RE = re.compile(r"[A-Za-z0-9_-]{6,40}")
 
@@ -224,7 +228,7 @@
 
     try:
         r = run(["schtasks", "/run", "/tn", WAKE_TASK_NAME],
-                capture_output=True, text=True, timeout=15)
+                capture_output=True, text=True, timeout=_WAKE_RUN_TIMEOUT_S)
     except (OSError, subprocess.SubprocessError) as e:
         _withdraw()
         return {"woke": False, "why": f"schtasks /run failed: {e}"}
```

and in `lib/mesh.py` (already declared; `LETTER_WRITE_MARGIN_S = 15` is already in the branch):

```diff
 from lib import config
+from tools.agent_transport import WAKE_WORST_CASE_S
@@
     "kill_worker": 60,
+    # ssh dial, then the far side's wake (up to WAKE_WORST_CASE_S), then the write.
+    "deliver_letter": CONNECT_TIMEOUT_S + round(WAKE_WORST_CASE_S) + LETTER_WRITE_MARGIN_S,
 }
```

Value: 10 + 30 + 15 = 55 s. `agent_transport` imports only `lib.notify`, `lib.config`, `tools.session_name`, `tools.tmux_session`; none import `lib.mesh`, so no cycle; `import lib.mesh` measured at 0.05 s.

**Tests are already in the branch** (`tests/test_mesh_followups.py`, 5 tests) and **fail on this branch as it stands**, which is the "fail on current main" proof:
- `test_deliver_letter_has_its_own_timeout`
- `test_deliver_letter_outlasts_the_windows_wake_plus_the_write`
- `test_the_wake_worst_case_is_built_from_the_numbers_the_wake_really_uses` (observes the `schtasks` timeout through a fake `run`, so a future edit to either number breaks it)
- `test_mesh_dispatch_gives_deliver_letter_that_timeout`
- `test_a_slow_wake_inside_the_timeout_is_a_reply_not_an_unreachable_host`

**Proof the fix works.** In a scratch copy of `HEAD` outside the repo with the two diffs above applied: `tests/test_mesh_followups.py tests/test_w44_probe_provides.py tests/test_w27_security.py` = 197 passed, 0 failed.

**To finish:** add `tools/agent_transport.py` to the task's touches and re-run me, or apply the two diffs above. `docs/ops/node-dispatch.md` should also gain one sentence on the `deliver_letter` timeout in the "Client side" section; I held that back so the doc does not describe code that is not in the branch.

## Test runs

- Full suite once, in the worktree: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` = **4954 passed, 5 failed, 28 skipped** in 546 s. The 5 failures are exactly the 5 item-2 tests above; nothing else is red.
- `scripts/test_mcp_role_config.py` (pytest) = 7 passed.
- `scripts/test_org_tools_registry.py` is in the 4954 (`pytest.ini` has `testpaths = scripts lib tests`) and passes inside the full run. Run **alone** under pytest it fails 12 + 1 error with `tests must not touch a real checkout's tasks.db (ADR 0021)`, identically on an extracted `bacba144` and on this branch, so it is order-dependent and not from this change: the file points `db.DB_PATH` at a temp file only in its own `main()`. Run as a script (`python scripts/test_org_tools_registry.py`, how it is written to run): ALL PASS, 0 FAIL.
- Invisible-character scan (Python, Cf/Cc/odd-space categories) over every changed and new file: 0.

## Status

| item | state |
|---|---|
| 1 retry cap | done, committed |
| 2 deliver_letter timeout | blocked on touches; 5 tests red in the branch until the patch above lands |
| 3 runner_claude macOS | done, committed |
