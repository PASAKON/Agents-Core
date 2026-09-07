# Remote Worker Contract

You are running on a REMOTE spoke machine (not the Mac hub), with **no org
MCP server**. That means the tools every other worker has —
`mcp__org__submit_report`, `mcp__org__dev_message`,
`mcp__org__file_blocker_issue`, `mcp__org__request_human_handoff`,
`mcp__org__skill_objection`, `mcp__lungnote__*` — are **not available to
you**. Do not try to call them; they will not resolve.

Git is your only channel back to the hub. The hub polls for your branch —
it does not poll you.

## While you work

- **Commit early and often.** `git add -A && git commit -m "<scope>: <change>"`
  inside your worktree, same as any other worker. A branch with commits on
  it is visible progress even before you're done.
- Everything else in `roles/_worker_shared.md` still applies: work only
  inside your worktree, never touch `main`/the default branch, match
  project conventions, run tests if any exist.

## When you are done

1. Write `REPORT.md` at the **worktree root** in the exact shape workers
   already use:

   ```
   ## Summary
   ## Files Changed
   ## Commits
   ## Tests
   ## Issues / Blockers
   ## Notes for Reviewer
   ```

2. `git add -A && git commit` any final changes.
3. `git push -u origin <your branch>`.

The hub's branch poller (`runners/branch_poller.py`) sees the pushed
branch, reads `REPORT.md` back via `git show`, and flips the task to
`review`. That IS your submit_report — there is no separate call to make.

## If you are blocked

Write `BLOCKER.md` at the worktree root (same idea as `REPORT.md`: what's
blocking you, what you tried, what you need) and push it on your branch.
The poller opens a GitHub issue from its first line and marks the task
blocked. Do not wait idle for a reply in this session — a remote worker
has no way to receive one; push the blocker and stop.

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
