"""Org Mesh W3.1 (task-97d0f7e8): the org core imports and runs on Windows.

winbox runs Python 3.11 on Windows, where `os.kill(pid, 0)` sends Ctrl-C instead
of probing, there is no tmux, osascript or fcntl, and the Mac paths in the config
do not exist. What is pinned here, all without a Windows box:

  * lib.proc.pid_alive on POSIX against real processes (a live one, a dead one,
    pid 0 and other non-pids, EPERM), so the same tests also run on winbox
  * the Windows branch with ctypes replaced by a fake kernel32 and os.kill
    made to raise: it must never be reached
  * the four old probe sites (delegate x2, worker_reap, session_list, session_cap)
    route through it, and no `os.kill(<x>, 0)` is left in those files
  * an import smoke test in a subprocess with sys.platform='win32' and fcntl,
    termios, pwd, grp, resource blocked (with a control that must fail)
  * the platform guards (tmux, osascript, local spawn) and the path lookups
    (.od root, claudeflow .env, venv python, wiki roots) degrade instead of crash

Nothing here reaches the real ledger, a worktree, tmux, iTerm or a spawn: the
delegate test drives `_spawn_local`'s first step by hand against a fake db.
"""
from __future__ import annotations

import ast
import json
import os
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

import cxo_mcp_config as cxo  # noqa: E402
import lib.config as config  # noqa: E402
import lib.db as db  # noqa: E402
import lib.notify as notify  # noqa: E402
import lib.proc as proc  # noqa: E402
import lib.telegram_out as telegram_out  # noqa: E402
import session_list as sl  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.session_cap as session_cap  # noqa: E402
import tools.tmux_session as ts  # noqa: E402
import tools.wiki as wiki  # noqa: E402
import tools.worker_reap as worker_reap  # noqa: E402

FOUR_FILES = ("tools/delegate.py", "tools/worker_reap.py",
              "scripts/session_list.py", "tools/session_cap.py")


@pytest.fixture(autouse=True)
def _keep_the_shared_logs_clean(monkeypatch):
    # Faking win32 makes notify.error() look like a real org event; never let it
    # write the live state/logs/cto.log.
    monkeypatch.setenv("ORG_NOTIFY_SILENT", "1")


def _boom(*_a, **_k):
    raise AssertionError("must not be reached on this platform")


def _sleeper() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])


# --------------------------------------------------------------------------
# pid_alive, for real (also runs on winbox, through the Windows branch there)
# --------------------------------------------------------------------------

def test_pid_alive_true_for_this_process_and_a_running_child():
    child = _sleeper()
    try:
        assert proc.pid_alive(os.getpid()) is True
        assert proc.pid_alive(child.pid) is True
    finally:
        child.kill()
        child.wait()


def test_pid_alive_false_for_a_process_that_has_exited():
    child = _sleeper()
    child.kill()
    child.wait()
    assert proc.pid_alive(child.pid) is False


@pytest.mark.parametrize("bad", [0, -1, -12345, True, False, None, "123", 12.0,
                                 2 ** 70])
def test_pid_alive_false_for_anything_that_is_not_a_pid(bad):
    assert proc.pid_alive(bad) is False


@pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="needs a pid this user may not signal (POSIX, not root)")
def test_pid_alive_eperm_is_alive_unless_the_caller_says_otherwise():
    # pid 1 (launchd / init) exists and is not ours to signal.
    assert proc.pid_alive(1) is True
    assert proc.pid_alive(1, denied_is_alive=False) is False


# --------------------------------------------------------------------------
# the Windows branch, ctypes faked
# --------------------------------------------------------------------------

class _FakeKernel32:
    """pid -> exit code for a process the fake knows; anything else is 'no such pid'."""

    def __init__(self, procs):
        self.procs = dict(procs)
        self.opened: list[tuple] = []
        self.closed: list[int] = []
        self.exit_code_call_ok = True

    def OpenProcess(self, access, inherit, pid):
        self.opened.append((access, inherit, pid))
        return 0x1000 + pid if pid in self.procs else 0

    def GetExitCodeProcess(self, handle, ref):
        if not self.exit_code_call_ok:
            return 0
        ref._obj.value = self.procs[handle - 0x1000]
        return 1

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return 1


