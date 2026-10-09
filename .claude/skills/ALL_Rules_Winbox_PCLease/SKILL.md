---
name: ALL_Rules_Winbox_PCLease
kind: rules
owner: CTO
aka: [winbox-pc-lease]
description: "RULES — Borrow the winbox screen from the job that farms it all night, and give it back. winbox runs an unattended workload around the clock; any agent that needs the desktop takes priority over it, but must claim the screen instead of fighting it for the foreground. Trigger on /ALL_Rules_Winbox_PCLease and ALWAYS before the first click, keystroke, screenshot or app launch on winbox — and whenever someone says 'Cookie Run is running', 'มีบอทวิ่งอยู่', 'ยืมคอม', 'ขอใช้เครื่อง winbox', 'หยุดบอทก่อน', 'the bot is using the screen', 'something else is on that machine', 'PC: CEO', 'CEO hold', 'ใช้คอม', 'เลิกใช้คอม', or a screenshot of winbox shows a game or an app you did not start. Do NOT fire for headless winbox work (ssh, ffmpeg, rclone, git, file copies) — that never touches the screen and needs no lease."
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

If `status` opens with `PC: CEO`, **the CEO is at that PC. Hands off** until he
presses his release button — see the next section. Nothing below gets past it.

That is the whole skill. Everything below is why the details are the way they
are.

---

## The CEO's hold — above every lease

The CEO has two buttons on the winbox desktop: **ใช้คอม** ("use PC") and
**เลิกใช้คอม** ("done"). Twice (2026-10-07, 2026-10-09) an agent found the lease
FREE and relaunched an app over the game he was playing. A FREE lease is not a
free screen; his button is the only thing that says he is there.

While his hold is on:

- `status` opens with `PC: CEO - the CEO is using this PC since HH:MM`.
- `take` and `extend` refuse, **exit 2, `--force` included**. `gate` and
  `ceo-check` refuse, **exit 3**, stdout still empty.
- `WINBOX_NO_LEASE=1` does **not** get past it: under that override
  `winbox-desktop.sh` and `winbox-line-send.sh` still run `pc-lease.sh
  ceo-check`. On the box, `desktop.ps1`, `line-send.ps1` and
  `cookierun_probe.py` check the hold file themselves and refuse.
- The watchdog resumes nothing and minimises nothing. If Cookie Run is running
  under the hold anyway, it stops it (`bot_stop`, never ESC) within 5 minutes.
- `give-back` releases your lease but clears no window and restarts nothing; the
  farm comes back when he presses เลิกใช้คอม.

**HARD — his press does not stop a run you already started.** It marks your lease
as bumped, and your next `take`, `extend` or `gate` is refused. Nothing reaches a
script that took the lease once and keeps clicking. So a runner that holds a lease
across stages (join, tour, capture, ...) **calls `pc-lease.sh gate --as "<who>"`
before every stage and stops on exit 3.** Without that, he presses his button and
watches your script carry on over his game.

**HARD — never run `ceo-on` / `ceo-off` yourself.** They are his buttons. Only if
he asked for it in words: `PC_LEASE_CEO_SAID="<his words>" ./scripts/pc-lease.sh
ceo-off`. Without the words it is refused, on the Mac and on the box, and every
run that cites his words is logged with them.

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
4. **Do your work.** Drive the desktop through `CTO_Knowledge_Winbox_DesktopGUI` — session 1,
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
   and you hold no lease, or the CEO holds the PC. `WINBOX_NO_LEASE=1` overrides
   the farm check for a genuine emergency — never the CEO's hold (the scripts
   then run `pc-lease.sh ceo-check`, which refuses only on his hold).

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

- **It does not make your clicks land.** Read `CTO_Knowledge_Winbox_DesktopGUI` before
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
| The CEO's hold — exists = held, unreadable = held | `…\modelplay\CEO_HOLD.json` |
| "Cookie Run is being put back" — revive stands down while fresh | `…\modelplay\FARM_RESUMING.json` |
| His two buttons | `windows/desktop/` → desktop, by `install_ceo_buttons.sh` |

`pc-lease.sh` redeploys `pc_lease.py` only when your copy's `LEASE_VERSION` is
**higher** than the box's (`scripts/lib/winbox_deploy.sh`), and keeps the box
copy read-only. An edit to `pc_lease.py` must bump `LEASE_VERSION` or it stays
on your machine — the wrapper says so on stderr. A checkout *behind* the box
runs the box's newer copy and is told to `git pull`; it can no longer put an
older file back. (Before 2026-10-09 this was an md5 compare, and any stale
worktree's first call replaced the hold-aware file with one that knew nothing
of the CEO's hold.) `cookierun_health.py` works the same way with
`HEALTH_VERSION`, `desktop.ps1` with `DESKTOP_PS1_VERSION` and `line-send.ps1`
with `LINE_SEND_PS1_VERSION`. `cookierun_revive.py` (`REVIVE_VERSION`) is deployed
only by `install_ceo_buttons.sh`, which installs only a HEAD that is on
origin/main, deploys and verifies every one of these first, and puts the buttons
on the desktop last.

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

Related: [[CTO_Knowledge_Winbox_DesktopGUI]] — how to make a click on that machine real.

## Field notes

- 2026-10-09 [MISSING] §The CEO's hold — the skill knew no CEO hold: his buttons, what refuses under it, that WINBOX_NO_LEASE no longer bypasses it, and that a bumped run is not stopped (runners call gate --as before every stage) · evidence: branch ceo-pc-hold 947800b2 + 4aa46d7a, tests/test_pc_lease_ceo_hold.py · status: promoted
- 2026-10-09 [WRONG] §Under the hood — "pc-lease.sh md5-compares and redeploys on every call": any stale checkout put an older pc_lease.py back on the box, one blind to the hold; replaced by a forward-only versioned deploy onto a read-only box copy · evidence: review of ceo-pc-hold 2026-10-09, 1224af88 · status: promoted
