"""Org Mesh W1.8 (task-1670b1f8): the pieces that put Contabo's ledger consumers on
the Postgres hub, built and tested, installed nowhere (docs/design/org-mesh-w18-contabo-consumers.md).

Three groups:

  1. scripts/hub/with-org-db-env.sh -- env file with ORG_DB_URL means no Infisical;
     no ORG_DB_URL plus this host's identity file means the command runs through
     `tools/infisical_setup.py run Agents-Core prod`; neither means a plain exec.
  2. deploy/systemd/<unit>.service.d/org-db.conf -- parsed, not run.
  3. scripts/hub/contabo-cutover-remote.sh steps 4, 5 and 8 against a throwaway git
     root, with fake `python3`, `systemctl` and `tmux` first on PATH. (W1.9 follow-up,
     task-a23e8873: step 4 only refuses; step 5 stops the units; step 8 installs the
     drop-ins. tests/test_w19b_cutover_fixes.py pins that order.)

Nothing here reaches a real file, service or database. Every child process gets a
built env (no ORG_DB_URL, no ORG_HOST inherited from the developer's shell or from a
suite run with ORG_HOST=contabo); the env file, node file, identity dir, systemd dir
and repo root are all under tmp_path. The fake `python3` stands in for
tools/infisical_setup.py: it records the argv it got (URLs redacted) and execs the
command after `--` with a fake ORG_DB_URL in its environment, as the real one does.
The fake URL carries a sentinel password; no test may see it in any output or log.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
HUB = ROOT / "scripts" / "hub"
WRAPPER = HUB / "with-org-db-env.sh"
REMOTE = HUB / "contabo-cutover-remote.sh"
CUTOVER = HUB / "contabo-cutover.sh"
SYSTEMD = ROOT / "deploy" / "systemd"
BLUEPRINT = ROOT / "state" / "contabo-blueprint-20260924" / "systemd-mooniex-units"
DESIGN = "docs/design/org-mesh-w18-contabo-consumers.md"

UNITS = ("mooniex-watchdog", "mooniex-secretary", "mooniex-secretary-waker")
SECRETARY_UNITS = ("mooniex-secretary", "mooniex-secretary-waker")

SENTINEL = "SENTINEL-W18-must-not-leak"
FAKE_URL = f"postgresql://fake:{SENTINEL}@127.0.0.1:1/org"

# ------------------------------------------------------------------ fake tools

_FAKE_PYTHON3 = """#!@PY@
import json, os, sys
argv = sys.argv[1:]
redact = lambda a: "<url>" if "postgresql://" in a else a
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"tool": "python3", "argv": [redact(a) for a in argv]}) + "\\n")
if argv and argv[0].endswith("/tools/infisical_setup.py"):
    if os.environ.get("FAKE_INFISICAL_FAIL") == "1":
        sys.stderr.write("fake infisical: refusing\\n")
        sys.exit(1)
    cmd = argv[argv.index("--") + 1:]
    os.execvpe(cmd[0], cmd, dict(os.environ, ORG_DB_URL="@URL@"))
os.execv("@PY@", ["@PY@"] + argv)
"""

# .venv/bin/python and .venv/bin/pip of the throwaway root: log, never run anything.
# node_hub = the node file already says `org_db: hub` at the moment of the call (NODE_YAML
# reaches every child, as the remote script's own env). dropins = how many
# <unit>.service.d/org-db.conf exist under SYSTEMD_DIR at that moment. FAKE_MIGRATE_FAIL
# makes the migration command exit 1.
_FAKE_VENV_TOOL = """#!@PY@
import glob, json, os, sys
redact = lambda a: "<url>" if "postgresql://" in a else a
node = os.environ.get("NODE_YAML", "")
node_hub = os.path.exists(node) and "org_db: hub" in open(node).read()
dropins = len(glob.glob(os.environ.get("SYSTEMD_DIR", "/nonexistent") + "/*/org-db.conf"))
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"tool": "@NAME@", "argv": [redact(a) for a in sys.argv[1:]],
                        "org_db_url": bool(os.environ.get("ORG_DB_URL")),
                        "node_hub": node_hub, "dropins": dropins}) + "\\n")
if os.environ.get("FAKE_MIGRATE_FAIL") and sys.argv[1:2] and sys.argv[1].endswith("migrate_tasks_db.py"):
    sys.exit(1)
"""

# dropins as above; node_env = MOONIEX_NODE_YAML as the script exported it to this child.
# FAKE_STOP_FAIL_UNIT / FAKE_RELOAD_FAIL make `stop <unit>` / `daemon-reload` exit 1.
_FAKE_SYSTEMCTL = """#!@PY@
import glob, json, os, sys
argv = sys.argv[1:]
node = os.environ.get("NODE_YAML", "")
node_hub = os.path.exists(node) and "org_db: hub" in open(node).read()
dropins = len(glob.glob(os.environ.get("SYSTEMD_DIR", "/nonexistent") + "/*/org-db.conf"))
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"tool": "systemctl", "argv": argv, "node_hub": node_hub,
                        "tombstone": os.path.isdir("state/tasks.db"), "dropins": dropins,
                        "node_env": os.environ.get("MOONIEX_NODE_YAML")}) + "\\n")
