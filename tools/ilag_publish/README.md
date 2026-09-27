# ILAG publish runners (winbox, Chrome on CDP 9224)

Zero-model scripts used on 2026-09-27 to finish and publish THE SHADOW BELOW while the CEO slept. Copy to
`C:\mooniex\ilag-runner\probe\` and run with `C:\mooniex\pwvenv\Scripts\python.exe` (`set PYTHONIOENCODING=utf-8`
first — the Thai Studio labels crash cp1252 stdout).

| Step | Script | Notes |
|---|---|---|
| Render | `render.cmd test|master|topview` | Glow LUT → ASS subs → TopView mark top-right incl. credits → credits appended; topview = ≤500 MiB copy |
| YouTube login | `yt_login_check.py`, `yt_switcher_check.py` | which channel Studio is on; which channels the account can switch to |
| Upload | `../yt_studio_upload.py --stop-before-publish` | video >50 MB goes in through CDP `DOM.setFileInputFiles` (Playwright refuses it over CDP) |
| Publish | `yt_publish_draft.py "<title part>" <channel> --publish` | the upload dialog's first Done left a DRAFT; this reopens "แก้ไขฉบับร่าง" and publishes; `yt_vis.py` reads the row |
| Language/category | `yt_set_lang.py <vid>` | Studio defaulted the video language to ไทย and category to เกม |
| Thumbnail A/B | `yt_ab_set.py <vid> A.jpg C.jpg --go` | "ภาพปกเท่านั้น"; the third slot's button was not reachable by script |
| Captions | `yt_subs_upload.py` | NOT working yet: the chooser takes the SRT but no editor/publish appears — upload by hand |
| TopView form | `tv_form_probe.py`, `tv_submit.py` (fill), `tv_finish.py --submit`, `tv_check_sub.py` | fields found by label; video via CDP file set; submit only after "Uploading..." clears |

If `connect_over_cdp` hangs with "ws connected", a stale tab is blocking the attach: list `/json/list` and close
leftovers with `/json/close/<id>`.
