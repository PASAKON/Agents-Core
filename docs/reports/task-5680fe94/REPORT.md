# REPORT task-5680fe94

## Overview
Executed Brief L4 (`/opt/MoonieXHQ/Work/khaohom-survival/briefs/BRIEF-L4-ep01-plates.md`) to create the complete set of 16:9 image plate prompts (`plates.json`) for Long Episode 1 (DAY 0, "เสียงเตือนจากมือถือ"), following the approved script (`Q-20261101-0819-764f`), Series Bible v3 (`canon/BIBLE-v3.md`), and format reference (`ep04/s1-stills/plates.json`).

The output includes:
1. **4 Character-Sheet Turnaround Plates (`NPC-<short>`):** Following the N0 specification (attaching `C1.png`, front/side/back views plus 3 expressions) for all new characters introduced in EP1:
   - `NPC-hoarder`: The panicked bottled-water hoarder in the convenience store.
   - `NPC-aunt`: The kind, stubborn elderly neighbour aunt sweeping water on her porch.
   - `NPC-pet-neighbour`: The compassionate female neighbour sheltering her pets.
   - `NPC-uncle`: The elderly uncle stranded on his porch without a vehicle.
2. **35 Still Plates (`L1-S01` to `L1-S35`):** In approved script order, fully adhering to 16:9 landscape framing, safe-zone exclusions (top 12% HUD, bottom 22% subtitles, right 14% inventory UI, central 70% width action zone), Day 0 character continuity, lighting requirements, and non-violent comic styling.
3. **Plate Notes (`NOTES.md`):** Detailed analysis of plate reuse opportunities (identical locations/poses) and the required `## Not checked / risk` section.

## Files Changed
- `docs/reports/task-5680fe94/plates.json` (created)
- `docs/reports/task-5680fe94/NOTES.md` (created)
- `docs/reports/task-5680fe94/REPORT.md` (created)

## Validation Performed
- **Contract & Security Compliance:**
  - Read input files strictly via plain shell commands (`cat`, `tail`, `grep`, `ls`) without chaining or redirection.
  - Never invoked `read_file` or `view_file` on `/opt/MoonieXHQ/Work`.
  - Wrote output files strictly inside `docs/reports/task-5680fe94/` within the assigned worktree.
  - Regularly checked for incoming messages in `MAILBOX.md`.
- **JSON Structure & Schema:**
  - Validated `plates.json` as a properly formed JSON list containing 39 entries (4 character turnarounds + 35 still plates).
  - Verified each entry contains required keys: `name`, `attach`, and `prompt`.
- **Attachment Specification:**
  - Attached `/opt/MoonieXHQ/Work/khaohom-survival/design-v2/chars/C1.png` when Khao Hom is in the frame or for character turnarounds.
  - Attached future NPC sheet paths `/opt/MoonieXHQ/Work/khaohom-survival/long/ep01/stills/NPC-<short>.png` when an NPC is solo in the frame (`L1-S13`, `L1-S28`, `L1-S29`).
  - Attached `C1.png` and described the NPC in words when both are in frame (`L1-S27`).
- **Prompt Formulation & Constraints:**
  - Every still prompt starts with `"Wide 16:9 landscape illustration. Same illustration style as the attached character sheet (clean dark outlines, soft cel-shaded lighting...)"`.
  - Every prompt embeds the exact 16:9 safe zone framing rule: central 70% width, top 12% HUD clearance, bottom 22% subtitle clearance, right 14% inventory clearance.
  - Night scenes (03:00, midnight) use torch or phone screen glow on Khao Hom's face, avoiding pitch-black darkness.
  - Selfish scenes are kept comic rather than cruel; no blood, wounds, fighting, or death are depicted.
  - Transformer failure (`L1-S33`) is depicted as a distant silent blue spark flash with no fire and no people near the utility pole.
  - All phone screens, store signs, labels, cash, and breaker panels are specified as blank or blurred with no readable words.
  - Every single prompt ends with: `"No text, no letters, no logos, no watermark. Natural skin tone, no blush, no red cheeks, no red ears."`

## Limitations
- This task authored prompt definitions (`plates.json`); actual rendering of image assets is deferred to downstream image synthesis jobs using diffusion/generation pipelines.
- NPC image files (`NPC-hoarder.png`, `NPC-pet-neighbour.png`, `NPC-uncle.png`) must be generated and placed in `/opt/MoonieXHQ/Work/khaohom-survival/long/ep01/stills/` before generating still plates `L1-S13`, `L1-S28`, and `L1-S29`.

## Blockers
- None.

## Skill learning
- - (none)
