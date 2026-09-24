# Multi-host workers — spawn on Mac, Windows or Contabo by capability

Status: **DRAFT for CEO decision** · CTO · 2026-09-07
Supersedes nothing; extends ADR 2026-07-12 (org runtime → Contabo, Phase A done).

## 1. Problem

Every worker the org spawns runs on the Mac. That is not a policy, it is three
pieces of code:

| Where the Mac is baked in | File | What it assumes |
|---|---|---|
| Spawn = open an iTerm tab via AppleScript | `tools/delegate.py` `_spawn_iterm_tab` | macOS + iTerm on this machine |
| Worktree = `Agents/worktrees/<...>` from `projects.yaml` `path:` | `tools/worktree.py` | absolute `/Users/gob/...` paths |
| Worker reaches the org via stdio MCP | `config/worker.mcp.json` | `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` on the same box as `state/tasks.db` |

Consequences seen today: four `browser_operator`s in one Chrome (limit is two)
→ tab group destroyed mid-submit, a Google sign-out, two teaser runs blocked.
Meanwhile Windows and Contabo sat idle. The Mac also sleeps, which kills every
worker on it (memory: *Mac sleeps mid-render*).

## 2. What each machine can actually do (measured 2026-09-07)

| | **Mac** | **winbox** (Win11, Tailscale 100.123.83.75) | **Contabo** (mooniex-vps) |
|---|---|---|---|
| Reachable from Mac | — | ✅ `ssh winbox` | ✅ `ssh mooniex-vps` |
| Reaches the Mac | — | not needed | ❌ closed by design (`mac_agent` dials out) |
| Claude Code | ✅ | ✅ 2.1.251, logged in (`.claude` exists) | ✅ 2.1.226, `~/.claude` present |
| Org runtime code | ✅ canonical | ❌ (only `win-cto.ps1`, scp'd) | ✅ `/opt/mooniex-agents` + venv 3.12 |
| `state/tasks.db` | ✅ live | ❌ | ⚠️ 0 rows — empty copy |
| tmux | ✅ | ❌ (Windows) | ✅ |
| Terminal launcher | iTerm | `wt.exe` (Windows Terminal) | tmux |
| **Chrome + logged-in web sessions** | ✅ org Chrome (Higgsfield, Flow, Grok…) | ❌ **no Chrome, no Edge installed** | ❌ headless, cannot hold a login |
| macOS computer-use | ✅ | ❌ | ❌ |
| Blender / bpy | via hfbridge → winbox | ✅ native | ❌ |
| Git clones | all projects | `Projects/{mooniex-webapp, mooniex-option, mooniex-line-automation, LLMs, LungNote}` (real clones, HTTPS remote) + **`mooniex-autopull`** scheduled pull | `/root/projects/{claudeflow, option, alphatrader, line-automation, line-poster}` |
| Git push identity | ✅ | ❓ `id_ed25519` present, not yet tested against GitHub | ❌ no `user.name`, no `gh auth` |
| 24/7 | ❌ sleeps | ⚠️ sleep-on-AC disabled | ✅ |
| Free RAM | ~8 GB total, tight | ~4 GB → **one worker at a time** | 6.4 GB |
| Services already running | CTO/CXO sessions, mac_agent | — | secretary (SomPong), waker, console, drive-broker, line-queue (systemd) |

## 3. Design — hub and spokes, git is the truck

```
                 ┌──────────────── HUB ────────────────┐
                 │ tasks.db  +  CTO session  +  router  │   (Mac today; Contabo later, ADR Phase D)
                 └──────┬───────────────┬───────────────┘
        ssh (push)      │               │  ssh (push)
                        ▼               ▼
              ┌─── SPOKE: winbox ───┐   ┌─── SPOKE: contabo ───┐   ┌─── SPOKE: mac ───┐
              │ launcher.ps1        │   │ launcher.sh + tmux   │   │ delegate.py (as-is)│
              │ worktree from git   │   │ worktree from git    │   │                    │
              │ TASK.md             │   │ TASK.md              │   │                    │
              │ claude --chrome ... │   │ claude ...           │   │                    │
              └─────────┬───────────┘   └──────────┬───────────┘   └─────────┬──────────┘
                        │  git push agent/<role>-<task>  (+ REPORT.md)       │
                        ▼                           ▼                       ▼
                 ┌────────────────────────── GitHub (origin) ──────────────────────────┐
                 └──────────────────────────────┬───────────────────────────────────────┘
                                                │  hub polls: branch appeared → status=review
                                                ▼
                                       CTO reviews diff, merge_task (unchanged)
```

**Five rules that make it work**

1. **A task says what it needs; a host says what it provides.**
   `needs: [chrome]`, `needs: [blender]`, `needs: [24x7]`, or nothing.
   Router: pick a host whose `provides ⊇ needs`, then the least loaded, and
   **default to Contabo** when a task needs nothing special — it is the only box
   that never sleeps and its idle capacity is free. Chrome work goes to the
   least-loaded Chrome host, **never more than two operators per Chrome**.

2. **Git is the only cross-machine channel for work.** Worktree in from git,
   branch + `REPORT.md` out via git push. No stdio MCP over SSH, no shared
   filesystem, no new servers. The hub notices a pushed branch and flips the
   task to `review`. `merge_task` is untouched. This is also why the
   `send_to_worker` body bug (#136) cannot recur across machines: a CTO
   instruction to a remote worker is a file committed on its branch, which is
   exactly how the teaser tasks were steered today.

3. **The hub pushes to spokes; spokes never reach into the hub.** Mac→winbox and
   Mac→Contabo SSH both work now. Contabo→Mac stays closed — that asymmetry is
   the existing security design (`runners/mac_agent.py`), and this keeps it.
   Blockers travel as GitHub issues, as they already do.

4. **Per-host paths, one registry.** `projects.yaml` gains
   `paths: {mac: …, winbox: …, contabo: …}`; today's `path:` becomes the Mac
   entry. A host without a path for a project simply cannot be routed that
   project.

5. **The launcher replicates `worker_init`, it does not reinvent it.**
   `runners/worker_init.py` already computes each role's `--allowed-tools`,
   `--chrome`, model, effort and MCP flags. The remote launcher calls the same
   function's output (rendered into the SSH command) so a worker on winbox is
   the same worker it would be on the Mac.

**What this deliberately does not do**
- No browser on Contabo. It cannot hold a logged-in session and has no display.
  Contabo = coding, API, 24/7 pollers, RunPod drivers, cron.
- No `tasks.db` on Windows. Windows is a spoke only.
- No stdio MCP tunnelled over SSH. It would work until the first dropped
  connection, then fail in the way #136 fails.

## 4. Phases

### Phase 1 — the Mac ↔ Windows pipe (this week)
Goal: one `browser_operator` task delegated from the Mac runs on winbox, in
winbox's Chrome, and lands on GitHub as a branch. Mac Chrome untouched.

| # | Step | Who | Est. |
|---|---|---|---|
| 1a | Install Chrome + the Claude-in-Chrome extension; sign in to Google (AI Plus account) and Higgsfield in that Chrome | **CEO, at the machine** | 15 min |
| 1b | Confirm/put a GitHub deploy key on winbox with push rights to the org repos (the existing `id_ed25519` may already be it — test `ssh -T git@github.com`) | CTO | 10 min |
| 1c | `windows/spawn-worker.ps1`: clone/fetch project, `git worktree add`, write `TASK.md`, launch `claude` detached via `Start-Process` with the role flags from `worker_init.worker_tool_grants`, write a pid file | developer | 1 task |
| 1d | `tools/delegate.py`: `host` parameter; for `winbox` run `ssh winbox powershell -File spawn-worker.ps1 …` instead of the AppleScript path; `tasks` gains a `host` column | developer | same task |
| 1e | `runners/branch_poller.py` on the hub: `git ls-remote` every 60 s for `agent/*` branches, flip matching tasks to `review`, pull `REPORT.md` into `report` | developer | same task |
| 1f | End-to-end proof: re-run the Flow teaser (task-65c37d19's brief) with `host=winbox` | CTO | — |

Acceptance: (1) the teaser task reports through GitHub, not through the Mac's
MCP; (2) `ps` on the Mac shows zero new `claude` processes during the run;
(3) the `google-flow-ops` skill gains a Windows timing row.

### Phase 2 — the Contabo spoke for coding / API / 24×7
`scripts/spawn-worker.sh` (bash + tmux — the same shape as today's tmux
backend), git identity + `gh` token on the box (this is ADR Phase C, still
open), `host=contabo` in `delegate.py`. Proof: a `developer` task on
`mooniex-claudeflow` runs there and is merged from the Mac.
Default routing for capability-less tasks moves to Contabo the day this lands.

### Phase 3 — the router
`needs` on `create_task`, `provides` per host in a new `config/hosts.yaml`,
load = live `claude` count per host, a `hosts` panel in the dashboard, and the
per-host stall Monitor the CTO already runs by hand.

### Phase 4 — move the hub to Contabo
ADR 2026-07-12 Phases D–F. After this the Mac is just another spoke and can
sleep. Nothing in Phases 1–3 has to change for it — that is the point of
routing by host name instead of by "here".

## 5. Cost and risk

- **Infra cost: $0.** Tailscale, GitHub and all three machines already exist.
- **winbox RAM ~4 GB** → hard cap one worker at a time there. The router
  enforces it.
- **Windows has no tmux** → detached `Start-Process` + pid file; the hub's
  liveness Monitor reads the pid over SSH instead of the process table.
- **Claude-in-Chrome on Windows is unverified.** 1a is the test. If it fails,
  Phase 1 still delivers the pipe (non-browser roles) and browser work stays on
  the Mac with the two-operator cap enforced.
- **Sign-outs happen mid-session** (seen twice today). A second Chrome halves
  the blast radius; it does not remove the failure mode.

## 5a. Teardown invariant (task-92118d4e, CEO rule 2026-09-07; extended
task-59780ac3, 2026-09-08)

*Terminal status ⇒ no process, no tmux, no tab, no claimed Chrome tab, on
any host; the watchdog sweep (`runners/watchdog.py:sweep_terminal_surfaces()`)
is the backstop, `close_dev`/`merge_task` are the method — Chrome tabs
claimed via `scripts/browser/tab_registry.py` are torn down the same way
(ADDENDUM 1).*

**Extended invariant (task-59780ac3):** a remote (winbox/contabo) worker is
closed when its task reaches a terminal status **OR** when it has published
REPORT.md and gone quiet — whichever comes first. The two triggers:

1. **Terminal status** — `sweep_terminal_surfaces()` now runs a remote pass
   too (before task-59780ac3 it skipped every non-mac host outright): for
   each terminal-status remote task past `REAP_GRACE_S`, it calls
   `tools/worker_reap.py:close_remote()` directly. There is no local
   pid/tmux/tab table for this box to probe a winbox/contabo surface with,
   so close_remote's own re-read-and-refuse-unless-terminal check
   (ADDENDUM 2) is the safety gate instead of a liveness check.
2. **REPORT.md pushed and quiet** — the gap that actually bit (measured
   2026-09-08: task-5d0bd2fa's winbox claude.exe + terminal window sat alive
   5h54m after finishing, until the CTO killed it by hand). `review` is a
   live-and-waiting status on the Mac (a C-level may still be deciding) and
   is deliberately excluded from the terminal set — but a remote worker in
   `review` has already pushed its entire output to git and holds nothing
   back. `runners/branch_poller.py`, right after flipping a task to
   `review`, closes that worker's surface via `close_remote(...,
   allow_review=True)` — a narrow, explicit opt-in only it passes — but only
   once ALL of: the host is a remote spoke, the re-read status is still
   `review`, REPORT.md is still present on the branch, and the branch's
   newest commit is at least `REVIEW_CLOSE_QUIET_S` (5 min) old (proof the
   worker has stopped pushing, not mid-push).

**Dead-worker detection (task-59780ac3):** a remote `in_progress` task whose
worker died before pushing anything is also no longer invisible forever.
`runners/watchdog.py`'s stall loop now asks the box itself over SSH (reusing
`runners/branch_poller.py:remote_pid_alive`) once a remote task has been
silent past `STALL_AFTER_S`: a definite **False** (the box answered, the pid
is gone) marks it `stalled` and files the same GH issue the local path
files; **None** (the SSH call itself failed — host unreachable) is treated
as unknown and never flips the task, exactly like the local path already
guards silence from becoming a false "dead" verdict on a network hiccup.

**Nothing on Windows runs on a timer of its own.** The task DB lives only on
the Mac and winbox cannot read it — there is no watchdog, no cron, no
scheduled task on Windows. All three mechanisms above are one Mac-side
watchdog/poller reaching out over SSH; that stays the whole design.

## 6. Decisions needed from the CEO

1. Approve a deploy key with **push** rights on winbox (and on Contabo in Phase 2).
2. Do step 1a yourself — Chrome + extension + logins on winbox — nobody else can.
3. Hub stays on the Mac through Phases 1–3, moves to Contabo in Phase 4. OK?

## 7. Phase 1 — status (developer, task-d1d6b2ef, 2026-09-07)

**Shipped:**

- `config/hosts.yaml` + `lib/config.py` `hosts()`/`host(name)`/
  `project_path_for_host(project, host)` — the last raises a clear error
  for an unrouted project/host pair instead of guessing.
- `config/projects.yaml` `paths:` filled for `mooniex-agents` (winbox +
  contabo), `mooniex-webapp` (winbox), `mooniex-claudeflow` (contabo). The
  other four Contabo repos named in the brief (`mooniex-option`,
  `mooniex-alphatrader`, `mooniex-line-automation`, `mooniex-line-poster`)
  are not registered `projects.yaml` entries at all yet — adding them
  needs a real `remote:` URL per repo, which this task did not fabricate.
  Flagged for whoever picks up Phase 2.
- `lib/db.py` `tasks.host` column (NULL = mac) + `create_task(host=...)`.
- `lib/config.py` `worker_session_name(host, role, task_id, title)` —
  `<MACHINE> <ROLE> #<id8> (<title>)` (ADDENDUM 1, CEO decision: every
  session is addressed from the Claude app, on any device, so the machine
  has to be in the name itself).