@pytest.fixture
def win(monkeypatch):
    """Turn this process into a fake Windows one: sys.platform, an os.kill that
    fails the test, a fake kernel32 and a scripted GetLastError."""
    def install(procs=None, last_error=87):
        k32 = _FakeKernel32(procs or {})
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(os, "kill", _boom)
        monkeypatch.setattr(proc, "_kernel32", lambda: k32)
        monkeypatch.setattr(proc, "_last_error", lambda: last_error)
        return k32
    return install


def test_windows_running_process_is_alive_and_the_handle_is_closed(win):
    k32 = win({4242: 259})
    assert proc.pid_alive(4242) is True
    assert k32.opened == [(0x1000, False, 4242)]   # PROCESS_QUERY_LIMITED_INFORMATION
    assert k32.closed == [0x1000 + 4242]


def test_windows_exited_process_is_dead_and_the_handle_is_closed(win):
    k32 = win({4242: 0})
    assert proc.pid_alive(4242) is False
    assert k32.closed == [0x1000 + 4242]


def test_windows_exit_code_query_failing_reads_as_dead_and_closes_the_handle(win):
    k32 = win({4242: 259})
    k32.exit_code_call_ok = False
    assert proc.pid_alive(4242) is False
    assert k32.closed == [0x1000 + 4242]


def test_windows_no_such_pid_is_dead(win):
    k32 = win({}, last_error=87)                    # ERROR_INVALID_PARAMETER
    assert proc.pid_alive(4242) is False
    assert k32.closed == []                          # nothing was opened, nothing to close


def test_windows_access_denied_means_it_exists(win):
    win({}, last_error=5)                            # ERROR_ACCESS_DENIED
    assert proc.pid_alive(4242) is True
    assert proc.pid_alive(4242, denied_is_alive=False) is False


@pytest.mark.parametrize("bad", [0, -4, None, True, "4242", 2 ** 32 + 4242])
def test_windows_never_opens_a_process_for_a_non_pid(win, bad):
    k32 = win({4242: 259})
    assert proc.pid_alive(bad) is False
    assert k32.opened == []                          # 2**32+4242 must not wrap onto 4242


def test_windows_branch_never_calls_os_kill(win):
    win({4242: 259})
    for pid in (4242, 4243, 1):
        proc.pid_alive(pid)                          # os.kill is _boom: any call fails the test


# --------------------------------------------------------------------------
# the four old sites go through it, with their own EPERM reading kept
# --------------------------------------------------------------------------

def test_worker_reap_session_cap_and_delegate_probe_through_lib_proc(win):
    win({4242: 259, 5000: 0})
    assert worker_reap._pid_alive(4242) is True
    assert session_cap._alive(4242) is True
    assert delegate._pid_alive(4242) is True
    assert worker_reap._pid_alive(5000) is False
    assert session_cap._alive(5000) is False
    assert delegate._pid_alive(5000) is False
    assert delegate._pid_alive(None) is False
    assert worker_reap._pid_alive(None) is False


def test_each_site_keeps_its_own_access_denied_reading(win):
    win({}, last_error=5)
    assert worker_reap._pid_alive(4242) is False     # a reaper never signals a stranger
    assert session_cap._alive(4242) is True          # a stranger still occupies the box
    assert delegate._pid_alive(4242) is True


def test_operator_cap_probe_on_windows(win, monkeypatch):
    win({4242: 259, 5000: 0})
    monkeypatch.setattr(delegate, "self_host", lambda: "winbox")
    live = delegate._operator_counts_as_live
    assert live({"pid": 4242}, "winbox") is True
    assert live({"pid": 5000}, "winbox") is False    # provably gone: holds no tab
    assert live({"pid": None}, "winbox") is True     # spawn in flight
    assert live({"pid": "not-a-pid"}, "winbox") is True
    assert live({"pid": 5000}, "contabo") is True    # another host cannot be probed from here


def test_session_list_lock_probe_on_windows(win, monkeypatch, tmp_path):
    win({4242: 259}, last_error=87)
    monkeypatch.setattr(sl, "REPO", str(tmp_path))
    (tmp_path / "state" / "locks").mkdir(parents=True)
    (tmp_path / "state" / "locks" / "cto-abc12345.lock").write_text("4242")
    (tmp_path / "state" / "locks" / "cto-dead0001.lock").write_text("5000")
    assert sl.tmux_lock_live("cto", "abc12345") is True     # tmux guard says no, lock pid says yes
    assert sl.tmux_lock_live("cto", "dead0001") is False
    assert sl.tmux_lock_live("cto", "nolock000") is False


