---
name: blender-previz
description: "Drive Blender (on winbox) from a Claude session to build free camera-previz for AI film scenes — the proven camera rigs (retreat-lead, whip-pan, snap-zoom, locked-master), the exec-bridge protocol, the playblast-to-MP4 pipeline, and the verification discipline. Use for previz/blocking/camera-reference work BEFORE spending Higgsfield credits; every bpy operation here is free. Trigger on /blender-previz, 'previz', 'บล็อกฉาก', 'มุมกล้อง Blender', 'camera reference', or any task that renders a Blender camera move for use as a Higgsfield @Video ref. NOT for paid Higgsfield generation (higgsfield-unlimited-gen owns that) and NOT for beauty renders."
created_by: human
audience: [cto]
---

# Blender Previz — free camera truth before paid generation

Born 2026-08-30 on «Sorry, Sir»: the CEO's insight is that the expensive
failure mode of AI video is CAMERA grammar (a prose "ONE LOCKED SHOT" is a
request; a reference video is geometry), and Blender iterations cost nothing
while a wrong Seedance take costs a 20–50-minute slot. So: prove the camera
in Blender, watch it with your own eyes, then let Higgsfield copy it.

Structure of this skill follows github.com/kevinbadi/blender-skills (one
move, one recipe, params up front) — but the moves here are NARRATIVE, not
product orbits, and every one below has actually shipped a CEO-approved clip.

## The rule that outranks everything

**The CEO approves every generation.** Everything `bpy.*` is free — build,
animate, playblast without asking. Anything in the plugin's Higgsfield panels
(`fnf_*`, Generate 3D/HDRI/Motion/Retexture, Realtime) spends real credits:
stage it, never fire it. Same standing order as the rest of the org
(`feedback_ask_before_paid_api`).

## Reaching Blender (the exec bridge)

Blender runs on `winbox` with the Higgsfield add-on, which opens a local exec
bridge on `127.0.0.1:9876`. `C:\Users\UsEr\Downloads\hfbridge.ps1` speaks its
protocol — JSON `{type:"execute", code, strict_json:false}`, request AND
response NUL-terminated:

```bash
scp -q /tmp/job.py winbox:'C:/Users/UsEr/Downloads/job.py'
ssh winbox 'powershell -NoProfile -ExecutionPolicy Bypass -Command \
  "$code = Get-Content -Raw \"C:\Users\UsEr\Downloads\job.py\"; \
   & \"C:\Users\UsEr\Downloads\hfbridge.ps1\" -Code $code"'
```

- **Always scp a .py and Get-Content it.** Inlining Python through
  ssh+powershell quoting mangles it.
- **hfbridge's read timeout is 30 s.** A long job (playblast) times the
  CLIENT out while Blender keeps working — poll for output files instead of
  trusting the response.
- **NEVER `raise SystemExit` (or sys.exit) in bridge code.** It propagates
  into the add-on's timer and kills the executor: the port stays open, every
  later request hangs forever. End loops with break-flags. If it happens, the
  only recovery is restarting Blender.
- **After any Blender restart the bridge stays DOWN** — the add-on only
  starts it on the interactive SIGNED_IN event, and a silent token restore
  fires AUTH_SETTLED instead. Relaunch with the fix-up script:
  `blender.exe --python C:\Users\UsEr\Downloads\boot_bridge.py` (waits for
  auth, then calls `mcp_service.start()`), via
  `schtasks /create … /it` + `/run` so the GUI lands in the user's session.
  Expect ~2–4 min before :9876 listens; poll, don't assume.

## Blender 5.x API traps (all hit on day one)

