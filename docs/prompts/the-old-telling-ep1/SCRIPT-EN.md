# The Old Telling EP1, first minute: SCRIPT-EN v4 (DRAFT for the CEO, 2026-10-09)

STATUS: draft. Step 5 of `CMO_Standard_TheOldTelling_Script` done; step 6 (3 native readers) NOT done, so no voice or render money is spent yet. Structure = the Thai v3 the CEO passed (same beats, same order, same facts); the words are written fresh in English, not translated. Rival channel for English: Mysteries of Mythology (wiki `research/2026-10-09-cmo-mysteries-of-mythology-top5-script-teardown.md`).

## What changed after the CEO's note of 2026-10-09 (his words kept in the Thai originals in chat)

| CEO | This version |
|---|---|
| Not every clip has to be 15 s; make the B-roll for the sentence and fit its seconds to the voice | H3 takes 4 to 15 s on a grid of 5+17k frames at 24 fps (107, 124, 141 ... 362 frames = 4.46, 5.17, 5.88 ... 15.08 s, steps of 0.71 s; `studio/src/lib/rules.ts`). Plan: voice first, then each shot gets the next grid length above its sentence time, the edit trims the rest |
| Characters may speak, few lines, in English in the video | 3 spoken lines in the minute (king, Orpheus, Eurydice off-screen), 1 to 6 words each, nothing else |
| No subtitles in the video (YouTube makes auto subtitles) | Burned-in subtitles removed. The caption file is not shipped with the master |
| Cover is very good, small change | English twin of the same card (below); tell me the change you want |
| Time passing = black picture with writing | card T1, "Seven months" |
| All text, character voice and picture text are English in the video; dubbing is a separate track per wanted language | Master is English only. Dubs (TH first) are separate audio files laid on the same picture, made only when asked. The Thai narration already made is the first dub draft (needs retiming to the new cut) |

## Beats (v4)

| Id | Voice | Text (English) | Est. s | Picture |
|---|---|---|---|---|
| N1 | narr | In ancient Greece, there lived a musician named Orpheus. | 3.7 | e01 meadow, lyre, dusk |
| N2 | narr | When he played the lyre, even wild animals stopped to listen. | 4.5 | e01 deer, wolf, fox lie still |
| N3 | narr | On his wedding day, a snake bit his wife. She died. | 4.5 | e01 second half: tall grass, silhouette walks off, snake |
| N4 | narr | This is The Old Telling. The version they softened. | 3.7 | e02 first 5 s: the Teller's room, ringed hands, book closes (series ritual line, 0:15 to 0:25) |
| N5 | narr | Orpheus walked down into the underworld, still alive. He played until the king of the dead gave way. | 7.3 | e02 second part: cavern, thrones, he plays |
| C1 | KING | Take her. But do not look back. | 3.3 | NEW shot, 4.5 s: the king on his throne, one line, lip-synced by H3 (the one new render) |
| N6 | narr | He climbed the dark stair. He could not hear her footsteps behind him. | 5.3 | e03 first half: stair, silhouette behind him, no face |
| N7 | narr | Near the light, he could not bear the silence. He turned. | 4.5 | e03 7.2 to 8.4 s: he turns (cut on the turn) |
| C2 | ORPHEUS | Eurydice! | 0.8 | e03 8.4 to 9.2 s: his mouth already opens here; H3's own garbled word muted, English line laid in |
| C3 | EURYDICE (voice only, off-screen) | Farewell. | 0.8 | e03 smoke dissolve at 12 s: silhouette only, never a face |
| N8 | narr | She did not blame him. She was gone. | 3.3 | e03 last 2 s: empty stair, light |
| T1 | card | Seven months later | 2.2 | black card, ember text, 2.2 s, made by hand (CEO: time passing = black picture with writing) |
| N9 | narr | Orpheus sat by the river, weeping. | 3.7 | e04 grey meadow, hands over his face |
| N10 | narr | And this is only the first half. His real ending is far worse. | 5.3 | e04 pull back to the ridge with the torches, hold |

