---
name: session-worktree
owner: CTO
origin: mooniex-org
scope: >-
  Answers "ทำถึงไหนแล้ว" with a session MAP: one JSON per session that the C-level
  patches with only what changed, tools/session_diagram.py draws it in the
  diagram-design system (START → goal blocks with task checklists → dependent
  goals, separate lines, detours, ◀ HERE, minutes per block), and the Artifact
  tool republishes one link per session. Chat gets a short status block, a plain
  recap and the link — never the picture, never the full tree unless asked.
  Absorbed the former /session-summary. Enforces the §35 one-problem view.
description: Show what this session has done, is doing, is blocked on, and has left — a session map (Artifact link) plus a short status block and a plain recap. Trigger on /session-worktree and when the CEO asks "ทำถึงไหนแล้ว", "เหลืออะไร", "ติด blocker ตรงไหน", "สรุป session", "อธิบายแบบบ้านๆ", "progress", "where are we", "recap", "ขอแผนที่ session", "ขอ diagram session". Do NOT fire at /session-open or on your own — the map exists only once the CEO asks for a worktree.
created_by: human
audience: [cxo]
---

# Session Worktree — the session map (+ short status + plain recap)

On `/session-worktree` (or "ทำถึงไหนแล้ว", "session status", "progress", "เหลืออะไร", "ติด blocker
ตรงไหน", "สรุป session", "recap", "วันนี้ทำอะไรไปบ้าง"), reconstruct the CURRENT session and answer
in three parts, in this order:

1. 📊 **status block** — printed by the script (counts · 📍 where we are · 🔴 blockers). Paste as-is.
2. 📋 **plain recap** — 5–8 lines, zero jargon, for a CEO with no coding knowledge.
3. 🖼 **the map** — the Artifact link, the **last line**. Every detail lives there.

Chat stays text + emoji (the CTO chat is a terminal REPL — [[cto-chat-text-output]]). The full
🌳 tree is no longer printed: the CEO chose "short + link" (2026-09-09) because a tree retyped
on every run was this skill's single biggest token cost. `show --tree` exists for the moment the
CEO explicitly asks for the text tree.

This is a **read of progress**, not new work. Don't start a task here — just mirror state.

## What the map is (CEO 2026-09-09)

A left→right picture of the session: **START** (what the CEO asked) → **goal blocks** → **FINISH**
(the charter's Definition of Done under a flag; every line runs into it, green when complete). A
goal that needs an earlier goal follows it with an arrow; a goal on its own line sits on its own
row; each block lists its tasks 1-2-3 with a status icon, the block's `start→finish · minutes`,
and the task being worked on is amber with a map-pin `HERE`. Work that left the path hangs under
its block as a **DETOUR** (came back, ↩) or **PARKED** (dead end ⊥, LungNote). **Workers** this
session delegated hang under the goal they serve (read live from `state/tasks.db`). Colours are
status — done green · doing amber · blocked red — icons are Tabler, never emoji; the standard is
`org:playbooks/session-map.md` (colours, icons, vocabulary) and is the same for every C-level.
One map, one link per session; on a phone it scrolls sideways — horizontal only (CEO 2026-09-09).

Vocabulary, so every session's map reads the same:

- **Goal** = one thing the CEO asked for in this session (เรื่องที่ CEO สั่ง). The charter's Entry
  Problem is usually `G1`; a second ask mid-session is a new goal. `depends_on` when a goal needs
  another finished first; no `depends_on` = a separate line.
- **Task** = a step inside a goal — the worktree nodes, numbered by the script. `type` is one of
  READ · RESEARCH · ANALYZE · BUILD · FIX · DESIGN · SETUP · TEST · SHIP · DOC; `evidence` (sha,
  file, "CEO approve") on done ones — no node is done by narration; `blocked_on` on blocked ones.
  The charter's DoD items become tasks of their goal.
- **Detour** = work that left the path. `interrupt` = had to be done, then back on the line (an
  incident, a fix, a CEO question); `parked` = raised, not done here, sent to LungNote (`note` =
  the todo id, IRON §35). Both hang under the goal they interrupted.
- **here** = `G2.3` (a task) or `G2` (a goal). Omit it and the script points at the first `doing`.
- **DoD** = the charter's Definition of Done items, `F.1 … F.n`, shown in the FINISH block; tick
  them with `set: {"F.2": "done"}` as they are verified — same honesty bar as `/session-close`.
- **Worker** = a task this session delegated (`tasks.owner_cto` = this session). The script reads
  every one of them at every render — role, task id, tmux name, worker session, host, status,
  runtime — you only say which goal it serves, once: `"workers": {"G2": ["task-149e6c86"]}`.
  Unassigned workers show in a band under the rows; finished ones stay (green / grey).
- **Times** are stamped by the script when a status changes (doing/blocked start the clock, done
  stops it) — never type times; the map derives each block's minutes from its tasks.

## Steps

### First /session-worktree of the session → `map`

```bash
.venv/bin/python tools/session_diagram.py map <<'EOF'
{"entry_problem": "<the charter sentence>",
 "start": "<what the CEO asked, in their words, ≤ 2 lines>",
 "dod": [{"text": "<charter DoD item>", "done": false}],
 "workers": {"G1": ["task-<id the session delegated>"]},
 "goals": [
   {"id": "G1", "title": "…", "type": "BUILD", "tasks": [
      {"title": "…", "status": "done", "type": "SETUP", "evidence": "sha:…"},
      {"title": "…", "status": "doing"},
      {"title": "…", "status": "todo", "type": "TEST"}],
    "detours": [{"title": "…", "kind": "interrupt", "status": "done"}]},
   {"id": "G2", "title": "…", "depends_on": ["G1"], "tasks": [{"title": "…"}]},
   {"id": "G3", "title": "a separate line", "tasks": [{"title": "…", "status": "blocked", "blocked_on": "รอ CEO …"}]}
 ],
 "here": "G1.2"}
EOF
```

Schema by example: `.venv/bin/python tools/session_diagram.py sample`. The session id comes
from the launcher env (`<role>-<id>`); files land in `state/session-diagrams/<session>.{json,html,artifact.html}`
(gitignored). `map` on an existing session replaces the map — only do that when the CEO asks
to start the map over.

### Every later /session-worktree → `patch` (only what changed)

```bash
.venv/bin/python tools/session_diagram.py patch <<'EOF'
{"set": {"G1.2": "done", "G1.3": "doing", "F.1": "done"}, "evidence": {"G1.2": "sha:abc1234"}, "here": "G1.3",
 "workers": {"G2": ["task-149e6c86"]},
 "add": {"tasks": {"G2": [{"title": "a new step"}]},
         "goals": [{"id": "G4", "title": "a new ask from the CEO", "tasks": [{"title": "…"}]}],
         "detours": {"G1": [{"title": "…", "kind": "parked", "note": "LungNote <todo id>"}]}},
 "blocked": {"G2.1": "รอ FAL_KEY"}}
EOF
```

Refs: `G2` goal · `G2.3` task · `D1` detour · `F.2` DoD item. `set` takes any status; `blocked`
sets the status and the reason in one go; `add` appends (tasks get the next number, detours the
next `D` id, `dod` the next `F`); `workers` ties delegated tasks to a goal. A typical patch is
1–3 lines; never resend the whole map. `sample-patch` prints an example.

### Then, every run

1. **Paste the script's status block** (the `📊` / `📍` / `🔴` lines) — that is part 1.
2. **Write the plain recap** (below) — part 2.
3. **Publish:** `Artifact(file_path="state/session-diagrams/<session>.artifact.html",
   description="Session map · <date> · <session>", favicon="🗺️")` on the session's first run; later
   runs call it with the same path and no favicon, which republishes the same URL.
4. **Last line = the link:** `🖼 https://claude.ai/code/artifact/<id>`. No Artifact tool in this
   runtime (the inline `cto_chat` REPL) → the last line is the file path and why:
   `🖼 state/session-diagrams/<session>.html · runtime นี้ไม่มี Artifact tool`.
5. **Titlebar:** `bash scripts/tab-main.sh "" <goals done>/<goals>` (numbers from the 📊 line) and
   `bash scripts/session-rename.sh "<entry problem, short>"` (silent when unchanged).

The script's `check:` line is diagram-design's own `self_check.py` — `check: FAIL` means fix
before publishing. Telegram (`--png --send`) is opt-in only, when the CEO asks for the picture in
SomPong; then the script's `telegram: ok` is the only "sent" ([[report_outcome_not_intent]]).

## Part 2 — the plain recap

Recap the WHOLE session so a CEO with **zero coding knowledge** gets it in ~30 seconds. This is
the merged-in `/session-summary` — same honesty bar, business-first.

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
📊 goals 2/4 · tasks 9/14 · 🔴 1 · ↪ 1 detour · ⏱ 1h 25m        ← the script's lines, as-is
📍 G2.3 — <task title>
🔴 G4.1 — รอ <what>
────────────────────────────────────────────────────────
📋 สรุปแบบบ้านๆ — <date>   (อ่าน ~30 วิ)
🎯 เรื่องหลัก: <ประโยคเดียว ภาษาคน>
✅ เสร็จแล้ว: <ผลลัพธ์ที่ธุรกิจได้> · <…>
🔄 กำลังทำ: <อะไร · รออะไรอยู่>
🔴 ต้องให้ CEO ตัดสินใจ: <ปัญหาแบบเข้าใจง่าย> → ขอ: <อนุมัติ / กุญแจ / เงิน $X / คำตอบ>
💡 แปลว่า: <ผลต่อธุรกิจ 1 บรรทัด>
💰 ค่าใช้จ่าย: ~<N> งานเอเจนต์ / $<X>   (ใส่เมื่อรู้ตัวเลขจริงเท่านั้น)
🖼 https://claude.ai/code/artifact/<id>
```

If a section is empty, **drop it** (don't print "ไม่มี"). Keep the recap to 5–8 lines.

## Work-type taxonomy (task `type`)

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

Use only the types that actually occur; tag a mixed step by its dominant outcome.

## The text tree — only when asked

`.venv/bin/python tools/session_diagram.py show --tree` prints the classic 🌳 tree (goals as
nodes, tasks and detours as children, ⬅️ อยู่ตรงนี้, ⏱ per line, 🔴 BLOCKERS) from the same map.
Print it only when the CEO asks for the text tree — it costs the tokens the map was built to save.

## Rules

1. **HARD — Never create the map on your own.** It exists only after the CEO asks for a
   worktree; `/session-open` does not create it and a mid-session status question that the CEO
   did not phrase as a worktree does not either.

   **Why hard:** scope of authorisation — the CEO set this boundary on 2026-09-09 ("ถ้าไม่สั่ง
   สร้างก็ห้ามทำ"), and every unrequested map spends tokens the design exists to save.

2. **Short + link, every time.** Status block → recap → link. The map carries the detail; the
   chat carries the "so what". One horizontal layout on every device (a phone scrolls sideways) —
   the CEO's choice, not a gap.
3. **Patch, don't resend.** After the first run, the map file is the source of truth; send only
   the deltas. Resending the whole map costs the tokens the design exists to save and can
   silently drop times the script stamped.
4. **Evidence on ✅ items** (sha, file, "CEO approve") — same honesty bar as `/session-close`. A
   side-effect (post sent, money spent, email out) counts as done only if verified in the real
   world ([[orphan_recovery_verify_external_state]]).
5. **Blockers are loud.** A blocked task carries `blocked_on`; the status block lists every 🔴;
   a real external blocker also carries a GitHub issue. A session with an open 🔴 cannot 🏁.
6. **Recap = zero jargon.** Every line passes the "CEO ไม่ต้อง Google" test. Outcome first,
   mechanism never. Code register stays normal inside code/commits.
7. **🔴 in the recap = an ask, stated plainly.** Name exactly what you need: a yes/no, a budget
   ($ amount — never spend before the OK, [[ask_before_paid_api]]), a key, or an answer.
8. **One entry problem per map.** A second ask from the CEO is a new goal on the same map (its
   own line, or `depends_on` if it needs the first); a topic that does not belong to this session
   is a `parked` detour → LungNote, not a new map.
9. **Read-only.** This mirrors state; the files under `state/session-diagrams/` and the Artifact
   publish are display-layer, like the tab title. Saved for next time? That's [[session-save]].
   The exit gate? [[session-close]]. Pairs with [[session-open]] (which sets the entry problem).
10. **The look is the org standard, not yours.** Colours, icons, chips and vocabulary come from
    `org:playbooks/session-map.md` via the script; every C-level's map reads the same. Want a
    change? Change the playbook and the script, not one session's output.
```
