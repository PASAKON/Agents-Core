#!/usr/bin/env python3
"""Bitkub live micro-test — the one experiment paper trading cannot run.

mm_probe.py measured a positive paper edge but the number is close to
tautological: quoting one tick inside a 28 bps spread "captures" 14 bps only if
the quote actually gets to sit at the touch. Whether it does depends on how the
incumbent market maker reacts to a new order appearing inside their spread, and
no amount of read-only data answers that. It has to be posted.

So this posts exactly one tiny resting limit order and measures two things:

    1. Does anybody re-quote inside it, and how many seconds does that take?
    2. Does it fill before that happens?

Then it cancels. That is the whole experiment.

Safety
------
- Dry-run is the default. It signs nothing and sends nothing; it prints the
  order it would place and then watches the book so the measurement still runs.
- --live requires BITKUB_API_KEY and BITKUB_API_SECRET in the environment and
  a typed confirmation phrase. Credentials are never written to disk or logged.
- post_only limit orders only. There is no market-order code path here.
- Notional is capped by MAX_NOTIONAL_USDT regardless of what is passed.
- The order is cancelled on timeout, on Ctrl-C, and on any unhandled error.

Usage:
    python3 mm_live_test.py --pair BTC --side bid              # dry run
    python3 mm_live_test.py --pair BTC --side bid --live       # posts for real
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

HOST = "https://api.bitkub.com"
API = f"{HOST}/api/v3/market"

# Nothing in this script may risk more than pocket change.
MAX_NOTIONAL_USDT = 20.0
DEFAULT_NOTIONAL_USDT = 6.0     # Bitkub min_quote_size for USDT pairs
REQUEST_TIMEOUT = 10


# --------------------------------------------------------------------------
# public endpoints
# --------------------------------------------------------------------------

def get_public(path: str):
    req = urllib.request.Request(f"{API}/{path}",
                                 headers={"User-Agent": "bitkub-live-test/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def symbol_meta(coin: str) -> dict:
    for s in get_public("symbols")["result"]:
        if s["symbol"] == f"{coin}_USDT" and s["status"] == "active":
            return s
    raise SystemExit(f"no active {coin}_USDT pair")


def touch(symbol: str) -> tuple[float, float]:
    book = get_public(f"depth?sym={symbol.lower()}&lmt=1")["result"]
    return float(book["bids"][0][0]), float(book["asks"][0][0])


# --------------------------------------------------------------------------
# signed endpoints — only reached with --live
# --------------------------------------------------------------------------

class Client:
    """Minimal signed client. Instantiated only when --live is confirmed."""

    def __init__(self, key: str, secret: str):
        self._key = key
        self._secret = secret.encode()

    def _send(self, method: str, path: str, query: str = "", payload: dict | None = None) -> dict:
        body = json.dumps(payload) if payload is not None else ""
        ts = str(int(time.time() * 1000))
        # Bitkub v3: HMAC-SHA256 over timestamp + method + path + query/body, hex.
        suffix = f"?{query}" if query else body
        sign = hmac.new(self._secret, f"{ts}{method}{path}{suffix}".encode(),
                        hashlib.sha256).hexdigest()
        url = f"{HOST}{path}" + (f"?{query}" if query else "")
        headers = {
            "Accept": "application/json",
            "X-BTK-APIKEY": self._key,
            "X-BTK-TIMESTAMP": ts,
            "X-BTK-SIGN": sign,
        }
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = body.encode()
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            out = json.loads(resp.read().decode())
        if out.get("error"):
            raise RuntimeError(f"bitkub error {out['error']} on {path}")
        return out

    def place(self, symbol: str, side: str, amount: float, rate: float) -> str:
        path = "/api/v3/market/place-bid" if side == "bid" else "/api/v3/market/place-ask"
        out = self._send("POST", path, payload={
            "sym": symbol, "amt": amount, "rat": rate,
            "typ": "limit", "post_only": True,
        })
        return str(out["result"]["id"])

    def cancel(self, symbol: str, order_id: str, side: str) -> None:
        self._send("POST", "/api/v3/market/cancel-order",
                   payload={"sym": symbol, "id": order_id, "sd": side})

    def is_open(self, symbol: str, order_id: str) -> bool:
        out = self._send("GET", "/api/v3/market/my-open-orders", query=f"sym={symbol}")
        return any(str(o.get("id")) == order_id for o in out.get("result", []))


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------

def watch(symbol: str, side: str, my_price: float, seconds: float,
          client: Client | None, order_id: str | None) -> dict:
    """Poll the touch until someone quotes inside us, we fill, or time runs out."""
    started = time.time()
    undercut_at = None
    filled = False

    # Seed the tape before the clock starts. Everything already printed happened
    # before this quote existed and must never be counted as a fill.
    seen: set[tuple] = set()
    if not client:
        try:
            seen = {tuple(t) for t in get_public(f"trades?sym={symbol.lower()}&lmt=50")["result"]}
        except (urllib.error.URLError, TimeoutError, KeyError):
            pass

    while time.time() - started < seconds:
        elapsed = time.time() - started
        try:
            bid, ask = touch(symbol)
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError):
            time.sleep(1.0)
            continue

        inside = bid > my_price if side == "bid" else ask < my_price
        if inside and undercut_at is None:
            undercut_at = elapsed
            who = f"bid {bid}" if side == "bid" else f"ask {ask}"
            print(f"  [{elapsed:6.1f}s] UNDERCUT — someone quoted inside at {who}")

        if client and order_id:
            try:
                if not client.is_open(symbol, order_id):
                    filled = True
                    print(f"  [{elapsed:6.1f}s] order no longer open — filled or cancelled")
                    break
            except (urllib.error.URLError, TimeoutError, RuntimeError):
                pass
        else:
            # Dry run: infer a would-be fill from the tape crossing our price.
            try:
                for entry in get_public(f"trades?sym={symbol.lower()}&lmt=50")["result"]:
                    key = tuple(entry)
                    if key in seen:
                        continue
                    seen.add(key)
                    price, tside = float(entry[1]), entry[3]
                    hit = (tside == "SELL" and price <= my_price) if side == "bid" \
                        else (tside == "BUY" and price >= my_price)
                    if hit:
                        filled = True
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError):
                pass
            if filled:
                print(f"  [{elapsed:6.1f}s] tape crossed our price — would have filled")
                break

        status = "UNDERCUT" if undercut_at is not None else "at touch"
        print(f"  [{elapsed:6.1f}s] bid {bid:<12} ask {ask:<12} ours {my_price:<12} {status}")
        time.sleep(1.0)

    return {
        "undercut_after_sec": None if undercut_at is None else round(undercut_at, 1),
        "filled": filled,
        "elapsed_sec": round(time.time() - started, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="BTC", help="base asset of a USDT pair (default BTC)")
    ap.add_argument("--side", choices=["bid", "ask"], default="bid")
    ap.add_argument("--notional", type=float, default=DEFAULT_NOTIONAL_USDT,
                    help=f"USDT notional (default {DEFAULT_NOTIONAL_USDT}, hard cap {MAX_NOTIONAL_USDT})")
    ap.add_argument("--seconds", type=float, default=60.0, help="how long to rest (default 60)")
    ap.add_argument("--live", action="store_true", help="actually post the order")
    ap.add_argument("--log", default="output/bitkub-arb")
    args = ap.parse_args()

    sys.stdout.reconfigure(line_buffering=True)

    if args.notional > MAX_NOTIONAL_USDT:
        print(f"notional capped at {MAX_NOTIONAL_USDT} USDT by this script", file=sys.stderr)
        return 1

    coin = args.pair.upper()
    meta = symbol_meta(coin)
    symbol = meta["symbol"]
    tick = float(meta["price_step"])
    if args.notional < float(meta["min_quote_size"]):
        print(f"{symbol} minimum is {meta['min_quote_size']} USDT", file=sys.stderr)
        return 1

    bid, ask = touch(symbol)
    mid = (bid + ask) / 2
    spread_bps = (ask - bid) / mid * 10_000
    my_price = round(bid + tick, meta["price_scale"]) if args.side == "bid" \
        else round(ask - tick, meta["price_scale"])
    qty = args.notional / my_price

    print(f"\n  pair          {symbol}")
    print(f"  book          bid {bid}  ask {ask}   spread {spread_bps:.1f} bps")
    print(f"  our {args.side:<10}{my_price}   ({args.notional} USDT = {qty:.8f} {coin})")
    print(f"  rest for      {args.seconds:.0f}s, post_only limit\n")

    client = None
    order_id = None
    if args.live:
        key, secret = os.environ.get("BITKUB_API_KEY"), os.environ.get("BITKUB_API_SECRET")
        if not key or not secret:
            print("set BITKUB_API_KEY and BITKUB_API_SECRET to run --live", file=sys.stderr)
            return 1
        print("  LIVE MODE — this posts a real order with real money.")
        if input('  type "POST" to confirm: ').strip() != "POST":
            print("  aborted")
            return 1
        client = Client(key, secret)
        order_id = client.place(symbol, args.side, args.notional, my_price)
        print(f"  posted, order id {order_id}\n")
    else:
        print("  DRY RUN — nothing sent. Watching the book to measure undercut time.")
        print("  (add --live, with API keys in env, to post it for real)\n")

    try:
        result = watch(symbol, args.side, my_price, args.seconds, client, order_id)
    finally:
        if client and order_id:
            try:
                client.cancel(symbol, order_id, args.side)
                print(f"\n  cancelled order {order_id}")
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                print(f"\n  CANCEL FAILED ({exc}) — check open orders manually", file=sys.stderr)

    print("\n  --- result ---")
    print(f"  would-be fill: {result['filled']}   (watched {result['elapsed_sec']:.0f}s)")
    if not args.live:
        # No order existed, so nobody could react to one. Saying "nobody
        # undercut us" here would be measuring the absence of our own quote.
        print("  undercut time: NOT MEASURABLE in dry run — no order was on the book,")
        print("                 so there was nothing for anyone to quote inside of.")
        print("  -> plumbing verified. The actual question needs --live.")
    elif result["undercut_after_sec"] is None:
        print(f"  nobody quoted inside us for {result['elapsed_sec']:.0f}s")
        print("  -> the touch is defendable. Market making is worth a bigger test.")
    else:
        print(f"  undercut after {result['undercut_after_sec']:.1f}s")
        print("  -> an incumbent reprices on top of you. The 14 bps paper edge is not")
        print("     reachable; you would be in a penny-jump war, not collecting spread.")

    row = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "live" if args.live else "dry",
        "symbol": symbol, "side": args.side, "my_price": my_price,
        "notional_usdt": args.notional, "spread_bps": round(spread_bps, 1),
        "touch_before": [bid, ask], **result,
    }
    logdir = pathlib.Path(args.log)
    logdir.mkdir(parents=True, exist_ok=True)
    logpath = logdir / f"live-test-{dt.date.today():%Y%m%d}.jsonl"
    with logpath.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(f"\n  logged to {logpath}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  interrupted")
        raise SystemExit(130)
