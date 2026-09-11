# Festival Meta Assets — Watermark + Packshot Download (task-8e6ef54d)

Download-only run against the "Meta assets" sidebar item in both festival
submission projects. Zero Generate/Rerun/Recreate clicks. No filing to
Google Drive (per task scope — filing belongs to the requester).

## Projects

| Film | Project URL | Meta assets folder |
|---|---|---|
| «Sorry, Sir» (SORRY SIR — The Valder Collection) | `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` | "Watermarks" (4 assets) |
| «Do Not Disturb» (DO NOT DISTURB) | `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival` | "Watermarks" (4 assets) |

Both project slugs re-verified against the address bar before every action
(`ai-film-festival-3` vs `ai-film-festival` — the one-character difference the
brief warned about). Window held at 1920x911 throughout (>=1280 required).

**Every asset offered under "Meta assets" was downloaded — exactly 4 per
project, no more, no fewer. Nothing was missing in either project**: one
watermark PNG + one packshot MOV per aspect ratio, 16:9 and 21:9, matching the
brief's expectation exactly. No substitutions were needed.

## File report

| Project | Asset name (platform filename) | Aspect | Saved as | Size (bytes, on disk) | MD5 | What it is |
|---|---|---|---|---|---|---|
| Sorry, Sir | higgsfield_watermark_16_9.png | 16:9 | `C:\mooniex\meta-sorrysir\higgsfield_watermark_16_9.png` | 43,739 | `889a00c32a75f135b1fad9d0972c03a7` | Still image. Transparent PNG (RGBA, alpha 0–255), 1920x1080. "Higgsfield Global Film Festival" laurel logo lockup on transparent background. |
| Sorry, Sir | higgsfield_watermark_21_9.png | 21:9 | `C:\mooniex\meta-sorrysir\higgsfield_watermark_21_9.png` | 46,676 | `a4410a330debfb953e6bee8e77adfa9e` | Still image. Transparent PNG (RGBA, alpha 0–255), 2560x1080. Same logo lockup, wide-canvas crop. |
| Sorry, Sir | higgsfield_packshot_16_9.mov | 16:9 | `C:\mooniex\meta-sorrysir\higgsfield_packshot_16_9.mov` | 1,130,494,068 | `87ac31353e5ce50a2a3c435ffa17a68c` | Video sting, **9.13 s** (9.133333s / 30fps), 3840x2160 4K. ProRes 4444 with **alpha channel** (`yuva444p12le` — transparent, not baked onto black), plus one PCM audio track. |
| Sorry, Sir | higgsfield_packshot_21_9.mov | 21:9 | `C:\mooniex\meta-sorrysir\higgsfield_packshot_21_9.mov` | 916,697,076 | `0adc33a98f4a0579464d48902fc6f032` | Video sting, **9.13 s**, 3840x1646 (21:9 crop of 4K), ProRes 4444 alpha, PCM audio track. |
| Do Not Disturb | higgsfield_watermark_16_9.png | 16:9 | `C:\mooniex\meta-dnd\higgsfield_watermark_16_9.png` | 42,704 | `3a3ad30fc4fbcf4d18283ba515811ff5` | Still image. Transparent PNG (RGBA, alpha 0–255), 1920x1080. Same laurel logo lockup. |
| Do Not Disturb | higgsfield_watermark_21_9.png | 21:9 | `C:\mooniex\meta-dnd\higgsfield_watermark_21_9.png` | 46,060 | `7186676519850ebf79294da5ba5ee5e7` | Still image. Transparent PNG (RGBA, alpha 0–255), 2560x1080. |
| Do Not Disturb | higgsfield_packshot_16_9.mov | 16:9 | `C:\mooniex\meta-dnd\higgsfield_packshot_16_9.mov` | 1,130,494,068 | `87ac31353e5ce50a2a3c435ffa17a68c` | Video sting, 9.13 s, 3840x2160, ProRes 4444 alpha, PCM audio. **Byte-identical to Sorry, Sir's copy** (see note below). |
| Do Not Disturb | higgsfield_packshot_21_9.mov | 21:9 | `C:\mooniex\meta-dnd\higgsfield_packshot_21_9.mov` | 916,697,076 | `0adc33a98f4a0579464d48902fc6f032` | Video sting, 9.13 s, 3840x1646, ProRes 4444 alpha, PCM audio. **Byte-identical to Sorry, Sir's copy.** |

### Note — the packshot .mov files are identical across both projects; the watermark .png files are not

The two `.mov` packshots (16:9 and 21:9) came back with **matching MD5s and
matching byte counts** between the two projects — confirmed by an independent
`md5sum` run reading all four files side by side. This is almost certainly
intentional: the packshot is Higgsfield's own generic festival bumper, not
something rendered per-film, so both submission projects were seeded with the
same file.

