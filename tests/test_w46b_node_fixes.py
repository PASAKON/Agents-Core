"""Org Mesh W4.6b: the node side and the endpoint side of security review task-79219f24.

  F1  accept (and the keys it needs) come before the long install; the node prints a fingerprint
      line; the poll says it is waiting for approval.
  F9  no --token: the token is asked for on /dev/tty with echo off, restored on every way out.
  F7  GitHub's SSH host keys go into known_hosts before the clone, which uses
      StrictHostKeyChecking=yes; no fallback when the fetch fails.
  F6  every python join.sh starts runs `-I`, and the probe still finds the repo modules.
  F11 tools/join_api.py lets 4 requests into the database at once and answers 503 "busy" to the rest.
  F3  (part) org-join.service carries the sandbox directives.

Nothing here installs anything, contacts GitHub, Infisical or a package manager, runs `sudo`, or
touches the real HOME. `curl` and `git` are shims that record what they were asked and answer from a
file; the endpoint tests run the real server on a throwaway SQLite ledger. join.ps1 cannot run on
this machine: it is read as text (and parsed where pwsh exists, in test_w43_join_scripts.py).

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w46b_node_fixes.py
"""
from __future__ import annotations

import ast
import http.client
import http.server
import inspect
import json
import logging
import os
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, db  # noqa: E402
from tools import hq_join, join_api  # noqa: E402

JOIN_SH = ROOT / "deploy" / "join" / "join.sh"
JOIN_PS1 = ROOT / "deploy" / "join" / "join.ps1"
UNIT = ROOT / "deploy" / "join" / "org-join.service"
README = ROOT / "deploy" / "join" / "README.md"

TOKEN = "hqj_" + "Tok3n_-" * 6 + "T"                # hqj_ + 43 characters
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
DEPLOY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA" + "A" * 43 + " org-node:node-a"
FINGERPRINT = PUB[-8:]
FPR_LINE = f"fingerprint: {FINGERPRINT} - the operator approves this in the Run Inbox"

# Synthetic key material: only its shape matters to join.sh.
GH_KEYS = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl",
    "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=",
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YSPKS4Dae+f2bV7sEcZhVuBi3bf+8mSXGLEnYtKxfeK4vnNKQIDzjBM6B+JE0HiBw==",
]

not_root = pytest.mark.skipif(os.geteuid() == 0, reason="as root the unreadable-file cases always read")


# ---------------------------------------------------------------- helpers

def _exe(path: Path, text: str) -> Path:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _env(tmp_path: Path, bindir: Path | None = None, **extra) -> dict:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    path = os.environ["PATH"] if bindir is None else f"{bindir}{os.pathsep}{os.environ['PATH']}"
    env = {"PATH": path, "HOME": str(home), "LC_ALL": "C", "TMPDIR": str(tmp_path)}
    env.update(extra)
    return env


def _run(args, *, env, stdin_text=None, timeout=60, cwd=None):
    # start_new_session: no controlling terminal, so a missing token cannot stop a test run on a prompt.
    return subprocess.run(args, input=stdin_text, capture_output=True, text=True, env=env, timeout=timeout,
                          cwd=cwd, start_new_session=True)


def _code_lines(path: Path) -> list[str]:
    """Lines of a script without the comment-only ones (a comment may say 'accept-new')."""
    return [ln for ln in path.read_text().splitlines() if not ln.lstrip().startswith("#")]


def _function(text: str, name: str, *, ps1=False) -> str:
    pat = (r"^function " + re.escape(name) + r"(?:\([^)]*\))? \{.*?^\}") if ps1 else (r"^" + re.escape(name) + r"\(\) \{.*?^\}")
    m = re.search(pat, text, re.S | re.M)
    assert m, name
    return m.group(0)


@pytest.fixture
def ledger(monkeypatch, tmp_path):
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()


@pytest.fixture
def server(ledger, caplog):
    caplog.set_level(logging.INFO)
    made = []

    def start(**kw):
        srv = join_api.make_server(0, **kw)
        t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        t.start()
        srv.port = srv.server_address[1]
        srv.url = f"http://127.0.0.1:{srv.port}/org-join"
        made.append((srv, t))
        return srv

    yield start
    for srv, t in made:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=5)


def _lib(tmp_path, body: str, *, hub: str = "http://127.0.0.1:1/org-join", token=TOKEN, extra=None,
         bindir: Path | None = None, timeout=60):
    """Source join.sh without running it, set what check_args/do_keys would have set, run `body`."""
    home = tmp_path / "home"
    env = _env(tmp_path, bindir, ORG_JOIN_LIB="1", JOIN_SH=str(JOIN_SH), T_HUB=hub, T_TOKEN=token,
               T_PUB=PUB, T_DEPLOY=DEPLOY, T_HOME=str(home))
    env.update(extra or {})
    prelude = (
        '. "$JOIN_SH"\n'
        'HUB=$T_HUB; HOST=node-a; TOKEN=$T_TOKEN; OS=linux; HQ_ROOT=$T_HOME/hq; PY=python3\n'
        'CORE=$HQ_ROOT/Agents/Core\n'
        'AGE_PUB=$T_PUB; DEPLOY_PUB=$T_DEPLOY; DRY_RUN=0\n'
        'CONF_DIR=$T_HOME/.config/mooniex; AGE_ID=$CONF_DIR/age-identity.txt; DEPLOY_KEY=$CONF_DIR/deploy_key\n'
    )
    return _run(["sh", "-c", prelude + body], env=env, timeout=timeout)


