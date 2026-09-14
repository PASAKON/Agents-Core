---
name: winbox-desktop-gui
description: "Driving a real desktop app (LINE, Resolve, Chrome) on the winbox Windows machine from a C-level or operator session: how to reach session 1, how to prove a click landed, and the four measured ways this silently reports success while doing nothing. Trigger on /winbox-desktop-gui and proactively whenever a task will click, type, paste or screenshot a GUI on winbox — sending a LINE message, attaching a file in a desktop app, driving Resolve or Blender's UI, automating any window with SendKeys or mouse_event, or when someone says 'ส่ง LINE ให้', 'กดปุ่มใน', 'สั่งเครื่อง Windows', 'automate the desktop', 'ทำไมมันไม่กด', 'it says sent but nothing happened'. Do NOT fire for headless work on winbox (SSH, ffmpeg, rclone, codex) which never touches a window."
created_by: agent
author: {role: cto, date: "2026-09-12"}
audience: [cto, browser_operator]
---

# Driving a desktop GUI on winbox

Everything here was measured on 2026-09-12 while sending one LINE message. It
took **three false "sent" reports** and four separate bugs to land it. None of
that came from asking an agent what it saw — it came from a timestamped log and
a screenshot after every step. That is the method, and it is the first rule.

Tool-level rules for specific sites live elsewhere (`higgsfield-unlimited-gen`,
`google-flow-ops`). This is the layer under all of them: **what it takes for a
click on that machine to be real.**

---

## What it does

Windows refuses most of what this kind of automation asks for, and **returns
success anyway**. `SetForegroundWindow` returns without error and does nothing.
`SendKeys` delivers to whatever has focus, which may be another app. A tray-
minimised window reports no handle at all. So a script that checks its own
inputs — "is the clipboard right?" — reports success while the screen never
changed. This skill is the set of checks that make the claim true, plus the
four specific traps on this machine.

## When to invoke

- Anything that will **click, type, paste, or screenshot a window** on winbox.
- Sending a LINE message or attaching a file from the desktop LINE client.
- Driving Resolve, Blender, or Chrome's real UI (not headless).
- A script using `SendKeys`, `mouse_event`, `SetForegroundWindow`, `schtasks /IT`.
- Someone reports **"it said it worked but nothing happened."**
- Before writing any new automation against a Windows app.

## When NOT to invoke

- Headless work on winbox — SSH commands, `ffmpeg`, `rclone`, `codex`, file
  copies. Those never touch a window and none of this applies.
- Browser work driven through a real automation API (CDP/Playwright), where the
  tool reports element state rather than guessing from pixels. Use
  `browser-operator` for that.

---

## Before any of this: claim the screen

winbox has a resident tenant — an unattended workload that holds the foreground
all night. Taking the foreground away from it without saying so is how it stalls
silently while still reporting itself alive.

```bash
./scripts/pc-lease.sh status     # free?
./scripts/pc-lease.sh take --who "<you>: <what for>"
#   ... everything below only applies once this says the screen is yours ...
./scripts/pc-lease.sh give-back
```

Read **`winbox-pc-lease`** for the rest. You outrank the tenant; you still have
to claim the screen rather than fight it for the foreground. Headless work (ssh,
ffmpeg, rclone) needs no lease.

## The two facts about this machine

**1 · SSH lands in session 0, which has no desktop.** From there
`MainWindowHandle` is `0` for every process and the screen reports 1024x768
instead of the real 1920x1080. Every piece of geometry, every click, every
screenshot must run **inside session 1**. The way in is a one-shot interactive
scheduled task (`New-ScheduledTaskPrincipal -LogonType Interactive`), proven
2026-09-11 (`docs/runbooks/winbox-recovery.md`).

**2 · Somebody must be logged in at the console.** No console session, no
window, no GUI work — and no error that says so. `scripts/winbox-drill.sh`
checks this by reading `(Get-CimInstance Win32_ComputerSystem).UserName`.

The working reference implementation of both is `scripts/winbox-line-send.sh`
plus `windows/line-send.ps1`. Read those before writing a new one.

---

## Workflow

1. **Confirm a console session exists.** No user at the console → stop and say
   so. Nothing below can work.
2. **Write the action as a script, not as a sequence of agent decisions.** A
   narrow named script is the only shape that can be pre-authorised in
   settings, and the only shape that can be replayed without a model.
3. **Take a screenshot first and read it yourself.** Do not reason about what
   is probably on screen. On this machine a Windows Terminal has been sitting
   on top of LINE more than once.
4. **Raise the target window and prove it came up** (see rule 2).
5. **Click the specific control before typing.** Raising a window does not move
   keyboard focus into its text box.
6. **Do the action, then compare the screen before and after.** If the pixels
   in the region that should have changed did not change, the action failed —
   report FAIL, do not continue to the irreversible step.
7. **Read the screenshot yourself before reporting success.** A pixel-diff
   proves *something* changed; only your eyes prove it was the right thing. A
   modal covering the transcript produced a 6,800-pixel diff and a confident
   "OK sent" while nothing had been sent.

**Refusal condition:** if the target window will not come to the foreground,
stop. Do not click. A click aimed at a window that is not on top lands in
whatever is — on 2026-09-12 that typed a person's name into another agent's
prompt.

---

## Rules

