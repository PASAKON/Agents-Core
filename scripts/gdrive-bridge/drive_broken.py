#!/usr/bin/env python3
"""Broken Drive uploads: rename BROKEN-<name> at once, keep a ledger, retry as a new revision of the same id.

A broken upload: the source died mid-stream (rclone finalised 859 MB of a 915 MB tar under the real
name, 2026-09-24), or the md5 read back by id does not match the source. CEO 2026-09-28 (ruling 1):
rename it at once without asking, never trash it, and rename it back once a re-upload verifies.
Rule: CXO_Rules_GDrive_Filing hard rule 10. Procedure: CXO_Procedure_GDrive_BulkTransfer.

  mark <file_id> --source <path> [--why TEXT]   rename to BROKEN-<name>, append a ledger entry
  retry [--id FILE_ID] [--dry-run]              per open entry: source gone -> reported, stays BROKEN;
                                                else upload the source as a NEW REVISION of the same
                                                file id, read md5Checksum back by id, and only on a
                                                match rename it back and mark the entry resolved
  list [--all]                                  open entries (--all: resolved ones too)

Drive REST with the ClaudeFlow OAuth (ilag_sync.py's access_token/api), so it runs on Contabo, which
has no Apps Script bridge. It never trashes, deletes or creates a Drive file; the broken bytes become
an older revision. Ledger: state/drive-broken.jsonl (DRIVE_BROKEN_LEDGER overrides), append-only.
"""
from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
# Contabo's ClaudeFlow env (ilag_rest.py sets the same default); read by ilag_sync at import time.
os.environ.setdefault("MOONIEX_CLAUDEFLOW_ENV", "/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env")
sys.path.insert(0, str(HERE))
import ilag_sync as s  # noqa: E402  -- access_token(), api(), md5_file(), the Drive URLs

PREFIX = "BROKEN-"
LEDGER = Path(os.environ.get("DRIVE_BROKEN_LEDGER") or REPO / "state" / "drive-broken.jsonl")
CHUNK = 64 * 1024 * 1024   # Drive's resumable protocol wants a multiple of 256 KiB
MAX_FAILS = 8
TH = timezone(timedelta(hours=7))
META_FIELDS = "id,name,size,md5Checksum,trashed,parents,mimeType"


def now() -> str:
    return datetime.now(TH).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- Drive

def _http(method: str, url: str, *, headers: dict | None = None, body: bytes | None = None,
          timeout: int = 600) -> tuple[int, dict, bytes]:
    """Bare HTTPS request -> (status, headers, body). No redirect handling, so Drive's
    308 Resume Incomplete comes back as a status instead of an exception. Tests replace it."""
    parts = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(parts.netloc, timeout=timeout)
    try:
        conn.request(method, parts.path + ("?" + parts.query if parts.query else ""),
                     body=body, headers=headers or {})
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


def _header(headers: dict, name: str) -> str | None:
    for k, v in headers.items():
        if k.lower() == name.lower():
            return v
    return None


def _next_offset(headers: dict) -> int:
    """Where Drive wants the next byte: `Range: bytes=0-N` -> N+1; no Range -> nothing stored."""
    rng = _header(headers, "Range")
    return int(rng.rsplit("-", 1)[-1]) + 1 if rng else 0


def meta(fid: str) -> dict | None:
    """Drive's view of the object by id, or None when the id is gone."""
    try:
        return s.api(f"{s.DRIVE_FILES}/{fid}", params={"fields": META_FIELDS}, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def rename(fid: str, name: str) -> dict:
    return s.api(f"{s.DRIVE_FILES}/{fid}", method="PATCH", params={"fields": "id,name"},
                 data=json.dumps({"name": name}).encode(),
                 headers={"Content-Type": "application/json"}, timeout=60)


def same_name_siblings(m: dict, name: str) -> list[dict]:
    """Other live files called `name` in the object's parent folder(s)."""
    out = []
    esc = name.replace("\\", "\\\\").replace("'", "\\'")
    for parent in m.get("parents") or []:
        q = f"'{parent}' in parents and trashed = false and name = '{esc}'"
        res = s.api(s.DRIVE_FILES, params={"q": q, "fields": "files(id,name)"}, timeout=60)
        out += [f for f in res.get("files", []) if f["id"] != m["id"]]
    return out


def upload_revision(fid: str, path: Path, name: str, size: int) -> dict:
    """Resumable media upload onto an EXISTING file id (PATCH upload/drive/v3/files/<id>):
    Drive keeps the id, name and parents and makes the bytes the new head revision.
    A dropped chunk resumes from where Drive says it stopped (PUT bytes */size)."""
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    url = f"{s.DRIVE_UPLOAD}/{fid}?" + urllib.parse.urlencode(
        {"uploadType": "resumable", "fields": "id,name,size,md5Checksum"})
    st, hdrs, body = _http("PATCH", url, body=b"{}", timeout=60, headers={
        "Authorization": "Bearer " + s.access_token(),
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)})
    session = _header(hdrs, "Location")
    if st not in (200, 201) or not session:
        raise RuntimeError(f"resumable session not opened: HTTP {st} {body[:200]!r}")
    sent, fails, ask = 0, 0, False
    with open(path, "rb") as f:
        while True:
            if fails >= MAX_FAILS:
                raise RuntimeError(f"gave up after {fails} failures at offset {sent}: "
                                   f"HTTP {st} {body[:200]!r}")
            if ask or (size and sent >= size):  # ask Drive where it stopped
                buf, rng = b"", f"bytes */{size}"
            else:
                f.seek(sent)
                buf = f.read(min(CHUNK, size - sent))
                rng = f"bytes {sent}-{sent + len(buf) - 1}/{size}" if size else "bytes */0"
            try:
                st, hdrs, body = _http("PUT", session, body=buf, headers={
                    "Content-Length": str(len(buf)), "Content-Range": rng})
            except (OSError, http.client.HTTPException) as e:
                st, hdrs, body = None, {}, repr(e).encode()
            if st in (200, 201):
                return json.loads(body or b"{}")
            if st == 308:
                nxt = _next_offset(hdrs)
                if nxt > sent:
                    fails = 0
                elif not ask:  # a chunk went up and Drive moved nowhere
                    fails += 1
                sent, ask = nxt, False
                continue
            fails += 1
            print(f"  chunk at {sent}: HTTP {st} {body[:160]!r} (failure {fails}/{MAX_FAILS})",
                  file=sys.stderr)
            if st in (400, 404, 410):  # a bad request or an expired session: resuming cannot help
                raise RuntimeError(f"gave up at offset {sent}: HTTP {st} {body[:200]!r}")
            time.sleep(min(60, 2 ** fails))
            ask = True


