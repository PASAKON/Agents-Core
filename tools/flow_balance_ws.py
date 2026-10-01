# -*- coding: utf-8 -*-
"""Read the Google Flow credit balance on winbox when playwright's browser-level attach hangs.

Read-only, stdlib only. Talks to ONE Flow project tab's own websocket (never the browser target):
mutes media, clicks the account button [aria-label="รายละเอียดบัญชี"], reads "เครดิต Google Flow N เครดิต", Escape.
Run ON winbox:  python tools\\flow_balance_ws.py [project-id-fragment]   (default: the Mimi project, 29b3326b)
If it prints "btn none" the page was still settling: run it again. Prints BALANCE <n> or BALANCE ?.
Do not point it at a project tab that is not yours.
"""
import sys
import socket, os, base64, json, re, struct, urllib.request, time
tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9226/json/list", timeout=8))
mine = [t for t in tabs if t["type"] == "page" and (sys.argv[1] if len(sys.argv) > 1 else "29b3326b") in t["url"]]
print("my tabs", len(mine))
ws = mine[0]["webSocketDebuggerUrl"]
host, rest = ws[5:].split("/", 1); h, port = host.split(":")
s = socket.create_connection((h, int(port)), timeout=15)
key = base64.b64encode(os.urandom(16)).decode()
s.sendall((f"GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
buf = b""
while b"\r\n\r\n" not in buf: buf += s.recv(4096)
print(buf.split(b"\r\n")[0].decode())
def send(obj):
    d = json.dumps(obj).encode(); mask = os.urandom(4)
    n = len(d); hdr = bytes([0x81])
    hdr += bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n)
    s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(d)))
def recv():
    def rd(n):
        b = b""
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c: raise EOFError
            b += c
        return b
    msg = b""
    while True:
        b1, b2 = rd(2); n = b2 & 0x7F
        if n == 126: n = struct.unpack(">H", rd(2))[0]
        elif n == 127: n = struct.unpack(">Q", rd(8))[0]
        msg += rd(n)
        if b1 & 0x80: return json.loads(msg.decode("utf-8", "replace"))
_id = [0]
def call(method, **params):
    _id[0] += 1; i = _id[0]; send({"id": i, "method": method, "params": params})
    t0 = time.time()
    while time.time() - t0 < 20:
        r = recv()
        if r.get("id") == i: return r
def ev(expr):
    r = call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
    return r.get("result", {}).get("result", {}).get("value")
print("mute", ev("document.querySelectorAll('video,audio').forEach(m=>{m.muted=true;m.pause()});1"))
print("btn", ev("""(()=>{const b=document.querySelector('[aria-label="รายละเอียดบัญชี"]'); if(!b) return 'none'; b.click(); return 'clicked'})()"""))
time.sleep(1.8)
txt = ev("document.body.innerText") or ""
call("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape", windowsVirtualKeyCode=27)
call("Input.dispatchKeyEvent", type="keyUp", key="Escape", code="Escape", windowsVirtualKeyCode=27)
i = txt.find("Google Flow")
print("MENU:", " ".join(txt[i + 100: i + 320].split()) if i >= 0 else "no 'Google Flow' text")
m = re.search(r"([\d,]+)\s*เครดิต", txt[i:i + 200]) if i >= 0 else None
print("BALANCE", m.group(1).replace(",", "") if m else "?")
