# Fastwork seller (freelancer) signup — requirements map

Status: **PARTIAL — blocked before the live form could be safely walked.** See
"Why this stopped" below. Everything under "Confirmed from public docs" is
sourced from Fastwork's own public pages, not from filling anything in.

## Why this stopped

The org's shared Chrome (device `mac-chrome`, the only browser this task was
authorized to use) was already logged into a **real, active Fastwork buyer
account** (profile "PASAKON") when this task opened it. That is not something
this task did — it was the pre-existing state of the tab. `get_page_text` /
JS inspection of the homepage showed a genuine notification history: real
order IDs (e.g. `90431QHI`, `N54ZZCXJ`, `PDPYKWTV`...), real payments, real
Point balances, spanning January–August 2026. This is a live account with
money history, not a sandbox.

The task's homepage button ("เริ่มรับงาน" / "สมัครเป็นฟรีแลนซ์") was clicked
once to see where it led. It produced **no visible navigation or modal** — the
URL stayed on `https://fastwork.co/`. That is the safe outcome (nothing was
submitted), but it means the button's actual behavior for a **logged-in**
account could not be observed without either (a) risking that a further click
silently starts real seller-onboarding on a real account, or (b) logging that
account out, which the task's hard stops and the browser-operator skill both
treat as a "beyond your task" action on someone else's live session — not this
agent's call to make unasked.