def _os_kill_zero_calls(source: str) -> list[int]:
    hits = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "kill"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "os"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant) and node.args[1].value == 0):
            hits.append(node.lineno)
    return hits


def test_the_static_check_can_see_an_os_kill_zero():
    assert _os_kill_zero_calls("import os\nos.kill(pid, 0)\n") == [2]
    assert _os_kill_zero_calls("import os\nos.kill(int(pid), 0)\n") == [2]
    assert _os_kill_zero_calls("import os\nos.kill(pid, 15)\n") == []
    assert _os_kill_zero_calls('"""os.kill(pid, 0) in a docstring"""\n') == []


@pytest.mark.parametrize("rel", FOUR_FILES)
def test_no_os_kill_zero_left_in_the_four_files(rel):
    source = (ROOT / rel).read_text(encoding="utf-8")
    assert _os_kill_zero_calls(source) == [], f"{rel} still probes with os.kill(<pid>, 0)"
    assert "lib.proc" in source, f"{rel} does not use lib.proc"


# --------------------------------------------------------------------------
# imports on Windows: fcntl and friends are not there
# --------------------------------------------------------------------------

_SMOKE = textwrap.dedent('''
    import importlib, json, sys
    mods, control = json.loads(sys.argv[1]), json.loads(sys.argv[2])
    report = {"phase1": {}, "ok": [], "failed": {}, "blocked": False}

    def load(name, into):
        try:
            importlib.import_module(name)
            return True
        except Exception as e:
            into[name] = f"{type(e).__name__}: {e}"
            return False

    # Phase 1 on the real platform warms the stdlib and third-party imports:
    # subprocess, ssl and friends pick their Windows branch at import time and
    # cannot be imported under a faked sys.platform on a POSIX box.
    for name in mods + control:
        load(name, report["phase1"])
    ours = ("lib", "tools", "scripts", "runners", "session_list", "cxo_mcp_config")
    for name in [n for n in sys.modules if n.split(".")[0] in ours]:
        del sys.modules[name]
    sys.platform = "win32"
    for blocked in ("fcntl", "termios", "pwd", "grp", "resource"):
        sys.modules[blocked] = None
    report["blocked"] = all(sys.modules[b] is None for b in ("fcntl", "termios", "pwd", "grp", "resource"))
    for name in mods + control:
        if load(name, report["failed"]):
            report["ok"].append(name)
    print(json.dumps(report))
''')

TOUCHED_MODULES = [
    "lib.proc", "lib.notify", "lib.db", "lib.telegram_out", "lib.config",
    "tools.tmux_session", "tools.session_cap", "tools.worker_reap", "tools.delegate",
    "tools.wiki", "session_list", "cxo_mcp_config",
]
# Imports fcntl at module level, so on Windows it must fail: proves the block works.
CONTROL = ["tools.credit_ledger"]


def test_touched_modules_import_with_windows_platform_and_no_fcntl():
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), str(ROOT / "scripts"), str(ROOT / "scripts" / "lib")])
    env["ORG_NOTIFY_SILENT"] = "1"
    r = subprocess.run(
        [sys.executable, "-c", _SMOKE, json.dumps(TOUCHED_MODULES), json.dumps(CONTROL)],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    report = json.loads(r.stdout.strip().splitlines()[-1])
    assert report["blocked"] is True
    broken_at_home = {k: v for k, v in report["phase1"].items() if k in TOUCHED_MODULES}
    assert broken_at_home == {}, f"import failed even on the real platform: {broken_at_home}"
    assert list(report["failed"]) == CONTROL, (
        f"expected only the fcntl control to fail, got {report['failed']}")
    assert "fcntl" in report["failed"][CONTROL[0]]
    assert sorted(report["ok"]) == sorted(TOUCHED_MODULES)


# --------------------------------------------------------------------------
# platform guards
# --------------------------------------------------------------------------

def test_tmux_helpers_degrade_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ts.subprocess, "run", _boom)
    monkeypatch.setattr(ts.subprocess, "Popen", _boom)
    assert ts.has_session("cto-abc12345") is False
    assert ts.capture("cto-abc12345") == ""
    assert ts.kill("cto-abc12345") is False
    with pytest.raises(RuntimeError, match="not available on Windows"):
        ts.create("wd-abc12345", ".", "true")
    with pytest.raises(RuntimeError, match="session not found"):
        ts.send_keys("wd-abc12345", "hello")
    with pytest.raises(RuntimeError, match="session not found"):
        ts.start_ttyd("wd-abc12345", 8700)


