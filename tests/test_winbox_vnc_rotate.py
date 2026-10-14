"""winbox VNC rotation: the password never reaches argv or output; the VNC-DES key and auth are right."""
from __future__ import annotations

import base64
import io
import os
import socket
import threading

import pytest

from tools import winbox_vnc_rotate as vr

PW = "Xy7#kQ2!"


@pytest.mark.parametrize("line", ["Xy7#kQ2!\n", "Xy7#kQ2!\r\n", "Xy7#kQ2!"])
def test_exactly_eight_printable_ascii_is_accepted(line):
    assert vr.read_password(io.StringIO(line)) == PW


@pytest.mark.parametrize("line", ["", "\n", "short7!\n", "nine9999!\n", "has space\n", "ab cd ef\n",
                                  "รหัสผ่าน12\n", "abc\tdefg\n", "abcdefg\x00\n"])
def test_anything_else_is_refused_before_ssh(line):
    with pytest.raises(SystemExit) as exc:
        vr.read_password(io.StringIO(line))
    assert "nothing changed" in str(exc.value)


def test_the_store_key_decodes_the_public_tightvnc_vector():
    # The widely published TightVNC registry example: d7a514d8c556aade -> "Secure!".
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
    from cryptography.hazmat.primitives.ciphers import Cipher, modes
    dec = Cipher(TripleDES(vr.STORE_KEY * 3), modes.ECB()).decryptor()
    assert dec.update(bytes.fromhex("d7a514d8c556aade")) + dec.finalize() == b"Secure!\0"
    # and the PowerShell script carries the same key bytes
    assert "0xE8,0x4A,0xD6,0x60,0xC4,0x72,0x1A,0xE0" in vr.PS_SCRIPT


def test_the_remote_command_is_fixed_and_carries_no_password():
    cmd = vr.ps_command()
    b64 = cmd.rsplit(" ", 1)[1]
    assert base64.b64decode(b64).decode("utf-16-le") == vr.PS_SCRIPT
    assert PW not in cmd


def test_password_goes_over_stdin_never_argv_and_output_is_redacted(capsys):
    seen = {}

    class P:
        returncode = 0
        stdout = "registry: Password replaced, readback matches\nechoed " + PW + " by mistake\n"
        stderr = ""

    def run(args, **kw):
        seen["args"], seen["kw"] = args, kw
        return P()

    assert vr.apply_on_box(PW, run=run) == 0
    assert all(PW not in a for a in seen["args"])
    assert seen["kw"]["input"] == PW + "\r\n"
    assert seen["args"][:2] == ["ssh", "-o"] and vr.HOST_ALIAS in seen["args"]
    out = capsys.readouterr().out
    assert PW not in out and "<redacted>" in out


def test_a_failed_box_step_skips_the_auth_check(monkeypatch, capsys):
    monkeypatch.setattr(vr.sys, "stdin", io.StringIO(PW + "\n"))
    monkeypatch.setattr(vr, "apply_on_box", lambda pw: 3)
    monkeypatch.setattr(vr, "vnc_auth", lambda *a, **k: pytest.fail("auth ran after a failed box step"))
    assert vr.main([]) == 3
    assert "skipped" in capsys.readouterr().out


def test_a_refused_password_never_calls_ssh(monkeypatch):
    monkeypatch.setattr(vr.sys, "stdin", io.StringIO("short\n"))
    monkeypatch.setattr(vr, "apply_on_box", lambda pw: pytest.fail("ssh ran on a refused password"))
    with pytest.raises(SystemExit):
        vr.main([])


_REV = {i: int("".join(reversed(format(i, "08b"))), 2) for i in range(256)}


def _fake_rfb(server_pw: str, result: dict):
    """A minimal RFB 3.8 server doing VNC auth with server_pw; its key derivation is table-based."""
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
    from cryptography.hazmat.primitives.ciphers import Cipher, modes
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def serve():
        conn, _ = srv.accept()
        with conn:
            conn.sendall(b"RFB 003.008\n")
            conn.recv(12)
            conn.sendall(bytes([2, 16, 2]))
            pick = conn.recv(1)
            challenge = os.urandom(16)
            conn.sendall(challenge)
            got = b""
            while len(got) < 16:
                got += conn.recv(16 - len(got))
            key = bytes(_REV[b] for b in server_pw.encode().ljust(8, b"\0"))
            enc = Cipher(TripleDES(key * 3), modes.ECB()).encryptor()
            ok = pick == b"\x02" and got == enc.update(challenge) + enc.finalize()
            result["ok"] = ok
            conn.sendall((0 if ok else 1).to_bytes(4, "big"))
        srv.close()

    threading.Thread(target=serve, daemon=True).start()
    return srv.getsockname()[1]


def test_vnc_auth_ok_with_the_right_password():
    result = {}
    port = _fake_rfb(PW, result)
    assert vr.vnc_auth("127.0.0.1", PW, port=port, timeout=5) is True
    assert result["ok"] is True


def test_vnc_auth_fails_with_a_wrong_password():
    result = {}
    port = _fake_rfb(PW, result)
    assert vr.vnc_auth("127.0.0.1", "Wrong#99", port=port, timeout=5) is False


def test_a_failed_auth_restarts_the_service_once_then_rechecks(monkeypatch, capsys):
    monkeypatch.setattr(vr.sys, "stdin", io.StringIO(PW + "\n"))
    monkeypatch.setattr(vr, "apply_on_box", lambda pw: 0)
    monkeypatch.setattr(vr, "box_ip", lambda: "100.64.0.9")
    answers = iter([False, True])
    monkeypatch.setattr(vr, "vnc_auth", lambda ip, pw: next(answers))
    restarts = []
    monkeypatch.setattr(vr, "restart_service", lambda: restarts.append(1))
    assert vr.main([]) == 0
    assert restarts == [1]
    out = capsys.readouterr().out
    assert "vnc auth OK" in out and PW not in out


def test_the_restart_call_carries_no_input():
    seen = {}

    class P:
        stdout = "service: tvnserver Running\n"

    vr.restart_service(run=lambda args, **kw: seen.update(args=args, kw=kw) or P())
    assert "input" not in seen["kw"]
