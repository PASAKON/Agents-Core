# `finance-knowledge/` — CFO + finance workers knowledge bank

Use this for finance work: monthly close, runway forecast, spend
approvals, unit economics, vendor contracts, budget envelopes. Shape
mirrors `mooniex-claudesign/`.

Primary owner: **CFO**. Workers: `data_analyst` when borrowed for
cost queries; future `finops_analyst` when spawned.

## Read order

1. **`craft/`** — conservative-forecasting, source-every-number,
   no-surprise-spend rules.
2. **`envelopes/<brand>-FY<year>.md`** — current budget envelope per
   project. Spend approvals must reference this file.
3. **`skills/<task>/SKILL.md`** — analytic / process shape
   (e.g., `monthly-close`, `runway-forecast`, `unit-economics`,
   `subscription-audit`, `budget-allocation`).

## How CFO uses this bank

- Writes/owns `envelopes/*` per project per fiscal year.
- Cites `skills/<task>/SKILL.md` checklist on approval / decline.
- Updates `craft/conservative-forecasting.md` after every forecast
  error (post-mortem-driven).

## How CTO/CMO/CGO use this bank

- **Before requesting spend:** Read `envelopes/<brand>-FY<year>.md` to
  check available envelope.
- **Before claiming ROAS / LTV / unit econ:** Cross-check `skills/unit-economics/SKILL.md` formula.

## Hard rules

1. **No surprise spend.** Every dollar routes through CFO with envelope
   citation.
2. **Conservative forecasts.** Headline number = low end of realistic
   range. Mid + high in body.
3. **Source every number.** Tie every figure to invoice / API event /
   ledger row.

## See also

- `LLMs/playbooks/knowledge-structure.md`
- `LLMs/playbooks/cfo-spend-approval.md`
- `roles/cfo.md` (CFO system prompt)
