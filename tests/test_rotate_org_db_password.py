"""scripts/security/rotate_org_db_password.py: rotate the hub role `org` to the password in Infisical.

Offline: psycopg.connect and subprocess.run are fakes, the hub is `hub.test`, every password is a
random fake, and no path may print the password, the verifier or the URL (ok, refused, fail).
Postgres (skipped unless ROTATE_TEST_PG_CONTAINER names a THROWAWAY postgres:16 container whose
superuser is `org`, published on 127.0.0.1:ROTATE_TEST_PG_PORT): the real psql/\\getenv/ALTER ROLE
path, a login with the new password, and no SCRAM string in the server log with log_statement=all:

    docker run -d --rm --name rotate-scram-test -e POSTGRES_USER=org -e POSTGRES_DB=org \\
      -e POSTGRES_PASSWORD="$(openssl rand -hex 16)" -p 127.0.0.1:55432:5432 postgres:16 \\
      -c log_statement=all -c log_min_error_statement=error
    ROTATE_TEST_PG_CONTAINER=rotate-scram-test ROTATE_TEST_PG_PORT=55432 \\
      .venv/bin/python -m pytest -p no:warnings tests/test_rotate_org_db_password.py

Never point it at org-postgres, and never run it under scripts/hub/org-python.sh or
with-org-db-env.sh: those put the real ORG_DB_URL in the environment.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import os
import secrets
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "security" / "rotate_org_db_password.py"
SHELL = ROOT / "scripts" / "security" / "rotate-org-db-password.sh"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rot = _load("rotate_org_db_password", SCRIPT)

HUB = {"host": "hub.test", "port": 5432, "database": "org", "container": "hub-ctr", "superuser": "org"}


class AuthFailed(Exception):
    sqlstate = "28P01"


class Unreachable(Exception):
    sqlstate = None


class FakeConn:
    def __init__(self, value=1):
        self.value = value
        self.closed = False

    def execute(self, sql):
        assert sql == "SELECT 1"
        return self

    def fetchone(self):
        return (self.value,)

    def close(self):
        self.closed = True


class Connect:
    """Plays a list of outcomes: an exception instance is raised, anything else is returned."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        out = self.outcomes.pop(0)
        if isinstance(out, BaseException):
            raise out
        return out


class Runner:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls = []
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        out, err = self.stdout, self.stderr
        if callable(out):
            out = out(kw)
        if callable(err):
            err = err(kw)
        return subprocess.CompletedProcess(argv, self.returncode, out, err)


@pytest.fixture
def secret():
    pw = "Fake-New-" + secrets.token_hex(12)
    return {"pw": pw, "url": f"postgresql://org:{pw}@hub.test:5432/org", "old": "Fake-Old-" + secrets.token_hex(12)}


@pytest.fixture
def env_file(tmp_path, secret):
    p = tmp_path / "org-db.env"
    p.write_text(f"POSTGRES_USER=org\nPOSTGRES_PASSWORD={secret['old']}\nPOSTGRES_DB=org\n")
    p.chmod(0o600)
    return p


@pytest.fixture
def unit_dir(tmp_path):
    d = tmp_path / "systemd"
    (d / "svc-b.service.d").mkdir(parents=True)
    (d / "svc-a.service").write_text("ExecStart=/x/scripts/hub/with-org-db-env.sh /x/py run\n")
    (d / "svc-b.service.d" / "org-db.conf").write_text(
        "ExecStart=python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- x\n")
    (d / "svc-c.service").write_text("ExecStart=python3 tools/infisical_setup.py run Org-Coo prod -- x\n")
    (d / "svc-d.service").write_text("ExecStart=bash scripts/hub/org-python.sh -m tools.x\n")
    return d


def _run(argv, secret, capsys, *, connect, runner, env_file, unit_dir, extra_env=None):
    environ = {"ORG_DB_URL": secret["url"], "PATH": os.environ.get("PATH", ""), **(extra_env or {})}
    code = rot.main(argv, environ=environ, hub=HUB, connect=connect, runner=runner,
                    env_file=env_file, unit_dir=unit_dir)
    out, err = capsys.readouterr()
    return code, out + err


def _assert_no_leak(text, secret, *extra):
    for needle in (secret["pw"], secret["url"], secret["old"], "SCRAM-SHA-256$", *extra):
        assert needle not in text, "a secret reached the output"


# ---- step 1: what the URL may be -------------------------------------------------------------

