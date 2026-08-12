"""Tests for tools/terminal_restart.py, the shared logic behind
scripts/terminal-restart.sh and scripts/session-restart.sh (task-b0b3f602).

No real tmux session and no real claude process: tmux (`tmux respawn-pane`,
`tmux list-panes`), `pgrep`/`ps` process lookups, and `time.sleep` are all
stubbed. Style follows scripts/test_watchdog_reap.py: plain functions +
_mark + a counting main().

Tests:
  1. refuses when the .uuid file is missing
  2. refuses when the session owns an in_progress task
  3. refuses when it owns a pending task
  4. --force overrides the owns-live-work refusal (and says what it overrode)
  5. builds a run-file containing -r <uuid> and the original env
  6. issues respawn-pane -k against the right target, and never kill-session
  7. session-restart's capture survives a simulated reap_locks
  8. the verify step reports failure when no claude is found afterwards

Run via: python scripts/test_terminal_restart.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid as uuid_mod
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.terminal_restart as tr  # noqa: E402
from tools import session_name  # noqa: E402

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _fresh_locks_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="terminal-restart-locks-"))


def _write_uuid(locks_dir: Path, name: str) -> str:
    u = str(uuid_mod.uuid4())
    (locks_dir / f"{name}.uuid").write_text(u + "\n")
    return u


def _insert_task(*, status: str, owner_cto: str, project: str = "test-proj") -> str:
    tid = "task-" + uuid_mod.uuid4().hex[:8]
    ts = db_mod.now_iso()
    with db_mod.get_conn() as conn:
        conn.execute(
            """INSERT INTO tasks
               (id, project, role, status, title, description, pid,
                depends_on, touches, owner_cto, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, project, "developer", status, "t", "d", None,
             "[]", "[]", owner_cto, ts, ts),
        )
    return tid


# ---------------------------------------------------------------------------
# 1. missing .uuid
# ---------------------------------------------------------------------------

def test_refuses_missing_uuid() -> bool:
    locks_dir = _fresh_locks_dir()
    result = tr.evaluate("cto-nouuid1", locks_dir)
    return (result["ok"] is False and result["uuid"] is None
           and "amnesia" in result["reason"])


# ---------------------------------------------------------------------------
# 2-3. owns live work (in_progress / pending)
# ---------------------------------------------------------------------------

def test_refuses_in_progress_owner() -> bool:
    locks_dir = _fresh_locks_dir()
    name = "cto-abc12345"
    _write_uuid(locks_dir, name)
    sid = session_name.id_from_tmux_session(name)
    tid = _insert_task(status="in_progress", owner_cto=sid)
    result = tr.evaluate(name, locks_dir)
    return (result["ok"] is False and result["overridden"] is None
           and tid in result["reason"])


def test_refuses_pending_owner() -> bool:
    locks_dir = _fresh_locks_dir()
    name = "cto-abc22222"
    _write_uuid(locks_dir, name)
    sid = session_name.id_from_tmux_session(name)
    tid = _insert_task(status="pending", owner_cto=sid)
    result = tr.evaluate(name, locks_dir)
    return (result["ok"] is False and tid in result["reason"]
           and "--force" in result["reason"])


# ---------------------------------------------------------------------------
# 4. --force overrides, and says what it overrode
# ---------------------------------------------------------------------------

def test_force_overrides_live_work() -> bool:
    locks_dir = _fresh_locks_dir()
    name = "cto-abc33333"
    _write_uuid(locks_dir, name)
    sid = session_name.id_from_tmux_session(name)
    tid = _insert_task(status="blocked_human", owner_cto=sid)
    result = tr.evaluate(name, locks_dir, force=True)
    return (result["ok"] is True and result["reason"] is None
           and result["overridden"] is not None and tid in result["overridden"])


# ---------------------------------------------------------------------------
# 5. run-file: -r <uuid> + original env preserved
# ---------------------------------------------------------------------------

def test_build_run_file_has_uuid_and_env() -> bool:
    locks_dir = _fresh_locks_dir()
    name = "cto-runfile1"
    original = (
        "#!/usr/bin/env bash\n"
        "export CTO_SESSION_ID='runfile1' && "
        "exec bash '/fake/root/scripts/cto-claude.sh' \n"
    )
    (locks_dir / f"{name}.run").write_text(original)
    u = _write_uuid(locks_dir, name)

    path, rebuilt = tr.write_resume_run_file(locks_dir, name, u)
    text = path.read_text()
    return (f"-r {u}" in text
           and "export CTO_SESSION_ID='runfile1'" in text
           and "cto-claude.sh" in text
           and rebuilt is False
           # never clobber .run — the launcher's EXIT trap owns that path
           and path.name.endswith(".resume.run"))


