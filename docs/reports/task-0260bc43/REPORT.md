# task-0260bc43 · VESPER INLET script B v2 and Omni Flash 1.2 shot grid

Outputs (outside the repo, as the task named them):
- `/opt/MoonieXHQ/Work/lituya-trailer/M4/SCRIPT_B_v2.md`
- `/opt/MoonieXHQ/Work/lituya-trailer/M4/SHOTGRID_omni12.md`
Inputs were read only. No media, no spend, no browser.

## Diff summary (v1 to v2)
1. **Music.** First score note moved from 44 s (39.6%) to **81.0 s (73.0%)**, on the cut to B19, the boat turning into the wave. Seconds 0-81 now run on bed, a hull-knock foley pulse, rock thunder bursts, a far town siren (72-78 s, new, sound only), and a sub drone capped near -32 LUFS. The hit at 44 s lands on sound alone, with a 0.7 s dip before it and an 8 dB dip at 80-81 before the score. Score stops dead at 93.0 (into BLACK), is absent 93-98, and returns as one held low note from 98.0. Rewritten: beat sheet rows, "Sound design", the sound cells of B10, B11, B12, B14, B15, B16, B17, B18, B19, B20, BLACK, B21, B22. Story, shots, timings and all 97 spoken words are unchanged.
2. **Clip grid.** 22 shots become **20 clips, 3-15 s in 1 s steps, 119 clip-seconds** (109.0 s used plus the 2.0 s edit-made black = 111 s). Merged: B03+B04 (C03, 10 s) and B11+B12 (C10, 6 s). B09/B13/B14 stay alone but grow to 7/6/7 s so each line ends 3 s before the clip does (standard rule 13). B16/B17/B18 are three 3 s clips.
3. **Credits (all UNVERIFIED, FelloAI rates):** 119 cr at 360p (1 cr/s), 357 cr at 720p (3 cr/s); with 2.5x retakes 297.5 and 892.5. Cross-check from our own Omni 1.1 reads (1.5 cr/s at 720p, 0.75 cr/s at 360p): about 179 and 89 cr, so the FelloAI 720p rate may be 2x high. Not 1.2 data either.
4. Housekeeping: the title-card note (46-50 s) moved from B11's cell to B10's, where those seconds are. Lip-sync table gains a clip column and new clip lengths.

Self-check script (scratchpad, not committed): shot table contiguous to 111.0 s, 22 shots, 20 clips, use matches grid, no dialogue overlap or crossing the hit, every lip-sync line ends 3 s before its clip, no long dash in either output. Result: no errors.

## Decisions for the CMO
- **Final wide and long face are 10 s; the 16:9 formula wants 12 s or more** (rules 12 and 15). Raising B15 or B22 to 12 s makes runtime 113-115 s (still inside 90-120) but changes shot timings and the D11/D15 cue times, so I did not do it.
- **D08 starts 0.3 s before B09's picture** (a J-cut), which fights lip-sync. Open for the lip-sync test: open the clip mid-word, or move D08 to 40.0-43.6.
- **Siren** at 72-78 s is a new sound element (diegetic, Mag set it off). Drop it if it reads as music.

## Not checked / risk
- Credit rates are FelloAI's, not read off our Flow UI; Omni Flash 1.2 may not even price like 1.1. Every credit number is a placeholder until one 360p estimate is read before Submit.
- No prompt was fired. Whether Omni 1.2 honours the internal hard cuts in C03 (at 6 s) and C10 (at 2 s), the 1.5 s action in the 3 s clips, or the quiet tail is untested; fallbacks are written in the clip notes.
- Sound targets (LUFS, dips, "no music before 81 s") are design intent, never heard or plotted. The "music test" (nothing hummable, no tempo) is my definition, not a measured rule.
- I did not read the wiki IRON-RULES page (the `org:` wiki was not available in this session); §37, §39 and §51 were applied from the task text. The film-study formula was read to line 630 of 762; the sample story and QC table after it were not needed.
- Prompt blocks use `{{...}}` markers for shared passages; they are drafts, not generated paste files, and the CAST lint has not been run.
- SKILL-OVERRIDE: CMO_Standard_Film_PromptFormat :: rule 13 quiet tail :: applied only to the three clips that carry a spoken line (7/6/7 s); the 17 silent clips are not padded by 3 s :: padding would add about 51 clip-seconds with nothing to protect, since all voices are laid in the edit.
- SKILL-OVERRIDE: CMO_Standard_Film_PromptFormat :: section 2 reference line `@TAG — NAME` :: wrote `@TAG - NAME` with a hyphen :: IRON-RULES §39 bans the long dash in script text.