@pytest.mark.parametrize("url_fmt", [
    "postgresql://someone:{pw}@hub.test:5432/org",          # not role org
    "postgresql://org:{pw}@elsewhere.test:5432/org",       # not the hub host
    "postgresql://org:{pw}@hub.test:6543/org",             # not the hub port
    "postgresql://org:{pw}@hub.test:5432/org_test",        # not the hub database
    "mysql://org:{pw}@hub.test:5432/org",                  # not postgres
    "postgresql://org:{pw}@hub.test:notaport/org",         # ValueError whose text quotes the URL
    "postgresql://org:short@hub.test:5432/org",            # too short
    "postgresql://org:{pw}%C3%A9@hub.test:5432/org",       # outside printable ASCII
    "",                                                   # unset
])
def test_refuses_any_url_but_the_hubs_org_role(url_fmt, secret, capsys, env_file, unit_dir):
    url = url_fmt.format(pw=secret["pw"])
    connect, runner = Connect(), Runner()
    code = rot.main(["apply"], environ={"ORG_DB_URL": url}, hub=HUB, connect=connect, runner=runner,
                    env_file=env_file, unit_dir=unit_dir)
    out, err = capsys.readouterr()
    assert code == 2
    assert "REFUSED" in out and "Nothing changed" in out
    assert connect.urls == [] and runner.calls == []
    _assert_no_leak(out + err, secret, url or "\0")
    assert secret["old"] in env_file.read_text()


def test_hub_address_comes_from_config():
    data = yaml.safe_load((ROOT / "config" / "hosts.yaml").read_text())
    expected = data["hosts"]["contabo"]["mesh_ssh"].rpartition("@")[2]
    hub = rot.load_hub()
    assert hub["host"] == expected and hub["host"]
    assert (hub["port"], hub["database"], hub["container"], hub["superuser"]) == (5432, "org", "org-postgres", "org")


