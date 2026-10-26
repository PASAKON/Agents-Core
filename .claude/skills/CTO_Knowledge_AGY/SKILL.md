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

## Argon (Gemini 4): when and how to use it (CEO ruling 2026-10-14)

The CEO, via SomPong, 14 Oct about 04:25 Thai time: "เขียนลง skill และกดเลยว่าจะใช้ argon ได้เมื่อไหร่ยังไงบ้าง".
Evidence: `docs/ops/argon-trial-2026-10/RESULTS.md`, 9 real jobs, all measured:
- on 4 paired developer jobs, the blind Opus judge gave Argon 8 points and Sonnet 5.5 6 (USABLE 2 / CORRECT 1 / WRONG 0);
- strict first pass: developer 2/5, Thai→English 1/3, analysis 0/1;
- Argon took 2–6× Sonnet's wall time.

- **Use Argon** (`agy`, `gemini-4-argon-high`; it bills `agy-gemini` and leaves Claude quota untouched) for:
  - developer S/M jobs that are file-scoped, with a brief that lists the files, the interface and the done-test. It
    is the first choice over a Claude developer;
  - refactors, docs from code, boilerplate and test scaffolds where a reviewer can run the tests. These have the
    same shape but were not measured in the trial.
- **Always:**
  - a CTO or PH review and a test run before the merge. No job type has reached phase 2;
  - the reviewer runs every command Argon cannot. Headless agy runs only the `config/agy-settings.json` allow-list
    (above).
- **Do not use Argon for:**
  - jobs that need a command off the allow-list, MCP, a browser, secrets, deploy, money or security. On Contabo agy
    has no MCP server configured (`agy mcp list`, 14 Oct);
  - the PH or C-level seat. A PH runs Opus 5.5 at effort medium and a C-level runs Opus 5.5 at xhigh (CEO 2026-10-14);
  - Thai→English translation, until the brief names what stays Thai (1/3 first pass; see the 2026-10-14 field note
    in `CXO_Protocol_DelegateExternal`);
  - anything urgent, since it takes 2–6× Sonnet's wall time.
- **Budget:**
  - a large job took 15–16 points of `gemini-5h` (D3 14.6, A1 16.3, measured); a small one took 0.1–3;
  - that allows about 5 large jobs per 5-hour window (estimate);
  - read `agy -p /usage` before starting one.
