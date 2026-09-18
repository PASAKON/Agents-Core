# Flow Thai-text-in-video test — quoting the sign text, and the เฟรม path

task-115ae41c, 2026-09-18. Follow-on to task-6403cbb4 (which settled that the
plate's text does not reach the video at all — Omni re-renders the scene, it
does not copy pixels).

## Question

Can the `@street_front` plate's shop sign (`ก๋วยเตี๋ยว - เครื่องดื่ม`) be kept
legible in a generated video, and by which of the two community-recommended
methods:

- **Arm 1** — name the sign's exact words in quotation marks inside the
  องค์ประกอบ (Ingredients) prompt.
- **Arm 2** — เฟรม (start/end frame) mode, image-to-video from a still whose
  text is already correct.

## Setup

- Project: **AI Film** (`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`)
- Browser: Mac Chrome, device `35a05d33-19a5-4d2e-bab0-08503bad0a9b`
- **One tab for the whole run**, as instructed. Confirmed no other Flow work
  running before starting (single blank tab in the MCP group, no other
  browser_operator tabs).
- Model: Omni 1.1 Flash · 9:16 · 360p · 8 วินาที · x1 for every fire — verified
  in the settings panel immediately before Arm 1's submit.
- Credit balance **before**: **9,995 เครดิต** (account is ULTRA tier).
- Credit balance **after both arms**: **9,989 เครดิต**.
- **Total spend: 6 credits** (one clip fired — Arm 1 only; Arm 2 never
  reached Submit, see below). Well inside the 20-credit cap.
- Never clicked Upgrade/Subscribe/Buy credits.

## Arm 1 — name the words in quotes, องค์ประกอบ mode

1. Opened the `+` picker, searched `street_front`, and before attaching,
   zoomed the preview pane to confirm the sign reads
   `ก๋วยเตี๋ยว - เครื่องดื่ม` (per the skill's "verify chip by thumbnail, never
   by row label" rule — labels are useless here since all ingredient rows
   read generic `ตัวละคร`). Confirmed correct plate.
2. Attached the chip via `เพิ่มไปยังพรอมต์`.
3. Typed the prompt exactly as given in the brief, with the sign text in
   quotation marks. Verified with `document.querySelector('[contenteditable="true"]').innerText`
   — matched the intended text byte-for-byte, Thai text included.
4. Re-verified settings (Omni 1.1 Flash, องค์ประกอบ, 9:16, 360p, 8s, x1,
   estimate **6 เครดิต**) before Submit.
5. Submitted. Render took ~45s (7% at 10s mark → done by ~40s mark),
   consistent with the skill's timing table.

### Reading the sign

The Flow editor's own preview player never rendered a frame (black box,
no `<video>` element in the DOM even after play/seek — a UI issue, not a
generation issue). Per the skill's documented workaround, pulled the actual
render straight from the CDN: `read_network_requests` on the tab surfaced
`https://flow-content.google/video/<id>?...`, `curl`'d it (1.05 MB,
`ffprobe` confirmed **duration=8.000000**), then `ffmpeg` extracted frames.

- **ARM 1 frame 0 reads: ก๋วยเตี๋ยว - เครื่องดื่ม** — full sign in frame,
  every character and both tone/vowel marks clean and legible.
  (`arm1_frame0.png`)
- At **t=7.0s** the sign is still fully in frame and still reads
  **ก๋วยเตี๋ยว - เครื่องดื่ม** exactly (`arm1_frame7s.png`) — the push-in
  camera move has not yet cropped it.
- **ARM 1 frame 8 (the true last frame, t≈8.0s) reads: only the lower half
  of the glyphs is visible** — the push-in has moved the sign's top edge
  (where the ๋ and ี marks sit) above the frame's top border by the final
  frame. What's visible reads consistent with "...ยเตยว - เครื่องดืม" — the
  consonant shapes match the correct word, but the diacritics that
  distinguish it from a similar-looking wrong string are cut off by the
  frame edge, not by resolution. (`arm1_frame8.png`)
- **ARM 1 MATCHES the plate's ก๋วยเตี๋ยว - เครื่องดื่ม for the first ~7 of 8
  seconds**, because frame 0 and the t=7.0s frame both show the complete,
  correctly-spelled sign with every mark intact. **The true last frame
  (t=8.0s) PARTIALLY MATCHES** — it is not illegible and not wrong, it is
  physically cropped by the composition (a push-in shot pushes the sign
  out the top of frame), so the diacritics cannot be confirmed in that
  exact frame.

This is the opposite of task-6403cbb4's failure mode. That run got Thai-shaped
**nonsense**, invented twice, because the words were never in the prompt.
This run got the **correct words**, held correctly for nearly the whole shot,
lost only to ordinary camera framing at the very end. **Quoting the sign's
exact text in the prompt works** — this settles the open question from the
google-flow-ops skill's Thai-text section ("whether naming the exact words in
the prompt produces legible Thai in video" — yes, it does).

### Side effect of quoting: none observed

Google's older guidance warned that quotation marks make the model render the
quoted string as an on-screen caption/subtitle. **Not observed here.** No
caption, subtitle, or extra text box appeared anywhere in either frame — the
quoted string rendered only as the shop sign the prompt described it as, not
as an overlay. This is a single clip, not a systematic test, but it is a data
point against the older-guidance warning firing in this Omni 1.1 Flash /
องค์ประกอบ configuration.

## Arm 2 — เฟรม mode, image-to-video

