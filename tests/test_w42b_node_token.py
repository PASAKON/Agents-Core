"""Org Mesh W4.2b: tools/node_token.py -- the node-side client of the token service.

`node_token.py run -- <cmd>` asks the hub for the Claude token, opens the sealed answer with the
node's own age identity, and starts <cmd> with the value in its environment. CEO ruling 2026-10-03,
R3: the token is never written to a file on the node. This file pins that and the way it fails:

  * end to end against the real service on loopback, sealed with the real `age` binary
  * no file is created, nothing is printed, the value is not in argv or in this process's environment
  * every failure is a status plus the hub's short code or the exception class, never a body
  * the program is standard library only and imports nothing from this repo (join.sh starts it as
    `python3 -I`, and a root process must not import files a user can write)

SQLite only: the hub side has its own Postgres tests (test_w42b_node_token_api.py).

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w42b_node_token.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import threading
import types
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from lib import db
from tools import hq_join, node_token

from test_w42b_node_token_api import Api, NAME, TOKEN, _keygen, _row, needs_age

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "node_token.py"
CIPHER = "-----BEGIN AGE ENCRYPTED FILE-----\nc3ludGhldGlj\n-----END AGE ENCRYPTED FILE-----\n"
URL = "http://100.64.0.1:8792/v1/token"
_REAL_FIND_AGE = node_token.find_age


class _Shim:
    """A stand-in for a stdlib module inside node_token only: the named attributes are replaced and
    everything else falls through to the real module, so a test never patches `os` for everyone."""

    def __init__(self, real, **over):
        self._real = real
        self.__dict__.update(over)

    def __getattr__(self, name):
        return getattr(self._real, name)


@pytest.fixture(autouse=True)
def hub(monkeypatch, tmp_path):
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", "ORG_DB_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "hub" / "tasks.db")
    (tmp_path / "hub").mkdir()
    db.init()
    monkeypatch.setattr(node_token, "time", types.SimpleNamespace(sleep=lambda s: None))   # the retry wait


@pytest.fixture
def fake_age(monkeypatch):
    """For the tests that hand open_token a runner: it must not need an `age` on this machine."""
    monkeypatch.setattr(node_token, "find_age", lambda: "/fake/bin/age")


def _node(tmp_path: Path, url: str, identity: Path | None, host: str = "node-a") -> Path:
    """A node.yaml in its own directory, the way join.sh writes one (flat key: value lines)."""
    conf = tmp_path / "conf"
    conf.mkdir(exist_ok=True)
    lines = [f"host: {host}", f"token_url: {url}"]
    if identity is not None:
        lines.append(f"age_identity: {identity}")
    path = conf / "node.yaml"
    path.write_text("\n".join(lines) + "\n")
    return path


def _files(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


class Launch:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, env):
        self.calls.append((list(argv), dict(env)))
        return 0


# ---------------------------------------------------------------- node.yaml

def test_node_yaml_is_read_as_flat_lines_with_quotes_cut(tmp_path):
    p = tmp_path / "node.yaml"
    p.write_text("# a comment\nhost: node-a\ntoken_url: 'http://100.64.0.1:8792/v1/token'\n"
                 'age_identity: "/root/.config/mooniex/age-identity.txt"\n  indented: 1\n')
    assert node_token.read_node_yaml(p) == {
        "host": "node-a", "token_url": "http://100.64.0.1:8792/v1/token",
        "age_identity": "/root/.config/mooniex/age-identity.txt"}


def test_a_missing_node_yaml_says_this_machine_has_not_joined(tmp_path):
    with pytest.raises(node_token.TokenError) as ei:
        node_token.settings(tmp_path / "nope.yaml")
    assert ei.value.code == 2 and "has not joined" in str(ei.value)


@pytest.mark.parametrize("host", ["", "Node-A", "a", "node_a", "-node", "node-", "x" * 40])
def test_a_bad_host_in_node_yaml_is_exit_2(tmp_path, host):
    path = _node(tmp_path, URL, None, host=host)
    with pytest.raises(node_token.TokenError) as ei:
        node_token.settings(path)
    assert ei.value.code == 2 and "'host'" in str(ei.value)


def test_a_node_that_joined_before_the_hub_served_the_token_is_told_to_join_again(tmp_path):
    path = tmp_path / "node.yaml"
    path.write_text("host: node-a\n")
    with pytest.raises(node_token.TokenError) as ei:
        node_token.settings(path)
    assert ei.value.code == 2 and "token_url" in str(ei.value) and "join.sh" in str(ei.value)


@pytest.mark.parametrize("url", ["ftp://100.64.0.1/v1/token", "file:///etc/passwd", "100.64.0.1/v1/token",
                                 "http://100.64.0.1:8792/v1/token?x=1", "http://a b/v1/token",
                                 "http://100.64.0.1:8792/v1/token#frag", "javascript:alert(1)", "http://"])
def test_a_token_url_that_is_not_a_plain_http_url_is_refused(tmp_path, url):
    with pytest.raises(node_token.TokenError) as ei:
        node_token.settings(_node(tmp_path, url, None))
    assert ei.value.code == 2 and "token_url" in str(ei.value)


def test_the_identity_defaults_to_the_file_join_sh_writes(tmp_path):
    _, _, identity = node_token.settings(_node(tmp_path, URL, None))
    assert identity == node_token.AGE_IDENTITY_DEFAULT
    assert str(identity).endswith(".config/mooniex/age-identity.txt")


# ---------------------------------------------------------------- the fetch, with a fake opener

class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class Opener:
    """open() answers each item in turn: bytes = a 200 body, an Exception is raised, (code, body) = an HTTP error."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append((request.full_url, request.get_method(), timeout))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        if isinstance(a, tuple):
            code, body = a
            raise urllib.error.HTTPError(request.full_url, code, "x", {}, io.BytesIO(body))
        return _Resp(a)


