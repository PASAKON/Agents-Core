#!/usr/bin/env python3
"""Rotate winbox's TightVNC password and keep VNC on the tailnet only (COO OPEN row 13, LungNote 614a2d97).

The old password leaked, and TightVNC listened on 0.0.0.0:5900 behind a firewall rule open to every
profile (the Ethernet profile is Public), so the leaked password worked from the LAN as well as over
Tailscale (read-only check, CTO #c34459eb, 2026-10-14).

Run it from a Run Inbox card on Contabo with --expects-input. The CEO types the new password into the
card's stdin box, which the hub never stores or logs (Console docs/run.md). This tool:
  1. reads exactly 8 printable ASCII characters from stdin (VNC auth uses 8 bytes; TightVNC silently
     cuts a longer one, so a longer one is refused here instead);
  2. sends a fixed PowerShell script to winbox over ssh (-EncodedCommand, no user data in it) and the
     password over ssh's stdin, never in argv;
  3. on winbox: writes the VNC-DES form of the password to HKLM\\SOFTWARE\\TightVNC\\Server\\Password,
     reads it back and compares (the old value is restored on a mismatch), narrows the "TightVNC"
     firewall rule to the tailnet (100.64.0.0/10), reloads tvnserver;
  4. from Contabo: a real RFB 3.8 handshake + VNC authentication with the new password over the tailnet,
     which prints "vnc auth OK" only when TightVNC accepts it.
It never prints the password; any output line that contains it is replaced before printing.

Undo the firewall step (if a phone off the tailnet must reach VNC): on winbox, as admin,
  Get-NetFirewallRule -DisplayName TightVNC | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress Any
"""
from __future__ import annotations

import base64
import re
import socket
import subprocess
import sys

HOST_ALIAS = "winbox"               # ~/.ssh/config on Contabo (HostName = winbox's tailnet IP)
VNC_PORT = 5900
TAILNET = "100.64.0.0/10"
PW_RE = re.compile(r"^[\x21-\x7e]{8}$")
# TightVNC/RFB store and authenticate with DES keyed by bit-reversed bytes. This is the fixed key every
# VNC server uses to obscure the stored password: {23,82,107,6,35,78,88,7}, bit-reversed per byte.
STORE_KEY = bytes((0xE8, 0x4A, 0xD6, 0x60, 0xC4, 0x72, 0x1A, 0xE0))