unit = (argv[-1] if argv else "").removesuffix(".service")
if argv[:1] == ["cat"] and unit == os.environ.get("FAKE_MISSING_UNIT"):
    sys.exit(1)
if argv[:1] == ["stop"] and unit == os.environ.get("FAKE_STOP_FAIL_UNIT"):
    sys.exit(1)
if argv[:1] == ["daemon-reload"] and os.environ.get("FAKE_RELOAD_FAIL"):
    sys.exit(1)
if argv[:1] == ["restart"] and unit == os.environ.get("FAKE_RESTART_FAIL_UNIT"):
    sys.exit(1)
if argv[:1] == ["is-active"] and unit == os.environ.get("FAKE_INACTIVE_UNIT"):
    sys.exit(3)
"""


def _make_fakebin(tmp_path: Path) -> Path:
    b = tmp_path / "fakebin"
    b.mkdir()
    for name, body in (("python3", _FAKE_PYTHON3), ("systemctl", _FAKE_SYSTEMCTL),
                       ("tmux", "#!/bin/sh\nexit 1\n")):
        p = b / name
        p.write_text(body.replace("@PY@", sys.executable).replace("@URL@", FAKE_URL))
        p.chmod(0o755)
    return b


def _read_log(log: Path) -> list[dict]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]


def _env(tmp_path: Path, fakebin: Path, log: Path, **extra: str) -> dict[str, str]:
    """A built env, never os.environ: no ORG_DB_URL, no ORG_HOST, every host path in tmp_path."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {
        "PATH": f"{fakebin}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(home),
        "FAKE_LOG": str(log),
        "MOONIEX_ORG_DB_ENV": str(tmp_path / "no-such-org-db.env"),
        "MOONIEX_NODE_YAML": str(tmp_path / "no-such-node.yaml"),
        "INFISICAL_CRED_DIR": str(tmp_path / "no-such-cred-dir"),
    }
    env.update(extra)
    return env


# ------------------------------------------------------------------- 1. wrapper

CHILD = ["sh", "-c", 'printf "%s" "${ORG_DB_URL:+set}"']  # prints "set" or nothing, never the value


@pytest.fixture
def wrapper_box(tmp_path):
    """A fake Agents root holding a copy of the wrapper, so its $ROOT is under tmp_path."""
    root = tmp_path / "agents"
    (root / "scripts" / "hub").mkdir(parents=True)
    wrapper = root / "scripts" / "hub" / "with-org-db-env.sh"
    shutil.copy2(WRAPPER, wrapper)
    fakebin = _make_fakebin(tmp_path)
    log = tmp_path / "calls.jsonl"
    return SimpleNamespace(
        root=root, wrapper=wrapper, log=log, tmp=tmp_path,
        env=lambda **extra: _env(tmp_path, fakebin, log, **extra),
    )


def _run_wrapper(box, env: dict[str, str], *cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(box.wrapper), *(cmd or CHILD)], env=env, capture_output=True,
                          text=True, timeout=30)


def _infisical_calls(box) -> list[list[str]]:
    return [c["argv"] for c in _read_log(box.log) if c["tool"] == "python3"]


def _expected_argv(box, *cmd: str) -> list[str]:
    return [f"{box.root}/tools/infisical_setup.py", "run", "Agents-Core", "prod", "--",
            *(cmd or CHILD)]


def _id_file(box) -> Path:
    f = box.tmp / "contabo-identity.env"
    f.write_text("this file is never read\n")
    return f


def _no_leak(r: subprocess.CompletedProcess) -> None:
    assert SENTINEL not in r.stdout + r.stderr


def test_wrapper_env_file_with_org_db_url_means_no_infisical(wrapper_box):
    """The Mac's file carries ORG_DB_URL: sourced as before, even with an identity file present."""
    env_file = wrapper_box.tmp / "org-db.env"
    env_file.write_text(f"ORG_DB_URL={FAKE_URL}\n")
    ident = _id_file(wrapper_box)

    r = _run_wrapper(wrapper_box, wrapper_box.env(
        MOONIEX_ORG_DB_ENV=str(env_file), MOONIEX_INFISICAL_ID_FILE=str(ident)))

    assert (r.returncode, r.stdout) == (0, "set")
    assert _infisical_calls(wrapper_box) == []
    _no_leak(r)


def test_wrapper_contabo_shape_env_file_without_org_db_url_goes_through_infisical(wrapper_box):
    """Contabo: the env file holds POSTGRES_* only. The identity file exists -> infisical run."""
    env_file = wrapper_box.tmp / "org-db.env"
    env_file.write_text("POSTGRES_USER=u\nPOSTGRES_PASSWORD=pw-not-a-url\nPOSTGRES_DB=org\n")
    ident = _id_file(wrapper_box)

    r = _run_wrapper(wrapper_box, wrapper_box.env(
        MOONIEX_ORG_DB_ENV=str(env_file), MOONIEX_INFISICAL_ID_FILE=str(ident)))

    assert (r.returncode, r.stdout) == (0, "set")
    assert _infisical_calls(wrapper_box) == [_expected_argv(wrapper_box)]
    _no_leak(r)


