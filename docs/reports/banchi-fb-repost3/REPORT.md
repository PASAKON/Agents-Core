# Banchi FB Reel repost 3 — new clean Reel published, broken post deleted

Task: task-c6bd5ba6. Page: «ละครสั้นคุณธรรม by ILAG Studio» (asset_id `1319535331240503`).
CEO authorized delete + re-post on 2026-09-24 ("Ok delete … คุณทำแทนได้ไหม", "can you do it for me").

## Result

- **New Reel permalink:** https://www.facebook.com/reel/4560927164226012
- **Reel id:** `4560927164226012`
- **content_id (Business Suite):** `122116305555470545`
- **Published:** 25 กันยายน 6:41 (2026-09-25)
- **Status badge:** clean — **no** "เผยแพร่ไม่สำเร็จ" / "ไม่ได้บันทึกไว้อย่างถูกต้อง" (confirmed in Business Suite → Content → เผยแพร่แล้ว, after a fresh-tab reload)
- **Old broken post (content_id `122115848307470545`):** deleted (moved to Trash via FB's own "ย้ายไปที่ถังขยะ" confirm — Meta's own 30-day-recoverable delete flow, not a raw purge). Confirmed gone from Published after reload; only the new post remains.

## Caption check

Read back from the live Reel (`ดูเพิ่มเติม` expanded, `body.innerText`) — matches `docs/scripts/banchi-reels-caption.txt` verbatim, including all hashtags (`#ILAGStudio` etc.). The script's own caption compare (`captions_match`, paragraph-level, tolerates the known contenteditable doubled-blank-line quirk) also reported `True` on both the dry-run and the real run.

## Cover

Set successfully both runs (`cover set: True`) via the composer's "อัพโหลดภาพ" tab → nested upload button → `expect_file_chooser` → `set_files`. Confirmed visually in the dry-run screenshot (the correct cover-A artwork appears selected under "เลือกภาพขนาดย่อ").

## AI label

**No AI-content-disclosure control exists anywhere in this composer.** Checked on both the media step and the final step (including after expanding "การตั้งค่าการกระจายขั้นสูง" / advanced distribution settings — that section only has "อนุญาตการฝัง" / embedding, "อนุญาตให้เพจอื่นๆ โพสต์", "การติดตาม"). Live exploration and both real runs confirm this; the caption itself already discloses "(ละครสร้างด้วย AI)" in text. Task step 5 said "turn it on if there is one" — there isn't one on this account/composer version.

## Audience

Public ("สาธารณะ") — confirmed selected (blue-filled radio) on both dry-run and real-run screenshots, and explicitly re-clicked by the script every run to guarantee it regardless of default.

## A bug found and fixed mid-task (worth reading before reusing this script)

The first two "real" runs **silently published nothing** — `fb.publish()` returned normally, no error, but no post ever appeared anywhere in Business Suite (checked Published/Draft/Scheduled, all empty of the new post). Root cause: `_find_publish_button()`'s original selector (`button/[role=button]` with exact text "แชร์" and `width > 50`) matched the wizard's own **breadcrumb step-tab** ("สร้าง ‣ แก้ไข ‣ แชร์" at the top of the page) instead of the real footer publish button — the breadcrumb renders as a real, ~100px-wide `<button>` element and comes first in DOM order, so `.find()` picked it. Clicking a step tab you're already on is a no-op. Fixed by anchoring on the "ย้อนกลับ" (Back) button, which exists only once, as the real publish button's sibling in the footer — verified live before and after the fix (see commit `9a3d57fb`). No duplicate or partial post was ever created by the two failed attempts; nothing needed cleanup.

Also found live: `connect_over_cdp` needs `is_local=True` or Playwright refuses any file upload over 50MB ("Cannot transfer files larger than 50Mb to a browser not co-located with the server") — the 845MB video needs this. And: connecting when the browser context has **zero** open tabs throws `Browser context management is not supported` — always leave at least one tab open (`final_cleanup.py` leaves a blank one).

## Screenshots

1. `dry-run-final.png` — final step of the `--dry-run`, real video/cover/caption/audience all set, publish button never clicked.
2. `delete-confirm-dialog.png` — FB's own "ย้ายโพสต์ไปที่ถังขยะ" (move to Trash) confirm dialog, opened on the OLD post row only (confirmed via its "เผยแพร่ไม่สำเร็จ" badge position before clicking).
3. `published-list-after-delete.png` — Business Suite → Content → เผยแพร่แล้ว, reloaded fresh: only the one new, healthy post remains.
4. `live-reel-caption-expanded.png` — the live public Reel at facebook.com/reel/4560927164226012, playing, full caption expanded.

