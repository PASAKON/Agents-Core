# ILAG hook demo: six narrator lines about ONE person (ป้าศรี / ศรีนวล)

Story: ขายชื่อ EP.1 (docs/scripts/ep5-ACT1-v3.md). Voice: edge-tts th-TH-NiwatNeural, rate +32% (free). 24 fps, 14 hard cuts
from 0 to 12.00 s, then kit `title` 12.00-14.00 s and kit `rewcard` 14.00-15.00 s. Watermark on every frame.
Shot ids are the script's (S1..); "src" is the time inside ep5-ep1.mp4 (EP1 final runs about 4 s later than the script's
8 s grid for S1-S4, so ids were matched by eye and by dialogue, not by arithmetic).

Hook shape and the truth behind each line:

## 1. A trait with a number: 0.10-2.14 s
"ป้าคนนี้ ตำส้มตำเก็บเงินแปดหมื่น ห้าปี"
- Truth: S6 "แม่ตำส้มตำเก็บมาห้าปี"; S5/S22 the 80,000.
- cut 1  0.00-0.58  S1  src 4.2   the mother pounding at the stall (sub: ป้าคนนี้)
- cut 2  0.58-1.71  S7  src 54.0  the mother chopping garlic (sub: ตำส้มตำเก็บเงินแปดหมื่น)
- cut 3  1.71-2.25  S1  src 8.0   the mother pounding, collector beside her (sub: ห้าปี)

## 2. Widen it: 2.28-3.98 s
"ใครแตะ โดนสากชี้หน้า แม้แต่ลูกชาย"
- Truth: S6 "ห้ามใครแตะเด็ดขาด", the pestle pointed at her son; S5 he asked to borrow it.
- cut 4  2.25-3.29  S6  src 45.0  pestle raised at her son (subs: ใครแตะ, โดนสากชี้หน้า)
- cut 5  3.29-4.08  S6  src 48.0  the son takes it in (sub: แม้แต่ลูกชาย)

## 3. A funny object as proof: 4.12-5.40 s
"แว่นลืมได้ แต่แปดหมื่น อยู่ครบ"
- Truth: S5, her own line "แว่นก็ลืมไว้บ้านอีกแล้ว แต่แปดหมื่นยังอยู่ครบ".
- cut 6  4.08-5.50  S5  src 37.0  phone held at arm's length, squinting (subs: แว่นลืมได้, แต่แปดหมื่น อยู่ครบ)

## 4. An absurd habit: 5.53-7.48 s
"ลูกถามทีไร ตอบว่าไม่มีอะไร ยิ้มสุดฤทธิ์"
- Truth: S3 "ไม่มีอะไรหรอกลูก" with the exaggerated bright smile; she does it again in ACT3 S57 ("พริกมันเข้าตา").
  "ทีไร" is the only generalisation: it rests on those two moments.
- cut 7  5.50-6.17  S3  src 20.5  the son asks what is wrong (sub: ลูกถามทีไร)
- cut 8  6.17-7.58  S3  src 22.5  her bright smile over the papaya (subs: ตอบว่าไม่มีอะไร, ยิ้มสุดฤทธิ์)

## 5. An unfinished "วันนี้...": 7.62-9.77 s
"แต่วันนี้ เจ้าของแผงมาทวงสามพัน แล้วเธอก็..."
- Truth: S1 the collector asks 3,000 for three months of rent; S2 she pleads. The line stops before what she does.
- cut 9  7.58-8.08  S2  src 11.0  the collector at the stall (sub: แต่วันนี้)
- cut 10 8.08-9.25  S1  src 9.5   the collector speaking: the rent (sub: เจ้าของแผงมาทวงสามพัน)
- cut 11 9.25-9.88  S2  src 13.0  the mother, palms pressed together (sub: แล้วเธอก็...)

## 6. The pressure lands on someone else: 9.91-11.66 s
"พรุ่งนี้เที่ยง ลูกชายต้องทำอะไรบางอย่าง"
- Truth: S2 collector "พรุ่งนี้เที่ยงนะป้า"; S7 son "สามพันนี่ ผมหาเองภายในพรุ่งนี้"; S17 the blank cards are the offer he gets.
- cut 12 9.88-10.46   S2  src 17.0  the collector looking back (sub: พรุ่งนี้เที่ยง)
- cut 13 10.46-11.00  S7  src 52.0  the son wiping his hands, jaw set (sub: ลูกชายต้อง)
- cut 14 11.00-12.00  S17 src 133.0 a hand of blank cards fanned out (sub: ทำอะไรบางอย่าง)

## Cards
- 12.00-14.00  kit `title` (blurred S2 background): ขายชื่อ / EP.1 / สามพันแลกชื่อ / คุ้มจริงเหรอ?  (title text taken from the EP1 reels caption; no quote marks)
- 14.00-15.00  kit `rewcard` "ย้อนกลับไปเมื่อเช้านี้" over S1 (src 4.2)

Kept out on purpose: the scam call, the lost money, the twist (ACT2/ACT3) and the ending.
