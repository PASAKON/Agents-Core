# «Sorry, Sir» — THE VALDER Draft 2 · continuity pass

CTO, 2026-09-05. Source: `Sorry sir THE VALDER Draft 2.mp4` — 5:26, 1280x720,
24fps, **58 shots** (scene-detected, threshold 0.25).

Method: one frame per shot at its midpoint, then full-resolution centre crops of
anything that looked wrong. Everything below is read off frames — where a call
rests on a 384px thumbnail rather than a full-res crop it says so.

---

## FINDING 1 — THE CRACK IS A DIFFERENT OBJECT AT 110.6-130.6s · **FIX THIS FIRST**

**The film's central object does not match itself, and it is wrong in the
longest shot in the picture — 20 seconds, the single biggest block of screen
time in the whole draft.**

What is on screen at 110.6-130.6s: a **small solid black SQUARE** at the centre
with **five or six perfectly straight, uniform-width black bars** radiating to
the edges of frame. Machine-drawn. No plaster, no ragged edge, no debris, no
depth, no thickness variation anywhere along any arm.

What the crack is everywhere else, and in the canon (`CRACK-CANON.md`, written
2026-09-04): a **torn hole** — a solid black arrowhead-shaped body pointing
down, a hooked spur off its upper right, a notch upper left, **four** long
irregular arms that thicken and thin and kink, crumbling white plaster lips,
debris on the floor. Verified at 214s, 308.5s and 315s: all three show the torn
hole with real plaster.

Six straight bars and a square centre versus four beaded arms and an arrowhead.
It is not a near-miss; it is a different object, and it is the thing the entire
film is about.

**Cause, and it is good news: this is a pre-canon clip.** The shot is S2K, THE
CROWD GATHERS — camera inside the wall, `loc_wall_pov_e`. **S2K-Fix1 has never
been generated.** The crack canon was written on 2026-09-04 precisely because
every sheet had been carrying a wrong description copied file to file since
August, and this clip predates the fix. Nothing needs rewriting: the corrected
sheet already exists and is sitting in the queue unfired.

**THE FIX — 110.6s to 130.6s.** Fire `s2k-fix1-the-crowd-gathers.txt` as
written. It is a 20-second shot, so either replace it whole, or shoot two 10s
passes and let the editor choose the halves he wants. No prompt change is
needed. This is the highest-value clip left in the entire queue.

---

## FINDING 2 — THE HOLE HAS NO ARMS AT 307.6-312.5s · lower priority

At 308.5s the wall carries a **rectangular torn hole with a crumbling plaster
lip and debris beneath it** — real damage, and it matches the aperture shots at
214s and 315s for texture. But it has **no radiating arms at all**, where the
canon calls for four.

Two readings, and I cannot separate them from frames alone:
- the shot is late enough in the story that the wall has been cut back for
  removal (there are workmen with tools at 302.3-307.6s, immediately before it),
  in which case the missing arms are correct and this is not a defect;
- or it is another pre-canon clip.

**Ask the editor which beat this is before spending a render on it.** If it is
after the removal crew, leave it alone.

---

## NOT DEFECTS — checked and cleared

- **199.5-204.0s exterior.** Looked like a repeat of the 0.0-2.3s opening. It is
  not: this one has **a helicopter over the building**. It is a later beat, the
  press arriving. Leave it.
- **130.6-131.8s**, 1.2s and odd in the thumbnail. Full res shows Carrington in
  white far down the gallery with Dupe near camera, back to us. Clean.
- **264.2-265.8s**, unreadable motion blur in the thumbnail. Full res shows legs
  and a white-trousered figure mid-stride over the terrazzo — a deliberate
  whip/blur, not a corrupt frame.

---

## THE SHOT MAP

Timecodes are cut boundaries; descriptions are from the midpoint frame.

