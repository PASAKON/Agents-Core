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
