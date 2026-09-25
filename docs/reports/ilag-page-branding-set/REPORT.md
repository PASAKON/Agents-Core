# ILAG Page branding — profile picture + cover photo set (task-58bd4100)

## Summary

Both images set on Page «ละครสั้นคุณธรรม by ILAG Studio» (id `61594116376333`,
asset_id `1319535331240503`), using exactly the CEO-approved files, default
centered position, no drag/zoom. Verified live on the Page while viewing as
the personal account (Dorsine Gobb), i.e. the public state, not an
admin-only preview.

- Profile picture: `FINAL-profile-lotus-ilag-circle-1080.png` → set.
- Cover photo: `FINAL-cover-two-worlds-title-by-1640x624.png` → set.

## Route used

route: step 5 (text-first DOM discovery), escalating to screenshots only
when a control had no discoverable text/aria path — this is a one-off
branding task with no API, so browser driving was correct per the task
brief; no existing script covered this flow.

1. **Cover photo** — done from **Meta Business Suite home**
   (`https://business.facebook.com/latest/home?asset_id=1319535331240503`).
   The page showed "เพิ่มรูปภาพหน้าปก" (Add cover photo) directly, no
   identity switch needed.
   - Clicked "เพิ่มรูปภาพหน้าปก" → menu → "อัพโหลดรูปภาพ" → `expect_file_chooser()` →
     `set_files(cover_path)` (Playwright intercepts before Chrome ever draws a
     native dialog — no click on a picker was made).
   - Default position was already centered/full-bleed (matches the file's
     1640×624 exact dimensions) — no drag performed.
   - Saved via "บันทึกการเปลี่ยนแปลง". Button text changed from
     "เพิ่มรูปภาพหน้าปก" → "แก้ไขรูปภาพหน้าปก" confirming save landed. Facebook
     auto-created a normal timeline update post (seen via a lightbox opened
     by an early exploratory click) — left as default per task step 3, not
     boosted, nothing else touched on it.

