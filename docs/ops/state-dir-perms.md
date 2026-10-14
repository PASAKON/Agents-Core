# state/ permissions on Contabo (sticky bit, read-only locks)

Follow-up to PR #283 review (OrgRestructure M10b, Agents-Core #272).

## What is wrong

`state/`, `state/locks/` and `state/logs/` are `drwxrwsr-x root:secretary`: group-writable, setgid, **no
sticky bit**. The `secretary` user (mooniex-secretary, mooniex-secretary-waker) can rename, unlink or
replace any entry in them, including root-owned files it cannot write. Root readers of `state/locks/*`
(the rename service, escalation_watch, live_sessions) defend with `ls.read_lock`: O_NOFOLLOW, O_NONBLOCK,
regular file, ≤256 B, root owner, no group/other write, one link. That stops a swapped-in file, but not a
root-owned `.project` being moved over another one (a label swap between two PHs).

## What uses the write bit (measured 2026-10-14)

- `state/locks/`: no file and no directory is owned by `secretary`; every writer runs as root
  (spawn-ph, spawn-cto, cxo-claude). The secretary code only reads `.spawned_by`. → the group write
  bit has no user.
- `state/` top level: secretary owns `decisions/`, `skill-usage.log`, `secretary_waker/`,
  `secretary_images/`, `inbox/`. It writes only inside these and creates new entries of its own. Under a
  sticky bit it keeps all of that: it may still create entries and rename or delete its own ones. It
  loses only the right to rename or delete root-owned entries, which is the point.
- `journalctl -u mooniex-secretary -u mooniex-secretary-waker --since -7d`: 0 permission errors before
  the change, the baseline to compare against after.

Not covered here: `state/inbox/` is secretary-owned with root-owned, group-writable mailboxes inside. A
mailbox's letters can be swapped the same way. That needs its own design (who may drop a letter where),
not a chmod.

## Run card (CTO raises it; host contabo)

```
cd /opt/MoonieXHQ/Agents/Core && stat -c '%A %U:%G' state state/locks && test -z "$(find state/locks -user secretary -print -quit)" && chmod g-w state/locks && chmod +t state && stat -c '%A %U:%G %n' state state/locks
```

Expected: `drwxrwsr-t root:secretary state` and `drwxr-sr-x root:secretary state/locks`. The `find`
guard stops the card if a secretary-owned file appeared in `state/locks` since this was measured.

Check afterwards (24 h): `journalctl -u mooniex-secretary -u mooniex-secretary-waker --since -24h | grep -ciE "permission denied|EPERM|EACCES"` stays 0, and the secretary still answers.

Roll back: `chmod g+w /opt/MoonieXHQ/Agents/Core/state/locks && chmod -t /opt/MoonieXHQ/Agents/Core/state`.

Not touched: `state/logs/` (secretary may append there; measure before changing it).
