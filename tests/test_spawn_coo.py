"""SomPong (the COO) is ONE session, on Contabo: the launcher refusal, /spawn-coo, the pieces around them.

docs/design/sompong-coo-session.md "Singleton + spawn" is the contract. What is tested here:

  * scripts/cxo-claude.sh --role coo refuses everywhere but Contabo (host from lib.config,
    unresolved host = refused), refuses --session, refuses a second live launcher, and on
    Contabo hands the real `claude` the channel flag, the SomPong .mcp.json, --remote-control
    SomPong, an empty environment plus a short allowlist, run as the unprivileged user;
  * scripts/spawn-coo.sh's four decisions: alive -> report, none -> start, stray local ->
    refuse, no route -> print the exact command;
  * the small helpers (coo_host.py, cxo_hooks_settings.py), the tmux-name override, the
    singleton refusals in send_to_cxo / the relay, the letter sharing for SomPong's user.

Everything runs against FAKES on PATH (tmux, ps, sleep, systemctl, ssh, runuser, claude) in a tmp
dir -- never a real tmux, systemd, ssh, `claude` or tools.worktree.create_worktree. The launcher
tests use a hermetic copy of the org root (symlinks to the code, a private state/ and ORG_ROOT).

Run: .venv/bin/python -m pytest tests/test_spawn_coo.py
"""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import venv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SPAWN_COO = ROOT / "scripts" / "spawn-coo.sh"
LAUNCHER = ROOT / "scripts" / "cxo-claude.sh"
CONTABO_COMMAND = "bash /opt/MoonieXHQ/Agents/Core/scripts/spawn-coo.sh"
REFUSAL = "SomPong (COO) runs on Contabo only — use /spawn-coo\n"

# The supervisor's fakes (tmux that enforces exact targets, ps, sleep) are shared, not copied.
_spec = importlib.util.spec_from_file_location("_sompong_sim", Path(__file__).with_name("test_sompong_supervise.py"))
_sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sim)  # type: ignore[union-attr]
Sim, READY, LOGIN = _sim.Sim, _sim.READY, _sim.LOGIN

HAS_FLOCK = shutil.which("flock") is not None
needs_flock = pytest.mark.skipif(not HAS_FLOCK, reason="Contabo path uses flock(1)")

FAKE_SYSTEMCTL = """#!/bin/sh
echo "$*" >> "$FAKE_TMUX_DIR/systemctl_calls"
if [ -f "$FAKE_TMUX_DIR/systemctl_fails" ]; then echo "Unit mooniex-sompong.service not found." >&2; exit 5; fi
if [ -f "$FAKE_TMUX_DIR/start_creates" ]; then
  printf 'sompong\\n' > "$FAKE_TMUX_DIR/sessions"
  cp "$FAKE_TMUX_DIR/start_creates" "$FAKE_TMUX_DIR/pane"
  printf '100\\n' > "$FAKE_TMUX_DIR/pane_pid"
  printf '100 1 bash\\n101 100 claude\\n' > "$FAKE_TMUX_DIR/ps"
  printf '1790000000\\n' > "$FAKE_TMUX_DIR/created"
fi
exit 0
"""
FAKE_SSH = """#!/bin/sh
echo "$*" >> "$FAKE_TMUX_DIR/ssh_calls"
echo "ssh-said-hello"
exit "${FAKE_SSH_RC:-0}"
"""


