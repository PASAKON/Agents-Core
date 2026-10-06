---
name: CTO_Procedure_Bedrock_SkyScene
kind: procedure
description: "PROCEDURE — Make one Minecraft Bedrock sky scene match its concept image in the running game, scored against a 90 target. Trigger on /CTO_Procedure_Bedrock_SkyScene and on \"ทำให้เหมือนได้ 90%\", \"match the concept image\", \"make the sky look like the concept\". Not for laying out worker lanes (CTO_Standard_Bedrock_WorkLayout)."
owner: CTO
created_by: agent
author: {role: cto, date: "2026-10-06"}
audience: [cto]
improved_by: []
aka: []
---

# One sky scene, matched to its concept image

The CEO, 2026-10-06: *"เอาท่าที่เกมทำได้เลย ทำให้เหมือนได้ 90% · อันไหนที่ เรื่อแสงทำไม่ได้ ให้ไไปอยู่ใน Taxture + VFX ได้เลย"*.
Match 90% with what the engine can do. What lighting cannot do goes to textures and VFX.
Also CEO 2026-10-06: capture every shot by script, look at ONE combined sheet once, tune in one pass.

Input: a scene (a stop id such as `T00`, scene #1, the dreamy day), its concept image, a MoonieX-Bedrock
checkout with the sky packs · Output: one sheet (concept next to game, similarity per band), the tuned files
committed with provenance rows, one learning fold · Tool: the table under "Tools".

## What it does

The game says how close the scene is, not a guess. A script puts a free camera at a measured spot. A resident
daemon on winbox takes the shot. `skymetric.py` compares two bands of the frame with the concept in Lab colour.
One tuning pass follows: the palette first (a script file, no client restart), then VFX and textures for what
the palette cannot reach. The loop exists because the CEO asked on 2026-10-06 to stop trial and error.

## When to invoke / when not

- Invoke when a scene has a concept image, a stop in `docs/testing/sky-tour.json` and a chosen camera spot in
  `docs/testing/sky-tour-spots.json` (if not: `tools/sky_spots.py find <STOP>`).
- Not for worker lanes and briefs (`CTO_Standard_Bedrock_WorkLayout`), button tests of a system (its item 9), or
  the first draft of a scene's art (lane work). It needs the winbox screen, so it needs the lease.

## What can reach what

Source: wiki `research/2026-10-05-bedrock-sky-visuals-limits.md` (mostly official docs; its labels apply).

| Band or element | Lever | Engine limit |
|---|---|---|
| zenith (`zen`) | `palettes.js` zenith colour, applied by script (`@minecraft/server-graphics`) | an input is not shown 1:1 |
| horizon (`hor`) | palette answers weakly; VFX haze `sun_glow`; sun texture | see Field notes |
| sun disc | `sun.png`, `sun_vv.png` | no size field; the sun quad bounds the texture |
| glow past the quad, rays | VFX particles `sun_glow`, `sun_rays` | particles only |
| cloud shape, rim colour | `clouds.png` | height, speed, thickness, direction fixed |
| air (petals, glints) | particles; sprite size | |
| stars, aurora | none native: particles or a cubemap | |
| whole-frame mood | colour grading (no keyframes; a script can change it) | |

## Tools

(A) Agents-Core · (B) MoonieX-Bedrock `tools/` · (S) the CTO session scratchpad `$S`, not in a repo yet (Field notes).

| Tool | Does |
|---|---|
| `scripts/pc-lease.sh` (A) | `status`, `take --who "<what for>"`, `give-back` |
| `scene1/test.sh <label> [clouds.png]` (S) | steps 2 to 8 for T00 in one run; the 2nd argument swaps `clouds.png` for an A/B |
| `scene1/deploy_sky.ps1` (S, runs on winbox) | unpack; `robocopy /MIR` each RP into the BDS dev folder AND the client's; BP into BDS; skips on a uuid mismatch |
| `join_lan.sh` (S) | restart the client, clear dialogs, click the LAN tile; each click follows OCR of a fresh shot |
| `mcmd.sh "<cmd>"` (S) | one console command through the bridge tunnel `127.0.0.1:18765` |
| `shotd_take.sh <name> <dest.png>` (S) | one screenshot from the resident winbox daemon, no focus change. The daemon ends itself after 8 h; `TIMEOUT <name>` means it is down (`shotd_start.ps1`) |
| `skymetric.py <round> [STOP ...]` (S) | the numbers below, from `caps/<round>/<STOP>.png` |
| `calib.py <STOP> <palette type> [--apply]` (S) | solve one stop's palette from the engine's measured response |
| `gridsheet.py` (S), `scene1/sheet.py` (S) | one sheet: a round of stops, or T00 variants |
| `tools/sky_tour.py go <STOP> --camera`, `reset` (B) | weather, time, forced type, free camera at the spot; `reset` returns camera and HUD |
| `tools/sky_spots.py find <STOP>` (B) | picks the camera spot, records every candidate |
| `tools/wire_scene1.py` (B) | rebuilds every shipped art file of scene #1; same inputs, same pixels |

**The metric.** Similarity = 100 − CIE76 dE per band, medians in Lab. `zen` = top 22% of the frame, `hor` = rows
30 to 50%, green foliage dropped. Target 90 (dE of 10 or less). Game shots lose 32 px at the top and 50 px at
the bottom (windowed client). Underwater stops (E16, E17) use the top and bottom thirds.

## Steps (numbered; each with the stop condition)

1. **Lease.** `./scripts/pc-lease.sh status`, then `take --who "cto: sky scene <STOP> match"` (ASCII only).
   Stop unless `take` printed `OK - the screen is yours until HH:MM`; on `FAILED` do not touch the screen. Never
   press ESC. Before the first in-game click ask the CEO for one typed sentence naming host, app and clicks (the
   classifier refused them on 2026-10-05).
2. **Deploy to BOTH copies.** `bash $S/scene1/test.sh <label> [clouds.png]`. It packs `sky_tex` RP, `sky` RP and
   `sky` BP; `deploy_sky.ps1` mirrors each RP into the BDS dev folder AND the client's own dev folder (same uuid
   and version, so the client uses its own copy). BP goes to BDS only; scripts run on the server. Stop unless
   five `ok ... files=N` lines print and no `uuid mismatch ... skipped` or `robocopy failed`. A BDS-only deploy
   proves nothing. A `palettes.js`-only change is BP: scp it to the BDS BP folder and `mcmd.sh reload`, as
   `sweep.py` and `calib.py` do.
