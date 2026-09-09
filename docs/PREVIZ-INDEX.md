# «Sorry, Sir» — Blender previz index

Free camera reference built in Blender (no credits spent). Each MP4 carries the
CAMERA ONLY — grey cylinders are proxies, never people. Any prompt that attaches
one of these must also carry the negative `no proxy rendered as an extra person`,
and must mention the file exactly ONCE as `@Video 1` (platform limit).

**Use a previz only for a scene that is still UNSHOT.** A scene with a delivered
keeper ignores its previz entirely unless the CEO orders a reshoot.

| Clip | Len | Camera it proves |
|---|---|---|
| `S5-Render.MP4` | 20s | off-axis wall master, five named guests |
| `S6-Render.MP4` | 15s | locked master, front-of-wall, two exact ranks |
| `S7-Blender.MP4` | 20s | retreat-lead corridor walk + one 90° whip pan + one snap zoom |
| `S8a-Render.MP4` | 20s | lateral dolly along the pieces + three 1s locked catalogue inserts |
| `S8b-Render.MP4` | 20s | dolly (vessel/canvas) → crowd parts → push down the cleared centreline |
| `S8c-Render.MP4` | 20s | slowest push-in on the axis, medium, hand held up |
| `S8d-Render.MP4` | 20s | same push continuing to close; the hand lowers at 17s |
| `S9-Render.MP4` | 20s | locked frontal portrait of Dupe + slow push, group blurred deep on the same axis |
| `S10-Render.MP4` | 20s | (wave 1) |
| `S10b-Render.MP4` | 20s | the duel: two locked singles, identical framing, cut on every bid |
| `S11-Render.MP4` | 20s | locked master, front-of-wall |
| `S12a/b/c-Render.MP4` | 20s ea | the slowest arrival, the room parts, the bid |
| `S14-Render.MP4` | 20s | the scream, the splat, snap zoom |
| `S16-Render.MP4` | 20s | the sawing wide |
| `S18a-Render.MP4` | 20s | the interview room |
| `S18b-Render.MP4` | 20s | vast symmetrical white locked frame; hammer up at 6s, down at 12s |
| `DH1-Render.MP4` | 10s | doll's house locked high: the empty board, Dupe crosses it |
| `DH2-Render.MP4` | 10s | doll's house: one figure enters the red door, walks toward the near plane |
| `DH3-Render.MP4` | 12s | doll's house: two figures centre, the arm sweeps the room at 5s |
| `DH4-Render.MP4` | 12s | doll's house: 14 figures in loose rows, guards a dark second rank, only Dupe moves |
| `S8a-Render-v2.MP4` | 20s | hall_v41 tour: one continuous lead-dolly, no cut; Valder presents vessel (4.5s), chair (12s), trap (18.5s); Dupe + cart working behind |
| `X2-Render.MP4` | 20s | Wave III room-tone bed: one-point symmetrical master of the empty hall, red door dead centre, camera dead still |
| `X3-Render.MP4` | 8s | Wave III red door: closed, both leaves swing open at 2s, seated closed again at 7s; static symmetrical framing |
| `X4-Render.MP4` | 10s | Wave III the row from the room: five backs at three-quarter angle (gold/cyan/plum/green/lime), Dupe + cart crossing behind |
| `S1C-Render.MP4` | 8s | Wave IV cart detail: one lateral track at cart height holding pace with the wheels, cart static in frame while the hall slides past; rack EMPTY per spec |
| `S2C-Render.MP4` | 20s | Fix-1 pacing: one locked wide looking UP the hall into Valder's collection, never the cracked wall; Dupe paces, exits at 5s, returns at 7s, freezes for the PA at 10s, leaves for good at 18s; the cart stands parked throughout |
| `S2E-Render.MP4` | 12s | Fix-1 fake cleaning: one locked three-quarter on Dupe at the wall — his hands work the cloth, his eyes never go near it, the old man crossing behind him is what they are actually following |
| `S2F-Render.MP4` | 12s | Fix-1 the old man looks: one locked three-quarter across the hall — he walks, stops at a piece, stands and looks, moves on, stops again. Dupe is not in this scene |
| `S2D-Render.MP4` | 20s | Fix-1 first guest: three locked shots cut at 7s and 10s — wide on the hero wall with the cart in from the left, the inside-the-wall beat (a generated plate, so the previz only holds its timing), then behind Dupe looking up the gallery as the first visitor enters at 12s |
| `S2Fix1-Render.MP4` | 20s | Fix-1 accident: locked wide → fast zoom into the crack at 8s → tilt down to the plaque at 10s → CUT close on Dupe at 12s → CUT wide, he racks the painting and wheels out while the camera stays put → CUT to the straight-on final, crack above and plaque below |
| `S2RF-Split-Render.MP4` | 20s | five vertical close-up panels (gold = Carrington, teal = the woman in green) lit one at a time, hard cut at 15s to the S2R full shot with the startle; Blender, 480 frames |
| `S2AJ-Render.MP4` | 30s | wall-POV locked master (S2N camera), the five interpreters appearing on their marks left→right by jump cut at 4/9/15/25s, the four arguing 20-25s, Dupe far back; camera + blocking only, no crack proxy; Blender, 720 frames |

