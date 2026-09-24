#!/usr/bin/env python3
"""tools/drive_leg.py -- Contabo's Drive leg of the Machine Contract (ADR 0031, IRON Sec58).

Brief: docs/ops/briefs/machine-contract-drive-leg.md. Contabo holds no rclone and no Drive
token on purpose (gdrive-filing rule 6: the token stays on winbox), so every byte this module
sends to Drive goes through `scripts/rclone_via_winbox.sh <rclone args...>`, which runs
winbox's rclone over ssh with THIS machine's stdin/stdout -- overridable with env
DRIVE_LEG_RCLONE (the tests point it at a fake relay script). The wrapper refuses any arg
with a space/quote/&|<>^ (cmd.exe), so every remote path used here is `gdrive:<folder>/<name>`
with no spaces, addressed by `--drive-root-folder-id <id>` (the six BACKUP/MoonieX HQ family
ids below, from the gdrive-filing skill's ID table -- never re-created here).

Precedents reused, not reinvented:
  - scripts/stream_backup_to_drive.py  -- freeze -> tar -> rcat -> verify (size+md5) -> manifest
    -> only-then-delete shape; its Sink/Drive.stat()/delete_frozen() patterns are mirrored below
    as _Sink / _lsjson / _delete_verified.
  - claude-home/tools/prune_transcripts.py -- the Mac's transcript archiver; `transcripts` here
    is its Contabo counterpart (session = <slug>/<uuid>.jsonl + sibling <uuid>/ dir), but this
    one archives to Drive instead of a mounted folder, and groups by day (Contabo alone has
    ~5,900 session files -- per-file objects would be thousands of Drive calls per run).
  - tools/work_archive.py -- manifest shape (name/created/files/count/bytes/md5/sha256/restore)
    and the "verified only after both the tar AND the manifest read back correctly" rule.

Five verbs (`transcripts`, `restore-transcript`, `uploads`, `docker-volumes`, `blueprints`) all
funnel through one core, `put()`: stream -> rcat -> verify by `lsjson --hash` (size AND md5) ->
upload the manifest beside it -> verify that too -> append one ledger line to
`$CLAUDE_CONFIG_DIR/logs/drive-archive.log`. `put()` NEVER deletes anything -- it raises
DriveLegError on any mismatch, before anything is logged, so a caller that only deletes local
files after a successful `put()` return can never delete on a failure. Every verb owns its own
delete step (most never delete at all -- see each verb's docstring and the brief).

`--dry-run` on every verb prints what would be streamed and calls the relay zero times.
`class_dir`/`rclone` are always explicit function parameters (never read from a module-global
cache), so tests never depend on process-wide monkeypatching of env vars for the data path --
only `DRIVE_LEG_RCLONE` (read by the relay-launching code) and the fake relay's own
FAKE_RELAY_STORE need an env var at all.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RCLONE = ROOT / "scripts" / "rclone_via_winbox.sh"

# Drive ids for the BACKUP/MoonieX HQ family (gdrive-filing SKILL.md ID table, CEO 2026-09-24).
# "family" and "Work-Archive" are listed for a single source of truth alongside the rest, even
# though no verb here uses them directly -- Work-Archive is tools/work_archive.py's job.
FOLDER_IDS = {
    "family": "1NqyT7TjUHVBuOCo0bw3dRy8niXLcLawK",
    "Claude-Transcripts": "1l5Up71pZWBHKwOQ5A6XNoKLYqICixyxP",
    "Claude-Uploads": "1t-5xXXx6VNP78Ewj1fd7mwcjk1oO_vyl",
    "Work-Archive": "1xu8hXdUZGBino913lCr2zdUz8kTd8tqA",
    "Docker-Volumes": "1bODM090gcAhlusA8g_6Jp-w_bzsDINwC",
    "Machine-Blueprints": "12yjlX_MvhjmJlwuhqFEqVFcQkNR0M7r0",
}

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
BLUEPRINT_RE = re.compile(r"^(?P<machine>[a-zA-Z0-9]+)-blueprint-(?P<date>\d{8})$")


class DriveLegError(RuntimeError):
    """Raised on any relay failure or verify mismatch. Always raised BEFORE anything is
    logged or deleted, so every verb's "delete only after verify" rule holds by construction:
    a caller that deletes only after `put()` returns (never after it raises) cannot delete on
    a failure."""


# --------------------------------------------------------------------------- env / paths
def config_dir() -> Path:
    """$CLAUDE_CONFIG_DIR, or ~/.claude when unset -- read fresh on every call, never cached,
    so a test can point it elsewhere without reloading this module."""
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(raw) if raw else Path.home() / ".claude"


def rclone_path() -> str:
    """The relay command, resolved from the repo root; overridable with DRIVE_LEG_RCLONE (the
    tests point this at a fake relay; dry-runs should pass DRIVE_LEG_RCLONE=/bin/false so a bug
    that skipped the dry-run guard fails loudly instead of silently reaching the real winbox)."""
    return os.environ.get("DRIVE_LEG_RCLONE") or str(DEFAULT_RCLONE)


def _docker_bin() -> str:
    return os.environ.get("DRIVE_LEG_DOCKER") or "docker"


def _default_who() -> str:
    return f"drive_leg.py@{socket.gethostname()}"


def log_path(config_dir_: Path) -> Path:
    return config_dir_ / "logs" / "drive-archive.log"


def transcript_index_path(config_dir_: Path) -> Path:
    return config_dir_ / "logs" / "transcript-archive-index.jsonl"


def uploads_index_path(config_dir_: Path) -> Path:
    return config_dir_ / "logs" / "uploads-archive-index.jsonl"


def blueprint_index_path(config_dir_: Path) -> Path:
    return config_dir_ / "logs" / "blueprint-archive-index.jsonl"


# --------------------------------------------------------------------------- small helpers
def _sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_ledger(log_path_: Path, *, source: str, remote: str, folder_id: str,
                    drive_id: str | None, count: int, nbytes: int, md5: str,
                    drive_md5: str | None, who: str) -> None:
    """Same pipe-separated shape as the existing drive-archive.log lines:
    ts | source | destination (id) | n files | bytes | md5 | verify | OK | who."""
    log_path_.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    verify = (f"drive md5 {drive_md5} = local" if drive_md5 == md5
              else f"MISMATCH drive md5 {drive_md5} != local {md5}")
    line = " | ".join([
        ts, source, f"{remote} ({folder_id}) id {drive_id}",
        f"{count} files", f"{nbytes} B", f"md5 {md5}", verify, "OK", who,
    ])
    with log_path_.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def build_manifest(*, name: str, machine: str, source: str, files: list[dict], restore: str,
                    excluded: list[str] | None = None, extra: dict | None = None) -> dict:
    """The fields `put()` doesn't fill. `put()` adds bytes/md5/sha256/drive after streaming --
    those aren't knowable until the tar has actually been sent."""
    manifest = {
        "name": name,
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "machine": machine,
        "source": source,
        "files": files,
        "count": len(files),
        "restore": restore,
        "excluded": excluded or [],
    }
    if extra:
        manifest.update(extra)
    return manifest


