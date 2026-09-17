# Google Flow account audit — 2026-09-17

Project: «เงินที่พ่อตั้งใจหา» (`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`)
Account signed in: `pass.gob1@gmail.com` (กอล์ฟ พัสกร.)
**Zero credits spent.** No Generate/submit control was clicked. No settings were changed (aspect, quantity, and model selection were read, not modified — verified 9:16 / x1 / Nano Banana 2 unchanged throughout).

## 1. Credit balance — CONFIRMED

**88 credits**, read from the account menu (avatar top-right → "เครดิต Google Flow 88 เครดิต").
Also visible as a persistent low-credit banner across every page: "เครดิต Google Flow เหลือน้อย เครดิตจะรีเซ็ตทุกเดือน หรืออัปเกรดเพื่อรับเพิ่มตอนนี้" (credits low; credits reset every month).

This is **up** from the 2026-09-08 reading of 52 (+36 net over 9 days — consistent with the previously observed mid-month jump pattern, though the exact mechanism is still not directly observed).

## 2. Credit reset / renewal date — NOT VISIBLE

The account menu and the low-credit banner both say credits reset monthly ("เครดิตจะรีเซ็ตทุกเดือน") but give **no specific date or countdown**. Followed "จัดการการสมัครใช้บริการ" (Manage subscription) to the Google One settings page (`one.google.com/settings`, read-only) — it shows plan/price comparison only, **no billing/renewal date** anywhere on that page either. Not visible anywhere I could read without opening a purchase/billing-history flow, which was out of scope.

## 3. Plan — CONFIRMED: Google AI Plus

Badge in the Flow header reads **"PLUS"**. Cross-checked on the Google One settings page: current package is **"Google AI Plus (2 TB)" at ฿350/เดือน** (confirms this is the ฿350/mo tier, not the ฿9,400 Ultra tier under discussion). Upgrade options shown (read-only, not selected): Google AI Pro 5TB ฿750/mo, Google AI Pro 10TB ฿1,750/mo.

## 4. Ingredients and voices

All 5 ingredients still exist in the project — **CONFIRMED**:
- @lung_somchai — present
- @nong_daeng — present
- @grandma_pranom — present
- @lender_cherd — present
- @noodle_shop — present (location)

Voices — **CONFIRMED, and this is the headline finding: none of the 4 characters currently has a voice attached.**
Opened each character's detail page individually (@lung_somchai, @nong_daeng, @grandma_pranom, @lender_cherd). Every one shows the generic placeholder button **"เลือกเสียง"** ("Select voice") with no preset name next to it — the same UI state you'd see on a character that never had a voice installed. There is no sign of Algenib / Iapetus / Gacrux / Umbriel (the four presets recorded in the wiki voice-casting ledger) being attached to any of them right now.

I cannot tell from the UI alone whether this is a genuine detach (voices were installed 2026-09-08 and are now gone) or whether the character-level "เลือกเสียง" button simply never reflects a voice that was added via the composer-level flow described in the skill notes (voice chips attach per-generation in the composer, not stored on the character object). Either way: **as of right now, opening these 4 character pages shows no voice indicator.** Recommend re-verifying via the composer's ingredient picker (which does show attached voice chips per the skill notes) before concluding voices are lost — that check needs someone who can also re-read the shot scripts' VOICE LOCK lines, which is beyond this read-only pass.

## 5. Model currently selected

The project composer is currently in **Image mode** ("รูปภาพ"), not Video mode. In that mode the selected model is **🍌 Nano Banana 2**, aspect 9:16, quantity x1, generation cost shown as "0 เครดิต".

The model dropdown (opened read-only, closed with Escape, nothing selected) currently offers only image models: **Nano Banana Pro, Nano Banana 2, Nano Banana 2 Lite.**

**Not visible:** the video-model list (Omni 1.1 Flash / Veo 3.1 Fast / Veo 3.1 Quality) — reading it would require switching the composer's Image/Video toggle, which is a project-setting change the task's hard stops forbid. So I did not check which video model is currently selected. Worth noting: the *default* composer state on this load was Image mode, not Video mode — on earlier sessions (skill notes, 2026-09-07/08) the default was a video composer with Omni 1.1 Flash. That default appears to have changed.

## 6. Old clips — still retrievable, CONFIRMED

The "วิดีโอ" (Video) tab of the project lists **14 clips** (14 play-button thumbnails), all still present in the project history — nothing looked deleted or expired. I did not open individual clips to check exact filenames/timestamps (would need per-clip screenshots, outside the 3-screenshot budget), but the count and thumbnails confirm the history is intact and not wiped.

## 7. Changes since 2026-09-08

- **New promo modal on load: "Flow is now on iOS"** — a QR-code app-download interstitial that blocked the page until dismissed with its own X. Did not exist in the earlier recon notes. Closed without interacting further.
- **Composer defaults to Image mode (Nano Banana 2), not Video mode (Omni 1.1 Flash)** as it did on 2026-09-07/08. Possibly just this session's last-used state rather than a real UI default change — can't be certain from one read.
- **All 4 characters show no attached voice**, versus the 2026-09-08 wiki ledger recording Algenib/Iapetus/Gacrux/Umbriel as installed. See §4.
- No new plan tier, no new warning banner beyond the standing low-credit notice.

## What this means for the Ultra decision

- **88 credits remain** on the ฿350/mo PLUS plan (confirmed plan, not yet Ultra).
- At the measured rates: 88 credits buys roughly **4 Veo 3.1 Fast clips** (20 credits/8s@720p) or **7 Omni 1.1 Flash clips** (12 credits/8s@720p) — assuming those rates still hold; not re-measured this session (read-only, zero spend).
- The project itself is **structurally intact**: all 5 ingredients survive, the character plates are all still there, and all 14 previously generated clips are still in history and retrievable — nothing has been deleted by Google.
- The one real gap found: **no voice is currently attached to any of the 4 speaking characters**, which — if real and not just a UI display quirk — means dialogue shots cannot be fired with locked voices until they're re-attached. That's a same-session fix (attach preset → เพิ่มไปยังพรอมต์), not a data-loss problem, but it needs doing before any dialogue shoot, Ultra or not.
- Nothing found here argues for or against ฿9,400/mo Ultra specifically — the project would need the same voice re-attach step regardless of which Google AI tier is running.

## One-line summary

**88 credits, PLUS plan. All 5 ingredients survive; all 4 characters currently show no attached voice (needs re-check/re-attach); 14 old clips still retrievable, nothing deleted.**