def test_session_list_never_calls_osascript_off_the_mac(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sl.subprocess, "run", _boom)
    assert sl.live_ids() == (set(), False)


def test_notify_never_reaches_osascript_off_the_mac(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(notify.subprocess, "run", _boom)
    notify.error("boom on winbox")              # error() asks for the mac banner
    notify.success("done on winbox")
    err = capsys.readouterr().err
    assert "boom on winbox" in err and "done on winbox" in err


def test_local_spawn_on_windows_fails_the_row_before_tmux(monkeypatch):
    row = {"id": "task-w31test", "role": "developer", "project": "mooniex-agents",
           "status": "pending"}
    updates = []

    def fake_update_status(task_id, status, **kw):
        updates.append((task_id, status, kw))
        return True

    monkeypatch.setattr(delegate.db, "update_status", fake_update_status)
    monkeypatch.setattr(delegate.db, "get_task", lambda tid: {**row, "status": "failed"})
    monkeypatch.setattr(delegate.tmux, "create", _boom)
    monkeypatch.setattr(delegate, "_write_task_sidecar", _boom)
    monkeypatch.setattr(delegate, "_spawn_iterm_tab", _boom)
    monkeypatch.setattr(delegate, "_spawn_background", _boom)
    monkeypatch.setattr(sys, "platform", "win32")

    # The Windows guard is the first step, so the coroutine finishes without an
    # await: drive it by hand rather than start an event loop under a fake platform.
    coro = delegate._spawn_local(row, {})
    with pytest.raises(StopIteration) as done:
        coro.send(None)
    result = done.value.value

    assert result["status"] == "failed"
    assert len(updates) == 1
    task_id, status, kw = updates[0]
    assert (task_id, status) == ("task-w31test", "failed")
    assert "Windows" in kw["delegate_log"] and "W3.3" in kw["delegate_log"]


# --------------------------------------------------------------------------
# paths: a missing one degrades with one warning, never at import
# --------------------------------------------------------------------------

def test_od_root_is_off_on_a_host_without_a_claudesign_checkout(monkeypatch, capsys):
    monkeypatch.delenv("CLAUDESIGN_OD_ROOT", raising=False)
    monkeypatch.setattr(config, "self_host", lambda: "winbox")
    monkeypatch.setattr(db, "_od_root_warned", False)
    assert db._od_root() is None
    assert db._od_root() is None
    assert capsys.readouterr().err.count("claudesign .od root not resolvable") == 1
    assert db.resolve_od_project("11111111-1111-1111-1111-111111111111") is None
    assert db.designer_kickoff_suffix("design 11111111-1111-1111-1111-111111111111") == ""


def test_od_root_on_the_mac_comes_from_projects_yaml(monkeypatch):
    monkeypatch.delenv("CLAUDESIGN_OD_ROOT", raising=False)
    monkeypatch.setattr(config, "self_host", lambda: "mac")
    expected = Path(config.project_path_for_host("mooniex-claudesign", "mac")) / ".od"
    assert db._od_root() == expected


def test_od_project_still_resolves_from_an_override_root(monkeypatch, tmp_path):
    pid = "22222222-2222-2222-2222-222222222222"
    con = sqlite3.connect(tmp_path / "app.sqlite")
    con.execute("CREATE TABLE projects (id TEXT, name TEXT, skill_id TEXT)")
    con.execute("INSERT INTO projects VALUES (?, ?, ?)", (pid, "Landing", "hero"))
    con.commit()
    con.close()
    monkeypatch.setenv("CLAUDESIGN_OD_ROOT", str(tmp_path))
    info = db.resolve_od_project(pid)
    assert info["name"] == "Landing" and info["skill"] == "hero"
    assert info["dir"] == str(tmp_path / "projects" / pid)


def test_claudeflow_env_fallback_is_off_outside_the_mac(monkeypatch, capsys):
    monkeypatch.delenv("CLAUDEFLOW_ENV", raising=False)
    monkeypatch.setattr(config, "self_host", lambda: "winbox")
    monkeypatch.setattr(telegram_out, "_claudeflow_fallback_warned", False)
    assert telegram_out._claudeflow_env() == {}
    assert telegram_out._claudeflow_env() == {}
    assert capsys.readouterr().err.count("claudeflow .env fallback off") == 1


def test_claudeflow_env_fallback_on_the_mac_comes_from_projects_yaml(monkeypatch):
    monkeypatch.setattr(config, "self_host", lambda: "mac")
    expected = str(Path(config.project_path_for_host("mooniex-claudeflow", "mac")) / ".env")
    assert telegram_out._claudeflow_env_default() == expected


def test_claudeflow_env_override_still_wins(monkeypatch, tmp_path):
    fixture = tmp_path / "claudeflow.env"
    fixture.write_text("SECRETARY_BOT_TOKEN=fixture-token\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDEFLOW_ENV", str(fixture))
    assert telegram_out._claudeflow_env() == {"SECRETARY_BOT_TOKEN": "fixture-token"}
    monkeypatch.setenv("CLAUDEFLOW_ENV", str(tmp_path / "nope.env"))
    assert telegram_out._claudeflow_env() == {}


def test_venv_python_names_the_interpreter_this_os_has(monkeypatch, tmp_path):
    root = str(tmp_path)
    posix = tmp_path / ".venv" / "bin" / "python"
    windows = tmp_path / ".venv" / "Scripts" / "python.exe"
    monkeypatch.setattr(cxo, "_is_windows", lambda: False)
    assert cxo._venv_python(root) == posix           # nothing yet: this OS's own path
    monkeypatch.setattr(cxo, "_is_windows", lambda: True)
    assert cxo._venv_python(root) == windows         # the error message names a path that can exist
    windows.parent.mkdir(parents=True)
    windows.write_text("")
    assert cxo._venv_python(root) == windows
    posix.parent.mkdir(parents=True)
    posix.write_text("")
    assert cxo._venv_python(root) == posix           # unchanged: bin/ wins when it exists


def test_every_venv_python_site_in_cxo_mcp_config_uses_the_helper():
    tree = ast.parse((ROOT / "scripts" / "lib" / "cxo_mcp_config.py").read_text(encoding="utf-8"))
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_venv_python")
    inside = range(helper.lineno, helper.end_lineno + 1)
    strays = [(n.value, n.lineno) for n in ast.walk(tree)
              if isinstance(n, ast.Constant) and n.value in {"bin", "Scripts", "python.exe", ".venv"}
              and n.lineno not in inside]
    assert strays == [], f"an interpreter path is built outside _venv_python: {strays}"
    callers = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Name) and n.func.id == "_venv_python"]
    assert len(callers) >= 3          # _org_tool_names, _build("org"), main()'s refusal message


