"""Pin the live-session cap (CEO 2026-08-07).

The policy is 5 concurrent C-level sessions, a 6th allowed under protest with
every session's Main Tab carrying the warning, and a 7th refused outright. The
failure mode worth guarding is silence: a cap that quietly stops counting looks
exactly like a cap nobody has hit yet, and the first sign of trouble would be
the OOM killer taking out claudeflow on the box that also runs production.

Run via:  python scripts/test_session_cap.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import session_cap  # noqa: E402

_failures = 0

DEAD_PID = 999999  # far above any plausible live pid on this box


def _mark(ok: bool, label: str) -> None:
    global _failures
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        _failures += 1


def _locks(tmp: Path, live: int, stale: int = 0) -> Path:
    d = tmp / "locks"
    d.mkdir(parents=True, exist_ok=True)
    for i in range(live):
        (d / f"cto-live{i:04d}.lock").write_text(f"{os.getpid()}\n")
    for i in range(stale):
        (d / f"cto-dead{i:04d}.lock").write_text(f"{DEAD_PID}\n")
    return d


def test_counts_only_live() -> None:
    print("counting")
    with tempfile.TemporaryDirectory() as t:
        d = _locks(Path(t), live=3, stale=4)
        _mark(len(session_cap.live_sessions(d)) == 3,
              "a lock whose process is gone is not a live session")

    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "locks"
        d.mkdir()
        # Only C-level roles count; a DEV or a daemon pidfile must not.
        (d / "developer-x1.lock").write_text(f"{os.getpid()}\n")
        (d / "maintab-daemon.pid.lock").write_text(f"{os.getpid()}\n")
        (d / "cfo-real0001.lock").write_text(f"{os.getpid()}\n")
        _mark(session_cap.live_sessions(d) == ["cfo-real0001"],
              "only cto/cmo/cfo/cxo locks are counted")


def test_warning_thresholds() -> None:
    print("the banner every session shows")
    cap = session_cap.CAP
    _mark(session_cap.warning(cap) == "", f"silent at exactly the cap ({cap})")
    _mark(session_cap.warning(cap - 1) == "", "silent below the cap")

    over = session_cap.warning(cap + 1)
    _mark(over != "", "one over the cap produces a banner")
    _mark(str(cap + 1) in over and str(cap) in over,
          "banner names both the current count and the cap")
    _mark("1" in over, "banner says how many need closing")
    _mark("2" in session_cap.warning(cap + 2), "banner scales past one over")


def test_spawn_gate() -> None:
    print("the spawn gate")
    cap, grace = session_cap.CAP, session_cap.GRACE

    with tempfile.TemporaryDirectory() as t:
        d = _locks(Path(t), live=cap - 1)
        _mark(session_cap.main(["--check-spawn", "--locks-dir", str(d)]) == 0,
              "under the cap: allowed")

    with tempfile.TemporaryDirectory() as t:
        # `cap` already live means this spawn is the grace slot.
        d = _locks(Path(t), live=cap)
        _mark(session_cap.main(["--check-spawn", "--locks-dir", str(d)]) == 0,
              f"the {cap + 1}th is allowed (grace slot)")

    with tempfile.TemporaryDirectory() as t:
        d = _locks(Path(t), live=cap + grace)
        _mark(session_cap.main(["--check-spawn", "--locks-dir", str(d)]) == 2,
              f"the {cap + grace + 1}th is refused (exit 2)")

    with tempfile.TemporaryDirectory() as t:
        # Stale locks must not push a legitimate spawn over the line.
        d = _locks(Path(t), live=1, stale=cap + grace)
        _mark(session_cap.main(["--check-spawn", "--locks-dir", str(d)]) == 0,
              "dead sessions do not consume cap slots")


def test_spawn_scripts_fail_open() -> None:
    """A checker that cannot run must not block a spawn.

    Both launchers distinguish exit 2 (over cap) from any other non-zero
    (checker broken, relocated ROOT with no tools/ package, python missing).
    Treating those alike would make an unrelated breakage look like a capacity
    limit and lock the CEO out of their own org.
    """
    print("launchers fail open, not closed")
    for name in ("spawn-cto.sh", "spawn-cxo.sh"):
        src = (ROOT / "scripts" / name).read_text()
        _mark("--check-spawn" in src, f"{name}: consults tools.session_cap")
        _mark("--locks-dir" in src,
              f"{name}: points the check at its own LOCKS_DIR")
        _mark("-eq 2" in src,
              f"{name}: only exit 2 refuses (anything else fails open)")


if __name__ == "__main__":
    test_counts_only_live()
    test_warning_thresholds()
    test_spawn_gate()
    test_spawn_scripts_fail_open()
    print()
    print("ALL PASS" if not _failures else f"FAILED — {_failures} failure(s)")
    raise SystemExit(1 if _failures else 0)
