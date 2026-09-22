---
name: cto-merge-checklist
owner: CTO
origin: mooniex-org
scope: >-
  Pre-merge gate only. Verifies a DEV branch before merge_task and refuses if any
  gate fails. Does not perform the merge, review code line-by-line, or resolve
  conflicts.
description: Pre-merge verification gate — refuses merge_task if any check fails. Trigger on /cto-merge-checklist and whenever about to call merge_task, or the user says "merge", "ship", "land", "approve", "close out" a task.
created_by: human
audience: [cto]
---

# CTO Merge Checklist

Run these gates before `merge_task(task_id)`. **Refuse merge if any gate fails.** Output a one-line pass/fail per gate, then the verdict.

## Required gates

### 0. Dirty base — park another session's WIP without touching it (born 2026-09-22, hit twice in one evening)
`merge_task` refuses when the base checkout has uncommitted changes (`merged: false · base_dirty: true`). Those files are almost always **another live session's work**. Never `git checkout --`, never bare `git stash`, never commit them for the owner.
- [ ] Identify the owner if you can (`git log -1 -- <path>`, mtime, the org logs). Not yours → it is data, not an obstacle.
- [ ] **Fingerprint before you move anything**: `git diff -- <path> > <scratch>/wip.patch && md5 -q <path>`.
- [ ] Path-limited, tagged stash: `git stash push -m "<sid>-<slug>" -- <path>` (untracked dirs the branch does not touch are ignored by the pre-flight and need no stash).
- [ ] `merge_task`, then `git stash apply <sha from git stash list --format='%H %gs'>` — **apply, not pop** — and `md5 -q <path>` must equal the fingerprint. Only then `git stash drop stash@{n}` (re-find n by tag; the stack is shared with every other session and worktree).
- [ ] Tell the owner what you did, with the md5. Two sessions did this round-trip on `tests/test_flow_shoot.py` on 2026-09-22 and both fingerprints matched — that line in the message is what lets them not worry.
- A file that is a **config the org runs on** (`claude-home/settings.json`, a model default, a remote) goes to the CEO, not into anyone's commit — the 2026-09-22 case was a harness-written model switch nobody had chosen.
- If `merge_task` instead says *"branch is already an ancestor of main — refusing to report success"*, that is not a dirty-base problem: the branch carries nothing to land (a worker whose deliverable lived outside the repo). Close the task honestly rather than forcing a no-op merge to look like one.

### 1. DEV report present + structured
- [ ] Report includes: files changed, tests run, blockers.
- [ ] Status is `done` (not `failed`, not `conflict`, not `in_progress`).
- If `failed` → do NOT merge. Investigate first (memory: never auto-merge failed task).

### 2. Tests green
- [ ] All tests DEV ran passed. Quote the output count.
- [ ] No tests skipped/xfailed without justification.
- If tests fail → reopen task with feedback, do not merge.

### 3. Path conflicts cleared
- [ ] No in-flight task locks the same paths (`check_collisions(project, touches)`).
- [ ] If this task had `depends_on`, all parents are merged (not just done).

### 4. Acceptance criteria met
- [ ] Re-read the original task description.
- [ ] Each criterion has explicit pass evidence in the DEV report.
- [ ] No "should also do X" creep — only what was asked.

### 4b. A guard must be ON THE PATH, not merely present — born from EP52, 2026-09-19
Applies whenever the task adds a limit, gate, precheck, budget, lock or kill-switch.
- [ ] Name the entry point a real run uses (`scripts/<x>.js`, the cron, the route), and trace from it to the guard. Paste the call chain into the gate output.
- [ ] `grep` for the guard and check which FUNCTION each hit sits in, not just which file:
      `awk '/^async function |^function /{fn=$0} /<guardName>/{print NR": "fn}' <file>`
- [ ] A test that calls the guard directly proves the guard works. It does not prove the guard runs. The test must enter through the same door production does.
- If the guard is only on a legacy or unused path → REOPEN. The branch is not wrong, it is inert.

Why this is a gate: task-2329c6ce added `EP_BUDGET_USD` with `assertBudget()` blocking before the crossing call, three call sites, tests green, 1178 passing. I reviewed the blocking logic and passed it. All three call sites were inside `processVideoProject()` — the old Notion-cron flow. The path a run actually takes is `resume-video.js → stage-runner → runTTS/runScenePrompts/runLipsync`, and those had none. The ceiling I had told the CEO was protecting a live $2 run would never have fired. A DEV found it on the first real run, before any money moved. One `awk` over the file would have caught it at review.