def test_build_run_file_rebuilds_when_original_gone() -> bool:
    """The launcher deletes .run on exit, so restart #2 has nothing to copy.

    Measured live on cto-0b4d93b9 (2026-08-13): the first restart succeeded and
    the second refused with "no run-file ... to base the resume on", making
    restart a once-per-session operation. Rebuild instead of failing.
    """
    locks_dir = _fresh_locks_dir()
    name = "cto-rebuild1"
    u = _write_uuid(locks_dir, name)          # uuid present, .run absent
    path, rebuilt = tr.write_resume_run_file(locks_dir, name, u, root="/fake/root")
    text = path.read_text()
    return (rebuilt is True
           and f"-r {u}" in text
           and "export CTO_SESSION_ID='rebuild1'" in text
           and "/fake/root/scripts/cto-claude.sh" in text)


def test_build_run_file_second_restart_has_one_resume_flag() -> bool:
    """Restarting twice must not stack two conflicting `-r` ids."""
    locks_dir = _fresh_locks_dir()
    name = "cto-twice1"
    u1 = _write_uuid(locks_dir, name)
    tr.write_resume_run_file(locks_dir, name, u1, root="/fake/root")
    u2 = "second-uuid-aaaa-bbbb-twice1"
    path, _ = tr.write_resume_run_file(locks_dir, name, u2, root="/fake/root")
    text = path.read_text()
    return text.count(" -r ") == 1 and u2 in text and u1 not in text


def _fake_transcripts(tmpdir: Path, uuids: list[str]) -> Path:
    """Build a fake ~/.claude/projects tree holding `uuids` as .jsonl files."""
    proj = tmpdir / "projects" / "-fake-slug"
    proj.mkdir(parents=True, exist_ok=True)
    for i, u in enumerate(uuids):
        f = proj / f"{u}.jsonl"
        f.write_text("{}\n")
        os.utime(f, (1000 + i, 1000 + i))     # ascending mtime: last = newest
    return tmpdir / "projects"


def test_resolve_uuid_uses_recorded_when_transcript_exists() -> bool:
    locks_dir = _fresh_locks_dir()
    name = "cto-good111"
    u = _write_uuid(locks_dir, name)
    with mock.patch.object(tr, "TRANSCRIPTS", _fake_transcripts(Path(tempfile.mkdtemp()), [u])):
        got, note = tr.resolve_resume_uuid(locks_dir, name)
    return got == u and note == ""


def test_resolve_uuid_falls_back_when_transcript_missing() -> bool:
    """The .uuid can name a session that never wrote a transcript.

    `--fork-session` mints a new id at boot; claude only writes the .jsonl once
    the session takes a turn. Restart-then-never-speak leaves .uuid pointing at
    nothing, and resuming into nothing killed cto-0b4d93b9 outright on
    2026-08-13. Fall back to the newest transcript this session really has.
    """
    locks_dir = _fresh_locks_dir()
    name = "cto-fall111"
    real_old = "aaaaaaaa-0000-0000-0000-00000fall111"
    real_new = "bbbbbbbb-0000-0000-0000-00000fall111"
    (locks_dir / f"{name}.uuid").write_text("never-written-uuid-fall111")
    with mock.patch.object(tr, "TRANSCRIPTS",
                           _fake_transcripts(Path(tempfile.mkdtemp()), [real_old, real_new])):
        got, note = tr.resolve_resume_uuid(locks_dir, name)
    return got == real_new and "falling back" in note


def test_resolve_uuid_refuses_when_no_transcript_at_all() -> bool:
    """No transcript anywhere: refuse rather than kill the pane by resuming."""
    locks_dir = _fresh_locks_dir()
    name = "cto-none111"
    (locks_dir / f"{name}.uuid").write_text("ghost-uuid-none111")
    with mock.patch.object(tr, "TRANSCRIPTS", _fake_transcripts(Path(tempfile.mkdtemp()), [])):
        got, note = tr.resolve_resume_uuid(locks_dir, name)
    return got is None and "refusing" in note


def test_default_run_file_text_cxo_shape() -> bool:
    """A non-cto role rebuilds through cxo-claude.sh with --role."""
    t = tr.default_run_file_text("cmo-abc123", "/fake/root")
    return ("export CXO_SESSION_ID='abc123'" in t
           and "/fake/root/scripts/cxo-claude.sh" in t
           and "--role cmo" in t)


# ---------------------------------------------------------------------------
# 6. respawn-pane -k against the right target, never kill-session
# ---------------------------------------------------------------------------

