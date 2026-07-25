#!/usr/bin/env python3
"""Bitkub book-reactivity meter — read-only proxy for "will they requote on me?"

Bitkub has no testnet, and trading needs KYC, so mm_live_test.py cannot run yet.
The question it exists to answer — does an incumbent maker reprice inside a new
order — still has a free proxy: how actively is the book being managed?

    Touch frozen for minutes, no reaction after trades
        -> the quote is set-and-forget. A new order inside it would rest.

    Touch churning every few seconds, repricing right after each print
        -> an algo is watching. It will step inside a new order too, and the
           paper edge turns into a penny-jump war.

Measured per symbol:

    touch changes/min   how often best bid or best ask moves at all
    dwell               how long one touch price survives (median and p90)
    reaction            seconds from a trade printing to the next touch change;
                        a tight, small number means something is reacting to flow

None of this proves the reflexive case either way — only a real order does. It
narrows the prior cheaply while KYC is pending.

Usage:
    python3 book_reactivity.py --pairs BTC,ETH --minutes 10
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
import sys
import time
import urllib.error
import urllib.request

API = "https://api.bitkub.com/api/v3/market"
REQUEST_TIMEOUT = 10
INTER_REQUEST_SLEEP = 0.1


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "bitkub-reactivity/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


class Watcher:
    def __init__(self, coin: str):
        self.coin = coin
        self.symbol = f"{coin}_USDT"
        self.last_touch: tuple[float, float] | None = None
        self.last_change_at: float | None = None
        self.dwells: list[float] = []
        self.changes = 0
        self.samples = 0
        # Trades awaiting the next touch change, to time the reaction.
        self.awaiting: list[float] = []
        self.reactions: list[float] = []
        self.seen_trades: set[tuple] = set()
        self.trades_seen = 0
        self.seeded = False

    def sample(self) -> None:
        now = time.time()
        try:
            book = get_json(f"{API}/depth?sym={self.symbol.lower()}&lmt=1")["result"]
            touch = (float(book["bids"][0][0]), float(book["asks"][0][0]))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
                KeyError, IndexError, ValueError):
            return
        self.samples += 1

        if self.last_touch is None:
            self.last_touch, self.last_change_at = touch, now
        elif touch != self.last_touch:
            self.changes += 1
            if self.last_change_at is not None:
                self.dwells.append(now - self.last_change_at)
            # Every trade still waiting for a reprice just got one.
            for trade_at in self.awaiting:
                self.reactions.append(now - trade_at)
            self.awaiting.clear()
            self.last_touch, self.last_change_at = touch, now

        time.sleep(INTER_REQUEST_SLEEP)
        try:
            tape = get_json(f"{API}/trades?sym={self.symbol.lower()}&lmt=30")["result"]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
            return
        for entry in tape:
            key = tuple(entry)
            if key in self.seen_trades:
                continue
            self.seen_trades.add(key)
            # The first tape read is history — it must not start a reaction timer.
            if not self.seeded:
                continue
            self.trades_seen += 1
            self.awaiting.append(now)
        self.seeded = True
        if len(self.seen_trades) > 2000:
            self.seen_trades = set(list(self.seen_trades)[-500:])

    def summary(self, minutes: float) -> dict:
        return {
            "symbol": self.symbol,
            "minutes": round(minutes, 1),
            "samples": self.samples,
            "touch_changes_per_min": round(self.changes / minutes, 2) if minutes else 0.0,
            "median_dwell_sec": round(statistics.median(self.dwells), 1) if self.dwells else None,
            "p90_dwell_sec": (round(sorted(self.dwells)[int(len(self.dwells) * 0.9)], 1)
                              if len(self.dwells) >= 10 else None),
            "max_dwell_sec": round(max(self.dwells), 1) if self.dwells else None,
            "trades_seen": self.trades_seen,
            "median_reaction_sec": (round(statistics.median(self.reactions), 1)
                                    if self.reactions else None),
            "reactions_measured": len(self.reactions),
        }


def read_result(row: dict) -> str:
    """Turn the numbers into the call they imply."""
    dwell = row["median_dwell_sec"]
    if dwell is None:
        return "no touch change observed — book frozen for the whole window"
    if dwell >= 30:
        return "set-and-forget book — an order inside it would likely rest"
    if dwell >= 5:
        return "moderately managed — contested, outcome unclear"
    return "actively managed — expect an immediate requote inside you"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default="BTC,ETH", help="comma-separated base assets")
    ap.add_argument("--minutes", type=float, default=10.0, help="how long to watch")
    ap.add_argument("--log", default="output/bitkub-arb")
    args = ap.parse_args()

    sys.stdout.reconfigure(line_buffering=True)
    coins = [c.strip().upper() for c in args.pairs.split(",")]
    watchers = [Watcher(c) for c in coins]

    print(f"watching {', '.join(w.symbol for w in watchers)} for {args.minutes:g} min")
    print("measuring: how long the touch survives, and how fast it moves after a trade\n")

    started = time.time()
    deadline = started + args.minutes * 60
    next_report = started + 60
    while time.time() < deadline:
        for w in watchers:
            w.sample()
        if time.time() >= next_report:
            mins = (time.time() - started) / 60
            parts = []
            for w in watchers:
                if w.dwells:
                    parts.append(f"{w.coin} chg/min {w.changes / mins:4.1f} "
                                 f"dwell {statistics.median(w.dwells):5.1f}s")
                else:
                    parts.append(f"{w.coin} no change yet")
            print(f"  [{mins:4.1f} min] " + "   ".join(parts))
            next_report += 60

    minutes = (time.time() - started) / 60
    rows = [w.summary(minutes) for w in watchers]

    print(f"\n  {'symbol':<12}{'chg/min':>9}{'dwell':>8}{'p90':>8}{'max':>8}"
          f"{'trades':>8}{'react':>8}   read")
    print(f"  {'-' * 96}")
    for r in rows:
        def f(value, spec: str = "8.1f") -> str:
            return "      --" if value is None else format(value, spec)
        print(f"  {r['symbol']:<12}{r['touch_changes_per_min']:>9.2f}"
              f"{f(r['median_dwell_sec'])}{f(r['p90_dwell_sec'])}{f(r['max_dwell_sec'])}"
              f"{r['trades_seen']:>8}{f(r['median_reaction_sec'])}   {read_result(r)}")

    logdir = pathlib.Path(args.log)
    logdir.mkdir(parents=True, exist_ok=True)
    logpath = logdir / f"reactivity-{dt.date.today():%Y%m%d}.jsonl"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with logpath.open("a") as fh:
        for r in rows:
            fh.write(json.dumps({"ts": stamp, **r}) + "\n")
    print(f"\n  logged to {logpath}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  interrupted")
        raise SystemExit(130)
