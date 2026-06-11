// One-shot: seed CEO pending-task note + dated todos (2026-06-11).
import { api } from "./index.js";

const note = await api.createNote(
  "งานค้างของ CEO — จาก CTO (MoonieX)",
  [
    "โน้ตนี้สร้างโดย CTO ผ่าน LungNote MCP — สรุปงานที่รอมือ CEO",
    "อัปเดตล่าสุด: 2026-06-11 19:15 (UTC+7)",
    "",
    "บริบทวันนี้: ship 7 ชิ้นขึ้น prod — /indicators, บทความ SEO, landing pivot,",
    "เลข rebate ล็อก 15/8, โปสเตอร์ 4 โบรก → หน้า guide, แก้ลิงก์ LINE bot 404,",
    "/links + /links/pasakon (link-in-bio — PARKED รอ CEO อยากสลับเอง)",
  ].join("\n")
);
console.log("note:", note);

const todos = [
  { text: "เปิด session แล้วสั่ง: delegate task-304b144e — Week-1 funnel review (ครบกำหนดวันนี้)", due_at: "2026-06-12T10:00:00+07:00", due_text: "พรุ่งนี้เช้า 10:00" },
  { text: "ส่งคลิป TikTok สั้น 1 คลิป สำหรับหน้า guide โบรกเกอร์ (ช่อง videoUrl เตรียมรอแล้ว เสียบได้ทันที)", due_at: null, due_text: "เมื่อสะดวก" },
  { text: "ส่งรูป headshot พี่กอล์ฟ ถ้าอยากเปลี่ยน avatar หน้า /links/pasakon (ตอนนี้ใช้โลโก้พระจันทร์)", due_at: null, due_text: "optional" },
  { text: "สลับ TikTok bio → mooniex.com/links เมื่อพร้อม (ตอนนี้เลือกใช้ openlink ต่อ — PARKED ไม่เร่ง)", due_at: null, due_text: "PARKED — ตัดสินใจเองเมื่อพร้อม" },
];
for (const t of todos) {
  const r = await api.addTodo(t.text, { dueAt: t.due_at, dueText: t.due_text, noteId: note.id });
  console.log("todo:", r.id, "|", r.text.slice(0, 40), "| due:", r.due_at);
}
console.log("---verify---");
console.log(JSON.stringify(await api.readNote(note.id), null, 2).slice(0, 600));
