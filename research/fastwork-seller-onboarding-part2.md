# Fastwork Seller Onboarding — Part 2 (Screen 1 + view behind the gate)

Date: 2026-09-17
Account: PASAKON (CEO's own, confirmed authorization for Screen 1 only)
Flow: `https://fastwork.co/start-selling` → "สมัครเป็นฟรีแลนซ์" (body button, ref found via `find`, NOT header nav) → opens `https://seller.fastwork.co/apply-freelance` in new tab.

## Step 1 — username check

`https://fastwork.co/user/ilagstudio` → **404** ("ไม่พบหน้าที่คุณต้องการ" — page not found).
`ilagstudio` is **FREE**. Proceeded to Step 2 per instructions.

## Screen 1 — "สร้างโปรไฟล์ฟรีแลนซ์ของคุณ"

Values set (screenshot taken before saving):

| field | old (prefilled from buyer account) | new value set |
|---|---|---|
| Username | `mypasakon` | `ilagstudio` |
| ชื่อที่ใช้แสดงในระบบ (display name) | `PASAKON` | `ILAG Studio` |
| ประเภทฟรีแลนซ์ (Full-time/Part-time) | none selected | **Full-time** |
| Profile photo | carried over from buyer account | left as-is |

Live preview panel on the right updated in real time to show "ILAG Studio" with the carried-over avatar, confirming the values bound correctly before submit.

Note on ประเภทฟรีแลนซ์: the field label itself carries `(ไม่ได้แสดงผล)` — "not displayed [to buyers]" — printed directly under the heading in the UI. Confirms the task's note that this is an internal-only field.

**Clicked "บันทึก และไปต่อ" ONCE.** Waited 3s, re-read the page rather than re-clicking. Result: **Screen 1 SAVED** — the SPA advanced to a new step (same URL, `seller.fastwork.co/apply-freelance`, React app — there are no separate per-step URLs) with a new heading and the profile preview now permanently reading "ILAG Studio".

## Screen 2 — "อธิบายตัวตนของคุณให้ลูกค้ารู้จักมากขึ้น" (view-only, this is where I stopped)

> Heading: "อธิบายตัวตนของคุณให้ลูกค้ารู้จักมากขึ้น" ("Explain yourself so clients get to know you better")
> Subheading: "เล่าประวัติการทำงานของคุณ เช่น ประสบการณ์การทำงาน ประวัติการศึกษา ใบรับรองที่เคยได้รับ ฯ" (work history / education / certificates)

| field | label | required? | prefilled? |
|---|---|---|---|
| `about_me` (textarea) | "เกี่ยวกับฟรีแลนซ์" | **No** — confirmed via DOM (`textarea.required === false`, no `maxLength` cap) | **No** — empty string, only a placeholder ("อธิบายจุดแข็งของคุณโดยสังเขป เพื่อให้ผู้ว่าจ้างใช้ประกอบการพิจารณา") |

Two forward controls visible: "ระบุภายหลัง" (specify later / skip) and "บันทึก และไปต่อ" (save and continue, `type="submit"`).

**I did not click either.** Both are exactly the class of control the task's hard stops forbid ("DO NOT click save/submit/ยืนยัน/บันทึก/ถัดไป on ANY screen after Screen 1. If moving forward requires a save, you have reached the end of your authorization — stop and report."). Screen 2 is a single-field screen with no separate URL and no way to peek at Screen 3 without triggering one of those two buttons. This is also consistent with the CEO's own authorization wording — "กดหน้า 1 แล้วหยุดหน้าถัดไป" ("click page 1, then stop at the page after it") — which names stopping at the very next screen, not walking the whole funnel.

Progress bar: a `Layout_progress-bar` div with an inner fill element. On Screen 2 the fill computed to `width: 37.5%` (120px / 320px). No step-count text is present in the DOM (no "2/8" style label), so the total step count could only be inferred from this percentage, not confirmed. **Not treated as a confirmed answer — see Q7 below.**

## CEO sit-down checklist v2

Have these ready before sitting down to run the identity/bank/portfolio steps in one sitting:

1. **A short "about" writeup** for ILAG Studio — optional but this is the very first thing asked; skip is available (ระบุภายหลัง) if there's nothing ready.
2. Likely next, based on the funnel's placement industry-wide but **not yet confirmed by this task**: บุคคลธรรมดา/นิติบุคคล choice, ID card (photo/number/selfie), bank passbook, phone/OTP, and listing setup (packages, price, delivery time, portfolio images). None of these were reached — see Q1–Q6 below, all still-unknown.
3. Decide before sitting down whether to write the "about me" text now or click "ระบุภายหลัง" — that is the very next click, and it is the first one this task was not authorized to make.

## Answers to the 7 questions

1. **บุคคลธรรมดา / นิติบุคคล choice** — still-unknown. Never reached; it did not appear on Screen 1 or Screen 2.
2. **VAT-registration toggle** — still-unknown. Not reached.
3. **บัตรประชาชน (ID card): now or deferred, photo/number/selfie** — still-unknown. Not reached.
4. **สมุดบัญชีธนาคาร: now or at first withdrawal, which banks, name-match rule** — still-unknown. Not reached.
5. **OTP/phone step, phone on file vs re-entry** — still-unknown. Not reached.
6. **Listing requirements (min portfolio images, package tiers, delivery-time field, price floor)** — still-unknown. Not reached — the flow so far is only the profile-identity screens (name/username, then "about me"), not yet the listing/gig builder.
7. **Total steps on the progress bar** — still-unknown, not confirmed. The progress-bar fill was measured at 37.5% width on Screen 2 (up from a smaller, unmeasured fraction on Screen 1); no explicit "step X of N" label exists in the DOM to confirm N.

## Where the flow stands now

- Screen 1 (username/display-name/freelance-type) is **saved**.
- Currently sitting on Screen 2 ("เกี่ยวกับฟรีแลนซ์" / about-me text), unsaved, textarea still empty.
- **The very next click** would be either "ระบุภายหลัง" (skip, moves forward with `about_me` empty) or "บันทึก และไปต่อ" (save the about-me text and move forward) — both out of this task's authorization. Whoever continues next should type the about-me text (or deliberately skip) and click through, then keep recording screens 3+ under the same hard-stop discipline (screenshot + field table, stop again at the next forced save if fresh authorization hasn't been given).
- Browser tab was closed after recording; no further state left open on the account.

## Screenshots taken (2 of 8 budget used)

1. Screen 1 filled, before saving (username/display-name/Full-time + live preview).
2. Screen 2 as landed after the one authorized save (about-me textarea, empty, both forward buttons visible).

## Notes

- Clicking the correct "สมัครเป็นฟรีแลนซ์" (body, not header) opened a new tab that briefly fell outside the MCP tab-group tracking after an intervening tab-close; recovered by navigating a fresh tab to the same `seller.fastwork.co/apply-freelance` URL — same session/cookies, so it re-rendered the identical Screen 1 with no side effects (confirmed by the still-prefilled `mypasakon`/`PASAKON` values before the fill).
- No account history, chat, or order data was opened, read, or screenshotted at any point.
