# Contabo → `/root/MoonieXHQ` migration plan — DRAFT

Status: **all 5 steps executed** (0–4 on 2026-09-23, step 5 `Agents/Core` on 2026-09-24). What is left is removing the compat links after a clean week.
Author: CTO 0e8d80b8, 2026-09-23. Survey read-only over ssh the same day.

## Why

CEO 2026-09-23: all work on Contabo lives in **one folder**, named exactly like the
Mac HQ — the rules already written in `MoonieXHQ/MAP.md` and IRON §54:
`MoonieXHQ` (no space), PascalCase, no hyphens, `Projects/<Brand>/<Suffix>` ⇔
`PASAKON/<Brand>-<Suffix>`. Tools that are installed separately stay outside.

Today the same repo has a different path on each machine (`/opt/mooniex-agents` vs
`~/MoonieXHQ/Agents/Core`), work is spread over `/opt`, `/root/projects` and loose
`/root/*` folders, and every doc carries a per-machine path table. Since `~` is
`/root` on Contabo, one root name means `~/MoonieXHQ/...` in any doc or config
resolves correctly on both machines (ADR 0030's `work_dir.root: ~/MoonieXHQ/Work`
already does).

## Target tree

```
/root/MoonieXHQ/
├── Agents/
│   ├── Core      ← /opt/mooniex-agents                 PASAKON/Agents-Core (git)
│   ├── Rules     ← /opt/agents-wikis                   rsync snapshot of Agents-Rules, read-only
│   ├── Wikis     ← /opt/mooniex-wikis                  rsync snapshot of Agents-Wikis, read-only
│   └── Memory    ← /opt/agents-memory                  PASAKON/Agents-Memory (git)
├── Projects/
│   ├── MoonieX/
│   │   ├── ClaudeFlow      ← /root/projects/mooniex-claudeflow       PASAKON/MoonieX-ClaudeFlow; compose + data bind
│   │   ├── Console         ← /opt/mooniex-console                    PASAKON/MoonieX-Console; 2 units + certs/
│   │   ├── AlphaTrader     ← /root/projects/mooniex-alphatrader      deployed copy, no .git
│   │   ├── LineAutomation* ← /root/projects/mooniex-line-automation  PASAKON/MoonieX-LineAutomation (box copy has no .git); unit mooniex-line-queue
│   │   ├── LinePoster*     ← /root/projects/mooniex-line-poster      no repo on GitHub, no .git, 1.6 GB
│   │   └── Option*         ← /root/projects/mooniex-option           PASAKON/MoonieX-Option (box remote still golfmaichai1/mooniex-option); 3 containers
│   └── LungNote/
│       └── Mcp             ← /opt/lungnote-mcp                       PASAKON/LungNote-MCP
├── Assets/MoonieX/CookierunBot/   ← /root/cookierun-gold, /root/idm-yt, idm-full, idm-baseline,
│                                    dataset-stage, idm-*.{log,json,sh}, cookierun-gold-2026-09-23.tgz
├── Work/                          created by delegate on the first worker after sessions restart
└── Archive/                       ← mooniex-vps/20260613T193125Z (was /root/restore — MOVED 2026-09-23),
                                     /root/backups, backup-lunar-hotfix-20260704, *-bundle/,
                                     /Users/gob/Projects/LLMs.stale-20260803
```

Names are not a decision: they come from MAP.md's rule (CEO 2026-09-23: "โครงสร้างชื่อมีแล้ว
นะ ใน map.md"). `*` = no row in `hq.yaml` yet — add it with the rule-derived name and
`machines: {contabo: …}`, same as the existing ClaudeFlow/Console rows. LinePoster has no
repo, so its row carries `repo: null` until one exists. `/root/arb` (no git, cron every 15
min) has no brand → `UNKNOWN/arb`, the map's own fallback.

## Stays outside (tools)

