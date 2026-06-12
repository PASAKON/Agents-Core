#!/usr/bin/env node
// LungNote MCP server — stdio. Wraps the LungNote Supabase (notes + todos)
// scoped to one user (LUNGNOTE_USER_EMAIL, resolved via auth.admin at boot).
// Register: claude mcp add --scope user lungnote -- node <abs path>/index.js
//
// RULE (CEO 2026-06-12, บังคับทุก user): ทุกการ "ใส่" ผ่าน Claude MCP —
// create_note / append_note / add_todo — โน้ตปลายทางต้องถูก tag "Claude" เสมอ
// (find-or-create ต่อ user + upsert idempotent) เพื่อให้รู้ว่ารายการนั้น
// Claude เป็นคนเพิ่ม. เพิ่ม write-path ใหม่เมื่อไหร่ ต้องเรียก tagNoteClaude ด้วย.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createClient } from "@supabase/supabase-js";
import { z } from "zod";
import { config } from "dotenv";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

config({ path: join(dirname(fileURLToPath(import.meta.url)), ".env") });

const { SUPABASE_URL, SUPABASE_SECRET_KEY, LUNGNOTE_USER_EMAIL } = process.env;
if (!SUPABASE_URL || !SUPABASE_SECRET_KEY || !LUNGNOTE_USER_EMAIL) {
  console.error("lungnote-mcp: missing SUPABASE_URL / SUPABASE_SECRET_KEY / LUNGNOTE_USER_EMAIL in .env");
  process.exit(1);
}

const db = createClient(SUPABASE_URL, SUPABASE_SECRET_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});

let cachedUserId = null;
export async function resolveUserId() {
  if (cachedUserId) return cachedUserId;
  // Prefer explicit id — LungNote auth has shadow email-users that never sign in
  // (see LungNote-webapp issue: email user pass.gob1 ≠ real LINE-login account),
  // so email lookup is NOT trustworthy for this product.
  if (process.env.LUNGNOTE_USER_ID) return (cachedUserId = process.env.LUNGNOTE_USER_ID);
  let page = 1;
  // paginate auth users until the Google-login email matches
  for (;;) {
    const { data, error } = await db.auth.admin.listUsers({ page, perPage: 200 });
    if (error) throw new Error(`auth.listUsers failed: ${error.message}`);
    const hit = data.users.find(
      (u) => (u.email || "").toLowerCase() === LUNGNOTE_USER_EMAIL.toLowerCase()
    );
    if (hit) return (cachedUserId = hit.id);
    if (data.users.length < 200) break;
    page += 1;
  }
  throw new Error(`no LungNote auth user with email ${LUNGNOTE_USER_EMAIL}`);
}

const fail = (e) => ({ content: [{ type: "text", text: `ERROR: ${e.message || e}` }], isError: true });
const ok = (obj) => ({ content: [{ type: "text", text: JSON.stringify(obj, null, 2) }] });

