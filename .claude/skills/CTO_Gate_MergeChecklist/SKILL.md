---
name: CTO_Gate_MergeChecklist
kind: gate
owner: CTO
aka: [cto-merge-checklist]
origin: mooniex-org
scope: >-
  Pre-merge gate only. Verifies a DEV branch before merge_task and refuses if any
  gate fails. Does not perform the merge, review code line-by-line, or resolve
  conflicts.
description: GATE — Pre-merge verification gate — refuses merge_task if any check fails. Trigger on /CTO_Gate_MergeChecklist and whenever about to call merge_task, or the user says "merge", "ship", "land", "approve", "close out" a task.
created_by: human
audience: [cto]
---

# CTO Merge Checklist

Run these gates before `merge_task(task_id)`. **Refuse merge if any gate fails.** Output a one-line pass/fail per gate, then the verdict.

## Required gates

### 0. Dirty base — park another session's WIP without touching it (born 2026-09-22, hit twice in one evening)
`merge_task` refuses when the base checkout has uncommitted changes (`merged: false · base_dirty: true`): every modified tracked file blocks, even one the branch never touches; an untracked path blocks only when the branch brings that path (`_blocking_dirty_paths` in `tools/git_ops.py`). Those files are almost always **another live session's work**. Never `git checkout --`, never bare `git stash`, never commit them for the owner.
- [ ] Identify the owner if you can (`git log -1 -- <path>`, mtime, the org logs). Not yours → it is data, not an obstacle.
- [ ] **The branch does not touch the file** → you may leave it in place and hand-merge (Operating rules): git refuses only a merge that would overwrite a dirty file. For a log a runner may still be appending to, this is the only safe way — a stash loses the lines written meanwhile.
- [ ] Otherwise **fingerprint before you move anything**: `git diff -- <path> > <scratch>/wip.patch && md5 -q <path>` (`md5` is macOS-only; on Linux/Contabo `md5sum <path> | cut -d' ' -f1`), then a path-limited, tagged stash: `git stash push -m "<sid>-<slug>" -- <path>`.
- [ ] `merge_task`, then `git stash apply <sha from git stash list --format='%H %gs'>` — **apply, not pop** — and the same md5 must equal the fingerprint. Only then `git stash drop stash@{n}` (re-find n by tag; the stack is shared with every other session and worktree).
- [ ] Tell the owner what you did, with the md5. Two sessions did this round-trip on `tests/test_flow_shoot.py` on 2026-09-22 and both fingerprints matched — that line in the message is what lets them not worry.
- A file that is a **config the org runs on** (`claude-home/settings.json`, a model default, a remote) goes to the CEO, not into anyone's commit — the 2026-09-22 case was a harness-written model switch nobody had chosen.
- If `merge_task` instead says *"branch is already an ancestor of main — refusing to report success"*, that is not a dirty-base problem: the branch carries nothing to land (a worker whose deliverable lived outside the repo, or a branch you already merged by hand). Close the task as a hand merge does (Operating rules) rather than forcing a no-op merge to look like one.

### 1. DEV report present + structured
- [ ] Report includes: files changed, tests run, blockers.
- [ ] Status is `done` (not `failed`, not `conflict`, not `in_progress`).
- If `failed` → do NOT merge. Investigate first (memory: never auto-merge failed task).

