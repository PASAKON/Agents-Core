# Escalation watch (M11)

CEO order 2026-10-14 ~11:45 TH: "ทำไมเวลา PH ติดปัญหาถึงไม่มาถาม C level · และทำไม C level ถึงไม่มาถามที่ run
เป็นกฎหลัก · ตอนนี้งานไม่เดินแล้ว session หยุดและตายไปช้า". The IRON rule says what a session does; this checks it.

`tools/escalation_watch.py` (dry run) / `--nudge` (sends), every 5 min on Contabo
(`deploy/systemd/escalation-watch.{service,timer}`, installed by a Run card).

| Finding | When | Who hears | How |
|---|---|---|---|
| `waiting` | a C-level or PH pane shows a choice prompt (permission prompt or on-screen question, the app's ✋; the record still says `idle`) | the COO, and a PH's owner (`.spawned_by`). **Never the waiting session**: it cannot read a letter while the prompt holds it, and a wake would press Enter on that prompt | at once (`blocker`) |
| `blocker` | a PH's `blocker` letter to its C-level, 15 min old, no letter back to the PH, no question card from that C-level since, and the PH still live | that C-level + COO | at once (`blocker`) |
| `idle` | a C-level or PH idle 30 min or more (`statusUpdatedAt`) | the COO only | digest (`fyi`) |
| `host` | a host's live-sessions publisher stale, for up to 24 h (longer = retired: a `note`, not a finding) | COO + every live C-level on this host | digest (`fyi`) |

A finding is an **episode**: it starts the first run it is seen and ends the first run it is gone
(`state/escalation_watch.json`). An at-once finding gets one letter and at most one reminder 60 min later,
then nothing until the episode ends. A digest finding gets one line per episode; each recipient gets at most
one digest letter per 2 h (the COO's rule, 14 Oct: no-action letters as `fyi`, batched; blocker and ask at once).

A wake (the usual tmux nudge) follows only an at-once letter, and only when the recipient's own screen is
`prompt_ready` (empty input box, no turn running, no prompt waiting): the rename service's test. A screen that
cannot be read gets no wake. A digest never wakes anyone. Letters carry box ids and numbers only, never a
session's display name or text a session wrote; a `from` or `to` that is not a box id is skipped.

The state file and the letter log are read only when root (or the reader) owns them, nobody else can write
them and they have one link (`state/` is group-writable by `secretary`). A state time later than now (the clock
stepped back) is clamped to now and its counters stay, so a step back never resets a rate limit.

**The state must be saveable, or nothing is sent.** Every `--nudge` run (also one with no findings, so ended
episodes are pruned and a due digest flushes) saves the state before its first letter. If that save fails (for
example a group member pre-created `state/escalation_watch.json` as a directory) or the file is over 1 MB (it is
never parsed from its tail), the run prints `note     state file … cannot be saved …`, sends nothing and exits 1,
so systemd shows the unit failed. Remove the planted path to recover. The saved state is bounded: the newest 500
episodes and 200 digest boxes, never more than the 1 MB the next run will read.

Sources: hub `live_sessions`/`live_hosts`; this host's session records; `tmux capture-pane`; the Run Inbox question
list (`tools/ask_run`); `state/reports/letters-meta.jsonl`, which `lib/mailbox.send` appends for every letter
(sent_at, from box, to box, kind; never the body; kind read off the body's `blocker · …` while the envelope flag is off,
rotated at 5 MB). An unreadable source is printed as a `note`, never guessed.

Limits:
- The letter log `state/reports/letters-meta.jsonl` is created `0600` by its first writer, and
  `state/reports` is root-only. A non-root sender (the COO, user `sompong`) is not logged, so a COO-owned PH's
  reply to a blocker is invisible here: its blocker gets its one letter and one reminder, then stops.
- A reply by SendMessage never touches `lib/mailbox`, so it is invisible too; the same cap bounds it.
- Rotation (5 MB → `.1`) can race between two writers and lose the old `.1`. Blocker findings look back only
  over what is left.
- Pane and idle checks see Contabo only (the Mac and winbox have no pane the watch can read; a dead Mac shows up
as `host`). Nothing restarts a session: the nudge goes to people who can.
