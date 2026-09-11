# «Sorry, Sir» — colour look: PARKED, two finalists

**CEO 2026-09-11:** *"3 กับ 4 ดูโอเคที่สุดเลย ยังตัดสินใจไม่ได้ ให้จดไว้ก่อน รอ Editor ปรับทุกอย่างครบ
เราจะส่ง Final แล้ว"*

**Status: no look is chosen. Do not apply one. Do not ask him to choose again until the
editor's final cut exists.** The decision is deferred on purpose, not forgotten.

---

## The two finalists

| | Look | What it does |
|---|---|---|
| **3** | **V3 Vitrine** | **No tint at all.** Architecture stays a neutral/pale field; saturation pushed hardest of the five (1.62). The costumes and props carry every bit of the colour. |
| **4** | **V4 Rose Hotel** | Everything leans rose/magenta — the closest of the five to the Grand Budapest exterior the CEO used as reference. |

Rejected: **V1 Lacquer** (warm amber — the CEO's own objection was exact: *"ที่คุณย้อมเป็นสีส้มใช่ไหม"*,
it amounts to tinting the whole frame orange), **V2 Confection** (teal shadows + pink highlights),
**V5 Bitter Almond** (olive-gold, faded poster).

## When to pick it up again

**After the editor delivers the final cut**, not before. Grading a locked picture once is
cheaper and safer than grading Draft 6 and re-grading whatever replaces it.

Then: render the final cut in **3 and 4 only**, one minute each from a section containing both a
wide and a close-up, and put them in front of the CEO. One question, two options, done.

## How to reproduce the looks — do NOT hunt for the .cube files

The five cubes are 9 MB each and are **not** in git. They do not need to be: they are a pure
function of `docs/astra-workspace/looks5.py`, which is committed and carries every parameter.

```bash
python3 docs/astra-workspace/looks5.py cube     # writes LUTs/V1..V5 .cube, 65^3
ffmpeg -i <cut>.mp4 -vf "lut3d=LUTs/V3_Vitrine.cube:interp=trilinear" \
       -c:v libx264 -crf 17 -preset medium -pix_fmt yuv420p -c:a copy out.mp4
```

Needs numpy + pillow. On Contabo use a venv — the system python is PEP-668 managed.
**Set `interp=trilinear` explicitly**: ffmpeg defaults to tetrahedral, Resolve's project is set to
trilinear, and a silent mismatch means our preview and the editor's render disagree.

Full film at 8:07 renders in about 10 minutes on Contabo.

## The one open technical issue, already measured

**A look that wins on wide shots can lose on a close-up face.** V3 was clearly best on the hotel
exterior — neutral architecture, electric blue uniforms — and among the worst on Valder's
close-up, where the same chroma push turns his skin sunburnt orange. V2 held skin best and was
unremarkable everywhere else.

So whichever of 3 or 4 is chosen, expect to need **a skin pullback on close-ups** underneath the
shared LUT. That is normal grading structure, not a fault in the look, and Astra's node design
(per-clip correction → shared look) already accommodates it. Budget for it; do not discover it
during the final render.

## The plan for when Final arrives — APPROVED by the CEO 2026-09-11

The CEO's own diagnosis, and it was correct: *"คุณใช้สมการเดียว ปรับตลอดทั้งคลิปโดยไม่ได้ดูเลย"* —
one LUT laid over every frame cannot reconcile shots that started from different balances, and a
shared look **amplifies** that drift instead of hiding it. The missing layer is Astra's node 01,
the per-shot balance, which was never applied: only the shared look was.

Measured on the 4:05–5:05 test minute: **19 cuts in 60 seconds**, so the full film is on the order
of **~150 shots**. That number decides the division of labour, and the CEO approved it:

| | Who | What |
|---|---|---|
| **Measure** | machine (`docs/astra-workspace/shotbalance.py`) | detect every cut, measure each shot's neutral point, pull all ~150 toward a common target. Pure measurement — no taste. |
| **Judge** | **Astra — "ให้ Astra เป็นสมอง"** | only the handful of shots that still read wrong after balancing. That is a session's worth of work, not 150. |
| **Decide** | CEO | the look (3 vs 4) and any shot he wants deliberately off-tone |

`shotbalance.py` is written and committed but **has never been run.** Its safeguards: balance is
measured on low-chroma pixels only (so a red-coat shot is never "corrected" until the coat goes
grey), green is held so it shifts colour and never exposure, gain is clamped to ±25 % and applied
at 75 % strength so deliberate colour survives. It writes `<out>.shots.json` with every shot's
gain and ranks the largest corrections — that ranked list is exactly what Astra should be handed.

## Two reasons nothing runs until the Final cut lands

1. **Draft 6 is not final.** Balancing 150 shots of a cut that is about to change wastes most of
   the work — the same argument the CEO used to park the look itself.
2. **Encode quality — my error, recorded so it is not repeated.** The five 1-minute previews were
   rendered at CRF 20 / preset faster ≈ **2 Mbps**, against Draft 6's own **~7.5 Mbps**. Nearly 4×
   less. Resolution was never the issue (both are 1280×720); the softness was second-generation
   H.264 at a bitrate I chose for fast delivery. **The CEO was judging picture quality on a file I
   had degraded myself.** For anything he judges on, and for every deliverable: CRF 14–16, preset
   slow, or a near-lossless intermediate. Never optimise a review copy for transfer size.

## Provenance

The colour transform is Astra's (`docs/astra-workspace/shared-LUT-source.py`, REPORT-01,
2026-09-11), unchanged. `looks5.py` adds one parameter Astra's version could not express — `lift`,
which raises the black floor for milky shadows; the original neutralises its shadow delta against
luma, so it can tint shadows but never lift them. Everything else is Astra's maths verbatim, which
is what keeps V1–V5 comparable with its A/B/C.

Festival legality: Official Rules §4 permits external colour grading explicitly and names
DaVinci Resolve. A LUT applies a fixed colour transform and generates no imagery.
