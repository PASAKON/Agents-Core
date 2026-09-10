# SomPong family-photo backup to Drive

Status: **Implemented (broker + filer + staging bridge), claudeflow side
pending** · task-a1c618db (2026-09-10), root-filer fix task-4307c02c
(2026-09-10), staging-copy fix task-29744f52 (2026-09-10) · design of record:
org wiki `mooniex:projects/sompong-line.md` feature F2

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
      │                                     under /root, bind-mounted into
      │                                     the container at
      │                                     /app/data/sompong/photos-outbox)
      │
      │  polled every SOMPONG_PHOTO_FILER_POLL_SECONDS (default 60s)
      ▼
runners/sompong_photo_filer.py   (host process, NOT in Docker, runs as
      │                            root, no Drive credential of any kind)
      │  verify sha256 → dedup against filed.json → month folder (Bangkok
      │  time) → build the Drive filename → COPY the verified bytes into
      │  the staging root under a name this process controls (task-29744f52)
      ▼
/var/lib/photoup/staging/<sha256><ext>   (owner root:photoup, mode 2770 dir
      │                                    / 0640 file — OUTSIDE /root, so
      │                                    the broker can actually reach it)
      │
      ▼
runners/drive_photo_broker.py's unix socket   (host process, its own
      │                                         systemd unit, own system user
      │                                         `photoup`)
      │  SO_PEERCRED uid check → path-in-staging-root check (now the
      │  staging root above, never the outbox) → resolve-or-create the
      │  month folder under the fixed root → upload → re-list the
      │  destination folder to verify → respond ok/error
      ▼
Google Drive — "My Picture & Videos." / YYYY-MM/ <filename>
      │
      ▼ (only once the broker confirms ok: true)