# --------------------------------------------------------------------------- ledger

def read_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for n, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            raise SystemExit(f"{LEDGER}:{n} is not JSON -- repair that line by hand; "
                             "never rewrite the ledger")
    return out


def append(event: dict) -> None:
    line = json.dumps(event, ensure_ascii=False)
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as e:
        print(f"LEDGER WRITE FAILED ({e}); add this line to {LEDGER} by hand:\n{line}",
              file=sys.stderr)
        raise SystemExit(1)


def entries() -> dict[str, dict]:
    """file_id -> its latest mark, folded with the retry/resolved events after it."""
    state: dict[str, dict] = {}
    for ev in read_ledger():
        fid, kind = ev.get("file_id"), ev.get("event")
        if kind == "mark":
            state[fid] = dict(ev, status="open", attempts=0, last=None)
        elif fid in state and kind == "retry":
            state[fid]["attempts"] += 1
            state[fid]["last"] = ev
        elif fid in state and kind == "resolved":
            state[fid]["status"] = "resolved"
            state[fid]["last"] = ev
    return state


# --------------------------------------------------------------------------- verbs

def cmd_mark(fid: str, source: str, why: str) -> int:
    known = entries().get(fid)
    if known and known["status"] == "open":
        print(f"ALREADY OPEN {fid}  {known['name']}  (marked {known['when']} on {known['host']})")
        return 0
    m = meta(fid)
    if m is None:
        raise SystemExit(f"{fid}: no such file on Drive")
    if m.get("trashed"):
        raise SystemExit(f"{fid}: it is in the Drive trash -- report it to the CEO; not marked")
    name = m["name"]
    original = name[len(PREFIX):] if name.startswith(PREFIX) else name
    src = Path(source).expanduser()
    src_md5 = src_size = None
    if src.is_file():
        src_size = src.stat().st_size
        src_md5 = s.md5_file(src)
        if m.get("md5Checksum") == src_md5 and int(m.get("size") or -1) == src_size:
            print(f"NOT BROKEN {fid}  {name}: Drive md5 {src_md5} and size match the source -- "
                  "nothing renamed, nothing recorded")
            return 2
    else:
        print(f"note: source {src} is {'missing' if not src.exists() else 'not a regular file'}; "
              "marking anyway -- retry will report it")
    event = {"event": "mark", "file_id": fid, "name": original, "source": str(src),
             "source_md5": src_md5, "size": src_size, "why": why, "when": now(),
             "host": socket.gethostname(), "drive_md5": m.get("md5Checksum"),
             "drive_size": int(m["size"]) if m.get("size") else None}
    if name != PREFIX + original:
        got = rename(fid, PREFIX + original)
        if got.get("name") != PREFIX + original:
            raise SystemExit(f"{fid}: rename did not take, Drive says {got.get('name')!r}; "
                             "nothing recorded")
    append(event)
    print(f"MARKED {fid}  {original} -> {PREFIX}{original}")
    return 0