Followed the exact path from the skill: composer → settings pill → วิดีโอ tab
→ submode toggle → เฟรม. The composer's attach area switched to the two
`เริ่ม` / `สิ้นสุด` slots with the swap control, as documented.

Clicked `เริ่ม`. The picker (`เลือกรูปภาพเฟรม`) opened showing **4 items total**:
`Man standing in alley 9x16`, `Envelope in puddle on p...`, `Man standing in
alley`, `Empty market street at d...` — all plain, untagged images. Searched
the exact handle `street_front` in the picker's own search box: **`ไม่พบชิ้นงาน`
("no items found")**.

**Arm 2 is blocked exactly as predicted.** `@street_front` was created as a
Character/Ingredient asset and the เฟรม picker excludes every
Character/Ingredient-tagged image, showing only plain, untagged images. This
confirms the skill's existing note under "What the frame picker will actually
show you," now confirmed a second time on a different plate. **Stopped the
arm here — no duplicate plate was generated as a workaround**, per the task's
explicit instruction. No credits were spent on Arm 2 (confirmed by the
before/after balance: only Arm 1's 6 credits were deducted).

**Production implication, not a workaround for this task:** any plate that
needs to serve as a frame-locked start image must be generated as a plain
image asset from the start, not as a Character/Ingredient. Since a location
plate currently doubles as both an ingredient reference (for the
องค์ประกอบ path used in Arm 1) and would need to be a plain image (for the
เฟรม path), a production that wants both text-perfect start frames AND
ingredient-referenceable locations needs **two separate assets per location**
— one tagged, one plain. That's a CTO-level production decision, not
something to solve by generating a duplicate mid-task.

## Answer to the task's question

**Yes, the sign can be kept — via Arm 1 (naming the exact words in quotes,
องค์ประกอบ mode), not via Arm 2 (เฟรม mode is inapplicable to this plate as
currently tagged).** The text held correctly for ~7 of 8 seconds and was only
cut off by ordinary shot framing at the very end, not by the model inventing
wrong characters. Quoting the exact Thai text in the prompt is the working
method.

## Costs and timing

| Action | Time | Credits |
|---|---|---|
| Balance read (before) | — | — |
| Arm 1 render (Omni 1.1 Flash, 360p, 8s, x1) | ~40–45s (7% at ~10s → done) | 6 |
| Arm 2 (เฟรม picker check only, never submitted) | ~10s to confirm exclusion | 0 |
| Balance read (after) | — | — |
| **Total** | | **6 / 20 cap** |

## Trap encountered, not previously in the skill

**The clip editor's own preview player can fail to render entirely** — no
`<video>` element ever appeared in the DOM on this account/session (checked
via `document.querySelector('video')` → `null`), across seek-to-end, play,
and reload-free retries. The timeline filmstrip thumbnails (individual
`flow-content.google/image/...` requests) still rendered fine, so this looks
like a lazy-load/player bug distinct from the documented "download button is
dead" trap. **Workaround: read the actual `flow-content.google/video/<id>`
URL out of `read_network_requests` (it's requested even though the player
never displays it) and `curl` it directly** — same CDN-pull pattern the skill
already documents for the dead download button, just applied to a dead
in-page player instead. `ffprobe`/`ffmpeg` locally is more reliable for
frame-accurate first/last-frame reads than trying to scrub Flow's UI anyway.

## SKILL-CONTRADICTION / additions for google-flow-ops

```
SKILL-CONTRADICTION: google-flow-ops :: (no existing rule covers this)
  :: The clip editor's built-in preview player rendered no <video> element at all
     (document.querySelector('video') === null) across play/seek/end-jump, while
     the timeline filmstrip thumbnails loaded fine. This is distinct from the
     documented "download button is dead" trap (that one at least has a player).
     Recovery: read_network_requests for `flow-content.google/video/`, curl it
     directly, ffprobe/ffmpeg locally. Byte-identical CDN pull, same pattern as
     the existing download-button workaround.
  :: 2026-09-18, task-115ae41c
```

```
SKILL-CONTRADICTION: google-flow-ops "Thai text ... video model is unproven" ::
  the open question ("whether naming the exact words in the prompt produces
  legible Thai in video") is now settled: yes, for the first ~7 of 8 seconds
  of an 8s Omni 1.1 Flash / องค์ประกอบ clip, quoting the exact Thai text in
  the prompt produced the exact correct sign, matching the plate. The failure
  mode was NOT wrong/invented characters (task-6403cbb4's failure) — it was
  ordinary camera framing cropping the sign at the very last frame.
  :: 2026-09-18, task-115ae41c, 6 credits, screenshots in
     docs/reports/flow-thaitext-20260918/
```

## Skill learning

- WRONG    : (none — no existing rule was disproven; the "frame picker
  excludes Character/Ingredient" rule was confirmed correct a second time)
- MISSING  : The skill has no fallback for "the in-page player itself never
  renders a `<video>` element" — only the separate "download button is dead"
  trap. Added as a SKILL-CONTRADICTION above with the CDN-pull workaround,
  which is the same technique already documented for the download-button
  case and should probably be generalized into one "never trust the player,
  always pull the CDN URL" rule rather than two separate traps.
- COSTLY   : Getting the last frame took the most time — the in-editor
  player being completely dead (no video element, not even a hung
  "exporting" state) meant several rounds of play/seek/pause before giving
  up on the UI and going straight to `read_network_requests` +
  `curl` + `ffprobe`. Knowing to skip the player entirely and go straight to
  network capture (which the skill already documents for downloads) would
  have saved ~5 of the ~35-step budget.
- (none)  : n/a — see MISSING/COSTLY above.
