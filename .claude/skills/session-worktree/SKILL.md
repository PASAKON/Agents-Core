---
name: session-worktree
owner: CTO
origin: mooniex-org
scope: >-
  Prints the current session as an emoji work-breakdown tree, each node tagged by
  work type (READ / BUILD / FIX / DESIGN / TEST / SHIP), then a plain-language
  summary for the CEO. Text and emoji only — CTO chat renders no inline images.
  Absorbed the former /session-summary. Enforces the §35 one-problem view.
description: Show what this session has done, is doing, is blocked on, and has left. Trigger on /session-worktree and when the CEO asks "ทำถึงไหนแล้ว", "เหลืออะไร", "ติด blocker ตรงไหน", "สรุป session", "อธิบายแบบบ้านๆ", "progress", "where are we", "recap".
created_by: human
audience: [cxo]
---

# Session Worktree — what's done / doing / blocked / left (+ plain recap)

On `/session-worktree` (or "ทำถึงไหนแล้ว", "session status", "progress", "เหลืออะไร",
"ติด blocker ตรงไหน", and the merged-in "สรุป session", "recap", "summarize", "วันนี้ทำอะไรไปบ้าง"),
reconstruct the CURRENT session from the conversation so far and print TWO stacked views as
**text + emoji** (Thai-safe; never an image — the CTO chat is a terminal REPL, see [[cto-chat-text-output]]):

1. 🌳 **the worktree tree** — technical, every node tagged by work type, with sha/file/approve evidence.
2. 📋 **the plain recap** — zero-jargon business summary for the CEO (the former `/session-summary`).

Same facts, two readers: the tree is for the CTO (detail), the recap is for a CEO with zero coding
knowledge (the "so what"). Always print **both**, tree first, recap last.

This is a **read of progress**, not new work. Don't start a task here — just mirror state.

## Colour vs emoji

- **Emoji: yes.** iTerm2 renders emoji — use them as the status + type markers (below).
- **ANSI colour: no** (in this skill). The output is text Claude types into the chat, which
  is markdown, not a TTY stream — raw `\033[..m` codes would print literally. Emoji carry the
  visual weight instead. (True ANSI colour only exists in `session_tree.py`, which is a real
  script printing to the terminal.)

## Build the tree

1. **main** = the session's Entry Problem (from the `/session-open` charter; if none was
   set, infer the single problem this session is solving — IRON §35: one session, one problem).
2. **nodes** = the concrete work items tackled, in order, numbered `#1, #2 … #N` (sub-steps
   `#4.1 … #4.5`). Nest as deep as the work actually branched.
3. Each node carries TWO orthogonal markers:
   - **status emoji** (scanned first): ✅ done · 🔄 in-progress · ⬜ not started · 🔴 blocked
   - **work-type tag** (glyph + WORD): what KIND of work it was — see the taxonomy below.
     A node's type and status are independent (a BUILD can be done, doing, or blocked).
4. Put `⬅️ อยู่ตรงนี้` on the node currently in progress.
5. **Blocked node (🔴):** append `· BLOCKED: รอ <what>` inline, and list every blocker in a
   `🔴 BLOCKERS` summary under the tree. Name the wait precisely — a CEO decision, an env/secret
   (e.g. FAL_KEY), a dependency task, prod creds, or an external party. Per the org rule, every
   real blocker also gets a GitHub issue — note the issue # if one exists.
6. Last node = 🏁 CLOSE — reachable only when every node above is ✅ (a 🔴 blocks the close).

## Work-type taxonomy (the node tag)

Pick the one tag that best fits each node. Core five used most: READ · BUILD · FIX · TEST · SHIP.

| glyph | TYPE | when |
|:--:|---|---|
| 🔍 | READ / RECON | reading code, surveying existing state, reconnaissance |
| 📚 | RESEARCH | external lookup (web, docs, a spec, an API) |
| 🧠 | ANALYZE / DECIDE | analysis, answering a CEO question, go/no-go, planning |
| 🔨 | BUILD | new thing created (code / feature / script) |
| 🔧 | FIX | bug fix, repair, recover something broken |
| 🎨 | DESIGN | UI / visual / redesign |
| ⚙️ | SETUP | env, creds, infra, deploy plumbing |
| 🧪 | TEST / VERIFY | testing, proving, live verification |
| 🚀 | SHIP | push to prod / merge / deploy |
| 📝 | DOC | documentation, wiki, memory |
| 🏁 | CLOSE | the session-close node |

Use only the types that actually occur. Don't force a tag — if a node is genuinely mixed,
tag it by its dominant outcome.

## Format — view 1: the tree (print straight to chat)

```
🌳 SESSION WORKTREE — <date>
🎯 main: <entry problem · one line>
│
├─ ✅ #1  🔧 FIX     — <what> ............. <evidence: sha / file / CEO approve>
├─ 🔄 #2  🔨 BUILD   — <what>                ⬅️ อยู่ตรงนี้
│  ├─ ✅ #2.1 🔍 READ   — <sub>
│  └─ ⬜ #2.2 🧪 TEST   — <sub>
├─ 🔴 #3  🚀 SHIP    — <what> · BLOCKED: รอ <CEO อนุมัติ / FAL_KEY / dep task-XYZ>
└─ ⬜ #N  🏁 CLOSE   — <what's left before close>
   └─ 🏁 Done · Close Session

📊 ✅ <done>/<total>   🔄 <doing>   ⬜ <todo>   🔴 <blocked>
📈 ตามชนิดงาน: 🔨 BUILD ×<n> · 🔧 FIX ×<n> · 🧠 ANALYZE ×<n> · <… types present>

🔴 BLOCKERS (<n>)
  • #3 — รอ <what> · <GH issue #NN ถ้ามี>
```

