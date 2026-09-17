# Scene 1 v2 — shot3 retake (prompt-syntax test) — 2026-09-18

**Folder name is legacy** (per CTO mid-session correction). The shot fired here
is now called **shot2** in the story's beat order, not shot3. Deliverable
files are named accordingly: `shot2-retake.mp4`, `shot2-retake_frame0.jpg`.
The folder itself keeps its original `scene1-v2-shot3-retake-20260918` name —
CTO said to keep using it, only the files inside are renamed.

## What this shoot tested

Shot 3 (original numbering) came back with the wrong face, wrong hair, and a
different noodle shop, despite Flow's post-hoc record confirming all 3
ingredient chips were used. Suspect: the prompt was written in Seedance/
Higgsfield style (`@handle speaks in Thai`, no per-chip role assignment)
instead of Omni's documented `<IMAGE_REF_N>` inline convention. This shoot
re-fires the same beat with the corrected prompt syntax, unedited, to isolate
whether prompt syntax (not chip binding) was the cause of the drift.

## Credit ledger

| Checkpoint | Balance | Delta |
|---|---|---|
| Start (read from account menu, confirmed) | 14 | — |
| Live estimate in settings panel, re-checked immediately before Submit | — | estimate read exactly "การสร้างจะใช้ 12 เครดิต" |
| After the one generation | 2 | **-12** |

Exactly 12 spent, matching the estimate and the task's hard cap. **One
generation fired. No retry, no second shot.**

One wrinkle worth recording: the Submit click surfaced a toast reading
"มีเครดิตไม่เพียงพอที่จะดำเนินการนี้ ลองใช้การตั้งค่าอื่นๆ หรืออัปเกรดเพื่อรับ
เครดิตเพิ่มเติม" (insufficient credits — try other settings or upgrade) at
the moment of submit, and the composer's chips/prompt text were cleared
immediately after. This read exactly like a failed/blocked submission. I did
**not** retry — per the "one shot" and "insufficient-credits toast" rules, I
went straight to checking the balance and the media library instead of
re-firing. The balance had already dropped 14→2 and the newest video card
(opened via the วิดีโอ tab, first item, title "Young man watching father in
sho...") showed the exact prompt, exact 3 chips, and Omni 1.1 Flash, 8s —
confirming **the generation did fire successfully** and the toast was a
stale/racy low-balance warning, not a real block. `SKILL-CONTRADICTION` below.

## Chip-attach verification (all 3, in order)

Attach order matters — `<IMAGE_REF_N>` is indexed by attach order.

1. **First attempt failed silently and was caught, not assumed.** Using
   `find()`'s natural-language match for "@nong_daeng row" clicked the wrong
   list item — the chip that landed was visually confirmed (via `zoom`) to be
   the **@noodle_shop** interior plate, not @nong_daeng's face, even though the
   picker's "ตัวละคร" category label matched all three items identically (Flow
   tags the location plate as a "character" type in this project). Caught by
   looking at the actual chip thumbnail, not by trusting the row label. Removed
   the chip and restarted using the picker's own search box + a preview-image
   check before every add from then on.
2. **@nong_daeng → IMAGE_REF_0.** Searched "nong_daeng" in the picker, preview
   pane showed the correct face, clicked "เพิ่มไปยังพรอมต์". Chip thumbnail
   confirmed visually as the face. **Picker-exclusion verified**: re-searching
   "nong_daeng" afterward returned "ไม่พบชิ้นงาน" (not found).
3. **@noodle_shop → IMAGE_REF_1.** Searched "noodle_shop", preview pane showed
   the correct shop interior, added. **Picker-exclusion verified**: re-search
   returned not-found.
4. **Iapetus (voice) → 3rd ingredient.** Opened the เสียง (voices) category,
   searched "Iapetus", confirmed label "Male, clear, mid-low pitch" (matches
   the cast ledger in `google-flow-ops`), added. **Picker-exclusion verified**:
   re-search of all three names ("nong_daeng", "noodle_shop", "Iapetus") in one
   pass all returned not-found — **3/3 bound, 0 error chips.**