def _exe(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture()
def sim(tmp_path: Path) -> Sim:
    s = Sim(tmp_path)
    _exe(s.bin / "systemctl", FAKE_SYSTEMCTL)
    _exe(s.bin / "ssh", FAKE_SSH)
    return s


def _log(sim: Sim, name: str) -> list[str]:
    f = sim.dir / name
    return f.read_text(encoding="utf-8").splitlines() if f.exists() else []


def spawn(sim: Sim, host: str, **extra: str) -> subprocess.CompletedProcess:
    knobs = {
        "ORG_HOST": host,
        "ORG_PYTHON": sys.executable,
        "SPAWN_COO_ROOT": str(ROOT),
        "SPAWN_COO_POLL_S": "1",
        "SPAWN_COO_WAIT_S": "3",
    }
    knobs.update(extra)
    env = sim.env(**knobs)
    return subprocess.run(["bash", str(SPAWN_COO)], env=env, capture_output=True, text=True, timeout=60)


def _alive(sim: Sim) -> None:
    sim.set_sessions("sompong")
    sim.put("pane_pid", "100\n")
    sim.put("pane", READY)
    sim.put("ps", "100 1 bash\n101 100 claude\n")
    sim.put("created", "1790000000\n")


# --- /spawn-coo on Contabo ------------------------------------------------------------------


@needs_flock
def test_contabo_alive_reports_and_starts_nothing(sim: Sim) -> None:
    _alive(sim)
    r = spawn(sim, "contabo")
    assert r.returncode == 0, r.stderr
    bkk = datetime.fromtimestamp(1790000000, timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")
    assert r.stdout.strip() == f"SomPong already online (tmux sompong, since {bkk})"
    assert _log(sim, "systemctl_calls") == []  # the singleton: never a second start
    assert sim.calls_of("new-session") == []


@needs_flock
def test_contabo_not_running_starts_the_unit_and_waits_for_the_prompt(sim: Sim) -> None:
    sim.put("start_creates", READY)
    r = spawn(sim, "contabo")
    assert r.returncode == 0, r.stderr
    assert "starting mooniex-sompong.service" in r.stdout
    assert r.stdout.strip().splitlines()[-1] == "SomPong online (tmux sompong)"
    assert _log(sim, "systemctl_calls") == ["start mooniex-sompong.service"]
    assert sim.calls_of("new-session") == []  # starting is systemd's job, not this script's


@needs_flock
def test_contabo_session_without_claude_counts_as_down(sim: Sim) -> None:
    sim.set_sessions("sompong")
    sim.put("pane_pid", "100\n")
    sim.put("ps", "100 1 bash\n")  # the launcher's bash, claude long gone
    sim.put("start_creates", READY)
    r = spawn(sim, "contabo")
    assert r.returncode == 0, r.stderr
    assert _log(sim, "systemctl_calls") == ["start mooniex-sompong.service"]


@needs_flock
def test_contabo_a_prefix_lookalike_session_is_not_sompong(sim: Sim) -> None:
    sim.set_sessions("sompong-old")  # tmux's loose `-t sompong` would have matched this
    sim.put("pane_pid", "100\n")
    sim.put("ps", "100 1 bash\n101 100 claude\n")
    sim.put("start_creates", READY)
    r = spawn(sim, "contabo")
    assert r.returncode == 0, r.stderr
    assert _log(sim, "systemctl_calls") == ["start mooniex-sompong.service"]


@needs_flock
def test_contabo_systemctl_failure_is_reported(sim: Sim) -> None:
    sim.put("systemctl_fails", "1")
    r = spawn(sim, "contabo")
    assert r.returncode == 1
    assert "systemctl start mooniex-sompong.service failed" in r.stderr
    assert "is the unit installed" in r.stderr


@needs_flock
def test_contabo_started_but_never_ready_times_out(sim: Sim) -> None:
    sim.put("start_creates", LOGIN)  # claude up, stuck on a login screen
    r = spawn(sim, "contabo", SPAWN_COO_WAIT_S="2")
    assert r.returncode == 1
    assert "did not show a ready prompt within 2s" in r.stderr
    assert "tmux capture-pane -p -t =sompong:" in r.stderr  # the pointer uses the exact target


@needs_flock
def test_contabo_two_spawns_at_once_are_serialised(sim: Sim) -> None:
    sim.state.mkdir(parents=True, exist_ok=True)
    with open(sim.state / "spawn.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r = spawn(sim, "contabo", SPAWN_COO_LOCK_WAIT_S="1")
    assert r.returncode == 1
    assert "another /spawn-coo has held the lock" in r.stderr
    assert _log(sim, "systemctl_calls") == []


# --- /spawn-coo off Contabo -------------------------------------------------------------------


@pytest.mark.parametrize("stray", ["sompong", "coo-1a2b3c4d"])
def test_mac_refuses_when_a_local_coo_session_exists(sim: Sim, stray: str) -> None:
    sim.set_sessions("cto-0123abcd", stray)
    r = spawn(sim, "mac")
    assert r.returncode == 1
    assert f"tmux session {stray}" in r.stderr
    assert "already exists on mac" in r.stderr
    assert "close the stray first" in r.stderr
    assert _log(sim, "ssh_calls") == []


def test_mac_without_a_stray_asks_contabo_over_ssh(sim: Sim) -> None:
    sim.set_sessions("cto-0123abcd", "sompong-old")  # neither is a coo session
    r = spawn(sim, "mac")
    assert r.returncode == 0, r.stderr
    assert "asking mooniex-vps" in r.stdout and "ssh-said-hello" in r.stdout
    assert _log(sim, "ssh_calls") == [f"-o BatchMode=yes -o ConnectTimeout=10 mooniex-vps {CONTABO_COMMAND}"]
    assert _log(sim, "systemctl_calls") == [] and sim.calls_of("new-session") == []  # nothing local


def test_mac_returns_the_remote_exit_code(sim: Sim) -> None:
    r = spawn(sim, "mac", FAKE_SSH_RC="7")
    assert r.returncode == 7


def tmp_basics(sim: Sim) -> str:
    """A bin dir of symlinks to the few tools the script needs, so `tmux` can be absent."""
    d = sim.dir.parent / "basics"
    d.mkdir(exist_ok=True)
    for tool in ("bash", "env", "grep", "sed", "awk", "date", "cat", "dirname", "mkdir", "head", "tr", "sleep", "cut"):
        src = shutil.which(tool, path="/usr/bin:/bin")
        if src and not (d / tool).exists():
            (d / tool).symlink_to(src)
    # the python the script is told to use is absolute (ORG_PYTHON); nothing else is needed
    return str(d)


def test_mac_with_no_tmux_at_all_still_routes(sim: Sim) -> None:
    (sim.bin / "tmux").unlink()
    # a minimal PATH that has the fakes and the basics, but no tmux anywhere
    basics = tmp_basics(sim)
    r = spawn(sim, "mac", PATH=f"{sim.bin}:{basics}")
    assert r.returncode == 0, r.stderr
    assert len(_log(sim, "ssh_calls")) == 1


def test_winbox_has_no_route_so_it_prints_the_exact_command(sim: Sim) -> None:
    r = spawn(sim, "winbox")
    assert r.returncode == 2
    assert "No ssh route from winbox to Contabo" in r.stdout
    assert CONTABO_COMMAND in r.stdout
    assert _log(sim, "ssh_calls") == []


def test_unresolved_host_is_refused_not_guessed(sim: Sim) -> None:
    r = spawn(sim, "not-a-host")
    assert r.returncode == 1
    assert "cannot tell which machine this is" in r.stderr
    assert _log(sim, "ssh_calls") == [] and _log(sim, "systemctl_calls") == []


# --- coo_host.py ---------------------------------------------------------------------------------


def _coo_host(arg: str, host: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, ORG_HOST=host)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lib" / "coo_host.py"), arg], env=env, capture_output=True, text=True
    )


@pytest.mark.parametrize("host", ["mac", "winbox", "contabo"])
def test_coo_host_names_the_machine(host: str) -> None:
    r = _coo_host("host", host)
    assert (r.returncode, r.stdout.strip()) == (0, host)


def test_coo_host_route_from_the_mac_is_the_registry_alias() -> None:
    r = _coo_host("route", "mac")
    assert r.returncode == 0
    alias, root = r.stdout.split()
    assert alias == "mooniex-vps" and root == "/opt/MoonieXHQ/Agents/Core"


@pytest.mark.parametrize("host", ["contabo", "winbox"])
def test_coo_host_route_is_absent_off_the_mac_and_on_contabo(host: str) -> None:
    r = _coo_host("route", host)
    assert (r.returncode, r.stdout) == (4, "")


def test_coo_host_unresolved_and_usage_exit_codes() -> None:
    assert _coo_host("host", "nonsense").returncode == 3
    assert _coo_host("frobnicate", "mac").returncode == 2


# --- the launcher ------------------------------------------------------------------------------------


def _hermetic_venv(dest: Path, prefix: str) -> None:
    """The root's `.venv`. cxo-claude.sh runs `source .venv/bin/activate`.

    A venv's own prefix has that file, so link to it. A bare interpreter prefix does not
    (CI: the setup-python toolcache), so build a venv over it that still sees its site-packages.
    """
    if (Path(prefix) / "bin" / "activate").exists():
        dest.symlink_to(prefix)
    else:
        # symlinks, as `python -m venv` does on POSIX: a copied interpreter loses its libpython on a shared build
        venv.create(dest, system_site_packages=True, symlinks=True, with_pip=False)


@pytest.fixture()
def lroot(tmp_path: Path) -> Path:
    """A hermetic org root: the real code by symlink, a private state/, the test's own venv."""
    root = tmp_path / "root"
    root.mkdir()
    for name in (".claude", "config", "lib", "policies", "roles", "runners", "scripts", "tools"):
        (root / name).symlink_to(ROOT / name)
    _hermetic_venv(root / ".venv", sys.prefix)
    (root / "state").mkdir()
    return root


def test_hermetic_venv_links_a_prefix_that_has_activate(tmp_path: Path) -> None:
    prefix = tmp_path / "prefix"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "bin" / "activate").write_text("", encoding="utf-8")
    _hermetic_venv(tmp_path / ".venv", str(prefix))
    assert (tmp_path / ".venv").is_symlink() and (tmp_path / ".venv").resolve() == prefix.resolve()


def test_hermetic_venv_builds_activate_over_a_prefix_that_has_none(tmp_path: Path) -> None:
    bare = tmp_path / "bare"  # the CI toolcache shape: an interpreter prefix with no bin/activate
    (bare / "bin").mkdir(parents=True)
    dest = tmp_path / ".venv"
    _hermetic_venv(dest, str(bare))
    assert (dest / "bin" / "activate").is_file() and not dest.is_symlink()
    r = subprocess.run(
        ["bash", "-c", f"cd {dest.parent} && source .venv/bin/activate && python3 -c 'import sys; print(sys.prefix)'"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()).resolve() == dest.resolve()


def _launch(lroot: Path, tmp: Path, *argv: str, **env_extra: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": f"{Path(sys.prefix) / 'bin'}:{tmp / 'fakebin'}:{os.environ['PATH']}",
        "HOME": str(tmp / "home"),
        "ORG_ROOT": str(tmp / "orgroot"),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
        "ORG_HOST": "contabo",
        "WIKI_ROOT_ORG": "/opt/MoonieXHQ/Agents/Rules",
        "WIKI_ROOT_MOONIEX": "/opt/MoonieXHQ/Agents/Wikis",
    }
    env.update(env_extra)
    for d in ("fakebin", "home", "orgroot"):
        (tmp / d).mkdir(exist_ok=True)
    # never the real runuser: it would really switch user. This one logs and runs the command as is.
    _exe(
        tmp / "fakebin" / "runuser",
        f"""#!/bin/sh
echo "RUNUSER $*" >> '{tmp / "runuser.log"}'
[ "$1" = "-u" ] || exit 9
shift 2; [ "$1" = "--" ] && shift
exec "$@"
""",
    )
    return subprocess.run(
        ["bash", str(lroot / "scripts" / "cxo-claude.sh"), *argv], env=env, capture_output=True, text=True, timeout=120
    )


@pytest.mark.parametrize("host", ["mac", "winbox", "not-a-host"])
@pytest.mark.parametrize("extra", [["--dry-run"], [], ["--session", "abc12345"]])
def test_launcher_refuses_coo_off_contabo(lroot: Path, tmp_path: Path, host: str, extra: list[str]) -> None:
    r = _launch(lroot, tmp_path, "--role", "coo", *extra, ORG_HOST=host)
    assert r.returncode == 1
    assert r.stderr.endswith(REFUSAL)  # exactly this line, so a caller can match it
    if host != "not-a-host":
        assert r.stderr == REFUSAL  # nothing else; an unresolved host adds one line saying why
    else:
        assert "cannot resolve this machine" in r.stderr
    assert r.stdout == ""
    # nothing was registered: the refusal comes before any lock, DB row or temp file
    assert list((lroot / "state").iterdir()) == []
    assert not list(tmp_path.glob("cxo-mcp-*"))


def test_launcher_still_starts_the_other_roles_off_contabo(lroot: Path, tmp_path: Path) -> None:
    r = _launch(lroot, tmp_path, "--role", "cto", "--dry-run", ORG_HOST="mac")
    assert r.returncode == 0, r.stderr
    assert "dry-run: role=cto" in r.stdout


@pytest.fixture()
def sompong(tmp_path: Path, lroot: Path) -> dict[str, Path]:
    """A SomPong checkout stand-in and a fake claude that records how it was started."""
    repo = tmp_path / "SomPong"
    repo.mkdir()
    (repo / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"sompong": {"command": "python3", "args": ["-m", "channel"]}}}), encoding="utf-8"
    )
    out = tmp_path / "claude.out"
    claude = tmp_path / "claude"
    # env -i empties the environment, so the output path is baked in, not passed.
    _exe(
        claude,
        f"""#!/bin/sh
{{ echo "PWD=$(pwd)"; for a in "$@"; do echo "ARG=$a"; done; env | sed 's/^/ENV=/'
  echo "BOXMODE=$(stat -c %a '{lroot}/state/inbox/coo-'"$CXO_SESSION_ID")"; }} > '{out}'
exit 0
""",
    )
    return {"repo": repo, "claude": claude, "out": out}


