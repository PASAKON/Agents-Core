# Machine Contract — Contabo's Drive leg (`tools/drive_leg.py`)

Brief: `docs/ops/briefs/machine-contract-drive-leg.md` (ADR 0031 / IRON Sec58, Phase 1 items
"transcript archiver to the new path, Docker-volume backup job, Claude-Uploads"). Precedents:
`scripts/stream_backup_to_drive.py` (freeze -> tar -> rcat -> verify -> manifest -> delete-only-
unchanged shape), `claude-home/tools/prune_transcripts.py` (the Mac's transcript archiver --
this is its Contabo counterpart), `tools/work_archive.py` (manifest shape + "verified only after
both objects read back correctly").

Contabo holds no rclone and no Drive token, on purpose (gdrive-filing rule 6: the token stays
on winbox). Every byte this tool sends to Drive goes through
`scripts/rclone_via_winbox.sh <rclone args...>`, which runs winbox's rclone over ssh with
Contabo's own stdin/stdout — overridable with env `DRIVE_LEG_RCLONE` (tests point this at a
fake relay; a real `--dry-run` should be run with `DRIVE_LEG_RCLONE=/bin/false` so a bug that
skipped the dry-run guard fails loudly instead of silently reaching winbox). No verb here has
ever been run against the real relay — every verification below used either `--dry-run` or the
tests' fake relay; **the first real (non-dry-run) run of every verb is the CTO's**, not this
task's.

## What each verb does

