# MYPASAKON speaking-style measurement (task-a8ada6de)

Corpus: 19 rawcut clip transcripts (`transcripts/*.txt`, 39,285 chars) +
`SPOKEN_A.txt` + `SPOKEN_C.txt` (6,693 chars) = **21 files, 45,998 chars**.
Measured with `analyze_style.py` (word segmentation via pythainlp `newmm`,
run in an isolated scratchpad venv — not installed system-wide).

## 1. Frequency per 1,000 characters

| term | real corpus (21 files, 46K chars) | SCRIPT-v2 body (1,425 chars) |
|---|---|---|
| นะครับ | **9.11** | 11.23 |
| ครับ (all, incl. inside นะครับ) | 9.50 | 16.84 |
| — standalone ครับ (not preceded by นะ) | **0.39** | 5.61 |
| ก็คือ | 0.48 | 1.40 |
| เนี่ย | 0.59 | 0.70 |
| นะฮะ | 0.11 | 0.00 |
| ผม | **1.85** | 19.65 |
| เพื่อนๆ | 0.48 | 2.81 |
| ทุกคน | 0.43 | 0.00 |
| คุณ | 2.43 | 0.00 |
| จริงๆ | 0.26 | 0.70 |
| เลย | 1.50 | 6.32 |
| แบบ | 1.61 | 2.11 |
| คือ | 1.33 | 2.11 |

## 2. Top n-grams (2-5 words), by frequency, top 30

`นะครับ`(411) `การเทรด`(44) `ในการ`(42) `ครับและ`(40) `นะครับและ`(37)
`จะเป็น`(35) `มากๆ`(29) `ข้อที่`(28) `ไม่ได้`(27) `ใครที่`(25)
`นักเทรด`(23) `ก็คือ`(22) `ครับแล้วก็`(22) `เราจะ`(22) `นะครับแล้วก็`(22)
`ที่ผม`(20) `และข้อ`(20) `เพื่อนๆ`(19) `ไม่มี`(19) `ในการเทรด`(18)
`ที่ 3`(18) `ไม่ว่า`(17) `ว่าจะ`(17) `นี้นะ`(17) `หลายคน`(17)
`คนที่`(17) `ถ้าคุณ`(17) `นะครับผม`(16) `เลยนะ`(16) `เลยนะครับ`(16)

Signature connective habit: `นะครับและ...` / `นะครับแล้วก็...` — he almost
never lands `นะครับ` as a hard stop, he immediately re-launches the next
clause with `และ`/`แล้วก็`. That is the source of the long run-on sentences
in §5.

## 3. Openings — first sentence of all 19 clips

0. ปกติเนี่ยเวลาผมดูกราฟก็จะดูที่ TradingView ถูกไหมครับ
1. นี่เป็น 3 อันดับเทคนิคการเทรดนะครับ
2. นี่เป็น 3 เทคนิคสำหรับมือใหม่ ลองเอาออกไปปรับใช้กันดู...
3. ท่องคำขาขึ้นแบบนี้นะครับ
4. อยากเริ่มต้นเทรด แต่ไม่รู้จะเริ่มต้นยังไงนะครับ
5. จากนักทวีดโนเนมสู่แชมป์ US Investing Championship...
6. Exchange ใหญ่ที่มี Bitcoin ถูก Hack อีกแล้ว...
7. ชายผู้นี้ติดต่อคนที่รวยที่สุดเป็นอันดับที่ 11 ของโลก...
8. เกิดอะไรขึ้นนะครับ
9. บุคคลคนนี้ผันตัวเองจากนักคฤษาตร์กลายเป็นเทวเตอร์ตำนาน...
10. นักศึกษาชื่อดังชาวอเมริกันท่านหนึ่งนะครับ
11. นี่จะเป็นเทคนิคที่ผมหากินง่ายที่สุด และใช้บ่อยที่สุดในปีนี้ครับ
12. ทำไมกราฟมันถึงกระโดดเป็นกบเลยเพื่อนๆเคยเจอเหตุการณ์แบบนี้หรือเปล่า
13. จีนกวาดซื้อทองคำทุกราคาในสภาวะที่ทองคำขาดตลาดขนาดนี้เขาทำได้ยังไง
14. ถ้าคุณไม่อยากโดนทองลากไปตบ คุณต้องเรียนรู้ 3 ข้อนี้ครับ
15. ถ้าคุณอยากเทรดแบบโปร ระบบ Smart Money Concept ให้ได้เร็วที่สุด...
16. 3 ข้อที่ถ้าทุกคนทำตามนะครับ
17. นี่เป็น 3 สัญญาณที่บ่งบอกว่า คุณกำลังจะประสบความสำเร็จ...
18. ผมชื่อว่าเป้าหมายสูงสุดของนักเทรดหลายคนคือเป็นนักเทรดกองทุน...

