---
name: session-merge
owner: CTO
origin: mooniex-org
scope: >-
  Folds another session's context into the current one as a synthesized recap, then
  marks the source 🔗 merged. Writes exactly one file (the source's .title).
  Synthesis, not verbatim transcript splicing — to continue that session itself, use
  spawn-cto --resume instead.
description: Carry another session's context into this one, then mark it merged. Trigger on /session-merge and when the CEO says "merge session", "รวม session", "เอา session A มารวมกับอันนี้", "ย้ายมาทำที่นี่แทน".
created_by: human
audience: [cxo]
---

# Session Merge — fold session A's context into session B (this one)

The CEO has a session A already in flight (saved, maybe even mid-task) but instead of
resuming A directly, they spawned or are sitting in a different session B and want A's
context folded in here. This skill does that: pull A's context, synthesize a carry-forward
recap in this chat, and mark A merged so `/session-list` stops surfacing it as open.

Backed by `scripts/session_merge.py <role> <A_id> [B_id]`. The script is dumb and safe —
it only reads files and, once explicitly told to, writes ONE file (A's `.title`). Everything
requiring judgment (which candidate is "A", what the recap actually says, whether it's safe
to proceed) happens here, in the skill.

## Gates — work through in order

### 1. Resolve session A
- If the CEO named an id (`#xxxxxxxx`) directly, use it.
- Otherwise run `python3 scripts/session_merge.py <role>` with no id — the script shells out
  to `session_list.py` and prints the not-yet-closed candidate table. Show it and ask which
  one is A. **Never guess** — an ambiguous "the one about X" needs a confirmed id before
  step 3 touches anything.

### 2. Preview before touching anything
- Run `python3 scripts/session_merge.py <role> <A_id> --dry-run` (B_id auto-resolves from
  this session's `$CXO_SESSION_ID`/`$CTO_SESSION_ID` env — pass it explicitly only if
  merging into a session other than this one). This is read-only: it pulls A's context and
  previews the exact `.title` rewrite without writing anything.
- If the script refuses because A is currently live in an iTerm tab ("partial-log read
  risk"), **stop and relay that verbatim** — tell the CEO to close/idle A first. Don't retry,
  don't work around it by reading A's log yourself.

### 3. Synthesize the carry-forward recap (this is YOUR job, not the script's)
- The script's JSON gives raw material only: `context.source` (`session-data` = parsed
  `## Session Summary` → Tasks / Files Modified / Notes-for-next bullets, or `log-tail` = last
  ~200 raw log lines when no session-data file exists, or `none` if neither was found).
- Turn that into a done/doing/blocked/left recap in the same shape as [[session-worktree]]'s
  tree (✅ done · 🔄 doing · 🔴 blocked · ⬜ left), headed "carried forward from #A". Use
  judgment — the raw Tasks list is often a flat log of slash-commands and pasted skill output,
  not a clean task list; read through it, don't paste it verbatim.
- If `context.source` is `"none"` (no session-data file, no log), say so plainly — don't
  fabricate a recap from nothing.

### 4. HARD LIMIT — state this to the CEO, every time
**This produces a synthesized context-carry-forward summary, NOT literal verbatim message
splicing.** The recap is your best reconstruction of what A did — it is not A's actual
conversation transcript grafted into B. If the CEO wants A's exact turn-by-turn history,
this is the wrong tool: point them at `spawn cto --resume <A_id>` (continuing A itself,
functional for standard 8-hex session ids since Step 1 of this work) instead of merging
into a separate session B.

### 5. Confirm, then apply
- Show the recap and the exact title-rewrite preview (`title_update.before` →
  `title_update.after` from the dry-run JSON). **Wait for explicit confirmation** before
  mutating anything — same bar as [[session-close]] gate 4c, never mutate on a hunch.
- Once confirmed, re-run without `--dry-run`, adding `--yes`:
  `python3 scripts/session_merge.py <role> <A_id> [B_id] --yes`. This writes A's
  `.title` to `<A's .base> 🔗 merged→#<B_id>` (truncated to 60 chars, same rule as
  `tab-title.sh`). A's `.log`, `.base`, and session-data files are never touched — the
  audit trail stays intact, only the tab-title glyph changes.
- After this, A drops out of `/session-list`'s default view (🔗 hides same as 🏁) — it's
  still visible with `--all`.

## Output format

```
🔗 SESSION MERGE — #<A_id> → #<B_id>
Source          : session-data <path>  /  log-tail <path>  /  none
Carried forward from #<A_id>:
  ✅ done
    - <item>
  🔄 doing / notes-for-next
    - <item>
  🔴 blocked
    - <item>
  ⬜ left
    - <item>
A marked         : <before title> → <after title>
Verdict          : MERGED 🔗  /  REFUSED (<reason>)  /  HOLD (awaiting CEO confirm)
```

## Rules

- **Never mutate without an explicit confirm.** Step 2's dry-run is not optional — always
  preview before `--yes`.
- **The live-guard is not yours to bypass.** If the script refuses because A is live, that's
  final for this turn — don't read A's log/session-data directly as a workaround.
- **Synthesis, not splicing** — see the HARD LIMIT above. Say it out loud in the report, not
  just in your head.
- **One state write, always the same file.** A's `.title` is the only thing this skill ever
  changes. If you find yourself editing A's `.log`, `.base`, or session-data file, stop —
  that's out of scope.
- **LungNote cross-check is optional and yours, not the script's.** The script has no MCP
  access; if the recap surfaces something LungNote-worthy (an open CEO action-item from A),
  that's a judgment call for you to make here, same discipline as [[session-close]] gate 4.
