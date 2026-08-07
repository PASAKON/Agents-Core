---
name: session-save
owner: CTO
origin: mooniex-org
scope: >-
  Wraps ECC's save-session engine (credit: ECC plugin) and adds the org's LungNote
  layer — writes a dated file to ~/.claude/session-data/ plus a SID-tagged summary,
  blocker, and timeline to LungNote. Saves state only; does not close the session.
description: Save this session's full context to disk and park a SID-tagged summary in LungNote. Trigger on /session-save and when the CEO says "save session", "เซฟ session", "บันทึก session", or before a context limit or handoff.
---

# Session Save — persist context for a future resume

Capture everything this session did and write it to a dated file so the next
session picks up exactly where this one stopped — **then park a short overview
in LungNote too**, so the resume trail is visible even to someone who never
opens `~/.claude/session-data/`. `/session-save` is just the org-standard name
that lines up with the rest of the `/session-*` family ([[session-open]],
[[session-close]], [[session-list]], [[session-worktree]]).

> **Engine + credit:** the local-file save logic is **ECC's `save-session`**
> (`~/.claude/plugins/marketplaces/ecc/commands/save-session.md`). This skill
> wraps it — all credit to the ECC plugin for the file mechanics — and adds one
> org-specific step ECC has no concept of: the LungNote park below. Equivalent
> local-file behavior to running `/save-session`; resume later with ECC's
> `/resume-session` (or `ecc:resume-session`).

## How to run it

1. **Local file** — prefer delegating to the **`ecc:save-session`** skill (or
   `/save-session` command) so file mechanics stay in sync with ECC. If it's
   unreachable, use the inlined fallback below to produce an identical file.
2. **LungNote park (mandatory, every run — not optional, not just at close)** —
   see the section below. Do this regardless of which path step 1 took.
3. Tell the CEO both: the resolved local file path, and confirmation the
   LungNote entry was written (with its `[SID:...]` tag).

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
close* gate). This step runs on *every* `/session-save` — mid-session
checkpoints included — and it's always exactly one SID-tagged entry per save,
not one per action-item. No LungNote schema change either way; both use the
existing `text` field.

## Notes

- One file per session — never append to a previous session's file.
- The "What Did NOT Work" section is the payload: it stops the next session from
  blindly retrying dead ends.
- Canonical store is the global `~/.claude/session-data/` (shared with ECC), not
  a repo path — so any future session, in any project, can resume it.
- The LungNote SID tag does **not** auto-load the session's context — it's a
  pointer. Pair it with `/session-merge <full-id>` (CTO/CXO) or the local file
  path from step 1 to actually pull the context back in.
- Saving ≠ closing. `/session-save` preserves context; [[session-close]] is the
  exit gate that flips the tab to 🏁. Often you save, then close.
- **This skill never kills the tmux session** — mid-session checkpoints are a
  primary use, and ending the session would defeat that. Ending it is
  [[session-close]]'s gate 6, which runs only on a verified 🏁. When the CEO
  saves *because* they're walking away, offer the command rather than assuming:
  ```bash
  bash scripts/session-kill.sh
  ```
  Worth offering explicitly, because closing the iTerm tab does NOT do this —
  it only detaches from tmux and leaves the session running.
