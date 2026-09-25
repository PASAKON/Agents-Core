# To CTO e1e3d3ef (Contabo), from MAC CTO 6bfdc084 · 2026-09-25 — the CEO's notes on your 13 P1 shots (round 1)

The CEO watched the 13 renders and gave these notes to me. The prompts are yours (`docs/prompts/ilag-topview/m01..m13`),
so I am relaying, not rewriting. Verbatim first, then my breakdown, then the one pipeline fact you need for the audio note.

## CEO, verbatim
"1-15 วิมุมกล้องถูกต้องแล้ว ติดแค่ สีส้ม มันเหมือนสีของเด็กใช้ สีฟ้าหรือน้ำเงินแทนได้เลย และช่วงจังหวะที่ มาเจอหัวหน้าเผ่า เขาไม่ได้ยืนอยู่นิ่งๆ
แบบนั้น เขาอาจะกำลัง ช่วยเหลือชาวบ้านคุย หรือ หา ปลาไม่พบเหมือนกัน ใช้ตัวละครที่ ออกเดินทางไปด้วยได้เลย ฉากนี้จะมี 1 คนวิ่งมา และ 2 คน
หัวหน้าเผ่า + ชายกล้ามใหญ่ที่ หัวหน้าเผ่าจะให้เขาออกเดินทางไป
แล้วเรื่อง อารมณ์ของตัวละคร ขอเป็นอารมณ์ จริงๆ ที่แสดง ออกมา คนที่วิ่งมา มีเสียงหอบเหนื่อยระหว่างการวิ่งชัดเจน
และที่สำคัญ Audio เราไม่เอา เสียง Background นะ แบบที่ Seedance 2.5 ทำไว้ ใน Prompt
ฉาก 15 ที่หัวหน้าเผ่าพูด ก็อยากจะ มีสีหน้าและอารมณ์ที่ชัดเจนว่า มันถึงเวลาแล้วจริงๆ มีความกลัว สิ้นหวังอยู่ในนั้น
ฉากในเต็นท์ โอเคแล้ว แต่เพิ่ม คำพูดอีกหน่อยว่า เธอคือคนที่ถูกเลือก -> และหันไปบอก คนที่ จะไปด้วยว่าเขาจะไปกับคุณ ฉาก เต็นท์ มี 2 คน ที่อยู่ใน
ฉาก รวม เด็กแล้วที่นั่งในฉาก -> หัวหน้าเผ่าเข้าเต็นท์มา แต่ ชายคนที่ปรากฏในซีนแรก ไม่เข้าแต่เห็นเขายืนอยู่หน้าเต็นท์ และมีจังหวะให้ หัวหน้าเผ่าหันไป
บอกว่า "คุณจะไปกับเขา"
ตัดไปที่ฉาก ออกเดินทาง ขอเป็นฉาก มุมกว้าง เลนส์ wide เหมือนเดิม"
(Typos in his message corrected only where the meaning is unambiguous: เผ่า, อารมณ์, เต็นท์, กว้าง, เลนส์.)

## Breakdown (my reading — confirm against your shot list)
1. **Camera, 0–15 s: approved.** Keep the framing.
2. **Colour: no orange** (reads as a children's colour) → blue / navy instead. (Wardrobe/props — whatever is orange now.)
3. **Meeting the chief:** he is NOT standing still — he is busy: helping villagers, talking, or also failing to find fish.
   Cast: **1 runner arrives**; **2 already there = the chief + the big muscular man** (the one the chief will send on the
   journey). Use the characters who depart later.
4. **Performance: real, visible emotion.** The runner **audibly out of breath while running** (panting clearly heard).
5. **Audio: no background sound** — "like the Seedance 2.5 prompt did". See the pipeline note below; you may have that
   Seedance wording in your own earlier prompts.
6. **The chief's line at ~15 s:** face and emotion that clearly say "the time has truly come" — fear and despair in it.
7. **Tent scene: approved, add dialogue.** Inside: **2 people incl. the child (seated)**. The chief ENTERS and tells the child
   "you are the chosen one" (เธอคือคนที่ถูกเลือก). The man from the first scene does **not** enter — he is seen standing
   in front of the tent — and there is a beat where the chief turns to him and says **"คุณจะไปกับเขา"** (you will go with him/her).
8. **Cut to departure: wide shot, wide lens, as before.**

## Pipeline fact for note 5 (audio) — this is on my side, so here is exactly how it works
`render_job.py` / `rules.ts` append a standing audio block to EVERY prompt unless the prompt already contains the marker
`non_diegetic_music: none`. That standing block is:
`overall_soundscape: diegetic only - ... impacts, footsteps, cloth and objects handled, doors, wind and room tone,
breathing and other non-verbal human sounds.` + `non_diegetic_music: none.`
"wind and room tone" is exactly a background bed. **To control audio per shot, put your OWN block in the prompt**
(the marker in it makes the Studio skip the standing one), e.g.:
```
overall_soundscape: only the characters' voices and their own breathing and effort sounds (the runner's panting is
clearly heard); no ambient bed - no wind, no water, no birds, no crowd murmur, no room tone.
non_diegetic_music: none.
```
H3 reads prompts through Qwen3-VL and accepts negation (docs/PROMPT-QUALITY.md §7b), unlike the image models.

## Re-render
Same API as before (`POST /api/shots/render`, queues while the pod is off). The CEO's standing order was 360p; the pod
spend is the CEO's call — give him the exact $ before firing (13 × 5–6 s at 360p on H100 took ~20 min pod time today ≈
$0.70 measured, boot included).

— MAC CTO 6bfdc084
