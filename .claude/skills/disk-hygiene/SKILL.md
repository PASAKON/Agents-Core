---
name: disk-hygiene
owner: CTO
origin: mooniex-org
scope: >-
  What may be deleted from a machine to reclaim space, what must be backed up
  first, and where every backup lands. Covers all three org machines — the Mac,
  winbox (Windows) and the Contabo VPS — one reference file each. Decides
  whether a thing may go; `gdrive-filing` decides where it lands on Drive and is
  read FIRST whenever Drive is touched. Not a file-transfer tool.
description: Rules for reclaiming disk space without losing data, on the Mac, winbox (Windows) and the Contabo VPS — the Green list (delete now, no asking), the back-up-first list, the never-touch list, and where every backup lives on Google Drive with its restore command. Trigger on /disk-hygiene, "disk เต็ม", "เคลียร์พื้นที่", "ที่เก็บข้อมูลเต็ม", "no space left", "ENOSPC", a DISK-WARNING.txt surfaced at session start, or before deleting ANY node_modules, .venv, cache, worktree, transcript, docker artefact or dataset. Use instead of guessing what is safe to delete. Read `gdrive-filing` as well (not instead) whenever the answer involves Drive; for Cookie Run training data the tier table in cookierun-bot/docs/DATA-STEWARD.md wins over this file.
created_by: agent
author: CTO
audience: [cxo, worker]
---

# Disk hygiene — reclaim space, lose nothing

Written 2026-09-10, the day the Mac hit **67 MB free** (tools could no longer
write a file) and winbox hit **6.6 GB** against a 30 GB floor. Both were fixed
the same day without losing a byte. This file is what that cost to learn.

## Which machine

Read this page for the law, then the one file for the box you are on.

| Machine | File | Shape of the problem |
|---|---|---|
| Mac (M1, 256 GB) | `references/mac.md` | chronically full, no Time Machine, orchestrates everything |
| winbox (Windows, 512 GB) | `references/winbox.md` | the CEO's game PC; a bot fills it 2-4 GB/day; steward tier only |
| Contabo VPS (72 GB) | `references/contabo.md` | production; comfortable today; every write needs the CEO's go |

## The one law

> **Regenerable → delete it now, do not ask.
> Everything else → back it up, VERIFY the backup, delete, then log it.**

"Regenerable" is a claim you must be able to defend in one sentence that names
the command which rebuilds it. If you cannot name that command, it is not
regenerable — back it up.

## The worker contract — every agent, every machine

1. **Measure first.** `df -h /` plus `du -sh` of the suspects. Never delete on a
   hunch about what is big.
2. **Read `gdrive-filing` before the first Drive call** of the session. A
   PreToolUse hook blocks Drive-touching calls until you have. Google's own
   limits are not a substitute for it.
3. **Back up anything not regenerable before deleting.** One tar per item, never
   loose files. Write `<name>.manifest.json` beside it: file count, bytes, sha256
   and md5, source path, date.
4. **Verify by checksum, never by size.** Read `md5Checksum` back from Drive and
   compare it with the local hash. Only then delete. "It looked like it uploaded"
   is not verification.
5. **Log it.** One line per item in `~/.claude/logs/drive-archive.log`: date,
   source, destination, files, bytes, sha256, drive md5, status. On winbox also
   `ledger/housekeeping.jsonl` — `ts` (ISO-8601 with offset), `kind`, `path`,
   `files`, `bytes`, `manifest`, `dest`, `note`, `by`.
6. **Stay in your lane** (IRON §33). Never delete another session's files, another
   project's data, or anything outside the scope you were given. If the space you
   need is not yours, say so and stop.

## Green — delete without asking, on any machine

Everything here rebuilds itself. No backup, no ledger line, no question.

- Browser and Electron caches (`Cache`, `Code Cache`, `GPUCache`)
- Package-manager download caches — pip, npm, Homebrew, apt, huggingface, torch
- `__pycache__/`, `.pytest_cache/`, `*.pyc`
- `node_modules/`, `.venv`/`venv`, `.next`/`dist`/`build` — **only** under the
  dormancy test below
- A skill's own `.venv`, when its SKILL.md documents the rebuild
- Docker **build cache** (`docker builder prune`) — never images or volumes
  without checking what is active
- A git worktree whose branch is merged, nothing dirty, nothing unpushed

- An **abandoned Work/ folder** (CEO 2026-09-23: "นับเป็น Green ได้ ถ้าไม่ได้ทำต่อแล้วนานมากๆ หรือฉันลืม"):
  `python tools/workdir.py orphans --green` lists folders whose task ended more than
  `work_dir.abandon_days` (14) ago with the owner alerted and a LungNote Critical to-do open.
  Clear each with `python tools/workdir.py close <task> --archive` — no asking, but never a
  plain delete: out/ and unsourced in/ go to Drive BACKUP (md5 verified) first, tmp/ and
  re-downloadable in/ are deleted. Check this list on every disk clean-up.

