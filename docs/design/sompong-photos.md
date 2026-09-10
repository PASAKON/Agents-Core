# SomPong family-photo backup to Drive

Status: **Implemented (broker + filer), claudeflow side pending** · task-a1c618db
(2026-09-10) · design of record: org wiki `mooniex:projects/sompong-line.md`
feature F2

## 1. Why

CEO 2026-09-10: "SomPong แอบเก็บรูป (เอาไว้เป็นความทรงจำ) ที่ทุกคนส่งมาในกลุ่ม
เสมอ รูปครอบครัว ไฟล์ครอบครัว ทุกอย่างที่โหลดได้ในนั้น เอาใส่ใน Google Drive" —
every photo/video/file the family sends into the LINE group SomPong sits in
should be quietly backed up to the CEO's Drive, automatically, no per-file
confirmation. The CEO approved a fixed destination, `My Picture & Videos.`
(Drive id `1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy`), split into month folders. This
is an explicit, narrow carve-out from the `gdrive-filing` skill's hard rules
1 ("ask before doing anything") and 3 ("never create a folder without
asking") — it applies to this one feature and this one folder only. Nothing
else about that skill changes.

Until this task, the wiki's own outbox contract said it plainly: "ไม่เก็บไบต์
ไม่โหลดไฟล์ (จนกว่าฟีเจอร์รูปเข้า Drive จะมา)" — no bytes kept, nothing
downloaded, until this feature existed. This document covers the half of it
that landed in this task: the broker and the host-side filer. The
claudeflow-side change (making the container actually write photo pairs into
the outbox) is a separate task.

## 2. The whole path

```
LINE group (family)
      │  photo/video attachment
      ▼
claudeflow container (Docker, on Contabo)
      │  writes <id>.bin (bytes) then, LAST + atomically, <id>.json (metadata)
      │  onto the shared volume — SEPARATE TASK, not built here
      ▼
/root/projects/mooniex-claudeflow/data/sompong/photos-outbox/   (host path,
      │                                     bind-mounted into the container
      │                                     at /app/data/sompong/photos-outbox)
      │
      │  polled every SOMPONG_PHOTO_FILER_POLL_SECONDS (default 60s)
      ▼
runners/sompong_photo_filer.py   (host process, NOT in Docker, no Drive
      │                            credential of any kind)
      │  verify sha256 → dedup against filed.json → month folder (Bangkok
      │  time) → build the Drive filename → ask the broker to upload
      ▼
runners/drive_photo_broker.py's unix socket   (host process, its own
      │                                         systemd unit, own system user)
      │  SO_PEERCRED uid check → path-in-staging-root check → resolve-or-
      │  create the month folder under the fixed root → upload → re-list
      │  the destination folder to verify → respond ok/error
      ▼
Google Drive — "My Picture & Videos." / YYYY-MM/ <filename>
```

Only the broker process ever holds the Drive OAuth credential. Neither the
claudeflow container nor the filer ever sees it.

## 3. Why the socket is not in the container

claudeflow runs in Docker. The obvious shortcut — mount the broker's unix
socket into the container so the bot can call it directly — was rejected on
purpose: a container compromise (a bad dependency, an RCE in whatever parses
an inbound LINE attachment, anything) would then be one hop from the CEO's
entire Drive-photo folder, and if the socket were EVER shared with the
existing `drive_upload_broker.py`, one hop from `Desktop Cloud` too. The
constraint carried into this design as two hard rules, both enforced in code
and in `scripts/install-photo-broker.sh`, not just by convention:

1. **The broker's socket is never mounted into the container.** The
   container's only interface to this feature is the filesystem — it writes
   files onto a bind-mounted volume claudeflow's compose already has
   (`./data:/app/data`) and does nothing else. It has no socket path, no
   broker address, no way to ask for an upload directly.
2. **Uid 0 is never added to the broker's allowlist**, on either side of the
   container boundary. Whatever uid the claudeflow container's process runs
   as (root-in-container is common for Node images unless a compose `user:`
   directive says otherwise) is irrelevant to the broker, because the
   container can never reach the socket at all — but even if some future
   change tried to change that, uid 0 must never appear in
   `DRIVE_PHOTO_BROKER_ALLOWED_UIDS`. The one uid on that list is the host
   filer service's own dedicated system user (`sompongphoto`), created by
   the install script specifically so it is never root.

The consequence: the container writes, a completely separate host process
(the filer) drains, and only the filer ever talks to the broker. A container
compromise can, at worst, write garbage files into the outbox — the filer's
sha256 verification and the JSON's fixed field set are what stand between
that and an actual Drive upload (see §6).

This is the same shape `drive_upload_broker.py` already uses for SomPong's
LINE-side commands (`secretary` user, unix socket, SO_PEERCRED, one fixed
folder) — see that module's own docstring for the fuller containment
argument. This feature is a **second, independent instance** of that
pattern, not a change to the first one: separate systemd units
(`mooniex-drive-photo-broker` / `mooniex-sompong-photo-filer` vs. the
existing `mooniex-drive-broker`), separate socket
(`/run/photoup/photo-broker.sock` vs. `/run/driveup/drive-broker.sock`),
separate system users (`photoup`/`sompongphoto` vs. `driveup`/`secretary`),
separate env var prefix (`DRIVE_PHOTO_BROKER_*` vs. `DRIVE_BROKER_*`), and a
separate fixed Drive folder (`My Picture & Videos.` vs. `Desktop Cloud`).
`scripts/install-photo-broker.sh` hardcodes the existing broker's constants
and refuses to run if any of its own would ever collide with them.

## 4. The outbox contract

For one attachment, claudeflow (separate task) writes two files sharing an
id, into `SOMPONG_PHOTO_OUTBOX` (default
`/root/projects/mooniex-claudeflow/data/sompong/photos-outbox`):

```
<id>.bin     raw bytes
<id>.json    {"groupId": "...", "messageId": "...", "userId": "...",
              "name": "...", "ts": 1788975600, "kind": "image",
              "mime": "image/jpeg", "ext": ".jpg", "sha256": "..."}
```

`<id>.bin` is written first, `<id>.json` **last and atomically** (write-tmp
+ rename). That ordering is the whole completeness contract: a directory
listing can only ever find a `.json` alongside its matching `.bin` for a
pair that finished writing. The filer scans for `*.json` — a `.bin` with no
`.json` yet is simply never enumerated (still being written, or the JSON
write hasn't landed), and if a `.json` somehow exists with no `.bin` (should
not happen given the ordering, but the filer treats it defensively) it is
skipped this tick rather than treated as an error, since a future tick may
find the `.bin` has since appeared. `ts` is a Unix epoch integer, the same
convention the wiki's own `log.jsonl` line shape already uses.

## 5. The `subfolder` validation — the one new attack surface

The broker's request shape gained exactly one new field beyond
`drive_upload_broker.py`'s `{"op", "path", "name"}`: `subfolder`. It exists
because the filer (which holds no Drive credential and cannot itself create
a Drive folder) needs the broker to resolve-or-create the month folder the
first time a given month is needed.

Because this is new capability, not just a new parameter name, it gets the
same design discipline the rest of the broker already uses — treat it as a
value, not a path:

```python
SUBFOLDER_RE = re.compile(r"^[0-9]{4}-[0-9]{2}$")
```

- **Explicit ASCII digit class, not `\d`.** Python's `\d` matches Unicode
  decimal digits under the default (non-`re.ASCII`) regex mode — e.g.
  U+0660 ARABIC-INDIC DIGIT ZERO — so a value built from those would still
  "look like a date" to a naive `\d{4}-\d{2}` pattern while being a
  different string than what a downstream `int()`/date parser expects.
  `[0-9]` matches only the literal ASCII characters, closing that gap.
- **`fullmatch`, fixed-width quantifiers.** No `..`, no `/`, no id-shaped
  string, no leading/trailing whitespace, and no length check needed
  separately — a 1000-character string simply fails to match a
  `{4}` / `{2}`-quantified pattern, so there's no separate cap to forget and
  no regex complex enough to worry about ReDoS.
- **Scope, not just shape.** Even a value that somehow passed the regex
  could only ever resolve or create a folder as a **direct child of the
  broker's own fixed `folder_id`** — the Drive query (`find_month_folder`)
  and the creation call (`create_month_folder`) both pin `parents`/`'...' in
  parents` to `cfg.folder_id`, which is never read from the request. There
  is no code path that lets a client walk to an arbitrary folder by
  supplying nested path segments, because `subfolder` is never treated as a
  path in the first place.
- **A request with no `subfolder` at all** uploads directly into the fixed
  folder, exactly like the sibling broker's only mode — this field is
  additive, not required.

`scripts/test_drive_photo_broker.py` exercises the reject table directly:
`../x`, `2026-9` (no zero-pad), `2026-09/x`, an id-looking string, Arabic-
Indic digit forms, an empty string, and a 1000-character string.

## 6. Verify-before-upload, dedup, and naming (filer side)

Per pair, oldest `ts` first:

1. **sha256 verify.** Recompute over the bytes, compare to the JSON's
   `sha256`. Mismatch (or a JSON that fails to parse, or is missing a
   required field) → both files move to `failed/` immediately — this is a
   hard quarantine, not a retry, since the bytes don't match what the pair
   claims and retrying changes nothing.
2. **Dedup.** `filed.json`, kept beside the outbox, maps
   `sha256 → {"name", "date"}`. A sha256 already present there (e.g. a
   retried webhook delivery re-wrote the same pair) is deleted locally
   without a second upload.
3. **Month folder.** `ts` (Unix epoch UTC) converted to Asia/Bangkok
   (`+07:00`, no DST) and formatted `YYYY-MM`. Bangkok is used because that
   is the timezone the whole CEO/family/business timeline runs on
   everywhere else in this org (LungNote deadlines, `logs.txt` timestamps,
   etc.) — a photo sent at 23:40 UTC on the 31st is already the 1st in
   Bangkok, and files under the Bangkok month, not the UTC one.
4. **Filename** — `gdrive-filing`'s parenthesised-fields style:
   `(<sender name>) (D-M-YYYY) (<HHMM>) <messageId><ext>`. The sender name
   comes from the JSON's `name` field, stripped of anything outside
   `[\w฀-๿ .()-]` (word characters — already Unicode-aware, so this covers
   Thai — plus the Thai Unicode block explicitly, space, dot, parens,
   hyphen). `D-M-YYYY` and `HHMM` are also Bangkok-local. `messageId` is
   appended raw, right before the extension, specifically so two photos
   sent in the same minute don't collide.
5. **Upload**, through the broker only. Only once it responds `ok: true`
   does the filer record the sha256 in `filed.json` (write-tmp + rename,
   atomic) and only then delete the local pair. If the process dies between
   those two writes, the next tick's dedup check (step 2) deletes the
   still-present local pair as a duplicate instead of re-uploading it or
   leaving it stranded — "never delete a file that hasn't been confirmed
   uploaded" holds across a crash, not just the happy path.
6. **Retry discipline**, same shape as `runners/secretary_waker.py`: a
   failed upload leaves both files exactly where they were and bumps a
   per-pair counter in `failcounts.json` (under the filer's own state dir,
   never inside the outbox); a pair that fails `MAX_RETRIES` (default 5)
   times in a row moves to `failed/` instead of retrying forever against a
   paid API.
7. **Single-flight**, a non-blocking `flock` — two ticks can never overlap,
   and one bad tick logs and sleeps rather than killing the loop.

## 7. Deploy steps on Contabo

Out of scope for this task: actually running these steps, and provisioning
the Drive OAuth credential itself. This section documents what a human does
once the code is deployed and this task is merged.

```bash
cd /root/projects/mooniex-agents   # or wherever this repo lives on the box
git pull
sudo scripts/install-photo-broker.sh install
```

This creates (idempotently — re-running is safe):

- system users `photoup` (broker) and `sompongphoto` (filer, added to the
  `photoup` group so it can reach the socket)
- the outbox directory if it doesn't already exist
  (`/root/projects/mooniex-claudeflow/data/sompong/photos-outbox`, owner
  `sompongphoto:photoup`, mode `2770`) — **if it already exists** (e.g. the
  claudeflow-side task created it first), the script leaves ownership/mode
  alone and prints what it found, since it may already hold live pairs
  written with different permissions
- two systemd units, `mooniex-drive-photo-broker` and
  `mooniex-sompong-photo-filer`, enabled and started

Then, **the one manual step this script deliberately does not do**: create
the broker's credential file by hand —

```
/home/photoup/.drive-photo.env      mode 600, owner photoup:photoup
    GOOGLE_OAUTH_CLIENT_ID=...
    GOOGLE_OAUTH_CLIENT_SECRET=...
    GOOGLE_OAUTH_REFRESH_TOKEN=...
```

The same OAuth app/Drive account the existing `drive_upload_broker.py`
already uses is fine to reuse here (same CEO, same Drive) — this is a
separate credential **file**, matching this broker's separate
`DRIVE_PHOTO_BROKER_ENV` variable, not a requirement for a different Google
Cloud project or refresh token. After creating it:

```bash
sudo systemctl restart mooniex-drive-photo-broker
journalctl -u mooniex-drive-photo-broker -f     # confirm it's listening, no config errors
journalctl -u mooniex-sompong-photo-filer -f    # confirm it's polling
```

**Known open dependency, claudeflow side:** the outbox directory lives under
`/root/projects/...`. If `/root` (or an intermediate directory) is not
traversable by `sompongphoto` — the common Linux default for `/root` is mode
`700`, which blocks every non-root user regardless of the leaf directory's
own permissions — the filer will never be able to read what claudeflow
writes there, no matter what this install script sets on the leaf directory
itself. `scripts/install-photo-broker.sh install` prints a one-line check
for this (`sudo -u sompongphoto test -r <outbox> && echo OK`) but does not
attempt to fix `/root`'s permissions itself, since loosening them is a
host-wide security decision outside this task's scope. Resolving it belongs
to the claudeflow-side task that actually makes the container write pairs
into this path.

## 8. What this task does not do

- Does not touch `runners/drive_upload_broker.py` or the `Desktop Cloud`
  target in any way.
- Does not make claudeflow write anything into the outbox — that container-
  side change is a separate task; until it ships, the outbox stays empty and
  both new services simply idle.
- Does not provision the Drive OAuth credential.
- Does not run the install script or touch the live Contabo box.