def _coo_env(sompong: dict[str, Path], **extra: str) -> dict[str, str]:
    env = {"SOMPONG_DIR": str(sompong["repo"]), "SOMPONG_USER": "nobody", "SOMPONG_CLAUDE": str(sompong["claude"])}
    env.update(extra)
    return env


needs_nobody = pytest.mark.skipif(shutil.which("getent") is None or subprocess.run(["id", "nobody"], capture_output=True).returncode != 0, reason="needs a `nobody` unix user")


# what the claude process may see: the launcher's allowlist, plus what the fake's own /bin/sh adds
COO_ENV_ALLOWED = {
    "HOME", "USER", "LOGNAME", "PATH", "TERM", "LANG", "ORG_HOST", "SOMPONG_COO_SESSION", "WIKI_ROOT_ORG",
    "WIKI_ROOT_MOONIEX", "DISABLE_AUTOUPDATER", "CLAUDE_CODE_DISABLE_TERMINAL_TITLE",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "CXO_ROLE", "CXO_SESSION", "CXO_SESSION_ID", "LUNGNOTE_MCP_NODE",
    "PWD", "SHLVL", "_", "OLDPWD",
}


@needs_nobody
def test_launcher_dry_run_on_contabo_describes_the_session(lroot: Path, tmp_path: Path, sompong) -> None:
    r = _launch(lroot, tmp_path, "--role", "coo", "--dry-run", **_coo_env(sompong))
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert f"dry-run: coo host=contabo cwd={sompong['repo']} user=nobody claude={sompong['claude']}" in out
    extra = next(line for line in out.splitlines() if line.startswith("dry-run: coo extra-args="))
    assert f"--mcp-config {sompong['repo']}/.mcp.json" in extra
    assert "--dangerously-load-development-channels server:sompong" in extra
    assert f"--add-dir {lroot}" in extra and "--settings " in extra
    allowed = next(line for line in out.splitlines() if line.startswith("dry-run: allowed-tools="))
    for tool in ("reply", "skip", "send", "ask_ceo", "history", "media"):
        assert f"mcp__sompong__{tool}" in allowed
    # root work goes through a Run Inbox card: both org tools must be callable in this session
    assert {"mcp__org__ask_run", "mcp__org__ask_run_wait"} <= set(allowed.split("=", 1)[1].split())
    names = next(line for line in out.splitlines() if line.startswith("dry-run: coo env=")).split("=", 1)[1].split()
    assert "SOMPONG_COO_SESSION" in names and "ORG_HOST" in names
    assert not [n for n in names if re.search(r"KEY|TOKEN|SECRET|PASSWORD|INFISICAL", n)]
    assert list((lroot / "state").iterdir()) == []  # a dry run registers nothing
    assert not list(tmp_path.glob("cxo-mcp-*"))  # and leaves no temp config behind


