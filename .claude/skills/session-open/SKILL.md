---
name: session-open
owner: CTO
origin: mooniex-org
scope: >-
  Charters a session — pins one Entry Problem plus Definition of Done, surfaces
  LungNote deadlines and open GitHub issues, sets both tab layers. Refuses a vague
  or multi-topic charter. Enforces IRON-RULES §35. Does not close or resume a
  session — see session-close and session-merge.
description: Charter a session under one bound problem before work starts. Trigger on /session-open and at the start of a session when the CEO states a goal — "เปิดงาน", "วันนี้ทำ", "ปัญหาคือ", "อยากแก้", "let's work on", "start".
created_by: human
audience: [cxo]
---

# Session Open — charter the session

One session binds to **one entry problem**, the way a `git worktree` binds to
one branch. This skill pins that problem before any work starts, so the session
has a clear thing to close. Enforces [IRON-RULES §35](../../../../LLMs/IRON-RULES.md).

## The shape (IRON §35)

```
┌─ OPEN ─ charter ──────────────────────┐
│ ① Entry Problem (1 ประโยค)            │
│    "session นี้แก้ ___ ให้จบ"          │
│ ② Definition of Done (วัดได้/เห็นได้)  │
│ ③ tab: ⏳ <problem>                    │
│  เขียน 1 ประโยคไม่ได้ = กว้างไป ซอยก่อน │
└───────────────┬───────────────────────┘
                ↓
┌─ WORK ─ focus-locked ─────────────────┐
│  loop:  ทำ → verify → ใกล้ DoD ยัง?    │
│  เรื่องใหม่เด้งเข้า:                    │
│   ├ เกี่ยว entry? → ทำต่อ              │
│   └ ไม่เกี่ยว? → PARK → lungnote todo  │
│                  ❌ ไม่สลับไปทำ          │
└───────────────┬───────────────────────┘
                ↓
┌─ EXIT GATE (/session-close) ──────────┐
│  entry แก้จบ + DoD ผ่าน + verify ext   │
│   → 🏁 ปิด  (ไม่จบ = ยังไม่ปิด)         │
└────────────────────────────────────────┘
```

## Steps to run

### 0. Pre-flight intake — surface pending work + deadlines (run FIRST)
Before asking what to work on, pull the candidate list so the CEO picks from
**real state, not memory**. This is the opening menu.

Belt-and-braces memory pull (task-8d37c0f1) — the launcher already pulled
before this process started; this just covers a `--resume`/`--continue` that
skipped the launcher: `python3 -m tools.memory_sync pull` (best-effort,
never blocks the charter).

1. **LungNote todos** — call `mcp__lungnote__list_todos` → the CEO's open
   action items (incl. anything parked by past `/session-close`).
2. **GitHub issue deadlines** — scan OPEN issues across every CEO repo and
   flag any with a deadline, soonest first:
   ```bash
   for r in mooniex-agents mooniex-webapp mooniex-claudeflow mooniex-claudesign lungnote-webapp warpclip-webapp; do
     gh issue list --repo PASAKON/$r --state open --json number,title,body,milestone --limit 50
   done
   ```
   A **deadline** = a native milestone `dueOn`, OR a date in the title/body —
   `YYYY-MM-DD`, "due", "deadline", "before", "cutover", "DUE", Thai
   "ภายใน/ก่อนวันที่/เดดไลน์". Compute days-from-today; mark overdue or ≤3 days 🔴.