| Verb | Source | Drive destination | Deletes locally? |
|---|---|---|---|
| `transcripts` | `$CLAUDE_CONFIG_DIR/projects/<slug>/<uuid>.jsonl` (+ sibling `<uuid>/` sub-agent dir) | `BACKUP/MoonieX HQ/Claude-Transcripts/contabo/<slug>/<day>.tar.gz` + `<day>.manifest.json` | Yes — only the files of a day that verified, only if unchanged since freeze |
| `restore-transcript <uuid-prefix>` | (reads back from Drive) | — | No (writes into `projects/<slug>/`) |
| `uploads` | `$CLAUDE_CONFIG_DIR/uploads/` | `BACKUP/MoonieX HQ/Claude-Uploads/contabo/<date>.tar` + manifest | Never |
| `docker-volumes` | Docker volumes `n8n_data`, `org-pgdata` | `BACKUP/MoonieX HQ/Docker-Volumes/contabo/<volume>/<date>.{tar,sql.gz}` + manifest | Never (nothing local to delete — both streams go straight from `docker`'s stdout to the relay) |
| `blueprints` | `state/<machine>-blueprint-<date>/` (git-tracked) | `BACKUP/MoonieX HQ/Machine-Blueprints/<machine>/<date>/<machine>-blueprint-<date>.tar` + manifest | Never (git is the primary copy; a local scratch tar it builds to compute a sha256 before upload is removed either way, regardless of outcome — that is disposal of our own temp copy, not of source data) |

Drive folder ids (gdrive-filing `SKILL.md` ID table, `BACKUP/MoonieX HQ/` family, CEO
2026-09-24 — not re-created here): family `1NqyT7TjUHVBuOCo0bw3dRy8niXLcLawK`,
Claude-Transcripts `1l5Up71pZWBHKwOQ5A6XNoKLYqICixyxP`, Claude-Uploads
`1t-5xXXx6VNP78Ewj1fd7mwcjk1oO_vyl`, Docker-Volumes `1bODM090gcAhlusA8g_6Jp-w_bzsDINwC`,
Machine-Blueprints `12yjlX_MvhjmJlwuhqFEqVFcQkNR0M7r0` (Work-Archive
`1xu8hXdUZGBino913lCr2zdUz8kTd8tqA` is listed in `tools/drive_leg.py`'s `FOLDER_IDS` for a
single source of truth alongside the rest, but no verb here uses it — that is
`tools/work_archive.py`'s job).

## The common core: `put()`

Every verb that uploads funnels through one function, `put(stream_fn, folder_id, remote_dir,
base_name, ext, manifest, ...)`: stream → `rclone rcat` through the relay (md5/sha256/size
computed on the fly from the bytes actually sent) → verify with `lsjson --hash` (size AND md5
must match) → fill the manifest's `bytes`/`md5`/`sha256`/`drive` fields → upload the manifest
beside the archive as `<base_name>.manifest.json` → verify that too → append one ledger line to
`$CLAUDE_CONFIG_DIR/logs/drive-archive.log` (pipe-separated: `ts | source | destination (id) |
n files | bytes | md5 | verify | OK | who`, the same shape as the log's existing lines). `put()`
raises `DriveLegError` on any mismatch or relay failure — always *before* the ledger line is
written — and never deletes anything itself; each verb performs its own delete step, strictly
after `put()` returns successfully.

Two deliberate departures from the brief's shorthand, both explained in `put()`'s own
docstring:
- The brief describes the core as `put(stream_fn, folder_id, remote_name, manifest)`. Here
  `remote_name` is split into `remote_dir` + `base_name` + `ext`, because the manifest's sibling
  filename (`<base_name>.manifest.json`) must be derivable, and the verify step needs to
  `lsjson` a *directory* (to read back one object's `Size`/`Hashes.md5` by name), not address a
  single file path directly.
- `org-pgdata`'s gzip step uses Python's stdlib `gzip` module (wrapping the upload sink) rather
  than piping through an external `gzip` binary — keeps the stdlib-only constraint and avoids a
  second subprocess in that pipeline.

`transcripts`, `docker-volumes` and `blueprints` each loop over multiple independent items
(days / volumes / blueprint dirs) and catch a failure **per item**, so one bad day/volume/dir
does not abort the others in the same run; the CLI's exit code reflects whether *any* item
failed. `uploads` and `restore-transcript` are single-item operations and let a failure
propagate to `main()`'s top-level handler.

## `uploads`' skip rule, precisely

The brief: "skip when the sha256 of the sorted (path, size, mtime) listing equals the last
ledger entry's." `drive-archive.log`'s shared 9-field shape has no field for that per-listing
fingerprint, so this is implemented with a small dedicated local index,
`$CLAUDE_CONFIG_DIR/logs/uploads-archive-index.jsonl` (one JSON row per run: `date`,
`listing_sha256`, `files`, `bytes`, `drive`), and "the last ledger entry" is that file's last
row. This is read-only and local, so `--dry-run` can correctly report "unchanged, would skip"
with zero relay calls. `blueprints`' "skip a dir whose tar sha256 is already in the ledger"
uses the analogous `blueprint-archive-index.jsonl`, and `transcripts`' restore path uses
`transcript-archive-index.jsonl` (uuid → slug/day/drive, so `restore-transcript` doesn't need a
Drive listing call in the common case — see fallback below).

## `restore-transcript`

Looks the uuid prefix up in the local `transcript-archive-index.jsonl` first. If that index is
missing or stale (e.g. rebuilt machine), it falls back to a recursive `lsjson` of the whole
Claude-Transcripts folder, downloading and reading each day's manifest via `cat` until a
matching uuid turns up — more expensive, only exercised when the fast path finds nothing.
Either way, it downloads the day's tar through the relay (`cat`), extracts *only* the matching
session's members (checked against path traversal, absolute paths and symlink/hardlink members
before extraction, plus the stdlib's own `filter="data"` extraction guard) into
`projects/<slug>/`, and refuses — raising, not silently skipping — if the uuid isn't found
inside that tar.

## Every delete path, and the verify that precedes it

`grep -n 'unlink\|rmtree\|remove(' tools/drive_leg.py` finds exactly two call sites (plus one
`rmdir()`, not matched by that pattern, at the same call site as the first):

1. **`_delete_verified()`** (`path.unlink()` + `d.rmdir()`) — the only place that deletes a
   caller's *source* data (a session's `.jsonl` and/or its sub-agent dir's files). Called from
   `transcripts()` exclusively inside the branch reached *after* `put(...)` has returned without
   raising — i.e., after the tar streamed, `lsjson --hash` confirmed the Drive object's size AND
   md5 match what was actually sent, the manifest uploaded and verified the same way, and the
   ledger line was appended. Even then, `_delete_verified()` re-`stat()`s every file and skips
   (never deletes) any whose size or `mtime_ns` no longer match what was frozen before the tar
   was built — a file touched during the upload window survives. `rmdir()` on a sub-agent
   directory only succeeds if it is actually empty (i.e., every file inside it was itself
   verified-unchanged and removed), so a directory with a surviving changed file is left in
   place.
2. **`tmp_path.unlink(missing_ok=True)`** in `blueprints()`'s `finally` block — deletes a
   scratch tarball `blueprints()` builds locally (via `tempfile.mkstemp`) purely to compute its
   sha256 before deciding whether to upload it. This is *our own* transient byte-copy, never a
   path under `state/<machine>-blueprint-<date>/` (the actual source directory is never opened
   for writing anywhere in this module) — it is removed unconditionally, on success, skip, or
   failure alike, because nothing downstream depends on that temp file surviving.

`uploads()` and `docker_volumes()` contain no delete calls at all, matching their "Never
deletes" verb descriptions in the brief.

## Contabo cron lines (INSTALLED 2026-09-24 by the CTO, staggered: docker-volumes Sun 02:30, uploads 03:00, transcripts 03:30 UTC — one relay stream at a time)

Modeled on `docs/ops/machine-contract-schedules.md`'s existing `machine_doctor.py` cron line
(same `.venv`, same log-redirection convention). All times UTC (Contabo's crontab convention).

```cron
# Claude Code transcripts -> Drive, weekly (archives every eligible day, min-age-days default 7)
30 3 * * 0 cd /opt/MoonieXHQ/Agents/Core && /opt/MoonieXHQ/Agents/Core/.venv/bin/python3 tools/drive_leg.py transcripts >> state/drive-leg.log 2>&1

# Chat uploads -> Drive, weekly (skips instantly when the folder hasn't changed)
0 3 * * 0 cd /opt/MoonieXHQ/Agents/Core && /opt/MoonieXHQ/Agents/Core/.venv/bin/python3 tools/drive_leg.py uploads >> state/drive-leg.log 2>&1

# n8n_data + org-pgdata -> Drive, weekly
0 3 * * 0 cd /opt/MoonieXHQ/Agents/Core && /opt/MoonieXHQ/Agents/Core/.venv/bin/python3 tools/drive_leg.py docker-volumes >> state/drive-leg.log 2>&1

# Blueprints -> Drive, run right after each capture (scripts/contabo_blueprint.sh), not on a
# fixed schedule -- add this line to the end of contabo_blueprint.sh's own wrapper instead of
# cron, or run it by hand immediately after a capture:
# /opt/MoonieXHQ/Agents/Core/.venv/bin/python3 tools/drive_leg.py blueprints
```

`state/drive-leg.log` is not tracked in git (matches `machine-doctor.log`'s CONFIG-class
treatment) — add a `.gitignore` line if it grows. `docker-volumes` and `blueprints` both need
`docker` CLI access and (for `org-pgdata`) a running `org-postgres` container reachable from
the box that installs the cron line — verify `docker exec org-postgres pg_dumpall -U org
| head -1` succeeds by hand before relying on the scheduled job.

## Before the first real (non-dry-run) run

- `DRIVE_LEG_RCLONE` must be unset (or point at the real
  `scripts/rclone_via_winbox.sh`) — every run in this task used either `--dry-run` or the
  tests' fake relay; nothing here has exercised the real winbox relay yet.
- `docker-volumes` needs real `docker` on the box, and for `org-pgdata` a reachable
  `org-postgres` container (override the name/user with `--pg-container`/`--pg-user` if they
  differ from the registry's assumed defaults).
- Run each verb once with `--dry-run` first (no flag needed to disable deletion — `--dry-run`
  itself guarantees zero relay calls and zero deletes) and read the printed `[n/N]` lines before
  the first real run, per this task's own verification below.

## Verification run for this task (2026-09-24, Contabo box)

```
.venv/bin/python -m pytest tests/test_drive_leg.py -q          # 18 passed (via the main
                                                                 # checkout's .venv -- this
                                                                 # worktree has none of its own)
DRIVE_LEG_RCLONE=/bin/false python3 tools/drive_leg.py transcripts --dry-run --max-days 3
DRIVE_LEG_RCLONE=/bin/false python3 tools/drive_leg.py docker-volumes --dry-run
DRIVE_LEG_RCLONE=/bin/false python3 tools/drive_leg.py blueprints --dry-run
DRIVE_LEG_RCLONE=/bin/false python3 tools/drive_leg.py uploads --dry-run
```

All four `--dry-run` invocations read this box's real `$CLAUDE_CONFIG_DIR` (`/root/.claude`)
and real `state/` dir, printed real counts (e.g. `blueprints` found the two real
`contabo-blueprint-20260924` / `winbox-blueprint-20260924` dirs; `uploads` found the real 14
files under `~/.claude/uploads`), exited 0, and — confirmed by `find /root/.claude
-newermt '...'` before/after — wrote nothing and deleted nothing.
