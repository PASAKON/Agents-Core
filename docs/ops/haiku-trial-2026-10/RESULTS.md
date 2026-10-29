# Haiku 5.5 shadow trial — result (2026-10-11)

**Verdict: FAIL on both jobs. Haiku 5.5 is not routed to either job; Sonnet 5.5 stays.**
No ADR 0009 addendum (the order asked for one only on a pass). Protocol, Step 1 proof and how to re-run: `README.md`.
Ran 2026-10-11 13:59–14:29 Thai on Contabo, Claude Code 2.1.289, 300 calls, 0 errors, all 300 served by the model asked for.

## Quality (blind Opus 5.5 judge, CTO blind audit of every WRONG before unblinding)

| Job | Model | Usable as is | Correct, needs edits | Wrong | Points (2/1/0) | Haiku ÷ Sonnet | Bar |
|---|---|---|---|---|---|---|---|
| 1 Field-note drafts | Haiku 5.5 | 10 | 36 | 4 | 56 | **0.66** | 0.90 ✗ |
| | Sonnet 5.5 | 35 | 15 | 0 | 85 | | |
| 2 REPORT.md summary | Haiku 5.5 | 19 | 25 | 6 | 63 | **0.72** | 0.90 ✗ |
| | Sonnet 5.5 | 39 | 9 | 2 | 87 | | |

- **Rule safety held:** 0 of 100 job-1 drafts flagged rule_risk by the judge, and an objective scan of all 100 found
  no heading outside the 70 real skills and no status other than `pending`. Haiku's 4 wrong notes would have
  recorded a false fact (a docstring said to exist that does not, a 2025 date, a reversed sentence, a
  claim about git's docs), not changed a rule.
- **Audit:** 14 WRONG verdicts read blind; 12 confirmed, 2 lowered to CORRECT (after unblinding: one Haiku draft,
  j1-09, and one Sonnet draft, j1-42). Without the audit job 1 is 55/84 = 0.65; the verdict does not depend on it.
  Spot check of 4 random USABLE job-1 verdicts: all held. No job-2 draft names a file absent from its input.
- **What Haiku gets wrong:** job 1 — drops details from the worker's line (35 of its 36 "needs edits"), leaves out
  the task id in evidence (23). Job 2 — overclaims or underclaims test runs (12), drops main points (10), pads open
  items with speculation (6); its 6 wrong reports include a brief misread ("run the installer" where the brief said
  do NOT), a wrong test count (7 vs 9), and calling logged facts "not shown".

## Time, tokens, quota (47 non-pilot calls per batch; pilot items included in totals)

| Job | Model | Median wall | p90 wall | Output tok (of which thinking) | Prompt tok | List-price equivalent |
|---|---|---|---|---|---|---|
| 1 | Haiku 5.5 | 9.0 s | 14.4 s | 87,746 (66,659) | 192,140 | $0.08 |
| 1 | Sonnet 5.5 | 9.1 s | 12.9 s | 49,424 (24,916) | 193,991 | $1.16 |
| 2 | Haiku 5.5 | 17.0 s | 25.9 s | 171,804 (128,361) | 445,844 | $0.18 |
| 2 | Sonnet 5.5 | 12.9 s | 18.3 s | 72,322 (23,641) | 447,693 | $2.51 |
| both | Opus 5.5 judge | 12.0 s | — | — | — | $9.21 |

- **Not faster:** at effort high Haiku thinks 3–5× more than Sonnet, so it is as fast on job 1 and slower on job 2.
- **Quota (the plan's own meters, 1-point resolution):** each 47-call generation batch moved the 5-hour meter by
  0–1 point, Haiku and Sonnet alike; the Opus judge moved it 3 points; the 7-day meter stayed at 89% throughout.
  The meters cannot separate Haiku's draw from Sonnet's at this volume. List prices put Haiku at ~1/15 of Sonnet.
- Prices: platform.claude.com/docs/en/about-claude/pricing, read 2026-10-11 (Haiku 5.5 $0.10/$0.50 ≤100k prompt,
  $0.50/$2.50 above; Sonnet 5.5 $2/$10; Opus 5.5 $4/$20; 1h cache-write rate, which Claude Code uses).

## What this does not cover

- One effort level (high, the Sonnet worker standard). Haiku at medium would think less and might be faster;
  its quality there is unmeasured. A retry would be a new trial, not this one.
- Job 2's "log" is the branch commit log; worker transcripts were not available on Contabo.
- The judge is a model. The audit covered every WRONG verdict, not every USABLE/CORRECT one.

Raw items, drafts, verdicts and `results.json`: `state/haiku-trial-2026-10/` on Contabo (not in git — this repo is
public and the items quote internal reports).