def _ok(cipher=CIPHER):
    return json.dumps({"ciphertext": cipher}).encode()


def test_the_request_is_a_get_with_the_host_and_no_secret_in_it():
    op = Opener(_ok())
    assert node_token.fetch_ciphertext(URL, "node-a", NAME, opener=op) == CIPHER
    assert op.requests == [(URL + "?host=node-a", "GET", node_token.HTTP_TIMEOUT_S)]


def test_a_non_default_name_goes_in_the_query():
    op = Opener(_ok())
    node_token.fetch_ciphertext(URL, "node-a", "OTHER_SECRET", opener=op)
    assert op.requests[0][0] == URL + "?host=node-a&name=OTHER_SECRET"


@pytest.mark.parametrize("code", ["left", "not_approved", "not_issuing", "unknown_host"])
def test_a_403_is_exit_3_with_the_hubs_short_code(code):
    op = Opener((403, json.dumps({"error": code}).encode()))
    with pytest.raises(node_token.TokenError) as ei:
        node_token.fetch_ciphertext(URL, "node-a", NAME, opener=op)
    assert ei.value.code == 3 and str(ei.value) == f"hub answered HTTP 403 ({code})"
    assert len(op.requests) == 1                                       # a refusal is not retried


def test_a_403_whose_body_is_not_a_short_code_says_only_the_status():
    for body in (b"<html>nope</html>", json.dumps({"error": "Sy nth: " + TOKEN}).encode(), b"", b"\xff\xfe"):
        with pytest.raises(node_token.TokenError) as ei:
            node_token.fetch_ciphertext(URL, "node-a", NAME, opener=Opener((403, body)))
        assert str(ei.value) == "hub answered HTTP 403" and TOKEN not in str(ei.value)


@pytest.mark.parametrize("code", [400, 404, 302])
def test_a_client_error_is_exit_4_and_not_retried(code):
    op = Opener((code, b'{"error":"bad_name"}'))
    with pytest.raises(node_token.TokenError) as ei:
        node_token.fetch_ciphertext(URL, "node-a", NAME, opener=op)
    assert ei.value.code == 4 and f"HTTP {code}" in str(ei.value) and len(op.requests) == 1


@pytest.mark.parametrize("code", [429, 500, 503])
def test_a_busy_or_failing_hub_is_retried_three_times_then_exit_4(code):
    op = Opener(*[(code, b'{"error":"busy"}')] * 3)
    with pytest.raises(node_token.TokenError) as ei:
        node_token.fetch_ciphertext(URL, "node-a", NAME, opener=op)
    assert ei.value.code == 4 and len(op.requests) == node_token.ATTEMPTS == 3
    assert f"HTTP {code}" in str(ei.value)


