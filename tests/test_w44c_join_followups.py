"""Org Mesh W4.4c: the follow-ups W4.3 (join scripts) and W4.4b (self_host) left behind.

  1. join.sh / join.ps1 step 9 (the node probe) reads the node.yaml step 8 wrote, even when
     `sudo` gives the probe root's HOME.
  2. tools/infisical_setup.NODE_HOST_RE is the same 3-31 rule as lib.config.HOST_NAME_RE, and
     infisical_setup.py stays stdlib-only (a Run Inbox card copies that one file).
  3. lib.db.seed_hosts_from_config() never seeds a host hosts.yaml does not declare, so the
     entry lib.config.hosts() synthesizes from a joined node's node.yaml cannot overwrite the
     hub's row for that node.

Nothing here installs, contacts a network, runs `sudo` for real or touches the real HOME,
~/.config/mooniex or config/hosts.yaml. The seed tests run on SQLite, and on the Postgres named by
ORG_TEST_DB_URL when it is set (same convention as tests/test_w41_hq_join.py).

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w44c_join_followups.py
"""
from __future__ import annotations

import ast
import json
import os
import platform
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, db, db_pg  # noqa: E402
from tools import hq_join, infisical_setup  # noqa: E402

JOIN_SH = ROOT / "deploy" / "join" / "join.sh"
JOIN_PS1 = ROOT / "deploy" / "join" / "join.ps1"

TOKEN = "hqj_" + "Tok3n_-" * 6 + "T"                # hqj_ + 43 characters
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
HOST = "node-a"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions", "hosts", "letters", "join_tokens")

not_root = pytest.mark.skipif(os.geteuid() == 0, reason="as root join.sh runs step 9 without sudo")


# ---------------------------------------------------------------- 1: join.sh step 9

def _fake_bin(tmp_path: Path) -> tuple[Path, Path]:
    """A bin dir with recorders for sudo/apt-get/brew/npm. The `sudo` does what a real one does
    under a default sudoers: it resets HOME to root's before it runs the command. Returns
    (bin dir, call log)."""
    bindir, log = tmp_path / "fakebin", tmp_path / "calls.log"
    bindir.mkdir()
    sudo = bindir / "sudo"
    sudo.write_text(f'#!/bin/sh\necho "sudo $*" >> "{log}"\nHOME=/nonexistent-root-home\nexport HOME\nexec "$@"\n')
    for name in ("apt-get", "brew", "npm"):
        (bindir / name).write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\nexit 1\n')
    for f in bindir.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    return bindir, log


def _sh_env(tmp_path: Path, bindir: Path, **extra) -> dict:
    home = tmp_path / "ho me"                        # a space: the HOME handed on must stay one word
    home.mkdir(exist_ok=True)
    env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "HOME": str(home), "LC_ALL": "C",
           "TMPDIR": str(tmp_path)}
    env.update(extra)
    return env


def _join_args(tmp_path: Path) -> str:
    return f"--token {TOKEN} --host {HOST} --hub https://hub.example.test --hq-root '{tmp_path}/hq'"


def test_dry_run_step_9_names_the_home_and_the_node_yaml_it_reads(tmp_path):
    bindir, calls = _fake_bin(tmp_path)
    env = _sh_env(tmp_path, bindir)
    home = env["HOME"]
    r = subprocess.run(["sh", str(JOIN_SH), "--token", TOKEN, "--host", HOST, "--hub", "https://hub.example.test",
                        "--hq-root", str(tmp_path / "hq"), "--dry-run"],
                       capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    step8, step9 = r.stdout.split("[8/9]", 1)[1].split("[9/9]", 1)
    # the very command a real run executes: HOME and ORG_HOST ride in the env
    assert f"env HOME={home} ORG_HOST={HOST} " in step9, step9
    assert "tools.node_dispatch probe" in step9
    # and the file it reads is the one step 8 is announced to write
    assert f"{home}/.config/mooniex/node.yaml" in step9
    assert f"node.yaml: host, os, hq_root -> {home}/.config/mooniex/node.yaml" in step8
    assert not calls.exists(), calls.read_text()        # a dry run calls nothing


def _stub_python(tmp_path: Path) -> Path:
    """Stands in for `$PY` in do_probe. `-c` is the JSON reader at the end of do_probe: the real
    interpreter. Anything else is the probe: it asks lib.config who this machine is, through the
    HOME it was started with, which is what tools.node_dispatch probe does first."""
    stub = tmp_path / "stub-python"
    stub.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = "-c" ]; then exec "$REAL_PY" "$@"; fi\n'
        'exec "$REAL_PY" -c \'\n'
        'import json\n'
        'from lib import config\n'
        'try:\n'
        '    h = config.self_host()\n'
        '    print(json.dumps({"ok": True, "result": {"host": h, "os": config.hosts()[h]["os"],'
        ' "free_gb": 1, "runners": []}}))\n'
        'except Exception as e:\n'
        '    print(json.dumps({"ok": False, "error": str(e)}))\n'
        '\'\n')
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    return stub


