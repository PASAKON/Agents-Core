---
name: dev-spawn-protocol
owner: CTO
origin: mooniex-org
scope: >-
  Spawn-time checklist only — visible iTerm tab, full task-id title, kickoff ping,
  touches lock, auto-close on done. Does not create the task or review DEV output.
  Enforces IRON-RULES §29.
description: Required steps when CTO spawns a DEV agent. Trigger on /dev-spawn-protocol and before any delegate_task or DEV spawn, or when the user says "spawn dev", "delegate", "kick off the dev", "start the developer".
created_by: human
audience: [cto]
---

# DEV Spawn Protocol

Required steps every time CTO spawns a DEV. Memory rule (CEO 2026-05-19, IRON-RULES §29): visible animation + mandatory kickoff ping. Skipping any step is a P0.

## Pre-spawn

### 0. Force Claude when a cheap miss is expensive (CEO 2026-08-10)
`WORKER_MODEL_PROVIDER=auto` routes on **quota headroom alone** — it cannot see how
costly a mistake on this particular task would be. Before delegating, set the
per-task override when the work is any of:

- **reviewing, finishing, or repairing someone else's code** (including a DEV
  that died mid-task)
- **security-sensitive** — auth, secrets, tokens, permissions
- **anything where a silent wrong answer ships**

```bash
sqlite3 state/tasks.db "UPDATE tasks SET model_hint='claude' WHERE id='task-XXXX';"
```

Everything else: leave it NULL and let the router pick on quota. An unrecognised
value falls back to normal routing (`lib.config.worker_provider_overrides`).

Why this exists: on 2026-08-10 a DEV finished a feature with all 96 existing
tests green — and the feature did not work at all. It never wired the new data
into the render call and shipped zero CSS for the new UI. No existing test
touched the new code, so green meant nothing. A second DEV on Claude, pointed at
the same branch, found both in one pass. Reviewing another agent's work is
exactly the job where a cheaper model's misses stay invisible until a human
hits them.

### 1. Pick role by deliverable, not title
- Writing **test infra / harness / fixtures** → `developer`, not `tester`.
- Writing **assertions on existing system** → `tester`.
- Memory: title keyword is misleading; deliverable kind decides.

### 2. Path lock — `touches` is mandatory
- Pass `touches` to `create_task` as JSON array of repo-relative paths the task will modify.
- Empty list **only** if genuinely read-only.
- Call `check_collisions(project, touches)` **before** `create_task` if any other task is in-flight.
- If overlap → either `depends_on` the blocker or shrink `touches` to be disjoint.

### 3. Serialize logical conflicts
- Lock layer ignores `depends_on`. Never pre-queue dependent waves with overlapping touches.
- One task at a time per overlapping path set.

### 3b. Web Designer spawns — carry Project ID + design-source + target (CEO 2026-06-04)
When role is `web_designer`, the kickoff brief MUST include all four, or the agent cannot locate the work (its worktree omits `.od/`):
1. **Project ID** — claudesign (open-design) UUID, e.g. `7b4becb9-65dd-4b89-b15f-b7b0ec35c607`.
2. **Design source (read-only)** — `/Users/gob/Projects/mooniex-claudesign/.od/projects/{ID}/`; name+skill via `sqlite3 …/.od/app.sqlite "select name,skill_id from projects where id='{ID}'"`; design at `.od/projects/{ID}/.od-skills/{skill}/example.html`. `.od/` is gitignored → read by ABSOLUTE path, never write into it.
3. **Target repo + path** — where the deliverable is written (the org `touches`); state which path is for what.
4. **Deliverable** — what to build.
Full spec + template line: `playbooks/web-designer.md §9`.

### 3c0. Before ANY browser_operator spawn — does a runner already exist? (IRON-RULES §53, CEO 2026-09-19)

If the task repeats the same operation more than 3 times, the model may not do the repetitions. Check for an existing zero-model runner first — the pattern is `scripts/higgsfield/gen_loop.py` (Playwright over CDP on a dedicated Chrome profile, resumable ledger) and the Flow port is `docs/ops/flow-operator-design.md` / `tools/flow_shoot.py`. If none exists, the first task is a `developer` task that BUILDS the runner, not an operator that clicks. Measured 2026-09-19: two operators, 650M context tokens, 405 screenshots, 8 clips.

### 3c. Browser Operator spawns — the brief is where the cost is (CEO 2026-08-10)

A browser task's token cost is set by **how you wrote it**, not by how clever the
agent is. Do not tell it to "find the cheapest way" — it will write a paragraph
of cost analysis before every task and you pay for that paragraph. The
`browser-operator` skill already carries the cheap-path ladder; your job is to
remove the reasons it has to climb.