class _StubHub(http.server.BaseHTTPRequestHandler):
    """A hub that answers from a script: {route: [(status, json body), ...]}, the last one repeating."""
    script: dict = {}
    seen: list = []

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        route = self.path.rsplit("/", 1)[-1]
        answers = self.script[route]
        status, body = answers.pop(0) if len(answers) > 1 else answers[0]
        self.seen.append((route, status))
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@contextmanager
def _stub_hub(script: dict):
    handler = type("H", (_StubHub,), {"script": {k: list(v) for k, v in script.items()}, "seen": []})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/org-join", handler
    finally:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=5)


# ---------------------------------------------------------------- F1: accept before install

def test_main_calls_keys_and_accept_before_install():
    main = _function(JOIN_SH.read_text(), "main")
    order = [re.search(rf"^  {fn}\b", main, re.M).start()
             for fn in ("do_keys", "do_accept", "do_install", "do_tailscale",
                        "do_wait_sealed", "do_clone", "do_identity", "do_probe")]
    assert order == sorted(order), main


def test_dry_run_prints_keys_and_accept_before_the_install_step(tmp_path):
    r = _run(["sh", str(JOIN_SH), "--token", TOKEN, "--host", "node-a", "--hub", "https://hub.example.test",
              "--hq-root", str(tmp_path / "hq"), "--dry-run"], env=_env(tmp_path))
    assert r.returncode == 0, r.stderr
    at = {n: r.stdout.find(f"[{n}/9]") for n in range(1, 10)}
    assert all(p >= 0 for p in at.values()) and list(at.values()) == sorted(at.values())
    assert re.search(r"\[2/9\] make the node's keys", r.stdout)
    assert re.search(r"\[3/9\] accept", r.stdout)
    assert re.search(r"\[4/9\] install", r.stdout)
    # the fingerprint line is promised inside step 3, before step 4's install
    fpr = r.stdout.find("fingerprint: <last 8 characters of the age recipient> - the operator approves this in the Run Inbox")
    assert at[3] < fpr < at[4], r.stdout
    # the long install is what waits: the key tools it needs first come with step 2
    assert "only the tools" in r.stdout[at[2]:at[3]]


def test_join_ps1_calls_keys_and_accept_before_install_and_numbers_the_steps_to_match():
    text = JOIN_PS1.read_text(encoding="ascii")
    body = text[text.rindex("Read-Args"):]
    order = [body.index(fn) for fn in ("New-Keys", "Send-Accept", "Install-Missing", "Join-Tailnet",
                                       "Wait-Sealed", "Copy-Core", "Save-Identity", "Invoke-Probe")]
    assert order == sorted(order), body
    for fn, n in (("New-Keys", 2), ("Send-Accept", 3), ("Install-Missing", 4), ("Join-Tailnet", 5)):
        assert f"Step {n} " in _function(text, fn, ps1=True), (fn, n)


def test_accept_prints_one_fingerprint_line_and_only_the_tail_of_the_recipient(server, tmp_path):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    r = _lib(tmp_path, "do_accept", hub=srv.url, token=token)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("fingerprint:") == 1
    assert f"    {FPR_LINE}\n" in r.stdout
    assert r.stdout.index("accepted") < r.stdout.index("fingerprint:")
    assert len(FINGERPRINT) == 8 and PUB not in r.stdout        # the tail only, never the whole key
    assert token not in r.stdout + r.stderr


def test_a_second_run_with_the_same_token_shows_the_fingerprint_again(server, tmp_path):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    assert _lib(tmp_path, "do_accept", hub=srv.url, token=token).returncode == 0
    again = _lib(tmp_path, "do_accept", hub=srv.url, token=token)
    assert again.returncode == 0 and "already joined" in again.stdout
    assert FPR_LINE in again.stdout


def test_a_refused_token_shows_no_fingerprint(server, tmp_path):
    srv = server()
    r = _lib(tmp_path, "do_accept", hub=srv.url, token="hqj_" + "Q" * 43)
    assert r.returncode == 1 and "fingerprint" not in r.stdout


def test_the_wait_step_says_it_is_waiting_for_the_operator_and_names_the_fingerprint(server, tmp_path):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    _lib(tmp_path, "do_accept", hub=srv.url, token=token)        # the host stays pending_identity
    r = _lib(tmp_path, "POLL_S=1; POLL_MAX_S=1; do_wait_sealed", hub=srv.url, token=token)
    assert r.returncode == 1 and "gave up waiting" in r.stderr
    assert f"waiting for the operator to approve fingerprint {FINGERPRINT} in the Run Inbox" in r.stdout
    assert f"operator approves fingerprint {FINGERPRINT}" in r.stdout        # the step's own header line


# ---------------------------------------------------------------- F11 node side: a busy hub

def test_accept_on_a_busy_hub_stops_with_a_clear_message_and_no_fingerprint(tmp_path):
    with _stub_hub({"accept": [(503, {"error": "busy"})]}) as (hub, _):
        r = _lib(tmp_path, "do_accept", hub=hub)
    assert r.returncode == 1
    assert "the hub is busy" in r.stderr and "run the same command again" in r.stderr
    assert "unexpected answer" not in r.stderr and "fingerprint" not in r.stdout


