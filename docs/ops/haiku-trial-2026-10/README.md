# Haiku 5.5 shadow trial — protocol (2026-10-11)

Order: CEO "ได้เลย" 2026-10-11 via SomPong (COO) · LungNote todo `6f825cac` (twin `bcc1eb36`) ·
results due 2026-10-25 · owner: Contabo CTO (model routing = ADR 0009) · background:
SomPong `docs/research/2026-10-11-claude-haiku-5-5-org-fit.md` (1d2cb60, 2aecd88).
**Shadow only:** no output of this trial is filed into a skill, a task or a report.

## Step 1 — does the CLI really run Haiku? (done before any score)

Claude Code on Contabo is now **2.1.289** (the todo said 2.1.286). `claude -p --model claude-haiku-5-5`
still prints `[claude-code:unrecognized_model] {"model":"claude-haiku-5-5","query_source":"sdk"}` on stderr.
Evidence that the request was not quietly answered by another model (`step1/` in the data dir):

| Check | Haiku run | Sonnet run |
|---|---|---|
| `system/init.model` | claude-haiku-5-5 | claude-sonnet-5-5 |
| API reply `message.model` (set by the server) | claude-haiku-5-5 | claude-sonnet-5-5 |
| `modelUsage` key / `canonicalModel` | claude-haiku-5-5 | claude-sonnet-5-5 |
| Speed, same 350-word prompt | 228 output tok/s (incl. 1,579 thinking) | 105 tok/s, no thinking |

Every one of the 300 trial calls also records `message.model`; `score.py` counts any call whose served model
differs from the one asked for (`served_as_asked`).

What the CLI gets wrong for an id it does not know: it reports Haiku's context window as **200,000** (real: 1M),
so auto-compact would fire early in a long session, and its `costUSD` has `costBasis: "unknown"`
(it priced a one-word "pong" at $0.052, more than Sonnet). Ignore the CLI's dollar figure for Haiku; `score.py`
prices tokens from the official price page instead.

## The two jobs (50 items each, real org data, seed 20261011)

| Job | Input the model gets | Items from |
|---|---|---|
| 1 Field-note drafts | a finished task's `## Skill learning` block, the 70 real skill names (38 rename stubs listed as old names), the drafting rules (ADR 0026, SkillAuthor §5) | 164 done tasks with a typed WRONG/MISSING/COSTLY line |
| 2 REPORT.md summary | the brief (≤4k chars), the branch's commit log, diffstat and diff (≤30k chars; 4 of 50 cut) | 302 tasks merged into Agents-Core (30 developer, 15 browser_operator, 5 other) |

Job 2 never sees the worker's report: `docs/reports/**`, `REPORT.md` and `WORKER.md` are cut from the diff.
"Log" means the branch's commit log: only 9 worker transcripts survive on Contabo, too few for 50 items.

## Calls

Same for both models: `claude -p --effort high` (the Sonnet worker standard), one fixed system prompt
(`run.py`), no tools, no MCP, no session file, cwd in an empty temp dir, at most 2 calls at once (8 GB box).
Recorded per call: served model, tokens (prompt, output, thinking), wall and API time, the plan's
5-hour/7-day meters. A run stops starting calls if the 7-day meter reaches 92%.

## Blind scoring

Judge: Opus 5.5 at effort high (`judge.py`). It sees the input, the rules the writers had and two drafts
labelled A and B; a seeded coin per item decides which model is A, and the key sits in `key.json`, which only
`score.py` reads. Job 2's judge also sees the worker's own report as a reference.
Labels: **USABLE** (correct, commit or post as is) = 2 points · **CORRECT** (nothing false, needs edits) = 1 ·
**WRONG** = 0. Job 1 also gets `rule_risk` (committing it would change, flip or wrongly attack a rule).
Before unblinding, the CTO reads every WRONG and every rule_risk verdict with the key closed and confirms or
overturns it (`audit.json`, applied by `score.py`).

**Pass, per job:** Haiku's points ≥ 90% of Sonnet's, and (job 1) zero Haiku drafts with rule_risk.

## Run it

```bash
bash scripts/hub/org-python.sh docs/ops/haiku-trial-2026-10/build_items.py      # items (hub + git)
python3 docs/ops/haiku-trial-2026-10/run.py --job 1 --model claude-haiku-5-5     # x2 jobs x2 models
(cd docs/ops/haiku-trial-2026-10 && python3 judge.py --job 1 && python3 score.py)
```

Raw items, drafts and verdicts live in `state/haiku-trial-2026-10/` (self-gitignored: this repo is public and
the items quote internal reports). Results: `RESULTS.md`.