- **Phase 2** (routing without the extra review) comes only when a job type reaches ≥90 % strict first pass over
  ≥10 jobs in `runner_fit`.

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
- 2026-10-14 [MISSING] measured fit, Gemini 4 Argon — `gemini-4-argon-high` (listed on Contabo and the Mac, agy 1.3.4) on 9 real jobs: on 4 paired developer S/M jobs the blind Opus judge gave Argon 8 points and Sonnet 5.5 6 (ratio 1.33; Sonnet WRONG on Console#27); strict first pass developer 2/5, translation 1/3, analysis 0/1; 2–6× Sonnet's wall time; one large job takes 15–16 points of `gemini-5h`. Route developer S/M with a CTO review; no type reaches phase 2 yet · evidence: argon-trial-2026-10, docs/ops/argon-trial-2026-10/RESULTS.md, 13 runner_fit events `argon-trial-*`; CEO ruling 2026-10-14 made it a rule → §Argon · status: promoted
- 2026-10-14 [MISSING] headless contract — agy `--output-format json` returning `status: "ERROR"` ("exceeded the output token limit") does not mean the run produced nothing: on job A1 agy had already written both files complete when its final reply hit the cap. Read the worktree diff before throwing away an ERROR run · evidence: argon-trial-2026-10 A1 (24.44 min, 164k output tokens), landing commit 0761c9a8 · status: pending
- 2026-10-14 [MISSING] headless contract — `agy -p … --mode plan` in a fresh HOME: (1) once returned rc 0 with a 95-character status line ("Waiting for the research subagent to complete…") and no answer: the plan-mode turn handed off to a subagent and print mode exited; (2) without a `permissions.allow` rule every read is auto-denied ("a tool required the \"read_file\" permission that headless mode cannot prompt for"). Rules take `read_file(<abs path>)`, `write_file(<abs path>)`, `read_url(<domain>|*)`, `command(...)`, `mcp(server/tool)`. With `read_file(/opt/MoonieXHQ)` + `read_url(*)` it answered from the web, but took 416 s and miscounted a directory (67 of 71; codex and Sonnet both said 71). A caller must check the answer is a real report (length + a heading), not rc · evidence: runners/coo_worker.py `is_report` + runners/coo_agy_settings.json, probes 2026-10-14 by cto-afe760fe (branch cto/coo-research-delegate a55a7aff) · status: pending
- 2026-10-14 [WRONG] §What it is ("forecast.needs_shell routes shell jobs away from it") — the router sent a developer job that must run node tests to agy anyway: task-0e750cc6 (ClaudeFlow, brief "add tests that prove it and open a PR", touches tests/videolib-paid-gen-gate.test.js). agy auto-denied the command tool, committed a stub REPORT.md ("jetski: no output produced — a tool required the "command" permission"), exit 0, in ~1 min; the hub row stayed in_progress with a dead pid and no tmux. Fix candidates: needs_shell true when touches hold a test file or the brief says tests; a stub "no output produced" REPORT marks the task failed. What worked: a new task with header `override: claude-tool — …` (task-f7c291b6, Sonnet) · evidence: task-0e750cc6, router line "agy gemini-3.8-flash-high [agy-gemini]" 10:10:55 CEST, session cto-c34459eb · status: pending
- 2026-10-14 [MISSING] §headless file access — headless agy auto-denies `read_file` on a path outside its worktree: a review brief that pointed at /opt/MoonieXHQ/Agents/Core/state/handoff/… ended with "a tool required the \"read_file\" permission that headless mode cannot prompt for, so it was auto-denied", no output file. Put inputs inside the task (the brief text, or a branch the worker checks out), or route the job to Codex · evidence: task-8cc2b28e (agy gemini-3.8-flash-high, PR #314 review) · status: pending
- 2026-10-15 [MISSING] §What holds — agy is edit-only, so the tests on an agy branch have never been run by anyone. Run them first, before reading the diff. Argon task-c7116818 (router "Claude runs out last") came back with tests that mocked APIs that don't exist, plus a slice error that broke forecast.py: 7 tests failed at collection or on assertions. The PH rewrote them and landed it as PR #343. Count an agy branch's tests as unverified until a shell run shows them green · evidence: task-c7116818, PR #343 f5806122, PH#6c487e37 report 2026-10-15 · status: pending
- 2026-10-15 [MISSING] §routing — to pin one AGY model, set `runner='agy'` and `runner_model='gemini-4-argon-high'` before `delegate_task` and open the description with `override: ceo-order …`; `agy` is not a valid reason code. `db.set_fields` has no `touches` column, so a file added to the scope after create lands through `merge_task(override_touches_check=True)` · evidence: task-1859d58c, `ps` showed `--model gemini-4-argon-high` · status: pending
- 2026-10-15 [MISSING] §measured — Argon (gemini-4-argon-high) on a size-S shell + test fix, edit-only: correct on the first pass in about 9 min, the new test verified to fail on the old code · evidence: task-1859d58c 8a343b3, merged MoonieX-Scriptable 562b4e8 · status: pending
- 2026-10-26 [MISSING] §measured — an AGY research run (claude-sonnet-5-5-high, agy-claude bucket) gets web search back as written summaries with redirect links and cannot open a page: no README, paper or commit list was read, so every external claim came back R (reported) and none V. A research brief whose decision rests on sources goes to a runner with page fetch, or the C-level checks the 3 to 5 claims the decision rests on · evidence: task-aeb9af11 REPORT §Limitations, delegate_log router line · status: pending
- 2026-10-26 [COSTLY] §measured — a headless AGY edit run (PH MrGraph edd58968, kit fix round 2) ended after 1421 s as status ERROR "The stream was interrupted. Please continue the task you were working on.", empty response, one turn, 471,783 tokens, and no file in the work folder changed during the run (last edit 13:19 CET, run 13:21-13:45, next edit 13:47 by the PH). Read the result JSON's status and the target diff before trusting a finished AGY run; a long single turn can come back with nothing · evidence: /opt/MoonieXHQ/Work/mistergraph/agy-kit-fix2.json · status: pending
