"""Contabo's shared tmux server: scripts/org-tmux-adopt.sh and its installer.

On 2026-10-02 `systemctl restart mooniex-sompong.service` killed every tmux session on
Contabo, because the one root tmux server had been started by sompong-supervise.sh and so
lived in that service's cgroup. org-tmux-adopt moves a server into its own scope,
org-tmux.scope; /etc/tmux.conf runs it when a server starts, before the first pane.

Nothing here touches a real systemd: busctl and logger are shell shims in tmp_path that
append their arguments to a file, and /proc is a fake tree named through ORG_TMUX_PROC.
Every script test runs under each POSIX shell this machine has (dash where installed, sh,
bash), because Contabo's /bin/sh is dash. One test runs a real tmux server on a private
socket, when tmux is installed, to prove the hook's two assumptions about tmux itself.
What systemd itself does with the scope (OOMPolicy, Delegate) was measured on Contabo and
is recorded in the script's header.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_org_tmux_adopt.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ADOPT = ROOT / "scripts" / "org-tmux-adopt.sh"
INSTALL = ROOT / "scripts" / "install-org-tmux-adopt.sh"
SHELLS = [s for s in ("/bin/dash", "/bin/sh", "/bin/bash") if Path(s).exists()]
SOCK = "/tmp/tmux-0/default"
PID = "4242"
SERVICE = "0::/system.slice/mooniex-sompong.service"
LOGIN = "0::/user.slice/user-0.slice/session-72408.scope"
VALUE = "v4lue-never-printed"
START = " StartTransientUnit ssa(sv)a(sa(sv)) "
PROPS = (" Slice s system.slice Delegate b true OOMPolicy s continue"
         " CollectMode s inactive-or-failed 0")


def _shim(bindir: Path, name: str, body: str) -> None:
    path = bindir / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


@pytest.fixture
def box(tmp_path):
    """A fake box: busctl/logger shims that log their calls, and a fake /proc."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    calls = tmp_path / "calls"
    # busctl fails when "<method>:<unit>" is named in $FAIL, like systemd refusing that call.
    # Otherwise it moves the server into the unit, as systemd does, unless $NOMOVE is set.
    _shim(bindir, "busctl",
          f'echo "busctl $*" >> "{calls}"\n'
          'for f in $FAIL; do [ "$f" = "$5:$7" ] && exit 1; done\n'
          f'[ -n "$NOMOVE" ] || echo "0::/system.slice/$7" > "$ORG_TMUX_PROC/{PID}/cgroup"\n'
          'exit 0\n')
    _shim(bindir, "logger", f'echo "logger $*" >> "{calls}"\n')
    proc = tmp_path / "proc"

    def set_server(cgroup: str, bus: tuple[str, ...] = (), pid: str = PID) -> None:
        (proc / pid).mkdir(parents=True, exist_ok=True)
        (proc / pid / "cgroup").write_text(cgroup + "\n")
        names = ("PATH", "HOME", *bus)
        (proc / pid / "environ").write_bytes(b"".join(f"{n}={VALUE}\0".encode() for n in names))

    def run(shell: str, *args: str, fail: str = "", nomove: bool = False):
        env = {"PATH": f"{bindir}:/usr/bin:/bin", "ORG_TMUX_PROC": str(proc), "FAIL": fail,
               "NOMOVE": "1" if nomove else "", "ORG_TMUX_WAIT": "3"}
        r = subprocess.run([shell, str(ADOPT), *args], env=env, capture_output=True,
                           text=True, timeout=30)
        lines = calls.read_text().splitlines() if calls.exists() else []
        calls.unlink(missing_ok=True)
        assert VALUE not in r.stdout + r.stderr + "\n".join(lines)
        return r, lines

    return set_server, run


def _bus(lines):
    return [line for line in lines if line.startswith("busctl ")]


def _starts(line: str, unit: str) -> bool:
    return f"{START}{unit} fail 6 PIDs au 1 {PID} " in line and line.endswith(PROPS)


def _logged(lines, text: str) -> bool:
    return any(line.startswith("logger ") and text in line for line in lines)


@pytest.mark.parametrize("shell", SHELLS)
def test_moves_a_server_out_of_a_service_cgroup(box, shell):
    set_server, run = box
    set_server(SERVICE)
    r, lines = run(shell, PID, SOCK)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    bus = _bus(lines)
    assert len(bus) == 1 and _starts(bus[0], "org-tmux.scope"), bus
    assert _logged(lines, "moved tmux server 4242 from /system.slice/mooniex-sompong.service "
                          "into org-tmux.scope")