### 2. Tests green
- **Never add `-q` to the pytest line** — this repo's `pytest.ini` already carries it; a second `-q` (`-qq`) drops the totals line, so a green run reads like a hang and a grep for "passed" finds nothing. Run plain `.venv/bin/python -m pytest <paths>` (add `-p no:warnings` for less noise). Promoted 2026-09-25 after three independent sightings: task-df0541aa (09-22), the T2 review (09-25) and the Run Inbox P1b worker (09-25).
- [ ] All tests DEV ran passed. Quote the output count.
- [ ] No tests skipped/xfailed without justification.
- [ ] **A pass that cannot fail proves nothing.** `scripts/test_mcp_role_config.py` counts failures instead of asserting, so pytest reports it "passed" whatever happens, and `scripts/test_org_tools_registry.py` is `--ignore`d in `pytest.ini`. On any org-tool change run both with python directly and quote their own verdict line. Seen twice: `scripts/test_tool_parity.py` (fixed 0cf98ec5, 2026-08-15), then the Run Inbox P1b worker (b2830b3c, 2026-09-25).
- [ ] **No test reaches a live API.** `conftest.py` at the repo root (not `tests/`) seals the `.env` reader for every test (`@pytest.mark.allow_dotenv` opts out). On a branch that calls an outside service, run the suite once with `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1`: a live call fails loudly instead of passing quietly (task-a6129a75; 2 live Jev calls per run on main, 2026-09-22).
- [ ] **New test files import only what `requirements.txt` has.** CI installs that file alone (`.github/workflows/ci.yml`); a package only the local `.venv` carries stops collection, and CI runs zero tests for every PR (task-67f82679, main red until 47f9d942). `git diff --name-only <base>...<branch> -- tests/`, then read each new file's imports.
- [ ] **No invisible characters in the diff.** The Write tool can land a typed `\uXXXX` escape as the literal code point: U+2028 inside a regex broke an import, bidi controls reached a source file (Run Inbox P1a + P1b, 2026-09-25). Every line this prints is a finding to judge:
      `git diff <base>...<branch> | python3 -c 'import sys,unicodedata as u; [print(n, hex(ord(c))) for n,l in enumerate(sys.stdin.buffer.read().decode("utf-8","replace").split("\n"),1) for c in l if u.category(c) in ("Cf","Zl","Zp","Co","Cn") or (u.category(c)=="Cc" and c not in "\t\r")]'`
