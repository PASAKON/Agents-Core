---
name: session-save
owner: CTO
origin: mooniex-org
scope: >-
  Wraps ECC's save-session engine (credit: ECC plugin) and adds the org's LungNote
  layer — writes a dated file to ~/.claude/session-data/ plus a SID-tagged summary,
  blocker, and timeline to LungNote. Then ENDS the session everywhere (parked,
  resumable) via scripts/session-kill.sh --status saved, so it stops costing RAM.
  This is the CEO's "park it" move, not a mid-session checkpoint.
description: Park this session — save full context to disk + a SID-tagged summary in LungNote, then END the session everywhere so it frees RAM. Resumable later. Trigger on /session-save and when the CEO says "save session", "เซฟ session", "จอด session", "บันทึก session", "เก็บไว้ก่อน", or before walking away to free memory.
created_by: human
audience: [cxo]
---

# Session Save — park this session for a future resume

Capture everything this session did, write it to a dated file, park a short
overview in LungNote — **then end the session everywhere**. This is the CEO's
"park it" move: the work is unfinished but a live session costs RAM (the Mac
sits at ~87% with swap ~83%), so the point of saving is to walk away *and free
the memory*. `/session-save` is the org-standard name that lines up with the
rest of the `/session-*` family ([[session-open]], [[session-close]],
[[session-list]], [[session-worktree]]).

The session ends as **`saved`** — parked on purpose, resumable. That is
distinct from [[session-close]]'s 🏁 (`closed`, work finished) and from its
force-close (`force_saved`, closed while unfinished by mistake — flagged loud).
A parked session is findable again by its LungNote SID tag and its saved file.

> **Engine + credit:** the local-file save logic is **ECC's `save-session`**
> (`~/.claude/plugins/marketplaces/ecc/commands/save-session.md`). This skill
> wraps it — all credit to the ECC plugin for the file mechanics — and adds two
> org-specific steps ECC has no concept of: the LungNote park and the
> session-end below. Equivalent local-file behavior to running `/save-session`;
> resume later with ECC's `/resume-session` (or `ecc:resume-session`).

## How to run it

1. **Local file** — prefer delegating to the **`ecc:save-session`** skill (or
   `/save-session` command) so file mechanics stay in sync with ECC. If it's
   unreachable, use the inlined fallback below to produce an identical file.
2. **LungNote park (mandatory, every run — not optional)** — see the section
   below. Do this regardless of which path step 1 took.
3. Tell the CEO both: the resolved local file path, and confirmation the
   LungNote entry was written (with its `[SID:...]` tag).
4. **End the session — LAST, after the report prints** (see the section below).
   The context is on disk and the trail is in LungNote, so the live session can
   now be ended to free RAM. This is what makes `/session-save` a *park*, not a
   checkpoint.

### Fallback (ECC process, inlined) — local file only
1. **Gather** — `git diff` / recall: files changed, what was tried, what passed,
   what failed and the EXACT error, decisions, blockers, the next step.
2. **Folder** — `mkdir -p ~/.claude/session-data`
3. **Write** `~/.claude/session-data/YYYY-MM-DD-<short-id>-session.tmp`
   (today's date; `<short-id>` = 8+ lowercase/digit/hyphen chars to avoid
   same-day collisions, e.g. `2026-06-15-a1b2c3d4-session.tmp`).
4. **Sections** (write every one honestly — "N/A" beats omitting):
   What We Are Building · What WORKED (with evidence) · What Did NOT Work (and
   why — the most important section) · What Has NOT Been Tried Yet · Current
   State of Files (table) · Decisions Made · Blockers & Open Questions · Exact
   Next Step · Environment & Setup Notes (only if relevant).
5. **Confirm** — show the full file, ask "accurate? anything to add before close?"

## LungNote park (mandatory, every run)

The local file is deep; LungNote gets the **short version** — enough for
future-you (or the CEO) to know at a glance what happened and whether it's
safe to walk away. Follow IRON-RULES §40's SID-tag convention exactly (same
tag format [[session-close]] and [[session-merge]] use).

1. **Resolve the full SID** — the same role-prefixed id already used for
   tab/log naming:
   - CTO session → `cto-$CTO_SESSION_ID`
   - CXO session → `cxo-$CXO_SESSION_ID`
   - Neither env var set (plain Claude Code session, not spawned via
     `spawn-cto.sh`/`spawn-cxo.sh`) → fall back to `claude-<last 8 hex of
     $CLAUDE_CODE_SESSION_ID>` and say so in the report — note this fallback
     form has no `/session-merge` target, it's provenance-only.
