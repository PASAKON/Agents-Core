# SomPong Drive SHARE broker

Status: **Built (broker + installer + tests), not deployed** · task-1c07d46b
(2026-09-26) · contract of record: org wiki `mooniex:projects/sompong-ea.md`
section D, ADR 0032

## 1. Why

SomPong (the CEO's EA runner, `sompong` on Contabo) sometimes needs to hand
the CEO a link to a file -- something it downloaded, generated, or was asked
to file -- that he can open from LINE on his phone with no Google sign-in.
The CEO approved exactly one destination for this, 2026-09-26: `SomPong
Share/` at the Drive root, id `1Qn7B0e6Pa7y8gS5bjUfs-f5ewMIERUsR`, "anyone
with the link" view access. This is a narrow, explicit carve-out from the
`gdrive-filing` skill's hard rules -- it applies to this one feature and this
one folder only.

## 2. Shape

```
SomPong EA runner (host process, user sompong, no Drive credential of any kind)
      │  verifies + copies a file into the staging root under a name it
      │  controls, then sends one JSON line to the broker's socket
      ▼
/var/lib/sompong-share/staging/<...>   (owner sompong:shareup, mode 2770 dir
      │                                 / 0640 file)
      ▼
runners/drive_share_broker.py's unix socket   (/run/mooniex-share-broker/broker.sock,
      │                                         host process, own systemd
      │                                         unit, own system user `shareup`)
      │  SO_PEERCRED uid check (sompong only) → path-in-staging-root check
      │  → upload into the FIXED folder → set {type:anyone, role:reader} →
      │  re-read the file fresh (parents AND size) to verify → build the
      │  webViewLink → delete the staged copy (success or failure alike)
      ▼
Google Drive -- "SomPong Share/" / <filename>, publicly viewable by link
```

Only the broker process ever holds the Drive OAuth credential. The EA
runner never sees it -- same containment shape as
`runners/drive_upload_broker.py` and `runners/drive_photo_broker.py`, a
**third, independent instance** of that pattern, not a change to either:
separate systemd unit (`mooniex-share-broker`), separate socket
(`/run/mooniex-share-broker/broker.sock`), separate system user (`shareup`),
separate env var prefix (`DRIVE_SHARE_BROKER_*` / `DRIVE_SHARE_MAX_MB`), and
a separate fixed Drive folder (`SomPong Share/`, never `Desktop Cloud` or
`My Picture & Videos.`).

## 3. What this broker adds over its siblings: a public permission

Every share ends with exactly one permission set on the freshly uploaded
file: `{"type": "anyone", "role": "reader"}` -- fixed literal, never built
from anything in the client's request. That is the entire reason this
broker exists (a link the CEO can open on his phone with no sign-in), and it
is also why the destination is locked to one folder that holds nothing
else: a compromised request can, at worst, make one more file in `SomPong
Share/` public, never touch `Desktop Cloud`'s or `My Picture & Videos.`'s
contents, because the folder id is this process's own fixed constant, never
a request field (`test_drive_share_broker.py`'s
`test_client_supplied_folder_id_in_any_field_is_ignored_not_used`).

Order of operations, all of it or none of it: **upload → set the
anyone/reader permission → re-read the file fresh (parents AND size) to
verify it actually landed, public, in the right place → return its
`webViewLink` → delete the staged copy.** The staged copy is removed in a
`finally` on `ok:true` AND `ok:false` alike, so a share request never
leaves a second copy of a CEO file sitting on disk after the socket
round-trip ends, win or lose.

## 4. The credential file -- root-owned, not broker-owned (task instruction)

Unlike `drive_upload_broker.py`'s and `drive_photo_broker.py`'s credential
files (owned by the broker's own account, mode 600), this broker's env file
is written `root:shareup`, mode `0640` -- readable by the broker user, not
writable by it. The broker still reads it directly
(`DRIVE_SHARE_BROKER_ENV`, same override idiom the sibling brokers use); it
just can no longer rewrite its own credential file even if its own
unprivileged account were ever compromised.

## 5. Caller identity: `sompong`, not root

The two sibling brokers' host-side callers (the drive-broker's `secretary`,
the photo broker's filer, which runs as root -- see
`docs/design/sompong-photos.md` for that reasoning) differ from this one:
here the caller IS SomPong's own EA runner process, running as its own
`sompong` account (org wiki `mooniex:projects/sompong-ea.md`). The
installer resolves `sompong`'s uid at install time (`id -u sompong`) into
`DRIVE_SHARE_BROKER_ALLOWED_UIDS` -- never hard-coded in the broker module
itself -- and adds `sompong` to the broker's own group (`shareup`) so it can
reach the group-gated socket (`0660`) and write into the staging directory
it owns (`sompong:shareup`, mode `2770`; staged files `0640`).

## 6. What this broker does NOT do

- No delete, move, list, read, or any other Drive operation -- `"share"` is
  the only recognised `op`; anything else is refused before any Drive call
  (`test_drive_share_broker.py`'s grep-style source guard +
  `test_op_other_than_share_is_refused`).
- No per-month or per-caller subfolders -- one fixed folder, always.
- Never logs a filename, display name, file content, the Drive file id, or
  the resulting link -- only a reason (`handle_connection`'s `logger.info`
  / `logger.warning` calls carry `uid` and `error` only).
- Does not provision the Drive OAuth credential, run the install script, or
  touch the live Contabo box -- all out of scope for this task, same as
  `docs/design/sompong-photos.md` §8.

## 7. Deploy steps on Contabo (not run by this task)

```bash
cd /opt/MoonieXHQ/Agents/Core   # or wherever this repo lives on the box
git pull
sudo scripts/install-share-broker.sh install <path-to-an-existing-GOOGLE_OAUTH-env-file>
```

Then verify:

```bash
sudo -u shareup test -r /var/lib/sompong-share/staging && echo OK
systemctl is-active mooniex-share-broker
```