| # | in-out | what |
|---|---|---|
| 0 | 0.0-2.3 | exterior, museum, day |
| 1 | 2.3-10.8 | **Dupe interview, WITH the projector** in near-left foreground |
| 2 | 10.8-16.5 | Dupe pushes the cart down the gallery |
| 3 | 16.5-24.2 | Dupe reaching up at a painting |
| 4 | 24.2-32.4 | Dupe at the painting, cart beside him, plaque on the wall |
| 5 | 32.4-34.0 | Dupe extreme close-up, eyes wide |
| 6 | 34.0-35.5 | long empty gallery, cart far off |
| 7 | 35.5-37.1 | Dupe on the wall phone |
| 8 | 37.1-47.8 | split screen — Dupe on the phone / contractor on scaffolding |
| 9 | 47.8-57.7 | Dupe standing mid-gallery with the cart |
| 10 | 57.7-66.5 | Dupe cleaning the wall, a guard far off |
| 11 | 66.5-72.4 | the elderly man in green leather at a piece |
| 12 | 72.4-96.4 | the guests standing in a row, Dupe left with cart |
| 13 | 96.4-110.6 | the same row, closer, woman in cobalt centre |
| 14 | **110.6-130.6** | **wall-POV, crowd at the crack — WRONG CRACK, see finding 1** |
| 15 | 130.6-131.8 | Carrington far down the gallery, Dupe near, back to us |
| 16 | 131.8-139.4 | Valder with his guards and the crowd |
| 17 | 139.4-144.0 | the group walking, yellow chair at right |
| 18 | 144.0-147.0 | **the yellow armchair, catalogue portrait** (S8a piece 1) |
| 19 | 147.0-150.3 | the group walking, woven form above |
| 20 | 150.3-152.8 | **the woven form, catalogue portrait** (S8a piece 2) |
| 21 | 152.8-156.0 | the group walking past the stone ring |
| 22 | 156.0-158.1 | **the stone ring, catalogue portrait** (S8a piece 3) |
| 23 | 158.1-159.4 | the group walking |
| 24 | 159.4-169.0 | crowd, Valder among them, Dupe present |
| 25 | 169.0-171.8 | Dupe pushes the cart away down the gallery |
| 26 | 171.8-175.8 | Dupe close, eyes down, crowd behind |
| 27 | 175.8-181.6 | Valder close, talking, crowd behind |
| 28 | 181.6-192.1 | long gallery, a green figure walking in far off between two rows |
| 29 | 192.1-196.1 | Carrington, Valder and the woman in green, guards |
| 30 | 196.1-199.5 | Valder close, smiling |
| 31 | 199.5-204.0 | exterior — **with a helicopter**, a later beat |
| 32 | 204.0-211.5 | crowd lining the gallery |
| 33 | 211.5-216.7 | **through the crack** — crowd, an old woman seated in a chair |
| 34 | 216.7-221.3 | the same, from further back |
| 35 | 221.3-226.3 | white gloves fitting the plaque: THE ABSENCE OF MEANING / Valder / 100,000,000 |
| 36 | 226.3-236.9 | old television, newsreader |
| 37 | 236.9-238.5 | exterior, Valder meets the contractor |
| 38-45 | 238.5-253.4 | the two men outside, cut in alternating singles |
| 46 | 253.4-262.0 | the two men at a grey door, facing each other |
| 47 | 262.0-263.5 | gallery, someone kneeling at the wall |
| 48 | 263.5-264.2 | Valder close |
| 49 | 264.2-265.8 | motion blur, legs mid-stride |
| 50 | 265.8-284.0 | crowd in the gallery |
| 51 | 284.0-291.4 | gallery, Valder, Dupe, a woman in purple |
| 52 | 291.4-296.5 | Valder, the registrar with his ledger, the contractor |
| 53 | 296.5-302.3 | Dupe extreme close-up, eyes wide (matches shot 5) |
| 54 | 302.3-307.6 | two workmen with long tools at a white wall, Valder watching |
| 55 | 307.6-312.5 | **the hole alone on a blank wall — no arms, see finding 2** |
| 56 | 312.5-319.7 | the man in maroon, seen through the crack |
| 57 | 319.7-326.1 | Dupe interview with the projector again — the film closes on it |

---

## TWO QUESTIONS FOR THE EDITOR

1. **The projector interview bookends the film** (shots 1 and 57) — but IVR1,
   IVR2 and IVR3 have never been generated and their plate does not exist yet.
   Where did these two come from? If the editor already has usable
   projector-look interview footage, the IVR work and its paid plate may not be
   needed at all.
2. **Shot 55** — is that after the removal crew has cut the wall back? If yes it
   is correct as it stands and finding 2 closes with no render.