def test_the_sealed_fallback_after_a_used_token_also_reports_busy(tmp_path):
    with _stub_hub({"accept": [(403, {"error": "refused"})], "sealed": [(503, {"error": "busy"})]}) as (hub, _):
        r = _lib(tmp_path, "do_accept", hub=hub)
    assert r.returncode == 1 and "the hub is busy" in r.stderr and "unknown, already used" not in r.stderr


def test_the_wait_step_keeps_polling_through_a_busy_answer(tmp_path):
    script = {"sealed": [(503, {"error": "busy"}), (200, {"status": "ready", "ciphertext": "CIPHERTEXT-1"})]}
    with _stub_hub(script) as (hub, handler):
        r = _lib(tmp_path, 'POLL_S=1; POLL_MAX_S=30; do_wait_sealed; printf "GOT=%s\\n" "$CIPHER"', hub=hub)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "HTTP 503, retrying" in r.stdout and "GOT=CIPHERTEXT-1" in r.stdout
    assert [s for _, s in handler.seen] == [503, 200]


# ---------------------------------------------------------------- F9: the token from the terminal

def test_no_token_and_no_terminal_stops_at_step_1(tmp_path):
    r = _run(["sh", str(JOIN_SH), "--host", "node-a", "--hub", "https://hub.example.test", "--dry-run"],
             env=_env(tmp_path))
    assert r.returncode == 1 and "no token" in r.stderr and "nothing was typed, or there is no terminal" in r.stderr
    assert "[2/9]" not in r.stdout


pty_mod = pytest.importorskip("pty", reason="needs a pty")
termios = pytest.importorskip("termios", reason="needs a pty")
fcntl = pytest.importorskip("fcntl", reason="needs a pty")


def _echo_on(fd: int) -> bool:
    return bool(termios.tcgetattr(fd)[3] & termios.ECHO)


class _Pty:
    """join.sh running with a real controlling terminal, both ends of which the test holds.

    An outer `sh` is the session leader and stays alive until released, because the terminal is
    revoked when its session leader exits and termios could no longer be read. The inner `sh` runs
    join.sh; its exit code and pid go to files."""

    def __init__(self, tmp_path: Path, body: str):
        self.master, self.slave = pty_mod.openpty()
        self.out, self.rc_file = tmp_path / "token-out.txt", tmp_path / "inner.rc"
        self.pid_file, self.go_file = tmp_path / "inner.pid", tmp_path / "release"
        env = _env(tmp_path, ORG_JOIN_LIB="1", JOIN_SH=str(JOIN_SH), OUT=str(self.out), RC=str(self.rc_file),
                   PIDF=str(self.pid_file), GO=str(self.go_file),
                   INNER='echo $$ > "$PIDF"\n. "$JOIN_SH"\n' + body)
        outer = 'sh -c "$INNER"; echo $? > "$RC"; while [ ! -e "$GO" ]; do sleep 0.05; done'

        def _ctty():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        self.proc = subprocess.Popen(["sh", "-c", outer], stdin=self.slave, stdout=self.slave, stderr=self.slave,
                                     env=env, preexec_fn=_ctty, close_fds=True)
        self.seen = b""

    def _drain(self, wait: float) -> bool:
        r, _, _ = select.select([self.master], [], [], wait)
        if not r:
            return False
        try:
            chunk = os.read(self.master, 4096)
        except OSError:
            return False
        self.seen += chunk
        return bool(chunk)

    def read_until(self, needle: bytes, timeout=15.0) -> bytes:
        end = time.time() + timeout
        while needle not in self.seen and time.time() < end:
            self._drain(0.2)
        assert needle in self.seen, self.seen
        return self.seen

    def signal(self, sig: int) -> None:
        end = time.time() + 10
        while not (self.pid_file.exists() and self.pid_file.read_text().strip()) and time.time() < end:
            time.sleep(0.02)
        os.kill(int(self.pid_file.read_text()), sig)

    def finish(self, timeout=15.0) -> int:
        """The inner shell's exit code. The terminal is still open afterwards (the outer shell waits)."""
        end = time.time() + timeout
        while not (self.rc_file.exists() and self.rc_file.read_text().strip()) and time.time() < end:
            self._drain(0.1)
        assert self.rc_file.exists(), self.seen
        while self._drain(0.05):
            pass
        return int(self.rc_file.read_text())

    def close(self):
        self.go_file.write_text("")
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        for fd in (self.master, self.slave):
            try:
                os.close(fd)
            except OSError:
                pass


@pytest.fixture
def tty(tmp_path):
    made = []

    def start(body):
        p = _Pty(tmp_path, body)
        made.append(p)
        return p

    yield start
    for p in made:
        p.close()


ASK = ('parse_args --host node-a --hub https://hub.example.test --hq-root /x\n'
       'check_args\n'
       'printf %s "$TOKEN" > "$OUT"\n')
PROMPT = b"Join token (typing is hidden): "


def test_the_token_is_read_from_the_terminal_with_echo_off_and_echo_comes_back(tty):
    t = tty(ASK)
    t.read_until(PROMPT)
    assert not _echo_on(t.slave), "echo must be off while the prompt waits"
    os.write(t.master, TOKEN.encode() + b"\n")
    assert t.finish() == 0, t.seen
    assert t.out.read_text() == TOKEN                       # check_args accepted it and kept it
    assert TOKEN.encode() not in t.seen                      # the terminal never echoed a character of it
    assert _echo_on(t.slave), "echo must be restored after the read"


