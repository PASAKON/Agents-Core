# task-1984898f: Ghost Rules EP3 + EP4 scheduled (14 Nov 2026)

## Result (read back from Studio after a reload, winbox Chrome :9226, channel Ghost Rules UCBhmXUsXrAFPXJJeyC4vcxQ)

| | video id | visibility | scheduled (Asia/Bangkok, browser tz checked) | title | cover |
|---|---|---|---|---|---|
| EP3 | K1djkamjxJE | กำหนดเวลาไว้ (scheduled) | Sat 14 Nov 2026 19:00 | หอพักห้องมุมชั้นสี่ กับกฎในตู้เสื้อผ้า \| Ghost Rules | already an A/B test of 3 custom covers (custom_1..3), left as is, see below |
| EP4 | fvqG_zzrN6U | กำหนดเวลาไว้ (scheduled) | Mon 16 Nov 2026 19:00 | บ้านไม้ใต้ถุนสูง กับกฎสี่ข้อห้ามเปิดหน้าต่างครัว \| Ghost Rules | custom cover ghostrules_ep04_cover.jpg (visible in the edit page) |

Content list (yt_list.py) after both saves: `K1djkamjxJE กำหนดเวลาไว้ 14 พ.ย. 2026`, `fvqG_zzrN6U กำหนดเวลาไว้ 16 พ.ย. 2026`.
Visibility dialog reopened after a reload: date 14 พ.ย. 2026 / time 19:00 (EP3) and 16 พ.ย. 2026 / time 19:00 (EP4).
EP4: kids = NOT_MFK, altered content = YES, 12 tag chips, title + description 567 chars read back equal to the TH files.

## EP3 cover: left as it was
ep03/thumbs has 4 candidates (v1/1..4.jpg) and nothing names one as approved. Studio already holds a saved 3-cover A/B test
(thumbnails custom_1, custom_2, custom_3; screenshot Work/ghostrules-full/ab_K1djkamjxJE_3saved.jpg, 13 Nov). I did not replace it.
If the CMO wants one fixed cover instead, that is a one-line follow-up.

## Drive first (md5)
Both files uploaded to ALL DRAFT/YT: Ghost Rules/EP04 (existing folder 1e60fTB95BAbZxgezqIzNPpCdbRc0qF-x, no folder created), md5 read back by id:
- ghostrules_ep04_full_1080p_v3.mp4  id 140QaqWVTW8V5-IJlMciI89iMo9WZOYM0  md5 3f7fb90423deb73d7a7d802b2157564e  MATCH
- ghostrules_ep04_cover.jpg          id 1_jI3MTDiOpCAQaxBYlIrzg9YK4olVndE  md5 38cdd9d5b32750af39073b6bbab320ef  MATCH
Then `rclone copy` Drive -> winbox C:\mooniex\ghostrules\ep04 (577 MiB, 10 s); winbox md5 equal. After Studio took the upload,
the two winbox copies (files I made) and the empty folder were deleted. Contabo originals in Work/task-0ef63967 and Work/task-b24809a4 are untouched.
winbox RAM: 0.76 GB available at the first check (a game was open), 4.7 GB at transfer time, 3.5 GB before the upload; disk 71 GB free.

## Files
- /opt/MoonieXHQ/Work/ghostrules-full/ep04/publish/TH/{title,description,tags}.txt (no « », no em dash, no episode number; links back to EP3 youtu.be/K1djkamjxJE)
- Screenshots (Work/ghostrules-full/):
  - ep03/publish/sched_dry_2_dialog_filled.png, sched_dry_3_form_before_save.png, sched_real_2/3/4*.png, sched_readback_dialog.png
  - ep04/publish/upload_gr04_5_filled.png, _6_private.png, _7_saved.png, upload_gr04.json, ep4_probe_before_schedule.png,
    sched_dry_*.png, sched_real_*.png, sched_readback_dialog.png, list_after_upload.png, list_final.png

## Traps met
1. Studio's active channel on :9226 was Jade Tally, not Ghost Rules: the EP3 edit URL answered "อ๊ะ มีบางอย่างผิดปกติ". Switched through youtube.com/channel_switcher (the channel row in ytd-account-item-renderer), did the work, then switched back to Jade Tally so the browser is as I found it.
2. Schedule dialog (Thai Studio): the typed date shows in the popup input but Enter does not commit it; click the day cell with real Input.dispatchMouseEvent (element.click() does nothing). Time: insertText "19:00" then Tab; Enter alone leaves the Done button disabled. Date format is "14 พ.ย. 2026" (Gregorian year).
3. The visibility box says only "กำหนดเวลาไว้" after saving, with no date: read the date from the reopened dialog (yt_readback.py) or the content list.
4. The upload wizard shows no video url at the first read (None); take the id from the content list after the upload (duration 15:34 matched EP4).

## Replay scripts (scripts/browser/)
ghostrules_yt_upload.py, ghostrules_yt_schedule.py, ghostrules_yt_readback.py, ghostrules_yt_list.py. They import /opt/MoonieXHQ/Work/cn-series/publish/cdp_raw.py
(raw CDP, own background tab) and need the tunnel `ssh -fN -L 19226:127.0.0.1:9226 winbox`; run with Agents/Core/.venv/bin/python.

## Not checked / risk
- The 19:00 publishes have not happened yet. I read back only what Studio stored; whether the video is public at 19:00 is YouTube's act.
- EP3 is scheduled while its A/B cover test is attached; I did not check how Studio starts the test on a scheduled video.
- EP4 processing / copyright checks were still "กำลังตรวจสอบ" at upload time and were not re-read afterwards; a failed check before 16 Nov 19:00 would block the publish.
- Active channel was switched Jade Tally -> Ghost Rules -> Jade Tally on the shared :9226 Chrome; a CnDrama job running in that window might have noticed. No other Studio tab was open at the time.
- The stale EP1 Studio tab (3H-aUIsUIu4) and other tabs in that Chrome were not mine and were left alone.
