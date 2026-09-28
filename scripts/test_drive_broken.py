"""Tests for scripts/gdrive-bridge/drive_broken.py -- no live Drive call anywhere.

Drive is a FakeDrive behind the tool's two seams: ilag_sync.api (metadata GET/PATCH, list
queries) and drive_broken._http (the resumable upload). urllib and http.client are also made
to refuse, so a path left unmocked fails loudly instead of reaching Google.
"""
import hashlib
import http.client
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent / "gdrive-bridge"))
import drive_broken as db  # noqa: E402

import pytest  # noqa: E402


class FakeDrive:
    def __init__(self):
        self.files = {}      # id -> {name, data, parent, trashed, revisions}
        self.sessions = {}   # session url -> {fid, size, buf, done}
        self.http_calls = []
        self.api_calls = []
        self.corrupt = False       # store a flipped last byte: md5 read back will not match
        self.drop_on_chunk = set()  # 1-based chunk numbers whose PUT drops the connection
        self.chunks = 0

    def add(self, fid, name, data, parent="PARENT1"):
        self.files[fid] = {"name": name, "data": data, "parent": parent, "trashed": False,
                           "revisions": 1}

    def meta(self, fid):
        f = self.files[fid]
        return {"id": fid, "name": f["name"], "size": str(len(f["data"])),
                "md5Checksum": hashlib.md5(f["data"]).hexdigest(), "trashed": f["trashed"],
                "parents": [f["parent"]], "mimeType": "application/x-tar"}

    # --- ilag_sync.api stand-in
    def api(self, url, *, method="GET", params=None, data=None, headers=None, timeout=300):
        self.api_calls.append((method, url, params, data))
        if url == db.s.DRIVE_FILES:
            assert method == "GET", "the tool never creates a Drive file"
            q = params["q"]
            parent = re.search(r"'([^']+)' in parents", q).group(1)
            name = re.search(r"name = '((?:[^'\\]|\\.)*)'", q).group(1).replace("\\'", "'")
            return {"files": [{"id": i, "name": f["name"]} for i, f in self.files.items()
                              if f["parent"] == parent and not f["trashed"] and f["name"] == name]}
        fid = url.rsplit("/", 1)[1]
        if fid not in self.files:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        if method == "GET":
            return self.meta(fid)
        if method == "PATCH":
            body = json.loads(data)
            assert set(body) == {"name"}, f"metadata PATCH may only rename, got {body}"
            self.files[fid]["name"] = body["name"]
            return {"id": fid, "name": body["name"]}
        raise AssertionError(f"unexpected {method} {url}")

    # --- drive_broken._http stand-in
    def http(self, method, url, *, headers=None, body=None, timeout=600):
        headers = dict(headers or {})
        self.http_calls.append((method, url, headers))
        if method == "PATCH":
            parts = urlsplit(url)
            assert url.startswith(db.s.DRIVE_UPLOAD + "/"), url
            assert parse_qs(parts.query)["uploadType"] == ["resumable"]
            fid = parts.path.rsplit("/", 1)[1]
            assert fid in self.files, "a revision goes onto an existing id"
            sess = f"https://upload.fake/session/{len(self.sessions)}"
            self.sessions[sess] = {"fid": fid, "size": int(headers["X-Upload-Content-Length"]),
                                   "buf": bytearray(), "done": False}
            return 200, {"Location": sess}, b""
        assert method == "PUT", method
        sess = self.sessions[url]
        rng = headers["Content-Range"]
        if rng.startswith("bytes */"):  # where did the upload stop?
            if sess["done"]:
                return 200, {}, json.dumps(self.meta(sess["fid"])).encode()
            got = len(sess["buf"])
            return 308, ({"Range": f"bytes=0-{got - 1}"} if got else {}), b""
        self.chunks += 1
        if self.chunks in self.drop_on_chunk:
            raise ConnectionResetError("peer reset mid-chunk")
        start = int(rng.split()[1].split("-")[0])
        assert start == len(sess["buf"]), f"chunk starts at {start}, Drive holds {len(sess['buf'])}"
        sess["buf"] += body
        if len(sess["buf"]) < sess["size"]:
            return 308, {"Range": f"bytes=0-{len(sess['buf']) - 1}"}, b""
        data = bytes(sess["buf"])
        if self.corrupt:
            data = data[:-1] + bytes([data[-1] ^ 0xFF])
        f = self.files[sess["fid"]]
        f["data"], f["revisions"], sess["done"] = data, f["revisions"] + 1, True
        return 200, {}, json.dumps(self.meta(sess["fid"])).encode()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("drive_broken tried a real network call")
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(db.s, "access_token", lambda: "test-token")


