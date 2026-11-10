# BLOCKER task-ca79b69b

## What is blocking
The task text says "read /opt/MoonieXHQ/Work/ghost-pilot/BRIEF-newchannel.md fully first". That file is a Contabo path. This worker runs on winbox (host GoB, Windows), and the brief is not here:
- `/opt/MoonieXHQ/Work/ghost-pilot/` does not exist (`/c/opt/MoonieXHQ/Work/` holds only `khaohom-survival`).
- `git fetch origin` then searching origin/main for "ghost-pilot" / "ghost channel" / any file named *ghost* finds nothing.
- No MAILBOX.md exists, and this box has no org MCP (no wiki_read).

The task description itself only says: "new ghost channel, park the old one", CEO order Q-20261110-1404-34fb, hard limits (live MT5 EA, no reboot, PC lease, post nothing, delete nothing), needs Chrome CDP on winbox signed-in homes plus relay requests. It does not say which channel, which platform, which accounts, or what the browser steps are.

## What I did
Nothing in the browser. I did not guess the scope: this job runs on signed-in sessions of the CEO's accounts and touches a PC lease on a box running a live-money EA, so a guess is not acceptable.

## What I need
Either (a) copy BRIEF-newchannel.md into the repo (a branch or origin/main) or append its text to MAILBOX.md in this worktree, or (b) re-delegate on Contabo where the file exists. Then re-spawn the task.

## Not checked
Chrome connectivity, PC lease state and the signed-in homes were not examined, since the job is undefined without the brief.