class _Sink:
    """File-like: forwards to the relay's stdin, hashing + counting what passes through.
    Precedent: scripts/stream_backup_to_drive.py's Sink."""

    def __init__(self, fh):
        self.fh = fh
        self.n = 0
        self.md5 = hashlib.md5()
        self.sha256 = hashlib.sha256()

    def write(self, b: bytes) -> int:
        self.fh.write(b)
        self.md5.update(b)
        self.sha256.update(b)
        self.n += len(b)
        return len(b)

    def flush(self) -> None:
        self.fh.flush()


def _lsjson(rclone: str, folder_id: str, remote_dir: str, *, dirs_only: bool = False,
            recursive: bool = False) -> list[dict]:
    remote = f"gdrive:{remote_dir}" if remote_dir else "gdrive:"
    cmd = [rclone, "lsjson", "--hash", "--no-mimetype"]
    cmd.append("--dirs-only" if dirs_only else "--files-only")
    if recursive:
        cmd.append("--recursive")
    cmd += ["--drive-root-folder-id", folder_id, remote]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise DriveLegError(f"lsjson rc={r.returncode} for {remote}: {(r.stderr or '').strip()[-400:]}")
    try:
        return json.loads(r.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise DriveLegError(f"lsjson returned bad JSON for {remote}: {exc}") from exc


def _find(objs: list[dict], name: str) -> dict | None:
    for o in objs:
        if o.get("Name") == name:
            return o
    return None


# --------------------------------------------------------------------------- put() -- the core
def put(stream_fn: Callable[[_Sink], None], folder_id: str, remote_dir: str, base_name: str,
        ext: str, manifest: dict, *, log_path_: Path, who: str,
        rclone: str | None = None, remote_prefix: str = "gdrive:") -> dict:
    """The common upload core every verb funnels through when NOT in --dry-run.

    (The brief's shorthand is `put(stream_fn, folder_id, remote_name, manifest)`; `remote_name`
    is split into `remote_dir` + `base_name` + `ext` here because the manifest's sibling name
    -- `<base_name>.manifest.json` -- must be derivable, and verifying needs to `lsjson` a
    DIRECTORY, not a single object.)

    Streams `stream_fn(sink)` into `rclone rcat <remote_prefix><remote_dir>/<base_name><ext>
    --drive-root-folder-id <folder_id>` through the relay -- md5/sha256/size computed on the
    fly from the bytes actually sent, never re-read off Drive -- confirms the object landed
    with `lsjson --hash` (size AND md5 must match), fills `manifest`'s bytes/md5/sha256/drive
    fields, uploads it beside the archive as `<base_name>.manifest.json`, verifies that too,
    then appends one ledger line to `log_path_`. Returns the completed manifest (with `drive`
    and `verified: True`).

    Raises DriveLegError -- never returns a falsy/partial result -- on any relay failure or
    verify mismatch, always BEFORE the ledger line is written. `put()` itself never deletes
    anything; every verb owns its own delete step, strictly after this returns.
    """
    rclone = rclone or rclone_path()
    tar_name = f"{base_name}{ext}"
    manifest_name = f"{base_name}.manifest.json"
    remote_tar = f"{remote_dir}/{tar_name}" if remote_dir else tar_name
    remote_manifest = f"{remote_dir}/{manifest_name}" if remote_dir else manifest_name

    if remote_dir:
        r = subprocess.run([rclone, "mkdir", f"{remote_prefix}{remote_dir}",
                            "--drive-root-folder-id", folder_id],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise DriveLegError(f"mkdir failed for {remote_dir!r}: {(r.stderr or '').strip()[-400:]}")

    with tempfile.TemporaryFile() as errf:
        proc = subprocess.Popen([rclone, "rcat", f"{remote_prefix}{remote_tar}",
                                 "--drive-root-folder-id", folder_id],
                                stdin=subprocess.PIPE, stderr=errf)
        sink = _Sink(proc.stdin)
        try:
            stream_fn(sink)
            proc.stdin.close()
        except DriveLegError:
            proc.kill()
            proc.wait()
            raise
        except Exception as exc:
            proc.kill()
            proc.wait()
            errf.seek(0)
            raise DriveLegError(
                f"stream to {remote_tar} broke after {sink.n} bytes: {exc!r} "
                f"(relay stderr: {errf.read()[-400:]!r})") from exc
        rc = proc.wait()
        if rc != 0:
            errf.seek(0)
            raise DriveLegError(f"relay rcat rc={rc} for {remote_tar}: {errf.read()[-400:]!r}")

    objs = _lsjson(rclone, folder_id, remote_dir)
    match = _find(objs, tar_name)
    tar_md5 = sink.md5.hexdigest()
    if not match or match.get("Size") != sink.n or (match.get("Hashes") or {}).get("md5") != tar_md5:
        raise DriveLegError(
            f"VERIFY FAILED for {remote_tar}: stream {sink.n} B md5={tar_md5}; drive object={match!r}")

    manifest = dict(manifest)
    manifest["bytes"] = sink.n
    manifest["md5"] = tar_md5
    manifest["sha256"] = sink.sha256.hexdigest()
    manifest["drive"] = {"folder_id": folder_id, "remote_path": f"{remote_prefix}{remote_tar}",
                         "id": match.get("ID")}
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    mp = subprocess.run([rclone, "rcat", f"{remote_prefix}{remote_manifest}",
                        "--drive-root-folder-id", folder_id],
                       input=manifest_bytes, capture_output=True, timeout=300)
    if mp.returncode != 0:
        raise DriveLegError(
            f"manifest upload failed for {remote_manifest} -- ARCHIVE ITSELF IS VERIFIED, "
            f"manifest failed, nothing deleted: rc={mp.returncode} "
            f"{(mp.stderr or b'').decode('utf-8', 'replace')[-400:]}")
    manifest_md5 = hashlib.md5(manifest_bytes).hexdigest()
    mobjs = _lsjson(rclone, folder_id, remote_dir)
    mmatch = _find(mobjs, manifest_name)
    if not mmatch or (mmatch.get("Hashes") or {}).get("md5") != manifest_md5:
        raise DriveLegError(
            f"manifest VERIFY FAILED for {remote_manifest} -- archive verified, manifest not, "
            f"nothing deleted: drive object={mmatch!r}")

    _append_ledger(log_path_, source=str(manifest.get("source", "")),
                   remote=f"{remote_prefix}{remote_tar}", folder_id=folder_id,
                   drive_id=match.get("ID"), count=manifest.get("count", 0), nbytes=sink.n,
                   md5=tar_md5, drive_md5=(match.get("Hashes") or {}).get("md5"), who=who)

    manifest["verified"] = True
    manifest["tar_name"] = tar_name
    manifest["manifest_name"] = manifest_name
    manifest["remote_dir"] = remote_dir
    manifest["manifest_id"] = mmatch.get("ID")
    return manifest


# =========================================================================== 1. transcripts
def _iter_sessions(config_dir_: Path):
    """Yield one dict per <slug>/<uuid>.jsonl under config_dir_/projects/ (+ the sibling
    <uuid>/ dir when it exists -- sub-agent transcripts)."""
    projects = config_dir_ / "projects"
    if not projects.is_dir():
        return
    for slug_dir in sorted(p for p in projects.iterdir() if p.is_dir()):
        for jsonl in sorted(slug_dir.glob("*.jsonl")):
            uuid = jsonl.stem
            if not UUID_RE.match(uuid):
                continue
            try:
                st = jsonl.stat()
            except OSError:
                continue
            subdir = slug_dir / uuid
            yield dict(slug=slug_dir.name, uuid=uuid, jsonl=jsonl,
                       subdir=subdir if subdir.is_dir() else None,
                       mtime=st.st_mtime)


def _session_files(sess: dict) -> list[Path]:
    files = [sess["jsonl"]]
    if sess["subdir"]:
        files += [p for p in sorted(sess["subdir"].rglob("*")) if p.is_file()]
    return files


def _local_day(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


def _group_by_day(sessions: list[dict], min_age_days: float, now: float) -> dict:
    """A (slug, day) group is eligible only when EVERY session in it is older than
    min_age_days -- never a day that mixes an old and a too-young session."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for sess in sessions:
        sess["day"] = _local_day(sess["mtime"])
        sess["age_days"] = (now - sess["mtime"]) / 86400.0
        groups.setdefault((sess["slug"], sess["day"]), []).append(sess)
    return {key: rows for key, rows in groups.items()
            if all(r["age_days"] > min_age_days for r in rows)}


def _all_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    out = [root]
    for dirpath, dirnames, _ in os.walk(root):
        out += [Path(dirpath) / d for d in dirnames]
    return out


def _delete_verified(frozen: list[tuple[Path, int, int]], dirs: list[Path] | None = None) -> int:
    """Delete each frozen (path, size, mtime_ns) file only if it is unchanged since freeze;
    a changed or already-gone file is skipped, never raised on. Then prune `dirs` (deepest
    first) that ended up empty. Returns the count of files removed. Precedent:
    scripts/stream_backup_to_drive.py's delete_frozen()."""
    removed = 0
    for path, size, mtime_ns in frozen:
        try:
            st = path.stat()
        except FileNotFoundError:
            continue
        if st.st_size != size or st.st_mtime_ns != mtime_ns:
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    for d in sorted(dirs or [], key=lambda p: -len(str(p))):
        try:
            d.rmdir()
        except OSError:
            pass
    return removed


def _append_transcript_index(config_dir_: Path, slug: str, day: str, sess_list: list[dict],
                              result: dict) -> None:
    path = transcript_index_path(config_dir_)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    for sess in sess_list:
        _append_jsonl(path, dict(uuid=sess["uuid"], slug=slug, day=day, archived_at=ts,
                                 drive=result.get("drive")))


def transcripts(*, config_dir: Path, min_age_days: float = 7, only_slug: str | None = None,
                 max_days: int | None = None, dry_run: bool = False, rclone: str | None = None,
                 who: str | None = None, now: float | None = None) -> dict:
    """$CLAUDE_CONFIG_DIR/projects/<slug>/<uuid>.jsonl (+ sibling <uuid>/ dir), grouped by
    (slug, local date of mtime); a day is archived only when every session in it is older
    than `min_age_days`. Per (slug, day): one <day>.tar.gz under
    Claude-Transcripts/contabo/<slug>/ + <day>.manifest.json, plus one row per uuid appended
    to $CLAUDE_CONFIG_DIR/logs/transcript-archive-index.jsonl. Local files for a day are
    deleted only after put() verifies AND only the ones whose size+mtime are still what they
    were at freeze time; a file younger than the threshold is never even considered."""
    now = time.time() if now is None else now
    who = who or _default_who()
    sessions = list(_iter_sessions(config_dir))
    if only_slug:
        sessions = [s for s in sessions if s["slug"] == only_slug]
    groups = _group_by_day(sessions, min_age_days, now)
    keys = sorted(groups)
    if max_days is not None:
        keys = keys[:max_days]

    report: dict = {"dry_run": dry_run, "days": [], "verified": 0, "failed": 0, "deleted_files": 0}
    if not keys:
        print(f"transcripts: nothing eligible (min_age_days={min_age_days})")
        return report

    for n, key in enumerate(keys, 1):
        slug, day = key
        sess_list = sorted(groups[key], key=lambda s: s["uuid"])
        base = config_dir / "projects" / slug
        members = [(f, str(f.relative_to(base))) for sess in sess_list for f in _session_files(sess)]
        total_bytes = sum(f.stat().st_size for f, _ in members)
        print(f"[{n}/{len(keys)}] transcripts {slug} {day}: {len(sess_list)} sessions, "
              f"{len(members)} files, {total_bytes} B")

        if dry_run:
            report["days"].append(dict(slug=slug, day=day, sessions=[s["uuid"] for s in sess_list],
                                        files=len(members), bytes=total_bytes, dry_run=True))
            continue

        frozen = [(f, f.stat().st_size, f.stat().st_mtime_ns) for f, _ in members]
        manifest = build_manifest(
            name=day, machine="contabo", source=f"{base} ({day})",
            files=[dict(path=arc, size=sz, mtime_ns=mt, sha256=_sha256_file(f))
                   for (f, sz, mt), (_, arc) in zip(frozen, members)],
            restore=f"tools/drive_leg.py restore-transcript <uuid>  (reads {day}.manifest.json "
                     f"under Claude-Transcripts/contabo/{slug}/)",
        )

        def _stream(sink, _members=members):
            with tarfile.open(fileobj=sink, mode="w:gz") as tf:
                for f, arcname in _members:
                    tf.add(f, arcname=arcname, recursive=False)

        try:
            result = put(_stream, FOLDER_IDS["Claude-Transcripts"], f"contabo/{slug}", day,
                        ".tar.gz", manifest, log_path_=log_path(config_dir), who=who, rclone=rclone)
        except DriveLegError as exc:
            print(f"    FAILED: {exc}")
            report["failed"] += 1
            report["days"].append(dict(slug=slug, day=day, verified=False, error=str(exc)))
            continue

        _append_transcript_index(config_dir, slug, day, sess_list, result)
        prune_dirs = [d for sess in sess_list if sess["subdir"] for d in _all_dirs(sess["subdir"])]
        removed = _delete_verified(frozen, prune_dirs)
        report["deleted_files"] += removed
        report["verified"] += 1
        report["days"].append(dict(slug=slug, day=day, verified=True, files=len(members),
                                    bytes=result["bytes"], deleted=removed))
    return report


# =========================================================================== restore-transcript
def _assert_safe_member(member: tarfile.TarInfo) -> None:
    name = member.name
    if name.startswith("/") or name.startswith("\\") or ".." in Path(name).parts:
        raise DriveLegError(f"unsafe tar member: {name!r}")
    if member.issym() or member.islnk():
        raise DriveLegError(f"unsafe tar member (link): {name!r}")


def _index_lookup(config_dir_: Path, uuid_prefix: str) -> dict | None:
    rows = _read_jsonl(transcript_index_path(config_dir_))
    hits = [r for r in rows if r.get("uuid", "").startswith(uuid_prefix)]
    if not hits:
        return None
    distinct = {h["uuid"] for h in hits}
    if len(distinct) > 1:
        raise DriveLegError(f"ambiguous uuid prefix {uuid_prefix!r}: matches {sorted(distinct)}")
    return hits[-1]


def _index_lookup_via_relay(uuid_prefix: str, rclone: str) -> dict | None:
    """Fallback when the local index is missing or stale: recursively lsjson the whole
    Claude-Transcripts folder, download each day's manifest via `cat`, and search its file
    list for a uuid matching the prefix. Only used when `_index_lookup` finds nothing."""
    folder_id = FOLDER_IDS["Claude-Transcripts"]
    try:
        objs = _lsjson(rclone, folder_id, "", recursive=True)
    except DriveLegError:
        return None
    for obj in objs:
        path = obj.get("Path", "")
        if not path.endswith(".manifest.json"):
            continue
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "contabo":
            continue
        slug, fname = parts[1], parts[2]
        day = fname[: -len(".manifest.json")]
        proc = subprocess.run([rclone, "cat", f"gdrive:{path}", "--drive-root-folder-id", folder_id],
                              capture_output=True, timeout=120)
        if proc.returncode != 0:
            continue
        try:
            manifest = json.loads(proc.stdout)
        except json.JSONDecodeError:
            continue
        for f in manifest.get("files", []):
            uuid = Path(f.get("path", "")).parts[0].split(".")[0] if f.get("path") else ""
            if uuid.startswith(uuid_prefix):
                return {"uuid": uuid, "slug": slug, "day": day}
    return None


def restore_transcript(uuid_prefix: str, *, config_dir: Path, rclone: str | None = None) -> dict:
    """Find the day tar via the local index (fallback: lsjson + read manifests), download it
    through the relay (`cat`), extract only the matching session back into
    projects/<slug>/. Refuses unsafe tar members (path traversal, symlinks/hardlinks)."""
    rclone = rclone or rclone_path()
    print(f"[1/1] restore-transcript {uuid_prefix}")
    hit = _index_lookup(config_dir, uuid_prefix) or _index_lookup_via_relay(uuid_prefix, rclone)
    if hit is None:
        raise DriveLegError(f"no archived session matching {uuid_prefix!r}")
    slug, day, uuid = hit["slug"], hit["day"], hit["uuid"]
    remote_tar = f"contabo/{slug}/{day}.tar.gz"

    proc = subprocess.run([rclone, "cat", f"gdrive:{remote_tar}", "--drive-root-folder-id",
                           FOLDER_IDS["Claude-Transcripts"]], capture_output=True, timeout=1800)
    if proc.returncode != 0:
        raise DriveLegError(f"relay cat rc={proc.returncode} for {remote_tar}: "
                            f"{(proc.stderr or b'').decode('utf-8', 'replace')[-400:]}")

    dest = config_dir / "projects" / slug
    dest.mkdir(parents=True, exist_ok=True)
    extracted = []
    with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:gz") as tf:
        for member in tf.getmembers():
            if not (member.name == f"{uuid}.jsonl" or member.name.startswith(f"{uuid}/")):
                continue
            _assert_safe_member(member)
            tf.extract(member, dest, filter="data")  # belt-and-suspenders: stdlib's own guard too
            extracted.append(member.name)
    if not extracted:
        raise DriveLegError(f"session {uuid} not found inside {remote_tar}")
    print(f"    restored {uuid} ({len(extracted)} member(s)) into {dest}")
    return dict(uuid=uuid, slug=slug, day=day, dest=str(dest), members=extracted)


# =========================================================================== 3. uploads
def uploads(*, config_dir: Path, dry_run: bool = False, rclone: str | None = None,
            who: str | None = None, now: float | None = None) -> dict:
    """$CLAUDE_CONFIG_DIR/uploads/ -> Claude-Uploads/contabo/<date>.tar + manifest. Skips
    when the sha256 of the sorted (path, size, mtime_ns) listing equals the previous run's
    (recorded locally in uploads-archive-index.jsonl -- the brief's "last ledger entry" read
    without a network call, so --dry-run can answer "unchanged" with zero relay calls too).
    Never deletes anything."""
    who = who or _default_who()
    now = time.time() if now is None else now
    src = config_dir / "uploads"
    files = sorted(p for p in src.rglob("*") if p.is_file()) if src.is_dir() else []
    listing = [[str(p.relative_to(src)), p.stat().st_size, p.stat().st_mtime_ns] for p in files]
    listing_sha256 = hashlib.sha256(json.dumps(listing).encode("utf-8")).hexdigest()

    idx_path = uploads_index_path(config_dir)
    rows = _read_jsonl(idx_path)
    last = rows[-1] if rows else None
    if last and last.get("listing_sha256") == listing_sha256:
        print(f"[1/1] uploads: unchanged since {last.get('date')}, skipping "
              f"({len(files)} files, listing sha256 {listing_sha256[:12]}...)")
        return dict(skipped=True, reason="unchanged", listing_sha256=listing_sha256, files=len(files))

    date = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
    total_bytes = sum(row[1] for row in listing)
    print(f"[1/1] uploads {date}: {len(files)} files, {total_bytes} B")
    if not files:
        print("    nothing under uploads/, skipping")
        return dict(skipped=True, reason="empty", listing_sha256=listing_sha256, files=0)
    if dry_run:
        return dict(dry_run=True, listing_sha256=listing_sha256, files=len(files), bytes=total_bytes)

    manifest = build_manifest(
        name=date, machine="contabo", source=str(src),
        files=[dict(path=str(p.relative_to(src)), size=p.stat().st_size,
                    mtime_ns=p.stat().st_mtime_ns, sha256=_sha256_file(p)) for p in files],
        restore=(f'rclone copy "gdrive:contabo/{date}.tar" . --drive-root-folder-id '
                 f'{FOLDER_IDS["Claude-Uploads"]} && tar xf {date}.tar -C {src}'),
        extra={"listing_sha256": listing_sha256},
    )

    def _stream(sink, _files=files, _src=src):
        with tarfile.open(fileobj=sink, mode="w|") as tf:
            for p in _files:
                tf.add(p, arcname=str(p.relative_to(_src)), recursive=False)

    result = put(_stream, FOLDER_IDS["Claude-Uploads"], "contabo", date, ".tar", manifest,
                log_path_=log_path(config_dir), who=who, rclone=rclone)
    _append_jsonl(idx_path, dict(date=date, listing_sha256=listing_sha256, files=len(files),
                                 bytes=result["bytes"], drive=result["drive"]))
    return result


# =========================================================================== 4. docker-volumes
def _n8n_cmd(volume: str) -> list[str]:
    return [_docker_bin(), "run", "--rm", "-v", f"{volume}:/v:ro", "alpine", "tar", "cf", "-",
            "--exclude=./config", "-C", "/v", "."]


def _pgdump_cmd(container: str, user: str) -> list[str]:
    return [_docker_bin(), "exec", container, "pg_dumpall", "-U", user]


def _copy_subprocess_stdout(cmd: list[str], sink: _Sink) -> None:
    """docker's own stdout IS the tar stream -- forwarded byte for byte, never re-tarred."""
    with tempfile.TemporaryFile() as errf:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf)
        try:
            while True:
                chunk = proc.stdout.read(1 << 20)
                if not chunk:
                    break
                sink.write(chunk)
        finally:
            proc.stdout.close()
        rc = proc.wait()
        if rc != 0:
            errf.seek(0)
            raise DriveLegError(f"command failed rc={rc} ({' '.join(cmd)}): {errf.read()[-400:]!r}")


def _copy_pgdump_gzip(cmd: list[str], sink: _Sink) -> None:
    """pg_dumpall's stdout, gzipped with the stdlib gzip module (no external `gzip` binary --
    stdlib-only requirement) straight into the sink."""
    with tempfile.TemporaryFile() as errf:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf)
        try:
            with gzip.GzipFile(fileobj=sink, mode="wb") as gz:
                while True:
                    chunk = proc.stdout.read(1 << 20)
                    if not chunk:
                        break
                    gz.write(chunk)
        finally:
            proc.stdout.close()
        rc = proc.wait()
        if rc != 0:
            errf.seek(0)
            raise DriveLegError(f"pg_dumpall failed rc={rc} ({' '.join(cmd)}): {errf.read()[-400:]!r}")


def docker_volumes(*, config_dir: Path, volumes: list[str] | None = None, dry_run: bool = False,
                   pg_container: str = "org-postgres", pg_user: str = "org",
                   rclone: str | None = None, who: str | None = None,
                   now: float | None = None) -> dict:
    """n8n_data -> `docker run --rm -v n8n_data:/v:ro alpine tar cf - --exclude=./config -C /v .`
    streamed as Docker-Volumes/contabo/n8n_data/<date>.tar (config excluded -- it holds n8n's
    encryptionKey, a secret; manifest carries the `excluded` note). org-pgdata -> `docker exec
    <pg_container> pg_dumpall -U <pg_user>` gzipped as .../org-pgdata/<date>.sql.gz. Never
    deletes anything local (there is nothing local to delete -- both streams go straight from
    docker's own stdout to the relay). --dry-run prints the docker commands and touches
    neither docker nor the relay."""
    who = who or _default_who()
    now = time.time() if now is None else now
    date = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
    volumes = volumes or ["n8n_data", "org-pgdata"]
    report: dict = {"dry_run": dry_run, "volumes": []}

    for n, vol in enumerate(volumes, 1):
        if vol == "n8n_data":
            cmd = _n8n_cmd(vol)
            ext = ".tar"
            excluded = ["config (n8n encryptionKey; restore it from the secrets bundle, see "
                        "registry row)"]
            restore = (f"docker volume create {vol}; rclone cat "
                      f'"gdrive:contabo/{vol}/{date}{ext}" --drive-root-folder-id '
                      f'{FOLDER_IDS["Docker-Volumes"]} | docker run --rm -i -v {vol}:/v alpine '
                      f"tar xf - -C /v   (config excluded: restore encryptionKey from the "
                      f"secrets bundle)")

            def _stream(sink, _cmd=cmd):
                _copy_subprocess_stdout(_cmd, sink)
        elif vol == "org-pgdata":
            cmd = _pgdump_cmd(pg_container, pg_user)
            ext = ".sql.gz"
            excluded = []
            restore = (f'rclone cat "gdrive:contabo/{vol}/{date}{ext}" --drive-root-folder-id '
                      f'{FOLDER_IDS["Docker-Volumes"]} | gunzip | docker exec -i {pg_container} '
                      f"psql -U {pg_user}")

            def _stream(sink, _cmd=cmd):
                _copy_pgdump_gzip(_cmd, sink)
        else:
            print(f"[{n}/{len(volumes)}] docker-volumes {vol}: unknown volume, skipping")
            report["volumes"].append(dict(volume=vol, skipped=True, reason="unknown volume"))
            continue

        print(f"[{n}/{len(volumes)}] docker-volumes {vol}: {' '.join(cmd)}")
        if dry_run:
            report["volumes"].append(dict(volume=vol, dry_run=True, cmd=cmd,
                                          dest=f"contabo/{vol}/{date}{ext}"))
            continue

        manifest = build_manifest(name=date, machine="contabo", source=f"docker volume {vol}",
                                  files=[], restore=restore, excluded=excluded)
        try:
            result = put(_stream, FOLDER_IDS["Docker-Volumes"], f"contabo/{vol}", date, ext,
                        manifest, log_path_=log_path(config_dir), who=who, rclone=rclone)
        except DriveLegError as exc:
            print(f"    FAILED: {exc}")
            report["volumes"].append(dict(volume=vol, verified=False, error=str(exc)))
            continue
        report["volumes"].append(dict(volume=vol, verified=True, bytes=result["bytes"]))
    return report


# =========================================================================== 5. blueprints
def _find_blueprint_dirs(state_dir: Path, only_machine: str | None = None) -> list[dict]:
    if not state_dir.is_dir():
        return []
    out = []
    for d in sorted(state_dir.iterdir()):
        if not d.is_dir():
            continue
        m = BLUEPRINT_RE.match(d.name)
        if not m:
            continue
        machine = m.group("machine")
        if only_machine and machine != only_machine:
            continue
        raw = m.group("date")
        out.append(dict(machine=machine, date=f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}", dir=d, name=d.name))
    return out


def blueprints(*, state_dir: Path, config_dir: Path, only_machine: str | None = None,
               dry_run: bool = False, rclone: str | None = None, who: str | None = None) -> dict:
    """state/<machine>-blueprint-<date>/ dirs (default: every one present in state_dir) ->
    Machine-Blueprints/<machine>/<date>/<machine>-blueprint-<date>.tar + manifest. Skips a
    dir whose tar sha256 is already recorded in blueprint-archive-index.jsonl. Never deletes
    the source dir -- git is the primary copy; the temp tar this function builds to compute
    the sha256 before uploading is its own scratch file, removed in `finally` regardless of
    outcome."""
    who = who or _default_who()
    dirs = _find_blueprint_dirs(state_dir, only_machine)
    idx_path = blueprint_index_path(config_dir)
    known_sha256 = {row.get("sha256") for row in _read_jsonl(idx_path)}
    report: dict = {"dry_run": dry_run, "blueprints": []}

    for n, bp in enumerate(dirs, 1):
        base_name = f"{bp['machine']}-blueprint-{bp['date']}"
        files = sorted(p for p in bp["dir"].rglob("*") if p.is_file())
        total_bytes = sum(p.stat().st_size for p in files)
        print(f"[{n}/{len(dirs)}] blueprints {base_name}: {len(files)} files, {total_bytes} B")
        if dry_run:
            report["blueprints"].append(dict(machine=bp["machine"], date=bp["date"],
                                              files=len(files), bytes=total_bytes, dry_run=True))
            continue

        tmp_fd, tmp_name = tempfile.mkstemp(prefix="drive_leg_blueprint_", suffix=".tar")
        os.close(tmp_fd)
        tmp_path = Path(tmp_name)
        try:
            with tarfile.open(tmp_path, mode="w") as tf:
                for p in files:
                    tf.add(p, arcname=str(p.relative_to(bp["dir"].parent)), recursive=False)
            tar_sha256 = _sha256_file(tmp_path)
            if tar_sha256 in known_sha256:
                print("    already archived (same sha256), skipping")
                report["blueprints"].append(dict(machine=bp["machine"], date=bp["date"],
                                                  skipped=True, reason="sha256 already archived"))
                continue

            manifest = build_manifest(
                name=base_name, machine=bp["machine"], source=str(bp["dir"]),
                files=[dict(path=str(p.relative_to(bp["dir"].parent)), size=p.stat().st_size,
                            mtime_ns=p.stat().st_mtime_ns, sha256=_sha256_file(p)) for p in files],
                restore=f"git checkout state/{bp['name']}/  (git is the primary copy; this Drive "
                         f"tar is a redundant copy)")

            def _stream(sink, _tmp=tmp_path):
                with _tmp.open("rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        sink.write(chunk)

            try:
                result = put(_stream, FOLDER_IDS["Machine-Blueprints"], f"{bp['machine']}/{bp['date']}",
                            base_name, ".tar", manifest, log_path_=log_path(config_dir), who=who,
                            rclone=rclone)
            except DriveLegError as exc:
                print(f"    FAILED: {exc}")
                report["blueprints"].append(dict(machine=bp["machine"], date=bp["date"],
                                                  verified=False, error=str(exc)))
                continue
            _append_jsonl(idx_path, dict(machine=bp["machine"], date=bp["date"], sha256=tar_sha256,
                                         drive=result["drive"]))
            known_sha256.add(tar_sha256)
            report["blueprints"].append(dict(machine=bp["machine"], date=bp["date"], verified=True,
                                             bytes=result["bytes"]))
        finally:
            tmp_path.unlink(missing_ok=True)
    return report


# =========================================================================== CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="drive_leg.py",
                                 description="Contabo's Drive leg of the Machine Contract")
    sub = ap.add_subparsers(dest="command", required=True)

    t = sub.add_parser("transcripts", help="archive Claude Code session transcripts to Drive")
    t.add_argument("--min-age-days", type=float, default=7)
    t.add_argument("--only-slug")
    t.add_argument("--max-days", type=int)
    t.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("restore-transcript", help="restore one archived session")
    r.add_argument("uuid_prefix")

    u = sub.add_parser("uploads", help="archive $CLAUDE_CONFIG_DIR/uploads/ to Drive")
    u.add_argument("--dry-run", action="store_true")

    d = sub.add_parser("docker-volumes", help="back up n8n_data + org-pgdata to Drive")
    d.add_argument("--volumes", default="n8n_data,org-pgdata")
    d.add_argument("--pg-container", default="org-postgres")
    d.add_argument("--pg-user", default="org")  # POSTGRES_USER of org-postgres; there is no "postgres" role (measured 2026-09-24)
    d.add_argument("--dry-run", action="store_true")

    b = sub.add_parser("blueprints", help="archive state/<machine>-blueprint-<date>/ dirs to Drive")
    b.add_argument("--only-machine")
    b.add_argument("--dry-run", action="store_true")

    args = ap.parse_args(argv)
    cfg_dir = config_dir()

    try:
        if args.command == "transcripts":
            report = transcripts(config_dir=cfg_dir, min_age_days=args.min_age_days,
                                 only_slug=args.only_slug, max_days=args.max_days,
                                 dry_run=args.dry_run)
            return 1 if report.get("failed") else 0

        if args.command == "restore-transcript":
            restore_transcript(args.uuid_prefix, config_dir=cfg_dir)
            return 0

        if args.command == "uploads":
            result = uploads(config_dir=cfg_dir, dry_run=args.dry_run)
            return 1 if result.get("verified") is False else 0

        if args.command == "docker-volumes":
            volumes = [v.strip() for v in args.volumes.split(",") if v.strip()]
            report = docker_volumes(config_dir=cfg_dir, volumes=volumes, dry_run=args.dry_run,
                                    pg_container=args.pg_container, pg_user=args.pg_user)
            failed = sum(1 for v in report["volumes"] if v.get("verified") is False)
            return 1 if failed else 0

        if args.command == "blueprints":
            report = blueprints(state_dir=ROOT / "state", config_dir=cfg_dir,
                               only_machine=args.only_machine, dry_run=args.dry_run)
            failed = sum(1 for row in report["blueprints"] if row.get("verified") is False)
            return 1 if failed else 0
    except Exception as exc:  # the CLI must always exit non-zero, never a raw traceback
        print(f"drive_leg.py: ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
