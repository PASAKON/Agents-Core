"""Tests for send_to_cto routing isolation (issue #4).

Verifies that:
1. With cto_id set and winid missing -> message is orphaned, not broadcast
2. With cto_id set and winid present but window gone -> message orphaned
3. With cto_id set and winid present -> AppleScript targets exact window id
4. With cto_id=None (default) -> orphan to unowned.log, NO broadcast (issue #15)
4b. With cto_id=None + SEND_TO_CTO_BROADCAST=1 -> legacy broadcast (opt-in)
5. _read_winid returns None for missing/invalid files; reads <role>-<id>.winid
6. _log_orphan writes the expected log line

Run via:   python scripts/test_send_to_cto_routing.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.send_to_cto import _log_orphan, _read_winid, send  # noqa: E402


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def test_read_winid_present(tmp_path: Path) -> bool:
    p = tmp_path / "cto-abc.winid"
    p.write_text("1234\n")
    import tools.send_to_cto as m
    orig = m.LOCKS_DIR
    m.LOCKS_DIR = tmp_path
    try:
        return _read_winid("abc") == "1234"
    finally:
        m.LOCKS_DIR = orig


def test_read_winid_missing(tmp_path: Path) -> bool:
    import tools.send_to_cto as m
    orig = m.LOCKS_DIR
    m.LOCKS_DIR = tmp_path
    try:
        return _read_winid("nope") is None
    finally:
        m.LOCKS_DIR = orig


def test_read_winid_garbage(tmp_path: Path) -> bool:
    p = tmp_path / "cto-bad.winid"
    p.write_text("not-a-number\n")
    import tools.send_to_cto as m
    orig = m.LOCKS_DIR
    m.LOCKS_DIR = tmp_path
    try:
        return _read_winid("bad") is None
    finally:
        m.LOCKS_DIR = orig


def test_log_orphan_writes_line(tmp_path: Path) -> bool:
    import tools.send_to_cto as m
    orig = m.STATE_DIR
    m.STATE_DIR = tmp_path
    try:
        _log_orphan("cto1", "task-abc", "developer", "hello world")
        log = tmp_path / "orphan-dev-replies-cto1.log"
        if not log.exists():
            return False
        content = log.read_text()
        return (
            "from=task-abc" in content
            and "role=developer" in content
            and "hello world" in content
        )
    finally:
        m.STATE_DIR = orig


def test_missing_winid_orphans_not_broadcasts(tmp_path: Path) -> bool:
    """When winid file is absent, send() must orphan and return False without
    calling osascript at all."""
    import tools.send_to_cto as m
    m.LOCKS_DIR = tmp_path
    m.STATE_DIR = tmp_path

    with mock.patch("subprocess.run") as mock_run:
        result = send("task-xyz", "hello", role="developer", cto_id="cto9")
        assert not mock_run.called, "osascript must not be called when winid missing"
    orphan = tmp_path / "orphan-dev-replies-cto9.log"
    return result is False and orphan.exists()


def test_strict_routing_uses_window_id(tmp_path: Path) -> bool:
    """When winid is present, the AppleScript must use 'window id <n>'
    and NOT loop over all windows."""
    import tools.send_to_cto as m
    m.LOCKS_DIR = tmp_path
    m.STATE_DIR = tmp_path
    (tmp_path / "cto-abc123.winid").write_text("5678\n")

    captured_scripts: list[str] = []

    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            captured_scripts.append(cmd[2])
        r = mock.MagicMock()
        r.returncode = 0
        r.stdout = "1"
        return r

    with mock.patch("subprocess.run", side_effect=fake_run):
        result = send("task-abc", "hi", role="developer", cto_id="abc123")

    if not captured_scripts:
        return False
    script = captured_scripts[0]
    return (
        result is True
        and "window id 5678" in script
        and "repeat with w in windows" not in script
    )


def test_gone_window_orphans(tmp_path: Path) -> bool:
    """When winid exists but osascript returns '0' (window gone), orphan."""
    import tools.send_to_cto as m
    m.LOCKS_DIR = tmp_path
    m.STATE_DIR = tmp_path
    (tmp_path / "cto-gone1.winid").write_text("9999\n")

    def fake_run(cmd, **kwargs):
        r = mock.MagicMock()
        r.returncode = 0
        r.stdout = "0"
        return r

    with mock.patch("subprocess.run", side_effect=fake_run):
        result = send("task-abc", "hi", role="developer", cto_id="gone1")

    orphan = tmp_path / "orphan-dev-replies-gone1.log"
    return result is False and orphan.exists()


def test_none_orphans_unowned_by_default(tmp_path: Path) -> bool:
    """cto_id=None without SEND_TO_CTO_BROADCAST must NOT call osascript;
    it orphans to orphan-dev-replies-unowned.log and returns False (issue #15)."""
    import tools.send_to_cto as m
    m.LOCKS_DIR = tmp_path
    m.STATE_DIR = tmp_path

    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SEND_TO_CTO_BROADCAST", None)
        with mock.patch("subprocess.run") as mock_run:
            result = send("task-abc", "hi", role="developer", cto_id=None)
            assert not mock_run.called, "osascript must not run when ownerless + no opt-in"

    orphan = tmp_path / "orphan-dev-replies-unowned.log"
    return result is False and orphan.exists() and "task-abc" in orphan.read_text()


def test_none_broadcasts_when_optin(tmp_path: Path) -> bool:
    """With SEND_TO_CTO_BROADCAST=1, cto_id=None restores the legacy
    broadcast to all CTO Chat tabs (single-CTO opt-in)."""
    import tools.send_to_cto as m
    m.LOCKS_DIR = tmp_path
    m.STATE_DIR = tmp_path

    captured_scripts: list[str] = []

    def fake_run(cmd, **kwargs):
        if cmd[0] == "osascript":
            captured_scripts.append(cmd[2])
        r = mock.MagicMock()
        r.returncode = 0
        r.stdout = "1"
        return r

    with mock.patch.dict(os.environ, {"SEND_TO_CTO_BROADCAST": "1"}), \
            mock.patch("subprocess.run", side_effect=fake_run):
        result = send("task-abc", "hi", role="developer", cto_id=None)

    if not captured_scripts:
        return False
    script = captured_scripts[0]
    return (
        result is True
        and "repeat with w in windows" in script
        and "CTO Chat" in script
        and "window id" not in script
    )


def test_read_winid_role_specific(tmp_path: Path) -> bool:
    """_read_winid(cto_id, role) reads <role>-<id>.winid, and for a non-cto
    role falls back to the legacy cto-<id>.winid when the role file is absent."""
    import tools.send_to_cto as m
    orig = m.LOCKS_DIR
    m.LOCKS_DIR = tmp_path
    try:
        # role-specific file wins
        (tmp_path / "cfo-abc123.winid").write_text("4242\n")
        role_hit = _read_winid("abc123", "cfo") == "4242"
        # legacy cto-<id> fallback for a non-cto role
        (tmp_path / "cto-legacy01.winid").write_text("7admin\n")  # not all-digits → invalid
        (tmp_path / "cto-legacy02.winid").write_text("8080\n")
        legacy_hit = _read_winid("legacy02", "cfo") == "8080"
        # no file at all → None
        miss = _read_winid("nope", "cmo") is None
        return role_hit and legacy_hit and miss
    finally:
        m.LOCKS_DIR = orig


def main() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)

        r = test_read_winid_present(tmp); fails += not r
        _mark(r, "_read_winid returns digits when file present")
        r = test_read_winid_missing(tmp); fails += not r
        _mark(r, "_read_winid returns None when file absent")
        r = test_read_winid_garbage(tmp); fails += not r
        _mark(r, "_read_winid returns None for non-digit content")
        r = test_log_orphan_writes_line(tmp); fails += not r
        _mark(r, "_log_orphan writes from/role/msg to log file")
        r = test_missing_winid_orphans_not_broadcasts(tmp); fails += not r
        _mark(r, "missing winid -> orphan, no osascript broadcast")
        r = test_strict_routing_uses_window_id(tmp); fails += not r
        _mark(r, "cto_id set + winid present -> AppleScript uses window id N")
        r = test_gone_window_orphans(tmp); fails += not r
        _mark(r, "osascript returns 0 (window gone) -> orphan logged")
        r = test_none_orphans_unowned_by_default(tmp); fails += not r
        _mark(r, "cto_id=None (default) -> orphan to unowned.log, no osascript")
        r = test_none_broadcasts_when_optin(tmp); fails += not r
        _mark(r, "cto_id=None + SEND_TO_CTO_BROADCAST=1 -> legacy broadcast")
        r = test_read_winid_role_specific(tmp); fails += not r
        _mark(r, "_read_winid reads <role>-<id>.winid + legacy cto-<id> fallback")

    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
