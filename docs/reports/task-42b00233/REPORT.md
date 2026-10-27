## Summary
A project still at stage `idea` whose PH session is live now shows up: `portfolio.py report` prints a line for it, and `portfolio_watch.py` sends the owner C-level one `blocker` letter per episode. The v2 monitor payload and the Console validator's attention kinds are untouched.

## Files Changed
- lib/portfolio.py — `idea_with_live_ph(now, conn=None)` + `LIVE_PH_S = 15 min`; returns `[{project_id, name, lane, owner_session, ph_session}]`, `[]` on any read error
- tools/portfolio.py — `report` (non-JSON) prints `idea · <name> (<id>) · PH <ph_session> live: set stage or park` after the table
- tools/portfolio_watch.py — finding kind `idea_live_ph` (`findings`, `LABEL`, `_letter`, `plan`) + module docstring ladder
- tests/test_projecttrack_p1.py — `live_sessions()` test helper, 3 tests (helper matching/staleness, unreadable -> [], report line)
- tests/test_portfolio_watch.py — 3 tests (one letter per episode + active clears it, stale/absent/other PH sends nothing, dry run + never the CEO)

## Commits
- 7016ff47 — portfolio: idea_with_live_ph helper, report line and idea_live_ph watch finding

## Tests
- ran: env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR .venv/bin/python -m pytest tests/test_portfolio_watch.py tests/test_projecttrack_p1.py tests/test_portfolio.py -q -p no:cacheprovider -o addopts=''
- tail: `208 passed, 36 skipped in 7.93s` (exit 0)
- passed: 208
- failed: 0
- skipped: 36 (all `ORG_TEST_DB_URL not set (local Postgres 16)`, tests/test_portfolio.py, already skipped before this change)
- mutation check (rule: a test must fail without the fix): 5 breaks each made `-k idea` fail, then restored. M1 red mark on idea episodes · M2 generic 4 h owner step · M3 no 15 min freshness filter · M4 helper raises instead of [] · M5 report line dropped. Restored tree: 6 passed.

## Issues / Blockers
- none. One guard hit: `git checkout -- .` was refused by self_repo_guard (worktree root); I restored per file instead.

## Notes for Reviewer
- Reaches: `monitor_payload`/`_monitor_all` NOT changed (checked in the test: attention == [] and projects == [] for the idea project). Callers of the new helper: `tools/portfolio.py run()` (report) and `portfolio_watch.findings()`. `plan()`, `_letter()` and `LABEL` are shared with the other kinds; they are the only shared lines edited.
- Console validator (read only, src/portfolio/validate.js:114) allows exactly late | waiting_ceo | no_plan | unlinked_order, so no new attention kind was possible; confirmed.
- Matching: live = `live_sessions.seen_at >= now - 15 min` and (`sid` == ph_session, with or without `project_head-`, or the session `name` contains it, only when it is 6+ characters, so a short ph_session cannot match every name). Role is not checked; the task named sid or name only.
- Interpretation: "no 4 h or 24 h step" also means no `red: true` mark at 24 h for this kind (the red mark is a 24 h step in `plan()`); it is skipped via `f["kind"] != "idea_live_ph"`. Revert that one condition if you want the mark.
- `findings()` calls the helper last: on PostgreSQL a failed `live_sessions` read aborts the shared transaction, and nothing reads after it.
- Letter subject `idea: <name> has a live PH`; body names `portfolio.py stage <id> active` and `park <id>`. Owner box comes from `_owner_box(lane, owner_session)`, so a project with no owner_session gets no letter (same as the other kinds).

## Not checked / risk
- Not run against a real Postgres (no hub, ORG_TEST_DB_URL unset): the `seen_at >= ?` comparison on a TIMESTAMPTZ with an aware datetime, and the real `live_sessions` row shapes, were tested only on the SQLite in-memory Store with ISO text. If PG rejects it the helper returns [] (silently no line, no letter), so the failure mode is "feature does nothing", not a crash.
- Not run: `tools/portfolio_watch.py --nudge` or `report` on the live hub (forbidden here). Whether a real PH row's `sid`/`name` carries the 8-hex was read from `tools/live_sessions.py` (`PH#<id>` names, sid = UUID tail), not observed on the hub.

- Rules read: IRON-RULES §23 (verify, no scope creep) and §30 (no DDL; the only CREATE TABLE is a test fixture in an in-memory SQLite store). I did not read the whole file, and `playbooks/` has no developer playbook (web-designer.md only).
- `REPORT.md` is untracked at the worktree root on purpose (not in the task's `touches`, and a root file would merge into main). Say if you want it under docs/reports/task-42b00233/ instead.

## Skill learning
- COSTLY [no owner] : `git checkout -- .` (restoring after a mutation run) was refused by self_repo_guard because `.` is the worktree root, and the whole Bash call, including the commit in it, did not run; one round lost · evidence: task-42b00233, hook text "Refused because it is the worktree root itself" · prevented by: a line in the developer pre-work list: restore by explicit declared path (`git checkout -- <file>`), commit before mutating.
- MISSING [developer role doc §Pre-work Checklist] : `mcp__org__wiki_read` answered "wiki 'org' not available in this environment" on this Contabo worker; the rules are on disk at /opt/MoonieXHQ/Agents/Rules, but `cd` there is refused by hook-cwd-guard, so only Read/Grep with absolute paths work · evidence: task-42b00233

## PH review (PH#40fefb4e)
- Real hub, read only: the `live_sessions` query with an aware datetime runs on TIMESTAMPTZ and returned 19 rows. A Contabo PH has its full 8-hex as `sid`, for example 45728c34 for RunMedia.
- Bug found and fixed: a PH on winbox or the Mac is listed with only the first 3 hex as `sid` (`f35` for f35affd5), and its name carries `PH#f35`. The name rule needs 6+ characters, so it could never match. Added: a `project_head` row with a 3-character sid matches an id that starts with it. Test added; 209 passed.
- Risk: two PHs whose ids share the first 3 hex. The cost is one extra letter to a C-level.
