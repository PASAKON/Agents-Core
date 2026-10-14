"""tools/rename_service.py (M10b, Agents-Core #272): a session's rename request is
typed as exactly one "/rename <rule name>" line, only into that session's empty
prompt, and only when the process asking descends from that session (§2b review of
#283). tmux is a fake that records every call; the session records point at this
test's own pid, so this process and its children count as the session."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
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
EMPTY = "out\n❯ \n  ? for shortcuts\n"
DRAFT = "out\n❯ half a sentence the CEO is typing\n"
PERMISSION = " Do you want to proceed?\n ❯ 1. Yes\n   2. No\n❯ \n"


class FakeTmux:
    def __init__(self):
        self.screens, self.calls, self.sent = {}, [], []
        self.after_capture = None   # called after each capture-pane (a CEO typing)

    def __call__(self, *args):
        self.calls.append(args)
        out = ""
        if args[0] == "capture-pane":
            out = self.screens.get(args[args.index("-t") + 1], EMPTY)
            if self.after_capture:
                self.after_capture(self)
        elif args[0] == "send-keys":
            self.sent.append((args[args.index("-t") + 1], args[-1]))
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
    n = [0]
    pending = {}

    def record(uuid, name, tmux, pid=None):
        n[0] += 1
        (sessions / f"{n[0]}.json").write_text(json.dumps(
            {"pid": pid or os.getpid(), "sessionId": uuid, "name": name, "tmux": tmux}))

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
    typed = [t for _, t in box.sent if t != "Enter"]
    assert len(typed) == 1 and [t for _, t in box.sent].count("Enter") == 1
    line = typed[0]
    assert line.startswith(f"/rename {CONTABO} CTO (Kavin)")
    assert line.count("/") == 1 + line[len("/rename "):].count("/")    # only the command's own slash leads
    assert not any(ord(c) < 32 or 0x7f <= ord(c) < 0xa0 or c in "  ‮​\u0085" for c in line)
    assert len(line) <= len("/rename ") + rs.NAME_MAX
    topic_part = line.split(" — ", 1)[1] if " — " in line else ""
    assert not topic_part.startswith("/") and len(topic_part) <= rs.TOPIC_MAX + 1
    assert all(c[0] in ("capture-pane", "send-keys") for c in box.calls)


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


def test_a_caller_running_as_another_user_is_refused(box, monkeypatch):
    monkeypatch.setattr(rs, "_uid", lambda pid: 1001)
    assert box.request("cto-c34459eb", "x") == "refused: the caller runs as another user than that session"
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
        if "cto-c34459eb" in args:
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


def test_listen_refuses_a_group_writable_socket_directory(tmp_path):
    d = tmp_path / "run"
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
])
def test_clean_topic(raw, clean):
    assert rs.clean_topic(raw) == clean


def test_preview_is_what_the_service_would_type(box, capsys):
    assert rs.main(["preview", "--role", "cto", "--sid", "c34459eb", "--topic", "x",
                    "--host", "contabo"]) == 0
    assert capsys.readouterr().out.strip() == f"{CONTABO} CTO (Kavin) — x"
    assert rs.main(["preview", "--role", "developer", "--sid", "afe57b21", "--host", "contabo"]) == 1