- **Read the failing path before calling a rerun red — the review environment is not the worker's.** A worktree's `node_modules` may be a symlink to a main checkout installed `--omit=dev` (`ERR_MODULE_NOT_FOUND`, Console task-94755874) or already deleted by the worker (`./node_modules/.bin/next` missing, 0 checks run, ComfyRunpod task-97ce5459): give it a working one (`npm ci`, or link main's), rerun, remove the link before `merge_task`. A Next.js `tsc` error under `<app>/.next/` on main is a stale build cache: `rm -rf <app>/.next/types`, rerun (ComfyRunpod 3bf4ddf, rc 2 → 0).
- If tests fail → reopen task with feedback, do not merge.

### 3. Path conflicts cleared
- [ ] No in-flight task locks the same paths (`check_collisions(project, touches)`).
- [ ] If this task had `depends_on`, all parents are merged (not just done).

### 4. Acceptance criteria met
- [ ] Re-read the original task description.
- [ ] Each criterion has explicit pass evidence in the DEV report.
- [ ] No "should also do X" creep — only what was asked.
- [ ] **No brief on the branch.** `git diff --name-only <base>..<branch>` must not list `TASK.md` or `CTO-*.md`. Workers commit their own brief; `merge_task` only reports it as a touches violation beside legitimate extra files, so an `override_touches_check` lands it on main. `git rm` it and commit on the branch first, then override for the real extras only. Promoted 2026-09-26 on two independent runs (task-4c62e072 f52fb40, task-c794b73a e39faac).

### 4b. A guard must be ON THE PATH, not merely present — born from EP52, 2026-09-19
Applies whenever the task adds a limit, gate, precheck, budget, lock or kill-switch.
- [ ] Name the entry point a real run uses (`scripts/<x>.js`, the cron, the route), and trace from it to the guard. Paste the call chain into the gate output.
- [ ] Count its call sites outside tests first: `grep -rn "<guard>(" <src dirs> | grep -v /tests/ | grep -v "def <guard>"` printing nothing means inert (task-adbc6f43: defined and tested, wired nowhere until a92f9b8a). Then check which FUNCTION each hit sits in, not just which file:
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
- [ ] **One live run's artefact** — the file it produced plus its log or ledger line. Compiling is not running: the ChatGPT image replay script passed the check and was merged (44b9d54e) never having run; live use found three bugs in its sibling runner within the hour (task-d206afca, fixed in 4c8ca093). No live run → merge it labelled UNTESTED in the merge line.
- [ ] The script covers the mechanical steps; only genuine judgement calls are left to a model.
- If it says `Replay Script: none` → **REFUSE the merge** and reopen asking for the script. The one accepted exception is the operator stating in writing which specific step cannot be scripted and why.
- Why this is a gate and not a suggestion: `roles/browser_operator.md` and `CXO_Protocol_DevSpawn` §3c.8 already required the script, and both were satisfied by writing `none`. On task-cda4f469 that cost roughly 5 model turns per clip across 20 near-identical clips. A rule with an opt-out phrase is not a rule.

## Output format

```
Gate 0 (Dirty base)           : PASS — clean / parked <path> md5=… restored identical / left in place, hand-merged <sha> / N/A
Gate 1 (DEV report)           : PASS — status=done, files=N, tests=ok
Gate 2 (Tests green)          : PASS — 113 passed, 0 failed · new imports in requirements.txt · no invisible chars
Gate 3 (Path conflicts)       : PASS — no overlap with in-flight
Gate 4 (Acceptance criteria)  : PASS — all 3 criteria met
Gate 4b (Guard is on the path) : PASS — resume-video.js -> stage-runner -> runTTS -> assertBudget / N/A — no guard added
Gate 5 (GH blockers)          : N/A — none opened
Gate 6 (Wiki ADR)             : DEFERRED — no arch change
Gate 7 (External state)       : PASS — queried claudeflow_posts: 0 prior rows / N/A — repo-only task
Gate 8 (Repetition → script)  : PASS — scripts/browser/<slug>.js, live run <file + log line> / UNTESTED — compiles, never run / N/A — ≤3 repetitions

Verdict: MERGE  /  REOPEN with feedback  /  HOLD pending <reason>
```

## Operating rules

- **Never paraphrase the gate as passed without evidence.** Quote the DEV report.
- **One iteration of feedback is normal, three is a smell.** If DEV is on iteration 3, escalate to CEO instead of looping further.
- **Cross-project dependencies** — DEVs never reach across projects. If gate 3 reveals one, refuse and rewrite scope.
- **"merged: true" is a local fact, not a pushed one.** Right after every `merge_task`,
  in the project repo: `git fetch -q origin && git merge-base --is-ancestor <merge_sha> origin/main`.
  If it fails: pull if origin moved, re-run the suite (next rule) and read its totals, then
  `git push origin main` as its own command (a push chained to the suite sent a red test to
  origin, fixed in dd4c8a6c), re-check. Report the merge only once it is on origin. Promoted from a field
  note on two independent runs with two different causes: origin had moved (task-bfa778ab),
  and a project that never pushes at all (mooniex-console, task-94755874, 0bd1c154 was
  7 commits ahead of origin).
- **HARD — Never run a project's tests in a checkout that live data or a live server runs from** until
  you have read what their setup deletes (`grep -nE 'rmtree|unlink|reset'` over the test files) and every
  dir it resolves to is a temp dir; otherwise run them in a worktree and, on the live checkout, check only
  `tsc`, `git merge-base --is-ancestor` and a `curl` of the live pages. (Agents-Core's default `pytest` run
  is side-effect-free by design: evals are `--ignore`d in `pytest.ini`.) **Why hard:** irreversible — seven
  ComfyRunpod test scripts wipe the studio data dir before starting `next dev`; run on main after merge
  e760235 they deleted the CEO's live prompts, entities and renders, restored only in part from a
  3-day-old Drive backup (task-fd7c3b35, P0 fix task-1ce96a4c). `[SUPERSEDED 2026-09-28]` "(after pulling
  if origin moved, and re-running the suite)", silent on where — beaten by that deletion.
