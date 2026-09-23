"""Cold-archive step for Work/<task_id>/ — Work/RULES.md rule 6, ADR 0030
(task-abc20690).

tools/workdir.py close() leaves in/ files with no SOURCES.txt line and out/
files with no filed home as "unfiled" and keeps the folder. This module is
the missing step: tar them, write a manifest, upload both to Google Drive
`BACKUP/`, verify by md5, and only report `verified: True` on a match. It
never deletes anything itself — tools/workdir.py close() deletes the source
files, and only after `verified` comes back True.

Transport is reused, not invented, from two places already in this repo:

- The copy-into-Drive step is the same one
  ~/.claude/tools/prune_transcripts.py's --archive uses: writing straight
  into the locally-synced "My Drive" folder (`claude-home/tools/
  prune_transcripts.py:54` DRIVE_ROOT; its `archive_session()` at
  `:279-296` does nothing more than `tarfile.open()` a path under that
  folder — there is no separate upload call, Google Drive for Desktop syncs
  the write on its own).
- Reading the md5 back from Drive reuses the OAuth + Drive REST helpers
  `scripts/gdrive-bridge/ilag_sync.py` already holds (`_load_oauth`/
  `access_token`/`api` at `:72-130`, the same `DRIVE_FILES` constant its
  `upload()` uses at `:182-209`) — the exact mechanism the
  `Agents-worktrees-<date>.tar` BACKUP-root precedent used
  (`claude-home/tools/drive-archive-gate.md:44`, "read back size,
  md5Checksum" — and the matching verified log lines in
  `~/.claude/logs/drive-archive.log`, e.g. the 2026-09-19T02:46:31 pair for
  `Agents-worktrees-untracked-2026-09-19.tar` + its manifest).

`uploader` is the test seam: production callers leave it `None` and get
`_default_uploader` (the two pieces above); tests inject a fake so nothing
here ever touches the real Drive.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable

from tools import workdir

ROOT = Path(__file__).resolve().parent.parent

# claude-home/tools/prune_transcripts.py:52 — same log, same append-only shape.
LOG_PATH = os.path.expanduser("~/.claude/logs/drive-archive.log")

# claude-home/tools/prune_transcripts.py:54 — the Mac-side Drive mount
# prune_transcripts.py --archive writes into. Reused verbatim as the
# transport; only the destination sub-folder (BACKUP/ instead of
# Claude-Transcripts/) differs.
DRIVE_ROOT = "/Users/gob/Library/CloudStorage/GoogleDrive-pass.gob1@gmail.com/ไดรฟ์ของฉัน"

# gdrive-filing skill: Drive `BACKUP` root, where this precedent's tars land
# directly (no sub-folder), per task-abc20690's brief.
BACKUP_FOLDER_ID = "1vU9GvMZdMXUV60_kTIkMR1aTwZcEHdlq"

Uploader = Callable[[Path, str], dict]


def _hash_file(path: Path) -> tuple[str, str]:
    sha256, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha256.update(chunk)
            md5.update(chunk)
    return sha256.hexdigest(), md5.hexdigest()


def _default_uploader(local_path: Path, dest_name: str) -> dict:
    """Copy into the Drive-mounted BACKUP/ folder (prune_transcripts.py's own
    transport, see module docstring), then read the md5Checksum back via the
    Drive REST API using scripts/gdrive-bridge/ilag_sync.py's existing OAuth
    helpers. Never called by this module's tests or by dry_run archives."""
    dest = Path(DRIVE_ROOT) / "BACKUP" / dest_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_path, dest)

    bridge_dir = str(ROOT / "scripts" / "gdrive-bridge")
    if bridge_dir not in sys.path:
        sys.path.insert(0, bridge_dir)
    import ilag_sync  # noqa: E402 — existing OAuth/Drive-API helpers, not a new transport

    resp = ilag_sync.api(
        ilag_sync.DRIVE_FILES,
        params={
            "q": f"name = '{dest_name}' and '{BACKUP_FOLDER_ID}' in parents and trashed = false",
            "fields": "files(id,name,md5Checksum,size)",
        },
    )
    files = resp.get("files") or []
    if not files:
        raise RuntimeError(f"{dest_name} not found under Drive BACKUP/ after copy (sync pending?)")
    return files[0]


