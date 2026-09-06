# Higgsfield account check — plan change to Plus $49/mo (2026-09-06)

Read-only verification. Nothing bought/upgraded/downgraded/generated. Account: `ilag-studio`'s workspace.

## Bottom line

**The plan change has NOT taken effect yet.** Account is still on **Ultra**, with a
scheduled downgrade to **Plus** on **September 7, 2026**. The old $250 pending
invoice is gone; it has been replaced by a new $49 pending invoice due the same
day. Seedance 2.5 Unlimited is still Active right now (Ultra plan), and it will
almost certainly stop being usable once the account actually drops to Plus,
because Plus does not carry Seedance 2.5 in its normal lineup at all (see §3).

## 1. Subscription page (`/me/settings/subscription`)

| Field | Value |
|---|---|
| Current plan | **Ultra Plan** |
| Status | "Your plan will be downgraded on **September 7, 2026**" (Cancel downgrade button present — not clicked) |
| Monthly credits | 6,000/mo |
| Credits left | 513 / 6,000 |
| Auto-refill | Disabled |

### Active unlimited models (verbatim)

| Model | Terms | Starts | Expires | Status |
|---|---|---|---|---|
| **Seedance 2.5 Unlimited** | 33-day, 720p quality | Aug 7, 2026 | **Sep 9, 2026** | **Active** |
| FLUX.2 Pro | 365 Unlimited, 1K quality | Auto-renewing | Auto-renewing | Active |
| GPT Image | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Seedream 4.5 | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Kling O1 Image | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Nano Banana | 365 Unlimited | Auto-renewing | Auto-renewing | Active |
| Seedream 5.0 Lite | 365 Unlimited | Auto-renewing | Auto-renewing | Active |

7 models currently unlimited. **KEY QUESTION ANSWERED: Seedance 2.5 Unlimited (33-day, 720p, Aug 7 → Sep 9) is still listed and Active.** It is a separate purchased grant, independent of the plan-level change, and its own expiry (Sep 9) is what will end it — not the Ultra→Plus downgrade.

⚠️ Caveat: this Unlimited grant sits on top of the *current* Ultra plan. Nobody has tested what happens to it the moment the account actually flips to Plus tomorrow (Sep 7) — flag this to the CEO before Sep 9 if the clip queue depends on it.

### Pending invoice

| Description | Due on | Status | Total |
|---|---|---|---|
| 1 × Higgsfield Plus - monthly (at $49.00/month) | September 7, 2026 | Upcoming | **$49** |

This is the **only** line in "Pending Invoices." The previously-reported "$250 due Sep 7" invoice is **gone** — superseded by this $49 line when the CEO changed the plan.

## 2. Billing → All invoices (`/me/settings/billing`)

Only 2 invoices exist, both already paid, both from before the plan change:

| Date | Status | Amount | Description | Invoice # |
|---|---|---|---|---|
| Aug 7, 2026 | Paid | $78.24 | Invoice payment | #VJRJFQXB-0004 |
| Aug 6, 2026 | Paid | $111.76 | Invoice payment | #VJRJFQXB-0003 |

