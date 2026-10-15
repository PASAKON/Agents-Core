"""terminal_window (CEO 2026-10-15): a host that sets `terminal_window: false` in config/hosts.yaml
starts every NEW session as a detached tmux session, with no iTerm window and no osascript.

Covered here:
  * lib.config.terminal_window(): a missing key is true, the Mac is false, an unknown host is true;
  * scripts/lib/coo_host.py terminal-window, the shell-facing answer every launcher reads;
  * scripts/spawn-cto.sh and scripts/spawn-cxo.sh, run for real against a hermetic org root with
    FAKE tmux and osascript on PATH: false -> `tmux new-session -d`, no osascript; true -> the
    iTerm window path, unchanged;
  * scripts/cto-claude.sh (CTO_CLAUDE_TEST_MODE): false -> no client_tty wait, no osascript lookup;
  * scripts/cxo-claude.sh and scripts/tab-title.sh: the osascript calls sit behind the same flag.

The delegate Mac path (tools/delegate._spawn_local) is covered in tests/test_w03_self_host_spawn.py.
Nothing here opens a window or starts a real tmux session.

Run: .venv/bin/python -m pytest tests/test_terminal_window.py
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config  # noqa: E402

SCRIPTS = ROOT / "scripts"
COO_HOST = SCRIPTS / "lib" / "coo_host.py"
MAC_ROOT_LINE = 'ROOT="/Users/gob/MoonieXHQ/Agents/Core"'


_HOSTS, _SELF_HOST = config.hosts, config.self_host  # the real cached functions, before any monkeypatch


@pytest.fixture(autouse=True)
def _fresh_config_caches():
    _HOSTS.cache_clear()
    _SELF_HOST.cache_clear()
    yield
    _HOSTS.cache_clear()
    _SELF_HOST.cache_clear()


# --- the reader --------------------------------------------------------------------------------


def test_the_mac_is_windowless_and_every_other_declared_host_keeps_its_window() -> None:
    assert config.terminal_window("mac") is False
    assert config.terminal_window("winbox") is True
    assert config.terminal_window("contabo") is True


def test_a_missing_key_means_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "hosts", lambda: {"box": {"os": "linux"}, "off": {"terminal_window": False},
                                                  "on": {"terminal_window": True}})
    assert config.terminal_window("box") is True
    assert config.terminal_window("off") is False
    assert config.terminal_window("on") is True


def test_an_unknown_host_fails_open_to_true() -> None:
    assert config.terminal_window("no-such-host") is True


# --- the shell-facing answer -------------------------------------------------------------------


def _coo_host(org_host: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, ORG_HOST=org_host)
    return subprocess.run([sys.executable, str(COO_HOST), "terminal-window"], env=env,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("host, answer", [("mac", "0"), ("winbox", "1"), ("contabo", "1")])
def test_coo_host_terminal_window_prints_the_flag_of_this_host(host: str, answer: str) -> None:
    r = _coo_host(host)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == answer


def test_coo_host_terminal_window_for_an_unresolvable_host_exits_3_and_prints_nothing() -> None:
    r = _coo_host("no-such-host")
    assert r.returncode == 3 and r.stdout.strip() == ""  # the launchers read that as "open the window"


# --- spawn-cto.sh / spawn-cxo.sh against a hermetic org root ------------------------------------

FAKE_TMUX = """#!/bin/sh
printf 'tmux %s\\n' "$*" >> "$FAKE_LOG_DIR/tmux.log"
exit 0
"""
FAKE_OSASCRIPT = """#!/bin/sh
printf 'osascript %s\\n' "$*" >> "$FAKE_LOG_DIR/osascript.log"
cat >> "$FAKE_LOG_DIR/osascript.log"
exit 0
"""


def _exe(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class Hq:
    """A throwaway org root plus fake binaries; the script under test is a copy with ROOT pointed at it."""

    def __init__(self, tmp: Path) -> None:
        self.root = tmp / "hq"
        self.bin = tmp / "bin"
        self.logs = tmp / "logs"
        for d in (self.root / "roles", self.root / "scripts", self.bin, self.logs):
            d.mkdir(parents=True)
        prefix = Path(sys.prefix)
        if not (prefix / "bin" / "activate").is_file():
            pytest.skip("needs a venv interpreter: the launchers `source .venv/bin/activate`")
        (self.root / ".venv").symlink_to(prefix)
        (self.root / "scripts" / "lib").symlink_to(SCRIPTS / "lib")
        for name in ("lib", "config", "policies"):
            (self.root / name).symlink_to(ROOT / name)
        for role in ("cto", "cmo"):
            (self.root / "roles" / f"{role}.md").write_text("# role\n", encoding="utf-8")
        _exe(self.bin / "tmux", FAKE_TMUX)
        _exe(self.bin / "osascript", FAKE_OSASCRIPT)
        _exe(self.bin / "python3", f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')

    def script(self, name: str) -> Path:
        src = (SCRIPTS / name).read_text(encoding="utf-8")
        assert src.count(MAC_ROOT_LINE) == 1, f"{name} changed shape; update MAC_ROOT_LINE"
        out = self.root.parent / name
        out.write_text(src.replace(MAC_ROOT_LINE, f'ROOT="{self.root}"'), encoding="utf-8")
        return out

    def run(self, name: str, *argv: str, host: str) -> subprocess.CompletedProcess:
        env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.root.parent),
            "FAKE_LOG_DIR": str(self.logs),
            "ORG_HOST": host,
            "LANG": "en_US.UTF-8",
            "CXO_NO_SESSION_WARN": "1",
        }
        return subprocess.run(["bash", str(self.script(name)), *argv], env=env, cwd=str(self.root),
                              capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)

    def log(self, name: str) -> list[str]:
        f = self.logs / name
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []


@pytest.fixture()
def hq(tmp_path: Path) -> Hq:
    return Hq(tmp_path)


def _sid(r: subprocess.CompletedProcess) -> str:
    m = re.search(r"\bid=([0-9a-f]{8})\b", r.stdout)
    assert m, r.stdout + r.stderr
    return m.group(1)


@pytest.mark.parametrize("script, argv, session_prefix", [
    ("spawn-cto.sh", (), "cto"),
    ("spawn-cxo.sh", ("--role", "cmo"), "cmo"),
])
def test_terminal_window_false_spawns_a_detached_tmux_session_and_never_osascript(
        hq: Hq, script: str, argv: tuple, session_prefix: str) -> None:
    r = hq.run(script, *argv, host="mac")
    assert r.returncode == 0, r.stderr
    sid = _sid(r)
    name = f"{session_prefix}-{sid}"
    run_file = hq.root / "state" / "locks" / f"{name}.run"
    assert f"tmux new-session -d -s {name} -c {hq.root} bash {run_file}" in hq.log("tmux.log")
    assert not [c for c in hq.log("tmux.log") if "new-session -A" in c], "no attached session without a window"
    assert hq.log("osascript.log") == [], "terminal_window=false must not call osascript"
    assert "no iTerm window" in r.stdout and f"terminal-open.sh {sid}" in r.stdout
    assert "cxo-claude.sh" in run_file.read_text() or "cto-claude.sh" in run_file.read_text()


@pytest.mark.parametrize("script, argv, session_prefix", [
    ("spawn-cto.sh", (), "cto"),
    ("spawn-cxo.sh", ("--role", "cmo"), "cmo"),
])
def test_terminal_window_true_still_opens_the_iterm_window(
        hq: Hq, script: str, argv: tuple, session_prefix: str) -> None:
    r = hq.run(script, *argv, host="winbox")  # winbox: no key, so true
    assert r.returncode == 0, r.stderr
    sid = _sid(r)
    name = f"{session_prefix}-{sid}"
    osa = "\n".join(hq.log("osascript.log"))
    assert 'tell application "iTerm"' in osa and "create window with default profile" in osa
    assert f"tmux new-session -A -s '{name}' -c '{hq.root}' bash" in osa
    assert not [c for c in hq.log("tmux.log") if "new-session" in c], "the window's own shell creates the session"
    assert "spawned iTerm window" in r.stdout


def test_with_logs_is_ignored_with_a_note_when_there_is_no_window(hq: Hq) -> None:
    r = hq.run("spawn-cto.sh", "--with-logs", host="mac")
    assert r.returncode == 0, r.stderr
    assert "--with-logs ignored" in r.stderr
    assert hq.log("osascript.log") == []


def test_an_unresolvable_host_keeps_the_window(hq: Hq) -> None:
    r = hq.run("spawn-cto.sh", host="no-such-host")
    assert r.returncode == 0, r.stderr
    assert hq.log("osascript.log"), "a host that will not resolve must keep today's behaviour"


# --- the launchers: no client_tty wait, no iTerm lookup when there is no window ---------------


@pytest.mark.skipif(not (ROOT / ".venv" / "bin" / "python").exists(),
                    reason="cto-claude.sh's MCP config generation needs a real .venv at repo root")
@pytest.mark.parametrize("host, window", [("mac", False), ("winbox", True)])
def test_cto_claude_skips_the_client_tty_wait_and_iterm_lookup_without_a_window(
        tmp_path: Path, host: str, window: bool) -> None:
    bin_dir, logs, locks = tmp_path / "bin", tmp_path / "logs", tmp_path / "locks"
    for d in (bin_dir, logs, locks):
        d.mkdir()
    _exe(bin_dir / "tmux", FAKE_TMUX)
    _exe(bin_dir / "osascript", FAKE_OSASCRIPT)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", FAKE_LOG_DIR=str(logs),
               CTO_CLAUDE_TEST_MODE="1", CTO_CLAUDE_LOCKS_DIR=str(locks), ORG_HOST=host,
               CTO_SESSION_ID="abcd1234", TMUX="/tmp/fake-tmux,1,0",
               # Contabo's /etc/org-flags/ORG_SINGLE_CLEVEL refuses a CTO on any other ORG_HOST
               # (tools/clevel_gate.py); the host is a stand-in here, so state the documented bypass.
               ORG_CLEVEL_EMERGENCY="1")
    env.pop("TMUX_PANE", None)
    r = subprocess.run(["bash", str(SCRIPTS / "cto-claude.sh")], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    tmux_calls = (logs / "tmux.log").read_text().splitlines() if (logs / "tmux.log").exists() else []
    asked_for_client = [c for c in tmux_calls if "client_tty" in c]
    osascript_called = (logs / "osascript.log").exists()
    assert bool(asked_for_client) is window
    assert osascript_called is window


def test_cxo_claude_and_tab_title_keep_osascript_behind_the_flag() -> None:
    """cxo-claude.sh has no test mode to run under, so the guard is checked in the source: the winid
    lookup runs only when TERMINAL_WINDOW is 1, and tab-title.sh's AppleScript fallback asks the same
    reader. Without this a PH or cxo session on the Mac would launch iTerm just to look for its tty."""
    cxo = (SCRIPTS / "cxo-claude.sh").read_text(encoding="utf-8")
    assert 'scripts/lib/coo_host.py" terminal-window' in cxo
    assert 'if [ "$TERMINAL_WINDOW" = "1" ] && [ -n "${TMUX:-}" ]; then' in cxo  # the client_tty wait
    assert 'if [ "$TERMINAL_WINDOW" = "1" ] && [ -n "$MY_TTY" ]; then\n  WINID="$(osascript' in cxo
    title = (SCRIPTS / "tab-title.sh").read_text(encoding="utf-8")
    assert re.search(r'if \[ "\$_TITLE_SET" != "1" \] && \[ "\$\(.*coo_host\.py" terminal-window.*\)" != "0" \]; then\nosascript', title)
