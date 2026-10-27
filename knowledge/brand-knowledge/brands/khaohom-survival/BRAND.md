# ข้าวหอม Survival ("Survival project") — BRAND truth

Owner: CMO. Written 27 Oct 2026 from PH KhaoHomSurvival #b2ff34d1's kit (approved by the CMO 2026-10-24,
`/opt/MoonieXHQ/Work/khaohom-survival/kit/sheet/out/kit-sheet-v2.png`) and its EP1 upload pack (`ep01/upload/`).

## What it is
- Thai survival lessons as a flat-vector cartoon: each EP is one emergency (EP1 = a Bangkok flood), lived through by
  ข้าวหอม and her grandmother ยายผิน, with every step backed by a named Thai or official source.
- **No name yet (CEO 2026-10-23: "ยังไม่ตั้งชื่อ เอาเป็น survival project ไปก่อน").** No channel name or handle appears
  in any art, end card or description until he names it. The channel waits on his EP1 verdict
  (QG-20261027-0239-fb86: "ขอดู EP1 ก่อน").
- **Job for the viewer:** "tell me what to do first, before it happens to my house." Real competitor: doing nothing
  until the water is in the soi, then searching on a phone (assumed, not measured).

## The picture (16:9 1920x1080 long-form, about 10 min; Shorts are native 9:16)
- Hand-coded SVG plus GSAP only. No AI images, no bitmaps, no stock footage.
- **ข้าวหอม** (Thai woman, 28; the CEO's approved design): `kit/ref/proto-index.tpl` lines 95 onward. Her head is a
  cream rice grain with a teal bob, a mustard top and a red-and-white pha khao ma scarf. Only she has the rice-grain
  head. **ยายผิน** (74, an original design): grey bun, round glasses, lavender sarong, a cane.
- **Colour tokens (LOCKED; `kit/ref/proto-index.tpl` line 9; code wins):**

| token | hex | | token | hex |
|---|---|---|---|---|
| night | `#1B1F3B` | | teal | `#1FA59A` |
| night2 | `#262B52` | | teal2 | `#15786F` |
| wall | `#2E3463` | | red | `#E2453C` |
| lamp | `#FFC86B` | | mustard | `#E9A93A` |
| cream | `#FFF1D6` | | ink | `#121428` (outline, stroke 7) |
| white | `#FFFFFF` | | | |

- Type: Kanit (OFL) for every on-screen word: HUD, cards and the thumbnail.

## The voice (edge-tts, `tools/vo.py`)
| who | voice | rate | pitch |
|---|---|---|---|
| narrator | `th-TH-NiwatNeural` | +0% | +0Hz |
| ข้าวหอม | `th-TH-PremwadeeNeural` | +6% | +0Hz |
| ยายผิน | `th-TH-PremwadeeNeural` | -12% | -18Hz |

## Packaging (one EP)
- **Title:** the viewer's question first, then `| ตอนที่ N <ชื่อตอน>`.
  EP1: "น้ำท่วมเข้าบ้านใน 1 ชั่วโมง ทำอะไรก่อน? | ตอนที่ 1 น้ำมาแล้ว".
- **Thumbnail:** 1280x720, a frame from the episode plus a Kanit title, palette tokens only.
- **Description:** the situation in two lines; "ในตอนนี้" with one line per lesson; the emergency numbers (1669
  medical, ปภ. 1784); the line that this is preparation knowledge and local officials' instructions come first;
  every source with its link; the next EP's title.
- **YouTube settings:** Category Education, not made for kids, language Thai. Altered or synthetic content: No. The
  art is hand-coded and nothing realistic is generated; the voices are stock TTS, not a clone of a real person.
  This is our reading of YouTube's rule; re-check it in YouTube's help at the first upload.
- Cash budget: under 5 THB per EP.

## Hard rules
1. Every safety claim traces to a named source in `facts/` and appears in the description. A claim with no source
   is cut, not softened.
2. No channel name or handle anywhere until the CEO names the channel.
3. One upload per EP; never re-post. Read the channel's uploads before every post.
4. No `·`, `« »` or em dash in any public text: `scripts/check-post-text.sh` passes on the title and description
   before upload (EP1's description fails on three `·` lines as of 27 Oct).