Measured on the first real run (task-e1c48798): 29 steps, 8 screenshots. The
brief said "on higgsfield.ai" instead of the deep link, so the agent spent steps
navigating to a URL the CTO already knew.

Every browser brief carries these:

1. **The deep link, not the site.** `https://site/app/page?model=x`, never "go to
   site and find the page".
2. **The goal as the fact you want back**, not the activity — "report the exact
   text on the Generate button", not "check the settings panel".
3. **What you already know** — where the controls are, what the page looked like
   last time, which selectors worked. Prior knowledge is free; rediscovery is not.
4. **The stopping condition** — "stop as soon as you can answer X". Without one
   it keeps looking.
5. **What NOT to verify** — "don't wait for it to finish", "don't check History".
   Agents over-verify by default; naming the non-goals is cheaper than paying for
   them.
6. **Budgets** — steps and screenshots, explicitly. 40/5 is the skill's default;
   set lower when you know the task is small.
7. **Answer in text.** Asking to "see" or "show" invites screenshots.
8. **If it repeats, ask for the script, not the answer.** One paid run, then zero.
9. **Anything longer than a few lines goes in the worktree, not the chat.**
   Write `<worktree>/<TOPIC>.md` and send a one-line pointer to it.
   `tools/send_to_worker.py` types character-by-character into a TUI: a long
   message is slow, can die mid-type (measured 2026-08-12: one SIGTERM at 2
   minutes), and is echoed back in full in the tool result, so you pay for the
   same text twice. A worktree file costs one write, survives the DEV being
   killed and respawned, and can be re-read any time. Proven on
   task-cda4f469 — a `PROMPTS.md` carrying ten generation prompts ended the
   operator's repeated requests for prompt text permanently.