@needs_nobody
@pytest.mark.parametrize(
    "case,extra,reason",
    [
        ("no repo", {"SOMPONG_DIR": "/nonexistent/SomPong"}, "SomPong repo not found"),
        ("no sompong server", {"__mcp": "{}"}, "does not declare MCP server 'sompong'"),
        ("no unix user", {"SOMPONG_USER": "no-such-user-xyz"}, "unix user 'no-such-user-xyz' does not exist"),
        ("root", {"SOMPONG_USER": "root"}, "must not run as root"),
        ("no claude", {"SOMPONG_CLAUDE": "/nonexistent/claude"}, "claude is not installed for nobody"),
    ],
)
def test_launcher_names_what_is_missing(lroot: Path, tmp_path: Path, sompong, case, extra, reason) -> None:
    extra = dict(extra)
    mcp = extra.pop("__mcp", None)
    if mcp is not None:
        (sompong["repo"] / ".mcp.json").write_text(mcp, encoding="utf-8")
    r = _launch(lroot, tmp_path, "--role", "coo", "--dry-run", **_coo_env(sompong, **extra))
    assert r.returncode == 1, (case, r.stdout)
    assert "SomPong (COO) cannot start:" in r.stderr and reason in r.stderr
    assert not list(tmp_path.glob("cxo-mcp-*"))