def test_respawn_issues_respawn_pane_not_kill_session() -> bool:
    fake = mock.Mock()
    fake.return_value = mock.Mock(returncode=0, stdout="", stderr="")
    with mock.patch.object(tr.subprocess, "run", fake):
        tr.respawn_pane("cto-target9999", Path("/fake/locks/cto-target9999.run"))
    assert fake.call_count == 1
    argv = fake.call_args.args[0]
    return (argv[:3] == ["tmux", "respawn-pane", "-k"]
           and "-t" in argv and argv[argv.index("-t") + 1] == "cto-target9999"
           and "kill-session" not in argv)


# ---------------------------------------------------------------------------
# 7. capture survives a simulated reap_locks
# ---------------------------------------------------------------------------

def test_capture_survives_reap_locks() -> bool:
    locks_dir = _fresh_locks_dir()
    name = "cto-capture1"
    u = _write_uuid(locks_dir, name)
    # The rest of the lock family a launcher would also have written.
    for suf in session_name.LOCK_SUFFIXES:
        (locks_dir / f"{name}{suf}").write_text("x")

    dest_dir = Path(tempfile.mkdtemp(prefix="terminal-restart-capture-"))
    dest = dest_dir / f"{name}.json"
    tr.capture_identity(locks_dir, name, dest)

    # Simulate session-kill.sh's reap_locks: delete every LOCK_SUFFIXES file
    # (mirrors tools.session_name.KEEP_SUFFIXES leaving .uuid alone, but the
    # capture must survive even if .uuid itself later disappears by hand —
    # so delete that too here to prove the *copy*, not the original, is what
    # session-restart.sh relies on).
    for suf in session_name.LOCK_SUFFIXES:
        (locks_dir / f"{name}{suf}").unlink()
    (locks_dir / f"{name}.uuid").unlink()

    if not dest.exists():
        return False
    data = tr.read_captured_identity(dest)
    return (data["name"] == name and data["role"] == "cto"
           and data["session_id"] == "capture1" and data["uuid"] == u)


# ---------------------------------------------------------------------------
# 8. verify reports failure when no claude comes back
# ---------------------------------------------------------------------------

def test_verify_fails_when_no_claude_found() -> bool:
    with mock.patch.object(tr, "find_claude_pid", mock.Mock(return_value=None)):
        result = tr.verify_restart("cto-dead0000", delay=0)
    return result["ok"] is False and result["pid"] is None


def test_verify_succeeds_when_claude_found() -> bool:
    with mock.patch.object(tr, "find_claude_pid", mock.Mock(return_value=4242)):
        result = tr.verify_restart("cto-alive000", delay=0)
    return result["ok"] is True and result["pid"] == 4242


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="terminal-restart-db-")
    db_mod.DB_PATH = Path(tmp) / "tasks.db"
    db_mod.init()

    print("== hard gate: missing uuid ==")
    _mark(test_refuses_missing_uuid(), "refuses when the .uuid file is missing")

    print("== hard gate: owns live work ==")
    _mark(test_refuses_in_progress_owner(), "refuses when session owns an in_progress task")
    _mark(test_refuses_pending_owner(), "refuses when session owns a pending task")
    _mark(test_force_overrides_live_work(),
          "--force overrides the owns-live-work refusal and names what it overrode")

    print("== run-file: -r <uuid> + original env ==")
    _mark(test_build_run_file_has_uuid_and_env(),
          "run-file contains -r <uuid> and the original env export")
    _mark(test_build_run_file_rebuilds_when_original_gone(),
          "rebuilds from defaults when the launcher already deleted .run")
    _mark(test_build_run_file_second_restart_has_one_resume_flag(),
          "a second restart carries exactly one -r, pointing at the new uuid")
    _mark(test_default_run_file_text_cxo_shape(),
          "non-cto roles rebuild through cxo-claude.sh --role")

    print("== resume uuid must have a transcript behind it ==")
    _mark(test_resolve_uuid_uses_recorded_when_transcript_exists(),
          "uses the recorded uuid when its transcript exists")
    _mark(test_resolve_uuid_falls_back_when_transcript_missing(),
          "falls back to the newest real transcript when .uuid names none")
    _mark(test_resolve_uuid_refuses_when_no_transcript_at_all(),
          "refuses when no transcript exists at all (never resume into nothing)")

    print("== respawn: right target, never kill-session ==")
    _mark(test_respawn_issues_respawn_pane_not_kill_session(),
          "issues respawn-pane -k against the right target, never kill-session")

    print("== session-restart: capture survives reap_locks ==")
    _mark(test_capture_survives_reap_locks(),
          "captured id+uuid survives a simulated reap_locks (and .uuid removal)")

    print("== verify: claude alive/dead after restart ==")
    _mark(test_verify_fails_when_no_claude_found(),
          "verify reports failure when no claude is found afterwards")
    _mark(test_verify_succeeds_when_claude_found(),
          "verify reports success when claude is found afterwards")

    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
