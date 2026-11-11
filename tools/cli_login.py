#!/usr/bin/env python3
"""Phone-friendly CLI authentication. Python 3.11; no third-party dependencies.

Only login URLs/device codes and sanitized status are displayed. Transfer payloads
are private SSH pipes, never command arguments. See docs/ops/cli-login.md.
"""
from __future__ import annotations

import argparse
import base64
import codecs
import json
import os
from pathlib import Path
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time

CLIS = ("claude", "codex", "agy")
HOSTS = ("winbox", "mac", "contabo")
LIMIT = 1024 * 1024


class Refused(Exception):
    pass


def credential_path(cli):
    home = Path.home()
    if cli == "codex":
        return Path(os.environ.get("CODEX_HOME", home / ".codex")) / "auth.json"
    if cli == "claude":
        if sys.platform == "darwin":
            return None  # Never read or write the Keychain.
        return Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")) / ".credentials.json"
    override = os.environ.get("CLI_LOGIN_AGY_TOKEN_FILE")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return None  # Session keyring documented; no verified portable file path.
    return home / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"


def executable(cli):
    path = shutil.which(cli)
    if not path and os.name == "nt" and cli == "agy":
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "agy/bin/agy.exe"
        if candidate.is_file():
            path = str(candidate)
    if not path:
        raise Refused("CLI executable unavailable")
    return path


def command(cli, args):
    exe = executable(cli)
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c",
                subprocess.list2cmdline([exe, *args])]
    return [exe, *args]


def status(cli):
    path = credential_path(cli)
    mtime = None
    present = False
    if path is not None:
        try:
            info = path.stat()
            mtime = info.st_mtime
            present = stat.S_ISREG(info.st_mode) and info.st_size > 0
        except OSError:
            pass
    ok = False
    reason = "status-no"
    try:
        args = {"claude": ["auth", "status"], "codex": ["login", "status"],
                "agy": ["models"]}[cli]
        if cli != "agy" or present:
            result = subprocess.run(command(cli, args), stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=20)
            out = (result.stdout + result.stderr).decode(errors="replace")
            if cli == "claude":
                ok = result.returncode == 0 and json.loads(result.stdout).get("loggedIn") is True
            elif cli == "codex":
                ok = result.returncode == 0
            else:
                # Listing models costs no inference; reject interactive auth responses.
                ok = (result.returncode == 0 and bool(out.strip()) and
                      not re.search(r"sign.?in|log.?in|authentication required|oauth|https://accounts", out, re.I))
        else:
            reason = "token-file-missing-or-keyring-unsupported"
    except (OSError, ValueError, subprocess.TimeoutExpired, Refused):
        reason = "status-unavailable"
    return {"cli": cli, "logged_in": ok, "credential_path": str(path) if path else None,
            "mtime": mtime, "reason": "status-yes" if ok else reason}


def show_status(rows, as_json=False):
    if as_json:
        print(json.dumps(rows), flush=True)
    else:
        for row in rows:
            print(f"{row['cli']}: logged in {'yes' if row['logged_in'] else 'no'}; "
                  f"path={row['credential_path'] or 'Keychain/keyring (no portable file)'}; "
                  f"mtime={row['mtime']}; {row['reason']}", flush=True)


def clean_terminal(text):
    # Strip OSC hyperlinks but preserve their visible URL, then CSI/charset escapes.
    text = re.sub(r"\x1b\].*?(?:\x07|\x1b\\)", "", text, flags=re.S)
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"\x1b[()][A-Z0-9]", "", text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def login_url(text):
    """Extract a URL only after a following prompt/blank line closes it.

    Newlines/indentation inside a TUI-wrapped URL are removed; prose is not.
    Caller waits for output quiescence before using a final unterminated line.
    """
    lines = clean_terminal(text).splitlines()
    found = []
    for i, line in enumerate(lines):
        match = re.search(r"https://[^\s<>\"\x00-\x1f]+", line)
        if not match:
            continue
        url = match.group().rstrip("│┃")
        for following in lines[i + 1:]:
            part = following.strip().strip("│┃").strip()
            if not part or re.search(r"\s", part) or not re.fullmatch(r"[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+", part):
                break
            if part.startswith("https://") or part.lower() in ("code:", "enter:"):
                break
            url += part
        # Only sign-in providers; never display arbitrary URLs from error output.
        if re.match(r"https://(?:accounts\.google\.com|auth\.openai\.com|chatgpt\.com|claude\.ai|platform\.claude\.com|console\.anthropic\.com)(?:/|$)", url):
            found.append(url)
    return max(found, key=len) if found else None


