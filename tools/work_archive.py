"""Cold-archive step for Work/<task_id>/ — Work/RULES.md rule 6, ADR 0030
(task-abc20690).

tools/workdir.py close() leaves in/ files with no SOURCES.txt line and out/
files with no filed home as "unfiled" and keeps the folder. This module is
the missing step: tar them, write a manifest, upload both to Google Drive
`BACKUP/`, verify by md5, and only report `verified: True` on a match. It
never deletes anything itself — tools/workdir.py close() deletes the source
files, and only after `verified` comes back True.

Upload transport (rewritten in iteration 1 — CTO reopen 2026-09-23):
`_default_uploader` speaks the Drive REST v3 *resumable* upload protocol
itself, streaming the file in fixed-size chunks so a multi-GB tar never sits
in RAM. Two things it deliberately does NOT do, both rejected in review:

- **Never writes into the Google-Drive-for-Desktop mount.** That mount
  (`claude-home/tools/prune_transcripts.py:54` DRIVE_ROOT) keeps a full LOCAL
  copy of anything written under it — the disk-hygiene skill's own 2026-09-23
  field note found this refills the Mac instead of freeing it, which defeats
  the entire point of this archive step.
- **Never calls `scripts/gdrive-bridge/ilag_sync.py`'s `upload()`**
  (`:182-209`) — it does `local_path.read_bytes()`, the whole file in memory,
  which would swap an 8 GB Mac to death on a multi-GB tar.

The only piece reused from `ilag_sync.py` is its OAuth helper,
`access_token()` (`:100-117`, itself built on `_load_oauth()` at `:72-98`) —
imported, never edited, exactly as instructed. Everything else here (the
resumable session init, the chunked `PUT` loop, 308 handling) is written in
this module because nothing chunked already existed to reuse.

`uploader` is the test seam on `archive()`: production callers leave it
`None` and get `_default_uploader`. `_default_uploader` itself takes an
`opener` seam (the raw HTTP call) so its resumable-chunking logic is testable
without a socket. Neither is ever exercised against the real Drive by this
module's tests or by a dry_run archive.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import mimetypes
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Callable

from tools import workdir

ROOT = Path(__file__).resolve().parent.parent

# claude-home/tools/prune_transcripts.py:52 — same log, same append-only shape.
LOG_PATH = os.path.expanduser("~/.claude/logs/drive-archive.log")

# gdrive-filing skill: the first Work/ archive (task-abc20690's brief) landed at the Drive `BACKUP` root;
# since 2026-09-24 the family below is the home (ADR 0031 Machine Contract).
# BACKUP/MoonieX HQ/Work-Archive (gdrive-filing ID table, created 2026-09-24) — new Agents-Work-<task>-<date>.tar land here;
# the 2026-09-23 one at the BACKUP root (1vU9GvMZdMXUV60_kTIkMR1aTwZcEHdlq) moves server-side on the CEO's yes.
BACKUP_FOLDER_ID = "1xu8hXdUZGBino913lCr2zdUz8kTd8tqA"

DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"

# Drive requires chunk sizes to be a multiple of 256 KiB; 8 MiB keeps a
# multi-GB tar's peak memory at one chunk, never the whole file.
CHUNK_SIZE = 8 * 1024 * 1024

Uploader = Callable[[Path, str], dict]
# opener(method, url, *, headers, body) -> (status, response_headers, response_body)
Opener = Callable[..., tuple[int, dict, bytes]]


def _hash_file(path: Path) -> tuple[str, str]:
    sha256, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha256.update(chunk)
            md5.update(chunk)
    return sha256.hexdigest(), md5.hexdigest()


def _header(headers: dict, name: str) -> str | None:
    name = name.lower()
    for k, v in headers.items():
        if k.lower() == name:
            return v
    return None


def _http(method: str, url: str, *, headers: dict | None = None,
          body: bytes | None = None, timeout: int = 300) -> tuple[int, dict, bytes]:
    """Bare HTTP/1.1 request via http.client -- no automatic redirect-
    following, so Drive's 308 Resume Incomplete comes back as an ordinary
    response instead of being chased or raised as an error. Real (non-test)
    opener; tests always inject their own."""
    parsed = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout)
    try:
        path = parsed.path + (("?" + parsed.query) if parsed.query else "")
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        resp_body = resp.read()
        return resp.status, dict(resp.getheaders()), resp_body
    finally:
        conn.close()


def _access_token() -> str:
    """The bridge's OAuth helper, imported and reused as-is -- never its
    upload() (reads the whole file into RAM) and ilag_sync.py itself is
    never edited."""
    bridge_dir = str(ROOT / "scripts" / "gdrive-bridge")
    if bridge_dir not in sys.path:
        sys.path.insert(0, bridge_dir)
    import ilag_sync  # noqa: E402 — access_token() only
    return ilag_sync.access_token()


def _init_resumable_session(opener: Opener, token: str, name: str, mime: str, size: int) -> str:
    url = DRIVE_UPLOAD + "?" + urllib.parse.urlencode({
        "uploadType": "resumable",
        "fields": "id,name,size,md5Checksum",
    })
    body = json.dumps({"name": name, "parents": [BACKUP_FOLDER_ID]}).encode()
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": mime,
        "X-Upload-Content-Length": str(size),
    }
    status, resp_headers, _ = opener("POST", url, headers=headers, body=body)
    if status not in (200, 201):
        raise RuntimeError(f"resumable session init failed: status={status}")
    location = _header(resp_headers, "Location")
    if not location:
        raise RuntimeError("resumable session init returned no Location header")
    return location


def _upload_chunks(opener: Opener, session_url: str, local_path: Path, size: int) -> dict:
    """PUTs `local_path` to `session_url` in <=CHUNK_SIZE reads, seeking to
    the server-confirmed offset after every 308 -- never the whole file in
    one call."""
    sent = 0
    with local_path.open("rb") as fh:
        while sent < size:
            fh.seek(sent)
            chunk = fh.read(min(CHUNK_SIZE, size - sent))
            if not chunk:
                raise RuntimeError(f"short read at offset {sent} of {size}")
            end = sent + len(chunk) - 1
            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {sent}-{end}/{size}",
            }
            status, resp_headers, body = opener("PUT", session_url, headers=headers, body=chunk)
            if status in (200, 201):
                return json.loads(body)
            if status == 308:
                range_header = _header(resp_headers, "Range")
                sent = int(range_header.rsplit("-", 1)[-1]) + 1 if range_header else end + 1
                continue
            raise RuntimeError(f"chunk upload failed: status={status} body={body[:300]!r}")
    raise RuntimeError("resumable upload read the whole file with no 200/201 response")


def _get_file_metadata(opener: Opener, token: str, file_id: str) -> dict:
    url = f"{DRIVE_FILES}/{file_id}?" + urllib.parse.urlencode(
        {"fields": "id,name,size,md5Checksum"})
    status, _, body = opener("GET", url, headers={"Authorization": "Bearer " + token})
    if status != 200:
        raise RuntimeError(f"metadata fetch failed: status={status}")
    return json.loads(body)


def _default_uploader(local_path: Path, dest_name: str, *, opener: Opener | None = None) -> dict:
    """Chunked Drive REST resumable upload -- see module docstring for why
    this exists instead of the Drive-mount copy or ilag_sync.py's upload().
    Never called by this module's tests or by a dry_run archive."""
    opener = opener or _http
    token = _access_token()
    size = local_path.stat().st_size
    mime = mimetypes.guess_type(dest_name)[0] or "application/octet-stream"

    session_url = _init_resumable_session(opener, token, dest_name, mime, size)
    meta = _upload_chunks(opener, session_url, local_path, size)
    if not meta.get("md5Checksum"):
        meta = _get_file_metadata(opener, token, meta["id"])
    return meta


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
