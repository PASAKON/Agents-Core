---
name: CXO_Procedure_GDrive_BulkTransfer
kind: procedure
owner: COO
description: >-
  PROCEDURE — Move gigabytes into the CEO's Google Drive and run moves / renames / deletes through the bridge: batches, md5 verification by file id, the gate row, the Contabo path without the bridge. Trigger on /CXO_Procedure_GDrive_BulkTransfer, "อัปโหลดไฟล์ใหญ่ขึ้น Drive", "bulk upload", "rclone copy", "ย้ายไฟล์เยอะใน Drive". Read CXO_Rules_GDrive_Filing first.
created_by: agent
author: {role: cto, date: "2026-09-27"}
aka: [gdrive-filing]
audience: [cxo, worker]
---

# Google Drive — bulk transfer and the bridge

Split out of `gdrive-filing` on 2026-09-27 (CEO-approved rename plan, Phase 2). The rules that govern every
step here — ask before creating a folder, never delete without the CEO's word, the folder map — are in
`CXO_Rules_GDrive_Filing` and `CXO_Knowledge_GDrive_FolderMap`. Streaming uploads for big files on Contabo:
`scripts/gdrive-bridge/ilag_rest.py` `upload_stream` (64 MB chunks, md5 checked by id).

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
   **State 2026-09-26 (measured): winbox is on rclone's SHARED client again.**
   `ssh winbox "rclone config redacted gdrive:"` prints `client_id = ` (empty). The 2026-09-24
   reinstall (new account `passg`) re-created the remote without our client, and the box has no
   `Projects\` folder, so `rclone_set_client.py` is not there either. On the shared client, big
   uploads 403 `rateLimitExceeded` for hours: a 562 MB film failed 12 times in an hour on
   2026-09-26, and three uploads died the same way on 2026-09-08/09. Until the CEO re-consents
   (procedure below; the client JSON must come from the Cloud console or the secrets bundle):
   - **Check before any winbox upload.** Run `rclone config redacted gdrive:` and read only the
     `client_id` line. An empty value means the shared client.
   - **On the shared client, one file over 100 MB goes by the Mac REST route**:
     `scripts/drive_rest_rclone_shim.py rcat gdrive:<name> --drive-root-folder-id <parent> < <file>`.
     It uses the Mac bridge's own OAuth client, not winbox's token. The MIME type comes from the
     file name.
   - **A retry loop prints the error of every failed attempt.** Never run the upload with
     `capture_output=True` and log only "not yet". After two `rateLimitExceeded` in a row, stop
     retrying that route and switch to the REST route. Never wait out a shared-client quota.
   [SUPERSEDED 2026-09-26 by the measured state above; kept as the history of the 09-09 fix and as
   the re-consent procedure.] **State since 2026-09-09:** winbox's `gdrive:` runs on OUR client — Google Cloud project
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


## Field notes
