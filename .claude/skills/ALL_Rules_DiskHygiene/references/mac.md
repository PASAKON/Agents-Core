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
- `~/Library/Caches/pip`, `~/.npm/_cacache`, `~/.npm/_npx` (1.1 GB), `~/.cache/huggingface`, `~/.cache/torch`
- `brew cleanup -s --prune=all` (its cache alone was 3.1 GB; with `_npx`, 3.9 → 8.1 GB free on 2026-09-25)
- `node_modules` / `.venv` / `.next` passing the dormancy test in the parent SKILL
- a skill's own `.venv` when its SKILL.md documents the rebuild
- `Docker.raw` **only** after `docker system df -v` shows 0 containers and 0 volumes

## Mac-specific traps

**Worktrees look enormous and are almost entirely re-checkout.** 40 task
worktrees held 15 GB, none had a `.venv`; the bulk was `docs/reports` and
`docs/prompts` media that is already committed. The only unique bytes are
unmerged commits, dirty files and untracked files — 48 MB across all 40. Back
up **that**, not the tree. Recipe in the parent SKILL, packages in
`BACKUP/Agents-worktrees-<date>.tar`. They also fill the disk fastest: at ~0.87 GB
each, ~7 spawns in an hour took the Mac to 0 bytes on 2026-09-23. Worker worktrees
have been sparse since (`tools/worktree.py` drops tracked media over 256 KiB by
exact path — a directory exclude makes `git add -A` refuse new files there; ~78 MB
each, `video_editor` still full), and the spawn floor queues below 5 GB.

**Every live Chrome holds a ~1.4 GB code-sign clone** in
`/private/var/folders/*/*/X/com.google.Chrome.code_sign_clone/` — the CEO's own
and each CDP profile (Flow 9223, TikTok 9224, relay tests 9250 …), invisible to a
`du` of our folders. Deleting a live one frees nothing and can break that Chrome;
the space returns when it quits (9223 + 9226 quit: 3.5 → 7.5 GB, 2026-09-24).
Count them first — `pgrep -fl 'Google Chrome.app/Contents/MacOS/Google Chrome' |
grep -o 'remote-debugging-port=[0-9]*'` — and ask each owner to quit an idle one.

**The Trash frees nothing.** `~/.Trash` is a rename on the same APFS volume: with
76 GB of backed-up data in it the Mac sat at 1.8 GB free until the CEO emptied it
(73 GB, 2026-09-25). Emptying is permanent deletion, his call (`ALL_Rules_Approvals`
rule 3): the moment anything big goes in, tell him its size and that it is the lever.

**`Agents/.git` is 3.5 GB and `git gc` will not help** (the pack grew 2.9 → 3.45 GiB
after absorbing loose objects). The cause is mp4/png committed under `docs/`.
The fix is to stop committing media there, not to rewrite history on a shared repo.

## Never touch on this machine

- `~/Pictures` — 51 GB, the Photos library (8,654 items). iCloud Photos was off,
  so the Mac held the only copy until `Mac-Reinstall-2026-09-24-Photos-p00…p19`
  (52.76 GB) went to Drive. Before any wipe re-check size, item count and iCloud Photos.
- `~/Library/Application Support/CloudDocs/session/i` — the iCloud store backing
  the CEO's Desktop (29 GB on 2026-09-10). Desktop files showing 0 bytes are
  evicted, not empty. It can hold an orphaned store: 1,050 files / 43.3 GB on
  2026-09-25 that `client.db` no longer referenced, invisible in Finder and in iCloud's figure.
  For the wipe the CEO said "สำรองด้วย ระหว่างสำรองลบ ข้อมูลที่ยืนยันได้ว่าสำรองแล้ว"
  (`Mac-Reinstall-2026-09-25-iCloudLeftovers-*`); that word covered that case only.
  There is no standing step: before any later wipe or clean-up, ask him again each
  time (CEO 2026-09-28: "Yes").
- Login state (parent SKILL, "Never Green") — ask the CEO first: `~/Library/Application Support/Google/Chrome/`
  (his own Chrome), the CDP profiles `~/.flow-automation/chrome-profile`,
  `~/.higgsfield-automation/chrome-profile`, `~/.bl-tiktok-automation/chrome-profile`,
  `~/.config/mooniex/`, `~/.config/gh/hosts.yml`, any `rclone.conf`,
  `~/.claude/.credentials.json`. Their `Cache` / `Code Cache` / `GPUCache` stay Green.
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
