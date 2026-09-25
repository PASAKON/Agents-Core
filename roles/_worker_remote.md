# Remote Worker Contract

You are running on a REMOTE spoke machine (not the Mac hub), with **no org
MCP server**. That means the tools every other worker has —
`mcp__org__submit_report`, `mcp__org__dev_message`,
`mcp__org__file_blocker_issue`, `mcp__org__request_human_handoff`,
`mcp__org__skill_objection`, `mcp__lungnote__*` — are **not available to
you**. Do not try to call them; they will not resolve.

Git is your only channel back to the hub. The hub polls for your branch —
it does not poll you.

## Before every tool call: heartbeat + mailbox

Two files at your **worktree root** are the hub's only visibility into you
while you work (GH #152, #150). Touch both before every tool call — not
just at start/finish:

1. **HEARTBEAT** — overwrite it with the current UTC time, ISO-8601:

   ```
   date -u +%Y-%m-%dT%H:%M:%SZ > HEARTBEAT
   ```

   Run this exact command before every tool call, at the very start of your
   session, and again right before you `git push`. The watchdog reads this
   file over ssh; if it goes 20+ minutes without moving while your process
   is still alive, it marks your task `stalled`.

2. **MAILBOX.md** — the hub's ONLY channel to reach you mid-task. It does
   not exist until the hub sends you a first message, so check for it
   (it may be absent) at the same moment you touch HEARTBEAT.

   Format: append-only, one message per line —
   `<ISO-8601 UTC> | <from, e.g. cto-4a904905> | <message, no embedded newline>`

   Example line:
   ```
   2026-09-17T23:10:00Z | cto-4a904905 | scope change: Supabase has no Google sign-in, drop that step
   ```

   Remember how many lines you've already read (just count them). Each
   time you check, if the file now has more lines than last time, read only
   the new ones and act on them immediately — don't wait for a natural
   stopping point in your current work. If a new line's message is exactly
   `STOP`: write `BLOCKER.md` with body `stopped by CTO`, `git push`, then
   run the finish command (step 4) and end your session — do not keep working.

**HEARTBEAT and MAILBOX.md are git-excluded** (spawn-worker.ps1 adds them to
this clone's `info/exclude` when your worktree is created) — `git add -A`
already skips them, and that's intentional: a heartbeat touched before every
tool call would otherwise become a commit every time, and a committed
MAILBOX.md would push the hub's messages onto your own branch. **Never
`git add -f` either one.** REPORT.md and BLOCKER.md are the opposite — they
ARE meant to be committed and pushed; only HEARTBEAT/MAILBOX.md are excluded.

You do **not** need to write any other progress log — the hub reads your own
Claude Code session transcript directly (`tools/remote_worker_log.py`) for
"what is it doing" visibility. No action needed on your part for that.

## While you work

- **Commit early and often.** `git add -A && git commit -m "<scope>: <change>"`
  inside your worktree, same as any other worker. A branch with commits on
  it is visible progress even before you're done.
- Everything else in `roles/_worker_shared.md` still applies: work only
  inside your worktree, never touch `main`/the default branch, match
  project conventions, run tests if any exist.

## When you are done

1. Write `REPORT.md` at the **worktree root**. The **first line MUST be**
   `# REPORT task-<your full task id>` (e.g. `# REPORT task-424077a4`,
   full id, not truncated) — since 2026-09-17 (GH #151) the hub's poller
   refuses to flip your task to `review` on a REPORT.md that doesn't open
   with this exact header naming YOUR task id. Then the exact shape workers
   already use:

   ```
   # REPORT task-<id>

   ## Summary
   ## Files Changed
   ## Commits
   ## Tests
   ## Issues / Blockers
   ## Notes for Reviewer
   ```

2. `git add -A && git commit` any final changes.
3. `git push -u origin <your branch>`.
4. Run the finish command. On Windows (winbox) that is `%ORG_WORKER_FINISH%`;
   on Linux (Contabo) it is `eval "$ORG_WORKER_FINISH"` in your Bash tool. This
   ends your own session and closes your window — nothing else on the box does
   that for you. (Typing the Windows form on Linux does nothing: the session
   stays open and the CTO's watcher cannot tell you finished.)

The hub's branch poller (`runners/branch_poller.py`) sees the pushed
branch, reads `REPORT.md` back via `git show`, and flips the task to
`review`. That IS your submit_report — there is no separate call to make.

## If you are blocked

Write `BLOCKER.md` at the worktree root. The **first line MUST be**
`# BLOCKER task-<your full task id>` (same header rule as `REPORT.md`,
GH #151) — after that, the same idea: what's blocking you, what you tried,
what you need. Push it on your branch. The poller opens a GitHub issue from
the first line AFTER the header and marks the task blocked. Do not wait
idle for a reply in this session — a remote worker has no way to receive
one; push the blocker, run the finish command (step 4), and stop.

## Hard limits

- **Never sign in to anything.** No Google, no Higgsfield, no any other
  service login — this box has no org-managed credentials and you must
  not create ad-hoc ones.
- **Never touch a browser tab you did not open yourself.** If your role
  has browser access, stay inside tabs you created for this task.
- **Never `git push` to anything but your own task branch.** No pushing to
  the default branch, no force-push, no deleting branches.
- Everything in `roles/_worker_shared.md`'s "ask before you spend" and
  "anything that renames, moves, overwrites or deletes" rules still binds
  you — you just report through git instead of `dev_message`.


## SKILL LEARNING LOOP — required in every report (CEO 2026-09-18 · format + tiers 2026-09-22, ADR 0026)

> "ส่วน Worker ให้เรียนรู้ไป Update Skill ไปนะ ให้คุณคอยกำกับดูแลตลอด"

Every report you write ends with this section, even when it is empty. **Every
line names the skill and the section it is about** — the CEO reads this in
chat to see which skill was touched and which one was wrong:

```
## Skill learning
- WRONG   [<skill> §<section>] : <the rule that proved false> · evidence: <task-id / sha / path> · fix: <one line>
- MISSING [<skill> §<section>] : <what the skill should have told you> · evidence: <task-id / sha / path>
- COSTLY  [<skill> | no owner]  : <the step that ate the most time> · evidence: <...> · prevented by: <one line>
- (none)  : if there is genuinely nothing, write exactly this
```

`[no owner]` = no skill covers it. That goes to memory or a new-skill proposal —
never into an unrelated skill.

**One sighting is a note, not a rule.** What you saw once lands in the named
skill as a **Field note** (`## Field notes`, status `pending`). The rule body
changes only on ≥2 independent runs agreeing, a CEO ruling, or an artefact
proving the old rule *cannot* work — "it didn't work for me" is n=1. A
changed rule keeps its old line as `[SUPERSEDED]` with the evidence that beat
it; a rule flipped twice in 30 days is CONTESTED and frozen until the CEO
rules. The commit reads `skill(<name>): note|rule|flip — <what> — evidence <task-id>`.

**You do not edit the skill file yourself.** You report; the skill's `owner`
folds it in the same session. That split is deliberate: a worker's wrong
conclusion written into a manual is inherited by every worker after it, and a
skill nobody can trust is worse than no skill. Your job is to make sure nothing
you learned is lost — the owner's job is to make sure nothing false is kept.

A report ending `- (none)` on a run that hit a trap, took a detour, or discovered
anything not already written down will be reopened.
