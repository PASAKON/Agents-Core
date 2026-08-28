# HOUSE PROMPT TEMPLATE — researched 2026-08-28 · applies to every video prompt

Sources: Higgsfield's own Seedance guide, fal.ai's guide, ChatCut's formulas,
MindStudio's timeline-prompting study. Cross-checked against what our own fires
already proved.

## THE TEMPLATE — element order is load-bearing

```
[TECH HEADER — FIRST LINE, ALWAYS]
20s · 720p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS  (or: Shot 1/Shot 2 labels)

[REFERENCES — each with an explicit JOB]
@ref — WHAT IT CONTROLS (face only / frame+light / the object / mood)

[TIMELINE BEATS — bracketed seconds, 3–4 beats max, 2–3 sentences each]
[0s]  Shot type: subject + physical action. Camera <operator term>. Atmosphere.
[7s]  ...
[14s] ... hold / exit.

[AUDIO — always state it, or you get car-ad score]
room tone, <one foley detail>, no music

[NEGATIVES — the 5–8 that matter for THIS scene, first; house wall after]
```

## THE TEN RULES

1. **Tech spec at the TOP, never the bottom.** Duration, resolution, aspect,
   and the camera-lock ("one continuous take, no cuts") are the first thing the
   model reads. *(We had been burying `20s · 720p` at the bottom of every file.)*
2. **Timestamps beat prose.** `[0s] [7s] [14s]` distributes action across the
   clip instead of cramming it into one static frame — measurably better
   adherence. 3–4 beats max; overloading a timestamp is the top failure mode.
3. **Each beat = Shot type → subject+action → Camera → atmosphere.** 2–3
   sentences. Precision over length.
4. **Say what the camera is NOT doing.** Without "no cuts, no zoom" Seedance
   invents cuts on its own. Operator vocabulary only: dolly, push-in, locked-off,
   whip pan, lateral track. Never "the camera moves".
5. **Dialogue: tone BEFORE the line, inline, in one sentence.**
   `He says it quietly, warm and unhurried: "Sir. You should have told me."`
   Short lines only — long monologues drift out of lip-sync; split across beats.
6. **Physical verbs.** melt / fracture / snap / slot / wipe — never "becomes",
   "begins to", "seems to".
7. **Every reference gets a stated JOB.** `@char_valder — face, build and
   costume` · `@loc_hall_big_e — the room, its light and floor; nothing else`.
   An unjobbed reference is a coin-flip about what the model borrows.
8. **Negatives: few and aimed.** 5–8 scene-specific bans up front (the ones
   that killed takes before), the long house wall after them. A 200-word wall
   with no priority buries the one ban that matters.
9. **Front-load what matters most.** The first 50–100 words carry the shot.
10. **Nouns stay identical.** One name per character per prompt — "Dupe" every
    time, never he/the cleaner/the man in rotation. Subject-reference drift is
    a documented failure mode.

## WHAT WE ALREADY DO RIGHT (keep)
Camera-lock language · "no music" every scene · quoted dialogue · one-colour
casting · reference thumbnails counted against mentions · warm-shadow grade
block · the Anderson plans (they translate perfectly into beats).
