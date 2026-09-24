# Plan: MoonieX Machine Contract — rebuildable machines, closed sessions, controlled growth

## Context (why)

On 2026-09-24 winbox (Windows) was reset before its Cookie Run data was fully backed up: 84 GB of
irreplaceable bot data was lost, while everything that lived in git (code, rules, skills, memory,
task definitions) came back in ~2 hours from GitHub + a captured "blueprint". The CEO's conclusion:
machines must never again be the only home of anything that matters, disk growth must be
controllable per session/task, and a reinstall (or a brand-new machine) must be a routine, rehearsed
operation — "พร้อมเสมอ ไม่กังวลอีกต่อไป".

Measured growth points this week: one CTO session transcript 42 MB (biggest on Contabo 221 MB,
588 MB total); a worker worktree ≈ 880 MB each (38 piled up = 13.5 GB on the Mac, 60 GB on winbox);
Cookie Run hit frames 2–4 GB/day; Docker on Contabo 7.5 GB; pagefile 18.5 GB on winbox; small
per-session leftovers (file-history, .claude.json backups, logs). Claude Code's own profile
(`~/.claude.json`, settings, plugins, transcripts) has no standing backup on any machine; only the
auto-memory directory is in git (Agents/Memory).

CEO requirements (2026-09-24, "Go"):
1. Machine Contract: per-machine BOM + one restore script; every session/task writes only into a
   closable place; retention/GC automation; disk dashboard for 3 machines; a cap on bot data; a
   re-OS drill (can run now on the fresh winbox).
2. Designed for change: when Claude Code moves/adds important paths, or a toolkit changes paths or
   versions, the registry is easy to update and unknown growth is flagged — no hard-coded
   assumptions buried in scripts.
3. Toolkits tracked at PATH level only (what/where/how to reinstall) — never function level.
4. Keep only what cannot be re-created or re-downloaded (irreplaceable assets + memory worth
   keeping); reinstallable things are never stored; garbage is not archived. Drive holds 20 TB.
   Mac / Contabo / winbox are brains + tools + workspaces, not stores.
5. A rule for agents (Agents/Rules) so every agent knows the scheme and how problems are handled.
6. Say which current practices are unnecessary.

## Findings from exploration

### A. What HQ already has (reuse, do not reinvent)
- `hq.yaml` (HQ root) = the folder inventory: one row per folder with `repo`, `owner`, `current`,
  `machines: {contabo, winbox}`, `keeps`/`never`; `scripts/hq.py map|doctor|show` regenerates
  MAP.md and **`doctor` reports disk-vs-map drift (exit 1)** — this is the natural home of the
  "registry" and of change detection. It is a project map, not a machine BOM (no packages, no
  profile paths, no restore steps).
- **ADR 0030** `Agents/Rules/decisions/0030-agent-storage-every-byte-has-a-tier-and-an-end.md`:
  tiers HOT / REBUILD / COLD / NEVER (`Agents/Core/config/storage-policy.yaml:45-88`), a free-space
  gauge (≥20 GB green … <5 GB red = refuse spawns), the `Work/<task>/{in,tmp,out}` close gate, the
  media-guard hook (`scripts/media_guard.py`, `storage-policy.yaml media_guard.max_bytes` 1 MiB),
  sparse worktrees, and a cross-machine disk endpoint `https://webhook.mooniex.com/disk`.
  **Pilot-scoped to one owner_cto, not org-wide.**
- Work/ discipline: `tools/workdir.py` (`create|check|close [--archive]|orphans`), close logic
  lines 187-287, ledger `Work/_ledger.jsonl` (ts, task, bytes, dest, md5, by);
  `tools/work_archive.py archive()` lines 201-289: tar + `.manifest.json` (with a `restore:` line),
  Drive REST resumable upload into `BACKUP/` (folder id constant line 62), md5 verified BEFORE any
  delete, log `~/.claude/logs/drive-archive.log`. `Work/RULES.md` = 10 rules + enforcement table.
  `tools/work_watch.py` flags Green-list items older than 14 days (never deletes).
- Rules: IRON-RULES.md highest §57 → **new rule = §58**; ADRs highest 0030 → **new ADR = 0031**.
  §55 (Work/), §56 (English). Playbook `drive-archive-gate.md` already carries the two one-off
  "reinstall" rows (Winbox Reinstall 2026-09-24, Mac-Reinstall-2026-09-24).
