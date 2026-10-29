#!/usr/bin/env python3
"""Disk hub for the "Disk Monitor" widget — one endpoint for three machines.

Runs on the always-on VPS (Contabo) behind traefik, like the usage servers.
Each machine PUSHES its own numbers; the hub keeps the latest report per host
plus 8 days (192 h, at most 1300 rows) of history, and the widget GETs one combined
document. Only `trend` reads the history today, and it looks back 30 h at most. A machine
that sleeps (the Mac) or drops off the network (winbox) simply stops pushing:
its last numbers stay, with `received_at` telling the widget how old they are.

    GET  /disk?k=<USAGE_TOKEN>                  -> combined JSON (below)
    POST /disk?k=<DISK_PUSH_TOKEN>&host=<name>  body: {"volumes": [...], "observed_at": "..."}

Two tokens on purpose: the read token already sits in the phone widget's URL;
if it could also write, anyone holding the widget could post fake numbers.

Report volume shape (first volume = the one that matters, e.g. C: or /):
    {"name": "C:", "mount": "C:\\", "size_bytes": 510240079872, "free_bytes": 11489771520}

Combined response:
    {"generated_at": ISO, "hosts": [
       {"host": "winbox", "label": "winbox", "received_at": ISO, "observed_at": ISO,
        "volumes": [...], "trend": {"free_delta_bytes": -18253611008, "span_hours": 23.8}}, ...]}
`trend` compares the newest free space of the first volume with the sample
closest to 24 h earlier among the samples of the last 30 h (the oldest of them, if
less history exists); it is omitted until at least 1 h of history exists.

Adaptive reporting (CEO 2026-09-23: "ยิงลดเยอะยิ่ง Update บ่อย … นิ่งก็ถอยไป
30 นาที 1 ชม. 3 ชม. 4 ชม. … ใช้เยอะกะทันหันปรับทันที", minimum 10 min).
Machines MEASURE every 10 min (a local read, free) but only REPORT when the
hub's schedule says so, or when free space moved by `force_delta_bytes` since
their last report. The schedule is decided here, from how fast the first
volume moved between the last two reports — see `schedule()`. Each stored doc
carries it, so the widget can tell "quiet by design" from "stopped reporting".
RAM (CEO 2026-10-06, "RAM Monitor" widget): same hub, same two tokens, its
own path under the same traefik prefix, so nothing new is routed or minted.

    GET  /disk/ram?k=<USAGE_TOKEN>                  -> {"generated_at", "hosts": [ram docs]}
    POST /disk/ram?k=<DISK_PUSH_TOKEN>&host=<name>  body: see `validate_ram()`

A RAM report is a snapshot (memory totals + the biggest process groups, sessions
and apps alike, with their RSS and how long they have run). Only the latest is
kept; there is no history and no schedule: machines report every 10 min.
Standard library only.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

READ_TOKEN = os.environ.get("USAGE_TOKEN", "")
PUSH_TOKEN = os.environ.get("DISK_PUSH_TOKEN", "")
DATA_DIR = Path(os.environ.get("DISK_DIR", "/srv/disk"))
PORT = int(os.environ.get("PORT", "8088"))

# Display order and labels. A host not listed here is refused.
HOSTS = {"mac": "Mac", "winbox": "winbox", "contabo": "Contabo"}
MAX_BODY = 8192
MAX_VOLUMES = 6
HISTORY_HOURS = 192
TREND_TARGET_H = 24

GBB = 10**9
# Report cadence. 10 min is the floor (the machines' measuring tick); stillness
# steps up one rung per quiet report.
LADDER_S = [600, 1800, 3600, 10800, 14400]
# Free-space floors, same numbers as the widget: under it a machine is watched
# closer (cadence capped, smaller jump forces a report).
FLOOR_GB = {"mac": 20, "winbox": 30, "contabo": 10}


def _epoch(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def schedule(host: str, prev: dict | None, free: int, now: float) -> dict:
    """Decide when this host reports next.

    prev = the host's previously stored doc (or None). Rate = how fast the first
    volume's free space moved between the previous report and this one, in
    either direction — a clean-up is news too.
    """
    below = free < FLOOR_GB.get(host, 10) * GBB
    force = GBB // 2 if below else GBB
    prev_t = _epoch(prev.get("received_at")) if prev else None
    prev_free = prev["volumes"][0]["free_bytes"] if prev and prev.get("volumes") else None
    prev_int = ((prev or {}).get("schedule") or {}).get("interval_s") or LADDER_S[0]
    if prev_t is None or prev_free is None:
        interval, reason, rate = LADDER_S[0], "first report", None
    else:
        hours = max((now - prev_t) / 3600, 1 / 60)
        delta = abs(free - prev_free)
        rate = delta / hours
        if rate >= 2 * GBB or delta >= 2 * GBB:
            interval, reason = LADDER_S[0], "moving fast"
        elif rate >= 0.5 * GBB:
            interval, reason = 1800, "moving"
        elif rate >= 0.1 * GBB:
            interval, reason = 3600, "moving slowly"
        else:
            nxt = [r for r in LADDER_S if r > prev_int]
            interval, reason = (nxt[0] if nxt else LADDER_S[-1]), "still"
    if below and interval > 1800:
        interval, reason = 1800, reason + ", below floor"
    return {"interval_s": interval, "next_due_at": _iso(now + interval), "force_delta_bytes": force,
            "reason": reason, "rate_bytes_per_h": None if rate is None else int(rate)}


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


def validate(body: dict) -> list[dict]:
    """Return the cleaned volume list, or raise ValueError with a reason."""
    vols = body.get("volumes")
    if not isinstance(vols, list) or not vols:
        raise ValueError("volumes must be a non-empty list")
    if len(vols) > MAX_VOLUMES:
        raise ValueError(f"at most {MAX_VOLUMES} volumes")
    out = []
    for v in vols:
        if not isinstance(v, dict):
            raise ValueError("each volume must be an object")
        size, free = v.get("size_bytes"), v.get("free_bytes")
        if not (isinstance(size, int) and isinstance(free, int)) or isinstance(size, bool) or isinstance(free, bool):
            raise ValueError("size_bytes and free_bytes must be integers")
        if size <= 0 or free < 0 or free > size:
            raise ValueError("need 0 <= free_bytes <= size_bytes and size_bytes > 0")
        out.append({"name": str(v.get("name") or "")[:40], "mount": str(v.get("mount") or "")[:80],
                    "size_bytes": size, "free_bytes": free})
    return out


def record(host: str, volumes: list[dict], observed_at: str | None, now: float | None = None,
           data_dir: Path | None = None) -> dict:
    """Store the latest report and append to the host's history (trimmed)."""
    now = time.time() if now is None else now
    d = data_dir or DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    prev = None
    if (d / f"{host}.json").exists():
        try:
            prev = json.loads((d / f"{host}.json").read_text())
        except json.JSONDecodeError:
            prev = None
    doc = {"host": host, "label": HOSTS[host], "received_at": _iso(now),
           "observed_at": (observed_at or "")[:40] or None, "volumes": volumes,
           "schedule": schedule(host, prev, volumes[0]["free_bytes"], now)}
    tmp = d / f".{host}.json.tmp"
    tmp.write_text(json.dumps(doc))
    tmp.replace(d / f"{host}.json")

    hist = d / f"{host}.hist.jsonl"
    rows = _history(hist)
    rows.append({"t": now, "free": volumes[0]["free_bytes"]})
    rows = [r for r in rows if r["t"] >= now - HISTORY_HOURS * 3600][-1300:]
    tmp = d / f".{host}.hist.tmp"
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    tmp.replace(hist)
    return doc