def test_echo_is_restored_when_the_run_is_killed_at_the_prompt(tty):
    t = tty(ASK)
    t.read_until(PROMPT)
    assert not _echo_on(t.slave)
    t.signal(signal.SIGTERM)
    assert t.finish() == 143
    assert _echo_on(t.slave), "the TERM trap must restore echo"
    assert not t.out.exists()


def test_echo_is_restored_on_interrupt_too(tty):
    t = tty(ASK)
    t.read_until(PROMPT)
    t.signal(signal.SIGINT)
    assert t.finish() == 130
    assert _echo_on(t.slave)


def test_end_of_input_at_the_prompt_is_no_token_and_echo_is_restored(tty):
    t = tty(ASK)
    t.read_until(PROMPT)
    os.write(t.master, b"\x04")                              # ^D at the start of the line: EOF
    assert t.finish() == 1
    assert b"no token" in t.seen and _echo_on(t.slave)


def test_a_token_in_the_wrong_shape_dies_with_echo_restored(tty):
    t = tty(ASK)
    t.read_until(PROMPT)
    os.write(t.master, b"hqj_short\n")
    assert t.finish() == 1
    assert b"not in the expected shape" in t.seen
    assert _echo_on(t.slave)


def test_a_token_given_as_an_argument_is_never_asked_for(tty):
    t = tty(f'parse_args --token {TOKEN} --host node-a --hub https://hub.example.test --hq-root /x\n'
            'check_args\nprintf %s "$TOKEN" > "$OUT"\n')
    assert t.finish() == 0
    assert b"Join token" not in t.seen and t.out.read_text() == TOKEN


def test_join_ps1_asks_for_a_missing_token_as_a_secure_string_and_never_prints_it():
    text = JOIN_PS1.read_text(encoding="ascii")
    ask = _function(text, "Read-TokenPrompt", ps1=True)
    assert "Read-Host" in ask and "-AsSecureString" in ask
    assert "SecureStringToBSTR" in ask and "PtrToStringBSTR" in ask and "ZeroFreeBSTR" in ask
    assert "Write-Host" not in ask and "Say " not in ask
    init = _function(text, "Initialize-Args", ps1=True)
    assert init.index("Read-TokenPrompt") < init.index("no token:")
    assert "$script:Token = Read-TokenPrompt" in init


def test_both_scripts_and_the_readme_say_the_no_argument_form_is_the_preferred_one():
    sh_head = "\n".join(JOIN_SH.read_text().splitlines()[:25])
    ps_head = "\n".join(JOIN_PS1.read_text().splitlines()[:25])
    assert "preferred" in sh_head and "typing hidden" in sh_head and "--token" in sh_head
    assert "preferred" in ps_head and "AsSecureString" in ps_head
    readme = README.read_text()
    assert "preferred form has no token in it" in readme
    assert "sh -s -- --host <name>" in readme and "ORG_JOIN_TOKEN" in readme and "--token <t>" in readme


# ---------------------------------------------------------------- F7: pinned GitHub host keys

def _shims(tmp_path: Path, *, meta: str | None, curl_rc: int = 0) -> tuple[Path, Path]:
    """curl answers the api.github.com/meta call from a file (or fails), git records how it was
    started and fakes a clone, and the venv python it leaves behind records its arguments."""
    bindir, log = tmp_path / "shims", tmp_path / "shim.log"
    bindir.mkdir()
    meta_file = tmp_path / "meta.json"
    if meta is not None:
        meta_file.write_text(meta)
    _exe(bindir / "curl", (
        '#!/bin/sh\n'
        f'echo "curl $*" >> "{log}"\n'
        f'[ {curl_rc} -eq 0 ] || exit {curl_rc}\n'
        f'case "$*" in *api.github.com/meta*) cat "{meta_file}" ;; *) exec /usr/bin/curl "$@" ;; esac\n'))
    _exe(bindir / "git", (
        '#!/bin/sh\n'
        f'echo "git $*" >> "{log}"\n'
        f'echo "GIT_SSH_COMMAND=$GIT_SSH_COMMAND" >> "{log}"\n'
        'kh=$(printf %s "$GIT_SSH_COMMAND" | sed -n "s/.*UserKnownHostsFile=\\([^ ]*\\).*/\\1/p" | tr -d "\'")\n'
        f'if [ -s "$kh" ]; then echo "known_hosts present at clone time" >> "{log}"; '
        f'else echo "known_hosts MISSING at clone time" >> "{log}"; fi\n'
        'if [ "$1" = clone ]; then\n'
        '  mkdir -p "$3/.git" "$3/.venv/bin"\n'
        f'  printf \'#!/bin/sh\\necho "venv-python $*" >> "{log}"\\n\' > "$3/.venv/bin/python"\n'
        '  chmod +x "$3/.venv/bin/python"\n'
        '  : > "$3/requirements.txt"\n'
        'fi\n'))
    return bindir, log


def _meta(keys=None, **extra) -> str:
    return json.dumps({"hooks": ["192.0.2.0/24"], "ssh_keys": GH_KEYS if keys is None else keys, **extra})


