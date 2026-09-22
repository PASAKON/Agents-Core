## Section 48 — Disk and transcript hygiene on the Mac: alert first, move by hand (CEO 2026-09-05, owner CTO)

**Why this rule exists.** Between 2026-08-28 and 2026-09-05 the 8 GB Mac
kernel-panicked six mornings out of nine. Panic string: `watchdog timeout: no
checkins from watchdogd in 93 seconds`, with `8 swapfiles and LOW swap space`.
Three CTO sessions with 70-255 MB transcripts, plus Chrome, LINE and Dropbox,
filled RAM; swap grew until it hit the ~7 GB left on a 96 %-full disk; the box
stalled and the watchdog reset it. Every open session died. Claude Code
transcripts (`~/.claude/projects`) were 8.5 GB of that disk, and they only
grow: the file is append-only, and every `--resume` copies the whole parent
into a new file, so a long-lived CTO session leaves a trail of dead copies.

**Nothing deletes on its own. The machine alerts; a human archives.**

1. **The daily watch only reports.** `~/.claude/tools/prune_transcripts.py --notify`
   runs at 09:00 via launchd `com.gob.claude-prune-transcripts` and messages
   the CEO over SomPong when free space is under 20 GB, transcripts ready to
   archive reach 2 GB, Drive-gate folders reach 2 GB, or it is Monday. It
   never deletes.
2. **Archiving is a manual command, and it archives before it deletes.**
   `prune_transcripts.py --archive` tars each candidate into Google Drive
   (`ไดรฟ์ของฉัน/Claude-Transcripts/<project>/<uuid>.tar.gz`), verifies the
   archive, and only then removes the local copy. `--restore <uuid>` brings a
   session back. `--apply` (delete without archive) exists for emergencies and
   needs the CEO's word. Candidates: ordinary sessions after 30 days, sessions
   over 150 MB after 7 days, sessions whose worktree is gone after 7 days;
   under 20 GB free, 14 / 3 / 7 days. Live sessions, anything written in the
   last 24 h, `memory/` and the `keep` list are never candidates.
3. **Folders move to Drive only through the gate.** `drive-archive-gate.md`
   (next to the tool) names what may move, where it lands, and the
   copy-verify-delete order. An agent moves a folder only after the CEO says
   go on a specific alert. No automatic mover, ever.
4. **Weekly check, Monday /session-open.** Run `--report`, read
   `~/.claude/logs/prune-transcripts.log` for `FAIL`, confirm the job is loaded
   with `launchctl print gui/$(id -u)/com.gob.claude-prune-transcripts`, read
   `df -h /System/Volumes/Data`. Under 20 GB is a finding; under 10 GB is a
   same-day escalation.
5. **A live session over 200 MB gets closed and reopened, not resumed forever.**
   Finish the job, leave the hand-off in the tab title and LungNote, start a
   fresh session. A CEO-facing tab is closed only with the CEO's OK.
6. **Overnight: at most 3 live sessions and at least 20 GB free.** A session
   with a day of history costs about 1 GB of RAM here (measured 2026-09-05: a
   255 MB transcript resumed = 1.1 GB RSS). Below either number the panic above
   is the expected outcome.
7. **Worktrees die with their task.** When a task closes, remove its worktree
   (`python3 -m tools.worktree` from the Agents root). Before removing, check
   `git status --porcelain` is empty and the branch is pushed or merged; 41
   leftovers held 6.5 GB on 2026-09-05, most with unpushed commits.
8. **Never:** delete `~/.claude/projects/*/memory/`; delete a transcript that
   `~/.claude/sessions/*.json` lists as live; touch
   `~/Library/Application Support/CloudDocs/session/i` (the iCloud store for
   the CEO's Desktop, not a cache); run any cleanup on `~/Desktop`,
   `~/Downloads`, `~/Movies` or the Photos library while the CEO is
   consolidating phone data there.

**Evidence:** `/Library/Logs/DiagnosticReports/panic-full-2026-09-05-110452.0002.panic`,
`ResetCounter-2026-09-03-094156.diag` (`Boot faults: wdog`), `last reboot`.
Tool, policy and log paths above are the single source; do not copy the
numbers into other pages.