def test_wrapper_no_env_file_but_identity_file_goes_through_infisical(wrapper_box):
    ident = _id_file(wrapper_box)

    r = _run_wrapper(wrapper_box, wrapper_box.env(MOONIEX_INFISICAL_ID_FILE=str(ident)))

    assert (r.returncode, r.stdout) == (0, "set")
    assert _infisical_calls(wrapper_box) == [_expected_argv(wrapper_box)]


def test_wrapper_neither_env_url_nor_identity_is_a_plain_exec(wrapper_box):
    r = _run_wrapper(wrapper_box, wrapper_box.env())

    assert (r.returncode, r.stdout) == (0, "")
    assert _infisical_calls(wrapper_box) == []


def test_wrapper_env_file_without_url_and_no_identity_stays_plain(wrapper_box):
    """Contabo before the identity exists: the child must not get an ORG_DB_URL from nowhere."""
    env_file = wrapper_box.tmp / "org-db.env"
    env_file.write_text("POSTGRES_USER=u\nPOSTGRES_PASSWORD=pw-not-a-url\n")

    r = _run_wrapper(wrapper_box, wrapper_box.env(
        MOONIEX_ORG_DB_ENV=str(env_file),
        MOONIEX_INFISICAL_ID_FILE=str(wrapper_box.tmp / "absent.env")))

    assert (r.returncode, r.stdout) == (0, "")
    assert _infisical_calls(wrapper_box) == []


def test_wrapper_an_org_db_url_already_in_the_environment_wins_over_the_identity(wrapper_box):
    ident = _id_file(wrapper_box)

    r = _run_wrapper(wrapper_box, wrapper_box.env(
        MOONIEX_INFISICAL_ID_FILE=str(ident), ORG_DB_URL=FAKE_URL))

    assert (r.returncode, r.stdout) == (0, "set")
    assert _infisical_calls(wrapper_box) == []


@pytest.mark.parametrize("how, node_body, org_host", [
    ("ORG_HOST", None, "contabo"),
    ("ORG_HOST is lowercased and trimmed", None, "  Contabo "),
    ("node host", "host: contabo\n", None),
    ("node host, quotes + comment + CRLF", 'org_db: hub\r\nhost: "Contabo"   # the VPS\r\n', None),
    ("node host, CRLF and no comment", "host: contabo\r\n", None),
    ("ORG_HOST wins over the node file", "host: mac\n", "contabo"),
])
def test_wrapper_finds_the_identity_by_host_name(wrapper_box, how, node_body, org_host):
    cred = wrapper_box.tmp / "cred"
    cred.mkdir()
    (cred / "contabo.env").write_text("never read\n")
    extra = {"INFISICAL_CRED_DIR": str(cred)}
    if node_body is not None:
        node = wrapper_box.tmp / "node.yaml"
        node.write_bytes(node_body.encode())
        extra["MOONIEX_NODE_YAML"] = str(node)
    if org_host is not None:
        extra["ORG_HOST"] = org_host

    r = _run_wrapper(wrapper_box, wrapper_box.env(**extra))

    assert (r.returncode, r.stdout) == (0, "set"), how
    assert _infisical_calls(wrapper_box) == [_expected_argv(wrapper_box)]


@pytest.mark.parametrize("how, node_body, org_host", [
    ("another host has no identity", "host: mac\n", None),
    ("ORG_HOST beats a node file that names contabo", "host: contabo\n", "mac"),
    ("no host anywhere", None, None),
    ("path traversal in ORG_HOST", None, "../evil"),
    ("slash in ORG_HOST", None, "a/b"),
    ("space inside the node host", "host: con tabo\n", None),
    ("newline inside ORG_HOST", None, "x\ncontabo"),
])
def test_wrapper_a_host_without_an_identity_file_stays_plain(wrapper_box, how, node_body, org_host):
    cred = wrapper_box.tmp / "cred"
    cred.mkdir()
    (cred / "contabo.env").write_text("never read\n")
    (wrapper_box.tmp / "evil.env").write_text("a file the traversal would reach\n")
    extra = {"INFISICAL_CRED_DIR": str(cred)}
    if node_body is not None:
        node = wrapper_box.tmp / "node.yaml"
        node.write_text(node_body)
        extra["MOONIEX_NODE_YAML"] = str(node)
    if org_host is not None:
        extra["ORG_HOST"] = org_host

    r = _run_wrapper(wrapper_box, wrapper_box.env(**extra))

    assert (r.returncode, r.stdout) == (0, ""), how
    assert _infisical_calls(wrapper_box) == []


def test_wrapper_only_tests_the_identity_file_it_never_opens_it(wrapper_box):
    ident = _id_file(wrapper_box)
    ident.chmod(0)  # a read would fail; a stat does not
    try:
        r = _run_wrapper(wrapper_box, wrapper_box.env(MOONIEX_INFISICAL_ID_FILE=str(ident)))
    finally:
        ident.chmod(stat.S_IRUSR | stat.S_IWUSR)

    assert (r.returncode, r.stdout) == (0, "set")
    assert "Permission denied" not in r.stderr


def test_wrapper_passes_hostile_arguments_through_untouched(wrapper_box):
    ident = _id_file(wrapper_box)
    hostile = ["a b", "c#d", "(x) [y]", "ไทย ทดสอบ", "--", "-n", "$HOME", ""]
    cmd = ["sh", "-c", 'for a in "$@"; do printf "<%s>" "$a"; done', "_", *hostile]

    for extra in ({}, {"MOONIEX_INFISICAL_ID_FILE": str(ident)}):
        r = _run_wrapper(wrapper_box, wrapper_box.env(**extra), *cmd)
        assert r.returncode == 0
        assert r.stdout == "".join(f"<{a}>" for a in hostile)
    assert _infisical_calls(wrapper_box) == [_expected_argv(wrapper_box, *cmd)]