- ✅ **CORRECTED 2026-09-04 — Blender 5.x CAN write MP4 directly.** This skill
  previously said it could not, and sent everyone down a PNG-sequence-plus-mux
  path for nothing. The earlier finding was half right: setting
  `file_format = 'FFMPEG'` on its own really does raise
  `TypeError: enum "FFMPEG" not found in (...)`. What was missed is WHY — 5.x
  gates video behind a new `media_type` property, and the format enum only
  offers video once you have switched it. Set that first and FFMPEG appears:

  ```python
  sc.render.image_settings.media_type = "VIDEO"     # <- the gate. Do this first.
  sc.render.image_settings.file_format = "FFMPEG"
  sc.render.ffmpeg.format = "MPEG4"
  sc.render.ffmpeg.codec  = "H264"
  sc.render.ffmpeg.constant_rate_factor = "HIGH"
  sc.render.ffmpeg.audio_codec = "NONE"
  sc.render.filepath = r"C:\Users\UsEr\Downloads\SCENE-Render.MP4"
  bpy.ops.render.render(animation=True)
  ```

  Six previz shipped this way on 2026-09-03/04, every one passing
  `previz-check.py`. Blender writes the extension lowercase (`.mp4`) whatever
  case you give it, so `scp` the lowercase name back. The PNG-sequence path
  further down still works and is still the fallback if a build genuinely
  lacks ffmpeg, but it is no longer the default.
- `action.fcurves` still exists in 5.2 despite the layered-actions rewrite.
  `obj.animation_data.action.fcurves` iterates fine, and it is how you force
  interpolation — which the motion section below depends on completely.
- **A timeline marker silently overrides `scene.camera`.** `hall_v41` carries
  one marker, `('FLY', 1, 'CAM_FLY4')`. You set `sc.camera = my_cam`, the
  assignment succeeds, and the render still comes out of the flyover camera —
  every frame pointed at the wrong end of the room, no error anywhere. Cost two
  full renders before anyone printed `sc.camera` from inside the render. Always
  `sc.timeline_markers.clear()` before assigning the camera.
- **Depth sign: the camera looks along −y, so NEARER means LARGER y.** A
  painting written at `y = -21.84` sits *behind* a crack at `-21.82` and
  vanishes into the wall. Anything meant to read as in front of something else
  needs the larger y. The same trap puts a camera inside a wall solid and
  renders flat brown — check a mesh's y-extent before placing a camera near it.
- **The parenting trap that shipped a broken previz:** `o.parent = walk;
  o.matrix_parent_inverse = walk.matrix_world.inverted()` KEEPS the child's
  world position — the group does not move to the empty, and everyone stays
  at the origin while the empty animates. For rig groups you want
  `o.parent = walk` with NO inverse, then set `o.location` to the intended
  LOCAL offset.

## The proven camera moves

All use one rig pattern — **never hand-rotate a camera**: camera gets
position keys only, plus a `TRACK_TO` constraint (`TRACK_NEGATIVE_Z`,
`UP_Y`) at an `AIM` empty; animating the AIM is what aims the shot.

**RETREAT-LEAD** (S7 walk): subject rides an empty from the far door toward
the camera at **1.5 m/s** (walking speed — first attempt used 4.7 m/s and
read as running); camera keys retreat along the same axis staying 3.5–4.5 m
ahead; AIM keys ride the subject's head (z≈1.5).

**WHIP-PAN**: at the beat frame, key the AIM from the walker's head to the
new subject's head over **6 frames** (0.25 s @24). The camera itself holds
position. Land the new subject at the same axis-coordinate as the camera so
the pan is a clean 90°.

**SNAP-ZOOM**: keyframe `camera.data.lens` only — e.g. 35→85 over 5 frames.
110 mm at ~3 m overshoots to a torso; 85 lands a head. Zoom targets whatever
AIM already looks at, so fix AIM height to the head (z≈1.62) at the pan.

**LOCKED-MASTER** (S2/S4/S6/S11 family): static camera, no AIM constraint
needed — position + a hand-set rotation is fine for a camera that never
moves; square-on at the hero wall, waist height (z≈1.1).

**Name tags**: every proxy gets a floating text object (emissive, character
colour, z≈2.2) with its own `TRACK_TO` at the camera (`TRACK_Z`, `UP_Y`) so
labels billboard — this is what lets the CEO read a gray previz.