@needs_nobody
def test_launcher_runs_claude_unprivileged_with_the_channel_flag_and_a_clean_env(
    lroot: Path, tmp_path: Path, sompong
) -> None:
    runuser_log = tmp_path / "runuser.log"
    # an empty hub DB for the launcher's background `register_cxo` (the schema is created elsewhere on a real hub)
    (tmp_path / "orgroot").mkdir()
    subprocess.run(
        [sys.executable, "-c", "from lib import db; db.init()"],
        cwd=ROOT, env=dict(os.environ, ORG_ROOT=str(tmp_path / "orgroot")), check=True, capture_output=True,
    )
    r = _launch(lroot, tmp_path, "--role", "coo", **_coo_env(sompong))
    assert r.returncode == 0, r.stderr
    got = sompong["out"].read_text(encoding="utf-8").splitlines()
    args = [line[4:] for line in got if line.startswith("ARG=")]
    env = dict(line[4:].split("=", 1) for line in got if line.startswith("ENV=") and "=" in line[4:])
    assert f"PWD={sompong['repo']}" in got  # cwd is the SomPong repo, not Agents-Core

    def after(flag: str) -> str:
        return args[args.index(flag) + 1]

    assert after("--dangerously-load-development-channels") == "server:sompong"
    assert after("--permission-mode") == "auto"
    assert after("--remote-control") == "SomPong"  # its own name in the Claude app
    assert after("--add-dir") == str(lroot)
    assert args.count("--mcp-config") == 2 and f"{sompong['repo']}/.mcp.json" in args
    assert "--strict-mcp-config" in args  # still strict: org + lungnote + sompong only
    assert "--settings" in args and "--session-id" in args and "--allowed-tools" in args
    assert "mcp__sompong__reply" in " ".join(args)

    # empty environment + the allowlist, and nothing that looks like a secret
    assert env["SOMPONG_COO_SESSION"] == "1" and env["ORG_HOST"] == "contabo"
    assert env["CXO_ROLE"] == "coo" and env["CXO_SESSION"] == "1" and re.fullmatch(r"[0-9a-f]{8}", env["CXO_SESSION_ID"])
    assert set(env) <= COO_ENV_ALLOWED, set(env) - COO_ENV_ALLOWED
    assert not [k for k in env if re.search(r"KEY|TOKEN|SECRET|PASSWORD|INFISICAL", k)]
    assert env["HOME"] != str(tmp_path / "home")  # the unprivileged user's home, not the caller's

    # bookkeeping happened as the launching user, claude through runuser as `nobody` (when uid differs)
    if os.getuid() != int(subprocess.check_output(["id", "-u", "nobody"], text=True)):
        assert runuser_log.read_text().startswith("RUNUSER -u nobody -- env -i ")
    # registered as role `coo` in c_level_sessions (a background job of the launcher: poll for it)
    import sqlite3

    db = tmp_path / "orgroot" / "state" / "tasks.db"
    row, deadline = None, time.time() + 30
    while row is None and time.time() < deadline:
        if db.exists():
            try:
                with sqlite3.connect(db, timeout=5) as conn:
                    row = conn.execute(
                        "SELECT role, host FROM c_level_sessions WHERE session_id = ?", (env["CXO_SESSION_ID"],)
                    ).fetchone()
            except sqlite3.Error:
                row = None
        if row is None:
            time.sleep(0.3)
    assert row == ("coo", "contabo"), row
    # the mailbox box existed while claude ran, group-writable so SomPong's user can delete a letter it read
    # (the launcher's exit trap removes an empty box afterwards)
    assert "BOXMODE=2775" in got


@needs_nobody
@pytest.mark.skipif(not Path("/proc/self/cmdline").exists(), reason="needs /proc")
def test_launcher_refuses_a_second_live_coo_launcher(lroot: Path, tmp_path: Path, sompong) -> None:
    # a live process whose command line says cxo-claude, holding a coo lock under another id
    other = subprocess.Popen(["bash", "-c", "exec -a cxo-claude-pretend sleep 60"])
    try:
        locks = lroot / "state" / "locks"
        locks.mkdir(parents=True)
        (locks / "coo-deadbeef.lock").write_text(f"{other.pid}\n", encoding="utf-8")
        time.sleep(0.2)
        r = _launch(lroot, tmp_path, "--role", "coo", **_coo_env(sompong))
        assert r.returncode == 1
        assert "SomPong (COO) is already running" in r.stderr and "one session only" in r.stderr
        assert not sompong["out"].exists()  # claude was never started
    finally:
        other.send_signal(signal.SIGTERM)
        other.wait(timeout=10)


@needs_nobody
def test_launcher_ignores_a_stale_coo_lock(lroot: Path, tmp_path: Path, sompong) -> None:
    locks = lroot / "state" / "locks"
    locks.mkdir(parents=True)
    (locks / "coo-deadbeef.lock").write_text("999999\n", encoding="utf-8")  # no such process
    r = _launch(lroot, tmp_path, "--role", "coo", **_coo_env(sompong))
    assert r.returncode == 0, r.stderr
    assert sompong["out"].exists()


@needs_nobody
def _session_home(tmp_path: Path) -> Path:
    """A fake `getent` so the session user's home is a directory the test owns (nobody's is /nonexistent)."""
    home = tmp_path / "sphome"
    home.mkdir()
    (tmp_path / "fakebin").mkdir(exist_ok=True)
    _exe(tmp_path / "fakebin" / "getent", f'#!/bin/sh\necho "$2:x:65534:65534::{home}:/usr/sbin/nologin"\n')
    return home


@needs_nobody
def test_launcher_keeps_the_session_users_home_and_warns_once_without_the_run_inbox_token(
    lroot: Path, tmp_path: Path, sompong
) -> None:
    home = _session_home(tmp_path)
    r = _launch(lroot, tmp_path, "--role", "coo", **_coo_env(sompong))
    assert r.returncode == 0, r.stderr  # a missing token never stops the session: only ask_run fails
    assert sompong["out"].exists()  # claude was started
    warning = [line for line in r.stderr.splitlines() if "run-inbox.token" in line]
    assert len(warning) == 1 and warning[0].startswith("SomPong (COO) warning: ")
    assert str(home / ".config" / "mooniex" / "run-inbox.token") in warning[0] and "ask_run" in warning[0]
    got = sompong["out"].read_text(encoding="utf-8").splitlines()
    assert f"ENV=HOME={home}" in got  # ask_run reads ~/.config/mooniex/run-inbox.token from THIS home


@needs_nobody
def test_launcher_is_quiet_when_the_run_inbox_token_is_there(lroot: Path, tmp_path: Path, sompong) -> None:
    home = _session_home(tmp_path)
    token = home / ".config" / "mooniex" / "run-inbox.token"
    token.parent.mkdir(parents=True)
    token.write_text("dummy-not-a-token\n", encoding="utf-8")
    token.chmod(0o600)
    r = _launch(lroot, tmp_path, "--role", "coo", **_coo_env(sompong))
    assert r.returncode == 0, r.stderr
    assert "run-inbox" not in r.stderr and "warning" not in r.stderr
    assert "dummy-not-a-token" not in r.stdout + r.stderr  # the file's content is never read out


