---
name: jules-ops
owner: CTO
origin: mooniex-org
scope: >-
  Dispatching repo-only, test-verifiable work to Jules (Google's async coding
  agent, included in the CEO's Google AI Ultra plan) and reviewing what comes
  back. Measured on the first two sessions, 2026-09-18/19.
description: >-
  How the org uses Jules — which work qualifies, the 7-line brief that keeps it
  disciplined, the API calls (create with AUTO_CREATE_PR, read the diff without
  a browser), and the review pipeline (script gates first, then Opus 5). Trigger
  on /jules-ops, "Jules", "jules.google.com", "ส่งให้ Jules", "งานให้ Jules",
  "Google coding agent", or when a C-level is about to spawn a `developer` for
  a bounded repo-only task whose verdict is a command exiting 0 — use this
  instead of a local DEV for that class of work. Not for anything that needs a
  browser, winbox, tmux, tasks.db, LINE, secrets, deploys, or human taste.
created_by: human
audience: [cxo]
---

# Jules ops — dispatch + review

**What it is.** An async coding agent on Google's cloud: give it a repo + a
brief, it clones into its own VM, edits, runs tests, and pushes a branch
`<slug>-<sessionId>` + opens a PR. It never merges. Plan "Jules in Ultra":
300 sessions/day; concurrency not shown. Composer models: `Gemini 3.1 Pro`
(default) and `Gemini 3.6 Flash`.

**Why the org uses it.** Zero Mac RAM, zero Claude quota, survives the Mac
sleeping. The binding constraints of this org are all three.

## 1. What qualifies — all four must hold

1. Repo is on GitHub, the Jules app can see it, **and it is on the dispatch
   allowlist** `config/jules.yaml` (CEO 2026-09-23: the app may SEE every repo;
   what it may WORK on is decided by us, per repo). The dispatch path must refuse
   any repo not listed and the review gate must reject a PR from an unlisted repo —
   **not yet enforced in code** (2026-09-23: `tools/jules_batch.py` takes any
   `--repo`; the check belongs in `tools/jules.py`, which the A/B batch is building).
   Until then the dispatcher checks the file by hand. Visibility is not permission —
   Jules can read Agents-Memory; nothing ever dispatches to it.
2. The verdict is a command that exits 0 (tests, lint, build) or a diff a
   script can validate. "Looks right" is not a verdict.
3. Nothing under deploy scripts, `.env`/secrets, auth, payments, or prod data.
4. Bounded: ≤ ~10 files, one repo, no cross-repo reasoning.

Good: CI/toolchain fixes with a known lead · dependency bumps with tests ·
lint / link / wiki-lint · tests for existing behaviour · rename or migrate
call sites · docs generated from code · small refactors under coverage.
Bad: design decisions · anything needing Higgsfield/Flow/LINE/winbox ·
anything the org DB or tmux is part of · brand/content · "make it better".

## 2. The 8-line brief — the discipline lives here, not in the model

Measured: the first session (Gemini 3.1 Pro, brief without lines 2/3/7) found
the right root cause in 15 min and then shipped a 1.1 MB change set with 3
scratch patch files, 5 scratch scripts, six 7,593-line logs, an unrequested
`nock` bump and an edit to a test to fit its VM — and ended with a question,
no PR. The second session, same model, brief with all seven lines: four
one-line changes, one PR, 2,996 bytes.

```
1. GOAL as the command that must pass       ("`npm test` green on Node 20 in CI")
2. FILES you may touch (name them)          + "no other file"
3. FORBIDDEN: scratch/log files, dependency or lockfile edits, test edits
   (unless the task IS tests), skipping/loosening tests
4. KNOWN LEAD / why the previous attempt was rejected
5. ENV NOTE: "failures caused by your VM lacking ffmpeg/a package → report,
   do not fix; CI installs them"
6. DELIVERABLE: one PR, title given, description = root cause + files
7. FACTS, NOT GUESSES: every claim in the PR body cites the command output or
   file:line that proves it; anything you could not establish is written as
   "unknown — not verified", never guessed (CEO 2026-09-23: "ห้ามเดา")
8. "No questions needed; proceed."
```

Model: **Gemini 3.6 Flash for every session** (CEO 2026-09-23: "3.6 Flash
เก่งกว่า 3.1 Pro"). 3.1 Pro only when a *measured* Flash failure on that class of
task says so — record the failure first; never switch on a hunch.
**The API cannot choose the model** (measured 2026-09-23: `POST /sessions` with
`model`, `modelId` or `agentModel` → `400 Unknown name … Cannot find field`; a
session's GET carries no model field). Which model an API session runs on is
unknown — not verified; write it that way in every ledger and report until the
web settings or a session's own report proves it.

## 3. API — never the web UI for dispatch

Key: `~/.config/mooniex/jules.env` → `JULES_API_KEY` (registered in
`mooniex:playbooks/api-key-registry.md`; load with `set -a; . <file>; set +a`
so the value never appears in a command). Base
`https://jules.googleapis.com/v1alpha`, header `X-Goog-Api-Key`.

```bash
# create — automationMode is what makes a PR appear at all
POST /sessions {"prompt":..., "title":..., "sourceContext":{"source":"sources/github/PASAKON/<repo>",
  "githubRepoContext":{"startingBranch":"main"}}, "automationMode":"AUTO_CREATE_PR", "requirePlanApproval":false}
GET  /sessions/{id}                       # state, outputs[].pullRequest.url, outputs[].changeSet
GET  /sessions/{id}/activities?pageSize=100   # agentMessaged = its questions/report;
                                              # artifacts[].changeSet.gitPatch.unidiffPatch = cumulative diff
```

Traps: a UI-created session has no automation mode → it ends with a diff and
no PR. `:sendMessage` on a COMPLETED session returns **404** — a finished
session cannot be re-instructed; open a new one carrying the rejection
reasons (line 4). The web session page is browser work: reading it from a
C-level tab counts against IRON §42.

## 4. Review pipeline — script gates, then one model pass

Gates a script answers for free (they caught 4 of 5 defects on session 1):
- changed files ⊆ allowed files (exactly the org's touches check)
- no `*.log`, `patch_*`, `test_*.js` at repo root, no `package*.json` /
  lockfile changes unless line 2 allowed them
- diff size cap (the good session was 3 KB; the bad one 1.1 MB)
- PR body names the root cause and the files
- verdict command run locally on the pinned runtime **with CI's own env values**
  (copy the `env:` block from the workflow; never the repo's `.env`) when CI is
  unavailable: `npx --yes -p node@20 -c '<test script>'` — flags before the file
  list. Measured 2026-09-19: cfoTrack passed 5/5 with `.env` on Node 20 and 26
  and failed on both with CI's dummy env — the failure was env-specific, and a
  local run with `.env` had wrongly cleared it as "VM-only" for a whole review

Then one model reads the packet (brief + facts + `diff --stat` + diff, logs
truncated). Blind A/B on session 1's diff, answer key of 5 defects:

| | Sonnet 5 | Opus 5 |
|---|---|---|
| verdict / 5-of-5 | REOPEN / ✓ | REOPEN / ✓ |
| beyond the key | — | +2 (test edit *masks* failures; dead env-order bug) |
| tokens / wall | 107k / 110 s | **92k / 43 s** |

Second data point (PR #211, a 3-line clean fix): Opus 5 alone → MERGE + two
non-blocking nits (partial run output in the PR body; a pre-existing unguarded
env restore), and it correctly argued *against* a source-side fix because prod
stores the key under the second name — 77k tokens / 87 s.

**Use Opus 5 (xhigh) for every Jules PR review** — deeper and, on both
diffs so far, no more expensive than Sonnet. Merge is a human/CTO act after the checklist
(`cto-merge-checklist`); Jules PRs into prod-adjacent repos (claudeflow,
webapp) need the CEO's per-repo OK like any other merge.

## 5. Guardrails without GitHub Pro

Branch protection and rulesets both return 403 on private repos under the
free plan (measured 2026-09-19); the CEO declined Pro. So: least-privilege
repo access (§1.1) · Jules never merges by design · a watchdog tripwire that
alerts when `main` HEAD's author is outside the allowlist · the app is
uninstallable in one click and every push carries its session id.

## 6. Outcome of the first job (2026-09-19)

"CI red since 2026-07-19" on MoonieX-ClaudeFlow, three sessions, ~2 h wall:
#1 right test, wrong discipline (reopened) · #2 hygiene PR #210 · #3 the real
cause, PR #211 — the test's telemetry-off setup deleted `SUPABASE_SERVICE_ROLE_KEY`
while CI sets `SUPABASE_SERVICE_KEY`, so a real POST leaked into the next test's
one-shot nock interceptor. Merged; main on Node 20 with CI's env 1,150/1,150.
The CTO's own mis-call ("VM-only", from a local run with `.env`) cost one
session — hence the §4 rule about CI's env block.

## 7. Not-yet-measured

Concurrency limit · Flash-tier quality · whether `sendMessage` works on an
IN_PROGRESS session · Jules behaviour when CI is blocked (2026-09-19: GitHub
Actions were suspended for billing — "recent account payments have failed or
your spending limit needs to be increased" — and Jules correctly reported it
rather than faking a green).

## Field notes

- 2026-09-23 [SUPERSEDED] §1.1 — "least privilege: keep the app on 2–3 repos, never 'all'" · evidence: replaced by the CEO's ruling 2026-09-23 (visibility may be all; permission = the dispatch allowlist in config/jules.yaml) · status: superseded
- 2026-09-23 [SUPERSEDED] §2 Model — "3.1 Pro for find/diagnose; 3.6 Flash for apply exactly this" · evidence: CEO ruling 2026-09-23 "3.6 Flash เก่งกว่า 3.1 Pro"; Pro only after a measured Flash failure · status: superseded
- 2026-09-23 [WRONG] §1.1 — 8e226a93 wrote "the dispatch path refuses any repo not listed"; no code did (`tools/jules_batch.py create` takes any `--repo`) · evidence: tools/jules_batch.py:66-73 · fix: body now says "must refuse — not yet enforced", check belongs in tools/jules.py · status: pending
- 2026-09-23 [MISSING] §2 Model — the v1alpha API has no model field: `POST /sessions` with `model`/`modelId`/`agentModel` → 400 "Unknown name … Cannot find field" (control without the field → 404 on the bogus source); GET sessions return no model key · evidence: probe from session cto-0e8d80b8 · fix: body says which model an API session runs on is unknown — not verified · status: pending