def _clone(tmp_path, *, meta, curl_rc=0):
    bindir, log = _shims(tmp_path, meta=meta, curl_rc=curl_rc)
    r = _lib(tmp_path, "do_clone", bindir=bindir)
    return r, log, tmp_path / "home" / ".config" / "mooniex" / "known_hosts"


def test_known_hosts_holds_github_keys_from_the_api_before_git_runs(tmp_path):
    r, log, kh = _clone(tmp_path, meta=_meta())
    assert r.returncode == 0, r.stdout + r.stderr
    assert kh.read_text().splitlines() == [f"github.com {k}" for k in GH_KEYS]
    calls = log.read_text()
    assert "curl -fsS --max-time 30 -H Accept: application/vnd.github+json https://api.github.com/meta" in calls
    assert " -k " not in calls and "--insecure" not in calls                      # TLS is verified
    assert calls.index("curl ") < calls.index("git clone ")
    assert "known_hosts present at clone time" in calls and "MISSING" not in calls
    assert f"git clone git@github.com:PASAKON/Agents-Core.git {tmp_path}/home/hq/Agents/Core" in calls


def test_the_clone_uses_strict_host_key_checking_and_only_that_known_hosts_file(tmp_path):
    r, log, kh = _clone(tmp_path, meta=_meta())
    assert r.returncode == 0, r.stdout + r.stderr
    ssh = next(ln for ln in log.read_text().splitlines() if ln.startswith("GIT_SSH_COMMAND="))
    assert "-o StrictHostKeyChecking=yes" in ssh and "accept-new" not in ssh and "=no" not in ssh
    assert f"-o UserKnownHostsFile='{kh}'" in ssh
    assert "IdentitiesOnly=yes" in ssh and "BatchMode=yes" in ssh


def test_a_failed_fetch_stops_the_run_and_git_is_never_started(tmp_path):
    r, log, kh = _clone(tmp_path, meta=None, curl_rc=22)
    assert r.returncode == 1
    assert "could not fetch GitHub's SSH host keys" in r.stderr and "Not cloning" in r.stderr
    assert "no trust-on-first-use" in r.stderr
    assert "git " not in log.read_text() and not kh.exists()


@pytest.mark.parametrize("meta", [
    "<html>captive portal</html>",                               # not JSON
    json.dumps({"hooks": []}),                                   # no ssh_keys
    json.dumps({"ssh_keys": []}),                                # none listed
    json.dumps({"ssh_keys": ["ssh-ed25519 short", "ssh-dss AAAAB3NzaC1kc3MAAACB" + "A" * 30, 7, None,
                             "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMq; rm -rf /"]}),   # nothing well formed
])
def test_a_reply_with_no_usable_host_key_stops_the_run(tmp_path, meta):
    r, log, kh = _clone(tmp_path, meta=meta)
    assert r.returncode == 1 and "did not list any SSH host key in the expected shape" in r.stderr
    assert "git " not in log.read_text() and not kh.exists()


def test_only_well_formed_keys_are_written_and_a_stale_file_is_replaced_not_appended(tmp_path):
    kh = tmp_path / "home" / ".config" / "mooniex" / "known_hosts"
    kh.parent.mkdir(parents=True)
    kh.write_text("github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC" + "E" * 40 + "\n")    # trusted on first use
    meta = _meta(keys=[GH_KEYS[0], "not a key", "ssh-ed25519 AAAA\nsneaky", GH_KEYS[1]])
    r, _, _ = _clone(tmp_path, meta=meta)
    assert r.returncode == 0, r.stdout + r.stderr
    assert kh.read_text().splitlines() == [f"github.com {GH_KEYS[0]}", f"github.com {GH_KEYS[1]}"]
    assert not (kh.parent / "known_hosts.tmp").exists()


def test_a_second_run_pulls_with_the_same_strict_settings(tmp_path):
    r, log, _ = _clone(tmp_path, meta=_meta())
    assert r.returncode == 0, r.stdout + r.stderr
    log.write_text("")
    again = _lib(tmp_path, "do_clone", bindir=tmp_path / "shims")
    assert again.returncode == 0 and "already cloned: updating" in again.stdout
    text = log.read_text()
    assert "git -C" in text and "pull --ff-only" in text and "StrictHostKeyChecking=yes" in text
    assert "known_hosts present at clone time" in text


@pytest.mark.parametrize("path", [JOIN_SH, JOIN_PS1])
def test_no_code_line_in_either_script_accepts_an_unknown_host_key(path):
    for ln in _code_lines(path):
        assert "accept-new" not in ln, ln
        assert "StrictHostKeyChecking=no" not in ln and "StrictHostKeyChecking no" not in ln, ln
    assert any("StrictHostKeyChecking=yes" in ln for ln in _code_lines(path))