def test_wrapper_never_prints_a_value():
    code = [ln for ln in WRAPPER.read_text().splitlines() if not ln.lstrip().startswith("#")]
    for ln in code:
        assert not re.search(r"\b(echo|printf)\b[^\n]*ORG_DB_URL", ln), ln
        assert "set -x" not in ln and "xtrace" not in ln


# ------------------------------------------------------------------ 2. drop-ins

def _dropin(unit: str) -> Path:
    return SYSTEMD / f"{unit}.service.d" / "org-db.conf"


def _body(unit: str) -> list[str]:
    """Non-comment, non-blank lines of the drop-in."""
    return [ln for ln in _dropin(unit).read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


AGENTS = "/opt/MoonieXHQ/Agents/Core"
VENV_PY = f"{AGENTS}/.venv/bin/python"
FETCH = f"/usr/bin/python3 {AGENTS}/tools/infisical_setup.py run Agents-Core prod --as contabo --"
SETPRIV = "/usr/bin/setpriv --reuid=secretary --regid=secretary --init-groups --"

EXPECTED_BODY = {
    "mooniex-watchdog": [
        "[Service]",
        "ExecStart=",
        f"ExecStart={FETCH} {VENV_PY} -m runners.watchdog --loop",
    ],
    "mooniex-secretary": [
        "[Service]",
        "Environment=HOME=/home/secretary",
        "ExecStart=",
        f"ExecStart=+{FETCH} {SETPRIV} {VENV_PY} {AGENTS}/runners/secretary_server.py",
    ],
    "mooniex-secretary-waker": [
        "[Service]",
        "Environment=HOME=/home/secretary",
        "ExecStart=",
        f"ExecStart=+{FETCH} {SETPRIV} {VENV_PY} -m runners.secretary_waker",
    ],
}


@pytest.mark.parametrize("unit", UNITS)
def test_dropin_body_is_exactly_the_designed_lines(unit):
    assert _body(unit) == EXPECTED_BODY[unit]


@pytest.mark.parametrize("unit", UNITS)
def test_dropin_clears_execstart_before_setting_it(unit):
    starts = [ln for ln in _body(unit) if ln.startswith("ExecStart")]
    assert len(starts) == 2 and starts[0] == "ExecStart=" and starts[1] != "ExecStart="


@pytest.mark.parametrize("unit", UNITS)
def test_dropin_plus_prefix_only_on_the_secretary_units(unit):
    plus = [ln for ln in _body(unit) if ln.startswith("ExecStart=+")]
    assert len(plus) == (1 if unit in SECRETARY_UNITS else 0)
    # `+` only ever as the prefix of ExecStart, nowhere inside a command
    for ln in _body(unit):
        assert "+" not in (ln[len("ExecStart=+"):] if ln.startswith("ExecStart=+") else ln)


@pytest.mark.parametrize("unit", UNITS)
def test_dropin_has_no_environmentfile_line(unit):
    """The secretary units' own EnvironmentFile= lines hold other secrets: not cleared, not extended."""
    text = _dropin(unit).read_text()
    assert not re.search(r"^\s*EnvironmentFile\s*=", text, re.MULTILINE)
    assert not re.search(r"^\s*Environment\s*=.*\.env", text, re.MULTILINE)


@pytest.mark.parametrize("unit", UNITS)
def test_dropin_holds_nothing_secret_looking(unit):
    text = _dropin(unit).read_text()
    assert SENTINEL not in text
    assert "://" not in text                                   # no URL, so no URL with a password
    for ln in _body(unit):                                     # comments may say "Secrets" (the rule's name)
        assert not re.search(r"pass(word|wd)|secret(?!ary)|token|api[_-]?key|bearer|credential", ln, re.I), ln
        for tok in ln.split():
            if "/" not in tok:                                 # paths are named, not secrets
                assert not (len(tok) >= 24 and re.search(r"[A-Za-z]", tok) and re.search(r"\d", tok)), tok


@pytest.mark.parametrize("unit", UNITS)
def test_dropin_says_why_names_the_design_doc_and_the_rollback(unit):
    text = _dropin(unit).read_text()
    head = [ln for ln in text.splitlines() if ln.startswith("#")]
    assert any(ln.startswith("# Why:") for ln in head)
    assert DESIGN in text and (ROOT / DESIGN).is_file()
    assert re.search(r"^# Rollback: rm /etc/systemd/system/" + re.escape(unit)
                     + r"\.service\.d/org-db\.conf", text, re.MULTILINE)
    assert "daemon-reload" in text and f"systemctl restart {unit}" in text


def test_only_the_three_dropins_exist():
    found = sorted(str(p.relative_to(SYSTEMD)) for p in SYSTEMD.rglob("*.conf"))
    assert found == sorted(f"{u}.service.d/org-db.conf" for u in UNITS)


def test_watchdog_dropin_runs_the_same_command_as_the_unit_it_extends():
    base = (SYSTEMD / "mooniex-watchdog.service").read_text()
    exec_line = re.search(r"^ExecStart=(.+)$", base, re.MULTILINE).group(1)
    assert EXPECTED_BODY["mooniex-watchdog"][-1].endswith(f"-- {exec_line}")
    assert "User=root" in base                                 # the identity file is root-only


@pytest.mark.parametrize("unit", UNITS)
def test_dropin_execstart_survives_infisical_setup_argument_parsing(unit, monkeypatch):
    """The real tools/infisical_setup.py main() splits at the FIRST `--`; the secretary lines carry a
    second one (before setpriv's program). Feed the drop-in's own ExecStart to the real parser."""
    import shlex

    sys.path.insert(0, str(ROOT))
    import tools.infisical_setup as inf

    line = _body(unit)[-1].split("=", 1)[1].removeprefix("+")
    argv = shlex.split(line)
    assert argv[:2] == ["/usr/bin/python3", f"{AGENTS}/tools/infisical_setup.py"]
    seen: dict = {}
    monkeypatch.setattr(inf, "cmd_run", lambda identity, project, env, command, path="/":
                        seen.update(identity=identity, project=project, env=env, command=command, path=path))

    inf.main(argv[2:])

    assert (seen["identity"], seen["project"], seen["env"], seen["path"]) == \
        ("contabo", "Agents-Core", "prod", "/")
    assert seen["command"] == argv[argv.index("--") + 1:]
    assert seen["command"][0] == ("/usr/bin/setpriv" if unit in SECRETARY_UNITS else VENV_PY)
    if unit in SECRETARY_UNITS:
        assert seen["command"].count("--") == 1 and seen["command"][-1] != "--"


@pytest.mark.skipif(not BLUEPRINT.is_dir(), reason="state/contabo-blueprint-20260924 not in this checkout")
@pytest.mark.parametrize("unit, target", [
    ("mooniex-secretary", f"{AGENTS}/runners/secretary_server.py"),
    ("mooniex-secretary-waker", "-m runners.secretary_waker"),
])
def test_secretary_dropins_match_the_09_24_unit_copies(unit, target):
    """Same script, same working directory, same user as the units they extend (copy from
    `systemctl cat`, state/contabo-blueprint-20260924); only the interpreter and the wrapping change."""
    base = (BLUEPRINT / f"{unit}.service").read_text()
    assert "User=secretary" in base
    assert f"WorkingDirectory={AGENTS}" in base
    assert base.count("EnvironmentFile=") == 2
    assert re.search(rf"^ExecStart=\S+ {re.escape(target)}$", base, re.MULTILINE)
    assert EXPECTED_BODY[unit][-1].endswith(target)


# ------------------------------------------------ 3. contabo-cutover-remote.sh

def _git(cwd: Path, *args: str) -> None:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stdout}{r.stderr}"


