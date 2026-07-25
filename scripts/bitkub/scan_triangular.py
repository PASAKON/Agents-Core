#!/usr/bin/env python3
"""Bitkub triangular arbitrage scanner — read-only.

Walks the real order books for every coin listed against BOTH THB and USDT and
computes the executable round-trip return for both triangle directions:

    Loop A:  THB -> USDT -> COIN -> THB
    Loop B:  THB -> COIN -> USDT -> THB

Every number is a size-aware VWAP walk through actual depth, not top-of-book,
so the printed edge is what an order of --notional would really receive.

Read-only by construction: hits only public endpoints, needs no API key, and
has no code path that places, cancels, or signs an order.

Usage:
    python3 scan_triangular.py                     # one pass, 10,000 THB
    python3 scan_triangular.py --notional 50000    # size the walk differently
    python3 scan_triangular.py --watch 5           # poll every 5s until Ctrl-C
    python3 scan_triangular.py --fee-mode credit   # price THB legs via fee credit
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

# Bitkub fee schedule, verified 2026-07-25 from the official Trading Fees page.
THB_FEE = 0.0025          # 0.25% on every THB-quoted pair, charged in THB
USDT_FEE_PROMO = 0.0      # 0% on USDT pairs, 14 Jul 2026 - 12 Aug 2026
USDT_FEE_NORMAL = 0.001   # 0.1% once the promo lapses
USDT_PROMO_ENDS = dt.date(2026, 8, 12)

# Fee-credit economics. Converting KUB yields a 30 THB/KUB floor + 10% bonus, so
# one baht of fee credit costs (KUB market price / 33) baht of real money.
# Fee credit is redeemable ONLY against THB-quoted pairs.
CREDIT_PER_KUB = 33.0

REQUEST_TIMEOUT = 10


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "bitkub-arb-scan/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def dual_listed_coins() -> list[str]:
    """Coins quoted against both THB and USDT — the only triangles that exist."""
    symbols = get_json(f"{API}/symbols")["result"]
    active = {s["symbol"] for s in symbols if s["status"] == "active"}
    coins = []
    for sym in sorted(active):
        base, _, quote = sym.partition("_")
        if quote == "USDT" and f"{base}_THB" in active:
            coins.append(base)
    return coins


def depth(sym: str, limit: int = 50) -> dict:
    """Order book. Levels are [price, base_asset_quantity]."""
    return get_json(f"{API}/depth?sym={sym.lower()}&lmt={limit}")["result"]


def spend_quote(asks: list, quote_amount: float) -> float | None:
    """Market-buy: spend `quote_amount` of quote currency, return base received.

    Returns None when the visible book cannot absorb the order.
    """
    base_out = 0.0
    remaining = quote_amount
    for price, base_qty in asks:
        level_cost = price * base_qty
        if remaining <= level_cost:
            base_out += remaining / price
            return base_out
        base_out += base_qty
        remaining -= level_cost
    return None


def sell_base(bids: list, base_amount: float) -> float | None:
    """Market-sell: sell `base_amount` of base asset, return quote received."""
    quote_out = 0.0
    remaining = base_amount
    for price, base_qty in bids:
        if remaining <= base_qty:
            quote_out += remaining * price
            return quote_out
        quote_out += base_qty * price
        remaining -= base_qty
    return None


def thb_fee_rate(mode: str, kub_price: float | None) -> tuple[float, str]:
    """Effective cash cost of a THB-pair fee under the chosen payment method."""
    if mode == "credit":
        if not kub_price:
            raise SystemExit("credit mode needs a live KUB price")
        rate = THB_FEE * (kub_price / CREDIT_PER_KUB)
        return rate, f"credit @ KUB {kub_price:.2f} -> {rate * 100:.4f}%"
    return THB_FEE, f"cash {THB_FEE * 100:.2f}%"


def usdt_fee_rate(today: dt.date) -> tuple[float, str]:
    if today <= USDT_PROMO_ENDS:
        return USDT_FEE_PROMO, "0% promo (ends 12 Aug 2026)"
    return USDT_FEE_NORMAL, f"{USDT_FEE_NORMAL * 100:.2f}%"


def run_loop_a(books: dict, coin: str, thb_in: float, f_thb: float, f_usdt: float):
    """THB -> USDT -> COIN -> THB."""
    usdt = spend_quote(books["USDT_THB"]["asks"], thb_in * (1 - f_thb))
    if usdt is None:
        return None
    coin_qty = spend_quote(books[f"{coin}_USDT"]["asks"], usdt)
    if coin_qty is None:
        return None
    coin_qty *= 1 - f_usdt  # USDT-pair fees are taken from the asset received
    thb_out = sell_base(books[f"{coin}_THB"]["bids"], coin_qty)
    if thb_out is None:
        return None
    return thb_out * (1 - f_thb)


def run_loop_b(books: dict, coin: str, thb_in: float, f_thb: float, f_usdt: float):
    """THB -> COIN -> USDT -> THB."""
    coin_qty = spend_quote(books[f"{coin}_THB"]["asks"], thb_in * (1 - f_thb))
    if coin_qty is None:
        return None
    usdt = sell_base(books[f"{coin}_USDT"]["bids"], coin_qty)
    if usdt is None:
        return None
    usdt *= 1 - f_usdt
    thb_out = sell_base(books["USDT_THB"]["bids"], usdt)
    if thb_out is None:
        return None
    return thb_out * (1 - f_thb)


def scan_once(coins: list[str], notional: float, fee_mode: str, logfile) -> list[dict]:
    today = dt.datetime.now(dt.timezone.utc).date()
    f_usdt, usdt_label = usdt_fee_rate(today)

    kub_price = None
    if fee_mode == "credit":
        kub_price = float(get_json(f"{API}/ticker?sym=kub_thb")[0]["last"])
    f_thb, thb_label = thb_fee_rate(fee_mode, kub_price)

    books = {"USDT_THB": depth("USDT_THB")}
    for coin in coins:
        books[f"{coin}_THB"] = depth(f"{coin}_THB")
        books[f"{coin}_USDT"] = depth(f"{coin}_USDT")

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for coin in coins:
        for name, fn in (("A", run_loop_a), ("B", run_loop_b)):
            net = fn(books, coin, notional, f_thb, f_usdt)
            gross = fn(books, coin, notional, 0.0, 0.0)
            rows.append({
                "ts": ts,
                "coin": coin,
                "loop": "A_thb_usdt_coin" if name == "A" else "B_thb_coin_usdt",
                "notional_thb": notional,
                "gross_pct": None if gross is None else (gross / notional - 1) * 100,
                "net_pct": None if net is None else (net / notional - 1) * 100,
                "fee_model": f"thb={thb_label} usdt={usdt_label}",
            })
    if logfile:
        for row in rows:
            logfile.write(json.dumps(row) + "\n")
        logfile.flush()

    print(f"\n  {ts}   notional {notional:,.0f} THB")
    print(f"  fees: THB leg {thb_label}  |  USDT leg {usdt_label}")
    print(f"  {'coin':<6} {'loop':<6} {'gross %':>10} {'net %':>10}   verdict")
    print(f"  {'-' * 52}")
    for row in sorted(rows, key=lambda r: -(r["net_pct"] if r["net_pct"] is not None else -99)):
        g = "  thin book" if row["gross_pct"] is None else f"{row['gross_pct']:+10.4f}"
        if row["net_pct"] is None:
            n, verdict = "  thin book", ""
        else:
            n = f"{row['net_pct']:+10.4f}"
            verdict = "PROFIT" if row["net_pct"] > 0 else ""
        print(f"  {row['coin']:<6} {row['loop'][0]:<6} {g} {n}   {verdict}")

    live = [r["net_pct"] for r in rows if r["net_pct"] is not None]
    if live:
        best = max(live)
        print(f"\n  best net edge: {best:+.4f}%", end="")
        print("  -> NO TRADE" if best <= 0 else f"  -> {best / 100 * notional:+,.2f} THB per cycle")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--notional", type=float, default=10_000, help="THB per cycle (default 10000)")
    ap.add_argument("--watch", type=float, metavar="SEC", help="poll forever every SEC seconds")
    ap.add_argument("--fee-mode", choices=["cash", "credit"], default="cash",
                    help="how THB-pair fees are paid (default cash)")
    ap.add_argument("--log", default="output/bitkub-arb", help="JSONL output directory")
    args = ap.parse_args()

    try:
        coins = dual_listed_coins()
    except urllib.error.URLError as exc:
        print(f"cannot reach Bitkub API: {exc}", file=sys.stderr)
        return 1
    print(f"dual-listed coins ({len(coins)}): {', '.join(coins)}")

    logdir = pathlib.Path(args.log)
    logdir.mkdir(parents=True, exist_ok=True)
    logpath = logdir / f"scan-{dt.date.today():%Y%m%d}.jsonl"

    with logpath.open("a") as logfile:
        try:
            while True:
                scan_once(coins, args.notional, args.fee_mode, logfile)
                if not args.watch:
                    break
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nstopped")
    print(f"\nlogged to {logpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