def test_join_ps1_fetches_the_keys_over_tls_and_writes_them_before_the_clone():
    text = JOIN_PS1.read_text(encoding="ascii")
    assert "$script:GithubMetaUrl = 'https://api.github.com/meta'" in text
    kh = _function(text, "Write-KnownHosts", ps1=True)
    assert "Invoke-RestMethod" in kh and "Tls12" in kh and "$script:GithubMetaUrl" in kh
    assert "ssh_keys" in kh and "-cmatch" in kh and "(ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa)" in kh
    assert "UTF8Encoding($false)" in kh and "`n" in kh                       # no BOM, LF only
    assert kh.count("Die ") >= 2                                             # a fetch failure and an empty list both stop
    assert "SkipCertificateCheck" not in text and "ServerCertificateValidationCallback" not in text
    ssh = _function(text, "Get-GitSshCommand", ps1=True)
    assert "StrictHostKeyChecking=yes" in ssh and "UserKnownHostsFile" in ssh
    core = _function(text, "Copy-Core", ps1=True)
    assert core.index("Write-KnownHosts") < core.index("Get-GitSshCommand")


# ---------------------------------------------------------------- F6: python -I on every call root makes

def test_every_python_join_sh_starts_is_isolated():
    seen = 0
    for n, ln in enumerate(JOIN_SH.read_text().splitlines(), 1):
        stripped = ln.lstrip()
        if stripped.startswith(("#", "say ", "[")):
            continue
        for m in re.finditer(r'("\$PY"|"\$_p"|"\$CORE/\.venv/bin/python")( +\S+)?', ln):
            if ln[:m.start()].rstrip().endswith(("-x", "-n", "-z")):     # a [ test, not a call
                continue
            nxt = (m.group(2) or "").strip()
            assert nxt == "-I", f"join.sh:{n}: {ln.strip()}"
            seen += 1
    assert seen >= 10, seen                      # the scan really saw the calls


def test_the_extractors_the_probe_and_save_run_isolated_and_the_probe_by_path():
    text = JOIN_SH.read_text()
    probe = _function(text, "do_probe")
    probe_code = "\n".join(ln for ln in probe.splitlines() if not ln.lstrip().startswith("#"))
    assert '"$PY" -I -B "$CORE/tools/infisical_setup.py" run Agents-Core prod' in probe_code
    assert '"$CORE/.venv/bin/python" -I -B "$CORE/tools/node_dispatch.py" probe' in probe_code
    assert "PYTHONDONTWRITEBYTECODE" not in probe_code and "-m tools.node_dispatch" not in probe_code
    assert ' env HOME="$HOME" ORG_HOST="$HOST" ' in probe                      # the w44c HOME pass-through stays
    ident = _function(text, "do_identity")
    assert 'as_root "$PY" -I "$CORE/tools/infisical_setup.py" save "$HOST" --stdin' in ident
    assert '"$PY" -I -c' in ident


def test_a_recording_python_sees_dash_I_first_on_every_call_of_accept_and_clone(server, tmp_path):
    srv = server()
    bindir, log = _shims(tmp_path, meta=_meta())
    rec = tmp_path / "py-calls.log"
    shim = _exe(tmp_path / "rec-python", f'#!/bin/sh\necho "$1" >> "{rec}"\nexec "{sys.executable}" "$@"\n')
    token = hq_join.mint("node-a")["token"]
    r = _lib(tmp_path, f'PY="{shim}"\ndo_accept\ndo_clone\n', hub=srv.url, token=token, bindir=bindir)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = rec.read_text().splitlines()
    assert len(calls) >= 3, calls              # the accept body, the accept answer, the known_hosts parse
    assert set(calls) == {"-I"}, calls                                 # -I is the first argument of every call
    venv_calls = [ln for ln in log.read_text().splitlines() if ln.startswith("venv-python ")]
    assert venv_calls and all(c.startswith("venv-python -I -m pip install") for c in venv_calls), venv_calls


def test_dash_I_breaks_dash_m_from_the_checkout_which_is_why_the_probe_runs_by_path():
    # The reproduction behind the do_probe change: -I puts no current directory on sys.path, so
    # `-m tools.node_dispatch` from the checkout cannot find the `tools` package.
    env = {"PATH": os.environ["PATH"], "HOME": "/nonexistent"}
    broken = subprocess.run([sys.executable, "-I", "-B", "-m", "tools.node_dispatch", "probe"], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=60)
    assert broken.returncode != 0 and "No module named 'tools'" in broken.stderr


def test_node_dispatch_run_by_path_under_dash_I_still_finds_the_repo_modules(tmp_path):
    # Runs the file's own prelude (the sys.path.insert of the checkout, then the `lib` imports) under
    # -I without starting a verb: runpy with a run_name other than __main__ executes the module body
    # and stops, so no ledger is opened.
    code = ("import runpy, sys\n"
            f"ns = runpy.run_path({str(ROOT / 'tools' / 'node_dispatch.py')!r}, run_name='probe_import')\n"
            "assert 'verb_probe' in ns and callable(ns['main']), sorted(ns)[:5]\n"
            "print('ok', sys.flags.isolated)\n")
    r = subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=tmp_path,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)}, capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "ok 1", r.stdout + r.stderr


# ---------------------------------------------------------------- F11: the database gate

def _post(srv, route: str, body: dict):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=15)
    try:
        conn.request("POST", join_api.PREFIX + route, body=json.dumps(body),
                     headers={"Content-Type": "application/json"})
        r = conn.getresponse()
        return r.status, r.read(), {k.lower(): v for k, v in r.getheaders()}
    finally:
        conn.close()


def _accept_body(token, host="node-a"):
    return {"token": token, "host": host, "os": "linux", "hq_root": "/opt/MoonieXHQ",
            "pubkey": PUB, "deploy_pubkey": DEPLOY}


