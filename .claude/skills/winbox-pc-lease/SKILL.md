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

0. **The scripts enforce this now — you will be refused, not reminded.**
   `winbox-desktop.sh` and `winbox-line-send.sh` call `pc-lease.sh gate` before
   they touch anything, and exit 3 with instructions if the tenant is farming
   and you hold no lease. `WINBOX_NO_LEASE=1` overrides it for a genuine
   emergency.

   **Why it is a gate and not a paragraph:** a session drove this desktop for
   three hours with the tenant live underneath. Every command returned OK. The
   tenant's notifications were stacking up inside that session's own
   screenshots the whole time and it read them as background noise. This rule
   already existed, in writing, and it did not fire — because nothing made it.

   The gate is an ssh round trip — **~3-4 s per screen-touching call**, paid
   even while you hold a valid lease. Invisible on a single borrow; a 30-call
   browsing session pays about 2 minutes of it. That is deliberate: a cached
   answer that could ever wave someone through is worse than a slow correct
   one. If you are doing many calls and it hurts, say so and it can be revisited
   — the lease file already carries an expiry a caller could check locally.

   `gate` writes **nothing to stdout, ever** — it is a predicate, not a
   reporter. The verdict is the exit code (0 proceed, 3 refused); refusal text
   and holder notes both go to stderr. So a script may read gate's stdout
   safely on every path, and a human still sees everything on the terminal.

   When a lease **is** held, the gate passes but prints the holder and the
   minutes remaining to stderr. It cannot tell who is calling, so it will not
   refuse a peer on the holder's behalf — but you will never again click into
   someone else's session without having been told whose it is.

   `WINBOX_NO_LEASE=1` is read by the consumer scripts, **not** by
   `pc-lease.sh gate` itself — calling `gate` directly with the override set
   still refuses. That is deliberate: the gate is an oracle and must answer
   "is the screen free?" truthfully; the decision to proceed anyway belongs to
   the caller. So anything that asks `gate` gets the real answer, whatever the
   environment says.

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
- **It does not check for a foreign window at resume.** If a Windows toast or
  another app's window is sitting over the game when the tenant restarts, the
  tenant may stall on a screen it cannot parse — the exact failure the lease
  exists to prevent, arriving through the back door. Detecting this properly
  needs session-1 foreground inspection, which is not cheap enough to run on
  every resume, so it is **not** done. Leave the screen as you found it:
  close what you opened before `give-back`.

  One measurement, so you can calibrate rather than panic: on 2026-09-14 a
  borrower left Chrome open on an unrelated page and gave the screen back. The
  tenant resumed and played normally — a window *behind* the game is harmless.
  What is not harmless is a window *over* it, which is why toasts were worth
  killing and why "close what you opened" is still the instruction.
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

**Verified 2026-09-14, against a running tenant**, by an independent session
that borrowed the screen for 12 minutes of real browser work:

| | |
|---|---|
| `take` while farming | 5 s — tenant parked, emulator left up |
| `status` while held | correct on every field, holder and minutes shown |
| 12 min of real work | no foreground fight, every click landed |
| `give-back` | 3 s — `resume ok=True (farming)` |
| independent re-check | `Cookie Run: RUNNING`, no lease left behind |

Also verified: refuse-while-held, lease expiry, watchdog reclaim, the audit log,
and the gate refusing an unleased caller.

One thing this cost, so you know the price: the round that was in flight ended
`end=stop-file` after 259 s — 10,300 frames and 517 presses still recorded, and
the partial round dropped downstream. That is the intended trade, not a fault.

Related: [[winbox-desktop-gui]] — how to make a click on that machine real.
