"""hq_join's deploy-key check, against real ssh-ed25519 keys (task-7dcc3d45).

2026-10-03, W4.7 join drill run 3: `join` failed with "deploy-pubkey is not an ssh-ed25519 public
key line". The regex ended `{43}`; a real key has 44 characters after the fixed head. Every test
fixture was head + "A" * 43, the same wrong shape, so the check was only ever compared with itself.

So: the keys below were made by `ssh-keygen -q -t ed25519 -N '' -C org-node:node-a` (public halves
pasted, private halves deleted), one test makes a key at run time, and a guard fails the suite if
a test builds a key out of filler again. Doors under test: hq_join.accept, the CLI
`accept --deploy-pubkey`, and the join API's accept route. There is no other validator.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_hq_join_deploy_pubkey.py
"""
from __future__ import annotations

import base64
import http.client
import json
import re
import shutil
import struct
import subprocess
import threading
from pathlib import Path

import pytest

from lib import db
from tools import hq_join, join_api

TESTS_DIR = Path(__file__).resolve().parent

# The example recipient from the age README: a real bech32 checksum.
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"

K1 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPevyJRWgM559TAkS0aqU6fNI/5HXCNkmC5EoKCEpoB6 org-node:node-a"   # has "/"
K2 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ2Yd9JmF0h6Hf7L52H4qZqx93vojzjt14XnLyl0YGBp org-node:node-a"
K3 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG9D06vH3gy5M9FVCiIgDoeYU6vNWImj359y+vMWz3Qh org-node:node-a"   # has "+"
# Real keys of the types a deploy key must not be (ssh-keygen -t ecdsa -b 256 / -t rsa -b 2048).
ECDSA = ("ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBMFUX3XmrV/U3n7B37WwvQOQPSBEHHeWc"
         "K6eDhomOFJcmc9ETiVMfBst2WcDhj4yQ3gMNZmY461lhrD5j9o8j8I= org-node:node-a")
RSA = ("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDH1QcZuZRbgNFMhH6x12rhbB1je29p8Mz+NSFm5qXXrOOsggKdqWcirXjSMgHPaPIbQI6zc/"
       "wlpn7ARGVZ4Tk7qwuT7t+cnUkpe0S2cqghHCtTPqAFUyJQ+l6i+BG5IoB0yqepTSDxFnXetR7k8lxz95QzfhqcmPO7H4LSMxvklpJC/tKtIE3k+"
       "dCYnc5dHelE46iD3IgqNPBbTI912aLqASi2BaSM6I/JRwquAwbLnrNgBXHFRmiUzKbBCh+8UPQjiWMt6yszq7BgFk/sv3ULmF1E5j08fwnxGa9T"
       "60dRKTqn6W8IO7vzk+R/ReXW4lD5L2EWD3vvb3IXbH1M3Knb org-node:node-a")


def _b64(line: str) -> str:
    return line.split()[1]


def _bare(line: str) -> str:
    """`ssh-ed25519 <base64>`: the form hosts.deploy_pubkey keeps."""
    return " ".join(line.split()[:2])


def _k(b64: str, comment: str = "") -> str:
    return "ssh-ed25519 " + b64 + (" " + comment if comment else "")


def _blob(kind: bytes = b"ssh-ed25519", key: bytes = bytes(range(32)), key_len: int | None = None) -> bytes:
    """An ssh wire blob: length-prefixed type, length-prefixed key."""
    return (struct.pack(">I", len(kind)) + kind
            + struct.pack(">I", len(key) if key_len is None else key_len) + key)


def _line(blob: bytes, kind: str = "ssh-ed25519") -> str:
    return kind + " " + base64.b64encode(blob).decode()


B64 = _b64(K1)
HEAD = B64[:24]                     # what every ed25519 key line shares after "ssh-ed25519 "


def _check(line):
    return hq_join._check_deploy_pubkey(line)


def _refused(line) -> None:
    with pytest.raises(hq_join.JoinError) as ei:
        _check(line)
    assert ei.value.code == "bad_arg"


# --------------------------------------------------------------- the check itself

