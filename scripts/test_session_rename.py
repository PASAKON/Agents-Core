"""Tests for scripts/session-rename.sh (task-460f3eaf).

Covers:
  1. root derivation is not hardcoded — the real, UNMODIFIED script is copied
     into a fake root under tmp_path and its state file lands there, not in
     the real repo's state/locks/.
  2. first send under tmux writes the .topic record and sends keys once.
  3. a second call with the SAME topic no-ops: prints "unchanged: <topic>",
     exits 0, and sends NO further keys — this is the twice-with-same-topic
     acceptance demonstration.
  4. a different topic sends again and updates the record.
  5. --force sends even when unchanged, and still updates the record.
  6. --show prints the recorded topic and sends nothing at all.
  7. no $TMUX still exits 0 with the would-run line, and never records
     (nothing was actually applied, so there is nothing to remember).
  8. with no session id (CTO_SESSION_ID / CXO_SESSION_ID both unset),
     persistence is disabled entirely — every call sends, nothing is
     written to disk.

A fake `tmux` shim on PATH stands in for the real binary: the script never
touches a live tmux pane. `TMUX=fake` only tells the script's own `[ -z
"${TMUX:-}" ]` guard that it is "inside tmux" — no real session is ever
addressed.

Run via:   pytest scripts/test_session_rename.py
       or: python scripts/test_session_rename.py
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REAL_ROOT = Path(__file__).resolve().parent.parent
REAL_SCRIPT = REAL_ROOT / "scripts" / "session-rename.sh"


def _stage(tmp_path: Path) -> tuple[Path, Path]:
    """Copy the real, UNMODIFIED script into a fresh fake root under
    tmp_path. `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` then
    resolves to this fake root purely from the script's own location — no
    line is patched out — which is what proves the root is derived, not the
    literal `/Users/gob/Projects/Agents` (or `/opt/mooniex-agents`) path.
    """
    fake_root = tmp_path / "fake-root"
    (fake_root / "scripts").mkdir(parents=True)
    script = fake_root / "scripts" / "session-rename.sh"
    script.write_text(REAL_SCRIPT.read_text())
    script.chmod(0o755)
    return fake_root, script


def _tmux_stub(tmp_path: Path) -> tuple[Path, Path]:
    """A fake `tmux` on PATH: logs every invocation, answers
    `display-message -p '#S'` with a fixed session name, never touches a
    real pane."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "tmux.log"
    (bin_dir / "tmux").write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        'if [ "$1" = "display-message" ]; then echo "fake-session"; fi\n'
        "exit 0\n"
    )
    (bin_dir / "tmux").chmod(0o755)
    return bin_dir, log


def _env(tmp_path: Path, bin_dir: Path | None, *, tmux: bool,
         sid: str | None = "rntest01", role: str = "cto") -> dict:
    env = dict(os.environ)
    if bin_dir is not None:
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    if tmux:
        env["TMUX"] = "/tmp/fake-tmux-socket,1,0"
    else:
        env.pop("TMUX", None)
    env["CXO_ROLE"] = role
    if sid is None:
        env.pop("CTO_SESSION_ID", None)
        env.pop("CXO_SESSION_ID", None)
    else:
        env["CTO_SESSION_ID"] = sid
        env.pop("CXO_SESSION_ID", None)
    return env


def _run(script: Path, args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], env=env,
                           capture_output=True, text=True, timeout=15)


def _send_count(log: Path) -> int:
    """Number of completed rename sends — one `send-keys ... Enter` line
    (the stub logs each whole invocation's argv as one `$*`-joined line)
    per actual `/rename` send."""
    if not log.exists():
        return 0
    return sum(
        1 for line in log.read_text().splitlines()
        if line.startswith("send-keys") and line.rstrip().endswith(" Enter")
    )


# ---------------------------------------------------------------------------
# root derivation
# ---------------------------------------------------------------------------

def test_root_not_hardcoded_state_lands_under_fake_root(tmp_path: Path) -> None:
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="roottest")

    r = _run(script, ["hello world"], env)
    assert r.returncode == 0
    assert "queued:" in r.stdout

    topic_file = fake_root / "state" / "locks" / "cto-roottest.topic"
    assert topic_file.exists(), "state must land under the script's OWN root"
    assert topic_file.read_text() == "hello world"

    real_topic_file = REAL_ROOT / "state" / "locks" / "cto-roottest.topic"
    assert not real_topic_file.exists(), (
        "a hardcoded root would have written into the real repo's state/locks/"
    )


# ---------------------------------------------------------------------------
# no-op / record / force / show
# ---------------------------------------------------------------------------

def test_first_call_sends_and_records(tmp_path: Path) -> None:
    _, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="samesame")

    r = _run(script, ["Alpha topic"], env)
    assert r.returncode == 0
    assert "queued:" in r.stdout
    assert _send_count(log) == 1


