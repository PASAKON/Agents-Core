---
name: CTO_Knowledge_Codex
kind: knowledge
description: KNOWLEDGE — What Codex CLI is in the org (where it runs, its weekly bucket, that it can run a shell) and how it has measured as a worker, per job type, from runner_fit. Folded weekly from the tool-value report. Trigger on /CTO_Knowledge_Codex, "codex ทำได้ไหม", "ส่ง codex", "codex quota", "runner-fit codex". Do NOT use it for how to write the brief (CXO_Protocol_DelegateExternal) or whether to route at all (CXO_Gate_RouteFirst).
owner: CTO
audience: [cxo]
created_by: agent
author: {role: cto, date: "2026-10-14"}
improved_by: []
aka: []
verified: "2026-10-14"
refresh_after: "2026-10-21"
---

# Codex: facts and measured fit

Folded every week from `tools/tool_value.py` (its runner-fit table and the hub `runner_fit` events). One sighting
is a Field note. A line enters the body only when ≥2 runs agree (ADR 0026). Brief rules for codex are in
`CXO_Protocol_DelegateExternal`, not here.

## What it is (checked 2026-10-14)

- **The CLI:** OpenAI Codex CLI, `codex-cli 0.155.1` on Contabo (`codex --version`, 14 Oct). It is paid by the ChatGPT
  subscription, $20 a month in `config/plans.yaml`.
- **Hosts:** `config/hosts.yaml` lists `codex` on contabo and winbox. The Mac has the CLI, but no lane uses it.
- **It can run a shell:** `shell_runners: [claude, codex]` in `config/plans.yaml`. A job that has to run tests, psql or
  docker can go to codex; agy cannot run it (`forecast.needs_shell`).
- **Its bucket:** one weekly %, read into quota-history.
  - The 3–10 Oct window peaked at 97%, and 50% was used inside 6–12 Oct. Both are measured (plan
    `docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md` §2.4).
  - The growth came from one CEO order on 10 Oct, not from the router.

## Measured fit (hub runner_fit, cell `codex`)

| Week | Job type | Jobs | Pass / redo / fail | First pass | Evidence |
|---|---|---|---|---|---|
| 13–19 Oct (to 14 Oct) | code | 2 | 2 / 0 / 0 | 2 of 2 | task-1ba49354 (16.1 min), task-eda3b609 |
| 13–19 Oct (to 14 Oct) | tests | 1 | 1 / 0 / 0 | 1 of 1 | task-61a8ce6a (6.0 min) |

The report's coarser counts are measured from the hub task table, not from runner_fit:

| Measure | 6–12 Oct | 13–14 Oct |
|---|---|---|
| Worthwhile (done, no reopen, iteration 0) | 10 of 16 | 3 of 4 |
| Mean rounds per finished task | 1.4 | 1.2 |

**Phase 1** (plan gate: ≥10 jobs at ≥80% first pass, its skill unchanged for 14 days). 3 jobs so far.

## What holds (≥2 runs)

- **A code job with a complete brief passes on the first try, and codex runs its own tests.** n=2: task-1ba49354
  ran 63 tests, task-eda3b609 ran 93. A complete brief has numbered sections, the list of tests, and the rule that
  fixtures stay in tmp_path. On task-1ba49354 codex also caught a step-order fault in the brief and reordered the
  steps safely.

## Not yet measured

- **Shared bucket?** Whether winbox and Contabo codex draw on one account bucket. The report reads Contabo only.
- **The reset-date jump.** At 13 Oct 11:09 UTC the reset date moved from 17 Oct to 20 Oct, with 31% already used.
  The cause is unknown (plan §2.4), so the report prints the window dates next to the %.

## Field notes
- 2026-10-14 [MISSING] dispatch — after the codex process exited, the hub row of task-eda3b609 stayed `in_progress`; the CTO closed it by hand (`update_status done` + a runner_fit record). Check `tmux ls` and the branch before trusting the row · evidence: task-eda3b609, session cto-dd03bac1 · status: pending
- 2026-10-14 [MISSING] sandbox — codex's own sandbox is a nested bwrap and needs a user namespace it can map: inside an outer `bwrap` that keeps uid 0 it fails "setting up uid map: Operation not permitted" (mapping uid 0 needs CAP_SETFCAP). It works when the outer box is `--unshare-user --uid 1000 --gid 1000 --cap-drop ALL`. `--search` is a top-level flag (`codex --search exec …`), not an `exec` flag; with it codex answered a web+local question correctly in 2.6 min in that box · evidence: runners/coo_worker.py box_argv, task-366861c9 (cto-afe760fe, branch cto/coo-research-delegate a55a7aff) · status: pending
- 2026-10-14 [MISSING] handoff from a Codex run — when the Codex desktop app worked a repo on winbox, its session log `C:\Users\passg\.codex\sessions\…\rollout-<date>-<id>.jsonl` is the handoff source, not `~/.claude/projects`. The Claude session before it (WINDOWS CTO #d73e6864) had only subagent metas left. Read the tail with PowerShell `Select-String '"role":"assistant"'`, and check the commit author (Codex commits as the desktop git user) plus codex CPU ≈0 before taking the repo over. The brief from CTO Main had pointed the PH at ~/.claude, which was wrong · evidence: PH CookieRun #f35affd5 M1, 14 Oct 11:11 TH; CookieRun HEAD 4fa8423 · status: pending
- 2026-10-22 [MISSING] git inside the sandbox — a Codex worker cannot checkout, merge or commit in its worktree: the sandbox refuses writes to `<repo>/.git/worktrees/<name>/`, which lies outside the worktree folder. The runner commits after the run, so the report still lands, but a brief that needs a merge or a branch switch must have it done in the worktree before delegating, or go to a claude worker · evidence: task-e38938f5 REPORT (the merge of agent/security_engineer-task-afe57b21 failed; the review itself was sound) · status: pending