filer deletes BOTH the staged copy and the outbox pair, records the sha256
```

Only the broker process ever holds the Drive OAuth credential. Neither the
claudeflow container, the filer, nor the staging copy in transit ever sees
it.

### Why a copy, not a shared mount or a loosened `/root` (task-29744f52)

The gap this fixes, measured on Contabo right after task-4307c02c's fix was
deployed: `mooniex-drive-photo-broker` still failed to start —
`DRIVE_PHOTO_BROKER_STAGING_ROOT does not exist:
/root/projects/mooniex-claudeflow/data/sompong/photos-outbox ([Errno 13]
Permission denied)` — because that variable pointed straight at the outbox,
and the outbox sits under `/root`, mode `0700`. Running the filer as root
(task-4307c02c) fixed the filer's own read of the outbox; it did nothing for
the broker, which is `photoup` — deliberately, since it holds the Drive
credential and must stay unprivileged — and therefore still cannot traverse
`/root` no matter what the outbox's leaf permissions say.

The filer is the only process that can see both sides of that wall (root on
one side, `photoup` on the other), so it becomes the bridge: it reads +
verifies a pair in the outbox as it always did, then copies the bytes into
`/var/lib/photoup/staging` — a directory that lives outside `/root` on
purpose, owned `root:photoup`, mode `2770` — before ever asking the broker
to upload. `DRIVE_PHOTO_BROKER_STAGING_ROOT` now points at that staging
directory, never at the outbox; the broker's existing "resolve first, then
check against the configured staging root" rule is unchanged, it is just
finally satisfiable.

Two alternatives were considered and rejected, for the same reasons
task-4307c02c's own §3 already gives for the filer's uid:

- **A shared bind mount / relocating the outbox so `photoup` can reach it
  directly.** This is the claudeflow-side move §7's "Known open dependency"
  used to point at — this task closes the gap from the host side instead,
  which needs no change on the claudeflow/container side at all — a
  coordinated change across two repos (this one and claudeflow's
  docker-compose) buys nothing over a same-host copy the filer can make on
  its own, today, without touching the container's mount contract.
- **Loosening `/root`'s permissions** (`chmod 711 /root`, or an ACL granting
  `photoup` traversal). Rejected for the identical reason task-4307c02c
  rejected it for the filer's own access: `/root` guards every credential
  file, systemd unit, and service user's home on the box behind that one
  `0700` bit — spending that boundary to save one `cp` is a bad trade.

The cost of the copy is a second, transient on-disk footprint per in-flight
photo — bounded by the free-space guard (`SOMPONG_PHOTO_MIN_FREE_MB`,
default 2048 MiB of headroom on top of the file's own size; a pair that
would breach it is skipped, not failed, and retried next tick) and by the
fact that the staged copy is removed immediately after every upload
attempt, success or failure — it never accumulates.

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
2. **The claudeflow container's uid must never appear in the broker's
   allowlist.** Whatever uid the container's process runs as (root-in-
   container is common for Node images unless a compose `user:` directive
   says otherwise) is irrelevant to the broker, because — per rule 1 above —
   the container can never reach the socket at all. That property does not
   depend on uid, and it is unaffected by uid 0 appearing in
   `DRIVE_PHOTO_BROKER_ALLOWED_UIDS` for a completely different reason (the
   host filer, next section).

### Why the host filer is allowed to run as root (task-4307c02c, 2026-09-10)

Measured on Contabo just after `install-photo-broker.sh install` first ran:
`/root` is mode `0700`, owned by `root`. No non-root uid can ever traverse
into it, no matter what the outbox's own leaf directory permissions say —
`sudo -u sompongphoto test -r <outbox>` failed even though the leaf itself
was group-writable to that user, and the broker's own `journalctl` showed
the identical failure (`DRIVE_PHOTO_BROKER_STAGING_ROOT does not exist ...
[Errno 13] Permission denied`) for the same reason. Both new units were
dead on arrival.

**The fix: `runners/sompong_photo_filer.py` runs as `root`, and `0` was
added to the photo broker's uid allowlist** (`DRIVE_PHOTO_BROKER_ALLOWED_UIDS`)
so the broker accepts the now-root filer's socket connection. That reads
like a weakening, so here is the reasoning, on the record, rather than left
implicit:

The property this broker exists to protect is **a compromise of the
claudeflow *container* must not reach the CEO's Drive.** That property is
unaffected by this change — the container still has no socket, no
credential, and no network path to either broker; it can only drop files
onto a disk it already writes to. **Host root is a different matter.** On
this box root already owns `/root/projects`, the credential files on disk,
systemd, and every service user (`photoup` included) — a host-root
compromise has the Drive regardless of which uid the filer runs as.
Spending a uid boundary that root can cross at will, in exchange for a
mount/permission puzzle across a `0700` home directory, buys nothing.

Rejected alternatives (recorded here so they are not re-litigated):

- **Moving the outbox to `/var/lib/...` plus a new bind mount in
  `docker-compose.webhook.yml`.** Works, but adds a mount and a second path
  convention to keep in sync across two repos (this one and claudeflow's)
  for no security gain over running the filer as root.
- **`chmod 711 /root` or an ACL granting a service user `x` on `/root`.**
  Loosens a directory that guards far more than this one feature — every
  credential file, systemd unit, and service user's home on the box sits
  behind that same `0700` bit.

**What this did NOT fix, at the time: the broker's own access.**
`runners/drive_photo_broker.py` keeps running as its own unprivileged
`photoup` user — it is the process that holds the Drive OAuth credential,
and that has not changed. `photoup` was therefore subject to the *exact
same* `/root` traversal block the filer used to hit: every upload the
broker is asked to perform requires it to `open()`/`stat()` the path it is
handed directly, and no uid-allowlist change touches that. Measured on
Contabo exactly as predicted: `mooniex-drive-photo-broker` failed to start
with `DRIVE_PHOTO_BROKER_STAGING_ROOT does not exist: .../photos-outbox
([Errno 13] Permission denied)` while `mooniex-sompong-photo-filer` ran
cleanly. **This residual gap is closed by task-29744f52** — see "Why a copy,
not a shared mount or a loosened `/root`" above: the broker is no longer
ever handed a path under `/root` at all, staged copies live in
`/var/lib/photoup/staging` instead. Verify with:
`sudo -u photoup test -r /var/lib/photoup/staging && echo OK`.

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
separate system users (`photoup`/root vs. `driveup`/`secretary` — the filer
ran as its own dedicated `sompongphoto` user until task-4307c02c moved it to
root, see §3),
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
5. **Free-space guard** (task-29744f52): before staging, check the staging
   filesystem has at least `SOMPONG_PHOTO_MIN_FREE_MB` (default 2048 MiB)
   free on top of the file's own size — the staged copy briefly doubles the
   file's on-disk footprint. Too little headroom skips the pair for this
   tick (logged, not quarantined, not counted against `MAX_RETRIES`) and it
   is retried next tick.
6. **Stage** (task-29744f52): copy the verified bytes into
   `DRIVE_PHOTO_BROKER_STAGING_ROOT` under `<sha256><ext>` — a name this
   process derives itself, never a name or path fragment taken from the
   message JSON — mode `0640`. This is the only directory the unprivileged
   broker can reach; see "Why a copy" in §2 above.
7. **Upload**, through the broker only, with the *staged* path — never the
   outbox path. Only once it responds `ok: true` does the filer record the
   sha256 in `filed.json` (write-tmp + rename, atomic) and only then delete
   the outbox pair. If the process dies between those two writes, the next
   tick's dedup check (step 2) deletes the still-present local pair as a
   duplicate instead of re-uploading it or leaving it stranded — "never
   delete a file that hasn't been confirmed uploaded" holds across a crash,
   not just the happy path. The staged copy itself is removed immediately
   after this step, success or failure — it never outlives one upload
   attempt, so a crash mid-tick can never leave a family photo sitting in a
   second place.
8. **Retry discipline**, same shape as `runners/secretary_waker.py`: a
   failed upload leaves both outbox files exactly where they were (the
   staged copy is still removed per step 7) and bumps a per-pair counter in
   `failcounts.json` (under the filer's own state dir, never inside the
   outbox); a pair that fails `MAX_RETRIES` (default 5) times in a row moves
   to `failed/` instead of retrying forever against a paid API.
9. **Single-flight**, a non-blocking `flock` — two ticks can never overlap,
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

- system user `photoup` (broker — holds the Drive credential, never root).
  The filer runs as `root` (task-4307c02c, see §3) and needs no dedicated
  system user of its own; re-running the script tears down the old
  `sompongphoto` account and its home dir if a prior install left one behind
  (and says so either way — removed, or already absent)
- the outbox directory if it doesn't already exist
  (`/root/projects/mooniex-claudeflow/data/sompong/photos-outbox`, owner
  `root:photoup`, mode `2770`) — **if it already exists** (e.g. the
  claudeflow-side task created it first), the script leaves ownership/mode
  alone and prints what it found, since it may already hold live pairs
  written with different permissions (it re-owns it from the now-removed
  `sompongphoto` to `root` if that is what it finds, without touching any
  pairs inside)
- the staging directory (`/var/lib/photoup/staging`, owner `root:photoup`,
  mode `2770`, task-29744f52) — unlike the outbox, always re-asserted on
  every run, since it holds nothing but transient in-flight copies
- two systemd units, `mooniex-drive-photo-broker` (now configured with
  `DRIVE_PHOTO_BROKER_STAGING_ROOT` pointed at the staging directory above,
  never the outbox) and `mooniex-sompong-photo-filer`, enabled and started

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

**Proof the staging fix actually closed the permission gap** (also printed
at the end of `install-photo-broker.sh install`):

```bash
sudo -u photoup test -r /var/lib/photoup/staging && echo OK
systemctl is-active mooniex-drive-photo-broker
systemctl is-active mooniex-sompong-photo-filer
```

Expect `OK` and `active` on all three — this is the check that used to fail
(see "Why a copy, not a shared mount or a loosened `/root`" in §3 above) and
now cannot, since `photoup` was never asked to traverse `/root` in the first
place.

**Resolved dependency (task-29744f52):** an earlier version of this
document tracked, here, an open dependency on a claudeflow-side change to
relocate the outbox out from under `/root` before the broker could start.
That dependency is now closed from the host side instead — the broker never
opens a path under `/root` at all, regardless of where claudeflow's outbox
ends up living. No claudeflow-side change is required for the broker to
work.

## 8. What this task does not do

- Does not touch `runners/drive_upload_broker.py` or the `Desktop Cloud`
  target in any way.
- Does not make claudeflow write anything into the outbox — that container-
  side change is a separate task; until it ships, the outbox stays empty and
  both new services simply idle.
- Does not provision the Drive OAuth credential.
- Does not run the install script or touch the live Contabo box.
