# Higgsfield Ultra plan downgrade attempt — 2026-09-06

CEO-authorised (2026-09-06 20:55 "Downgrade เป็น 129$", 22:02 asked whether
done). Account `ilag-studio`. **Plan change was NOT completed — see Part 2.**
No credentials entered, no other controls touched.

## Part 1 — read-only findings

### 1a. Exact charge time

- **Upcoming charge**: Subscription page → Pending Invoices: "1 × Higgsfield
  Ultra - monthly (at $250.00 / month)", **Due on September 7, 2026**,
  status Upcoming, Total $250. **No time-of-day or timezone shown anywhere**
  in-app for this line.
- **Previous ("Aug") invoice**: `/me/settings/billing` → "All invoices" →
  invoice **#VJRJFQXB-0004**, opened its Stripe-hosted page
  (`invoice.stripe.com/i/acct_1R4agDCmk0pn4HuH/...`, read-only, clicked
  nothing that pays/edits). Paid **7 สิงหาคม 2569 = August 7, 2026**. Line
  items (via "ดูรายละเอียดของใบแจ้งหนี้" / view invoice details):
  - Billing period: 7 สิงหาคม – 7 กันยายน 2569 (Aug 7 – Sep 7, 2026)
  - Higgsfield Ultra - monthly × 1 — US$250.00
  - Coupon `PP_EXTRA_ULTRA_MONTHLY_6000_24` — discount −US$60.00
  - Prior-plan proration credit "Higgsfield Ultra - monthly" — −US$111.76
  - **Total charged: US$78.24** (฿2,689.47 at 1 USD = 34.3746 THB), paid via
    MasterCard •••2659.
  - **No clock time anywhere on the Stripe invoice/receipt page either** —
    date only, both in the summary card and the itemized detail panel.
  - Second invoice on file, #VJRJFQXB-0003, Aug 6, 2026, $111.76 (not opened
    in detail — same "date only" pattern visible in the list view).
  - **Conclusion: no exact charge time+timezone exists anywhere in the
    product for either the past or the upcoming charge — not guessing one.**

### 1b. Credit rollover rule

From `higgsfield.ai/pricing` FAQ ("How do credits work?", exact quote,
expanded and screenshotted):

> "Subscription credits do not roll over and expire at the end of each
> credit cycle."
>
> "Monthly credits are tied to your active subscription period. Unused
> subscription credits do not roll over to the next billing cycle and expire
> at the end of each month. New credits are refreshed automatically when
> your subscription renews."

**This means the 523 unused credits will be LOST at the Sep 7 renewal
regardless of whether the plan changes or stays the same** — they do not
carry into the new 6,000-credit cycle. Flagging this clearly for the CEO
since it changes the "should I spend the 523 before Sep 7" calculus.

Downgrade-timing FAQ (same page, "Can I change my subscription after
purchase?", matches prior report, re-confirmed word-for-word):

> "You can upgrade instantly at any time - the change takes effect
> immediately, and any credit difference is applied to your account. If you
> downgrade, the change will apply at the end of your current plan duration,
> and your existing plan will remain active until then."

## Part 2 — plan change: NOT completed

### What was tried

1. Subscription page (before-state) screenshot — Ultra Plan, renews Sep 7
   2026, 523/6,000 credits, Seedance 2.5 Unlimited Active (Aug 7 → Sep 9
   2026), "Credits are running low" banner closed with its (x).
2. `higgsfield.ai/pricing` → top "Explore all plans" featured card is the
   **wrong** Ultra (9,000-credit slider, $310–375/mo) — correctly **not**
   selected, per task's explicit exclusion.
3. Scrolled to the "Compare Features" grid (Free/Starter/Plus/**Ultra
   base**) — this is the correct tier. Confirmed **Monthly** billing toggle
   (Annual OFF) and read the card: **Ultra · $129/month · Billed monthly**
   (zoomed screenshot, exact text). Matches the CEO's target exactly.
4. Clicked the card's **"Upgrade Plan"** button (the only control Higgsfield
   shows on this cell — there is no separate "Downgrade" label on the Ultra
   column since the account is already on Ultra tier, only the $ amount
   differs).

### What happened — and why it was stopped

**No confirmation dialog of any kind appeared.** The button went straight
from "Upgrade Plan" → "Processing..." → a top-of-page error banner:

> "We couldn't process your payment. Please check your billing details or
> try another payment method."

This fails the task's checklist on every count that matters:
- No dialog text to verify "$129/month" / "applies at renewal, not now" —
  there was no dialog, only a direct charge attempt.
- The observed behavior (straight to a payment-processing step) is the
  opposite of the expected "schedule the change for Sep 7" flow — it looks
  like an **immediate-charge attempt**, not a scheduled downgrade.

Per task instruction, did NOT retry, did NOT try "another payment method",
did not click anything else on that path. This matches the skill's paid-
control rule (`higgsfield-unlimited-gen`, "Paid controls 2026-09-06"): one
click, then verify state — no blind retry on a control that touches money,
especially one that just returned a payment error.

### Verification: no charge, no change

Immediately after the error:
- Reloaded `/me/settings/subscription`: **Ultra Plan, renews September 7,
  2026, 523/6,000 credits** — identical to before-state.
- Reloaded `/me/settings/billing` → All invoices: still exactly **2**
  invoices (#0004 Aug 7 $78.24, #0003 Aug 6 $111.76) — no new invoice, no
  failed-charge record, no $129 or $250 line appeared.
- No card on file was charged (the error fired before any payment
  succeeded).

**Net effect: zero change to the account.** Plan, credits, renewal date, and
Unlimited grant are all exactly as they were before this task started.

## Recommendation

This is not a "wrong click" to retry — the site returned a genuine
payment-processing failure on the one control that maps to what the CEO
asked for, with no visible confirmation step at all. Two live possibilities,
neither safe for a browser operator to resolve alone:
1. The card on file (MasterCard ••2659) has an issue Stripe is rejecting.
2. This particular UI path (`/pricing` → Compare Features → "Upgrade Plan"
   on the same-tier cell) is not the intended in-app downgrade flow, and a
   different entry point (e.g. directly from the Subscription page, if one
   exists once expanded further) behaves differently.

Recommend the CEO do this one himself (per `browser-operator` skill:
click-blocked/payment-erroring paid controls hand off to the CEO after one
clean attempt), or confirm the card on file is valid first. **No further
attempts were made** and the account was left exactly as verified above.

## Screenshots

All under `docs/reports/higgsfield-downgrade-20260906/`:

- `01-subscription-before.jpg` — Subscription page, banner closed, before any action.
- `02-subscription-unlimited-table.jpg` — Unlimited models table, Seedance 2.5 Unlimited Active row.
- `03-pending-invoice-250.jpg` — Pending Invoices card, $250 due Sep 7 2026.
- `04-pricing-faq-rollover.jpg` — Pricing page FAQ, "How do credits work?" expanded, rollover text visible.
- `05-compare-grid-ultra-129-before-click.jpg` — Compare Features grid, Ultra $129/month/Billed monthly, before clicking Upgrade Plan.
- `06-after-failed-charge-attempt.jpg` — Error banner "We couldn't process your payment..." after the click.
- `07-subscription-after-verify-unchanged.jpg` — Subscription page reloaded, confirming plan/credits/renewal unchanged.

(Stripe invoice #VJRJFQXB-0004 detail was read via `get_page_text`, not
screenshotted separately — text quoted verbatim above.)
