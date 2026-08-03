# YouTube Narration Script - Leopold Aschenbrenner / Situational Awareness Fund (EP2) - v2 (long-form)

- Channel: TRADER UNCUT (@traderuncut, YouTube + TikTok) - real-trader
  stories, documentary-narration tone, white/black/red brand
  (see `design-templates/trader-uncut/BRAND.md` in mooniex-claudesign)
- Working title: "เด็กอายุ 24 ทายอนาคต AI ถูกทุกจุด แต่พอร์ต 45,000 ล้าน หายไปกว่าครึ่งใน 1 เดือน"
- Status: EP2 REDO - v1 (commit 1011c16) ran only ~450 words / ~3.0-3.5 min,
  written before `voices/trader-uncut/VOICE.md` existed. This v2 follows
  VOICE.md's 8-beat structural recipe (empirically derived from 5 benchmark
  transcripts of channel "Uhas Trader") end to end: cold-open hook before
  greeting, dedicated brand-stamp beat, formal greeting/restate, biography
  as primary length driver, a dated real-time walkthrough of the July 2026
  selloff, a mechanics-explainer aside on leverage/margin calls with a
  worked numeric example, a first-person host-narrator layer throughout,
  and an aftermath/lesson/sign-off with two engagement CTAs. Same hedging
  discipline as v1 preserved at the sentence level (see Verification Flags).
- Word count: ~1,616 Thai words + number/English tokens (narration only,
  excludes bracketed cutaway labels and section headers; Thai has no
  inter-word spaces so count is estimated via char-count/4 heuristic, same
  method as v1) - within VOICE.md's own 1,050-1,800 word target for an
  8-12 min script.
- Estimated runtime: ~10.8-12.4 min at 130-150 Thai wpm. At the faster end
  of the range (150 wpm, closer to this channel's actual pace per the
  benchmark transcripts) this lands inside 8-12 min; the slowest-pace edge
  (130 wpm) overshoots by ~0.4 min. Trimmed twice already to get here
  without cutting verified facts or hedging language - flagging this as
  "close enough, minor overshoot on worst-case pacing only" rather than
  silently rounding it away.
- USD→THB conversions use an approximate ~33 บาทต่อดอลลาร์ rate, flagged
  as "คร่าวๆ" (rough) every time - no source in the research brief states
  an exact rate for this date, so figures are stated as estimates only.

---

## [HOOK - 0:00-0:15]

เด็กหนุ่มวัย 24 ปีคนหนึ่งทายทิศทางของ AI ได้ถูกเกือบทุกจุด
เขาระดมทุนตั้งต้นแค่ 225 ล้านดอลลาร์ หรือคิดเป็นเงินไทยคร่าวๆ ก็ราว 7,400 ล้านบาท
แล้วดันพอร์ตพุ่งขึ้นไปแตะจุดสูงสุดที่ประมาณ 45,000 ล้านดอลลาร์ หรือราว 1.5 ล้านล้านบาท ภายในเวลาไม่ถึงปี
แต่แล้วในเดือนเดียว พอร์ตก้อนนั้นก็หายไปมากกว่าครึ่ง เหลือเงินอยู่ราว 10,000 ล้านดอลลาร์ หรือประมาณ 3.3 แสนล้านบาท
เรื่องราวจะเป็นอย่างไร เดี๋ยวเราจะมาดูกันในคลิปนี้

[CUTAWAY: AI chip / data-center b-roll montage, red down-arrow overlay building tension]

## [BRAND STAMP + CTA - short]

นี่คือ TRADER UNCUT ช่องที่พาคุณไปถอดบทเรียนจากเรื่องจริงของนักลงทุนและนักเทรดทั่วโลก
ถ้าอยากได้เครื่องมือเทรดดีๆ หรือโปรโมชั่นพิเศษ ลิงก์อยู่ด้านล่างคลิปเลยนะครับ {{AFFILIATE_LINK}}

[CUTAWAY: TRADER UNCUT logo sting / channel bumper]

## [GREETING + TOPIC RESTATE]

