# ILAG publish runners (winbox, Chrome on CDP 9224)

Zero-model scripts used on 2026-09-27 to finish and publish THE SHADOW BELOW while the CEO slept. Copy to
`C:\mooniex\ilag-runner\probe\` and run with `C:\mooniex\pwvenv\Scripts\python.exe` (`set PYTHONIOENCODING=utf-8`
first — the Thai Studio labels crash cp1252 stdout).

| Step | Script | Notes |
|---|---|---|
| Render | `render.cmd test|master|topview` (v1) · `master2|topview2` (v2) | Glow LUT → ASS subs → TopView mark top-right. v1 appended our credits roll — WRONG for this film: the editor's cut already ended with its own roll + music, so v1 showed the credits twice. **Look at the cut's last minute before appending anything.** v2 = the cut alone, frame-exact (8274 frames) |
| YouTube login | `yt_login_check.py`, `yt_switcher_check.py` | which channel Studio is on; which channels the account can switch to |
| Upload | `../yt_studio_upload.py --stop-before-publish` | video >50 MB goes in through CDP `DOM.setFileInputFiles` (Playwright refuses it over CDP) |
| Publish | `yt_publish_draft.py "<title part>" <channel> --publish` | the upload dialog's first Done left a DRAFT; this reopens "แก้ไขฉบับร่าง" and publishes; `yt_vis.py` reads the row |
| Language/category | `yt_set_lang.py <vid>` | Studio defaulted the video language to ไทย and category to เกม |
| Thumbnail A/B | `yt_ab_set.py <vid> C.jpg D.jpg [--replace] --go` | "ภาพปกเท่านั้น"; **slot 1 is pre-filled with the current thumbnail** — pass only the other two (passing A again gave A/C/A). `--replace` accepts "การทดสอบใหม่" over a running test; `--go` refuses unless 3 slots = current + the uploads. Verify with `yt_ab_probe.py` (prints each variant's ytimg URL; match them to the files by pixels) |
| Captions | `yt_subs_upload.py` | NOT working yet: the chooser takes the SRT but no editor/publish appears — upload by hand |
| Trim a published video | `yt_trim_end.py <vid> <start m:ss:ff> <end m:ss:ff> [--save [--confirm]]` | Studio editor, keeps URL/views/A/B test. Boxes are m:ss:**frames**, typed WITH colons (a bare number is seconds); order = cut start, cut end, playhead; the confirm dialog's `#apply-button` stays disabled until `#confirm-checkbox` is ticked; permanent. `yt_edit_status.py` looks for the processing notice |
| TopView: replace the video | `tv_edit_video.py [--video F.mp4 [--go]]` | My submissions → Edit (inline form). Removes the old file (the X beside its name), sets the new one by CDP, waits for the upload, saves only if the form shows only the new file and every text field is unchanged |
| TopView form | `tv_form_probe.py`, `tv_submit.py` (fill), `tv_finish.py --submit`, `tv_check_sub.py` | fields found by label; video via CDP file set; submit only after "Uploading..." clears |

If `connect_over_cdp` hangs with "ws connected", a stale tab is blocking the attach: list `/json/list` and close
leftovers with `/json/close/<id>`.
