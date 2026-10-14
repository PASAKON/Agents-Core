"""Rename service (M10b, Agents-Core #272): applies the sessions' own rename requests.

CEO 2026-10-14 11:50 (via CMO): sessions rename themselves and never ask him. A
session may not type into its own pane: an allow rule for that would let it type
any slash command into its own prompt. So `scripts/session-rename.sh` only sends a
request, the topic and a state glyph, to this service (root on Contabo, systemd,
installed by one Run card) over the unix socket /run/rename-service/sock. The
service builds the name itself with lib/session_names and types exactly one line,
"/rename <name>", then Enter, into THAT session's pane, and only when its prompt
line (❯) is empty and no choice prompt is up; otherwise it tries again on the next
pass. It never types onto a draft, never sends C-u, and never starts or moves the
tmux server (client commands only: capture-pane, send-keys).

Who may ask (§2b review of #283): the kernel says who is on the other end of the
socket (SO_PEERCRED on Linux, LOCAL_PEERPID + LOCAL_PEERCRED on macOS). A
request for <role>-<sid> is accepted only when that
session's Claude process (its live session record) is an ancestor of the
connecting process and runs as the same effective uid. So a session renames only
itself, and a process with no session (a service user such as `secretary`)
renames nothing. That check runs BEFORE any lock file is read. A session record
counts only when its pid descends from a pane of that session's own tmux session
(read from root's tmux server), it carries procStart, and the file's owner is
the pid's uid: a user who writes its own registry dir (sompong) cannot claim
another session's pane (review v2, M-1). Requests live in this process's memory:
root writes no file a non-root user could plant a symlink for, and lock files are
read with ls.read_lock (no symlink, no FIFO, at most 256 bytes, root-owned).

On the Mac (M10c, CEO 2026-10-14 13:38) the same code runs from a LaunchDaemon
(deploy/launchd/com.mooniex.rename-service.plist) as the user the sessions run as,
not root: it only reads that user's session records and talks to that user's own
tmux server, and root running code from a checkout that user can write would
hand every session root. Its socket is ~/.rename-service/sock (0700 dir); there is
no /proc, so ancestry and uids come from `ps`.

The request carries no name, so nothing a session sends can reach the pane except
a topic: clean_topic() keeps letters, marks, digits, spaces and a few punctuation
marks, drops every control and format character (newline, ESC), strips a leading
"/", and cuts it to 40 characters.

    python tools/rename_service.py run           # the service
    python tools/rename_service.py request --role cto --sid c34459eb --topic "x" [--prefix ✅]
    python tools/rename_service.py preview --role cto --sid c34459eb --topic "x"
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import select
import socket
import stat
import struct
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import config, session_names  # noqa: E402
from tools import live_sessions as ls  # noqa: E402

LOCKS_DIR = ROOT / "state" / "locks"
DARWIN = sys.platform == "darwin"
SOCK = Path(os.environ.get("RENAME_SERVICE_SOCK")
            or (Path.home() / ".rename-service" / "sock" if DARWIN else "/run/rename-service/sock"))
PROC = Path("/proc")
REQUEST_MAX = 4096
REQUEST_DEADLINE_S = 2.0          # for the whole request, not per recv (review v2, L-1)
PENDING_MAX = 64
TOPIC_MAX = 40
NAME_MAX = 120
PREFIXES = ("", "✅", "⏸", "⛔")        # ✅ close, ⏸ save, ⛔ merged
RETRY_S = 120                                      # a sent rename that did not land is sent again
MAX_SENDS = 3
INTERVAL_S = 15
TYPED_WAIT_S = 1.0       # how long the typed line may take to show before it is taken back
TYPED_POLL_S = 0.1
_BOX_RE = re.compile(r"(c[a-z]o|project_head)-([0-9a-f]{8})")   # always fullmatch
_FIXED_TMUX = {"coo": "sompong"}
_TOPIC_PUNCT = set(" -_.,:()+#&'!?%")   # no ';': tmux strips a trailing one from send-keys
_PROMPT = "❯"


# --- the name ----------------------------------------------------------------------

def clean_topic(text) -> str:
    """The only session-written text that reaches a pane. One line, no control or
    format character, no leading "/", letters/marks/digits/spaces/_TOPIC_PUNCT only."""
    text = unicodedata.normalize("NFC", str(text or ""))
    kept = []
    for c in text:
        cat = unicodedata.category(c)
        if cat[0] in "LMN" or c in _TOPIC_PUNCT:
            kept.append(c)
        elif cat[0] in "CZ":
            kept.append(" ")          # a newline or tab becomes a space, never a key
    topic = re.sub(r" {2,}", " ", "".join(kept)).strip().lstrip("/ ").strip()
    if len(topic) > TOPIC_MAX:
        topic = topic[:TOPIC_MAX].rstrip() + "…"
    return topic


def _read(name: str) -> str:
    return ls.read_lock(LOCKS_DIR / name)


def build_name(role: str, sid: str, topic, prefix, host: str) -> str | None:
    """The rule name for a C-level or PH plus the cleaned topic, or None (no rule
    for this role, a PH with no project record, a prefix not in PREFIXES)."""
    prefix = str(prefix or "")
    if prefix not in PREFIXES:
        return None
    topic = clean_topic(topic)
    if role == "project_head":
        project = _read(f"project_head-{sid}.project")
        spawned = _read(f"project_head-{sid}.spawned_by").split(":")   # cxo:<lane>:<sid>
        lane = spawned[1] if len(spawned) == 3 else ""
        if not re.fullmatch(r"[A-Za-z0-9_]{1,40}", project) or not re.fullmatch(r"c[a-z]o", lane):
            return None
        base = config.ph_session_name(sid, lane, project, host)
        if topic == project:
            topic = ""
    elif re.fullmatch(r"c[a-z]o", role) and role != "ceo":
        persona = config.persona_for(role)
        if persona and not re.fullmatch(r"[A-Za-z]{2,32}", persona):
            return None
        base = session_names.with_host(host, f"{role.upper()} ({persona})" if persona else role.upper())
    else:
        return None
    name = base + (f" — {topic}" if topic else "")
    name = f"{prefix} {name}" if prefix else name
    if (len(name) > NAME_MAX or name.startswith("/")
            or any(unicodedata.category(c)[0] == "C" or c in "\n\r" for c in name)):
        return None
    return name


# --- the panes ---------------------------------------------------------------------

def tmux(*args: str) -> subprocess.CompletedProcess:
    from tools.tmux_session import tmux_bin   # launchd's PATH has no /opt/homebrew/bin
    return subprocess.run([tmux_bin(), *args], capture_output=True, text=True, timeout=10)


def target(tmux_name: str) -> str:
    """An exact tmux target: '=' stops a prefix match on another session's name."""
    return f"={tmux_name}:"