def _step_8_then_9(tmp_path: Path, join_sh: Path = JOIN_SH):
    """join.sh's own parse_args + check_args, then step 8's write_node_yaml, then step 9's do_probe,
    under a `sudo` that swaps HOME for root's. Returns (result, call log, HOME)."""
    bindir, calls = _fake_bin(tmp_path)
    env = _sh_env(tmp_path, bindir, ORG_JOIN_LIB="1", JOIN_SH=str(join_sh), REAL_PY=sys.executable,
                  PYTHONPATH=str(ROOT), STUB=str(_stub_python(tmp_path)))
    (tmp_path / "hq" / "Agents" / "Core").mkdir(parents=True)
    body = (
        '. "$JOIN_SH"\n'
        f'parse_args {_join_args(tmp_path)}\n'
        'check_args\n'
        'PY=$STUB; DRY_RUN=0\n'
        'mkdir -p "$CONF_DIR"\n'
        'write_node_yaml\n'
        'do_probe\n'
    )
    r = subprocess.run(["sh", "-c", body], capture_output=True, text=True, env=env, timeout=60)
    return r, calls, Path(env["HOME"])


@not_root
def test_the_probe_reads_the_node_yaml_step_8_wrote_even_when_sudo_resets_home(tmp_path):
    r, calls, home = _step_8_then_9(tmp_path)
    assert (home / ".config" / "mooniex" / "node.yaml").is_file()
    assert r.returncode == 0, r.stdout + r.stderr
    this_os = {"Darwin": "darwin", "Linux": "linux"}[platform.system()]      # check_args reads uname
    assert f"probe: ok host={HOST} os={this_os}" in r.stdout, r.stdout + r.stderr
    sudo_line = calls.read_text().splitlines()[0]
    assert sudo_line.startswith(f"sudo env HOME={home} ORG_HOST={HOST} "), sudo_line


@not_root
def test_the_same_run_fails_when_the_home_is_left_out_of_the_probe_command(tmp_path):
    # The control. With HOME taken back out of the probe's command line the run reproduces the
    # bug (root's HOME, no node.yaml, "not a known host"), so the pass above is the HOME
    # pass-through and not the stub being kind.
    text = JOIN_SH.read_text()
    assert ' env HOME="$HOME" ORG_HOST="$HOST" ' in text
    broken = tmp_path / "join-without-home.sh"
    broken.write_text(text.replace(' env HOME="$HOME" ORG_HOST="$HOST" ', ' env ORG_HOST="$HOST" '))
    r, _, _ = _step_8_then_9(tmp_path, broken)
    assert r.returncode == 1 and "probe: FAILED" in r.stdout and "not a known host" in r.stdout, r.stdout


def _function_body(text: str, name: str) -> str:
    m = re.search(r"^function " + re.escape(name) + r" \{.*?^\}", text, re.S | re.M)
    assert m, name
    return m.group(0)


def test_join_ps1_runs_step_9_in_the_window_and_user_that_wrote_node_yaml():
    # Windows has no sudo hop. "Run as administrator" keeps the account, so USERPROFILE is the
    # same, and the probe is a child of this same process: it inherits that USERPROFILE, which is
    # what Path.home() reads on Windows. ConfDir (where step 8 writes node.yaml) is built from it.
    text = JOIN_PS1.read_text(encoding="ascii")
    assert "$script:ConfDir = Join-Path $env:USERPROFILE '.config\\mooniex'" in text
    probe = _function_body(text, "Invoke-Probe")
    for hop in ("Start-Process", "-Credential", "-Verb", "runas", "Invoke-Command", "$env:USERPROFILE ="):
        assert hop not in probe, hop
    assert "$venvPy (Join-Path $script:Core 'tools\\infisical_setup.py') run Agents-Core prod" in probe
    # the dry run says which node.yaml the probe reads, and under which USERPROFILE
    assert "(Join-Path $script:ConfDir 'node.yaml')" in probe and "$env:USERPROFILE" in probe
    assert "Write-NodeYaml" in _function_body(text, "Save-Identity")
    assert "Join-Path $script:ConfDir 'node.yaml'" in _function_body(text, "Write-NodeYaml")


# ---------------------------------------------------------------- 2: one host-name rule

def test_node_host_re_is_lib_config_host_name_re_to_the_character():
    # infisical_setup.py cannot import lib.config (one stdlib-only file), so the rule is copied
    # and this test is what keeps the copies the same string.
    assert infisical_setup.NODE_HOST_RE.pattern == config.HOST_NAME_RE.pattern == r"[a-z][a-z0-9-]{1,29}[a-z0-9]"
    assert infisical_setup.NODE_HOST_RE.flags == config.HOST_NAME_RE.flags
    assert hq_join.HOST_RE.pattern == infisical_setup.NODE_HOST_RE.pattern


@pytest.mark.parametrize("name, ok", [
    ("ab", False), ("abc", True), ("a" * 31, True), ("a" * 32, False), ("a-c", True), ("ab-", False),
    ("1bc", False), ("aBc", False), ("a_c", False), ("", False),
])
def test_node_host_re_takes_3_to_31_characters(name, ok):
    assert bool(infisical_setup.NODE_HOST_RE.fullmatch(name)) is ok
    assert bool(config.HOST_NAME_RE.fullmatch(name)) is ok


