# Draft 6 — every shot containing the wall and/or the crack

CTO, 2026-09-11. Source: `Sorry sir THE VALDER Draft 6.mp4` (8:06.75, 1280×720, 24 fps).
Method: scene-cut detection across the whole film (**105 shots, 104 cuts**), per-shot measurement,
then every shot inspected by eye on contact sheets. Not sampled — all 105 were looked at.

**17 shots · 83.8 seconds · 17 % of the film.**

---

## A · The wall with NO people — these are clean plates

The most valuable rows in this document. Same wall, camera locked, nobody in frame.

| Shot | In | Out | Length |
|---|---|---|---|
| #15 | **1:18.46** | **1:21.00** | 2.54 s |
| #38 | **3:56.71** | **3:58.29** | 1.58 s |
| #41 | **4:00.46** | **4:03.71** | 3.25 s |
| #47 | **4:24.71** | **4:26.83** | 2.12 s |
| #62 | **5:06.38** | **5:08.88** | 2.50 s |
| #99 | **7:22.08** | **7:27.00** | 4.92 s — this is the **hole**, not the crack |

**≈ 12 seconds of unobstructed wall, from six separate takes.**

## B · The wall WITH people

| Shot | In | Out | Length | What is in it |
|---|---|---|---|---|
| #10 | 0:47.21 | 0:50.38 | 3.17 s | bellboy at the wall |
| #11 | 0:50.38 | 1:00.79 | 10.42 s | bellboy at the wall |
| #16 | 1:21.00 | 1:32.92 | 11.92 s | old man in green + bellboy |
| #18 | 1:37.62 | 1:41.04 | 3.42 s | old man + bellboy |
| #19 | 1:41.04 | 1:56.88 | 15.83 s | the crowd |
| #21 | 2:13.29 | 2:18.33 | 5.04 s | white gloves mounting the plaque |
| #34 | 3:26.29 | 3:28.17 | 1.88 s | plaque on the wall |
| #66 | 5:19.38 | 5:22.92 | 3.54 s | gloves mounting "THE ABSENCE OF MEANING / Valder / 100,000,000" |
| #84 | 6:09.58 | 6:12.58 | 3.00 s | workman crouched at the plaque |
| #89 | 6:39.12 | 6:41.62 | 2.50 s | workman + bellboy + Valder |
| #91 | 6:44.17 | 6:50.33 | 6.17 s | bellboy standing at the wall |

---

## The finding that decides how hard the work is

**The wall shots are locked off.** Measured as the mean frame-to-frame difference in the four
corners (away from any actor) between the first and last second of each shot:

| Shot | corner drift | |
|---|---|---|
| #15, #38, #41, #47, #62, #99 | **1.46 – 1.67** | locked |
| #91 (bellboy) | **2.68** | locked |
| #16 (old man) | 3.03 | slight drift |

Under ~3 is camera noise, not camera movement.

**This answers the question Astra correctly flagged as the hard one** — *"ถ้าพื้นหลังที่ถูกบัง
ไม่เคยปรากฏในคลิปเลย เราต้องวาดหรือสร้างส่วนนั้นเอง"*. For this film the hidden background
**is** available: six clean takes of the same wall, on a locked camera. Nothing has to be invented,
and with a locked camera there is nothing to track either.

That moves most wall work from Astra's "ยาก" row into its "ค่อนข้างง่าย" row.

## What this makes cheap, and what stays hard

| Job | Difficulty here | Why |
|---|---|---|
| Move the plaque up or down | **easy** | patch its old position from a clean plate, paste it lower |
| Remove / resize / re-shape the crack | **easy** | same |
| Change the plaque's text | **easy** | flat surface, locked camera |
| Remove a prop from the wall | **easy** | clean plate exists |
| Remove a **person** standing at the wall | **moderate** | plate exists, but their soft edges, shadow and floor contact must be handled |
| Anything in the moving gallery shots | **hard** | no plate, camera moves — and no shot in the list needs it |

## Doing it without opening any application

Everything above is arithmetic on pixels — patch a region, feather an edge, match blur, match
grain, composite a layer. **None of it requires Fusion, a GUI, or a desktop session**, and
running it as code has three advantages over doing it by hand in Resolve:

1. **It works today.** Fusion needs an interactive Windows session, which is exactly what neither
   I nor Astra currently has over SSH (`timed out connecting to the Windows sandbox runner`).
2. **It survives a re-cut.** A script re-runs against the new Final in minutes; hand-built Fusion
   nodes on Draft 6 would have to be redone.
3. **It is reviewable.** The patch is a diff, not a memory of what someone clicked.

Fusion becomes the better tool only where a human eye must nudge a spline frame by frame — soft
hair edges, a person's silhouette against a busy background. Nothing in section A needs that.

**Festival legality:** Official Rules §4 permits mask-based retouching and compositing, and
permits patching **from other frames of the same clip** — which is precisely what a clean plate
is. Nothing here generates new imagery. The rule this must never cross is generative fill or AI
inpainting, and none is involved.

## Known target already waiting for this

The plaque's height is baked into the `loc_wall_crack` Element and has survived every prompt
rewrite — re-generating cannot fix it, because the plate itself carries it. It is a locked-camera
flat-surface move with six clean plates available: the cheapest possible instance of this work.
