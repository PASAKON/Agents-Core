"""Org Mesh W4.5: the join endpoint behind traefik.

Files only, nothing live: the --bind allowlist of tools/join_api.py, the compose file that
carries the traefik labels, the systemd unit, and deploy/join/bind-docker0.sh run against a
fake `ip`. No docker, traefik, systemd, network or database is touched.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w45_bind.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tools import join_api

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "deploy" / "join" / "docker-compose.join-proxy.yml"
UNIT = ROOT / "deploy" / "join" / "org-join.service"
WRAPPER = ROOT / "deploy" / "join" / "bind-docker0.sh"

# The six labels, nothing more: enable, the four router settings, the service port.
SIX_LABELS = {
    "traefik.enable": "true",
    "traefik.http.routers.org-join.rule": "Host(`webhook.mooniex.com`) && PathPrefix(`/org-join`)",
    "traefik.http.routers.org-join.entrypoints": "websecure",
    "traefik.http.routers.org-join.tls": "true",
    "traefik.http.routers.org-join.tls.certresolver": "mytlschallenge",
    "traefik.http.services.org-join.loadbalancer.server.port": "8080",
}


# ---------------------------------------------------------------- the bind allowlist

@pytest.mark.parametrize("addr", ["127.0.0.1", "127.0.0.2", "172.17.0.1", "172.16.0.1", "172.31.255.254"])
def test_check_bind_accepts_loopback_and_docker_bridges(addr):
    assert join_api.check_bind(addr) == addr


@pytest.mark.parametrize("addr", [
    "0.0.0.0",            # every interface
    "::",                 # every interface, IPv6
    "::1",                # loopback, but this server is AF_INET
    "::ffff:127.0.0.1",   # IPv4-mapped IPv6
    "172.32.0.1",         # one past 172.16.0.0/12
    "172.15.255.255",     # one before it
    "10.0.0.1",
    "192.168.1.10",
    "100.64.2.37",        # tailnet
    "194.233.80.26",      # Contabo's public address
    "8.8.8.8",
    "localhost",          # a name is not an address
    "",
    " 172.17.0.1",
    "172.17.0.1/16",
    "172.17.0.1:8791",
])
def test_check_bind_refuses_everything_else(addr):
    with pytest.raises(ValueError):
        join_api.check_bind(addr)


def test_the_default_bind_is_loopback():
    assert join_api.BIND_HOST == "127.0.0.1"
    assert join_api.check_bind(join_api.BIND_HOST)


@pytest.mark.parametrize("addr", ["0.0.0.0", "::", "10.0.0.1", "172.32.0.1", "194.233.80.26"])
def test_the_server_itself_refuses_a_bad_bind_before_any_socket(addr):
    with pytest.raises(ValueError):
        join_api.JoinServer(0, bind=addr)


def test_the_server_binds_loopback_unless_told_otherwise():
    srv = join_api.JoinServer(0)
    try:
        assert srv.server_address[0] == "127.0.0.1"
    finally:
        srv.server_close()


class _FakeServer:
    """What main() needs from a JoinServer, without a socket or a database."""
    server_address = ("127.0.0.1", 0)
    minter = None

    def serve_forever(self):
        raise KeyboardInterrupt

    def server_close(self):
        pass


@pytest.fixture
def started(monkeypatch):
    """main() with the database check and the listener replaced; records make_server's kwargs."""
    calls = []
    monkeypatch.setattr(join_api, "_preflight", lambda: None)
    monkeypatch.setattr(join_api, "make_server", lambda port, **kw: calls.append(kw) or _FakeServer())
    monkeypatch.delenv("JOIN_API_BIND", raising=False)
    return calls


def test_main_passes_bind_from_the_flag_and_from_the_env(started, monkeypatch):
    assert join_api.main(["--bind", "172.17.0.1"]) == 0
    monkeypatch.setenv("JOIN_API_BIND", "172.18.0.1")
    assert join_api.main([]) == 0
    assert join_api.main(["--bind", "127.0.0.1"]) == 0  # the flag beats the env
    assert [kw["bind"] for kw in started] == ["172.17.0.1", "172.18.0.1", "127.0.0.1"]


def test_main_defaults_to_loopback_with_no_flag_and_no_or_empty_env(started, monkeypatch):
    assert join_api.main([]) == 0
    monkeypatch.setenv("JOIN_API_BIND", "")
    assert join_api.main([]) == 0
    assert [kw["bind"] for kw in started] == ["127.0.0.1", "127.0.0.1"]


