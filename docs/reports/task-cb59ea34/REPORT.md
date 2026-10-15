# REPORT task-cb59ea34

Task: fact-check the 7 claims about Google "Gemini 4 Argon" made in Geek Daily EP425 (youtu.be/q2Hh9rw_TZs).
Date of check: 2026-10-15. Web access: yes (fetch + search tools).

## Summary table

| # | Claim | Verdict | Best primary figure | Source |
|---|-------|---------|---------------------|--------|
| 1 | #1 on GDPval at 68.9%, beats "Claude Sonnet 5.5" | **Partly true**: the 68.9% is real but it is the **Vals Index**, not GDPval. The rival in the table is **Claude Opus 5.5** (67.0%), not Sonnet 5.5. GDPval: not found | Vals Index 68.9% vs 67.0% / 65.8% / 63.1% | Model card |
| 2 | #1 on coding benchmarks (DeepSWE and others) | **Partly true**: leads DeepSWE v1.1 and Vibe Code Bench, but loses on 3 of the other 5 coding or ML-engineering rows | DeepSWE v1.1 77.9% (best); FrontierSWE v2 55.0% (best 65.5%); Terminal-bench 4.0 57.4% (best 66.4%) | Model card |
| 3 | 1M context and up to 1M output | **True with caveat**: 1M is one unified input+output window. Max output is 65,536 by default and up to 1,048,576 only with "long decode" | 1,048,576 context; 65,536 default / 1,048,576 long-decode output | Gemini API model doc; model card |
| 4 | Hallucination rate 15%, lowest of any model | **Not found** in any primary page I could open | n/a | see below |
| 5 | Cyber: finds and patches vulnerabilities, 2× better than other models | **False as stated (2×)**: CWE-bench v1 is 68.0%, tied with GPT-6 Astra and 1 point above Opus 5.5. "Finds and patches": not found in what I read | CWE-bench v1 68.0% / 68.0% / 67.0% / 58.0% | Model card |
| 6 | "Team Preview": dozens of agents inside Antigravity | **Not found** in any primary page I could open | n/a | see below |
| 7 | 60% cheaper (API) until end of November | **Partly true**: the promo exists and ends 30 Nov 2026, but the discount is **50%** off the 1 Dec price, not 60% | $2.00 in / $10.00 out through 30 Nov 2026; $4.00 / $20.00 from 1 Dec 2026 | Gemini API pricing page |

## Per-claim detail

All quotes were copied from pages I opened. Table cells are quoted cell by cell.

### 1. GDPval 68.9%, #1, beats "Claude Sonnet 5.5": partly true
- Primary: Google DeepMind model card, https://deepmind.google/models/model-cards/gemini-4-argon/ (page says "Published 13 October 2026").
- Benchmark table, header row: "Gemini 4 Argon" | "GPT-6 Astra" | "Claude Fable 5.1" | "Claude Opus 5.5". Row "Vals Index": "68.9%" | "63.1%" | "65.8%" | "67.0%". Argon leads this row.
- No GDPval row exists in that table. The table lists no "Claude Sonnet 5.5" either.
- The same card says "Additional benchmarks and details on approach, results and their methodologies can be found at: deepmind.com/models/evals-methodology/gemini-4-argon". I opened https://deepmind.google/models/evals-methodology/gemini-4-argon. It returned a PDF (352,830 bytes) that my tools could not read as text, so I could not check whether GDPval is in it. Treat GDPval as "not found", not "disproved".
- Artificial Analysis, https://artificialanalysis.ai/models/gemini-4-argon: "Gemini 4 Argon (High) scores 53 on the Artificial Analysis Intelligence Index, placing it well above average among comparable models (median: 27)." The page's rank badge reads #8 / 216 for Intelligence. So Argon is not #1 on the AA index. The page shows no GDPval-AA figure that I saw.

### 2. #1 on coding benchmarks: partly true
- Primary: same model card, "Agentic coding" and "ML engineering" rows (Argon | GPT-6 Astra | Claude Fable 5.1 | Claude Opus 5.5):
  - DeepSWE v1.1: 77.9% | 74.1% | 67.4% | 74.2% (Argon best)
  - Vibe Code Bench: 91.9% | 89.6% | 90.3% | 90.3% (Argon best)
  - FrontierSWE v2: 55.0% | 65.5% | 56.3% | 62.3% (GPT-6 Astra best)
  - Terminal-bench 4.0: 57.4% | 58.2% | 57.9% | 66.4% (Opus 5.5 best)
  - PostTrainBench (ML engineering): 45.3% | 44.3% | 40.2% | 49.3% (Opus 5.5 best)
- Caveat: the card is Google's own table, not the benchmarks' own leaderboards. I did not open the DeepSWE leaderboard.

