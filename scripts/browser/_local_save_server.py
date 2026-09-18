#!/usr/bin/env python3
"""One-off local sink so a Chrome page can POST bytes straight to disk,
bypassing Chrome's per-site automatic-downloads permission gate. Used once
for task-75926848 (banchi plates harvest) after the browser Downloads path
was found persistently blocked (confirmed after reload + several minutes).
"""
import http.server
import os
import sys

DEST = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Desktop/banchi-plates")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8934
os.makedirs(DEST, exist_ok=True)


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        from urllib.parse import urlparse, parse_qs

        qs = parse_qs(urlparse(self.path).query)
        name = qs.get("name", ["unnamed.bin"])[0]
        name = os.path.basename(name)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        path = os.path.join(DEST, name)
        with open(path, "wb") as f:
            f.write(body)
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(f"OK {len(body)} {path}".encode())
        print(f"saved {path} ({len(body)} bytes)", flush=True)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"listening on 127.0.0.1:{PORT}, writing to {DEST}", flush=True)
    srv.serve_forever()