def test_the_tailnet_getting_up_late_is_waited_for():
    op = Opener(urllib.error.URLError("connection refused"), TimeoutError(), _ok())
    assert node_token.fetch_ciphertext(URL, "node-a", NAME, opener=op) == CIPHER
    assert len(op.requests) == 3


def test_a_hub_that_never_answers_is_exit_4_naming_the_exception_class_only():
    op = Opener(*[urllib.error.URLError("Sy-nth password=" + TOKEN)] * 3)
    with pytest.raises(node_token.TokenError) as ei:
        node_token.fetch_ciphertext(URL, "node-a", NAME, opener=op)
    assert ei.value.code == 4 and str(ei.value) == "hub not reachable (URLError)"


@pytest.mark.parametrize("body", [b"not json", b"[]", b"{}", json.dumps({"ciphertext": 5}).encode(),
                                  json.dumps({"ciphertext": "plain text"}).encode(), b"\xff\xfe\xfd"])
def test_an_answer_that_is_not_a_ciphertext_is_exit_4(body):
    with pytest.raises(node_token.TokenError) as ei:
        node_token.fetch_ciphertext(URL, "node-a", NAME, opener=Opener(body))
    assert ei.value.code == 4


def test_an_answer_that_is_too_long_is_exit_4():
    big = json.dumps({"ciphertext": CIPHER + "x" * node_token.MAX_ANSWER}).encode()
    with pytest.raises(node_token.TokenError) as ei:
        node_token.fetch_ciphertext(URL, "node-a", NAME, opener=Opener(big))
    assert ei.value.code == 4 and "too long" in str(ei.value)


# ---------------------------------------------------------------- opening the answer

def _opened(host="node-a", name=NAME, value=TOKEN, v=1):
    return json.dumps({"v": v, "host": host, "name": name, "value": value, "issued_at": "t"}).encode()


def _ident(tmp_path: Path) -> Path:
    ident = tmp_path / "id.txt"
    ident.write_text("AGE-SECRET-KEY-1SYNTHETIC\n")
    return ident


def _open(ident, out=b"", rc=0):
    seen = []

    def runner(argv, data):
        seen.append((argv, data))
        return rc, out
    return node_token.open_token(CIPHER, ident, "node-a", NAME, runner=runner), seen


def test_the_value_comes_back_and_age_sees_the_identity_path_only(tmp_path, fake_age):
    ident = _ident(tmp_path)
    value, seen = _open(ident, _opened())
    assert value == TOKEN
    argv, data = seen[0]
    assert argv == ["/fake/bin/age", "-d", "-i", str(ident)] and data == CIPHER.encode()
    assert TOKEN not in " ".join(argv) and "AGE-SECRET-KEY" not in " ".join(argv)


@pytest.mark.parametrize("out,rc,message", [
    (_opened(), 1, "could not open the answer"),                          # sealed to another key
    (b"not json", 0, "not the expected JSON"),
    (b"[1]", 0, "not the expected JSON"),
    (_opened(host="node-b"), 0, "another host or secret"),                # an answer meant for another node
    (_opened(name="OTHER_SECRET"), 0, "another host or secret"),
    (_opened(v=2), 0, "another host or secret"),
    (_opened(value=""), 0, "holds no value"),
    (json.dumps({"v": 1, "host": "node-a", "name": NAME, "value": 7}).encode(), 0, "holds no value"),
])
def test_an_answer_that_cannot_be_used_is_exit_5_and_never_echoed(tmp_path, fake_age, out, rc, message):
    with pytest.raises(node_token.TokenError) as ei:
        _open(_ident(tmp_path), out, rc)
    assert ei.value.code == 5 and message in str(ei.value) and TOKEN not in str(ei.value)


def test_a_missing_identity_file_is_exit_5_before_age_runs(tmp_path):
    ran = []
    with pytest.raises(node_token.TokenError) as ei:
        node_token.open_token(CIPHER, tmp_path / "none.txt", "node-a", NAME, runner=lambda a, d: ran.append(1))
    assert ei.value.code == 5 and "does not exist" in str(ei.value) and not ran


