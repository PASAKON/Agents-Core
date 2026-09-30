# task-10136806: host router (W2.6 / PLAN-auto-dispatch H2)

Branch `agent/developer-task-10136806`, based on origin/main a4e999fd. Not pushed.

**Status: code done, verification incomplete.** Two things are open and both need the CTO: (1) my own test file was not hermetic and left 7 worktrees and 7 branches behind (details under Blockers); (2) the fix for that is committed but not re-run, because the auto-mode classifier denied every further pytest run and the cleanup.

## Files changed

- `lib/router.py` (new) — `pick_host(task, *, hosts_rows=None, now=None) -> HostPick`, `enabled()`, `parse_needs()`, `add_needs_line()`, `manual_line()`, `role_runners()`.
- `tools/delegate.py` — host-resolution block (was one line, `resolved_host = host if host is not None else (task.get("host") or self_host())`), two small helpers `_route_host` and `_keep_host_line`, one import, and 2 lines after the `_route_runner` call. `_route_runner`, `pick_runner`, `check_override` and `tools/route.py` are untouched.
- `runners/cto_mcp_server.py` — `create_task` gains an optional `needs: str = ""` that appends a `needs: a, b` line to the description (see Blockers for why it lives here and not in the registry).
- `tests/test_w26_pick_host.py` (new) — 78 tests (77 verified green at 72903d58; the hermetic-fixture fix adds one test and is not re-run).
- `docs/reports/task-10136806/REPORT.md` — this file.

## What was done

**Flag.** `ORG_HOST_ROUTER` (1/true/on), default OFF, same shape as `lib.mesh.enabled`. With it off, `delegate_task` runs the original line unchanged in an `else:` branch: explicit arg > `tasks.host` > `self_host()`. No `delegate_log` write, `pick_host` never called (a test asserts this with a `pick_host` that raises).

**Flag on.**
- Explicit `host=` or non-NULL `tasks.host` wins; `delegate_log` = `manual: <h> · host= argument` or `manual: <h> · tasks.host`.
- Otherwise `pick_host` runs (in `asyncio.to_thread`, because route can trigger a cold quota read).
- Hosts considered = `config/hosts.yaml` names plus any host only in the table (the latter is rejected: `not in config/hosts.yaml`).
- A host is rejected with exactly one reason, the first check it fails, in this order:
  1. probe: `no probe ≤60 s` (row missing or `probed_at` NULL); `(last one N s old)` when older than 60 s; `(probed_at unreadable)`; `(probed_at in the future)` beyond 10 s of skew. 60 s exactly is fresh. Also `status` offline / pending_identity / left. NULL status is accepted, because the probe never writes `status`.
  2. `provides lacks <names>` for the `needs:` line.
  3. `full r/max`; `running/max_workers unknown` if either is NULL.
  4. `no paths.<host> for <project>` (uses `config.project_path_for_host`, so `mac` falls back to `path:`); `unknown project <p>`.
  5. `no usable runner (role: a,b · host: c)`. The role's runners come from `route.plan(cls, touches=, brief=, host=None)`: the `p.choice.runner` of every plan with `verdict == "ok"`. It mirrors `_route_runner`'s skips: a hand-pinned runner, `model_hint` claude and `ORG_ROUTER=off` give that runner or claude; a role with no router class gives claude. Route is read only when at least one host got through checks 1-4.
- Survivors: lowest `load_per_core`, then `ram_free_gb` desc, then name. NULL load ranks last and NULL ram loses the tie; neither rejects.
- Success line: `host: <h> · load <x>/core · ram <y> GB · running <r>/<max> · rejected: <h2>(<why>) ...` (`rejected: none` when empty).
- No match: `delegate_task` writes `no_host: <h>(<why>) <h2>(<why>) ...` to `delegate_log`, returns the task row (status still pending, `tasks.host` still NULL) and does no spawn and no `_route_runner`. `pick_host` never raises: an unreadable table or a route error rejects every host with the error as the reason.
- `_route_runner` overwrites `delegate_log` with its own `router:` line, so `_keep_host_line` puts the host line back in front after it runs (two lines, `\n`-separated). The overwritten value also stays in the events table.
- The chosen host is what `_route_runner(task, role, resolved_host)`, the disk floor, the browser cap and `_spawn_remote` / the local spawn all receive.

