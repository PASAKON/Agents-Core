"""No real credentials, SSH or model requests: all processes use a temporary HOME."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools import cli_login as login


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    for key in list(os.environ):
        if any(word in key for word in ("TOKEN", "API_KEY", "ANTHROPIC", "ANTIGRAVITY", "GEMINI", "GOOGLE", "CLAUDE", "CODEX")):
            monkeypatch.delenv(key, raising=False)
    for key in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "APPDATA", "LOCALAPPDATA"):
        monkeypatch.setenv(key, str(tmp_path))
    monkeypatch.delenv("CLI_LOGIN_AGY_TOKEN_FILE", raising=False)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    script = '''#!PYTHON
import json, os, sys, time
from pathlib import Path
h = Path.home()
name = Path(sys.argv[0]).name
if sys.argv[1:] in (["auth", "status"], ["login", "status"], ["models"]):
    ok = (h / "ok").exists()
    if name == "claude": print(json.dumps({"loggedIn": ok, "email": "private@example.test"}))
    elif name == "agy": print("models: fake-model" if ok else "Please sign in")
    else: print("Logged in using ChatGPT" if ok else "Not logged in")
    sys.exit(0 if ok else 1)
assert os.isatty(0)
if name == "agy":
    print("Select login method: > 1. Google OAuth", flush=True)
    input()
print("\\x1b[32mhttps://accounts.google.com/o/oauth2/auth?client_id=fake&", flush=True)
print("  redirect_uri=https%3A%2F%2Fantigravity.google%2Foauth-callback&", flush=True)
time.sleep(.8 if (h / "slow-wrap").exists() else .05)
print("  state=fake\\x1b[0m", flush=True)
if name == "codex":
    print("Your device code: ABCD-1234", flush=True)
    time.sleep(1)
else:
    print("Paste code here > ", end="", flush=True)
    code = input()
    (h / "forwarded").write_text(code)
    print("private@example.test credential-must-not-be-output " + code, flush=True)
if not (h / "stay-no").exists():
    (h / "ok").touch()
    p = h / ".gemini/antigravity-cli/antigravity-oauth-token"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("fake-only")
'''.replace("PYTHON", sys.executable)
    for cli in login.CLIS:
        path = bin_dir / cli
        path.write_text(script)
        path.chmod(0o700)
    return tmp_path


@pytest.mark.parametrize("cli", login.CLIS)
def test_login_pty_join_and_forward(fake_home, cli):
    result = subprocess.run([sys.executable, str(Path(login.__file__)), "login", cli],
                            input="pasted-private-code\n", capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert "OPEN: https://accounts.google.com/o/oauth2/auth?client_id=fake&redirect_uri=https%3A%2F%2Fantigravity.google%2Foauth-callback&state=fake\n" in result.stdout
    if cli == "codex":
        assert "CODE: ABCD-1234\n" in result.stdout
        assert not (fake_home / "forwarded").exists()
    else:
        assert (fake_home / "forwarded").read_text() == "pasted-private-code"
    assert "pasted-private-code" not in result.stdout + result.stderr
    assert "private@example.test" not in result.stdout + result.stderr
    assert "credential-must-not-be-output" not in result.stdout + result.stderr


def test_login_exit_zero_does_not_override_status_no(fake_home):
    (fake_home / "stay-no").touch()
    result = subprocess.run([sys.executable, str(Path(login.__file__)), "login", "claude"],
                            input="fake-code\n", capture_output=True, text=True, timeout=15)
    assert result.returncode != 0


def test_wait_for_prompt_before_publishing_wrapped_url(fake_home):
    (fake_home / "slow-wrap").touch()
    result = subprocess.run([sys.executable, str(Path(login.__file__)), "login", "claude"],
                            input="fake-code\n", capture_output=True, text=True, timeout=15)
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    assert len(lines) == 1 and lines[0].endswith("&state=fake")


def test_url_osc_and_crlf():
    url = "https://claude.ai/oauth/authorize?state=fake&code_challenge=fake"
    text = f"Sign in: \x1b]8;;{url}\x1b\\{url[:40]}\r\n  {url[40:]}\x1b]8;;\x1b\\\r\nPaste code here > "
    assert login.login_url(text) == url


def test_status_sanitized(fake_home, capsys):
    (fake_home / "ok").touch()
    assert login.main(["status", "--json", "--cli", "claude"]) == 0
    output = capsys.readouterr().out
    assert "private@example.test" not in output
    assert json.loads(output)[0]["logged_in"] is True


def test_agy_presence_alone_is_not_logged_in(fake_home):
    path = login.credential_path("agy")
    path.parent.mkdir(parents=True)
    path.write_text("fake-stale-token")
    assert login.status("agy")["logged_in"] is False


def test_unsupported_keychain_never_reads_files(fake_home, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert login.credential_path("claude") is None
    with pytest.raises(login.Refused):
        login.payload("claude")


def test_export_rejects_non_ssh(fake_home, monkeypatch, capsys):
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.setattr(login, "payload", lambda cli: pytest.fail("read before transport guard"))
    assert login.main(["_export", "codex"]) == 1
    assert capsys.readouterr().out == ""


def test_push_private_stdin(fake_home, monkeypatch, capsys):
    path = login.credential_path("codex")
    path.parent.mkdir()
    secret = b'fake-secret-bytes-ONLY'
    path.write_bytes(secret)
    calls = []
    def ssh(argv, **kwargs):
        calls.append((argv, kwargs))
        assert argv[0] == "ssh"
        assert "winbox" in argv
        assert secret.decode() not in " ".join(argv)
        assert base64.b64encode(secret).decode() not in " ".join(argv)
        assert base64.b64decode(json.loads(kwargs["input"])["data"]) == secret
        return subprocess.CompletedProcess(argv, 0, secret, secret)
    monkeypatch.setattr(subprocess, "run", ssh)
    assert login.transfer("codex", "winbox") == 0
    output = capsys.readouterr()
    assert secret.decode() not in output.out + output.err
    assert len(calls) == 1


def test_receive_permissions_and_wrong_cli(fake_home):
    data = json.dumps({"cli": "codex", "data": base64.b64encode(b"fake").decode()}).encode()
    login.receive("codex", data)
    path = login.credential_path("codex")
    assert path.read_bytes() == b"fake"
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(login.Refused):
        login.receive("claude", data)


def test_mac_route_refused_before_read(fake_home, monkeypatch):
    monkeypatch.setattr(login, "payload", lambda cli: pytest.fail("read before route check"))
    with pytest.raises(login.Refused, match="Mac inbound"):
        login.transfer("codex", "mac")


def test_pull_private_pipe(fake_home, monkeypatch, capsys):
    secret = b"fake-pulled-secret"
    data = json.dumps({"cli": "codex", "data": base64.b64encode(secret).decode()}).encode()
    def ssh(argv, **kwargs):
        assert "mooniex-vps" in argv and "_export codex" in argv[-1]
        assert kwargs["capture_output"] is True
        return subprocess.CompletedProcess(argv, 0, data, b"")
    monkeypatch.setattr(subprocess, "run", ssh)
    monkeypatch.setattr(login, "status", lambda cli: {"cli": cli, "logged_in": True, "credential_path": "fake", "mtime": 0, "reason": "status-yes"})
    assert login.transfer("codex", "contabo", pull=True) == 0
    assert login.credential_path("codex").read_bytes() == secret
    assert secret.decode() not in capsys.readouterr().out


def test_failed_ssh_is_sanitized(fake_home, monkeypatch, capsys):
    monkeypatch.setattr(login, "payload", lambda cli: b"fake")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 1, b"secret", b"secret"))
    assert login.main(["push", "codex", "--to", "winbox"]) == 1
    output = capsys.readouterr()
    assert "secret" not in output.out + output.err


def test_symlink_destination_refused(fake_home):
    path = login.credential_path("codex")
    path.parent.mkdir()
    target = fake_home / "target"
    target.write_text("unchanged")
    path.symlink_to(target)
    with pytest.raises(login.Refused):
        login.receive("codex", json.dumps({"cli": "codex", "data": "ZmFrZQ=="}).encode())
    assert target.read_text() == "unchanged"