def test_missing_wiki_roots_degrade_instead_of_crashing(monkeypatch, tmp_path):
    cfg = tmp_path / "wikis.yaml"
    cfg.write_text(
        "default: mooniex\nwikis:\n"
        "  - ns: org\n    name: Org\n    path: /Users/nobody/MoonieXHQ/Agents/Rules\n"
        "  - ns: mooniex\n    name: MoonieX\n    path: /Users/nobody/MoonieXHQ/Agents/Wikis\n",
        encoding="utf-8")
    for var in ("WIKI_ROOT", "WIKI_ROOT_ORG", "WIKI_ROOT_MOONIEX"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(wiki, "WIKIS_CONFIG", cfg)
    wiki._registry.cache_clear()
    wiki._roots.cache_clear()
    try:
        assert wiki._available_roots() == []
        with pytest.raises(wiki.WikiError, match="not available in this environment"):
            wiki.wiki_read("org:IRON-RULES.md")
        with pytest.raises(wiki.WikiError, match="not available in this environment"):
            wiki.wiki_list("")
    finally:
        wiki._registry.cache_clear()
        wiki._roots.cache_clear()


# --------------------------------------------------------------------------
# text files: Windows reads with cp1252/cp874 unless told otherwise
# --------------------------------------------------------------------------

PORTABLE_FILES = FOUR_FILES + ("lib/proc.py", "lib/db.py", "lib/telegram_out.py", "lib/notify.py",
                               "lib/config.py", "tools/tmux_session.py",
                               "scripts/lib/cxo_mcp_config.py")


def _text_io_without_encoding(source: str) -> list[int]:
    """Lines of read_text/write_text and text-mode open() calls with no encoding=."""
    bare = []
    for n in ast.walk(ast.parse(source)):
        if not isinstance(n, ast.Call) or any(k.arg == "encoding" for k in n.keywords):
            continue
        if isinstance(n.func, ast.Attribute) and n.func.attr in ("read_text", "write_text"):
            if not (n.func.attr == "write_text" and len(n.args) > 1):   # positional data, encoding
                bare.append(n.lineno)
        elif isinstance(n.func, ast.Name) and n.func.id == "open":
            mode = n.args[1] if len(n.args) > 1 else next(
                (k.value for k in n.keywords if k.arg == "mode"), None)
            if not (isinstance(mode, ast.Constant) and "b" in str(mode.value)):
                bare.append(n.lineno)
    return bare


def test_the_encoding_check_can_see_a_bare_read():
    assert _text_io_without_encoding("p.read_text()") == [1]
    assert _text_io_without_encoding("p.write_text(s)") == [1]
    assert _text_io_without_encoding("open(p)") == [1]
    assert _text_io_without_encoding("open(p, 'w')") == [1]
    assert _text_io_without_encoding("p.read_text(encoding='utf-8')") == []
    assert _text_io_without_encoding("open(p, encoding='utf-8')") == []
    assert _text_io_without_encoding("open(p, 'rb')") == []


@pytest.mark.parametrize("rel", PORTABLE_FILES)
def test_no_text_read_or_write_without_an_encoding(rel):
    # config/*.yaml and the state files carry Thai and typographic characters; a
    # bare read_text() decodes them with the locale codec and dies on winbox.
    bare = _text_io_without_encoding((ROOT / rel).read_text(encoding="utf-8"))
    assert bare == [], f"{rel}: text read/write without encoding= at lines {bare}"


def test_lib_config_loads_the_yaml_files_under_a_non_utf8_locale():
    # The measured failure: projects()/agents()/hosts() raised UnicodeDecodeError
    # ('ascii' codec can't decode byte 0xe2) because the yaml holds Thai and
    # typographic characters.
    code = ("import json, locale, sys; sys.path.insert(0, %r);"
            "import lib.config as c;"
            "print(json.dumps({'enc': locale.getpreferredencoding(False),"
            " 'projects': len(c.projects()), 'agents': len(c.agents()),"
            " 'hosts': len(c.hosts())}))" % str(ROOT))
    env = {**os.environ, "LC_ALL": "C", "LANG": "C", "PYTHONCOERCECLOCALE": "0",
           "PYTHONUTF8": "0", "ORG_NOTIFY_SILENT": "1"}
    r = subprocess.run([sys.executable, "-X", "utf8=0", "-c", code], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["enc"].lower().replace("-", "").replace("_", "") in ("usascii", "ascii", "ansix3.41968"), out
    assert out["projects"] == len(config.projects())
    assert out["agents"] == len(config.agents())
    assert out["hosts"] == len(config.hosts())


def test_delegate_reads_its_policy_file_under_a_non_utf8_locale():
    # storage-policy.yaml has non-ASCII bytes; _scope_owners used to let the
    # UnicodeDecodeError escape (it only catches OSError and YAMLError).
    code = ("import json, locale, sys; sys.path.insert(0, %r);"
            "import tools.delegate as d;"
            "print(json.dumps({'enc': locale.getpreferredencoding(False),"
            " 'floor': d._disk_orange_floor_gb(), 'owners': d._scope_owners('__no_such_feature__')}))"
            % str(ROOT))
    env = {**os.environ, "LC_ALL": "C", "LANG": "C", "PYTHONCOERCECLOCALE": "0",
           "PYTHONUTF8": "0", "ORG_NOTIFY_SILENT": "1"}
    r = subprocess.run([sys.executable, "-X", "utf8=0", "-c", code], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["enc"].lower().replace("-", "").replace("_", "") in ("usascii", "ascii", "ansix3.41968"), out
    assert out["floor"] == delegate._disk_orange_floor_gb()
    assert out["owners"] is None
