---
name: session-save
description: Save the current session's full context (what was built, what worked, what failed, blockers, exact next step) to a dated file in ~/.claude/session-data/ so a future session can resume with zero memory loss. This is the Mooniex-org canonical name — it wraps ECC's save-session engine (credit: ECC plugin). Trigger on /session-save and when the CEO says "save session", "เซฟ session", "บันทึก session", "save the session before we close", or before a context-limit / handoff. Sits next to /session-open, /session-close, /session-list, /session-worktree.
---

# Session Save — persist context for a future resume

Capture everything this session did and write it to a dated file so the next
session picks up exactly where this one stopped. `/session-save` is just the
org-standard name that lines up with the rest of the `/session-*` family
([[session-open]], [[session-close]], [[session-list]], [[session-worktree]]).

> **Engine + credit:** the actual save logic is **ECC's `save-session`**
> (`~/.claude/plugins/marketplaces/ecc/commands/save-session.md`). This skill is
> a thin alias over it — all credit to the ECC plugin. Equivalent to running
> `/save-session`; resume later with ECC's `/resume-session` (or `ecc:resume-session`).

## How to run it

Prefer delegating to the engine so behaviour stays in sync with ECC:

1. Invoke the **`ecc:save-session`** skill (or the `/save-session` command).
2. When it finishes, tell the CEO it was saved under the org `/session-save`
   alias and show the resolved file path.

If for any reason the ECC skill isn't reachable, do the save yourself following
ECC's process (so the output is identical):

### Fallback (ECC process, inlined)
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

## Notes

- One file per session — never append to a previous session's file.
- The "What Did NOT Work" section is the payload: it stops the next session from
  blindly retrying dead ends.
- Canonical store is the global `~/.claude/session-data/` (shared with ECC), not
  a repo path — so any future session, in any project, can resume it.
- Saving ≠ closing. `/session-save` preserves context; [[session-close]] is the
  exit gate that flips the tab to 🏁. Often you save, then close.
