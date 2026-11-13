# REPORT task-559cc362

## Summary
The router now drops every agy candidate for a task that needs a command outside agy's print-mode allow-list, and says why in the router line (`agy skipped: needs npm (project mooniex-console)`). The allow-list is read straight from `config/agy-settings.json` (no second copy); `plans.yaml` only says which jobs need more (`agy_skip`: roles, command words, stack words), and tests keep the two in step. Console developer task, video_editor task: no longer agy. Agents-Core python developer task: still agy.

## Files Changed
- config/plans.yaml — new `agy_skip` block: `roles: [video_editor, browser_operator]`, `commands: [npm, npx, pnpm, yarn, node, ssh, scp, rsync, curl, wget, docker, ffmpeg]`, `stack: [node, pnpm, yarn, npm, next.js, electron]`; comment on `shell_runners` pointing to it.
- tools/route.py — `AGY_SETTINGS`, `agy_allows(cmdline, settings=None)` (reads the real allow/deny rules; deny wins; unreadable file allows nothing), `_names_command`, `_project_node_command`, `agy_skip_reason(worker_role, cls, brief, project, cfg)`. `plan()` gets `worker_role=`/`project=` and marks every agy candidate `cannot` with why `agy skipped: <reason>`; `pick_runner()` gets `project=` and appends the reason to the chosen choice's `reason` (that is the `router:` line in delegate_log).
- tools/delegate.py — `_route_runner` passes `project=task.get("project")` to `pick_runner` (one line).
- tests/test_route_agy_skip.py — new, 36 tests.
- tests/test_delegate_router.py — the three `pick_runner.assert_called_once_with(...)` pins now include `project=` (first one pinned to the task's `"test-project"`, the other two `ANY`).
- docs/reports/task-559cc362/REPORT.md — this file.

## Commits
- 8cf3c711 — router: skip agy for jobs that need a command outside its allow-list
- 36646cbb — router: next.js/electron stack words mark a node project; report (this file)
- (a last commit only fixes this list; `git log origin/agent/developer-task-559cc362` has its sha)

## Tests
- ran: `PYTHONUTF8=1 python -m pytest tests/test_route_agy_skip.py tests/test_route_pick.py tests/test_route_browser_agy.py tests/test_route_plan.py tests/test_route_budget.py tests/test_route_ceo_order.py tests/test_route_claude_last.py tests/test_route_override.py tests/test_delegate_router.py` (Windows box, scratch venv Python 3.11.9 + pytest 8.4.2; the Contabo interpreter does not exist here)
- passed: 152 (36 of them the new file)
- failed: 0
- skipped: 0
- not runnable on this box (Windows has no `fcntl`, scratch venv has no `mcp`): `tests/test_route_guards.py` 32 failed / 5 passed (hook scripts, never import tools.route), `tests/test_router.py` collection error, `tests/test_router_hub_only.py` 1 failed / 9 passed, `tests/test_w26_pick_host.py` 1 failed + 14 errors / 67 passed (its `role_runners` tests, which stub `route.plan`, are among the passes). Every one of those errors is `ModuleNotFoundError: fcntl` (one `mcp`). Not caused by this change; run them on Contabo.
- Baseline before my change: the same 55 route/delegate tests were 53 passed + 2 failed with Windows' cp1252 default; both pass under `PYTHONUTF8=1` (plans.yaml has non-ASCII), so all runs above use it.
- Fails-without-the-fix check (done): with the `agy_skip and c.runner == "agy"` line disabled, 5 of the 36 new tests fail (Console, video_editor, plan marking, worker-role, router-line); restored, 36 pass. Sync tests: adding `command(npm)` to the real allow-list fails `test_every_command_in_agy_skip_is_refused_by_the_real_allow_list` (+ 4 others that depend on npm being refused); adding `command(playwright)` to the deny list fails `test_every_denied_tool_command_is_known_to_the_router`. Both edits reverted (`git diff config/agy-settings.json` empty).

## Issues / Blockers
- none that stop the work. Judgement calls the CTO may want to overrule are listed under Notes.

## Skill learning
- COSTLY  [no owner] : running pytest on a Windows remote worker took ~10 min of setup: no pytest, no `tzdata` (lib/coo_policy `ZoneInfo("Asia/Bangkok")` fails at conftest import), no `requests`, and cp1252 makes `load_plans()` fail on the non-ASCII plans.yaml (2 baseline failures that vanish under `PYTHONUTF8=1`) · evidence: task-559cc362 · prevented by: a recipe in roles/_worker_remote.md: `python -m venv <scratch>; pip install pytest pyyaml psutil tzdata requests; PYTHONUTF8=1 python -m pytest ...`
- MISSING [CTO_Knowledge_AGY §allow-list] : the skill says agy runs only `config/agy-settings.json`'s list, but not that the router now enforces it from plans.yaml `agy_skip` (role / brief command / node project), nor the `edit-only:` header that lifts the brief and project checks · evidence: task-559cc362 8cf3c711
- MISSING [CXO_Protocol_DevSpawn §0, field note 2026-10-15] : "pin Claude when the brief's check commands need node/git -C/Playwright" is now partly done by the router for npm, npx, pnpm, yarn, node, ssh, scp, rsync, curl, wget, docker, ffmpeg and node projects; `git -C`, `playwright`, bare `python <script>` and `git commit` are still NOT caught, so that pin advice still holds for those · evidence: task-559cc362 tools/route.py `agy_skip_reason`
- MISSING [roles/_worker_remote.md AGY contract | no owner] : tests/test_route*.py as a glob also matches test_router.py, test_router_hub_only.py and test_route_guards.py, which import `fcntl` and cannot run on a Windows worker · evidence: task-559cc362

## Notes for Reviewer
Reach, listed before the first edit:
- `pick_runner` callers: `tools/delegate.py::_route_runner` (updated), the `--pick` CLI in route.py (no project, unchanged). Tests that pin its call: `tests/test_delegate_router.py` (3 asserts, updated).
- `plan()` callers: `pick_runner`; `lib/router.py::role_runners` and `runners/coo_worker.py::candidates` call it without `worker_role`/`project`. Effect: the brief-command check applies to both (it only needs `brief`); the role and project checks do not. So the host router's `role_runners` can still list agy for a video_editor / node-project task that `pick_runner` then drops. I left lib/router.py alone (outside the brief); passing `worker_role=task["role"], project=task.get("project")` there is a two-kwarg follow-up, and its test stub `plan(cls, **kw)` already accepts them. coo_worker's research workers (agy in a no-command box) would lose agy if a research brief names e.g. `curl` or `ssh`; rare, noted.
- Config: plans.yaml `agy_skip` (read by route only). `config/agy-settings.json` is read, never written. The winbox settings file (config/agy-settings-winbox.json) is not consulted: it allows no command but agy_browse, so everything in the catalogue is refused there too.

Judgement calls (change in plans.yaml / one function, no code redesign):
1. Project signal is OR, not AND with the brief: a developer task on a node project goes off agy unless the brief header has `edit-only: <why>`. Reason: the role doc tells every worker to run the tests, and in a node repo that is npm. Evaluated against the real registry: claudeflow (test_command npm), webapp (npx), option (node), claudesign (stack pnpm), console (stack node), lungnote-webapp and warpclip-webapp (stack next.js) skip agy on every machine; dungeonrunner skipped here only because this box (winbox) has its checkout with a root package.json, so a project with no test_command and no node/next/electron stack word is judged by the checkouts the router's machine has. `typescript` is deliberately not a stack word (comfy-runpod-worker is python + typescript). If you want AND (brief must also name npm/node), it is one line in `agy_skip_reason`.
2. Role skip is unconditional (even `edit-only:` does not lift it): video_editor work is ffmpeg/ssh/media scripts by nature (CEO 11 Nov put it on dev_shell for codex's shell). browser_operator is a no-op today (not in role_classes) and only guards a future entry; the browser_agy class is exempt (GH #188), tested.
3. Brief matching is deliberately plain: a lower-case command word followed by an argument, `node` needs a flag or a `.js/.mjs/.cjs` path, case-sensitive ("SSH section" does not match). Known false positive: prose like "the curl library is ..." skips agy; `edit-only:` lifts it. Known gaps (not in scope): bare `python script.py`, `git commit`, `git -C`, `playwright`.
4. `agy_skip.commands` entries that the real allow-list allows are ignored at runtime, so allowing npm later needs no plans.yaml edit; the sync tests (every catalogued command refused; every plain deny rule known to the router, except rm/sudo) fail loudly if the files drift the other way.

## Not checked / risk
- Not run on Contabo/Linux with the real venv: `test_route_guards.py`, `test_router.py`, `test_router_hub_only.py`, `test_w26_pick_host.py` could not run here (`fcntl`/`mcp`); my change reaches them only through `plan()`'s new optional kwargs, so I expect green, but I did not see it.
- Not run end to end: no real `delegate_task` through a hub; the `router:` line text is checked on `Choice.reason` in unit tests, not in a delegate_log row. I could not read the briefs of task-74363c69, task-79bcc8af or task-502a032c (hub DB not reachable from this box), so the Console/video_editor cases use synthetic briefs plus the real projects.yaml.
- Behaviour risk: more tasks move from agy to codex/Claude (every developer task on 7 node projects, every video_editor task). Claude is on the Pro budget; I did not measure how many tasks shift. A stray `package.json` added at the Agents-Core root would silently move every Agents-Core task off agy (`test_the_real_registry_marks_node_projects_and_not_agents_core` would then fail on that machine, which is the signal).