class PosixTerminal:
    def __init__(self, argv):
        import fcntl
        import pty
        import struct
        import termios
        self.master, slave = pty.openpty()
        attrs = termios.tcgetattr(slave)
        attrs[3] &= ~termios.ECHO
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 240, 0, 0))
        try:
            self.process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave,
                                            start_new_session=True)
        finally:
            os.close(slave)

    def read(self):
        return os.read(self.master, 65536)

    def write(self, data):
        os.write(self.master, data)

    def close(self):
        import signal
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
        os.close(self.master)


class WindowsTerminal:
    """Native ConPTY through ctypes (Windows 10 1809+); no pywinpty required."""
    def __init__(self, argv):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        k = self.k = c.WinDLL("kernel32", use_last_error=True)
        class COORD(c.Structure):
            _fields_ = [("X", c.c_short), ("Y", c.c_short)]
        class STARTUPINFO(c.Structure):
            _fields_ = [("cb", w.DWORD), ("reserved", w.LPWSTR), ("desktop", w.LPWSTR),
                        ("title", w.LPWSTR), ("x", w.DWORD), ("y", w.DWORD),
                        ("xs", w.DWORD), ("ys", w.DWORD), ("xc", w.DWORD),
                        ("yc", w.DWORD), ("fill", w.DWORD), ("flags", w.DWORD),
                        ("show", w.WORD), ("cb2", w.WORD), ("reserved2", c.c_void_p),
                        ("stdin", w.HANDLE), ("stdout", w.HANDLE), ("stderr", w.HANDLE)]
        class STARTUPINFOEX(c.Structure):
            _fields_ = [("si", STARTUPINFO), ("attrs", c.c_void_p)]
        class PROCESSINFO(c.Structure):
            _fields_ = [("process", w.HANDLE), ("thread", w.HANDLE),
                        ("pid", w.DWORD), ("tid", w.DWORD)]
        signatures = {
            "CreatePipe": ([c.POINTER(w.HANDLE), c.POINTER(w.HANDLE), c.c_void_p, w.DWORD], w.BOOL),
            "CreatePseudoConsole": ([COORD, w.HANDLE, w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)], c.c_long),
            "InitializeProcThreadAttributeList": ([c.c_void_p, w.DWORD, w.DWORD, c.POINTER(c.c_size_t)], w.BOOL),
            "UpdateProcThreadAttribute": ([c.c_void_p, w.DWORD, c.c_size_t, c.c_void_p, c.c_size_t, c.c_void_p, c.c_void_p], w.BOOL),
            "CreateProcessW": ([w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL, w.DWORD, c.c_void_p, w.LPCWSTR, c.c_void_p, c.POINTER(PROCESSINFO)], w.BOOL),
            "ReadFile": ([w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p], w.BOOL),
            "WriteFile": ([w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p], w.BOOL),
            "CloseHandle": ([w.HANDLE], w.BOOL),
            "ClosePseudoConsole": ([w.HANDLE], None),
            "TerminateProcess": ([w.HANDLE, w.UINT], w.BOOL),
            "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
            "DeleteProcThreadAttributeList": ([c.c_void_p], None),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(k, name)
            fn.argtypes, fn.restype = args, result
        self.handles = []
        self.console = w.HANDLE()
        self.pi = PROCESSINFO()
        self.attrs = None
        try:
            inp, self.writer, self.reader, out = (w.HANDLE() for _ in range(4))
            for r, v in [(inp, self.writer), (self.reader, out)]:
                if not k.CreatePipe(c.byref(r), c.byref(v), None, 0):
                    raise OSError("pipe creation failed")
                self.handles.extend([r, v])
            if k.CreatePseudoConsole(COORD(240, 40), inp, out, 0, c.byref(self.console)) != 0:
                raise OSError("ConPTY unavailable")
            size = c.c_size_t()
            k.InitializeProcThreadAttributeList(None, 1, 0, c.byref(size))
            self.attrs = c.create_string_buffer(size.value)
            if not k.InitializeProcThreadAttributeList(self.attrs, 1, 0, c.byref(size)):
                raise OSError("attribute initialization failed")
            if not k.UpdateProcThreadAttribute(self.attrs, 0, 0x20016, self.console, c.sizeof(w.HANDLE), None, None):
                raise OSError("ConPTY attachment failed")
            si = STARTUPINFOEX()
            si.si.cb = c.sizeof(si)
            si.attrs = c.cast(self.attrs, c.c_void_p)
            if not k.CreateProcessW(None, c.create_unicode_buffer(subprocess.list2cmdline(argv)),
                                    None, None, False, 0x80000, None, None, c.byref(si), c.byref(self.pi)):
                raise OSError("CLI launch failed")
            for handle in (inp, out):
                k.CloseHandle(handle)
                self.handles.remove(handle)
        except BaseException:
            self.close()
            raise

    def read(self):
        buf = self.c.create_string_buffer(65536)
        count = self.w.DWORD()
        if not self.k.ReadFile(self.reader, buf, len(buf), self.c.byref(count), None):
            return b""
        return buf.raw[:count.value]

    def write(self, data):
        count = self.w.DWORD()
        if not self.k.WriteFile(self.writer, data, len(data), self.c.byref(count), None):
            raise OSError("PTY write failed")

    def close(self):
        if self.pi.process:
            self.k.TerminateProcess(self.pi.process, 1)
            self.k.WaitForSingleObject(self.pi.process, 3000)
            self.k.CloseHandle(self.pi.process)
            self.k.CloseHandle(self.pi.thread)
        if self.console:
            self.k.ClosePseudoConsole(self.console)
        for handle in self.handles:
            self.k.CloseHandle(handle)
        if self.attrs is not None:
            self.k.DeleteProcThreadAttributeList(self.attrs)