3. **Restart.** `test.sh` runs `tools/mcb stop`, then `tools/mcb start --transport bds --server-dir
   'C:\mooniex\bedrock\bds' --world mooniex-sky --pack-sha "scene1-<label>"`, then waits 30 s. The client
   restarts in step 5, so an RP change always loads fresh. Stop if `mcb start` fails; step 4 shows it.
4. **Tunnel check.** `curl -s -m 5 http://127.0.0.1:18765/state` must answer. If not,
   `ssh -f -N -L 127.0.0.1:18765:127.0.0.1:8765 winbox`. Stop unless `/state` answers.
5. **Join.** `bash $S/join_lan.sh`. It clicks only the LAN tile (the block holding both `mooniex-sky` and
   `Dev's`), with integer coordinates under `LC_ALL=C`. Stop at `JOINED` and `mcmd.sh list` showing `There are
   1/`. Exit 3 (single-player dialog): a local world opened; give the lease back and look. `GAVE UP`: read
   `caps/join.png`. A Widgets panel over the game: kill process `WidgetBoard`, never ESC.
6. **Camera to the measured spot.** `(cd <worktree> && python3 tools/sky_tour.py go <STOP> --camera)`, then
   wait 15 s. Stop on any `FAIL` line. `no chosen spot` means run `sky_spots.py find <STOP>` first.
7. **Shoot the whole batch, with the overlay check.** `bash $S/shotd_take.sh <name> <dest.png>` for the base
   and every variant; after each, `tesseract <png> - | grep -iE 'been away|jump back|dressing room|resume game'`.
   A hit: rejoin (step 5), camera again (step 6), reshoot; twice at most. Rejoin before a batch if the last
   join is more than 10 min old. Stop when no shot shows those words and `mcmd.sh list` shows a player.
8. **Measure.** `(cd $S && python3 skymetric.py <round> <STOP>)`, or the row `test.sh` prints. Stop when every
   shot has a `zen` and a `hor` number. A number from a frame with an overlay, a menu, the desktop or no
   player is void; shoot it again.
9. **One sheet.** `python3 $S/gridsheet.py <round> <out.jpg> 4 192`, or `python3 $S/scene1/sheet.py <out.jpg>
   base:<png> v1:<png>` for T00 variants (full frame plus a 2x crop of sun and clouds, similarity on each
   panel). Stop when one image shows the concept next to every game shot.
10. **One look.** Open the sheet once. Write each gap as one line tied to a band or element (zen, hor, sun,
    clouds, air), with its number. No second look until the tuning pass is deployed.
11. **Tuning pass, palette first.** `python3 $S/calib.py <STOP> <palette type> [--apply]`. It shoots six pairs
    (a base, then the same palette with one of zen L, a, b, hor L, a, b moved 20 Lab), builds the 6x6 response
    matrix, solves by damped least squares, shoots two Newton steps and prints similarity per band; `--apply`
    writes the best palette line into `palettes.js`. Stop fitting palettes once `zen` is 90 or more. If `hor`
    is still below 90 after the two solves, do not run calib again; go to step 12. Look in the calib log for
    `idle overlay, rejoining` between a base and its moved shot: that pair is void.
