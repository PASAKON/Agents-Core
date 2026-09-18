# «บัญชี» องก์ 1 — REWORK SPEC (CEO 2026-09-18: "เราจะเริ่ม Rework องก์ 1 ใหม่ทั้งหมด")

Every rule here was paid for today. The first Act 1 passed every check we had and
the CEO could not follow it. This is what the second one obeys.

## 1. Duration follows the line — never the other way round

Flow offers 4 · 6 · 8 · 10 seconds. Pick the length that fits the speech, then
add one beat of air at most. Thai conversation runs ~4–5 syllables/second; keep
the model comfortable at **~3–4 syl/s**:

| shot length | syllables carried | cost (720p) |
|---|---|---|
| 4 s | 10–16 | 6 |
| 6 s | 16–24 | 9 |
| 8 s | 22–32 | 12 |
| 10 s | 28–40 | 15 |

Measured ceilings: 8 s carried ~30 cleanly (shot 11); ~40 dropped the last two
lines (shot 48). Never exceed the top of the band.

## 2. Air is a beat, never a stretch

Reference reel (1.9M views, 2:03): 11% silent, longest gap 1.7 s.
Our Act 1: ~79% silent, ~6 s of air in every shot.

- No shot opens on silence. The line starts within the first second.
- No gap over ~1.5 s inside a shot, and none at all across a cut.
- A character doing something talks while doing it, about what they are doing,
  or answers the previous line — the CEO's "ทำอะไรอยู่ให้พูดไปด้วย".

## 3. The camera is on the mouth that is speaking

Off-frame speech gets a random voice (measured: shots 9, 28, 31, 39). The
reference reel is close-ups of faces on nearly every shot.

- The speaker's **face is in frame** for the whole line. Medium or close-up.
- Two people talking in one shot: a two-shot where both faces are visible, or
  cut to the speaker. No "voice from the next room".
- Hands, props and inserts are allowed only when nobody is speaking in them —
  and rule 2 says that is almost never. Fold the insert into the shot: the face
  speaks, the hands work below.

## 4. Three chips, every block verbatim

- **≤ 3 chips** per shot (the 4th is silently disabled). Usually 2 characters +
  1 location, or 1 character + 1 prop + 1 location.
- **Attach in the order the prompt numbers them**; verify by thumbnail.
- **SET BLOCK** for the location, **POSTURE BLOCK** for the grandmother,
  **APPEARANCE** for each speaker — pasted verbatim, never paraphrased. They
  live in §7 below.
- **NOT-LIST** per scene: money → notes folded face-down / in the pouch / hand
  closed, no note face, no portrait, no denomination, no notebook, no pen, no
  paper · grandmother → no glasses, hair cropped very short, cannula on ·
  anything the model reached for last time.
- Quoted Thai for anything that must be readable on a sign.

## 5. Voices are cast by the CEO from the full preset list

Today's three men sit within 20 Hz of each other (father 132, son 148, policeman
150 Hz) and the grandmother's preset reads young. The CEO picks from the 30
presets before the re-shoot; a worker rebinds (free); the shoot does not start
until the character pages show the new names.

Emotion goes in the shot prompt, in words, next to the line — Google's own Veo
3.1 form: `he says, in a weary voice: "…"`. Levers that are documented to work:
volume (whispered · hushed · raised · shouting over the noise), emotional state
(weary · delighted · defensive · resigned · quietly furious · tender), pace
(clipped · unhurried · rushing · trailing off), register (formal · casual ·
conspiratorial), physical state (out of breath · voice cracking · through a
smile). One or two per line, never a paragraph.

## 6. Money is never a face

Four of four money shots rendered a Thai banknote face, three with a royal
portrait. Every money beat is staged as: a closed hand, the edge of a fold, the
cloth pouch, a sealed envelope, a drawer seen from above with folded backs. The
amount is always spoken.

## 7. Blocks (paste verbatim)

APPEARANCE สมชาย: a Thai man of 58, lean, with a weathered square face, short greying black hair, deep-set brown eyes and light stubble, wearing a faded dark-blue cotton shopkeeper's apron over a plain white short-sleeved shirt and a worn leather watch on his left wrist
APPEARANCE ต้น: a Thai man of 24, slim, oval-faced, with thick black hair swept back, dark brown eyes, clean-shaven, in a plain grey short-sleeved polo shirt and a thin silver chain — [APRON: CEO to rule ON/OFF in the shop]
APPEARANCE ย่าประนอม + POSTURE: a frail Thai woman of 79, thin, silver-white hair cropped very short and thinning at the temples, deeply wrinkled papery skin, sunken cheeks, cloudy but alert dark eyes, no glasses, in a faded floral-print cotton nightgown, lying propped on two stacked pillows, a thin nasal cannula looped over her ears and a small brass amulet on a string at her neck
APPEARANCE วิทย์: a Thai man of 32, medium athletic build, short neat black hair, clean-shaven, calm steady eyes, in a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist, a canvas bag on his shoulder
SET ร้าน (@noodle_shop): a narrow Bangkok shophouse ground floor turned noodle shop — five worn wooden tables with mismatched plastic stools, a stainless-steel soup cart with a steaming broth pot against the left wall, an open roll-up shutter onto a busy street, a narrow wooden staircase at the back, bare bulbs strung overhead, walls stained pale yellow with age, a laminated payment sign on the counter
SET ห้องย่า (@upstairs_bedroom): a small upstairs bedroom in an old Bangkok shophouse — a single low wooden bed with a scratched wooden side rail against a bare plaster wall marked with cracks and water stains, a grey folded blanket, a small side table holding medicine bottles and a glass of water, an oscillating pedestal fan, one bare bulb hanging from the ceiling and no table lamp, a piece of cloth hanging on the wall near the window, wooden floorboards with visible gaps, a shuttered window letting in one thin band of daylight
SET บันได (@staircase): a narrow steep wooden staircase inside an old Bangkok shophouse — worn treads, a wooden handrail, stairwell walls painted teal-turquoise with peeling paint, a pipe running down the wall, cluttered shop stock on shelving at the foot of the stairs, a single bare bulb on the landing above
SET ตรอกหลัง (@back_alley): a narrow back alley behind an old Bangkok shophouse at night — rough concrete and brick walls, one blue and one red crate, a closed steel rear door, a drain grate in the wet ground, tangled cables, a bicycle against the wall, a single distant streetlamp throwing hard side shadows
STYLE: Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.

## 8. Order of work

1. CEO casts voices → worker rebinds (0 credits) → character pages confirm.
2. Rewrite Act 1 dialogue to density: 20–34 syllables per 8 s equivalent, no gap,
   every line by a face in frame. `tools/shotsheet_lint.py` must PASS.
3. Test 3 shots at 360p (≈ 18 credits): one 4 s, one 8 s at 30 syllables, one
   10 s at 38 — read them back with whisper, confirm nothing is dropped.
4. Shoot Act 1, two operators, **capturing each clip's /edit id at submit**.
5. CTO checks frames + whisper; CEO listens.
