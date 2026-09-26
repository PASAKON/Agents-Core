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
it only reads files and, once explicitly told to, writes ONE file (A's `.title`) plus one
best-effort action: if A's tmux session happens to still be alive (task-bbdfa8d1, CEO
2026-09-11 — the live-guard above only checks iTerm tabs, not tmux itself, so a session
whose tab was closed while its process kept running slips past it), it types
`/rename ⛔ MERGED→#<B_id>` into A's own pane so the CEO's Claude app entry for A carries
the merge state too, not just the local tab-title. A dead A (the common case — already
saved/parked) is a silent no-op: once a session is offline its display name can no longer
be changed at all. Never blocks the merge if the rename fails. Everything requiring
judgment (which candidate is "A", what the recap actually says, whether it's safe
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
- **A's last blocked prompt is A's last order.** When the CEO's final prompt to A was blocked by
  `scripts/hook-cache-cold-warn.py` (idle notice, prompt never re-sent), it never reached A — carry it
  forward as the first open item and act on it in B. Find it in one `tmux capture-pane` of A before
  killing A, or in A's transcript. Promoted from two runs (#95cbbb28, #6bfdc084, 2026-09-26).
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
- **One state write, always the same file — plus one best-effort rename.** A's `.title` is
  the only FILE this skill ever changes; the only other effect is the best-effort
  `⛔ MERGED→#<B_id>` app-name stamp when A's tmux is still alive (task-bbdfa8d1), which
  touches nothing on disk. If you find yourself editing A's `.log`, `.base`, or session-data
  file, stop — that's out of scope.
- **LungNote cross-check is optional and yours, not the script's.** The script has no MCP
  access; if the recap surfaces something LungNote-worthy (an open CEO action-item from A),
  that's a judgment call for you to make here, same discipline as [[session-close]] gate 4.

## Field notes
- 2026-09-26 [MISSING] §Gates 5 (live rename) — the rename is typed into A's input with `send-keys -l` + Enter, so anything already sitting in A's prompt gets the `/rename …` appended and SUBMITTED as one prompt. On #95cbbb28 the prompt showed "ลบโฟลเดอร์ --help ได้เลย" — a Drive delete — and it was only safe because `capture-pane -e` showed it wrapped in `ESC[2m` (dim): Claude Code's ghost prompt suggestion, not text anyone typed. `C-u`/`C-e C-u` did not change it. Before `--yes` on a live A, capture A's prompt line with `-e`: dim = suggestion, safe; normal weight = a real unsent draft, stop and ask · evidence: merge #95cbbb28→#83a61127 · status: pending
- 2026-09-26 [MISSING] §1 — "session ค้าง ไม่ตอบ" was not a hang: the CEO's last prompt had been blocked by `scripts/hook-cache-cold-warn.py` (idle 5 h, 845k context), which only prints a notice and waits for the prompt to be re-sent. `tmux capture-pane` of A shows it in one call; do that before diagnosing a stuck session, and carry the blocked prompt forward as A's last unanswered order · evidence: merge #95cbbb28→#83a61127; second run #6bfdc084→#a27c4702 (blocked "Negative Prompt ภาษาจีน" order) agreed, promoted to §3 rule · status: promoted
- 2026-09-26 [MISSING] §2 live-guard — when the CEO asks to merge AND kill A, the order that works is `bash scripts/session-kill.sh --status saved --note "merged into <B>" <role>-<A>` first (resumable, records why), then the dry-run passes the live-guard. Capture A's pane before the kill, it is the last cheap look at an unsent/blocked prompt · evidence: merge #6bfdc084→#a27c4702 · status: pending
- 2026-09-26 [COSTLY] §3 — `context.source: session-data` returned 10 "tasks" that were raw slash-command and task-notification lines, no real work items. The usable recap was the LAST `isCompactSummary` row of A's transcript (`~/.claude/projects/<proj>/<uuid>.jsonl`, uuid ends in A's id) plus the user/assistant text after it — read it only once A is dead · evidence: merge #6bfdc084→#a27c4702 · status: pending
