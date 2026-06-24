#!/usr/bin/env python3
"""
Tiny read-only HTTPS file server for the Claude usage cache (Phase B).

Serves /opt/claude-usage-monitor/usage.json (mounted at /srv/usage.json) so the
iPhone widget can fetch live usage straight from the always-on VPS — meaning the
widget stays fresh even when the Mac is asleep / off / out of battery.

Access is gated by a secret token (?k=... or X-Token header). The data is just
utilization percentages + reset times (low sensitivity); the token mainly keeps
the endpoint from being casually scraped. Sits behind traefik (TLS).
"""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

TOKEN = os.environ.get("USAGE_TOKEN", "")
FILE  = os.environ.get("USAGE_FILE", "/srv/usage.json")
PORT  = int(os.environ.get("PORT", "8088"))


class Handler(BaseHTTPRequestHandler):
    def _deny(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(msg.encode())

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        tok = (q.get("k") or [""])[0] or self.headers.get("X-Token", "")
        if not TOKEN or tok != TOKEN:
            return self._deny(401, "unauthorized")
        try:
            with open(FILE, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            return self._deny(404, "no data yet")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass   # quiet


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
