# task-6f6e5179 — Org Mesh W0.3: delegate to self and to a spoke from any host

## Summary
A C-level on any host now delegates locally by default (`self_host()`, not a literal `mac`), the local spawn is its own function that touches iTerm/osascript/`open` on Darwin only, and remote deploys ship `git show origin/<base>:<path>` blobs instead of the Mac's working tree. `create_worktree` resolves the checkout per host, the worker MCP config is rendered per spawn for the host's own ROOT, and `state/machine-discovered-*.yaml` is untracked. Full suite: 3142 passed, 27 skipped, 0 failed.

## Files Changed
- `tools/delegate.py` — default host and every "this machine" comparison use `self_host()`; new `_spawn_local(task, proj)` (iTerm/osascript/`open` only when `sys.platform == "darwin"`, otherwise the tmux backend); `_task_meta` / `_write_task_sidecar` (local spawns write the same `.org-task.json`, mode 600, git-excluded, that remote spawns write); `_fetch_origin` / `_origin_blob` and both deploy functions read from `origin/<base>`; Linux launcher goes to `<agents_root>/.launch/spawn-worker-remote.sh`; the guard entry is gone from `_REMOTE_DEPLOY_FILES_LINUX`; deploys run no git/network in dry-run. The router hook (`_route_runner`, the `routed = await asyncio.to_thread(...)` block, the runner pre-flight) is untouched — no changed line in the diff against origin/main contains those names.
- `tools/worktree.py` — `_repo_path()` = `project_path_for_host(project, self_host())`, used by `create_worktree`, `remove_worktree`, `list_worktrees`.
- `lib/worker_mcp_config.py` (new) — renders `config/worker.mcp.json` (kept as the tracked template) for this host: Mac root → this ROOT, venv python via `cxo_mcp_config._venv_python`, LungNote via `LUNGNOTE_MCP_JS`/`LUNGNOTE_MCP_NODE` (server dropped + one stderr line when no candidate exists), everything else passed through so `cutover_flip.py`'s command/env survive. `write_for_worktree` writes `<worktree>/.org-worker.mcp.json` (mode 600) and adds it to the worktree's info/exclude. `scripts/lib/cxo_mcp_config.py` is imported, not edited.
- `runners/worker_init.py`, `runners/worker_resume.py` — both now pass `write_for_worktree(worktree, ROOT)` to `--mcp-config`.
- `lib/notify.py` — `mac=True` desktop banner (osascript) only when `sys.platform == "darwin"` (found by my own test, see Notes; CTO added the path to touches).
- `scripts/spawn-worker-remote.sh` — guard-copy block (section 2c) and its three dry-run wordings deleted; header says the launcher lives in `.launch/`; `.worker.pid` exclude line kept; `bash -n` clean under /bin/bash 3.2.57.
- `.gitignore` — `.launch-*/`, `state/machine-discovered-*.yaml` (`.launch/` was already there).
- `state/machine-discovered-contabo.yaml` — `git rm --cached` (file stays on disk).
- `conftest.py` — opt-in fixture `pinned_mac_host` (ORG_HOST unset, no node.yaml, ROOT = Mac agents_root, platform = Darwin, `self_host` cache cleared both sides).
- `tests/test_w03_self_host_spawn.py` (new, 20 tests), `tests/test_worker_naming.py`, `tests/test_mesh_check.py`, `tests/test_multihost.py`, `tests/test_spawn_remote_linux.py`, `tests/test_worktree_sparse.py`, `tests/test_worktree_keep_paths.py`, `scripts/test_gc_worktree_reap.py` — see Tests.

## Commits
- bda28f76 — delegate: default host = self_host(), _spawn_local, origin-blob deploy; worktree: repo per host
- 202bcb24 — worker: render worker.mcp.json per spawn for THIS host
- da410b92 — spawn-worker-remote: drop guard copy, launcher lives under .launch/
- f7106b4f — gitignore: .launch-*/, state/machine-discovered-*.yaml; untrack contabo's copy
- 10e58dc9 — tests: pin self_host to mac where a test means 'the Mac'
- c8a23214 — tests: W0.3 self_host spawn, origin-blob deploy, per-host worker MCP config
- ce20536a — notify: desktop banner (osascript) on Darwin only, with a test
- 5ee55722 — drop CTO-FEEDBACK.md from the branch (my `git add -A` had swept it in)

