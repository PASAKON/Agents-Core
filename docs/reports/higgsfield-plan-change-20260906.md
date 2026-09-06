# Higgsfield plan-change support probe — 2026-09-06

CEO-authorised (2026-09-06 20:55/20:58): ask support first, plan change on
hold. **No account-changing action was taken.** No downgrade/upgrade/cancel/
top-up/Generate control was clicked. Read-only throughout.

## Step 1 — Ask Support: result

**No in-app support channel exists on Higgsfield.** Confirmed by checking, in
order:

1. Subscription page → "Need help?" widget (bottom-left) → "Go to Help
   Center" button → **opens `https://discord.com/invite/higgsfield`** (a
   Discord community invite, not an in-app chat, not account-specific).
2. Account menu (avatar, top right) → only "Join Community" (same Discord),
   no Support/Contact item.
3. `higgsfield.ai/creator-hub/help-center` — searched the DOM for any
   Intercom/Zendesk/Drift/Crisp/Chatwoot widget script or container
   (`#intercom-container`, `.intercom-lightweight-app`, `[id*="intercom"]`,
   `[id*="zendesk"]`, `[id*="drift"]`, iframe selectors, etc.) — **0 matches**,
   confirming no chat-widget library is loaded on this page. Only a "Search"
   / "Ask AI" box (AI-answers-from-docs, not a human ticket/chat channel).
4. `higgsfield.ai/contact` ("Get in Touch with Higgsfield") lists exactly two
   channels:
   - **"Fast help on Discord"** — community server, requires joining.
   - **"Billing Support"** — "For questions about charges, credits,
     subscriptions, or refunds, contact: **support@higgsfield.ai**" (a plain
     email address, no in-app form/widget).

Per task instruction ("If there is NO in-app channel (only an email address),
do not email — record the address in the report and move on to Step 2"):

- **Support message: NOT sent.**
- **Channel found: email only — `support@higgsfield.ai`** (billing/credits/
  subscriptions/refunds). No live chat, no ticket form, no Intercom-style
  widget anywhere in the app.
- Discord was not joined (would require authenticating/creating a presence
  there — out of scope, and it's a community forum, not an account-specific
  support line anyway).
- No expected-reply-time indicator exists because no chat channel was found
  to check one on.

## Step 2 — Subscription page (read-only), before/after

No control was clicked that could change plan, credits, or billing. Values
were read twice (once at task start, once after the Step 1 probe) — identical
both times:

| Field | Value |
|---|---|
| Plan | Ultra Plan |
| Renewal date | September 7, 2026 |
| Monthly credits left | 523 / 6,000 |
| Auto-refill credits | 0 (disabled) |
| Active unlimited models | 7 currently unlimited |
| Seedance 2.5 Unlimited grant | 33-day, 720p quality · Starts Aug 7, 2026 · Expires Sep 9, 2026 · **Active** |
| Other active unlimited models | FLUX.2 Pro (365 Unlimited, 1K), GPT Image (365 Unlimited), Seedream 4.5 (365 Unlimited), Kling O1 Image (365 Unlimited), + 2 more, all auto-renewing/active |
| Free generations in total | 658 |
| Saved in total | +$5,473.6 |

These match the read-only probe (task-9819bf34) facts exactly — no drift.

**No confirmation dialog was ever shown** because no change-plan/downgrade
control was opened — per Step 2 instruction, the plan change stayed on hold
throughout. I did not confirm anything.

**"Credits are running low" banner**: appeared on the Subscription page and
again on the Contact page; closed with its (x) both times, as instructed.

## Screenshots

All under `docs/reports/higgsfield-plan-change-20260906/`:

- `docs/reports/higgsfield-plan-change-20260906/01-subscription-before.jpg` — Subscription page on arrival (banner still open, before close).
- `docs/reports/higgsfield-plan-change-20260906/02-contact-page-billing-support-email.jpg` — `/contact` page showing the two support channels (Discord + `support@higgsfield.ai`).
- `docs/reports/higgsfield-plan-change-20260906/03-subscription-after-topbanner.jpg` — Subscription page re-read after the support probe, top section (plan/credits unchanged).
- `docs/reports/higgsfield-plan-change-20260906/04-subscription-after-unlimited-table.jpg` — Subscription page scrolled to the Active unlimited models table, showing the Seedance 2.5 Unlimited grant.

## Anything odd

- The only "Help Center" entry point on the account UI actually routes to
  Discord, not to a knowledge base or ticket form — easy to mistake for an
  in-app support chat at a glance. Confirmed by following it.
- `support@higgsfield.ai` is scoped explicitly to "charges, credits,
  subscriptions, or refunds" — i.e. it is the right address for the exact
  question the CEO wants asked, just not a channel this task was authorised
  to use (email, not in-app chat).

## Recommendation for next step

Since no in-app channel exists, the CEO's two questions (will the Seedance
2.5 Unlimited grant + 523 credits survive the plan change; will the change
land at the Sep 7 renewal at $129 instead of $250) can only be asked by:
(a) emailing `support@higgsfield.ai` directly (needs explicit go-ahead — this
task's scope only covered in-app messaging), or (b) the CEO asking on Discord
himself, or (c) proceeding with the downgrade based on the FAQ text already
in hand ("change applies at the end of your current plan duration") and
verifying the outcome after Sep 7. This decision is the CEO's, not this
worker's — flagging it, not acting on it.