### 5. No GH blocker issue open
- [ ] If DEV opened a GH issue mid-task, confirm it's closed or explicitly deferred.
- [ ] Memory rule: GH issue on every blocker — closed means real fix, not "ignored".

### 6. Wiki updates queued (if applicable)
- [ ] If task changed architecture/decisions → ADR drafted for `decisions/` (don't gate merge on this, but flag).

### 7. External-State Gate (side-effect tasks) — born from the 2026-06-10 TraderMindset double-post
Applies when the task's deliverable touches anything OUTSIDE the repo: DB writes, social posting, payments, deploys, emails, file uploads.
- [ ] Query the external system (prod DB / page / provider) for evidence of **prior execution** and paste the result into the gate output. A commit proves authorship — **never execution**.
- [ ] Orphan/dead-DEV recovery: default = **assume already executed** until the external query proves otherwise (reverse of the natural default).
- [ ] "Idempotent" claims: verify the idempotency KEY is stable across reruns (run-date-stamped titles/keys are NOT idempotent across days). State the key in the gate output.
- [ ] Any go/no-go question sent to the CEO may contain **only verified facts**; remaining assumptions must be labeled "ยังไม่ได้เช็ค" explicitly.
- If the external query cannot be run (no creds/access) → HOLD, do not guess.

### 8. Repetition → script (born from the 2026-08-12 Higgsfield wave)
Applies to any task whose report shows the **same operation performed more than 3 times** — browser_operator especially, but any role.
- [ ] The report's `## Replay Script` section names a real path, not `none`.
- [ ] **`python3 tools/check_replay_script.py <that path>` exits 0.** It compiles the file (py_compile / node --check / bash -n) and refuses comment-only files. A path that exists is not the test — on 2026-09-19 a 128-line prose `.js` was delivered as the script (cc16c251). IRON-RULES §53.
- [ ] The script covers the mechanical steps; only genuine judgement calls are left to a model.
- If it says `Replay Script: none` → **REFUSE the merge** and reopen asking for the script. The one accepted exception is the operator stating in writing which specific step cannot be scripted and why.
- Why this is a gate and not a suggestion: `roles/browser_operator.md` and `dev-spawn-protocol` §3c.8 already required the script, and both were satisfied by writing `none`. On task-cda4f469 that cost roughly 5 model turns per clip across 20 near-identical clips. A rule with an opt-out phrase is not a rule.

## Output format

```
Gate 0 (Dirty base)           : PASS — clean / parked <path> md5=… restored identical / N/A
Gate 1 (DEV report)           : PASS — status=done, files=N, tests=ok
Gate 2 (Tests green)          : PASS — 113 passed, 0 failed
Gate 3 (Path conflicts)       : PASS — no overlap with in-flight
Gate 4 (Acceptance criteria)  : PASS — all 3 criteria met
Gate 4b (Guard is on the path) : PASS — resume-video.js -> stage-runner -> runTTS -> assertBudget / N/A — no guard added
Gate 5 (GH blockers)          : N/A — none opened
Gate 6 (Wiki ADR)             : DEFERRED — no arch change
Gate 7 (External state)       : PASS — queried claudeflow_posts: 0 prior rows / N/A — repo-only task
Gate 8 (Repetition → script)  : PASS — scripts/browser/<slug>.js / N/A — ≤3 repetitions

Verdict: MERGE  /  REOPEN with feedback  /  HOLD pending <reason>
```

## Operating rules

- **Never paraphrase the gate as passed without evidence.** Quote the DEV report.
- **One iteration of feedback is normal, three is a smell.** If DEV is on iteration 3, escalate to CEO instead of looping further.
- **Cross-project dependencies** — DEVs never reach across projects. If gate 3 reveals one, refuse and rewrite scope.
- **Merges are the CTO's call on every repo** (CEO 2026-09-19: "Coding คือหน้าที่คุณ เห็นสมควรจัดการได้เลย ฉันมีหน้าที่วางแผน"). A gate-clean PR is merged and reported in one line — never "ขออนุมัติ merge". Spend, prod deploys, migrations and secrets keep their own gates; those are consequences, not code decisions.