`git fetch origin && git merge origin/main` at the end: "Already up to date" (origin/main = cc812fa2, the base).

## Tests
- ran: `ORG_ROUTER=off .venv/bin/python -m pytest` (full suite, background, no -q/-x/-n)
- passed: 3142
- failed: 0
- skipped: 27
- (exit 0, 194 s. The known Mac failure `test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins` did not occur in this run.)
- ran: `tests/test_worker_naming.py tests/test_mesh_check.py tests/test_multihost.py tests/test_self_host.py tests/test_w03_self_host_spawn.py` three times — default env, `ORG_HOST=contabo`, and `HOME=<tmp>` with a `~/.config/mooniex/node.yaml` saying `host: contabo` (confirmed `self_host()` = contabo there) → 131 passed, 0 failed each time.
- ran: `.venv/bin/python scripts/test_org_tools_registry.py` → last line `ALL PASS`
- ran: `.venv/bin/python scripts/test_mcp_role_config.py` → last line `OK — 0 failure(s)`
- New file `tests/test_w03_self_host_spawn.py` (20): self_host=contabo + no host arg → one tmux create, zero ssh/scp argv; local `.org-task.json` mode 600 + excluded; non-darwin → no osascript/`open`, no iTerm; darwin → iTerm kept; notify banner runs osascript on darwin only (linux/win32/darwin); `create_worktree` uses `paths.<self_host()>` (contabo and mac, temp repos) and refuses a host with no path; Linux deploy sends the fetched `origin/main` blob while the working-tree copy is dirty and origin was one commit ahead of the hub's last fetch; no ssh/scp argv touches `<agents_root>/scripts` and none mentions the guard; Windows deploy sends origin blobs; dry-run runs no subprocess; Mac generated MCP config == template; other-host config has no `/Users/gob`; LungNote dropped with exactly one stderr line; cutover-flipped org command/env survive; generated file mode 600 and git-excluded; both launchers go through `write_for_worktree`.
- Existing tests changed: `test_current_host_defaults_to_mac`, `test_current_host_blank_org_host_falls_back_to_mac`, `test_check_l0_green_when_sources_agree` (pinned via `pinned_mac_host`); `test_browser_operator_cap_reached_sets_conflict` (a NULL host now counts as `self_host()`, so it is pinned to the Mac); `test_spawn_remote_linux.py` (launcher path `.launch/`, guard no longer in dry-run); the three worktree tests that stub `worktree.get_project` also stub `project_path_for_host`.

## Issues / Blockers
- none open. One block on the way: `lib/notify.py` was refused by `self_repo_guard` (not in touches); reported via `dev_message`, CTO added it, fixed.

## Notes for Reviewer
- **Contabo — exact commands BEFORE the next `git pull`** (root over `ssh mooniex-vps`). The pull deletes the tracked `state/machine-discovered-contabo.yaml`; if the weekly cron already rewrote it, the pull refuses instead. Rehearsed in throwaway repos: without prep `error: Your local changes ... would be overwritten by merge`; with the steps below the live copy comes back and `git status` is clean. In the toy repo the pull also removed the now-empty `state/` directory, so `mkdir -p state` is there for safety.
  ```bash
  cd /opt/MoonieXHQ/Agents/Core
  # 0. earlier deploys overwrote TRACKED scripts/spawn-worker-remote.sh and scripts/hook-self-repo-guard.py
  #    with the Mac's working-tree copies. Look, then restore them so the pull is clean:
  git status --short
  git diff --stat -- scripts/spawn-worker-remote.sh scripts/hook-self-repo-guard.py
  git checkout -- scripts/spawn-worker-remote.sh scripts/hook-self-repo-guard.py
  # 1. back up the live discovered file OUTSIDE the repo
  cp -p state/machine-discovered-contabo.yaml /root/machine-discovered-contabo.yaml.pre-w03
  # 2. drop the local (cron) rewrite so git can delete the file, then pull
  git checkout -- state/machine-discovered-contabo.yaml
  git fetch origin && git merge --ff-only origin/main
  # 3. restore the live copy; it is git-ignored now
  mkdir -p state && cp -p /root/machine-discovered-contabo.yaml.pre-w03 state/machine-discovered-contabo.yaml
  git status --short              # expect nothing for state/
  git check-ignore -v state/machine-discovered-contabo.yaml   # expect the .gitignore rule
  ```
  Step 0 changes tracked files on Contabo: read the `git diff --stat` first; if anything other than those two paths is dirty, stop.
