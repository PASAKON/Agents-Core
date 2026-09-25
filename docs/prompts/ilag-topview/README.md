# ILAG TopView trailer: shot prompts in the «Sorry, Sir» house format

One file per shot, two zones (NOTES never pasted; PASTE block between the arrows). The rules are the
«Sorry, Sir» ones, not new ones: `docs/prompts/absence/PROMPT-STYLE.md` and `AUTHORING-RULES.md`.
Tech header first · every @ reference declared ONCE with a job, then called by one fixed name
(THE YOUNG ONE, THE ELDER, THE STRONG ONE, THE MOUNT, THE THREE RIDERS) · `[Ns]` beats · a manner tag
of five words or fewer before every quote · AUDIO stated · colour grade block (DAY / TURNING / DARK) ·
CRITICAL NEGATIVES, then the house wall.

The files are GENERATED: edit `build.py`, run `python3 docs/prompts/ilag-topview/build.py`, never hand-edit
a `m*.txt`. `build.py` refuses a block where an @ appears twice. `P1-ALL-MAIN-SCENES.txt` = all 13 in one file.

Before pasting any block, the «Sorry, Sir» pre-fire grep must match only the two marker lines:
`grep -nE '⚠️|✅|\(CE[OT]|\(CTO|20[0-9]{2}-[0-9]{2}|take [0-9]|GH #|\.md|\.txt|\.MP4|\.png|chip|plate|Elements panel|UUID|paste|operator|spoken words|Fire |Cuts against|as S[0-9]'`

P1 = the 13 main scenes (`m01`..`m13`, SCRIPT.md draft 2), for our MiniMax H3 studio at 360p. P2 (extra
angles) and P3 (B-roll) follow once P1 passes (CEO: main scenes first).

## The Elements (create each once in the studio's Entities page, then type the @ handle)

All files are on Drive, `YT: ILAG/รอตั้งชื่อ (Topview Wan3 Challenge 2026)/Element/`.

| @ handle | Kind | Drive file | What it is |
|---|---|---|---|
| @Young | character | Character/`ref-Young.png` | the child (full body) |
| @Elder | character | Character/`ref-Elder.png` | the elder (full body) |
| @Strong | character | Character/`ref-Strong.png` | the big green man (full body) |
| @Villagers | character | Character/`ref-Villagers.png` | six villagers in one photo, numbers removed |
| @Manta | character | Character/`ref-Manta.png` | the manta with the driftwood seat (hero view) |
| @Lantern | prop | Prop/`ref-Lantern.png` | shell lantern, glowing |
| @LanternDark | prop | Prop/`ref-LanternDark.png` | the same lantern, dead |
| @Pole | prop | Prop/`ref-Pole.png` | steering pole |
| @Necklace | prop | Prop/`ref-Necklace.png` | seed-husk necklace |
| @GlassSpiral | creature | Location/`ref-GlassSpiral.png` | glass creature, spiral |
| @GlassCathedral | creature | Location/`ref-GlassCathedral.png` | glass creature, dome of veils |
| @GlassHalo | creature | Location/`ref-GlassHalo.png` | glass creature, rings |
| @GlassBloom | creature | Location/`ref-GlassBloom.png` | glass creature, flower |
| @Mountain | creature | Location/`crt_mountain_horizon_v3.png` | the shape on the horizon, no eyes |
| @Eye | creature | Location/`crt_eye_v4a.png` | the face and both eyes |
| @Village | location | Location/`loc_village_above_A_v2.png` | the village from the water |
| @Dock | location | Location/`loc_village_above_B_v2.png` | the village from above, the manta dock |
| @OpenSea | location | Location/`loc_open_sea.png` | calm open sea, close moon |
| @Pillars | location | Location/`loc_storm_pillars_A_v3.png` | the storm pillars |
| @Line | location | Location/`loc_deep_line_v2.png` | the line: clearest vs pitch black |
| @ClearWater | location | Location/`ref-ClearWater.png` | the clearest water, empty seabed |
| @BlackSea | location | Location/`ref-BlackSea.png` | the pitch-black sea under a purple storm |
| @Waves | location | Location/`loc_giant_waves_v2.png` | the colossal wave |
| @Planet | location | Location/`planet_from_space_v3.png` | the split planet and its moon |
