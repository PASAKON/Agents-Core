---
name: session-worktree
owner: CTO
origin: mooniex-org
scope: >-
  Prints the current session as an emoji work-breakdown tree, each node tagged by
  work type (READ / BUILD / FIX / DESIGN / TEST / SHIP), then a plain-language
  summary for the CEO, then sends the same tree as a picture — rendered by
  tools/session_diagram.py in the diagram-design system and pushed to the CEO's
  Telegram as a PNG. Chat stays text and emoji — CTO chat renders no inline
  images; the picture travels out-of-band. Absorbed the former /session-summary.
  Enforces the §35 one-problem view.
description: Show what this session has done, is doing, is blocked on, and has left — as a text tree, a plain recap, and a diagram sent to the CEO's Telegram. Trigger on /session-worktree and when the CEO asks "ทำถึงไหนแล้ว", "เหลืออะไร", "ติด blocker ตรงไหน", "สรุป session", "อธิบายแบบบ้านๆ", "progress", "where are we", "recap", "ขอ diagram session", "ส่งรูป worktree".
created_by: human
audience: [cxo]
---

# Session Worktree — what's done / doing / blocked / left (+ plain recap)

On `/session-worktree` (or "ทำถึงไหนแล้ว", "session status", "progress", "เหลืออะไร",
"ติด blocker ตรงไหน", and the merged-in "สรุป session", "recap", "summarize", "วันนี้ทำอะไรไปบ้าง"),
reconstruct the CURRENT session from the conversation so far and print TWO stacked views as
**text + emoji** (Thai-safe; never an image inline — the CTO chat is a terminal REPL, see
[[cto-chat-text-output]]), then send the SAME tree as a picture (view 3):

1. 🌳 **the worktree tree** — technical, every node tagged by work type, with sha/file/approve evidence.
2. 📋 **the plain recap** — zero-jargon business summary for the CEO (the former `/session-summary`).
3. 🖼 **the picture** — the tree rendered by `tools/session_diagram.py` in the `diagram-design`
   system and sent to the CEO's Telegram as a PNG; its path + send status is the **last line**.

Same facts, three readers: the tree is for the CTO (detail), the recap is for a CEO with zero coding
knowledge (the "so what"), the picture is the whole session at a glance on the CEO's phone
(CEO 2026-09-08: "เราจะได้เห็นภาพรวมของทั้ง session เป็น diagram เลย"). Always print tree first,
recap second, picture line last.

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

## Format — view 3: the picture (last line)

One source for text and picture: write the tree as JSON, let the script draw it. The model
owns the facts, the script owns the geometry — a hand-drawn diagram costs ~15 minutes of SVG
per picture, the script costs 5 seconds and cannot disagree with view 1.

1. **Feed the tree as JSON on stdin** — one Bash call, no file to write by hand. Schema by
   example: `.venv/bin/python tools/session_diagram.py --sample`. Same nodes, ids, statuses
   (`done|doing|todo|blocked`), type tags, evidence and `blocked_on` as view 1;
   `entry_problem` = the charter's sentence; `dod` = the charter's items with their current
   `done`. Omit `session` — the script reads the session id from the env. The script keeps a
   copy as `state/session-diagrams/<session>-<yyyymmdd-HHMM>.json` (the dir is gitignored).
2. **Render + send** — do this BEFORE typing view 1, and paste the script's tree as view 1:
   ```bash
   .venv/bin/python tools/session_diagram.py - --print-tree --check --png --send <<'EOF'
   {"entry_problem": "…", "dod": [{"text": "…", "done": true}],
    "nodes": [{"status": "done", "type": "BUILD", "title": "…", "evidence": "sha:…"}]}
   EOF
   ```
   `--print-tree` prints view 1 in this skill's exact format · `--check` runs diagram-design's
   own `self_check.py` · `--png` renders with headless Chrome · `--send` pushes the PNG to the
   CEO's Telegram as a real file (CEO order #38, never a link).
3. **Read the script's `telegram:` line and report exactly that**, as the last line of the
   whole output:
   ```
   🖼 state/session-diagrams/<file>.png · ส่งเข้า Telegram แล้ว ✓                 ← telegram: ok
   🖼 state/session-diagrams/<file>.png · Telegram ส่งไม่ผ่าน: <reason>            ← telegram: FAILED
   🖼 state/session-diagrams/<file>.html · เครื่องนี้ไม่มี Chrome ส่งเป็นไฟล์ HTML แทน  ← png: skipped
   ```
   `ok` is the only thing that counts as sent ([[report_outcome_not_intent]]). No Chrome on
   the box (Contabo today) → the script skips the PNG and sends the HTML as a document; say so.

## After printing: push the count to the Main Tab

The tree already counted `✅ done / total`. Send that same pair to the window
titlebar so the CEO reads progress off the tab bar without opening anything:

```bash
bash scripts/tab-main.sh "" <done>/<total>   # "" keeps the goal set at /session-open
bash scripts/session-rename.sh "<entry problem, short>"
```

Use the numbers already in the `📊` line — never invent a percentage. This is
the routine moment the bar moves; skipping it leaves the titlebar showing a
stale count until close.

`session-rename.sh` is normally **silent** here — it prints nothing worth
reading (`unchanged: <topic>`) on the vast majority of calls, because it only
sends `/rename` when the entry problem's short form has actually drifted from
what the session is already named. That's the same category of exception as
the `tab-main.sh` call right above it: `/session-worktree` documents itself
as read-only, and pushing an unchanged display name is exactly as much "new
work" as pushing an unchanged progress count — a display-layer sync, not a
task. Skip it only if the session never charter'd a topic at all.

## Rules

- **Print both text views, every time, then the picture line.** Tree first (technical), plain
  recap second (business), the `🖼` line last.
- **Chat stays text + emoji.** Never paste an image into the chat — the terminal shows nothing
  inline. The picture goes to Telegram (view 3); the chat shows its path and the send verdict.
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
- **Read-only.** This prints a recap; it changes nothing in the work — the JSON/PNG under
  `state/session-diagrams/` and the Telegram message are display-layer, like the tab title.
  Want it saved for next time? That's
  [[session-save]]. Want the exit gate? [[session-close]]. Pairs with [[session-open]] (sets
  the main + first nodes). `session_tree.py` is the *other* tree — DB tasks across all projects,
  not this single conversation.
```
