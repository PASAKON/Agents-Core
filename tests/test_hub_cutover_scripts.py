"""Tests for the Org Mesh W1.1 fixes to scripts/hub/cutover-mac.sh and
scripts/hub/contabo-cutover.sh (TASK.md, docs/design/tasks-db-hub.md §3.3).

No existing test of either script was found (grepped tests/ and scripts/
for "cutover-mac" / "contabo-cutover" before writing this) -- this is a new
file, not an extension.

Hard rule from the task brief: NEVER run either script against a real
ledger, the real Contabo box, or a real Postgres. This suite honours that
by construction, not just by omission:

  * scripts/hub/contabo-cutover.sh itself (the ssh transport) is never
    invoked -- its remote body was split out into scripts/hub/
    contabo-cutover-remote.sh specifically so it CAN be run directly, with
    ROOT/ENVF pointed at a throwaway git repo, with no ssh and no real
    Contabo box involved. See that file's own header for why.
  * scripts/hub/cutover-mac.sh is never invoked as a subprocess either: it
    resolves its own ROOT from BASH_SOURCE (two directories up from its own
    location on disk), so running the real file always operates on the
    real repo checkout regardless of any env var a test sets -- there is
    no safe way to sandbox it without copying the whole tree. Its fixes
    are proven instead by (a) directly testing the two pieces it now calls
    (scripts/hub/wal-checkpoint-archive.sh, scripts/hub/
    verify_migration_counts.py) in isolation, and (b) structural
    assertions on its own source (call order, set -e still present).
  * The row-count mismatch check (scripts/hub/verify_migration_counts.py)
    talks to Postgres via lib.db_pg/psycopg, which needs a real reachable
    server to test end-to-end -- none is available in this sandbox (no
    ORG_TEST_DB_URL, no local Postgres). It's tested at the function level
    instead (same technique scripts/hub/test_cutover_gate.py already uses:
    import the module, monkeypatch its I/O boundary functions,
    tests/hub/test_cutover_gate.py's _pid_alive/_pid_matches_task) --
    sqlite_counts() runs for real against a temp WAL-mode db (proving it
    reads WAL-resident rows correctly), pg_counts() is monkeypatched
    (this IS "stub psql/python" in spirit: it stubs the boundary that
    would otherwise hit a real Postgres, at the Python level since neither
    script actually shells out to the psql binary).
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HUB = ROOT / "scripts" / "hub"
CUTOVER_MAC = HUB / "cutover-mac.sh"
CONTABO_CUTOVER = HUB / "contabo-cutover.sh"
CONTABO_REMOTE = HUB / "contabo-cutover-remote.sh"
WAL_ARCHIVE = HUB / "wal-checkpoint-archive.sh"

sys.path.insert(0, str(ROOT))
from scripts.hub import verify_migration_counts as vmc  # noqa: E402


def _run(args: list[str], cwd: Path | None = None,
         env: dict[str, str] | None = None, timeout: float = 30) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd,
                           env=full_env, timeout=timeout)


# ============================================================== bash -n syntax

@pytest.mark.parametrize("script", [CUTOVER_MAC, CONTABO_CUTOVER, CONTABO_REMOTE, WAL_ARCHIVE])
def test_bash_syntax_ok(script):
    r = _run(["bash", "-n", str(script)])
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("script", [CUTOVER_MAC, CONTABO_CUTOVER, CONTABO_REMOTE])
def test_scripts_still_set_dash_e(script):
    # The safety net a mismatch/checkpoint refusal relies on to actually stop
    # the script (see module docstring: this is how "verify before archive"
    # is proven at the shell level without a real Postgres).
    text = script.read_text(encoding="utf-8")
    assert re.search(r"^set -\w*e\w*", text, re.MULTILINE), \
        f"{script.name} no longer has `set -e...` near the top"


# ===================================================== wal-checkpoint-archive.sh

def _make_wal_db(db_path: Path) -> sqlite3.Connection:
    """WAL-mode db with a row that exists ONLY in the -wal file (the
    connection is returned OPEN and idle -- closing it would auto-
    checkpoint, defeating the point of this fixture)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE foo (id INTEGER PRIMARY KEY, val TEXT)")
    conn.commit()
    conn.execute("INSERT INTO foo (id, val) VALUES (1, 'wal-only-row')")
    conn.commit()
    return conn


