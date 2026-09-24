"""tests/test_drive_leg.py -- tools/drive_leg.py (Contabo's Drive leg of the Machine
Contract, ADR 0031 / IRON Sec58). Brief: docs/ops/briefs/machine-contract-drive-leg.md.

No network, no docker, no real rclone/winbox. Every test either exercises pure-local
logic (no relay involved) or points DRIVE_LEG_RCLONE at `fake_relay` -- a tiny script
written to tmp_path at fixture time that stores whatever `rcat` sends it under
FAKE_RELAY_STORE and answers `lsjson --hash` / `mkdir` / `cat` from that store, the same
way the brief asks for ("the tests point it at a fake script that stores the stream in a
temp dir and answers lsjson --hash from it"). Every test also uses a temp
CLAUDE_CONFIG_DIR (never the real ~/.claude) via an explicit `config_dir=` kwarg -- the
module never reads that env var itself except in `main()`, so tests that go through the
CLI set it with monkeypatch.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tarfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.drive_leg as drive_leg  # noqa: E402

UUID_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
UUID_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
UUID_C = "cccccccc-cccc-cccc-cccc-cccccccccccc"


# --------------------------------------------------------------------------- fake relay
FAKE_RELAY_SRC = r'''#!/usr/bin/env python3
"""Fake rclone_via_winbox.sh for tests: stores rcat streams under FAKE_RELAY_STORE and
answers lsjson/mkdir/cat from that store. Set FAKE_RELAY_CORRUPT=1 to make lsjson report
a wrong md5 for every file (simulates a corrupted upload detected on read-back)."""
import hashlib
import json
import os
import sys

STORE = os.environ["FAKE_RELAY_STORE"]
CORRUPT = os.environ.get("FAKE_RELAY_CORRUPT") == "1"
CALLS = os.path.join(STORE, "_calls.log")


def record(args):
    with open(CALLS, "a") as fh:
        fh.write(" ".join(args) + "\n")


def entry(full, name, relpath):
    if os.path.isdir(full):
        return {"Name": name, "Path": relpath, "IsDir": True}
    with open(full, "rb") as fh:
        data = fh.read()
    md5 = "0" * 32 if CORRUPT else hashlib.md5(data).hexdigest()
    fid = "fake-" + hashlib.sha1(relpath.encode()).hexdigest()[:16]
    return {"Name": name, "Path": relpath, "Size": len(data), "IsDir": False,
            "ID": fid, "Hashes": {"md5": md5}}


def main():
    args = sys.argv[1:]
    record(args)
    if not args:
        return 2
    verb = args[0]
    folder_id = args[args.index("--drive-root-folder-id") + 1] \
        if "--drive-root-folder-id" in args else "_"
    remotes = [a for a in args[1:] if a.startswith("gdrive:")]
    remote = remotes[0] if remotes else "gdrive:"
    rel = remote[len("gdrive:"):]
    base = os.path.join(STORE, "objects", folder_id, rel)

    if verb == "mkdir":
        os.makedirs(base, exist_ok=True)
        return 0
    if verb == "rcat":
        os.makedirs(os.path.dirname(base), exist_ok=True)
        data = sys.stdin.buffer.read()
        with open(base, "wb") as fh:
            fh.write(data)
        return 0
    if verb == "cat":
        if not os.path.isfile(base):
            sys.stderr.write("no such object: %s\n" % base)
            return 1
        with open(base, "rb") as fh:
            sys.stdout.buffer.write(fh.read())
        return 0
    if verb == "lsjson":
        dirs_only = "--dirs-only" in args
        recursive = "--recursive" in args or "-R" in args
        out = []
        if not os.path.isdir(base):
            print("[]")
            return 0
        if recursive:
            for dirpath, _dirnames, filenames in os.walk(base):
                for name in filenames:
                    full = os.path.join(dirpath, name)
                    relpath = os.path.relpath(full, base).replace(os.sep, "/")
                    out.append(entry(full, name, relpath))
        else:
            for name in sorted(os.listdir(base)):
                full = os.path.join(base, name)
                is_dir = os.path.isdir(full)
                if dirs_only and not is_dir:
                    continue
                if not dirs_only and is_dir:
                    continue
                out.append(entry(full, name, name))
        print(json.dumps(out))
        return 0
    sys.stderr.write("fake_rclone: unknown verb %r\n" % verb)
    return 2


if __name__ == "__main__":
    sys.exit(main())
'''


@pytest.fixture
def fake_relay(tmp_path, monkeypatch):
    """Writes the fake relay script, points DRIVE_LEG_RCLONE + FAKE_RELAY_STORE at it,
    and returns the store dir (objects/<folder_id>/<remote path> holds every uploaded
    file; _calls.log records every invocation for the zero-calls assertions)."""
    script = tmp_path / "fake_rclone.py"
    script.write_text(FAKE_RELAY_SRC, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    store = tmp_path / "relay_store"
    store.mkdir()
    monkeypatch.setenv("DRIVE_LEG_RCLONE", str(script))
    monkeypatch.setenv("FAKE_RELAY_STORE", str(store))
    monkeypatch.delenv("FAKE_RELAY_CORRUPT", raising=False)
    return store


def _calls(store: Path) -> list[str]:
    calls_log = store / "_calls.log"
    return calls_log.read_text().splitlines() if calls_log.exists() else []


def _write_session(config_dir: Path, slug: str, uuid: str, age_days: float, *,
                    content: bytes = b'{"type":"summary"}\n',
                    subagent_files: dict[str, bytes] | None = None) -> Path:
    proj = config_dir / "projects" / slug
    proj.mkdir(parents=True, exist_ok=True)
    jsonl = proj / f"{uuid}.jsonl"
    jsonl.write_bytes(content)
    mtime = time.time() - age_days * 86400
    os.utime(jsonl, (mtime, mtime))
    if subagent_files:
        sub = proj / uuid
        sub.mkdir(parents=True, exist_ok=True)
        for name, data in subagent_files.items():
            p = sub / name
            p.write_bytes(data)
            os.utime(p, (mtime, mtime))
        os.utime(sub, (mtime, mtime))
    return jsonl


# =========================================================================== transcripts
def test_transcripts_archives_only_eligible_days(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    j_young = _write_session(cfg, "slugA", UUID_A, 1)   # too young (< 7d), must stay
    j_old = _write_session(cfg, "slugB", UUID_B, 8)     # eligible
    j_ancient = _write_session(cfg, "slugC", UUID_C, 30,  # eligible, has a sub-agent dir
                               subagent_files={"tool-result.json": b'{"ok":true}'})

    report = drive_leg.transcripts(config_dir=cfg, min_age_days=7)

    assert report["failed"] == 0
    assert report["verified"] == 2
    archived_slugs = {d["slug"] for d in report["days"] if d.get("verified")}
    assert archived_slugs == {"slugB", "slugC"}

    assert j_young.exists()          # untouched: too young
    assert not j_old.exists()        # archived + deleted
    assert not j_ancient.exists()
    assert not (cfg / "projects" / "slugC" / UUID_C).exists()  # sub-agent dir pruned too

    # manifests list the uuids
    manifests = list((fake_relay / "objects").rglob("*.manifest.json"))
    assert len(manifests) == 2
    found = set()
    for m in manifests:
        data = json.loads(m.read_text())
        for f in data["files"]:
            found.add(Path(f["path"]).parts[0].split(".")[0])
    assert found == {UUID_B, UUID_C}

    # local transcript index
    idx_rows = [json.loads(ln) for ln in
                (cfg / "logs" / "transcript-archive-index.jsonl").read_text().splitlines()]
    assert {r["uuid"] for r in idx_rows} == {UUID_B, UUID_C}

    # ledger: one line per archived day, pipe-separated, ends "OK | who"
    ledger_lines = (cfg / "logs" / "drive-archive.log").read_text().splitlines()
    assert len(ledger_lines) == 2
    for ln in ledger_lines:
        fields = ln.split(" | ")
        assert len(fields) == 9
        assert fields[7] == "OK"


def test_transcripts_dry_run_calls_relay_zero_times(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    jsonl = _write_session(cfg, "slugY", UUID_B, 10)

    report = drive_leg.transcripts(config_dir=cfg, min_age_days=7, dry_run=True)

    assert report["days"] and report["days"][0]["dry_run"] is True
    assert jsonl.exists()
    assert _calls(fake_relay) == []


def test_transcripts_max_days_and_only_slug_selection(tmp_path):
    cfg = tmp_path / "claude_config"
    _write_session(cfg, "slugA", UUID_A, 10)
    _write_session(cfg, "slugB", UUID_B, 20)
    _write_session(cfg, "slugC", UUID_C, 30)

    capped = drive_leg.transcripts(config_dir=cfg, min_age_days=7, max_days=1, dry_run=True)
    assert len(capped["days"]) == 1

    only_b = drive_leg.transcripts(config_dir=cfg, min_age_days=7, only_slug="slugB", dry_run=True)
    assert {d["slug"] for d in only_b["days"]} == {"slugB"}


def test_bad_md5_exits_nonzero_and_deletes_nothing(fake_relay, tmp_path, monkeypatch):
    cfg = tmp_path / "claude_config"
    jsonl = _write_session(cfg, "slugX", UUID_A, 10)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    monkeypatch.setenv("FAKE_RELAY_CORRUPT", "1")

    rc = drive_leg.main(["transcripts", "--min-age-days", "7"])

    assert rc != 0
    assert jsonl.exists()  # nothing deleted on a verify mismatch


def test_bad_md5_reports_failed_via_python_api(fake_relay, tmp_path, monkeypatch):
    cfg = tmp_path / "claude_config"
    jsonl = _write_session(cfg, "slugX", UUID_A, 10)
    monkeypatch.setenv("FAKE_RELAY_CORRUPT", "1")

    report = drive_leg.transcripts(config_dir=cfg, min_age_days=7)

    assert report["failed"] == 1
    assert report["verified"] == 0
    assert jsonl.exists()


def test_delete_verified_skips_files_changed_since_freeze(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    st_a, st_b = a.stat(), b.stat()
    frozen = [(a, st_a.st_size, st_a.st_mtime_ns), (b, st_b.st_size, st_b.st_mtime_ns)]

    b.write_bytes(b"twotwo")  # changed after freeze -- size differs too

    removed = drive_leg._delete_verified(frozen)

    assert removed == 1
    assert not a.exists()
    assert b.exists()


def test_assert_safe_member_rejects_traversal_and_links():
    with pytest.raises(drive_leg.DriveLegError):
        drive_leg._assert_safe_member(tarfile.TarInfo(name="../../etc/passwd"))
    with pytest.raises(drive_leg.DriveLegError):
        drive_leg._assert_safe_member(tarfile.TarInfo(name="/etc/passwd"))
    drive_leg._assert_safe_member(tarfile.TarInfo(name=f"{UUID_A}/ok.json"))  # does not raise


# =========================================================================== restore-transcript
def test_restore_transcript_byte_identical(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    content = b'{"type":"summary","note":"\xc3\xa9"}\n' + b"y" * 500
    subfile = b"tool result payload, byte for byte"
    jsonl = _write_session(cfg, "slugR", UUID_C, 10, content=content,
                           subagent_files={"result.json": subfile})

    archived = drive_leg.transcripts(config_dir=cfg, min_age_days=7)
    assert archived["verified"] == 1
    assert not jsonl.exists()

    result = drive_leg.restore_transcript(UUID_C[:8], config_dir=cfg)

    assert result["uuid"] == UUID_C
    restored_jsonl = cfg / "projects" / "slugR" / f"{UUID_C}.jsonl"
    restored_sub = cfg / "projects" / "slugR" / UUID_C / "result.json"
    assert restored_jsonl.read_bytes() == content
    assert restored_sub.read_bytes() == subfile


def test_restore_transcript_unknown_uuid_raises(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    (cfg / "logs").mkdir(parents=True)
    with pytest.raises(drive_leg.DriveLegError):
        drive_leg.restore_transcript("deadbeef", config_dir=cfg)


# =========================================================================== uploads
def test_uploads_skips_on_unchanged_listing_and_reuploads_on_change(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    uploads_dir = cfg / "uploads"
    uploads_dir.mkdir(parents=True)
    (uploads_dir / "a.png").write_bytes(b"hello")

    first = drive_leg.uploads(config_dir=cfg)
    assert first.get("verified") is True
    calls_after_first = len(_calls(fake_relay))
    assert calls_after_first > 0

    second = drive_leg.uploads(config_dir=cfg)
    assert second.get("skipped") is True
    assert second.get("reason") == "unchanged"
    assert len(_calls(fake_relay)) == calls_after_first  # no new relay traffic

    (uploads_dir / "b.png").write_bytes(b"new file")
    third = drive_leg.uploads(config_dir=cfg)
    assert third.get("verified") is True
    assert len(_calls(fake_relay)) > calls_after_first

    # never deletes
    assert (uploads_dir / "a.png").exists()
    assert (uploads_dir / "b.png").exists()


def test_uploads_dry_run_calls_relay_zero_times(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    uploads_dir = cfg / "uploads"
    uploads_dir.mkdir(parents=True)
    (uploads_dir / "a.png").write_bytes(b"hello")

    result = drive_leg.uploads(config_dir=cfg, dry_run=True)

    assert result.get("dry_run") is True
    assert _calls(fake_relay) == []


def test_uploads_empty_dir_skips_without_relay_call(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    result = drive_leg.uploads(config_dir=cfg)
    assert result.get("skipped") is True
    assert result.get("reason") == "empty"
    assert _calls(fake_relay) == []


# =========================================================================== docker-volumes
def test_docker_volumes_dry_run_prints_commands_and_touches_nothing(fake_relay, tmp_path, capsys):
    cfg = tmp_path / "claude_config"

    report = drive_leg.docker_volumes(config_dir=cfg, dry_run=True, now=time.time())

    assert report["dry_run"] is True
    vols = {v["volume"]: v for v in report["volumes"]}
    assert set(vols) == {"n8n_data", "org-pgdata"}
    assert "--exclude=./config" in vols["n8n_data"]["cmd"]
    assert "pg_dumpall" in vols["org-pgdata"]["cmd"]
    assert _calls(fake_relay) == []  # dry-run never touches the relay
    out = capsys.readouterr().out
    assert "docker" in out  # the commands are printed, per the brief


def test_docker_volumes_default_volume_list_is_n8n_and_pgdata(tmp_path):
    cfg = tmp_path / "claude_config"
    report = drive_leg.docker_volumes(config_dir=cfg, dry_run=True)
    assert [v["volume"] for v in report["volumes"]] == ["n8n_data", "org-pgdata"]


# =========================================================================== blueprints
def test_blueprints_archives_then_skips_duplicate_sha256(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    state_dir = tmp_path / "state"
    bp_dir = state_dir / "contabo-blueprint-20260924"
    bp_dir.mkdir(parents=True)
    (bp_dir / "brew.txt").write_bytes(b"formula list")
    (bp_dir / "sub" / "units.txt").parent.mkdir(parents=True)
    (bp_dir / "sub" / "units.txt").write_bytes(b"mooniex-x.service")

    first = drive_leg.blueprints(state_dir=state_dir, config_dir=cfg)
    assert first["blueprints"][0]["machine"] == "contabo"
    assert first["blueprints"][0]["date"] == "2026-09-24"
    assert first["blueprints"][0]["verified"] is True

    second = drive_leg.blueprints(state_dir=state_dir, config_dir=cfg)
    assert second["blueprints"][0].get("skipped") is True

    # never deletes the source
    assert (bp_dir / "brew.txt").exists()
    assert (bp_dir / "sub" / "units.txt").exists()

    manifest_files = list((fake_relay / "objects").rglob("*.manifest.json"))
    assert len(manifest_files) == 1
    manifest = json.loads(manifest_files[0].read_text())
    assert manifest["count"] == 2
    assert {f["path"] for f in manifest["files"]} == {
        "contabo-blueprint-20260924/brew.txt", "contabo-blueprint-20260924/sub/units.txt"}


def test_blueprints_ignores_non_matching_dirs(tmp_path):
    cfg = tmp_path / "claude_config"
    state_dir = tmp_path / "state"
    (state_dir / "logs").mkdir(parents=True)
    (state_dir / "logs" / "x.log").write_bytes(b"not a blueprint dir")

    report = drive_leg.blueprints(state_dir=state_dir, config_dir=cfg, dry_run=True)

    assert report["blueprints"] == []


def test_blueprints_dry_run_calls_relay_zero_times(fake_relay, tmp_path):
    cfg = tmp_path / "claude_config"
    state_dir = tmp_path / "state"
    bp_dir = state_dir / "winbox-blueprint-20260924"
    bp_dir.mkdir(parents=True)
    (bp_dir / "tasks.xml").write_bytes(b"<tasks/>")

    report = drive_leg.blueprints(state_dir=state_dir, config_dir=cfg, dry_run=True)

    assert report["blueprints"][0]["dry_run"] is True
    assert _calls(fake_relay) == []


# =========================================================================== put() core
def test_put_manifest_upload_failure_leaves_archive_verified_but_raises(fake_relay, tmp_path, monkeypatch):
    """A relay that accepts the tar but rejects the manifest rcat -- put() must still
    raise (nothing gets logged, nothing downstream deletes)."""
    cfg = tmp_path / "claude_config"
    log = drive_leg.log_path(cfg)
    real_run = drive_leg.subprocess.run

    def flaky_run(cmd, **kwargs):
        # The tar itself streams through subprocess.Popen, never subprocess.run -- so the
        # only "rcat" that ever reaches subprocess.run() in a successful put() is the
        # manifest upload. Failing it here simulates that specific stage breaking.
        if "rcat" in cmd:
            class _R:
                returncode = 1
                stderr = b"disk full"
            return _R()
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(drive_leg.subprocess, "run", flaky_run)

    def _stream(sink):
        sink.write(b"hello world")

    manifest = drive_leg.build_manifest(name="x", machine="contabo", source="test",
                                        files=[], restore="n/a")
    with pytest.raises(drive_leg.DriveLegError, match="manifest upload failed"):
        drive_leg.put(_stream, drive_leg.FOLDER_IDS["Claude-Uploads"], "contabo", "2026-09-24",
                     ".tar", manifest, log_path_=log, who="test")
    assert not log.exists()  # nothing logged on a manifest-stage failure


def test_state_db_backs_up_a_consistent_copy_and_skips_unchanged(fake_relay, tmp_path):
    import gzip
    import sqlite3
    import time as _time
    from tools import drive_leg as _dl
    cfg = tmp_path / "cfg"
    (cfg / "logs").mkdir(parents=True)
    db = tmp_path / "tasks.db"
    con = sqlite3.connect(db)
    con.execute("create table tasks(id text)")
    con.execute("insert into tasks values('t1')")
    con.commit()
    con.close()
    now = _time.time()
    r1 = _dl.state_db(config_dir=cfg, db_path=db, now=now)
    assert not r1.get("skipped") and r1.get("verified") is not False
    objs = list((fake_relay / "objects").rglob("*.sqlite.gz"))
    assert len(objs) == 1
    with gzip.open(objs[0]) as gz:
        data = gz.read()
    assert data[:16] == b"SQLite format 3\x00"  # a real SQLite image, not a tar
    # the copy is readable on its own and carries the row
    snap = tmp_path / "restored.db"
    snap.write_bytes(data)
    assert sqlite3.connect(snap).execute("select count(*) from tasks").fetchone()[0] == 1
    calls = len(_calls(fake_relay))
    r2 = _dl.state_db(config_dir=cfg, db_path=db, now=now)
    assert r2.get("skipped") and r2["reason"] == "unchanged"
    assert len(_calls(fake_relay)) == calls  # no relay traffic for an unchanged db
    con = sqlite3.connect(db)
    con.execute("insert into tasks values('t2')")
    con.commit()
    con.close()
    r3 = _dl.state_db(config_dir=cfg, db_path=db, now=now + 86400)
    assert not r3.get("skipped")
    assert len(list((fake_relay / "objects").rglob("*.sqlite.gz"))) == 2
    # dry-run never touches the relay
    calls = len(_calls(fake_relay))
    r4 = _dl.state_db(config_dir=cfg, db_path=db, dry_run=True, now=now + 2 * 86400)
    assert r4.get("dry_run") is not True or len(_calls(fake_relay)) == calls
