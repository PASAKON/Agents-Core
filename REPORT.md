# REPORT task-109734f6

W3.5 spike: can a letter wake a Windows Terminal tab on winbox?

**Result: yes, in the desktop session, with a guard that had to be fixed twice by
measurement. One thing could not be measured (a genuine session-0 origin), so the design
does not depend on it: the CEO registers one persistent task once, and the remote side only
writes a file and runs `schtasks /run`. W3.3's `woke: false` can become `woke: <real>` for
C-level letters once that task exists and `node_dispatch` is wired (patch below, not applied).**

## Summary

Measured on winbox (`GoB`, desktop session id 2, Windows Terminal, own test window
`orgwake` with tabs `org-wake-test` = target and `org-wake-decoy`; a Notepad of my own for
the "different window has focus" cases). Target only ever my own tabs; the CTO's tab and the
window it sits in were read (title shape only) and never focused or typed into. Screen lease
taken and given back; my tabs and Notepad closed; the WT window is as I found it.

### Measurements (final code, 81 trials; raw rows in `results/final-code-81-trials.csv`)

| Method | Session | Attempts | Delivered | Seconds to marker | Notes |
|---|---|---|---|---|---|
| `appactivate` (a): AppActivate + SendKeys | desktop (1) | 10 | 10 | 1.6-1.8 | target tab already selected; incl. 5 with Notepad in front (raised WT first) |
| `appactivate`, focus on the **tab strip** | desktop (1) | 3 | **0, by design** | - | guard refused, **exit 3, nothing typed** |
| `uia` (b): UI Automation Select + SetFocus | desktop (1) | 20 | 20 | 1.8-1.95 | target selected / **background tab** / Notepad in front (x2 each 5) |
| `auto` (a then b) | desktop (1) | 15 | 15 | 1.6-2.0 | background tab, Notepad in front, window **verified minimized** (restored first) |
| any of the above, via one-shot **Interactive scheduled task** | desktop (1), task-launched | 20 | 20 | 2.9-4.2 | the spawn-worker / `_one_shot_task_script` pattern; task unregistered each time |
| `-Contains "-wake-test"` token, direct | desktop (1) | 10 | 10 | 1.65-1.98 | how a real `CTO #<sid> (<topic>)` tab must be addressed |
| `-Contains`, via one-shot task | desktop (1), task-launched | 3 | 3 | 3.8-4.2 | |
| production shape: hidden task -> `wake-request.ps1` -> `wake.ps1`, request file in / result file out | desktop (1), task-launched | 3 | 3 | 3.8-4.7 | harness `runner-task-test.ps1` (not in the 81) |
| **session-0 origin** (ssh -> interactive task) | **0-hop** | **0** | **not measured** | - | see "What I could not measure" |

Pass criterion (plan): marker at the prompt within 30 s, 5/5, in session 1: **met** (78/78 that
should deliver did, slowest 4.2 s; 3 that should refuse did). Zero leaks: 0 markers in the decoy
tab, 0 in Notepad, on every trial. Lowest free RAM seen: 3.1 GB at the start (limit 1 GB).

### Four findings, in the order they mattered

1. **The brief's guard passes while every key is lost.** Foreground window + exact title were
   both true, `SendKeys` ran, exit 0, and **0 of 5** markers arrived
   (`results/v1-guard-no-focus-check-5-trials.csv`). Reading my own tab's buffer through UIA
   `TextPattern` showed the prompt empty and `FocusedElement` = the tab item (`ListViewItem`),
   not the terminal (`TermControl`). Cause: UIA `Select()` on the already-selected tab moves
   keyboard focus onto the tab item; WT only refocuses the terminal on a real tab change. The
   first successful trial had been luck (a real tab switch). Fix: the guard also requires
   `FocusedElement.ClassName == 'TermControl'` in the foreground process, and the `uia` method
   selects only when needed and `SetFocus`es the terminal. Adverse-focus `appactivate` now
   refuses (3/3) instead of lying.
2. **A negative test found a wrong-target hole.** `-Contains` with a token matching two tabs of
   one window did not refuse: a window's title is only its selected tab, so counting windows
   cannot see a second match, and one marker was typed into the selected tab (mine).
   Fix: count matching **tabs** through UIA across all WT windows before any method runs; two
   or more -> exit 2. Applies to exact titles too. Re-tested: ambiguous / no match / short token /
   non-ASCII marker all refuse with nothing typed.
