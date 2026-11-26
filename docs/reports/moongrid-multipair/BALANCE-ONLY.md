# MoonGrid multi-symbol: balance-only results (order O-20261121-1059-5a69)

Source: winbox tester log extract, 98 rows, 83 distinct runs (duplicates in the extract removed).
Settings: live MoonGrid inputs, lot 0.01, deposit 100 USD. Period: 2024, 2025, 2026 (to 20 Nov), and 1 Oct to 20 Nov 2026.

## Not measured (say so plainly)
- Max drawdown %, profit factor and trade counts were NOT measured: the tester reports did not write.
- "Blown" = final balance at or below 0 only. Equity dips inside a run are unknown.
- Six runs end at exactly 100.00: no trades were placed.
- Correlation between symbols was NOT computed: no daily price series in this extract.

## Top 12 by final balance (USD)
| final | symbol | period | spread cap |
|---|---|---|---|
| 193.68 | ETHUSDc | 2026 | 35 |
| 111.16 | GBPJPYc | 2024 | 35 |
| 106.44 | USDJPYc | 2024 | 35 |
| 104.24 | EURJPYc | 2024 | 35 |
| 103.79 | XAGUSDc | 2024 | 35 |
| 103.60 | GBPAUDc | 2025 | 35 |
| 103.29 | GBPJPYc | 2026 | 35 |
| 102.66 | EURAUDc | 2025 | 35 |
| 102.48 | CADJPYc | 2024 | 35 |
| 102.24 | GBPAUDc | 2024 | 35 |
| 102.08 | AUDJPYc | 2024 | 35 |
| 101.35 | EURAUDc | 2024 | 35 |

## Bottom (worst final balance)
| final | symbol | period |
|---|---|---|
| -9.55 | XAUUSDc | 2026 (1 Oct to 20 Nov) |
| -8.24 | BTCUSDc | 2024, spread cap 0 |
| -2.74 | XAUUSDc | 2025 |
| -2.57 | XAUUSDc | 2024 |
| -0.89 | XAUUSDc | 2026 |
| -0.72 | ETHUSDc | 2025 |

Counts: 37 of 83 distinct runs end below 100. BTCUSDc at spread cap 35 never traded (balance stays 100.00).

## Read
- Gold (XAUUSDc) lost in every period tested. Do not use it.
- JPY crosses (GBPJPY, USDJPY, EURJPY, CADJPY, AUDJPY) and the AUD/GBP crosses finished above 100 in 2024 and 2025.
- The FX majors finished close to 100: few trades, so little signal either way.
- Balance alone cannot rank by drawdown. A 3-6 symbol portfolio cannot be recommended until a drawdown round runs.

## Next (needs a CEO decision)
A drawdown round: reports must be written, or equity sampled per run. Requires the screen-lease decision.

## Per-symbol summary (83 distinct runs; blown = final balance <= 0)
| symbol | runs | mean final | min | blown |
|---|---|---|---|---|
| USDJPYc | 4 | 102.14 | 99.92 | 0 |
| GBPAUDc | 4 | 101.53 | 100.07 | 0 |
| GBPJPYc | 4 | 101.33 | 90.66 | 0 |
| EURAUDc | 4 | 101.00 | 99.68 | 0 |
| USDCADc | 4 | 100.38 | 100.06 | 0 |
| AUDNZDc | 4 | 100.15 | 99.79 | 0 |
| CADJPYc | 4 | 100.12 | 97.47 | 0 |
| EURUSDc, GBPUSDc, AUDUSDc, EURGBPc, NZDUSDc | 4 each | 98.9 to 100.0 | 96.6 | 0 |
| EURJPYc | 4 | 96.99 | 82.91 | 0 |
| BTCUSDc | 5 | 78.35 | -8.24 | 1 |
| ETHUSDc | 4 | 73.10 | -0.72 | 2 |
| XAGUSDc | 4 | 42.70 | -0.65 | 2 |
| US30c | 2 | 28.60 | 26.83 | 0 |
| XAUUSDc | 4 | -3.94 | -9.55 | 4 |

## Where it fails (balance evidence only)
- Gold (XAU) blew up in 4 of 4 runs. Silver, ETH and BTC blew up in some runs.
- Every FX pair stayed above 0 in every run; none blew.

## Recommendation (candidate, NOT verified)
- Shortlist: USDJPYc, GBPAUDc, USDCADc. Three different currency legs, so less overlap than the JPY/AUD crosses.
- Correlation NOT computed: the extract has no daily price series. Combined drawdown NOT measured.
- Avoid XAU, XAG, ETH, BTC and US30 on $100 at this lot.

## Still not measured
Max drawdown %, profit factor, trade counts, daily correlation, combined portfolio drawdown. A drawdown round is needed for any of these.