def test_usage_on_bad_verb(secret, capsys, env_file, unit_dir):
    code, text = _run(["rotate"], secret, capsys, connect=Connect(), runner=Runner(),
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 2 and "usage" in text


# ---- step 2: refuse while the URL still logs in ------------------------------------------------

def test_refuses_while_infisical_password_still_works(secret, capsys, env_file, unit_dir):
    connect, runner = Connect(FakeConn()), Runner()
    code, text = _run(["apply"], secret, capsys, connect=connect, runner=runner,
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 3
    assert "REFUSED: Infisical still holds a working password; set the new one first" in text
    assert runner.calls == []
    assert secret["old"] in env_file.read_text()
    _assert_no_leak(text, secret)


def test_refuses_when_hub_does_not_answer(secret, capsys, env_file, unit_dir):
    connect, runner = Connect(Unreachable(f"connection to {secret['url']} timed out")), Runner()
    code, text = _run(["apply"], secret, capsys, connect=connect, runner=runner,
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 4 and "Unreachable" in text and "Nothing changed" in text
    assert runner.calls == []
    _assert_no_leak(text, secret)


def test_check_is_read_only(secret, capsys, env_file, unit_dir):
    before = env_file.read_text()
    connect, runner = Connect(AuthFailed(f"password authentication failed {secret['pw']}")), Runner()
    code, text = _run(["check"], secret, capsys, connect=connect, runner=runner,
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 0 and "CHECK OK" in text and "POSTGRES_PASSWORD" in text
    assert runner.calls == [] and len(connect.urls) == 1
    assert env_file.read_text() == before
    _assert_no_leak(text, secret)


def test_auth_failure_recognised_by_message_without_sqlstate(secret, capsys, env_file, unit_dir):
    exc = Exception(f'FATAL:  password authentication failed for user "org" {secret["url"]}')
    code, text = _run(["check"], secret, capsys, connect=Connect(exc), runner=Runner(),
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 0
    _assert_no_leak(text, secret)


def test_check_warns_on_a_stale_test_url(secret, capsys, env_file, unit_dir):
    stale = f"postgresql://org:{secret['old']}@hub.test:5432/org_test"
    code, text = _run(["check"], secret, capsys, connect=Connect(AuthFailed()), runner=Runner(),
                      env_file=env_file, unit_dir=unit_dir, extra_env={"ORG_TEST_DB_URL": stale})
    assert code == 0 and "ORG_TEST_DB_URL" in text and "update it too" in text
    _assert_no_leak(text, secret, stale)


# ---- steps 3-6: apply ------------------------------------------------------------------------

def test_apply_ok(secret, capsys, env_file, unit_dir):
    conn = FakeConn()
    connect, runner = Connect(AuthFailed(f"password authentication failed {secret['pw']}"), conn), Runner()
    code, text = _run(["apply"], secret, capsys, connect=connect, runner=runner,
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 0, text
    assert "OK: role org accepts the new password" in text
    assert conn.closed
    # step 4: the verifier by name on argv, by value only in docker's environment
    (argv, kw), = runner.calls
    assert argv[:6] == ["docker", "exec", "-i", "-e", "NEWVERIFIER", "hub-ctr"]
    assert argv[6:] == ["psql", "-X", "-q", "-U", "org", "-d", "org", "-v", "ON_ERROR_STOP=1"]
    verifier = kw["env"]["NEWVERIFIER"]
    assert rot.VERIFIER_RE.match(verifier)
    assert not any(verifier in a or secret["pw"] in a for a in argv)
    assert secret["pw"] not in kw["input"] and verifier not in kw["input"]
    assert "\\getenv v NEWVERIFIER" in kw["input"] and "ALTER ROLE org PASSWORD :'v';" in kw["input"]
    assert kw["input"].index("SET log_statement = 'none'") < kw["input"].index("ALTER ROLE")
    assert not any(secret["pw"] in v for k, v in kw["env"].items())
    assert not any(k.endswith("_DB_URL") or k.startswith("PG") for k in kw["env"])
    # the verifier matches the password: SCRAM StoredKey = H(HMAC(SaltedPassword, "Client Key"))
    _, it_salt, keys = verifier.split("$")
    iterations, salt = it_salt.split(":")
    stored, server = keys.split(":")
    salted = hashlib.pbkdf2_hmac("sha256", secret["pw"].encode(), base64.b64decode(salt), int(iterations))
    assert base64.b64decode(stored) == hashlib.sha256(hmac.new(salted, b"Client Key", "sha256").digest()).digest()
    assert base64.b64decode(server) == hmac.new(salted, b"Server Key", "sha256").digest()
    # step 5: the stale lines gone, nothing new written, 0600
    body = env_file.read_text()
    assert secret["old"] not in body and secret["pw"] not in body and verifier not in body
    assert "POSTGRES_USER=org\n" in body and "POSTGRES_DB=org\n" in body
    assert "POSTGRES_PASSWORD=" not in body
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert not list(env_file.parent.glob(".org-db.env.rotate-*"))
    # step 6: the holders by name
    assert "svc-a.service" in text and "svc-b.service" in text and "svc-d.service" in text
    assert "svc-c.service" not in text
    _assert_no_leak(text, secret, verifier)


def test_apply_psql_failure_hides_the_verifier(secret, capsys, env_file, unit_dir):
    leak = lambda kw: f"ERROR:  bad thing near '{kw['env']['NEWVERIFIER']}' {secret['pw']}\n"  # noqa: E731
    runner = Runner(returncode=3, stdout="", stderr=leak)
    connect = Connect(AuthFailed())
    code, text = _run(["apply"], secret, capsys, connect=connect, runner=runner,
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 5 and "FAIL: psql exited 3" in text
    verifier = runner.calls[0][1]["env"]["NEWVERIFIER"]
    assert len(connect.urls) == 1                     # no verify after a failed apply
    assert secret["old"] in env_file.read_text()      # the file is left alone
    _assert_no_leak(text, secret, verifier)


def test_apply_psql_output_with_password_is_scrubbed(secret, capsys, env_file, unit_dir):
    runner = Runner(returncode=3, stderr=f"ERROR:  role says {secret['pw']}\n")
    code, text = _run(["apply"], secret, capsys, connect=Connect(AuthFailed()), runner=runner,
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 5 and "***" in text
    _assert_no_leak(text, secret)


def test_apply_docker_crash_prints_class_only(secret, capsys, env_file, unit_dir):
    def runner(argv, **kw):
        raise OSError(f"{secret['pw']} {kw['env']['NEWVERIFIER']}")
    code, text = _run(["apply"], secret, capsys, connect=Connect(AuthFailed()), runner=runner,
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 5 and "OSError" in text
    _assert_no_leak(text, secret)


def test_apply_verify_failure(secret, capsys, env_file, unit_dir):
    connect = Connect(AuthFailed(), AuthFailed(f"password authentication failed for {secret['url']}"))
    code, text = _run(["apply"], secret, capsys, connect=connect, runner=Runner(),
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 6 and "FAIL: role org does not accept the new password" in text
    assert secret["old"] in env_file.read_text()
    _assert_no_leak(text, secret)


def test_apply_select_failure(secret, capsys, env_file, unit_dir):
    class Broken(FakeConn):
        def execute(self, sql):
            raise RuntimeError(secret["url"])
    code, text = _run(["apply"], secret, capsys, connect=Connect(AuthFailed(), Broken()), runner=Runner(),
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 6 and "RuntimeError" in text
    _assert_no_leak(text, secret)


def test_apply_env_file_error_is_a_warning(secret, capsys, env_file, unit_dir, monkeypatch):
    def boom(path):
        raise PermissionError(secret["pw"])
    monkeypatch.setattr(rot, "scrub_env_file", boom)
    code, text = _run(["apply"], secret, capsys, connect=Connect(AuthFailed(), FakeConn()), runner=Runner(),
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 0 and "WARN" in text and "PermissionError" in text
    _assert_no_leak(text, secret)


def test_unexpected_error_prints_class_only(secret, capsys, env_file, unit_dir, monkeypatch):
    def boom(url, hub):
        raise KeyError(url)
    monkeypatch.setattr(rot, "parse_url", boom)
    code, text = _run(["apply"], secret, capsys, connect=Connect(), runner=Runner(),
                      env_file=env_file, unit_dir=unit_dir)
    assert code == 1 and "FAIL: KeyError" in text
    _assert_no_leak(text, secret)


def test_missing_env_file_is_fine(secret, capsys, tmp_path, unit_dir):
    code, text = _run(["apply"], secret, capsys, connect=Connect(AuthFailed(), FakeConn()), runner=Runner(),
                      env_file=tmp_path / "absent.env", unit_dir=unit_dir)
    assert code == 0 and "holds none of" in text


def test_scrub_handles_export_and_keeps_other_lines(tmp_path):
    p = tmp_path / "e.env"
    p.write_text("# c\nexport ORG_DB_URL=postgresql://org:x@h/org\nPOSTGRES_USER=org\nORG_TEST_DB_URL=y\n")
    assert rot.scrub_env_file(p) == ["ORG_DB_URL", "ORG_TEST_DB_URL"]
    body = p.read_text()
    assert "org:x@" not in body and "=y" not in body and "# c\n" in body and "POSTGRES_USER=org\n" in body


def test_verifier_matches_the_coo_gate_copy():
    coo = _load("org_coo_role", ROOT / "deploy" / "coo-gate" / "org_coo_role.py")
    salt = bytes(range(16))
    assert rot.scram_verifier("Fake-pass-0123456789", salt=salt) == coo.scram_verifier("Fake-pass-0123456789", salt=salt)


def test_shell_wrapper_refuses_bad_verb_without_running_anything():
    done = subprocess.run(["bash", str(SHELL), "bogus"], capture_output=True, text=True,
                          env={"PATH": os.environ.get("PATH", "")}, timeout=10)
    assert done.returncode == 2 and "usage" in done.stderr
    text = SHELL.read_text()
    assert "infisical_setup.py run Agents-Core prod --as contabo --" in text
    assert "rotate_org_db_password.py \"$VERB\"" in text


# ---- real Postgres (throwaway container only) ------------------------------------------------

PG_CONTAINER = os.environ.get("ROTATE_TEST_PG_CONTAINER", "")
PG_PORT = int(os.environ.get("ROTATE_TEST_PG_PORT") or 55432)


@pytest.mark.skipif(not PG_CONTAINER, reason="ROTATE_TEST_PG_CONTAINER (a throwaway postgres:16) not set")
def test_real_postgres_scram_rotation(capsys, tmp_path):
    assert PG_CONTAINER != "org-postgres", "never the hub"
    import psycopg

    pw = "Fake-New-" + secrets.token_hex(12)
    url = f"postgresql://org:{pw}@127.0.0.1:{PG_PORT}/org"
    hub = {"host": "127.0.0.1", "port": PG_PORT, "database": "org", "container": PG_CONTAINER, "superuser": "org"}
    environ = {"ORG_DB_URL": url, "PATH": os.environ.get("PATH", "")}
    code = rot.main(["apply"], environ=environ, hub=hub, env_file=tmp_path / "absent.env", unit_dir=tmp_path)
    out, err = capsys.readouterr()
    assert code == 0, out
    assert "OK: role org accepts the new password" in out
    with psycopg.connect(url, connect_timeout=3) as conn:
        assert conn.execute("SELECT 1").fetchone() == (1,)
        assert conn.execute("SELECT current_user").fetchone() == ("org",)
    # run again: the URL now works, so the helper refuses and changes nothing
    assert rot.main(["apply"], environ=environ, hub=hub, env_file=tmp_path / "absent.env", unit_dir=tmp_path) == 3
    out2, err2 = capsys.readouterr()
    logs = subprocess.run(["docker", "logs", PG_CONTAINER], capture_output=True, text=True, timeout=30)
    assert "SET log_statement" in logs.stdout + logs.stderr or "statement:" in logs.stdout + logs.stderr
    for text in (out + err, out2 + err2, logs.stdout + logs.stderr):
        assert pw not in text
        assert "SCRAM-SHA-256$" not in text
    assert "ALTER ROLE" not in logs.stdout + logs.stderr     # the statement never reached the log
