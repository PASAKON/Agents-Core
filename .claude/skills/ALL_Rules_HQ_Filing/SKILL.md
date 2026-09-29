---
name: ALL_Rules_HQ_Filing
kind: rules
owner: COO
aka: [hq-filing]
origin: mooniex-org
scope: >-
  Filing rules for MoonieX HQ (~/MoonieXHQ) — where every repo, dataset and clone lives on
  the Mac, what may be created there and by whom. Read before creating, moving, cloning,
  renaming or deleting any folder under HQ or under the three legacy roots. Rules + the
  map's location; the map itself is hq.yaml in the HQ repo.
description: RULES — Filing rules for MoonieX HQ — read before creating/moving/cloning/renaming/deleting any project folder on the Mac, before `git clone`, before deciding where a new repo, dataset, render or third-party clone goes. Trigger on /ALL_Rules_HQ_Filing, "MoonieX HQ", "จัดโฟลเดอร์", "โปรเจคนี้เก็บที่ไหน", "clone มาไว้ไหน", "สร้าง repo ใหม่", "where does this repo live", "folder layout", "ย้ายโปรเจค". Use instead of guessing a path under ~/Projects. Google Drive filing is `CXO_Rules_GDrive_Filing`; local disk clean-up is `ALL_Rules_DiskHygiene`; the inside of a project is `Agents-Rules/playbooks/project-layout.md`.
created_by: human
audience: [all]
---

# HQ filing — the map decides, the disk follows

The **one map** is `~/MoonieXHQ/hq.yaml` (rendered to `MAP.md`). This skill is the rules for
using it. When the CEO defines a folder or changes a rule, edit the yaml (and this file if the
rule changed) — never restate the map in memory or a CLAUDE.md.

## Hard rules
1. **No folder without a row, no row without CEO approval.** Every folder under HQ appears in
   `hq.yaml` (path · kind · repo · owner · keeps · never · current · machines) before it exists on
   disk, and the CEO approved the row (CEO 2026-09-22). Propose the row in chat, wait for yes,
   then `git clone` / `mkdir`. **Why hard:** the CEO's own rule — order over speed; an
   unapproved folder is exactly the mess HQ replaces.
2. **path ⇔ repo bijection.** `Projects/<Brand>/<Suffix>` ⇔ `github.com/PASAKON/<Brand>-<Suffix>`
   (ADR 0012 naming). Read a path → you know the repo; read a repo → you know the path.
   Folder names PascalCase, no spaces, no hyphens (`ClaudeFlow`, not `claude-flow`).