def test_archive_step_moves_wal_only_rows(tmp_path):
    db = tmp_path / "tasks.db"
    conn = _make_wal_db(db)
    try:
        assert (tmp_path / "tasks.db-wal").exists()
        archive = tmp_path / "tasks.db.archived-2026-09-28"

        r = _run(["bash", str(WAL_ARCHIVE), str(db), str(archive)])
        assert r.returncode == 0, r.stdout + r.stderr

        assert not db.exists(), "original path must be moved, not copied"
        assert archive.exists()

        ro = sqlite3.connect(f"file:{archive}?mode=ro", uri=True)
        try:
            row = ro.execute("SELECT val FROM foo WHERE id = 1").fetchone()
        finally:
            ro.close()
        assert row is not None and row[0] == "wal-only-row", \
            "the WAL-only row did not survive the archive step"
    finally:
        conn.close()


def test_archive_step_moves_wal_and_shm_together(tmp_path):
    db = tmp_path / "tasks.db"
    conn = _make_wal_db(db)
    try:
        archive = tmp_path / "tasks.db.archived-2026-09-28"
        r = _run(["bash", str(WAL_ARCHIVE), str(db), str(archive)])
        assert r.returncode == 0, r.stdout + r.stderr
        assert not (tmp_path / "tasks.db-wal").exists()
        assert not (tmp_path / "tasks.db-shm").exists()
        # After a successful TRUNCATE checkpoint the -wal is emptied before the
        # move, so its archived copy is optional -- what matters is nothing
        # was left behind next to the ORIGINAL path under the old name.
    finally:
        conn.close()


def test_missing_db_refuses_without_touching_archive_path(tmp_path):
    db = tmp_path / "tasks.db"
    archive = tmp_path / "tasks.db.archived-2026-09-28"
    r = _run(["bash", str(WAL_ARCHIVE), str(db), str(archive)])
    assert r.returncode != 0
    assert not archive.exists()


def test_busy_checkpoint_refuses_and_leaves_original_in_place(tmp_path):
    db = tmp_path / "tasks.db"
    writer = _make_wal_db(db)
    # A second connection holding an open READ transaction blocks a full
    # TRUNCATE checkpoint (measured: PRAGMA wal_checkpoint(TRUNCATE) then
    # reports busy=1, exit code still 0 -- the retry loop must catch this
    # from the pragma's own result row, not from sqlite3's exit status).
    blocker = sqlite3.connect(str(db))
    blocker.execute("BEGIN")
    blocker.execute("SELECT * FROM foo")
    try:
        archive = tmp_path / "tasks.db.archived-2026-09-28"
        start = time.monotonic()
        r = _run(["bash", str(WAL_ARCHIVE), str(db), str(archive)], timeout=30)
        elapsed = time.monotonic() - start

        assert r.returncode != 0, r.stdout + r.stderr
        assert "REFUSING" in r.stderr
        assert elapsed >= 4, "must retry a few times, not fail on the first busy result"
        assert db.exists(), "original db must still be at its original path"
        assert not archive.exists(), "must never move a half-checkpointed db"
    finally:
        blocker.close()
        writer.close()


# ==================================================== verify_migration_counts.py

def test_find_mismatches_all_equal_is_empty():
    counts = {"tasks": 10, "c_level_sessions": 3, "events": 50, "locks": 0}
    assert vmc.find_mismatches(counts, dict(counts)) == []


def test_find_mismatches_reports_every_differing_table():
    before = {"tasks": 10, "c_level_sessions": 3, "events": 50, "locks": 0}
    after = {"tasks": 9, "c_level_sessions": 3, "events": 51, "locks": 0}
    assert set(vmc.find_mismatches(before, after)) == {"tasks", "events"}


def test_find_mismatches_missing_table_counts_as_mismatch():
    before = {"tasks": 10, "c_level_sessions": 3, "events": 50}
    after = {"tasks": 10, "c_level_sessions": 3}  # events missing
    assert vmc.find_mismatches(before, after) == ["events"]


