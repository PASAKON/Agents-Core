# THE LAST BELL — story v2 and round 2 (2026-10-04, session 671f688f)

The CEO asked, before going to sleep (verbatim, abridged):
"เนื้อเรื่อง + Dialog คุณได้เขียนตาม Skill หรือไม่ ตัวละคร และการดำเนินเรื่องมีเหตุผลหรือป่าว จุดเริ่มต้นของเรื่องคืออะไร
จุดพลิกผันคืออะไร และตอนจบ คืออะไร … อะไรที่ไม่สื่อหรือไม่จำเป็นไม่ต้องแสดงมันออกมา", and approved overnight A/B tests:
"อนุมัติให้ทำ A/B Test ได้ และค่อยๆ เรียนรู้ไปกับการ Generate ไป ได้".

Full audits: `STORY-AUDIT-2026-10-04.md` (scene engine per scene, plot holes, every line) and
`DUPLICATE-LESSONS-2026-10-04.md` (every recorded duplicate-character lesson, with file:line).

## 1 · Honest answer: the story gate was skipped

`CMO_Gate_Story_SceneEngine` (IRON-RULES §51) was never run before wave 1. BIBLE.md still says "plot draft v1, not
yet a locked script", and 40 shots were queued on 2026-10-03. Scenes A and C fail the gate (no reversal), B and E
are partial, D fails because its reversal shifts no visible verdict.

| Beat | v1 shots | What the viewer actually gets in v1 |
|---|---|---|
| Inciting incident | B01 | The Governor announces the storm and leaves the poor behind |
| Twist | D03–D06 | The Naga only capsizes the villain's barge while the crowd cheers, so "No... I woke it" regrets a success |
| Climax / ending | E04–E07 / E08–E10 | The lullaby calms the Naga, it holds back the wave; dawn; Yai's last shot reads as her death |

The five problems a viewer would notice: the twist undoes itself (the legend comes true anyway); the storm comes
before the bell, and "the storm was the Naga" is never on screen; the chain breaks after the Naga is already loose;
"ring it right" is never visibly broken; Kaew is absent from her own climax.

## 2 · v2 — inside the approved spine (BIBLE §1)

Spine line 4: "the bell was never a call. It was the chain that kept the Naga asleep, and the storm was the Naga
all along. Kaew has set it free with her own hands." v2 puts each clause on screen:

| Shot | v2 change | Fixes |
|---|---|---|
| A08b (new B-roll) | Under the yellow lagoon a vast jade shape turns in its sleep | Plants "the storm was the Naga" |
| B06-v2 | Kaew says her goal ("I'll ring the great bell"); "too weak to climb" dropped | Goal locked on screen |
| C08b (new B-roll) | A colossal coil moves inside the mountain wave | The storm is the Naga, seen |
| C09-rs2 | She starts in Yai's rhythm, sees the wave, panics, beats it wild | "Ring it right" visibly broken |
| D03b (new) | A poor family cheers, then the coil crashes onto their street; the child's bell drops | The verdict "she doomed the city" gets an image |
| D03c (new) | Kaew at the rail sees it; her smile dies | Earns her guilt |
| D45 (new, merges D04+D05) | She strikes once more to call it back; the bronze cracks under her own blow; lightning shows the chained naga; "It was never a call. It was a chain." | Her own hands free it; the line states the twist; crack before the bands break (D06 follows) |
| E06b (new) | Kaew keeps tapping as the coil rises like a wall | Hero present in her climax |
| E09-v2 | Yai, alive, answers the bells with her stick | Removes the accidental death |

Cut in the edit (no generation): A02, C07 (fake obstacle), D02; merge A03+A04, C05+C06, B02 into B01 as an
off-screen shout, E02 as an off-screen "Kaew, run!" over E01. E03 can reuse A05/A05b footage as the memory.

## 3 · Rules applied to every round-2 prompt

- **Quiet tail** (`CMO_Standard_Film_PromptFormat` rule 13, CEO 2026-10-04): every voice and story beat ends by 12 s;
  the last beat is a hold. `tools/shortmovie_qc.py stage1` fails any voice in the last 3 s (`tail_voice`). Wave 1
  broke it 5 times in 53 takes (A05 t1/t2 Yai's hum, B01 t2, E03, E04).
- **Longer than 15 s** = split by whole phrases and continue: A05 keeps its take, cut before 12 s, then A05b sings
  the first half of the lullaby; E04 sings the first half, E04b the second.
- **Duplicates** (the Governor doubled in 3 of 5 takes that bind his sheet): every extra dressed in plain brown and
  placed; "the only person in the frame wearing white or gold"; "There is exactly ONE GOVERNOR"; verbatim negatives
  `no duplicate characters, no twins, no character appearing twice`. These held together on Seedance 2.5
  («Sorry, Sir» AB-LEDGER); unproven on Seedance 2.0 until round 2 lands.

## 4 · A/B tests running on the free lane (no money)

| Test | A | B | Decided by |
|---|---|---|---|
| T1 continuation over 15 s | A05b-A: from A05's last 3 frames before the hum, same angle | A05b-B: a close-up cut-in, one frame as a look reference | Does the join hide? Same voice and look? |
| T2 merge vs continue | D04 + D05 (D05 from D04's frames at the 8 s cut) | D45 standalone | Which tells the twist clearly in fewer seconds |
| T3 duplicate fix, reference type | B04-rs2 with the 5-panel sheet (×2 takes) | B04-rs2c with a single full-body crop (×2) | Heads and white jackets counted at full resolution |
| T4 quiet tail | wave 1: 5 of 53 takes had voice in the last 3 s | round 2 with the hold beat | `tail_voice` count |

Results go into the skills as field notes (n=1 each) and into `NOTES.md`.

## 5 · For the CEO in the morning

1. v1 or v2 story (or a mix): the round-2 clips let both be cut.
2. The film runs about 6:46 against 8:00; v2 adds about 40 s. Close the gap with story (a Kaew–Mek beat before
   C01, a closing beat with Yai), not scenery.
3. Still open: B06 soaked or dry (v2 keeps soaked); E04 mallet dark or crimson; E10 bell whole after E08 broken.
