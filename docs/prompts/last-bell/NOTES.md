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
- Camera, light, lens and colour: skill `CMO_Knowledge_Cinematography_ShortMovie`. CEO 2026-10-03: "ที่สำคัฐ
  อันนี้คือShort Movie ไม่ใช่ ละครสั้นนะ อย่าเอามา ปนกัร" — no lakorn / short-drama rule enters this film.

## Drive (CEO 2026-10-03: "ALL DRAFT/YT: ILAG/The Last Bell/ ตกลง")

Created 2026-10-03 by cto-671f688f, layout copied from THE SHADOW BELOW (`CXO_Rules_GDrive_Filing` §YT: ILAG).
Every upload appends a line to `logs.txt` in the same turn; nothing on this branch is deleted.

| Path | Drive id |
|---|---|
| `ALL DRAFT/YT: ILAG/The Last Bell/` | `1ygI2iuJJGavGO-PwBjDB-oT4JRukOVlS` |
| `logs.txt` | `1vQOSnq9k4RxZI1azm7e_7hUXQ7uo5pKu` |
| `All Scene/` | `1pT0rGcZqnbWE6-fTEdt5nkibzViGfkoV` |
| `Element/` | `1gyKkEl08MUWV3yvwaoN9iUqT1R8LUPxE` |
| `Element/Character/` | `1tppgjOyzPF3W5rDWqDwlm2ELbVd9CWY5` |
| `Element/Location/` | `1mbbtYAq2CQed3V7w5pZfunT3yBjtpYlI` |
| `Element/Prop/` | `1MxP2lwz5pQkVfafTUftHLdR4y0Cq59qA` |
| `Soundtrack/` | `12E2_u7hfIKq0KUajJYbK7oZgjTNypQDT` |
| `Final Draft/` | `1xYY-3WDxxU3XR3lNAT9lA2DqgwpYrIWp` |
| `StoryBoard` (Google Doc) | `1j_mA0HcB7Zd8c5j7wHrenrFIAMWzj5V8JjyGVJMxEIA` |

## Assumptions not yet confirmed (CTO, 2026-10-03)

- Kaew is about 12 and Mek about 14. The Governor is a provincial governor, never royalty: no crown, no royal regalia.
- The city, Suwannawari, is fictional and timeless, built from Thai stilt-house, chedi and naga forms. No real place or period.
- The lullaby is an original Thai lyric written for this film. No existing song.
- The Naga has one head (easier to keep consistent across shots than seven).

## Reference picks (round 1 + two fixes)

- CEO 2026-10-03 08:32, typed in the COO session and relayed by SomPong: "เรื่องหนังเลือก A ได้เลย". The `_a` casting is locked for all five characters.
- CEO 2026-10-03 08:34, same route: "ส่วนงานไหนที่ทำได้ทำไปก่อน blocker ที่ไม่เกี่ยวกับ run หรือ relay ให้ทำต่อได้เลย". The CTO therefore redid the two plates it had flagged:
  - `loc_yai_house-2`: a poor zinc-roofed stilt shack. Round 1's teak house read as wealthy.
  - `ch_naga_a-2`: the same Naga A with its bronze neck bands clearly visible. Made as an edit in the chat of `ch_naga_a`.
- Prompts for the fixes: `docs/ops/briefs/last-bell-refs-round2.json` (ChatGPT on winbox, `tools/chatgpt_images.py --json`).

Locked refs. All are on Drive, each md5 was re-read by file id, and each has a row in `logs.txt`:

| ref | Drive folder | md5 |
|---|---|---|
| ch_kaew_a | Element/Character | f508dc4262f8135a8471278fad7c39be |
| ch_yai_a | Element/Character | 336b5cd757c108cdf4b311faaac0bdfc |
| ch_mek_a | Element/Character | dd7f904d39a0f167b4e69c78121e82f7 |
| ch_governor_a | Element/Character | 0a64cff17cb1e19e06fb2782d4d0ac49 |
| ch_naga_a-2 | Element/Character | 1bcb8a16f293c3b946daf67eadc1aa1f |
| loc_city | Element/Location | 6a212ac7a1c2feac51bf7c63075bf4cb |
| loc_bell_pavilion | Element/Location | a1649af9ab21d72afe7ff9ece10e449c |
| loc_canal | Element/Location | c4cdfb13b5835a1bcc5a32b15bfccb0f |
| loc_yai_house-2 | Element/Location | befdf11e1a032c2397bc3bac1f3fd72d |
| prop_great_bell | Element/Prop | 4846d3de387bcd7729283a28605786ab |
| prop_mallet | Element/Prop | c800212edd7b192858af98861f995abb |
| key_bell_naga | film root (no key-art folder yet) | e1a3d5c0234ebc1194aabbd9a7f3cbe7 |
| key_storm_city | film root | 54eabb4747c6df31d014fd53cc23d53f |

- Superseded: `ch_naga_a`. It is on Drive in Element/Character and is replaced by `-2`.
- Not used: every `ch_*_b` and round 1's `loc_yai_house`. They stay only on winbox in `C:\mooniex\last-bell\refs`.
