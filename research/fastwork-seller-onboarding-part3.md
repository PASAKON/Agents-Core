# Fastwork Seller Onboarding — Part 3 (Screen 2 skip → Screen 3 wall: ID card)

Date: 2026-09-17
Account: PASAKON / ILAG Studio (CEO's own, buyer account 8 months old, now applying as freelancer)
Authorization: CEO 2026-09-17, "เดินทะลุหน้าที่ไม่ขอข้อมูลส่วนตัว" — walk through any screen that does not ask for personal data; stop the instant one does.
Continues from `research/fastwork-seller-onboarding-part2.md` (Screen 1 saved: username `ilagstudio`, display name `ILAG Studio`, Full-time — landed back on Screen 2, unsaved, same session/cookies).

## Numbered walkthrough

### Screen 2 — "อธิบายตัวตนของคุณให้ลูกค้ารู้จักมากขึ้น" (about-me)

- Heading: อธิบายตัวตนของคุณให้ลูกค้ารู้จักมากขึ้น
- Subheading: เล่าประวัติการทำงานของคุณ เช่น ประสบการณ์การทำงาน ประวัติการศึกษา ใบรับรองที่เคยได้รับ ฯ

| field | label | required? | prefilled? |
|---|---|---|---|
| `about_me` (textarea) | เกี่ยวกับฟรีแลนซ์ | No | No — empty, placeholder only |

Left empty (not mine to write — the CEO's own pitch text, per this task's instructions). Progress bar measured at 37.5% (confirmed again this run, matches part2).

**Left via: "ระบุภายหลัง"** (skip). First click via element `ref` did not advance the SPA (heading unchanged after 2s and after a retry) — a real pixel click on the same button's coordinates did advance it. Note this for the replay script: ref-based `computer` clicks on this button silently no-op on this build; use pixel coordinates or `find` immediately followed by a coordinate click.

### Screen 3 — "ข้อมูลบัตรประชาชนเพื่อออกเอกสาร 📑" (ID card info, for issuing documents) — **THE WALL**

- Heading: ข้อมูลบัตรประชาชนเพื่อออกเอกสาร 📑
- Subheading: อย่าลืมเช็คความถูกต้องก่อนบันทึก ("don't forget to check correctness before saving")
- Live preview panel on the right renders a **ใบเสร็จรับเงิน** (receipt/tax document) template with ผู้ขาย (seller) / ลูกค้า (customer) fields — this screen exists to populate the legal identity that goes on that receipt, which is why it wants the real name + ID number rather than the display name/username from Screen 1.

Every field on this screen (from live DOM, `name` attributes confirmed via `javascript_tool`):

| field | label | input | required (DOM attr)? | prefilled? |
|---|---|---|---|---|
| `national_card.initial` | คำนำหน้าชื่อ | dropdown: นาง / นางสาว / นาย | `required=false` in DOM, but flow-gated (form won't advance without it in practice — not tested) | No — "กรุณาระบุ" placeholder shown |
| `national_card.first_name` | ชื่อ | text | `required=false` in DOM | No |
| `national_card.last_name` | นามสกุล | text | `required=false` in DOM | No |
| `national_card.uid` | เลขบัตรประชาชน | text, placeholder "ระบุเลขบัตรประชาชน 13 หลัก" (13-digit ID number, **typed**, not a photo upload) | `required=false` in DOM | No |
| `national_card.address` | ที่อยู่ตามบัตรประชาชน → รายละเอียดที่อยู่ | text, placeholder "ระบุเลขที่, หมู่, ถนน, ซอย" | `required=false` in DOM | No |
| (react-select) | รหัสไปรษณีย์ | dropdown/typeahead | — | No |
| (react-select) | จังหวัด | dropdown | — | No |
| (react-select) | อำเภอ/เขต | dropdown | — | No |
| (react-select) | ตำบล/แขวง | dropdown | — | No |

Confirmed by direct DOM query (`document.querySelectorAll('input[type=file]').length === 0`, and no match for `/selfie|liveness|ถ่ายรูปคู่|เซลฟี่|ยืนยันตัวตนด้วยใบหน้า|ถ่ายรูปบัตร|อัปโหลด|upload/i` anywhere in `body.innerText`):

- **No photo/file upload field of any kind on this screen.**
- **No selfie or liveness-check step.**
- Only **typed** text/dropdown fields: title, first name, last name, 13-digit ID number, address (free text + 4 dropdowns for postal code/province/district/subdistrict).

Progress bar: 62.5% fill (200px / 320px), up from 37.5% on Screen 2 — a 25-point jump for this one step. Not enough data points to derive N confidently (see Q7).

**I did not type into any field and did not click "บันทึก และไปต่อ".** This is a hard-stop screen per the task's rules (บัตรประชาชน number + real legal name + address are explicitly listed personal data). Screenshotted, recorded every field above, then closed the tab. No further navigation attempted.

## THE WALL SCREEN — full detail

**Screen 3, "ข้อมูลบัตรประชาชนเพื่อออกเอกสาร"**, is the first hard stop reached this task. What the CEO must have in hand to clear it himself:

1. **คำนำหน้าชื่อ** — นาง / นางสาว / นาย (pick one)
2. **ชื่อ-นามสกุลจริง** (real first + last name, presumably matching the ID card — not the "ILAG Studio" display name from Screen 1)
3. **เลขบัตรประชาชน 13 หลัก** — the CEO must type the 13-digit ID number himself. No photo/OCR path exists on this screen — it is pure manual entry.
4. **ที่อยู่ตามบัตรประชาชน** — full ID-card address: house number/moo/road/soi (free text) + รหัสไปรษณีย์/จังหวัด/อำเภอ/ตำบล (four dropdowns)

No selfie, no ID photo, no liveness check on THIS screen — but the screen explicitly says the purpose is "เพื่อออกเอกสาร" (to issue documents/receipts), so Fastwork is treating this as the legal-identity-of-record step, not a KYC/verification step. Whether a photo/selfie verification step exists **later** (e.g. before first payout) is still unknown — this screen simply isn't it.

## CEO sit-down checklist v3

In order, from where the flow now sits (Screen 3, unsaved, nothing typed):

1. Have ready: title (นาย/นาง/นางสาว), full legal first+last name exactly as on the ID card, the 13-digit ID number, and the ID-card address broken into (a) house/moo/road/soi free text, (b) postal code, (c) province, (d) district (อำเภอ/เขต), (e) subdistrict (ตำบล/แขวง).
2. Type/select all of the above on Screen 3, then click **"บันทึก และไปต่อ"** — this is the very next click (see below), and it is the first one this task was not authorized to make.
3. From there, expect (not yet confirmed, still-unknown per below): a bank-account screen, possibly a legal-form (บุคคลธรรมดา/นิติบุคคล) or VAT screen, possibly an OTP/phone step, then the listing/gig builder. None of these have been observed yet — the next operator resumes exploration immediately after Screen 3 is saved, under the same hard-stop discipline (screenshot + field table, stop again at the next screen demanding bank details, OTP send, file upload, or a submit/publish action).
4. Per `mooniex:projects/ilag-studio.md`, the CEO has already decided **บุคคลธรรมดา** (individual, no VAT registration) for this shop — if/when a บุคคลธรรมดา/นิติบุคคล choice appears, that decision is already made; confirm the screen doesn't lock in anything irreversible before selecting it.

## The seven questions

1. **บุคคลธรรมดา / นิติบุคคล choice** — **still-unknown.** Not seen on Screen 2 or Screen 3. (Wiki note: CEO has already decided บุคคลธรรมดา for this shop, per `mooniex:projects/ilag-studio.md` — but the screen itself has not yet been observed in this flow.)
2. **VAT-registration toggle** — **still-unknown.** Not reached.
3. **บัตรประชาชน — now or deferred; photo/number/selfie?** — **CONFIRMED.** Demanded **now**, during onboarding (Screen 3), not deferred to first payout. It is **typed only**: 13-digit number + name + address as text/dropdown fields. **No photo upload, no selfie/liveness check** anywhere on this screen (confirmed via DOM: 0 file inputs, no selfie/liveness/photo-upload text present).
4. **สมุดบัญชีธนาคาร — now or at withdrawal, which banks, name-match rule** — **still-unknown.** Not reached; Screen 3 (ID card) came before any bank screen.
5. **OTP/phone step, phone on file vs re-entry** — **still-unknown.** Not reached.
6. **Listing requirements (min portfolio images, package tiers, delivery-time field, price floor)** — **still-unknown.** Not reached — still in the identity section of the funnel, not the listing/gig builder.
7. **Total step count** — **still-unknown, not confirmed.** No "X of N" label exists in the DOM on either screen observed. Progress-bar fill measured: Screen 2 = 37.5%, Screen 3 (ID card) = 62.5% — a 25-point jump for one step. Not enough data to derive N with confidence; treat any guess (e.g. "4 more equal steps") as unconfirmed.

## What the very next click would be

On Screen 3, with all ID-card fields filled in: click **"บันทึก และไปต่อ"** (the blue button under the ตำบล/แขวง dropdown). This is exactly the click this task was not authorized to make, since it requires typing the CEO's real ID number, legal name, and home address first.

## Screenshots taken (3 of 10 budget used this task)

1. Screen 2 as landed (about-me textarea, empty, both forward buttons) — confirms state matched part2's report exactly.
2. Screen 3 (ID card), scrolled to show postal-code/province/district/subdistrict + the "บันทึก และไปต่อ" button.
3. Screen 3, scrolled to top, showing the full heading, title/name/ID-number fields, and the live receipt preview panel.

No order history, chat, buyer names, or order IDs were opened or captured at any point.

## Notes for whoever continues

- Ref-based clicks on the "ระบุภายหลัง" button silently no-op on this SPA build (React event delegation likely needs a real pointer event, not the synthetic one `computer` dispatches via `ref`) — use pixel coordinates from a screenshot instead, or verify the heading actually changed after a `ref` click before assuming it worked.
- Tab was closed after recording (`tab_registry.py done`); no state left open on the account.
- The flow remains a single-page app with one URL (`seller.fastwork.co/apply-freelance`) for every step — re-navigating to that URL resumes exactly where the account left off (confirmed twice now, across two separate task sessions).