Final state before submit: 3 chips visible in composer (face thumbnail, shop
thumbnail, pink voice icon), องค์ประกอบ mode (not เฟรม — ingredients, not
frame-lock), model Omni 1.1 Flash, 720p, 8 วินาที (8s), 9:16, x1, credit
estimate exactly 12. Verified live estimate a second time immediately before
the Submit click, per the "re-verify at the moment you commit" rule.

## Prompt — byte-for-byte verification

Typed via `document.execCommand('insertText', ...)` per paragraph (with
`insertParagraph` between blocks) after `el.focus()`, never via simulated
keystrokes — avoids the `@`-autocomplete trap (not relevant here since no
`@handle` appears in this prompt, which is itself part of the fix). Read
`innerText` of the `[contenteditable="true"]` element before submit:
confirmed exact match to the brief, including:
- Both `<IMAGE_REF_0>` and `<IMAGE_REF_1>` present, inline, at the sentence
  points naming that subject (per Omni's documented convention).
- The Thai line `ลูกค้าเก่าคนไหนโทรตั้งสี่ครั้ง` present character-for-character.
- No "No music." line (deliberately omitted, per the brief and the skill's
  2026-09-08 correction).

## Render result

| Check | Result |
|---|---|
| Duration | 8.00s (ffprobe) |
| Resolution | 720x1280 |
| Audio | AAC present, mean_volume -19.8 dB, max_volume -0.0 dB (real signal, not silence) |
| Model used | Omni 1.1 Flash (visible in the clip's own edit page) |
| Chips on the fired generation | 3 (face, shop, voice) — visible on the clip's own detail page after the fact |
| Prompt on the fired generation | matches the sheet exactly (visible in the clip's sidebar) |

Downloaded via the documented workaround (toolbar download button is a
confirmed dead no-op on this account, per `google-flow-ops`): played the clip,
captured the signed CDN URL via `read_network_requests`
(`flow-content.google/video/<id>?Expires=...&Signature=...`), `curl`'d it
directly. Verified byte-identical playable file via `ffprobe`/`ffmpeg`.

## Frame-0 comparison against shot1

(`shot1_frame0.jpg` pulled from commit `279276f3` of the prior scene1-v2
shoot — this worktree's `docs/reports/` did not carry that folder, so the
reference was retrieved via `git show` from history rather than assumed
missing.)

**Set / location — matches on every structural element, differs on one
readable detail:**
- Fluorescent tube light overhead, same position and style: **match**.
- Red/orange Thai menu board on the left wall, same position: **match on
  layout and color scheme**. **Does not match on the printed text** — shot1's
  board reads "บ้านตำร..." and this take's board reads "...เห้อนด่าขแต้ง" (a
  different, garbled Thai string). Omni is regenerating the sign's text each
  time rather than holding it fixed — expected, since the location reference
  is a photo, not an OCR-locked asset, and no shot in this series has pinned
  signage text.
- Roller shutter open to the street, top-right: **match**. Street beyond it
  (motorcycles, a pickup truck, shopfronts) reads as the same kind of busy
  Thai street in both, though the specific vehicles differ shot to shot (both
  takes differ from each other too, so this is consistent with "same set,
  different render" rather than drift).
- Wooden tables with customers eating in the background: **match** (present
  in both, different individual diners — expected, they were never chip-locked
  characters).
- No aspect-ratio padding, no black-and-white re-fire: **confirmed** — full
  color, 720x1280, matching the 9:16 setting throughout all sampled frames
  (0s, 3s, 5s, 7s).

**Character — matches on wardrobe and general look, close but not
pixel-identical on hair:**
- Wardrobe: plain grey polo shirt, dark trousers in both — **match**.
- Hair: both are short black hair. Shot1's cut reads slightly longer on top
  with more of a side part; this take's cut reads tighter/more closely
  cropped, consistent with the prompt's explicit "24 years old, short cropped
  black hair" (the earlier report's `shot3_frame0.jpg` — the take being
  re-shot here — is the one that was *wrong*, not shot1; I compared against
  shot1 as instructed, and the hair here is close to shot1's but not an exact
  pixel match). Face structure, build, and general look read as the same
  actor/@nong_daeng reference in both.

**Action beat — checked across the clip, not just frame 0:** frame 0 catches
him mid-cooking (ladling broth); by ~3s he has stopped, turned, and is
speaking with a visible frown; by ~5s he is standing still, mouth closed,
frowning, looking off toward where the father would be. This matches the
brief's described beat ("stops what he is doing and stands still... watching
his father's back... with a small frown") — the father himself is not in
frame, consistent with a medium shot held on the son alone.

## Voice — technical check only, no ear claim

AAC track present, non-silent (mean -19.8 dB / max -0.0 dB, `ffmpeg
volumedetect`). That is the limit of what I can verify. I have no ears —
whether it is audibly Iapetus, whether it sounds like the same speaker as
shot1's ต้น, and whether the line reads as "pointed, quietly suspicious, low
volume, never raised" as directed, are judgments for the CEO.

## Verdict

**The prompt-syntax fix worked, on the evidence available.** The set now
carries every structural element shot1 had (light, menu-board position and
color, open shutter, street beyond, tables with diners), the character wears
the correct wardrobe and a closely-matching (if not pixel-identical) haircut,
and the described action beat (stop → turn → frown → watch) plays out inside
the 8s exactly as briefed. None of the shot3-original's failure modes (wrong
face, wrong hair, a completely different shop) recurred. The one soft miss —
the menu board's printed Thai text differing between takes — is a
signage-regeneration artifact, not a reference-binding failure, and was
present as a risk in every take in this series (no shot pins the sign's exact
text).

## SKILL-CONTRADICTION

```
SKILL-CONTRADICTION: google-flow-ops :: no existing note describes an
  "insufficient credits" toast appearing at Submit when the live estimate
  read exactly the balance available (14 balance, 12-credit estimate, 2
  credits of headroom)
  :: On this account, clicking Submit surfaced
  "มีเครดิตไม่เพียงพอที่จะดำเนินการนี้ ลองใช้การตั้งค่าอื่นๆ หรืออัปเกรดเพื่อรับ
  เครดิตเพิ่มเติม" and the composer's chips/prompt were cleared immediately —
  reading exactly like a blocked/failed submission. It was not: the balance
  dropped 14->2 (exactly -12) and the newest video in the project's วิดีโอ tab
  carried the exact prompt, exact 3 chips, and Omni 1.1 Flash/8s config that
  had just been submitted. The toast appears to be a stale or racy low-balance
  warning fired alongside a generation that actually succeeded, not a real
  block. Future operators seeing this toast should check the balance and the
  media library before assuming the shot did not fire and before considering
  any retry.
  :: 2026-09-18, task-8ea0576a
```

## Files in this folder

- `shot2-retake.mp4` — the fired clip, pulled from Flow's signed CDN URL
  (download button confirmed dead again this session), verified with
  `ffprobe`/`ffmpeg`.
- `shot2-retake_frame0.jpg` — first frame, used for the shot1 comparison
  above.

## Hard stops respected

- One generation only — did not retry despite the insufficient-credits toast.
- Did not click "อัปเกรด" (upgrade) anywhere, including on the toast itself
  and the low-credit banner.
- Did not touch or rename any existing character/voice/location asset in the
  project.
- Did not sign in to anything; session was already authenticated.
- Balance read from the account menu before and after, both confirmed via
  `javascript_tool` text match, not assumed from a screenshot glance.
