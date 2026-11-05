# REPORT task-0c40e116

## Summary
Channel is renamed to **365 to Survive** (@365tosurvive, handle was free), watermark replaced, video title and the 5 localized titles updated, and the video is **PUBLIC** (plays logged out). **Not done: the new cover thumbnail**. YouTube asks for phone-number verification before a custom thumbnail can be added, which I cannot do (OTP). The public thumbnail is still the auto-picked video frame.

## Results
- **Public URL:** https://youtu.be/fuwKC8xjUFc  (logged-out curl: playabilityStatus OK, isUnlisted false; title tag "365 to Survive | Day 0: Flash Flood Alert at 3 AM - YouTube"; oEmbed 200, author "365 to Survive")
- **New handle:** @365tosurvive (first choice, green check, no fallback needed). https://www.youtube.com/@365tosurvive returns 200, canonical channel URL on the watch page is /@365tosurvive. Channel name "365 to Survive".
- **Channel description:** left as is (no "Survive 365" in it).
- **Watermark:** replaced with watermark-150x150.png, published, persisted after reload (screenshot 07). Display time unchanged (end of video).
- **Video title:** "365 to Survive | Day 0: Flash Flood Alert at 3 AM", saved.
- **Localized titles th/es/pt-BR/hi/id:** all five set to POST-KIT.md TITLE lines and published; I reopened each row after reload and read the saved title back, all match. Descriptions untouched (they already equal POST-KIT: 2154/2409/2388/2299/2379 chars).
- **Visibility:** Public, premiere box unchecked, saved ("บันทึกการเปลี่ยนแปลงแล้ว", Studio shows "สาธารณะ").
- **Screenshots:** C:\mooniex\shots\khaohom-ep01b\ (24 png + public-thumb-maxres.jpg), copied to Contabo /opt/MoonieXHQ/Work/khaohom-survival/long/ep01/intl/shots/ (25 files). Not in git.

## Files Changed
- scripts/browser/khaohom_rename/*.py — replay scripts (Playwright over CDP :9224) for name/handle, watermark, video title, localized titles, visibility
- scripts/browser/khaohom_ep01/* — restored from the task-62430afa branch for reference (unchanged)
- REPORT.md

## Commits
- see git log on branch

## Tests
- ran: none (browser task)
- passed: 0
- failed: 0
- skipped: 0

## Issues / Blockers
- **Thumbnail NOT set.** Clicking "อัปโหลดไฟล์" under ภาพปก opens "ปลดล็อกฟีเจอร์อื่นๆ บน YouTube: คุณต้องยืนยันหมายเลขโทรศัพท์ก่อนจึงจะเพิ่มภาพปกวิดีโอที่ทำเองได้" with a ยืนยัน button. I cancelled it. Earlier `input[type=file].set_input_files` + Save also silently did nothing (Studio said saved, no custom thumbnail). Needs the CEO to verify a phone number on the channel's Google account (a relay/card request), then upload cover-1280x720.png (Contabo .../intl/postkit/). Until then viewers see an auto frame (Jasmine in the supermarket, "DAY 0 / 365" HUD), not the cover.
- No org MCP on this box: I could not send the letter to CMO or cc project_head-b2ff34d1. The CTO/hub needs to relay this report to them.
- Chrome-in-Chrome extension not used; I drove the :9224 automation Chrome with Playwright (same route as task-62430afa), my own tab only, closed at the end.

## Notes for Reviewer
- PC lease taken 05:47 and given back (status FREE, Cookie Run idle throughout, untouched). terminal64/MT5 untouched, no reboot.
- Winbox copies deleted: C:\mooniex\khaohom-ep01b (37 files, ~9.4 MB: POST-KIT.md, cover, watermark, html dumps, scripts) — files were mine, created this session; scripts and shots kept elsewhere.
- Heads-up: the video's EN description and tags still contain "survive 365" (tags line in POST-KIT.md: "survive 365, ..."), fine as a keyword, but the existing channel "Survive 365" (@Survive365Days) from task-62430afa still exists.
- Channel name/handle changes are limited to 2 per 14 days; both used 1.
- Studio localized-title selectors: row opened by hover + mouse click at (677, row y); dialog close button is "ยกเลิก" (not "ปิด") when unchanged.

## Not checked / risk
- Did not verify the localized titles from a logged-out viewer in each language (curl with Accept-Language returned the English title for all, so the per-language display is only confirmed through Studio read-back).
- Thumbnail still auto-frame; if the CEO wants the cover live, the verification step is a blocker I could not clear. The old handle @khaohomsurvival is reserved by YouTube for 14 days, old links may redirect.

## Skill learning
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Traps (YouTube Studio)] : custom thumbnail upload requires phone verification on this channel; Studio shows "saved" after set_input_files with no thumbnail applied, so verify via https://i.ytimg.com/vi/<id>/maxresdefault.jpg · evidence: task-0c40e116, shots/18-thumb-help.png
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Traps (YouTube Studio)] : channel name + handle + watermark are all on Customization > Profile (/channel/<UC>/editing/profile), watermark file input index 2 then "เสร็จ" then top "เผยแพร่"; Visibility = click current state text, radio tp-yt-paper-radio-button[name=PUBLIC] in the SAME script (dropdown closes when the script exits), "เสร็จสิ้น", then #save · evidence: scripts/browser/khaohom_rename/
- COSTLY [no owner] : Playwright default 30s timeouts on invisible elements printed ~60 retry lines each (twice) · prevented by: pg.set_default_timeout(5000) at the top of every script and `| tail -5`