def _db_must_not_be_touched(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("the database or the listener was reached before the bind address was checked")
    monkeypatch.setattr(join_api, "_preflight", boom)
    monkeypatch.setattr(join_api, "make_server", boom)


@pytest.mark.parametrize("addr", ["0.0.0.0", "::", "10.0.0.1", "172.32.0.1", "194.233.80.26", "localhost"])
def test_main_exits_2_with_a_clear_message_before_the_database(addr, monkeypatch, capsys):
    _db_must_not_be_touched(monkeypatch)
    with pytest.raises(SystemExit) as e:
        join_api.main(["--bind", addr])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "join_api: error:" in err and ("refused" in err or "not an IPv4 address" in err)


def test_a_refused_bind_from_the_env_exits_2_too(monkeypatch, capsys):
    monkeypatch.setenv("JOIN_API_BIND", "0.0.0.0")
    _db_must_not_be_touched(monkeypatch)
    with pytest.raises(SystemExit) as e:
        join_api.main([])
    assert e.value.code == 2
    assert "0.0.0.0" in capsys.readouterr().err


# ---------------------------------------------------------------- the compose file

def _labels(service: dict) -> dict:
    labels = service["labels"]
    if isinstance(labels, list):
        return dict(item.split("=", 1) for item in labels)
    return {k: str(v) for k, v in labels.items()}


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def proxy(compose) -> dict:
    assert list(compose["services"]) == ["org-join-proxy"], "one container, nothing else"
    return compose["services"]["org-join-proxy"]


def test_the_compose_file_carries_exactly_the_six_labels(proxy):
    assert _labels(proxy) == SIX_LABELS


def test_the_compose_file_routes_nothing_but_org_join(proxy):
    for key in _labels(proxy):
        assert key == "traefik.enable" or ".org-join." in key, key


def test_the_compose_file_publishes_no_port_and_mounts_and_passes_nothing(compose, proxy):
    for key in ("ports", "volumes", "environment", "env_file", "secrets", "configs",
                "privileged", "network_mode", "pid", "ipc", "devices", "cap_add"):
        assert key not in proxy, key
    for key in ("volumes", "secrets", "configs"):
        assert key not in compose, key
    assert not re.search(r"^\s*-?\s*ports\s*:", COMPOSE.read_text(encoding="utf-8"), re.M)


def test_the_container_is_locked_down(proxy):
    assert proxy["read_only"] is True
    assert proxy["restart"] == "no"     # W4.6c: the door is closed by default, a reboot must not reopen it
    assert proxy["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in proxy["security_opt"]
    assert proxy["user"] not in ("0", "0:0", "root")
    assert re.fullmatch(r"\d+[mMgG]", str(proxy["mem_limit"]))
    assert int(proxy["pids_limit"]) > 0


def test_the_image_is_pinned(proxy):
    image = proxy["image"]
    assert ":" in image and not image.endswith(":latest"), image


def test_the_container_joins_traefiks_network_and_reaches_the_host_gateway(compose, proxy):
    assert proxy["networks"] == ["n8n_default"]
    assert compose["networks"] == {"n8n_default": {"external": True}}
    assert proxy["extra_hosts"] == ["host.docker.internal:host-gateway"]


def test_socat_listens_on_the_service_port_and_forwards_to_the_endpoint(proxy):
    listen, target = proxy["command"]
    port = SIX_LABELS["traefik.http.services.org-join.loadbalancer.server.port"]
    assert re.match(rf"TCP-LISTEN:{port}(,|$)", listen)
    assert target == f"TCP:host.docker.internal:{join_api.DEFAULT_PORT}"


# ---------------------------------------------------------------- the unit

def _unit_lines() -> list[str]:
    return UNIT.read_text(encoding="utf-8").splitlines()


def test_the_unit_carries_the_two_env_lines():
    lines = _unit_lines()
    assert "Environment=JOIN_API_PUBLIC_URL=https://webhook.mooniex.com" in lines
    assert "Environment=JOIN_API_TRUST_FORWARDED=1" in lines


def test_the_unit_carries_no_secret_value():
    env_names = sorted(ln.split("=", 2)[1] for ln in _unit_lines() if ln.startswith("Environment="))
    assert env_names == ["HOME", "JOIN_API_PUBLIC_URL", "JOIN_API_TRUST_FORWARDED", "PYTHONUNBUFFERED"]
    text = UNIT.read_text(encoding="utf-8")
    for pattern in (r"postgres(ql)?://", r"://[^/\s]*:[^/\s]*@", r"tskey-", r"AGE-SECRET-KEY-", r"ghp_",
                    r"github_pat_", r"sk-[A-Za-z0-9]{10}", r"eyJ[A-Za-z0-9_-]{10}", r"ORG_DB_URL\s*="):
        assert not re.search(pattern, text), pattern


def test_the_unit_resolves_docker0_first_then_fetches_secrets_then_drops_root():
    (exec_start,) = [ln for ln in _unit_lines() if ln.startswith("ExecStart=")]
    assert exec_start.startswith("ExecStart=/bin/sh /opt/MoonieXHQ/Agents/Core/deploy/join/bind-docker0.sh ")
    order = [exec_start.index(s) for s in (
        "bind-docker0.sh", "infisical_setup.py run Agents-Core prod --as contabo --path /org-join --",
        "setpriv --reuid=org-join", "-m tools.join_api --port 8791")]
    assert order == sorted(order)
    assert "--bind" not in exec_start and "0.0.0.0" not in exec_start


# ---------------------------------------------------------------- bind-docker0.sh

def test_the_wrapper_and_compose_are_ascii_only():
    for path in (WRAPPER, COMPOSE):
        assert not [b for b in path.read_bytes() if b > 127], path.name


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck is not installed")
def test_the_wrapper_is_shellcheck_clean():
    r = subprocess.run(["shellcheck", "-s", "sh", str(WRAPPER)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def _run_wrapper(path_dir: Path, env_extra: dict | None = None, command=("sh", "-c", 'echo "bind=$JOIN_API_BIND"')):
    env = {"PATH": f"{path_dir}:/usr/bin:/bin", **(env_extra or {})}
    return subprocess.run(["sh", str(WRAPPER), *command], capture_output=True, text=True, env=env, timeout=20)


@pytest.fixture
def fake_ip(tmp_path):
    """A directory first on PATH whose `ip` prints what `ip_out` holds; it only answers the exact
    call the wrapper is meant to make."""
    ip = tmp_path / "ip"
    ip.write_text('#!/bin/sh\n[ "$*" = "-4 -o addr show dev docker0" ] || exit 64\ncat "$(dirname "$0")/ip_out"\n')
    ip.chmod(0o755)

    def run(out: str, env_extra: dict | None = None):
        (tmp_path / "ip_out").write_text(out)
        return _run_wrapper(tmp_path, env_extra)
    return run


DOCKER0_LINE = ("4: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\\       "
                "valid_lft forever preferred_lft forever\n")


def test_the_wrapper_exports_the_docker0_address_and_execs_the_command(fake_ip):
    r = fake_ip(DOCKER0_LINE)
    assert (r.returncode, r.stdout.strip()) == (0, "bind=172.17.0.1"), r.stderr
    assert join_api.check_bind("172.17.0.1")


def test_the_wrapper_overrides_a_bind_it_inherited(fake_ip):
    r = fake_ip(DOCKER0_LINE, {"JOIN_API_BIND": "0.0.0.0"})
    assert r.stdout.strip() == "bind=172.17.0.1"


def test_the_wrapper_takes_the_first_address_when_docker0_has_two(fake_ip):
    r = fake_ip(DOCKER0_LINE + DOCKER0_LINE.replace("172.17.0.1", "172.17.0.9"))
    assert r.stdout.strip() == "bind=172.17.0.1"


@pytest.mark.parametrize("out", ["", "\n"])
def test_the_wrapper_fails_closed_when_docker0_has_no_address(fake_ip, out):
    r = fake_ip(out)
    assert r.returncode == 1
    assert "docker0 has no IPv4 address" in r.stderr
    assert "bind=" not in r.stdout  # the command never ran, so nothing fell back to a default


def test_the_wrapper_fails_closed_when_ip_itself_fails(tmp_path):
    (tmp_path / "ip").write_text("#!/bin/sh\nexit 1\n")
    (tmp_path / "ip").chmod(0o755)
    r = _run_wrapper(tmp_path, command=("sh", "-c", "echo ran"))
    assert r.returncode == 1 and "ran" not in r.stdout