# A numbered choice with the cursor on it (maybe inside a │ box), plus a choice footer:
# a permission prompt or an on-screen question, the app's ✋ "waiting for you".
_CHOICE_RE = re.compile(r"^[\s\u2502\u2503|]*\u276f\s*\d+\.\s")
_CHOICE_HINTS = ("Do you want", "Esc to cancel", "to navigate", "Enter to select", "Would you like")


def pane_waiting(text: str) -> bool:
    """True when a pane's screen holds a choice prompt waiting on a person."""
    tail = text.splitlines()[-30:]
    return any(_CHOICE_RE.match(l) for l in tail) and any(h in l for l in tail for h in _CHOICE_HINTS)


def prompt_line(screen: str) -> str | None:
    """The text on the last ❯ line, or None when there is none."""
    lines = [l for l in screen.splitlines() if _PROMPT in l]
    if not lines:
        return None
    return lines[-1].split(_PROMPT, 1)[1].replace("\xa0", " ").strip().strip("".join(_BOX_CHARS)).strip()


# Box-drawing (─ │ ╭ ╮ …) and block characters a TUI draws around its input box.
_BOX_CHARS = {chr(c) for c in range(0x2500, 0x25A0)}


def _box_rows(screen: str) -> list[str] | None:
    """The input box's rows: the text after the last ❯ plus the rows it wrapped onto,
    up to the box's bottom rule, box characters removed. None with no ❯ line."""
    lines = screen.splitlines()
    idx = [i for i, l in enumerate(lines) if _PROMPT in l]
    if not idx:
        return None
    rows = [lines[idx[-1]].split(_PROMPT, 1)[1]]
    for l in lines[idx[-1] + 1:]:
        if l.strip() and all(c in _BOX_CHARS or c.isspace() for c in l):
            break                                   # the rule under the input box
        rows.append(l)
    return ["".join(c for c in r if c not in _BOX_CHARS).strip() for r in rows]


