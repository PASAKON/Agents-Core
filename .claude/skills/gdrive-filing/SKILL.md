---
name: gdrive-filing
owner: CFO
origin: mooniex-org
scope: >-
  Filing rules for the CEO's personal Drive (pass.gob1@gmail.com) — where things
  live and what AI may create, move, rename, or delete. Read before any Drive
  mutation, whether via the gdrive-bridge script or the Drive MCP tools. Rules
  only; not a file-transfer tool.
description: Filing rules for the CEO's Google Drive — read before ANY Drive action (create/upload/move/rename/delete, rclone, the gdrive-bridge, the Drive MCP). Trigger on /gdrive-filing, "จัดระเบียบ Drive", "ย้ายไฟล์ไป Drive", "เก็บไฟล์นี้ไว้ที่ไหน", "ลบไฟล์ใน Drive", "save this to Drive", "file this", "backup to Drive", "สำรองไป Gdrive", "upload to Drive", "rclone", "Google Drive". A PreToolUse hook (scripts/hook-gdrive-skill-gate.py) blocks Drive-touching tool calls until this file has been read in the session.
created_by: human
audience: [cxo]
---

# Google Drive Filing — CEO's personal Drive (pass.gob1@gmail.com)

This is the **one place** filing rules and the folder map live. When the CEO
defines a new folder or changes a rule, edit THIS file — do not duplicate
rules into memory, CLAUDE.md, or anywhere else. Every session reads this same
file, so it stays consistent without re-explaining itself each time.

## Hard rules — apply to every action, no exceptions

1. **Ask before doing anything.** No silent create/move/rename/delete. (Bulk uploads: see the "Bulk transfer" chapter — same rules, plus verification and a gate row.)
2. **Never delete without being told, and always confirm first.** Before any
   `trash` call: state which file/folder, why you believe it's safe (e.g.
   "confirmed empty via search"), and wait for an explicit yes. **Re-verify
   emptiness right before deleting** even if a memory/skill note says a
   folder was empty before — folders that looked empty earlier can pick up
   real content later (happened 2026-08-04 with `Media (สื่อ)` and `_Review`).
3. **Never create a new sub-folder without asking first.** You may *propose*
   one when a file doesn't fit any existing definition — wait for approval,
   then create it.
4. **Every folder must have a definition before you file into it.** Use the
   map below to decide placement. If nothing fits, it goes to `UNKNOWN`.
5. **`UNKNOWN`** (Drive root) is the fallback — anything you can't confidently
   place, or that has no folder yet, goes there instead of guessing. Moving
   an *existing* folder (with its own pre-existing internal structure) into
   `UNKNOWN` is fine even though it then has sub-sub-folders — the 1-level
   cap governs what AI creates fresh inside `UNKNOWN`, not folders relocated
   there wholesale.
6. **Keep the tree and table in sync, same turn.** Any rename/move/create/
   delete you perform — or notice already happened outside this session —
   updates BOTH the ASCII tree and the ID table below immediately. They must
   never drift apart. After editing, paste the updated tree back to the CEO
   in chat so they see it without having to open the file.
7. **Never invent a folder's definition.** If you find a folder (new, or an
   existing one still marked "undefined" below) with no definition, ask the
   CEO what it's for — do not guess or summarize one yourself from the name
   or its contents. Only write a definition down once the CEO has actually
   told you, close to their own words, not your interpretation of them.
8. **Depth caps, per branch (confirmed 2026-08-04, PROJECT levels clarified 2026-08-05):**
   - `UNKNOWN` — max **1** sub-folder level. See its own protocol below.
   - `PROJECT` — max **3 levels under the project folder** (CEO's own numbering):
     `PROJECT/ → L1 = project name e.g. MOONIEX → L2 = category, named for
     what it holds → L3 = sub-category, ONLY when L2 has genuinely too much
     data to stay flat`. No level beyond L3. See "PROJECT — level semantics"
     below for how AI is allowed to create L2/L3 categories.
9. **IDs are the real identifier, names are just a label.** Drive IDs never
   change on rename/move; titles do. Always resolve against the ID table
   below (or a fresh search) before calling the bridge — never act on a
   name match alone.

### UNKNOWN — filing protocol (exception to Rule 1)
When the CEO sends a batch of files that are clearly the same group (sent
together, one request): file them directly into `UNKNOWN` **without asking
first** — this is the one standing exception to Rule 1. After filing, report
back how many you filed and how many you couldn't place (with why). Every
filed item gets renamed to:
```
(original file name) (D-M-YYYY) (SID:xxxxxxxx)
```
e.g. `(PosterLiquid) (3-06-2026) (SID:dqeqwe23)` — SID is this session/
conversation's id (same convention as LungNote's `[SID:...]` tag, IRON §40).

### PROJECT — level semantics & category creation protocol (confirmed 2026-08-05)
- **L1** (e.g. `MOONIEX`) = the project name. Fixed, one per project.
- **L2** = a category inside that project — its name must describe what
  group of data it holds (e.g. "Mooniex Finance", "Company & Legal").
- **L3** = a sub-category of one L2 folder, only created when that L2's
  data has genuinely grown too much to stay flat (e.g. `Mooniex Finance` →
  `Contracts`, `Invoices`).
- **Naming/defining L2 and L3 is AI's judgment call, always subject to CEO
  approval before creating.** Investigate the actual file/data first — don't
  guess blind. Propose a name + definition, wait for the CEO's yes, then
  create it.
- **If a file is clearly within a known project (e.g. obviously MOONIEX-
  related) but no existing L2 category fits it, propose a NEW L2 category
  under that project — do NOT default it to `UNKNOWN`.** `UNKNOWN` is for
  files where even the *project* is unclear, not for "right project, no
  category yet."

