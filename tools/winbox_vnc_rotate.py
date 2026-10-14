#!/usr/bin/env python3
"""Rotate winbox's TightVNC password and keep VNC on the tailnet only (COO OPEN row 13, LungNote 614a2d97).

Run it from a Run Inbox card on Contabo with --expects-input, as `.venv/bin/python tools/winbox_vnc_rotate.py`
(the system python3 has no cryptography.hazmat.decrepit). The card's stdin box types into the card's
terminal, and that terminal's output is stored on the hub, so this tool turns the terminal's echo off and
only then prints "ready"; the CEO types the new password after that line. Input already waiting when echo
went off had been echoed into the stored output, so it is refused. This tool:
  1. reads exactly 8 printable ASCII characters (VNC auth uses 8 bytes; TightVNC silently cuts a longer one,
     so a longer one is refused here instead);
  2. sends a fixed PowerShell script to winbox over ssh (-EncodedCommand, no user data in it) and the
     password over ssh's stdin, never in argv;
  3. on winbox: refuses the current password; writes the VNC-DES form to
     HKLM\\SOFTWARE\\TightVNC\\Server\\Password and reads it back (the old value is restored on a mismatch);
     reloads tvnserver and disconnects every open viewer (one logged in with the old password would
     otherwise stay); then narrows every enabled inbound Allow rule for tvnserver.exe or port 5900/5800 to
     the tailnet (100.64.0.0/10, fd7a:115c:a1e0::/48), printing each rule's old address and its undo line;
  4. from Contabo: a real RFB 3.8 handshake + VNC authentication with the new password over the tailnet,
     which prints "vnc auth OK" only when TightVNC accepts it; a failure restarts tvnserver once and checks again.
It never prints the password; any output line that contains it is replaced before printing.
"""
from __future__ import annotations

import base64
import fcntl
import ipaddress
import re
import socket
import struct
import subprocess
import sys
import termios

from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers import Cipher, modes

HOST_ALIAS = "winbox"               # ~/.ssh/config on Contabo (HostName = winbox's tailnet IP)
SSH = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=15"]
VNC_PORT = 5900
TAILNET = ipaddress.ip_network("100.64.0.0/10")
FIREWALL_FAILED = 6                 # the PS script's exit code when the new password is live but the rules are not narrowed
BOX_TIMED_OUT = 7                   # the box step hung; whether the password changed is proven by the auth check
PW_RE = re.compile(r"[\x21-\x7e]{8}")
# TightVNC/RFB store and authenticate with DES keyed by bit-reversed bytes. This is the fixed key every
# VNC server uses to obscure the stored password: {23,82,107,6,35,78,88,7}, bit-reversed per byte.
STORE_KEY = bytes((0xE8, 0x4A, 0xD6, 0x60, 0xC4, 0x72, 0x1A, 0xE0))