def typed_text(screen: str) -> str | None:
    """What sits in the input box with every space and box character removed (a long
    name wraps at the pane width). None when there is no ❯ line."""
    rows = _box_rows(screen)
    return None if rows is None else _squash("".join(rows))


def _box_len(screen: str | None) -> int:
    """At least the number of characters in the input box: its rows plus one space
    per wrap, which a capture drops."""
    rows = _box_rows(screen) if screen is not None else None
    rows = [r for r in rows or [] if r]
    return sum(len(r) for r in rows) + len(rows)


def _squash(text: str) -> str:
    return "".join(c for c in text if not c.isspace() and c not in _BOX_CHARS)


# An empty box in a fresh session shows a dim hint (`Try "fix lint errors"`), which a
# plain capture cannot tell from typed text (seen on a real pane 14 Oct).
_PLACEHOLDER_RE = re.compile(r'Try"[^"]{1,80}"')
# A turn is running: the footer says so, or the spinner line "✽ Computing… (11s · …)".
_BUSY_RE = re.compile(r"esc to interrupt|…\s*\(\d+[sm]\b")


def box_empty(screen: str) -> bool:
    """The WHOLE input box is empty, not only its ❯ row: a draft can start with an
    empty first row (Shift+Enter) and hold text below it (review round 4, M-1)."""
    text = typed_text(screen)
    return text is not None and (text == "" or bool(_PLACEHOLDER_RE.fullmatch(text)))


def pane_busy(screen: str) -> bool:
    """A turn is running: Enter could land on a dialog that opens a moment later."""
    return bool(_BUSY_RE.search(screen))


def prompt_ready(screen: str) -> bool:
    """The whole input box is empty, no turn is running and no choice prompt
    (permission / question) is up."""
    return not pane_waiting(screen) and not pane_busy(screen) and box_empty(screen)


def pane_pids(tmux_name: str) -> set[int]:
    """The pids of every pane of that tmux session, from this (root's) tmux server."""
    r = tmux("list-panes", "-s", "-t", target(tmux_name), "-F", "#{pane_pid}")
    if r.returncode != 0:
        return set()
    return {int(x) for x in r.stdout.split() if x.isdigit()}


def _record(p: Path) -> tuple[dict, int] | None:
    """(record, file owner uid) for one registry file, read like ls does it."""
    fd = ls._safe_open(p, os.O_RDONLY, create=False)
    if fd is None:
        return None
    try:
        st = os.fstat(fd)
        if st.st_size > ls.MAX_SESSION_BYTES:
            return None
        data = os.read(fd, ls.MAX_SESSION_BYTES + 1)
    except OSError:
        return None
    finally:
        os.close(fd)
    try:
        rec = json.loads(data.decode("utf-8"))
    except (ValueError, RecursionError):       # RecursionError: a planted deep nest (L-5)
        return None
    return (rec, st.st_uid) if isinstance(rec, dict) else None


def session_of(box: str, host: str) -> dict | None:
    """The one live session record in this box's launcher tmux, or None."""
    m = _BOX_RE.fullmatch(box)
    if not m:
        return None
    role, sid = m.groups()
    tmux_name = _FIXED_TMUX.get(role, box)
    panes = None
    hits = []
    for d in ls.session_dirs(host):
        try:
            files = [p for p in Path(d).iterdir() if ls._SESSION_FILE_RE.match(p.name)]
        except OSError:
            continue
        for p in files:
            got = _record(p)
            if got is None:
                continue
            data, owner = got
            try:
                pid = int(data["pid"])
            except (ValueError, KeyError, TypeError):
                continue
            if str(data.get("tmux") or "").split(":", 1)[0] != tmux_name:
                continue
            uuid = str(data.get("sessionId") or "")
            start = ls._proc_start(data.get("procStart"))
            if not data.get("procStart") or (not DARWIN and start is None):
                continue                    # Linux: an int; macOS writes a date (kill(0) only)
            if not uuid.endswith(sid) or not ls.is_alive(pid, start):
                continue
            if owner != _uid(pid):          # a record speaks only for its writer's own process
                continue
            if panes is None:
                panes = pane_pids(tmux_name)
            if not panes.intersection(ancestors(pid)):   # it really runs in that tmux session
                continue
            if role == "coo" and not ls._launcher_uuid("coo", uuid):
                continue
            hits.append({"name": str(data.get("name") or ""), "pane": str(data["tmux"]).split(":", 1)[0],
                         "uuid": uuid, "pid": pid})
    return hits[0] if len(hits) == 1 else None


