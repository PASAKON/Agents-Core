# REPORT task-5f9b0d7a

## Summary
Set the Ghost Rules (@ghostrulestv, UCBhmXUsXrAFPXJJeyC4vcxQ) banner, profile picture, description and video watermark from `C:\Users\passg\ghostrules-kit\` in YouTube Studio and pressed Publish. The public page now shows the banner, avatar, handle and the first line of the description; name and handle are unchanged. $0 spent.

## What was set
- Banner: `banner_B_2560x1440.jpg`, default crop accepted ("เสร็จ"). Public page shows the "GHOST RULES / EVERY PLACE HAS A RULE" banner.
- Profile picture: `avatar_B_800x800.png`, default crop accepted. Public page shows the red eye and tally-marks avatar.
- Video watermark: `watermark_150.png`, display time = ตลอดทั้งวิดีโอ (entire video; the default was ตอนท้ายวิดีโอ). Studio read-back after a fresh load: that radio is checked and the watermark image is present.
- Description: `description.txt` pasted whole (EN + TH + hashtags). Studio read-back after a fresh load equals the file when trimmed (518 = 518 chars). Public page shows "Every place has a rule. Break it after midnight, and something answers." with "...เพิ่มเติม".
- Publish pressed once; Publish and Cancel then both went disabled (no pending changes).
- Not touched: name (Ghost Rules), handle, links, email, other channels, videos. No login typed. The existing Studio session on Chrome 9226 was already on the right account, and the deep link `studio.youtube.com/channel/UCBhmXUsXrAFPXJJeyC4vcxQ` opened the Ghost Rules dashboard directly, so no account switch was needed.

## Public page screenshot
`docs/reports/ghostrules-branding-20261111/public_page.png` (this branch), https://www.youtube.com/@ghostrulestv at 1280x720, taken signed in as the owner.

## Browser Actions
- route: step 3, raw CDP on the existing winbox Chrome 9226 (no API for channel branding, no existing script). Playwright `connect_over_cdp` timed out (known hang), so I wrote a small raw-CDP helper on Node's built-in WebSocket.
- Own tabs only: two, both closed (the first froze after Publish). Other tabs on 9226 untouched.
- PC lease: `pc_lease.py take` (status was FREE, Cookie Run not running), then `give-back` printed "lease released". `scripts/pc-lease.sh` does not work on winbox itself (it ssh's to `winbox`, which does not resolve there), so I ran `C:\mooniex\pclease\pc_lease.py` directly.
- screenshots: about 12, page about 929x881.

## Replay Script
- path: scripts/browser/ghostrules-branding.mjs (uses scripts/browser/cdp_raw.mjs)
- covers: open Studio profile, banner, avatar, description, watermark and display time, optional `--publish`
- brittle: `ytcp-banner-upload`, `ytcp-profile-image-upload`, `#textbox[contenteditable]`, `tp-yt-paper-radio-button`, Thai button labels (เสร็จ, อัปโหลด, เผยแพร่)

## Files Changed
- scripts/browser/cdp_raw.mjs: raw CDP client (new tab, eval, trusted click, file chooser answer, Input.insertText)
- scripts/browser/ghostrules-branding.mjs: replay script for the flow
- docs/reports/ghostrules-branding-20261111/public_page.png: public page screenshot
- REPORT.md

## Commits
- see `git log` on this branch

## Tests
- ran: `node --check` on both scripts
- passed: 2
- failed: 0
- skipped: 0 (the replay script itself was not run end-to-end, see risk)

## Issues / Blockers
- none blocking.

## Notes for Reviewer
- The channel has no videos, so the watermark cannot be seen on the public page; it was verified only as saved state in Studio.
- Banner crop: default crop accepted as instructed. On the public desktop page the title and both side panels sit inside the visible area.
- The first tab froze after Publish when I navigated it; a fresh tab read back fine.

## Not checked / risk
- The watermark was not seen rendering on a real video, and the banner was not checked on TV or mobile layouts, only the desktop public page. The replay script was assembled from steps run by hand and not run end-to-end; a Studio selector change would break it.

## Skill learning
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Files in and out] : `DOM.setFileInputFiles` needs forward-slash Windows paths (`C:/Users/...`). With backslashes the page got `NotReadableError` and Studio silently showed no crop dialog (only a console "Error {isTrusted:true}"). Probe: a throwaway `<input type=file>` then `file.arrayBuffer()` · evidence: task-5f9b0d7a
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Step order 2] : Playwright `connect_over_cdp` on winbox 9226 hangs after "ws connected" (second sighting after the 2026-10-28 note). Node 24 raw CDP (global WebSocket, `scripts/browser/cdp_raw.mjs`) works with no install · evidence: task-5f9b0d7a
- MISSING [ALL_Rules_Winbox_PCLease §Workflow] : on winbox itself `scripts/pc-lease.sh` fails (`ssh winbox` does not resolve); run `python C:\mooniex\pclease\pc_lease.py status|take|give-back` directly · evidence: task-5f9b0d7a
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Traps] : new Studio layout is Customization > Profile (banner, avatar, name, handle, description `#textbox[contenteditable]` + `Input.insertText`, watermark radios `tp-yt-paper-radio-button`, Publish `เผยแพร่`). Navigating the tab right after Publish froze its renderer (n=1); read back from a fresh tab · evidence: task-5f9b0d7a
