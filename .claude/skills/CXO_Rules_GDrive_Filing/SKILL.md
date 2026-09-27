---
name: CXO_Rules_GDrive_Filing
kind: rules
owner: COO
aka: [gdrive-filing]
origin: mooniex-org
scope: >-
  Filing rules for the CEO's personal Drive (pass.gob1@gmail.com) — where things
  live and what AI may create, move, rename, or delete. Read before any Drive
  mutation, whether via the gdrive-bridge script or the Drive MCP tools. Rules
  only; not a file-transfer tool.
description: RULES — Filing rules for the CEO's Google Drive — read before ANY Drive action (create/upload/move/rename/delete, rclone, the gdrive-bridge, the Drive MCP). Trigger on /CXO_Rules_GDrive_Filing, "จัดระเบียบ Drive", "ย้ายไฟล์ไป Drive", "เก็บไฟล์นี้ไว้ที่ไหน", "ลบไฟล์ใน Drive", "save this to Drive", "file this", "backup to Drive", "สำรองไป Gdrive", "upload to Drive", "rclone", "Google Drive". A PreToolUse hook (scripts/hook-gdrive-skill-gate.py) blocks Drive-touching tool calls until this file has been read in the session.
created_by: human
audience: [cxo]
---

# Google Drive Filing — CEO's personal Drive (pass.gob1@gmail.com)

This is the **one place** the filing rules live (the folder map: `CXO_Knowledge_GDrive_FolderMap`). When the CEO
defines a new folder or changes a rule, edit THIS file — do not duplicate
rules into memory, CLAUDE.md, or anywhere else. Every session reads this same
file, so it stays consistent without re-explaining itself each time.

**Deleting from a machine, not from Drive? Read `ALL_Rules_DiskHygiene` first.** It owns the
Green list (what may go without asking), the back-up-first list, the never-touch
list and the per-machine files for the Mac, winbox and Contabo. It defers to THIS
file for anything that lands on Drive, and this file defers to it for what may be
removed locally.

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
   **This covers every new story or project, however fixed its pattern (CEO
   2026-09-27):** *"ถ้ามีเรื่องอื่น ต้องขออนุญาตในการสร้าง Folder + Path ที่คิดว่า
   เหมาะสม รออนุมัติสร้าง และเก็บ backup ไว้เสมอ"*. The ask names the folder AND its
   full Drive path (e.g. `ALL DRAFT/FB: ละครสั้นคุณธรรม/เรื่อง<ชื่อเรื่อง>/` with the
   sub-folders it will get), then waits for the yes. Ask when the story starts, not
   at clean-up: film 3 reached its Desktop clean-up with no Drive folder at all, so
   nothing had been backed up and the clean-up had to stop for the ask.
4. **Every folder must have a definition before you file into it.** Use the
   map (`CXO_Knowledge_GDrive_FolderMap`) to decide placement. If nothing fits, it goes to `UNKNOWN`.
5. **`UNKNOWN`** (Drive root) is the fallback — anything you can't confidently
   place, or that has no folder yet, goes there instead of guessing. Moving
   an *existing* folder (with its own pre-existing internal structure) into
   `UNKNOWN` is fine even though it then has sub-sub-folders — the 1-level
   cap governs what AI creates fresh inside `UNKNOWN`, not folders relocated
   there wholesale.
6. **Keep the tree and table in sync, same turn.** Any rename/move/create/
   delete you perform — or notice already happened outside this session —
   updates BOTH the ASCII tree and the ID table (`CXO_Knowledge_GDrive_FolderMap`) immediately. They must
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


## Where the rest of the Drive knowledge lives (split 2026-09-27)

- **The folder tree and the ID table** — `CXO_Knowledge_GDrive_FolderMap`. Every rule here that says "the map",
  "the tree" or "the ID table" means that skill; rule 6 keeps both in sync in the same turn.
- **Moving gigabytes in, and the bridge** (moves, renames, deletes; the Contabo path without it) —
  `CXO_Procedure_GDrive_BulkTransfer`.
- This file keeps the rules: the hard rules, the per-branch rules (UNKNOWN, PROJECT, AI Assets, YT: ILAG, the
  lakorn films), what stays on disk and what goes to Drive, and how a new folder or rule is recorded.

## YT: ILAG — its own rules (CEO 2026-08-12)

`ALL DRAFT/YT: ILAG` is a YouTube channel of **AI-generated short films**, made
under the ILAG Studio brand (brand identity lives in `mooniex-claudesign`,
"The Stamp", task-1ceb4c08). "ILAG" is not an acronym — it is just the name.