def login(cli, timeout=1700):
    args = {"claude": ["auth", "login"], "codex": ["login", "--device-auth"], "agy": []}[cli]
    terminal = (WindowsTerminal if os.name == "nt" else PosixTerminal)(command(cli, args))
    events = queue.Queue()
    def read_output():
        try:
            while True:
                data = terminal.read()
                if not data:
                    break
                events.put(("output", data))
        except OSError:
            pass
        finally:
            events.put(("eof", b""))
    def read_code():
        # One line only. Never echo it or include it in exception output.
        events.put(("code", sys.stdin.readline(8192)))
    threading.Thread(target=read_output, daemon=True).start()
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    text = ""
    opened = sent_menu = reading = sent_code = False
    last_output = time.monotonic()
    next_check = last_output + 2
    deadline = last_output + timeout
    try:
        while time.monotonic() < deadline:
            try:
                kind, data = events.get(timeout=.15)
            except queue.Empty:
                kind, data = "idle", b""
            if kind == "output":
                text = (text + decoder.decode(data))[-131072:]
                last_output = time.monotonic()
                if b"\x1b[6n" in data:
                    terminal.write(b"\x1b[1;1R")  # ConPTY cursor-position query
            elif kind == "code":
                if not data or not data.strip():
                    return 1
                terminal.write(data.rstrip("\r\n").encode() + b"\r")
                sent_code = True
            cleaned = clean_terminal(text)
            if cli == "agy" and not sent_menu and "Select login method" in cleaned:
                terminal.write(b"\r")
                sent_menu = True
            quiet = time.monotonic() - last_output > .5 or kind == "eof"
            prompt = re.search(r"(?:paste|enter)[^\n]{0,100}code[^\n]{0,60}(?:[:>]|Enter)", cleaned, re.I)
            device_code = re.search(r"\b[A-Z0-9]{4,6}-[A-Z0-9]{4,6}\b", cleaned)
            if not opened and quiet and (prompt or cli == "codex" and device_code):
                url = login_url(text)
                if url:
                    print("OPEN: " + url, flush=True)
                    opened = True
            if cli == "codex" and opened:
                code = device_code
                if code and not reading:
                    print("CODE: " + code.group(), flush=True)
                    reading = True
            elif opened and prompt and not reading:
                threading.Thread(target=read_code, daemon=True).start()
                reading = True
            if kind == "eof":
                break
            if time.monotonic() >= next_check and (sent_code or cli == "codex" and opened):
                next_check = time.monotonic() + 3
                if status(cli)["logged_in"]:
                    return 0
        return 0 if status(cli)["logged_in"] else 1
    finally:
        terminal.close()


