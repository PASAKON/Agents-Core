---
question: Who is Seaaii, how does it sell, what does it cost, and can Chatudo beat it in the Thai chat-commerce AI market?
date: 2026-10-04
sources: [https://seaaii.com/, https://seaaii.com/seaaii/about, https://seaaii.com/seaaii/terms, https://www.facebook.com/seasalepage, https://www.facebook.com/ads/library/?country=TH&q=Seaaii]
measured_by_us: yes   # pages and Ad Library captured by our own headless Chromium on 2026-10-04 22:5x TH; screenshots in /root/chatudo-outreach/seaaii-capture/ (outside the repo)
refresh_after: 2026-10-18   # prices and ads change weekly
confidence: medium        # public layer only; the product, the Facebook feed and the comments are NOT yet seen (login requests rq-6c31c0a5, rq-601563ce)
---

# Seaaii — competitor teardown, part 1 (public layer)
Session CMO #3c1fc6bc. CEO asked 4 Oct 2026 22:38 TH, after seeing the Seaaii page on his phone. DO NOT PUSH: Agents-Core is public.

## 1. What it is (official = their own pages)
| Fact | Value | Level |
|---|---|---|
| Product line | "AI Chat & Order Management Platform": AI answers chats, recommends products, summarises orders, takes orders, checks transfer slips, sends tracking numbers, calls couriers | official |
| Channels | Facebook, LINE OA, Instagram in one inbox (no TikTok/Shopee/Lazada shown) | official |
| Company | SUPER FIRM COMPANY LIMITED, Don Mueang, Bangkok; phone 095-598-9191; LINE @seaaii | official |
| Brand history | `seasalepage.com` redirects (302) to `seaaii.com`; the Facebook page URL is still `/seasalepage`; Google snippet: "Sale Page สำเร็จรูป ใน 5 นาที". So it was a sale-page builder first and pivoted to AI chat | measured (redirect) + inference (pivot) |
| Team, founders, year started, customer count | not shown anywhere | official silence |

## 2. Price (official, read from the page text, not a summary)
| Plan | Term | Tokens | Per month | Upfront | Users |
|---|---|---|---|---|---|
| Standard | 3 months | 25M | ฿9,667 | ฿29,000 | 5 |
| Advanced | 6 months | 35M | ฿8,167 | ฿49,000 | 7 |
| Pro (marked "แนะนำ") | 12 months | 50M | ฿6,543 | ฿79,000 | 10, + CRM |
| Enterprise | custom | | | | |
- Smallest buy-in is ฿29,000 for 3 months. No monthly plan shown. Free trial exists as a button (`/auth/signup?trial=1`); length and limits not stated.
- Terms: paid fees "may not be refundable" case by case; "ผลลัพธ์จาก AI อาจมีข้อผิดพลาด" (AI output may be wrong); token consumption not defined; no PDPA wording, a separate data-deletion page exists.
- Our prior market note: Thai SMB chatbots run ฿500–3,000/mo (`research/2026-09-28-chatbot-saas-market-by-country.md`). Seaaii at ฿6,543–9,667/mo sits 2–4× above that band.

## 3. How they sell on Facebook (Ad Library, no login, measured)
- ~22 ads shown, those we could read started 24–30 Sep 2026. **Correction (4 Oct, own re-read):** for ordinary commercial ads outside the EU the Ad Library lists only ads that are running now, so ads switched off earlier are invisible. The right reading is "the oldest ad still running started 24 Sep", not "the paid push is 10 days old". How long and how much they have paid is unknown; the 29k followers cannot be explained or excluded by this. The old brand name returns 0 ads (also running-now only).
- Format: 13-second videos/images, dark neon + robot mascot. CTA button "Send Message" (Click-to-Messenger).
- Every ad carries the same line: "สำหรับธุรกิจ • แพ็กเกจเริ่มต้นไม่เกิน 300 บาท/วัน • กรุณาตอบข้อมูลคัดกรอง" = a daily-price frame (฿300×30 = ฿9,000 ≈ their ฿9,667/mo) plus screening questions before a human answers.
- Hooks seen (Thai): "ธุรกิจโต แต่แชทพัง = เงินหาย" · "ไม่ต้องส่งต่อแอดมิน เพราะ AI ปิดจบได้" · "ใครตอบก่อน คนนั้นได้ยอด" · "ตอบแชทอย่างเดียว ไม่พอ ต้องปิดจบงานขายได้" · "พูดเหมือนคน ขายเก่งเหมือนทีมมืออาชีพ" · "ลูกค้าทักมา Seaaii ปิดยอดให้" · "หยุด! ... เริ่มตอบให้ปิดยอด". Body text: "ตอบไว • ปิดการขาย • เพิ่มยอด สนใจทดลอง Demo ระบบ โทร 0955989191 / @seaaii".
- Reading: lead-gen funnel (ad → Messenger → screening → demo call), not self-serve signup.
- **Reader pass (AGY Gemini read 14 site + 8 ad screenshots; I re-checked the claims below against raw text or the image):** about 13 distinct creatives, each angle runs a loud pain line. Angles beyond the hooks above: "ก่อนจ้างเพิ่ม ลองให้ AI ทำงาน 24 ชม." (instead of hiring) · "จ่ายค่าแอดให้คนทัก ต้องมี AI ช่วยปิดยอด" (protect your ad spend) · "ทุกแชทมีเงินซ่อนอยู่ คุณกำลังเก็บ หรือทำหล่น?" (hidden money) · "AI ที่ดี ต้องทำเงิน". Four of these are in the raw text [verified]; two image-only lines ("หยุดตอบ… เริ่มตอบให้ปิดยอด", the selfie ad's "ตอบ… ช้า…") the reader misread once, so quote them loosely. Style: dark navy neon, a white 3D robot, 13 s video; one UGC selfie ad and one warm-yellow phone walkthrough.
- **Arithmetic the ads do not show [computed]:** the ad says the starting package is "ไม่เกิน 300 บาท/วัน". The Standard plan, ฿29,000 for 3 months, is ฿315–322 a day. Advanced is ฿272 and Pro ฿216 a day. So the line holds for the two longer prepaid plans, not the entry plan; either there is an offer we cannot see or the line is loose. We do not know which.

## 4. The Facebook page (public view only)
- 2.9 หมื่น followers (≈29k), follows 3, 0 reviews, category "โฆษณา/การตลาด · บริการด้านธุรกิจ"; cover claims "ไว้ใจร้านค้าออนไลน์กว่า 10,000+ ร้าน".
- Logged-out we see ONE post (27 Sep 19:00, 13 s video, hook "Seaaii ไม่ได้ถูกสร้างมาเพื่อเป็นแค่ Chatbot ตอบคำถาม…") before the login wall. Cadence, formats, reactions, comments, who comments: **not seen yet**.
- Claim vs evidence: "10,000+ ร้าน" has no support on their own site (12 logos, no count). Treat as unverified marketing. Why 29k followers and many comments: **unknown**; the only evidence so far is the Seasalepage-to-Seaaii rename, which fits a follower base built under the older brand [inference, to be checked with the page's name history].

## 5. Chatudo vs Seaaii (preliminary, public layer only)
| Axis | Seaaii | Chatudo (CEO-approved 1 Oct) | Who wins today |
|---|---|---|---|
| Price | ฿9,667/mo, ฿29,000 upfront | Founding ฿990×2 then ฿1,990 | Chatudo, ~5× cheaper (fact) |
| Commitment | 3-month minimum, refunds case by case | 14 days free, no auto-charge, cancel any time | Chatudo (fact) |
| Promise | replace the admin ("AI ปิดจบได้") | help the admin | different, see risk below |
| Scope | orders, slips, tracking, couriers, CRM, API | chat reply + admin assist; no orders/slips/shipping | Seaaii (fact) |
| Verticals | online product sellers | courses, booking shops, small chat sellers | little overlap except small chat sellers |
| Reply quality | unknown | G0 sendable 4/19 = 21% vs 70% target (CTO, 3 Oct) | unknown / Chatudo is behind its own bar |
| Distribution | paid Messenger lead ads (22 running now; total spend and start unknown) | founder-led outreach, ~35 contacts/working day | not comparable yet |
- **Scary question:** if a small chat-selling shop wants orders, slips and shipping handled, is "helps your admin" at ฿1,990 enough, or do they pay 5× for Seaaii because it closes the sale? Cheapest test: ask the first 7 pilot shops what they do after the AI reply (write the order? check the slip?). If most say "I write the order by hand", the order feature is the product and we lack it.
- **Overlap is only segment 3** (small chat sellers). Courses, booking studios and clinics are not Seaaii's pitch. That is where Chatudo can stay out of its way.
- Not yet answered: how good Seaaii's AI replies are, what the trial gives, the page's real engagement. Those need the logged-in look.

### 5b. Where Seaaii is attackable, and where it is strong (site + ads, 4 Oct)
| Attackable (point to the page) | Level |
|---|---|
| Ads say "ไม่เกิน 300 บาท/วัน"; the site sells only 3/6/12-month prepaid blocks, ฿29,000 minimum, no monthly plan | read + computed |
| Token caps (25M/35M/50M) with no overage rule or "tokens per chat" explanation | read |
| "ลดเวลาตอบ 80% · ออเดอร์ตกหล่น −90% · ปิดการขาย +45%" with no baseline, sample or source | read |
| 3 testimonials: first names + shop type only, no shop name or link (placeholder avatars: reader saw, not checked by me) | read / seen |
| "ทดลองใช้งานฟรี" everywhere, trial length and limits nowhere | read |
| On-site AI demo is one question: "สินค้านี้มีสีอะไรบ้าง" → "มี 3 สีค่ะ…". No haggling, no objection, no order close shown | read |
| CRM only on the ฿79,000 plan; seat caps 5/7/10 | read |
| Legal: "AI may be wrong", refunds case by case, no PDPA text | read (terms) |

| Strong (we must respect) | Level |
|---|---|
| Whole order chain in every plan: slip check, tracking message, courier call (9 carriers), own storefront, API/webhook | read |
| Registered company shown with address, DBD Registered mark in the footer | read + seen (I checked the image) |
| 13 customer logos incl. Saha Farm, Thai Best Poultry, Little Sheep, Dr.G (we have not verified they are paying customers) | read |
| ~22 live ads with systematic angle testing (≥10 hooks, 2 versions each) and a screening-then-demo funnel: they run a real sales motion | read / inference |
- Reading for Chatudo: Seaaii sells **closing orders for product sellers** to shops that already pay for ads. Its weak points (prepaid lock-in, vague trial, one-question demo, no proof method) are exactly what a 14-day free pilot with real shop replies answers. Its strengths (orders, slips, shipping) are a different product from "helps your admin". Do not copy its "replaces the admin" frame (CEO ruling 28 Sep).

## 6. Next steps (cheapest first)
1. CEO registers a trial account through relay rq-6c31c0a5; a script captures the dashboard and a sample AI reply read-only.
2. CEO logs a spare Facebook account in via rq-601563ce; a script captures ~30 posts with reactions/comments/shares and reads the comment mix.
3. Then a final verdict on "can we win" with the two gaps closed.
