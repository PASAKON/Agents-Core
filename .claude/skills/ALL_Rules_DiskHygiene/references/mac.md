# Mac — MacBook Pro 13" M1, 8 GB RAM, 256 GB SSD

The tightest machine in the org and the one that orchestrates everything. It has
**no Time Machine backup**; treat every delete as unrecoverable unless a copy is
proven to exist somewhere else.

## State

| | |
|---|---|
| Disk | 228 GiB volume, ~19 GiB of it system |
| 2026-09-04 | 39.5 MB free — tools could not write files |
| 2026-09-10 before | 67 MB free |
| 2026-09-10 after | **27.5 GB free** |

## Green here — delete, do not ask

- `~/Library/Caches/Google/Chrome/*/{Cache,Code Cache,GPUCache}` (was 984 MB)
- `~/Library/Caches/tradingview-desktop-updater`, `.../Application Support/TradingView/Code Cache`, `.../discord/{Cache,Code Cache}`
- `~/Library/Caches/pip`, `~/.cache/huggingface`, `~/.cache/torch`
- `brew cleanup -s --prune=all`
- `node_modules` / `.venv` / `.next` passing the dormancy test in the parent SKILL
- a skill's own `.venv` when its SKILL.md documents the rebuild
- `Docker.raw` **only** after `docker system df -v` shows 0 containers and 0 volumes

## The two Mac-specific traps

**Worktrees look enormous and are almost entirely re-checkout.** 40 task
worktrees held 15 GB, none had a `.venv`; the bulk was `docs/reports` and
`docs/prompts` media that is already committed. The only unique bytes are
unmerged commits, dirty files and untracked files — 48 MB across all 40. Back
up **that**, not the tree. Recipe in the parent SKILL, packages in
`BACKUP/Agents-worktrees-<date>.tar`.

**`Agents/.git` is 3.5 GB and `git gc` will not help** (the pack grew 2.9 → 3.45 GiB
after absorbing loose objects). The cause is mp4/png committed under `docs/`.
The fix is to stop committing media there, not to rewrite history on a shared repo.

## Never touch on this machine

- `~/Pictures` — 51 GB, the Photos library
- `~/Library/Application Support/CloudDocs/session/i` — 29 GB, the iCloud store
  backing the CEO's Desktop. Desktop files showing 0 bytes are evicted, not empty.
- `~/Desktop`, `~/Downloads`, `~/Movies`
- `~/.claude/projects/*/memory/`
- `/private/tmp/claude-501/<other session uuid>` — another session's scratch
- `~/Library/Application Support/Claude/vm_bundles/` — Claude Desktop's VM image (`rootfs.img` 9.2 GB on 2026-09-23). CEO 2026-09-23: "ไฟล์ VM ไม่ชัวร์ห้ามยุ่ง" — not ours to delete, move or resize, whatever the disk says

## What is left, and who decides

| | Size | Decision |
|---|---|---|
| `~/Pictures` | 51 GB | CEO |
| CloudDocs (Desktop's iCloud store) | 29 GB | CEO |
| `~/.claude/projects` (transcripts <7 days) | 7.0 GB | automatic, ages out |
| `Agents/.git` | 3.5 GB | stop committing media into `docs/` |
| other sessions' scratch | ~2.9 GB | the owning session |
| `/Applications/Docker.app` | 2.4 GB | CEO — keep only if images will be built locally |
| Homebrew `Cellar` | 2.1 GB | installed software, not cache |

## Hardware note (CEO decision, open)

M1 8 GB / 256 GB, battery 77% at 1281 cycles, "Service Recommended". Mac mini M6
16 GB is 32,900 THB and ships 22 Sep; a used M1 13" sells for 12-18K. An external
1-2 TB SSD plus Time Machine is the cheaper first move and the machine has no
backup at all today.

## Git auto-gc spike (2026-09-23)
Agents-Core's pack is 3.4 GB. An auto `git gc` rewrites it and holds old + new side by side — the Mac dropped to 1.6 GB free for minutes. `gc.bigPackThreshold = 1g` is set in Agents-Core's `.git/config` so auto-gc leaves packs over 1 GB alone. Run a manual `git gc` only with > 10 GB free.
