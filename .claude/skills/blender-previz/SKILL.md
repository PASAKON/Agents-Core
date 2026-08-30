---
name: blender-previz
description: "Drive Blender (on winbox) from a Claude session to build free camera-previz for AI film scenes — the proven camera rigs (retreat-lead, whip-pan, snap-zoom, locked-master), the exec-bridge protocol, the playblast-to-MP4 pipeline, and the verification discipline. Use for previz/blocking/camera-reference work BEFORE spending Higgsfield credits; every bpy operation here is free. Trigger on /blender-previz, 'previz', 'บล็อกฉาก', 'มุมกล้อง Blender', 'camera reference', or any task that renders a Blender camera move for use as a Higgsfield @Video ref. NOT for paid Higgsfield generation (higgsfield-unlimited-gen owns that) and NOT for beauty renders."
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

- `action.fcurves` is GONE (layered actions). Skip easing loops; defaults are
  fine for previz.
- `render.image_settings.file_format` has NO video formats any more —
  **Blender 5.x cannot write MP4.** Playblast to a PNG sequence and mux with
  ffmpeg (installed on winbox via winget, find it under
  `$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*`).
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

## Playblast → MP4 (~1 minute for 480 frames)

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
