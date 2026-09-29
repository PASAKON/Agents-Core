# REPORT task-26988fe3

## Summary
A Linux hub that delegates a codex or agy task to itself now runs `scripts/spawn-worker-remote.sh` with plain `bash` (no ssh, no copy into `.launch/`), and parses the launcher's output through the same code as the ssh path. Claude on a Linux hub, agy on the Mac, and a Linux hub delegating to another host are unchanged. New `tests/test_w03b_local_launcher.py`: 24 pass; the two full-suite runs, the two standalone scripts and every failure are itemised below.

## Files Changed
- `tools/delegate.py` — `delegate_task`: `local_launcher = resolved_host == this_host and resolved_runner != "claude" and sys.platform.startswith("linux")`; the host-routing `if` becomes `resolved_host != this_host or local_launcher` and passes `local=local_launcher`. `_spawn_remote` gets a `local: bool = False` keyword: local uses `ROOT/scripts/spawn-worker-remote.sh` (no `_ensure_remote_deploy_linux`), builds `["bash", script, *args]` instead of `["ssh", alias, "bash <script> ..."]`, and no longer requires an ssh alias. Same args, same stdin prompt, same SPAWN_REFUSED / SPAWNED parsing, same final `update_status` (host, runner, pid, tmux_session, worktree, branch). `--dry-run` prints `[dry-run] host=<h> local_cmd=bash <script> ...`; the ssh dry-run text (`ssh_cmd=`) is byte-identical. `local=True` on a non-linux host raises `NotImplementedError`. `_route_runner` and the router lines above `# Runner pre-flight` are untouched.
- `tests/test_w03b_local_launcher.py` (new, 24 tests) — see Tests.
- `docs/reports/task-26988fe3/REPORT.md` — this file.

## Commits
- 264703c5 — delegate: a Linux hub runs codex/agy on itself through the launcher over local bash (task-26988fe3)
- (report commit follows — `git log` on the branch)

## Tests
- ran: `tests/test_w03b_local_launcher.py` (with `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings`; the worktree has no `.venv` of its own)
  - passed: 24 · failed: 0 · skipped: 0
  - mutation check: with the routing condition reverted to `resolved_host != this_host`, 11 of the 24 fail (every local-transport test); restored, md5 identical.
- ran: `.venv/bin/python -m pytest -p no:warnings` (native env on Contabo, `ORG_HOST=contabo`)
  - **3286 passed, 6 failed, 27 skipped** in 459 s — the 6 are itemised below; none touches this change.
- ran: `ORG_HOST=mac .venv/bin/python -m pytest -p no:warnings`
  - **3287 passed, 5 failed, 27 skipped** in 423 s — the same five as the native run minus the timing-dependent sixth, which passed this time. No test is "Mac-pinned and fails only on Linux because of this change"; the five are the pre-existing Linux-environment failures in the table below.
- ran: `scripts/test_mcp_role_config.py` standalone → **`OK — 0 failure(s)`**, exit 0.
- ran: `scripts/test_org_tools_registry.py` standalone → **`ALL PASS`, exit 0, but only with the wiki roots exported** (`WIKI_ROOT_ORG=/opt/MoonieXHQ/Agents/Rules WIKI_ROOT_MOONIEX=/opt/MoonieXHQ/Agents/Wikis`). In this worker shell those are unset, so `wiki_list org:decisions` returns `ERROR: wiki 'org' not available in this environment` and the script prints `[FAIL] wiki_list matches (toon)` / `1 FAILURE(S)` (exit 1). Identical on the pre-change `delegate.py` (1bd7582b) and under `ORG_HOST=mac`; unrelated to this change.

### The failures — 6 in the native (ORG_HOST=contabo) run, the first 5 again in the ORG_HOST=mac run; all pre-existing on Linux
Checked by swapping in `git show 1bd7582b:tools/delegate.py`, running the same tests, then `git checkout -- tools/delegate.py` (md5 restored):
| test | with my change | on 1bd7582b |
|---|---|---|
| `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins` | fail | fail (installed_plugins.json on this box lacks `finance@…`, `cost-guardian@…`, `meigen@…`) |
| `tests/test_delegate_disk_floor.py::test_sufficient_disk_proceeds_to_spawn_step` | fail | fail |
| `tests/test_delegate_workdir.py::test_delegate_task_exports_work_dir_for_pilot_owner` | fail | fail |
| `tests/test_reopen_live_worker.py::test_reopen_on_dead_worker_spawns_as_before` | fail | fail |
| `tests/test_reopen_live_worker.py::test_live_pid_without_its_tmux_session_is_not_trusted` | fail | fail |
| `tests/test_delegate_workdir.py::test_delegate_task_gives_non_pilot_neither_folder_nor_env` | failed in the full run, **passed** in isolation and in its own file, on both versions | same — timing-dependent |

