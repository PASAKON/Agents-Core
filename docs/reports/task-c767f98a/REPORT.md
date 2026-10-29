# REPORT task-c767f98a

## What changed
- `runners/watchdog.py:1373-1381`: Added `REPO_ROOT = Path(__file__).resolve().parent.parent` and `_GIT_BUSY_NAMES` (`index.lock`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `rebase-merge`, `rebase-apply`).
- `runners/watchdog.py:1384-1394`: Added `_code_rev(root: Path = REPO_ROOT) -> str | None` reading `HEAD` via `subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], timeout=10, capture_output=True, text=True)` and returning `None` on missing `git`, timeout, non-zero exit (including dubious ownership), or empty output.
- `runners/watchdog.py:1397-1416`: Added `_git_busy(root: Path = REPO_ROOT) -> bool` resolving `<root>/.git` as either a directory or a linked-worktree file (`gitdir:` line) and returning `True` while any entry in `_GIT_BUSY_NAMES` exists.
- `runners/watchdog.py:1449-1464`: In `main()` (loop mode only, right after the `info("watchdog loop started ...")` line), checks `WATCHDOG_RELOAD_ON_CODE_CHANGE != "0"`, records `start_rev = _code_rev()`, and prints `watchdog: code reload off (<reason>)` via `print()` when reload is disabled or `start_rev` is `None`. At the top of every loop iteration after the first (after `time.sleep(args.interval)`, before `scan_once()`), when `start_rev is not None` and `not _git_busy()`, compares `_code_rev()` to `start_rev`; if changed, prints `watchdog: code changed <old12>..<new12>; exiting for a restart` via `print()` and returns `0`.
- `tests/test_watchdog_code_reload.py:1-200`: Added unit and `tmp_path` git repository tests covering cases a–g.

## Start path check (`main()` up to the loop)
- `runners/watchdog.py:1419-1448`: Before entering the `while True:` loop, `main()` sets `os.environ["CTO_SESSION_ID"] = "watchdog"` (if neither `CTO_SESSION_ID` nor `CXO_ROLE` is set), parses CLI arguments, runs `db.init()`, and calls `info("watchdog loop started — ...")`.
- `info()` in `lib/notify.py:124` calls `notify("info", msg)` with `mac=False` (default), which prints to `sys.stderr` and only writes to `state/logs/cto.log` when `CTO_SESSION=1` or `WORKER_TASK_ID` is set (`lib/notify.py:34-42`). It does not send a letter, ping, email, or macOS desktop notification (`osascript` only runs when `mac=True`, i.e., `success()` or `error()`). Left unchanged per brief.

## Service manager restart on exit 0
- **Contabo systemd unit** (`deploy/systemd/mooniex-watchdog.service:24-25`):
  ```ini
  Restart=always
  RestartSec=10
  ```
  `Restart=always` restarts the unit on any exit status, including clean exit code `0`, after 10 seconds.
- **macOS launchd plist** (`scripts/com.mooniex.agents-watchdog.plist:35-36`):
  ```xml
    <key>KeepAlive</key>
    <true/>
  ```
  Unconditional `<key>KeepAlive</key><true/>` respawns the daemon whenever it exits, including exit code `0`.

## Tests (`tests/test_watchdog_code_reload.py`)
- **a. `test_a_head_changes_after_first_scan_exits_zero` (`tests/test_watchdog_code_reload.py:104-109`)**: Proves that when `HEAD` moves from `REV_A` to `REV_B` after the first scan, `main()` prints `watchdog: code changed aaaaaaaaaaaa..bbbbbbbbbbbb; exiting for a restart` and returns `0` after exactly 1 `scan_once()` call.
- **b. `test_b_head_unchanged_still_looping_after_five_scans` (`tests/test_watchdog_code_reload.py:112-117`)**: Proves that when `_code_rev` continues returning `REV_A`, `main()` does not exit early, checks `_code_rev` on each subsequent loop iteration, and is still looping after 5 scans (terminated only by the `time.sleep` test sentinel `_LoopStop`).
- **c. `test_c_code_rev_none_at_start_never_exits` (`tests/test_watchdog_code_reload.py:120-126`)**: Proves that when `_code_rev()` returns `None` at startup, `main()` prints `watchdog: code reload off (...)` and keeps looping without exiting even when later `_code_rev` calls would return `REV_B`.
- **d. `test_d_git_busy_defers_exit_until_clear` (`tests/test_watchdog_code_reload.py:129-135`)**: Proves that when `HEAD` has changed after scan 1 but `_git_busy()` is `True` on iteration 2, `main()` skips the reload check for that iteration (running scan 2) and exits `0` on iteration 3 once `_git_busy()` returns `False`.
- **e. `test_e_env_opt_out_disables_reload` (`tests/test_watchdog_code_reload.py:138-144`)**: Proves that setting `WATCHDOG_RELOAD_ON_CODE_CHANGE=0` prints `watchdog: code reload off (WATCHDOG_RELOAD_ON_CODE_CHANGE=0)` and prevents `main()` from exiting when `HEAD` moves.
- **f. `test_f_oneshot_mode_never_calls_code_rev` (`tests/test_watchdog_code_reload.py:147-152`)**: Proves that running `main()` without `--loop` (`sys.argv = ["watchdog"]`) runs one scan, returns `0`, and never calls `_code_rev`.
- **g. `test_g_code_rev_and_git_busy_on_tmp_repo` (`tests/test_watchdog_code_reload.py:164-200`)**: Proves against a real temporary git repo in `tmp_path` that `_code_rev` reads the initial commit SHA, returns a different SHA after a second commit, returns `None` outside a repo, and that `_git_busy` flips to `True` when `.git/index.lock` exists (both for a standard `.git/` directory and a linked-worktree `.git` file) and back to `False` once removed.

## Validation performed
- File-only edits performed per AGY worker contract ("Edit files only. Do not run any command: the CTO reviewer runs the tests"). Static inspection of `runners/watchdog.py` and `tests/test_watchdog_code_reload.py` completed.

## Not checked / risk
- Quoted `deploy/systemd/mooniex-watchdog.service:24-25` (`Restart=always`, `RestartSec=10`) and `scripts/com.mooniex.agents-watchdog.plist:35-36` (`<key>KeepAlive</key>` / `<true/>`), but could not inspect live `systemctl` state on Contabo or `launchctl` state on the Mac to confirm the installed daemon definitions match the checked-in files.
- Did not execute `pytest tests/test_watchdog_code_reload.py` in a shell because the task instructions and AGY contract forbid running commands; test execution is deferred to the CTO reviewer.
- In-memory module globals in `runners/watchdog.py` (`_mesh_probe_skip_noted`, `_provision_retry_at`, `_unapproved_noted_until`) reset when the process restarts after a merge (`_mesh_probe_state` itself is persisted in `state/watchdog-mesh-probe.json`).

## Blockers
- (none)

## Skill learning
- (none)
