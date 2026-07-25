#!/usr/bin/env python3
"""Bitkub fee-sensitivity matrix — does a cheaper fee actually change the answer?

Runs the same passive market-making simulation on BOTH books of each coin, on
live spreads and live prices, then prices the identical fills under every fee
assumption that exists on this exchange:

    THB pair     0.25% cash          the published rate
                 0.25% x KUB/33      the rate if fees are paid with fee credit
                                     bought by converting KUB (30 floor + 10%)

    USDT pair    0%                  promo, until 12 Aug 2026
                 0.1%                the rate that returns after that

Fee credit is redeemable ONLY against THB pairs. Running both markets side by
side is therefore the direct test of whether buying fee credit is worth doing:
if the THB book is too tight to make markets in, a cheaper fee on it is a
discount on an activity you cannot profitably perform.

Fill model matches mm_probe: quote one tick inside the touch, staged one poll
ahead so it can never match trades that already printed, and retired once it
trades. Everything is converted to THB so the two markets are comparable.

Read-only: public endpoints, no API key, no order path.

Usage:
    python3 fee_matrix.py --pairs BTC,ETH,SOL --minutes 10
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

API = "https://api.bitkub.com/api/v3/market"

THB_FEE = 0.0025           # published rate on THB pairs, charged in THB
USDT_FEE_PROMO = 0.0       # USDT pairs, 14 Jul - 12 Aug 2026
USDT_FEE_AFTER = 0.001     # USDT pairs after the promo
CREDIT_PER_KUB = 33.0      # 30 THB floor + 10% bonus tier

REQUEST_TIMEOUT = 10
SLEEP = 0.1


def get_json(path: str):
    req = urllib.request.Request(f"{API}/{path}",
                                 headers={"User-Agent": "bitkub-fee-matrix/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def symbols() -> dict[str, dict]:
    return {s["symbol"]: s for s in get_json("symbols")["result"] if s["status"] == "active"}


def last_price(symbol: str) -> float | None:
    try:
        return float(get_json(f"ticker?sym={symbol.lower()}")[0]["last"])
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError):
        return None


class Sim:
    """Passive two-sided quote on one book."""

    def __init__(self, symbol: str, tick: float, scale: int, notional_thb: float,
                 quote_is_thb: bool):
        self.symbol = symbol
        self.tick = tick
        self.scale = scale
        self.notional_thb = notional_thb
        self.quote_is_thb = quote_is_thb   # True for COIN_THB, False for COIN_USDT
        self.live_bid: float | None = None
        self.live_ask: float | None = None
        self.seen: set[tuple] = set()
        self.seeded = False
        self.spreads: list[float] = []
        self.fills = 0
        self.volume_quote = 0.0     # notional traded, in the pair's quote currency
        self.pnl_quote = 0.0        # gross P&L before fees, quote currency
        self.inventory = 0.0
        self.peak_inventory = 0.0
        self.last_mid = 0.0

    def step(self, usdt_thb: float) -> None:
        try:
            book = get_json(f"depth?sym={self.symbol.lower()}&lmt=1")["result"]
            bid, ask = float(book["bids"][0][0]), float(book["asks"][0][0])
            time.sleep(SLEEP)
            tape = get_json(f"trades?sym={self.symbol.lower()}&lmt=50")["result"]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
                KeyError, IndexError, ValueError):
            return

        mid = (bid + ask) / 2
        self.spreads.append((ask - bid) / mid * 10_000)

        # One unit of the quote currency, expressed in THB.
        quote_thb = 1.0 if self.quote_is_thb else usdt_thb
        qty = (self.notional_thb / quote_thb) / mid

        for entry in tape:
            key = tuple(entry)
            if key in self.seen:
                continue
            self.seen.add(key)
            if not self.seeded:
                continue
            price, size, side = float(entry[1]), float(entry[2]), entry[3]
            filled = min(size, qty)
            if side == "SELL" and self.live_bid is not None and price <= self.live_bid:
                self.pnl_quote -= self.live_bid * filled
                self.inventory += filled
                self.volume_quote += self.live_bid * filled
                self.fills += 1
                self.live_bid = None
            elif side == "BUY" and self.live_ask is not None and price >= self.live_ask:
                self.pnl_quote += self.live_ask * filled
                self.inventory -= filled
                self.volume_quote += self.live_ask * filled
                self.fills += 1
                self.live_ask = None
        self.seeded = True
        self.peak_inventory = max(self.peak_inventory, abs(self.inventory) * mid)

        my_bid, my_ask = round(bid + self.tick, self.scale), round(ask - self.tick, self.scale)
        if my_bid < my_ask:
            self.live_bid, self.live_ask = my_bid, my_ask
        else:
            self.live_bid = self.live_ask = None
        self.last_mid = mid

    def result(self, usdt_thb: float, fees: dict[str, float]) -> dict:
        quote_thb = 1.0 if self.quote_is_thb else usdt_thb
        gross_quote = self.pnl_quote + self.inventory * self.last_mid
        gross_thb = gross_quote * quote_thb
        volume_thb = self.volume_quote * quote_thb
        spread = sorted(self.spreads)[len(self.spreads) // 2] if self.spreads else None
        return {
            "symbol": self.symbol,
            "market": "thb" if self.quote_is_thb else "usdt",
            "spread_bps": round(spread, 2) if spread is not None else None,
            "fills": self.fills,
            "volume_thb": round(volume_thb, 2),
            # Capital reality check. Peak inventory is the position the strategy
            # would actually have had to fund and carry; gross P&L above marks it
            # to mid, so a large number means the profit is unrealised and at risk.
            "end_inventory_thb": round(self.inventory * self.last_mid * quote_thb, 2),
            "peak_inventory_thb": round(self.peak_inventory * quote_thb, 2),
            "gross_pnl_thb": round(gross_thb, 4),
            "net_pnl_thb": {name: round(gross_thb - volume_thb * rate, 4)
                            for name, rate in fees.items()},
        }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default="BTC,ETH,SOL,XRP")
    ap.add_argument("--minutes", type=float, default=10.0)
    ap.add_argument("--notional-thb", type=float, default=1000.0,
                    help="THB quoted per side, same on both books (default 1000)")
    ap.add_argument("--log", default="output/bitkub-arb")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    meta = symbols()
    usdt_thb = last_price("USDT_THB")
    kub = last_price("KUB_THB")
    if not usdt_thb or not kub:
        print("cannot read USDT_THB / KUB_THB reference prices", file=sys.stderr)
        return 1

    credit_rate = THB_FEE * (kub / CREDIT_PER_KUB)
    thb_fees = {"cash 0.25%": THB_FEE, f"credit {credit_rate * 100:.3f}%": credit_rate}
    usdt_fees = {"promo 0%": USDT_FEE_PROMO, "after 0.1%": USDT_FEE_AFTER}

    print(f"\n  live refs: USDT/THB {usdt_thb}   KUB/THB {kub}")
    print(f"  fee credit costs {kub:.2f}/{CREDIT_PER_KUB:.0f} = "
          f"{kub / CREDIT_PER_KUB:.4f} THB per THB of credit")
    print(f"  -> THB-pair fee {THB_FEE * 100:.2f}% cash  vs  {credit_rate * 100:.3f}% on credit "
          f"({(1 - credit_rate / THB_FEE) * 100:.1f}% cheaper)")
    print("  -> fee credit does NOT apply to USDT pairs (THB market only)\n")

    sims = []
    for coin in (c.strip().upper() for c in args.pairs.split(",")):
        for quote in ("THB", "USDT"):
            sym = f"{coin}_{quote}"
            if sym not in meta:
                continue
            m = meta[sym]
            sims.append(Sim(sym, float(m["price_step"]), m["price_scale"],
                            args.notional_thb, quote == "THB"))
    print(f"  simulating {len(sims)} books, {args.notional_thb:,.0f} THB/side, "
          f"{args.minutes:g} min\n")

    deadline = time.time() + args.minutes * 60
    while time.time() < deadline:
        for s in sims:
            s.step(usdt_thb)

    rows = [s.result(usdt_thb, thb_fees if s.quote_is_thb else usdt_fees) for s in sims]

    print(f"  {'book':<12}{'spread':>9}{'fills':>7}{'volume':>12}{'peak inv':>11}{'gross':>9}"
          "   net (fee scenario)")
    print(f"  {'':<12}{'bps':>9}{'':>7}{'THB':>12}{'THB':>11}{'THB':>9}")
    print(f"  {'-' * 92}")
    for r in rows:
        nets = "   ".join(f"{k}: {v:+.2f}" for k, v in r["net_pnl_thb"].items())
        sp = "       --" if r["spread_bps"] is None else f"{r['spread_bps']:9.1f}"
        print(f"  {r['symbol']:<12}{sp}{r['fills']:>7}{r['volume_thb']:>12,.0f}"
              f"{r['peak_inventory_thb']:>11,.0f}{r['gross_pnl_thb']:>9.2f}   {nets}")

    thb_rows = [r for r in rows if r["market"] == "thb"]
    usdt_rows = [r for r in rows if r["market"] == "usdt"]
    print("\n  --- what the fee discount is worth ---")
    if thb_rows:
        cash = sum(list(r["net_pnl_thb"].values())[0] for r in thb_rows)
        cred = sum(list(r["net_pnl_thb"].values())[1] for r in thb_rows)
        vol = sum(r["volume_thb"] for r in thb_rows)
        print(f"  THB books : {vol:,.0f} THB traded  ->  cash {cash:+.2f}  credit {cred:+.2f}"
              f"   (fee credit adds {cred - cash:+.2f} THB)")
        if cash < 0 and cred < 0:
            print("              both negative: the discount is on an activity that loses money")
    if usdt_rows:
        promo = sum(list(r["net_pnl_thb"].values())[0] for r in usdt_rows)
        after = sum(list(r["net_pnl_thb"].values())[1] for r in usdt_rows)
        vol = sum(r["volume_thb"] for r in usdt_rows)
        print(f"  USDT books: {vol:,.0f} THB traded  ->  promo {promo:+.2f}  after {after:+.2f}"
              f"   (12 Aug cliff costs {after - promo:+.2f} THB)")
        print("              fee credit cannot be used here at any price")

    logdir = pathlib.Path(args.log)
    logdir.mkdir(parents=True, exist_ok=True)
    logpath = logdir / f"fee-matrix-{dt.date.today():%Y%m%d}.jsonl"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with logpath.open("a") as fh:
        for r in rows:
            fh.write(json.dumps({"ts": stamp, "usdt_thb": usdt_thb, "kub_thb": kub, **r}) + "\n")
    print(f"\n  logged to {logpath}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  interrupted")
        raise SystemExit(130)
