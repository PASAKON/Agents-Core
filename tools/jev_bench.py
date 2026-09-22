#!/usr/bin/env python3
"""jev_bench.py -- is Jev fast enough to play Cookie Run, and what would it cost?

The CEO's question (2026-09-22), in his words: fire it for real, time how long it
thinks, can it keep up in realtime, and what does a full non-stop day cost, to
the last decimal.

Nothing here is estimated if it can be measured. Latency is wall-clock around
the HTTP call; cost is `usage.cost` as the provider reports it, never the price
table. Where a figure has to be DERIVED (winbox's end-to-end latency, from two
separately measured legs) it is labelled as derived.

Three modes, because "how long does it take" has three honest answers:

  fresh      a new TCP+TLS connection per call -- what tools/decide.py does today
  keepalive  one reused connection -- the best a realtime loop could ever get
  network    NO key, NO model: an unauthenticated POST the edge rejects. Measures
             only the wire. Run this one on winbox, where the bot actually lives,
             without moving a secret onto that machine.

    python tools/jev_bench.py --mode keepalive --n 25
    python tools/jev_bench.py --mode network  --n 25        # safe anywhere, costs $0
"""
import argparse
import json
import os
import statistics as st
import sys
import time
from pathlib import Path

import requests

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"
PRICE_IN_PER_MTOK = 0.042          # config/decisions/_providers.yaml, measured 2026-09-22
MAX_CALLS = 200                    # hard ceiling: a typo in --n must not become a bill

# What the eyes would hand the brain. Our trained vision model sees the frame;
# this is the SMALLEST text that carries what it saw -- the decision-layer spec's
# rule is that state size is where the cost lives, so nothing decorative goes in.
# Three variants so a cached answer cannot flatter the latency.
STATES = [
    "cookie: on ground, not in air. next obstacle: low spike 210px ahead. "
    "after that: high bar 480px ahead. scroll speed: 880 px/s.",
    "cookie: in air, falling. next obstacle: pit 140px ahead, width 90px. "
    "after that: none within 600px. scroll speed: 880 px/s.",
    "cookie: on ground. next obstacle: high bar 95px ahead (clearance too low to "
    "jump under). after that: low spike 330px ahead. scroll speed: 910 px/s.",
]
QUESTION = "Which control should the cookie press right now?"
OPTIONS = {
    "jump": "Press jump now: an obstacle at ground level is close enough to hit.",
    "slide": "Press slide now: an overhead obstacle is close enough to hit.",
    "double_jump": "Jump again while airborne: a pit or tall obstacle needs more height.",
    "none": "Press nothing: no obstacle is close enough to need a response yet.",
}


def load_key(env_file: str | None) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    if env_file and Path(env_file).exists():
        for line in Path(env_file).read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def payload(i: int) -> dict:
    return {"model": MODEL, "state": STATES[i % len(STATES)],
            "questions": {"control": {"type": "choice", "instructions": QUESTION,
                                      "criteria": OPTIONS}}}


def stats(ms: list[float]) -> dict:
    s = sorted(ms)
    pick = lambda q: s[min(len(s) - 1, int(round(q * (len(s) - 1))))]
    return {"n": len(s), "min": round(s[0], 1), "p50": round(st.median(s), 1),
            "p90": round(pick(0.90), 1), "p99": round(pick(0.99), 1),
            "max": round(s[-1], 1), "mean": round(st.mean(s), 1)}


def run(mode: str, n: int, key: str) -> dict:
    sess = requests.Session() if mode in ("keepalive", "network") else None
    headers = {} if mode == "network" else {"Authorization": f"Bearer {key}"}
    post = (sess.post if sess else requests.post)

    if sess:
        # Warm the connection and discard it: the first call pays TCP+TLS setup,
        # which a long-running loop pays once, not per decision.
        try:
            post(URL, headers=headers, json=payload(0), timeout=20)
        except requests.RequestException:
            pass

    lat, rows = [], []
    for i in range(n):
        t0 = time.perf_counter()
        r = post(URL, headers=headers, json=payload(i), timeout=20)
        ms = (time.perf_counter() - t0) * 1000
        lat.append(ms)
        row = {"i": i, "ms": round(ms, 1), "http": r.status_code}
        if mode != "network" and r.status_code == 200:
            d = r.json()
            a = (d.get("answers") or {}).get("control") or {}
            u = d.get("usage") or {}
            row.update(choice=a.get("choice"), confidence=a.get("confidence"),
                       tokens_in=u.get("input_tokens"), tokens_out=u.get("output_tokens"),
                       cost=u.get("cost"))
        elif mode != "network":
            row["error"] = r.text[:200]
        rows.append(row)

    out = {"mode": mode, "latency_ms": stats(lat), "calls": rows}
    if mode != "network":
        ok = [r for r in rows if r.get("cost") is not None]
        if ok:
            costs = [float(r["cost"]) for r in ok]
            tin = [int(r["tokens_in"]) for r in ok if r.get("tokens_in") is not None]
            out["cost_usd"] = {"total": sum(costs), "per_call_mean": st.mean(costs),
                               "per_call_min": min(costs), "per_call_max": max(costs)}
            out["tokens_in_mean"] = st.mean(tin) if tin else None
            out["answered"] = len(ok)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fresh", "keepalive", "network"], required=True)
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--env-file", default="/home/secretary/.secretary.env")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.n > MAX_CALLS:
        print(f"refusing --n {a.n}: ceiling is {MAX_CALLS}")
        return 2
    key = "" if a.mode == "network" else load_key(a.env_file)
    if a.mode != "network" and not key:
        print("no OPENROUTER_API_KEY in env or --env-file")
        return 2
    if a.mode != "network":
        # Say the worst case BEFORE spending it. ~250 input tokens is the schema
        # plus the state; output is free.
        worst = (a.n + 1) * 400 / 1e6 * PRICE_IN_PER_MTOK
        print(f"about to make {a.n + (1 if a.mode == 'keepalive' else 0)} paid calls; "
              f"worst case ${worst:.8f}", flush=True)

    res = run(a.mode, a.n, key)
    L = res["latency_ms"]
    print(f"{a.mode:<10} n={L['n']}  min {L['min']}  p50 {L['p50']}  p90 {L['p90']}  "
          f"p99 {L['p99']}  max {L['max']}  mean {L['mean']}  (ms)")
    if "cost_usd" in res:
        c = res["cost_usd"]
        print(f"           answered {res['answered']}/{L['n']}  tokens_in mean "
              f"{res['tokens_in_mean']:.1f}  cost/call ${c['per_call_mean']:.10f}  "
              f"total ${c['total']:.10f}")
        choices = [r.get("choice") for r in res["calls"]]
        print(f"           choices: {choices}")
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