The `.png` watermarks are **not** identical between projects — different MD5s
and slightly different byte counts (Sorry, Sir: 43,739 / 46,676 bytes;
DND: 42,704 / 46,060 bytes) despite being visually the same laurel logo at the
same pixel dimensions (1920x1080 / 2560x1080). Each project's asset-detail
panel also reported a different "Uploaded" timestamp for its watermark PNGs
(Sorry, Sir: 17.08.2026, 09:35; DND: 25.08.2026, 07:29) and for its packshot
MOVs (Sorry, Sir: 01.09.2026 / 21.08.2026; DND: 01.09.2026 / 21.08.2026,
different minute). So the PNGs were uploaded separately per project even
though they render the same, and the MOVs were very likely uploaded from the
same source file twice. Not investigated further — outside this task's scope,
flagging in case it matters for eligibility auditing later.

## Usage-instruction text on the platform (verbatim)

The **only** rule text found anywhere in either project — checked the Meta
assets/Watermarks page itself (no instructions there) and the project's
"Festival rules" page (the festival's Official Rules, reproduced in full
inside the Cinema Studio project) — is this one line, identical in both
projects since both point at the same festival rules document:

> **Watermark**
> "The official Higgsfield watermark and packshot are available inside your
> submission project. They must appear on your final video and on the
> version you post to social media."

That is the entire instruction. **Nothing else was found anywhere on the
platform about *where* the watermark must sit on frame, *how long* the
packshot must stay on screen, sequencing (start vs. end), or any other
placement/timing rule.** Adjacent context from the same Festival Rules
document, for completeness (this is *not* a watermark placement rule, just
the surrounding submission requirement it sits inside):

> **Minimal Viable Submission (MVS)** — "Final video — with the official
> Higgsfield watermark and packshot." / "Social media post — a valid public
> link ... showing your final film with watermark and packshot intact."
> "Any Entry missing an MVS component will be marked incomplete."

No other section of the Official Rules (Definitions, Eligibility, Format,
Film Requirements, Prohibited Content, Prize Pool, Judging, Verification,
Rights, Warranties, Disputes, Platform Availability, Schedule Changes,
Privacy, Limitation of Liability, General Legal) mentions the watermark or
packshot again.

## Browser actions

- `route: step 3 (tabs) — no API for this, no existing meta-assets replay
  script; task needs downloading via a UI panel`
- Browser: winbox-chrome (`815ddf16-…`), selected directly from
  `config/hosts.yaml` — no `list_connected_browsers` round-trip needed.
- One tab, opened via `tabs_create_mcp`, claimed in `tab_registry.py`,
  released (`done`) and closed at the end. Never touched another operator's
  tab.
- Window verified at 1920x911 (`resize_window(1600,1000)` request, actual
  OS-honoured size larger — read back via `javascript_tool`, not trusted from
  the resize call's return value).
- 8 total downloads via each asset's detail-panel "Download" button (never
  the composer, never a References/upload panel). Zero Generate, zero Rerun,
  zero Recreate — confirmed by never opening the video/image composer tab at
  the bottom of the page.
- One `CDP sendCommand Page.captureScreenshot` timeout hit mid-session on the
  DND project (after closing a "3 days left" deadline-reminder modal, before
  any Generate-adjacent control was on screen). Per the higgsfield-unlimited-
  gen skill's error-handling rule, treated as "check state, don't assume
  nothing happened" — retried the screenshot immediately (succeeded), then
  re-verified by screenshot that the click landed on the intended sidebar
  item rather than assuming success. It had not (see below) — caught by
  re-reading state, not by luck.
- One misclick: an intended "Meta assets" click landed on "Settings"
  instead — DND project's sidebar entries render at very slightly different
  y-offsets than Sorry, Sir's (an artifact of the deadline-modal
  layout-shift right before that click). Caught immediately from the
  resulting screenshot (breadcrumb read "Settings" not "All / Watermarks"),
  corrected with one more click, no side effects (Settings is a read-only
  landing tab, nothing was changed on it).
- Screenshots taken: 11. Zoom calls: 0 (the asset-detail side panel's text
  was read directly from screenshots since it was already small/isolated
  text, not worth a separate javascript_tool round-trip for 4x2 fields).
- No replay script written. This flow is unlikely to repeat (one-time asset
  harvest for festival submission prep) and is simple enough (open Meta
  assets → click each tile → Download) that a script would not have paid for
  itself relative to a ~15-minute manual run. `none` — one-off harvest, low
  value to automate.

## MACHINE-LOCK.txt

Was empty at start (per brief expectation). Wrote `task-8e6ef54d` in for the
duration, cleared it back to empty at the end.
