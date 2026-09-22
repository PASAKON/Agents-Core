---
name: session-close
owner: CTO
origin: mooniex-org
scope: >-
  Exit gate only. Verifies the Entry Problem is solved and every Definition-of-Done
  item checked before allowing the 🏁 glyph, and parks leftovers to LungNote. On an
  unmet DoD it records force_saved (closed unfinished, flagged loud) instead of
  refusing — STAY OPEN is the CEO's explicit "still working" choice. Enforces
  IRON-RULES §35. Companion to session-open.
description: Verify a session's Entry Problem is actually solved before closing it 🏁. Trigger on /session-close and when the CEO says "ปิด session", "จบงาน", "พอแค่นี้", "close out", "done for now".
created_by: human
audience: [cxo]
---

# Session Close — exit gate tied to the entry problem

A session closes cleanly (🏁) only when its **one entry problem** is solved. "We
talked a lot" is not 🏁. This skill runs the exit gate from [IRON-RULES §35](../../../../LLMs/IRON-RULES.md):
if the Definition of Done isn't verifiably met it no longer refuses — it records
**force_saved** (closed unfinished, flagged loud) so the session ends and frees
RAM, and the unfinished work stays findable later. `STAY OPEN` remains for the
CEO's explicit "I'm still working."

## Gates — 🏁 only if every one passes; else force_saved

### 1. Recall the charter
- [ ] State the session's **Entry Problem** (one sentence) and its **DoD list**
      as pinned at open. If no charter was set, reconstruct it now from the
      session's actual work, then judge against it.
- [ ] 🏁 Cross-check against the DB: `python3 -m tools.session_charter get`
      should echo the same Entry Problem — if it comes back empty, this
      session's `/session-open` never ran step 1b, worth naming in the report.

### 2. Every DoD item passes — with evidence
- [ ] Walk each DoD item; mark `[x]` only with concrete proof (sha, test count,
      query result, CEO "approve"). Quote the evidence inline.
- [ ] No item marked done by narration ("should be working") — that's a FAIL.

### 2b. Skill learning folded (ADR 0026)
Every `## Skill learning` line this session produced — yours and every worker
report you reviewed — has left the chat. A line still only in chat is lost the
moment the session ends (measured 2026-09-22).
- [ ] Each WRONG / MISSING / COSTLY line is filed: a Field note appended to the
      skill it names (`skill(<name>): note — …`), a rule change carrying its
      evidence (`skill(<name>): rule|flip — …`), a memory file, or a new-skill
      proposal. Quote the sha(s) / memory path.
- [ ] `python scripts/skill-curator.py notes` — nothing MALFORMED; anything
      CONTESTED is named in the report for the CEO to rule on.
- [ ] Unfiled lines → no 🏁. The session force-saves with the unfiled lines
      named in the note.

### 3. External-state verified (side-effect work)
Applies if the entry problem touched anything outside the repo — DB write, social
post, deploy, email, payment, upload.
- [ ] Query the external system for evidence the effect actually landed. **A commit
      proves authorship, never execution.** Paste the result.
- [ ] If it can't be queried (no creds/access) → the session does **not** 🏁-close;
      report it as HOLD (not 🏁). If the CEO closes anyway it lands as **force_saved**
      with that unverified item named in the note — it is not left running by default.

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

- [ ] If the entry problem itself is **unfinished**: this close is not 🏁 — it's
      a **force_saved** park. Name what's unfinished in one line; that note is what
      `session-kill.sh --status force_saved --note …` records so the session is
      findable again. Per §35 an unsolved entry problem is not a 🏁; under this
      gate it closes anyway as force_saved rather than lingering as a live session
      burning RAM. `STAY OPEN` stays available only when the CEO decides mid-gate
      they are still working.

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

### 4e. Push the auto-memory repo (task-8d37c0f1)
`MEMORY.md` gains nothing this session wrote until it leaves this machine —
push is the exit gate for memory the same way it already is for any other
DEV's work ("push คือด่านออกของ spoke").
```bash
python3 -m tools.memory_sync push
```
- **Exit 0** (incl. "nothing changed") → continue normally.
- **Non-zero** → this is **not** a 🏁. Record it as `force_saved` with the
  reason named, same as any other unmet gate — don't silently drop to
  `session-kill.sh --status closed` anyway. Name the exact `memory_sync`
  error in the report's Verdict line.

### 5. Flip BOTH tab layers + final report
Only after gates 1–4 pass:
```bash
bash scripts/tab-title.sh "🏁 <entry problem solved, ≤35 chars>"
bash scripts/tab-main.sh "" <N>/<N>          # every DoD item done -> a full bar
bash scripts/session-rename.sh --prefix "✅" "<entry problem, short>"   # verdict CLOSE 🏁
bash scripts/session-rename.sh --prefix "⏸" "<entry problem, short>"   # verdict FORCE-SAVED
```
Both tab layers, always. A 🏁 sub tab above a half-empty progress bar is the
tab bar contradicting itself, and the CEO reads the bar first.

