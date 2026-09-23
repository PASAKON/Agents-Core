# Jules A/B — batch ab1 (2026-09-22/23): 13 tasks × 2 briefs

CEO ask (2026-09-23): run ~10 small tasks from LungNote + GitHub issues through Jules, A/B the
instructions, and find out how many pass, how many fail, and whether a failure is **our brief**,
**the model guessing**, or something else — then make `jules-ops` stronger.

**Arms.** A = the 7-line brief from `jules-ops` §2 (files allowed, forbidden list, known lead,
env note, deliverable, "no questions"). B = two sentences, the way a busy person writes a ticket.
Same task, same repo, same hour. Briefs in `briefs/`, ledger `state/jules/ab1.jsonl`,
review artefacts `state/jules/ab1-review/`. Model: the account default (the API cannot choose).

## Results

| Task | Source | A (7-line brief) | B (2 sentences) | Why the loser lost |
|---|---|---|---|---|
| T01 pin `mcp<2` | CI red | **PASS** → merged #166 | pass (no rationale comment) | — |
| T02 `anyio` floor | osv | **PASS** → merged #166 | pass (no comment) | — |
| T03 #159 lock leak | GH | stalled: asked where the "remote branch" is | stalled, then FAILED | **our brief**: asserted a code path that does not exist |
| T04 #158.1 reopen→TASK.md | GH | stalled: asked which writer | stalled: asked plan approval (found the right files) | **our brief**: pointed at stale file locations; B = model asks when not told to proceed |
| T05 #147 hook-inbox | GH | **PASS** → merged #166 (issue was NOT fixed on main) | pass (test outside allowlist) | — |
| T06 #155 plist env | GH | **PASS** → merged #166 | wrong: set `ORG_WATCHDOG_BRANCH_POLL=1` | **model guessed**: switched on a system the CEO has not approved |
| T07 browser guard | LungNote | **PASS** → merged #166 | partial: invented its own caps 150/100 | **model guessed** where brief was silent |
| T08 `tools/jules.py` | tooling | partial: `create` used field `brief`, `report` read a shape that does not exist; mocked tests locked both in | FAILED (test errors) | **model guessed** API field names; **our brief** did not name them. Fixed at review, merged #166 |
| T09 first test suite | Scriptable | **PASS** → merged PR #2 (its pytest.ini hid 11 existing tests — fixed) | partial: half scope, wrong folder | loose brief |
| T10 link checker | Wikis | **PASS** → merged PR #6 | partial: committed its own output file | loose brief |
| T11 #65 tab fallback | LungNote/GH | partial: test-only, "already fixed" | **found the real live hazard** in `itermtab.py` (but edited existing test mocks) | **our brief** pointed at the wrong file; B explored. B's fix merged, its test edits dropped |
| T12 remove Z.ai/9Router | LungNote | partial → FAILED: went outside the list (correctly), never finished | stalled: asked to proceed | **our brief**: file list incomplete (11 of 17 files) |
| T13 delegate refuses missing worktree | LungNote | passed at the time; stale now (`delegate.py` changed 5× in 20 h) | stalled: asked plan approval | **base drift** on a hot file |

**Tally.** A: 7 pass · 4 partial · 2 stalled. B: 3 pass · 4 partial · 3 wrong · 3 stalled.
Merged from the batch: 9 changes (A ×7, B ×1 in part, + review fixes) via Agents-Core #166,
MoonieX-Scriptable #2, Agents-Wikis #6.

## Where failures came from (A and B together, 21 non-clean results)

| Cause | Count | Examples |
|---|---|---|
| **Our brief** was wrong, stale or incomplete | 8 | T03 A+B, T04-A, T11-A, T12-A, T08-A (field names), and every A brief said `tests/` — a folder pytest does not collect |
| **Model guessed** where the brief was silent | 5 | T06-B turned a flag on, T07-B invented caps, T08-A invented API fields + an activity shape, T13-B chose a different design |
| **Model asked instead of acting** (no "proceed" line) | 3 | T04-B, T12-B, T13-B — A arms asked only when a brief fact was false |
| **Hygiene** under a loose brief | 4 | output file committed (T10-B), wrong folder (T09-B), existing test mocks edited (T11-B), tests outside scope (T05-B/T07-B) |
| **Platform / env** | — | Agents-Core: 0 of 16 finished sessions opened a PR (Scriptable/Wikis: 4 of 4); T11-B's VM lacked pyyaml; T13 base drift |

**Answer to the CEO's question.** Most failures were **ours**: a brief that states a wrong fact
makes the disciplined arm stop and ask (correct behaviour), and a brief that is silent lets the
loose arm guess (T06-B turned on a system nobody approved). The model's own weakness is
**inventing interfaces** it cannot see — API field names, response shapes — and then writing
mocked tests that agree with its invention (T08-A). The 7-line brief roughly doubled the clean
pass rate (7 vs 3) and eliminated the wrong-but-confident results (0 vs 3).

## Platform facts measured (feed `jules-ops`)
- Concurrency: 26 sessions accepted and ran at once; none refused.
- The API has no model field; `automationMode` is not echoed back.
- Agents-Core: finished sessions end identically to PR-opening ones, but no PR appears and no branch
  is pushed. Workaround: `tools/jules.py diff <id>` → apply → commit per session → PR yourself.
- Closing a PR (with a comment) restarts the finished session even if it was archived; with an
  explicit "superseded — stop" comment the agent stops, pushes nothing, but the session reads
  IN_PROGRESS for ~3 h before returning to COMPLETED.
- Mocked unit tests prove nothing about an API client: `create` and `report` passed 6/6 tests and
  failed against the live API.

## Round 2 (batch ab2, dispatched 2026-09-23 17:43 via the fixed `tools/jules.py`)
T03, T04, T12 re-briefed with verified facts, the reproduction-not-location rule, tests in
`scripts/`, and "if a fact here is wrong, say so and continue". T13 held until `delegate.py`
settles. Results appended when they land.
