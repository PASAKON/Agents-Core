"""tools/rename_service.py (M10b, Agents-Core #272): a session's rename request is
typed as exactly one "/rename <rule name>" line, only into that session's empty
prompt, and only when the process asking descends from that session (§2b review of
#283). tmux is a fake that records every call; the session records point at this
test's own pid, so this process and its children count as the session."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

from lib import config
from tools import live_sessions as ls
from tools import rename_service as rs

CONTABO = "\U0001F310"
MAC = "\U0001F4BB"
U_CTO = "00000000-0000-0000-0000-0000c34459eb"
U_PH = "00000000-0000-0000-0000-000036c49776"
U_COO = "00000000-0000-0000-0000-0000fde4c4ca"
RULE = "─" * 50
# The layout a real Claude pane shows (14 Oct, 50 columns): rules above and below the box.
EMPTY = f"out\n{RULE}\n❯ \n{RULE}\n  ⏵⏵ auto mode on (shift+tab to cycle) · esc to…\n"
FRESH = f"out\n{RULE}\n❯ Try \"fix lint errors\"\n{RULE}\n  ? for shortcuts\n"
DRAFT = f"out\n{RULE}\n❯ half a sentence the CEO is typing\n{RULE}\n"
DRAFT_BELOW = f"out\n{RULE}\n❯ \n  second row of a draft (Shift+Enter first)\n{RULE}\n"
BUSY = f"out\n✽ Computing… (11s · ↓ 302 tokens · thinking)\n{RULE}\n❯ \n{RULE}\n  esc to interrupt\n"
PERMISSION = " Do you want to proceed?\n ❯ 1. Yes\n   2. No\n❯ \n"


class FakeTmux:
    """Root's tmux server: every pane of every session has this test's pid (so this
    process is "in" each session) unless `panes` says otherwise. Typed text shows
    on the ❯ line; Enter clears it."""

    def __init__(self):
        self.screens, self.calls, self.sent, self.panes = {}, [], [], {}
        self.box = {}               # what is in each input box
        self.width = 200            # the pane width the box wraps at
        self.lag = 0                # captures that still show the screen from before the typing
        self.after_capture = None   # called after each capture-pane (a CEO typing)
        self.after_type = None      # called after the literal send (a key pressed right then)
        self._old = {}

    def draw(self, name):
        text, w = self.box.get(name, ""), self.width - 4
        rows = [text[i:i + w] for i in range(0, len(text), w)] or [""]
        rule = "─" * self.width
        self.screens[name] = "\n".join(["out", rule, "│ ❯ " + rows[0] + " │",
                                         *("│   " + r + " │" for r in rows[1:]), rule, "  ? for shortcuts", ""])

    def __call__(self, *args):
        self.calls.append(args)
        t = args[args.index("-t") + 1]
        assert t.startswith("=") and t.endswith(":"), f"not an exact target: {t}"
        name, out = t[1:-1], ""
        if args[0] == "capture-pane":
            if self._old.get(name, 0) > 0:          # the TUI has not redrawn yet
                self._old[name] -= 1
                out = EMPTY
            else:
                out = self.screens.get(name, EMPTY)
            if self.after_capture:
                self.after_capture(self)
        elif args[0] == "list-panes":
            out = "".join(f"{pid}\n" for pid in self.panes.get(name, [os.getpid()]))
        elif args[0] == "send-keys":
            self.sent.append((name, args[-1]))
            if "-l" in args:
                self.box[name] = self.box.get(name, "") + args[-1]
                self._old[name] = self.lag
                if self.after_type:
                    self.after_type(self, name)
            elif args[-1] == "BSpace":
                n = int(args[args.index("-N") + 1]) if "-N" in args else 1
                self.box[name] = self.box.get(name, "")[:-n]
            else:                                    # Enter submits the box
                self.box[name] = ""
            self.draw(name)
        else:
            raise AssertionError(f"tmux {args[0]} is never used: {args}")
        return subprocess.CompletedProcess(["tmux", *args], 0, out, "")


@pytest.fixture
def box(tmp_path, monkeypatch):
    sessions, locks = tmp_path / "s", tmp_path / "locks"
    for d in (sessions, locks):
        d.mkdir()
    monkeypatch.setattr(ls, "session_dirs", lambda host: [sessions])
    for mod in (rs, ls):
        monkeypatch.setattr(mod, "LOCKS_DIR", locks)
    fake = FakeTmux()
    monkeypatch.setattr(rs, "tmux", fake)
    monkeypatch.setattr(rs, "TYPED_WAIT_S", 0.2)
    monkeypatch.setattr(rs, "TYPED_POLL_S", 0.01)
    monkeypatch.setattr(rs, "_DECIDED", {})          # the sweep's memory is per test
    monkeypatch.setattr(rs, "_NOTED", {})
    n = [0]
    pending = {}

    def record(uuid, name, tmux, pid=None, **extra):
        n[0] += 1
        pid = pid or os.getpid()
        f = sessions / f"{n[0]}.json"
        f.write_text(json.dumps({"pid": pid, "sessionId": uuid, "name": name, "tmux": tmux,
                                 "procStart": str(ls._proc_starttime(pid)), **extra}))
        return f

    def request(box_name, topic, prefix="", peer=None):
        """A request from this test process (a descendant of every record's pid)."""
        role, sid = box_name.rsplit("-", 1)
        a, b = socket.socketpair()
        with a, b:
            a.sendall(json.dumps({"role": role, "sid": sid, "topic": topic, "prefix": prefix}).encode())
            a.shutdown(socket.SHUT_WR)
            return rs.handle(b, "contabo", pending, peer or (os.getpid(), os.getuid()))

    record(U_CTO, "CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto-c34459eb:@1.%1")
    record(U_PH, "PH#36c (CMO) - MimiPage — MimiPage", "project_head-36c49776:@2.%2")
    record(U_COO, "COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong)", "sompong:@3.%3")
    (locks / "project_head-36c49776.project").write_text("MimiPage")
    (locks / "project_head-36c49776.spawned_by").write_text("cxo:cmo:ef04792e")
    fake.record, fake.request, fake.locks, fake.sessions, fake.pending = record, request, locks, sessions, pending
    return fake


@pytest.mark.parametrize("topic", [
    "ok\n/permissions",                      # a newline would be Enter, then a new command
    "\n/exit",
    "x\r/exit",
    "\x1b[201~\x1b[200~/exit\x1b",           # bracketed-paste / ESC sequences
    "/model opus",                           # a leading slash
    "a /exit b\u0085c",           # unicode line separators
    "‮ evil ​ zero width",        # bidi / format characters
    "\t/exit",
    "x" * 500,
    "$(touch /tmp/pwned) `id` ; | > <",      # shell / tmux key names stay literal text
])
def test_no_payload_in_a_topic_reaches_the_pane_beyond_one_rename_line(box, topic):
    box.request("cto-c34459eb", topic)
    rs.once("contabo", box.pending, now=1000.0)
    typed = [t for _, t in box.sent if t not in ("Enter", "BSpace")]
    assert len(typed) == 1 and [t for _, t in box.sent].count("Enter") == 1
    line = typed[0]
    assert line.startswith(f"/rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin)")
    assert line.count("/") == 1 + line[len("/rename "):].count("/")    # only the command's own slash leads
    assert not any(ord(c) < 32 or 0x7f <= ord(c) < 0xa0 or c in "  ‮​\u0085" for c in line)
    assert len(line) <= len("/rename ") + rs.NAME_MAX
    topic_part = line.split(" — ", 1)[1] if " — " in line else ""
    assert not topic_part.startswith("/") and len(topic_part) <= rs.TOPIC_MAX + 1
    assert all(c[0] in ("capture-pane", "send-keys", "list-panes") for c in box.calls)


def test_it_types_only_into_an_empty_prompt_and_retries_later(box):
    box.request("cto-c34459eb", "next job")
    for screen, why in ((DRAFT, "prompt not empty"), (PERMISSION, "choice prompt up")):
        box.screens["cto-c34459eb"] = screen
        assert rs.once("contabo", box.pending, now=1000.0) == [f"wait     cto-c34459eb: {why}"]
        assert box.sent == []
    box.screens["cto-c34459eb"] = EMPTY
    assert rs.once("contabo", box.pending, now=1000.0) == [f"renamed  cto-c34459eb: {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — next job"]
    assert box.sent == [("cto-c34459eb", f"/rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — next job"),
                        ("cto-c34459eb", "Enter")]


def test_a_landed_rename_ends_the_request_and_one_that_did_not_is_sent_again(box):
    box.request("cto-c34459eb", "t")
    rs.once("contabo", box.pending, now=1000.0)
    assert rs.once("contabo", box.pending, now=1010.0) == ["sent     cto-c34459eb: waiting for it to land"]
    rs.once("contabo", box.pending, now=1000.0 + rs.RETRY_S + 1)
    assert len([t for _, t in box.sent if t != "Enter"]) == 2
    for f in box.sessions.iterdir():                     # now it landed
        d = json.loads(f.read_text())
        if d["sessionId"] == U_CTO:
            d["name"] = f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — t"
            f.write_text(json.dumps(d))
    assert rs.once("contabo", box.pending, now=5000.0) == [f"done     cto-c34459eb: {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — t"]
    assert box.pending == {}


def test_it_types_into_that_sessions_pane_only(box):
    box.request("project_head-36c49776", "MimiPage")
    rs.once("contabo", box.pending, now=1.0)
    assert box.sent[0] == ("project_head-36c49776", f"/rename {CONTABO} PH#36c (CMO) - MimiPage")
    box.sent.clear()
    # no session of that id: refused at the socket, nothing typed anywhere
    assert box.request("cto-aaaaaaaa", "x") == "refused: no single live session for cto-aaaaaaaa in its tmux"
    rs.once("contabo", box.pending, now=1.0)
    assert box.sent == []


def test_the_coo_needs_its_launcher_uuid_file(box):
    assert box.request("coo-fde4c4ca", "x").startswith("refused: no single live session")
    (box.locks / "coo-fde4c4ca.uuid").write_text(U_COO)
    assert box.request("coo-fde4c4ca", "x").startswith("queued")
    rs.once("contabo", box.pending, now=1.0)
    assert box.sent[0] == ("sompong", f"/rename {CONTABO} COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong) — x")


@pytest.mark.parametrize("box_name,body", [
    ("developer-afe57b21", {"topic": "x"}),                      # workers have no requests
    ("cto-c34459eb", {"topic": "x", "prefix": "/exit"}),         # prefix outside the set
    ("../cto-c34459eb", {"topic": "x"}),
])
def test_requests_with_no_rule_name_are_refused(box, box_name, body):
    role, sid = box_name.rsplit("-", 1)
    a, b = socket.socketpair()
    with a, b:
        a.sendall(json.dumps({"role": role, "sid": sid, **body}).encode())
        a.shutdown(socket.SHUT_WR)
        assert rs.handle(b, "contabo", box.pending, (os.getpid(), os.getuid())).startswith("refused")
    rs.once("contabo", box.pending, now=1.0)
    assert box.sent == [] and box.pending == {}


@pytest.mark.parametrize("raw", [b"x" * (rs.REQUEST_MAX + 1), b"\xff\xfe", b"[1, 2]", b""])
def test_a_huge_or_unreadable_request_is_refused(box, raw):
    a, b = socket.socketpair()
    with a, b:
        a.sendall(raw)
        a.shutdown(socket.SHUT_WR)
        assert rs.handle(b, "contabo", box.pending, (os.getpid(), os.getuid())) == "refused: unreadable request"
    assert box.pending == {}


# --- who may ask (§2b review of #283, BLOCKING 2) ---------------------------------------

@pytest.fixture
def stranger():
    """A live process other than this test, used as another session's Claude pid."""
    p = subprocess.Popen(["sleep", "300"])
    yield p.pid
    p.kill()
    p.wait()


def test_another_session_cannot_rename_this_one(box, stranger):
    # The CTO's session record belongs to another process: this test is not its descendant.
    box.record(U_CTO.replace("c34459eb", "dddddddd"), "CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto-dddddddd:@9.%9", pid=stranger)
    assert box.request("cto-dddddddd", "hijack") == (
        "refused: that session is not an ancestor of the caller (a session renames only itself)")
    rs.once("contabo", box.pending, now=1.0)
    assert box.sent == []


def test_a_caller_with_no_session_is_refused(box):
    # e.g. the `secretary` service user: its process descends from no session record.
    # This test's parent is outside the session (whose Claude pid is this test's pid).
    assert box.request("cto-c34459eb", "x", peer=(os.getppid(), os.getuid())).startswith(
        "refused: that session is not an ancestor")
    assert box.pending == {}


def test_a_caller_running_as_another_user_is_refused(box):
    assert box.request("cto-c34459eb", "x", peer=(os.getpid(), os.geteuid() + 1)) == (
        "refused: the caller runs as another user than that session")
    assert box.pending == {}


def test_a_child_process_of_the_session_may_ask(box):
    # session-rename.sh runs under the session's Bash tool: a grandchild of Claude.
    child = subprocess.Popen(["sleep", "300"])
    try:
        assert box.request("cto-c34459eb", "x", peer=(child.pid, os.getuid())).startswith("queued")
    finally:
        child.kill()
        child.wait()


def test_the_real_socket_reads_the_callers_pid_from_the_kernel(box, tmp_path):
    """End to end: a child process connects; SO_PEERCRED names it, and it is a
    descendant of this test's pid, the session record's pid."""
    sock = Path("/tmp") / f"rs-test-{os.getpid()}.sock"
    sock.unlink(missing_ok=True)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock))
    srv.listen(1)
    replies = []

    def serve_one():
        conn, _ = srv.accept()
        with conn:
            r = rs.handle(conn, "contabo", box.pending)
            replies.append(r)
            conn.sendall(r.encode())

    t = threading.Thread(target=serve_one)
    t.start()
    try:
        out = subprocess.run([sys.executable, "-c",
                              "import sys; sys.path.insert(0, sys.argv[1]);"
                              "from tools import rename_service as rs;"
                              "print(rs.send_request('cto', 'c34459eb', 'via socket', '', rs.Path(sys.argv[2])))",
                              str(rs.ROOT), str(sock)], capture_output=True, text=True, timeout=20)
        t.join(10)
    finally:
        srv.close()
        sock.unlink(missing_ok=True)
    assert out.stdout.strip() == f"queued cto-c34459eb: {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — via socket", out.stderr
    assert box.pending["cto-c34459eb"]["name"] == f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — via socket"


