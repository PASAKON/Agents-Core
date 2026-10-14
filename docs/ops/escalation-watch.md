# Escalation watch (M11)

CEO order 2026-10-14 ~11:45 TH: "ทำไมเวลา PH ติดปัญหาถึงไม่มาถาม C level · และทำไม C level ถึงไม่มาถามที่ run
เป็นกฎหลัก · ตอนนี้งานไม่เดินแล้ว session หยุดและตายไปช้า". The IRON rule says what a session does; this checks it.

`tools/escalation_watch.py` (dry run) / `--nudge` (sends), every 5 min on Contabo
(`deploy/systemd/escalation-watch.{service,timer}`, installed by a Run card).

| Finding | When | Nudged |
|---|---|---|
| `waiting` | a C-level or PH pane shows a choice prompt (permission prompt or on-screen question, the app's ✋; the record still says `idle`) | its C-level (a PH's owner from `.spawned_by`) + COO |
| `idle` | a C-level or PH idle 30 min or more (`statusUpdatedAt`) | same |
| `blocker` | a PH's `blocker` letter to its C-level, 15 min old, no letter back to the PH and no question card from that C-level since | that C-level + COO |
| `host` | a host's live-sessions publisher is stale | COO + every live C-level on this host |

A nudge is one mailbox letter (`blocker · urgent · escalation watch: …`, from `watchdog-escalation`) plus the usual
wake, again at most every 30 min per finding (`state/escalation_watch.json`).

Sources: hub `live_sessions`/`live_hosts`; this host's session records; `tmux capture-pane`; the Run Inbox question
list (`tools/ask_run`); `state/reports/letters-meta.jsonl`, which `lib/mailbox.send` appends for every letter
(sent_at, from box, to box, kind; never the body; kind read off the body's `blocker · …` while the envelope flag is off,
rotated at 5 MB). An unreadable source is printed as a `note`, never guessed.

Limits: pane and idle checks see Contabo only (the Mac and winbox have no pane the watch can read; a dead Mac shows up
as `host`). Nothing restarts a session: the nudge goes to people who can.