def test_age_missing_is_exit_5_and_says_join_installs_it(tmp_path, monkeypatch):
    monkeypatch.setattr(node_token, "find_age", _REAL_FIND_AGE)
    monkeypatch.setattr(node_token, "shutil", _Shim(node_token.shutil, which=lambda name: None))
    monkeypatch.setattr(node_token, "os", _Shim(os, access=lambda *a: False))
    with pytest.raises(node_token.TokenError) as ei:
        node_token.open_token(CIPHER, _ident(tmp_path), "node-a", NAME)
    assert ei.value.code == 5 and "age is not installed" in str(ei.value)


def test_age_that_hangs_or_cannot_start_is_exit_5_with_the_class_only(tmp_path, fake_age):
    def boom(argv, data):
        raise subprocess.TimeoutExpired(argv, 30, output=TOKEN.encode())
    with pytest.raises(node_token.TokenError) as ei:
        node_token.open_token(CIPHER, _ident(tmp_path), "node-a", NAME, runner=boom)
    assert ei.value.code == 5 and str(ei.value) == "age failed (TimeoutExpired)"


# ---------------------------------------------------------------- run(): fetch, open, hand over

def _run_fake(cfg, argv, **kw):
    return node_token.run(argv, config=cfg, opener=Opener(_ok()), runner=lambda a, d: (0, _opened()), **kw)


def test_run_hands_the_value_to_the_command_environment_and_to_nothing_else(tmp_path, monkeypatch, capsys, fake_age):
    cfg = _node(tmp_path, URL, _ident(tmp_path))
    before = _files(cfg.parent)
    launch = Launch()
    monkeypatch.delenv(NAME, raising=False)
    assert _run_fake(cfg, ["/bin/echo", "hello"], launch=launch) == 0
    argv, env = launch.calls[0]
    assert argv == ["/bin/echo", "hello"] and env[NAME] == TOKEN
    assert NAME not in os.environ                                       # this process is not changed
    assert _files(cfg.parent) == before                                 # no file written next to node.yaml
    assert capsys.readouterr() == ("", "")


def test_the_command_may_not_be_empty_and_the_name_must_look_like_a_secret_name(tmp_path):
    cfg = _node(tmp_path, URL, None)
    for argv, name in (([], NAME), (["x"], "lower"), (["x"], "A"), (["x"], "BAD NAME"), (["x"], "A;B")):
        with pytest.raises(node_token.TokenError) as ei:
            node_token.run(argv, config=cfg, name=name, opener=Opener(), launch=Launch())
        assert ei.value.code == 2


def test_a_command_that_cannot_start_is_exit_127_with_the_class_only(tmp_path, monkeypatch, fake_age):
    def no_exec(*a):
        raise FileNotFoundError("/no/such/cmd " + TOKEN)
    monkeypatch.setattr(node_token, "os", _Shim(os, name="posix", execvpe=no_exec))
    with pytest.raises(node_token.TokenError) as ei:
        _run_fake(_node(tmp_path, URL, _ident(tmp_path)), ["/no/such/cmd"])
    assert ei.value.code == 127 and TOKEN not in str(ei.value) and "FileNotFoundError" in str(ei.value)


def test_the_command_replaces_this_process_on_posix_and_is_waited_for_on_windows(tmp_path, monkeypatch, fake_age):
    cfg = _node(tmp_path, URL, _ident(tmp_path))
    seen = {}
    monkeypatch.setattr(node_token, "os", _Shim(os, name="posix",
                        execvpe=lambda f, a, e: seen.setdefault("exec", (f, a, e[NAME]))))
    _run_fake(cfg, ["tool", "x"])
    assert seen["exec"] == ("tool", ["tool", "x"], TOKEN)

    def call(argv, env):
        seen["call"] = (argv, env[NAME])
        return 7
    monkeypatch.setattr(node_token, "os", _Shim(os, name="nt"))
    monkeypatch.setattr(node_token, "subprocess", _Shim(subprocess, call=call))
    assert _run_fake(cfg, ["tool.exe"]) == 7
    assert seen["call"] == (["tool.exe"], TOKEN)


# ---------------------------------------------------------------- main(): usage and messages