3. **Real tab titles are not knowable in advance.** The CTO's tab is `CTO #<sid> (<topic>)`
   (topic added and changed by Claude Code); a worker's begins with an animated glyph
   (non-ASCII). Exact-title match cannot find them. Hence `-Contains` with the stable token
   `#<sid>` (>= 6 chars, must match one tab). An ephemeral session started with
   `-TabTitle "CMO ephemeral"` has no sid in its title and cannot be woken.
4. **Raising the window is not the hard part.** In the 40 delivered trials that started with my
   Notepad in front, WT came to the front every time: 22 by `AppActivate(<the window's own title>)`,
   18 because UIA `Select()` on a background tab activated its window by itself.
   `SetForegroundWindow` + `AttachThreadInput` was never needed; it stays only as a fallback. No synthetic ALT is used (it is a key
   sent to whatever is in front before any guard).

### What I could not measure

- **A real session-0 origin.** There is no ssh-to-self without adding my key to
  `authorized_keys` (a persistent access change I did not make). Emulating session 0 with an
  S4U scheduled task failed: `Register-ScheduledTask : Access is denied` (0x80070005, S4U
  needs elevation). That is Windows, not the auto-mode classifier, and I did not elevate or
  work around it. What is established instead: (i) the one-shot Interactive task runs
  `wake.ps1` on the desktop from a task-launched process, 26/26 (20 + 3 token + 3 through the
  runner); (ii) this worker was launched on winbox by `windows/spawn-worker.ps1` (its
  `.launch-task-109734f6` folder), whose last step is the same one-shot Interactive task, so the
  hub already reaches the console session that way when it can.
  The classifier refusal in the brief did not occur for me (my own tool calls, not an ssh command).
