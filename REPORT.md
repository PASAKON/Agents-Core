# REPORT task-fd32e033

## Summary
Fixed winbox's stale post-reinstall paths in `config/hosts.yaml` and
`config/projects.yaml` (Org Mesh W3.0): the Windows profile moved from
`C:\Users\UsEr` to `C:\Users\passg`, and `C:\Users\UsEr` now only survives as
a compat junction made by `windows/winbox-reinstall/rebuild/fresh_inv.ps1`.
Named the real, measured paths for `mooniex-agents` and `cookierun-bot`, and
**removed** `mooniex-webapp`'s `paths.winbox` entirely since no checkout of
it exists anywhere on winbox. Verified (by reading `lib/config.py` and
`tools/delegate.py`, not by guessing) that a missing `paths.<host>` key
already produces a clean refusal rather than a crash or a spawn into a
missing folder — no code change was needed for that. Also verified there is
no folder-trust pre-seeding by path string anywhere in this repo's code, so
nothing needed updating there either.

## Files Changed
- `config/hosts.yaml` — winbox `agents_root` → `C:\Users\passg\mooniex`,
  `worktrees` → `C:\Users\passg\mooniex\worktrees`.
- `config/projects.yaml` —
  - `mooniex-agents.paths.winbox` → `C:\Users\passg\mooniex\repo\MoonieX-Agents`
    (updated the stale comment above it too — it used to say "winbox has no
    clone yet"; the task brief confirms a real checkout with `.venv` exists
    there now).
  - `cookierun-bot.paths.winbox` → `C:\Users\passg\cookierun-bot`.
  - `mooniex-webapp.paths` — removed the `winbox:` line entirely (only
    `mac:` remains); rewrote the comment above it to explain why, instead of
    leaving a stale "winbox is a real clone already" claim in place.
- `tests/test_multihost.py` —
  - `test_project_path_for_host_winbox_resolves` now asserts the `passg`
    path.
  - Added `test_project_path_for_host_webapp_winbox_not_routable`, mirroring
    the existing `mooniex-console` not-routable test, to lock in the new
    "no checkout on winbox → refuse cleanly" behavior for `mooniex-webapp`
    specifically (this is the actual behavior change item 2 in the task
    brief cared about, and nothing previously asserted it).

Left `scripts/test_remote_worker_log.py`, `scripts/test_send_to_worker_remote.py`,
and `scripts/test_watchdog_remote_heartbeat.py` untouched: their
`WINBOX_HOST_CFG`/inline dicts (e.g. `{"worktrees": r"C:\Users\UsEr\mooniex\worktrees"}`)
are free-standing fixtures fed to monkeypatched `get_host`/`config.host`
calls — none of them read `config/hosts.yaml` or `config/projects.yaml` — so
per the task brief's own instruction ("change them to passg only if they
read the real config") they stay as-is.

## Commits
- `817e07fd` — config: fix winbox paths after reinstall (Org Mesh W3.0)

## Tests
- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest` (full suite,
  `testpaths = scripts lib tests`, `run_in_background: true`, no `-q`/`-x`
  added — `pytest.ini`'s own `addopts` already carries `-q`)
- passed: 2883
- failed: 4
- skipped: 26
- total time: 297.15s

All 4 failures are exactly the four pre-declared known-unrelated failures
from the task brief, none of which touch `config/hosts.yaml`,
`config/projects.yaml`, or path resolution:
`scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`,
`tests/test_mesh_check.py::test_check_l0_green_when_sources_agree`,
`tests/test_worker_naming.py::test_current_host_defaults_to_mac`,
`tests/test_worker_naming.py::test_current_host_blank_org_host_falls_back_to_mac`.

`tests/test_multihost.py` is **not** part of that default run (its own
docstring says so, and a `grep` of the log confirms zero matches — it's in
`tests/` but nothing in `pytest.ini` special-cases it either way, it simply
isn't picked up by the default invocation used here), so I ran it
explicitly and separately, also `run_in_background: true`:
- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_multihost.py -v`
- passed: 44
- failed: 0
- skipped: 0
- total time: 11.34s

## Issues / Blockers
- none