def test_the_pasted_keys_are_what_ssh_keygen_says_they_are(tmp_path):
    """The literals above are the oracle for everything below, so check them against something
    that is not hq_join: they are 68 characters, 51 bytes, and ssh-keygen reads them as ED25519."""
    for key in (K1, K2, K3):
        assert len(_b64(key)) == 68 and len(base64.b64decode(_b64(key), validate=True)) == 51
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not installed")
    f = tmp_path / "pasted.pub"
    f.write_text("\n".join([K1, K2, K3]) + "\n")
    out = subprocess.run(["ssh-keygen", "-l", "-f", str(f)], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0 and out.stdout.count("(ED25519)") == 3, out.stdout + out.stderr


@pytest.mark.parametrize("key", [K1, K2, K3], ids=["slash-in-base64", "plain", "plus-in-base64"])
def test_a_real_key_is_accepted_and_reduced_to_type_and_blob(key):
    assert _check(key) == _bare(key)                          # with a comment: the comment is dropped
    assert _check(_bare(key)) == _bare(key)                   # without one
    assert _check("  " + key + "  \n") == _bare(key)          # surrounding whitespace, as `cat k.pub` leaves it
    assert _check(key + "\r\n") == _bare(key)


def test_none_stays_none():
    assert _check(None) is None


def test_a_well_formed_blob_is_accepted_whatever_its_bytes():
    """The check is the wire format, not a list of known keys or a character count."""
    assert _check(_line(_blob())) == _line(_blob())
    assert _check(_line(_blob(key=b"\xff" * 32))) == _line(_blob(key=b"\xff" * 32))


def test_a_comment_of_one_to_eighty_printable_characters_is_accepted():
    for comment in ("x", "root@node-a", "has some spaces in it", "z" * 80, "~!@#$%^&*()"):
        assert _check(_k(B64, comment)) == _k(B64)


BAD = {
    # the length of the base64 text
    "the old fixture shape: head + 43 filler": _k(HEAD + "A" * 43),
    "right length, wrong length field: head + 44 filler": _k(HEAD + "A" * 44),
    "head + 45 filler": _k(HEAD + "A" * 45),
    "a real key and four more characters": _k(B64 + "AAAA"),
    "a real key, last character cut": _k(B64[:-1]),
    "a real key, last four characters cut": _k(B64[:-4]),
    "ssh-ed25519 and nothing after": "ssh-ed25519",
    "ssh-ed25519 and a space": "ssh-ed25519 ",
    # padding and the base64 alphabet
    "= padding after a real key": _k(B64 + "="),
    "= in place of the last character": _k(B64[:-1] + "="),
    "== in place of the last two": _k(B64[:-2] + "=="),
    "url-safe -": _k(B64[:30] + "-" + B64[31:]),
    "url-safe _": _k(B64[:30] + "_" + B64[31:]),
    "a character outside base64": _k(B64[:30] + "*" + B64[31:]),
    "a non-ASCII character in the base64": _k(B64[:30] + "é" + B64[31:]),
    "a space inside the base64": _k(B64[:30] + " " + B64[31:]),
    # a blob that is the right size but not an ed25519 key
    "blob names another type (ssh-ed25518)": _line(_blob(kind=b"ssh-ed25518")),
    "blob key of 31 bytes": _line(_blob(key=bytes(range(31)))),
    "blob key of 33 bytes": _line(_blob(key=bytes(range(33)))),
    "blob length field says 31, 32 bytes follow": _line(_blob(key_len=31)),
    "blob with three bytes after the key": _line(_blob() + b"\x00\x00\x00"),
    "an rsa blob under the ssh-ed25519 label": "ssh-ed25519 " + _b64(RSA),
    # other key types, as ssh-keygen makes them
    "an ecdsa key": ECDSA,
    "an rsa key": RSA,
    "an sk-ssh-ed25519 key": _line(_blob(kind=b"sk-ssh-ed25519@openssh.com", key=bytes(range(32)) + b"\x00\x00\x00\x04ssh:"),
                                   kind="sk-ssh-ed25519@openssh.com") + " org-node:node-a",
    "an ed25519 certificate type": "ssh-ed25519-cert-v01@openssh.com " + B64,
    "the type in capitals": K1.replace("ssh-ed25519", "SSH-ED25519"),
    # more than one key, or something in front of it
    'an options prefix: from=""': 'from="10.0.0.1" ' + K1,
    "an options prefix: command=": 'command="true",no-pty ' + K1,
    "an options prefix: restrict": "restrict " + K1,
    "two keys on one line": K1 + " " + K2,
    "two keys on two lines": K1 + "\n" + K2,
    "a second line": _bare(K1) + "\nsecond",
    "text before the key": "key: " + K1,
    # control characters
    "a newline inside the base64": _k(B64[:34] + "\n" + B64[34:]),
    "a carriage return in the comment": _bare(K1) + " a\rb",
    "a NUL after the key": _bare(K1) + "\x00",
    "a NUL before the key": "\x00" + _bare(K1),
    "a NUL in the comment": _bare(K1) + " a\x00b",
    "a tab for the separator": _bare(K1).replace(" ", "\t", 1),
    "a tab before the comment": _bare(K1) + "\tcomment",
    "a tab in the comment": _bare(K1) + " a\tb",
    "a control character in the comment": _bare(K1) + " bad\x01comment",
    "DEL in the comment": _bare(K1) + " bad\x7fcomment",
    "a non-ASCII comment": _bare(K1) + " โหนด",
    "a comment over 80 characters": _k(B64, "z" * 81),
    # not a key line at all
    "an empty string": "",
    "only whitespace": "   \n",
    "an age recipient": PUB,
}


@pytest.mark.parametrize("line", list(BAD.values()), ids=list(BAD))
def test_a_line_that_is_not_one_real_ed25519_key_is_refused(line):
    _refused(line)


@pytest.mark.parametrize("value", [123, b"ssh-ed25519 " + B64.encode(), [K1], {"k": K1}, True],
                         ids=["int", "bytes", "list", "dict", "bool"])
def test_a_value_that_is_not_a_string_is_refused(value):
    _refused(value)


def test_the_error_names_the_shape_and_never_echoes_the_input():
    with pytest.raises(hq_join.JoinError) as ei:
        _check(_k(B64, "SECRET-COMMENT") + "\x00")
    assert "ssh-ed25519" in ei.value.message and "SECRET-COMMENT" not in ei.value.message


# ------------------------------------------- the doors production uses: accept, CLI, join API

DOORS = ("accept", "cli", "api")


@pytest.fixture
def hub(monkeypatch, tmp_path):
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", "ORG_DB_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()


@pytest.fixture
def server(hub):
    srv = join_api.make_server(0)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    thread.join(timeout=5)


def _post_accept(srv, body: dict) -> tuple[int, dict]:
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    try:
        conn.request("POST", join_api.PREFIX + "accept", json.dumps(body).encode(),
                     {"Content-Type": "application/json"})
        r = conn.getresponse()
        return r.status, json.loads(r.read())
    finally:
        conn.close()


def _join_via(door: str, srv, key, host: str = "node-a"):
    """mint a token and take `key` through one door. Returns (joined, token)."""
    token = hq_join.mint(host)["token"]
    if door == "accept":
        try:
            hq_join.accept(token, host, "linux", "/opt/MoonieXHQ", PUB, deploy_pubkey=key)
        except hq_join.JoinError as exc:
            assert exc.code == "bad_arg"
            return False, token
        return True, token
    if door == "cli":
        rc = hq_join.main(["accept", "--host", host, "--os", "linux", "--hq-root", "/opt/MoonieXHQ",
                           "--pubkey", PUB, "--token", token, "--deploy-pubkey", key])
        assert rc in (0, 2)
        return rc == 0, token
    status, body = _post_accept(srv, {"token": token, "host": host, "os": "linux",
                                      "hq_root": "/opt/MoonieXHQ", "pubkey": PUB, "deploy_pubkey": key})
    assert status in (200, 400), (status, body)
    if status == 400:
        assert body["error"] == "bad_arg"
    return status == 200, token


@pytest.mark.parametrize("door", DOORS)
@pytest.mark.parametrize("key", [K1, K2, K3], ids=["slash-in-base64", "plain", "plus-in-base64"])
def test_a_real_key_joins_through_every_door_and_the_comment_is_not_stored(door, key, server):
    joined, _ = _join_via(door, server, key)
    assert joined
    assert db.get_host("node-a")["deploy_pubkey"] == _bare(key)


_DOOR_REFUSALS = ["the old fixture shape: head + 43 filler", "right length, wrong length field: head + 44 filler",
                  "= padding after a real key", "url-safe _", "an ecdsa key", "an rsa key",
                  "an sk-ssh-ed25519 key", 'an options prefix: from=""', "two keys on one line",
                  "a second line", "a NUL after the key", "a tab for the separator",
                  "a comment over 80 characters", "an empty string"]


@pytest.mark.parametrize("door", DOORS)
@pytest.mark.parametrize("name", _DOOR_REFUSALS)
def test_a_bad_key_is_refused_by_every_door_before_the_token_is_spent(door, name, server):
    joined, token = _join_via(door, server, BAD[name])
    assert not joined
    assert db.get_host("node-a") is None
    hq_join.accept(token, "node-a", "linux", "/opt/MoonieXHQ", PUB)       # the token is still good
    assert db.get_host("node-a")["deploy_pubkey"] is None


@pytest.mark.parametrize("value", [123, ["x"], True], ids=["int", "list", "bool"])
def test_the_api_refuses_a_deploy_key_that_is_not_a_string(value, server):
    token = hq_join.mint("node-a")["token"]
    status, body = _post_accept(server, {"token": token, "host": "node-a", "os": "linux",
                                         "hq_root": "/opt/MoonieXHQ", "pubkey": PUB, "deploy_pubkey": value})
    assert status == 400 and body["error"] == "bad_arg"
    assert db.get_host("node-a") is None


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen not installed")
@pytest.mark.parametrize("door", DOORS)
def test_a_key_ssh_keygen_makes_now_joins_through_the_door(door, tmp_path, server):
    """No literal, no fixture: whatever ssh-keygen on this machine makes today. The same command
    join.sh runs (`ssh-keygen -q -t ed25519 -N '' -C org-node:<host> -f <path>`), in tmp_path."""
    for n in range(3):
        host = f"node-{n}"
        path = tmp_path / f"k{n}"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"org-node:{host}", "-f", str(path)],
                       check=True, capture_output=True, timeout=30)
        line = path.with_name(path.name + ".pub").read_text()
        path.unlink()                                                    # the private half goes at once
        assert line.endswith("\n") and len(_b64(line)) == 68
        joined, _ = _join_via(door, server, line, host=host)
        assert joined, line
        assert db.get_host(host)["deploy_pubkey"] == _bare(line)