สวัสดีครับคุณผู้ฟังทุกท่าน กลับมาพบกันอีกครั้งกับ TRADER UNCUT
เนื้อหาในวันนี้เราจะพาไปทำความรู้จักกับ Leopold Aschenbrenner อดีตนักวิจัยด้านความปลอดภัยของ AI จาก OpenAI
ที่ผันตัวมาเปิดกองทุนเฮดจ์ฟันด์ของตัวเอง แล้วพอร์ตพุ่งขึ้นเร็วจนน่าตกใจ ก่อนจะเจอบทเรียนราคาแพงในเดือนกรกฎาคมที่ผ่านมา
เรื่องราวจะเป็นอย่างไร ค่อยๆ ไปดูกันทีละขั้นนะครับ

## [BACKSTORY / BIOGRAPHY]

ก่อนอื่นเรามาทำความรู้จักตัวตนของเขากันก่อนนะครับ
Leopold Aschenbrenner เกิดในประเทศเยอรมนี พ่อแม่เป็นแพทย์ทั้งคู่
เขาเป็นเด็กที่เรียนข้ามชั้นมาตลอด จบมัธยมปลายตั้งแต่อายุ 15 ปี
แล้วไปเรียนต่อที่ Columbia University ในสหรัฐฯ จบด้วยเกียรตินิยมอันดับหนึ่งของรุ่นตอนอายุแค่ 19 ปีเท่านั้น
คุณผู้ฟังลองนึกภาพดูนะครับ อายุ 19 ปีคือช่วงที่หลายคนยังเรียนมหาวิทยาลัยไม่จบด้วยซ้ำ

[CUTAWAY: Columbia University campus stock footage / graduation cap graphic]

หลังจบการศึกษา เขาเข้าไปทำงานในทีม Superalignment ของ OpenAI ซึ่งเป็นทีมที่ดูแลเรื่องความปลอดภัยของปัญญาประดิษฐ์ระดับสูง
แต่พอถึงปี 2024 เขาก็ต้องออกจาก OpenAI โดยบริษัทให้เหตุผลว่าเขาเปิดเผยข้อมูลภายในอย่างไม่เหมาะสม
ฝั่ง Aschenbrenner เองออกมาโต้แย้งว่าเอกสารที่เขาแชร์ออกไปเป็นแค่เอกสารวางแผนทั่วไปที่ไม่ได้เป็นความลับอะไรมากมาย
เรื่องนี้ผมต้องบอกตรงๆ ว่ายังไม่มีข้อสรุปชัดเจนจากทั้งสองฝ่ายนะครับ เพราะฉะนั้นเราฟังไว้เป็นข้อมูลทั้งสองด้าน ไม่ตัดสินใครถูกใครผิด

[CUTAWAY: OpenAI office exterior stock footage / "Superalignment" text card]

หลังออกจาก OpenAI เขาเขียนบทความยาวชื่อ Situational Awareness: The Decade Ahead
ทำนายว่าโลกกำลังจะเข้าสู่ยุคที่ AI ต้องการโครงสร้างพื้นฐานมหาศาล ทั้งชิปประมวลผล หน่วยความจำ ศูนย์ข้อมูล ไปจนถึงพลังงานไฟฟ้า
บทความนี้ได้รับความสนใจอย่างมากในวงการเทคโนโลยี และมันคือจุดเริ่มต้นของสิ่งที่เกิดขึ้นต่อมา
เดือนกรกฎาคม 2024 เขาก่อตั้งกองทุนชื่อ Situational Awareness ด้วยเงินทุนตั้งต้น 225 ล้านดอลลาร์ หรือราว 7,400 ล้านบาท
นักลงทุนรุ่นแรกมีทั้งผู้ร่วมก่อตั้ง Stripe และ Nat Friedman นักลงทุนชื่อดังในวงการเทคโนโลยี

[CUTAWAY: kinetic typography - "$225M seed / ~7,400 ล้านบาท" building up]

