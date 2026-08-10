---
name: session-list
owner: CTO
origin: mooniex-org
scope: >-
  Read-only inventory of PAST sessions not yet 🏁-closed, excluding iTerm tabs open
  right now. --all includes closed ones; --verify cross-checks a stuck title against
  its real log to catch title-sync bugs and true ghost spawns. Does not close or
  resume anything.
description: List past CTO/CXO sessions still open, with state, blocker, and age. Trigger on /session-list and when the CEO asks "ดู session เก่า", "session ที่ค้าง", "session ไหนยังไม่ปิด", "list sessions", "what sessions are still open".
---

# Session List — inventory past sessions, minus the live tabs

Answers "which old sessions are still hanging around, and where did each one
stop?" Reads every session's last tab glyph from `state/tab-titles/*.title`
and prints a table, **excluding the iTerm2 tabs currently open** (those are
being worked right now — not stale).

This is the cross-session view. Contrast:
- [[session-worktree]] — work-breakdown of THIS one conversation
- `session_tree.py` — DB *tasks* across all projects
- **this** — every past chat *session* and its close-state

## Run it

```bash
python3 /Users/gob/Projects/Agents/scripts/session_list.py           # default: NOT-yet-closed only
python3 /Users/gob/Projects/Agents/scripts/session_list.py --all      # include 🏁 closed too
python3 /Users/gob/Projects/Agents/scripts/session_list.py --verify   # + evidence/flag columns
```

The script prints a ready Markdown table — relay it straight to the CEO (CTO
chat renders no images, see [[cto-chat-text-output]]; a table is the right form).
Default `/session-list` → run with **no flag** — shows only sessions that are
**not yet 🏁-closed** (closed ones are done; no value re-listing them, CEO
2026-06-15). Add `--all` only if the CEO wants the closed ones in too.

## Columns

| column | meaning |
|---|---|
| session | `ROLE #id` (CTO/CFO/CMO/CGO + 8-hex session id) |
| state | glyph + word — ⏳ working · ✅ pending · 🔴 blocked · 💤 idle/parked · 🏁 closed — **overlaid with the DB lifecycle** (task-728e4741): a parked session shows `· saved`, and a `force_saved` one shows `🚨 FORCE_SAVED` regardless of its (possibly stale) tab glyph |
| blocker | for 🔴, the wait; for `saved`/`force_saved`, the one-line **note** recorded at close (the entry problem, so the list is readable months later); else the `รอ …` clause; else `—` |
| created | spawn time (earliest birth of the session's title/base/log) `YYYY-MM-DD HH:MM` |
| last active (ago) | latest title/log mtime + age as `Xd Yh Zm` |
| evidence *(--verify only)* | what backs the state: `title-only` (trusted as-is) · `log NL[, merge event]` · `transcript SIZE[, saved: FILE]` · `no log/transcript found` |
| flag *(--verify only)* | `✓` verified · `⚠ stale-title→done` (real work merged, title never flipped) · `⚠ stale-title (…)` (real activity, unclear/unparked) · `💤 parked (resumable)` (a `/session-save` file exists) · `🗑 suspect (test data?)` (log looks synthetic) · `🗑 ghost-candidate` (nothing ever ran) |

Sorted by **last active, newest first**. Footer = count + per-state tally
(+ per-flag tally under `--verify`).

### Why `--verify` exists

Title-sync bugs are real (memory: `feedback_session_title_stray_file_bug`): a tab's
title can stay stuck at the spawn placeholder `"⏳ เริ่ม session"` forever
even after the session did real, merged work — or never touched anything at
all. `--verify` only deep-checks rows whose glyph is `⏳` **and** whose
summary is exactly that literal placeholder (custom titles, even short
ones, are trusted without the extra I/O). For each candidate it:

1. Reads `state/logs/<role>-<id>.log` — if it has real varying-timestamp
   entries, evidence = `log NL`, flagged `⚠ stale-title→done` when a merge
   event shows up. Identical timestamps across ≥2 lines reads as synthetic
   test data → `🗑 suspect`.
2. Falls back to a real Claude Code transcript search under
   `~/.claude/projects/**/*<id>*.jsonl` (short id = last-8-hex of the
   session's own uuid for pre-rollout sessions) — if found, tail-scans for
   a `/session-save` write and reports `💤 parked (resumable)` with the
   save filename, else `⚠ stale-title (transcript, not parked)`.
3. Neither found → `🗑 ghost-candidate` (opened, never engaged — safe to
   close via `tab-title.sh` directly since there's no live tab to run
   `/session-close` in).

## How it decides "live" (excluded)

Queries iTerm2 via `osascript` for every open tab's session name, pulls the
`#<id>`, and drops those rows. If iTerm can't be queried the table prints with
a loud `⚠ iTerm query failed — live tabs NOT excluded` header — say so, don't
pretend the exclusion happened.

## Reading the result

- **⏳ with a 0-byte log / age > a few hours** = a ghost spawn (opened, never
  charter'd, never closed). Cleanup candidates, not real work. Run with
  `--verify` to confirm before acting — some `⏳` rows LOOK like ghosts but
  their title just never got flipped (see above).
- **🔴 / ✅ / 💤-with-`รอ`** = genuinely un-closed — has pending work or a
  blocker. These are what `/session-close` should eventually resolve.
- **`· saved`** = parked on purpose (`/session-save`) to free RAM — resumable;
  the blocker cell carries the one-line note. Shown by default.
- **`🚨 FORCE_SAVED`** = closed while the work was NOT done — the one to find
  again. Loud on purpose, **never hidden** (even with a stale 🏁 glyph), and
  counted in the footer's `**parked**` tally. Resume it with the UUID in
  `c_level_sessions.resume_uuid` (or `scripts/session-kill.sh` left the
  `.uuid` file in place).
- **🏁** = already closed; hidden by default, shown only with `--all`.

Don't mutate anything here — this is a read. To actually close one, that
session runs [[session-close]]; to save its context, /session-save.