If there are no blockers, drop the `🔴 BLOCKERS` block entirely (don't print an empty one).
The `📈 ตามชนิดงาน` line tallies the type tags so the CEO sees what the session mostly was
(building? firefighting? researching?). Drop it if there are only one or two nodes.

## Format — view 2: the plain recap (append after the tree)

Print a separator, then recap the WHOLE session so a CEO with **zero coding knowledge** gets
it in ~30 seconds. This is the merged-in `/session-summary` — same honesty bar, business-first.

### The one rule: translate everything

If the CEO would have to Google a word, **it's banned** — replace it with the business outcome.
Lead with what changed for the company; the technical thing goes in parentheses at most, or drops.

| ❌ jargon (don't say) | ✅ say instead |
|---|---|
| merged PR / pushed to main | ขึ้นระบบจริงแล้ว / รวมเข้างานหลักแล้ว |
| deployed | ปล่อยใช้งานจริงบนเว็บแล้ว |
| branch / worktree / sha / commit | *(ข้ามไปเลย — CEO ไม่ต้องรู้)* |
| bug / exception / stack trace | จุดที่พัง / ระบบคำนวณผิด |
| schema / migration / database | โครงสร้างข้อมูล |
| API / endpoint | ช่องเชื่อมต่อระบบ |
| env / API key / secret / token | กุญแจเชื่อมต่อระบบ |
| refactor | จัดระเบียบของเดิมให้เร็ว/สะอาดขึ้น (ผลเหมือนเดิม) |
| deploy blocked / merge conflict | ยังขึ้นจริงไม่ได้ เพราะ… |

Rule of thumb: **"ลูกค้า/ธุรกิจได้อะไร"** มาก่อนเสมอ.

```
────────────────────────────────────────────────────────
📋 สรุปแบบบ้านๆ — <date>   (อ่าน ~30 วิ)

🎯 เรื่องหลัก: <ประโยคเดียว ภาษาคน>

✅ เสร็จแล้ว
  • <ผลลัพธ์ที่ธุรกิจได้ ภาษาบ้านๆ>
  • <…>

🔄 กำลังทำ / รอผล
  • <อะไร · รออะไรอยู่>

🔴 ต้องให้ CEO ตัดสินใจ
  • <ปัญหาแบบเข้าใจง่าย> → ขอ: <อนุมัติ / กุญแจ / เงิน $X / คำตอบ>

💡 แปลว่า: <ผลต่อธุรกิจ 1 บรรทัด — ขายได้ขึ้น? ลูกค้าลื่นขึ้น? กันพังไว้?>
💰 ค่าใช้จ่าย: ~<N> งานเอเจนต์ / $<X>   (ใส่เมื่อรู้ตัวเลขจริงเท่านั้น)
```

Keep the recap to roughly one screen. If a section is empty, **drop it** (don't print "ไม่มี").
A small **table** is fine instead of bullets when clearer (e.g. before/after, or a few items
each with a status emoji).

## After printing: push the count to the Main Tab

The tree already counted `✅ done / total`. Send that same pair to the window
titlebar so the CEO reads progress off the tab bar without opening anything:

```bash
bash scripts/tab-main.sh "" <done>/<total>   # "" keeps the goal set at /session-open
```

Use the numbers already in the `📊` line — never invent a percentage. This is
the routine moment the bar moves; skipping it leaves the titlebar showing a
stale count until close.

## Rules

- **Print both views, every time.** Tree first (technical), plain recap last (business).
- **Text + emoji only.** Never render an image — the terminal shows nothing inline.
- **Two markers per node:** status emoji (state) + type tag (kind). Don't collapse them.
- **Evidence on ✅ items** (sha, file, "CEO approve") — same honesty bar as `/session-close`;
  no node marked done by narration. A side-effect (post sent, money spent, email out) counts
  as done only if verified in the real world ([[orphan_recovery_verify_external_state]]).
- **Blockers are loud.** A 🔴 node must say what it's waiting on, surface in the summary, and
  (for real external blockers) carry a GitHub issue. A session with an open 🔴 cannot 🏁.
- **Recap = zero jargon.** Every line passes the "CEO ไม่ต้อง Google" test. Outcome first,
  mechanism never. Code register stays normal inside code/commits — nothing technical leaks here.
- **🔴 in the recap = an ask, stated plainly.** Name exactly what you need: a yes/no, a budget
  ($ amount — never spend before the OK, [[ask_before_paid_api]]), a key, or an answer.
- **One main per tree.** If the session drifted into a second problem, show the entry problem's
  tree and note the drift as a parked item (it belongs in a new session).
- **Don't over-nest trivia.** Group tiny steps; nest only where the work genuinely branched.
- **Read-only.** This prints a recap; it changes nothing. Want it saved for next time? That's
  [[session-save]]. Want the exit gate? [[session-close]]. Pairs with [[session-open]] (sets
  the main + first nodes). `session_tree.py` is the *other* tree — DB tasks across all projects,
  not this single conversation.
```
