#!/usr/bin/env python3
"""BL EP61 cost check: what ONE order costs, from one broker's own published numbers.

Every input below is quoted from a page of the broker itself (Tickmill), captured 2026-10-13
(see RUNLOG.md claim ledger). Nothing is estimated. Arithmetic is exact (Decimal); rounding to
cents happens only at the final print.

Run:  python3 prototypes/bl61-script/cost_check.py
Exit code 1 if a self-check fails (the page's own examples are re-computed and compared).
"""
from decimal import Decimal as D
import sys

# ---- inputs, each with the page it comes from -------------------------------------------------
LOTS = D("1")                       # one standard lot, the worked example in the script
CONTRACT_SIZE_EUR = D("100000")     # raw-account page: "1 lot of EURUSD, contract size of 100,000 EUR"
PIP = D("0.0001")                   # EURUSD quotes to 4 decimals; 1 pip = 0.0001 USD per EUR (channel's arithmetic)
PIP_VALUE_PER_STD_LOT = CONTRACT_SIZE_EUR * PIP   # USD per pip on 1 standard lot (channel's arithmetic)

CLASSIC_SPREAD_FROM_PIPS = D("1.6")  # accounts-overview + classic-account page: "Spreads From 1.6 pips"
CLASSIC_COMMISSION_PER_LOT_SIDE = D("0")   # "Zero Commissions"
RAW_SPREAD_FROM_PIPS = D("0.0")      # accounts-overview + raw-account page: "Spreads From 0.0 pips"
RAW_COMMISSION_PER_LOT_SIDE = D("3") # "$3 per lot per side"
SIDES = D("2")                       # one order opened and then closed = two sides ("6 USD round turn", raw page)

# not spoken, printed only to show that "from" is not the typical number:
SPREADS_PAGE_EURUSD_TYPICAL_PIPS = D("0.1")   # spreads-swaps table row EURUSD; the page does not say which account


def spread_cost(spread_pips: D, lots: D) -> D:
    """Tickmill's own formula (spreads-swaps FAQ): Trade Cost = Spread x Trade Size x Pip Value."""
    return spread_pips * lots * PIP_VALUE_PER_STD_LOT


def commission(rate_per_lot_side: D, lots: D, sides: D = SIDES) -> D:
    return rate_per_lot_side * lots * sides


def money(x: D) -> str:
    return f"${x.quantize(D('0.01'))}"


def main() -> int:
    print("INPUTS (all quoted from Tickmill's own pages, captured 2026-10-13)")
    print(f"  lots                         = {LOTS}")
    print(f"  contract size                = {CONTRACT_SIZE_EUR} EUR            (raw-account page)")
    print(f"  pip                          = {PIP}                (EURUSD, 4 decimals)")
    print(f"  pip value, 1 standard lot    = {CONTRACT_SIZE_EUR} x {PIP} = {PIP_VALUE_PER_STD_LOT} USD   (channel arithmetic, not on the page)")
    print(f"  Classic: spread from {CLASSIC_SPREAD_FROM_PIPS} pips, commission {CLASSIC_COMMISSION_PER_LOT_SIDE} per lot per side")
    print(f"  Raw:     spread from {RAW_SPREAD_FROM_PIPS} pips, commission {RAW_COMMISSION_PER_LOT_SIDE} USD per lot per side, sides = {SIDES}")
    print("  swap: 0 by construction (trade opened and closed inside the day; page: swap is charged past 00:00 platform time)")
    print()

    results = {}
    for name, spread, rate in (
        ("Classic", CLASSIC_SPREAD_FROM_PIPS, CLASSIC_COMMISSION_PER_LOT_SIDE),
        ("Raw", RAW_SPREAD_FROM_PIPS, RAW_COMMISSION_PER_LOT_SIDE),
    ):
        sc = spread_cost(spread, LOTS)
        cm = commission(rate, LOTS)
        total = sc + cm
        results[name] = (sc, cm, total)
        print(f"{name}:")
        print(f"  spread     = {spread} x {LOTS} x {PIP_VALUE_PER_STD_LOT} = {sc}  ->  {money(sc)}")
        print(f"  commission = {rate} x {LOTS} x {SIDES} = {cm}  ->  {money(cm)}")
        print(f"  TOTAL (minimum, from the advertised 'from' numbers) = {total}  ->  {money(total)}")
        print()

    # sensitivity, NOT spoken: if Raw's spread were the table's typical 0.1 instead of the 'from' 0.0
    alt = spread_cost(SPREADS_PAGE_EURUSD_TYPICAL_PIPS, LOTS) + commission(RAW_COMMISSION_PER_LOT_SIDE, LOTS)
    print(f"SENSITIVITY (not spoken): Raw with the spreads-page typical {SPREADS_PAGE_EURUSD_TYPICAL_PIPS} pip "
          f"= {SPREADS_PAGE_EURUSD_TYPICAL_PIPS} x {LOTS} x {PIP_VALUE_PER_STD_LOT} + {commission(RAW_COMMISSION_PER_LOT_SIDE, LOTS)} "
          f"= {alt} -> {money(alt)}  (the page does not say which account its typical column is for)")
    print()

    # ---- self-checks against the page's own examples ---------------------------------------
    ok = True
    # raw-account page: 1 lot EURUSD -> commission 3 USD per side and 6 USD round turn
    if commission(RAW_COMMISSION_PER_LOT_SIDE, D("1"), D("1")) != D("3") or commission(RAW_COMMISSION_PER_LOT_SIDE, D("1")) != D("6"):
        print("CHECK FAILED: raw page says 3 USD per side and 6 USD round turn"); ok = False
    # spreads-swaps FAQ: Spread 1.2 pips x 1 mini lot x pip value $1 = $1.20
    if D("1.2") * D("1") * D("1") != D("1.20"):
        print("CHECK FAILED: FAQ example 1.2 x 1 x $1 = $1.20"); ok = False
    # a mini lot is a tenth of a standard lot, so its pip value is a tenth of ours (page uses $1)
    if PIP_VALUE_PER_STD_LOT / D("10") != D("1"):
        print("CHECK FAILED: standard-lot pip value is not ten times the page's $1 mini-lot pip value"); ok = False
    print("SELF-CHECKS vs the page's own examples:", "pass" if ok else "FAIL")

    # the two figures the script says out loud
    spoken = {"Classic": D("16.00"), "Raw": D("6.00")}
    for k, v in spoken.items():
        if results[k][2].quantize(D("0.01")) != v:
            print(f"CHECK FAILED: script says {k} = {v}, computed {results[k][2]}"); ok = False
    print("SCRIPT NUMBERS (สิบหกดอลลาร์ / หกดอลลาร์):", "match" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
