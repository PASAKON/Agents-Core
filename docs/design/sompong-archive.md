# SomPong LINE archive backup to Drive

Status: **Implemented (broker instance + filer), ClaudeFlow side not yet
deployed** · task-3f9b62a0 (2026-09-26) · design of record: org wiki
`mooniex:projects/sompong-ea.md` section E.

## 1. Why

CEO ruling, 2026-09-26: SomPong's LINE text log and media stay on the Contabo
box for 30 days, then move to Drive "ตามกฏ" (the `gdrive-filing` skill's own
rule set) — a narrow carve-out to a fixed folder, `BACKUP/MoonieX HQ/
SomPong-LINE/<YYYY-MM>/` (Drive id `162JgquLAznKpw_UPL4fHKry4VjU5hQPd`), the
same shape as the family-photo carve-out in `docs/design/sompong-photos.md`
§1. ClaudeFlow (separate task, `docs/sompong-ea-v2.md` in that repo) rotates
rows and media older than its own local retention window into an
**archive-outbox** it never touches again; this task builds the host-side
job that drains that outbox to Drive and only then deletes the local copy.

## 2. The whole path

```
ClaudeFlow (Contabo, separate task)
      │  rotates rows/media past their local retention window
      ▼
/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/data/sompong/archive-outbox/
      log-<YYYY-MM>.jsonl              one append-only text log per month
      media/<YYYY-MM>/<msgid>.<ext>    a media file
      media/<YYYY-MM>/<msgid>.json     its sidecar, written LAST
      │
      │  polled every SOMPONG_ARCHIVE_FILER_POLL_SECONDS (default 300s)
      ▼
runners/sompong_archive_filer.py   (host process, root, no Drive credential)
      │  logs: closed-month + stable(24h) gate → gzip → local ledger (dedup
      │        + -partN numbering) → stage
      │  media: pair-complete gate → sha256 verify → local ledger (dedup) →
      │        stage bin + sidecar separately
      ▼
/var/lib/archiveup/staging/   (owner root:archiveup, mode 2770 — outside the
      │                         outbox's own permission tree, so the
      │                         unprivileged broker can actually reach it;
      │                         same "copy across the wall" shape as
      │                         sompong-photos.md §2)
      ▼
runners/drive_photo_broker.py, THIRD instance   (own systemd unit, socket,
      │                                           system user `archiveup`)
      │  upload → widened ilag_sync.upload() fields include md5Checksum →
      │  passed back in the response
      ▼
Google Drive — SomPong-LINE/<YYYY-MM>/<name>
      │
      ▼ (only once the filer's own md5 matches the broker's response)
filer deletes the staged copy + the outbox file(s), records the ledger entry
```

