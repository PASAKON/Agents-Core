"""winbox VNC rotation: the password never reaches argv or output; the VNC-DES key and auth are right."""
from __future__ import annotations

import base64
import io
import os
import pty
import select
import socket
import subprocess
import termios
import threading
import time

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
    assert seen["args"][:2] == ["ssh", "-T"] and vr.HOST_ALIAS in seen["args"]   # -T: no remote pty to echo stdin
    assert "StrictHostKeyChecking=yes" in seen["args"] and "BatchMode=yes" in seen["args"]
    out = capsys.readouterr().out
    assert PW not in out and "<redacted>" in out


def test_a_failed_box_step_skips_the_auth_check(monkeypatch, capsys):
    monkeypatch.setattr(vr.sys, "stdin", io.StringIO(PW + "\n"))
    monkeypatch.setattr(vr, "box_ip", lambda: "100.64.0.9")
    monkeypatch.setattr(vr, "apply_on_box", lambda pw: 3)
    monkeypatch.setattr(vr, "vnc_auth", lambda *a, **k: pytest.fail("auth ran after a failed box step"))
    assert vr.main([]) == 3
    assert "skipped" in capsys.readouterr().out


def test_a_refused_password_never_calls_ssh(monkeypatch):
    monkeypatch.setattr(vr.sys, "stdin", io.StringIO("short\n"))
    monkeypatch.setattr(vr, "box_ip", lambda: pytest.fail("ssh -G ran on a refused password"))
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
        returncode = 0

    vr.restart_service(run=lambda args, **kw: seen.update(args=args, kw=kw) or P())
    assert "input" not in seen["kw"]
    assert seen["kw"]["stdin"] is subprocess.DEVNULL   # never inherits the card's terminal


def _drain(fd: int) -> bytes:
    out = b""
    while select.select([fd], [], [], 0.3)[0]:
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    return out


def test_on_the_cards_terminal_the_typed_password_is_never_echoed():
    # The Run card's stdin box types into a pty whose output the hub stores (B1 of the review).
    master, slave = pty.openpty()
    stream = os.fdopen(slave, "r", closefd=False)
    ready, got = threading.Event(), {}

    def say(*a, **k):
        ready.set()

    t = threading.Thread(target=lambda: got.update(pw=vr.read_password(stream, say=say)), daemon=True)
    t.start()
    assert ready.wait(5), "never said ready"
    assert not termios.tcgetattr(slave)[3] & termios.ECHO
    os.write(master, (PW + "\n").encode())
    t.join(5)
    assert got["pw"] == PW
    assert PW.encode() not in _drain(master)
    assert termios.tcgetattr(slave)[3] & termios.ECHO      # echo is back afterwards
    os.close(master), os.close(slave)


def test_typing_before_ready_is_refused_because_it_was_echoed():
    master, slave = pty.openpty()
    os.write(master, (PW + "\n").encode())                 # echo is still on: the terminal shows it
    time.sleep(0.2)
    stream = os.fdopen(slave, "r", closefd=False)
    with pytest.raises(SystemExit) as exc:
        vr.read_password(stream, say=lambda *a, **k: pytest.fail("said ready with input waiting"))
    assert "before 'ready'" in str(exc.value)
    assert termios.tcgetattr(slave)[3] & termios.ECHO
    os.close(master), os.close(slave)


@pytest.mark.parametrize("host,ok", [("100.64.0.9", True), ("100.127.255.254", True), ("192.168.1.20", False), ("winbox", False), ("", False)])
def test_the_box_address_must_be_on_the_tailnet(monkeypatch, host, ok):
    class P:
        stdout = f"user x\nhostname {host}\nport 22\n"

    monkeypatch.setattr(vr.subprocess, "run", lambda *a, **k: P())
    if ok:
        assert vr.box_ip() == host
    else:
        with pytest.raises(SystemExit) as exc:
            vr.box_ip()
        assert "nothing changed" in str(exc.value)


def test_a_firewall_failure_still_proves_the_new_password_and_exits_6(monkeypatch, capsys):
    monkeypatch.setattr(vr.sys, "stdin", io.StringIO(PW + "\n"))
    monkeypatch.setattr(vr, "box_ip", lambda: "100.64.0.9")
    monkeypatch.setattr(vr, "apply_on_box", lambda pw: vr.FIREWALL_FAILED)
    monkeypatch.setattr(vr, "vnc_auth", lambda ip, pw: True)
    assert vr.main([]) == vr.FIREWALL_FAILED
    assert "vnc auth OK" in capsys.readouterr().out


def test_the_box_script_refuses_the_old_password_reloads_then_disconnects_then_narrows():
    ps = vr.PS_SCRIPT
    assert "that is the current password; nothing changed" in ps
    assert ps.index("-reload") < ps.index("-disconnectall") < ps.index("Set-NetFirewallAddressFilter")
    assert "trap {" in ps and "fd7a:115c:a1e0::/48" in ps and "'undo: " in ps
    # $pw is only compared and encoded on the box, never printed
    uses = [l for l in ps.splitlines() if "$pw" in l]
    assert all(("-cnotmatch" in l or "-ceq $pw" in l or "-cne $pw" in l or "GetBytes($pw)" in l
                or l.startswith("$pw = ")) for l in uses)


def test_a_line_typed_before_ready_without_enter_is_still_refused():
    # R2-M1: with ICANON on, FIONREAD counts only finished lines; the half line had already been echoed.
    master, slave = pty.openpty()
    os.write(master, PW.encode())                          # no newline yet
    time.sleep(0.2)
    stream = os.fdopen(slave, "r", closefd=False)
    with pytest.raises(SystemExit) as exc:
        vr.read_password(stream, say=lambda *a, **k: pytest.fail("said ready with a half line waiting"))
    assert "before 'ready'" in str(exc.value)
    attrs = termios.tcgetattr(slave)[3]
    assert attrs & termios.ECHO and attrs & termios.ICANON   # the terminal is put back as it was
    os.close(master), os.close(slave)


def test_a_hung_box_step_prints_what_it_has_and_still_runs_the_auth_check(monkeypatch, capsys):
    def hang(args, **kw):
        raise subprocess.TimeoutExpired(args, 300, output=b"registry: Password replaced, readback matches\n")

    assert vr.apply_on_box(PW, run=hang) == vr.BOX_TIMED_OUT
    out = capsys.readouterr().out
    assert "readback matches" in out and "timed out" in out
    monkeypatch.setattr(vr.sys, "stdin", io.StringIO(PW + "\n"))
    monkeypatch.setattr(vr, "box_ip", lambda: "100.64.0.9")
    monkeypatch.setattr(vr, "apply_on_box", lambda pw: vr.BOX_TIMED_OUT)
    monkeypatch.setattr(vr, "vnc_auth", lambda ip, pw: True)
    assert vr.main([]) == vr.BOX_TIMED_OUT
    assert "vnc auth OK" in capsys.readouterr().out


def test_tvnserver_calls_are_bounded_and_port_ranges_count():
    assert "WaitForExit(15000)" in vr.PS_SCRIPT and "& $exe" not in vr.PS_SCRIPT
    assert "Test-VncPort $_.LocalPort" in vr.PS_SCRIPT