12. **Then what the palette cannot reach: VFX and texture.** Use the lever table: sun haze and glow
    (`sun_glow`, `sun_rays`), sun disc (`sun.png`), cloud rims (`clouds.png`), air (sprite size). Stop when every
    change answers one gap from step 10 and all of them ship in ONE deploy. Art: the PixelLab brief is the last
    section of wiki `research/2026-10-06-pixellab-vfx-pixelart-references.md`; every rule there is an estimate
    (Field notes). Run PixelLab calls one at a time. A lane that needs the key cannot start on the Mac
    (`CTO_Standard_Bedrock_WorkLayout` Field notes). Scene #1's files rebuild with `tools/wire_scene1.py
    --blossom-draft <png> --palette <png>`; the drafts are archived at
    `/Users/gob/MoonieXHQ/Assets/MoonieX/Bedrock/sky/pixellab-drafts-2026-10-06` (SHA256SUMS). The CTO picks the
    option closest to the concept; options never go to the CEO.
    **Before touching an effect's look, project its spawn positions through the tour camera** (rule, 3 runs).
    `tools/sky_tour.py` puts the free camera 4 blocks ahead of the player and below the head, so an effect spawned
    round the feet sits behind the lens and one spawned round the head reads high: aurora and shooting stars spawned
    64-90 deg up and were never in frame, snow/fireflies/mist were 1-4% in frame, and the aimed sun haze landed
    0.12-0.18 H above the sun. The camera height below the head is not settled (1.6 vs 2.34 blocks). Test helpers
    `world()` + `px()` in `tests/js/sky_fx_near.test.mjs` do the projection. Runs: task-e7485779, task-222da532,
    task-4ba4a067.
13. **Confirm once.** Repeat steps 2 to 9 once with all changes together. Stop at `zen` and `hor` of 90 or
    more, or at a ceiling written down: band, number, levers tried, what the engine cannot do. Commit the
    files with their provenance rows in the same commit (`CTO_Standard_Bedrock_WorkLayout` item 4).
14. **Give the lease back** the moment the last shot is taken: `python3 tools/sky_tour.py reset`, then
    `./scripts/pc-lease.sh give-back`. Stop when `status` shows the lease free. If `give-back` prints `COOKIE RUN
    DID NOT COME BACK`, tell the CTO and do not report clean.
15. **Fold.** `ALL_Protocol_SkillAuthor` section 5: one line per lesson under `## Field notes` of this skill.
    First run `git log --since=1.day --oneline -- .claude/skills/CTO_Procedure_Bedrock_SkyScene/SKILL.md` and
    extend a same-day note instead of adding a twin. Stop when every number measured today sits in a note or
    a table, so nobody measures it again.

## Verify (the commands, and what "done" looks like)

```bash
S=<folder with the scene tools>   # 2026-10-06: the CTO session scratchpad
W=<MoonieX-Bedrock worktree>
bash $S/scene1/test.sh <label> | grep -E '^(ok |uuid mismatch|robocopy failed)'   # five "ok" lines only
curl -s -m 5 http://127.0.0.1:18765/state | head -c 200                           # JSON, not an error
bash $S/mcmd.sh list | tail -1                                                    # "There are 1/..."
for p in <dir>/*.png; do tesseract "$p" - 2>/dev/null | grep -qiE 'been away|jump back|dressing room|resume game' && echo "OVERLAY $p"; done   # prints nothing
(cd $S && python3 skymetric.py <round> T00)                    # zen and hor rows; similarity = 100 - dE
(cd $S && python3 gridsheet.py <round> <out.jpg> 4 192)        # prints "<out> (w, h) N stops"
(cd $W && python3 tools/provenance.py check packs/sky_tex && python3 tools/provenance.py check packs/sky)   # prints nothing
(cd $W && pytest tests -q -c /dev/null --rootdir=. --confcutdir=.)   # a worktree under Agents/Core needs these flags
```

Done means: a sheet with similarity on each panel; `zen` and `hor` at 90 or more, or a written ceiling; the
provenance check silent; the lease given back; the fold written.

## Rules

1. **HARD — winbox: take the pc-lease first, never press ESC, give the lease back the moment the screen work
   is done.**
   **Why hard:** irreversible — ESC on that box writes a hold file only a human clears, and the farm stays down
   for the night (`ALL_Rules_Winbox_PCLease` rule 1).
2. **HARD — the concept image is never uploaded to an outside service, never shipped and never traced.** Only
   palettes sampled from it leave the machine, as a `color_image` strip we build.
   **Why hard:** scope of authorisation — the standing Dreamy Skies rule of 2026-10-06; an upload cannot be
   recalled.
3. **HARD — paid spend needs the exact price and the CEO's OK first.** Free trial credits are fine.
   **Why hard:** money — PixelLab's free plan gave 40 generations; a call charged in USD stops the run.
4. Capture every shot by script, look at one sheet once, tune in one pass (CEO 2026-10-06). Each extra look
   is a round trip, and the frame drifts between shots.
5. The CTO picks the closest option to the concept, by the numbers and then by eye on the sheet. The CEO does
   not choose between options. Report picture first, numbers after.
6. Match what the engine can do. Stop fitting palettes at `zen` 90; give the rest to textures and VFX.

## Output format (the report)

```
sky scene <STOP> · concept <id> · label <label>
sheet: <path or Drive link> (concept next to game, similarity on each panel)
before: zen NN hor NN · after: zen NN hor NN · target 90      (NN = measured, never estimated)
levers: palette (calib, 2 steps) · <VFX or texture change> · ...
ceiling: <band> stops at NN because <measured reason>; left for <lever>, not tried
spent: 0 USD, N free generations · lease: taken HH:MM, given back HH:MM
```

## Failure modes seen (dated)

- 2026-10-06 — a rain-fog test pushed fogs to BDS only and proved nothing: the client runs its own copy of an RP
  with the same uuid and version (`deploy_sky.ps1` header). Step 2 deploys to both.
- 2026-10-06 03:00 — a click on the first `mooniex-sky` word opened the local world in single player. The join
  now clicks only the LAN tile (`join_lan.sh` header).
- 2026-10-06 19:3x — the Mac's `LC_NUMERIC` is af_ZA, so awk printed `735,5`; the click hit the taskbar's
  Widgets button and the panel covered the game (OCR read news and tickers). Integer coordinates under
  `LC_ALL=C` fixed it. Under `LC_ALL=C` the test `/Dev.s/` then never matched the game's curly apostrophe in
  `Dev’s`, and the join gave up after 40 steps; it matches `Dev` alone now (`join_lan.sh` header).
- 2026-10-06 19:2x — the Mac-side tunnel to the bridge died across a long break; every call was refused and the
  join gave up after 40 steps. `test.sh` checks `/state` and reopens it now.