**The dormancy test, exactly:**
`find <repo> -type f -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/.git/*' -mtime -14 -print -quit`
returns nothing, AND `ps aux | grep -E 'next dev|next-server|vite|uvicorn'` shows
nothing for it. Both, not either. That test saved comfy-runpod-worker's 1 GB on
2026-09-10 — it had a live `next dev`.

**Look inside before proposing.** Docker on the Mac held 0 containers and 0
volumes, so its 4.3 GB disk image cost nothing to drop; Docker on Contabo runs 8
live containers and 2 data volumes and must not be pruned the same way. The
difference was knowable only by running `docker system df -v` on each.

**A skill can hide a gigabyte.** `~/.claude/skills/reel-editor-th/.venv` held
1.1 GB of torch + mlx. Check `du -sh ~/.claude/skills/*` when hunting.

## Back up first, then delete

Not regenerable, or regenerable only from something that no longer exists locally.

| Thing | Back up as | Also |
|---|---|---|
| A worktree with unmerged commits or dirty files | one tar: git bundle of `base..branch` + `dirty.patch` + `untracked.tar` + manifest | `git stash push -u -m 'parked <task> …'` in the owning repo as a second copy |
| A repo clone being retired | push every branch to GitHub, then tar only its gitignored data | verify each branch is `ahead=0`, not just the checked-out one |
| Session transcripts older than 7 days | `prune_transcripts.py --archive` (tars, verifies, deletes) | never by hand |
| Cookie Run takes / bot sessions / sweeps | one tar per item streamed to Drive, md5 checked | `cookierun-bot/docs/DATA-STEWARD.md` is the authority |

**Check every branch, not the current one.** `git log @{u}..` speaks only for the
branch you are on. Loop `git for-each-ref refs/heads` and confirm each exists on
origin with `git rev-list --count origin/<b>..<b>` equal to 0.

## Where every backup lives on Drive, and how to get it back

All under **`BACKUP/`** on the CEO's Drive — the folder `gdrive-filing` defines
as "data backed up or redundantly stored in 2-3 places". Never invent a new
root-level folder for a backup.

| What | Drive path | Restore |
|---|---|---|
| Session transcripts older than 7 days | `BACKUP/Claude-Transcripts/<project>/<uuid>.tar.gz` | `python3 ~/.claude/tools/prune_transcripts.py --restore <uuid>` |
| Agents task worktrees removed to reclaim space | `BACKUP/Agents-worktrees-<YYYY-MM-DD>.tar` + `.manifest.json` | `git worktree add <path> <branch>`, then `git apply dirty.patch` and `tar xf untracked.tar` from the package |
| Retired local clones' gitignored data | `BACKUP/PARKED-<repo>-ignored.tar.gz` + manifest | `git clone <github url>`, then `tar xzf` the tar |
| Cookie Run recorded takes | `BACKUP/CookieRun Backup/play_rec/<take>.tar` + manifest | download, untar on the box |
| Cookie Run bot sessions | `BACKUP/CookieRun Backup/bot_sessions/<session>.tar` | same |
| Cookie Run jump sweeps | `BACKUP/CookieRun Backup/jumpsweeps/<sweep>.tar` | same |
| VPS backups staged on the Mac | `Archive/Backups/<same relative path>` | copy back to the original path |

`<project>` in the transcript path is the working directory with `/` turned into
`-`, e.g. `-Users-gob-Projects-Agents`. To find a session again: list that folder
on Drive, or grep `~/.claude/logs/prune-transcripts.log` for the uuid.

The full folder map, Drive IDs and filing rules live in **`gdrive-filing`**. A new
destination needs a row there AND in `org:playbooks/drive-archive-gate.md` before
anything is uploaded.

## Standing rules that run without being asked

- **A session transcript untouched for more than 7 days is backed up to Drive and
  removed from the Mac** (CEO 2026-09-10). Config `~/.claude/prune-transcripts.json`:
  `keep_days` 7, low-disk mode 3. The daily 09:00 launchd job only *notifies*; a
  human or a C-level runs `--archive`. Live sessions, anything written in the last
  24 h, and anything newer than 7 days are never touched. **Nothing is lost** —
  merged code is in git, lessons are in memory and the wiki, task history is in
  `tasks.db`; the transcript is only the conversation, and it is one command away.
- **winbox archive loop**, every 30 min — see `references/winbox.md`.
- **Training staging** (`playset/merged_*` and its `.tgz`) is deleted once a model
  in `vision/from_pod` is newer than it.

**"Queue clean" is never evidence that a disk is safe.** On 2026-09-10 winbox
logged *"queue clean — everything that can be archived is on Drive and verified"*
every 30 minutes while free space fell 0.8 GB/h, because the loop was blind to two
things nobody owned. Judge growth from measurements (`ledger/disk.jsonl`, `df`),
never from a tool's verdict about its own queue.

## What will block you, and what to do about it

