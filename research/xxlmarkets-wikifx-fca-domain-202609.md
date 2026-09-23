---
title: XXLMARKETS — WikiFX profile, live domain status, FCA register attempt (for BL EP57 script)
date: 2026-09-23
refresh_after: 2026-10-23
source: WikiFX TH/EN dealer pages (WebFetch), dig/curl/whois + Claude-in-Chrome live visit (this Mac), register.fca.org.uk + fca.org.uk (Claude-in-Chrome, both blocked/inconclusive)
---

# XXLMARKETS — verification pass for BL EP57

The CEO's source card (`prototypes/bl57-realfootage/third-party/wikifx-xxlmarkets-review.jpg`)
claims: score 1.99/10, "ยังไม่มีการกำกับดูแล", UK, 2-5 years,
"ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์", website inaccessible. Every number re-checked live
2026-09-23.

## WikiFX profile — CONFIRMED, matches the card exactly

Source: https://www.wikifx.com/th/dealer/3697715948.html (WikiFX Thailand),
cross-checked against https://www.wikifx.com/en/dealer/3697715948.html
(WikiFX English), both fetched 2026-09-23 via WebFetch.

- Trust score: **1.99/10** (TH page, matches the card). EN page also read
  1.99/10 at fetch time; a WebSearch snippet elsewhere quoted 1.45 — treat
  that as a stale/cached search-index snapshot, not the live page, and use
  the live TH page's 1.99 in the script.
- Regulatory status: "ยังไม่มีการกำกับดูแล" (TH) / "Not Regulated" (EN) —
  matches the card.
- Country: สหราชอาณาจักร / United Kingdom — matches the card.
- Years in operation: 2-5 years — matches the card. EN page separately
  states "Founded 2021".
- License: "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์" (TH) / "No forex trading license
  found. Please be aware of the risks." (EN) — matches the card.
- Warning banner (TH): "ใบอนุญาตในการกำกับดูแลกำลังถูกตั้งข้อสงสัย |
  กลุ่มธุรกิจที่ต้องสงสัย | ระวังความเสี่ยงอันตรายที่อาจจะซ่อนอยู่"
- Website status (WikiFX's own note, TH): "https://xxlmarkets.com/
  ไม่สามารถเข้าถึงได้อย่างปกติในขณะนี้" — matches the card's
  "เว็บเข้าไม่ได้" claim, see live re-check below (which found it worse than
  "inaccessible").
- Rating breakdown (EN): Regulation 2.69/10, Tech 4.54/10, Reputation
  3.51/10, Business 6.31/10, Risk Control 2.79/10.
- Contact: phone +44 7441427348, email support@xxlmarkets.com.
- WikiFX's own EN search summary states regulatory status is unverified
  "even the local FCA shows no results about it" — WikiFX's own claim, not
  independently confirmed by us today (see FCA section below).

## xxlmarkets.com — the card's claim is TRUE and now STRONGER than "inaccessible"

Checked live 2026-09-23T14:36 UTC (2026-09-23 21:36 +07):

1. `dig xxlmarkets.com` (default resolver) — empty answer.
2. `dig @8.8.8.8 xxlmarkets.com` — empty answer.
3. `dig xxlmarkets.com` full query — **status: NXDOMAIN** (domain does not
   exist in the DNS root, not merely unreachable).
4. `whois -h whois.verisign-grs.com xxlmarkets.com` — **"No match for
   domain "XXLMARKETS.COM""** — the .com registry itself has no record of
   this domain being registered at all right now.
5. `curl -I https://xxlmarkets.com/` and `curl -I http://xxlmarkets.com/` —
   both fail with "Could not resolve host".
6. Claude-in-Chrome live navigation to `https://xxlmarkets.com/` — Chrome
   renders its own DNS-failure error page (a screenshot attempt on that page
   errors with "Frame with ID 0 is showing error page", confirming the tab
   never got real content).

**Conclusion: as of 2026-09-23, xxlmarkets.com is not merely down or timing
out — the domain itself is not currently registered (NXDOMAIN + "no match"
at the registry).** The card's "เว็บเข้าไม่ได้" is confirmed and can be
written as flatly true; the script should say it is worse than "โหลดไม่ขึ้น"
— the domain itself doesn't exist in DNS right now.

## FCA register — direct lookup attempted, INCONCLUSIVE (not independently verified today)

Two attempts via Claude-in-Chrome, both failed to return usable results:

1. `https://register.fca.org.uk/s/search?q=XXLMARKETS` — page title updates
   to "XXLMARKETS - Search Firms - FCA Register" (so the query registered
   client-side) but the results panel spins forever (tried 3 times across
   ~2 minutes total wait, including after accepting/denying the cookie
   banner on a fresh load of the site root first). WebFetch on the same URL
   independently returned a "CSS Error" state. This matches a known-working
   URL pattern from EP55's research (`research/regulator-license-registers-2026-09.md`
   confirms `register.fca.org.uk/s/` is the FCA's own real Register site,
   with a live search box) — today's failure looks like a client-side
   rendering/API issue on this specific query, not a wrong URL.
2. `https://www.fca.org.uk/scamsmart/warning-list` (and the redirect target
   `/consumers/warning-list-unauthorised-firms`) — returned a bot-detection
   "กำลังทำการตรวจสอบความปลอดภัย" (security check) interstitial. Per hard
   rule, bot-detection/CAPTCHA challenges are never bypassed — stopped here.

**We could not independently confirm or deny an FCA listing for XXLMARKETS
today.** The only source for "no FCA result" is WikiFX's own EN page text
("even the local FCA shows no results about it") — cited in the script as
WikiFX's claim (status: attributed), not as something this channel verified
directly, per the compliance rule that every claim states its source.

## What this means for the EP57 script

Nothing on the CEO's card turned out to be false. If anything the live
re-check makes the website claim stronger (domain gone from DNS entirely,
not just "เข้าไม่ได้"). The FCA claim stays attributed to WikiFX, flagged
honestly as not independently re-verified today (register.fca.org.uk did
not render, and the ScamSmart warning-list page is behind bot-detection we
will not bypass).