Scene conventions from the hall build: metres, 24 fps, film geography is
LAW — in «Sorry, Sir» the crack wall is the END wall OPPOSITE the red door,
not a side wall (CEO caught this in v1; check the film's canon before
placing hero geometry).

## Headless EEVEE render → MP4 (standard path, ~30s for 192 frames)

**Use this, not the opengl playblast below, unless you already have GUI
access.** `bpy.ops.render.opengl` (viewport playblast) needs an interactive
window station, and getting one on winbox over ssh does not work — no window
station, and the scheduled-task workaround is (correctly) refused by the
safety classifier as a persistence-technique pattern. `bpy.ops.render.render`
(a real production render) does NOT need a window station at all and runs
fine from a plain background Blender process:

```bash
scp -q previz_job.py winbox:'C:/Users/UsEr/Downloads/previz_job.py'
ssh winbox 'powershell -NoProfile -Command "& \"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe\" -b \"C:\Users\UsEr\Downloads\SorrySir_hall_v41.blend\" --python \"C:\Users\UsEr\Downloads\previz_job.py\" -- <SHOT> 2>&1 | Out-String"'
```

This is `-b` (background CLI mode), a completely separate mechanism from the
exec bridge on :9876 — no bridge, no window station, no GUI, ever. This is
the actual fix for "no window station": swap which render call you use, not
how you reach Blender.

**The settings that made it fast** (measured on S1C, 192 frames, 1280×720,
Blender 5.2.1 LTS, hall_v41, 2026-09-03):

```python
S.render.engine = 'BLENDER_EEVEE'
S.eevee.taa_render_samples = 4
S.eevee.use_shadows = False       # see WHY below — this is the one that matters
S.eevee.use_raytracing = False
S.eevee.use_fast_gi = False
S.render.use_simplify = True
S.render.simplify_subdivision_render = 0
```

| Run | Settings | Wall clock (192 frames) | Notes |
|---|---|---|---|
| BEFORE | `taa_render_samples=8`, everything else default (shadows/raytracing/fast_gi ON, no simplify) — today's committed `x_shots_720.py` as-is | **598.58s (9m59s)** | `Error: Shadow buffer full, may result in missing shadows and lower performance. (3340-3355 / 2048)` on nearly every frame (see WHY) |
| AFTER | block above | **29.16s** | zero shadow-buffer errors; visually verified from the muxed MP4's own frames — camera track and proxy read are unchanged |

**20.5x faster, and well under the "couple of minutes" target** — 192 frames
at 1280×720 landed at 29s, not "a few minutes." Confirmed via
`ffprobe -count_frames` on the muxed MP4 (not just the PNG count) and by
looking at contact-sheet frames pulled from that MP4, per the verification
discipline below.

**WHY it was slow: this is EEVEE Next, and the scene has 31 shadow-casting
lights.** `SorrySir_hall_v41.blend` carries 20 spot lights @700W, 10 point
lights @140W, 1 area light, 1 sun — every one casting a shadow by default.
EEVEE Next's shadow system pools all lights' shadow tiles into one
`shadow_pool_size` (default 2048); this scene needs ~3340-3355, so every
single frame overflowed it and re-computed shadows from a blown budget —
that overflow, not sample count, was the dominant cost. `taa_render_samples`
matters far less here than `use_shadows` because flat grey/emissive proxy
materials don't produce meaningful noise at low sample counts to begin with.
**If a scene's proxies need shadows for the blocking to read** (rare — the
whole layer is deliberately grey and flat), raise `shadow_pool_size` instead
of leaving it overflowing, or drop `shadow_resolution_scale` well below 1.0
to shrink the per-light footprint — don't just crank samples, that was never
the bottleneck.

**EEVEE Next (Blender 5.2.1) is a different API from legacy EEVEE — do not
carry over old attribute names.** Verified via runtime introspection
(`dir(scene.eevee)`), not docs, since the API moved twice in two majors:
- `use_gtao`, `use_bloom`, `use_ssr`, `use_soft_shadows` **do not exist any
  more.** Setting any of them raises `AttributeError`.
- Bloom is **gone entirely** — no EEVEE Next equivalent, compositor-only now.
  Nothing to disable; it already costs zero.