แนวคิดการลงทุนของเขาไม่ซับซ้อน เขามองว่า AI ต้องการโครงสร้างพื้นฐานมหาศาล เลยเข้าซื้อหุ้นกลุ่มนั้นโดยตรง
อย่าง SK Hynix ผู้ผลิตหน่วยความจำรายใหญ่ และ CoreWeave บริษัทคลาวด์สำหรับ AI พร้อมกันนั้นก็ short หุ้นกลุ่มซอฟต์แวร์ที่มองว่าเสี่ยงถูก AI แทนที่
ตามรายงานของ Wall Street Journal ผลตอบแทนกองทุนตั้งแต่ต้นปีถึงมิถุนายน 2026 พุ่งขึ้นกว่า 1,000% แม้บางสำนักข่าวจะรายงานตัวเลขต่างออกไปที่ราว 439% ก็ตาม
ไม่ว่าตัวเลขจริงจะเป็นเท่าไหร่ สิ่งที่ยืนยันตรงกันคือพอร์ตของเขาพุ่งจนแตะจุดสูงสุดประมาณ 45,000 ล้านดอลลาร์ หรือราว 1.5 ล้านล้านบาทในเดือนกรกฎาคม 2026 โดยใช้เลเวอเรจในตลาดสาธารณะสูงถึง 400%
ตรงนี้แหละครับที่ผมอยากให้คุณผู้ฟังจำไว้ให้ดี เพราะมันคือกุญแจของเรื่องทั้งหมดที่จะเกิดขึ้นต่อไป

[CUTAWAY: leverage multiplier animation - "400% leverage" stamp / margin bar filling red]

## [REAL-TIME WALKTHROUGH - the July 2026 selloff]

ก่อนไปดูว่าเกิดอะไรขึ้น ผมอยากพาคุณผู้ฟังไล่ตามไทม์ไลน์ของข่าวจริงที่ทยอยออกมาก่อนนะครับ
วันที่ 30 กรกฎาคม 2026 CNBC รายงานเป็นครั้งแรกว่ากองทุน Situational Awareness กำลังเผชิญการขาดทุนหนักจากหุ้นกลุ่ม AI ตลาดเริ่มจับตาทันที เพราะกองทุนนี้เพิ่งพุ่งไปแตะจุดสูงสุดเมื่อไม่กี่สัปดาห์ก่อนหน้านั้นเอง

[CUTAWAY: semiconductor stock chart red candles / breaking-news headline card dated "30 July"]

เพียงวันถัดมา คือวันที่ 31 กรกฎาคม CNBC รายงานตามมาอีกสองชิ้นติดๆ กัน
ชิ้นแรกอธิบายว่าทำไมกองทุนถึงพังลงขนาดนี้ ชิ้นที่สองรายงานว่ากองทุนต้องเทขายพอร์ตหุ้นสาธารณะก้อนใหญ่
ซึ่งมีมูลค่ารวมประมาณ 16,000 ถึง 20,000 ล้านดอลลาร์ หรือราว 5.3 ถึง 6.6 แสนล้านบาท ให้กับ Citadel กองทุนของ Ken Griffin ในราคาที่ต่ำกว่าราคาตลาด
นี่คือสิ่งที่เรียกว่า fire sale หรือการเทขายฉุกเฉินเพื่อหาสภาพคล่อง

[CUTAWAY: fire-sale headline card / Citadel logo graphic]

สาเหตุหลักคือหุ้นกลุ่มเซมิคอนดักเตอร์ที่กองทุนถืออยู่หนักๆ อย่าง SK Hynix เจอแรงเทขายอย่างรุนแรงในช่วงเวลาไล่เลี่ยกัน
พอราคาสินทรัพย์ที่ใช้เลเวอเรจอยู่ร่วงลง โบรกเกอร์ก็เริ่มเรียก margin call หรือเรียกให้เติมเงินประกันเข้าพอร์ต
ถ้าเติมไม่ทันหรือเติมไม่พอ ระบบก็จะบังคับปิดสถานะโดยอัตโนมัติ
เหตุการณ์นี้เกิดขึ้นถี่และแรงมากภายในเดือนกรกฎาคมเดือนเดียว จนกองทุนเสียมูลค่าไปรวมประมาณ 67% ภายในเดือนนั้นเดือนเดียว
คุณผู้ฟังลองคิดดูนะครับ พอร์ตที่ใช้เวลาสร้างมาเกือบปีเต็ม ใช้เวลาแค่ไม่กี่สัปดาห์ในการทำลายมันไปมากกว่าครึ่ง

