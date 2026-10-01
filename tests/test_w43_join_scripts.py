"""Org Mesh W4.3: deploy/join/join.sh and join.ps1.

Static checks (sh -n, shellcheck when installed, ASCII-only, pwsh parse when installed), a
`curl | sh`-shaped --dry-run against the real endpoint, and step-by-step runs of join.sh's own
functions (ORG_JOIN_LIB=1 sources the file without running it) against the real endpoint on a
throwaway SQLite ledger. No test installs anything, touches a real HOME, or contacts Infisical,
GitHub, Tailscale or a package manager: `sudo`, `apt-get`, `brew` and `npm` are replaced by
recorders, and the `save` step talks to a stub, never to infisical_setup.py.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w43_join_scripts.py
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import subprocess
import threading
import urllib.request
from pathlib import Path

import pytest
import yaml

from lib import db, sealed
from tools import hq_join, join_api

ROOT = Path(__file__).resolve().parent.parent
JOIN_SH = ROOT / "deploy" / "join" / "join.sh"
JOIN_PS1 = ROOT / "deploy" / "join" / "join.ps1"
UNIT = ROOT / "deploy" / "join" / "org-join.service"

TOKEN = "hqj_" + "Tok3n_-" * 6 + "T"                # hqj_ + 43 characters
assert len(TOKEN) == 47
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
DEPLOY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA" + "A" * 43 + " org-node:node-a"
CLIENT_ID = "client-id-synthetic"
CLIENT_SECRET = "client-secret-synthetic-7f3a"
TS_KEY = "tskey-auth-kSyntheticKey123-abcdefghijklmnop"

needs_age = pytest.mark.skipif(not (shutil.which("age") and shutil.which("age-keygen")),
                               reason="age is not installed")


# ---------------------------------------------------------------- static

def test_join_sh_parses_under_sh():
    r = subprocess.run(["sh", "-n", str(JOIN_SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck is not installed")
def test_join_sh_is_shellcheck_clean():
    r = subprocess.run(["shellcheck", "-s", "sh", str(JOIN_SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_the_node_side_files_are_ascii_only():
    # PowerShell 5.1 reads a BOM-less file as the ANSI code page: one stray byte above 127
    # (a dash, a quote) changes the script. join.sh and the unit travel the same way.
    for path in (JOIN_PS1, JOIN_SH, UNIT):
        data = path.read_bytes()
        bad = [i for i, b in enumerate(data) if b > 127]
        assert not bad, f"{path.name}: non-ASCII byte at offset {bad[0]}"
        assert not data.startswith(b"\xef\xbb\xbf")


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh is not installed")
def test_join_ps1_parses_under_powershell():
    cmd = ("$e = $null; $t = $null; "
           f"[System.Management.Automation.Language.Parser]::ParseFile('{JOIN_PS1}', [ref]$t, [ref]$e) | Out-Null; "
           "if ($e.Count) { $e | ForEach-Object { $_.ToString() }; exit 1 }")
    r = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_each_script_carries_the_hub_placeholder_exactly_once_and_the_nine_steps():
    for path in (JOIN_SH, JOIN_PS1):
        text = path.read_text(encoding="ascii")
        assert text.count(join_api.HUB_PLACEHOLDER.decode()) == 1, path.name
        for n in range(1, 10):
            assert f"step {n} " in text or f"Step {n} " in text, (path.name, n)


def test_no_script_line_prints_or_stores_the_token():
    sh = JOIN_SH.read_text().splitlines()
    assert not any(line.strip().startswith(("set -x", "set -o xtrace")) for line in sh)
    for n, line in enumerate(sh, 1):
        code = line.split("#", 1)[0]
        if "TOKEN" in code:
            assert "echo" not in code and not any(op in code for op in (" > ", ">>", "tee")), (n, line)
    for n, line in enumerate(JOIN_PS1.read_text().splitlines(), 1):
        if "$script:Token" in line or "$o.Token" in line:
            assert not any(w in line for w in ("Write-Host", "Say ", "Out-File", "Set-Content", "Add-Content",
                                               "Write-Output", "Tee-Object")), (n, line)


# ---------------------------------------------------------------- a real server

@pytest.fixture
def ledger(monkeypatch, tmp_path):
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()


@pytest.fixture
def server(ledger, caplog):
    caplog.set_level(logging.INFO)
    made = []

    def start(**kw):
        srv = join_api.make_server(0, **kw)
        t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        t.start()
        srv.url = f"http://127.0.0.1:{srv.server_address[1]}/org-join"
        made.append((srv, t))
        return srv

    yield start
    for srv, t in made:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=5)


def _recorders(tmp_path: Path) -> tuple[Path, Path]:
    """A bin dir whose sudo/apt-get/brew/npm record the call and fail, so a dry run that
    reached any of them is caught. Returns (bin dir, call log)."""
    bindir, log = tmp_path / "fakebin", tmp_path / "calls.log"
    bindir.mkdir()
    for name in ("sudo", "apt-get", "brew", "npm"):
        f = bindir / name
        f.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\nexit 1\n')
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    return bindir, log


def _env(tmp_path: Path, bindir: Path | None = None, **extra) -> dict:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    path = os.environ["PATH"] if bindir is None else f"{bindir}{os.pathsep}{os.environ['PATH']}"
    env = {"PATH": path, "HOME": str(home), "LC_ALL": "C", "TMPDIR": str(tmp_path)}
    env.update(extra)
    return env


def _run(args, *, env, stdin_text=None, timeout=60):
    # start_new_session: no controlling terminal. join.sh asks for a missing token on /dev/tty, and
    # a test run from a terminal would otherwise stop and wait for a person to type it.
    return subprocess.run(args, input=stdin_text, capture_output=True, text=True, env=env, timeout=timeout,
                          start_new_session=True)


def _tree(path: Path) -> list:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


# ---------------------------------------------------------------- the dry run

def test_dry_run_through_the_curl_pipe_prints_nine_steps_and_changes_nothing(server, caplog, tmp_path):
    srv = server()
    script = urllib.request.urlopen(f"{srv.url}/join.sh", timeout=10).read().decode("ascii")
    bindir, calls = _recorders(tmp_path)
    env = _env(tmp_path, bindir)
    home = Path(env["HOME"])
    before = _tree(home)

    # `curl .../join.sh | sh -s -- ...`: the script arrives on stdin, with its hub filled in
    r = _run(["sh", "-s", "--", "--token", TOKEN, "--host", "node-a", "--dry-run"],
             env=env, stdin_text=script)

    assert r.returncode == 0, r.stderr + r.stdout
    positions = [r.stdout.find(f"[{n}/9]") for n in range(1, 10)]
    assert all(p >= 0 for p in positions), r.stdout
    assert positions == sorted(positions)
    assert f"hub {srv.url}" in r.stdout
    assert "DRY RUN" in r.stdout and "Nothing was changed" in r.stdout
    assert "ROOT NEEDED" in r.stdout          # elevation is announced before anything runs
    assert _tree(home) == before == []         # HOME untouched: no key, no node.yaml, no dir
    assert not calls.exists(), calls.read_text()   # no sudo, no package manager, nothing
    assert TOKEN not in r.stdout + r.stderr
    served = [rec.getMessage() for rec in caplog.records if rec.name == "join_api"]
    assert served == ["GET /org-join/join.sh 200 host=-"], served   # the dry run contacted nothing


def test_dry_run_names_the_files_it_would_make(server, tmp_path):
    srv = server()
    env = _env(tmp_path, _recorders(tmp_path)[0])
    r = _run(["sh", str(JOIN_SH), "--token", TOKEN, "--host", "node-a", "--hub", srv.url,
              "--hq-root", str(tmp_path / "hq"), "--dry-run"], env=env)
    assert r.returncode == 0, r.stderr
    home = env["HOME"]
    for want in (f"{home}/.config/mooniex/age-identity.txt", f"{home}/.config/mooniex/deploy_key",
                 f"{home}/.ssh/org_dispatch", f"{home}/.config/mooniex/node.yaml",
                 f"{tmp_path}/hq/Agents/Core", "git@github.com:PASAKON/Agents-Core.git",
                 "--advertise-tags=tag:org-node", "infisical_setup.py save node-a --stdin",
                 "tools/node_dispatch.py probe"):
        assert want in r.stdout, want


def test_the_token_can_come_from_the_environment_and_is_never_echoed(server, tmp_path):
    srv = server()
    env = _env(tmp_path, _recorders(tmp_path)[0], ORG_JOIN_TOKEN=TOKEN)
    r = _run(["sh", str(JOIN_SH), "--host", "node-a", "--hub", srv.url, "--dry-run"], env=env)
    assert r.returncode == 0, r.stderr
    assert TOKEN not in r.stdout + r.stderr


def test_help_prints_usage_and_exits_zero(tmp_path):
    r = _run(["sh", str(JOIN_SH), "--help"], env=_env(tmp_path))
    assert r.returncode == 0 and "--token" in r.stdout and "--dry-run" in r.stdout


@pytest.mark.parametrize("args, message", [
    ([], "no token"),
    (["--token", "hqj_short", "--host", "node-a", "--hub", "http://h:1"], "not in the expected shape"),
    (["--token", TOKEN, "--hub", "http://h:1"], "no --host"),
    (["--token", TOKEN, "--host", "Node_A", "--hub", "http://h:1"], "--host must be 3-31"),
    (["--token", TOKEN, "--host", "a" * 32, "--hub", "http://h:1"], "--host must be 3-31"),
    (["--token", TOKEN, "--host", "node-a", "--hub", "http://h:1", "--bogus"], "unknown argument"),
    (["--token", TOKEN, "--host", "node-a", "--hub", "http://h:1", "--hq-root", "rel/path"], "absolute"),
    (["--token", TOKEN, "--host", "node-a"], "no hub URL"),          # the raw file: placeholder unreplaced
    (["--token", TOKEN, "--host", "node-a", "--hub", "ftp://x"], "--hub must look like"),
    (["--token", TOKEN, "--host", "node-a", "--hub", "http://hub.example.test"], "must be https"),
    (["--token", TOKEN, "--host", "node-a", "--hub", "http://127.0.0.1.evil.test"], "must be https"),
    (["--token"], "--token needs a value"),
])
def test_bad_arguments_stop_at_step_1_and_never_echo_the_token(tmp_path, args, message):
    bindir, calls = _recorders(tmp_path)
    r = _run(["sh", str(JOIN_SH), *args], env=_env(tmp_path, bindir))
    assert r.returncode == 1
    assert message in r.stderr, r.stderr
    assert r.stderr.startswith("\njoin: ")
    assert TOKEN not in r.stdout + r.stderr
    assert "[2/9]" not in r.stdout and not calls.exists()


# ---------------------------------------------------------------- the steps, one at a time

def _lib(tmp_path, body: str, *, hub: str, host="node-a", token=TOKEN, age_pub=PUB, extra=None,
         timeout=60):
    """Source join.sh without running it, set what check_args/do_keys would have set, run `body`."""
    home = tmp_path / "home"
    env = _env(tmp_path, ORG_JOIN_LIB="1", JOIN_SH=str(JOIN_SH), T_HUB=hub, T_HOST=host, T_TOKEN=token,
               T_PUB=age_pub, T_DEPLOY=DEPLOY, T_HOME=str(home))
    env.update(extra or {})
    prelude = (
        '. "$JOIN_SH"\n'
        'HUB=$T_HUB; HOST=$T_HOST; TOKEN=$T_TOKEN; OS=linux; HQ_ROOT=/opt/MoonieXHQ; PY=python3\n'
        'AGE_PUB=$T_PUB; DEPLOY_PUB=$T_DEPLOY; DRY_RUN=0\n'
        'CONF_DIR=$T_HOME/.config/mooniex; AGE_ID=$CONF_DIR/age-identity.txt\n'
    )
    return _run(["sh", "-c", prelude + body], env=env, timeout=timeout)


def test_the_accept_step_joins_through_the_real_endpoint_and_gets_no_tailscale_key(server, tmp_path):
    minted = []
    srv = server(minter=lambda host: minted.append(host) or TS_KEY)
    token = hq_join.mint("node-a")["token"]
    r = _lib(tmp_path, 'do_accept; printf "TS=[%s]\\n" "$TS_KEY"', hub=srv.url, token=token)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "accepted" in r.stdout and "TS=[]" in r.stdout    # the key comes with the sealed answer
    assert minted == [] and TS_KEY not in r.stdout + r.stderr
    row = db.get_host("node-a")
    assert row["status"] == "pending_identity" and row["pubkey"] == PUB
    assert row["deploy_pubkey"].startswith("ssh-ed25519 AAAA")
    assert token not in r.stdout + r.stderr


def test_a_second_run_with_the_same_token_carries_on(server, tmp_path):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    assert "accepted" in _lib(tmp_path, "do_accept", hub=srv.url, token=token).stdout
    again = _lib(tmp_path, "do_accept", hub=srv.url, token=token)
    assert again.returncode == 0, again.stderr
    assert "already joined with this token" in again.stdout


def test_a_token_that_was_never_valid_stops_the_run(server, tmp_path):
    srv = server()
    r = _lib(tmp_path, "do_accept", hub=srv.url, token="hqj_" + "Q" * 43)
    assert r.returncode == 1
    assert "refused this token" in r.stderr and "hqj_QQQ" not in r.stderr + r.stdout


def test_the_hubs_message_for_a_bad_key_is_shown(server, tmp_path):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    r = _lib(tmp_path, "do_accept", hub=srv.url, token=token, age_pub="age1notakey")
    assert r.returncode == 1 and "not a valid age X25519 recipient" in r.stderr


def test_an_unreachable_hub_is_named_not_hung(tmp_path):
    r = _lib(tmp_path, "do_accept", hub="http://127.0.0.1:1/org-join", timeout=40)
    assert r.returncode == 1 and "could not reach the hub" in r.stderr


CIPHER = "-----BEGIN AGE ENCRYPTED FILE-----\nc3ludGhldGlj\n-----END AGE ENCRYPTED FILE-----\n"


def _ready(host="node-a", ciphertext=CIPHER):
    now = "2026-10-01T00:00:00+00:00"
    with db.get_conn() as conn:
        conn.execute("INSERT INTO node_secrets (host, ciphertext, infisical_client_secret_id, created_at) "
                     "VALUES (?, ?, ?, ?)", (host, ciphertext, "sid-1", now))
        conn.execute("UPDATE hosts SET status = ? WHERE host = ?", (hq_join.STATUS_READY, host))


def test_the_wait_step_returns_the_ciphertext_once_the_hub_has_sealed_it(server, tmp_path):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    assert "accepted" in _lib(tmp_path, "do_accept", hub=srv.url, token=token).stdout
    _ready()
    r = _lib(tmp_path, 'do_wait_sealed; printf "%s" "$CIPHER"', hub=srv.url, token=token)
    assert r.returncode == 0, r.stderr
    assert r.stdout.endswith(CIPHER.rstrip("\n"))   # multi-line, intact


def test_the_wait_step_gives_up_and_says_how_to_continue(server, tmp_path):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    _lib(tmp_path, "do_accept", hub=srv.url, token=token)       # the host stays pending_identity
    r = _lib(tmp_path, "POLL_S=1; POLL_MAX_S=1; do_wait_sealed", hub=srv.url, token=token)
    assert r.returncode == 1
    assert "pending" in r.stdout and "gave up waiting" in r.stderr and "same command again" in r.stderr


def test_the_wait_step_stops_at_once_when_the_hub_refuses(server, tmp_path):
    srv = server()
    r = _lib(tmp_path, "POLL_S=1; POLL_MAX_S=30; do_wait_sealed", hub=srv.url, token="hqj_" + "Q" * 43)
    assert r.returncode == 1 and "will not release" in r.stderr


# ---------------------------------------------------------------- the tailnet comes after the wait

def test_the_wait_step_takes_the_tailscale_key_from_the_sealed_answer(server, tmp_path):
    minted = []
    srv = server(minter=lambda host: minted.append(host) or TS_KEY)
    token = hq_join.mint("node-a")["token"]
    _lib(tmp_path, "do_accept", hub=srv.url, token=token)
    _ready()
    r = _lib(tmp_path, 'do_wait_sealed; printf "TS=%s\\n" "$TS_KEY"', hub=srv.url, token=token)
    assert r.returncode == 0, r.stderr
    assert f"TS={TS_KEY}" in r.stdout and minted == ["node-a"]
    # the script itself never prints the key: only the test's own printf above did
    quiet = _lib(tmp_path, "do_wait_sealed", hub=srv.url, token=token)
    assert quiet.returncode == 0 and TS_KEY not in quiet.stdout + quiet.stderr


def test_a_node_still_waiting_for_approval_has_no_key_and_the_hub_minted_none(server, tmp_path):
    minted = []
    srv = server(minter=lambda host: minted.append(host) or TS_KEY)
    token = hq_join.mint("node-a")["token"]
    _lib(tmp_path, "do_accept", hub=srv.url, token=token)       # pending_identity: not approved
    r = _lib(tmp_path, 'POLL_S=1; POLL_MAX_S=1; do_wait_sealed', hub=srv.url, token=token)
    assert r.returncode == 1 and "gave up waiting" in r.stderr
    assert minted == [] and TS_KEY not in r.stdout + r.stderr


def _tailscale_stub(tmp_path: Path, *, on_tailnet: bool) -> tuple[dict, Path]:
    """A `tailscale` that answers `ip -4` and records `up`, and an as_root that runs the command
    itself (sudo is a recorder in these tests). Returns (extra env for _lib, the call log)."""
    bindir, log = tmp_path / "tsbin", tmp_path / "tailscale.log"
    bindir.mkdir()
    exe = bindir / "tailscale"
    ip = "echo 100.64.0.9; exit 0" if on_tailnet else "exit 1"
    exe.write_text(f'#!/bin/sh\ncase "$1" in\n  ip) {ip} ;;\n  up) echo "$*" >> "{log}"; exit 0 ;;\nesac\nexit 2\n')
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}, log


def test_the_tailnet_step_joins_with_the_key_the_wait_step_got_and_forgets_it(server, tmp_path):
    srv = server()
    extra, log = _tailscale_stub(tmp_path, on_tailnet=False)
    r = _lib(tmp_path, f'as_root() {{ "$@"; }}; TS_KEY={TS_KEY}; do_tailscale; printf "after=[%s]\\n" "$TS_KEY"',
             hub=srv.url, extra=extra)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "[6/9] join the tailnet" in r.stdout and "joined the tailnet" in r.stdout
    assert log.read_text().strip() == f"up --auth-key {TS_KEY} --hostname node-a --advertise-tags=tag:org-node"
    assert "after=[]" in r.stdout and TS_KEY not in r.stdout + r.stderr


def test_the_tailnet_step_keeps_the_already_on_it_path_and_the_join_by_hand_message(server, tmp_path):
    srv = server()
    extra, log = _tailscale_stub(tmp_path, on_tailnet=True)
    r = _lib(tmp_path, f'as_root() {{ "$@"; }}; TS_KEY={TS_KEY}; do_tailscale', hub=srv.url, extra=extra)
    assert r.returncode == 0 and "already on the tailnet as 100.64.0.9" in r.stdout
    assert not log.exists()                        # on the tailnet already: the key is not used

    off = tmp_path / "off"
    off.mkdir()
    extra, log = _tailscale_stub(off, on_tailnet=False)
    r = _lib(tmp_path, 'as_root() { "$@"; }; TS_KEY=; do_tailscale', hub=srv.url, extra=extra)
    assert r.returncode == 1 and not log.exists()
    assert "hub sent no Tailscale key" in r.stderr and "tailscale up --hostname node-a" in r.stderr


# ---------------------------------------------------------------- step 8, with a real age

def _stub_core(tmp_path: Path, *, exit_code=0) -> tuple[Path, Path]:
    """A checkout whose tools/infisical_setup.py records what `save` would have been given."""
    core = tmp_path / "hq" / "Agents" / "Core"
    (core / "tools").mkdir(parents=True)
    out = tmp_path / "save.json"
    (core / "tools" / "infisical_setup.py").write_text(
        "import json, sys\n"
        "data = sys.stdin.read()\n"
        f"open({str(out)!r}, 'w').write(json.dumps({{'argv': sys.argv[1:], 'stdin': data}}))\n"
        "if not data.strip():\n"
        "    sys.exit('empty input, nothing saved')\n"
        f"sys.exit({exit_code})\n")
    return core, out


def _age_identity(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["age-keygen", "-o", str(path)], check=True, capture_output=True)
    path.chmod(0o600)
    return subprocess.run(["age-keygen", "-y", str(path)], check=True, capture_output=True, text=True).stdout.strip()


def _seal_for(pub: str, **over) -> str:
    payload = {"v": 1, "host": "node-a", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    payload.update(over)
    return sealed.seal(pub, json.dumps(payload).encode()).decode("ascii")


_IDENTITY_BODY = (
    'as_root() { "$@"; }; sudo() { :; }\n'          # the test is not root and must never prompt
    'CORE=$T_CORE; CIPHER=$T_CIPHER; PY=python3\n'
    "do_identity\n"
)


@needs_age
def test_the_identity_step_decrypts_and_hands_two_lines_to_save(tmp_path):
    home = tmp_path / "home"
    pub = _age_identity(home / ".config" / "mooniex" / "age-identity.txt")
    core, out = _stub_core(tmp_path)
    r = _lib(tmp_path, _IDENTITY_BODY, hub="http://h:1/org-join",
             extra={"T_CORE": str(core), "T_CIPHER": _seal_for(pub)})
    assert r.returncode == 0, r.stderr + r.stdout
    got = json.loads(out.read_text())
    assert got["argv"] == ["save", "node-a", "--stdin"]
    assert got["stdin"] == f"{CLIENT_ID}\n{CLIENT_SECRET}\n"
    assert CLIENT_SECRET not in r.stdout + r.stderr and CLIENT_ID not in r.stdout + r.stderr
    node = yaml.safe_load((home / ".config" / "mooniex" / "node.yaml").read_text())
    assert node == {"host": "node-a", "os": "linux", "hq_root": "/opt/MoonieXHQ"}


@needs_age
def test_the_identity_step_with_the_wrong_key_stores_nothing_and_leaks_nothing(tmp_path):
    home = tmp_path / "home"
    _age_identity(home / ".config" / "mooniex" / "age-identity.txt")
    stranger = _age_identity(tmp_path / "other" / "identity.txt")
    core, out = _stub_core(tmp_path)
    r = _lib(tmp_path, _IDENTITY_BODY, hub="http://h:1/org-join",
             extra={"T_CORE": str(core), "T_CIPHER": _seal_for(stranger)})
    assert r.returncode == 1
    assert "nothing was stored" in r.stderr
    assert json.loads(out.read_text())["stdin"].strip() == ""      # `save` got no secret and refused
    assert not (home / ".config" / "mooniex" / "node.yaml").exists()
    assert CLIENT_SECRET not in r.stdout + r.stderr


@needs_age
def test_the_identity_step_refuses_a_node_yaml_that_names_another_host(tmp_path):
    home = tmp_path / "home"
    pub = _age_identity(home / ".config" / "mooniex" / "age-identity.txt")
    (home / ".config" / "mooniex" / "node.yaml").write_text("host: mac\n")
    core, _ = _stub_core(tmp_path)
    r = _lib(tmp_path, _IDENTITY_BODY, hub="http://h:1/org-join",
             extra={"T_CORE": str(core), "T_CIPHER": _seal_for(pub)})
    assert r.returncode == 1 and "already names another host" in r.stderr
    assert (home / ".config" / "mooniex" / "node.yaml").read_text() == "host: mac\n"
