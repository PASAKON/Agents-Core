# `data-knowledge/` — data_analyst knowledge bank

Use this when producing analytic artifacts: funnel reports, cohort
retention, ROAS attribution, dashboards, SQL queries, KPI summaries.
Shape mirrors `mooniex-claudesign/`.

## Read order (workers MUST follow on every task)

1. **`craft/`** — universal don'ts (statistical discipline, PII handling,
   chart honesty).
2. **`models/<brand>/MODEL.md`** — KPI definitions + formulas for that
   brand (CAC, LTV, retention curve shape, attribution window). If
   missing, ask CGO/CFO to author.
3. **`skills/<analysis>/SKILL.md`** — analytic shape
   (e.g., `funnel-analysis`, `cohort-retention`, `roas-attribution`,
   `event-quality-audit`).

## How CFO/CGO use this bank

- **CFO:** `models/<brand>/MODEL.md` is the official KPI ledger.
  Forecasts MUST cite the formula source from here.
- **CGO:** Same models, used for attribution + lift measurement.

## Hard rules

1. **Source every number.** Every number in a report must cite query +
   source table (e.g., `webapp_activity_log row count where ts > X`).
2. **PII handling.** Email/phone/IP only in aggregate or k-anonymized.
   No raw user_ids in shared output unless explicitly approved.
3. **No p-hacking.** State hypothesis + min_sample before query.
4. **Chart honesty.** Y-axis starts at 0 for absolute counts. Time
   series share consistent x-axis range when compared.

## See also

- `LLMs/playbooks/knowledge-structure.md`
- `roles/data_analyst.md`