# --- who is asking ----------------------------------------------------------------

def _proc_info(pid: int) -> tuple[int, int] | None:
    """(parent pid, effective uid) of `pid` from /proc, or from `ps` where there is
    none (the Mac: its `uid` column is the effective one); None when unreadable."""
    if PROC.is_dir():
        try:
            text = (PROC / str(pid) / "status").read_text(encoding="utf-8", errors="replace")
            st = dict(l.split(":", 1) for l in text.splitlines() if ":" in l)
            return int(st["PPid"].strip()), int(st["Uid"].split()[1])
        except (OSError, KeyError, ValueError, IndexError):
            return None
    try:
        out = subprocess.run(["ps", "-o", "ppid=", "-o", "uid=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=5)
        ppid, uid = out.stdout.split()
        return int(ppid), int(uid)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _uid(pid: int) -> int | None:
    """The effective uid (SO_PEERCRED reports the effective one too; review v2, L-6)."""
    info = _proc_info(pid)
    return info[1] if info else None


def ancestors(pid: int, limit: int = 64) -> list[int]:
    """pid, its parent, its grandparent … up to init (at most `limit`)."""
    chain = []
    while pid > 1 and len(chain) < limit:
        chain.append(pid)
        info = _proc_info(pid)
        if info is None:
            break
        pid = info[0]
    return chain


def owner_refusal(peer_pid: int, peer_uid: int, sess: dict) -> str | None:
    """None when the connecting process belongs to `sess`: the session's Claude
    process is its ancestor and runs as the same uid."""
    if sess["pid"] not in ancestors(peer_pid):
        return "that session is not an ancestor of the caller (a session renames only itself)"
    if _uid(sess["pid"]) != peer_uid:
        return "the caller runs as another user than that session"
    return None


# macOS <sys/un.h>: SOL_LOCAL, LOCAL_PEERCRED (struct xucred), LOCAL_PEERPID.
_SOL_LOCAL, _LOCAL_PEERCRED, _LOCAL_PEERPID = 0, 0x001, 0x002
_XUCRED_SIZE = 76   # u_int cr_version; uid_t cr_uid; short cr_ngroups; gid_t cr_groups[16]


def darwin_peer(pid_raw: bytes, cred_raw: bytes) -> tuple[int, int]:
    (pid,) = struct.unpack_from("i", pid_raw)
    _version, uid = struct.unpack_from("II", cred_raw)
    return pid, uid


def peer(conn: socket.socket) -> tuple[int, int]:
    """(pid, uid) of the process on the other end, from the kernel."""
    if DARWIN:
        return darwin_peer(conn.getsockopt(_SOL_LOCAL, _LOCAL_PEERPID, 4),
                           conn.getsockopt(_SOL_LOCAL, _LOCAL_PEERCRED, _XUCRED_SIZE))
    pid, uid, _gid = struct.unpack("3i", conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                                         struct.calcsize("3i")))
    return pid, uid


def _read_request(conn: socket.socket) -> dict | None:
    deadline = time.monotonic() + REQUEST_DEADLINE_S
    buf = b""
    try:
        while len(buf) <= REQUEST_MAX:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            conn.settimeout(left)
            chunk = conn.recv(REQUEST_MAX + 1 - len(buf))
            if not chunk:
                break
            buf += chunk
    except OSError:
        return None
    if len(buf) > REQUEST_MAX:
        return None
    try:
        d = json.loads(buf.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    return d if isinstance(d, dict) else None


def handle(conn: socket.socket, host: str, pending: dict, peer_ids: tuple[int, int] | None = None) -> str:
    """One request on the socket: queue the rename for the caller's own session, or say why not."""
    peer_pid, peer_uid = peer_ids or peer(conn)
    req = _read_request(conn)
    if req is None:
        return "refused: unreadable request"
    box = f"{req.get('role')}-{req.get('sid')}"
    if not _BOX_RE.fullmatch(box):
        return "refused: not an org session"
    role, sid = box.split("-", 1)
    # Who is asking first: no lock file is read for a caller that is not that session.
    sess = session_of(box, host)
    if sess is None:
        return f"refused: no single live session for {box} in its tmux"
    why = owner_refusal(peer_pid, peer_uid, sess)
    if why:
        return f"refused: {why}"
    name = build_name(role, sid, req.get("topic"), req.get("prefix"), host)
    if name is None:
        return f"refused: no rule name for {box}"
    if box not in pending and len(pending) >= PENDING_MAX:
        return "refused: too many renames waiting"
    pending[box] = {"name": name, "pid": sess["pid"], "sends": 0, "sent_at": 0.0}
    return f"queued {box}: {name}"


# --- one pass ----------------------------------------------------------------------

def _screen(pane: str) -> str | None:
    r = tmux("capture-pane", "-p", "-t", target(pane))
    return r.stdout if r.returncode == 0 else None


def _ready(pane: str) -> bool:
    screen = _screen(pane)
    return screen is not None and prompt_ready(screen)


def _one(box: str, job: dict, host: str, now: float) -> tuple[str, bool]:
    """(log line, finished) for one waiting rename."""
    name = job["name"]
    sess = session_of(box, host)
    if sess is None or sess["pid"] != job["pid"]:
        return f"drop     {box}: the session that asked has gone", True
    if sess["name"] == name:
        return f"done     {box}: {name}", True
    sends = job["sends"]
    if sends and now - job["sent_at"] < RETRY_S:
        return f"sent     {box}: waiting for it to land", False
    if sends >= MAX_SENDS:
        return f"gave up  {box}: {MAX_SENDS} sends did not land", True
    # Twice, the second right before typing: a draft started in between must stop it.
    if not _ready(sess["pane"]) or not _ready(sess["pane"]):
        return f"wait     {box}: prompt not empty", False
    job["sends"], job["sent_at"] = sends + 1, now
    result = type_rename(sess["pane"], f"/rename {name}")
    if result == "renamed":
        return f"renamed  {box}: {name}", False
    if result == "held":
        return f"held     {box}: the input box did not show exactly the rename; took it back, no Enter", False
    return (f"stopped  {box}: after taking the rename back the input box is not empty; "
            "no more keys for this session"), True


def _ok_to_enter(screen: str | None, want: str) -> bool:
    return (screen is not None and not pane_waiting(screen) and not pane_busy(screen)
            and typed_text(screen) == want)


def type_rename(pane: str, line: str) -> str:
    """Type `line` into a pane whose whole box is empty (the caller checked twice),
    then press Enter only once the box shows exactly it with no turn running and no
    dialog up, checked again right before the Enter (re-read for up to TYPED_WAIT_S:
    the TUI redraws a moment later, and a long line wraps). "renamed".

    Otherwise take back what was added since the box was empty: one BSpace per
    character (a real Claude box deletes a whole emoji per BSpace), never C-u. "held"
    when the box is empty again; "stopped" when it is not (someone typed in that
    second, or the take-back fell short): the caller sends no more keys there
    (review round 4, M-1)."""
    t = target(pane)
    if tmux("send-keys", "-t", t, "-l", line).returncode != 0:
        return "held"
    want = _squash(line)
    deadline = time.monotonic() + TYPED_WAIT_S
    screen = None
    while True:
        screen = _screen(pane)
        if _ok_to_enter(screen, want) and _ok_to_enter(_screen(pane), want):
            tmux("send-keys", "-t", t, "Enter")
            return "renamed"
        if time.monotonic() >= deadline:
            break
        time.sleep(TYPED_POLL_S)
    # The box was empty before we typed, so all of it was added since: our line plus
    # any key pressed in this second. Never fewer than our own line: a screen caught
    # half redrawn shows less than we typed, and a leftover "/rename…" would start the
    # person's next message. More is harmless: BSpace on an empty box does nothing.
    added = _box_len(screen) if screen is not None and not box_empty(screen) else 0
    tmux("send-keys", "-t", t, "-N", str(max(added, len(line))), "BSpace")
    deadline = time.monotonic() + TYPED_WAIT_S
    while True:
        time.sleep(TYPED_POLL_S)
        after = _screen(pane)
        if after is not None and box_empty(after):
            return "held"
        if time.monotonic() >= deadline:
            return "stopped"


def once(host: str, pending: dict, now: float | None = None) -> list[str]:
    now = time.time() if now is None else now
    out = []
    for box in sorted(pending):
        try:
            line, finished = _one(box, pending[box], host, now)
        except Exception as e:  # noqa: BLE001 - one bad rename must not stop the others
            line, finished = f"error    {box}: {type(e).__name__}: {e}", True
        out.append(line)
        if finished:
            pending.pop(box, None)
    return out


# --- the socket ----------------------------------------------------------------------

def listen(path: Path = SOCK) -> socket.socket:
    """Bind the request socket. Its directory must be this user's and not
    writable by group or other: systemd RuntimeDirectory=rename-service makes it
    0755 root on Contabo; on the Mac this makes ~/.rename-service 0700."""
    if not os.path.lexists(path.parent):
        os.mkdir(path.parent, 0o700 if DARWIN else 0o755)
    st = os.lstat(path.parent)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o022:
        raise SystemExit(f"{path.parent} must be a directory owned by this user with no group/other write")
    with contextlib.suppress(OSError):
        if stat.S_ISSOCK(os.lstat(path).st_mode):
            os.unlink(path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(path))
    os.chmod(path, 0o666)   # any local user may ask; only for its own session (owner_refusal)
    srv.listen(16)
    return srv


def serve(host: str, path: Path = SOCK) -> None:
    srv = listen(path)
    pending: dict = {}
    next_pass = 0.0
    while True:
        now = time.time()
        if now >= next_pass:
            for line in once(host, pending, now):
                print(line, flush=True)
            next_pass = now + INTERVAL_S
        ready, _, _ = select.select([srv], [], [], max(0.1, next_pass - time.time()))
        if not ready:
            continue
        try:
            conn, _ = srv.accept()
        except OSError:
            continue
        with conn:
            try:
                reply = handle(conn, host, pending)
            except Exception as e:  # noqa: BLE001
                reply = f"refused: {type(e).__name__}"
            print(reply, flush=True)
            try:
                conn.sendall((reply + "\n").encode("utf-8"))
            except OSError:
                pass


def send_request(role: str, sid: str, topic: str, prefix: str, path: Path | None = None) -> str:
    """The client side, used by scripts/session-rename.sh."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    with s:
        s.connect(str(path or SOCK))
        s.sendall(json.dumps({"role": role, "sid": sid, "topic": topic, "prefix": prefix},
                             ensure_ascii=False).encode("utf-8"))
        s.shutdown(socket.SHUT_WR)
        return s.recv(4096).decode("utf-8", "replace").strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    for cmd in ("preview", "request"):
        pv = sub.add_parser(cmd)
        pv.add_argument("--role", required=True)
        pv.add_argument("--sid", required=True)
        pv.add_argument("--topic", default="")
        pv.add_argument("--prefix", default="")
        if cmd == "preview":
            pv.add_argument("--host")
            pv.add_argument("--locks-dir", help="the calling checkout's state/locks")
    a = ap.parse_args(argv)
    if a.cmd == "request":
        try:
            reply = send_request(a.role, a.sid, a.topic, a.prefix)
        except OSError as e:
            print(f"rename service not reachable at {SOCK} ({e.strerror or e})")
            return 2
        print(reply)
        return 0 if reply.startswith("queued") else 1
    if a.cmd == "preview":
        if a.locks_dir:
            global LOCKS_DIR
            LOCKS_DIR = Path(a.locks_dir)
        try:
            host = a.host or config.self_host()
        except Exception:
            host = ""
        name = build_name(a.role, a.sid, a.topic, a.prefix, host)
        print(name or "")
        return 0 if name else 1
    serve(config.self_host())
    return 0


if __name__ == "__main__":
    sys.exit(main())
