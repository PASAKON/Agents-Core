# S2S-Fix1 — A HUNDRED MILLION — 2026-09-08, task-23004a8b

STATUS: NO TAKE 3 FIRED. CTO issued a mid-task change of plan: the "take 2"
withheld earlier tonight (card `ad847559`, Created 20:56) was a misidentified
S2S-B card, not S2S's. S2S's real take 2 (fired 20:22, never reviewed) was
found, reviewed, PASSED item 1, and filed as the take. Take 3 was never
generated — no browser slot spent, no Unlimited generation used.

## Timeline of the mid-task pivot

1. Task assigned: fire S2S take 3, WITH the previz, on Unlimited.
2. Pre-flight gates run clean (see below) and the video composer was fully
   staged — Seedance 2.5, Unlimited ON (`UNLIMITED · ~~140~~ · 0` confirmed),
   20s/720p/16:9/High/Sound On all set, `docs/S2S-Render.MP4` uploaded to the
   references panel (4159 KB reported, matching `ls -l` 4,259,236 bytes).
   Before the Generate click, the Chrome tab hit a sustained rendering fault
   (`Page.captureScreenshot` timing out repeatedly, viewport briefly reporting
   784×380 against an 1440 outer width — consistent with the skill's "a
   window can shrink on its own" failure mode) and was abandoned per that
   HARD rule: closed, released from `tab_registry.py`, fresh tab opened.
3. Before re-staging the composer, the CTO sent a correction: asset
   `ad847559` (the card the 22:56 log entry reviewed and found FAILING item
   1) actually belongs to **S2S-B**, not S2S — Higgsfield's Created time is
   the fire time, and 20:56 does not match S2S's own fire at 20:22. S2S's
   real take 2 had never been looked at.
4. Per the CTO's explicit branch instruction: locate and review the real
   card FIRST; only fire take 3 if it fails or is missing.
5. Real card found (see Identification below), reviewed, **PASSED item 1**
   → per instruction, take 3 was NOT fired. The real take-2 clip was
   uploaded to Drive `Fix-2` as `S2S-Fix1.MP4` instead.

## Pre-flight (run before the pivot, all against the flattened paste block)

- `git log` already at/past `a12dc16` ("the previz carries camera distance").
- `grep -c 'reference video' <sheet>` = 3 (>0, previz required confirmed).
- Depth gate (extreme foreground/very front/floating/toward the mark/backs to
  the room/nearest+crack-mark-star-plaque), flattened: 0 matches.
- Black-suit flattened: only hit is the bodyguard's "all-black suit, black
  shirt and tie" — no registrar/gold-V collision.
- `SHE WEARS EXACTLY WHAT HER PICTURE SHOWS` count in the paste block: 1
  (other hits in the file are TAKE LOG notes, outside the paste block).
- `thibault` count in the paste block: 0 (all 4 whole-file hits are in the
  NOTES/TAKE LOG sections, never pasted).
- `prompt-lint.py` exit 0; 14/14 unique `@` chip mentions in the paste block,
  matching the task's "14 chips" requirement exactly.
- `docs/S2S-Render.MP4`: 1280×720, 20.0s, `ls -l` byte count 4,259,236 —
  recorded before upload.

## Identification of the real S2S take-2 card

Higgsfield's "Sence 1/2/3" project folders turned out to belong to an
**unrelated production** sharing the same `ilag-studio` account (WW2-era
newsroom/military imagery) — not this film's scene numbering. Abandoned that
path and worked from the project's flat "All assets" grid instead, filtered
to `Filter → Date range → Today`.

Opened candidate video cards via each card's own `... → Open` (never
`Rerun`), reading the Info panel's Created timestamp + prompt text:

- First candidates checked (Created 9:29 PM, 5:56 PM) were unrelated scenes
  — a wheelchair-adjacent camera-move shot and an 8s three-shot plaque scene,
  neither matching S2S's "ONE LOCKED SHOT... never moves" spec.
