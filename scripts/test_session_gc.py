"""Tests for tools/session_gc.py + tools/session_name.py.

A C-level session is real only when BOTH halves agree: a live lock file AND a
tmux session with the same name. Measured 2026-08-10 the halves diverged both
ways (lock cto-4020c182, tmux cto-session-mslldjt6) and the same orphaned
spawn was simultaneously invisible to the cap and uncounted on the phone.
These tests pin the reconcile/reap contract that closes that gap.

Cases:
  1. lock with dead pid + no tmux        -> lock_only, reaped by --reap
  2. lock with LIVE pid + no tmux        -> ORPHAN, reported, NOT reaped
  3. tmux with no lock                    -> tmux_only, never touched
  4. both present                         -> matched, nothing done
  5. --reap without --yes                 -> deletes nothing (dry-run default)
  6. reconcile is pure                    -> same inputs, no filesystem writes
  7. one name, one lock basename          -> incl. the fallback-name case
  8. reap sweeps the whole sibling family (.run/.tty/.uuid/.winid/...)
  9. non-C-level locks (developer-x1) are ignored

Run via:  python scripts/test_session_gc.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import session_gc as gc  # noqa: E402
from tools import session_name as nm  # noqa: E402

_failures = 0

DEAD_PID = 999999  # far above any plausible live pid on this box
LIVE_PID = os.getpid()  # this test process is, by construction, alive


def _mark(ok: bool, label: str) -> None:
    global _failures
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        _failures += 1


def _new_locks(tmp: Path) -> Path:
    d = tmp / "locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_family(d: Path, stem: str, pid: int) -> None:
    """Write the full sibling family for a session, each holding the pid."""
    for suf in nm.LOCK_SUFFIXES:
        (d / f"{stem}{suf}").write_text(f"{pid}\n")


def _family_present(d: Path, stem: str) -> bool:
    return all((d / f"{stem}{suf}").exists() for suf in nm.LOCK_SUFFIXES)


def _no_family(d: Path, stem: str) -> bool:
    return not any((d / f"{stem}{suf}").exists() for suf in nm.LOCK_SUFFIXES)


def _mock_tmux(names):
    """Point the CLI's tmux detection at a fixed list (restore via the orig)."""
    orig = gc._detect_tmux_sessions
    gc._detect_tmux_sessions = lambda: list(names)
    return orig


def test_dead_lock_no_tmux_is_lock_only_and_reaped() -> None:
    print("dead-pid lock, no tmux -> lock_only, reaped")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "cto-dead1", DEAD_PID)
        rec = gc.reconcile(d, tmux_sessions=set())
        _mark(rec.lock_only == {"cto-dead1"}, "classified lock_only")
        _mark(rec.matched == set() and rec.tmux_only == set(),
              "not matched, no tmux_only")
        _mark(rec.orphans == {}, "a dead pid is not an orphan")
        reaped, skipped = gc.reap(d, rec, dry_run=False)
        _mark(reaped == ["cto-dead1"], "reap returns the dead stem")
        _mark(skipped == [], "nothing skipped")
        _mark(_no_family(d, "cto-dead1"), "whole sibling family removed")


def test_live_lock_no_tmux_is_orphan_not_reaped() -> None:
    print("live-pid lock, no tmux -> ORPHAN, not reaped")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "cto-orph1", LIVE_PID)
        rec = gc.reconcile(d, tmux_sessions=set())
        _mark(rec.lock_only == {"cto-orph1"}, "still lock_only (no tmux)")
        _mark(rec.orphans == {"cto-orph1": LIVE_PID},
              "orphans carries the live pid")
        # Even with --yes, a live pid is never deleted.
        reaped, skipped = gc.reap(d, rec, dry_run=False)
        _mark(reaped == [], "orphan NOT reaped even under --yes")
        _mark(skipped == ["cto-orph1"], "orphan reported as skipped")
        _mark(_family_present(d, "cto-orph1"),
              "live lock family left intact on disk")