@contextmanager
def _slots_held(n: int):
    got = 0
    try:
        for _ in range(n):
            assert join_api._DB_GATE.acquire(blocking=False)
            got += 1
        yield
    finally:
        for _ in range(got):
            join_api._DB_GATE.release()


def test_the_gate_is_a_module_level_bounded_semaphore_of_4_with_a_2_second_wait():
    assert isinstance(join_api._DB_GATE, threading.BoundedSemaphore)
    assert join_api.DB_SLOTS == 4 and join_api.DB_WAIT_S == 2.0
    for n in range(4):
        assert join_api._DB_GATE.acquire(blocking=False), n
    assert not join_api._DB_GATE.acquire(blocking=False)
    for _ in range(4):
        join_api._DB_GATE.release()


def test_every_route_that_touches_the_database_takes_a_slot():
    assert "_db_slot()" in inspect.getsource(join_api._route_accept)
    assert inspect.getsource(join_api._route_sealed).count("_db_slot()") == 2     # the SELECTs, the ciphertext read
    assert "_db_slot()" not in inspect.getsource(join_api._route_script)
    db_routes = sorted(k for k, fn in join_api.ROUTES.items() if "_db_slot" in inspect.getsource(fn))
    assert db_routes == [("POST", join_api.PREFIX + "accept"), ("POST", join_api.PREFIX + "sealed")]
    # no other function reaches the database except the start-up preflight
    tree = ast.parse(Path(join_api.__file__).read_text())
    touching = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
            if attrs & {"get_conn", "accept", "sealed_ciphertext"}:
                touching.add(fn.name)
    assert touching == {"_route_accept", "_route_sealed", "_preflight"}, touching


def test_accept_answers_503_busy_when_no_slot_frees_within_the_wait(server, monkeypatch):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    monkeypatch.setattr(join_api, "DB_WAIT_S", 0.3)
    with _slots_held(join_api.DB_SLOTS):
        t0 = time.time()
        status, body, headers = _post(srv, "accept", _accept_body(token))
        waited = time.time() - t0
    assert status == 503 and json.loads(body) == {"error": "busy"}
    assert 0.25 <= waited < 5 and "retry-after" in headers
    assert headers["content-type"].startswith("application/json")
    # the refused call did nothing: the token is not used up, and the same call works right after
    status, body, _ = _post(srv, "accept", _accept_body(token))
    assert status == 200 and json.loads(body) == {"host": "node-a", "status": "pending_identity"}


def test_sealed_answers_the_same_503_for_a_good_token_and_a_made_up_one(server, monkeypatch):
    srv = server()
    token = hq_join.mint("node-a")["token"]
    assert _post(srv, "accept", _accept_body(token))[0] == 200
    monkeypatch.setattr(join_api, "DB_WAIT_S", 0.2)
    with _slots_held(join_api.DB_SLOTS):
        answers = {_post(srv, "sealed", {"host": "node-a", "token": token})[:2],
                   _post(srv, "sealed", {"host": "node-a", "token": "hqj_" + "Z" * 43})[:2],
                   _post(srv, "sealed", {"host": "node-b", "token": token})[:2]}
    assert answers == {(503, b'{"error":"busy"}')} or {s for s, _ in answers} == {503}
    assert len(answers) == 1, answers                   # no oracle: load, never the token, decides
    assert _post(srv, "sealed", {"host": "node-a", "token": token})[0] == 202


def test_a_malformed_request_is_still_refused_the_old_way_while_the_gate_is_full(server, monkeypatch):
    srv = server()
    monkeypatch.setattr(join_api, "DB_WAIT_S", 0.2)
    with _slots_held(join_api.DB_SLOTS):
        bad_shape = _post(srv, "sealed", {"host": "node-a", "token": "short"})
        bad_accept = _post(srv, "accept", {"token": "short"})
        script = urllib.request.urlopen(f"{srv.url}/join.sh", timeout=10)
    assert bad_shape[0] == 403                                       # the shape check comes before the slot
    assert bad_accept[0] in (400, 403)
    assert script.status == 200                                      # the script download needs no database


