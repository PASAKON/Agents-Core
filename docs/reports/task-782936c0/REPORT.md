# task-782936c0 -- Org Mesh W3.3: node_dispatch on Windows, letters to a worker

Branch `agent/developer-task-782936c0`. Design: `docs/design/org-mesh.md`.
Build and unit test only. Nothing here ran on the real winbox (that is W3.4).

## What changed

### Part A -- `tools/node_dispatch.py` on `sys.platform == 'win32'`

| Verb | On Windows now |
|---|---|
| `spawn_worker` | Runs `windows/spawn-worker.ps1` in place from the checkout (`-AgentsRoot <checkout>`). That script already registers the one-shot Interactive scheduled task (session 1) for the real launch, so nothing else starts `claude`. Output is read the way `delegate._spawn_remote` reads it: `in_progress` + pid, `blocked_host` (+ `taskkill` of a leaked pid), `conflict`, `failed`. |
| `start_clevel` | One-shot Interactive scheduled task for `windows/cxo-claude.ps1 -Role <r> -Session <sid> [--resume <full uuid>]`. Same result dict shape as `_start_clevel_tmux`, `via: "schtask"`. |
| `pid_alive` / `_pid_is_alive` | `lib.proc.pid_alive`. No `os.kill(pid, 0)` is left in the file (a test scans the AST for it). |
| `deliver_letter` | C-level: writes the inbox like `lib.mailbox.send`, `woke: false`, does not refuse for missing tmux. Worker: see Part B. |
| `probe` | `_ram_free_gb` (ctypes `GlobalMemoryStatusEx`), `_cpu_facts`, `_os_name` no longer crash on win32. |

Argument safety on the win32 path:

* Every subprocess call is an argv list. PowerShell receives its script as `-EncodedCommand` (base64 UTF-16LE), so no shell or command line re-parses it.
* Every value formatted into that script is held to its own allow-list first: `TASK_ID_RE`, role from `config.role`, runner in `(claude, codex, agy)`, `SESSION_ID_RE`, a resume target that must be a full UUID, and a per-parameter regex table for `spawn-worker.ps1` (`_SPAWN_PARAMS`). A value outside its pattern is a `Refusal` (exit 2) before any file is written or any subprocess runs.
* The task title (free text) is cut to `[A-Za-z0-9 ._-]` before it becomes part of the session name.