def retry_one(e: dict, *, dry_run: bool, allow_changed: bool) -> str:
    fid, name, src = e["file_id"], e["name"], Path(e["source"])

    def done(result: str, detail: str, **extra) -> str:
        if not dry_run:
            append({"event": "retry", "file_id": fid, "result": result, "detail": detail,
                    "when": now(), "host": socket.gethostname(), **extra})
        print(f"{result.upper():<16} {fid}  {name}  {detail}")
        return result

    if src.is_dir():
        return done("source-not-file", f"{src} is a folder (a streamed tar) -- re-run the stream under "
                    f"the original name; this object stays {PREFIX}{name}")
    if not src.is_file():
        return done("source-missing", f"{src} is gone -- stays {PREFIX}{name}; report it to the CEO")
    m = meta(fid)
    if m is None:
        return done("drive-missing", "the file id is gone from Drive -- report it to the CEO")
    if m.get("trashed"):
        return done("trashed", "the file is in the Drive trash -- report it to the CEO")
    size, local = src.stat().st_size, s.md5_file(src)
    if e.get("source_md5") and local != e["source_md5"] and not allow_changed:
        return done("source-changed", f"source md5 is now {local}, was {e['source_md5']} at the mark "
                    "-- skipped (--allow-changed-source uploads it anyway)", source_md5=local)
    uploaded = False
    if m.get("md5Checksum") != local or int(m.get("size") or -1) != size:
        if dry_run:
            return done("would-upload", f"{size} bytes, md5 {local}, as a new revision of {fid}")
        try:
            upload_revision(fid, src, name, size)
        except (RuntimeError, OSError, http.client.HTTPException) as ex:
            return done("error", f"upload failed: {ex}")
        uploaded = True
        m = meta(fid) or {}
    if m.get("md5Checksum") != local:  # the proof is Drive's own md5, read back by id
        return done("md5-mismatch", f"Drive md5 {m.get('md5Checksum')} != source {local} "
                    f"-- stays {PREFIX}{name}", source_md5=local, drive_md5=m.get("md5Checksum"))
    if dry_run:
        return done("would-rename", f"Drive md5 already matches -- would rename back to {name}")
    taken = same_name_siblings(m, name)
    if taken:
        return done("name-taken", f"md5 verified, but {name!r} already exists beside it "
                    f"({taken[0]['id']}) -- left as {PREFIX}{name}; ask the CEO", source_md5=local)
    if m.get("name") != name:
        got = rename(fid, name)
        if got.get("name") != name:
            return done("error", f"md5 verified, rename back did not take: {got.get('name')!r}")
    append({"event": "resolved", "file_id": fid, "name": name, "md5": local, "size": size,
            "uploaded": uploaded, "when": now(), "host": socket.gethostname()})
    print(f"{'RESOLVED':<16} {fid}  {name}  md5 {local}"
          f"{' (new revision uploaded)' if uploaded else ' (Drive already held the right bytes)'}")
    return "resolved"


def cmd_retry(only: str | None, dry_run: bool, allow_changed: bool) -> int:
    todo = [e for e in entries().values()
            if e["status"] == "open" and (only is None or e["file_id"] == only)]
    if not todo:
        print(f"no open entry for {only}" if only else "no open entries")
        return 1 if only else 0
    results = [retry_one(e, dry_run=dry_run, allow_changed=allow_changed) for e in todo]
    left = sum(r != "resolved" for r in results)
    if not dry_run:
        print(f"\n{len(results) - left} resolved, {left} still BROKEN")
    ok = {"would-upload", "would-rename"} if dry_run else {"resolved"}
    return 0 if all(r in ok for r in results) else 1


def cmd_list(show_all: bool) -> int:
    rows = [e for e in entries().values() if show_all or e["status"] == "open"]
    if not rows:
        print("ledger has no entries" if show_all else "no open entries")
        return 0
    for e in rows:
        last = e["last"] or {}
        print(f"{e['status'].upper():<9} {e['file_id']}  {PREFIX if e['status'] == 'open' else ''}"
              f"{e['name']}")
        print(f"          marked {e['when']} on {e['host']}: {e['why']}")
        print(f"          source {e['source']}  md5 {e['source_md5']}  size {e['size']}")
        if last:
            print(f"          tries {e['attempts']}, last {last.get('result', last.get('event'))} "
                  f"{last['when']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="drive_broken.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)
    p = sub.add_parser("mark", help="rename a broken upload BROKEN-<name> and record it")
    p.add_argument("file_id")
    p.add_argument("--source", required=True, help="local file the object should have been")
    p.add_argument("--why", default="broken upload", help="what broke (source died, md5 mismatch)")
    p = sub.add_parser("retry", help="re-upload open entries as a new revision; rename back on md5 match")
    p.add_argument("--id", dest="only", help="only this file id")
    p.add_argument("--dry-run", action="store_true", help="read Drive and the source; write nothing")
    p.add_argument("--allow-changed-source", action="store_true",
                   help="upload even if the source md5 differs from the one recorded at the mark")
    p = sub.add_parser("list", help="show open entries")
    p.add_argument("--all", action="store_true", help="include resolved entries")
    a = ap.parse_args(argv)
    if a.verb == "mark":
        return cmd_mark(a.file_id, a.source, a.why)
    if a.verb == "retry":
        return cmd_retry(a.only, a.dry_run, a.allow_changed_source)
    return cmd_list(a.all)


if __name__ == "__main__":
    raise SystemExit(main())
