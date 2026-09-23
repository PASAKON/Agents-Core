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
- **"merged: true" is a local fact, not a pushed one.** Right after every `merge_task`,
  in the project repo: `git fetch -q origin && git merge-base --is-ancestor <merge_sha> origin/main`.
  If it fails, `git push origin main` (after pulling if origin moved, and re-running the
  suite), then re-check. Report the merge only once it is on origin. Promoted from a field
  note on two independent runs with two different causes: origin had moved (task-bfa778ab),
  and a project that never pushes at all (mooniex-console, task-94755874, 0bd1c154 was
  7 commits ahead of origin).
- **Merges are the CTO's call on every repo** (CEO 2026-09-19: "Coding คือหน้าที่คุณ เห็นสมควรจัดการได้เลย ฉันมีหน้าที่วางแผน"). A gate-clean PR is merged and reported in one line — never "ขออนุมัติ merge". Spend, prod deploys, migrations and secrets keep their own gates; those are consequences, not code decisions.

## Field notes

- 2026-09-22 [MISSING] §0 — `merge_task` refused twice in one evening on a dirty base that was another live session's WIP (`tests/test_flow_shoot.py`, then `claude-home/settings.json`); no gate said what to do with it, and the natural moves (checkout, bare stash, commit-for-them) all destroy or misattribute someone's work. Gate 0 added: fingerprint → path-limited tagged stash → merge → apply-not-pop → md5 must match → drop by re-found index; configs the org runs on go to the CEO instead · evidence: sessions cto-a29c7576 + cto-8c06958c, both md5 round-trips matched (ff175ec3…), ADR 0026 · status: promoted
- 2026-09-22 [MISSING] §4b — the awk "which function is the guard in" step passed a branch whose `artefact_gate` had one definition and zero production call sites (only tests called it). The faster, decisive first check is call-site count outside tests: `grep -rn "<guard>(" <src dirs> | grep -v "/tests/" | grep -v "def <guard>"` — empty means inert, reopen · evidence: task-adbc6f43 iteration 1→2, caught before merge · status: pending
- 2026-09-22 [MISSING] §2 — this repo's `pytest.ini` `addopts` already carries `-q`; adding `-q` on the command line makes `-qq`, which drops the final pass/fail summary line — a green run then reads like a hang or a truncated log. Use `-p no:warnings` for less noise, never a second `-q`; count the dots or drop `-q` when you need the summary · evidence: worker task-df0541aa (background run judged "still running" for 30 min) and the CTO's own suite run on main 21:38, same evening · status: pending
- 2026-09-22 [MISSING] §2 — a `os.environ.get(X) or _read_dotenv_var(X)` fallback makes "no key set" tests silently read the real gitignored `.env` and go LIVE; the autouse fixture must monkeypatch the dotenv reader too. The rule now lives in the tool: `tests/conftest.py` autouse fixture neutralises the dotenv reader for every test (opt-out marker `allow_dotenv` for the one test that is about the reader). On review, run the suite with `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1` once — a live call fails loudly instead of passing quietly · evidence: task-a6129a75 (2 unplanned live calls) + main after merging T2 and T1b (tests/test_decide_browser_sites.py made 2 live Jev calls per run, 22:33) — two independent hits the same evening · status: promoted
- 2026-09-23 [MISSING] after merge — `merge_task` returned `merged: true` (merge_sha f335cbf1, no push field in the result) while origin/main had moved (the CTO had pushed Jules merges from a scratch worktree); f335cbf1 was NOT on origin until a manual `git pull --no-rebase origin main` + suite + `git push`. After every merge_task run `git merge-base --is-ancestor <merge_sha> origin/main` — "merged" is a local fact, not a pushed one · evidence: task-bfa778ab, fix pushed as f38daffd; second run task-94755874 (mooniex-console never pushes; 0bd1c154 7 ahead) agreed 2026-09-23, promoted to Operating rules · status: promoted
- 2026-09-23 [MISSING] §2 — a worker may leave its worktree's `node_modules` as a symlink to the main checkout; if that checkout was installed `--omit=dev` (it is also the live Console-Mac deploy dir), the reviewer's `vitest run` dies with ERR_MODULE_NOT_FOUND. Replace the symlink with a real `npm ci` in the worktree before rerunning (merge_task's cleanup removes it) · evidence: task-94755874 review · status: pending
- 2026-09-23 [MISSING] after merge — MoonieX-Console `scripts/console-deploy.sh service` only enables/starts the unit; a RUNNING service keeps the old code (the same pid 1039 before and after, `/api/relay/targets` 404). Deploy = `sync` → `install` → `ssh mooniex-vps systemctl restart mooniex-console` → `verify`, then smoke-test a new route on the canonical `https://terminal.mooniex.com` (not :8443, which 302s) · evidence: task-94755874 deploy 18:1x · status: pending
- 2026-09-23 [MISSING] after merge — when the CTO merges a branch by hand (scratch worktree + push), `merge_task` then refuses as a no-op ("already an ancestor… refusing to report success") and leaves the task in review. Close it with `close_dev` + `lib.db.update_status(id, "done")` and a delegate_log line naming the merge sha, then remove the worktree/branch — never raw sqlite · evidence: task-95439aa8 → d53e2dd2 · status: pending