3. **Present the menu** — one short table, nearest deadline on top (cap ~10,
   group the rest). **Label every row with a pick-code** so the CEO can choose
   by code (e.g. reply "ทำ A1+A2"):
   - **A1, A2, A3 …** = urgent — overdue or ≤3 days 🔴
   - **B1, B2, B3 …** = soon — has a date, >3 days out 🟡
   - **C1, C2 …** = no deadline / backlog ⚪ (group; surface only the few worth a look)

   Columns: **code** · item · source (todo / repo#NN) · deadline + days-left.

4. **Role-scope the TOP + the recommendation (IRON §33 — stay in your lane).**
   The full A/B/C list still shows **EVERYTHING** — it's the CEO's memory of all
   pending work, whoever owns it. But this session is run by ONE C-level (detect
   the role from `$CXO_ROLE` env, else default `cto`). So:
   - **Tag each row with its owning lane** — `[CTO]` `[CGO]` `[CMO]` `[CFO]` — by
     matching the item to a domain below.
   - **Float this session's own-lane items to the top** of each tier.
   - **The ⭐ recommendation MUST come from THIS role's domain only.** Never push
     another role's work; if the most-urgent item belongs to a different C-level,
     name it and tell the CEO to open THAT role's session for it.

   Role → domain (what each session may recommend):
   - **CTO** — coding, build, deploy, bugfix, infra, migration, .env/secrets,
     instrumentation, schema, DEV orchestration.
   - **CGO** — KPI, A/B test, funnel, conversion, attribution, growth metrics,
     retention, cohort.
   - **CMO** — content, creative, brand, posters/video, campaigns, copy, channel posts.
   - **CFO** — finance, billing, spend, invoices, subscriptions, budget, cost.
   - other C-levels → their named remit.

Then ask: **"session นี้เลือกทำอะไร?"** The CEO replies by code ("A1", "A1+A2") or
names something NOT on the list — the list is a prompt, not a constraint. The
pick becomes the Entry Problem in step 1.
> If the CEO bundles several codes, they still must collapse to **one** entry
> problem (step 1's single-sentence test). Related picks (e.g. two Contabo
> items) = one problem; unrelated picks = split, take one, park the rest.

> **Read-only intake.** Don't start any item here — just list them so the
> charter is informed. If LungNote/gh is unreachable, say so and proceed to
> step 1 from the CEO's own statement.

### 1. Capture the Entry Problem — one sentence
Ask the CEO (or restate from their request): **"session นี้แก้อะไรให้จบ?"**
Write it as a single sentence.

- **Refuse if it needs more than one sentence** or contains "และ / กับ / รวมถึง"
  joining unrelated jobs. That is two+ problems → tell the CEO it is too broad,
  propose a split, and ask which sub-problem this session takes. The other(s) get
  parked to LungNote, not worked.
- A good entry problem names a *change of state*, not an activity:
  - ✅ "TM poster t009–t011 ผ่าน reject criteria แล้ว merge ปิด 3 ตัว"
  - ❌ "ดูเรื่อง poster กับ funnel แล้วก็เคลียร์ของค้าง" (activity, multi-topic)

### 1b. Write the charter to the DB (mandatory)
`/session-open` itself never touches the DB, which is why it used to be
skippable (2026-09-17: a CTO session skipped it and fanned into 5 unrelated
threads). This command is the actual enforcement — skipping it does not fail
quietly: the **next** `create_task` call this session makes (any task spawn)
raises a `RuntimeError` and refuses to create the task.
```bash
python3 -m tools.session_charter set "<Entry Problem, one sentence, from step 1>"
```
Escape hatch for setup/repair sessions only, never for normal work:
`ORG_CHARTER_GATE=off`.

### 2. Define Done — observable, tied to the entry problem
List 1–4 DoD items, each one **checkable**: a prod query result, a green test,
a merged sha, a deployed URL, an explicit CEO "approve". Ban "discussed" /
"looks done" / "should be fine".

### 3. Set BOTH tab layers (§32)
The tab has two independent surfaces. Set both here — this is the one moment
the charter is fresh, and the Main Tab stays a bare "🎯 CTO #<sid>" all session
if this step is skipped.
```bash
# Sub tab (the coloured strip): what is happening right now
bash scripts/tab-title.sh "⏳ <entry problem ≤35 chars>"
# Main tab (the window titlebar): where the session is going, 0 of N DoD done
bash scripts/tab-main.sh "<entry problem, fuller wording is fine>" 0/<DoD count>
# Claude session name (mobile app / Remote Control list): machine+role+id+topic
bash scripts/session-rename.sh "<entry problem, short>"
```
The clock runs itself from here (shared 60s daemon). The goal and the progress
numbers do not — they move only when `tab-main.sh` is called again, which
`/session-worktree` and `/session-close` do.

`session-rename.sh` types `/rename <MACHINE> <ROLE> #<id> (<topic>)` into this
session's own tmux pane — the command queues and executes right after the
current turn ends, and the new name syncs to claude.ai + the mobile app
(CEO 2026-08-30). Run it as the LAST tool call of the charter turn so nothing
else interleaves; skip silently if not under tmux (script handles it).

### 4. (optional) Bind a git worktree for code sessions
If the session's work is code on one repo, make the metaphor literal — branch +
worktree per IRON §1.5, so the filesystem isolates the focus too:
```bash
cd /Users/gob/Projects/<repo>
git worktree add ../<repo>-wt-<slug> -b session/<date>-<slug> origin/<base>
```

## Output format

```
📌 SESSION CHARTER
Entry Problem : <one sentence>
Definition of Done:
  [ ] <observable item 1>
  [ ] <observable item 2>
Tab           : ⏳ <summary>
Parked (not this session): <anything split off> → LungNote
```

Then start WORK. From here, anything off-topic is **parked, not pivoted to**
(see /session-close for the exit gate).

## Operating rules

- **One sentence or split.** The single-sentence test is the whole point — if it
  fails, the session is already two jobs.
- **DoD must be verifiable by someone else.** If only you can tell it's done, it
  isn't a DoD.
- **Don't pre-load future waves.** Charter THIS problem only; downstream work is
  a separate session (and, for tasks with overlapping `touches`, IRON §-serial).

## Field notes

- 2026-09-22 [MISSING] §0 Pre-flight — when the CEO opens the session with the problem already stated, the A/B/C menu adds nothing: the SessionStart hook has already surfaced the deadlines, and `list_todos` returned 80 rows (60 KB) that were never read; charter from the CEO's sentence and skip to step 1 · evidence: session cto-0e8d80b8 · status: pending