def test_tmux_with_no_lock_is_tmux_only_never_touched() -> None:
    print("tmux session, no lock -> tmux_only, never touched")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        # A tmux session the console made but no lock was ever written.
        rec = gc.reconcile(d, tmux_sessions={"cmo-session-abc12345"})
        _mark(rec.tmux_only == {"cmo-session-abc12345"}, "classified tmux_only")
        _mark(rec.lock_only == set() and rec.matched == set(),
              "no locks to classify")
        reaped, skipped = gc.reap(d, rec, dry_run=False)
        _mark(reaped == [] and skipped == [],
              "reap does nothing for tmux_only (no tmux ever killed)")


def test_both_present_is_matched_nothing_done() -> None:
    print("live lock + matching tmux -> matched, nothing done")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "cfo-real1", LIVE_PID)
        rec = gc.reconcile(d, tmux_sessions={"cfo-real1"})
        _mark(rec.matched == {"cfo-real1"}, "classified matched")
        _mark(rec.lock_only == set() and rec.tmux_only == set() and
              rec.orphans == {}, "no drift when both halves agree")
        reaped, skipped = gc.reap(d, rec, dry_run=False)
        _mark(reaped == [] and skipped == [], "matched is never reaped")
        _mark(_family_present(d, "cfo-real1"), "matched family left intact")


def test_reap_without_yes_deletes_nothing() -> None:
    print("--reap without --yes is a dry run")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "cto-dead2", DEAD_PID)
        rec = gc.reconcile(d, tmux_sessions=set())
        reaped, skipped = gc.reap(d, rec, dry_run=True)  # default
        _mark(reaped == ["cto-dead2"], "dry-run still REPORTS what it would reap")
        _mark(_family_present(d, "cto-dead2"),
              "but the files survive (dry-run deletes nothing)")

        # The CLI default for --reap is dry-run too.
        orig = _mock_tmux([])
        out = _capture(lambda: gc.main(["--reap", "--locks-dir", str(d)]))
        gc._detect_tmux_sessions = orig
        _mark(_family_present(d, "cto-dead2"),
              "CLI --reap (no --yes) leaves files on disk")
        _mark("would delete" in out and "dry-run only" in out,
              "CLI dry-run announces itself")


def test_reconcile_is_pure() -> None:
    print("reconcile is pure: no filesystem writes")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "cto-a", DEAD_PID)
        _make_family(d, "cto-b", LIVE_PID)
        (d / "cto-c.lock").write_text("not-a-number\n")  # unreadable pid

        before = _snapshot(d)
        rec1 = gc.reconcile(d, tmux_sessions={"cto-b"})
        rec2 = gc.reconcile(d, tmux_sessions={"cto-b"})
        after = _snapshot(d)

        _mark(_path(rec1) == _path(rec2),
              "same inputs -> identical classification")
        _mark(before == after,
              "no file created, modified, or deleted by reconciling")
        # cto-c has an unreadable pid -> treated as not-alive -> lock_only,
        # and definitely not an orphan (no live pid).
        _mark("cto-c" in rec1.lock_only and "cto-c" not in rec1.orphans,
              "unreadable-pid lock is lock_only, not orphan")