[CUTAWAY: margin-call animation - red bar filling downward, "-67% in July" stamp]

มีรายละเอียดอีกจุดหนึ่งที่ผมอยากเล่าให้ฟังไว้ แต่ต้องบอกก่อนว่ามาจากแหล่งข่าวเดียวคือ Inc.com เท่านั้น ยังไม่มีสำนักข่าวอื่นยืนยันซ้ำ
มีรายงานว่าก่อนข่าวขาดทุนจะแพร่ออกไปไม่กี่วัน กองทุนได้ขอเงินทุนเพิ่มจากนักลงทุนเดิม ผมเล่าไว้เป็นข้อมูลประกอบ แต่ยังถือว่าต้องระวังไว้ก่อนนะครับ

## [MECHANICS EXPLAINER ASIDE - leverage & margin calls]

ก่อนที่เราจะไปต่อ ผมอยากที่จะทำความเข้าใจเรื่องเลเวอเรจกับ margin call ให้ตรงกันก่อนนะครับ เผื่อคุณผู้ฟังบางคนยังไม่คุ้นเคยกับคำสองคำนี้
สมมติง่ายๆ ว่าคุณมีเงินทุน 100 บาท แล้วใช้เลเวอเรจ 400% เท่ากับควบคุมสินทรัพย์มูลค่ารวม 400 บาท ทั้งที่มีเงินจริงแค่ 100 บาท
ทีนี้ถ้าสินทรัพย์ตัวนั้นราคาตกลงแค่ 25% พอร์ต 400 บาทจะเสียมูลค่าไป 100 บาทพอดี เท่ากับเงินทุนทั้งหมดของคุณหายไปหมดเกลี้ยงในทันที
นี่แค่ตัวอย่างสมมติใช้ตัวเลขกลมๆ ให้เห็นภาพเท่านั้นนะครับ ไม่ใช่ตัวเลขจริงของกองทุนนี้
ในโลกจริง ถ้าราคายังตกต่อ โบรกเกอร์จะเรียก margin call ให้เติมเงินเข้าไปเพิ่ม เติมไม่ทันระบบก็บังคับปิดสถานะอัตโนมัติ
ยิ่งเลเวอเรจสูงเท่าไหร่ ระยะที่ราคาต้องขยับก่อนพอร์ตจะพังก็ยิ่งแคบลง นี่คือเหตุผลที่กองทุนเลเวอเรจ 400% ถึงพังเร็วขนาดนี้เมื่อตลาดพลิกทิศทาง

[CUTAWAY: leverage worked-example info-graphic - "100 -> 400 -> -25% -> 0" walkthrough card]

## [RESULT / AFTERMATH]

กลับมาที่กองทุนของ Aschenbrenner กันต่อนะครับ
หลังการเทขายครั้งใหญ่ AUM หรือมูลค่าสินทรัพย์ภายใต้การบริหารร่วงจากจุดสูงสุดประมาณ 45,000 ล้านดอลลาร์ เหลือประมาณ 10,000 ล้านดอลลาร์ หรือราว 3.3 แสนล้านบาท
แต่ตรงนี้ผมอยากให้ฟังให้ครบนะครับ เพราะหลายคนอาจเข้าใจผิดว่า Aschenbrenner สิ้นเนื้อประดาตัวไปแล้ว ซึ่งไม่ใช่ความจริง
ส่วนพอร์ตที่เป็นการลงทุนภาคเอกชน คิดเป็นประมาณ 34% ของพอร์ตเดิม รวมถึงหุ้น Anthropic มูลค่าหลายพันล้านดอลลาร์ที่เขาถืออยู่ ไม่ได้รับผลกระทบจากการเทขายในตลาดสาธารณะครั้งนี้เลย
สิ่งที่พังไปคือเดิมพันที่ใช้เลเวอเรจหนักในตลาดเปิด ไม่ใช่ทรัพย์สินส่วนตัวทั้งหมดของเขา และก็ยังไม่มีแหล่งข่าวไหนยืนยันชัดเจนว่าปีนี้โดยรวมเขายังกำไรหรือขาดทุนสุทธิกันแน่
พูดได้แค่ว่ากองทุนเจอความเสียหายหนักในเดือนกรกฎาคม แต่ยังไม่ถึงขั้นล้มละลายอย่างที่บางคนพูดกัน