def test_main_mismatch_exits_nonzero_and_prints_both_sets(monkeypatch, capsys):
    before = {"tasks": 10, "c_level_sessions": 3, "events": 50, "locks": 0}
    after = {"tasks": 8, "c_level_sessions": 3, "events": 50, "locks": 0}
    monkeypatch.setattr(vmc, "sqlite_counts", lambda path: before)
    monkeypatch.setattr(vmc, "pg_counts", lambda url: after)

    rc = vmc.main(["--sqlite", "ignored.db", "--pg", "postgresql://ignored/db"])

    assert rc == 1
    out, err = capsys.readouterr()
    assert "sqlite=10" in out and "postgres=8" in out
    assert "tasks" in err and "REFUSING" in err


def test_main_matching_counts_exits_zero(monkeypatch, capsys):
    counts = {"tasks": 10, "c_level_sessions": 3, "events": 50, "locks": 0}
    monkeypatch.setattr(vmc, "sqlite_counts", lambda path: dict(counts))
    monkeypatch.setattr(vmc, "pg_counts", lambda url: dict(counts))

    rc = vmc.main(["--sqlite", "ignored.db", "--pg", "postgresql://ignored/db"])

    assert rc == 0


def test_sqlite_counts_reads_wal_resident_rows_for_real(tmp_path):
    # Real I/O against a real WAL-mode db (no Postgres involved) -- proves
    # the "before" snapshot used by both cutover scripts isn't blind to
    # rows still sitting in the WAL at the point counts are taken.
    db = tmp_path / "tasks.db"
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL;")
    for table in vmc.TABLES:
        conn.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.execute("INSERT INTO tasks (id) VALUES (1)")
    conn.execute("INSERT INTO tasks (id) VALUES (2)")
    conn.execute("INSERT INTO events (id) VALUES (1)")
    conn.commit()  # WAL-resident; connection stays open, not checkpointed
    try:
        counts = vmc.sqlite_counts(str(db))
        assert counts == {"tasks": 2, "c_level_sessions": 0, "events": 1}
    finally:
        conn.close()


# =============================================== cutover script call ordering

def test_cutover_mac_verifies_counts_before_archiving():
    text = CUTOVER_MAC.read_text(encoding="utf-8")
    verify_at = text.index("verify_migration_counts.py")
    archive_at = text.index("wal-checkpoint-archive.sh")
    assert verify_at < archive_at, \
        "counts must be verified before state/tasks.db is archived"


def test_contabo_remote_verifies_counts_before_archiving():
    text = CONTABO_REMOTE.read_text(encoding="utf-8")
    verify_at = text.index("verify_migration_counts.py")
    archive_at = text.index("wal-checkpoint-archive.sh")
    assert verify_at < archive_at, \
        "counts must be verified before state/tasks.db is archived"


def test_neither_script_moves_only_the_main_db_file_by_hand():
    # The bug this whole task closes: a bare `mv state/tasks.db ...` with no
    # checkpoint and no -wal/-shm move alongside it.
    for script in (CUTOVER_MAC, CONTABO_REMOTE):
        text = script.read_text(encoding="utf-8")
        assert not re.search(r"^\s*mv\s+state/tasks\.db\s", text, re.MULTILINE), \
            f"{script.name} still moves tasks.db by hand instead of via wal-checkpoint-archive.sh"


def test_contabo_remote_no_longer_deletes_wal_shm():
    # The old step 6 did `rm -f state/tasks.db-wal state/tasks.db-shm` --
    # discarding, not archiving, anything still in the WAL.
    text = CONTABO_REMOTE.read_text(encoding="utf-8")
    assert "rm -f state/tasks.db-wal" not in text
    assert "rm -f state/tasks.db-shm" not in text


def test_neither_script_uses_checkout_dash_capital_b():
    for script in (CUTOVER_MAC, CONTABO_CUTOVER, CONTABO_REMOTE):
        text = script.read_text(encoding="utf-8")
        assert not re.search(r"checkout\s+-q?\s*-B\b", text), \
            f"{script.name} still force-resets a branch with checkout -B"


# ============================================== contabo-cutover-remote.sh: git

def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)} failed: {r.stdout}{r.stderr}"
    return r


