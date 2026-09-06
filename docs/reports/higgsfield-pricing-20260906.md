# Higgsfield pricing + billing — 2026-09-06 (read-only capture)

Task: task-9819bf34. Goal: give the CEO exact numbers to decide whether to drop
from Ultra to a cheaper plan at the next billing date. **No clicks that buy,
upgrade, downgrade, cancel, or top up were made.** Toggled Monthly/Annual
display switch only (explicitly allowed — a display toggle, not a purchase).

## TL;DR for the CEO

- **Renewal is TOMORROW: September 7, 2026**, and the charge is **$250.00/month**
  (see invoice, screenshot 08). That does not match ANY price currently shown
  on the public pricing page for Ultra (see contradictions below) — you are
  very likely on an older/legacy rate, not today's listed price.
- **Seedance 2.5 Unlimited is not a standing Ultra perk on the current pricing
  page at all.** It's a separate, time-boxed grant on your account:
  **"Seedance 2.5 Unlimited, 33-day, 720p quality" — Aug 7, 2026 → expires
  Sep 9, 2026** (screenshot 06). It expires in **3 days** regardless of
  whether you renew Ultra or downgrade.
- Today's Ultra plan (public page) does **not** list Seedance 2.5 under
  Unlimited at all — Seedance 2.5/2.0 are listed under "ACCESS TO SEEDANCE
  MODELS" as **"Full access"** (credit-metered, not free) on every tier that
  has it. See "Contradicts the brief" below.
- Downgrade FAQ (exact quote): *"If you downgrade, the change will apply at
  the end of your current plan duration, and your existing plan will remain
  active until then."*

## 1. Plan table — higgsfield.ai/pricing (logged in as ilag-studio)

Window confirmed at 1366×754 (>=1280 required by brief; `window.innerWidth`
read back). "Credits are running low! Over 90% already used" banner appeared
and was closed with its own (x) — screenshot 01 (before close), banner gone in
screenshot 02 onward.

The page has **two separate plan groupings** — this is easy to misread and
caused internal confusion while transcribing it:

### A. Featured/highlighted cards ("Explore all plans" — top of page)

| Plan | Credits/mo | Price — Annual billing | Price — Monthly billing |
|---|---|---|---|
| **Ultra** (individual, slider 6,000–9,000 credits, shown at 9,000) | 9,000 | $387 → **$270**/mo, billed annually (30% off) | $375 → **$310**/mo first month, "renews at $375" (17% off label) |
| **Team** (2–9 seats, priced per seat) | 2,000 total/mo (1,000/seat) | $79 → **$65**/seat/mo, annual (18% off) | $79 → **$69**/seat/mo, "renews at $79" (13% off) |
| **Scale** (5–15 seats, priced per seat) | 12,500 total/mo (2,500/seat) | $245 → **$150**/seat/mo, annual (30% off) | $245 → **$169**/seat/mo (22% off) |

Screenshots: 02 (annual), 07 (monthly).

### B. "Compare features" full grid — Free / Starter / Plus / Ultra (individual tiers)

This is a **different, lower Ultra tier** (base, 6,000 credits/mo — matches
what the account actually has) from the 9,000-credit card above.

| Plan | Price — Annual | Price — Monthly |
|---|---|---|
| Free | Free (limited use) | Free |
| Starter | $15/month, billed annually | $15/month, billed monthly |
| Plus | $49/month, billed annually | $49/month, billed monthly |
| **Ultra (base)** | **$99/month**, billed annually | **$129/month**, billed monthly |

⚠️ **Contradicts the brief / worth a double-check before deciding**: the
account's actual invoice is **$250.00/month** for "Higgsfield Ultra - monthly"
(screenshot 08). That is nowhere close to today's listed $129/mo (monthly) or
$99/mo (annual) for base Ultra, nor the $310–375/mo for the 9,000-credit
upsized Ultra. Most likely explanation: the account is grandfathered on an
older Ultra price point from whenever it was originally purchased, and
Higgsfield's current live pricing has dropped since. **Worth confirming with
Higgsfield support before assuming a "downgrade" is the only way to cut the
bill — switching this same Ultra tier from monthly to annual billing, per the
page's own numbers, would drop it from ~$129/mo to ~$99/mo, a separate lever
from changing tiers.** Not clicked/tested (would be a purchase action).