**needs.** No column (lib/db.py is locked). Read from a description line `needs: a, b` (case-insensitive, line must start with `needs:`, several lines merge, names are lowercased and de-duplicated). Empty = no constraint. `create_task(needs="win_gui, chrome")` or a JSON array appends that line.

**Real ledger.** The `hosts` table on this Mac's sqlite ledger is empty (probe timers not installed). With the flag on, every host is therefore rejected with `no probe ≤60 s` and the task stays pending: `no_host: contabo(no probe ≤60 s) mac(no probe ≤60 s) winbox(no probe ≤60 s)`. There is no fallback, on purpose. I asserted this with an empty temp ledger (`test_flag_on_no_match_leaves_the_task_pending_and_never_spawns`); I did not read the real ledger, installed nothing, no ssh.

The brief says `get_hosts`; the function is `db.list_hosts()`, which is what `pick_host` uses.

## Tests (quoted)

Interpreter: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` (the worktree has no `.venv`). Both full runs below were at commit 72903d58 and were started at the same time (in parallel).

- `python -m pytest -p no:warnings`, `ORG_HOST` unset: `3950 passed, 27 skipped in 344.62s (0:05:44)`
- `ORG_HOST=mac python -m pytest -p no:warnings`: `2 failed, 3948 passed, 27 skipped in 342.38s (0:05:42)`
  - `tests/test_w26_pick_host.py::test_flag_off_is_todays_resolution_and_never_calls_pick_host[None-None-mac]` — mine. `tools.worktree.GitError: git config extensions.worktreeConfig true / error: could not lock config file .git/config: File exists`. Cause (proven from the traceback): that case resolves to this box, so `delegate_task` reached the real `create_worktree` (tools/delegate.py:2216). The two parallel runs collided on the repo's `.git/config` lock.
  - `scripts/test_hq_migrate_step4b.py::test_rollback_restores_dir_symlink_plists_and_yaml_byte_for_byte` — a `.venv/bin/python` path mismatch inside a pytest tmp dir (`scripts/test_hq_migrate_step4b.py:430`). Not touched by this task. It passed in the earlier `ORG_HOST=mac` full run at 07ffd5d6 (`3950 passed, 27 skipped in 318.45s`). Probably the same parallel-run collision, but I did not prove that.
- Earlier, before the load-ranking change (07ffd5d6): `ORG_HOST` unset `3950 passed, 27 skipped in 335.64s`.
- At 72903d58: `scripts/test_org_tools_registry.py` -> `ALL PASS`; `scripts/test_mcp_role_config.py` -> `OK — 0 failure(s)`; `scripts/test_tool_parity.py` -> `ALL PASS` (tool names only; it does not compare parameters).
- **Not run:** the hermetic-fixture fix (below) has not been executed. The auto-mode classifier denied `pytest tests/test_w26_pick_host.py` twice ("Interfere With Workloads"). I did not work around it. The `ORG_HOST=mac` full run has therefore not been re-done clean.

Before editing I grepped tests/ for pins on `resolved_host` / `self_host` defaults (130 hits in 16 files). All of them run with the flag off, so they exercise the untouched `else:` branch.

## Blockers

1. **My tests were not hermetic, and left artefacts.** The `flow` fixture faked `_route_runner`, `_spawn_remote` and the disk probes, but not `create_worktree` or `_spawn_local`. Every run of the "resolves to this box" case (flag off, no host) therefore cut a real worktree and branch and called the real `_spawn_local`. Found because of the parallel-run collision above. Left behind, all from my own runs:
   - 7 git worktrees under `/Users/gob/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-10136806/worktrees/mooniex-agents__developer__task-<id>` (this path is gitignored, inside my own worktree), for ids `139b2fec 391182e8 3d8e4fe4 58ba5860 5d256124 beef44d1 de40320e`. Each is clean and 0 commits ahead of main.
   - 7 branches in the shared repo, `agent/developer-task-<same ids>`. Rule 2 says I do not delete branches.
   - Checked afterwards: no process has its cwd in any of them, no tmux session and no `osascript` process exists for them. The spawn did not leave a live worker. I cannot rule out that an iTerm tab opened and closed.
   - I tried `git worktree remove` on the 7 directories (after counting them and confirming each was clean and unadvanced); the classifier denied it. Left in place for the CTO: `git worktree remove <path>` for each, then `git branch -d agent/developer-task-<id>` (fully merged into main, so `-d` works).
   - Fix, committed but not run: the `flow` fixture now fakes `create_worktree`, `_spawn_local` and `_warn_if_stale_code`, and records `local_spawns`. The flag-off case asserts the local spawn, and a new test `test_flag_on_pick_of_this_box_takes_the_local_spawn` covers a flag-on pick of this box.
   - Also from those runs: `git config extensions.worktreeConfig true` ran on the shared repo, which `create_worktree` does for every task anyway.
2. **`lib/org_tools_registry.py` is not in touches** and self_repo_guard refused the edit (sent to the CTO by `dev_message`, no answer). The registry's `_h_create_task` and `ToolSpec` own `create_task`'s real parameter list; `cto_mcp_server.py` is a stub over it, and the registry's `_prepare()` silently drops any kwarg not in `spec.params`. Forwarding `needs=` alone would have been a silent no-op, so the stub appends the line itself (`router.add_needs_line`). Consequences: `cto.py` / `cto_chat.py` (built from the registry) have no `needs`, and the MCP tool description text does not mention it. Registry patch if you add the path to touches: `_h_create_task(..., needs: str = "")` doing `description = router.add_needs_line(description, needs)`, `Param("needs", str, "")` in the `create_task` ToolSpec, and the stub forwards `needs=needs` instead of appending.

## Notes for the reviewer

- **All-candidates-will_hit case.** Per the brief I use only `verdict == "ok"` plans. `pick_runner` falls back to the first non-`cannot` plan when nothing is ok; `pick_host` does not. With the flag on and every bucket `will_hit` or `unknown` (for example quotas unreadable), every host is rejected `no usable runner (role: none ok ...)` and the task waits. That matches PLAN §3 ("stays pending with the reason") but is stricter than today's runner fallback. One-line change if you want `unknown` to count as usable.
- **Windows load.** The probe returns `load_per_core = NULL` on Windows. Rejecting on that would make winbox unpickable and `win_gui` tasks always `no_host`, so NULL load ranks last instead and the line prints `load ?/core`.
- **Probe vs config runners.** `pick_host` checks the probe's `hosts.runners`; `_route_runner` / `_validate_runner` afterwards use `config/hosts.yaml` `runners:`. If they disagree the later step decides.
- **delegate_log.** With the flag on, the resolution block overwrites `delegate_log` (like every other refusal does). A re-delegate of an already-running task therefore gets a `manual:`/`host:` line first, replaced by the duplicate-delegate refusal a few lines later.
- `role_runners` imports `tools.route` lazily: route imports `tools.delegate`, which imports `lib.router`.
- `ORG_HOST_ROUTER` is not switched on anywhere. Nothing installed. No `dev_message` progress pings; one blocked-state message (registry file).

## Skill learning

- MISSING [CXO_Protocol_DevSpawn §touches] : a brief that says "add a param to create_task in runners/cto_mcp_server.py" should also list `lib/org_tools_registry.py`; the stub is a thin wrapper and the registry silently drops unknown kwargs · evidence: task-10136806, `_prepare()` in lib/org_tools_registry.py, self_repo_guard block
- MISSING [no owner] : a test that drives `delegate_task` to a host equal to `self_host()` reaches the real `create_worktree` + `_spawn_local` and cuts a real worktree/branch in the shared repo. Fake both (see tests/test_w03b_local_launcher.py) · evidence: task-10136806, 7 stray worktrees + branches, `tools/delegate.py:2216` · prevented by: a fixture note in the tester/developer playbook
- MISSING [no owner] : the brief's `db.get_hosts` does not exist (`db.list_hosts` / `db.get_host` do) · evidence: task-10136806, lib/db.py · a brief should quote the function name from the code
- COSTLY [no owner] : the worktree has no `.venv`, so the brief's `.venv/bin/python -m pytest` cannot run there; the working interpreter is `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` · evidence: task-10136806 · prevented by: naming the interpreter in the brief
- COSTLY [no owner] : running the two required full suites (default and `ORG_HOST=mac`) in parallel let an unhermetic test collide on `.git/config`; ~11 min lost and one failure of unproven cause · evidence: task-10136806 · prevented by: run them one after the other