- **Hand merge — when `merge_task` cannot run**: a Contabo session (it opens the project's Mac `path`,
  not `paths.contabo` in `config/projects.yaml` — still so in `tools/git_ops.py` on 2026-09-28), a dirty
  file the branch does not touch (gate 0), or a branch already merged (a no-op refusal). Run its checks
  yourself (declared touches vs `git diff --name-only <base>...<branch>`; `tools/workdir.py close <id> --dry-run`
  if the task has a Work folder — `merge_task` runs the same close and refuses on anything unfiled, a
  symlink included: delete the link, never its target), then `git pull --ff-only origin <base>` → `git merge --no-ff <branch>` →
  push → `git merge-base --is-ancestor HEAD origin/<base>`. Close: `close_dev`,
  `lib.db.update_status(<id>, "done", actor="cto")` + a delegate_log line naming the merge sha,
  `git worktree remove`, `git branch -D` (`-d` refuses even with `main..branch` empty); never raw sqlite.
  Runs: task-95439aa8 → d53e2dd2, task-854cb512 → 65cae7ec, task-9f6fec26 → a21c625a, task-a40d2d8e → 3a24ba8e.
- **Merges and deploys are the CTO's call on every repo** (merges, CEO 2026-09-19: "Coding คือหน้าที่คุณ เห็นสมควรจัดการได้เลย ฉันมีหน้าที่วางแผน"; deploys, CEO 2026-09-27: "อยากให้ CTO เป็นคนตัดสินใจ เมื่อเห็นสมควร ... มีเช็ค list ในการ Deploy", `ALL_Rules_Approvals` rule 5). A gate-clean PR is merged and reported in one line — never "ขออนุมัติ merge"; a deploy goes out when this checklist is green, is announced with a rollback line, and is reported after. Spend, migrations and secrets keep their own gates (`ALL_Rules_Approvals`). `[SUPERSEDED 2026-09-28]` "Spend, prod deploys, migrations and secrets keep their own gates; those are consequences, not code decisions" — prod deploys left that list on the CEO's 2026-09-27 ruling.
- **A deploy, or a merge into something running, is done when the new code is seen running** — not on
  exit 0 or green tests (they build fresh state). A service only enabled/started keeps its old process
  (Console: same pid 1039, new route 404 until `systemctl restart`, task-94755874); a `globalThis`
  singleton in a live `next dev` keeps its old shape under new code (every ComfyRunpod Start aborted
  silently for 5 min, 41d9658 → fix 412190b). Check the new route on the canonical URL or the new process
  in `pgrep`, on the box where it runs (a tool that runs on winbox needs a pull there, task-854cb512).

## Field notes

