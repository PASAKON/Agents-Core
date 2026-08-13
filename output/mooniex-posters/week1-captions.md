# TraderMindset — Week 1 (4 posts, MoonieX TradeTech FB)

Source images: `Agents/output/personal-brand/candidates/r{1..4}_final.png`
(also `~/Desktop/mooniex-candidates/random/`). Caption format = claudeflow convention:
"." on its own line = paragraph break; hashtags separate (tags field).

Schedule: 4 posts this week, 19:30 (TH FB evening peak). Order below.

---

## Post 1 — r1_final.png (วินัย)
```
กำไรที่คนอื่นมองไม่เห็น
ไม่ได้ซ่อนอยู่ในอินดิเคเตอร์ตัวไหน
แต่ซ่อนอยู่ใน "วินัย" ของเราครับ
.
คนเก่งทำกำไรได้เป็นไม้ๆ
แต่คนมีวินัย ทำกำไรได้ทั้งเส้นทาง
.
วันนี้เรารักษาวินัยข้อไหนไว้ได้บ้าง?
```
tags: #mooniex #เทรดทอง #XAUUSD #วินัยการเทรด #mindsetเทรดเดอร์ #forexไทย

## Post 2 — r2_final.png (อดทน)
```
ตลาดไม่เคยให้รางวัลคนที่เก่งที่สุด
แต่ให้คนที่ "อยู่รอด" นานที่สุดครับ
.
ความเก่งทำให้เราเข้าออเดอร์ได้สวย
แต่ความอดทน ทำให้เราอยู่ในเกมนานพอ
จนกำไรมันออกดอกผล
.
รีบ ไม่ได้แปลว่าได้ก่อนเสมอไป
```
tags: #mooniex #เทรดเดอร์ #อดทน #forex #เทรดทอง #จิตวิทยาการเทรด

## Post 3 — r3_final.png (โฟกัส)
```
เราคุมตลาดไม่ได้ครับ
แต่เราคุม "ตัวเอง" ได้
.
คุมความเสี่ยงต่อไม้
คุมว่าจะเข้า หรือจะไม่เข้า
คุมว่าจะหยุดตรงไหน
.
โฟกัสสิ่งที่อยู่ในมือเรา
แล้วปล่อยสิ่งที่ไม่ใช่ของเราไป
พอร์ตจะนิ่งขึ้นเยอะเลย
```
tags: #mooniex #จิตวิทยาการเทรด #โฟกัส #riskmanagement #forexไทย #เทรดทอง

## Post 4 — r4_final.png (กำไร)
```
ลองสังเกตดูนะครับ
ไม้ที่เราขาดทุนหนักๆ ส่วนใหญ่มาจากความ "รีบ"
.
รีบเข้าเพราะกลัวตกรถ
รีบแก้เพราะไม่ยอมรับว่าผิด
.
แต่กำไรดีๆ มักมาจากการ "รอ"
รอให้ราคาวิ่งมาหาแผนของเรา
```
tags: #mooniex #เทรดทอง #XAUUSD #patience #forex #เทรดเดอร์สายวินัย

---

## To go live (claudeflow `claudeflow_posts` queue → existing 5-min publish cron)
1. Upload r1..4_final.png to Supabase `claudeflow-media` → public URLs.
2. Insert 4 rows: workflow_key=`trader_mindset`, media_urls=[url], caption=content,
   tags, scheduled_at = the 4 slots, status=READY.
3. Ensure a FB destination (MoonieX TradeTech page) is mapped for `trader_mindset`
   (reuse tradetech's, or add a workflow_destinations row).
4. Existing cron picks up READY posts at scheduled_at and posts to FB. Verify after first.
