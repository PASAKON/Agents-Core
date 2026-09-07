# Shot 58 A/B: Omni 1.1 Flash vs Veo 3.1 Fast

One generation, one shot, for the CEO to put side by side. Task cap was 15
credits; this used 12. Balance: 50 -> 38 (floor was 35 — not touched).

- Existing clip (Veo 3.1 Fast, on `main`): `docs/reports/teaser-shoot-winbox-20260907-run2/shot58.mp4`
- New clip (Omni 1.1 Flash, this branch): `docs/reports/omni-vs-veo-shot58-20260908/shot58-omni.mp4`
- Same project, same two ingredients (`@lung_somchai`, `@noodle_shop`), same
  prompt text, same 9:16 / 720p / 8s / x1 settings. Only the model changed,
  plus one addition: the father's locked voice (**Algenib** — "Male, gravelly,
  low pitch") attached as a third ingredient chip, which Omni supports and
  Veo does not.

## 1. ffprobe

| | Veo 3.1 Fast (existing) | Omni 1.1 Flash (new) |
|---|---|---|
| Video codec | h264 | h264 |
| Resolution | 720x1280 | 720x1280 |
| Frame rate | 24/1 | 24/1 |
| Audio codec | aac, 48000 Hz, stereo | aac, 48000 Hz, stereo |
| Duration | 8.000000 s | 8.000000 s |
| File size | 7,674,929 bytes (~7.3 MB) | 2,916,059 bytes (~2.8 MB) |

Both clips are mechanically identical in container, codec, resolution, frame
rate and duration. The Omni file is **~2.6x smaller** for the same duration
and resolution — a materially lower bitrate. That alone does not prove lower
visual quality, but it is consistent with the softer, more compressed-looking
frames below.

## 2. Frame stills

Six stills in this folder (`docs/reports/omni-vs-veo-shot58-20260908/`), 9:16,
at 0s / 4s / ~7.9s (8.0s itself is past EOF on an 8.000s clip, so the last
sample is 7.9s):

- `veo_frame_0s.jpg`, `veo_frame_4s.jpg`, `veo_frame_7_9s.jpg`
- `omni_frame_0s.jpg`, `omni_frame_4s.jpg`, `omni_frame_7_9s.jpg`

## 3. Comparison (looked at each pair directly; being specific, not kind)

**0s — near-identical setup, both good.** Same man from behind, grey/salt
hair, white t-shirt, navy strap apron, ladle in the broth pot. Veo's frame is
brighter and more legible: the street-facing tables and chairs outside are
sharp and readable, the wall texture and hanging bulb wiring are crisp. Omni's
frame is darker and shallower — background falls into near-black past a few
feet, and the practical bulb blooms more. Read as a lighting/exposure choice,
not a face/wardrobe drift: apron, hair and build match between the two.

**4s — clearest divergence, and it matters for the brief.** Veo shows him
mid-ladle, side profile, mouth closed, nothing that reads as speech. Omni
shows him mid-word — jaw dropped, lips parted, head half-turned toward the
bowl he's placing on the counter — which is exactly the "speaking over his
shoulder" beat the prompt asked for. This is the strongest single piece of
evidence that Omni is actually generating to the dialogue line rather than
just the visual description. Sharpness-wise Veo is still the crisper frame;
Omni's noodle rack and glass cabinet in the background are soft to the point
of being hard to read, and there's a motorbike shape behind the glass that
reads as a slightly generic AI smudge rather than a specific object.

**~7.9s — this is where the two clips actually disagree about the shot.** The
existing Veo clip **turns him to face the camera, smiling, offering the bowl
forward** — a full turn-and-smile that contradicts the prompt's own
instruction ("without turning around... never raises his voice", implicitly
staying in character, not breaking to a presentational smile at camera). This
is a pre-existing property of the clip already on `main`, not something this
task introduced. Omni's clip, by contrast, **stays in the "back to camera,
over-the-shoulder" framing for the entire 8 seconds** — closer to what the
prompt actually specifies, though it also means the CEO gets less full-face
coverage to judge lip sync from later frames.

**Character identity.** Comparing both against the `@lung_somchai` reference
portrait used in Flow (grey-cropped hair, weathered face, moustache, navy
apron over white tee, arms-crossed default pose): both clips carry the same
hair colour/style, build and apron design. I cannot certify pixel-identical
facial geometry from stills at this size — that judgment needs the CEO's eye
on the full-face Veo frame at 7.9s, which is the only frame across all six
that shows the face straight-on and unambiguous.