Only the broker process ever holds the Drive OAuth credential. The filer
never sees it, and never asks Drive "does this exist?" — the broker exposes
exactly one operation (`upload`, no list/read; enforced by
`scripts/test_drive_photo_broker.py`'s guard tests), so the filer's own local
ledger is the sole record of what has already been archived. If that ledger
is ever lost, the worst case is a harmless duplicate upload (same name/
content, new file id) on the next tick — never a lost upload, and never a
wrongly deleted local file, because deletion is gated on the ledger write
happening first.

## 3. Users, paths, sockets

| | user | holds | path/socket |
|---|---|---|---|
| filer | `root` | outbox read/delete, staged-copy write | `runners/sompong_archive_filer.py` |
| broker | `archiveup` (new) | Drive OAuth credential | `/run/archiveup/archive-broker.sock` |
| outbox | claudeflow-written, root-drained | `/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/data/sompong/archive-outbox` — reached via `SOMPONG_ARCHIVE_DATA_DIR` (the `data` dir, opened by path) then a fixed `sompong`/`archive-outbox` walk (each opened `O_DIRECTORY\|O_NOFOLLOW` by dir_fd), never the full path opened directly |
| staging | filer writes, broker reads | `/var/lib/archiveup/staging` |
| credential file | root-owned, mode `0640`, group `archiveup` | `/home/archiveup/.drive-archive.env` |

The filer runs as root for the identical reason `sompong_photo_filer.py`
does (§3 of `sompong-photos.md`): ClaudeFlow's container may write the
outbox as a uid the host has no other account for, and root can always read
it regardless of that file's owner. The broker stays unprivileged
(`archiveup`) — it is the only process holding the credential, and that
never changes.

This is a **third, independent instance** of `runners/drive_photo_broker.py`
— own unit (`mooniex-drive-archive-broker`), own socket, own staging dir, own
uid allowlist (`0`, the root filer), own fixed folder id. Its credential
file is root-owned mode `0640` (like `install-share-broker.sh`'s pattern,
copying only the three `GOOGLE_OAUTH_*` lines from an existing source file),
not broker-owned mode `600` like the photo/original brokers — the broker can
read it but not rewrite it. `scripts/install-archive-uploader.sh` hardcodes
all three existing brokers' unit/socket/folder constants and refuses to run
if any of its own would ever collide.

**No broker code change was needed for file types.** `drive_photo_broker.py`
was audited end to end (`_valid_name`, `resolve_staged_path`, `do_upload`) —
none of it gates on extension or mime type, so `.jsonl.gz`, audio, and
arbitrary media types upload through the existing broker unchanged. The one
broker-side change made is additive: `do_upload()`'s response now includes
`md5Checksum` (sourced from widening `ilag_sync.upload()`'s Drive `fields`
request param, no new API call), because the filer's verify-before-delete
step needs it and the broker exposes no list/read call to fetch it any other
way.

## 4. Why the local ledger, not a Drive query

The task's own "if `log-<M>.jsonl.gz` already exists, upload as `-partN`"
and "same name+md5 already on Drive counts as done" requirements would
normally call for asking Drive what's already there. The broker cannot
answer that — by design, it has no list/read operation, the same hard
invariant `drive_share_broker.py`'s and `drive_photo_broker.py`'s own test
suites enforce. Since this filer is the *only* writer into this Drive
folder, its own local ledger (`filed_logs.json` keyed by raw content
sha256 → `{name, month}`; `filed_media.json` keyed by the media file's
sha256 → `{msgid, month, bin_name}`; both beside the filer's state, written
only after a verified upload, before the local delete) is authoritative for
both questions: a duplicate skips straight to "already done, delete local,"
and a per-month part counter (`log_parts.json`) picks the next free `-partN`
without ever needing to list the Drive folder.

Keys are content sha256 plus the identifier the outbox already gives that
sha no right to collapse: `filed_logs.json` is keyed by `<month>:<raw
sha256>` → `{name, month}` (a second file for the same month with different
bytes is simply a different key); `filed_media.json` is keyed by
`<month>/<msgid>` → `{sha256, bin_uploaded, json_uploaded, msgid, month,
bin_name}`, with the sha stored as a value rather than as the key itself.
Two distinct messages that happen to carry identical bytes (the same photo
forwarded twice in a family group) get two ledger entries, not one, so the
second message's sidecar (who sent it, when) still reaches Drive instead of
being silently deleted as "already filed." "Already filed" for media means
same key AND same stored sha; a msgid that comes back with different bytes
than what the ledger recorded is treated as new. The two booleans also
survive a bin-succeeds/sidecar-fails split attempt: the next try only
re-uploads whichever half is still `false`, so a flaky sidecar upload never
gives Drive a second copy of the bin.

## 5. Failure behavior

- **Open month, or closed but modified in the last 24h** — skipped this
  tick, not counted against retries; ClaudeFlow may still be appending late
  rows right up to rollover.
- **md5 mismatch** (staged bytes vs. what Drive reports back) — local file
  kept, retried next tick, failcount bumped.
- **Broker unreachable** — same: kept, retried, failcount bumped.
- **`MAX_RETRIES` (default 5) exceeded** — moved to `<outbox>/failed/`
  (logs) or `<outbox>/failed/media/<month>/` (media pairs, both bin and
  sidecar together) for a human to inspect; stops retrying forever against a
  paid API. Every directory on that quarantine path is created with
  `os.mkdir(name, dir_fd=parent_fd)` (EEXIST ignored) and reopened
  `O_DIRECTORY | O_NOFOLLOW` relative to its parent, and the move itself
  uses `src_dir_fd=`/`dst_dir_fd=` — the outbox's own container controls
  every name under it, so a path-built `mkdir`/`rename` could otherwise be
  redirected through a planted symlink (e.g. `failed` → the filer's own
  state dir) into overwriting files outside the outbox entirely. If
  `failed` (or a level under it) turns out to be anything but a plain
  directory, quarantine is refused: logged, and the entry is left exactly
  where it was, never moved through the symlink.
- **A symlinked outbox path component** — only `DATA_DIR` (ClaudeFlow's
  `data` dir, the host bind-mount source the container cannot replace) is
  opened by path; the fixed relative walk below it (`sompong`, then
  `archive-outbox`) is opened `O_DIRECTORY | O_NOFOLLOW` relative to the
  previous fd. If either component is a symlink, the whole tick is refused
  (logged, skipped) rather than resolved.
- **Symlink, hardlink (`st_nlink != 1`), FIFO, or any non-regular file** in
  the outbox — every name the filer reads comes from a directory listing
  (never JSON content or a client string), then opened with
  `os.open(name, O_NOFOLLOW | O_NONBLOCK, dir_fd=parent_fd)` followed by
  `os.fstat(fd)`; anything that fails the regular-file/single-hardlink check
  is skipped and logged (file name + reason only), never opened by path a
  second time. This is the same TOCTOU-safe pattern `drive_share_broker.py`
  (main branch) uses, chosen over `sompong_photo_filer.py`'s older
  resolve-then-check guard because a month's log file can still be mid-append
  by another process while this filer is scanning the directory.
- **A late append between the upload and the delete** — right before
  unlinking an uploaded log, the filer re-opens the name `O_NOFOLLOW`,
  `fstat`s it, and compares `(st_ino, st_size, st_mtime_ns)` against the
  stat it read the content from. Any difference means ClaudeFlow appended
  late rows in that window (e.g. a silent group waking up and triggering
  its trim); the file is kept rather than deleted, and the rows it now
  holds go out as the next `-partN` on a later tick. The upload that just
  happened is still recorded in the ledger — it genuinely covers the bytes
  it uploaded, just not the ones appended afterward.
- **Duplicate content already in the ledger** — deleted locally without a
  second upload attempt (crash-recovery path: the process died after
  uploading but before deleting, or after deleting the outbox pair but a
  new copy of the same content reappeared).
- **Logs never carry chat content.** Every log line names a file, a month,
  a msgid, or a reason — never a row's or a sidecar's actual text/metadata
  content.

## 6. What this task does not do

- Does not deploy anything, ssh to Contabo, or run the install script.
- Does not touch `runners/drive_upload_broker.py`, `mooniex-drive-broker`,
  `runners/drive_share_broker.py`, or `mooniex-share-broker` in any way.
- Does not make ClaudeFlow write into `archive-outbox/` — that is
  `docs/sompong-ea-v2.md` in the ClaudeFlow repo, task-a6e06a3d, merged but
  not yet deployed. Until it ships, the outbox stays empty and both new
  services simply idle.
- Does not provision the Drive OAuth credential.
