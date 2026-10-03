# REFS.md — reference images and the champa slot method

## The champa slot rule (CEO, 2026-10-03)

- Images are attached in slot order and named in the prompt by position: the first attached image is
  `@ภาพ1`, the second `@ภาพ2`, and so on. The prompt describes what each one is.
- **Measured 2026-10-03: 9 slots** (`@ภาพ1`–`@ภาพ9`), not the 10 the CEO estimated. In "หลายภาพอ้างอิง"
  mode the first slot is the "Frame 1" button, every later one `button[aria-label='Add frame']`; that button
  disappears after the 9th image. The paperclip ("Up to 3 images") is a different attach, capped at 3; do not use it.
  The test job with 9 references (`lb-t2-e5-r9`) was accepted with all 9 tags in the @ menu.
- **Prompt cap: 2,000 characters.** The textarea keeps 12,000+, but the server answers "ข้อมูลไม่ถูกต้อง" and
  queues nothing above 2,000 (2,000 accepted; 2,001 / 2,500 / 3,000 / 4,000 / 8,000 refused, 2026-10-03; measured with ASCII text, Thai not yet).
  `build_shots.py` asserts the cap for every shot.
- A continue shot therefore carries at most **6** other references (9 minus the 3 continue frames).
- Fill order: location → characters → props → (last 3 slots) continue frames.
- **Continue the same scene** (same place, the action carries on): put the previous clip's frames at
  **−1.0 s, −0.5 s and the last frame** in the last 3 slots (CEO's choice of spacing, 2026-10-03), oldest first,
  and say in the prompt: "Continue directly from the last three images, oldest first: same place, same light, same
  positions; the action carries on from the last frame."
- **Change of location or scene:** no continue frames. The prompt carries the story on from the last scene.
- Extract the three frames with ffmpeg (`-sseof -1.0`, `-sseof -0.5`, and the last frame) as PNG at source size.

## Round 1 reference images (ChatGPT on winbox, 2026-10-03)

Character sheets follow CMO_Procedure_CharacterSheet (plain light background, numbered emotion panels, one
full-body panel). Two variants of each character so the CEO can choose. Locations and key art carry the film's
yellow-green look; locations hold no people.

| Name | What | Variants |
|---|---|---|
| ch_kaew_a / _b | @Kaew sheet | 2 |
| ch_yai_a / _b | @Yai sheet | 2 |
| ch_mek_a / _b | @Mek sheet | 2 |
| ch_governor_a / _b | @Governor sheet | 2 |
| ch_naga_a / _b | @Naga creature sheet | 2 |
| loc_city | Suwannawari at dawn, wide | 1 |
| loc_bell_pavilion | top of the great chedi, the bell pavilion | 1 |
| loc_yai_house | inside Yai's stilt house | 1 |
| loc_canal | canal with the long footbridge | 1 |
| prop_great_bell | THE GREAT BELL, three views | 1 |
| prop_mallet | THE MALLET, three views | 1 |
| key_bell_naga | key art: Kaew at the bell, the Naga's eye rising | 1 |
| key_storm_city | key art: the city under the storm sky | 1 |
