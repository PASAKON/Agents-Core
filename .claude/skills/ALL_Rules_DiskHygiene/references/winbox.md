# winbox — Windows 11, Ryzen 5 5500, 16 GB RAM, 512 GB NVMe

The CEO's own gaming PC. It runs the Cookie Run bot around the clock and records
everything it plays. **It is not an org machine** — roughly 400 of its 510 GB
belong to the CEO, and BlueStacks alone holds 19.1 GB.

## Authority — read this before deleting anything here

`cookierun-bot/docs/DATA-STEWARD.md` is the authority, not this file. Only a
session at **Opus 5 or above, effort max, working the Cookie Run scope** may
create, move or delete data here. Any other agent: **read only** — write a note
in `ledger/housekeeping.jsonl` and stop.

## State

| | |
|---|---|
| Disk | 510 GB, floor 30 GB free (critical below that) |
| 2026-09-10 before | 6.65 GB free — the recorder was minutes from failing |
| 2026-09-10 after | **24.8 GB free**, ours down 65.2 → 53.5 GB |

## Scope — the only paths that are ours

`Documents\CookieRunScript\`, `cookierun-bot\`, the RunPod volume, and the Drive
folder. Nothing else. Not `AppData\Local\Temp` (2.71 GB), not `Windows\Temp`
(0.92 GB), not `$Recycle.Bin` (0.62 GB) — report those to the CEO, never clear them.

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
- Deploy is `scp` into `winbox:cookierun-bot/` — that copy is **not** a git checkout.

## The ceiling this cannot fix

`modelplay\*\run-*\hit_*` is ~15.6 GB of full-size JPEGs growing **2-4 GB/day**.
Hit frames are tier A, so no steward may delete them. Options belong to the CEO:
tar per session to Drive and keep only the last N days; record fewer frames per
hit; or fit a 2 TB NVMe (~4-5K THB). Until one is chosen the disk returns to
critical in under a week however well the archive loop runs.
