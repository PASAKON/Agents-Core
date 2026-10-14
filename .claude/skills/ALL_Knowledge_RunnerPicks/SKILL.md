---
name: ALL_Knowledge_RunnerPicks
kind: knowledge
description: KNOWLEDGE — Which runner:model:effort to send each job kind to (code, fix, review, research, docs, decision …), read from reviewers' verdicts on real runs (hub events runner_fit), with the trials already measured. Trigger on /ALL_Knowledge_RunnerPicks, "ใช้โมเดลไหน", "ส่งงานนี้ให้ใคร", "which model for", "runner picks", "effort เท่าไหร่". Do NOT use it for a runner's own facts (CTO_Knowledge_AGY/Codex/Jules/Haiku), how to brief it (CXO_Protocol_DelegateExternal) or whether to route outside at all (CXO_Gate_RouteFirst).
owner: CTO
audience: [all]
created_by: agent
author: {role: project_head, date: "2026-10-14"}
improved_by: []
aka: [runner-picks]
verified: "2026-10-14"
refresh_after: "2026-10-21"
---

# Runner picks — which runner:model:effort for which job

CEO 14 Oct: picks come from real work, not separate trials. The CTO, PHs (CTO lane) and the CMO lane comment
on their own lane's runs; this skill is the table those comments make.

## Where the data comes from
- **The verdict:** one `runner_fit` event per reviewed task, written at review time by `tools/runner_fit.py`
  (CXO_Gate_RouteFirst Gate 5): job, pass/redo/fail, `--why` (the reviewer's one line), first pass (computed:
  pass, iteration 0, no reviewer fix). Nothing else to fill in.
- **The model and effort:** the task row's `runner_model`, spelled `<model>[:<effort>]`, copied into the event.
  Codex with no model is recorded as `gpt-6-astra:default`. AGY model names carry the effort (`-high`).
- **The table:** `bash scripts/hub/org-python.sh tools/runner_picks.py` (`--since <date>`, `--write <path>`).
  A cell with fewer than 3 reviewed runs prints "—" and is not a pick.
- **The router** reads the same events through `tools/model_stats.py`, per (runner, model).

## Picks (table of 14 Oct; refresh from `tools/runner_picks.py`)
| Job | Pick (≥3 runs) | Runs · first pass | What reviewers said |
|---|---|---|---|
| fix (S/M, file-scoped) | `agy:gemini-4-argon-high` | 4 · 2/4 | Argon trial: judge 8–9/10 blind, beats Sonnet on points (below) |
| fix | `claude:claude-sonnet-5-5` | 4 · 3/4 | same trial; better strict first pass than Argon |
| research (read-only, cited) | `codex` (model unknown) | 4 · 4/4 | cites sources, says plainly when nothing official exists |
| code, docs, tests, review, skill | — | under 3 runs each | no pick yet: comment every run |

## Measured outside the table (trials before 14 Oct)
- **Argon vs Sonnet** (argon-trial-2026-10, landed 9c078b65): Argon 8 vs Sonnet 6 judge points, but strict first
  pass on dev was 2/5. Rule from it: dev S/M goes to Argon **with a CTO/PH review**; no phase 2.
- **Haiku 5.5** (trial 10-11): 0.66/0.72 of Sonnet against a 0.90 bar. Failed; Sonnet stays the cheap Claude.
- **Codex effort was never set** before PR #320: 59 of 60 runs up to 14 Oct were gpt-6-astra at the CLI default
  (`low`). Treat older Codex comments as "astra, low effort", not as Codex at its best.
- **Jev** (`typesafe/jev-1.13`, OpenRouter) is the pick for **decision** jobs (typed choice/score, fast and cheap).
  How to use it: `ALL_Knowledge_Jev`. CEO Q-20261014-1239-4f5b: "JEV = Jev lab, not a Codex model"; he wants
  its usage studied further.

## Rules
1. A pick needs ≥3 reviewed runs in one cell. One sighting goes in a Field note, not the table (ADR 0026).
2. Record every review with `tools/runner_fit.py task <id> --job … --result … --why "…"`. A failure caused by the
   setup (permission, sandbox, missing tool) is `--result fail --fail-reason other` with that cause in `--why`.
3. When a brief names a model, give the effort too (`codex:sol:high`). Without it Codex runs at its default.
4. Runner facts (quota, hosts, shell) live in CTO_Knowledge_AGY / CTO_Knowledge_Codex / CTO_Knowledge_Jules /
   CTO_Knowledge_Haiku. Do not copy them here.

## Open
- "Menium" (CEO's list of Codex models, 14 Oct) matches no CLI model; not answered on Q-20261014-1239-4f5b.
- Codex CLI 0.155 models: gpt-6-astra, gpt-6-sol, gpt-6-luna, gpt-reserve, gpt-5.6-sol/terra/luna, gpt-5.5.
- Jules: no reviewed run in `runner_fit` yet.

## Field notes
- 2026-10-14 [MISSING] Rules — AGY review task-8cc2b28e produced no output: headless AGY auto-denied `read_file`. An environment failure, not the model's · evidence: task-8cc2b28e report · status: pending
- 2026-10-14 [MISSING] Picks — Codex gpt-6-sol (default effort) built a 4-part spec (launcher, router, stats, table) in 16 min with green tests; missed one Postgres-shape test · evidence: task-0e3dd035, PR #320 · status: pending