- `session-close` skill parks unfinished work to LungNote and pushes the memory repo; it does not
  touch disk bytes.
- Gaps confirmed: no per-machine BOM/restore script; no scheduled retention/GC (only flagging);
  ADR 0030 not org-wide; no Claude-profile backup; no agent rule for the scheme.

### B. Backup / disk / retention tooling that exists today
- `scripts/stream_backup_to_drive.py` — GENERIC primitive: freeze file list (size+mtime) → tar → `rclone rcat`
  (`--drive-root-folder-id`) → verify size+md5 → manifest → `--delete-after-verify` (only unchanged files); runs on
  winbox, or from the Mac via `scripts/rclone_via_winbox.sh` / `drive_rest_rclone_shim.py`; logs
  `<workdir>/<name>.{log,progress.txt,result.json}`. Used for the Mac pre-wipe backup (3 tars: `claude-home` 1.77 GB =
  all of `~/.claude` minus plugins/cache; `MoonieXHQ-code` 0.92 GB = git bundles of unpushed branches + patches;
  `MoonieXHQ-data` 2.87 GB = gitignored data); secrets never to Drive → `contabo:/opt/MoonieXHQ/Archive/mac-secrets-*`.
- `scripts/vps-backup.sh` (+ `scripts/vps-backup/README.md`) — pull-based, resumable, 11-item full-VPS backup to the
  Mac with `discover / backup / verify / mirror` — the closest existing "per-machine BOM + restore" precedent.
- `claude-home/tools/prune_transcripts.py` — report/notify/archive/restore transcripts >7 d (Mac launchd
  `com.gob.claude-prune-transcripts` daily 09:00, notify-only). Drive gate row 3 already names the transcript
  destination `Claude-Transcripts/<project>/<uuid>.tar.gz`.
- `tools/disk_queue.py` + `runners/watchdog.py --interval 300` — spawn refused under the floor goes to a FIFO and is
  drained later; `tools/gc_stale_tasks.py` + `tools/worktree.py` reap dead worktrees.
- disk-hygiene skill (`references/{mac,winbox,contabo}.md`): Green list (delete now), back-up-first list,
  never-touch per machine (Mac: Pictures 51 GB, iCloud, Desktop/Downloads/Movies, memory dirs; winbox: only
  CookieRunScript + cookierun-bot are in scope; Contabo: the 2 live Docker volumes, active images, /root/restore,
  the rsync wiki snapshots).
- Schedules: winbox `CookieRunStreamRetry` every 30 min (archive_runner + archive_reclaim in cookierun-bot),
  `CookieRun-DiskSense` daily; Mac launchd transcript notifier daily; Contabo has NO cron for disk/backup (only
  the Agents watchdog loop).
- `disksense.py` lives in cookierun-bot (winbox), not in Agents-Core.

### C. Claude Code's own storage + toolkits (Contabo measured; Mac/winbox same shape)
- `CLAUDE_CONFIG_DIR` relocates Claude's home; org hooks/statusline already honour it. `scripts/claude_home_migrate.py`
  (ADR 0027) already moves org-owned parts of `~/.claude` (CLAUDE.md, settings.json, hooks/, commands/, mcp/, tools/,
  skills) into the repo (`claude-home/`, `.claude/skills/`) and symlinks back — **the "profile in git" pattern
  exists**; it does not cover `~/.claude.json` trust/allowedTools, transcripts, uploads, or project-slug renames
  (the HQ move hard-linked transcripts under the new slug by hand).
- Classification (Claude): `projects/*/*.jsonl` transcripts 589 MB = IRREPLACEABLE (sole copy); `uploads/` 11 MB
  IRREPLACEABLE; `projects/*/memory` = in git already; `settings.json` CONFIG; `.claude.json` → only its `projects{}`
  map (trust + allowedTools) matters; `.credentials.json` = never copy, re-login; `skills/synced`, `plugins`
  REBUILDABLE; `file-history, cache, session-*, sessions, shell-snapshots, state, logs, backups, downloads` DISPOSABLE.
