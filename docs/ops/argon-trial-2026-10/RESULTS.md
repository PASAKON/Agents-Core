# Gemini 4 Argon trial: results (2026-10-14)

**Answer.** Argon (agy, `gemini-4-argon-high`) matched or beat Sonnet 5.5 on developer S/M jobs:
- blind judge points 8 against Sonnet's 6 on four paired jobs, a ratio of 1.33 against a bar of 0.90;
- Sonnet's output was WRONG on D3, while Argon's was USABLE on all four.

No job type reaches phase 2. Argon's strict first pass, meaning accepted with no redo and no reviewer fix, was:

| type | strict first pass |
|---|---:|
| developer | 2 of 5 |
| translation | 1 of 3 |
| analysis | 0 of 1 |

The bar is 90%. Argon was also 2 to 6 times slower than Sonnet, and a big job used 15 to 16 points of the agy
`gemini-5h` bucket. Recommended routing:
- **developer S/M:** Argon, always with a CTO review;
- **Thai to English translation:** not routed until the brief says which Thai text stays Thai;
- **shell-free analysis:** undecided, since only one job ran.

How the trial ran: `README.md`. All numbers below are measured unless marked.

## Availability (measured 13 Oct)
- **Contabo:** agy 1.3.4 lists gemini-4-argon-low, -medium and -high.
- **Mac:** agy 1.3.4 lists Argon too, according to MAC CTO #671f688f.
- **Billing:** runs bill to the agy Gemini buckets (`gemini-5h`, `gemini-weekly`). The Claude meters did not move
  because of Argon.
- **Plan:** `/usage` does not show which Google plan this is.

## Per job

| job | type | source | Argon | Sonnet | Argon strict first pass | landed |
|---|---|---|---|---|---|---|
| D1 | dev | LungNote f2209b5b item 1: comment-only checker | Argon alone: redo 1, then pass + fix | — | no | Argon, Agents-Core branch |
| D2 | dev | Console#11 | USABLE 8 | USABLE 9 | yes | Sonnet: Console b946e1e (byte-identical diffs) |
| D3 | dev | Console#27 | USABLE 7 | WRONG 4 | no (3 reviewer fixes) | Argon: Console 15b3f7f, then reverted e3e51fe because the CEO declined the feature (Q-20261013-2045-0404), not because of the code |
| D4 | dev | ClaudeFlow#213 | USABLE 8 | USABLE 9 | yes | Sonnet: ClaudeFlow d3383c1 (byte-identical diffs) |
| D5 | dev | ClaudeFlow#227 | USABLE 9 | USABLE 7 | no (1 reviewer fix) | Argon: ClaudeFlow 4208690 |
| T1 | doc | f2209b5b item 5: winbox recovery runbook | Argon alone: pass + fix (2 lines) | — | no | Argon, Agents-Core branch |
| T2 | doc | item 5: winbox checklist | Argon alone: pass | — | yes | Argon, Agents-Core branch |
| T3 | doc | item 4: session-worktree skill body | Argon alone: redo-level, fixed by the reviewer (11 of 14 lines) | — | no | Argon, Agents-Core branch |
| A1 | analysis | item 5: translation batch plan | Argon alone: pass + fix (totals) | — | no | Argon, Agents-Core branch |

Scores: the blind Opus 5.5 judge's label and 0–10 score on paired jobs; the reviewer's verdict (`review/<job>.json`) on Argon-only jobs.

What the reviewer fixed:
- **D5:** a fake `docker` in the test dumped the whole environment. It now dumps only `SOMPONG_*`.
- **D3:** three fixes: scope, a security change, and per-credential counting.
- **D1:** round 0 ignored indentation in Python and YAML and word spacing in shell, and failed 5 of 35 hidden probes. Round 1 passed all 35. A `#` in the middle of a shell word or a YAML value was still read as a comment; the reviewer fixed that and added six tests.
- **T1:** two Thai sentences that are said aloud to a family member had been translated. They went back to Thai, with an English gloss.
- **T3:** 11 lines went back to Thai: the "say instead" words, a template word, and a tool's output string. Argon had flagged each of them as borderline.
- **A1:** a 2-character slip in one header carried into ten total lines, and Argon gave an invented reason for the gap.

## Per job type

| type | jobs (paired) | Argon / Sonnet judge points | ratio | Argon strict first pass | minutes, paired jobs: Argon / Sonnet | phase 2 |
|---|---|---|---:|---:|---|---|
| developer S/M | 5 (4) | 8 / 6 | 1.33 | 2/5 | 32.3 / 6.3 | no |
| docs / translation | 3 (0) | — | — | 1/3 | — | no |
| shell-free analysis | 1 (0) | — | — | 0/1 | — | no |

## Time and quota per Argon run

Minutes are wall time. Bucket moves are agy `/usage` "remaining %" read before and after each run.

| run | minutes | gemini-5h | gemini-weekly | Sonnet minutes (same job) |
|---|---:|---:|---:|---:|
| D2 | 1.87 | −1.25 | −0.29 | 0.45 |
| D4 | 1.37 | −0.13 | −0.03 | 0.77 |
| D5 | 7.15 | −7.55 | −1.94 | 1.26 |
| D3 | 21.95 | −14.58 | −3.09 | 3.87 |
| D1 r0 | 8.42 | −2.30 | −1.24 | — |
| D1 r1 | 7.27 | −2.94 | −0.73 | — |
| T1 | 4.22 | −1.26 | −0.31 | — |
| T2 | 3.98 | −1.41 | −0.35 | — |
| T3 | 5.73 | −1.68 | +0.41 | — |
| A1 | 24.44 | −16.26 | +5.50 | — |
| **sum** | **86.4** | **−49.4** | about −8 (two readings rose, see caveat 5) | |

- **Sonnet runs:** the Claude meters (`/opt/claude-usage-monitor/usage.json`) moved 0–1 point per run. Those meters
  cover the whole account, including this Opus session, so the cost of a Sonnet run cannot be read from them.
- **A1:** agy returned status `ERROR` ("exceeded the output token limit") after it had written both files completely.
  A runner that trusts that status alone would throw away finished work.

## Caveats
1. **Small sample.** Four paired jobs and five Argon-only jobs. A single job changes any rate here by 20–33 points.
2. **Uneven scrutiny.** Landed Argon outputs (D3, D5) were reviewed line by line, and every fix counts against
   Argon's first pass. The Sonnet outputs that were thrown away got only the judge's read. Argon's strict first-pass
   rate is therefore biased low against Sonnet's.
3. **Strict first pass counts any reviewer fix,** even a two-line one.
4. **Brief faults.** The translation rules kept "text customers or viewers see" in Thai, but they did not name Thai
   words the CEO says to Thai speakers. That gap explains part of T1 and T3.
5. **The agy buckets may include other agy use on Contabo during a run.** The weekly bucket rose 5.5 points during A1
   (estimated cause: the rolling window moved), so weekly figures are rough.
6. **Argon-only jobs have no Sonnet baseline.** After the CEO's 03:40 order, D1, T1–T3 and A1 ran on Argon alone to save
   quota.

## Records
- `runner_fit`: 13 hub events, written 2026-10-14 by `fit.py --write`. Task ids are `argon-trial-<job>` and the
  meter moves are in `why`.
- Raw data, diffs and verdicts: Contabo `state/argon-trial-2026-10/`. They are not committed because the repo is public.
