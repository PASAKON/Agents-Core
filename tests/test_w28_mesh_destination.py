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