[CUTAWAY: split-screen graphic - "$45B -> $10B public" vs "private Anthropic stake, untouched"]

## [LESSON / CTA + SIGN-OFF]

ถ้ามองภาพรวมทั้งหมด สิ่งที่น่าสนใจที่สุดสำหรับผมไม่ใช่ว่า Aschenbrenner ทายผิด เขาทายทิศทาง AI ถูกเกือบทุกจุดจริงๆ
ปัญหาไม่ได้อยู่ที่มุมมองของเขา แต่อยู่ที่ขนาดของการเดิมพันและระดับเลเวอเรจที่ใช้ ต่อให้มุมมองถูกทุกอย่าง ถ้าขนาดโพซิชันไม่สัมพันธ์กับความเสี่ยงที่รับได้จริง ตลาดแกว่งแค่ครั้งเดียวก็เอาคืนไปมากกว่าครึ่งได้ เหมือนที่เห็นในเดือนกรกฎาคมที่ผ่านมา
บทเรียนนี้ใช้ได้กับทุกคนนะครับ ไม่ว่าพอร์ตเล็กแค่ไหน ถ้าไม่บริหารขนาดโพซิชันให้เหมาะสม เลเวอเรจก็พร้อมกลายเป็นดาบสองคมเสมอ

ก่อนไปนะครับ ถ้าคลิปนี้มีประโยชน์ ฝากกดไลก์ กดซับสไครบ์ TRADER UNCUT ไว้ด้วยนะครับ จะได้ไม่พลาดเรื่องราวนักเทรดและนักลงทุนคนต่อไป
และถ้าอยากบริหารความเสี่ยงในพอร์ตของคุณเองให้ดีขึ้นตั้งแต่วันนี้ ลิงก์อยู่ด้านล่างคลิปเลยครับ {{AFFILIATE_LINK}}

[CUTAWAY: MoonieX branded end card / logo lockup]

แล้วถ้าคุณผู้ฟังอยากให้เราถอดเรื่องราวของนักเทรดหรือนักลงทุนคนไหนต่อ คอมเมนต์บอกกันไว้ข้างล่างได้เลยนะครับ เดี๋ยวคลิปหน้าเจอกันใหม่ สวัสดีครับ

[CUTAWAY: TRADER UNCUT outro sting]

---

## Verification Flags

1. **Gain-percentage figure through June 2026 (disputed)** - cited by
   naming the source: "ตามรายงานของ Wall Street Journal ... พุ่งขึ้นกว่า
   1,000%", immediately followed by "แม้บางสำนักข่าวจะรายงานตัวเลขไว้
   ต่างออกไปที่ราว 439% ก็ตาม" - neither averaged nor invented; one figure
   attributed by name, the conflicting figure surfaced explicitly.
2. **"Not personally ruined" framing** - respected and expanded. Script
   states the ~$10B AUM the fund retains, the untouched ~34%
   private-investment slice including the multibillion-dollar Anthropic
   stake, and explicitly says "Aschenbrenner สิ้นเนื้อประดาตัวไปแล้ว ซึ่ง
   ไม่ใช่ความจริง" - never uses "broke"/"ruined"/"ล้มละลาย" as fact; frames
   the loss as "the leveraged public bet imploded."
