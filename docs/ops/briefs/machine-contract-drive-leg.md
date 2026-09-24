# Brief — Machine Contract, Drive leg for Contabo (`tools/drive_leg.py`)

Context: `docs/ops/machine-contract-plan-2026-09-24.md` (approved plan, phase 1 items "transcript
archiver to the new path, Docker-volume backup job, Claude-Uploads"), ADR 0031 / IRON §58 (copies under
`/opt/MoonieXHQ/Agents/Rules/`), registry `config/machine-contract.yaml`, Drive family definitions in
`.claude/skills/gdrive-filing/SKILL.md` (tree entry `BACKUP/MoonieX HQ/` and its ID-table row — the ids
are there), precedents `scripts/stream_backup_to_drive.py` (freeze → tar → rcat → verify → manifest →
delete; reuse its manifest shape and its "delete only unchanged files" rule) and
`claude-home/tools/prune_transcripts.py` (the Mac archiver; ours is the Contabo counterpart),
`tools/work_archive.py` (manifest + ledger precedent). Everything you write is English (IRON §56).

## How Contabo reaches Drive
Contabo has no rclone and no Drive token, on purpose (gdrive-filing rule 6: the token stays on winbox).
`scripts/rclone_via_winbox.sh <rclone args…>` runs winbox's rclone over ssh with THIS machine's
stdin/stdout, so `tar cf - … | scripts/rclone_via_winbox.sh rcat "gdrive:BACKUP/MoonieX HQ/…/x.tar"`
streams without a local copy, and `scripts/rclone_via_winbox.sh lsjson --hash "gdrive:…" ` reads
size + md5 back. The wrapper refuses args with spaces/quotes/`&|<>^` (cmd.exe), so address folders by
id: `--drive-root-folder-id <id>` with a remote path of `gdrive:<relative path with no spaces>`
(sub-folders `contabo/n8n_data/` etc. have no spaces; create them with `mkdir` through the same wrapper).
Compute md5 + sha256 + byte count on the Contabo side from the bytes you feed the pipe.

Drive ids (from the gdrive-filing ID table, do not re-create): family `1NqyT7TjUHVBuOCo0bw3dRy8niXLcLawK`;
`Claude-Transcripts` `1l5Up71pZWBHKwOQ5A6XNoKLYqICixyxP`; `Claude-Uploads` `1t-5xXXx6VNP78Ewj1fd7mwcjk1oO_vyl`;
`Work-Archive` `1xu8hXdUZGBino913lCr2zdUz8kTd8tqA`; `Docker-Volumes` `1bODM090gcAhlusA8g_6Jp-w_bzsDINwC`;
`Machine-Blueprints` `12yjlX_MvhjmJlwuhqFEqVFcQkNR0M7r0`.

## Deliverable: `tools/drive_leg.py` (stdlib only, Python 3.12) + `tests/test_drive_leg.py` + `docs/ops/machine-contract-drive-leg.md`

Common core: `put(stream_fn, folder_id, remote_name, manifest)` → tar/gz streamed to rcat, md5/sha256/size
computed on the fly, `lsjson --hash` read-back must match size AND md5, manifest uploaded beside it and
read back too, one ledger line appended to `$CLAUDE_CONFIG_DIR/logs/drive-archive.log` (same pipe-separated
shape as the existing lines there: ts | source | destination (id) | n files | bytes | md5 | verify | OK |
who), and ONLY then any local delete. The relay command is `scripts/rclone_via_winbox.sh` resolved from the
repo root, overridable with env `DRIVE_LEG_RCLONE` (the tests point it at a fake script that stores the
stream in a temp dir and answers `lsjson --hash` from it). `--dry-run` everywhere prints what would be
streamed (names, counts, bytes) and never calls the relay. Every verb prints `[n/N] <step>` lines and exits
non-zero on any mismatch, leaving local files untouched.