@pytest.mark.parametrize("args", [
    [], ["run"], ["run", "x"], ["get", "--", "x"], ["--", "x"], ["run", "--bogus", "--", "x"],
    ["run", "--name", "--", "x"], ["run", "--config", "--", "x"], ["run", "--name", "lower", "--", "x"],
    ["run", "--"]])
def test_main_usage_errors_are_exit_2_and_say_so(args, capsys):
    assert node_token.main(args) == 2
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("node_token: ")


def test_main_with_a_node_that_never_joined_is_exit_2(tmp_path, capsys):
    assert node_token.main(["run", "--config", str(tmp_path / "none.yaml"), "--", "/bin/true"]) == 2
    assert "has not joined" in capsys.readouterr().err


# ---------------------------------------------------------------- end to end: the real service, the real age

@pytest.fixture
def served():
    made = []

    def _serve():
        a = Api(tokens={NAME: TOKEN})                                  # the real lib.sealed.seal
        made.append(a)
        return a
    yield _serve
    for a in made:
        a.close()


@needs_age
def test_end_to_end_the_node_gets_the_token_and_writes_nothing(served, tmp_path, monkeypatch, capsys):
    ident, pub = _keygen(tmp_path, "node")
    api = served()
    _row("node-a", pubkey=pub)
    cfg = _node(tmp_path, f"http://127.0.0.1:{api.port}/v1/token", ident)
    before = _files(cfg.parent)
    launch = Launch()
    monkeypatch.delenv(NAME, raising=False)
    assert node_token.run(["claude", "-p", "hi"], config=cfg, launch=launch) == 0
    argv, env = launch.calls[0]
    assert env[NAME] == TOKEN and argv == ["claude", "-p", "hi"] and TOKEN not in " ".join(argv)
    assert _files(cfg.parent) == before and NAME not in os.environ
    assert capsys.readouterr() == ("", "")


@needs_age
def test_end_to_end_through_the_real_exec_the_child_gets_the_value_and_stdout_does_not(served, tmp_path):
    """`python3 -I tools/node_token.py run -- sh -c ...`, as join.sh and the drill start it."""
    ident, pub = _keygen(tmp_path, "node")
    api = served()
    _row("node-a", pubkey=pub)
    cfg = _node(tmp_path, f"http://127.0.0.1:{api.port}/v1/token", ident)
    home, work, scratch = (tmp_path / n for n in ("home", "work", "scratch"))
    for d in (home, work, scratch):
        d.mkdir()
    env = {k: v for k, v in os.environ.items() if k != NAME}
    env.update(HOME=str(home), TMPDIR=str(scratch))
    before = _files(cfg.parent)
    done = subprocess.run(
        [sys.executable, "-I", str(SOURCE), "run", "--config", str(cfg), "--", "/bin/sh", "-c",
         'printf "%s" "${CLAUDE_CODE_OAUTH_TOKEN:+set}"; printf " %s" "${#CLAUDE_CODE_OAUTH_TOKEN}"'],
        env=env, capture_output=True, text=True, timeout=60, cwd=work)
    assert done.returncode == 0, done.stderr
    assert done.stdout == f"set {len(TOKEN)}"                          # the child had it; we never printed it
    assert TOKEN not in done.stdout + done.stderr and done.stderr == ""
    assert _files(cfg.parent) == before
    assert [_files(d) for d in (home, work, scratch)] == [[], [], []]   # nothing written anywhere it could


@needs_age
def test_end_to_end_a_host_that_left_gets_exit_3_and_the_command_never_starts(served, tmp_path):
    ident, pub = _keygen(tmp_path, "node")
    api = served()
    _row("node-a", status=hq_join.STATUS_LEFT, pubkey=pub)
    cfg = _node(tmp_path, f"http://127.0.0.1:{api.port}/v1/token", ident)
    marker = tmp_path / "ran"
    done = subprocess.run(
        [sys.executable, "-I", str(SOURCE), "run", "--config", str(cfg), "--", "/usr/bin/touch", str(marker)],
        capture_output=True, text=True, timeout=60)
    assert done.returncode == 3 and not marker.exists()
    assert done.stderr == "node_token: hub answered HTTP 403 (left)\n" and done.stdout == ""


