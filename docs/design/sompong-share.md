# SomPong Drive SHARE broker

Status: **Built (broker + installer + tests), not deployed** · task-1c07d46b
(2026-09-26); credential and caller changed in task-e71026a4 (2026-10-27: no
env file, caller uid 0) · contract of record: org wiki
`mooniex:projects/sompong-ea.md` section D, ADR 0032 (its caller line still
says `sompong`: see §5)

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
SomPong's inbox (host process, root, no Drive credential of any kind)
      │  verifies + copies a file into the staging root under a name it
      │  controls, then sends one JSON line to the broker's socket
      ▼
/var/lib/sompong-share/staging/<...>   (dir root:shareup 2770; file owned by
      │                                 root, group shareup, 0640)
      ▼
runners/drive_share_broker.py's unix socket   (/run/mooniex-share-broker/broker.sock,
      │                                         host process, own systemd
      │                                         unit, own system user `shareup`)
      │  SO_PEERCRED uid check (uid 0 only) → path-in-staging-root check
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

## 4. The credential -- in Infisical, never in a file (CEO rule, task-e71026a4)

There is no credential file. `deploy/share-broker/mooniex-share-broker.service`
has root run `tools/infisical_setup.py run MoonieX-SomPong prod --as contabo
--path /drive-share`, which puts `GOOGLE_OAUTH_CLIENT_ID` /
`_CLIENT_SECRET` / `_REFRESH_TOKEN` in the environment of a process that
`setpriv` has already dropped to `shareup` (the Gmail broker's pattern,
`scripts/install-gmail-broker.sh`). The broker snapshots the three values at
startup, removes them from `os.environ`, and hands `ilag_sync` a loader that
returns the snapshot, so nothing is read from disk. With neither that nor the
legacy `DRIVE_SHARE_BROKER_ENV` file path, startup fails with a `ConfigError`
that names the missing keys, never values. The one-time import of the three
values into the `/drive-share` folder is a CEO-card step: see the header of
`scripts/install-share-broker.sh`.

## 5. Caller identity: root (task-e71026a4)

SomPong's inbox calls the broker as root, so the unit sets
`DRIVE_SHARE_BROKER_ALLOWED_UIDS=0` and the broker's staged-file owner check
(owner must equal the connecting uid) requires the staged file to be owned by
root. The staging directory is `root:shareup` mode `2770` (setgid, so staged
files keep group `shareup`) and the inbox must create each file `0640` so the
broker user can read it and unlink it. `sompong` needs no group membership
and the installer no longer adds it to `shareup`. The uid is set in the unit
(one `Environment=` line), never hard-coded in the broker module. The wiki
contract (section D) still names uid `sompong`: if the staging process turns
out to run as `sompong` (uid 994 on Contabo), change that one line to the
uid, put `sompong` in `shareup`, and stage files owned by `sompong`.

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
  touch the live Contabo box -- all out of scope for the build tasks, same as
  `docs/design/sompong-photos.md` §8; the PH does both on a CEO card.

## 7. Deploy steps on Contabo (not run by this task)

```bash
cd /opt/MoonieXHQ/Agents/Core   # a root-owned checkout; the installer refuses any other
git pull
sudo scripts/install-share-broker.sh install --dry-run   # review the steps + the rendered unit
# the one-time secret import (header of the script) on a CEO card, then:
sudo scripts/install-share-broker.sh install              # takes no credential file
```

Then verify:

```bash
sudo -u shareup test -r /var/lib/sompong-share/staging && echo OK
scripts/install-share-broker.sh status
```
