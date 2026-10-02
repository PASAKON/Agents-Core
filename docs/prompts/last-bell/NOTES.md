# THE LAST BELL — director's notes (CEO's words, verbatim)

Written the moment they were said (CMO_Knowledge_Film_Production §10). Newest at the bottom.

## 2026-10-03 — the order

> อยากได้ Movie จังไหนๆ ก็ generate ได้ไม่จำกัดแล้ว ช่วยเอา Skill การทำ Movie มาหน่อย
> อยากได้แนว อลังการเลย
> ออกแบบเรื่องสั้น 5 บรรทัดมาก่อนนะ

The CTO proposed «ระฆังสุดท้ายแห่งนครน้ำ» in five lines (BIBLE.md §1). The CEO approved it:

> ใช้ได้ ไม่แน่ใจว่าใส่ได้กี่รูป แต่ Champa จะต้องอธิบายรูปภาพ โดยใช้ @ภาพ1 @ภาพ2 @ภาพ3 @ภาพ4
> แบบนี้โดยเรียงตามภาพที่ใส่ตาม Postion เลย ฉันเดาไว้ประมาน 10 Ref
> เอาเนื้องเรื่องตามที่คุณขอ
> โทนแสงขอเป็นย้อมเขียวเหลือง เหนือจิตนาการ
> คุณออกแบบบทต่างๆมา ให้จบภายใน 1 เดือน ราวๆ 8 นาที
> เริ่ม เขียน พอต เรื่องคล้ายวๆ และ สั่ง worker ไป genreat Image มาให้เลือกได้เลย
> ขอตัวละครที่เป็นเอกลักษณ์ เราจะ ทำมันออกมาเป็น English Version นะ แต่มีควมเป็นไทย อยู่ในนั้น
> เพิ่มเติมหน่อย เราไม่สามารถ ทำฉากยาวต่อกันได้แบบ Video to video เพราะฉนั้นเราอาจะต้อง เอา Slot เที่เหลือ มาอ้างอิงให้ AI รู้ว่า ต้อง Continue ฉากจากเดิมที่จุดไหนอะไร ยังไง
> เราจะใช้ Frame สุดท้าย รองสุดท้าย และ รองของสุดท้าย ในจังหวะ Slot ที่เหลือ
> สมมุติว่า เราใส่ได้ 10 slot ใส่ location Charactor porp แล้ว เหลืออีก 3 slot เราจะเอา 3 slot นั้นมาใส่ 3 frame สุดท้ายของ Video ก่อนหน้า ถ้าเราต้องการเล่าต่อจากเดิม
> ส่วนการ เปลื่ยน Location เปลื่ยนฉากไป ฉากอื่นๆ ไม่ต้องใช้ Contonue แบบ ข้างบน ให้เล่า เรื่องต่อจากเดิมได้เลย

> ถามคำถามก่อน เมื่อไม่มั่นใจ

## 2026-10-03 — answers to the CTO's four questions

| Question | CEO's answer |
|---|---|
| What makes the character and location pictures | ChatGPT on winbox (`tools/chatgpt_images.py`, plan, no extra $) |
| How many characters | 5: Kaew, Yai Bua, the Naga, Mek, the Governor |
| Where the English voice comes from | The characters speak inside the clip (Seedance audio; champa's audio is not yet verified) |
| The three "continue" frames | Spaced 0.5 s: the frames at −1.0 s, −0.5 s and the last frame |

## Standing decisions

- Engine: champa.io, Seedance 2.0, 16:9, free Unlimited lane (no money).
- Length about 8 minutes. Finished by **2026-11-02** (one month from 2026-10-03).
- Look: a surreal yellow-green grade ("ย้อมเขียวเหลือง เหนือจินตนาการ").
- English version, with Thai identity inside it.
- The CTO asks before acting on anything it is not sure of.

## Assumptions not yet confirmed (CTO, 2026-10-03)

- Kaew is about 12 and Mek about 14. The Governor is a provincial governor, never royalty: no crown, no royal regalia.
- The city, Suwannawari, is fictional and timeless, built from Thai stilt-house, chedi and naga forms. No real place or period.
- The lullaby is an original Thai lyric written for this film. No existing song.
- The Naga has one head (easier to keep consistent across shots than seven).
