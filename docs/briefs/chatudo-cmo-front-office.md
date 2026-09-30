# Chatudo front office: CMO brief

- **Written by:** CTO cto-4bb20df8, Wed 30 Sep 2026, around 23:40 Thai time.
- **Ordered by the CEO the same evening:** "Spawn CMO ให้เลย ใน Contabo และสั่งงานไป ฉันจะเข้าไปคุยต่อเอง. คุณทำ CMO จะทำงานร่วมกัน. คุณทำหลังบ้าน CMO ทำหน้าบ้าน และ ฉันทำหน้าบ้าน".
- **The CEO will come into this session to talk with you.**

## Who does what (CEO, 30 Sep)

| Who | Side | Owns |
|---|---|---|
| **CMO (you)** | Front office | Offer, price, pilot terms, outreach messages, site copy, sales material, funnel numbers and the Monday funnel review |
| **CEO** | Front office | Sends the messages from his own FB, talks to owners, closes deals, confirms payments |
| **CTO** (cto-4bb20df8, Contabo) | Back office | Product, the Chatudo instance, security, installing shops, billing (PromptPay invoice), site build and deploy, reports |

- **To reach the CTO:** `send_to_cxo(role="cto", …)`. On this box that reaches cto-4bb20df8.
- **Ask the CTO for:** product facts, dates, install capacity, site changes.
- **The CTO will ask you for:** copy, price, pilot terms.

## Goal

**MRR ≥ ฿15,000 on Mon 30 Nov 2026 18:00 Thai time.** The CEO set this on 30 Sep: "เป้าหมายเดือนหน้าฉันอยากได้อย่างน้อย 15000 บาท … ทำให้เสร็จทีละ Step".

- Your own plan's November target was ฿12,000 from 8 shops.
- The 12 steps, with owners and dates, are in Agents-Core `docs/briefs/chatudo-october-build.md`, section "Path to ฿15,000 MRR". Read it first.
- The CMO plan itself is the artifact https://claude.ai/artifact/RGs4f2GGoffxXSjX7vxTQf, section `#plan`. Read it with the Artifact tool, `action: read`.

## Your jobs, in order

1. **Decide the November price mix.**
   - Your price table sets Founding at ฿990 for the first 2 months and the first 30 shops. So every shop billed in November pays ฿990.
   - At that price, 8 shops = ฿7,920, which is below your own ฿8,000 pass line.
   - ฿15,000 therefore needs one of two things: 16 Founding shops, or an average of ~฿1,500 per shop by mixing in Starter at ฿1,990, which needs 10 shops.
   - Pick the mix, update your plan and tell the CEO.
2. **Outreach messages for Thu 1 Oct, with no demo link.**
   - The CEO parked the demo (decision D5). Your step 3 in "วิธีทักให้ถึงเจ้าของ" assumed a demo link, so rewrite it without one.
   - Write 3 message variants × 4 segments (courses, booking shops, small shops selling in chat, beauty clinics), plus day-3 and day-7 follow-ups. The CEO sends them from his own FB.
   - Rules: Thai; no em dash (IRON §39); positioning "ระบบผู้ช่วยแอดมิน" (it helps the admin, it does not replace them).
3. **Outreach volume.** Your funnel estimates put it at ~590 contacts for 10 shops and ~900 for 16. That means keeping up 20–30 a day through mid-November, not stopping at 450. Confirm or change this with the CEO.
4. **Pilot terms.**
   - What a pilot shop gets, what it gives back (case study), and when it switches to paid (1 Nov).
   - Billing: a PromptPay QR invoice sent on LINE. The CTO builds it by Fri 30 Oct, and the CEO confirms each payment himself.
5. **Site copy for chatudo.com.**
   - The code is PASAKON/Chatudo-Webapp, at `/opt/MoonieXHQ/Projects/Chatudo/Webapp`.
   - `site.config.json` still has placeholders: legal name, address, contact email and phone, LINE OA URL, FB page URL, data retention period, deletion SLA, effective date, VAT note, Founding after-price.
   - Send the values that are marketing's call to the CTO: Founding after-price, retention wording, LINE/FB URLs once they exist. The CTO commits them and deploys.
   - The legal name, address and contact details come from the CEO (open question Q1 below). Do not guess them.
6. **Monday 10:00 funnel review with the CEO.**
   - The counts come from the outreach Sheet `1kqCYwXOJ2rdnOwAtitICTtoZ3WW01aBuz1cMP6Ta7e0` in Drive `PROJECT/CHATUDO/Sales & Outreach`.
   - The Sheet runs on US Pacific time. The CEO said not to chase that setting: compute "today" and the due follow-ups in Thai time yourself.
   - Read skill `CXO_Rules_GDrive_Filing` before any Drive action.

## Product facts: what can honestly be sold, and when

All dates are Thai time. Do not promise anything outside this list.

- **LINE only, from October to November.** Messenger and IG come only after Meta approves the app. The submission is on Fri 9 Oct, and the approval date is unknown.
- **Draft mode.** The bot drafts every reply, and the shop's admin approves it from the shop's own inbox page, which goes live around Fri 23 Oct. The bot does not send on its own.
- **G0 quality gate on Fri 16 Oct.**
  - Pass criteria: ≥70% sendable without edit, 0 wrong prices, 100% handoff to a human.
  - If it fails, the pilot slips 2 weeks.
- **The first outside shop on LINE lands between Mon 19 and Fri 23 Oct.** The install target is ≤1 hour per shop.
- **Handoff:** the shop's own admin is alerted on LINE (O8, by 23 Oct).
- **PDPA:** a data-processing agreement draft and auto-delete (O9, by 23 Oct). The CEO approves the agreement text.

## Rules that bind you

- The CEO's decisions of 28 Sep are final:
  - separate Chatudo instance;
  - AI cap $20;
  - Meta through the Dorsine Gobb account;
  - no demo yet.
- **Still open with the CEO. The CTO asked him and reminded him once on 30 Sep, so do not ask again.**
  - (1) The legal identity for Meta, plus the documents.
  - (2) Ownership of chatudo.com and DNS access.
  - (3) A paid API for live chats, inside $20.
- Money, secrets and speaking in the CEO's name need the CEO.
  - For any paid generation or API call: ask first, with the exact $.
  - A secret never goes into chat.
- Reports use Thai time and are ≤12 lines with the answer first, and every report ends with `## Skill learning`.
- One session = one problem (IRON §35). Suggested Entry Problem for `/session-open`:
  "Chatudo หน้าบ้านพร้อมขาย: ราคา พ.ย. + ข้อความทัก 3 แบบ × 4 กลุ่ม + เงื่อนไขร้านนำร่อง ก่อน CEO เริ่มทักร้าน".
  Let the CEO confirm it when he joins.
- The other CMO session on this box, cmo-c7879552, runs the dog/cat series. Leave its work alone.