def test_second_call_same_topic_is_a_noop(tmp_path: Path) -> None:
    """The twice-with-same-topic acceptance demonstration: calling twice with
    the same topic sends keys exactly once."""
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="samesame")

    r1 = _run(script, ["Alpha topic"], env)
    assert r1.returncode == 0 and "queued:" in r1.stdout
    assert _send_count(log) == 1, "first call must send once"

    r2 = _run(script, ["Alpha topic"], env)
    assert r2.returncode == 0
    assert r2.stdout.strip() == "unchanged: Alpha topic", (
        f"second call's output: {r2.stdout!r}"
    )
    assert _send_count(log) == 1, (
        "second call with the SAME topic must NOT send again — "
        f"log after second call: {log.read_text() if log.exists() else '<no log>'}"
    )


def test_different_topic_sends_again_and_updates_record(tmp_path: Path) -> None:
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="difftopic")

    _run(script, ["First topic"], env)
    assert _send_count(log) == 1

    r = _run(script, ["Second topic"], env)
    assert r.returncode == 0 and "queued:" in r.stdout
    assert _send_count(log) == 2, "a changed topic must send again"

    topic_file = fake_root / "state" / "locks" / "cto-difftopic.topic"
    assert topic_file.read_text() == "Second topic"


def test_force_sends_even_when_unchanged(tmp_path: Path) -> None:
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="forcetest")

    _run(script, ["Same topic"], env)
    assert _send_count(log) == 1

    r = _run(script, ["--force", "Same topic"], env)
    assert r.returncode == 0
    assert "queued:" in r.stdout, f"--force must still send: {r.stdout!r}"
    assert _send_count(log) == 2, "--force must send even though the topic is unchanged"

    topic_file = fake_root / "state" / "locks" / "cto-forcetest.topic"
    assert topic_file.read_text() == "Same topic"


def test_show_prints_recorded_and_touches_nothing(tmp_path: Path) -> None:
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="showtest")

    _run(script, ["Recorded topic"], env)
    assert _send_count(log) == 1
    log_before = log.read_text()

    r = _run(script, ["--show"], env)
    assert r.returncode == 0
    assert r.stdout.strip() == "recorded: Recorded topic"
    assert log.read_text() == log_before, "--show must never touch the pane"

    topic_file = fake_root / "state" / "locks" / "cto-showtest.topic"
    assert topic_file.read_text() == "Recorded topic", "--show must not mutate the record"


def test_show_with_no_record_says_none(tmp_path: Path) -> None:
    _, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="neverset")

    r = _run(script, ["--show"], env)
    assert r.returncode == 0
    assert r.stdout.strip() == "recorded: (none)"
    assert not log.exists(), "--show must never invoke tmux"


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------

def test_no_tmux_still_exits_zero_with_would_run_line(tmp_path: Path) -> None:
    _, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=False, sid="notmuxid")

    r = _run(script, ["Gamma topic"], env)
    assert r.returncode == 0
    assert r.stdout.startswith("not inside tmux — rename manually: /rename ")
    assert "Gamma topic" in r.stdout
    assert not log.exists(), "the no-tmux guard must never invoke tmux"

    topic_file = script.parent.parent / "state" / "locks" / "cto-notmuxid.topic"
    assert not topic_file.exists(), (
        "nothing was actually applied, so the no-tmux branch must not record"
    )


def test_no_session_id_disables_persistence(tmp_path: Path) -> None:
    """Without CTO_SESSION_ID/CXO_SESSION_ID the script cannot name a record
    file, so it degrades to the pre-existing always-send behaviour rather
    than guessing at a shared filename."""
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid=None)

    r1 = _run(script, ["Same topic"], env)
    assert r1.returncode == 0 and "queued:" in r1.stdout
    r2 = _run(script, ["Same topic"], env)
    assert r2.returncode == 0 and "queued:" in r2.stdout, (
        "with no session id, repeated calls must keep sending (no false no-op)"
    )
    assert _send_count(log) == 2

    locks_dir = fake_root / "state" / "locks"
    assert not locks_dir.exists() or not list(locks_dir.glob("*.topic")), (
        "no session id means no .topic file should be written anywhere"
    )


def test_usage_error_without_topic(tmp_path: Path) -> None:
    _, script = _stage(tmp_path)
    bin_dir, _ = _tmux_stub(tmp_path)
    env = _env(tmp_path, bin_dir, tmux=True, sid="usagetest")

    r = _run(script, [], env)
    assert r.returncode == 1
    assert "usage:" in r.stderr


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def main() -> int:
    import tempfile

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fails = 0
    for t in tests:
        with tempfile.TemporaryDirectory() as tmp_s:
            try:
                t(Path(tmp_s))
                _mark(True, t.__name__)
            except AssertionError as e:
                fails += 1
                _mark(False, f"{t.__name__}: {e}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