Title card (0:00 to 0:03, over the first frames of the meadow): "The Legend of Orpheus" / "The man who went down to bring his wife back from the underworld" (ember word: underworld). Same card, same palette; English twin of the passed Thai card.

Counted by code: narration 112 words; estimated total 61 s = title 3.2 + lines and narration 52.8 + gaps 4.5 at 2.45 words per second [A]. The real figures come from the ElevenLabs timestamps after the voice read.

## Cost to make it (estimates [A] until measured)

- Voice: English narration about 520 characters plus 3 lines, about $0.05 at $0.08 per 1,000 characters (cap $0.25 approved earlier, $0.07 spent). One more audition read of the Teller costs about $0.04.
- Picture, route A (recommended): recut the four clips we already own to the English sentences and render ONE new short shot (king, 4.5 s), about 0.8 to 1.2 CU [A: 0.15 CU per second of picture measured at 1080p, plus take overhead]. The cap of 25 CU has 15.55 left.
- Picture, route B: render every sentence as its own shot, fit to the voice: about 9 to 11 CU [A], roughly the cost of the first set. Better fit, new faces to check. Suggested for the next episode, where the script is written to the sentence times from the start.
- RunPod $0 (not requested).

## Structure gate (carried from v3)

Goal, obstacle, tactic, reversal and value shift are those of SCRIPT-TH v3 section "Structure gate". The new lines sharpen it: the king's condition is now heard, not narrated, and Eurydice's last word is heard, not narrated.

## Rules that bind (unchanged)

Adults 18+; no red face or red ears; Eurydice only as a silhouette (her voice may be heard, never her face); no gore on screen; no em dash in public text; narration never bound to H3; H3's own voicing of a line is muted and the real line is laid at the mouth opening.

## Thai back-translation (for the CEO to judge step 6 himself; CEO ruling 2026-10-09 "ได้เลย")

Faithful, not literary. N = Teller, C = character, T = black card.

| Id | Thai |
|---|---|
| N1 | ในกรีซโบราณ มีนักดนตรีคนหนึ่งชื่อออร์เฟียส |
| N2 | เมื่อเขาเล่นพิณ แม้สัตว์ป่าก็หยุดฟัง |
| N3 | ในวันแต่งงาน งูกัดภรรยาของเขา เธอตาย |
| N4 | นี่คือ The Old Telling ฉบับที่พวกเขาทำให้เบาลง |
| N5 | ออร์เฟียสเดินลงสู่ยมโลกทั้งที่ยังมีชีวิต เขาเล่นพิณจนราชาแห่งความตายยอมอ่อน |
| C1 กษัตริย์ | พาเธอไปเถิด แต่ห้ามมองกลับมา |
| N6 | เขาไต่ขึ้นบันไดมืด เขาไม่ได้ยินเสียงฝีเท้าของเธอตามหลังมา |
| N7 | ใกล้ถึงแสงสว่าง เขาทนความเงียบไม่ไหว เขาหันกลับไป |
| C2 ออร์เฟียส | ยูริไดซี! |
| C3 ยูริไดซี (เสียงเท่านั้น) | ลาก่อน |
| N8 | เธอไม่ได้โทษเขา เธอหายไปแล้ว |
| T1 การ์ดดำ | เจ็ดเดือนต่อมา |
| N9 | ออร์เฟียสนั่งร้องไห้อยู่ริมแม่น้ำ |
| N10 | และนี่เป็นเพียงครึ่งแรก ตอนจบจริงของเขาเลวร้ายกว่านี้มาก |

Thai dub rule (CEO 2026-10-09): the English picture is cut first and locked. Thai lines are laid on it with their pauses landing on the picture changes. A Thai line longer than its shot may run on; a shorter one gets air (silence). No time-stretch.
