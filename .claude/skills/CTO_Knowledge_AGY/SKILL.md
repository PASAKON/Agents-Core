---
name: CTO_Knowledge_AGY
kind: knowledge
description: KNOWLEDGE — What Antigravity (agy) is in the org (its two weekly buckets, the file-only headless contract, the agy_browse lane) and how it has measured as a worker, per job type, from runner_fit. Folded weekly from the tool-value report. Trigger on /CTO_Knowledge_AGY, "agy ทำได้ไหม", "ส่ง agy", "Antigravity", "agy quota", "runner-fit agy". Do NOT use it for how to write the brief (CXO_Protocol_DelegateExternal) or for driving a browser (tools/agy_browse.py, IRON §60).
owner: CTO
audience: [cxo]
created_by: agent
author: {role: cto, date: "2026-10-14"}
improved_by: []
aka: []
verified: "2026-10-14"
refresh_after: "2026-10-21"
---

# AGY (Antigravity): facts and measured fit

Folded every week from `tools/tool_value.py` (its runner-fit table and the hub `runner_fit` events). One sighting
is a Field note. A line enters the body only when ≥2 runs agree (ADR 0026). Brief rules for agy, including the
allow-list spelling, are in `CXO_Protocol_DelegateExternal`, not here.

## What it is (checked 2026-10-14)

- **The CLI:** `agy` 1.3.4 on Contabo, at `/root/.local/bin/agy`; it is not on root's PATH. `config/hosts.yaml` lists
  agy on mac, winbox and contabo.
- **Two weekly buckets**, both inside Google AI Ultra:
  - `agy-gemini`;
  - `agy-claude` (Sonnet 4.6: Claude quality, billed to Google).
  The read is `agy -p /usage` on Contabo, into quota-history. That the buckets are per account, not per host, is
  ASSUMED (plan §2.3).
- **Headless it is file-only.**
  - It runs only the commands on the allow-list in `config/agy-settings.json`.
  - A tool with no permission rule is denied silently.
  - An unlisted command aborts the whole run.
  - `shell_runners` in `config/plans.yaml` leaves agy out, so `forecast.needs_shell` routes shell jobs away from it.
- **The browse lane:** `tools/agy_browse.py`. Since 1116f7c8 its audit line lands in the main checkout's log and as a
  hub event, so worker calls are no longer lost with their worktrees.

## Use (measured, quota-history)

| Window | agy-gemini used | agy-claude used |
|---|---|---|
| 6–12 Oct | 3.4% | 18.3% |
| 13–14 Oct | 0.8% | 0% |

This is the org's largest idle gap (plan §2.3).

## Measured fit (hub runner_fit, cell `agy-gemini`)

| Week | Job type | Jobs | Pass / redo / fail | First pass | Evidence |
|---|---|---|---|---|---|
| 13–19 Oct (to 14 Oct) | code | 2 | 2 / 0 / 0 | 0 of 2 (both reviewer-fixed) | task-f3f80ab6 (12.6 min), task-30206a64 (13.1 min) |
| 13–19 Oct (to 14 Oct) | tests | 1 | 0 / 0 / 1 (`no-shell`) | 0 of 1 | task-0156526f (0.2 min) |

**Phase 1:** 3 jobs so far.

## What holds (≥2 runs)

- **A file-only code job comes back with every brief item done as written, and no command run.** n=2: f3f80ab6,
  30206a64.
- **The reviewer fixes so far were faults in the brief, not agy's work.**
  - f3f80ab6: a regex that broke the agy_browse lane; v1 tests not listed.
  - 30206a64: a code path on the held local main; the send path from a deploy tree.
  So check the brief before blaming the runner.
- **Never give agy a job that needs a command.**
  - n=3:
    - task-4ec8abff (30 Sep): could not read files;
    - task-5ba7bccf (30 Sep): a relative interpreter path;
    - task-0156526f (13 Oct): needed git and pytest; exit 0, no output.
  - Shell jobs go to codex.

## Not yet measured

- **The agy-claude bucket on real work.** It was 0% this week. Text roles that need Claude quality but no Claude-only
  tool wait on an A/B (plan §4.3 M5).
- **agy_browse use.** 0 calls in both windows on Contabo. The Mac and winbox are not read yet.

## Field notes
- 2026-10-14 [MISSING] measurement — `runner_fit` has no brief-fault flag: a reviewer fix caused by the brief still sets `first_pass: false`, so agy-gemini code reads 0% first pass on 2 passes whose fixes were brief faults. Either record `brief_fault` or count first pass as "no fix to the runner's own work" · evidence: task-f3f80ab6, task-30206a64 runner_fit 13 Oct · status: pending
- 2026-10-14 [MISSING] measured fit, Gemini 4 Argon — `gemini-4-argon-high` (listed on Contabo and the Mac, agy 1.3.4) on 9 real jobs: on 4 paired developer S/M jobs the blind Opus judge gave Argon 8 points and Sonnet 5.5 6 (ratio 1.33; Sonnet WRONG on Console#27); strict first pass developer 2/5, translation 1/3, analysis 0/1; 2–6× Sonnet's wall time; one large job takes 15–16 points of `gemini-5h`. Route developer S/M with a CTO review; no type reaches phase 2 yet · evidence: argon-trial-2026-10, docs/ops/argon-trial-2026-10/RESULTS.md, 13 runner_fit events `argon-trial-*` · status: pending
- 2026-10-14 [MISSING] headless contract — agy `--output-format json` returning `status: "ERROR"` ("exceeded the output token limit") does not mean the run produced nothing: on job A1 agy had already written both files complete when its final reply hit the cap. Read the worktree diff before throwing away an ERROR run · evidence: argon-trial-2026-10 A1 (24.44 min, 164k output tokens), landing commit 0761c9a8 · status: pending