def portable_path(cli):
    path = credential_path(cli)
    if path is None:
        raise Refused("No verified portable credential file; see docs/ops/cli-login.md")
    return path


def payload(cli):
    path = portable_path(cli)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= LIMIT:
        raise Refused("Credential file absent, unsafe or too large")
    data = path.read_bytes()
    return json.dumps({"cli": cli, "data": base64.b64encode(data).decode("ascii")}).encode()


def secure_file(path):
    os.chmod(path, 0o600)
    if os.name == "nt":
        # chmod does not implement Unix permissions on NTFS. Replace inherited
        # access with the current user's SID before writing any secret bytes.
        who = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, check=True)
        sid = re.search(rb"S-1-\d+(?:-\d+)+", who.stdout)
        if not sid:
            raise Refused("Cannot resolve Windows owner SID")
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                        "*" + sid.group().decode() + ":F"], capture_output=True, check=True)


def receive(cli, data):
    path = portable_path(cli)
    if len(data) > LIMIT * 2:
        raise Refused("Transfer too large")
    envelope = json.loads(data)
    if set(envelope) != {"cli", "data"} or envelope["cli"] != cli:
        raise Refused("Wrong transfer envelope")
    raw = base64.b64decode(envelope["data"], validate=True)
    if not 0 < len(raw) <= LIMIT:
        raise Refused("Empty or oversized credential")
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise Refused("Symlink credential destination refused")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".cli-login-", dir=path.parent)
    try:
        secure_file(name)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if fd != -1:
            os.close(fd)
        if os.path.exists(name):
            os.unlink(name)


def remote_command(host, action, cli):
    if host == "mac":
        raise Refused("Mac inbound SSH is restricted; use a Mac Run card with pull --from contabo")
    if host == "winbox":
        remote = f'python C:/Users/passg/mooniex/repo/MoonieX-Agents/tools/cli_login.py {action} {cli}'
        alias = "winbox"
    else:
        remote = f'python3 /opt/MoonieXHQ/Agents/Core/tools/cli_login.py {action} {cli}'
        alias = "mooniex-vps"
    return ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", alias, remote]


def transfer(cli, host, pull=False):
    argv = remote_command(host, "_export" if pull else "_receive", cli)
    result = subprocess.run(argv, input=b"" if pull else payload(cli),
                            capture_output=True, timeout=120)
    if result.returncode:
        raise Refused("SSH transfer or remote status failed (remote output suppressed)")
    if pull:
        receive(cli, result.stdout)
        row = status(cli)
        show_status([row])
        return 0 if row["logged_in"] else 1
    # Remote output is untrusted and may include credentials. Do not forward it.
    print(f"{cli}: transfer complete; remote status yes", flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    s.add_argument("--cli", choices=CLIS)
    for action in ("login", "push", "pull", "_receive", "_export"):
        p = sub.add_parser(action)
        p.add_argument("cli", choices=CLIS)
        if action == "push":
            p.add_argument("--to", choices=HOSTS, required=True)
        if action == "pull":
            p.add_argument("--from", dest="source", choices=HOSTS, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            rows = [status(cli) for cli in ([args.cli] if args.cli else CLIS)]
            show_status(rows, args.json)
            return 0 if all(r["logged_in"] for r in rows) else 1
        if args.action == "login":
            return login(args.cli)
        if args.action in ("push", "pull"):
            return transfer(args.cli, args.source if args.action == "pull" else args.to,
                            pull=args.action == "pull")
        if args.action == "_receive":
            receive(args.cli, sys.stdin.buffer.read(LIMIT * 2 + 1))
            row = status(args.cli)
            show_status([row])
            return 0 if row["logged_in"] else 1
        if args.action == "_export":
            # Internal pull endpoint only. No terminal output; SSH captures this
            # directly into the receiver's memory, never the Run-card log.
            if sys.stdout.isatty() or "SSH_CONNECTION" not in os.environ:
                raise Refused("Export requires an SSH pipe")
            sys.stdout.buffer.write(payload(args.cli))
            return 0
    except (OSError, ValueError, Refused, subprocess.SubprocessError):
        # Exception messages can contain subprocess output, codes or tokens.
        print("CLI login operation failed; check paths, supported storage and connectivity in the ops guide.", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