- 2026-10-06 — the "You've been away" overlay came back about 13 to 17 min after a join, twice: with the F15
  keep-alive on (shot 6, 04:48) and with both pause options set to 0 and F15 off (shot 7, 05:38). Neither
  stops it; the keep-alive stays in `shotd.ps1` and helps nothing. OCR and rejoin do. Calib run 2 hit it on shot
  d4 (`caps/f15/idletest.log`, `caps/pausefix/log.txt`).
- 2026-10-06 — with nothing changed the frame drifts. Calib run 1: zen L 61 to 48 over five shots. Run 2: base
  zen L 73, 74, 73, 70, 68, then 73 again after a rejoin. A 12 Lab step moved the zenith by under 2 L. So a base
  shot sits before every move and the step is 20 (`calib.py` header).
- 2026-10-06 — calib run 2, pair d4 (hor a) straddled an idle-overlay rejoin: hor chroma 18 to 45 in that shot
  only. Its matrix column is not trustworthy, and both Newton steps used it (`caps/calib2_t00.log`).
- 2026-10-06 02:30 — the client closed mid-sweep and the remaining rows measured the desktop. `sweep.py` and
  `calib.py` now stop when `mcmd.sh list` shows `There are 0/`.
- 2026-10-06 — PixelLab's free plan runs one generation at a time: two calls sent together got HTTP 429
  (`petal_b`, `blossom_a`, not charged). Send them one by one (`calls.jsonl` in the draft archive).

## Field notes