The rename call is the same display-layer sync `/session-worktree` does mid-
session ([[session-worktree]]) — usually a silent `unchanged: <topic>` no-op,
sent here so a closing session's Claude display name reflects what it ended
up being about, not the entry problem it was chartered under if that topic
drifted along the way. `--prefix` stamps the CEO's Claude app entry with the
verdict this gate just reached (task-bbdfa8d1, CEO 2026-09-11 "เช็คไม่ได้เลย
ว่ามี session เปิดจริงไหม") — ✅ on a verified 🏁, ⏸ on FORCE-SAVED (unfinished
but resumable, same "parked" reading as [[session-save]]'s ⏸). Pick the ONE
line matching this gate's actual verdict, never both. If the rename fails
(no `$TMUX`, or the send errors) log it and continue to step 6 regardless —
stamping must never block the close it belongs to.

### 6. End the tmux session — LAST, on 🏁 or force_saved
Print the report first (below), then as the final action of the whole skill:
```bash
bash scripts/session-kill.sh --status closed                                       # on a verified 🏁
bash scripts/session-kill.sh --status force_saved --note "<one line of what's unfinished>"
```
Since the tmux migration an iTerm tab is only a *viewer*: closing it detaches
and leaves this Claude process running — still burning quota, still counting
against the 5-session cap, still listed on the phone. Both 🏁 (done) and
force_saved (unfinished, parked) mean the live session should end rather than
linger as a zombie burning RAM for the CEO to hunt down later (CEO 2026-08-07).
The `--status` flag records WHY it ended so [[session-list]] can tell a finished
close from a flagged one months later.

- **Kill on `CLOSE 🏁` (→ closed) and on `FORCE-SAVED` (→ force_saved).** Both
  end the session; the status is the only difference.
- **Never kill on `STAY OPEN`** — that verdict is the CEO deciding they are
  still working, so the session keeps running. This is the one refusal that
  remains, and it is the CEO's explicit choice, not the gate refusing to
  record-and-park.
- **Report first, kill last.** The script defers a self-kill a few seconds so
  the final output flushes, but nothing after this line will be seen.
- Irreversible for in-memory context: gate 4 must already have parked
  everything to LungNote. force_saved especially — its whole point is that the
  unfinished work is recoverable from LungNote + the recorded note, so capture
  it before the kill.

## Output format

```
🏁 SESSION CLOSE — <entry problem>
DoD:
  [x] <item 1> — evidence: <sha / test / query>
  [x] <item 2> — evidence: <...>
External state : VERIFIED — <query result>  /  N/A repo-only  /  HOLD <reason>
Skill learning : filed — <skill> sha:<abc1234>, <skill> sha:…  /  none this session  /  CONTESTED: <skill> (CEO)
Saved → LungNote (todo · due):
  CEO action-items / reminders:
    - <thing CEO must do> · due <ISO date or "—">
  Backlog (off-topic / unfinished):
    - <item> · due <date or "—">
Open issues    : <#NN title — repo>  /  none   (re-surfaced by next /session-open)
Verdict        : CLOSE 🏁 (status=closed)
               / FORCE-SAVED (entry unfinished, status=force_saved) — <one line of what's unfinished>
               / STAY OPEN (still working — session keeps running)
```

## Operating rules

- **The entry problem is the only 🏁 condition.** Side quests done ≠ session
  done. Side quests undone ≠ session blocked. Judge against the charter only.
- **Unfinished ≠ refused.** An unmet DoD no longer holds the session open by
  default — running `/session-close` on unfinished work force-saves it: ends the
  session, flags it `force_saved` with the unfinished bit named in the note. Only
  `STAY OPEN` keeps it running, and only when the CEO means "I'm still working."
  A live session burning RAM is exactly the cost this avoids.
- **Verify, don't assume, external effects** — same discipline as
  cto-merge-checklist gate 7 (born from the 2026-06-10 double-post near-miss).
- **🏁 is a promise** (§32): every DoD met, nothing waiting. If unsure, it's
  force_saved (closed unfinished), not 🏁.
- **Parking is mandatory, not optional.** An off-topic idea that's only in the
  chat log is lost; in LungNote it's a job for a future session.

## Field notes

- 2026-09-22 [MISSING] §2b — no gate caught a C-level's own `## Skill learning` lines; they stayed in chat and were lost at session end, so gate 2b was added · evidence: session cto-0e8d80b8, CEO OK 2026-09-22, ADR 0026 · status: promoted
- 2026-09-23 [MISSING] §2b — `python scripts/skill-curator.py notes` as written cannot run in a C-level Bash shell: `python` is not on PATH (`command not found`) and system `python3` dies on `import yaml` (ModuleNotFoundError, exit 1, output looks like "no findings" if grepped). Works as `.venv/bin/python scripts/skill-curator.py notes` · evidence: session cto-01c3a0e8, VIRTUAL_ENV unset · status: pending
