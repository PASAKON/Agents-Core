# REPORT task-9823c1e3

## Summary
`tools/forecast.py` no longer treats the bare words "screenshot" and "screen capture" as a Claude-only tool, so a brief such as "take 844x390 screenshots with the headless e2e script (Playwright/node)" now routes to Codex as shell work. Phrases that really mean the Claude browser (`in chrome`, `claude-in-chrome`, `chrome mcp`, `browser_operator`, `drive the browser`, `mcp__`, ...) are unchanged and still force Claude.

## Files Changed
- tools/forecast.py — removed `"screenshot"` and `"screen capture"` from `CLAUDE_TOOL_PATTERNS`; comment above the list says why and which phrases still catch a browser screenshot. No other pattern touched, no new pattern (`"screenshot in chrome"` is already covered by `"in chrome"`).
- tests/test_route_claude_last.py — 6 new rows in `test_needs_claude_tool`: three that must be False (`Playwright screenshots via node design/e2e-headless.cjs`; `Take 844x390 screenshots with the headless e2e script (Playwright/node)`; `Grab a screen capture of the page with ffmpeg`) and three that must stay True (`use claude-in-chrome to take a screenshot`; `Take a screenshot in Chrome and attach it`; `Use the chrome mcp to take a screenshot of the dashboard`).
- docs/reports/task-9823c1e3/REPORT.md — this file.

## Commits
- 64b2198d — router: bare "screenshot" / "screen capture" no longer mark a brief as Claude-only
- (a second commit adds this report; `git log origin/agent/developer-task-9823c1e3` has its sha)

## Tests
- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/ -k "forecast or route"` (plain, no -q), Contabo, run from the worktree
- passed: 362
- failed: 0
- skipped: 2 (`tests/test_w42b_node_token_api.py:654` and `tests/test_w43_join_api.py:544`: `ORG_TEST_DB_URL not set`, the real-Postgres param; nothing to do with the router)
- also ran: `tests/test_ph_brain.py tests/test_delegate_router.py` — 47 passed, 0 failed (the first has a "take a screenshot" brief, `test_ensure_browser_agy_brief_passes_route_class_for`; it still passes because it also says "Higgsfield")
- repro before the fix: `forecast.needs_claude_tool(...)` returned True for the Playwright/node brief (the bug), and for all five probe briefs.
- fails-without-the-fix check (done): `git checkout HEAD -- tools/forecast.py` then `pytest tests/test_route_claude_last.py -k needs_claude_tool` → 3 failed (the three new False rows), 10 passed. Fix copied back, 13 passed. The three new True rows pass both ways by design: they guard against dropping too much.

## Issues / Blockers
- Instruction conflict, resolved in favour of the task text: the shared worker rules say "Never `git push`", the task says "Commit and push". I pushed only my own branch `agent/developer-task-9823c1e3` (never main), as the task asked and as IRON §2 and the previous router task (task-559cc362, PR #731) did.
- The wiki tool `mcp__org__wiki_read` answered `ERROR: wiki 'org' not available in this environment`; I read `IRON-RULES.md` and `projects/mooniex-agents.md` from `/opt/MoonieXHQ/Agents/Rules/` on disk instead. `roles/developer.md` does not exist there (the role text is in the system prompt), and I did not open a developer playbook file beyond that.

## Notes for Reviewer
Reach, listed before the first edit:
- Callers of `forecast.needs_claude_tool`: only `tools/route.py:429` (inside `plan()`, when the `needs_claude_tool` argument is None). `tools/route.py:507` turns it into `cannot: needs a Claude-only tool` for every non-Claude candidate. `route.plan` is reached from `pick_runner` and from `tools/delegate.py` `_route_runner`.
- Tests that cover it: `tests/test_route_claude_last.py` (`test_needs_claude_tool`, `test_cannot_outside_ranks_after_claude`), `tests/test_ph_brain.py`, `tests/test_delegate_router.py`.
- Config/docs that list the patterns: none (`config/plans.yaml` only mentions `needs_claude_tool` in comments about footage capture and browser; those words are still patterns).
- Behaviour change to be aware of: a brief whose only browser hint is the word "screenshot" or "screen capture" (for example "take a screenshot of the Higgsfield queue" with no other marker) is no longer pushed to Claude by this function. A Higgsfield brief still is (`higgsfield` is a pattern). A browser_operator task is also still caught by the `browser_operator` pattern and by the role-based `agy_skip`/`browser_agy` routing from PR #731. If the CTO wants the old behaviour for some specific phrasing, add that exact phrase as a pattern rather than the bare word.
- `"in chrome"` is a substring match, so "headless chrome" is NOT caught but "screenshots in Chrome" is. A node/Playwright brief that says "run it in Chrome" would still go to Claude; I left that alone because the task named only the two bare patterns.

## Not checked / risk
- I did not run the full test suite (13,000+ tests), only `-k "forecast or route"` plus `test_ph_brain.py` and `test_delegate_router.py`; a test elsewhere that depends on a bare "screenshot" brief being Claude-only would not have been seen (a grep of `tests/` for "screenshot" found only the ones above).
- I did not send a live task through the router to see Codex chosen for the two real briefs (task-ae536649, task-084a5227); the proof is at the `needs_claude_tool` level, not the end-to-end `router:` line.
- Real Claude-only screenshot briefs that used only the bare word will now be tried on Codex/agy first and may fail there (one wasted run, recorded as a runner_fit fail).

## Skill learning
- MISSING [no owner] : `mcp__org__wiki_read` returns `wiki 'org' not available in this environment` for a Contabo developer worker, so the "read wiki first" rule cannot be followed through the tool; the files are on disk at `/opt/MoonieXHQ/Agents/Rules/` and `/opt/MoonieXHQ/Agents/Wikis/`, but `roles/developer.md` is not there · evidence: task-9823c1e3 (wiki_read org:IRON-RULES.md)
- MISSING [CXO_Protocol_DevSpawn §brief template] : the shared worker conventions say "Never `git push`" while the delegated brief says "Commit and push"; the worker has to guess which wins and flag it · evidence: task-9823c1e3 Issues / Blockers
- COSTLY  [no owner] : the Bash hook that blocks a `cd` out of the worktree refused a one-line `cd /opt/MoonieXHQ/Agents/Rules && ...` read; absolute paths with `wc`/`grep` were the fix, one wasted call · evidence: task-9823c1e3 · prevented by: shared conventions say "use absolute paths for wiki reads on disk"