Everything in this section applies to **this branch only**. The CEO's reason,
in his words: *"เพราะโปรเจคนี้ค่อนข้างละเอียดอ่อน"*. Do not generalise these
rules to `MYPASAKON`, `BLACK LIQUIDITY`, `YT: TRADER UNCUT` or any other
channel — they keep the ordinary per-clip production-stage layout.

**One exception, added 2026-09-18: `ALL DRAFT/FB: ละครสั้นคุณธรรม` runs on these
same rules.** The CEO answered a request for a folder pattern by sending the
`YT: ILAG` link, and approved a tree built to match. So everything below —
`logs.txt`, `S<n>`, append-only, one `Element/`, nothing deleted, names belong
to the director — binds that channel too. Read "this branch" as both.

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

## Film work, «บัญชี», and recording a new folder or rule

### Film work: what stays on disk, what goes to Drive, what is simply deleted (CEO 2026-09-23)

**Standing rule — do not ask again.** The CEO's words when the Mac hit 3.7 GB free
of 228 GB: *"งานคุณทำแล้ว สำรองขึ้น Drive แล้วเคลียร์ด้วย อย่าให้สั่งบ่อยๆ
เขียนเป็นกฎไว้เลย"* — and, on what deserves backing up at all: *"เรามีพื้นที่
Google Drive เยอะ แต่ก็ไม่ควรสำรองไฟล์ 1.3 GB เยอะๆ เพียงแค่ปรับ 1-2 ฉาก
มันเปลือง คุณฉลาดพอที่จะตัดสินใจได้."*

So decide, do not ask:

| what | where it belongs |
|---|---|
| **Individual shot clips** (`shot-NN.mp4`) | **Drive, always.** Every take, good or bad — the branch keeps generation history. They are 2–6 MB each. |
| **One working folder of the current clips** | **Keep on disk in the task's Work folder** (`~/MoonieXHQ/Work/<task-id>/out/`, IRON §55) while it waits for the CEO's review; after review it goes up to Drive and the Work folder is closed. Never ~/Desktop (CEO 2026-09-23: "ให้เขาเก็บไว้ที่ Work แล้วส่งขึ้น Drive เมื่อตรวจเสร็จแล้ว หรือรอตรวจไว้ที่ Disk ได้"). |
| **Staging folders** the runner wrote into (`banchi-ACT<n>/`, `banchi-FIX/`, `banchi-TEST/`, comparison folders) | **Delete** once their clips are copied into the working folder AND verified on Drive. They are duplicates by construction. |
| **The assembled full cut** (~1.3 GB) | **Do NOT back up every version.** Re-assembling from the clips is a two-minute ffmpeg run, so an old cut is a cheap thing to recreate and an expensive thing to store. Upload a cut to `Final Draft/` only when it is one the CEO has signed off, or the last one of the day. |
| **A superseded cut** (`-v1` when `-v2` exists) | **Delete it as soon as the new one verifies.** Do not keep both. |

**The order never changes, and step 3 is not optional:**

1. Copy the new clips into the working folder.
2. Upload to `All Scene/ACT<n>/`; if a clip of that name already exists and the
   bytes differ, **trash the old one first** — Drive will otherwise keep two
   files with the same name and the next reader cannot tell which is current.
3. **Verify from Drive's own listing**: name present AND size equal, for every
   file. Not the upload call's return value.
4. Only then delete the staging copy.

**Verify before deleting means verify, every time.** On 2026-09-23 a check found
13 clips on Drive still holding the pre-fix version after a re-shoot — deleting
the local copies at that moment would have destroyed the only good take of nine
scenes. The check is two minutes; the loss is unrecoverable.

Reference implementation: `docs/ops/` and the `checkdrive`/`refresh` pattern used
that day — list the folder, compare `name → size` against the local file, upload
and trash only what differs, then re-list to prove the diff is empty.

**When a film is finished, clear it off every machine it was made on (CEO 2026-09-27).**
*"เก็บ backup ไว้เสมอ เมื่อจบงาน ให้เคลียร์ออกจากเครื่องที่ทำไว้ เพื่อประหยัด Disk ไว้ทำงานต่อไป"*.
"Finished" means posted. Do it in the same session as the post, without being asked:

1. Back up per the table above: clips to `All Scene/ACT<n>/`, plates to `Element/`,
   the published cut and cover to `Final Draft/`.
2. Verify by **md5** against the Drive listing, for every file. A name and size
   match is not enough.