def test_mint_node_secret_refuses_a_32_character_host_before_it_talks_to_anyone():
    with pytest.raises(infisical_setup.ApiError, match="bad host name"):
        infisical_setup.mint_node_secret(None, "a" * 32)       # org=None: the name is checked first


def test_infisical_setup_imports_only_the_standard_library():
    # A Run Inbox card copies this one file onto a box that has nothing else of ours.
    tree = ast.parse((ROOT / "tools" / "infisical_setup.py").read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    assert mods, "no imports found: the check is reading nothing"
    assert mods <= set(sys.stdlib_module_names), sorted(mods - set(sys.stdlib_module_names))


# ---------------------------------------------------------------- 3: seed_hosts_from_config

def _drop_pg(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for table in _PG_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(params=["sqlite", "pg"])
def hub(request, monkeypatch, tmp_path):
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    if request.param == "pg":
        if not ORG_TEST_DB_URL:
            pytest.skip("ORG_TEST_DB_URL not set -- pg param runs only against a throwaway org_test")
        monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
        _drop_pg(ORG_TEST_DB_URL)
        db.init()
        yield request.param
        _drop_pg(ORG_TEST_DB_URL)
    else:
        monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
        db.init()
        yield request.param


@pytest.fixture
def node_yaml(monkeypatch, tmp_path):
    """Write this machine's node.yaml (in tmp) and clear the caches that would hide it."""
    monkeypatch.delenv("ORG_HOST", raising=False)
    path = tmp_path / "node-home" / "node.yaml"
    monkeypatch.setattr(config, "NODE_CONFIG_PATH", path)

    def write(host=HOST, os_name="linux", hq_root="/opt/MoonieXHQ"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({"host": host, "os": os_name, "hq_root": hq_root}), encoding="utf-8")
        config.self_host.cache_clear()
        config.hosts.cache_clear()

    config.self_host.cache_clear()
    config.hosts.cache_clear()
    yield write
    config.self_host.cache_clear()
    config.hosts.cache_clear()


def _declared() -> dict:
    return yaml.safe_load(config.HOSTS_CONFIG.read_text(encoding="utf-8"))["hosts"]


def _row(name):
    row = db.get_host(name)
    return None if row is None else dict(row)


def test_the_node_yaml_entry_is_in_hosts_but_not_in_hosts_yaml(node_yaml):
    # the precondition every seed test below stands on
    node_yaml()
    assert HOST not in _declared()
    assert HOST in config.hosts()


def test_seed_leaves_the_hubs_row_for_a_joined_node_untouched(hub, node_yaml):
    token = hq_join.mint(HOST)["token"]
    hq_join.accept(token, HOST, "linux", "/opt/MoonieXHQ", PUB)
    db.upsert_host(HOST, status="online", free_gb=9.5)           # a heartbeat the hub has kept
    before = _row(HOST)
    hub_cfg = json.loads(before["config_json"])
    assert hub_cfg["ssh"] == HOST                                 # what the hub keeps ...

    node_yaml()
    synthesized = config.hosts()[HOST]
    assert synthesized["ssh"] is None and synthesized != hub_cfg  # ... is not what this node would write

    db.seed_hosts_from_config()

    assert _row(HOST) == before


def test_seed_creates_no_row_for_a_node_yaml_host_the_hub_has_never_heard_of(hub, node_yaml):
    node_yaml()
    db.seed_hosts_from_config()
    assert _row(HOST) is None
    assert {h["host"] for h in db.list_hosts()} == set(_declared())       # hosts.yaml, all of it, only it


def test_seed_still_writes_every_host_hosts_yaml_declares(hub, node_yaml):
    node_yaml()
    db.seed_hosts_from_config()
    for name, entry in _declared().items():
        row = _row(name)
        assert row is not None, name
        assert json.loads(row["config_json"]) == entry, name
        assert row["os"] == entry.get("os"), name


def test_a_node_yaml_that_names_a_hosts_yaml_host_is_seeded_from_hosts_yaml(hub, node_yaml):
    # hosts.yaml wins in lib.config.hosts(); seed follows it, so the node.yaml values never land.
    node_yaml(host="contabo", os_name="linux", hq_root="/srv/elsewhere")
    assert config.hosts()["contabo"] == _declared()["contabo"]
    db.seed_hosts_from_config()
    assert json.loads(_row("contabo")["config_json"]) == _declared()["contabo"]


def test_seed_twice_with_a_node_yaml_present_changes_nothing(hub, node_yaml):
    node_yaml()
    db.seed_hosts_from_config()
    first = {h["host"]: (h["os"], h["agents_root"], h["provides"], h["max_workers"], h["config_json"])
             for h in db.list_hosts()}
    db.seed_hosts_from_config()
    second = {h["host"]: (h["os"], h["agents_root"], h["provides"], h["max_workers"], h["config_json"])
              for h in db.list_hosts()}
    assert first == second and HOST not in first
