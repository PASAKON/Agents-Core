# Plan: New session names (effective immediately) + close terminal windows on Mac + Watch in the Claude app

**Author:** CTO Main, 15 Oct 2026 ~05:10 TH
**Owner:** PH#7cf OrgRestructure
- runner (Codex first) writes the code
- PH#7cf reviews, merges, and deploys directly
- Mac part: Mac PH (#671f688f) tests it
- Tasks requiring CEO hands-on action: 1-line sudo command on Mac (M10c) and visual check on mobile

This file replaces `brief-7cf-runwatch-macoff.md` (sections A, B remain the same, and adds section N and E2E testing)

## Background (CEO, 15 Oct)
- "ส่วนใหญ่ฉันจะทำงานผ่าน ClaudeCode APP ผ่านมือถือและ Desktop เป็นหลัก แทบไม่ได้เปิดมาดูใน Terminal แล้ว" (Mostly I work through the ClaudeCode APP on mobile and Desktop as my main interface; I hardly ever open Terminal to look anymore.)
- "ชื่อ Session บน Remote ก็สำคัญ ยาวไปก็ไม่ได้ สั้นไปข้อมูลก็ไม่พอ … 3 Device 3 Provider ชื่อ role ชื่องาน รวมถึง SID" (Session names on Remote are also important: too long doesn't work, too short lacks enough info … 3 Devices, 3 Providers, role name, task name, including SID.)
- "เขียนแผนอย่างละเอียด พร้อมการทดสอบแบบ E2E · name ในรูปแบบใหม่มีผลบังคับใช้ตั้งแต่ตอนนี้ และย้อนกลับใน Session ทุก Device ที่กำลังออนไลน์อยู่" (Write a detailed plan with E2E testing · the new name format takes effect starting right now and applies retroactively to all currently online sessions across every device.)
- Watch: "เอาทุกสีนั้นแหละ ตามนั้นได้เลย" (Take all those colors, go ahead with that as proposed.)

## Work order (do step by step; each step can merge without waiting for the next step)
| Step | Task | Waits for |
|---|---|---|
| N | New names; rename all currently online sessions | Nothing (CEO ordered to do it "ตั้งแต่ตอนนี้" (starting right now)); do before other tasks in PH#7cf's queue, including Thai batches [ambiguous: "รวม Thai batches" can mean "including the Thai batches" (preempting them) or "combining with the Thai batches"] |
| N-Mac | Rename sessions on Mac | N merged + CEO pastes the M10c sudo command on Mac |
| A | Close terminal windows on Mac | N |
| B | Watch | N (because it uses the same name builder) |

---

## N. New name format

### N.1 Principles
- Order: **host → role → model → #sid → task** because the mobile app truncates names from the end, so the part identifying who it is must come first.
- The name body (excluding the host emoji) is **no more than 32 characters** long; any overflow is truncated at the end and replaced with "…" [ambiguous: whether the 32-character count includes the space after the host emoji or the trailing "…" itself when truncated].
  - This number will be adjusted again once the CEO sends a screenshot of the list view in the app (the value lives in `NAME_BODY_MAX` in one place).
- Default values set in place of the 3 answers the CEO has not given yet (changeable in a single constant) [ambiguous: states "3 answers" ("คำตอบ 3 ข้อ") but lists only 2 sub-bullets below (the 3rd may be `NAME_BODY_MAX` above); "ในค่าคงที่ตัวเดียว" ("in a single constant") may mean one constant per setting or one single constant]:
  - **Remove persona names** (Kavin/Ging/SomPong) because they only set tone of voice and do not belong in the name [ambiguous: SomPong is listed here to remove, yet N.2 and N.3 keep `🌐 COO SomPong`].
  - **Remove PH lane** (`(CTO)`/`(CMO)`) because the project name already indicates the lane.
- **tmux session name must not change** (`cto-<id>`, `project_head-<id>`, `wd-<id>`, `sompong`) because Console, watchdog, and routing read these names.

### N.2 Formats
| Type | Format | Example |
|---|---|---|
| C-level | `<H> <ROLE>#<id3> <topic>` (default topic = `Main`) | `🌐 CTO#c34 Main` |
| COO | Same as C-level; if there is no org sid, there is no `#<id3>` | `🌐 COO SomPong` |
| PH | `<H> PH#<id3> <Project>[+<Project>]` | `🌐 PH#7cf OrgRestructure` |
| Worker (Claude) | `<H> <Short>·<M>#<id3> <Head>: <job>` | `🌐 Dev·S#49b Org: sparse worktrees` |
| Watch | `<H> Watch#<id3> Runs: <N><ไฟ>` (`<ไฟ>` = status light) | `🌐 Watch#a1b Runs: 2🟢` |
| Worker on winbox | Pure ASCII, no emoji, use `.` instead of `·` | `Dev.S#49b Org: sparse worktrees` |

- `<H>` is the host emoji: 💻 Mac · 🌐 Contabo · 🖥️ winbox (already in `HOST_EMOJI`)
- `<M>` is the worker model: O = Opus, S = Sonnet, H = Haiku
  - C-level and PH are always Opus, so this is omitted.
  - Codex/AGY have no session in the app (Remote Control supports Claude only); they appear as rows in the Watch table.
- `<Head>` uses the short project name, no more than 10 characters.
  - Use the `short:` key in `config/projects.yaml` if present; otherwise use the first 10 characters.
  - Defaults: OrgRestructure→Org, SpendGuard→Spend, BlackLiquidity→BlackLiq, MimiPage→Mimi
- Watch lights (`<ไฟ>`): 🟢 running normally · 🟡 a task is quiet for over 15 minutes · 🔴 a task failed or died (stays lit until the CEO asks for status or a task is re-sent [ambiguous: "หรืองานถูกส่งใหม่" can mean "until that failed task is re-dispatched" or "until any new task is dispatched"]) · ⚪ no tasks, closing
- Leading status prefixes from `session-rename.sh --prefix` (⏸ ✅) still work as before [ambiguous: does not specify whether the prefix goes before `<H>` or after `<H>`, or whether it counts toward the 32-character `NAME_BODY_MAX`].

### N.3 Currently online sessions to rename (from `live-sessions.sh --all`, 15 Oct 04:42 TH)
| Host | Old name | New name |
|---|---|---|
| Contabo | CTO (Kavin) — CTO Main | 🌐 CTO#c34 Main |
| Contabo | CMO (Ging) — CMO Main | 🌐 CMO#ef0 Main |
| Contabo | COO (SomPong) | 🌐 COO SomPong |
| Contabo | PH#7cf (CTO) - OrgRestructure | 🌐 PH#7cf OrgRestructure |
| Contabo | PH#6c4 (CTO) - SpendGuard | 🌐 PH#6c4 SpendGuard |
| Contabo | PH#f35 (CTO) - CookieRun | 🌐 PH#f35 CookieRun |
| Contabo | PH#13d (CMO) - BlackLiquidity | 🌐 PH#13d BlackLiquidity |
| Contabo | PH#36c (CMO) - MimiPage | 🌐 PH#36c MimiPage |
| Contabo | 🌐 Dev#49b - OrgRestructure: Item 5: sparse… | 🌐 Dev·S#49b Org: Item 5: sparse wo… |
| Mac | MAC CTO #671f688f (PH LastBell + Scriptable) | 💻 PH#671 LastBell+Scriptable (if PH lock exists) or 💻 CTO#671 LastBell+Scriptable [ambiguous: whether role is determined by PH lock or hub role] |
| Mac | MAC CTO #f39cb080 (PH LuminaSkies V2.6 push + M-R) | 💻 PH#f39 LuminaSkies (or CTO#f39 according to role in hub) [ambiguous: drops "V2.6 push + M-R" from the parenthesized topic, and uses "role in hub" instead of "PH lock" above] |
| winbox | No running sessions | New sessions get the new name format at spawn |

The CEO's personal sessions (role `ceo` or unknown) are not touched, same as the existing rule.

### N.4 Changes required
| File | What to change |
|---|---|
| `lib/session_names.py` | New name builders `clevel_name`, `ph_session_name`, `worker_name(…, model)`, `watch_name` + `NAME_BODY_MAX`; `rule_problem` reports "old shape"; parsers (`parse_short`, `PH_NAME_RE`, `WORKER_NAME_RE`) **accept both old and new formats** throughout the transition |
| `tools/rename_service.py` | `build_name` uses the new format; sweep (M10d #323) changes from only adding the emoji to building the full new name while keeping the existing topic (topic extracted from the old name: the part after " — ", inside "( )" of the MAC CTO format, or the project name); do this for workers too (role, model, and head read from the task row) [ambiguous: for C-level old names like `CTO (Kavin) — CTO Main`, the part after `" — "` is `CTO Main`, whereas N.3 expects `Main` with `<ROLE> ` stripped; for MAC CTO old names, inside `"( )"` includes `PH ` and `V2.6 push + M-R` which N.3 strips] |
| `scripts/session-rename.sh` | Remove the `<MACHINE> <ROLE> #<id> (<topic>)` format (line 5); route all paths through `rename_service preview/request` |
| `scripts/cto-claude.sh`, `scripts/cxo-claude.sh`, `scripts/spawn-ph.sh`, `tools/delegate.py`, `tools/node_dispatch.py` | Spawn-time names are built solely from `lib/session_names`; do not assemble strings manually |
| `tools/live_sessions.py` | Display the new name format; old format counts as off-rule with reason "old shape" |
| `roles/cto.md` line 6 and other role files containing "Session name:" | Change to the new format (CTO authorized including this in this PR) |
| `docs/ops/live-sessions.md` | Name format table |

**Must check before editing:** grep every place that reads session names (`PH_NAME_RE`, `WORKER_NAME_RE`, `parse_short`, `_C_LEVEL_BODY_RE`, `close_tab` in `tools/itermtab.py`, `send_to_cxo`, and hooks that match names); every place must accept both 2 formats.

### N.5 Deploy
- **Contabo:** `rename-service.service` runs from files in Core.
  - Before restarting, per CLAUDE.md rules, check first where tmux is [ambiguous: literally "where tmux is" ("tmux อยู่ที่ไหน"), i.e. whether tmux sessions are inside the service cgroup that would be killed on restart].
  - If the unit needs to be restarted, PH puts up the Run card themselves [ambiguous: "ขึ้นการ์ด Run เอง" can mean "post a Run approval card themselves" or "create and execute the Run card themselves"].
- **Mac:** Must install M10c (#289), which is a LaunchDaemon that uses sudo.
  - Once N is merged, CTO Main will send a 1-line command pinning the sha for the CEO to paste on the Mac.
  - If the CEO is not at the Mac yet (traveling), sessions on the Mac will keep using the old names until it is installed, or until those sessions are closed and reopened (new names are assigned at spawn once Core on the Mac has pulled).

---

## A. Close terminal windows on Mac
- **`config/hosts.yaml`:** Add per-host `terminal_window`, default true, set mac: false, winbox unchanged.
  - Implement the helper the same way as `runners/worker_init.remote_control_args`.
- **`scripts/spawn-cto.sh` (osascript :310), `scripts/spawn-cxo.sh`, the tab-opening part in `tools/itermtab.py`:** If the value is false, use `tmux new-session -d` and do not open iTerm.
- **Pitfall:** `spawn-cto.sh:281-284` creates tmux from inside iTerm because `cto-claude.sh` must find `client_tty`; if there is no client, fall back the same way Contabo currently does.
- **Open a window when needed:** `scripts/terminal-open.sh <id>` as before, and add 1 line in the skill saying "CEO asks for a window on host X → run this on that host" [ambiguous: "ใน skill" does not specify which skill file].

## B. Watch (Haiku, 1 per host)
- **`tools/run_watch.py`:** Model-free API.
  - `status [--json] [--bad]`, `tail <task> [-n 15]`, `follow`
  - Statuses: running · quiet>15m · done · failed · dead (pid is gone but status is not finished)
  - `follow` notifies only when status changes, batched no more frequently than once every 2 minutes
  - The liveness reader lives in a single place in `lib`, shared with Steward [ambiguous: does not name the specific file under `lib/`]
  - Thresholds (quiet, close-after, batch) can be overridden via env for testing [ambiguous: exact environment variable names are not specified]
- **The watcher:**
  - Runs in tmux `runwatch-<host>` with `claude --model haiku --remote-control`
  - Does not load MCP (`--strict-mcp-config` with an empty config)
  - Allows only `Bash(bash scripts/hub/org-python.sh tools/run_watch.py *)`; denies everything else without prompting
  - System prompt is `roles/run_watch.md`
- **Skill `CTO_Procedure_RunWatch`:** A table of pattern → command → reply template no more than 3 lines:
  - "มีอะไรรันอยู่" (what is running) → `status`
  - "งาน X ถึงไหน" (how far along is task X) → `tail X`
  - "อะไรพัง" (what is broken) → `status --bad`
  - Event line → repeat back in 1 line
  - Other questions → "ตอบได้แค่สถานะงาน ถาม PH/CTO" (can only answer task status; ask PH/CTO)
- **Receiving events:** Use Monitor on `follow`; if unavailable, have the watchdog tick type into the pane per rule M10b; session name is updated by the rename service only when it changes.
- **Lifetime:**
  - watchdog tick starts the watcher when the host's first task starts
  - Closes 10 minutes after the last task finishes, and does not resume [ambiguous: "และไม่ resume" can mean "do not pass `--resume` when starting a watcher" or "do not resume the closed session"]
  - If it dies while tasks are still running, reopen it 1 time; if it dies again, write to `state/steward/<host>/open.md` [ambiguous: does not specify when the 1-retry counter resets]
- **Cost:** RAM around 250 MB per host (measured: Contabo 8 GB has 3.1 GB free, each claude is 210–416 MB); uses 0 token when idle.

---

## E2E Testing

Rules:
- Every item must have evidence (command output, sha, journal lines, or screenshot) recorded in the PH's `STATUS.md`.
- Output from tools that always return pass does not count as evidence.
- Every test costs $0: Codex and Haiku use subscription quota.
- Test in a worktree only; never run tests in the main checkout.

### N — Names
| # | Test | Method | Passes when |
|---|---|---|---|
| N1 | Name builders | pytest fixture covering every row of N.2 + length 31/32/33 examples + winbox | Exact string match character for character, body no more than 32, winbox is pure ASCII |
| N2 | Parser accepts both 2 formats | Feed all 11 rows of N.3 in both old and new name formats | `parse_short` gets the exact role/id for both, `rule_problem` reports the old format as "old shape" and the new format gets None |
| N3 | Sweep keeps topic | `rename_service` test with the 11 old names in N.3 | Queued names match the "New name" column [ambiguous: the 2 Mac rows in N.3 list two alternatives each]; already valid names are untouched; re-running does not re-queue |
| N4 | Does not type over draft | test: input box has characters / a turn is currently running | Does not type; retries on the next tick (rule M10b) |
| N5 | Live Contabo | Before: `live-sessions.sh --all` → deploy → wait 2 ticks → run again | 0 off-rule lines for Contabo; rename-service journal has typed=9 and no error |
| N6 | CEO visual check | CEO opens the mobile app and sends a screenshot of the list view | All new names visible, role#sid part readable on every row (use the screenshot to adjust `NAME_BODY_MAX` if needed) |
| N7 | Name at spawn | Delegate 1 probe task on Contabo + `session-rename.sh "test"` in PH's session | worker gets `🌐 Probe·S#xxx …` [ambiguous: N7 puts `Probe` in the `<Short>` role slot, whereas N.2 defines `<Short>` as the worker role short name] and PH gets `🌐 PH#7cf test` |
| N8 | Routing not broken | `send_to_cxo` to PH with new name; SendMessage with new name; `live-sessions.sh` | Actually delivered (logs wake succeeded); Console still sees the session (because tmux name did not change) |
| N9 | Self-healing | Manually rename 1 test session to violate the rule | Sweep fixes it back once; if it cannot fix it, reports 1 time and does not loop |
| N10 | Mac | After CEO installs M10c: Mac PH runs `live-sessions.sh --all` | 0 off-rule lines for Mac |

### A — Close windows on Mac
| # | Test | Method | Passes when |
|---|---|---|---|
| A1 | Read flag | pytest like `scripts/test_session_remote_control.py` | mac gets false, unset gets true; launcher has a detached path under a single condition [ambiguous: "ตามเงื่อนไขทางเดียว" can mean "via a single conditional branch" or "only takes the detached path under that condition"] |
| A2 | Live spawn on Mac (Mac PH) | `osascript -e 'tell app "iTerm2" to count windows'` before and after delegating a probe task on Mac | Window count unchanged, `tmux ls` sees `wd-<id>`, session appears in the app with the new name |
| A3 | Open on demand | `terminal-open.sh <id>` then close that window | Window count increases by 1 and session remains alive after closing the window |
| A4 | Contabo unaffected | Delegate a probe task on Contabo | Starts normally |

### B — Watch
| # | Test | Method | Passes when |
|---|---|---|---|
| B1 | Status from fixture | pytest feeding task row + pid + log mtime covering all 5 statuses; event batching | Correct status for every row, events within 120 s are combined into 1 batch, `--json` matches schema |
| B2 | Permission lock | Start watcher in test mode and type "ลบไฟล์ /tmp/x" (delete file /tmp/x) and "merge PR 1" | Replies with template; transcript has no tool calls other than `run_watch.py`; no permission dialog hanging in the pane |
| B3 | Live lifecycle on Contabo | override env: quiet 60 s, close-after 60 s<br>t0 no tasks → delegate P1 (Codex: sleep 300 then write ok) → P2 (prints nothing at all) → kill P2 → P1 finishes | t0 no tmux `runwatch-contabo`; P1 → tmux exists and app shows `Runs: 1🟢`; P2 quiet → 🟡 + line "เงียบ" (quiet); kill P2 → within 3 minutes shows 🔴 + "ตาย" (dead); P1 finishes → "เสร็จ" (done) and count decreases; after last task → ⚪ then tmux disappears within close-after |
| B4 | Q&A | During B3 type "มีอะไรรันอยู่" and "P2 ถึงไหน" (how far along is P2) | Gets a table of no more than 5 lines / gets status + 3 lines of log [ambiguous: Section B states replies are "no more than 3 lines" and `tail` defaults to `-n 15`, whereas B4 expects a table <= 5 lines / status + 3 log lines] |
| B5 | Watcher dies | Kill watcher while P1 is still running, then kill it a second time | Tick reopens it 1 time; on the 2nd kill it does not reopen and writes a line in `open.md` |
| B6 | Cost | `ps -o rss` of watcher; watcher transcript | RSS no more than 300 MB; uses 1 turn per 1 batch; with no events for 30 minutes, transcript is not written (0 turn) |
| B7 | Hub down | Run `run_watch.py` with a bad `ORG_DB_URL` (never stop the real hub) | Prints 1 line "hub unreachable"; no task is falsely reported as "ตาย" |
| B8 | CEO visual check | During B3 CEO opens the app | Sees `🌐 Watch#… Runs: 1🟢` change to 🟡/🔴 matching reality |

## Done when
- N1–N9 pass and `live-sessions.sh --all` has no off-rule lines for Contabo
- N10 passes after the CEO installs M10c
- A1–A4 pass
- B1–B8 pass
- Every PR: gitleaks passes and the CI fail-set is a subset of main's fail-set (this repo is public)
- PH collects the worker's Skill learning themselves

**15 Oct ~06:40 TH, CEO hand-renames override §N defaults:** existing names keep persona + lane and only gain the host emoji; new PH = `🌐 PH#<id3> (<LANE>) - <Project>`; plan shape only for Watch and workers; no 32-char cap on existing names. Told PH#7cf. [ambiguous: this post-hoc override contradicts §N.1–N.4 and tests N1–N3/N5 on persona removal, PH lane removal, and the 32-char cap for existing sessions]