- Toolkits (Contabo): Docker images 5.1 GB REBUILDABLE; **volumes `n8n_data` 1.55 GB and `org-pgdata` 73 MB are
  IRREPLACEABLE data** (workflows/creds, coordination DB) — no other copy today; build cache DISPOSABLE;
  `.venv`/`node_modules`/`idm-venv`/`node-v22` REBUILDABLE; `/root/.acme.sh` CONFIG (keep, LE rate limits);
  systemd `mooniex-*` units CONFIG **not in git**; `/opt/claude-usage-monitor` code in git, JSON regenerates.
- Capture tools: only winbox has a blueprint (`windows/winbox-reinstall/rebuild/blueprint.ps1`, secrets excluded by
  design); Mac and Contabo have none. The usage monitor overwrites `usage.json` (no history) — not a ledger.
- Change detection idea (agent C): keep the "left alone on purpose" list as baseline; weekly diff of
  `find ~/.claude -maxdepth 2` and `jq keys ~/.claude.json` against a checked-in snapshot, triggered also on
  `claude --version` bumps (`.last-update-result.json`); same `du` diff for toolkit paths and `mooniex-*` units.

## Recommended approach — extend ADR 0030 org-wide, add the three missing pieces

Principle (CEO): git = code + config; Drive (20 TB) = the only store for irreplaceable bytes; machines are
brains + tools + workspaces and must be rebuildable from git + Drive at any time; reinstallable things
are never stored; garbage is never archived; every session/task leaves the disk where it found it.

