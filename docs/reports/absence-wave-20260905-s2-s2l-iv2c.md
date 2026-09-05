# Absence wave 2026-09-05 — S2 / S2L take5 / IV2c take4

task-1fe95cf3. Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
("The Valder Collection No.7"). Video-reference upload outage (GH #133) was
still live for this wave — the S2L loop ran per the escalation ladder in
`docs/PREVIZ-ELEMENTS.md`.

## 1. S2 — S2-Fix1.MP4

- **Fields**: 20s · 720p · 16:9 · Seedance 2.5 · High · 1/4 · Sound On
- **Price**: Unlimited, struck `140 → 0` — zoom-confirmed immediately before fire
- **Chips**: 6/6 bound, 0 error chips (`prompt-lint --chips` expected 6; live count
  via `[class*="preview-item"]` tiles, deduped by `@project_` label — see selector
  note below)
- **Previz**: none needed — this sheet carries no video reference, outage does
  not touch it
- **Info icon**: no "Rights verification required" banner, no NSFW/refusal badge
- **Verdict**: PASS on the sheet's own review order — painting hangs crooked at
  0s, comes to rest at ~8s with the zoom into a correct four-armed beaded star
  crack, cuts to Dupe's held reaction, cart carries the painting away at
  matching size, final frame holds the crack above the intact plaque. One cart
  throughout, castor wheels visible, no duplicate painting.
- **Drive**: `All Scene/Fix-1/S2-Fix1.MP4` —
  https://drive.google.com/file/d/112De80aMuLgLKi01eq3MGXKONv_aH-dv/view

## 2. S2L take 5 — S2L-Fix1-take5.MP4

- **Fields**: 20s · 720p · 16:9 · Seedance 2.5 · High · 1/4 · Sound On
- **Price**: Unlimited, struck `140 → 0` — zoom-confirmed immediately before fire
- **Chips**: 8/8 bound, 0 error chips — the exact five that were plain text last
  round (char_woman, char_student_c, char_visitor_b, char_visitor_a,
  char_critic_b) all bound clean this time, plus char_cleaner_c,
  loc_wall_pov_e, prop_cart_a_painted
- **Previz**: `docs/S2L-Render.MP4` attached, waited the full 20 minutes,
  never resolved (tile stayed on the "Checking.." spinner the whole time) —
  fired WITHOUT it per the outage loop, reference removed before paste
- **Info icon**: no rejection banner, no NSFW badge
- **Verdict**: FLAGGED — camera geometry defect, exactly the cost the previz
  was supposed to prevent. The prompt calls for "the camera INSIDE the broken
  wall, looking out" with the break as a hard black silhouette filling the
  extreme foreground and every person behind it. The actual render is a
  conventional wide gallery shot with the crack small and distant on a back
  wall — no foreground silhouette at all. Content otherwise close: three
  people present at 0s (art student, tawny fur, magenta fur) as written, Dupe
  correctly isolated far left with his cart, blue-coat woman correctly
  arriving into frame. Did not confirm the maroon-suit man's final arrival
  cleanly in scrub — he is only faintly visible mid-background at ~13s, not
  clearly landing in the final five-person lineup the way [18s] describes.
  Filed as-is per the no-exceptions rule; the editor decides usability.
- **Drive**: `All Scene/Fix-1/S2L-Fix1-take5.MP4` —
  https://drive.google.com/file/d/1nNUles8-OyWVLuFq7iwesPkyVRW7r67P/view

## 3. IV2c take 4 — IV2c-Fix1-take4.MP4

- **Fields**: 20s · 720p · 16:9 · Seedance 2.5 · High · 1/4 · Sound On
- **Price**: Unlimited, struck `140 → 0` — zoom-confirmed immediately before fire
- **Chips**: 1/1 bound (`@project_absence_char_dupe_interview_house`), 0 error
  chips
- **Previz**: none needed — no video reference, unaffected by the outage
- **Info icon**: no rejection banner, no NSFW badge
- **Verdict**: FLAGGED — the crash's cause is still not visible. Scrubbed the
  8s crew reveal at multiple frames (0:07–0:09): three crew members present,
  correctly distinct (camera operator seated, boom operator standing with
  pole, bearded man standing), Dupe's own frame stays clean 0–7s, whip pan in
  and out reads correctly, tall daylit windows with greenery visible behind
  the crew — but **no fallen light stand is anywhere in frame**. Both LED
  softbox stands are upright. The bearded man's arms are out at chest height
  but not unambiguously "half-raised and frozen" the way the sheet specifies;
  without the fallen stand beside him there is nothing for the pose to be
  about. This is the identical defect that got take 3 flagged, recurring in
  take 4 despite the rewritten prompt explicitly describing the stand "ON THE
  FLOOR... unmistakably DOWN." Plum seating / built-in shelving not clearly
  confirmed in the crew's half either — only the window/greenery criterion
  reads clean. Filed as-is; needs a take 5 or a stronger prompt bind on the
  light stand specifically.
- **Drive**: `All Scene/Fix-1/IV2c-Fix1-take4.MP4` —
  https://drive.google.com/file/d/1ZsiXyZIfXF3V9ZMcoYlazxOhkZHok58g/view

## Selector correction for the chip gate

`document.querySelectorAll('[data-element-id], .element-chip, a[href*="/element"]')`
returned **0** on the live composer even with 6–8 visibly-bound reference
thumbnails sitting above the prompt box. The selector that actually matches
resolved reference tiles on this composer version is:

```js
[...document.querySelectorAll('[class*="preview-item"]')]
  .map(t => t.textContent.match(/@project_\S+/)?.[0])
  .filter(Boolean)
```
then dedupe with `new Set(...)` — each tile renders twice in the DOM (image +
label overlay), so the raw NodeList count is 2x the true bound-reference
count. `.text-icon-error` returned 0 throughout and is presumably still
correct for the error state, but was never observed non-zero this wave to
confirm.

## Download-folder gotcha

Higgsfield's Download button writes files named `hf_<YYYYMMDD_HHMMSS>_<uuid>.mp4`
into the shared `~/Downloads` folder — not the generic `top_000NN_.mp4` files
already sitting there from other sessions. Matched each download to its clip
by the embedded timestamp (close to the fire time) plus a `ffprobe`
duration/resolution check plus a visual frame-grab, after an early false
alarm: grabbing the newest-by-mtime file in `~/Downloads` picked up an
**unrelated pre-existing file** (15.08s / 1920x1088, clean-decodes, no
truncation) that had nothing to do with this wave. Do not identify a
Higgsfield download by "newest mtime in ~/Downloads" alone — that folder is
shared across every operator and task that has ever driven this account.
Match by the `hf_*` timestamp prefix and verify content with a frame grab.

## Fire-slot note

Between S2L finishing and IV2c's first fire attempt, two consecutive
Generate clicks were refused with "You can generate 1 unlimited video, image
& audio generation at a time" even though this project's own "Processing"
indicator read 0 and `tab_registry.py list` showed no other live
browser_operator task. A 2-minute wait cleared it on the third attempt with
no other action taken — most likely server-side slot-release lag rather
than a genuinely stuck slot. Recorded here in case the pattern recurs.

## Reload / composer-drift notes (already documented in the skill, reconfirmed)

- A full page reload preserves the composer's pasted text and reference
  chips, but always resets Unlimited to OFF, resolution to 480p, and duration
  to 5s. All three were rebuilt and re-verified before every fire this wave.
- Two consecutive clicks on the Generate button produced no visible response
  once (mid S2L); one hard reload fixed it, per the skill's stale-tab
  escalation ladder. No second tab was opened — the tab registry hook
  correctly refused a second tab for this task.
