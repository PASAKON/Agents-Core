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
| Worker reaches the org via stdio MCP | `config/worker.mcp.json` | `/Users/gob/Projects/Agents/.venv/bin/python` on the same box as `state/tasks.db` |

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
