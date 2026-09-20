import type { FleetNode, Message, Room } from "../types";

export const rooms: Room[] = [
  { id: "command", name: "command-center", unread: 3 },
  { id: "product", name: "product-design" },
  { id: "research", name: "research-lab", unread: 8 },
  { id: "ops", name: "node-operations", private: true },
];

export const fleet: FleetNode[] = [
  {
    id: "mac-studio",
    name: "Mac Studio M1",
    platform: "macOS · Apple Silicon",
    location: "Bangkok",
    status: "online",
    cpu: 18,
    memory: 42,
    sessions: 2,
    capabilities: ["Claude Code", "Computer Use", "Design"],
  },
  {
    id: "winbox",
    name: "Winbox",
    platform: "Windows 11 · x64",
    location: "Local",
    status: "busy",
    cpu: 64,
    memory: 58,
    sessions: 2,
    capabilities: ["Codex", "Terminal", "Browser"],
  },
  {
    id: "contabo",
    name: "Contabo Core",
    platform: "Ubuntu · Remote",
    location: "Singapore",
    status: "online",
    cpu: 31,
    memory: 37,
    sessions: 1,
    capabilities: ["24/7", "Scheduler", "MCP"],
  },
];

export const initialMessages: Message[] = [
  {
    id: "m1",
    author: "You",
    role: "Owner",
    accent: "#efc06a",
    initials: "PK",
    time: "10:41",
    body: "ช่วยวางโครงสร้าง MoonieX Core, Node และ App ให้แต่ละเครื่องแบ่งงานกันโดยไม่รบกวนผู้ใช้",
    mentions: ["@CTO", "@Codex", "@Claude"],
  },
  {
    id: "m2",
    author: "MoonieX CTO",
    role: "Orchestrator",
    accent: "#9f8cff",
    initials: "CT",
    time: "10:42",
    body: "รับงานแล้ว ฉันจะแยก control plane ออกจาก execution plane และเลือก Node ตาม capability, load และ permission ที่ได้รับ",
    event: {
      label: "Mission delegated",
      detail: "3 workers across 2 nodes · approval required before external actions",
      status: "running",
    },
  },
  {
    id: "m3",
    author: "Codex",
    role: "Worker · Winbox",
    accent: "#66d9c5",
    initials: "CX",
    time: "10:44",
    body: "Repository boundary พร้อมแล้ว กำลังสร้าง Desktop control surface แยกจาก Core เพื่อให้ปิด App ได้โดยงานบน Node ยังเดินต่อ",
  },
  {
    id: "m4",
    author: "Claude",
    role: "Worker · Mac Studio",
    accent: "#f19b70",
    initials: "CL",
    time: "10:45",
    body: "ฉันกำลังตรวจ interaction และ accessibility บน macOS ส่วน Node จะประกาศเฉพาะเครื่องมือที่เจ้าของอนุญาต",
    event: {
      label: "Review checkpoint",
      detail: "Waiting for interface contract from MoonieX Core",
      status: "waiting",
    },
  },
];
