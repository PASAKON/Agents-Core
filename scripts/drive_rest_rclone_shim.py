#!/usr/bin/env python3
"""The two rclone verbs stream_backup_to_drive.py uses (rcat, lsjson), done with the Mac's own Drive REST
resumable uploader (tools/work_archive.py) -- for when winbox's rclone is unreachable or on rclone's shared,
throttled client_id. Uploads into the folder --drive-root-folder-id names; the MIME type comes from the file name."""
import argparse
import http.client, json, mimetypes, os, sys, tempfile, time, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv" / "bin" / "python"
if __name__ == '__main__' and sys.prefix == sys.base_prefix and VENV.exists():
    os.execv(str(VENV), [str(VENV), __file__, *sys.argv[1:]])
sys.path.insert(0, str(ROOT))
from tools import work_archive as wa


def upload(path, name, root):
    """work_archive's resumable protocol, plus what it lacks: on a 5xx or a dropped connection, ask Drive
    where the upload stopped (PUT bytes */size) and resume from there instead of failing the whole file."""
    token, size = wa._access_token(), os.path.getsize(path)
    st0, rh0, _ = wa._http("POST", wa.DRIVE_UPLOAD + "?" + urllib.parse.urlencode(
        {"uploadType": "resumable", "fields": "id,name,size,md5Checksum,parents"}),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": mimetypes.guess_type(name)[0] or "application/x-tar",
                 "X-Upload-Content-Length": str(size)},
        body=json.dumps({"name": name, "parents": [root]}).encode())
    session = wa._header(rh0, "Location")
    if st0 not in (200, 201) or not session:
        raise RuntimeError(f"resumable session init failed: status={st0}")
    sent, fails = 0, 0
    with open(path, "rb") as fh:
        while True:
            fh.seek(sent)
            chunk = fh.read(min(wa.CHUNK_SIZE, size - sent))
            hdr = {"Content-Length": str(len(chunk)), "Content-Range": f"bytes {sent}-{sent + len(chunk) - 1}/{size}"}
            try:
                st, rh, body = wa._http("PUT", session, headers=hdr, body=chunk)
            except (OSError, http.client.HTTPException) as e:
                st, rh, body = None, {}, repr(e).encode()
            if st in (200, 201):
                meta = json.loads(body)
                break
            if st == 308:
                r = wa._header(rh, "Range")
                sent, fails = (int(r.rsplit("-", 1)[-1]) + 1 if r else sent + len(chunk)), 0
                continue
            fails += 1
            print(f"chunk at {sent}: status={st} {body[:120]!r}; retry {fails}", file=sys.stderr)
            if fails > 10:
                raise RuntimeError(f"gave up after {fails} failures at offset {sent}")
            time.sleep(min(60, 2 ** fails))
            try:
                st, rh, body = wa._http("PUT", session, headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"}, body=b"")
            except (OSError, http.client.HTTPException):
                continue
            if st in (200, 201):
                meta = json.loads(body)
                break
            if st == 308:
                r = wa._header(rh, "Range")
                sent = int(r.rsplit("-", 1)[-1]) + 1 if r else 0
    return meta if meta.get("md5Checksum") else wa._get_file_metadata(wa._http, token, meta["id"])


FOLDER_MIME = 'application/vnd.google-apps.folder'


def quote(value):
    return value.replace('\\', '\\\\').replace("'", "\\'")


def children(root, token):
    page = None
    while True:
        params = {'q': f"'{quote(root)}' in parents and trashed = false",
                  'fields': 'nextPageToken,files(id,name,size,md5Checksum,mimeType)', 'pageSize': 1000}
        if page:
            params['pageToken'] = page
        st, _, body = wa._http('GET', wa.DRIVE_FILES + '?' + urllib.parse.urlencode(params),
                              headers={'Authorization': 'Bearer ' + token})
        if st != 200:
            raise RuntimeError(f'list via REST failed: {st}')
        data = json.loads(body)
        yield from data['files']
        page = data.get('nextPageToken')
        if not page:
            break


def directory(root, parts, token, create=False):
    for name in parts:
        matches = [f for f in children(root, token) if f['name'] == name and f.get('mimeType') == FOLDER_MIME]
        if len(matches) > 1:
            raise RuntimeError('ambiguous Drive directory')
        if matches:
            root = matches[0]['id']
        elif create:
            st, _, body = wa._http('POST', wa.DRIVE_FILES,
                headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
                body=json.dumps({'name': name, 'parents': [root], 'mimeType': FOLDER_MIME}).encode())
            if st not in (200, 201):
                raise RuntimeError(f'mkdir via REST failed: {st}')
            root = json.loads(body)['id']
        else:
            raise RuntimeError('Drive directory does not exist')
    return root


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('verb', choices=['mkdir', 'rcat', 'lsjson'])
    parser.add_argument('remote')
    parser.add_argument('--drive-root-folder-id', required=True)
    for flag in ('hash', 'no-mimetype', 'files-only', 'dirs-only', 'recursive'):
        parser.add_argument('--' + flag, action='store_true')
    parser.add_argument('--include')
    args = parser.parse_intermixed_args(argv)
    root = args.drive_root_folder_id
    if len(root) < 20 or ':' not in args.remote:
        parser.error('need a Drive folder id and remote prefix')
    raw = args.remote.split(':', 1)[1].strip('/')
    parts = raw.split('/') if raw else []
    if any(p in ('', '.', '..') or '\\' in p for p in parts):
        parser.error('invalid remote path')
    token = wa._access_token()
    if args.verb == 'mkdir':
        directory(root, parts, token, create=True)
    elif args.verb == 'rcat':
        if not parts:
            parser.error('rcat needs a file name')
        parent = directory(root, parts[:-1], token, create=True)
        fd, path = tempfile.mkstemp(dir=os.environ.get('SHIM_TMP'), suffix='.part')
        try:
            with os.fdopen(fd, 'wb') as out:
                import shutil
                shutil.copyfileobj(sys.stdin.buffer, out, 8 << 20)
            print(json.dumps(upload(path, parts[-1], parent)), file=sys.stderr)
        finally:
            os.remove(path)
    else:
        parent = directory(root, parts, token)
        include = args.include.lstrip('/').replace('\\[', '[') if args.include else None
        def listing(folder, prefix='', ancestors=()):
            if folder in ancestors:
                raise RuntimeError('cyclic Drive directory')
            for f in children(folder, token):
                is_dir = f.get('mimeType') == FOLDER_MIME
                path = prefix + f['name']
                if (include is None or path == include) and not (args.files_only and is_dir or args.dirs_only and not is_dir):
                    yield {'Name': f['name'], 'Path': path, 'Size': int(f.get('size', 0)),
                           'ID': f['id'], 'IsDir': is_dir, 'Hashes': {'md5': f.get('md5Checksum')}}
                if args.recursive and is_dir:
                    yield from listing(f['id'], path + '/', (*ancestors, folder))
        print(json.dumps(list(listing(parent))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
