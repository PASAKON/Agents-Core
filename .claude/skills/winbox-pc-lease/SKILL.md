---
name: winbox-pc-lease
description: "Borrow the winbox screen from the job that farms it all night, and give it back. winbox runs an unattended workload around the clock; any agent that needs the desktop takes priority over it, but must claim the screen instead of fighting it for the foreground. Trigger on /winbox-pc-lease and ALWAYS before the first click, keystroke, screenshot or app launch on winbox — and whenever someone says 'Cookie Run is running', 'มีบอทวิ่งอยู่', 'ยืมคอม', 'ขอใช้เครื่อง winbox', 'หยุดบอทก่อน', 'the bot is using the screen', 'something else is on that machine', or a screenshot of winbox shows a game or an app you did not start. Do NOT fire for headless winbox work (ssh, ffmpeg, rclone, git, file copies) — that never touches the screen and needs no lease."
created_by: agent
author: {role: cto, date: "2026-09-14"}
audience: [cto, cmo, cgo, cfo, browser_operator, developer]
---

# Borrowing the winbox screen

winbox has a resident tenant: an unattended workload that plays a game on that
desktop all night to collect training data. It is the lowest-priority thing on
the machine. **You outrank it. Always.** (CEO 2026-09-14.)

But it holds the foreground, and a foreground fight is how both jobs lose —
your click lands in its window, its screen-reader reads your window and stalls.
So there is a lease: you claim the screen, it steps aside, you work, you hand it
back.

**You do not need to know anything about that workload** — not what it does, not
how it runs, not how to restart it. Three commands is the whole interface.

---

## The whole thing

```bash
./scripts/pc-lease.sh status                                    # is the screen free?
./scripts/pc-lease.sh take --who "browser_operator: harvest 4 clips"
#   ... do your work on the screen ...
./scripts/pc-lease.sh give-back                                 # put it back
```

`take` parks the tenant and hands you the screen. `give-back` restarts it.
Default lease is **120 minutes**; `--minutes N` to change it, `extend --minutes N`
if you run long.

That is the whole skill. Everything below is why the details are the way they
are.

---

## When to invoke

- **Before the first click, keystroke, screenshot or app launch on winbox.**
  Before, not after you notice something else is up.
- A winbox screenshot shows a game, or any app you did not start.
- Someone says the bot / Cookie Run / "something else" is using that machine.
- You are writing new automation that will drive a winbox window.

## When NOT to invoke

- Headless winbox work: `ssh`, `ffmpeg`, `rclone`, `git`, `scp`, file copies,
  reading logs. None of it touches the screen; a lease would just block the
  tenant for nothing.
- Any machine that is not winbox.

---

## Workflow

1. **`status` first.** It tells you in plain words whether the screen is free,
   who holds it, and whether the tenant is running. Cheap, read-only, no side
   effects.
2. **`take --who "<your name>: <what for>"`.** `--who` is required and shows up
   in `status` for whoever looks next — make it a sentence a stranger can act
   on, not `agent1`. Keep it **ASCII**: it crosses a PowerShell argument layer
   that turns anything else into `?`, and `?` is a wildcard in PowerShell paths.
3. **Read what `take` printed.** It ends with `OK - the screen is yours until
   HH:MM`. If it prints `FAILED`, **do not touch the screen** — the tenant is
   still live and your clicks will collide with it.
4. **Do your work.** Drive the desktop through `winbox-desktop-gui` — session 1,
   screenshot before and after, all of it still applies. This skill only gets
   you the screen; it does not make clicking safe.
5. **`give-back` the moment you are done.** Not at the end of your session, not
   "later" — the moment the screen work is finished. Every minute you hold it is
   a minute of the night's data that does not exist.

---

## Rules

1. **HARD — never stop the tenant by hand, and never press ESC on that
   machine.** Use `take`. Nothing else.

   **Why hard:** ESC on that box writes a hold file that blocks *every* future
   launch until a **human** clears it — the app refuses to clear it on a
   script's say-so, by design. An agent that presses ESC does not borrow the
   machine for an hour, it takes the farm down for the night and only the CEO
   can bring it back. `take` uses the graceful stop, which leaves no hold, so
   the screen comes back on its own.

2. **`take` before you click, not after you notice.** The tenant reads the
   screen to decide what to press. A window of yours on top of it does not read
   as "someone else is working" — it reads as game state it cannot parse, and it
   stalls there *while still reporting itself alive*. You will not get an error;
   you will get a silently wasted night.

3. **`--who` is for the next agent, not for the log.** `status` shows your
   string to whoever wants the screen next. `browser_operator: harvest 4 clips,
   ~20 min` lets them decide to wait. `agent` tells them nothing and they will
   take the screen out from under you.

4. **Stopping costs at most one round — do not optimise it.** The default stop
   cuts within about two seconds, and the round in flight is written with
   `end=stop-file`, so downstream training drops it. Nothing is corrupted. There
   is a `--after-round` flag that waits for a clean boundary (up to 4 minutes)
   if you specifically want that round's data kept, but the default is correct
   almost every time. Do not make the tenant finish its round out of politeness
   — that is four minutes of you waiting to save one round of data that gets
   regenerated all night.

5. **Forgetting `give-back` is survivable; lying about it is not.** A watchdog
   on the box checks every 5 minutes and puts the tenant back the moment your
   lease expires, even if your session died mid-task. So the cost of forgetting
   is the unused remainder of your lease. But if `give-back` prints
   `COOKIE RUN DID NOT COME BACK`, say so to the CTO — do not report your task
   as clean. The farm is then idle until a person looks.

6. **A refused `take` means a peer is on the machine.** `status` names them and
   when they expire. Wait, or agree with them and use `--force`. `--force`
   without agreement is how two agents end up clicking in the same window.

---

## What this does NOT do

- **It does not make your clicks land.** Read `winbox-desktop-gui` before
  driving any window; on that machine `SetForegroundWindow` returns success and
  does nothing, and a screenshot is the only proof a click worked.
- **It does not know if the game is on a broken screen.** If the tenant comes
  back to a login prompt, an update dialog or a crash box, it cannot clear that
  itself. `give-back` reports what it verified; believe that line over your
  expectations.
- **It does not arbitrate between two non-tenant agents.** It shows you who
  holds the lease. Two peers sorting out who goes first is a conversation, not
  a lock.

---

## Under the hood (you do not need this, but it is here)

| Piece | Where |
|---|---|
| CLI (any machine with `ssh winbox`) | `scripts/pc-lease.sh` |
| The logic, on the box | `windows/pc_lease.py` → `C:\mooniex\pclease\pc_lease.py` |
| Lease file | `…\Documents\CookieRunScript\modelplay\PC_LEASE.json` |
| Audit log — every take, give-back and watchdog action | `…\modelplay\pc_lease.log` |
| Watchdog, every 5 min | scheduled task `MooniexPCLease` |

`pc-lease.sh` md5-compares and redeploys `pc_lease.py` on every call, so editing
the local copy is the whole deploy step.

The watchdog refuses to resume if a human ESC hold appeared while you held the
lease — a person's stop outranks an expiring lease. After 3 failed resume
attempts it stops retrying and writes a loud line to `pc_lease.log` rather than
looping forever against a broken screen.

**Verified 2026-09-14:** take / refuse-while-held / expiry / watchdog-reclaim /
logging, end to end. The stop-and-resume path was exercised against an idle
tenant; the first real stop of a *running* tenant is still unproven — if you are
the first to run it live, check `status` after `take` and tell the CTO what you
saw.

Related: [[winbox-desktop-gui]] — how to make a click on that machine real.