@pytest.mark.parametrize("shell", SHELLS)
def test_joins_a_scope_that_is_still_alive(box, shell):
    set_server, run = box
    set_server(SERVICE)
    r, lines = run(shell, PID, SOCK, fail="StartTransientUnit:org-tmux.scope")
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    bus = _bus(lines)
    assert len(bus) == 2 and _starts(bus[0], "org-tmux.scope")
    assert " AttachProcessesToUnit ssau org-tmux.scope " in bus[1]
    assert bus[1].endswith(" 1 4242")
    assert _logged(lines, "into org-tmux.scope")


@pytest.mark.parametrize("shell", SHELLS)
def test_a_scope_that_refuses_the_server_gets_a_spare(box, shell):
    set_server, run = box
    set_server(SERVICE)
    r, lines = run(shell, PID, SOCK,
                   fail="StartTransientUnit:org-tmux.scope AttachProcessesToUnit:org-tmux.scope")
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    bus = _bus(lines)
    assert len(bus) == 3 and _starts(bus[2], "org-tmux-4242.scope")
    assert _logged(lines, "into org-tmux-4242.scope (org-tmux.scope exists and refused it)")


@pytest.mark.parametrize("shell", SHELLS)
def test_a_move_that_never_lands_is_logged(box, shell):
    """StartTransientUnit returns when the job is queued; the hook waits for the cgroup."""
    set_server, run = box
    set_server(SERVICE)
    started = time.monotonic()
    r, lines = run(shell, PID, SOCK, nomove=True)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    assert time.monotonic() - started >= 0.3  # it waited ORG_TMUX_WAIT tenths of a second
    assert len(_bus(lines)) == 1
    assert _logged(lines, "systemd accepted moving tmux server 4242 into org-tmux.scope, "
                          "but after 0 s it is still outside it")
    assert not _logged(lines, "moved tmux server")


@pytest.mark.parametrize("shell", SHELLS)
def test_a_refusal_is_logged_and_never_fails(box, shell):
    set_server, run = box
    set_server(SERVICE)
    r, lines = run(shell, PID, SOCK, fail="StartTransientUnit:org-tmux.scope "
                   "AttachProcessesToUnit:org-tmux.scope StartTransientUnit:org-tmux-4242.scope")
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")
    assert len(_bus(lines)) == 3
    assert _logged(lines, "could not move tmux server 4242 out of "
                          "/system.slice/mooniex-sompong.service")


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("cgroup", ["0::/system.slice/org-tmux.scope",
                                    "0::/system.slice/org-tmux-777.scope"])
def test_a_server_already_in_its_scope_is_left_alone(box, shell, cgroup):
    set_server, run = box
    set_server(cgroup)
    r, lines = run(shell, PID, SOCK)
    assert (r.returncode, lines) == (0, [])


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("var", ["XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"])
def test_a_login_server_with_a_user_bus_stays_in_its_session(box, shell, var):
    """Its panes live under user@0.service; only its login session keeps user@0 alive."""
    set_server, run = box
    set_server(LOGIN, bus=(var,))
    r, lines = run(shell, PID, SOCK)
    assert r.returncode == 0
    assert _bus(lines) == []
    assert _logged(lines, "left tmux server 4242 in /user.slice/user-0.slice/session-72408.scope")


@pytest.mark.parametrize("shell", SHELLS)
def test_a_login_server_without_a_user_bus_is_moved(box, shell):
    """Its panes follow the server, so they move with it."""
    set_server, run = box
    set_server(LOGIN)
    r, lines = run(shell, PID, SOCK)
    assert r.returncode == 0
    bus = _bus(lines)
    assert len(bus) == 1 and _starts(bus[0], "org-tmux.scope")


@pytest.mark.parametrize("shell", SHELLS)
def test_a_service_server_with_a_user_bus_is_moved_with_a_warning(box, shell):
    """A restart of its service would kill it; its panes are under user@0 either way."""
    set_server, run = box
    set_server(SERVICE, bus=("XDG_RUNTIME_DIR",))
    r, lines = run(shell, PID, SOCK)
    assert r.returncode == 0
    bus = _bus(lines)
    assert len(bus) == 1 and _starts(bus[0], "org-tmux.scope")
    assert _logged(lines, "tmux server 4242 has a user bus: its panes go to user@0.service")


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("sock", ["/tmp/tmux-0/cgtest", "/tmp/tmux-1001/default", ""])
def test_other_sockets_are_left_alone(box, shell, sock):
    set_server, run = box
    set_server(SERVICE)
    r, lines = run(shell, PID, sock)
    assert (r.returncode, lines) == (0, [])


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("pid", ["", "abc", "12x", "-1"])
def test_a_bad_pid_is_logged_not_acted_on(box, shell, pid):
    _, run = box
    r, lines = run(shell, pid, SOCK)
    assert r.returncode == 0
    assert _bus(lines) == []
    assert _logged(lines, "no server pid given")