def test_one_name_one_lock_basename() -> None:
    print("one session name, one lock basename (incl. fallback name)")
    # Normal uuid-hex id (the Mac spawn path).
    _mark(nm.lock_basename("cto", "4020c182") == "cto-4020c182",
          "uuid id: basename is <role>-<id>")
    # Console fallback slug: slugify produces session-<base36> for an empty
    # name. The launcher must adopt that same string so lock basename ==
    # tmux session name — this is exactly the Aug-10 divergence.
    fallback_id = nm.id_from_tmux_session("cto-session-mslldjt6", role="cto")
    _mark(fallback_id == "session-mslldjt6",
          "fallback tmux name yields its slug as the id")
    _mark(nm.lock_basename("cto", fallback_id) == "cto-session-mslldjt6",
          "fallback: lock basename == tmux session name (one value)")
    # A name whose role prefix belongs to another role is NOT adopted — a
    # CMO launcher must not steal a CTO session's name as its own lock.
    _mark(nm.id_from_tmux_session("cto-session-mslldjt6", role="cmo") is None,
          "id not adopted when the role prefix mismatches")
    _mark(nm.id_from_tmux_session("developer-x1") is None,
          "non-C-level name yields no id (falls back to fresh uuid)")
    # All five C-level roles round-trip a fallback name through the rule.
    for role in nm.ROLES:
        _mark(nm.id_from_tmux_session(f"{role}-session-zzz", role=role)
              == "session-zzz",
              f"{role}: fallback name adopts cleanly")


def test_reap_sweeps_whole_family() -> None:
    print("reap removes every sibling, not just .lock")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "cxo-fam1", DEAD_PID)
        gc.reap(d, gc.reconcile(d, set()), dry_run=False)
        for suf in nm.LOCK_SUFFIXES:
            _mark(not (d / f"cxo-fam1{suf}").exists(),
                  f"cxo-fam1{suf} removed")


def test_non_clevel_locks_ignored() -> None:
    print("non-C-level lock files are not C-level sessions")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "developer-x1", DEAD_PID)   # a DEV worktree pidfile
        _make_family(d, "maintab-daemon.pid", DEAD_PID)  # a daemon
        rec = gc.reconcile(d, tmux_sessions=set())
        _mark(rec.matched == set() and rec.lock_only == set() and
              rec.tmux_only == set(),
              "DEV/daemon locks are neither half of a C-level session")


def test_quiet_silent_when_clean() -> None:
    print("--quiet prints nothing when there is no drift")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        orig = _mock_tmux([])  # no tmux, no locks -> nothing to say
        out = _capture(lambda: gc.main(
            ["--report", "--quiet", "--locks-dir", str(d)]))
        gc._detect_tmux_sessions = orig
        _mark(out == "", "clean reconcile under --quiet is silent")


def test_orphan_surfaces_loudly_in_report() -> None:
    print("an orphan is reported loudly and separately")
    with tempfile.TemporaryDirectory() as t:
        d = _new_locks(Path(t))
        _make_family(d, "cto-loud1", LIVE_PID)
        orig = _mock_tmux([])
        out = _capture(lambda: gc.main(["--report", "--locks-dir", str(d)]))
        gc._detect_tmux_sessions = orig
        _mark("ORPHAN" in out and f"pid {LIVE_PID}" in out,
              "report names the orphan and its live pid")
        _mark("NOT reaped" in out, "report states the orphan is not reaped")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _snapshot(d: Path) -> dict:
    return {p.name: p.read_text() for p in d.iterdir() if p.is_file()}


def _path(rec) -> dict:
    """A plain-data view of a Reconciliation for equality comparison."""
    return {
        "matched": sorted(rec.matched),
        "lock_only": sorted(rec.lock_only),
        "tmux_only": sorted(rec.tmux_only),
        "orphans": dict(rec.orphans),
    }


def _capture(fn) -> str:
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue()


if __name__ == "__main__":
    test_dead_lock_no_tmux_is_lock_only_and_reaped()
    test_live_lock_no_tmux_is_orphan_not_reaped()
    test_tmux_with_no_lock_is_tmux_only_never_touched()
    test_both_present_is_matched_nothing_done()
    test_reap_without_yes_deletes_nothing()
    test_reconcile_is_pure()
    test_one_name_one_lock_basename()
    test_reap_sweeps_whole_family()
    test_non_clevel_locks_ignored()
    test_quiet_silent_when_clean()
    test_orphan_surfaces_loudly_in_report()
    print()
    print("ALL PASS" if not _failures else f"FAILED — {_failures} failure(s)")
    raise SystemExit(1 if _failures else 0)
