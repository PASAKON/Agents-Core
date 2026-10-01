"""Option B (CEO 2026-10-02): a user-scoped machine credential on Windows nodes where nothing
runs elevated (winbox: UAC on, so Claude, the Run executor and every scheduled task are
non-elevated and cannot read the Administrators-only %ProgramData%\\Infisical file).

`save --scope user` writes %LOCALAPPDATA%\\MoonieX\\Infisical\\<name>.env, ACL'd to the user +
SYSTEM + Administrators; read_cred falls back to it when the machine file is missing or
unreadable. Off Windows nothing changes.
"""
from __future__ import annotations

import builtins
import shutil
import subprocess
from pathlib import Path

import pytest

from tools import infisical_setup

SID = "S-1-5-21-111-222-333-1001"
REPO = Path(__file__).resolve().parents[1]


def _windows(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: True)
    monkeypatch.setattr(infisical_setup, "_DEFAULT_CRED_DIR", str(tmp_path / "machine"))
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "machine"))
    monkeypatch.setattr(infisical_setup, "USER_CRED_DIR", str(tmp_path / "user"))


def _cred_text(cid, secret):
    return (f"INFISICAL_API_URL=x\nINFISICAL_UNIVERSAL_AUTH_CLIENT_ID={cid}\n"
            f"INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET={secret}\n")


def test_lock_acl_grants_the_user_sid_only_when_given(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: True)
    calls = []
    infisical_setup.lock_acl(str(tmp_path), lambda argv: calls.append(argv) or 0, SID)
    infisical_setup.lock_acl(str(tmp_path), lambda argv: calls.append(argv) or 0)
    base = ["icacls", str(tmp_path), "/inheritance:r", "/grant:r", "SYSTEM:F", "Administrators:F"]
    assert calls == [base + [f"*{SID}:F"], base]


def test_write_cred_user_scope_writes_under_the_user_dir_without_root(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    monkeypatch.setattr(infisical_setup, "require_root", lambda: pytest.fail("user scope needs no admin"))
    calls = []
    path = infisical_setup.write_cred("winbox", "cid", "SECRET-B-1", scope="user", user_sid=SID,
                                      run=lambda argv: calls.append(argv) or 0)
    assert Path(path) == tmp_path / "user" / "winbox.env"
    assert Path(path).read_text().count("SECRET-B-1") == 1
    assert [c[1] for c in calls] == [str(tmp_path / "user"), path + ".tmp"]   # dir first, then the file
    assert all(c[-1] == f"*{SID}:F" for c in calls)
    assert not (tmp_path / "machine").exists()


def test_write_cred_user_scope_fails_closed_when_the_acl_fails(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    with pytest.raises(infisical_setup.AclError):
        infisical_setup.write_cred("winbox", "cid", "SECRET-B-2", scope="user", user_sid=SID,
                                   run=lambda argv: 0 if argv[1].endswith("user") else 1)
    assert list((tmp_path / "user").iterdir()) == []                 # no file, not even a .tmp


def test_write_cred_user_scope_is_refused_off_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "USER_CRED_DIR", str(tmp_path / "user"))
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: False)
    with pytest.raises(infisical_setup.AclError, match="Windows"):
        infisical_setup.write_cred("winbox", "cid", "SECRET-B-3", scope="user", user_sid=SID)
    assert not (tmp_path / "user").exists()


def test_cmd_save_user_scope_exits_off_windows_before_reading_anything(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "USER_CRED_DIR", str(tmp_path / "user"))
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: False)
    monkeypatch.setattr(infisical_setup.sys, "stdin", None)          # reading would crash
    with pytest.raises(SystemExit, match="Windows"):
        infisical_setup.cmd_save("winbox", from_stdin=True, scope="user")


def test_read_cred_falls_back_to_the_user_file_when_the_machine_file_is_missing(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    (tmp_path / "user").mkdir()
    (tmp_path / "user" / "winbox.env").write_text(_cred_text("cid-u", "sec-u"))
    assert infisical_setup.read_cred("winbox") == ("cid-u", "sec-u")


def test_read_cred_falls_back_when_the_machine_file_is_unreadable(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    (tmp_path / "machine").mkdir()
    machine = tmp_path / "machine" / "winbox.env"
    machine.write_text(_cred_text("cid-m", "sec-m"))
    (tmp_path / "user").mkdir()
    (tmp_path / "user" / "winbox.env").write_text(_cred_text("cid-u", "sec-u"))

    def guarded(path, *a, **kw):
        if Path(path) == machine:
            raise PermissionError(13, "Access is denied")              # admin-only, process not elevated
        return builtins.open(path, *a, **kw)

    monkeypatch.setattr(infisical_setup, "open", guarded, raising=False)
    assert infisical_setup.read_cred("winbox") == ("cid-u", "sec-u")


def test_read_cred_prefers_a_readable_machine_file(monkeypatch, tmp_path):
    _windows(monkeypatch, tmp_path)
    for scope, cid in (("machine", "cid-m"), ("user", "cid-u")):
        (tmp_path / scope).mkdir()
        (tmp_path / scope / "winbox.env").write_text(_cred_text(cid, "s"))
    assert infisical_setup.read_cred("winbox")[0] == "cid-m"


def test_read_cred_has_no_fallback_off_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: False)
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "machine"))
    monkeypatch.setattr(infisical_setup, "USER_CRED_DIR", str(tmp_path / "user"))
    (tmp_path / "user").mkdir()
    (tmp_path / "user" / "winbox.env").write_text(_cred_text("cid-u", "sec-u"))
    with pytest.raises(FileNotFoundError):
        infisical_setup.read_cred("winbox")


