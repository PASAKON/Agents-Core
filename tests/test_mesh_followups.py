"""Org Mesh follow-ups (task-3bf2da7c) from the W2.7 and W4.4 reviews.

1. queued_remote retry cap: a row whose host never answers is failed at
   ORG_MESH_MAX_ATTEMPTS (default 12), its path locks released, the owner told
   once. The attempt count is per task and exact, not a window over the ledger.
2. deliver_letter timeout: long enough for the Windows wake
   (agent_transport.wake_windows_tab, ~30 s worst case) plus the write, so a
   slow wake is not read as an unreachable host for a letter already on disk.

(3, runner_claude on macOS, lives in tests/test_w44_probe_provides.py.)

Fakes only. mesh.dispatch is a scripted stand-in (no ssh leaves this process),
lib.db points at a tmp_path SQLite ledger, and the owner letter and the
notifier are recorders.

Run:  .venv/bin/python -m pytest tests/test_mesh_followups.py
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, mesh  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import notify as notify_mod  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
from tools import agent_transport  # noqa: E402
from tools import delegate  # noqa: E402
from tools import send_to_cto  # noqa: E402

PROJECT = "mooniex-agents"
TOUCH = ["lib/mesh.py"]


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "mac")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(mesh.ENV_FLAG, "1")
    monkeypatch.delenv("ORG_MESH_MAX_ATTEMPTS", raising=False)
    # error()/warn() would run osascript on the Mac: record, never notify.
    monkeypatch.setattr(notify_mod, "notify", lambda *a, **kw: None)
    config.self_host.cache_clear()
    yield
    config.self_host.cache_clear()


class Letters:
    """send_to_cto.send, recorded: the owner mailbox is never really written."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *a, **kw):
        self.calls.append((a, kw))
        return True


@pytest.fixture()
def letters(monkeypatch) -> Letters:
    rec = Letters()
    monkeypatch.setattr(send_to_cto, "send", rec)
    return rec