export const api = {
  async searchNotes(query, limit = 10) {
    const uid = await resolveUserId();
    const { data, error } = await db
      .from("lungnote_notes")
      .select("id,title,updated_at")
      .eq("user_id", uid)
      .or(`title.ilike.%${query}%,body.ilike.%${query}%`)
      .order("updated_at", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return data;
  },
  async readNote(noteId) {
    const uid = await resolveUserId();
    const { data: note, error } = await db
      .from("lungnote_notes").select("id,title,body,created_at,updated_at")
      .eq("user_id", uid).eq("id", noteId).single();
    if (error) throw error;
    const { data: todos } = await db
      .from("lungnote_todos").select("id,text,done,due_at,due_text,position")
      .eq("note_id", noteId).order("position");
    return { ...note, todos: todos ?? [] };
  },
  async ensureClaudeTag(uid) {
    const { data: tag } = await db
      .from("lungnote_tags").select("id").eq("user_id", uid).ilike("name", "claude").maybeSingle();
    if (tag) return tag.id;
    const { data: created, error } = await db
      .from("lungnote_tags").insert({ user_id: uid, name: "Claude", color: "#cdac65" })
      .select("id").single();
    if (error) throw error;
    return created.id;
  },
  // RULE enforcement point — every MCP write path MUST route note-marking
  // through here so any user's note added/extended by Claude carries the tag.
  async tagNoteClaude(uid, noteId) {
    const tagId = await this.ensureClaudeTag(uid);
    const { error } = await db
      .from("lungnote_notes_tags").upsert({ note_id: noteId, tag_id: tagId });
    if (error) throw error;
    return tagId;
  },
  async createNote(title, body = "") {
    const uid = await resolveUserId();
    const { data, error } = await db
      .from("lungnote_notes").insert({ user_id: uid, title, body })
      .select("id,title").single();
    if (error) throw error;
    await this.tagNoteClaude(uid, data.id);
    return data;
  },
  async appendNote(noteId, text) {
    const uid = await resolveUserId();
    const { data: note, error } = await db
      .from("lungnote_notes").select("id,body").eq("user_id", uid).eq("id", noteId).single();
    if (error) throw error;
    const body = note.body ? `${note.body}\n${text}` : text;
    const { error: e2 } = await db.from("lungnote_notes").update({ body }).eq("id", noteId);
    if (e2) throw e2;
    await this.tagNoteClaude(uid, noteId);
    return { id: noteId, appended: text.length };
  },
  async listRecent(limit = 10) {
    const uid = await resolveUserId();
    const { data, error } = await db
      .from("lungnote_notes").select("id,title,updated_at")
      .eq("user_id", uid).order("updated_at", { ascending: false }).limit(limit);
    if (error) throw error;
    return data;
  },
  async addTodo(text, { dueAt = null, dueText = null, noteId = null, noteTitle = "Inbox จาก Claude" } = {}) {
    const uid = await resolveUserId();
    let nid = noteId;
    if (!nid) {
      const { data: existing } = await db
        .from("lungnote_notes").select("id").eq("user_id", uid).eq("title", noteTitle)
        .limit(1).maybeSingle();
      nid = existing?.id ?? (await this.createNote(noteTitle)).id;
    }
    const { data: last } = await db
      .from("lungnote_todos").select("position").eq("note_id", nid)
      .order("position", { ascending: false }).limit(1).maybeSingle();
    const { data, error } = await db
      .from("lungnote_todos")
      .insert({
        user_id: uid, note_id: nid, text, due_at: dueAt, due_text: dueText,
        position: (last?.position ?? -1) + 1, source: "web",
      })
      .select("id,text,due_at").single();
    if (error) throw error;
    // todo ที่ Claude ใส่ → โน้ตแม่ต้องติด tag Claude เสมอ (RULE header)
    await this.tagNoteClaude(uid, nid);
    return data;
  },
  async listTodos(includeDone = false, limit = 50) {
    const uid = await resolveUserId();
    let q = db
      .from("lungnote_todos")
      .select("id,text,done,due_at,due_text,note_id,updated_at")
      .eq("user_id", uid)
      .order("due_at", { ascending: true, nullsFirst: false })
      .limit(limit);
    if (!includeDone) q = q.eq("done", false);
    const { data, error } = await q;
    if (error) throw error;
    return data;
  },
  async completeTodo(todoId) {
    const uid = await resolveUserId();
    const { data, error } = await db
      .from("lungnote_todos").update({ done: true })
      .eq("user_id", uid).eq("id", todoId).select("id,text,done").single();
    if (error) throw error;
    return data;
  },
};

const server = new McpServer({ name: "lungnote", version: "1.1.0" });

server.tool("search_notes", "ค้นหาโน้ตใน LungNote (title+body)", { query: z.string(), limit: z.number().optional() },
  async ({ query, limit }) => api.searchNotes(query, limit ?? 10).then(ok).catch(fail));
server.tool("read_note", "อ่านโน้ตเต็ม + todos ในโน้ต", { note_id: z.string().uuid() },
  async ({ note_id }) => api.readNote(note_id).then(ok).catch(fail));
server.tool("create_note", "สร้างโน้ตใหม่", { title: z.string().max(200), body: z.string().optional() },
  async ({ title, body }) => api.createNote(title, body ?? "").then(ok).catch(fail));
server.tool("append_note", "ต่อท้ายข้อความลงโน้ตเดิม", { note_id: z.string().uuid(), text: z.string() },
  async ({ note_id, text }) => api.appendNote(note_id, text).then(ok).catch(fail));
server.tool("list_recent", "ลิสต์โน้ตล่าสุด", { limit: z.number().optional() },
  async ({ limit }) => api.listRecent(limit ?? 10).then(ok).catch(fail));
server.tool("add_todo", "เพิ่มงาน (มี due_at ISO-8601 ได้) ลงโน้ต — ไม่ระบุโน้ตจะลง 'Inbox จาก Claude'",
  { text: z.string().max(2000), due_at: z.string().datetime({ offset: true }).optional(), due_text: z.string().optional(), note_id: z.string().uuid().optional(), note_title: z.string().optional() },
  async ({ text, due_at, due_text, note_id, note_title }) =>
    api.addTodo(text, { dueAt: due_at ?? null, dueText: due_text ?? null, noteId: note_id ?? null, ...(note_title ? { noteTitle: note_title } : {}) }).then(ok).catch(fail));
server.tool("list_todos", "ลิสต์งานค้าง (เรียงตาม due_at)", { include_done: z.boolean().optional(), limit: z.number().optional() },
  async ({ include_done, limit }) => api.listTodos(include_done ?? false, limit ?? 50).then(ok).catch(fail));
server.tool("complete_todo", "ติ๊กงานเสร็จ", { todo_id: z.string().uuid() },
  async ({ todo_id }) => api.completeTodo(todo_id).then(ok).catch(fail));

// Start only when executed directly (so seed/test scripts can import { api }).
import { pathToFileURL } from "node:url";
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  // CLI test mode: `node index.js --selftest` (no MCP client needed)
  if (process.argv.includes("--selftest")) {
    const uid = await resolveUserId();
    console.log("user:", uid);
    console.log("recent:", (await api.listRecent(3)).map((n) => n.title));
    process.exit(0);
  }
  await server.connect(new StdioServerTransport());
}
