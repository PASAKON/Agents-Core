# REPORT task-0f8396b6

## Summary

Added unit tests for `tools/resume_worker.py` in `tests/test_resume_worker.py` covering soft vs. hard resume paths, exact `subprocess.run` (`osascript`) argv and embedded shell command construction, unknown task IDs and task status handling, owner window ID pass-through and missing-owner fallback behaviour, and `main()` CLI output/return codes for valid and invalid inputs. All external boundaries (`subprocess.run`, `lib.db`, and `tools.delegate._owner_window_id`) are mocked via an `autouse` fixture so no test opens an iTerm tab or touches the SQLite/Postgres hub.

## Files Changed

- `tests/test_resume_worker.py` (new): 10 unit tests (`16` test cases including parametrized status cases) for `tools/resume_worker.py`.
- `docs/reports/task-0f8396b6/REPORT.md` / `REPORT.md`: task report, seeded reverts per test, and bugs found in `tools/resume_worker.py`.

## Seeded Reverts (One-Line Changes in `tools/resume_worker.py` Caught by Each Test)

| Test in `tests/test_resume_worker.py` | Line in `tools/resume_worker.py` | Original Line | One-Line Seeded Revert | Why the Test Goes Red |
|---|---|---|---|---|
| `test_soft_resume_when_session_id_present` | Line 98 | `    mode = "soft" if task.get("session_id") else "hard"` | `    mode = "hard"` | `resume("task-soft01")` returns `"... (mode=hard)"` instead of `"OK: resume tab opened for task-soft01 (mode=soft)"`. |
| `test_hard_resume_when_session_id_missing_or_empty` | Line 98 | `    mode = "soft" if task.get("session_id") else "hard"` | `    mode = "soft"` | `resume("task-hard02")` returns `"... (mode=soft)"` instead of `"OK: resume tab opened for task-hard02 (mode=hard)"`. |
| `test_spawn_resume_tab_exact_argv_and_runner_command` | Line 32 | `        f"python -m runners.worker_resume {role} {task_id}"` | `        f"python -m runners.worker_init {role} {task_id}"` | The shell command embedded in the `osascript` argv no longer matches `python -m runners.worker_resume developer task-argv03` (or changing line 84 `["osascript", "-e", script]` to `["osascript", script]` breaks the exact argv assertion). |
| `test_unknown_task_id_returns_error_without_spawning` | Line 91 | `        return f"ERROR: task {task_id} not found"` | `        return f"ERROR: {task_id} missing"` | Returned string for an unknown task no longer matches `"ERROR: task task-unknown99 not found"`. |
| `test_done_status_returns_error_without_spawning` | Line 92 | `    if task["status"] == "done":` | `    if False:` | `resume("task-done01")` fails to short-circuit on `status == "done"`, calls `_spawn_resume_tab` / `subprocess.run`, and returns `"OK: ..."` instead of `"ERROR: task task-done01 already done; nothing to resume"`. |
| `test_other_statuses_are_resumed_by_current_code` | Line 88 | `    db.init()` | `    pass` | `mock_env.db_init.assert_called_once_with()` fails (or changing line 92 `if task["status"] == "done":` to `if task["status"] != "rate_limited":` causes the other parametrized statuses to return `"ERROR: ..."` instead of `"OK: ..."`). |
| `test_owner_window_id_passed_through_and_embedded_in_applescript` | Line 39 | `    owner_winid = _owner_window_id(owner_cto, owner_role)` | `    owner_winid = None` | `_owner_window_id` is not called with `("cfo01234", "cfo")` and the AppleScript embeds `first window whose id is (0)` instead of `(4821)`. |
| `test_missing_owner_handled_with_cto_default_and_fallback_script` | Line 96 | `    owner_role = task.get("owner_role") or "cto"` | `    owner_role = task.get("owner_role")` | `_owner_window_id` is called with `(None, None)` instead of `(None, "cto")`. |
| `test_cli_main_missing_arg_prints_usage_to_stderr_and_returns_1` | Line 105 | `        return 1` | `        return 0` | `main()` returns `0` instead of `1` when invoked without `<task_id>`. |
| `test_cli_main_with_task_id_prints_result_and_returns_0_for_good_and_bad_task` | Line 106 | `    print(resume(sys.argv[1]))` | `    resume(sys.argv[1])` | `main()` prints nothing to `stdout` instead of the `resume()` status line. |

