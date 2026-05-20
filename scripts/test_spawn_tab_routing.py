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

from tools.delegate import (  # noqa: E402
    _build_spawn_applescript,
    _owner_window_id,
)


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


def test_owner_winid_targets_by_id() -> bool:
    """When the CTO's .winid file is present, AppleScript must target
    the iTerm window by id — name matching is unreliable due to session
    title flicker."""
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-w", owner_cto="ctoabcd",
        owner_winid="2354")
    return (
        "first window whose id is (2354)" in script
        and 'targetWin is missing value' in script
    )


def test_owner_winid_absent_falls_back_to_name() -> bool:
    """With no winid file, the by-id branch must be dead-code (gated by
    `if "" is not ""`) so the name match is what actually runs."""
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-w", owner_cto="ctoabcd",
        owner_winid=None)
    return (
        'if "" is not "" then' in script
        and 'first window whose id is (0)' in script
        and 'CTO Chat #ctoabcd' in script
    )


def test_owner_window_id_reader(tmp_path_like: Path | None = None) -> bool:
    """The reader returns the digits when the lock file exists and is
    well-formed, None otherwise. Uses the real lock dir but a synthetic
    CTO id so it doesn't collide with anything live."""
    fake_id = "testwin1"
    p = ROOT / "state" / "locks" / f"cto-{fake_id}.winid"
    try:
        p.write_text("9999\n")
        ok_present = _owner_window_id(fake_id) == "9999"
        p.unlink()
        ok_missing = _owner_window_id(fake_id) is None
        p.write_text("not-a-number\n")
        ok_garbage = _owner_window_id(fake_id) is None
        return ok_present and ok_missing and ok_garbage
    finally:
        if p.exists():
            p.unlink()


def test_checks_both_title_surfaces() -> bool:
    """Each lookup must check `name of t` (sticky tab title) AND
    `name of current session of t` (session badge). Without this the
    AppleScript can miss the CTO window during a session-name flicker."""
    script = _build_spawn_applescript(
        cmd="echo hi", task_id="task-z", owner_cto="ctowxyzab")
    return (
        script.count("set tabName to name of t") >= 3
        and script.count("set sessName to name of current session of t") >= 3
        and "tabName contains \"(task-z)\"" in script
        and "sessName contains \"(task-z)\"" in script
        and "tabName contains \"CTO Chat #ctowxyzab\"" in script
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
        env.pop("CTO_SESSION_ID", None)

        proc = subprocess.run(
            ["bash", str(patched_path), "--id", live_id],
            env=env, capture_output=True, text=True, timeout=15,
        )
        return (
            proc.returncode != 0
            and "already running" in (proc.stderr or "")
            and live_id in (proc.stderr or "")
        )


def test_spawn_cto_drops_inherited_env() -> bool:
    """spawn-cto.sh must NOT honor an inherited CTO_SESSION_ID. Running
    it from inside an existing CTO chat would otherwise clone that
    chat's id into the new tab — the real-world bug that motivated this
    patch."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        (tmp / "state" / "locks").mkdir(parents=True, exist_ok=True)
        patched_path = _stage_fake_root(tmp)
        shim = _stage_osascript_shim(tmp)

        env = dict(os.environ)
        env["PATH"] = f"{shim}:{env.get('PATH', '')}"
        env["CTO_SESSION_ID"] = "parentcc"

        proc = subprocess.run(
            ["bash", str(patched_path)],
            env=env, capture_output=True, text=True, timeout=15,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0 and "parentcc" not in out


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
        env.pop("CTO_SESSION_ID", None)

        proc = subprocess.run(
            ["bash", str(patched_path), "--id", stale_id],
            env=env, capture_output=True, text=True, timeout=15,
        )
        return proc.returncode == 0


def main() -> int:
    fails = 0
    r = test_owner_cto_routing(); fails += not r
    _mark(r, "owner_cto literal embedded in AppleScript")
    r = test_owner_winid_targets_by_id(); fails += not r
    _mark(r, "winid present -> AppleScript targets window by id")
    r = test_owner_winid_absent_falls_back_to_name(); fails += not r
    _mark(r, "winid absent -> AppleScript falls back to name match")
    r = test_owner_window_id_reader(); fails += not r
    _mark(r, "_owner_window_id reads digit content + rejects garbage")
    r = test_checks_both_title_surfaces(); fails += not r
    _mark(r, "AppleScript still checks tab name and session name")
    r = test_no_owner_falls_through(); fails += not r
    _mark(r, "absent owner_cto disables exact match branch")
    r = test_reuse_check_comes_first(); fails += not r
    _mark(r, "tab-reuse check precedes owner-window lookup")
    r = test_spawn_cto_collision(); fails += not r
    _mark(r, "spawn-cto.sh rejects live duplicate via --id")
    r = test_spawn_cto_drops_inherited_env(); fails += not r
    _mark(r, "spawn-cto.sh ignores inherited CTO_SESSION_ID")
    r = test_spawn_cto_reaps_stale_lock(); fails += not r
    _mark(r, "spawn-cto.sh reaps stale lock and reuses id via --id")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
