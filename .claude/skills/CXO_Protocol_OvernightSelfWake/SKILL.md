---
name: CXO_Protocol_OvernightSelfWake
kind: protocol
description: "PROTOCOL — Keep a C-level session working and waking itself while the CEO sleeps: decide alone what is yours, wake on events plus a heartbeat with a backup, and spend the fewest tokens per wake. Trigger on /CXO_Protocol_OvernightSelfWake and on \"ปลุกตัวเอง\", \"อย่าให้ตัวเองหลับ\", \"ขอตัวไปนอน\", \"ระหว่าง CEO หลับ\", \"wake yourself\", \"keep working overnight\". Do NOT use for watching a rented GPU (IRON-RULES §46) or for a browser loop (IRON-RULES §42: delegate to browser_operator)."
owner: CTO
created_by: agent
author: {role: cto, date: "2026-10-07"}
improved_by: []
aka: []
audience: [cxo]
---

# How a C-level keeps working while the CEO sleeps

Trigger: the CEO says he is going to sleep or will be away for hours, and this session still has work (its own tasks,
running workers, a peer it helps). Also when he asks the session to wake itself.

The CEO, 2026-10-07 01:2x (session cto-369faf85), verbatim fragments: "ฉันขอตัวไปนอนก่อน … ช่วยงาน f39c… ให้เสร็จนะมีอะไรที่คุณทำให้ได้ในระกว่างงานของเขาช่วยทันทีเลยไม่ต้องรอให้เขาบอกคุณคิดเองได้" ·
"ช่วยปลุกตัวเอง ด้วย อย่าให้ตัวเองหลับ อย่างน้อย ทุกๆ 1-2 ชั่วโมง หรือแล้วแต่ว่างานนั้นใช่เวลารอนานแค่ไหน ปลุกตามเห็นสมควรได้เลย" ·
"และเรื่อง Token ใช้ประหยัดๆ นะ" · "อะไรที่ตัดสินใจเองได้ ทำให้ก่อนได้ ห้ามรอจนกว่า CEO ตื่นโดนไม่ทำอะไรแล้วนิ่งหายไปเฉยๆ" ·
"และมีแผนสำรองเสมอ ในการปลุก".

## What went wrong on past nights (the evidence this protocol is built from)

| Date | What happened | Cost | Step that prevents it |
|---|---|---|---|
| 2026-08-28 to 09-05 | The Mac force-restarted overnight 6 times: kernel watchdog panic from swap exhaustion, 3+ CTO sessions on the 8 GB M1 | every session died; resumed by hand next morning | 1 (memory), 2, 7 |
| 2026-08-25 | The stall watchdog killed a healthy browser operator that was silent for 94 min while waiting on renders | its report was lost | 3 (worker heartbeat) |
| 2026-08-30 | `pmset` sleep 1, worker caffeinate only 300 s: the Mac slept mid-render and the tmux server died | ~75 min idle until the next wake noticed | 1 (caffeinate) |
| 2026-09-05 | The 8 GB memory watchdog killed two `run_in_background` jobs, one of them a sleeping watcher | the watcher never fired | 3 (never one layer) |
| 2026-09-06 | A "blocked" worker report was accepted without a probe | render queue idle 01:00 to 07:00 | 6 (test a blocker) |
| 2026-09-07 | A worker's "holding for CTO" line reached only the log; nothing woke the CTO | 35 min held | 3, 5 |
| 2026-09-09 | A Monitor's parser crashed on every poll and emitted nothing; the CEO had been told "the monitor will chain it" | box idle 2 h | 3 (first event before trust) |
| 2026-09-23 | On battery the Mac ran Maintenance Sleep cycles; a 30-min Monitor got 0 events | 30 min of nothing | 1 (power) |
| 2026-10-01 | A refill loop exited "ALL DONE" and the queue sat empty | 21:42 to 23:11 | 5 (tick reads the queue, not the loop) |
| 2026-10-03 | A hung renderer timed out every prep | 00:29 to 08:58, 9 h | 5 (tick sees a stall) |
| 2026-10-07 | At the CEO's goodnight the check found the Mac on battery at 4%, ~8 min left | caught: push sent, CEO plugged in | 1 |

