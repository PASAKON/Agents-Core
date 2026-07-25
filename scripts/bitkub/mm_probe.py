#!/usr/bin/env python3
"""Bitkub market-making probe — paper only, read-only.

Phase 0 of the MM plan: measure whether posting a passive two-sided quote on
Bitkub's USDT books would actually earn money, WITHOUT risking capital.

Model
-----
Each poll it reads the book and the trade tape, then simulates a quote posted
one tick inside the touch:

    my_bid = best_bid + tick        my_ask = best_ask - tick

One tick inside means the quote sits alone at the front of the queue, so fill
detection needs no queue-position guesswork: any SELL print at or below my_bid
would have hit me, any BUY print at or above my_ask would have lifted me.

Causality matters more than any of that. A quote computed from poll N's book
is only allowed to fill against trades that arrive in poll N+1 and later. The
first version of this probe priced a quote off the current book and then
matched it against trades that had ALREADY happened, which is look-ahead bias:
it silently kept only the fills that survived the move and reported adverse
selection of roughly zero. Quotes are therefore staged one poll ahead, and a
filled side is retired until the next repost, which is also what a real
maker faces after a fill.

Scoring a fill needs a price you can trust, and the USDT book's own mid is not
one. Those books are wide and stale — quotes sit unchanged for minutes, so mid
drift measures ~0 for every pair and every horizon, which reads as "no adverse
selection" when it really means "no signal". The liquid reference lives on the
THB side of the same exchange (BTC_THB quotes to a satang), so fair value is
synthesised from the tight books:

    fair(COIN/USDT) = mid(COIN_THB) / mid(USDT_THB)

The headline number is therefore how good the fill was against fair value at
the moment it happened:

    buy  filled at P  ->  edge_bps = (fair - P) / fair * 10_000
    sell filled at P  ->  edge_bps = (P - fair) / fair * 10_000

Positive means the passive quote bought below, or sold above, what the coin was
actually worth. Mid drift over `--horizon` is still tracked as a secondary
column, but it is diagnostic only, never the decision input.

Known upper-bound bias that remains: a multi-second poll cannot resolve queue
dynamics on a book that trades many times per minute, and it assumes the quote
is never queue-jumped. Treat a positive edge here as "worth a live micro test",
never as a realised return.

P&L is marked to mid and shown twice: at today's 0% USDT maker fee, and at the
0.1% that returns after the promo ends 12 Aug 2026.

Read-only by construction: public endpoints only, no API key, no order path.

Usage:
    python3 mm_probe.py                              # all pairs, 3s poll
    python3 mm_probe.py --pairs BTC,ETH --poll 2
    python3 mm_probe.py --quote-usdt 50 --horizon 60
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import signal
import statistics
import sys
import time
import urllib.error
import urllib.request

API = "https://api.bitkub.com/api/v3/market"

USDT_FEE_PROMO = 0.0      # 0% on USDT pairs through 12 Aug 2026
USDT_FEE_AFTER = 0.001    # 0.1% once the promo lapses
USDT_PROMO_ENDS = dt.date(2026, 8, 12)

REQUEST_TIMEOUT = 10
INTER_REQUEST_SLEEP = 0.12   # keep depth calls under the 10 req/s ceiling
TRADE_MEMORY = 400           # dedupe window for tape entries


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "bitkub-mm-probe/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def book_mid(symbol: str) -> float | None:
    """Top-of-book mid, or None if the book or the request is unusable."""
    try:
        book = get_json(f"{API}/depth?sym={symbol.lower()}&lmt=1")["result"]
        mid = (float(book["bids"][0][0]) + float(book["asks"][0][0])) / 2
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
            KeyError, IndexError, ValueError, TypeError):
        return None
    finally:
        time.sleep(INTER_REQUEST_SLEEP)
    return mid


def usdt_symbols() -> dict[str, dict]:
    """USDT-quoted symbols keyed by base asset, with their tick size."""
    out = {}
    for s in get_json(f"{API}/symbols")["result"]:
        if s["quote_asset"] == "USDT" and s["status"] == "active":
            out[s["base_asset"]] = {
                "symbol": s["symbol"],
                "tick": float(s["price_step"]),
                "min_quote": float(s["min_quote_size"]),
            }
    return out


class PairProbe:
    """Rolling MM statistics for one symbol."""

    def __init__(self, coin: str, meta: dict, quote_usdt: float, horizon: float):
        self.coin = coin
        self.symbol = meta["symbol"]
        self.tick = meta["tick"]
        self.min_quote = meta["min_quote"]
        self.quote_usdt = quote_usdt
        self.horizon = horizon

        self.seen: collections.deque = collections.deque(maxlen=TRADE_MEMORY)
        self.seen_set: set = set()

        self.spreads_bps: list[float] = []
        self.fills: list[dict] = []       # settled fills, adverse selection known
        self.pending: list[dict] = []     # fills awaiting the horizon re-check
        self.fills_bid = 0
        self.fills_ask = 0
        self.base_inventory = 0.0
        self.usdt_cash = 0.0
        self.started = time.time()
        self.polls = 0
        self.quotable_polls = 0
        # Quote staged by the PREVIOUS poll. Trades seen this poll may only fill
        # this one — never a quote priced off the book we are reading right now.
        self.live_bid: float | None = None
        self.live_ask: float | None = None

    def remember(self, trade: tuple) -> bool:
        """True the first time a tape entry is seen."""
        if trade in self.seen_set:
            return False
        if len(self.seen) == self.seen.maxlen:
            self.seen_set.discard(self.seen[0])
        self.seen.append(trade)
        self.seen_set.add(trade)
        return True

    def poll(self, fair: float | None) -> None:
        """One observation. `fair` is COIN/USDT synthesised from the THB books."""
        book = get_json(f"{API}/depth?sym={self.symbol.lower()}&lmt=5")["result"]
        time.sleep(INTER_REQUEST_SLEEP)
        tape = get_json(f"{API}/trades?sym={self.symbol.lower()}&lmt=50")["result"]

        self.polls += 1
        if not book.get("bids") or not book.get("asks"):
            return

        best_bid = float(book["bids"][0][0])
        best_ask = float(book["asks"][0][0])
        mid = (best_bid + best_ask) / 2
        now = time.time()

        self.spreads_bps.append((best_ask - best_bid) / mid * 10_000)

        qty = self.quote_usdt / mid
        first_pass = self.polls == 1
        for entry in tape:
            trade = (entry[0], float(entry[1]), float(entry[2]), entry[3])
            fresh = self.remember(trade)
            # The first poll only seeds the dedupe window: that tape predates
            # any quote of ours, so it must never book a fill.
            if not fresh or first_pass:
                continue
            _, price, size, side = trade
            filled = min(size, qty)
            # Match against the quote STAGED LAST POLL, and retire a side once
            # it trades — a resting order is consumed, not infinitely refilled.
            if side == "SELL" and self.live_bid is not None and price <= self.live_bid:
                self._fill("bid", self.live_bid, filled, mid, now, fair)
                self.live_bid = None
            elif side == "BUY" and self.live_ask is not None and price >= self.live_ask:
                self._fill("ask", self.live_ask, filled, mid, now, fair)
                self.live_ask = None

        # Stage the quote for the NEXT poll off the book we just read.
        my_bid = best_bid + self.tick
        my_ask = best_ask - self.tick
        if my_bid < my_ask:
            self.quotable_polls += 1
            self.live_bid, self.live_ask = my_bid, my_ask
        else:
            # Spread too narrow to improve on both sides — stand aside.
            self.live_bid = self.live_ask = None

        self._settle(now, mid)

    def _fill(self, side: str, price: float, qty: float, mid: float,
              now: float, fair: float | None) -> None:
        if side == "bid":
            self.fills_bid += 1
            self.base_inventory += qty
            self.usdt_cash -= price * qty
        else:
            self.fills_ask += 1
            self.base_inventory -= qty
            self.usdt_cash += price * qty
        if fair:
            # Did the passive quote buy below, or sell above, true value?
            signed = (fair - price) if side == "bid" else (price - fair)
            fair_edge_bps = signed / fair * 10_000
        else:
            fair_edge_bps = None
        self.pending.append({
            "side": side, "price": price, "qty": qty,
            "mid_at_fill": mid, "ts": now, "fair_at_fill": fair,
            "fair_edge_bps": fair_edge_bps,
            "half_spread_bps": abs(mid - price) / mid * 10_000,
        })

    def _settle(self, now: float, mid: float) -> None:
        """Resolve fills whose adverse-selection horizon has elapsed."""
        still = []
        for f in self.pending:
            if now - f["ts"] < self.horizon:
                still.append(f)
                continue
            drift = (mid - f["mid_at_fill"]) / f["mid_at_fill"] * 10_000
            # Positive drift means the (stale) mid moved against the position.
            # Diagnostic only — these books barely reprice, so it trends to 0.
            f["drift_bps"] = -drift if f["side"] == "bid" else drift
            self.fills.append(f)
        self.pending = still

    def summary(self, mid: float | None) -> dict:
        mins = max((time.time() - self.started) / 60, 1e-9)
        fair_edges = [f["fair_edge_bps"] for f in self.fills if f["fair_edge_bps"] is not None]
        drifts = [f["drift_bps"] for f in self.fills]
        halves = [f["half_spread_bps"] for f in self.fills]
        volume = sum(f["price"] * f["qty"] for f in self.fills)
        equity = self.usdt_cash + (self.base_inventory * mid if mid else 0.0)
        return {
            "coin": self.coin,
            "median_spread_bps": statistics.median(self.spreads_bps) if self.spreads_bps else None,
            "quotable_pct": self.quotable_polls / self.polls * 100 if self.polls else 0.0,
            "fills_bid": self.fills_bid,
            "fills_ask": self.fills_ask,
            "fills_per_min": (self.fills_bid + self.fills_ask) / mins,
            "median_half_spread_bps": statistics.median(halves) if halves else None,
            "median_drift_bps": statistics.median(drifts) if drifts else None,
            "median_edge_bps": statistics.median(fair_edges) if fair_edges else None,
            "settled_fills": len(fair_edges),
            "inventory_base": self.base_inventory,
            "filled_volume_usdt": volume,
            "paper_pnl_usdt": equity,
            "paper_pnl_usdt_at_0p1_fee": equity - volume * USDT_FEE_AFTER,
            "minutes": mins,
        }


def fmt(value, spec: str = "8.2f", dash: str = "     -- ") -> str:
    return dash if value is None else format(value, spec)


def print_table(rows: list[dict], fee_note: str) -> None:
    print(f"\n  {dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}   USDT maker fee now: {fee_note}")
    print(f"  {'coin':<6}{'spread':>9}{'quotable':>10}{'fills':>8}{'f/min':>8}"
          f"{'half':>8}{'drift':>9}{'EDGE':>8}{'pnl@0%':>10}{'pnl@0.1%':>10}")
    print(f"  {'':<6}{'bps':>9}{'%':>10}{'b/a':>8}{'':>8}{'bps':>8}{'bps':>9}"
          f"{'vs fair':>8}{'USDT':>10}{'USDT':>10}")
    print(f"  {'-' * 94}")
    ranked = sorted(
        rows,
        key=lambda r: -(r["median_edge_bps"] if r["median_edge_bps"] is not None else -1e9),
    )
    for r in ranked:
        flag = ""
        if r["median_edge_bps"] is not None and r["median_edge_bps"] > 0:
            flag = "  <-- POSITIVE"
        ba = f"{r['fills_bid']}/{r['fills_ask']}"
        print(f"  {r['coin']:<6}{fmt(r['median_spread_bps'], '9.1f', '       --')}"
              f"{r['quotable_pct']:>9.0f}%"
              f"{ba:>8}"
              f"{r['fills_per_min']:>8.1f}"
              f"{fmt(r['median_half_spread_bps'], '8.1f')}"
              f"{fmt(r['median_drift_bps'], '9.1f')}"
              f"{fmt(r['median_edge_bps'], '8.1f')}"
              f"{r['paper_pnl_usdt']:>10.4f}"
              f"{r['paper_pnl_usdt_at_0p1_fee']:>10.4f}{flag}")


def verdict(rows: list[dict]) -> None:
    settled = [r for r in rows if r["settled_fills"] >= 10 and r["median_edge_bps"] is not None]
    print()
    if not settled:
        print("  not enough settled fills yet — keep it running, need >=10 per pair")
        return
    best = max(settled, key=lambda r: r["median_edge_bps"])
    print(f"  best: {best['coin']} edge-vs-fair {best['median_edge_bps']:+.1f} bps/fill "
          f"over {best['settled_fills']} fills, {best['minutes']:.0f} min")
    if best["median_edge_bps"] <= 0:
        print("  -> NO GO. Passive fills land on the wrong side of fair value.")
    elif best["paper_pnl_usdt_at_0p1_fee"] <= 0:
        print("  -> promo-only. Positive at 0% fee, dies at 0.1% after 12 Aug 2026.")
    else:
        print("  -> survives the 12 Aug fee cliff. Candidate for a live micro test.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", help="comma-separated base assets (default: all USDT pairs)")
    ap.add_argument("--poll", type=float, default=3.0, help="seconds between polls (default 3)")
    ap.add_argument("--quote-usdt", type=float, default=30.0, help="notional per side (default 30)")
    ap.add_argument("--horizon", type=float, default=30.0,
                    help="seconds to wait before scoring adverse selection (default 30)")
    ap.add_argument("--duration", type=float, metavar="MIN",
                    help="stop after MIN minutes (default: run until Ctrl-C)")
    ap.add_argument("--log", default="output/bitkub-arb", help="JSONL output directory")
    args = ap.parse_args()

    # Keep the table readable when stdout is redirected to a file.
    sys.stdout.reconfigure(line_buffering=True)

    try:
        meta = usdt_symbols()
    except urllib.error.URLError as exc:
        print(f"cannot reach Bitkub API: {exc}", file=sys.stderr)
        return 1

    wanted = [c.strip().upper() for c in args.pairs.split(",")] if args.pairs else sorted(meta)
    missing = [c for c in wanted if c not in meta]
    if missing:
        print(f"no USDT pair for: {', '.join(missing)}", file=sys.stderr)
        return 1

    for coin in wanted:
        if args.quote_usdt < meta[coin]["min_quote"]:
            print(f"--quote-usdt below {coin} minimum {meta[coin]['min_quote']}", file=sys.stderr)
            return 1

    probes = [PairProbe(c, meta[c], args.quote_usdt, args.horizon) for c in wanted]
    fee_note = ("0% promo" if dt.datetime.now(dt.timezone.utc).date() <= USDT_PROMO_ENDS
                else f"{USDT_FEE_AFTER * 100:.1f}%")

    logdir = pathlib.Path(args.log)
    logdir.mkdir(parents=True, exist_ok=True)
    logpath = logdir / f"mm-probe-{dt.date.today():%Y%m%d}.jsonl"

    print(f"probing {len(probes)} pairs: {', '.join(wanted)}")
    print(f"quote {args.quote_usdt} USDT/side, 1 tick inside touch, "
          f"adverse horizon {args.horizon:.0f}s, poll {args.poll}s")
    print("first poll only seeds the tape — fills start counting on poll 2")
    print("Ctrl-C for final summary")

    stop = False

    def on_sigint(_sig, _frm):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, on_sigint)

    deadline = time.time() + args.duration * 60 if args.duration else None

    with logpath.open("a") as logfile:
        round_no = 0
        while not stop:
            if deadline and time.time() >= deadline:
                print(f"\n  reached --duration {args.duration:g} min")
                break
            round_no += 1
            rows = []
            usdt_thb = book_mid("USDT_THB")
            for p in probes:
                if stop:
                    break
                # Fair value from the tight THB books, not the stale USDT mid.
                coin_thb = book_mid(f"{p.coin}_THB")
                fair = coin_thb / usdt_thb if (coin_thb and usdt_thb) else None
                try:
                    p.poll(fair)
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                    print(f"  {p.coin}: poll failed ({exc.__class__.__name__}), skipping",
                          file=sys.stderr)
                    continue
                rows.append(p.summary(book_mid(p.symbol)))

            if rows:
                print_table(rows, fee_note)
                verdict(rows)
                stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                for r in rows:
                    logfile.write(json.dumps({"ts": stamp, "round": round_no, **r}) + "\n")
                logfile.flush()

            for _ in range(int(max(args.poll, 0.1) * 10)):
                if stop:
                    break
                time.sleep(0.1)

    print(f"\nlogged to {logpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