@pytest.fixture
def box(tmp_path):
    """A throwaway Contabo: bare origin + `work` clone as ROOT, fake .venv, fake systemd dir,
    fake node file dir, fake tools first on PATH, and a byte-checked stand-in for org-db.env."""
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "Test")
    for unit in UNITS:  # the real tracked drop-ins, so the real script installs the real files
        dst = work / "deploy" / "systemd" / f"{unit}.service.d" / "org-db.conf"
        dst.parent.mkdir(parents=True)
        shutil.copy2(_dropin(unit), dst)
    for rel in ("scripts/hub/cutover_flip.py", "scripts/lib/cxo_mcp_config.py",
                "scripts/hub/wal-checkpoint-archive.sh"):
        (work / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, work / rel)
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "init")
    _git(work, "push", "-q", "origin", "main")

    fakebin = _make_fakebin(tmp_path)
    log = tmp_path / "calls.jsonl"
    for name in ("python", "pip"):  # untracked: the script's dirty check ignores '??'
        p = work / ".venv" / "bin" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_FAKE_VENV_TOOL.replace("@PY@", sys.executable).replace("@NAME@", f"venv-{name}"))
        p.chmod(0o755)

    systemd = tmp_path / "etc-systemd-system"
    node = tmp_path / "cfg" / "node.yaml"
    node.parent.mkdir()
    node.write_text("host: contabo\n")
    # Contabo's real org-db.env holds POSTGRES_* only. It sits at the path a careless script
    # would append to (HOME's), and must come out byte-identical.
    envfile = tmp_path / "home" / ".config" / "mooniex" / "org-db.env"
    envfile.parent.mkdir(parents=True)
    envfile.write_bytes(b"POSTGRES_USER=u\nPOSTGRES_PASSWORD=pw-not-a-url\nPOSTGRES_DB=org\n")

    return SimpleNamespace(
        tmp=tmp_path, work=work, systemd=systemd, node=node, envfile=envfile, log=log,
        env=lambda **extra: _env(tmp_path, fakebin, log, **{
            "ROOT": str(work), "SYSTEMD_DIR": str(systemd), "NODE_YAML": str(node),
            "FLAG": "--sessions-closed", "RESTART_SETTLE_S": "0", **extra}),
    )


def _run_remote(box, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(REMOTE)], env=box.env(**extra), capture_output=True,
                          text=True, timeout=60)