@pytest.mark.skipif(os.getuid() != 0, reason="the direct (no runuser) path is taken only when the launcher itself is root")
def test_root_is_an_explicit_opt_in_and_still_gets_the_clean_env(lroot: Path, tmp_path: Path, sompong) -> None:
    # SOMPONG_USER=root + SOMPONG_ALLOW_ROOT=1 (a deploy choice in the unit, never a code default): the
    # session starts as root with no runuser hop, and the environment is still `env -i` + the allowlist,
    # so a key in the launching shell (the supervisor's, an Infisical identity) never reaches claude.
    r = _launch(
        lroot, tmp_path, "--role", "coo",
        **_coo_env(sompong, SOMPONG_USER="root", SOMPONG_ALLOW_ROOT="1", SOMPONG_INBOX_KEY="canary", INFISICAL_TOKEN="canary"),
    )
    assert r.returncode == 0, r.stderr
    got = sompong["out"].read_text(encoding="utf-8").splitlines()
    env = dict(line[4:].split("=", 1) for line in got if line.startswith("ENV=") and "=" in line[4:])
    assert not (tmp_path / "runuser.log").exists()  # claude was exec'd directly, not through runuser
    assert env["USER"] == "root" and env["LOGNAME"] == "root"
    assert env["SOMPONG_COO_SESSION"] == "1" and env["ORG_HOST"] == "contabo"
    assert set(env) <= COO_ENV_ALLOWED, set(env) - COO_ENV_ALLOWED
    assert not [k for k in env if re.search(r"KEY|TOKEN|SECRET|PASSWORD|INFISICAL", k)]
    assert "canary" not in "\n".join(got)


# --- the org MCP server for a session user that is not root ------------------------------------------
# The COO session runs as the unprivileged `sompong` user, and state/tasks.db is root-owned. The org MCP server
# (runners.cto_mcp_server, started by every C-level launcher) calls db.init() before it serves a single tool.

NOBODY_UID = 65534


def _serve_tools_as_nobody(state_mode: int, db_mode: int, group: int) -> tuple[list[str] | None, str]:
    """Start the org MCP server as uid `nobody` against a private org root whose tasks.db has the given
    modes; send initialize + tools/list over stdio. Returns (tool names or None, stderr tail)."""
    import select
    import tempfile

    fx = Path(tempfile.mkdtemp(dir="/tmp", prefix="coo-orgdb-"))
    try:
        fx.chmod(0o755)
        (fx / "state").mkdir()
        py = shutil.which("python3", path=str(Path(sys.prefix) / "bin")) or sys.executable
        subprocess.run(
            [py, "-c", "from lib import db; db.init()"], cwd=ROOT, check=True, capture_output=True,
            env=dict(os.environ, ORG_ROOT=str(fx)),
        )
        os.chown(fx / "state", 0, group)
        os.chown(fx / "state" / "tasks.db", 0, group)
        (fx / "state").chmod(state_mode)
        (fx / "state" / "tasks.db").chmod(db_mode)
        env = {
            "PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "ORG_ROOT": str(fx), "ORG_HOST": "contabo",
            "PYTHONUNBUFFERED": "1", "CXO_ROLE": "coo", "CXO_SESSION": "1",
            "WIKI_ROOT_ORG": "/opt/MoonieXHQ/Agents/Rules", "WIKI_ROOT_MOONIEX": "/opt/MoonieXHQ/Agents/Wikis",
        }
        p = subprocess.Popen(
            [py, "-m", "runners.cto_mcp_server"], cwd=ROOT, env=env, user=NOBODY_UID, group=group, extra_groups=[],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

        def reply(want_id: int) -> dict | None:
            deadline = time.time() + 30
            while time.time() < deadline:
                if not select.select([p.stdout], [], [], 1.0)[0]:
                    if p.poll() is not None:
                        return None
                    continue
                line = p.stdout.readline()
                if not line:
                    return None
                try:  # db.init() prints a "[db] initialized" line to stdout first
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("id") == want_id:
                    return msg
            return None

        def send(msg: dict) -> None:
            p.stdin.write(json.dumps(msg) + "\n")
            p.stdin.flush()

        names = None
        try:
            send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}}})
            if reply(1) is not None:
                send({"jsonrpc": "2.0", "method": "notifications/initialized"})
                send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                listed = reply(2)
                names = [t["name"] for t in listed["result"]["tools"]] if listed else None
        except (BrokenPipeError, OSError):
            names = None
        finally:
            if p.poll() is None:
                p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
            err = p.stderr.read()[-800:]
        return names, err
    finally:
        shutil.rmtree(fx, ignore_errors=True)


needs_root_and_nobody = pytest.mark.skipif(
    os.getuid() != 0 or shutil.which("getent") is None
    or subprocess.run(["id", "-u", "nobody"], capture_output=True, text=True).stdout.strip() != str(NOBODY_UID),
    reason="needs root (to switch to uid nobody and chown a fixture)",
)


@needs_root_and_nobody
def test_org_mcp_server_starts_and_lists_its_tools_for_a_uid_that_can_write_the_shared_db() -> None:
    # The deploy prerequisite for the unprivileged COO: tasks.db and state/ shared with the session user's group.
    from lib.org_tools_registry import REGISTRY

    names, err = _serve_tools_as_nobody(state_mode=0o2775, db_mode=0o664, group=NOBODY_UID)
    assert names is not None, err
    assert {s.name for s in REGISTRY} <= set(names)
    assert {"ask_run", "ask_run_wait"} <= set(names)


@needs_root_and_nobody
@pytest.mark.xfail(
    strict=True,
    reason="a uid that can read but not write state/tasks.db cannot start the org MCP server: runners/cto_mcp_server.py "
    "calls db.init() first, and lib/db.py _connect() runs PRAGMA journal_mode=WAL (a WAL database also needs a writable "
    "-shm beside it) -> sqlite3.OperationalError: attempt to write a readonly database. The session has no org tools "
    "(ask_run included) until tasks.db is shared with the session user or the tasks hub is live.",
)
def test_org_mcp_server_starts_and_lists_its_tools_for_a_uid_that_can_only_read_the_db() -> None:
    names, err = _serve_tools_as_nobody(state_mode=0o755, db_mode=0o644, group=0)
    assert names, err  # today: names is None and err ends "attempt to write a readonly database"