3. Clear every working copy on **every** machine:
   - the Mac: `~/Desktop/<ep>-*` and `Work/<task>/out`;
   - winbox: `C:\mooniex\<ep>\clips|plates|cover`.
   Rough cuts and phone-size cuts are not backed up; they are made again from the clips.
   Keep the small text files (ledgers, sheets, runner scripts) until the CEO says otherwise.
4. On the Mac, move files to the Trash; never `rm`. On winbox, use the Recycle Bin.
   **The Trash frees no space until it is emptied, and emptying is the CEO's call.**
   Report the exact GB in the Trash (disk-hygiene field note 2026-09-25).

### «บัญชี» — the download → verify → delete loop (CEO 2026-09-19)

The CEO's words: *"ตรวจเสร็จแล้ว Upload ลง Drive แล้ว เชคแล้วว่า Upload แล้ว ให้ลบ
ที่โหลดมาในเครื่องนี้ด้วยนะ จะได้ไม่มีไฟล์ซ้ำๆ"* — and separately, that **test
takes and failed takes go up too**, not in the bin.

The order is fixed and the third step is not optional:

1. **Review it locally** — the CTO watches the clip and runs `tools/clip_review.py`.
2. **Upload to Drive**, into this story's `All Scene/ACT<n>/` (this branch splits by act, not by scene).
3. **Verify it is actually there** — list the folder and match the size. Drive's
   own listing, not the upload call's return value.
4. **Only then delete the local copy.** Not before, not on faith.
5. Append the `logs.txt` line in the same turn as the upload, per the branch rule.

**Failed and test takes are uploaded, never deleted.** This branch keeps
superseded takes as generation history, and a take that came out wrong is the
most useful thing to compare the fix against. A stuttered line, a wrong voice, a
drifted face — those go to Drive beside the good take, and `logs.txt`'s `note`
says what was wrong with it.

**The one local copy that stays: `Element/` plates.** `tools/build_shotsheet.py`
refuses to render a sheet whose handles have no local plate, so deleting them
breaks the build. All twenty together are ~12 MB; the delete-local rule exists
for 500 MB of renders, not for that. Drive is the archive, `~/Desktop/banchi-plates/`
is the working copy, and both are correct.

### When the CEO defines a new folder or gives a new rule
1. Add/update its row in the table above (or the Hard Rules list) — this file
   is the only place it needs to go.
2. If it's a brand-new folder that doesn't exist in Drive yet, create it with
   `create_folder` (after asking), then record the returned ID here.

## Field notes

