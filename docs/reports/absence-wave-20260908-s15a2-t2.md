# S15a2-RoomDecides — t2 fire (task-1e95d2af)

## Gate checks (re-run after CTO fix 12→21 crowd count, commit 6767a97)
- depth/gaze grep on paste block: 0 hits
- `prompt-lint.py`: exit 0
- Chips: 12/12, exact match to expected list
- HARD CUT count: 2

## Money
- Lane: CREDIT (per CEO auth 2026-09-07, not Unlimited)
- Balance before: 58 credits
- Generate button read (zoomed pixels): `GENERATE / 56 / 52` (52 live, matches 8s spec exactly)
- Clicked exactly once
- Balance after: 6 credits (58 − 52 = 6, exact)

## Fire
- Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (confirmed in address bar before fire)
- Model: Seedance 2.5, 720p, 16:9, 8s (verified via `aria-valuenow`), High, 1/4, Sound On, Unlimited OFF
- Prompt pasted via synthetic `ClipboardEvent`, End→space→Backspace sync tap
- 12/12 chips bound (verified via `span.text-font-brand` selector), no warning triangles on any of the 12 thumbnails zoomed
- Downloaded: `hf_20260907_173333_fc9630b4-59ac-4f77-a06d-d5fea69f43a6.mp4`, 8.041667s, 1280x720

## Frame review

### FIRST FRAME PASS/FAIL (0.0s)
Dupe dead centre, white uniform/orange trim/gold V, mustache, holding rolled item.
Valder (cream/white suit) immediately left, workman (slate overalls, bucket,
towel) immediately right — matches reference plates. Room static, all faces
already turned toward Dupe center. No walk-in. **PASS** — cuts against S15a-1.

### Hard cut 1 (~3.0s) — shot 1 → shot 2
Confirmed clean cut to room-wide shot: registrar (black suit, white gloves,
ledger), two navy guards, Carrington's bodyguard (black suit/glasses), ~4-5
press with cameras, grandmother in wheelchair at the cart (painting face-out,
matches `prop_cart_b`), Madame Thibault in green leather, men in coats at
edges. **PASS.**

### Room reaction (unison tilt / nod), 3.0s-4.5s
Sampled frames 3.0s, 3.5s(implied), 4.0s, 4.5s — head positions look
essentially static across all samples, no clearly visible synchronized tilt
or slow nod. **FLAG** — the directed beat ("heads tilt IN UNISON... one of
them nods slowly") is not confirmable from frame sampling; may be too subtle
to register at 0.5s intervals, or may not have rendered.

### Hard cut 2 timing
Room shot (shot 2) still showing at 4.5s (f_010), already cut back to Dupe's
close-up by 5.0s (f_011) — cut landed ~4.5s-5.0s, not the scripted 5.5s. Shot
2 ran ~1.5-2.0s vs the scripted 2.5s; shot 3 correspondingly longer. **FLAG**
(minor timing deviation, ~20-40% short on shot 2).

### Crowd voice line, no face (5.5s-8s / shot 3)
Frames 5.5s, 6.5s, 7.5s all show Dupe's face in progressively closer push-in
— no cutaway to any other character during the line. **PASS.**

### Push-in smoothness
Frame progression 12→14→16 shows continuous, centred zoom on Dupe's face, no
visible jump/cut within the shot. Final frame: mouth slightly parted, no
reply — matches spec. **PASS** (cannot independently confirm zero handheld
wobble from stills, but framing stays centred/stable across samples).

### Six words, no repeated dialogue
Not independently verified — no audio transcription tool available this
session. No visual indication of any other character shown mid-speech.
**NOT VERIFIED (visual only).**

### Cast count — TWENTY-ONE PEOPLE
Rough visual count in the shot-2 wide frame: ~19-21 distinct heads, no
obviously duplicated FACES spotted in that pass alone.

## CTO's independent crop findings (both confirmed against frames pulled locally)

### 1. Duplicate/mirrored 4th navy guard
CTO's crop `x=0.60-0.78, y=0.20-0.75` of the 3.2s frame shows a navy-uniformed
figure (peaked cap with gold V, navy tunic, white glove) standing ALONE on
the frame-right side, behind the grey-overcoat man — isolated from the
group of 3 (2 navy + 1 black-suit) correctly clustered stage-left.
`guard_valder_two`'s reference is explicitly "one picture is both of them"
(2 guards), so this is a duplication/mirroring defect: **3 navy uniforms
visible across the full frame width vs the 2 specified.** Confirmed via
extracted frame `f_320.png` + `f_320_rightcrop.png`. **FLAG — third
occurrence tonight of this exact defect class** (S15a-1 t1 duplicated the
registrar, S2S-B t2 duplicated the guard pair).

### 2. Wall mark shape/weight
Cropped the opening-shot mark region (`f_001_markcrop.png`, ~4x zoom). It
renders as a thin, translucent, spidery/insect-like shape — a small dark
body with several thin leg-like lines radiating outward, reading as a
mosquito or spider rather than the crack canon's "one small solid-black
star-shaped crack about a hand across." Scale is roughly in range (~head-
wide). Shape and weight both fail — it is not solid black and does not read
as a fracture. **FLAG.**

## VERDICT: FLAGGED

Filed to Drive regardless, per instructions ("failures get filed too"):
`All Scene/Fix-1/S15a2-RoomDecides-Fix1.MP4`
https://drive.google.com/file/d/19zD1SxuEkI-0qI5GbC2_abnI0mNoVXds/view

Cast/blocking, hard-cut structure, and the first-frame continuity all pass.
The clip does NOT pass clean: duplicated navy guard (3rd occurrence of this
defect class tonight) and the wall mark's shape/weight both need a re-fire
before this can cut into the film. Room-reaction unison-tilt and shot-2
timing are softer flags worth a second look but are not, on their own,
blocking.