def test_current_user_sid_parses_whoami_and_fails_closed():
    out = f'"desktop-3nqb2qo\\passg","{SID}"\r\n'
    assert infisical_setup.current_user_sid(lambda argv: out) == SID
    with pytest.raises(infisical_setup.AclError):
        infisical_setup.current_user_sid(lambda argv: "garbage")

    def missing(argv):
        raise FileNotFoundError("whoami")

    with pytest.raises(infisical_setup.AclError):
        infisical_setup.current_user_sid(missing)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_bootstrap_refuses_an_unknown_scope_before_any_network_call():
    r = subprocess.run(["node", str(REPO / "scripts/infisical/bootstrap_setup_identity.mjs"),
                        "http://127.0.0.1:9", "--identity", "winbox", "--scope", "everyone"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 64 and "bad --scope" in r.stderr


def test_bootstrap_forwards_the_scope_to_the_save_tool():
    src = (REPO / "scripts/infisical/bootstrap_setup_identity.mjs").read_text(encoding="utf-8")
    assert "'save', IDENTITY, '--stdin', '--scope', opt.scope" in src


def test_a_moved_cred_dir_never_falls_back_to_a_real_user_file(monkeypatch, tmp_path):
    """Other suites point CRED_DIR at tmp and expect FileNotFoundError; on winbox the real user
    file exists, and falling back to it would make those tests log in live."""
    _windows(monkeypatch, tmp_path)
    (tmp_path / "user").mkdir()
    (tmp_path / "user" / "winbox.env").write_text(_cred_text("cid-u", "sec-u"))
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "elsewhere"))
    with pytest.raises(FileNotFoundError):
        infisical_setup.read_cred("winbox")


class _FakeOrg:
    def __init__(self, identity):
        self.identity = identity

    def get(self, path, **params):
        return {"secrets": [{"secretKey": "SUPABASE_URL", "secretValue": "https://x"}]}


def _fake_run_env(monkeypatch):
    monkeypatch.setattr(infisical_setup, "Org", _FakeOrg)
    monkeypatch.setattr(infisical_setup, "_project", lambda org, name: {"id": "p1", "name": name})


def test_run_on_windows_waits_for_the_child_and_returns_its_exit_code(monkeypatch):
    """os.execvpe on Windows ends the parent at once, so a supervisor would lose the program."""
    _fake_run_env(monkeypatch)
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: True)
    monkeypatch.setattr(infisical_setup.os, "execvpe", lambda *a: pytest.fail("exec on Windows"))
    seen = {}

    def call(argv, env):
        seen["argv"], seen["url"] = argv, env.get("SUPABASE_URL")
        return 7

    monkeypatch.setattr(infisical_setup.subprocess, "call", call)
    with pytest.raises(SystemExit) as exc:
        infisical_setup.cmd_run("winbox", "MoonieX-Option", "prod", ["node", "trader.js"])
    assert exc.value.code == 7
    assert seen["argv"][1:] == ["trader.js"] and seen["url"] == "https://x"


def test_run_off_windows_still_execs(monkeypatch):
    _fake_run_env(monkeypatch)
    monkeypatch.setattr(infisical_setup, "_is_nt", lambda: False)
    seen = {}

    def execvpe(file, argv, env):
        seen["argv"], seen["url"] = argv, env.get("SUPABASE_URL")
        raise SystemExit(0)

    monkeypatch.setattr(infisical_setup.os, "execvpe", execvpe)
    monkeypatch.setattr(infisical_setup.subprocess, "call", lambda *a, **k: pytest.fail("child off Windows"))
    with pytest.raises(SystemExit):
        infisical_setup.cmd_run("contabo", "MoonieX-Option", "prod", ["node", "trader.js"])
    assert seen == {"argv": ["node", "trader.js"], "url": "https://x"}