- 2026-09-23 [WRONG] §Film work — the «บัญชี» row says the Element plates live on Drive AND on the Mac ("Drive is the archive, ~/Desktop/banchi-plates/ is the working copy"). The bridge lists Element/Character, /Location, /Prop as EMPTY, so the Mac folder was the only copy; it was deleted in a disk clear-up and tools/build_shotsheet.py then refused every sheet. Fix: after the re-harvest, upload the plates to Element/<kind>/ and verify by name+size before trusting the row again. · evidence: session cto-8c06958c, drive_get.find on 1mQ5Hx…/1DlzY…/1ZgN1F… → 0 files, task-f78ca70e · status: pending
- 2026-09-23 [SUPERSEDED] §Film work — "one working folder of the current clips … ~/Desktop/banchi-ALL/" · evidence: CEO ruling 2026-09-23 (the CEO had asked for Desktop only to view clips easily): clips stay in the task's Work/<task-id>/out/ until reviewed, then Drive · status: superseded
- 2026-09-23 [MISSING] §BACKUP — no row for closed-task Work/ archives; now `Agents-Work-<task>-<date>.tar` at the BACKUP root (first: task-95439aa8, id 1uPnam5a…, md5 verified by id) · evidence: CEO approval 2026-09-23 "ส่งไฟล์ขึ้น Drive ครั้งแรก (workdir.py close --archive) … จัดการได้เลย", gate row a043428 · status: promoted
- 2026-09-23 [MISSING] §BACKUP — no row for a box's own self-backup tarballs; now `Contabo-mooniex-agents-pre-20260807.tar` at the BACKUP root (id 1lj-dbuC5YiNz3Zf2qRRj9M1NVtGS6rui, md5 read back by id) · evidence: CEO 2026-09-23 "ถ้าไม่ชัวร์ สำรองก่อน", gate row in org:playbooks/drive-archive-gate.md · status: promoted
- 2026-09-24 [WRONG] FB drama branch — the earlier "plates never on Drive" note stayed `pending` and nothing acted on it: at the CEO's Mac clean-out `Element/Character|Location|Prop` of «จุดจบของเจ้าหนี้นอกระบบ» were still EMPTY while the only copy (`~/Desktop/banchi-plates`, 23 files) had already gone to the iCloud Trash — a Desktop delete on this Mac lands in `~/Library/Mobile Documents/.Trash/`, recoverable (copied back 23/23 by md5). The check that caught it: md5 of every local file against the md5 set of the whole Drive branch (not names, not sizes). A film is not "backed up" until Element/ holds its plates; run that md5 check before telling the CEO a Mac folder is safe to delete · evidence: CTO 8c06958c 2026-09-24 02:48, CEO then declined the upload ("โปรเจคเราจบแล้ว") · status: pending
- 2026-09-24 [MISSING] §Bulk transfer — the reference implementation names only Cookie Run tools; a generic one now exists: `scripts/stream_backup_to_drive.py` (freeze list → tar into `rclone rcat --drive-root-folder-id` → md5+size read back → manifest → delete only files whose size+mtime are unchanged; never follows junctions; refuses to overwrite an existing tar). 8 groups / 15.9 GB of winbox moved with it, 0 skipped files · evidence: session cto-46fb0d60, drive-archive.log 2026-09-23T20:39Z · status: pending
- 2026-09-24 [MISSING] §Hard rules — the root is not always forbidden: the CEO put two loose files there himself for a reinstall ("เอาไว้ที่ Root ได้เลย"), because a fresh Windows has only Edge and drive.google.com; a folder path is one more thing to get wrong on a bare machine · evidence: winbox-bootstrap.ps1 + winbox-reinstall-README-th.md at the Drive root, Agents-Core windows/winbox-reinstall/ · status: pending
- 2026-09-24 [MISSING] §Bulk transfer rule 3 — a stream whose SOURCE dies does not leave "nothing" on Drive: winbox went offline mid-`tar | ssh | rclone rcat`, the ssh drop gave rclone EOF, and rclone FINALIZED an 859 MB object of a 915 MB tar under the real name. It looked exactly like a backup. Only the size+md5 read-back exposed it. Always verify by md5 before trusting a name, and rename/trash any unverified object at once · evidence: session cto-46fb0d60, id 1vaZ9ywNjgjxs_VCUyEAGzLnx7-lL5C-E · status: pending
- 2026-09-24 [MISSING] §Bulk transfer — the Mac has no rclone token (rule 6), so Mac data has two routes: pipe into winbox's rclone over ssh (byte-exact, ~13 MB/s, token stays on winbox), or `tools/work_archive.py`'s resumable REST (needs a local spool file). Both plug into `stream_backup_to_drive.py --rclone`: `scripts/rclone_via_winbox.sh` / `scripts/drive_rest_rclone_shim.py` (run it with the venv python). The second is the fallback when winbox is down · evidence: session cto-46fb0d60 Mac-Reinstall-2026-09-24 tars · status: pending
- 2026-09-24 [COSTLY] §Bulk transfer — with ProtonVPN connected (default route utun9, RTT 343 ms to Google), every Mac REST upload got 502s and connection resets; a 201 MB tar never landed in 25 min and `tools/work_archive.py` gives up on the first non-308. Check `route -n get default` before a big upload, and resume (PUT `bytes */size`) instead of failing — `scripts/drive_rest_rclone_shim.py` does. VPN off: 52.8 GB went up at ~7 MB/s, 0 failures · evidence: session cto-46fb0d60, shim commit 8aa52611 · status: pending
- 2026-09-24 [COSTLY] §Bulk transfer — every rclone call on the rebuilt winbox costs 4–8 s (token refresh + the shared-client_id NOTICE), so seven calls chained in one ssh (`for %d … rclone mkdir` ×5 + 2 `lsjson`) blew a 90 s Bash timeout and the last mkdir never ran (`Machine-Blueprints` had to be created in a second call). Prevented by: one rclone call per ssh, or `run_in_background` for anything over three calls; `rclone mkdir` of the deepest path creates its parents, so a family with sub-folders is one call per leaf, not per level · evidence: bkhf5in6p 17:46–17:48, ids read back in commit 258b4217 · status: pending
- 2026-09-24 [MISSING] §Hard rules — rclone printed "This remote uses rclone's shared Google Drive client_id, which is being retired and will stop working during 2026" on every call after the re-consent. The winbox remote needs its own OAuth client_id (Google Cloud console, the CEO's account) before that cut-off or every Drive route in this skill stops at once; the switch is `rclone config reconnect gdrive:` after setting client_id/secret, and it is a HUMAN step (browser consent) · evidence: winbox rclone stderr 2026-09-24 17:46 · status: pending
- 2026-09-24 [MISSING] §Bulk transfer — a long series of small `rclone rcat` calls trips Drive's per-minute write quota on the shared client_id (`RATE_LIMIT_EXCEEDED`, `quota_unit 1/min/{project}`): 2 of 28 transcript day-tars failed mid-run from Contabo, both landed on a plain retry 10 min later. Design uploaders so every object is independent and idempotent (skip when the Drive object already has the right md5), never as one all-or-nothing batch; a failed object is a retry, not a loss · evidence: state/drive-leg-first-run-2026-09-24.log lines 19/38, ledger 13:44 vs 13:49 · status: pending
- 2026-09-24 [MISSING] §The bridge — Contabo has NO bridge config (`~/.config/mooniex/gdrive-bridge.json` absent), so `gdrive_move.py` dies there with FileNotFoundError. Create-folder / rename / upload / logs.txt append from Contabo go through Drive REST with the ClaudeFlow OAuth instead: `scripts/gdrive-bridge/ilag_rest.py` (create-if-absent, md5 checked by id, append = GET→PATCH→prefix check; set `ILAG_LOG_ACTOR`). A Google Doc can be made from markdown in one call: multipart upload, metadata mimeType `application/vnd.google-apps.document`, media `text/markdown` · evidence: 4b21f866, the TopView trailer project build (StoryBoard doc 1H9S-CG0…) · status: pending
- 2026-09-25 [WRONG] §Bulk transfer — `tools/work_archive.BACKUP_FOLDER_ID` is NOT the BACKUP root any more: 936fb0ad (2026-09-24) repointed it to `BACKUP/MoonieX HQ/Work-Archive` (`1xu8hXdU…`), and the REST shim that reused `work_archive._init_resumable_session` inherited that parent, so every upload would have been filed there silently (its own guard caught it by refusing the real root). Never borrow a module constant as the parent; pass it explicitly (`--drive-root-folder-id`), fixed in the shim at e6039963 · evidence: session cto-46fb0d60 · status: pending
- 2026-09-25 [COSTLY] §Bulk transfer — the REST shim spools the whole tar to local disk (needs part size + ~3 GB free); on a near-full Mac the last part, one 7.0 GB .mov, waited ~70 min for space. A part that is a single file needs no tar: upload it raw from its path with the shim's `upload()` (resumable, zero spool) and verify size + md5 by id (`Mac-Reinstall-2026-09-25-iCloudLeftovers-p09-f786.mov`) · evidence: session cto-46fb0d60 run.out 21:33→22:40 · prevented by: a runner that uploads single-file parts raw · status: pending
- 2026-09-26 [COSTLY] §Bulk transfer — a 562 MB film upload through `scripts/rclone_via_winbox.sh` 403'd `rateLimitExceeded` 12 times over an hour (winbox `gdrive:` is back on rclone's shared client_id — see the 2026-09-24 note), and the retry loop ran `rcat` with `capture_output=True`, so its log only said "not yet" and never the 403. The Mac's own Drive REST client (`tools/work_archive` `_access_token` + `_upload_chunks`, raw from the path, `X-Upload-Content-Type: video/mp4`, parent passed explicitly) landed it first try with md5 verified. Until winbox gets its own client_id, send single large files that way, and never let a retry loop swallow the tool's stderr · evidence: Work/task-c2723478/out/drive-final-retry.log (GAVE UP) vs drive-final-rest.log (UPLOADED 17Gl1LqfUHiEK0cmVK05luhJlSjnS7vXv) · prevented by: a `--mime` flag on `scripts/drive_rest_rclone_shim.py` (it hard-codes application/x-tar) · promoted 2026-09-26 to Hard rule 6 "State 2026-09-26": the artefact `rclone config redacted gdrive:` shows `client_id = ` empty, which proves the 09-09 state line false; the shim now takes the MIME type from the file name (video/mp4, x-tar kept for tars, checked with a fake HTTP layer, no live upload) · status: promoted
- 2026-09-27 [MISSING] §Hard rules 3 + §Film work — film 3 reached its Desktop clean-up with no Drive folder, so nothing was backed up; the CEO ruled: ask for the folder + full path when a story starts, always keep a backup, and clear every machine it was made on when the film is finished (winbox held a second 491 MB copy). Rule body changed on the CEO's ruling. The Mac Drive REST upload (ilag_sync helpers, 16 MB resumable chunks) moved 1.0 GB and 115 files in ~12 min with 0 retries · evidence: task-c816fbc0, Drive 15cGRMSGUdpn-K_PAw0823lQ-eTpLB8Ur, 369a6c92 · status: promoted
