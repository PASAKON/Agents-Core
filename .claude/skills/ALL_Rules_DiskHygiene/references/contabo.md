# Contabo VPS (`mooniex-vps`) — 72 GB disk, production

Runs claudeflow, the secretary, the LINE bots and the Console. **Production**:
read-only diagnostics over ssh are pre-approved, every write is not. Propose the
command, get the CEO's go, then run it.

## State (`/dev/sda1`, 72 GB)

| Date | Free | What moved it |
|---|---|---|
| 2026-09-10 | 31 GB | baseline; housekeeping, not a fire |
| 2026-09-23 | 17 → 42 GB | the easy wins below on the CEO's go (build cache 10.31 GB, journal → 500 MB, pip 539 MB), then `/root/idm-packs` (12.29 GB, a 47/47 md5 copy of Drive `BACKUP/CookieRun Backup/colab_packs`) deleted — `docs/ops/contabo-hq-migration-plan-2026-09-23.md` |
| 2026-09-28 | **7.9 GB** | Agents-Core worktrees ~17.5 GB (`worktrees/` 11 GB for 12, `.claude/worktrees/` 6.5 GB for 7), `/tmp/claude-0` 6.3 GB, `Work/` 3.2 GB; build cache back to only 0.8 GB |

Where the 41 GB sat on 2026-09-10:

| Path | Size | What |
|---|---|---|
| `/var/lib` | 19 GB | almost all Docker |
| `/var/log` | 4.1 GB | mostly the systemd journal |
| `/root` | 5.8 GB | incl. `/root/restore` 2.4 GB, `/root/projects` 1.8 GB |
| `/usr` | 5.0 GB | the OS |
| `/opt` | 2.8 GB | `mooniex-agents` 2.4 GB, `node-v22`, `mooniex-console`, wikis |

Docker on this box, unlike the Mac's, is **live production**:

| | |
|---|---|
| Images | 9, 14.93 GB, 7 active — only 230 MB reclaimable |
| Containers | 8, all running |
| Volumes | 2, 1.548 GB, both in use — **these hold real data** |
| Build cache | 131 entries, 14.82 GB, **12.95 GB reclaimable** |

## The easy wins — safe, but ask first

```bash
docker builder prune -f                 # ~12.9 GB — build cache only, never images or volumes
journalctl --vacuum-size=500M           # ~3.3 GB — keeps the most recent logs
apt-get clean                           # ~123 MB
```

They ran on 2026-09-23; re-measure before proposing them again. None of it
touches a running container, an image in use, or a volume.

## Never touch here

- The 2 Docker **volumes** — they are the live databases and state of running services.
- Any **image that is active**; `docker image prune -a` would pull them all again
  on the next deploy. Use `docker builder prune`, which is a different thing.
- `/root/restore` (2.4 GB) — unidentified; ask the CEO what it is before assuming
  it is a leftover.
- Contabo's wiki copies `/opt/agents-wikis` and `/opt/mooniex-wikis` are **rsync
  snapshots, not git checkouts** — nothing to pull, nothing to push, and a write
  there is silently overwritten by the next sync. Treat as read-only.
- Anything under a service's data directory while that service is running.

## Backups from this box

VPS backups land on the Mac under `~/Backups/**` and go to Drive under
`Archive/Backups/<same relative path>` per the drive-archive gate. Keep the folder
names and dates; they are how a restore is found.