The four delegate tests and the flaky one call the real `_spawn_local`, which on Linux runs a real `tmux new-session` executing `scripts/spawn-worker.sh` (`tools/tmux_session.py:142` → "tmux session 'wd-…' was not alive after new-session — its command exited immediately"). The W0.3 suite figure (3268 passed, 0 failed) was taken off-Linux, where the same tests take the iTerm branch. Not fixed and not deleted, per the brief.

## Issues / Blockers
- none blocking.
- Brief conflicts, resolved as follows: (a) the task text says report at `docs/reports/<id>/REPORT.md`, "never a root REPORT.md"; the remote-worker contract says root `REPORT.md`, which is what `runners/branch_poller.py` reads (`read_remote_file(..., "REPORT.md")`). I followed the task text, so **the poller will not auto-flip this row to `review`** — the CTO needs to flip it by hand (same as task-6f6e5179). (b) The shared rules say never `git push`; the remote-worker contract says push your own task branch. I pushed only `agent/developer-task-26988fe3`.
- The task's `.venv/bin/python` does not exist in a worktree (no `.venv` there); I used the main checkout's interpreter from inside the worktree.

## Notes for Reviewer
- Design choice: `local` is an explicit keyword on `_spawn_remote`, decided by `delegate_task`, rather than `_spawn_remote` calling `self_host()` itself. That keeps every existing direct caller and `tests/test_spawn_remote_linux.py` (W0.6's, untouched) on the ssh path regardless of which box runs them.
- The local launcher inherits the hub process's environment; over ssh it gets a fresh sshd environment. The launcher writes its own `launch.sh` (ORG_HOST, PATH, finish command), and new tmux sessions take the tmux server's environment, so in practice a running tmux server (always the case on Contabo) shields the worker. If the hub ever starts the first tmux server itself, the codex/agy worker would inherit the hub's env (e.g. `ORG_DB_URL`, `CTO_SESSION_ID`). I did not add an env scrub (not in the brief, and it would differ from `_spawn_local`); say if you want one.
- Local runs the launcher from `ROOT` = the checkout that imported `delegate.py`; the launcher derives `AGENTS_ROOT` (`.launch-<task>/`, `.tools/node/bin`, `roles/`) from its own location. On Contabo that is `/opt/MoonieXHQ/Agents/Core`, as with the ssh path. A hub started from a worktree would put `.launch-<task>/` in that worktree.
- Windows hub is untouched: on `win32` a self-host codex/agy task still goes to `_spawn_local`.
- One real-bash test (`test_local_argv_is_accepted_by_the_real_launcher`) feeds the hub-built argv plus `--dry-run` to the real launcher (exits before any git/tmux/file work) so a flag the launcher rejects would fail the suite. No codex/agy/claude was started.
- Not exercised live: a real codex/agy spawn on Contabo from a Contabo hub (brief: do not spawn one). The first live run is the router's test lane B.

## Skill learning
- MISSING [CXO_Protocol_DevSpawn §touches lock] : `hook-self-repo-guard.py` matches paths named anywhere in the Bash command text, not just written ones — a heredoc whose *comment string* mentioned an undeclared `runners/…` path was refused although the only write was to a declared file. Tell workers to make source edits with the Edit tool (or keep undeclared paths out of the command text) · evidence: task-26988fe3, first edit attempt blocked, nothing written
- MISSING [CXO_Protocol_DevSpawn §done criteria] : the brief's `.venv/bin/python -m pytest` cannot run from a worktree (no `.venv`); name the main checkout's interpreter (`/opt/MoonieXHQ/Agents/Core/.venv/bin/python`) · evidence: task-26988fe3
- MISSING [CXO_Protocol_DevSpawn §done criteria] : a brief that expects `scripts/test_org_tools_registry.py` "ALL PASS" on a Contabo worker must say to export `WIKI_ROOT_ORG`/`WIKI_ROOT_MOONIEX` first; without them `wiki_list` fails on the baseline too · evidence: task-26988fe3, `wiki 'org' not available in this environment`
- MISSING [CXO_Protocol_DevSpawn §done criteria] : list the known Linux-only red tests in the brief (`test_delegate_workdir`, `test_reopen_live_worker`, `test_delegate_disk_floor::test_sufficient_disk_proceeds_to_spawn_step`, `test_skill_visibility`); they fail on 1bd7582b too, and one of them is timing-dependent · evidence: task-26988fe3 native run 3286 passed / 6 failed
- COSTLY [no owner] : telling a change's failures from the baseline's took five re-runs; a `tools/` helper that runs a named test list against `git show <base>:<file>` and restores it would have made it one command · evidence: task-26988fe3 · prevented by: a `scripts/` baseline-compare script