**No $49 invoice has posted yet** (it's not due until Sep 7) and **no $250 invoice appears here either** — confirms it was replaced, not merely hidden.

## 3. Pricing page (`/pricing`, Monthly billing toggle)

Toggled off "Annual 30% OFF" to get true monthly prices:

| Plan | Price | Billing |
|---|---|---|
| Free | Free | — |
| Starter | $15/month | Billed monthly |
| **Plus** | **$49/month** | Billed monthly |
| Ultra | $129/month | Billed monthly |

### Plus column — Video section (Compare features table)

| Row | Free | Starter | Plus | Ultra |
|---|---|---|---|---|
| Concurrent jobs | 1 | 2 | **6** | 8 |
| Seedance 2.0 720p (~22 credits/5s) | ✗ | ✗ | **44 videos** | 133 videos |
| Seedance 2.0 1080p (~45 credits/5s) | ✗ | ✗ | **22 videos** | 66 videos |
| Seedance 2.0 4K (~110 credits/5s) | ✗ | ✗ | **9 videos** | 27 videos |
| Seedance 2.0 Fast 720p (~17 credits/5s) | ✗ | 11 videos | **57 videos** | 171 videos |

**Seedance 2.5 does not appear as a row in this table at all** — for Free, Starter, Plus, or Ultra. It only shows up as marketing-copy bullet text on the top-of-page Ultra/Team/Scale summary cards ("Access to all Seedance models" / "Access to Seedance 2.5"), never as a metered line item for Plus. **Answer: Plus does not get Seedance 2.5 through the standard plan allotment — only Seedance 2.0 variants are listed for Plus.** Seedance 2.5 access on this account currently comes exclusively from the separately-purchased Unlimited grant (§1), which is tied to Ultra, not Plus.

No "Unlimited window" is granted automatically by the Plus tier itself in this table — the "Get unlimited access to top models from $5" offer (seen on the subscription page) is a standalone paid add-on available regardless of plan tier, not something Plus includes for free.

## 4. Price-per-clip — composer (`/generate/@ilag-studio/ai-film-festival-3`, project "The Valder Collection No.7")

Video tab, 16:9, High quality, Sound On, Unlimited toggle left OFF for the credit readings. Slider set via ARIA `role="slider"` keyboard input, never clicked Generate.

### Seedance 2.5 — 720p

| Duration | Generate button (struck → actual) |
|---|---|
| 5s | ~~35~~ **33** |
| 10s | ~~70~~ **65** |
| 15s | ~~105~~ **98** |
| 20s | ~~140~~ **130** |

Unlimited toggle **is offered** for Seedance 2.5. With it switched ON at 20s, the button read: **"UNLIMITED · ~~140~~ 0"** — free, because the account's existing Seedance 2.5 Unlimited grant (§1) applied automatically, no purchase prompt.

### Seedance 2.0 — 720p

Max duration on this model is **15s** (slider range 4–15), so 20s is not selectable at all.

| Duration | Generate button (struck → actual) |
|---|---|
| 5s | ~~30~~ **23** |
| 10s | ~~60~~ **45** |
| 15s | ~~90~~ **68** |
| 20s | **not offered** — model caps at 15s |

Unlimited toggle **is offered** for Seedance 2.0 too, but behaves differently: switching it ON at 15s did **not** zero the price — instead it opened a **"Get Unlimited — SEEDANCE 2.0"** purchase modal offering **1-day Unlimited $65** or **3-day Unlimited $152 (was $195)**, "Pay once." This is despite the account already holding a "Seedance 2.0 · 365 Unlimited · Auto-renewing" grant on the subscription page — the two did not reconcile in the composer. Closed the modal with the X, did not select or pay for anything, toggle reverted to OFF.

## Screenshots

All under `docs/reports/higgsfield-plus-plan-20260906/`:
- `01-subscription-ultra-downgrade-sep7.jpg` — Ultra plan, downgrade scheduled Sep 7
- `02-unlimited-models-table-seedance25-active.jpg` — full 7-model unlimited table, Seedance 2.5 Active
- `03-pending-invoice-49-payment-methods.jpg` — $49 pending invoice + payment methods
- `04-all-invoices-no-250-no-49-yet.jpg` — All invoices page, only 2 paid Aug invoices
- `05-pricing-compare-plus-column-monthly.jpg` — Plus/Ultra monthly pricing + Seedance 2.0 rows
- `06-composer-seedance25-20s-unlimited-off-130.png` — Seedance 2.5, 20s, Unlimited OFF, 130 credits
- `07-composer-seedance25-20s-unlimited-on-zero.png` — Seedance 2.5, 20s, Unlimited ON, $0
- `08-composer-seedance20-unlimited-purchase-modal-152.png` — Seedance 2.0 Unlimited purchase modal (not purchased)

## Recommendation for the CEO

Before Sep 7 downgrade takes effect, confirm whether the Ultra→Plus switch will kill the Seedance 2.5 Unlimited grant early (it's currently valid through Sep 9) — Plus has no Seedance 2.5 line at all in the standard comparison table, so there's a real risk the Unlimited grant either gets orphaned or silently stops applying once the account is no longer Ultra. Worth asking Higgsfield support directly rather than assuming.