## Real Bugs Found in `tools/resume_worker.py` (Not Modified per Brief)

1. **Non-resumable statuses other than `"done"` are not rejected (`tools/resume_worker.py:92-93`)**:
   - `resume()` only checks `if task["status"] == "done":`. Tasks in `"cancelled"`, `"review"` (report already submitted and awaiting merge), `"pending"` (never started), or `"in_progress"` (potentially still running with a live PID) are not guarded and will unconditionally spawn a duplicate resume tab.
2. **`main()` exits `0` and writes to `stdout` on `ERROR:` results (`tools/resume_worker.py:106-107`)**:
   - When `resume(task_id)` returns `"ERROR: task <id> not found"` or `"ERROR: task <id> already done; nothing to resume"`, `main()` prints the error to `stdout` (not `stderr`) and returns exit code `0`, masking failures from shell callers.
3. **`owner_cto` is ignored in the AppleScript tab-title fallback (`tools/resume_worker.py:48-64`)**:
   - Unlike `tools/delegate.py:_build_spawn_applescript` (which first matches `"{display} Chat #{owner_cto}"` / `"{display} #{owner_cto}"` before falling back to any `"{display} Chat #"` / `"{display} #"`), `_spawn_resume_tab` never interpolates `owner_cto` into the AppleScript. If the `.winid` file is absent or stale and multiple sessions of the same C-level role (e.g., two CTO windows) are open, the resumed worker tab can attach to the wrong C-level window.
4. **AppleScript fallback only checks `name of current session of t` and misses persona tab titles (`tools/resume_worker.py:52-56`)**:
   - It does not check `name of t` (sticky tab title) to guard against iTerm session-name flicker, and it only checks `"{owner_display} Chat #"` / `"{owner_display} #"`, which fails to match persona-formatted C-level titles such as `"CTO (Kavin) #<id>"` or `"CMO (Ging) #<id>"`.
5. **Missing `; exit $?`, `WORKER_CTO_ID`/`WORK_DIR` exports, Ctrl-U prompt clear, and focus restoration (`tools/resume_worker.py:29-33, 66-82`)**:
   - Unlike `tools/delegate.py:_spawn_iterm_tab`, the shell command in `_spawn_resume_tab` does not end with `; exit $?` (leaving a zombie idle shell tab if `runners.worker_resume` exits early with code 2 or 4), does not export `WORKER_CTO_ID` or `WORK_DIR`, does not send `ASCII character 21` (Ctrl-U) before `write text`, and does not restore `frontApp` / `priorWin` / `priorTab` (stealing focus when opening a tab).
6. **Docstring vs. module responsibility mismatch (`tools/resume_worker.py:1-4, 29-33, 98`)**:
   - The module docstring says `tools/resume_worker.py` *"Soft-resumes via `claude --resume <session_id>` if the hook captured a session id, otherwise hard-resumes through runners.worker_init"*, whereas `tools/resume_worker.py` always runs `python -m runners.worker_resume {role} {task_id}` via `osascript` and only uses `task.get("session_id")` to format `(mode=soft)` vs. `(mode=hard)` in its return string (the actual `claude --resume` vs. `runners.worker_init` exec branching lives in `runners/worker_resume.py`).

## Validation Performed & Limitations

- **Limitation (No shell / headless AGY contract)**: Per the AGY Remote Worker Contract (*"For AGY, use file tools only; leave shell validation to the review process"*) and headless run rules (*"Any tool call that needs approval is auto-denied, and ONE denial ends your whole run with nothing saved"* / *"You may not have a shell: if you cannot run pytest, say so"*), `pytest` was not executed in a shell during this session.
- **Validation command for review**:
  ```
  /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_resume_worker.py
  ```
- **Static verification**: Verified imports, fixtures, mock targets (`subprocess.run`, `lib.db.init`, `lib.db.get_task`, `lib.db.get_conn`, `tools.delegate._owner_window_id`, `tools.resume_worker._owner_window_id`), and exact line-by-line correspondence with `tools/resume_worker.py` and `policies/agents.yaml`.

## Blockers

- (none)

## Skill learning

- (none)