The brief's "credit discount" row (0 / 200 / 1000 / 3000 for
Free/Starter/Plus/Ultra) appears in the DOM as a distinct "Credit discount"
line in the feature grid, separate from monthly credit allocation — did not
independently verify what it means; flagging rather than guessing.

## 2. THE UNLIMITED MATRIX — per plan, Seedance 2.5 highlighted

**This is the single biggest finding: on the CURRENT public pricing page,
Seedance 2.5 is not offered as "Unlimited" on ANY plan.** It is offered as
**"Full access"** (i.e., included in the model line-up, charged per credit
like normal) on Ultra/Team/Scale. Below Ultra/Team/Scale, Free/Starter/Plus
individual tiers don't show a Seedance 2.5 access line at all in the
"Compare features" video table (that table only lists Seedance 2.0/1.5 and
other models at metered credit rates — no dedicated Seedance 2.5 row).

| Plan | Seedance 2.5 | Seedance 2.0 | What IS shown as "Unlimited" instead |
|---|---|---|---|
| **Ultra** | **Full access** (1080p) — credit-metered, NOT unlimited | Full access (4K) — credit-metered | Nano Banana Pro (2K), Nano Banana 2 (2K), Kling 3.0 — all **"7-day unlimited"** (time-limited promo, not permanent). Expanding "7 unlimited & free generation models" also shows: Soul V2 & Cinema (10,000 free gens), Seedream 5.0 Lite / Flux.2 Pro (1K) / Seedream 4.5 (4K) / Nano Banana / Kling O1 Image / GPT Image — all **"365 unlimited"** |
| **Team** | Full access (per "Access to Seedance 2.5" checkmark) | — | Nano Banana Pro / Seedream 5.0 Pro / Kling 3.0 — all "**No unlimited**" on Team |
| **Scale** | Full access | — | Nano Banana Pro / Seedream 5.0 Pro / Kling 3.0 — all "7-day unlimited" |
| Free/Starter/Plus | Not listed as a distinct access line | Metered, per the big credit-rate table | none |

