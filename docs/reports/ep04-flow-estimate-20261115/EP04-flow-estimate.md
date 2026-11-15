# EP04 Flow credit estimate (read-only, nothing generated)

Read live on 2026-11-15 ~10:05-10:12 TH from winbox Chrome :9226 (Flow, plan ULTRA), by browser_operator task-81e26a3c.
Setting for every price: video, **เฟรม** (first/last frame) mode, **16:9**, **x1**. Price = the composer's own line "การสร้างจะใช้ N เครดิต" before pressing generate. Generate was never pressed.

**Balance: 6,930 credits** (account panel "เครดิต Google Flow", read before and after the probing: 6,930 both times, so reading spent nothing).

Shot list: EP04-FULL-SHEET.md = 120 shots, every one 15 s. 102 are `Type: flow` (need a Flow clip from a first frame), 18 are still+fx (not Flow). Every flow prompt in the sheet is written as a 15-second brief.

## The deciding fact: only Omni 1.2 Flash can make a 15 s clip

| Model | Seconds offered | Resolutions |
|---|---|---|
| Omni 1.2 Flash | slider 3-15 s (1 s steps) | 360p, 720p |
| Omni 1.1 Flash (retires 5 Dec) | 4, 6, 8, 10 | 360p, 720p |
| Veo 3.1 Lite | 4, 6, 8 | none offered |
| Veo 3.1 Fast (retires 5 Dec) | 4, 6, 8 | none offered |
| Veo 3.1 Quality (retires 5 Dec) | 4, 6, 8 | none offered |

Only Omni 1.2 Flash covers the sheet's 15 s per shot in one clip. For every other model a 15 s shot would need the clip at its maximum length plus a second clip or a re-timed brief; the totals below are for ONE clip per flow shot (102 clips), and a column shows the cost if a second clip per shot is needed.

## Table: 102 clips at each model's longest clip

| Model | Quality | cr/clip | seconds/clip | Total for 102 | Balance after (from 6,930) | Clips the balance covers | If 2 clips per shot (204) |
|---|---|---|---|---|---|---|---|
| **Omni 1.2 Flash** | 720p | **60** | **15** | **6,120** | **810** | 115 | not needed (15 s in one clip) |
| **Omni 1.2 Flash** | 360p | **20** | **15** | **2,040** | **4,890** | 346 | not needed |
| Omni 1.1 Flash | 720p | 15 | 10 | 1,530 | 5,400 | 462 | 3,060 (clip is 10 s, short of 15) |
| Omni 1.1 Flash | 360p | 7 | 10 | 714 | 6,216 | 990 | 1,428 |
| Veo 3.1 Lite | (not shown) | 5 | 8 | 510 | 6,420 | 1,386 | 1,020 |
| Veo 3.1 Fast | (not shown) | 10 | 8 | 1,020 | 5,910 | 693 | 2,040 |
| Veo 3.1 Quality | (not shown) | 100 | 8 | 10,200 | -3,270 (short) | 69 | 20,400 |

## Omni 1.2 Flash full price curve (x1, 16:9, เฟรม)

| seconds | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 360p | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 12 | 14 | 16 | 18 | 20 |
| 720p | 9 | 12 | 15 | 18 | 21 | 24 | 27 | 30 | 36 | 42 | 48 | 54 | 60 |

(360p tooltip in the UI: "สร้างได้เร็วขึ้นที่ความละเอียดต่ำลง" = generates faster at lower resolution.)

## Other prices read (for completeness)

- Omni 1.1 Flash 720p: 4 s = 7, 6 s = 10, 8 s = 12, 10 s = 15. 360p: 4 s = 4, 6 s = 5, 8 s = 6, 10 s = 7.
- Veo 3.1 Lite = 5 cr, Fast = 10 cr, Quality = 100 cr, flat across 4/6/8 s (no resolution control shown).
- x2/x3/x4 multiply the same estimate (not tested, not needed for the plan).

## What the numbers say for the CEO card

- One pass of all 102 flow clips at Omni 1.2 Flash 720p / 15 s costs 6,120 and leaves 810, i.e. about 13 re-shoots at 60. That is thin if any shot is rejected.
- Omni 1.2 Flash 360p / 15 s costs 2,040 and leaves 4,890 (about 81 re-shoots at 720p, or 244 at 360p). 360p is a proof tier; the sheet's final cut needs the 720p take.
- A sensible split to put in front of the CEO: 360p proof pass of all 102 (2,040) then 720p only for the keepers; but a 360p-then-720p approach pays twice for every kept shot (20 + 60 = 80 per shot, 8,160 for 102), which is MORE than going straight to 720p. Straight 720p (6,120) is cheaper unless a large share of shots is rejected at proof.
- Veo options are much cheaper per clip but cannot give 15 s, and Quality is unaffordable. Omni 1.1 Flash, Veo Fast and Veo Quality are listed in the UI as retiring on 5 Dec.

## Not checked / risk

- **Estimates were read with the first-frame slot EMPTY.** The skill (CMO_Knowledge_Flow_Omni1.1 §Cost in เฟรม mode) says a before/after delta with an image attached is unmeasured; I did not attach an image (no picker/upload without a named path, and the scratch project has no assets). Risk: a first frame could change the price; the Omni 1.1 and Veo reads in earlier runs matched the composer line exactly at fire time, so the risk is small but not proven for 1.2.
- Price is the panel estimate, not a ledger charge. Retries, refunds and content-moderated generations are not modelled; a failed shot that is not refunded adds its full price again.
- The balance is a shared Ultra pool: another session's spend between this read (10:12 TH) and the paid run changes it (a 2026-10-02 read showed 668 credits drawn by another user). Re-read before the run.
- Veo shows no resolution control; its output resolution and any later 1080p/4K upscale cost were not measured.
- The 102 count is from `Type: flow` headers in EP04-FULL-SHEET.md. **EP04-S029.png is missing from stills/ep04** (119 pngs + `_incoming`); S029 is a flow shot, so its first frame must exist before the run. Ledger status of the other 101 first frames (approved / rejected) was not checked.
- I did not verify that 15 s Omni 1.2 clips from a first frame hold the brief's 0-5 / 5-12 / 12-15 s beats; the estimate is price only.
- Side effects: the :9226 Chrome was NOT running; I started it with the org's scheduled task MooniexFlowChrome9226 (it opened one Flow tab, signed in as ULTRA, no login typed) and created one empty Flow project (default name) in that tab to get a composer. Nothing generated. The empty project can be deleted by the CEO or kept.