- **A live Claude Code composer.** Only a `Read-Host` prompt in my own tab. `SendKeys` sends key
  events, not a paste, so Enter should submit; unproven (the tmux path has a rescue Enter for a
  bracketed-paste swallow, GH #70).
- **Whether a person is typing.** The woken tab is raised to the front; a draft in that composer
  would get the marker appended and submitted. See "Decision for the CEO".
- The guard's refuse-because-a-foreign-window-is-in-front branch never triggered: `AppActivate`
  always won the foreground. Its refusal (exit 3) was exercised by the tab-strip case and pinned
  statically.

## Decision

- **Method: `-Method auto`** (appactivate if the target tab is already selected, else UIA), always
  with the strengthened guard. In production **`-Contains "#<sid>"`**.
- **The CEO must run `windows\register-org-tasks.ps1` once**, at the desktop, from the checkout
  that runs `node_agent`. It registers `MooniexOrgWake` (Interactive, Limited, no trigger, 2 min).
  I did not register it (`Get-ScheduledTask MooniexOrgWake` -> not present). Reason it is
  needed: ssh cannot reach the desktop and registering a task from ssh was classifier-refused on
  2026-09-30; with the persistent task, ssh only writes `state\wake\requests\<id>.json` and runs
  `schtasks /run /tn MooniexOrgWake`.
- **W3.3's `woke: false` becomes `woke = agent_transport.wake_windows_tab(f"{role}-{sid}",
  from_role.upper())["woke"]`** for C-level letters on win32 (true only when `wake.ps1` exited 0,
  i.e. keys reached the verified tab; false, with a reason, when the task is not registered, the
  tab is not found, or the guard refused). Worker letters (`MAILBOX.md`) stay `woke: false`;
  workers read it before every tool call. **Not applied**: `tools/node_dispatch.py` was out of
  scope while W2.7 reviews it. The 3-line patch is in `docs/ops/windows-wake.md` ("Wiring").
- **Decision for the CEO before enabling the wiring:** waking raises a window on a desktop you
  use, and cannot tell if you are mid-sentence in that composer. If that is not acceptable, the
  next step is an idle gate (`GetLastInputInfo`; refuse with a new exit code when the last input
  was seconds ago). I did not build it: it is a policy choice, and unmeasured.

## Files Changed

- `windows/wake.ps1` (new) - the mechanism. ASCII, exit codes 0/2/3/4/64, guard before every send.
- `windows/wake-request.ps1` (new) - runner for the persistent task; trust boundary (one marker shape).
- `windows/register-org-tasks.ps1` (new) - CEO runs once; `-Remove` undoes it.
- `tools/agent_transport.py` - `wake_windows_tab()`, `_attempt_wake_windows()`, one marked additive block in `attempt_wake`.
- `tests/test_w35_wake.py` (new), `.gitignore` (`state/wake/`), `docs/ops/windows-wake.md` (new).
- `docs/reports/task-109734f6/` - this report, `harness/` (the scripts that produced the numbers), `results/` (raw CSVs).
- Not touched: `tools/node_dispatch.py`, hosts/projects yaml, venv, node.yaml.

## Commits

- `caacfe44` wake.ps1 first version
- `fe961da8` focus-in-terminal guard, unique-tab rule in every method, `-Contains`
- `0de22dc6` wake-request.ps1 + register-org-tasks.ps1
- `4e1e34ba` agent_transport win32 branch + tests
- (docs and report: see `git log`)

## Tests

- `tests/test_w35_wake.py`: **45 passed** (Windows, Python 3.11.9, pytest 9.1.1 installed in a
  scratch folder outside the repo). Covers: ASCII-only for the three scripts; foreground read
  before the text and again before Enter; no `SendKeys` outside `Send-Guarded`; focus check in the
  guard; exit 3 path; exactly-one-tab located before any raise/send; no `Register-ScheduledTask`
  and no `keybd_event`/ALT in wake.ps1; runner allow-lists (and that Python's own request passes
  them); register script has no trigger and a `-Remove`; nothing in Python registers the task;
  **POSIX pin**: `attempt_wake` minus the marked block and `_wake_tmux_send` hash identically to
  their pre-change source, plus behaviour tests on the tmux path; the win32 function with
  `subprocess.run` faked (request written, result read, refusals, unserved request withdrawn,
  hostile session names and labels write nothing).
- **Mutation check**: 10 deliberate breakages (guard removed, focus check dropped, extra unguarded
  SendKeys, task registration added, runner allow-list opened, POSIX log text / settle delay / platform
  test changed, label alphabet opened) - each caught by a test.
- Before/after on the tests my change could touch (`test_w33_node_dispatch_windows`,
  `test_node_dispatch`, `test_w33_spawn_worker_ps1`): **21 failed before, the same 21 after, 0 new**.
  Those 21 already fail on this Windows box (they simulate POSIX); the Mac is where they run.
  `tests/test_w31_windows_portability.py` fails at collection here (ImportError), also before my change.
- Not run: PowerShell has no unit runner here; `Parser.ParseFile` = 0 errors on all three `.ps1`.

## Issues / Blockers

- No blocker. The session-0 hop and a live Claude composer are unmeasured (above).
- My mistake, caught and repaired: during mutation testing I ran `git checkout -- tools/agent_transport.py`
  with that file's W3.5 edits still uncommitted, which reverted them. I re-applied them from the
  transcript, re-ran everything, committed, and redid the mutation checks with a clean tree.
- Side effect undone: an `ssh -o StrictHostKeyChecking=no localhost` probe added `localhost` to
  `~/.ssh/known_hosts`; removed with `ssh-keygen -R` (and the `.old`).
- Push: the shared DEV conventions say "never `git push`"; WORKER.md (the remote-worker contract in
  this worktree, for a spoke with no org MCP) says git is the only channel back and to push this task
  branch. I followed the more specific one and pushed ONLY `agent/developer-task-109734f6`, no force,
  no other ref. If that was wrong, the branch is safe to delete.
- Cookie Run was "HELD by a human ESC" before I took the lease and still is; `give-back` printed
  the standard "was not running when you took it" note. I did not touch it.

## Notes for Reviewer

- Read `wake.ps1`'s `Test-Foreground` and `Send-Guarded` first; everything else is plumbing.
- `windows\register-org-tasks.ps1` is for the CEO; nothing here runs it.
- The two guard fixes (findings 1 and 2) each came from a measurement, not from review; both are pinned in the tests.
- The harness in `docs/reports/task-109734f6/harness/` drives ONLY my own two tabs and one Notepad titled
  `org-wake-notepad`; it selects tabs by exact name. Re-running it elsewhere needs `launch-test-window.ps1` first.

SKILL-OVERRIDE: ALL_Rules_Winbox_PCLease :: use `./scripts/pc-lease.sh take|give-back` :: ran `windows/pc_lease.py` (the deployed copy) directly with the box's venv python :: the wrapper ssh's to `winbox` and this session already runs on winbox (no alias to itself); same code, same lease file, same output
SKILL-OVERRIDE: CTO_Knowledge_Winbox_DesktopGUI :: rule 1 "compare a screenshot before and after" :: verified by the target prompt's own timestamped log line plus a UIA TextPattern read of my own tab's buffer :: no screenshot tool in this session; a line written by the receiving prompt is a stronger proof than pixels, and both were compared against the decoy tab and Notepad for leaks

## Skill learning

- MISSING [CTO_Knowledge_Winbox_DesktopGUI §Rules] : foreground window + exact title verified is NOT proof keys will land in a Windows Terminal tab. After a UIA `SelectionItemPattern.Select()` on the already-selected tab (or a click on the tab strip) keyboard focus sits on the tab item and `SendKeys` is swallowed while the script exits 0. Check `AutomationElement.FocusedElement.ClassName -ceq 'TermControl'` in the foreground process; fix with `SetFocus()` on the visible `TermControl`. 5/5 "sent", 0/5 received · evidence: task-109734f6 `results/v1-guard-no-focus-check-5-trials.csv`, `windows/wake.ps1` Test-Foreground · fix: add as a numbered rule next to rule 2 (n=1, so a Field note first)
- MISSING [CTO_Knowledge_Winbox_DesktopGUI §Rules 2] : the escalation list omits what actually worked on this box: `WScript.Shell.AppActivate(<the window's own current title>)` raised Windows Terminal from Notepad 22/22 times (direct and from a task-launched process), and UIA `Select()` on a background tab activated its window itself in the other 18 of 40; `SetForegroundWindow` was never needed. Also: do not include a synthetic ALT step, it is a key sent to the window in front · evidence: `results/final-code-81-trials.csv` column `detail` (`via=AppActivate` / `via=already`)
- MISSING [CTO_Knowledge_Winbox_DesktopGUI §Rules 1] : a test harness's own setup lies the same way the automation does: "raise Notepad" with `SetForegroundWindow` silently failed on 9 of 10 trials and "minimize the window" left it foreground, so 15 early trials measured nothing while reporting success. Read the foreground / `IsIconic` back after setup and skip the trial if the precondition is false · evidence: `harness/trials.ps1` `Raise-Verified`, `invalid_setup` column in the development CSV
- MISSING [ALL_Rules_Winbox_PCLease §Workflow] : on winbox itself `scripts/pc-lease.sh` cannot run (no `ssh winbox` alias to itself, `PYEXE` is `C:\Users\UsEr\...`); run `C:\mooniex\pclease\pc_lease.py <take|give-back|status|extend>` with that venv python instead. And `give-back`'s screen-clear minimizes every visible window except the tenant's, but bails out when no BlueStacks window is visible; check that before giving back from inside a WT tab of your own · evidence: this task (n=1)
- WRONG [no owner - docs/design/org-mesh.md C4 and plan §W3.5] : the plan assumed a session's tab can be found by its exact title. Live tabs are `CTO #<sid> (<topic>)` and worker tabs start with an animated glyph; only a token (`#<sid>`) is stable · evidence: UIA tab-name shapes read on winbox 2026-09-30, `windows/cxo-claude.ps1:203-207` sets `CLAUDE_CODE_DISABLE_TERMINAL_TITLE`, but the CTO tab I read carries a topic suffix (launcher not checked) · fix: address tabs by `#<sid>` with `-Contains`
- COSTLY [no owner] : a fresh winbox worktree has no git identity, so the first `git commit` failed with "Author identity unknown"; `git config` in a worktree writes the SHARED `.git/config`, so I passed `-c user.name/-c user.email` per command · evidence: this task, 22:3x · prevented by: spawn-worker.ps1 exporting `GIT_AUTHOR_*`/`GIT_COMMITTER_*` for the worker process
- COSTLY [no owner] : mutation-testing with `git checkout -- <file>` on an uncommitted file reverts the work under test (lost the `agent_transport.py` edits, re-applied from the transcript) · prevented by: commit before any mutation run; restore only files that are clean
- COSTLY [no owner] : the PowerShell safety hook blocks `Remove-Item` on a path built from a variable with "blocked ... system path '/'" - misleading, and it consumed a retry; the file did not exist anyway · prevented by: `Test-Path` first, or literal paths