@needs_age
@pytest.mark.parametrize("status,approved,code", [
    (hq_join.STATUS_PENDING, False, "not_approved"), (hq_join.STATUS_PENDING, True, "not_issuing")])
def test_end_to_end_a_node_the_ceo_has_not_approved_gets_exit_3(served, tmp_path, status, approved, code):
    ident, pub = _keygen(tmp_path, "node")
    api = served()
    _row("node-a", status=status, approved=approved, pubkey=pub)
    cfg = _node(tmp_path, f"http://127.0.0.1:{api.port}/v1/token", ident)
    with pytest.raises(node_token.TokenError) as ei:
        node_token.run(["x"], config=cfg, launch=Launch())
    assert ei.value.code == 3 and str(ei.value) == f"hub answered HTTP 403 ({code})"


@needs_age
def test_end_to_end_an_answer_sealed_to_another_key_is_exit_5(served, tmp_path):
    ident, _ = _keygen(tmp_path, "node")
    _, other_pub = _keygen(tmp_path, "someone-else")
    api = served()
    _row("node-a", pubkey=other_pub)                                    # the hub holds another key for this host
    cfg = _node(tmp_path, f"http://127.0.0.1:{api.port}/v1/token", ident)
    with pytest.raises(node_token.TokenError) as ei:
        node_token.run(["x"], config=cfg, launch=Launch())
    assert ei.value.code == 5 and TOKEN not in str(ei.value)


@needs_age
def test_the_environment_cannot_route_the_request_through_a_proxy(served, tmp_path, monkeypatch):
    ident, pub = _keygen(tmp_path, "node")
    api = served()
    _row("node-a", pubkey=pub)
    cfg = _node(tmp_path, f"http://127.0.0.1:{api.port}/v1/token", ident)
    for var in ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.setenv(var, "http://127.0.0.1:9")                   # nothing listens there
    for var in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(var, raising=False)
    launch = Launch()
    assert node_token.run(["x"], config=cfg, launch=launch) == 0
    assert launch.calls[0][1][NAME] == TOKEN


def test_a_redirect_is_not_followed():
    hits = []

    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:9/steal")
            self.end_headers()

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), Redirect)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        with pytest.raises(node_token.TokenError) as ei:
            node_token.fetch_ciphertext(f"http://127.0.0.1:{srv.server_address[1]}/v1/token", "node-a", NAME)
    finally:
        srv.shutdown()
        srv.server_close()
    assert ei.value.code == 4 and "HTTP 302" in str(ei.value) and hits == ["/v1/token?host=node-a"]


# ---------------------------------------------------------------- what the source may do

def _tree() -> ast.Module:
    return ast.parse(SOURCE.read_text(encoding="utf-8"))


def test_the_program_is_standard_library_only_and_imports_nothing_from_the_repo():
    imported = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported.add((node.module or "").split(".")[0])
    assert imported <= set(sys.stdlib_module_names), imported - set(sys.stdlib_module_names)
    assert not imported & {"lib", "tools", "runners", "yaml", "requests"}


def test_the_program_runs_on_the_python_a_node_has_by_default():
    ast.parse(SOURCE.read_text(encoding="utf-8"), feature_version=(3, 8))


def test_the_program_has_no_way_to_write_a_file_log_or_print_the_value():
    names, attrs, opens = set(), set(), []
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                attrs.add(f.attr)
                if f.attr == "open":
                    opens.append(getattr(f.value, "id", ""))
    assert "open" not in names, "the builtin open() would write or read a file"
    assert opens == ["opener"]                                               # the only .open(): the HTTP opener's
    assert not attrs & {"write", "write_text", "write_bytes", "mkstemp", "NamedTemporaryFile", "copy",
                        "copyfile", "putenv", "system", "popen"}, attrs
    prints = [n for n in ast.walk(_tree()) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"]
    assert len(prints) == 1                                                  # main()'s one error line
    imported = {a.name for n in ast.walk(_tree()) if isinstance(n, ast.Import) for a in n.names}
    assert not imported & {"logging", "tempfile", "pickle", "shelve", "sqlite3"}


def test_the_value_is_only_ever_put_in_the_child_environment():
    src = SOURCE.read_text(encoding="utf-8")
    assert "env[name] = value" in src and "os.environ[" not in src and "shell=True" not in src
    assert "execvpe" in src
