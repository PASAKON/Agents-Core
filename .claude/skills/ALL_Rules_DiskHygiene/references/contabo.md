# Contabo VPS (`mooniex-vps`) — 72 GB disk, production

Runs claudeflow, the secretary, the LINE bots and the Console. **Production.**
The Green list runs here without asking, as on every machine (CEO 2026-09-28:
"ตามนั้น"). Anything else deleted here: propose the command, get the CEO's go.

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

## Green here — no asking

```bash
docker builder prune -f                 # 12.9 GB on 2026-09-23 — build cache only, never images or volumes
apt-get clean                           # ~123 MB
pip cache purge                         # 287 MB on 2026-09-28
npm cache clean --force                 # ~/.npm/_cacache; ~/.npm/_npx is its own rm -rf
```

None of it touches a running container, an image in use, or a volume. The journal is Green too
since 2026-09-28 ("log บน Contabo เอาออกได้เลย"): `journalctl --vacuum-size=500M` (760.8 MB → 500 MB that day).
[SUPERSEDED 2026-09-28] "Not Green, so still his go: `journalctl --vacuum-size=500M` (~3.3 GB on
2026-09-10) — old logs do not rebuild."

**Worktrees are the big consumer, and they are full checkouts here.** On 2026-09-28
none of the 22 worktrees had a sparse-checkout: developer ones ~0.93 GB each,
`worktrees/` 11 GB, the harness's `.claude/worktrees/` 6.5 GB. A merged, clean one
is Green for its own session; another session's goes to its owner (contract step 6).

## Never touch here

- The 2 Docker **volumes** — they are the live databases and state of running services.
- Any **image that is active**; `docker image prune -a` would pull them all again
  on the next deploy. Use `docker builder prune`, which is a different thing.
- Login state (parent SKILL, "Never Green") — ask the CEO first: the Console's
  Browser Home profiles `/opt/MoonieXHQ/Projects/MoonieX/Console/data/browser-homes/<id>/profile/`,
  `/root/.claude/.credentials.json` and the one under `/opt/claude-usage-monitor/`,
  `/root/.config/gh/hosts.yml`, `/root/.config/mooniex/` (Run Inbox token, YouTube OAuth),
  the Drive brokers' `/home/driveup/.drive.env` and `/home/photoup/.drive-photo.env`.
- Contabo's wiki copies `/opt/MoonieXHQ/Agents/Rules` and `/opt/MoonieXHQ/Agents/Wikis`
  (old `/opt/agents-wikis`, `/opt/mooniex-wikis` are links to them) are **rsync
  snapshots, not git checkouts** — nothing to pull, nothing to push, and a write
  there is silently overwritten by the next sync. Treat as read-only.
- `/tmp/claude-0/<slug>/<other session uuid>/` — another session's scratch.
- Anything under a service's data directory while that service is running.

## Backups from this box

VPS backups land on the Mac under `~/Backups/**` and go to Drive under
`Archive/Backups/<same relative path>` per the drive-archive gate. Keep the folder
names and dates; they are how a restore is found.
