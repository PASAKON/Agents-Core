# EA sweep: KARATE-X, Pro3XTHUNDER, MoonX gold, and SAMWOLF

**Status: blocked before download or execution.** The requested comparison could not be completed because the Contabo-to-Winbox SSH connection was denied by the environment (`Control socket connect(...): Operation not permitted`). No EA was downloaded or run, and no baseline metrics were available to inspect.

## Results

| EA | Period / symbol coverage | Net | PF | Equity DD | Trades | Trades / trading day | Win rate | Gold tested |
|---|---|---:|---:|---:|---:|---:|---:|---|
| KARATE-X | Not available | — | — | — | — | — | — | Unknown |
| Pro3XTHUNDER | Not available | — | — | — | — | — | — | Unknown |
| MoonX gold | Not available | — | — | — | — | — | — | Unknown |
| SAMWOLF_1.7 | Not tested | — | — | — | — | — | — | No |

The baseline requested at `C:\Users\passg\ea-eval\sweep3\results.csv` on Winbox was not retrieved. No recommendation is supportable without those results and the SAMWOLF scan and backtest.

## Not checked / risk

- SAMWOLF binary authenticity, SHA-256, size, `strings -a` / `strings -el` findings, and safety scan were not checked; the binary was not downloaded.
- CEO hold, lease status, terminal process identity, free RAM, tester configuration, and per-case metrics were not checked.
- The 1-minute OHLC model can overstate scalper performance. This risk remains applicable to any eventual comparison.
- Account numbers and balances were not accessed or reported.
