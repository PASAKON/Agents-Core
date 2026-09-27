# Contabo VPS (`mooniex-vps`) — 72 GB disk, production

Runs claudeflow, the secretary, the LINE bots and the Console. **Production**:
read-only diagnostics over ssh are pre-approved, every write is not. Propose the
command, get the CEO's go, then run it.

## State measured 2026-09-10

| | |
|---|---|
| `/dev/sda1` | 72 GB, 41 GB used, **31 GB free (58%)** |
| Not critical | there is room; this is housekeeping, not a fire |

Where the 41 GB sits:

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

Roughly **16 GB back**, taking the box from 31 GB to ~47 GB free. None of it
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