@pytest.mark.parametrize("shell", SHELLS)
def test_an_unreadable_cgroup_is_logged_not_acted_on(box, shell):
    _, run = box
    r, lines = run(shell, "999", SOCK)
    assert r.returncode == 0
    assert _bus(lines) == []
    assert _logged(lines, "cannot read the cgroup of pid 999")


def test_scripts_are_executable():
    """tmux's run-shell runs the installed path directly, and the hook line's
    `>/dev/null 2>&1 || true` hides "Permission denied": on Contabo a copy without the
    exec bit did nothing and logged nothing (2026-10-02)."""
    assert os.access(ADOPT, os.X_OK), "git mode of scripts/org-tmux-adopt.sh must be 100755"
    assert os.access(INSTALL, os.X_OK), "git mode of scripts/install-org-tmux-adopt.sh must be 100755"


@pytest.mark.parametrize("shell", SHELLS)
def test_installer_adds_the_hook_once_and_keeps_the_config(tmp_path, shell):
    sbin = tmp_path / "sbin" / "org-tmux-adopt"
    sbin.parent.mkdir()
    conf = tmp_path / "tmux.conf"
    conf.write_text("set -g history-limit 5000\n")
    env = {"PATH": "/usr/bin:/bin", "ORG_TMUX_SBIN": str(sbin), "ORG_TMUX_CONF": str(conf)}
    for _ in range(2):
        r = subprocess.run([shell, str(INSTALL)], env=env, capture_output=True, text=True,
                           timeout=30)
        assert r.returncode == 0, r.stderr
    text = conf.read_text()
    hook = f"run-shell '{sbin} #{{pid}} #{{socket_path}} >/dev/null 2>&1 || true'"
    assert text.count(hook) == 1
    assert text.startswith("set -g history-limit 5000\n")
    # -b would let the first pane start before the server has moved.
    assert "run-shell -b" not in text
    assert sbin.read_bytes() == ADOPT.read_bytes()
    assert os.access(sbin, os.X_OK)


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck is not installed")
@pytest.mark.parametrize("script", [ADOPT, INSTALL], ids=lambda p: p.name)
def test_scripts_are_shellcheck_clean(script):
    r = subprocess.run(["shellcheck", "-s", "sh", str(script)], capture_output=True,
                       text=True, timeout=60)
    assert r.returncode == 0, r.stdout


@pytest.mark.skipif(not shutil.which("tmux"), reason="tmux is not installed")
def test_tmux_runs_the_hook_with_the_server_pid_before_the_first_pane(tmp_path):
    """The hook relies on two facts about tmux: a config-file run-shell expands #{pid} and
    #{socket_path} to the new server's own, and the first session's pane is forked only
    after that run-shell returns. A real server on a private socket checks both."""
    seen = tmp_path / "seen"
    order = tmp_path / "order"
    conf = tmp_path / "tmux.conf"
    conf.write_text(f"run-shell 'echo \"#{{pid}} #{{socket_path}}\" > {seen}; sleep 1; "
                    f"echo hook >> {order}'\n")
    name = f"orgadopt-{uuid.uuid4().hex[:8]}"
    tmux = ["tmux", "-L", name, "-f", str(conf)]
    env = {k: v for k, v in os.environ.items() if k != "TMUX"}
    try:
        subprocess.run([*tmux, "new-session", "-d", "-s", "t", f"echo pane >> {order}; sleep 30"],
                       env=env, check=True, timeout=30)
        for _ in range(50):
            if order.exists() and len(order.read_text().split()) >= 2:
                break
            time.sleep(0.1)
        server = subprocess.run([*tmux, "display-message", "-p", "#{pid} #{socket_path}"],
                                env=env, capture_output=True, text=True, timeout=10,
                                check=True).stdout.strip()
        assert seen.read_text().strip() == server
        assert order.read_text().split() == ["hook", "pane"]
    finally:
        subprocess.run([*tmux, "kill-server"], env=env, capture_output=True, timeout=10)