def _make_tasks_db(work: Path, *statuses: str) -> None:
    """state/tasks.db with one row per status (default: one finished task). Step 5 counts
    the live statuses in it (W1.9 F3), so the table carries a status column."""
    (work / "state").mkdir(exist_ok=True)
    rows = "".join(f"INSERT INTO tasks VALUES ({i}, '{st}');" for i, st in enumerate(statuses or ("done",), 1))
    subprocess.run(["sqlite3", str(work / "state" / "tasks.db"),
                    f"PRAGMA journal_mode=WAL; CREATE TABLE tasks (id INTEGER, status TEXT); {rows}"],
                   check=True, capture_output=True)


def _tools(box) -> list[str]:
    """One label per logged call, in order."""
    out = []
    for c in _read_log(box.log):
        a = c["argv"]
        if c["tool"] == "python3" and a and a[0].endswith("/tools/infisical_setup.py"):
            out.append("infisical:" + " ".join(a[a.index("--") + 1:][:2]))
        elif c["tool"] == "python3":
            out.append("python3:" + (a[0] if a else ""))
        elif c["tool"] == "systemctl":
            out.append("systemctl:" + " ".join(a))
        else:
            out.append(f"{c['tool']}:" + " ".join(a[:2]))
    return out


def _no_dropins_installed(box) -> bool:
    return not box.systemd.exists() or not list(box.systemd.rglob("*"))


def test_step4_dry_path_refuses_when_infisical_cannot_reach_the_hub_and_changes_nothing(box):
    node_before, env_before = box.node.read_bytes(), box.envfile.read_bytes()

    r = _run_remote(box, FAKE_INFISICAL_FAIL="1")

    assert r.returncode != 0
    assert "REFUSING: Agents-Core/prod ORG_DB_URL is missing or the hub is not reachable" in r.stdout
    assert "== step 5:" not in r.stdout
    assert _no_dropins_installed(box)
    assert box.node.read_bytes() == node_before and box.envfile.read_bytes() == env_before
    assert not any(t.startswith("systemctl:daemon-reload") or t.startswith("systemctl:restart")
                   for t in _tools(box))
    assert SENTINEL not in r.stdout + r.stderr


def test_step4_verifies_with_infisical_run_as_contabo_before_writing_anything(box):
    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr

    first = next(c for c in _read_log(box.log)
                 if c["tool"] == "python3" and c["argv"][0].endswith("/tools/infisical_setup.py"))
    a = first["argv"]
    assert a[:6] == [f"{box.work}/tools/infisical_setup.py", "run", "Agents-Core", "prod", "--as", "contabo"]
    assert a[6:9] == ["--", ".venv/bin/python", "-c"]
    # the connect snippet: needs the URL in the env, connects, prints no value
    assert 'os.environ.get("ORG_DB_URL"' in a[9] and "psycopg.connect(url" in a[9]
    assert not re.search(r"print\([^)]*url", a[9])
    # and it ran before the first drop-in was copied or the node file touched
    tools = _tools(box)
    connect = next(t for t in tools if t.startswith("infisical:.venv/bin/python -c"))
    assert tools.index(connect) < tools.index("systemctl:daemon-reload")


@pytest.mark.parametrize("what", ["source", "unit"])
def test_step4_refuses_before_any_write_on_a_missing_source_or_unit(box, what):
    extra = {}
    if what == "source":
        (box.work / "deploy" / "systemd" / "mooniex-secretary-waker.service.d" / "org-db.conf").unlink()
        _git(box.work, "commit", "-aq", "-m", "drop a drop-in")
        _git(box.work, "push", "-q", "origin", "main")
    else:
        extra["FAKE_MISSING_UNIT"] = "mooniex-secretary"

    r = _run_remote(box, **extra)

    assert r.returncode != 0 and "REFUSING:" in r.stdout
    assert _no_dropins_installed(box)
    assert box.node.read_bytes() == b"host: contabo\n"
    assert not any(t.startswith("infisical:") for t in _tools(box))  # refused before the network check


def test_step8_installs_the_three_dropins_byte_for_byte_and_reloads(box):
    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr

    for unit in UNITS:
        installed = box.systemd / f"{unit}.service.d" / "org-db.conf"
        assert installed.read_bytes() == _dropin(unit).read_bytes()
        assert stat.S_IMODE(installed.stat().st_mode) == 0o644
    tools = _tools(box)
    assert tools.count("systemctl:daemon-reload") == 1
    assert [t for t in tools if t.startswith("systemctl:cat")] == \
        [f"systemctl:cat {u}.service" for u in UNITS]


def test_node_yaml_is_written_after_the_migration_and_before_the_restarts(box):
    """Fails if the write sits in step 4: a session spawned between step 4 and the migration would
    open the hub while it is empty. Every call before step 8 must see a node file without the switch."""
    _make_tasks_db(box.work)

    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr

    before_switch, restarts = [], []
    for c in _read_log(box.log):
        if c["tool"] == "systemctl" and c["argv"][:1] == ["restart"]:
            restarts.append(c)
        elif c["tool"] in ("venv-python", "venv-pip"):
            before_switch.append(c)
    kinds = [c["argv"][0] if c["argv"] else "" for c in before_switch]
    assert any(k.endswith("migrate_tasks_db.py") for k in kinds)
    assert any(k.endswith("verify_migration_counts.py") for k in kinds)
    assert "-" in kinds                                         # step 7's read-back
    reloads = [c for c in _read_log(box.log) if c["tool"] == "systemctl" and c["argv"][:1] == ["daemon-reload"]]
    assert len(reloads) == 1 and reloads[0]["node_hub"] is True, "the reload is step 8's, after the node write (W1.9 F2)"
    assert all(c["node_hub"] is False for c in before_switch), \
        [(c["argv"][:1], c["node_hub"]) for c in before_switch if c["node_hub"]]
    assert len(restarts) == 3 and all(c["node_hub"] is True for c in restarts)
    assert r.stdout.index("== step 7:") < r.stdout.index("wrote org_db: hub") < r.stdout.index("active: mooniex-watchdog")