`/opt/node-v22`, `/opt/usage` (agy/codex feeds + serve containers), `/opt/claude-usage-monitor`,
`/opt/disk-monitor`, `/opt/containerd`, `/docker/n8n`, `/root/.acme.sh`, `/root/idm-venv`
(regenerable venv), Docker volumes (org-postgres etc.), `~/.cache`, `~/.npm`.

Z.ai — `/opt/zai-usage-monitor`, `zai-usage-monitor.service`, container `zai-usage-serve`:
**kept** (CEO 2026-09-23: keep it so a future Z.ai model can be wired back through the API).
It is a tool, so it stays outside `/root/MoonieXHQ`.

## What must be repointed (measured 2026-09-23)

| Kind | Items |
|---|---|
| systemd units (8) | `mooniex-drive-broker`, `mooniex-drive-photo-broker`, `mooniex-secretary-waker`, `mooniex-secretary`, `mooniex-sompong-photo-filer` (all `/opt/mooniex-agents`), `mooniex-console` + `mooniex-console-cert-renew` (`/opt/mooniex-console`), `mooniex-line-queue` (line-automation venv) |
| docker compose (2 projects) | `mooniex-claudeflow` (working_dir + bind `data/`), `mooniex-option` (3 containers) |
| cron | `/root/arb/scan_v2.py` — only if arb moves |
| Agents-Core | root `CLAUDE.md` Contabo table, `scripts/cto-claude.sh` + `cxo-claude.sh` (`WIKI_ROOT_*=/opt/...`), the Mac→Contabo rsync lines, Console config that launches C-level sessions from `/opt/mooniex-agents`, any `config/*.yaml` host paths — grep `/opt/` and `/root/projects` before the move |
| Claude Code | transcript slug `-opt-mooniex-agents` → `-root-MoonieXHQ-Agents-Core`: same trap as Mac step ④b (a symlinked slug broke tool-result spill) — make the new slug a real dir with `memory/` linked |
| venvs | `.venv` shebangs carry absolute paths: they keep working through the compat symlink; rebuild (`python -m venv --clear` + `pip install -r`) before the symlink is removed |
| `hq.yaml` | `machines: {contabo: …}` already exists on Wikis, Core, ClaudeFlow, Console — repoint those to `/root/MoonieXHQ/…` and add it to Rules, Memory, LungNote/Mcp, AlphaTrader + the new rows |

## Method (same as Mac step ④b)

Per folder: stop its units/containers → `mv` → compat symlink old path → new path →
repoint unit/compose → `systemctl daemon-reload` + start → verify (port, health URL, logs)
→ next folder. Before each edit, tar the unit and compose files (rollback = remove the
link, `mv` back, restore the files). Compat links are removed only after a clean week,
like Mac step 5.

Order, lowest risk first:
1. `Archive/` + `Assets/` — no services.
2. `Agents/Rules`, `Agents/Wikis`, `Agents/Memory` — change the rsync targets in the same commit.
3. Projects without services — AlphaTrader, LinePoster.
4. Services one at a time — LungNote/Mcp, LineAutomation, Option, ClaudeFlow, Console.
5. `Agents/Core` last — only while both Contabo CTO sessions are idle; restart them after.

Downtime estimate (not measured): about a minute per service while it restarts.

## Needs the CEO

1. Go to execute (service restarts on production) — steps 1–3 have no services.
2. Which project `arb` belongs to (until then `UNKNOWN/arb`).
Answered 2026-09-23: `/root/restore` → Archive for now (done); Z.ai → keep; old tarballs →
delete, back up first if unsure (done, backed up).

## Done the same day (CEO go 2026-09-23)

- Docker build cache pruned (10.31 GB), journal vacuumed to 500 MB (3.4 GB), pip cache removed (539 MB).
- `/root/idm-packs` removed: 47 shards, 12,290,070,828 bytes, md5 47/47 equal to Drive
  `BACKUP/CookieRun Backup/colab_packs` (`1dHtISY1PRVyT5tEP4kr3SqK7zIAJFjpT`); logged in
  `~/.claude/logs/drive-archive.log`. Restore: `rclone copy` that folder, or repack from
  `play_rec` with `windows/cookierun_pack_for_colab.py`.
