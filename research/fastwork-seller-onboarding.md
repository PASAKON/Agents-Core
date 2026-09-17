# Fastwork seller-onboarding walkthrough — account "PASAKON"

Date: 2026-09-17. Account: logged-in Mac Chrome session, buyer history back to Jan 2026.
Authorization: CEO confirmed 2026-09-17 this is his own account, "ไปต่อได้เลย" — view only, no submit (task-0b41a490).

## 1. Is the account already seller-enabled?

**No.** Confirmed two ways, live:

- Navigating directly to `https://seller.fastwork.co` bounces to the public marketing page
  `https://fastwork.co/start-selling` — there is no seller dashboard to redirect into.
- The page's own analytics calls (captured from `read_network_requests` on
  `seller.fastwork.co/apply-freelance`) carry `up.is_selling=false` and
  `upn.seller_verification_status=0` for this account's user id
  (`5687fec4-7daa-4a46-9209-271918bb08c1`).

So the job is "how to sign up," not "what's missing to go live" — Q1 in the brief is answered: not enabled.

## 2. The real entry point (verified live)

Tried in order:

1. `https://seller.fastwork.co` bare URL → **redirects to** `https://fastwork.co/start-selling` (marketing page only, confirms #1 above). Does not work as a direct onboarding entry for a non-seller account.
2. `https://fastwork.co/start-selling` — clicking the **"สมัครเป็นฟรีแลนซ์"** button (hero section, and the one repeated near the page bottom) **opens a new tab** at:

   **`https://seller.fastwork.co/apply-freelance`** ← this is the real, working onboarding entry point.

   (The task brief noted the *homepage* CTA "เริ่มรับงาน"/"สมัครเป็นฟรีแลนซ์" produced nothing while logged in — that was the homepage nav button. The one embedded in the `/start-selling` page body works and opens the flow in a fresh tab.)
3. Header profile/account menu — not needed once #2 worked; not explored further (out of scope once the real path was confirmed).

## 3. Screens walked, in order

### Screen 1 — "สร้างโปรไฟล์ฟรีแลนซ์ของคุณ"

URL: `https://seller.fastwork.co/apply-freelance`
Subheading: "กำหนดข้อมูลเบื้องต้นเพื่อสร้างความน่าเชื่อถือ"

A progress bar at top shows this is step 1 of several (first of ~6 segments lit). A live preview card on the right mirrors the profile as it will look to buyers (avatar, name, and 4 placeholder stat rows for reviews/orders/repeat-rate/messages).

Fields on this screen:

| Field | Already filled? | Required? | Agent-can-type / CEO-must-do | Notes |
|---|---|---|---|---|
| Username (`Fastwork.co/user/___`) | **Yes** — prefilled `mypasakon` | Yes | Agent-can-type (if CEO wants a different handle) | English only, becomes part of the public profile URL |
| ชื่อที่ใช้แสดงในระบบ (display name) | **Yes** — prefilled `PASAKON` | Yes | Agent-can-type | Carried over from the buyer account |
| Profile photo | **Yes** — carried over from the buyer account (same S3-hosted photo used in buyer profile) | — | — | No upload needed for this field; already usable |
| ประเภทฟรีแลนซ์ (Part-time / Full-time) — labelled "(ไม่ได้แสดงผล)" i.e. not shown publicly, internal only | **No** — neither radio pre-selected | Yes | Agent-can-type (just a radio choice, not personal data) | Helper text: "ใช้พัฒนาระบบเพื่อคุณเท่านั้น หากยังเป็นนักศึกษาอยู่ ตอบ Part-time ได้เลย" |
| Button: **"บันทึก และไปต่อ"** | — | — | **CEO must click** | This is a write action (saves username + freelancer type to the real account). Matches the task's banned-word list ("บันทึก") — **not clicked**. This is as far as the flow was walked. |

### Screens 2+ — not reachable read-only

Fastwork's `apply-freelance` flow is server-backed step-by-step: the next screen's content is only served **after** "บันทึก และไปต่อ" POSTs screen 1's data. There is no read-only preview of steps 2+ through the live app itself. Attempts to find the remaining screens without writing to the account:

- Direct call to the page's own status endpoint (`POST api/user/v2/applySeller.getProgressAndData`, seen in the network log) returned `401 UNAUTHORIZED` when re-issued manually — it needs auth context beyond cookies that wasn't worth reproducing for a read-only peek.
- Fastwork's Zendesk help centre 403s automated fetches (already known from prior task).
- The official walkthrough video linked from `start-selling` (`https://youtu.be/c_Zbam4k8xw`, labelled "ดูวิดิโอ ตัวอย่างการสมัครเป็นฟรีแลนซ์") has no fetchable transcript via WebFetch — YouTube serves an SPA shell with no captions text.

So everything below about steps 2+ is **carried over from the public `fastwork.co/start-selling` marketing copy only** (already known before this session, restated here for completeness) — it is **not verified against the live form** and is labelled as such:

- Step 2 (unverified, from public copy): "ลงประกาศขายงาน" — prepare portfolio (ผลงาน) and job/service descriptions; submission reviewed and approved by Fastwork staff within 48 hours.
- Registration overall requires บัตรประชาชน (ID card) + สมุดบัญชี (bank passbook) ready, per the public copy's step 1 description — not yet seen as an actual form field, since we stopped before reaching it.
- Minimum age 18 (from public copy, prior task's research).
- The three tiers — Freelancer / Specialist / Professional — are confirmed (again) on the public page as a ladder earned after selling, **not a signup-time choice**.

## 4. บุคคลธรรมดา / นิติบุคคล — does this choice exist?

**Not seen on Screen 1**, and not mentioned anywhere in the public `start-selling` copy. Cannot confirm or deny it appears on a later screen — those screens were not reachable without writing to the account (see §3). **Do not treat this as "confirmed absent"** — it is an open question, flagged below rather than guessed at (CEO rule: ห้ามเดา).

## 5. VAT-registration toggle — does this exist?

Same answer as §4: not seen on Screen 1, not mentioned in public copy, not confirmed either way. Open question.

## 6. Listing-creation requirements (minimum images, tiers, delivery time, price floor)

**Not reached.** The listing-creation screen sits behind both "บันทึก และไปต่อ" on Screen 1 and the entire step-2 identity/bank verification gate. Could not view it without submitting Screen 1 first. Open question — needs either explicit sign-off to proceed past the "บันทึก" button, or the CEO doing it himself.

## 7. Where the flow first becomes irreversible

**Right here: the "บันทึก และไปต่อ" button on Screen 1** (`สร้างโปรไฟล์ฟรีแลนซ์ของคุณ`). It is the very first control in the entire flow, and it:

- Writes the chosen username and freelancer-type to the real, 8-month-old "PASAKON" account.
- Is required to unlock every subsequent screen — there is no way to preview further without triggering it.
- Matches the task's explicit "do not click" pattern (button text contains "บันทึก").

Everything after that point (ID card upload, bank book upload, portfolio, any OTP) is necessarily further along the same one-way ladder and was not explored.

## CEO sit-down checklist

Have in hand before starting (from public copy + confirmed account state):

- [ ] บัตรประชาชน (ID card) — physical or clear photo, for identity verification
- [ ] สมุดบัญชีธนาคาร (bank passbook / bank account details) — for payout verification
- [ ] Decide: username (`mypasakon` is already reserved/prefilled — keep or change)
- [ ] Decide: display name (currently `PASAKON` — keep or change)
- [ ] Decide: ประเภทฟรีแลนซ์ — Part-time or Full-time (internal only, not shown publicly)
- [ ] Portfolio material (ผลงาน) + a description of the service(s) to sell, for the listing step
- [ ] Be ready for a phone/OTP step if one appears (not yet seen — Fastwork already has this account's phone/email from the buyer history, but a verification code may still be sent to confirm)

Ordered steps, in one sitting:

1. Open `https://fastwork.co/start-selling`, click "สมัครเป็นฟรีแลนซ์" → opens `seller.fastwork.co/apply-freelance` in a new tab.
2. Confirm/edit username and display name (both prefilled already).
3. Pick Part-time or Full-time.
4. Click "บันทึก และไปต่อ" — **this is the CEO's click, not an agent's**, since it's the first real write to the account and everything past it is uncharted (ID/bank upload most likely next).
5. From there: expect ID card upload, bank passbook upload, and possibly an OTP — all HARD-STOP items for an agent, so the CEO drives the rest of the flow personally, in the same sitting, using the documents gathered above.
6. Once past verification, expect a listing-creation step (portfolio + description) — unverified field list; the CEO should expect to spend a few more minutes here per the public copy ("เตรียมผลงานและคำอธิบายงาน").
7. Submit for review; Fastwork approves within 48 hours per public copy.

## Open questions (do not guess — flagging per CEO instruction)

1. Does a บุคคลธรรมดา / นิติบุคคล choice exist anywhere in steps 2+? — **unconfirmed**, not visible on Screen 1 or in public docs.
2. Does a VAT-registration toggle exist? — **unconfirmed**, same reason.
3. Exact fields/limits on the listing-creation screen (minimum portfolio images, number of package tiers, delivery-time field, price floor) — **unreached**, gated behind Screen 1's save + identity verification.
4. Whether an OTP/SMS step appears during identity verification, and whether the phone number on file (from the buyer account) is reused or must be re-entered — **unreached**.
5. Exact total step count in the progress bar — the bar showed step 1 of several; count not confirmed since only step 1 was viewed.

To resolve 1–4, the CEO needs to click through Screen 1 himself (or explicitly authorize an agent to click "บันทึก และไปต่อ" and continue past it), since the product gates every subsequent screen behind a real write.
