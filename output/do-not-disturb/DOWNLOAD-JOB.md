# Standing job — land finished clips on Google Drive

CEO 2026-08-12 22:20. **Supersedes the Desktop version of this file entirely.**
Start only after the generation wave reaches 20/20 — generation has priority.

**Read the `gdrive-filing` skill before your first Drive action.** It is
mandatory for this branch and it already contains the folder map, the `logs.txt`
contract, and the naming rules. This file only covers what is specific to the
download loop.

## The change

Drive is now the only home. The Desktop folder is retired — it held 513.8 MB on
a machine whose swap is already 90% full. **Local disk is a staging area, not a
copy.**

Target: `ALL DRAFT/YT: ILAG/Do Not Disturb/All Scene/S<n>/`
Project folder id: `1GT_h_D6pMMpPuspoP7d_lXz9dzZQAt6w`
`All Scene` id: `159zXCuZ3AJylUQdgQu5O6fvzclXa4KHa`

`S1`–`S16` **already exist on Drive with ids recorded in the skill's folder
table.** Do not create scene folders and do not invent names — resolve against
that table, never against a name match.

Note the spelling difference: Drive is `All Scene` (correct), the retired local
mirror was `All Screne`. `ilag_sync.py` maps them in `FOLDER_ALIASES`.

## The loop, per batch

1. **Download** from Higgsfield to this machine — one clip or many, whichever is
   cheapest. Many arrives as a zip; unzip locally, there is no password.
2. **Upload** to the matching `S<n>`.
3. **Append `logs.txt`** for each file, same turn as the upload. Nine
   pipe-separated fields, format in the skill. Never batch these to the end.
4. **Verify it is on Drive**, then **delete the local copy**.

### Step 4 is the one dangerous step

- Delete **only files this loop downloaded**, and **only after Drive confirms
  them**.
- **Never a glob. Never a whole directory. Never anything the loop did not put
  there.** Name each file explicitly.
- When in doubt, leave it. Disk is cheaper than a lost render.
- **"Nothing in here gets deleted" still applies to Drive.** Removing a local
  staging copy is not deleting from the branch. Deleting anything *in Drive*
  remains forbidden — including takes that look superseded, which are the
  generation history the festival can demand.

Prove the upload before deleting:

```bash
.venv/bin/python scripts/gdrive-bridge/ilag_sync.py diff
```

`ONLY LOCAL (0)` with `size-mismatch: 0` means every local file is on Drive at a
matching size. That is the green light, and nothing else is.

## Bulk download — do not click cards one at a time

`scripts/browser/higgsfield-jumpcut-gen.js`, **Wave 5 findings
(task-939d45ba)**. Read it first. Summary:

1. Switch the History panel to **Grid view** (`List`/`Grid`, top-right). List
   view has no section checkboxes.
2. The date-section header has a **select-all checkbox**; ticking it reveals a
   bottom toolbar with a real **Download** button that zips the whole selection
   server-side — one click for 12-45 files.
3. The zip lands in `~/Downloads/archive.zip`, then `archive (1).zip`, etc. A
   45-file, ~210 MB zip took ~15s to prepare. **Poll for file-size stability**
   (two `stat` calls seconds apart) rather than sleeping a fixed amount.
4. Keep the source zip until its contents are confirmed on Drive. It is the only
   recovery path if an extract goes wrong.

## Current state — verified 2026-08-12 22:20

`ilag_sync.py diff` came back completely clean:

```
local  : 61 file(s), 513.8 MB
drive  : 63 file(s)
in both: 61   size-mismatch: 0
ONLY LOCAL   (0)
ONLY ON DRIVE (0)
```

Every local file is already on Drive at a matching size. **Nothing needs
uploading from the old mirror**, and those 513.8 MB are pure duplication. The
CEO has authorised reclaiming them; the CTO is confirming scope before anything
is removed.

Drive counts per the skill's table: S1 3, S2 7, S3 5, S4 9, S5 5, S6 4, S7–S16
empty.

## The S2 question — diagnosis corrected

Earlier this was called a silent `cp` overwrite. **That was wrong.** Drive and
local both hold 7 for S2, and they agree exactly — so nothing was lost in
copying. The Higgsfield sidebar showed **8** this morning, which means one clip
was **never downloaded at all**.

When you reach S2: find the card that has no counterpart on Drive, download just
that one, upload it, log it. Do not re-download the whole scene.

Remember the sidebar count includes NSFW-flagged and refunded cards that carry
no usable video. Count those separately and say so, rather than reporting a
mismatch that is not real.

## Verification is ordered one folder at a time

**CEO rule: never verify the whole tree in one order.** A full sweep is a long
loop with a large result and re-checks folders nobody asked about. The C-level
names **one `S<n>`** per order; you verify that one and stop.

- "Verify S6" means S6 only — do not walk S1–S5 on the way.
- `ilag_sync.py diff` is exempt: it is one command with a small result and it
  covers the whole tree, so run it freely.
- The expensive half is the Higgsfield side — opening the sidebar, counting
  cards, opening cards to identify them. That is per-folder and only on request.
- Spot something wrong in a folder you were not asked about? Say so in one line.
  Do not start fixing it.

## Reporting

Hard Rule 10 applies: state change only. For this job that means the one-row
verification result you were asked for, then one report when a batch is on Drive
and logged, plus anything that does not reconcile. No progress pings.