@pytest.fixture
def drive(tmp_path, monkeypatch):
    fake = FakeDrive()
    monkeypatch.setattr(db, "LEDGER", tmp_path / "state" / "drive-broken.jsonl")
    monkeypatch.setattr(db.s, "api", fake.api)
    monkeypatch.setattr(db, "_http", fake.http)
    monkeypatch.setattr(db, "CHUNK", 4)
    monkeypatch.setattr(db.time, "sleep", lambda _s: None)
    return fake


GOOD = b"the whole tar, all 36 bytes of it..."
SHORT = GOOD[:20]  # what a dead stream leaves behind under the real name


def ledger():
    if not db.LEDGER.exists():
        return []
    return [json.loads(l) for l in db.LEDGER.read_text().splitlines() if l.strip()]


def src_file(tmp_path, data=GOOD, name="backup.tar"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_mark_renames_and_records(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    src = src_file(tmp_path)
    assert db.main(["mark", "F1", "--source", str(src), "--why", "winbox went offline"]) == 0
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    (ev,) = ledger()
    assert ev["event"] == "mark" and ev["file_id"] == "F1" and ev["name"] == "backup.tar"
    assert ev["source"] == str(src) and ev["source_md5"] == hashlib.md5(GOOD).hexdigest()
    assert ev["size"] == len(GOOD) and ev["why"] == "winbox went offline"
    assert ev["when"] and ev["host"]
    assert ev["drive_md5"] == hashlib.md5(SHORT).hexdigest() and ev["drive_size"] == len(SHORT)


def test_mark_refuses_an_object_whose_md5_matches(tmp_path, drive):
    drive.add("F1", "backup.tar", GOOD)
    assert db.main(["mark", "F1", "--source", str(src_file(tmp_path))]) == 2
    assert drive.files["F1"]["name"] == "backup.tar"
    assert ledger() == []


def test_mark_with_source_gone_still_renames(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    assert db.main(["mark", "F1", "--source", str(tmp_path / "gone.tar")]) == 0
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    assert ledger()[0]["source_md5"] is None


def test_mark_twice_is_one_entry_and_one_prefix(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    src = src_file(tmp_path)
    db.main(["mark", "F1", "--source", str(src)])
    assert db.main(["mark", "F1", "--source", str(src)]) == 0
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    assert len(ledger()) == 1


def test_retry_uploads_a_revision_verifies_md5_and_renames_back(tmp_path, drive, capsys):
    drive.add("F1", "backup.tar", SHORT)
    db.main(["mark", "F1", "--source", str(src_file(tmp_path))])
    assert db.main(["retry"]) == 0
    f = drive.files["F1"]
    assert f["data"] == GOOD and f["name"] == "backup.tar" and f["revisions"] == 2
    assert list(drive.files) == ["F1"], "same id, no new file"
    patch = [c for c in drive.http_calls if c[0] == "PATCH"]
    assert len(patch) == 1 and "/upload/drive/v3/files/F1?" in patch[0][1]
    assert patch[0][2]["X-Upload-Content-Length"] == str(len(GOOD))
    assert drive.chunks == -(-len(GOOD) // db.CHUNK)  # chunked, every chunk sent once
    events = [e["event"] for e in ledger()]
    assert events == ["mark", "resolved"]
    assert ledger()[-1]["md5"] == hashlib.md5(GOOD).hexdigest()
    assert db.entries()["F1"]["status"] == "resolved"
    assert "RESOLVED" in capsys.readouterr().out


def test_retry_with_source_gone_leaves_it_broken(tmp_path, drive, capsys):
    drive.add("F1", "backup.tar", SHORT)
    src = src_file(tmp_path)
    db.main(["mark", "F1", "--source", str(src)])
    src.unlink()
    assert db.main(["retry"]) == 1
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    assert drive.files["F1"]["data"] == SHORT
    assert ledger()[-1]["result"] == "source-missing"
    assert db.entries()["F1"]["status"] == "open"
    assert not [c for c in drive.http_calls if c[0] == "PATCH"]
    assert "SOURCE-MISSING" in capsys.readouterr().out


def test_retry_with_a_folder_source_says_so(tmp_path, drive):
    drive.add("F1", "winbox-downloads.tar", SHORT)
    folder = tmp_path / "Downloads"
    folder.mkdir()
    db.main(["mark", "F1", "--source", str(folder), "--why", "tar stream died"])
    assert db.main(["retry"]) == 1
    assert ledger()[-1]["result"] == "source-not-file"
    assert drive.files["F1"]["name"] == "BROKEN-winbox-downloads.tar"


def test_retry_md5_mismatch_keeps_the_broken_name(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    db.main(["mark", "F1", "--source", str(src_file(tmp_path))])
    drive.corrupt = True
    assert db.main(["retry"]) == 1
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    ev = ledger()[-1]
    assert ev["event"] == "retry" and ev["result"] == "md5-mismatch"
    assert db.entries()["F1"]["status"] == "open"


def test_retry_dry_run_writes_nothing(tmp_path, drive, capsys):
    drive.add("F1", "backup.tar", SHORT)
    db.main(["mark", "F1", "--source", str(src_file(tmp_path))])
    before = db.LEDGER.read_text()
    assert db.main(["retry", "--dry-run"]) == 0
    assert db.LEDGER.read_text() == before
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    assert drive.http_calls == []
    assert len([c for c in drive.api_calls if c[0] == "PATCH"]) == 1  # the mark's rename only
    assert "WOULD-UPLOAD" in capsys.readouterr().out


def test_retry_resumes_after_a_dropped_chunk(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    db.main(["mark", "F1", "--source", str(src_file(tmp_path))])
    drive.drop_on_chunk = {3}
    assert db.main(["retry"]) == 0
    assert drive.files["F1"]["data"] == GOOD and drive.files["F1"]["name"] == "backup.tar"
    status_queries = [c for c in drive.http_calls
                      if c[0] == "PUT" and c[2]["Content-Range"].startswith("bytes */")]
    assert len(status_queries) == 1


def test_retry_skips_a_changed_source_unless_allowed(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    src = src_file(tmp_path)
    db.main(["mark", "F1", "--source", str(src)])
    src.write_bytes(GOOD + b"!")
    assert db.main(["retry"]) == 1
    assert ledger()[-1]["result"] == "source-changed"
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    assert db.main(["retry", "--allow-changed-source"]) == 0
    assert drive.files["F1"]["data"] == GOOD + b"!" and drive.files["F1"]["name"] == "backup.tar"


def test_retry_does_not_rename_onto_a_taken_name(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    db.main(["mark", "F1", "--source", str(src_file(tmp_path))])
    drive.add("F2", "backup.tar", b"someone re-uploaded")
    assert db.main(["retry"]) == 1
    assert drive.files["F1"]["data"] == GOOD
    assert drive.files["F1"]["name"] == "BROKEN-backup.tar"
    assert ledger()[-1]["result"] == "name-taken"


def test_retry_when_drive_already_holds_the_right_bytes(tmp_path, drive):
    drive.add("F1", "backup.tar", SHORT)
    db.main(["mark", "F1", "--source", str(src_file(tmp_path))])
    drive.files["F1"]["data"] = GOOD  # fixed by hand in between
    assert db.main(["retry"]) == 0
    assert drive.http_calls == []
    assert drive.files["F1"]["name"] == "backup.tar"
    assert ledger()[-1]["uploaded"] is False


def test_retry_id_filter_and_list(tmp_path, drive, capsys):
    drive.add("F1", "a.tar", SHORT)
    drive.add("F2", "b.tar", SHORT)
    db.main(["mark", "F1", "--source", str(src_file(tmp_path, name="a.tar"))])
    db.main(["mark", "F2", "--source", str(src_file(tmp_path, name="b.tar"))])
    assert db.main(["retry", "--id", "F2"]) == 0
    assert drive.files["F1"]["name"] == "BROKEN-a.tar" and drive.files["F2"]["name"] == "b.tar"
    capsys.readouterr()
    db.main(["list"])
    out = capsys.readouterr().out
    assert "F1" in out and "F2" not in out
    db.main(["list", "--all"])
    out = capsys.readouterr().out
    assert "F1" in out and "RESOLVED" in out and "F2" in out
    assert db.main(["retry", "--id", "NOPE"]) == 1


def test_upload_gives_up_on_an_expired_session(tmp_path, drive, monkeypatch):
    drive.add("F1", "backup.tar", SHORT)
    real = drive.http

    def expired(method, url, **kw):
        if method == "PUT":
            return 404, {}, b"session expired"
        return real(method, url, **kw)
    monkeypatch.setattr(db, "_http", expired)
    with pytest.raises(RuntimeError, match="404"):
        db.upload_revision("F1", src_file(tmp_path), "backup.tar", len(GOOD))


def test_help_names_every_verb(capsys):
    with pytest.raises(SystemExit) as e:
        db.main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    for verb in ("mark", "retry", "list", "NEW REVISION", "never trashes"):
        assert verb in out