class Dial:
    """mesh.dispatch: every call is recorded, then the host is silent."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, host, verb, *args, timeout=None):
        self.calls.append((host, verb, args))
        raise mesh.MeshUnreachable(f"{verb} on {host}: no route")


@pytest.fixture()
def dial(monkeypatch) -> Dial:
    d = Dial()
    monkeypatch.setattr(mesh, "dispatch", d)
    return d


def _task(touches=None, owner=("abcd1234", "cto")) -> str:
    tid = db_mod.create_task(PROJECT, "developer", "t", "d", touches=touches,
                             owner_cto=owner[0], owner_role=owner[1])
    if touches:
        ok, _, _ = db_mod.lock_paths(tid, PROJECT, touches)
        assert ok
    return tid


def _queued(tid: str, attempts: int, host: str = "contabo") -> None:
    """A row that has been unreachable `attempts` times: that many
    `status_queued_remote` events, exactly as mesh_spawn_worker writes them."""
    for _ in range(attempts):
        db_mod.update_status(tid, "queued_remote", host=host, actor="cto",
                             delegate_log="mesh spawn_worker unreachable")


def _lock_keys(tid: str) -> list[str]:
    with db_mod.get_conn() as conn:
        rows = conn.execute("SELECT key FROM locks WHERE owner=?", (tid,)).fetchall()
    return sorted(r["key"] for r in rows)


# ---------------------------------------------------------------------------
# 1. the cap: constant, env override, bad values
# ---------------------------------------------------------------------------

def test_the_default_cap_is_twelve_and_fits_the_watchdog_tick():
    assert mesh.MAX_ATTEMPTS == 12
    assert mesh.max_attempts() == 12
    # 12 attempts = the first at delegate time + 11 watchdog passes: about an
    # hour at the 300 s tick. Pinned so a change to either number is deliberate.
    assert watchdog.INTERVAL_S == 300
    assert (mesh.max_attempts() - 1) * watchdog.INTERVAL_S == 55 * 60


@pytest.mark.parametrize("value,expected", [
    ("3", 3), (" 5 ", 5), ("1", 1),
    ("0", 12), ("-4", 12), ("", 12), ("many", 12), ("2.5", 12),
])
def test_the_env_override_is_read_and_a_bad_value_never_means_unlimited(monkeypatch, value, expected):
    monkeypatch.setenv("ORG_MESH_MAX_ATTEMPTS", value)
    assert mesh.max_attempts() == expected


# ---------------------------------------------------------------------------
# 1. the cap, through the watchdog
# ---------------------------------------------------------------------------

def test_a_row_at_the_cap_is_failed_not_dialled_again(dial, letters):
    tid = _task(touches=TOUCH)
    _queued(tid, 12)
    assert delegate._queued_remote_attempts(tid) == 12

    out = watchdog._retry_queued_remote()

    assert out == [{"task": tid, "host": "contabo", "status": "failed"}]
    assert dial.calls == []  # the cap stops the dial, it does not spend one more
    row = db_mod.get_task(tid)
    assert row["status"] == "failed"
    assert "contabo" in row["delegate_log"] and "12" in row["delegate_log"]
    assert "ORG_MESH_MAX_ATTEMPTS" in row["delegate_log"]
    assert db_mod.list_tasks(status="queued_remote") == []


def test_a_row_under_the_cap_is_still_retried(dial, letters):
    tid = _task()
    _queued(tid, 11)
    out = watchdog._retry_queued_remote()
    assert dial.calls == [("contabo", "spawn_worker", (tid,))]
    assert out == [{"task": tid, "host": "contabo", "status": "queued_remote"}]
    assert db_mod.get_task(tid)["status"] == "queued_remote"
    assert letters.calls == []


def test_the_twelfth_failed_attempt_is_the_last_one(dial, letters):
    """End to end from attempt 1: 12 dials, then the next pass fails the row
    without a 13th."""
    tid = _task()
    _queued(tid, 1)  # attempt 1, at delegate time
    for _ in range(11):  # attempts 2..12
        assert watchdog._retry_queued_remote()[0]["status"] == "queued_remote"
    assert len(dial.calls) == 11
    assert delegate._queued_remote_attempts(tid) == 12
    assert watchdog._retry_queued_remote()[0]["status"] == "failed"
    assert len(dial.calls) == 11  # no 13th dial
    assert db_mod.get_task(tid)["status"] == "failed"


def test_the_env_override_moves_the_cap(monkeypatch, dial, letters):
    monkeypatch.setenv("ORG_MESH_MAX_ATTEMPTS", "3")
    tid = _task()
    _queued(tid, 3)
    assert watchdog._retry_queued_remote() == [
        {"task": tid, "host": "contabo", "status": "failed"}]
    assert dial.calls == []


def test_the_path_locks_are_released_like_a_failed_launcher_run(dial, letters):
    tid = _task(touches=TOUCH)
    _queued(tid, 12)
    assert _lock_keys(tid), "queued_remote must hold the path locks while it waits"
    assert db_mod.find_conflicts(PROJECT, TOUCH)  # a second task would be blocked

    watchdog._retry_queued_remote()

    assert _lock_keys(tid) == []
    assert db_mod.find_conflicts(PROJECT, TOUCH) == []  # free for the next task


def test_the_owner_hears_once_not_once_per_pass(dial, letters):
    tid = _task()
    _queued(tid, 12)
    watchdog._retry_queued_remote()
    watchdog._retry_queued_remote()
    watchdog._retry_queued_remote()
    assert len(letters.calls) == 1
    args, kw = letters.calls[0]
    assert args[0] == tid
    assert "contabo" in args[1] and "12" in args[1]
    assert kw["cto_id"] == "abcd1234" and kw["owner_role"] == "cto"


def test_a_failed_owner_letter_does_not_undo_the_failure(monkeypatch, dial):
    def boom(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr(send_to_cto, "send", boom)
    tid = _task(touches=TOUCH)
    _queued(tid, 12)
    out = watchdog._retry_queued_remote()
    assert out[0]["status"] == "failed"
    assert _lock_keys(tid) == []


def test_the_failure_is_raised_through_the_error_path_once(monkeypatch, dial, letters):
    seen: list[str] = []
    monkeypatch.setattr(delegate, "error", lambda msg, *a, **kw: seen.append(msg))
    tid = _task()
    _queued(tid, 12)
    watchdog._retry_queued_remote()
    watchdog._retry_queued_remote()
    assert len(seen) == 1 and tid in seen[0] and "contabo" in seen[0]


def test_a_row_someone_else_already_moved_is_not_failed_or_announced(dial, letters):
    """Give-up only acts on a row still waiting. A far side that moved it (or a
    second watchdog that got there first) must not get a `failed` on top."""
    tid = _task()
    _queued(tid, 12)
    db_mod.update_status(tid, "in_progress", pid=4242, host="contabo", actor="test")
    row = delegate.give_up_queued_remote(tid, "contabo", 12)
    assert row["status"] == "in_progress"
    assert letters.calls == []


def test_one_row_at_the_cap_does_not_stop_the_others(dial, letters):
    capped = _task()
    _queued(capped, 12)
    fresh = _task()
    _queued(fresh, 1)
    out = watchdog._retry_queued_remote()
    assert {(o["task"], o["status"]) for o in out} == {
        (capped, "failed"), (fresh, "queued_remote")}
    assert dial.calls == [("contabo", "spawn_worker", (fresh,))]


# ---------------------------------------------------------------------------
# 1. the count is per task and exact
# ---------------------------------------------------------------------------

def test_the_attempt_count_ignores_other_tasks_however_busy_the_ledger(dial, letters):
    """recent_events(limit=500) over a busy ledger: 600 newer events from other
    tasks must not bury this task's attempts."""
    tid = _task()
    _queued(tid, 4)
    noisy = _task()
    for i in range(600):
        db_mod.set_fields(noisy, actor="noise", delegate_log=f"noise {i}")
    assert delegate._queued_remote_attempts(tid) == 4
    assert delegate._queued_remote_attempts(noisy) == 0