- Card **uuid `00b1bf9e-784d-4075-90c2-3f95755579f3`**, Info panel Created
  **"September 8, 2026 at 8:22 PM"** — exact match to the 20:22 ICT fire
  time recorded in this sheet's own take-2-fired log entry.
- Prompt text (via "See all"): *"20s · 720p · 16:9 · ONE LOCKED SHOT. The
  camera never moves, never pans, never zooms, no cuts, for the whole twenty
  seconds... the reference video (Video 1) is the CAMERA AND BLOCKING
  REFERENCE for this shot — a 20-second grey previz of this exact scene.
  Every grey block is a prop, never a person."* — word-for-word match to
  this sheet's paste block. (S2S-B's own sheet instead opens "IN THE NEAR
  FOREGROUND... A VERY OLD WOMAN SITS IN A POWERED WHEELCHAIR", confirming
  this card is NOT S2S-B.)
- Downloaded via the card's own Download button:
  `hf_20260908_132206_ec15173c-7890-495d-8b43-fec65e8a06ec.mp4`. Filename
  timestamp `132206` = 13:22:06 UTC = 20:22:06 ICT, matching the fire time a
  second, independent way.
- `md5`: `0c4f71b1f309a22528d6298cc4091bfe` — checked against every other
  `.mp4` already in `~/Downloads` (including the S2S-B card's
  `ad847559...` file, md5 `f330cc82...`) — unique, genuinely a different
  render.
- `ffprobe`: h264 1280×720 + aac, duration 20.041667s — spec matches exactly
  (20s / 720p / Seedance 2.5).

## Frame review — REVIEW ORDER

Frames extracted to `docs/reports/frames-s2s-t2-real/` at 0.5s, 4s, 8s, 12s,
16s, 17.0s/17.25s/17.5s (spike check), 19s, 19.5s.