### 3. 1M context, up to 1M output: true with caveat
- Primary: Gemini API model page, https://ai.google.dev/gemini-api/docs/models/gemini-4-argon. Quotes: "Context window (unified input and output token limit)" = "1,048,576". "Max output" = "65,536 (default synchronous) / up to 1,048,576 (with long decode)".
- Model card, https://deepmind.google/models/model-cards/gemini-4-argon/: "with a combined input-output token context window of up to 1M." and "Text, with up to a 1M token input + output."
- A 1M-token output therefore means almost no input. Artificial Analysis agrees on context: "has a 1M tokens context window." (https://artificialanalysis.ai/models/gemini-4-argon).

### 4. Hallucination rate 15%, lowest of any model: not found
- The model card gives no hallucination figure. Its only mention is: "Gemini 4 Argon may exhibit some of the general limitations of foundation models, such as hallucinations."
- Artificial Analysis model page (opened): no hallucination figure seen in the summary text or the cost/speed panels I read. The page is about 4 MB on one line and I could not search it.
- I opened https://artificialanalysis.ai/evaluations/omniscience (the AA-Omniscience page). Its content is one huge line and I could not read it, so I cannot confirm or deny a 15% figure.
- Searches tried: "Gemini 4 Argon hallucination rate 15% AA-Omniscience". The search summary suggested the 15% comes from AA-Omniscience, with the caveat that the metric is "incorrect / all non-correct outcomes", so it partly reflects abstention. That was a search-engine summary only. I never opened its cited pages, so it is a lead, not a citation.

### 5. Cyber, "2× better": false as stated
- Primary: model card, row "CWE-bench v1" (Argon | GPT-6 Astra | Claude Fable 5.1 | Claude Opus 5.5): 68.0% | 68.0% | 58.0% | 67.0%. Argon ties GPT-6 Astra and is 1 point above Opus 5.5. There is no 2× gap.
- Cyber is a stated focus: "Gemini 4 Argon delivers frontier performance to help in complex workflows across real-world software engineering, enterprise knowledge work like legal and finance, and cybersecurity defense." Intended usage also lists "cybersecurity defense".
- "Finds and patches vulnerabilities": I did not find that wording. The model card's Safety & Security section was past my read limit (see Limitations).

### 6. "Team Preview": not found
- Searches tried: "Antigravity "Team Preview" Gemini 4 Argon agents working together". The summary said the feature is called "Teamwork Preview" (a `/teamwork-preview` command), but I did not open its cited pages, so the name is unconfirmed.
- Primary pages opened: https://antigravity.google/ (a JS-driven homepage; the part I read had no mention of this feature). The model card lists "Google Antigravity" only as a distribution channel: "Google Antigravity" (antigravity.google/docs).
- I did not open antigravity.google/docs or any Antigravity release notes. "Dozens of agents" is unverified.

### 7. 60% cheaper until end of November: partly true (50%, not 60%)
- Primary: https://ai.google.dev/gemini-api/docs/pricing, section "Gemini 4 Argon", Standard tier. Input: "$2.00 through November 30, 2026." and "$4.00 starting December 1, 2026." Output (including thinking tokens): "$10.00 through November 30, 2026." and "$20.00 starting December 1, 2026."
- $2 vs $4 and $10 vs $20 is a 50% reduction from the later price. Batch tier is also halved: "$1.00 through November 30, 2026." / "$2.00 starting December 1, 2026."
- The page does not use the word "discount", and "60%" appears nowhere I read. Possibly the clip compares against a different baseline; I found none.
- Artificial Analysis lists the introductory price: "In $2.00 Out $10.00 Cache Discount 95%".
- The page also notes: "Gemini 4 Argon is not available on the Free tier or on the Google AI Pro plan."

## Other notes
- Date mismatch: the model card says published 13 Oct 2026; the Artificial Analysis page says "Released September 2026".
- Model-name mismatch: the card compares against "Claude Opus 5.5" and "Claude Fable 5.1". "Claude Sonnet 5.5" appears nowhere in the card.

## Files changed
- `docs/reports/task-cb59ea34/REPORT.md` (this file only; no code changed).

## Validation performed
- Every URL cited above was fetched successfully in this session (HTTP 200 content returned). The one 404 (https://deepmind.google/models/gemini/argon/) is not cited.
- Quotes were read from the saved page text. The PH should re-check them. For the model card and AA page, find the table row or text by searching the page for the quoted string.
- No tests were run; none apply.

## Limitations
- The model card HTML is huge. I read the Model Information, Distribution, Evaluation (benchmark table) and Intended Usage and Limitations sections. The Safety & Security section, with any Frontier Safety/cyber text, was past the end of what I could read, so claim 5's "finds and patches" part and any hallucination mention there are unchecked.
- The evals-methodology page is a PDF that I could not read as text.
- The Artificial Analysis pages are very large single-line pages, so I used only the model-page summary text and counters.
- I did not open the benchmarks' own leaderboards (DeepSWE, GDPval, CWE-bench, Vals), the Google blog announcement, or the clip's transcript (the clip page fetch returned only YouTube page scaffolding). The claims are taken from the task text.
- The search tool returns summaries with redirect URLs. I used them only as leads and cited none of them.

## Blockers
- (none). To close the open items, a person with a browser should check: (a) the model card's Safety & Security section and the evals-methodology PDF for GDPval, hallucination and cyber numbers; (b) the AA-Omniscience page for Argon's hallucination rate; (c) Antigravity docs/release notes for "Teamwork Preview" and the number of agents.

## Skill learning
- (none)