def test_the_attempt_count_survives_a_task_with_hundreds_of_other_events(dial, letters):
    """The same task logging 600 unrelated events after its attempts: a window
    of 500 would read 0 and a dead host would never hit the cap."""
    tid = _task()
    _queued(tid, 12)
    for i in range(600):
        db_mod.set_fields(tid, actor="noise", delegate_log=f"noise {i}")
    assert delegate._queued_remote_attempts(tid) == 12
    assert watchdog._retry_queued_remote()[0]["status"] == "failed"


# ---------------------------------------------------------------------------
# 2. deliver_letter timeout
# ---------------------------------------------------------------------------

def test_deliver_letter_has_its_own_timeout():
    assert "deliver_letter" in mesh.VERB_TIMEOUT_S


def test_deliver_letter_outlasts_the_windows_wake_plus_the_write():
    wake_worst = agent_transport.WAKE_WORST_CASE_S
    assert wake_worst >= 30  # schtasks /run 15 s + the result wait 15 s
    # the ssh dial, then the far side runs the wake, then the write
    assert mesh.VERB_TIMEOUT_S["deliver_letter"] > mesh.CONNECT_TIMEOUT_S + wake_worst
    assert mesh.VERB_TIMEOUT_S["deliver_letter"] > mesh.DEFAULT_TIMEOUT_S


def test_the_wake_worst_case_is_built_from_the_numbers_the_wake_really_uses(tmp_path):
    """WAKE_WORST_CASE_S is not a second copy of a number: the schtasks timeout
    and the result wait the wake runs with are the two terms of it."""
    seen = {}

    def run(argv, **kw):
        seen["timeout"] = kw.get("timeout")
        return subprocess.CompletedProcess(argv, 1, "", "no task")

    agent_transport.wake_windows_tab("cto-2c6b9f03", "CTO", wake_dir=tmp_path, run=run,
                                     sleep=lambda s: None)
    wait_default = inspect.signature(agent_transport.wake_windows_tab).parameters["wait_s"].default
    assert seen["timeout"] == agent_transport._WAKE_RUN_TIMEOUT_S
    assert wait_default == agent_transport._WAKE_WAIT_S
    assert agent_transport.WAKE_WORST_CASE_S == seen["timeout"] + wait_default