## Script dry-run output (`dry-run.log`, second attempt — first hit the 50MB co-location bug, fixed before this run)

```
composer opened; Page name shown: '​'
upload_video: 100% confirmed, snippet='จุดจบของเจ้าหนี้นอกระบบ-FINAL.mp4\n1080 x 1920\n100%\nลบ\n​\nเพิ่มวิดีโอ\nเพิ่มรูปภาพ\n'
caption readback matches: True
cover set: True
AI label: no AI-content-disclosure control found in this composer
audience set to Public: True
screenshot saved: docs/reports/banchi-fb-repost3/dry-run-final.png
DRY RUN — stopping before publish, as contracted.
```

## Script real-run output (`real-run-2.log` — the run that actually worked, after the publish-button fix)

```
composer opened; Page name shown: '​'
upload_video: 100% confirmed, snippet='จุดจบของเจ้าหนี้นอกระบบ-FINAL.mp4\n1080 x 1920\n100%\nลบ\n​\nเพิ่มวิดีโอ\nเพิ่มรูปภาพ\n'
caption readback matches: True
cover set: True
AI label: no AI-content-disclosure control found in this composer
audience set to Public: True
screenshot saved: docs/reports/banchi-fb-repost3/real-run-2-final.png
PUBLISHED — clicked the real 'แชร์' button exactly once.
post-publish URL: https://business.facebook.com/latest/reels_composer/?ref=biz_web_home_create_reel&asset_id=1319535331240503
reel_id (best-effort): None
anchors seen: []
This is a best-effort capture, not the verification the task requires.
Verify manually in Business Suite → Content before deleting the old post:
  status must read เผยแพร่แล้ว with no ไม่สำเร็จ / ไม่ได้บันทึกไว้อย่างถูกต้อง
```

Note: `capture_post_publish_link()` (best-effort, in-script) found nothing — FB keeps you on the composer page after publish with no visible URL/anchor change, instead showing a "กำลังประมวลผลคลิป Reels" (Processing) modal for a video this long (24:01), and the post only appears in Business Suite ~5 minutes later once processing finishes. The script prints this honestly as "best-effort, not the verification the task requires" rather than claiming success from it — the actual permalink/reel id above was obtained by manual verification afterward (Business Suite → Content → row menu → "คัดลอก ID คลิป Reels", then confirmed by opening the live reel URL directly), which is the real step-7 verification the task asked for. First real-run attempt (`real-run.log`) is the pre-fix run that silently published nothing — kept for the record, superseded by `real-run-2.log`.

## Replay script

`tools/fb_reel_post.py` — does steps 1-6 (open composer, confirm Page name, upload video via file-chooser interception, set caption with read-back compare, set cover, check/toggle AI label, ensure Public audience, `--dry-run` stops here) and the publish click (real footer "แชร์" button exactly once, best-effort post-publish URL capture). It does **not** do the full step-7 Business Suite verification (status badge check, live-reel caption re-read) or step 9 (delete) — those need the id, which the composer itself never surfaces, so they were done as separate one-off, read-only-until-confirmed scripts this run (not checked in — the whole point of `tools/fb_reel_post.py` is the *creation* half, which needs no human judgement; the *replace-and-verify* half genuinely needs a human/model to look at a status badge and decide "is this the right row" before deleting anything, which is exactly the judgement call this org's rules say should not be blindly scripted).

```
python3 tools/check_replay_script.py tools/fb_reel_post.py   # -> ok
pytest tests/test_fb_reel_post.py                            # -> 10 passed
```

## Follow-up for next episode

`tools/fb_reel_post.py` reliably does the create-and-publish half end to end now (bug fixed, verified live twice). What it's still missing for a fully hands-off run: (1) a step-7 verifier that navigates Business Suite Content, finds the newest row's status badge and reads it back programmatically instead of a human eyeballing a screenshot; (2) a `--delete-content-id` flag that does the "..." → จัดการโพสต์ → ลบโพสต์ → ย้ายไปที่ถังขยะ flow this report did by hand. Both are straightforward given the selectors this run discovered (`get_by_text("เปิดดรอปดาวน์")`, `"จัดการโพสต์"` hover, `"ลบโพสต์"`, confirm text `"ย้ายไปที่ถังขยะ"`) — left out of this pass to keep the delete step under direct human/model judgement per the task's own "if there is any failure state, STOP" instruction, rather than trusting a script to self-certify success on a post it just created.