def test_a_failed_migration_never_writes_the_node_file_or_restarts_a_unit(box):
    _make_tasks_db(box.work)
    before = box.node.read_bytes()

    r = _run_remote(box, FAKE_MIGRATE_FAIL="1")

    assert r.returncode != 0
    assert box.node.read_bytes() == before
    assert not any(t.startswith("systemctl:restart") for t in _tools(box))
    assert (box.work / "state" / "tasks.db").is_file(), "no tombstone before a successful migration"
    assert "org_db: hub" not in r.stdout


def test_step8_node_yaml_write_is_idempotent_and_keeps_every_other_line(box):
    box.node.write_text("# node\nhost: contabo\norg_db: sqlite\nhq_root: /x\n")

    assert _run_remote(box).returncode == 0
    once = box.node.read_bytes()
    assert once == b"# node\nhost: contabo\norg_db: hub\nhq_root: /x\n"

    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr
    assert box.node.read_bytes() == once
    assert "already says org_db: hub" in r.stdout
    for unit in UNITS:  # a second run re-installs identical bytes
        assert (box.systemd / f"{unit}.service.d" / "org-db.conf").read_bytes() == _dropin(unit).read_bytes()


def test_step8_creates_a_missing_node_file_holding_only_the_switch(box):
    box.node.unlink()
    box.node.parent.rmdir()

    assert _run_remote(box).returncode == 0
    assert box.node.read_text() == "org_db: hub\n"