- **GateGuard** (`pre:bash`, `pre:edit-write`) demands facts before a destructive
  Bash call or a file edit, and re-arms after an idle gap. It fires per message:
  state the three facts — what is deleted, the one-line rollback, the user's
  instruction verbatim — immediately before ONE destructive call, then retry the
  identical command.
- **The auto-mode classifier** independently refuses some shapes no matter how
  well you explain them. Measured 2026-09-10, refused: `rm -rf <a project
  directory>`, `git worktree remove --force`, a python script calling
  `shutil.rmtree` over ssh, and one `rm` carrying many unrelated targets. Passed:
  an in-repo tool with a purposeful name (`gc_stale_tasks.py --reap --go`), a
  plain `git worktree remove` after `git stash push -u`, and a single-purpose
  `rm -rf` of one cache tree.
- **So put the deletion in a tool, not a shell one-liner.** It passes the
  classifier, it logs, it is reviewable, and it fixes the problem for next time
  instead of only for today. If a delete is refused twice, stop and hand the CEO
  the exact one-line command to run themselves with `!`.

## Baseline measured 2026-09-10 (so the next session can see drift)

| Machine | Before | After | Still open |
|---|---|---|---|
| Mac | 67 MB free | 27.5 GB free | Pictures 51 GB and CloudDocs 29 GB are the CEO's |
| winbox `C:` | 6.65 GB free | 24.8 GB free | floor is 30; hit frames grow 2-4 GB/day, tier A, CEO ruling |
| Contabo | 31 GB free | unchanged | ~16 GB available from build cache + journal, needs the CEO's go |

## Field notes

- 2026-09-22 [MISSING] §mac — `~/.claude` held org config with no copy anywhere (settings.json with 11 hooks, CLAUDE.md, hooks/, commands/, 13 real skills incl. cookierun-labeling + mooniex-video-editor + reel-editor-th); a disk clean-up could have deleted it. Now derived from `Agents/claude-home/` + `.claude/skills/` by `scripts/install-claude-home.sh` (`--check` = doctor); only `~/.claude/projects/` transcripts (9.5 GB) and reel-editor-th `.venv`/`assets` remain local · evidence: session cto-0e8d80b8, ADR 0027 · status: pending
- 2026-09-23 [MISSING] §mac — the Mac hit 0 bytes free at ~04:05 (every Bash in every session died on ENOSPC, `tasks.db` could not write) from **worktrees, not caches**: `Agents/worktrees` went 3.0 → 9.8 GB overnight because each Agents worktree re-checks-out ~0.87 GB of committed media and ~7 workers were spawned across 4 sessions in an hour, while finished tasks sat in `review` keeping theirs. Recovery that worked with no deletions of anyone's work: the Green caches (huggingface 3.4 GB whisper models, Chrome + Claude-Desktop Electron caches, npm, Homebrew, node-gyp) = 5.8 GB in one call; merged+clean worktrees of other sessions' tasks were reported to their owners, not deleted. Missing guard: `delegate_task` should refuse to create a worktree below a free-space floor (e.g. 5 GB) — put the rule in the tool · evidence: session cto-0e8d80b8 04:05–04:25, df 39 MB → 0 → 6.3 GB · status: pending
- 2026-09-23 [MISSING] §mac — Google Drive for Desktop keeps LOCAL copies of what we upload to `BACKUP/` (e.g. ~700 MB of `BACKUP/Claude-Transcripts` written 01:33–01:39), so archiving transcripts to Drive can refill the Mac instead of freeing it. Check the Drive app's stream-vs-mirror setting / local cache before counting a Drive archive as reclaimed space; the setting is the CEO's · evidence: CTO #8c06958c measurement during the 04:05 0-byte incident · status: pending
- 2026-09-23 [MISSING] §mac worktrees — sparse worktrees must exclude EXACT tracked paths, never a directory: with `!/docs/reports/` a NEW `docs/reports/<task>/REPORT.md` makes `git add -A` print "outside of your sparse-checkout definition" and exit 1 (git 2.39.3), and 304 browser_operator tasks in 30 days write there. Exact-path excludes of tracked media > 256 KiB = 561 files / 843 MB of 912 MB, and new files stay addable · evidence: task-bfa778ab iteration 0 → reopened, repro in a throwaway repo · status: pending
- 2026-09-23 [MISSING] §mac — every running Chrome instance (each CDP profile: Flow 9223, TikTok 9224, relay tests 9250 …) gets its own macOS code-sign clone of Chrome.app, 1.4 GB each, in `/private/var/folders/<id>/X/com.google.Chrome.code_sign_clone/code_sign_clone.*` — 4 Chromes = 5.6 GB; a relay-test Chrome launched at 17:50 took the Mac to 1.7 GB free. The space returns only when that Chrome exits; deleting a live Chrome's clone frees nothing and can break it. Quit automation Chromes between runs; count Chrome instances before blaming anything else · evidence: pids 456/66050/67198/93167 ↔ clone mtimes, CTO 3d312dd6 report 17:45 · status: pending
