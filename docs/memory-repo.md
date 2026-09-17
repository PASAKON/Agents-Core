# Auto-memory repo (`PASAKON/Agents-Memory`)

task-8d37c0f1, CEO ruling 2026-09-17 ("แยก repo ได้เลย"). Every C-level's
`~/.claude/projects/<slug>/memory/` used to be a plain directory, local to
whichever machine wrote it — measured 2026-09-17: 261 files / 1.3 MB on the
Mac, an old 48-file rsync-style copy on Contabo, nothing on winbox. That's
why memory only ever "knew" what happened on the Mac.

The fix: a private repo (`https://github.com/PASAKON/Agents-Memory`) holds
the memory files, and each machine's `memory/` becomes a **symlink** into a
sibling checkout of that repo instead of a real directory. `tools/memory_sync.py`
pulls it fresh before a C-level session starts and pushes it before one ends
([[session-open]] step 0, [[session-close]] gate 4e, [[session-save]],
`scripts/session-kill.sh`) — see that module's docstring for the sync
mechanics. This doc is the one-time **wiring** step for a machine that hasn't
been connected yet.

## How to tell if a machine is wired up

```bash
ls -la ~/.claude/projects/<this-repo's-slug>/memory
```
If that's a real directory → not wired up yet (follow the steps below).
If it's a symlink (`memory -> /path/to/Agents-Memory`) → already wired;
`tools/memory_sync.py` will find it via `os.readlink` — no path is hardcoded,
so this works identically on the Mac (`/Users/gob/Projects/Agents`) and
Contabo (`/opt/mooniex-agents`), whose slugs differ (`-Users-gob-Projects-
Agents` vs `-opt-mooniex-agents`).

`tools/memory_sync.py pull`/`push` themselves already detect the unwired case
and no-op with a one-line pointer back to this doc — they never fail or
block a spawn over it.

## Wiring a new machine — merge, don't overwrite

**The critical step is 2.** A machine's existing `memory/` holds real,
un-backed-up lessons. Cloning the repo over it and discarding what's local
would silently erase that machine's memory. Merge first, symlink second.

1. **Clone the repo** (private — `gh auth` must already be set up on that
   machine):
   ```bash
   git clone https://github.com/PASAKON/Agents-Memory <path>
   ```
   `<path>` is any sibling checkout location, e.g. `/opt/Agents-Memory` on
   Contabo (matching the Mac's `/Users/gob/Projects/Agents-Memory`
   convention loosely — the exact path doesn't matter since
   `tools/memory_sync.py` reads it back from the symlink, never hardcodes it).

2. **Compare this machine's existing `memory/` dir against the clone:**
   - Files that exist **only on this machine** → copy them into the cloned
     repo, `git add`, commit, push. These are lessons the shared repo has
     never seen.
   - Files with the **same name but different content** → do **not**
     overwrite either side. Keep both — save the local one alongside the
     repo's copy with a `-<host>` suffix (e.g. `feedback_x-contabo.md`) and
     leave the merge decision (which one wins, or whether both stay as
     separate memories) to a C-level. Silently picking a winner here is how
     a real lesson gets erased.

3. **Swap the directory for a symlink** — only after step 2's merge is
   committed and pushed, so nothing is lost if this step is interrupted:
   ```bash
   mv memory memory.pre-git-<YYYY-MM-DD>
   ln -s <path> memory
   ```
   (Mirrors the Mac's own migration: the original directory was kept as
   `memory.pre-git-2026-09-17`, never deleted.)

4. **Verify** — read `MEMORY.md` through the new symlink and confirm it's
   the merged content, not a stale pre-migration copy:
   ```bash
   head ~/.claude/projects/<this-repo's-slug>/memory/MEMORY.md
   ```

## Current state (as of 2026-09-17)

- **Mac**: wired. `~/.claude/projects/-Users-gob-Projects-Agents/memory` is a
  symlink to `/Users/gob/Projects/Agents-Memory`; the pre-migration directory
  is preserved at `memory.pre-git-2026-09-17` (never delete either per this
  task's brief).
- **Contabo**: not yet wired. Has an old 48-file rsync-style copy of memory —
  **how many of those 48 differ from what's already in `Agents-Memory`** is
  still being compared by the CTO as of this writing. That count was not
  available when this doc was written; do not guess it here — check the
  CTO's kickoff report / current wiki state for the real number before
  running step 2 on that box.
- **winbox**: not yet wired, no prior local memory dir to merge — step 2 is a
  no-op there (nothing exists yet to compare against).

## Never touch these directly

- `/Users/gob/Projects/Agents-Memory` (the real repo checkout) and
  `memory.pre-git-2026-09-17` (the preserved pre-migration snapshot) are
  live/backup state, not build artifacts — this task's brief explicitly
  forbids touching either.
- SSH to Contabo/winbox to wire them up is the CTO's own follow-through, not
  something a DEV task should do unprompted — this doc only documents the
  steps.