- 2026-09-22 [MISSING] §0 — `merge_task` refused twice in one evening on a dirty base that was another live session's WIP (`tests/test_flow_shoot.py`, then `claude-home/settings.json`); no gate said what to do with it, and the natural moves (checkout, bare stash, commit-for-them) all destroy or misattribute someone's work. Gate 0 added: fingerprint → path-limited tagged stash → merge → apply-not-pop → md5 must match → drop by re-found index; configs the org runs on go to the CEO instead · evidence: sessions cto-a29c7576 + cto-8c06958c, both md5 round-trips matched (ff175ec3…), ADR 0026 · status: promoted
- 2026-09-22 [MISSING] §4b — the awk "which function is the guard in" step passed a branch whose `artefact_gate` had one definition and zero production call sites (only tests called it). The faster, decisive first check is call-site count outside tests: `grep -rn "<guard>(" <src dirs> | grep -v "/tests/" | grep -v "def <guard>"` — empty means inert, reopen · evidence: task-adbc6f43 iteration 1→2, caught before merge; the fixing commit a92f9b8a ("wire artefact_gate into branch_poller (task-adbc6f43 iter 2)") is the artefact that iteration 1 was inert → §4b · status: promoted
- 2026-09-22 [MISSING] §2 — this repo's `pytest.ini` `addopts` already carries `-q`; adding `-q` on the command line makes `-qq`, which drops the final pass/fail summary line — a green run then reads like a hang or a truncated log. Use `-p no:warnings` for less noise, never a second `-q`; count the dots or drop `-q` when you need the summary · evidence: worker task-df0541aa (background run judged "still running" for 30 min) and the CTO's own suite run on main 21:38, same evening (rule in §2, 2026-09-25) · status: promoted
- 2026-09-22 [MISSING] §2 — a `os.environ.get(X) or _read_dotenv_var(X)` fallback makes "no key set" tests silently read the real gitignored `.env` and go LIVE; the autouse fixture must monkeypatch the dotenv reader too. The rule now lives in the tool: `tests/conftest.py` autouse fixture neutralises the dotenv reader for every test (opt-out marker `allow_dotenv` for the one test that is about the reader). On review, run the suite with `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1` once — a live call fails loudly instead of passing quietly · evidence: task-a6129a75 (2 unplanned live calls) + main after merging T2 and T1b (tests/test_decide_browser_sites.py made 2 live Jev calls per run, 22:33) — two independent hits the same evening · status: promoted
- 2026-09-23 [MISSING] after merge — `merge_task` returned `merged: true` (merge_sha f335cbf1, no push field in the result) while origin/main had moved (the CTO had pushed Jules merges from a scratch worktree); f335cbf1 was NOT on origin until a manual `git pull --no-rebase origin main` + suite + `git push`. After every merge_task run `git merge-base --is-ancestor <merge_sha> origin/main` — "merged" is a local fact, not a pushed one · evidence: task-bfa778ab, fix pushed as f38daffd; second run task-94755874 (mooniex-console never pushes; 0bd1c154 7 ahead) agreed 2026-09-23, promoted to Operating rules · status: promoted
- 2026-09-23 [MISSING] §2 — a worker may leave its worktree's `node_modules` as a symlink to the main checkout; if that checkout was installed `--omit=dev` (it is also the live Console-Mac deploy dir), the reviewer's `vitest run` dies with ERR_MODULE_NOT_FOUND. Replace the symlink with a real `npm ci` in the worktree before rerunning (merge_task's cleanup removes it) · evidence: task-94755874 review; second run task-97ce5459 (2026-09-26) agreed → §2 "Read the failing path" · status: promoted
- 2026-09-23 [MISSING] after merge — MoonieX-Console `scripts/console-deploy.sh service` only enables/starts the unit; a RUNNING service keeps the old code (the same pid 1039 before and after, `/api/relay/targets` 404). Deploy = `sync` → `install` → `ssh mooniex-vps systemctl restart mooniex-console` → `verify`, then smoke-test a new route on the canonical `https://terminal.mooniex.com` (not :8443, which 302s) · evidence: task-94755874 deploy 18:1x; same point from ComfyRunpod 41d9658 → 412190b (2026-09-27) → Operating rules "seen running" · status: promoted
- 2026-09-23 [MISSING] after merge — when the CTO merges a branch by hand (scratch worktree + push), `merge_task` then refuses as a no-op ("already an ancestor… refusing to report success") and leaves the task in review. Close it with `close_dev` + `lib.db.update_status(id, "done")` and a delegate_log line naming the merge sha, then remove the worktree/branch — never raw sqlite · evidence: task-95439aa8 → d53e2dd2; the same close agreed in task-854cb512 and task-9f6fec26/a40d2d8e → Operating rules "Hand merge" · status: promoted
- 2026-09-23 [MISSING] §gates — a branch that adds a test under `tests/` (a collected path since bde67a10) must not import a third-party package missing from requirements.txt. The local .venv has it, so the suite is green locally, but CI stops at collection ("Interrupted: 1 error during collection") and runs ZERO tests, for every session's PR, not only yours. Cheap check before merging: `git diff main...<branch> --name-only -- tests/` → grep each new file's top-level imports against requirements.txt · evidence: task-67f82679 (tests/test_bl_realfootage.py imported PIL; main red from merge until 47f9d942; reported by CTO a29c7576, run 35856165137); fixing commit 47f9d942 proves a local-green §2 can land a CI that runs zero tests → §2 · status: promoted
- 2026-09-24 [MISSING] after the HQ move — `merge_task` from a CONTABO session fails with `No such file or directory: '/Users/gob/MoonieXHQ/Agents/Core'`: it reads the project's top-level `path` (Mac) instead of `paths.contabo` (`/opt/mooniex-agents`) that config/projects.yaml already carries. Merge by hand: `git pull --ff-only origin main` → `git merge --no-ff origin/<branch>` → push → `git merge-base --is-ancestor HEAD origin/main`; close with `lib.db.update_status(id,"done")` + a delegate_log line naming the sha; on winbox also pull `C:\Users\UsEr\mooniex\repo\MoonieX-Agents` so the merged tool is where it runs · evidence: task-854cb512 → 65cae7ec; `tools/git_ops.py` merge_task still opens `proj["path"]` (read 2026-09-28) — merged with the 2026-09-23 hand-merge note → Operating rules "Hand merge"; winbox pull → "seen running" · status: promoted
- 2026-09-24 [MISSING] §8 — `check_replay_script.py` exit 0 only proves the file compiles; `scripts/browser/chatgpt_image.py` passed it, was merged (44b9d54e) and had never run once (no playwright in the worker's env). Live use found 3 real bugs in the sibling runner within an hour (image turn outside `[data-message-author-role]`, first paste landing nothing, a second Send click that would hit Stop). For a replay script, ask for one live run's artefact (a file + its log/ledger line), or merge it labelled UNTESTED · evidence: task-d206afca → deleted in 4c8ca093 (merged 44b9d54e, never run; the fixing commit is the artefact) → §8 · status: promoted

- 2026-09-25 [MISSING] §pre-flight — `merge_task` refuses with `base_dirty` on `claude-home/settings.json` whenever the harness has saved a `/model` switch into it (one-line diff, the CEO's "ห้ามยุ่ง" file). Park only that path: `git stash push -- claude-home/settings.json` → merge → `git stash pop`; do not commit the CEO's model choice as a side effect (9dc6c2a8 was a deliberate CEO ruling, not a pattern). Also: `merge_task` refuses while the task's Work/ folder has unfiled entries and treats symlinks as unfiled — delete the symlinks (targets untouched) then `tools/workdir.py close` · evidence: task-67bb7a11 merge 7dfef62e, stash 76eac58a; tools/workdir.py `check()` flags every symlink (rule 10) and `close()` counts a linked file as unfiled, and tools/git_ops.py refuses merge_task on it (read 2026-09-28) → Operating rules "Hand merge" (symlinks); the settings.json half is §0's, whose apply-not-pop (two runs) beats this note's `pop` · status: promoted
- 2026-09-25 [COSTLY] §2 — `pytest -q` added on top of pytest.ini's own `-q` makes pytest very quiet: no totals line, so a grep for "passed" finds nothing; run without the extra flag · evidence: this session's T2 review (rule in §2, 2026-09-25) · status: promoted
- 2026-09-25 [MISSING] §2 — a Next.js project's `tsc --noEmit` can pass in the worker's worktree and fail on MAIN for a reason unrelated to the branch: main's gitignored `.next/types/validator.ts` (a build cache, here from Aug 22) still referenced a route deleted weeks earlier (TS2307 `api/characters/route.js`). Worktrees have no `.next`, so they never see it. Before blaming the merge, read the error path; if it is under `.next/`, `rm -rf <app>/.next/types` (regenerated on next dev/build) and re-run · evidence: ComfyRunpod merge 3bf4ddf, tsc rc=2 → 0 — merged with the 2026-09-23 node_modules note (same point: environment, not branch) → §2 "Read the failing path" · status: promoted
- 2026-09-25 [COSTLY] §2 — `scripts/test_mcp_role_config.py` (and `scripts/test_org_tools_registry.py`) record their checks and print `OK —`/`FAILED`; under pytest they collect as tests that can never fail, so "9 passed" from `pytest scripts/test_mcp_role_config.py` proves nothing — only the standalone run's own verdict line counts (`test_tool_parity.py` had the same flaw, fixed 2026-08-15). Also `scripts/test_org_tools_registry.py` is not collected by pytest at all and was stale on main (2 tool names missing) until the Run Inbox P1b worker ran it by hand. On review of any org-tool change: run the three standalone scripts and read their verdict lines · evidence: P1b worker report 2026-09-25, commit b2830b3c; earlier run 0cf98ec5 (test_tool_parity, 2026-08-15); `_mark` still never raises (read 2026-09-28) → §2 · status: promoted
- 2026-09-25 [MISSING] §2 — no gate scans the diff for invisible / format characters: typed `\uXXXX` escapes reached files as the literal code points (U+2028 inside a regex literal broke an import; literal bidi controls landed in a source file). Before merging anything a worker wrote, scan the diff with unicodedata for categories Cf/Zl/Zp/Co/Cn and any Cc other than `\n`/`\t`; the P1a worker scanned every new file that way before committing · evidence: Run Inbox P1a + P1b reports 2026-09-25 (memory js-line-separator-escape-via-write-tool) → §2 · status: promoted
- 2026-09-25 [MISSING] §0 — `merge_task` refuses `base_dirty` on ANY modified tracked file in the main tree, even ones the branch never touches (here a peer's live `state/banchi/flow_shoot.log` + `tools/flow_upload_element.py`; stashing a log a runner may be appending to loses lines). What worked twice: a hand `git merge --no-ff <branch>` in the main tree — git itself only refuses when the merge would overwrite a dirty file — then `close_dev` + `lib.db.update_status(id,'done')` + a delegate_log line naming the merge sha, `git worktree remove`, `git branch -D` (`-d` refused although `main..branch` was empty). The settings.json model line still needs the §0 tagged-stash round-trip when the branch touches settings.json (T1: stash → merge → apply → drop, key landed + model line back) · evidence: task-9f6fec26 → a21c625a, task-a40d2d8e → 3a24ba8e — merged with the 2026-09-23 hand-merge note → §0 + Operating rules "Hand merge" · status: promoted
- 2026-09-25 [COSTLY] after merge — I pushed main in the same command that printed the suite result, before reading it: main went to origin with a new red test (`test_settings_json_keeps_existing_keys` asserted the CEO's live `model` value). Read the totals, then push, as two commands; a test that reads `claude-home/settings.json` may assert key presence only, never the model value · evidence: dd4c8a6c fix, suite-main 3 failed/1128 passed → Operating rules "merged: true" (read, then push); the settings.json test point lives in the fixed test itself (dd4c8a6c) · status: promoted
- 2026-09-26 [MISSING] §4 scope — a worker committed its own `TASK.md` (the brief) into the project branch (f52fb40); merge_task flagged it only as a touches violation beside a legit extra file. Before `override_touches_check`, list every extra file; for TASK.md / CTO-*.md run `git rm --cached` + commit on the branch first, so the brief never lands on main · evidence: task-4c62e072 → 6a599f7; second run task-c794b73a (e39faac, dropped in 6e61c75 before merge b3f9921) agreed 2026-09-26, promoted to §4 · status: promoted
- 2026-09-26 [MISSING] §2 — a ComfyRunpod worker deletes its `studio/node_modules` symlink before reporting, so the reviewer's rerun of `scripts/test_runware_images.py` dies at once with `FileNotFoundError: './node_modules/.bin/next'` (rc=1, 0 checks). That is not a red suite: `ln -s <main>/studio/node_modules <worktree>/studio/node_modules`, rerun (120/120), then remove the link again before `merge_task`. Same family as the 2026-09-23 Console note: the worktree's node_modules state at review is not the worker's · evidence: task-97ce5459 review → 499b7ca — merged with the 2026-09-23 note → §2 "Read the failing path" · status: promoted
- 2026-09-27 [COSTLY] after merge — merging a change to the SHAPE of a `globalThis` singleton (ComfyRunpod `podRuntime.ts` `rt`, kept there so it survives hot reload) into a live `next dev` server leaves the OLD object running under the NEW code. `rt.bootGeneration` was missing, `++` gave NaN, the spawn guard `NaN !== NaN` aborted every Start silently, and the Studio said "starting" for 5 min with no process. Every test was green because tests build a fresh object. After such a merge: confirm the new path really ran on the live server (here: `pgrep -fl 'pod_boot.py start'`), and make the module backfill missing fields on load · evidence: 41d9658 → fix 412190b — merged with the 2026-09-23 Console deploy note → Operating rules "seen running" · status: promoted
- 2026-09-27 [MISSING] after merge — a ComfyRunpod test that spawns its own `next dev` (`scripts/test_entity_notes.py`, `test_scene_aspect.py`) prints "next dev never came up - aborting" when run on MAIN while the live studio dev server (:4100) is up: Next allows one `next dev` per project dir. That is the environment, not the branch. Run those tests in the worktree (symlink `studio/node_modules` + `workflows/templates/object_info-snapshot.json`); on main run only the no-server scripts + `tsc`, then `curl` the live pages for 200 · evidence: task-fd7c3b35 merge e760235 (worktree 26/26, main aborted, /render + /scenes 200); superseded by the next note, the abort came AFTER the data wipe · status: superseded
- 2026-09-27 [WRONG] after merge — "re-run the suite on main after merging" is destructive for a project whose tests reset a data dir. Seven ComfyRunpod scripts (`test_entity_notes.py`, `test_scene_aspect.py`, `test_scene_gen.py`, `test_prompt_chat.py`, `test_prompt_fill.py`, `test_venice_images.py`, `test_runware_images.py`) run `shutil.rmtree(<repo>/studio/data)` BEFORE they try to start `next dev`, so the "never came up - aborting" above came after the CEO's live studio data (master prompts, entities, renders) was already deleted. Restored only partly, from a 3-day-old Drive backup. Before running any project test outside a worktree, grep its setup for `rmtree`/`unlink`/"reset" and confirm the dir it resolves to is a temp dir; on a project's main checkout check only `tsc`, `git merge-base --is-ancestor`, and a `curl` of the live pages · evidence: task-fd7c3b35 merge e760235, P0 fix task-1ce96a4c, memory feedback_never_run_project_tests_in_main_checkout; the deletion is the artefact that beat the old line → Operating rules HARD, old text kept as SUPERSEDED · status: promoted
- 2026-09-28 [SUPERSEDED] Operating rules — "Spend, prod deploys, migrations and secrets keep their own gates" still put deploys outside the CTO's call; the CEO ruled on 2026-09-27 that deploys are the CTO's decision on its checklist ("อยากให้ CTO เป็นคนตัดสินใจ เมื่อเห็นสมควร ... มีเช็ค list ในการ Deploy"). Rewritten, old line kept as SUPERSEDED · evidence: .claude/skills/ALL_Rules_Approvals/SKILL.md rule 5 → Operating rules "Merges and deploys" · status: promoted
- 2026-09-28 [WRONG] §2 — the promoted dotenv note (and pytest.ini's marker text) name `tests/conftest.py`; the file is `conftest.py` at the repo root · evidence: `ls tests/conftest.py` fails 2026-09-28, fold worker, session 14cc900f; re-checked by the next fold worker (`conftest.py:156` `_no_dotenv_no_paid_calls`, marker `allow_dotenv`) → §2 "No test reaches a live API" (with the 2026-09-22 note's proxy check); pytest.ini's marker text still says `tests/conftest.py` — outside this skill · status: promoted
- 2026-09-28 [WRONG] §0 — `md5 -q` is macOS-only; Contabo has only `md5sum`, so the fingerprint step fails as written there (Linux: `md5sum <path> | cut -d' ' -f1`) · evidence: `command -v md5` → none on Contabo 2026-09-28, fold worker, session 14cc900f; re-checked (`command -v md5 md5sum` → only /usr/bin/md5sum) → §0 · status: promoted