PS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
trap { 'ERROR: ' + $_.Exception.Message; exit 1 }
$pw = [Console]::In.ReadLine()
if ($pw -cnotmatch '^[\x21-\x7e]{8}$') { 'REFUSED: the box got something other than 8 printable ASCII characters; nothing changed'; exit 2 }
$des = [System.Security.Cryptography.DES]::Create()
$des.Mode = [System.Security.Cryptography.CipherMode]::ECB
$des.Padding = [System.Security.Cryptography.PaddingMode]::None
$des.Key = [byte[]](0xE8,0x4A,0xD6,0x60,0xC4,0x72,0x1A,0xE0)
function Open-Vnc([byte[]]$b) { [Text.Encoding]::ASCII.GetString($des.CreateDecryptor().TransformFinalBlock($b, 0, 8)).TrimEnd([char]0) }
$reg = 'HKLM:\SOFTWARE\TightVNC\Server'
$old = [byte[]](Get-ItemProperty -Path $reg -Name Password).Password
if ((Open-Vnc $old) -ceq $pw) { 'REFUSED: that is the current password; nothing changed'; exit 2 }
$enc = $des.CreateEncryptor().TransformFinalBlock([Text.Encoding]::ASCII.GetBytes($pw), 0, 8)
Set-ItemProperty -Path $reg -Name Password -Value ([byte[]]$enc) -Type Binary
$back = [byte[]](Get-ItemProperty -Path $reg -Name Password).Password
if ((Open-Vnc $back) -cne $pw) {
  Set-ItemProperty -Path $reg -Name Password -Value $old -Type Binary
  'FAILED: registry readback did not match; the old password was put back'; exit 3
}
'registry: Password replaced, readback matches'
$names = (Get-ItemProperty -Path $reg).PSObject.Properties.Name
foreach ($n in 'PasswordViewOnly', 'ControlPassword') { if ($names -contains $n) { 'WARN: ' + $n + ' is set and was left unchanged' } }
$exe = 'C:\Program Files\TightVNC\tvnserver.exe'
function Invoke-Tvn([string]$verb) {
  # bounded: an error MessageBox nobody can see would otherwise hang the ssh session
  $p = Start-Process -FilePath $exe -ArgumentList '-controlservice', $verb -PassThru -WindowStyle Hidden
  $null = $p.Handle
  if (-not $p.WaitForExit(15000)) { $p.Kill(); return 'timeout (killed)' }
  return $p.ExitCode
}
'service: reload exit ' + (Invoke-Tvn '-reload')
Start-Sleep -Seconds 3
'service: disconnect-all exit ' + (Invoke-Tvn '-disconnectall') + ', tvnserver ' + (Get-Service -Name tvnserver -ErrorAction SilentlyContinue).Status
function Test-VncPort($ports) {
  foreach ($x in @($ports)) {
    if ($x -eq '5900' -or $x -eq '5800') { return $true }
    if ($x -match '^(\d+)-(\d+)$') { foreach ($v in 5800, 5900) { if ([int]$matches[1] -le $v -and [int]$matches[2] -ge $v) { return $true } } }
  }
  return $false
}
$tailnet = @('100.64.0.0/10', 'fd7a:115c:a1e0::/48')
try {
  $found = @(Get-NetFirewallRule -DisplayName 'TightVNC' -ErrorAction SilentlyContinue)
  $found += @(Get-NetFirewallApplicationFilter | Where-Object { $_.Program -like '*\tvnserver.exe' } | Get-NetFirewallRule)
  $found += @(Get-NetFirewallPortFilter | Where-Object { Test-VncPort $_.LocalPort } | Get-NetFirewallRule)
  $rules = @($found | Where-Object { $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' -and $_.Enabled -eq 'True' } | Sort-Object -Property Name -Unique)
  if ($rules.Count -eq 0) { 'firewall: no enabled inbound Allow rule for tvnserver.exe or port 5900/5800 (nothing narrowed)' }
  foreach ($r in $rules) {
    $before = (($r | Get-NetFirewallAddressFilter).RemoteAddress) -join ','
    $r | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress $tailnet
    $after = (($r | Get-NetFirewallAddressFilter).RemoteAddress) -join ','
    'firewall: ' + $r.DisplayName + ' remote ' + $before + ' -> ' + $after
    'undo: Get-NetFirewallRule -Name ''' + $r.Name + ''' | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress ' + $before
  }
} catch {
  'ERROR firewall: ' + $_.Exception.Message + ' (the new password IS live; the firewall was not narrowed)'; exit 6
}
"""


def _pending(fd: int) -> int:
    return struct.unpack("i", fcntl.ioctl(fd, termios.FIONREAD, b"\0\0\0\0"))[0]


def read_password(stream, say=print) -> str:
    """Exactly 8 printable ASCII characters. On a terminal (the Run card's), echo goes off first and only
    then "ready" is said; anything already waiting by then was echoed into the card's output, so it is refused."""
    fd = old = None
    waiting = 0
    if stream.isatty():
        fd = stream.fileno()
        old = termios.tcgetattr(fd)
        raw = termios.tcgetattr(fd)
        raw[3] &= ~(termios.ECHO | termios.ICANON)       # with ICANON on, FIONREAD misses a line not yet ended
        termios.tcsetattr(fd, termios.TCSANOW, raw)
        waiting = _pending(fd)
        quiet = termios.tcgetattr(fd)
        quiet[3] = (quiet[3] | termios.ICANON) & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, quiet)
    try:
        if fd is not None:
            if waiting:
                raise SystemExit("refused: something was typed before 'ready' and the card may have shown it;"
                                 " nothing changed. Run the card again with a different password")
            say("ready: type the new 8-character password now (it is not shown)", flush=True)
        line = stream.readline()
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSANOW, old)
    pw = line.rstrip("\r\n")
    if not PW_RE.fullmatch(pw):
        raise SystemExit("refused: type exactly 8 printable ASCII characters (no spaces, no Thai); nothing changed")
    return pw


def ps_command() -> str:
    b64 = base64.b64encode(PS_SCRIPT.encode("utf-16-le")).decode("ascii")
    return f"powershell -NoProfile -NonInteractive -EncodedCommand {b64}"


def redact(text: str, pw: str) -> str:
    return text.replace(pw, "<redacted>") if pw else text


def _text(out) -> str:
    return out.decode("utf-8", "replace") if isinstance(out, bytes) else (out or "")


def apply_on_box(pw: str, run=subprocess.run) -> int:
    try:
        proc = run([*SSH, HOST_ALIAS, ps_command()], input=pw + "\r\n", capture_output=True,
                   text=True, errors="replace", timeout=300)
    except subprocess.TimeoutExpired as exc:
        for line in _text(exc.stdout).splitlines():
            if line.strip():
                print(redact(line.strip(), pw))
        print("winbox step timed out after 300 s; the VNC auth check below says whether the new password is live")
        return BOX_TIMED_OUT
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
    """winbox's address from ssh config; refused unless it is on the tailnet (the VNC response can be
    brute-forced offline, so it is never sent anywhere else)."""
    out = subprocess.run(["ssh", "-G", HOST_ALIAS], capture_output=True, text=True, timeout=10).stdout
    host = next(((l.split(None, 1) + [""])[1].strip() for l in out.splitlines() if l.startswith("hostname ")), "")
    try:
        if ipaddress.ip_address(host) in TAILNET:
            return host
    except ValueError:
        pass
    raise SystemExit(f"refused: ssh config gives winbox as {host!r}, not a tailnet address; nothing changed")


def main(argv=None) -> int:
    pw = read_password(sys.stdin)
    ip = box_ip()
    rc = apply_on_box(pw)
    if rc not in (0, FIREWALL_FAILED, BOX_TIMED_OUT):
        print(f"winbox step exited {rc}; VNC auth check skipped")
        return rc
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
    return rc if ok else 5


RESTART_PS = ("$ProgressPreference = 'SilentlyContinue'; Restart-Service -Name tvnserver -Force; "
              "Start-Sleep -Seconds 5; 'service: tvnserver ' + (Get-Service -Name tvnserver).Status")


def restart_service(run=subprocess.run) -> None:
    b64 = base64.b64encode(RESTART_PS.encode("utf-16-le")).decode("ascii")
    proc = run([*SSH, HOST_ALIAS, f"powershell -NoProfile -NonInteractive -EncodedCommand {b64}"],
               stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", timeout=90)
    for line in (proc.stdout or "").splitlines():
        if line.strip():
            print(line.strip())
    print(f"restart exit {proc.returncode}")


if __name__ == "__main__":
    raise SystemExit(main())