- Free space 17 GB → 42 GB.
- `/opt/mooniex-agents`: remote → `git@github.com:PASAKON/Agents-Core.git`, fast-forward
  44a8a525 → ee423c2c. Services were **not** restarted; they run the old code until their next restart.
- `/root/restore` → `/root/MoonieXHQ/Archive/mooniex-vps/20260613T193125Z` (same-disk rename; 2,410 files,
  2,542,551,604 bytes before and after). The Mac original `~/Backups/mooniex-vps/` no longer exists, so this
  may be the only copy; the Archive rule (Drive backup, then delete) stays open — its `_env-bundle` secrets go
  to Infisical first. Row in `hq.yaml` Archive items.
- Old tarballs `mooniex-agents-pre{GitSwap-20260807-093707,Sync-20260807-074856}.tgz` → Drive
  `BACKUP/Contabo-mooniex-agents-pre-20260807.tar` (id `1lj-dbuC5YiNz3Zf2qRRj9M1NVtGS6rui`, md5 by id =
  local) + manifest, then deleted from the box. Gate row in `org:playbooks/drive-archive-gate.md`.

## Executed 2026-09-23 (CEO go "ย้ายได้เลย")

**Real folder is `/opt/MoonieXHQ`, and `/root/MoonieXHQ` links to it.** Found at execution time: `/root`
is 0700, and four services run as non-root users (`mooniex-secretary` + `-waker` as `secretary`,
`mooniex-drive-broker` as `driveup`, `mooniex-drive-photo-broker` as `photoup`). They must reach
Agents/Core, so under `/root` they would stop. Opening `/root` would weaken the box's security, which
was not ours to do. So the folder lives under `/opt` (world-traversable, as `/opt/mooniex-agents` is
today), and `~/MoonieXHQ` still resolves for root sessions. `/opt/MoonieXHQ` is a clone of
`PASAKON/MoonieX-HQ`, the same as the Mac (hq.yaml, MAP.md, CLAUDE.md, scripts/, Work/RULES.md). Folders
that came from `/root` keep the old 0700 protection: `Archive/`, `Assets/`, `UNKNOWN/` and each moved
`/root/projects/*` project are chmod 700.

| Step | What moved (old path → compat link) | Verified |
|---|---|---|
| 0 | HQ clone at `/opt/MoonieXHQ`; unit files + crontab tarred to `Archive/hq-migration-20260923/` | 2,410 files in the restore bundle after the move |
| 1 | `/root/{backups, backup-lunar-hotfix-20260704}` + `/Users/gob/Projects/LLMs.stale-20260803` → `Archive/`; 3 secretary `.bak-20260825-174911` files → `Archive/secretary-bak-20260825-174911/` (no link); Cookie Run data (cookierun-gold + its tgz, idm-yt/full/baseline, dataset-stage, idm logs/scripts/zip/json) → `Assets/MoonieX/CookierunBot/`; `/root/arb` → `UNKNOWN/arb` | arb ran via the old path, exit 0; crontab now names the new path |
| 2 | `/opt/agents-wikis` → `Agents/Rules`, `/opt/mooniex-wikis` → `Agents/Wikis`, `/opt/agents-memory` → `Agents/Memory` | nothing had them open; `os.walk` and `grep -r` see 96 files through the link. **`find` sees 0 through a link** — tools/wiki.py `.resolve()`s its roots, so it is unaffected |
| 3 | `/root/projects/mooniex-{alphatrader,line-poster}` → `Projects/MoonieX/{AlphaTrader,LinePoster}` | nothing had them open |
| 4 | `/opt/lungnote-mcp` → `Projects/LungNote/Mcp`; `line-automation` → `LineAutomation` (unit repointed, restarted); `mooniex-option` → `Option`; `mooniex-claudeflow` → `ClaudeFlow`; `/opt/mooniex-console` → `Projects/MoonieX/Console` (2 units + `.env` TLS paths repointed, restarted) | line-queue `/docs` 200; Console 8443 302 (login); compose from the new folders lists the same containers (`COMPOSE_PROJECT_NAME` pinned in each `.env`); ClaudeFlow still sees `/app/data`; tmux sessions sit in a user scope, not the console cgroup, so the restart killed no session; all 7 units active |