@pytest.fixture
def repo(tmp_path):
    """A bare 'origin' plus a 'work' clone (this is ROOT for the script under
    test) with an initial commit already pushed to both. work/state/
    machine-discovered-contabo.yaml exists and is tracked, mirroring the
    real Contabo checkout's weekly-rewritten file."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "Test")
    (work / "state").mkdir()
    (work / "state" / "machine-discovered-contabo.yaml").write_text("host: contabo\n")
    (work / "README.md").write_text("hello\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "init")
    _git(work, "push", "-q", "origin", "main")
    return origin, work


def _run_remote(root: Path, timeout: float = 15) -> subprocess.CompletedProcess:
    env = {
        "ROOT": str(root),
        "ENVF": str(root / "does-not-exist.env"),
        "FLAG": "--sessions-closed",  # never depend on this box's real tmux state
    }
    return _run(["bash", str(CONTABO_REMOTE)], env=env, timeout=timeout)


def test_dirty_machine_discovered_file_alone_is_not_a_refusal(repo):
    _origin, work = repo
    (work / "state" / "machine-discovered-contabo.yaml").write_text("host: contabo\nrescanned: true\n")

    r = _run_remote(work)

    assert "REFUSING: tracked files are dirty" not in r.stdout
    assert "ok: ignoring machine_doctor" in r.stdout


def test_dirty_other_tracked_file_still_refuses(repo):
    _origin, work = repo
    (work / "README.md").write_text("hello, changed\n")

    r = _run_remote(work)

    assert r.returncode != 0
    assert "REFUSING: tracked files are dirty" in r.stdout
    assert "README.md" in r.stdout
    assert "== step 3:" not in r.stdout, "must refuse before doing anything past step 2"


def test_dirty_machine_discovered_plus_another_file_still_refuses(repo):
    _origin, work = repo
    (work / "state" / "machine-discovered-contabo.yaml").write_text("host: contabo\nrescanned: true\n")
    (work / "README.md").write_text("hello, changed\n")

    r = _run_remote(work)

    assert r.returncode != 0
    assert "REFUSING: tracked files are dirty" in r.stdout
    assert "README.md" in r.stdout


def test_clean_fast_forward_succeeds_and_moves_main(repo):
    origin, work = repo
    # A second clone pushes a new commit to origin -- work's local main is a
    # strict ancestor of it, so `git merge --ff-only` must succeed.
    other = work.parent / "other"
    subprocess.run(["git", "clone", "-q", str(origin), str(other)], check=True)
    _git(other, "config", "user.email", "test@example.invalid")
    _git(other, "config", "user.name", "Test")
    (other / "README.md").write_text("hello, from origin\n")
    _git(other, "commit", "-aq", "-m", "origin moves forward")
    _git(other, "push", "-q", "origin", "main")
    expected_tip = _git(other, "rev-parse", "HEAD").stdout.strip()

    r = _run_remote(work)

    assert "REFUSING: local main is not fast-forwardable" not in r.stdout
    assert f"main now at: {expected_tip[:7]}" in r.stdout or expected_tip[:7] in r.stdout
    tip = _git(work, "rev-parse", "main").stdout.strip()
    assert tip == expected_tip


def test_non_ff_checkout_refuses_and_keeps_local_commit(repo):
    origin, work = repo
    # Diverge: a second clone pushes its own commit to origin...
    other = work.parent / "other"
    subprocess.run(["git", "clone", "-q", str(origin), str(other)], check=True)
    _git(other, "config", "user.email", "test@example.invalid")
    _git(other, "config", "user.name", "Test")
    (other / "README.md").write_text("hello, from origin\n")
    _git(other, "commit", "-aq", "-m", "origin moves forward")
    _git(other, "push", "-q", "origin", "main")

    # ...while work makes its OWN local commit that was never pushed --
    # this is exactly the "local commits not yet in origin" case the old
    # `checkout -B main origin/main` would have silently discarded.
    (work / "NOTES.md").write_text("local work in progress\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "local-only commit")
    local_tip_before = _git(work, "rev-parse", "main").stdout.strip()

    r = _run_remote(work)

    assert r.returncode != 0
    assert "REFUSING: local main is not fast-forwardable" in r.stdout

    tip_after = _git(work, "rev-parse", "main").stdout.strip()
    assert tip_after == local_tip_before, \
        "main must be untouched -- the local-only commit must not be discarded"
    assert (work / "NOTES.md").exists(), "the local-only commit's file must still be present"

    # A backup branch was still made, even though nothing needed rolling
    # back from (defence in depth, matches the old script's intent).
    branches = _git(work, "branch", "--list", "backup/main-before-hub-*").stdout
    assert "backup/main-before-hub-" in branches
