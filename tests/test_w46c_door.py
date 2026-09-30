"""Org Mesh W4.6c: deploy/join/door.sh, the hub's join door ("the door is closed by default").

door.sh runs as root on Contabo and opens or closes the public join endpoint: systemctl for
org-join.service, docker compose for the org-join-proxy container, systemd-run for the timer that
closes it again, and `tools.hq_join approve` for the F1 gate. Nothing here touches a real systemd
or docker: systemctl, docker, systemd-run, python3 and setpriv are shell shims in tmp_path, named
to the script through the ORG_JOIN_* variables the script documents, and they keep their state in
plain files. Every test runs under each POSIX shell this machine has (dash where installed, the
system sh, bash), because Contabo runs dash and the Mac's /bin/sh is bash 3.2 in POSIX mode.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w46c_door.py
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOOR = ROOT / "deploy" / "join" / "door.sh"
NOW = 1790000000                                  # a fixed clock: 2026-09-21T13:33:20Z
SHELLS = [s for s in ("/bin/dash", "/bin/sh", "/bin/bash") if Path(s).exists()]
not_root = pytest.mark.skipif(os.geteuid() == 0, reason="this test needs a non-root user")


def _utc(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


SYSTEMCTL = r'''#!/bin/sh
# shim: state lives in $SHIM_STATE/<name>; every call is one line in $SHIM_STATE/calls.log
echo "systemctl $*" >>"$SHIM_STATE/calls.log"
verb=$1
shift
case $verb in
    start)
        [ -e "$SHIM_STATE/fail_service_start" ] && { echo "Job for org-join.service failed" >&2; exit 1; }
        : >"$SHIM_STATE/service"
        ;;
    stop)
        [ -e "$SHIM_STATE/stuck" ] && exit 0
        case $1 in
            org-join.service) rm -f "$SHIM_STATE/service" ;;
            org-join-door-close.timer) rm -f "$SHIM_STATE/timer" ;;
        esac
        ;;
    is-active)
        [ "$1" = --quiet ] && shift
        [ -e "$SHIM_STATE/dies_after_start" ] && exit 3
        case $1 in
            org-join.service) [ -e "$SHIM_STATE/service" ] && exit 0 ;;
            org-join-door-close.timer) [ -e "$SHIM_STATE/timer" ] && exit 0 ;;
        esac
        exit 3
        ;;
    reset-failed) ;;
    *) echo "shim systemctl: unexpected $verb" >&2; exit 99 ;;
esac
'''

DOCKER = r'''#!/bin/sh
echo "docker $*" >>"$SHIM_STATE/calls.log"
case $1 in
    compose)
        case "$*" in
            *" up -d"*)
                [ -e "$SHIM_STATE/fail_proxy_start" ] && { echo "no such network n8n_default" >&2; exit 1; }
                : >"$SHIM_STATE/proxy" ;;
            *" down"*) [ -e "$SHIM_STATE/stuck" ] || rm -f "$SHIM_STATE/proxy" ;;
        esac
        ;;
    ps) [ -e "$SHIM_STATE/proxy" ] && echo 4f1c2a9d7b3e ;;
    rm) [ -e "$SHIM_STATE/stuck" ] || rm -f "$SHIM_STATE/proxy" ;;
    *) echo "shim docker: unexpected $1" >&2; exit 99 ;;
esac
exit 0
'''

SYSTEMD_RUN = r'''#!/bin/sh
echo "systemd-run $*" >>"$SHIM_STATE/calls.log"
[ -e "$SHIM_STATE/fail_timer" ] && { echo "Failed to connect to bus" >&2; exit 1; }
if [ -e "$SHIM_STATE/timer" ]; then
    echo "Failed to start transient timer unit: Unit org-join-door-close.timer already exists." >&2
    exit 1
fi
: >"$SHIM_STATE/timer"
for a in "$@"; do printf '%s\n' "$a"; done >"$SHIM_STATE/timer.argv"
echo "Running timer as unit: org-join-door-close.timer" >&2
'''

PYTHON3 = r'''#!/bin/sh
# shim for /usr/bin/python3 running infisical_setup.py ... -- setpriv ... -- venv-python -m tools.hq_join approve
echo "python3 $*" >>"$SHIM_STATE/calls.log"
echo "[infisical run] project Agents-Core prod: 3 variable names injected (values not shown)" >&2
if [ -e "$SHIM_STATE/approve_refused" ]; then
    echo "hq_join: refused (fingerprint_mismatch): the key on file does not match" >&2
    exit 2
fi
echo '{"ok": true, "host": "node-a", "status": "pending_identity", "changed": true}'
'''


@pytest.fixture(params=SHELLS)
def shell(request):
    return request.param


class Door:
    def __init__(self, tmp_path: Path, shell: str, dirname: str = "core"):
        self.shell = shell
        self.state = tmp_path / "state"
        self.state.mkdir()
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        self.core = tmp_path / dirname
        (self.core / "deploy" / "join").mkdir(parents=True)
        (self.core / "deploy" / "join" / "docker-compose.join-proxy.yml").write_text("name: org-join-proxy\n")
        self.home = tmp_path / "door-home"
        self.script = tmp_path / "runner" / "door.sh"            # where the card runner left it
        self.script.parent.mkdir()
        shutil.copyfile(DOOR, self.script)
        for name, body in (("systemctl", SYSTEMCTL), ("docker", DOCKER), ("systemd-run", SYSTEMD_RUN),
                           ("python3", PYTHON3), ("setpriv", "#!/bin/sh\nexit 0\n")):
            p = self.bin / name
            p.write_text(body)
            p.chmod(0o755)
        self.env = {
            "PATH": "/usr/bin:/bin",
            "SHIM_STATE": str(self.state),
            "ORG_JOIN_CORE": str(self.core),
            "ORG_JOIN_DOOR_HOME": str(self.home),
            "ORG_JOIN_SYSTEMCTL": str(self.bin / "systemctl"),
            "ORG_JOIN_DOCKER": str(self.bin / "docker"),
            "ORG_JOIN_SYSTEMD_RUN": str(self.bin / "systemd-run"),
            "ORG_JOIN_PYTHON3": str(self.bin / "python3"),
            "ORG_JOIN_SETPRIV": str(self.bin / "setpriv"),
            "ORG_JOIN_NOW_EPOCH": str(NOW),
            "ORG_JOIN_SETTLE_S": "0",
            "ORG_JOIN_DOOR_TEST": "1",
        }

    def run(self, *args: str, env: dict | None = None, script: Path | None = None):
        return subprocess.run([self.shell, str(script or self.script), *args], capture_output=True, text=True,
                              env={**self.env, **(env or {})}, timeout=60)

    def flag(self, name: str):
        (self.state / name).write_text("")

    def up(self, name: str) -> bool:
        return (self.state / name).exists()

    def calls(self) -> list[str]:
        p = self.state / "calls.log"
        return p.read_text().splitlines() if p.exists() else []

    def called(self, prefix: str) -> list[str]:
        return [c for c in self.calls() if c.startswith(prefix)]

    @property
    def door_copy(self) -> Path:
        return self.home / "door.sh"


@pytest.fixture
def door(tmp_path, shell):
    return Door(tmp_path, shell)


@pytest.fixture
def sdoor(tmp_path):
    """One shell only (dash: the strictest, and the one Contabo runs), for the big argument matrices."""
    return Door(tmp_path, SHELLS[0])


def _opened(d: Door, *args):
    r = d.run("open", *args)
    assert r.returncode == 0, r.stderr
    return r


# ------------------------------------------------------------ open

def test_open_prints_one_line_with_the_close_time(door):
    r = _opened(door)
    assert r.stdout == f"open until {_utc(NOW + 30 * 60)}\n"
    assert r.stderr == ""
    assert door.up("service") and door.up("proxy") and door.up("timer")


def test_open_schedules_its_own_close_before_it_starts_anything(door):
    _opened(door, "--minutes", "45")
    calls = door.calls()
    timer_at = next(i for i, c in enumerate(calls) if c.startswith("systemd-run"))
    start_at = next(i for i, c in enumerate(calls) if c.startswith("systemctl start org-join.service"))
    up_at = next(i for i, c in enumerate(calls) if " up -d" in c)
    assert timer_at < start_at < up_at
    argv = (door.state / "timer.argv").read_text().splitlines()
    assert argv == ["--on-active=45m", "--timer-property=AccuracySec=1s", "--unit", "org-join-door-close",
                    str(door.door_copy), "close"]


def test_the_timer_runs_a_copy_that_outlives_the_file_the_card_ran_from(door):
    _opened(door)
    assert door.door_copy.read_bytes() == DOOR.read_bytes()
    assert stat.S_IMODE(door.door_copy.stat().st_mode) == 0o700
    assert stat.S_IMODE(door.home.stat().st_mode) == 0o700
    door.script.unlink()                                           # the card runner cleans up
    argv = (door.state / "timer.argv").read_text().splitlines()
    r = subprocess.run([door.shell, *argv[-2:]], capture_output=True, text=True, env=door.env, timeout=60)
    assert (r.returncode, r.stdout) == (0, "closed\n")             # what the timer does when it fires
    assert not door.up("service") and not door.up("proxy") and not door.up("timer")


def test_open_starts_the_service_then_the_proxy_compose_of_the_checkout(door):
    _opened(door)
    compose = door.core / "deploy" / "join" / "docker-compose.join-proxy.yml"
    assert door.called("docker compose") == [f"docker compose -f {compose} up -d"]
    assert door.called("systemctl start") == ["systemctl start org-join.service"]


@pytest.mark.parametrize("args,minutes", [
    ((), 30), (("--minutes", "1"), 1), (("--minutes", "120"), 120), (("--minutes=15",), 15),
    (("--minutes", "007"), 7), (("--minutes", "010"), 10),
])
def test_the_minutes_default_to_30_and_take_1_to_120(door, args, minutes):
    r = _opened(door, *args)
    assert r.stdout == f"open until {_utc(NOW + minutes * 60)}\n"
    assert f"--on-active={minutes}m" in (door.state / "timer.argv").read_text().splitlines()


@pytest.mark.parametrize("bad", ["0", "00", "121", "500", "-5", "+5", "abc", "", "1.5", "1e2", "30m", " 5",
                                 "5 ", "99999999999999999999", "٣٠", "3;true", "$(true)"])
def test_bad_minutes_are_refused_and_nothing_is_started(sdoor, bad):
    r = sdoor.run("open", "--minutes", bad)
    assert r.returncode != 0 and r.stdout == ""
    assert "minutes" in r.stderr
    assert sdoor.calls() == [] and not sdoor.home.exists()


@pytest.mark.parametrize("args", [["--minutes"], ["--minute", "5"], ["5"], ["--minutes", "5", "extra"], ["--now"]])
def test_open_with_other_arguments_is_a_usage_error(sdoor, args):
    r = sdoor.run("open", *args)
    assert r.returncode == 2 and "usage:" in r.stderr and r.stdout == ""
    assert sdoor.calls() == []


def test_a_second_open_replaces_the_timer_and_the_door_stays_open(door):
    _opened(door, "--minutes", "10")
    r = _opened(door, "--minutes", "60")
    assert r.stdout == f"open until {_utc(NOW + 60 * 60)}\n"
    assert "--on-active=60m" in (door.state / "timer.argv").read_text().splitlines()
    assert door.called("systemctl stop org-join-door-close.timer")          # the old one went first
    assert door.up("service") and door.up("proxy") and door.up("timer")


def test_if_the_close_cannot_be_scheduled_nothing_is_opened(door):
    door.flag("fail_timer")
    r = door.run("open")
    assert r.returncode == 1 and r.stdout == ""
    assert "could not schedule the close, so nothing was opened" in r.stderr
    assert not door.up("service") and not door.up("proxy")
    assert door.called("systemctl start") == [] and door.called("docker compose") == []


def test_if_the_service_does_not_start_the_door_is_closed_again(door):
    door.flag("fail_service_start")
    r = door.run("open")
    assert r.returncode == 1 and r.stdout == ""
    assert "could not start org-join.service, door closed again" in r.stderr
    assert "Job for org-join.service failed" in r.stderr
    assert not door.up("service") and not door.up("proxy") and not door.up("timer")


def test_if_the_proxy_does_not_start_the_service_is_stopped_again(door):
    door.flag("fail_proxy_start")
    r = door.run("open")
    assert r.returncode == 1 and r.stdout == ""
    assert "could not start the proxy, door closed again" in r.stderr
    assert not door.up("service") and not door.up("proxy") and not door.up("timer")


def test_if_the_service_dies_right_after_starting_open_does_not_claim_success(door):
    door.flag("dies_after_start")                                  # is-active says no for everything
    r = door.run("open")
    assert r.returncode == 1 and "open until" not in r.stdout
    assert "door closed again" in r.stderr and "journalctl -u org-join.service" in r.stderr
    assert door.called("systemctl stop org-join.service") and door.called("docker compose -f")


def test_open_without_the_compose_file_refuses_before_scheduling_anything(door):
    (door.core / "deploy" / "join" / "docker-compose.join-proxy.yml").unlink()
    r = door.run("open")
    assert r.returncode == 1 and "docker-compose.join-proxy.yml" in r.stderr
    assert door.calls() == []


# ------------------------------------------------------------ close

def test_close_stops_the_proxy_the_service_and_the_timer_and_says_closed(door):
    _opened(door)
    r = door.run("close")
    assert (r.returncode, r.stdout, r.stderr) == (0, "closed\n", "")
    assert not door.up("service") and not door.up("proxy") and not door.up("timer")
    assert door.called("docker compose")[-1].endswith(" down")
    assert door.called("systemctl stop org-join-door-close.timer")


def test_close_is_idempotent_and_needs_nothing_to_be_open(door):
    for _ in range(3):
        r = door.run("close")
        assert (r.returncode, r.stdout) == (0, "closed\n")


def test_close_without_the_compose_file_still_removes_the_container(door):
    _opened(door)
    (door.core / "deploy" / "join" / "docker-compose.join-proxy.yml").unlink()
    r = door.run("close")
    assert (r.returncode, r.stdout) == (0, "closed\n")
    assert door.called("docker rm -f org-join-proxy") and not door.up("proxy")


def test_close_never_says_closed_when_something_is_still_running(door):
    _opened(door)
    door.flag("stuck")                                             # every stop "succeeds" and does nothing
    r = door.run("close")
    assert r.returncode == 1 and "closed" not in r.stdout
    assert "NOT closed" in r.stderr and "docker rm -f org-join-proxy" in r.stderr


def test_close_takes_no_arguments(door):
    r = door.run("close", "now")
    assert r.returncode == 2 and "usage:" in r.stderr and door.calls() == []


# ------------------------------------------------------------ status

def test_status_closed(door):
    r = door.run("status")
    assert (r.returncode, r.stdout) == (0, "closed\n")


def test_status_open_shows_the_close_time(door):
    _opened(door, "--minutes", "20")
    r = door.run("status")
    assert (r.returncode, r.stdout) == (0, f"open until {_utc(NOW + 20 * 60)}\n")


def test_status_after_close_is_closed(door):
    _opened(door)
    door.run("close")
    assert door.run("status").stdout == "closed\n"


def test_status_says_so_when_only_one_half_is_up(door):
    _opened(door)
    (door.state / "proxy").unlink()
    assert door.run("status").stdout == "half open: service up, proxy down; run close\n"
    door.flag("proxy")
    (door.state / "service").unlink()
    assert door.run("status").stdout == "half open: service down, proxy up; run close\n"


def test_status_says_so_when_the_timer_is_gone(door):
    _opened(door)
    (door.state / "timer").unlink()
    assert door.run("status").stdout == "open, no close timer scheduled; run close\n"


def test_status_needs_no_root_and_changes_nothing(door):
    r = door.run("status", env={"ORG_JOIN_DOOR_TEST": ""})
    assert r.returncode == 0
    assert all(c.startswith(("systemctl is-active", "docker ps")) for c in door.calls())


# ------------------------------------------------------------ approve

def test_approve_runs_hq_join_approve_as_secretary_and_prints_the_result_only(door):
    r = door.run("approve", "--host", "node-a", "--fingerprint", "9aqmcac8")
    assert r.returncode == 0
    assert r.stdout == '{"ok": true, "host": "node-a", "status": "pending_identity", "changed": true}\n'
    assert r.stderr == ""
    (call,) = door.called("python3")
    assert call == (f"python3 {door.core}/tools/infisical_setup.py run Agents-Core prod --as contabo -- "
                    f"{door.bin}/setpriv --reuid=secretary --regid=secretary --init-groups -- "
                    f"{door.core}/.venv/bin/python -m tools.hq_join approve --host node-a --fingerprint 9aqmcac8")


def test_approve_passes_the_refusal_and_its_exit_code_through(door):
    door.flag("approve_refused")
    r = door.run("approve", "--host", "node-a", "--fingerprint", "9aqmcac8")
    assert r.returncode == 2
    assert "hq_join: refused (fingerprint_mismatch)" in r.stdout and "[infisical run]" not in r.stdout


def test_approve_does_not_touch_the_door(door):
    door.run("approve", "--host", "node-a", "--fingerprint", "9aqmcac8")
    assert [c for c in door.calls() if not c.startswith("python3")] == []


@pytest.mark.parametrize("host", ["", "-x", "--host", "a b", "node #1", "node(1)", "x;y", "$(id)", "`id`",
                                  "a|b", "a&b", "a>b", "a\nb", "โหนด", "node/1", "a'b", 'a"b', "x" * 64])
def test_approve_refuses_a_host_that_is_not_a_host_name(sdoor, host):
    r = sdoor.run("approve", "--host", host, "--fingerprint", "9aqmcac8")
    assert r.returncode != 0 and r.stdout == ""
    assert sdoor.called("python3") == []


@pytest.mark.parametrize("fp", ["", "9aqmcac", "9aqmcac88", "9aqm cac", "9aqmcac!", "9aqmcac;", "$(id)abcd", "-9aqmcac",
                                "ไทยไทยไทย", "9aqmcac\n"])
def test_approve_refuses_a_fingerprint_that_is_not_eight_letters_and_digits(sdoor, fp):
    r = sdoor.run("approve", "--host", "node-a", "--fingerprint", fp)
    assert r.returncode != 0 and r.stdout == ""
    assert sdoor.called("python3") == []


@pytest.mark.parametrize("args", [[], ["--host", "node-a"], ["--fingerprint", "9aqmcac8"], ["node-a", "9aqmcac8"],
                                  ["--host"], ["--host", "node-a", "--fingerprint"], ["--host", "a", "--x", "b"]])
def test_approve_needs_both_arguments(sdoor, args):
    r = sdoor.run("approve", *args)
    assert r.returncode == 2 and "usage:" in r.stderr
    assert sdoor.called("python3") == []


# ------------------------------------------------------------ root, usage, paths

@not_root
@pytest.mark.parametrize("verb", [["open"], ["close"], ["approve", "--host", "node-a", "--fingerprint", "9aqmcac8"]])
def test_a_verb_that_changes_things_refuses_to_run_as_a_normal_user(sdoor, verb):
    r = sdoor.run(*verb, env={"ORG_JOIN_DOOR_TEST": ""})
    assert r.returncode == 1 and "run as root" in r.stderr and r.stdout == ""
    assert sdoor.calls() == [] and not sdoor.home.exists()


@pytest.mark.parametrize("args", [[], ["nope"], ["OPEN"], ["--help"], ["open", "--minutes", "5", "close"]])
def test_no_verb_or_an_unknown_verb_prints_usage_and_does_nothing(sdoor, args):
    r = sdoor.run(*args)
    assert r.returncode == 2 and "usage:" in r.stderr and r.stdout == ""
    assert sdoor.calls() == []


@pytest.mark.parametrize("dirname", ["core with spaces", "core #1 (x)", "โหนด"])
def test_paths_with_spaces_hash_parentheses_and_thai_survive(tmp_path, shell, dirname):
    d = Door(tmp_path, shell, dirname=dirname)
    d.home = tmp_path / f"home {dirname}"
    d.env["ORG_JOIN_DOOR_HOME"] = str(d.home)
    r = d.run("open")
    assert r.returncode == 0, r.stderr
    assert d.door_copy.exists()
    argv = (d.state / "timer.argv").read_text().splitlines()
    assert argv[-2:] == [str(d.door_copy), "close"]
    assert d.run("close").stdout == "closed\n"
    assert d.run("approve", "--host", "node-a", "--fingerprint", "9aqmcac8").returncode == 0
    assert str(d.core) in d.called("python3")[0]


def test_the_door_writes_only_its_own_folder(tmp_path, shell):
    d = Door(tmp_path, shell)
    before = set(tmp_path.rglob("*"))
    _opened(d)
    d.run("close")
    added = set(tmp_path.rglob("*")) - before
    allowed = (d.home, d.state, d.script.parent)
    assert all(any(a == p or a in p.parents for a in allowed) for p in added), sorted(map(str, added))
    assert not (d.home / "close_at").exists()                      # close removes the clock file


# ------------------------------------------------------------ the file itself

def test_door_sh_is_posix_sh_ascii_and_executable():
    text = DOOR.read_text(encoding="ascii")
    assert text.startswith("#!/bin/sh\n")
    assert os.access(DOOR, os.X_OK)
    assert "set -eu" in text
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    for bashism in ("[[", "]]", "local ", "function ", "echo -e", "<<<", "&>", "=(", "${!", "declare ", "source ",
                    "read -p", "set -o pipefail", "<(", ";&"):
        assert bashism not in code, bashism
    assert not re.search(r"(?<!\^)\$'", code)                     # $'...' is not POSIX
    for gnu in ("readlink -f", "timeout ", "sed -i", "grep -P", "xargs -r"):
        assert gnu not in code, gnu
    # `date -d` exists only behind the `date --version` (GNU) check; BSD date gets `-r`
    assert code.count("date -u -d") == 1 and code.count("date --version") == 1
    assert code.index("date --version") < code.index("date -u -d") < code.index("date -u -r")


def test_door_sh_never_prints_the_environment_or_traces():
    code = "\n".join(ln for ln in DOOR.read_text().splitlines() if not ln.lstrip().startswith("#"))
    for leak in ("printenv", "set -x", "set -v", "env >", " env ", "export "):
        assert leak not in code, leak
    assert not re.search(r"postgres(ql)?://|ORG_DB_URL|ORG_JOIN_DB_URL|tskey-|AGE-SECRET-KEY", code)


@pytest.mark.parametrize("sh", SHELLS)
def test_door_sh_parses_under_every_shell(sh):
    r = subprocess.run([sh, "-n", str(DOOR)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck is not installed")
def test_door_sh_is_shellcheck_clean():
    r = subprocess.run(["shellcheck", "-s", "sh", str(DOOR)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout
