"""Org Mesh W2.8 (docs/ops/node-dispatch.md, "No ssh config"): a mesh call dials
the host's `mesh_ssh` (user@tailnet address) with `ssh -F none`, so no ssh
config file, no admin alias and no admin key is ever part of it.

Fakes only: subprocess.run is a recorder or a tripwire, and config.host is
replaced where a test needs a host shape hosts.yaml does not have.

Run:  .venv/bin/python -m pytest tests/test_w28_mesh_destination.py
"""
from __future__ import annotations

import ipaddress
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, mesh  # noqa: E402

TAILNET = ipaddress.ip_network("100.64.0.0/10")
DECLARED = yaml.safe_load(config.HOSTS_CONFIG.read_text(encoding="utf-8"))["hosts"]


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))  # the org_dispatch key path expands from it
    monkeypatch.setenv("ORG_HOST", "mac")
    config.self_host.cache_clear()
    yield
    config.self_host.cache_clear()


def _tripwire(monkeypatch):
    def run(*a, **kw):
        raise AssertionError(f"nothing may be dialled: {a}")
    monkeypatch.setattr(subprocess, "run", run)


def _testbox(monkeypatch, **entry):
    """config.host('testbox') answers `entry`; every other name is real."""
    real = config.host
    monkeypatch.setattr(config, "host", lambda name: entry if name == "testbox" else real(name))


@pytest.mark.parametrize("host", ["contabo", "winbox"])
def test_a_remote_call_reads_no_ssh_config_and_dials_mesh_ssh(host):
    cfg = config.host(host)
    argv = mesh.build_argv(host, "probe", ())
    assert argv[:3] == ["ssh", "-F", "none"]
    assert argv[-2:] == [cfg["mesh_ssh"], "probe"]
    assert cfg["ssh"] not in argv  # the admin alias is never part of a mesh call


def test_the_dispatch_key_is_the_only_identity(tmp_path):
    argv = mesh.build_argv("contabo", "probe", ())
    keys = [argv[i + 1] for i, a in enumerate(argv) if a == "-i"]
    assert keys == [str(tmp_path / ".ssh" / "org_dispatch")]
    opts = [argv[i + 1] for i, a in enumerate(argv) if a == "-o"]
    assert "IdentitiesOnly=yes" in opts and "IdentityAgent=none" in opts
    assert not [o for o in opts if o.split("=")[0].lower() in
                ("identityfile", "proxycommand", "proxyjump", "localcommand")]


@pytest.mark.parametrize("host", sorted(DECLARED))
def test_every_declared_mesh_ssh_is_a_user_at_a_tailnet_address(host):
    """from= on the far side pins the dispatcher's tailnet address, so a mesh
    destination outside the tailnet could never be answered (the admin alias
    for Contabo dials its public address)."""
    entry = DECLARED[host]
    assert "mesh_ssh" in entry, f"{host}: say mesh_ssh: null when it takes no mesh calls"
    dest = entry["mesh_ssh"]
    if dest is None:
        return
    user, _, addr = dest.partition("@")
    assert user and ipaddress.ip_address(addr) in TAILNET, dest
    assert dest != entry.get("ssh")


def test_the_mac_takes_no_mesh_calls_until_its_sshd_opens(monkeypatch):
    """G2 (Remote Login + sshd hardening) is the CEO's step at the very end."""
    assert DECLARED["mac"]["mesh_ssh"] is None
    monkeypatch.setenv("ORG_HOST", "contabo")
    config.self_host.cache_clear()
    _tripwire(monkeypatch)
    with pytest.raises(mesh.MeshUnreachable, match="no mesh_ssh"):
        mesh.dispatch("mac", "probe")


@pytest.mark.parametrize("value", [None, ""])
def test_no_mesh_ssh_dials_nothing(monkeypatch, value):
    _testbox(monkeypatch, ssh="testbox-admin", mesh_ssh=value)
    _tripwire(monkeypatch)
    with pytest.raises(mesh.MeshUnreachable, match="no mesh_ssh"):
        mesh.dispatch("testbox", "probe")


def test_a_host_without_the_key_at_all_dials_nothing(monkeypatch):
    """A joined node's entry (tools/hq_join, config._node_entry) has no mesh_ssh."""
    _testbox(monkeypatch, ssh="testbox")
    _tripwire(monkeypatch)
    with pytest.raises(mesh.MeshUnreachable, match="no mesh_ssh"):
        mesh.dispatch("testbox", "probe")


@pytest.mark.parametrize("value", [
    "mooniex-vps",                      # an alias: with -F none it would go to DNS
    "contabo-mesh",
    "-oProxyCommand=sh@x",              # would be read as an ssh option
    "root@-oProxyCommand=sh",
    "root@100.118.171.23 id",
    "root@100.118.171.23;id",
    "root@100.118.171.23\n",
    "root@",
    "@100.118.171.23",
    "ro ot@100.118.171.23",
    "root@100.118.171.23:2222",
    42,
    ["root@100.118.171.23"],
])
def test_a_malformed_mesh_ssh_is_refused_before_ssh(monkeypatch, value):
    _testbox(monkeypatch, ssh="testbox-admin", mesh_ssh=value)
    _tripwire(monkeypatch)
    with pytest.raises(mesh.MeshUnreachable, match="not user@address"):
        mesh.dispatch("testbox", "probe")


@pytest.mark.parametrize("value", [
    "root@100.118.171.23", "passg@100.124.196.11", "gob@mac.tail1234.ts.net", "UsEr@100.64.0.1"])
def test_a_plain_user_at_address_is_dialled_as_given(monkeypatch, value):
    _testbox(monkeypatch, ssh="testbox-admin", mesh_ssh=value)
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"ok": true, "verb": "probe"}\n', "")

    monkeypatch.setattr(subprocess, "run", run)
    assert mesh.dispatch("testbox", "probe")["ok"] is True
    (argv,) = calls
    assert argv[:3] == ["ssh", "-F", "none"] and argv[-2:] == [value, "probe"]
    assert "testbox-admin" not in argv


def test_a_bad_verb_is_still_refused_before_the_destination_is_read(monkeypatch):
    _testbox(monkeypatch, ssh="testbox-admin", mesh_ssh=None)
    _tripwire(monkeypatch)
    reply = mesh.dispatch("testbox", "bash", "-c", "id")
    assert reply["ok"] is False and "unknown verb" in reply["error"]


# ---------------------------------------------------------------------------
# The far side: the forced command must reach the hub (G1). sshd starts it
# with a bare environment, and state/tasks.db is a tombstone since the cutover.
# ---------------------------------------------------------------------------

DOC = ROOT / "docs" / "ops" / "node-dispatch.md"
WRAPPER = ROOT / "scripts" / "hub" / "with-org-db-env.sh"


def _doc_key_lines() -> list[str]:
    return [ln.strip() for ln in DOC.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("command=") and "ssh-ed25519" in ln]


def test_every_posix_forced_command_starts_node_dispatch_through_the_hub_env_wrapper():
    posix = [ln for ln in _doc_key_lines() if "C:\\" not in ln]
    assert posix
    for ln in posix:
        command = ln.split('",', 1)[0]
        assert "exec /bin/bash scripts/hub/with-org-db-env.sh " in command, ln
        # the wrapper starts python; python never starts first
        assert command.index("with-org-db-env.sh") < command.index("python"), ln


def test_the_winbox_forced_command_reaches_the_hub_through_its_org_node_identity():
    (win,) = [ln for ln in _doc_key_lines() if "C:\\" in ln]
    command = win.split('",', 1)[0]
    checkout = "C:\\Users\\passg\\mooniex\\repo\\MoonieX-Agents"
    projects = yaml.safe_load((ROOT / "config" / "projects.yaml").read_text(encoding="utf-8"))
    paths = [p.get("paths", {}).get("winbox") for p in projects["projects"]]
    assert checkout in paths  # the line names the real checkout, not agents_root
    assert f"{checkout}\\tools\\infisical_setup.py run Org-Node prod --as winbox -- " in command
    assert command.endswith(f"{checkout}\\tools\\node_dispatch.py")


def test_the_wrapper_never_reads_the_callers_text():
    assert "SSH_ORIGINAL_COMMAND" not in WRAPPER.read_text(encoding="utf-8")


def test_the_wrapper_hands_the_callers_text_through_with_the_hub_url(tmp_path):
    env_file = tmp_path / "org-db.env"
    env_file.write_text("ORG_DB_URL=postgresql://org@hub.invalid:5432/org\n", encoding="utf-8")
    probe = "import os; print(os.environ['SSH_ORIGINAL_COMMAND']); print('ORG_DB_URL' in os.environ)"
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "MOONIEX_ORG_DB_ENV": str(env_file),
           "SSH_ORIGINAL_COMMAND": "probe; id"}
    r = subprocess.run(["/bin/bash", str(WRAPPER), sys.executable, "-E", "-s", "-c", probe],
                       env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["probe; id", "True"]  # passed on as data, never run
    assert "uid=" not in r.stdout + r.stderr
