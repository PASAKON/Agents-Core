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

**Deleting from a machine, not from Drive? Read `disk-hygiene` first.** It owns the
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
├── winbox-bootstrap.ps1          TWO LOOSE FILES AT THE ROOT ON PURPOSE (CEO 2026-09-24:
├── winbox-reinstall-README-th.md "เอา Script เก็บไว้ใน Google Drive … เอาไว้ที่ Root ได้เลย"): the
│                                 first thing the freshly reset winbox downloads (OpenSSH + keys +
│                                 Tailscale bootstrap, and the Thai reinstall sheet). ids
│                                 1ddHBrrk1ptF_imJLAaKS0xAEVORzFa-O / 1MCO2BV-goQgEHsVQXpTjgTvtfkBgLBkY.
│                                 Source of truth: Agents-Core windows/winbox-reinstall/. Copies also
│                                 sit in BACKUP/Winbox Reinstall 2026-09-24/. Remove from the root
│                                 only when the CEO says the reinstall is over.
├── (--help/)                     an empty rclone-typo folder seen 2026-09-24 09:47 UTC; the CEO said
│                                 "ลบได้เลย" the same day → re-verified empty, `rclone rmdir` (Drive trash).
├── Archive/                      DEFINED BY THE CEO 2026-09-24: "สำรองเหมือนกัน แต่เป็นสำรองแบบยกเลิกไปแล้ว
│   ├── Agents-output/            … ใช้แต่ BACKUP อย่างเดียวก็พอ" — an earlier, ABANDONED backup scheme.
│   └── Backups/                  Nothing new is filed here; `BACKUP/` is the only backup root. Contents
│                                 untouched until the CEO says what to do with them (not asked yet). ids
│                                 Archive 1uQo4YCdxVlYLFjD-6LQIBcNAVMoyXdC_ · Agents-output
│                                 1uILo8ZPrsEwi2wonrsgdZsg0ugYj4siG · Backups 1KD8ZQ-fXg7pjklTgOetidJFhSpLjGZGz.
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
│   │   │                     id 14uc0nxq0ZmaS0GZuCq7hZOl1ROeUYRbV (added 2026-09-18).
│   │   │                     2026-09-18: +65 Seedance 2.0 B-roll into BL (9:16), each
│   │   │                     named (purpose) (date) (Seedance 2.0); catalogue + drive ids in
│   │   │                     Agents/prototypes/bl-broll-catalog/ — workers grep that, not this tree
│   │   │   ├── BLACK LIQUIDITY (9:16)/   ← naming order CONFIRMED as
│   │   │   └── BLACK LIQUIDITY (16:9)/     "CHANNEL (ratio)", not "ratio
│   │   │                                   CHANNEL" (reverted 2026-08-04).
│   │   │                                   Every clip: (scene) (date)
│   │   │                                   (model) — 21 BLACK LIQUIDITY
│   │   │                                   clips renamed 2026-08-04.
│   │   │   MYPASAKON (9:16)/, MYPASAKON (16:9)/ — same pattern, currently
│   │   │   empty, created 2026-08-04 ready for future footage
│   │   ├── Audio/                NEW 2026-09-18 (CEO). เสียงที่ใช้ร่วมกันข้ามช่อง —
│   │   │   │                     CEO: "Audio อาจจะมี /SFX หรืออื่นๆ ได้อีก เป็น
│   │   │   │                     Sound Effect ที่ใช้รวมกัน"
│   │   │   ├── Voice Library/    คลังตัวอย่างเสียง TTS ไว้ฟังเลือกผู้บรรยาย ก่อนพากย์จริง
│   │   │   └── SFX/              นิยามไว้แล้วตามที่ CEO บอก ยังไม่ได้สร้าง —
│   │   │                         สร้างเมื่อมีไฟล์แรกจริง (กฎข้อ 3)
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
│       │                          PROJECT NAMING (CEO 2026-09-24): `<film title> (<competition> <year>)`,
│       │                          so the three projects read alike. DND and Sorry, Sir were renamed
│       │                          that day (ids unchanged, a RENAME line in each logs.txt).
│       │                          (`The Valder Collection No.7/`, an unmapped old project with 3 hf_ mp4s from
│       │                          19-20 Aug, TRASHED 2026-09-24 on the CEO's word: "โปรเจคเก่า ลบออกได้เลย")
│       └── Do Not Disturb (Higgsfield Global Film Festival 2026)/   one PROJECT = one film/episode
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
│           ├── Meta (Higgsfield)/ NEW 2026-09-12 — 21:9 ONLY (this film is
│           │                      1470×630). Server-side copy from Sorry, Sir
│           └── StoryBoard (Doc)   synopsis + link to the director's notebook
│       └── Sorry, Sir (The Valder Collection) (Higgsfield Global Film Festival 2026)/   the second ILAG film, in
│           │                      production Sept 2026, festival deadline 9 Sep
│           ├── logs.txt           append-only, same 9-field contract
│           ├── All Scene/         → Fix-1/ every take up to 2026-09-08 morning, named
│           │                      for its scene · Fix-2/ NEW 2026-09-08 (CEO) — the
│           │                      SECOND EDIT. In the CEO's words: "ฉากที่สร้างในวันนี้
│           │                      จนถึงจบโปรเจคใส่ Fix-2 … เป็นการ Edit ครั้งที่ 2" — every
│           │                      clip generated from 2026-09-08 to the end of the
│           │                      project files HERE. Fix-1 takes nothing new. Seeded
│           │                      by moving the five 2026-09-08 clips out of Fix-1.
│           ├── Element/           the @Element plates
│           ├── Plates (raw source)/  raw hf_ generations behind those plates
│           ├── Previz/            NEW 2026-09-08 on the CEO's instruction — grey
│           │                      previz clips, each named for the SCENE that used
│           │                      it (S2C-Previz.MP4). If the scene is unknown the
│           │                      CEO's named fallback is Previz/Unknow/ — not
│           │                      created yet, nothing has needed it
│           ├── Soundtrack/        music stems, 9 unique files
│           ├── Poster/            NEW 2026-09-12 (CEO approved in chat). Key art for
│           │                      the film and the YouTube thumbnail
│           ├── Meta (Higgsfield)/ NEW 2026-09-12 (CEO: "ใส่ Upload Drive ไว้เลย
│           │                      ตั้ง folder ไว้ด้วย"). Festival-mandated Higgsfield
│           │                      branding: watermark PNG + packshot ProRes.
│           │                      16:9 ONLY — this film is 1280×720. The 21:9 pair
│           │                      lives under Do Not Disturb, which is 1470×630
│           └── Final Draft/       the editor's cut comes back here
│       └── รอตั้งชื่อ (Topview Wan3 Challenge 2026)/   NEW 2026-09-24 (CEO: "Create New Project
│           │                      Folder ... ไว้ข้างๆ Do not disturb + Sorry sir ... สร้างเลียนแบบ").
│           │                      The alien-ocean trailer for the TopView Wan3 Challenge. Title not
│           │                      chosen yet: rename in place when it is (id stays). Layout = DND's.
│           ├── logs.txt           append-only, 9-field contract
│           ├── All Scene/         Wan3 clips, S<n> per storyboard shot
│           ├── Element/           → Character/ (char_*, villagers, creature), Location/ (loc_*,
│           │                      colour script, crt_* stills), Prop/ — the ChatGPT reference images
│           ├── Previz/            NEW 2026-09-25, same as Sorry, Sir's: the MiniMax H3 360p previz takes,
│           │                      named M<n>-H3-take<N>.mp4 (prompts: Agents-Core docs/prompts/ilag-topview/)
│           ├── Soundtrack/
│           ├── Final Draft/
│           └── StoryBoard (Doc)   snapshot of Agents-Core docs/promo/topview-trailer/ (the living copy)
├── FB: ละครสั้นคุณธรรม/          NEW 2026-09-18 (CEO approved in chat, "ตามนั้น
│   │                          Approve"). Facebook page «ละครสั้นคุณธรรม by ILAG
│   │                          Studio» (id 61594116376333). Thai moral short
│   │                          dramas, ONE COMPLETE STORY PER EPISODE (ฟ้ามีตา
│   │                          format) — not a serial. Same brand as YT: ILAG,
│   │                          different platform and different show, so it is a
│   │                          sibling channel, not a folder inside it.
│   │                          ⚠ RUNS ON THE YT: ILAG BRANCH RULES — read that
│   │                          section: mandatory per-project logs.txt, S<n>
│   │                          scene naming, append-only, nothing ever deleted,
│   │                          and plate names belong to the director not to us.
│   └── เรื่องจุดจบของเจ้าหนี้นอกระบบ/   ONE STORY = ONE FOLDER, named `เรื่อง<ชื่อเรื่อง>` —
│       │                      always the word เรื่อง first (CEO 2026-09-19, e.g.
│       │                      the CEO named this one 2026-09-19). Was `EP1 บัญชี`,
│       │                      then `เรื่องบัญชี`, same day; the id never changed.
│       │                      Repo files keep the working name `banchi`.
│       ├── logs.txt           append-only, 9-field contract (YT: ILAG rules)
│       ├── All Scene/         split by ACT, one sub-folder per act: `ACT1/`,
│       │   └── ACT1/          `ACT2/` … — every take of that act, good, failed
│       │                      and test alike, named `shot-NN.mp4`. ACT1 approved
│       │                      2026-09-19; the next acts follow the same pattern
│       │                      without asking again.
│       ├── Element/           → Character/, Location/, Prop/
│       ├── Soundtrack/
│       ├── Final Draft/       the assembled cuts (`<เรื่อง>-ตอนที่N-cutK-<date>.mp4`)
│       └── StoryBoard (Doc)
├── BACKUP/                       NEW 2026-08-04. Important data that doesn't
│   │                             fit any other folder / can't be categorized,
│   │                             or redundant copies the CEO wants kept in
│   │                             2-3 places — temporary or permanent, either
│   │                             is fine.
│   ├── MoonieX HQ/               NEW 2026-09-24 (CEO: "ใส่ไว้ใน BACKUP/MoonieX HQ/{สิ่งที่จะเก็บ}
│   │   │                         ได้เลย เพิ่มนิยามให้ด้วย"). The org's Machine Contract store
│   │   │                         (ADR 0031, IRON §58): everything a machine keeps that is not
│   │   │                         in git, one sub-folder per KIND of thing, each defined here so
│   │   │                         an agent cleaning up or searching knows where it lives. Every
│   │   │                         item = tar (or .jsonl.gz) + manifest, md5 verified before the
│   │   │                         local copy goes. CREATED 2026-09-24 17:47 by rclone on winbox
│   │   │                         (right after the CEO's re-consent); parent id
│   │   │                         1NqyT7TjUHVBuOCo0bw3dRy8niXLcLawK, children in the ID table.
│   │   │                         Registry rows point here: Agents-Core config/machine-contract.yaml.
│   │   │                         Contabo reaches it through scripts/rclone_via_winbox.sh (token stays
│   │   │                         on winbox, rule 6); the Mac through the same relay or its bridge.
│   │   ├── Claude-Transcripts/<machine>/<project-slug>/   every Claude Code session .jsonl,
│   │   │                         all machines, archived after 7 days on the box, KEPT FOREVER
│   │   │                         (CEO 2026-09-24). `contabo/` id 1d7mVpwFy4bY56u2t30f9nUfmhbqa11Xt
│   │   │                         (29 day-tars, 370 MB, 2026-09-24); `mac/` id 1FqUUq9CdwL7AvMnPzlui3kgUtKTMU4ZP
│   │   │                         = the old `BACKUP/Claude-Transcripts` folder moved in whole (Mac's
│   │   │                         `prune_transcripts.py` layout `<slug>/<uuid>.tar.gz`, 112 files).
│   │   │                         Packing: one `<YYYY-MM-DD>.tar.gz` per slug per
│   │   │                         day (sessions inside as `<uuid>.jsonl` + their sub-agent dirs) +
│   │   │                         `<YYYY-MM-DD>.manifest.json` listing every uuid — Contabo alone has
│   │   │                         ~5,900 session files, most a few KB, so per-file objects would be
│   │   │                         thousands of Drive calls. Restore one session by uuid:
│   │   │                         `tools/drive_leg.py restore-transcript <uuid>` (reads the manifests)
│   │   ├── Claude-Uploads/<machine>/<date>.tar   files people attached in chat (~/.claude/uploads)
│   │   ├── Work-Archive/         Agents-Work-<task-id>-<date>.tar + manifest from
│   │   │                         `workdir.py close --archive` — NEW tars go here; the ones at the
│   │   │                         BACKUP root (2026-09-23) move here server-side once
│   │   ├── Docker-Volumes/<machine>/<volume>/<date>.tar|.sql.gz   sole-copy Docker data:
│   │   │                         contabo n8n_data (n8n workflows+creds), org-pgdata (pg_dump), weekly
│   │   ├── Machine-Blueprints/<machine>/<date>/   copy of each capture (installed software,
│   │   │                         scheduled jobs, unit files, settings, public keys; NO secrets);
│   │   │                         the primary copy is git Agents-Core state/<machine>-blueprint-<date>/
│   │   │                         Secrets are never on Drive: another machine's HQ Archive/ at 0600.
│   │   └── State-DB/<machine>/tasks-<date>.sqlite.gz   NEW 2026-09-24 (CEO "อนุมัติ"). Each box's org
│   │                             task ledger (`Agents/Core/state/tasks.db`, SQLite, gitignored — the
│   │                             Postgres hub is still empty), taken with sqlite's online backup API
│   │                             (never cp of a live DB), gzip + manifest, weekly by
│   │                             `tools/drive_leg.py state-db`. id 15xudjmiHK6MfSCxM48cqwjPOKOWgoNzO.
│   ├── (Claude-Transcripts/)     MOVED 2026-09-24 on the CEO's "Yes go": the pre-existing Mac archive
│   │                             folder (112 `<uuid>.tar.gz`, 1.27 GiB, 40 Mac project-slug folders) is now
│   │                             `MoonieX HQ/Claude-Transcripts/mac/` — one server-side DirMove, same id
│   │                             1FqUUq9CdwL7AvMnPzlui3kgUtKTMU4ZP, every file id unchanged.
│   ├── FaceBook Backup/          Meta "Download Your Information" auto-export
│       ├── meta-2025-Jun.../     bundles — rarely actually used. Moved here
│       ├── ... (10 total)        from root 2026-08-04. New meta-* exports
│       └── meta-2026-Jun-18.../  land at Drive ROOT (Meta gives no destination
│                                 control) — move each one in here manually.
│   ├── CookieRun Backup/         NEW 2026-09-06 (CEO-approved). Raw copies of the
│       │                     Cookie Run bot's data from the Windows box (winbox),
│       │                     uploaded by rclone as one tar per take + a sha256
│       │                     manifest — never loose frames. Steward brief:
│       │                     cookierun-bot/docs/DATA-STEWARD.md; gate row in
│       │                     playbooks/drive-archive-gate.md.
│       ├── play_rec/         <take>.tar + <take>.manifest.json (CEO's recorded takes)
│       ├── bot_sessions/     NEW 2026-09-08 (CEO-approved). The bot's own play: per
│       │                     session one tar of the rounds NOT in the top 20% by coins
│       │                     + manifest; rounds.jsonl/hits never leave the box
│       ├── jumpsweeps/       NEW 2026-09-08 (CEO-approved). Jump-physics sweeps: per
│       │                     sweep one tar of the bursts without a human label + manifest
│       ├── hits/             NEW 2026-09-24 (CEO "อนุมัติ"). Hit frames (`modelplay/session-*/run-*/hit_NN/`)
│       │                     beyond the 500 MB/day that stays on the box: one `hits-<YYYY-MM-DD>.tar`
│       │                     per day + manifest, streamed by the bot's archive runner (queue item 5,
│       │                     opened by the gate file `archive/hits_archive_enabled`, written 2026-09-24),
│       │                     deleted locally only after md5 verify. id 1e-TGFYiEecMKIu34dOhJeZMw1PREd2__
│       └── from_pod-mac-only-2026-09-13.tar (+ .manifest.json)   NEW 2026-09-13
│                             (CEO-approved). The 27 trained models that existed ONLY on
│                             the Mac, backed up when cookierun-bot was split into
│                             code-on-GitHub / data-on-winbox. Filed at this folder's
│                             root — a models/ sub-folder is PROPOSED, not approved
│   ├── iPhone14Pro_Backup/       seen 2026-09-10 (created 2026-08-05) — UNDEFINED,
│   │                             ask the CEO what it is for (Rule 7); do not file into it
│   ├── Agents-worktrees-2026-09-10.tar (+ .manifest.json)   NEW 2026-09-10, CEO-approved
│   │                             in chat ("สำรองถ้าไม่มั่นใจ ใน Skill google drive filling").
│   │                             Restore packages of the 38 Agents task worktrees removed
│   │                             in the Mac disk reclaim: per worktree a git bundle of the
│   │                             unmerged commits + dirty patch + untracked files + TASK.md.
│   │                             Filed at the BACKUP root on purpose — a `BACKUP/Agents
│   │                             Backup/` sub-folder is PROPOSED, not yet approved; move it
│   │                             there (server-side) once the CEO OKs the name. Gate row in
│   │                             org:playbooks/drive-archive-gate.md.
│   ├── Agents-Work-<task-id>-<YYYY-MM-DD>.tar (+ .manifest.json)   NEW 2026-09-23, CEO-approved in
│   │                             chat ("ส่งไฟล์ขึ้น Drive ครั้งแรก (workdir.py close --archive) … จัดการได้เลย").
│   │                             A closed task's unfiled Work/ files (IRON §55): `tools/workdir.py close
│   │                             <task> --archive`, chunked REST upload, md5 checked by id before the local
│   │                             delete. First: task-95439aa8 (HQ step 4b rollback manifests), id
│   │                             1uPnam5aoLWqZEgQH7kFOpBMmCkhU_STr, 51,200 B, md5 731889bf…. Gate row in
│   │                             org:playbooks/drive-archive-gate.md.
│   ├── Winbox Reinstall 2026-09-24/   NEW 2026-09-24, CEO-approved in chat ("อณุมัติ"). Everything NOT Cookie Run
│   │                             that winbox held before its Windows reinstall: code not on GitHub (bundles +
│   │                             patches), Downloads leftovers (Sorry Sir frame sequences, personal clips),
│   │                             C:\mooniex data folders, Desktop/Pictures. One tar per group + .manifest.json,
│   │                             md5 read back from Drive before any local delete. Id 12LWNL3LwEYcfqQWtvnV_KZeKegDt5Ic8.
│   │                             Filled 2026-09-24 (8 tars, 15.9 GB): downloads-sorrysir-frames, downloads-other,
│   │                             mooniex-data (these 3 deleted from the box), userfiles, mooniex-live, code-agents,
│   │                             code-agents-core, code-misc (backup only). Ids + what each holds: table row below.
│   ├── Mac-Reinstall-2026-09-24-{claude-home,MoonieXHQ-code,MoonieXHQ-data}.tar (+ .manifest.json)   NEW
│   │                             2026-09-24, CEO in chat ("สำรองให้เลย" — Claude sessions + MoonieXHQ before the Mac
│   │                             wipe). At the BACKUP root, same precedent as Agents-worktrees-*/Contabo-*; 5.55 GB,
│   │                             md5 read back by id, code tar restore-tested. Secrets are NOT here (Contabo, see row).
│   │                             The broken `…MoonieXHQ-code.PARTIAL-DO-NOT-USE-truncated-859MB.tar` was trashed on CEO OK.
│   │                             + `Mac-Reinstall-2026-09-24-Photos-p00-library…p19.tar` (20 tars, 52.76 GB): the Mac Photos
│   │                             library (iPhone camera roll 2021-01…2026-07-09; iCloud Photos was OFF on this Mac).
│   │                             + `…-final-delta-0837.tar` (changes 06:47→08:37) and `…-home-media.tar` (Movies/Music/Desktop/…, 1.18 GB).
│   ├── Contabo-mooniex-agents-pre-20260807.tar (+ .manifest.json)   NEW 2026-09-23, CEO-approved
│   │                             in chat ("ถ้าไม่ชัวร์ สำรองก่อน"). Two 2026-08-07 self-backups of
│   │                             Contabo's /opt/mooniex-agents (pre git swap/sync), deleted from the
│   │                             box after the md5 check by id. Gate row in org:playbooks/drive-archive-gate.md.
│   ├── ILAG-trailer-plates-2026-09-24.tar (+ .manifest.json)   NEW 2026-09-24, CEO in chat
│   │                             ("สำรองงานคุณลง Drive ก่อนนะ ฉันจะ Reinstall window ใหม่"). The 8 ChatGPT
│   │                             reference plates of the TopView trailer, whose only home was winbox. Parked
│   │                             here because the trailer has no YT: ILAG project folder yet; move them into
│   │                             its Element/ once the CEO approves that folder. DONE 2026-09-24: the 8 PNGs were
│   │                             COPIED (md5 checked by id) into `YT: ILAG/รอตั้งชื่อ (Topview Wan3 Challenge 2026)/
│   │                             Element/`; the tar stays here as the backup (nothing deleted).
│   └── PARKED-<repo>-ignored.tar.gz (+ .manifest.json)   NEW 2026-09-10, same approval.
│                                 Gitignored data of the two PARKED repos (moonx backtest
│                                 data/out_*, video-engine renders); the code itself lives
│                                 on GitHub PASAKON/PARKED-* (archived) — local clones deleted.
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
   **State since 2026-09-09:** winbox's `gdrive:` runs on OUR client — Google Cloud project
   `gen-lang-client-0516233449` ("Default Gemini Project", the CEO's), OAuth client
   `rclone-winbox` (Desktop app, id `997773077636-6sjdlu2lg1ggeh45l3dcd4g0mn7o2mdt…`), Drive
   API enabled; the token was re-issued at full `drive` scope by the CEO's own 2026-09-08
   decision. The shared client had 403'd `rateLimitExceeded` for hours (three dead uploads,
   2026-09-08/09); on our client a 2.7 GB tar landed in 3 min. **Re-consent procedure (token
   never leaves the box):** `cookierun-bot/tools/rclone_set_client.py <client json>` writes the
   id/secret; then from the Mac
   `printf 'y\ny\nn\n' | ssh -L 53682:127.0.0.1:53682 winbox "<rclone> config reconnect gdrive:"`
   (detached/nohup, no `--auth-no-open-browser` — that flag is not a reconnect flag), the CEO opens
   the printed `http://127.0.0.1:53682/auth?state=…` link in a Mac browser and clicks Allow; the
   third `n` answers "Shared Drive?". While an app's publishing status is **Testing** the CEO's
   address must be a test user and the refresh token expires after 7 days. **Final state
   2026-09-09 19:36:** the box now uses project `mooniex-cookierun` (OAuth app "MoonieX CookieRun
   Archive", **In production** — Google demands a homepage + privacy URL for that, filled with
   https://mooniex.com and https://mooniex.com/privacy), Desktop client `rclone-winbox`
   (`578700074167-k6ittpff8t6kfhm82p1pjba0c9qj1268…`), token re-issued at full `drive` scope with the
   CEO's own click; it does not expire. The first attempt in the Make.com project
   (`gen-lang-client-0516233449`, client `997773077636-…`) stays as a spare; that project cannot be
   published without app-domain URLs of its own.
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

### On Contabo the bridge is ABSENT, but uploading still works (measured 2026-09-10)

`~/.config/mooniex/gdrive-bridge.json` does not exist on the VPS, so **every
bridge action fails there** — `move`, `rename`, `trash`, `create_folder`,
`create_doc` and, the one that matters most, `append_log`. `ilag_sync.py`'s own
`append_log()` is built on the bridge, so it fails too.

**That does not mean a Contabo session cannot file a clip.** The upload path is
separate and works: `ilag_sync.upload(local_path, name, parent_id)` talks to the
Drive REST API directly using `GOOGLE_OAUTH_CLIENT_ID` / `_CLIENT_SECRET` /
`_REFRESH_TOKEN` out of `/root/projects/mooniex-claudeflow/.env` (note the
`GOOGLE_OAUTH_` prefix — grepping for `GOOGLE_REFRESH_TOKEN` finds nothing and
wrongly reads as "no credentials"). The same token appends `logs.txt` fine with a
plain `uploadType=media` PATCH, and reports `capabilities.canEdit: true`.

So on Contabo, filing a clip is: `upload()` → PATCH `logs.txt` → verify. **Both
halves or neither** — ILAG rule 4 forbids leaving a file on Drive with no log
line, and a session that can upload but cannot log must not upload.

Two safety steps that are not optional when appending `logs.txt` by hand,
because a `uploadType=media` PATCH replaces the whole file and the log is
append-only:

1. **GET `?alt=media` and save the bytes locally before writing.** That copy is
   the only undo.
2. **After writing, re-download and assert `new.startswith(old.rstrip())`** —
   proof no history was truncated — plus a byte-delta equal to the line you
   added. Size alone is not verification.

Measured clean this way filing `S22-TheCrate-Fix1.MP4` into `Fix-2`: 60,606 →
61,011 bytes (+405), prefix intact, new line last.

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
| `ALL DRAFT/ASSETS` | `1LJreOD8H3jUNzypxTnPwvq-pS7jkQNRd` | Shared assets usable across every channel. `ALL Assets` = general cross-project media, named for subject, image or video. `AI Assets` = AI-generated B-roll, VIDEO ONLY, sub-folders named `<CHANNEL> (ratio)` e.g. `BLACK LIQUIDITY (9:16)` (always both ratios per channel), files named `(scene/purpose) (D-M-YYYY) (AI model)` — see "AI Assets footage naming" above. `XM Assets` / `Exness Assets` = one sub-folder per real-world event (e.g. "XM GALA DINER 2024"), holding every photo/video shot during that event — both already matched this pattern before any fix was needed. | **Drift found 2026-09-18 (recorded per Rule 6, definitions NOT invented — ask the CEO):** six more broker folders exist here that this map never listed — `FXGT Assets` `1ZrNp0P-0oCBF549KrLtuP46hLgAnTFEC`, `FXPro Assets` `1ra1DDwzMEOi1EyvLoW6hLB0jeFjHzgFa`, `IQ Option Assets` `10x4nDVx0nkBkT92ReU_l4Ho_mRE3cJQs`, `Infinox Assets` `1xz0GZfT0VxxeD0-0Loz0i8o81q_4nd--`, `KCMTrade Assets` `1kKJkiTlKcCHyWF4Nmpzb9qYSccoWDAcP`, `OANDA Assets` `15b0xPW_e8gFMK4W-3Xvutp_Z8MRgNsgq`, plus `Cover Example.` `19lXq1c40za6V3A8E5PcHoJrdvuqvQ1_I`. They look like the same per-broker pattern as XM/Exness but nobody has said so — no definition is written here until the CEO gives one. Also note: **there is no audio folder anywhere under ASSETS**, which is why a shared TTS voice library has nowhere to live yet.
| `ALL DRAFT/ASSETS/AI Assets` | `14uc0nxq0ZmaS0GZuCq7hZOl1ROeUYRbV` | The parent of the four `<CHANNEL> (ratio)` folders. Id recorded 2026-09-18 — it had been missing from this table, and the CEO pointed at it by link when asked where B-roll belongs ("ในนี้มีอยู่แล้ว"). Definition is on the `ALL DRAFT/ASSETS` row above. |
| `ALL DRAFT/ASSETS/Audio` | `1QxYqKsn2AqwujTH4It9NXKAsQvXmAOXH` | Created 2026-09-18 on the CEO's instruction, who gave both the path and the definition in the same breath: **"Audio อาจจะมี /SFX หรืออื่นๆ ได้อีก เป็น Sound Effect ที่ใช้รวมกัน"** — i.e. audio shared across channels, not tied to one clip. Per-clip audio still lives in that clip's own `Audio/` under its channel folder; this one is the shared shelf. Children are named for the kind of sound they hold. |
| `ALL DRAFT/ASSETS/Audio/Voice Library` | `1WIsUFqcsHY_PQpFX3kzLI_qZOWZxcsMF` | Created 2026-09-18, CEO-named ("ALL DRAFT/ASSETS/Audio/Voice Library/ Drop file here"). TTS voice samples kept so a narrator can be chosen **by listening, without generating anything again**. First contents: 30 Gemini 3.1 Flash TTS Thai takes of one BL50 excerpt named `Gemini31-Thai-<NN>-<Voice>-<GoogleLabel>.mp3`, one 19-minute audition reel, `INDEX.md` giving each voice's timestamp in that reel, plus the losing engines kept for comparison (Chirp 3 HD, Gemini 2.5 Pro, MiniMax) and `_script-that-was-spoken.txt`. 60 files, 85.3 MB, every one md5-verified. |
| `ALL DRAFT/ASSETS/Audio/SFX` | *(not created yet)* | Defined by the CEO on 2026-09-18 in the same message as `Audio/` — shared sound effects. **Do not create it until a real file needs filing** (Rule 3). |
| `ALL DRAFT/AI Assets/BLACK LIQUIDITY (9:16)` | `1vg8j7DY_hPE-X3yyTsp6ZrM8Gf72cfVG` | 21 real Kling V3 Pro clips renamed 2026-08-04 to `(scene) (date) (Kling V3 Pro)` pattern; `CHARACTER+THEME.png` left untouched (reference asset, not footage). **2026-09-18:** +65 Seedance 2.0 clips (Higgsfield Unlimited, 3–7 Aug 2026) named `(purpose) (D-M-YYYY) (Seedance 2.0).mp4`, purpose in English kebab; ~17 % of them are general-use rather than red/black and are kept here anyway, told apart by the `fit` column in `Agents/prototypes/bl-broll-catalog/CATALOG.md` (CEO chose one folder + tags over a new GENERAL folder). One clip (#48 chat bubbles) carries baked-in Thai text and is tagged `caution`. Gate row in `playbooks/drive-archive-gate.md`. **2026-09-18 (later that day):** +5 **Wan 3.0** clips named `(purpose) (D-M-YYYY) (Wan 3.0).mp4` — the keepers from the Kling-vs-Wan bake-off; three of them carry legible baked-in ENGLISH text (a phone 'RETURN 35% / MONTH', a court 'NOTICE OF SEIZURE', a bank 'TRANSFER FAILED'), which is why Wan won that test and why each has a `caution` row in the catalogue. Folder now holds 65 Seedance + 19 Kling + 5 Wan + `CHARACTER+THEME.png`. |
| `ALL DRAFT/AI Assets/BLACK LIQUIDITY (16:9)` | `1Fad43yAblQvTrqAv07-16VugdStbMg0f` | Created 2026-08-04; **first used 2026-09-18** — 4 Seedance 2.0 clips (1280x720, 15 s, generated 1–2 Aug 2026) moved here out of a `Mooniex B-Roll Library` folder that had been sitting inside the `ALL DRAFT/BLACK LIQUIDITY` channel root, where b-roll does not belong. Renamed to the convention; the CEO confirmed the model by hand after the move went in as `(model TBC)` — **do not guess a model, ask** (Rule 7). The empty `Mooniex B-Roll Library/01_trading-finance` folders were trashed on the CEO's word ("ลบออกได้เลย เพราะมันคือแกะดำ") after re-verifying both were empty. |
| `ALL DRAFT/AI Assets/MYPASAKON (9:16)` | `1TYQbXsEduH-gWMtfpwrMZq2r6x0PiU51` | Empty, awaiting first footage. |
| `ALL DRAFT/AI Assets/MYPASAKON (16:9)` | `1jpsoZi11u9WVZmmR0UxBQDCRKvATolRE` | Empty, created 2026-08-04, ready for future 16:9 footage. |
| `ALL DRAFT/BLACK LIQUIDITY` | `1nH2aZ6B8wuI9KoxMSS4hAk77cGq0Z1WY` | AI-Avatar short-video channel (TikTok @black_liquidity). **Two files sit at this root on purpose and are not clip folders:** the lipsync reference videos the claudeflow pipeline feeds to Sync Labs — `main.mp4` (640x1024, the original, and the reason every episode before 2026-09-18 has a soft face) and `(BL-avatar-lipsync-reference) (18-9-2026) (OmniHuman 1.5).mp4` `1jTFDDm3f8MLVGubSo9xubIyX8AYJCR47` (1080x1920, 20 s, the one `VIDEO_REFERENCE_FILE_ID` now points at). The CEO chose this location — "ข้างๆ อันเก่า". The channel logo lives here too, on the same instruction: `(BL-logo-cropped-transparent) (18-9-2026).png` `1UcCowYlq3OyV-pj-SrAYjNUunmyraxdw` (698x256, already transparent — the one the cut template uses) and `(BL-logo-source) (18-9-2026) (CEO).png` `1-09cf5YQJy5s1-IhBzvZPHs_UVv92YIr` (1080x603 uncropped original). Inside: **one sub-folder per clip** — docs, script, footage/b-roll, MANIFEST — the editor/script-writer's workspace for that clip. |
| `ALL DRAFT/MYPASAKON` | `10L6KFHfi-rOnTqh9F1PRJDTGYh603Ajg` | Main channel, CEO's own trading content, 80K+ followers. Same per-clip sub-folder structure as above. Renamed 2026-08-04 from `MY PASAKON` to match the CEO's no-space PROJECT-naming convention; 14 sub-folders/clip-titles with "myPasakon" casing also fixed to "MYPASAKON" the same day. |
| `ALL DRAFT/YT: MYPASAKON` | `1YnVptu-1dhwblIf3nojXu7Fnn24X353a` | Confirmed 2026-08-05 — same pattern as `BLACK LIQUIDITY` (below), just a different channel: YouTube-specific cut of MYPASAKON content. One sub-folder per clip, named for the clip's topic; inside each, production-stage sub-folders (AI Drafts/Final Draft, Audio, Rawcut, Thumbnail, Convert to .mp3). Renamed 2026-08-04 (was "YT: MY PASAKON"). |
| `ALL DRAFT/LUNGNOTE` | `1luO-_NW1eKmT7gfbQbKMDSrcpoG9iyKG` | Video project folder for LungNote (real Mooniex project name — was misspelled `LUNENOTE`, fixed 2026-08-04). Same name as `PROJECT/LUNGNOTE` on purpose: that one holds LungNote's non-video docs/images/billing, this one holds its video/footage — same split pattern as MOONIEX. Confirmed 2026-08-05 — same per-clip / production-stage pattern as `BLACK LIQUIDITY`; `DAY0/` already shows the Audio/Finals structure. |
| `ALL DRAFT/TRADE TO THE MOON` | `11YGzdDAtKyJVSS9VkKyX9on8_AmQ6A18` | Confirmed 2026-08-05 — same pattern as `BLACK LIQUIDITY`: one sub-folder per clip (TTTM-titled), production-stage sub-folders inside each. |
| `ALL DRAFT/YT: ILAG` | `1Pczc2QfRilB2DoGUVl7ZPPSwy-cbF6KN` | Defined 2026-08-12. YouTube channel of **AI-generated short films**, ILAG Studio brand. "ILAG" is not an acronym. Does NOT use the per-clip production-stage layout of the other channels — see the "YT: ILAG" section above for its own layout, `S<n>` scene naming, and the mandatory per-project `logs.txt`. |
| `YT: ILAG/Do Not Disturb (Higgsfield Global Film Festival 2026)` | `1GT_h_D6pMMpPuspoP7d_lXz9dzZQAt6w` | Renamed 2026-09-24 from `Do Not Disturb` (CEO: add the competition name; id unchanged, RENAME line in its logs.txt). Defined 2026-08-12. One **project** = one film/episode; `Do Not Disturb` is the episode title (horror short for the Higgsfield Global Film Festival, deadline 2026-09-03). Holds everything needed to hand the film to an editor: `All Scene/`, `Element/`, `Soundtrack/`, the `StoryBoard` doc, and its own `logs.txt`. |
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
| `ALL DRAFT/FB: ละครสั้นคุณธรรม` | `1zu3azrqtw22X0n72fJfREDWQb_kjLm4K` | Created 2026-09-18, CEO approved the whole tree in chat ("ตามนั้น Approve") after being shown it. The Facebook channel «ละครสั้นคุณธรรม by ILAG Studio» (page id 61594116376333, which lives on the **Dorsine Gobb** profile — see the two-Facebook-accounts note). Thai moral short dramas in the ฟ้ามีตา format: **one complete story per episode**, villain punished, family visibly comes through. Named `<platform>: <channel>` like every other channel row. **Inside it, one story = one folder named `เรื่อง<ชื่อเรื่อง>`** (CEO 2026-09-19 — the word เรื่อง always first; not `EP<n>`), each holding `All Scene/ACT<n>/`. **Follows the YT: ILAG branch rules in full** — the CEO pointed at `YT: ILAG` by link when asked for a pattern — so: one `logs.txt` per project, append-only, `S<n>` scene folders, exactly one `Element/`, nothing in the branch ever deleted, and plate/sub-folder names are the director's to choose. |
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

| `FB: ละครสั้นคุณธรรม/เรื่องจุดจบของเจ้าหนี้นอกระบบ` | `1TqUWgJuvrLsePuhFqFsj35NtdDQdoVLy` | The first story, working title «บัญชี» in the repo (was `EP1 บัญชี`, then `เรื่องบัญชี`, both 2026-09-19 — CEO: one story = one folder named `เรื่อง<ชื่อเรื่อง>`, the word เรื่อง always first; the show is made story by story and each story already carries its acts under `All Scene/`). Children: `All Scene` `1N4VfSl4ZUtCi2bNf4BOfNrSLOA2BlyHY` (→ `ACT1` `1JXwe8zap26f8YPXKPvFAAcB_6ZVBLtyn`, approved 2026-09-19; `ACT<n>` per act, same pattern, no re-ask), `Element` `1atBkEGmvH-EAIUgRUxNEEyQcPPXDGDN9` (→ `Character` `1mQ5HxUwPS-bNqT7d7bgTLMhxGBayeEGM`, `Location` `1DlzY-QJ3QnGk_EEwIrIOb8gRckOt15JS`, `Prop` `1ZgN1FS-tWrxFVVhIIEQrFDbkHOLzARLP`), `Soundtrack` `1XBQ_P4gdYqtgEjDUH1RMpRwMz6vaexzv`, `Final Draft` `1aq3B9g8NQyAhgXlim-WywmtZmGrWQ7dy`, `logs.txt` `1bbSIUxnVoM7V5492dBW1vcoUYrp-ibNE`, `StoryBoard` (Doc) `1jGDHb4RAJxtwN6U8Hu7N5D9kNtRYrboSJoGKrlTxzrk`. Episodes are numbered `EP<n> <title>` because this is a recurring show and bare titles stop sorting once there are twenty. **Exception to the branch's delete-local-after-upload rule, stated by the CTO and approved in the same message:** the `Element/` plates stay on the Mac as well as on Drive. `tools/build_shotsheet.py` refuses to render a shot sheet whose handles have no local plate, so deleting them would break the build; the rule exists for 500 MB of renders, and all 20 plates together are ~12 MB. |
| `BACKUP` (root) | `1vU9GvMZdMXUV60_kTIkMR1aTwZcEHdlq` | NEW 2026-08-04. Important data that doesn't belong to / can't be categorized into any other folder, specifically related to backing up or redundantly storing data in 2-3 places. Can be temporary or permanent. **2026-09-10:** holds, directly at this root, `Agents-worktrees-2026-09-10.tar` (id `1yWF1ArtjxYyhkNNUuICskv00X1h52A4k`, 48.8 MB) and `PARKED-mooniex-moonx-ignored.tar.gz` (`1BPEG1mazutBiF2Utlx8zGXq3joJ6DQQ8`, 248 MB) + `PARKED-mooniex-video-engine-ignored.tar.gz` (`1zvbnsoHwxXvQoSTJ5-i3vckCGgukDgeN`, 7 MB), each with a `.manifest.json` beside it (sha256/md5, source, restore line) — CEO-approved in chat ("สำรองถ้าไม่มั่นใจ ใน Skill google drive filling"); gate rows in `org:playbooks/drive-archive-gate.md`; log lines in `~/.claude/logs/drive-archive.log`. A `BACKUP/Agents Backup/` sub-folder is proposed for these, not yet approved. **2026-09-23:** also `Agents-Work-task-95439aa8-2026-09-23.tar` (`1uPnam5aoLWqZEgQH7kFOpBMmCkhU_STr`, 51,200 B, md5 `731889bf277119fa89b8042f9fb9a831`) + `.manifest.json` — the first Work/ archive (`tools/workdir.py close --archive`), CEO-approved in chat; every later closed task with unfiled Work files lands here as `Agents-Work-<task>-<date>.tar`. **2026-09-24:** also `ILAG-trailer-plates-2026-09-24.tar` (`1Sd19nC5PaGyN9DU-L2Ao-1AHwWoku8Ah`, 20,930,560 B, md5 `1bdbe13cd6f4dcff6701238acfae7e5c`, 8 PNG) + `.manifest.json` (`1piIia4EVhCgBdHCANaUljCSVK34FpA20`), the TopView trailer's reference plates backed up before winbox's Windows reinstall on the CEO's instruction; md5 read back by id. Temporary home: they belong in the trailer's own `YT: ILAG` project `Element/` once that folder is approved. Also contains `iPhone14Pro_Backup` (id `1L4G227DG8Tf0AQUE0iozhyAycc1JTnpk`, created 2026-08-05) with NO definition yet — ask the CEO before filing anything into it (Rule 7). |
| `BACKUP/FaceBook Backup` | `1cNHt6bg7-ggXf8ec6DChzouUrw3nUGig` | Meta "Download Your Information" auto-export bundles — rarely actually used. Moved here from Drive root 2026-08-04 (was a root-level folder). Meta's export flow has no destination-folder setting, so new `meta-*` exports will keep landing at Drive root — move each one into this folder manually/by AI when found. The old stray `meta-2026-Jun-18-22-41-35` was merged in here 2026-08-04. |
| `BACKUP/CookieRun Backup` | `1a5I-YVpeLelju2EY5Ey-jqDmRymfgQEl` | NEW 2026-09-06, CEO-approved in chat. Raw copies of the Cookie Run bot's data from the Windows box: the CEO's recorded takes, later the bot's own sessions and training sets. Uploaded from the box by rclone (remote `gdrive:`, scope drive.file) as one tar per item + sha256 manifest, verified with `rclone check`. Rules and lifecycle: `cookierun-bot/docs/DATA-STEWARD.md`; the move row lives in `playbooks/drive-archive-gate.md`. Created by rclone (not the bridge) so the drive.file token can still see it. **2026-09-13:** also holds, at this root, `from_pod-mac-only-2026-09-13.tar` (486,183,936 B, 27 models, sha256 `d2052f85…`, Drive md5 `cf692c4e…`, `rclone check --one-way` → 0 differences) + its `.manifest.json` — the models that existed only on the Mac when `cookierun-bot` was split into code-on-GitHub (`PASAKON/MoonieX-CookieRun`) and data-on-winbox. The other 31 files in that directory were byte-identical to winbox's own copies and were not uploaded: **compare by md5 before uploading a model directory**, or you ship 763 MB to preserve 464 MB. The Mac could not upload it itself — the rclone token is confined to winbox by rule 6 above — so the tar was scp'd to the box and copied from there. **2026-09-24:** child `hits` `1e-TGFYiEecMKIu34dOhJeZMw1PREd2__` (CEO "อนุมัติ"; hit frames beyond the 500 MB/day that stays on the box, one tar per day — definition in the tree; gate file `archive/hits_archive_enabled` on winbox written the same day). |
| `BACKUP/CookieRun Backup/play_rec` | `1U_-pog8MCHrvpVbLLbwe_sMJKDRbZphH` | `<take>.tar` + `<take>.manifest.json` per recorded take. First item 2026-09-06: `1788525250.tar` (3,494,379,520 B, 14,000 frames). 2026-09-08: `1788654527` streamed as `.part1of3.tar` … `.part3of3.tar` (19.6 GB total, split because a single 19.5 GB rcat died on `rateLimitExceeded` on 2026-09-06). |
| `BACKUP/CookieRun Backup/bot_sessions` | `1awbqSHkw9UdXUDOM8lqQ-8QnOmqPM2ND` | Created 2026-09-08 by rclone, CEO-approved in chat ("อนุมัติ"). The bot's own play recordings: per `bot_session-<stamp>` one tar of the round folders NOT in the top 20% by coins (`cookierun-bot/tools/rank_bot_sessions.py` decides) + `<session>.manifest.json`. `rounds.jsonl` and hit frames are tier A and stay on the box. |
| `BACKUP/CookieRun Backup/jumpsweeps` | `1XeGI2SJTU3hIA44t8NBn2BSDDVCO9YSJ` | Created 2026-09-08 by rclone, CEO-approved in chat. Jump-physics sweeps (`play_rec/jumpsweep*-<stamp>`): per sweep one tar of the bursts that carry no human landing click + manifest; bursts the CEO clicked stay on the box with their frames. |
| `BACKUP/Winbox Reinstall 2026-09-24` | `12LWNL3LwEYcfqQWtvnV_KZeKegDt5Ic8` | NEW 2026-09-24, CEO-approved in chat ("อณุมัติ"). The non-Cookie-Run backup of winbox before its Windows reinstall (Cookie Run data goes to `CookieRun Backup/` sub-folders by type, created by the Cookie Run CTO under the same approval). One tar per group + `.manifest.json`; each verified by Drive md5 before the local copy is deleted. **Contents 2026-09-24** (streamed by `scripts/stream_backup_to_drive.py`, each re-listed by `rclone lsjson --hash`: size + md5 + id match; restore line inside each manifest): `downloads-sorrysir-frames.tar` `1DVIRq7jw8lJbQnHGk53VDXtetN2RqK1-` 9.69 GB, 26 Blender/previz `*_seq` PNG folders, md5 `7a866b53…` — deleted from the box · `downloads-other.tar` `1POHYDM7N31_eu3sR9HHyggmKc3r0W8Sw` 3.15 GB, the rest of Downloads minus `.exe`/`.msi`, md5 `ac66aa81…` — deleted · `mooniex-data.tar` `1YlCfyZUEMm2fkH9nYtrF73o6OtXdH8b1` 1.67 GB, `C:\mooniex\{out,sub,astra-workspace,harvest-20260911,line,desktop,brand,youtube,dnd,meta-dnd,meta-sorrysir,poster-20260912}`, md5 `a5c8f9c5…` — deleted · `userfiles.tar` `13f1SOXzPqwGiLJL0RCN4D54V3t9RUNMK` 1.03 GB, Desktop/Pictures/Videos/Music + Documents minus CookieRunScript (game saves, Codex) · `mooniex-live.tar` `1OcA8CLBPufO-VN42FKWLBRdKAoCSqJ27` 0.35 GB, live `C:\mooniex` dirs kept on the box (pclease, coordination, ilag-trailer, tools, runtime, …) · `code-agents.tar` `1jjw_lQAKxxEbn3-UuQQCWvC0mMwjWuD_` (bundle of the 39 branches of `C:\mooniex\agents` not in origin/main — MVP feature/* + worker/* — plus patches + untracked; restore-tested: bundle verifies) · `code-agents-core.tar` `1YK4du_x4l3Em8wEEUWAj55PDXy3tg6ld` (bundle of `~\mooniex` Agents-Core worktree branches not in origin/main + worker scaffolding) · `code-misc.tar` `1dDjV2daqq_narqQYiSsITJW6QnaYAZJL` (hermes-agent diff, LungNote design/handoff, autopull, `.buzz` minus models). Bundles are thin: every prerequisite commit (19) is on Agents-Core `origin/main`, so `git fetch <bundle>` into any clone restores them. |
| `BACKUP/MoonieX HQ` | `1NqyT7TjUHVBuOCo0bw3dRy8niXLcLawK` | NEW 2026-09-24 17:47, created by rclone on winbox minutes after the CEO's re-consent; the family the CEO approved the same day ("ใส่ไว้ใน BACKUP/MoonieX HQ/{สิ่งที่จะเก็บ} ได้เลย เพิ่มนิยามให้ด้วย") for the Machine Contract (ADR 0031, IRON §58). One child per KIND of kept thing, definitions in the tree above; every object = tar/tar.gz + `.manifest.json`, md5 read back by id before any local delete; Contabo uploads through `scripts/rclone_via_winbox.sh`. Children: `Claude-Transcripts` `1l5Up71pZWBHKwOQ5A6XNoKLYqICixyxP` (per machine / project slug / day tar.gz + manifest, kept forever) · `Claude-Uploads` `1t-5xXXx6VNP78Ewj1fd7mwcjk1oO_vyl` (`<machine>/<date>.tar` of `~/.claude/uploads`) · `Work-Archive` `1xu8hXdUZGBino913lCr2zdUz8kTd8tqA` (new `Agents-Work-<task>-<date>.tar` from `workdir.py close --archive`; the 2026-09-23 one at the BACKUP root moves here server-side on the CEO's yes) · `Docker-Volumes` `1bODM090gcAhlusA8g_6Jp-w_bzsDINwC` (`contabo/n8n_data/<date>.tar` WITHOUT the n8n encryption-key file, `contabo/org-pgdata/<date>.sql.gz`, weekly) · `Machine-Blueprints` `12yjlX_MvhjmJlwuhqFEqVFcQkNR0M7r0` (`<machine>/<date>/` copy of each capture; git `state/` is primary) · `State-DB` `15xudjmiHK6MfSCxM48cqwjPOKOWgoNzO` (CEO "อนุมัติ" 2026-09-24; `<machine>/tasks-<date>.sqlite.gz`, sqlite online backup of `state/tasks.db`, weekly). Inside Claude-Transcripts: `contabo` `1d7mVpwFy4bY56u2t30f9nUfmhbqa11Xt`, `mac` `1FqUUq9CdwL7AvMnPzlui3kgUtKTMU4ZP` (the old `BACKUP/Claude-Transcripts` folder, moved whole 2026-09-24). **First objects 2026-09-24** (all from Contabo through the winbox relay, md5 read back by id, ledger `~/.claude/logs/drive-archive.log`): 29 transcript day-tars (370 MB), `Claude-Uploads/contabo/2026-09-24.tar`, `Docker-Volumes/contabo/n8n_data/2026-09-24.tar` (1.55 GB, id `1vvQ9NAJ81giQJwxBNQ_AhF8ElG1EjsGl`) + `org-pgdata/2026-09-24.sql.gz` (1.1 KB — the cluster is empty), `Machine-Blueprints/{contabo,winbox}/2026-09-24/`, `State-DB/contabo/tasks-2026-09-24.sqlite.gz`. |
| `BACKUP/Mac-Reinstall-2026-09-24-*.tar` (BACKUP root) | claude-home `1GMBZeR4sQkcEQ3iJCmXORA_z35rqu8Et` · MoonieXHQ-code `1t8LzRXb53wzHuHkgxZ3dahueAhGyJ0-z` · MoonieXHQ-data `1bT-nFkwwqRBtJr_QKYDoS9g3HDni5Iur` | NEW 2026-09-24, CEO in chat ("session ของ Claude และ MoonXHQ … ของ MAC สำรองให้เลย") before the Mac wipe. **claude-home** 1.77 GB, md5 `50b14e71…`: all of `~/.claude` minus plugins/cache (every transcript; the symlinked config/skills/memory live in Agents-Core / Agents-Memory git). **MoonieXHQ-code** 0.92 GB, md5 `19a45797…`: thin bundles of the 10 repos with unpushed branches (prerequisites on their remotes; ClaudeSign's remotes are `mooniex`/`upstream`, not `origin`), 13 stash patches (ClaudeFlow stash0 alone is 886 MB with untracked files), dirty patches, untracked files; **restore-tested** (downloaded, extracted, Agents-Core + ClaudeSign bundles verify, stash patch applies). **MoonieXHQ-data** 2.87 GB, md5 `8625c45b…`: gitignored data — Agents/Core state (tasks.db etc. plus consistent `sqlite3 .backup` copies under `_extra/sqlite`) + output, ComfyRunpod studio/data, WebDesign/archive, CookierunBot shots/vision, Work/, UNKNOWN/. Regenerable dirs (node_modules, .venv, .next, worktree checkouts, ClaudeSign/.tmp) skipped. **Secrets never went to Drive:** `.env*`, certs, `~/.ssh`, `~/.config/mooniex`, `~/.claude.json`, launchd plists, dotfiles and shell history are in `contabo:/opt/MoonieXHQ/Archive/mac-secrets-20260924/` (root 0600, sha256 checked both ends). The broken `Mac-Reinstall-2026-09-24-MoonieXHQ-code.PARTIAL-DO-NOT-USE-truncated-859MB.tar` `1vaZ9ywNjgjxs_VCUyEAGzLnx7-lL5C-E` was trashed on the CEO's OK ("ลบทิ้ง"), see the field note. **Photos:** `Mac-Reinstall-2026-09-24-Photos-p00-library.tar` (library database + resources, derivatives/caches skipped) and `-p01`…`-p19.tar` (the 8,792 originals in ≤3 GB parts, sorted by path) — 20 tars, 52.76 GB, 11,222 files, every one md5-checked by id, 0 skipped, 0 changed; `Photos.sqlite` was last written 03:48, before the upload, and the Photos app was closed. It is the CEO's iPhone camera roll 2021-01-15…2026-07-09 (8,654 items: 7,931 photos, 723 videos; screenshots, bank slips, a passport page — treat as private). iCloud Photos was OFF on this Mac, so this was the only copy the Mac held. Restore: download all 20, `tar xf` each into `~/Pictures/`, open the library in Photos. Ids per part in `~/.claude/logs/drive-archive.log`. |
| `BACKUP/CookieRun Backup/colab_packs` | `1dHtISY1PRVyT5tEP4kr3SqK7zIAJFjpT` | Created 2026-09-18 by rclone, CEO-approved in chat ("เครื่องว่างแล้วลุยเลย", answering a request that named this destination and its size). **Derived working data, not an archive** — the Cookie Run IDM training corpus packed into `.npz` shards (`x` uint8 80x192 frames, `y` jump/slide labels, `t` timestamps) so Colab can read it; Colab cannot reach winbox, which is the only reason these bytes are on Drive at all. First upload 2026-09-18: 799,300 frames, 0 skipped, **47 shards / 11.45 GiB**, `--transfers 1 --drive-chunk-size 64M` (the bot was playing), `rclone check --one-way` → **0 differences**. Every shard is re-creatable from `BACKUP/CookieRun Backup/play_rec` with `windows/cookierun_pack_for_colab.py`, so **deleting this folder costs a repack, not data** — unlike its sibling folders, whose retention rules must not be read onto it. Gate row recorded in `mooniex-agents/docs/ops/drive-gate-row-colab-packs.md`; it still needs mirroring into `org:playbooks/drive-archive-gate.md` **from the Mac**, because Contabo's wiki is an rsync snapshot and a write there is overwritten by the next sync. |
| `YT: ILAG/รอตั้งชื่อ (Topview Wan3 Challenge 2026)` | `1fdS2YrDWrEF_trd4YzgoyxOBsH3e2oon` | Created 2026-09-24, CEO in chat: "Create New Project Folder ใน google Drive ไว้ข้างๆ Do not disturb + Sorry sir ... สร้าง Path Folder ตามกฏ และสร้างเลียนแบบ Sorry Sir + DND ได้ ... ชื่อเรื่องยังไม่มี ใส่ {รอตั้งชื่อ} (Topview Wan3 Challenge 2026)". The third ILAG film: the alien-ocean trailer for the TopView Wan3 Challenge (submit by 28 Sep 06:59 Thai). Rename in place once the title exists. Same branch rules; `logs.txt` `1asL3Woa5f1Lz3qhdHHTRrB-krpSRXDBY`. Children: `All Scene` `1LTme3KAdrsQgYv_F6J7pf9cq8BYp7NPD`, `Element` `1AglGrsH_4PXPYXuRog9Gkfbjaa6gYNYX` (→ `Character` `1IXrrVe0WcdSNVjFxQHh5APm3Sr-8NsXa`, `Location` `1mrnHtqYNcqUa5lyw_vVxxh0tvu-CJf71`, `Prop` `1FUwd7qPAsBtrVjFxoOZpcHlbnK1fkjPf`: the ChatGPT reference images, filed by their name prefix), `Soundtrack` `1eETTWwzOY3u5z_mcmhv4Ln-NsuuOdmVD`, `Final Draft` `1NkLTYnK4kRCZbeaZePLTO4hp0LihZDNP`, `Previz` `1UAxdGydQWpV7-tb9vcEoRj3Ue_EKN4bp` (2026-09-25, mirrors Sorry, Sir's Previz/: the H3 360p previz takes), `StoryBoard` Doc `1H9S-CG0YFunegyIctWrJSyM68b-xq2tGd0_dML4NEC0` (a snapshot; the living copy is Agents-Core `docs/promo/topview-trailer/`). |
| `YT: ILAG/The Valder Collection No.7` (TRASHED) | `1Sh5qcE_NPwsb7QS1Fv-xT2qpNavkRAe1` | Found 2026-09-24 (created 2026-08-20, never mapped). CEO the same day: "โปรเจคเก่า ลบออกได้เลย". Re-listed right before: 3 mp4s, 55.3 MB (`hf_20260819_231613_72417b15…` md5 bd77ac95…, `hf_20260820_113545_8da554d3…` md5 7605d7e4…, `hf_20260820_212856_6ad23888…` md5 3673e189…), found nowhere else under Sorry, Sir or DND by md5. Moved to Drive Trash (restorable until ~2026-10-24), not permanently deleted. |
| `YT: ILAG/Sorry, Sir (The Valder Collection) (Higgsfield Global Film Festival 2026)` | `1eJH1p789LLfufpSgWF47KeHziUxOHxPh` | Renamed 2026-09-24 from `Sorry, Sir (The Valder Collection)` (CEO: add the competition name; id unchanged, RENAME line in its logs.txt). Second ILAG film, in production Sept 2026 (Higgsfield Global Film Festival, deadline 9 Sep). Same branch rules as `Do Not Disturb` — its own `logs.txt` (`1bSH4v-E8PLkUtZVACum_O2nW1_FlsBuW`), append-only, reconcile on entry. Children: `All Scene` `1KMD0xsVe691SSh5eCAWM_QDOJMbzRNyJ` (holds `Fix-1` `1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc`, every take up to the morning of 2026-09-08 filed under its scene name, and `Fix-2` `1rkCQ5SSZeOvyX-0UZXe3OvBtFhObHrkw`, created 2026-09-08 on the CEO's instruction as the SECOND EDIT — "ฉากที่สร้างในวันนี้จนถึงจบโปรเจคใส่ Fix-2 … เป็นการ Edit ครั้งที่ 2": every clip generated from 2026-09-08 to the end of the project files here and Fix-1 takes nothing new; seeded by moving the five 2026-09-08 clips S14a/S14b/S15b1/S16/S15c out of Fix-1, DECIDE line in logs.txt), `Element` `1AD-nNuvJc_Z25qot7zATWzY2ZZtI_BX3`, `Plates (raw source)` `1GocR7uHiG2VNqjqu42JdbSMvCnSG6QYJ`, `Previz` `1mMSvWzzp4WoQK31N_Th3kPptQ1VkljB2`, `Soundtrack` `1CN5ceI34pxKfAf6b9UkIK1DcgB08BvfC`, `Final Draft` `1YBTampuEPWbwHPzRzlO3PRLtqAqNDa4A`. |
| `Sorry, Sir/Previz` | `1mMSvWzzp4WoQK31N_Th3kPptQ1VkljB2` | Created 2026-09-08 on the CEO's explicit instruction, which also named the path. Holds the grey previz clips fed to the generator as camera/blocking references. Each is named for the SCENE that used it — `S2C-Previz.MP4`, `S2D-Previz.MP4`. When the scene a previz belongs to is not known, the CEO's fallback is a `Unknow` sub-folder here; it does not exist yet because nothing has needed it, and it should only be created when something does. |
| `Sorry, Sir/Meta (Higgsfield)` | `1cV5SkpAd5xrargbiyF4wmL2Y_rEoy6CS` | Created 2026-09-12 by rclone on winbox, CEO-approved in chat ("เอา ใส่ Upload Drive ไว้เลยตั้ง folder ไว้ด้วย"). The branding the festival **requires** on the delivered film. **This film is 16:9 (1280×720), so only the 16:9 pair lives here** (CEO, same day, after the first upload put all four in both folders): `higgsfield_watermark_16_9.png` (3840×2160, `1SCmNdnlTfVMgDt1xxoSx850dk4Zos_wv`) and `higgsfield_packshot_16_9.mov` (ProRes 4444 **with a real alpha channel**, 3840×2160, 9.13s @30, `1hlzWomoKIb70EyTXr2k-1yIlhXk_Pm4N`). Uploaded from winbox `Downloads` with `rclone copy --transfers 1 --drive-chunk-size 64M`, verified `rclone check --one-way` → 0 differences. The 21:9 pair was trashed from here in the split, logged with an `EXCEPTION:` note per the branch's no-delete rule. Not footage and not a generation plate, which is why no existing folder fitted. **The 1080p watermarks winbox also holds are deliberately NOT here** — the 4K ones downscale cleanly to a 720p master and there is no reason to ship the smaller pair. |
| `Do Not Disturb/Meta (Higgsfield)` | `1uNBmXIh7RukK4auf2T0juFD_cG9Z9Quq` | Created 2026-09-12, same approval, filled by a **server-side** `rclone copy` from the Sorry, Sir folder (seconds, no second upload), verified `rclone check` → 0 differences. **This film is 21:9 — verified as 1470×630 from its own Final Draft rather than taken on trust — so only the 21:9 pair stays**: `higgsfield_packshot_21_9.mov` (3840×1646, `1zPHdGxOGH370nBoOkPutIY67mA6ca80l`) and `higgsfield_watermark_21_9.png` (5120×2160, `1v2Ga4qJIK_MbVAyFqOIMojW9mAPOpP4h`). The 16:9 pair was trashed here in the same split. **Why the split matters:** giving an editor both ratios invites the wrong one being burned into a delivery, and that is not visible until someone watches the export. |
| `Sorry, Sir/Poster` | `1p1_DwQSG6Z9zyRdJpNFrU9umIDOUsBae` | Created 2026-09-12, CEO approved in chat (he answered "Poster" when asked where the key art should go). Holds the film's key art and the YouTube thumbnail — not footage, not a generation plate, which is why none of the existing folders fitted. First contents: `SorrySir-Poster-A-Lineup-16x9-2K.png` (the fifteen-character line-up outside the museum) and `SorrySir-Poster-B-TheWall-16x9-2K.png` (the empty wall with one small figure), both GPT Image 2.5 Sunburst, 16:9 2K, titles rendered by the model and checked letter by letter. |
| `Desktop Cloud` (root) | `115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR` | Cross-device sync (Desktop/Windows/Drive). Expect duplicates and off-taxonomy files — that's normal. **AI never auto-files in or out — ONE exception, below.** Search/read is fine anytime; delete only on direct CEO command. **EXCEPTION (CEO 2026-08-24): SomPong's video grabber files here automatically.** The CEO was shown the "AI never auto-files here" rule, asked where a clip grabbed from a pasted link should land, and chose this folder over `ALL DRAFT/ASSETS/ALL Assets` and over a new folder — granting the carve-out explicitly. Scope: uploads only, by that one feature, of clips the CEO asked for by sending a link. Nothing else about this folder changes, and the no-delete rule is untouched. Target id lives in `DRIVE_SOMPONG_GRAB_FOLDER_ID`. **Do NOT reuse `DRIVE_VIDEO_PARENT_FOLDER_ID` for this** — that one is `ALL DRAFT/BLACK LIQUIDITY` and is load-bearing for `mooniex-claudeflow/src/video/videodrive.js` and `scripts/higgsfield/gen_loop.py`; repointing it breaks both. (`scripts/video_to_drive.py` was built on it and would have created a `desktop cloud` folder *inside* the BLACK LIQUIDITY channel, beside 53 real clip folders. Caught before it ever ran.) |
| `My Picture & Videos.` (root) | `1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy` | Personal photos/videos — memories, family, travel. Very personal. File by month (e.g. `2026-08/`) so timeline browsing works. **EXCEPTION (CEO 2026-09-10): SomPong's family-group archive files here automatically.** The CEO asked SomPong to keep every photo/video/file sent in the family LINE group "เอาไว้เป็นความทรงจำ" and approved both carve-outs explicitly: uploads happen without asking each time (Rule 1), and the `YYYY-MM` month folder is created by the filer when the month turns (Rule 3). Scope: uploads only, by that one feature, into `YYYY-MM/` only. Nothing else about this folder changes and the no-delete rule is untouched. Names: `(sender) (D-M-YYYY) (HHMM) <lineMessageId><ext>`. The credential lives in a second broker (`runners/drive_photo_broker.py`, `DRIVE_PHOTO_BROKER_FOLDER_ID`) locked to THIS folder id — the claudeflow container never holds it and cannot reach it; it only drops files in an outbox on disk. Do NOT repoint `DRIVE_BROKER_FOLDER_ID` (that one is `Desktop Cloud`, for the video grabber). Design: `mooniex-agents/docs/design/sompong-photos.md`, wiki `mooniex:projects/sompong-line.md` F2. |

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
