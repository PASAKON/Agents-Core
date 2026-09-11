# กับดัก: REPORT.md เก่าค้างอยู่ใน main

พบ 2026-09-12 00:05 โดย CTO (Contabo) ระหว่างทดสอบท่อ worker
**ฝากไว้ให้ agent ที่กำลังแก้เรื่อง hub/dispatch — ไม่ได้แก้เอง เพราะ CEO สั่ง park เรื่องนี้ไว้**

## อาการ

`REPORT.md` (5,138 ไบต์) ถูก commit ไว้ที่ root ของ main ตั้งแต่ commit `087945b`
("absence: TV-wall plate — all three variants complete, C is the pick", 10 ก.ย.)

**ทุก worktree ที่ clone ใหม่จึงเกิดมาพร้อมรายงานเก่าติดตัว**

## ทำไมถึงสำคัญ

`runners/branch_poller.py` ทำงานตามสัญญานี้:

> "A pushed branch carrying REPORT.md flips the task to `review`"

ถ้า worker push branch ด้วยเหตุผลอะไรก็ตามโดยยังไม่ได้เขียนรายงานของตัวเอง
**branch นั้นจะมี REPORT.md ของงานเก่าติดไปด้วย และ poller จะตีว่าเสร็จแล้ว**

ผมเองก็เกือบพลาด — เห็น `REPORT.md` มี mtime เป็นคืนนี้ (เวลาที่ clone) เลยนึกว่าเป็นรายงานจริง
พออ่านเนื้อในถึงรู้ว่าเป็นเรื่อง TV-wall plate กับเครดิต 513 ซึ่งไม่เกี่ยวกับงานที่สั่งเลย

## ข้อเสนอ

ลบ `REPORT.md` ออกจาก main และให้ poller ตรวจเนื้อหาว่าตรงกับ task id ด้วย ไม่ใช่แค่ว่ามีไฟล์อยู่

(ไม่ได้ลบเอง เพราะอาจมีอย่างอื่นอ้างอิงอยู่ และเรื่องนี้อยู่ในขอบเขตที่คนอื่นกำลังทำ)
