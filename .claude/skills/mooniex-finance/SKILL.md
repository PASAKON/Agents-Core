---
name: mooniex-finance
owner: CFO
origin: mooniex-org
scope: >-
  MoonieX-grounded org finance only — the real webapp_cfo_* tables, how
  /admin/finance computes its tiles, ratified budget policy, card-to-vendor
  mapping, monthly close. Not general accounting: for standard bookkeeping
  (journal entries, reconciliation, SOX) use the finance:* skills instead.
description: The org's finance authority — budget, runway, burn, subscriptions, /admin/finance, and the webapp_cfo_* tables. Trigger on /mooniex-finance and on "budget", "runway", "burn", "spend", "subscription", "CFO", "cost tracking", "monthly close", "ค่าใช้จ่าย", "งบ". Use instead of the generic finance:* bookkeeping skills, which are not MoonieX-grounded.
created_by: human
audience: [cfo]
---

# MoonieX Finance & Cost-Tracking Skill

You are the MoonieX finance authority for the CFO role. This skill is the
codebase-grounded reference for org spend: the real tables, the real
dashboard, the ratified policy, and the traps that have already bitten a
past CFO session — so you don't rediscover them from scratch every time.

## Operating Principles

1. **Never trust the dashboard number alone.** `/admin/finance` reads from
   `webapp_cfo_subscriptions`, which is populated by manual migrations, not
   live provider sync. It goes stale silently. Before reporting a fixed-cost
   figure as fact, cross-check at least the largest line items against a
   real Gmail receipt or provider dashboard. (Confirmed 2026-07-02: the
   dashboard showed Anthropic at $214/mo for over a week after it had
   actually dropped to $20/mo — nobody had re-verified.)
2. **ASK before any paid top-up.** State the exact $ amount and wait for
   explicit CEO OK before spending on OpenRouter, fal.ai, or any other
   usage-based provider. A rejection is not the same as "no charge happened"
   — verify the provider dashboard balance either way.
3. **Merging code ≠ fixing prod data.** A DB migration only takes effect
   once it actually *runs* against the live Supabase instance (via the
   migrations runner / `/admin/migrations`), separately from the Vercel code
   deploy. After merging a task that includes a migration, always re-check
   the live page — don't report "fixed" from the merge confirmation alone.
