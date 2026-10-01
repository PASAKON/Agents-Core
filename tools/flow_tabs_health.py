#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which tab of the Flow Chrome is hung? Read-only, stdlib only — run it ON winbox.

Playwright `connect_over_cdp` attaches to EVERY page of the browser and waits for each; one renderer that does not
answer makes the whole attach time out ("<ws connecting> ws://…/devtools/browser/…") although /json/version and a raw
browser websocket answer in 0.0 s. Measured 2026-10-02: one stuck Flow project tab of another session blocked
tools/flow_shoot.py for everyone on :9226; closing that tab fixed the attach in 0.4 s.

    C:\\mooniex\\pwvenv\\Scripts\\python.exe tools\\flow_tabs_health.py [--port 9226] [--timeout 6]

Prints one line per page / worker: `<type> <url> -> (seconds, ok)` or `HUNG`. A HUNG page is the one to close:
`curl http://127.0.0.1:9226/json/close/<targetId>` — but it may be another session's tab, so ask its owner first.
"""
import argparse, base64, json, os, socket, struct, time, urllib.request


def ping(wsurl, timeout):
    host, rest = wsurl[5:].split("/", 1)
    h, port = host.split(":")
    s = socket.create_connection((h, int(port)), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
    s.settimeout(timeout)
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    d = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": "1+1"}}).encode()
    mask = os.urandom(4)
    s.sendall(bytes([0x81, 0x80 | len(d)]) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(d)))
    t = time.time()
    r = s.recv(4096)
    s.close()
    return round(time.time() - t, 2), b'"value":2' in r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9226)
    ap.add_argument("--timeout", type=float, default=6)
    a = ap.parse_args()
    tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{a.port}/json/list", timeout=8))
    hung = 0
    for t in tabs:
        if t["type"] != "page":
            continue
        u = t["url"][:80].encode("ascii", "replace").decode()
        try:
            print("page", u, "id", t["id"], "->", ping(t["webSocketDebuggerUrl"], a.timeout))
        except Exception as e:  # timeout / reset = the renderer does not answer
            hung += 1
            print("page", u, "id", t["id"], "-> HUNG", type(e).__name__)
    print("HUNG PAGES", hung)
    raise SystemExit(1 if hung else 0)


if __name__ == "__main__":
    main()
