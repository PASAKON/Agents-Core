---
name: gdrive-filing
owner: CFO
origin: mooniex-org
scope: >-
  Filing rules for the CEO's personal Drive (pass.gob1@gmail.com) — where things
  live and what AI may create, move, rename, or delete. Read before any Drive
  mutation, whether via the gdrive-bridge script or the Drive MCP tools. Rules
  only; not a file-transfer tool.
description: Filing rules for the CEO's Google Drive — read before any create/move/rename/delete there. Trigger on /gdrive-filing, "จัดระเบียบ Drive", "ย้ายไฟล์ไป Drive", "เก็บไฟล์นี้ไว้ที่ไหน", "ลบไฟล์ใน Drive", "save this to Drive", "file this".
---

# Google Drive Filing — CEO's personal Drive (pass.gob1@gmail.com)

This is the **one place** filing rules and the folder map live. When the CEO
defines a new folder or changes a rule, edit THIS file — do not duplicate
rules into memory, CLAUDE.md, or anywhere else. Every session reads this same
file, so it stays consistent without re-explaining itself each time.

## Hard rules — apply to every action, no exceptions

1. **Ask before doing anything.** No silent create/move/rename/delete.
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
│   └── YT: TRADER UNCUT/          NEW 2026-08-05. New YouTube+TikTok channel
│       ├── EP1 | .../             (Jadoodoo/KOSPI crash) → Final Draft/,
│       │                          Audio/, Rawcut/, Thumbnail/, Script (doc)
│       ├── EP2 | .../             (Leopold Aschenbrenner) same 4 sub-folders
│       │                          + Script (doc)
│       └── EP3 | .../             (Nick Pinto/TRUMP memecoin) same 4
│                                  sub-folders + Script (doc)
├── BACKUP/                       NEW 2026-08-04. Important data that doesn't
│   │                             fit any other folder / can't be categorized,
│   │                             or redundant copies the CEO wants kept in
│   │                             2-3 places — temporary or permanent, either
│   │                             is fine.
│   └── FaceBook Backup/          Meta "Download Your Information" auto-export
│       ├── meta-2025-Jun.../     bundles — rarely actually used. Moved here
│       ├── ... (10 total)        from root 2026-08-04. New meta-* exports
│       └── meta-2026-Jun-18.../  land at Drive ROOT (Meta gives no destination
│                                 control) — move each one in here manually.
├── Desktop Cloud/                cross-device sync — AI never auto-files here
└── My Picture & Videos./         personal, filed by month
```

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
```

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
| `BACKUP` (root) | `1vU9GvMZdMXUV60_kTIkMR1aTwZcEHdlq` | NEW 2026-08-04. Important data that doesn't belong to / can't be categorized into any other folder, specifically related to backing up or redundantly storing data in 2-3 places. Can be temporary or permanent. |
| `BACKUP/FaceBook Backup` | `1cNHt6bg7-ggXf8ec6DChzouUrw3nUGig` | Meta "Download Your Information" auto-export bundles — rarely actually used. Moved here from Drive root 2026-08-04 (was a root-level folder). Meta's export flow has no destination-folder setting, so new `meta-*` exports will keep landing at Drive root — move each one into this folder manually/by AI when found. The old stray `meta-2026-Jun-18-22-41-35` was merged in here 2026-08-04. |
| `Desktop Cloud` (root) | `115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR` | Cross-device sync (Desktop/Windows/Drive). Expect duplicates and off-taxonomy files — that's normal. **AI never auto-files in or out.** Search/read is fine anytime; delete only on direct CEO command. |
| `My Picture & Videos.` (root) | `1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy` | Personal photos/videos — memories, family, travel. Very personal. File by month (e.g. `2026-08/`) so timeline browsing works. |

### When the CEO defines a new folder or gives a new rule
1. Add/update its row in the table above (or the Hard Rules list) — this file
   is the only place it needs to go.
2. If it's a brand-new folder that doesn't exist in Drive yet, create it with
   `create_folder` (after asking), then record the returned ID here.