def test_step8_the_written_line_is_the_one_the_generators_read(box, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    import cxo_mcp_config as cxo

    monkeypatch.setenv("MOONIEX_NODE_YAML", str(box.node))
    assert cxo.hub_is_live() is False
    assert _run_remote(box).returncode == 0
    assert cxo.hub_is_live() is True


def test_step4_appends_nothing_to_any_env_file_and_prints_no_value(box):
    env_before = box.envfile.read_bytes()

    r = _run_remote(box)

    assert r.returncode == 0, r.stdout + r.stderr
    assert box.envfile.read_bytes() == env_before
    assert SENTINEL not in r.stdout + r.stderr
    assert SENTINEL not in box.log.read_text()
    code = [ln for ln in REMOTE.read_text().splitlines() if not ln.lstrip().startswith("#")]
    for ln in code:
        assert "ORG_TEST_DB_URL" not in ln, ln
        assert not re.search(r">>?\s*\"?\$\{?ENVF|\bsource\s|^\s*\.\s+\"?\$\{?ENVF|org-db\.env", ln), ln


def test_later_steps_get_org_db_url_only_through_infisical_run(box):
    _make_tasks_db(box.work)

    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr

    venv = [c for c in _read_log(box.log) if c["tool"] == "venv-python"]
    with_url = [c["argv"] for c in venv if c["org_db_url"]]
    without = [c["argv"] for c in venv if not c["org_db_url"]]
    assert any(a[0].endswith("migrate_tasks_db.py") and a[a.index("--to") + 1] == "<url>"
               and a[a.index("--default-host") + 1] == "contabo" and "--append-events" in a
               for a in with_url)
    assert any(a[0].endswith("verify_migration_counts.py") and a[a.index("--pg") + 1] == "<url>"
               and a[a.index("--mode") + 1] == "subset" for a in with_url)
    assert ["-"] in with_url        # step 7's read-back through lib.db
    assert any(a[:1] == ["-c"] and "psycopg.connect" in a[1] for a in with_url)  # step 4's connect check
    # the only python run without the URL is step 3's import probe
    assert without == [["-c", "import psycopg; print('psycopg', psycopg.__version__)"]]
    assert SENTINEL not in r.stdout + r.stderr + box.log.read_text()


def test_restart_comes_last_after_the_migration_and_the_tombstone(box):
    _make_tasks_db(box.work)

    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr

    assert (box.work / "state" / "tasks.db").is_dir(), "tombstone directory expected"
    calls = _read_log(box.log)
    labels = []
    for c in calls:
        a = c["argv"]
        if c["tool"] == "venv-python" and a and a[0].endswith("migrate_tasks_db.py"):
            labels.append("migrate")
        elif c["tool"] == "venv-python" and a and a[0].endswith("verify_migration_counts.py"):
            labels.append("verify-counts")
        elif c["tool"] == "systemctl" and a[:1] == ["daemon-reload"]:
            labels.append("daemon-reload")
        elif c["tool"] == "systemctl" and a[:1] == ["stop"]:
            labels.append("stop:" + a[1].removesuffix(".service"))
        elif c["tool"] == "systemctl" and a[:1] == ["restart"]:
            labels.append("restart:" + a[1].removesuffix(".service"))
            assert c["tombstone"] is True, "a unit was restarted before state/tasks.db was tombstoned"
    assert labels == [*[f"stop:{u}" for u in UNITS], "migrate", "verify-counts", "daemon-reload",
                      *[f"restart:{u}" for u in UNITS]]
    checks = [c["argv"] for c in calls if c["tool"] == "systemctl" and c["argv"][:1] == ["is-active"]]
    assert checks == [["is-active", "--quiet", f"{u}.service"] for u in UNITS]
    assert "== step 8:" in r.stdout and "active: mooniex-watchdog" in r.stdout


def test_a_unit_that_is_not_active_after_the_restart_fails_the_cutover(box):
    r = _run_remote(box, FAKE_INACTIVE_UNIT="mooniex-secretary")

    assert r.returncode != 0
    assert "NOT ACTIVE: mooniex-secretary" in r.stdout
    assert "REFUSING to call this done" in r.stdout
    assert "== done." not in r.stdout


def _assert_rollback_names_the_switch_line(node: Path, out: str) -> None:
    """The rollback printed on a step 8 failure: drop-ins, the org_db: line, reload, restart."""
    tail = out[out.index("Rollback"):]
    assert "org-db.conf" in tail and "mooniex-secretary-waker" in tail
    assert f"remove the org_db: line from {node}" in tail
    assert "cutover_flip.py --rollback --apply" in tail
    assert "daemon-reload" in tail and "restart the three units" in tail


def test_step8_failure_after_the_node_write_still_prints_the_org_db_line_rollback(box):
    r = _run_remote(box, FAKE_INACTIVE_UNIT="mooniex-secretary")

    assert r.returncode != 0
    assert "org_db: hub" in box.node.read_text(), "the scenario: the switch was written, then a unit failed"
    _assert_rollback_names_the_switch_line(box.node, r.stdout)
    assert "== done." not in r.stdout


def test_step8_restart_command_failure_is_reported_and_prints_the_rollback(box):
    r = _run_remote(box, FAKE_RESTART_FAIL_UNIT="mooniex-secretary")

    assert r.returncode != 0
    assert "RESTART FAILED: mooniex-secretary" in r.stdout
    restarts = [t for t in _tools(box) if t.startswith("systemctl:restart")]
    assert restarts == [f"systemctl:restart {u}.service" for u in UNITS]   # the others were still tried
    checked = [c["argv"][-1] for c in _read_log(box.log) if c["argv"][:1] == ["is-active"]]
    assert "mooniex-secretary.service" not in checked                       # a failed restart is not re-judged
    _assert_rollback_names_the_switch_line(box.node, r.stdout)
    assert "== done." not in r.stdout


def test_step8_node_file_write_failure_restarts_nothing_and_prints_the_rollback(box):
    blocker = box.tmp / "a-file"
    blocker.write_text("not a directory\n")
    node = blocker / "node.yaml"                                # its parent is a file: the write cannot succeed

    r = _run_remote(box, NODE_YAML=str(node))

    assert r.returncode != 0
    assert "could not write org_db: hub" in r.stdout and "No unit was restarted" in r.stdout
    assert not any(t.startswith("systemctl:restart") for t in _tools(box))
    _assert_rollback_names_the_switch_line(node, r.stdout)


def test_the_full_run_on_the_throwaway_root_prints_every_step_in_order(box):
    _make_tasks_db(box.work)

    r = _run_remote(box)

    assert r.returncode == 0, r.stdout + r.stderr
    steps = re.findall(r"^== step (\d+b?):", r.stdout, re.MULTILINE)
    assert steps == ["1", "2", "3", "4", "5", "5b", "6", "7", "8"]
    assert "== done." in r.stdout


# ----------------------------------------------------------- shell syntax + text

@pytest.mark.parametrize("script", [WRAPPER, REMOTE, CUTOVER])
def test_bash_syntax_ok(script):
    r = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_both_cutover_scripts_carry_the_dropin_and_switch_rollback():
    for script in (REMOTE, CUTOVER):
        text = script.read_text()
        assert "org-db.conf" in text and "cutover_flip.py" in text and "--rollback" in text, script.name
        assert "daemon-reload" in text and "systemctl restart" in text, script.name
    # the two ORG_*_URL lines are gone from the rollback: nothing is appended to org-db.env any more
    assert "delete the two ORG_*_URL lines" not in CUTOVER.read_text()


def test_the_switch_write_is_in_step_8_before_the_first_restart_and_not_in_step_4():
    text = REMOTE.read_text()
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    step4 = code.split('echo "== step 4:')[1].split('echo "== step 5:')[0]
    step8 = code.split('echo "== step 8:')[1]
    assert "set_org_db" not in step4 and "org_db: hub" not in step4
    assert step8.index("set_org_db") < step8.index("systemctl restart")
    header = CUTOVER.read_text()                                # the header says the same
    h4 = header.split("#   4.")[1].split("#   5.")[0]
    h8 = header.split("#   8.")[1].split("# Rollback:")[0]
    assert "org_db: hub" not in h4 and "not touched here (step 8)" in h4
    assert "node.yaml" in h8 and "org_db: hub" in h8 and "`org_db:` line" in h8
