---
question: Does the CEO's Google AI subscription include Google Cloud credits, how much, and can they pay for Cloud TTS or Gemini image generation without us opening billing?
date: 2026-10-14
author: CTO (Contabo) session dd03bac1, for SomPong's CEO order 14 Oct (tool-value report, Google Cloud credit check)
sources: [https://blog.google/innovation-and-ai/technology/developers-tools/gdp-premium-ai-pro-ultra/, https://medium.com/google-cloud/from-prototype-to-production-how-google-ai-subscription-bridges-the-last-mile-for-ai-developers-dd80bb149a3e, https://discuss.google.dev/t/end-of-google-cloud-developer-program-premium/324980, https://techcabal.com/2026/06/05/google-ai-subscription-plans-explained/, https://agentdeals.dev/google-developer-program-2026]
measured_by_us: no. One web search (search-result summaries; no page fetched, console not opened). Our own billing facts come from the CFO's 2026-08-04 check in wiki projects/finance.md.
refresh_after: 2026-11-13
confidence: high that Pro/Ultra include monthly Cloud credits through Google Developer Program premium (Google's own blog). Low on the amount for the CEO's plan ($100 per Google's blog, $40 per two third-party pages; tier names changed at I/O 2026).
labels: [M] Google official page · [3] third party · [O] our own record
---

# Google AI subscription → monthly Google Cloud credits

## Answer
- **Yes, there are credits.** Since 27 Jan 2026, Google AI Pro and Ultra subscribers get Google Developer Program premium at no extra cost, and it includes monthly Google Cloud credits. [M]
- **Amount.**
  - Pro: $10/month. [M]
  - Ultra: $100/month on Google's blog [M], $40/month on two third-party pages [3].
  - The CEO pays $100/month. Whether that buys a tier with $40 or $100 of credits is **not verified**.
  - The standalone Developer Program premium plan ended on 31 Mar 2026. [3]
- **They do nothing until activated.** The benefit has to be activated once by adding the credits to a Cloud billing account. With no billing account, one has to be created. [3]
- **Our billing accounts.** Both of the CEO's Cloud billing accounts were **Closed** on 2026-08-04 (01F933-…, card expired; 018426-…). [O] So the monthly credits have most likely never been activated, and every month that passes is lost.
- **Can they pay for Cloud TTS or Gemini image models?** Not answered here. It depends on the scope the credit carries, which shows only on console.cloud.google.com/billing → Credits after activation.

## What it takes (not done by us)
Activating needs an open billing account with a payment method: that is the CEO's call. Our order said read-only, no billing account. After activation, set the ฿300 budget alert at once, as the 2026-08-04 note says.

## Open
- The real balance and expiry. These need the CEO's Google console (whichever of his accounts holds the subscription).
- Whether the subscription is on the same Google account as the closed billing accounts.
