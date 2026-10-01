# winbox — Windows 11, Ryzen 5 5500, 16 GB RAM, 512 GB NVMe

The CEO's own gaming PC. It runs the Cookie Run bot around the clock and records
everything it plays. Most of its disk is the CEO's, and BlueStacks alone held
19.1 GB. Since the 2026-09-24 reset the account is `passg` (a junction keeps the
old `C:\Users\UsEr` paths alive — write `%USERPROFILE%`, never `UsEr`).

## Two owners on one disk — read this before deleting anything here

| Area | Paths | Who may delete |
|---|---|---|
| **Cookie Run data** | `Documents\CookieRunScript\`, `cookierun-bot\`, the RunPod volume, its Drive folder | **only** a session at Opus 5 or above, effort max, working the Cookie Run scope. `cookierun-bot/docs/DATA-STEWARD.md` is the authority, not this file. Any other agent: read only — write a note in `ledger/housekeeping.jsonl` and stop |
| **Org worker space** | `C:\Users\passg\mooniex\worktrees\` (worker worktrees, `config/hosts.yaml`), the worker clones beside it, `C:\mooniex\` (PC lease, YouTube auth, LINE/subtitle outputs, the doctor's sparse `Agents\Core`) | the parent SKILL's law, like any machine: a merged, clean, pushed worktree is Green for its own session; anything else is backed up first (2026-09-24: 30 worker worktrees, 26.6 GB, held 2.1 MB of unique commits) |
| Everything else | `AppData\Local\Temp` (2.71 GB), `Windows\Temp` (0.92 GB), `$Recycle.Bin` (0.62 GB) … | the CEO — report them, never clear them |

Login state is never Green here either (parent SKILL, "Never Green"): ask the CEO
before touching `%LOCALAPPDATA%\Google\Chrome\User Data`, the CDP profiles
`%USERPROFILE%\.flow-automation\chrome-profile` and `.chatgpt-automation\chrome-profile`,
`%APPDATA%\rclone\rclone.conf`, `C:\mooniex\yt-auth\` or `%USERPROFILE%\.claude\.credentials.json`.

## Limits the spawn path enforces (since 2026-10-01)

- **30 GB floor on `C:`** — `config/storage-policy.yaml` `host_floor_gb.winbox`. Below it
  `tools/delegate.py` queues a worker instead of spawning it. The probe is PowerShell
  (`Get-PSDrive`); the old `df` probe failed through cmd.exe, so the floor never applied here.
- **At most 2 workers** — `config/hosts.yaml` `max_workers` (CEO 2026-09-09), counted per
  dispatching machine until the shared hub is live.
- **Sparse worktrees** — `windows/spawn-worker.ps1 -SparseFile`: tracked media over 256 KiB
  stays out of a worker's checkout.

## State

| | |
|---|---|
| Disk | 510 GB, floor 30 GB free (critical below that) |
| 2026-09-10 before | 6.65 GB free — the recorder was minutes from failing |
| 2026-09-10 after | **24.8 GB free**, ours down 65.2 → 53.5 GB |
| 2026-09-24 | **reset** (new account `passg`); everything above is history. Measure the current state with `tools/machine_doctor.py --machine winbox check` before quoting a number |

## Tiers (summary — the brief has the full table)

| Tier | Meaning | Examples |
|---|---|---|
| A | never deleted | takes' `keys.jsonl`/`frames.jsonl`/`meta.json`, verified `take.mp4`, `rounds.jsonl`, **hit frames** |
| B | rebuildable, cheap to keep | `playset/<take>/`, `playset/dagger*/` |
| C | keep the ranked part | `play_rec/bot_session-*` round recordings |
| D | delete after the run | `playset/merged*`, `*.tgz`, debug dumps after 7 days |

## The loop that runs itself

A 30-minute SYSTEM scheduled task named **`CookieRunStreamRetry`** — a misleading
leftover name — runs `tools\archive_tick.bat`:

1. `archive_runner.py` — re-ranks the bot-session plan if a session is newer than
   it, then streams each queued item to Drive as one tar and verifies md5.
2. `archive_reclaim.py --apply` — deletes only what an `ok` manifest covers, plus
   finished training staging, and writes a ledger line per delete.

Both stand down while `play_model` or `record_play` owns the frame clock, so they
work the gaps between rounds. Budget ~3 minutes per bot session (20-30k small files).

## Traps that have actually cost us

- **"Queue clean" is not proof the disk is safe.** For two days every tick logged
  it while free space fell 0.8 GB/h. Judge growth from `ledger/disk.jsonl`.
- **No heavy I/O while the bot plays** — measured: an encode, a Drive stream and
  the farm together halved capture FPS and made that recording worthless as data.
  At most ONE such job, at below-normal priority, and prefer idle windows.
- **Every box-side process must own no window.** Pass `creationflags=0x08000000`
  (`CREATE_NO_WINDOW`) to every subprocess; a stray console over BlueStacks made
  the navigator refuse every screen for 40 minutes.
- **Never materialise an archive locally** when the disk is tight — stream it
  (`tar` into `rclone rcat`), hashing on the way.
- **`schtasks /Run` on an already-running task returns SUCCESS and starts nothing.**
- **A size scan must skip junctions.** `Local Settings` and `AppData\Local\Application Data`
  loop back into `AppData\Local`, and Python < 3.12 `os.walk` follows them: the first
  doctor run read AppData as 98.7 GB when ~10 GB was real. Prune reparse points
  (`st_file_attributes & 0x400`, as `tools/machine_doctor.py` has since 92e9ae01);
  PowerShell `Get-ChildItem -Recurse` already skips them.
- **Remote survey scripts:** PowerShell variable names are case-insensitive
  (`foreach($d …)` overwrote `$D`, the Downloads path), and the ssh console is cp1252,
  so a Python `print` of a Thai file name crashes. scp a `.ps1` and run it with `-File`;
  in Python write UTF-8 files and print with `backslashreplace`
  (`scripts/stream_backup_to_drive.py` `log()`).
- **A winbox clone looks dirty when it is not:** `C:\mooniex\agents` read 112 unpushed /
  3,143 dirty — 0 ahead after `git fetch`, and 3,134 of the "dirty" were deletions
  (2026-09-24). Diff with `--ignore-cr-at-eol` (CRLF) and split modified from deleted
  before calling anything unique.
- Deploy is `scp` into `winbox:cookierun-bot/` — that copy is **not** a git checkout.

## The ceiling this cannot fix

`modelplay\*\run-*\hit_*` is ~15.6 GB of full-size JPEGs growing **2-4 GB/day**.
Hit frames are tier A, so no steward may delete them. Options belong to the CEO:
tar per session to Drive and keep only the last N days; record fewer frames per
hit; or fit a 2 TB NVMe (~4-5K THB). Until one is chosen the disk returns to
critical in under a week however well the archive loop runs.