- `tools/delegate.py` `_spawn_remote()`: dispatches to
  `windows/spawn-worker.ps1` over SSH when a task's resolved host isn't
  `mac` (explicit `delegate_task(host=...)` arg > `tasks.host` > `'mac'`).
  Renders the remote argv from `worker_tool_grants()` (never a second
  hand-maintained tool list) plus `--remote-control`, deploys
  `spawn-worker.ps1` + the role docs to the box automatically (sha256
  compare, only copies what changed), and supports `dry_run=True` to print
  the exact ssh command without running it.
- `windows/spawn-worker.ps1`: clones/fetches the project, adds a worktree
  on the task branch, writes `TASK.md`/`WORKER.md`, launches
  `claude.exe --remote-control` inside a **Windows Terminal tab**
  (`wt.exe -w 0 nt`) rather than a detached process — Remote Control needs
  an interactive console, and a detached process would never show up in
  the CEO's Claude app. No `-NoExit`: the tab's lifetime equals
  claude.exe's, so a hub-side `taskkill /PID <pid> /T /F` closes the
  window too (CEO rule: ending a worker closes its window, never just the
  process). Falls back to `ssh.github.com:443` when `github.com:22` is
  blocked (measured true from this box on 2026-09-07) and reports which
  route worked. Never prompts.