Given the hard stops ("DO NOT create an account", "DO NOT log in", "DO NOT
guess anything"), the safest read is: **an already-authenticated session is
functionally equivalent to being logged in**, so continuing to click through
onboarding screens on it is out of scope the same way logging in would be.
Stopped there rather than pushing further.

**What this means practically:** the step-by-step screen-by-screen walkthrough
the task asked for (item 1 in the brief) could not be completed live. The
table below is built from Fastwork's own public marketing/help page instead,
which is lower-resolution than a live walkthrough but carries zero risk.

## Confirmed from public docs (fastwork.co/start-selling)

1. Homepage → click **"สมัครเป็นฟรีแลนซ์"** (also labeled "เริ่มรับงาน" in
   the nav) — this is the entry point; per the task's own prior research
   `/signup`, `/register`, `/sell` are all 404, so the button drives a
   client-side flow rather than a static page.
2. The page tells the applicant to **register with ID card and bank book
   ready**: *"ลงทะเบียนพร้อมเตรียมบัตรประชาชนและสมุดบัญชีสำหรับ[การตรวจสอบ]"*
   — i.e., both a Thai national ID card and a bank passbook/account are
   named as prep material for the registration/verification step, not
   explicitly deferred to first payout. (This is the strongest public signal
   on timing; it was not confirmed against the live form — see Open
   Questions.)
3. After registration, a second step needs **portfolio samples** ("ผลงาน")
   and job/service descriptions before the team reviews the application.
4. **Review time:** approval/rejection is communicated by email within **48
   hours** (one source page) / **2 business days, excluding weekends and
   public holidays** (Zendesk search snippet) — treat these as the same claim
   phrased two ways.
5. **Age requirement:** general minimum is **18**. Applicants aged **15–19**
   can register but must attach a guardian-consent document
   ("เอกสารรับรองจากผู้ปกครอง") during registration.
6. **Three freelancer tiers exist**, but they are a status ladder, not a
   signup choice: **Fastwork Freelancer** (default, immediate), **Fastwork
   Specialist** (vetted, tested, badge, bonuses), **Fastwork Professional**
   (top tier, invited to large corporate projects). None of these require a
   different signup path — they are earned/upgraded after the base account
   exists.
7. **No individual-vs-company (บุคคลธรรมดา / นิติบุคคล) distinction appears
   anywhere in the public marketing copy.** Fastwork does separately sell a
   "จดทะเบียนบริษัท" (company registration) *service* as a gig category
   freelancers can buy — that is an unrelated marketplace listing, not a
   seller account type.
8. Fastwork's own help center (Zendesk, `fastwork4276.zendesk.com`) almost
   certainly has the field-by-field article, titled **"วิธีการลงทะเบียนเป็น
   ฟรีแลนซ์"** and **"สมัครอย่างไร"**, but the Zendesk host returned **HTTP 403
   to every fetch attempt** (WebFetch and curl with a browser user-agent both
   blocked; Wayback Machine lookup hit a rate limit). Their content could not
   be read this session — only search-engine snippets of them were available,
   which is where items 4–5 above come from.

## Field table

| field | Thai label (best known) | required? | who can supply it | notes |
|---|---|---|---|---|
| National ID card | บัตรประชาชน | Required (per start-selling page) | **CEO only** | Photo/scan of a real ID — hard stop for an agent regardless |
| Bank account / passbook | สมุดบัญชี | Required (per start-selling page); exact trigger point (signup vs. first payout) unconfirmed | **CEO only** | Site copy implies it's requested alongside the ID at registration, not deferred — unverified against live form |
| Portfolio samples | ผลงาน | Required, second step | CEO (or agent if given already-approved, non-sensitive samples) | Needed for the 48h team review |
| Guardian consent doc | เอกสารรับรองจากผู้ปกครอง | Required only for age 15–19 | CEO only | Not applicable if CEO is an adult |
| Email | — | Unconfirmed | CEO only if real address needed | Blocked — could not reach the live field list |
| Password | — | Unconfirmed | N/A (never enter) | Hard stop regardless |
| Phone / OTP | — | Unconfirmed whether required at signup | **CEO only** | Task hard-stops any OTP trigger; unconfirmed if avoidable |
| Google/Facebook login | — | Confirmed **offered** (OAuth callback hosts exist per task brief: `auth2.fastwork.co/auth/google/callback`, `/auth/facebook/callback`) | CEO only | Whether it still demands a phone/OTP afterward is unconfirmed |
| Individual vs. company toggle | บุคคลธรรมดา / นิติบุคคล | **Not found in public docs at all** | — | Open question — may not exist as a seller-account distinction |
| VAT registration toggle | — | Unconfirmed | — | Open question |
| Date of birth | — | Implied by the 15–19 guardian-consent rule (so DOB is collected somewhere) | CEO only | Exact field/step unconfirmed |
| Listing package tiers / price floor / min. images | — | Unconfirmed | — | Blocked — needs live form or a listing-specific help article |

## What only the CEO can do

- Supply and upload a real Thai ID card (บัตรประชาชน).
- Supply a real bank account / passbook, matched to their verified identity.
- Receive and enter any phone OTP, if the flow requires one (unconfirmed but
  must be assumed possible for a Thai marketplace signup).
- Enter their own real email, password, name, address, date of birth.
- Decide whether to use the already-logged-in Fastwork account on the shared
  Chrome for this, or a fresh one — see Open Questions.
- Click the actual submit/สมัคร button — explicitly out of scope for this
  agent regardless of account state.

## Open questions for the CEO

1. **The shared Mac Chrome is already logged into a live Fastwork account
   ("PASAKON") with real order/payment history.** Is that your personal
   buyer account? If you want the seller-signup flow actually walked
   (screen-by-screen, to finish items 1–2, 6–9 of the original brief), the
   safest path is either you drive it yourself, or you explicitly authorize
   using that logged-in account to view (not submit) the seller-onboarding
   screens, or you give a throwaway/incognito path for an agent to look at
   the anonymous version of the flow.
2. Is the ID-card-and-bank-book requirement demanded **at initial
   registration**, or only surfaced as "have these ready for later" copy?
   The public page's wording suggests early, but this needs a live-form
   confirmation to be sure.
3. Does Fastwork have an individual/company (บุคคลธรรมดา / นิติบุคคล) account
   distinction at all? Nothing in public docs mentions one — worth confirming
   directly with Fastwork support if it matters for your VAT/invoicing setup.
4. Do you want another attempt at reading Fastwork's Zendesk help center
   (403'd on every automated fetch this session — may need a human browser
   session, or a different IP/UA, or simply isn't crawlable)?

## Method note

Per the task's own instruction to prefer public docs over the live form: tried
`doc.fastwork.co`-adjacent search results and the Zendesk help center first
(WebSearch + WebFetch + curl with browser UA), all blocked by Zendesk's 403.
The `fastwork.co/start-selling` marketing page was fetchable and is the source
for everything in "Confirmed from public docs" above. Only after exhausting
docs did this task open the live homepage — where it hit the logged-in-account
finding described above and stopped.

Browser budget used: ~10 actions, 0 screenshots (well under the 30-step /
4-screenshot budget). Stopped early by choice, not by budget exhaustion.
