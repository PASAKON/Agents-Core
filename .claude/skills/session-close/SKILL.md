---
name: session-close
owner: CTO
origin: mooniex-org
scope: >-
  Exit gate only. Verifies the Entry Problem is solved and every Definition-of-Done
  item checked before allowing the 🏁 glyph, and parks leftovers to LungNote.
  Refuses to close otherwise. Enforces IRON-RULES §35. Companion to session-open.
description: Verify a session's Entry Problem is actually solved before closing it 🏁. Trigger on /session-close and when the CEO says "ปิด session", "จบงาน", "พอแค่นี้", "close out", "done for now".
---

# Session Close — exit gate tied to the entry problem

A session closes only when its **one entry problem** is solved. "We talked a lot"
is not closed. This skill runs the exit gate from [IRON-RULES §35](../../../../LLMs/IRON-RULES.md)
and refuses 🏁 if the entry Definition of Done isn't verifiably met.

## Gates — refuse 🏁 if any fails

### 1. Recall the charter
- [ ] State the session's **Entry Problem** (one sentence) and its **DoD list**
      as pinned at open. If no charter was set, reconstruct it now from the
      session's actual work, then judge against it.

### 2. Every DoD item passes — with evidence
- [ ] Walk each DoD item; mark `[x]` only with concrete proof (sha, test count,
      query result, CEO "approve"). Quote the evidence inline.
- [ ] No item marked done by narration ("should be working") — that's a FAIL.

### 3. External-state verified (side-effect work)
Applies if the entry problem touched anything outside the repo — DB write, social
post, deploy, email, payment, upload.
- [ ] Query the external system for evidence the effect actually landed. **A commit
      proves authorship, never execution.** Paste the result.
- [ ] If it can't be queried (no creds/access) → the session does **not** 🏁-close;
      report it as HOLD pending verification.

### 4. Capture every CEO action-item + park open work → LungNote (สำคัญมาก)
Two things land in LungNote here. Anything that lives only in the chat is lost
the moment the tab closes — so save it now, with dates.

**4a. CEO action-items + reminders — capture every one, with dates.**
Walk the WHOLE session for anything **the CEO personally must do** — not just
code: reply to an email, send a doc, decide A/B, pay an invoice, migrate X→Y,
follow up with a person, renew a key. For EACH:
- `mcp__lungnote__add_todo` with a clear one-line `text`.
- **If it has a date/deadline → set `due_at` (ISO-8601, e.g. `2026-06-18T00:00:00Z`)**
  so LungNote shows the countdown ("ขึ้นแจ้งเตือนกี่วัน / ลงวันไหน"). Convert
  relative dates ("ก่อนศุกร์", "ภายใน 3 วัน", "พรุ่งนี้") to an absolute ISO date
  FIRST (today is known from context). If genuinely no date, save without
  `due_at` but say so in the report.
- These are **reminders, not necessarily ClaudeCode work** — "รอตอบ email จาก
  ___", "ส่ง KYC ก่อน ___", "migrate A→B ก่อน 2026-06-18" all count, even though
  the CEO (not an agent) does them.

**4b. Park unfinished / off-topic work — backlog.**
Anything raised but **not** part of the entry problem → `add_todo` one line each
(with `due_at` if dated), so it's a real backlog item, not a loose thread.

- [ ] If the entry problem itself is **unfinished**: do NOT 🏁. Set the tab to
      `✅` (work pending) or `🔴` (blocked), and say plainly it's abandoned/partial
      — per §35, an unsolved entry problem is not a close.