## Notes for Reviewer
- **Missing-key handling (task brief item 2, verified not guessed):**
  `lib/config.py:308` `project_path_for_host()` already raises
  `ValueError(f"project {project_key!r} has no path configured for host "
  f"{host_name!r} — not routable there. Add it under paths.{host_name} in
  config/projects.yaml.")` when a project has no `paths.<host>` entry (this
  is the exact mechanism the pre-existing `mooniex-console`/winbox test
  exercises). `tools/delegate.py:1238` calls it inside `_spawn_remote()`
  with the comment "raises if not routable", uncaught at that point. Its
  only caller, `delegate_task()` (`tools/delegate.py:1761-1774`), wraps the
  entire `_spawn_remote()` call in `try/except Exception`: on failure it
  releases any path locks, logs `remote spawn setup failed task=... host=...:
  <e>`, and sets the task's status to `failed` with
  `delegate_log=f"remote spawn setup failed ({resolved_host}): {e}"` — then
  returns the task row normally. So a delegate of `mooniex-webapp` to
  `winbox` now fails loudly with a clear, specific reason on the task row;
  it never reaches `spawn-worker.ps1` and never touches winbox's
  filesystem. I did not add any fake/placeholder path — none was needed.
- **Folder-trust pre-seeding (task brief item 4):** grepped
  `windows/spawn-worker.ps1` and `tools/delegate.py` (and, for completeness,
  `runners/worker_init.py`, `runners/branch_poller.py`, `claude-home/`) for
  `.claude.json`, `trustedFolders`, `hasTrustDialogAccepted`, "trust" in any
  form. Found nothing that seeds Claude's folder-trust config by a path
  string anywhere in this repo's code. `spawn-worker.ps1`'s only
  profile-relative reference is `$claude = Join-Path $env:USERPROFILE
  '.local\bin\claude.exe'` (line 276) — already dynamic via the live SSH
  session's `$env:USERPROFILE`, so it needs no change and will resolve
  under the `passg` profile automatically. Per `.claude/skills/CXO_Protocol_DevSpawn/SKILL.md`
  §5b, the trust prompt ("Accessing workspace … ❯ No, exit / Yes, I trust
  this folder") is instead answered **interactively** by a human/operator
  running a `tmux capture-pane` poller that sends `Down`, `Enter` when the
  prompt appears — path-agnostic by construction, since it works by
  screen-scraping whatever text is on screen rather than matching a
  specific path. So there is nothing to re-seed for the new `passg` path,
  and I made no edit to `spawn-worker.ps1`.
- Two **stale, non-functional comment examples** referencing the old
  `C:\Users\UsEr` path remain in `windows/spawn-worker.ps1` (line 20's
  `# Deployed to $AgentsRoot (e.g. C:\Users\UsEr\mooniex\spawn-worker.ps1)`
  and line 189's `# C:\Users\UsEr\.git\info\exclude`). Left untouched — the
  task brief scopes edits to that file strictly to a one-line folder-trust
  fix, and neither line is trust-related or functional (both are
  illustrative comments only, unrelated to `$env:USERPROFILE`-derived
  behavior). Flagging for whoever picks up `roles/cto-windows.md`
  (task W3.2) or a docs pass, since they're now misleading.
- `config/machine-contract.yaml` and every doc under `docs/` (including
  `docs/design/multi-host-workers.md`, `docs/design/org-mesh.md`,
  `docs/ops/agent-runners.md`) still say `C:\Users\UsEr\...` — explicitly
  out of scope per the task brief ("Out of scope … docs. The junction keeps
  those working"), left untouched.
- Cookie Run scripts (`windows/cookierun_*.py`, `scripts/cookierun-health.sh`,
  `scripts/pc-lease.sh`, `tools/cookierun_teachers.py`) and
  `roles/cto-windows.md` also still reference the old path — explicitly
  out of scope per the brief, untouched.

## Skill learning
- MISSING [no owner] : no skill documents that `pytest.ini`'s `testpaths =
  scripts lib tests` does **not** guarantee every file under `tests/` runs
  in the default invocation — `tests/test_multihost.py`'s own docstring is
  the only place that says so, and it's easy to miss and report a
  misleadingly-good "N passed" number that silently excludes the file the
  task actually cared about most. evidence: task-fd32e033, confirmed via
  `grep -c test_multihost` on the full-suite log (0 matches) after the run
  finished. fix: a one-line addendum to whichever skill covers running this
  repo's test suite (I don't have write access to propose the exact one) —
  "grep the full-suite log for a file you expect to be covered before
  trusting the pass count; some files under `tests/` are opt-in-explicit
  despite being inside `testpaths`."
- (none) beyond the item above — the config edits, the
  `project_path_for_host`/`_spawn_remote`/`delegate_task` refusal chain,
  and the folder-trust investigation all matched what the task brief
  predicted on the first read; no surprises in the test run either (exactly
  the four pre-declared unrelated failures, nothing else).
