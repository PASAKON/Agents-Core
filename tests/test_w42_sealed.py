"""Org Mesh W4.2: lib/sealed.py -- seal a secret to a node's age recipient.

Most tests use a fake `age` executable (a bash script in tmp_path) so the real
subprocess path runs -- stdin in, stdout out, argv recorded -- without needing
age installed. One test does a real age round trip and skips when age is not on
PATH.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w42_sealed.py
"""
from __future__ import annotations

import shutil
import stat
import subprocess

import pytest

from lib import sealed

PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
SECRET = b'{"client_secret":"SECRETVALUE-7f3a9c2e"}'

# bash 3.2 safe. Encrypt mode wraps base64(stdin) in the age armor lines; decrypt
# mode unwraps it. Every argv is appended to LOG, which is how the tests prove the
# plaintext never reached argv.
FAKE_AGE = """#!/bin/bash
printf '%s\\n' "$@" >> '{log}'
mode=enc
for a in "$@"; do [ "$a" = "-d" ] && mode=dec; done
if [ "$mode" = enc ]; then
  echo "-----BEGIN AGE ENCRYPTED FILE-----"; base64; echo "-----END AGE ENCRYPTED FILE-----"
else
  sed '1d;$d' | base64 --decode
fi
"""


def _script(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


@pytest.fixture
def fake_age(tmp_path):
    log = tmp_path / "argv.log"
    return _script(tmp_path, "age", FAKE_AGE.format(log=log)), log


def test_seal_runs_age_with_the_plaintext_on_stdin_never_argv(fake_age):
    age, log = fake_age
    blob = sealed.seal(PUB, SECRET, age_bin=age)
    assert blob.startswith(b"-----BEGIN AGE ENCRYPTED FILE-----")
    argv = log.read_text().split("\n")
    assert argv[:3] == ["-r", PUB, "-a"]
    assert b"SECRETVALUE" not in log.read_bytes()            # not in argv
    assert b"SECRETVALUE" not in blob                        # the fake base64s it, like real age hides it
    assert sealed.open("/id/file", blob, age_bin=age) == SECRET
    assert "-d\n-i\n/id/file" in log.read_text()


def test_open_takes_str_or_bytes(fake_age):
    age, _ = fake_age
    blob = sealed.seal(PUB, b"hello", age_bin=age)
    assert sealed.open("/id", blob.decode("ascii"), age_bin=age) == b"hello"


def test_a_missing_age_fails_closed_with_a_clear_error(tmp_path):
    with pytest.raises(sealed.SealError, match="not installed"):
        sealed.seal(PUB, SECRET, age_bin="no-such-age-binary-w42")
    with pytest.raises(sealed.SealError, match="not an executable"):
        sealed.seal(PUB, SECRET, age_bin=str(tmp_path / "nope" / "age"))


def test_there_is_no_fallback_when_age_is_missing(monkeypatch, tmp_path):
    """An empty PATH and no extra bin dirs: SealError, and nothing that looks like
    ciphertext comes back."""
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(sealed, "_EXTRA_BIN_DIRS", ())
    with pytest.raises(sealed.SealError):
        sealed.seal(PUB, SECRET)


@pytest.mark.parametrize("bad", ["", "age1short", PUB[:-1] + "q", PUB.upper(),
                                 "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIexample", None])
def test_a_bad_recipient_is_refused_before_age_runs(bad):
    def boom(argv, data, timeout):
        raise AssertionError("age must not run for a bad recipient")
    with pytest.raises(sealed.SealError, match="recipient"):
        sealed.seal(bad, SECRET, runner=boom)


@pytest.mark.parametrize("bad", [b"", "text", None])
def test_only_non_empty_bytes_are_sealed(bad):
    with pytest.raises(sealed.SealError, match="non-empty bytes"):
        sealed.seal(PUB, bad, runner=lambda *a: (0, b"", b""))


def test_an_age_failure_raises_and_never_relays_the_plaintext(tmp_path):
    age = _script(tmp_path, "age-fails",
                  "#!/bin/bash\ncat >/dev/null\n"
                  "echo 'boom {\"client_secret\":\"SECRETVALUE-7f3a9c2e\"} leaked' >&2\nexit 3\n")
    with pytest.raises(sealed.SealError) as ei:
        sealed.seal(PUB, SECRET, age_bin=age)
    assert "age exited 3" in str(ei.value)
    assert "SECRETVALUE" not in str(ei.value)


def test_output_that_is_not_an_age_file_is_refused(tmp_path):
    age = _script(tmp_path, "age-plain", "#!/bin/bash\ncat\n")   # echoes the plaintext back
    with pytest.raises(sealed.SealError, match="not an armored age file"):
        sealed.seal(PUB, SECRET, age_bin=age)


def test_open_refuses_input_that_is_not_armored():
    def boom(argv, data, timeout):
        raise AssertionError("age must not run")
    with pytest.raises(sealed.SealError, match="not an armored"):
        sealed.open("/id", b"plain text", runner=boom)


def test_an_injected_runner_replaces_the_binary_and_sees_stdin_only():
    seen = {}

    def runner(argv, data, timeout):
        seen.update(argv=argv, data=data, timeout=timeout)
        return 0, sealed.ARMOR_HEADER + b"\nxx\n", b""

    out = sealed.seal(PUB, SECRET, runner=runner)
    assert out.startswith(sealed.ARMOR_HEADER)
    assert seen["data"] == SECRET and seen["argv"][1:] == ["-r", PUB, "-a"]
    assert SECRET not in " ".join(seen["argv"]).encode()
    assert seen["timeout"] == sealed.TIMEOUT_S


def test_a_timeout_is_a_seal_error(monkeypatch, tmp_path):
    age = _script(tmp_path, "age-slow", "#!/bin/bash\nsleep 5\n")
    monkeypatch.setattr(sealed, "TIMEOUT_S", 1)
    with pytest.raises(sealed.SealError, match="did not finish"):
        sealed.seal(PUB, SECRET, age_bin=age)


@pytest.mark.skipif(not (shutil.which("age") and shutil.which("age-keygen")),
                    reason="age is not on PATH")
def test_real_age_round_trip(tmp_path):
    ident = tmp_path / "id.txt"
    subprocess.run(["age-keygen", "-o", str(ident)], check=True, capture_output=True)
    recipient = next(line.split(": ", 1)[1].strip()
                     for line in ident.read_text().splitlines()
                     if line.startswith("# public key: "))
    blob = sealed.seal(recipient, SECRET)
    assert blob.startswith(b"-----BEGIN AGE ENCRYPTED FILE-----") and SECRET not in blob
    assert sealed.open(str(ident), blob) == SECRET
