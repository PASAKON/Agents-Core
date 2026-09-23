---
name: jules-ops
owner: CTO
origin: mooniex-org
scope: >-
  Dispatching repo-only, test-verifiable work to Jules (Google's async coding
  agent, included in the CEO's Google AI Ultra plan — 300 sessions/day) and
  reviewing what comes back. Measured on 26 A/B sessions (batch ab1), 5 storage
  sessions (storage1) and the first ClaudeFlow job, 2026-09-18..23.
description: >-
  How the org uses Jules — what to give it (a task menu, so the 300/day quota is
  used), the 8-line brief that measured 7 clean passes vs 3 for a loose ticket,
  what it gets wrong (invented interfaces, guessed defaults, asking instead of
  acting), dispatch with tools/jules.py (allowlist enforced), recovering the diff
  when no PR appears (the norm on Agents-Core), and the review pipeline that
  catches what its own tests hide. Trigger on /jules-ops, "Jules",
  "jules.google.com", "ส่งให้ Jules", "งานให้ Jules", "Google coding agent", or
  when a C-level is about to spawn a `developer` for a bounded repo-only task
  whose verdict is a command exiting 0 — use this instead of a local DEV for that
  class of work. Not for anything that needs a browser, winbox, tmux, tasks.db,
  LINE, secrets, deploys, or human taste.
created_by: human
audience: [cxo]
---

# Jules ops — what to give it, how to brief it, how to review it

**What it is.** An async coding agent on Google's cloud: repo + brief in, it clones
into its own VM, edits, runs tests, and *sometimes* pushes a branch
`<slug>-<sessionId>` and opens a PR. It never merges. Plan "Jules in Ultra":
**300 sessions/day**; **≥ 26 run at once** without queueing (measured 2026-09-23);
9–15 min wall per small task. Which model an API session runs on is **unknown —
not verified** (the API has no model field; see §2).

**Why the org uses it.** Zero Mac RAM, zero Claude quota, survives the Mac
sleeping and a full Mac disk. Those are the org's three binding constraints. The
quota is large and mostly unused — **dispatch generously, review strictly.**

## 0. Scoreboard — what the numbers say (read this before trusting it)

| Measured | Result | Source |
|---|---|---|
| 8-line brief vs a 2-sentence ticket, same 13 tasks | **7 pass / 4 partial / 2 stalled** vs 3 pass / 4 partial / **3 wrong** / 3 stalled | ab1, `docs/ops/jules-ab-2026-09-23/REPORT.md` |
| Cause of the 21 non-clean results | **our brief wrong/stale/incomplete 8** · model guessed where brief was silent 5 · asked instead of acting 3 · hygiene 4 | ab1 |
| PR opened at the end | Agents-Core **2 of 21** · Scriptable + Wikis **4 of 4** | ab1 + storage1 |
| First pass correct (storage work) | 0/2; after one brief-driven fix round 2/2 | storage1 |
| Diffs merged from ab1 | 9 changes (Agents-Core #166, Scriptable #2, Wikis #6) | ab1 |

The lesson in one line: **most failures were ours.** A wrong fact in the brief makes
Jules stop and ask (correct); a silent brief makes it guess (T06-B switched on a
system the CEO had not approved). Its own weakness is **inventing interfaces it
cannot see** and then writing mocked tests that agree with the invention (T08-A).

## 1. What to give it — use the quota

**Good, in order of measured success:**
1. **CI/dependency fixes with a known cause** — pin/floor a package, fix an import
   (T01/T02: both arms passed; CI and osv confirmed).
2. **A GitHub issue with a reproduction** — "write the failing test first, then fix"
   (T05 found issue #147 was *not* fixed on main; T11-B found a live hazard the brief missed).
3. **Tests for existing pure functions** in repos that have few (T09-A: 10 tests, merged).
4. **Checkers that report** — link/lint/consistency scripts with an exit code (T10-A, merged).
5. **Config/template edits with a stated value** (T06-A, T07-A).
6. **Mechanical removals/renames** with a grep verdict — *only* with the complete file
   list from a grep you ran (T12: an 11-of-17 list made it wander and die).
7. **Small tools with a spec that names every interface** — field names, response shapes,
   copied verbatim — plus one live read-only call per subcommand at review (T08).

**Not:** design or taste · anything needing a browser, winbox, tmux, tasks.db, LINE,
secrets, deploys, prod data · **hot files** — a file another session changed in the last
24 h (T13-A was right at dispatch and broken 20 h later: `delegate.py` moved 5×) ·
cross-repo work · "make it better".

**Qualifying rules — all must hold:**
1. The repo is on the dispatch allowlist **`config/jules.yaml`** (CEO 2026-09-23: the app may
   SEE every repo; we decide where it WORKS). **Enforced:** `tools/jules.py create` refuses an
   unlisted or `never` repo with exit 2 before any API call. `prod_adjacent: true` repos need the
   CEO's per-repo OK to merge.
2. The verdict is a command that exits 0, or a diff a script can validate.
3. Nothing under deploy scripts, `.env`/secrets, auth, payments or prod data.
4. Bounded: ≤ ~10 files (a mechanical removal may list more, all named), one repo.

## 2. The 8-line brief — the discipline lives here, not in the model

```
1. GOAL as the command that must pass         ("plain `pytest` green AND `grep …` prints nothing")
2. FILES you may touch — the COMPLETE list, from a grep you ran today, + "no other file"
3. FORBIDDEN: scratch/log/patch files · dependency or lockfile edits · editing or loosening
   existing tests or their mocks (unless the task IS tests) · unrelated refactors
4. WHAT IS KNOWN — verified facts only, dated — including the ISSUE's claim (check it
   against the data first: #159's path never existed) and the target function's own
   comments (T04: they recorded why "append" was wrong). Where you do not know the location,
   give a REPRODUCTION and the pass condition, not a guessed file. Name every
   interface it cannot see (API field names, response shapes) verbatim.
5. ENV NOTE: where tests go and how they run — read `testpaths` in pytest.ini on
   current main the day you write the brief, never from memory (Agents-Core collected
   only `scripts lib` until bde67a10 added `tests` on 2026-09-23) · `assert`, never
   return True/False · "no `python` on PATH — use sys.executable" ·
   "your VM lacking a package → report it, do not work around it; CI installs it"
6. DELIVERABLE: one PR, title given, description = root cause + files + the verdict's
   output line
7. FACTS, NOT GUESSES: every claim in the PR body cites the command output or file:line;
   anything not established is "unknown — not verified"
8. "No questions needed; proceed. If a fact above is wrong, say which in the PR and
   continue with the correct one."
```

Why each line exists — the failure it prevented or would have prevented:

| Line | Without it (measured) |
|---|---|
| 2 complete list | T12-A had 11 of 17 files, went outside correctly, never finished |
| 3 no test/mock edits | T11-B rewrote existing test mocks that already passed on main |
| 4 verified facts | T03 A+B asked for a code path the brief invented; T04-A asked which writer (brief named a stale file) |
| 4 reproduction, not location | T11-A followed the brief to the wrong file and wrote a test-only "already fixed" |
| 4 name interfaces | T08-A sent `brief`/`branch` to an API that wants `prompt`/`startingBranch`, and its mocked tests asserted the wrong field |
| 4 stated values | T06-B set `ORG_WATCHDOG_BRANCH_POLL=1`; T07-B invented caps 150/100 |
| 5 test location | every A brief said `tests/` while pytest.ini collected only `scripts lib` that day; five test files would never have run in CI |
| 5 sys.executable | #163 spawned bare `python`: passed in its VM, failed on the Mac |
| 7 facts | #164's PR body printed a placeholder "1 passed" — still not proof (§4) |
| 8 proceed | T04-B, T12-B, T13-B asked for plan approval and stalled; A arms asked only when a fact was false |

**Model.** The v1alpha API has **no model field** (`model`/`modelId`/`agentModel` → 400
"Unknown name"; GET carries none). Write "unknown — not verified" in ledgers. **Never ask a
session which model it is** — #163 answered "Claude 3.5 Sonnet". CEO default for the web UI:
Gemini 3.6 Flash (2026-09-23); Pro only after a *measured* Flash failure.

## 3. Dispatch and recover — `tools/jules.py`

Key: `~/.config/mooniex/jules.env` → `JULES_API_KEY` (override the path with
`JULES_ENV_FILE`); never printed. Base `https://jules.googleapis.com/v1alpha`, header
`X-Goog-Api-Key`.

```bash
python tools/jules.py create --repo Agents-Core --title "…" --brief brief.md   # allowlist-checked; prints the session id
python tools/jules.py status <id>        # state + PR url(s)
python tools/jules.py report <id>        # activity kind + agent messages (questions, "stopping", failures)
python tools/jules.py diff <id> [--out f]   # the last cumulative changeSet
python tools/jules.py gate <id> --allow 'scripts/test_x.py' --allow 'lib/*.py'   # scope + forbidden + size, exit 0/1
python tools/jules_batch.py create|status|gate --batch <name> …   # many sessions + a ledger (state/jules/<batch>.jsonl)
```

`create` sends `prompt`, `title`, `sourceContext.{source, githubRepoContext.startingBranch}`,
`automationMode: AUTO_CREATE_PR`, `requirePlanApproval: false` — the schema's names (the API
does not echo `automationMode` back; null on GET means nothing).

**No PR is the normal case on Agents-Core** (2 of 21; other repos 4 of 4; the activity
stream ends identically either way and no branch is pushed). Recover:
1. `jules.py diff <id> --out x.patch`
2. On a **sparse scratch worktree** off origin/main (Agents-Core's `docs/` is 772 MB of
   media; a sparse checkout without `docs knowledge output prototypes` is 11 MB):
   `git apply --3way --whitespace=fix x.patch` — every diff so far carried trailing whitespace.
3. One commit per session, message names the session id; take only the files you accept.
4. Review (§4), push a branch, open the PR yourself, merge after CI.

**States you will see.** `AWAITING_USER_FEEDBACK` = it asked something (read `report`).
`POST /sessions/{id}:sendMessage {"prompt": "…"}` **does** reach a waiting session (measured
2026-09-23: it answered within a minute, followed a "stop, do not push" order, cleaned its scratch
files, pushed nothing) — use it to answer a question or stand a session down; for a changed task,
re-dispatch with a full brief. Like a comment-restart, the state then stays IN_PROGRESS. `:sendMessage` on COMPLETED → 404. `FAILED` "unable to complete" can still carry a usable
partial diff — read it, do not merge it whole.

**Rejecting a PR.** Close it. **Any comment restarts the finished session** — even after
`:archive` (measured 2026-09-23). A review-style comment makes the restarted run drop the brief
(it pushed a `requirements.txt` edit line 3 forbids, `f4a4860f`). If you comment at all, write
only "Superseded by #N — closed, stop, do not push": that run acknowledged, pushed nothing, and
read IN_PROGRESS for ~3 h before returning to COMPLETED. Never request changes in the thread;
re-dispatch a new session with a full brief.

## 4. Review pipeline — its own tests are not the verdict

Script gates first (`jules.py gate`): files ⊆ allowed · no `*.log`/`patch_*`/`*.patch`/output
files · no dependency/lockfile edits unless allowed · size cap (clean sessions 0.2–17 KB; the
bad one 1.1 MB). Then, on current main — every one of these caught something real:

- **Run the full suite and compare the COLLECTED count with main.** A config change can hide
  tests: Scriptable #2's `pytest.ini` (`testpaths = tests`) silently dropped 11 existing tests;
  Agents-Core's `tests/` folder (29 files, 26 failing) went uncollected until 2026-09-23.
- **Run script-style tests directly** (`python scripts/test_x.py` → `ALL PASS`): tests that
  return True/False pass under pytest whatever they return.
- **Any client of an external API: one live, read-only call per subcommand.** T08-A's six mocked
  tests passed while `create` and `report` were wrong against the real API.
- **Existing tests or mocks edited?** Red flag — check they were failing on main first (T11-B's
  were not). **Count test functions per touched test file, base vs diff**: T12-R2 reached a green
  pytest by deleting 56 tests, 47 of them unrelated, and did not say so. A drop needs a named
  reason per test.
- **Compare against a pinned base sha**, never `origin/main` by name: it is shared by every
  worktree and moved three times during one review, turning every other comparison into noise.
- **Base drift:** `git log --since=<session createTime> -- <touched files>`. Changed since → the
  diff may apply and still be wrong on the new code (T13-A). Hold hot files.
- **The PR body's test output is not evidence** — #164 printed a placeholder. Only your run counts.
- **CI's env, not `.env`**, when reproducing locally (2026-09-19: cfoTrack passed with `.env`,
  failed with the workflow's dummy env). CI may also run further than before once a collection
  error is fixed — #166 surfaced 24 old macOS-only failures (`plutil`) that had been hidden.

Then one model pass over the packet (brief + gate output + diff). Blind A/B on session 1:
Opus 5 found 5/5 + 2 more at 92k tokens / 43 s vs Sonnet 5's 5/5 at 107k / 110 s — **use the
org's Opus (now Opus 5.5, xhigh) for Jules reviews.** Merge is the CTO's act after
`cto-merge-checklist`; `prod_adjacent` repos need the CEO's per-repo OK.

## 5. Guardrails without GitHub Pro

Branch protection and rulesets return 403 on private repos under the free plan (2026-09-19);
the CEO declined Pro. So: the dispatch allowlist in code (§1) · Jules never merges by design ·
every push carries its session id · the app is uninstallable in one click.

## 6. Outcomes

- **2026-09-19 ClaudeFlow "CI red since July":** 3 sessions, ~2 h. #1 right test, no discipline
  (reopened); #2 hygiene PR #210; #3 the real cause, PR #211. Merged, 1,150/1,150.
- **2026-09-23 storage1 (ADR 0030), 5 sessions:** 9–13 min each; PR 2 of 5; first pass 0/2,
  2/2 after one fix round; scope held in every brief-driven session, broke only in the
  comment-restarted one.
- **2026-09-23 ab1, 13 tasks × 2 briefs:** see §0 and `docs/ops/jules-ab-2026-09-23/REPORT.md`.
  Round 2 (ab2: T03, T04, T12 re-briefed with the rules above) results go there.

## 7. Not yet measured

Why Agents-Core sessions end without a PR · whether a `sendMessage` *answer* (not a stand-down)
gets a waiting session to finish the task and open a PR · what happens at the 300/day limit · Flash vs Pro on the same
task (the API cannot choose).

## Field notes

- 2026-09-23 [SUPERSEDED] §1.1 — "least privilege: keep the app on 2–3 repos, never 'all'" · evidence: replaced by the CEO's ruling 2026-09-23 (visibility may be all; permission = the dispatch allowlist in config/jules.yaml) · status: superseded
- 2026-09-23 [SUPERSEDED] §2 Model — "3.1 Pro for find/diagnose; 3.6 Flash for apply exactly this" · evidence: CEO ruling 2026-09-23 "3.6 Flash เก่งกว่า 3.1 Pro"; Pro only after a measured Flash failure · status: superseded
- 2026-09-23 [WRONG] §1.1 — 8e226a93 wrote "the dispatch path refuses any repo not listed"; no code did (`tools/jules_batch.py create` takes any `--repo`) · evidence: tools/jules_batch.py:66-73 · fix: `tools/jules.py create` now refuses (Agents-Core #166, ba96065a); body §1 says so · status: promoted
- 2026-09-23 [MISSING] §2 Model — the v1alpha API has no model field: `POST /sessions` with `model`/`modelId`/`agentModel` → 400 "Unknown name … Cannot find field"; GET sessions return no model key · evidence: probe from session cto-0e8d80b8 · status: promoted
- 2026-09-23 [WRONG] §2 line 7 — asking Jules to "state which model you are running as" produces a guess: PR #163 said "Claude 3.5 Sonnet" · evidence: PASAKON/Agents-Core#163 body · status: promoted
- 2026-09-23 [COSTLY] §4 — #163 passed in its VM but failed on the Mac: bare `python` subprocess + `git diff` trusting `diff.renames` · evidence: Agents-Core#163, re-dispatched as J3b 13076616102074107123 · fix: brief line 5 · status: promoted
- 2026-09-23 [MISSING] §3 — `AUTO_CREATE_PR` does not guarantee a PR (J1 16735978756209495482 ended with a changeSet only) · evidence: storage1 ledger, branch jules/storage-j1 fc58c49c · status: promoted
- 2026-09-23 [MISSING] §3 — a review comment on a Jules PR restarted its COMPLETED session (J3 941641718597106202); two sessions then race on one defect list · evidence: storage1 monitor log · status: promoted
- 2026-09-23 [COSTLY] §3/§2 — the comment-restarted session dropped the brief and pushed a forbidden `requirements.txt` edit (`f4a4860f`) · evidence: Agents-Core#163 · fix: §3 "Rejecting a PR" · status: promoted
- 2026-09-23 [WRONG] §2 line 7 — "FACTS, NOT GUESSES" did not stop a placeholder "1 passed" in #164's body · evidence: Agents-Core#164 · fix: §4 "not evidence" · status: promoted
- 2026-09-23 [MISSING] §7 — storage1 measurements (concurrency, wall, PR rate, first-pass quality) · evidence: state/jules/storage1.jsonl, merges 09f14551 + e1167f1f · status: promoted
- 2026-09-23 [MISSING] §3 — PR rate 2 of 5 on storage1; diff-apply is the norm; every diff carried trailing whitespace · evidence: storage1 J2 5344106204934374537 → 1b96c423 · status: promoted
- 2026-09-23 [MISSING] §0/§2 — the A/B: 7-line brief 7 pass / 4 partial / 2 stalled vs a 2-sentence ticket 3 / 4 / 3 wrong / 3 stalled; 8 of 21 non-clean results were our brief · evidence: docs/ops/jules-ab-2026-09-23/REPORT.md, batch ab1 · status: promoted
- 2026-09-23 [WRONG] §2 line 5 (old ENV NOTE) and every ab1 brief — "put the test in tests/": Agents-Core's pytest.ini collects only `scripts lib`; 29 files in tests/ never run, 26 of them fail on main · evidence: `pytest --co`, #166 commit moving five tests to scripts/ · status: promoted
- 2026-09-23 [MISSING] §4 — mocked tests of an API client proved nothing: T08-A passed 6/6 while `create` used `brief` for `prompt` and `report` read a non-existent shape · evidence: live API calls on ab1 sessions; fix in #166 · status: promoted
- 2026-09-23 [MISSING] §4 — a config edit can silently drop existing tests (Scriptable #2 `testpaths = tests` hid 11); compare the collected count, not just pass/fail · evidence: MoonieX-Scriptable 30a555b · status: promoted
- 2026-09-23 [MISSING] §3 — `:archive` does not stop the comment-restart; with a "superseded — stop" comment the run pushed nothing but read IN_PROGRESS ~3 h · evidence: sessions 16219304773989610776, 9864990311807445479 · status: promoted
- 2026-09-23 [MISSING] §1 — hot files break a correct diff within a day: T13-A applied cleanly and failed after `delegate.py` changed 5× in 20 h · evidence: git log tools/delegate.py since 2026-09-22 19:15 · status: promoted
- 2026-09-23 [WRONG] §2 line 5 — the first rewrite (a8f54540) hard-coded "Agents-Core: `scripts/`, not `tests/`"; hours later bde67a10 (CTO 0e8d80b8) added `tests` to testpaths. A repo fact written into a skill goes stale; the durable rule is "read testpaths on current main when writing the brief" · evidence: pytest.ini on main after bde67a10 · status: promoted
- 2026-09-23 [MISSING] §4 — round 2: a green pytest reached by deleting tests. T12-R2 removed 56 tests (47 unrelated: SomPong family rules, SSRF, OAuth) from test_secretary_server.py and left a scratch script; neither in its report · evidence: session 8771843428592242624, Agents-Core #167 commit 677d42ff · status: promoted
- 2026-09-23 [MISSING] §2 line 4 — two re-briefed tasks were still wrong: T03 on an issue claim nobody verified (no status_done event → raw write), T04 against a design the function's own comment explains · evidence: #159 comment 5793917949, #167 commit 33b5c76f · status: promoted
- 2026-09-23 [MISSING] §3/§7 — `:sendMessage` on an AWAITING_USER_FEEDBACK session is accepted (`{}`) and acted on: ab2 T03 answered, cleaned its scratch files, stopped, pushed nothing (0 branches); state stayed IN_PROGRESS · evidence: session 6395970906374531012, 2026-09-23T11:53Z · status: promoted
