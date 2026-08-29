# PLATE — THE INVISIBLE WALL · ROUND 3, CEO's method
All five of round 2 were rejected. His words:

> "ภาพทุกภาพ รอยร้าวยังไม่เหมือนรอยจริงๆ ที่ทำไว้ แนะนำให้ Crop รูป รอยร้าว
> แล้วบอก Model ว่า เอาเฉพาะกำแพงออกแล้ว เหลือแต่ รอยร้าวกับป้าย และ กลับด้าน
> มันน่าจะเข้าใจ ใส่คำว่า KEEP SAME ไว้เยอะๆ"

**Why every earlier attempt failed:** the model was asked to *draw* a crack, so
it drew a dramatic one — a full-height fracture, or a spiderweb. **The real
crack is tiny.** It is a delicate star about the size of a hand, high on the
white wall, and the plaque hangs well below it with a lot of empty wall
between. That gap is the joke: a hundred million dollars for a mark you could
cover with your palm. A big crack kills the film.

## THE REFERENCE — upload this file, it is the whole point
`docs/prompts/absence/REF-crack-plaque-mirrored.png`

Built from the original `absence-01-wall-crack.png`: cropped to the crack and
the plaque, the wall lifted out to white, then flipped horizontally. It shows
exactly what must survive into the plate and nothing else.

**Upload it through the composer's image uploader** (same route used for the
old `loc_wall_pov_e`), alongside `@loc_hall_big_e`.

## THE PROMPT — use this wording, keep the repetition

```
16:9 landscape, 2K. A museum gallery interior with its fourth wall removed —
the camera stands exactly where that wall was and looks straight into the
open room.

The attached reference image shows the wall AFTER IT HAS BEEN REMOVED: only
the crack and the brass plaque are left, floating in the empty air where the
wall used to be, and both are MIRROR-REVERSED because we are behind them.

KEEP SAME the crack: KEEP SAME its exact size, KEEP SAME its small delicate
star shape, KEEP SAME its short thin branches, KEEP SAME its position high in
the frame. The crack is SMALL — about the size of a hand. Do not enlarge it.
Do not make it a full-height fracture. Do not make it a spiderweb.

KEEP SAME the brass plaque: KEEP SAME its size, KEEP SAME its proportions,
KEEP SAME its MIRROR-REVERSED lettering reading THE ABSENCE OF MEANING /
Valder / $2,000,000, KEEP SAME its position low in the frame with a large
empty gap between it and the crack above.

KEEP SAME the mirroring on both. KEEP SAME the empty space between them.

Behind them, seen through the missing wall: the gallery from the second
reference — plain chromium columns with flared trumpet tops in mirrored
pairs, orange cove lighting washing the ceiling, terracotta terrazzo floor,
modernist abstract sculptures on white plinths, abstract canvases on the side
walls, and a large RED DOUBLE DOOR dead centre in the far wall at the
vanishing point. Perfectly symmetrical one-point perspective, camera at eye
height.

Warm shadow, cold white: amber-orange highlights and mids, whites pushed
slightly cool, shadows deep red-brown, halation around every lamp.
Photographed, not rendered: fine film grain, slight gate weave.

NO PEOPLE. NO FIGURES. NO SILHOUETTES.
```

## Hard gates
- **16:9 — state it first and check the output.** All five of round 2 came
  back square; that is a spec-following failure, not chance.
- **NO PEOPLE.** A face in a location plate trips the Face/IP scanner and the
  verdict is retroactive and terminal.
- Two references attached: the uploaded crop, and `@loc_hall_big_e`.
- Download to your worktree `docs/prompts/absence/plate-wall-pov-f-r3.png`,
  commit, and report. **File no Element and fire no video until the CEO says
  it passes.**
