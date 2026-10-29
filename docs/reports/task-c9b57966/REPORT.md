# REPORT task-c9b57966

## Summary

Completed M4 proof report comparing the EP1 baseline prompt pattern ("current way") against the Cinematic Prompt Library (`CMO_Knowledge_CinematicPrompts`) across five core story shots for ILAG S1 EP2 "ล้มบอลซอย". Delivered the full side-by-side prompt analysis, 3-line technical diffs, Flow Omni 1.1 operational risk analysis, and CMO comparison matrix at `docs/reports/cineprompt/M4-PROOF.md`.

## Files Changed

- `docs/reports/cineprompt/M4-PROOF.md` (new proof report with all 5 EP2 shots written both ways, diffs, and head-to-head evaluation)
- `docs/reports/task-c9b57966/REPORT.md` (task report)

## Work Performed

1. **Library & Baseline Audit:**
   - Inspected `agent/agy-task-9378123b:.claude/skills/CMO_Knowledge_CinematicPrompts/references/prompts/shortfilm.json` and `movie.json`.
   - Reviewed `CMO_Knowledge_Flow_Omni1.1` and `CMO_Standard_Film_PromptFormat` for house constraints (9:16 vertical, 720p, single continuous take, speech done by second 5/7, last 3 seconds hold, daylight only, cast counts, no on-screen text, banned banknotes/currency).
   - Reused EP1 continuity cast handles (`@friend__jersey`, `@boy__tiger`, `@ton__work`, `@mee__rider`, `@collector__work`) and established plate references (`soi__field`).

2. **Five EP2 Shots Written in Both Ways:**
   - **Shot A (The Bribe):** Baseline (EP1 S14) vs. Library (`shortfilm-ilag_lakorn-02` + `shortfilm-ilag_lakorn-07`). Low-angle 50mm prime compression and 5600K raking split key elevate bribery to lakorn moral extortion.
   - **Shot B (Comic):** Baseline (EP1 S16) vs. Library (`movie-comedy-01` + `movie-comedy-02`). Wide screwball comedy framing on 35mm lens with 5000K shadowless sitcom bounce illumination for five bandaged players and Ton.
   - **Shot C (The Turn):** Baseline (EP1 S33) vs. Library (`shortfilm-ilag_lakorn-04` + `shortfilm-ilag_lakorn-10`). Eye-level 50mm prime lens with 3800K warm afternoon rim light and moral cinema redemption palette.
   - **Shot D (The Twist):** Baseline (EP1 S30) vs. Library (`shortfilm-ilag_lakorn-08` + `movie-thriller-01`). 35mm slow creeping dolly with 4500K directional sunbeam key for the referee waist pouch unmasking.
   - **Shot E (The AI Gag):** Baseline (EP1 S35) vs. Library (`movie-comedy-03` + `shortfilm-thai_everyday-04`). Deadpan 50mm prime comic framing with 3200K golden-hour raking light on Boy's reaction to impossible mid-air ball physics.

3. **Validation & Ban Compliance:**
   - Checked hard bans: 0 occurrences of emotional redness (`blush`, `flushed`, `red face`, `red cheeks`, `red ears`, `หน้าแดง`, `หูแดง`).
   - Confirmed all depicted individuals are adults (18+); no children or minors.
   - Checked typography: 0 occurrences of `«`, `»`, or em dashes `—` in prompts and report.
   - Strictly enforced 1 Thai dialogue line per shot without em dashes or guillemets.
   - Maintained all EP1 house rule paragraphs verbatim across both prompt variants.

## Not checked / risk

- **No live video generation was performed ($0 edit-only task):** Hypotheses regarding Flow Omni 1.1 rendering behavior are derived from measured skill documentation (`CMO_Knowledge_Flow_Omni1.1`) rather than fresh test fires.
- **Shot B multi-character coherence risk:** Staging six simultaneous adult characters (Ton + five injured players with distinct bandage placements) carries a high risk of facial distortion, limb merging, and bandage position drift on Flow Omni 1.1 Flash. The current way's flat framing is rated safer than complex beat timing.
- **Shot E generative physics risk:** Flow Omni 1.1 may struggle with non-physical vector redirection (the soccer ball snapping 90 degrees mid-air without inertia) and could introduce generative warping or visual noise.
- **Fine-motor object contact risk:** Envelope handoffs (Shots A and C) and waist pouch zipper manipulation (Shot D) carry documented risks of hand/object blending on Omni 1.1.

## Limitations

- The report evaluates prompt formulation and structural guidance text only; final visual appeal remains subject to Flow Omni 1.1 generation lottery upon future production firing.

## Blockers

- (none)

## Skill learning

- Reconciled the Cinematic Prompt Library's advanced cinematography parameters (precise focal lengths, Kelvin color temperatures, directional lighting ratios, and dedicated color grade blocks) with Flow Omni 1.1's strict house negative boundaries (single take, no cuts, no on-screen text, daylight lock, tail quiet hold).
- Identified that while the library way decisively improves dramatic 1-to-2 character confrontations, simpler baseline prompts remain strategically preferable for high-complexity multi-character frames to prevent prompt token congestion and generative artifacting.