# --- robustness (§2b review of #283, MED) ------------------------------------------------

def test_a_draft_started_between_the_check_and_the_send_stops_it(box):
    box.request("cto-c34459eb", "x")

    def ceo_types(fake):
        fake.screens["cto-c34459eb"] = DRAFT     # after the first look, before the second
        fake.after_capture = None

    box.after_capture = ceo_types
    assert rs.once("contabo", box.pending, now=1.0) == ["wait     cto-c34459eb: prompt not empty"]
    assert box.sent == []
    assert len([c for c in box.calls if c[0] == "capture-pane"]) == 2


def test_a_tmux_error_on_one_rename_does_not_stop_the_others(box):
    box.request("cto-c34459eb", "x")
    box.request("project_head-36c49776", "MimiPage")
    real = rs.tmux

    def flaky(*args):
        if any("cto-c34459eb" in a for a in args):
            raise subprocess.TimeoutExpired("tmux", 10)
        return real(*args)

    rs.tmux = flaky
    try:
        out = rs.once("contabo", box.pending, now=1.0)
    finally:
        rs.tmux = real
    assert out[0].startswith("error    cto-c34459eb: TimeoutExpired")
    assert out[1].startswith("renamed  project_head-36c49776")
    assert "cto-c34459eb" not in box.pending


