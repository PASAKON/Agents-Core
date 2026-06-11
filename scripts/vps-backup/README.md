# vps-backup.sh — Hostinger VPS off-box backup (Migration Gate #1)

Pull-based, resumable backup of the Hostinger VPS (`srv1395225`, `72.61.118.1`)
to this Mac. This is **Gate #1** of the Hostinger → Contabo migration
(`mooniex-claudeflow` issue #140, "Migration plan v2").

> ⛔ **Hostinger is cancelled after 2026-06-18 — all VPS data is permanently
> destroyed.** Nothing in the migration proceeds until this backup exists and
> `verify` passes. The restore onto Contabo *is* the backup's real test.

The script lives at `scripts/vps-backup.sh`; this folder holds its docs only.

---

## Prerequisites (already satisfied on this Mac)

- SSH alias **`mooniex-vps`** in `~/.ssh/config` (read-only diagnostics +
  backup pulls pre-approved by CEO; all VPS operations here are read-only
  except the optional `pm2 save` in item 10).
- Local tools: `ssh`, `rsync` (Apple 2.6.9 is fine), `dig`, `shasum`, `tar`,
  `du`, `awk`. The script checks these at startup.
- Free disk: ≈ **3.5 GB** for a full run (n8n_data ~1.5 G + line-poster ~1.6 G
  + everything else ~0.3 G).

## Quick start

```bash
scripts/vps-backup.sh discover                 # read-only inventory → inventory.txt
scripts/vps-backup.sh backup --dry-run         # plan: what + sizes, no transfer
scripts/vps-backup.sh backup                   # full pull → ~/Backups/mooniex-vps/<UTC>/
scripts/vps-backup.sh verify                   # PASS/FAIL table + sha256-manifest.txt
scripts/vps-backup.sh mirror <RUN_DIR> /Volumes/<disk>/mooniex-vps   # required 2nd copy
```

Grab the small/critical items first, big volumes later:

```bash
scripts/vps-backup.sh backup --skip-large      # everything except n8n_data + line-poster
scripts/vps-backup.sh backup --only n8n-vol,line-poster   # then the big two
```

Final re-pull on **Jun 18** (only changed files re-transfer; rest hardlink):

```bash
scripts/vps-backup.sh backup --delta --mirror /Volumes/<disk>/mooniex-vps
```

## Commands

| Command | Purpose |
|---|---|
| `discover` | Read-only SSH inventory → writes `inventory.txt`. Run this first; it pins the exact paths the manifest pulls. |
| `backup` *(default)* | Pull the 11-item manifest into a fresh `<UTC-timestamp>/` run dir. |
| `verify [RUN_DIR]` | Walk the manifest of a run (default: latest), check each item exists & non-empty, run the n8n encryptionKey check, write `sha256-manifest.txt`, print a PASS/FAIL/WARN table. **Exits non-zero on any required FAIL.** |
| `mirror RUN_DIR DST` | rsync a completed run dir to a 2nd location (external disk / second folder). |

## Options

| Flag | Effect |
|---|---|
| `--dry-run` | Plan only: prints each item + remote size; no transfers, no remote writes. |
| `--delta` | New run dir, `rsync --link-dest` against the previous run — unchanged files are hardlinked (cheap re-pull). Volume tar streams always re-pull in full. |
| `--skip-large` | Skip the two big items (`n8n-vol`, `line-poster`). `--only` overrides. |
| `--only <csv>` | Pull only these item keys (overrides `--skip-large`). |
| `--mirror <path>` | After a successful backup, rsync the run dir to `<path>`. |
| `--no-pm2-save` | Don't run `pm2 save` on the VPS (item 10) — pulls the existing dump as-is. |
| `--dest <path>` | Backup root. Default `~/Backups/mooniex-vps`. **Keep it outside any git repo.** |
| `--host <alias>` | SSH host/alias. Default `mooniex-vps`. Update after the IP flips to Contabo. |

## The 11-item manifest (paths pinned from live discovery 2026-06-11)

| # | key | Source on VPS | Pulled as | ~Size |
|---|---|---|---|---|
| 1 | `claudeflow` | `/root/projects/mooniex-claudeflow/{data,.env}` | `claudeflow/` | 80 K |
| 2 | `n8n-vol` ⚑ | docker volume `n8n_data` (streamed tar) | `volumes/n8n_data.tar.gz` | 1.5 G |
| 3 | `traefik-vol` | docker volume `traefik_data` (acme.json) | `volumes/traefik_data.tar.gz` | 36 K |
| 4 | `n8n-compose` | `/docker/n8n/` (compose + `.env`) | `docker-n8n/` | 4 K |
| 5 | `option` | `/root/projects/mooniex-option/` + `.env` | `option/` | ~30 M¹ |
| 6 | `line-automation` | `/root/projects/mooniex-line-automation/` (`queue.db`) + pip freeze | `line-automation/` | ~1 M¹ |
| 7 | `line-poster` ⚑ | `/root/projects/mooniex-line-poster/` (`wineprefix` + `screenshots/` + `launch_line.sh`) | `line-poster/` | 1.6 G |
| 8 | `alphatrader` | `/root/projects/mooniex-alphatrader/` (`traders.json`, `bot.log`, `.env`) | `alphatrader/` | ~25 M¹ |
| 9 | `env-bundle` | all 5 `.env` collected + var-counted | `_env-bundle/` | 30 K |
| 10 | `system` | crontab, pm2 dump, systemd `mooniex-*`, ufw, authorized_keys | `system/` | 30 K |
| 11 | `dns` | `dig` snapshot (run from this Mac) | `dns-snapshot.txt` | 4 K |

⚑ = "large" (skipped by `--skip-large`).
¹ Sizes exclude reconstructable dirs (see below). On-disk source dirs are
bigger (option 273 M, alphatrader 208 M, line-automation 56 M) mostly due to
`node_modules` / `venv`.

### The 5 `.env` files (item 9, ~163 vars)

| label | path | non-comment vars (2026-06-11) |
|---|---|---|
| claudeflow | `/root/projects/mooniex-claudeflow/.env` | 102 |
| option | `/root/projects/mooniex-option/.env` | 33 |
| line-automation | `/root/projects/mooniex-line-automation/.env` | 2 |
| alphatrader | `/root/projects/mooniex-alphatrader/.env` | 26 |
| docker-n8n | `/docker/n8n/.env` | 4 |
| **total** | | **167** |

`verify`/`backup` re-count these and FAIL loudly if any of the 5 is missing.

## What is deliberately **excluded** (reconstructable, not silent)

Full-dir pulls (items 5–8) skip: `node_modules`, `venv`, `.venv`,
`__pycache__`, `.pytest_cache`, `*.pyc`, `*.egg-info`. These rebuild from
`package.json` / `pyproject.toml` / `requirements*.txt`. The exclude list is
printed at the top of every `SUMMARY.txt`. `.git`, per-machine state
(`ui-coords.json`, `ui-refs/`, `.browser-profile/`) and all secrets ARE kept —
`line-poster` / `line-automation` / `alphatrader` have **no git remote on the
VPS**, so the backup is their only copy.

## Run-dir layout

```
~/Backups/mooniex-vps/<UTC-timestamp>/       # timestamp = date -u +%Y%m%dT%H%M%SZ
  inventory.txt          # discover output (pinned paths + sizes)
  MANIFEST.txt           # per-item status line
  SUMMARY.txt            # per-item size/duration + next steps
  sha256-manifest.txt    # written by `verify` (every file hashed)
  claudeflow/  volumes/  docker-n8n/  option/  line-automation/
  line-poster/ alphatrader/ _env-bundle/ system/  dns-snapshot.txt
```

## Security

- **Never commit pulled data.** `.env` files hold ~167 production secrets;
  `dump.pm2` may embed process env; `traefik_data` holds the TLS private key.
  The default dest (`~/Backups/...`) is outside any repo by design.
- Pulled `.env` files and `authorized_keys` are `chmod 600`; run dirs `chmod 700`.
- For the required off-site 2nd copy, prefer an encrypted external volume
  (FileVault / encrypted APFS) and use `mirror`.

## Restore cheatsheet (on Contabo)

```bash
# n8n volume (MUST restore before starting n8n, or all creds are unreadable)
docker volume create n8n_data
docker run --rm -i -v n8n_data:/data alpine sh -c 'cd /data && tar xzf -' < volumes/n8n_data.tar.gz
# sanity: the encryption key must be present
docker run --rm -v n8n_data:/data alpine cat /data/config   # -> {"encryptionKey":"..."}

docker volume create traefik_data
docker run --rm -i -v traefik_data:/data alpine sh -c 'cd /data && tar xzf -' < volumes/traefik_data.tar.gz

# project dirs + compose: rsync/copy back into place, restore each .env, then
# `docker compose -f /docker/n8n/docker-compose.yml up -d` and `pm2 resurrect`.
```

## Known deviations from the manifest text (verified 2026-06-11)

- **claudeflow `state/` does not exist on the VPS** (the app uses Supabase as
  source of truth). Item 1 pulls `data/` + `.env` and drops a
  `claudeflow/STATE-ABSENT.txt` marker. Not a data-loss risk.
- **`line-poster` is pulled as the full project dir** (still the manifest's
  `wineprefix` + `screenshots/` + `launch_line.sh`, plus the local-only
  `login*.py` and the LINE installer `.exe`s) since it has no git remote.
- **Env total is 167, not ~163** — the manifest figure was approximate; all 5
  files are present.
- **Root crontab is empty** (cron runs via pm2 + in-app `node-cron`); item 10
  still records a truthful empty-marker file. **ufw is inactive** — recorded as
  such.