2. **Write the one-line overview** — pull straight from the Gather step, don't
   re-derive: what this session did, whether it hit a **blocker** (name it, or
   say "none"), and the **exact next step** if anything is left open.
3. **Timeline/deadline, if any** — if a concrete date is in play (CEO
   deadline, external SLA, a "come back on X" point), convert any relative
   date ("พรุ่งนี้", "ภายใน 3 วัน") to an absolute ISO-8601 date using today's
   date from context, and set `due_at`. No real date → omit `due_at` entirely;
   an undated todo is a quiet trail marker, not a reminder (the SessionStart
   deadline hook only surfaces items that carry `due_at`).
4. **Call `mcp__lungnote__add_todo`** with:
   `text` = `[SID:<full-id>] <one-line: what happened> — blocker: <blocker or "none"> — next: <next step or "done">`
   `due_at` = the ISO date from step 3, or omitted.
5. **If the session ended clean with nothing to resume** (no blocker, no open
   next step), immediately `mcp__lungnote__complete_todo` it right after
   adding — this keeps the audit trail without leaving a false-pending item
   in the CEO's list. If there's a real blocker/next-step, leave it open so it
   surfaces at the next `/session-open` LungNote review.
6. **Retrieval later is `list_todos`** (with `include_done:true` and an
   explicit `limit`) — **never `search_notes`**, which only searches note
   text and will not find a todo's `[SID:...]` tag.

This is a different job from [[session-close]]'s own LungNote parking (gate
4a/4b there captures individual CEO action-items and backlog at the *actual
close* gate). This step runs on *every* `/session-save` and it's always exactly
one SID-tagged entry per save, not one per action-item. No LungNote schema
change either way; both use the existing `text` field. Because `/session-save`
parks (ends the session), this todo is the **resume trail** — leave it OPEN so
it surfaces at the next `/session-open` LungNote review. Only `complete_todo`
it (step 5) when there is genuinely nothing left to resume.

## End the session — LAST, after the report prints

The context is on disk and the trail is in LungNote, so the live session is now
pure RAM cost. End it everywhere, as the **final action** of the whole skill —
after the report to the CEO has printed, mirroring [[session-close]] gate 6.
Push the auto-memory repo first (task-8d37c0f1) — a session that's about to
park has already written this run's lessons to `MEMORY.md`, and those are
lost the moment the process ends if they never left this machine:
```bash
python3 -m tools.memory_sync push
bash scripts/session-rename.sh --prefix "⏸" "<topic, short>"
bash scripts/session-kill.sh --status saved
```
A non-zero `memory_sync push` doesn't block the park (the CEO's "walk away
and free RAM" still happens) — name the failure in the report instead, same
as any other best-effort step here.
The rename call stamps the CEO's Claude app entry with ⏸ (task-bbdfa8d1, CEO
2026-09-11 "เช็คไม่ได้เลยว่ามี session เปิดจริงไหม") BEFORE the kill takes the
pane away — this is the only moment left to change what the app shows, since
a session that has already gone offline cannot be renamed. If the rename
fails (no `$TMUX`, or the send errors) log it and run the kill anyway —
stamping must never block the park.

This records `status='saved'` in `c_level_sessions` (so [[session-list]] shows
it as parked + resumable with its note), preserves the `.uuid` resume key, and
kills the tmux session. `--status saved` is what makes a parked session
distinguishable from a 🏁-closed one or a mistake `force_saved` one.

- **Report first, kill last.** The script defers a self-kill a few seconds so
  the final output flushes — but nothing after this line will be seen.
- **Closing the iTerm tab does NOT do this** — it only detaches from tmux and
  leaves the Claude process running, still burning quota and counting against
  the cap. `--status saved` is the only thing that actually parks it.
- **Don't run it if the CEO only wanted a context snapshot.** That is rare
  (they don't use mid-session checkpoints); if they say so explicitly, save the
  file + LungNote and stop at step 3, leaving the session running.

## Notes

- One file per session — never append to a previous session's file.
- The "What Did NOT Work" section is the payload: it stops the next session from
  blindly retrying dead ends.
- Canonical store is the global `~/.claude/session-data/` (shared with ECC), not
  a repo path — so any future session, in any project, can resume it.
- The LungNote SID tag does **not** auto-load the session's context — it's a
  pointer. Pair it with `/session-merge <full-id>` (CTO/CXO) or the local file
  path from step 1 to actually pull the context back in.
- `/session-save` parks (status `saved`); [[session-close]] is the exit gate that
  flips the tab to 🏁 (`closed`) or `force_saved`. Same kill mechanism, different
  status — that is how the three end-states stay distinguishable months later.