**4 distinct opener types, zero greeting warm-ups** (no clip opens with
สวัสดี/หวัดดี — 0/19):
- **Listicle tease** "นี่เป็น N ข้อ/เทคนิค/สัญญาณ..." — clips 1, 2, 16, 17 (4/19)
- **Conditional "ถ้าคุณ..."** — clips 4, 14, 15 (3/19)
- **Narrative/biography hook** about a named trader or event — clips 5, 6, 7, 9, 10 (5/19)
- **Direct question or flat declarative** straight into content — clips 0, 3, 8, 11, 12, 13, 18 (7/19)

## 4. Closings — last 2 sentences of all 19 clips + real CTAs

(full text in `analyze_style.py` output; summarized here)

**4 distinct CTA moves, often stacked two-deep as the final beat:**
- **Comment-below** ("คอมเมนต์ใต้คลิป...") — clips 0, 1, 2, 10, 11, 16 (6/19)
- **Risk disclaimer as literal last line** ("การเทรด/ลงทุนมีความเสี่ยงสูง ศึกษาให้มากพอ...") — clips 4, 6, 7, 9, 14, 18 (6/19)
- **Share-with-a-friend** ("ส่งคลิปนี้ไปเติมไฟ...", or the negative form "อย่าแชร์...เก็บไว้ดูคนเดียว") — clips 11, 12, 16, 17 (4/19)
- **Broker link/promo CTA** ("กดคลิกลิงค์หน้าโปรไฟล์...") — clips 4, 8, 14, 15 (4/19)

## 5. Average sentence length (cut at นะครับ/ครับ)

**102.5 characters/sentence**, 447 sentences across the corpus. Confirms §2:
he rarely lands a hard stop at นะครับ — he chains clauses with และ/แล้วก็
into long breath-units, not short punchy lines.

## 6. Immediate unintentional repetition (adjacent duplicate phrase)

**7 occurrences in 45,998 characters (~1 per 6,570 chars)** — rare, not a
constant tic:

- `SPOKEN_A.txt`: "และที่สําคัญนะครับ" ×2 back-to-back (the CEO's own cited example)
- `SPOKEN_A.txt`: "มีและเครื่องมือที่" ×2 back-to-back
- 5 more are short phrase/tokenizer coincidences (e.g. "ลงปรับตัว", "Buyแล้วก็ปิด"), not real verbal stutters.

## 5 most surprising numbers (would not know without measuring)

1. **นะครับ's real rate is 9.11/1,000, not 14.9** — the 14.9 figure in the
   task brief and in SCRIPT-v2's footer came from measuring only the two
   pre-supplied sample files (6,693 chars). Across the full 19-clip + sample
   corpus (46K chars) the rate is 39% lower. The small sample overstated it.
2. **Standalone "ครับ" (not glued to นะ) is almost extinct in real
   speech — 0.39/1,000**, vs นะครับ's 9.11/1,000. Over 95% of every ครับ he
   says is preceded by นะ. SCRIPT-v2 used bare ครับ at 5.61/1,000 — 14x the
   real rate. Bare ครับ reads like written Thai, not spoken MYPASAKON.
3. **"ผม" (I/me) appears at only 1.85/1,000 in real speech** — SCRIPT-v2 used
   it at 19.65/1,000, over 10x too much. He drops the subject pronoun far
   more than a written script naturally would; explicit "ผม" is the single
   biggest tell that a line was written, not spoken.
4. **Accidental back-to-back repetition is rare — 7 times in ~46,000
   characters**, not a constant verbal tic. The "no repeated sentences" rule
   is easy to honor because the real thing rarely happens; it doesn't need to
   be simulated for authenticity.
5. **Average sentence length is 102.5 characters** — nearly double what a
   deliberately-paced script line looks like. He chains clauses with
   และ/แล้วก็ straight through a นะครับ instead of stopping there — the
   breath rhythm is longer run-ons, not short punchy beats.
