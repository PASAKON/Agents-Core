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

### 5b. Check the pane for the folder-trust prompt right after spawn
Until GH #161 is fixed, a worktree under the moved `~/MoonieXHQ/Agents/Core/worktrees/`
is not covered by Core's trust entry, so Claude opens on "Accessing workspace …
❯ No, exit / Yes, I trust this folder" — and the kickoff wake's Enter picks
**No, exit**. The worker claims the task, then dies with no transcript.
Within ~10 s of `delegate_task`, `tmux capture-pane -p -t wd-<id> | grep -q "trust this folder"`;
if it matches, send `Down` then `Enter`. If it already died: reset the row
(`status='pending', pid=NULL, assigned_agent=NULL`), respawn in tmux with
`remain-on-exit on`, and do the same. Promoted from a field note on two runs
(task-77a2e043, task-94755874).

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
- 2026-09-23 [MISSING] §6b — a worker that dies seconds after spawn with NO transcript, on a repo that was just moved (HQ migration), is Claude's folder-trust prompt: the default is "No, exit" and the kickoff/wake Enter confirms it. Reproduce by running spawn-worker.sh in a tmux pane with `remain-on-exit on`; recover with Down+Enter in the pane · evidence: task-77a2e043, GH #161; second run task-94755874 agreed 2026-09-23, promoted to §5b · status: promoted
- 2026-09-23 [MISSING] §3c — every live Chrome on the Mac holds a ~1.4 GB code-sign clone of Chrome.app under /private/var/folders/…/X/com.google.Chrome.code_sign_clone, freed only when that Chrome quits. A brief that has a worker launch a test Chrome must say "quit it whenever you are not actively testing, and before you report"; the worker's :9250 test Chrome tipped the Mac to 1.7 GB free at 17:52 · evidence: task-94755874, measured by CTO 0e8d80b8 · status: pending
- 2026-09-23 [MISSING] §6b — resetting a dead task to pending must also clear `assigned_agent`: `db.claim_task` requires it NULL, so every re-delegate dies with "could not claim task" in ~6 s while the MCP `delegate_task` returns the row as if it spawned · evidence: task-77a2e043 · status: pending
- 2026-09-23 [MISSING] §3c.9 — after a queued message is consumed, the NEXT line typed into an idle worker can sit unsubmitted in the input box: `send-keys Enter` twice did nothing, and `send-keys C-m` submitted it. The line was 78 chars, so this is not the wrap case. Always capture the pane after sending; if the text is still on the `❯` line, send C-m · evidence: task-77a2e043, 8 min idle 03:21–03:29 · status: pending
- 2026-09-23 [COSTLY] §before delegate — a C-level whose delegate emits "imported delegate.py … still running the OLD code" does not have that day's disk floor or sparse worktrees: three spawns at 14:29 made three full 882 MB checkouts and free space fell 11 → 3.4 GB (red). When that warning appears: restart the session before spawning, or at least run `df -h /` first and spawn nothing under 10 GB free · evidence: tasks abc20690/44963fee/74ad48db, df 14:30 · status: pending
- 2026-09-23 [MISSING] §3c.9 — a winbox spawn that fails with "claude did not appear within 60s ... interactive scheduled task may not have started" can be the **Windows 32,767-char command-line limit**, not the scheduled task: `launch.ps1` passes the prompt AND the 27.7k-char shared conventions as arguments, leaving ~3.7k chars for the brief. Measure `args.json` in `C:\Users\UsEr\mooniex\.launch-<task>\` before debugging the desktop. Fix that worked: brief in `docs/ops/briefs/<task>.md` on main, row holds a ~450-char pointer · evidence: task-fc7157c8 (33,856 chars failed twice, pointer spawned first try, pid 18580); GH issue not filed, gh unauthenticated on Contabo · status: pending
- 2026-09-23 [MISSING] §7 — `close_dev` from a CONTABO session errors `No such file or directory: 'osascript'` (it closes an iTerm tab, Mac-only) before it kills a winbox worker. A winbox worker that wrote REPORT.md but never ran its finish step stays `in_progress` with a live pid. Path that worked: scp REPORT.md → store it in `report`, status review → `ssh winbox taskkill /PID <pid> /T /F` (launch.ps1 exits 0, so the WT tab closes with it) → status done · evidence: task-fc7157c8 · status: pending
- 2026-09-23 [MISSING] §6b — a LIVE worker that ends its turn (waiting on a long pipeline run, or asking the CTO a question) can be stamped `rate_limited` with no 429 anywhere; GC then reaps it at 30 min as "rate_limited overdue". Check the pane and the pid before trusting that status. Repair that worked twice: `UPDATE tasks SET status='in_progress' WHERE id=… AND status='rate_limited'`, then re-arm the Monitor · evidence: task-77a2e043 (EP55 pipeline, reset twice the same afternoon), memory reference_rate_limited_false_positive_from_higgsfield_429 · status: pending
- 2026-09-23 [COSTLY] §4 — two `delegate_task` calls started in parallel both ran `git config extensions.worktreeConfig true` on the shared repo; one died with "could not lock config file .git/config: File exists" and the task stayed pending with no worktree. Delegate one at a time, or make tools/worktree.py retry on the config lock · evidence: task-82380776 first delegate 21:27 (re-delegated alone, fine) · status: pending
- 2026-09-23 [MISSING] §3c — a brief for video/frame analysis must carry a disk budget: extracting every frame of an 85 s 1080x1920 clip as PNG is ~7 GB, above what the Mac had free (5.3 GB, floor 5 GB). Say "decode through an ffmpeg pipe or at 270x480, full-res only for single frames, stop under 6 GB free" in the brief, not after spawn · evidence: CTO-FEEDBACK.md sent to task-82380776 at 21:40; disk dipped to 3 GB the same half hour · status: pending
- 2026-09-23 [MISSING] §2 — a `touches` entry is an exact file or a directory ending in `/`, never a name prefix. `config/decisions/bl.` (meant as bl.*.yaml) matched nothing, and self_repo_guard refused every write to the six site files; the worker stopped and filed #169. List the files explicitly · evidence: task-5cfe20b1, Agents-Core#169 · status: pending
- 2026-09-23 [MISSING] §2 — write deliverable paths in the brief in full, repo-relative, and identical to `touches`. The brief listed `scripts/bl_compose.py` under a skill heading while touches said `.claude/skills/blackliquidity-cut/scripts/…`. The worker built in repo-root `scripts/`, and the merge needed override_touches_check · evidence: task-42e3b6af → de0acea1 · status: pending
- 2026-09-24 [MISSING] §6b — for a REMOTE (winbox) worker, detect its report with `git -C <worktree> status --porcelain --untracked-files=all` plus `git log origin/main..HEAD`, never by filename or mtime: a fresh worktree checkout stamps every REPORT.md already in the repo with the spawn time, so "any REPORT.md newer than X" fires at once (false positive twice in one hour), and the CTO-event log timestamps are Contabo-local (Europe/Berlin), not UTC — converting them as UTC put one watch's start time 2 h in the future, so it never saw the real report · evidence: monitors for task-e3000e68 and task-23af5df3; the git-status watch saw the committed REPORT+REPLAY immediately · status: pending

## Field notes
- 2026-09-25 [MISSING] §remote — a worker spawned on a spoke (Contabo) has NO write path until its declared `touches` reach that box: `scripts/hook-self-repo-guard.py` reads them from the checkout's local `state/tasks.db`, which on a spoke is an unsynced copy, so it fails closed on every Write/Edit. Ship the touches with the spawn (task-378523bb adds a `.org-task.json` sidecar) before assigning any spoke task that must write · evidence: GH #180, task-43b6514d blocked_human on Contabo · status: pending
- 2026-09-25 [MISSING] §5b — arm the trust-prompt answer BEFORE `delegate_task`, not after: the kickoff wake's Enter lands ~6 s after spawn and picks "No, exit" before a post-spawn check can react. A background poller (tmux capture-pane every 0.2 s for "trust this folder" → `send-keys Down`, `Enter`) answered it at poll 11 and the worker lived; the three later spawns in the same session showed no prompt at all · evidence: task-27a80b13 (first spawn died silently, pid gone, tmux gone; respawn with the poller survived), tasks 7c2a89d1 / 4f4d4bd0 / 6b659049 no prompt · status: pending
- 2026-09-25 [MISSING] §2 brief — a brief that cites a GITIGNORED fixture (here `workflows/templates/object_info-snapshot.json`, a pod schema dump) must say where to copy it from: a fresh worktree does not have it. One worker copied it from the main tree; the other GENERATED its own from source and validated against that, which makes the check circular — caught only because its WORKLOG line said so · evidence: task-27a80b13 Skill learning, task-7c2a89d1 WORKLOG 21:04 + CTO-FEEDBACK.md · status: pending
- 2026-09-25 [MISSING] §remote — a remote worker's "done" is its branch + REPORT.md on origin, nothing else: it ends its own tmux after pushing (ORG_WORKER_FINISH) and the branch poller is OFF, so a Mac worker that waited on a Monitor/tmux signal sat idle 25 min after the spoke had already pushed. Wait with `git ls-remote --heads origin agent/<role>-<task>` (+ `git show origin/<branch>:REPORT.md`), then flip the row yourself · evidence: task-378523bb pane 04:13 vs branch f658b6c8 already pushed · status: pending
- 2026-09-25 [MISSING] §2 — the worktree is cut from `origin/main` when a remote exists, so on a repo whose local main is ahead and never pushed (ComfyRunpod: origin created 09-22, config still says local-only) the worker starts 23 commits behind, without the feature its brief builds on; it noticed and fast-forwarded itself. Before delegating on such a repo, either push main or tell the worker `git merge main` first · evidence: task-91e793eb base af81317 vs local main 49709e4; same on task-6b659049 · status: pending
- 2026-09-25 [WRONG] §3 brief — "test with synthetic data" is not isolation: the worktree gets a SYMLINK to the project's real `.env` (RUNPOD_API_KEY) and the pod state file lives in `$HOME`, so a worker that opened the Studio page locally fired real RunPod status calls through the page's SSE while the CEO had a live pod on the same account — a queue runner seeing an empty synthetic queue could as easily have called stop. For apps with a live external session: tell the worker not to run the app against the real `.env` (unset the key or point HOME/state at a temp dir), or to test by curl only · evidence: task-91e793eb Skill learning; CEO pod ek8i1p6i8qebq6 checked intact 09:2x · status: pending
- 2026-09-25 [COSTLY] §waiting — an orchestrator worker waiting on two spoke workers sent ~30 "Routine, waiting" dev_messages in 40 min (05:43–06:24), one turn each on a large context; a wait is ONE Monitor (or a `git ls-remote` loop in a single background shell) with a real condition, silent until it fires, and at most one status line to the CTO per state change · evidence: task-aae4f843 CTO-event log · status: pending
- 2026-09-25 [MISSING] §spawn — `mcp__org__delegate_task(host="contabo")` fails with "host 'contabo' (os=linux) has no remote launcher yet — only winbox is wired in Phase 1" and stamps the task `failed`: the MCP server process runs code older than tools/delegate.py (Contabo launcher landed in task-a5c0549d). Reset `status='pending'`, then delegate with the CLI: `ORG_SESSION_ID=<sid> .venv/bin/python -c "import asyncio; from tools.delegate import delegate_task; asyncio.run(delegate_task('task-X', host='contabo'))"` · evidence: task-1678d38e 2026-09-25 (MCP failed, CLI spawned pid 3630056) · status: pending
- 2026-09-25 [MISSING] §Spawn — on Contabo the org MCP server runs the LOCAL checkout, which can sit far behind origin (146 commits on 25 Sep, local main cannot pull over other sessions' dirty files): `delegate_parallel_tasks` resolved the Mac path (`No such file or directory: /Users/gob/...`) and `delegate_task(host="contabo")` answered "only winbox is wired in Phase 1" although the Linux launcher (task-a5c0549d) is on origin. Fallback that worked: Agent tool with `isolation: worktree`, first step `git fetch origin && git checkout -B <branch> origin/main`, brief file pushed to origin first, CTO reviews and merges the branch · evidence: task-c3e07fb1 delegate_log, task-e7cc2d83 · status: pending
- 2026-09-25 [WRONG] §2 (field note 2026-09-22 'a worktree is cut from LOCAL main') — `tools/worktree.py:create_worktree` now branches from `origin/<base>` whenever an origin exists (lines 215-224). On a repo whose `auto_push` is false, local main runs ahead of origin: ComfyRunpod's origin/main sat at af81317 (09-14) while local main was 9ad9c51, 38 commits ahead. So the worker built on a 2-week-old tree, re-created a `docs/STUDIO-API.md` that already existed and reported that `?return=saved` 'does not exist in the codebase'. Before reviewing a worker on an auto_push:false project, run `git -C <worktree> merge-base --is-ancestor main HEAD`. Fix in the tool: branch from local <base> when it already contains origin/<base>. · evidence: task-78c03f7b iteration 0 → rebase requested in CTO-FEEDBACK.md · status: pending
- 2026-09-25 [MISSING] §Spawn — Agent-tool fallback on Contabo (the org delegate cannot spawn LOCAL workers there): the tool's worktree is cut from the shared checkout's LOCAL HEAD, which can lag origin by hours, so push the brief to origin BEFORE spawning and tell the worker to `git fetch origin && git reset --hard origin/main` inside its own worktree first; the worktree also has no `.venv`, so the verification line must name `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` · evidence: Run Inbox P1b worker fell back to the scratchpad copy of its brief (2026-09-25); the phase-3 restore worker hit the missing venv the day before · status: pending
- 2026-09-25 [COSTLY] §Spawn (Console tests on Contabo) — `/opt/node-v22/bin/npx vitest run` still runs node 20: npx's `#!/usr/bin/env node` resolves from PATH, and `NODE_OPTIONS=--experimental-sqlite` then aborts ("not allowed in NODE_OPTIONS"). The line that works, put it in the brief verbatim: `( cd <worktree> && PATH=/opt/node-v22/bin:$PATH NODE_OPTIONS=--experimental-sqlite npx vitest run )` · evidence: Run Inbox P1a worker · status: pending
- 2026-09-25 [WRONG] §3 "Serialize logical conflicts" — two briefs written in parallel against ONE API contract (Run Inbox P1a Console + P1b Agents-Core) drifted in three places (the C-level list, a role-claim gate vs a token-class gate, the letter file name) and the corrections had to be relayed mid-task to both. When two parallel briefs share a contract, the contract lives in one file (docs/design/<feature>/CONTRACT.md) that both briefs link to, and neither brief restates it · evidence: P1a report "Where I departed from the brief", P1b open questions 1-6 · status: pending
- 2026-09-25 [MISSING] §2 brief — a brief that says "append to `WORKLOG.md` in the worktree root" gets `WORKLOG.md` + `REPORT.md` COMMITTED at the repo root: `merge_task` then fails the touches check (2 extra files) and two tasks' root REPORT.md collide at merge. Say `docs/reports/<task-id>/REPORT.md` + `WORKLOG.md` in the brief and add `docs/reports/<task-id>/` to `touches` (patch the DB row after `create_task` when the id is not known while writing) · evidence: task-9f6fec26 and task-a40d2d8e both needed a `git mv` commit before merging; T3–T5 briefs patched in tasks.db · status: pending
- 2026-09-25 [COSTLY] §6b — the Monitor script in this section keys its change detection on the WORKLOG line count, so every worker step wakes the CTO (7 turns in 10 min on task-9f6fec26, each on a 100k+ context). Emit only on status/alive/dialog changes plus a single STALL line when the worklog has not grown for 15 min; the worklog count rides along as a field, never as a trigger · evidence: monitors b7efdlsgy (chatty) vs blsbgqhrb (quiet) in session cto-ce3535eb · status: pending
- 2026-09-25 [MISSING] §Spawn — `delegate` refuses under the ADR 0030 disk floor (5.0 GB on the Mac) and queues the task ("queued for disk (N ahead)", auto-spawns when space clears); a sparse Core worktree is ~180 MB, so plan for it: `df -h /` before creating a wave, and know that Green cache clean-up on this Mac yields <1 GB — the big consumers are live Chrome code-sign clones (1.4 GB each) and other sessions' review-state worktrees (0.9 GB) that are not yours to remove · evidence: task-9ea68924 / 17f60167 / 9c6daaf7 queued at 4.9 → 2.9 GB free · status: pending
- 2026-09-25 [MISSING] §6b — remote (Contabo) workers stop on a Claude Code first-run prompt "Teach auto mode about your environment? 1 Yes 2 Not now 3 Don't show again · Enter to confirm". The pid and tmux stay alive and the pane shows no error. `tmux send-keys -t mooniex-<task> 3` clears it; the A/B watcher now does this itself. Also: a remote worker's last pane line is the literal `Run %ORG_WORKER_FINISH%` (placeholder not substituted) and its status stays `in_progress` after it pushed. Watch for that string, or for the pushed branch, not for the status · evidence: task-1a5eb073, task-9a4f1029 2026-09-25 · status: pending
- 2026-09-25 [MISSING] §3 brief — a headless A/B arm that installs a hook BINARY must put it on the child process's PATH: RTK rewrites commands to bare `rtk …` (argv[0] is not its install path), so with the binary only under `tools/rtk_ab/bin` every rewritten command died `exit 127` and the smoke run burned 2× tokens working around it. Say "prepend the bin dir to PATH for the `claude -p` child" in the brief · evidence: task-9ea68924 smoke run B-0, docs/ops/rtk-ab-2026-09-25.md · status: pending
- 2026-09-25 [MISSING] §3 brief (hooks) — UserPromptSubmit/PreToolUse hooks in the same settings array run in PARALLEL, not in order (code.claude.com/docs/en/hooks, verified live): a blocking hook cannot rely on array order to protect a sibling hook's destructive work (`hook-inbox.py` drains the mailbox). A hook-writing brief must say so and ask for a non-destructive peek/exemption · evidence: task-a40d2d8e report, `_has_pending_mail()` in scripts/hook-cache-cold-warn.py · status: pending
- 2026-09-25 [MISSING] §3 brief (hooks) — a worker's own env carries `WORKER_TASK_ID`, so its manual smoke test of a hook that exempts workers passes silently; tell hook briefs to run the manual smoke with `env -u WORKER_TASK_ID` and a non-worktree cwd · evidence: task-17f60167 Skill learning · status: pending
- 2026-09-25 [MISSING] §3 brief — a worker that WebFetches docs trips `scripts/hook-research-gate.py` (ADR 0028 §6: write `mooniex:research/*.md` after a web search) but the developer role has no wiki write path; either the CTO pre-fetches the doc facts into the brief, or the brief says to quote the fetched facts in REPORT.md and that the CTO files the research note · evidence: task-9f6fec26 Skill learning · status: pending
- 2026-09-25 [MISSING] §3 brief — a sparse worktree has no `.venv`; say `.venv/bin/python` means the MAIN checkout's absolute path (`/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`) so the worker does not hunt for it (three workers noted it today; the RTK A/B runs spent 7–10 Bash calls per run on that hunt) · evidence: task-9f6fec26, task-9ea68924 (env-discovery churn) · status: pending
- 2026-09-25 [MISSING] §Spawn — on Contabo, `delegate_task` runs whatever code the shared checkout `/opt/MoonieXHQ/Agents/Core` has, and that main was 214 commits behind origin (it lacked the Contabo spoke 6a183fa8), so every spawn failed three different ways: `browser cap: 0/0` (config read once per MCP-server process by lru_cache, so a hosts.yaml edit needs a server restart), `no remote launcher yet` (host=contabo), and `FileNotFoundError /Users/gob/…` (no host → Mac path). Check `git -C /opt/MoonieXHQ/Agents/Core rev-list --count main..origin/main` before the first spawn on Contabo; when it is not 0, a worker cannot be spawned there until the tree is synced, and an in-session Agent subagent with the same brief is the fallback · evidence: task-a8152277 (cancelled), cto-885ae930 · status: pending
- 2026-09-26 [MISSING] §2 worktree — `tools/worktree.py:provision_worktree` symlinks the canonical repo's REAL `.env` into every worker worktree. On ComfyRunpod the studio's `loadRootEnv()` then lets that `.env` override the fake keys a test sets, so an 'offline' test made 2 paid NinjaChat calls ($0.16). RunPod could have been hit too. Opt-out now exists: put a `.worktree-no-env` marker in the repo (Agents-Core 75604322; ComfyRunpod 8ad6899). Before spawning on a repo whose `.env` holds spending keys, check the marker is there · evidence: task-e59b65e3 · status: pending
- 2026-09-26 [COSTLY] §6b parallel workers — two ComfyRunpod workers both used `next dev -p 4199`. The second one's review test silently hit the first worker's server, and 17 checks failed on the wrong code. Give each parallel task its own port in the brief (e.g. 4190 + n), and on review run `lsof -iTCP:<port>` + the cwd before trusting a failure · evidence: task-e59b65e3 review vs task-4c62e072 · status: pending
- 2026-09-26 [MISSING] §6b — a winbox worker (task-dd118c0a) sat 31 min with its claude.exe alive, no HEARTBEAT file and no transcript anywhere: it never reached its first tool call (most likely a startup prompt nobody can answer from ssh). Its claude.exe runs from C:\Users\passg\.local\bin while the worktree is under C:\Users\UsEr, so look for its transcript and trust flag under both profiles. Cheap check at +5 min: `ssh winbox "type <worktree>\HEARTBEAT"` — missing = not started; kill the PID alone (never `taskkill /T`) and re-run the job another way · evidence: task-dd118c0a cancelled 2026-09-26, the same job finished by an in-session agent over ssh (1bab51c4) · status: pending
- 2026-09-26 [COSTLY] §3c brief facts — WebFetch's summariser NORMALISED an enum's casing: it reported Runware `outputType` as "url"/"base64"/"datauri" and my brief passed that on; the real values are `base64Data`/`dataURI`/`URL` (official SDK `IOutputType`). The worker caught it; a worker that trusted the brief would have failed only on the first PAID call. For any enum, field name or casing in a brief, quote it from the SDK source / raw schema (`curl raw.githubusercontent.com/...types.ts | grep`), not from a WebFetch summary · evidence: task-7affa61d report + Runware/sdk-js types.ts:46 · status: pending
- 2026-09-26 [MISSING] §3c.9 — the same trap hits a C-LEVEL pane: a script's `tmux send-keys … Enter` wake (scripts/infisical/after_login.sh → cto-885ae930) typed while the session was mid-turn sat on the ❯ line for 8+ hours, survived a `/compact`, and a `send-keys C-u` from a tool call did not remove it — it is a queued message, not editor text, and it fires STALE after a later turn (this one said "apply FAILED" from a run that had since been fixed and re-run green). A wake into a C-level pane must carry its timestamp + the log path so the reader can tell it is old, and the sender should re-capture the pane after 5 s to see whether it was submitted or queued · evidence: cto-885ae930 pane 2026-09-26 10:4x UTC, state/logs/infisical-p1.log · status: pending
- 2026-09-26 [MISSING] §3c — a developer building a Playwright tool on a shared CDP Chrome (:9230) hunted for a UI control with ~30 throwaway exploration scripts; each opened a new tab and none closed it (11 tabs open, CEO: "Worker วนลูป เปิด tab ไม่หยุด"), and it spent 12 screenshots against a budget of 10. A browser brief must say: reuse one tab or close every tab you open in a `finally`; explore by dumping text/aria-labels, not screenshots; exploration is time-boxed (20 min), then report what was tried · evidence: task-cfdc75a8, CDP /json/list 11 pages at 19:0x · status: pending
- 2026-09-26 [MISSING] §3c.9 — a line sent to a worker pane can land with the footer "Removed 1 invisible character · review and press Enter to send" and sit unsubmitted; one more Enter (or C-m) submits it. Capture the pane after every send and look for that footer as well as text left on the `❯` line · evidence: task-5a0ed790 · status: pending
- 2026-09-26 [MISSING] §3c brief — a ComfyRunpod (comfy-runpod-worker) worktree has no `studio/node_modules` and no `workflows/templates/object_info-snapshot.json` (both gitignored; the provisioner links only a repo-root node_modules), and Next 16 Turbopack refuses a symlinked node_modules ("points out of the filesystem root"). Two studio workers in a row lost time re-discovering both. Put in every studio brief: symlink both from the main checkout, add `/studio/node_modules` to `.git/info/exclude`, spawn `next dev --webpack`. Five of six studio test scripts now pass `--webpack`; `scripts/test_venice_images.py` still does not. Real fix = the worktree provisioner links them · evidence: task-c794b73a (7b834a5), task-6e65b416 (531d5f5, REPORT "Environment fix") · status: pending