PS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$pw = [Console]::In.ReadLine()
if ($pw -cnotmatch '^[\x21-\x7e]{8}$') { 'REFUSED: the box got something other than 8 printable ASCII characters'; exit 2 }
$des = [System.Security.Cryptography.DES]::Create()
$des.Mode = [System.Security.Cryptography.CipherMode]::ECB
$des.Padding = [System.Security.Cryptography.PaddingMode]::None
$des.Key = [byte[]](0xE8,0x4A,0xD6,0x60,0xC4,0x72,0x1A,0xE0)
$enc = $des.CreateEncryptor().TransformFinalBlock([Text.Encoding]::ASCII.GetBytes($pw), 0, 8)
$reg = 'HKLM:\SOFTWARE\TightVNC\Server'
$old = [byte[]](Get-ItemProperty -Path $reg -Name Password).Password
Set-ItemProperty -Path $reg -Name Password -Value ([byte[]]$enc) -Type Binary
$back = [byte[]](Get-ItemProperty -Path $reg -Name Password).Password
$dec = [Text.Encoding]::ASCII.GetString($des.CreateDecryptor().TransformFinalBlock($back, 0, 8))
if ($dec -cne $pw) {
  Set-ItemProperty -Path $reg -Name Password -Value $old -Type Binary
  'FAILED: registry readback did not match; the old password was put back'; exit 3
}
'registry: Password replaced, readback matches'
$rules = @(Get-NetFirewallRule -DisplayName 'TightVNC' -ErrorAction SilentlyContinue)
if ($rules.Count -eq 0) { 'firewall: no rule named TightVNC (nothing narrowed)' }
foreach ($r in $rules) {
  $r | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress '100.64.0.0/10'
  'firewall: ' + $r.DisplayName + ' remote=' + ((($r | Get-NetFirewallAddressFilter).RemoteAddress) -join ',') + ' enabled=' + $r.Enabled
}
& 'C:\Program Files\TightVNC\tvnserver.exe' -controlservice -reload
Start-Sleep -Seconds 3
'service: tvnserver ' + (Get-Service -Name tvnserver).Status
"""


def read_password(stream) -> str:
    line = stream.readline()
    pw = line.rstrip("\r\n")
    if not PW_RE.match(pw):
        raise SystemExit("refused: type exactly 8 printable ASCII characters (no spaces, no Thai); nothing changed")
    return pw


def ps_command() -> str:
    b64 = base64.b64encode(PS_SCRIPT.encode("utf-16-le")).decode("ascii")
    return f"powershell -NoProfile -NonInteractive -EncodedCommand {b64}"


def redact(text: str, pw: str) -> str:
    return text.replace(pw, "<redacted>") if pw else text


def apply_on_box(pw: str, run=subprocess.run) -> int:
    proc = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST_ALIAS, ps_command()],
               input=pw + "\r\n", capture_output=True, text=True, timeout=180)
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line:
            print(redact(line, pw))
    if proc.returncode != 0:
        err = [l for l in (proc.stderr or "").splitlines() if l.strip() and "CLIXML" not in l and "<Objs" not in l]
        for l in err[-5:]:
            print("  stderr: " + redact(l.strip(), pw)[:200])
    return proc.returncode


def _bitrev(b: int) -> int:
    return int(f"{b:08b}"[::-1], 2)


def vnc_response(pw: str, challenge: bytes) -> bytes:
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
    from cryptography.hazmat.primitives.ciphers import Cipher, modes
    key = bytes(_bitrev(c) for c in pw.encode("ascii").ljust(8, b"\0")[:8])
    enc = Cipher(TripleDES(key * 3), modes.ECB()).encryptor()   # K1=K2=K3 = single DES
    return enc.update(challenge) + enc.finalize()


def _recv(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            raise ConnectionError("VNC server closed the connection")
        buf += part
    return buf


def vnc_auth(host: str, pw: str, port: int = VNC_PORT, timeout: float = 15.0) -> bool:
    """A real RFB 3.8 handshake + VNC authentication. True only when the server says OK."""
    with socket.create_connection((host, port), timeout=timeout) as s:
        banner = _recv(s, 12)
        if not banner.startswith(b"RFB 003."):
            raise ConnectionError(f"not an RFB server: {banner!r}")
        s.sendall(b"RFB 003.008\n")
        count = _recv(s, 1)[0]
        if count == 0:
            raise ConnectionError("server refused the connection before auth")
        types = _recv(s, count)
        if 2 not in types:
            raise ConnectionError(f"server does not offer VNC authentication (types {list(types)})")
        s.sendall(bytes([2]))
        s.sendall(vnc_response(pw, _recv(s, 16)))
        return int.from_bytes(_recv(s, 4), "big") == 0


def box_ip() -> str:
    out = subprocess.run(["ssh", "-G", HOST_ALIAS], capture_output=True, text=True, timeout=10).stdout
    for line in out.splitlines():
        if line.startswith("hostname "):
            return line.split(None, 1)[1].strip()
    raise SystemExit("cannot resolve the winbox address from ssh config")


def main(argv=None) -> int:
    pw = read_password(sys.stdin)
    rc = apply_on_box(pw)
    if rc != 0:
        print(f"winbox step exited {rc}; VNC auth check skipped")
        return rc
    ip = box_ip()
    try:
        ok = vnc_auth(ip, pw)
    except (OSError, ConnectionError) as exc:
        print("vnc auth check could not run: " + redact(str(exc), pw)[:200])
        return 4
    if not ok:
        # A reload that did not pick up the new value: restart the service once (drops any viewer for a
        # few seconds) and check again. No secret goes over this second ssh call.
        print("vnc auth FAILED after reload; restarting tvnserver once")
        restart_service()
        try:
            ok = vnc_auth(ip, pw)
        except (OSError, ConnectionError) as exc:
            print("vnc auth check could not run: " + redact(str(exc), pw)[:200])
            return 4
    print(f"vnc auth {'OK' if ok else 'FAILED'} with the new password over the tailnet ({ip}:{VNC_PORT})")
    return 0 if ok else 5


RESTART_PS = ("$ProgressPreference = 'SilentlyContinue'; Restart-Service -Name tvnserver -Force; "
              "Start-Sleep -Seconds 5; 'service: tvnserver ' + (Get-Service -Name tvnserver).Status")


def restart_service(run=subprocess.run) -> None:
    b64 = base64.b64encode(RESTART_PS.encode("utf-16-le")).decode("ascii")
    proc = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST_ALIAS,
                f"powershell -NoProfile -NonInteractive -EncodedCommand {b64}"],
               capture_output=True, text=True, timeout=90)
    for line in (proc.stdout or "").splitlines():
        if line.strip():
            print(line.strip())


if __name__ == "__main__":
    raise SystemExit(main())
