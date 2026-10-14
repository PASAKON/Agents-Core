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

    record(U_CTO, "CTO (Kavin)", "cto-c34459eb:@1.%1")
    record(U_PH, "PH#36c (CMO) - MimiPage — MimiPage", "project_head-36c49776:@2.%2")
    record(U_COO, "COO (SomPong)", "sompong:@3.%3")
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
    assert line.startswith(f"/rename {CONTABO} CTO (Kavin)")
    assert line.count("/") == 1 + line[len("/rename "):].count("/")    # only the command's own slash leads
    assert not any(ord(c) < 32 or 0x7f <= ord(c) < 0xa0 or c in "  ‮​\u0085" for c in line)
    assert len(line) <= len("/rename ") + rs.NAME_MAX
    topic_part = line.split(" — ", 1)[1] if " — " in line else ""
    assert not topic_part.startswith("/") and len(topic_part) <= rs.TOPIC_MAX + 1
    assert all(c[0] in ("capture-pane", "send-keys", "list-panes") for c in box.calls)


def test_it_types_only_into_an_empty_prompt_and_retries_later(box):
    box.request("cto-c34459eb", "next job")
    for screen in (DRAFT, PERMISSION):
        box.screens["cto-c34459eb"] = screen
        assert rs.once("contabo", box.pending, now=1000.0) == ["wait     cto-c34459eb: prompt not empty"]
        assert box.sent == []
    box.screens["cto-c34459eb"] = EMPTY
    assert rs.once("contabo", box.pending, now=1000.0) == [f"renamed  cto-c34459eb: {CONTABO} CTO (Kavin) — next job"]
    assert box.sent == [("cto-c34459eb", f"/rename {CONTABO} CTO (Kavin) — next job"),
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
            d["name"] = f"{CONTABO} CTO (Kavin) — t"
            f.write_text(json.dumps(d))
    assert rs.once("contabo", box.pending, now=5000.0) == [f"done     cto-c34459eb: {CONTABO} CTO (Kavin) — t"]
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
    assert box.sent[0] == ("sompong", f"/rename {CONTABO} COO (SomPong) — x")


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
    box.record(U_CTO.replace("c34459eb", "dddddddd"), "CTO (Kavin)", "cto-dddddddd:@9.%9", pid=stranger)
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
    assert out.stdout.strip() == f"queued cto-c34459eb: {CONTABO} CTO (Kavin) — via socket", out.stderr
    assert box.pending["cto-c34459eb"]["name"] == f"{CONTABO} CTO (Kavin) — via socket"


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
    assert capsys.readouterr().out.strip() == f"{CONTABO} CTO (Kavin) — x"
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
    line = f"/rename {CONTABO} CTO (Kavin) — x"
    assert [t for _, t in box.sent] == [line, "BSpace"]
    bs = [c for c in box.calls if c[-1] == "BSpace"][0]
    assert int(bs[bs.index("-N") + 1]) >= len(line) + 1  # ours plus the one key, never C-u
    assert not any("C-u" in c for c in box.calls)
    assert box.box["cto-c34459eb"] == ""                 # no leading "/" left for the next message


def test_a_slow_redraw_still_gets_its_enter(box):
    box.lag = 3                                          # 3 captures still show the old screen
    box.request("cto-c34459eb", "x")
    assert rs.once("contabo", box.pending, now=1.0) == [f"renamed  cto-c34459eb: {CONTABO} CTO (Kavin) — x"]
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
    assert rs.once("contabo", box.pending, now=1.0) == ["wait     cto-c34459eb: prompt not empty"]
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
    line = f"/rename {CONTABO} CTO (Kavin) — x"
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
    line = f"/rename {CONTABO} CTO (Kavin) — x"
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