def test_no_more_than_4_requests_are_inside_the_database_at_once(server, monkeypatch):
    srv = server(limiter=join_api.RateLimiter(limit=1000))
    monkeypatch.setattr(join_api, "DB_WAIT_S", 0.25)
    lock, state = threading.Lock(), {"now": 0, "max": 0}
    release = threading.Event()

    def slow_accept(*a, **kw):
        with lock:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        release.wait(10)
        with lock:
            state["now"] -= 1
        return {"host": a[1], "status": "pending_identity"}

    monkeypatch.setattr(hq_join, "accept", slow_accept)
    results = []

    def call(i):
        try:
            results.append(_post(srv, "accept", _accept_body(TOKEN, host=f"node-{i:02d}"))[0])
        except Exception as exc:  # a dropped connection must show up in the assertion below
            results.append(repr(exc))

    threads = [threading.Thread(target=call, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
        time.sleep(0.02)                 # not one burst of 8 connects into the server's small listen backlog
    deadline = time.time() + 10
    while len(results) < 4 and time.time() < deadline:               # the 4 that found no slot answer 503
        time.sleep(0.05)
    release.set()
    for t in threads:
        t.join(15)
    assert state["max"] == 4, state
    assert sorted(results, key=str) == [200] * 4 + [503] * 4, results


def test_a_failing_handler_gives_its_slot_back(server, monkeypatch):
    srv = server()

    def boom(*a, **kw):
        raise RuntimeError("database gone")

    monkeypatch.setattr(hq_join, "accept", boom)
    for i in range(join_api.DB_SLOTS + 2):
        status, _, _ = _post(srv, "accept", _accept_body(TOKEN, host=f"node-{i:02d}"))
        assert status != 503, i                                      # never a leaked slot
    for n in range(join_api.DB_SLOTS):
        assert join_api._DB_GATE.acquire(blocking=False), n          # all 4 are free again
    for _ in range(join_api.DB_SLOTS):
        join_api._DB_GATE.release()


# ---------------------------------------------------------------- F3 (part): the unit's sandbox

DIRECTIVES = ("NoNewPrivileges", "ProtectSystem=strict", "ProtectHome", "PrivateTmp", "ProtectKernelTunables",
              "ProtectKernelModules", "ProtectControlGroups", "RestrictSUIDSGID", "LockPersonality")


def _unit_lines() -> list[str]:
    return UNIT.read_text(encoding="ascii").splitlines()


def test_the_unit_carries_every_sandbox_directive_and_explains_each_in_a_comment():
    lines = _unit_lines()
    service = lines[lines.index("[Service]"):]
    for d in DIRECTIVES:
        want = d if "=" in d else f"{d}=yes"
        assert want in service, want
        i = service.index(want)
        key = want.split("=")[0]
        assert any(ln.startswith("# " + key) for ln in service[max(0, i - 8):i]), f"{key} is not explained"


def test_the_unit_still_runs_the_root_leg_into_infisical_setup_and_then_setpriv():
    exec_start = next(ln for ln in _unit_lines() if ln.startswith("ExecStart="))
    assert ("bind-docker0.sh /usr/bin/python3 /opt/MoonieXHQ/Agents/Core/tools/infisical_setup.py "
            "run Agents-Core prod --as contabo") in exec_start
    assert "/usr/bin/setpriv --reuid=secretary --regid=secretary --init-groups" in exec_start
    assert "-m tools.join_api --port 8791" in exec_start
    code = [ln for ln in _unit_lines() if not ln.startswith("#")]
    assert "User=root" in code                       # the root leg reads /etc/infisical/*.env, then drops
    assert "NoNewPrivileges=yes" in code             # setpriv only drops privilege: this does not stop it
    # directives that would break the root leg or the dropped leg are not here
    for bad in ("ProtectSystem=full", "ReadOnlyPaths=/etc", "InaccessiblePaths", "CapabilityBoundingSet",
                "User=secretary", "PrivateDevices", "SystemCallFilter", "RestrictAddressFamilies",
                "PrivateNetwork", "ProtectProc", "MemoryDenyWriteExecute"):
        assert not any(ln.startswith(bad) for ln in code), bad


def test_the_unit_has_no_writable_path_because_the_service_writes_nothing():
    code = [ln for ln in _unit_lines() if not ln.startswith("#")]
    assert not any(ln.startswith(("ReadWritePaths=", "StateDirectory=", "RuntimeDirectory=", "LogsDirectory="))
                   for ln in code)
    assert "ReadWritePaths" in UNIT.read_text()      # a comment says why there is none
    # what backs that: the endpoint module opens no file for writing and makes no directory
    src = Path(join_api.__file__).read_text()
    assert not re.search(r"open\([^)]*['\"][wa+]", src) and "write_text" not in src and ".mkdir(" not in src


def test_the_unit_keeps_its_environment_lines_and_stays_ascii():
    env = sorted(ln for ln in _unit_lines() if ln.startswith("Environment="))
    assert env == ["Environment=HOME=/home/secretary", "Environment=JOIN_API_PUBLIC_URL=https://webhook.mooniex.com",
                   "Environment=JOIN_API_TRUST_FORWARDED=1", "Environment=PYTHONUNBUFFERED=1"]
    assert all(b < 128 for b in UNIT.read_bytes())


@not_root
def test_an_unreadable_home_does_not_break_the_one_config_read_the_endpoint_makes(tmp_path, monkeypatch):
    # ProtectHome=yes turns /home/secretary into an empty mode-0000 directory: stat on a file under
    # it fails with EACCES, which Python 3.12 raises from Path.exists(). The accept path reads
    # lib.config.hosts(), which must treat that as "no node.yaml", not crash.
    locked = tmp_path / "locked"
    locked.mkdir()
    monkeypatch.setattr(config, "NODE_CONFIG_PATH", locked / ".config" / "mooniex" / "node.yaml")
    locked.chmod(0)
    try:
        assert isinstance(config.hosts(), dict)
    finally:
        locked.chmod(0o700)


@pytest.mark.skipif(not shutil.which("systemd-analyze"), reason="systemd-analyze is not installed")
def test_systemd_analyze_accepts_the_unit_syntax():
    r = subprocess.run(["systemd-analyze", "verify", str(UNIT)], capture_output=True, text=True, timeout=60)
    bad = [ln for ln in (r.stdout + r.stderr).splitlines()
           if re.search(r"Unknown (key|lvalue|section)|Invalid argument|Failed to parse|Unknown assignment", ln)]
    assert not bad, bad