def test_a_restarted_session_drops_the_old_request(box, stranger):
    box.request("cto-c34459eb", "x")
    box.pending["cto-c34459eb"]["pid"] = stranger    # asked from an older Claude process
    assert rs.once("contabo", box.pending, now=1.0) == ["drop     cto-c34459eb: the session that asked has gone"]
    assert box.sent == []


def test_the_service_writes_no_file(box, tmp_path):
    before = sorted(p for p in tmp_path.rglob("*"))
    box.request("cto-c34459eb", "x")
    rs.once("contabo", box.pending, now=1.0)
    rs.once("contabo", box.pending, now=1.0 + rs.RETRY_S + 1)
    assert sorted(p for p in tmp_path.rglob("*")) == before


@pytest.fixture
def short_dir():
    """A socket path must fit sun_path (104 bytes on macOS, 108 on Linux). The Mac's
    pytest tmp_path (/var/folders/…/pytest-of-<user>/…/<test name>/) does not."""
    d = Path(tempfile.mkdtemp(prefix="rs-", dir="/tmp"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_listen_refuses_a_group_writable_socket_directory(short_dir):
    d = short_dir / "run"
    d.mkdir()
    d.chmod(0o775)
    with pytest.raises(SystemExit):
        rs.listen(d / "sock")
    d.chmod(0o755)
    srv = rs.listen(d / "sock")
    srv.close()
    assert oct((d / "sock").stat().st_mode & 0o777) == "0o666"


@pytest.mark.parametrize("raw,clean", [
    ("ดูแล org  ทั้งหมด", "ดูแล org ทั้งหมด"), ("a\nb", "a b"), ("//x", "x"), ("  ", ""),
    ("M10: names (ok) + #272", "M10: names (ok) + #272"), ("a\x1b[2Jb", "a 2Jb"),
    ("a; b;", "a b"),                       # tmux strips a trailing ';' from send-keys
])
def test_clean_topic(raw, clean):
    assert rs.clean_topic(raw) == clean


def test_preview_is_what_the_service_would_type(box, capsys):
    assert rs.main(["preview", "--role", "cto", "--sid", "c34459eb", "--topic", "x",
                    "--host", "contabo"]) == 0
    assert capsys.readouterr().out.strip() == f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x"
    assert rs.main(["preview", "--role", "developer", "--sid", "afe57b21", "--host", "contabo"]) == 1


# --- the Mac (M10c): no /proc, LOCAL_PEERPID + LOCAL_PEERCRED, launchd ------------------

def test_without_proc_ancestry_and_uid_come_from_ps(monkeypatch, tmp_path):
    with_proc = rs.ancestors(os.getpid())
    monkeypatch.setattr(rs, "PROC", tmp_path / "no-proc")
    assert rs.ancestors(os.getpid()) == with_proc
    assert rs._uid(os.getpid()) == os.getuid()
    gone = subprocess.Popen(["true"])
    gone.wait()
    assert rs._proc_info(gone.pid) is None


def test_the_darwin_peer_credentials_are_read_from_the_kernel_structs():
    pid_raw = (4242).to_bytes(4, sys.byteorder, signed=True)
    cred_raw = (0).to_bytes(4, sys.byteorder) + (501).to_bytes(4, sys.byteorder) + bytes(rs._XUCRED_SIZE - 8)
    assert rs.darwin_peer(pid_raw, cred_raw) == (4242, 501)


def test_tmux_is_found_where_launchd_cannot_see_it(monkeypatch):
    import tools.tmux_session as ts
    seen = []
    monkeypatch.setattr(ts, "tmux_bin", lambda: "/opt/homebrew/bin/tmux")
    monkeypatch.setattr(rs.subprocess, "run", lambda argv, **k: seen.append(argv) or
                        subprocess.CompletedProcess(argv, 0, "", ""))
    rs.tmux("capture-pane", "-p", "-t", "x")
    assert seen[0][0] == "/opt/homebrew/bin/tmux"


def test_listen_makes_its_missing_directory_private_to_this_user(short_dir):
    srv = rs.listen(short_dir / "new" / "sock")
    srv.close()
    st = (short_dir / "new").stat()
    assert st.st_uid == os.geteuid() and not st.st_mode & 0o022


def test_the_mac_launch_daemon_runs_this_service_as_the_sessions_user():
    import plistlib
    path = rs.ROOT / "deploy" / "launchd" / "com.mooniex.rename-service.plist"
    d = plistlib.loads(path.read_bytes())
    assert d["Label"] == path.stem
    assert d["UserName"] == "gob"                       # never root: see the plist comment
    core = "/Users/gob/MoonieXHQ/Agents/Core"
    assert d["ProgramArguments"] == [f"{core}/.venv/bin/python", f"{core}/tools/rename_service.py", "run"]
    assert d["WorkingDirectory"] == core
    assert d["EnvironmentVariables"]["HOME"] == "/Users/gob"
    assert d["EnvironmentVariables"]["ORG_HOST"] == "mac" and "mac" in ls._config().hosts()
    assert "/opt/homebrew/bin" in d["EnvironmentVariables"]["PATH"].split(":")
    assert d["KeepAlive"] is True and d["RunAtLoad"] is True

# --- §2b re-review of #283 (v2) ---------------------------------------------------------

def test_no_lock_file_is_read_for_a_caller_that_is_not_that_session(box, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("build_name ran before the owner check")

    monkeypatch.setattr(rs, "build_name", boom)
    monkeypatch.setattr(ls, "read_lock", boom)
    assert box.request("project_head-36c49776", "x", peer=(os.getppid(), os.getuid())).startswith(
        "refused: that session is not an ancestor")


@pytest.mark.parametrize("kind", ["dev-zero", "fifo", "big", "symlink-to-file"])
def test_a_planted_lock_file_is_never_followed_or_read_whole(box, kind, tmp_path):
    lock = box.locks / "project_head-36c49776.project"
    lock.unlink()
    if kind == "dev-zero":
        lock.symlink_to("/dev/zero")
    elif kind == "fifo":
        os.mkfifo(lock)
    elif kind == "big":
        lock.write_text("MimiPage" + " " * 300)
    else:
        (tmp_path / "token").write_text("MimiPage")
        lock.symlink_to(tmp_path / "token")
    t0 = time.monotonic()
    assert box.request("project_head-36c49776", "x") == "refused: no rule name for project_head-36c49776"
    assert time.monotonic() - t0 < 2
    (box.locks / "coo-fde4c4ca.uuid").symlink_to("/dev/zero")
    assert ls._launcher_uuid("coo", U_COO) is False


def test_a_lock_file_owned_by_another_user_is_not_trusted(box):
    if os.geteuid() != 0:
        pytest.skip("needs root to chown")
    os.chown(box.locks / "project_head-36c49776.project", 1001, -1)
    assert box.request("project_head-36c49776", "x") == "refused: no rule name for project_head-36c49776"


def test_a_record_written_by_another_user_speaks_for_no_session(box, monkeypatch):
    # sompong writes its own registry dir: a record naming a root pid is not his to write.
    real = rs._uid
    monkeypatch.setattr(rs, "_uid", lambda pid: os.geteuid() + 1 if pid == os.getpid() else real(pid))
    assert box.request("cto-c34459eb", "x").startswith("refused: no single live session")


def test_a_record_not_running_in_that_tmux_session_is_refused(box, stranger):
    box.panes["cto-c34459eb"] = [stranger]     # root's tmux says that session's panes are elsewhere
    assert box.request("cto-c34459eb", "x").startswith("refused: no single live session")
    assert box.request("project_head-36c49776", "x").startswith("queued")


def test_a_record_without_proc_start_is_refused(box):
    for f in box.sessions.iterdir():
        d = json.loads(f.read_text())
        d.pop("procStart")
        f.write_text(json.dumps(d))
    assert box.request("cto-c34459eb", "x").startswith("refused: no single live session")


def test_a_deeply_nested_record_breaks_nothing(box):
    (box.sessions / "999.json").write_text("[" * 100_000)
    assert box.request("cto-c34459eb", "x").startswith("queued")


def test_a_slow_caller_holds_the_service_two_seconds_at_most(box):
    a, b = socket.socketpair()
    with a, b:
        a.sendall(b'{"role": "cto", ')        # and then nothing, never a shutdown
        t0 = time.monotonic()
        assert rs.handle(b, "contabo", box.pending, (os.getpid(), os.getuid())) == "refused: unreadable request"
        assert time.monotonic() - t0 < rs.REQUEST_DEADLINE_S + 1


@pytest.mark.parametrize("sid", ["c34459eb\n", "c34459eb ", "C34459EB", "c34459eb-x"])
def test_a_sid_must_match_whole(box, sid):
    a, b = socket.socketpair()
    with a, b:
        a.sendall(json.dumps({"role": "cto", "sid": sid, "topic": "x"}).encode())
        a.shutdown(socket.SHUT_WR)
        assert rs.handle(b, "contabo", box.pending, (os.getpid(), os.getuid())) == "refused: not an org session"


def test_a_key_pressed_while_typing_is_never_submitted(box):
    box.request("cto-c34459eb", "x")

    def ceo_presses(fake, name):
        fake.box[name] += "k"

    box.after_type = ceo_presses
    assert rs.once("contabo", box.pending, now=1.0) == [
        "held     cto-c34459eb: the input box did not show exactly the rename; took it back, no Enter"]
    line = f"/rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x"
    assert [t for _, t in box.sent] == [line, "BSpace"]
    bs = [c for c in box.calls if c[-1] == "BSpace"][0]
    assert int(bs[bs.index("-N") + 1]) >= len(line) + 1  # ours plus the one key, never C-u
    assert not any("C-u" in c for c in box.calls)
    assert box.box["cto-c34459eb"] == ""                 # no leading "/" left for the next message


def test_a_slow_redraw_still_gets_its_enter(box):
    box.lag = 3                                          # 3 captures still show the old screen
    box.request("cto-c34459eb", "x")
    assert rs.once("contabo", box.pending, now=1.0) == [f"renamed  cto-c34459eb: {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x"]
    assert [t for _, t in box.sent][-1] == "Enter" and box.box["cto-c34459eb"] == ""


def test_a_long_name_that_wraps_at_phone_width_still_gets_its_enter(box):
    box.width = 50
    box.request("project_head-36c49776", "a topic long enough to wrap the input box twice")
    out = rs.once("contabo", box.pending, now=1.0)
    assert out[0].startswith("renamed  project_head-36c49776")
    assert [t for _, t in box.sent][-1] == "Enter"


def test_a_redraw_that_never_comes_takes_the_text_back(box):
    box.lag = 10_000
    box.request("cto-c34459eb", "x")
    assert rs.once("contabo", box.pending, now=1.0)[0].startswith("held")
    assert box.box["cto-c34459eb"] == "" and "Enter" not in [t for _, t in box.sent]


def test_typed_text_reads_a_wrapped_box_and_stops_at_its_rule():
    screen = "out\n╭────╮\n│ ❯ /rename PH#36c │\n│   (CMO) - Mimi │\n╰────╯\n  ? for shortcuts\n"
    assert rs.typed_text(screen) == "/renamePH#36c(CMO)-Mimi"
    assert rs.typed_text("no prompt here") is None


@pytest.mark.parametrize("kind", ["group-writable", "hard-linked"])
def test_a_lock_file_renamed_or_linked_in_from_elsewhere_is_not_trusted(box, kind, tmp_path):
    # state/logs/* are root-owned and group-writable: secretary can move or link one in (round 3, L-1).
    lock = box.locks / "project_head-36c49776.project"
    if kind == "group-writable":
        lock.chmod(0o664)
    else:
        os.link(lock, tmp_path / "elsewhere")
    assert box.request("project_head-36c49776", "x") == "refused: no rule name for project_head-36c49776"


def test_on_the_mac_a_date_proc_start_counts_and_a_missing_one_does_not(box, monkeypatch):
    monkeypatch.setattr(rs, "DARWIN", True)
    for f in box.sessions.iterdir():
        d = json.loads(f.read_text())
        d["procStart"] = "Tue Oct 13 11:55:05 2026"     # what Claude Code writes on macOS
        f.write_text(json.dumps(d))
    assert box.request("cto-c34459eb", "x").startswith("queued")
    for f in box.sessions.iterdir():
        d = json.loads(f.read_text())
        d.pop("procStart")
        f.write_text(json.dumps(d))
    assert box.request("project_head-36c49776", "x").startswith("refused: no single live session")


# --- review round 4 ------------------------------------------------------------------

@pytest.mark.parametrize("screen,ready", [
    (EMPTY, True), (FRESH, True),                 # a fresh session's dim hint counts as empty
    (DRAFT, False), (DRAFT_BELOW, False),         # the whole box, not only its ❯ row
    (BUSY, False), (PERMISSION, False), ("no prompt", False),
])
def test_ready_means_the_whole_box_is_empty_and_no_turn_runs(screen, ready):
    assert rs.prompt_ready(screen) is ready


def test_a_draft_below_an_empty_first_row_is_never_typed_onto(box):
    box.screens["cto-c34459eb"] = DRAFT_BELOW
    box.request("cto-c34459eb", "x")
    assert rs.once("contabo", box.pending, now=1.0) == ["wait     cto-c34459eb: prompt not empty"]
    assert box.sent == []


def test_no_typing_while_a_turn_runs(box):
    box.screens["cto-c34459eb"] = BUSY
    box.request("cto-c34459eb", "x")
    assert rs.once("contabo", box.pending, now=1.0) == ["wait     cto-c34459eb: turn running"]
    assert box.sent == []


def test_a_turn_or_dialog_that_starts_after_typing_gets_no_enter(box):
    box.request("cto-c34459eb", "x")

    def a_turn_starts(fake, name):
        fake.draw(name)
        fake.screens[name] = "✽ Computing… (1s · thinking)\n" + fake.screens[name]
        fake.after_type = None

    box.after_type = a_turn_starts
    real_draw = box.draw

    def keep_busy(name):
        real_draw(name)
        box.screens[name] = "✽ Computing… (1s · thinking)\n" + box.screens[name]

    box.draw = keep_busy
    out = rs.once("contabo", box.pending, now=1.0)
    assert "Enter" not in [t for _, t in box.sent]
    assert out[0].startswith("held") and box.box["cto-c34459eb"] == ""


def test_the_take_back_counts_what_was_added_not_the_whole_line_twice(box):
    box.request("cto-c34459eb", "x")
    box.after_type = lambda fake, name: fake.box.__setitem__(name, fake.box[name] + "k")
    rs.once("contabo", box.pending, now=1.0)
    bs = [c for c in box.calls if c[-1] == "BSpace"][0]
    line = f"/rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x"
    assert len(line) + 1 <= int(bs[bs.index("-N") + 1]) <= len(line) + 1 + 2   # ours + the key (+wrap slack)
    assert box.box["cto-c34459eb"] == ""


def test_a_take_back_that_leaves_text_stops_that_session(box):
    box.request("cto-c34459eb", "x")
    real = rs.tmux

    def short_backspace(*args):
        if args[-1] == "BSpace":                     # the CEO keeps typing during the take-back
            box.box[args[args.index("-t") + 1][1:-1]] = "his new words"
            box.draw(args[args.index("-t") + 1][1:-1])
            return subprocess.CompletedProcess(args, 0, "", "")
        return real(*args)

    box.after_type = lambda fake, name: fake.box.__setitem__(name, fake.box[name] + "k")
    rs.tmux = short_backspace
    try:
        out = rs.once("contabo", box.pending, now=1.0)
    finally:
        rs.tmux = real
    assert out[0].startswith("stopped  cto-c34459eb") and "cto-c34459eb" not in box.pending
    assert box.box["cto-c34459eb"] == "his new words"        # left alone


def test_a_half_redrawn_screen_at_the_deadline_still_takes_back_the_whole_line(box, monkeypatch):
    # Review follow-up to round 4: the last capture shows only a prefix of what we typed.
    line = f"/rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x"
    monkeypatch.setattr(rs, "_ok_to_enter", lambda screen, want: False)
    real_screen = rs._screen
    calls = {"n": 0}

    def half(pane):
        calls["n"] += 1
        s = real_screen(pane)
        if box.box.get(pane) == line:               # before the take-back: a partial redraw
            return s.replace(line[10:], "")
        return s

    monkeypatch.setattr(rs, "_screen", half)
    assert rs.type_rename("cto-c34459eb", line) == "held"
    bs = [c for c in box.calls if c[-1] == "BSpace"][0]
    assert int(bs[bs.index("-N") + 1]) >= len(line)
    assert box.box["cto-c34459eb"] == ""


# --- the sweep (M10d): a session that started before the host emoji gets it added -------

def _set_name(box, uuid, name):
    for f in box.sessions.iterdir():
        d = json.loads(f.read_text())
        if d["sessionId"] == uuid:
            d["name"] = name
            f.write_text(json.dumps(d))


def test_persona_migration_keeps_topic_and_leaves_ph_worker(box):
    old = f"{CONTABO} CTO (Kavin) — CTO Main"
    _set_name(box, U_CTO, old)
    _set_name(box, U_PH, f"{CONTABO} PH#36c (CMO) - MimiPage")
    box.record("00000000-0000-0000-0000-0000780c8d2d",
               f"{CONTABO} Dev#780 - Org: work", "wd-780c8d2d:@9.%9")
    rs.sweep("contabo", box.pending, 1.0)
    assert list(box.pending) == ["cto-c34459eb"]
    assert box.pending["cto-c34459eb"]["name"] == (
        f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main")
    assert box.sent == []


def _new_pid(box, pid, name="CTO (\U0001F468\u200d\U0001F4BB: Kavin)"):
    """The CTO's session restarted: another Claude process in the same tmux session."""
    for f in box.sessions.iterdir():
        if json.loads(f.read_text())["sessionId"] == U_CTO:
            f.unlink()
    box.record(U_CTO, name, "cto-c34459eb:@1.%1", pid=pid)
    box.panes["cto-c34459eb"] = [pid]


def test_the_sweep_queues_the_emoji_and_keeps_the_rest_of_the_name_byte_for_byte(box):
    box.request("cto-c34459eb", "x")                       # the job a session's own request queues
    keys = set(box.pending.pop("cto-c34459eb"))
    name = "CTO (\U0001F468\u200d\U0001F4BB: Kavin) — ดูแล org  #272 (ok)…"            # Thai, two spaces, punctuation: all kept
    _set_name(box, U_CTO, name)
    out = rs.sweep("contabo", box.pending, 1.0)
    assert box.pending["cto-c34459eb"] == {"name": f"{CONTABO} {name}", "pid": os.getpid(),
                                           "sends": 0, "sent_at": 0.0}
    assert set(box.pending["cto-c34459eb"]) == keys
    assert box.pending["project_head-36c49776"]["name"] == f"{CONTABO} PH#36c (CMO) - MimiPage — MimiPage"
    assert sorted(box.pending) == ["cto-c34459eb", "project_head-36c49776"]    # the COO is only a name here
    assert len(out) == 2 and all(line.startswith("sweep    ") for line in out)
    assert box.sent == []                                  # queued, nothing typed by the sweep itself
    rs.once("contabo", box.pending, now=1000.0)            # _one() types it: the same path as a request
    assert ("cto-c34459eb", f"/rename {CONTABO} {name}") in box.sent
    assert [t for n, t in box.sent if n == "cto-c34459eb"].count("Enter") == 1


def test_the_sweep_leaves_an_on_rule_session_alone(box):
    _set_name(box, U_CTO, f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x")
    _set_name(box, U_PH, f"{CONTABO} PH#36c (CMO) - MimiPage")
    assert rs.sweep("contabo", box.pending, 1.0) == []
    assert box.pending == {} and box.sent == []


def test_the_sweep_does_not_queue_a_box_that_is_already_waiting(box):
    box.request("cto-c34459eb", "asked by itself")
    asked = dict(box.pending["cto-c34459eb"])
    rs.sweep("contabo", box.pending, 1.0)
    assert box.pending["cto-c34459eb"] == asked            # not replaced
    box.pending["project_head-36c49776"]["sends"] = 2      # the PH's job is part-way
    assert rs.sweep("contabo", box.pending, 2.0) == []
    assert box.pending["project_head-36c49776"]["sends"] == 2


@pytest.mark.parametrize("how", ["gave up", "error"])
def test_a_box_the_sweep_could_not_fix_is_not_queued_again_for_that_pid(box, monkeypatch, stranger, how):
    rs.sweep("contabo", box.pending, 1.0)
    if how == "gave up":
        for job in box.pending.values():
            job["sends"], job["sent_at"] = rs.MAX_SENDS, 0.0
        assert all(l.startswith("gave up") for l in rs.once("contabo", box.pending, now=1000.0))
    else:
        def boom(*a):
            raise subprocess.TimeoutExpired("tmux", 10)
        monkeypatch.setattr(rs, "tmux", boom)
        assert all(l.startswith("error") for l in rs.once("contabo", box.pending, now=1000.0))
        monkeypatch.setattr(rs, "tmux", box)
    assert box.pending == {}
    assert rs.sweep("contabo", box.pending, 2000.0) == [] and box.pending == {}
    _new_pid(box, stranger)                                # a new pid is tried; the PH (same pid) is not
    rs.sweep("contabo", box.pending, 3000.0)
    assert list(box.pending) == ["cto-c34459eb"] and box.pending["cto-c34459eb"]["pid"] == stranger


def test_a_session_that_renames_itself_off_the_rule_again_is_swept_again(box):
    rs.sweep("contabo", box.pending, 1.0)
    for job in box.pending.values():
        job["sends"], job["sent_at"] = rs.MAX_SENDS, 0.0
    rs.once("contabo", box.pending, now=1000.0)            # gave up on both
    _set_name(box, U_CTO, "CTO (\U0001F468\u200d\U0001F4BB: Kavin) — a new topic")     # same pid, a name it chose itself
    rs.sweep("contabo", box.pending, 2000.0)
    assert list(box.pending) == ["cto-c34459eb"]
    assert box.pending["cto-c34459eb"]["name"] == f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — a new topic"
    # and one that landed, then went back to the very same bare name, is swept as well
    box.pending.clear()
    _set_name(box, U_CTO, f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — a new topic")
    rs.sweep("contabo", box.pending, 3000.0)               # seen on the rule: the memory is cleared
    _set_name(box, U_CTO, "CTO (\U0001F468\u200d\U0001F4BB: Kavin) — a new topic")
    rs.sweep("contabo", box.pending, 4000.0)
    assert list(box.pending) == ["cto-c34459eb"]


@pytest.mark.parametrize("name", [
    "Dev#afe - OrgRestructure: x",       # a worker's shape on a C-level's box
    "CTO (Someone)",                     # not the persona policies/agents.yaml pins
    "CTO",
    "something else entirely",
    f"{MAC} CTO (\U0001F468\u200d\U0001F4BB: Kavin)",                # another host's emoji is not ours to swap
])
def test_the_sweep_fixes_only_a_missing_emoji_and_says_so_once_for_the_rest(box, name):
    _set_name(box, U_CTO, name)
    _set_name(box, U_PH, f"{CONTABO} PH#36c (CMO) - MimiPage")
    out = rs.sweep("contabo", box.pending, 1.0)
    assert len(out) == 1 and out[0].startswith("skip     cto-c34459eb: ")
    assert box.pending == {}
    assert rs.sweep("contabo", box.pending, 2.0) == []     # logged once per box and pid
    assert box.sent == []


@pytest.mark.parametrize("raw", [
    "CTO (\U0001F468\u200d\U0001F4BB: Kavin) — a\x1b[2Jb",            # an ESC: ls._clean shows it as a space, the pane would get a key
    "CTO (\U0001F468\u200d\U0001F4BB: Kavin) — a\u2028b",
    "CTO (\U0001F468\u200d\U0001F4BB: Kavin) — " + "x" * 105,        # 119 characters: emoji and space would take it to 121 > NAME_MAX
])
def test_the_sweep_never_types_a_name_it_could_not_type_for_a_request(box, raw):
    _set_name(box, U_CTO, raw)
    _set_name(box, U_PH, f"{CONTABO} PH#36c (CMO) - MimiPage")
    out = rs.sweep("contabo", box.pending, 1.0)
    assert len(out) == 1 and "cannot be typed" in out[0]
    assert box.pending == {} and box.sent == []
    assert rs.sweep("contabo", box.pending, 2.0) == []


def test_a_state_glyph_stays_in_front_of_the_emoji(box):
    _set_name(box, U_CTO, "⏸ CTO (\U0001F468\u200d\U0001F4BB: Kavin) — saved")
    rs.sweep("contabo", box.pending, 1.0)
    assert box.pending["cto-c34459eb"]["name"] == f"⏸ {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — saved"
    assert rs.session_names.rule_problem(box.pending["cto-c34459eb"]["name"], "cto", "c34459eb",
                                         "contabo", persona="Kavin") is None


def test_the_sweep_reaches_the_coo_in_its_fixed_tmux_once_the_launcher_file_names_it(box):
    (box.locks / "coo-fde4c4ca.uuid").write_text(U_COO)
    rs.sweep("contabo", box.pending, 1.0)
    assert box.pending["coo-fde4c4ca"]["name"] == f"{CONTABO} COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong)"
    rs.once("contabo", box.pending, now=1.0)
    assert ("sompong", f"/rename {CONTABO} COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong)") in box.sent


@pytest.mark.parametrize("host,emoji,darwin", [("contabo", CONTABO, False), ("mac", MAC, True)])
def test_each_host_gets_its_own_emoji(box, monkeypatch, host, emoji, darwin):
    monkeypatch.setattr(rs, "DARWIN", darwin)
    if darwin:
        for f in box.sessions.iterdir():
            d = json.loads(f.read_text())
            d["procStart"] = "Tue Oct 13 11:55:05 2026"    # what Claude Code writes on macOS
            f.write_text(json.dumps(d))
    rs.sweep(host, box.pending, 1.0)
    assert box.pending["cto-c34459eb"]["name"] == f"{emoji} CTO (\U0001F468\u200d\U0001F4BB: Kavin)"
    assert box.pending["project_head-36c49776"]["name"] == f"{emoji} PH#36c (CMO) - MimiPage — MimiPage"
    rs.once(host, box.pending, now=1.0)
    assert ("cto-c34459eb", f"/rename {emoji} CTO (\U0001F468\u200d\U0001F4BB: Kavin)") in box.sent


def test_the_sweep_stops_at_the_pending_limit(box):
    for i in range(rs.PENDING_MAX):
        box.pending[f"cto-{i:08x}"] = rs._job("x", 1)
    assert rs.sweep("contabo", box.pending, 1.0) == []
    assert len(box.pending) == rs.PENDING_MAX


def test_serve_sweeps_before_it_types(monkeypatch, capsys):
    order = []

    class Stop(Exception):
        pass

    def stop(*a):
        raise Stop

    monkeypatch.setattr(rs, "listen", lambda path=None: object())
    monkeypatch.setattr(rs, "sweep", lambda host, pending, now: order.append("sweep") or ["sweep line"])
    monkeypatch.setattr(rs, "once", lambda host, pending, now: order.append("once") or ["once line"])
    monkeypatch.setattr(rs.select, "select", stop)
    with pytest.raises(Stop):
        rs.serve("contabo")
    assert order == ["sweep", "once"]
    assert capsys.readouterr().out.splitlines() == ["sweep line", "once line"]


# --- 15 Oct: the ghost suggestion, and what the sweep does with the live names ------------------------

GHOST = f"out\n{RULE}\n\x1b[39m❯\xa0\x1b[2mรับยอดเกิน $1.78 ได้\x1b[0m\n{RULE}\n  ? for shortcuts\n"
GREY_BUSY = f"out\n{RULE}\n\x1b[38;5;246m❯\xa0\x1b[39m\n{RULE}\n  \x1b[38;5;246mesc to interrupt\x1b[39m\n"


def test_the_screen_is_captured_with_its_attributes(box):
    """A plain capture-pane cannot tell Claude Code's dim ghost suggestion from a draft, and four
    idle sessions waited 20+ minutes on one (Contabo, 15 Oct). The one capture the service makes is
    `capture-pane -p -e`."""
    box.request("cto-c34459eb", "next job")
    rs.once("contabo", box.pending, now=1000.0)
    captures = [c for c in box.calls if c[0] == "capture-pane"]
    assert captures and all(c[:3] == ("capture-pane", "-p", "-e") for c in captures)


def test_a_ghost_suggestion_is_not_a_draft_so_the_rename_is_typed(box):
    box.screens["cto-c34459eb"] = GHOST
    box.request("cto-c34459eb", "next job")
    out = rs.once("contabo", box.pending, now=1000.0)
    assert out == [f"renamed  cto-c34459eb: {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — next job"]
    assert [t for _, t in box.sent if t != "Enter"] == [f"/rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — next job"]


def test_a_swept_emoji_is_typed_over_a_ghost_suggestion_but_never_over_a_draft(box):
    _set_name(box, U_CTO, "CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main")
    rs.sweep("contabo", box.pending, 1.0)
    box.pending.pop("project_head-36c49776")
    box.screens["cto-c34459eb"] = DRAFT
    assert rs.once("contabo", box.pending, now=1000.0) == ["wait     cto-c34459eb: prompt not empty"]
    assert box.sent == []
    box.screens["cto-c34459eb"] = GHOST
    assert rs.once("contabo", box.pending, now=1000.0) == [f"renamed  cto-c34459eb: {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main"]
    assert [t for _, t in box.sent] == [f"/rename {CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main", "Enter"]


def test_a_grey_pointer_with_the_interrupt_hint_waits_and_says_a_turn_is_running(box):
    """The grey ❯ is what a running turn draws (seen on two worker panes 15 Oct); the log names
    that, not "prompt not empty"."""
    box.screens["cto-c34459eb"] = GREY_BUSY
    box.request("cto-c34459eb", "x")
    assert rs.once("contabo", box.pending, now=1.0) == ["wait     cto-c34459eb: turn running"]
    assert box.sent == []


# the Contabo registry at 15 Oct 06:25 TH, as the CEO keeps the names: (tmux box, session name, queued as)
N3_CONTABO = [
    ("cmo-ef04792e", "CMO (\U0001F469\U0001F3FB\u200d\U0001F3A8: Ging) — CMO Main", f"{CONTABO} CMO (\U0001F469\U0001F3FB\u200d\U0001F3A8: Ging) — CMO Main"),
    ("cto-c34459eb", f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — CTO Main", None),
    ("project_head-13db8720", "PH#13d (CMO) - BlackLiquidity", f"{CONTABO} PH#13d (CMO) - BlackLiquidity"),
    ("project_head-36c49776", "PH#36c (CMO) - MimiPage", f"{CONTABO} PH#36c (CMO) - MimiPage"),
    ("project_head-6c487e37", f"{CONTABO} PH#6c4 (CTO) - SpendGuard", None),
    ("project_head-7cf528f0", f"{CONTABO} PH#7cf (CTO) - OrgRestructure", None),
    ("project_head-f35affd5", "PH#f35 (CTO) - CookieRun", f"{CONTABO} PH#f35 (CTO) - CookieRun"),
]


def _n3_sessions(box):
    for f in box.sessions.iterdir():
        f.unlink()
    for tmux_box, name, _ in N3_CONTABO:
        sid = tmux_box.rsplit("-", 1)[1]
        box.record(f"00000000-0000-0000-0000-0000{sid}", name, f"{tmux_box}:@1.%1")
    # a Claude worker (its own `wd-` tmux) and a name only: no C-level or PH pane to type into
    box.record("00000000-0000-0000-0000-0000780c8d2d", f"{CONTABO} Dev#780 - OrgRestructure: Item 6", "wd-780c8d2d:@9.%9")
    box.record("00000000-0000-0000-0000-00000000aaaa", "CTO (\U0001F468\u200d\U0001F4BB: Kavin)", None)


def test_N3_the_sweep_adds_the_host_emoji_to_the_names_that_lack_it_and_changes_nothing_else(box):
    _n3_sessions(box)
    out = rs.sweep("contabo", box.pending, 1.0)
    want = {b: new for b, _old, new in N3_CONTABO if new}
    assert {b: j["name"] for b, j in box.pending.items()} == want
    assert len(out) == len(want) and all(line.startswith("sweep    ") for line in out)
    for tmux_box, old, new in N3_CONTABO:
        if new:
            assert new == rs.session_names.with_host("contabo", old)       # the emoji, byte for byte, and no other change
            assert rs.session_names.strip_host(new) == old
    assert box.sent == []                                                    # the sweep itself types nothing


def test_N3_a_name_the_sweep_wrote_is_left_alone_on_the_next_passes(box):
    _n3_sessions(box)
    rs.sweep("contabo", box.pending, 1.0)
    assert rs.sweep("contabo", box.pending, 2.0) == []                       # still waiting: not queued twice
    for tmux_box, _old, new in N3_CONTABO:                                   # every rename lands
        if new:
            _set_name(box, f"00000000-0000-0000-0000-0000{tmux_box.rsplit('-', 1)[1]}", new)
    assert all(l.startswith("done ") for l in rs.once("contabo", box.pending, now=1000.0))
    assert box.pending == {}
    assert rs.sweep("contabo", box.pending, 2000.0) == []                    # no requeue once on the rule
    assert rs.sweep("contabo", box.pending, 3000.0) == [] and box.pending == {}


def test_N9_a_name_is_fixed_once_or_reported_once_never_looped(box):
    _n3_sessions(box)
    _set_name(box, "00000000-0000-0000-0000-0000c34459eb", f"{MAC} CTO (\U0001F468\u200d\U0001F4BB: Kavin)")     # another host's emoji: not ours
    first = rs.sweep("contabo", box.pending, 1.0)
    assert len([l for l in first if l.startswith("skip     cto-c34459eb")]) == 1
    for job in box.pending.values():                                                # give up on all of them
        job["sends"], job["sent_at"] = rs.MAX_SENDS, 0.0
    assert all(l.startswith("gave up") for l in rs.once("contabo", box.pending, now=1000.0))
    for now in (2000.0, 3000.0, 4000.0):
        assert rs.sweep("contabo", box.pending, now) == [] and box.pending == {}


# --- a C-level box made a Project Head (the Mac's cto-f39cb080, cto-671f688f) ------------------
# Their box is cto-<sid> because CXO_ROLE=cto, so build_name("cto", …) gave CTO Main's persona.
# state/locks/project_head-<sid>.project makes the box follow the PH rule (effective_role).

U_MAC_PH = "00000000-0000-0000-0000-0000f39cb080"
MAC_PH_BOX = "cto-f39cb080"


def _mark_ph(box, project="LuminaSkies", spawned_by=None, sid="f39cb080"):
    (box.locks / f"project_head-{sid}.project").write_text(project)
    if spawned_by is not None:
        (box.locks / f"project_head-{sid}.spawned_by").write_text(spawned_by)


def _on_rule_neighbours(box):
    """The fixture's other two sessions, on the rule, so a sweep has only the box under test to say."""
    _set_name(box, U_CTO, f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — x")
    _set_name(box, U_PH, f"{CONTABO} PH#36c (CMO) - MimiPage")


def test_a_cto_box_with_a_ph_marker_and_spawned_by_is_named_as_a_ph_of_the_spawned_lane(box):
    _mark_ph(box, spawned_by="cxo:cmo:ef04792e")
    assert rs.build_name("cto", "f39cb080", "LuminaSkies", "", "mac") == f"{MAC} PH#f39 (CMO) - LuminaSkies"
    # the PH branch's topic rule: a topic equal to the project is dropped, another one is kept
    assert rs.build_name("cto", "f39cb080", "ถ่ายทำ ep2", "⏸", "mac") == f"⏸ {MAC} PH#f39 (CMO) - LuminaSkies — ถ่ายทำ ep2"
    assert rs.build_name("cto", "f39cb080", "", "", "mac") == f"{MAC} PH#f39 (CMO) - LuminaSkies"


def test_a_cto_box_with_a_ph_marker_and_no_spawned_by_is_a_ph_of_its_own_lane(box):
    _mark_ph(box)
    assert rs.build_name("cto", "f39cb080", "LuminaSkies", "", "mac") == f"{MAC} PH#f39 (CTO) - LuminaSkies"
    assert rs.build_name("cto", "f39cb080", "next", "", "contabo") == f"{CONTABO} PH#f39 (CTO) - LuminaSkies — next"


def test_a_cto_box_with_no_marker_keeps_the_cto_persona_name(box):
    assert rs.build_name("cto", "f39cb080", "LuminaSkies", "", "mac") == f"{MAC} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — LuminaSkies"
    # .spawned_by alone is no marker; neither is an empty .project
    (box.locks / "project_head-f39cb080.spawned_by").write_text("cxo:cmo:ef04792e")
    (box.locks / "project_head-f39cb080.project").write_text("")
    assert rs.build_name("cto", "f39cb080", "LuminaSkies", "", "mac") == f"{MAC} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — LuminaSkies"
    assert rs.effective_role("cto", "f39cb080") == "cto"


def test_the_marker_only_moves_a_c_level_box_to_the_ph_rule_never_a_ph_to_a_persona(box):
    _mark_ph(box)
    assert rs.effective_role("cto", "f39cb080") == "project_head"
    assert rs.effective_role("cfo", "f39cb080") == "project_head"
    assert rs.effective_role("ceo", "f39cb080") == "ceo"            # no rule for the CEO, marker or not
    assert rs.effective_role("developer", "f39cb080") == "developer"
    assert rs.build_name("developer", "f39cb080", "x", "", "mac") is None
    assert rs.build_name("ceo", "f39cb080", "x", "", "mac") is None
    assert rs.effective_role("project_head", "f39cb080") == "project_head"
    # a project_head box with a marker and no .spawned_by still has no lane: refused, as before
    assert rs.build_name("project_head", "f39cb080", "x", "", "mac") is None
    # a marker for another sid is not this box's
    assert rs.effective_role("cto", "c34459eb") == "cto"


@pytest.mark.parametrize("project", ["bad project", "x" * 41, "Lumina;Skies", "../x", "Lumina Skies", "ลูมินา"])
def test_a_bad_project_in_the_marker_gives_no_name_not_the_cto_persona(box, project):
    _mark_ph(box, project=project, spawned_by="cxo:cmo:ef04792e")
    assert rs.build_name("cto", "f39cb080", "x", "", "mac") is None
    _mark_ph(box, project=project)                                  # and with no .spawned_by
    assert rs.build_name("cto", "f39cb080", "x", "", "mac") is None


@pytest.mark.parametrize("spawned_by", ["cxo:ceoo:ef04792e", "cxo:CTO:ef04792e", "garbage", "cxo:cto"])
def test_a_garbled_spawned_by_is_not_absent_so_the_lane_is_not_guessed(box, spawned_by):
    _mark_ph(box, spawned_by=spawned_by)
    assert rs.build_name("cto", "f39cb080", "x", "", "mac") is None


def test_the_sweep_judges_a_marked_cto_box_by_the_ph_rule(box):
    box.record(U_MAC_PH, f"{CONTABO} PH#f39 (CTO) - LuminaSkies", f"{MAC_PH_BOX}:@7.%7")
    _on_rule_neighbours(box)
    # no marker: its PH-shaped name is off the rule for role cto, logged once, never typed
    out = rs.sweep("contabo", box.pending, 1.0)
    assert len(out) == 1 and out[0].startswith(f"skip     {MAC_PH_BOX}: ") and "off-rule" in out[0]
    # the marker lands: the same name is on the rule, so there is no "off-rule" line and nothing queued
    _mark_ph(box)
    assert rs.sweep("contabo", box.pending, 2.0) == []
    assert box.pending == {} and box.sent == []
    # a fresh service process says the same (the verdict does not lean on the sweep's memory)
    rs._NOTED.clear()
    rs._DECIDED.clear()
    assert rs.sweep("contabo", box.pending, 3.0) == []


def test_the_sweep_adds_only_the_emoji_to_a_marked_boxs_ph_name(box):
    box.record(U_MAC_PH, "PH#f39 (CTO) - LuminaSkies — ถ่ายทำ", f"{MAC_PH_BOX}:@7.%7")
    _on_rule_neighbours(box)
    _mark_ph(box)
    out = rs.sweep("contabo", box.pending, 1.0)
    assert out == [f"sweep    {MAC_PH_BOX}: PH#f39 (CTO) - LuminaSkies — ถ่ายทำ -> "
                   f"{CONTABO} PH#f39 (CTO) - LuminaSkies — ถ่ายทำ"]
    assert list(box.pending) == [MAC_PH_BOX]
    rs.once("contabo", box.pending, now=1000.0)                     # typed into the ORIGINAL box's pane
    assert box.sent == [(MAC_PH_BOX, f"/rename {CONTABO} PH#f39 (CTO) - LuminaSkies — ถ่ายทำ"),
                        (MAC_PH_BOX, "Enter")]


def test_a_marked_box_still_reads_a_cto_persona_name_as_off_rule_and_leaves_it_alone(box):
    # the state the two Mac sessions are in today: marker written, name still CTO Main's
    box.record(U_MAC_PH, f"{CONTABO} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — LuminaSkies", f"{MAC_PH_BOX}:@7.%7")
    _on_rule_neighbours(box)
    _mark_ph(box)
    out = rs.sweep("contabo", box.pending, 1.0)
    assert len(out) == 1 and "off-rule" in out[0] and 'not "PH#<id3> (<LANE>) - <Project>"' in out[0]
    assert box.pending == {} and box.sent == []


def test_the_owner_check_stays_on_the_original_box_a_marker_changes_only_the_name(box, stranger):
    box.record(U_MAC_PH, "CTO (\U0001F468\u200d\U0001F4BB: Kavin)", f"{MAC_PH_BOX}:@7.%7")
    _mark_ph(box, spawned_by="cxo:cto:ef04792e")
    # a process that is not that session: refused at the owner check, nothing queued, nothing typed
    assert box.request(MAC_PH_BOX, "x", peer=(os.getppid(), os.getuid())).startswith(
        "refused: that session is not an ancestor")
    assert box.request(MAC_PH_BOX, "x", peer=(os.getpid(), os.geteuid() + 1)) == (
        "refused: the caller runs as another user than that session")
    # the marker does not make project_head-f39cb080 a box: no tmux session of that name
    assert box.request("project_head-f39cb080", "x") == (
        "refused: no single live session for project_head-f39cb080 in its tmux")
    # a session that is another box's Claude (its own marker or none) cannot rename this one
    box.record(U_MAC_PH.replace("f39cb080", "dddddddd"), "CTO (\U0001F468\u200d\U0001F4BB: Kavin)", "cto-dddddddd:@8.%8", pid=stranger)
    assert box.request("cto-dddddddd", "x", peer=(os.getpid(), os.getuid())).startswith(
        "refused: that session is not an ancestor")
    assert box.pending == {}
    rs.once("contabo", box.pending, now=1.0)
    assert box.sent == []
    # the session itself: queued under the ORIGINAL box, as the PH name, typed into cto-f39cb080
    assert box.request(MAC_PH_BOX, "LuminaSkies") == f"queued {MAC_PH_BOX}: {CONTABO} PH#f39 (CTO) - LuminaSkies"
    assert list(box.pending) == [MAC_PH_BOX]
    rs.once("contabo", box.pending, now=1.0)
    assert box.sent == [(MAC_PH_BOX, f"/rename {CONTABO} PH#f39 (CTO) - LuminaSkies"), (MAC_PH_BOX, "Enter")]


def test_the_marker_is_read_only_after_the_owner_check(box, monkeypatch):
    box.record(U_MAC_PH, "CTO (\U0001F468\u200d\U0001F4BB: Kavin)", f"{MAC_PH_BOX}:@7.%7")
    _mark_ph(box)

    def boom(*a, **k):
        raise AssertionError("the marker was read before the owner check")

    monkeypatch.setattr(rs, "effective_role", boom)
    assert box.request(MAC_PH_BOX, "x", peer=(os.getppid(), os.getuid())).startswith(
        "refused: that session is not an ancestor")


def test_preview_names_a_marked_cto_box_as_a_ph_with_the_hosts_emoji(box, monkeypatch, capsys):
    locks = box.locks.parent / "marked-locks"
    locks.mkdir()
    (locks / "project_head-f39cb080.project").write_text("LuminaSkies")
    monkeypatch.setattr(rs, "LOCKS_DIR", locks)          # main() sets it from --locks-dir; restored after
    argv = ["preview", "--role", "cto", "--sid", "f39cb080", "--topic", "LuminaSkies",
            "--locks-dir", str(locks)]
    assert rs.main([*argv, "--host", "mac"]) == 0
    assert capsys.readouterr().out.strip() == f"{MAC} PH#f39 (CTO) - LuminaSkies"
    assert rs.main([*argv, "--host", "contabo"]) == 0
    assert capsys.readouterr().out.strip() == f"{CONTABO} PH#f39 (CTO) - LuminaSkies"


def test_preview_cli_picks_the_host_emoji_from_org_host_as_session_rename_sh_runs_it(box, tmp_path):
    locks = tmp_path / "cli-locks"
    locks.mkdir()
    (locks / "project_head-f39cb080.project").write_text("LuminaSkies")
    run = lambda *extra: subprocess.run(                  # noqa: E731
        [sys.executable, str(rs.ROOT / "tools" / "rename_service.py"), "preview", "--role", "cto",
         "--sid", "f39cb080", "--topic", "LuminaSkies", "--locks-dir", str(locks), *extra],
        capture_output=True, text=True, timeout=60, cwd=rs.ROOT, env={**os.environ, "ORG_HOST": "mac"})
    r = run()                                             # no --host: config.self_host() → ORG_HOST
    assert (r.returncode, r.stdout.strip()) == (0, f"{MAC} PH#f39 (CTO) - LuminaSkies"), r.stderr
    (locks / "project_head-f39cb080.project").unlink()    # the same command with no marker: CTO Main's name
    r = run()
    assert (r.returncode, r.stdout.strip()) == (0, f"{MAC} CTO (\U0001F468\u200d\U0001F4BB: Kavin) — LuminaSkies"), r.stderr


def test_the_coo_record_without_a_tmux_field_is_found_by_its_pane(box, stranger):
    # cxo-claude.sh starts SomPong with `runuser … env -i`, so $TMUX is gone and Claude writes
    # no tmux field. The fixed tmux "sompong" plus pane ancestry still prove which session it is.
    for f in box.sessions.iterdir():
        d = json.loads(f.read_text())
        if d["sessionId"] == U_COO:
            d["tmux"] = None
            f.write_text(json.dumps(d))
    (box.locks / "coo-fde4c4ca.uuid").write_text(U_COO)
    box.panes["sompong"] = [stranger]          # not in that tmux session: still refused
    assert box.request("coo-fde4c4ca", "x").startswith("refused: no single live session")
    del box.panes["sompong"]
    assert box.request("coo-fde4c4ca", "x").startswith("queued")
    rs.once("contabo", box.pending, now=1.0)
    assert ("sompong", f"/rename {CONTABO} COO (\U0001F468\U0001F3FD\u200d\U0001F4BC: SomPong) — x") in box.sent


def test_a_missing_tmux_field_is_allowed_only_for_a_fixed_tmux_role(box):
    for f in box.sessions.iterdir():
        d = json.loads(f.read_text())
        if d["sessionId"] == U_CTO:
            d.pop("tmux")
            f.write_text(json.dumps(d))
    assert box.request("cto-c34459eb", "x").startswith("refused: no single live session")