**Location (`@noodle_shop`) consistency.** Confirmable in Veo (steel shelving,
metal bowls, string-lit alley with tables/chairs — matches shots 56/57 on
`main`). Harder to confirm in Omni: the shallow depth of field and dark grade
obscure most of the background past the immediate wok station. What is
visible (steel wok basin, glass display cabinet, hanging bulb) is consistent
with the same location, but a reviewer should not take this as a strong
confirmation the way the Veo frame is.

**Lip sync.** I have no ears and did not attempt to judge audio — per the
role rules, that call belongs to the CEO on playback. What I can say from
frames alone: Omni's 4s frame shows an open, mid-articulation mouth positioned
exactly where the prompt places a line of dialogue; Veo's corresponding frame
shows a closed mouth mid-action. That is a visual signal the audio/video are
plausibly coupled in the Omni clip, not a sync verdict.

**Net read:** Veo is the sharper, more finished-looking frame in isolation.
Omni is moodier/softer but (a) is the only one of the two that can carry a
locked voice at all, (b) shows visible speech-articulation timed to the
dialogue beat, and (c) stayed truer to the "no turn to camera" instruction
than the Veo clip already on `main` did. Picture quality: Veo ahead. Fitness
to the actual dialogue-driven brief: closer contest than the raw frames alone
suggest.

## 4. Cost table

| | Value |
|---|---|
| Balance before | 50 credits |
| Live estimate shown before firing | 12 credits |
| Balance after | 38 credits |
| Actual spend | 12 credits |
| Cap | 15 credits (not exceeded) |
| Floor | 35 credits (not breached — landed at 38) |
| Re-fires | 0 (single generation, as instructed) |

## 5. Settings and ingredients used (verified before firing)

- Model: **Omni 1.1 Flash** (account default, reconfirmed via the settings
  panel and read back from the fired card's own metadata: "Omni 1.1 Flash ·
  720p · 8 วินาที · 9:16")
- Submode: **องค์ประกอบ** (ingredients), not เฟรม
- Aspect: **9:16**, quantity **x1**, resolution **720p**, length **8 วินาที**
- Agent chip: confirmed **off** (`aria-pressed="false"`) before firing
- Ingredient chips at fire time: **3** — `@lung_somchai`, `@noodle_shop`,
  and the `Algenib` voice (`<flow-audio-ingredient-chip>`, confirmed
  `disabled: false` once the two other ingredients were present)
- Prompt verified via `.ProseMirror` innerText (placeholder stripped) before
  submit — matched the specified text byte for byte, including the Thai
  dialogue line
- Fired with a real `computer` click on เริ่มสร้าง (not JS `.click()`)

## 6. SKILL-CONTRADICTION

```
SKILL-CONTRADICTION: google-flow-ops :: "the only path that inserts a real chip is:
  tile's more-options menu -> click the inner <span class="label">เพิ่มไปยังพรอมต์</span>
  node... succeeded roughly once in fifteen attempts"
  :: On this account/session (2026-09-08, winbox, task-0793785a) there is no
  more-options (⋮) menu on the asset-item row at all — DOM-confirmed
  (`<button class="asset-item" role="option">` with no nested menu button).
  Single-clicking the row selects it (aria-selected) and opens a preview pane
  to the right of the list with a full-width "เพิ่มไปยังพรอมต์" button below the
  preview. Clicking THAT button attached the chip successfully on the first
  try for both @lung_somchai and @noodle_shop (2/2), and on the first try for
  the Algenib voice preset (1/1) — no retries needed, no 7-fail streak. This
  may be a genuine UI change since the skill was last measured, or it may be
  that the ⋮ menu only appears for asset types not tried here; either way, the
  "select the row, then click the panel's own เพิ่มไปยังพรอมต์ button" path is
  the one that actually worked, every time, this session.
  :: 2026-09-08, task-0793785a
```

Also reconfirmed (not new, but worth the tally): `document.hidden === true`
held for this whole tab/session and made two `zoom` screenshot calls time out
after 30s each; `resize_window` reported success but `window.innerWidth`
stayed 1920 throughout; the export hang happened once and needed exactly one
full page reload before the download icon returned to normal and a retry
succeeded.