Sources: memories `feedback_mac_sleeps_mid_render`, `mac_watchdog_panic_and_cto_resume` (legacy),
`feedback_watchdog_reaps_polling_operator`, `feedback_overnight_queue_token_economy`, `feedback_monitor_silence_is_not_success`,
`reference_champa_higgsfield_night_run_traps`; the last row is this protocol's first run.

## Steps

### 1. Before the CEO leaves: the 2-minute check, while he can still act

```bash
pmset -g batt | sed -n 2p      # must read "charging" or AC Power
pmset -g | grep '^ sleep'      # this Mac: sleep 1; it needs a long caffeinate preventer
memory_pressure | tail -1      # free %; low free + 3 or more sessions = the overnight panic
```

- **Battery:** discharging → push-notify the CEO now, one line. A dead battery ends every session.
- **Sleep:** hold it off for the whole night from THIS session, never from a worker (a worker's hold dies with it):
  `nohup caffeinate -i -m -s -t <seconds until morning> >/dev/null 2>&1 &`. `-s` holds only on AC. The workers' own
  `caffeinate -i -t 300` lasts 5 minutes.
- **Memory:** more than 3 Claude sessions or a heavy Chrome on the 8 GB Mac → tell the CEO which ones could close.
  Never close another session yourself.
- **CEO-only items** (a sign-in, a money OK, a typed approval sentence): ask NOW, all in one message. After he
  sleeps they wait until morning.

### 2. Write the night plan: one file, 15 lines or fewer

Put it on disk in Agents-Core, `state/night/<short-sid>.md` (it survives a reboot; the scratchpad under /tmp may not). It holds:

- what runs: task ids, agent or worker, expected end;
- the wake layers armed (step 3) and the next wake time;
- what each event triggers (agent done → review, gates, push, send the sha);
- what waits for the CEO, as one-line questions;
- the resume line if the session dies: `bash scripts/spawn-cto.sh --id <short> --resume <uuid>`
  (`state/locks/cto-<short>.uuid` holds the UUID; without `--id` the resumed session gets a new short id).

### 3. Arm the wakes: always two layers, from different mechanisms

| Layer | Mechanism | Wakes when | Dies when | Idle cost |
|---|---|---|---|---|
| Event (primary) | background `Agent` completion, `run_in_background` job exit, a peer's `SendMessage`, a `Monitor` line | the thing happens | the session ends; the memory watchdog kills background Bash | 0 |
| Heartbeat | `CronCreate` one-shot ~50 min ahead, re-armed by every tick | the time comes and the REPL is idle | the session ends; a tick forgets to re-arm | one turn per fire |
| Backup | `CronCreate` recurring every 2 h at an off-minute; it re-arms the heartbeat when none is pending | the time comes | the session ends; auto-expires after 7 days | one short turn per fire |
| Inside /loop only | `ScheduleWakeup` (60 to 3600 s) | only when the CEO started `/loop` without an interval | the loop stops | one turn |
| Off-session | none: Contabo has no route to the Mac, so nothing outside can wake a dead Mac session | n/a | n/a | n/a |

- Never rely on one layer (2026-09-05, 2026-09-09).
- A Monitor counts only after its first event has arrived. Put its script in a file, `bash -n` it, run it once in the
  foreground. A Monitor expires after 30 min and every re-arm is a turn: for one outcome prefer `run_in_background`
  with `until <done marker>; do sleep 60; done`.
- Wait on the producer's own done marker, never on a file count or on a file existing.
- Workers you spawn: a heartbeat line every ~3 min during long waits, and each value reported the moment it exists.
- `CronCreate` jobs live only in this session and fire only while the REPL is idle (tool doc, 2026-10-07). A session
  that is busy for 2 h skips them, which is fine: it is awake.
- When the session itself dies, step 2's file and the morning resume are the last resort.

### 4. Pick the interval from what you wait for

| Waiting for | Wake on |
|---|---|
| A job with a known end (an agent, a render of ~30 to 90 min, CI of ~8 min) | its event, plus one check near the expected end |
| External state with no event | one check at the expected change time, not a 5-min poll |
| Only a peer's reply | the heartbeat |
| Nothing: the charter is done | stop the heartbeat, write the morning report, tab 💤 |

**The heartbeat is ~50 min, not 2 h.** This is token math, an estimate from Anthropic's published prompt-cache prices,
not measured on our bill. This session's prompt cache lives 1 hour (ScheduleWakeup tool doc, 2026-10-07). A wake
inside the hour reads the whole context at the cache-read price, about 0.1x input. A wake after the hour writes the
whole context again, about 2x input for the 1-hour cache. So with a large context two warm wakes cost less than one
cold one. The CEO's "1-2 ชั่วโมง" is the upper bound, not the target. Do not wake more often than every ~10 min unless a
job ends sooner. In usage overage the cache drops to 5 min and the math flips: then fewer wakes are cheaper.

### 5. The cheap tick

- **One command:** a script file, read-only, 10 lines of output or fewer, one line per thing that can change: workers
  and agents, task rows, the peer's branch head, power, caffeinate, memory.
- **Nothing changed:** one line of reply, no tab change, no notification, re-arm, end.
- **Something changed:** do the next step at once (review, gates, push, the next job), then one line.
- **Never on a tick:** screenshots; large files or transcripts (an Agent's `.output` file is its whole JSONL); a full
  test suite "to check"; re-reading a skill already loaded; re-measuring a number already recorded.
- **See a stall, not only a finish:** compare the age of the last activity with the expected time (2026-10-03: a hung
  renderer went unseen for 9 h).

```bash
#!/bin/bash
# night tick: read-only, one short line per thing that can change
echo "time $(TZ=Asia/Bangkok date +%H:%M) | $(pmset -g batt | sed -n 2p | cut -f2) | caffeinate $(pgrep -f 'caffeinate -i -m -s' >/dev/null && echo up || echo DOWN)"
git -C <repo> fetch -q origin; echo "peer head $(git -C <repo> log -1 --format='%h %s' origin/<branch> | cut -c1-70)"
bash /Users/gob/MoonieXHQ/Agents/Core/scripts/hub/org-python.sh -c "from lib import db; print(' | '.join(f\"{t} {(db.get_task(t) or {}).get('status')}\" for t in (<ids>)))"
```

### 6. Decide alone, prepare, or leave, but never go silent

| Do it now, alone | Prepare for the morning, do not do | Never |
|---|---|---|
| Work inside the charter and your lane | Money: the exact $ and the CEO's OK (`ALL_Rules_Approvals`) | Take a CEO-only decision because he is asleep |
| Review a finished worker, run the gates, fix a red test | Secrets, privilege, deleting login state | Retry an action the classifier refused |
| Push your own branch; merge where you are the merger | Public posts, outward messages in the CEO's name | Act in another session's lane (relay only) |
| Respawn or cancel your own stuck worker | Restarting a shared service, deleting data | Push-notify for routine progress |
| Take the next unblocked item; send the peer its sha | Anything the lane owner merges | |
| Pick a default the spec allows, and say which | | |
| Write Field notes and memory; park off-topic items to LungNote | | |

- **Blocked:** test the blocker once (a reload, a fresh probe) before accepting it (2026-09-06). Still blocked: write a
  one-screen card for the morning report (options, recommendation, cost), then move to the next unblocked item.
- Ask a question once. A repeated question opens turns for nothing.
- Push-notify the sleeping CEO only for what he must act on before morning, or a risk to data or money (the battery, a
  paid pod he approved that is burning money). Everything else waits for the report.
- Help the peer without being asked: with each delivery offer the next item in your lane; when idle, look in the
  peer's plan for unowned work in your lane.

### 7. Morning

- First message, 12 lines or fewer: done (shas), running, the cards waiting for the CEO, how many ticks fired and what
  they caught, anything that died.
- `CronDelete` the heartbeat and the backup, close the night plan file, set the tab.
- If the session died overnight: read `state/night/<sid>.md`, resume with its line, and check every external job
  against its own state (a render keeps running server-side; a pushed branch is on origin).

## Who is involved

- **The C-level session:** owns every wake, the caffeinate hold and the night plan.
- **Workers** (in-session Agents, org workers): report by event, heartbeat in long waits.
- **Peer C-levels:** their SendMessage wakes this session. Send them shas, not questions.
- **The CEO:** only before he sleeps (power, approvals) and in the morning (the cards).

## What it never does

- Never arms only one wake layer.
- Never runs a browser loop in a C-level tab (IRON-RULES §42).
- Never writes a long reply to a quiet tick.
- Never trusts a monitor before its first event, or says "it will chain" before it has.
- Never decides money, secrets, privilege, publication or another session's lane for the sleeping CEO.

## Field notes

- 2026-10-07 [MISSING] §1 — first run: at the CEO's goodnight (01:2x) the check found the Mac on battery at 4%, ~8 min left; a push went out and the CEO plugged in by 01:27 · evidence: session cto-369faf85 · status: pending
- 2026-10-07 [MISSING] §4 — the 50-min heartbeat comes from published cache prices, not a measurement; compare the morning usage with the night's tick count · evidence: session cto-369faf85 · status: pending
- 2026-10-09 [COSTLY] §night state — the overnight tools (pyround.py, provmerge3.py, ring plans) and every capture since 10-08 18:27 lived only in the session scratchpad under /private/tmp; a Mac reboot at ~01:29 wiped it with an uncommitted merge inside. Only the transcript still holds the scripts. Rsync the scratchpad (minus worktrees) to Assets at each heartbeat, and commit or push a merge before a long gate run (n=1) · evidence: cto-f39cb080 twin park file ~/.claude/session-data/2026-10-09-f39cb080-twin-session.tmp; same reboot, cto-369faf85 lost its two worktrees and its provenance merge helper (rebuilt as merge_prov.py, copy in Assets scratch-cto-369faf85-2026-10-08) while its pushed branches and the Assets package survived · status: pending
- 2026-10-09 [MISSING] §3 — a backup layer that restarts the primary (and the primary restarting the backup) through `pgrep … || nohup … &` is a fork bomb, not a safety net: when the Mac neared `kern.maxprocperuid` (1333), `pgrep` itself could not fork, returned non-zero, was read as "dead", and every tick started one more copy — 220 + 440 copies, 1,483 processes, "fork: Resource temporarily unavailable" in every session on the Mac for ~5 h, until the CEO rebooted the Mac (~01:29). The classifier refused the session's own `pkill` ("Interfere With Workloads") until the CEO typed "go ahead". What replaced it: ONE supervisor per job family (`lb_supervisor.sh`), held by `mkdir <lock>` + its pid inside, children tracked by pid file + `kill -0` (bash builtins, nothing forks), nothing restarts the supervisor but a human or the 2-hour check; the two old scripts are stubs that refuse to run. Rule candidate for §3: a liveness check must not fork, and no two loops may restart each other. Run every new loop once in the foreground and read its first log lines before leaving it · evidence: session cto-671f688f 2026-10-08 20:18 → 10-09 01:43, memory `reference_mutual_pgrep_restart_fork_bomb.md`, `lb_out/queue_guard.log` ("restarted keepalive" ×hundreds) · status: pending
- 2026-10-09 [MISSING] §3 — the reboot also ended every session cron: the restored session (fork d5663133) had an empty CronList, so the morning wake would never have fired. On the first turn after a restore, run CronList and re-arm the wakes (n=1) · evidence: cto-369faf85 01:58 CronList empty, cron 520cec4c re-armed · status: pending