### Phase 0 — the registry and the rule (1 day, no new runtime code)
1. **Registry** `Agents/Core/config/machine-contract.yaml` (new; sibling of `storage-policy.yaml`).
   Not hq.yaml rows: `hq.py doctor` models HQ folders bijected to repos; a Docker volume, a systemd
   unit or a `.claude.json` key is not a folder-repo. `Agents/Core`'s hq.yaml row already `keeps:
   config/`, so no hq.yaml edit. Row fields: `machine`, `path` (with `$CLAUDE_CONFIG_DIR` / `$HOME` /
   `%USERPROFILE%` placeholders), `class` IRREPLACEABLE | CONFIG | REBUILD | DISPOSABLE, `owner`,
   `restore` (one line), `reviewed`, `discovered: true|false`. Seed rows = findings B/C (Claude profile,
   Docker volumes `n8n_data` + `org-pgdata`, `mooniex-*` units, `.acme.sh`, winbox CookieRunScript,
   BlueStacks instance conf, task XMLs, Chrome profiles, venvs, Downloads).
2. **ADR 0031** `Agents/Rules/decisions/0031-machine-contract.md`: supersedes ADR 0030's pilot scope
   (org-wide, all three machines), maps HOT/REBUILD/COLD/NEVER → the four classes, points at the
   registry, records "what is unnecessary now". One `Relates:` line added to 0030's header.
3. **IRON-RULES §58 "Machine Contract"** (after §57), HARD lines with `Why hard:` per skill-author
   doctrine (money / irreversible / scope), the rest as facts. Text in section "Rule text" below.
4. Skills: `disk-hygiene` (+ `references/{mac,winbox,contabo}.md`) points its Green / never-touch lists
   at the registry as the authoritative class source; `gdrive-filing` gets one line: restore hints and
   Drive destinations come from the registry. **No new skill.**

### Phase 1 — capture, close-to-baseline, ledger (2–3 days)
5. **Capture verb per machine** ("blueprint", text only, secrets excluded, output committed to
   `Agents/Core/state/<machine>-blueprint-<date>/`): winbox = existing
   `windows/winbox-reinstall/rebuild/blueprint.ps1` (already proven; commit its 2026-09-24 output);
   new `scripts/mac_blueprint.sh` (brew bundle dump, `launchctl list`, relevant `defaults read`,
   `~/.claude` tree, `.claude.json` keys + projects map) and `scripts/contabo_blueprint.sh` (apt/pip/npm
   lists, `mooniex-*` unit files, crontab, compose files, `docker volume ls` names, `~/.claude` tree).
6. **Close-to-baseline** = existing tools, one new field: `tools/workdir.py close --archive`
   (Work/, `work_archive.py`, md5 before delete) for task output; `scripts/stream_backup_to_drive.py
   --delete-after-verify` for big data outside Work/; `claude-home/tools/prune_transcripts.py
   --archive` for transcripts older than N days. New: `added_bytes` stamped at `workdir.py create` and
   diffed at `close`, written into the existing `Work/_ledger.jsonl` line — "+X added, −X archived",
   disk back to baseline is `added_bytes − bytes ≈ 0`. Session-end checklist in §58 / session-close.
7. **Claude profile in git**: extend the existing `scripts/claude_home_migrate.py` pattern
   (`claude-home/`) with the `.claude.json` `projects{}` map (trust + allowedTools, no secrets) and a
   slug-rename map (`old slug → new slug`) so a path move never needs hand hard-linking again.

### Phase 2 — retention/GC + drift detection (1–2 days)
8. **`tools/machine_doctor.py`** (new, same shape as `hq.py doctor`: walk registry vs disk, exit 1):
   weekly diff of `~/.claude` (depth 2), `.claude.json` keys, toolkit paths, `docker volume ls`,
   `systemctl list-unit-files 'mooniex-*'` / schtasks / launchd, against a committed
   `state/machine-snapshot-<machine>.json`; anything > N MB not matching a row is reported as
   `discovered` and must be classified within 14 days (never auto-deleted). Also runs when
   `claude --version` changes (`~/.claude/.last-update-result.json`).
9. **Schedules** reuse the existing schedulers: Mac launchd (`com.gob.claude-prune-transcripts` +
   weekly doctor), winbox schtasks (`MachineContractDoctor` weekly, pattern of `CookieRun-DiskSense.xml`),
   Contabo cron (one weekly line — today it has none). Floors = ADR 0030 gauge, org-wide.
   NEVER auto-deleted = `storage-policy.yaml tiers.NEVER` ∪ registry IRREPLACEABLE.

### Phase 3 — restore verb + re-OS drill (2 days + the drill)
10. **`restore` per machine** modeled on `scripts/vps-backup/README.md` "Restore cheatsheet" and
    `winbox-bootstrap.ps1` + `rebuild_r1/r2.ps1`: `scripts/mac_restore.sh`, `scripts/contabo_restore.sh`,
    winbox = the existing bootstrap + rebuild scripts made idempotent and registry-driven. Human-only
    checkpoints stay explicit: logins, Tailscale, OAuth re-consent, LINE.
11. **Drill now on winbox** (does not block the CEO's game install): re-run `blueprint.ps1`, diff
    against the committed capture; PASS = every winbox CONFIG/REBUILD row present or restorable by one
    command, every IRREPLACEABLE row has a verified Drive copy; MEASURE = minutes to remote access
    (today: ~10 min of CEO steps), minutes to restore (today: ~2 h), bytes from git vs Drive, human
    steps count. Log one line per drill in `state/re-os-drills.jsonl`. Quarterly cadence: winbox
    (real), Mac (real when it is next wiped — it is now), Contabo (in a VM or a scratch VPS).

### What is unnecessary now (drop)
- Backing up REBUILD bytes (node_modules, .venv, Docker image layers 5.1 GB) — keep only the
  rebuild command in the registry.
- One-off reinstall tars per incident (the two 2026-09-24 gate rows) — replaced by the standing
  capture/restore verbs.
- Hand hard-linking transcripts when a project path moves — a slug map row instead.
- Keeping raw transcripts forever: archive to Drive after 7 days (existing), delete the raw
  `.jsonl` from Drive after a CEO-chosen window (proposal 180 days) — anything worth keeping longer
  must already be in Agents/Memory (git). CEO decision.

### Cookie Run data (CEO decision)
Hit frames grow 2–4 GB/day and were the bulk of the 100 GB. Registry rows: `rounds.jsonl` +
manifests IRREPLACEABLE (tiny); hit frames = IRREPLACEABLE only up to a daily cap the CEO sets, the
rest DISPOSABLE after the 30-min `archive_runner` stream. Proposal: cap 500 MB/day of hits kept
locally, everything older streamed to Drive by the existing `CookieRunStreamRetry` and deleted
after verify.

## Registry format (`Agents/Core/config/machine-contract.yaml`)
Four classes = asset replaceability (orthogonal to ADR 0030's activity tiers):
IRREPLACEABLE (sole copy → verified Drive copy before any wipe) · CONFIG (small, hand-set, restore
from a captured value) · REBUILD (one command recreates it; store the command, never the bytes) ·
DISPOSABLE (never stored, never archived). Row = `machine, path (placeholders $CLAUDE_CONFIG_DIR /
$HOME / %USERPROFILE%), class, owner, restore (one line), review (date), discovered (bool)`;
a scan-found row carries the sentinel `class: UNCLASSIFIED` (never blank).
Header: `unknown_growth: {min_mb: 500, classify_within_days: 14, report: weekly}`, `review_cycle_days: 90`.
Representative rows: Claude transcripts IRREPLACEABLE (restore via `prune_transcripts.py --restore`
from `BACKUP/Claude-Transcripts/`); `.claude.json` CONFIG (only `projects{}`); `projects/*/memory`
REBUILD (git Agents-Memory); Docker `n8n_data` + `org-pgdata` IRREPLACEABLE (volume tar / pg_dump);
`/etc/systemd/system/mooniex-*.service` CONFIG; winbox `CookieRunScript\play_rec\**` IRREPLACEABLE;
`bluestacks.conf` CONFIG; task XMLs CONFIG; Chrome profile REBUILD (re-login, never exported);
`.venv` REBUILD (`pip install -r`); `Downloads` DISPOSABLE. CEO-personal paths (Pictures, Desktop,
iCloud) stay out — disk-hygiene's never-touch list governs them. Path moves / version bumps =
one-row edits.

## Rule text — IRON-RULES §58 (draft, house style; HARD lines carry Why-hard)
1. HARD — no OS reinstall, disk wipe, or volume/folder delete proceeds until every IRREPLACEABLE row
   of that machine shows a Drive copy verified by checksum. Why hard: irreversible — 2026-09-24
   winbox lost 84 GB with no other copy.
2. HARD — a `discovered` path past its 14-day window is only a DISPOSABLE *candidate*; no agent
   deletes it without an explicit human go. Why hard: irreversible; the clock creates pressure to
   classify, not licence to guess.
3. Entries are paths with placeholders for what moves — never a function, package or version; a
   Claude Code or toolkit path change is a one-row edit.
4. `hq.yaml` maps HQ project folders (CEO-approved, §54); `machine-contract.yaml` maps OS / profile /
   toolkit paths and is CTO-maintained — a path lives in exactly one of them.
5. The weekly scan reports every path over the floor that matches no row as `discovered`; the owner
   classifies within 14 days.
6. Reinstallable is never stored, garbage is never archived: a REBUILD row stores only its command; a
   DISPOSABLE row is never written to Drive.
7. Drive (20 TB) is the store; Mac, winbox, Contabo are brains + tools + workspaces — each must be
   able to go to zero and come back from git + this manifest + Drive alone.
8. CEO-personal paths are out of scope (disk-hygiene governs them).
9. A machine that has never been rebuilt on paper is not proven rebuildable: the re-OS drill runs
   at least quarterly (ADR 0031).
Session/task end checklist (also in `session-close`): `workdir.py close <task> --archive` →
`stream_backup_to_drive.py --delete-after-verify` for bytes outside Work/ → transcripts via the daily
prune job (never by hand) → gauge back in green, no UNCLASSIFIED pile.

## Re-OS drill
Record four numbers + PASS/FAIL per drill in `state/re-os-drills.jsonl`: minutes to remote access;
minutes until every registry row is accounted for (present or logged loss); bytes from git vs bytes
from Drive; the numbered list of human-hand steps with their durations. PASS = every IRREPLACEABLE
row verified present or logged as a known loss (never a silent gap), every CONFIG/REBUILD restore
line worked as written, doctor exits 0. Winbox NOW: score the org leg retroactively (≈10 min CEO
steps to remote access; ≈2 h to code/venv/tasks; CookieRunScript rows = known FAIL, 0 bytes
recovered); BlueStacks/game rows stay pending on the CEO, no deadline. Cadence: one real drill per
quarter rotating Mac → winbox → Contabo; Contabo's drill uses a disposable VPS/VM, never the live box.

## Verification (end to end)
- Phase 0: `python -c "import yaml; yaml.safe_load(open('config/machine-contract.yaml'))"`; every path
  from findings B/C has a row; `skill-lint.py check` passes; IRON-RULES has §58; ADR 0031 exists and
  0030 links it.
- Phase 1: run each blueprint verb on its machine, commit output, `grep -riE 'token|secret|password'`
  over the output returns nothing; `workdir.py create` → write 50 MB → `close --archive` → ledger line
  has `added_bytes` and `bytes`, Drive object md5 matches, folder gone.
- Phase 2: `tools/machine_doctor.py` first run writes the baseline; add a 600 MB junk file under
  `~/.claude/x/` → run → exits 1 and lists it as discovered; remove → exits 0. Cron/launchd/schtasks
  entries visible in `crontab -l` / `launchctl list` / `schtasks /Query`.
- Phase 3: winbox drill scored and logged; Mac restore script dry-run on a scratch path; the Mac's
  real wipe (in progress now) is drill #2 — measure the same four numbers.
- Disk outcome to watch (the CEO's actual goal): per machine, free space returns to the baseline
  after each closed task; weekly doctor report empty of UNCLASSIFIED after the first month.

## CEO decisions (answered 2026-09-24)
1. **Transcripts: keep ALL on Drive, forever** (after 7 days off the machine). Drive home for every
   kept category is **`BACKUP/MoonieX HQ/<what-is-kept>/`**, each subfolder with a written definition
   so an agent cleaning up or searching knows where things live.
2. **Cookie Run hit frames: 500 MB/day stays on the box; the rest streams to Drive** (existing
   30-min `CookieRunStreamRetry`), deleted after md5 verify; `rounds.jsonl` + manifests always kept.
3. **I write everything; the Mac CTO runs and verifies the Mac verbs** and reports the drill numbers
   (I cannot reach the Mac). Hand-off = a file in the repo + a mailbox letter, not chat.
4. **Drill scope now: winbox org leg (retroactive score) + the Mac's real wipe as drill #2.**

## Drive layout to create and define (gdrive-filing tree + ID table + drive-archive-gate rows)
`BACKUP/MoonieX HQ/` (new family, CEO-approved above):
- `Claude-Transcripts/<machine>/<project-slug>/<session-uuid>.jsonl.gz` — every session, all machines,
  never deleted; restore = `prune_transcripts.py --restore`. (Replaces gate row 3's location.)
- `Claude-Uploads/<machine>/<date>.tar` — files people attached in chat (`~/.claude/uploads`).
- `Work-Archive/Agents-Work-<task-id>-<date>.tar` + manifest — closed task output (`work_archive.py`;
  new tars go here, the existing ones at `BACKUP/` root are moved server-side once, by the bridge).
- `Docker-Volumes/<machine>/<volume>/<date>.tar` + manifest — `n8n_data`, `org-pgdata` (first-ever
  backup of these), weekly.
- `Machine-Blueprints/<machine>/<date>/` — a copy of each capture (primary copy is git `state/`).
- Cookie Run data stays in the existing `BACKUP/CookieRun Backup/` family (approved 2026-09-23/24);
  the registry rows point there.
- Secrets never go to Drive (unchanged): they go to a second machine's `Archive/` at 0600 with a
  sha256 list, and the registry row says so. (Open item for later: an encrypted secrets bundle on
  Drive — not in this plan.)
Each subfolder gets: a tree line + definition in `gdrive-filing/SKILL.md`, its Drive id in the ID
table, and one `drive-archive-gate.md` row (source → destination → verify → log).

## Execution order (what I build, in this order; est. 5–6 working days of agent time)
0. Phase 0 (registry, ADR 0031, §58, skill pointers, Drive folders + definitions) — day 1.
1. Phase 1 (blueprints for Mac/Contabo, `added_bytes` ledger, transcript archiver to the new path,
   Docker-volume backup job, hit-frame cap in the winbox archive plan) — days 2–3.
2. Phase 2 (`machine_doctor.py`, schedules on 3 machines, weekly report) — day 4.
3. Phase 3 (restore verbs, winbox drill scored + logged, Mac drill package handed to the Mac CTO) —
   day 5. Nothing in this plan spends money; Drive space used ≈ a few GB/month.
Hand-offs: Mac verbs run by the Mac CTO; winbox game/BlueStacks steps stay the CEO's (no deadline);
Cookie Run farm resumes only after the CEO's "เกมพร้อม".