1. **SHE NEVER ARRIVES — PASS (the CTO's explicit gate for this branch).**
   Not visible at 0.5s (room still facing camera). Visible tiny at the red
   double door by 4s (room already turned). At 8s her figure spans roughly
   y376–y457 of the 720px-tall frame (~11% of frame height), centred at the
   far red door. At 19s she is at essentially the same size and position
   (~11%, same spot) — no appreciable approach across 11 seconds of clip.
   Matches take 1's original passing criterion exactly, and is the opposite
   of what the mistaken S2S-B review found (camera co-located with her,
   filling the foreground).
2. **Voice before visible, room turns at once — PASS.** RMS waveform (0.1s
   windows) shows a clear vocal spike 0.8–2.0s (peak ~2800 vs a ~250
   baseline), before she is visible in any sampled frame (first appears
   ~3–4s). The 0.5s frame shows the whole cast still facing camera; by 4s
   everyone visible has turned away — consistent with one simultaneous turn
   around 3s. Exact line not transcribed (no ASR tool available in this
   environment); timing matches the script's `[1s]` cue.
3. **Two leave past the lens — PARTIAL.** The art student (acid
   yellow-green curly hair) is present and walking toward camera at 16s,
   fills/blurs the frame passing near the lens at 17.0–17.25s (this is the
   sweep's one large spike, see item 7), and is gone from the group by 19s
   — confirmed exit. The second scripted exit (the woman in tawny/rust fur,
   rightmost in frame) remained visible in every sampled frame through
   19.5s; her exit was not captured in this sample set and is unconfirmed
   (not denied — she may leave in the final ~0.5s, or between samples).
4. **Real powered wheelchair, no attendant — PASS.** Chromium tubular frame
   visible, no attendant/nurse/pusher beside her, at both 8s and 19s.
5. **One line of dialogue — consistent, not word-verified.** Single early
   vocal spike (0.8–2.0s, see item 2); no ASR tool available to transcribe.
6. **Thirteen people, no extras — consistent by count** at 4s/8s/12s:
   gentleman (Carrington), registrar, bodyguard, Valder, two guards, woman
   in cobalt/blue, woman in magenta fur, woman in green, woman in tawny fur,
   Dupe + cart, art student, grandmother = 13, no unidentified extras.
7. **Camera dead still — PASS.** 0.2s-equivalent sweep (source is 24fps, so
   used a 6-frame/0.25s stride, 80 steps): median luma-diff step 0.587, one
   spike at step 68 (~17.25s) of 11.165 (19.0x median) — nominally over the
   15x/median cut heuristic. Frames either side of the spike (17.0s, 17.25s,
   17.5s) show identical background/column/red-door geometry with the art
   student's own blurred body filling most of the frame passing the lens —
   a near-lens walker producing a large luma delta, not a camera cut. Camera
   lock holds throughout.

Wardrobe: grandmother's headscarf/cardigan read grey throughout (face
partially visible at 8s/12s/16s, no sunglasses seen); registrar reads
cream-white with orange piping. Spec fields all match: Seedance 2.5 / 720p /
16:9 / 20s / High / Sound On.

## Filing

Uploaded via `scripts/gdrive-bridge/upload_fix1.py` (default destination:
`All Scene/Fix-2`, the second-edit tree per the CEO's 2026-09-08 instruction)
to `S2S-Fix1.MP4`:
https://drive.google.com/file/d/1O5sBMbhmFd6FquuxEguIRv2Wp6uiVwxJ/view

Logged automatically to `Sorry, Sir/logs.txt` by the same script call.
`gdrive-filing` skill read before this call. Fix-2 folder confirmed via
`drive.google.com` (breadcrumb `All Scene > Fix-2`) to hold no prior
`S2S-Fix1.MP4` — only `S2S-B-Fix1.MP4` was already present, confirming no
collision/overwrite.

## Cost / browser

No generation fired — zero credits, zero Unlimited slot time spent on this
task. Two tabs used: the first (`53476238`) was abandoned mid-setup after a
sustained render-pipe fault (screenshot timeouts, transient sub-1280 viewport
reading) per the HARD "a window can shrink on its own" rule — closed and
released from `tab_registry.py` rather than retried past the first clean
recovery attempt. The second tab (`53476245`) did all the identification,
review, and Drive-folder verification work and was closed and released at
the end of the task.

## Verdict

Real S2S take 2 (never previously reviewed) PASSES item 1, the CTO's
explicit gate for this branch, and every other REVIEW ORDER item checked is
either PASS or consistent-but-unconfirmed — nothing FAILED. No take 3 was
generated. Filed to Drive as the S2S-Fix1.MP4 take. Pending the CTO's own
frame review per the standing "operator never self-certifies" rule,
particularly item 3's unconfirmed second exit.

## Notes for reviewer

- **Root cause of the original mix-up (documented on `main`, commit
  `fed52e9`, not yet in this worktree's history but read and applied
  directly since it only concerned wiki/skill files, not code):**
  Higgsfield's Created timestamp is the **fire** time, not the landing time.
  A worker that grabs "the newest card that looks like mine" after a render
  can easily land on a sibling scene's card if that sibling fired later and
  finished around the same wall-clock moment. The fix that held here:
  identify strictly by Created-time == your own fire-time, cross-checked
  against the card's actual prompt text — never by thumbnail similarity or
  grid position, and never by "which card is newest."
- Higgsfield's own "Sence 1/2/3" folders are NOT this film's scene
  numbering — they hold an unrelated production sharing the same account.
  Any future card search for this film should stay in the flat "All assets"
  grid with the Date-range filter, not the Sence-N folders.
- `file_upload` (the Chrome-extension tool) has a 10 MB per-call cap; this
  clip was 18.2 MB, so the browser upload path was skipped entirely in favor
  of `scripts/gdrive-bridge/upload_fix1.py`'s direct Drive REST API upload —
  worth noting for any future clip in this size range.