Verbs:
1. `transcripts` — `$CLAUDE_CONFIG_DIR/projects/<slug>/<uuid>.jsonl` (+ the sibling `<uuid>/` dir when it
   exists, sub-agent transcripts) grouped by (slug, local date of the file's mtime); a day is eligible when
   every session in it is older than `--min-age-days` (default 7). Per (slug, day): `<YYYY-MM-DD>.tar.gz`
   streamed to `Claude-Transcripts/contabo/<slug>/` + `<YYYY-MM-DD>.manifest.json` listing every uuid with
   size, mtime, sha256. Also append each uuid → (slug, day, drive id) to a local index
   `$CLAUDE_CONFIG_DIR/logs/transcript-archive-index.jsonl`. Delete the local files only after verify and
   only if their size+mtime are unchanged since the freeze. Never touch a file younger than the threshold.
   `--only-slug`, `--max-days N` (stop after N day-tars, for a first controlled run), `--dry-run`.
2. `restore-transcript <uuid-prefix>` — find the day tar via the local index (fallback: `lsjson` the slug
   folders and read manifests), download through the relay (`cat` verb of rclone), extract only that
   session back into `projects/<slug>/`, refuse unsafe tar members.
3. `uploads` — `$CLAUDE_CONFIG_DIR/uploads/` → `Claude-Uploads/contabo/<YYYY-MM-DD>.tar` + manifest, skip
   when the sha256 of the sorted (path,size,mtime) listing equals the last ledger entry's. Never deletes.
4. `docker-volumes` — for each volume listed in `--volumes` (default `n8n_data,org-pgdata`):
   `n8n_data` → `docker run --rm -v n8n_data:/v:ro alpine tar cf - --exclude=./config -C /v .` streamed as
   `Docker-Volumes/contabo/n8n_data/<YYYY-MM-DD>.tar` (the `config` file holds n8n's encryptionKey — a
   secret — so it is EXCLUDED; the manifest carries `"excluded": ["config (n8n encryptionKey; restore it from
   the secrets bundle, see registry row)"]`); `org-pgdata` → `docker exec org-postgres pg_dumpall -U postgres
   | gzip` as `Docker-Volumes/contabo/org-pgdata/<YYYY-MM-DD>.sql.gz` (container name and user via
   `--pg-container/--pg-user`). Never deletes anything local. `--dry-run` prints the docker commands.
5. `blueprints` — `state/<machine>-blueprint-<date>/` dirs (default: every one present in `state/`) →
   `Machine-Blueprints/<machine>/<date>/<machine>-blueprint-<date>.tar` + manifest; skip a dir whose tar
   sha256 is already in the ledger. Never deletes (git is the primary copy).

Manifest shape (JSON): `{name, created, machine: "contabo", source, files: [{path, size, mtime_ns, sha256}],
count, bytes, md5, sha256, drive: {folder_id, remote_path}, restore: "<one line>", excluded: [...]}`.

Tests (`tests/test_drive_leg.py`, pytest, no network, no docker): the fake relay; a temp
`CLAUDE_CONFIG_DIR` with three slugs, sessions at ages 1/8/30 days, one with a sub-agent dir → `transcripts`
archives exactly the eligible days, manifest lists the uuids, local files deleted only for verified days;
a fake relay that returns a wrong md5 → exit non-zero and nothing deleted; `uploads` skips on an unchanged
listing; `restore-transcript` puts the session back byte-identical; `--dry-run` calls the relay zero times.

`docs/ops/machine-contract-drive-leg.md`: what each verb does, the Drive paths, the proposed Contabo cron
lines (transcripts weekly Sun 03:30 UTC, uploads weekly, docker-volumes weekly Sun 03:00 UTC, blueprints
after each capture) — write them, do not install them; the first real run of each verb is the CTO's.

## Verification to paste into your report
- `.venv/bin/python -m pytest tests/test_drive_leg.py -q` (or `python3`)
- `python3 tools/drive_leg.py transcripts --dry-run --max-days 3` on this box (prints eligible days/bytes,
  relay never called — confirm with `DRIVE_LEG_RCLONE=/bin/false`)
- `python3 tools/drive_leg.py docker-volumes --dry-run` and `blueprints --dry-run` and `uploads --dry-run`
- `grep -c 'delete' tools/drive_leg.py` and a one-paragraph statement of every code path that deletes and
  the verify that precedes it.

## Not in scope / must not
No real uploads or relay calls (the CTO runs the first ones); no docker commands outside `--dry-run`;
no deletes on this box; no secrets read or printed (never open `.credentials.json`, `.env*`, the n8n
`config` file, `rclone.conf`); no edits to the registry (propose rows in the report); no `cd` in compound
shell commands (a hook blocks it — use absolute paths); no file over 1 MiB in the worktree.