- 2026-10-06 [MISSING] §Step 12 — sun haze: measure it as ring colours in sun-disc radii (upper half-plane, 1.0 to 7.3 radii) against the concept. On a pale sky use `particles_blend`; `particles_add` only brightens. Mock-up distance to the concept (lower is closer): base 31.3, V5-a 22.8, V5-b 14.1, V5-c 13.3; V5-c is the option wired into scene #1. One scene, a mock-up, not yet seen in game · evidence: task-811d6a5f, merge 8b81b3d · status: pending
- 2026-10-06 [MISSING] §Step 12 — tint alone carries V5-c to T00, E07 and E14; E06, E08 and E12 also need a size or alpha change. Mock-up transfer check, not in game · evidence: task-811d6a5f, a0c3c28 (the haze tint holds 1,1,1 at E07 as the check found) · status: pending
- 2026-10-06 [MISSING] §What can reach what — the game sun disc is about 182 px across at 1920x1080 (concept 3.9% of the width, game 9.5%). The sun quad is about 343 px, so glow past about 1.9 core radii is not sun.png's job. One scene, one resolution · evidence: task-b3540bea · status: pending
- 2026-10-06 [MISSING] §Step 12 — cloud colour is the texture RGB times an engine multiplier of about (0.91, 0.92, 0.94): keep the cloud RGB bright and put the warmth in the rims. If it holds, colour pixels in clouds.png do count in game, which the 2026-10-05 research left open (its question 4) · evidence: task-b3540bea, wire_scene1.py clouds_from_draft · status: pending
- 2026-10-06 [MISSING] §Tools — the texture lane's constants HORIZON and OLD_CLOUD_BOXES were read by hand for T00 and E08 only; another scene needs them read again · evidence: task-b3540bea · status: pending
- 2026-10-06 [MISSING] §Step 11 — palette ceiling on T00. Calib run 2: base zen 91.2, hor 74.8; after two Newton steps hor 83.0 but zen 87.4. In that matrix the horizon barely answered its own L and b inputs, so horizon warmth looks like a VFX haze and sun-texture job, but no run has shown VFX closing it. The d4 column was void (see Failure modes) and run 1 had no usable matrix. calib.py's header also says the engine puts green into the horizon and caps night brightness, with no numbers kept · evidence: caps/calib2_t00.log (session scratchpad), calib.py · status: pending
- 2026-10-06 [MISSING] §Step 12 — floating-air density: "scale the rate so on-screen density matches" is the wrong lever. Over 80 seeds the count in view is angular and barely depends on spawn radius; sprite size carries coverage (AIR_SCALE .76 gives 1.00x coverage, 0.94x count, rate unchanged). A simulation, not measured in game · evidence: task-20215157, wire/exp_density2.py · status: pending
- 2026-10-06 [MISSING] §Step 12 — the wiki's PixelLab brief is estimates until a draft proves them. Round 1 (6 free generations) used a keyword prompt, `color_image`, `seed` and `no_background` only. Round 2 (clouds from a code-drawn sketch at `init_image_strength` 450, 500, 550) copied the sketch: mask agreement 1.0 and colour copy 0.994 to 1.0 in 4 of 4 drafts, every colour exactly in the palette strip. So 450 and up recolours, it does not redraw; 350 is queued in jobs3.json, not run. Not yet judged by eye · evidence: pixellab/out2/metrics.json (session scratchpad, 20:06), calls.jsonl in the draft archive, research/2026-10-06-pixellab-vfx-pixelart-references.md · status: pending
- 2026-10-06 [MISSING] §Step 7 — with nothing changed, zen chroma read 34, 43, 45, 45, 45 on five shots 2 min apart (the first 2 min after the camera was set; zen L stayed 63). Cause unknown. A shot taken in the first minutes after a join may not match a later one · evidence: caps/f15/idletest.log (session scratchpad) · status: pending
- 2026-10-06 [MISSING] §Tools — the Mac tools sit in the session scratchpad, not in a repo. `test.sh`, `sheet.py` and `skymetric.py` are bound to scene #1 (T00 uses E07's concept image) and `test.sh` runs `C:\mooniex\stage\contentlog.ps1` without copying it. Before this skill merges, commit them to one MoonieX-Bedrock folder and make the stop id an argument · evidence: scene1/test.sh, skymetric.py CONCEPT map, read 2026-10-06 · status: pending
- 2026-10-06 [WRONG] §Measure — a shot taken right after a fresh BDS start + join measures the resource-pack defaults, not the palette: the client drops graphics overrides sent while it is still loading in (T00 fresh L57 C50 = sky reset L56 C53; after a /reload or reset + force L48 C24). So calib.py/sweep.py (they /reload) measured the palette all along, and test.sh's after_a/after_b 69/49 did not. Fixed in the pack: a first spawn re-applies at 100 and 600 ticks (MoonieX-Bedrock 2b1a2b2; fresh join then measured L48 C24) · evidence: scratchpad caps/reloadexp A0 R0 X1 N0 F0 F1 J1 · status: pending
- 2026-10-06 [MISSING] §Join — tesseract read "Dev's" under the LAN tile at confidence 28, below the old > 30 filter, and the join looped 40 steps without a click. join_lan.sh now matches "Dev" at any confidence but only within 400 px of the tile's own x · evidence: caps/join_tile.tsv 21:1x, scene1/join_joinfix2.log · status: pending
- 2026-10-06 [MISSING] §Assets — every non-cloud sprite follows vanilla's measured style (hard alpha, 2-3 tones, vanilla ramps, 3-10 px shapes); the rules live in tools/sprites/style_lint.py + tests/test_sprite_style.py, the drawer in tools/sprites/draw_vanilla_style.py. Before baking a colour into a sprite, grep which particles the BP script tints per day (the leaf is grey x variable.color) · evidence: MoonieX-Bedrock 419e9ce, 588bbbb, 2cd154f; CEO order 2026-10-06 · status: pending
- 2026-10-06 [MISSING] §Tools — the old generators (wire_scene1.py, gen_sky_particles.py, gen_sky_textures.py) silently overwrote hand-redrawn sprites; they now refuse without --legacy-sprites. List every writer of packs/ files before changing an asset · evidence: sprite lane report, 419e9ce · status: pending
- 2026-10-06 [MISSING] §Tune — the sky's brightness is set by `sunIlluminance`, not by the zenith/horizon colours. At T00 (dreamy, t=1600) lux 100/200/400/800 gave zenith L48/54/62/72 and the whole frame L43/48/56/66, while chroma fell 25/20/14/9. `skyIntensity` 1.5 and 2 and a 4x `ambientIlluminance` moved nothing (dE < 1). Grading `temperature` shifts the hue of the whole frame (4500 K: zen h41 C9; 9000 K: zen h286 C25), so it cannot give a cool zenith over a warm horizon; that split must come from the colour inputs. Order: lux first to match the whole-frame L, then solve the colours at that lux · evidence: scratchpad caps/sweep_light.log, caps/sweep_light2.log · status: pending
- 2026-10-06 [WRONG] §Measure — the band median (zen = top 22%, hor = rows 30-50%) mixes the concept's blue sky with its pink clouds into a lilac (T00 A4A2C3) that no pixel has. Tuning the game sky to it scored zen 89.8 / hor 81.7 and looked nothing like the concept by eye: a flat lilac haze against a blue sky with pink clouds. Split the concept first (concept_split.py): T00 clear sky L69 C36 h266 in rows 1-17%, pink cloud L79 C23 h358 and warm haze L86 C21 h57 in rows 8-40%. The sky colours target the clear sky; cloud and haze are VFX targets. Look at one sheet before believing any band number · evidence: scratchpad scene1/T00_sheet_light.jpg, MoonieX-Bedrock 29589b2 · status: pending
- 2026-10-06 [MISSING] §Frame — check the sun's place in the frame before tuning colour: T00's chosen spot looked 40 degrees right of the sun (yaw -50), so the sun and its light never entered the shot. Measure the centroid of the brightest 0.2% of pixels in concept and game (sunpos.py); match x by yaw and y by time of day, not pitch, so the horizon stays where the concept has it. T00 now yaw -73, time 600: sun x36% y31% vs concept x35% y32% · evidence: MoonieX-Bedrock 6fe8ab0, caps/reloadexp/time600.png · status: pending
- 2026-10-06 [WRONG] §Assets — stepped glow bands (≤6) for sun_glow and sun_rays look like broken rendering at sky scale: huge translucent polygons over half the frame, plus a pale square around the sun. Only one in-game look so far (n=1); the rule stays until a smooth-glow variant is compared on the same sheet · evidence: scene1/T00_sheet_frame.jpg (sun_frame, sun_ray8) · status: pending
- 2026-10-07 [MISSING] §Tune — before you tune the sky colour, run `key_weights(t)` for the stop's tick. At T00 (tick 600) the .75 zenith key carried 0.9 of the sky. While that key was lilac (7476BD), rayleigh up to 8 still gave a grey-lilac top band (L75 C10 h3). A blue key (359DE3) plus rayleigh 8 and sun mie .5 gave L71 C19 h276 (concept L70 C20 h286). That was one sheet of 6 shots, judged by eye · evidence: MoonieX-Bedrock sky-tune 86f9607, scratchpad scene1/T00_sheet_glow.jpg · status: pending
- 2026-10-07 [WRONG] §Assets — the earlier note's fix held. A smooth-alpha sun_glow (flat ramp colours, alpha fading to 0 at 0.88 of the radius) plus rays with black transparent texels removed the pale square that the stepped variant drew left of the sun (A/B on one sheet). The ring is still too wide: rings at 10/15/20% of the height measured 90/88/86 in game against 85/75/73 in the concept · evidence: sky-glow-b b14ece6, merged 39392ad · status: pending
- 2026-10-07 [COSTLY] §Gates — I committed a tour change (T00 tick 1600 to 600) without running the gates. It broke 2 node fx tests, because the sun haze tint is keyed on the stop's tick. The peer caught it at merge. Run all 4 gates before every commit that touches sky-tour.json or palettes.js · evidence: 6fe8ab0, fixed in fcb1270 · second sighting 2026-10-07: the reframe (T00 600 to 850, E14 23600 to 23990) failed 3 node fx tests for the same reason; the gates ran BEFORE the commit this time, so the tint keys went to the fx lane owner by letter instead of a red merge (sky-frame 939b222). Two runs agree: tint keyed on a tick breaks with every tour move; keying it by stop or by sun elevation would end it · status: pending
- 2026-10-07 [MISSING] §Verify — find the sun only above the horizon (T00: rows 0-55%), rank pixels after a 1% blur, take the middle of a clipped 255 plateau, and accept only a compact (spread ≤3% of height) near-white (blurred grey ≥235) blob, else n/a. The concept T00 disc is at x34 y23, not 35,32: the old centroid was pulled by scattered specks and the water reflection; the game sun reads x35 y29 · evidence: task-f6300207 d919154, REPORT addendum · status: pending
- 2026-10-07 [MISSING] §Verify — headline sky = raw × min(1, clear share game/concept), n/a under 0.25 × the concept share; always print raw and both shares beside it (V_b raw 73.9, headline 46.5; F_ray8_mie05 75.2) · evidence: task-f6300207 e8096ae, owner decision cto-f39cb080 · status: pending
- 2026-10-07 [MISSING] §Frame — a projection model predicts the sun's place without a shot: vertical FOV 60 (winbox options.txt `gfx_field_of_view:60`), so 91.5 deg horizontal at 16:9; x = 0.5 + tan(bearing - yaw) / (2 tan 45.75), y = 0.5 - tan(elevation + pitch) / (2 tan 30); Minecraft celestial angle a = f + ((1 - (cos(pi f) + 1) / 2) - f) / 3, f = frac(t/24000 - 0.25), sun in the east-west plane, moon opposite. It matched base22's measured sun on T00 (x35 y29 vs x35 y27-29), E06 and E07 (x63 vs x63), E08 (x63 y13 vs x62 y11) and E12 (x68 y36 vs x68 y35), and showed 13 of 14 disc stops framed off the concept (E06/E07/E08 sun x62-63 where the concept has x28-34). `frame.py` (session scratchpad) solves yaw for x and tick for y, pitch kept, inside the stop's day/night slot and moon-phase day, and rewrote both tour files in one commit. Frame every stop this way before any colour pass; the model is checked on day stops only, the moon not yet · evidence: MoonieX-Bedrock sky-frame 939b222, caps/base22 · status: pending
- 2026-10-07 [MISSING] §Step 12 — before tuning a VFX glow, shoot it off (`scriptevent mooniex_sky:fx sun_glow off`, then `sun_rays off`) at the same spot and score all three. T00 (yaw -73, tick 600): glow on sky 86.4, zen L63 C48, rings 5/10/15/20 = 100 92 92 90, haze share 22%; glow off sky 91.6, zen L66 C44, rings 100 93 95 91, haze 10%; glow+rays off sky 92.2; concept rings 93 86 81 70, haze 22%. So the pale wide ring was engine sky and horizon brightness (a palette job), not the sprite. The glow gave the warm haze share the concept has, but cost 5 points of zenith by reaching the clear-sky rows. One stop, one shot each · evidence: caps/post22 (session scratchpad), pack 86f9607 · status: pending
- 2026-10-07 [MISSING] §Tools — a palette solver built on finite differences reads the model's output as float Lab, never rounded to 8 bits, and divides each difference by the step the 8-bit key really took: rounding put up to 0.5 Lab of noise in every 4 Lab step and a nominal +4 L on 549EF5 landed with -0.8 a / +0.9 b, so a 7 Lab one-stop ask missed by 1.41 (0.41 after the fix). A weather mix is solved for what the clear pass left of the stop's ask, not the whole ask again. Give every ported solver a test that it meets a known ask · evidence: task-7b0ba85c, MoonieX-Bedrock 20bc0df (base22 weighted miss 1911 -> 1757, no change 5501) · status: pending
- 2026-10-07 [MISSING] §Tools — an OCR anchor word in a click script tolerates one misread letter (`/De.?v/`), and the real failing tesseract dump is kept as the test fixture: "Dev's" read as "Deyv's" stalled E11's rejoin 4 min; the old match printed nothing on that dump, the new one 81 735 · evidence: task-41b997d2, MoonieX-Bedrock 5c51e71 · status: pending
- 2026-10-07 [MISSING] §What can reach what — sun_glow is emitted at `logic.js sunOffset()` (nominal arc, 30 blocks), not on the sun disc: at T00 its centre sits 11% H below the sun, so a glow limit written as "N% H above the sun" (the task-9d4e21d1 brief did) lands in the wrong place; the limit is in texture space (clear-sky rows start 10.5-15 texels above the glow centre). The billboard `size` is the half size, the blend fits as linear light, and two particles are alive (phase 45). Model a glow change with `tools/skytune/ringfit.py` before shooting · evidence: task-9d4e21d1 (model vs real glow-on frame: 0.05 L, 0.09 C, 0.6 haze points), MoonieX-Bedrock sky-ring 901b6bf · status: pending
- 2026-10-07 [COSTLY] §Tools — read a particle's JSON components before inferring its billboard orientation from frames: sun_rays has `minecraft:particle_initial_spin` (random 0-360), so ~15 CPU min of template matching on it could not show the `lookat_xyz` roll; only a spin-free asymmetric test sprite in game can · evidence: task-9d4e21d1 · status: pending
- 2026-10-07 [WRONG] §Frame — the projection model puts the sun at 12.43 deg elevation at ticks 0 and 12000 (it sets at 12785 and rises at 23214), not at the horizon as the task-de2d51db brief said; `frame.py` and `elfit.py` now live in `tools/skytune` with tests pinning this (sky-frametool 835c81f), and elfit on base22 + frame22 gives 12 day rows, d +0.9 to +2.9, mean 1.6 (T00 and E07 share a concept) · evidence: task-de2d51db · status: pending
- 2026-10-07 [MISSING] §Frame — `frame.py` maps yaw and elevation to x and y separately, which drifts off-axis: a point more than ~20 deg off the centre column lands up to ~13 points of y wrong (T00 cloud row r4: y27% in frame.py, y14% in an exact pinhole, game rows 5-25%). Fine for a sun near the centre; use an exact pinhole for VFX layouts · evidence: task-69457481, docs/design/sky/cloud-bank-framing.md · status: pending
- 2026-10-07 [MISSING] §Step 12 — before tuning where a VFX effect sits, confirm it runs at that stop's type: `activeRates()` plus the go.log status `type=`. Four of five "missing cloud bank" stops (E06 golden, E07/E13 pastel_dream, E08 crisp_clear) never spawned one, because `cloud_bank` runs on `SUN_HAZE_TYPES = ['dreamy']` only · evidence: task-69457481 · status: pending
- 2026-10-07 [COSTLY] §Verify — shot timing: every bridge `/cmd` waits its 5 s capture window + 0.25 s echo, so the force lands ~35 s before the capture, not the 15 s batch.sh SETTLE suggests; derive timing from `go`'s command count and check it against batch.log (71 s from go to shot at frame22) · evidence: task-69457481 · status: pending
- 2026-10-07 [MISSING] §Verify — scoring a VFX by a strict colour class reads ~0 for an effect that is present but hue-shifted (T00 cloud bank: strict class 8% vs model 35%, pink-or-lilac 41% vs 52%, hue 320 vs 355); also measure a relaxed class (h300-30, C>8, L>55) to tell absent from wrong colour · evidence: task-69457481 · status: pending
- 2026-10-07 [WRONG] §Verify — a worker's "sprites 0 and 2 are h320 in the PNG" was false: re-measured, all three cloud sprites sit at median h358 (body #EDB5C6 is half the texels); in the T00 game shot the cloud-like pixels read h350 and the "320" mixed lilac sky (C28, above any sprite tone) into the cloud boxes. Re-measure a colour claim on the shipped PNG and on a cloud-only pixel class before changing a generator · evidence: task-55fd162b REPORT, task-69457481 · status: pending
- 2026-10-07 [MISSING] §Frame — `EL_BIAS` 1.6 (game sun above the model) was fitted through frame.py's separate yaw/elevation projection and holds only there; an exact pinhole on the same five morning discs gives +0.47 deg (0.37-0.60). Anything placed in 3D (sunOffset, a particle aim) takes the pinhole value · evidence: task-4ba4a067, docs/design/sky/sun-aim.md · status: pending
- 2026-10-07 [MISSING] §Verify — `sky_tour.py` puts the player 4 blocks behind the free camera (head 2.34 blocks above it), so every head-anchored effect (sun haze, cloud bank, air) has parallax in tour frames: once sunOffset was aimed at the real sun, the glow landed 0.12-0.18 H above the sun in tour shots while it fits in first person. Confirm head-anchored fx in first person, or with the player at the camera spot · evidence: task-4ba4a067 (checked by hand: +7 deg at 30 blocks). Cause, read in code 2026-10-07 02:30: the old tp kept the camera's y while 4 blocks back, and the player (not flying) fell to the ground there, so the head offset changed from spot to spot; the three workers measured different heights (1.6, 2.34). Fixed in the harness, MoonieX-Bedrock ed1c134: `gamemode spectator @a`, then tp the feet to camera y - 1.62 at the camera's x/z, so the eyes sit on the camera. `reset` sends `gamemode default @a`. BDS accepted it (02:40). Not yet confirmed by a shot · evidence: sky-tourhead ad97811, confirm22 batch · status: pending
- 2026-10-07 [MISSING] §Step 12 — nightfx and nearfx both found their effects invisible only by placement (spawned outside every tour frame), nothing wrong in colour or size; with the sun-aim parallax that is 3 runs, promoted to the Step 12 rule · evidence: task-e7485779, task-222da532, task-4ba4a067 · status: promoted
- 2026-10-07 [MISSING] §Measure — frame facts the workers had to rediscover: a billboard `size` is a half-extent; the game-shot crop is rows 32..H-50, then a centred 16:9; the frame top is pitch + 30 deg (VFOV 60) · evidence: task-e7485779 docs/design/sky/night-fx.md · status: pending
- 2026-10-07 [MISSING] §Measure — a blob census of a whole game shot counts terrain texture (E11: 2222 blobs of median 3 px, all snow blocks); restrict it to the sky rows or use the spawn model · evidence: task-222da532 · status: pending
- 2026-10-07 [MISSING] §What can reach what — rayleigh_strength is the lever for a grey day sky, not the zenith colour. Sweep, one stop per row, rejoined per stop, every shot OCR-clean, zen L C h against the concept: E06 golden 1: L59 C9, 4: L72 C15 h335, 8: L78 C19 (concept L69 C13 h329). E07 pastel 1: L57 C15, 4: L66 C25, 8: L70 C29 (concept L71 C21). E08 crisp 1.4: L48 C35, 4: L56 C47, 8: L60 C52 (concept L61 C53). E03 starry_dark night 1: L2 C1, 8: L6 C9 (concept L7 C36). E12 golden sunset (tick 11990) only gets paler: 1: L59 C7, 4: L70 C5, 0.5: L55 C10; sun mie 4 adds nothing (L59 C8). No rayleigh or mie value gives a sunset its rose chroma (concept C39 h12): that goes to VFX. A rayleigh keyframe object ({.2: 4, .25: .5}) at 11990 read L67, between the 0.5 and 4 scalars, so whether the setter takes keyframes is unproven; ship scalars · evidence: scratchpad caps/raysweep.log, caps/ray12.log; MoonieX-Bedrock 01c01e2 · status: pending
- 2026-10-07 [COSTLY] §Step 7 — `tools/skytune/sweep.py` has no idle-overlay check. Run 1 of the rayleigh sweep (5 stops, about 40 min) was void: the overlay dimmed the frame (E06 base L30 against L59 after a rejoin). Wrap it: `join_lan.sh` before each stop, then tesseract every shot · evidence: scratchpad raysweep.sh, caps/sweep/e06_check.jpg · status: pending
- 2026-10-07 [MISSING] §Step 12 — a world-fixed ring of discs needs a spawn stride coprime with the slot count, checked against how many slots low quality leaves dark at the scene's REAL rates (fireflies were 14/s on the base, not the 8 an older table said, which raised the dark slots from ~16 to 27); milky_way uses 84 slots, stride 29 · evidence: task-a7541a42 · status: pending
- 2026-10-07 [COSTLY] §Measure — when the tour camera geometry changes (sky_tour spectator, eyes on the camera, ed1c134), every offline fit of objects within ~100 blocks needs a re-run; keep each worker's simulator scripts in the brief's scratch folder so the re-run is one command (the night worker re-ran aurora, meteors and the band; the CTO re-ran the mist band: 95-100% covered) · evidence: task-a7541a42, task-222da532 · status: pending
- 2026-10-07 [COSTLY] §Tools — `skymetric.py <round> <STOP>` rewrites `caps/<round>/metric.json` with that one stop only, so every tool reading the round afterwards (multitune, famtune) sees one stop: famtune printed "reaches no scored stop" for every family on frame22. Rebuild the round with `tools/skytune/scenes/batch_metric.py metric <round>`; measure a single stop into a scratch round, never the batch's · evidence: caps/frame22/metric.json held only T00, rebuilt 2026-10-07 03:0x · status: pending
- 2026-10-07 [COSTLY] §Tools — shotd ends itself 8 h after its start, and a batch does not check its age: confirm22 aborted at E16 when the join got "no shot" (E16, E17 never shot). Before a batch longer than a few minutes, restart it (`ssh winbox 'powershell -NoProfile -ExecutionPolicy Bypass -File C:\mooniex\desktop\shotd_start.ps1'`) unless it started under 6 h ago · evidence: caps/confirm22/batch.log, restarted 03:27 · status: pending
- 2026-10-07 [MISSING] §Step 11 — `paletteFor` overwrites one zenith key with a sampled target for dreamy/normal stops in five families (warm_dry .25, cherry .75, cold .5, swamp .5, peaks 0), so multitune's Jacobian through that key is 0 and those stops get almost none of their ask (E15 swamp, E18 cold on frame22). Solve the family targets separately: scratchpad `famtune.py <round> --apply` after `multitune.py --apply`, 3 Lab per family, ridge .2, clip 25, ask = what the worktree left over HEAD. On confirm22 it moved cold 13255C to 233373 and swamp 031958 to 001E86 · evidence: MoonieX-Bedrock 9e44f2f · status: pending
- 2026-10-07 [MISSING] §What can reach what — in rain and thunder the zenith colour and the weather mix colour do not move the sky (E09 zen L50 a2 b-4 in both frame22 and confirm22 after the mix went 9690AF to A3ABF4; E10 L42 likewise), as wiki research 2026-10-05 §8 predicts (Vibrant Visuals draws a static classic sky in weather but still applies colour grading). Highlights + Midtones colour grading gain does move it, close to linearly in linear RGB: E09 gain (1.06, .9, 1.5) took zen C4 to C22 at h302 (concept C25 h302), E10 (.7, .55, 1) took C5 to C21 at h303 (concept C47). Set gain from the concept/game linear-RGB zenith ratio; a sweep of 3 variants on 2 stops is enough to check the response · evidence: caps/gain.log (scratchpad, backed up to Assets/MoonieX/Bedrock/sky/scratch-cto-f39cb080-2026-10-07), MoonieX-Bedrock 909f718 · status: pending
