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
improved_by:
  - {role: coo, date: "2026-11-28", what: "CEO 28 Nov end-to-end 7-step Rebate Resolution SOP (instant slip send vs 3-7d large-payout SLA, active account ID confirmation, Tue check-back)"}
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
| **E. Trade Screenshots Received (Large Case)** | Sent MT4/MT5 History screenshots (e.g. 50+ screenshots) | Check date range covered (first screenshot date → last screenshot date). Reply: `"ได้รับรูปประวัติการเทรดครบแล้วครับ เดี๋ยวแอดมินตรวจยอดแล้วแจ้งกลับนะครับ"` and `escalate` with `{customer, mt_id, image_count, date_range}`. |
| **F. Broker Deposit / Account Restricted** | Exness/XM deposit missing or `PMT... บัญชีถูกจำกัด` | Follow `CARE_Rules_MoonieX §3`: explain calmly in short bubbles to tap `"เปิดคำขอฝ่ายบริการลูกค้า"` in the broker app to check withdrawal/verification first (never advise duplicate registration to bypass restriction), and offer opening an XM account under MoonieX if they need a working Thai QR account with rebate. |
| **G. Simple Ack / Sticker After Close** | Sticker or `"ขอบคุณครับ/ค่ะ"` after case is answered | If a sticker alone needs no reply, `skip(event_id, "closing_sticker")`; if polite text, reply a single bubble `"ครับผม ติดปัญหาตรงไหนแจ้งได้ตลอดเลยครับ"`. |

### Step 3 · Pre-Send Gate (Self-Check Before Calling `reply`)
Check all 5 boxes before calling `reply`:
1. Zero `%` numbers and zero unapproved `$`/`฿` amounts anywhere in the text.
2. Plain text only (no `**`, no `#`, no bullet tables, no quotes wrapping the reply).
3. `≤5` short bubbles, one point per bubble, using `ผม`/`แอดมิน` + `คุณ<ชื่อ>` + natural Thai (`CMO_Standard_HumanVoice_TH`).
4. Every question the customer actually asked (including a second account ID like `<second-mt5-id>`) is addressed or explicitly escalated.
5. Never ask for passwords, OTPs, or secret keys.

### Step 4 · End-to-End Missing-Rebate Resolution Flow (CEO 2026-11-28 Standard SOP)
Whenever a customer reports missing XM rebates, execute this exact 7-step flow without improvising:
1. **Collect & Verify Account:** Get the customer's MT4/MT5 ID and the date rebates stopped (check `MyWallet` screenshot if sent — e.g. last rebate date). Escalate to COO/CTO to check XM Partner (`#/auto-rebate/report` and `#/reports/traders-trades`).
2. **Fix Plan First:** CTO moves/attaches the in-network account to `MNVIP30` (after CEO card if write-gated). Out-of-network accounts (`0` rows in XM Partner, 0 matching trader rows) are never paid back-pay — explain politely and invite opening an additional account with partner code `MNFUNDS`.
3. **Calculate Per-Customer Back-Pay (30% of MoonieX Commission):**
   - Count **only** the account(s) that customer asked about, for unpaid rows (`ค่าคอมรีเบตสำหรับนักเทรด = $0`) from their proven stop date through the plan-fix date.
   - If back-pay is **large (>\$30)**: ask the customer for MT4/MT5 history screenshots first and reconcile lots day-by-day against XM Partner before quoting any number.
4. **CEO Approval Card (`Q-...`) + THB FX Table:** Present the verified USD amounts + THB table at XM's real Local Bank withdrawal rate (`Spot − 2.0% to 2.5%` PSP FX spread) along with each customer's QR image. Never state an amount to a customer before the CEO taps approve.
5. **QR Collection & Payout Execution:**
   - **Instant transfer (small cases, ≤\$30):** Once CEO sends the transfer slips, verify recipient name + masked account on each slip against that customer's QR, then send: (a) the **actual slip image**, (b) confirmation naming the **exact MT4/MT5 account ID(s)** now active for rebate, (c) a sincere apology for the delay, and (d) the Monday-trade → Tuesday-rebate check-back notice.
   - **3–7 Day Payout SLA (large cases, >\$30):** Once CEO approves USD and customer sends QR, reply with: (a) apology for the delay + notice that the transfer will arrive within **3–7 days** and admin will notify immediately upon arrival, (b) confirmation that their **exact MT4/MT5 account ID** is now active for rebate (`ไม่ต้องเปลี่ยนรหัสพันธมิตร`), and (c) the Tuesday check-back notice; log a dated LungNote to-do (due in 3–5 days) so the payout is never forgotten.
6. **Tuesday Verification Loop:**
   - **10:30 TH Tuesday:** CTO checks XM Partner read-only whether Monday's trades on all fixed accounts credited rebate into `MyWallet` (fixing any issue before messaging customers).
   - **~11:00 TH Tuesday:** Proactively message each customer (`"รีเบตเมื่อวานเข้า MyWallet แล้วไหมครับ"`) to confirm end-to-end resolution.

## What This Protocol Never Does

- Never guesses whether an MT4/MT5 account is in our network without an XM check via COO/CTO.
- Never sends one copy-pasted broadcast reply to multiple customers without tailoring to each customer's own chat history.
- Never leaves an inbound event without either `reply` or `skip`.

## Field notes

- 2026-11-28 [MISSING] Multi-account customers (customer replying about a second MT5 ID without sending the QR for the fixed primary MT5 ID) require handling both threads in the next reply · evidence: Work/MoonieXCare/check-2026-11-28 · status: pending