- `roles/_worker_remote.md`: the remote-worker contract — no org MCP, no
  `submit_report`/`dev_message`; report by pushing `REPORT.md`/`BLOCKER.md`
  and `git push`.
- `runners/branch_poller.py`: polls every 60s for in-progress remote
  tasks; a pushed branch with `REPORT.md` → `review`; with `BLOCKER.md` →
  a `gh issue create` + `blocked_human` (closest existing status to
  "blocked" — `lib/db.py` has no bare `blocked`); no branch and a dead
  remote pid → `failed`. `--once` for a single tick (tests).
- `tools/delegate.py` `_spawn_iterm_tab`: tmux-attach branch now ends
  `; exit $?` (ADDENDUM 2) so a dead tmux session doesn't leave an open
  bare-shell tab, matching the non-tmux branch's existing GH #27 fix.
- `tests/test_multihost.py`: 25 tests — remote argv rendering (chrome per
  role, `--allowed-tools` last), hosts/paths resolution + the not-routable
  error, `worker_session_name` shape, `.worker.json` parsing, and
  `branch_poller` state transitions against a real local git repo standing
  in for GitHub (a bare repo on disk, no real network) — report/blocker/
  dead-pid/unreachable-host/still-working/skip-mac all covered.

**Deploy (one-line, manual/emergency — normally automatic on first
`delegate_task(host='winbox')`):**