def _log(line: str) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def archive(task_id: str, paths: list[str], *, root: str | Path | None = None,
            dry_run: bool = True, uploader: Uploader | None = None) -> dict:
    """Tar `paths` (posix, relative to Work/<task_id>/) into one
    `Agents-Work-<task_id>-<YYYY-MM-DD>.tar` + `.manifest.json`, upload both,
    verify each by md5. Returns `verified: True` only when every uploaded
    file's Drive `md5Checksum` matches its local md5 — a mismatch, an upload
    error, or `dry_run=True` all come back `verified: False` with the local
    tar/manifest left on disk (never deleted here; only cleaned up after a
    verified upload)."""
    if not paths:
        raise ValueError("archive() needs at least one path")

    folder = workdir.folder_path(task_id, root=root)
    if not folder.is_dir():
        raise FileNotFoundError(f"no such Work folder: {folder}")

    date_tag = datetime.now().strftime("%Y-%m-%d")
    tar_name = f"Agents-Work-{task_id}-{date_tag}.tar"
    manifest_name = tar_name + ".manifest.json"

    scratch = Path(tempfile.mkdtemp(prefix="work-archive-"))
    tar_path = scratch / tar_name
    manifest_path = scratch / manifest_name

    with tarfile.open(tar_path, "w") as tf:
        for rel in paths:
            tf.add(folder / rel, arcname=rel)

    tar_sha256, tar_md5 = _hash_file(tar_path)
    tar_bytes = tar_path.stat().st_size
    manifest = {
        "task": task_id,
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "files": len(paths),
        "bytes": tar_bytes,
        "sha256": tar_sha256,
        "md5": tar_md5,
        "sources": list(paths),
        "restore": f"mkdir -p {folder} && tar xf {tar_name} -C {folder}",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    manifest_sha256, manifest_md5 = _hash_file(manifest_path)

    result = {
        "task": task_id,
        "dry_run": dry_run,
        "verified": False,
        "tar_path": str(tar_path),
        "manifest_path": str(manifest_path),
        "dest": tar_name,
        "md5": tar_md5,
        "sha256": tar_sha256,
        "bytes": tar_bytes,
        "files": len(paths),
        "error": None,
    }
    if dry_run:
        return result

    upload = uploader or _default_uploader
    try:
        tar_meta = upload(tar_path, tar_name)
        manifest_meta = upload(manifest_path, manifest_name)
    except Exception as exc:
        result["error"] = f"upload failed: {exc}"
        return result

    tar_drive_md5 = tar_meta.get("md5Checksum")
    manifest_drive_md5 = manifest_meta.get("md5Checksum")
    verified = tar_drive_md5 == tar_md5 and manifest_drive_md5 == manifest_md5
    result["verified"] = verified
    if not verified:
        result["error"] = (
            f"md5 mismatch: tar local={tar_md5} drive={tar_drive_md5}; "
            f"manifest local={manifest_md5} drive={manifest_drive_md5}"
        )
        return result

    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    _log(f"{ts} | {tar_path} | BACKUP/{tar_name} | 1 file | {tar_bytes} B | "
         f"md5 {tar_md5} | drive md5 {tar_drive_md5} | verified | id {tar_meta.get('id', '')}")
    _log(f"{ts} | {manifest_path} | BACKUP/{manifest_name} | 1 file | "
         f"{manifest_path.stat().st_size} B | md5 {manifest_md5} | drive md5 {manifest_drive_md5} "
         f"| verified | id {manifest_meta.get('id', '')}")

    shutil.rmtree(scratch, ignore_errors=True)
    return result