@needs_nobody  # the COO launcher reads the user's home with getent (cxo-claude.sh), which macOS lacks
def test_launcher_moves_an_unread_letter_to_the_new_box(lroot: Path, tmp_path: Path, sompong) -> None:
    old = lroot / "state" / "inbox" / "coo-0ldb0x00"
    old.mkdir(parents=True)
    (old / "letter-1.json").write_text('{"from_role": "cto"}', encoding="utf-8")
    r = _launch(lroot, tmp_path, "--role", "coo", **_coo_env(sompong))
    assert r.returncode == 0, r.stderr
    boxes = [p for p in (lroot / "state" / "inbox").iterdir() if p.name.startswith("coo-")]
    kept = [b for b in boxes if (b / "letter-1.json").exists()]
    assert len(kept) == 1 and kept[0].name != "coo-0ldb0x00"
    assert not old.exists()  # the emptied old box is removed


# --- spawn-cxo.sh (the Mac iTerm path) -------------------------------------------------------------------


def test_spawn_cxo_refuses_coo_before_any_applescript(tmp_path: Path) -> None:
    sim = Sim(tmp_path)
    _exe(sim.bin / "osascript", "#!/bin/sh\necho osascript >> \"$FAKE_TMUX_DIR/osascript_calls\"\nexit 0\n")
    r = subprocess.run(
        ["bash", str(ROOT / "scripts" / "spawn-cxo.sh"), "--role", "coo"],
        env=sim.env(), capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 1
    assert r.stderr == REFUSAL
    assert _log(sim, "osascript_calls") == []


# --- tmux name, wake, refusals --------------------------------------------------------------------------------------


def test_tmux_name_override_is_sompong_for_coo_only() -> None:
    from tools import session_name

    assert session_name.tmux_name("coo", "1a2b3c4d") == "sompong"
    assert session_name.tmux_name("cto", "1a2b3c4d") == "cto-1a2b3c4d"
    assert session_name.tmux_name_for_stem("coo-1a2b3c4d") == "sompong"
    assert session_name.tmux_name_for_stem("cmo-1a2b3c4d") == "cmo-1a2b3c4d"
    assert session_name.tmux_name_for_stem("not-a-clevel-stem") == "not-a-clevel-stem"


def test_a_letter_to_coo_wakes_tmux_sompong_not_coo_dash_id(monkeypatch) -> None:
    from tools import send_to_cxo

    woken: list[str | None] = []
    monkeypatch.setattr(send_to_cxo.agent_transport, "attempt_wake", lambda session, *a, **k: woken.append(session))
    send_to_cxo.attempt_wake("coo", "1a2b3c4d", "cto")
    send_to_cxo.attempt_wake("cmo", "1a2b3c4d", "cto")
    assert woken == ["sompong", "cmo-1a2b3c4d"]


def test_cross_host_letter_liveness_asks_tmux_for_sompong(monkeypatch) -> None:
    from tools import node_dispatch

    asked: list[str] = []
    monkeypatch.setattr(node_dispatch, "_is_windows", lambda: False)
    monkeypatch.setattr(node_dispatch, "_session_live", lambda name: asked.append(name) or True)
    assert node_dispatch._clevel_session_live("coo", "1a2b3c4d") is True
    assert node_dispatch._clevel_session_live("cmo", "1a2b3c4d") is True
    assert asked == ["sompong", "cmo-1a2b3c4d"]  # a Mac -> Contabo letter to coo is not refused as "no live session"


def test_session_gc_matches_a_live_coo_lock_with_tmux_sompong(tmp_path: Path) -> None:
    from tools import session_gc

    (tmp_path / "coo-1a2b3c4d.lock").write_text(f"{os.getpid()}\n", encoding="utf-8")
    (tmp_path / "cmo-5e6f7a8b.lock").write_text(f"{os.getpid()}\n", encoding="utf-8")
    rec = session_gc.reconcile(tmp_path, {"sompong", "cmo-5e6f7a8b", "scratch"})
    assert rec.matched == {"coo-1a2b3c4d", "cmo-5e6f7a8b"}
    assert not rec.lock_only and not rec.orphans and not rec.tmux_only


def test_session_gc_reports_coo_drift_both_ways(tmp_path: Path) -> None:
    from tools import session_gc

    lock = tmp_path / "coo-1a2b3c4d.lock"
    lock.write_text(f"{os.getpid()}\n", encoding="utf-8")
    rec = session_gc.reconcile(tmp_path, set())  # SomPong running with no tmux: the orphan
    assert rec.orphans == {"coo-1a2b3c4d": os.getpid()} and not rec.matched
    rec = session_gc.reconcile(tmp_path, {"coo-1a2b3c4d"})  # `coo-<id>` is not SomPong's tmux name
    assert not rec.matched and rec.tmux_only == {"coo-1a2b3c4d"} and "coo-1a2b3c4d" in rec.orphans
    lock.unlink()
    rec = session_gc.reconcile(tmp_path, {"sompong"})  # tmux `sompong` with no lock: reported, never touched
    assert rec.tmux_only == {"sompong"} and not rec.matched and not rec.lock_only


def test_coo_is_never_spawned_per_request(monkeypatch) -> None:
    from lib import roles
    from tools import send_to_cxo

    assert roles.SINGLETON_ROLES == ("coo",)
    assert roles.singleton_refusal("cto") is None
    msg = roles.singleton_refusal("coo")
    assert "/spawn-coo" in msg and "ONE" in msg
    with pytest.raises(ValueError, match="/spawn-coo"):
        send_to_cxo.spawn("coo", "hello")


def test_send_to_coo_with_no_live_session_says_how_to_start_it(monkeypatch) -> None:
    from tools import send_to_cxo

    monkeypatch.setattr(send_to_cxo, "_active_session_id", lambda role: None)
    monkeypatch.setattr(send_to_cxo, "_remote_target", lambda role: None)
    with pytest.raises(ValueError) as e:
        send_to_cxo.send("coo", "hello")
    assert "/spawn-coo" in str(e.value) and "spawn-cxo.sh" not in str(e.value)
    with pytest.raises(ValueError) as e:
        send_to_cxo.send("cmo", "hello")
    assert "spawn-cxo.sh --role cmo" in str(e.value)


def test_the_relay_refuses_spawn_c_level_coo_on_every_host(monkeypatch) -> None:
    from runners import relay_mcp_server as rms

    audited: list[tuple] = []
    monkeypatch.setattr(rms, "_audit", lambda *a, **k: audited.append(a))

    def boom(*a, **k):
        raise AssertionError("nothing may be started or dialled")

    monkeypatch.setattr(subprocess, "run", boom)
    for host in ("mac", "contabo", "winbox"):
        res = json.loads(rms.spawn_c_level("coo", host))
        assert res["status"] == "rejected" and "/spawn-coo" in res["reason"]
    assert [a[:3] for a in audited] == [("spawn_c_level", "coo", "rejected")] * 3


def test_share_letter_makes_the_letter_readable_by_the_session_user(tmp_path: Path) -> None:
    from tools import send_to_cxo

    box = tmp_path / "coo-1a2b3c4d"
    box.mkdir(mode=0o755)
    letter = box / "1.json"
    fd = os.open(letter, os.O_CREAT | os.O_WRONLY, 0o600)  # what mailbox.send's mkstemp leaves
    os.close(fd)
    send_to_cxo._share_letter(letter)
    assert stat.S_IMODE(letter.stat().st_mode) == 0o664
    assert stat.S_IMODE(box.stat().st_mode) == 0o2775
    send_to_cxo._share_letter(None)  # no letter (a refused send): nothing happens
    send_to_cxo._share_letter(tmp_path / "gone.json")  # a vanished letter never raises


def test_send_shares_the_letter_for_coo_but_not_for_other_roles(tmp_path: Path, monkeypatch) -> None:
    from tools import send_to_cxo

    shared: list[Path | None] = []
    monkeypatch.setattr(send_to_cxo, "_share_letter", lambda letter: shared.append(letter))
    monkeypatch.setattr(send_to_cxo, "_active_session_id", lambda role: "1a2b3c4d")
    monkeypatch.setattr(send_to_cxo, "authorize", lambda *a, **k: None)
    monkeypatch.setattr(send_to_cxo, "_log_hop", lambda *a, **k: None)
    monkeypatch.setattr(send_to_cxo, "_attempt_wake", lambda *a, **k: None)
    monkeypatch.setattr(send_to_cxo.mailbox, "send", lambda role, sid, *a, **k: tmp_path / f"{role}.json")
    send_to_cxo.send("coo", "hi", sender="cto")
    send_to_cxo.send("cmo", "hi", sender="cto")
    assert shared == [tmp_path / "coo.json"]


# --- the hooks file for a session whose cwd is another repo -----------------------------------------------------------------


def test_org_hooks_follow_the_session_into_the_sompong_cwd() -> None:
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    import cxo_hooks_settings as chs

    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert chs.PLACEHOLDER in json.dumps(settings["hooks"])  # the premise: hooks are cwd-relative today
    out = chs.hooks_settings(settings, "/opt/MoonieXHQ/Agents/Core")
    text = json.dumps(out)
    assert set(out) == {"hooks"}  # only hooks: permissions/env stay the launcher's call
    assert "CLAUDE_PROJECT_DIR" not in text and chs.PLACEHOLDER not in text
    commands = [h["command"] for groups in out["hooks"].values() for g in groups for h in g["hooks"]]
    assert commands and all('"/opt/MoonieXHQ/Agents/Core"/scripts/' in c for c in commands if "/scripts/" in c)
    # a root with a character JSON must escape still yields valid JSON
    json.loads(json.dumps(chs.hooks_settings(settings, '/odd "root"\\dir')))


def test_hooks_settings_cli_refuses_an_empty_hook_set(tmp_path: Path) -> None:
    root = tmp_path / "r"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "settings.json").write_text('{"hooks": {}}', encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lib" / "cxo_hooks_settings.py"), "--root", str(root), "--out", str(tmp_path / "o.json")],
        capture_output=True, text=True,
    )
    assert r.returncode == 1 and "no hooks" in r.stderr and not (tmp_path / "o.json").exists()


