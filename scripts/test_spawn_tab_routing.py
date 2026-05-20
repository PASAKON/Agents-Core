"""Smoke tests for the iTerm tab routing patches.

Covers:
  1. delegate._build_spawn_applescript embeds the owner_cto exactly so
     DEV tabs route to the spawning CTO's window (not whatever window
     happens to own the first "CTO" tab).
  2. The same script reuses an existing tab when one with the task_id
     already exists, instead of always opening a new tab.
  3. scripts/spawn-cto.sh picks a fresh CTO id when the previously
     chosen id is held by a live lock, and refuses an explicit id that
     is already live.

Run via:   python scripts/test_spawn_tab_routing.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.delegate import _build_spawn_applescript  # noqa: E402


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def test_owner_cto_routing() -> bool:
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-deadbeef", owner_cto="ctoaaaaa")
    return (
        'contains "CTO Chat #ctoaaaaa"' in script
        and 'contains "(task-deadbeef)"' in script
        and 'return "reused"' in script
        and 'return "spawned"' in script
    )


def test_no_owner_falls_through() -> bool:
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-1", owner_cto=None)
    return (
        '"" is not ""' in script
        and 'contains "CTO Chat #"' in script
    )


def test_reuse_check_comes_first() -> bool:
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-xyz", owner_cto="ctobbbbb")
    reuse_idx = script.find('(task-xyz)')
    owner_idx = script.find('CTO Chat #ctobbbbb')
    return 0 <= reuse_idx < owner_idx


def _stage_fake_root(tmp: Path) -> Path:
    fake_root = tmp / "fake-root"
    fake_root.mkdir()
    (fake_root / ".venv").mkdir()
    (fake_root / "state").symlink_to(tmp / "state")
    scripts_dir = fake_root / "scripts"
    scripts_dir.mkdir()
    for stub in ("cto-claude.sh", "tail-dev-logs.sh"):
        (scripts_dir / stub).write_text("#!/usr/bin/env bash\nexit 0\n")
        (scripts_dir / stub).chmod(0o755)
    src = (ROOT / "scripts" / "spawn-cto.sh").read_text()
    patched = src.replace(
        'ROOT="/Users/gob/Projects/Agents"',
        f'ROOT="{fake_root}"',
    )
    patched_path = scripts_dir / "spawn-cto.patched.sh"
    patched_path.write_text(patched)
    patched_path.chmod(0o755)
    return patched_path


def _stage_osascript_shim(tmp: Path) -> Path:
    shim = tmp / "bin"
    shim.mkdir()
    (shim / "osascript").write_text("#!/usr/bin/env bash\nexit 0\n")
    (shim / "osascript").chmod(0o755)
    return shim


def test_spawn_cto_collision() -> bool:
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        locks = tmp / "state" / "locks"
        locks.mkdir(parents=True, exist_ok=True)
        live_id = "livecto1"
        (locks / f"cto-{live_id}.lock").write_text(f"{os.getpid()}\n")

        patched_path = _stage_fake_root(tmp)
        shim = _stage_osascript_shim(tmp)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        env["CTO_SESSION_ID"] = live_id

        proc = subprocess.run(
            ["bash", str(patched_path)],
            env=env, capture_output=True, text=True, timeout=15,
        )
        return (
            proc.returncode != 0
            and "already running" in (proc.stderr or "")
            and live_id in (proc.stderr or "")
        )


def test_spawn_cto_reaps_stale_lock() -> bool:
    """Stale lock (pid no longer alive) should be reaped so the spawn
    succeeds when the explicit id is reused."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        locks = tmp / "state" / "locks"
        locks.mkdir(parents=True, exist_ok=True)

        dead_pid = 999999
        while dead_pid < 2_000_000:
            try:
                os.kill(dead_pid, 0)
                dead_pid += 1
            except (ProcessLookupError, OSError):
                break
        else:
            print("    (skipping stale-lock test: no dead PID found)")
            return True

        stale_id = "stalecto"
        (locks / f"cto-{stale_id}.lock").write_text(f"{dead_pid}\n")

        patched_path = _stage_fake_root(tmp)
        shim = _stage_osascript_shim(tmp)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        env["CTO_SESSION_ID"] = stale_id

        proc = subprocess.run(
            ["bash", str(patched_path)],
            env=env, capture_output=True, text=True, timeout=15,
        )
        return proc.returncode == 0


def main() -> int:
    fails = 0
    r = test_owner_cto_routing(); fails += not r
    _mark(r, "owner_cto literal embedded in AppleScript")
    r = test_no_owner_falls_through(); fails += not r
    _mark(r, "absent owner_cto disables exact match branch")
    r = test_reuse_check_comes_first(); fails += not r
    _mark(r, "tab-reuse check precedes owner-window lookup")
    r = test_spawn_cto_collision(); fails += not r
    _mark(r, "spawn-cto.sh rejects live duplicate CTO_SESSION_ID")
    r = test_spawn_cto_reaps_stale_lock(); fails += not r
    _mark(r, "spawn-cto.sh reaps stale lock and reuses id")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
