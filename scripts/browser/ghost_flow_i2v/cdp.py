# -*- coding: utf-8 -*-
"""Stdlib raw-CDP helper for winbox Chrome :9226 - used because Playwright's connect_over_cdp hangs while ANOTHER session's
Flow tab is hung (flow_tabs_health.py shows HUNG). Talks only to a tab THIS script opened (own websocket); never attaches to the browser."""
import sys, socket, os, base64, json, struct, time, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
CDP = "http://127.0.0.1:9226"
STATE = "C:/mooniex/ghost_flow/tab.json"
def http(path, method="GET"):
    req = urllib.request.Request(CDP + path, method=method)
    return json.load(urllib.request.urlopen(req, timeout=10))
class Tab:
    def __init__(self, ws):
        host, rest = ws[5:].split("/", 1); h, port = host.split(":")
        self.s = socket.create_connection((h, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf: buf += self.s.recv(4096)
        self.i = 0; self.events = []
    def _send(self, obj):
        d = json.dumps(obj).encode(); mask = os.urandom(4); n = len(d); hdr = bytes([0x81])
        hdr += bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.s.sendall(hdr + mask + bytes(b ^ mask[k % 4] for k, b in enumerate(d)))
    def _rd(self, n):
        b = b""
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c: raise EOFError
            b += c
        return b
    def _recv(self):
        msg = b""
        while True:
            b1, b2 = self._rd(2); n = b2 & 0x7F
            if n == 126: n = struct.unpack(">H", self._rd(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._rd(8))[0]
            msg += self._rd(n)
            if b1 & 0x80: return json.loads(msg.decode("utf-8", "replace"))
    def call(self, method, timeout=30, **params):
        self.i += 1; i = self.i; self._send({"id": i, "method": method, "params": params}); t0 = time.time()
        self.s.settimeout(timeout)
        while time.time() - t0 < timeout:
            r = self._recv()
            if r.get("id") == i: return r
            self.events.append(r)
        raise TimeoutError(method)
    def ev(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r.get("result", {}): raise RuntimeError(str(r["result"]["exceptionDetails"])[:300])
        return r.get("result", {}).get("result", {}).get("value")
    def wait(self, s):
        time.sleep(s)
    def mute(self):
        self.ev("document.querySelectorAll('video,audio').forEach(v=>{v.muted=true;v.volume=0});1")
    def click_xy(self, x, y):
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=t, x=x, y=y, button="left", clickCount=1, buttons=1 if t == "mousePressed" else 0)
    def click(self, js_find, nth_visible=True):
        """js_find: JS expression returning an Element. Scrolls into view, trusted-clicks its centre."""
        r = self.ev("(()=>{const e=(%s); if(!e) return null; e.scrollIntoView({block:'center'}); const b=e.getBoundingClientRect(); return [b.x+b.width/2,b.y+b.height/2,b.width,b.height]})()" % js_find)
        if not r or r[2] == 0: raise RuntimeError("not found/zero size: " + js_find[:120])
        self.click_xy(r[0], r[1]); return r
    def key(self, k, code, vk):
        for t in ("keyDown", "keyUp"):
            self.call("Input.dispatchKeyEvent", type=t, key=k, code=code, windowsVirtualKeyCode=vk)
def project_url():
    return "https://flow.google.com/project/fc0fa309-571a-4584-a099-710123b78c80"
def open_tab(fresh=False):
    """Reuse the tab id saved in STATE (it is ours), else open a new one with PUT /json/new."""
    tid = None
    if os.path.exists(STATE) and not fresh:
        tid = json.load(open(STATE)).get("id")
    tabs = {t["id"]: t for t in http("/json/list")}
    if tid not in tabs:
        t = http("/json/new?" + urllib.parse.quote(project_url(), safe=":/"), "PUT")
        tid = t["id"]; tabs[tid] = t
        json.dump({"id": tid}, open(STATE, "w"))
    tab = Tab(tabs[tid]["webSocketDebuggerUrl"])
    tab.call("Page.enable"); tab.call("Runtime.enable")
    tab.call("Emulation.setFocusEmulationEnabled", enabled=True)
    tab.call("Emulation.setDeviceMetricsOverride", width=1600, height=1000, deviceScaleFactor=1, mobile=False)
    return tab, tid