Screenshot 03 shows the "ACCESS TO SEEDANCE MODELS — Full line-up included"
card with "Seedance 2.5 · 1080p · Full access" and "Seedance 2.0 · 4K · Full
access" sitting in a **different card, below and separate from**, the
"UNLIMITED & FREE GENS" card. Screenshot 04 (the "Unlimited & Free
generations for Ultra Annual plan" expand modal) lists all 7
unlimited/free-gen models and **Seedance does not appear in it.**

**"What Plus and Max cap Seedance at"** (as asked in the brief): there is no
plan currently named "Max" on this page — the individual tiers are Free /
Starter / Plus / Ultra. **Plus** does not carry a Seedance 2.5 access line at
all on the current page (it's an Ultra/Team/Scale-only feature). No cap
numbers (clip length / resolution) are shown per-plan for Seedance 2.5 beyond
"1080p" on Ultra's "Full access" badge — the page does not break out a
20s/720p Unlimited cap anywhere for any plan.

**This directly contradicts the task brief's premise** that some plan shows
Seedance 2.5 at 20s/720p as Unlimited. See section 3 for where that benefit
actually lives on this account (it's not on the pricing page at all).

## 3. Account billing/subscription page — higgsfield.ai/me/settings/subscription

Reached via avatar (top-right) → **Manage Account** → **Subscription** in the
left sidebar (Personal profile / Gifts / **Subscription** / Usage / Promocode).

- **Current plan: Ultra Plan.**
- **Next renewal: September 7, 2026** (i.e., tomorrow from today, 2026-09-06).
- **Monthly credit allocation: 6,000/month** (the base Ultra tier, not the
  9,000-credit upsized one from the featured card).
- **Credit balance: 523 / 6,000 credits left** (≈9% remaining — matches the
  "Credits are running low! Over 90% already used" banner).
- **Billing period: MONTHLY** (confirmed from the pending invoice, not annual)
  — "1 × Higgsfield Ultra - monthly (at $250.00 / month)", due September 7,
  2026, status **Upcoming**, total **$250**. Screenshot 08.
- Included checkmarks on this plan (no dollar figures, just features):
  6,000 credits/month; Parallel generations up to 8 Videos/8 Images; Access to
  Supercomputer; **Access to all Seedance models**; Access to all models &
  features; Early access to advanced AI features; Access to unlimited
  marketplace; Lowest cost per credit. **No "Unlimited" line for Seedance
  appears in this checklist** — it's a plain access checkmark, matching the
  pricing page's "Full access" (credit-metered) designation. Screenshot 05.

### "Unlimited models" table (Subscription page, scrolled down)

This IS where the account's real Unlimited benefits live — a separate table
from the plan checklist above:

| Model | Terms | Starts | Expires | Status |
|---|---|---|---|---|
| **Seedance 2.5 Unlimited** | **33-day, 720p quality** | **Aug 7, 2026** | **Sep 9, 2026** | **Active** |
| FLUX.2 Pro | 365 Unlimited, 1K quality | Auto-renewing | Auto-renewing | Active |
| GPT Image | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Seedream 4.5 | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Kling O1 Image | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Nano Banana | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Seedream 5.0 Lite | 365 Unlimited | Auto-renewing | Auto-renewing | Active |

Summary stats shown above the table: **7 models currently unlimited**, **658**
free generations in total, **+$5,473.60 saved in total**. Screenshot 06.

**Key point for the downgrade decision: Seedance 2.5 Unlimited is its own
33-day grant, not tied to the plan's renewal cycle, and it expires
Sep 9, 2026 — 3 days from today — regardless of what happens to the Ultra
subscription on Sep 7.** No clip-length cap (20s or otherwise) is stated on
this row; only "33-day, 720p quality" is shown as the terms. Did not find
anywhere on the account pages that states a clip-duration cap for this
benefit — flagging as not found rather than guessing.

An "Get unlimited access to top models from $5 / Seedance 2.0, Nano Banana
Pro, Kling 3.0 and more / **Get Unlimited**" upsell banner sits directly above
this table — **not clicked**, this is a paid upsell control per the
`higgsfield-unlimited-gen` skill's standing warning about exactly this kind of
button.

## 4. Downgrade FAQ — exact quotes

From the pricing page FAQ accordion (clicked to expand, read verbatim):

> **Can I change my subscription after purchase?**
> "Yes. You can upgrade instantly at any time - the change takes effect
> immediately, and any credit difference is applied to your account. If you
> downgrade, the change will apply at the end of your current plan duration,
> and your existing plan will remain active until then."

> **How does Unlimited work?** (relevant context, not itself about
> downgrading, but explains what "Unlimited" means on this platform)
> "Unlimited lets you generate content without spending credits on supported
> models, resolutions, or quality tiers included in your plan... Dynamic Speed
> Adjustment: Generation speed and concurrency may temporarily vary during
> periods of exceptionally high system load or peak traffic hours... Credit
> Mode: You can turn off Unlimited at any time to generate faster using
> credits... Fair Use: This feature is designed for personal, human use
> only..."

**No FAQ item specifically addresses what happens to an in-progress Unlimited
window (like the Seedance 2.5 grant above) on downgrade** — the general
downgrade answer ("applies at the end of your current plan duration") is the
only stated rule found. Given the Seedance 2.5 window already expires
Sep 9 (2 days after the Sep 7 renewal), this is close to moot either way.

## Screenshots (docs/reports/higgsfield-pricing-20260906/)

1. `01-pricing-top-annual-banner.jpg` — hero + Explore all plans, Annual
   toggle on, "Credits are running low" banner visible (before close)
2. `02-pricing-ultra-team-scale-annual.jpg` — Ultra/Team/Scale cards, Annual
   prices ($387→$270, $79→$65, $245→$150), banner closed
3. `03-access-to-seedance-models-fullaccess.jpg` — "ACCESS TO SEEDANCE
   MODELS" card (Seedance 2.5 1080p Full access, Seedance 2.0 4K Full
   access) alongside Team/Scale "UNLIMITED MODELS" panels
4. `04-unlimited-free-gens-modal-ultra-annual.jpg` — "Unlimited & Free
   generations for Ultra Annual plan" expand modal, full 7-model list (no
   Seedance)
5. `05-account-subscription-ultra-plan-top.jpg` — account Subscription page:
   Ultra Plan, renews Sep 7 2026, 6,000 credits/mo, 523 left
6. `06-account-unlimited-models-table-seedance25.jpg` — account's own
   "Unlimited models" table: Seedance 2.5 Unlimited, 33-day/720p,
   Aug 7 → Sep 9 2026, Active
7. `07-pricing-ultra-team-scale-monthly.jpg` — same top cards with Monthly
   toggle ($375→$310, $79→$69, $245→$169)
8. `08-account-pending-invoice-250-monthly.jpg` — Pending Invoices: "1 ×
   Higgsfield Ultra - monthly (at $250.00 / month)", due Sep 7 2026,
   Upcoming, $250

## What contradicts the brief (recap)

- Brief assumed some plan shows "Seedance 2.5 at 20s/720p Unlimited" as a
  standing plan feature. **Not true on the current public pricing page** —
  Seedance is "Full access" (credit-metered) on every tier that has it at
  all. The Unlimited Seedance 2.5 the account actually has is a **separate,
  time-boxed 33-day grant** (Aug 7 → Sep 9, 2026) visible only on the
  account's own Subscription page, not derivable from the pricing page.
- Brief asked what "Plus and Max" cap Seedance at. There is no "Max" plan;
  current individual tiers are Free/Starter/Plus/Ultra, and Plus has no
  Seedance 2.5 access line at all.
- The account's actual monthly charge ($250) does not match any price
  currently listed on the pricing page for Ultra at any commitment/credit
  tier — likely a legacy/grandfathered rate, flagged for the CEO to confirm
  rather than assumed.

## Browser Actions

- route: step 5 (text/DOM-first) — task needs exact structured numbers plus
  required screenshots; used `javascript_tool`/`get_page_text` for data,
  screenshots only for the visual proof the brief explicitly asked for.
- steps_used: ~34 tool calls (over the ~20 suggested budget — the brief's own
  ask, an exhaustive plan+Unlimited matrix plus account billing, needed more
  reads than a simple lookup; no paid/state-changing action taken at any
  point)
- screenshots_taken: 8 (window 1366×754 effective viewport; ~700-750 tokens
  each per the browser-operator cost table)
- pages_visited: `https://higgsfield.ai/pricing` (Annual and Monthly toggle
  states), `https://higgsfield.ai/me/settings/subscription`
- Tab 53473609 claimed under task-9819bf34 in `scripts/browser/tab_registry.py`
  for the duration; task-cf095f15's S2N tab was never touched (registry
  showed it unclaimed/orphaned at start of this session — left alone
  regardless, per brief).

## Replay Script

- path: none
- covers: n/a
- brittle: n/a — this is a one-off manual data pull for a point-in-time
  decision; Higgsfield's pricing page changes frequently (see the
  monthly/annual discount-percentage labels shifting between toggles) and a
  scripted scrape would need re-verification each run anyway. If the CEO
  wants this re-checked at a future decision point, re-run the same manual
  steps (pricing page → Explore all plans + Compare features + FAQ, account
  → Subscription) rather than trust a cached script against a page that
  reprices this often.

## Issues / Blockers

- None. Zero paid/state-changing clicks made: only navigation, the pricing
  page's own display-only Monthly/Annual toggle, closing the low-credit
  banner and the unlimited-list expand modal (both dismiss-only), and
  opening the avatar/account menus.
- The "Get unlimited access" and "Get Unlimited" upsell buttons were seen
  and explicitly NOT clicked (they are paid purchase flows).