## How a previz gets built (recorded 2026-09-03, so it is done once)

`scripts/previz/s2fix1_previz.py` is the first build script kept in the repo.
Every earlier one lived only on winbox and was lost, which is how the trap below
cost two wasted renders. Run it headless:

```
ssh winbox 'cmd /c ""C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" \
  -b "C:\Users\UsEr\Downloads\SorrySir_hall_v41.blend" -P "C:\Users\UsEr\Downloads\<script>.py""'
```

**The set already exists — never rebuild it.** `SorrySir_hall_v41.blend` carries
the hall, the columns, the red door, Valder's collection pieces, and the crack
and plaque at their approved size and position (`crack_core` + `crack_arm_0..4`
at `(0, -21.82, 3.05)`, `plaque` at `(0, -21.80, 1.05)`, 0.35 × 0.22 m). A previz
script adds a camera and character proxies and nothing else.

**Three traps, each measured rather than guessed:**

1. **A timeline marker overrides `scene.camera`.** `hall_v41` holds one marker,
   `('FLY', 1, 'CAM_FLY4')`. Setting `sc.camera` looks like it works and the
   render still comes out of the flyover camera — every frame pointed at the red
   door instead of the hero wall. `sc.timeline_markers.clear()` before assigning.
2. **Blender 5.x hides video behind a media type.** `image_settings.file_format
   = "FFMPEG"` raises an enum error on its own; set
   `image_settings.media_type = "VIDEO"` first.
3. **The camera looks along −y, so nearer means larger y.** A painting written
   at `y = -21.84` sits *behind* a crack at `-21.82` and vanishes into the wall.
   Anything meant to hang in front of the crack belongs at about `-21.70`.

Derive angles from the geometry instead of eyeballing them — the plaque tilt is
`atan2(cam_z - plaque_z, cam_y - plaque_y)`, which is 45° from a camera at
`(0, -19.80, 3.05)`, not the 38.7° a first guess produced.

## Deliberately NOT previz'd

`P1–P3` (plaque inserts), `D1–D5` (Dupe reaction inserts), `X1–X4`, `X6–X8a/b`
are locked-off with no camera movement — there is no camera grammar for a previz
to prove, so prose carries them. `X5` is a slow macro push on the painting;
also not worth a build.

## Known previz limitation

The void around the doll's house box reads dark grey, not glossy black — a
viewport-shading limit of the playblast, not a staging error. The plate
`@loc_dollhouse` carries the true black; the previz is only there for the
figure blocking, count and scale.

## A previz must be at least the resolution we generate at (measured 2026-09-03)

**Every previz is 1280x720. A 640x360 file will fail the generation.**

This cost three failed generations and two operator sessions before anyone
measured it. S1C's previz was 640x360; the shot fired cleanly three times, each
rendered ~26 minutes, and each died on Higgsfield's generic *"Something went
wrong. Please try again, or change your input files or prompt."* Every other
explanation was eliminated first — all 33 previz are exactly 16:9, S1C was not
the largest file, its raw bitrate ranked fifth of thirty-three, and a
file-by-file count found no duplicate `@Video` mention anywhere.

The one thing left was resolution. Of previz used as video references, both at
640x360 had failed and all five at 1280x720 had passed. The previz was scaled to
1280x720 with nothing else changed — same 8 seconds, same 192 frames, same
camera — and **take 4 passed**: `absence-S1C-take4-023e91c3-PASS-8s-720p.mp4`.

Higgsfield documents no such requirement anywhere. A sweep of all 74 help
articles, 20 doc pages and the full OpenAPI spec found nothing about video
reference resolution at all, so this is our own measurement and nobody else's
rule. It holds for our pipeline at 720p output; if we ever generate at 1080p,
assume it moves with the output and re-measure rather than trusting this line.

`scripts/previz-check.py` enforces it. Run it before using any previz as a
reference — it also catches wrong frame rate, wrong duration, a stray audio
track, and a bitrate outside the band the corpus occupies.