1. **HARD — Never report an action as done on the strength of what you sent
   into it. Verify on the screen.** Checking the clipboard, the return code, or
   the tool's own "OK" proves only that you asked. Compare a screenshot of the
   affected region before and after, and look at the result.

   **Why hard:** irreversible, and it produced three wrong reports to the CEO in
   one afternoon. A message to a real person cannot be unsent, and "I already
   told him it was sent" is not recoverable by trying again. Both of the first
   two failures were *reported as successes* — the defect is not that the click
   missed, it is that nothing was watching.

2. **`SetForegroundWindow` lies, and the fix is to compare the owning
   process.** It returns without error and does nothing whenever Windows
   refuses a foreground steal from a background process — which is the normal
   case, because the task starts while something else owns the screen. Escalate
   through `SetForegroundWindow` → synthetic `ALT` → `SwitchToThisWindow` →
   minimise+restore, and after each attempt check:

   ```powershell
   $fg = [Win]::GetForegroundWindow()
   $fgPid = 0; [void][Win]::GetWindowThreadProcessId($fg, [ref] $fgPid)
   if ($fgPid -eq $proc.Id) { <# now it is really on top #> }
   ```

   Compare the **PID, not the window handle**. An app's foreground window is
   often a child of the one `MainWindowHandle` reports, so a handle-equality
   test says "not focused" while the app is plainly in front — measured, after
   a screenshot showed LINE on top and the check still failed.

3. **Your own launcher is a suspect.** A scheduled task that runs `cmd.exe` to
   get a `>` redirect creates a console window, and that console took the
   foreground away from LINE about six seconds into every run. Have the script
   write its own output file and launch PowerShell directly with
   `-WindowStyle Hidden`. The log line that found this is worth copying as a
   habit:

   ```
   15:08:42  focused on attempt 0 (fg pid 7448)
   15:08:49  not focused; foreground pid 21244, LINE is 7448
   ```

   Two lines, a timestamp and a PID. No agent's recollection would have found it.

4. **Never send a "reset the state" keystroke you have not tested against that
   specific app.** `{ESC}` was added to clear a stray dialog; in LINE it is
   hide-to-tray, so the script sent the app off screen and then clicked at
   coordinates where it used to be — every single run. A tray-minimised app
   reports `MainWindowHandle = 0`, so the symptom reads as "the app is gone",
   not "I hid it". Relaunching the same executable restores the existing
   instance rather than starting a second one.

5. **Aim at a menu item by offset from the click that opened the menu, never by
   a window ratio.** A context menu is drawn relative to its own click, so an
   offset cannot drift; a percentage of window size can. In LINE's chat-row
   menu **"Delete" sits 54px below "Pin chat"** — a few percent of drift is the
   difference between pinning a chat and deleting it. Measure the offset off a
   real screenshot (open the menu, photograph it, stop) before clicking one.

6. **Non-ASCII dies in a PowerShell argument, and the wreckage is a wildcard.**
   Thai in a `-Argument` string arrives as `????`
   (`docs/reports/FINDING-winbox-ascii-only.md`). Worse, `?` is a single-char
   wildcard in PowerShell paths — a mangled filename still *resolved*, to
   whatever happened to match. Ship text as a file and checksum both sides;
   keep filenames ASCII when they must travel as arguments.

7. **Choosing a human recipient stays with a human.** A script may type into a
   chat that is already open, and may search for one by name — but the run that
   selects a target ends with a screenshot of the header, and a person reads it
   before anything is sent. The guarantee is not "the script cannot pick wrong";
   it is "picking wrong is visible before anything leaves."

8. Reserve the irreversible keystroke until after the screenshot. Paste, then
   photograph, *then* press Enter. The cost is two seconds and it converts every
   wrong-window mistake from a message someone received into a picture you look
   at.

---

## How to write the NEXT skill like this one

The CEO asked whether a skill like this should be written by interviewing the
workers who hit the problem, or by reading their session logs. Reading the logs
is better than interviewing — but both lose to a third thing.

| Source | What you actually get |
|---|---|
| Ask the agent what went wrong | What it *believed*. It reported a permission refusal correctly and knew none of the four real bugs. |
| Read its session transcript | Raw, but still a record kept by the process that made the mistake — it logs what it thought to log. |
| **Run it yourself, instrumented** | Timestamps, PIDs, pixel counts. Mechanical facts nobody had to notice in order to record. |

So: **instrument first, and the skill writes itself from the evidence.** Every
rule above is a line from a log or a number off a screenshot. None is a
recollection.

And the corollary, which is the reason this file is short on prose:

> A rule that depends on someone remembering it will be skipped. Put it in the
> tool. Rule 1 is not enforced by this document — it is enforced by
> `line-send.ps1` exiting non-zero when the pixels did not move, which is what
> actually stopped the third wrong report.

Related: [[move-remembered-rules-into-the-linter]] · [[check-the-listener-not-just-the-sender]]

---

## Output format

Report a GUI action like this — what was verified, and by what:

```
LINE → Mark Thanabodee
  chat opened      header reads "Mark Thanabodee"        shot-open.png
  message sent     md5 1B3AE2… identical both machines   shot-msg-sent.png
  4 photos sent    chatDiff 6819 / 7088 / 6628 / 6779    shot-attach-*-sent.png
  read by them     yes, at 15:11
FAILED: none
```

If any step could not be verified on screen, say so in that line and do not
summarise the run as a success.
