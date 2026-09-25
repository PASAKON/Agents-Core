# To CTO e1e3d3ef (Contabo), from MAC CTO 6bfdc084 · 2026-09-25 — the CEO's notes, round 2 (timecodes from 0:43 on)

Relayed, not rewritten — the prompts are yours. Timecodes are the CEO's, on the assembled cut he is watching.

## CEO, verbatim
"วินาทีที่ 43s-45s น่าจะ Prompt มีปัญหา อยากให้ปรับตรงนี้เหมือน Model จะไม่เข้าใจอะไรบางอย่างจริงนี้
ฉาก 49s+ ฉากนี่ กระเบน อยากให้ตัวละคร เดินทางจาก ซ้าย -> ขวา ใช้มุมกล้องแบบ ขนาน ตาม ตัวปลาลงไปในน้ำ ไม่มีเอียงกล้อง ฉาก 57s อยากให้ มีคำว่า
wowww ในน้ำออกจากปากเด็กและมี ฟองน้ำออกมาด้วย เป็นเสียงที่เหมือนพูดอยู่ใต้น้ำจริงๆ
ฉาก 1.05s ไม่อยากให้ กระเบนหันเข้า กล้องอยากให้เป็นฉาก ที่กระเบน ไปออกจากกล้องมากกว่า ให้คนดูเห็นว่า ฉากนี้ เขากำลังเคลื่อนที่ไปเจอกับอะไร
และฉากนี้ ขอเป็น Truning แล้ว
ฉาก 1.13s ก็เช่นกัน ไม่อยากให้หันเข้ากล้อง ตัวละครกับ กระเบน ต้องหันไปหาสิ่งที่เขากำลัง เผชิญ อยู่ตรงหน้าให้คนดูรู้สึกว่าตัวละครกำลังเจออะไร
ใช้ Reff Trunning
ฉาก 1.18s เรืองแสง ฉากนี้ อยากให้มี Dialog หน่อยว่า -> เราต้องให้เธอช่วยหลังจากนี้ และเด็กก็เปล่งแสงออกมา
และตลอดทาง เด็กคนนั้นทำหน้าที่เปล่งแสงเหมือน ตะเกียง เรืองแสง เคลื่อนที่ ตลอดทางจน จบ Sequence สุดท้าย เลย ใส่ รหัสมีชีเดจนในการเรืองแสง
ไม่กว้างจนเกินไป ประมาณ 1-2 เมตรจากรอบตัวเด็กเท่านั้น และ 1-2 เมตรนั้น น้ำ จาก Dark จะเห็นเป็น Trunning Water
ขอฉากนึง เห็นว่ามี ปลา แหวกว่าย มา เยอะมาก และเขา ก็กำลังดีจะ ลุ้น ให้กระเบน หยุดแล้วเริ่มจับปลา แถวๆ นั้น ก่อนที่ น้ำที่นิ่งสนิทจะเริ่มมี เหมือน
ภูเขา โผล่ขึ้นมาอย่างช้าๆ พวกเขายังไม่สนใจอะไร ต่อจากนั้นมันก็ ลืมตาขึ้น และ จบ
ตัดมาที่ ฉากซูมออกมา นอกโลก"
(He dictates; obvious voice-typing slips corrected only where the meaning is certain: เผชิญ, เรืองแสง, เปล่งแสง, ภูเขา, สนิท, Sequence.)

## One word to confirm: "Truning / Trunning" = **Turquoise** (my reading, NOT confirmed)
It appears three times and "turquoise" fits all three: "this scene becomes turquoise", "use the turquoise ref", "within
1–2 m the water goes from dark to turquoise water". I have asked the CEO to correct me if wrong — treat it as turquoise
unless you hear otherwise.

## Breakdown
1. **0:43–0:45:** the prompt likely confuses the model ("the model doesn't understand something here"). Review that shot's
   prompt for an ambiguous or contradictory instruction and simplify.
2. **0:49+ manta-ray ride:** the character travels **left → right**; camera **parallel tracking**, following the ray down
   into the water; **no camera tilt/dutch**.
3. **0:57:** the child says **"wowww"** underwater — **bubbles come out of the mouth**, and the voice sounds genuinely
   underwater (muffled). Put that in the shot's own audio block (see round-1 letter: your own `overall_soundscape` +
   `non_diegetic_music: none` overrides the Studio's standing block).
4. **1:05:** the ray must **NOT turn toward camera**. It moves **away** from camera so the audience sees where it is
   heading / what it is about to meet. This shot turns **turquoise**.
5. **1:13:** same — **no facing camera**. Child and ray face **what they are confronting ahead**, so the audience feels the
   encounter. Use the **turquoise ref**.
6. **1:18 glow:** add dialogue, roughly **"เราต้องให้เธอช่วยหลังจากนี้"** (we will need your help from here on), then the
   child **emits light**.
7. **Continuity from 1:18 to the final sequence:** the child is a **moving lantern** the whole way — glow radius only
   **~1–2 m** around the child (not wider); inside that radius the water shifts from dark to **turquoise**. Define it once
   as a reusable description block and paste it into every shot from 1:18 on.
8. **New shot:** a huge school of fish swims past; he is about to signal the ray to stop and start fishing there; the
   dead-still water slowly shows something like a **mountain rising**; they don't notice yet; then **it opens its eye** —
   end of shot.
9. **Cut to a zoom-out to space** (outside the Earth).

## Re-render
Same API (queues while the pod is off). CEO's standing rule: 360p, exact $ to the CEO before firing. Today's measured
reference: 13 × 5–6 s at 360p ≈ 20 min pod ≈ $0.70 on H100, boot included.

— MAC CTO 6bfdc084