`windows/spawn-worker.ps1`: new optional `-AgentsRoot` (empty = the script's own folder, so the ssh deploy path is unchanged). `roles\`, `.launch-<task>\` and `launch-<task>.cmd` hang off it. The file is now ASCII only (the em dashes and section signs became `--` and `sec.`), and a new static test pins that.

### Part B -- letters to a worker

* `_write_letter` has a worker branch. `to_session` must match `TASK_ID_RE`, and the task row must carry this `to_role` and this host.
  * POSIX: `mailbox.send(role, task_id, ...)` plus `agent_transport.attempt_wake(task['tmux_session'], ...)`. Refused when that tmux session is not live or its name is unsafe. A failed wake never fails delivery.
  * win32: one line appended to `<worktree>\MAILBOX.md` (same format `send_to_worker._send_remote` writes) with a read-back check. The worktree must sit under the worktrees root.
* `tools/send_to_worker.py`: with `mesh.enabled()` and `task['host'] != self_host()`, the message becomes `db.create_letter(task['host'], task['role'], message, to_session=tid, from_host=self_host(), ...)` plus `send_to_cxo.dispatch_letter(id)`. A letter that cannot be delivered now is queued (the W2.4 watchdog retries it) and `send()` does not raise. Flag off is byte-for-byte today's behaviour, pinned by a test that makes every `lib.mesh` entry point explode.

## Verification

* `tests/test_w33_node_dispatch_windows.py` -- 476 tests. Platform faked at `node_dispatch._is_windows`; `subprocess.run` is a recorder and `Popen`, `os.kill`, tmux and `delegate_task` explode if reached.
  * `spawn_worker`: row written, brief file present while PowerShell runs and gone after, codex runner + runner model, title sanitised, dead route (`blocked_host` + `taskkill` argv), `SPAWN_REFUSED`, launcher failure, powershell missing, wrong status/host, 12 hostile task rows, the script builder against 9 hostile values in each of its 16 parameters, a non-Windows run still goes through `delegate_task`.
  * `start_clevel` fresh and resume, `pid_alive`, `deliver_letter` (C-level and worker, POSIX and win32), `probe`.
  * The hostile-argument matrix (`;`, `&`, backtick, `$(`, `$(id)`, newline, `"`, `'`, and combinations) is run against every verb and asserts exit 2 with zero subprocess calls.
  * `send_to_worker`: flag on (one letter + one verb), queued and refused paths, same-host never touches the mesh, flag off takes the ssh path with every `lib.mesh` entry point exploding, and an end-to-end letter to `MAILBOX.md` on win32.
* `tests/test_w33_spawn_worker_ps1.py` -- 6 static tests on the launcher (ASCII only, `-AgentsRoot` optional and the only path root, still an Interactive one-shot task, braces balance). This box has no PowerShell; none of the `.ps1` text was executed.
* Full suite, once, sequentially: `.venv/bin/python -m pytest -p no:warnings` -> **4564 passed, 28 skipped, 0 failed** (357 s).
* `scripts/test_mcp_role_config.py` -> 7 passed.
* `scripts/test_org_tools_registry.py` -> 23 passed, 12 failed, 1 error. Not caused by this change: the file is in `pytest.ini`'s `--ignore` list, the 12 failures are `RuntimeError: tests must not touch a real checkout's tasks.db (ADR 0021)` from `lib/db.py:375` (this diff does not touch `lib/db.py` or that test), and the 1 error is `fixture 'tid' not found` on `test_get_task_equivalence`. I did not set anything to get past the guard, because that would open the real tasks.db.
* Invisible-character scan (Cf/Zl/Zp/Co/Cn, and Cc other than newline and tab) over every changed and new file: 0 found. gitleaks pre-commit: no leaks.

## Decisions to check

1. **`tools/delegate.py` was not edited.** `self_repo_guard` refused the edit (not in this task's declared touches) and I did not work around it. `spawn_worker` on win32 therefore lives in `node_dispatch.py` and imports `delegate`'s helpers read-only (`_validate_runner`, `_ssh_remote_url`, `_render_remote_runner_args`, `_runner_branch_name`), so the branch, argument and URL rules have one copy. What it does NOT repeat is `delegate_task`'s gating (dependencies, path locks, browser cap, disk floor). The hub already runs that before it sends the verb; on Windows the verb no longer re-runs it against the spoke's own DB copy. If you would rather have the spawn inside `delegate._spawn_remote(local=True)`, that needs `tools/delegate.py`, `tests/test_w03b_local_launcher.py` (pins `NotImplementedError` for windows local) and a `.gitignore` line added to the touches.
2. **`launch-*.cmd` is not in `.gitignore`.** `spawn-worker.ps1 -AgentsRoot <checkout>` writes `launch-<task>.cmd` into the checkout root. `.launch-*/` is ignored, the `.cmd` is not, so a running worker leaves an untracked file in the checkout. `.gitignore` is not in the touches; one line (`launch-*.cmd`) fixes it.
3. **`tests/test_w24_letters.py` was edited (undeclared).** W2.4 pinned "`send_to_worker` is not changed by the flag" with a `NotImplementedError` test. Part B reverses that on purpose, so the pin became `test_send_to_worker_flag_on_is_a_letter_since_w33`. Two obsolete Windows-refusal tests in `tests/test_node_dispatch.py` were replaced by pointer comments for the same reason.
4. **W2.4 is merged into this branch** (`2cff8fad`, `25d9884e`) because Part B needs `letters.from_host` and `send_to_cxo.dispatch_letter`. Merge W2.4 first; this branch then adds only its own commits.
5. **`start_clevel` uses `-Session <sid>`.** `cxo-claude.ps1` has no other way to take an id. That is its ephemeral shape: no `<role>-active` pointer, so a letter to such a session must name `to_session`; a role-only letter finds nothing.
6. **C-level letter liveness on win32 reads the launcher's lock file** (`state\locks\<role>-<sid>.lock`, the pid of the PowerShell) through `lib.proc.pid_alive`. A missing, dead or garbled lock is a refusal ("no live session"), so a letter is not silently written into a box nobody reads. The brief only said not to refuse for missing tmux; this is my call.
7. **`--resume <full uuid>`, not `-r`**: PowerShell binds `-r` as an abbreviation of `-Role` / `-RemainingArgs`. `cxo-claude.ps1` adds `--fork-session` itself.
8. **`spawn_worker` passes the computed branch to `_build_prompt`** (`{**task, "branch": branch}`); `delegate._spawn_remote` passes the row as it is, where `branch` can still be empty before the spawn.
9. **`tests/test_w33_spawn_worker_ps1.py` is not named `test_spawn_worker_ps1.py`** on purpose: that basename already exists in `scripts/` and collides at collection when both are in one run.
10. `docs/ops/node-dispatch.md` said `pid_alive` / `start_clevel` are refused on Windows until W3. Corrected.

## Not verified (W3.4 on the real winbox)

* That unregistering a Running one-shot task keeps its process alive (assumed from what `spawn-worker.ps1` already does for codex/agy).
* That `cxo-claude.ps1` behaves in a console launched by a scheduled task (it is not `wt.exe` there).
* The `powershell.exe -EncodedCommand ... ; exit $LASTEXITCODE` exit-code hand-off, and the 300 s timeout on a cold clone.
* No env scrubbing on the win32 local launch (the POSIX launcher has one; the sshd session env is what the ssh path gets today).

## Commits (this task, after the W2.4 merge)

* `0be34ef8` node_dispatch: win32 start_clevel via schtask, pid_alive via lib.proc, probe ram, worker + windows letters
* `d0b820e1` send_to_worker: a worker on another host gets a letter when the mesh flag is on
* `21f0307c` node_dispatch: win32 spawn_worker runs windows/spawn-worker.ps1 in place, values allow-listed before PowerShell
* the report + docs/ops/node-dispatch.md correction commit (last on the branch)