3. **2024 OpenAI dismissal** - both sides represented: OpenAI's stated
   reason (improper disclosure of internal information) and
   Aschenbrenner's dispute of it ("ไม่ได้เป็นความลับอะไรมากมาย"), closed
   with "ยังไม่มีข้อสรุปชัดเจนจากทั้งสองฝ่าย" - neither side stated as
   settled fact.
4. **"Personally profitable for 2026" claim** - deliberately excluded as
   a stated fact; script explicitly says no source confirms this either
   way ("ยังไม่มีแหล่งข่าวไหนยืนยันชัดเจนว่าปีนี้โดยรวมเขายังเป็นกำไรหรือ
   ขาดทุนสุทธิกันแน่").
5. **Inc.com "asked investors for more money days before" detail** -
   included but explicitly flagged in-script as single-source,
   uncorroborated ("มาจากแหล่งข่าวเดียวคือ Inc.com ยังไม่มีสำนักข่าวอื่น
   ยืนยันซ้ำ") rather than presented as settled fact - stronger hedge than
   simply omitting it, matches VOICE.md's real-time-walkthrough technique
   while keeping the sentence-level discipline from v1.
6. **Real-time walkthrough dates (30/31 July 2026)** - drawn directly from
   the three dated CNBC article URLs in the research brief (steep-losses
   piece dated 2026-07-30; fire-sale and why-it-imploded pieces dated
   2026-07-31). No invented hour-by-hour granularity - the walkthrough
   paces itself around the actual reporting dates the brief supports,
   per VOICE.md beat 5's instruction not to fabricate false blow-by-blow
   detail.
7. **Leverage/margin-call worked example (100 -> 400 -> -25% -> 0)** - an
   illustrative, explicitly-labeled hypothetical ("ตัวอย่างสมมติที่ใช้
   ตัวเลขกลมๆ... ไม่ใช่ตัวเลขจริงของกองทุนนี้"), not a claimed fact about
   Aschenbrenner's actual fund positions - matches VOICE.md beat 6.
8. **Verified spine numbers** - $225M seed, ~$45B peak AUM, 400% leverage,
   -67% in July 2026, ~$10B AUM after, $16-20B forced sale to Citadel at a
   discount, ~34% untouched private stake - all stated as fact per the
   VERIFIED section (CNBC x3, IBTimes, Inc.com, TradingKey).
9. **Biography (Columbia, physician parents, skipped grades, age-15
   graduation, age-19 valedictorian)** - stated as fact per the research
   brief's VERIFIED section (IBTimes). No invented daily-routine or
   personality detail was added per VOICE.md beat 4's explicit
   instruction to substitute verified career/context facts instead of
   fabricating biographical color when granular personal detail isn't
   sourced.
10. **USD->THB conversions (~33 บาทต่อดอลลาร์)** - the research brief does
    not name an exchange rate for this date. Every conversion in-script is
    stated as an approximation ("คร่าวๆ", "ประมาณ", "ราว") rather than a
    precise figure - flagging for CMO/CEO to confirm or adjust the rate
    used if precision matters for this clip.

## Cutaway / B-roll Notes for video_editor

- 13 cutaway beats total, averaging roughly one every 45-60s of narration -
  matches VOICE.md's "one cutaway every 45-75 seconds" density guidance
  for an 8-12 min script (more than v1's 6, proportional to the ~3x longer
  runtime).
- No real Aschenbrenner likeness scripted - none verified as licensed;
  cutaways specify generic AI-infrastructure/finance stock footage,
  kinetic typography, dated breaking-news headline cards, or data-driven
  graphic cards only.
- Two beats need the most graphic-design care: the "$45B -> $10B public /
  private Anthropic stake untouched" split-screen (RESULT section) and the
  leverage worked-example walkthrough card ("100 -> 400 -> -25% -> 0",
  MECHANICS section) - both carry a nuance that needs to read correctly at
  a glance, flag to CMO if either needs simplifying for a fast cut.
- The two dated-headline cards ("30 July" / "31 July" CNBC pieces) should
  visually read as real news-breaking, not stylized - they're doing the
  real-time-walkthrough pacing job VOICE.md calls for.
