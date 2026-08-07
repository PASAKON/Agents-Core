---
name: cto-merge-checklist
owner: CTO
origin: mooniex-org
scope: >-
  Pre-merge gate only. Verifies a DEV branch before merge_task and refuses if any
  gate fails. Does not perform the merge, review code line-by-line, or resolve
  conflicts.
description: Pre-merge verification gate — refuses merge_task if any check fails. Trigger on /cto-merge-checklist and whenever about to call merge_task, or the user says "merge", "ship", "land", "approve", "close out" a task.
---

# CTO Merge Checklist

Run these gates before `merge_task(task_id)`. **Refuse merge if any gate fails.** Output a one-line pass/fail per gate, then the verdict.

## Required gates

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

## Output format

```
Gate 1 (DEV report)           : PASS — status=done, files=N, tests=ok
Gate 2 (Tests green)          : PASS — 113 passed, 0 failed
Gate 3 (Path conflicts)       : PASS — no overlap with in-flight
Gate 4 (Acceptance criteria)  : PASS — all 3 criteria met
Gate 5 (GH blockers)          : N/A — none opened
Gate 6 (Wiki ADR)             : DEFERRED — no arch change
Gate 7 (External state)       : PASS — queried claudeflow_posts: 0 prior rows / N/A — repo-only task

Verdict: MERGE  /  REOPEN with feedback  /  HOLD pending <reason>
```

## Operating rules

- **Never paraphrase the gate as passed without evidence.** Quote the DEV report.
- **One iteration of feedback is normal, three is a smell.** If DEV is on iteration 3, escalate to CEO instead of looping further.
- **Cross-project dependencies** — DEVs never reach across projects. If gate 3 reveals one, refuse and rewrite scope.
- **Memory:** Agents meta-repo auto-commit+push is allowed; other projects need explicit confirmation per repo.
