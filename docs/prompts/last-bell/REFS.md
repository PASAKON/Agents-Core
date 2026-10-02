# REFS.md — reference images and the champa slot method

## The champa slot rule (CEO, 2026-10-03)

- Images are attached in slot order and named in the prompt by position: the first attached image is
  `@ภาพ1`, the second `@ภาพ2`, and so on. The prompt describes what each one is.
- The CEO estimates about 10 slots. **Not yet measured** — the first champa test counts them.
- Fill order: location → characters → props → (last 3 slots) continue frames.
- **Continue the same scene** (same place, the action carries on): put the previous clip's frames at
  **−1.0 s, −0.5 s and the last frame** in the last 3 slots (CEO's choice of spacing, 2026-10-03), oldest first,
  and say in the prompt: "Continue directly from @ภาพ8 → @ภาพ9 → @ภาพ10: same place, same light, same
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