**4c. Apply directly — verify first, then just do it (no approval round-trip).**
The todos are the CEO's backlog, but this skill auto-applies once evidence clears
the same bar as gate 2 — no "propose and wait for approve" step (retired
2026-08-04; the LungNote backend's status field ships complete/cancel/delete
natively now, so there's nothing left to gate).
- **Before `complete_todo` / `cancel_todo` / `delete_todo`**: FIRST verify with
  real evidence (prod query / merged sha / live check) — same bar as gate 2. A
  todo from a past session can LOOK done but isn't
  ([[orphan_recovery_verify_external_state]]). Never tick something off on a hunch.
- Call the tool directly, then log it with its marker:
  - `➕` `add_todo` — new backlog item
  - `✅` `complete_todo` — verified done, evidence inline
  - `❌` `cancel_todo` — no longer relevant / superseded, reason inline
  - `🗑️` `delete_todo` — added by mistake or a duplicate
- Then flip the tab (gate 5) — no separate wait step in between.

List every applied change — marker, text, evidence/reason, and due date — in the report.

**4d. Surface still-open work so the next session inherits it.**
The loop only closes cleanly if what's unfinished is visible at the next open.
- [ ] **Open GitHub issues** — list any this session opened or touched that are
      still open (`gh issue list` on the relevant repo(s), or just the issue #s
      you know about). Name them in the report so `/session-open` re-surfaces
      them next time. A blocker parked as an issue (e.g. GH mooniex-webapp#85)
      belongs here, not silently in the chat log.
- [ ] **Deadline to-dos** — confirm every dated item from 4a/4b actually carries
      a `due_at` (not just prose). The `SessionStart` deadline hook only re-
      surfaces items that have a real `due_at` — an undated "remember later" is
      invisible to the loop. If it has a date, it MUST have `due_at`.

### 5. Flip BOTH tab layers + final report
Only after gates 1–4 pass:
```bash
bash scripts/tab-title.sh "🏁 <entry problem solved, ≤35 chars>"
bash scripts/tab-main.sh "" <N>/<N>          # every DoD item done -> a full bar
```
Both, always. A 🏁 sub tab above a half-empty progress bar is the tab bar
contradicting itself, and the CEO reads the bar first.

### 6. End the tmux session — LAST, and only on 🏁
Print the report first (below), then as the final action of the whole skill:
```bash
bash scripts/session-kill.sh
```
Since the tmux migration an iTerm tab is only a *viewer*: closing it detaches
and leaves this Claude process running — still burning quota, still counting
against the 5-session cap, still listed on the phone. 🏁 means done, so the
session should actually end rather than linger as a zombie for the CEO to hunt
down later (CEO 2026-08-07).

- **Only on `CLOSE 🏁`.** On `STAY OPEN` or `HOLD` the session must keep
  running — that is the whole point of those verdicts. Never kill on them.
- **Report first, kill last.** The script defers a self-kill a few seconds so
  the final output flushes, but nothing after this line will be seen.
- Irreversible for in-memory context: gate 4 must already have parked
  everything to LungNote. If unsure whether something was captured, the
  verdict isn't 🏁 yet.

## Output format

```
🏁 SESSION CLOSE — <entry problem>
DoD:
  [x] <item 1> — evidence: <sha / test / query>
  [x] <item 2> — evidence: <...>
External state : VERIFIED — <query result>  /  N/A repo-only  /  HOLD <reason>
Saved → LungNote (todo · due):
  CEO action-items / reminders:
    - <thing CEO must do> · due <ISO date or "—">
  Backlog (off-topic / unfinished):
    - <item> · due <date or "—">
Open issues    : <#NN title — repo>  /  none   (re-surfaced by next /session-open)
Verdict        : CLOSE 🏁  /  STAY OPEN (entry unsolved)  /  HOLD <reason>
```

## Operating rules

- **The entry problem is the only close condition.** Side quests done ≠ session
  done. Side quests undone ≠ session blocked. Judge against the charter only.
- **Verify, don't assume, external effects** — same discipline as
  cto-merge-checklist gate 7 (born from the 2026-06-10 double-post near-miss).
- **🏁 is a promise** (§32): every DoD met, nothing waiting. If unsure, it's `✅`,
  not 🏁.
- **Parking is mandatory, not optional.** An off-topic idea that's only in the
  chat log is lost; in LungNote it's a job for a future session.