2. **Profile picture** — Business Suite home has **no equivalent control**
   for the profile picture (only cover). Per the task's alternative route,
   switched into the **Page identity** (top-right account menu →
   "Dorsine Gobb"/"ILAG Studio" switcher → selected "ILAG Studio"). From
   there:
   - The avatar is a `div[role="button"] aria-label="การดำเนินการกับรูปโปรไฟล์"`
     covering the full circle — clicking its exact center intermittently hit
     a child status-note bubble instead (opened a "โน้ตใหม่" dialog once, closed
     without posting). Dispatching `.click()` on the element directly via
     `page.evaluate` reliably opened the real menu → "เลือกรูปโปรไฟล์" →
     "อัพโหลดรูปภาพ" → `expect_file_chooser()` → `set_files(profile_path)`.
   - Crop preview showed the image centered exactly as delivered (the file
     already has the margin baked in for FB's circular crop) — accepted the
     default, no zoom/drag.
   - Clicked "บันทึก" (Save). Body text then read "รูปโปรไฟล์ของคุณได้รับการอัพเดตแล้ว"
     ("Your profile picture has been updated"), confirming the save.
   - Switched identity back to "Dorsine Gobb" via the same account menu
     immediately after.

## Verification

Navigated to the live Page URL (`https://www.facebook.com/profile.php?id=61594116376333`)
**while back on the personal identity** (Dorsine Gobb — confirmed by the
sidebar showing the disabled/⊘ admin-tool icons that only render for a
non-switched viewer, same as the pre-task baseline).

- `img[src]` for the cover: `.../824452135_122116356093470545_...` at
  **1640×624** — matches the delivered file's exact dimensions.
- `<image>` (SVG) `href` for the profile picture: `.../821639219_122116363539470545_...` at
  168×168 (rendered avatar size) — a different asset id than the pre-task
  default placeholder, confirming the new upload took.
- Screenshot saved: `~/MoonieXHQ/Work/task-58bd4100/out/verify-live-page.png`
  (moved out of the git repo — media_guard pre-commit hook rejects files
  over 1.0 MB per ADR 0030; this PNG is 1.7 MB) — shows the gold lotus + ILAG
  circle as the profile picture and the two-worlds scene with
  «ละครสั้นคุณธรรม» / "by ILAG Studio" as the cover, both centered as
  delivered.

Both images took. Nothing else on the Page (name, username, category,
about, buttons, access) was touched.

## Identity switch

Switched into the Page ("ILAG Studio") identity to reach the profile-picture
control, then **switched back to "Dorsine Gobb" (personal) before finishing** —
confirmed by the top nav returning to personal-mode icons (home/reels/
marketplace/dating/gaming) and the personal avatar.

## Replay script

**None** — one-off branding task (set once, not a recurring flow); no
repetition occurred that would justify a script per the skill's >3-repeat
rule. If this ever needs to run again (e.g. a future re-brand), the steps
above are the whole flow: cover via Business Suite's "เพิ่มรูปภาพหน้าปก" menu,
profile picture via the Page-identity avatar's
`[aria-label="การดำเนินการกับรูปโปรไฟล์"]` → "เลือกรูปโปรไฟล์" → "อัพโหลดรูปภาพ"
→ `expect_file_chooser` → `set_files` → "บันทึก".

## Issues / Blockers

- **Unintended side effect, not undoable**: while locating the account-switch
  menu (searching by rough on-screen coordinates before falling back to a
  DOM bounding-box query), one exploratory click landed on something that
  triggered a toast: "ซ่อนงานแล้ว คุณจะไม่เห็นงานเหล่านี้บนเพจของคุณอีก"
  ("Jobs hidden — you won't see these jobs on your Page anymore"). This reads
  as dismissing a "recommended jobs" suggestion widget in the admin view, not
  a public-facing Page change (no Page setting, post, or content was
  affected — verified via the live-page screenshot and DOM checks above).
  The toast's "เลิกทำ" (Undo) option had already expired by the time I tried
  to reverse it. Flagging it transparently since it was not authorized by
  the task and I could not confirm undo; it does not appear to be visible to
  the public or to have changed anything reviewable on the Page.
- No login/verification prompts encountered. No credentials entered. No
  boosting. No other Page setting changed.

## Notes for Reviewer

- Please check `~/MoonieXHQ/Work/task-58bd4100/out/verify-live-page.png`
  visually to confirm the two images read correctly at a glance.
- The "ซ่อนงานแล้ว" toast above is the one loose end — if it turns out to be
  more than a recommendation-widget dismissal, it should be easy to find
  under the Page's Business Suite "งาน"/Jobs area and re-enable.

## Skill learning
- COSTLY [browser-operator §Budget] : profile-picture edit control had no discoverable aria/text path from Business Suite home (only cover photo does); needed identity switch + a bounding-box DOM scan + a JS-level `.click()` to bypass a child element intercepting the hit-test at the visual center of the avatar button. This alone drove screenshot count well past the 5-screenshot soft cap for what is otherwise a two-click task. · evidence: task-58bd4100, ~30+ screenshots taken · prevented by: a future skill note naming the working selector `[aria-label="การดำเนินการกับรูปโปรไฟล์"]` and the "dispatch .click() via evaluate, not page.mouse.click at center" trick for FB avatar buttons that have a child status-composer bubble overlapping their visual center.
- MISSING [browser-operator §Facebook] : account identity switching (personal ↔ Page) has no reliable text selector for the target account menu — the menu itself is reachable only via a DOM bounding-box scan for a `div[role=button]` in the top-right nav corner (viewport-relative, not screenshot-pixel-relative — the two are NOT the same scale on a CDP-attached real window and blind pixel-coordinate clicks land on the wrong element). · evidence: task-58bd4100, several failed `page.mouse.click` attempts on the "สลับ" identity-switch button before falling back to `getBoundingClientRect()`-driven clicks.
- MISSING [browser-operator §Facebook] : clicking anywhere near the top-right corner of a Facebook page while exploring can trigger unrelated toasts (e.g. "ซ่อนงานแล้ว" hiding a Jobs recommendation) with no visible modal warning and only a few seconds to undo. Recommend future operators verify exact element target via `getBoundingClientRect()` BEFORE any coordinate-based click in that region, not after. · evidence: task-58bd4100.