def test_mesh_dispatch_gives_deliver_letter_that_timeout(monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(kw)
        return subprocess.CompletedProcess(argv, 0, '{"ok": true, "verb": "deliver_letter"}\n', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    mesh.dispatch("contabo", "deliver_letter", "42")
    assert calls[0]["timeout"] == mesh.VERB_TIMEOUT_S["deliver_letter"]


def test_a_slow_wake_inside_the_timeout_is_a_reply_not_an_unreachable_host(monkeypatch):
    """The far side took longer than the old 30 s default and answered: the
    caller gets the reply. (A TimeoutExpired is what the old default raised.)"""
    limit = mesh.VERB_TIMEOUT_S["deliver_letter"]
    took = agent_transport.WAKE_WORST_CASE_S + 1  # wake at its worst, plus the write

    def fake_run(argv, **kw):
        if took > kw["timeout"]:
            raise subprocess.TimeoutExpired(argv, kw["timeout"])
        return subprocess.CompletedProcess(argv, 0, '{"ok": true, "verb": "deliver_letter"}\n', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert limit > took
    assert mesh.dispatch("contabo", "deliver_letter", "42")["ok"] is True


# ---------------------------------------------------------------------------
# 3. runner_claude on macOS: signed in without reading the secret
# ---------------------------------------------------------------------------

import ast  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402

from tools import node_dispatch as nd  # noqa: E402

CLAUDE = "/fake/bin/claude"
SECURITY = "/usr/bin/security"
SERVICE = "Claude Code-credentials"
SECRET = "sk-ant-oat01-SECRET-TOKEN-BODY"
EMAIL = "someone@example.invalid"
# a flag that would make `security` print the password: -w (only), -g (to stderr),
# alone or bundled with others (-gw, -ag ...)
_SECRET_FLAG = re.compile(r"-[A-Za-z]*[wg][A-Za-z]*")


def _status(logged_in) -> str:
    return json.dumps({"loggedIn": logged_in, "authMethod": "claude.ai",
                       "email": EMAIL, "orgName": "Some Org", "subscriptionType": "max"})


class Children:
    """subprocess.run, replaced. `table` maps argv[0] to (exit code, stdout) or an
    exception. A child that was not planned is recorded and then fails the test
    (nd swallows the AssertionError into probe_errors, so `calls` is the witness)."""

    def __init__(self) -> None:
        self.table: dict[str, object] = {}
        self.calls: list[tuple[list, dict]] = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        hit = self.table.get(argv[0])
        if hit is None:
            raise AssertionError(f"unplanned child process: {argv}")
        if isinstance(hit, BaseException):
            raise hit
        code, out = hit
        return subprocess.CompletedProcess(
            argv, code, out if kw.get("stdout") == subprocess.PIPE else None, None)

    @property
    def argvs(self) -> list[list]:
        return [c[0] for c in self.calls]


class Mac:
    def __init__(self, monkeypatch, tmp_path: Path, os_name: str = "darwin") -> None:
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.children = Children()
        self.on_path: dict[str, str] = {}
        monkeypatch.setenv("HOME", str(self.home))
        monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
        monkeypatch.setattr(nd.shutil, "which", lambda name, *a, **kw: self.on_path.get(name))
        monkeypatch.setattr(subprocess, "run", self.children)
        monkeypatch.setattr(nd, "_os_name", lambda: os_name)
        monkeypatch.setattr(nd, "_is_windows", lambda: os_name == "windows")

    def cli(self, code: int, out: str) -> None:
        self.on_path["claude"] = CLAUDE
        self.children.table[CLAUDE] = (code, out)

    def keychain(self, code: int) -> None:
        self.children.table[SECURITY] = (code, f"attributes... password: {SECRET}")


@pytest.fixture()
def mac(monkeypatch, tmp_path) -> Mac:
    return Mac(monkeypatch, tmp_path)


def test_the_cli_says_signed_in(mac):
    mac.cli(0, _status(True))
    assert nd._claude_signed_in() is True
    assert mac.children.argvs == [[CLAUDE, "auth", "status", "--json"]]  # the Keychain is not asked


def test_the_cli_says_signed_out_and_that_answer_stands(mac):
    mac.cli(1, _status(False))
    mac.keychain(0)  # an item is there, but the CLI knows better
    assert nd._claude_signed_in() is False
    assert mac.children.argvs == [[CLAUDE, "auth", "status", "--json"]]


def test_without_the_cli_the_keychain_item_answers(mac):
    mac.keychain(0)
    assert nd._claude_signed_in() is True
    assert mac.children.argvs == [[SECURITY, "find-generic-password", "-s", SERVICE]]
    mac.children.calls.clear()
    mac.keychain(44)  # errSecItemNotFound
    assert nd._claude_signed_in() is False


@pytest.mark.parametrize("cli_answer", [
    subprocess.TimeoutExpired([CLAUDE, "auth", "status"], 5),  # hung
    OSError("exec format error"),                              # would not start
    (2, "error: unknown command 'auth'"),                      # an older CLI
    (0, "not json at all"),
    (0, "[]"),
    (0, json.dumps({"loggedIn": "yes"})),                      # not a boolean
    (0, json.dumps({"authMethod": "none"})),                   # no loggedIn
])
def test_a_cli_that_cannot_answer_falls_back_to_the_keychain(mac, cli_answer):
    mac.on_path["claude"] = CLAUDE
    mac.children.table[CLAUDE] = cli_answer
    mac.keychain(0)
    assert nd._claude_signed_in() is True
    assert mac.children.argvs[-1] == [SECURITY, "find-generic-password", "-s", SERVICE]


def test_a_custom_config_dir_is_not_judged_by_the_default_keychain_item(mac, monkeypatch, tmp_path):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / ".credentials.json").write_text("x", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    mac.keychain(0)  # the default login is someone else's
    assert nd._claude_signed_in() is True  # the file check answers for this dir
    assert SECURITY not in [a[0] for a in mac.children.argvs]
    (cfg / ".credentials.json").unlink()
    assert nd._claude_signed_in() is False


@pytest.mark.parametrize("os_name", ["linux", "windows"])
def test_linux_and_windows_keep_the_credentials_file_check(monkeypatch, tmp_path, os_name):
    box = Mac(monkeypatch, tmp_path, os_name)
    assert nd._claude_signed_in() is False
    cred = box.home / ".claude" / ".credentials.json"
    cred.parent.mkdir()
    cred.write_text("", encoding="utf-8")
    assert nd._claude_signed_in() is False  # empty file: not a login
    cred.write_text(SECRET, encoding="utf-8")
    assert nd._claude_signed_in() is True
    assert box.children.calls == []  # no claude, no security, no child at all


@pytest.mark.parametrize("setup", [
    lambda m: (m.cli(0, _status(True))),
    lambda m: (m.cli(1, _status(False))),
    lambda m: (m.keychain(0)),
    lambda m: (m.keychain(44)),
    lambda m: (m.on_path.update(claude=CLAUDE), m.children.table.update({CLAUDE: (0, "junk")}), m.keychain(0)),
])
def test_no_child_ever_gets_a_flag_that_prints_the_secret(mac, setup):
    setup(mac)
    nd._claude_signed_in()
    assert mac.children.argvs, "a detector that asks nothing proves nothing"
    for argv in mac.children.argvs:
        assert [a for a in argv[1:] if _SECRET_FLAG.fullmatch(a)] == [], argv


def test_the_keychain_child_output_is_never_captured(mac):
    mac.keychain(0)
    nd._claude_signed_in()
    (argv, kw), = mac.children.calls
    assert argv[0] == SECURITY
    assert kw["stdout"] == subprocess.DEVNULL and kw["stderr"] == subprocess.DEVNULL
    assert kw["timeout"] == nd.PROBE_CHILD_TIMEOUT_S
    assert kw["stdin"] == subprocess.DEVNULL
    assert "shell" not in kw or kw["shell"] is False


def test_the_cli_child_is_bounded_and_its_stderr_is_dropped(mac):
    mac.cli(0, _status(True))
    nd._claude_signed_in()
    (argv, kw), = mac.children.calls
    assert kw["timeout"] == nd.PROBE_CHILD_TIMEOUT_S
    assert kw["stderr"] == subprocess.DEVNULL and kw["stdin"] == subprocess.DEVNULL


def test_neither_the_secret_nor_the_cli_identity_reaches_the_probe_answer(mac, monkeypatch):
    mac.cli(0, _status(True))
    measured, errors = nd._measure_provides()
    assert "runner_claude" in measured and "macos" in measured
    assert errors == []
    blob = json.dumps([measured, errors])
    assert EMAIL not in blob and SECRET not in blob and "Some Org" not in blob


def test_a_keychain_child_that_hangs_is_named_once_and_is_not_a_login(mac):
    mac.children.table[SECURITY] = subprocess.TimeoutExpired([SECURITY], 5)
    measured, errors = nd._measure_provides()
    assert "runner_claude" not in measured
    assert errors == ["runner_claude: TimeoutExpired"]


def test_node_dispatch_source_has_no_flag_that_prints_a_secret():
    """Any -w / -g style flag string in this module is a way for `security` to
    print the password. There is none today; adding one fails here."""
    tree = ast.parse((ROOT / "tools" / "node_dispatch.py").read_text(encoding="utf-8"))
    flags = sorted(n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and _SECRET_FLAG.fullmatch(n.value))
    assert flags == []


def test_the_macos_detector_source_never_opens_or_reads_a_file():
    tree = ast.parse((ROOT / "tools" / "node_dispatch.py").read_text(encoding="utf-8"))
    names = {"_claude_logged_in_per_cli", "_claude_signed_in"}
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {f.name for f in funcs} == names
    bad = []
    for fn in funcs:
        for call in (c for c in ast.walk(fn) if isinstance(c, ast.Call)):
            f = call.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in ("open", "read_text", "read_bytes"):
                bad.append(name)
    assert bad == []