# --- the role file and the command ----------------------------------------------------------------------------------------------


def test_the_coo_role_file_carries_the_contract_points() -> None:
    text = (ROOT / "roles" / "coo.md").read_text(encoding="utf-8")
    for needle in (
        '<channel source="sompong"',  # how messages arrive
        "mcp__sompong__",  # replied to with tools
        "reply(event_id, text)", "skip(event_id", "ask_ceo",
        "send_to_cxo",  # routing to the owning C-level
        "ask_run.py create", "--risk red", "timeout 900", "ask_run.py wait", "ask_run.py cancel",  # root work = a Run Inbox card via the CLI
        "Face ID", "sudo",
        "money", "secrets", "permanent deletion",  # always the CEO's call
        "family",
        "docs/design/sompong-coo-session.md",
        "SKILL LEARNING LOOP",
    ):
        assert needle in text, needle


def test_the_spawn_coo_command_may_only_run_the_spawn_script() -> None:
    text = (ROOT / "claude-home" / "commands" / "spawn-coo.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    allowed = re.search(r"^allowed-tools: (.+)$", front, re.M).group(1)
    assert allowed == "Bash(bash /Users/gob/MoonieXHQ/Agents/Core/scripts/spawn-coo.sh:*)"
    assert "!`bash /Users/gob/MoonieXHQ/Agents/Core/scripts/spawn-coo.sh`" in text