Not moved (tools, or in use by another session): `cookierun-disk-guard.sh` (running, Cookie Run CTO),
`contabo-usage-bundle/` + `disk-monitor-bundle/` (tool deploy bundles touched on 09-22/23), `idm-venv`,
secretary one-off scripts, dotfiles.

Code repointed (old path kept as fallback): `scripts/cto-claude.sh` + `cxo-claude.sh` (WIKI_ROOT_*),
`scripts/lib/cxo_mcp_config.py` + `scripts/session-deadline-check.py` (LungNote Mcp), `config/wikis.yaml`
comment, root `CLAUDE.md` (table + rsync targets). `hq.yaml` rows carry `machines.contabo`.

**Compat links to remove after a clean week (≈ 2026-09-30) — first grep each old path across systemd units, the scripts they run, every `.env*` and tracked scripts in every repo (the Mac step 5 broke Console-Mac by skipping this):** `/opt/{agents-wikis, mooniex-wikis,
agents-memory, lungnote-mcp, mooniex-console}`, `/root/projects/*` (5), `/root/{backups,
backup-lunar-hotfix-20260704, arb, cookierun-gold, cookierun-gold-2026-09-23.tgz, idm-yt, idm-full,
idm-baseline, dataset-stage, idm_colab_out.zip, idm-*.{json,log,sh}, idm-full.log.crashed-1913}`,
`/Users/gob/Projects/LLMs.stale-20260803`. Before removing: the LineAutomation venv's shebangs still name
`/root/projects/mooniex-line-automation` — rebuild the venv first.

**Step 5 — `Agents/Core` — still to do.** Wait until both Contabo CTOs are idle (cto-6ebacd0e was running
an hourly Cookie Run count loop at the time). Then `mv` + link, repoint the 5 agents units, restart them,
and handle the Claude transcript slug (`-opt-mooniex-agents` → `-opt-MoonieXHQ-Agents-Core`: Node's cwd is
the physical path) before either session is resumed.

## Step 5 executed 2026-09-24 (CEO: "ส่ง message หาเขาเองได้เลย")

Handshake: cto-6ebacd0e was woken and asked for a window. It answered by touching
`state/core-move-ok` within a minute, and waited on `state/core-move-done`, which carries the result.

In one Python call: `os.rename(/opt/mooniex-agents, /opt/MoonieXHQ/Agents/Core)` + `os.symlink` back.
It then repointed the 5 agents units, the `cookierun_teachers` cron line and the Console `.env` `ORG_ROOT`.
Claude slug: `/root/.claude/projects/-opt-MoonieXHQ-Agents-Core/` is a **real** dir holding **hard links** to
all 7 transcripts, so both slugs see the same growing files. This avoids the Mac 4b symlink-alias, which broke
tool-result spill. `/root/.claude.json` got a trust row for the new path. `git worktree repair` was a no-op
(no worktrees). Backups: `Archive/hq-migration-20260923/core-move-20260924/`.
Verified: all 7 units active, with cwd on the new path; no error lines in the journal after restart;
secretary on 172.18.0.1:8643, brokers on their /run sockets; Console 302; both tmux sessions alive.

Add to the link-removal list: `/opt/mooniex-agents`. First rebuild `.venv` (shebangs name the old path),
and check both Contabo sessions have been relaunched from the new path.
