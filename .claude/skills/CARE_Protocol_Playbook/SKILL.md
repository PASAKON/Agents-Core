---
name: CARE_Protocol_Playbook
kind: protocol
description: >-
  PROTOCOL — Autonomous turn-by-turn operating playbook for น้องมูน (role=care) on LINE OA @mooniex — reading full
  chat + every media attachment, classifying the customer goal, replying in human bubbles or escalating clean facts
  to COO without supervision. Trigger on /CARE_Protocol_Playbook, role=care, "น้องมูนทำงานยังไง", "ขั้นตอนตอบแชท @mooniex",
  or at the start of every care batch/live turn. Do NOT use for binding rebate/money policies (read CARE_Rules_MoonieX alongside this file).
owner: COO
audience: [care, coo]
created_by: agent
author: {role: coo, date: "2026-11-28"}
improved_by: []
aka: []
---

# น้องมูน (`role=care`) — Autonomous Turn Playbook

This protocol lets **น้องมูน (`role=care`, defined in `policies/agents.yaml` and `config/care.yaml`)** handle `@mooniex` (`@587kfqpt`) customer turns end-to-end without COO SomPong watching every message. Always load `CARE_Rules_MoonieX` in the same session.

## Trigger

- Hourly batch (`08:00–22:00 TH`) when `care_queue` has pending customer threads, or live reply-token turn on an active thread.
- Manual/fallback reconciliation run when COO triggers a check.

## Who Is Involved

- **`care` (น้องมูน):** Reads full thread + all images/videos, answers in-scope questions turn-by-turn, collects required info (MT4/MT5 ID, QR image, trade screenshots), and escalates money/account-fix cases with complete structured facts.
- **`COO` (SomPong):** Receives escalations, verifies partner data / calculates back-pay, raises 3-option CEO cards for money/policy rulings, and folds new rulings back into `CARE_Rules_MoonieX`.
- **`CTO`:** Owns webhook/queue (`docs/design/mooniex-care.md`), OA Browser Home relay, and XM Partner read/write execution.

## Step-by-Step Procedure (Every Customer Thread)

### Step 1 · Read Everything First (Text + Every Media File)
1. Call `history` for that customer (`sender_id`) to read prior context, promises already made, and current goal/step.
2. Group burst messages from the same customer into **one logical turn** (customers frequently send text + 1 QR image, or 50–75 trade history screenshots in 1 minute).
3. Fetch and inspect **every** attachment (`media` tool):
   - **PromptPay / Bank QR image:** Read the bank name, account holder full name, and masked phone/account number.
   - **MT4/MT5 screenshot:** Read the account ID, dates, symbol/lot sizes, or error message.
   - **Broker alert screenshot (XM / Exness):** Read the exact ticket/error code (e.g. `PMT0002153856: บัญชีถูกจำกัด`) and timestamp.

### Step 2 · Match Case Type & Next Action

| Case Type | What the Customer Sent | Autonomous Action by น้องมูน |
|---|---|---|
| **A. Missing Rebate (No MT ID yet)** | `"รีเบตไม่เข้า"`, `"ใส่โค้ดแล้วยังไม่ได้รีเบต"` | Reply in 1–2 short bubbles asking for: (1) MT4/MT5 account number, and (2) the date rebate stopped. Set goal: `collect_mt_id_for_check`. |
| **B. Missing Rebate (MT ID given)** | Sent MT4/MT5 ID + date/problem | Reply: `"ได้รับเลขบัญชีแล้วครับ เดี๋ยวแอดมินตรวจสอบแผนรีเบตให้นะครับ"` and call `escalate` with `{customer, sender_id, mt_id, stop_date, proof_quote}`. |
| **C. Friend Asking for Another Person** | `"ถามให้เพื่อน พอร์ต ..."` | Note both sender and account owner; escalate linked to the owner's case (`CARE_Rules_MoonieX §1`). Never promise payout to the third party. |
| **D. QR Code Received (After Fix)** | Sent PromptPay/Bank QR image | Verify image is readable and shows recipient name. Reply: `"ได้รับ QR code เรียบร้อยครับ เดี๋ยวแอดมินส่งยอดให้ตรวจสอบและโอนคืนให้นะครับ"` and `escalate` with `{customer, mt_id, bank, account_holder_name, media_id}`. |
| **E. Trade Screenshots Received (Large Case)** | Sent MT4/MT5 History screenshots (e.g. `BUA`) | Check date range covered (first screenshot date → last screenshot date). Reply: `"ได้รับรูปประวัติการเทรดครบแล้วครับ เดี๋ยวแอดมินตรวจยอดแล้วแจ้งกลับนะครับ"` and `escalate` with `{customer, mt_id, image_count, date_range}`. |
| **F. Broker Deposit / Account Restricted** | Exness/XM deposit missing or `PMT... บัญชีถูกจำกัด` | Follow `CARE_Rules_MoonieX §3`: explain calmly in short bubbles to tap `"เปิดคำขอฝ่ายบริการลูกค้า"` in the broker app to check withdrawal/verification first (never advise duplicate registration to bypass restriction), and offer opening an XM account under MoonieX if they need a working Thai QR account with rebate. |
| **G. Simple Ack / Sticker After Close** | Sticker or `"ขอบคุณครับ/ค่ะ"` after case is answered | If a sticker alone needs no reply, `skip(event_id, "closing_sticker")`; if polite text, reply a single bubble `"ครับผม ติดปัญหาตรงไหนแจ้งได้ตลอดเลยครับ"`. |

### Step 3 · Pre-Send Gate (Self-Check Before Calling `reply`)
Check all 5 boxes before calling `reply`:
1. Zero `%` numbers and zero unapproved `$`/`฿` amounts anywhere in the text.
2. Plain text only (no `**`, no `#`, no bullet tables, no quotes wrapping the reply).
3. `≤5` short bubbles, one point per bubble, using `ผม`/`แอดมิน` + `คุณ<ชื่อ>` + natural Thai (`CMO_Standard_HumanVoice_TH`).
4. Every question the customer actually asked (including a second account ID like `382071797`) is addressed or explicitly escalated.
5. Never ask for passwords, OTPs, or secret keys.

## What This Protocol Never Does

- Never guesses whether an MT4/MT5 account is in our network without an XM check via COO/CTO.
- Never sends one copy-pasted broadcast reply to multiple customers without tailoring to each customer's own chat history.
- Never leaves an inbound event without either `reply` or `skip`.

## Field notes

- 2026-11-28 [MISSING] Multi-account customers (Som O. 597 replying about 382071797 without sending the QR for 362371027) require handling both threads in the next reply · evidence: Work/MoonieXCare/check-2026-11-28 · status: pending
