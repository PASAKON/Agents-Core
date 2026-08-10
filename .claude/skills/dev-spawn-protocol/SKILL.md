---
name: dev-spawn-protocol
owner: CTO
origin: mooniex-org
scope: >-
  Spawn-time checklist only — visible iTerm tab, full task-id title, kickoff ping,
  touches lock, auto-close on done. Does not create the task or review DEV output.
  Enforces IRON-RULES §29.
description: Required steps when CTO spawns a DEV agent. Trigger on /dev-spawn-protocol and before any delegate_task or DEV spawn, or when the user says "spawn dev", "delegate", "kick off the dev", "start the developer".
---

# DEV Spawn Protocol

Required steps every time CTO spawns a DEV. Memory rule (CEO 2026-05-19, IRON-RULES §29): visible animation + mandatory kickoff ping. Skipping any step is a P0.

## Pre-spawn

### 0. Force Claude when a cheap miss is expensive (CEO 2026-08-10)
`DEV_MODEL_PROVIDER=auto` routes on **quota headroom alone** — it cannot see how
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
value falls back to normal routing (`lib.config.dev_provider_overrides`).

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