def _history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            r = json.loads(line)
            if isinstance(r.get("t"), (int, float)) and isinstance(r.get("free"), int):
                rows.append(r)
        except json.JSONDecodeError:
            continue
    return rows


def trend(rows: list[dict]) -> dict | None:
    if len(rows) < 2:
        return None
    newest = rows[-1]
    # Trend math must keep using <= 30 h even though rows now holds up to 192 h.
    recent = [r for r in rows[:-1] if r["t"] >= newest["t"] - 30 * 3600]
    if not recent:
        return None
    target = newest["t"] - TREND_TARGET_H * 3600
    ref = min(recent, key=lambda r: abs(r["t"] - target))
    span = (newest["t"] - ref["t"]) / 3600
    if span < 1 or span > 30:
        return None
    return {"free_delta_bytes": newest["free"] - ref["free"], "span_hours": round(span, 1)}


def combined(data_dir: Path | None = None, now: float | None = None) -> dict:
    d = data_dir or DATA_DIR
    hosts = []
    for host in HOSTS:
        p = d / f"{host}.json"
        if not p.exists():
            continue
        try:
            doc = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        t = trend(_history(d / f"{host}.hist.jsonl"))
        if t:
            doc["trend"] = t
        hosts.append(doc)
    return {"generated_at": _iso(time.time() if now is None else now), "hosts": hosts}


# ---------- RAM ----------
MAX_RAM_BODY = 24576
MAX_GROUPS = 24
KINDS = ("session", "app")
PRESSURE = ("normal", "warn", "critical")


def _int(v, name: str, lo: int = 0) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or v < lo:
        raise ValueError(f"{name} must be an integer >= {lo}")
    return v


def _str(v, n: int) -> str | None:
    return None if v is None else str(v)[:n]