# ------------------------------------------------------------ the guard against a circular fixture

_FILLER = r"""(?:["'][A-Za-z0-9+/]["']\s*\*\s*\d+|\d+\s*\*\s*["'][A-Za-z0-9+/]["'])"""
_FILLER_KEY = re.compile(r"ssh-ed25519 [A-Za-z0-9+/]*(?:[\"']\s*\+\s*|\{\s*)" + _FILLER)
_HEAD_ONLY = re.compile(r"AAAAC3NzaC1lZDI1NTE5AAAA[\"']")        # the shared head, closed: something is appended


def _circular_key_lines(text: str) -> list[str]:
    """Lines that build an ssh-ed25519 key from the fixed head plus one repeated character, the
    shape that hid the {43} bug. `"ssh-ed25519 short"` and `"hqj_" + "A" * 43` are not keys."""
    return [ln.strip() for ln in text.splitlines() if _FILLER_KEY.search(ln) or _HEAD_ONLY.search(ln)]


def test_the_guard_sees_the_shapes_it_is_there_for():
    head = "ssh-ed25519 " + HEAD
    for line in (f'DEPLOY = "{head}" + "B" * 43',
                 f'DEPLOY = "{head}" + 43 * "A" + " org-node:node-a"',
                 'DEPLOY = f"' + head + "{'A' * 43}\"",
                 f'PREFIX = "{head}"'):
        assert _circular_key_lines(line), line
    for line in (f'DEPLOY = "{K1}"', 'bad = "ssh-ed25519 short"', 'TOKEN = "hqj_" + "A" * 43',
                 'json.dumps(["ssh-ed25519 short", "ssh-dss AAAAB3NzaC1kc3MAAACB" + "A" * 30])'):
        assert not _circular_key_lines(line), line


def test_no_test_builds_an_ed25519_key_from_filler():
    found = {}
    for path in sorted(TESTS_DIR.glob("**/*.py")):
        if path.resolve() == Path(__file__).resolve():
            continue                                        # this file holds the shapes above as samples
        hits = _circular_key_lines(path.read_text(encoding="utf-8", errors="replace"))
        if hits:
            found[path.name] = hits
    assert not found, ("a fixture built as head + filler is only ever compared with the check that "
                       "shares its shape; paste a key ssh-keygen made: " + json.dumps(found, indent=1))
