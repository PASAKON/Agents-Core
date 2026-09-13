"""Tests for scripts/session-rename.sh's --prefix flag (task-bbdfa8d1).

State-in-the-name, stamped via the existing rename path: `/session-close`
sends `--prefix "✅"`, `/session-save` sends `--prefix "⏸"`. Covers:

  1. --prefix puts the glyph in front of the machine/role in the sent name.
  2. --show reports the combined "<prefix> <topic>" record.
  3. Same prefix + same topic twice -> second call is a no-op (unchanged).
  4. A prefix change alone (same topic) still sends again -- the dedupe key
     must include the prefix, not just the topic.
  5. No --prefix at all is byte-identical to the pre-existing behaviour
     (covered already by scripts/test_session_rename.py; asserted again here
     as a guard that --prefix's default is truly a no-op).

Same fake-tmux-on-PATH harness as scripts/test_session_rename.py — no real
tmux pane is ever addressed.

Run via:   pytest scripts/test_session_rename_prefix.py
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REAL_ROOT = Path(__file__).resolve().parent.parent
REAL_SCRIPT = REAL_ROOT / "scripts" / "session-rename.sh"


def _stage(tmp_path: Path) -> tuple[Path, Path]:
    fake_root = tmp_path / "fake-root"
    (fake_root / "scripts").mkdir(parents=True)
    script = fake_root / "scripts" / "session-rename.sh"
    script.write_text(REAL_SCRIPT.read_text())
    script.chmod(0o755)
    return fake_root, script


def _tmux_stub(tmp_path: Path) -> tuple[Path, Path]:
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


def _env(bin_dir: Path, *, sid: str = "rntest01", role: str = "cto") -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["TMUX"] = "/tmp/fake-tmux-socket,1,0"
    env["CXO_ROLE"] = role
    env["CTO_SESSION_ID"] = sid
    env.pop("CXO_SESSION_ID", None)
    return env


def _run(script: Path, args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], env=env,
                           capture_output=True, text=True, timeout=15)


def _send_count(log: Path) -> int:
    if not log.exists():
        return 0
    return sum(
        1 for line in log.read_text().splitlines()
        if line.startswith("send-keys") and line.rstrip().endswith(" Enter")
    )


def test_prefix_lands_in_front_of_machine_role(tmp_path: Path) -> None:
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(bin_dir, sid="pfx01")

    r = _run(script, ["--prefix", "✅", "close it"], env)
    assert r.returncode == 0
    assert "queued: /rename ✅ " in r.stdout
    # prefix precedes the machine label, not trailing after the topic paren
    body = r.stdout.split("queued: /rename ", 1)[1]
    assert body.startswith("✅ ")
    assert "(close it)" in body


def test_show_reports_prefix_plus_topic(tmp_path: Path) -> None:
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(bin_dir, sid="pfx02")

    _run(script, ["--prefix", "⏸", "park it"], env)
    r = _run(script, ["--show"], env)
    assert r.stdout.strip() == "recorded: ⏸ park it"


def test_same_prefix_and_topic_twice_is_noop(tmp_path: Path) -> None:
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(bin_dir, sid="pfx03")

    r1 = _run(script, ["--prefix", "✅", "same topic"], env)
    assert r1.returncode == 0 and _send_count(log) == 1

    r2 = _run(script, ["--prefix", "✅", "same topic"], env)
    assert r2.returncode == 0
    assert r2.stdout.strip() == "unchanged: ✅ same topic"
    assert _send_count(log) == 1


def test_prefix_change_alone_sends_again(tmp_path: Path) -> None:
    """The dedupe key must fold in the prefix -- a save->close transition on
    the SAME topic (⏸ -> ✅) must still stamp the new state, not silently
    no-op because the bare topic string didn't change."""
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(bin_dir, sid="pfx04")

    _run(script, ["--prefix", "⏸", "same topic"], env)
    assert _send_count(log) == 1

    r = _run(script, ["--prefix", "✅", "same topic"], env)
    assert r.returncode == 0
    assert "queued:" in r.stdout, f"prefix change must send again: {r.stdout!r}"
    assert _send_count(log) == 2


def test_no_prefix_matches_legacy_shape(tmp_path: Path) -> None:
    """Omitting --prefix entirely must stay byte-identical to the
    pre-task-bbdfa8d1 name shape: '<MACHINE> <ROLE> #<id> (<topic>)', no
    leading glyph or stray space."""
    fake_root, script = _stage(tmp_path)
    bin_dir, log = _tmux_stub(tmp_path)
    env = _env(bin_dir, sid="pfx05")

    r = _run(script, ["legacy topic"], env)
    assert r.returncode == 0
    sent = r.stdout.split("queued: /rename ", 1)[1].split(" (executes", 1)[0]
    assert not sent.startswith(("✅", "⏸", "⛔"))
    assert sent.endswith("(legacy topic)")