```
scp windows/spawn-worker.ps1 winbox:'C:\Users\UsEr\mooniex\spawn-worker.ps1'
```

**Not done / open:**

- `lib/org_tools_registry.py`'s `host` param on `create_task`/
  `delegate_task` (registry half of deliverable 3) — that file was outside
  this task's declared `touches`; self_repo_guard refused the edit and a
  touches-expansion request was sent to the CTO mid-task. `runners/
  cto_mcp_server.py`'s side (in touches) is done; until the registry side
  lands, an MCP-level `host=` argument is silently dropped by
  `_prepare()`'s param filter — `delegate_task` still works correctly when
  called with `host=` from Python directly (as the acceptance run below
  does), just not yet through the MCP tool surface.
- Live end-to-end acceptance against the real winbox box — see the
  developer's task report for what was actually run (dry-run vs. real).

## 8. Visibility: what a remote worker is doing (GH #150-153, task-3009a00d)

**Iteration 1 mistake, reverted (2026-09-18 CTO review):** an early fix for
"the hub is blind while a remote worker is stuck" (GH #152) piped
`claude.exe`'s stdout+stderr through `| Tee-Object -FilePath worker.log`.
Claude Code is an Ink TUI; a non-TTY stdout makes it silently drop into
`--print` mode and exit within seconds ("Input must be provided either
through stdin or as a prompt argument when using --print"), even with a
prompt already given positionally. That line would have killed **every**
winbox spawn. Never pipe `claude.exe`'s own stdout/stderr in the launcher.

**What ships instead:** Claude Code already writes a full JSONL transcript
per session, with no launcher change needed, under

```
<home>\.claude\projects\<cwd-slug>\<session-uuid>.jsonl
```

`<cwd-slug>` is the worktree's absolute path with every `\`, `/`, `:`, `_`
replaced 1:1 with `-` — measured on winbox 2026-09-18:
`C:\Users\UsEr\mooniex\worktrees\mooniex-agents__browser_operator__task-424077a4`
became `C--Users-UsEr-mooniex-worktrees-mooniex-agents--browser-operator--task-424077a4`
(`ssh winbox dir C:\Users\UsEr\.claude\projects`). `<home>` is resolved live
via `$env:USERPROFILE` over ssh, not hardcoded, so this doesn't assume any
particular Windows username.

`tools/remote_worker_log.py` reads it:

```
python -m tools.remote_worker_log <task-id> [-n 30] [--raw]
```

Resolves host + worktree from `tasks.db` via the same slug rule as
`runners.watchdog._remote_worktree_dir` (not duplicated), finds the newest
`.jsonl` in that directory over one ssh round trip, and prints the last N
entries as `<HH:MM:SS> <type> <summary>` (`assistant-text` /
`tool_use(<tool>, <input preview>)` / `tool_result(ok|error, <preview>)` /
`user`), masking anything secret-shaped
(`(sk|ghp|eyJ)[A-Za-z0-9_-]{8,}` → `***`). `--raw` dumps the raw tail
instead. Exit codes are never "probably": `0` printed something, `1` usage
error (bad task id, or the task's host has no ssh alias — e.g. `mac`,
where the transcript is already local), `2` ssh reached the box but no
transcript exists yet, `3` ssh itself failed.

Windows-only today (mirrors `tools/send_to_worker._send_remote`'s existing
`os != "windows"` guard) — a Contabo/Linux worker's home directory isn't
derivable the same way (`agents_root` there is `/opt/mooniex-agents`, not
under a user home) and wasn't measured, so it raises a clear error instead
of guessing at a path.

The remote PowerShell is sent via `-EncodedCommand` (base64 of UTF-16LE),
not `-Command` with the raw script text. Measured live on winbox
2026-09-18: `ssh` joins its remaining argv into ONE string that the box's
outer shell re-parses before `powershell.exe` ever sees it, so a raw script
containing `|` (needed for `Get-ChildItem ... | Sort-Object ... |
Select-Object -First 1`) had its pipe characters consumed by that outer
shell first — `Sort-Object`/`Select-Object` got split off as their own
"commands" and failed with `'Sort-Object' is not recognized as an internal
or external command`. Base64 has no shell-special characters at all, so
nothing downstream can misparse it. First real live run (against
task-424077a4's actual transcript) also confirmed `capture_output=True`
keeps PowerShell's `#< CLIXML` progress noise ("Preparing modules for first
use") isolated to stderr — stdout is clean JSONL.

**Also fixed the same review round:** `HEARTBEAT` and `MAILBOX.md` (GH #150,
#152 — the worker's liveness/mailbox files) must never be committed.
`windows/spawn-worker.ps1` now appends both names to the clone's shared
`info/exclude` (not the project's own `.gitignore`, which must stay generic
across any repo cloned on the box) right after `worktree add`, once per
clone. `REPORT.md`/`BLOCKER.md` are unaffected — they ARE the hub's channel
and are meant to be committed+pushed.

## 7b. Phase 2 — status (developer, task-a5c0549d, 2026-09-25)

**Shipped:**

- `scripts/spawn-worker-remote.sh` — the Contabo/Linux spoke launcher,
  parameter-compatible with `windows/spawn-worker.ps1` (same 12 flags, one
  runner today: `claude`). Bash + tmux instead of PowerShell + a scheduled
  task: no session-0/session-1 boundary to cross on Linux, so
  `tmux new-session -d` IS the detached worker, and its `pane_pid` stays the
  worker's own pid once `launch.sh`'s last line `exec`s into `claude` (no
  fork in between — verified live). Idempotent worktree reuse, the same
  stale-file/`info/exclude` handling as the winbox launcher, and its own
  `--dry-run` mode (for local testing under the Mac's real bash 3.2, since
  the script only ever *executes* on Contabo's newer bash — see its header).
  Resolves `claude`'s absolute path itself (`command -v` + known install
  locations) rather than trusting a login shell's `PATH` — measured live: a
  plain `ssh alias 'bash script'` is a non-interactive, non-login
  invocation that sources neither `~/.bashrc` nor `~/.zshrc`, so a
  `bash -l "$LAUNCH_SH"` launch could not see a PATH entry the ssh session's
  own environment already had.
- `tools/delegate.py::_spawn_remote` gained a `linux` branch (`windows`
  branch untouched, only re-indented under an `os_name` check): renders the
  same `worker_tool_grants`-based claude flags winbox already gets via the
  existing, already-host-agnostic `_render_remote_claude_args`, pipes the
  rendered `TASK.md` prompt over ssh's own stdin (`subprocess.run(...,
  input=prompt)`) instead of scp — plain OpenSSH forwards it, no
  PowerShell console-encoding hazard to work around — and parses the
  launcher's own `SPAWNED pid=<n> session=<name> worktree=<path>` /
  `SPAWN_REFUSED=<reason>` stdout contract (regex, not the bare
  `int(lines[-1])` the windows branch uses — deliberately different, more
  structured shapes for two different launchers).
- `_ensure_remote_deploy_linux` / `_remote_sha256_posix`: scp's just
  `scripts/spawn-worker-remote.sh` onto the spoke (sha256-compared, only
  when changed) — the pre-merge bootstrap problem, since this task's own
  script can't reach Contabo through `git pull` until the PR that adds it
  is merged to main. Unlike winbox's dedicated non-git deploy folder,
  Contabo's `agents_root` **is** a live git checkout of this same repo (two
  CTO sessions run out of it today), so role docs (`roles/*.md`) are read
  by the launcher directly from that checkout instead of being deployed a
  second time.
- `config/hosts.yaml` contabo: `agents_root`/`worktrees` now point at the
  real MoonieXHQ checkout (`/opt/MoonieXHQ/Agents/Core`) — `/opt/mooniex-agents`
  was a compat symlink from the 2026-09-23 migration, still valid today but
  due for removal; `provides` widened to `[always_on, api, ffmpeg,
  playwright_chromium, node20]` (measured present on the box).
  `config/projects.yaml`'s `paths.contabo` for `mooniex-agents` was
  **left** on the old `/opt/mooniex-agents` value — updating it wasn't a
  declared `touches` path for this task, and the compat symlink resolves
  correctly today; flagged for whoever removes the symlink.
- **Disk-floor host-awareness fix** (CTO review mid-task, 2026-09-24): the
  disk-floor gate (§ADR 0030) ran unconditionally against the **Mac's**
  free space for every spawn, including one bound for a spoke —
  `delegate_task`'s own host resolution happened *after* the gate. Caught
  live: task-43b6514d ("queued for disk — 3.9 GB free, needs 5.0 GB")
  while Contabo itself had plenty. Fixed: `resolved_host` is now computed
  before the gate; a `mac`-bound spawn still reads local disk
  (`_free_gb()`), any other host is probed over ssh (`_remote_free_gb`,
  `df -Pk /`) instead. Fails **open** (never refuses) on an unreachable
  probe, and is skipped entirely during `dry_run` (a real ssh probe there
  would violate `dry_run`'s own "prints the command, never runs it"
  contract). **Known remaining gap, not fixed here:**
  `runners/watchdog.py`'s `_drain_disk_queue()` still gates every queued
  entry's resume purely on the Mac's free space (`DISK_QUEUE_RESUME_MARGIN_GB`
  check), regardless of which host it was queued for — a spoke-bound task
  queued by a low Mac disk reading will still wait on the *Mac's* disk
  clearing before the watchdog even attempts to drain it.
  `runners/watchdog.py` was not a declared `touches` path for this task.
- `tests/test_spawn_remote_linux.py` — 19 tests: linux dry-run renders the
  exact ssh command (every flag asserted), the winbox dry-run shape is
  byte-for-byte unchanged (regression guard), an `os: freebsd` host still
  raises `NotImplementedError`, the `SPAWNED`/`SPAWN_REFUSED` output
  contract is parsed correctly (success/refused/unparseable), the
  disk-floor host-awareness fix (spoke-healthy-Mac-low proceeds,
  spoke-low-Mac-healthy queues naming the spoke, fail-open on an
  unreachable probe, skipped during dry-run), `_remote_free_gb`'s `df`
  parsing, and the shell script itself under `bash -n` + its own
  `--dry-run` (real bash 3.2, per the script's header).

**Measured live on Contabo (task-43b6514d, the brief's own acceptance
smoke test — `npx hyperframes --version` + a 5s 1080x1920 render):**

- Real `delegate_task(host="contabo")` (dry-run then real) against the
  **production** `state/tasks.db`: dry-run rendered the exact ssh command;
  the real call auto-deployed `spawn-worker-remote.sh` (sha256 mismatch —
  first use), then reported `SPAWNED pid=3251641 session=mooniex-task-43b6514d
  worktree=/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-43b6514d`.
  `ssh mooniex-vps tmux ls` confirmed the session alive; `tmux capture-pane`
  showed a live, thinking Claude Code session under the correct cwd —
  the pid/tmux/worktree/pipe mechanics of this task's own new code are
  fully proven working end to end against the real box.
- **New finding, not fixed here (`scripts/hook-self-repo-guard.py` not a
  declared `touches` path):** spawning the **`mooniex-agents` project
  itself** (the org's own self-modifying repo) onto a spoke trips
  `hook-self-repo-guard.py`. That hook resolves the task's declared
  `touches` from `<worktree>/../../state/tasks.db` — the checkout's *own*
  local copy — which on the Mac is the live hub but on Contabo is a
  near-empty, unsynced copy (confirmed live by the spawned worker itself:
  `sqlite3 .../state/tasks.db "SELECT count(*) FROM tasks"` → 22 rows, none
  matching its own task id). A missing row raises `GuardError` (not the
  hook's `HubUnreachable`/`ArchivedHub` fail-**open** paths — the sqlite
  file opens fine, it's just missing the row), so `decide()` fails
  **closed**: every `Edit`/`Write` call, and every `Bash` command
  containing a `>` redirect or another write-pattern `bash_targets()`
  recognizes, is refused as "undecidable" — regardless of whether the
  actual target path is even one of the protected prefixes
  (`lib/ runners/ tools/ policies/ config/ state/locks/`), because the
  touches lookup happens before path classification. This is narrow — the
  hook only activates for a worktree literally named `mooniex-agents__*`
  (`WORKTREE_PREFIX`), so it is inert for every other project spawned on a
  spoke — but it means **this specific smoke task, on this specific
  project, could not write its HyperFrames test file** the ordinary way.
  Live evidence (`tmux capture-pane`, task-43b6514d): the spawned worker
  independently diagnosed the exact same root cause on its own (reading
  the hook's source, querying the local db) before this report was
  written. Fixing this needs either (a) `hook-self-repo-guard.py` reading
  the **hub's** tasks.db over ssh/API on a spoke the way `HubUnreachable`'s
  Postgres path already anticipates, or (b) not spawning the org's own
  repo onto a spoke that lacks a synced task registry — a decision for
  whoever owns that hook, out of this task's scope.
- fps/RAM numbers: not obtained — the smoke task never reached the
  `npx hyperframes render` step because of the guard finding above. Left
  for a re-run once the guard question above is resolved, or for a smoke
  task on a project the guard doesn't watch.

**Not done / open:**

- `config/projects.yaml`'s `paths.contabo` left on the compat-symlink path
  (see above) — cheap follow-up once it's a declared touches path.
- `runners/watchdog.py`'s disk-queue drain is still Mac-disk-only (see
  above).
- `hook-self-repo-guard.py`'s spoke/hub tasks.db mismatch for the
  `mooniex-agents` project (see above) — the more consequential of the two
  gaps, since it blocks real DEV work on this repo from Contabo, not just
  disk-queue timing.
- Runner support beyond `claude` on Contabo (`codex`/`agy`) — not
  installed/verified on the box; `config/hosts.yaml` lists `runners:
  [claude]` only, matching what winbox went through in two steps
  (task-adbc6f43 added codex/agy there well after Phase 1 shipped).

## 7c. Both Phase 2 gaps fixed + smoke render proven (developer, task-378523bb,
GH PASAKON/Agents-Core#180, 2026-09-25)

**Gap 1 fixed — touches sidecar.** `tools/delegate.py::_spawn_remote`'s linux
branch now renders the task's declared `touches` as a base64 JSON blob
(`--task-meta-b64`, shape `{task_id, project, role, host, owner_cto,
touches:[...]}` — no secret in it). `scripts/spawn-worker-remote.sh` decodes
it into `<worktree>/.org-task.json` (mode 600, added to the worktree's own
`info/exclude` alongside HEARTBEAT/MAILBOX.md — never committed).
`hook-self-repo-guard.py` gained `load_touches_for(root, task_id)`, which
prefers a task-id-matching sidecar over the tasks.db lookup and falls back
to the unchanged `load_touches(db_path_for(root), task_id)` when no sidecar
exists (the Mac path — behavior-identical to before). `.org-task.json` was
added to `PROTECTED_EXACT` so a worker can't edit its own grant. Fixed
`db_path_for`'s docstring, which still named the pre-migration
`/opt/mooniex-agents` path.

**The pre-merge bootstrap problem, twice.** `_ensure_remote_deploy_linux`
(renamed from a single-file to a `_REMOTE_DEPLOY_FILES_LINUX` list) now
scp's *two* files onto the spoke ahead of any merge, sha256-compared like
before: `scripts/spawn-worker-remote.sh` (existing) and
`scripts/hook-self-repo-guard.py` (new). The second one matters because a
freshly `git worktree add`-ed worktree checks out whatever's on
`origin/<base>` — which doesn't carry this fix until the PR merges — so
`spawn-worker-remote.sh` itself now copies its own box's (just-deployed)
`scripts/hook-self-repo-guard.py` into every worktree it creates, right
after the worktree exists. Verified locally end-to-end against a fake git
repo (clone + worktree add + fake tmux) before touching the real box: the
sidecar decoded correctly (mode 600, correct JSON), the worktree's guard
copy carried the "fixed" content rather than the stale committed one, and
`launch.sh`'s generated PATH line was correct.

**Gap 2 fixed — Node 22 for workers only.** Official Node 22 LTS Linux x64
tarball (`v22.23.3`, sha256-verified against that release's
`SHASUMS256.txt`) installed under
`/opt/MoonieXHQ/Agents/Core/.tools/node/` (gitignored;
`config/machine-contract.yaml` row added, class REBUILD, one-line rebuild
command). `spawn-worker-remote.sh`'s generated `launch.sh` prepends
`<agents_root>/.tools/node/bin` onto `PATH` only when that directory
exists. Confirmed after install: inside `.tools/node/bin/node --version` →
`v22.23.3`; system `node --version` (still `/usr/bin/node`, unchanged) →
`v20.20.2` — host services (usage feeds, login relay) untouched. An
unrelated, untracked `/opt/node-v22` (v22.11.0) was found already present
on the box during this task (`config/machine-contract.yaml`'s existing
glob row for `.venv`/`idm-venv` mentions it) — left alone, not reused, per
the task's explicit path instruction; flagged here so whoever owns it
knows a second Node 22 exists.

**Stale smoke worker cleaned up.** task-43b6514d's tmux session
(`mooniex-task-43b6514d`, pid 3251641) killed over ssh, its worktree
removed with `git worktree remove --force` on Contabo, then closed via
`lib.db.update_status(..., actor="developer-task-378523bb", delegate_log=
"superseded by task-c1645fe5")` — `close_dev`/`close_remote` exist but both
refuse `blocked_human` by design (awaiting a human decision), so neither
was the right tool here; `update_status` (never raw sqlite) is the org
path for this case.

**PROOF — smoke render on the real box, task-c1645fe5** (spawned via a
direct `delegate.delegate_task(host="contabo")` call from this task's own
worktree against the production hub db, same pattern task-a5c0549d used;
dry-run first, then real — deploy log confirmed both files scp'd fresh).
REPORT.md pulled from `origin/agent/developer-task-c1645fe5` (`git fetch` +
`git show <branch>:REPORT.md`, pushed by the worker itself; task closed
`done` directly per CTO instruction since the branch poller is off):

- `npx hyperframes@0.8.40 --version` → `0.8.40`.
- Composition: `prototypes/contabo-smoke/` — a minimal 5s 1080x1920
  HyperFrames composition, one moving text block (GSAP `y:400→-400`,
  opacity `0→1`). `lint`/`check` both fully green.
- Render: `npx hyperframes@0.8.40 render` — **exit 0, 150/150 frames**,
  ffprobe-verified output (h264, 1080x1920, 30/1 fps, `duration=5.000000s`).
- **Wall seconds:** 25.5s for the render pipeline alone (compile → capture
  → assemble, as the CLI itself reports); **40.72s** for the full command
  including a one-time ~114MB chrome-headless-shell download (first
  successful render on this box, nothing cached yet).
- **Frames/second:** capture-phase only, 150 / 23.648s = **6.34 fps**;
  whole pipeline (excludes the Chrome download), 150 / 25.5s ≈ **5.88
  fps**. Capture ran in `screenshot` mode (software GL — no browser GPU on
  this box), not the faster BeginFrame path; expected on a headless VPS,
  not a defect.
- **`free -m`, sampled every 2s through the render:** peak `used` 3598MB of
  7941MB total (`available` never dropped below ~4.3GB); swap `used` held
  flat at 19MB throughout — no swap pressure, no low-memory fallback
  triggered (that only forces below the box's ~8GB boundary).
- One real dependency gap found and fixed along the way: `unzip` was
  missing on this box, so the CLI's first-run chrome-headless-shell
  download couldn't be extracted (`no zip archiver is available`) and the
  first render attempt failed before the fix (`apt-get install -y unzip`,
  ~174KB, reversible). Worth baking into the box's base provisioning
  rather than being a per-session discovery — flagged in the smoke task's
  own skill-learning section (`hyperframes-cli`, missing prereq check).

**Both Phase 2 gaps from §7b are now closed.** The `mooniex-agents`
project's own repo can be worked on from a Contabo-spawned DEV, and a
HyperFrames render runs there end-to-end with real numbers on record.