### AI Assets footage naming (confirmed 2026-08-04)
Every AI-generated clip inside `AI Assets/<CHANNEL> (ratio)/` gets renamed to:
```
(scene/purpose) (D-M-YYYY) (AI model)
```
e.g. `(RunningMan) (3-10-2026) (Kling V3 Pro).mp4`. If two files would get an
identical name (near-duplicate takes, same scene/date/model), the CEO has
authorized `Name`, `Name_1`, `Name_2`, … suffixes rather than blocking on it.
Determine the real AI model from the actual generation pipeline/commit
history when possible (don't guess) — e.g. the mooniex-claudeflow
`videolib.js` `VIDEO_MODEL_T2V`/`VIDEO_MODEL_I2V` constants + git history
pinned "Kling V3 Pro" (`fal-ai/kling-video/v3/pro/...`) as the model for
every file generated 2026-04-10 through at least 2026-05-19.

### External auto-backups landing in Drive (Facebook, etc.)
Meta's "Export your information → Google Drive" recurring-transfer feature
(Facebook Account Center → Your information and permissions → Export your
information) has **no destination-folder setting** — it always drops a fresh
`meta-YYYY-Mon-DD-HH-MM-SS` folder at Drive **root**, no matter what. There is
no way to point it at `BACKUP/Facebook Backup` directly (checked 2026-08-04).
Workaround: whenever a new root-level `meta-*` folder shows up, move it into
`BACKUP/Facebook Backup` (this skill's job, not something to keep asking the
CEO to drag manually). Also note: the CEO has **two** Facebook profiles
(`Pasakon Gobb` and `Dorsine Gobb`) — the real recurring export lives under
**Pasakon Gobb**; double-check which profile before touching Facebook export
settings again.

## Folder tree (down to the deepest level worth tracking by name)

Checked/updated 2026-08-04. Names below are for humans to scan — **the table
further down (with Drive IDs) is what you actually resolve against.**

```
Google Drive (root) — pass.gob1@gmail.com
├── UNKNOWN/                      fallback, nothing fits / no folder yet
│   ├── claudeflow-media-archive/ org auto-backup (moved in 2026-08-04)
│   ├── Media (สื่อ)/              turned out non-empty, moved in 2026-08-04
│   └── _Review (ไม่มีชื่อ)/       turned out non-empty, moved in 2026-08-04
├── PROJECT/                      non-video per-project stuff (docs/images/billing)
│   ├── MOONIEX/                  merged from old root MoonieX — 19 pre-existing
│   │   │                         category folders below, NONE individually
│   │   │                         defined yet (names only, ask CEO for each).
│   │   │                         Depth-audited 2026-08-05 against the L1/L2/L3
│   │   │                         cap: 2 real violations found + flattened
│   │   │                         (EA File/MoonX Farm, Employee File/Employee
│   │   │                         Image — see their rows below); User Files/
│   │   │                         LINE stays exempt (auto-gen, not real
│   │   │                         taxonomy). Everything else already ≤3 levels:
│   │   ├── Rate Cards & Profile/
│   │   ├── Content Scripts/
│   │   ├── Tools & Sheets/
│   │   ├── Company & Legal/
│   │   ├── Project Backup/       → WarpClip/, LungNote/, MoonieX/ (1 more level)
│   │   ├── Broker Info & Data/
│   │   ├── Proposals/
│   │   ├── Mooniex Finance/      → Contracts/, Invoices/, Marketing/,
│   │   │                           Quotations/, Company Docs/, Payslips/
│   │   ├── Logos/
│   │   ├── Images/               → 📰 Economic calendar/, 📈 Pivot Points/,
│   │   │                           📊 iDeaTrade/
│   │   ├── User Files/           → LINE/ ⚠ auto-generated LINE backup,
│   │   │                           50+ opaque folders, leave alone —
│   │   │                           User Images./
│   │   ├── EA File/              → Hub Semi & Full Auto/, MoonX Settings/,
│   │   │                           MoonX Farm/ (flattened 2026-08-05 — was
│   │   │                           4-5 levels via V3.2/Settings/, now all 5
│   │   │                           files sit directly in MoonX Farm/),
│   │   │                           การติดตั้ง EA MoonX Farm. (Video)/
│   │   ├── Moonez/
│   │   ├── Poster/
│   │   ├── Fastwork/             → MoonieX Company/, MoonieX Box/,
│   │   │                           MoonFlow SMC Slide/
│   │   ├── เอกสารประกอบการเรียน BASIC FOREX (2024) by mooniex/
│   │   ├── Employee File./       → Employee Image./ (flattened 2026-08-05 —
│   │   │                           was 4 levels via ID Card/, now 6 ID photos
│   │   │                           sit directly in Employee Image., each
│   │   │                           renamed "ID Card - <Full Name>.jpeg" to
│   │   │                           avoid all colliding as "line_item.jpeg")
│   │   ├── Banners/              → Economic Calendar/
│   │   └── Policy .PDF File/     → Thai Version./, English Version./
│   ├── LUNGNOTE/
│   ├── BRAND PROMPT/
│   ├── WARPCLIP/
│   └── LINKREED/
├── ALL DRAFT/                    video projects, per channel
│   ├── ASSETS/                   shared across every channel
│   │   ├── ALL Assets/           cross-project general assets (image or
│   │   │                         video), named for subject — not tied to
│   │   │                         one channel or broker
│   │   ├── AI Assets/            AI-generated B-roll, VIDEO ONLY —
│   │   │   ├── BLACK LIQUIDITY (9:16)/   ← naming order CONFIRMED as
│   │   │   └── BLACK LIQUIDITY (16:9)/     "CHANNEL (ratio)", not "ratio
│   │   │                                   CHANNEL" (reverted 2026-08-04).
│   │   │                                   Every clip: (scene) (date)
│   │   │                                   (model) — 21 BLACK LIQUIDITY
│   │   │                                   clips renamed 2026-08-04.
│   │   │   MYPASAKON (9:16)/, MYPASAKON (16:9)/ — same pattern, currently
│   │   │   empty, created 2026-08-04 ready for future footage
│   │   ├── XM Assets/            → sub-folder per real-world EVENT (e.g.
│   │   │                         "XM GALA DINER 2024"), holding every
│   │   │                         photo/video shot during that event —
│   │   │                         ALREADY matched this pattern, no fix needed
│   │   └── Exness Assets/        same event-folder pattern — ALREADY matched,
│   │                             no fix needed
│   ├── BLACK LIQUIDITY/          ~20 numbered clip folders — each one has
│   │   └── <clip title>/         AI Drafts (or Final Draft) / Audio / Rawcut /
│   │                             Thumbnail / Convert to .mp3 inside
│   ├── MYPASAKON/                50-90+ clip folders — same production-stage
│   │   └── <clip title>/         pattern (AI Drafts / Audio / Finals) inside.
│   │                             14 folders here had "myPasakon" casing
│   │                             fixed to "MYPASAKON" 2026-08-04.
│   ├── YT: MYPASAKON/             YouTube cut of MYPASAKON — same per-clip
│   │                              / production-stage pattern as BLACK LIQUIDITY
│   ├── LUNGNOTE/                  video side of LungNote — same pattern; has
│   │   └── DAY0/, BRAND/          DAY0 already shows the Audio/Finals structure
│   ├── TRADE TO THE MOON/         same pattern, several TTTM-titled clips
│   ├── YT: TRADER UNCUT/          NEW 2026-08-05. New YouTube+TikTok channel
│   │   ├── EP1 | .../             (Jadoodoo/KOSPI crash) → Final Draft/,
│   │   │                          Audio/, Rawcut/, Thumbnail/, Script (doc)
│   │   ├── EP2 | .../             (Leopold Aschenbrenner) same 4 sub-folders
│   │   │                          + Script (doc)
│   │   └── EP3 | .../             (Nick Pinto/TRUMP memecoin) same 4
│   │                              sub-folders + Script (doc)
│   └── YT: ILAG/                  NEW 2026-08-12. AI-generated short-film
│       │                          channel on YouTube (ILAG Studio). Does NOT
│       │                          use the per-clip production-stage layout the
│       │                          other channels use — see the "YT: ILAG"
│       │                          section below; this branch has its own rules.
│       └── Do Not Disturb/        one PROJECT = one film/episode
│           ├── logs.txt           MANDATORY, one per project. See below.
│           ├── All Scene/         AI-generated footage, one folder per scene
│           │   ├── S1/ … S16/     renamed from "1".."6" on 2026-08-12;
│           │   │                  S7–S16 created the same day (16 scenes)
│           │   └── (S1-A, S1-B…)  sub-shots / repair takes, siblings of S1
│           ├── Element/           reference plates fed to the generator
│           │   ├── Character/     one plate per character
│           │   ├── Location/      one plate per location
│           │   └── Prop/          one plate per prop
│           ├── Soundtrack/        music + SFX + voice for this film
│           └── StoryBoard (Doc)   synopsis + link to the director's notebook
├── BACKUP/                       NEW 2026-08-04. Important data that doesn't
│   │                             fit any other folder / can't be categorized,
│   │                             or redundant copies the CEO wants kept in
│   │                             2-3 places — temporary or permanent, either
│   │                             is fine.
│   ├── FaceBook Backup/          Meta "Download Your Information" auto-export
│       ├── meta-2025-Jun.../     bundles — rarely actually used. Moved here
│       ├── ... (10 total)        from root 2026-08-04. New meta-* exports
│       └── meta-2026-Jun-18.../  land at Drive ROOT (Meta gives no destination
│                                 control) — move each one in here manually.
│   └── CookieRun Backup/         NEW 2026-09-06 (CEO-approved). Raw copies of the
│       │                     Cookie Run bot's data from the Windows box (winbox),
│       │                     uploaded by rclone as one tar per take + a sha256
│       │                     manifest — never loose frames. Steward brief:
│       │                     cookierun-bot/docs/DATA-STEWARD.md; gate row in
│       │                     playbooks/drive-archive-gate.md.
│       ├── play_rec/         <take>.tar + <take>.manifest.json (CEO's recorded takes)
│       └── (bot_sessions/, playsets/ — proposed, not created yet)
├── Desktop Cloud/                cross-device sync — AI never auto-files here
└── My Picture & Videos./         personal, filed by month
```

## Bulk transfer — moving gigabytes INTO Drive (CEO 2026-09-06)

The bridge and the Drive MCP move metadata and read files; they never carry bytes. Anything
larger than a handful of files — recordings, datasets, backups from the Windows box — goes
through **rclone**, and rclone obeys this file exactly like every other hand.

**Which hand for which job**

| Job | Tool | Notes |
|---|---|---|
| Upload GB–TB from a machine (Windows box, VPS) | `rclone` (remote `gdrive:` on that machine) | one tar per item + manifest; verify; log |
| Move / rename / create folder / trash inside Drive | gdrive-bridge (`scripts/gdrive-bridge/gdrive_move.py`) | metadata only, IDs not names |
| Search, read, verify a folder is empty | Drive MCP (`mcp__claude_ai_Google_Drive__*`) | read side |
| The Mac's synced Drive folder (stream mode) | never for bulk | the Mac has no disk for the cache |

**Rules for every bulk upload (in addition to the hard rules above)**

1. **Destination must already be a defined folder in the map with a row in the Drive archive gate**
   (`Agents-Wikis/playbooks/drive-archive-gate.md`, CEO-approved per source). No row → ask first;
   never invent a folder at the root (that is exactly what happened on 2026-09-06 and was undone).
   New folders are created ONCE with the CEO's OK — by the bridge, or by rclone when the token's
   scope must be able to see them later — and go into the tree + ID table the same turn.
2. **One tar per item, never loose files.** A take is 14k–84k JPEGs; Drive allows 500,000 items
   per folder and flags "automated mass upload". Tar it (no gzip for JPEG/MP4), stream it if the
   source disk is full (`tools/stream_take_to_drive.py` in cookierun-bot: tar → `rclone rcat`,
   hashes on the fly, no local copy), and write `<item>.manifest.json` next to it: file count,
   bytes, sha256 (and md5) of the tar, source path, date.
3. **Verify before anything is deleted.** `rclone check <src> <dst> --one-way` (md5 from Drive)
   or Drive size + `rclone md5sum` against the manifest. Size alone is not verification.
   Then, and only then, delete the source — and log it.
4. **Log every item** in `~/.claude/logs/drive-archive.log` (one line: date, source, destination,
   files, bytes, sha256, drive md5, status) and in the machine's own housekeeping ledger.
5. **Limits to respect (Google's own numbers, read 2026-09-06):** 750 GB upload per user per
   24 h; 5 TB per file; 500,000 items per folder; account activity at least every 2 years.
   Big nights: check the day's total before starting a third 20 GB tar.
6. **Credentials:** the rclone token lives only in `rclone.conf` on the machine that uploads
   (Windows: `%APPDATA%\rclone\rclone.conf`); scope **`drive.file`** (sees only what rclone
   created; set `root_folder_id` to the approved folder) — a full-scope token is a CEO decision,
   never a default. Use the org's own Google client_id (rclone's shared one is being throttled
   in 2026); never copy the token to the Mac, a repo, a chat, or a pod.
7. **Never `rclone sync`/`delete`/`purge` against Drive.** `copy`, `copyto`, `rcat`, `moveto`
   (server-side, for filing) and `check` are the whole vocabulary. A sync would mirror a
   machine's deletions into the archive.
8. **Bandwidth manners:** `--transfers 1 --drive-chunk-size 64M` from the game box while the bot
   plays (the CPU/disk contention halved the recorder's frame rate on 2026-09-06); bigger
   parallelism only on an idle machine.
9. **Same-turn bookkeeping:** after the first upload into a new folder, update the tree and the
   ID table here and paste the subtree back to the CEO (hard rule 6).

Reference implementation: cookierun-bot `docs/DATA-STEWARD.md` (lifecycle), `tools/archive_take.py`,
`tools/stream_take_to_drive.py`, gate rows `winbox play_rec → BACKUP/CookieRun Backup/play_rec`.

## The bridge — how moves/renames/deletes actually happen

Google's own Drive MCP connector (`mcp__claude_ai_Google_Drive__*`) can only
search/read/create — it has no move, rename, or delete. All of those go
through a small Apps Script web app instead (`scripts/gdrive-bridge/`),
called via a CLI:

```bash
python3 scripts/gdrive-bridge/gdrive_move.py move <fileId> <newParentId>
python3 scripts/gdrive-bridge/gdrive_move.py rename <fileId> <newName>
python3 scripts/gdrive-bridge/gdrive_move.py trash <fileId>
python3 scripts/gdrive-bridge/gdrive_move.py untrash <fileId>
python3 scripts/gdrive-bridge/gdrive_move.py create_folder <name> [parentId]

# added 2026-08-12 — read side + logs.txt support
python3 scripts/gdrive-bridge/gdrive_move.py list <folderId>
python3 scripts/gdrive-bridge/gdrive_move.py create_file <name> <parentId> [content]
python3 scripts/gdrive-bridge/gdrive_move.py create_doc <name> <parentId>
python3 scripts/gdrive-bridge/gdrive_move.py read_file <fileId>
python3 scripts/gdrive-bridge/gdrive_move.py append_log <fileId> <line> [line ...]
```

⚠️ **Any change to `Code.gs` needs a redeploy before it exists server-side** —
a deployment serves the version that was published, not the file on disk, so a
saved-but-undeployed action returns `unknown_action`. Redeploy via
**Deploy → Manage deployments → ✏️ → Version: New version**. Never
**New deployment**: that mints a fresh URL while `~/.config/mooniex/gdrive-bridge.json`
still points at the old one, so the bridge goes dead while the UI reports success.
Confirm afterwards that the deployment id still starts with the same 8 characters.

⚠️ **Deploying does not grant new OAuth scopes.** Apps Script asks for scopes at
*run* time, not at deploy time, so a redeploy raises no consent screen and any
call needing a new scope fails at runtime instead. Learned 2026-08-12: a
`create_doc` built on `DocumentApp` deployed cleanly and then failed with
"ไม่ได้รับอนุญาตให้เรียกใช้ DocumentApp.create". **Prefer building on services the
bridge already holds** (`Drive`, `DriveApp`) over adding a scope — the fix was to
create the doc as a Drive file with the Docs mimeType.

- Config (URL + secret token) lives at `~/.config/mooniex/gdrive-bridge.json`
  — outside git, never commit it.
- All operations are metadata-only (Drive API v3 `files.update` /
  `files.create`) — nothing is ever re-uploaded or copied, so nothing can be
  dropped mid-move.
- `create_folder` and `move`/`rename`/`trash` occasionally 404 on the very
  first call after Apps Script goes cold — retry once before treating it as
  a real failure.
- Occasionally a single call hangs instead of erroring (seen 2026-08-04, one
  `rename` never returned). The client now has a 25s socket timeout so it
  fails loudly instead of hanging forever — if a call times out, just retry
  it individually. Don't chain many calls in one `&&`-joined Bash command;
  run them one at a time so a single hang doesn't block the rest.
- Source: `scripts/gdrive-bridge/Code.gs` (Apps Script) — read it if you need
  to add a new bridge action.

Use `mcp__claude_ai_Google_Drive__search_files` / `get_file_metadata` for all
read/lookup work (verifying a folder is empty, finding IDs, browsing) — only
reach for the bridge when something needs to actually change.

## YT: ILAG — its own rules (CEO 2026-08-12)

`ALL DRAFT/YT: ILAG` is a YouTube channel of **AI-generated short films**, made
under the ILAG Studio brand (brand identity lives in `mooniex-claudesign`,
"The Stamp", task-1ceb4c08). "ILAG" is not an acronym — it is just the name.

Everything in this section applies to **this branch only**. The CEO's reason,
in his words: *"เพราะโปรเจคนี้ค่อนข้างละเอียดอ่อน"*. Do not generalise these
rules to `MYPASAKON`, `BLACK LIQUIDITY`, `YT: TRADER UNCUT` or any other
channel — they keep the ordinary per-clip production-stage layout.

### Layout

```
YT: ILAG/
└── <film title>/          ← one PROJECT = one film/episode
    ├── logs.txt           ← mandatory, one per project, never shared
    ├── All Scene/         ← AI-generated footage, one sub-folder per scene
    │   ├── S1/ S2/ S3/ …
    │   └── S3-A/ S3-B/ …  ← sub-shots, SIBLINGS of S3 (not inside it)
    ├── Element/           ← the @Element plates. EXACTLY ONE per project.
    │   └── <anything>/    ← sub-folders named by the director, not by us
    ├── Soundtrack/        ← everything audio
    │   └── <anything>/    ← SFX / Ambient / Audio / … director's call
    ├── Final Draft/       ← what the editor hands back, finished
    └── StoryBoard         ← Google Doc: whole film's storyboard, one doc
```

### Who names things here — not us (CEO 2026-08-12)

`Element/` holds the `@Element` plates that the **video generator, the script
writer and the director** reference by name. Naming them is *their* call, not
ours:

> "สิทธ์ในการตั้งชื่อขึ้นอยู่กับเขา ไม่ใช่เรา เรามีหน้าที่แค่บันทึกลงไป"

So:

- **Never rename a plate or an `Element` sub-folder to make it consistent.** A
  name that looks wrong to us may be the exact string a prompt resolves against
  (`@Motel-Front`). Record what is there; do not tidy it.
- **Every project has exactly one `Element/` folder.** Inside it, sub-folders may
  be called anything the director likes; the real plates live one level down and
  get reused from there.
- The same applies to `Soundtrack/`: it holds **everything audio** for the film,
  split into whatever sub-folders make it easy for the editor to grab — `SFX`,
  `Ambient`, `Audio`, any name that serves them.
- `Final Draft/` is where the editor returns the finished cut, matching the
  `Final Draft` stage folder the MYPASAKON project already uses.

The one place we *did* pick a spelling — `Element/Character` where the local
mirror says `Charactor` — was an explicit CEO decision on 2026-08-12, not a
tidy-up. Nothing since then licenses another one.

### Drive is the only home — the Desktop mirror is retired (CEO 2026-08-12, 22:20)

> *"เปลื่ยนใหม่ๆ ให้ทำขึ้น Gdrive ไปเลย Desktop Folder ไม่ต้องทำแล้ว เพราะเปือง
> พื้นที่ … หลังจากเอาลง Gdrive แล้ว ก็ลบ ไฟล์ในเครื่องนี้ได้เลย (ไฟล์ที่โหลดมา
> เท่านั้นห้ามลบมั่ว)"*

The permanent local mirror is gone. It held 513.8 MB on a machine whose swap was
already 90% full. **Local disk is now a staging area, not a copy.** The loop for
every batch of new renders:

1. Download from the generator to this machine — one clip or many, whichever is
   cheapest. A multi-file download arrives as a zip; unzip it locally, there is
   no password.
2. Upload to the right `S<n>` folder under
   `ALL DRAFT/YT: ILAG/<film>/All Scene/`.
3. Append the `logs.txt` line for each file, in the same turn as the upload.
4. **Verify the file is on Drive**, then delete the local copy to reclaim space.

**The delete is narrow, and it is the one dangerous step here.** Only files this
loop itself downloaded, only after Drive has confirmed them. Never a glob, never
a whole directory, never anything the loop did not put there. When in doubt,
leave it — disk is cheaper than a lost render.

**"Nothing in here gets deleted" still holds and is not weakened by this.** That
rule governs the Drive branch. Removing a redundant local staging copy is not
deleting from the branch; deleting anything *in Drive* remains forbidden.

`ilag_sync.py diff` is how you prove a file landed before removing it. A clean
run — `ONLY LOCAL (0)`, `size-mismatch: 0` — means every local file exists on
Drive at a matching size, so the local copies are safe to drop. Verified in that
state 2026-08-12 22:20: 61 local files / 513.8 MB, all present on Drive.

### The old local mirror and `ilag_sync.py`

Kept because the tooling and its traps still govern the staging loop above, and
because a mirror may still exist on disk from before this change. Reconcile with
`scripts/gdrive-bridge/ilag_sync.py` — never by eye:

```bash
python3 scripts/gdrive-bridge/ilag_sync.py diff          # read-only report
python3 scripts/gdrive-bridge/ilag_sync.py diff --log    # report + append to logs.txt
python3 scripts/gdrive-bridge/ilag_sync.py upload        # upload what is only-local
```

- **The mirror's folder names are misspelled and Drive's are not** (`All Screne`
  → `All Scene`, `SoudTrack` → `Soundtrack`, `Charactor` → `Character`). The
  tool maps them in `FOLDER_ALIASES`. **Fix the alias, never the CEO's folder** —
  renaming their local directories is not yours to do.
- Uploads go through the Drive REST API, not this bridge: the bridge creates
  text files only, and the mirror is ~500 MB of mp4/webp. Auth reuses the OAuth
  refresh token in `mooniex-claudeflow/.env` for this same Drive.
- **`--create-folders` is off by default** and stays that way until the CEO
  approves the folder names, per Rule 3.
- **A file on Drive but missing locally is an ALERT, not drift.** The CEO deletes
  nothing except true duplicates and broken generations, and keeps superseded
  takes as generation history — so a disappearance means something went wrong.
  The tool never deletes anything, anywhere, and the answer to an alert is never
  to delete the Drive copy.

The project folder is the **handoff package to the editor** — footage, sound,
and storyboard in one place, nothing else needed to start cutting.

### Scene folder naming
- `S<n>` — one scene as generated. **Never** a bare number (`1`), never
  `Scene 1`, never `Sence 1`.
- `S<n>-<A|B|C…>` — a sub-shot of that scene: either a long scene split up for
  storytelling, or a repair/re-generated take. It sits **beside** `S<n>`, at
  the same level, so the two sort next to each other and depth stays flat.
- The letter carries no meaning by itself. *Why* a sub-shot exists belongs in
  the `note` column of `logs.txt`, not in the folder name.

**Default: the split replaces the bare folder.** `S3-A`/`S3-B`/`S3-C` with no
`S3` beside them. That is what you get when the split was planned before the
scene was generated.

**But `S3` + `S3-A`/`-B`/`-C` side by side is not an error.** It is what
naturally happens when `S3` was made first and the sub-shots were added later.
The two shapes record two different histories, and neither is wrong.

So when you find a bare `S<n>` living alongside its own `S<n>-A`:

1. **Read `logs.txt` first.** If a `DECIDE` line already records the CEO's
   answer for that scene, honour it and say nothing. **Ask once, never twice** —
   re-asking a settled question is the failure mode this protocol exists to
   prevent.
2. If nothing is recorded, **ask the CEO: rename to the flat form, or keep both?**
   Do not decide it yourself either way.
3. Record the answer as a `DECIDE` line with the reason, so the next agent
   inherits it instead of re-deriving it.
4. The CEO may change their mind later. When they do, follow the new answer and
   append a new `DECIDE` line superseding the old one — never edit the old line.

### logs.txt — what it is for

Three parties work inside one project folder: **AI** (agents), **CEO**, and the
**editor** (a human outside this system). When something appears, moves, or
disappears, whoever is looking for it needs to know instantly *"is this new, is
it gone, where is the link"* — without asking anyone. That is the whole job of
this file. It is not an audit trail for blame; it is a signpost between three
people.

Concretely, the CEO's own example: *S3-A had 7 videos, the 8th arrived on
<date>, here is its link.* One line of the log must answer that.

**Location:** `<film title>/logs.txt`, at the project root. One per project.
A new project folder gets its `logs.txt` created in the same turn it is created
— the first line of the log is the creation of the project itself.

**Format:** plain text, append-only, 9 fields separated by ` | `
(space-pipe-space). Never TAB — under a non-UTF-8 locale, tmux silently
rewrites TABs and any tab-separated parse breaks without an error.

| # | field | values |
|---|---|---|
| 1 | `ts` | ISO-8601 with offset — `2026-08-12T20:40:11+07:00` |
| 2 | `actor` | `AI:<role>-<sid>` · `CEO` · `EDITOR` · `HUMAN` (unattributable) |
| 3 | `action` | State changes: `ADD` `DELETE` `MOVE` `RENAME` `RESTORE`. Plus `ALERT` (something anomalous found, nothing changed) and `DECIDE` (a CEO ruling recorded so it is never re-asked). No other verbs — invent one and the log stops being greppable. |
| 4 | `type` | `FILE` · `FOLDER` |
| 5 | `name` | the file/folder name at that moment |
| 6 | `link` | full Drive URL, clickable. The ID is recoverable from it |
| 7 | `where` | path under the project root, e.g. `All Scene/S3-A` |
| 8 | `n` | how many items that folder holds **after** this action (`-` if N/A) |
| 9 | `note` | reason, previous name, or `backfill <D-M-YYYY>` |

```
# logs.txt — Do Not Disturb (ILAG Studio)
# APPEND-ONLY. Never edit or delete an existing line.
# ts | actor | action | type | name | link | where | n | note
2026-08-11T18:03:10+07:00 | AI:browser_operator-task-cda4f469 | ADD | FILE | hf_20260811_180310_<uuid>.mp4 | https://drive.google.com/file/d/<id>/view | All Scene/S1 | 3 | Higgsfield Seedance 2.5 · take 2
2026-08-12T09:12:00+07:00 | EDITOR | DELETE | FILE | S3-A_take4.mp4 | https://drive.google.com/file/d/<id>/view | All Scene/S3-A | 7 | backfill 12-08-2026 · found missing during reconcile
2026-08-12T20:40:11+07:00 | CEO | ADD | FILE | S3-A_take8.mp4 | https://drive.google.com/file/d/<id>/view | All Scene/S3-A | 8 | 8th take of S3-A
```

### The rules bend — but never silently (CEO 2026-08-12)

Nothing in this section is absolute. A project runs the way the person running
it wants it to run, and these rules describe the normal case, not the only legal
one. What is **not** negotiable is that a departure leaves a trace:

- **Warn when you see something that contradicts a rule here.** Do not quietly
  normalise it, and do not quietly obey it either. Say what you found.
- **When a rule is knowingly broken, `logs.txt` must say so** — the note begins
  `EXCEPTION:` and gives the reason. Someone reading this branch in six months
  has to be able to tell a deliberate special case from an accident, and the log
  is the only thing that can tell them.
- **Ask once, then honour the record.** Before raising a question about this
  branch, grep `logs.txt` for a `DECIDE` line covering it. If the CEO has already
  ruled, follow the ruling silently. Re-asking a settled question is its own kind
  of failure.
- **A ruling can be revisited.** If the CEO changes their mind, follow the new
  answer and append a new `DECIDE` line that supersedes the old one. Never edit
  or delete the old line — append-only means the reversal is part of the record.

### Nothing in here gets deleted (CEO 2026-08-12)

The CEO does not delete files from this branch. The only exceptions are a true
duplicate, or a generation that is genuinely broken or malformed. **A superseded
take is not a candidate for deletion** — regenerating a shot never retires the
old one, because the discarded takes *are* the generation history and the
festival requires that history be producible on request.

Consequences that bind every agent:

- Never delete, trash, or overwrite anything in this branch. If something looks
  redundant, say so and let the CEO decide.
- A file that disappears is an anomaly worth raising, not drift to absorb.
- Do not "tidy up" a scene folder that has accumulated many takes. Many takes is
  the expected steady state, not a mess.

### Still undefined — ask, do not invent (as of 2026-08-12)

Written down so the next agent knows these are open questions rather than
oversights. Rule 7 applies: get the CEO's answer, do not guess one.

No open questions as of 2026-08-12. Answered that day, kept here so the
reasoning is not lost:

- **Naming inside `Element/` and `Soundtrack/`** — not ours to define. See "Who
  names things here" above.
- **Where the finished cut lives** — `Final Draft/`, same as MYPASAKON.
- **Whether the scene prompts belong in Drive** — **no.** The editor receives
  footage that is already generated and generates nothing themselves, so the
  prompts are not part of their handoff package. They stay in the DEV worktree.
- **Whether a split scene keeps its bare `S<n>`** — the flat form is the default,
  but both shapes are legal because they record different histories. Ask once
  when you meet one, honour the `DECIDE` line thereafter. See *Scene folder
  naming*.

### Rules for any agent entering a YT: ILAG project folder

1. **Reconcile before you work.** `list` the project recursively, diff it
   against `logs.txt`, and append the missing history *first*: files present
   with no `ADD` line get one with `actor=EDITOR` (or `HUMAN` if you cannot
   tell) and `ts` from Drive's own created time; files in the log that are no
   longer in Drive get a `DELETE` line. Only then do the work you were sent to
   do. **Without this step the log starts lying the moment the editor drags a
   file in** — and the editor is a human outside this system who will never
   write a log line.
2. **Append immediately after each action succeeds, in the same turn.** Never
   batch the writing up for the end.
3. **Append-only.** Never edit or delete an existing line, even a wrong one.
   Correct it by appending a new line that supersedes it.
4. **If the append fails, stop.** Do not perform further Drive actions in this
   branch, and tell the CEO. A silent gap between Drive and the log is worse
   than an unfinished task.
5. **Close with a snapshot.** After a batch of work, append a block giving the
   current state. Appending a new snapshot never rewrites the old one, so
   append-only still holds — the last block in the file is the current truth,
   and the editor can read state off the bottom without reading history.

```
--- SNAPSHOT 2026-08-12T21:00+07:00 by AI:cto-<sid> ---
All Scene/S1    3 files
All Scene/S3-A  8 files
Soundtrack      0 files
StoryBoard      Doc · last edited 12-08-2026
--- END ---
```

## Folder map (living — update this table as the CEO defines more)

| Folder | Drive ID | Definition |
|---|---|---|
| `UNKNOWN` (root) | `1PIha6ByPigaVZQG89qZI9uCGW_Lw6ePA` | Fallback — file here when nothing else fits, or no folder exists yet. Max 1 sub-folder level (existing folders moved in wholesale are exempt — see Rule 5). Same-batch files from CEO can be filed without asking (Rule-1 exception) — see "UNKNOWN — filing protocol" above for the required `(name) (D-M-YYYY) (SID:xxxx)` tag. Contains (moved 2026-08-04): `claudeflow-media-archive`, `Media (สื่อ)`, `_Review (ไม่มีชื่อ)`. |
| `PROJECT` (root) | `1HVLTPS09R4WvhYyOPW_0HHrfWxWGF-hQ` | Important-but-not-video stuff per project: images, ideas, text/svg, government docs, company data, billing. **No video ever.** Max depth 4 (see Rule 8): project-name folder → category folder → optional bundle folder. One sub-folder per project, name = PROJECT NAME IN CAPS. |
| `PROJECT/MOONIEX` | `1NjXdmQM2Fx0Payd-rqL5hW7B1DDQJSXY` | Merged 2026-08-04 from the old root-level `MoonieX` folder (renamed in place, so its ~19 pre-existing sub-folders like Company & Legal, Broker Info & Data, Mooniex Finance, Proposals, etc. came along and are NOT yet individually re-defined). |
| `PROJECT/LUNGNOTE` | `113iaRrHorZ7Z8be2bAGbw59tIPbdoWjB` | Empty, awaiting first files. |
| `PROJECT/BRAND PROMPT` | `1A306O59m-X20MrqCsT_bZocAJ73RNAWT` | Empty, awaiting first files. |
| `PROJECT/WARPCLIP` | `1K4d6daPrWr_IGiqMYM8KIEE4X8lOMueF` | Empty, awaiting first files. |
| `PROJECT/LINKREED` | `1bHC9Zmtg3M_M8I-cwV8Dvmlxl17FVPjh` | Empty, awaiting first files. |
| `ALL DRAFT` (root) | `138qB8fRfv6Yo_2mBY2aObDcw1A1IRZ7q` | Video projects for every channel: AI-generated footage + b-roll. **Video lives here, never in `PROJECT`.** |
| `ALL DRAFT/ASSETS` | `1LJreOD8H3jUNzypxTnPwvq-pS7jkQNRd` | Shared assets usable across every channel. `ALL Assets` = general cross-project media, named for subject, image or video. `AI Assets` = AI-generated B-roll, VIDEO ONLY, sub-folders named `<CHANNEL> (ratio)` e.g. `BLACK LIQUIDITY (9:16)` (always both ratios per channel), files named `(scene/purpose) (D-M-YYYY) (AI model)` — see "AI Assets footage naming" above. `XM Assets` / `Exness Assets` = one sub-folder per real-world event (e.g. "XM GALA DINER 2024"), holding every photo/video shot during that event — both already matched this pattern before any fix was needed. |
| `ALL DRAFT/AI Assets/BLACK LIQUIDITY (9:16)` | `1vg8j7DY_hPE-X3yyTsp6ZrM8Gf72cfVG` | 21 real Kling V3 Pro clips renamed 2026-08-04 to `(scene) (date) (Kling V3 Pro)` pattern; `CHARACTER+THEME.png` left untouched (reference asset, not footage). |
| `ALL DRAFT/AI Assets/BLACK LIQUIDITY (16:9)` | `1Fad43yAblQvTrqAv07-16VugdStbMg0f` | Empty, created 2026-08-04, ready for future 16:9 footage. |
| `ALL DRAFT/AI Assets/MYPASAKON (9:16)` | `1TYQbXsEduH-gWMtfpwrMZq2r6x0PiU51` | Empty, awaiting first footage. |
| `ALL DRAFT/AI Assets/MYPASAKON (16:9)` | `1jpsoZi11u9WVZmmR0UxBQDCRKvATolRE` | Empty, created 2026-08-04, ready for future 16:9 footage. |
| `ALL DRAFT/BLACK LIQUIDITY` | `1nH2aZ6B8wuI9KoxMSS4hAk77cGq0Z1WY` | AI-Avatar short-video channel (TikTok @black_liquidity). Inside: **one sub-folder per clip** — docs, script, footage/b-roll, MANIFEST — the editor/script-writer's workspace for that clip. |
| `ALL DRAFT/MYPASAKON` | `10L6KFHfi-rOnTqh9F1PRJDTGYh603Ajg` | Main channel, CEO's own trading content, 80K+ followers. Same per-clip sub-folder structure as above. Renamed 2026-08-04 from `MY PASAKON` to match the CEO's no-space PROJECT-naming convention; 14 sub-folders/clip-titles with "myPasakon" casing also fixed to "MYPASAKON" the same day. |
| `ALL DRAFT/YT: MYPASAKON` | `1YnVptu-1dhwblIf3nojXu7Fnn24X353a` | Confirmed 2026-08-05 — same pattern as `BLACK LIQUIDITY` (below), just a different channel: YouTube-specific cut of MYPASAKON content. One sub-folder per clip, named for the clip's topic; inside each, production-stage sub-folders (AI Drafts/Final Draft, Audio, Rawcut, Thumbnail, Convert to .mp3). Renamed 2026-08-04 (was "YT: MY PASAKON"). |
| `ALL DRAFT/LUNGNOTE` | `1luO-_NW1eKmT7gfbQbKMDSrcpoG9iyKG` | Video project folder for LungNote (real Mooniex project name — was misspelled `LUNENOTE`, fixed 2026-08-04). Same name as `PROJECT/LUNGNOTE` on purpose: that one holds LungNote's non-video docs/images/billing, this one holds its video/footage — same split pattern as MOONIEX. Confirmed 2026-08-05 — same per-clip / production-stage pattern as `BLACK LIQUIDITY`; `DAY0/` already shows the Audio/Finals structure. |
| `ALL DRAFT/TRADE TO THE MOON` | `11YGzdDAtKyJVSS9VkKyX9on8_AmQ6A18` | Confirmed 2026-08-05 — same pattern as `BLACK LIQUIDITY`: one sub-folder per clip (TTTM-titled), production-stage sub-folders inside each. |
| `ALL DRAFT/YT: ILAG` | `1Pczc2QfRilB2DoGUVl7ZPPSwy-cbF6KN` | Defined 2026-08-12. YouTube channel of **AI-generated short films**, ILAG Studio brand. "ILAG" is not an acronym. Does NOT use the per-clip production-stage layout of the other channels — see the "YT: ILAG" section above for its own layout, `S<n>` scene naming, and the mandatory per-project `logs.txt`. |
| `YT: ILAG/Do Not Disturb` | `1GT_h_D6pMMpPuspoP7d_lXz9dzZQAt6w` | Defined 2026-08-12. One **project** = one film/episode; `Do Not Disturb` is the episode title (horror short for the Higgsfield Global Film Festival, deadline 2026-09-03). Holds everything needed to hand the film to an editor: `All Scene/`, `Element/`, `Soundtrack/`, the `StoryBoard` doc, and its own `logs.txt`. |
| `Do Not Disturb/All Scene` | `159zXCuZ3AJylUQdgQu5O6fvzclXa4KHa` | Defined 2026-08-12. AI-generated footage for this film, **one sub-folder per scene**. Renamed from the misspelled `All Sence` on 2026-08-12 (CEO approved). |
| `All Scene/S1` … `All Scene/S16` ⚠️ **INCOMPLETE — resolve ids fresh from Drive, never from this row** | S1 `1h6mB9hyrpWqEJ4OnneBY5R1BpGb3CMRr` · S2 `1ca-56TDlBa9UiKVIlwi3Wmk7X-spaFQ5` · S3 `1z-lE7kh1fQVwZGw9W6mSnST1ftPAt6RT` · S4 `11YIz4-mByH5qj0jAhl8st2bLoFTOkjZX` · S5 `1jHvoTrzrR0hywHVop0YubQuzUIUpbWWL` · S6 `1Bkm4vVYe4SAK1IjpWo7ciba8oWe5-TI6` · S7 `1xu3FF6CNOLUEjxALAJVo5lUf_lruL8so` · S8 `16W65_TjjmSDxJfQfO1kqh-RRJ9rH0h1e` · S9 `1C46LZWjVgimtPEBobFzuPHnifHNlxqMl` · S10 `1JhIOGMNiWERLAI8NNqYYD9Ktg8itulcZ` · S11 `1UUr-xoemX6WAFVF-ziIkU2Qwlvbamb8P` · S12 `1Vxsi_fJPHJjGeWvz32orHjYQTxP2St7I` · S13 `1ajLMdhz0UovCONTX45gxmP3hsekGj7dr` · S14 `1cFrb9DsVK5eCZoti3Kvd_cyaKR3oov7x` · S15 `1YaN2Wrr_3BScYxj5EIZr5bkvYbVxzsNz` · S16 `1dDHOHkxojnvfJYPg6DWt7aOFYd7trWqu` | One folder per generated scene; the film runs to **16 scenes**. Renamed from bare numbers `1`–`6` to `S1`–`S6` on 2026-08-12 so `S1-A`/`S1-B` sub-shots read unambiguously; S7–S16 created the same day. Counts at 2026-08-12: S1 3, S2 7, S3 5, S4 9, S5 5, S6 4, S7–S16 empty. Clips keep their raw Higgsfield names (`hf_<timestamp>_<uuid>.mp4`) — the `AI Assets` renaming convention does **not** apply here. **⚠️ NAMING CHANGED 2026-08-13 (CEO) — Drive and Higgsfield organise on different axes. Read before filing anything.**

| | Higgsfield | Google Drive |
|---|---|---|
| Split by | **shot** — `Sence 9-A`, `9-D-B`, `10-A` | **resolution** |
| A/B/C sub-folders | **yes, keep** | **none — flattened** |
| 720p vs 1080p | not separated | **separated** |

Drive uses exactly two folder families, both directly under `All Scene/`:

- **`S1` … `S15`** — older clips: Seedance 2.5, 720p, 20s
- **`S1-1080P` … `S15-1080P`** — newer: Seedance 2.0, 1080p, 15s, 21:9. **No `-Fix` suffix.**

A clip from `Sence 9-D-B` files into `S9`, or `S9-1080P` if it is a 1080p take.
**Never create a letter-suffixed folder in Drive again.** The reason for the
split: Higgsfield is the working view, where an operator must tell shots apart;
Drive is the editor's view, where he wants every take of a scene together and
needs to see at a glance which are the sharp ones.

**Note:** S9 was originally a duplicate `S7` created by a retry after a 404 that had already succeeded; it was repurposed rather than deleted, so its id looks out of sequence. **⚠️ THIS ROW IS INCOMPLETE AND WILL STAY THAT WAY.** It lists only the sixteen bare scene folders. It does NOT list the sibling sub-shot folders operators create as the film is split — `S9-A`, `S9-B`, `S9-C`, `S9-D-A`, `S9-D-B`, `S9-D-C`, `S10-A`, `S10-B`, `S10-C`, `S10-D` and whatever comes next. An operator reading this row will find a plausible `S9` or `S10` id and file sub-shot clips into the wrong folder — the exact shape of GH #58, but sourced from our own documentation instead of a bad argument. **Always resolve the target folder id fresh from Drive by name immediately before uploading, and confirm the resolved folder's real name matches where you intend to file.** A static table cannot track folders that agents create at runtime; treat these ids as a convenience for the sixteen that predate the split, never as authority. |
| `Do Not Disturb/Element` | `1PcujKkvTageWpoF-k8yY2jV7T_jLIX3i` | Created 2026-08-12. The `@Element` plates the generator, script writer and director reference by name. **Exactly one `Element` folder per project**; its sub-folders are named by the director, not by us — currently `Character` (`1R5GbLTEsUYFHWuageqoPON0rCP5LJhx1`), `Location` (`1zsNiTRunPKJloU8U8BLwzx-KEwk3qgTI`), `Prop` (`1rQ736mfLQUYsY8KUul29AVPjMWHb0spa`). Never rename a plate or a sub-folder here for consistency; a prompt may resolve against that exact string. |
| `Do Not Disturb/Final Draft` | `1LReMlLCM2KhSjjQ1PDWCBatt9Tba_pao` | Created 2026-08-12. Where the editor returns the finished cut, matching the `Final Draft` production-stage folder the MYPASAKON project already uses. Empty until the first cut comes back. |
| `Do Not Disturb/logs.txt` | `1GVmc1Cqg-97YMcCd303_1EbNFhaiIfiO` | The project log. Append-only, 9 pipe-separated fields — see the YT: ILAG section above for the contract and the reconcile-on-entry rule. |
| `Do Not Disturb/StoryBoard` | `18nykJSEtNPstN7-gB1VmGTjs8HAovFcivhBhAVgqdRw` | Google Doc. Short synopsis, the locked story facts, the festival constraints, and a link to the director's-notebook artifact where the volatile detail lives. |
| `Do Not Disturb/Soundtrack` | `1BcwtvPSSGN4kQwuYnerWYyPrLF3iAwjQ` | Defined 2026-08-12 — **everything audio** for this film — music, SFX, ambience, voice. Sub-folders are split by whatever kind makes it easy for the editor to grab (`SFX`, `Ambient`, `Audio`, …), named by the director rather than by us (CEO 2026-08-12). Empty as of that date. |
| `BACKUP` (root) | `1vU9GvMZdMXUV60_kTIkMR1aTwZcEHdlq` | NEW 2026-08-04. Important data that doesn't belong to / can't be categorized into any other folder, specifically related to backing up or redundantly storing data in 2-3 places. Can be temporary or permanent. |
| `BACKUP/FaceBook Backup` | `1cNHt6bg7-ggXf8ec6DChzouUrw3nUGig` | Meta "Download Your Information" auto-export bundles — rarely actually used. Moved here from Drive root 2026-08-04 (was a root-level folder). Meta's export flow has no destination-folder setting, so new `meta-*` exports will keep landing at Drive root — move each one into this folder manually/by AI when found. The old stray `meta-2026-Jun-18-22-41-35` was merged in here 2026-08-04. |
| `BACKUP/CookieRun Backup` | `1a5I-YVpeLelju2EY5Ey-jqDmRymfgQEl` | NEW 2026-09-06, CEO-approved in chat. Raw copies of the Cookie Run bot's data from the Windows box: the CEO's recorded takes, later the bot's own sessions and training sets. Uploaded from the box by rclone (remote `gdrive:`, scope drive.file) as one tar per item + sha256 manifest, verified with `rclone check`. Rules and lifecycle: `cookierun-bot/docs/DATA-STEWARD.md`; the move row lives in `playbooks/drive-archive-gate.md`. Created by rclone (not the bridge) so the drive.file token can still see it. |
| `BACKUP/CookieRun Backup/play_rec` | `1U_-pog8MCHrvpVbLLbwe_sMJKDRbZphH` | `<take>.tar` + `<take>.manifest.json` per recorded take. First item 2026-09-06: `1788525250.tar` (3,494,379,520 B, 14,000 frames). |
| `Desktop Cloud` (root) | `115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR` | Cross-device sync (Desktop/Windows/Drive). Expect duplicates and off-taxonomy files — that's normal. **AI never auto-files in or out — ONE exception, below.** Search/read is fine anytime; delete only on direct CEO command. **EXCEPTION (CEO 2026-08-24): SomPong's video grabber files here automatically.** The CEO was shown the "AI never auto-files here" rule, asked where a clip grabbed from a pasted link should land, and chose this folder over `ALL DRAFT/ASSETS/ALL Assets` and over a new folder — granting the carve-out explicitly. Scope: uploads only, by that one feature, of clips the CEO asked for by sending a link. Nothing else about this folder changes, and the no-delete rule is untouched. Target id lives in `DRIVE_SOMPONG_GRAB_FOLDER_ID`. **Do NOT reuse `DRIVE_VIDEO_PARENT_FOLDER_ID` for this** — that one is `ALL DRAFT/BLACK LIQUIDITY` and is load-bearing for `mooniex-claudeflow/src/video/videodrive.js` and `scripts/higgsfield/gen_loop.py`; repointing it breaks both. (`scripts/video_to_drive.py` was built on it and would have created a `desktop cloud` folder *inside* the BLACK LIQUIDITY channel, beside 53 real clip folders. Caught before it ever ran.) |
| `My Picture & Videos.` (root) | `1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy` | Personal photos/videos — memories, family, travel. Very personal. File by month (e.g. `2026-08/`) so timeline browsing works. |

### When the CEO defines a new folder or gives a new rule
1. Add/update its row in the table above (or the Hard Rules list) — this file
   is the only place it needs to go.
2. If it's a brand-new folder that doesn't exist in Drive yet, create it with
   `create_folder` (after asking), then record the returned ID here.