4. **CFO cannot enter payment credentials anywhere.** Card updates on
   Vercel/Anthropic/etc.'s own billing pages are always a CEO action. CFO's
   job is to diagnose the problem (e.g. "card •1848 is dead, causing 5
   failed charges") and hand back the exact fix needed — never to enter
   card data.
5. **Trace every dollar.** Every number in a CFO report should be
   traceable to a specific source: a Gmail receipt ID, a migration file, a
   wiki decision doc, or a live dashboard screenshot — not a remembered
   figure from a prior session.

---

## 1. Real Data Architecture (Supabase, `webapp_cfo_*` prefix — IRON §4)

| Table | Purpose | Notes |
|---|---|---|
| `webapp_cfo_api_events` | Every paid API call: provider, project, agent, cost, tokens | Feeds "Spend by provider" MTD table on `/admin/finance` |
| `webapp_cfo_subscriptions` | Fixed recurring cost per vendor | **Manually maintained via migrations, not live-synced.** Columns include `vendor`, `plan`, `monthly_usd`, `est_cost_usd_month`, `is_estimate`, `billing_day`, `next_renewal`, `card_on_file`, `active`, `notes`, `priority_tier`. `active=true` rows sum into the Monthly Burn / Runway tiles. |
| `webapp_cfo_subscriptions_meta` | 🆕 (2026-07-02) Single-row "subscriptions last verified" stamp: `last_verified_at`, `verified_by`, `note` | Manual CFO/CEO-set config, per the hardcode-vs-automatic principle (§4 below) — never auto-computed from `updated_at`. Update this every time you do a real reconciliation pass. |
| `webapp_cfo_daily_rollup` | Daily aggregation, written by a 00:05 UTC cron | — |
| `webapp_cfo_alerts` | Anomaly / budget-breach feed | Spend-spike alerts shown at the top of `/admin/finance` |
| `webapp_cfo_config` | Manual CEO/CFO-set values (budget envelope, cash-on-hand) | Referenced in `decisions/2026-06-23-cfo-api-budget-control.md`; replaces old env-var hardcoding |
| `webapp_cfo_api_limits` | Per-provider monthly spend limit (config, not derived) | Drives the quota-gauge 🟢🟡🔴 |

## 2. `/admin/finance` — how the tiles actually compute

Source: `src/lib/cfo/report.ts` (`getCfoSnapshot()`), rendered by
`src/app/admin/finance/FinanceClient.tsx`.

- **Monthly Burn** = sum of `monthly_usd` over `webapp_cfo_subscriptions` where `active = true`, plus variable API MTD from `webapp_cfo_api_events`.
- **Runway** = cash on hand (`webapp_cfo_config` / historically `CFO_CASH_BALANCE_USD`) ÷ Monthly Burn, capped display at 24mo (a genuine UI quirk observed 2026-07-02: the number itself can render above the stated cap, e.g. "58.0 months... capped at 24mo" — cosmetic, not a data bug, don't over-investigate).
- **Budget Envelope** = the ratified org AI cap ($500/mo, ฿17,000 — `decisions/budget-FY2026.md`), forecast % = linear MTD extrapolation.
- **Spend by provider** table = `webapp_cfo_api_events` grouped by provider, MTD. If a provider shows calls with 100% `FAILED` status and $0 cost, that usually means the provider's balance hit zero and every call is bouncing — an operational outage, not a "no spend" fact. Cross-check the provider's own dashboard/balance before concluding usage is genuinely zero.
- **Subscriptions table flag/status derivation** — see the gotcha in §5, this is the single most-bitten piece of this dashboard.

Report API: `GET /api/cfo/report?period=mtd[&format=md]`.

## 3. Ratified Budget Policy

| Policy | Value | Source |
|---|---|---|
| Org AI monthly cap | $500/mo (฿17,000 @ ฿34/$) | `decisions/budget-FY2026.md`, ratified CEO 2026-06-12 |
| Claude subscription tier | Downgraded Max→Pro effective 2026-06-22, $214→$20/mo | Gmail receipt #2844-1297-3030; verify against `/admin/finance` staying in sync |
| Per-campaign paid-media spend authority | CMO standalone ≤$50, CFO-notify $51-200, CFO-approve $201-500, CFO+CEO $501-2000, CEO+board >$2000 | `decisions/2026-05-25-marketing-budget-authority.md` |
| Per-brand campaign cap | WarpClip $300, MoonieX $500, LungNote $200, Option/Alphatrader/Moonx $300 | same ADR |
| Channel monthly cap (rollup) | Meta $1500, Google $1000, TikTok $500, LINE OA paid $300 | same ADR |
| Hardcode-vs-automatic principle | System-derived numbers (spend, tokens, balance) = always live/automatic, never hardcoded. CEO/CFO config (budget envelope, cash-on-hand, per-provider limits, "last verified" stamps) = manual, settable, stored in DB not env vars. | `decisions/2026-06-23-cfo-api-budget-control.md` |
| Quota gauge thresholds | 🟢 <70% · 🟡 70-90% · 🔴 >90%, resets 1st of month (Thai time) | same ADR |
| Vercel hard cap | $20 base + $1 overage = $21 max, Spend Management pauses prod above it | IRON §16 |

## 4. Card / Vendor Payment Mapping

**Hard rule: never store full card numbers, expiry, or CVV — last-4 only.**

As of 2026-07-02 (Gmail-verified, previous mapping in the registry was wrong on multiple points):

| Card/wallet | Actually pays for |
|---|---|
| MC prepaid •2011 | Anthropic (Claude Pro), Vercel (intended — see gotcha below) |
| MC prepaid •1848 | 🔴 dead/cancelled card, was still on file for Vercel, caused a string of failed charges until CEO caught it |
| MC prepaid •2587 | Previously assumed to be the Anthropic/Vercel card — this was **wrong**. Actual usage unclear as of 07-02, likely just domains. Re-verify before relying on it. |
| TrueMoney wallet •8330 | Google One (auto-debit), plus ad-hoc manual top-ups (CEO has used it to clear OpenRouter/Vercel dues directly) |

**Gotcha:** a payment method being "on file" per the org's own notes does not mean it's the one actually being charged — always reconcile against a real receipt, not the registry's prior assumption.

## 5. Known Dashboard Gotchas (learn from these, don't re-discover them)

### 5.1 The notes-field regex self-trigger (found + fixed 2026-07-02)
`FinanceClient.tsx`'s `deriveSub()` flags any subscription "Cancel" if its
free-text `notes` column matches `/cancel|kill|untracked|dead|terminat/`
(case-insensitive, **substring, not word-bounded** — "cancelled",
"termination", "undead" would all match). This is independent of the
`active` boolean, which is the real source of truth for whether it counts
in the burn total.

Two real incidents from this bug:
- Contabo (a live prod VPS) got flagged "Cancel" because its notes
  mentioned retiring the *old Hostinger* VPS during a cutover — unrelated
  text, same regex match.
- The **first fix attempt** for that bug re-triggered itself: the
  explanatory notes text used the literal word "cancel" to describe the
  bug, re-matching the same regex it was trying to clear. Second fix had
  to paraphrase around the trigger words entirely (e.g. "stop-word flag
  check" instead of naming "cancel" directly) and added a self-verifying
  SQL assertion that greps the final notes text for all 5 trigger words
  before allowing the migration to succeed.

**When writing or editing any subscription's `notes` field: grep your own
new text for cancel/kill/untracked/dead/terminat before committing it.**
Don't just eyeball it — write the assertion, like the fix above did.

### 5.2 Merge ≠ live
Merging a task's branch (`merge_task`) pushes code to the default branch
and, if the repo has Vercel's GitHub integration, triggers a build — but
does **not** run any bundled SQL migration against the production Supabase
instance. That's a separate step (this repo's migrations runner /
`/admin/migrations`). Confirmed 2026-07-02: a migration's data changes
appeared live within ~10 minutes of merge without an explicit "run
migration" action being taken by the CFO session — suggesting *something*
in the deploy pipeline does apply pending migrations automatically, but
this has not been confirmed as guaranteed behavior. **Always re-check the
live page after a merge; never report a DB fix as done from the merge
confirmation alone.**

### 5.3 "Deploy events" page can lie
`/admin/deploys` has shown every row (including ones already confirmed
live via the Finance page itself) stuck at status "queued", with the page
subtitle literally reading "connecting..." — its Supabase Realtime
subscription hadn't established. Don't treat that page as ground truth if
it contradicts a direct check of the actual feature page.

### 5.4 100% failed API calls ≠ zero spend
If `webapp_cfo_api_events` shows N calls for a provider with N failures and
$0 cost, don't report "no spend this month" — check whether the provider's
balance hit zero (calls failing = an active outage, not idle usage).

## 6. Monthly Close / Gmail-Receipt-Verification Workflow

When asked "is this month's budget enough" or to reconcile subscriptions:

1. Pull the current `/admin/finance` state (screenshot + `get_page_text`, note the routing sometimes needs a scroll/screenshot rather than `get_page_text` right after `navigate` — the SPA occasionally renders the wrong route's content for the first read).
2. Cross-check the largest fixed line items against real Gmail receipts —
   `search_threads` grouped by vendor domain, `after:` the last verified
   date. Don't trust "confirmed" labels from a prior session without a
   receipt citation.
3. If a discrepancy is found, write the corrected numbers to
   `projects/finance.md` and `decisions/subscriptions-registry.md` in the
   wiki **before** spawning a dev fix — the wiki is the paper trail even if
   the DB fix takes a few rounds.
4. Delegate the DB/display fix as a `developer` task on `mooniex-webapp`
   (touches: `app/admin/finance`, `lib/cfo`, `supabase/migrations`). Include
   in the task description: the exact old→new values, the receipt/evidence
   citation for each, and an instruction to write a self-verifying SQL
   assertion rather than just eyeballing correctness.
5. Run the CTO merge-checklist gates before merging (see `/cto-merge-checklist`
   skill) — CFO has merge authority for finance/cost-tracking branches.
6. **Re-verify live** after merge (§5.2) before reporting the fix as done.
7. Update `webapp_cfo_subscriptions_meta.last_verified_at` (via the dev
   task) so the dashboard's "last verified" banner reflects the real
   reconciliation date, not just "page rendered."

## 7. Live Provider Balance — already built, don't re-invent

`/admin/api-health` (`src/lib/api-health/openrouter.ts` + `fal.ts`) already
fetches live balance, not just uptime:

- **OpenRouter:** `GET https://openrouter.ai/api/v1/credits`, header
  `Authorization: Bearer ${OPENROUTER_API_KEY}`. Response
  `data.total_credits - data.total_usage` = live balance. Shown directly
  on the page as "BALANCE $X.XX".
- **fal.ai:** `GET https://api.fal.ai/v1/account/billing?expand=credits`,
  header `Authorization: Key ${FAL_API_KEY}` → `credits.current_balance`.
  **Caveat confirmed 2026-07-02: this silently returns 401/403 (balance
  hidden, page just shows "$0.0000 spent" with no BALANCE line) unless
  FAL_API_KEY has admin scope** — a regular model-call key won't show
  balance. If fal balance is needed live, check/upgrade the key's scope
  first rather than assuming the integration is broken.

Don't re-build a balance fetcher — this one exists and is called on every
page load (`auto-refresh 30s`). If asked "what's the OpenRouter/fal
balance," check `/admin/api-health` before doing anything else.

## 8. Wiki Path Index

| Path | What it holds |
|---|---|
| `decisions/budget-FY2026.md` | Org-level budget cap, cash on hand, Claude Max tier |
| `decisions/subscriptions-registry.md` | Full vendor/card/billing-day registry — the CFO's working ledger |
| `decisions/cost-tracking-policy.md` | Active cost-tracking policy |
| `decisions/2026-06-23-cfo-api-budget-control.md` | Hardcode-vs-automatic principle, quota gauge rules, variable-API tracking scope |
| `decisions/2026-05-25-marketing-budget-authority.md` | Per-campaign / per-brand / per-channel spend gates for CMO/CGO |
| `projects/finance.md` | CFO meta-project — table list, dashboard status, open tasks, monthly close ritual |
| `mooniex-webapp/src/lib/cfo/report.ts` | The actual burn/runway/subscription computation code |
| `mooniex-webapp/src/app/admin/finance/FinanceClient.tsx` | The actual dashboard rendering + flag-derivation logic |
| `mooniex-webapp/supabase/migrations/2026060*__webapp_cfo_subscriptions_*.sql` | Migration history for the subscriptions table — read recent ones before writing a new one, to match the established idempotent-hint pattern the migrations runner lints for |

## 9. Invoice / quotation generator

Moved here from the org memory index 2026-08-25.

`scripts/invoice_gen/generate_invoice.py` renders FlowAccount-style Thai QT/INV
PDFs from a JSON data file via headless Chrome:
`python3 generate_invoice.py <data.json> [out.pdf]`. Output defaults to
`output/invoices/<doc_no>.{pdf,html}`. A JSON list is a batch.

Fields: `doc_type` (quotation|invoice), `doc_no`, `date` (DD/MM/YYYY),
`seller{name,address}`, `contact`, `customer{name,lines[]}`,
`items[{desc,sub[],qty,unit,amount}]`, `currency`, `fx_rate`, `notes[]`.
Signature-block pre-fill: `seller_sign_date` / `customer_sign_date`.

**`sample_axi.json` is a STALE sample (April/$569) — not live data.** The real
Axi document is `axi_qt2026030001.json` (June/$284, QT2026030001, 15/06/2026).

**Drive backup of finance documents.** The CEO's finance docs live at
`~/Library/CloudStorage/GoogleDrive-pass.gob1@gmail.com/ไดรฟ์ของฉัน/Mooniex Finance/`
— the Drive is Thai-locale, so "My Drive" is `ไดรฟ์ของฉัน`. Six category folders:
Invoices, Quotations, Contracts, **Company Docs** (registration / หนังสือรับรอง —
irreplaceable), Payslips, Marketing. Backup means COPY; the local Desktop copy
stays. No `gdrive` or `rclone` CLI is installed — use the CloudStorage sync
folder. Thai accounting-document retention is 5 years.

## 10. Subscription inventory — what each SaaS line actually pays for

Moved here from the org memory index 2026-08-25. From the CFO billing audit of
2026-06-19 (Gmail). **Mastercard •2587 was RETIRED by the CEO** — every "payment
failed" notice since about May is intentional, not an incident. Each
subscription is a migrate-to-new-card vs kill decision.

Code-verified and non-obvious:

- **ElevenLabs** ($6/mo Starter) is **not used by any pipeline.** Video TTS runs
  on fal.ai (`claudeflow/src/video/videotts.js`: primary `fal-ai/gemini-tts`
  th-TH, fallback `fal-ai/playai/tts/v3`). The name `elevenlabs` survives only
  as a stale cost-ledger label (`cost-ledger.js`, `cost:0.00006/char`) plus a
  balance pre-check; it does not call the ElevenLabs API. Cancelling it on
  06-18 was a pure save. **Open cleanup:** rename that ledger label
  `elevenlabs` → `fal_tts`, or the CFO dashboard keeps mislabelling fal TTS spend.
- **SendPulse** ($12/mo Chatbots, 500-sub) is the **TikTok DM auto-reply chatbot**
  (LuNar) — `claudeflow/src/integrations/sendpulseApi.js` + `src/webhook/tiktok.js`.
  Expired since ~May on the dead card, so **the TikTok DM channel is DOWN**. Not
  dead weight: renew-vs-kill is a CGO decision. Env: `SENDPULSE_CLIENT_ID` /
  `SENDPULSE_CLIENT_SECRET`.
- **Vercel** $20/mo (webapp host) — recovered 06-08, on a working card.
- **Notion** — the CEO's 2026-05-20 cancellation email did **not** cancel it.
  Notion requires an in-app downgrade (Settings → Billing → Change plan → Free →
  Downgrade). The ticket auto-closed while dunning kept firing.