def validate_ram(body: dict) -> dict:
    """Clean a RAM report or raise ValueError.

    {"observed_at": ISO, "uptime_s": int,
     "mem": {"total": int, "used": int, "available": int, "swap_total": int, "swap_used": int,
             "pressure": "normal"|"warn"|"critical"|null},
     "groups": [{"kind": "session"|"app", "name": str, "role": str|null, "sid": str|null,
                 "topic": str|null, "rss": int, "up_s": int, "busy": bool|null, "n": int}, ...],
     "rest": {"count": int, "rss": int}, "sessions": int, "sessions_busy": int}
    """
    mem = body.get("mem")
    if not isinstance(mem, dict):
        raise ValueError("mem must be an object")
    total = _int(mem.get("total"), "mem.total", 1)
    clean_mem = {"total": total}
    for k in ("used", "available", "swap_total", "swap_used"):
        clean_mem[k] = _int(mem.get(k, 0), "mem." + k)
    if clean_mem["used"] > total or clean_mem["available"] > total:
        raise ValueError("mem.used and mem.available must not exceed mem.total")
    pr = mem.get("pressure")
    clean_mem["pressure"] = pr if pr in PRESSURE else None
    groups = body.get("groups")
    if not isinstance(groups, list):
        raise ValueError("groups must be a list")
    if len(groups) > MAX_GROUPS:
        raise ValueError(f"at most {MAX_GROUPS} groups")
    out = []
    for g in groups:
        if not isinstance(g, dict):
            raise ValueError("each group must be an object")
        if g.get("kind") not in KINDS:
            raise ValueError("group.kind must be session or app")
        busy = g.get("busy")
        out.append({"kind": g["kind"], "name": _str(g.get("name") or "?", 60), "role": _str(g.get("role"), 12),
                    "sid": _str(g.get("sid"), 16), "topic": _str(g.get("topic"), 80),
                    "rss": _int(g.get("rss"), "group.rss"), "up_s": _int(g.get("up_s", 0), "group.up_s"),
                    "busy": busy if isinstance(busy, bool) else None, "n": _int(g.get("n", 1), "group.n")})
    out.sort(key=lambda g: -g["rss"])
    rest = body.get("rest") or {}
    if not isinstance(rest, dict):
        raise ValueError("rest must be an object")
    return {"mem": clean_mem, "uptime_s": _int(body.get("uptime_s", 0), "uptime_s"), "groups": out,
            "rest": {"count": _int(rest.get("count", 0), "rest.count"), "rss": _int(rest.get("rss", 0), "rest.rss")},
            "sessions": _int(body.get("sessions", 0), "sessions"),
            "sessions_busy": _int(body.get("sessions_busy", 0), "sessions_busy")}


def record_ram(host: str, report: dict, observed_at: str | None, now: float | None = None,
               data_dir: Path | None = None) -> dict:
    now = time.time() if now is None else now
    d = data_dir or DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    doc = {"host": host, "label": HOSTS[host], "received_at": _iso(now),
           "observed_at": (observed_at or "")[:40] or None, **report}
    tmp = d / f".{host}.ram.tmp"
    tmp.write_text(json.dumps(doc))
    tmp.replace(d / f"{host}.ram.json")
    return doc


def combined_ram(data_dir: Path | None = None, now: float | None = None) -> dict:
    d = data_dir or DATA_DIR
    hosts = []
    for host in HOSTS:
        p = d / f"{host}.ram.json"
        if not p.exists():
            continue
        try:
            hosts.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            continue
    return {"generated_at": _iso(time.time() if now is None else now), "hosts": hosts}


def _is_ram(path: str) -> bool:
    return urlparse(path).path.rstrip("/").endswith("/ram")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        body = (json.dumps(obj) if not isinstance(obj, str) else obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json" if not isinstance(obj, str) else "text/plain")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _query(self) -> dict:
        return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

    def do_GET(self):
        q = self._query()
        if not READ_TOKEN or (q.get("k") or self.headers.get("X-Token", "")) != READ_TOKEN:
            return self._send(401, "unauthorized")
        self._send(200, combined_ram() if _is_ram(self.path) else combined())

    def do_POST(self):
        q = self._query()
        if not PUSH_TOKEN or (q.get("k") or self.headers.get("X-Token", "")) != PUSH_TOKEN:
            return self._send(401, "unauthorized")
        host = q.get("host", "")
        if host not in HOSTS:
            return self._send(400, f"unknown host {host!r}")
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > (MAX_RAM_BODY if _is_ram(self.path) else MAX_BODY):
            return self._send(413, "body missing or too large")
        if _is_ram(self.path):
            try:
                body = json.loads(self.rfile.read(n))
                rep = validate_ram(body if isinstance(body, dict) else {})
            except (json.JSONDecodeError, ValueError) as e:
                return self._send(400, f"bad report: {e}")
            doc = record_ram(host, rep, body.get("observed_at"))
            return self._send(200, {"ok": True, "host": host, "received_at": doc["received_at"]})
        try:
            body = json.loads(self.rfile.read(n))
            vols = validate(body if isinstance(body, dict) else {})
        except (json.JSONDecodeError, ValueError) as e:
            return self._send(400, f"bad report: {e}")
        doc = record(host, vols, body.get("observed_at"))
        sch = doc["schedule"]
        self._send(200, {"ok": True, "host": host, "received_at": doc["received_at"],
                         "next_push_after_s": sch["interval_s"],
                         "force_delta_bytes": sch["force_delta_bytes"], "reason": sch["reason"]})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