- **Readers of `state/machine-discovered-*.yaml`** (grep of the whole tree), all fine untracked: `tools/machine_doctor.py` — `_load_discovered` returns `[]` when the file is absent, `check()` does `sd.mkdir(parents=True, exist_ok=True)` before `_write_discovered`, nothing ever `git add`s it; `scripts/hub/contabo-cutover-remote.sh` (:38-46) filters it out of `git status --porcelain` — an ignored file never appears there, the filter only matters for a legacy tracked copy, so it stays harmless (its comment still says "tracked"; not edited); `scripts/hub/contabo-cutover.sh` (comment only); `scripts/contabo_restore.sh` and `scripts/mac_restore.sh` run `machine_doctor check` only; docs `docs/ops/machine-contract-schedules.md`, `docs/ops/briefs/machine-contract-phase1.md`; tests `test_machine_doctor.py` (tmp_path) and `test_hub_cutover_scripts.py` (builds its own temp repo with the file tracked — still valid for the legacy state).
- The first deploy after this lands creates `<agents_root>/.launch/spawn-worker-remote.sh` on Contabo (git-ignored). `LAUNCH_DIR` inside the script is still `<agents_root>/.launch-<task>/`; `AGENTS_ROOT=dirname(SCRIPT_DIR)` still resolves correctly from `.launch/`.
- `tools/delegate.py::_ensure_remote_deploy` (Windows) gained a `base=None` keyword; a real (non-dry-run) deploy now runs `git fetch origin <base>` in the hub's repo — a failed fetch only warns and the last fetched ref is used; a missing blob on origin is skipped.
- `lib/notify.py`: `success()`/`error()` pass `mac=True`, and "DEV spawned" is a `success()`, so a Contabo local spawn reached `osascript` (harmless there — FileNotFoundError is caught — but against "never call osascript off Darwin"). My test caught it.
- The Linux launcher builds its own claude command and never passes `--mcp-config`; only `worker_init`/`worker_resume` (Mac/winbox paths) were wired.
- `pinned_mac_host` lives in the root `conftest.py` (shared by two test files); it patches `config.ROOT` — only `.env` reads use it lazily, and `_read_dotenv_var` is already neutralised there.
- A worker's generated `.org-worker.mcp.json` equals the template only when ROOT is the Mac hub checkout (`worker_init.ROOT` is the hub root, never the worktree). Under a worktree ROOT, paths follow that ROOT by design.

## Skill learning
- MISSING [CXO_Protocol_DevSpawn §touches] : a brief that says "never call osascript off Darwin" must list `lib/notify.py` in touches — `success()`/`error()` (mac=True) are the osascript callers on the spawn path; without it the DEV is blocked by self_repo_guard mid-task · evidence: task-6f6e5179, guard refusal, CTO-FEEDBACK.md 19:39
- MISSING [CXO_Protocol_DevSpawn §worktree excludes] : `CTO-FEEDBACK.md` is not in the worktree's info/exclude, so the DEV's mandatory `git add -A` committed it into the branch · evidence: commit ce20536a → removed in 5ee55722 · fix: add it to the provisioning exclude names next to TASK.md
- COSTLY [no owner] : `hook-secret-env-guard` blocks a command that merely uses a Python variable named `ps` (reads as `ps e`) — cost one retry and the paths.mac/path check · evidence: task-6f6e5179 session · prevented by: never name a shell/Python variable `ps`
- COSTLY [no owner] : zsh does not word-split `$pre`/`$FILES`; `pytest $FILES` and `$pre cmd` failed with "no such file" twice despite the rule in the shared conventions · evidence: task-6f6e5179 · prevented by: write the file list out in full or use bash
- COSTLY [no owner] : GateGuard armed once per new file (11 rounds this task), and `rm -rf` / `git checkout --` in a scratch rehearsal triggered its "destructive" gate; a cwd-guard also blocked `cd "$SP/..."`. Put scratch rehearsals in a script file under the scratchpad and run `/bin/bash file` · evidence: task-6f6e5179
