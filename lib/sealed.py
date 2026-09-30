"""Seal a secret to a node's age recipient, and open it on the node (Org Mesh W4.2).

    blob = seal("age1...", b"plaintext")      # ASCII-armored age, safe to store in the hub
    text = open("/path/to/age-identity", blob)  # on the node that holds the identity

Both run the `age` binary. The plaintext goes to it on STDIN and the result comes
back on stdout: never argv (visible in `ps`), never a temp file. There is no
fallback: if `age` is missing or fails, SealError is raised and nothing is
"sealed" some weaker way. age is not implemented here.

`open` shadows the builtin inside this module on purpose (the W4.2 brief names
it); this file never needs the builtin.

The runner is injectable so tests never need a real age: `runner(argv, data,
timeout)` returns `(returncode, stdout_bytes, stderr_bytes)`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable

AGE_BIN = "age"
TIMEOUT_S = 30
ARMOR_HEADER = b"-----BEGIN AGE ENCRYPTED FILE-----"
# launchd / systemd units often run with a short PATH that lacks Homebrew.
_EXTRA_BIN_DIRS = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin")

Runner = Callable[[list, bytes, int], tuple]


class SealError(RuntimeError):
    """age is missing, refused, or returned something that is not age output.
    The message never contains the plaintext."""


def _subprocess_runner(argv: list, data: bytes, timeout: int) -> tuple:
    try:
        p = subprocess.run(argv, input=data, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise SealError(f"age did not finish within {timeout} s") from None
    return p.returncode, p.stdout, p.stderr


def find_age(age_bin: str | None = None) -> str:
    """Path of the age binary, or SealError. `age_bin` may be a bare name or a path."""
    name = age_bin or AGE_BIN
    if os.sep in name:
        if os.access(name, os.X_OK):
            return name
        raise SealError(f"age binary {name!r} is not an executable file")
    found = shutil.which(name)
    if found is None:
        for d in _EXTRA_BIN_DIRS:
            cand = os.path.join(d, name)
            if os.access(cand, os.X_OK):
                found = cand
                break
    if found is None:
        raise SealError("age is not installed (brew install age / apt install age): "
                        "refusing to seal without it, there is no fallback")
    return found


def _run(argv_tail: list, data: bytes, age_bin: str | None, runner: Runner | None,
         secret: bytes) -> bytes:
    # A custom runner stands in for the binary, so it is not looked up.
    argv = [find_age(age_bin) if runner is None else (age_bin or AGE_BIN), *argv_tail]
    rc, out, err = (runner or _subprocess_runner)(argv, data, TIMEOUT_S)
    if rc != 0:
        text = err.decode("utf-8", "replace")
        if len(secret) >= 4:  # belt and braces: age does not echo stdin, but never relay it
            text = text.replace(secret.decode("utf-8", "replace"), "<redacted>")
        raise SealError(f"age exited {rc}: {text.strip()[:200]}")
    return out


def seal(recipient: str, plaintext: bytes, *, age_bin: str | None = None,
         runner: Runner | None = None) -> bytes:
    """ASCII-armored age ciphertext of `plaintext` for `recipient` (age1...)."""
    from tools.hq_join import valid_age_recipient  # lazy: hq_join imports this module
    if not isinstance(recipient, str) or not valid_age_recipient(recipient):
        raise SealError("recipient is not a valid age X25519 recipient (age1...)")
    if not isinstance(plaintext, (bytes, bytearray)) or not plaintext:
        raise SealError("plaintext must be non-empty bytes")
    out = _run(["-r", recipient, "-a"], bytes(plaintext), age_bin, runner, bytes(plaintext))
    if not out.startswith(ARMOR_HEADER):
        raise SealError("age output is not an armored age file")
    return out


def open(identity_path: str, armored: bytes | str, *, age_bin: str | None = None,  # noqa: A001
         runner: Runner | None = None) -> bytes:
    """Decrypt armored age ciphertext with the identity file at `identity_path`.
    The path is an argument (it is not a secret); the ciphertext goes on stdin."""
    data = armored.encode("ascii") if isinstance(armored, str) else bytes(armored)
    if not data.lstrip().startswith(ARMOR_HEADER):
        raise SealError("input is not an armored age file")
    return _run(["-d", "-i", str(identity_path)], data, age_bin, runner, b"")