10. **A live secret can never be typed into a worker.** The worker sandbox's
   Bash classifier refuses any command containing a credential-shaped string
   (`Auto-Mode Bypass`, then `Credential Leakage`), no matter who authorised
   it — measured 2026-09-18 on task-13bfcd4d, where two single-use OAuth
   codes from the CEO expired unused (GH #156). OAuth, 2FA and device-flow
   steps therefore end at "hand the human a runnable command"; write the
   brief that way from the start instead of relaying codes mid-task. Also:
   PKCE-style logins bind the code to the process that printed the URL, so a
   code pasted into a *different* run fails even without the classifier.

Costly signs in a draft brief: no URL, "check whether…", "make sure everything
looks right", "explore", "and report anything interesting".

## Spawn

### 4. Visible iTerm tab
- Every spawn = new iTerm tab (or tmux+ttyd pane).
- Tab title = **full task-id** (e.g. `task-65a08ade`), not short prefix.
- Route by iTerm window id, not name (see commit 67101ec).

### 5. Mandatory kickoff ping
- First message to DEV must be a kickoff confirming: task-id, repo, role, scope, allowed paths.
- DEV must echo-ack before doing real work.
- No silent spawns. Memory: IRON-RULES §29.

## During

### 6. GH issue on every blocker
- If DEV reports a blocker (env, missing access, ambiguous spec), CTO opens a GH issue immediately.
- Title = `[task-XXX] <blocker summary>`. Body = DEV's exact message + context.
- Memory: every blocker = issue, no exception.

### 6b. Arm a liveness Monitor at delegate time — this replaces DEV progress pings
`_worker_shared.md` Hard Rule 10 forbids the DEV from reporting that it is still
working. **Watching for its death is therefore your job, and you must arm the
watch at spawn, not after something looks wrong.**

Why: a heartbeat ping costs a full C-level turn — the entire system prompt,
every CLAUDE.md, the memory index and the whole conversation re-processed — to
learn one bit of information. A Monitor gets the same bit from the process
table for free. Measured on task-cda4f469: 52 of 65 DEV messages carried no
new information, and the Monitor caught a killed operator immediately.

**Watch three things, not one: the status, the PROGRESS, and the dialog.**
A pid answers "alive" for a worker that is working, a worker that is wedged, and
a worker sitting on a permission prompt. It cannot tell them apart, so on its own
it is close to useless. Measured 2026-09-18 across 41 workers in one session:
**not one died on its own**, but two stalled for 50 and 25 minutes while this
check reported `proc=alive` the entire time.

Arm this right after `delegate_task` returns. Substitute the task id, the tmux
name, and `OUT` — **the file the task is supposed to be filling.** A flat line
count next to a live pid is what a stall actually looks like.

```bash
DB=/Users/gob/MoonieXHQ/Agents/Core/state/tasks.db
W=/Users/gob/MoonieXHQ/Agents/Core/worktrees/<project>__<role>__task-XXXXXXXX
OUT="$W/<the file this task produces>"     # progress, not liveness
prev=""
while true; do
  row=$(sqlite3 "$DB" "SELECT status||'~'||COALESCE(pid,0) FROM tasks WHERE id='task-XXXXXXXX';" 2>/dev/null || echo "dberror~0")
  st=${row%%~*}; p=${row##*~}
  alive=dead
  if [ "$p" != "0" ] && kill -0 "$p" 2>/dev/null; then alive=alive; fi
  n=0; [ -f "$OUT" ] && n=$(wc -l < "$OUT" | tr -d ' ')
  blocked=no
  tmux capture-pane -p -t wd-XXXXXXXX 2>/dev/null | grep -q "Enter to confirm" && blocked=PERMISSION-DIALOG
  cur="$st/$alive/$n/$blocked"
  if [ "$cur" != "$prev" ]; then echo "task status=$st proc=$alive progress=$n blocked=$blocked"; prev="$cur"; fi
  case "$st" in
    done|review|failed|cancelled|conflict) echo "TERMINAL state=$st progress=$n"; break;;
    dberror) echo "DB READ FAILED"; break;;
  esac
  if [ "$alive" = "dead" ] && [ "$st" = "in_progress" ]; then
    echo "SILENT DEATH - status=in_progress but pid $p gone"; break
  fi
  sleep 45
done
```

If a task produces no file until the end, give it one — ask the brief for an
append-as-you-go log. A task whose only output arrives at the end is a task you
cannot supervise, and it is also a task that loses everything when it stalls.

Run it with `persistent: true`. It emits only on change, so a quiet DEV
produces zero notifications.

**What the Monitor does not catch:** a process that is alive but internally
wedged. **The most common cause by far is a permission dialog** — the worker
asked for access to something (a desktop app, a new tool) and is sitting on
`Enter to confirm · Esc to cancel` forever. The pid is alive, the status is
`in_progress`, the tmux session is healthy, and nothing whatsoever is happening.
Measured 2026-09-18: 25 minutes lost this way on a task with a deadline, while
the Monitor reported `proc=alive` the whole time.

Two cheap fixes, both worth doing:

- **Watch progress, not liveness.** Add the task's own output to the Monitor —
  a line count of the file it is supposed to be filling — so a flat number is
  visible even while the process looks fine:
  `n=0; [ -f "$W/out.tsv" ] && n=$(wc -l < "$W/out.tsv")`
- **Detect the dialog directly**, since it has a fixed string:
  `tmux capture-pane -p -t wd-<id> | grep -q "Enter to confirm" && echo BLOCKED`

To clear one: `tmux send-keys -t wd-<id> Enter` confirms the highlighted option,
which is **Deny** by default. `Escape` alone did not clear it on the measured
occasion. Then send the worker a message saying what to do instead — a denial
with no redirection just stalls it again. Detect that from the *absence* of expected state changes against the
job's known per-item duration — if a step normally lands every ~25 minutes and
90 minutes have passed with nothing, intervene. Do not solve this by
re-introducing heartbeats.

## Post

### 7. Auto-close tab on done
- When DEV `status=done` and CTO accepts → close iTerm tab automatically.
- Do not leave stale tabs.
- Failed tasks keep their tab open for inspection.

### 8. Hand off to merge gate
- Move to `cto-merge-checklist` before `merge_task`.
- Do not skip the checklist even on "obvious" merges.

## Failure modes to refuse

- Spawning without `touches` set → refuse, retry with paths.
- Spawning into an existing tab (reuse) → refuse, new tab only.
- Title using short prefix → refuse, full task-id.
- Skipping kickoff ping → refuse, DEV must echo-ack.
- Spawning `web_designer` without Project ID + design-source + target → refuse, fill from `playbooks/web-designer.md §9` (step 3b).

## Reference

- `runners/cto.py` — CTO orchestration loop
- `lib/db.py` — task table + locks table
- `scripts/spawn-cto.sh` — top-level entry
- Wiki: `playbooks/web-designer.md §9` — Designer spawn inputs (Project ID + paths)
- Memory:
  - `feedback_dev_orchestration.md`
  - `feedback_dev_visible_animation.md`
  - `feedback_dev_role_selection.md`
  - `feedback_task_queue_serial.md`
  - `feedback_designer_spawn_inputs.md`

## Field notes

- 2026-09-22 [MISSING] §6b — `reopen_task` + `delegate_task` on a LIVE worker re-sends only the generic kickoff; the worker answered "same kickoff, already handled" and the 25 s watchdog stamped `failed` with the pid alive. Repair that worked: `UPDATE tasks SET status='in_progress' WHERE id=… AND status='failed'` (keeps the surface reaper off the live pid) → write `<worktree>/CTO-FEEDBACK.md` (send_to_worker delivers header only, #136/#154) → `tmux send-keys -t wd-<id> C-u 'read CTO-FEEDBACK.md and continue' Enter` · evidence: task-ad534f86 21:23–21:26, worker resumed in its own context · status: pending
- 2026-09-22 [MISSING] §3c.9 — a line typed into a worker's tmux pane that wraps past one screen line is never submitted: Enter is eaten and the text sits in the input box ("Press up to edit queued messages" when the worker is mid-turn). Keep the pane message under ~100 chars and put the substance in a worktree file · evidence: two workers the same evening (ad534f86, df0541aa), both fixed by C-u + a short line · status: pending
- 2026-09-22 [MISSING] §2 — a worktree is cut from LOCAL main; if the brief says "X merged <sha>" and the file is missing, `git rev-parse main origin/main HEAD` and `git merge main` — `git status`'s "up to date with origin/main" is about the tracking ref, not about the file · evidence: task-a6129a75 (local main 8 ahead at spawn, tools/decide.py absent in the worktree) · status: pending
- 2026-09-22 [MISSING] §Failure modes — a remote spawn refused with `GITHUB_SSH_ROUTE=unreachable` is a network reading from **winbox → github.com**, outbound. Re-probe it live before changing anything: `ssh winbox "git ls-remote --exit-code git@github.com:PASAKON/MoonieX-Agents.git HEAD"`. Tailscale SSH (`tailscale set --ssh=false`) governs INBOUND ssh to a tailnet node and cannot cause this. 11 spawns failed this way 11-12 Sep; on 22 Sep ports 22 and 443 both answered and ls-remote returned HEAD in one call, so it was transient, not config · evidence: state/logs/cto-e1e3d3ef.log lines 4-53, task-0ae3acc9 · status: pending
- 2026-09-23 [MISSING] §6b — a worker that dies seconds after spawn with NO transcript, on a repo that was just moved (HQ migration), is Claude's folder-trust prompt: the default is "No, exit" and the kickoff/wake Enter confirms it. Reproduce by running spawn-worker.sh in a tmux pane with `remain-on-exit on`; recover with Down+Enter in the pane · evidence: task-77a2e043, GH #161 · status: pending
- 2026-09-23 [MISSING] §6b — resetting a dead task to pending must also clear `assigned_agent`: `db.claim_task` requires it NULL, so every re-delegate dies with "could not claim task" in ~6 s while the MCP `delegate_task` returns the row as if it spawned · evidence: task-77a2e043 · status: pending
- 2026-09-23 [MISSING] §3c.9 — after a queued message is consumed, the NEXT line typed into an idle worker can sit unsubmitted in the input box: `send-keys Enter` twice did nothing, and `send-keys C-m` submitted it. The line was 78 chars, so this is not the wrap case. Always capture the pane after sending; if the text is still on the `❯` line, send C-m · evidence: task-77a2e043, 8 min idle 03:21–03:29 · status: pending
- 2026-09-23 [COSTLY] §before delegate — a C-level whose delegate emits "imported delegate.py … still running the OLD code" does not have that day's disk floor or sparse worktrees: three spawns at 14:29 made three full 882 MB checkouts and free space fell 11 → 3.4 GB (red). When that warning appears: restart the session before spawning, or at least run `df -h /` first and spawn nothing under 10 GB free · evidence: tasks abc20690/44963fee/74ad48db, df 14:30 · status: pending
- 2026-09-23 [MISSING] §3c.9 — a winbox spawn that fails with "claude did not appear within 60s ... interactive scheduled task may not have started" can be the **Windows 32,767-char command-line limit**, not the scheduled task: `launch.ps1` passes the prompt AND the 27.7k-char shared conventions as arguments, leaving ~3.7k chars for the brief. Measure `args.json` in `C:\Users\UsEr\mooniex\.launch-<task>\` before debugging the desktop. Fix that worked: brief in `docs/ops/briefs/<task>.md` on main, row holds a ~450-char pointer · evidence: task-fc7157c8 (33,856 chars failed twice, pointer spawned first try, pid 18580); GH issue not filed, gh unauthenticated on Contabo · status: pending
- 2026-09-23 [MISSING] §7 — `close_dev` from a CONTABO session errors `No such file or directory: 'osascript'` (it closes an iTerm tab, Mac-only) before it kills a winbox worker. A winbox worker that wrote REPORT.md but never ran its finish step stays `in_progress` with a live pid. Path that worked: scp REPORT.md → store it in `report`, status review → `ssh winbox taskkill /PID <pid> /T /F` (launch.ps1 exits 0, so the WT tab closes with it) → status done · evidence: task-fc7157c8 · status: pending