3. **One project = one folder = one repo, fully independent.** Never import another
   project's code, read its files, or share a database table with it. **Projects talk only through
   APIs** (CEO 2026-09-22: ClaudeFlow reads LungNote through LungNote's API). A project must keep
   working when moved to another host. Cross-project need with no API = the task is "add the API".
4. **One clone per repo per machine** (ADR 0007). Parallel work = `git worktree` under the runtime's
   worktree dir, GC'd within 7 days. `hq doctor` flags a second clone as a duplicate.
5. **Media, datasets, renders, venvs never in a code repo folder.** They go to `Assets/<Brand>/<Suffix>/`
   (not git). Trainable datasets and delivered renders are also on Google Drive (`CXO_Rules_GDrive_Filing`);
   cache/intermediate stays local. A pre-commit hook refuses media > 5 MB.
6. **Other people's code → `External/`, read-only, pinned commit.** To change it, fork to
   `PASAKON/<Brand>-<Suffix>` and give it a `Projects/` row first (AlphaTrader 2026-09-22 is the precedent).
7. **Archive rule.** On GitHub → no extra backup, delete the local folder. Not on GitHub → back
   up to Drive (CXO_Rules_GDrive_Filing) then delete. Only a restore note stays (in `Agents/Rules/reference/`).
   "On GitHub" means every local branch's sha is on origin or an ancestor of its default branch, read
   live (`git ls-remote` + `merge-base --is-ancestor`), never from cached refs or a survey — the same test
   clears a duplicate clone (rule 4). A survey's `ahead=0` against a stale ref hid 4 branches in a dup the
   CEO had approved as "safe to delete" (task-ad534f86).
8. **`UNKNOWN/` is the fallback, never a guess** — and it must be empty at `/session-close`
   (each item either got a row or left).
9. **Map and disk agree in the same turn.** Any move/clone/rename/delete you make — or find already
   happened — updates `hq.yaml`, re-renders `MAP.md`, and `hq doctor` is clean before the turn ends.
10. **Search real repo paths.** `find`, `rg`, `grep -r` return **zero, with no error**, through a
    symlink hub (measured 2026-09-22, 204 files vs 0). Never point a search at a folder of links.

## Machines
The map is the Mac's layout; each row records other checkouts under `machines`. **Contabo** uses the
same names under `/opt/MoonieXHQ` since 2026-09-23/24 (`machine_roots` in hq.yaml; record
`docs/ops/contabo-hq-migration-plan-2026-09-23.md`). The real folder sits under `/opt` because `/root`
is 0700 and non-root services (secretary, driveup, photoup) must reach Agents/Core; `/root/MoonieXHQ`
links to it, and folders moved out of `/root` are chmod 700. Its old paths (`/opt/mooniex-agents`,
`/root/projects/…`, `/opt/*-wikis`) are compat links until ≈2026-10-01 — write the new path. Its wikis
are rsync snapshots. **winbox** paths are per row (CookierunBot's home is there). Git is the only
channel between machines; never copy files across.

## Migration (2026-09) and moving a folder
Mac: ① map → ② `Projects/LungNote` + `Projects/WarpClip` → ③ `Projects/MoonieX/*` → ④ `Agents/*`
all ran 2026-09-22/23; ⑤ removed the unused compat links — `~/Projects/Agents` and three links that
tracked scripts still hardcode remain, each with its `remove_when` in hq.yaml `compat_links`. Contabo
moved 2026-09-23/24 (§Machines). A row's `step` says when it moves; `current` says where it is today.
Nothing moves outside its step.

Moving a repo or folder — each of these broke something in 2026-09:
1. **Link the old path in the same step as the `mv`** (`os.rename` + `os.symlink` in one call), before
   any repair, push or verify: a crash in that window left `com.mooniex.console-mac` without a working
   directory (task-b5f61b47). A migrate script is resumable — an old path that already resolves to its
   target is done, not an error (b3ad7213).
2. **`git worktree prune` before `git worktree repair`**: a dangling admin entry (dir deleted without
   `git worktree remove`) makes repair refuse with "not a valid path" (task-b5f61b47).
3. **Point env vars, launchers and searches at the real path, not the link.** `find` without `-L`
   returns 0 through a link given as its start path, while `grep -r` and `os.walk` see all 96 files
   (Contabo 2026-09-23). Pin `COMPOSE_PROJECT_NAME` in the `.env` before moving a compose project, or
   the folder's basename renames it.
4. **Never alias a Claude project slug dir with a symlink**: Claude Code refuses to spill oversized tool
   results through it ("tool-results path refused: … is a link or not a directory") and large MCP
   results are lost. Make the new slug a real dir — its `memory` may be a link (Mac, 2026-09-23), or
   hard-link the transcripts into it (Contabo, 2026-09-24).
5. **Grep the old path everywhere before calling a repoint done, and again before removing a compat
   link** — tracked text of every kind in every repo (`.md` too), launchd plists / systemd units and the
   scripts they run, every project's `.env*` — then run the full suite. A subset failed both times: the
   4b `--repoint` rewrote only `.py` (20 live `.md` files and one test's expected slug kept the old path,
   d53e2dd2); step ⑤ judged 16 links unused from live processes and `com.mooniex.console-mac`
   crash-looped until MoonieX-Console 41f9ee6, so 3 links came back with a `remove_when`.
6. **After moving a Next.js app, delete `<app>/.next` and restart dev from the new path**: Turbopack's
   persistent cache keeps the old absolute path, and `next dev` threw `Module not found` 71,904 times in
   ~70 s though the package was installed (ComfyRunpod studio, 2026-09-25).

## Verbs
```bash
PY=/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python
$PY ~/MoonieXHQ/scripts/hq.py map              # hq.yaml → MAP.md
$PY ~/MoonieXHQ/scripts/hq.py doctor           # disk vs map; exit 1 on any disagreement
$PY ~/MoonieXHQ/scripts/hq.py show Projects/LungNote/Mcp
```

## Related
`CXO_Rules_GDrive_Filing` (Drive side of rule 5 and 7) · `ALL_Rules_DiskHygiene` (what may be deleted locally) ·
`Agents/Rules/playbooks/project-layout.md` (inside a project) · `Agents/Rules/IRON-RULES.md` §54 ·
ADR 0028 · `Agents/Wikis/research/README.md` (the research cache — search it before the web).

## Field notes

- 2026-09-22 [MISSING] §Migration — a duplicate clone the CEO approved as "safe to delete" held 4 branches that existed nowhere else (the survey's `ahead=0` was against a stale remote-tracking ref). The migration script's live `git ls-remote` + `merge-base --is-ancestor` check caught it; rule to fold: a dup is deletable only when every local branch sha is on origin or an ancestor of origin's default branch — never from cached refs, never from the CEO's read alone · evidence: task-ad534f86 iteration 1, WarpClip-webapp → §Hard rules 7 (clarifies "On GitHub"; stricter, artefact) · status: promoted
- 2026-09-23 [MISSING] §Migration — a repo's `git worktree list` can carry a DANGLING admin entry (worktree dir deleted without `git worktree remove`); `git worktree repair` refuses it ("not a valid path") and a script that treats that as fatal crashes mid-apply. Drop entries whose path no longer exists (`git worktree prune`) before repairing · evidence: task-b5f61b47, `/private/tmp/console-review` on mooniex-console, manifest hq-step3-migration-20260923T020936 → §Migration item 2 · status: promoted
- 2026-09-23 [MISSING] §Migration — when a live launchd/systemd job's WorkingDirectory is a repo being moved, the compat symlink must be created IMMEDIATELY after the `mv`, before any repair/push/verify step — the crash above landed in that window and `com.mooniex.console-mac` briefly had no working directory. Also: every migrate script must be resumable (a row whose old path already resolves to its target is done, not an error). Step ④ (Agents-Core = the runtime itself) inherits both rules · evidence: task-b5f61b47 incident section, commit b3ad7213 → §Migration item 1 (Contabo step 5 applied it 2026-09-24: rename + link in one call) · status: promoted
- 2026-09-23 [MISSING] §Migration — the 4b "org quiet" gate counts task STATUS rows, not live work: one rate_limited task whose worker sat idle at its prompt (report submitted) blocked the move. Added `--ceo-override-idle <id>` (repeatable, printed loudly) — use it only after reading the worker's pane and only on the CEO's word · evidence: task-95439aa8, 93f22ea0, apply 2026-09-23 13:17 — rejected: the gate and its flag live only in the one-off scripts/hq_migrate_step4b.py; step 4b ran 2026-09-23 and the Contabo move finished 2026-09-24 without it · status: rejected
- 2026-09-23 [MISSING] §Migration — the step-4b `--repoint` rewrites only `.py`; 20 live `.md` files (skills, claude-home CLAUDE.md + spawn commands, README) still named the old path, and one test's INPUT was rewritten while its EXPECTED slug was not (test_memory_sync). After any repoint: `git grep` the old path across all text files and run the full suite · evidence: merge d53e2dd2 → §Migration item 5 (merged with the 2026-09-23 compat-link note) · status: promoted
- 2026-09-23 [WRONG] §Migration — the 4b "Claude slug alias" (new slug dir = SYMLINK to the old slug) breaks every session launched from the new path: Claude Code refuses to spill oversized tool results through it ("tool-results path refused: …-Users-gob-MoonieXHQ-Agents-Core is a link or not a directory"), so large MCP results are lost. Fix used 13:55: the new slug is a REAL dir whose `memory` is a symlink to ~/MoonieXHQ/Agents/Memory (a symlinked memory/ inside is fine — the old slug already worked that way); move only the transcripts of sessions launched from the new path into it. Never alias a whole project slug dir · evidence: report by CTO b4ed592c 2026-09-23 06:52Z; manifest state/hq-step4b/ (its Phase E rollback now targets a dir, not a link) → §Migration item 4 (Contabo step 5 used a real dir + hard links, 2026-09-24) · status: promoted
- 2026-09-23 [MISSING] §Machines — on a box where `/root` is 0700 and some units run as non-root users (Contabo: secretary, driveup, photoup must reach Agents/Core), the HQ folder cannot live under `/root`. The real folder goes under a traversable path (`/opt/MoonieXHQ`, an HQ clone), and `/root/MoonieXHQ` links to it so `~/MoonieXHQ` still resolves; folders moved out of `/root` get chmod 700 to keep their old protection · evidence: Contabo move f8f0e5a8, docs/ops/contabo-hq-migration-plan-2026-09-23.md §Executed → §Machines · status: promoted
- 2026-09-23 [MISSING] §Migration — a compat link hides files from `find` (0 results without -L) while `os.walk`, `grep -r` and `Path.rglob` see them (96 files), so point env vars and launchers at the real path, never at the link. Moving a compose project also renames it (the folder basename becomes the project name) unless `COMPOSE_PROJECT_NAME` is pinned first · evidence: Contabo 2026-09-23, same record → §Migration item 3 · status: promoted
- 2026-09-23 [WRONG] §Migration — step 5 judged the 16 `~/Projects/*` compat links "unused" and removed them. `com.mooniex.console-mac` then crash-looped (ERR_MODULE_NOT_FOUND) because `scripts/mac-console.sh` and the Console `.env` (TLS paths, ORG_ROOT) still named `~/Projects/mooniex-console`, so the phone lost every Mac session until cto-b4ed592c fixed it (MoonieX-Console 41f9ee6). A later sweep found 4 more tracked scripts hardcoding removed paths (CookierunBot jump_*.sh, the ComfyRunpod pod-stop watchdog, WarpClip render-png.sh), so 3 links were restored with a `remove_when`. Before removing any compat link, grep the old path across launchd plists, the scripts they run, every project's `.env*`, and tracked `*.sh|*.py|*.js` in every repo — not only live processes · evidence: cto-b4ed592c letter 2026-09-23T16:52Z, hq.yaml compat_links → §Migration item 5 (merged with the d53e2dd2 note; the Contabo plan adopted the same check) · status: promoted
- 2026-09-25 [MISSING] §move — moving a Next.js project breaks its Turbopack persistent cache: `.next/dev/cache/turbopack` keeps the OLD absolute path (grep found `Projects/comfy-runpod-worker` in the .sst files), so after the move `next dev` threw `Module not found: Can't resolve 'lucide-react'` 71,904 times in ~70 s at 457% CPU although the package was installed. After moving any Next app: stop dev, delete `<app>/.next`, restart from the NEW path · evidence: ComfyRunpod studio 2026-09-25 07:08, fixed by CTO 6bfdc084 (/ and /render 200 after) → §Migration item 6 · status: promoted
- 2026-09-28 [MISSING] §Migration — the compat-link sweep in the note above also missed `~/.claude/skills/*`: 21 user-level skill symlinks still pointed at `~/Projects/external/…` and `~/Projects/mooniex-claude-skills/…` after those links went, so skills CLAUDE.md routes to by name (debug-mantra, scrutinize, post-mortem, diagram-design, mooniex-growth/content/kpi/seo/retention/tool-builder) silently stopped loading for about 5 days. The targets were intact at `~/MoonieXHQ/External/…` and `~/MoonieXHQ/Agents/Skills/…`, so `ln -sfn` to the new path fixed all 21. Add to the pre-removal checklist: `for l in ~/.claude/skills/*; do [ -L "$l" ] && [ ! -e "$l" ] && echo $l; done` must print nothing · evidence: CMO a82def00 letter 2026-09-27T19:43Z; old targets logged in CTO db340a19 scratchpad skill-relink-old.txt · status: pending