- AO is folded into the GI system: `use_fast_gi` (+ `fast_gi_*` quality
  knobs), not a separate toggle.
- Reflections/refraction ray tracing is one master switch: `use_raytracing`.
- Shadows are one master switch, `use_shadows`, plus `shadow_ray_count`,
  `shadow_step_count`, `shadow_resolution_scale`, `shadow_pool_size` for
  quality/cost if you need shadows kept on for a specific scene.
- `render.use_simplify` + `simplify_subdivision_render = 0` cost nothing to
  set but did nothing measurable here either — the proxy geometry has no
  subsurf modifiers to simplify. Harmless to leave on; don't expect it to
  move the needle on a proxy-only scene.
- `film_transparent` and colour management (`view_settings.view_transform`,
  currently `AgX`) were left alone, per the "don't touch unless you can show
  it costs time" rule — untested because `use_shadows` alone already blew
  past the target; no reason to touch anything with no evidence behind it.
- **Direct FFMPEG output is a trap, not just unavailable** — see the API
  traps section above; the static enum lies, the runtime enum doesn't.
  PNG-sequence + external `ffmpeg` mux stays mandatory.

**Mux, same as before, but check the bitrate:**
`ffmpeg -framerate 24 -i f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 20
<Name>.MP4`. `-crf 20` is the default starting point, but a shot with a lot
of foreground detail sliding past camera (S1C's colonnade) can push CRF 20
above the corpus's usual ~80-900 kbps band (`scripts/previz-check.py` flags
this, doesn't fail it) — S1C measured 1417 kbps at CRF 20 against 841 kbps at
CRF 24, same PNG frames, no visible difference in contact-sheet frames at
either. Bump CRF a few points on a busy shot rather than accepting a
50%-over-band file by default.

## Playblast → MP4 (GUI-only fallback, ~1 minute for 480 frames)

Use this only when you already have interactive GUI access to Blender on
winbox (this skill does not obtain one — see the rule above).

1. Bridge job: viewport capture through the scene camera —
   `region_3d.view_perspective='CAMERA'`, shading `MATERIAL`, overlays off,
   `bpy.ops.render.opengl(animation=True)` inside a `temp_override`, PNG seq
   to `Downloads\<scene>_seq\f_####.png` at 1280×720.
2. Mux on winbox: `ffmpeg -framerate 24 -i f_%04d.png -c:v libx264
   -pix_fmt yuv420p -crf 20 <Name>.MP4`.
3. `scp` back to the Mac, `bash scripts/video-see.sh screen <file>` for the
   structural read (expect `FROZEN` flags at hold beats — proxies have no
   idle animation; that is normal, not a defect).

## Two rendering traps measured 2026-08-30 (S12a build)

- **Never re-key an object that already has animation from an earlier bridge
  call — rebuild it fresh.** `animation_data_clear()` + new keys on an
  existing object produced a scene where `frame_set` + `matrix_world`
  evaluated CORRECTLY in the bridge, but every render (write_still AND the
  animation playblast) drew the OLD pose — Blender 5's slotted actions plus
  the never-redrawn viewport hold stale state, and even explicitly assigning
  `animation_data.action_slot` did not fix the draw. Objects created AND
  keyed inside the same script render correctly every time. So: each scene
  script deletes its animated actors and recreates them; only dead
  architecture (walls, columns, crack) is safe to reuse across scripts.
- **The default Cube comes back after every Blender restart** (fresh startup
  scene) and photobombs dead centre of the master. Remove `Cube` and `Light`
  at the top of every build script, not once per session.

## Human motion timing — the hardest thing to fake (added 2026-09-04)

The CEO rejected three previz in a row for movement before anyone rejected one
for framing. Camera grammar is what previz exists to prove, but a body moving
at the wrong speed destroys a take just as thoroughly, and it is the note you
will hear first. Full working: `Agents-Wikis/research/2026-09-04-human-motion-timing-for-previz.md`.

### Never pick frame numbers by feel. Derive them from speed.

    frames = round(distance / speed * fps)

| | speed | notes |
|---|---|---|
| adult, unhurried | 1.2–1.4 m/s | ~0.70 m stride, ~2 steps/s |
| elderly, or with a cane | 0.9–1.3 m/s | |
| hurrying, not running | 1.6–1.9 m/s | |

Eyeballing frame counts is how an elderly man in a heavy overcoat ended up
crossing a gallery at **1.87 m/s** — faster than a healthy young adult walks —
across three separate previz before anyone did the division.

**🟡 Proxy correction:** our proxies are legless cylinders. They give the eye no
gait cues, so they read as gliding and a correct 1.2 m/s looks too fast. **Use
0.95 m/s in previz** while the prompt still says an ordinary unhurried pace.
Re-measure if proxies ever get legs.

### A jump is ballistic, and Blender's defaults fight you

    airtime = 2 * sqrt(2h/g)        take-off = sqrt(2gh)        g = 9.81

0.28 m → 0.48 s airtime → **11 frames at 24fps**, leaving the ground at 2.34 m/s.

The trap is not the airtime. **It is the shape.** A jump leaves the ground
fastest and hangs at the apex; Blender's default bezier eases out of the first
key and into the last, which is exactly backwards. Two keyframes will never
read as a jump whatever numbers they hold — the first attempt here looked like
a glitch and stayed looking like one through two rounds of "make it slower".

And airtime is only the middle. The five-phase counter-movement jump:

| phase | s | frames |
|---|---|---|
| crouch (sink 0.10–0.12 m) | 0.30 | 7 |
| push-off, accelerating | 0.20 | 5 |
| **flight — the parabola** | 0.48 | 11 |
| land and absorb | 0.25 | 6 |
| recover to standing | 0.20 | 5 |
| **whole cycle** | **1.43** | **34** |

Budget a hop at a second and a half, not a quarter of one.

```python
def hop(o, start, x, y, z0, h=0.28, crouch=0.11, fps=24.0):
    g = 9.81
    air = int(round(2 * math.sqrt(2 * h / g) * fps))
    CR, PU, AB, RE = 7, 5, 6, 5
    f = start
    for i in range(CR + 1):                       # sink
        key(o, f + i, x, y, z0 - crouch * (i / CR))
    f += CR
    for i in range(PU + 1):                       # drive, accelerating
        key(o, f + i, x, y, z0 - crouch + crouch * (i / PU) ** 2)
    f += PU
    for i in range(air + 1):                      # SAMPLE the parabola
        t = i / air
        key(o, f + i, x, y, z0 + 4 * h * t * (1 - t))
    f += air
    for i in range(AB + 1):                       # land, absorb
        key(o, f + i, x, y, z0 - crouch * (i / AB))
    f += AB
    for i in range(RE + 1):                       # stand up
        key(o, f + i, x, y, z0 - crouch * (1 - i / RE))
    return f + RE
```

Two rules or it does not work:

1. **Sample the curve; do not key its endpoints.** `4*h*t*(1-t)` passes through
   0, h, 0. One key per frame.
2. **Force LINEAR afterwards** or Blender re-eases your samples and undoes the
   whole thing:

```python
for fc in obj.animation_data.action.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
```

### Prove it with numbers, not with your eyes

```python
prev = None
for fr in range(start, end):
    sc.frame_set(fr); z = obj.location.z
    if prev is not None: print(fr, round(z,3), round((z-prev)*fps, 2))   # m/s
    prev = z
```

A correct jump prints a slow negative through the crouch, a rising positive
through the push, a peak near `sqrt(2gh)`, a smooth decay to 0.00 at the apex,
then the mirror. **Deceleration must land near 9.8 m/s².** Ours read 10.7 — the
expected over-read from two-frame differencing.

The broken version printed **±6 to ±12 m/s**. No human does that, and the
number said so in one line where two rounds of watching the render only got
"still too fast".

### Watch for patches racing each other

Two edits to the same keyframe block in one session, and the second one
anchored on text the first had already replaced — so a "fixed" render shipped
still containing the old motion. And walk keys running to frame 150 while hops
started at 120 fought for the same channel. **After any motion edit, probe the
values out of the .blend before re-rendering.** The probe above costs seconds
and catches both.

### The gate cannot replace a person watching

`previz-check.py` passed every one of these renders. It does not know that a
man is hopping a metre to the left of the crack he is trying to see into, or
that a trolley whose long axis runs along y is being wheeled sideways along x.
Both shipped through the gate and were caught by the CEO watching the video.
**Mechanical checks catch mechanical faults. Staging needs eyes.**

## The verification discipline (non-negotiable)

v1 shipped with three wrong things the structural check could not see. So:
**verify from the MP4's OWN FRAMES, not from viewport stills** — playblast,
mux, then `ffmpeg -ss <t> -i file.MP4 -frames:v 1 chk.png` at each story
beat, scp back, and LOOK at them yourself with Read. A viewport still can
disagree with both the depsgraph and the final movie (see the re-key trap
above); frames extracted from the muxed MP4 are the ground truth of what
the CEO will actually receive. Claiming a camera does X without having seen a frame is how you
send the CEO a film of the wrong wall. Only after the stills match the text
do you playblast, mux, and deliver via `mcp__org__send_media_to_ceo`.

## Handoff to Higgsfield

The finished previz becomes a camera reference for generation: drag the MP4
onto the Seedance prompt box and mention it as `@Video 1`, Elements as
normal (CEO's method — full procedure and its verification live in
`higgsfield-unlimited-gen`). Festival ruling, CEO 2026-08-30: Blender/AE are
editing-class tools and exempt from platform-only — generation still happens
on Higgsfield; the previz carries only the camera.

## Three more traps, all measured on hall_v41 (2026-09-04)

**`action.fcurves` is gone in Blender 5.2.** Actions are slotted now, so the
flat list raises `AttributeError` and the curves live at
`action.layers[].strips[].channelbags[].fcurves`. Any LINEAR-interpolation pass
needs to handle both:

```python
def all_fcurves(act):
    fl = getattr(act, "fcurves", None)
    if fl is not None:
        yield from fl; return
    for layer in getattr(act, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                yield from cb.fcurves
```

**`matrix_parent_inverse` cancels the parent, it does not enable it.** Setting
it to `parent.matrix_world.inverted()` makes world = local, which is right when
you are placing an already-positioned prop under a parent and want it to stay
put — and exactly wrong when you want camera-space placement. A lens mask
parented that way lands at its raw coordinates in world space, which on this
project buried it under the floor 22 m from the camera. For true camera space,
**leave the inverse as identity** so world = `cam.matrix_world @ local`. Either
way, `bpy.context.view_layer.update()` first — `matrix_world` is stale until the
depsgraph ticks, so parenting straight after moving a camera uses the old matrix.

**`charlib.CHARS` is a fixed key table.** `spawn_char` does `CHARS[name]` with
no fallback, so a scene-local proxy name is a `KeyError` that kills the whole
render. Check the table before inventing a name; the colours already encode the
costumes (COLLECTOR_A is blue, STUDENT yellow-green, CRITIC magenta).

## Previz is a depth diagram, not a beauty render

Hall geometry beats intuition, and both of these were caught only by rendering
frames and looking at them:

- **Measure the room before placing a tracking camera.** A lateral dolly at
  x=-10.5 rendered solid black because the hall is only x -6.0..+6.0 — the
  camera was outside the building. One `bound_box` probe would have said so.
- **Cheat scale to encode depth order.** The wall break is 0.34 m of hairline
  sticks; at true size, 1.8 m from the lens, it reads as a small mark on the far
  wall — and the model's standing failure is staging people *in front of* it.
  Scaling it 3x in previz only, so its arms visibly cross the figures, makes the
  ordering unmisreadable. The true shape still comes from the Element.
- **A black aperture mask is worse than none.** Four slabs leaving a hole render
  as a hard rectangle, and Seedance copies it as a letterbox. Carry the
  aperture look in the prompt and the reference image instead.
